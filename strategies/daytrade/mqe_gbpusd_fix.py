"""
MQE GBP_USD Fix — Month-End London 4pm Fix Reversal (15m daytrade)

仮説 (Melvin-Prins 2015 拡張、Frömmel 2008):
  Month-end last 2 営業日の London 4pm fix window (15:30-16:00 UTC) で
  GBP_USD は institutional rebalancing 圧力 → 直前の move を反転する典型。

mqe_audit (2026-04-27, 730d) 結果:
  GBP_USD reversal fw=6: WR 69.8%, n=96, p_bonf 0.00158 ✅
  GBP_USD reversal fw=4: WR 66.7%, n=96, p_bonf 0.01709 ✅
  GBP_USD reversal fw=8: WR 66.7%, n=96, p_bonf 0.01709 ✅
  Best Sharpe: 6.03 (fw=6)

エントリ:
  - GBP_USD のみ (Bonferroni-significant)
  - month_end_last_2_business_days ∧ 15:30-16:00 UTC 内
  - direction = -sign(prior 4-bar move) → fade
  - SL = 1 ATR, TP = 1.5 ATR
  - Hold ≤ 6 bars (90 min)
"""
from __future__ import annotations
from typing import Optional
import calendar

import numpy as np
import pandas as pd

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from modules.round_number import shift_tp_inside


def _is_month_end_window(ts: pd.Timestamp, days_before: int = 2) -> bool:
    """Last `days_before` business days of the month."""
    last_day = calendar.monthrange(ts.year, ts.month)[1]
    end = pd.Timestamp(ts.year, ts.month, last_day,
                       tz=ts.tz if hasattr(ts, "tz") else None)
    threshold_date = end
    count = 0
    while count < days_before:
        if threshold_date.weekday() < 5:
            count += 1
            if count >= days_before:
                break
        threshold_date = threshold_date - pd.Timedelta(days=1)
    return ts.date() >= threshold_date.date()


class MqeGbpusdFix(StrategyBase):

    name = "mqe_gbpusd_fix"
    mode = "daytrade"
    enabled = True
    strategy_type = "reversal"

    _ALLOWED_SYMBOLS = frozenset({"GBPUSD"})

    FIX_HOUR_START = 15        # UTC 15:00-16:00 (London 4pm fix)
    FIX_HOUR_END = 16
    MONTH_END_DAYS = 2

    SL_ATR_MULT = 1.0
    TP_ATR_MULT = 1.5
    MIN_RR = 1.4
    MAX_HOLD_BARS = 6
    PRIOR_MOVE_BARS = 4

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        if sym not in self._ALLOWED_SYMBOLS:
            return None
        if ctx.df is None or len(ctx.df) < self.PRIOR_MOVE_BARS + 2:
            return None
        if ctx.bar_time is None and not hasattr(ctx.df.index[-1], "hour"):
            return None

        # Get current timestamp
        ts = ctx.bar_time if ctx.bar_time is not None else ctx.df.index[-1]
        if not hasattr(ts, "hour") or not hasattr(ts, "year"):
            return None

        # Time window check
        if not (self.FIX_HOUR_START <= ts.hour < self.FIX_HOUR_END):
            return None
        if not _is_month_end_window(ts, days_before=self.MONTH_END_DAYS):
            return None

        # Prior move (last N bars)
        prior_close = float(ctx.df["Close"].iloc[-(self.PRIOR_MOVE_BARS + 1)])
        prior_move = ctx.entry - prior_close
        if abs(prior_move) < 1e-9:
            return None

        signal = "SELL" if prior_move > 0 else "BUY"

        atr = max(ctx.atr, 1e-9)
        if signal == "BUY":
            sl = ctx.entry - self.SL_ATR_MULT * atr
            tp = ctx.entry + self.TP_ATR_MULT * atr
        else:
            sl = ctx.entry + self.SL_ATR_MULT * atr
            tp = ctx.entry - self.TP_ATR_MULT * atr

        tp = shift_tp_inside(tp, signal, pip=0.0001, shift_pips=3.0)

        sl_dist = abs(ctx.entry - sl)
        tp_dist = abs(tp - ctx.entry)
        if sl_dist <= 0:
            return None
        rr = tp_dist / sl_dist
        if rr < self.MIN_RR:
            return None

        score = 4.5  # high-confidence event-driven
        reasons = [
            f"✅ Month-end fix window ({ts.hour:02d}:{ts.minute:02d} UTC)",
            f"✅ Prior {self.PRIOR_MOVE_BARS}-bar move {prior_move:+.5f} → fade {signal}",
            f"✅ RR={rr:.2f} hold≤{self.MAX_HOLD_BARS}bar",
        ]

        return Candidate(
            signal=signal,
            confidence=min(100, int(score * 18)),
            sl=float(sl),
            tp=float(tp),
            reasons=reasons,
            entry_type=self.name,
            score=float(score),
        )
