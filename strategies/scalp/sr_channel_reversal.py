"""SR/Channel Bounce Reversal — 水平線・並行チャネル反発 (Osler 2000)"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from modules.confidence_v2 import apply_penalty
from typing import Optional


class SrChannelReversal(StrategyBase):
    name = "sr_channel_reversal"
    mode = "scalp"
    enabled = True   # v7.0: Sentinel再有効化 — デモデータ蓄積で検証
    strategy_type = "MR"   # v11: S/R bounce = MR by construction

    # チューナブルパラメータ
    sr_proximity = 0.3    # ATR倍率
    rsi5_buy = 45
    rsi5_sell = 55
    tp_mult = 1.5
    sl_mult = 0.5
    sl_sr_offset = 0.15  # ATR倍率
    min_score = 3.0

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if ctx.is_friday:
            return None
        if not ctx.sr_levels or ctx.df is None or len(ctx.df) < 10:
            return None

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0

        # 並行チャネル検出（app.pyのfind_parallel_channelを使用）
        try:
            from app import find_parallel_channel
            _channel = find_parallel_channel(ctx.df, window=5, lookback=min(100, len(ctx.df) - 1))
        except ImportError:
            _channel = None
        _ch_upper = float(_channel["upper"][-1]["value"]) if _channel else None
        _ch_lower = float(_channel["lower"][-1]["value"]) if _channel else None

        # SR近接判定
        _sr_buy = [l for l in ctx.sr_levels if 0 < ctx.entry - l < ctx.atr * self.sr_proximity]
        _sr_sell = [l for l in ctx.sr_levels if 0 < l - ctx.entry < ctx.atr * self.sr_proximity]
        _at_ch_lower = _ch_lower and abs(ctx.entry - _ch_lower) < ctx.atr * self.sr_proximity
        _at_ch_upper = _ch_upper and abs(ctx.entry - _ch_upper) < ctx.atr * self.sr_proximity

        # BUY
        if (_sr_buy or _at_ch_lower) and ctx.rsi5 < self.rsi5_buy and ctx.stoch_k > ctx.stoch_d:
            score = 3.0
            signal = "BUY"
            if _sr_buy:
                _nearest = max(_sr_buy)
                _dist = abs(ctx.entry - _nearest) / ctx.atr
                score += max(0, (0.3 - _dist) * 3.0)
                reasons.append(f"✅ SRサポート反発({_nearest:.3f}, dist={_dist:.2f}ATR)")
            if _at_ch_lower:
                score += 0.8
                reasons.append(f"✅ チャネル下限反発({_ch_lower:.3f})")
            if ctx.rsi5 < 35:
                score += 0.5
                reasons.append(f"✅ RSI5過売({ctx.rsi5:.0f})")
            if ctx.stoch_k < 30 and ctx.stoch_k > ctx.stoch_d:
                score += 0.5
                reasons.append(f"✅ Stoch反転上昇({ctx.stoch_k:.0f}>{ctx.stoch_d:.0f})")
            if ctx.macdh > 0 or ctx.macdh > ctx.macdh_prev:
                score += 0.4
                reasons.append("✅ MACD-H反転上昇")
            if ctx.entry > ctx.open_price:
                score += 0.3
            tp = ctx.entry + ctx.atr7 * self.tp_mult
            _nearest_sup = max(_sr_buy) if _sr_buy else (_ch_lower if _ch_lower else ctx.entry - ctx.atr7 * self.sl_mult)
            sl = min(ctx.entry - ctx.atr7 * self.sl_mult, _nearest_sup - ctx.atr7 * self.sl_sr_offset)

        # SELL
        elif (_sr_sell or _at_ch_upper) and ctx.rsi5 > self.rsi5_sell and ctx.stoch_k < ctx.stoch_d:
            score = 3.0
            signal = "SELL"
            if _sr_sell:
                _nearest = min(_sr_sell)
                _dist = abs(_nearest - ctx.entry) / ctx.atr
                score += max(0, (0.3 - _dist) * 3.0)
                reasons.append(f"✅ SRレジスタンス反発({_nearest:.3f}, dist={_dist:.2f}ATR)")
            if _at_ch_upper:
                score += 0.8
                reasons.append(f"✅ チャネル上限反発({_ch_upper:.3f})")
            if ctx.rsi5 > 65:
                score += 0.5
                reasons.append(f"✅ RSI5過買({ctx.rsi5:.0f})")
            if ctx.stoch_k > 70 and ctx.stoch_k < ctx.stoch_d:
                score += 0.5
                reasons.append(f"✅ Stoch反転下降({ctx.stoch_k:.0f}<{ctx.stoch_d:.0f})")
            if ctx.macdh < 0 or ctx.macdh < ctx.macdh_prev:
                score += 0.4
                reasons.append("✅ MACD-H反転下降")
            if ctx.entry < ctx.open_price:
                score += 0.3
            tp = ctx.entry - ctx.atr7 * self.tp_mult
            _nearest_res = min(_sr_sell) if _sr_sell else (_ch_upper if _ch_upper else ctx.entry + ctx.atr7 * self.sl_mult)
            sl = max(ctx.entry + ctx.atr7 * self.sl_mult, _nearest_res + ctx.atr7 * self.sl_sr_offset)

        if signal is None or score < self.min_score:
            return None

        _legacy_conf = int(min(85, 45 + score * 5))
        conf = apply_penalty(_legacy_conf, self.strategy_type, ctx.adx, conf_max=85)
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)
