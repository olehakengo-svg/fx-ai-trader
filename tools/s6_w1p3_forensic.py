#!/usr/bin/env python3
"""S6 W1P3 forensic audit for primary chart-pattern geometry."""
from __future__ import annotations

import argparse
import math
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


PIP_SIZE = 0.01
PRIMARY_PATTERNS: tuple[tuple[str, str], ...] = (
    ("ascending_triangle", "BUY"),
    ("descending_triangle", "SELL"),
    ("rising_wedge", "BUY"),
    ("falling_wedge", "SELL"),
    ("double_bottom", "BUY"),
    ("double_top", "SELL"),
    ("inverse_head_shoulders", "BUY"),
    ("head_shoulders", "SELL"),
)
FRICTIONS = (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--signals", required=True)
    parser.add_argument("--parquet", required=True)
    parser.add_argument("--output-report", required=True)
    parser.add_argument("--spread-pip", type=float, default=1.5)
    parser.add_argument("--slippage-pip", type=float, default=0.3)
    return parser.parse_args()


def pf_from_pnl(pnl: np.ndarray) -> float:
    wins = pnl[pnl > 0.0]
    losses = pnl[pnl < 0.0]
    gp = float(wins.sum()) if wins.size else 0.0
    gl = float(-losses.sum()) if losses.size else 0.0
    if gl == 0.0:
        return math.inf if gp > 0.0 else 0.0
    return gp / gl


def fmt(value: float | None, digits: int = 3) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, float) and math.isinf(value):
        return "inf"
    if isinstance(value, float) and math.isnan(value):
        return "nan"
    return f"{float(value):.{digits}f}"


def load_rows(db_path: Path) -> pd.DataFrame:
    where = " OR ".join(["(s.pattern_name = ? AND s.direction = ?)"] * len(PRIMARY_PATTERNS))
    params: list[str] = []
    for pattern, direction in PRIMARY_PATTERNS:
        params.extend([pattern, direction])
    with sqlite3.connect(db_path) as con:
        df = pd.read_sql_query(
            f"""
            SELECT
                s.id AS signal_id,
                s.pattern_name,
                s.direction,
                s.signal_ts,
                s.entry_px,
                s.sl_px,
                s.tp_px,
                s.confidence_score,
                o.outcome,
                o.bars_held,
                o.pnl_pips
            FROM chart_pattern_signals s
            JOIN chart_pattern_outcomes o ON o.signal_id = s.id
            WHERE {where}
            ORDER BY s.signal_ts, s.id
            """,
            con,
            params=params,
        )
    df["signal_ts"] = pd.to_datetime(df["signal_ts"], utc=True)
    sign = np.where(df["direction"].to_numpy() == "BUY", 1.0, -1.0)
    df["tp_dist_pip"] = (df["tp_px"] - df["entry_px"]) * sign / PIP_SIZE
    df["sl_dist_pip"] = (df["entry_px"] - df["sl_px"]) * sign / PIP_SIZE
    df["rr"] = df["tp_dist_pip"] / df["sl_dist_pip"]
    return df


