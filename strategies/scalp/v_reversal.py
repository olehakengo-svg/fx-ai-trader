"""V-Reversal — 急落/急騰後の反転検出 (Cont 2001, Jegadeesh & Titman 1993)"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class VReversal(StrategyBase):
    name = "v_reversal"
    mode = "scalp"

    # チューナブルパラメータ
    min_drop_pip = 8.0     # 最低急落/急騰幅(pip)
    rsi_buy = 25           # RSI14閾値
    rsi_sell = 75
    bbpb_buy = 0.10
    bbpb_sell = 0.90
    stoch_buy = 15
    stoch_sell = 85
    body_ratio_min = 0.25  # 実体比率最低値
    tp_mult = 1.5
    sl_mult = 0.7

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if ctx.df is None or len(ctx.df) < 20:
            return None

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0

        # 直近10本の価格変動(pip)
        _lookback = min(10, len(ctx.df) - 1)
        _price_10 = float(ctx.df["Close"].iloc[-_lookback - 1])
        _drop = (_price_10 - ctx.entry) * 100    # 正=下落幅(pip)
        _surge = (ctx.entry - _price_10) * 100    # 正=上昇幅(pip)

        # RSIダイバージェンス検出(直近5本)
        _rsi_vals = [float(ctx.df.iloc[-j].get("rsi", 50)) for j in range(1, min(6, len(ctx.df)))]
        _price_vals = [float(ctx.df["Close"].iloc[-j]) for j in range(1, min(6, len(ctx.df)))]
        _rsi_min_idx = _rsi_vals.index(min(_rsi_vals)) if _rsi_vals else 0
        _price_min_idx = _price_vals.index(min(_price_vals)) if _price_vals else 0
        _rsi_max_idx = _rsi_vals.index(max(_rsi_vals)) if _rsi_vals else 0
        _price_max_idx = _price_vals.index(max(_price_vals)) if _price_vals else 0

        _prev_stoch = float(ctx.df.iloc[-2].get("stoch_k", 50)) if len(ctx.df) >= 2 else 50
        _prev_bbpb = float(ctx.df.iloc[-2].get("bb_pband", 0.5)) if len(ctx.df) >= 2 else 0.5

        # ボディ比率
        _high = float(ctx.df.iloc[-1]["High"])
        _low = float(ctx.df.iloc[-1]["Low"])
        _bar_range = _high - _low if _high > _low else 0.001
        _body_ratio = abs(ctx.entry - ctx.open_price) / _bar_range

        # V字底: BUY
        if (_drop >= self.min_drop_pip
                and ctx.rsi < self.rsi_buy
                and ctx.bbpb < self.bbpb_buy
                and ctx.stoch_k < self.stoch_buy
                and ctx.entry > ctx.open_price
                and _body_ratio >= self.body_ratio_min
                and ctx.stoch_k > _prev_stoch):
            signal = "BUY"
            score = 3.5
            reasons.append(f"✅ V字底検出: 直近{_lookback}本で-{_drop:.1f}pip急落 [Cont 2001]")
            reasons.append(f"✅ 3指標極端: RSI={ctx.rsi:.0f}<{self.rsi_buy}, BB%B={ctx.bbpb:.2f}<{self.bbpb_buy}, Stoch={ctx.stoch_k:.0f}<{self.stoch_buy}")
            reasons.append(f"✅ 陽線+Stoch回復確認(前={_prev_stoch:.0f}→{ctx.stoch_k:.0f})")
            # RSI Bullish Divergence
            if (_price_min_idx < _rsi_min_idx and len(_rsi_vals) >= 3
                    and _rsi_vals[0] > min(_rsi_vals)):
                score += 1.5
                reasons.append("✅ RSI Bullish Divergence: 価格新安値 vs RSI底上げ [Jegadeesh 1993]")
            if ctx.bbpb > _prev_bbpb:
                score += 0.5
                reasons.append(f"✅ BB%B回復({_prev_bbpb:.2f}→{ctx.bbpb:.2f})")
            if ctx.macdh > ctx.macdh_prev:
                score += 0.5
                reasons.append("✅ MACD-H反転上昇")
            tp = ctx.entry + ctx.atr7 * self.tp_mult
            _recent_low = float(ctx.df["Low"].iloc[-3:].min())
            sl = min(ctx.entry - ctx.atr7 * self.sl_mult, _recent_low - 0.002)

        # V字天井: SELL
        elif (_surge >= self.min_drop_pip
                and ctx.rsi > self.rsi_sell
                and ctx.bbpb > self.bbpb_sell
                and ctx.stoch_k > self.stoch_sell
                and ctx.entry < ctx.open_price
                and _body_ratio >= self.body_ratio_min
                and ctx.stoch_k < _prev_stoch):
            signal = "SELL"
            score = 3.5
            reasons.append(f"✅ V字天井検出: 直近{_lookback}本で+{_surge:.1f}pip急騰 [Cont 2001]")
            reasons.append(f"✅ 3指標極端: RSI={ctx.rsi:.0f}>{self.rsi_sell}, BB%B={ctx.bbpb:.2f}>{self.bbpb_sell}, Stoch={ctx.stoch_k:.0f}>{self.stoch_sell}")
            reasons.append(f"✅ 陰線+Stoch反落確認(前={_prev_stoch:.0f}→{ctx.stoch_k:.0f})")
            # RSI Bearish Divergence
            if (_price_max_idx < _rsi_max_idx and len(_rsi_vals) >= 3
                    and _rsi_vals[0] < max(_rsi_vals)):
                score += 1.5
                reasons.append("✅ RSI Bearish Divergence: 価格新高値 vs RSI天井下げ")
            if ctx.bbpb < _prev_bbpb:
                score += 0.5
                reasons.append(f"✅ BB%B反落({_prev_bbpb:.2f}→{ctx.bbpb:.2f})")
            if ctx.macdh < ctx.macdh_prev:
                score += 0.5
                reasons.append("✅ MACD-H反転下落")
            tp = ctx.entry - ctx.atr7 * self.tp_mult
            _recent_high = float(ctx.df["High"].iloc[-3:].max())
            sl = max(ctx.entry + ctx.atr7 * self.sl_mult, _recent_high + 0.002)

        if signal is None:
            return None

        conf = int(min(85, 50 + score * 5))
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)
