#!/usr/bin/env python3
"""S6 Wave 2c cross-pair validator.

No LIVE/Shadow/OANDA access. Existing detector output is treated as frozen when
present; an empty local DB may be seeded from the archived W1P0 SQLite artifact.

Locked W2c DDL:

CREATE TABLE IF NOT EXISTS chart_pattern_w2c_cross_pair_verdicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_id INTEGER NOT NULL,
    pattern_name TEXT NOT NULL,
    pair TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    axis TEXT NOT NULL CHECK (axis IN ('isolated','regime_BULL','regime_BEAR')),
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
    max_dd_pips REAL NOT NULL,
    spread_pips_used REAL NOT NULL,
    spread_source TEXT NOT NULL,
    verdict TEXT NOT NULL CHECK (verdict IN ('PROMOTE','SHADOW','REJECT','INSUFFICIENT')),
    cross_pair_consistency TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(pattern_id, pair, timeframe, axis)
);
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import math
import sqlite3
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import s6_chart_pattern_detector as detector


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "chart_patterns.db"
W1P0_ARCHIVE_DB = ROOT / "knowledge-base" / "raw" / "bt-results" / "s6-w1p0-production-2026-05-04.sqlite"
MASSIVE_DIR = ROOT / "data" / "cache" / "massive"
DEMO_DB_CANDIDATES = (ROOT / "data" / "demo_trades.db", ROOT / "demo_trades.db")

PIP_FACTOR_BY_PAIR = {"EUR_USD": 10000.0}
DEFAULT_JPY_PIP_FACTOR = 100.0
MAX_HOLD_BARS = 20
PRIMARY_M = 24
REGIME_M = 48
ALPHA = 0.05
DEFAULT_SPREADS = {"GBP_JPY": 2.5, "EUR_USD": 1.2, "USD_JPY": 1.5}


SIGNALS_DDL = detector.SQLITE_DDL

BT_DDL = """
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

