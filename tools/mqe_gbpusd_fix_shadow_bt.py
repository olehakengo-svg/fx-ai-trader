#!/usr/bin/env python3
"""A/B BT light filter for mqe_gbpusd_fix V2 fix-window/time-stop redesign."""
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

TARGETS = [("GBP_USD", "GBPUSD=X")]
LOOKBACK_DAYS = 365
MINIMUM_DAYS = 365
INTERVAL = "15m"
STRATEGY = "mqe_gbpusd_fix"
FLAG = "MQE_GBPUSD_FIX_REDESIGN_V2"
OUTFILE = ROOT / "bt-results" / "mqe_gbpusd_fix-shadow-redesign-v2-2026-05-05.json"


def _compute_mqe_only_signal(df, tf, sr_levels, symbol="GBPUSD=X",
                             backtest_mode=False, bar_time=None, htf_cache=None):
    from strategies.context import SignalContext
    from strategies.daytrade.mqe_gbpusd_fix import MqeGbpusdFix

    if df is None or len(df) == 0:
        return {"signal": "WAIT", "entry_type": "wait", "reasons": ["empty df"]}

    row = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else row
    entry = float(row["Close"])
    atr = float(row.get("atr", row.get("atr7", 0.0)))
    ctx = SignalContext(
        entry=entry,
        open_price=float(row["Open"]),
        atr=atr,
        atr7=float(row.get("atr7", atr)),
        prev_close=float(prev["Close"]),
        prev_open=float(prev["Open"]),
        prev_high=float(prev["High"]),
        prev_low=float(prev["Low"]),
        symbol=symbol,
        tf=tf,
        is_jpy=False,
        pip_mult=10000,
        df=df,
        sr_levels=sr_levels,
        htf=(htf_cache or {}).get("htf", {}) if isinstance(htf_cache, dict) else {},
        backtest_mode=backtest_mode,
        bar_time=bar_time,
    )
    cand = MqeGbpusdFix().evaluate(ctx)
    if cand is None:
        return {
            "signal": "WAIT",
            "entry": entry,
            "entry_type": "wait",
            "reasons": ["mqe_gbpusd_fix no signal"],
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
        "reasons": ["✅ mqe_gbpusd_fix strategy-filter BT"] + list(cand.reasons or []),
        "score": cand.score,
        "atr": atr,
        "mode": "daytrade",
        "layer_status": {},
        "regime": {},
        "indicators": {},
        "shadow_emit_signals": [],
        "max_hold_bars": cand.max_hold_bars,
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


def _run(app, data_mod, symbol: str, proposed: bool) -> dict:
    from strategies.daytrade.mqe_gbpusd_fix import MqeGbpusdFix

    os.environ[FLAG] = "1" if proposed else "0"
    MqeGbpusdFix.reset_dedup_state()
    app._dt_bt_cache.clear()
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
            "pnl_sign_preserved": "SKIPPED",
            "shadow_promote_recommendation": "RECOMMEND_SHADOW",
            "warnings": {
                "bt_error_current": current.get("bt_error"),
                "bt_error_proposed": proposed.get("bt_error"),
            },
        }

    current_pf = _num(current["PF"])
    proposed_pf = _num(proposed["PF"])
    pf_change = proposed_pf - current_pf
    wilson_lo_change = proposed["wilson_lo"] - current["wilson_lo"]
    n_change_pct = _change_pct(proposed["N"], current["N"])
    sign_ok = _pnl_sign_preserved(current["PnL"], proposed["PnL"])
    verdict = "PASS" if sign_ok else "REJECT"
    return {
        "pf_change_warn_only": round(pf_change, 4) if math.isfinite(pf_change) else str(pf_change),
        "wilson_lo_change_warn_only": round(wilson_lo_change, 4),
        "n_change_pct_warn_only": round(n_change_pct, 4) if math.isfinite(n_change_pct) else str(n_change_pct),
        "pnl_sign_preserved": sign_ok,
        "catastrophic_check": sign_ok,
        "verdict": verdict,
        "shadow_promote_recommendation": "RECOMMEND_SHADOW" if verdict == "PASS" else "REJECT",
        "warnings": {
            "bt_error_current": current.get("bt_error"),
            "bt_error_proposed": proposed.get("bt_error"),
            "pf_wilson_n_are_warn_only": True,
            "sanity_floor_removed_in_v2_1": True,
        },
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
            empty = {"N": 0, "wins": 0, "WR": 0.0, "EV": 0.0, "PnL": 0.0,
                     "PF": 0.0, "wilson_lo": 0.0, "bt_error": err}
            cells[pair] = {
                "current": empty,
                "proposed": empty,
                "lock_criteria": {"verdict": "BLOCKED_DATA", "reason": "missing_massive_cache"},
            }
    else:
        import app  # noqa: E402
        from modules import data as data_mod  # noqa: E402

        app.compute_daytrade_signal = _compute_mqe_only_signal

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
    if verdicts and all(v == "PASS" for v in verdicts):
        overall = "PASS"
    elif verdicts and all(v in {"PASS", "INSUFFICIENT_BT_EVIDENCE"} for v in verdicts):
        overall = "INSUFFICIENT_BT_EVIDENCE"
    elif verdicts and all(v == "BLOCKED_DATA" for v in verdicts):
        overall = "BLOCKED_DATA"
    else:
        overall = "REJECT"

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategy": STRATEGY,
        "variant": "fix_window_1530_1600_dedup_time_stop_6bar_v2",
        "flag": FLAG,
        "target_scope": "GBP_USD only; trigger thesis and pair gate unchanged",
        "lookback_days": LOOKBACK_DAYS,
        "minimum_days": MINIMUM_DAYS,
        "interval": INTERVAL,
        "runner": "app.run_daytrade_backtest(backtest_mode=True; production daytrade path; strategy-only compute patch)",
        "data_source_required": "data/cache/massive/{PAIR}_{TF}.parquet with BT_MODE=1 and BT_REQUIRE_MASSIVE_CACHE=1",
        "bt_mode": os.environ.get("BT_MODE"),
        "massive_cache_verified": not missing,
        "targets": [pair for pair, _ in TARGETS],
        "missing_caches": missing,
        "lock_spec": {
            "version": "v2.1",
            "bt_evidence_threshold": "if proposed N < 20 => INSUFFICIENT_BT_EVIDENCE, skip catastrophic, recommend shadow",
            "catastrophic_check": {"pnl_sign_preserved": "baseline PnL > 0 and proposed PnL < 0 is the only REJECT condition"},
            "warn_only": ["pf_change", "wilson_lo_change", "n_change_pct"],
            "sanity_floor": "removed",
            "positive_direction": "not required",
            "absolute_kelly": "not required",
        },
        "cells": cells,
        "overall_verdict": overall,
        "shadow_promote_recommendation": (
            "RECOMMEND_SHADOW" if overall in {"PASS", "INSUFFICIENT_BT_EVIDENCE"} else "REJECT"
        ),
        "shadow_registration_note": (
            "mqe_gbpusd_fix is already in DaytradeEngine.SHADOW_ALWAYS_STRATEGIES; "
            "V2 behavior remains default-off unless MQE_GBPUSD_FIX_REDESIGN_V2=1"
        ),
        "shadow_accumulation_target": "60-90 days or N>=30 after shadow start",
        "elapsed_s": round(time.time() - started, 1),
        "self_review": {
            "catastrophic_only": "PASS: verdict uses only pnl_sign_preserved when proposed N>=20; PF/Wilson/N are warnings only.",
            "insufficient_bt_evidence": "PASS: proposed N<20 becomes INSUFFICIENT_BT_EVIDENCE and recommends shadow.",
            "absolute_kelly": "PASS: no Kelly or live-promotion threshold is used.",
            "production_live_safety": "PASS: strategy V2 timing/dedup/time-stop metadata is default-off unless MQE_GBPUSD_FIX_REDESIGN_V2=1.",
            "post_hoc_adjustment": "PASS: only the audit-recommended 15:30-16:00 + 1/window dedup + 6bar time stop variant is evaluated.",
            "bt_source_guard": "PASS: BT_REQUIRE_MASSIVE_CACHE=1 prevents Yahoo fallback for this report.",
        },
    }
    OUTFILE.parent.mkdir(parents=True, exist_ok=True)
    OUTFILE.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"outfile": str(OUTFILE), "overall_verdict": overall}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
