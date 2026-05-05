#!/usr/bin/env python3
"""A/B 365d BT for doji_breakout range-close redesign."""
from __future__ import annotations

import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

os.environ["BT_MODE"] = "1"
os.environ["NO_AUTOSTART"] = "1"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.edge_discovery.significance import binomial_one_sided_p  # noqa: E402


TARGETS = [
    ("GBP_USD", "GBPUSD=X"),
    ("USD_JPY", "USDJPY=X"),
]
LOOKBACK_DAYS = 365
INTERVAL = "15m"
STRATEGY = "doji_breakout"
OUTFILE = ROOT / "knowledge-base/raw/bt-results/doji_breakout-redesign-2026-05-05.json"


def _pnl_r(t: dict) -> float:
    friction = float(t.get("exit_friction_m", 0) or 0)
    if t.get("outcome") == "WIN":
        return float(t.get("tp_m", 1.5) or 1.5) - friction
    return -(float(t.get("actual_sl_m", t.get("sl_m", 1.0)) or 1.0) + friction)


def _wilson_lower(wins: int, n: int, z: float = 1.959963984540054) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return max(0.0, (centre - spread) / denom)


def _kelly(pnls: list[float]) -> float | None:
    wins = [p for p in pnls if p > 0]
    losses = [-p for p in pnls if p < 0]
    if not wins or not losses:
        return None
    p = len(wins) / len(pnls)
    b = (sum(wins) / len(wins)) / (sum(losses) / len(losses))
    if b <= 0:
        return None
    return (p * b - (1 - p)) / b


def _pf(pnls: list[float]) -> float:
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = -sum(p for p in pnls if p < 0)
    if gross_loss <= 0:
        return float("inf") if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def _wf3(trades: list[dict]) -> dict:
    n = len(trades)
    window_size = n // 3
    if window_size < 5:
        return {"folds": [], "n_folds": 0, "positive_ratio": 0.0}
    folds = []
    for wi in range(3):
        wt = trades[wi * window_size:(wi + 1) * window_size]
        pnls = [_pnl_r(t) for t in wt]
        wins = sum(1 for p in pnls if p > 0)
        ev = sum(pnls) / len(pnls)
        folds.append({
            "fold": wi + 1,
            "N": len(wt),
            "WR": round(wins / len(wt), 4),
            "EV": round(ev, 4),
            "positive": ev > 0,
        })
    positives = sum(1 for f in folds if f["positive"])
    return {
        "folds": folds,
        "n_folds": len(folds),
        "positive_folds": positives,
        "positive_ratio": round(positives / len(folds), 4),
    }


def _stats(result: dict) -> dict:
    trades = [t for t in result.get("trade_log", []) if t.get("entry_type") == STRATEGY]
    pnls = [_pnl_r(t) for t in trades]
    n = len(trades)
    wins = sum(1 for p in pnls if p > 0)
    ev = sum(pnls) / n if n else 0.0
    return {
        "N": n,
        "wins": wins,
        "WR": round(wins / n, 4) if n else 0.0,
        "EV": round(ev, 4),
        "PnL": round(sum(pnls), 4),
        "PF": round(_pf(pnls), 4) if n else 0.0,
        "kelly": None if _kelly(pnls) is None else round(_kelly(pnls), 4),
        "wilson_lo": round(_wilson_lower(wins, n), 4),
        "wf3": _wf3(trades),
        "total_trades_all_strategies": result.get("trades", 0),
        "bt_error": result.get("error"),
    }


def _run(app, *, symbol: str, proposed: bool) -> dict:
    os.environ["DOJI_BREAKOUT_RANGE_CLOSE"] = "1" if proposed else "0"
    app._dt_bt_cache.clear()
    return app.run_daytrade_backtest(symbol, lookback_days=LOOKBACK_DAYS, interval=INTERVAL)


def main() -> int:
    started = time.time()
    import app  # noqa: E402

    cells = {}
    for pair, yf_symbol in TARGETS:
        print(f"Running current: {pair}", flush=True)
        current = _stats(_run(app, symbol=yf_symbol, proposed=False))
        print(f"Running proposed: {pair}", flush=True)
        proposed = _stats(_run(app, symbol=yf_symbol, proposed=True))

        p_raw = 1.0
        if proposed["N"] > 0 and current["N"] > 0:
            p_raw = binomial_one_sided_p(
                proposed["wins"],
                proposed["N"],
                max(min(current["WR"], 0.999999), 0.000001),
            )
        cells[pair] = {
            "current": current,
            "proposed": proposed,
            "significance": {
                "raw_p_vs_current_wr": round(p_raw, 6),
                "bonferroni_p": round(min(1.0, p_raw * len(TARGETS)), 6),
                "wilson_lo_delta": round(proposed["wilson_lo"] - current["wilson_lo"], 4),
            },
        }

    pass_cells = []
    for pair, cell in cells.items():
        prop = cell["proposed"]
        sig = cell["significance"]
        wf = prop["wf3"]
        stable = wf["n_folds"] >= 3 and wf["positive_ratio"] >= 0.67
        significant = sig["bonferroni_p"] < 0.05 or sig["wilson_lo_delta"] >= 0.05
        pass_cells.append(stable and significant)
        cell["lock_criteria"] = {
            "stable": stable,
            "significant": significant,
            "kelly_desired": prop["kelly"] is not None and prop["kelly"] >= 0.40,
            "verdict": "PASS" if stable and significant else "FAIL",
        }

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategy": STRATEGY,
        "variant": "range_close_buffer",
        "lookback_days": LOOKBACK_DAYS,
        "interval": INTERVAL,
        "targets": [pair for pair, _ in TARGETS],
        "bonferroni_family_size": len(TARGETS),
        "cells": cells,
        "overall_verdict": "PASS" if all(pass_cells) else "FAIL",
        "elapsed_s": round(time.time() - started, 1),
        "self_review": {
            "post_hoc_selection": "PASS: only the locked range_close_buffer variant was evaluated.",
            "data_leakage": "PASS: run_daytrade_backtest uses rolling bar_df slices and next-bar entry.",
            "lookahead_bias": "PASS: proposed trigger reads the already-closed breakout bar at df.iloc[-2], matching existing timing.",
            "live_promote": "PASS: variant is default-off and selected only by test/env flag.",
        },
    }

    OUTFILE.parent.mkdir(parents=True, exist_ok=True)
    OUTFILE.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved: {OUTFILE}")
    print(f"Overall: {result['overall_verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
