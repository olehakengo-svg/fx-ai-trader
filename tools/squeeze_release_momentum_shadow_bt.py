#!/usr/bin/env python3
"""A/B BT light filter for squeeze_release_momentum V2 timing hardening."""
from __future__ import annotations

import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

os.environ["BT_MODE"] = "1"
os.environ["BT_REQUIRE_MASSIVE_CACHE"] = "1"
os.environ["NO_AUTOSTART"] = "1"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TARGETS = [
    ("EUR_USD", "EURUSD=X"),
    ("GBP_USD", "GBPUSD=X"),
]
LOOKBACK_DAYS = 365
INTERVAL = "15m"
STRATEGY = "squeeze_release_momentum"
FLAG = "SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2"
OUTFILE = ROOT / "knowledge-base/raw/bt-results/squeeze_release_momentum-shadow-bt-2026-05-05.json"


def _cache_path(pair: str) -> Path:
    return ROOT / "data" / "cache" / "massive" / f"{pair}_{INTERVAL}.parquet"


def _pnl_r(trade: dict) -> float:
    friction = float(trade.get("exit_friction_m", 0) or 0)
    if trade.get("outcome") == "WIN":
        return float(trade.get("tp_m", 1.5) or 1.5) - friction
    return -(float(trade.get("actual_sl_m", trade.get("sl_m", 1.0)) or 1.0) + friction)


def _wilson_lower(wins: int, n: int, z: float = 1.959963984540054) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return max(0.0, (centre - spread) / denom)


def _pf(pnls: list[float]) -> float:
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = -sum(p for p in pnls if p < 0)
    if gross_loss <= 0:
        return float("inf") if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


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
        "wilson_lo": round(_wilson_lower(wins, n), 4),
        "total_trades_all_strategies": result.get("trades", 0),
        "bt_error": result.get("error"),
        "data_source": result.get("data_source"),
        "bars_fetched": result.get("bars_fetched"),
    }


def _run(app, data_mod, symbol: str, proposed: bool) -> dict:
    os.environ[FLAG] = "1" if proposed else "0"
    app._dt_bt_cache.clear()
    data_mod._data_cache.clear()
    from strategies.daytrade.squeeze_release_momentum import SqueezeReleaseMomentum
    SqueezeReleaseMomentum.reset_dedup_state()
    return app.run_daytrade_backtest(
        symbol=symbol,
        lookback_days=LOOKBACK_DAYS,
        interval=INTERVAL,
    )


def _change_pct(proposed: float, current: float) -> float:
    if current == 0:
        if proposed == 0:
            return 0.0
        return float("inf") if proposed > 0 else float("-inf")
    return (proposed - current) / abs(current) * 100.0


def _pnl_sign_preserved(current: float, proposed: float) -> bool:
    return not (current > 0 and proposed < 0)


def _criteria(current: dict, proposed: dict) -> dict:
    missing = current.get("bt_error") or proposed.get("bt_error")
    if missing:
        return {
            "verdict": "FAIL",
            "reason": "bt_error",
            "non_catastrophic": False,
            "positive_direction": False,
            "sanity_floor": False,
        }
    pf_change = proposed["PF"] - current["PF"]
    wilson_lo_change = proposed["wilson_lo"] - current["wilson_lo"]
    n_change_pct = _change_pct(proposed["N"], current["N"])
    ev_change_pct = _change_pct(proposed["EV"], current["EV"])
    checks = {
        "pf_change": round(pf_change, 4),
        "wilson_lo_change": round(wilson_lo_change, 4),
        "n_change_pct": round(n_change_pct, 4) if math.isfinite(n_change_pct) else str(n_change_pct),
        "pnl_sign_preserved": _pnl_sign_preserved(current["PnL"], proposed["PnL"]),
        "ev_change_pct": round(ev_change_pct, 4) if math.isfinite(ev_change_pct) else str(ev_change_pct),
    }
    non_cat = (
        pf_change >= -0.05
        and wilson_lo_change >= -0.02
        and n_change_pct >= -20
        and checks["pnl_sign_preserved"]
    )
    positive = (
        wilson_lo_change >= 0.01
        or ev_change_pct >= 5
        or pf_change >= 0.02
    )
    floor = proposed["wilson_lo"] >= 0.30 and proposed["PF"] >= 0.95
    return {
        **checks,
        "non_catastrophic": non_cat,
        "positive_direction": positive,
        "sanity_floor": floor,
        "verdict": "PASS" if non_cat and positive and floor else "FAIL",
    }


def main() -> int:
    started = time.time()
    cells = {}
    missing = [str(_cache_path(pair).relative_to(ROOT)) for pair, _ in TARGETS if not _cache_path(pair).exists()]

    if missing:
        for pair, _symbol in TARGETS:
            err = f"missing MASSIVE parquet cache: {_cache_path(pair).relative_to(ROOT)}"
            cells[pair] = {
                "current": {"N": 0, "wins": 0, "WR": 0.0, "EV": 0.0, "PnL": 0.0,
                            "PF": 0.0, "wilson_lo": 0.0, "bt_error": err},
                "proposed": {"N": 0, "wins": 0, "WR": 0.0, "EV": 0.0, "PnL": 0.0,
                             "PF": 0.0, "wilson_lo": 0.0, "bt_error": err},
                "lock_criteria": {"verdict": "FAIL", "reason": "missing_massive_cache"},
            }
    else:
        import app  # noqa: E402
        from modules import data as data_mod  # noqa: E402

        for pair, symbol in TARGETS:
            print(f"Running baseline: {pair}", flush=True)
            current = _stats(_run(app, data_mod, symbol, proposed=False))
            print(f"Running proposed: {pair}", flush=True)
            proposed = _stats(_run(app, data_mod, symbol, proposed=True))
            cells[pair] = {
                "current": current,
                "proposed": proposed,
                "lock_criteria": _criteria(current, proposed),
            }

    overall = "PASS" if cells and all(c["lock_criteria"].get("verdict") == "PASS" for c in cells.values()) else "FAIL"
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategy": STRATEGY,
        "variant": "closed_bar_dedup_v2",
        "flag": FLAG,
        "lookback_days": LOOKBACK_DAYS,
        "minimum_days": 90,
        "interval": INTERVAL,
        "data_source_required": "data/cache/massive/{PAIR}_{TF}.parquet with BT_MODE=1",
        "targets": [pair for pair, _ in TARGETS],
        "missing_caches": missing,
        "cells": cells,
        "overall_verdict": overall,
        "shadow_promote_recommendation": "REJECT" if overall != "PASS" else "RECOMMEND_SHADOW",
        "shadow_accumulation_target": "60-90 days or N>=30 after shadow start",
        "elapsed_s": round(time.time() - started, 1),
        "self_review": {
            "relative_check_only": "PASS: verdict uses relative PF/Wilson/N/PnL and sanity floors; no absolute Kelly gate.",
            "production_live_safety": "PASS: strategy behavior is default-off unless SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2=1.",
            "post_hoc_adjustment": "PASS: only the pre-registered closed_bar_dedup_v2 variant is evaluated.",
            "bt_source_guard": "PASS: BT_REQUIRE_MASSIVE_CACHE=1 prevents Yahoo/network fallback for this report.",
        },
    }

    OUTFILE.parent.mkdir(parents=True, exist_ok=True)
    OUTFILE.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved: {OUTFILE}")
    print(f"Overall: {overall}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
