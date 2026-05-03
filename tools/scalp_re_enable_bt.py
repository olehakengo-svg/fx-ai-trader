#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import os
import sys
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

os.environ.setdefault("BT_MODE", "1")
os.environ.setdefault("NO_AUTOSTART", "1")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import modules.demo_trader as _demo_trader_module
from modules.bt_vec_harness import HtfFeatureSpec, VecBacktestRunner, _load_local_cache
from modules.stats_utils import kelly_criterion
from research.edge_discovery.significance import binomial_one_sided_p
from tools.cell_edge_audit import wilson_lower
from tools.cell_negative_edge_audit import wilson_upper_at


class _StubDemoTrader:
    def __init__(self, db=None):
        self.db = db


_demo_trader_module.DemoTrader = _StubDemoTrader

import app
from tools.bt_common import compute_wrapper_fingerprint

app.get_master_bias = lambda symbol: {"direction": "neutral", "label": "offline", "score": 0}


PRIMARY_PAIR = "USD_JPY"
PRIMARY_STRATEGY = "mtf_regime_trend_cascade_scalp"
PRIMARY_INTERVAL = "5m"
PRIMARY_LOOKBACK = 180
DEFAULT_ENGINE_TIMEOUT_SECONDS = int(os.environ.get("SCALP_RE_ENABLE_BT_TIMEOUT", "900"))
LIVE_COMPARABLE_CUTOFF = "2026-04-08T00:00:00+00:00"
USDJPY_BEV_WR = 0.344
BONFERRONI_ALPHA = 0.05
BONFERRONI_K = 5
BONFERRONI_JUSTIFICATION = (
    "Decision pool fixed ex ante as 5 scalp candidates: primary "
    "mtf_regime_trend_cascade_scalp plus 4 roadmap-v2.1 alternatives "
    "(bb_squeeze_breakout, engulfing_bb, fib_reversal, sr_channel_reversal)."
)

VERDICT_THRESHOLDS = {
    "promote": {
        "min_n": 30,
        "min_pf": 1.30,
        "min_wilson_lo_pp_over_bev": 5.0,
        "min_pf_is": 1.20,
        "min_pf_oos": 1.20,
        "max_dd_pct": 30.0,
        "bonf_alpha_div_k": BONFERRONI_ALPHA / BONFERRONI_K,
    },
    "shadow": {
        "min_n": 30,
        "min_pf": 1.10,
        "min_wilson_lo_pp_over_bev": 0.0,
        "min_pf_is": 1.00,
        "min_pf_oos": 1.00,
        "max_dd_pct": 30.0,
    },
}

SCALP_POOL = {
    "mtf_regime_trend_cascade_scalp": {
        "pair": "USD_JPY",
        "interval": "5m",
        "roadmap_ev_pips": None,
    },
    "bb_squeeze_breakout": {
        "pair": "USD_JPY",
        "interval": "5m",
        "roadmap_ev_pips": 1.030,
    },
    "engulfing_bb": {
        "pair": "USD_JPY",
        "interval": "5m",
        "roadmap_ev_pips": 0.677,
    },
    "fib_reversal": {
        "pair": "EUR_USD",
        "interval": "1m",
        "roadmap_ev_pips": 0.426,
    },
    "sr_channel_reversal": {
        "pair": "EUR_USD",
        "interval": "5m",
        "roadmap_ev_pips": 0.231,
    },
}

ALTERNATIVE_SCAN_ORDER = (
    "bb_squeeze_breakout",
    "engulfing_bb",
    "fib_reversal",
    "sr_channel_reversal",
)

ROADMAP_ALT_REFERENCE = {
    "bb_squeeze_breakout": {"n": 11, "wins": 10, "wr": 90.9, "ev": 1.030},
    "engulfing_bb": {"n": 17, "wins": 15, "wr": 88.2, "ev": 0.677},
    "fib_reversal": {"n": 40, "wins": 29, "wr": 72.5, "ev": 0.426},
    "sr_channel_reversal": {"n": 17, "wins": 12, "wr": 70.6, "ev": 0.231},
}


@dataclass
class Stats:
    n: int
    wins: int
    losses: int
    win_rate: float
    ev_pips: float
    profit_factor: float | None
    gross_profit: float
    gross_loss_abs: float
    avg_win_pips: float | None
    avg_loss_pips_abs: float | None
    wilson_lo_95: float
    wilson_hi_95: float
    bev_wr: float
    bonferroni_p: float
    bonferroni_alpha_div_k: float
    kelly_full: float
    kelly_half: float
    kelly_edge: float
    max_drawdown_pips: float
    max_drawdown_pct: float | None
    walk_forward: dict[str, Any]


def normalize_symbol(symbol: str) -> str:
    s = (symbol or "").upper().replace("=X", "").replace("/", "_")
    if "_" in s:
        return s
    if len(s) == 6:
        return f"{s[:3]}_{s[3:]}"
    return s


def yahoo_symbol(pair: str) -> str:
    return normalize_symbol(pair).replace("_", "") + "=X"


