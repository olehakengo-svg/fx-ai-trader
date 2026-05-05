"""Engulfing at BB Band — 包み足パターン at BB極端"""
import os
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class EngulfingBB(StrategyBase):
    name = "engulfing_bb"
    mode = "scalp"
    enabled = True   # v7.0: Sentinel再有効化 — デモデータ蓄積で再検証

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
        if os.environ.get("ENGULFING_BB_REDESIGN_V2") == "1":
            return self._evaluate_redesign_v2(ctx)

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

    def _evaluate_redesign_v2(self, ctx: SignalContext) -> Optional[Candidate]:
        """Closed-bar signal variant for shadow-first V2 redesign.

        Signal geometry is evaluated on the completed signal bar (df[-2])
        against df[-3]. Entry remains the dispatcher/backtest execution price.
        """
        if ctx.is_friday:
            return None
        if ctx.df is None or len(ctx.df) < 3:
            return None

        signal_bar = ctx.df.iloc[-2]
        prev_bar = ctx.df.iloc[-3]

        sig_open = float(signal_bar["Open"])
        sig_close = float(signal_bar["Close"])
        sig_high = float(signal_bar["High"])
        sig_low = float(signal_bar["Low"])
        prev_open = float(prev_bar["Open"])
        prev_close = float(prev_bar["Close"])

        prev_body = abs(prev_close - prev_open)
        sig_body = abs(sig_close - sig_open)
        sig_range = sig_high - sig_low
        if prev_body <= 0:
            return None

        atr7 = float(signal_bar.get("atr7", signal_bar.get("atr", ctx.atr7 or ctx.atr)))
        if atr7 <= 0:
            return None

        bbpb = float(signal_bar.get("bb_pband", ctx.bbpb))
        rsi5 = float(signal_bar.get("rsi5", signal_bar.get("rsi", ctx.rsi5)))
        stoch_k = float(signal_bar.get("stoch_k", ctx.stoch_k))
        stoch_d = float(signal_bar.get("stoch_d", ctx.stoch_d))

        is_bullish = (
            prev_close < prev_open
            and sig_close > sig_open
            and sig_body > prev_body * self.body_mult
            and sig_close > prev_open
            and sig_range > atr7 * self.min_range_mult
        )
        is_bearish = (
            prev_close > prev_open
            and sig_close < sig_open
            and sig_body > prev_body * self.body_mult
            and sig_close < prev_open
            and sig_range > atr7 * self.min_range_mult
        )

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0

        if is_bullish and bbpb < self.bbpb_buy and rsi5 < self.rsi5_buy:
            signal = "BUY"
            score = 4.0
            reasons.append(f"✅ ENGULFING_BB_REDESIGN_V2 closed-bar bullish engulfing(body {sig_body/prev_body:.1f}x)")
            reasons.append(f"✅ closed-bar BB lower extreme(%B={bbpb:.2f}<{self.bbpb_buy})")
            reasons.append(f"✅ closed-bar RSI5 oversold({rsi5:.1f}<{self.rsi5_buy})")
            if stoch_k > stoch_d:
                score += 0.5
                reasons.append("✅ closed-bar Stoch K>D")
            tp = ctx.entry + atr7 * self.tp_mult
            sl = min(sig_low, ctx.entry - atr7 * self.sl_mult) - atr7 * self.sl_offset
        elif is_bearish and bbpb > self.bbpb_sell and rsi5 > self.rsi5_sell:
            signal = "SELL"
            score = 4.0
            reasons.append(f"✅ ENGULFING_BB_REDESIGN_V2 closed-bar bearish engulfing(body {sig_body/prev_body:.1f}x)")
            reasons.append(f"✅ closed-bar BB upper extreme(%B={bbpb:.2f}>{self.bbpb_sell})")
            reasons.append(f"✅ closed-bar RSI5 overbought({rsi5:.1f}>{self.rsi5_sell})")
            if stoch_k < stoch_d:
                score += 0.5
                reasons.append("✅ closed-bar Stoch K<D")
            tp = ctx.entry - atr7 * self.tp_mult
            sl = max(sig_high, ctx.entry + atr7 * self.sl_mult) + atr7 * self.sl_offset

        if signal is None:
            return None

        conf = int(min(82, 48 + score * 4))
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)
