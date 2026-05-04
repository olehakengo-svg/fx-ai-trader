#!/usr/bin/env python3
"""S6 W1P3 pre-registered chart-pattern TP/SL geometry variants."""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from s6_w1p2_primary_bt import (
    PIP_SIZE,
    PRIMARY_PATTERNS,
    bootstrap_pvalue,
    finite_or_none,
    pf_from_pnl,
    status_kelly_half,
    status_max_year_share,
    status_oos_is,
    status_pf,
    status_positive_years,
    status_pvalue,
    status_wilson,
    verdict_from_statuses,
    wilson_lower,
)


WILSON_Z = 1.959963984540054
MAX_HORIZON_BARS = 288

BT_DDL = """
CREATE TABLE IF NOT EXISTS chart_pattern_w1p3_bt (
    variant TEXT NOT NULL,
    pattern_name TEXT NOT NULL,
    direction TEXT NOT NULL,
    n_total INTEGER NOT NULL,
    n_valid INTEGER NOT NULL,
    dm_count INTEGER NOT NULL,
    raw_hr REAL,
    effective_wr REAL,
    pf REAL,
    gross_profit REAL,
    gross_loss REAL,
    avg_win REAL,
    avg_loss REAL,
    wilson_lo REAL,
    is_pf REAL,
    oos_pf REAL,
    oos_is_pf_ratio REAL,
    max_year_share REAL,
    positive_years INTEGER NOT NULL,
    total_years INTEGER NOT NULL,
    p_value REAL,
    bonf_pvalue REAL,
    kelly_full REAL,
    kelly_half REAL,
    sharpe REAL,
    pf_status TEXT NOT NULL,
    wilson_status TEXT NOT NULL,
    oos_is_status TEXT NOT NULL,
    max_year_share_status TEXT NOT NULL,
    positive_years_status TEXT NOT NULL,
    bonf_status TEXT NOT NULL,
    kelly_status TEXT NOT NULL,
    verdict TEXT NOT NULL,
    reject_reasons TEXT NOT NULL,
    needs_more_evidence_reasons TEXT NOT NULL,
    bootstrap_iters INTEGER NOT NULL,
    spread_pip REAL NOT NULL,
    slippage_pip REAL NOT NULL,
    round_trip_cost_pip REAL NOT NULL,
    is_end TEXT NOT NULL,
    bonferroni_m INTEGER NOT NULL,
    seed INTEGER NOT NULL,
    computed_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY(variant, pattern_name, direction)
);
"""


@dataclass(frozen=True)
class Signal:
    signal_id: int
    pattern_name: str
    direction: str
    signal_ts: str
    entry_px: float
    original_tp_px: float
    pattern_height_atr: float
    atr_at_detection: float
    pivot_anchor_ts: str
    pivot_opposite_ts: str
    confidence_score: float
    raw_geometry_json: str


@dataclass(frozen=True)
class Outcome:
    signal_id: int
    pattern_name: str
    direction: str
    signal_ts: str
    included: int
    exclusion_reason: str | None
    entry_px: float
    tp_px: float
    sl_px: float
    sl_side_valid: int
    outcome: str
    exit_ts: str | None
    bars_held: int
    pnl_pips: float | None


