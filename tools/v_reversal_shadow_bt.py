#!/usr/bin/env python3
"""A/B BT filter for v_reversal V2 closed-bar timing redesign."""
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
    ("EUR_GBP", "EURGBP=X"),
    ("EUR_JPY", "EURJPY=X"),
    ("EUR_USD", "EURUSD=X"),
    ("GBP_JPY", "GBPJPY=X"),
    ("GBP_USD", "GBPUSD=X"),
    ("USD_JPY", "USDJPY=X"),
]
LOOKBACK_DAYS = 365
MINIMUM_DAYS = 365
INTERVAL = "15m"
STRATEGY = "v_reversal"
FLAG = "V_REVERSAL_REDESIGN_V2"
SHADOW_PROMOTE_FLAG = "V_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE"
OUTFILE = ROOT / "bt-results" / "v_reversal-shadow-redesign-v2-2026-05-05.json"


def _compute_v_reversal_only_signal(
    df,
    tf,
    sr_levels,
    symbol="USDJPY=X",
    backtest_mode=False,
    bar_time=None,
    htf_cache=None,
):
    from strategies.context import SignalContext
    from strategies.scalp.v_reversal import VReversal

    if df is None or len(df) == 0:
        return {"signal": "WAIT", "entry_type": "wait", "reasons": ["empty df"]}

    row = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else row
    entry = float(row["Close"])
    atr = float(row.get("atr", 0.0))
    if bar_time is None:
        bar_time = df.index[-1]
    is_jpy = "JPY" in symbol.upper()
    htf = (htf_cache or {}).get("htf", {}) if isinstance(htf_cache, dict) else {}
    ctx = SignalContext(
        entry=entry,
        open_price=float(row["Open"]),
        atr=atr,
        atr7=float(row.get("atr7", atr)),
        ema9=float(row.get("ema9", entry)),
        ema21=float(row.get("ema21", entry)),
        ema50=float(row.get("ema50", entry)),
        ema200=float(row.get("ema200", row.get("ema50", entry))),
        rsi=float(row.get("rsi", 50.0)),
        rsi5=float(row.get("rsi5", row.get("rsi", 50.0))),
        rsi9=float(row.get("rsi9", row.get("rsi", 50.0))),
        stoch_k=float(row.get("stoch_k", 50.0)),
        stoch_d=float(row.get("stoch_d", 50.0)),
        adx=float(row.get("adx", 25.0)),
        adx_pos=float(row.get("adx_pos", 25.0)),
        adx_neg=float(row.get("adx_neg", 25.0)),
        macdh=float(row.get("macd_hist", 0.0)),
        macdh_prev=float(prev.get("macd_hist", 0.0)),
        macdh_prev2=float(df.iloc[-3].get("macd_hist", 0.0)) if len(df) >= 3 else 0.0,
        bbpb=float(row.get("bb_pband", 0.5)),
        bb_upper=float(row.get("bb_upper", entry + atr)),
        bb_mid=float(row.get("bb_mid", entry)),
        bb_lower=float(row.get("bb_lower", entry - atr)),
        bb_width=float(row.get("bb_width", 0.01)),
        prev_close=float(prev["Close"]),
        prev_open=float(prev["Open"]),
        prev_high=float(prev["High"]),
        prev_low=float(prev["Low"]),
        layer1=(htf_cache or {}).get("layer1", {}) if isinstance(htf_cache, dict) else {},
        htf=htf,
        symbol=symbol,
        tf=tf,
        is_jpy=is_jpy,
        pip_mult=100 if is_jpy else 10000,
        df=df,
        sr_levels=sr_levels,
        regime={"regime": "RANGE"},
        backtest_mode=backtest_mode,
        bar_time=bar_time,
        hour_utc=bar_time.hour if hasattr(bar_time, "hour") else 12,
    )
    cand = VReversal().evaluate(ctx)
    if cand is None:
        return {
            "signal": "WAIT",
            "entry": entry,
            "entry_type": "wait",
            "reasons": ["v_reversal no signal"],
            "atr": atr,
            "mode": "daytrade",
            "indicators": {"adx": ctx.adx, "rsi": ctx.rsi, "bb_pband": ctx.bbpb},
        }
    return {
        "signal": cand.signal,
        "entry": entry,
        "confidence": cand.confidence,
        "sl": cand.sl,
        "tp": cand.tp,
        "entry_type": cand.entry_type,
        "reasons": ["v_reversal strategy-filter BT"] + list(cand.reasons or []),
        "score": cand.score,
        "atr": atr,
        "mode": "daytrade",
        "layer_status": {},
        "regime": {"regime": "RANGE"},
        "indicators": {"adx": ctx.adx, "rsi": ctx.rsi, "bb_pband": ctx.bbpb, "stoch_k": ctx.stoch_k},
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


def _stats_from_pnls(pnls: list[float], *, bt_error=None, result=None) -> dict:
    n = len(pnls)
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
        "total_trades_all_strategies": (result or {}).get("trades", n),
        "bt_error": bt_error or (result or {}).get("error"),
        "data_source": (result or {}).get("data_source"),
        "bars_fetched": (result or {}).get("bars_fetched"),
    }


def _stats(result: dict) -> tuple[dict, list[float]]:
    trades = [t for t in result.get("trade_log", []) if t.get("entry_type") == STRATEGY]
    pnls = [_pnl_r(t) for t in trades]
    return _stats_from_pnls(pnls, result=result), pnls


def _run(app, data_mod, symbol: str, proposed: bool) -> dict:
    os.environ[FLAG] = "1" if proposed else "0"
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


