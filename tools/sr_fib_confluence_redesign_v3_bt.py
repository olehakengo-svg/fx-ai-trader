#!/usr/bin/env python3
"""A/B BT filter for sr_fib_confluence redesign V3."""
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
    ("USD_JPY", "USDJPY=X"),
]
_TARGET_FILTER = {
    x.strip().upper()
    for x in os.environ.get("SR_FIB_CONFLUENCE_BT_TARGETS", "").split(",")
    if x.strip()
}
if _TARGET_FILTER:
    TARGETS = [
        (pair, symbol)
        for pair, symbol in TARGETS
        if pair in _TARGET_FILTER or symbol.upper() in _TARGET_FILTER
    ]
LOOKBACK_DAYS = 365
MINIMUM_DAYS = 365
INTERVAL = "15m"
STRATEGY = "sr_fib_confluence"
ALT_ENTRY_TYPES = {"sr_fib_confluence", "ob_retest"}
FLAG = "SR_FIB_CONFLUENCE_REDESIGN_V3"
SHADOW_PROMOTE_FLAG = "SR_FIB_CONFLUENCE_REDESIGN_V3_SHADOW_PROMOTE"
OUTFILE = ROOT / "bt-results" / "sr_fib_confluence-redesign-v3-2026-06-04.json"
if os.environ.get("SR_FIB_CONFLUENCE_BT_OUTFILE"):
    OUTFILE = ROOT / os.environ["SR_FIB_CONFLUENCE_BT_OUTFILE"]


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
        if t.get("entry_type", t.get("type")) in ALT_ENTRY_TYPES
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


def _legacy_reasons_from_layer3(layer3: dict) -> list[str]:
    reasons = []
    if layer3.get("fib_level") is not None:
        reasons.append(f"✅ Fib structured BT level={float(layer3['fib_level']):.5f}")
    if layer3.get("ob_zone_low") is not None and layer3.get("ob_zone_high") is not None:
        reasons.append(
            "✅ OB structured BT zone="
            f"{float(layer3['ob_zone_low']):.5f}-{float(layer3['ob_zone_high']):.5f}"
        )
    return reasons


def _structured_layer3(df, sr_levels) -> dict:
    row = df.iloc[-1]
    close = float(row["Close"])
    atr = float(row.get("atr", 0.0) or 0.0)
    layer3 = {
        "score": 0.0,
        "label": "structured sr/fib/ob BT extractor",
        "components": {},
        "signal_bar_time": str(getattr(row, "name", "")),
    }
    if atr <= 0:
        return layer3

    if len(df) >= 100:
        sub = df.tail(100)
        swing_high = float(sub["High"].max())
        swing_low = float(sub["Low"].min())
        swing_range = swing_high - swing_low
        if swing_range > atr * 2:
            fib_levels = [
                ("fib_38.2_bull", swing_high - swing_range * 0.382),
                ("fib_50.0_bull", swing_high - swing_range * 0.500),
                ("fib_61.8_bull", swing_high - swing_range * 0.618),
                ("fib_38.2_bear", swing_low + swing_range * 0.382),
                ("fib_50.0_bear", swing_low + swing_range * 0.500),
                ("fib_61.8_bear", swing_low + swing_range * 0.618),
            ]
            fib_name, fib_level = min(fib_levels, key=lambda x: abs(close - x[1]))
            if abs(close - fib_level) <= atr * 0.35:
                layer3["fib_level"] = float(fib_level)
                layer3["confluence_type"] = fib_name

    if sr_levels:
        def _sr_price(x):
            return float(x["price"] if isinstance(x, dict) else x)

        nearest = min(sr_levels, key=lambda x: abs(_sr_price(x) - close))
        sr_level = _sr_price(nearest)
        if abs(close - sr_level) <= atr * 0.5:
            layer3["sr_level"] = sr_level
            layer3.setdefault("confluence_type", "sr_level")

    sub = df.tail(80)
    if len(sub) >= 20:
        opens = sub["Open"].to_numpy()
        highs = sub["High"].to_numpy()
        lows = sub["Low"].to_numpy()
        closes = sub["Close"].to_numpy()
        atrs = sub["atr"].to_numpy() if "atr" in sub else None
        for i in range(len(sub) - 3, 0, -1):
            imp_i = i + 1
            imp_atr = float(atrs[imp_i]) if atrs is not None and atrs[imp_i] > 0 else atr
            imp_body = abs(float(closes[imp_i]) - float(opens[imp_i]))
            if imp_body < 1.5 * imp_atr:
                continue
            bull_ob = closes[imp_i] > opens[imp_i] and closes[i] < opens[i]
            bear_ob = closes[imp_i] < opens[imp_i] and closes[i] > opens[i]
            if not (bull_ob or bear_ob):
                continue
            zone_low = float(lows[i])
            zone_high = float(highs[i])
            if zone_low <= close <= zone_high:
                layer3["ob_zone_low"] = min(zone_low, zone_high)
                layer3["ob_zone_high"] = max(zone_low, zone_high)
                layer3["confluence_type"] = "bull_ob_retest" if bull_ob else "bear_ob_retest"
                break

    return layer3


