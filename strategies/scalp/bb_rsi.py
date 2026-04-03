"""BB + RSI Mean Reversion — レンジ相場用 (Bollinger 2001 + Wilder 1978)"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class BBRsiReversion(StrategyBase):
    name = "bb_rsi_reversion"
    mode = "scalp"

    # チューナブルパラメータ
    adx_max = 32          # レンジ判定上限
    bbpb_buy = 0.25       # BB%B BUY閾値
    bbpb_sell = 0.75      # BB%B SELL閾値
    rsi5_buy = 45         # RSI5 BUY閾値
    rsi5_sell = 55        # RSI5 SELL閾値
    stoch_buy = 45        # Stoch BUY閾値
    stoch_sell = 55       # Stoch SELL閾値
    tp_mult_tier1 = 2.0   # TP倍率 (Tier1)
    tp_mult_tier2 = 1.5   # TP倍率 (Tier2)

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if ctx.adx >= self.adx_max:
            return None

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0

        _min_sl = 0.030 if ctx.is_jpy else 0.00030

        # ── BUY判定 ──
        if (ctx.bbpb <= self.bbpb_buy and ctx.rsi5 < self.rsi5_buy
                and ctx.stoch_k < self.stoch_buy and ctx.stoch_k > ctx.stoch_d):
            signal = "BUY"
            tier1 = ctx.bbpb <= 0.05 and ctx.rsi5 < 25 and ctx.stoch_k < 20
            score = (4.5 if tier1 else 3.0) + (38 - ctx.rsi5) * 0.06
            reasons.append(f"✅ BB下限(%B={ctx.bbpb:.2f}≤{self.bbpb_buy}) — 平均回帰 (Bollinger 2001)")
            reasons.append(f"✅ RSI5売られすぎ({ctx.rsi5:.1f}<{self.rsi5_buy})")
            reasons.append(f"✅ Stochゴールデンクロス(K={ctx.stoch_k:.0f}>D={ctx.stoch_d:.0f})")
            # Stochクロスギャップボーナス
            gap = ctx.stoch_k - ctx.stoch_d
            if gap > 1.5:
                score += 0.6
                reasons.append(f"✅ Stochクロスギャップ大({gap:.1f}>1.5)")
            # 前バー陰線ボーナス
            if ctx.prev_close <= ctx.prev_open:
                score += 0.3
                reasons.append("✅ 前バー陰線（プルバック確認）")
            if tier1:
                reasons.append("🎯 Tier1: 極端条件（高確信）")
            # MACD方向ボーナス
            if ctx.macdh > 0:
                score += 0.5
                reasons.append("✅ MACDヒストグラム上昇")
            # MACD-H反転ボーナス
            if ctx.macdh > ctx.macdh_prev and ctx.macdh_prev <= ctx.macdh_prev2:
                score += 0.6
                reasons.append("✅ MACD-H反転上昇（モメンタム消耗→回復）")
            # SL/TP
            tp_mult = self.tp_mult_tier1 if tier1 else self.tp_mult_tier2
            tp = ctx.entry + ctx.atr7 * tp_mult
            sl_dist = max(abs(ctx.entry - ctx.bb_lower) + ctx.atr7 * 0.3, _min_sl)
            sl = ctx.entry - sl_dist

        # ── SELL判定 ──
        if (signal is None and ctx.bbpb >= self.bbpb_sell
                and ctx.rsi5 > self.rsi5_sell and ctx.stoch_k > self.stoch_sell
                and ctx.stoch_k < ctx.stoch_d):
            signal = "SELL"
            tier1 = ctx.bbpb >= 0.95 and ctx.rsi5 > 75 and ctx.stoch_k > 80
            score = (4.5 if tier1 else 3.0) + (ctx.rsi5 - 58) * 0.06
            reasons.append(f"✅ BB上限(%B={ctx.bbpb:.2f}≥{self.bbpb_sell}) — 平均回帰 (Bollinger 2001)")
            reasons.append(f"✅ RSI5買われすぎ({ctx.rsi5:.1f}>{self.rsi5_sell})")
            reasons.append(f"✅ Stochデッドクロス(K={ctx.stoch_k:.0f}<D={ctx.stoch_d:.0f})")
            gap = ctx.stoch_d - ctx.stoch_k
            if gap > 1.5:
                score += 0.6
                reasons.append(f"✅ Stochクロスギャップ大({gap:.1f}>1.5)")
            if ctx.prev_close >= ctx.prev_open:
                score += 0.3
                reasons.append("✅ 前バー陽線（戻り確認）")
            if tier1:
                reasons.append("🎯 Tier1: 極端条件（高確信）")
            if ctx.macdh < 0:
                score += 0.5
                reasons.append("✅ MACDヒストグラム下落")
            if ctx.macdh < ctx.macdh_prev and ctx.macdh_prev >= ctx.macdh_prev2:
                score += 0.6
                reasons.append("✅ MACD-H反転下落（モメンタム消耗→回復）")
            tp_mult = self.tp_mult_tier1 if tier1 else self.tp_mult_tier2
            tp = ctx.entry - ctx.atr7 * tp_mult
            sl_dist = max(abs(ctx.bb_upper - ctx.entry) + ctx.atr7 * 0.3, _min_sl)
            sl = ctx.entry + sl_dist

        if signal is None:
            return None

        conf = int(min(85, 50 + score * 4))
        reasons.append(f"📊 レジーム: レンジ(ADX={ctx.adx:.1f}<{self.adx_max})")
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)
