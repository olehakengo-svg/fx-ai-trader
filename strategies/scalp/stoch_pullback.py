"""Stochastic Trend Pullback — トレンド方向のStoch押し目/戻り"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class StochTrendPullback(StrategyBase):
    name = "stoch_trend_pullback"
    mode = "scalp"
    enabled = True   # 復帰 (2026-04-07): 本番13t WR=46.2% EV=+1.08 — 全scalp戦略中最良EV

    # チューナブルパラメータ（学術水準: ADX≥20でトレンド確認）
    adx_min = 20          # ADXトレンド閾値（12→20: 学術的に有意なトレンド水準）
    adx_weak = 25         # 弱トレンド帯（15→25: ADX20-25は弱トレンド）
    prev_stoch_buy = 48   # 前バーStoch売られすぎ閾値（42→48緩和）
    prev_stoch_sell = 52  # 前バーStoch買われすぎ閾値（58→52緩和）
    stoch_max_buy = 70    # Stoch上昇余地（65→70緩和）
    stoch_min_sell = 30   # Stoch下落余地（35→30緩和）
    tp_mult = 1.8
    sl_mult = 0.8

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if ctx.adx < self.adx_min:
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
                and ctx.rsi5 > 28 and ctx.rsi5 < 62
                and ctx.bbpb > 0.10 and ctx.bbpb < 0.70):
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
                and ctx.rsi5 > 38 and ctx.rsi5 < 72
                and ctx.bbpb > 0.30 and ctx.bbpb < 0.90):
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
