#!/usr/bin/env python3
"""
h4_level_edge_explore.py — Stage-1 IC (Information Coefficient) 探索ツール

目的:
  「H4 heavy wall への 15m 価格相互作用イベント」をリッチな特徴量付きでログ化し、
  各特徴量が forward-return を予測するか (Spearman IC) を測る。
  これは戦略の BT ではなく、エッジが「条件付け」で救えるかの探索。
  設計準拠: docs/superpowers/specs/2026-06-22-h4-level-edge-discovery-design.md §3/§7

絶対規律 (このツールが守るもの):
  1. 因果性: いかなる特徴量・イベント判定も未来 bar を参照しない。
     H4 swing pivot は Williams Fractal(n=2) で center の 2 本後に確定するため、
     pivot は center 時刻 + 2 H4 bar 経過後 (= confirm bar close) からのみ利用可能。
  2. train スライスのみ: 共通窓 2022-01〜2026-05 の時系列前半 60% だけ使う。holdout 不可触。
  3. 閾値最適化禁止: IC は連続特徴量と forward-return の Spearman 相関のみ。2値化WR最大化はしない。
  4. silent except 禁止: skip は理由を count して最後に出力する。

CLI:
  python3 tools/h4_level_edge_explore.py --pair EUR_USD --horizon 12,48

モジュールトップで副作用禁止 (os.environ / chdir / parse_args / Thread を import 時に実行しない)。
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "cache" / "massive"

# ── 共通窓 (設計 §7: chronological train/holdout split の起点) ──
# 4h データが 2021-12-24 起点、15m が長期。共通窓を 2022-01-01〜2026-05-15 に固定。
WINDOW_START = pd.Timestamp("2022-01-01", tz="UTC")
WINDOW_END = pd.Timestamp("2026-05-15", tz="UTC")
TRAIN_FRAC = 0.60  # 前半 60% のみ探索。後半 holdout は触らない。

# ── 凍結パラメータ (設計 §6 の初期値。Stage1 では IC 計測のみ、閾値最適化しない) ──
FRACTAL_N = 2          # Williams Fractal: center ± n 本で swing 判定。確定は center+n 本後。
LOOKBACK_H4 = 180      # wall 構成窓 (≈30 営業日)。直近 H4 swing をこの本数だけ走査。
MAX_PIVOTS = 40        # 設計: 直近 maxPivots=40 の swing price を保持。
KDE_TOL_MULT = 0.5     # tol = 0.5 × ATR14(H4)。クラスタ許容幅。
MIN_TOUCHES = 3        # heavy wall = touch_count ≥ 3。
INTERACT_TOL_MULT = 0.5  # 相互作用帯 = ±0.5 × ATR14(15m) (イベント定義のスペック)。
APPROACH_N = 4         # approach_velocity の lookback (直近 4 本 = 1h)。
ATR_MED_WINDOW = 2000  # atr_regime の長期中央値窓 (15m, ≈3 週間)。長期ボラ基準。

ATR_PERIOD = 14

# ── セッション境界 (UTC, 設計のセッション分類) ──
# Tokyo: 00-07 UTC / London: 07-12 UTC / NY: 12-21 UTC / その他は Off
def _session_label(hour_utc: int) -> str:
    if 0 <= hour_utc < 7:
        return "Tokyo"
    if 7 <= hour_utc < 12:
        return "London"
    if 12 <= hour_utc < 21:
        return "NY"
    return "Off"


def _pip_size(pair: str) -> float:
    """pip サイズ。JPY クロスは 0.01、それ以外は 0.0001。"""
    return 0.01 if pair.endswith("_JPY") else 0.0001


# ──────────────────────────────────────────────────────────────────────
# 指標計算
# ──────────────────────────────────────────────────────────────────────
def _atr(df: pd.DataFrame, period: int = ATR_PERIOD) -> pd.Series:
    """Wilder ATR。完全 causal (shift で前 close を使う)。"""
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    # Wilder smoothing (EWM alpha=1/period, adjust=False)
    return tr.ewm(alpha=1.0 / period, adjust=False).mean()


def _ema(s: pd.Series, span: int) -> pd.Series:
    return s.ewm(span=span, adjust=False).mean()


# ──────────────────────────────────────────────────────────────────────
# H4 swing 検出 (Williams Fractal, causal-confirmed)
# ──────────────────────────────────────────────────────────────────────
@dataclass
class Swing:
    confirm_time: pd.Timestamp  # この時刻 (= center+n bar の close) から利用可能
    price: float
    kind: str  # "high" / "low"


def detect_h4_swings(h4: pd.DataFrame, n: int = FRACTAL_N) -> list[Swing]:
    """Williams Fractal n で swing high/low を検出。
    center bar i が swing high <=> High[i] > High[i±1..n] 全て。
    確定は center+n 本後 (未来 n 本を見て初めて判定できるため)。
    confirm_time = h4.index[i + n] (= 確定 H4 bar の時刻)。
    """
    highs = h4["High"].to_numpy()
    lows = h4["Low"].to_numpy()
    idx = h4.index
    out: list[Swing] = []
    m = len(h4)
    for i in range(n, m - n):
        wh = highs[i - n : i + n + 1]
        wl = lows[i - n : i + n + 1]
        center = n
        # swing high: center が窓内で厳密最大
        if highs[i] == wh.max() and (wh[center] > np.delete(wh, center)).all():
            out.append(Swing(confirm_time=idx[i + n], price=float(highs[i]), kind="high"))
        # swing low: center が窓内で厳密最小
        if lows[i] == wl.min() and (wl[center] < np.delete(wl, center)).all():
            out.append(Swing(confirm_time=idx[i + n], price=float(lows[i]), kind="low"))
    return out


def build_heavy_walls(
    swings_known: list[Swing],
    atr_h4: float,
    min_touches: int = MIN_TOUCHES,
    tol_mult: float = KDE_TOL_MULT,
) -> list[tuple[float, int]]:
    """確定済み swing 群 (= 評価時点で既知のもののみ) から heavy wall を構成。
    近傍 (±tol) クラスタ化 → touch_count ≥ min_touches を heavy wall とする。
    クラスタ中心 = 近傍 swing price の平均。
    返り値: [(wall_price, touch_count), ...] price 昇順。
    """
    if not swings_known or atr_h4 <= 0:
        return []
    tol = tol_mult * atr_h4
    prices = np.sort(np.array([s.price for s in swings_known], dtype=float))
    walls: list[tuple[float, int]] = []
    used = np.zeros(len(prices), dtype=bool)
    for i in range(len(prices)):
        if used[i]:
            continue
        # price[i] を種に ±tol 帯のメンバを集める (greedy 単一パス)
        mask = (np.abs(prices - prices[i]) <= tol) & (~used)
        members = prices[mask]
        if len(members) >= min_touches:
            walls.append((float(members.mean()), int(len(members))))
            used[mask] = True
    return walls


# ──────────────────────────────────────────────────────────────────────
# イベント抽出
# ──────────────────────────────────────────────────────────────────────
@dataclass
class SkipCounter:
    counts: Counter = field(default_factory=Counter)

    def add(self, reason: str, n: int = 1):
        self.counts[reason] += n

    def report(self) -> str:
        if not self.counts:
            return "  (skip 0 件)"
        lines = []
        for reason, n in self.counts.most_common():
            lines.append(f"  - {reason}: {n}")
        return "\n".join(lines)


def extract_events(
    pair: str,
    m15: pd.DataFrame,
    h4: pd.DataFrame,
    horizons: list[int],
    skips: SkipCounter,
) -> pd.DataFrame:
    """15m closed bar ごとに H4 heavy wall 相互作用イベントを抽出。
    全ての特徴量・wall は評価 bar の close 時点で既知の過去情報のみを使う (causal)。
    forward-return は event bar の **次** 15m open を基準に計算。
    """
    pip = _pip_size(pair)

    # ── 15m 指標 (causal) ──
    m15 = m15.copy()
    m15["atr"] = _atr(m15, ATR_PERIOD)
    m15["atr_med"] = m15["atr"].rolling(ATR_MED_WINDOW, min_periods=200).median()

    o = m15["Open"].to_numpy()
    h = m15["High"].to_numpy()
    l = m15["Low"].to_numpy()
    c = m15["Close"].to_numpy()
    atr15 = m15["atr"].to_numpy()
    atr_med = m15["atr_med"].to_numpy()
    idx15 = m15.index
    n15 = len(m15)

    # ── H4 指標 (causal: EMA / ATR は shift 不要だが「確定 bar のみ」で参照する) ──
    h4 = h4.copy()
    h4["atr"] = _atr(h4, ATR_PERIOD)
    h4["ema9"] = _ema(h4["Close"], 9)
    h4["ema21"] = _ema(h4["Close"], 21)
    h4["ema50"] = _ema(h4["Close"], 50)
    h4_idx = h4.index
    h4_atr = h4["atr"].to_numpy()
    h4_ema9 = h4["ema9"].to_numpy()
    h4_ema21 = h4["ema21"].to_numpy()
    h4_ema50 = h4["ema50"].to_numpy()

    # ── swing 検出 (確定時刻つき) ──
    swings = detect_h4_swings(h4, FRACTAL_N)
    swing_confirm = np.array([s.confirm_time.value for s in swings])  # ns int
    swing_order = np.argsort(swing_confirm)
    swings = [swings[i] for i in swing_order]
    swing_confirm = swing_confirm[swing_order]

    # 15m bar の時刻 -> その時点で「確定済み」の最新 H4 bar の位置を引くため
    # H4 bar i は idx i の close == 次 H4 bar の open。close 時刻 = h4_idx[i] + 4h。
    # ある 15m close 時刻 t に対し、close 済み H4 bar の最新は (open+4h) <= t を満たす最大 i。
    h4_close_time = (h4_idx + pd.Timedelta(hours=4)).values.astype("int64")
    swing_confirm_close = swing_confirm + pd.Timedelta(hours=4).value  # confirm bar も close 後に既知

    max_h = max(horizons)
    rows = []

    # 各 15m bar を走査
    for i in range(ATR_PERIOD + 1, n15):
        a15 = atr15[i]
        if not np.isfinite(a15) or a15 <= 0:
            skips.add("atr15 invalid/NaN")
            continue

        t_close = idx15[i].value  # この 15m bar の close 時刻 (ns)

        # ── この時点で確定済み H4 bar の最新位置 j (close <= t_close) ──
        j = np.searchsorted(h4_close_time, t_close, side="right") - 1
        if j < FRACTAL_N + 1:
            skips.add("h4 history insufficient")
            continue
        atr_h4 = h4_atr[j]
        if not np.isfinite(atr_h4) or atr_h4 <= 0:
            skips.add("atr_h4 invalid/NaN")
            continue

        # ── この時点で確定済み swing (confirm bar の close <= t_close) ──
        # swing_confirm_close が t_close 以下のもののみ既知。
        k = np.searchsorted(swing_confirm_close, t_close, side="right")
        if k == 0:
            skips.add("no confirmed h4 swing yet")
            continue
        known = swings[max(0, k - MAX_PIVOTS) : k]  # 直近 MAX_PIVOTS の確定 swing
        # lookback_h4 窓: confirm が現在 H4 close から LOOKBACK_H4 本以内
        cutoff_time = h4_close_time[max(0, j - LOOKBACK_H4)]
        known = [s for s in known if (s.confirm_time.value + pd.Timedelta(hours=4).value) >= cutoff_time]
        if not known:
            skips.add("no swing within lookback window")
            continue

        walls = build_heavy_walls(known, atr_h4, MIN_TOUCHES, KDE_TOL_MULT)
        if not walls:
            skips.add("no heavy wall (touch<min)")
            continue

        close_i = c[i]
        wall_prices = np.array([w[0] for w in walls])
        wall_tc = np.array([w[1] for w in walls])

        # 最近接 heavy wall
        d = np.abs(wall_prices - close_i)
        nearest = int(np.argmin(d))
        wall = wall_prices[nearest]
        touch_count = int(wall_tc[nearest])

        # 相互作用イベント判定: close が ±(INTERACT_TOL × ATR15) 帯に入る
        band = INTERACT_TOL_MULT * a15
        if abs(close_i - wall) > band:
            # イベントではない (帯外) — skip ではなく単に非イベント。count しない。
            continue

        # forward-return の余地があるか (次 open + max horizon が存在)
        if i + 1 + max_h >= n15:
            skips.add("insufficient forward bars")
            continue

        # ── 特徴量 (全て過去/現在 bar のみ) ──
        # dist_to_wall_atr (符号付き: close が wall より上なら +)
        dist_to_wall_atr = (close_i - wall) / a15

        # wick_ratio: 上下ヒゲの非対称度。+: 上ヒゲ優勢 (上方向 reject)。
        rng = h[i] - l[i]
        if rng <= 0:
            skips.add("zero-range bar")
            continue
        body_hi = max(o[i], c[i])
        body_lo = min(o[i], c[i])
        upper_wick = h[i] - body_hi
        lower_wick = body_lo - l[i]
        wick_ratio = (upper_wick - lower_wick) / rng  # [-1, +1]

        # close_position
        close_position = (close_i - l[i]) / rng  # [0,1]

        # approach_velocity: 直近 N bar の close 変化 / ATR15
        if i - APPROACH_N < 0:
            skips.add("approach window insufficient")
            continue
        approach_velocity = (close_i - c[i - APPROACH_N]) / a15

        # h4_bias: H4 EMA(9/21/50) 構造スコア (causal, 確定 H4 bar j)
        e9, e21, e50 = h4_ema9[j], h4_ema21[j], h4_ema50[j]
        if not (np.isfinite(e9) and np.isfinite(e21) and np.isfinite(e50)):
            skips.add("h4 ema NaN")
            continue
        if e9 > e21 > e50:
            h4_bias = 1.0
        elif e9 < e21 < e50:
            h4_bias = -1.0
        else:
            h4_bias = 0.0

        # session
        session = _session_label(idx15[i].hour)

        # atr_regime
        amed = atr_med[i]
        if not np.isfinite(amed) or amed <= 0:
            skips.add("atr_med NaN/invalid")
            continue
        atr_regime = a15 / amed

        # dist_to_next_wall_atr: 反対側 (close から見て wall と逆側) の最近接 heavy wall
        if close_i >= wall:
            # 現在 wall は下側 (support 的)。反対側 = close より上の最近接 wall。
            above = wall_prices[wall_prices > close_i]
            nxt = above.min() if above.size else np.nan
        else:
            below = wall_prices[wall_prices < close_i]
            nxt = below.max() if below.size else np.nan
        if np.isfinite(nxt):
            dist_to_next_wall_atr = abs(nxt - close_i) / a15
        else:
            dist_to_next_wall_atr = np.nan

        # wall が close の上にあるか (resistance) 下か (support)
        wall_is_resistance = wall > close_i

        # ── forward-return (event bar の次 15m open 基準) ──
        entry = o[i + 1]
        rec = {
            "time": idx15[i],
            "session": session,
            "touch_count": float(touch_count),
            "dist_to_wall_atr": dist_to_wall_atr,
            "wick_ratio": wick_ratio,
            "close_position": close_position,
            "approach_velocity": approach_velocity,
            "h4_bias": h4_bias,
            "atr_regime": atr_regime,
            "dist_to_next_wall_atr": dist_to_next_wall_atr,
            "_wall_is_resistance": wall_is_resistance,
        }
        for hz in horizons:
            fut = c[i + 1 + hz]  # horizon 本後の close (entry から hz 本保有)
            raw = (fut - entry) / pip  # raw forward-return (上昇 +), pip
            rec[f"raw_{hz}"] = raw
            rec[f"abs_{hz}"] = abs(raw)
            # continuation: wall 方向への動き (breakout 仮説のターゲット)
            #   resistance → 上抜け continuation = +raw / support → 下抜け = -raw
            cont = raw if wall_is_resistance else -raw
            rec[f"cont_{hz}"] = cont
            # reversion: wall から跳ね返る動き (reversal 仮説のターゲット)
            #   resistance → 反落 = -raw / support → 反発 = +raw
            rec[f"rev_{hz}"] = -cont
        rows.append(rec)

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).set_index("time")


# ──────────────────────────────────────────────────────────────────────
# IC 計算 / 集計
# ──────────────────────────────────────────────────────────────────────
FEATURES = [
    "touch_count",
    "dist_to_wall_atr",
    "wick_ratio",
    "close_position",
    "approach_velocity",
    "h4_bias",
    "atr_regime",
    "dist_to_next_wall_atr",
]
TARGET_KINDS = ["raw", "abs", "cont", "rev"]


def spearman_ic(x: pd.Series, y: pd.Series) -> tuple[float, float, int]:
    """Spearman IC と両側 p 値、有効 N。NaN ペアは除外。"""
    m = x.notna() & y.notna()
    xn, yn = x[m], y[m]
    if len(xn) < 10 or xn.nunique() < 3:
        return np.nan, np.nan, int(m.sum())
    rho, p = stats.spearmanr(xn, yn)
    return float(rho), float(p), int(m.sum())


def quintile_means(x: pd.Series, y: pd.Series) -> Optional[tuple[float, float, bool]]:
    """特徴量の Q1(下位)/Q5(上位) quintile の y 平均と単調性フラグ。
    単調性: 5 quintile 平均が単調増 or 単調減なら True。
    """
    m = x.notna() & y.notna()
    xn, yn = x[m], y[m]
    if len(xn) < 50 or xn.nunique() < 5:
        return None
    try:
        q = pd.qcut(xn.rank(method="first"), 5, labels=False)
    except ValueError:
        return None
    means = yn.groupby(q).mean()
    if len(means) < 5:
        return None
    vals = means.to_numpy()
    mono = bool((np.diff(vals) > 0).all() or (np.diff(vals) < 0).all())
    return float(means.iloc[0]), float(means.iloc[-1]), mono


def run_pair(pair: str, horizons: list[int]) -> Optional[dict]:
    skips = SkipCounter()
    f15 = DATA_DIR / f"{pair}_15m.parquet"
    f4h = DATA_DIR / f"{pair}_4h.parquet"
    if not f15.exists() or not f4h.exists():
        print(f"[{pair}] データ欠損: {f15.name} or {f4h.name} 不在 — 除外")
        return None

    m15 = pd.read_parquet(f15)
    h4 = pd.read_parquet(f4h)

    # ── 共通窓に制限 ──
    m15 = m15[(m15.index >= WINDOW_START) & (m15.index <= WINDOW_END)]
    h4 = h4[(h4.index >= WINDOW_START) & (h4.index <= WINDOW_END)]
    if len(m15) < 1000 or len(h4) < 200:
        print(f"[{pair}] 共通窓内 N 不足 (15m={len(m15)}, 4h={len(h4)}) — 除外")
        return None

    # ── train slice (前半 60%, chronological) ──
    # 15m 側で 60% 時点の時刻を求め、両 TF をその時刻以前に制限。holdout は触らない。
    split_t = m15.index[int(len(m15) * TRAIN_FRAC)]
    m15_tr = m15[m15.index < split_t]
    h4_tr = h4[h4.index < split_t]
    print(f"[{pair}] train slice: {m15_tr.index.min()} -> {m15_tr.index.max()} "
          f"(15m={len(m15_tr)}, 4h={len(h4_tr)})  [holdout >= {split_t} 未使用]")

    ev = extract_events(pair, m15_tr, h4_tr, horizons, skips)
    n_ev = len(ev)
    return {"pair": pair, "events": ev, "n": n_ev, "skips": skips, "horizons": horizons}


def print_report(result: dict):
    pair = result["pair"]
    ev = result["events"]
    horizons = result["horizons"]
    n = result["n"]
    skips = result["skips"]

    n_tests = len(FEATURES) * len(TARGET_KINDS) * len(horizons)
    bonf_alpha = 0.05 / n_tests if n_tests else 1.0

    print("\n" + "=" * 78)
    print(f"# {pair} — Stage-1 IC 探索結果")
    print("=" * 78)
    print(f"イベント総数 N = {n}")
    print(f"検定数 = 特徴量{len(FEATURES)} × ターゲット{len(TARGET_KINDS)} × horizon{len(horizons)} = {n_tests}")
    print(f"Bonferroni 補正後 α = 0.05 / {n_tests} = {bonf_alpha:.5f}  (★ = p < この値)")

    if n < 30:
        print(f"\n⚠️ N={n} < 30 — IC 評価に不十分。スキップ理由:")
        print(skips.report())
        return

    # ── IC 表 ──
    for hz in horizons:
        print(f"\n── Spearman IC 表 (horizon = {hz} 本 = {hz*15/60:.1f}h) [|IC| 降順] ──")
        print(f"{'feature':<24}{'target':<7}{'IC':>9}{'p':>12}{'N':>8}  sig")
        ic_rows = []
        for feat in FEATURES:
            for tk in TARGET_KINDS:
                col = f"{tk}_{hz}"
                rho, p, nn = spearman_ic(ev[feat], ev[col])
                ic_rows.append((feat, tk, rho, p, nn))
        ic_rows.sort(key=lambda r: (-abs(r[2]) if np.isfinite(r[2]) else 0))
        for feat, tk, rho, p, nn in ic_rows:
            if not np.isfinite(rho):
                print(f"{feat:<24}{tk:<7}{'n/a':>9}{'n/a':>12}{nn:>8}  -")
                continue
            star = "★" if (np.isfinite(p) and p < bonf_alpha) else ("·" if p < 0.05 else "")
            print(f"{feat:<24}{tk:<7}{rho:>9.4f}{p:>12.2e}{nn:>8}  {star}")

    # ── quintile 単調性 (continuation / reversion, 各 horizon) ──
    for hz in horizons:
        print(f"\n── Quintile 平均 forward-return (horizon {hz}) [Q1 下位 / Q5 上位, pip] ──")
        print(f"{'feature':<24}{'target':<6}{'Q1':>10}{'Q5':>10}{'Q5-Q1':>10}  mono")
        for feat in FEATURES:
            for tk in ["cont", "rev"]:
                col = f"{tk}_{hz}"
                qm = quintile_means(ev[feat], ev[col])
                if qm is None:
                    print(f"{feat:<24}{tk:<6}{'n/a':>10}{'n/a':>10}{'n/a':>10}  -")
                    continue
                q1, q5, mono = qm
                flag = "MONO" if mono else ""
                print(f"{feat:<24}{tk:<6}{q1:>10.2f}{q5:>10.2f}{q5-q1:>10.2f}  {flag}")

    # ── session 別 IC (category, raw のみ参考) ──
    print(f"\n── Session 別 平均 continuation/reversion (horizon {horizons[0]}, pip) ──")
    g = ev.groupby("session")
    print(f"{'session':<10}{'N':>7}{'cont_mean':>12}{'rev_mean':>12}{'raw_mean':>12}")
    for sess, sub in g:
        col_c = f"cont_{horizons[0]}"
        col_r = f"rev_{horizons[0]}"
        col_raw = f"raw_{horizons[0]}"
        print(f"{sess:<10}{len(sub):>7}{sub[col_c].mean():>12.2f}{sub[col_r].mean():>12.2f}{sub[col_raw].mean():>12.2f}")

    # ── skip 集計 ──
    print(f"\n── Skip / NaN カウント ({pair}) ──")
    print(skips.report())

    # ── NaN feature カウント ──
    print(f"\n── 特徴量 NaN 件数 (イベント内) ──")
    for feat in FEATURES:
        na = int(ev[feat].isna().sum())
        if na:
            print(f"  - {feat}: {na} / {n}")


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Stage-1 H4-level IC explorer")
    ap.add_argument("--pair", default="EUR_USD", help="comma 区切りで複数可")
    ap.add_argument("--horizon", default="12,48", help="forward horizon 本数 (comma 区切り)")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    pairs = [p.strip() for p in args.pair.split(",") if p.strip()]
    horizons = [int(h) for h in args.horizon.split(",") if h.strip()]
    if not horizons:
        print("horizon 指定なし — 中断", file=sys.stderr)
        return 2

    print(f"Stage-1 IC 探索  pairs={pairs}  horizons={horizons}")
    print(f"共通窓 {WINDOW_START.date()}〜{WINDOW_END.date()}, train={TRAIN_FRAC:.0%} (前半のみ)")
    print(f"凍結param: fractal_n={FRACTAL_N} lookback_h4={LOOKBACK_H4} "
          f"kde_tol={KDE_TOL_MULT}xATR min_touches={MIN_TOUCHES} "
          f"interact_tol={INTERACT_TOL_MULT}xATR15")

    any_ok = False
    for pair in pairs:
        res = run_pair(pair, horizons)
        if res is None:
            continue
        any_ok = True
        print_report(res)

    if not any_ok:
        print("有効ペアなし", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
