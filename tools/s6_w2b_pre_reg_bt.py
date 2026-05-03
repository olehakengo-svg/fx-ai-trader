#!/usr/bin/env python3
"""S6 Wave 2b pre-registration BT engine.

No LIVE/Shadow/OANDA routing. Frozen W1P0 labels are read-only inputs.

Locked SQLite DDL:

CREATE TABLE IF NOT EXISTS chart_pattern_w2b_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id TEXT NOT NULL CHECK (candidate_id IN ('C1','C2','C3')),
    signal_id INTEGER NOT NULL,
    pattern_id INTEGER NOT NULL,
    pair TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('BUY','SELL')),
    intrabar_resolve TEXT NOT NULL CHECK (intrabar_resolve IN ('SL_FIRST','TP_FIRST')),
    entry_ts TEXT NOT NULL,
    entry_px REAL NOT NULL,
    sl_px REAL NOT NULL,
    tp_px REAL NOT NULL,
    exit_ts TEXT NOT NULL,
    exit_px REAL NOT NULL,
    exit_reason TEXT NOT NULL CHECK (exit_reason IN ('TP','SL','TIMEOUT')),
    spread_pips_applied REAL NOT NULL,
    pnl_pips REAL NOT NULL,
    mafe_pips REAL NOT NULL,
    mfe_pips REAL NOT NULL,
    hold_bars INTEGER NOT NULL,
    is_train_oos TEXT NOT NULL CHECK (is_train_oos IN ('TRAIN','OOS')),
    wf_fold INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_cpw2b_cand ON chart_pattern_w2b_trades(candidate_id, intrabar_resolve, is_train_oos);

CREATE TABLE IF NOT EXISTS chart_pattern_w2b_verdicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id TEXT NOT NULL,
    pattern_id INTEGER NOT NULL,
    intrabar_resolve TEXT NOT NULL,
    eval_split TEXT NOT NULL CHECK (eval_split IN ('OOS_1','WF_1','WF_2','WF_3','TRAIN')),
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
    verdict TEXT NOT NULL CHECK (verdict IN ('PROMOTE','SHADOW','REJECT','INSUFFICIENT')),
    verdict_reason TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(candidate_id, intrabar_resolve, eval_split)
);
"""
from __future__ import annotations

import argparse
import math
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd
from scipy.stats import binomtest

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.s6_chart_pattern_bt import PIP_FACTOR, max_drawdown_pips, profit_factor, wilson_lower


RR_MULTIPLIER = 1.25
MAX_HOLD_BARS = 30
BONFERRONI_ALPHA = 0.05 / 3
INTRABAR_RESOLVES = ("SL_FIRST", "TP_FIRST")

SQLITE_DDL = """
CREATE TABLE IF NOT EXISTS chart_pattern_w2b_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id TEXT NOT NULL CHECK (candidate_id IN ('C1','C2','C3')),
    signal_id INTEGER NOT NULL,
    pattern_id INTEGER NOT NULL,
    pair TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('BUY','SELL')),
    intrabar_resolve TEXT NOT NULL CHECK (intrabar_resolve IN ('SL_FIRST','TP_FIRST')),
    entry_ts TEXT NOT NULL,
    entry_px REAL NOT NULL,
    sl_px REAL NOT NULL,
    tp_px REAL NOT NULL,
    exit_ts TEXT NOT NULL,
    exit_px REAL NOT NULL,
    exit_reason TEXT NOT NULL CHECK (exit_reason IN ('TP','SL','TIMEOUT')),
    spread_pips_applied REAL NOT NULL,
    pnl_pips REAL NOT NULL,
    mafe_pips REAL NOT NULL,
    mfe_pips REAL NOT NULL,
    hold_bars INTEGER NOT NULL,
    is_train_oos TEXT NOT NULL CHECK (is_train_oos IN ('TRAIN','OOS')),
    wf_fold INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_cpw2b_cand ON chart_pattern_w2b_trades(candidate_id, intrabar_resolve, is_train_oos);

CREATE TABLE IF NOT EXISTS chart_pattern_w2b_verdicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id TEXT NOT NULL,
    pattern_id INTEGER NOT NULL,
    intrabar_resolve TEXT NOT NULL,
    eval_split TEXT NOT NULL CHECK (eval_split IN ('OOS_1','WF_1','WF_2','WF_3','TRAIN')),
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
    verdict TEXT NOT NULL CHECK (verdict IN ('PROMOTE','SHADOW','REJECT','INSUFFICIENT')),
    verdict_reason TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(candidate_id, intrabar_resolve, eval_split)
);
"""


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    pattern_id: int
    pattern_name: str


