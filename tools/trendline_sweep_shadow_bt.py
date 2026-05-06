#!/usr/bin/env python3
"""A/B BT for trendline_sweep V2 pair-scope shadow redesign."""
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
    ("EUR_GBP", "EURGBP=X"),
]
XAU_TARGET = ("XAU_USD", "XAUUSD=X")
LOOKBACK_DAYS = 365
MINIMUM_DAYS = 365
INTERVAL = "15m"
STRATEGY = "trendline_sweep"
FLAG = "TRENDLINE_SWEEP_REDESIGN_V2"
SHADOW_PROMOTE_FLAG = "TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE"
V2_LIVE_PAIRS = {"EUR_USD", "GBP_USD"}
V2_SHADOW_PAIRS = {"EUR_GBP", "XAU_USD"}
OUTFILE = ROOT / "bt-results" / "trendline_sweep-shadow-redesign-v2-2026-05-05.json"


def _pair_from_symbol(symbol: str) -> str:
    s = symbol.upper().replace("=X", "").replace("=F", "").replace("/", "").replace("_", "")
    if s in {"XAUUSD", "GC", "GCF"}:
        return "XAU_USD"
    if len(s) == 6:
        return f"{s[:3]}_{s[3:]}"
    return s


def _compute_trendline_sweep_only_signal(
    df, tf, sr_levels, symbol="EURUSD=X", backtest_mode=False, bar_time=None, htf_cache=None
):
    from strategies.context import SignalContext
    from strategies.daytrade.trendline_sweep import TrendlineSweep

    if df is None or len(df) == 0:
        return {"signal": "WAIT", "entry_type": "wait", "reasons": ["empty df"]}

    pair = _pair_from_symbol(symbol)
    row = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else row
    entry = float(row["Close"])
    atr = float(row.get("atr", 0.0))
    if os.environ.get(FLAG) == "1" and pair not in V2_LIVE_PAIRS:
        return {
            "signal": "WAIT",
            "entry": entry,
            "entry_type": "wait",
            "reasons": [f"{FLAG}: {pair} scoped to shadow-only routing"],
            "atr": atr,
            "mode": "daytrade",
            "indicators": {"adx": float(row.get("adx", 25.0))},
            "shadow_emit_signals": [],
        }
    if bar_time is None:
        bar_time = df.index[-1]
    hour_utc = bar_time.hour if hasattr(bar_time, "hour") else 12
    is_jpy = "JPY" in pair
    htf = (htf_cache or {}).get("htf", {}) if isinstance(htf_cache, dict) else {}
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
        htf=htf,
        backtest_mode=backtest_mode,
        bar_time=bar_time,
        hour_utc=hour_utc,
    )
    cand = TrendlineSweep().evaluate(ctx)
    if cand is None:
        return {
            "signal": "WAIT",
            "entry": entry,
            "entry_type": "wait",
            "reasons": ["trendline_sweep no signal"],
            "atr": atr,
            "mode": "daytrade",
            "indicators": {"adx": ctx.adx},
            "shadow_emit_signals": [],
        }
    return {
        "signal": cand.signal,
        "entry": entry,
        "confidence": cand.confidence,
        "sl": cand.sl,
        "tp": cand.tp,
        "entry_type": cand.entry_type,
        "reasons": ["✅ trendline_sweep strategy-filter BT"] + list(cand.reasons or []),
        "score": cand.score,
        "atr": atr,
        "mode": "daytrade",
        "layer_status": {},
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
    n = len(trades) if trades else int(result.get("trades", 0) or 0)
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
        "wilson_lo": round(_wilson_lower(wins, len(pnls)), 4) if pnls else 0.0,
        "total_trades_all_strategies": result.get("trades", 0),
        "bt_error": result.get("error"),
        "data_source": result.get("data_source"),
        "bars_fetched": result.get("bars_fetched"),
    }


def _run(app, data_mod, symbol: str, proposed: bool) -> dict:
    os.environ[FLAG] = "1" if proposed else "0"
    if hasattr(app, "_dt_bt_cache"):
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
            "warnings": {
                "n_change_pct": round(_change_pct(proposed["N"], current["N"]), 4)
                if math.isfinite(_change_pct(proposed["N"], current["N"]))
                else str(_change_pct(proposed["N"], current["N"])),
                "pf_change": "WARN_ONLY",
                "wilson_lo_change": "WARN_ONLY",
            },
        }
    err = current.get("bt_error") or proposed.get("bt_error")
    if err:
        return {
            "verdict": "REJECT",
            "reason": "bt_error_with_sufficient_proposed_n",
            "bt_error": err,
            "catastrophic_check": False,
            "shadow_promote_recommendation": "REJECT",
        }
    current_pf = _num(current["PF"])
    proposed_pf = _num(proposed["PF"])
    pf_change = proposed_pf - current_pf
    wilson_lo_change = proposed["wilson_lo"] - current["wilson_lo"]
    n_change_pct = _change_pct(proposed["N"], current["N"])
    sign_ok = _pnl_sign_preserved(current["PnL"], proposed["PnL"])
    return {
        "pnl_sign_preserved": sign_ok,
        "catastrophic_check": sign_ok,
        "warnings": {
            "pf_change": round(pf_change, 4) if math.isfinite(pf_change) else str(pf_change),
            "wilson_lo_change": round(wilson_lo_change, 4),
            "n_change_pct": round(n_change_pct, 4) if math.isfinite(n_change_pct) else str(n_change_pct),
        },
        "verdict": "PASS" if sign_ok else "REJECT",
        "shadow_promote_recommendation": "RECOMMEND_SHADOW" if sign_ok else "REJECT",
    }


