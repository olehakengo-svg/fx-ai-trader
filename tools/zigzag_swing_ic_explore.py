#!/usr/bin/env python3
"""
zigzag_swing_ic_explore.py — ZIGZAG (swing構造) の Stage-1 IC 探索

目的:
  「ATR+RSI+MACD+EMA+ZIGZAG を組み合わせれば最強」という発想に対し、
  ZIGZAG (= swing/pivot 構造) を戦略に組み込む前に、その構造特徴量が
  forward-return を予測するか (Spearman IC) を causal に測る。
  予測力ゼロなら組み込み不要 (安価な棄却)。これは BT ではなく IC 探索。

絶対規律 (h4_level_edge_explore.py 準拠):
  1. 因果性: ZIGZAG swing は Williams Fractal(n) で center+n 本後に確定。
     repaint 回避のため、評価 bar の時点で「確定済み」swing のみ使う。未来 bar 参照禁止。
  2. train スライスのみ探索 (前半 60%)、holdout 不可触。
  3. 閾値最適化禁止。IC は連続特徴量と forward-return の Spearman 相関のみ。
  4. silent except 禁止。skip は理由を count。

CLI:
  python3 tools/zigzag_swing_ic_explore.py --pair EUR_USD --horizon 12,48

モジュールトップで副作用禁止。
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "cache" / "massive"

# mtf_regime_switch_explore と同窓に揃え比較可能に (4h整合は不要だが期間を統一)
WINDOW_START = pd.Timestamp("2022-01-01", tz="UTC")
WINDOW_END = pd.Timestamp("2026-05-15", tz="UTC")
TRAIN_FRAC = 0.60

FRACTAL_N = 2      # Williams Fractal: center±n。確定は center+n 本後。
ATR_PERIOD = 14
MAX_LOOKBACK_SWINGS = 8  # 直近この本数の確定 swing から構造を読む


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


def detect_swings(high: np.ndarray, low: np.ndarray, n: int = FRACTAL_N) -> list[Swing]:
    """Williams Fractal n で swing high/low を検出。確定は center+n 本後。"""
    out: list[Swing] = []
    m = len(high)
    for i in range(n, m - n):
        wh = high[i - n: i + n + 1]
        wl = low[i - n: i + n + 1]
        c = n
        if high[i] == wh.max() and (high[i] > np.delete(wh, c)).all():
            out.append(Swing(confirm_idx=i + n, price=float(high[i]), kind="high"))
        if low[i] == wl.min() and (low[i] < np.delete(wl, c)).all():
            out.append(Swing(confirm_idx=i + n, price=float(low[i]), kind="low"))
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


# ZIGZAG/swing 構造の特徴量
FEATURES = [
    "swing_trend",      # 直近 HH/HL(+) vs LH/LL(-) 構造スコア {-2..+2}
    "swing_pos",        # 直近 swing-low〜swing-high レンジ内 close 位置 [0,1]
    "leg_atr",          # 直近確定 swing からの距離 / ATR (どれだけ走ったか, 符号付き)
    "swing_amp_atr",    # 直近 swing high-low 振幅 / ATR (レンジ規模)
    "bars_since_swing", # 直近 swing 確定からの経過 bar (新鮮さ)
]
TARGET_KINDS = ["raw", "abs", "struct"]  # struct = raw * sign(swing_trend): 構造方向への継続


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
    rows = []
    for i in range(ATR_PERIOD + FRACTAL_N + 2, n - max_h - 1):
        a = atrv[i]
        if not np.isfinite(a) or a <= 0:
            skips.add("atr invalid")
            continue
        # 確定済み swing (confirm_idx <= i)
        k = np.searchsorted(confirm_arr, i, side="right")
        if k < 4:
            skips.add("swing history insufficient")
            continue
        known = swings[max(0, k - MAX_LOOKBACK_SWINGS): k]
        highs = [s for s in known if s.kind == "high"]
        lows = [s for s in known if s.kind == "low"]
        if len(highs) < 2 or len(lows) < 2:
            skips.add("need 2 highs + 2 lows")
            continue

        # 構造スコア: 直近2 swing high の HH(+1)/LH(-1), 直近2 swing low の HL(+1)/LL(-1)
        hh = 1 if highs[-1].price > highs[-2].price else -1
        hl = 1 if lows[-1].price > lows[-2].price else -1
        swing_trend = float(hh + hl)  # {-2, 0, +2}

        last_high = highs[-1].price
        last_low = lows[-1].price
        rng = last_high - last_low
        if rng <= 0:
            skips.add("degenerate range")
            continue
        swing_pos = (close[i] - last_low) / rng  # [0,1] 近辺

        # 直近確定 swing (high/low 問わず最後に確定したもの) からの距離・経過
        last_swing = known[-1]
        leg_atr = (close[i] - last_swing.price) / a
        bars_since_swing = float(i - last_swing.confirm_idx)
        swing_amp_atr = rng / a

        rec = {
            "time": idx[i],
            "session": _session_label(idx[i].hour),
            "swing_trend": swing_trend,
            "swing_pos": swing_pos,
            "leg_atr": leg_atr,
            "swing_amp_atr": swing_amp_atr,
            "bars_since_swing": bars_since_swing,
        }
        sgn = np.sign(swing_trend) if swing_trend != 0 else 0.0
        for hz in horizons:
            raw = (close[i + hz] - close[i]) / pip
            rec[f"raw_{hz}"] = raw
            rec[f"abs_{hz}"] = abs(raw)
            rec[f"struct_{hz}"] = raw * sgn  # 構造方向への継続 (>0 なら構造が当たった)
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


def print_report(pair: str, ev: pd.DataFrame, horizons: list[int], skips: SkipCounter):
    n = len(ev)
    n_tests = len(FEATURES) * len(TARGET_KINDS) * len(horizons)
    bonf = 0.05 / n_tests if n_tests else 1.0
    print("\n" + "=" * 78)
    print(f"# {pair} — ZIGZAG swing 構造 Stage-1 IC")
    print("=" * 78)
    print(f"イベント N = {n}  検定数 = {n_tests}  Bonferroni α = {bonf:.5f} (★=p<α, ·=p<0.05)")
    if n < 30:
        print(f"⚠️ N={n} < 30 — 不十分。skip:")
        print(skips.report())
        return

    for hz in horizons:
        print(f"\n── Spearman IC (horizon {hz}本 = {hz*15/60:.1f}h) [|IC|降順] ──")
        print(f"{'feature':<20}{'target':<8}{'IC':>9}{'p':>12}{'N':>8}  sig")
        rows = []
        for f in FEATURES:
            for tk in TARGET_KINDS:
                rho, p, nn = spearman_ic(ev[f], ev[f"{tk}_{hz}"])
                rows.append((f, tk, rho, p, nn))
        rows.sort(key=lambda r: (-abs(r[2]) if np.isfinite(r[2]) else 0))
        for f, tk, rho, p, nn in rows:
            if not np.isfinite(rho):
                print(f"{f:<20}{tk:<8}{'n/a':>9}{'n/a':>12}{nn:>8}  -")
                continue
            star = "★" if (np.isfinite(p) and p < bonf) else ("·" if p < 0.05 else "")
            print(f"{f:<20}{tk:<8}{rho:>9.4f}{p:>12.2e}{nn:>8}  {star}")

    # swing_trend カテゴリ別 struct 平均 (構造がトレンド継続を予測するか直接確認)
    print(f"\n── swing_trend カテゴリ × forward-return (horizon {horizons[0]}, pip) ──")
    print(f"{'swing_trend':<14}{'N':>7}{'raw_mean':>12}{'struct_mean':>13}")
    for st in sorted(ev["swing_trend"].unique()):
        sub = ev[ev["swing_trend"] == st]
        print(f"{st:<14.0f}{len(sub):>7}{sub[f'raw_{horizons[0]}'].mean():>12.3f}{sub[f'struct_{horizons[0]}'].mean():>13.3f}")

    print(f"\n── skip ──")
    print(skips.report())


def run_pair(pair: str, horizons: list[int]) -> int:
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
    print(f"凍結param: fractal_n={FRACTAL_N} lookback_swings={MAX_LOOKBACK_SWINGS}")

    ev = extract(pair, m15_tr, horizons, skips)
    print_report(pair, ev, horizons, skips)
    return 0


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="ZIGZAG swing 構造 Stage-1 IC")
    ap.add_argument("--pair", default="EUR_USD")
    ap.add_argument("--horizon", default="12,48")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    pairs = [p.strip() for p in args.pair.split(",") if p.strip()]
    horizons = [int(h) for h in args.horizon.split(",") if h.strip()]
    print(f"ZIGZAG swing IC  pairs={pairs}  horizons={horizons}")
    print(f"共通窓 {WINDOW_START.date()}〜{WINDOW_END.date()}, train={TRAIN_FRAC:.0%}")
    ok = False
    for p in pairs:
        if run_pair(p, horizons) == 0:
            ok = True
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
