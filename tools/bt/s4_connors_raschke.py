#!/usr/bin/env python3
"""S4 Connors-Raschke 80-20 pre-registered BT runner.

Reads local USDJPY M5 parquet cache only. The sensitivity grid and verdict
thresholds are locked as module-level constants before any BT execution.
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
from tools.cell_edge_audit import wilson_lower


PENETRATION_TICKS = [5, 10, 15]
EXIT_METHODS = ["50_trailing", "100_trailing", "fixed_time"]
SESSION_BOUNDARIES = ["NY_close_21UTC", "London_close_16UTC", "H24"]
BONFERRONI_M = 27
BONFERRONI_ALPHA = 0.05
PRIMARY_CELL = {
    "penetration_tick": 10,
    "exit_method": "50_trailing",
    "session_boundary": "NY_close_21UTC",
}
BEV_WR_USDJPY = 0.344
BOOTSTRAP_ITERATIONS = 1000
DEFAULT_SEED = 20260503
CACHE_MIN_ROWS = 900_000
CACHE_MIN_START = "2014-01-31"
CACHE_MIN_END = "2026-04-29"
CATALOG_PATH = Path("/Users/jg-n-012/test/wiki/learning/global-retail-fx-edges-2026-05-03.md")

VERDICT_THRESHOLDS = {
    "A": {
        "n": 200,
        "wilson_lo": 0.45,
        "pf": 1.5,
        "oos_is_pf_ratio": 0.8,
        "bonferroni_p": 0.01,
        "sharpe": 1.0,
        "kelly": 0.10,
    },
    "B": {
        "n": 100,
        "wilson_lo": 0.42,
        "pf": 1.2,
        "oos_is_pf_ratio": 0.6,
        "bonferroni_p": 0.10,
        "sharpe": 0.5,
        "kelly": 0.05,
    },
    "B-marg": {
        "n": 50,
        "wilson_lo": 0.40,
        "pf": 1.0,
        "oos_is_pf_ratio": 0.4,
        "bonferroni_p": 0.20,
        "sharpe": 0.0,
        "kelly": 0.0,
    },
}


class InterventionListMissing(RuntimeError):
    pass


@dataclass(frozen=True)
class SetupDay:
    day: pd.Timestamp
    direction: str
    high: float
    low: float
    open: float
    close: float
    next_day: pd.Timestamp | None = None


@dataclass(frozen=True)
class Trade:
    entry_ts: pd.Timestamp
    exit_ts: pd.Timestamp
    direction: str
    entry_price: float
    exit_price: float
    pnl_pip: float
    pnl_pct: float
    holding_minutes: int
    setup_day: pd.Timestamp
    exit_reason: str


def grid_cells() -> list[dict]:
    return [
        {
            "penetration_tick": tick,
            "exit_method": exit_method,
            "session_boundary": boundary,
        }
        for tick in PENETRATION_TICKS
        for exit_method in EXIT_METHODS
        for boundary in SESSION_BOUNDARIES
    ]


def bonferroni_adjusted_p(p_value: float) -> float:
    return min(1.0, float(p_value) * BONFERRONI_M)


def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out = out.rename(columns={c: c.lower() for c in out.columns})
    missing = {"open", "high", "low", "close"} - set(out.columns)
    if missing:
        raise ValueError(f"OHLC cache missing columns: {sorted(missing)}")
    out.index = pd.to_datetime(out.index, utc=True)
    return out.sort_index()


def verify_cache(df: pd.DataFrame) -> dict:
    start = pd.Timestamp(df.index.min()).tz_convert("UTC")
    end = pd.Timestamp(df.index.max()).tz_convert("UTC")
    rows = len(df)
    if rows < CACHE_MIN_ROWS or str(start.date()) > CACHE_MIN_START or str(end.date()) < CACHE_MIN_END:
        raise RuntimeError(f"CACHE_INSUFFICIENT rows={rows} start={start} end={end}")
    return {"rows": rows, "start": start.isoformat(), "end": end.isoformat()}


def daily_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    df = normalize_ohlcv(df)
    d = df.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"})
    return d.dropna(subset=["open", "high", "low", "close"])


def detect_setups(daily: pd.DataFrame) -> dict[pd.Timestamp, str | None]:
    out: dict[pd.Timestamp, str | None] = {}
    eps = 1e-12
    for day, row in daily.iterrows():
        rng = float(row["high"] - row["low"])
        if rng <= 0:
            out[day] = None
            continue
        open_pct = float((row["open"] - row["low"]) / rng)
        close_pct = float((row["close"] - row["low"]) / rng)
        if open_pct >= 0.80 - eps and close_pct <= 0.20 + eps:
            out[day] = "bearish"
        elif open_pct <= 0.20 + eps and close_pct >= 0.80 - eps:
            out[day] = "bullish"
        else:
            out[day] = None
    return out


def build_setup_days(daily: pd.DataFrame, intervention_dates: set[str]) -> list[SetupDay]:
    labels = detect_setups(daily)
    days = list(daily.index)
    setups: list[SetupDay] = []
    for i, day in enumerate(days[:-1]):
        label = labels.get(day)
        if label is None:
            continue
        row = daily.loc[day]
        next_day = days[i + 1]
        if str(day.date()) in intervention_dates or str(next_day.date()) in intervention_dates:
            continue
        if float(row["close"]) > 158.0:
            continue
        setups.append(
            SetupDay(
                day=day,
                direction="SHORT" if label == "bearish" else "LONG",
                high=float(row["high"]),
                low=float(row["low"]),
                open=float(row["open"]),
                close=float(row["close"]),
                next_day=next_day,
            )
        )
    return setups


def _session_end(day: pd.Timestamp, boundary: str) -> pd.Timestamp:
    start = day.normalize()
    if boundary == "NY_close_21UTC":
        return start + pd.Timedelta(hours=21)
    if boundary == "London_close_16UTC":
        return start + pd.Timedelta(hours=16)
    if boundary == "H24":
        return start + pd.Timedelta(hours=23, minutes=55)
    raise ValueError(f"unknown session_boundary={boundary}")


def simulate_setup_day(
    bars: pd.DataFrame,
    setup: SetupDay,
    penetration_tick: int,
    exit_method: str,
    session_boundary: str,
) -> Trade | None:
    bars = normalize_ohlcv(bars)
    next_day = setup.next_day or (setup.day + pd.Timedelta(days=1))
    end = _session_end(next_day, session_boundary)
    day_bars = bars[(bars.index >= next_day.normalize()) & (bars.index <= end)]
    if day_bars.empty:
        return None

    penetration = penetration_tick * 0.001
    armed = False
    entry_ts = None
    entry_price = None
    for ts, row in day_bars.iterrows():
        if setup.direction == "SHORT":
            if not armed and float(row["low"]) <= setup.low - penetration:
                armed = True
                continue
            if armed and float(row["close"]) >= setup.low:
                entry_ts = ts
                entry_price = float(row["close"])
                break
        else:
            if not armed and float(row["high"]) >= setup.high + penetration:
                armed = True
                continue
            if armed and float(row["close"]) <= setup.high:
                entry_ts = ts
                entry_price = float(row["close"])
                break
    if entry_ts is None or entry_price is None:
        return None

    future = day_bars[day_bars.index > entry_ts]
    if future.empty:
        future = day_bars[day_bars.index == entry_ts]
    exit_ts = future.index[-1]
    exit_price = float(future.iloc[-1]["close"])
    exit_reason = "session_close"
    stop = setup.high + 0.050 if setup.direction == "SHORT" else setup.low - 0.050
    trail_dist = None
    if exit_method == "50_trailing":
        trail_dist = 0.5 * (setup.high - setup.low)
    elif exit_method == "100_trailing":
        trail_dist = setup.high - setup.low
    elif exit_method != "fixed_time":
        raise ValueError(f"unknown exit_method={exit_method}")

    best = entry_price
    for ts, row in future.iterrows():
        close = float(row["close"])
        if setup.direction == "SHORT":
            if float(row["high"]) >= stop:
                exit_ts, exit_price, exit_reason = ts, stop, "stop"
                break
            best = min(best, float(row["low"]))
            if trail_dist is not None and close >= best + trail_dist:
                exit_ts, exit_price, exit_reason = ts, close, f"trail_{50 if exit_method == '50_trailing' else 100}"
                break
        else:
            if float(row["low"]) <= stop:
                exit_ts, exit_price, exit_reason = ts, stop, "stop"
                break
            best = max(best, float(row["high"]))
            if trail_dist is not None and close <= best - trail_dist:
                exit_ts, exit_price, exit_reason = ts, close, f"trail_{50 if exit_method == '50_trailing' else 100}"
                break

    raw = (exit_price - entry_price) / 0.01
    if setup.direction == "SHORT":
        raw *= -1
    holding_minutes = int((exit_ts - entry_ts) / pd.Timedelta(minutes=1))
    return Trade(
        entry_ts=entry_ts,
        exit_ts=exit_ts,
        direction=setup.direction,
        entry_price=entry_price,
        exit_price=exit_price,
        pnl_pip=round(raw, 6),
        pnl_pct=round(raw / 10000, 8),
        holding_minutes=holding_minutes,
        setup_day=setup.day,
        exit_reason=exit_reason,
    )


def profit_factor(pnls: Iterable[float]) -> float:
    vals = list(pnls)
    gross_win = sum(v for v in vals if v > 0)
    gross_loss = abs(sum(v for v in vals if v < 0))
    if gross_loss == 0:
        return float("inf") if gross_win > 0 else 0.0
    return gross_win / gross_loss


def _binomial_one_sided_p(wins: int, n: int, p0: float) -> float:
    if n <= 0:
        return 1.0
    if n <= 1000:
        prob = (1.0 - p0) ** n
        total = 0.0
        for k in range(0, n + 1):
            if k >= wins:
                total += prob
            if k < n:
                prob *= (n - k) / (k + 1) * p0 / (1.0 - p0)
        return max(0.0, min(1.0, total))
    mean = n * p0
    var = n * p0 * (1.0 - p0)
    z = (wins - 0.5 - mean) / math.sqrt(var)
    return 0.5 * math.erfc(z / math.sqrt(2))


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
    eq = 0.0
    peak = 0.0
    dd = 0.0
    for pnl in pnls:
        eq += pnl
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    return dd


def annualized_sharpe_from_daily(daily_pnl: pd.DataFrame) -> float:
    if daily_pnl.empty or len(daily_pnl) < 2:
        return 0.0
    vals = daily_pnl["pnl_pip"].astype(float).to_numpy()
    sd = vals.std(ddof=1)
    if sd == 0:
        return 0.0
    return float(vals.mean() / sd * math.sqrt(252))


def summarize_trades(trades: list[Trade]) -> dict:
    pnls = [t.pnl_pip for t in trades]
    wins = sum(1 for p in pnls if p > 0)
    n = len(pnls)
    wr = wins / n if n else 0.0
    wins_p = [p for p in pnls if p > 0]
    losses_p = [-p for p in pnls if p < 0]
    avg_win = sum(wins_p) / len(wins_p) if wins_p else 0.0
    avg_loss = sum(losses_p) / len(losses_p) if losses_p else 0.0
    kelly = kelly_criterion(wr, avg_win, avg_loss)["full_kelly"]
    p_raw = _binomial_one_sided_p(wins, n, BEV_WR_USDJPY)
    daily = daily_pnl_series(trades)
    wf = walk_forward_50_50(trades)
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
        "kelly": kelly,
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
    trades: list[Trade] = []
    for setup in setups:
        if setup.next_day is None:
            continue
        start = setup.next_day.normalize()
        end = _session_end(setup.next_day, cell["session_boundary"])
        chunk = df[(df.index >= start) & (df.index <= end)]
        trade = simulate_setup_day(
            chunk,
            setup,
            cell["penetration_tick"],
            cell["exit_method"],
            cell["session_boundary"],
        )
        if trade is not None:
            trades.append(trade)
    return trades


def null_bootstrap_primary_pf(df: pd.DataFrame, daily: pd.DataFrame, setups: list[SetupDay], n: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    days = [s.day for s in setups]
    directions = [s.direction for s in setups]
    pfs: list[float] = []
    primary_trades = run_cell(df, setups, PRIMARY_CELL)
    actual_pf = profit_factor(t.pnl_pip for t in primary_trades)
    for _ in range(n):
        shuffled = rng.permutation(directions)
        shuffled_setups: list[SetupDay] = []
        for day, direction in zip(days, shuffled):
            row = daily.loc[day]
            next_idx = list(daily.index).index(day) + 1
            if next_idx >= len(daily.index):
                continue
            shuffled_setups.append(
                SetupDay(
                    day=day,
                    direction=str(direction),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    open=float(row["open"]),
                    close=float(row["close"]),
                    next_day=daily.index[next_idx],
                )
            )
        bt = run_cell(df, shuffled_setups, PRIMARY_CELL)
        pfs.append(profit_factor(t.pnl_pip for t in bt))
    finite = [v for v in pfs if math.isfinite(v)]
    if not finite:
        finite = [0.0]
    actual_cmp = actual_pf if math.isfinite(actual_pf) else max(finite)
    ge = sum(1 for v in finite if v >= actual_cmp)
    le = sum(1 for v in finite if v <= actual_cmp)
    two_sided = min(1.0, 2.0 * min(ge, le) / len(finite))
    return {
        "iterations": n,
        "actual_pf": actual_pf,
        "mean_pf": float(np.mean(finite)),
        "median_pf": float(np.median(finite)),
        "empirical_pf_percentile": float(sum(v <= actual_cmp for v in finite) / len(finite)),
        "two_sided_p": two_sided,
        "distribution": finite,
    }


def cohort_tables(trades: list[Trade]) -> dict:
    if not trades:
        return {"annual": [], "monthly": [], "single_year_gt_50pct": False, "max_year_share": 0.0}
    df = pd.DataFrame({"exit_ts": [t.exit_ts for t in trades], "pnl_pip": [t.pnl_pip for t in trades]})
    df["year"] = df["exit_ts"].dt.year
    df["month"] = df["exit_ts"].dt.strftime("%Y-%m")
    annual = df.groupby("year", as_index=False).agg(pnl_pip=("pnl_pip", "sum"), n=("pnl_pip", "size"))
    monthly = df.groupby("month", as_index=False).agg(pnl_pip=("pnl_pip", "sum"), n=("pnl_pip", "size"))
    total_pos = abs(float(df["pnl_pip"].sum()))
    shares = annual["pnl_pip"].abs() / total_pos if total_pos > 0 else annual["pnl_pip"] * 0
    max_share = float(shares.max()) if len(shares) else 0.0
    return {
        "annual": annual.to_dict(orient="records"),
        "monthly": monthly.to_dict(orient="records"),
        "single_year_gt_50pct": max_share > 0.5,
        "max_year_share": max_share,
    }


def load_intervention_dates(path: Path = CATALOG_PATH) -> set[str]:
    text = path.read_text(encoding="utf-8")
    section = text
    marker = "#### B-2. Connors-Raschke"
    if marker in text:
        section = text[text.index(marker) : text.find("#### B-3.", text.index(marker))]
    dates = sorted(set(re.findall(r"20\d{2}-\d{2}-\d{2}", section)))
    if len(dates) != 8:
        raise InterventionListMissing(
            f"INTERVENTION_LIST_MISSING: expected definitive 8-event list in {path}, found {len(dates)} date(s): {dates}"
        )
    return set(dates)


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
        "# S4 Connors-Raschke 80-20 BT (USDJPY M5)",
        "",
        f"**Status**: {result.get('status')}",
        f"**Rule**: R1 Slow & Strict",
        f"**Bonferroni m**: {BONFERRONI_M}",
        f"**Primary cell**: `{PRIMARY_CELL}`",
        "",
    ]
    if result.get("status") == "INTERVENTION_LIST_MISSING":
        lines += [
            "## Abort",
            "",
            "`INTERVENTION_LIST_MISSING`。指定カタログに definitive 8-event list が無いため、日付を補完せずBTを中止した。",
            "",
            f"Evidence: {result.get('error')}",
            "",
            "Deferred validity #2 fib_reversal LIVE corr: not run.",
            "Deferred validity #4 yfinance broker cross-check: not run.",
            "",
        ]
        path.write_text("\n".join(lines), encoding="utf-8")
        return
    lines += [
        "## Sensitivity Grid",
        "| tick | exit | boundary | N | Wilson_lo | PF | OOS/IS PF | Bonf p | Sharpe | Kelly | Max DD | Verdict |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in result["grid"]:
        s = row["summary"]
        lines.append(
            f"| {row['penetration_tick']} | {row['exit_method']} | {row['session_boundary']} | "
            f"{s['n']} | {s['wilson_lo']:.3f} | {s['pf']:.3f} | {s['oos_is_pf_ratio']:.3f} | "
            f"{s['bonferroni_p']:.4f} | {s['sharpe']:.3f} | {s['kelly']:.3f} | {s['max_dd_pip']:.1f} | {row['verdict']} |"
        )
    p = result["primary"]
    lines += [
        "",
        "## Primary Deep Dive",
        json.dumps(p["summary"], indent=2, ensure_ascii=False, default=_json_default),
        "",
        "## Null Bootstrap",
        json.dumps({k: v for k, v in result["bootstrap"].items() if k != "distribution"}, indent=2, ensure_ascii=False, default=_json_default),
        "",
        "## Time Cohorts",
        f"single_year_gt_50pct={result['cohorts']['single_year_gt_50pct']}, max_year_share={result['cohorts']['max_year_share']:.3f}",
        "",
        "## Scenario Verdict",
        result["scenario_verdict"]["text"],
        "",
        "## Post-hoc Validity Markers",
        "- Validity #2 fib_reversal LIVE correlation: DEFERRED to Claude; use primary trade-list parquet.",
        "- Validity #4 yfinance broker cross-check: DEFERRED to Claude; use primary daily-PnL parquet.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_raw_summary(path: Path, result: dict) -> None:
    primary = result.get("primary", {}).get("summary", {})
    path.write_text(
        "\n".join(
            [
                "# S4 Connors-Raschke Raw Summary",
                "",
                f"status: {result.get('status')}",
                f"primary_verdict: {result.get('primary', {}).get('verdict', 'N/A')}",
                f"primary_n: {primary.get('n', 'N/A')}",
                f"primary_pf: {primary.get('pf', 'N/A')}",
                f"primary_bonferroni_p: {primary.get('bonferroni_p', 'N/A')}",
            ]
        ),
        encoding="utf-8",
    )


def print_dry_run() -> None:
    print("S4 Connors-Raschke 80-20 USDJPY M5 DRY RUN")
    print(f"BONFERRONI_M={BONFERRONI_M} alpha={BONFERRONI_ALPHA}")
    print(f"PRIMARY_CELL={PRIMARY_CELL}")
    print(f"BEV_WR_USDJPY={BEV_WR_USDJPY}")
    print("VERDICT_THRESHOLDS:")
    print(json.dumps(VERDICT_THRESHOLDS, indent=2))
    print("GRID:")
    for cell in grid_cells():
        marker = " PRIMARY" if cell == PRIMARY_CELL else ""
        print(f"- {cell}{marker}")


def scenario_verdict(primary_verdict: str, bootstrap: dict, cohorts: dict) -> dict:
    if primary_verdict == "FAIL" or bootstrap["two_sided_p"] >= 0.05:
        return {"scenario": "C", "text": "Scenario C — primary FAIL OR null bootstrap p >= 0.05. Reject; catalog §B-2 academic-only candidate."}
    if primary_verdict in {"B", "A"} and not cohorts["single_year_gt_50pct"]:
        return {
            "scenario": "A-pending",
            "text": "A-pending — post-hoc Validity #2 (fib_reversal LIVE corr) + #4 (yfinance cross-check) required for final LOCK.",
        }
    return {"scenario": "B", "text": "Scenario B — B-marginal or cohort concentration warning. Hold; recommend Wave 4 grid expansion."}


def run_bt(args: argparse.Namespace) -> int:
    output_prefix = Path(args.output_prefix)
    report = Path(args.report)
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    try:
        df = normalize_ohlcv(pd.read_parquet(args.cache))
        cache_info = verify_cache(df)
        intervention_dates = load_intervention_dates(CATALOG_PATH)
    except InterventionListMissing as exc:
        result = {"status": "INTERVENTION_LIST_MISSING", "error": str(exc), "bonferroni_m": BONFERRONI_M}
        write_markdown_report(report, result)
        (output_prefix.with_suffix(".json")).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
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
        row = {**cell, "summary": summary, "verdict": verdict}
        grid.append(row)
        if cell == PRIMARY_CELL:
            primary_trades = trades
            primary_summary = summary
            primary_verdict = verdict

    bootstrap = null_bootstrap_primary_pf(df, daily, setups, BOOTSTRAP_ITERATIONS, DEFAULT_SEED)
    cohorts = cohort_tables(primary_trades)
    scenario = scenario_verdict(primary_verdict, bootstrap, cohorts)
    result = {
        "status": "OK",
        "cache": cache_info,
        "bonferroni_m": BONFERRONI_M,
        "bev_wr_usdjpy": BEV_WR_USDJPY,
        "primary_cell": PRIMARY_CELL,
        "grid": grid,
        "primary": {
            "summary": primary_summary,
            "verdict": primary_verdict,
            "trades": [asdict(t) for t in primary_trades],
        },
        "bootstrap": bootstrap,
        "cohorts": cohorts,
        "scenario_verdict": scenario,
    }
    (output_prefix.with_suffix(".json")).write_text(json.dumps(result, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")
    write_raw_summary(output_prefix.with_suffix(".md"), result)
    write_markdown_report(report, result)
    trade_df = pd.DataFrame([asdict(t) for t in primary_trades])
    trade_df = trade_df.rename(
        columns={
            "entry_ts": "entry_ts_utc",
            "exit_ts": "exit_ts_utc",
            "setup_day": "setup_day_utc",
        }
    )
    Path("knowledge-base/raw/bt-results").mkdir(parents=True, exist_ok=True)
    trade_df.to_parquet("knowledge-base/raw/bt-results/s4-primary-trade-list-2026-05-03.parquet", index=False)
    daily_pnl_series(primary_trades).to_parquet("knowledge-base/raw/bt-results/s4-primary-daily-pnl-2026-05-03.parquet", index=False)
    print(f"OK wrote {output_prefix}.json/.md and {report}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--cache", default="data/cache/massive/USD_JPY_5m_2014_2026.parquet")
    parser.add_argument("--output-prefix", default="knowledge-base/raw/bt-results/s4-connors-raschke-2026-05-03")
    parser.add_argument("--report", default="knowledge-base/wiki/learning/s4-connors-raschke-bt-2026-05-03.md")
    args = parser.parse_args()
    if args.dry_run:
        print_dry_run()
        return 0
    return run_bt(args)


if __name__ == "__main__":
    raise SystemExit(main())