CANDIDATES = {
    "C1": Candidate("C1", 8, "triple_bottom"),
    "C2": Candidate("C2", 11, "triple_top"),
    "C3": Candidate("C3", 9, "inverse_head_shoulders"),
}
CANDIDATES_BY_PATTERN = {c.pattern_id: c for c in CANDIDATES.values()}


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
    frozen_tp_px: float


@dataclass(frozen=True)
class Trade:
    candidate_id: str
    signal_id: int
    pattern_id: int
    pair: str
    timeframe: str
    direction: str
    intrabar_resolve: str
    entry_ts: str
    entry_px: float
    sl_px: float
    tp_px: float
    exit_ts: str
    exit_px: float
    exit_reason: str
    spread_pips_applied: float
    pnl_pips: float
    mafe_pips: float
    mfe_pips: float
    hold_bars: int
    is_train_oos: str
    wf_fold: int | None


@dataclass(frozen=True)
class AggregateStats:
    n: int
    wr: float
    ev_pips: float
    pf: float | None
    wilson_lo_95: float
    bev_wr: float
    bonferroni_p: float
    kelly: float
    max_dd_pips: float


@dataclass(frozen=True)
class VerdictRow:
    candidate_id: str
    pattern_id: int
    intrabar_resolve: str
    eval_split: str
    n: int
    wr: float
    ev_pips: float
    pf: float | None
    wilson_lo_95: float
    bev_wr: float
    bonferroni_p: float
    bonferroni_alpha: float
    kelly: float
    max_dd_pips: float
    verdict: str
    verdict_reason: str


def _ts(value: str) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        return ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


def _iso(value) -> str:
    return pd.Timestamp(value).tz_convert("UTC").isoformat()


def normalize_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    if df.attrs.get("s6_w2b_normalized_ohlc"):
        return df
    out = df.rename(columns={c: c.lower() for c in df.columns}).copy()
    missing = {"open", "high", "low", "close"} - set(out.columns)
    if missing:
        raise ValueError(f"OHLC missing columns: {sorted(missing)}")
    out.index = pd.to_datetime(out.index, utc=True)
    out = out.sort_index()
    out.attrs["s6_w2b_normalized_ohlc"] = True
    return out


def recompute_tp(direction: str, entry_px: float, sl_px: float) -> float:
    distance = abs(float(entry_px) - float(sl_px))
    if distance <= 0:
        raise ValueError("SL distance must be positive")
    if direction == "BUY":
        return float(entry_px) + distance * RR_MULTIPLIER
    if direction == "SELL":
        return float(entry_px) - distance * RR_MULTIPLIER
    raise ValueError(f"unsupported direction: {direction}")


def is_london_ny_overlap(ts: str) -> bool:
    hour = _ts(ts).hour
    return 12 <= hour < 16


def spread_for_signal_hour(signal_ts: str, profile: dict[int, float]) -> float:
    hour = _ts(signal_ts).hour
    if hour not in profile:
        raise ValueError(f"missing spread profile hour: {hour}")
    return float(profile[hour])


def oos_label(entry_ts: str) -> str:
    return "OOS" if _ts(entry_ts) >= pd.Timestamp("2023-01-01", tz="UTC") else "TRAIN"


