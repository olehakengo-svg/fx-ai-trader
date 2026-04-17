#!/usr/bin/env python3
"""
Regime Cross-Tab: production tag vs OANDA-independent labeler
══════════════════════════════════════════════════════════════

conditional-edge-estimand §6 の action E.
production 自己申告 regime と OANDA 独立 labeler の乖離を直接計測する.

Hypothesis (from portfolio-balance-audit 2026-04-17):
    production `RANGE` 40% の内訳が独立 labeler では up_trend/down_trend/uncertain
    にばらける。特に RANGE × SELL -1.57p の悪化は "実は up_trend だった期間" が
    RANGE と誤ラベルされている可能性。

Usage:
    python3 tools/regime_cross_tab.py
    python3 tools/regime_cross_tab.py --date-from 2026-04-08
"""
from __future__ import annotations
import argparse
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

env_path = ROOT / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)


def _parse_prod_regime(regime_json: str) -> str:
    import json
    if not regime_json or not isinstance(regime_json, str):
        return "UNKNOWN"
    try:
        obj = json.loads(regime_json)
    except (json.JSONDecodeError, ValueError):
        return "UNKNOWN"
    if not isinstance(obj, dict):
        return "UNKNOWN"
    r = obj.get("regime", "UNKNOWN")
    return r if r in ("TREND_BULL", "TREND_BEAR", "RANGE") else "UNKNOWN"


