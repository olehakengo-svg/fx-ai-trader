#!/usr/bin/env python3
"""S6 chart pattern Wave 2 backtest engine.

No LIVE/Shadow routing. Frozen labels in chart_pattern_signals are read-only.
"""
from __future__ import annotations

import argparse
import dataclasses
import math
import sqlite3
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import pandas as pd
from scipy.stats import binomtest

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.s6_chart_pattern_detector import PATTERNS, PATTERN_BY_ID, PatternSpec


SPREAD_PIPS = 1.5
PIP_FACTOR = 100.0
MAX_HOLD_BARS = 20
BONFERRONI_ALPHA = 0.05 / 12
WEDGE_PATTERN_IDS = {2, 5}

SQLITE_DDL = """
CREATE TABLE IF NOT EXISTS chart_pattern_bt_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id INTEGER NOT NULL,
    pattern_id INTEGER NOT NULL,
    pattern_name TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('BUY','SELL')),
    pair TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    entry_ts TEXT NOT NULL,
    entry_px REAL NOT NULL,
    exit_ts TEXT NOT NULL,
    exit_px REAL NOT NULL,
    exit_reason TEXT NOT NULL CHECK (exit_reason IN ('TP','SL','TIMEOUT')),
    pnl_pips REAL NOT NULL,
    mafe_pips REAL NOT NULL,
    mfe_pips REAL NOT NULL,
    hold_bars INTEGER NOT NULL,
    bt_run_id TEXT NOT NULL,
    arbitration_loser_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_cpbt_pattern ON chart_pattern_bt_trades(pattern_id, bt_run_id);
CREATE INDEX IF NOT EXISTS idx_cpbt_signal ON chart_pattern_bt_trades(signal_id);

CREATE TABLE IF NOT EXISTS chart_pattern_bt_verdicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_id INTEGER NOT NULL,
    pattern_name TEXT NOT NULL,
    pair TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    bt_run_id TEXT NOT NULL,
    n INTEGER NOT NULL,
    wr REAL NOT NULL,
    ev_pips REAL NOT NULL,
    pf REAL,
    wilson_lo_95 REAL NOT NULL,
    bev_wr REAL NOT NULL,
    bonferroni_p REAL NOT NULL,
    bonferroni_alpha REAL NOT NULL,
    kelly REAL NOT NULL,
    max_dd_pips REAL NOT NULL,
    wf_fold1_pf REAL,
    wf_fold2_pf REAL,
    wf_fold3_pf REAL,
    wf_all_folds_positive INTEGER NOT NULL,
    verdict TEXT NOT NULL CHECK (verdict IN ('PROMOTE','SHADOW','REJECT','INSUFFICIENT')),
    verdict_reason TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(pattern_id, pair, timeframe, bt_run_id)
);
"""


@dataclass(frozen=True)
class Signal:
    signal_id: int
    pattern_id: int
    pattern_name: str
    direction: str
    pair: str
    timeframe: str
    signal_ts: str
    sl_px: float
    tp_px: float
    confidence_score: float = 0.0


@dataclass
class Trade:
    signal_id: int = 0
    pattern_id: int = 0
    pattern_name: str = ""
    direction: str = "BUY"
    pair: str = "USD_JPY"
    timeframe: str = "M5"
    entry_ts: str = "2026-01-01T00:00:00+00:00"
    entry_px: float = 0.0
    exit_ts: str = "2026-01-01T00:00:00+00:00"
    exit_px: float = 0.0
    exit_reason: str = "TIMEOUT"
    pnl_pips: float = 0.0
    mafe_pips: float = 0.0
    mfe_pips: float = 0.0
    hold_bars: int = 0
    bt_run_id: str = ""
    arbitration_loser_count: int = 0
    sl_px: float = 0.0
    tp_px: float = 0.0


@dataclass(frozen=True)
class WalkForwardFold:
    fold_id: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp


