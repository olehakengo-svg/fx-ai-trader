#!/usr/bin/env python3
"""S6 Wave 2a diagnosis utilities.

Read-only with respect to frozen Wave 2 BT tables. The only DB writes are the
diagnosis snapshot tables requested by the W2a task.
"""
from __future__ import annotations

import argparse
import dataclasses
import math
import sqlite3
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Iterable, Sequence

import pandas as pd
from scipy.stats import binomtest

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.s6_chart_pattern_bt import SPREAD_PIPS, PIP_FACTOR, profit_factor, wilson_lower


BONFERRONI_ALPHA = 0.05
RR_MULTIPLIERS = (0.50, 0.75, 1.00, 1.25, 1.50)
HOUR_BUCKETS = (
    ("Asia", 0, 8),
    ("London", 8, 12),
    ("London_NY_overlap", 12, 16),
    ("NY+late", 16, 24),
)

SQLITE_DDL = """
CREATE TABLE IF NOT EXISTS chart_pattern_bt_spread_profile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pair TEXT NOT NULL,
    hour_utc INTEGER NOT NULL CHECK (hour_utc BETWEEN 0 AND 23),
    n_observations INTEGER NOT NULL,
    avg_round_trip_spread_pips REAL NOT NULL,
    median_round_trip_spread_pips REAL,
    p95_round_trip_spread_pips REAL,
    source TEXT NOT NULL,
    snapshot_ts TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(pair, hour_utc, source)
);

CREATE TABLE IF NOT EXISTS chart_pattern_w2a_diagnosis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_id INTEGER NOT NULL,
    pattern_name TEXT NOT NULL,
    pair TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    bt_run_id TEXT NOT NULL,
    axis TEXT NOT NULL,
    sub_key TEXT,
    n INTEGER NOT NULL,
    wr REAL NOT NULL,
    ev_pips REAL NOT NULL,
    pf REAL,
    wilson_lo_95 REAL NOT NULL,
    bev_wr REAL NOT NULL,
    bonferroni_p REAL NOT NULL,
    bonferroni_alpha REAL NOT NULL,
    bonferroni_m INTEGER NOT NULL,
    kelly REAL NOT NULL,
    proposed_verdict TEXT NOT NULL CHECK (proposed_verdict IN ('PROMOTE','SHADOW','REJECT','INSUFFICIENT')),
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(pattern_id, bt_run_id, axis, sub_key)
);
"""


@dataclass(frozen=True)
class SpreadHour:
    hour_utc: int
    n_observations: int
    avg_round_trip_spread_pips: float
    median_round_trip_spread_pips: float
    p95_round_trip_spread_pips: float
    source: str = "demo_trades_empirical"


@dataclass(frozen=True)
class DiagnosisRow:
    pattern_id: int
    pattern_name: str
    pair: str
    timeframe: str
    bt_run_id: str
    axis: str
    sub_key: str
    n: int
    wr: float
    ev_pips: float
    pf: float | None
    wilson_lo_95: float
    bev_wr: float
    bonferroni_p: float
    bonferroni_alpha: float
    bonferroni_m: int
    kelly: float
    proposed_verdict: str
    notes: str = ""


