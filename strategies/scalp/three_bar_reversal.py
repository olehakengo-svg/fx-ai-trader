"""Three-Bar Reversal — 3本足反転パターン"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class ThreeBarReversal(StrategyBase):
    name = "three_bar_reversal"
    mode = "scalp"
    enabled = False  # DISABLED: BT結果未検証

    # チューナブルパラメータ
    bbpb_buy = 0.35
    bbpb_sell = 0.65
    rsi5_buy = 42
    rsi5_sell = 58
    tp_mult = 1.5
    sl_offset = 0.15  # ATR倍率

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if ctx.is_friday:
            return None
        if ctx.df is None or len(ctx.df) < 4:
            return None

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0

        _c3 = float(ctx.df.iloc[-4]["Close"]); _o3 = float(ctx.df.iloc[-4]["Open"])
        _c2 = float(ctx.df.iloc[-3]["Close"]); _o2 = float(ctx.df.iloc[-3]["Open"])
        _c1 = float(ctx.df.iloc[-2]["Close"]); _o1 = float(ctx.df.iloc[-2]["Open"])

        _three_bear = (_c3 < _o3) and (_c2 < _o2) and (_c1 < _o1)
        _three_bull = (_c3 > _o3) and (_c2 > _o2) and (_c1 > _o1)

        # BUY: 3連続陰線→陽線
        _curr_bull = ctx.entry > ctx.open_price
        if (_three_bear and _curr_bull
                and ctx.entry > float(ctx.df.iloc[-2]["High"])
                and ctx.bbpb < self.bbpb_buy
                and ctx.rsi5 < self.rsi5_buy):
            signal = "BUY"
            score = 3.3
            reasons.append("✅ 3本足反転: 3連続陰線→陽線突破")
            reasons.append(f"✅ 前足高値{float(ctx.df.iloc[-2]['High']):.3f}超え — 反転確認")
            reasons.append(f"✅ BB下半分(%B={ctx.bbpb:.2f}) + RSI={ctx.rsi5:.0f}")
            if ctx.stoch_k > ctx.stoch_d:
                score += 0.4
                reasons.append("✅ Stochクロス確認")
            tp = ctx.entry + ctx.atr7 * self.tp_mult
            sl = min(float(ctx.df.iloc[-2]["Low"]), float(ctx.df.iloc[-3]["Low"])) - ctx.atr7 * self.sl_offset

        # SELL: 3連続陽線→陰線
        _curr_bear = ctx.entry < ctx.open_price
        if (signal is None and _three_bull and _curr_bear
                and ctx.entry < float(ctx.df.iloc[-2]["Low"])
                and ctx.bbpb > self.bbpb_sell
                and ctx.rsi5 > self.rsi5_sell):
            signal = "SELL"
            score = 3.3
            reasons.append("✅ 3本足反転: 3連続陽線→陰線突破")
            reasons.append(f"✅ 前足安値{float(ctx.df.iloc[-2]['Low']):.3f}割れ — 反転確認")
            reasons.append(f"✅ BB上半分(%B={ctx.bbpb:.2f}) + RSI={ctx.rsi5:.0f}")
            if ctx.stoch_k < ctx.stoch_d:
                score += 0.4
                reasons.append("✅ Stochデッドクロス確認")
            tp = ctx.entry - ctx.atr7 * self.tp_mult
            sl = max(float(ctx.df.iloc[-2]["High"]), float(ctx.df.iloc[-3]["High"])) + ctx.atr7 * self.sl_offset

        if signal is None:
            return None

        conf = int(min(78, 45 + score * 4))
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)
