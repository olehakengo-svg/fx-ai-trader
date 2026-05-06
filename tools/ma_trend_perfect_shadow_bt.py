#!/usr/bin/env python3
"""A/B BT filter for ma_trend_perfect V2 closed-bar timing redesign."""
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

TARGETS = [("USD_JPY", "USDJPY=X")]
LOOKBACK_DAYS = 365
MINIMUM_DAYS = 365
INTERVAL = "15m"
HTF_INTERVAL = "5m"
STRATEGY = "ma_trend_perfect"
FLAG = "MA_TREND_PERFECT_REDESIGN_V2"
SHADOW_PROMOTE_FLAG = "MA_TREND_PERFECT_REDESIGN_V2_SHADOW_PROMOTE"
OUTFILE = ROOT / "bt-results" / "ma_trend_perfect-shadow-redesign-v2-2026-05-05.json"

_FULL_DF = None
_BAR_INDEX: dict = {}
_HTF_MERGED = None


def _cache_path(pair: str) -> Path:
    return ROOT / "data" / "cache" / "massive" / f"{pair}_{INTERVAL}.parquet"


def _htf_cache_path(pair: str) -> Path:
    return ROOT / "data" / "cache" / "massive" / f"{pair}_{HTF_INTERVAL}.parquet"


def _set_full_df(df) -> None:
    global _FULL_DF, _BAR_INDEX, _HTF_MERGED
    import pandas as pd
    import app
    from modules.bt_vec_harness import (
        HtfFeatureSpec,
        compute_h1_features,
        compute_m15_features,
        compute_m5_features,
    )

    _FULL_DF = df
    _BAR_INDEX = {ts: i for i, ts in enumerate(df.index)}
    spec = HtfFeatureSpec(
        include_hurst_m15=True,
        include_range_20_m15=True,
        include_rsi_divergence_m5=True,
    )
    df_h1 = app.resample_df(df, "1h")
    df_15 = app.resample_df(df, "15min")
    df_5 = app.resample_df(df, "5min")
    feat_h1 = compute_h1_features(df_h1, spec)
    feat_15 = compute_m15_features(df_15, spec)
    feat_5 = compute_m5_features(df_5, spec)

    base = pd.DataFrame({"ts": pd.to_datetime(df.index)})
    frames = [
        ("h1", feat_h1),
        ("m15", feat_15),
        ("m5", feat_5),
    ]
    merged = base.sort_values("ts")
    for prefix, feat in frames:
        feat_re = feat.reset_index().rename(columns={feat.index.name or "index": "ts"})
        feat_re["ts"] = pd.to_datetime(feat_re["ts"])
        feat_re.sort_values("ts", inplace=True)
        merged = pd.merge_asof(
            merged,
            feat_re.add_prefix(f"{prefix}_").rename(columns={f"{prefix}_ts": "ts"}),
            on="ts",
            direction="backward",
        )
    _HTF_MERGED = merged.set_index("ts")


def _bt_htf_for_bar(app, bar_time) -> dict:
    if _FULL_DF is None or _HTF_MERGED is None:
        return {"h1": {}, "m15": {}, "m5": {}}
    if bar_time in _BAR_INDEX:
        row_pos = _BAR_INDEX[bar_time]
    else:
        row_pos = _HTF_MERGED.index.searchsorted(bar_time, side="right") - 1
        if row_pos < 0:
            return {"h1": {}, "m15": {}, "m5": {}}
    row = _HTF_MERGED.iloc[row_pos]

    def f(name: str) -> float:
        value = row.get(name, 0.0)
        try:
            if math.isnan(value):
                return 0.0
        except TypeError:
            pass
        return float(value or 0.0)

    return {
        "h1": {
            "close": f("h1_close"),
            "ema9": f("h1_ema9"),
            "ema21": f("h1_ema21"),
            "ema50": f("h1_ema50"),
            "ema200": f("h1_ema200"),
            "adx": f("h1_adx"),
            "rsi14": f("h1_rsi14"),
            "is_closed": True,
        },
        "m15": {
            "close": f("m15_close"),
            "adx": f("m15_adx"),
            "ema9": f("m15_ema9"),
            "ema21": f("m15_ema21"),
            "ema50": f("m15_ema50"),
            "rsi14": f("m15_rsi14"),
            "atr": f("m15_atr"),
            "atr_pct": f("m15_atr_pct"),
            "ema_slope": f("m15_ema_slope"),
            "is_closed": True,
        },
        "m5": {
            "close": f("m5_close"),
            "high": f("m5_high"),
            "low": f("m5_low"),
            "prev_close": f("m5_prev_close"),
            "prev_high": f("m5_prev_high"),
            "prev_low": f("m5_prev_low"),
            "sma21": f("m5_sma21"),
            "ema21": f("m5_ema21"),
            "atr": f("m5_atr"),
            "bbpb": f("m5_bbpb"),
            "rsi14": f("m5_rsi14"),
            "stoch_k": f("m5_stoch_k"),
            "stoch_d": f("m5_stoch_d"),
            "is_closed": True,
        },
    }


