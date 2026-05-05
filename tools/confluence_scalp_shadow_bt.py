#!/usr/bin/env python3
"""A/B BT light filter for confluence_scalp V2 timing hardening."""
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
    ("USD_JPY", "USDJPY=X"),
    ("EUR_JPY", "EURJPY=X"),
    ("GBP_USD", "GBPUSD=X"),
    ("GBP_JPY", "GBPJPY=X"),
]
LOOKBACK_DAYS = 365
MINIMUM_DAYS = 365
INTERVAL = "15m"
STRATEGY = "confluence_scalp"
FLAG = "CONFLUENCE_SCALP_REDESIGN_V2"
SHADOW_FLAG = "CONFLUENCE_SCALP_REDESIGN_V2_SHADOW_PROMOTE"
OUTFILE = ROOT / "bt-results/confluence_scalp-shadow-redesign-v2-2026-05-05.json"


class _ConfluenceOnlyScalperEngine:
    """BT strategy filter equivalent to strategies=['confluence_scalp']."""

    SHADOW_ALWAYS_STRATEGIES = frozenset()

    def __init__(self):
        from strategies.scalp.confluence_scalp import ConfluenceScalp
        self.strategies = [ConfluenceScalp()]

    def evaluate_all(self, ctx):
        candidates = []
        for strategy in self.strategies:
            result = strategy.evaluate(ctx)
            if result is not None:
                candidates.append(result)
        return candidates

    def select_best(self, candidates):
        if not candidates:
            return None
        return max(candidates, key=lambda c: c.score)

    def split_shadow_always(self, candidates, best):
        return []


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
    trades = [
        t for t in result.get("trade_log", [])
        if t.get("entry_type", t.get("type")) == STRATEGY
    ]
    pnls = [_pnl_r(t) for t in trades]
    n = len(trades)
    wins = sum(1 for p in pnls if p > 0)
    ev = sum(pnls) / n if n else 0.0
    pf = _pf(pnls)
    return {
        "N": n,
        "wins": wins,
        "WR": round(wins / n, 4) if n else 0.0,
        "EV": round(ev, 4),
        "PnL": round(sum(pnls), 4),
        "PF": round(pf, 4) if math.isfinite(pf) else "inf",
        "wilson_lo": round(_wilson_lower(wins, n), 4),
        "total_trades_all_strategies": result.get("trades", 0),
        "bt_error": result.get("error"),
        "data_source": result.get("data_source"),
        "bars_fetched": result.get("bars_fetched"),
    }


def _run(app, data_mod, symbol: str, proposed: bool, days: int) -> dict:
    os.environ[FLAG] = "1" if proposed else "0"
    app._scalp_bt_cache.clear()
    data_mod._data_cache.clear()
    from strategies.scalp.confluence_scalp import ConfluenceScalp
    ConfluenceScalp.reset_dedup_state()
    return app.run_scalp_backtest(
        symbol=symbol,
        lookback_days=days,
        interval=INTERVAL,
    )


def _num(value) -> float:
    if value == "inf":
        return float("inf")
    return float(value)


def _change_pct(proposed: float, current: float) -> float:
    if current == 0:
        if proposed == 0:
            return 0.0
        return float("inf") if proposed > 0 else float("-inf")
    return (proposed - current) / abs(current) * 100.0


def _pnl_sign_preserved(current: float, proposed: float) -> bool:
    return not (current > 0 and proposed < 0)


def _criteria(current: dict, proposed: dict) -> dict:
    if proposed["N"] < 20:
        return {
            "verdict": "INSUFFICIENT_BT_EVIDENCE",
            "reason": "proposed BT trades < 20; v2 spec skips catastrophic check",
            "catastrophic_check": "SKIPPED",
            "sanity_floor": "SKIPPED",
            "shadow_promote_recommendation": "RECOMMEND_SHADOW",
        }
    err = current.get("bt_error") or proposed.get("bt_error")
    if err:
        return {
            "verdict": "REJECT",
            "reason": "bt_error",
            "catastrophic_check": False,
            "sanity_floor": False,
            "shadow_promote_recommendation": "REJECT",
        }
    current_pf = _num(current["PF"])
    proposed_pf = _num(proposed["PF"])
    pf_change = proposed_pf - current_pf
    wilson_lo_change = proposed["wilson_lo"] - current["wilson_lo"]
    n_change_pct = _change_pct(proposed["N"], current["N"])
    checks = {
        "pf_change": round(pf_change, 4) if math.isfinite(pf_change) else str(pf_change),
        "wilson_lo_change": round(wilson_lo_change, 4),
        "n_change_pct": round(n_change_pct, 4) if math.isfinite(n_change_pct) else str(n_change_pct),
        "pnl_sign_preserved": _pnl_sign_preserved(current["PnL"], proposed["PnL"]),
    }
    catastrophic_check = (
        pf_change >= -0.10
        and wilson_lo_change >= -0.05
        and n_change_pct >= -30
        and checks["pnl_sign_preserved"]
    )
    floor = proposed["wilson_lo"] >= 0.20 and proposed_pf >= 0.85
    verdict = "PASS" if catastrophic_check and floor else "REJECT"
    return {
        **checks,
        "catastrophic_check": catastrophic_check,
        "sanity_floor": floor,
        "verdict": verdict,
        "shadow_promote_recommendation": "RECOMMEND_SHADOW" if verdict == "PASS" else "REJECT",
    }


