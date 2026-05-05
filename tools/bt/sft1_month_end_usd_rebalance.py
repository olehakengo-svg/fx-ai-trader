#!/usr/bin/env python3
"""SFT-1A month-end USD rebalance literal BT.

This module also holds the small shared harness used by the three SFT-1
research-only runners. It does not import or modify production strategies.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from modules.stats_utils import kelly_criterion
from tools.audit.neighborhood_stability import compute_neighborhood_stability
from tools.cell_edge_audit import wilson_lower
from tools.data.build_structural_events import build_structural_events


BT_START = "2014-01-01"
BT_END = "2026-04-30"
RESULT_DATE = "2026-05-04"
BONFERRONI_M = 3
BOOTSTRAP_ITERATIONS = 1000
DEFAULT_SEED = 20260504
CALENDAR_PATH = Path("data/calendar/structural_events.parquet")
RAW_DIR = Path("knowledge-base/raw/bt-results")
REQUIRED_SPEC_DOCS = [
    "knowledge-base/wiki/decisions/structural-flow-tier-2026-05-04.md",
    "knowledge-base/wiki/lessons/feedback_partial_quant_trap.md",
    "knowledge-base/wiki/lessons/feedback_label_empirical_audit.md",
]
INTERVENTION_DATES = {
    "2022-09-22",
    "2022-10-21",
    "2022-10-24",
    "2024-04-29",
    "2024-05-01",
}

PAIR_FILES = {
    "USDJPY": ["data/cache/massive/USD_JPY_5m.parquet", "data/cache/massive/USD_JPY_5m_2014_2026.parquet"],
    "EURUSD": ["data/cache/massive/EUR_USD_5m.parquet", "data/cache/extended/EUR_USD_5m.parquet"],
    "GBPUSD": ["data/cache/massive/GBP_USD_5m.parquet", "data/cache/extended/GBP_USD_5m.parquet"],
}
PIP_SIZE = {"USDJPY": 0.01, "EURUSD": 0.0001, "GBPUSD": 0.0001}
SPREAD_PIP = {"USDJPY": 1.0, "EURUSD": 0.8, "GBPUSD": 0.9}

MONTH_GRID = {
    "entry_offset_min": [-60, -30, 0],
    "exit_min": [30, 60, 120],
}
PRIMARY_CELL = {"entry_offset_min": -30, "exit_min": 60}
PRIMARY_PAIRS = ["USDJPY", "EURUSD", "GBPUSD"]
PAIR_DIRECTIONS = {"USDJPY": "SHORT", "EURUSD": "LONG", "GBPUSD": "LONG"}


@dataclass(frozen=True)
class Trade:
    strategy: str
    pair: str
    event_date: str
    entry_ts_utc: pd.Timestamp
    exit_ts_utc: pd.Timestamp
    direction: str
    entry_price: float
    exit_price: float
    raw_pnl_pip: float
    spread_pip: float
    pnl_pip: float
    cell: str


def locked_grid_cells(grid: dict[str, list[int]]) -> list[dict[str, int]]:
    return [
        {axis0: value0, axis1: value1}
        for axis0, values0 in [next(iter(grid.items()))]
        for axis1, values1 in [list(grid.items())[1]]
        for value0 in values0
        for value1 in values1
    ]


def assert_locked_grid(primary_cell: dict[str, int], grid: dict[str, list[int]]) -> None:
    if BONFERRONI_M != 3:
        raise AssertionError("SFT-1 Bonferroni m must remain 3")
    cells = locked_grid_cells(grid)
    if primary_cell not in cells:
        raise AssertionError(f"primary cell not in locked grid: {primary_cell}")
    for key, values in grid.items():
        if len(values) != len(set(values)):
            raise AssertionError(f"duplicate locked-grid values for {key}")


def pair_cache_path(pair: str) -> Path | None:
    for raw in PAIR_FILES[pair]:
        path = Path(raw)
        if path.exists():
            return path
    return None


def normalize_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    out = df.rename(columns={c: c.lower() for c in df.columns}).copy()
    missing = {"open", "high", "low", "close"} - set(out.columns)
    if missing:
        raise ValueError(f"OHLC cache missing columns: {sorted(missing)}")
    out.index = pd.to_datetime(out.index, utc=True)
    return out.sort_index()


def load_pair_data(pair: str) -> pd.DataFrame:
    path = pair_cache_path(pair)
    if path is None:
        raise FileNotFoundError(f"missing cache for {pair}")
    df = normalize_ohlc(pd.read_parquet(path))
    if df.index.min() > pd.Timestamp("2014-02-01", tz="UTC") or df.index.max() < pd.Timestamp(BT_END, tz="UTC"):
        raise RuntimeError(f"CACHE_INSUFFICIENT {pair} start={df.index.min()} end={df.index.max()} rows={len(df)}")
    return df


def load_calendar(path: Path = CALENDAR_PATH) -> pd.DataFrame:
    if path.exists():
        df = pd.read_parquet(path)
    else:
        df = build_structural_events(BT_START, BT_END)
    for col in ("date_utc", "tokyo_fix_utc", "london_fix_utc"):
        df[col] = pd.to_datetime(df[col], utc=True)
    return df


def _price_at_or_after(df: pd.DataFrame, ts: pd.Timestamp) -> tuple[pd.Timestamp, float] | None:
    ts = pd.Timestamp(ts).tz_convert("UTC")
    pos = df.index.searchsorted(ts)
    if pos >= len(df.index):
        return None
    actual = df.index[pos]
    if actual > ts + pd.Timedelta(minutes=10):
        return None
    return actual, float(df.iloc[pos]["close"])


def _raw_pnl(pair: str, direction: str, entry_price: float, exit_price: float) -> float:
    pnl = (exit_price - entry_price) / PIP_SIZE[pair]
    if direction == "SHORT":
        pnl *= -1
    return pnl


def simulate_fixed_window_trade(
    *,
    df: pd.DataFrame,
    pair: str,
    strategy: str,
    event_date: str,
    anchor_ts: pd.Timestamp,
    direction: str,
    entry_offset_min: int,
    exit_min: int,
    spread_multiplier: float,
    cell: dict[str, int],
) -> Trade | None:
    entry_target = anchor_ts + pd.Timedelta(minutes=entry_offset_min)
    exit_target = entry_target + pd.Timedelta(minutes=exit_min)
    entry = _price_at_or_after(df, entry_target)
    exit_ = _price_at_or_after(df, exit_target)
    if entry is None or exit_ is None:
        return None
    entry_ts, entry_price = entry
    exit_ts, exit_price = exit_
    spread = SPREAD_PIP[pair] * spread_multiplier
    raw = _raw_pnl(pair, direction, entry_price, exit_price)
    return Trade(
        strategy=strategy,
        pair=pair,
        event_date=event_date,
        entry_ts_utc=entry_ts,
        exit_ts_utc=exit_ts,
        direction=direction,
        entry_price=entry_price,
        exit_price=exit_price,
        raw_pnl_pip=round(raw, 6),
        spread_pip=round(spread, 6),
        pnl_pip=round(raw - spread, 6),
        cell=json.dumps(cell, sort_keys=True),
    )


def profit_factor(pnls: Iterable[float]) -> float:
    vals = list(pnls)
    gross_win = sum(v for v in vals if v > 0)
    gross_loss = abs(sum(v for v in vals if v < 0))
    if gross_loss == 0:
        return float("inf") if gross_win > 0 else 0.0
    return gross_win / gross_loss


def max_drawdown(pnls: list[float]) -> float:
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    return max_dd


def daily_pnl_series(trades: list[Trade]) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame(columns=["date", "pnl_pip", "trade_count"])
    df = pd.DataFrame({"date": [t.exit_ts_utc.date().isoformat() for t in trades], "pnl_pip": [t.pnl_pip for t in trades]})
    return df.groupby("date", as_index=False).agg(pnl_pip=("pnl_pip", "sum"), trade_count=("pnl_pip", "size"))


def _binomial_one_sided_p(wins: int, n: int, p0: float) -> float:
    if n <= 0:
        return 1.0
    p0 = min(max(p0, 1e-6), 1 - 1e-6)
    if n <= 1000:
        prob = (1.0 - p0) ** n
        total = 0.0
        for k in range(n + 1):
            if k >= wins:
                total += prob
            if k < n:
                prob *= (n - k) / (k + 1) * p0 / (1.0 - p0)
        return max(0.0, min(1.0, total))
    mean = n * p0
    var = n * p0 * (1.0 - p0)
    z = (wins - 0.5 - mean) / math.sqrt(var)
    return 0.5 * math.erfc(z / math.sqrt(2))


def bev_wr_from_pnls(pnls: list[float]) -> float:
    wins = [p for p in pnls if p > 0]
    losses = [-p for p in pnls if p < 0]
    if not wins or not losses:
        return 0.5
    avg_win = sum(wins) / len(wins)
    avg_loss = sum(losses) / len(losses)
    return avg_loss / (avg_win + avg_loss)


def walk_forward_folds(trades: list[Trade], folds: int = 4) -> list[dict]:
    if not trades:
        return []
    ordered = sorted(trades, key=lambda t: t.entry_ts_utc)
    chunks = np.array_split(np.arange(len(ordered)), folds)
    out = []
    for i, idxs in enumerate(chunks, start=1):
        fold_trades = [ordered[int(idx)] for idx in idxs]
        summary = summarize_trades(fold_trades, bonferroni=False)
        out.append({"fold": i, "n": summary["n"], "pf": summary["pf"], "wilson_lo": summary["wilson_lo"]})
    return out


def null_bootstrap_p(trades: list[Trade], iterations: int = BOOTSTRAP_ITERATIONS, seed: int = DEFAULT_SEED) -> float:
    pnls = [t.pnl_pip for t in trades]
    if len(pnls) < 5:
        return 1.0
    actual = sum(pnls)
    magnitudes = np.abs(np.array(pnls, dtype=float))
    rng = np.random.default_rng(seed)
    sims = []
    for _ in range(iterations):
        signs = rng.choice([-1.0, 1.0], size=len(magnitudes))
        sims.append(float(np.sum(magnitudes * signs)))
    return float(sum(v >= actual for v in sims) / len(sims))


def single_year_concentration(trades: list[Trade]) -> float:
    if not trades:
        return 0.0
    df = pd.DataFrame({"year": [t.exit_ts_utc.year for t in trades], "pnl": [t.pnl_pip for t in trades]})
    annual = df.groupby("year")["pnl"].sum().abs()
    total = float(annual.sum())
    if total <= 0:
        return 0.0
    return float(annual.max() / total)


def summarize_trades(trades: list[Trade], *, bonferroni: bool = True) -> dict:
    pnls = [t.pnl_pip for t in trades]
    n = len(pnls)
    wins = sum(1 for p in pnls if p > 0)
    wr = wins / n if n else 0.0
    wins_p = [p for p in pnls if p > 0]
    losses_p = [-p for p in pnls if p < 0]
    avg_win = sum(wins_p) / len(wins_p) if wins_p else 0.0
    avg_loss = sum(losses_p) / len(losses_p) if losses_p else 0.0
    kelly = kelly_criterion(wr, avg_win, avg_loss)["full_kelly"]
    bev = bev_wr_from_pnls(pnls)
    raw_p = _binomial_one_sided_p(wins, n, bev)
    return {
        "n": n,
        "wins": wins,
        "wr": wr,
        "wilson_lo": wilson_lower(wins, n),
        "pf": profit_factor(pnls),
        "kelly": kelly,
        "max_dd_pip": max_drawdown(pnls),
        "total_pip": sum(pnls),
        "bev_wr": bev,
        "raw_p": raw_p,
        "bonferroni_p": min(1.0, raw_p * BONFERRONI_M) if bonferroni else raw_p,
    }


def subperiod_summary(trades: list[Trade]) -> dict:
    start = pd.Timestamp("2023-04-01", tz="UTC")
    end = pd.Timestamp("2026-04-30 23:59:59", tz="UTC")
    subset = [t for t in trades if start <= t.entry_ts_utc <= end]
    s = summarize_trades(subset)
    return {"n": s["n"], "wilson_lo": s["wilson_lo"]}


def nsg1_for_grid(grid_rows: list[dict], primary_cell: dict[str, int], axes: list[str]) -> dict:
    df = pd.DataFrame(grid_rows)
    if df.empty:
        return {"status": "DEFERRED", "reason": "empty grid"}
    metric_df = df.rename(columns={"n": "N"})
    result = compute_neighborhood_stability(metric_df, primary_cell, float(metric_df.loc[(metric_df[axes] == pd.Series(primary_cell)).all(axis=1), "bev_wr"].iloc[0]), axes=axes)
    return asdict(result) if hasattr(result, "__dataclass_fields__") else dict(result)


def scenario_verdict(summary: dict, bootstrap_p: float, concentration: float, nsg: dict, missing_pairs: list[str]) -> tuple[str, str]:
    failures = []
    if missing_pairs:
        return "BLOCKED", f"missing required pair cache(s): {', '.join(missing_pairs)}"
    if summary["n"] < 30:
        failures.append("N<30")
    if summary["wilson_lo"] < 0.40:
        failures.append("Wilson_lo<0.40")
    if summary["pf"] < 1.0:
        failures.append("PF<1.0")
    if summary["bonferroni_p"] >= 0.20:
        failures.append("Bonferroni p>=0.20")
    if bootstrap_p >= 0.10:
        failures.append("null bootstrap p>=0.10")
    if not nsg.get("pass_overall", False):
        failures.append("NSG-1 fail")
    if failures:
        return "C", "failed axes: " + ", ".join(failures)
    if summary["n"] >= 100 and summary["wilson_lo"] >= 0.45 and summary["pf"] >= 1.5 and summary["bonferroni_p"] < 0.01 and bootstrap_p < 0.05 and concentration <= 0.50:
        return "A", "strong literal edge"
    if concentration > 0.50:
        return "D", "single-year concentration warning"
    return "B", "positive but marginal literal edge"


def json_default(obj):
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if isinstance(obj, float) and math.isinf(obj):
        return "inf"
    if isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    return str(obj)


def write_outputs(slug: str, result: dict, trades: list[Trade], spread2x_summary: dict) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    json_path = RAW_DIR / f"sft1-{slug}-{RESULT_DATE}.json"
    md_path = RAW_DIR / f"sft1-{slug}-{RESULT_DATE}.md"
    trade_path = RAW_DIR / f"sft1-{slug}-trade-list-{RESULT_DATE}.parquet"
    daily_path = RAW_DIR / f"sft1-{slug}-daily-pnl-{RESULT_DATE}.parquet"
    pd.DataFrame([asdict(t) for t in trades]).to_parquet(trade_path, index=False)
    daily_pnl_series(trades).to_parquet(daily_path, index=False)
    result["artifacts"] = {"trade_list": str(trade_path), "daily_pnl": str(daily_path)}
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=json_default), encoding="utf-8")
    s = result["primary"]["summary"]
    sub = result["subperiod"]
    nsg = result["nsg1"]
    md_path.write_text(
        "\n".join(
            [
                f"# SFT-1 {result['strategy_name']} BT",
                "",
                "## Verdict",
                "",
                f"- N: {s['n']}",
                f"- Wilson_lo (95% CI): {s['wilson_lo']:.6f}",
                f"- PF: {s['pf']:.6f}",
                f"- WF folds: {len(result['wf_folds'])}",
                f"- Bonferroni-adjusted p (m=3): {s['bonferroni_p']:.6f}",
                f"- Kelly: {s['kelly']:.6f}",
                f"- Max DD: {s['max_dd_pip']:.6f} pip",
                f"- Null bootstrap p: {result['null_bootstrap_p']:.6f}",
                f"- Single-year concentration: {result['single_year_concentration']:.2%}",
                f"- 2x spread Wilson_lo: {spread2x_summary['wilson_lo']:.6f}",
                "",
                "## Sub-period 検証",
                "",
                "直近 3 年 (2023-04 .. 2026-04) のみ:",
                f"- N: {sub['n']}",
                f"- Wilson_lo: {sub['wilson_lo']:.6f}",
                "",
                "## NSG-1",
                "",
                json.dumps(nsg, indent=2, ensure_ascii=False, default=json_default),
                "",
                "## Scenario verdict",
                "",
                f"{result['scenario_verdict']} — {result['scenario_reason']}",
                "",
                "## Data caveats",
                "",
                f"- Missing required spec docs in checkout: {', '.join(result['missing_spec_docs']) or 'none'}",
                f"- Missing pair caches: {', '.join(result['missing_pairs']) or 'none'}",
            ]
        ),
        encoding="utf-8",
    )


def run_month_end_cell(
    calendar: pd.DataFrame,
    pair_data: dict[str, pd.DataFrame],
    cell: dict[str, int],
    spread_multiplier: float,
) -> list[Trade]:
    events = calendar[calendar["month_end_us"]]
    trades: list[Trade] = []
    for _, event in events.iterrows():
        for pair in PRIMARY_PAIRS:
            if pair not in pair_data:
                continue
            trade = simulate_fixed_window_trade(
                df=pair_data[pair],
                pair=pair,
                strategy="SFT-A",
                event_date=event["date_utc"].date().isoformat(),
                anchor_ts=event["london_fix_utc"],
                direction=PAIR_DIRECTIONS[pair],
                entry_offset_min=cell["entry_offset_min"],
                exit_min=cell["exit_min"],
                spread_multiplier=spread_multiplier,
                cell=cell,
            )
            if trade is not None:
                trades.append(trade)
    return trades


def evaluate_strategy(
    *,
    slug: str,
    strategy_name: str,
    primary_cell: dict[str, int],
    grid: dict[str, list[int]],
    required_pairs: list[str],
    cell_runner: Callable[[pd.DataFrame, dict[str, pd.DataFrame], dict[str, int], float], list[Trade]],
) -> dict:
    assert_locked_grid(primary_cell, grid)
    calendar = load_calendar()
    pair_data = {}
    missing_pairs = []
    for pair in required_pairs:
        try:
            pair_data[pair] = load_pair_data(pair)
        except (FileNotFoundError, RuntimeError):
            missing_pairs.append(pair)
    grid_rows = []
    primary_trades: list[Trade] = []
    spread2x_trades: list[Trade] = []
    for cell in locked_grid_cells(grid):
        trades = cell_runner(calendar, pair_data, cell, 1.0)
        summary = summarize_trades(trades)
        grid_rows.append({**cell, **summary})
        if cell == primary_cell:
            primary_trades = trades
            spread2x_trades = cell_runner(calendar, pair_data, cell, 2.0)
    primary_summary = summarize_trades(primary_trades)
    spread2x_summary = summarize_trades(spread2x_trades)
    bootstrap_p = null_bootstrap_p(primary_trades)
    concentration = single_year_concentration(primary_trades)
    nsg = nsg1_for_grid(grid_rows, primary_cell, list(grid.keys()))
    scenario, reason = scenario_verdict(primary_summary, bootstrap_p, concentration, nsg, missing_pairs)
    result = {
        "status": "OK" if not missing_pairs else "BLOCKED_DATA",
        "strategy_name": strategy_name,
        "primary_cell": primary_cell,
        "bonferroni_m": BONFERRONI_M,
        "missing_spec_docs": [p for p in REQUIRED_SPEC_DOCS if not Path(p).exists()],
        "missing_pairs": missing_pairs,
        "grid": grid_rows,
        "primary": {"summary": primary_summary, "trades": [asdict(t) for t in primary_trades]},
        "spread_2x": {"summary": spread2x_summary},
        "wf_folds": walk_forward_folds(primary_trades),
        "null_bootstrap_p": bootstrap_p,
        "single_year_concentration": concentration,
        "subperiod": subperiod_summary(primary_trades),
        "nsg1": nsg,
        "scenario_verdict": scenario,
        "scenario_reason": reason,
    }
    write_outputs(slug, result, primary_trades, spread2x_summary)
    return result


def print_dry_run() -> None:
    assert_locked_grid(PRIMARY_CELL, MONTH_GRID)
    print("SFT-1A month_end_usd_rebalance_short DRY RUN")
    print(f"BONFERRONI_M={BONFERRONI_M}")
    print(f"PRIMARY_CELL={PRIMARY_CELL}")
    print(f"PRIMARY_PAIRS={PRIMARY_PAIRS}")
    print("GRID:")
    for cell in locked_grid_cells(MONTH_GRID):
        marker = " PRIMARY" if cell == PRIMARY_CELL else ""
        print(f"- {cell}{marker}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        print_dry_run()
        return 0
    result = evaluate_strategy(
        slug="month-end-usd-rebalance",
        strategy_name="month_end_usd_rebalance_short",
        primary_cell=PRIMARY_CELL,
        grid=MONTH_GRID,
        required_pairs=PRIMARY_PAIRS,
        cell_runner=run_month_end_cell,
    )
    print(f"{result['scenario_verdict']} {result['scenario_reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