@dataclass
class AggregateStats:
    n: int = 0
    wr: float = 0.0
    ev_pips: float = 0.0
    pf: float | None = 0.0
    wilson_lo_95: float = 0.0
    bev_wr: float = 0.0
    bonferroni_p: float = 1.0
    kelly: float = 0.0
    max_dd_pips: float = 0.0
    wf_fold_pfs: list[float | None] = field(default_factory=lambda: [None, None, None])


@dataclass(frozen=True)
class Verdict:
    verdict: str
    reason: str


@dataclass(frozen=True)
class PatternResult:
    pattern_id: int
    pattern_name: str
    pair: str
    timeframe: str
    bt_run_id: str
    stats: AggregateStats
    verdict: Verdict


def _iso(ts) -> str:
    return pd.Timestamp(ts).tz_convert("UTC").isoformat()


def normalize_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    if df.attrs.get("s6_normalized_ohlc"):
        return df
    out = df.copy()
    out = out.rename(columns={c: c.lower() for c in out.columns})
    missing = {"open", "high", "low", "close"} - set(out.columns)
    if missing:
        raise ValueError(f"OHLC missing columns: {sorted(missing)}")
    out.index = pd.to_datetime(out.index, utc=True)
    out = out.sort_index()
    out.attrs["s6_normalized_ohlc"] = True
    return out


def simulate_trade(signal: Signal, bars: pd.DataFrame, bt_run_id: str = "", loser_count: int = 0) -> Trade | None:
    bars = normalize_ohlc(bars)
    signal_ts = pd.Timestamp(signal.signal_ts)
    if signal_ts.tzinfo is None:
        signal_ts = signal_ts.tz_localize("UTC")
    else:
        signal_ts = signal_ts.tz_convert("UTC")
    loc = bars.index.searchsorted(signal_ts, side="right")
    entry_idx = int(loc)
    timeout_idx = entry_idx + MAX_HOLD_BARS
    if entry_idx >= len(bars):
        return None

    entry_ts = bars.index[entry_idx]
    entry_px = float(bars["open"].iloc[entry_idx])
    end_idx = min(timeout_idx, len(bars) - 1)
    exit_idx = end_idx
    exit_px = float(bars["close"].iloc[end_idx])
    exit_reason = "TIMEOUT"

    for i in range(entry_idx, end_idx + 1):
        high = float(bars["high"].iloc[i])
        low = float(bars["low"].iloc[i])
        if signal.direction == "BUY":
            if low <= signal.sl_px:
                exit_idx, exit_px, exit_reason = i, float(signal.sl_px), "SL"
                break
            if high >= signal.tp_px:
                exit_idx, exit_px, exit_reason = i, float(signal.tp_px), "TP"
                break
        else:
            if high >= signal.sl_px:
                exit_idx, exit_px, exit_reason = i, float(signal.sl_px), "SL"
                break
            if low <= signal.tp_px:
                exit_idx, exit_px, exit_reason = i, float(signal.tp_px), "TP"
                break

    if exit_reason == "TIMEOUT" and timeout_idx >= len(bars):
        return None

    window = bars.iloc[entry_idx : exit_idx + 1]
    if signal.direction == "BUY":
        gross = (exit_px - entry_px) * PIP_FACTOR
        mafe = max(0.0, (entry_px - float(window["low"].min())) * PIP_FACTOR)
        mfe = max(0.0, (float(window["high"].max()) - entry_px) * PIP_FACTOR)
    else:
        gross = (entry_px - exit_px) * PIP_FACTOR
        mafe = max(0.0, (float(window["high"].max()) - entry_px) * PIP_FACTOR)
        mfe = max(0.0, (entry_px - float(window["low"].min())) * PIP_FACTOR)

    return Trade(
        signal_id=signal.signal_id,
        pattern_id=signal.pattern_id,
        pattern_name=signal.pattern_name,
        direction=signal.direction,
        pair=signal.pair,
        timeframe=signal.timeframe,
        entry_ts=_iso(entry_ts),
        entry_px=entry_px,
        exit_ts=_iso(bars.index[exit_idx]),
        exit_px=exit_px,
        exit_reason=exit_reason,
        pnl_pips=gross - SPREAD_PIPS,
        mafe_pips=mafe,
        mfe_pips=mfe,
        hold_bars=exit_idx - entry_idx,
        bt_run_id=bt_run_id,
        arbitration_loser_count=loser_count,
        sl_px=signal.sl_px,
        tp_px=signal.tp_px,
    )


