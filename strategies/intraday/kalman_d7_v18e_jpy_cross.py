"""Kalman D7 v18e JPY cross shadow-tier signal generator.

Pre-registration LOCK (commit message must include rule:R1):
  - Pair: AUD_JPY, EUR_JPY (M15)
  - Window: 365d BT; Codex-reviewed Python port confirmed marginal positive
    PF 1.10 / 1.08 with N=109 / 119.
  - Shadow tier only until N>=30 (~3-6 months expected).
  - Promote only if Wilson 95% WR lower >= 0.50, PF >= 1.10, BH-FDR survivor
    (m=2, q=0.10), Max DD <= 5%, Sharpe > 0.
  - Retreat if Wilson 95% WR upper < 0.50, PF < 0.95 at N>=30, or 3 months
    net negative.

The entry port mirrors tools.kalman_d7_v18e_python_port without importing it,
so production strategy code does not depend on BT tooling.  Exit parameters
are encoded into the shadow trade record; no live order routing is enabled.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from strategies.base import Candidate, StrategyBase
from strategies.context import SignalContext


JPY_MINTICK = 0.001


@dataclass(frozen=True)
class KalmanD7V18eConfig:
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
    mintick: float = JPY_MINTICK


def _pair_env_enabled(instrument: str) -> bool:
    pair = _normalize_pair(instrument)
    if pair == "AUD_JPY":
        return os.environ.get("KALMAN_D7_V18E_AUDJPY_SHADOW") == "1"
    if pair == "EUR_JPY":
        return os.environ.get("KALMAN_D7_V18E_EURJPY_SHADOW") == "1"
    return False


def _normalize_pair(symbol: str) -> str:
    cleaned = (symbol or "").upper().replace("=X", "").replace("/", "_")
    if "_" in cleaned:
        parts = cleaned.split("_")
        if len(parts) >= 2:
            return f"{parts[0]}_{parts[1]}"
    compact = cleaned.replace("_", "")
    if len(compact) == 6:
        return f"{compact[:3]}_{compact[3:]}"
    return cleaned


def _normal_ohlc(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    if df is None or len(df) < 205:
        return None
    out = df.copy()
    rename = {}
    for col in out.columns:
        low = str(col).lower()
        if low in {"open", "high", "low", "close", "volume"}:
            rename[col] = low.capitalize()
    out = out.rename(columns=rename)
    required = ["Open", "High", "Low", "Close"]
    if any(col not in out.columns for col in required):
        return None
    if isinstance(out.index, pd.DatetimeIndex):
        if out.index.tz is None:
            out.index = out.index.tz_localize("UTC")
        else:
            out.index = out.index.tz_convert("UTC")
    return out[required].dropna(subset=required)


def _rma(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()


def add_kalman_d7_v18e_indicators(
    df: pd.DataFrame,
    config: KalmanD7V18eConfig = KalmanD7V18eConfig(),
) -> pd.DataFrame:
    """Return OHLC plus canonical v18e entry-gate columns."""
    out = _normal_ohlc(df)
    if out is None:
        return pd.DataFrame()

    close = out["Close"]
    high = out["High"]
    low = out["Low"]
    out["ema25"] = close.ewm(span=config.ema_fast, adjust=False, min_periods=config.ema_fast).mean()
    out["ema75"] = close.ewm(span=config.ema_mid, adjust=False, min_periods=config.ema_mid).mean()
    out["ema200"] = close.ewm(span=config.ema_slow, adjust=False, min_periods=config.ema_slow).mean()

    tr = pd.concat(
        [high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()],
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

    window = config.atr_quantile_window
    out["atr_p20"] = out["atr"].rolling(window, min_periods=window).quantile(0.20)
    out["atr_p80"] = out["atr"].rolling(window, min_periods=window).quantile(0.80)
    out["perfect_up"] = (
        (out["ema25"] > out["ema75"])
        & (out["ema75"] > out["ema200"])
        & (out["Close"] > out["ema25"])
    )
    out["po_up_start"] = out["perfect_up"] & ~out["perfect_up"].shift(1).fillna(False).astype(bool)
    out["dist_atr"] = (out["Close"] - out["ema200"]) / out["atr"]
    out["gap_atr"] = (out["ema25"] - out["ema200"]) / out["atr"]
    hour = out.index.hour if isinstance(out.index, pd.DatetimeIndex) else pd.Index([12] * len(out))
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


def _round_to_mintick(value: float, mintick: float = JPY_MINTICK) -> float:
    return round(value / mintick) * mintick


class KalmanD7V18eJpyCross(StrategyBase):
    """AUDJPY/EURJPY M15 long-only Kalman D7 v18e shadow candidate."""

    name = "kalman_d7_v18e"
    mode = "daytrade"
    enabled = True
    strategy_type = "trend"
    _enabled_pairs = frozenset({"AUD_JPY", "EUR_JPY"})

    def __init__(self, config: KalmanD7V18eConfig | None = None):
        self.config = config or KalmanD7V18eConfig()

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        pair = _normalize_pair(ctx.symbol)
        if pair not in self._enabled_pairs:
            return None
        if not _pair_env_enabled(pair):
            return None
        if ctx.tf not in ("15m", "M15"):
            return None

        data = add_kalman_d7_v18e_indicators(ctx.df, self.config)
        if data.empty or len(data) < self.config.atr_quantile_window + 5:
            return None
        row = data.iloc[-1]
        if not bool(row.get("entry_signal", False)):
            return None

        atr = float(row["atr"])
        if not np.isfinite(atr) or atr <= 0:
            return None
        entry = float(ctx.entry or row["Close"])
        sl = _round_to_mintick(entry - self.config.stop_atr * atr, self.config.mintick)
        trail_activation = _round_to_mintick(
            entry + self.config.trail_points_atr * atr,
            self.config.mintick,
        )
        trail_offset = _round_to_mintick(self.config.trail_offset_atr * atr, self.config.mintick)
        score = 4.0
        if bool(ctx.ema200_bull or row["Close"] > row["ema200"]):
            score += 0.3
        if float(ctx.adx or 0.0) >= 25.0:
            score += 0.3
        if float(ctx.macdh or 0.0) > 0.0 and float(ctx.macdh or 0.0) > float(ctx.macdh_prev or 0.0):
            score += 0.2

        reasons = [
            f"Kalman D7 v18e shadow-only {pair} M15",
            "PO-UP start + DIST/GAP/ATR-Q/RSI/session gates passed",
            f"DIST={float(row['dist_atr']):.2f} ATR, GAP={float(row['gap_atr']):.2f} ATR",
            f"ATR Q [{float(row['atr_p20']):.3f}, {float(row['atr_p80']):.3f}), RSI={float(row['rsi']):.1f}",
            f"dynamic SL entry-2.0ATR={sl:.3f}; trail activates at +1.0ATR={trail_activation:.3f}",
            f"trail offset 0.5ATR={trail_offset:.3f}; Pine process_orders_on_close port uses next-open entry/exit BT semantics",
        ]

        return Candidate(
            signal="BUY",
            confidence=int(min(85, 55 + score * 5)),
            sl=float(sl),
            tp=float(trail_activation),
            reasons=reasons,
            entry_type=self.name,
            score=float(score),
            max_hold_bars=240,
        )

