#!/usr/bin/env python3
"""Stage 0 BT runner for EMA10 x M15 x 4-pattern pullback.

This module keeps I/O at the CLI layer. The exported functions operate on
DataFrames and plain values so the pre-registered mechanics can be unit tested
without touching production strategy code.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.stats import binomtest


PIP_SIZE_BY_PAIR = {"USD_JPY": 0.01}
DEFAULT_CACHE = Path("data/cache/massive/USD_JPY_5m_2014_2026.parquet")
FALLBACK_CACHE = Path("data/cache/massive/USD_JPY_5m.parquet")
RESAMPLE_METHOD = "M5 closed=left label=left -> M15"
FORBIDDEN_WEEKDAY_START_HOUR = 22
UNIT_NOTIONAL = 100_000


@dataclass(frozen=True)
class Position:
    side: str
    entry_ts: pd.Timestamp
    entry_idx: int
    signal_ts: pd.Timestamp
    entry_price: float
    sl: float
    tp: float
    pattern: str


@dataclass(frozen=True)
class Trade:
    side: str
    pattern: str
    signal_ts: pd.Timestamp
    entry_ts: pd.Timestamp
    exit_ts: pd.Timestamp
    entry_price: float
    exit_price: float
    sl: float
    tp: float
    pnl_pip: float
    exit_reason: str
    entry_open: float
    exit_open: float | None
    exit_high: float
    exit_low: float
    exit_close: float


def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Return UTC-indexed OHLCV with capitalized column names from real cache."""
    rename = {c: str(c).capitalize() for c in df.columns}
    out = df.rename(columns=rename).copy()
    missing = {"Open", "High", "Low", "Close", "Volume"} - set(out.columns)
    if missing:
        raise ValueError(f"OHLCV cache missing columns: {sorted(missing)}")
    out = out[["Open", "High", "Low", "Close", "Volume"]].copy()
    out.index = pd.to_datetime(out.index, utc=True)
    out = out.sort_index()
    return out


def resample_m5_to_m15(df_m5: pd.DataFrame) -> pd.DataFrame:
    """M5 -> M15 OHLC resample with closed='left', label='left'."""
    df = normalize_ohlcv(df_m5)
    return (
        df.resample("15min", closed="left", label="left")
        .agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"})
        .dropna()
    )


def filter_weekend_bars(df: pd.DataFrame) -> pd.DataFrame:
    idx = df.index
    mask = ~(
        ((idx.dayofweek == 4) & (idx.hour >= FORBIDDEN_WEEKDAY_START_HOUR))
        | (idx.dayofweek == 5)
        | ((idx.dayofweek == 6) & (idx.hour < FORBIDDEN_WEEKDAY_START_HOUR))
    )
    return df.loc[mask].copy()


def is_bull_pinbar(open_, high, low, close) -> bool:
    body = abs(close - open_)
    rng = high - low
    if rng == 0:
        return False
    lower_wick = min(open_, close) - low
    return lower_wick >= 2 * body and body / rng <= 0.4 and close > open_


def is_bull_hammer_bear(open_, high, low, close) -> bool:
    body = abs(close - open_)
    rng = high - low
    if rng == 0:
        return False
    lower_wick = min(open_, close) - low
    return lower_wick >= 2 * body and close < open_


def is_bullish_engulfing(prev_open, prev_close, open_, close) -> bool:
    return close > open_ and open_ <= prev_close and close >= prev_open and prev_close < prev_open


def is_bullish_harami_breakout(prev_open, prev_close, prev_high, prev_low, open_, close) -> bool:
    # Pre-reg text locks only previous bearish candle and current close breakout.
    if prev_close >= prev_open:
        return False
    return close > open_ and close > prev_high


def is_bear_pinbar(open_, high, low, close) -> bool:
    body = abs(close - open_)
    rng = high - low
    if rng == 0:
        return False
    upper_wick = high - max(open_, close)
    return upper_wick >= 2 * body and body / rng <= 0.4 and close < open_


def is_bear_hammer_bull(open_, high, low, close) -> bool:
    body = abs(close - open_)
    rng = high - low
    if rng == 0:
        return False
    upper_wick = high - max(open_, close)
    return upper_wick >= 2 * body and close > open_


