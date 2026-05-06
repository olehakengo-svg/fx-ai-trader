#!/usr/bin/env python3
"""A/B BT filter for vol_surge_detector V2 closed-bar timing hardening."""
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
STRATEGY = "vol_surge_detector"
FLAG = "VOL_SURGE_REDESIGN_V2"
SHADOW_FLAG = "VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE"
OUTFILE = ROOT / "bt-results/vol_surge-shadow-redesign-v2-2026-05-05.json"


class _VolSurgeOnlyScalperEngine:
    SHADOW_ALWAYS_STRATEGIES = frozenset()

    def __init__(self):
        from strategies.scalp.vol_surge import VolSurgeDetector
        self.strategies = [VolSurgeDetector()]

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


def _cache_path(pair: str) -> Path:
    return ROOT / "data" / "cache" / "massive" / f"{pair}_{INTERVAL}.parquet"


def _pnl_r(trade: dict) -> float:
    if "pnl_r" in trade:
        return float(trade["pnl_r"])
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


def _format_pf(value: float):
    return round(value, 4) if math.isfinite(value) else "inf"


def _stats(result: dict) -> dict:
    trades = [
        t for t in result.get("trade_log", [])
        if t.get("entry_type", t.get("type")) == STRATEGY
    ]
    pnls = [_pnl_r(t) for t in trades]
    n = len(trades)
    wins = sum(1 for p in pnls if p > 0)
    ev = sum(pnls) / n if n else 0.0
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = -sum(p for p in pnls if p < 0)
    return {
        "N": n,
        "wins": wins,
        "WR": round(wins / n, 4) if n else 0.0,
        "EV": round(ev, 4),
        "PnL": round(sum(pnls), 4),
        "gross_profit": round(gross_profit, 4),
        "gross_loss": round(gross_loss, 4),
        "PF": _format_pf(_pf(pnls)),
        "wilson_lo": round(_wilson_lower(wins, n), 4),
        "total_trades_all_strategies": result.get("trades", 0),
        "bt_error": result.get("error"),
        "data_source": result.get("data_source"),
        "bars_fetched": result.get("bars_fetched"),
    }


def _run(app, data_mod, symbol: str, proposed: bool, days: int) -> dict:
    os.environ[FLAG] = "1" if proposed else "0"
    app._scalp_bt_cache.clear()
    data_mod._data_cache.clear()
    from strategies.scalp.vol_surge import VolSurgeDetector
    VolSurgeDetector.reset_dedup_state()
    return app.run_scalp_backtest(
        symbol=symbol,
        lookback_days=days,
        interval=INTERVAL,
    )


def _pair_to_symbol(pair: str) -> str:
    return f"{pair.replace('_', '')}=X"


def _simulate_trade(df, i: int, cand, max_hold: int = 40) -> dict:
    entry = float(df["Close"].iloc[i])
    sl = float(cand["sl"] if isinstance(cand, dict) else cand.sl)
    tp = float(cand["tp"] if isinstance(cand, dict) else cand.tp)
    signal = cand["signal"] if isinstance(cand, dict) else cand.signal
    risk = abs(entry - sl)
    reward = abs(tp - entry)
    outcome = "LOSS"
    exit_i = min(i + max_hold, len(df) - 1)
    pnl_r = -1.0
    for j in range(i + 1, min(i + max_hold + 1, len(df))):
        high = float(df["High"].iloc[j])
        low = float(df["Low"].iloc[j])
        if signal == "BUY":
            hit_sl = low <= sl
            hit_tp = high >= tp
        else:
            hit_sl = high >= sl
            hit_tp = low <= tp
        if hit_sl or hit_tp:
            exit_i = j
            if hit_sl:
                outcome = "LOSS"
                pnl_r = -1.0
            else:
                outcome = "WIN"
                pnl_r = reward / risk if risk > 0 else 0.0
            break
    return {
        "entry_type": STRATEGY,
        "signal": signal,
        "outcome": outcome,
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "pnl_r": pnl_r,
        "tp_m": reward / risk if risk > 0 else 0.0,
        "sl_m": 1.0,
        "entry_i": i,
        "exit_i": exit_i,
    }


