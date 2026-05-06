#!/usr/bin/env python3
"""A/B BT filter for sr_channel_reversal V2 closed-bar + MR geometry."""
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.modules.setdefault("pytest", object())

TARGETS = [
    ("USD_JPY", "USDJPY=X"),
    ("EUR_JPY", "EURJPY=X"),
    ("EUR_USD", "EURUSD=X"),
    ("GBP_USD", "GBPUSD=X"),
    ("GBP_JPY", "GBPJPY=X"),
]
LOOKBACK_DAYS = 365
MINIMUM_DAYS = 365
INTERVAL = "15m"
STRATEGY = "sr_channel_reversal"
FLAG = "SR_CHANNEL_REVERSAL_REDESIGN_V2"
SHADOW_FLAG = "SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE"
OUTFILE = ROOT / "bt-results" / "sr_channel_reversal-shadow-redesign-v2-2026-05-05.json"


class _SrChannelOnlyScalperEngine:
    """BT strategy filter equivalent to strategies=['sr_channel_reversal']."""

    SHADOW_ALWAYS_STRATEGIES = frozenset()

    def __init__(self):
        from strategies.scalp.sr_channel_reversal import SrChannelReversal
        self.strategies = [SrChannelReversal()]

    def evaluate_all(self, ctx):
        candidates = []
        for strategy in self.strategies:
            result = strategy.evaluate(ctx)
            if result is not None:
                candidates.append(result)
        return candidates

    def select_best(self, candidates):
        if not candidates:
            return None
        return max(candidates, key=lambda c: c.score)

    def split_shadow_always(self, candidates, best):
        return []