def wf_fold(entry_ts: str) -> int | None:
    ts = _ts(entry_ts)
    if pd.Timestamp("2019-01-01", tz="UTC") <= ts < pd.Timestamp("2021-01-01", tz="UTC"):
        return 1
    if pd.Timestamp("2021-01-01", tz="UTC") <= ts < pd.Timestamp("2023-01-01", tz="UTC"):
        return 2
    if pd.Timestamp("2023-01-01", tz="UTC") <= ts < pd.Timestamp("2026-05-01", tz="UTC"):
        return 3
    return None


def _hit_order(direction: str, high: float, low: float, sl_px: float, tp_px: float, intrabar_resolve: str) -> tuple[bool, bool]:
    if direction == "BUY":
        sl_hit = low <= sl_px
        tp_hit = high >= tp_px
    else:
        sl_hit = high >= sl_px
        tp_hit = low <= tp_px
    if intrabar_resolve == "SL_FIRST":
        return sl_hit, tp_hit
    if intrabar_resolve == "TP_FIRST":
        return tp_hit, sl_hit
    raise ValueError(f"unsupported intrabar resolve: {intrabar_resolve}")


def simulate_trade(signal: Signal, bars: pd.DataFrame, spread_profile: dict[int, float], intrabar_resolve: str) -> Trade | None:
    if signal.pattern_id not in CANDIDATES_BY_PATTERN:
        return None
    if not is_london_ny_overlap(signal.signal_ts):
        return None

    bars = normalize_ohlc(bars)
    signal_ts = _ts(signal.signal_ts)
    entry_idx = int(bars.index.searchsorted(signal_ts, side="right"))
    if entry_idx >= len(bars):
        return None
    entry_ts = bars.index[entry_idx]
    if not is_london_ny_overlap(_iso(entry_ts)):
        return None
    timeout_idx = entry_idx + MAX_HOLD_BARS
    end_idx = min(timeout_idx, len(bars) - 1)

    entry_px = float(bars["open"].iloc[entry_idx])
    sl_px = float(signal.sl_px)
    tp_px = recompute_tp(signal.direction, entry_px, sl_px)
    spread = spread_for_signal_hour(signal.signal_ts, spread_profile)

    exit_idx = end_idx
    exit_px = float(bars["close"].iloc[end_idx])
    exit_reason = "TIMEOUT"
    for i in range(entry_idx, end_idx + 1):
        high = float(bars["high"].iloc[i])
        low = float(bars["low"].iloc[i])
        first_hit, second_hit = _hit_order(signal.direction, high, low, sl_px, tp_px, intrabar_resolve)
        if first_hit:
            exit_idx = i
            if intrabar_resolve == "SL_FIRST":
                first_reason = "SL"
            else:
                first_reason = "TP"
            exit_reason = first_reason
            exit_px = sl_px if first_reason == "SL" else tp_px
            break
        if second_hit:
            exit_idx = i
            if intrabar_resolve == "SL_FIRST":
                second_reason = "TP"
            else:
                second_reason = "SL"
            exit_reason = second_reason
            exit_px = sl_px if second_reason == "SL" else tp_px
            break

    window = bars.iloc[entry_idx : exit_idx + 1]
    if signal.direction == "BUY":
        gross = (exit_px - entry_px) * PIP_FACTOR
        mafe = max(0.0, (entry_px - float(window["low"].min())) * PIP_FACTOR)
        mfe = max(0.0, (float(window["high"].max()) - entry_px) * PIP_FACTOR)
    else:
        gross = (entry_px - exit_px) * PIP_FACTOR
        mafe = max(0.0, (float(window["high"].max()) - entry_px) * PIP_FACTOR)
        mfe = max(0.0, (entry_px - float(window["low"].min())) * PIP_FACTOR)

    entry_iso = _iso(entry_ts)
    return Trade(
        candidate_id=CANDIDATES_BY_PATTERN[signal.pattern_id].candidate_id,
        signal_id=signal.signal_id,
        pattern_id=signal.pattern_id,
        pair=signal.pair,
        timeframe=signal.timeframe,
        direction=signal.direction,
        intrabar_resolve=intrabar_resolve,
        entry_ts=entry_iso,
        entry_px=entry_px,
        sl_px=sl_px,
        tp_px=tp_px,
        exit_ts=_iso(bars.index[exit_idx]),
        exit_px=float(exit_px),
        exit_reason=exit_reason,
        spread_pips_applied=spread,
        pnl_pips=gross - spread,
        mafe_pips=mafe,
        mfe_pips=mfe,
        hold_bars=exit_idx - entry_idx,
        is_train_oos=oos_label(entry_iso),
        wf_fold=wf_fold(entry_iso),
    )


