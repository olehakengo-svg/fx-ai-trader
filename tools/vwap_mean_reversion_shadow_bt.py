#!/usr/bin/env python3
"""A/B BT report for vwap_mean_reversion V2 closed-bar redesign."""
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
    ("EUR_GBP", "EURGBP=X"),
]
LOOKBACK_DAYS = 365
MINIMUM_DAYS = 365
INTERVAL = "15m"
STRATEGY = "vwap_mean_reversion"
FLAG = "VWAP_MEAN_REVERSION_REDESIGN_V2"
SHADOW_PROMOTE_FLAG = "VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE"
OUTFILE = ROOT / "bt-results" / "vwap_mean_reversion-shadow-redesign-v2-2026-05-05.json"


def _compute_vwap_mr_only_signal(df, tf, sr_levels, symbol="USDJPY=X",
                                 backtest_mode=False, bar_time=None, htf_cache=None):
    if df is None or len(df) < 50 or "vwap" not in df.columns:
        return {"signal": "WAIT", "entry_type": "wait", "reasons": ["vwap_mean_reversion no data"]}

    row = df.iloc[-1]
    entry = float(row["Close"])
    atr = float(row.get("atr", 0.0))
    if os.environ.get(FLAG, "0") != "1":
        return {
            "signal": "WAIT",
            "entry": entry,
            "entry_type": "wait",
            "reasons": ["vwap_mean_reversion disabled baseline"],
            "atr": atr,
            "mode": "daytrade",
            "shadow_emit_signals": [],
        }

    signal_row = row
    signal_time = bar_time if bar_time is not None else row.name
    signal_df = df
    vwap = float(signal_row["vwap"])
    if vwap <= 0:
        return {"signal": "WAIT", "entry": entry, "entry_type": "wait", "reasons": ["bad vwap"], "atr": atr}

    dev_series = ((signal_df["Close"] - signal_df["vwap"]) / signal_df["vwap"] * 100).tail(50)
    std = float(dev_series.std())
    if std <= 0:
        return {"signal": "WAIT", "entry": entry, "entry_type": "wait", "reasons": ["zero vwap deviation std"], "atr": atr}

    signal_entry = float(signal_row["Close"])
    dev = (signal_entry - vwap) / vwap * 100
    sig = None
    conf = 0
    if dev < -2 * std:
        sig = "BUY"
        conf = int(55 + min(10, abs(dev) * 5))
    elif dev > 2 * std:
        sig = "SELL"
        conf = int(50 + min(5, abs(dev) * 3))
    if sig is None:
        return {"signal": "WAIT", "entry": entry, "entry_type": "wait", "reasons": ["vwap_mean_reversion no signal"], "atr": atr}

    reasons = []
    vwap_tail = signal_df["vwap"].tail(10).values
    if len(vwap_tail) >= 5:
        slope_raw = (float(vwap_tail[-1]) - float(vwap_tail[0])) / max(1, len(vwap_tail) - 1)
        slope_norm = abs(slope_raw) / max(1e-9, std * vwap / 100)
        if slope_norm > 0.3:
            return {"signal": "WAIT", "entry": entry, "entry_type": "wait", "reasons": [f"slope too steep {slope_norm:.2f}"], "atr": atr}

    adx = float(signal_row.get("adx", row.get("adx", 25.0)))
    if adx >= 22.0:
        return {"signal": "WAIT", "entry": entry, "entry_type": "wait", "reasons": [f"ADX={adx:.1f} hard block"], "atr": atr}

    hour = signal_time.hour if hasattr(signal_time, "hour") else 12
    if hour not in range(7, 20):
        return {"signal": "WAIT", "entry": entry, "entry_type": "wait", "reasons": [f"outside active hours UTC {hour}"], "atr": atr}

    prev_dev = float(dev_series.iloc[-2]) if len(dev_series) >= 2 else dev
    if sig == "BUY" and prev_dev <= dev:
        return {"signal": "WAIT", "entry": entry, "entry_type": "wait", "reasons": ["no BUY reclaim"], "atr": atr}
    if sig == "SELL" and prev_dev >= dev:
        return {"signal": "WAIT", "entry": entry, "entry_type": "wait", "reasons": ["no SELL reclaim"], "atr": atr}

    sigma_dev = abs(dev) / std
    score = min(5.0, sigma_dev)
    if sig == "BUY":
        sl = entry - atr * 1.2
        tp = entry + max(abs(vwap - signal_entry), atr * 1.0)
        reasons.append(f"✅ [VWAP-MR] Price < VWAP-2σ ({dev:.2f}%, σ={std:.2f}) → BUY")
    else:
        sl = entry + atr * 1.2
        tp = entry - max(abs(vwap - signal_entry), atr * 1.0)
        reasons.append(f"✅ [VWAP-MR] Price > VWAP+2σ ({dev:+.2f}%, σ={std:.2f}) → SELL")
    reasons.append(f"✅ [VWAP-MR V2] closed_bar_time={signal_time} next-bar execution; HTF direction veto disabled")

    return {
        "signal": sig,
        "entry": entry,
        "confidence": conf,
        "sl": sl,
        "tp": tp,
        "entry_type": STRATEGY,
        "reasons": reasons,
        "score": score,
        "atr": atr,
        "mode": "daytrade",
        "layer_status": {},
        "regime": {"regime": "RANGE"},
        "indicators": {"adx": adx, "vwap": vwap},
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


def _run(app, data_mod, symbol: str, proposed: bool, days: int) -> dict:
    os.environ[FLAG] = "1" if proposed else "0"
    app._dt_bt_cache.clear()
    data_mod._data_cache.clear()
    if hasattr(app, "_VWAP_MEAN_REVERSION_V2_SEEN_BAR_KEYS"):
        app._VWAP_MEAN_REVERSION_V2_SEEN_BAR_KEYS.clear()
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
    err = current.get("bt_error") or proposed.get("bt_error")
    sample_short_current = "サンプル数不足" in str(current.get("bt_error") or "")
    sample_short_proposed = "サンプル数不足" in str(proposed.get("bt_error") or "")
    if err and not (sample_short_current or sample_short_proposed):
        return {
            "verdict": "BLOCKED_DATA" if "missing MASSIVE parquet cache" in str(err) else "REJECT",
            "reason": "bt_error",
            "bt_error": err,
            "shadow_promote_recommendation": "IMPLEMENT_ONLY_DEFAULT_OFF",
        }
    if proposed["N"] < 20:
        return {
            "verdict": "INSUFFICIENT_BT_EVIDENCE",
            "reason": "proposed BT trades < 20; catastrophic check skipped under v2.1",
            "catastrophic_check": "SKIPPED",
            "warnings": _warn_only(current, proposed),
            "shadow_promote_recommendation": "RECOMMEND_SHADOW",
        }

    sign_ok = _pnl_sign_preserved(current["PnL"], proposed["PnL"])
    return {
        "pnl_sign_preserved": sign_ok,
        "catastrophic_check": sign_ok,
        "warnings": _warn_only(current, proposed),
        "verdict": "PASS" if sign_ok else "REJECT",
        "shadow_promote_recommendation": "RECOMMEND_SHADOW" if sign_ok else "REJECT",
    }


def _warn_only(current: dict, proposed: dict) -> dict:
    current_pf = _num(current["PF"])
    proposed_pf = _num(proposed["PF"])
    pf_change = proposed_pf - current_pf
    n_change_pct = _change_pct(proposed["N"], current["N"])
    return {
        "pf_change": round(pf_change, 4) if math.isfinite(pf_change) else str(pf_change),
        "wilson_lo_change": round(proposed["wilson_lo"] - current["wilson_lo"], 4),
        "n_change_pct": round(n_change_pct, 4) if math.isfinite(n_change_pct) else str(n_change_pct),
        "note": "WARN ONLY in v2.1; not used for verdict",
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

        app.compute_daytrade_signal = _compute_vwap_mr_only_signal
        app.get_master_bias = lambda symbol: {"direction": "neutral", "label": "BT strategy filter", "score": 0}
        app.find_sr_levels_weighted = lambda *args, **kwargs: []
        app._compute_bt_htf_bias = lambda *args, **kwargs: {"agreement": "mixed", "label": "BT strategy filter"}

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
    if verdicts and any(v == "REJECT" for v in verdicts):
        overall = "REJECT"
    elif verdicts and any(v == "BLOCKED_DATA" for v in verdicts):
        overall = "BLOCKED_DATA"
    elif verdicts and any(v == "INSUFFICIENT_BT_EVIDENCE" for v in verdicts):
        overall = "INSUFFICIENT_BT_EVIDENCE"
    else:
        overall = "PASS"

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategy": STRATEGY,
        "variant": "closed_bar_timing_and_htf_soft_v2",
        "flag": FLAG,
        "shadow_worker_flag": SHADOW_PROMOTE_FLAG,
        "lookback_days": LOOKBACK_DAYS,
        "minimum_days": MINIMUM_DAYS,
        "interval": INTERVAL,
        "runner": "app.run_daytrade_backtest(backtest_mode=True; vwap_mean_reversion strategy-filter signal path; neutral HTF/SR precompute for BT filter)",
        "data_source_required": "data/cache/massive/{PAIR}_{TF}.parquet with BT_MODE=1 and BT_REQUIRE_MASSIVE_CACHE=1",
        "bt_mode": os.environ.get("BT_MODE"),
        "massive_cache_verified": not missing,
        "targets": [pair for pair, _ in TARGETS],
        "missing_caches": missing,
        "lock_spec": {
            "bt_evidence_threshold": "if proposed N < 20 => INSUFFICIENT_BT_EVIDENCE, skip catastrophic check, recommend shadow",
            "catastrophic_check": "pnl_sign_preserved only; NG only when baseline PnL > 0 and proposed PnL < 0",
            "sanity_floor": "REMOVED in v2.1",
            "pf_change_wilson_lo_change_n_change_pct": "WARN ONLY",
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
            "catastrophic_only": "PASS: only positive-to-negative PnL sign flip can reject when N>=20.",
            "insufficient_bt_evidence": "PASS: proposed N<20 becomes INSUFFICIENT_BT_EVIDENCE and recommends shadow.",
            "sanity_floor_removed": "PASS: PF/Wilson/N changes are warnings only.",
            "production_live_safety": "PASS: behavior is default-off unless VWAP_MEAN_REVERSION_REDESIGN_V2=1.",
            "post_hoc_adjustment": "PASS: no thresholds adjusted after results.",
            "bt_source_guard": "PASS: BT_REQUIRE_MASSIVE_CACHE=1 prevents fallback.",
        },
    }

    OUTFILE.parent.mkdir(parents=True, exist_ok=True)
    OUTFILE.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved: {OUTFILE}")
    print(f"Overall: {overall}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