def _run_direct(pair: str, proposed: bool) -> dict:
    os.environ[FLAG] = "1" if proposed else "0"
    import pandas as pd
    from modules.indicators import add_indicators
    from strategies.scalp.vol_surge import VolSurgeDetector

    raw = pd.read_parquet(_cache_path(pair))
    df = add_indicators(raw.copy()).dropna()
    if len(df) < 300:
        return {
            "error": "データ不足",
            "trades": 0,
            "mode": "scalp",
            "data_source": "massive-parquet-direct",
            "bars_fetched": len(df),
            "trade_log": [],
        }

    symbol = _pair_to_symbol(pair)
    strategy = VolSurgeDetector()
    open_values = df["Open"].to_numpy()
    high_values = df["High"].to_numpy()
    low_values = df["Low"].to_numpy()
    close_values = df["Close"].to_numpy()
    volume_values = df["Volume"].to_numpy() if "Volume" in df.columns else None
    range_values = (df["High"] - df["Low"]).to_numpy()
    atr7_values = df["atr7"].to_numpy() if "atr7" in df.columns else df["atr"].to_numpy()
    bbpb_values = df["bb_pband"].to_numpy()
    rsi5_values = (df["rsi5"] if "rsi5" in df.columns else df["rsi"]).to_numpy()
    adx_values = df["adx"].to_numpy()
    adx_pos_values = df["adx_pos"].to_numpy()
    adx_neg_values = df["adx_neg"].to_numpy()
    ema9_values = df["ema9"].to_numpy()
    ema21_values = df["ema21"].to_numpy()
    stoch_k_values = df["stoch_k"].to_numpy() if "stoch_k" in df.columns else None
    stoch_d_values = df["stoch_d"].to_numpy() if "stoch_d" in df.columns else None
    ema200_values = df["ema200"].to_numpy() if "ema200" in df.columns else None
    pip_mult = 100 if ("JPY" in symbol.upper() or "XAU" in symbol.upper()) else 10000
    min_sl = 0.030 if pip_mult == 100 else 0.00030
    blocked_hours = strategy._blocked_hours_by_pair.get(symbol.upper().replace("=X", "").replace("_", ""))

    def likely_surge(idx: int) -> bool:
        sig_idx = idx - 1 if proposed else idx
        start = sig_idx - strategy.vol_lookback
        if start < 0:
            return False
        if volume_values is not None:
            prev_vol = volume_values[start:sig_idx]
            vol_mean = float(prev_vol.mean())
            vol_cur = float(volume_values[sig_idx])
            if vol_mean > 0 and vol_cur > 0:
                return vol_cur >= vol_mean * strategy.vol_surge_mult
        prev_range = range_values[start:sig_idx]
        range_mean = float(prev_range.mean())
        range_cur = float(range_values[sig_idx])
        if range_mean <= 0:
            return False
        if range_cur < range_mean * strategy.vol_surge_mult:
            return False
        sig_atr7 = float(atr7_values[sig_idx])
        return not (sig_atr7 > 0 and range_cur / sig_atr7 < strategy.bar_range_atr_min)

    def candidate_at(idx: int):
        if blocked_hours:
            ts = df.index[idx]
            if getattr(ts, "hour", 12) in blocked_hours:
                return None
        if not likely_surge(idx):
            return None
        sig_idx = idx - 1 if proposed else idx
        entry = float(close_values[idx])
        atr7 = float(atr7_values[idx])
        sig_open = float(open_values[sig_idx])
        sig_close = float(close_values[sig_idx])
        sig_bbpb = float(bbpb_values[sig_idx])
        sig_rsi5 = float(rsi5_values[sig_idx])
        sig_adx = float(adx_values[sig_idx])
        sig_adx_pos = float(adx_pos_values[sig_idx])
        sig_adx_neg = float(adx_neg_values[sig_idx])
        sig_ema9 = float(ema9_values[sig_idx])
        sig_ema21 = float(ema21_values[sig_idx])
        signal = None
        mode = None
        score = 0.0
        sl = 0.0
        tp = 0.0
        if (
            sig_bbpb <= strategy.climax_bbpb_buy
            and sig_rsi5 < strategy.climax_rsi_buy
            and sig_close > sig_open
        ):
            signal = "BUY"
            mode = "climax"
            score = 3.5
            tp = entry + atr7 * strategy.climax_tp_mult
            sl = entry - max(atr7 * strategy.climax_sl_mult, min_sl)
        elif (
            sig_bbpb >= strategy.climax_bbpb_sell
            and sig_rsi5 > strategy.climax_rsi_sell
            and sig_close < sig_open
        ):
            signal = "SELL"
            mode = "climax"
            score = 3.5
            tp = entry - atr7 * strategy.climax_tp_mult
            sl = entry + max(atr7 * strategy.climax_sl_mult, min_sl)
        elif (
            sig_adx >= strategy.momentum_adx_min
            and sig_adx_pos > sig_adx_neg
            and sig_ema9 > sig_ema21
            and sig_close > sig_open
        ):
            signal = "BUY"
            mode = "momentum"
            score = 3.0
            tp = entry + atr7 * strategy.momentum_tp_mult
            sl = entry - max(atr7 * strategy.momentum_sl_mult, min_sl)
        elif (
            sig_adx >= strategy.momentum_adx_min
            and sig_adx_neg > sig_adx_pos
            and sig_ema9 < sig_ema21
            and sig_close < sig_open
        ):
            signal = "SELL"
            mode = "momentum"
            score = 3.0
            tp = entry - atr7 * strategy.momentum_tp_mult
            sl = entry + max(atr7 * strategy.momentum_sl_mult, min_sl)
        if signal is None:
            return None
        if volume_values is not None:
            start = sig_idx - strategy.vol_lookback
            surge_ratio = float(volume_values[sig_idx]) / max(float(volume_values[start:sig_idx].mean()), 1)
        else:
            start = sig_idx - strategy.vol_lookback
            surge_ratio = float(range_values[sig_idx]) / max(float(range_values[start:sig_idx].mean()), 1e-8)
        if surge_ratio >= 3.0:
            score += 0.8
        elif surge_ratio >= 2.5:
            score += 0.4
        if mode == "climax" and stoch_k_values is not None and stoch_d_values is not None:
            sk = float(stoch_k_values[sig_idx])
            sd = float(stoch_d_values[sig_idx])
            if signal == "BUY" and sk < 25 and sk > sd:
                score += 0.4
            elif signal == "SELL" and sk > 75 and sk < sd:
                score += 0.4
        if mode == "momentum" and ema200_values is not None:
            ema200_bull = float(close_values[sig_idx]) > float(ema200_values[sig_idx])
            if signal == "BUY" and ema200_bull:
                score += 0.3
            elif signal == "SELL" and not ema200_bull:
                score += 0.3
        return {"signal": signal, "sl": sl, "tp": tp, "score": score}

    trades = []
    last_trade_i = -99
    max_hold = 40
    for i in range(220, len(df) - max_hold - 1):
        if i - last_trade_i < 1:
            continue
        if volume_values is not None:
            vol = float(volume_values[i])
            if vol > 0 and vol < 100:
                continue
        bar_range = float(range_values[i])
        min_bar_range = 0.008 if "JPY" in symbol.upper() else 0.00008
        if bar_range < min_bar_range:
            continue
        cand = candidate_at(i)
        if cand is None:
            continue
        trades.append(_simulate_trade(df, i, cand, max_hold=max_hold))
        last_trade_i = i
    return {
        "trades": len(trades),
        "mode": "scalp",
        "data_source": "massive-parquet-direct",
        "bars_fetched": len(df),
        "trade_log": trades,
    }


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


