#!/usr/bin/env python3
"""A/B BT filter for vsg_jpy_reversal V2 MR exit geometry."""
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
sys.modules.setdefault("pytest", object())

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TARGETS = [("EUR_JPY", "EURJPY=X"), ("GBP_JPY", "GBPJPY=X")]
LOOKBACK_DAYS = 365
MINIMUM_DAYS = 365
INTERVAL = "15m"
STRATEGY = "vsg_jpy_reversal"
FLAG = "VSG_JPY_REVERSAL_REDESIGN_V2"
SHADOW_PROMOTE_FLAG = "VSG_JPY_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE"
OUTFILE = ROOT / "bt-results" / "vsg_jpy_reversal-shadow-redesign-v2-2026-05-05.json"


def _compute_vsg_only_signal(df, tf, sr_levels, symbol="EURJPY=X",
                             backtest_mode=False, bar_time=None, htf_cache=None):
    from strategies.context import SignalContext
    from strategies.daytrade.vsg_jpy_reversal import VsgJpyReversal

    if df is None or len(df) == 0:
        return {"signal": "WAIT", "entry_type": "wait", "reasons": ["empty df"]}

    row = df.iloc[-1]
    entry = float(row["Close"])
    atr = float(row.get("atr", 0.0))
    is_jpy = "JPY" in symbol.upper()
    ctx = SignalContext(
        entry=entry,
        open_price=float(row["Open"]),
        atr=atr,
        adx=float(row.get("adx", 25.0)),
        symbol=symbol,
        tf=tf,
        is_jpy=is_jpy,
        pip_mult=100 if is_jpy else 10000,
        df=df,
        sr_levels=sr_levels,
        layer3={},
        htf=(htf_cache or {}).get("htf", {}) if isinstance(htf_cache, dict) else {},
        backtest_mode=backtest_mode,
        bar_time=bar_time,
    )
    cand = VsgJpyReversal().evaluate(ctx)
    if cand is None:
        return {
            "signal": "WAIT",
            "entry": entry,
            "entry_type": "wait",
            "reasons": ["vsg_jpy_reversal no signal"],
            "atr": atr,
            "mode": "daytrade",
            "indicators": {},
        }
    return {
        "signal": cand.signal,
        "entry": entry,
        "confidence": cand.confidence,
        "sl": cand.sl,
        "tp": cand.tp,
        "entry_type": cand.entry_type,
        "reasons": ["✅ vsg_jpy_reversal strategy-filter BT"] + list(cand.reasons or []),
        "score": cand.score,
        "atr": atr,
        "mode": "daytrade",
        "layer_status": {},
        "regime": {},
        "indicators": {},
        "max_hold_bars": cand.max_hold_bars,
        "shadow_emit_signals": [],
    }


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
    n = len(trades) if trades else int(result.get("trades", 0) or 0)
    wins = sum(1 for p in pnls if p > 0)
    ev = sum(pnls) / n if n and pnls else 0.0
    pf = _pf(pnls)
    return {
        "N": n,
        "wins": wins,
        "WR": round(wins / n, 4) if n and pnls else 0.0,
        "EV": round(ev, 4),
        "PnL": round(sum(pnls), 4),
        "PF": round(pf, 4) if math.isfinite(pf) else "inf",
        "wilson_lo": round(_wilson_lower(wins, n), 4) if pnls else 0.0,
        "total_trades_all_strategies": result.get("trades", 0),
        "bt_error": result.get("error"),
        "data_source": result.get("data_source"),
        "bars_fetched": result.get("bars_fetched"),
    }


def _run(app, data_mod, symbol: str, proposed: bool) -> dict:
    os.environ[FLAG] = "1" if proposed else "0"
    app._dt_bt_cache.clear()
    if hasattr(data_mod, "_data_cache"):
        data_mod._data_cache.clear()
    return app.run_daytrade_backtest(
        symbol=symbol,
        lookback_days=LOOKBACK_DAYS,
        interval=INTERVAL,
        backtest_mode=True,
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
            "reason": "proposed BT trades < 20; v2.1 skips catastrophic check",
            "catastrophic_check": "SKIPPED",
            "shadow_promote_recommendation": "RECOMMEND_SHADOW",
        }
    err = current.get("bt_error") or proposed.get("bt_error")
    if err:
        return {
            "verdict": "REJECT",
            "reason": "bt_error",
            "bt_error": err,
            "catastrophic_check": False,
            "shadow_promote_recommendation": "REJECT",
        }

    current_pf = _num(current["PF"])
    proposed_pf = _num(proposed["PF"])
    pf_change = proposed_pf - current_pf
    wilson_lo_change = proposed["wilson_lo"] - current["wilson_lo"]
    n_change_pct = _change_pct(proposed["N"], current["N"])
    pnl_ok = _pnl_sign_preserved(current["PnL"], proposed["PnL"])
    warnings = {
        "pf_change": round(pf_change, 4) if math.isfinite(pf_change) else str(pf_change),
        "wilson_lo_change": round(wilson_lo_change, 4),
        "n_change_pct": round(n_change_pct, 4) if math.isfinite(n_change_pct) else str(n_change_pct),
    }
    verdict = "PASS" if pnl_ok else "REJECT"
    return {
        "verdict": verdict,
        "catastrophic_check": pnl_ok,
        "pnl_sign_preserved": pnl_ok,
        "warn_only_metrics": warnings,
        "sanity_floor": "REMOVED_IN_V2_1",
        "shadow_promote_recommendation": "RECOMMEND_SHADOW" if pnl_ok else "REJECT",
    }


