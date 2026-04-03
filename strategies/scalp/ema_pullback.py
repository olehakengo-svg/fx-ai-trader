"""EMA Pullback — トレンド方向のEMAプルバック反発"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class EmaPullback(StrategyBase):
    name = "ema_pullback"
    mode = "scalp"

    # チューナブルパラメータ（緩和済み）
    adx_min = 12           # （15→12緩和）
    adx_weak = 15          # （18→15緩和）
    rsi5_buy_min = 30      # （38→30緩和）
    rsi5_buy_max = 62      # （58→62緩和）
    rsi5_sell_min = 38     # （42→38緩和）
    rsi5_sell_max = 70     # （62→70緩和）
    bbpb_buy_min = 0.12    # （0.20→0.12緩和）
    bbpb_buy_max = 0.70    # （0.65→0.70緩和）
    bbpb_sell_min = 0.30   # （0.35→0.30緩和）
    bbpb_sell_max = 0.88   # （0.80→0.88緩和）
    tp_mult = 1.8
    sl_ema_offset = 0.3   # EMA21からのSLオフセット（ATR倍率）

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

        # BUY: 上昇トレンド + EMA21付近へのプルバック + 反発
        if (ctx.ema9 > ctx.ema21  # EMA順列（EMA50整列不要に緩和）
                and ctx.entry >= ctx.ema21  # EMA21の上に戻った
                and ctx.prev_low <= ctx.ema9  # 前バーがEMA9以下にタッチ
                and ctx.prev_low >= ctx.ema21 - ctx.atr7 * self.sl_ema_offset
                and ctx.entry > ctx.prev_close  # 現バー陽線方向
                and ctx.rsi5 > self.rsi5_buy_min and ctx.rsi5 < self.rsi5_buy_max
                and ctx.bbpb > self.bbpb_buy_min and ctx.bbpb < self.bbpb_buy_max):
            signal = "BUY"
            score = 3.0 + min((ctx.adx - self.adx_min) * 0.05, 1.0)
            reasons.append(f"✅ EMAプルバック反発: EMA9({ctx.ema9:.3f})タッチ→反発")
            reasons.append(f"✅ EMA完全整列 (9>21>50, ADX={ctx.adx:.1f})")
            reasons.append(f"✅ 陽線反発確認 ({ctx.entry:.3f}>{ctx.prev_close:.3f})")
            if ctx.prev_low <= ctx.ema21 + ctx.atr7 * 0.1:
                score += 0.5
                reasons.append(f"✅ EMA21深押し(Low={ctx.prev_low:.3f})")
            if ctx.stoch_k > ctx.stoch_d:
                score += 0.3
                reasons.append("✅ Stochゴールデンクロス")
            tp = ctx.entry + ctx.atr7 * self.tp_mult
            sl = ctx.ema21 - ctx.atr7 * self.sl_ema_offset

        # SELL: 下降トレンド + EMA21付近への戻り + 反落
        elif (ctx.ema9 < ctx.ema21  # EMA逆順列（EMA50整列不要に緩和）
                and ctx.entry <= ctx.ema21  # EMA21の下に戻った
                and ctx.prev_high >= ctx.ema9  # 前バーがEMA9以上にタッチ
                and ctx.prev_high <= ctx.ema21 + ctx.atr7 * self.sl_ema_offset
                and ctx.entry < ctx.prev_close  # 現バー陰線方向
                and ctx.rsi5 > self.rsi5_sell_min and ctx.rsi5 < self.rsi5_sell_max
                and ctx.bbpb > self.bbpb_sell_min and ctx.bbpb < self.bbpb_sell_max):
            signal = "SELL"
            score = 3.0 + min((ctx.adx - self.adx_min) * 0.05, 1.0)
            reasons.append(f"✅ EMAプルバック反落: EMA9({ctx.ema9:.3f})タッチ→反落")
            reasons.append(f"✅ EMA逆整列 (9<21<50, ADX={ctx.adx:.1f})")
            reasons.append(f"✅ 陰線反落確認 ({ctx.entry:.3f}<{ctx.prev_close:.3f})")
            if ctx.prev_high >= ctx.ema21 - ctx.atr7 * 0.1:
                score += 0.5
                reasons.append(f"✅ EMA21深戻り(High={ctx.prev_high:.3f})")
            if ctx.stoch_k < ctx.stoch_d:
                score += 0.3
                reasons.append("✅ Stochデッドクロス")
            tp = ctx.entry - ctx.atr7 * self.tp_mult
            sl = ctx.ema21 + ctx.atr7 * self.sl_ema_offset

        if signal is None:
            return None

        conf = int(min(75, 40 + score * 4))
        # ADX弱トレンド帯はグラデーション減衰
        if ctx.adx < self.adx_weak:
            conf = int(conf * 0.9)
            reasons.append(f"⚠️ ADX弱トレンド帯({ctx.adx:.1f}<{self.adx_weak}) → conf×0.9")
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)