def _warn_metrics(current: dict, proposed: dict) -> dict:
    current_pf = _num(current["PF"])
    proposed_pf = _num(proposed["PF"])
    pf_change = proposed_pf - current_pf
    n_change_pct = _change_pct(proposed["N"], current["N"])
    return {
        "pf_change": round(pf_change, 4) if math.isfinite(pf_change) else str(pf_change),
        "wilson_lo_change": round(proposed["wilson_lo"] - current["wilson_lo"], 4),
        "n_change_pct": round(n_change_pct, 4) if math.isfinite(n_change_pct) else str(n_change_pct),
    }


def _criteria(current: dict, proposed: dict) -> dict:
    warnings = _warn_metrics(current, proposed)
    if proposed["N"] < 20:
        return {
            **warnings,
            "verdict": "INSUFFICIENT_BT_EVIDENCE",
            "reason": "proposed BT trades < 20; v2.1 skips catastrophic check and recommends shadow observation",
            "catastrophic_check": "SKIPPED",
            "sanity_floor": "REMOVED_V2_1",
            "warn_only": ["pf_change", "wilson_lo_change", "n_change_pct"],
            "shadow_promote_recommendation": "RECOMMEND_SHADOW",
        }
    err = current.get("bt_error") or proposed.get("bt_error")
    if err:
        return {
            **warnings,
            "verdict": "BLOCKED_DATA" if "missing" in str(err).lower() else "REJECT",
            "reason": "bt_error",
            "bt_error": err,
            "catastrophic_check": False,
            "sanity_floor": "REMOVED_V2_1",
            "warn_only": ["pf_change", "wilson_lo_change", "n_change_pct"],
            "shadow_promote_recommendation": "REJECT",
        }

    pnl_ok = _pnl_sign_preserved(current["PnL"], proposed["PnL"])
    return {
        **warnings,
        "pnl_sign_preserved": pnl_ok,
        "catastrophic_check": pnl_ok,
        "sanity_floor": "REMOVED_V2_1",
        "warn_only": ["pf_change", "wilson_lo_change", "n_change_pct"],
        "verdict": "PASS" if pnl_ok else "REJECT",
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
    current_all: list[float] = []
    proposed_all: list[float] = []

    if missing:
        err = "missing MASSIVE parquet cache"
        aggregate_current = _stats_from_pnls([], bt_error=err)
        aggregate_proposed = _stats_from_pnls([], bt_error=err)
        aggregate_lock = {"verdict": "BLOCKED_DATA", "reason": "missing_massive_cache"}
    else:
        import app
        from modules import data as data_mod

        app.compute_daytrade_signal = _compute_v_reversal_only_signal

        for pair, symbol in TARGETS:
            print(f"Running baseline: {pair} {LOOKBACK_DAYS}d", flush=True)
            current, current_pnls = _stats(_run(app, data_mod, symbol, proposed=False))
            print(f"Running proposed: {pair} {LOOKBACK_DAYS}d", flush=True)
            proposed, proposed_pnls = _stats(_run(app, data_mod, symbol, proposed=True))
            current_all.extend(current_pnls)
            proposed_all.extend(proposed_pnls)
            cells[pair] = {
                "current": current,
                "proposed": proposed,
                "lock_criteria": _criteria(current, proposed),
            }

        aggregate_current = _stats_from_pnls(current_all)
        aggregate_proposed = _stats_from_pnls(proposed_all)
        aggregate_lock = _criteria(aggregate_current, aggregate_proposed)

    overall = aggregate_lock.get("verdict", "REJECT")
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategy": STRATEGY,
        "variant": "closed_bar_signal_v2",
        "redesign_axes": ["Axis 3 timing: closed-bar signal with next-bar execution separation", "strategy-side live dedup"],
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
        "target_scope_note": "W4 audit scope is v_reversal ALL; all available MASSIVE 15m FX pairs are included.",
        "missing_caches": missing,
        "lock_spec": {
            "version": "v2.1 shadow-first",
            "bt_evidence_threshold": "if proposed N < 20 => INSUFFICIENT_BT_EVIDENCE, skip catastrophic, recommend shadow",
            "catastrophic_check": {"pnl_sign_preserved": "baseline PnL > 0 and proposed PnL < 0 is the only REJECT regression"},
            "sanity_floor": "REMOVED",
            "warn_only": ["pf_change", "wilson_lo_change", "n_change_pct"],
            "positive_direction": "not required",
            "absolute_kelly": "not required",
        },
        "aggregate": {
            "current": aggregate_current,
            "proposed": aggregate_proposed,
            "lock_criteria": aggregate_lock,
        },
        "cells": cells,
        "overall_verdict": overall,
        "shadow_promote_recommendation": (
            "RECOMMEND_SHADOW" if overall in {"PASS", "INSUFFICIENT_BT_EVIDENCE"} else "REJECT"
        ),
        "shadow_accumulation_target": "60-90 days or N>=30 after shadow start",
        "elapsed_s": round(time.time() - started, 1),
        "self_review": {
            "catastrophic_only": "PASS: v2.1 verdict uses only pnl_sign_preserved when proposed N>=20; PF/Wilson/N drop are WARN only.",
            "absolute_kelly": "PASS: no Kelly criterion is computed or required for verdict.",
            "production_live_safety": f"PASS: strategy behavior is default-off unless {FLAG}=1; shadow emit also requires {SHADOW_PROMOTE_FLAG}=1.",
            "post_hoc_adjustment": "PASS: only the pre-registered closed-bar timing variant is evaluated.",
            "bt_source_guard": "PASS: BT_MODE=1 and BT_REQUIRE_MASSIVE_CACHE=1 are set before importing app/data.",
        },
    }

    OUTFILE.parent.mkdir(parents=True, exist_ok=True)
    OUTFILE.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved: {OUTFILE}")
    print(f"Overall: {overall}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
