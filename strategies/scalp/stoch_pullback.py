"""Stochastic Trend Pullback — トレンド方向のStoch押し目/戻り"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class StochTrendPullback(StrategyBase):
    name = "stoch_trend_pullback"
    mode = "scalp"

    # チューナブルパラメータ
    adx_min = 15          # ADXトレンド閾値
    adx_weak = 18         # 弱トレンド帯（グラデーション減衰）
    prev_stoch_buy = 42   # 前バーStoch売られすぎ閾値
    prev_stoch_sell = 58  # 前バーStoch買われすぎ閾値
    stoch_max_buy = 65    # Stoch上昇余地
    stoch_min_sell = 35   # Stoch下落余地
    tp_mult = 1.8
    sl_mult = 0.8

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if ctx.adx < self.adx_min or ctx.is_friday:
            return None
        if ctx.df is None or len(ctx.df) < 5:
            return None

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0

        _prev_stoch_k = float(ctx.df.iloc[-2].get("stoch_k", 50)) if len(ctx.df) >= 2 else 50

        # BUY: 上昇トレンド中のStoch売られすぎ回復
        if (ctx.ema9 > ctx.ema21 and ctx.entry > ctx.ema21
                and ctx.stoch_k > ctx.stoch_d
                and _prev_stoch_k < self.prev_stoch_buy
                and ctx.stoch_k < self.stoch_max_buy
                and ctx.rsi5 > 32 and ctx.rsi5 < 58
                and ctx.bbpb > 0.15 and ctx.bbpb < 0.65):
            signal = "BUY"
            score = 3.2 + min((ctx.adx - self.adx_min) * 0.04, 0.8)
            reasons.append(f"✅ トレンドプルバック: Stoch売られすぎ回復(K={ctx.stoch_k:.0f}, 前={_prev_stoch_k:.0f})")
            reasons.append(f"✅ 上昇トレンド確認 (EMA9>21, ADX={ctx.adx:.1f}≥{self.adx_min})")
            reasons.append(f"✅ Stochゴールデンクロス(K>D: {ctx.stoch_k:.0f}>{ctx.stoch_d:.0f})")
            tp = ctx.entry + ctx.atr7 * self.tp_mult
            sl = ctx.entry - ctx.atr7 * self.sl_mult

        # SELL: 下降トレンド中のStoch買われすぎ回復
        elif (ctx.ema9 < ctx.ema21 and ctx.entry < ctx.ema21
                and ctx.stoch_k < ctx.stoch_d
                and _prev_stoch_k > self.prev_stoch_sell
                and ctx.stoch_k > self.stoch_min_sell
                and ctx.rsi5 > 42 and ctx.rsi5 < 68
                and ctx.bbpb > 0.35 and ctx.bbpb < 0.85):
            signal = "SELL"
            score = 3.2 + min((ctx.adx - self.adx_min) * 0.04, 0.8)
            reasons.append(f"✅ トレンドプルバック: Stoch買われすぎ回復(K={ctx.stoch_k:.0f}, 前={_prev_stoch_k:.0f})")
            reasons.append(f"✅ 下降トレンド確認 (EMA9<21, ADX={ctx.adx:.1f}≥{self.adx_min})")
            reasons.append(f"✅ Stochデッドクロス(K<D: {ctx.stoch_k:.0f}<{ctx.stoch_d:.0f})")
            tp = ctx.entry - ctx.atr7 * self.tp_mult
            sl = ctx.entry + ctx.atr7 * self.sl_mult

        if signal is None:
            return None

        conf = int(min(80, 45 + score * 4))
        # ADX弱トレンド帯はグラデーション減衰
        if ctx.adx < self.adx_weak:
            conf = int(conf * 0.9)
            reasons.append(f"⚠️ ADX弱トレンド帯({ctx.adx:.1f}<{self.adx_weak}) → conf×0.9")
        reasons.append(f"📊 レジーム: トレンド(ADX={ctx.adx:.1f}≥{self.adx_min})")
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)
