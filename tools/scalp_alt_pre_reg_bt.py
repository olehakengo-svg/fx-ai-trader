#!/usr/bin/env python3
"""A2-alt simple-structure Scalp pre-registration BT wrapper.

LOCK discipline:
  - Candidate family K=4 is fixed ex ante.
  - Thresholds are module-level constants and must not be changed after BT.
  - Primary engine is app.run_scalp_backtest; vec_harness is intentionally
    out of scope for this simple-first candidate family.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import signal
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ─────────────────────────────────────────────────────────────────────────
# LOCKED constants: encoded before BT observation.
# ─────────────────────────────────────────────────────────────────────────

RUN_ID = "scalp-alt-180d-2026-05-03"
LOCK_DATE = "2026-05-03"
LOOKBACK_DAYS = 180
BONFERRONI_K = 4
ALPHA = 0.05
ALPHA_BONFERRONI = ALPHA / BONFERRONI_K
MIN_N = 30
PROMOTE_PF_MIN = 1.30
SHADOW_PF_MIN = 1.10
PROMOTE_WILSON_MARGIN = 0.05
PROMOTE_WF_PF_MIN = 1.20
SHADOW_WF_PF_MIN = 1.00
MAX_DD_PCT_LIMIT = 0.30
OOS_STABILITY_RATIO_MIN = 0.85
INITIAL_CAPITAL_PIP_SURROGATE = 100.0

BEV_WR_BY_PAIR = {
    "USD_JPY": 0.344,
    "EUR_USD": 0.397,
}

PROMOTE_TIEBREAK_FIELDS = (
    "bonferroni_p",
    "-pf",
    "-ev_pip_per_trade",
    "-n",
)

DEFAULT_SINGLE_OUTPUTS = {
    "bb_squeeze_breakout": ROOT / "knowledge-base/raw/bt-results/scalp-alt-bb_squeeze-2026-05-03.json",
    "engulfing_bb": ROOT / "knowledge-base/raw/bt-results/scalp-alt-engulfing-2026-05-03.json",
    "fib_reversal": ROOT / "knowledge-base/raw/bt-results/scalp-alt-fib-2026-05-03.json",
    "sr_channel_reversal": ROOT / "knowledge-base/raw/bt-results/scalp-alt-sr-2026-05-03.json",
}

RAW_AGG_JSON = ROOT / "knowledge-base/raw/bt-results/scalp-alt-180d-2026-05-03.json"
RAW_AGG_MD = ROOT / "knowledge-base/raw/bt-results/scalp-alt-180d-2026-05-03.md"
DEFAULT_DOC = ROOT / "knowledge-base/wiki/learning/scalp-alt-pre-registration-2026-05-03.md"


@dataclass(frozen=True)
class Candidate:
    ordinal: int
    strategy: str
    pair: str
    symbol: str
    interval: str
    roadmap_bt_ev: float
    structure_complexity: str


CANDIDATES = (
    Candidate(1, "bb_squeeze_breakout", "USD_JPY", "USDJPY=X", "5m", 1.030, "BB + squeeze (1 indicator + 1 condition)"),
    Candidate(2, "engulfing_bb", "USD_JPY", "USDJPY=X", "5m", 0.677, "engulfing candle + BB extreme (2 conditions)"),
    Candidate(3, "fib_reversal", "EUR_USD", "EURUSD=X", "1m", 0.426, "Fib retracement (1 level set)"),
    Candidate(4, "sr_channel_reversal", "EUR_USD", "EURUSD=X", "5m", 0.231, "SR / channel bounce (1 level set)"),
)

CANDIDATE_BY_STRATEGY = {c.strategy: c for c in CANDIDATES}


try:
    from tools.cell_edge_audit import wilson_lower as _wilson_lower
except Exception:  # pragma: no cover - fallback for isolated imports
    _wilson_lower = None

try:
    from tools.cell_negative_edge_audit import wilson_upper_at as _wilson_upper_at
except Exception:  # pragma: no cover - fallback for isolated imports
    _wilson_upper_at = None

try:
    from modules.stats_utils import kelly_criterion
except Exception:  # pragma: no cover - fallback for isolated imports
    kelly_criterion = None


def _round(value: float | None, ndigits: int = 4) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and (math.isinf(value) or math.isnan(value)):
        return value
    return round(float(value), ndigits)


def wilson_lower_95(wins: int, n: int) -> float:
    if _wilson_lower is not None:
        return float(_wilson_lower(wins, n))
    if n <= 0:
        return 0.0
    z = 1.96
    phat = wins / n
    denom = 1 + z * z / n
    centre = phat + z * z / (2 * n)
    spread = z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n))
    return max(0.0, (centre - spread) / denom)


def wilson_upper_95(wins: int, n: int) -> float:
    if n <= 0:
        return 1.0
    wr = wins / n
    if _wilson_upper_at is not None:
        return float(_wilson_upper_at(wr, n))
    z = 1.96
    denom = 1 + z * z / n
    centre = wr + z * z / (2 * n)
    spread = z * math.sqrt((wr * (1 - wr) + z * z / (4 * n)) / n)
    return min(1.0, (centre + spread) / denom)


def binomial_one_sided_p(wins: int, n: int, null_wr: float) -> float:
    """Exact one-sided P[X >= wins] under Binomial(n, null_wr)."""
    if n <= 0:
        return 1.0
    if wins <= 0:
        return 1.0
    if null_wr <= 0:
        return 0.0
    if null_wr >= 1:
        return 1.0

    logs = []
    log_p = math.log(null_wr)
    log_q = math.log1p(-null_wr)
    lg_n1 = math.lgamma(n + 1)
    for k in range(wins, n + 1):
        logs.append(lg_n1 - math.lgamma(k + 1) - math.lgamma(n - k + 1)
                    + k * log_p + (n - k) * log_q)
    m = max(logs)
    return max(0.0, min(1.0, math.exp(m) * sum(math.exp(x - m) for x in logs)))


def bonferroni_one_sided_p(wins: int, n: int, null_wr: float) -> float:
    return min(1.0, binomial_one_sided_p(wins, n, null_wr) * BONFERRONI_K)


def trade_entry_type(trade: dict[str, Any]) -> str:
    return str(trade.get("entry_type") or trade.get("type") or "")


def trade_pnl_pips(trade: dict[str, Any]) -> float:
    """Reconstruct per-trade PnL units from run_scalp_backtest trade_log.

    The engine trade_log does not currently expose literal pnl_pips. When a
    pnl field is present we use it; otherwise we reconstruct sign-adjusted
    engine PnL units from tp_m/sl_m/actual_sl_m, matching the result shape
    available without modifying app.py.
    """
    for key in ("pnl_pips", "pnl", "pnl_pip"):
        if trade.get(key) is not None:
            return float(trade[key])
    outcome = str(trade.get("outcome") or "").upper()
    if outcome == "WIN":
        return float(trade.get("tp_m") or 0.0)
    if outcome == "LOSS":
        return -float(trade.get("actual_sl_m", trade.get("sl_m") or 0.0) or 0.0)
    return 0.0


def profit_factor(pnls: list[float]) -> float:
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p < 0))
    if gross_loss == 0:
        return 999.0 if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def max_drawdown(pnls: list[float]) -> tuple[float, float]:
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    peak_equity = max(INITIAL_CAPITAL_PIP_SURROGATE, INITIAL_CAPITAL_PIP_SURROGATE + peak)
    return max_dd, max_dd / peak_equity if peak_equity > 0 else 0.0


def split_walk_forward(pnls: list[float], outcomes: list[str]) -> dict[str, float | int]:
    split = len(pnls) // 2
    is_pnls = pnls[:split]
    oos_pnls = pnls[split:]
    is_outcomes = outcomes[:split]
    oos_outcomes = outcomes[split:]

    def wr(values: list[str]) -> float:
        return values.count("WIN") / len(values) if values else 0.0

    return {
        "is_n": len(is_pnls),
        "oos_n": len(oos_pnls),
        "is_pf": profit_factor(is_pnls),
        "oos_pf": profit_factor(oos_pnls),
        "is_wr": wr(is_outcomes),
        "oos_wr": wr(oos_outcomes),
    }


def half_kelly(wr: float, pnls: list[float]) -> float:
    wins = [p for p in pnls if p > 0]
    losses = [-p for p in pnls if p < 0]
    if not wins or not losses:
        return 0.0
    avg_win = sum(wins) / len(wins)
    avg_loss = sum(losses) / len(losses)
    if kelly_criterion is None:
        b = avg_win / avg_loss
        full = (wr * b - (1 - wr)) / b
        return max(0.0, full / 2)
    return float(kelly_criterion(wr, avg_win, avg_loss).get("half_kelly", 0.0))


def apply_verdict(metrics: dict[str, Any]) -> dict[str, Any]:
    n = int(metrics.get("n", 0) or 0)
    if metrics.get("bt_gate_blocked"):
        return {
            "verdict": "BT_GATE_BLOCKED",
            "base_verdict": "BT_GATE_BLOCKED",
            "overfit_suspected": False,
            "downgraded_for_overfit": False,
            "gap_to_30": MIN_N,
            "reasons": ["N=0 despite pre-registered QUALIFIED_TYPES membership"],
        }
    if n < MIN_N:
        return {
            "verdict": "INSUFFICIENT",
            "base_verdict": "INSUFFICIENT",
            "overfit_suspected": False,
            "downgraded_for_overfit": False,
            "gap_to_30": MIN_N - n,
            "reasons": [f"N<{MIN_N} (gap={MIN_N - n})"],
        }

    pair = str(metrics["pair"])
    bev = BEV_WR_BY_PAIR[pair]
    pf = float(metrics.get("pf", 0.0) or 0.0)
    wlo = float(metrics.get("wilson_lo", 0.0) or 0.0)
    max_dd_pct = float(metrics.get("max_dd_pct", 1.0) or 1.0)
    wf_is_pf = float(metrics.get("wf_is_pf", 0.0) or 0.0)
    wf_oos_pf = float(metrics.get("wf_oos_pf", 0.0) or 0.0)
    p_bonf = float(metrics.get("bonferroni_p", 1.0) or 1.0)

    promote_checks = {
        "N>=30": n >= MIN_N,
        "PF>=1.30": pf >= PROMOTE_PF_MIN,
        "Wilson_lo>BEV+5pp": wlo > bev + PROMOTE_WILSON_MARGIN,
        "WF_IS_PF>=1.20": wf_is_pf >= PROMOTE_WF_PF_MIN,
        "WF_OOS_PF>=1.20": wf_oos_pf >= PROMOTE_WF_PF_MIN,
        "Bonferroni_p<0.0125": p_bonf < ALPHA_BONFERRONI,
        "max_DD_pct<=30%": max_dd_pct <= MAX_DD_PCT_LIMIT,
    }
    shadow_checks = {
        "N>=30": n >= MIN_N,
        "PF>=1.10": pf >= SHADOW_PF_MIN,
        "Wilson_lo>BEV": wlo > bev,
        "WF_IS_PF>=1.00": wf_is_pf >= SHADOW_WF_PF_MIN,
        "WF_OOS_PF>=1.00": wf_oos_pf >= SHADOW_WF_PF_MIN,
        "max_DD_pct<=30%": max_dd_pct <= MAX_DD_PCT_LIMIT,
    }

    if all(promote_checks.values()):
        base = "PROMOTE"
        failed = [k for k, v in promote_checks.items() if not v]
    elif all(shadow_checks.values()):
        base = "SHADOW"
        failed = [k for k, v in promote_checks.items() if not v]
    else:
        base = "REJECT"
        failed = [k for k, v in shadow_checks.items() if not v]

    overfit = wf_is_pf > 0 and wf_oos_pf < wf_is_pf * OOS_STABILITY_RATIO_MIN
    verdict = base
    downgraded = False
    if overfit:
        if base == "PROMOTE":
            verdict = "SHADOW"
            downgraded = True
        elif base == "SHADOW":
            verdict = "REJECT"
            downgraded = True

    reasons = []
    if failed:
        reasons.append("failed: " + ", ".join(failed))
    if overfit:
        reasons.append("OVERFIT_SUSPECTED: OOS PF degraded by >15% from IS PF")

    return {
        "verdict": verdict,
        "base_verdict": base,
        "overfit_suspected": overfit,
        "downgraded_for_overfit": downgraded,
        "gap_to_30": 0,
        "reasons": reasons,
    }


def summarize_candidate_result(candidate: Candidate, engine_result: dict[str, Any], elapsed_s: float) -> dict[str, Any]:
    trade_log = engine_result.get("trade_log") or []
    target_trades = [t for t in trade_log if trade_entry_type(t) == candidate.strategy]
    pnls = [trade_pnl_pips(t) for t in target_trades]
    outcomes = [str(t.get("outcome") or "").upper() for t in target_trades]
    n = len(target_trades)
    wins = outcomes.count("WIN")
    losses = outcomes.count("LOSS")
    wr = wins / n if n else 0.0
    ev = sum(pnls) / n if n else 0.0
    pf = profit_factor(pnls)
    wlo = wilson_lower_95(wins, n)
    whi = wilson_upper_95(wins, n)
    dd_pip, dd_pct = max_drawdown(pnls)
    wf = split_walk_forward(pnls, outcomes)
    p_raw = binomial_one_sided_p(wins, n, BEV_WR_BY_PAIR[candidate.pair])
    p_bonf = min(1.0, p_raw * BONFERRONI_K)

    metrics = {
        "strategy": candidate.strategy,
        "pair": candidate.pair,
        "symbol": candidate.symbol,
        "interval": candidate.interval,
        "lookback_days": LOOKBACK_DAYS,
        "roadmap_bt_ev": candidate.roadmap_bt_ev,
        "structure_complexity": candidate.structure_complexity,
        "n": n,
        "wins": wins,
        "losses": losses,
        "wr": wr,
        "ev_pip_per_trade": ev,
        "pf": pf,
        "wilson_lo": wlo,
        "wilson_hi": whi,
        "max_dd_pip": dd_pip,
        "max_dd_pct": dd_pct,
        "wf_is_pf": wf["is_pf"],
        "wf_oos_pf": wf["oos_pf"],
        "wf_is_wr": wf["is_wr"],
        "wf_oos_wr": wf["oos_wr"],
        "wf_is_n": wf["is_n"],
        "wf_oos_n": wf["oos_n"],
        "binomial_one_sided_p": p_raw,
        "bonferroni_p": p_bonf,
        "half_kelly": half_kelly(wr, pnls),
        "bt_gate_blocked": n == 0,
        "likely_gate_chain_failure": (
            "signal-confirmation count, friction/spread-SL gate, Phase0/session filter, "
            "or _compute_bt_htf_bias blocked all candidate entries"
            if n == 0 else None
        ),
    }
    verdict = apply_verdict(metrics)
    return {
        "schema": "scalp_alt_pre_reg_candidate_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": RUN_ID,
        "candidate": asdict(candidate),
        "engine": {
            "name": "run_scalp_backtest",
            "elapsed_s": round(elapsed_s, 3),
            "total_engine_trades": engine_result.get("trades", 0),
            "engine_error": engine_result.get("error"),
            "data_source": engine_result.get("data_source"),
            "bars_fetched": engine_result.get("bars_fetched"),
        },
        "locked_constants": locked_constants(),
        "metrics": {k: _round(v, 6) if isinstance(v, float) else v for k, v in metrics.items()},
        "verdict": verdict,
        "raw_engine_result": engine_result,
    }


class Timeout:
    def __init__(self, seconds: int):
        self.seconds = int(seconds)
        self._old_handler = None

    def __enter__(self):
        if hasattr(signal, "SIGALRM") and self.seconds > 0:
            self._old_handler = signal.signal(signal.SIGALRM, self._raise)
            signal.alarm(self.seconds)
        return self

    def __exit__(self, exc_type, exc, tb):
        if hasattr(signal, "SIGALRM"):
            signal.alarm(0)
            if self._old_handler is not None:
                signal.signal(signal.SIGALRM, self._old_handler)
        return False

    def _raise(self, signum, frame):  # noqa: ARG002
        raise TimeoutError(f"run_scalp_backtest exceeded --engine-timeout={self.seconds}s")


def run_candidate(candidate: Candidate, engine_timeout: int) -> dict[str, Any]:
    os.environ.setdefault("BT_MODE", "1")
    os.environ.setdefault("NO_AUTOSTART", "1")
    import app  # Imported lazily so tests/dry-run do not initialize Flask app.

    if hasattr(app, "_scalp_bt_cache"):
        app._scalp_bt_cache.clear()

    started = time.time()
    with Timeout(engine_timeout):
        result = app.run_scalp_backtest(
            candidate.symbol,
            lookback_days=LOOKBACK_DAYS,
            interval=candidate.interval,
        )
    return summarize_candidate_result(candidate, result, time.time() - started)


def locked_constants() -> dict[str, Any]:
    return {
        "lock_date": LOCK_DATE,
        "lookback_days": LOOKBACK_DAYS,
        "bonferroni_k": BONFERRONI_K,
        "alpha": ALPHA,
        "alpha_bonferroni": ALPHA_BONFERRONI,
        "min_n": MIN_N,
        "promote": {
            "pf_min": PROMOTE_PF_MIN,
            "wilson_margin_over_bev": PROMOTE_WILSON_MARGIN,
            "wf_is_pf_min": PROMOTE_WF_PF_MIN,
            "wf_oos_pf_min": PROMOTE_WF_PF_MIN,
            "bonferroni_p_lt": ALPHA_BONFERRONI,
            "max_dd_pct_lte": MAX_DD_PCT_LIMIT,
        },
        "shadow": {
            "pf_min": SHADOW_PF_MIN,
            "wilson_margin_over_bev": 0.0,
            "wf_is_pf_min": SHADOW_WF_PF_MIN,
            "wf_oos_pf_min": SHADOW_WF_PF_MIN,
            "max_dd_pct_lte": MAX_DD_PCT_LIMIT,
        },
        "oos_stability_ratio_min": OOS_STABILITY_RATIO_MIN,
        "bev_wr_by_pair": BEV_WR_BY_PAIR,
        "initial_capital_pip_surrogate": INITIAL_CAPITAL_PIP_SURROGATE,
        "promote_tiebreak_fields": PROMOTE_TIEBREAK_FIELDS,
    }


def dry_run_text() -> str:
    lines = [
        "# A2-alt Scalp Pre-reg BT Dry Run",
        "",
        "LOCKED constants:",
        f"- LOOKBACK_DAYS={LOOKBACK_DAYS}",
        f"- BONFERRONI_K={BONFERRONI_K}",
        f"- ALPHA={ALPHA}",
        f"- ALPHA_BONFERRONI={ALPHA_BONFERRONI:.4f}",
        f"- MIN_N={MIN_N}",
        f"- PROMOTE: PF>={PROMOTE_PF_MIN}, Wilson_lo>BEV+{PROMOTE_WILSON_MARGIN:.0%}, "
        f"WF IS/OOS PF>={PROMOTE_WF_PF_MIN}, p_bonf<{ALPHA_BONFERRONI:.4f}, maxDD<={MAX_DD_PCT_LIMIT:.0%}",
        f"- SHADOW: PF>={SHADOW_PF_MIN}, Wilson_lo>BEV, "
        f"WF IS/OOS PF>={SHADOW_WF_PF_MIN}, maxDD<={MAX_DD_PCT_LIMIT:.0%}",
        "- REJECT: any non-insufficient configuration that fails Promote and Shadow gates",
        f"- INSUFFICIENT: N<{MIN_N}, with explicit gap-to-30",
        f"- OVERFIT_SUSPECTED if OOS_PF < IS_PF * {OOS_STABILITY_RATIO_MIN}",
        "",
        "BEV_WR:",
    ]
    for pair, wr in BEV_WR_BY_PAIR.items():
        lines.append(f"- {pair}: {wr:.1%}")
    lines.extend(["", "Candidates:"])
    for c in CANDIDATES:
        lines.append(
            f"{c.ordinal}. {c.strategy} | {c.pair} | {c.symbol} | {c.interval} | "
            f"roadmap EV {c.roadmap_bt_ev:+.3f} | {c.structure_complexity}"
        )
    return "\n".join(lines) + "\n"


def load_candidate_json(path: Path, candidate: Candidate) -> dict[str, Any]:
    if not path.exists():
        return {
            "schema": "scalp_alt_pre_reg_candidate_v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "run_id": RUN_ID,
            "candidate": asdict(candidate),
            "engine": {"name": "run_scalp_backtest", "status": "BT_PENDING"},
            "locked_constants": locked_constants(),
            "metrics": {
                "strategy": candidate.strategy,
                "pair": candidate.pair,
                "symbol": candidate.symbol,
                "interval": candidate.interval,
                "lookback_days": LOOKBACK_DAYS,
                "roadmap_bt_ev": candidate.roadmap_bt_ev,
                "structure_complexity": candidate.structure_complexity,
            },
            "verdict": {
                "verdict": "BT_PENDING",
                "base_verdict": "BT_PENDING",
                "overfit_suspected": False,
                "downgraded_for_overfit": False,
                "gap_to_30": MIN_N,
                "reasons": [f"missing parent-run JSON: {path}"],
            },
        }
    with path.open() as f:
        return json.load(f)


def _promote_sort_key(record: dict[str, Any]) -> tuple:
    m = record.get("metrics", {})
    return (
        float(m.get("bonferroni_p", 1.0) or 1.0),
        -float(m.get("pf", 0.0) or 0.0),
        -float(m.get("ev_pip_per_trade", 0.0) or 0.0),
        -int(m.get("n", 0) or 0),
    )


def enforce_single_promote(records: list[dict[str, Any]]) -> None:
    promote_records = [r for r in records if r.get("verdict", {}).get("verdict") == "PROMOTE"]
    if len(promote_records) <= 1:
        return
    winner = sorted(promote_records, key=_promote_sort_key)[0]
    for record in promote_records:
        if record is winner:
            record["verdict"]["promote_selected"] = True
            continue
        record["verdict"]["promote_selected"] = False
        record["verdict"]["base_verdict_before_promote_cap"] = record["verdict"]["base_verdict"]
        record["verdict"]["verdict"] = "SHADOW"
        record["verdict"].setdefault("reasons", []).append(
            "PROMOTE_CAP: downgraded because only one Promote may be selected"
        )


def aggregate_records(input_paths: dict[str, Path]) -> dict[str, Any]:
    records = [
        load_candidate_json(input_paths[c.strategy], c)
        for c in CANDIDATES
    ]
    enforce_single_promote(records)
    verdict_counts: dict[str, int] = {}
    for record in records:
        verdict = record.get("verdict", {}).get("verdict", "UNKNOWN")
        verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
    pending = [
        r for r in records
        if r.get("verdict", {}).get("verdict") == "BT_PENDING"
    ]
    promote_or_shadow = [
        r for r in records
        if r.get("verdict", {}).get("verdict") in {"PROMOTE", "SHADOW"}
    ]
    next_task = (
        "Parent Claude — execute the four pre-registered --candidate runs, then rerun --aggregate"
        if pending
        else "A3-simple — register the Promote candidate to OANDA bridge with monitoring"
        if any(r.get("verdict", {}).get("verdict") == "PROMOTE" for r in records)
        else "A3-simple-shadow — register Shadow candidate at lot=0.1 with monitoring"
        if promote_or_shadow
        else "A2-alt2 — pre-register the next simple candidate from the broader Scalp pool"
    )
    return {
        "schema": "scalp_alt_pre_reg_aggregate_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": RUN_ID,
        "locked_constants": locked_constants(),
        "input_paths": {k: str(v) for k, v in input_paths.items()},
        "records": records,
        "verdict_counts": verdict_counts,
        "next_task": next_task,
    }


def fmt_pct(value: Any) -> str:
    if value is None or value == "":
        return "NA"
    try:
        return f"{float(value) * 100:.1f}%"
    except Exception:
        return "NA"


def fmt_num(value: Any, digits: int = 3) -> str:
    if value is None or value == "":
        return "NA"
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return "NA"


def render_markdown(aggregate: dict[str, Any]) -> str:
    constants = aggregate["locked_constants"]
    records = aggregate["records"]
    lines = [
        "# Scalp Alt Simple-Structure Pre-registration (LOCKED)",
        "",
        f"- Date: {LOCK_DATE}",
        f"- Engine: `run_scalp_backtest` standard BT only",
        f"- Lookback: {LOOKBACK_DAYS}d",
        "- Lineage: direct simple-first execution of `knowledge-base/wiki/decisions/complex-gate-edge-destruction-pattern-2026-05-03.md`.",
        "- Registration to OANDA bridge is out of scope and gated on this verdict.",
        "",
        "## LOCKED Thresholds",
        "",
        f"- Bonferroni K={BONFERRONI_K}; alpha/K={ALPHA_BONFERRONI:.4f}. Candidate pool is fixed ex ante.",
        f"- Promote: N>=30, PF>=1.30, Wilson_lo > BEV_WR + 5pp, WF IS/OOS PF>=1.20, Bonferroni p < {ALPHA_BONFERRONI:.4f}, max DD <=30%.",
        "- Shadow: N>=30, PF>=1.10, Wilson_lo > BEV_WR, WF IS/OOS PF>=1.00, max DD <=30%.",
        "- Reject: any other configuration.",
        "- Insufficient: N<30 with explicit gap-to-30.",
        f"- OVERFIT_SUSPECTED: OOS PF < IS PF * {OOS_STABILITY_RATIO_MIN}; downgrade Promote->Shadow or Shadow->Reject.",
        f"- BEV_WR: USD_JPY={constants['bev_wr_by_pair']['USD_JPY']:.1%}, EUR_USD={constants['bev_wr_by_pair']['EUR_USD']:.1%}.",
        "- Metric note: if `run_scalp_backtest` trade_log lacks literal `pnl_pips`, EV/PF/DD use reconstructed sign-adjusted engine PnL units from `tp_m/sl_m/actual_sl_m`; raw engine output is retained in JSON.",
        "",
        "## Verdict Summary",
        "",
        "| # | Strategy | Pair | TF | Verdict | N | WR | EV | PF | Bonf p | Overfit | Gap |",
        "|---|---|---|---|---|---:|---:|---:|---:|---:|---|---:|",
    ]
    for record in records:
        c = record["candidate"]
        m = record.get("metrics", {})
        v = record.get("verdict", {})
        lines.append(
            f"| {c['ordinal']} | `{c['strategy']}` | {c['pair']} | {c['interval']} | "
            f"{v.get('verdict', 'UNKNOWN')} | {m.get('n', 'NA')} | {fmt_pct(m.get('wr'))} | "
            f"{fmt_num(m.get('ev_pip_per_trade'))} | {fmt_num(m.get('pf'))} | "
            f"{fmt_num(m.get('bonferroni_p'), 6)} | {v.get('overfit_suspected', False)} | "
            f"{v.get('gap_to_30', 0)} |"
        )
    lines.extend([
        "",
        "## Per-candidate Quant Table",
        "",
        "| Strategy | N | Wins/Losses | WR | EV | PF | Wilson 95% CI | max DD pip | max DD % | WF IS PF/OOS PF | WF IS WR/OOS WR | Bonf p | Half-Kelly |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for record in records:
        m = record.get("metrics", {})
        lines.append(
            f"| `{m.get('strategy', record['candidate']['strategy'])}` | {m.get('n', 'NA')} | "
            f"{m.get('wins', 'NA')}/{m.get('losses', 'NA')} | {fmt_pct(m.get('wr'))} | "
            f"{fmt_num(m.get('ev_pip_per_trade'))} | {fmt_num(m.get('pf'))} | "
            f"[{fmt_pct(m.get('wilson_lo'))}, {fmt_pct(m.get('wilson_hi'))}] | "
            f"{fmt_num(m.get('max_dd_pip'))} | {fmt_pct(m.get('max_dd_pct'))} | "
            f"{fmt_num(m.get('wf_is_pf'))}/{fmt_num(m.get('wf_oos_pf'))} | "
            f"{fmt_pct(m.get('wf_is_wr'))}/{fmt_pct(m.get('wf_oos_wr'))} | "
            f"{fmt_num(m.get('bonferroni_p'), 6)} | {fmt_num(m.get('half_kelly'), 4)} |"
        )
    lines.extend(["", "## Candidate Notes", ""])
    for record in records:
        c = record["candidate"]
        v = record.get("verdict", {})
        reasons = "; ".join(v.get("reasons", [])) or "all locked checks satisfied for stated verdict"
        likely = record.get("metrics", {}).get("likely_gate_chain_failure")
        lines.append(f"- `{c['strategy']}`: {v.get('verdict', 'UNKNOWN')}. {reasons}.")
        if likely:
            lines.append(f"  Gate-chain note: {likely}.")
    lines.extend([
        "",
        "## Next Task",
        "",
        aggregate["next_task"],
        "",
    ])
    return "\n".join(lines)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def parse_input_paths(values: list[str] | None) -> dict[str, Path]:
    paths = dict(DEFAULT_SINGLE_OUTPUTS)
    for value in values or []:
        if "=" not in value:
            raise SystemExit(f"--input must be strategy=path, got: {value}")
        strategy, raw_path = value.split("=", 1)
        if strategy not in CANDIDATE_BY_STRATEGY:
            raise SystemExit(f"unknown strategy in --input: {strategy}")
        paths[strategy] = Path(raw_path)
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="print LOCKED constants and candidate pool")
    parser.add_argument("--candidate", choices=sorted(CANDIDATE_BY_STRATEGY), help="run one candidate via run_scalp_backtest")
    parser.add_argument("--aggregate", action="store_true", help="aggregate parent-run JSON files and render verdict docs")
    parser.add_argument("--input", action="append", help="aggregate input override: strategy=path")
    parser.add_argument("--output", help="output path for candidate JSON or aggregate markdown")
    parser.add_argument("--engine-timeout", type=int, default=600, help="run_scalp_backtest timeout seconds")
    args = parser.parse_args(argv)

    if args.dry_run:
        print(dry_run_text(), end="")
        return 0

    if args.candidate:
        candidate = CANDIDATE_BY_STRATEGY[args.candidate]
        payload = run_candidate(candidate, args.engine_timeout)
        output = Path(args.output) if args.output else DEFAULT_SINGLE_OUTPUTS[candidate.strategy]
        write_json(output, payload)
        print(f"wrote {output}")
        return 0

    if args.aggregate:
        aggregate = aggregate_records(parse_input_paths(args.input))
        md = render_markdown(aggregate)
        write_json(RAW_AGG_JSON, aggregate)
        write_text(RAW_AGG_MD, md)
        output = Path(args.output) if args.output else DEFAULT_DOC
        if output.suffix.lower() == ".json":
            write_json(output, aggregate)
        else:
            write_text(output, md)
        print(f"wrote {RAW_AGG_JSON}")
        print(f"wrote {RAW_AGG_MD}")
        print(f"wrote {output}")
        return 0

    parser.error("choose one of --dry-run, --candidate, or --aggregate")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
