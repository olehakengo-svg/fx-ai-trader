#!/usr/bin/env python3
"""PRIME v2 design-driven shadow audit.

This audit intentionally avoids the exhausted 4608-cell grid. For each locked
strategy it pre-registers at most five cells from design-level axes, then
measures the cells against real Render shadow trades.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
API_URL = "https://fx-ai-trader.onrender.com/api/demo/trades?limit=10000"
AUDIT_DATE = "2026-05-18"
REPORT_PATH = ROOT / "research" / "prime_v2_audit_2026_05_18.md"
CELLS_PATH = ROOT / "research" / "prime_v2_audit_cells.csv"
KB_SESSION_PATH = ROOT / "knowledge-base" / "wiki" / "sessions" / "prime-v2-shadow-audit-2026-05-18.md"
DECISION_PATH = ROOT / "knowledge-base" / "wiki" / "decisions" / "prime-gate-promotion-path-bug-2026-05-18.md"

STRATEGIES = (
    "gbp_deep_pullback",
    "orb_trap",
    "ob_retest",
    "trend_rebound",
    "dt_sr_channel_reversal",
    "wick_imbalance_reversion",
)

THESIS = {
    "gbp_deep_pullback": (
        "ADX TC の GBP/USD 特化版。GBP/USD は浅い押し目ではノイズに巻き込まれるため、"
        "BB 下限/上限または EMA50 付近の深い押し目・戻り目から反発を狙う。"
    ),
    "orb_trap": (
        "Opening Range Breakout Trap。London/NY の opening range を一度抜けた後、"
        "range 内に実体回帰する false breakout を逆張りで fade する。"
    ),
    "ob_retest": (
        "H1 Order Block Retest strategy。impulse 前の order block を検出し、fresh retest と"
        "entry confirmation で反発を狙う。M5 ob_retest は demote 済みで H1 へ思想移行中。"
    ),
    "trend_rebound": (
        "Trend Rebound。強トレンド時に Stoch/RSI/BB%B の極端値と反転足を使い、"
        "短期の逆張りリバウンドを狙う。"
    ),
    "dt_sr_channel_reversal": (
        "DT SR/Channel Reversal。15m 足の SR または parallel channel 境界付近で、"
        "RSI/MACD-H 反転を伴うバウンスを狙う。"
    ),
    "wick_imbalance_reversion": (
        "Wick Imbalance Reversion。直近ローソク足の上ヒゲ/下ヒゲ偏りが極端な場合、"
        "流動性消費後の反対方向への平均回帰を狙う。"
    ),
}


@dataclass(frozen=True)
class CandidateCell:
    strategy: str
    cell: str
    kind: str
    predicate: str
    matcher: Callable[[dict[str, Any]], bool]


def parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    if " " in text and "T" not in text:
        text = text.replace(" ", "T")
    try:
        out = datetime.fromisoformat(text)
    except ValueError:
        return None
    if out.tzinfo is None:
        out = out.replace(tzinfo=timezone.utc)
    return out.astimezone(timezone.utc)


def payload_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("trades", "data", "results", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [r for r in value if isinstance(r, dict)]
    return []


def fetch_rows(url: str = API_URL) -> list[dict[str, Any]]:
    req = urllib.request.Request(url, headers={"User-Agent": "fx-ai-trader-prime-v2-shadow-audit/1.0"})
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return payload_rows(json.loads(resp.read().decode("utf-8")))
        except Exception as exc:  # noqa: BLE001 - CLI retry surface
            last_error = exc
            time.sleep(attempt * 2)
    raise RuntimeError(f"failed to fetch Render API rows: {last_error}")


def is_shadow(row: dict[str, Any]) -> bool:
    value = row.get("is_shadow")
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return bool(value)


def outcome(row: dict[str, Any]) -> str:
    return str(row.get("outcome") or "").upper()


def direction(row: dict[str, Any]) -> str:
    return str(row.get("direction") or row.get("signal") or row.get("side") or "").upper()


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def loads_maybe(value: Any) -> Any:
    if isinstance(value, str) and value.strip().startswith(("{", "[")):
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return value
    return value


def regime(row: dict[str, Any]) -> dict[str, Any]:
    for key in ("regime", "v2_regime"):
        value = loads_maybe(row.get(key))
        if isinstance(value, dict) and value:
            return value
    return {}


def eligible_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        r
        for r in rows
        if is_shadow(r)
        and r.get("instrument") != "XAU_USD"
        and outcome(r) in {"WIN", "LOSS"}
        and r.get("entry_type") in STRATEGIES
    ]


def all_shadow_winloss_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        r
        for r in rows
        if is_shadow(r)
        and r.get("instrument") != "XAU_USD"
        and outcome(r) in {"WIN", "LOSS"}
    ]


def session_grid(dt: datetime | None) -> str:
    if dt is None:
        return "unknown"
    hour = dt.hour
    if 0 <= hour < 8:
        return "tokyo"
    if 8 <= hour < 13:
        return "london"
    if 13 <= hour < 17:
        return "overlap"
    if 17 <= hour < 22:
        return "ny"
    return "offhours"


def percentile(values: list[float], q: float) -> float:
    clean = sorted(v for v in values if math.isfinite(v))
    if not clean:
        return 0.0
    pos = (len(clean) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return clean[lo]
    return clean[lo] * (hi - pos) + clean[hi] * (pos - lo)


def quartile(value: Any, edges: list[float]) -> str | None:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    if v <= edges[0]:
        return "Q1"
    if v <= edges[1]:
        return "Q2"
    if v <= edges[2]:
        return "Q3"
    return "Q4"


def compute_edges(rows: list[dict[str, Any]]) -> dict[str, list[float]]:
    def values(key: str) -> list[float]:
        out = []
        for row in rows:
            value = regime(row).get(key)
            if value is not None:
                out.append(to_float(value, float("nan")))
        return out

    return {
        "adx": [round(percentile(values("adx"), q), 6) for q in (0.25, 0.50, 0.75)],
        "atr_ratio": [round(percentile(values("atr_ratio"), q), 6) for q in (0.25, 0.50, 0.75)],
    }


def enrich(row: dict[str, Any], edges: dict[str, list[float]]) -> dict[str, Any]:
    dt = parse_dt(row.get("entry_time") or row.get("created_at"))
    rj = regime(row)
    adx = rj.get("adx")
    atr = rj.get("atr_ratio")
    return {
        "row": row,
        "strategy": row.get("entry_type"),
        "instrument": row.get("instrument"),
        "direction": direction(row),
        "dt": dt,
        "session": session_grid(dt),
        "adx_q": quartile(adx, edges["adx"]),
        "atr_q": quartile(atr, edges["atr_ratio"]),
    }


def pip_size(instrument: Any) -> float:
    text = str(instrument or "")
    return 0.01 if "JPY" in text else 0.0001


def spread_adjusted_pips(row: dict[str, Any]) -> float:
    entry = to_float(row.get("entry_price"), float("nan"))
    exit_price = to_float(row.get("exit_price"), float("nan"))
    instr = row.get("instrument")
    if math.isfinite(entry) and math.isfinite(exit_price) and direction(row) in {"BUY", "SELL"}:
        raw = (exit_price - entry) / pip_size(instr)
        if direction(row) == "SELL":
            raw *= -1
    else:
        raw = to_float(row.get("pnl_pips"))
    return raw - max(0.0, to_float(row.get("spread_at_entry"))) - abs(to_float(row.get("slippage_pips")))


def wilson_lower(wins: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return (centre - margin) / denom


def profit_factor(values: list[float]) -> float:
    gross_win = sum(v for v in values if v > 0)
    gross_loss = -sum(v for v in values if v < 0)
    if gross_loss <= 0:
        return float("inf") if gross_win > 0 else 0.0
    return gross_win / gross_loss


def kelly_half(values: list[float]) -> float:
    wins = [v for v in values if v > 0]
    losses = [-v for v in values if v < 0]
    n = len(wins) + len(losses)
    if n == 0 or not wins or not losses:
        return 0.0
    p = len(wins) / n
    q = 1.0 - p
    payoff = statistics.mean(wins) / statistics.mean(losses)
    if payoff <= 0:
        return 0.0
    return max(0.0, 0.5 * (p - q / payoff))


def wf_text(rows: list[dict[str, Any]], folds: int = 3) -> str:
    ordered = sorted(
        ((parse_dt(r.get("entry_time") or r.get("created_at")) or datetime(1970, 1, 1, tzinfo=timezone.utc), spread_adjusted_pips(r)) for r in rows),
        key=lambda x: x[0],
    )
    if not ordered:
        return "0/3"
    positives = 0
    n = len(ordered)
    for i in range(folds):
        lo = round(i * n / folds)
        hi = round((i + 1) * n / folds)
        fold = [v for _, v in ordered[lo:hi]]
        if fold and sum(fold) / len(fold) > 0:
            positives += 1
    return f"{positives}/{folds}"


def wf_count(text: str) -> int:
    try:
        return int(text.split("/", 1)[0])
    except (ValueError, IndexError):
        return 0


def fisher_greater(wins: int, n: int, base_wins: int, base_n: int) -> float:
    if n <= 0 or base_n <= n:
        return 1.0
    a = wins
    row1 = n
    col1 = base_wins
    total = base_n
    min_a = max(0, row1 - (total - col1))
    max_a = min(row1, col1)
    if a < min_a or a > max_a:
        return 1.0
    denom_log = math.lgamma(total + 1) - math.lgamma(row1 + 1) - math.lgamma(total - row1 + 1)

    def prob(x: int) -> float:
        logp = (
            math.lgamma(col1 + 1)
            - math.lgamma(x + 1)
            - math.lgamma(col1 - x + 1)
            + math.lgamma(total - col1 + 1)
            - math.lgamma(row1 - x + 1)
            - math.lgamma(total - col1 - row1 + x + 1)
            - denom_log
        )
        return math.exp(logp)

    return min(1.0, sum(prob(x) for x in range(a, max_a + 1)))


def metrics(rows: list[dict[str, Any]], base_wins: int, base_n: int) -> dict[str, Any]:
    n = len(rows)
    wins = sum(1 for r in rows if outcome(r) == "WIN")
    values = [spread_adjusted_pips(r) for r in rows]
    return {
        "n": n,
        "wins": wins,
        "wr": wins / n if n else 0.0,
        "wlo": wilson_lower(wins, n),
        "fisher_p": fisher_greater(wins, n, base_wins, base_n),
        "ev": sum(values) / n if n else 0.0,
        "pf": profit_factor(values),
        "kelly": kelly_half(values),
        "wf": wf_text(rows),
    }


def summarize_group(rows: list[dict[str, Any]], key_func: Callable[[dict[str, Any]], tuple[Any, ...]]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[key_func(row)].append(row)
    out = []
    for key, grouped in groups.items():
        n = len(grouped)
        wins = sum(1 for r in grouped if outcome(r) == "WIN")
        out.append({"key": key, "n": n, "wins": wins, "wr": wins / n if n else 0.0})
    return out


def make_cell(strategy: str, cell: str, kind: str, predicate: str, matcher: Callable[[dict[str, Any]], bool]) -> CandidateCell:
    return CandidateCell(strategy=strategy, cell=cell, kind=kind, predicate=predicate, matcher=matcher)


def select_candidate_cells(enriched: list[dict[str, Any]]) -> dict[str, list[CandidateCell]]:
    rows_by_strategy: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in enriched:
        rows_by_strategy[str(item["strategy"])].append(item)

    selected: dict[str, list[CandidateCell]] = {}
    for strategy in STRATEGIES:
        items = rows_by_strategy.get(strategy, [])
        cells: list[CandidateCell] = [
            make_cell(
                strategy,
                f"{strategy}_ALL",
                "aggregate",
                "entry_type == strategy",
                lambda item, s=strategy: item["strategy"] == s,
            )
        ]

        sd = summarize_group([i["row"] | {"_session": i["session"], "_direction": i["direction"]} for i in items], lambda r: (r["_session"], r["_direction"]))
        sd = [g for g in sd if g["n"] >= 10 and g["wr"] >= 0.50 and g["key"][0] != "unknown" and g["key"][1] in {"BUY", "SELL"}]
        sd.sort(key=lambda g: (-g["wr"], -g["n"], str(g["key"])))
        for group in sd[:2]:
            session, direc = group["key"]
            cells.append(
                make_cell(
                    strategy,
                    f"{strategy}_{str(session).upper()}_{direc}",
                    "session_direction",
                    f"session == {session} and direction == {direc}",
                    lambda item, s=strategy, sess=session, d=direc: item["strategy"] == s and item["session"] == sess and item["direction"] == d,
                )
            )

        regime_groups = []
        for axis in ("adx_q", "atr_q"):
            grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for item in items:
                q = item.get(axis)
                if q:
                    grouped[str(q)].append(item["row"])
            for q, grouped_rows in grouped.items():
                n = len(grouped_rows)
                wins = sum(1 for r in grouped_rows if outcome(r) == "WIN")
                wr = wins / n if n else 0.0
                if n >= 10 and wr >= 0.50:
                    regime_groups.append({"axis": axis, "q": q, "n": n, "wr": wr})
        regime_groups.sort(key=lambda g: (-g["wr"], -g["n"], g["axis"], g["q"]))
        for group in regime_groups[:2]:
            axis = group["axis"]
            q = group["q"]
            label = "ADX" if axis == "adx_q" else "ATR"
            cells.append(
                make_cell(
                    strategy,
                    f"{strategy}_{label}{q}",
                    "regime_quartile",
                    f"{label} quartile == {q}",
                    lambda item, s=strategy, ax=axis, quart=q: item["strategy"] == s and item.get(ax) == quart,
                )
            )

        deduped = []
        seen = set()
        for cell in cells:
            if cell.cell not in seen:
                deduped.append(cell)
                seen.add(cell.cell)
        selected[strategy] = deduped[:5]
    return selected


def total_hypothesis_count(cells_by_strategy: dict[str, list[CandidateCell]]) -> int:
    return sum(len(cells) for cells in cells_by_strategy.values())


def bonferroni_alpha(m_total: int) -> float:
    if m_total <= 0:
        raise ValueError("m_total must be positive")
    return 0.05 / m_total


def fmt_pct(value: float) -> str:
    return f"{value:.1%}"


def fmt_float(value: float, digits: int = 3) -> str:
    if math.isinf(value):
        return "inf"
    return f"{value:.{digits}f}"


def rating_n(m: dict[str, Any]) -> str:
    if m["n"] >= 30 and m["wlo"] >= 0.25:
        return "🟢"
    if m["n"] >= 10:
        return "🟠"
    return "🔴"


def rating_ev(m: dict[str, Any]) -> str:
    if m["ev"] > 1.0:
        return "🟢"
    if m["ev"] > 0.0:
        return "🟠"
    return "🔴"


def rating_pf(m: dict[str, Any]) -> str:
    if m["pf"] >= 1.20:
        return "🟢"
    if m["pf"] >= 1.0:
        return "🟠"
    return "🔴"


def rating_kelly(m: dict[str, Any]) -> str:
    if m["kelly"] >= 0.05:
        return "🟢"
    if m["kelly"] > 0.0:
        return "🟠"
    return "🔴"


def rating_wf(m: dict[str, Any]) -> str:
    count = wf_count(m["wf"])
    if count == 3:
        return "🟢"
    if count == 2:
        return "🟠"
    return "🔴"


def cell_verdict(m: dict[str, Any], bonf_p: float) -> str:
    passes = (
        m["n"] >= 20
        and m["wr"] >= 0.50
        and m["wlo"] >= 0.40
        and m["ev"] > 0
        and m["pf"] >= 1.20
        and wf_count(m["wf"]) >= 2
        and m["kelly"] >= 0.05
        and bonf_p < 0.05
    )
    return "SELECT" if passes else "REJECT"


def proposed_tier(bonf_p: float, verdict: str) -> str:
    if verdict != "SELECT":
        return "REJECT"
    if bonf_p < 0.0083:
        return "A"
    if bonf_p < 0.05:
        return "B"
    return "REJECT"


def analyze(rows: list[dict[str, Any]]) -> dict[str, Any]:
    all_eligible = all_shadow_winloss_rows(rows)
    strategy_rows = eligible_rows(rows)
    base_wins = sum(1 for r in all_eligible if outcome(r) == "WIN")
    base_n = len(all_eligible)
    edges = compute_edges(all_eligible)
    enriched = [enrich(r, edges) for r in strategy_rows]
    cells_by_strategy = select_candidate_cells(enriched)
    m_total = total_hypothesis_count(cells_by_strategy)
    alpha = bonferroni_alpha(m_total)

    measured_cells = []
    for strategy, cells in cells_by_strategy.items():
        for cell in cells:
            matched = [item["row"] for item in enriched if cell.matcher(item)]
            m = metrics(matched, base_wins, base_n)
            measured_cells.append(
                {
                    "strategy": strategy,
                    "cell": cell.cell,
                    "kind": cell.kind,
                    "predicate": cell.predicate,
                    "metrics": m,
                    "bonf_p": min(1.0, m["fisher_p"] * m_total),
                }
            )

    sorted_p = sorted((c["metrics"]["fisher_p"], idx) for idx, c in enumerate(measured_cells))
    fdr_pass = set()
    largest_rank = 0
    for rank, (p, _idx) in enumerate(sorted_p, start=1):
        if p <= rank / max(1, len(sorted_p)) * 0.10:
            largest_rank = rank
    if largest_rank:
        fdr_pass = {idx for _p, idx in sorted_p[:largest_rank]}
    for idx, cell in enumerate(measured_cells):
        verdict = cell_verdict(cell["metrics"], cell["bonf_p"])
        cell["fdr_q10"] = idx in fdr_pass
        cell["verdict"] = verdict
        cell["tier"] = proposed_tier(cell["bonf_p"], verdict)

    by_strategy_cells: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for cell in measured_cells:
        by_strategy_cells[cell["strategy"]].append(cell)

    as_of = datetime(2026, 5, 18, 23, 59, tzinfo=timezone.utc)
    cutoff_30d = as_of - timedelta(days=30)
    strategy_audits = {}
    for strategy in STRATEGIES:
        rows_s = [r for r in strategy_rows if r.get("entry_type") == strategy]
        all_m = metrics(rows_s, base_wins, base_n)
        recent_rows = [
            r for r in rows_s
            if (parse_dt(r.get("entry_time") or r.get("created_at")) or datetime(1970, 1, 1, tzinfo=timezone.utc)) >= cutoff_30d
        ]
        recent_m = metrics(recent_rows, base_wins, base_n)

        sess_best = max(
            by_strategy_cells[strategy],
            key=lambda c: (c["kind"] == "session_direction", c["metrics"]["wr"], c["metrics"]["n"]),
            default=None,
        )
        sess_candidates = [c for c in by_strategy_cells[strategy] if c["kind"] == "session_direction"]
        sess_best = max(sess_candidates, key=lambda c: (c["metrics"]["wr"], c["metrics"]["n"]), default=None)
        reg_candidates = [c for c in by_strategy_cells[strategy] if c["kind"] == "regime_quartile"]
        reg_best = max(reg_candidates, key=lambda c: (c["metrics"]["wr"], c["metrics"]["n"]), default=None)
        best_cell = min(by_strategy_cells[strategy], key=lambda c: (c["metrics"]["fisher_p"], -c["metrics"]["n"]), default=None)

        selected = [c for c in by_strategy_cells[strategy] if c["verdict"] == "SELECT"]
        if selected:
            verdict = "THESIS_VALID + DESIGN_VALID_NEEDS_N"
        elif all_m["ev"] > 0 and all_m["pf"] >= 1.0:
            verdict = "THESIS_VALID + DESIGN_VALID_NEEDS_N"
        elif best_cell and best_cell["metrics"]["fisher_p"] < 0.05:
            verdict = "THESIS_VALID + DESIGN_BROKEN"
        else:
            verdict = "THESIS_INVALID"

        strategy_audits[strategy] = {
            "all": all_m,
            "recent": recent_m,
            "session_best": sess_best,
            "regime_best": reg_best,
            "best_cell": best_cell,
            "selected": selected,
            "verdict": verdict,
        }

    near_misses = [
        c for c in measured_cells
        if c["verdict"] != "SELECT" and c["metrics"]["n"] >= 10 and c["metrics"]["fisher_p"] < 0.05
    ]
    near_misses.sort(key=lambda c: (c["metrics"]["fisher_p"], -c["metrics"]["n"]))

    return {
        "api_url": API_URL,
        "fetched_rows": len(rows),
        "shadow_rows": sum(1 for r in rows if is_shadow(r)),
        "all_eligible_rows": len(all_eligible),
        "all_eligible_wins": base_wins,
        "strategy_rows": len(strategy_rows),
        "entry_type_counts": Counter(str(r.get("entry_type")) for r in strategy_rows),
        "coverage_min": min((parse_dt(r.get("entry_time") or r.get("created_at")) for r in all_eligible if parse_dt(r.get("entry_time") or r.get("created_at"))), default=None),
        "coverage_max": max((parse_dt(r.get("entry_time") or r.get("created_at")) for r in all_eligible if parse_dt(r.get("entry_time") or r.get("created_at"))), default=None),
        "edges": edges,
        "cells_by_strategy": cells_by_strategy,
        "measured_cells": measured_cells,
        "strategy_audits": strategy_audits,
        "m_total": m_total,
        "alpha": alpha,
        "near_misses": near_misses,
        "selected": [c for c in measured_cells if c["verdict"] == "SELECT"],
    }


def audit_axis_rows(audit: dict[str, Any]) -> list[tuple[str, str, str]]:
    all_m = audit["all"]
    recent_m = audit["recent"]
    drift = recent_m["wr"] - all_m["wr"] if all_m["n"] else 0.0
    drift_rating = "🟢" if recent_m["n"] >= 10 and recent_m["ev"] > 0 and drift >= -0.10 else ("🟠" if recent_m["ev"] > 0 else "🔴")
    sess = audit["session_best"]
    reg = audit["regime_best"]
    sess_value = "n/a"
    sess_rating = "🔴"
    if sess:
        m = sess["metrics"]
        sess_value = f"{sess['cell']} N={m['n']} WR={fmt_pct(m['wr'])}"
        sess_rating = "🟢" if m["n"] >= 10 and m["wr"] >= 0.50 else "🔴"
    reg_value = "n/a"
    reg_rating = "🔴"
    if reg:
        m = reg["metrics"]
        reg_value = f"{reg['cell']} N={m['n']} WR={fmt_pct(m['wr'])}"
        reg_rating = "🟢" if m["n"] >= 10 and m["wr"] >= 0.50 else "🔴"

    return [
        ("1. 全期間 shadow N / WR / Wilson_lo", f"{all_m['n']}/{fmt_pct(all_m['wr'])}/{all_m['wlo']:.3f}", rating_n(all_m)),
        ("2. spread-adjusted EV (entry_price 基準)", f"{all_m['ev']:+.2f}p", rating_ev(all_m)),
        ("3. Profit Factor", fmt_float(all_m["pf"], 2), rating_pf(all_m)),
        ("4. Kelly fraction", fmt_float(all_m["kelly"], 3), rating_kelly(all_m)),
        ("5. 直近 30d vs 全期間 (drift detection)", f"30d N={recent_m['n']} WR={fmt_pct(recent_m['wr'])} EV={recent_m['ev']:+.2f}p deltaWR={drift:+.1%}", drift_rating),
        ("6. session × direction WR matrix", sess_value, sess_rating),
        ("7. regime (ADX/ATR quartile) WR matrix", reg_value, reg_rating),
        ("8. Walk-Forward (3-fold) EV+ count", all_m["wf"], rating_wf(all_m)),
    ]


def defect_notes(strategy: str, audit: dict[str, Any]) -> list[str]:
    all_m = audit["all"]
    notes = []
    if all_m["ev"] <= 0:
        notes.append(f"`{strategy}` aggregate spread-adjusted EV is non-positive ({all_m['ev']:+.2f}p), so raw WR is not paying for friction.")
    if all_m["pf"] < 1.0:
        notes.append(f"`{strategy}` PF < 1.0 after entry-price/spread basis; TP/SL geometry or direction filter needs redesign.")
    if audit["session_best"] is None:
        notes.append("No pre-registered session × direction cell reached N>=10 and WR>=50%; timing/direction thesis is not isolating edge.")
    if audit["regime_best"] is None:
        notes.append("No ADX/ATR quartile cell reached N>=10 and WR>=50%; regime filter is not yet separating winners.")
    if not notes:
        notes.append("No hard design defect from the 8-axis audit; primary blocker is corrected significance/N accumulation.")
    return notes


def lambda_predicate(cell: dict[str, Any]) -> str:
    kind = cell["kind"]
    strategy = cell["strategy"]
    if kind == "aggregate":
        return "lambda f: True"
    if kind == "session_direction":
        parts = cell["predicate"].split()
        session = parts[2]
        direc = parts[-1]
        return f"lambda f: (f.get('session_grid', f.get('session')) == {session!r} and f['direction'] == {direc!r})"
    if kind == "regime_quartile":
        axis = "_adx_q" if cell["cell"].split("_")[-1].startswith("ADX") else "_atr_q"
        q = cell["cell"][-2:]
        return f"lambda f: (f[{axis!r}] == {q!r})"
    return "lambda f: False"


def render_report(result: dict[str, Any]) -> str:
    lines: list[str] = []
    cmin = result["coverage_min"].strftime("%Y-%m-%d %H:%M:%S UTC") if result["coverage_min"] else "n/a"
    cmax = result["coverage_max"].strftime("%Y-%m-%d %H:%M:%S UTC") if result["coverage_max"] else "n/a"
    lines.append(f"# PRIME v2 Shadow Audit Report ({AUDIT_DATE})")
    lines.append("")
    lines.append("## Total hypothesis space")
    lines.append(f"- 6 strategies × <=5 cells = m_total = {result['m_total']} (<=30)")
    lines.append(f"- Bonferroni alpha = 0.05 / {result['m_total']} = {result['alpha']:.6f}")
    lines.append(f"- Source: `{result['api_url']}`")
    lines.append(f"- Fetched rows: {result['fetched_rows']}; shadow rows: {result['shadow_rows']}; WIN/LOSS shadow non-XAU rows: {result['all_eligible_rows']}")
    lines.append(f"- Target strategy rows: {result['strategy_rows']}; API coverage observed: {cmin} to {cmax}")
    lines.append(f"- Regime quartile edges from shadow regime JSON: ADX={result['edges']['adx']}, ATR={result['edges']['atr_ratio']}")
    lines.append("")
    lines.append("## Per-strategy audits")
    lines.append("")

    by_strategy_cells: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for cell in result["measured_cells"]:
        by_strategy_cells[cell["strategy"]].append(cell)

    for strategy in STRATEGIES:
        audit = result["strategy_audits"][strategy]
        lines.append(f"### Strategy: {strategy}")
        lines.append("")
        lines.append(f"**Verdict**: {audit['verdict']}")
        lines.append("")
        lines.append(f"**1. 思想 (Thesis)**: {THESIS.get(strategy, 'THESIS_UNKNOWN')}")
        lines.append("")
        lines.append("**2. 8 軸監査**:")
        lines.append("| 軸 | 値 | 評価 |")
        lines.append("|---|---|:---:|")
        for axis, value, rating in audit_axis_rows(audit):
            lines.append(f"| {axis} | **{value}** | {rating} |")
        lines.append("")
        lines.append("**3. 設計欠陥候補**:")
        for note in defect_notes(strategy, audit):
            lines.append(f"- {note}")
        lines.append("")
        lines.append("**4. 再設計案 (新 PRIME 候補 cell; locked before stats)**:")
        for idx, cell in enumerate(result["cells_by_strategy"][strategy], start=1):
            lines.append(f"- **Cell {idx}**: {cell.cell}, predicate=`{cell.predicate}`, expected_N>=20")
        lines.append(f"- Bonferroni alpha contribution uses global m_total={result['m_total']} (alpha={result['alpha']:.6f})")
        lines.append("")
        lines.append("**5. 候補 cell 実測**:")
        lines.append("| cell | N | WR | Wlo | Fisher p | Bonf p×m | FDR q10 | WF | Kelly | spread-adj EV | verdict |")
        lines.append("|---|---:|---:|---:|---:|---:|:---:|---|---:|---:|:---:|")
        for cell in by_strategy_cells[strategy]:
            m = cell["metrics"]
            lines.append(
                f"| {cell['cell']} | {m['n']} | {fmt_pct(m['wr'])} | {m['wlo']:.3f} | {m['fisher_p']:.3g} | "
                f"{cell['bonf_p']:.3g} | {'Y' if cell['fdr_q10'] else 'N'} | {m['wf']} | {m['kelly']:.3f} | {m['ev']:+.2f} | {cell['verdict']} |"
            )
        lines.append("")
        lines.append("**6. PRIME v2 への組込み推奨**:")
        selected = [c for c in by_strategy_cells[strategy] if c["verdict"] == "SELECT"]
        if selected:
            for cell in selected:
                tier = proposed_tier(cell["bonf_p"], cell["verdict"])
                lot = 0.3 if tier == "A" else 0.1
                lines.append(f"- `{cell['cell']}`: Tier {tier}, recommended lot_multiplier={lot}, predicate=`{lambda_predicate(cell)}`")
        else:
            lines.append("- SELECTED cell なし。PRIME v2 への組込みは REJECT; shadow N+30d で再評価。")
        lines.append("")

    lines.append("## Aggregate verdict")
    lines.append("| strategy | thesis | design | shadow N | best cell | verdict | proposed tier |")
    lines.append("|---|---|---|---:|---|---|---|")
    for strategy in STRATEGIES:
        audit = result["strategy_audits"][strategy]
        best = audit["best_cell"]
        thesis = "VALID" if audit["verdict"].startswith("THESIS_VALID") else "INVALID"
        design = "VALID_NEEDS_N" if "DESIGN_VALID" in audit["verdict"] else ("BROKEN" if "DESIGN_BROKEN" in audit["verdict"] else "N/A")
        tier = "REJECT"
        if audit["selected"]:
            tier = proposed_tier(audit["selected"][0]["bonf_p"], audit["selected"][0]["verdict"])
        lines.append(
            f"| {strategy} | {thesis} | {design} | {audit['all']['n']} | {best['cell'] if best else 'n/a'} | {audit['verdict']} | {tier} |"
        )
    lines.append("")
    lines.append("## PRIME v2 candidate proposal")
    if result["selected"]:
        lines.append("Deltas to apply to `modules/prime_gate.py` `_PRIMES` list in a separate apply task:")
        for cell in result["selected"]:
            tier = proposed_tier(cell["bonf_p"], cell["verdict"])
            lot = 0.3 if tier == "A" else 0.1
            lines.append(f"- Add `({cell['cell']!r}, {cell['strategy']!r}, {tier!r}, {lot}, {lambda_predicate(cell)})`")
    else:
        lines.append("- No `_PRIMES` deltas recommended. All design-driven v2 cells are REJECT under corrected m_total Bonferroni.")
    lines.append("")
    lines.append("## Next steps")
    if result["selected"]:
        lines.append("- Queue separate apply task `20260518-XXXX-prime-v2-add-candidates` for selected PRIME v2 cells.")
    else:
        lines.append("- NULL result retained. Future re-eval @ shadow N+30d with the same design-driven cell lock.")
        lines.append("- Near-miss cells (N>=10 and uncorrected Fisher p<0.05):")
        if result["near_misses"]:
            for cell in result["near_misses"]:
                m = cell["metrics"]
                lines.append(f"  - {cell['cell']}: N={m['n']} WR={fmt_pct(m['wr'])} Fisher p={m['fisher_p']:.3g} EV={m['ev']:+.2f}p")
        else:
            lines.append("  - None.")
    return "\n".join(lines) + "\n"


def write_cells_csv(result: dict[str, Any], path: Path = CELLS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "strategy",
                "cell",
                "kind",
                "predicate",
                "n",
                "wins",
                "wr",
                "wilson_lo",
                "fisher_p",
                "bonf_p_x_m",
                "fdr_bh_q10",
                "wf",
                "kelly_half",
                "pf",
                "spread_adj_ev",
                "verdict",
                "tier",
            ],
        )
        writer.writeheader()
        for cell in result["measured_cells"]:
            m = cell["metrics"]
            writer.writerow(
                {
                    "strategy": cell["strategy"],
                    "cell": cell["cell"],
                    "kind": cell["kind"],
                    "predicate": cell["predicate"],
                    "n": m["n"],
                    "wins": m["wins"],
                    "wr": f"{m['wr']:.8f}",
                    "wilson_lo": f"{m['wlo']:.8f}",
                    "fisher_p": f"{m['fisher_p']:.12g}",
                    "bonf_p_x_m": f"{cell['bonf_p']:.12g}",
                    "fdr_bh_q10": cell["fdr_q10"],
                    "wf": m["wf"],
                    "kelly_half": f"{m['kelly']:.8f}",
                    "pf": "inf" if math.isinf(m["pf"]) else f"{m['pf']:.8f}",
                    "spread_adj_ev": f"{m['ev']:.8f}",
                    "verdict": cell["verdict"],
                    "tier": cell["tier"],
                }
            )


def write_artifacts(result: dict[str, Any]) -> None:
    report = render_report(result)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    KB_SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    KB_SESSION_PATH.write_text(report, encoding="utf-8")
    write_cells_csv(result)

    append = (
        "\n\n## v2 Shadow Audit Complete ✓\n\n"
        f"2026-05-18 design-driven PRIME v2 shadow audit completed with `tools/prime_v2_shadow_audit.py`.\n\n"
        f"- Hypothesis space: m_total={result['m_total']} (<=30), Bonferroni alpha={result['alpha']:.6f}\n"
        f"- Render rows fetched: {result['fetched_rows']} (shadow={result['shadow_rows']}, WIN/LOSS shadow non-XAU={result['all_eligible_rows']})\n"
        f"- Target strategy rows: {result['strategy_rows']} across 6 locked strategies\n"
        f"- Selected PRIME v2 candidates: {len(result['selected'])}\n"
        f"- Report: `research/prime_v2_audit_2026_05_18.md`\n"
        f"- Cells CSV: `research/prime_v2_audit_cells.csv`\n"
        f"- KB session: `knowledge-base/wiki/sessions/prime-v2-shadow-audit-2026-05-18.md`\n"
    )
    if DECISION_PATH.exists():
        current = DECISION_PATH.read_text(encoding="utf-8")
        marker = "## v2 Shadow Audit Complete ✓"
        if marker in current:
            current = current.split(marker, 1)[0].rstrip()
        DECISION_PATH.write_text(current.rstrip() + append, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=API_URL)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    rows = fetch_rows(args.url)
    result = analyze(rows)
    report = render_report(result)
    print(report)
    if not args.no_write:
        write_artifacts(result)
        print(f"Artifacts written: {REPORT_PATH}, {CELLS_PATH}, {KB_SESSION_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
