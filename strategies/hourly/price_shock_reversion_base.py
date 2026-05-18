"""
Price-Shock Reversion family — Tier 1 common base.

Reference: Qiita "予測を捨て、分布を読め" (tikeda123/f3bead031159ee8ca1bf)
           + Price-Shock Reversion Grid BT (commit 63c7cf18)

Entry: when a closed H1 bar's log_return is at or below the 252-bar rolling
1%-tile of previous returns. Direction is LONG. Exit is horizon bars later or
the catastrophic -2 x ATR-proxy stop, whichever comes first.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Optional

import numpy as np
import pandas as pd

from strategies.base import Candidate, StrategyBase
from strategies.context import SignalContext


VolBucket = Literal["Q1", "Q2", "Q3", "Q4", "Q5", "ALL"]


@dataclass(frozen=True)
class PriceShockRevConfig:
    name: str
    pair: str
    percentile: float
    horizon_bars: int
    vol_q: VolBucket
    rolling_window: int = 252
    vol20_window: int = 20
    sl_atr_mult: float = 2.0


class PriceShockReversionBase(StrategyBase):
    """Shared logic for the pre-registered Tier 1 Price-Shock Reversion family."""

    cfg: PriceShockRevConfig
    mode = "hourly"
    enabled = True
    strategy_type = "MR"

    @property
    def name(self) -> str:
        return self.cfg.name

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if not self._pair_matches(getattr(ctx, "symbol", ""), self.cfg.pair):
            return None
        df = getattr(ctx, "df", None)
        if df is None or not self._has_enough_history(df):
            return None
        return self.evaluate_from_dataframe(df)

    def evaluate_from_dataframe(self, df: pd.DataFrame) -> Optional[Candidate]:
        if not self._has_enough_history(df):
            return None

        computed = self.add_precomputed_columns(df)
        row = computed.iloc[-1]
        if pd.isna(row["log_return"]) or pd.isna(row["lower_0p01"]):
            return None
        if float(row["log_return"]) > float(row["lower_0p01"]):
            return None
        if self.cfg.vol_q != "ALL" and row["vol_quintile_calc"] != self.cfg.vol_q:
            return None

        current_price = float(row["Close"])
        vol20 = float(row["vol20"])
        if not math.isfinite(current_price) or not math.isfinite(vol20) or current_price <= 0 or vol20 <= 0:
            return None

        atr_proxy = vol20 * current_price * math.sqrt(self.cfg.vol20_window)
        sl_distance = self.cfg.sl_atr_mult * atr_proxy
        if not math.isfinite(sl_distance) or sl_distance <= 0:
            return None

        sl = current_price - sl_distance
        # The live/demo pipeline requires a positive TP distance. Price-Shock
        # exits are time-stop only; demo_trader skips TP hits for these names.
        tp = current_price + sl_distance * 10.0
        return Candidate(
            signal="BUY",
            confidence=70,
            sl=sl,
            tp=tp,
            reasons=[
                "✅ Price-Shock Reversion pre-reg trigger",
                f"✅ log_return<=rolling_{self.cfg.percentile:.2%}_tile(prev252)",
                f"✅ vol_q={self.cfg.vol_q}",
            ],
            entry_type=self.cfg.name,
            score=1.0,
            max_hold_bars=self.cfg.horizon_bars,
            sr_meta={
                "horizon_bars": self.cfg.horizon_bars,
                "sl_distance": sl_distance,
                "exit_kind": "horizon_or_atr_sl",
                "is_shadow": True,
                "vol_q": self.cfg.vol_q,
                "percentile": self.cfg.percentile,
            },
        )

    def add_precomputed_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out["log_return"] = np.log(out["Close"] / out["Close"].shift(1))
        out["vol20"] = out["log_return"].rolling(
            self.cfg.vol20_window, min_periods=self.cfg.vol20_window
        ).std()
        shifted_ret = out["log_return"].shift(1)
        shifted_vol = out["vol20"].shift(1)
        out["lower_0p01"] = shifted_ret.rolling(
            self.cfg.rolling_window, min_periods=self.cfg.rolling_window
        ).quantile(self.cfg.percentile)
        out["lower_p_0p01"] = out["lower_0p01"]
        out["vol_q20"] = shifted_vol.rolling(
            self.cfg.rolling_window, min_periods=self.cfg.rolling_window
        ).quantile(0.20)
        out["vol_q40"] = shifted_vol.rolling(
            self.cfg.rolling_window, min_periods=self.cfg.rolling_window
        ).quantile(0.40)
        out["vol_q60"] = shifted_vol.rolling(
            self.cfg.rolling_window, min_periods=self.cfg.rolling_window
        ).quantile(0.60)
        out["vol_q80"] = shifted_vol.rolling(
            self.cfg.rolling_window, min_periods=self.cfg.rolling_window
        ).quantile(0.80)
        conditions = [
            out["vol20"] <= out["vol_q20"],
            out["vol20"] <= out["vol_q40"],
            out["vol20"] <= out["vol_q60"],
            out["vol20"] <= out["vol_q80"],
            out["vol20"] > out["vol_q80"],
        ]
        out["vol_quintile_calc"] = np.select(
            conditions, ["Q1", "Q2", "Q3", "Q4", "Q5"], default=None
        )
        return out

    def signal_mask_from_dataframe(self, df: pd.DataFrame) -> pd.Series:
        computed = self.add_precomputed_columns(df)
        mask = (computed["log_return"] <= computed["lower_0p01"]).fillna(False)
        if self.cfg.vol_q != "ALL":
            mask = mask & (computed["vol_quintile_calc"] == self.cfg.vol_q)
        return pd.Series(mask, index=df.index).fillna(False)

    def _has_enough_history(self, bars) -> bool:
        return len(bars) >= self.cfg.rolling_window + self.cfg.vol20_window + 1

    def _compute_log_returns(self, bars) -> list[Optional[float]]:
        return self.add_precomputed_columns(self._as_dataframe(bars))["log_return"].tolist()

    def _compute_vol20(self, log_returns) -> list[Optional[float]]:
        return pd.Series(log_returns).rolling(
            self.cfg.vol20_window, min_periods=self.cfg.vol20_window
        ).std().tolist()

    def _rolling_quantile_excluding_current(self, log_returns, q: float) -> Optional[float]:
        series = pd.Series(log_returns).shift(1)
        value = series.rolling(
            self.cfg.rolling_window, min_periods=self.cfg.rolling_window
        ).quantile(q).iloc[-1]
        return None if pd.isna(value) else float(value)

    def _compute_vol_quintile(self, vol20, current_idx: int) -> Optional[VolBucket]:
        series = pd.Series(vol20)
        shifted = series.shift(1)
        pos = current_idx if current_idx >= 0 else len(series) + current_idx
        if pos < 0 or pos >= len(series) or pd.isna(series.iloc[pos]):
            return None
        hist = shifted.iloc[: pos + 1]
        q20 = hist.rolling(self.cfg.rolling_window, min_periods=self.cfg.rolling_window).quantile(0.20).iloc[-1]
        q40 = hist.rolling(self.cfg.rolling_window, min_periods=self.cfg.rolling_window).quantile(0.40).iloc[-1]
        q60 = hist.rolling(self.cfg.rolling_window, min_periods=self.cfg.rolling_window).quantile(0.60).iloc[-1]
        q80 = hist.rolling(self.cfg.rolling_window, min_periods=self.cfg.rolling_window).quantile(0.80).iloc[-1]
        if any(pd.isna(x) for x in (q20, q40, q60, q80)):
            return None
        current = float(series.iloc[pos])
        if current <= q20:
            return "Q1"
        if current <= q40:
            return "Q2"
        if current <= q60:
            return "Q3"
        if current <= q80:
            return "Q4"
        return "Q5"

    def _as_dataframe(self, bars) -> pd.DataFrame:
        if isinstance(bars, pd.DataFrame):
            return bars
        return pd.DataFrame(
            {
                "Open": [float(b.open) for b in bars],
                "High": [float(b.high) for b in bars],
                "Low": [float(b.low) for b in bars],
                "Close": [float(b.close) for b in bars],
            }
        )

    def _pair_matches(self, symbol: str, pair: str) -> bool:
        if not symbol:
            return True
        compact_symbol = str(symbol).upper().replace("=X", "").replace("/", "").replace("_", "")
        compact_pair = pair.upper().replace("_", "")
        return compact_pair in compact_symbol