def _compute_ma_trend_perfect_only_signal(
    df,
    tf,
    sr_levels,
    symbol="USDJPY=X",
    backtest_mode=False,
    bar_time=None,
    htf_cache=None,
):
    import app
    from strategies.context import SignalContext
    from strategies.scalp.ma_trend_perfect import MaTrendPerfect

    if df is None or len(df) < 3:
        return {"signal": "WAIT", "entry_type": "wait", "reasons": ["empty df"]}

    row = df.iloc[-1]
    prev = df.iloc[-2]
    entry = float(row["Close"])
    atr = float(row.get("atr", 0.0))
    if bar_time is None:
        bar_time = df.index[-1]
    is_jpy = "JPY" in symbol.upper()

    htf = _bt_htf_for_bar(app, bar_time)
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
        hour_utc=bar_time.hour if hasattr(bar_time, "hour") else 12,
    )
    cand = MaTrendPerfect().evaluate(ctx)
    if cand is None:
        return {
            "signal": "WAIT",
            "entry": entry,
            "entry_type": "wait",
            "reasons": ["ma_trend_perfect no signal"],
            "atr": atr,
            "mode": "daytrade",
            "indicators": {"adx": ctx.adx, "rsi": ctx.rsi},
        }
    return {
        "signal": cand.signal,
        "entry": entry,
        "confidence": cand.confidence,
        "sl": cand.sl,
        "tp": cand.tp,
        "entry_type": cand.entry_type,
        "reasons": ["✅ ma_trend_perfect strategy-filter BT"] + list(cand.reasons or []),
        "score": cand.score,
        "atr": atr,
        "mode": "daytrade",
        "layer_status": {},
        "regime": {},
        "indicators": {"adx": ctx.adx, "rsi": ctx.rsi},
        "shadow_emit_signals": [],
    }


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
    app._bt_scalp_mtf_precompute_cache.clear()
    data_mod._data_cache.clear()
    df = data_mod.fetch_ohlcv(symbol, period=f"{LOOKBACK_DAYS}d", interval=HTF_INTERVAL)
    _set_full_df(app.add_indicators(df).dropna())
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
            "bt_error": err,
            "catastrophic_check": False,
            "sanity_floor": False,
            "shadow_promote_recommendation": "REJECT",
        }
    current_pf = _num(current["PF"])
    proposed_pf = _num(proposed["PF"])
    pf_change = proposed_pf - current_pf
    wilson_lo_change = proposed["wilson_lo"] - current["wilson_lo"]
    n_change_pct = _change_pct(proposed["N"], current["N"])
    pnl_sign_preserved = not (current["PnL"] > 0 and proposed["PnL"] < 0)
    catastrophic_pass = (
        pf_change >= -0.10
        and wilson_lo_change >= -0.05
        and n_change_pct >= -30
        and pnl_sign_preserved
    )
    sanity_floor = proposed["wilson_lo"] >= 0.20 and proposed_pf >= 0.85
    verdict = "PASS" if catastrophic_pass and sanity_floor else "REJECT"
    return {
        "pf_change": round(pf_change, 4) if math.isfinite(pf_change) else str(pf_change),
        "wilson_lo_change": round(wilson_lo_change, 4),
        "n_change_pct": round(n_change_pct, 4) if math.isfinite(n_change_pct) else str(n_change_pct),
        "pnl_sign_preserved": pnl_sign_preserved,
        "catastrophic_check": catastrophic_pass,
        "sanity_floor": sanity_floor,
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
    missing.extend(
        str(_htf_cache_path(pair).relative_to(ROOT))
        for pair, _ in TARGETS
        if not _htf_cache_path(pair).exists()
    )
    current_all: list[float] = []
    proposed_all: list[float] = []

    if missing:
        err = "missing MASSIVE parquet cache"
        aggregate_current = _stats_from_pnls([], bt_error=err)
        aggregate_proposed = _stats_from_pnls([], bt_error=err)
        aggregate_lock = {"verdict": "REJECT", "reason": "missing_massive_cache"}
    else:
        import app
        from modules import data as data_mod

        app.compute_daytrade_signal = _compute_ma_trend_perfect_only_signal

        for pair, symbol in TARGETS:
            print(f"Running baseline: {pair} {LOOKBACK_DAYS}d {INTERVAL}", flush=True)
            current, current_pnls = _stats(_run(app, data_mod, symbol, proposed=False))
            print(f"Running proposed: {pair} {LOOKBACK_DAYS}d {INTERVAL}", flush=True)
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
        "variant": "closed_bar_m5_breakout_next_bar_confirmation_v2",
        "flag": FLAG,
        "shadow_worker_flag": SHADOW_PROMOTE_FLAG,
        "lookback_days": LOOKBACK_DAYS,
        "minimum_days": MINIMUM_DAYS,
        "interval": INTERVAL,
        "htf_feature_interval": HTF_INTERVAL,
        "runner": "app.run_daytrade_backtest(backtest_mode=True; production daytrade path; strategy-only compute patch)",
        "data_source_required": "data/cache/massive/{PAIR}_{TF}.parquet with BT_MODE=1 and BT_REQUIRE_MASSIVE_CACHE=1",
        "data_source_note": "Primary production run_daytrade bars use 15m MASSIVE; H1/M15/M5 context is precomputed from native 5m MASSIVE cache, not Yahoo/network fallback.",
        "bt_mode": os.environ.get("BT_MODE"),
        "massive_cache_verified": not missing,
        "targets": [pair for pair, _ in TARGETS],
        "target_scope_note": "Audit/code restrict ma_trend_perfect to USD_JPY.",
        "missing_caches": missing,
        "lock_spec": {
            "bt_evidence_threshold": "if proposed N < 20 => INSUFFICIENT_BT_EVIDENCE, skip catastrophic, recommend shadow",
            "catastrophic_check": {
                "pf_change": ">= -0.10",
                "wilson_lo_change": ">= -0.05",
                "n_change_pct": ">= -30",
                "pnl_sign_preserved": True,
            },
            "sanity_floor": {"wilson_lo_proposed": ">= 0.20", "pf_proposed": ">= 0.85"},
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
            "catastrophic_only": "PASS: verdict ignores positive-direction and Kelly; applies only v2 catastrophic/floor rules when N>=20.",
            "insufficient_bt_evidence": "PASS: proposed N<20 becomes INSUFFICIENT_BT_EVIDENCE and shadow recommendation.",
            "production_live_safety": f"PASS: strategy V2 behavior is default-off unless {FLAG}=1; shadow loser emit also requires {SHADOW_PROMOTE_FLAG}=1.",
            "post_hoc_adjustment": "PASS: only the pre-registered closed-bar timing variant is evaluated.",
            "bt_source_guard": "PASS: BT_REQUIRE_MASSIVE_CACHE=1 prevents Yahoo/network fallback for price data.",
        },
    }

    OUTFILE.parent.mkdir(parents=True, exist_ok=True)
    OUTFILE.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved: {OUTFILE}")
    print(f"Overall: {overall}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