def is_bearish_engulfing(prev_open, prev_close, open_, close) -> bool:
    return close < open_ and open_ >= prev_close and close <= prev_open and prev_close > prev_open


def is_bearish_harami_breakout(prev_open, prev_close, prev_high, prev_low, open_, close) -> bool:
    if prev_close <= prev_open:
        return False
    return close < open_ and close < prev_low


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    parts = pd.concat([(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1)
    return parts.max(axis=1)


def atr14(df: pd.DataFrame) -> pd.Series:
    return true_range(df["High"], df["Low"], df["Close"]).rolling(14, min_periods=14).mean()


def swing_highs(df: pd.DataFrame) -> pd.Series:
    h = df["High"]
    return (h > h.shift(1)) & (h > h.shift(2)) & (h > h.shift(-1)) & (h > h.shift(-2))


def swing_lows(df: pd.DataFrame) -> pd.Series:
    l = df["Low"]
    return (l < l.shift(1)) & (l < l.shift(2)) & (l < l.shift(-1)) & (l < l.shift(-2))


def _nearest_level(
    df: pd.DataFrame,
    flags: pd.Series,
    t: int,
    lookback: int,
    column: str,
    predicate,
) -> float | None:
    start = max(0, t - lookback)
    for i in range(t - 1, start - 1, -1):
        if bool(flags.iloc[i]):
            level = float(df[column].iloc[i])
            if predicate(level):
                return level
    return None


def compute_swing_sl_tp_long(
    df: pd.DataFrame,
    t: int,
    entry_price: float,
    atr_value: float,
    sl_mult: float,
    tp_lookback: int,
    high_flags: pd.Series | None = None,
    low_flags: pd.Series | None = None,
) -> tuple[float, float]:
    high_flags = swing_highs(df) if high_flags is None else high_flags
    low_flags = swing_lows(df) if low_flags is None else low_flags
    atr = float(atr_value) if math.isfinite(float(atr_value)) and float(atr_value) > 0 else max(0.001, entry_price * 0.0005)
    sl = _nearest_level(df, low_flags, t, tp_lookback, "Low", lambda x: x < entry_price)
    tp = _nearest_level(df, high_flags, t, tp_lookback, "High", lambda x: x > entry_price)
    return (sl if sl is not None else entry_price - sl_mult * atr, tp if tp is not None else entry_price + 1.5 * atr)


def compute_swing_sl_tp_short(
    df: pd.DataFrame,
    t: int,
    entry_price: float,
    atr_value: float,
    sl_mult: float,
    tp_lookback: int,
    high_flags: pd.Series | None = None,
    low_flags: pd.Series | None = None,
) -> tuple[float, float]:
    high_flags = swing_highs(df) if high_flags is None else high_flags
    low_flags = swing_lows(df) if low_flags is None else low_flags
    atr = float(atr_value) if math.isfinite(float(atr_value)) and float(atr_value) > 0 else max(0.001, entry_price * 0.0005)
    sl = _nearest_level(df, high_flags, t, tp_lookback, "High", lambda x: x > entry_price)
    tp = _nearest_level(df, low_flags, t, tp_lookback, "Low", lambda x: x < entry_price)
    return (sl if sl is not None else entry_price + sl_mult * atr, tp if tp is not None else entry_price - 1.5 * atr)


def long_pattern(df: pd.DataFrame, t: int) -> str | None:
    row = df.iloc[t]
    prev = df.iloc[t - 1]
    if is_bull_pinbar(row.Open, row.High, row.Low, row.Close):
        return "L1_bull_pinbar"
    if is_bull_hammer_bear(row.Open, row.High, row.Low, row.Close):
        return "L2_bear_hammer"
    if is_bullish_engulfing(prev.Open, prev.Close, row.Open, row.Close):
        return "L3_bullish_engulfing"
    if is_bullish_harami_breakout(prev.Open, prev.Close, prev.High, prev.Low, row.Open, row.Close):
        return "L4_bullish_harami_breakout"
    return None


def short_pattern(df: pd.DataFrame, t: int) -> str | None:
    row = df.iloc[t]
    prev = df.iloc[t - 1]
    if is_bear_pinbar(row.Open, row.High, row.Low, row.Close):
        return "S1_bear_pinbar"
    if is_bear_hammer_bull(row.Open, row.High, row.Low, row.Close):
        return "S2_bull_hammer"
    if is_bearish_engulfing(prev.Open, prev.Close, row.Open, row.Close):
        return "S3_bearish_engulfing"
    if is_bearish_harami_breakout(prev.Open, prev.Close, prev.High, prev.Low, row.Open, row.Close):
        return "S4_bearish_harami_breakout"
    return None


def _pnl_pip(side: str, entry: float, exit_price: float, pip_size: float) -> float:
    raw = (exit_price - entry) / pip_size
    return raw if side == "long" else -raw


def close_position(
    position: Position,
    df: pd.DataFrame,
    exit_idx: int,
    exit_price: float,
    reason: str,
    pip_size: float,
) -> Trade:
    row = df.iloc[exit_idx]
    return Trade(
        side=position.side,
        pattern=position.pattern,
        signal_ts=position.signal_ts,
        entry_ts=position.entry_ts,
        exit_ts=df.index[exit_idx],
        entry_price=position.entry_price,
        exit_price=exit_price,
        sl=position.sl,
        tp=position.tp,
        pnl_pip=round(_pnl_pip(position.side, position.entry_price, exit_price, pip_size), 6),
        exit_reason=reason,
        entry_open=float(df["Open"].iloc[position.entry_idx]),
        exit_open=float(row.Open) if "Open" in df.columns else None,
        exit_high=float(row.High),
        exit_low=float(row.Low),
        exit_close=float(row.Close),
    )


def run_backtest(
    df_m15: pd.DataFrame,
    *,
    pair: str = "USD_JPY",
    sl_mult: float = 1.0,
    tp_lookback: int = 20,
    spread_pip: float = 1.5,
    slippage_pip: float = 0.5,
) -> tuple[list[Trade], dict]:
    df = normalize_ohlcv(df_m15)
    pip_size = PIP_SIZE_BY_PAIR[pair]
    cost = (spread_pip + slippage_pip) * pip_size
    ema10 = df["Close"].ewm(span=10, adjust=False).mean()
    atr = atr14(df)
    high_flags = swing_highs(df)
    low_flags = swing_lows(df)
    trend = 0
    position: Position | None = None
    trades: list[Trade] = []
    pattern_triggers = {k: 0 for k in ["L1", "L2", "L3", "L4", "S1", "S2", "S3", "S4"]}
    signal_counts = {"pullback_touch": 0, "long_confirmed": 0, "short_confirmed": 0, "trend_crosses": 0}

    for t in range(2, len(df)):
        prev_trend = trend
        close_t = float(df["Close"].iloc[t])
        close_prev = float(df["Close"].iloc[t - 1])
        if close_t > float(ema10.iloc[t]) and close_prev <= float(ema10.iloc[t - 1]):
            trend = 1
        elif close_t < float(ema10.iloc[t]) and close_prev >= float(ema10.iloc[t - 1]):
            trend = -1
        if trend != prev_trend and prev_trend != 0:
            signal_counts["trend_crosses"] += 1

        if position is not None and t + 1 < len(df):
            if (position.side == "long" and trend == -1) or (position.side == "short" and trend == 1):
                raw_exit = float(df["Open"].iloc[t + 1])
                exit_price = raw_exit - cost if position.side == "long" else raw_exit + cost
                trades.append(close_position(position, df, t + 1, exit_price, "trend_cross", pip_size))
                position = None

        if position is not None:
            high = float(df["High"].iloc[t])
            low = float(df["Low"].iloc[t])
            if position.side == "long":
                if low <= position.sl:
                    trades.append(close_position(position, df, t, position.sl - cost, "sl", pip_size))
                    position = None
                    continue
                if high >= position.tp:
                    trades.append(close_position(position, df, t, position.tp - cost, "tp", pip_size))
                    position = None
                    continue
            else:
                if high >= position.sl:
                    trades.append(close_position(position, df, t, position.sl + cost, "sl", pip_size))
                    position = None
                    continue
                if low <= position.tp:
                    trades.append(close_position(position, df, t, position.tp + cost, "tp", pip_size))
                    position = None
                    continue
            continue

        if t + 1 >= len(df):
            continue
        pullback_touch = float(df["Low"].iloc[t]) <= float(ema10.iloc[t]) <= float(df["High"].iloc[t])
        if not pullback_touch:
            continue
        signal_counts["pullback_touch"] += 1

        if trend == 1:
            pattern = long_pattern(df, t)
            if pattern is None:
                continue
            pattern_triggers[pattern[:2]] += 1
            signal_counts["long_confirmed"] += 1
            entry = float(df["Open"].iloc[t + 1]) + cost
            sl, tp = compute_swing_sl_tp_long(df, t, entry, float(atr.iloc[t]), sl_mult, tp_lookback, high_flags, low_flags)
            position = Position("long", df.index[t + 1], t + 1, df.index[t], entry, sl, tp, pattern)
        elif trend == -1:
            pattern = short_pattern(df, t)
            if pattern is None:
                continue
            pattern_triggers[pattern[:2]] += 1
            signal_counts["short_confirmed"] += 1
            entry = float(df["Open"].iloc[t + 1]) - cost
            sl, tp = compute_swing_sl_tp_short(df, t, entry, float(atr.iloc[t]), sl_mult, tp_lookback, high_flags, low_flags)
            position = Position("short", df.index[t + 1], t + 1, df.index[t], entry, sl, tp, pattern)

    if position is not None:
        last_idx = len(df) - 1
        raw_exit = float(df["Close"].iloc[last_idx])
        exit_price = raw_exit - cost if position.side == "long" else raw_exit + cost
        trades.append(close_position(position, df, last_idx, exit_price, "eod", pip_size))

    diagnostics = {"pattern_triggers": pattern_triggers, "signal_counts": signal_counts}
    return trades, diagnostics


def profit_factor(pnls: Iterable[float]) -> float:
    vals = list(pnls)
    gross_win = sum(v for v in vals if v > 0)
    gross_loss = abs(sum(v for v in vals if v < 0))
    if gross_loss == 0:
        return 99.0 if gross_win > 0 else 0.0
    return min(99.0, gross_win / gross_loss)


def max_drawdown(pnls: list[float]) -> float:
    equity = 0.0
    peak = 0.0
    dd = 0.0
    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
    return float(dd)


def annualized_trade_sharpe(pnls: list[float]) -> float:
    if len(pnls) < 2:
        return 0.0
    arr = np.array(pnls, dtype=float)
    sd = float(arr.std(ddof=1))
    if sd == 0:
        return 0.0
    return float(arr.mean() / sd * math.sqrt(252))


def yearly_breakdown(trades: list[Trade]) -> list[dict]:
    if not trades:
        return []
    df = pd.DataFrame({"year": [t.exit_ts.year for t in trades], "pnl": [t.pnl_pip for t in trades]})
    rows = []
    for year, group in df.groupby("year"):
        pnls = group["pnl"].astype(float).tolist()
        rows.append({"year": int(year), "n": int(len(pnls)), "pf": float(profit_factor(pnls)), "ev_pip": float(np.mean(pnls))})
    return rows


def profit_year_concentration(trades: list[Trade]) -> float:
    if not trades:
        return 0.0
    df = pd.DataFrame({"year": [t.exit_ts.year for t in trades], "pnl": [t.pnl_pip for t in trades]})
    yearly = df.groupby("year")["pnl"].sum()
    positive = yearly[yearly > 0]
    total = float(positive.sum())
    if total <= 0:
        return 1.0
    return float(positive.max() / total)


def summarize_metrics(trades: list[Trade], pair: str = "USD_JPY") -> dict:
    pnls = [float(t.pnl_pip) for t in trades]
    n = len(pnls)
    wins = sum(1 for p in pnls if p > 0)
    wr = wins / n if n else 0.0
    wins_p = [p for p in pnls if p > 0]
    losses_p = [-p for p in pnls if p < 0]
    avg_win = float(np.mean(wins_p)) if wins_p else 0.0
    avg_loss = float(np.mean(losses_p)) if losses_p else 0.0
    wilson = binomtest(wins, n).proportion_ci(0.95).low if n else 0.0
    max_dd_pip = max_drawdown(pnls)
    pip_value_jpy = UNIT_NOTIONAL * PIP_SIZE_BY_PAIR[pair]
    max_dd_pct = (max_dd_pip * pip_value_jpy) / (UNIT_NOTIONAL * 100.0)
    return {
        "n": int(n),
        "wr": float(wr),
        "wilson_lo_95": float(wilson),
        "pf": float(profit_factor(pnls)),
        "ev_pip_per_trade": float(np.mean(pnls)) if pnls else 0.0,
        "avg_rr": float(avg_win / avg_loss) if avg_loss > 0 else (99.0 if avg_win > 0 else 0.0),
        "max_dd_pip": float(max_dd_pip),
        "max_dd_pct": float(max_dd_pct),
        "sharpe": annualized_trade_sharpe(pnls),
        "profit_year_concentration": profit_year_concentration(trades),
    }


def data_quality(df_m15_full: pd.DataFrame, df_m15_filtered: pd.DataFrame) -> dict:
    if df_m15_full.empty:
        expected = actual = 0
    else:
        grid = pd.date_range(df_m15_full.index.min(), df_m15_full.index.max(), freq="15min", tz="UTC")
        mask = ~(
            ((grid.dayofweek == 4) & (grid.hour >= FORBIDDEN_WEEKDAY_START_HOUR))
            | (grid.dayofweek == 5)
            | ((grid.dayofweek == 6) & (grid.hour < FORBIDDEN_WEEKDAY_START_HOUR))
        )
        expected = int(mask.sum())
        actual = int(len(df_m15_filtered))
    missing_pct = float(max(0, expected - actual) / expected) if expected else 0.0
    return {
        "expected_bars": expected,
        "actual_bars": actual,
        "missing_pct": missing_pct,
        "weekend_filtered": True,
        "resample_method": RESAMPLE_METHOD,
    }


def gate(metrics: dict, dq: dict) -> tuple[str, list[str]]:
    reasons = []
    if metrics["pf"] < 1.10:
        reasons.append("PF < 1.10")
    if metrics["wilson_lo_95"] < 0.50:
        reasons.append("Wilson_lo_95 < 0.50")
    if metrics["n"] < 150:
        reasons.append("N < 150")
    if metrics["profit_year_concentration"] >= 0.55:
        reasons.append("profit_year_concentration >= 0.55")
    if metrics["ev_pip_per_trade"] <= 0:
        reasons.append("EV_pip_per_trade <= 0")
    if dq["missing_pct"] > 0.02:
        reasons.append("data_quality.missing_pct > 0.02")
    return ("FAIL" if reasons else "PASS", reasons)


def equity_ascii(pnls: list[float], width: int = 72, height: int = 12) -> str:
    if not pnls:
        return "(no trades)"
    equity = np.cumsum(np.array(pnls, dtype=float))
    if len(equity) > width:
        idx = np.linspace(0, len(equity) - 1, width).astype(int)
        series = equity[idx]
    else:
        series = equity
    mn = float(series.min())
    mx = float(series.max())
    if mx == mn:
        return "\n".join(["*" * len(series)])
    rows = []
    for r in range(height):
        threshold = mx - (mx - mn) * r / (height - 1)
        line = "".join("*" if v >= threshold else " " for v in series)
        rows.append(line.rstrip())
    return "\n".join(rows)


def build_result(
    trades: list[Trade],
    diagnostics: dict,
    dq: dict,
    *,
    pair: str,
    pattern_set: str,
    sl_mult: float,
    tp_lookback: int,
    spread_pip: float,
    slippage_pip: float,
) -> dict:
    metrics = summarize_metrics(trades, pair)
    decision, fail_reasons = gate(metrics, dq)
    return {
        "primary_cell": {
            "pair": pair,
            "pattern_set": pattern_set,
            "sl_multiplier": float(sl_mult),
            "tp_lookback": int(tp_lookback),
            "spread_pip": float(spread_pip),
            "slippage_pip": float(slippage_pip),
        },
        "metrics": metrics,
        "yearly_breakdown": yearly_breakdown(trades),
        "data_quality": dq,
        "gate_decision": decision,
        "fail_reasons": fail_reasons,
        "_diagnostics": diagnostics,
        "_trades": [asdict(t) for t in trades],
    }


def _fmt_float(v: float, digits: int = 4) -> str:
    if math.isinf(float(v)):
        return "inf"
    return f"{float(v):.{digits}f}"


def git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return "UNKNOWN"


def write_markdown_report(path: Path, result: dict, command: str, source_path: Path, open_questions: list[str]) -> None:
    metrics = result["metrics"]
    dq = result["data_quality"]
    diag = result["_diagnostics"]
    trades = result["_trades"]
    pnls = [float(t["pnl_pip"]) for t in trades]
    gate_rows = [
        ("PF >= 1.10", metrics["pf"] >= 1.10, _fmt_float(metrics["pf"])),
        ("Wilson_lo_95 >= 0.50", metrics["wilson_lo_95"] >= 0.50, _fmt_float(metrics["wilson_lo_95"])),
        ("N >= 150", metrics["n"] >= 150, str(metrics["n"])),
        (
            "profit_year_concentration < 0.55",
            metrics["profit_year_concentration"] < 0.55,
            _fmt_float(metrics["profit_year_concentration"]),
        ),
        ("EV_pip_per_trade > 0", metrics["ev_pip_per_trade"] > 0, _fmt_float(metrics["ev_pip_per_trade"])),
        ("data missing_pct <= 2%", dq["missing_pct"] <= 0.02, _fmt_float(dq["missing_pct"])),
    ]
    exit_counts = {}
    for t in trades:
        exit_counts[t["exit_reason"]] = exit_counts.get(t["exit_reason"], 0) + 1
    n = len(trades) or 1
    lines = [
        "# EMA10 x M15 x 4-Pattern Pullback Stage 0 (2026-05-05)",
        "",
        "## Verdict",
        "",
        f"**Verdict**: {result['gate_decision']}",
        "",
        "| Gate | Pass | Observed |",
        "|---|---:|---:|",
    ]
    for name, ok, observed in gate_rows:
        lines.append(f"| {name} | {'PASS' if ok else 'FAIL'} | {observed} |")
    if result["fail_reasons"]:
        lines += ["", f"Fail reasons: {', '.join(result['fail_reasons'])}"]
    lines += [
        "",
        "## Primary Cell Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    for key in [
        "n",
        "wr",
        "wilson_lo_95",
        "pf",
        "ev_pip_per_trade",
        "avg_rr",
        "max_dd_pip",
        "max_dd_pct",
        "sharpe",
        "profit_year_concentration",
    ]:
        value = metrics[key]
        lines.append(f"| {key} | {value if isinstance(value, int) else _fmt_float(value, 6)} |")
    lines += [
        "",
        "## Yearly Breakdown",
        "",
        "| Year | N | PF | EV pip |",
        "|---:|---:|---:|---:|",
    ]
    for row in result["yearly_breakdown"]:
        lines.append(f"| {row['year']} | {row['n']} | {_fmt_float(row['pf'], 4)} | {_fmt_float(row['ev_pip'], 4)} |")
    lines += [
        "",
        "## Data Quality",
        "",
        f"- Source: `{source_path}`",
        f"- Expected M15 bars after weekend filter: {dq['expected_bars']}",
        f"- Actual M15 bars after weekend filter: {dq['actual_bars']}",
        f"- Missing pct: {_fmt_float(dq['missing_pct'], 6)}",
        f"- Weekend filter applied: {dq['weekend_filtered']}",
        f"- Resample method: `{dq['resample_method']}`",
        "",
        "## Equity Curve",
        "",
        "```text",
        equity_ascii(pnls),
        "```",
        "",
        "## Sample Trade Ledger",
        "",
        "| Slice | Side | Pattern | Signal UTC | Entry UTC | Exit UTC | Entry | Exit | SL | TP | PnL pip | Reason | OHLC exit |",
        "|---|---|---|---|---|---|---:|---:|---:|---:|---:|---|---|",
    ]
    sample = [(("first" if i < 5 else "last"), t) for i, t in enumerate(trades[:5] + trades[-5:])]
    for label, t in sample:
        lines.append(
            f"| {label} | {t['side']} | {t['pattern']} | {t['signal_ts']} | {t['entry_ts']} | {t['exit_ts']} | "
            f"{_fmt_float(t['entry_price'], 3)} | {_fmt_float(t['exit_price'], 3)} | {_fmt_float(t['sl'], 3)} | "
            f"{_fmt_float(t['tp'], 3)} | {_fmt_float(t['pnl_pip'], 2)} | {t['exit_reason']} | "
            f"O={_fmt_float(t['exit_open'], 3)} H={_fmt_float(t['exit_high'], 3)} L={_fmt_float(t['exit_low'], 3)} C={_fmt_float(t['exit_close'], 3)} |"
        )
    lines += [
        "",
        "## Sanity Checks",
        "",
        "### Pattern Trigger Breakdown",
        "",
        "| Pattern | Count |",
        "|---|---:|",
    ]
    for key, value in diag["pattern_triggers"].items():
        lines.append(f"| {key} | {value} |")
    lines += [
        "",
        "### Exit Breakdown",
        "",
        "| Exit reason | Count | Ratio |",
        "|---|---:|---:|",
    ]
    for key in sorted(exit_counts):
        lines.append(f"| {key} | {exit_counts[key]} | {_fmt_float(exit_counts[key] / n, 4)} |")
    lines += [
        "",
        f"- Trend cross forced close ratio: {_fmt_float(exit_counts.get('trend_cross', 0) / n, 4)}",
        f"- Pullback touch count: {diag['signal_counts']['pullback_touch']}",
        f"- Long confirmed count: {diag['signal_counts']['long_confirmed']}",
        f"- Short confirmed count: {diag['signal_counts']['short_confirmed']}",
        "",
        "## Reproducibility",
        "",
        "```bash",
        command,
        "```",
        "",
        f"- Git SHA: `{git_sha()}`",
    ]
    if open_questions:
        lines += ["", "## Open Questions", ""]
        lines.extend(f"- {q}" for q in open_questions)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def json_public(result: dict) -> dict:
    return {k: v for k, v in result.items() if not k.startswith("_")}


def _json_default(obj):
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    return str(obj)


def load_cache(path: Path) -> tuple[pd.DataFrame, Path, list[str]]:
    open_questions: list[str] = []
    source = path
    if not source.exists():
        if path == DEFAULT_CACHE and FALLBACK_CACHE.exists():
            source = FALLBACK_CACHE
            open_questions.append(f"Pre-reg named cache `{DEFAULT_CACHE}` was absent; used matching real cache `{FALLBACK_CACHE}`.")
        else:
            raise FileNotFoundError(path)
    return pd.read_parquet(source), source, open_questions


def run_cli(args: argparse.Namespace) -> int:
    if args.stage != 0:
        raise ValueError("Only --stage 0 is implemented for this pre-registered task.")
    raw, source_path, open_questions = load_cache(Path(args.cache))
    df_m5 = normalize_ohlcv(raw)
    start = pd.Timestamp(args.start, tz="UTC")
    end = pd.Timestamp(args.end, tz="UTC") + pd.Timedelta(days=1) - pd.Timedelta(minutes=5)
    df_m5 = df_m5[(df_m5.index >= start) & (df_m5.index <= end)]
    df_m15_full = resample_m5_to_m15(df_m5)
    df_m15 = filter_weekend_bars(df_m15_full)
    trades, diagnostics = run_backtest(
        df_m15,
        pair=args.pair,
        sl_mult=args.sl_mult,
        tp_lookback=args.tp_lookback,
        spread_pip=args.spread_pip,
        slippage_pip=args.slippage_pip,
    )
    dq = data_quality(df_m15_full, df_m15)
    result = build_result(
        trades,
        diagnostics,
        dq,
        pair=args.pair,
        pattern_set=args.pattern_set,
        sl_mult=args.sl_mult,
        tp_lookback=args.tp_lookback,
        spread_pip=args.spread_pip,
        slippage_pip=args.slippage_pip,
    )
    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(json_public(result), indent=2, ensure_ascii=False, default=_json_default) + "\n", encoding="utf-8")
    command = "python " + " ".join(sys.argv)
    write_markdown_report(Path(args.output_md), result, command, source_path, open_questions)
    print(f"{result['gate_decision']} n={result['metrics']['n']} pf={result['metrics']['pf']:.4f} ev={result['metrics']['ev_pip_per_trade']:.4f}")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=int, required=True)
    parser.add_argument("--pair", default="USD_JPY")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--pattern-set", default="all_four")
    parser.add_argument("--sl-mult", type=float, default=1.0)
    parser.add_argument("--tp-lookback", type=int, default=20)
    parser.add_argument("--spread-pip", type=float, default=1.5)
    parser.add_argument("--slippage-pip", type=float, default=0.5)
    parser.add_argument("--cache", default=str(DEFAULT_CACHE))
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-json", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return run_cli(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
