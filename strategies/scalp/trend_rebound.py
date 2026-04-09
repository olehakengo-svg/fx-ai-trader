"""Trend Rebound — 強トレンド時の逆張りリバウンド (Jegadeesh 1990)"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class TrendRebound(StrategyBase):
    name = "trend_rebound"
    mode = "scalp"
    enabled = True   # v7.0: Sentinel再有効化 — デモデータ蓄積で検証

    # チューナブルパラメータ（緩和済み）
    adx_min = 25           # （35→25緩和）
    stoch_buy = 12         # （5→12緩和）
    stoch_sell = 88         # （95→88緩和）
    rsi5_buy = 28          # （22→28緩和）
    rsi5_sell = 72          # （78→72緩和）
    bbpb_buy = 0.12        # （0.08→0.12緩和）
    bbpb_sell = 0.88        # （0.92→0.88緩和）
    momentum_limit = 8     # pip（5→8緩和）
    sl_mult = 1.0
    tp_mult_high = 1.5
    tp_mult_low = 1.0

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if ctx.adx < self.adx_min:
            return None
        if ctx.df is None or len(ctx.df) < 10:
            return None

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0

        _prev_stoch_k = float(ctx.df.iloc[-2].get("stoch_k", 50)) if len(ctx.df) >= 2 else 50

        # 10バーモメンタム
        _momentum = 0.0
        if len(ctx.df) >= 10:
            _momentum = (ctx.entry - float(ctx.df["Close"].iloc[-10])) * ctx.pip_mult

        # BUY: 下降トレンド中のリバウンド
        if (ctx.stoch_k < self.stoch_buy
                and ctx.rsi5 < self.rsi5_buy
                and ctx.bbpb < self.bbpb_buy
                and ctx.entry > ctx.open_price  # 陽線確認
                and ctx.ema9 < ctx.ema21         # 下降トレンド確認
                and _momentum < self.momentum_limit):
            signal = "BUY"
            score = 3.5
            reasons.append(f"✅ Trend Rebound BUY: ADX={ctx.adx:.0f}≥{self.adx_min} + EMA下降(9<21)")
            reasons.append(f"✅ 極端値: Stoch={ctx.stoch_k:.0f}<{self.stoch_buy}, RSI={ctx.rsi5:.0f}<{self.rsi5_buy}, BB%B={ctx.bbpb:.2f}<{self.bbpb_buy}")
            reasons.append(f"✅ 陽線反転 + モメンタム中立({_momentum:+.1f}pip)")
            if ctx.macdh > ctx.macdh_prev:
                score += 0.5
                reasons.append("✅ MACD-H反転上昇")
            if ctx.stoch_k > ctx.stoch_d:
                score += 0.5
                reasons.append("✅ Stoch GC")
            if ctx.stoch_k > _prev_stoch_k:
                score += 0.3
            tp = ctx.entry + ctx.atr7 * (self.tp_mult_high if score >= 4.0 else self.tp_mult_low)
            sl = ctx.entry - ctx.atr7 * self.sl_mult

        # SELL: 上昇トレンド中のリバウンド
        elif (ctx.stoch_k > self.stoch_sell
                and ctx.rsi5 > self.rsi5_sell
                and ctx.bbpb > self.bbpb_sell
                and ctx.entry < ctx.open_price  # 陰線確認
                and ctx.ema9 > ctx.ema21         # 上昇トレンド確認
                and _momentum > -self.momentum_limit):
            signal = "SELL"
            score = 3.5
            reasons.append(f"✅ Trend Rebound SELL: ADX={ctx.adx:.0f}≥{self.adx_min} + EMA上昇(9>21)")
            reasons.append(f"✅ 極端値: Stoch={ctx.stoch_k:.0f}>{self.stoch_sell}, RSI={ctx.rsi5:.0f}>{self.rsi5_sell}, BB%B={ctx.bbpb:.2f}>{self.bbpb_sell}")
            reasons.append(f"✅ 陰線反転 + モメンタム中立({_momentum:+.1f}pip)")
            if ctx.macdh < ctx.macdh_prev:
                score += 0.5
                reasons.append("✅ MACD-H反転下落")
            if ctx.stoch_k < ctx.stoch_d:
                score += 0.5
                reasons.append("✅ Stoch DC")
            if ctx.stoch_k < _prev_stoch_k:
                score += 0.3
            tp = ctx.entry - ctx.atr7 * (self.tp_mult_high if score >= 4.0 else self.tp_mult_low)
            sl = ctx.entry + ctx.atr7 * self.sl_mult

        if signal is None:
            return None

        conf = int(min(80, 45 + score * 4))
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)
