#!/usr/bin/env python3
"""B3 Turtle Soup pre-registered BT runner.

Reads local USDJPY M5 parquet cache only. Grid axes, primary cell, thresholds,
Bonferroni denominator, and BEV are locked as module-level constants before BT.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from modules.stats_utils import kelly_criterion
from tools.bt import s4_connors_raschke as s4
from tools.cell_edge_audit import wilson_lower


FAILURE_WINDOWS = [6, 12, 24]
EXIT_METHODS = ["50_trailing", "100_trailing", "fixed_time"]
SESSION_BOUNDARIES = ["NY_close_21UTC", "London_close_16UTC", "H24"]
BONFERRONI_M = 27
BONFERRONI_ALPHA = 0.05
PRIMARY_CELL = {
    "failure_window": 12,
    "exit_method": "100_trailing",
    "session_boundary": "London_close_16UTC",
}
BEV_WR_USDJPY = 0.344
BOOTSTRAP_ITERATIONS = 1000
DEFAULT_SEED = 20260503
DONCHIAN_DAYS = 20
PIP = 0.01
FAILURE_BUFFER_PIP = 5
FAILURE_BUFFER = FAILURE_BUFFER_PIP * PIP
INTERVENTION_REGIME_OFF = 158.0
CACHE_MIN_ROWS = 900_000
CACHE_MIN_START = "2014-01-31"
CACHE_MIN_END = "2026-04-29"
CATALOG_CANDIDATES = [
    Path("knowledge-base/wiki/learning/global-retail-fx-edges-2026-05-03.md"),
    Path("/Users/jg-n-012/test/wiki/learning/global-retail-fx-edges-2026-05-03.md"),
]

VERDICT_THRESHOLDS = {
    "A": {"n": 200, "wilson_lo": 0.45, "pf": 1.5, "oos_is_pf_ratio": 0.8, "bonferroni_p": 0.01, "sharpe": 1.0, "kelly": 0.10},
    "B": {"n": 100, "wilson_lo": 0.42, "pf": 1.2, "oos_is_pf_ratio": 0.6, "bonferroni_p": 0.10, "sharpe": 0.5, "kelly": 0.05},
    "B-marg": {"n": 50, "wilson_lo": 0.40, "pf": 1.0, "oos_is_pf_ratio": 0.4, "bonferroni_p": 0.20, "sharpe": 0.0, "kelly": 0.0},
}


class InterventionListMissing(RuntimeError):
    pass


@dataclass(frozen=True)
class SetupDay:
    day: pd.Timestamp
    donchian_high: float
    donchian_low: float
    donchian_range: float
    prev_close: float


@dataclass(frozen=True)
class Trade:
    entry_ts: pd.Timestamp
    exit_ts: pd.Timestamp
    direction: str
    breakout_ts: pd.Timestamp
    breakout_price: float
    entry_price: float
    exit_price: float
    stop_price: float
    pnl_pip: float
    pnl_pct: float
    holding_minutes: int
    setup_day: pd.Timestamp
    exit_reason: str


def grid_cells() -> list[dict]:
    return [
        {"failure_window": window, "exit_method": exit_method, "session_boundary": boundary}
        for window in FAILURE_WINDOWS
        for exit_method in EXIT_METHODS
        for boundary in SESSION_BOUNDARIES
    ]


def bonferroni_adjusted_p(p_value: float) -> float:
    return min(1.0, float(p_value) * BONFERRONI_M)


def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    return s4.normalize_ohlcv(df)


def verify_cache(df: pd.DataFrame) -> dict:
    start = pd.Timestamp(df.index.min()).tz_convert("UTC")
    end = pd.Timestamp(df.index.max()).tz_convert("UTC")
    rows = len(df)
    if rows < CACHE_MIN_ROWS or str(start.date()) > CACHE_MIN_START or str(end.date()) < CACHE_MIN_END:
        raise RuntimeError(f"CACHE_INSUFFICIENT rows={rows} start={start} end={end}")
    return {"rows": rows, "start": start.isoformat(), "end": end.isoformat()}


def daily_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    return s4.daily_ohlc(df)


def load_intervention_dates(candidates: Iterable[Path] = CATALOG_CANDIDATES) -> tuple[set[str], Path]:
    checked: list[str] = []
    for path in candidates:
        checked.append(str(path))
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        section = text
        marker = "#### B-2. Connors-Raschke"
        if marker in text:
            start = text.index(marker)
            end = text.find("#### B-3.", start)
            section = text[start:] if end == -1 else text[start:end]
        dates = sorted(set(re.findall(r"20\d{2}-\d{2}-\d{2}", section)))
        if len(dates) == 8:
            return set(dates), path
    raise InterventionListMissing(f"INTERVENTION_LIST_MISSING: expected definitive 8-event list, checked={checked}")


def build_setup_days(daily: pd.DataFrame, intervention_dates: set[str]) -> list[SetupDay]:
    days = list(daily.index)
    setups: list[SetupDay] = []
    for i in range(DONCHIAN_DAYS, len(days)):
        day = days[i]
        prev_day = days[i - 1]
        if str(day.date()) in intervention_dates or str(prev_day.date()) in intervention_dates:
            continue
        prev_close = float(daily.loc[prev_day, "close"])
        if prev_close >= INTERVENTION_REGIME_OFF:
            continue
        lookback = daily.iloc[i - DONCHIAN_DAYS : i]
        hi = float(lookback["high"].max())
        lo = float(lookback["low"].min())
        if hi <= lo:
            continue
        setups.append(SetupDay(day=day, donchian_high=hi, donchian_low=lo, donchian_range=hi - lo, prev_close=prev_close))
    return setups


def _session_end(day: pd.Timestamp, boundary: str) -> pd.Timestamp:
    return s4._session_end(day, boundary)


def simulate_setup_day(bars: pd.DataFrame, setup: SetupDay, failure_window: int, exit_method: str, session_boundary: str) -> Trade | None:
    if not {"open", "high", "low", "close"}.issubset(bars.columns):
        bars = normalize_ohlcv(bars)
    end = _session_end(setup.day, session_boundary)
    if not bars.empty and bars.index[0] >= setup.day.normalize() and bars.index[-1] <= end:
        day_bars = bars
    else:
        day_bars = bars[(bars.index >= setup.day.normalize()) & (bars.index <= end)]
    if day_bars.empty:
        return None

    idx = day_bars.index
    highs = day_bars["high"].to_numpy(dtype=float)
    lows = day_bars["low"].to_numpy(dtype=float)
    closes = day_bars["close"].to_numpy(dtype=float)
    breakout_idx = None
    direction = None
    breakout_price = None
    for i in range(len(day_bars)):
        if highs[i] > setup.donchian_high:
            breakout_idx, direction, breakout_price = i, "SHORT", setup.donchian_high
            break
        if lows[i] < setup.donchian_low:
            breakout_idx, direction, breakout_price = i, "LONG", setup.donchian_low
            break
    if breakout_idx is None or direction is None or breakout_price is None:
        return None

    breakout_ts = idx[breakout_idx]
    entry_ts = None
    entry_price = None
    for i in range(breakout_idx + 1, min(len(day_bars), breakout_idx + 1 + failure_window)):
        close = closes[i]
        if direction == "SHORT" and close <= setup.donchian_high - FAILURE_BUFFER:
            entry_ts, entry_price = idx[i], close
            break
        if direction == "LONG" and close >= setup.donchian_low + FAILURE_BUFFER:
            entry_ts, entry_price = idx[i], close
            break
    if entry_ts is None or entry_price is None:
        return None

    if direction == "SHORT":
        stop = highs[breakout_idx] + FAILURE_BUFFER
    else:
        stop = lows[breakout_idx] - FAILURE_BUFFER

    entry_pos = int(day_bars.index.get_loc(entry_ts))
    start_pos = min(entry_pos + 1, len(day_bars) - 1)
    exit_pos = len(day_bars) - 1
    exit_ts = idx[exit_pos]
    exit_price = float(closes[exit_pos])
    exit_reason = "session_close"
    trail_dist = None
    if exit_method == "50_trailing":
        trail_dist = 0.5 * setup.donchian_range
    elif exit_method == "100_trailing":
        trail_dist = setup.donchian_range
    elif exit_method != "fixed_time":
        raise ValueError(f"unknown exit_method={exit_method}")

    best = entry_price
    for i in range(start_pos, len(day_bars)):
        close = closes[i]
        if direction == "SHORT":
            if highs[i] >= stop:
                exit_ts, exit_price, exit_reason = idx[i], stop, "stop"
                break
            best = min(best, lows[i])
            if trail_dist is not None and close >= best + trail_dist:
                exit_ts, exit_price, exit_reason = idx[i], close, f"trail_{50 if exit_method == '50_trailing' else 100}"
                break
        else:
            if lows[i] <= stop:
                exit_ts, exit_price, exit_reason = idx[i], stop, "stop"
                break
            best = max(best, highs[i])
            if trail_dist is not None and close <= best - trail_dist:
                exit_ts, exit_price, exit_reason = idx[i], close, f"trail_{50 if exit_method == '50_trailing' else 100}"
                break

    pnl = (exit_price - entry_price) / PIP
    if direction == "SHORT":
        pnl *= -1
    return Trade(
        entry_ts=entry_ts,
        exit_ts=exit_ts,
        direction=direction,
        breakout_ts=breakout_ts,
        breakout_price=float(breakout_price),
        entry_price=float(entry_price),
        exit_price=float(exit_price),
        stop_price=float(stop),
        pnl_pip=round(float(pnl), 6),
        pnl_pct=round(float(pnl) / 10000, 8),
        holding_minutes=int((exit_ts - entry_ts) / pd.Timedelta(minutes=1)),
        setup_day=setup.day,
        exit_reason=exit_reason,
    )


def profit_factor(pnls: Iterable[float]) -> float:
    return s4.profit_factor(pnls)


def walk_forward_50_50(trades: list[Trade]) -> dict:
    ordered = sorted(trades, key=lambda t: t.entry_ts)
    mid = len(ordered) // 2
    is_trades = ordered[:mid]
    oos_trades = ordered[mid:]
    is_pf = profit_factor(t.pnl_pip for t in is_trades)
    oos_pf = profit_factor(t.pnl_pip for t in oos_trades)
    if is_pf in (0.0, float("inf")):
        ratio = 0.0 if oos_pf == 0.0 else (float("inf") if is_pf == 0.0 else 1.0)
    else:
        ratio = oos_pf / is_pf
    return {"is_n": len(is_trades), "oos_n": len(oos_trades), "is_pf": is_pf, "oos_pf": oos_pf, "oos_is_pf_ratio": ratio}


def daily_pnl_series(trades: list[Trade]) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame(columns=["date", "pnl_pip", "trade_count"])
    df = pd.DataFrame({"date": [t.exit_ts.date().isoformat() for t in trades], "pnl_pip": [t.pnl_pip for t in trades]})
    return df.groupby("date", as_index=False).agg(pnl_pip=("pnl_pip", "sum"), trade_count=("pnl_pip", "size"))


def max_drawdown(pnls: list[float]) -> float:
    return s4.max_drawdown(pnls)


def annualized_sharpe_from_daily(daily_pnl: pd.DataFrame) -> float:
    return s4.annualized_sharpe_from_daily(daily_pnl)


def _binomial_one_sided_p(wins: int, n: int, p0: float) -> float:
    return s4._binomial_one_sided_p(wins, n, p0)


def summarize_trades(trades: list[Trade]) -> dict:
    pnls = [t.pnl_pip for t in trades]
    wins = sum(1 for p in pnls if p > 0)
    n = len(pnls)
    wr = wins / n if n else 0.0
    wins_p = [p for p in pnls if p > 0]
    losses_p = [-p for p in pnls if p < 0]
    avg_win = sum(wins_p) / len(wins_p) if wins_p else 0.0
    avg_loss = sum(losses_p) / len(losses_p) if losses_p else 0.0
    wf = walk_forward_50_50(trades)
    p_raw = _binomial_one_sided_p(wins, n, BEV_WR_USDJPY)
    daily = daily_pnl_series(trades)
    return {
        "n": n,
        "wins": wins,
        "wr": wr,
        "wilson_lo": wilson_lower(wins, n),
        "pf": profit_factor(pnls),
        "oos_is_pf_ratio": wf["oos_is_pf_ratio"],
        "is_pf": wf["is_pf"],
        "oos_pf": wf["oos_pf"],
        "bonferroni_p": bonferroni_adjusted_p(p_raw),
        "raw_p": p_raw,
        "sharpe": annualized_sharpe_from_daily(daily),
        "kelly": kelly_criterion(wr, avg_win, avg_loss)["full_kelly"],
        "max_dd_pip": max_drawdown(pnls),
        "total_pip": sum(pnls),
    }


def verdict_for_summary(summary: dict) -> str:
    for tier in ("A", "B", "B-marg"):
        t = VERDICT_THRESHOLDS[tier]
        if (
            summary["n"] >= t["n"]
            and summary["wilson_lo"] > t["wilson_lo"]
            and summary["pf"] > t["pf"]
            and summary["oos_is_pf_ratio"] > t["oos_is_pf_ratio"]
            and summary["bonferroni_p"] < t["bonferroni_p"]
            and summary["sharpe"] > t["sharpe"]
            and summary["kelly"] > t["kelly"]
        ):
            return tier
    return "FAIL"


def run_cell(df: pd.DataFrame, setups: list[SetupDay], cell: dict) -> list[Trade]:
    chunks = build_day_chunks(df, setups, cell["session_boundary"])
    return run_cell_with_chunks(chunks, setups, cell)


def build_day_chunks(df: pd.DataFrame, setups: list[SetupDay], session_boundary: str) -> dict[pd.Timestamp, pd.DataFrame]:
    needed = {setup.day.normalize() for setup in setups}
    chunks: dict[pd.Timestamp, pd.DataFrame] = {}
    for day, chunk in df.groupby(df.index.normalize(), sort=False):
        if day in needed:
            chunks[day] = chunk
    return chunks


def run_cell_with_chunks(chunks: dict[pd.Timestamp, pd.DataFrame], setups: list[SetupDay], cell: dict) -> list[Trade]:
    trades: list[Trade] = []
    for setup in setups:
        chunk = chunks.get(setup.day)
        if chunk is None:
            continue
        trade = simulate_setup_day(chunk, setup, cell["failure_window"], cell["exit_method"], cell["session_boundary"])
        if trade is not None:
            trades.append(trade)
    return trades


def detect_primary_label(chunks: dict[pd.Timestamp, pd.DataFrame], setup: SetupDay) -> str:
    trade = simulate_setup_day(
        chunks[setup.day],
        setup,
        PRIMARY_CELL["failure_window"],
        PRIMARY_CELL["exit_method"],
        PRIMARY_CELL["session_boundary"],
    )
    if trade is None:
        return "none"
    return "up_failed" if trade.direction == "SHORT" else "down_failed"


def simulate_forced_label(
    bars: pd.DataFrame,
    setup: SetupDay,
    label: str,
    failure_window: int,
    exit_method: str,
    session_boundary: str,
) -> Trade | None:
    if label == "none":
        return None
    if not {"open", "high", "low", "close"}.issubset(bars.columns):
        bars = normalize_ohlcv(bars)
    end = _session_end(setup.day, session_boundary)
    if not bars.empty and bars.index[0] >= setup.day.normalize() and bars.index[-1] <= end:
        day_bars = bars
    else:
        day_bars = bars[(bars.index >= setup.day.normalize()) & (bars.index <= end)]
    if day_bars.empty:
        return None

    want_short = label == "up_failed"
    breakout_idx = None
    highs = day_bars["high"].to_numpy(dtype=float)
    lows = day_bars["low"].to_numpy(dtype=float)
    for i in range(len(day_bars)):
        if want_short and highs[i] > setup.donchian_high:
            breakout_idx = i
            break
        if not want_short and lows[i] < setup.donchian_low:
            breakout_idx = i
            break
    if breakout_idx is None:
        return None

    forced_setup = setup
    # Reuse the normal simulator after masking away the opposite breakout side
    # before the selected breakout. This keeps exit semantics identical.
    masked = day_bars.copy()
    pre_idx = list(day_bars.index[:breakout_idx])
    if pre_idx:
        if want_short:
            masked.loc[pre_idx, "low"] = np.maximum(masked.loc[pre_idx, "low"].to_numpy(), setup.donchian_low)
        else:
            masked.loc[pre_idx, "high"] = np.minimum(masked.loc[pre_idx, "high"].to_numpy(), setup.donchian_high)
    return simulate_setup_day(masked, forced_setup, failure_window, exit_method, session_boundary)


def null_bootstrap_primary_pf(df: pd.DataFrame, setups: list[SetupDay], n: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    chunks = build_day_chunks(df, setups, PRIMARY_CELL["session_boundary"])
    labels = [detect_primary_label(chunks, setup) for setup in setups]
    primary_trades = run_cell_with_chunks(chunks, setups, PRIMARY_CELL)
    actual_pf = profit_factor(t.pnl_pip for t in primary_trades)
    forced_pnls: dict[str, list[float | None]] = {"up_failed": [], "down_failed": [], "none": []}
    for setup in setups:
        for label in ("up_failed", "down_failed"):
            trade = simulate_forced_label(
                chunks[setup.day],
                setup,
                label,
                PRIMARY_CELL["failure_window"],
                PRIMARY_CELL["exit_method"],
                PRIMARY_CELL["session_boundary"],
            )
            forced_pnls[label].append(None if trade is None else trade.pnl_pip)
        forced_pnls["none"].append(None)
    pfs: list[float] = []
    for _ in range(n):
        shuffled = rng.permutation(labels)
        pnls = [forced_pnls[str(label)][i] for i, label in enumerate(shuffled)]
        pfs.append(profit_factor(p for p in pnls if p is not None))
    finite = [v for v in pfs if math.isfinite(v)] or [0.0]
    actual_cmp = actual_pf if math.isfinite(actual_pf) else max(finite)
    ge = sum(1 for v in finite if v >= actual_cmp)
    le = sum(1 for v in finite if v <= actual_cmp)
    return {
        "iterations": n,
        "actual_pf": actual_pf,
        "mean_pf": float(np.mean(finite)),
        "median_pf": float(np.median(finite)),
        "empirical_pf_percentile": float(sum(v <= actual_cmp for v in finite) / len(finite)),
        "two_sided_p": min(1.0, 2.0 * min(ge, le) / len(finite)),
        "distribution": finite,
    }


def cohort_tables(trades: list[Trade]) -> dict:
    if not trades:
        return {"annual": [], "monthly": [], "cohort_concentrated": False, "max_year_share": 0.0}
    df = pd.DataFrame({"exit_ts": [t.exit_ts for t in trades], "pnl_pip": [t.pnl_pip for t in trades]})
    df["year"] = df["exit_ts"].dt.year
    df["month"] = df["exit_ts"].dt.strftime("%Y-%m")
    annual = df.groupby("year", as_index=False).agg(pnl_pip=("pnl_pip", "sum"), n=("pnl_pip", "size"))
    monthly = df.groupby("month", as_index=False).agg(pnl_pip=("pnl_pip", "sum"), n=("pnl_pip", "size"))
    total = abs(float(df["pnl_pip"].sum()))
    shares = annual["pnl_pip"].abs() / total if total > 0 else annual["pnl_pip"] * 0
    max_share = float(shares.max()) if len(shares) else 0.0
    return {
        "annual": annual.to_dict(orient="records"),
        "monthly": monthly.to_dict(orient="records"),
        "cohort_concentrated": max_share >= 0.50,
        "max_year_share": max_share,
    }


def scenario_verdict(primary_verdict: str, bootstrap: dict, cohorts: dict) -> dict:
    if primary_verdict == "FAIL" or bootstrap["two_sided_p"] >= 0.05 or cohorts["max_year_share"] >= 0.70:
        return {"scenario": "C", "text": "Scenario C — primary FAIL OR null bootstrap p>=0.05 OR max_year_share>=0.70. REJECT; catalog §B-3 academic-only candidate."}
    if primary_verdict in {"B", "A"} and bootstrap["two_sided_p"] < 0.05 and not cohorts["cohort_concentrated"]:
        return {"scenario": "A-pending", "text": "A-pending — post-hoc D/E/F required before final LOCK."}
    return {"scenario": "B", "text": "Scenario B — B-marginal or cohort_concentrated flag. Hold for Wave 4."}


def _json_default(obj):
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    if isinstance(obj, float) and math.isinf(obj):
        return "inf"
    return str(obj)


def write_markdown_report(path: Path, result: dict) -> None:
    lines = [
        "# B3 Turtle Soup BT (USDJPY M5)",
        "",
        f"**Status**: {result.get('status')}",
        "**Rule**: R1 Slow & Strict",
        f"**Bonferroni m**: {BONFERRONI_M}",
        f"**Primary cell**: `{PRIMARY_CELL}`",
        f"**Catalog source**: `{result.get('catalog_source', 'N/A')}`",
        "",
        "## Strategy Spec",
        f"- Donchian: prev {DONCHIAN_DAYS} trading days high/low.",
        f"- Failure trigger: close back through breakout level by {FAILURE_BUFFER_PIP} pip within `failure_window` M5 bars.",
        "- Filters: prev_close < 158.000 and 8 BoJ intervention dates from catalog only. No HMM/MA/ATR gate.",
        "",
    ]
    if result.get("status") == "INTERVENTION_LIST_MISSING":
        lines += ["## Abort", "", "`INTERVENTION_LIST_MISSING`。catalog §B-2 exact 8-event list が取得できないため中止。", "", f"Evidence: {result.get('error')}"]
        path.write_text("\n".join(lines), encoding="utf-8")
        return
    if result.get("status") == "CACHE_INSUFFICIENT":
        lines += ["## Abort", "", "`CACHE_INSUFFICIENT`。required cache sanity を満たさないため中止。", "", f"Evidence: {result.get('error')}"]
        path.write_text("\n".join(lines), encoding="utf-8")
        return
    lines += [
        "## Sensitivity Grid",
        "| failure_window | exit | boundary | N | Wilson_lo | PF | OOS/IS PF | Bonf p | Sharpe | Kelly | Max DD | Total pip | Verdict |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in result["grid"]:
        s = row["summary"]
        lines.append(
            f"| {row['failure_window']} | {row['exit_method']} | {row['session_boundary']} | {s['n']} | {s['wilson_lo']:.3f} | "
            f"{s['pf']:.3f} | {s['oos_is_pf_ratio']:.3f} | {s['bonferroni_p']:.4f} | {s['sharpe']:.3f} | "
            f"{s['kelly']:.3f} | {s['max_dd_pip']:.1f} | {s['total_pip']:.1f} | {row['verdict']} |"
        )
    p = result["primary"]
    boot = {k: v for k, v in result["bootstrap"].items() if k != "distribution"}
    lines += [
        "",
        "## Primary Deep Dive",
        json.dumps(p["summary"], indent=2, ensure_ascii=False, default=_json_default),
        "",
        "## Null Bootstrap",
        json.dumps(boot, indent=2, ensure_ascii=False, default=_json_default),
        "",
        "## Time Cohorts",
        f"max_year_share={result['cohorts']['max_year_share']:.3f}, cohort_concentrated={result['cohorts']['cohort_concentrated']}",
        "",
        "| year | pnl_pip | n |",
        "|---:|---:|---:|",
    ]
    for row in result["cohorts"]["annual"]:
        lines.append(f"| {int(row['year'])} | {row['pnl_pip']:.1f} | {int(row['n'])} |")
    lines += [
        "",
        "### Monthly Heatmap Input",
        "| month | pnl_pip | n |",
        "|---|---:|---:|",
    ]
    for row in result["cohorts"]["monthly"]:
        lines.append(f"| {row['month']} | {row['pnl_pip']:.1f} | {int(row['n'])} |")
    lines += [
        "",
        "## Scenario Verdict",
        result["scenario_verdict"]["text"],
        "",
        "## Deferred Validity Markers",
        "- D S2 Turtle anti-correlation: DEFERRED to Claude; use primary trade-list and daily-PnL parquet.",
        "- E fib_reversal LIVE corr: DEFERRED to Claude/Render.",
        "- F yfinance broker cross-check: DEFERRED to Claude.",
        "",
        "## Rejected Alternative Variables",
        "- failure_window expansion beyond 24 bars requires fresh pre-registration.",
        "- ATR-based failure buffer would be a new strategy definition.",
        "- Pair extension to GBPJPY requires full 12-year M5 cache.",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_raw_summary(path: Path, result: dict) -> None:
    primary = result.get("primary", {}).get("summary", {})
    lines = [
        "# B3 Turtle Soup Raw Summary",
        "",
        f"status: {result.get('status')}",
        f"primary_verdict: {result.get('primary', {}).get('verdict', 'N/A')}",
        f"primary_n: {primary.get('n', 'N/A')}",
        f"primary_pf: {primary.get('pf', 'N/A')}",
        f"primary_bonferroni_p: {primary.get('bonferroni_p', 'N/A')}",
        f"scenario: {result.get('scenario_verdict', {}).get('scenario', 'N/A')}",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def print_dry_run() -> None:
    print("B3 Turtle Soup USDJPY M5 DRY RUN")
    print(f"BONFERRONI_M={BONFERRONI_M} alpha={BONFERRONI_ALPHA}")
    print(f"PRIMARY_CELL={PRIMARY_CELL}")
    print(f"BEV_WR_USDJPY={BEV_WR_USDJPY}")
    print(f"DONCHIAN_DAYS={DONCHIAN_DAYS} FAILURE_BUFFER_PIP={FAILURE_BUFFER_PIP}")
    print("VERDICT_THRESHOLDS:")
    print(json.dumps(VERDICT_THRESHOLDS, indent=2))
    print("GRID:")
    for cell in grid_cells():
        marker = " PRIMARY" if cell == PRIMARY_CELL else ""
        print(f"- {cell}{marker}")


def run_bt(args: argparse.Namespace) -> int:
    output_prefix = Path(args.output_prefix)
    report = Path(args.report)
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    try:
        df = normalize_ohlcv(pd.read_parquet(args.cache))
        cache_info = verify_cache(df)
    except RuntimeError as exc:
        if "CACHE_INSUFFICIENT" not in str(exc):
            raise
        result = {"status": "CACHE_INSUFFICIENT", "error": str(exc), "bonferroni_m": BONFERRONI_M}
        write_markdown_report(report, result)
        output_prefix.with_suffix(".json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        write_raw_summary(output_prefix.with_suffix(".md"), result)
        print(str(exc))
        return 2
    try:
        intervention_dates, catalog_source = load_intervention_dates()
    except InterventionListMissing as exc:
        result = {"status": "INTERVENTION_LIST_MISSING", "error": str(exc), "bonferroni_m": BONFERRONI_M}
        write_markdown_report(report, result)
        output_prefix.with_suffix(".json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        write_raw_summary(output_prefix.with_suffix(".md"), result)
        print(str(exc))
        return 2

    daily = daily_ohlc(df)
    setups = build_setup_days(daily, intervention_dates)
    grid = []
    primary_trades: list[Trade] = []
    primary_summary = {}
    primary_verdict = "FAIL"
    for cell in grid_cells():
        trades = run_cell(df, setups, cell)
        summary = summarize_trades(trades)
        verdict = verdict_for_summary(summary)
        grid.append({**cell, "summary": summary, "verdict": verdict})
        if cell == PRIMARY_CELL:
            primary_trades = trades
            primary_summary = summary
            primary_verdict = verdict

    bootstrap = null_bootstrap_primary_pf(df, setups, BOOTSTRAP_ITERATIONS, DEFAULT_SEED)
    cohorts = cohort_tables(primary_trades)
    scenario = scenario_verdict(primary_verdict, bootstrap, cohorts)
    result = {
        "status": "OK",
        "cache": cache_info,
        "catalog_source": str(catalog_source),
        "intervention_dates": sorted(intervention_dates),
        "bonferroni_m": BONFERRONI_M,
        "bev_wr_usdjpy": BEV_WR_USDJPY,
        "primary_cell": PRIMARY_CELL,
        "grid": grid,
        "primary": {"summary": primary_summary, "verdict": primary_verdict, "trades": [asdict(t) for t in primary_trades]},
        "bootstrap": bootstrap,
        "cohorts": cohorts,
        "scenario_verdict": scenario,
    }
    output_prefix.with_suffix(".json").write_text(json.dumps(result, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")
    write_raw_summary(output_prefix.with_suffix(".md"), result)
    write_markdown_report(report, result)
    trade_df = pd.DataFrame([asdict(t) for t in primary_trades])
    if not trade_df.empty:
        trade_df = trade_df.rename(columns={"entry_ts": "entry_ts_utc", "exit_ts": "exit_ts_utc", "breakout_ts": "breakout_ts_utc", "setup_day": "setup_day_utc"})
    trade_path = output_prefix.parent / "b3-turtle-soup-primary-trade-list-2026-05-03.parquet"
    pnl_path = output_prefix.parent / "b3-turtle-soup-primary-daily-pnl-2026-05-03.parquet"
    trade_df.to_parquet(trade_path, index=False)
    daily_pnl_series(primary_trades).to_parquet(pnl_path, index=False)
    print(f"OK wrote {output_prefix}.json/.md, {report}, {trade_path}, {pnl_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--cache", default="data/cache/massive/USD_JPY_5m_2014_2026.parquet")
    parser.add_argument("--output-prefix", default="knowledge-base/raw/bt-results/b3-turtle-soup-2026-05-03")
    parser.add_argument("--report", default="knowledge-base/wiki/learning/b3-turtle-soup-bt-2026-05-03.md")
    args = parser.parse_args()
    if args.dry_run:
        print_dry_run()
        return 0
    return run_bt(args)


if __name__ == "__main__":
    raise SystemExit(main())