def parse_ts(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def interval_to_timedelta(interval: str) -> timedelta:
    value = interval.lower()
    if value.endswith("m"):
        return timedelta(minutes=int(value[:-1]))
    if value.endswith("h"):
        return timedelta(hours=int(value[:-1]))
    raise ValueError(f"unsupported interval: {interval}")


def load_local_bt_frame(pair: str, interval: str, lookback_days: int):
    df = _load_local_cache(yahoo_symbol(pair), interval, lookback_days)
    if df is None or len(df) < 100:
        raise RuntimeError(
            f"Local parquet cache missing or too small for pair={pair} interval={interval} "
            f"lookback_days={lookback_days}"
        )
    df = app.add_indicators(df.copy()).dropna()
    if len(df) < 100:
        raise RuntimeError(
            f"Indicator-enriched local cache too small for pair={pair} interval={interval}"
        )
    return df


def extract_trade_pnl(trade: dict[str, Any]) -> float:
    value = trade.get("pnl_pips")
    if value is not None:
        return float(value)
    entry = float(trade.get("entry_price", trade.get("ep", trade.get("entry_px", 0.0))) or 0.0)
    exit_px = float(trade.get("exit_price", 0.0) or 0.0)
    sig = str(trade.get("sig", trade.get("signal", "")) or "").upper()
    if entry and exit_px and sig in {"BUY", "SELL"}:
        pip_mult = 100 if "JPY" in normalize_symbol(str(trade.get("symbol", PRIMARY_PAIR))) else 10000
        raw = (exit_px - entry) * pip_mult if sig == "BUY" else (entry - exit_px) * pip_mult
        return float(raw)
    return 0.0


def trade_time(trade: dict[str, Any]) -> datetime | None:
    return (
        parse_ts(trade.get("entry_time"))
        or parse_ts(trade.get("ts"))
        or parse_ts(trade.get("time"))
    )


def sort_trades(trades: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        list(trades),
        key=lambda t: trade_time(t) or datetime.min.replace(tzinfo=timezone.utc),
    )


def max_drawdown(pnls: list[float]) -> tuple[float, float | None]:
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    max_dd_pct: float | None = 0.0
    for pnl in pnls:
        equity += pnl
        if equity > peak:
            peak = equity
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd
            max_dd_pct = (dd / peak * 100.0) if peak > 0 else None
    return round(max_dd, 3), (round(max_dd_pct, 3) if max_dd_pct is not None else None)


def profit_factor(gross_profit: float, gross_loss_abs: float) -> float | None:
    if gross_loss_abs <= 0:
        return None if gross_profit <= 0 else math.inf
    return gross_profit / gross_loss_abs


def walk_forward_stats(
    trades: list[dict[str, Any]],
    midpoint: datetime,
    bev_wr: float,
) -> dict[str, Any]:
    is_trades = [t for t in trades if (trade_time(t) or midpoint) < midpoint]
    oos_trades = [t for t in trades if (trade_time(t) or midpoint) >= midpoint]
    return {
        "split": "50/50 time split",
        "midpoint_utc": midpoint.isoformat(),
        "is": stats_from_trades(is_trades, bev_wr, midpoint, include_wf=False),
        "oos": stats_from_trades(oos_trades, bev_wr, midpoint, include_wf=False),
    }


def stats_from_trades(
    trades: list[dict[str, Any]],
    bev_wr: float,
    midpoint: datetime,
    *,
    include_wf: bool = True,
) -> dict[str, Any]:
    ordered = sort_trades(trades)
    pnls = [extract_trade_pnl(t) for t in ordered]
    n = len(ordered)
    wins = sum(1 for p in pnls if p > 0)
    losses = sum(1 for p in pnls if p < 0)
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss_abs = abs(sum(p for p in pnls if p < 0))
    wr = wins / n if n else 0.0
    ev = sum(pnls) / n if n else 0.0
    pf = profit_factor(gross_profit, gross_loss_abs)
    avg_win = (gross_profit / wins) if wins else None
    avg_loss_abs = (gross_loss_abs / losses) if losses else None
    if avg_win is not None and avg_loss_abs is not None and 0 < wr < 1:
        kelly = kelly_criterion(wr, avg_win, avg_loss_abs)
    else:
        kelly = {"full_kelly": 0.0, "half_kelly": 0.0, "edge": 0.0}
    w_lo = wilson_lower(wins, n)
    w_hi = wilson_upper_at(wr, n) if n else 0.0
    p_value = binomial_one_sided_p(wins, n, bev_wr) if n else 1.0
    dd_pips, dd_pct = max_drawdown(pnls)
    payload = {
        "n": n,
        "wins": wins,
        "losses": losses,
        "win_rate": round(wr * 100.0, 3),
        "ev_pips": round(ev, 3),
        "profit_factor": ("inf" if pf == math.inf else (round(pf, 3) if pf is not None else None)),
        "gross_profit": round(gross_profit, 3),
        "gross_loss_abs": round(gross_loss_abs, 3),
        "avg_win_pips": round(avg_win, 3) if avg_win is not None else None,
        "avg_loss_pips_abs": round(avg_loss_abs, 3) if avg_loss_abs is not None else None,
        "wilson_lo_95": round(w_lo * 100.0, 3),
        "wilson_hi_95": round(w_hi * 100.0, 3),
        "bev_wr": round(bev_wr * 100.0, 3),
        "bonferroni_p": round(p_value, 8),
        "bonferroni_alpha_div_k": round(BONFERRONI_ALPHA / BONFERRONI_K, 8),
        "kelly_full": round(float(kelly.get("full_kelly", 0.0)), 6),
        "kelly_half": round(float(kelly.get("half_kelly", 0.0)), 6),
        "kelly_edge": round(float(kelly.get("edge", 0.0)), 6),
        "max_drawdown_pips": dd_pips,
        "max_drawdown_pct": dd_pct,
    }
    if include_wf:
        payload["walk_forward"] = walk_forward_stats(ordered, midpoint, bev_wr)
    return payload


def determine_verdict(stats: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if stats["n"] < VERDICT_THRESHOLDS["promote"]["min_n"]:
        reasons.append(f"N<{VERDICT_THRESHOLDS['promote']['min_n']}")
        return "Insufficient", reasons

    wf = stats.get("walk_forward", {})
    is_stats = wf.get("is", {})
    oos_stats = wf.get("oos", {})
    wf_promote = (
        (is_stats.get("profit_factor") not in (None, "inf") and float(is_stats["profit_factor"]) >= VERDICT_THRESHOLDS["promote"]["min_pf_is"])
        and (oos_stats.get("profit_factor") not in (None, "inf") and float(oos_stats["profit_factor"]) >= VERDICT_THRESHOLDS["promote"]["min_pf_oos"])
    )
    wf_shadow = (
        (is_stats.get("profit_factor") not in (None,) and (is_stats.get("profit_factor") == "inf" or float(is_stats["profit_factor"]) >= VERDICT_THRESHOLDS["shadow"]["min_pf_is"]))
        and (oos_stats.get("profit_factor") not in (None,) and (oos_stats.get("profit_factor") == "inf" or float(oos_stats["profit_factor"]) >= VERDICT_THRESHOLDS["shadow"]["min_pf_oos"]))
    )
    pf = stats.get("profit_factor")
    dd_pct = stats.get("max_drawdown_pct")
    wilson_margin_pp = stats["wilson_lo_95"] - stats["bev_wr"]
    bonf_pass = stats["bonferroni_p"] < VERDICT_THRESHOLDS["promote"]["bonf_alpha_div_k"]
    dd_ok = dd_pct is not None and dd_pct <= VERDICT_THRESHOLDS["promote"]["max_dd_pct"]

    if (
        pf not in (None,) and (pf == "inf" or float(pf) >= VERDICT_THRESHOLDS["promote"]["min_pf"])
        and wilson_margin_pp > VERDICT_THRESHOLDS["promote"]["min_wilson_lo_pp_over_bev"]
        and wf_promote
        and bonf_pass
        and dd_ok
    ):
        return "Promote", reasons

    if (
        pf not in (None,) and (pf == "inf" or float(pf) >= VERDICT_THRESHOLDS["shadow"]["min_pf"])
        and wilson_margin_pp > VERDICT_THRESHOLDS["shadow"]["min_wilson_lo_pp_over_bev"] - 1e-9
        and wf_shadow
        and dd_ok
    ):
        return "Shadow", reasons

    if pf in (None,):
        reasons.append("PF unavailable")
    elif pf != "inf" and float(pf) < VERDICT_THRESHOLDS["shadow"]["min_pf"]:
        reasons.append(f"PF<{VERDICT_THRESHOLDS['shadow']['min_pf']}")
    if wilson_margin_pp <= 0:
        reasons.append("Wilson_lo<=BEV_WR")
    if not wf_shadow:
        reasons.append("WF shadow threshold failed")
    if dd_pct is None or dd_pct > VERDICT_THRESHOLDS["shadow"]["max_dd_pct"]:
        reasons.append("max DD > 30% or undefined")
    if not bonf_pass:
        reasons.append("Bonferroni threshold failed for Promote")
    return "Reject", reasons


@contextmanager
def capture_run_scalp_trades():
    captured: dict[str, Any] = {"trades": None}
    previous = sys.gettrace()

    def tracer(frame, event, arg):
        if frame.f_code.co_name == "run_scalp_backtest":
            if event == "return":
                trades = frame.f_locals.get("trades")
                if isinstance(trades, list):
                    captured["trades"] = [dict(t) for t in trades]
            return tracer
        return tracer

    sys.settrace(tracer)
    try:
        yield captured
    finally:
        sys.settrace(previous)


def run_standard_bt(pair: str, strategy: str, interval: str, lookback_days: int) -> dict[str, Any]:
    df = load_local_bt_frame(pair, interval, lookback_days)
    midpoint = (df.index.max().to_pydatetime() - timedelta(days=lookback_days / 2)).astimezone(timezone.utc)
    with capture_run_scalp_trades() as cap:
        result = app.run_scalp_backtest(
            symbol=yahoo_symbol(pair),
            lookback_days=lookback_days,
            interval=interval,
            _df_override=df,
        )
    raw_trades = cap.get("trades") or []
    for trade in raw_trades:
        trade.setdefault("symbol", pair)
    filtered = [t for t in raw_trades if t.get("entry_type") == strategy]
    stats = stats_from_trades(filtered, USDJPY_BEV_WR if normalize_symbol(pair) == PRIMARY_PAIR else USDJPY_BEV_WR, midpoint)
    return {
        "summary": result,
        "bars_fetched": len(df),
        "window_start_utc": df.index.min().isoformat(),
        "window_end_utc": df.index.max().isoformat(),
        "midpoint_utc": midpoint.isoformat(),
        "raw_trade_count_all": len(raw_trades),
        "raw_trade_count_strategy": len(filtered),
        "strategy_stats": stats,
        "qualification_note": (
            "run_scalp_backtest keeps a function-local QUALIFIED_TYPES gate; "
            "this wrapper does not edit app.py, so any omitted strategy remains suppressed."
        ),
    }


def make_vec_strategy(name: str):
    if name == "mtf_regime_trend_cascade_scalp":
        from strategies.scalp.mtf_regime_trend_cascade_scalp import MtfRegimeTrendCascadeScalp

        return MtfRegimeTrendCascadeScalp()
    raise ValueError(f"vec harness not registered for strategy={name}")


def run_vec_bt(pair: str, strategy: str, interval: str, lookback_days: int) -> dict[str, Any]:
    if strategy != PRIMARY_STRATEGY or interval != PRIMARY_INTERVAL:
        return {
            "available": False,
            "reason": "Vector oracle is only wired for mtf_regime_trend_cascade_scalp on 5m/1m cache stack.",
        }
    spec = HtfFeatureSpec(
        include_hurst_m15=True,
        include_range_20_m15=True,
        include_h1=True,
        inject_spread=2.14,
    )
    runner = VecBacktestRunner(
        spec=spec,
        strategy_factory=lambda: make_vec_strategy(strategy),
    )
    result = runner.run(symbol=yahoo_symbol(pair), days=lookback_days, verbose=False)
    trades = [dict(t) for t in result.get("trades_full", [])]
    for trade in trades:
        trade["entry_type"] = strategy
        trade["symbol"] = pair
    df = _load_local_cache(yahoo_symbol(pair), "1m", lookback_days)
    if df is None or len(df) < 100:
        raise RuntimeError("1m local cache missing for vec harness midpoint calculation")
    midpoint = (df.index.max().to_pydatetime() - timedelta(days=lookback_days / 2)).astimezone(timezone.utc)
    stats = stats_from_trades(trades, USDJPY_BEV_WR if normalize_symbol(pair) == PRIMARY_PAIR else USDJPY_BEV_WR, midpoint)
    return {
        "available": True,
        "summary": result,
        "bars_1m": len(df),
        "midpoint_utc": midpoint.isoformat(),
        "strategy_stats": stats,
    }


def empty_stats(bev_wr: float = USDJPY_BEV_WR) -> dict[str, Any]:
    midpoint = datetime.now(timezone.utc)
    return stats_from_trades([], bev_wr, midpoint)


def unavailable_engine(reason: str) -> dict[str, Any]:
    return {
        "available": False,
        "reason": reason,
        "bars_fetched": 0,
        "window_start_utc": None,
        "window_end_utc": None,
        "midpoint_utc": datetime.now(timezone.utc).isoformat(),
        "raw_trade_count_all": 0,
        "raw_trade_count_strategy": 0,
        "strategy_stats": empty_stats(),
    }


def _engine_worker(queue: mp.Queue, fn, args: tuple[Any, ...]) -> None:
    try:
        queue.put({"ok": True, "value": fn(*args)})
    except Exception as exc:
        queue.put({"ok": False, "error": str(exc)})


def run_engine_bounded(label: str, fn, *args, timeout_seconds: int = DEFAULT_ENGINE_TIMEOUT_SECONDS) -> dict[str, Any]:
    if timeout_seconds <= 0:
        try:
            out = fn(*args)
            out.setdefault("available", True)
            return out
        except Exception as exc:
            return unavailable_engine(str(exc))

    queue: mp.Queue = mp.Queue(maxsize=1)
    proc = mp.Process(target=_engine_worker, args=(queue, fn, args))
    proc.start()
    proc.join(timeout_seconds)
    if proc.is_alive():
        proc.terminate()
        proc.join(5)
        return unavailable_engine(f"{label} exceeded {timeout_seconds}s timeout")
    if queue.empty():
        return unavailable_engine(f"{label} exited without result")
    result = queue.get()
    if not result.get("ok"):
        return unavailable_engine(result.get("error", f"{label} failed"))
    out = result["value"]
    out.setdefault("available", True)
    return out


def compare_engines(standard_stats: dict[str, Any], vec_stats: dict[str, Any]) -> dict[str, Any]:
    std_n = standard_stats["n"]
    vec_n = vec_stats["n"]
    if vec_n == 0:
        gap_pct = None
    else:
        gap_pct = abs(std_n - vec_n) / vec_n * 100.0
    return {
        "standard_n": std_n,
        "vec_n": vec_n,
        "n_gap_pct": round(gap_pct, 3) if gap_pct is not None else None,
        "within_tolerance_5pct": gap_pct is not None and gap_pct <= 5.0,
        "oracle": "vec_harness" if gap_pct is None or gap_pct > 5.0 else "standard_bt",
    }


def live_comparable_subset(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cutoff = parse_ts(LIVE_COMPARABLE_CUTOFF)
    assert cutoff is not None
    return [t for t in trades if (trade_time(t) or cutoff) >= cutoff]


def serialize_payload(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n")


def format_float(value: Any, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    if value == "inf":
        return "inf"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def build_markdown(payload: dict[str, Any], abbreviated: bool) -> str:
    primary = payload["primary"]
    selected = primary["selected"]
    selected_stats = selected["strategy_stats"]
    lines = [
        f"# Scalp Re-enable BT Summary — {payload['run_at'][:10]}",
        "",
        f"Strategy: `{payload['config']['strategy']}`",
        f"Pair: `{payload['config']['pair']}`",
        f"Interval: `{payload['config']['interval']}`",
        f"Lookback: `{payload['config']['lookback_days']}d`",
        f"Verdict: `{primary['verdict']}`",
        "",
        "## Pre-registered thresholds",
        "",
        f"- Promote: N>={VERDICT_THRESHOLDS['promote']['min_n']}, PF>={VERDICT_THRESHOLDS['promote']['min_pf']}, Wilson_lo > BEV+5pp, WF PF_IS/OOS>={VERDICT_THRESHOLDS['promote']['min_pf_is']}, Bonferroni p<{VERDICT_THRESHOLDS['promote']['bonf_alpha_div_k']:.5f}, max DD<=30%",
        f"- Shadow: N>={VERDICT_THRESHOLDS['shadow']['min_n']}, PF>={VERDICT_THRESHOLDS['shadow']['min_pf']}, Wilson_lo > BEV, WF PF_IS/OOS>={VERDICT_THRESHOLDS['shadow']['min_pf_is']}, max DD<=30%",
        f"- Reject: anything else. Insufficient: N<{VERDICT_THRESHOLDS['promote']['min_n']}.",
        "",
        "## Selected engine stats",
        "",
        f"- Engine: `{primary['selected_engine']}`",
        f"- N/W/L: {selected_stats['n']} / {selected_stats['wins']} / {selected_stats['losses']}",
        f"- WR: {selected_stats['win_rate']:.3f}%",
        f"- EV: {selected_stats['ev_pips']:.3f} pip/trade",
        f"- PF: {format_float(selected_stats['profit_factor'])}",
        f"- Wilson 95%: [{selected_stats['wilson_lo_95']:.3f}%, {selected_stats['wilson_hi_95']:.3f}%]",
        f"- BEV_WR: {selected_stats['bev_wr']:.3f}%",
        f"- Bonferroni: K={payload['bonferroni']['k']}, p={selected_stats['bonferroni_p']}, alpha/K={selected_stats['bonferroni_alpha_div_k']}",
        f"- Kelly half: {selected_stats['kelly_half']:.6f}",
        f"- Max DD: {selected_stats['max_drawdown_pips']:.3f} pip, {format_float(selected_stats['max_drawdown_pct'])}%",
        "",
        "## Walk-forward 50/50",
        "",
        f"- IS: N={selected_stats['walk_forward']['is']['n']}, WR={selected_stats['walk_forward']['is']['win_rate']:.3f}%, PF={format_float(selected_stats['walk_forward']['is']['profit_factor'])}, EV={selected_stats['walk_forward']['is']['ev_pips']:.3f}",
        f"- OOS: N={selected_stats['walk_forward']['oos']['n']}, WR={selected_stats['walk_forward']['oos']['win_rate']:.3f}%, PF={format_float(selected_stats['walk_forward']['oos']['profit_factor'])}, EV={selected_stats['walk_forward']['oos']['ev_pips']:.3f}",
        "",
        "## Engine comparison",
        "",
        f"- Standard BT N: {primary['standard']['strategy_stats']['n']}",
    ]
    if primary["standard"].get("available") is False:
        lines.append(f"- Standard BT: unavailable ({primary['standard'].get('reason')})")
    if primary["vec"].get("available"):
        lines.extend(
            [
                f"- Vec harness N: {primary['vec']['strategy_stats']['n']}",
                f"- N gap: {format_float(primary['comparison']['n_gap_pct'])}%",
                f"- Oracle selection: `{primary['comparison']['oracle']}`",
            ]
        )
    else:
        lines.append(f"- Vec harness: unavailable ({primary['vec']['reason']})")
    if not abbreviated:
        live = primary["live_comparable_selected"]
        lines.extend(
            [
                "",
                "## Live-comparable subset",
                "",
                f"- Cutoff: `{LIVE_COMPARABLE_CUTOFF}`",
                f"- N/W/L: {live['n']} / {live['wins']} / {live['losses']}",
                f"- WR: {live['win_rate']:.3f}%",
                f"- EV: {live['ev_pips']:.3f}",
                f"- PF: {format_float(live['profit_factor'])}",
            ]
        )
    return "\n".join(lines) + "\n"


def build_prereg_markdown(payload: dict[str, Any], alternatives: list[dict[str, Any]] | None = None) -> str:
    primary = payload["primary"]
    selected = primary["selected"]
    stats = selected["strategy_stats"]
    live = primary["live_comparable_selected"]
    alt_lines: list[str] = []
    if alternatives:
        alt_lines.extend(["## 8. Alternative candidate scan", ""])
        for alt in alternatives:
            if alt.get("available") is False:
                alt_lines.append(
                    f"- `{alt['strategy']}` {alt['pair']} {alt['interval']}: not run "
                    f"({alt.get('reason', 'unavailable')})"
                )
                continue
            alt_lines.append(
                f"- `{alt['strategy']}` {alt['pair']} {alt['interval']}: verdict `{alt['verdict']}`, "
                f"N={alt['selected']['strategy_stats']['n']}, PF={format_float(alt['selected']['strategy_stats']['profit_factor'])}, "
                f"WR={alt['selected']['strategy_stats']['win_rate']:.3f}%, EV={alt['selected']['strategy_stats']['ev_pips']:.3f}"
            )
        alt_lines.append("")
    else:
        alt_lines.extend(
            [
                "## 8. Alternative candidate scan",
                "",
                "- Pending: fill after abbreviated scans if primary verdict is Reject or Insufficient.",
                "",
            ]
        )
    verdict_note = {
        "Promote": "Promote",
        "Shadow": "Shadow",
        "Reject": "Reject",
        "Insufficient": "Insufficient",
    }[primary["verdict"]]
    lines = [
        "# Scalp re-enable pre-registration — 2026-05-03",
        "",
        f"**Strategy**: `{payload['config']['strategy']}` on `{payload['config']['pair']}` `{payload['config']['interval']}`",
        f"**Rule**: `R1 Slow & Strict`",
        f"**BT engine of record**: `{primary['selected_engine']}`",
        f"**Current verdict**: `{verdict_note}`",
        "",
        "## 1. Strategy",
        "",
        "- Objective: evaluate whether `mtf_regime_trend_cascade_scalp` should be re-enabled for Scalp N-acceleration without editing `app.py` in this task.",
        "- BT source of truth for the decision is the 180d deterministic local-cache run, cross-checked against the vector harness oracle.",
        "- Live remains the source of truth for any later production promotion; this document only locks the decision thresholds and the BT evidence.",
        "",
        "## 2. Pre-registered thresholds",
        "",
        f"- Promote: N>={VERDICT_THRESHOLDS['promote']['min_n']}, PF>={VERDICT_THRESHOLDS['promote']['min_pf']}, Wilson_lo > BEV_WR + 5pp, WF PF_IS>={VERDICT_THRESHOLDS['promote']['min_pf_is']} and PF_OOS>={VERDICT_THRESHOLDS['promote']['min_pf_oos']}, Bonferroni p<{VERDICT_THRESHOLDS['promote']['bonf_alpha_div_k']:.5f}, max DD<=30%.",
        f"- Shadow: N>={VERDICT_THRESHOLDS['shadow']['min_n']}, PF>={VERDICT_THRESHOLDS['shadow']['min_pf']}, Wilson_lo > BEV_WR, WF PF_IS>={VERDICT_THRESHOLDS['shadow']['min_pf_is']} and PF_OOS>={VERDICT_THRESHOLDS['shadow']['min_pf_oos']}, max DD<=30%.",
        f"- Reject: any other configuration. Insufficient: N<{VERDICT_THRESHOLDS['promote']['min_n']}.",
        "",
        "## 3. BT evidence",
        "",
        f"- Engine selected for verdict: `{primary['selected_engine']}`. Standard BT strategy N={primary['standard']['strategy_stats']['n']}; vec harness strategy N={primary['vec']['strategy_stats']['n'] if primary['vec'].get('available') else 'n/a'}.",
        f"- Standard BT availability: `{primary['standard'].get('available', True)}`; reason: {primary['standard'].get('reason', 'completed')}.",
        f"- Vec harness availability: `{primary['vec'].get('available', True)}`; reason: {primary['vec'].get('reason', 'completed')}.",
        f"- N / Wins / Losses: {stats['n']} / {stats['wins']} / {stats['losses']}",
        f"- WR: {stats['win_rate']:.3f}%",
        f"- EV: {stats['ev_pips']:.3f} pip/trade",
        f"- PF: {format_float(stats['profit_factor'])}",
        f"- Wilson 95% CI: [{stats['wilson_lo_95']:.3f}%, {stats['wilson_hi_95']:.3f}%]",
        f"- BEV_WR (USD_JPY): {stats['bev_wr']:.3f}%",
        f"- Bonferroni one-sided p: {stats['bonferroni_p']}",
        f"- Kelly half: {stats['kelly_half']:.6f}",
        f"- Max DD: {stats['max_drawdown_pips']:.3f} pip / {format_float(stats['max_drawdown_pct'])}%",
        "",
        "## 4. Walk-Forward summary",
        "",
        f"- Split: {stats['walk_forward']['split']} at {stats['walk_forward']['midpoint_utc']}",
        f"- IS: N={stats['walk_forward']['is']['n']}, WR={stats['walk_forward']['is']['win_rate']:.3f}%, PF={format_float(stats['walk_forward']['is']['profit_factor'])}, EV={stats['walk_forward']['is']['ev_pips']:.3f}",
        f"- OOS: N={stats['walk_forward']['oos']['n']}, WR={stats['walk_forward']['oos']['win_rate']:.3f}%, PF={format_float(stats['walk_forward']['oos']['profit_factor'])}, EV={stats['walk_forward']['oos']['ev_pips']:.3f}",
        "",
        "## 5. Bonferroni K-value justification",
        "",
        f"- K={BONFERRONI_K}. {BONFERRONI_JUSTIFICATION}",
        f"- Alpha/K = {VERDICT_THRESHOLDS['promote']['bonf_alpha_div_k']:.5f}.",
        "",
        "## 6. Verdict",
        "",
        f"- Locked verdict: `{primary['verdict']}`.",
        f"- Deterministic reasons: {', '.join(primary['verdict_reasons']) if primary['verdict_reasons'] else 'all pre-registered Promote conditions passed'}",
        f"- Live-comparable subset from {LIVE_COMPARABLE_CUTOFF}: N={live['n']}, WR={live['win_rate']:.3f}%, EV={live['ev_pips']:.3f}, PF={format_float(live['profit_factor'])}.",
        "",
        "## 7. Lock statement",
        "",
        "- The thresholds above were encoded in `tools/scalp_re_enable_bt.py` before the BT output was reviewed.",
        "- This task does not edit `app.py` `QUALIFIED_TYPES`; any later registration must happen in a separate reviewed task.",
        "",
    ]
    lines.extend(alt_lines)
    lines.extend(
        [
            "## 9. Live N target",
            "",
            "- Minimum live target after any registration step: N>=30 before claiming Promote-quality evidence from Live.",
            "- If registered as Shadow, lot remains 0.1 until live N and BT/live drift checks are reviewed separately.",
            "",
            "## 10. Stopping criteria",
            "",
            "- Stop and do not re-enable if live N stays below 30 or drift shows PF<1.0 after enough observations.",
            "- If primary remains Reject or Insufficient, advance the next Scalp candidate instead of weakening thresholds.",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def summarize_alternative_payload(payload: dict[str, Any]) -> dict[str, Any]:
    cfg = payload["config"]
    primary = payload["primary"]
    return {
        "strategy": cfg["strategy"],
        "pair": cfg["pair"],
        "interval": cfg["interval"],
        "roadmap_ev_pips": SCALP_POOL.get(cfg["strategy"], {}).get("roadmap_ev_pips"),
        "verdict": primary["verdict"],
        "verdict_reasons": primary["verdict_reasons"],
        "selected_engine": primary["selected_engine"],
        "selected": primary["selected"],
        "comparison": primary["comparison"],
    }


def run_alternative_scans(lookback: int, engine_timeout: int = DEFAULT_ENGINE_TIMEOUT_SECONDS) -> list[dict[str, Any]]:
    alternatives: list[dict[str, Any]] = []
    for strategy in ALTERNATIVE_SCAN_ORDER:
        cfg = SCALP_POOL[strategy]
        args = argparse.Namespace(
            pair=cfg["pair"],
            strategy=strategy,
            interval=cfg["interval"],
            lookback=lookback,
            output=None,
            abbreviated=True,
            dry_run=False,
            engine_timeout=engine_timeout,
        )
        try:
            alternatives.append(summarize_alternative_payload(build_payload(args)))
        except Exception as exc:
            alternatives.append(
                {
                    "strategy": strategy,
                    "pair": cfg["pair"],
                    "interval": cfg["interval"],
                    "roadmap_ev_pips": cfg.get("roadmap_ev_pips"),
                    "available": False,
                    "reason": str(exc),
                }
            )
    return alternatives


def roadmap_alternative_references(reason: str) -> list[dict[str, Any]]:
    alternatives: list[dict[str, Any]] = []
    midpoint = datetime.now(timezone.utc)
    for strategy in ALTERNATIVE_SCAN_ORDER:
        cfg = SCALP_POOL[strategy]
        ref = ROADMAP_ALT_REFERENCE[strategy]
        wins = ref["wins"]
        n = ref["n"]
        losses = max(0, n - wins)
        stats = stats_from_trades([], USDJPY_BEV_WR, midpoint)
        stats.update(
            {
                "n": n,
                "wins": wins,
                "losses": losses,
                "win_rate": ref["wr"],
                "ev_pips": ref["ev"],
                "profit_factor": None,
                "wilson_lo_95": round(wilson_lower(wins, n) * 100.0, 3),
                "wilson_hi_95": round(wilson_upper_at(wins / n, n) * 100.0, 3),
                "bonferroni_p": round(binomial_one_sided_p(wins, n, USDJPY_BEV_WR), 8),
            }
        )
        alternatives.append(
            {
                "strategy": strategy,
                "pair": cfg["pair"],
                "interval": cfg["interval"],
                "roadmap_ev_pips": cfg.get("roadmap_ev_pips"),
                "verdict": "ReferenceOnly",
                "verdict_reasons": [reason],
                "selected_engine": "roadmap-v2.1",
                "selected": {"strategy_stats": stats},
                "comparison": None,
            }
        )
    return alternatives


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair", default=PRIMARY_PAIR)
    parser.add_argument("--strategy", default=PRIMARY_STRATEGY)
    parser.add_argument("--interval", default=PRIMARY_INTERVAL)
    parser.add_argument("--lookback", type=int, default=PRIMARY_LOOKBACK)
    parser.add_argument("--output", default=None)
    parser.add_argument("--abbreviated", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--engine-timeout",
        type=int,
        default=DEFAULT_ENGINE_TIMEOUT_SECONDS,
        help="Seconds allowed for each BT engine. Use 0 to disable the per-engine timeout.",
    )
    return parser.parse_args(argv)


def abbreviated_output_paths(strategy: str, pair: str, interval: str, lookback: int) -> tuple[Path, Path]:
    stem = f"scalp-alt-{strategy}-{normalize_symbol(pair).lower()}-{interval}-{lookback}d-2026-05-03"
    md = ROOT / "knowledge-base" / "raw" / "bt-results" / f"{stem}.md"
    return md, md.with_suffix(".json")


def write_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def default_output_paths() -> tuple[Path, Path, Path]:
    raw_md = ROOT / "knowledge-base" / "raw" / "bt-results" / "scalp-mtf-cascade-180d-2026-05-03.md"
    raw_json = ROOT / "knowledge-base" / "raw" / "bt-results" / "scalp-mtf-cascade-180d-2026-05-03.json"
    prereg = ROOT / "knowledge-base" / "wiki" / "learning" / "scalp-re-enable-pre-registration-2026-05-03.md"
    return raw_md, raw_json, prereg


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    pair = normalize_symbol(args.pair)
    strategy = args.strategy
    interval = args.interval
    standard = run_engine_bounded(
        "standard run_scalp_backtest",
        run_standard_bt,
        pair,
        strategy,
        interval,
        args.lookback,
        timeout_seconds=args.engine_timeout,
    )
    vec = run_engine_bounded(
        "bt_vec_harness",
        run_vec_bt,
        pair,
        strategy,
        interval,
        args.lookback,
        timeout_seconds=args.engine_timeout,
    )
    selected_engine = "standard_bt"
    selected = standard
    comparison = None
    if vec.get("available"):
        comparison = compare_engines(standard["strategy_stats"], vec["strategy_stats"])
    if not standard.get("available") and vec.get("available"):
        selected_engine = "vec_harness"
        selected = vec
    elif not standard.get("available") and not vec.get("available"):
        selected_engine = "unavailable"
        selected = standard
    elif vec.get("available"):
        if comparison["oracle"] == "vec_harness":
            selected_engine = "vec_harness"
            selected = vec
    selected_trades: list[dict[str, Any]]
    if selected_engine == "vec_harness":
        selected_trades = [dict(t) for t in vec["summary"].get("trades_full", [])]
        for trade in selected_trades:
            trade["entry_type"] = strategy
            trade["symbol"] = pair
    else:
        selected_trades = []
        # Only strategy trades matter here and they are already baked into stats.
        # The raw filtered list is not persisted from the tracer to keep payload small.
    midpoint = parse_ts(selected["midpoint_utc"])
    assert midpoint is not None
    live_stats = stats_from_trades(live_comparable_subset(selected_trades), USDJPY_BEV_WR, midpoint) if selected_trades else stats_from_trades([], USDJPY_BEV_WR, midpoint)
    verdict, verdict_reasons = determine_verdict(selected["strategy_stats"])
    payload = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "wrapper_fingerprint": compute_wrapper_fingerprint(__file__),
        "config": {
            "pair": pair,
            "strategy": strategy,
            "interval": interval,
            "lookback_days": args.lookback,
            "engine_timeout_seconds": args.engine_timeout,
            "abbreviated": args.abbreviated,
            "dry_run": args.dry_run,
        },
        "bonferroni": {
            "alpha": BONFERRONI_ALPHA,
            "k": BONFERRONI_K,
            "alpha_div_k": BONFERRONI_ALPHA / BONFERRONI_K,
            "justification": BONFERRONI_JUSTIFICATION,
        },
        "thresholds": VERDICT_THRESHOLDS,
        "primary": {
            "standard": standard,
            "vec": vec,
            "comparison": comparison,
            "selected_engine": selected_engine,
            "selected": selected,
            "verdict": verdict,
            "verdict_reasons": verdict_reasons,
            "live_comparable_selected": live_stats,
        },
    }
    return payload


def dry_run_text() -> str:
    lines = [
        "LOCKED THRESHOLDS",
        json.dumps(
            {
                "thresholds": VERDICT_THRESHOLDS,
                "bonferroni": {
                    "alpha": BONFERRONI_ALPHA,
                    "k": BONFERRONI_K,
                    "alpha_div_k": BONFERRONI_ALPHA / BONFERRONI_K,
                    "justification": BONFERRONI_JUSTIFICATION,
                },
                "live_comparable_cutoff": LIVE_COMPARABLE_CUTOFF,
                "primary": {
                    "pair": PRIMARY_PAIR,
                    "strategy": PRIMARY_STRATEGY,
                    "interval": PRIMARY_INTERVAL,
                    "lookback_days": PRIMARY_LOOKBACK,
                },
            },
            indent=2,
            ensure_ascii=False,
        ),
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.dry_run:
        sys.stdout.write(dry_run_text())
        return 0

    payload = build_payload(args)
    raw_md_default, raw_json_default, prereg_default = default_output_paths()
    if args.abbreviated and not args.output:
        raw_md_path, raw_json_path = abbreviated_output_paths(
            args.strategy, args.pair, args.interval, args.lookback
        )
    else:
        raw_md_path = Path(args.output) if args.output else raw_md_default
        raw_json_path = raw_md_path.with_suffix(".json") if args.output else raw_json_default
    write_markdown(raw_md_path, build_markdown(payload, args.abbreviated))
    serialize_payload(payload, raw_json_path)
    if not args.abbreviated and normalize_symbol(args.pair) == PRIMARY_PAIR and args.strategy == PRIMARY_STRATEGY:
        alternatives = None
        if payload["primary"]["verdict"] != "Promote":
            if payload["primary"]["selected_engine"] == "unavailable":
                alternatives = roadmap_alternative_references(
                    "fresh primary BT engines unavailable; alternatives enumerated from roadmap-v2.1 reference table only"
                )
            else:
                alternatives = run_alternative_scans(args.lookback, args.engine_timeout)
        write_markdown(prereg_default, build_prereg_markdown(payload, alternatives))
    print(json.dumps(
        {
            "verdict": payload["primary"]["verdict"],
            "selected_engine": payload["primary"]["selected_engine"],
            "n": payload["primary"]["selected"]["strategy_stats"]["n"],
            "pf": payload["primary"]["selected"]["strategy_stats"]["profit_factor"],
            "wilson_lo_95": payload["primary"]["selected"]["strategy_stats"]["wilson_lo_95"],
            "output_md": str(raw_md_path),
            "output_json": str(raw_json_path),
            "prereg_md": str(prereg_default if not args.abbreviated else ""),
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