def payoff_bev(avg_win: float, avg_loss: float) -> float:
    denom = avg_win + avg_loss
    if denom <= 0:
        return 1.0
    return min(1.0, max(0.0, avg_loss / denom))


def kelly_fraction(wr: float, payoff: float) -> float:
    if payoff <= 0 or not math.isfinite(payoff):
        return wr if payoff == math.inf else 0.0
    return wr - (1 - wr) / payoff


def stats_for_pnls(pnls: Iterable[float], trades: Sequence[Trade]) -> AggregateStats:
    vals = [float(v) for v in pnls]
    n = len(vals)
    if n == 0:
        return AggregateStats(0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0)
    wins = sum(1 for v in vals if v > 0)
    wr = wins / n
    win_vals = [v for v in vals if v > 0]
    loss_vals = [v for v in vals if v < 0]
    avg_win = sum(win_vals) / len(win_vals) if win_vals else 0.0
    avg_loss = abs(sum(loss_vals) / len(loss_vals)) if loss_vals else 0.0
    payoff = avg_win / avg_loss if avg_loss > 0 else math.inf
    bev = payoff_bev(avg_win, avg_loss)
    p_value = float(binomtest(wins, n, min(max(bev, 1e-12), 1 - 1e-12), alternative="greater").pvalue)
    return AggregateStats(
        n=n,
        wr=wr,
        ev_pips=sum(vals) / n,
        pf=profit_factor(vals),
        wilson_lo_95=wilson_lower(wins, n),
        bev_wr=bev,
        bonferroni_p=p_value,
        kelly=kelly_fraction(wr, payoff),
        max_dd_pips=max_drawdown_pips(vals),
    )


def decide_verdict(stats: AggregateStats, wf_pfs: Sequence[float | None]) -> tuple[str, str]:
    if stats.n < 30:
        return "INSUFFICIENT", "N<30"
    pf_value = 0.0 if stats.pf is None or not math.isfinite(stats.pf) else stats.pf
    if stats.wilson_lo_95 <= stats.bev_wr:
        return "REJECT", "Wilson_lo <= BEV"
    if pf_value < 1.0:
        return "REJECT", "PF<1.0"
    promote = (
        pf_value >= 1.5
        and stats.bonferroni_p < BONFERRONI_ALPHA
        and stats.kelly > 0
        and all(pf is not None and pf > 1.0 for pf in wf_pfs)
    )
    if promote:
        return "PROMOTE", "OOS and WF gates passed"
    if pf_value >= 1.2:
        return "SHADOW", "OOS weak gates passed; promote blocked"
    return "REJECT", "PF<1.2 shadow gate"


def ensure_schema(con: sqlite3.Connection) -> None:
    con.executescript(SQLITE_DDL)


def load_spread_profile(db_path: Path, pair: str) -> dict[int, float]:
    with sqlite3.connect(db_path) as con:
        rows = con.execute(
            """
            SELECT hour_utc, avg_round_trip_spread_pips
            FROM chart_pattern_bt_spread_profile
            WHERE pair=?
            ORDER BY hour_utc
            """,
            (pair,),
        ).fetchall()
    profile = {int(h): float(v) for h, v in rows}
    if set(profile) != set(range(24)):
        raise ValueError(f"spread profile must contain 24 hours for {pair}; got {sorted(profile)}")
    return profile