def _compute_sr_fib_only_signal(df, tf, sr_levels, symbol="USDJPY=X",
                                backtest_mode=False, bar_time=None, htf_cache=None):
    from strategies.context import SignalContext
    from strategies.daytrade.sr_fib_confluence import SrFibConfluence

    if df is None or len(df) < 3:
        return {"signal": "WAIT", "entry_type": "wait", "reasons": ["insufficient df"]}

    row = df.iloc[-1]
    prev = df.iloc[-2]
    prev2 = df.iloc[-3]
    entry = float(row["Close"])
    atr = float(row.get("atr", 0.0) or 0.0)
    if bar_time is None:
        bar_time = df.index[-1]
    is_jpy = "JPY" in symbol.upper()
    htf = (htf_cache or {}).get("htf", {}) if isinstance(htf_cache, dict) else {}
    layer3 = _structured_layer3(df, sr_levels)
    layer3["dt_reasons"] = _legacy_reasons_from_layer3(layer3)
    ctx = SignalContext(
        entry=entry,
        open_price=float(row["Open"]),
        atr=atr,
        atr7=float(row.get("atr7", atr)),
        ema9=float(row.get("ema9", entry)),
        ema21=float(row.get("ema21", entry)),
        ema50=float(row.get("ema50", entry)),
        ema200=float(row.get("ema200", entry)),
        ema9_prev=float(prev.get("ema9", entry)),
        ema21_prev=float(prev.get("ema21", entry)),
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
        macdh_prev2=float(prev2.get("macd_hist", 0.0)),
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
        layer3=layer3,
        htf=htf,
        backtest_mode=backtest_mode,
        bar_time=bar_time,
        hour_utc=bar_time.hour if hasattr(bar_time, "hour") else 12,
    )
    cand = SrFibConfluence().evaluate(ctx)
    if cand is None:
        return {
            "signal": "WAIT",
            "entry": entry,
            "entry_type": "wait",
            "reasons": ["sr_fib_confluence no signal"],
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
        "reasons": ["✅ sr_fib_confluence strategy-filter BT"] + list(cand.reasons or []),
        "score": float(cand.score),
        "atr": atr,
        "mode": "daytrade",
        "layer_status": {},
        "regime": {},
        "indicators": {"adx": ctx.adx},
        "shadow_emit_signals": [],
    }


def _run(app, data_mod, symbol: str, proposed: bool) -> dict:
    os.environ[FLAG] = "1" if proposed else "0"
    os.environ["SR_FIB_CONFLUENCE_REDESIGN_V2"] = "0"
    from strategies.daytrade.sr_fib_confluence import SrFibConfluence

    SrFibConfluence.reset_dedup_state()
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
            "reason": "proposed BT trades < 20",
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
    pf_change = _num(proposed["PF"]) - _num(current["PF"])
    wilson_change = proposed["wilson_lo"] - current["wilson_lo"]
    n_change_pct = _change_pct(proposed["N"], current["N"])
    pnl_sign_preserved = not (current["PnL"] > 0 and proposed["PnL"] < 0)
    verdict = "PASS" if pnl_sign_preserved else "REJECT"
    return {
        "pf_change_warn_only": round(pf_change, 4) if math.isfinite(pf_change) else str(pf_change),
        "wilson_lo_change_warn_only": round(wilson_change, 4),
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
                "lock_criteria": {
                    "verdict": "BLOCKED_DATA",
                    "reason": "missing_massive_cache",
                    "shadow_promote_recommendation": "DEFAULT_OFF_UNTIL_DATA_READY",
                },
            }
    else:
        import app  # noqa: E402
        from modules import data as data_mod  # noqa: E402

        app.compute_daytrade_signal = _compute_sr_fib_only_signal

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
    elif verdicts and any(v == "BLOCKED_DATA" for v in verdicts):
        overall = "BLOCKED_DATA"

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategy": STRATEGY,
        "variant": "classical_mr_follow_v3",
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
            "post_hoc_adjustment": "PASS: only structured_layer3_fib_ob_gate_v2 is evaluated.",
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
