#!/usr/bin/env python3
"""Pre-registered Bigbeluga displacement/intrabar-delta grid BT.

Uses repo-local MASSIVE M5 parquet only. No Yahoo fallback.
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.bigbeluga_grid_db import connect, replace_cells  # noqa: E402


PRIMARY_PAIRS = ["USD_JPY", "GBP_JPY"]
SECONDARY_PAIRS = ["EUR_USD", "GBP_USD", "EUR_JPY", "EUR_GBP", "AUD_CAD", "AUD_NZD", "NZD_CAD"]
PAIR_SCHEMA_MAP = {
    "USD_JPY": "lower",
    "GBP_JPY": "lower",
    "EUR_USD": "upper",
    "GBP_USD": "upper",
    "EUR_JPY": "upper",
    "EUR_GBP": "upper",
    "AUD_CAD": "upper",
    "AUD_NZD": "upper",
    "NZD_CAD": "upper",
}
VOL_MULTS_PRIMARY = [1.5, 2.0, 2.5, 3.0]
BODY_PCTS_PRIMARY = [0.40, 0.50, 0.60]
VOL_MULTS_SECONDARY = [2.0]
BODY_PCTS_SECONDARY = [0.50]
HYPOTHESES = ["H-A", "H-B", "H-C", "H-D"]
HORIZONS = [1, 3, 6, 12]
PRIMARY_M = 384
FDR_Q = 0.10
BONFERRONI_ALPHA = 0.05 / PRIMARY_M
DATA_SOURCE = "MASSIVE_parquet"
ANNUAL_SCALE = math.sqrt(252 * 24)
DELTA_THRESHOLD = 0.30
TYPICAL_SPREAD_PIP = {
    "USD_JPY": 0.2,
    "GBP_JPY": 0.5,
    "EUR_USD": 0.1,
    "GBP_USD": 0.2,
    "EUR_JPY": 0.3,
    "EUR_GBP": 0.2,
    "AUD_CAD": 0.5,
    "AUD_NZD": 0.6,
    "NZD_CAD": 0.6,
}
DEFAULT_CACHE_DIR = ROOT / "data" / "cache" / "massive"
DEFAULT_OUT_DIR = ROOT / "reports" / "bigbeluga_displacement_delta"
DEFAULT_DB = ROOT / "data" / "bigbeluga_grid_cells.db"


@dataclass(frozen=True)
class LoadedM5:
    pair: str
    df: pd.DataFrame
    source_path: Path
    schema: str


def pip_multiplier(pair: str) -> float:
    return 100.0 if "JPY" in pair else 10000.0


def parquet_path(cache_dir: Path, pair: str) -> Path:
    return cache_dir / f"{pair}_5m.parquet"


def normalize_m5_by_pair(pair: str, raw: pd.DataFrame) -> pd.DataFrame:
    schema = PAIR_SCHEMA_MAP[pair]
    if schema == "lower":
        required = ["open", "high", "low", "close", "volume"]
        missing = [col for col in required if col not in raw.columns]
        if missing:
            raise ValueError(f"{pair} lower schema missing columns: {missing}")
        out = raw[required].rename(
            columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}
        ).copy()
        if "timestamp_utc" in raw.columns:
            out.index = pd.to_datetime(raw["timestamp_utc"], utc=True)
    elif schema == "upper":
        required = ["Open", "High", "Low", "Close", "Volume"]
        missing = [col for col in required if col not in raw.columns]
        if missing:
            raise ValueError(f"{pair} upper schema missing columns: {missing}")
        out = raw[required].copy()
    else:
        raise ValueError(f"unknown schema for {pair}: {schema}")

    if not isinstance(out.index, pd.DatetimeIndex):
        raise ValueError(f"{pair} parquet must have a DatetimeIndex or timestamp_utc column")
    if out.index.tz is None:
        out.index = out.index.tz_localize("UTC")
    else:
        out.index = out.index.tz_convert("UTC")
    out = out.sort_index()
    out = out[~out.index.duplicated(keep="last")]
    return out.astype(float).dropna()


def load_m5(cache_dir: Path, pair: str) -> LoadedM5:
    path = parquet_path(cache_dir, pair)
    if not path.exists():
        raise FileNotFoundError(f"missing required MASSIVE M5 parquet: {path}")
    df = normalize_m5_by_pair(pair, pd.read_parquet(path))
    if df.empty:
        raise ValueError(f"empty MASSIVE M5 parquet: {path}")
    return LoadedM5(pair=pair, df=df, source_path=path, schema=PAIR_SCHEMA_MAP[pair])


def build_h1_features(m5: pd.DataFrame) -> pd.DataFrame:
    direction = np.sign(m5["Close"] - m5["Open"])
    enriched = m5.copy()
    enriched["buy_vol"] = np.where(direction > 0, enriched["Volume"], 0.0)
    enriched["sell_vol"] = np.where(direction < 0, enriched["Volume"], 0.0)
    grouped = enriched.resample("1h", label="left", closed="left")
    h1 = grouped.agg(
        Open=("Open", "first"),
        High=("High", "max"),
        Low=("Low", "min"),
        Close=("Close", "last"),
        Volume=("Volume", "sum"),
        buyVol=("buy_vol", "sum"),
        sellVol=("sell_vol", "sum"),
        n_m5=("Close", "count"),
    ).dropna(subset=["Open", "High", "Low", "Close"])
    h1 = h1[h1["n_m5"] > 0].copy()
    total_delta_vol = h1["buyVol"] + h1["sellVol"]
    h1["deltaRatio"] = np.where(total_delta_vol > 0, (h1["buyVol"] - h1["sellVol"]) / total_delta_vol, 0.0)
    h1["avgVol20_prior"] = h1["Volume"].shift(1).rolling(20, min_periods=20).mean()
    bar_range = h1["High"] - h1["Low"]
    h1["bodyRatio"] = np.where(bar_range > 0, (h1["Close"] - h1["Open"]).abs() / bar_range, 0.0)
    h1["bullBody"] = h1["Close"] > h1["Open"]
    h1["bearBody"] = h1["Close"] < h1["Open"]
    return h1


def cell_id(pair: str, hypothesis: str, vol_mult: float, body_pct: float, horizon: int) -> str:
    return f"{pair}_{hypothesis}_{vol_mult:g}_{body_pct:.2f}_{horizon}"


def wilson_lower(wins: int, n: int, z: float = 1.959963984540054) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (centre - spread) / denom)


def profit_factor(values: np.ndarray) -> float:
    gross_profit = float(values[values > 0].sum())
    gross_loss = float(-values[values < 0].sum())
    if gross_loss <= 0:
        return float("inf") if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def p_value_binomial_two_sided(wins: int, n: int) -> float:
    if n <= 0:
        return 1.0
    try:
        from scipy import stats

        return float(stats.binomtest(wins, n, p=0.5, alternative="two-sided").pvalue)
    except Exception:
        # Exact two-sided binomial fallback for p=0.5.
        tail = min(wins, n - wins)
        prob = sum(math.comb(n, k) for k in range(tail + 1)) / (2**n)
        return min(1.0, 2.0 * prob)


def max_drawdown_pct(returns_pct: np.ndarray) -> float:
    if len(returns_pct) == 0:
        return 0.0
    equity = np.cumsum(returns_pct)
    peaks = np.maximum.accumulate(equity)
    return float((equity - peaks).min())


def year_flip_count(years: np.ndarray, returns_pct: np.ndarray) -> int:
    if len(returns_pct) == 0:
        return 0
    aggregate = float(np.nanmean(returns_pct))
    if aggregate == 0 or not math.isfinite(aggregate):
        return 0
    agg_sign = 1 if aggregate > 0 else -1
    flips = 0
    for year in sorted(set(int(y) for y in years)):
        yr_returns = returns_pct[years == year]
        yr_mean = float(np.nanmean(yr_returns)) if len(yr_returns) else 0.0
        if yr_mean == 0 or not math.isfinite(yr_mean):
            continue
        if (1 if yr_mean > 0 else -1) != agg_sign:
            flips += 1
    return flips


def mae_mfe(h1: pd.DataFrame, idx: np.ndarray, horizon: int, side: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    opens = h1["Open"].to_numpy(dtype=float)
    highs = h1["High"].to_numpy(dtype=float)
    lows = h1["Low"].to_numpy(dtype=float)
    mae: list[float] = []
    mfe: list[float] = []
    for raw_i, raw_side in zip(idx, side):
        i = int(raw_i)
        entry_i = i + 1
        exit_i = i + 1 + horizon
        if entry_i >= len(h1) or exit_i >= len(h1):
            continue
        entry = opens[entry_i]
        lows_window = lows[entry_i : exit_i + 1]
        highs_window = highs[entry_i : exit_i + 1]
        if int(raw_side) > 0:
            mae.append((float(np.nanmin(lows_window)) / entry - 1.0) * 100.0)
            mfe.append((float(np.nanmax(highs_window)) / entry - 1.0) * 100.0)
        else:
            mae.append((entry / float(np.nanmax(highs_window)) - 1.0) * 100.0)
            mfe.append((entry / float(np.nanmin(lows_window)) - 1.0) * 100.0)
    return np.asarray(mae, dtype=float), np.asarray(mfe, dtype=float)


def empty_cell(
    pair: str,
    hypothesis: str,
    vol_mult: float,
    body_pct: float,
    horizon: int,
    cohort: str,
    period_start: str,
    period_end: str,
    generated_at: str,
) -> dict:
    return {
        "cell_id": cell_id(pair, hypothesis, vol_mult, body_pct, horizon),
        "pair": pair,
        "tf": "H1",
        "intrabar_tf": "M5",
        "hypothesis": hypothesis,
        "vol_mult": vol_mult,
        "body_pct": body_pct,
        "horizon_bars": horizon,
        "cohort": cohort,
        "n_trades": 0,
        "win_rate": 0.0,
        "ev_pip": 0.0,
        "ev_pct": 0.0,
        "profit_factor": 0.0,
        "wilson_lower_95": 0.0,
        "sharpe_annual": 0.0,
        "kelly_fraction": 0.0,
        "max_dd_pct": 0.0,
        "mae_mean_pct": 0.0,
        "mae_p5_pct": 0.0,
        "mfe_mean_pct": 0.0,
        "year_flip_count": 0,
        "p_value": 1.0,
        "bonferroni_pass": 0,
        "bh_fdr_pass": 0,
        "g7_delta_incremental": None if hypothesis in {"H-A", "H-B"} else 0,
        "verdict": "REJECT",
        "period_start": period_start,
        "period_end": period_end,
        "bt_data_source": DATA_SOURCE,
        "generated_at": generated_at,
    }


def signal_side(h1: pd.DataFrame, hypothesis: str, vol_mult: float, body_pct: float) -> pd.Series:
    high_vol = h1["Volume"] > h1["avgVol20_prior"] * vol_mult
    is_displacement = h1["bodyRatio"] >= body_pct
    bull_shift = h1["bullBody"] & high_vol & is_displacement
    bear_shift = h1["bearBody"] & high_vol & is_displacement
    side = pd.Series(0, index=h1.index, dtype="int8")
    if hypothesis == "H-A":
        side.loc[bull_shift] = 1
        side.loc[bear_shift] = -1
    elif hypothesis == "H-B":
        side.loc[bull_shift] = -1
        side.loc[bear_shift] = 1
    elif hypothesis == "H-C":
        side.loc[bull_shift & (h1["deltaRatio"] > DELTA_THRESHOLD)] = 1
        side.loc[bear_shift & (h1["deltaRatio"] < -DELTA_THRESHOLD)] = -1
    elif hypothesis == "H-D":
        side.loc[bull_shift & (h1["deltaRatio"] < -DELTA_THRESHOLD)] = 1
        side.loc[bear_shift & (h1["deltaRatio"] > DELTA_THRESHOLD)] = -1
    else:
        raise ValueError(f"unknown hypothesis: {hypothesis}")
    return side


def stats_for_cell(
    h1: pd.DataFrame,
    idx: np.ndarray,
    side: np.ndarray,
    pair: str,
    hypothesis: str,
    vol_mult: float,
    body_pct: float,
    horizon: int,
    cohort: str,
    period_start: str,
    period_end: str,
    generated_at: str,
) -> dict:
    n = int(len(idx))
    if n == 0:
        return empty_cell(pair, hypothesis, vol_mult, body_pct, horizon, cohort, period_start, period_end, generated_at)

    opens = h1["Open"].to_numpy(dtype=float)
    closes = h1["Close"].to_numpy(dtype=float)
    entry = opens[idx + 1]
    exit_ = closes[idx + 1 + horizon]
    side_float = side.astype(float)
    pct_ret = np.where(side_float > 0, (exit_ / entry - 1.0) * 100.0, (entry / exit_ - 1.0) * 100.0)
    pip_ret = (exit_ - entry) * pip_multiplier(pair) * side_float
    wins = int((pct_ret > 0).sum())
    wr = wins / n
    pf = profit_factor(pip_ret)
    std = float(np.nanstd(pct_ret, ddof=1)) if n > 1 else 0.0
    sharpe = float(np.nanmean(pct_ret) / std * ANNUAL_SCALE) if std > 0 else 0.0
    gains = pct_ret[pct_ret > 0]
    losses = pct_ret[pct_ret < 0]
    rr = float(np.nanmean(gains) / -np.nanmean(losses)) if len(gains) and len(losses) else None
    kelly = wr - (1.0 - wr) / rr if rr and rr > 0 else (1.0 if len(gains) and not len(losses) else 0.0)
    mae, mfe = mae_mfe(h1, idx, horizon, side)
    years = h1.index[idx].year.to_numpy()
    p_value = p_value_binomial_two_sided(wins, n)
    return {
        "cell_id": cell_id(pair, hypothesis, vol_mult, body_pct, horizon),
        "pair": pair,
        "tf": "H1",
        "intrabar_tf": "M5",
        "hypothesis": hypothesis,
        "vol_mult": vol_mult,
        "body_pct": body_pct,
        "horizon_bars": horizon,
        "cohort": cohort,
        "n_trades": n,
        "win_rate": wr,
        "ev_pip": float(np.nanmean(pip_ret)),
        "ev_pct": float(np.nanmean(pct_ret)),
        "profit_factor": pf,
        "wilson_lower_95": wilson_lower(wins, n),
        "sharpe_annual": sharpe,
        "kelly_fraction": float(kelly),
        "max_dd_pct": max_drawdown_pct(pct_ret),
        "mae_mean_pct": float(np.nanmean(mae)) if len(mae) else 0.0,
        "mae_p5_pct": float(np.nanpercentile(mae, 5)) if len(mae) else 0.0,
        "mfe_mean_pct": float(np.nanmean(mfe)) if len(mfe) else 0.0,
        "year_flip_count": year_flip_count(years, pct_ret),
        "p_value": p_value,
        "bonferroni_pass": int(cohort == "primary_12y" and p_value < BONFERRONI_ALPHA),
        "bh_fdr_pass": 0,
        "g7_delta_incremental": None if hypothesis in {"H-A", "H-B"} else 0,
        "verdict": "REJECT",
        "period_start": period_start,
        "period_end": period_end,
        "bt_data_source": DATA_SOURCE,
        "generated_at": generated_at,
    }


def compute_grid_for_loaded(loaded: LoadedM5, cohort: str, generated_at: str) -> list[dict]:
    h1 = build_h1_features(loaded.df)
    period_start = h1.index.min().isoformat()
    period_end = h1.index.max().isoformat()
    rows: list[dict] = []
    vol_mults = VOL_MULTS_PRIMARY if cohort == "primary_12y" else VOL_MULTS_SECONDARY
    body_pcts = BODY_PCTS_PRIMARY if cohort == "primary_12y" else BODY_PCTS_SECONDARY
    bar_positions = np.arange(len(h1))
    for vol_mult in vol_mults:
        for body_pct in body_pcts:
            for hypothesis in HYPOTHESES:
                sides = signal_side(h1, hypothesis, vol_mult, body_pct).to_numpy(dtype=np.int8)
                base_valid = sides != 0
                for horizon in HORIZONS:
                    valid = base_valid & (bar_positions + 1 + horizon < len(h1))
                    idx = np.flatnonzero(valid)
                    rows.append(
                        stats_for_cell(
                            h1=h1,
                            idx=idx,
                            side=sides[idx],
                            pair=loaded.pair,
                            hypothesis=hypothesis,
                            vol_mult=vol_mult,
                            body_pct=body_pct,
                            horizon=horizon,
                            cohort=cohort,
                            period_start=period_start,
                            period_end=period_end,
                            generated_at=generated_at,
                        )
                    )
    return rows


def gate_values(row: dict) -> dict[str, bool]:
    spread = TYPICAL_SPREAD_PIP.get(row["pair"], 0.5)
    return {
        "G1": row["n_trades"] >= 30,
        "G2": (row["wilson_lower_95"] or 0.0) >= 0.50,
        "G3": (row["profit_factor"] or 0.0) >= 1.20,
        "G4": bool(row["bh_fdr_pass"]),
        "G5": row["year_flip_count"] <= 1,
        "G6": (row["ev_pip"] or 0.0) >= 1.5 * spread,
        "G7": row["hypothesis"] in {"H-A", "H-B"} or bool(row.get("g7_delta_incremental")),
    }


def classify_verdict(row: dict) -> str:
    gates = gate_values(row)
    if all(gates.values()):
        return "SHADOW_CANDIDATE"
    if gates["G1"] and gates["G2"] and gates["G3"] and gates["G4"]:
        return "CONDITIONAL"
    return "REJECT"


def apply_multiple_testing_and_verdicts(rows: list[dict]) -> None:
    primary = [row for row in rows if row["cohort"] == "primary_12y"]
    ordered = sorted((row for row in primary if math.isfinite(float(row["p_value"]))), key=lambda r: r["p_value"])
    max_pass_rank = 0
    for rank, row in enumerate(ordered, start=1):
        if row["p_value"] <= (rank / PRIMARY_M) * FDR_Q:
            max_pass_rank = rank
    pass_ids = {row["cell_id"] for row in ordered[:max_pass_rank]}
    for row in rows:
        row["bh_fdr_pass"] = int(row["cell_id"] in pass_ids and row["cohort"] == "primary_12y")
        row["bonferroni_pass"] = int(row["cohort"] == "primary_12y" and row["p_value"] < BONFERRONI_ALPHA)
        row["verdict"] = classify_verdict(row)

    by_key = {(r["pair"], r["vol_mult"], r["body_pct"], r["horizon_bars"], r["hypothesis"]): r for r in rows}
    for row in rows:
        if row["hypothesis"] not in {"H-C", "H-D"}:
            row["g7_delta_incremental"] = None
            continue
        ha = by_key.get((row["pair"], row["vol_mult"], row["body_pct"], row["horizon_bars"], "H-A"))
        row["g7_delta_incremental"] = int(ha is not None and ha["verdict"] == "REJECT")
    for row in rows:
        row["verdict"] = classify_verdict(row)


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def fmt_num(value: float | int | None, digits: int = 4) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float) and not math.isfinite(value):
        return "inf" if value > 0 else "-inf"
    return f"{float(value):.{digits}f}"


def evidence_line(row: dict) -> str:
    return (
        f"{row['cell_id']}: N={row['n_trades']} WR={fmt_num(row['win_rate'], 3)} "
        f"Wilson={fmt_num(row['wilson_lower_95'], 3)} PF={fmt_num(row['profit_factor'], 2)} "
        f"EV={fmt_num(row['ev_pip'], 2)}pip/{fmt_num(row['ev_pct'], 4)}% "
        f"p={fmt_num(row['p_value'], 6)} BH={row['bh_fdr_pass']} Bonf={row['bonferroni_pass']} "
        f"flips={row['year_flip_count']} G7={row['g7_delta_incremental']} verdict={row['verdict']}"
    )


def fail_tags(row: dict) -> list[str]:
    gates = gate_values(row)
    return [name for name, ok in gates.items() if not ok]


def build_survivors(rows: list[dict], generated_at: str) -> str:
    lines = [f"# Bigbeluga Displacement Delta Survivors\n\nGenerated: {generated_at}\n"]
    if not rows:
        lines.append("\n🔴 No SHADOW_CANDIDATE cells passed G1-G6/G7.\n")
    for row in sorted(rows, key=lambda r: (r["hypothesis"] in {"H-C", "H-D"}, r["ev_pip"]), reverse=True):
        warning = " 🟠 H-A displacement-only survivor; regime-fluke prior applies." if row["hypothesis"] == "H-A" else ""
        lines.append(f"- {evidence_line(row)}{warning}")
    lines.extend(
        [
            "\n## Verdict",
            "Survivors are shadow candidates only; no live promotion is permitted by this task.",
            "\n## Rec",
            "Promote only G7-pass H-C/H-D cells to the next commander-reviewed shadow wave.",
            "\n## 思想",
            "Test whether Bigbeluga high-volume displacement gains discrimination from intrabar M5 delta.",
            "\n## 設計欠陥",
            "M5 delta is a proxy for tick-direction volume, not true aggressor-side order flow.",
            "\n## 再設計案",
            "Future work should validate survivor stability on a six-month forward shadow sample before any live design.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_conditional(rows: list[dict], generated_at: str) -> str:
    lines = [f"# Bigbeluga Conditional Cells\n\nGenerated: {generated_at}\n"]
    if not rows:
        lines.append("\nNo CONDITIONAL cells. No cell passed G1-G4 while failing G5/G6/G7.\n")
    for row in sorted(rows, key=lambda r: r["ev_pip"], reverse=True):
        lines.append(f"- {evidence_line(row)} fail={','.join(fail_tags(row))}")
    return "\n".join(lines) + "\n"


def build_null_summary(rows: list[dict], generated_at: str) -> str:
    reject = [r for r in rows if r["verdict"] == "REJECT"]
    fail_counts = {
        "G1_N不足": sum(1 for r in reject if r["n_trades"] < 30),
        "G2_Wilson": sum(1 for r in reject if r["wilson_lower_95"] < 0.50),
        "G3_PF": sum(1 for r in reject if r["profit_factor"] < 1.20),
        "G4_BH": sum(1 for r in reject if not r["bh_fdr_pass"]),
        "G5_year": sum(1 for r in reject if r["year_flip_count"] > 1),
        "G6_cost": sum(1 for r in reject if r["ev_pip"] < 1.5 * TYPICAL_SPREAD_PIP.get(r["pair"], 0.5)),
        "G7_delta": sum(1 for r in reject if r["hypothesis"] in {"H-C", "H-D"} and not r["g7_delta_incremental"]),
    }
    lines = [f"# Bigbeluga Null Summary\n\nGenerated: {generated_at}\n"]
    lines.append(f"- total_cells={len(rows)} reject={len(reject)}")
    for key, value in fail_counts.items():
        lines.append(f"- {key}: {value}")
    lines.append("\n## Top Rejects By EV")
    for row in sorted(reject, key=lambda r: r["ev_pip"], reverse=True)[:20]:
        lines.append(f"- {evidence_line(row)} fail={','.join(fail_tags(row))}")
    return "\n".join(lines) + "\n"


def build_hypothesis_comparison(rows: list[dict], generated_at: str) -> str:
    lines = [f"# Bigbeluga Hypothesis Comparison\n\nGenerated: {generated_at}\n"]
    lines.append("| Hypothesis | Cells | Shadow | Conditional | Median EV pip | Best PF | BH pass |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for hyp in HYPOTHESES:
        subset = [r for r in rows if r["hypothesis"] == hyp]
        ev = float(np.median([r["ev_pip"] for r in subset])) if subset else 0.0
        finite_pf = [r["profit_factor"] for r in subset if math.isfinite(float(r["profit_factor"]))]
        best_pf = max(finite_pf) if finite_pf else float("inf") if any(not math.isfinite(float(r["profit_factor"])) for r in subset) else 0.0
        lines.append(
            f"| {hyp} | {len(subset)} | {sum(r['verdict']=='SHADOW_CANDIDATE' for r in subset)} "
            f"| {sum(r['verdict']=='CONDITIONAL' for r in subset)} | {fmt_num(ev, 3)} "
            f"| {fmt_num(best_pf, 2)} | {sum(r['bh_fdr_pass'] for r in subset)} |"
        )
    lines.append("\n## Delta Incremental Edge")
    for hyp in ["H-C", "H-D"]:
        subset = [r for r in rows if r["hypothesis"] == hyp]
        lines.append(f"- {hyp}: G7 PASS cells={sum(1 for r in subset if r['g7_delta_incremental'])}/{len(subset)}")
    return "\n".join(lines) + "\n"


def build_secondary_sanity(rows: list[dict], generated_at: str) -> str:
    primary_shadow = [r for r in rows if r["cohort"] == "primary_12y" and r["verdict"] == "SHADOW_CANDIDATE"]
    secondary = [r for r in rows if r["cohort"] == "secondary_1y"]
    lines = [f"# Bigbeluga Secondary Sanity\n\nGenerated: {generated_at}\n"]
    lines.append(f"- primary_survivors={len(primary_shadow)}")
    lines.append(f"- secondary_cells={len(secondary)}")
    if not primary_shadow:
        lines.append("- No primary survivor exists, so secondary reproduction is not applicable.")
    else:
        for survivor in primary_shadow:
            matches = [
                r
                for r in secondary
                if r["hypothesis"] == survivor["hypothesis"]
                and r["horizon_bars"] == survivor["horizon_bars"]
                and r["vol_mult"] == 2.0
                and r["body_pct"] == 0.50
            ]
            pos = sum(1 for r in matches if r["ev_pip"] > 0)
            lines.append(f"- {survivor['cell_id']}: secondary positive EV pairs={pos}/{len(matches)}")
    lines.append("\n## Secondary Top EV")
    for row in sorted(secondary, key=lambda r: r["ev_pip"], reverse=True)[:15]:
        lines.append(f"- {evidence_line(row)}")
    return "\n".join(lines) + "\n"


def build_summary(rows: list[dict], loaded: list[LoadedM5], generated_at: str) -> str:
    shadow = [r for r in rows if r["verdict"] == "SHADOW_CANDIDATE"]
    conditional = [r for r in rows if r["verdict"] == "CONDITIONAL"]
    reject = [r for r in rows if r["verdict"] == "REJECT"]
    lines = [f"# Bigbeluga Displacement Delta Summary\n\nGenerated: {generated_at}\n"]
    lines.append(f"- primary_cells={sum(1 for r in rows if r['cohort']=='primary_12y')}")
    lines.append(f"- secondary_cells={sum(1 for r in rows if r['cohort']=='secondary_1y')}")
    lines.append(f"- SHADOW_CANDIDATE={len(shadow)} CONDITIONAL={len(conditional)} REJECT={len(reject)}")
    lines.append(f"- G7_delta_incremental_PASS={sum(1 for r in rows if r['hypothesis'] in {'H-C','H-D'} and r['g7_delta_incremental'])}")
    lines.append("\n## Data")
    for item in loaded:
        lines.append(f"- {item.pair}: {item.source_path} schema={item.schema} rows={len(item.df)}")
    lines.append("\n## Top H-C/H-D")
    for row in sorted([r for r in rows if r["hypothesis"] in {"H-C", "H-D"}], key=lambda r: r["ev_pip"], reverse=True)[:10]:
        lines.append(f"- {evidence_line(row)}")
    return "\n".join(lines) + "\n"


def build_verdict(rows: list[dict], generated_at: str) -> str:
    shadow = [r for r in rows if r["verdict"] == "SHADOW_CANDIDATE"]
    delta_shadow = [r for r in shadow if r["hypothesis"] in {"H-C", "H-D"} and r["g7_delta_incremental"]]
    lines = [f"# Bigbeluga Verdict\n\nGenerated: {generated_at}\n"]
    if len(delta_shadow) >= 3:
        overall = "GO for commander-reviewed Wave 1 shadow observation of G7-pass H-C/H-D cells."
    elif shadow:
        overall = "NO-GO for Bigbeluga delta edge; only non-delta or insufficient-delta evidence survived."
    else:
        overall = "NO-GO. Hypothesis kill under the pre-registered gates."
    lines.append(f"Overall: {overall}")
    lines.append(f"- shadow_candidates={len(shadow)}")
    lines.append(f"- g7_delta_shadow_candidates={len(delta_shadow)}")
    for row in sorted(delta_shadow, key=lambda r: r["ev_pip"], reverse=True):
        lines.append(f"- promote_review: {evidence_line(row)}")
    return "\n".join(lines) + "\n"


def build_final_md(rows: list[dict], generated_at: str) -> str:
    primary = [r for r in rows if r["cohort"] == "primary_12y"]
    secondary = [r for r in rows if r["cohort"] == "secondary_1y"]
    shadow = [r for r in rows if r["verdict"] == "SHADOW_CANDIDATE"]
    conditional = [r for r in rows if r["verdict"] == "CONDITIONAL"]
    reject = [r for r in rows if r["verdict"] == "REJECT"]
    top_delta = sorted(
        [r for r in rows if r["hypothesis"] in {"H-C", "H-D"} and r["verdict"] == "SHADOW_CANDIDATE"],
        key=lambda r: r["ev_pip"],
        reverse=True,
    )[:5]
    if len(top_delta) < 5:
        top_delta = sorted([r for r in rows if r["hypothesis"] in {"H-C", "H-D"}], key=lambda r: r["ev_pip"], reverse=True)[:5]
    lines = [f"# Bigbeluga Displacement Delta Final\n\nGenerated: {generated_at}\n"]
    lines.append(f"- 投入 cell 数: primary={len(primary)}, secondary={len(secondary)}, total={len(rows)}")
    lines.append(f"- SHADOW_CANDIDATE={len(shadow)}")
    lines.append(f"- CONDITIONAL={len(conditional)}")
    lines.append(f"- REJECT={len(reject)}")
    lines.append(
        f"- G7 (delta incremental) PASS 数={sum(1 for r in rows if r['hypothesis'] in {'H-C','H-D'} and r['g7_delta_incremental'])}"
    )
    lines.append("\n## Top 5 H-C/H-D evidence (no survivors; top rejected shown)")
    for row in top_delta:
        lines.append(f"- {evidence_line(row)}")
    return "\n".join(lines) + "\n"


def write_reports(out_dir: Path, rows: list[dict], loaded: list[LoadedM5], generated_at: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / "grid_full.csv", rows)
    (out_dir / "survivors.md").write_text(
        build_survivors([r for r in rows if r["verdict"] == "SHADOW_CANDIDATE"], generated_at), encoding="utf-8"
    )
    (out_dir / "conditional.md").write_text(
        build_conditional([r for r in rows if r["verdict"] == "CONDITIONAL"], generated_at), encoding="utf-8"
    )
    (out_dir / "null_summary.md").write_text(build_null_summary(rows, generated_at), encoding="utf-8")
    (out_dir / "hypothesis_comparison.md").write_text(build_hypothesis_comparison(rows, generated_at), encoding="utf-8")
    (out_dir / "secondary_sanity.md").write_text(build_secondary_sanity(rows, generated_at), encoding="utf-8")
    (out_dir / "SUMMARY.md").write_text(build_summary(rows, loaded, generated_at), encoding="utf-8")
    (out_dir / "verdict.md").write_text(build_verdict(rows, generated_at), encoding="utf-8")
    (ROOT / "final.md").write_text(build_final_md(rows, generated_at), encoding="utf-8")


def run_grid(cache_dir: Path, out_dir: Path, db_path: Path) -> list[dict]:
    generated_at = datetime.now(timezone.utc).isoformat()
    loaded: list[LoadedM5] = []
    rows: list[dict] = []
    for pair in PRIMARY_PAIRS:
        item = load_m5(cache_dir, pair)
        loaded.append(item)
        rows.extend(compute_grid_for_loaded(item, "primary_12y", generated_at))
    for pair in SECONDARY_PAIRS:
        item = load_m5(cache_dir, pair)
        loaded.append(item)
        rows.extend(compute_grid_for_loaded(item, "secondary_1y", generated_at))
    apply_multiple_testing_and_verdicts(rows)
    write_reports(out_dir, rows, loaded, generated_at)
    with connect(db_path) as conn:
        replace_cells(conn, rows)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    rows = run_grid(args.cache_dir, args.out_dir, args.db)
    counts = {verdict: sum(1 for row in rows if row["verdict"] == verdict) for verdict in ["SHADOW_CANDIDATE", "CONDITIONAL", "REJECT"]}
    print(
        f"wrote {len(rows)} cells to {args.out_dir} and {args.db} "
        f"shadow={counts['SHADOW_CANDIDATE']} conditional={counts['CONDITIONAL']} reject={counts['REJECT']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
