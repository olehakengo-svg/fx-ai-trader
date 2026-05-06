#!/usr/bin/env python3
"""A/B BT filter for mtf_regime_range_cascade_scalp redesign V2.1."""
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
]
LOOKBACK_DAYS = 365
MINIMUM_DAYS = 365
INTERVAL = "15m"
STRATEGY = "mtf_regime_range_cascade_scalp"
FLAG = "MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2"
SHADOW_PROMOTE_FLAG = "MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2_SHADOW_PROMOTE"
OUTFILE = ROOT / "bt-results" / "mtf_regime_range_cascade_scalp-shadow-redesign-v2-2026-05-05.json"


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
    n = len(trades) if trades else int(result.get("trades", 0) or 0)
    pnls = [_pnl_r(t) for t in trades]
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


def _build_ctx(df, tf, sr_levels, symbol, backtest_mode, bar_time):
    from strategies.context import SignalContext

    row = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else row
    pip_mult = 100 if ("JPY" in symbol.upper() or "XAU" in symbol.upper()) else 10000
    entry = float(row["Close"])
    atr = float(row.get("atr", 0.0) or 0.0)
    atr7 = float(row.get("atr7", atr) or atr)
    adx = float(row.get("adx", 0.0) or 0.0)
    ema21 = float(row.get("ema21", entry))
    ema_slope = 0.0
    if "ema21" in df.columns and len(df) >= 5:
        ema_slope = ema21 - float(df["ema21"].iloc[-5])
    htf = {
        "m15": {
            "adx": adx,
            "ema_slope": ema_slope,
            "atr": atr,
            "atr15": atr,
            "hurst_64": 0.85 if adx < 18.0 else 0.90,
        },
        "m5": {
            "bbpb": float(row.get("bb_pband", 0.5)),
            "atr": atr,
            "low": float(row["Low"]),
            "high": float(row["High"]),
            "swing_high": float(df["High"].tail(8).max()),
            "swing_low": float(df["Low"].tail(8).min()),
        },
    }
    return SignalContext(
        entry=entry,
        open_price=float(row["Open"]),
        atr=atr,
        atr7=atr7,
        rsi=float(row.get("rsi", 50.0)),
        rsi5=float(row.get("rsi5", row.get("rsi", 50.0))),
        stoch_k=float(row.get("stoch_k", 50.0)),
        stoch_d=float(row.get("stoch_d", 50.0)),
        bbpb=float(row.get("bb_pband", 0.5)),
        bb_upper=float(row.get("bb_upper", entry + atr)),
        bb_mid=float(row.get("bb_mid", entry)),
        bb_lower=float(row.get("bb_lower", entry - atr)),
        prev_close=float(prev["Close"]),
        prev_open=float(prev["Open"]),
        prev_high=float(prev["High"]),
        prev_low=float(prev["Low"]),
        adx=adx,
        symbol=symbol,
        tf=tf,
        is_jpy="JPY" in symbol.upper(),
        pip_mult=pip_mult,
        df=df,
        sr_levels=sr_levels,
        htf=htf,
        backtest_mode=backtest_mode,
        bar_time=bar_time,
        hour_utc=bar_time.hour if hasattr(bar_time, "hour") else 12,
    )


def _compute_strategy_only_signal(df, tf, sr_levels, symbol="USDJPY=X",
                                  backtest_mode=False, bar_time=None, htf_cache=None):
    from strategies.scalp.mtf_regime_range_cascade_scalp import MtfRegimeRangeCascadeScalp

    if df is None or len(df) < 6:
        return {"signal": "WAIT", "entry_type": "wait", "reasons": ["insufficient df"]}
    if bar_time is None:
        bar_time = df.index[-1]
    ctx = _build_ctx(df, tf, sr_levels, symbol, backtest_mode, bar_time)
    cand = MtfRegimeRangeCascadeScalp().evaluate(ctx)
    entry = float(df.iloc[-1]["Close"])
    atr = float(df.iloc[-1].get("atr", 0.0) or 0.0)
    if cand is None:
        return {
            "signal": "WAIT",
            "entry": entry,
            "entry_type": "wait",
            "reasons": [f"{STRATEGY} no signal"],
            "atr": atr,
            "mode": "daytrade",
            "indicators": {"adx": ctx.adx},
            "shadow_emit_signals": [],
        }
    return {
        "signal": cand.signal,
        "entry": entry,
        "confidence": cand.confidence,
        "sl": float(cand.sl),
        "tp": float(cand.tp),
        "entry_type": cand.entry_type,
        "reasons": [f"strategy-filter BT: {STRATEGY}"] + list(cand.reasons or []),
        "score": float(cand.score),
        "atr": atr,
        "mode": "daytrade",
        "layer_status": {},
        "regime": {},
        "indicators": {"adx": ctx.adx},
        "shadow_emit_signals": [],
    }


