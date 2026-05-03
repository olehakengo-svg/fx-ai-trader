#!/usr/bin/env python3
"""C-1 London Open Breakout pre-registered BT runner.

This runner is intentionally standalone and BT-only. It reads local Massive
Market Data parquet cache, evaluates the fixed 81-cell sensitivity grid, and
writes deterministic JSON/Markdown artifacts for Rule 1 review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
from dataclasses import asdict, dataclass
from datetime import time
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

BONFERRONI_M = 81
PRIMARY_CELL = {
    "asian_window_h": 7,
    "entry_method": "close",
    "exit_method": "range_1.0",
    "range_filter_mult": 1.0,
}
ASIAN_WINDOWS = [6, 7, 8]
ENTRY_METHODS = ["close", "high_break", "m1_close"]
EXIT_METHODS = ["time_12utc", "range_1.0", "range_1.5"]
RANGE_FILTERS = [1.0, 1.2, 1.5]
DEFAULT_SEED = 20260503
INTERVENTION_DATES = {
    "2022-09-22",
    "2022-10-21",
    "2022-10-24",
    "2024-04-29",
    "2024-05-01",
    "2024-07-11",
    "2024-07-12",
}
COHORTS = [
    ("2014-2016 pre-Brexit", "2014-01-01", "2016-06-22"),
    ("2016-2017 Brexit Vote", "2016-06-23", "2017-12-31"),
    ("2018-2019 calm", "2018-01-01", "2019-12-31"),
    ("2020 COVID", "2020-01-01", "2020-12-31"),
    ("2021-2022 Truss budget", "2021-01-01", "2022-12-31"),
    ("2023-2024", "2023-01-01", "2024-12-31"),
    ("2025-2026", "2025-01-01", "2026-04-30"),
]


@dataclass(frozen=True)
class AsianRange:
    high: float
    low: float
    width: float
    width_pips: float


@dataclass(frozen=True)
class Entry:
    timestamp: pd.Timestamp
    side: str
    price: float
    break_price: float


def bonferroni_alpha() -> float:
    return 0.05 / BONFERRONI_M


def pip_size(pair: str) -> float:
    return 0.01 if "JPY" in pair.replace("_", "") else 0.0001


def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    rename = {c: c.lower() for c in out.columns}
    out = out.rename(columns=rename)
    required = {"open", "high", "low", "close"}
    missing = required - set(out.columns)
    if missing:
        raise ValueError(f"OHLCV cache missing columns: {sorted(missing)}")
    out.index = pd.to_datetime(out.index, utc=True)
    return out.sort_index()


def compute_asian_range(df: pd.DataFrame, day: pd.Timestamp, window_h: int) -> AsianRange | None:
    df = normalize_ohlcv(df)
    day = pd.Timestamp(day).tz_convert("UTC") if pd.Timestamp(day).tzinfo else pd.Timestamp(day, tz="UTC")
    start = day.normalize()
    end = start + pd.Timedelta(hours=window_h)
    chunk = df[(df.index >= start) & (df.index < end)]
    if chunk.empty:
        return None
    high = float(chunk["high"].max())
    low = float(chunk["low"].min())
    width = high - low
    return AsianRange(high=high, low=low, width=width, width_pips=width / 0.01)


def find_breakout_entry(
    df: pd.DataFrame,
    day: pd.Timestamp,
    asian: AsianRange,
    entry_method: str,
) -> Entry | None:
    df = normalize_ohlcv(df)
    start = pd.Timestamp(day).normalize() + pd.Timedelta(hours=7)
    end = pd.Timestamp(day).normalize() + pd.Timedelta(hours=8)
    gate = df[(df.index >= start) & (df.index < end)]
    for ts, row in gate.iterrows():
        if entry_method in {"close", "m1_close"}:
            if float(row["close"]) > asian.high:
                return Entry(ts, "LONG", float(row["close"]), asian.high)
            if float(row["close"]) < asian.low:
                return Entry(ts, "SHORT", float(row["close"]), asian.low)
        elif entry_method == "high_break":
            if float(row["high"]) > asian.high:
                return Entry(ts, "LONG", asian.high, asian.high)
            if float(row["low"]) < asian.low:
                return Entry(ts, "SHORT", asian.low, asian.low)
        else:
            raise ValueError(f"unknown entry_method={entry_method}")
    return None


def _spread_profile_pips() -> dict[int, float]:
    # H-1 task files were absent in this checkout. Use the documented London
    # FX-only friction fallback from friction-analysis.md and record it in JSON.
    return {hour: 0.86 for hour in range(24)}


def _is_excluded_day(day: pd.Timestamp) -> bool:
    d = day.date()
    if day.weekday() >= 5:
        return True
    if (d.month == 12 and d.day >= 24) or (d.month == 1 and d.day <= 3):
        return True
    return str(d) in INTERVENTION_DATES


def _exit_trade(
    df: pd.DataFrame,
    day: pd.Timestamp,
    entry: Entry,
    asian: AsianRange,
    exit_method: str,
    pair: str,
    spread_profile: dict[int, float],
) -> dict:
    pipsz = pip_size(pair)
    start = entry.timestamp + pd.Timedelta(minutes=5)
    hard_close = day.normalize() + pd.Timedelta(hours=17)
    noon = day.normalize() + pd.Timedelta(hours=12)
    chunk = df[(df.index >= start) & (df.index <= hard_close)]
    if chunk.empty:
        exit_ts = entry.timestamp
        exit_price = entry.price
        reason = "no_future_bar"
    else:
        stop_dist = asian.width * 0.5
        target_mult = {"time_12utc": None, "range_1.0": 1.0, "range_1.5": 1.5}[exit_method]
        if entry.side == "LONG":
            stop = entry.break_price - stop_dist
            target = None if target_mult is None else entry.price + asian.width * target_mult
        else:
            stop = entry.break_price + stop_dist
            target = None if target_mult is None else entry.price - asian.width * target_mult
        exit_ts = chunk.index[-1]
        exit_price = float(chunk.iloc[-1]["close"])
        reason = "force_17utc"
        for ts, row in chunk.iterrows():
            high = float(row["high"])
            low = float(row["low"])
            close = float(row["close"])
            if entry.side == "LONG":
                if low <= stop:
                    exit_ts, exit_price, reason = ts, stop, "stop"
                    break
                if target is not None and high >= target:
                    exit_ts, exit_price, reason = ts, target, "target"
                    break
            else:
                if high >= stop:
                    exit_ts, exit_price, reason = ts, stop, "stop"
                    break
                if target is not None and low <= target:
                    exit_ts, exit_price, reason = ts, target, "target"
                    break
            if ts >= noon:
                exit_ts, exit_price, reason = ts, close, "time_12utc"
                break
    raw = (exit_price - entry.price) / pipsz
    if entry.side == "SHORT":
        raw *= -1
    spread = float(spread_profile.get(entry.timestamp.hour, 0.86))
    net = raw - spread
    return {
        "timestamp": entry.timestamp.isoformat(),
        "exit_timestamp": exit_ts.isoformat(),
        "side": entry.side,
        "entry": round(entry.price, 6),
        "exit": round(exit_price, 6),
        "exit_reason": reason,
        "pnl_pip_raw": round(raw, 6),
        "pnl_pip_net": round(net, 6),
        "spread_pip": spread,
        "asian_range_pip": round(asian.width_pips, 6),
        "holding_bars": max(0, int((exit_ts - entry.timestamp) / pd.Timedelta(minutes=5))),
    }


def _wilson_lower(wins: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    den = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return max(0.0, (centre - margin) / den) * 100


def _profit_factor(pnls: Iterable[float]) -> float:
    vals = list(pnls)
    gross_win = sum(v for v in vals if v > 0)
    gross_loss = abs(sum(v for v in vals if v < 0))
    if gross_loss == 0:
        return float("inf") if gross_win > 0 else 0.0
    return gross_win / gross_loss


def _binomial_p_one_sided(wins: int, n: int) -> float:
    if n <= 0 or wins <= n / 2:
        return 1.0
    if n <= 250:
        return sum(math.comb(n, k) for k in range(wins, n + 1)) / (2**n)
    z = (wins - 0.5 - n * 0.5) / math.sqrt(n * 0.25)
    return 0.5 * math.erfc(z / math.sqrt(2))


def _kelly_fraction(pnls: list[float]) -> float:
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    if not wins or not losses:
        return 0.0
    p = len(wins) / len(pnls)
    b = (sum(wins) / len(wins)) / abs(sum(losses) / len(losses))
    return max(0.0, (b * p - (1 - p)) / b)


def _sharpe(pnls: list[float]) -> float:
    if len(pnls) < 2:
        return 0.0
    arr = np.array(pnls, dtype=float)
    sd = float(arr.std(ddof=1))
    if sd == 0:
        return 0.0
    return float(math.sqrt(252) * arr.mean() / sd)


def _wf_ratio(trades: list[dict]) -> float:
    if len(trades) < 30:
        return 0.0
    ordered = sorted(trades, key=lambda t: t["timestamp"])
    folds = np.array_split(ordered, 3)
    ratios = []
    for i in range(1, len(folds)):
        train = [t["pnl_pip_net"] for fold in folds[:i] for t in fold.tolist()]
        test = [t["pnl_pip_net"] for t in folds[i].tolist()]
        train_pf = _profit_factor(train)
        test_pf = _profit_factor(test)
        if train_pf and math.isfinite(train_pf):
            ratios.append(test_pf / train_pf)
    return float(min(ratios)) if ratios else 0.0


def summarize_trades(trades: list[dict]) -> dict:
    pnls = [float(t["pnl_pip_net"]) for t in trades]
    raw = [float(t["pnl_pip_raw"]) for t in trades]
    n = len(pnls)
    wins = sum(1 for p in pnls if p > 0)
    p = _binomial_p_one_sided(wins, n)
    return {
        "n": n,
        "wins": wins,
        "wr_pct": round((wins / n * 100) if n else 0.0, 6),
        "wilson_lo_pct": round(_wilson_lower(wins, n), 6),
        "pf": round(_profit_factor(pnls), 6) if math.isfinite(_profit_factor(pnls)) else "inf",
        "oos_is_pf_ratio": round(_wf_ratio(trades), 6),
        "p_value": p,
        "bonferroni_p": min(1.0, p * BONFERRONI_M),
        "bonferroni_pass": p < bonferroni_alpha(),
        "sharpe": round(_sharpe(pnls), 6),
        "kelly_fraction": round(_kelly_fraction(pnls), 6),
        "pnl_pip_net": round(sum(pnls), 6),
        "pnl_pip_raw": round(sum(raw), 6),
        "max_dd_pip": round(_max_drawdown(pnls), 6),
        "avg_holding_bars": round(float(np.mean([t["holding_bars"] for t in trades])) if trades else 0.0, 6),
    }


def _max_drawdown(pnls: list[float]) -> float:
    equity = 0.0
    peak = 0.0
    dd = 0.0
    for p in pnls:
        equity += p
        peak = max(peak, equity)
        dd = min(dd, equity - peak)
    return dd


def run_cell(df: pd.DataFrame, pair: str, cell: dict, spread_profile: dict[int, float]) -> list[dict]:
    day_index = pd.date_range(df.index.min().normalize(), df.index.max().normalize(), freq="D", tz="UTC")
    prior_ranges: list[float] = []
    trades: list[dict] = []
    for day in day_index:
        if _is_excluded_day(day):
            continue
        day_df = df[(df.index >= day) & (df.index < day + pd.Timedelta(days=1))]
        if day_df.empty:
            continue
        asian = compute_asian_range(day_df, day, cell["asian_window_h"])
        if asian is None or asian.width <= 0:
            continue
        if len(prior_ranges) >= 20:
            median_60 = float(np.median(prior_ranges[-60:]))
            if asian.width < median_60 * cell["range_filter_mult"]:
                prior_ranges.append(asian.width)
                continue
        entry = find_breakout_entry(day_df, day, asian, cell["entry_method"])
        prior_ranges.append(asian.width)
        if entry is None:
            continue
        trades.append(_exit_trade(day_df, day, entry, asian, cell["exit_method"], pair, spread_profile))
    return trades


def _cell_id(cell: dict) -> str:
    return f"aw{cell['asian_window_h']}_{cell['entry_method']}_{cell['exit_method']}_rf{cell['range_filter_mult']}"


def _is_primary(cell: dict) -> bool:
    return all(cell[k] == v for k, v in PRIMARY_CELL.items())


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def load_local_cache(pair: str) -> tuple[pd.DataFrame, str]:
    long_path = Path("data/cache/extended") / f"{pair}_5m_long.parquet"
    massive_path = Path("data/cache/massive") / f"{pair}_5m.parquet"
    if long_path.exists():
        return normalize_ohlcv(pd.read_parquet(long_path)), str(long_path)
    if not massive_path.exists():
        raise FileNotFoundError(
            f"missing local cache: tried {long_path} then {massive_path}"
        )
    return normalize_ohlcv(pd.read_parquet(massive_path)), str(massive_path)


def build_result(pair: str, start: str, end: str, seed: int) -> dict:
    df, cache_path = load_local_cache(pair)
    requested_start = pd.Timestamp(start, tz="UTC")
    requested_end = pd.Timestamp(end, tz="UTC") + pd.Timedelta(hours=23, minutes=59, seconds=59)
    df = df[(df.index >= requested_start) & (df.index <= requested_end)]
    if df.empty:
        raise RuntimeError("no bars in requested window")
    spread_profile = _spread_profile_pips()
    cells = []
    primary = None
    for aw in ASIAN_WINDOWS:
        for entry in ENTRY_METHODS:
            for exit_method in EXIT_METHODS:
                for rf in RANGE_FILTERS:
                    cell = {
                        "asian_window_h": aw,
                        "entry_method": entry,
                        "exit_method": exit_method,
                        "range_filter_mult": rf,
                    }
                    trades = run_cell(df, pair, cell, spread_profile)
                    row = {
                        "cell_id": _cell_id(cell),
                        "params": cell,
                        "is_primary": _is_primary(cell),
                        "stats": summarize_trades(trades),
                        "trades": trades,
                    }
                    cells.append(row)
                    if row["is_primary"]:
                        primary = row
    assert primary is not None
    coverage_days = int((df.index.max().normalize() - df.index.min().normalize()) / pd.Timedelta(days=1)) + 1
    requested_days = int((requested_end.normalize() - requested_start.normalize()) / pd.Timedelta(days=1)) + 1
    header = {
        "strategy": "c1_london_open_breakout",
        "data_source": f"local_parquet:{cache_path}",
        "live_separation": "bt_only",
        "pair": pair,
        "interval": "M5",
        "time_window": {"start": start, "end": end},
        "actual_data_window": {
            "start": df.index.min().isoformat(),
            "end": df.index.max().isoformat(),
            "bars": int(len(df)),
            "coverage_days": coverage_days,
            "requested_days": requested_days,
            "coverage_ratio": round(coverage_days / requested_days, 6),
        },
        "git_sha": _git_sha(),
        "seed": seed,
        "bonferroni_m": BONFERRONI_M,
        "primary_cell": PRIMARY_CELL,
        "spread_profile_source": "fallback friction-analysis.md London FX-only 0.86pip; H-1 audit files absent",
        "limitations": [],
    }
    if coverage_days < requested_days * 0.95:
        header["limitations"].append("LOCAL_CACHE_INCOMPLETE_FOR_2014_2026_REQUEST")
    verdict = verdict_from_primary(primary, blocked=bool(header["limitations"]))
    return {"header": header, "primary": primary, "cells": cells, "scenario_verdict": verdict}


def verdict_from_primary(primary: dict, blocked: bool = False) -> dict:
    s = primary["stats"]
    pf = float("inf") if s["pf"] == "inf" else float(s["pf"])
    passes = {
        "n_ge_30": s["n"] >= 30,
        "wilson_lo_ge_50": s["wilson_lo_pct"] >= 50,
        "pf_ge_1_10": pf >= 1.10,
        "oos_is_ge_0_80": s["oos_is_pf_ratio"] >= 0.80,
        "bonferroni_pass": bool(s["bonferroni_pass"]),
        "sharpe_ge_0_5": s["sharpe"] >= 0.5,
        "kelly_gt_0": s["kelly_fraction"] > 0,
    }
    if blocked:
        scenario = "BLOCKED_DATA"
    elif all(passes.values()):
        scenario = "NEEDS_VALIDITY_CHECK"
    elif (not passes["wilson_lo_ge_50"]) or (not passes["kelly_gt_0"]):
        scenario = "REJECT"
    else:
        scenario = "NEEDS_MORE_EVIDENCE"
    return {"scenario": scenario, "matrix_passes": passes}


def write_outputs(result: dict, output_prefix: str) -> None:
    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    json_path = prefix.with_suffix(".json")
    md_path = prefix.with_suffix(".md")
    payload = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
    json_path.write_text(payload + "\n")
    md_path.write_text(render_markdown(result, json_path), encoding="utf-8")


def render_markdown(result: dict, json_path: Path) -> str:
    h = result["header"]
    p = result["primary"]
    lines = [
        "# C-1 London Open Breakout BT",
        "",
        f"- JSON: `{json_path}`",
        f"- pair/interval: {h['pair']} {h['interval']}",
        f"- requested: {h['time_window']['start']} to {h['time_window']['end']}",
        f"- actual: {h['actual_data_window']['start']} to {h['actual_data_window']['end']} ({h['actual_data_window']['bars']} bars)",
        f"- verdict: **{result['scenario_verdict']['scenario']}**",
        "",
        "## Primary Cell",
        "",
        "| N | WR | Wilson lo | PF | OOS/IS | Bonf pass | Sharpe | Kelly | Net pip |",
        "|---:|---:|---:|---:|---:|---|---:|---:|---:|",
    ]
    s = p["stats"]
    lines.append(
        f"| {s['n']} | {s['wr_pct']:.2f}% | {s['wilson_lo_pct']:.2f}% | {s['pf']} | "
        f"{s['oos_is_pf_ratio']:.2f} | {s['bonferroni_pass']} | {s['sharpe']:.2f} | "
        f"{s['kelly_fraction']:.4f} | {s['pnl_pip_net']:.2f} |"
    )
    lines += [
        "",
        "## 81 Cell Grid",
        "",
        "| cell | N | WR | Wilson | PF | OOS/IS | Bonf p | Sharpe | Kelly | Net pip |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["cells"]:
        st = row["stats"]
        mark = " **PRIMARY**" if row["is_primary"] else ""
        lines.append(
            f"| {row['cell_id']}{mark} | {st['n']} | {st['wr_pct']:.2f}% | {st['wilson_lo_pct']:.2f}% | "
            f"{st['pf']} | {st['oos_is_pf_ratio']:.2f} | {st['bonferroni_p']:.6g} | "
            f"{st['sharpe']:.2f} | {st['kelly_fraction']:.4f} | {st['pnl_pip_net']:.2f} |"
        )
    if h["limitations"]:
        lines += ["", "## Limitations", ""]
        lines += [f"- {x}" for x in h["limitations"]]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", default="GBP_JPY")
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = ap.parse_args()
    np.random.seed(args.seed)
    result = build_result(args.pair, args.start, args.end, args.seed)
    write_outputs(result, args.output)
    digest = hashlib.sha256(Path(args.output).with_suffix(".json").read_bytes()).hexdigest()
    print(f"wrote {args.output}.json sha256={digest}")
    print(f"scenario={result['scenario_verdict']['scenario']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
