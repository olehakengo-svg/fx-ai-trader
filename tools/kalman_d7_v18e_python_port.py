#!/usr/bin/env python3
"""Python port of Kalman D7 v18e 0.5 ATR trail.

The port mirrors the Pine rules supplied in the 2026-06-07 cross-pair BT
request.  It is intentionally standalone and does not import live strategy
modules, so it cannot mutate or depend on USDJPY LIVE wiring.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import NormalDist
from typing import Any

import numpy as np
import pandas as pd


INITIAL_EQUITY = 100_000.0
QTY_PCT = 0.10
COMMISSION_RATE = 0.00002  # 0.002%
JPY_MINTICK = 0.001


@dataclass(frozen=True)
class V18EConfig:
    ema_fast: int = 25
    ema_mid: int = 75
    ema_slow: int = 200
    atr_len: int = 14
    rsi_len: int = 14
    atr_quantile_window: int = 200
    dist_atr_max: float = 3.0
    gap_atr_max: float = 3.0
    rsi_max: float = 70.0
    stop_atr: float = 2.0
    trail_points_atr: float = 1.0
    trail_offset_atr: float = 0.5
    qty_pct: float = QTY_PCT
    commission_rate: float = COMMISSION_RATE
    mintick: float = JPY_MINTICK
    initial_equity: float = INITIAL_EQUITY


@dataclass(frozen=True)
class Trade:
    pair: str
    entry_time: str
    exit_time: str
    signal_time: str
    entry: float
    exit: float
    qty: float
    pnl: float
    gross_pnl: float
    commission: float
    bars_held: int
    exit_reason: str
    atr_entry: float
    dist_atr: float
    gap_atr: float
    rsi: float


def normalize_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    """Return UTC-indexed Open/High/Low/Close/Volume columns."""
    out = df.copy()
    rename = {}
    for col in out.columns:
        low = str(col).lower()
        if low in {"open", "high", "low", "close", "volume"}:
            rename[col] = low.capitalize()
    out = out.rename(columns=rename)
    required = ["Open", "High", "Low", "Close"]
    missing = [c for c in required if c not in out.columns]
    if missing:
        raise ValueError(f"missing OHLC columns: {missing}")
    if not isinstance(out.index, pd.DatetimeIndex):
        out.index = pd.to_datetime(out.index, utc=True)
    elif out.index.tz is None:
        out.index = out.index.tz_localize("UTC")
    else:
        out.index = out.index.tz_convert("UTC")
    out = out.sort_index()
    return out[required + ([c for c in ["Volume"] if c in out.columns])].dropna(subset=required)


def resample_5m_to_15m(df: pd.DataFrame) -> pd.DataFrame:
    """Convert MASSIVE 5m OHLCV to right-open 15m candles."""
    src = normalize_ohlc(df)
    agg: dict[str, str] = {
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
    }
    if "Volume" in src.columns:
        agg["Volume"] = "sum"
    out = src.resample("15min", label="left", closed="left").agg(agg)
    return out.dropna(subset=["Open", "High", "Low", "Close"])


def load_ohlc(path: Path, *, resample_from_5m: bool = False) -> pd.DataFrame:
    df = pd.read_parquet(path)
    if resample_from_5m:
        return resample_5m_to_15m(df)
    return normalize_ohlc(df)


def _rma(series: pd.Series, length: int) -> pd.Series:
    # TradingView ta.atr uses Wilder RMA.  With no Pine dump available, ewm
    # alpha=1/length adjust=False is the closest deterministic port.
    return series.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()


def add_v18e_indicators(df: pd.DataFrame, config: V18EConfig = V18EConfig()) -> pd.DataFrame:
    out = normalize_ohlc(df)
    close = out["Close"]
    high = out["High"]
    low = out["Low"]

    out["ema25"] = close.ewm(span=config.ema_fast, adjust=False, min_periods=config.ema_fast).mean()
    out["ema75"] = close.ewm(span=config.ema_mid, adjust=False, min_periods=config.ema_mid).mean()
    out["ema200"] = close.ewm(span=config.ema_slow, adjust=False, min_periods=config.ema_slow).mean()

    tr = pd.concat(
        [
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    out["atr"] = _rma(tr, config.atr_len)

    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = _rma(gain, config.rsi_len)
    avg_loss = _rma(loss, config.rsi_len)
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out["rsi"] = 100.0 - (100.0 / (1.0 + rs))
    out.loc[(avg_loss == 0.0) & (avg_gain > 0.0), "rsi"] = 100.0
    out.loc[(avg_loss == 0.0) & (avg_gain == 0.0), "rsi"] = 50.0

    out["atr_p20"] = out["atr"].rolling(config.atr_quantile_window, min_periods=config.atr_quantile_window).quantile(0.20)
    out["atr_p80"] = out["atr"].rolling(config.atr_quantile_window, min_periods=config.atr_quantile_window).quantile(0.80)
    out["perfect_up"] = (
        (out["ema25"] > out["ema75"])
        & (out["ema75"] > out["ema200"])
        & (out["Close"] > out["ema25"])
    )
    out["po_up_start"] = out["perfect_up"] & ~out["perfect_up"].shift(1).fillna(False).astype(bool)
    out["dist_atr"] = (out["Close"] - out["ema200"]) / out["atr"]
    out["gap_atr"] = (out["ema25"] - out["ema200"]) / out["atr"]
    hour = out.index.hour
    out["session_ok"] = (hour < 7) | ((hour >= 7) & (hour < 12)) | ((hour >= 16) & (hour < 21))
    out["entry_signal"] = (
        out["po_up_start"]
        & (out["dist_atr"] < config.dist_atr_max)
        & (out["gap_atr"] < config.gap_atr_max)
        & (out["atr"] >= out["atr_p20"])
        & (out["atr"] < out["atr_p80"])
        & (out["rsi"] < config.rsi_max)
        & out["session_ok"]
    )
    return out


def _round_to_mintick(value: float, mintick: float) -> float:
    return round(value / mintick) * mintick


def run_v18e_backtest(
    pair: str,
    df: pd.DataFrame,
    *,
    config: V18EConfig = V18EConfig(),
    start: str | pd.Timestamp | None = None,
    end: str | pd.Timestamp | None = None,
) -> dict[str, Any]:
    data = add_v18e_indicators(df, config)
    if start is not None:
        data = data.loc[data.index >= pd.Timestamp(start, tz="UTC" if pd.Timestamp(start).tz is None else None)]
    if end is not None:
        data = data.loc[data.index <= pd.Timestamp(end, tz="UTC" if pd.Timestamp(end).tz is None else None)]
    data = data.copy()
    if len(data) < config.atr_quantile_window + 5:
        return empty_result(pair, data, config)

    equity = float(config.initial_equity)
    peak_equity = equity
    max_dd = 0.0
    trades: list[Trade] = []
    equity_points: list[tuple[pd.Timestamp, float]] = []
    daily_pnl: dict[str, float] = {}
    i = 0
    n = len(data)
    while i < n - 2:
        row = data.iloc[i]
        if not bool(row.get("entry_signal", False)):
            i += 1
            continue

        entry_i = i + 1
        entry_bar = data.iloc[entry_i]
        signal_time = data.index[i]
        entry_time = data.index[entry_i]
        atr = float(row["atr"])
        if not math.isfinite(atr) or atr <= 0:
            i += 1
            continue

        raw_entry = float(entry_bar["Open"])
        entry = raw_entry + config.mintick
        qty = (equity * config.qty_pct) / entry
        entry_commission = qty * entry * config.commission_rate
        initial_stop = entry - config.stop_atr * atr
        trail_trigger = entry + _round_to_mintick(config.trail_points_atr * atr, config.mintick)
        trail_offset = _round_to_mintick(config.trail_offset_atr * atr, config.mintick)
        active_trail = False
        highest = float(entry_bar["High"])
        trail_stop = initial_stop
        exit_price: float | None = None
        exit_reason = ""
        exit_i = entry_i

        for j in range(entry_i, n):
            bar = data.iloc[j]
            high = float(bar["High"])
            low = float(bar["Low"])
            highest = max(highest, high)

            stop_to_check = max(initial_stop, trail_stop if active_trail else initial_stop)
            if low <= stop_to_check:
                exit_price = stop_to_check - config.mintick
                exit_reason = "stop" if not active_trail else "trail"
                exit_i = j
                break

            if high >= trail_trigger:
                active_trail = True
                trail_stop = max(trail_stop, highest - trail_offset)
                if low <= trail_stop:
                    exit_price = trail_stop - config.mintick
                    exit_reason = "trail"
                    exit_i = j
                    break

        if exit_price is None:
            exit_i = n - 1
            exit_price = float(data.iloc[exit_i]["Close"]) - config.mintick
            exit_reason = "eod"

        exit_time = data.index[exit_i]
        gross_pnl = qty * (exit_price - entry)
        exit_commission = qty * exit_price * config.commission_rate
        commission = entry_commission + exit_commission
        pnl = gross_pnl - commission
        equity += pnl
        peak_equity = max(peak_equity, equity)
        max_dd = max(max_dd, (peak_equity - equity) / peak_equity if peak_equity > 0 else 0.0)
        day_key = exit_time.date().isoformat()
        daily_pnl[day_key] = daily_pnl.get(day_key, 0.0) + pnl
        equity_points.append((exit_time, equity))
        trades.append(
            Trade(
                pair=pair,
                entry_time=entry_time.isoformat(),
                exit_time=exit_time.isoformat(),
                signal_time=signal_time.isoformat(),
                entry=entry,
                exit=exit_price,
                qty=qty,
                pnl=pnl,
                gross_pnl=gross_pnl,
                commission=commission,
                bars_held=int(exit_i - entry_i + 1),
                exit_reason=exit_reason,
                atr_entry=atr,
                dist_atr=float(row["dist_atr"]),
                gap_atr=float(row["gap_atr"]),
                rsi=float(row["rsi"]),
            )
        )
        i = exit_i + 1

    return summarize_backtest(pair, data, trades, equity, max_dd, daily_pnl, equity_points, config)


def empty_result(pair: str, data: pd.DataFrame, config: V18EConfig) -> dict[str, Any]:
    return summarize_backtest(pair, data, [], config.initial_equity, 0.0, {}, [], config)


def wilson_lower_bound(wins: int, n: int, confidence: float = 0.95) -> float:
    if n <= 0:
        return 0.0
    z = NormalDist().inv_cdf(1 - (1 - confidence) / 2)
    phat = wins / n
    denom = 1 + z * z / n
    center = phat + z * z / (2 * n)
    margin = z * math.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n)
    return (center - margin) / denom


def log_pf_pvalue(pnls: list[float]) -> dict[str, float | None]:
    wins = np.array([x for x in pnls if x > 0], dtype=float)
    losses = np.array([-x for x in pnls if x < 0], dtype=float)
    if len(wins) == 0 or len(losses) == 0:
        return {"log_pf": None, "log_pf_se": None, "z": None, "p_one_sided": None}
    gross_win = float(wins.sum())
    gross_loss = float(losses.sum())
    if gross_win <= 0 or gross_loss <= 0:
        return {"log_pf": None, "log_pf_se": None, "z": None, "p_one_sided": None}
    log_pf = math.log(gross_win / gross_loss)
    win_mean = float(wins.mean())
    loss_mean = float(losses.mean())
    win_var = float(wins.var(ddof=1)) if len(wins) > 1 else win_mean * win_mean
    loss_var = float(losses.var(ddof=1)) if len(losses) > 1 else loss_mean * loss_mean
    se2 = win_var / (len(wins) * win_mean * win_mean) + loss_var / (len(losses) * loss_mean * loss_mean)
    se = math.sqrt(max(se2, 1e-12))
    z = log_pf / se
    p = 1 - NormalDist().cdf(z)
    return {"log_pf": log_pf, "log_pf_se": se, "z": z, "p_one_sided": p}


def summarize_backtest(
    pair: str,
    data: pd.DataFrame,
    trades: list[Trade],
    equity: float,
    max_dd: float,
    daily_pnl: dict[str, float],
    equity_points: list[tuple[pd.Timestamp, float]],
    config: V18EConfig,
) -> dict[str, Any]:
    pnls = [t.pnl for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    gross_profit = float(sum(wins))
    gross_loss = float(-sum(losses))
    n = len(pnls)
    win_count = len(wins)
    pf = gross_profit / gross_loss if gross_loss > 0 else (math.inf if gross_profit > 0 else 0.0)
    daily = pd.Series(daily_pnl, dtype=float).sort_index()
    sharpe = 0.0
    if len(daily) > 1 and float(daily.std(ddof=1)) > 0:
        sharpe = float(daily.mean() / daily.std(ddof=1) * math.sqrt(252))
    summary = {
        "pair": pair,
        "bars": int(len(data)),
        "start": data.index[0].isoformat() if len(data) else None,
        "end": data.index[-1].isoformat() if len(data) else None,
        "years": float((data.index[-1] - data.index[0]).days / 365.25) if len(data) > 1 else 0.0,
        "signals": int(data["entry_signal"].sum()) if "entry_signal" in data.columns else 0,
        "n": n,
        "wins": win_count,
        "losses": len(losses),
        "wr": win_count / n if n else 0.0,
        "wilson95_wr_lower": wilson_lower_bound(win_count, n),
        "pf": pf,
        "net": float(sum(pnls)),
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "max_dd_pct": float(max_dd * 100.0),
        "sharpe_daily": sharpe,
        "avg_win": float(np.mean(wins)) if wins else 0.0,
        "avg_loss": float(np.mean(losses)) if losses else 0.0,
        "avg_bars_in_trade": float(np.mean([t.bars_held for t in trades])) if trades else 0.0,
        "ending_equity": float(equity),
        "pvalue": log_pf_pvalue(pnls),
    }
    return {
        "summary": summary,
        "trades": [asdict(t) for t in trades],
        "daily_pnl": daily_pnl,
        "equity_points": [(ts.isoformat(), eq) for ts, eq in equity_points],
        "config": asdict(config),
    }