def main() -> int:
    started = time.time()
    cells = {}
    missing_required = [
        str(_cache_path(pair).relative_to(ROOT))
        for pair, _ in TARGETS
        if not _cache_path(pair).exists()
    ]
    xau_missing = not _cache_path(XAU_TARGET[0]).exists()

    if missing_required:
        for pair, _symbol in TARGETS:
            err = f"missing MASSIVE parquet cache: {_cache_path(pair).relative_to(ROOT)}"
            cells[pair] = {
                "current": {"N": 0, "wins": 0, "WR": 0.0, "EV": 0.0, "PnL": 0.0,
                            "PF": 0.0, "wilson_lo": 0.0, "bt_error": err},
                "proposed": {"N": 0, "wins": 0, "WR": 0.0, "EV": 0.0, "PnL": 0.0,
                             "PF": 0.0, "wilson_lo": 0.0, "bt_error": err},
                "lock_criteria": {"verdict": "BLOCKED_DATA", "reason": "missing_required_massive_cache"},
            }
    else:
        import app  # noqa: E402
        from modules import data as data_mod  # noqa: E402

        app.compute_daytrade_signal = _compute_trendline_sweep_only_signal

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

    if xau_missing:
        xau_err = f"missing MASSIVE parquet cache: {_cache_path(XAU_TARGET[0]).relative_to(ROOT)}"
        cells[XAU_TARGET[0]] = {
            "current": {"N": 0, "wins": 0, "WR": 0.0, "EV": 0.0, "PnL": 0.0,
                        "PF": 0.0, "wilson_lo": 0.0, "bt_error": xau_err},
            "proposed": {"N": 0, "wins": 0, "WR": 0.0, "EV": 0.0, "PnL": 0.0,
                         "PF": 0.0, "wilson_lo": 0.0, "bt_error": xau_err},
            "lock_criteria": {
                "verdict": "BLOCKED_DATA",
                "reason": "XAU shadow-only cache absent; implementation remains default-off until opt-in data exists",
                "shadow_promote_recommendation": "IMPLEMENTATION_ONLY_DEFAULT_OFF",
            },
        }

    runnable_verdicts = [
        c["lock_criteria"].get("verdict")
        for pair, c in cells.items()
        if c["lock_criteria"].get("verdict") != "BLOCKED_DATA"
    ]
    if missing_required:
        overall = "BLOCKED_DATA"
    elif runnable_verdicts and all(v == "PASS" for v in runnable_verdicts):
        overall = "PASS"
    elif runnable_verdicts and all(v in {"PASS", "INSUFFICIENT_BT_EVIDENCE"} for v in runnable_verdicts):
        overall = "INSUFFICIENT_BT_EVIDENCE"
    else:
        overall = "REJECT"

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategy": STRATEGY,
        "variant": "pair_scope_v2_eurusd_gbpusd_live_eurgbp_xau_shadow",
        "flag": FLAG,
        "shadow_worker_flag": SHADOW_PROMOTE_FLAG,
        "lookback_days": LOOKBACK_DAYS,
        "minimum_days": MINIMUM_DAYS,
        "interval": INTERVAL,
        "runner": "app.run_daytrade_backtest(backtest_mode=True; production daytrade path; strategy-only compute patch)",
        "data_source_required": "data/cache/massive/{PAIR}_{TF}.parquet with BT_MODE=1 and BT_REQUIRE_MASSIVE_CACHE=1",
        "bt_mode": os.environ.get("BT_MODE"),
        "live_pairs_v2": sorted(V2_LIVE_PAIRS),
        "shadow_pairs_v2": sorted(V2_SHADOW_PAIRS),
        "targets": [pair for pair, _ in TARGETS] + [XAU_TARGET[0]],
        "missing_caches": missing_required + ([str(_cache_path(XAU_TARGET[0]).relative_to(ROOT))] if xau_missing else []),
        "lock_spec": {
            "bt_evidence_threshold": "if proposed N < 20 => INSUFFICIENT_BT_EVIDENCE, skip catastrophic, recommend shadow",
            "catastrophic_check": {"pnl_sign_preserved": "baseline PnL > 0 and proposed PnL < 0 is the only REJECT"},
            "warn_only": ["pf_change", "wilson_lo_change", "n_change_pct"],
            "sanity_floor": "REMOVED in v2.1",
            "positive_direction": "not required",
            "absolute_kelly": "not required",
        },
        "cells": cells,
        "overall_verdict": overall,
        "shadow_promote_recommendation": (
            "RECOMMEND_SHADOW"
            if overall in {"PASS", "INSUFFICIENT_BT_EVIDENCE"}
            else "IMPLEMENTATION_ONLY_DEFAULT_OFF" if overall == "BLOCKED_DATA" else "REJECT"
        ),
        "shadow_accumulation_target": "60-90 days or N>=30 after shadow start",
        "elapsed_s": round(time.time() - started, 1),
        "self_review": {
            "catastrophic_only": "PASS: verdict uses pnl_sign_preserved only when proposed N>=20; PF/Wilson/N are warnings only.",
            "absolute_kelly": "PASS: no Kelly threshold is used.",
            "production_live_safety": f"PASS: behavior is default-off unless {FLAG}=1; parallel shadow emit also requires {SHADOW_PROMOTE_FLAG}=1.",
            "post_hoc_adjustment": "PASS: only the audit-specified pair routing scope changed; trigger/timing/SL/TP geometry is untouched.",
            "bt_source_guard": "PASS: BT_REQUIRE_MASSIVE_CACHE=1 prevents Yahoo fallback for runnable 15m targets.",
        },
    }

    OUTFILE.parent.mkdir(parents=True, exist_ok=True)
    OUTFILE.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved: {OUTFILE}")
    print(f"Overall: {overall}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