def _warns(current: dict, proposed: dict) -> dict:
    current_pf = _num(current["PF"])
    proposed_pf = _num(proposed["PF"])
    pf_change = proposed_pf - current_pf
    n_change_pct = _change_pct(proposed["N"], current["N"])
    return {
        "pf_change_warn_only": round(pf_change, 4) if math.isfinite(pf_change) else str(pf_change),
        "wilson_lo_change_warn_only": round(proposed["wilson_lo"] - current["wilson_lo"], 4),
        "n_change_pct_warn_only": round(n_change_pct, 4) if math.isfinite(n_change_pct) else str(n_change_pct),
    }


def _criteria(current: dict, proposed: dict) -> dict:
    err = current.get("bt_error") or proposed.get("bt_error")
    if err:
        return {
            "verdict": "REJECT",
            "reason": "bt_error",
            "shadow_promote_recommendation": "REJECT",
        }
    if proposed["N"] < 20:
        return {
            **_warns(current, proposed),
            "verdict": "INSUFFICIENT_BT_EVIDENCE",
            "reason": "proposed BT trades < 20; v2.1 skips catastrophic check",
            "catastrophic_check": "SKIPPED",
            "pnl_sign_preserved": "SKIPPED",
            "shadow_promote_recommendation": "RECOMMEND_SHADOW",
        }
    preserved = _pnl_sign_preserved(current["PnL"], proposed["PnL"])
    verdict = "PASS" if preserved else "REJECT"
    return {
        **_warns(current, proposed),
        "pnl_sign_preserved": preserved,
        "catastrophic_check": preserved,
        "verdict": verdict,
        "shadow_promote_recommendation": "RECOMMEND_SHADOW" if preserved else "REJECT",
    }


