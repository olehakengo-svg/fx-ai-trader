#!/usr/bin/env python3
"""
channel_edge_ic_explore.py — チャネル(平行線/回帰)の Stage-1 IC 探索

目的:
  本番ページが描く「平行線(チャネル)」— 回帰チャネル(±2σ) と swing高安fit平行
  チャネル — が forward-return を方向予測するか (Spearman IC) を causal に測る。
  主役特徴 `*_dev_sigma` (符号付き偏差; +上限側/−下限側) の IC 符号で機構を判別:
    IC < 0 有意 → 平均回帰(境界で反発)   IC > 0 有意 → ブレイクアウト/継続
    IC ≈ 0      → 方向エッジ無し (H4 水平線 falsification と同じ結論)
  これは BT ではなく「エッジが存在するか」の安価な棄却テスト。
  設計同型: tools/zigzag_swing_ic_explore.py / tools/h4_level_edge_explore.py

絶対規律 (流用元と同一):
  1. 因果性: いかなる特徴量も未来 bar を参照しない。回帰チャネルは close[i-L+1:i+1]
     のみ。平行チャネルは Williams Fractal(n) で confirm 済み swing (confirm_idx<=i) のみ。
  2. train スライスのみ探索 (前半 60%)、holdout 不可触。
  3. 閾値最適化禁止。IC は連続特徴量と forward-return の Spearman 相関のみ。
  4. silent except 禁止。skip は理由を count。

事前登録 falsification 基準 (cross-pair summary で判定):
  ある (feature × target × horizon) が
    |IC| >= 0.05 かつ p < Bonferroni(0.05/n_tests) かつ 6ペア中 >=4 ペアで同符号
  を満たして初めて「生存」。満たさなければ falsify 確定・実装せず。

CLI:
  python3 tools/channel_edge_ic_explore.py --pair EUR_USD --horizon 4,12,48
  python3 tools/channel_edge_ic_explore.py \
      --pair EUR_USD,GBP_USD,USD_JPY,AUD_USD,USD_CAD,EUR_JPY --horizon 4,12,48

モジュールトップで副作用禁止 (os.environ / chdir / parse_args / Thread を import 時に実行しない)。
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "cache" / "massive"

# zigzag_swing_ic_explore と同窓に揃え比較可能に
WINDOW_START = pd.Timestamp("2022-01-01", tz="UTC")
WINDOW_END = pd.Timestamp("2026-05-15", tz="UTC")
TRAIN_FRAC = 0.60

FRACTAL_N = 2          # Williams Fractal: center±n。確定は center+n 本後。
ATR_PERIOD = 14
MAX_LOOKBACK_SWINGS = 8   # 平行チャネル fit に使う直近確定 swing 本数
REG_LOOKBACK = 50         # 回帰チャネルの窓 (get_regression_channel 既定と同じ)

DEFAULT_PAIRS = "EUR_USD,GBP_USD,USD_JPY,AUD_USD,USD_CAD,EUR_JPY"


def _pip_size(pair: str) -> float:
    return 0.01 if pair.endswith("_JPY") else 0.0001


def _session_label(h: int) -> str:
    if h < 7:
        return "Tokyo"
    if h < 13:
        return "London"
    if h < 22:
        return "NY"
    return "Off"


def _atr(df: pd.DataFrame, period: int = ATR_PERIOD) -> pd.Series:
    high, low, close = df["High"], df["Low"], df["Close"]
    prev = close.shift(1)
    tr = pd.concat([(high - low), (high - prev).abs(), (low - prev).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False).mean()


@dataclass
class Swing:
    confirm_idx: int    # この bar index の close から利用可能 (= center+n)
    price: float
    kind: str           # "high" / "low"
    center_idx: int     # pivot 本体の index (傾き fit の x に使う)


def detect_swings(high: np.ndarray, low: np.ndarray, n: int = FRACTAL_N) -> list[Swing]:
    """Williams Fractal n で swing high/low を検出。確定は center+n 本後。"""
    out: list[Swing] = []
    m = len(high)
    for i in range(n, m - n):
        wh = high[i - n: i + n + 1]
        wl = low[i - n: i + n + 1]
        c = n
        if high[i] == wh.max() and (high[i] > np.delete(wh, c)).all():
            out.append(Swing(confirm_idx=i + n, price=float(high[i]), kind="high", center_idx=i))
        if low[i] == wl.min() and (low[i] < np.delete(wl, c)).all():
            out.append(Swing(confirm_idx=i + n, price=float(low[i]), kind="low", center_idx=i))
    out.sort(key=lambda s: s.confirm_idx)
    return out


@dataclass
class SkipCounter:
    counts: Counter = field(default_factory=Counter)

    def add(self, reason: str, k: int = 1):
        self.counts[reason] += k

    def report(self) -> str:
        if not self.counts:
            return "  (skip 0 件)"
        return "\n".join(f"  - {r}: {n}" for r, n in self.counts.most_common())


# チャネル特徴量 (reg=回帰チャネル, par=swing高安平行チャネル)
FEATURES = [
    "reg_dev_sigma",      # 符号付き偏差 cur_dev/σ (+上限側/−下限側) ★主役
    "reg_pos",            # チャネル内位置 [0,1] (0=−2σ,1=+2σ)
    "reg_slope_atr",      # 回帰傾き/bar / ATR (トレンド方向・強度)
    "reg_width_atr",      # 4σ 幅 / ATR (レンジ規模 regime)
    "par_dev_sigma",      # 平行チャネル中央からの符号付き偏差 (+上限/−下限, mid基準で±1=境界)
    "par_pos",            # 平行チャネル内位置 [0,1]
    "par_slope_atr",      # 平行チャネル傾き/bar / ATR
    "par_width_atr",      # 平行チャネル幅 / ATR
]
TARGET_KINDS = ["raw", "abs"]   # raw=符号付き forward return(pip), abs=|return|(ボラ予測)


def _reg_channel(closes: np.ndarray):
    """close[...:i+1] (末尾が評価 bar) の線形回帰チャネル。Returns dict or None."""
    L = len(closes)
    if L < 10:
        return None
    x = np.arange(L)
    m, b = np.polyfit(x, closes, 1)
    mid = m * x + b
    resid = closes - mid
    std = float(np.std(resid))
    if std < 1e-12:
        return None
    cur_dev = float(resid[-1])
    dev_sigma = cur_dev / std
    pos = float(np.clip((dev_sigma + 2.0) / 4.0, 0.0, 1.0))
    return {"dev_sigma": dev_sigma, "pos": pos, "slope": float(m), "width": 4.0 * std}


def _par_channel(known, i: int):
    """確定 swing high/low に上下平行線を fit し評価 bar i での値を返す。"""
    highs = [s for s in known if s.kind == "high"]
    lows = [s for s in known if s.kind == "low"]
    if len(highs) < 2 or len(lows) < 2:
        return None
    hx = np.array([s.center_idx for s in highs], dtype=float)
    hy = np.array([s.price for s in highs], dtype=float)
    lx = np.array([s.center_idx for s in lows], dtype=float)
    ly = np.array([s.price for s in lows], dtype=float)
    hm, hb = np.polyfit(hx, hy, 1)
    lm, lb = np.polyfit(lx, ly, 1)
    upper = hm * i + hb
    lower = lm * i + lb
    width = upper - lower
    if width <= 0:
        return None
    slope = (hm + lm) / 2.0
    return {"upper": float(upper), "lower": float(lower),
            "width": float(width), "slope": float(slope)}


def extract(pair: str, m15: pd.DataFrame, horizons: list[int], skips: SkipCounter) -> pd.DataFrame:
    pip = _pip_size(pair)
    m15 = m15.copy()
    m15["atr"] = _atr(m15)
    high = m15["High"].to_numpy()
    low = m15["Low"].to_numpy()
    close = m15["Close"].to_numpy()
    atrv = m15["atr"].to_numpy()
    idx = m15.index
    n = len(m15)

    swings = detect_swings(high, low, FRACTAL_N)
    confirm_arr = np.array([s.confirm_idx for s in swings])

    max_h = max(horizons)
    start = max(ATR_PERIOD + FRACTAL_N + 2, REG_LOOKBACK)
    rows = []
    for i in range(start, n - max_h - 1):
        a = atrv[i]
        if not np.isfinite(a) or a <= 0:
            skips.add("atr invalid")
            continue

        # --- 回帰チャネル (因果: close[i-L+1:i+1]) ---
        reg = _reg_channel(close[i - REG_LOOKBACK + 1: i + 1])
        if reg is None:
            skips.add("reg channel degenerate")
            continue

        # --- 平行チャネル (因果: confirm 済み swing のみ) ---
        k = np.searchsorted(confirm_arr, i, side="right")
        if k < 4:
            skips.add("swing history insufficient")
            continue
        known = swings[max(0, k - MAX_LOOKBACK_SWINGS): k]
        par = _par_channel(known, i)
        if par is None:
            skips.add("par channel needs 2 highs + 2 lows")
            continue

        c = close[i]
        par_mid = (par["upper"] + par["lower"]) / 2.0
        par_dev_sigma = (c - par_mid) / (par["width"] / 2.0)   # ±1 = 境界
        par_pos = (c - par["lower"]) / par["width"]

        rec = {
            "time": idx[i],
            "session": _session_label(idx[i].hour),
            "reg_dev_sigma": reg["dev_sigma"],
            "reg_pos": reg["pos"],
            "reg_slope_atr": reg["slope"] / a,
            "reg_width_atr": reg["width"] / a,
            "par_dev_sigma": float(par_dev_sigma),
            "par_pos": float(par_pos),
            "par_slope_atr": par["slope"] / a,
            "par_width_atr": par["width"] / a,
        }
        for hz in horizons:
            raw = (close[i + hz] - c) / pip
            rec[f"raw_{hz}"] = raw
            rec[f"abs_{hz}"] = abs(raw)
        rows.append(rec)

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).set_index("time")


def spearman_ic(x: pd.Series, y: pd.Series) -> tuple[float, float, int]:
    m = x.notna() & y.notna()
    xn, yn = x[m], y[m]
    if len(xn) < 10 or xn.nunique() < 3:
        return np.nan, np.nan, int(m.sum())
    rho, p = stats.spearmanr(xn, yn)
    return float(rho), float(p), int(m.sum())


def _n_tests(horizons: list[int]) -> int:
    return len(FEATURES) * len(TARGET_KINDS) * len(horizons)


def print_report(pair: str, ev: pd.DataFrame, horizons: list[int], skips: SkipCounter,
                 collect: dict):
    n = len(ev)
    n_tests = _n_tests(horizons)
    bonf = 0.05 / n_tests if n_tests else 1.0
    print("\n" + "=" * 78)
    print(f"# {pair} — チャネル(平行線/回帰) Stage-1 IC")
    print("=" * 78)
    print(f"イベント N = {n}  検定数 = {n_tests}  Bonferroni α = {bonf:.5f} (★=p<α, ·=p<0.05)")
    if n < 30:
        print(f"⚠️ N={n} < 30 — 不十分。skip:")
        print(skips.report())
        return

    for hz in horizons:
        print(f"\n── Spearman IC (horizon {hz}本 = {hz*15/60:.1f}h) [|IC|降順] ──")
        print(f"{'feature':<18}{'target':<8}{'IC':>9}{'p':>12}{'N':>8}  sig")
        rows = []
        for f in FEATURES:
            for tk in TARGET_KINDS:
                rho, p, nn = spearman_ic(ev[f], ev[f"{tk}_{hz}"])
                rows.append((f, tk, rho, p, nn))
                # cross-pair 集計用
                if np.isfinite(rho):
                    collect[(f, tk, hz)].append((pair, rho, p, bonf))
        rows.sort(key=lambda r: (-abs(r[2]) if np.isfinite(r[2]) else 0))
        for f, tk, rho, p, nn in rows:
            if not np.isfinite(rho):
                print(f"{f:<18}{tk:<8}{'n/a':>9}{'n/a':>12}{nn:>8}  -")
                continue
            star = "★" if (np.isfinite(p) and p < bonf) else ("·" if p < 0.05 else "")
            print(f"{f:<18}{tk:<8}{rho:>9.4f}{p:>12.2e}{nn:>8}  {star}")

    print(f"\n── skip ──")
    print(skips.report())


def print_cross_pair(collect: dict, n_pairs: int):
    """事前登録 falsification 基準で生存する組合せを判定。"""
    print("\n" + "#" * 78)
    print("# CROSS-PAIR 再現性 — falsification 判定")
    print(f"# 基準: |IC|>=0.05 かつ p<Bonferroni かつ {n_pairs}ペア中 >=4 ペアで同符号")
    print("#" * 78)
    survivors = []
    print(f"\n{'feature':<18}{'target':<7}{'hz':>4}{'meanIC':>9}"
          f"{'+/-':>7}{'≥.05&★':>8}  verdict")
    for key in sorted(collect.keys(), key=lambda k: (k[2], k[0], k[1])):
        f, tk, hz = key
        recs = collect[key]
        ics = [r[1] for r in recs]
        mean_ic = float(np.mean(ics))
        n_pos = sum(1 for v in ics if v > 0)
        n_neg = sum(1 for v in ics if v < 0)
        # |IC|>=0.05 かつ p<bonf を満たすペア数 (符号別)
        strong_pos = sum(1 for (_, rho, p, bonf) in recs if rho >= 0.05 and p < bonf)
        strong_neg = sum(1 for (_, rho, p, bonf) in recs if rho <= -0.05 and p < bonf)
        strong = max(strong_pos, strong_neg)
        dom_sign = max(n_pos, n_neg)
        survive = strong >= 4 and dom_sign >= 4
        verdict = "✅生存" if survive else "✗null"
        if survive:
            if tk == "abs":
                mech = "vol-predict(方向中立)"
            elif mean_ic < 0:
                mech = "mean-revert"
            else:
                mech = "breakout/継続"
            survivors.append((key, mean_ic, mech))
        print(f"{f:<18}{tk:<7}{hz:>4}{mean_ic:>9.4f}"
              f"{f'{n_pos}/{n_neg}':>7}{strong:>8}  {verdict}")
    print("\n" + "-" * 60)
    if survivors:
        print(f"✅ 生存 {len(survivors)} 組合せ — 次段 (TV Pine canon) へ:")
        for key, mic, mech in survivors:
            print(f"   {key}  meanIC={mic:+.4f}  {mech}")
    else:
        print("✗ 生存ゼロ — チャネル方向エッジ falsify 確定。実装せず。")
        print("  (H4 水平線 falsification と同じ結論。decision doc へ記録。)")


def run_pair(pair: str, horizons: list[int], collect: dict) -> int:
    skips = SkipCounter()
    f15 = DATA_DIR / f"{pair}_15m.parquet"
    if not f15.exists():
        print(f"[{pair}] {f15.name} 不在 — 中断", file=sys.stderr)
        return 1
    m15 = pd.read_parquet(f15)
    if m15.index.tz is None:
        m15.index = m15.index.tz_localize("UTC")
    m15 = m15[(m15.index >= WINDOW_START) & (m15.index <= WINDOW_END)]
    if len(m15) < 2000:
        print(f"[{pair}] N不足 (15m={len(m15)})", file=sys.stderr)
        return 1

    split_t = m15.index[int(len(m15) * TRAIN_FRAC)]
    m15_tr = m15[m15.index < split_t]
    print(f"[{pair}] train: {m15_tr.index.min().date()}〜{m15_tr.index.max().date()} "
          f"(15m={len(m15_tr)})  [holdout >= {split_t.date()} 未使用]")
    print(f"凍結param: fractal_n={FRACTAL_N} lookback_swings={MAX_LOOKBACK_SWINGS} "
          f"reg_lookback={REG_LOOKBACK}")

    ev = extract(pair, m15_tr, horizons, skips)
    print_report(pair, ev, horizons, skips, collect)
    return 0


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="チャネル(平行線/回帰) Stage-1 IC")
    ap.add_argument("--pair", default=DEFAULT_PAIRS)
    ap.add_argument("--horizon", default="4,12,48")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    pairs = [p.strip() for p in args.pair.split(",") if p.strip()]
    horizons = [int(h) for h in args.horizon.split(",") if h.strip()]
    print(f"CHANNEL IC  pairs={pairs}  horizons={horizons}")
    print(f"共通窓 {WINDOW_START.date()}〜{WINDOW_END.date()}, train={TRAIN_FRAC:.0%}")
    collect: dict = defaultdict(list)
    ok_pairs = 0
    for p in pairs:
        if run_pair(p, horizons, collect) == 0:
            ok_pairs += 1
    if ok_pairs:
        print_cross_pair(collect, ok_pairs)
    return 0 if ok_pairs else 1


if __name__ == "__main__":
    sys.exit(main())
