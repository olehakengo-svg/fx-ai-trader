"""
RSK GBP_JPY Reversion — Realized Skewness Mean Reversion (15m daytrade)

仮説 (Barndorff-Nielsen-Shephard 2005, Amaya-Christoffersen 2015):
  Rolling 30-bar realized skewness の z-score が ±2.0σ extreme で
  反転 bias 発生 (downside skew exhausts → BUY edge、upside skew → SELL).
  GBP_JPY は intraday 変動が最大級で skewness 信号が最も鋭敏。

rsk_audit (2026-04-27, 365d) 結果:
  GBP_JPY sw=30 th=2.0 fw=6: WR 54.7%, n=1915, Sharpe 12.2, p_bonf 0.003 ✅
  + 12 more Bonferroni-significant combos すべて GBP_JPY
  Best Sharpe: sw=20 th=2.0 fw=2: 14.2

エントリ:
  - GBP_JPY のみ (Bonferroni-significant 唯一の pair)
  - rolling 30-bar realized skewness z-score |z| > 2.0
  - direction = -sign(z) → MR
  - SL = 1 ATR, TP = 1.5 ATR (RR 1.5)
  - Hold ≤ 6 bars (90 min)
"""
from __future__ import annotations
from typing import Optional

import numpy as np

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from modules.round_number import shift_tp_inside


class RskGbpjpyReversion(StrategyBase):

    name = "rsk_gbpjpy_reversion"
    mode = "daytrade"
    enabled = True
    strategy_type = "MR"

    _ALLOWED_SYMBOLS = frozenset({"GBPJPY"})

    SKEW_WINDOW = 30           # rolling skewness window
    SKEW_Z_WINDOW = 96         # z-normalization window (24h)
    Z_THRESHOLD = 2.0          # |z| > 2.0 = extreme

    SL_ATR_MULT = 1.0
    TP_ATR_MULT = 1.5
    MIN_RR = 1.4
    MAX_HOLD_BARS = 6

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        if sym not in self._ALLOWED_SYMBOLS:
            return None
        if ctx.df is None or len(ctx.df) < (self.SKEW_WINDOW + self.SKEW_Z_WINDOW):
            return None

        # Compute rolling realized skewness (vectorized)
        r = ctx.df["Close"].pct_change().fillna(0)
        m1 = r.rolling(self.SKEW_WINDOW).mean()
        centered = r - m1
        m3 = (centered ** 3).rolling(self.SKEW_WINDOW).mean()
        var = (centered ** 2).rolling(self.SKEW_WINDOW).mean()
        std = var.pow(0.5)
        skew = m3 / (std ** 3 + 1e-12)

        # Z-score normalize
        skew_mean = skew.rolling(self.SKEW_Z_WINDOW).mean()
        skew_std = skew.rolling(self.SKEW_Z_WINDOW).std()
        skew_z = (skew - skew_mean) / (skew_std + 1e-12)

        latest_z = float(skew_z.iloc[-1])
        if not np.isfinite(latest_z):
            return None

        if abs(latest_z) < self.Z_THRESHOLD:
            return None

        # MR direction: negative skew → BUY
        signal = "BUY" if latest_z < 0 else "SELL"

        # Confirmation: bar direction matches
        if signal == "BUY" and ctx.entry < ctx.open_price:
            return None
        if signal == "SELL" and ctx.entry > ctx.open_price:
            return None

        atr = max(ctx.atr, 1e-9)
        if signal == "BUY":
            sl = ctx.entry - self.SL_ATR_MULT * atr
            tp = ctx.entry + self.TP_ATR_MULT * atr
        else:
            sl = ctx.entry + self.SL_ATR_MULT * atr
            tp = ctx.entry - self.TP_ATR_MULT * atr

        tp = shift_tp_inside(tp, signal, pip=0.01, shift_pips=3.0)

        sl_dist = abs(ctx.entry - sl)
        tp_dist = abs(tp - ctx.entry)
        if sl_dist <= 0:
            return None
        rr = tp_dist / sl_dist
        if rr < self.MIN_RR:
            return None

        score = 4.0 + min(2.0, abs(latest_z) - self.Z_THRESHOLD)
        reasons = [
            f"✅ Realized skew z={latest_z:+.2f} (>{self.Z_THRESHOLD})",
            f"✅ Skewness MR {signal} (downside exhaustion)" if signal == "BUY"
                else f"✅ Skewness MR {signal} (upside exhaustion)",
            f"✅ RR={rr:.2f} hold≤{self.MAX_HOLD_BARS}bar",
        ]

        return Candidate(
            signal=signal,
            confidence=min(100, int(score * 16)),
            sl=float(sl),
            tp=float(tp),
            reasons=reasons,
            entry_type=self.name,
            score=float(score),
        )
