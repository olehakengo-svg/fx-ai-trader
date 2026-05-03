#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import re
import signal
import sys
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.bt_common import compute_wrapper_fingerprint

RUN_DATE = "2026-05-03"
LOOKBACK_DAYS = 180
DEFAULT_ENGINE_TIMEOUT_SECONDS = 600
BONFERRONI_ALPHA = 0.05
BONFERRONI_K = 4
BONFERRONI_ALPHA_DIV_K = BONFERRONI_ALPHA / BONFERRONI_K
BONFERRONI_JUSTIFICATION = (
    "Decision pool fixed ex ante as 4 simple-structure scalp candidates: "
    "bb_squeeze_breakout, engulfing_bb, fib_reversal, sr_channel_reversal."
)
SCHEMA_VERSION = 1
PAIR_BEV_WR = {
    "USD_JPY": 0.344,
    "EUR_USD": 0.397,
}
BT_GATE_LIKELY_GATES = [
    "_compute_bt_htf_bias / HTF alignment",
    "signal confirmation count",
    "friction / spread-SL gate",
    "Phase0 / Phase A gate chain",
]
VERDICT_THRESHOLDS = {
    "promote": {
        "min_n": 30,
        "min_pf": 1.30,
        "min_wilson_lo_pp_over_bev": 5.0,
        "min_pf_is": 1.20,
        "min_pf_oos": 1.20,
        "max_dd_pct": 30.0,
        "bonf_alpha_div_k": BONFERRONI_ALPHA_DIV_K,
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
VERDICT_CATEGORIES = {
    "Promote": "N>=30, PF>=1.30, Wilson_lo > BEV_WR + 5pp, WF IS/OOS PF>=1.20, Bonferroni p<0.0125, max DD<=30%",
    "Shadow": "N>=30, PF>=1.10, Wilson_lo > BEV_WR, WF IS/OOS PF>=1.00, max DD<=30%",
    "Reject": "any configuration that fails Promote/Shadow and is not N-insufficient or BT-gate-blocked",
    "Insufficient": "N<30 with explicit gap-to-30 reporting",
    "BT_GATE_BLOCKED": "run_scalp_backtest returns N=0 for a registered QUALIFIED_TYPES candidate",
}
CANDIDATES = {
    "bb_squeeze_breakout": {
        "pair": "USD_JPY",
        "interval": "5m",
        "roadmap_ev_pips": 1.030,
        "structure_complexity": "BB + squeeze (1 indicator + 1 condition)",
        "slug": "bb_squeeze",
    },
    "engulfing_bb": {
        "pair": "USD_JPY",
        "interval": "5m",
        "roadmap_ev_pips": 0.677,
        "structure_complexity": "engulfing candle + BB extreme (2 conditions)",
        "slug": "engulfing",
    },
    "fib_reversal": {
        "pair": "EUR_USD",
        "interval": "1m",
        "roadmap_ev_pips": 0.426,
        "structure_complexity": "Fib retracement (1 level set)",
        "slug": "fib",
    },
    "sr_channel_reversal": {
        "pair": "EUR_USD",
        "interval": "5m",
        "roadmap_ev_pips": 0.231,
        "structure_complexity": "SR / channel bounce (1 level set)",
        "slug": "sr",
    },
}


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


def format_float(value: Any, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    if value == "inf":
        return "inf"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def pf_to_float(value: Any) -> float | None:
    if value in (None, "n/a"):
        return None
    if value == "inf":
        return math.inf
    return float(value)


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


def extract_trade_pnl(trade: dict[str, Any]) -> float:
    value = trade.get("pnl_pips")
    if value is not None:
        return float(value)
    outcome = str(trade.get("outcome", "") or "").upper()
    exit_friction_m = float(trade.get("exit_friction_m", 0.0) or 0.0)
    if outcome == "WIN":
        return float(trade.get("tp_m", 0.0) or 0.0) - exit_friction_m
    if outcome == "LOSS":
        return -(float(trade.get("actual_sl_m", trade.get("sl_m", 0.0)) or 0.0) + exit_friction_m)
    if outcome == "BREAKEVEN":
        return 0.0
    entry = float(trade.get("entry_price", trade.get("ep", trade.get("entry_px", 0.0))) or 0.0)
    exit_px = float(trade.get("exit_price", 0.0) or 0.0)
    sig = str(trade.get("sig", trade.get("signal", "")) or "").upper()
    if entry and exit_px and sig in {"BUY", "SELL"}:
        pip_mult = 100 if "JPY" in normalize_symbol(str(trade.get("symbol", ""))) else 10000
        raw = (exit_px - entry) * pip_mult if sig == "BUY" else (entry - exit_px) * pip_mult
        return float(raw)
    return 0.0


def extract_strategy_trades(
    summary: dict[str, Any],
    captured_trades: list[dict[str, Any]],
    strategy: str,
) -> list[dict[str, Any]]:
    candidates = captured_trades
    if not candidates and isinstance(summary.get("trade_log"), list):
        candidates = [dict(t) for t in summary["trade_log"]]
    return [
        dict(t)
        for t in candidates
        if (t.get("entry_type") or t.get("type")) == strategy
    ]


def trade_outcome(trade: dict[str, Any], pnl: float) -> str:
    outcome = str(trade.get("outcome", "") or "").upper()
    if outcome in {"WIN", "LOSS", "BREAKEVEN"}:
        return outcome
    if pnl > 0:
        return "WIN"
    if pnl < 0:
        return "LOSS"
    return "BREAKEVEN"


def profit_factor(gross_profit: float, gross_loss_abs: float) -> float | None:
    if gross_loss_abs <= 0:
        return None if gross_profit <= 0 else math.inf
    return gross_profit / gross_loss_abs


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


def compute_midpoint(trades: list[dict[str, Any]]) -> datetime:
    ordered = sort_trades(trades)
    if not ordered:
        return datetime.now(timezone.utc)
    times = [trade_time(t) for t in ordered]
    known = [t for t in times if t is not None]
    if not known:
        return datetime.now(timezone.utc)
    mid_idx = len(known) // 2
    return known[mid_idx]


def load_quant_helpers():
    sys.path.insert(0, str(ROOT))
    from modules.stats_utils import kelly_criterion
    from research.edge_discovery.significance import binomial_one_sided_p
    from tools.cell_edge_audit import wilson_lower
    from tools.cell_negative_edge_audit import wilson_upper_at

    return kelly_criterion, binomial_one_sided_p, wilson_lower, wilson_upper_at


def stats_from_trades(
    trades: list[dict[str, Any]],
    bev_wr: float,
    midpoint: datetime | None = None,
    *,
    include_wf: bool = True,
) -> dict[str, Any]:
    kelly_criterion, binomial_one_sided_p, wilson_lower, wilson_upper_at = load_quant_helpers()
    ordered = sort_trades(trades)
    midpoint = midpoint or compute_midpoint(ordered)
    pnls = [extract_trade_pnl(t) for t in ordered]
    n = len(ordered)
    outcomes = [trade_outcome(t, p) for t, p in zip(ordered, pnls)]
    wins = sum(1 for outcome in outcomes if outcome == "WIN")
    losses = sum(1 for outcome in outcomes if outcome == "LOSS")
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
    dd_pips, dd_pct = max_drawdown(pnls)
    p_value = binomial_one_sided_p(wins, n, bev_wr) if n else 1.0
    payload = {
        "n": n,
        "wins": wins,
        "losses": losses,
        "win_rate": round(wr * 100.0, 3),
        "ev_pips": round(ev, 3),
        "profit_factor": "inf" if pf == math.inf else (round(pf, 3) if pf is not None else None),
        "gross_profit": round(gross_profit, 3),
        "gross_loss_abs": round(gross_loss_abs, 3),
        "wilson_lo_95": round(wilson_lower(wins, n) * 100.0, 3) if n else 0.0,
        "wilson_hi_95": round(wilson_upper_at(wr, n) * 100.0, 3) if n else 0.0,
        "bev_wr": round(bev_wr * 100.0, 3),
        "bonferroni_p": round(min(1.0, p_value * BONFERRONI_K), 8),
        "bonferroni_alpha_div_k": round(BONFERRONI_ALPHA_DIV_K, 8),
        "kelly_full": round(float(kelly.get("full_kelly", 0.0)), 6),
        "kelly_half": round(float(kelly.get("half_kelly", 0.0)), 6),
        "max_drawdown_pips": dd_pips,
        "max_drawdown_pct": dd_pct,
    }
    if include_wf:
        is_trades = [t for t in ordered if (trade_time(t) or midpoint) < midpoint]
        oos_trades = [t for t in ordered if (trade_time(t) or midpoint) >= midpoint]
        payload["walk_forward"] = {
            "split": "50/50 chronological split",
            "midpoint_utc": midpoint.isoformat(),
            "is": stats_from_trades(is_trades, bev_wr, midpoint, include_wf=False),
            "oos": stats_from_trades(oos_trades, bev_wr, midpoint, include_wf=False),
        }
    return payload


def metadata_for_candidate(strategy: str) -> dict[str, Any]:
    if strategy not in CANDIDATES:
        raise KeyError(f"unknown candidate: {strategy}")
    cfg = dict(CANDIDATES[strategy])
    cfg["strategy"] = strategy
    cfg["pair"] = normalize_symbol(cfg["pair"])
    cfg["bev_wr"] = PAIR_BEV_WR[cfg["pair"]]
    return cfg


def overfit_flag(stats: dict[str, Any]) -> dict[str, Any]:
    wf = stats.get("walk_forward", {})
    is_pf = pf_to_float(wf.get("is", {}).get("profit_factor"))
    oos_pf = pf_to_float(wf.get("oos", {}).get("profit_factor"))
    flagged = False
    ratio = None
    if is_pf is not None and oos_pf is not None and math.isfinite(is_pf) and is_pf > 0:
        ratio = oos_pf / is_pf
        flagged = ratio < 0.85
    return {
        "flagged": flagged,
        "oos_to_is_ratio": round(ratio, 6) if ratio is not None else None,
        "threshold": 0.85,
    }


def determine_verdict(stats: dict[str, Any], gate_blocked: bool) -> tuple[str, list[str], list[str], dict[str, Any]]:
    reasons: list[str] = []
    flags: list[str] = []
    if gate_blocked:
        reasons.append("run_scalp_backtest returned N=0 for a registered QUALIFIED_TYPES candidate")
        return "BT_GATE_BLOCKED", reasons, flags, overfit_flag(stats)
    if stats["n"] < VERDICT_THRESHOLDS["promote"]["min_n"]:
        reasons.append(f"N<{VERDICT_THRESHOLDS['promote']['min_n']}")
        reasons.append(f"gap_to_30={VERDICT_THRESHOLDS['promote']['min_n'] - stats['n']}")
        return "Insufficient", reasons, flags, overfit_flag(stats)

    wf = stats["walk_forward"]
    is_pf = pf_to_float(wf["is"]["profit_factor"])
    oos_pf = pf_to_float(wf["oos"]["profit_factor"])
    pf = pf_to_float(stats["profit_factor"])
    dd_pct = stats["max_drawdown_pct"]
    wilson_margin_pp = stats["wilson_lo_95"] - stats["bev_wr"]
    promote = (
        pf is not None
        and pf >= VERDICT_THRESHOLDS["promote"]["min_pf"]
        and wilson_margin_pp > VERDICT_THRESHOLDS["promote"]["min_wilson_lo_pp_over_bev"]
        and is_pf is not None and is_pf >= VERDICT_THRESHOLDS["promote"]["min_pf_is"]
        and oos_pf is not None and oos_pf >= VERDICT_THRESHOLDS["promote"]["min_pf_oos"]
        and stats["bonferroni_p"] < VERDICT_THRESHOLDS["promote"]["bonf_alpha_div_k"]
        and dd_pct is not None and dd_pct <= VERDICT_THRESHOLDS["promote"]["max_dd_pct"]
    )
    shadow = (
        pf is not None
        and pf >= VERDICT_THRESHOLDS["shadow"]["min_pf"]
        and wilson_margin_pp > VERDICT_THRESHOLDS["shadow"]["min_wilson_lo_pp_over_bev"] - 1e-9
        and is_pf is not None and is_pf >= VERDICT_THRESHOLDS["shadow"]["min_pf_is"]
        and oos_pf is not None and oos_pf >= VERDICT_THRESHOLDS["shadow"]["min_pf_oos"]
        and dd_pct is not None and dd_pct <= VERDICT_THRESHOLDS["shadow"]["max_dd_pct"]
    )
    verdict = "Promote" if promote else "Shadow" if shadow else "Reject"
    if verdict == "Reject":
        if pf is None or pf < VERDICT_THRESHOLDS["shadow"]["min_pf"]:
            reasons.append(f"PF<{VERDICT_THRESHOLDS['shadow']['min_pf']}")
        if wilson_margin_pp <= 0:
            reasons.append("Wilson_lo<=BEV_WR")
        if is_pf is None or is_pf < VERDICT_THRESHOLDS["shadow"]["min_pf_is"] or oos_pf is None or oos_pf < VERDICT_THRESHOLDS["shadow"]["min_pf_oos"]:
            reasons.append("WF shadow threshold failed")
        if dd_pct is None or dd_pct > VERDICT_THRESHOLDS["shadow"]["max_dd_pct"]:
            reasons.append("max DD > 30% or undefined")
        if stats["bonferroni_p"] >= VERDICT_THRESHOLDS["promote"]["bonf_alpha_div_k"]:
            reasons.append("Bonferroni threshold failed for Promote")

    overfit = overfit_flag(stats)
    if overfit["flagged"]:
        flags.append("OVERFIT_SUSPECTED")
        reasons.append("OOS PF degraded by more than 15% from IS PF")
        if verdict == "Promote":
            verdict = "Shadow"
        elif verdict == "Shadow":
            verdict = "Reject"
    return verdict, reasons, flags, overfit


def load_app_runtime():
    os.environ.setdefault("BT_MODE", "1")
    os.environ.setdefault("NO_AUTOSTART", "1")
    sys.path.insert(0, str(ROOT))
    import modules.demo_trader as demo_trader_module

    class _StubDemoTrader:
        def __init__(self, db=None):
            self.db = db

    demo_trader_module.DemoTrader = _StubDemoTrader
    import app
    from modules.bt_vec_harness import _load_local_cache

    app.get_master_bias = lambda symbol: {"direction": "neutral", "label": "offline", "score": 0}

    _CAP_RENAME = {"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}

    def _local_only_fetch_ohlcv(symbol="USDJPY=X", period="5d", interval="1m"):
        m = re.match(r"(\d+)d", str(period or ""))
        days = int(m.group(1)) if m else 7
        df = _load_local_cache(symbol, interval, days)
        if df is None or len(df) < 50:
            raise RuntimeError(
                f"local cache miss for fetch_ohlcv({symbol}, period={period}, interval={interval})"
            )
        return df.rename(columns=_CAP_RENAME)

    app.fetch_ohlcv = _local_only_fetch_ohlcv
    return app, _load_local_cache


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


def load_local_bt_frame(pair: str, interval: str, lookback_days: int):
    app, _load_local_cache = load_app_runtime()
    df = _load_local_cache(yahoo_symbol(pair), interval, lookback_days)
    if df is None or len(df) < 100:
        raise RuntimeError(
            f"Local parquet cache missing or too small for pair={pair} interval={interval} lookback_days={lookback_days}"
        )
    df = df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"})
    df = app.add_indicators(df.copy()).dropna()
    if len(df) < 100:
        raise RuntimeError(f"Indicator-enriched local cache too small for pair={pair} interval={interval}")
    return app, df


def run_standard_bt(strategy: str, pair: str, interval: str, lookback_days: int) -> dict[str, Any]:
    app, df = load_local_bt_frame(pair, interval, lookback_days)
    with capture_run_scalp_trades() as cap:
        result = app.run_scalp_backtest(
            symbol=yahoo_symbol(pair),
            lookback_days=lookback_days,
            interval=interval,
            _df_override=df,
        )
    raw_trades = cap.get("trades") or []
    if not raw_trades and isinstance(result.get("trade_log"), list):
        raw_trades = [dict(t) for t in result["trade_log"]]
    for trade in raw_trades:
        trade.setdefault("symbol", pair)
    filtered = extract_strategy_trades(result, raw_trades, strategy)
    midpoint = compute_midpoint(filtered)
    stats = stats_from_trades(filtered, PAIR_BEV_WR[pair], midpoint)
    gate_blocked = len(filtered) == 0
    return {
        "summary": result,
        "bars_fetched": len(df),
        "window_start_utc": df.index.min().isoformat(),
        "window_end_utc": df.index.max().isoformat(),
        "midpoint_utc": midpoint.isoformat(),
        "raw_trade_count_all": len(raw_trades),
        "raw_trade_count_strategy": len(filtered),
        "strategy_trades": filtered,
        "strategy_stats": stats,
        "gate_blocked": gate_blocked,
    }


class EngineTimeoutError(RuntimeError):
    pass


@contextmanager
def enforce_timeout(seconds: int):
    if seconds <= 0:
        yield
        return

    def _handler(signum, frame):
        raise EngineTimeoutError(f"run_scalp_backtest exceeded {seconds}s timeout")

    previous_handler = signal.signal(signal.SIGALRM, _handler)
    signal.setitimer(signal.ITIMER_REAL, float(seconds))
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.0)
        signal.signal(signal.SIGALRM, previous_handler)


def default_candidate_output_path(strategy: str) -> Path:
    return ROOT / "knowledge-base" / "raw" / "bt-results" / f"scalp-alt-{CANDIDATES[strategy]['slug']}-{RUN_DATE}.json"


def aggregate_json_path() -> Path:
    return ROOT / "knowledge-base" / "raw" / "bt-results" / f"scalp-alt-180d-{RUN_DATE}.json"


def aggregate_md_path() -> Path:
    return ROOT / "knowledge-base" / "raw" / "bt-results" / f"scalp-alt-180d-{RUN_DATE}.md"


def prereg_md_path() -> Path:
    return ROOT / "knowledge-base" / "wiki" / "learning" / f"scalp-alt-pre-registration-{RUN_DATE}.md"


def serialize_payload(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def candidate_summary_markdown(payload: dict[str, Any]) -> str:
    stats = payload["stats"]
    overfit = payload["overfit"]
    flags = ", ".join(payload["flags"]) if payload["flags"] else "none"
    lines = [
        f"# Scalp alt candidate — {payload['candidate']['strategy']} — {RUN_DATE}",
        "",
        f"Strategy: `{payload['candidate']['strategy']}`",
        f"Pair / Interval: `{payload['candidate']['pair']}` / `{payload['candidate']['interval']}`",
        f"Verdict: `{payload['verdict']}`",
        f"Flags: {flags}",
        "",
        "## Quant",
        "",
        f"- N / Wins / Losses: {stats['n']} / {stats['wins']} / {stats['losses']}",
        f"- WR: {stats['win_rate']:.3f}%",
        f"- EV: {stats['ev_pips']:.3f} pip/trade",
        f"- PF: {format_float(stats['profit_factor'])}",
        f"- Wilson 95%: [{stats['wilson_lo_95']:.3f}%, {stats['wilson_hi_95']:.3f}%]",
        f"- BEV_WR: {stats['bev_wr']:.3f}%",
        f"- Bonferroni: K={BONFERRONI_K}, p={stats['bonferroni_p']}, alpha/K={stats['bonferroni_alpha_div_k']}",
        f"- Max DD: {stats['max_drawdown_pips']:.3f} pip / {format_float(stats['max_drawdown_pct'])}%",
        f"- WF IS PF / OOS PF: {format_float(stats['walk_forward']['is']['profit_factor'])} / {format_float(stats['walk_forward']['oos']['profit_factor'])}",
        f"- OOS/IS PF ratio: {format_float(overfit['oos_to_is_ratio'], 6)}",
        "",
        "## Notes",
        "",
    ]
    if payload["verdict"] == "BT_GATE_BLOCKED":
        lines.append(f"- Likely gates: {', '.join(payload['gate_blocked_likely_gates'])}")
    else:
        lines.append(f"- Reasons: {', '.join(payload['reasons']) if payload['reasons'] else 'all conditions passed'}")
    return "\n".join(lines) + "\n"


def build_candidate_payload(strategy: str, engine_timeout: int) -> dict[str, Any]:
    cfg = metadata_for_candidate(strategy)
    with enforce_timeout(engine_timeout):
        result = run_standard_bt(strategy, cfg["pair"], cfg["interval"], LOOKBACK_DAYS)
    verdict, reasons, flags, overfit = determine_verdict(result["strategy_stats"], result["gate_blocked"])
    payload = {
        "schema_version": SCHEMA_VERSION,
        "run_at": datetime.now(timezone.utc).isoformat(),
        "wrapper_fingerprint": compute_wrapper_fingerprint(__file__),
        "candidate": cfg,
        "bonferroni": {
            "alpha": BONFERRONI_ALPHA,
            "k": BONFERRONI_K,
            "alpha_div_k": BONFERRONI_ALPHA_DIV_K,
            "justification": BONFERRONI_JUSTIFICATION,
        },
        "thresholds": VERDICT_THRESHOLDS,
        "engine_timeout_seconds": engine_timeout,
        "stats": result["strategy_stats"],
        "verdict": verdict,
        "reasons": reasons,
        "flags": flags,
        "overfit": overfit,
        "engine": {
            "name": "run_scalp_backtest",
            "bars_fetched": result["bars_fetched"],
            "window_start_utc": result["window_start_utc"],
            "window_end_utc": result["window_end_utc"],
            "midpoint_utc": result["midpoint_utc"],
            "raw_trade_count_all": result["raw_trade_count_all"],
            "raw_trade_count_strategy": result["raw_trade_count_strategy"],
            "summary": result["summary"],
        },
        "strategy_trades": result["strategy_trades"],
        "gate_blocked_likely_gates": BT_GATE_LIKELY_GATES if result["gate_blocked"] else [],
    }
    return payload


def summarize_candidate(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "strategy": payload["candidate"]["strategy"],
        "pair": payload["candidate"]["pair"],
        "interval": payload["candidate"]["interval"],
        "roadmap_ev_pips": payload["candidate"]["roadmap_ev_pips"],
        "structure_complexity": payload["candidate"]["structure_complexity"],
        "verdict": payload["verdict"],
        "reasons": payload["reasons"],
        "flags": payload["flags"],
        "overfit": payload["overfit"],
        "stats": payload["stats"],
        "gate_blocked_likely_gates": payload["gate_blocked_likely_gates"],
        "json_path": str(default_candidate_output_path(payload["candidate"]["strategy"])),
    }


def candidate_priority(verdict: str) -> int:
    order = {
        "Promote": 0,
        "Shadow": 1,
        "Reject": 2,
        "Insufficient": 3,
        "BT_GATE_BLOCKED": 4,
    }
    return order.get(verdict, 9)


def apply_promote_cap(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    promote_candidates = [c for c in candidates if c["verdict"] == "Promote"]
    if len(promote_candidates) <= 1:
        return candidates

    keep_strategy = max(
        promote_candidates,
        key=lambda c: (c["stats"]["ev_pips"], c["stats"]["profit_factor"] == "inf", c["stats"]["n"]),
    )["strategy"]
    capped: list[dict[str, Any]] = []
    for candidate in candidates:
        candidate = dict(candidate)
        if candidate["verdict"] == "Promote" and candidate["strategy"] != keep_strategy:
            candidate["verdict"] = "Shadow"
            candidate["flags"] = list(candidate["flags"]) + ["PROMOTE_CAP_DOWNGRADED"]
            candidate["reasons"] = list(candidate["reasons"]) + [
                "Promote cap applied: only the top EV candidate may remain Promote"
            ]
        capped.append(candidate)
    return capped


def recommended_next_task(candidates: list[dict[str, Any]]) -> str:
    if any(c["verdict"] in {"Promote", "Shadow"} for c in candidates):
        return "A3-simple — register the Promote candidate to OANDA bridge with monitoring"
    return "A2-alt2 — pre-register the next simple candidate from the broader Scalp pool"


def build_aggregate_payload(candidate_payloads: list[dict[str, Any]]) -> dict[str, Any]:
    summaries = [summarize_candidate(p) for p in candidate_payloads]
    summaries = apply_promote_cap(summaries)
    sorted_candidates = sorted(summaries, key=lambda c: (candidate_priority(c["verdict"]), -c["stats"]["ev_pips"]))
    promote_candidates = [c["strategy"] for c in sorted_candidates if c["verdict"] == "Promote"]
    return {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "bonferroni": {
            "alpha": BONFERRONI_ALPHA,
            "k": BONFERRONI_K,
            "alpha_div_k": BONFERRONI_ALPHA_DIV_K,
            "justification": BONFERRONI_JUSTIFICATION,
        },
        "thresholds": VERDICT_THRESHOLDS,
        "candidates": sorted_candidates,
        "summary": {
            "promote_candidates": promote_candidates,
            "promote_count": len(promote_candidates),
            "top_ranked_strategy": sorted_candidates[0]["strategy"] if sorted_candidates else None,
            "next_task": recommended_next_task(sorted_candidates),
            "simple_first_lineage": "complex-gate-edge-destruction-pattern-2026-05-03",
        },
    }


def aggregate_quant_table(candidate: dict[str, Any]) -> list[str]:
    stats = candidate["stats"]
    return [
        f"| `{candidate['strategy']}` | `{candidate['pair']}` | `{candidate['interval']}` | {candidate['verdict']} | {','.join(candidate['flags']) or 'none'} | {stats['n']} | {stats['wins']} / {stats['losses']} | {stats['win_rate']:.3f}% | {stats['ev_pips']:.3f} | {format_float(stats['profit_factor'])} | [{stats['wilson_lo_95']:.3f}%, {stats['wilson_hi_95']:.3f}%] | {stats['max_drawdown_pips']:.3f} / {format_float(stats['max_drawdown_pct'])}% | {format_float(stats['walk_forward']['is']['profit_factor'])} / {format_float(stats['walk_forward']['oos']['profit_factor'])} | {stats['walk_forward']['is']['win_rate']:.3f}% / {stats['walk_forward']['oos']['win_rate']:.3f}% | {stats['bonferroni_p']} | {stats['kelly_half']:.6f} |"
    ]


def build_aggregate_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# Scalp alt aggregate BT results — {RUN_DATE}",
        "",
        f"- Bonferroni: K={payload['bonferroni']['k']}, alpha/K={payload['bonferroni']['alpha_div_k']:.5f}",
        f"- Promote count: {payload['summary']['promote_count']}",
        f"- Next task: {payload['summary']['next_task']}",
        "",
        "| Strategy | Pair | TF | Verdict | Flags | N | W/L | WR | EV | PF | Wilson 95% | Max DD pip/% | WF PF IS/OOS | WF WR IS/OOS | Bonf p | Half-Kelly |",
        "|---|---|---|---|---|---:|---|---:|---:|---:|---|---|---|---|---:|---:|",
    ]
    for candidate in payload["candidates"]:
        lines.extend(aggregate_quant_table(candidate))
    return "\n".join(lines) + "\n"


def build_prereg_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# Scalp alt pre-registration — {RUN_DATE}",
        "",
        "**Rule**: `R1 Slow & Strict`",
        "**Decision lineage**: `complex-gate-edge-destruction-pattern-2026-05-03` simple-first principle",
        "",
        "## LOCKED thresholds",
        "",
        f"- Promote: N>={VERDICT_THRESHOLDS['promote']['min_n']}, PF>={VERDICT_THRESHOLDS['promote']['min_pf']}, Wilson_lo > BEV_WR + 5pp, WF PF_IS>={VERDICT_THRESHOLDS['promote']['min_pf_is']} and PF_OOS>={VERDICT_THRESHOLDS['promote']['min_pf_oos']}, Bonferroni p<{VERDICT_THRESHOLDS['promote']['bonf_alpha_div_k']:.5f}, max DD<=30%.",
        f"- Shadow: N>={VERDICT_THRESHOLDS['shadow']['min_n']}, PF>={VERDICT_THRESHOLDS['shadow']['min_pf']}, Wilson_lo > BEV_WR, WF PF_IS>={VERDICT_THRESHOLDS['shadow']['min_pf_is']} and PF_OOS>={VERDICT_THRESHOLDS['shadow']['min_pf_oos']}, max DD<=30%.",
        f"- Reject: any other configuration. Insufficient: N<{VERDICT_THRESHOLDS['promote']['min_n']}.",
        "- OVERFIT_SUSPECTED: OOS PF < IS PF x 0.85 triggers a one-tier downgrade.",
        "",
        "## Bonferroni K=4 justification",
        "",
        f"- {payload['bonferroni']['justification']}",
        f"- Alpha/K = {payload['bonferroni']['alpha_div_k']:.5f}.",
        "",
        "## Summary table",
        "",
        "| Strategy | Pair | TF | Roadmap EV | Complexity | Verdict | Flags | N | PF | Bonf p |",
        "|---|---|---|---:|---|---|---|---:|---:|---:|",
    ]
    for candidate in payload["candidates"]:
        lines.append(
            f"| `{candidate['strategy']}` | `{candidate['pair']}` | `{candidate['interval']}` | {candidate['roadmap_ev_pips']:.3f} | {candidate['structure_complexity']} | {candidate['verdict']} | {','.join(candidate['flags']) or 'none'} | {candidate['stats']['n']} | {format_float(candidate['stats']['profit_factor'])} | {candidate['stats']['bonferroni_p']} |"
        )
    lines.extend(
        [
            "",
            "## Per-candidate quant table",
            "",
            "| Strategy | Verdict | Flags | N | Wins/Losses | WR | EV pip/trade | PF | Wilson 95% CI | Max DD pip | Max DD % | WF PF IS/OOS | WF WR IS/OOS | Bonferroni one-sided p | half-Kelly |",
            "|---|---|---|---:|---|---:|---:|---:|---|---:|---:|---|---|---:|---:|",
        ]
    )
    for candidate in payload["candidates"]:
        stats = candidate["stats"]
        lines.append(
            f"| `{candidate['strategy']}` | {candidate['verdict']} | {','.join(candidate['flags']) or 'none'} | {stats['n']} | {stats['wins']} / {stats['losses']} | {stats['win_rate']:.3f}% | {stats['ev_pips']:.3f} | {format_float(stats['profit_factor'])} | [{stats['wilson_lo_95']:.3f}%, {stats['wilson_hi_95']:.3f}%] | {stats['max_drawdown_pips']:.3f} | {format_float(stats['max_drawdown_pct'])} | {format_float(stats['walk_forward']['is']['profit_factor'])} / {format_float(stats['walk_forward']['oos']['profit_factor'])} | {stats['walk_forward']['is']['win_rate']:.3f}% / {stats['walk_forward']['oos']['win_rate']:.3f}% | {stats['bonferroni_p']} | {stats['kelly_half']:.6f} |"
        )
        lines.append(f"Verdict note: {', '.join(candidate['reasons']) if candidate['reasons'] else 'all pre-registered conditions passed'}")
        if candidate["verdict"] == "BT_GATE_BLOCKED":
            lines.append(f"Likely gate chain failure: {', '.join(candidate['gate_blocked_likely_gates'])}")
    lines.extend(
        [
            "",
            "## Promote cap",
            "",
            f"- Promote candidates identified: {payload['summary']['promote_count']} (at most one allowed by decision policy).",
            f"- Top ranked candidate: `{payload['summary']['top_ranked_strategy']}`.",
            "",
            "## Recommendation",
            "",
            f"- Next recommended task: {payload['summary']['next_task']}",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def dry_run_text() -> str:
    payload = {
        "candidates": {
            strategy: {
                "pair": cfg["pair"],
                "interval": cfg["interval"],
                "roadmap_ev_pips": cfg["roadmap_ev_pips"],
                "structure_complexity": cfg["structure_complexity"],
            }
            for strategy, cfg in CANDIDATES.items()
        },
        "thresholds": VERDICT_THRESHOLDS,
        "verdict_categories": VERDICT_CATEGORIES,
        "bonferroni": {
            "alpha": BONFERRONI_ALPHA,
            "k": BONFERRONI_K,
            "alpha_div_k": BONFERRONI_ALPHA_DIV_K,
            "justification": BONFERRONI_JUSTIFICATION,
        },
        "bev_wr": {pair: round(value * 100.0, 3) for pair, value in PAIR_BEV_WR.items()},
        "lookback_days": LOOKBACK_DAYS,
    }
    return "LOCKED THRESHOLDS\n" + json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--aggregate", action="store_true")
    parser.add_argument("--candidate", choices=sorted(CANDIDATES))
    parser.add_argument("--output")
    parser.add_argument("--engine-timeout", type=int, default=DEFAULT_ENGINE_TIMEOUT_SECONDS)
    return parser.parse_args(argv)


def load_candidate_payloads() -> list[dict[str, Any]]:
    payloads = []
    current_fingerprint = compute_wrapper_fingerprint(__file__)
    for strategy in CANDIDATES:
        path = default_candidate_output_path(strategy)
        if not path.exists():
            raise FileNotFoundError(f"missing candidate JSON: {path}")
        payload = json.loads(path.read_text())
        produced_fingerprint = payload.get("wrapper_fingerprint")
        if produced_fingerprint != current_fingerprint:
            raise ValueError(
                "wrapper_fingerprint mismatch: "
                f"{path.name} was produced by wrapper {produced_fingerprint or 'missing'}, "
                f"current wrapper is {current_fingerprint}"
            )
        validate_candidate_payload(payload, strategy)
        payloads.append(payload)
    return payloads


def validate_candidate_payload(payload: dict[str, Any], expected_strategy: str) -> None:
    strategy = payload.get("candidate", {}).get("strategy")
    if strategy != expected_strategy:
        raise ValueError(f"candidate JSON strategy mismatch: expected {expected_strategy}, got {strategy}")

    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"stale candidate JSON for {expected_strategy}: schema_version must be {SCHEMA_VERSION}; rerun --candidate"
        )

    stats = payload.get("stats", {})
    engine = payload.get("engine", {})
    raw_count = engine.get("raw_trade_count_strategy")
    if raw_count is not None and stats.get("n") != raw_count:
        raise ValueError(
            f"candidate JSON trade-count mismatch for {expected_strategy}: stats.n={stats.get('n')} raw={raw_count}"
        )

    trades = payload.get("strategy_trades")
    if raw_count and not isinstance(trades, list):
        raise ValueError(f"stale candidate JSON for {expected_strategy}: missing strategy_trades; rerun --candidate")

    breakdown = engine.get("summary", {}).get("entry_breakdown", {}).get(expected_strategy)
    if breakdown:
        if breakdown.get("total") != stats.get("n") or breakdown.get("wins") != stats.get("wins"):
            raise ValueError(
                f"stale candidate JSON for {expected_strategy}: stats disagree with run_scalp_backtest entry_breakdown"
            )


def run_candidate(strategy: str, output: str | None, engine_timeout: int) -> int:
    payload = build_candidate_payload(strategy, engine_timeout)
    json_path = Path(output) if output else default_candidate_output_path(strategy)
    md_path = json_path.with_suffix(".md")
    serialize_payload(payload, json_path)
    write_text(md_path, candidate_summary_markdown(payload))
    print(json.dumps(
        {
            "strategy": strategy,
            "verdict": payload["verdict"],
            "output_json": str(json_path),
            "output_md": str(md_path),
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


def run_aggregate(output: str | None) -> int:
    try:
        candidate_payloads = load_candidate_payloads()
    except ValueError as exc:
        sys.stderr.write(str(exc) + "\n")
        return 2
    payload = build_aggregate_payload(candidate_payloads)
    raw_json = aggregate_json_path()
    raw_md = aggregate_md_path()
    prereg = Path(output) if output else prereg_md_path()
    serialize_payload(payload, raw_json)
    write_text(raw_md, build_aggregate_markdown(payload))
    write_text(prereg, build_prereg_markdown(payload))
    print(json.dumps(
        {
            "aggregate_json": str(raw_json),
            "aggregate_md": str(raw_md),
            "prereg_md": str(prereg),
            "next_task": payload["summary"]["next_task"],
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.dry_run:
        sys.stdout.write(dry_run_text())
        return 0
    if args.aggregate:
        return run_aggregate(args.output)
    if not args.candidate:
        raise SystemExit("--candidate or --aggregate or --dry-run is required")
    return run_candidate(args.candidate, args.output, args.engine_timeout)


if __name__ == "__main__":
    raise SystemExit(main())