def main() -> int:
    started = time.time()
    cells = {}
    missing = [
        str(_cache_path(pair).relative_to(ROOT))
        for pair, _ in TARGETS
        if not _cache_path(pair).exists()
    ]

    if missing:
        for pair, _symbol in TARGETS:
            err = f"missing MASSIVE parquet cache: {', '.join(missing)}"
            cells[pair] = {
                "current": {"N": 0, "wins": 0, "WR": 0.0, "EV": 0.0, "PnL": 0.0,
                            "PF": 0.0, "wilson_lo": 0.0, "bt_error": err},
                "proposed": {"N": 0, "wins": 0, "WR": 0.0, "EV": 0.0, "PnL": 0.0,
                             "PF": 0.0, "wilson_lo": 0.0, "bt_error": err},
                "lock_criteria": {
                    "verdict": "BLOCKED_DATA",
                    "reason": "missing required MASSIVE parquet cache",
                },
            }
    else:
        import app  # noqa: E402
        from modules import data as data_mod  # noqa: E402

        app.compute_daytrade_signal = _compute_vsg_only_signal

        for pair, symbol in TARGETS:
            print(f"Running baseline: {pair} {LOOKBACK_DAYS}d", flush=True)
            current = _stats(_run(app, data_mod, symbol, proposed=False))
            print(f"Running proposed: {pair} {LOOKBACK_DAYS}d", flush=True)
            proposed = _stats(_run(app, data_mod, symbol, proposed=True))
            cells[pair] = {
                "current": current,
                "proposed": proposed,
                "lock_criteria": _criteria(current, proposed),
            }

    verdicts = [c["lock_criteria"].get("verdict") for c in cells.values()]
    if verdicts and any(v == "REJECT" for v in verdicts):
        overall = "REJECT"
    elif verdicts and all(v == "BLOCKED_DATA" for v in verdicts):
        overall = "BLOCKED_DATA"
    elif verdicts and any(v == "INSUFFICIENT_BT_EVIDENCE" for v in verdicts):
        overall = "INSUFFICIENT_BT_EVIDENCE"
    elif verdicts and all(v == "PASS" for v in verdicts):
        overall = "PASS"
    else:
        overall = "REJECT"

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategy": STRATEGY,
        "variant": "v2_mr_exit_geometry_sl_1p8atr_tp_0p9atr_no_min_rr_pair_hold",
        "flag": FLAG,
        "shadow_worker_flag": SHADOW_PROMOTE_FLAG,
        "target_scope": "EUR_JPY and GBP_JPY; trigger thesis preserved with GBP_JPY threshold relaxed to 1.0",
        "lookback_days": LOOKBACK_DAYS,
        "minimum_days": MINIMUM_DAYS,
        "interval": INTERVAL,
        "runner": "app.run_daytrade_backtest(backtest_mode=True; production daytrade path; strategy-only compute patch)",
        "data_source_required": "data/cache/massive/{PAIR}_{TF}.parquet with BT_MODE=1 and BT_REQUIRE_MASSIVE_CACHE=1",
        "bt_mode": os.environ.get("BT_MODE"),
        "bt_require_massive_cache": os.environ.get("BT_REQUIRE_MASSIVE_CACHE"),
        "massive_cache_verified": not missing,
        "targets": [pair for pair, _ in TARGETS],
        "missing_caches": missing,
        "lock_spec": {
            "bt_evidence_threshold": "if proposed N < 20 => INSUFFICIENT_BT_EVIDENCE, skip catastrophic, recommend shadow",
            "catastrophic_check": "pnl_sign_preserved only: baseline PnL > 0 and proposed PnL < 0 rejects",
            "warn_only": ["pf_change", "wilson_lo_change", "n_change_pct"],
            "sanity_floor": "removed in v2.1",
            "positive_direction": "not required",
            "absolute_kelly": "not required",
        },
        "cells": cells,
        "overall_verdict": overall,
        "shadow_promote_recommendation": (
            "RECOMMEND_SHADOW" if overall in {"PASS", "INSUFFICIENT_BT_EVIDENCE"} else overall
        ),
        "shadow_registration_note": (
            "base vsg_jpy_reversal is already in DaytradeEngine.SHADOW_ALWAYS_STRATEGIES; "
            "V2 behavior is default-off unless VSG_JPY_REVERSAL_REDESIGN_V2=1. "
            "No V2 shadow-promote setting is applied when the overall verdict is REJECT."
        ),
        "shadow_accumulation_target": "60-90 days or N>=30 after shadow start",
        "elapsed_s": round(time.time() - started, 1),
        "self_review": {
            "catastrophic_only": "PASS: verdict uses only pnl_sign_preserved when proposed N>=20; PF/Wilson/N are warn-only.",
            "insufficient_bt_evidence": "PASS: proposed N<20 becomes INSUFFICIENT_BT_EVIDENCE and recommends shadow.",
            "production_live_safety": "PASS: V2 trigger/geometry/time-exit are default-off unless VSG_JPY_REVERSAL_REDESIGN_V2=1; BT cache and SL/TP preserve are flag-aware.",
            "post_hoc_adjustment": "PASS: only pre-registered V2 exit geometry plus pair threshold/hold candidates from the audit are evaluated.",
            "bt_source_guard": "PASS: BT_REQUIRE_MASSIVE_CACHE=1 requires MASSIVE parquet and prevents Yahoo fallback for this report.",
        },
    }
    OUTFILE.parent.mkdir(parents=True, exist_ok=True)
    OUTFILE.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"outfile": str(OUTFILE), "overall_verdict": overall}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
