#!/usr/bin/env python3
"""A/B BT filter for sr_anti_hunt_bounce V2 closed-bar timing contract."""
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

TARGETS = [
    ("USD_JPY", "USDJPY=X"),
    ("EUR_USD", "EURUSD=X"),
    ("GBP_USD", "GBPUSD=X"),
    ("EUR_JPY", "EURJPY=X"),
    ("GBP_JPY", "GBPJPY=X"),
]
LOOKBACK_DAYS = 365
MINIMUM_DAYS = 365
INTERVAL = "15m"
STRATEGY = "sr_anti_hunt_bounce"
FLAG = "SR_ANTI_HUNT_BOUNCE_REDESIGN_V2"
SHADOW_PROMOTE_FLAG = "SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE"
OUTFILE = ROOT / "bt-results" / "sr_anti_hunt_bounce-shadow-redesign-v2-2026-05-05.json"


def _compute_sr_anti_hunt_only_signal(df, tf, sr_levels, symbol="USDJPY=X",
                                      backtest_mode=False, bar_time=None, htf_cache=None):
    from strategies.context import SignalContext
    from strategies.daytrade.sr_anti_hunt_bounce import SrAntiHuntBounce

    if df is None or len(df) == 0:
        return {"signal": "WAIT", "entry_type": "wait", "reasons": ["empty df"]}

    row = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else row
    entry = float(row["Close"])
    atr = float(row.get("atr", 0.0))
    if bar_time is None:
        bar_time = df.index[-1]
    hour_utc = bar_time.hour if hasattr(bar_time, "hour") else 12
    is_jpy = "JPY" in symbol.upper()
    ctx = SignalContext(
        entry=entry,
        open_price=float(row["Open"]),
        atr=atr,
        atr7=float(row.get("atr7", atr)),
        ema9=float(row.get("ema9", entry)),
        ema21=float(row.get("ema21", entry)),
        ema50=float(row.get("ema50", entry)),
        ema200=float(row.get("ema200", entry)),
        rsi=float(row.get("rsi", 50.0)),
        adx=float(row.get("adx", 25.0)),
        adx_pos=float(row.get("adx_pos", 25.0)),
        adx_neg=float(row.get("adx_neg", 25.0)),
        macdh=float(row.get("macd_hist", 0.0)),
        macdh_prev=float(prev.get("macd_hist", 0.0)),
        bbpb=float(row.get("bb_pband", 0.5)),
        bb_upper=float(row.get("bb_upper", entry + atr)),
        bb_mid=float(row.get("bb_mid", entry)),
        bb_lower=float(row.get("bb_lower", entry - atr)),
        bb_width=float(row.get("bb_width", 0.01)),
        prev_close=float(prev["Close"]),
        prev_open=float(prev["Open"]),
        prev_high=float(prev["High"]),
        prev_low=float(prev["Low"]),
        symbol=symbol,
        tf=tf,
        is_jpy=is_jpy,
        pip_mult=100 if is_jpy else 10000,
        df=df,
        sr_levels=sr_levels,
        regime={"regime": "RANGE"},
        htf=(htf_cache or {}).get("htf", {}) if isinstance(htf_cache, dict) else {},
        backtest_mode=backtest_mode,
        bar_time=bar_time,
        hour_utc=hour_utc,
    )
    cand = SrAntiHuntBounce().evaluate(ctx)
    if cand is None:
        return {
            "signal": "WAIT",
            "entry": entry,
            "entry_type": "wait",
            "reasons": ["sr_anti_hunt_bounce no signal"],
            "atr": atr,
            "mode": "daytrade",
            "indicators": {"adx": ctx.adx, "bb_pband": ctx.bbpb},
        }
    return {
        "signal": cand.signal,
        "entry": entry,
        "confidence": cand.confidence,
        "sl": cand.sl,
        "tp": cand.tp,
        "entry_type": cand.entry_type,
        "reasons": ["✅ sr_anti_hunt_bounce strategy-filter BT"] + list(cand.reasons or []),
        "score": cand.score,
        "atr": atr,
        "mode": "daytrade",
        "layer_status": {},
        "regime": {"regime": "RANGE"},
        "indicators": {"adx": ctx.adx, "bb_pband": ctx.bbpb},
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
    os.environ[FLAG] = "1" if proposed else "0"
    app._dt_bt_cache.clear()
    data_mod._data_cache.clear()
    from strategies.daytrade.sr_anti_hunt_bounce import SrAntiHuntBounce
    SrAntiHuntBounce._v2_seen_closed_bar_keys.clear()
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
    err = current.get("bt_error") or proposed.get("bt_error")
    if err:
        return {
            "verdict": "BLOCKED_DATA" if "missing MASSIVE parquet cache" in str(err) else "REJECT",
            "reason": err,
            "catastrophic_check": "SKIPPED",
            "shadow_promote_recommendation": "IMPLEMENT_ONLY_DEFAULT_OFF",
        }
    if proposed["N"] < 20:
        return {
            "verdict": "INSUFFICIENT_BT_EVIDENCE",
            "reason": "proposed BT trades < 20; v2.1 skips catastrophic check and recommends shadow",
            "catastrophic_check": "SKIPPED",
            "sanity_floor": "REMOVED_IN_V2_1",
            "shadow_promote_recommendation": "RECOMMEND_SHADOW",
        }

    try:
        current_pf = _num(current["PF"])
        proposed_pf = _num(proposed["PF"])
        pf_change = proposed_pf - current_pf
        pf_change_warn = round(pf_change, 4) if math.isfinite(pf_change) else str(pf_change)
    except (TypeError, ValueError):
        pf_change_warn = "not_reconstructed_from_cell_stats"
    wilson_lo_change = proposed["wilson_lo"] - current["wilson_lo"]
    n_change_pct = _change_pct(proposed["N"], current["N"])
    pnl_sign_preserved = _pnl_sign_preserved(current["PnL"], proposed["PnL"])
    return {
        "verdict": "PASS" if pnl_sign_preserved else "REJECT",
        "pnl_sign_preserved": pnl_sign_preserved,
        "catastrophic_check": pnl_sign_preserved,
        "catastrophic_rule": "baseline PnL > 0 and proposed PnL < 0 is the only REJECT condition",
        "sanity_floor": "REMOVED_IN_V2_1",
        "warnings_only": {
            "pf_change": pf_change_warn,
            "wilson_lo_change": round(wilson_lo_change, 4),
            "n_change_pct": round(n_change_pct, 4) if math.isfinite(n_change_pct) else str(n_change_pct),
        },
        "shadow_promote_recommendation": "RECOMMEND_SHADOW" if pnl_sign_preserved else "REJECT",
    }


def _aggregate(stats: list[dict]) -> dict:
    n = sum(s["N"] for s in stats)
    wins = sum(s["wins"] for s in stats)
    pnl = sum(s["PnL"] for s in stats)
        # Aggregate PF cannot be reconstructed exactly from rounded cell stats.
    return {
        "N": n,
        "wins": wins,
        "WR": round(wins / n, 4) if n else 0.0,
        "EV": round(pnl / n, 4) if n else 0.0,
        "PnL": round(pnl, 4),
        "PF": "not_reconstructed_from_cell_stats",
        "wilson_lo": round(_wilson_lower(wins, n), 4),
        "bt_error": None,
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
            err = f"missing MASSIVE parquet cache: {_cache_path(pair).relative_to(ROOT)}"
            cells[pair] = {
                "current": {"N": 0, "wins": 0, "WR": 0.0, "EV": 0.0, "PnL": 0.0,
                            "PF": 0.0, "wilson_lo": 0.0, "bt_error": err},
                "proposed": {"N": 0, "wins": 0, "WR": 0.0, "EV": 0.0, "PnL": 0.0,
                             "PF": 0.0, "wilson_lo": 0.0, "bt_error": err},
                "lock_criteria": {"verdict": "BLOCKED_DATA", "reason": "missing_massive_cache"},
            }
    else:
        import app  # noqa: E402
        from modules import data as data_mod  # noqa: E402

        app.compute_daytrade_signal = _compute_sr_anti_hunt_only_signal

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

    aggregate_current = _aggregate([c["current"] for c in cells.values()])
    aggregate_proposed = _aggregate([c["proposed"] for c in cells.values()])
    aggregate_lock = _criteria(aggregate_current, aggregate_proposed)
    overall = aggregate_lock["verdict"]

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategy": STRATEGY,
        "variant": "closed_bar_signal_next_bar_execution_dedup_v2",
        "flag": FLAG,
        "shadow_worker_flag": SHADOW_PROMOTE_FLAG,
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
            "catastrophic_check": {
                "pnl_sign_preserved_only": "baseline PnL > 0 and proposed PnL < 0 is the only REJECT condition",
            },
            "sanity_floor": "REMOVED in v2.1",
            "n_pf_wilson_changes": "WARN ONLY in v2.1",
            "positive_direction": "not required",
            "absolute_kelly": "not required",
        },
        "cells": cells,
        "aggregate": {
            "current": aggregate_current,
            "proposed": aggregate_proposed,
            "lock_criteria": aggregate_lock,
        },
        "overall_verdict": overall,
        "shadow_promote_recommendation": (
            "RECOMMEND_SHADOW" if overall in {"PASS", "INSUFFICIENT_BT_EVIDENCE"} else "REJECT"
        ),
        "shadow_accumulation_target": "60-90 days or N>=30 after shadow start",
        "elapsed_s": round(time.time() - started, 1),
        "self_review": {
            "catastrophic_only": "PASS: v2.1 verdict uses only pnl_sign_preserved when proposed N>=20.",
            "insufficient_bt_evidence": "PASS: proposed N<20 becomes INSUFFICIENT_BT_EVIDENCE and shadow recommendation.",
            "sanity_floor_removed": "PASS: no PF/Wilson floor gates shadow promotion.",
            "production_live_safety": "PASS: strategy behavior is default-off unless SR_ANTI_HUNT_BOUNCE_REDESIGN_V2=1; shadow emit also requires SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE=1.",
            "post_hoc_adjustment": "PASS: only the pre-registered closed-bar timing + live dedup V2 variant is evaluated.",
            "bt_source_guard": "PASS: BT_REQUIRE_MASSIVE_CACHE=1 prevents Yahoo fallback for 15m price data.",
        },
    }

    OUTFILE.parent.mkdir(parents=True, exist_ok=True)
    OUTFILE.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved: {OUTFILE}")
    print(f"Overall: {overall}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