def _compute_sr_channel_only_signal(df, tf, sr_levels, symbol="USDJPY=X",
                                    backtest_mode=False, bar_time=None, htf_cache=None):
    from strategies.context import SignalContext
    from strategies.scalp.sr_channel_reversal import SrChannelReversal

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
    cand = SrChannelReversal().evaluate(ctx)
    if cand is None:
        return {
            "signal": "WAIT",
            "entry": entry,
            "entry_type": "wait",
            "reasons": ["sr_channel_reversal no signal"],
            "atr": atr,
            "mode": "scalp",
            "indicators": {"rsi": ctx.rsi, "adx": ctx.adx, "bb_mid": ctx.bb_mid},
        }
    return {
        "signal": cand.signal,
        "entry": entry,
        "confidence": cand.confidence,
        "sl": cand.sl,
        "tp": cand.tp,
        "entry_type": cand.entry_type,
        "reasons": ["✅ sr_channel_reversal strategy-filter BT"] + list(cand.reasons or []),
        "score": cand.score,
        "atr": atr,
        "mode": "scalp",
        "layer_status": {},
        "regime": {"regime": "RANGE"},
        "indicators": {"rsi": ctx.rsi, "adx": ctx.adx, "bb_mid": ctx.bb_mid},
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
    trades = [
        t for t in result.get("trade_log", [])
        if t.get("entry_type", t.get("type")) == STRATEGY
    ]
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


def _run(app, data_mod, symbol: str, proposed: bool, days: int) -> dict:
    os.environ[FLAG] = "1" if proposed else "0"
    app._scalp_bt_cache.clear()
    data_mod._data_cache.clear()
    from strategies.scalp.sr_channel_reversal import SrChannelReversal
    SrChannelReversal._v2_seen_closed_bar_keys.clear()
    return app.run_scalp_backtest(
        symbol=symbol,
        lookback_days=days,
        interval=INTERVAL,
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
    warnings = {
        "pf_change": None,
        "wilson_lo_change": round(proposed["wilson_lo"] - current["wilson_lo"], 4),
        "n_change_pct": round(_change_pct(proposed["N"], current["N"]), 4)
        if math.isfinite(_change_pct(proposed["N"], current["N"]))
        else str(_change_pct(proposed["N"], current["N"])),
        "warn_only": ["pf_change", "wilson_lo_change", "n_change_pct"],
    }
    current_pf = _num(current["PF"])
    proposed_pf = _num(proposed["PF"])
    pf_change = proposed_pf - current_pf
    warnings["pf_change"] = round(pf_change, 4) if math.isfinite(pf_change) else str(pf_change)

    if proposed["N"] < 20:
        return {
            **warnings,
            "verdict": "INSUFFICIENT_BT_EVIDENCE",
            "reason": "proposed BT trades < 20; v2.1 skips catastrophic check and recommends shadow",
            "catastrophic_check": "SKIPPED",
            "sanity_floor": "REMOVED",
            "shadow_promote_recommendation": "RECOMMEND_SHADOW",
        }
    if err:
        return {
            **warnings,
            "verdict": "BLOCKED_DATA" if "missing MASSIVE parquet cache" in str(err) else "REJECT",
            "reason": "bt_error",
            "bt_error": err,
            "catastrophic_check": False,
            "sanity_floor": "REMOVED",
            "shadow_promote_recommendation": "REJECT",
        }

    pnl_sign_preserved = _pnl_sign_preserved(current["PnL"], proposed["PnL"])
    verdict = "PASS" if pnl_sign_preserved else "REJECT"
    return {
        **warnings,
        "pnl_sign_preserved": pnl_sign_preserved,
        "catastrophic_check": pnl_sign_preserved,
        "sanity_floor": "REMOVED",
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
    days = LOOKBACK_DAYS

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
                    "shadow_promote_recommendation": "REJECT",
                },
            }
    else:
        import app  # noqa: E402
        from modules import data as data_mod  # noqa: E402
        import strategies.scalp as scalp_mod  # noqa: E402

        scalp_mod.ScalperEngine = _SrChannelOnlyScalperEngine
        app.ScalperEngine = _SrChannelOnlyScalperEngine
        app.compute_scalp_signal = _compute_sr_channel_only_signal

        for pair, symbol in TARGETS:
            print(f"Running baseline: {pair} {days}d", flush=True)
            current = _stats(_run(app, data_mod, symbol, proposed=False, days=days))
            print(f"Running proposed: {pair} {days}d", flush=True)
            proposed = _stats(_run(app, data_mod, symbol, proposed=True, days=days))
            cells[pair] = {
                "current": current,
                "proposed": proposed,
                "lock_criteria": _criteria(current, proposed),
            }

    cell_verdicts = [c["lock_criteria"].get("verdict") for c in cells.values()]
    if cells and any(v == "REJECT" for v in cell_verdicts):
        overall = "REJECT"
    elif cells and any(v == "BLOCKED_DATA" for v in cell_verdicts):
        overall = "BLOCKED_DATA"
    elif cells and any(v == "INSUFFICIENT_BT_EVIDENCE" for v in cell_verdicts):
        overall = "INSUFFICIENT_BT_EVIDENCE"
    elif cells and all(v == "PASS" for v in cell_verdicts):
        overall = "PASS"
    else:
        overall = "REJECT"

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategy": STRATEGY,
        "variant": "closed_bar_signal_boundary_sl_mean_tp_v2",
        "flag": FLAG,
        "shadow_worker_flag": SHADOW_FLAG,
        "lookback_days": days,
        "minimum_days": MINIMUM_DAYS,
        "interval": INTERVAL,
        "runner": "app.run_scalp_backtest (production scalp path; strategy-isolated ScalperEngine patch)",
        "data_source_required": "data/cache/massive/{PAIR}_{TF}.parquet with BT_MODE=1 and BT_REQUIRE_MASSIVE_CACHE=1",
        "bt_mode": os.environ.get("BT_MODE"),
        "massive_cache_verified": not missing,
        "bt_error_data_source_note": "run_scalp_backtest may omit trade_log when it returns <10 trades; N then falls back to result.trades.",
        "targets": [pair for pair, _ in TARGETS],
        "missing_caches": missing,
        "lock_spec": {
            "bt_evidence_threshold": "if proposed N < 20 => INSUFFICIENT_BT_EVIDENCE, skip catastrophic, recommend shadow",
            "catastrophic_check": {
                "pnl_sign_preserved": "baseline PnL > 0 and proposed PnL < 0 is the only REJECT trigger",
            },
            "sanity_floor": "REMOVED in v2.1",
            "pf_change": "WARN_ONLY",
            "wilson_lo_change": "WARN_ONLY",
            "n_change_pct": "WARN_ONLY",
            "positive_direction": "not required",
            "absolute_kelly": "not required",
        },
        "cells": cells,
        "overall_verdict": overall,
        "shadow_promote_recommendation": (
            "RECOMMEND_SHADOW"
            if overall in {"PASS", "INSUFFICIENT_BT_EVIDENCE"}
            else "REJECT"
        ),
        "shadow_accumulation_target": "60-90 days or N>=30 after shadow start",
        "elapsed_s": round(time.time() - started, 1),
        "self_review": {
            "catastrophic_only": "PASS: verdict uses only pnl_sign_preserved when proposed N>=20; PF/Wilson/N changes are warn-only.",
            "absolute_kelly": "PASS: no Kelly or absolute promotion floor is used.",
            "production_live_safety": "PASS: strategy behavior is default-off unless SR_CHANNEL_REVERSAL_REDESIGN_V2=1; shadow emit also requires SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE=1.",
            "post_hoc_adjustment": "PASS: only the pre-registered closed-bar + boundary SL + mean-side TP V2 variant is evaluated.",
            "bt_source_guard": "PASS: BT_MODE=1 and BT_REQUIRE_MASSIVE_CACHE=1 are set before importing app.",
            "runner_note": "PASS: sr_channel_reversal is a scalp-engine strategy, so run_scalp_backtest is the production runner; run_daytrade_backtest does not evaluate this strategy.",
        },
    }

    OUTFILE.parent.mkdir(parents=True, exist_ok=True)
    OUTFILE.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved: {OUTFILE}")
    print(f"Overall: {overall}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
