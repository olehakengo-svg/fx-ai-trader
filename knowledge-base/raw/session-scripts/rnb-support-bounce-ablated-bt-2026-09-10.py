#!/usr/bin/env python3
"""rnb_support_bounce BE/Trail-ablated closed-bar BT (2026-09-10, rule:R3 — R1 パケット evidence).

再現手順: リポジトリルートで `python3 knowledge-base/raw/session-scripts/rnb-support-bounce-ablated-bt-2026-09-10.py`
(data/cache/massive/USD_JPY_15m.parquet が必要 — gitignore 対象、MASSIVE 由来)

Estimand (パケット §BT evidence と同一):
  - PRODUCTION signal fn app.compute_rnb_signal を各**確定足**で評価 (backtest_mode=True)
  - 固定 TP=20p / SL=15p、MAX_HOLD = 8 x 15m bars (7200s = MODE_CONFIG MAX_HOLD_SEC)
  - BE/Trail なし (MEMORY project_be_trail_inflates_python_bt_wr: +20pp 水増しの ablation)
  - 同時 1 ポジション (live _mode_limits: daytrade-class = 1)
  - 同一バーで SL/TP 両接触 → SL 扱い (悲観側)
  - friction: USD_JPY RT 2.14p (wiki/analyses/friction-analysis.md)
  - ATR は live 慣行と同一 (ta.volatility.AverageTrueRange window=14, modules/indicators.py)

⚠️ この BT は closed-bar estimand。live は 30 秒ごと forming-bar 評価
(MEMORY project_ps_capture_estimand_disjoint_2026_09_09) — BT EV を live 期待値に使わない。
"""
import os, sys, math, json
import pandas as pd
import numpy as np

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, _REPO)

PARQUET = os.path.join(_REPO, "data", "cache", "massive", "USD_JPY_15m.parquet")
PIP = 0.01
TP_PIPS, SL_PIPS = 20.0, 15.0
MAX_HOLD_BARS = 8          # 7200s / 900s
FRICTION_RT = 2.14         # pips round trip
WARMUP = 40


def wilson_lo(w, n, z=1.96):
    if n == 0:
        return 0.0
    p = w / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return max(0.0, (centre - spread) / denom)


def run_window(df, label):
    from app import compute_rnb_signal
    n = len(df)
    closes = df["Close"].values
    highs = df["High"].values
    lows = df["Low"].values

    signals, trades = [], []
    open_until = -1
    i = WARMUP
    while i < n:
        window = df.iloc[max(0, i - 34):i + 1]
        sig = compute_rnb_signal(window, tf="15m", symbol="USDJPY=X", backtest_mode=True)
        if sig["signal"] == "BUY":
            signals.append(i)
            if i > open_until and i + 1 < n:
                entry = closes[i]
                tp = entry + TP_PIPS * PIP
                sl = entry - SL_PIPS * PIP
                outcome, pnl, exit_i, ambiguous = None, None, None, False
                last_j = min(i + MAX_HOLD_BARS, n - 1)
                for j in range(i + 1, last_j + 1):
                    hit_sl = lows[j] <= sl
                    hit_tp = highs[j] >= tp
                    if hit_sl and hit_tp:
                        outcome, pnl, exit_i, ambiguous = "SL_AMBIG", -SL_PIPS, j, True
                        break
                    if hit_sl:
                        outcome, pnl, exit_i = "SL", -SL_PIPS, j
                        break
                    if hit_tp:
                        outcome, pnl, exit_i = "TP", TP_PIPS, j
                        break
                if outcome is None:
                    exit_i = last_j
                    pnl = (closes[exit_i] - entry) / PIP
                    outcome = "TIMEOUT"
                trades.append({"t": str(df.index[i]), "outcome": outcome, "pnl": pnl,
                               "ambiguous": ambiguous, "hold_bars": exit_i - i})
                open_until = exit_i
        i += 1

    N = len(trades)
    pnls = np.array([t["pnl"] for t in trades]) if N else np.array([])
    wins = int((pnls > 0).sum()) if N else 0
    net = pnls - FRICTION_RT
    gp = float(pnls[pnls > 0].sum()) if N else 0.0
    gl = float(-pnls[pnls < 0].sum()) if N else 0.0
    weeks = (df.index[-1] - df.index[0]).days / 7.0
    return {
        "label": label, "bars": n, "raw_signals": len(signals), "N_trades": N,
        "signals_per_week": round(len(signals) / weeks, 3),
        "trades_per_week": round(N / weeks, 3),
        "WR": round(wins / N, 4) if N else None,
        "wilson_lo_95": round(wilson_lo(wins, N), 4) if N else None,
        "gross_EV_pips": round(float(pnls.mean()), 3) if N else 0.0,
        "net_EV_pips_f2.14": round(float(net.mean()), 3) if N else 0.0,
        "net_total_pips": round(float(net.sum()), 1) if N else 0.0,
        "PF_gross": round(gp / gl, 3) if gl > 0 else None,
        "outcomes": {k: sum(1 for t in trades if t["outcome"] == k)
                     for k in ("TP", "SL", "SL_AMBIG", "TIMEOUT")},
        "BEV_WR_friction": round((SL_PIPS + FRICTION_RT) / (TP_PIPS + SL_PIPS), 4),
    }, trades


def main():
    df = pd.read_parquet(PARQUET)
    df = df[~df.index.duplicated(keep="first")].sort_index()
    from ta.volatility import AverageTrueRange
    df["atr"] = AverageTrueRange(df["High"], df["Low"], df["Close"], window=14).average_true_range()

    end = df.index[-1]
    for label, days in (("365d", 365), ("730d", 730), ("90d", 90)):
        w = df[df.index >= end - pd.Timedelta(days=days)].copy()
        res, trades = run_window(w, label)
        print(json.dumps(res, ensure_ascii=False, indent=1))
        if label == "365d":
            monthly = {}
            for t in trades:
                monthly.setdefault(t["t"][:7], []).append(t["pnl"] - FRICTION_RT)
            print("monthly net pnl (pips):")
            for m in sorted(monthly):
                print(f"  {m}: N={len(monthly[m]):3d} net={sum(monthly[m]):+8.1f}")


if __name__ == "__main__":
    main()