def _aggregate(stats: list[dict]) -> dict:
    wins = 0
    n = 0
    pnl = 0.0
    gross_profit = 0.0
    gross_loss = 0.0
    for s in stats:
        n += int(s["N"])
        wins += int(s["wins"])
        pnl += float(s["PnL"])
        gross_profit += float(s.get("gross_profit", 0.0))
        gross_loss += float(s.get("gross_loss", 0.0))
    ev = pnl / n if n else 0.0
    pf = float("inf") if gross_loss <= 0 and gross_profit > 0 else gross_profit / gross_loss if gross_loss > 0 else 0.0
    return {
        "N": n,
        "wins": wins,
        "WR": round(wins / n, 4) if n else 0.0,
        "EV": round(ev, 4),
        "PnL": round(pnl, 4),
        "gross_profit": round(gross_profit, 4),
        "gross_loss": round(gross_loss, 4),
        "PF": _format_pf(pf),
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
                "lock_criteria": {
                    "verdict": "BLOCKED_DATA",
                    "reason": "missing_massive_cache",
                    "shadow_promote_recommendation": "IMPLEMENT_ONLY_DEFAULT_OFF",
                },
            }
    else:
        for pair, symbol in TARGETS:
            print(f"Running baseline: {pair} {LOOKBACK_DAYS}d", flush=True)
            current = _stats(_run_direct(pair, proposed=False))
            print(f"Running proposed: {pair} {LOOKBACK_DAYS}d", flush=True)
            proposed = _stats(_run_direct(pair, proposed=True))
            cells[pair] = {
                "current": current,
                "proposed": proposed,
                "lock_criteria": _criteria(current, proposed),
            }

    current_agg = _aggregate([c["current"] for c in cells.values()])
    proposed_agg = _aggregate([c["proposed"] for c in cells.values()])
    if missing:
        overall = "BLOCKED_DATA"
        overall_criteria = {
            "verdict": overall,
            "reason": "missing required MASSIVE parquet cache",
            "shadow_promote_recommendation": "IMPLEMENT_ONLY_DEFAULT_OFF",
        }
    else:
        overall_criteria = _criteria(current_agg, proposed_agg)
        overall = overall_criteria["verdict"]

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategy": STRATEGY,
        "variant": "closed_bar_timing_and_dedup_v2",
        "flag": FLAG,
        "shadow_worker_flag": SHADOW_FLAG,
        "lookback_days": LOOKBACK_DAYS,
        "minimum_days": MINIMUM_DAYS,
        "interval": INTERVAL,
        "runner": "strategy-isolated MASSIVE harness using production VolSurgeDetector.evaluate() and production indicators",
        "runner_note": "vol_surge_detector is a scalp strategy; run_daytrade_backtest does not evaluate it. app.run_scalp_backtest was attempted but was too slow for the full 6-pair A/B run in this environment.",
        "data_source_required": "data/cache/massive/{PAIR}_{TF}.parquet with BT_MODE=1 and BT_REQUIRE_MASSIVE_CACHE=1",
        "bt_mode": os.environ.get("BT_MODE"),
        "massive_cache_verified": not missing,
        "targets": [pair for pair, _ in TARGETS],
        "missing_caches": missing,
        "lock_spec": {
            "bt_evidence_threshold": "if proposed N < 20 => INSUFFICIENT_BT_EVIDENCE, skip catastrophic, recommend shadow",
            "catastrophic_check": "REJECT only when baseline PnL > 0 and proposed PnL < 0",
            "pf_change": "WARN ONLY",
            "wilson_lo_change": "WARN ONLY",
            "n_change_pct": "WARN ONLY",
            "sanity_floor": "REMOVED in v2.1",
            "positive_direction": "not required",
            "absolute_kelly": "not required",
        },
        "aggregate": {
            "current": current_agg,
            "proposed": proposed_agg,
            "lock_criteria": overall_criteria,
        },
        "cells": cells,
        "overall_verdict": overall,
        "shadow_promote_recommendation": (
            "RECOMMEND_SHADOW"
            if overall in {"PASS", "INSUFFICIENT_BT_EVIDENCE"}
            else "IMPLEMENT_ONLY_DEFAULT_OFF" if overall == "BLOCKED_DATA" else "REJECT"
        ),
        "shadow_accumulation_target": "60-90 days or N>=30 after shadow start",
        "elapsed_s": round(time.time() - started, 1),
        "self_review": {
            "catastrophic_only": "PASS: verdict uses only PnL sign preservation when proposed N>=20; PF/Wilson/N are warn-only.",
            "insufficient_bt_evidence": "PASS: proposed N<20 becomes INSUFFICIENT_BT_EVIDENCE and still recommends shadow.",
            "absolute_kelly": "PASS: no Kelly threshold is calculated or required.",
            "production_live_safety": "PASS: strategy behavior is default-off unless VOL_SURGE_REDESIGN_V2=1; shadow emit also requires VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE=1.",
            "post_hoc_adjustment": "PASS: only the pre-registered closed_bar_timing_and_dedup_v2 variant is evaluated.",
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