def percentile(values: Sequence[float], q: float) -> float:
    vals = sorted(float(v) for v in values)
    if not vals:
        return 0.0
    if len(vals) == 1:
        return vals[0]
    pos = (len(vals) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return vals[lo]
    return vals[lo] + (vals[hi] - vals[lo]) * (pos - lo)


def hour_bucket(hour: int) -> str:
    for name, start, end in HOUR_BUCKETS:
        if start <= hour < end:
            return name
    raise ValueError(f"hour out of range: {hour}")


def bonferroni_m(axis: str) -> int:
    return {
        "spread_adj": 12,
        "rr_optimal": 12 * len(RR_MULTIPLIERS),
        "hour_bucket": 12 * len(HOUR_BUCKETS),
        "pivot_quality": 12 * 4,
        "regime": 12 * 2,
        "exit_reason": 12,
        "mafe_mfe": 12,
        "early_hit": 12,
        "triple_bottom_wf1": 1,
    }[axis]


def ensure_schema(con: sqlite3.Connection) -> None:
    con.executescript(SQLITE_DDL)


def build_spread_profile(demo_db_path: Path, pair: str) -> list[SpreadHour]:
    with sqlite3.connect(demo_db_path) as con:
        rows = con.execute(
            """
            SELECT
                CAST(strftime('%H', entry_time) AS INTEGER) AS hour_utc,
                spread_at_entry + COALESCE(spread_at_exit, spread_at_entry) AS rt_spread
            FROM demo_trades
            WHERE instrument=?
              AND spread_at_entry > 0
              AND entry_time IS NOT NULL
            """,
            (pair,),
        ).fetchall()
    by_hour: dict[int, list[float]] = defaultdict(list)
    by_bucket: dict[str, list[float]] = defaultdict(list)
    all_values: list[float] = []
    for hour, spread in rows:
        if hour is None or spread is None:
            continue
        value = float(spread)
        h = int(hour)
        by_hour[h].append(value)
        by_bucket[hour_bucket(h)].append(value)
        all_values.append(value)
    if not all_values:
        raise ValueError(f"no empirical spread samples for {pair}")

    global_med = float(median(all_values))
    profile: list[SpreadHour] = []
    for hour in range(24):
        vals = by_hour.get(hour, [])
        fallback_vals = by_bucket.get(hour_bucket(hour), []) or all_values
        calc_vals = vals or fallback_vals
        profile.append(
            SpreadHour(
                hour_utc=hour,
                n_observations=len(vals),
                avg_round_trip_spread_pips=sum(calc_vals) / len(calc_vals) if calc_vals else global_med,
                median_round_trip_spread_pips=float(median(calc_vals)) if calc_vals else global_med,
                p95_round_trip_spread_pips=percentile(calc_vals, 0.95) if calc_vals else global_med,
            )
        )
    return profile


def load_trades(chart_db_path: Path, pair: str, timeframe: str, bt_run_id: str) -> pd.DataFrame:
    with sqlite3.connect(chart_db_path) as con:
        df = pd.read_sql_query(
            """
            SELECT
                t.id AS trade_row_id,
                t.signal_id,
                t.pattern_id,
                t.pattern_name,
                t.direction,
                t.pair,
                t.timeframe,
                t.entry_ts,
                t.entry_px,
                t.exit_ts,
                t.exit_px,
                t.exit_reason,
                t.pnl_pips,
                t.mafe_pips,
                t.mfe_pips,
                t.hold_bars,
                t.bt_run_id,
                s.sl_px,
                s.tp_px,
                s.pattern_height_atr,
                s.atr_at_detection
            FROM chart_pattern_bt_trades t
            JOIN chart_pattern_signals s ON s.id = t.signal_id
            WHERE t.pair=? AND t.timeframe=? AND t.bt_run_id=?
            ORDER BY t.entry_ts, t.id
            """,
            con,
            params=(pair, timeframe, bt_run_id),
        )
    if df.empty:
        raise ValueError(f"no BT trades for {pair} {timeframe} {bt_run_id}")
    df["entry_dt"] = pd.to_datetime(df["entry_ts"], utc=True)
    df["entry_hour"] = df["entry_dt"].dt.hour
    df["raw_pnl_pips"] = df["pnl_pips"] + SPREAD_PIPS
    df["tp_dist_pips"] = (df["tp_px"] - df["entry_px"]).abs() * PIP_FACTOR
    df["sl_dist_pips"] = (df["entry_px"] - df["sl_px"]).abs() * PIP_FACTOR
    df["pattern_height_pips"] = df["tp_dist_pips"]
    return df


def apply_spread_adjustment(trades: pd.DataFrame, profile: Sequence[SpreadHour]) -> pd.DataFrame:
    by_hour = {p.hour_utc: p.avg_round_trip_spread_pips for p in profile}
    out = trades.copy()
    if "raw_pnl_pips" not in out.columns:
        out["raw_pnl_pips"] = out["pnl_pips"] + SPREAD_PIPS
    out["empirical_spread_pips"] = out["entry_hour"].map(by_hour).astype(float)
    out["pnl_adjusted"] = out["raw_pnl_pips"] - out["empirical_spread_pips"]
    return out


def payoff_bev(avg_win: float, avg_loss: float) -> float:
    denom = avg_win + avg_loss
    if denom <= 0:
        return 1.0
    return min(1.0, max(0.0, avg_loss / denom))


def stats_for_pnls(pnls: Iterable[float], bonf_m: int) -> tuple[int, float, float, float | None, float, float, float, float, str]:
    vals = [float(v) for v in pnls]
    n = len(vals)
    if n == 0:
        return 0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 0.0, "INSUFFICIENT"
    wins = sum(1 for v in vals if v > 0)
    wr = wins / n
    win_vals = [v for v in vals if v > 0]
    loss_vals = [v for v in vals if v < 0]
    avg_win = sum(win_vals) / len(win_vals) if win_vals else 0.0
    avg_loss = abs(sum(loss_vals) / len(loss_vals)) if loss_vals else 0.0
    pf = profit_factor(vals)
    bev = payoff_bev(avg_win, avg_loss)
    p = float(binomtest(wins, n, min(max(bev, 1e-12), 1 - 1e-12), alternative="greater").pvalue)
    payoff = avg_win / avg_loss if avg_loss > 0 else math.inf
    kelly = wr - (1 - wr) / payoff if math.isfinite(payoff) and payoff > 0 else (wr if payoff == math.inf else 0.0)
    wilson = wilson_lower(wins, n)
    ev = sum(vals) / n
    verdict = propose_verdict(n, ev, pf, wilson, bev, p, bonf_m, kelly)
    return n, wr, ev, pf, wilson, bev, p, kelly, verdict


def propose_verdict(n: int, ev: float, pf: float | None, wilson: float, bev: float, p_value: float, bonf_m: int, kelly: float) -> str:
    if n < 100:
        return "INSUFFICIENT"
    pf_value = 0.0 if pf is None or not math.isfinite(pf) else pf
    alpha = BONFERRONI_ALPHA / bonf_m
    core = ev > 0 and pf_value >= 1.3 and wilson > bev and p_value < alpha and kelly > 0
    if not core:
        return "REJECT"
    return "PROMOTE" if kelly >= 0.05 else "SHADOW"


def row_from_group(group: pd.DataFrame, pnl_col: str, axis: str, sub_key: str, notes: str = "") -> DiagnosisRow:
    bonf_m = bonferroni_m(axis)
    n, wr, ev, pf, wilson, bev, p, kelly, verdict = stats_for_pnls(group[pnl_col].tolist(), bonf_m)
    first = group.iloc[0]
    return DiagnosisRow(
        pattern_id=int(first["pattern_id"]),
        pattern_name=str(first["pattern_name"]),
        pair=str(first["pair"]),
        timeframe=str(first["timeframe"]),
        bt_run_id=str(first["bt_run_id"]),
        axis=axis,
        sub_key=sub_key,
        n=n,
        wr=wr,
        ev_pips=ev,
        pf=pf,
        wilson_lo_95=wilson,
        bev_wr=bev,
        bonferroni_p=p,
        bonferroni_alpha=BONFERRONI_ALPHA / bonf_m,
        bonferroni_m=bonf_m,
        kelly=kelly,
        proposed_verdict=verdict,
        notes=notes,
    )


def hypothetical_rr_pnl(row: pd.Series, multiplier: float) -> float:
    tp = float(row["pattern_height_pips"]) * multiplier
    sl = float(row["sl_dist_pips"])
    mfe = float(row["mfe_pips"])
    mafe = float(row["mafe_pips"])
    if mafe >= sl:
        gross = -sl
    elif mfe >= tp:
        gross = tp
    else:
        gross = float(row["raw_pnl_pips"])
    return gross - SPREAD_PIPS


def add_regime_tags(trades: pd.DataFrame, parquet_path: Path | None) -> pd.DataFrame:
    out = trades.copy()
    if parquet_path is None or not parquet_path.exists():
        out["d1_regime"] = "UNKNOWN"
        return out
    bars = pd.read_parquet(parquet_path)
    bars = bars.rename(columns={c: c.lower() for c in bars.columns})
    bars.index = pd.to_datetime(bars.index, utc=True)
    daily = bars["close"].resample("1D").last().dropna().to_frame("d1_close")
    daily["d1_ema200"] = daily["d1_close"].ewm(span=200, adjust=False, min_periods=200).mean()
    daily["d1_regime"] = ["BULL" if c > e else "BEAR" if c <= e else "UNKNOWN" for c, e in zip(daily["d1_close"], daily["d1_ema200"])]
    keyed = daily[["d1_regime"]].reset_index().rename(columns={daily.index.name or "index": "day_ts"})
    keyed.columns = ["day_ts", "d1_regime"]
    sorted_trades = out.sort_values("entry_dt").reset_index(drop=False)
    merged = pd.merge_asof(sorted_trades, keyed.sort_values("day_ts"), left_on="entry_dt", right_on="day_ts", direction="backward")
    merged = merged.sort_values("index").drop(columns=["index", "day_ts"])
    return merged.reset_index(drop=True)


def build_diagnosis_rows(trades: pd.DataFrame, profile: Sequence[SpreadHour], parquet_path: Path | None = None) -> tuple[list[DiagnosisRow], dict[str, object]]:
    adjusted = apply_spread_adjustment(trades, profile)
    rows: list[DiagnosisRow] = []
    diagnostics: dict[str, object] = {}

    for _, group in adjusted.groupby("pattern_id", sort=True):
        rows.append(row_from_group(group, "pnl_adjusted", "spread_adj", "all", "flat 1.5p removed; empirical hour spread applied"))

    exit_notes = {}
    for pattern_id, group in adjusted.groupby("pattern_id", sort=True):
        counts = Counter(group["exit_reason"].tolist())
        n = len(group)
        timeout = counts.get("TIMEOUT", 0) / n
        sl = counts.get("SL", 0) / n
        exit_notes[int(pattern_id)] = dict(counts)
        note = f"TP={counts.get('TP',0)/n:.1%}; SL={sl:.1%}; TIMEOUT={timeout:.1%}"
        rows.append(row_from_group(group, "pnl_pips", "exit_reason", "distribution", note))
    diagnostics["exit_reason"] = exit_notes

    mafe_notes = {}
    for pattern_id, group in adjusted.groupby("pattern_id", sort=True):
        mafe = group["mafe_pips"]
        mfe = group["mfe_pips"]
        note = (
            f"MAFE p25/med/p75/p95={mafe.quantile(.25):.2f}/{mafe.median():.2f}/{mafe.quantile(.75):.2f}/{mafe.quantile(.95):.2f}; "
            f"MFE p25/med/p75/p95={mfe.quantile(.25):.2f}/{mfe.median():.2f}/{mfe.quantile(.75):.2f}/{mfe.quantile(.95):.2f}; "
            f"avgTP={group['tp_dist_pips'].mean():.2f}; avgSL={group['sl_dist_pips'].mean():.2f}"
        )
        mafe_notes[int(pattern_id)] = note
        rows.append(row_from_group(group, "pnl_pips", "mafe_mfe", "distribution", note))
    diagnostics["mafe_mfe"] = mafe_notes

    rr_summary: dict[int, list[DiagnosisRow]] = defaultdict(list)
    for mult in RR_MULTIPLIERS:
        col = f"rr_{mult:.2f}"
        adjusted[col] = adjusted.apply(hypothetical_rr_pnl, axis=1, multiplier=mult)
        for _, group in adjusted.groupby("pattern_id", sort=True):
            row = row_from_group(group, col, "rr_optimal", f"rr={mult:.2f}", "hypothetical from existing MAFE/MFE; SL fixed")
            rows.append(row)
            rr_summary[row.pattern_id].append(row)
    diagnostics["rr_best"] = {pid: max(vals, key=lambda r: r.ev_pips) for pid, vals in rr_summary.items()}

    adjusted["hour_bucket"] = adjusted["entry_hour"].map(hour_bucket)
    for (_, bucket), group in adjusted.groupby(["pattern_id", "hour_bucket"], sort=True):
        rows.append(row_from_group(group, "pnl_pips", "hour_bucket", str(bucket), "UTC bucket"))

    adjusted["height_q"] = adjusted.groupby("pattern_id")["pattern_height_atr"].transform(lambda s: pd.qcut(s.rank(method="first"), 4, labels=["q1", "q2", "q3", "q4"]))
    for (_, q), group in adjusted.groupby(["pattern_id", "height_q"], sort=True, observed=True):
        rows.append(row_from_group(group, "pnl_pips", "pivot_quality", str(q), "pattern_height_atr quartile"))

    regime_df = add_regime_tags(adjusted, parquet_path)
    regime_df = regime_df[regime_df["d1_regime"].isin(["BULL", "BEAR"])]
    if not regime_df.empty:
        for (_, regime), group in regime_df.groupby(["pattern_id", "d1_regime"], sort=True):
            aligned = ((group["direction"] == "BUY") & (group["d1_regime"] == "BULL")) | ((group["direction"] == "SELL") & (group["d1_regime"] == "BEAR"))
            note = f"D1 EMA200 regime; direction_aligned={aligned.mean():.1%}"
            rows.append(row_from_group(group, "pnl_pips", "regime", str(regime), note))

    for _, group in adjusted.groupby("pattern_id", sort=True):
        tp_hold = group.loc[group["exit_reason"] == "TP", "hold_bars"]
        sl_hold = group.loc[group["exit_reason"] == "SL", "hold_bars"]
        note = f"median_hold_bars TP={tp_hold.median() if not tp_hold.empty else math.nan:.1f}; SL={sl_hold.median() if not sl_hold.empty else math.nan:.1f}"
        rows.append(row_from_group(group, "pnl_pips", "early_hit", "hold_bars", note))

    wf1_tb = adjusted[(adjusted["pattern_name"] == "triple_bottom") & (adjusted["entry_dt"] >= pd.Timestamp("2019-01-01", tz="UTC")) & (adjusted["entry_dt"] < pd.Timestamp("2021-01-01", tz="UTC"))]
    if not wf1_tb.empty:
        rows.append(row_from_group(wf1_tb, "pnl_pips", "triple_bottom_wf1", "2019-2020", "VIX/DXY source unavailable locally; cluster limited to WF1 aggregate"))

    return rows, diagnostics


def write_spread_profile(chart_db_path: Path, pair: str, profile: Sequence[SpreadHour]) -> None:
    with sqlite3.connect(chart_db_path) as con:
        ensure_schema(con)
        con.executemany(
            """
            INSERT INTO chart_pattern_bt_spread_profile (
                pair, hour_utc, n_observations, avg_round_trip_spread_pips,
                median_round_trip_spread_pips, p95_round_trip_spread_pips, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(pair, hour_utc, source) DO UPDATE SET
                n_observations=excluded.n_observations,
                avg_round_trip_spread_pips=excluded.avg_round_trip_spread_pips,
                median_round_trip_spread_pips=excluded.median_round_trip_spread_pips,
                p95_round_trip_spread_pips=excluded.p95_round_trip_spread_pips,
                snapshot_ts=datetime('now')
            """,
            [
                (
                    pair,
                    p.hour_utc,
                    p.n_observations,
                    p.avg_round_trip_spread_pips,
                    p.median_round_trip_spread_pips,
                    p.p95_round_trip_spread_pips,
                    p.source,
                )
                for p in profile
            ],
        )
        con.commit()


def write_diagnosis_rows(chart_db_path: Path, rows: Sequence[DiagnosisRow]) -> None:
    with sqlite3.connect(chart_db_path) as con:
        ensure_schema(con)
        con.executemany(
            """
            INSERT INTO chart_pattern_w2a_diagnosis (
                pattern_id, pattern_name, pair, timeframe, bt_run_id, axis, sub_key, n, wr,
                ev_pips, pf, wilson_lo_95, bev_wr, bonferroni_p, bonferroni_alpha,
                bonferroni_m, kelly, proposed_verdict, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(pattern_id, bt_run_id, axis, sub_key) DO UPDATE SET
                pattern_name=excluded.pattern_name,
                pair=excluded.pair,
                timeframe=excluded.timeframe,
                n=excluded.n,
                wr=excluded.wr,
                ev_pips=excluded.ev_pips,
                pf=excluded.pf,
                wilson_lo_95=excluded.wilson_lo_95,
                bev_wr=excluded.bev_wr,
                bonferroni_p=excluded.bonferroni_p,
                bonferroni_alpha=excluded.bonferroni_alpha,
                bonferroni_m=excluded.bonferroni_m,
                kelly=excluded.kelly,
                proposed_verdict=excluded.proposed_verdict,
                notes=excluded.notes,
                created_at=datetime('now')
            """,
            [
                (
                    r.pattern_id,
                    r.pattern_name,
                    r.pair,
                    r.timeframe,
                    r.bt_run_id,
                    r.axis,
                    r.sub_key,
                    r.n,
                    r.wr,
                    r.ev_pips,
                    None if r.pf is None or math.isinf(r.pf) else r.pf,
                    r.wilson_lo_95,
                    r.bev_wr,
                    r.bonferroni_p,
                    r.bonferroni_alpha,
                    r.bonferroni_m,
                    r.kelly,
                    r.proposed_verdict,
                    r.notes,
                )
                for r in rows
            ],
        )
        con.commit()


def run_diagnosis(chart_db_path: Path, demo_db_path: Path, pair: str, timeframe: str, bt_run_id: str, parquet_path: Path | None, write_db: bool = True) -> tuple[list[SpreadHour], list[DiagnosisRow], dict[str, object]]:
    profile = build_spread_profile(demo_db_path, pair)
    trades = load_trades(chart_db_path, pair, timeframe, bt_run_id)
    rows, diagnostics = build_diagnosis_rows(trades, profile, parquet_path=parquet_path)
    if write_db:
        write_spread_profile(chart_db_path, pair, profile)
        write_diagnosis_rows(chart_db_path, rows)
    return profile, rows, diagnostics


def run_self_test() -> dict[str, str]:
    assert hour_bucket(0) == "Asia"
    assert hour_bucket(8) == "London"
    assert hour_bucket(12) == "London_NY_overlap"
    assert hour_bucket(23) == "NY+late"
    assert bonferroni_m("hour_bucket") == 48
    sample = pd.Series({"pattern_height_pips": 10.0, "sl_dist_pips": 6.0, "mfe_pips": 7.5, "mafe_pips": 1.0, "raw_pnl_pips": 0.0})
    assert math.isclose(hypothetical_rr_pnl(sample, 0.75), 6.0)
    return {"SELF_TEST_PASS": "ok"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        for key, value in run_self_test().items():
            print(f"{key}: {value}")
        return 0
    parser.error("use tools/s6_run_w2a.py for production runs")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
