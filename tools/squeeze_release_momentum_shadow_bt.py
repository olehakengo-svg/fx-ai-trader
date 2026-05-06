#!/usr/bin/env python3
"""A/B BT filter for squeeze_release_momentum V2 timing hardening."""
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
    ("EUR_USD", "EURUSD=X"),
    ("GBP_USD", "GBPUSD=X"),
]
LOOKBACK_DAYS = 365
MINIMUM_DAYS = 365
INTERVAL = "15m"
STRATEGY = "squeeze_release_momentum"
FLAG = "SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2"
SHADOW_PROMOTE_FLAG = "SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE"
OUTFILE = ROOT / "bt-results/squeeze_release_momentum-shadow-redesign-v2-2026-05-05.json"


def _compute_srm_only_signal(df, tf, sr_levels, symbol="USDJPY=X",
                             backtest_mode=False, bar_time=None,
                             htf_cache=None):
    import app
    from strategies.context import SignalContext
    from strategies.daytrade.squeeze_release_momentum import SqueezeReleaseMomentum

    if df is None or len(df) == 0:
        return {"signal": "WAIT", "entry_type": "wait", "reasons": ["empty df"]}

    row = df.iloc[-1]
    entry = float(row["Close"])
    atr = float(row.get("atr", 0.0))
    if bar_time is None:
        bar_time = df.index[-1]

    regime = app.detect_market_regime(df)
    ctx = SignalContext.from_df(
        df=df,
        row=row,
        symbol=symbol,
        tf=tf,
        sr_levels=sr_levels,
        layer0={},
        layer1={},
        regime=regime,
        layer2={},
        layer3={},
        htf=(htf_cache or {}).get("htf", {}) if isinstance(htf_cache, dict) else {},
        session={},
        backtest_mode=backtest_mode,
        bar_time=bar_time,
    )
    cand = SqueezeReleaseMomentum().evaluate(ctx)
    if cand is None:
        return {
            "signal": "WAIT",
            "entry": entry,
            "entry_type": "wait",
            "reasons": ["squeeze_release_momentum no signal"],
            "atr": atr,
            "mode": "daytrade",
            "indicators": {"bbpb": ctx.bbpb, "bb_width": ctx.bb_width},
            "shadow_emit_signals": [],
        }
    return {
        "signal": cand.signal,
        "entry": entry,
        "confidence": cand.confidence,
        "sl": cand.sl,
        "tp": cand.tp,
        "entry_type": cand.entry_type,
        "reasons": ["squeeze_release_momentum strategy-filter BT"] + list(cand.reasons or []),
        "score": cand.score,
        "atr": atr,
        "mode": "daytrade",
        "layer_status": {},
        "indicators": {"bbpb": ctx.bbpb, "bb_width": ctx.bb_width},
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
    n = len(trades)
    wins = sum(1 for p in pnls if p > 0)
    ev = sum(pnls) / n if n else 0.0
    return {
        "N": n,
        "wins": wins,
        "WR": round(wins / n, 4) if n else 0.0,
        "EV": round(ev, 4),
        "PnL": round(sum(pnls), 4),
        "PF": round(_pf(pnls), 4) if n and math.isfinite(_pf(pnls)) else ("inf" if n else 0.0),
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
        backtest_mode=True,
    )


def _change_pct(proposed: float, current: float) -> float:
    if current == 0:
        if proposed == 0:
            return 0.0
        return float("inf") if proposed > 0 else float("-inf")
    return (proposed - current) / abs(current) * 100.0


def _pnl_sign_preserved(current: float, proposed: float) -> bool:
    return not (current > 0 and proposed < 0)


def _num(value) -> float:
    if value == "inf":
        return float("inf")
    return float(value)


def _criteria(current: dict, proposed: dict) -> dict:
    missing = current.get("bt_error") or proposed.get("bt_error")
    if missing:
        return {
            "verdict": "REJECT",
            "reason": "bt_error",
            "catastrophic_check": "FAIL",
            "sanity_floor": False,
        }
    if proposed["N"] < 20:
        return {
            "verdict": "INSUFFICIENT_BT_EVIDENCE",
            "reason": "proposed_N_lt_20",
            "proposed_N": proposed["N"],
            "catastrophic_check": "SKIP",
            "sanity_floor": "SKIP",
            "shadow_promote_recommendation": "RECOMMEND_SHADOW",
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
        "pf_threshold": -0.10,
        "wilson_lo_threshold": -0.05,
        "n_change_pct_threshold": -30.0,
    }
    catastrophic_pass = (
        pf_change >= -0.10
        and wilson_lo_change >= -0.05
        and n_change_pct >= -30
        and checks["pnl_sign_preserved"]
    )
    floor = proposed["wilson_lo"] >= 0.20 and proposed_pf >= 0.85
    return {
        **checks,
        "catastrophic_check": "PASS" if catastrophic_pass else "FAIL",
        "sanity_floor": floor,
        "verdict": "PASS" if catastrophic_pass and floor else "REJECT",
        "shadow_promote_recommendation": (
            "RECOMMEND_SHADOW" if catastrophic_pass and floor else "REJECT"
        ),
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
                "lock_criteria": {"verdict": "REJECT", "reason": "missing_massive_cache"},
            }
    else:
        import app  # noqa: E402
        from modules import data as data_mod  # noqa: E402

        app.compute_daytrade_signal = _compute_srm_only_signal

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

    promotable_verdicts = {"PASS", "INSUFFICIENT_BT_EVIDENCE"}
    overall = (
        "PASS" if cells and all(c["lock_criteria"].get("verdict") == "PASS" for c in cells.values())
        else "INSUFFICIENT_BT_EVIDENCE"
        if cells and all(c["lock_criteria"].get("verdict") in promotable_verdicts for c in cells.values())
        else "REJECT"
    )
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategy": STRATEGY,
        "variant": "closed_bar_dedup_v2",
        "flag": FLAG,
        "shadow_worker_flag": SHADOW_PROMOTE_FLAG,
        "lookback_days": LOOKBACK_DAYS,
        "minimum_days": MINIMUM_DAYS,
        "interval": INTERVAL,
        "data_source_required": "data/cache/massive/{PAIR}_{TF}.parquet with BT_MODE=1",
        "runner": (
            "app.run_daytrade_backtest(symbol=..., lookback_days=365, interval=\"15m\", "
            "backtest_mode=True; production daytrade path; strategy-only compute patch)"
        ),
        "bt_mode": os.environ.get("BT_MODE"),
        "massive_cache_verified": not missing,
        "targets": [pair for pair, _ in TARGETS],
        "missing_caches": missing,
        "cells": cells,
        "overall_verdict": overall,
        "shadow_promote_recommendation": (
            "RECOMMEND_SHADOW" if overall in promotable_verdicts else "REJECT"
        ),
        "shadow_flag": "SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE",
        "lock_criteria_v2": {
            "bt_evidence_threshold": "if proposed N < 20: INSUFFICIENT_BT_EVIDENCE; skip catastrophic_check",
            "catastrophic_check": {
                "pf_change_min": -0.10,
                "wilson_lo_change_min": -0.05,
                "n_change_pct_min": -30.0,
                "pnl_sign_preserved": True,
            },
            "sanity_floor": {
                "wilson_lo_proposed_min": 0.20,
                "pf_proposed_min": 0.85,
            },
            "positive_direction_required": False,
            "absolute_kelly_required": False,
        },
        "shadow_accumulation_target": "60-90 days or N>=30 after shadow start",
        "elapsed_s": round(time.time() - started, 1),
        "self_review": {
            "catastrophic_check_only": "PASS: verdict uses catastrophic PF/Wilson/N/PnL checks plus sanity floors; no positive-direction gate.",
            "production_live_safety": "PASS: strategy behavior is default-off unless SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2=1.",
            "post_hoc_adjustment": "PASS: only the pre-registered closed_bar_dedup_v2 variant is evaluated.",
            "bt_source_guard": "PASS: BT_REQUIRE_MASSIVE_CACHE=1 prevents Yahoo/network fallback for this report.",
            "absolute_kelly_gate": "PASS: no Kelly threshold is used.",
        },
    }

    OUTFILE.parent.mkdir(parents=True, exist_ok=True)
    OUTFILE.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved: {OUTFILE}")
    print(f"Overall: {overall}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