W2C_DDL = """
CREATE TABLE IF NOT EXISTS chart_pattern_w2c_cross_pair_verdicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_id INTEGER NOT NULL,
    pattern_name TEXT NOT NULL,
    pair TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    axis TEXT NOT NULL CHECK (axis IN ('isolated','regime_BULL','regime_BEAR')),
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
    max_dd_pips REAL NOT NULL,
    spread_pips_used REAL NOT NULL,
    spread_source TEXT NOT NULL,
    verdict TEXT NOT NULL CHECK (verdict IN ('PROMOTE','SHADOW','REJECT','INSUFFICIENT')),
    cross_pair_consistency TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(pattern_id, pair, timeframe, axis)
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
    signal_id: int
    pattern_id: int
    pattern_name: str
    direction: str
    pair: str
    timeframe: str
    entry_ts: str
    entry_px: float
    exit_ts: str
    exit_px: float
    exit_reason: str
    pnl_pips: float
    mafe_pips: float
    mfe_pips: float
    hold_bars: int
    bt_run_id: str
    sl_px: float
    tp_px: float
    d1_regime: str = "UNKNOWN"


@dataclass(frozen=True)
class Stats:
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
    pattern_id: int
    pattern_name: str
    pair: str
    timeframe: str
    axis: str
    stats: Stats
    bonferroni_alpha: float
    bonferroni_m: int
    spread_pips_used: float
    spread_source: str
    verdict: str
    cross_pair_consistency: str
    notes: str = ""


def pip_factor(pair: str) -> float:
    return PIP_FACTOR_BY_PAIR.get(pair, DEFAULT_JPY_PIP_FACTOR if pair.endswith("_JPY") else 10000.0)


def iso(ts) -> str:
    return pd.Timestamp(ts).tz_convert("UTC").isoformat()


def normalize_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    if df.attrs.get("s6_w2c_normalized_ohlc"):
        return df
    out = df.copy()
    out = out.rename(columns={c: c.lower() for c in out.columns})
    missing = {"open", "high", "low", "close"} - set(out.columns)
    if missing:
        raise ValueError(f"OHLC missing columns: {sorted(missing)}")
    out.index = pd.to_datetime(out.index, utc=True)
    out = out.sort_index()
    out.attrs["s6_w2c_normalized_ohlc"] = True
    return out


def ensure_schema(con: sqlite3.Connection) -> None:
    con.executescript(SIGNALS_DDL)
    con.executescript(BT_DDL)
    con.executescript(W2C_DDL)


def table_exists(con: sqlite3.Connection, table: str) -> bool:
    row = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    return row is not None


def seed_usdjpy_signals_if_empty(db_path: Path = DB_PATH, archive_path: Path = W1P0_ARCHIVE_DB) -> bool:
    if not archive_path.exists():
        return False
    with sqlite3.connect(db_path) as con:
        ensure_schema(con)
        current = con.execute("SELECT COUNT(*) FROM chart_pattern_signals WHERE pair='USD_JPY'").fetchone()[0]
        if current:
            return False
        con.execute("ATTACH DATABASE ? AS w1", (str(archive_path),))
        con.execute(
            """
            INSERT OR IGNORE INTO chart_pattern_signals (
                id, pattern_id, pattern_name, direction, pair, timeframe, signal_ts, detection_ts,
                entry_px, sl_px, tp_px, pattern_height_atr, duration_bars, atr_at_detection,
                pivot_anchor_ts, pivot_opposite_ts, pivot_count, confidence_score, raw_geometry_json,
                created_at
            )
            SELECT
                id, pattern_id, pattern_name, direction, pair, timeframe, signal_ts, detection_ts,
                entry_px, sl_px, tp_px, pattern_height_atr, duration_bars, atr_at_detection,
                pivot_anchor_ts, pivot_opposite_ts, pivot_count, confidence_score, raw_geometry_json,
                created_at
            FROM w1.chart_pattern_signals
            WHERE pair='USD_JPY' AND timeframe='M5'
            """
        )
        con.commit()
        con.execute("DETACH DATABASE w1")
        return True


def insert_signals(db_path: Path, signals: Sequence[detector.ChartPatternSignal]) -> int:
    with sqlite3.connect(db_path) as con:
        ensure_schema(con)
        before = con.execute(
            "SELECT COUNT(*) FROM chart_pattern_signals WHERE pair=? AND timeframe=?",
            (signals[0].pair, signals[0].timeframe) if signals else ("", ""),
        ).fetchone()[0] if signals else 0
        con.executemany(
            """
            INSERT OR IGNORE INTO chart_pattern_signals (
                pattern_id, pattern_name, direction, pair, timeframe, signal_ts, detection_ts,
                entry_px, sl_px, tp_px, pattern_height_atr, duration_bars, atr_at_detection,
                pivot_anchor_ts, pivot_opposite_ts, pivot_count, confidence_score, raw_geometry_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    s.pattern_id,
                    s.pattern_name,
                    s.direction,
                    s.pair,
                    s.timeframe,
                    s.signal_ts,
                    s.detection_ts,
                    s.entry_px,
                    s.sl_px,
                    s.tp_px,
                    s.pattern_height_atr,
                    s.duration_bars,
                    s.atr_at_detection,
                    s.pivot_anchor_ts,
                    s.pivot_opposite_ts,
                    s.pivot_count,
                    s.confidence_score,
                    s.raw_geometry_json,
                )
                for s in signals
            ],
        )
        after = con.execute(
            "SELECT COUNT(*) FROM chart_pattern_signals WHERE pair=? AND timeframe=?",
            (signals[0].pair, signals[0].timeframe) if signals else ("", ""),
        ).fetchone()[0] if signals else before
        con.commit()
        return after - before


