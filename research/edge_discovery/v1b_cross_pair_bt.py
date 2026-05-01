"""v1b cross-pair generalization BT — EUR_USD / GBP_USD への横展開検証

Objective:
  v1b ma_trend_perfect が USD_JPY 特化 overfit なのか structural edge なのか
  を検証。LOCK 期間中だが BT 結果のみ生成、コードは変更しない (monkey-patch
  with original restored on exit)。

Pair-specific spreads (USD_JPY=0.8 baseline, others scaled):
  - USD_JPY: 0.8 pip (production)
  - EUR_USD: 0.5 pip (typical OANDA spread)
  - GBP_USD: 0.7 pip (typical OANDA spread)

Output: per-pair × session promotion CSV、cross-pair comparison summary
"""
from __future__ import annotations
import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd

os.environ.setdefault("BT_MODE", "1")
os.environ.setdefault("NO_AUTOSTART", "1")

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


PAIRS_AND_SPREADS = [
    ("USD_JPY", 0.8),
    ("EUR_USD", 0.5),
    ("GBP_USD", 0.7),
]


def run_pair(pair: str, spread: float, days: int, output_dir: Path) -> dict:
    """Run v1b BT for one pair with monkey-patched _ALLOWED_PAIRS."""
    # Monkey-patch to allow this pair (restored at end of function)
    from strategies.scalp import ma_trend_perfect as mtp
    original_pairs = mtp._ALLOWED_PAIRS
    mtp._ALLOWED_PAIRS = {pair}

    try:
        from modules.bt_vec_harness import VecBacktestRunner, HtfFeatureSpec
        from strategies.scalp.ma_trend_perfect import MaTrendPerfect

        spec = HtfFeatureSpec(
            m15_fields=["close", "ema9", "ema21", "ema50", "adx", "ema_slope", "atr"],
            m5_fields=[
                "close", "prev_close", "prev_high", "prev_low",
                "ema9", "ema21", "sma21",
                "bbpb", "rsi14", "stoch_k", "stoch_d",
                "swing_high", "swing_low", "atr",
            ],
            include_h1=True,
            h1_fields=["close", "ema9", "ema21", "ema50", "ema200", "adx"],
            inject_spread=spread,
        )
        runner = VecBacktestRunner(spec=spec, strategy_factory=MaTrendPerfect)
        t0 = time.perf_counter()
        result = runner.run(symbol=pair, days=days, verbose=False)
        elapsed = time.perf_counter() - t0
        return {
            "pair": pair, "spread_pip": spread, "days": days,
            "elapsed_sec": round(elapsed, 1),
            **{k: result.get(k) for k in [
                "n_evaluated", "n_trades", "n_wins", "n_losses",
                "wr_pct", "wilson_lower_pct", "ev_pips", "pf",
                "kelly_pct", "avg_win_pips", "avg_loss_pips"
            ]},
            "trades_full": result.get("trades_full") or [],
        }
    finally:
        mtp._ALLOWED_PAIRS = original_pairs


def session_of_hour(h: int) -> str:
    if 0 <= h < 7: return "Tokyo"
    if 7 <= h < 13: return "London"
    if 13 <= h < 21: return "NY"
    return "Off"


def cell_breakdown(trades: list, spread: float) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame()
    rows = []
    for t in trades:
        ts = pd.Timestamp(t["ts"])
        rows.append({
            "ts": ts, "session": session_of_hour(ts.hour),
            "outcome": t["outcome"], "pnl_pips": t["pnl_pips"],
        })
    df = pd.DataFrame(rows)
    out = []
    for sess in ("Tokyo", "London", "NY", "ALL"):
        sub = df if sess == "ALL" else df[df["session"] == sess]
        n = len(sub)
        if n == 0:
            out.append({"session": sess, "n": 0})
            continue
        wins = int((sub["outcome"] == "WIN").sum())
        wr = wins / n
        pnls = sub["pnl_pips"].values
        gw = pnls[pnls > 0].sum()
        gl = -pnls[pnls < 0].sum()
        pf = (gw / gl) if gl > 0 else 99.0
        ev = float(pnls.mean())
        out.append({
            "session": sess, "n": n, "wr_pct": round(wr * 100, 2),
            "ev_pips": round(ev, 3), "pf": round(pf, 3),
        })
    return pd.DataFrame(out)


def main():
    days = 180
    out_dir = Path("knowledge-base/raw/audits/ma_family_v1/cross_pair")
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    print("=" * 78)
    print("v1b ma_trend_perfect — Cross-pair generalization BT")
    print("=" * 78)

    summary = []
    for pair, spread in PAIRS_AND_SPREADS:
        print(f"\n[{pair} spread={spread}p] running 180d BT...")
        try:
            r = run_pair(pair, spread, days, out_dir)
            print(f"  N={r['n_trades']}  WR={r['wr_pct']}%  PF={r['pf']}  Kelly={r['kelly_pct']}%  EV={r['ev_pips']}p  ({r['elapsed_sec']}s)")

            cells = cell_breakdown(r.pop("trades_full"), spread)
            cells["pair"] = pair
            print(cells.to_string(index=False))
            summary.append({
                "pair": pair, "spread": spread,
                "n": r["n_trades"], "wr": r["wr_pct"], "pf": r["pf"],
                "kelly": r["kelly_pct"], "ev": r["ev_pips"],
                "wilson_lo": r["wilson_lower_pct"],
                "cells": cells.to_dict("records"),
            })
        except Exception as e:
            print(f"  ERROR: {e}")
            summary.append({"pair": pair, "error": str(e)})

    # Save summary
    out_path = out_dir / f"cross_pair_summary_{ts}.json"
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\nSaved: {out_path}")

    # Aggregate comparison
    print("\n" + "=" * 78)
    print("Cross-pair Comparison")
    print("=" * 78)
    print(f"{'pair':<10} {'spread':<8} {'N':<5} {'WR%':<7} {'PF':<6} {'Kelly%':<8} {'EV pip':<8} {'Wilson%':<8} {'Verdict'}")
    for s in summary:
        if "error" in s:
            print(f"{s['pair']:<10} ERROR: {s['error']}")
            continue
        verdict = (
            "🎯 STRUCTURAL EDGE" if s["wilson_lo"] > 50 and s["pf"] > 1.5
            else "✅ Generalizes" if s["wilson_lo"] > 30 and s["pf"] > 1.2
            else "🟡 Marginal" if s["pf"] > 1.0
            else "🔴 No edge / overfit"
        )
        print(f"{s['pair']:<10} {s['spread']:<8} {s['n']:<5} {s['wr']:<7} {s['pf']:<6} {s['kelly']:<8} {s['ev']:<8} {s['wilson_lo']:<8} {verdict}")


if __name__ == "__main__":
    main()