def wilson_lower(wins: int, n: int, z: float = 1.959963984540054) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    denom = 1 + z * z / n
    center = p + z * z / (2 * n)
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return max(0.0, (center - half) / denom)


def binomial_edge_p(wins: int, n: int, bev_wr: float) -> float:
    if n <= 0:
        return 1.0
    p = min(max(bev_wr, 1e-12), 1 - 1e-12)
    return float(binomtest(wins, n, p, alternative="greater").pvalue)


def kelly_fraction(wr: float, payoff: float) -> float:
    if payoff <= 0 or not math.isfinite(payoff):
        return 0.0 if payoff <= 0 else wr
    return wr - (1 - wr) / payoff


def profit_factor(pnls: Iterable[float]) -> float | None:
    vals = list(pnls)
    wins = sum(v for v in vals if v > 0)
    losses = abs(sum(v for v in vals if v < 0))
    if losses == 0:
        return math.inf if wins > 0 else 0.0
    return wins / losses


def max_drawdown_pips(pnls: Iterable[float]) -> float:
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        max_dd = min(max_dd, equity - peak)
    return max_dd


def breakeven_wr(trades: list[Trade]) -> float:
    if not trades:
        return 0.0
    total_dist = 0.0
    for t in trades:
        total_dist += abs(t.tp_px - t.entry_px) * PIP_FACTOR + abs(t.entry_px - t.sl_px) * PIP_FACTOR
    avg_dist = total_dist / len(trades)
    if avg_dist <= 0:
        return 1.0
    return min(1.0, SPREAD_PIPS / avg_dist)


def aggregate_trades(trades: list[Trade]) -> AggregateStats:
    if not trades:
        return AggregateStats()
    pnls = [t.pnl_pips for t in trades]
    wins = sum(1 for p in pnls if p > 0)
    wr = wins / len(trades)
    win_pnls = [p for p in pnls if p > 0]
    loss_pnls = [p for p in pnls if p < 0]
    avg_win = sum(win_pnls) / len(win_pnls) if win_pnls else 0.0
    avg_loss = abs(sum(loss_pnls) / len(loss_pnls)) if loss_pnls else 0.0
    payoff = (avg_win / avg_loss) if avg_loss > 0 else math.inf
    bev = breakeven_wr(trades)
    return AggregateStats(
        n=len(trades),
        wr=wr,
        ev_pips=sum(pnls) / len(pnls),
        pf=profit_factor(pnls),
        wilson_lo_95=wilson_lower(wins, len(trades)),
        bev_wr=bev,
        bonferroni_p=binomial_edge_p(wins, len(trades), bev),
        kelly=kelly_fraction(wr, payoff),
        max_dd_pips=max_drawdown_pips(pnls),
        wf_fold_pfs=walk_forward_pfs(trades),
    )


def walk_forward_folds() -> list[WalkForwardFold]:
    utc = "UTC"
    return [
        WalkForwardFold(1, pd.Timestamp("2014-01-01", tz=utc), pd.Timestamp("2019-01-01", tz=utc), pd.Timestamp("2019-01-01", tz=utc), pd.Timestamp("2021-01-01", tz=utc)),
        WalkForwardFold(2, pd.Timestamp("2014-01-01", tz=utc), pd.Timestamp("2021-01-01", tz=utc), pd.Timestamp("2021-01-01", tz=utc), pd.Timestamp("2023-01-01", tz=utc)),
        WalkForwardFold(3, pd.Timestamp("2014-01-01", tz=utc), pd.Timestamp("2023-01-01", tz=utc), pd.Timestamp("2023-01-01", tz=utc), pd.Timestamp("2026-05-01", tz=utc)),
    ]