def run_detector_if_needed(db_path: Path, pair: str, timeframe: str, parquet_path: Path) -> int:
    with sqlite3.connect(db_path) as con:
        ensure_schema(con)
        count = con.execute(
            "SELECT COUNT(*) FROM chart_pattern_signals WHERE pair=? AND timeframe=?",
            (pair, timeframe),
        ).fetchone()[0]
    if count:
        return count
    df = pd.read_parquet(parquet_path)
    signals = detector.detect_chart_patterns(df, pair=pair, timeframe=timeframe)
    insert_signals(db_path, signals)
    return len(signals)


def load_signals(db_path: Path, pair: str, timeframe: str) -> list[Signal]:
    with sqlite3.connect(db_path) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            """
            SELECT id, pattern_id, pattern_name, direction, pair, timeframe, signal_ts, sl_px, tp_px,
                   COALESCE(confidence_score, 0.0) AS confidence_score
            FROM chart_pattern_signals
            WHERE pair=? AND timeframe=?
            ORDER BY signal_ts, pattern_id, id
            """,
            (pair, timeframe),
        ).fetchall()
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
            tp_px=float(r["tp_px"]),
            confidence_score=float(r["confidence_score"]),
        )
        for r in rows
    ]


def resolve_spread(pair: str, demo_paths: Sequence[Path] = DEMO_DB_CANDIDATES) -> tuple[float, str]:
    for path in demo_paths:
        if not path.exists() or path.stat().st_size == 0:
            continue
        try:
            with sqlite3.connect(path) as con:
                row = con.execute(
                    "SELECT AVG(spread_at_entry) FROM demo_trades WHERE instrument=? AND spread_at_entry > 0",
                    (pair,),
                ).fetchone()
        except sqlite3.Error:
            continue
        if row and row[0] is not None:
            return float(row[0]), "demo_trades_empirical"
    return float(DEFAULT_SPREADS.get(pair, 2.5)), "literature_default"


def simulate_trade(signal: Signal, bars: pd.DataFrame, spread_pips: float) -> Trade | None:
    bars = normalize_ohlc(bars)
    signal_ts = pd.Timestamp(signal.signal_ts)
    signal_ts = signal_ts.tz_localize("UTC") if signal_ts.tzinfo is None else signal_ts.tz_convert("UTC")
    entry_idx = int(bars.index.searchsorted(signal_ts, side="right"))
    if entry_idx >= len(bars):
        return None
    timeout_idx = entry_idx + MAX_HOLD_BARS
    end_idx = min(timeout_idx, len(bars) - 1)
    exit_idx = end_idx
    entry_px = float(bars["open"].iloc[entry_idx])
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

    factor = pip_factor(signal.pair)
    window = bars.iloc[entry_idx : exit_idx + 1]
    if signal.direction == "BUY":
        gross = (exit_px - entry_px) * factor
        mafe = max(0.0, (entry_px - float(window["low"].min())) * factor)
        mfe = max(0.0, (float(window["high"].max()) - entry_px) * factor)
    else:
        gross = (entry_px - exit_px) * factor
        mafe = max(0.0, (float(window["high"].max()) - entry_px) * factor)
        mfe = max(0.0, (entry_px - float(window["low"].min())) * factor)
    return Trade(
        signal_id=signal.signal_id,
        pattern_id=signal.pattern_id,
        pattern_name=signal.pattern_name,
        direction=signal.direction,
        pair=signal.pair,
        timeframe=signal.timeframe,
        entry_ts=iso(bars.index[entry_idx]),
        entry_px=entry_px,
        exit_ts=iso(bars.index[exit_idx]),
        exit_px=exit_px,
        exit_reason=exit_reason,
        pnl_pips=gross - spread_pips,
        mafe_pips=mafe,
        mfe_pips=mfe,
        hold_bars=exit_idx - entry_idx,
        bt_run_id="isolated",
        sl_px=signal.sl_px,
        tp_px=signal.tp_px,
    )


def simulate_signals(signals: Sequence[Signal], bars: pd.DataFrame, spread_pips: float) -> list[Trade]:
    bars = normalize_ohlc(bars)
    out: list[Trade] = []
    for sig in signals:
        trade = simulate_trade(sig, bars, spread_pips)
        if trade is not None:
            out.append(trade)
    return out


