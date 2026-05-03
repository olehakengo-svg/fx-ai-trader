#!/usr/bin/env python3
"""S6 W1P2 primary chart-pattern BT.

Computes the pre-registered W1P2 metrics for the eight primary
chart-pattern/direction pairs using W1P1 labeled outcomes.
"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import numpy as np


PIP_SIZE = 0.01
WILSON_Z = 1.959963984540054
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


RESULT_DDL = """
CREATE TABLE IF NOT EXISTS chart_pattern_w1p2_bt (
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
    PRIMARY KEY(pattern_name, direction)
);
"""


@dataclass(frozen=True)
class PatternResult:
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
    parser.add_argument("--signals", required=True, help="SQLite DB containing chart_pattern_signals/outcomes")
    parser.add_argument("--output", required=True, help="Same SQLite DB; receives chart_pattern_w1p2_bt")
    parser.add_argument("--primary-only", action="store_true", help="Run the locked primary eight patterns")
    parser.add_argument("--pattern", help="Single pattern_name to run")
    parser.add_argument("--direction", choices=("BUY", "SELL"), help="Single direction to run")
    parser.add_argument("--bootstrap-iters", type=int, default=1000)
    parser.add_argument("--bootstrap-chunk", type=int, default=100)
    parser.add_argument("--spread-pip", type=float, default=1.5)
    parser.add_argument("--slippage-pip", type=float, default=0.3)
    parser.add_argument("--is-end", default="2022-12-31")
    parser.add_argument("--bonferroni-m", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20260504)
    return parser.parse_args()


def finite_or_none(value: float | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return float(value)


def pf_from_pnl(pnl: np.ndarray) -> tuple[float, float, float]:
    wins = pnl[pnl > 0.0]
    losses = pnl[pnl < 0.0]
    gross_profit = float(wins.sum()) if wins.size else 0.0
    gross_loss = float(-losses.sum()) if losses.size else 0.0
    if gross_loss == 0.0:
        pf = math.inf if gross_profit > 0.0 else 0.0
    else:
        pf = gross_profit / gross_loss
    return pf, gross_profit, gross_loss


def wilson_lower(successes: int, n: int) -> float:
    if n <= 0:
        return math.nan
    phat = successes / n
    z2 = WILSON_Z * WILSON_Z
    denom = 1.0 + z2 / n
    centre = phat + z2 / (2.0 * n)
    margin = WILSON_Z * math.sqrt((phat * (1.0 - phat) + z2 / (4.0 * n)) / n)
    return (centre - margin) / denom


def status_pf(value: float) -> str:
    if value >= 1.20:
        return "ACCEPT"
    if value >= 1.05:
        return "NEEDS_MORE_EVIDENCE"
    return "REJECT"


def status_wilson(value: float) -> str:
    if value >= 0.50:
        return "ACCEPT"
    if value >= 0.45:
        return "NEEDS_MORE_EVIDENCE"
    return "REJECT"


def status_oos_is(value: float) -> str:
    if value >= 0.85:
        return "ACCEPT"
    if value >= 0.70:
        return "NEEDS_MORE_EVIDENCE"
    return "REJECT"


def status_max_year_share(value: float | None) -> str:
    if value is None:
        return "REJECT"
    if value < 0.50:
        return "ACCEPT"
    if value < 0.65:
        return "NEEDS_MORE_EVIDENCE"
    return "REJECT"


def status_positive_years(value: int) -> str:
    if value >= 8:
        return "ACCEPT"
    if value >= 6:
        return "NEEDS_MORE_EVIDENCE"
    return "REJECT"


def status_pvalue(value: float, bonferroni_m: int) -> str:
    alpha = 0.05 / bonferroni_m
    if value < alpha:
        return "ACCEPT"
    if value < 0.05:
        return "NEEDS_MORE_EVIDENCE"
    return "REJECT"


def status_kelly_half(value: float) -> str:
    if value >= 0.05:
        return "ACCEPT"
    if value >= 0.02:
        return "NEEDS_MORE_EVIDENCE"
    return "REJECT"


def verdict_from_statuses(statuses: dict[str, str]) -> tuple[str, list[str], list[str]]:
    reject_reasons = [name for name, status in statuses.items() if status == "REJECT"]
    nme_reasons = [name for name, status in statuses.items() if status == "NEEDS_MORE_EVIDENCE"]
    critical_reject = any(statuses[name] == "REJECT" for name in ("pf", "bonf_pvalue", "kelly_half"))

    if len(reject_reasons) >= 3 or critical_reject:
        verdict = "REJECT"
    elif not reject_reasons and not nme_reasons:
        verdict = "ACCEPT"
    else:
        verdict = "NEEDS_MORE_EVIDENCE"
    return verdict, reject_reasons, nme_reasons


def load_pattern_rows(db_path: Path, pattern: str, direction: str) -> dict[str, np.ndarray]:
    with sqlite3.connect(db_path) as con:
        rows = con.execute(
            """
            SELECT
                s.signal_ts,
                s.entry_px,
                s.sl_px,
                s.tp_px,
                o.outcome,
                o.pnl_pips
            FROM chart_pattern_signals s
            JOIN chart_pattern_outcomes o ON o.signal_id = s.id
            WHERE s.pattern_name = ? AND s.direction = ?
            ORDER BY s.signal_ts, s.id
            """,
            (pattern, direction),
        ).fetchall()

    if not rows:
        raise ValueError(f"no rows for {pattern} {direction}")

    signal_ts = np.array([str(row[0]).replace("+00:00", "") for row in rows], dtype="datetime64[ns]")
    entry = np.array([float(row[1]) for row in rows], dtype=np.float64)
    sl = np.array([float(row[2]) for row in rows], dtype=np.float64)
    tp = np.array([float(row[3]) for row in rows], dtype=np.float64)
    outcomes = np.array([str(row[4]) for row in rows])
    pnl = np.array([np.nan if row[5] is None else float(row[5]) for row in rows], dtype=np.float64)
    direction_sign = 1.0 if direction == "BUY" else -1.0

    return {
        "signal_ts": signal_ts,
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "outcomes": outcomes,
        "pnl": pnl,
        "tp_pips": (tp - entry) * direction_sign / PIP_SIZE,
        "sl_pips": (sl - entry) * direction_sign / PIP_SIZE,
    }


def bootstrap_pvalue(
    observed_pf: float,
    outcomes: np.ndarray,
    tp_pips: np.ndarray,
    sl_pips: np.ndarray,
    to_pips_pool: np.ndarray,
    cost_pips: float,
    iters: int,
    chunk_size: int,
    rng: np.random.Generator,
) -> float:
    if iters <= 0:
        raise ValueError("--bootstrap-iters must be positive")
    if chunk_size <= 0:
        raise ValueError("--bootstrap-chunk must be positive")

    labels = np.zeros(outcomes.size, dtype=np.int8)
    labels[outcomes == "SL"] = 1
    labels[outcomes == "TO"] = 2
    n = labels.size
    ge_count = 0
    done = 0
    if to_pips_pool.size == 0:
        to_pips_pool = np.array([0.0], dtype=np.float64)

    while done < iters:
        chunk = min(chunk_size, iters - done)
        order = np.argsort(rng.random((chunk, n)), axis=1)
        shuffled = labels[order]
        to_draws = rng.choice(to_pips_pool, size=(chunk, n), replace=True)
        pnl = np.where(shuffled == 0, tp_pips, np.where(shuffled == 1, sl_pips, to_draws))
        pnl = pnl - cost_pips
        gross_profit = np.where(pnl > 0.0, pnl, 0.0).sum(axis=1)
        gross_loss = np.where(pnl < 0.0, -pnl, 0.0).sum(axis=1)
        null_pf = np.divide(
            gross_profit,
            gross_loss,
            out=np.where(gross_profit > 0.0, np.inf, 0.0),
            where=gross_loss != 0.0,
        )
        ge_count += int(np.count_nonzero(null_pf >= observed_pf))
        done += chunk

    return ge_count / iters


def calc_result(
    db_path: Path,
    pattern: str,
    direction: str,
    cost_pips: float,
    is_end: str,
    bootstrap_iters: int,
    bootstrap_chunk: int,
    bonferroni_m: int,
    rng: np.random.Generator,
) -> PatternResult:
    data = load_pattern_rows(db_path, pattern, direction)
    outcomes_all = data["outcomes"]
    valid_mask = outcomes_all != "DM"
    n_total = int(outcomes_all.size)
    n_valid = int(np.count_nonzero(valid_mask))
    dm_count = n_total - n_valid
    if n_valid <= 0:
        raise ValueError(f"no valid non-DM rows for {pattern} {direction}")

    outcomes = outcomes_all[valid_mask]
    pnl_raw = data["pnl"][valid_mask]
    signal_ts = data["signal_ts"][valid_mask]
    tp_pips = data["tp_pips"][valid_mask]
    sl_pips = data["sl_pips"][valid_mask]

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
    if avg_win > 0.0:
        kelly_full = (effective_wr * avg_win - lr * avg_loss) / avg_win
    else:
        kelly_full = 0.0
    kelly_half = kelly_full / 2.0

    is_end_dt = np.datetime64(f"{is_end}T23:59:59.999999999")
    is_mask = signal_ts <= is_end_dt
    oos_mask = signal_ts > is_end_dt
    is_pf = pf_from_pnl(pnl_net[is_mask])[0] if np.any(is_mask) else 0.0
    oos_pf = pf_from_pnl(pnl_net[oos_mask])[0] if np.any(oos_mask) else 0.0
    if is_pf == 0.0:
        oos_is_ratio = math.inf if oos_pf > 0.0 else 0.0
    else:
        oos_is_ratio = oos_pf / is_pf

    years = signal_ts.astype("datetime64[Y]").astype(int) + 1970
    min_year = int(years.min())
    max_year = int(years.max())
    yearly_pnl = np.array([pnl_net[years == year].sum() for year in range(min_year, max_year + 1)])
    total_years = int(yearly_pnl.size)
    total_pnl = float(yearly_pnl.sum())
    if total_pnl > 0.0:
        max_year_share = float(yearly_pnl.max() / total_pnl)
    else:
        max_year_share = None
    positive_years = int(np.count_nonzero(yearly_pnl > 0.0))

    if pnl_net.size > 1:
        std = float(pnl_net.std(ddof=1))
        span_days = max(
            1.0,
            float((signal_ts.max() - signal_ts.min()) / np.timedelta64(1, "D")),
        )
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
        pattern_name=pattern,
        direction=direction,
        n_total=n_total,
        n_valid=n_valid,
        dm_count=dm_count,
        raw_hr=raw_hr,
        effective_wr=effective_wr,
        pf=pf,
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        avg_win=avg_win,
        avg_loss=avg_loss,
        wilson_lo=wilson_lo,
        is_pf=is_pf,
        oos_pf=oos_pf,
        oos_is_pf_ratio=oos_is_ratio,
        max_year_share=max_year_share,
        positive_years=positive_years,
        total_years=total_years,
        p_value=p_value,
        bonf_pvalue=p_value,
        kelly_full=kelly_full,
        kelly_half=kelly_half,
        sharpe=sharpe,
        statuses=statuses,
        verdict=verdict,
        reject_reasons=reject_reasons,
        needs_more_evidence_reasons=nme_reasons,
    )


def write_results(
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
        con.executescript(RESULT_DDL)
        con.executemany(
            """
            DELETE FROM chart_pattern_w1p2_bt
            WHERE pattern_name = ? AND direction = ?
            """,
            [(r.pattern_name, r.direction) for r in results],
        )
        con.executemany(
            """
            INSERT INTO chart_pattern_w1p2_bt (
                pattern_name, direction, n_total, n_valid, dm_count,
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
                ?,?,?,?,?,?,?,?,?,?,?
            )
            """,
            rows,
        )
        con.commit()


def selected_patterns(args: argparse.Namespace) -> list[tuple[str, str]]:
    if args.primary_only:
        if args.pattern or args.direction:
            raise SystemExit("--primary-only cannot be combined with --pattern/--direction")
        return list(PRIMARY_PATTERNS)
    if bool(args.pattern) != bool(args.direction):
        raise SystemExit("--pattern and --direction must be provided together")
    if args.pattern and args.direction:
        pair = (args.pattern, args.direction)
        if pair not in PRIMARY_PATTERNS:
            raise SystemExit(f"{pair[0]} {pair[1]} is not in the locked primary set")
        return [pair]
    raise SystemExit("use --primary-only or --pattern <name> --direction <BUY|SELL>")


def print_summary(results: list[PatternResult]) -> None:
    print("pattern_name,direction,n_total,n_valid,pf,wilson_lo,oos_is_pf_ratio,max_year_share,positive_years,bonf_pvalue,kelly_half,verdict")
    for r in results:
        max_share = "NULL" if r.max_year_share is None else f"{r.max_year_share:.6f}"
        print(
            f"{r.pattern_name},{r.direction},{r.n_total},{r.n_valid},"
            f"{r.pf:.6f},{r.wilson_lo:.6f},{r.oos_is_pf_ratio:.6f},"
            f"{max_share},{r.positive_years},{r.bonf_pvalue:.6f},"
            f"{r.kelly_half:.6f},{r.verdict}"
        )


def main() -> int:
    args = parse_args()
    signals_path = Path(args.signals)
    output_path = Path(args.output)
    if signals_path.resolve() != output_path.resolve():
        raise SystemExit("W1P2 writes only to the same SQLite DB passed as --signals")
    if args.bootstrap_iters <= 0:
        raise SystemExit("--bootstrap-iters must be positive")
    if args.bonferroni_m != 8:
        raise SystemExit("W1P2 primary pre-registration locks --bonferroni-m to 8")
    if args.spread_pip != 1.5 or args.slippage_pip != 0.3:
        raise SystemExit("W1P2 friction model is locked to --spread-pip 1.5 --slippage-pip 0.3")

    cost_pips = args.spread_pip + (2.0 * args.slippage_pip)
    rng = np.random.default_rng(args.seed)
    results = [
        calc_result(
            db_path=signals_path,
            pattern=pattern,
            direction=direction,
            cost_pips=cost_pips,
            is_end=args.is_end,
            bootstrap_iters=args.bootstrap_iters,
            bootstrap_chunk=args.bootstrap_chunk,
            bonferroni_m=args.bonferroni_m,
            rng=rng,
        )
        for pattern, direction in selected_patterns(args)
    ]
    write_results(
        db_path=output_path,
        results=results,
        bootstrap_iters=args.bootstrap_iters,
        spread_pip=args.spread_pip,
        slippage_pip=args.slippage_pip,
        cost_pips=cost_pips,
        is_end=args.is_end,
        bonferroni_m=args.bonferroni_m,
        seed=args.seed,
    )
    print_summary(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