def fold_for_trade(trade: Trade, folds: list[WalkForwardFold]) -> WalkForwardFold | None:
    ts = pd.Timestamp(trade.entry_ts).tz_convert("UTC")
    for fold in folds:
        if fold.test_start <= ts < fold.test_end:
            return fold
    return None


def walk_forward_pfs(trades: list[Trade]) -> list[float | None]:
    by_fold: dict[int, list[float]] = defaultdict(list)
    folds = walk_forward_folds()
    for trade in trades:
        fold = fold_for_trade(trade, folds)
        if fold is not None:
            by_fold[fold.fold_id].append(trade.pnl_pips)
    return [profit_factor(by_fold[i]) if by_fold[i] else None for i in (1, 2, 3)]


def decide_verdict(stats: AggregateStats) -> Verdict:
    if stats.n < 100:
        return Verdict("INSUFFICIENT", "N<100")
    pf_value = stats.pf if stats.pf is not None else 0.0
    wilson_pass = stats.wilson_lo_95 > stats.bev_wr
    core_pass = wilson_pass and stats.ev_pips > 0 and pf_value >= 1.3 and stats.bonferroni_p < BONFERRONI_ALPHA and stats.kelly > 0
    if stats.bonferroni_p >= BONFERRONI_ALPHA or not wilson_pass:
        return Verdict("REJECT", "Bonferroni or Wilson gate failed")
    if not core_pass:
        return Verdict("REJECT", "EV/PF/Kelly core gate failed")
    wf_positive = all(pf is not None and pf > 1.0 for pf in stats.wf_fold_pfs)
    if wf_positive and stats.kelly > 0.05:
        return Verdict("PROMOTE", "All gates passed")
    return Verdict("SHADOW", "Core gates passed but WF or Kelly<0.05 blocked promote")


def arbitrate_signals(signals: list[Signal]) -> list[tuple[Signal, int]]:
    grouped: dict[str, list[Signal]] = defaultdict(list)
    for sig in signals:
        grouped[sig.signal_ts].append(sig)
    kept: list[tuple[Signal, int]] = []
    for ts in sorted(grouped):
        group = grouped[ts]
        group.sort(key=lambda s: (-float(s.confidence_score or 0.0), s.pattern_id))
        kept.append((group[0], len(group) - 1))
    return kept


def reverse_wedge_signals(signals: list[Signal]) -> list[Signal]:
    out: list[Signal] = []
    for sig in signals:
        if sig.pattern_id not in WEDGE_PATTERN_IDS:
            raise ValueError("reversed mode is limited to wedge patterns 2 and 5")
        entry_ref = (sig.sl_px + sig.tp_px) / 2
        sl_dist = abs(entry_ref - sig.sl_px)
        tp_dist = abs(sig.tp_px - entry_ref)
        if sig.direction == "BUY":
            direction = "SELL"
            sl_px = entry_ref + sl_dist
            tp_px = entry_ref - tp_dist
        else:
            direction = "BUY"
            sl_px = entry_ref - sl_dist
            tp_px = entry_ref + tp_dist
        out.append(dataclasses.replace(sig, direction=direction, sl_px=sl_px, tp_px=tp_px))
    return out