def write_trades(db_path: Path, pair: str, timeframe: str, trades: Sequence[Trade]) -> None:
    with sqlite3.connect(db_path) as con:
        ensure_schema(con)
        con.execute(
            "DELETE FROM chart_pattern_bt_trades WHERE pair=? AND timeframe=? AND bt_run_id='isolated'",
            (pair, timeframe),
        )
        con.executemany(
            """
            INSERT INTO chart_pattern_bt_trades (
                signal_id, pattern_id, pattern_name, direction, pair, timeframe, entry_ts, entry_px,
                exit_ts, exit_px, exit_reason, pnl_pips, mafe_pips, mfe_pips, hold_bars,
                bt_run_id, arbitration_loser_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
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
                )
                for t in trades
            ],
        )
        con.commit()


def load_trades(db_path: Path, pair: str, timeframe: str) -> list[Trade]:
    with sqlite3.connect(db_path) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            """
            SELECT t.signal_id, t.pattern_id, t.pattern_name, t.direction, t.pair, t.timeframe,
                   t.entry_ts, t.entry_px, t.exit_ts, t.exit_px, t.exit_reason, t.pnl_pips,
                   t.mafe_pips, t.mfe_pips, t.hold_bars, t.bt_run_id, s.sl_px, s.tp_px
            FROM chart_pattern_bt_trades t
            JOIN chart_pattern_signals s ON s.id=t.signal_id
            WHERE t.pair=? AND t.timeframe=? AND t.bt_run_id='isolated'
            ORDER BY t.entry_ts, t.signal_id
            """,
            (pair, timeframe),
        ).fetchall()
    return [
        Trade(
            signal_id=int(r["signal_id"]),
            pattern_id=int(r["pattern_id"]),
            pattern_name=str(r["pattern_name"]),
            direction=str(r["direction"]),
            pair=str(r["pair"]),
            timeframe=str(r["timeframe"]),
            entry_ts=str(r["entry_ts"]),
            entry_px=float(r["entry_px"]),
            exit_ts=str(r["exit_ts"]),
            exit_px=float(r["exit_px"]),
            exit_reason=str(r["exit_reason"]),
            pnl_pips=float(r["pnl_pips"]),
            mafe_pips=float(r["mafe_pips"]),
            mfe_pips=float(r["mfe_pips"]),
            hold_bars=int(r["hold_bars"]),
            bt_run_id=str(r["bt_run_id"]),
            sl_px=float(r["sl_px"]),
            tp_px=float(r["tp_px"]),
        )
        for r in rows
    ]


def wilson_lower(wins: int, n: int, z: float = 1.959963984540054) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    denom = 1 + z * z / n
    center = p + z * z / (2 * n)
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return max(0.0, (center - half) / denom)


def profit_factor(pnls: Iterable[float]) -> float | None:
    vals = list(pnls)
    gross_win = sum(v for v in vals if v > 0)
    gross_loss = abs(sum(v for v in vals if v < 0))
    if gross_loss == 0:
        return math.inf if gross_win > 0 else 0.0
    return gross_win / gross_loss


def payoff_bev(avg_win: float, avg_loss: float) -> float:
    denom = avg_win + avg_loss
    if denom <= 0:
        return 1.0
    return min(1.0, max(0.0, avg_loss / denom))


def binomial_edge_p(wins: int, n: int, bev: float) -> float:
    if n <= 0:
        return 1.0
    p = min(max(bev, 1e-12), 1 - 1e-12)
    if n > 1000:
        mean = n * p
        var = n * p * (1 - p)
        if var <= 0:
            return 0.0 if wins > mean else 1.0
        z = ((wins - 0.5) - mean) / math.sqrt(var)
        return 0.5 * math.erfc(z / math.sqrt(2))
    k = max(0, min(wins, n))
    logs: list[float] = []
    logp = math.log(p)
    logq = math.log1p(-p)
    for i in range(k, n + 1):
        logs.append(math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * logp + (n - i) * logq)
    m = max(logs)
    return min(1.0, math.exp(m) * sum(math.exp(v - m) for v in logs))


def max_drawdown_pips(pnls: Iterable[float]) -> float:
    equity = 0.0
    peak = 0.0
    dd = 0.0
    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        dd = min(dd, equity - peak)
    return dd


def aggregate(trades: Sequence[Trade]) -> Stats:
    vals = [float(t.pnl_pips) for t in trades]
    n = len(vals)
    if n == 0:
        return Stats(0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0)
    wins = sum(1 for v in vals if v > 0)
    win_vals = [v for v in vals if v > 0]
    loss_vals = [v for v in vals if v < 0]
    avg_win = sum(win_vals) / len(win_vals) if win_vals else 0.0
    avg_loss = abs(sum(loss_vals) / len(loss_vals)) if loss_vals else 0.0
    pf = profit_factor(vals)
    wr = wins / n
    bev = payoff_bev(avg_win, avg_loss)
    payoff = avg_win / avg_loss if avg_loss > 0 else math.inf
    if payoff == math.inf:
        kelly = wr
    elif payoff > 0 and math.isfinite(payoff):
        kelly = wr - (1 - wr) / payoff
    else:
        kelly = 0.0
    return Stats(
        n=n,
        wr=wr,
        ev_pips=sum(vals) / n,
        pf=pf,
        wilson_lo_95=wilson_lower(wins, n),
        bev_wr=bev,
        bonferroni_p=binomial_edge_p(wins, n, bev),
        kelly=kelly,
        max_dd_pips=max_drawdown_pips(vals),
    )


def decide(stats: Stats, bonf_m: int) -> str:
    if stats.n < 100:
        return "INSUFFICIENT"
    pf_value = 0.0 if stats.pf is None or not math.isfinite(stats.pf) else stats.pf
    core = (
        stats.ev_pips > 0
        and pf_value >= 1.3
        and stats.wilson_lo_95 > stats.bev_wr
        and stats.bonferroni_p < ALPHA / bonf_m
        and stats.kelly > 0
    )
    if not core:
        return "REJECT"
    return "PROMOTE" if stats.kelly >= 0.05 else "SHADOW"


def d1_regime_map(bars: pd.DataFrame) -> pd.DataFrame:
    bars = normalize_ohlc(bars)
    daily = bars["close"].resample("1D").last().dropna().to_frame("d1_close")
    daily["d1_ema200"] = daily["d1_close"].ewm(span=200, adjust=False, min_periods=200).mean()
    daily["d1_regime"] = [
        "BULL" if c > e else "BEAR" if c <= e else "UNKNOWN"
        for c, e in zip(daily["d1_close"], daily["d1_ema200"])
    ]
    return daily[["d1_regime"]].reset_index().rename(columns={daily.index.name or "index": "day_ts"})


def tag_regimes(trades: Sequence[Trade], bars: pd.DataFrame) -> list[Trade]:
    if not trades:
        return []
    regimes = d1_regime_map(bars)
    entry_dt = pd.to_datetime([t.entry_ts for t in trades], utc=True).as_unit("ns")
    df = pd.DataFrame({"idx": range(len(trades)), "entry_dt": entry_dt})
    df["entry_key"] = entry_dt.astype("int64")
    regimes = regimes.copy()
    regime_dt = pd.to_datetime(regimes["day_ts"], utc=True).dt.as_unit("ns")
    regimes["day_key"] = regime_dt.astype("int64")
    merged = pd.merge_asof(df.sort_values("entry_key"), regimes.sort_values("day_key"), left_on="entry_key", right_on="day_key", direction="backward")
    regime_by_idx = {int(r.idx): str(r.d1_regime) for r in merged.itertuples() if str(r.d1_regime) in {"BULL", "BEAR"}}
    out: list[Trade] = []
    for i, trade in enumerate(trades):
        out.append(dataclasses.replace(trade, d1_regime=regime_by_idx.get(i, "UNKNOWN")))
    return out


def cross_pair_consistency(pattern_id: int, axis: str, verdict: str, n: int) -> str:
    if n < 100:
        return "N_INSUFFICIENT"
    usd_null = True
    if verdict in {"PROMOTE", "SHADOW"} and usd_null:
        return "CONTRADICTS_USDJPY"
    return "CONFIRMS_USDJPY"


def build_verdict_rows(
    trades: Sequence[Trade],
    pair: str,
    timeframe: str,
    spread: float,
    spread_source: str,
) -> list[VerdictRow]:
    rows: list[VerdictRow] = []
    by_pattern: dict[int, list[Trade]] = defaultdict(list)
    for trade in trades:
        by_pattern[trade.pattern_id].append(trade)
    for spec in detector.PATTERNS:
        group = by_pattern.get(spec.pattern_id, [])
        stats = aggregate(group)
        verdict = decide(stats, PRIMARY_M)
        rows.append(
            VerdictRow(
                spec.pattern_id,
                spec.name,
                pair,
                timeframe,
                "isolated",
                stats,
                ALPHA / PRIMARY_M,
                PRIMARY_M,
                spread,
                spread_source,
                verdict,
                cross_pair_consistency(spec.pattern_id, "isolated", verdict, stats.n),
            )
        )
        for regime in ("BULL", "BEAR"):
            rg = [t for t in group if t.d1_regime == regime]
            rstats = aggregate(rg)
            rverdict = decide(rstats, REGIME_M)
            rows.append(
                VerdictRow(
                    spec.pattern_id,
                    spec.name,
                    pair,
                    timeframe,
                    f"regime_{regime}",
                    rstats,
                    ALPHA / REGIME_M,
                    REGIME_M,
                    spread,
                    spread_source,
                    rverdict,
                    cross_pair_consistency(spec.pattern_id, f"regime_{regime}", rverdict, rstats.n),
                    "D1 EMA200 regime",
                )
            )
    return rows


def write_verdict_rows(db_path: Path, pair: str, timeframe: str, rows: Sequence[VerdictRow]) -> None:
    with sqlite3.connect(db_path) as con:
        ensure_schema(con)
        con.executemany(
            """
            INSERT INTO chart_pattern_w2c_cross_pair_verdicts (
                pattern_id, pattern_name, pair, timeframe, axis, n, wr, ev_pips, pf,
                wilson_lo_95, bev_wr, bonferroni_p, bonferroni_alpha, bonferroni_m,
                kelly, max_dd_pips, spread_pips_used, spread_source, verdict,
                cross_pair_consistency, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(pattern_id, pair, timeframe, axis) DO UPDATE SET
                pattern_name=excluded.pattern_name,
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
                max_dd_pips=excluded.max_dd_pips,
                spread_pips_used=excluded.spread_pips_used,
                spread_source=excluded.spread_source,
                verdict=excluded.verdict,
                cross_pair_consistency=excluded.cross_pair_consistency,
                notes=excluded.notes,
                created_at=datetime('now')
            """,
            [
                (
                    r.pattern_id,
                    r.pattern_name,
                    r.pair,
                    r.timeframe,
                    r.axis,
                    r.stats.n,
                    r.stats.wr,
                    r.stats.ev_pips,
                    None if r.stats.pf is None or math.isinf(r.stats.pf) else r.stats.pf,
                    r.stats.wilson_lo_95,
                    r.stats.bev_wr,
                    r.stats.bonferroni_p,
                    r.bonferroni_alpha,
                    r.bonferroni_m,
                    r.stats.kelly,
                    r.stats.max_dd_pips,
                    r.spread_pips_used,
                    r.spread_source,
                    r.verdict,
                    r.cross_pair_consistency,
                    r.notes,
                )
                for r in rows
            ],
        )
        con.commit()


def parquet_for(pair: str) -> Path:
    return MASSIVE_DIR / f"{pair}_5m.parquet"


def run_pair(pair: str, timeframe: str = "M5", db_path: Path = DB_PATH, aux_only: bool = False) -> list[VerdictRow]:
    parquet_path = parquet_for(pair)
    if not parquet_path.exists():
        print(json.dumps({"pair": pair, "status": "MISSING_PARQUET", "path": str(parquet_path)}))
        return []
    seed_usdjpy_signals_if_empty(db_path)
    run_detector_if_needed(db_path, pair, timeframe, parquet_path)
    bars = pd.read_parquet(parquet_path)
    spread, spread_source = resolve_spread(pair)
    signals = load_signals(db_path, pair, timeframe)
    trades = simulate_signals(signals, bars, spread)
    trades = tag_regimes(trades, bars)
    if not aux_only:
        write_trades(db_path, pair, timeframe, trades)
    rows = build_verdict_rows(trades, pair, timeframe, spread, spread_source)
    if not aux_only:
        write_verdict_rows(db_path, pair, timeframe, rows)
    return rows


def run_self_test() -> dict[str, str]:
    assert math.isclose(wilson_lower(50, 100), 0.4038315303659956)
    assert resolve_spread("GBP_JPY", demo_paths=[])[0] == 2.5
    stats = aggregate([dataclasses.replace(_dummy_trade(), pnl_pips=10.0) for _ in range(80)] + [dataclasses.replace(_dummy_trade(), pnl_pips=-5.0) for _ in range(20)])
    assert stats.n == 100 and stats.pf == 8.0 and stats.ev_pips == 7.0
    assert decide(stats, PRIMARY_M) in {"PROMOTE", "SHADOW"}
    weak = aggregate([dataclasses.replace(_dummy_trade(), pnl_pips=1.0) for _ in range(60)] + [dataclasses.replace(_dummy_trade(), pnl_pips=-2.0) for _ in range(40)])
    assert decide(weak, PRIMARY_M) == "REJECT"
    assert cross_pair_consistency(1, "isolated", "REJECT", 100) == "CONFIRMS_USDJPY"
    assert cross_pair_consistency(1, "isolated", "PROMOTE", 100) == "CONTRADICTS_USDJPY"
    assert cross_pair_consistency(1, "isolated", "REJECT", 99) == "N_INSUFFICIENT"
    return {"SELF_TEST_PASS": "ok"}


def _dummy_trade() -> Trade:
    return Trade(
        signal_id=1,
        pattern_id=1,
        pattern_name="ascending_triangle",
        direction="BUY",
        pair="GBP_JPY",
        timeframe="M5",
        entry_ts="2026-01-01T00:00:00+00:00",
        entry_px=100.0,
        exit_ts="2026-01-01T00:05:00+00:00",
        exit_px=100.1,
        exit_reason="TP",
        pnl_pips=1.0,
        mafe_pips=0.0,
        mfe_pips=1.0,
        hold_bars=1,
        bt_run_id="isolated",
        sl_px=99.9,
        tp_px=100.1,
    )


def format_rows(rows: Sequence[VerdictRow]) -> str:
    return "\n".join(
        f"{r.pattern_name}\t{r.axis}\t{r.stats.n}\t{r.stats.wr:.3f}\t{r.stats.ev_pips:.2f}\t"
        f"{0.0 if r.stats.pf is None else r.stats.pf:.2f}\t{r.stats.wilson_lo_95:.3f}\t"
        f"{r.stats.bonferroni_p:.5g}\t{r.verdict}\t{r.cross_pair_consistency}"
        for r in rows
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--pair", default="GBP_JPY")
    parser.add_argument("--tf", default="M5")
    parser.add_argument("--aux-only", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        for k, v in run_self_test().items():
            print(f"{k}: {v}")
        return 0
    rows = run_pair(args.pair, args.tf, aux_only=args.aux_only)
    if rows:
        print(format_rows(rows))
        return 0
    return 0 if args.aux_only else 1


if __name__ == "__main__":
    raise SystemExit(main())