@dataclass(frozen=True)
class PatternResult:
    variant: str
    pattern_name: str
    direction: str
    n_total: int
    n_valid: int
    dm_count: int
    raw_hr: float
    effective_wr: float
    pf: float
    gross_profit: float
    gross_loss: float
    avg_win: float
    avg_loss: float
    wilson_lo: float
    is_pf: float
    oos_pf: float
    oos_is_pf_ratio: float
    max_year_share: float | None
    positive_years: int
    total_years: int
    p_value: float
    bonf_pvalue: float
    kelly_full: float
    kelly_half: float
    sharpe: float
    statuses: dict[str, str]
    verdict: str
    reject_reasons: list[str]
    needs_more_evidence_reasons: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", required=True, choices=("V1", "V2", "V3"))
    parser.add_argument("--signals", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--parquet", default="data/cache/massive/USD_JPY_5m.parquet")
    parser.add_argument("--bootstrap-iters", type=int, default=1000)
    parser.add_argument("--bootstrap-chunk", type=int, default=100)
    parser.add_argument("--spread-pip", type=float, default=1.5)
    parser.add_argument("--slippage-pip", type=float, default=0.3)
    parser.add_argument("--is-end", default="2022-12-31")
    parser.add_argument("--bonferroni-m", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20260504)
    return parser.parse_args()


def load_bars(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df = df.rename(columns={c: c.lower() for c in df.columns})
    missing = {"high", "low", "close"} - set(df.columns)
    if missing:
        raise ValueError(f"parquet is missing OHLC columns: {sorted(missing)}")
    df.index = pd.to_datetime(df.index, utc=True)
    return df.sort_index()


def load_signals(db_path: Path) -> list[Signal]:
    where = " OR ".join(["(pattern_name = ? AND direction = ?)"] * len(PRIMARY_PATTERNS))
    params: list[str] = []
    for pattern, direction in PRIMARY_PATTERNS:
        params.extend([pattern, direction])
    with sqlite3.connect(db_path) as con:
        rows = con.execute(
            f"""
            SELECT
                id, pattern_name, direction, signal_ts, entry_px, tp_px,
                pattern_height_atr, atr_at_detection, pivot_anchor_ts,
                pivot_opposite_ts, confidence_score, raw_geometry_json
            FROM chart_pattern_signals
            WHERE {where}
            ORDER BY signal_ts, id
            """,
            params,
        ).fetchall()
    return [
        Signal(
            signal_id=int(row[0]),
            pattern_name=str(row[1]),
            direction=str(row[2]),
            signal_ts=str(row[3]),
            entry_px=float(row[4]),
            original_tp_px=float(row[5]),
            pattern_height_atr=float(row[6]),
            atr_at_detection=float(row[7]),
            pivot_anchor_ts=str(row[8]),
            pivot_opposite_ts=str(row[9]),
            confidence_score=float(row[10]) if row[10] is not None else math.nan,
            raw_geometry_json=str(row[11]),
        )
        for row in rows
    ]


def direction_sign(direction: str) -> float:
    return 1.0 if direction == "BUY" else -1.0


def variant_prices(signal: Signal, variant: str) -> tuple[float, float, int]:
    sign = direction_sign(signal.direction)
    if variant in ("V1", "V3"):
        height_px = signal.pattern_height_atr * signal.atr_at_detection
        tp_px = signal.entry_px + height_px * sign
        sl_px = signal.entry_px - height_px * 0.5 * sign
    elif variant == "V2":
        geometry = json.loads(signal.raw_geometry_json)
        candidates = [
            float(pivot["price"])
            for pivot in geometry.get("pivots", [])
            if pivot.get("ts") in {signal.pivot_anchor_ts, signal.pivot_opposite_ts}
        ]
        if not candidates:
            raise ValueError(f"signal_id={signal.signal_id} has no V2 pivot candidates")
        sl_px = min(candidates, key=lambda px: abs(px - signal.entry_px))
        tp_px = signal.original_tp_px
    else:
        raise ValueError(f"unknown variant {variant}")
    sl_side_valid = int((sl_px < signal.entry_px) if signal.direction == "BUY" else (sl_px > signal.entry_px))
    return float(tp_px), float(sl_px), sl_side_valid


def v3_thresholds(signals: list[Signal]) -> dict[tuple[str, str], float]:
    thresholds: dict[tuple[str, str], float] = {}
    for pattern, direction in PRIMARY_PATTERNS:
        values = [s.confidence_score for s in signals if s.pattern_name == pattern and s.direction == direction]
        thresholds[(pattern, direction)] = float(np.nanmedian(np.array(values, dtype=np.float64)))
    return thresholds


def pnl_pips(direction: str, entry_px: float, exit_px: float) -> float:
    return (exit_px - entry_px) * direction_sign(direction) / PIP_SIZE


def label_signal(
    signal: Signal,
    bars: pd.DataFrame,
    tp_px: float,
    sl_px: float,
    included: int,
    exclusion_reason: str | None,
) -> Outcome:
    signal_ts = pd.Timestamp(signal.signal_ts)
    if signal_ts.tzinfo is None:
        signal_ts = signal_ts.tz_localize("UTC")
    else:
        signal_ts = signal_ts.tz_convert("UTC")

    start_pos = int(bars.index.searchsorted(signal_ts, side="right"))
    if start_pos >= len(bars):
        return Outcome(
            signal.signal_id,
            signal.pattern_name,
            signal.direction,
            signal.signal_ts,
            included,
            exclusion_reason,
            signal.entry_px,
            tp_px,
            sl_px,
            int((sl_px < signal.entry_px) if signal.direction == "BUY" else (sl_px > signal.entry_px)),
            "DM",
            None,
            0,
            None,
        )

    horizon_end_pos = start_pos + MAX_HORIZON_BARS - 1
    observed_end_pos = min(horizon_end_pos, len(bars) - 1)
    lows = bars["low"].to_numpy()
    highs = bars["high"].to_numpy()
    closes = bars["close"].to_numpy()

    for pos in range(start_pos, observed_end_pos + 1):
        sl_hit = lows[pos] <= sl_px <= highs[pos]
        tp_hit = lows[pos] <= tp_px <= highs[pos]
        bars_held = pos - start_pos + 1
        exit_ts = bars.index[pos].isoformat()
        if sl_hit:
            return Outcome(
                signal.signal_id,
                signal.pattern_name,
                signal.direction,
                signal.signal_ts,
                included,
                exclusion_reason,
                signal.entry_px,
                tp_px,
                sl_px,
                int((sl_px < signal.entry_px) if signal.direction == "BUY" else (sl_px > signal.entry_px)),
                "SL",
                exit_ts,
                bars_held,
                pnl_pips(signal.direction, signal.entry_px, sl_px),
            )
        if tp_hit:
            return Outcome(
                signal.signal_id,
                signal.pattern_name,
                signal.direction,
                signal.signal_ts,
                included,
                exclusion_reason,
                signal.entry_px,
                tp_px,
                sl_px,
                int((sl_px < signal.entry_px) if signal.direction == "BUY" else (sl_px > signal.entry_px)),
                "TP",
                exit_ts,
                bars_held,
                pnl_pips(signal.direction, signal.entry_px, tp_px),
            )

    if horizon_end_pos >= len(bars):
        return Outcome(
            signal.signal_id,
            signal.pattern_name,
            signal.direction,
            signal.signal_ts,
            included,
            exclusion_reason,
            signal.entry_px,
            tp_px,
            sl_px,
            int((sl_px < signal.entry_px) if signal.direction == "BUY" else (sl_px > signal.entry_px)),
            "DM",
            None,
            len(bars) - start_pos,
            None,
        )

    exit_px = float(closes[horizon_end_pos])
    return Outcome(
        signal.signal_id,
        signal.pattern_name,
        signal.direction,
        signal.signal_ts,
        included,
        exclusion_reason,
        signal.entry_px,
        tp_px,
        sl_px,
        int((sl_px < signal.entry_px) if signal.direction == "BUY" else (sl_px > signal.entry_px)),
        "TO",
        bars.index[horizon_end_pos].isoformat(),
        MAX_HORIZON_BARS,
        pnl_pips(signal.direction, signal.entry_px, exit_px),
    )


def outcome_table_name(variant: str) -> str:
    return f"chart_pattern_w1p3_{variant.lower()}_outcomes"


def write_outcomes(db_path: Path, variant: str, outcomes: list[Outcome]) -> None:
    table = outcome_table_name(variant)
    ddl = f"""
    CREATE TABLE IF NOT EXISTS {table} (
        signal_id INTEGER PRIMARY KEY,
        pattern_name TEXT NOT NULL,
        direction TEXT NOT NULL,
        signal_ts TEXT NOT NULL,
        included INTEGER NOT NULL,
        exclusion_reason TEXT,
        entry_px REAL NOT NULL,
        tp_px REAL NOT NULL,
        sl_px REAL NOT NULL,
        sl_side_valid INTEGER NOT NULL,
        outcome TEXT NOT NULL CHECK (outcome IN ('TP','SL','TO','DM')),
        exit_ts TEXT,
        bars_held INTEGER NOT NULL,
        pnl_pips REAL,
        audited_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY(signal_id) REFERENCES chart_pattern_signals(id)
    );
    CREATE INDEX IF NOT EXISTS idx_{table}_pattern ON {table}(pattern_name, direction, included);
    CREATE INDEX IF NOT EXISTS idx_{table}_outcome ON {table}(outcome);
    """
    rows = [
        (
            o.signal_id,
            o.pattern_name,
            o.direction,
            o.signal_ts,
            o.included,
            o.exclusion_reason,
            o.entry_px,
            o.tp_px,
            o.sl_px,
            o.sl_side_valid,
            o.outcome,
            o.exit_ts,
            o.bars_held,
            o.pnl_pips,
        )
        for o in outcomes
    ]
    with sqlite3.connect(db_path) as con:
        con.execute("PRAGMA foreign_keys = ON")
        con.executescript(ddl)
        con.execute(f"DELETE FROM {table}")
        con.executemany(
            f"""
            INSERT INTO {table} (
                signal_id, pattern_name, direction, signal_ts, included,
                exclusion_reason, entry_px, tp_px, sl_px, sl_side_valid,
                outcome, exit_ts, bars_held, pnl_pips
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            rows,
        )
        con.commit()


def rows_for_pattern(outcomes: list[Outcome], pattern: str, direction: str) -> list[Outcome]:
    return [
        o
        for o in outcomes
        if o.pattern_name == pattern and o.direction == direction and o.included == 1
    ]


def calc_result(
    variant: str,
    pattern: str,
    direction: str,
    rows: list[Outcome],
    cost_pips: float,
    is_end: str,
    bootstrap_iters: int,
    bootstrap_chunk: int,
    bonferroni_m: int,
    rng: np.random.Generator,
) -> PatternResult:
    if not rows:
        raise ValueError(f"no included rows for {variant} {pattern} {direction}")
    outcomes_all = np.array([o.outcome for o in rows])
    valid_mask = outcomes_all != "DM"
    n_total = int(outcomes_all.size)
    n_valid = int(np.count_nonzero(valid_mask))
    dm_count = n_total - n_valid
    if n_valid <= 0:
        raise ValueError(f"no valid non-DM rows for {variant} {pattern} {direction}")

    outcomes = outcomes_all[valid_mask]
    pnl_raw = np.array([np.nan if o.pnl_pips is None else o.pnl_pips for o in rows], dtype=np.float64)[valid_mask]
    signal_ts = np.array([o.signal_ts.replace("+00:00", "") for o in rows], dtype="datetime64[ns]")[valid_mask]
    sign = direction_sign(direction)
    tp_pips = np.array([(o.tp_px - o.entry_px) * sign / PIP_SIZE for o in rows], dtype=np.float64)[valid_mask]
    sl_pips = np.array([(o.sl_px - o.entry_px) * sign / PIP_SIZE for o in rows], dtype=np.float64)[valid_mask]

    pnl_net = pnl_raw - cost_pips
    pf, gross_profit, gross_loss = pf_from_pnl(pnl_net)
    wins = pnl_net[pnl_net > 0.0]
    losses = pnl_net[pnl_net < 0.0]
    raw_hr = float(np.count_nonzero(outcomes == "TP") / n_valid)
    effective_wr = float(wins.size / n_valid)
    avg_win = float(wins.mean()) if wins.size else 0.0
    avg_loss = float((-losses).mean()) if losses.size else 0.0
    wilson_lo = wilson_lower(int(wins.size), n_valid)

    lr = 1.0 - effective_wr
    kelly_full = (effective_wr * avg_win - lr * avg_loss) / avg_win if avg_win > 0.0 else 0.0
    kelly_half = kelly_full / 2.0

    is_end_dt = np.datetime64(f"{is_end}T23:59:59.999999999")
    is_mask = signal_ts <= is_end_dt
    oos_mask = signal_ts > is_end_dt
    is_pf = pf_from_pnl(pnl_net[is_mask])[0] if np.any(is_mask) else 0.0
    oos_pf = pf_from_pnl(pnl_net[oos_mask])[0] if np.any(oos_mask) else 0.0
    oos_is_ratio = (math.inf if oos_pf > 0.0 else 0.0) if is_pf == 0.0 else oos_pf / is_pf

    years = signal_ts.astype("datetime64[Y]").astype(int) + 1970
    yearly = np.array([pnl_net[years == year].sum() for year in range(int(years.min()), int(years.max()) + 1)])
    total_pnl = float(yearly.sum())
    max_year_share = float(yearly.max() / total_pnl) if total_pnl > 0.0 else None
    positive_years = int(np.count_nonzero(yearly > 0.0))
    total_years = int(yearly.size)

    if pnl_net.size > 1:
        std = float(pnl_net.std(ddof=1))
        span_days = max(1.0, float((signal_ts.max() - signal_ts.min()) / np.timedelta64(1, "D")))
        trades_per_year = n_valid / (span_days / 365.25)
        sharpe = float((pnl_net.mean() / std) * math.sqrt(trades_per_year)) if std > 0.0 else 0.0
    else:
        sharpe = 0.0

    to_pips_pool = pnl_raw[outcomes == "TO"]
    p_value = bootstrap_pvalue(
        observed_pf=pf,
        outcomes=outcomes,
        tp_pips=tp_pips,
        sl_pips=sl_pips,
        to_pips_pool=to_pips_pool,
        cost_pips=cost_pips,
        iters=bootstrap_iters,
        chunk_size=bootstrap_chunk,
        rng=rng,
    )
    statuses = {
        "pf": status_pf(pf),
        "wilson_lo": status_wilson(wilson_lo),
        "oos_is_pf_ratio": status_oos_is(oos_is_ratio),
        "max_year_share": status_max_year_share(max_year_share),
        "positive_years": status_positive_years(positive_years),
        "bonf_pvalue": status_pvalue(p_value, bonferroni_m),
        "kelly_half": status_kelly_half(kelly_half),
    }
    verdict, reject_reasons, nme_reasons = verdict_from_statuses(statuses)
    return PatternResult(
        variant,
        pattern,
        direction,
        n_total,
        n_valid,
        dm_count,
        raw_hr,
        effective_wr,
        pf,
        gross_profit,
        gross_loss,
        avg_win,
        avg_loss,
        wilson_lo,
        is_pf,
        oos_pf,
        oos_is_ratio,
        max_year_share,
        positive_years,
        total_years,
        p_value,
        p_value,
        kelly_full,
        kelly_half,
        sharpe,
        statuses,
        verdict,
        reject_reasons,
        nme_reasons,
    )


def write_bt_results(
    db_path: Path,
    results: list[PatternResult],
    bootstrap_iters: int,
    spread_pip: float,
    slippage_pip: float,
    cost_pips: float,
    is_end: str,
    bonferroni_m: int,
    seed: int,
) -> None:
    rows = []
    for r in results:
        rows.append(
            (
                r.variant,
                r.pattern_name,
                r.direction,
                r.n_total,
                r.n_valid,
                r.dm_count,
                r.raw_hr,
                r.effective_wr,
                finite_or_none(r.pf),
                r.gross_profit,
                r.gross_loss,
                r.avg_win,
                r.avg_loss,
                r.wilson_lo,
                finite_or_none(r.is_pf),
                finite_or_none(r.oos_pf),
                finite_or_none(r.oos_is_pf_ratio),
                finite_or_none(r.max_year_share),
                r.positive_years,
                r.total_years,
                r.p_value,
                r.bonf_pvalue,
                r.kelly_full,
                r.kelly_half,
                r.sharpe,
                r.statuses["pf"],
                r.statuses["wilson_lo"],
                r.statuses["oos_is_pf_ratio"],
                r.statuses["max_year_share"],
                r.statuses["positive_years"],
                r.statuses["bonf_pvalue"],
                r.statuses["kelly_half"],
                r.verdict,
                json.dumps(r.reject_reasons, sort_keys=True),
                json.dumps(r.needs_more_evidence_reasons, sort_keys=True),
                bootstrap_iters,
                spread_pip,
                slippage_pip,
                cost_pips,
                is_end,
                bonferroni_m,
                seed,
            )
        )
    with sqlite3.connect(db_path) as con:
        con.executescript(BT_DDL)
        con.executemany("DELETE FROM chart_pattern_w1p3_bt WHERE variant = ? AND pattern_name = ? AND direction = ?", [(r.variant, r.pattern_name, r.direction) for r in results])
        con.executemany(
            """
            INSERT INTO chart_pattern_w1p3_bt (
                variant, pattern_name, direction, n_total, n_valid, dm_count,
                raw_hr, effective_wr, pf, gross_profit, gross_loss,
                avg_win, avg_loss, wilson_lo, is_pf, oos_pf,
                oos_is_pf_ratio, max_year_share, positive_years, total_years,
                p_value, bonf_pvalue, kelly_full, kelly_half, sharpe,
                pf_status, wilson_status, oos_is_status, max_year_share_status,
                positive_years_status, bonf_status, kelly_status, verdict,
                reject_reasons, needs_more_evidence_reasons, bootstrap_iters,
                spread_pip, slippage_pip, round_trip_cost_pip, is_end,
                bonferroni_m, seed
            ) VALUES (
                ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,
                ?,?,?,?,?,?,?,?,?,?,?,?
            )
            """,
            rows,
        )
        con.commit()


def print_summary(results: list[PatternResult]) -> None:
    print("variant,pattern_name,direction,n_total,n_valid,pf,wilson_lo,oos_is_pf_ratio,max_year_share,positive_years,bonf_pvalue,kelly_half,verdict")
    for r in results:
        max_share = "NULL" if r.max_year_share is None else f"{r.max_year_share:.6f}"
        print(
            f"{r.variant},{r.pattern_name},{r.direction},{r.n_total},{r.n_valid},"
            f"{r.pf:.6f},{r.wilson_lo:.6f},{r.oos_is_pf_ratio:.6f},"
            f"{max_share},{r.positive_years},{r.bonf_pvalue:.6f},"
            f"{r.kelly_half:.6f},{r.verdict}"
        )


def main() -> int:
    args = parse_args()
    signals_path = Path(args.signals)
    output_path = Path(args.output)
    if signals_path.resolve() != output_path.resolve():
        raise SystemExit("W1P3 writes only to the same SQLite DB passed as --signals")
    if args.bonferroni_m != 8:
        raise SystemExit("W1P3 pre-registration locks --bonferroni-m to 8")
    if args.spread_pip != 1.5 or args.slippage_pip != 0.3:
        raise SystemExit("W1P3 friction model is locked to --spread-pip 1.5 --slippage-pip 0.3")

    bars = load_bars(Path(args.parquet))
    signals = load_signals(signals_path)
    thresholds = v3_thresholds(signals)
    outcomes: list[Outcome] = []
    for signal in signals:
        tp_px, sl_px, _sl_side_valid = variant_prices(signal, args.variant)
        included = 1
        exclusion_reason = None
        if args.variant == "V3":
            threshold = thresholds[(signal.pattern_name, signal.direction)]
            if not signal.confidence_score >= threshold:
                included = 0
                exclusion_reason = "confidence_below_pattern_median"
        outcomes.append(label_signal(signal, bars, tp_px, sl_px, included, exclusion_reason))

    write_outcomes(output_path, args.variant, outcomes)
    cost_pips = args.spread_pip + 2.0 * args.slippage_pip
    rng = np.random.default_rng(args.seed + {"V1": 1, "V2": 2, "V3": 3}[args.variant])
    results = [
        calc_result(
            variant=args.variant,
            pattern=pattern,
            direction=direction,
            rows=rows_for_pattern(outcomes, pattern, direction),
            cost_pips=cost_pips,
            is_end=args.is_end,
            bootstrap_iters=args.bootstrap_iters,
            bootstrap_chunk=args.bootstrap_chunk,
            bonferroni_m=args.bonferroni_m,
            rng=rng,
        )
        for pattern, direction in PRIMARY_PATTERNS
    ]
    write_bt_results(
        output_path,
        results,
        args.bootstrap_iters,
        args.spread_pip,
        args.slippage_pip,
        cost_pips,
        args.is_end,
        args.bonferroni_m,
        args.seed,
    )
    print_summary(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