def load_signals(db_path: Path, pair: str, timeframe: str, patterns: set[int] | None = None) -> list[Signal]:
    sql = """
        SELECT id, pattern_id, pattern_name, direction, pair, timeframe, signal_ts, sl_px, tp_px,
               COALESCE(confidence_score, 0.0) AS confidence_score
        FROM chart_pattern_signals
        WHERE pair=? AND timeframe=?
        ORDER BY signal_ts, pattern_id, id
    """
    with sqlite3.connect(db_path) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(sql, (pair, timeframe)).fetchall()
    signals = [
        Signal(
            signal_id=int(r["id"]),
            pattern_id=int(r["pattern_id"]),
            pattern_name=str(r["pattern_name"]),
            direction=str(r["direction"]),
            pair=str(r["pair"]),
            timeframe=str(r["timeframe"]),
            signal_ts=str(r["signal_ts"]),
            sl_px=float(r["sl_px"]),
            tp_px=float(r["tp_px"]),
            confidence_score=float(r["confidence_score"]),
        )
        for r in rows
    ]
    if patterns is not None:
        signals = [s for s in signals if s.pattern_id in patterns]
    return signals


def prepare_signals(signals: list[Signal], mode: str) -> list[tuple[Signal, int]]:
    if mode == "isolated":
        return [(s, 0) for s in signals]
    if mode == "arbitrated":
        return arbitrate_signals(signals)
    if mode == "reversed":
        return [(s, 0) for s in reverse_wedge_signals(signals)]
    raise ValueError(f"unsupported mode: {mode}")


def simulate_signals(signals: list[Signal], bars: pd.DataFrame, mode: str) -> list[Trade]:
    trades: list[Trade] = []
    run_id = mode
    bars = normalize_ohlc(bars)
    for sig, losers in prepare_signals(signals, mode):
        trade = simulate_trade(sig, bars, bt_run_id=run_id, loser_count=losers)
        if trade is not None:
            trades.append(trade)
    return trades


def summarize_by_pattern(trades: list[Trade], pair: str, timeframe: str, bt_run_id: str) -> list[PatternResult]:
    by_pattern: dict[int, list[Trade]] = defaultdict(list)
    for trade in trades:
        by_pattern[trade.pattern_id].append(trade)
    pattern_ids = sorted(by_pattern)
    results: list[PatternResult] = []
    for pattern_id in pattern_ids:
        spec = PATTERN_BY_ID[pattern_id]
        stats = aggregate_trades(by_pattern[pattern_id])
        results.append(PatternResult(pattern_id, spec.name, pair, timeframe, bt_run_id, stats, decide_verdict(stats)))
    return results


def ensure_schema(con: sqlite3.Connection) -> None:
    con.executescript(SQLITE_DDL)


def write_results(db_path: Path, trades: list[Trade], results: list[PatternResult], bt_run_id: str) -> None:
    with sqlite3.connect(db_path) as con:
        ensure_schema(con)
        con.execute("DELETE FROM chart_pattern_bt_trades WHERE bt_run_id=?", (bt_run_id,))
        con.execute("DELETE FROM chart_pattern_bt_verdicts WHERE bt_run_id=?", (bt_run_id,))
        con.executemany(
            """
            INSERT INTO chart_pattern_bt_trades (
                signal_id, pattern_id, pattern_name, direction, pair, timeframe, entry_ts, entry_px,
                exit_ts, exit_px, exit_reason, pnl_pips, mafe_pips, mfe_pips, hold_bars,
                bt_run_id, arbitration_loser_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
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
                    t.arbitration_loser_count,
                )
                for t in trades
            ],
        )
        con.executemany(
            """
            INSERT INTO chart_pattern_bt_verdicts (
                pattern_id, pattern_name, pair, timeframe, bt_run_id, n, wr, ev_pips, pf,
                wilson_lo_95, bev_wr, bonferroni_p, bonferroni_alpha, kelly, max_dd_pips,
                wf_fold1_pf, wf_fold2_pf, wf_fold3_pf, wf_all_folds_positive, verdict, verdict_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    r.pattern_id,
                    r.pattern_name,
                    r.pair,
                    r.timeframe,
                    r.bt_run_id,
                    r.stats.n,
                    r.stats.wr,
                    r.stats.ev_pips,
                    None if r.stats.pf is None or math.isinf(r.stats.pf) else r.stats.pf,
                    r.stats.wilson_lo_95,
                    r.stats.bev_wr,
                    r.stats.bonferroni_p,
                    BONFERRONI_ALPHA,
                    r.stats.kelly,
                    r.stats.max_dd_pips,
                    r.stats.wf_fold_pfs[0],
                    r.stats.wf_fold_pfs[1],
                    r.stats.wf_fold_pfs[2],
                    int(all(pf is not None and pf > 1.0 for pf in r.stats.wf_fold_pfs)),
                    r.verdict.verdict,
                    r.verdict.reason,
                )
                for r in results
            ],
        )
        con.commit()


