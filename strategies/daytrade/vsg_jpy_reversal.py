"""
VSG JPY Reversal — EWMA-forecast Vol Surprise Reversal (15m daytrade)

仮説 (Engle-Patton 2001 + 実測):
  Realized return が EWMA(λ=0.94) forecast の 1.5x を超える「vol surprise」
  発生時、JPY crosses (EUR_JPY, GBP_JPY) は **fade** する (mean reversion)。
  panic / carry unwind 系 event は overshoot → 反転構造。

vsg_audit (2026-04-27, 365d) 結果:
  EUR_JPY reversal th=1.5 fw=2: WR 58.1%, n=718, p_bonf 0.00081 ✅
  EUR_JPY reversal th=2.0 fw=2: WR 59.4%, n=367, p_bonf 0.01674 ✅
  GBP_JPY reversal th=1.0 fw=4: WR 55.6%, n=1439, p_bonf 0.00108 ✅
  → Bonferroni 90-test family で 7 combo 通過 — 真のエッジ確定

エントリ:
  - Symbol: EUR_JPY, GBP_JPY のみ (Bonferroni 通過 pair)
  - 直前 bar の |realized_ret| / EWMA_forecast > 1.5 (surprise event)
  - direction = -sign(realized_ret) → fade 方向
  - SL = 1 ATR、TP = 1.5 ATR (RR 1.5)
  - Hold ≤ 4 bars (60 min)

Shadow: enabled=True、PAIR_PROMOTED 追加なし default Sentinel
"""
from __future__ import annotations
from typing import Optional

import numpy as np

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from modules.round_number import shift_tp_inside


class VsgJpyReversal(StrategyBase):

    name = "vsg_jpy_reversal"
    mode = "daytrade"
    enabled = True   # Bonferroni-significant edge — Shadow data 蓄積で確認
    strategy_type = "MR"

    # Bonferroni 通過 pair のみ (USD_JPY は EWMA surprise で edge 弱い)
    _ALLOWED_SYMBOLS = frozenset({"EURJPY", "GBPJPY"})

    SURPRISE_THRESHOLD = 1.5      # |realized| / forecast > 1.5
    EWMA_LAMBDA = 0.94            # RiskMetrics standard

    SL_ATR_MULT = 1.0
    TP_ATR_MULT = 1.5
    MIN_RR = 1.4

    MAX_HOLD_BARS = 4

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        if sym not in self._ALLOWED_SYMBOLS:
            return None
        if ctx.df is None or len(ctx.df) < 30:
            return None

        # EWMA volatility forecast
        returns = ctx.df["Close"].pct_change().fillna(0)
        sq_ret = returns ** 2
        ewma_var = sq_ret.ewm(alpha=1 - self.EWMA_LAMBDA, adjust=False).mean()
        forecast = float(np.sqrt(ewma_var.iloc[-2]))   # t-1 forecast for t bar
        realized = float(abs(returns.iloc[-1]))

        if forecast <= 1e-9:
            return None
        surprise = (realized - forecast) / forecast

        if surprise <= self.SURPRISE_THRESHOLD:
            return None

        # Direction: fade
        last_ret = float(returns.iloc[-1])
        if last_ret == 0:
            return None
        signal = "SELL" if last_ret > 0 else "BUY"

        atr = max(ctx.atr, 1e-9)
        if signal == "BUY":
            sl = ctx.entry - self.SL_ATR_MULT * atr
            tp = ctx.entry + self.TP_ATR_MULT * atr
        else:
            sl = ctx.entry + self.SL_ATR_MULT * atr
            tp = ctx.entry - self.TP_ATR_MULT * atr

        # RNR: TP shift away from round numbers
        tp = shift_tp_inside(tp, signal, pip=0.01, shift_pips=3.0)

        sl_dist = abs(ctx.entry - sl)
        tp_dist = abs(tp - ctx.entry)
        if sl_dist <= 0:
            return None
        rr = tp_dist / sl_dist
        if rr < self.MIN_RR:
            return None

        score = 4.0 + min(2.0, surprise - 1.0)   # bigger surprise → higher score

        reasons = [
            f"✅ Vol surprise: realized/forecast={1+surprise:.2f}x (>{1+self.SURPRISE_THRESHOLD})",
            f"✅ Fade {signal} (last_ret={last_ret*100:+.3f}%)",
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