def load_atr(parquet_path: Path) -> pd.Series:
    bars = pd.read_parquet(parquet_path)
    bars = bars.rename(columns={c: c.lower() for c in bars.columns}).sort_index()
    bars.index = pd.to_datetime(bars.index, utc=True)
    prev_close = bars["close"].shift(1)
    tr = pd.concat(
        [
            bars["high"] - bars["low"],
            (bars["high"] - prev_close).abs(),
            (bars["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(14, min_periods=14).mean()


def add_regime(df: pd.DataFrame, atr: pd.Series) -> pd.DataFrame:
    idx = atr.index.searchsorted(df["signal_ts"].to_numpy(), side="right") - 1
    atr_values = np.full(len(df), np.nan, dtype=np.float64)
    valid = idx >= 0
    atr_values[valid] = atr.to_numpy()[idx[valid]]
    df = df.copy()
    df["atr14"] = atr_values
    median = float(np.nanmedian(atr_values))
    df["regime"] = np.where(df["atr14"] <= median, "low_vol", "high_vol")
    return df


def markdown_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return lines


def rr_distribution(df: pd.DataFrame) -> list[str]:
    rows = []
    for pattern, direction in PRIMARY_PATTERNS:
        g = df[(df["pattern_name"] == pattern) & (df["direction"] == direction)]
        rows.append(
            [
                pattern,
                direction,
                str(len(g)),
                fmt(float(g["tp_dist_pip"].median())),
                fmt(float(g["tp_dist_pip"].mean())),
                fmt(float(g["tp_dist_pip"].std(ddof=1))),
                fmt(float(g["sl_dist_pip"].median())),
                fmt(float(g["sl_dist_pip"].mean())),
                fmt(float(g["sl_dist_pip"].std(ddof=1))),
                fmt(float(g["rr"].median())),
                fmt(float(g["rr"].mean())),
            ]
        )
    return markdown_table(
        [
            "pattern",
            "dir",
            "n",
            "tp_med",
            "tp_mean",
            "tp_sd",
            "sl_med",
            "sl_mean",
            "sl_sd",
            "rr_med",
            "rr_mean",
        ],
        rows,
    )


def friction_sensitivity(df: pd.DataFrame) -> list[str]:
    valid = df[df["outcome"] != "DM"].copy()
    rows = []
    for pattern, direction in PRIMARY_PATTERNS:
        g = valid[(valid["pattern_name"] == pattern) & (valid["direction"] == direction)]
        raw = g["pnl_pips"].to_numpy(dtype=np.float64)
        pfs = [pf_from_pnl(raw - f) for f in FRICTIONS]
        cross = "none"
        for left_f, right_f, left_pf, right_pf in zip(FRICTIONS, FRICTIONS[1:], pfs, pfs[1:]):
            if left_pf >= 1.0 and right_pf <= 1.0:
                if left_pf == right_pf:
                    cross = fmt(left_f)
                else:
                    frac = (left_pf - 1.0) / (left_pf - right_pf)
                    cross = fmt(left_f + frac * (right_f - left_f))
                break
        rows.append([pattern, direction] + [fmt(v) for v in pfs] + [cross])
    return markdown_table(["pattern", "dir"] + [f"{f:.1f}" for f in FRICTIONS] + ["PF=1 cross pip"], rows)


def time_to_resolution(df: pd.DataFrame) -> list[str]:
    rows = []
    for pattern, direction in PRIMARY_PATTERNS:
        g = df[(df["pattern_name"] == pattern) & (df["direction"] == direction)]
        row = [pattern, direction]
        for outcome in ("TP", "SL"):
            bars = g.loc[g["outcome"] == outcome, "bars_held"].to_numpy(dtype=np.float64)
            if bars.size:
                q25, med, q75 = np.percentile(bars, [25, 50, 75])
                row.extend([str(int(bars.size)), fmt(q25, 1), fmt(med, 1), fmt(q75, 1)])
            else:
                row.extend(["0", "nan", "nan", "nan"])
        rows.append(row)
    return markdown_table(
        ["pattern", "dir", "tp_n", "tp_p25", "tp_med", "tp_p75", "sl_n", "sl_p25", "sl_med", "sl_p75"],
        rows,
    )


def regime_split(df: pd.DataFrame, cost_pips: float) -> list[str]:
    valid = df[df["outcome"] != "DM"].copy()
    rows = []
    for pattern, direction in PRIMARY_PATTERNS:
        g = valid[(valid["pattern_name"] == pattern) & (valid["direction"] == direction)]
        row = [pattern, direction]
        for regime in ("low_vol", "high_vol"):
            r = g[g["regime"] == regime]
            row.extend([str(len(r)), fmt(pf_from_pnl(r["pnl_pips"].to_numpy(dtype=np.float64) - cost_pips))])
        rows.append(row)
    return markdown_table(["pattern", "dir", "low_n", "low_pf", "high_n", "high_pf"], rows)


def quality_filter(df: pd.DataFrame, cost_pips: float) -> list[str]:
    valid = df[df["outcome"] != "DM"].copy()
    rows = []
    labels = [
        ("Top 25%", 0.75, 1.01),
        ("25-50%", 0.50, 0.75),
        ("50-75%", 0.25, 0.50),
        ("Bottom 25%", -0.01, 0.25),
    ]
    for pattern, direction in PRIMARY_PATTERNS:
        g = valid[(valid["pattern_name"] == pattern) & (valid["direction"] == direction)].copy()
        q = g["confidence_score"].quantile([0.25, 0.50, 0.75]).to_dict()
        row = [pattern, direction]
        for _label, lo_q, hi_q in labels:
            lo = -math.inf if lo_q < 0 else float(g["confidence_score"].quantile(lo_q))
            hi = math.inf if hi_q > 1 else float(g["confidence_score"].quantile(hi_q))
            if hi_q > 1:
                part = g[g["confidence_score"] >= lo]
            elif lo_q < 0:
                part = g[g["confidence_score"] < hi]
            else:
                part = g[(g["confidence_score"] >= lo) & (g["confidence_score"] < hi)]
            row.extend([str(len(part)), fmt(pf_from_pnl(part["pnl_pips"].to_numpy(dtype=np.float64) - cost_pips))])
        rows.append(row)
    return markdown_table(
        ["pattern", "dir", "top_n", "top_pf", "q2_n", "q2_pf", "q3_n", "q3_pf", "bottom_n", "bottom_pf"],
        rows,
    )


def yearly_pnl(df: pd.DataFrame, cost_pips: float) -> list[str]:
    valid = df[df["outcome"] != "DM"].copy()
    valid["year"] = valid["signal_ts"].dt.year
    years = list(range(int(valid["year"].min()), int(valid["year"].max()) + 1))
    rows = []
    for pattern, direction in PRIMARY_PATTERNS:
        g = valid[(valid["pattern_name"] == pattern) & (valid["direction"] == direction)]
        row = [pattern, direction]
        for year in years:
            y = g[g["year"] == year]
            pnl = float((y["pnl_pips"] - cost_pips).sum()) if len(y) else 0.0
            row.append(fmt(pnl, 1))
        rows.append(row)
    return markdown_table(["pattern", "dir"] + [str(y) for y in years], rows)


def main() -> int:
    args = parse_args()
    cost_pips = args.spread_pip + 2.0 * args.slippage_pip
    df = load_rows(Path(args.signals))
    df = add_regime(df, load_atr(Path(args.parquet)))

    sections: list[str] = [
        "# S6 W1P3 Forensic Report",
        "",
        f"- signals: {len(df)} primary rows",
        f"- valid non-DM outcomes: {int((df['outcome'] != 'DM').sum())}",
        f"- friction model for non-sensitivity tables: {cost_pips:.1f} pip",
        "",
        "## 1. R:R Distance Distribution",
        *rr_distribution(df),
        "",
        "## 2. Friction Sensitivity Curve",
        *friction_sensitivity(df),
        "",
        "## 3. Time-to-Resolution Distribution",
        *time_to_resolution(df),
        "",
        "## 4. ATR(14) Regime Split",
        *regime_split(df, cost_pips),
        "",
        "## 5. Confidence Score Quartiles",
        *quality_filter(df, cost_pips),
        "",
        "## 6. Yearly PnL",
        *yearly_pnl(df, cost_pips),
        "",
    ]
    output = Path(args.output_report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(sections), encoding="utf-8")
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