def run(date_from: str) -> None:
    import pandas as pd
    from research.edge_discovery.production_fetcher import fetch_closed_trades
    from research.edge_discovery.regime_labeler import (
        fetch_and_label, label_trades,
    )

    print("═" * 78)
    print("REGIME CROSS-TAB: production tag vs OANDA-independent labeler")
    print(f"date_from={date_from}")
    print("═" * 78)

    trades = fetch_closed_trades(date_from=date_from, include_shadow=True)
    if trades.empty:
        print("no trades; abort")
        return
    trades["regime_prod"] = trades["regime"].apply(_parse_prod_regime) \
        if "regime" in trades.columns else "UNKNOWN"
    print(f"Fetched {len(trades)} trades "
          f"({trades['entry_time'].min().date()} → "
          f"{trades['entry_time'].max().date()})")

    instruments = sorted(trades["instrument"].dropna().unique())
    instruments = [i for i in instruments if "XAU" not in i]
    print(f"Instruments: {instruments}")

    # Fetch + label candles per instrument
    # 9 days × 48 M30 bars/day = ~432 bars minimum. Fetch 1000 for buffer.
    print("\nFetching OANDA candles (M30, count=1000 per instrument)...")
    candles_by_inst = {}
    for inst in instruments:
        try:
            labeled = fetch_and_label(instrument=inst, granularity="M30",
                                      count=1000)
            candles_by_inst[inst] = labeled
            vc = labeled["regime"].value_counts(normalize=True).round(3)
            print(f"  {inst}: {len(labeled)} bars, "
                  f"range={vc.get('range', 0):.2%}, "
                  f"up={vc.get('up_trend', 0):.2%}, "
                  f"down={vc.get('down_trend', 0):.2%}, "
                  f"unc={vc.get('uncertain', 0):.2%}")
        except Exception as e:
            print(f"  {inst}: FETCH FAILED — {e}")
            candles_by_inst[inst] = pd.DataFrame()

    # Join trades → regime_independent
    trades = label_trades(trades, candles_by_inst)

    # ── 1. Cross-tab: production vs independent (counts) ──────────────
    print("\n" + "─" * 78)
    print("1. CROSS-TAB: production tag (rows) vs independent labeler (cols)")
    print("─" * 78)
    live = trades[trades.get("is_shadow", 0) != 1].copy()
    ct = pd.crosstab(live["regime_prod"], live["regime_independent"],
                     margins=True, margins_name="Total")
    print(ct.to_string())

    # ── 2. Cross-tab: row % (production view) ─────────────────────────
    print("\n" + "─" * 78)
    print("2. CROSS-TAB (row %): production が X とラベルした trade は")
    print("   独立 labeler では何に分類されたか")
    print("─" * 78)
    ct_row = pd.crosstab(live["regime_prod"], live["regime_independent"],
                         normalize="index")
    print((ct_row * 100).round(1).to_string())

    # ── 3. π_sample (independent, LIVE only) ──────────────────────────
    print("\n" + "─" * 78)
    print("3. π_sample — independent labeler (LIVE only)")
    print("─" * 78)
    vc = live["regime_independent"].value_counts(normalize=True).round(3)
    for r in ["up_trend", "down_trend", "range", "uncertain"]:
        print(f"  {r:12s}: {vc.get(r, 0):.1%}")

    # ── 4. PnL by independent regime × direction ──────────────────────
    print("\n" + "─" * 78)
    print("4. INDEPENDENT REGIME × DIRECTION × PNL (LIVE only)")
    print("─" * 78)
    print(f"  {'regime':12s} {'dir':5s} {'N':>5s} {'WR':>6s} "
          f"{'Avg':>8s} {'Med':>8s}")
    for r in ["up_trend", "down_trend", "range", "uncertain"]:
        for d in ["BUY", "SELL"]:
            s = live[(live["regime_independent"] == r)
                     & (live["direction"] == d)]["pnl_pips"]
            if len(s) < 5:
                continue
            wr = 100 * (s > 0).mean()
            print(f"  {r:12s} {d:5s} {len(s):5d} {wr:5.1f}% "
                  f"{s.mean():+7.2f}p {s.median():+7.2f}p")

    # ── 5. PnL by production regime × direction (for comparison) ──────
    print("\n" + "─" * 78)
    print("5. PRODUCTION REGIME × DIRECTION × PNL (LIVE, baseline)")
    print("─" * 78)
    print(f"  {'regime_prod':12s} {'dir':5s} {'N':>5s} {'WR':>6s} "
          f"{'Avg':>8s} {'Med':>8s}")
    for r in ["TREND_BULL", "TREND_BEAR", "RANGE", "UNKNOWN"]:
        for d in ["BUY", "SELL"]:
            s = live[(live["regime_prod"] == r)
                     & (live["direction"] == d)]["pnl_pips"]
            if len(s) < 5:
                continue
            wr = 100 * (s > 0).mean()
            print(f"  {r:12s} {d:5s} {len(s):5d} {wr:5.1f}% "
                  f"{s.mean():+7.2f}p {s.median():+7.2f}p")

    # ── 6. Disagreement rate ──────────────────────────────────────────
    print("\n" + "─" * 78)
    print("6. AGREEMENT RATE")
    print("─" * 78)
    # Map: production RANGE → independent range, production TREND_BULL →
    # independent up_trend, TREND_BEAR → down_trend.
    map_prod = {"TREND_BULL": "up_trend", "TREND_BEAR": "down_trend",
                "RANGE": "range", "UNKNOWN": "uncertain"}
    live["prod_mapped"] = live["regime_prod"].map(map_prod)
    agree = (live["prod_mapped"] == live["regime_independent"]).mean()
    print(f"  strict agreement (prod == independent): {agree:.1%}")
    # Loose: production TREND_BULL|TREND_BEAR → any trend
    def _to_class(r):
        if r in ("up_trend", "down_trend"):
            return "trend"
        return r
    live["prod_class"] = live["prod_mapped"].apply(_to_class)
    live["ind_class"] = live["regime_independent"].apply(_to_class)
    loose = (live["prod_class"] == live["ind_class"]).mean()
    print(f"  loose agreement (trend==trend): {loose:.1%}")

    print("\n" + "═" * 78)
    print("完了. 解釈は portfolio-balance-audit-2026-04-17.md に追記予定.")
    print("═" * 78)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date-from", default="2026-04-08")
    args = parser.parse_args()
    run(date_from=args.date_from)


if __name__ == "__main__":
    main()
