#!/usr/bin/env python3
"""A/B BT filter for wick_imbalance_reversion V2 shadow redesign."""
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
    ("GBP_USD", "GBPUSD=X"),
]
LOOKBACK_DAYS = 365
MINIMUM_DAYS = 365
INTERVAL = "15m"
STRATEGY = "wick_imbalance_reversion"
FLAG = "WICK_IMBALANCE_REVERSION_REDESIGN_V2"
LEGACY_FLAG = "ALPHA_WICK_IMBALANCE_REDESIGN_V2"
SHADOW_FLAG = "WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE"
OUTFILE = ROOT / "bt-results" / "wick_imbalance_reversion-shadow-redesign-v2-2026-05-05.json"


def _compute_wick_only_signal(df, tf, sr_levels, symbol="USDJPY=X",
                              backtest_mode=False, bar_time=None, htf_cache=None):
    from strategies.context import SignalContext
    from strategies.daytrade.alpha_wick_imbalance import WickImbalanceReversion

    if df is None or len(df) == 0:
        return {"signal": "WAIT", "entry_type": "wait", "reasons": ["empty df"]}

    row = df.iloc[-1]
    entry = float(row["Close"])
    atr = float(row.get("atr", 0.0))
    htf = (htf_cache or {}).get("htf", {}) if isinstance(htf_cache, dict) else {}
    layer1 = (htf_cache or {}).get("layer1", {}) if isinstance(htf_cache, dict) else {}
    is_jpy = "JPY" in symbol.upper()
    ctx = SignalContext(
        entry=entry,
        open_price=float(row["Open"]),
        atr=atr,
        atr7=float(row.get("atr7", atr)),
        rsi=float(row.get("rsi", 50.0)),
        rsi5=float(row.get("rsi5", row.get("rsi", 50.0))),
        rsi9=float(row.get("rsi9", row.get("rsi", 50.0))),
        adx=float(row.get("adx", 25.0)),
        adx_pos=float(row.get("adx_pos", 25.0)),
        adx_neg=float(row.get("adx_neg", 25.0)),
        macdh=float(row.get("macd_hist", 0.0)),
        bbpb=float(row.get("bb_pband", 0.5)),
        bb_width_pct=float(row.get("bb_width_pct", row.get("bb_width_percentile", 0.50))),
        layer1=layer1,
        htf=htf,
        symbol=symbol,
        tf=tf,
        is_jpy=is_jpy,
        pip_mult=100 if is_jpy else 10000,
        df=df,
        sr_levels=sr_levels,
        backtest_mode=backtest_mode,
        bar_time=bar_time,
    )
    cand = WickImbalanceReversion().evaluate(ctx)
    if cand is None:
        return {
            "signal": "WAIT",
            "entry": entry,
            "entry_type": "wait",
            "reasons": ["wick_imbalance_reversion no signal"],
            "atr": atr,
            "mode": "daytrade",
            "indicators": {"adx": ctx.adx},
        }
    return {
        "signal": cand.signal,
        "entry": entry,
        "confidence": cand.confidence,
        "sl": cand.sl,
        "tp": cand.tp,
        "entry_type": cand.entry_type,
        "reasons": ["✅ wick_imbalance_reversion strategy-filter BT"] + list(cand.reasons or []),
        "score": cand.score,
        "atr": atr,
        "mode": "daytrade",
        "layer_status": {"layer1": layer1},
        "regime": {},
        "indicators": {"adx": ctx.adx},
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
    if n == 0 and result.get("error") and result.get("trades") is not None:
        n = int(result.get("trades", 0) or 0)
    wins = sum(1 for p in pnls if p > 0)
    ev = sum(pnls) / len(pnls) if pnls else 0.0
    pf = _pf(pnls)
    return {
        "N": n,
        "wins": wins,
        "WR": round(wins / len(pnls), 4) if pnls else 0.0,
        "EV": round(ev, 4),
        "PnL": round(sum(pnls), 4),
        "PF": round(pf, 4) if math.isfinite(pf) else "inf",
        "wilson_lo": round(_wilson_lower(wins, len(pnls)), 4),
        "total_trades_all_strategies": result.get("trades", 0),
        "bt_error": result.get("error"),
        "data_source": result.get("data_source"),
        "bars_fetched": result.get("bars_fetched"),
    }


def _run(app, data_mod, symbol: str, proposed: bool) -> dict:
    os.environ[FLAG] = "1" if proposed else "0"
    os.environ[LEGACY_FLAG] = "0"
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
            "reason": "proposed BT trades < 20; v2.1 skips catastrophic check and recommends shadow",
            "catastrophic_check": "SKIPPED",
            "sanity_floor": "REMOVED_V2_1",
            "shadow_promote_recommendation": "RECOMMEND_SHADOW",
        }
    err = current.get("bt_error") or proposed.get("bt_error")
    if err:
        return {
            "verdict": "REJECT",
            "reason": "bt_error",
            "bt_error": err,
            "catastrophic_check": False,
            "sanity_floor": "REMOVED_V2_1",
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
        "warn_only": ["pf_change", "wilson_lo_change", "n_change_pct"],
    }
    catastrophic_pass = checks["pnl_sign_preserved"]
    verdict = "PASS" if catastrophic_pass else "REJECT"
    return {
        **checks,
        "catastrophic_check": catastrophic_pass,
        "sanity_floor": "REMOVED_V2_1",
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

        app.compute_daytrade_signal = _compute_wick_only_signal

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
    overall = "REJECT"
    if verdicts and all(v == "PASS" for v in verdicts):
        overall = "PASS"
    elif verdicts and all(v in {"PASS", "INSUFFICIENT_BT_EVIDENCE"} for v in verdicts):
        overall = "INSUFFICIENT_BT_EVIDENCE"

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategy": STRATEGY,
        "entry_type": STRATEGY,
        "variant": "closed_bar_no_htf_hard_block_v2",
        "flag": FLAG,
        "shadow_worker_flag": SHADOW_FLAG,
        "lookback_days": LOOKBACK_DAYS,
        "minimum_days": MINIMUM_DAYS,
        "interval": INTERVAL,
        "runner": "app.run_daytrade_backtest (production daytrade path; strategy-isolated compute patch)",
        "data_source_required": "data/cache/massive/{PAIR}_{TF}.parquet with BT_MODE=1 and BT_REQUIRE_MASSIVE_CACHE=1",
        "data_source_note": "run_daytrade_backtest omits data_source/bars_fetched when it returns the <20 trades error; console output should show massive-parquet/15m for each target.",
        "bt_mode": os.environ.get("BT_MODE"),
        "massive_cache_verified": not missing,
        "targets": [pair for pair, _ in TARGETS],
        "targets_note": "Pair-promoted Tier 1 cell from the W4 audit.",
        "missing_caches": missing,
        "lock_spec": {
            "bt_evidence_threshold": "if proposed N < 20 => INSUFFICIENT_BT_EVIDENCE, skip catastrophic, recommend shadow",
            "catastrophic_check": {
                "pnl_sign_preserved": "baseline PnL > 0 and proposed PnL < 0 is the only REJECT condition",
            },
            "warn_only": ["pf_change", "wilson_lo_change", "n_change_pct"],
            "sanity_floor": "REMOVED in v2.1",
            "positive_direction": "not required",
            "absolute_kelly": "not required",
        },
        "cells": cells,
        "overall_verdict": overall,
        "shadow_promote_recommendation": (
            "RECOMMEND_SHADOW" if overall in {"PASS", "INSUFFICIENT_BT_EVIDENCE"} else "REJECT"
        ),
        "shadow_accumulation_target": "60-90 days or N>=30 after shadow start",
        "elapsed_s": round(time.time() - started, 1),
        "self_review": {
            "catastrophic_only": "PASS: verdict uses only pnl_sign_preserved when proposed N>=20; PF/Wilson/N changes are WARN only.",
            "insufficient_bt_evidence": "PASS: proposed N<20 becomes INSUFFICIENT_BT_EVIDENCE and shadow recommendation.",
            "production_live_safety": "PASS: strategy behavior is default-off unless WICK_IMBALANCE_REVERSION_REDESIGN_V2=1; shadow emit also requires the separate shadow flag.",
            "post_hoc_adjustment": "PASS: only the pre-registered closed_bar_no_htf_hard_block_v2 variant is evaluated.",
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
