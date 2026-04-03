"""MTF Reversal Confluence — 複数時間軸RSI+MACDクロス一致"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class MtfReversalConfluence(StrategyBase):
    name = "mtf_reversal_confluence"
    mode = "scalp"

    # チューナブルパラメータ
    min_score = 3.2
    tp_mult = 1.5
    sl_mult = 0.5

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if ctx.is_friday:
            return None

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0

        # HTFからRSI/MACDを取得
        _htf_h1 = ctx.htf.get("h1", {})
        _htf_h4 = ctx.htf.get("h4", {})
        _htf_h1_rsi = _htf_h1.get("rsi", 50)
        _htf_h4_rsi = _htf_h4.get("rsi", 50)
        _htf_h1_score = _htf_h1.get("score", 0)

        # BUY: 複数時間軸でoversold + MACD反転
        _mtf_buy_rsi = (ctx.rsi5 < 40 and _htf_h1_rsi < 45) or (ctx.rsi5 < 35 and _htf_h4_rsi < 50)
        _mtf_buy_macd = ctx.macdh > 0 or ctx.macdh > ctx.macdh_prev
        _mtf_buy_stoch = ctx.stoch_k > ctx.stoch_d and ctx.stoch_k < 40

        if _mtf_buy_rsi and _mtf_buy_macd and _mtf_buy_stoch:
            signal = "BUY"
            score = 3.2
            # RSI一致ボーナス
            if ctx.rsi5 < 35 and _htf_h1_rsi < 40:
                score += 0.8
                reasons.append(f"✅ MTF RSI一致 (1m={ctx.rsi5:.0f}, 1H={_htf_h1_rsi:.0f})")
            else:
                score += 0.4
                reasons.append(f"✅ MTF RSI oversold (1m={ctx.rsi5:.0f}, 1H={_htf_h1_rsi:.0f})")
            # 4H RSIも一致
            if _htf_h4_rsi < 45:
                score += 0.5
                reasons.append(f"✅ 4H RSI一致({_htf_h4_rsi:.0f})")
            # HTF MACDクロス一致
            if _htf_h1_score > 0:
                score += 0.5
                reasons.append("✅ 1H MACDブルクロス一致")
            reasons.append(f"✅ MACD-H反転({ctx.macdh:.5f})")
            reasons.append(f"✅ Stoch反転({ctx.stoch_k:.0f}>{ctx.stoch_d:.0f})")
            tp = ctx.entry + ctx.atr7 * self.tp_mult
            sl = ctx.entry - ctx.atr7 * self.sl_mult

        # SELL: 複数時間軸でoverbought + MACD反転
        _mtf_sell_rsi = (ctx.rsi5 > 60 and _htf_h1_rsi > 55) or (ctx.rsi5 > 65 and _htf_h4_rsi > 50)
        _mtf_sell_macd = ctx.macdh < 0 or ctx.macdh < ctx.macdh_prev
        _mtf_sell_stoch = ctx.stoch_k < ctx.stoch_d and ctx.stoch_k > 60

        if signal is None and _mtf_sell_rsi and _mtf_sell_macd and _mtf_sell_stoch:
            signal = "SELL"
            score = 3.2
            if ctx.rsi5 > 65 and _htf_h1_rsi > 60:
                score += 0.8
                reasons.append(f"✅ MTF RSI一致 (1m={ctx.rsi5:.0f}, 1H={_htf_h1_rsi:.0f})")
            else:
                score += 0.4
                reasons.append(f"✅ MTF RSI overbought (1m={ctx.rsi5:.0f}, 1H={_htf_h1_rsi:.0f})")
            if _htf_h4_rsi > 55:
                score += 0.5
                reasons.append(f"✅ 4H RSI一致({_htf_h4_rsi:.0f})")
            if _htf_h1_score < 0:
                score += 0.5
                reasons.append("✅ 1H MACDベアクロス一致")
            reasons.append(f"✅ MACD-H反転({ctx.macdh:.5f})")
            reasons.append(f"✅ Stoch反転({ctx.stoch_k:.0f}<{ctx.stoch_d:.0f})")
            tp = ctx.entry - ctx.atr7 * self.tp_mult
            sl = ctx.entry + ctx.atr7 * self.sl_mult

        if signal is None or score < self.min_score:
            return None

        conf = int(min(80, 40 + score * 5))
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)