def run_backtest(db_path: Path, parquet_path: Path, pair: str, timeframe: str, mode: str, patterns: set[int] | None = None) -> tuple[list[Trade], list[PatternResult]]:
    bars = pd.read_parquet(parquet_path)
    signals = load_signals(db_path, pair, timeframe, patterns=patterns)
    if mode == "reversed" and any(s.pattern_id not in WEDGE_PATTERN_IDS for s in signals):
        raise ValueError("reversed mode requires wedge-only patterns")
    trades = simulate_signals(signals, bars, mode)
    results = summarize_by_pattern(trades, pair, timeframe, mode)
    return trades, results


def synthetic_trade_for_pattern(pattern_id: int, reason: str) -> Trade | None:
    spec = PATTERN_BY_ID[pattern_id]
    ts0 = pd.Timestamp("2026-01-01 00:00", tz="UTC")
    rows = [(ts0, 100.0, 100.01, 99.99, 100.0)]
    if reason == "TIMEOUT":
        for i in range(1, 23):
            rows.append((ts0 + pd.Timedelta(minutes=5 * i), 100.0, 100.03, 99.97, 100.0))
        sl, tp = (99.0, 101.0) if spec.direction == "BUY" else (101.0, 99.0)
    elif spec.direction == "BUY" and reason == "TP":
        rows.append((ts0 + pd.Timedelta(minutes=5), 100.0, 100.20, 99.98, 100.15))
        sl, tp = 99.8, 100.1
    elif spec.direction == "BUY":
        rows.append((ts0 + pd.Timedelta(minutes=5), 100.0, 100.02, 99.80, 99.90))
        sl, tp = 99.9, 100.2
    elif reason == "TP":
        rows.append((ts0 + pd.Timedelta(minutes=5), 100.0, 100.02, 99.80, 99.90))
        sl, tp = 100.2, 99.9
    else:
        rows.append((ts0 + pd.Timedelta(minutes=5), 100.0, 100.20, 99.98, 100.10))
        sl, tp = 100.1, 99.8
    bars = pd.DataFrame(
        {"open": [r[1] for r in rows], "high": [r[2] for r in rows], "low": [r[3] for r in rows], "close": [r[4] for r in rows]},
        index=pd.to_datetime([r[0] for r in rows], utc=True),
    )
    sig = Signal(pattern_id, pattern_id, spec.name, spec.direction, "USD_JPY", "M5", _iso(ts0), sl, tp, 0.75)
    return simulate_trade(sig, bars)


def run_self_test() -> dict[int, str]:
    results: dict[int, str] = {}
    reasons = ["TP", "SL", "TIMEOUT"]
    for spec in PATTERNS:
        reason = reasons[(spec.pattern_id - 1) % len(reasons)]
        trade = synthetic_trade_for_pattern(spec.pattern_id, reason)
        if trade is None:
            raise AssertionError(f"self-test no fill for {spec.name}")
        results[spec.pattern_id] = trade.exit_reason
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        results = run_self_test()
        for spec in PATTERNS:
            print(f"{spec.pattern_id:02d} {spec.name}: {results[spec.pattern_id]}")
        print("SELF_TEST_PASS")
        return 0
    parser.error("only --self-test is supported by this module; use tools/s6_run_w2_bt.py for production runs")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