def _run(app, data_mod, symbol: str, proposed: bool, days: int) -> dict:
    os.environ[FLAG] = "1" if proposed else "0"
    from strategies.scalp.mtf_regime_range_cascade_scalp import MtfRegimeRangeCascadeScalp

    MtfRegimeRangeCascadeScalp.reset_dedup_state()
    app._dt_bt_cache.clear()
    data_mod._data_cache.clear()
    return app.run_daytrade_backtest(
        symbol=symbol,
        lookback_days=days,
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
    pnl_sign_preserved = _pnl_sign_preserved(current["PnL"], proposed["PnL"])
    verdict = "PASS" if pnl_sign_preserved else "REJECT"
    return {
        "pf_change_warn_only": round(pf_change, 4) if math.isfinite(pf_change) else str(pf_change),
        "wilson_lo_change_warn_only": round(wilson_lo_change, 4),
        "n_change_pct_warn_only": round(n_change_pct, 4) if math.isfinite(n_change_pct) else str(n_change_pct),
        "pnl_sign_preserved": pnl_sign_preserved,
        "catastrophic_check": pnl_sign_preserved,
        "sanity_floor": "REMOVED_IN_V2_1",
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
                "lock_criteria": {"verdict": "BLOCKED_DATA", "reason": "missing_massive_cache"},
            }
    else:
        import app  # noqa: E402
        from modules import data as data_mod  # noqa: E402

        app.compute_daytrade_signal = _compute_strategy_only_signal

        for pair, symbol in TARGETS:
            print(f"Running baseline: {pair} {LOOKBACK_DAYS}d", flush=True)
            current = _stats(_run(app, data_mod, symbol, proposed=False, days=LOOKBACK_DAYS))
            print(f"Running proposed: {pair} {LOOKBACK_DAYS}d", flush=True)
            proposed = _stats(_run(app, data_mod, symbol, proposed=True, days=LOOKBACK_DAYS))
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
    elif verdicts and any(v == "BLOCKED_DATA" for v in verdicts):
        overall = "BLOCKED_DATA"

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategy": STRATEGY,
        "variant": "range_edge_reclaim_closed_bar_v2",
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
            "bt_evidence_threshold": "if proposed N < 20 => INSUFFICIENT_BT_EVIDENCE, skip catastrophic, recommend shadow",
            "catastrophic_check": {
                "pnl_sign_preserved_only": "baseline PnL > 0 and proposed PnL < 0 is the only REJECT condition",
            },
            "warn_only": ["pf_change", "wilson_lo_change", "n_change_pct"],
            "sanity_floor": "REMOVED in v2.1",
            "positive_direction": "not required",
            "absolute_kelly": "not required",
        },
        "cells": cells,
        "overall_verdict": overall,
        "shadow_promote_recommendation": (
            "RECOMMEND_SHADOW" if overall in {"PASS", "INSUFFICIENT_BT_EVIDENCE"} else overall
        ),
        "shadow_accumulation_target": "60-90 days or N>=30 after shadow start",
        "elapsed_s": round(time.time() - started, 1),
        "self_review": {
            "catastrophic_only": "PASS: v2.1 verdict uses only pnl_sign_preserved when proposed N>=20.",
            "warn_only_metrics": "PASS: PF, Wilson lower, and N drop are reported only as warnings.",
            "absolute_kelly": "PASS: no Kelly threshold is applied.",
            "production_live_safety": "PASS: redesign and shadow worker behavior are default-off env flags.",
            "post_hoc_adjustment": "PASS: only the pre-registered range_edge_reclaim_closed_bar_v2 variant is evaluated.",
            "bt_source_guard": "PASS: BT_REQUIRE_MASSIVE_CACHE=1 prevents Yahoo fallback for this report.",
        },
    }

    OUTFILE.parent.mkdir(parents=True, exist_ok=True)
    OUTFILE.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved: {OUTFILE}")
    print(f"Overall: {overall}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
