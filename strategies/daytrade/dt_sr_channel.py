"""DT SR/Channel Reversal — 15m足SR/チャネルバウンス"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class DtSrChannelReversal(StrategyBase):
    name = "dt_sr_channel_reversal"
    mode = "daytrade"

    # チューナブルパラメータ
    sr_proximity = 0.4  # ATR倍率

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if not ctx.sr_levels or ctx.df is None or len(ctx.df) < 20:
            return None

        signal = None
        score = 0.0
        reasons = []

        # チャネル検出
        try:
            from app import find_parallel_channel
            _ch = find_parallel_channel(ctx.df, window=5, lookback=min(100, len(ctx.df) - 1))
        except ImportError:
            _ch = None
        _ch_upper = float(_ch["upper"][-1]["value"]) if _ch else None
        _ch_lower = float(_ch["lower"][-1]["value"]) if _ch else None

        _sr_buy = [l for l in ctx.sr_levels if 0 < ctx.entry - l < ctx.atr * self.sr_proximity]
        _sr_sell = [l for l in ctx.sr_levels if 0 < l - ctx.entry < ctx.atr * self.sr_proximity]
        _at_ch_lower = _ch_lower and abs(ctx.entry - _ch_lower) < ctx.atr * self.sr_proximity
        _at_ch_upper = _ch_upper and abs(ctx.entry - _ch_upper) < ctx.atr * self.sr_proximity

        # BUY
        if (_sr_buy or _at_ch_lower) and ctx.rsi < 45 and ctx.macdh > ctx.macdh_prev:
            signal = "BUY"
            score = 3.2
            if _sr_buy:
                reasons.append(f"✅ DT SRサポート反発({max(_sr_buy):.3f})")
            if _at_ch_lower:
                score += 0.5
                reasons.append(f"✅ DT チャネル下限反発({_ch_lower:.3f})")
            if ctx.ema9 > ctx.ema21:
                score += 0.5
                reasons.append("✅ EMA順列確認")
            tp = ctx.entry + ctx.atr7 * 2.0
            sl = ctx.entry - ctx.atr7 * 1.0

        # SELL
        elif (_sr_sell or _at_ch_upper) and ctx.rsi > 55 and ctx.macdh < ctx.macdh_prev:
            signal = "SELL"
            score = 3.2
            if _sr_sell:
                reasons.append(f"✅ DT SRレジスタンス反発({min(_sr_sell):.3f})")
            if _at_ch_upper:
                score += 0.5
                reasons.append(f"✅ DT チャネル上限反発({_ch_upper:.3f})")
            if ctx.ema9 < ctx.ema21:
                score += 0.5
                reasons.append("✅ EMA逆順列確認")
            tp = ctx.entry - ctx.atr7 * 2.0
            sl = ctx.entry + ctx.atr7 * 1.0

        if signal is None:
            return None

        conf = int(min(75, 40 + score * 4))
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)