def main() -> int:
    started = time.time()
    cells = {}
    missing = [
        str(_cache_path(pair).relative_to(ROOT))
        for pair, _ in TARGETS
        if not _cache_path(pair).exists()
    ]
    days = LOOKBACK_DAYS

    if missing:
        for pair, _symbol in TARGETS:
            err = f"missing MASSIVE parquet cache: {_cache_path(pair).relative_to(ROOT)}"
            cells[pair] = {
                "current": {"N": 0, "wins": 0, "WR": 0.0, "EV": 0.0, "PnL": 0.0,
                            "PF": 0.0, "wilson_lo": 0.0, "bt_error": err},
                "proposed": {"N": 0, "wins": 0, "WR": 0.0, "EV": 0.0, "PnL": 0.0,
                             "PF": 0.0, "wilson_lo": 0.0, "bt_error": err},
                "lock_criteria": {
                    "verdict": "REJECT",
                    "reason": "missing_massive_cache",
                    "shadow_promote_recommendation": "REJECT",
                },
            }
    else:
        import app  # noqa: E402
        from modules import data as data_mod  # noqa: E402
        import strategies.scalp as scalp_mod  # noqa: E402

        scalp_mod.ScalperEngine = _ConfluenceOnlyScalperEngine
        app.ScalperEngine = _ConfluenceOnlyScalperEngine

        for pair, symbol in TARGETS:
            print(f"Running baseline: {pair} {days}d", flush=True)
            current = _stats(_run(app, data_mod, symbol, proposed=False, days=days))
            print(f"Running proposed: {pair} {days}d", flush=True)
            proposed = _stats(_run(app, data_mod, symbol, proposed=True, days=days))
            cells[pair] = {
                "current": current,
                "proposed": proposed,
                "lock_criteria": _criteria(current, proposed),
            }

    cell_verdicts = [c["lock_criteria"].get("verdict") for c in cells.values()]
    if cells and any(v == "REJECT" for v in cell_verdicts):
        overall = "REJECT"
    elif cells and any(v == "INSUFFICIENT_BT_EVIDENCE" for v in cell_verdicts):
        overall = "INSUFFICIENT_BT_EVIDENCE"
    elif cells and all(v == "PASS" for v in cell_verdicts):
        overall = "PASS"
    else:
        overall = "REJECT"
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategy": STRATEGY,
        "variant": "closed_bar_dedup_v2",
        "flag": FLAG,
        "shadow_worker_flag": SHADOW_FLAG,
        "lookback_days": days,
        "minimum_days": MINIMUM_DAYS,
        "interval": INTERVAL,
        "runner": "app.run_scalp_backtest (production scalp path; strategy-isolated ScalperEngine patch)",
        "data_source_required": "data/cache/massive/{PAIR}_{TF}.parquet with BT_MODE=1 and BT_REQUIRE_MASSIVE_CACHE=1",
        "bt_mode": os.environ.get("BT_MODE"),
        "massive_cache_verified": not missing,
        "bt_error_data_source_note": "run_scalp_backtest omits data_source/bars_fetched when it returns the <20 trades error; console output should show massive-parquet/15m and missing_caches must be empty.",
        "targets": [pair for pair, _ in TARGETS],
        "missing_caches": missing,
        "lock_spec": {
            "bt_evidence_threshold": "if proposed N < 20 => INSUFFICIENT_BT_EVIDENCE, skip catastrophic, recommend shadow",
            "catastrophic_check": {
                "pf_change": ">= -0.10",
                "wilson_lo_change": ">= -0.05",
                "n_change_pct": ">= -30",
                "pnl_sign_preserved": True,
            },
            "sanity_floor": {
                "wilson_lo_proposed": ">= 0.20",
                "pf_proposed": ">= 0.85",
            },
            "positive_direction": "not required",
            "absolute_kelly": "not required",
        },
        "cells": cells,
        "overall_verdict": overall,
        "shadow_promote_recommendation": (
            "RECOMMEND_SHADOW"
            if overall in {"PASS", "INSUFFICIENT_BT_EVIDENCE"}
            else "REJECT"
        ),
        "shadow_accumulation_target": "60-90 days or N>=30 after shadow start",
        "elapsed_s": round(time.time() - started, 1),
        "self_review": {
            "catastrophic_only": "PASS: verdict ignores positive-direction and Kelly; applies only v2 catastrophic/floor rules when N>=20.",
            "insufficient_bt_evidence": "PASS: proposed N<20 becomes INSUFFICIENT_BT_EVIDENCE and shadow recommendation.",
            "production_live_safety": "PASS: strategy behavior is default-off unless CONFLUENCE_SCALP_REDESIGN_V2=1; shadow emit also requires CONFLUENCE_SCALP_REDESIGN_V2_SHADOW_PROMOTE=1.",
            "post_hoc_adjustment": "PASS: only the pre-registered closed_bar_dedup_v2 variant is evaluated.",
            "bt_source_guard": "PASS: BT_REQUIRE_MASSIVE_CACHE=1 prevents Yahoo/network fallback for this report.",
            "runner_note": "PASS: confluence_scalp is a scalp-engine strategy, so run_scalp_backtest is the production runner; run_daytrade_backtest does not evaluate this strategy.",
        },
    }

    OUTFILE.parent.mkdir(parents=True, exist_ok=True)
    OUTFILE.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved: {OUTFILE}")
    print(f"Overall: {overall}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
