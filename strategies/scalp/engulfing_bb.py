"""Engulfing at BB Band — 包み足パターン at BB極端"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class EngulfingBB(StrategyBase):
    name = "engulfing_bb"
    mode = "scalp"
    enabled = False  # DISABLED: BT EV negative

    # チューナブルパラメータ
    bbpb_buy = 0.30
    bbpb_sell = 0.70
    rsi5_buy = 45
    rsi5_sell = 55
    body_mult = 1.3   # 包み倍率
    min_range_mult = 0.5  # ATR比の最低足サイズ
    tp_mult = 1.5
    sl_mult = 0.8
    sl_offset = 0.15  # ATR倍率

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if ctx.is_friday:
            return None
        if ctx.df is None or len(ctx.df) < 2:
            return None

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0

        _prev_body = abs(ctx.prev_close - ctx.prev_open)
        _curr_body = abs(ctx.entry - ctx.open_price)
        _curr_range = float(ctx.df.iloc[-1]["High"]) - float(ctx.df.iloc[-1]["Low"])

        # 包み足判定
        _is_bullish = (ctx.prev_close < ctx.prev_open  # 前足陰線
                       and ctx.entry > ctx.open_price    # 現在足陽線
                       and _curr_body > _prev_body * self.body_mult
                       and ctx.entry > ctx.prev_open     # 前足始値を超える
                       and _curr_range > ctx.atr7 * self.min_range_mult)

        _is_bearish = (ctx.prev_close > ctx.prev_open
                       and ctx.entry < ctx.open_price
                       and _curr_body > _prev_body * self.body_mult
                       and ctx.entry < ctx.prev_open
                       and _curr_range > ctx.atr7 * self.min_range_mult)

        # BUY
        if _is_bullish and ctx.bbpb < self.bbpb_buy and ctx.rsi5 < self.rsi5_buy:
            signal = "BUY"
            score = 4.0
            reasons.append(f"✅ ブリッシュ包み足(ボディ比{_curr_body/_prev_body:.1f}x)")
            reasons.append(f"✅ BB極端下限(%B={ctx.bbpb:.2f}<{self.bbpb_buy})")
            reasons.append(f"✅ RSI5売られすぎ({ctx.rsi5:.1f}<{self.rsi5_buy})")
            if ctx.stoch_k > ctx.stoch_d:
                score += 0.5
                reasons.append("✅ Stochゴールデンクロス確認(K>D)")
            tp = ctx.entry + ctx.atr7 * self.tp_mult
            sl = min(float(ctx.df.iloc[-1]["Low"]), ctx.entry - ctx.atr7 * self.sl_mult) - ctx.atr7 * self.sl_offset

        # SELL
        elif _is_bearish and ctx.bbpb > self.bbpb_sell and ctx.rsi5 > self.rsi5_sell:
            signal = "SELL"
            score = 4.0
            reasons.append(f"✅ ベアリッシュ包み足(ボディ比{_curr_body/_prev_body:.1f}x)")
            reasons.append(f"✅ BB極端上限(%B={ctx.bbpb:.2f}>{self.bbpb_sell})")
            reasons.append(f"✅ RSI5買われすぎ({ctx.rsi5:.1f}>{self.rsi5_sell})")
            if ctx.stoch_k < ctx.stoch_d:
                score += 0.5
                reasons.append("✅ Stochデッドクロス確認(K<D)")
            tp = ctx.entry - ctx.atr7 * self.tp_mult
            sl = max(float(ctx.df.iloc[-1]["High"]), ctx.entry + ctx.atr7 * self.sl_mult) + ctx.atr7 * self.sl_offset

        if signal is None:
            return None

        conf = int(min(82, 48 + score * 4))
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)
