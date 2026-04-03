"""MACD Histogram Reversal at BB Extreme — モメンタム消耗 + 価格極端 = 高確率反転"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class MacdhReversal(StrategyBase):
    name = "macdh_reversal"
    mode = "scalp"

    # チューナブルパラメータ（緩和済み）
    bbpb_buy = 0.30       # BB%B BUY閾値（0.25→0.30緩和）
    bbpb_sell = 0.70      # BB%B SELL閾値（0.75→0.70緩和）
    rsi5_buy = 48         # RSI5 BUY閾値（42→48緩和）
    rsi5_sell = 52        # RSI5 SELL閾値（58→52緩和）
    tp_mult = 1.5         # TP倍率
    sl_mult = 1.0         # SL倍率

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0

        # BUY: BB下限 + MACD-H上向き反転
        if (ctx.bbpb < self.bbpb_buy
                and ctx.macdh > ctx.macdh_prev
                and ctx.macdh_prev <= ctx.macdh_prev2
                and ctx.rsi5 < self.rsi5_buy):
            signal = "BUY"
            score = 3.5
            reasons.append(f"✅ MACD-Hモメンタム反転上昇(H={ctx.macdh:.4f}, 前={ctx.macdh_prev:.4f})")
            reasons.append(f"✅ BB下限圏(%B={ctx.bbpb:.2f}<{self.bbpb_buy})")
            reasons.append(f"✅ RSI5売られすぎ({ctx.rsi5:.1f}<{self.rsi5_buy})")
            if ctx.stoch_k > ctx.stoch_d:
                score += 0.5
                reasons.append("✅ Stochゴールデンクロス(K>D)")
            tp = ctx.entry + ctx.atr7 * self.tp_mult
            sl = ctx.entry - ctx.atr7 * self.sl_mult

        # SELL: BB上限 + MACD-H下向き反転
        elif (ctx.bbpb > self.bbpb_sell
                and ctx.macdh < ctx.macdh_prev
                and ctx.macdh_prev >= ctx.macdh_prev2
                and ctx.rsi5 > self.rsi5_sell):
            signal = "SELL"
            score = 3.5
            reasons.append(f"✅ MACD-Hモメンタム反転下落(H={ctx.macdh:.4f}, 前={ctx.macdh_prev:.4f})")
            reasons.append(f"✅ BB上限圏(%B={ctx.bbpb:.2f}>{self.bbpb_sell})")
            reasons.append(f"✅ RSI5買われすぎ({ctx.rsi5:.1f}>{self.rsi5_sell})")
            if ctx.stoch_k < ctx.stoch_d:
                score += 0.5
                reasons.append("✅ Stochデッドクロス(K<D)")
            tp = ctx.entry - ctx.atr7 * self.tp_mult
            sl = ctx.entry + ctx.atr7 * self.sl_mult

        if signal is None:
            return None

        conf = int(min(80, 45 + score * 4))
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)