def load_signals(db_path: Path, pair: str, timeframe: str) -> list[Signal]:
    pattern_ids = tuple(sorted(CANDIDATES_BY_PATTERN))
    placeholders = ",".join("?" for _ in pattern_ids)
    sql = f"""
        SELECT id, pattern_id, pattern_name, direction, pair, timeframe, signal_ts, sl_px, tp_px
        FROM chart_pattern_signals
        WHERE pair=? AND timeframe=? AND pattern_id IN ({placeholders})
        ORDER BY signal_ts, pattern_id, id
    """
    with sqlite3.connect(db_path) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(sql, (pair, timeframe, *pattern_ids)).fetchall()
    return [
        Signal(
            signal_id=int(r["id"]),
            pattern_id=int(r["pattern_id"]),
            pattern_name=str(r["pattern_name"]),
            direction=str(r["direction"]),
            pair=str(r["pair"]),
            timeframe=str(r["timeframe"]),
            signal_ts=str(r["signal_ts"]),
            sl_px=float(r["sl_px"]),
            frozen_tp_px=float(r["tp_px"]),
        )
        for r in rows
    ]


def simulate_signals(signals: Sequence[Signal], bars: pd.DataFrame, spread_profile: dict[int, float]) -> list[Trade]:
    trades: list[Trade] = []
    bars = normalize_ohlc(bars)
    for signal in signals:
        for resolve in INTRABAR_RESOLVES:
            trade = simulate_trade(signal, bars, spread_profile, resolve)
            if trade is not None:
                trades.append(trade)
    return trades


def _stats_for_trades(trades: Sequence[Trade]) -> AggregateStats:
    return stats_for_pnls([t.pnl_pips for t in trades], trades)


def build_verdict_rows(trades: Sequence[Trade]) -> list[VerdictRow]:
    rows: list[VerdictRow] = []
    for candidate in CANDIDATES.values():
        for resolve in INTRABAR_RESOLVES:
            scoped = [t for t in trades if t.candidate_id == candidate.candidate_id and t.intrabar_resolve == resolve]
            wf_pfs = []
            for fold in (1, 2, 3):
                fold_trades = [t for t in scoped if t.wf_fold == fold]
                wf_pfs.append(profit_factor([t.pnl_pips for t in fold_trades]) if fold_trades else None)
            split_groups = {
                "OOS_1": [t for t in scoped if t.is_train_oos == "OOS"],
                "WF_1": [t for t in scoped if t.wf_fold == 1],
                "WF_2": [t for t in scoped if t.wf_fold == 2],
                "WF_3": [t for t in scoped if t.wf_fold == 3],
            }
            for split, group in split_groups.items():
                stats = _stats_for_trades(group)
                if split == "OOS_1":
                    verdict, reason = decide_verdict(stats, wf_pfs)
                else:
                    verdict, reason = decide_verdict(stats, wf_pfs=[])
                    reason = f"auxiliary {split}: {reason}"
                rows.append(
                    VerdictRow(
                        candidate.candidate_id,
                        candidate.pattern_id,
                        resolve,
                        split,
                        stats.n,
                        stats.wr,
                        stats.ev_pips,
                        stats.pf,
                        stats.wilson_lo_95,
                        stats.bev_wr,
                        stats.bonferroni_p,
                        BONFERRONI_ALPHA,
                        stats.kelly,
                        stats.max_dd_pips,
                        verdict,
                        reason,
                    )
                )
    return rows


def _finite_or_none(value: float | None) -> float | None:
    if value is None or not math.isfinite(value):
        return None
    return float(value)


