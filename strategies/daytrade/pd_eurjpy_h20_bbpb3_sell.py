"""
pd_eurjpy_h20_bbpb3_sell — Phase 8 Track A discovered cell, Sentinel deploy.

Pre-reg / aggregation:
  - knowledge-base/wiki/decisions/pre-reg-phase8-track-a-2026-04-28.md
  - raw/phase8/aggregation_2026-04-28.md (master gate + override rationale)

Cell specification (Track A 3-way interaction, holdout-passed):
  pair=EUR_JPY, hour_utc=20, bbpb_15m_b=3 (bbpb_15m ∈ (0.6, 0.8]),
  direction=SELL, SL=1.0*ATR, TP=1.5*ATR, RR=1.5, fw=12 (informational).

Backtest metrics:
  Training (275d, 365d-90d holdout): n=102 WR=0.618 Wilson_lo=0.521
    EV_net=+3.17p PF=1.596 Kelly=0.231 Sharpe_pe=0.231 trades/mo=11.1
    BH-FDR p=0.022 (Stage 1 LOCK pass)
  Holdout (90d OOS): n=40 WR=0.600 Wilson_lo=0.446 EV_net=+2.14p PF=1.330

Master gate:
  Wilson_lower_holdout 0.446 < strict gate 0.48 (n-limited, 0.034 miss).
  Adopted under aggressive Shadow exploration override per master plan
  §「Shadow deployment は積極的に top 3 採用、迷ったら採用側に倒す」.
  Orthogonality vs existing 7 strategies: ✓ (LCR-v2 covers GBP_JPY only;
  EUR_JPY × hour_utc=20 was Phase 7 single-feature reject — 3rd feature
  bbpb_15m_b=3 unlocks the positive subset).

Implementation:
  - 15m TF only (cell discovered on 15m bars)
  - Symbol gate: EUR_JPY only
  - Hour gate: UTC 20:00-20:59 (hour_utc bucket = 20)
  - bbpb gate: 0.6 < bbpb ≤ 0.8
  - SL=1.0*ATR above entry, TP=1.5*ATR below entry, MIN_RR=1.5

Sentinel 0.01 lot via universal_sentinel registration in tier-master.json.
PAIR_PROMOTED 不可 — 30 trade Live shadow 蓄積後 cell_edge_audit 再判定。
"""
from typing import Optional

from strategies.base import Candidate, StrategyBase
from strategies.context import SignalContext


class PdEurJpyH20Bbpb3Sell(StrategyBase):
    name = "pd_eurjpy_h20_bbpb3_sell"
    mode = "daytrade"
    enabled = True
    strategy_type = "reversal"

    _ALLOWED_NORMSYM = "EURJPY"
    _ALLOWED_TFS = frozenset({"15m"})
    HOUR_UTC = 20
    BBPB_LOW = 0.6   # exclusive
    BBPB_HIGH = 0.8  # inclusive

    SL_ATR_MULT = 1.0
    TP_ATR_MULT = 1.5
    MIN_RR = 1.5

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        sym = (ctx.symbol or "").upper().replace("=X", "").replace("/", "").replace("_", "")
        if sym != self._ALLOWED_NORMSYM:
            return None

        if (ctx.tf or "").lower() not in self._ALLOWED_TFS:
            return None

        if ctx.hour_utc != self.HOUR_UTC:
            return None

        if not (self.BBPB_LOW < ctx.bbpb <= self.BBPB_HIGH):
            return None

        if ctx.atr <= 0 or ctx.entry <= 0:
            return None

        if ctx.is_friday:
            return None

        sl = ctx.entry + self.SL_ATR_MULT * ctx.atr
        tp = ctx.entry - self.TP_ATR_MULT * ctx.atr

        sl_d = abs(sl - ctx.entry)
        tp_d = abs(ctx.entry - tp)
        if sl_d <= 0 or tp_d + 1e-9 < self.MIN_RR * sl_d:
            return None

        score = 3.5
        reasons = [
            f"✅ PD EURJPY h20 bbpb3 SELL: bbpb={ctx.bbpb:.2f} ∈ (0.6, 0.8]",
            f"📊 RR={tp_d / sl_d:.1f} SL={sl:.3f} TP={tp:.3f} (1.0/1.5×ATR)",
        ]

        # Confidence boost when RSI is also elevated (alignment with mean-reversion)
        if ctx.rsi >= 60:
            score += 0.3
            reasons.append(f"✅ RSI={ctx.rsi:.0f} ≥ 60 (overbought alignment)")

        conf = int(min(70, 45 + score * 4))
        return Candidate(
            signal="SELL",
            confidence=conf,
            sl=sl,
            tp=tp,
            reasons=reasons,
            entry_type=self.name,
            score=score,
        )