def write_results(db_path: Path, trades: Sequence[Trade], verdicts: Sequence[VerdictRow]) -> None:
    with sqlite3.connect(db_path) as con:
        ensure_schema(con)
        con.executemany(
            """
            INSERT INTO chart_pattern_w2b_trades (
                candidate_id, signal_id, pattern_id, pair, timeframe, direction, intrabar_resolve,
                entry_ts, entry_px, sl_px, tp_px, exit_ts, exit_px, exit_reason,
                spread_pips_applied, pnl_pips, mafe_pips, mfe_pips, hold_bars, is_train_oos, wf_fold
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    t.candidate_id,
                    t.signal_id,
                    t.pattern_id,
                    t.pair,
                    t.timeframe,
                    t.direction,
                    t.intrabar_resolve,
                    t.entry_ts,
                    t.entry_px,
                    t.sl_px,
                    t.tp_px,
                    t.exit_ts,
                    t.exit_px,
                    t.exit_reason,
                    t.spread_pips_applied,
                    t.pnl_pips,
                    t.mafe_pips,
                    t.mfe_pips,
                    t.hold_bars,
                    t.is_train_oos,
                    t.wf_fold,
                )
                for t in trades
            ],
        )
        con.executemany(
            """
            INSERT INTO chart_pattern_w2b_verdicts (
                candidate_id, pattern_id, intrabar_resolve, eval_split, n, wr, ev_pips, pf,
                wilson_lo_95, bev_wr, bonferroni_p, bonferroni_alpha, kelly, max_dd_pips,
                verdict, verdict_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(candidate_id, intrabar_resolve, eval_split) DO UPDATE SET
                pattern_id=excluded.pattern_id,
                n=excluded.n,
                wr=excluded.wr,
                ev_pips=excluded.ev_pips,
                pf=excluded.pf,
                wilson_lo_95=excluded.wilson_lo_95,
                bev_wr=excluded.bev_wr,
                bonferroni_p=excluded.bonferroni_p,
                bonferroni_alpha=excluded.bonferroni_alpha,
                kelly=excluded.kelly,
                max_dd_pips=excluded.max_dd_pips,
                verdict=excluded.verdict,
                verdict_reason=excluded.verdict_reason,
                created_at=datetime('now')
            """,
            [
                (
                    v.candidate_id,
                    v.pattern_id,
                    v.intrabar_resolve,
                    v.eval_split,
                    v.n,
                    v.wr,
                    v.ev_pips,
                    _finite_or_none(v.pf),
                    v.wilson_lo_95,
                    v.bev_wr,
                    v.bonferroni_p,
                    v.bonferroni_alpha,
                    v.kelly,
                    v.max_dd_pips,
                    v.verdict,
                    v.verdict_reason,
                )
                for v in verdicts
            ],
        )
        con.commit()


def run_backtest(db_path: Path, parquet_path: Path, pair: str, timeframe: str, write_db: bool = True) -> tuple[list[Trade], list[VerdictRow]]:
    spread_profile = load_spread_profile(db_path, pair)
    signals = load_signals(db_path, pair, timeframe)
    bars = pd.read_parquet(parquet_path)
    trades = simulate_signals(signals, bars, spread_profile)
    verdicts = build_verdict_rows(trades)
    if write_db:
        write_results(db_path, trades, verdicts)
    return trades, verdicts


def run_self_test() -> dict[str, str]:
    bars = pd.DataFrame(
        {"open": [100.0, 100.0], "high": [100.01, 100.20], "low": [99.99, 99.80], "close": [100.0, 100.0]},
        index=pd.to_datetime(["2026-01-01 12:00", "2026-01-01 12:05"], utc=True),
    )
    signal = Signal(1, 8, "triple_bottom", "BUY", "USD_JPY", "M5", "2026-01-01T12:00:00+00:00", 99.90, 100.30)
    sl_first = simulate_trade(signal, bars, {12: 1.0}, "SL_FIRST")
    tp_first = simulate_trade(signal, bars, {12: 1.0}, "TP_FIRST")
    assert sl_first is not None and sl_first.exit_reason == "SL"
    assert tp_first is not None and tp_first.exit_reason == "TP"
    assert math.isclose(recompute_tp("BUY", 100.0, 99.9), 100.125)
    assert is_london_ny_overlap("2026-01-01T15:59:00+00:00")
    assert not is_london_ny_overlap("2026-01-01T16:00:00+00:00")
    return {"SELF_TEST_PASS": "ok"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        for key, value in run_self_test().items():
            print(f"{key}: {value}")
        return 0
    parser.error("use tools/s6_run_w2b.py for production runs")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
