"""MTF Reversal Confluence — 複数時間軸RSI+MACDクロス一致"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from modules.confidence_v2 import apply_penalty
from typing import Optional
import os


class MtfReversalConfluence(StrategyBase):
    name = "mtf_reversal_confluence"
    mode = "scalp"
    strategy_type = "MR"   # v11: Multi-TF reversal by construction

    # チューナブルパラメータ
    min_score = 3.2
    tp_mult = 1.5
    sl_mult = 0.5
    v2_tp_mult = 0.8
    v2_sl_mult = 1.2

    _dedup_state: dict = {}

    @classmethod
    def reset_dedup_state(cls):
        cls._dedup_state.clear()

    def _redesign_v2_enabled(self) -> bool:
        return os.environ.get("MTF_CONFLUENCE_REDESIGN_V2") == "1"

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        _v2 = self._redesign_v2_enabled()
        _entry = ctx.entry
        _atr7 = ctx.atr7
        _adx = ctx.adx
        _rsi5 = ctx.rsi5
        _stoch_k = ctx.stoch_k
        _stoch_d = ctx.stoch_d
        _macdh = ctx.macdh
        _macdh_prev = ctx.macdh_prev
        _bar_id = None

        if _v2:
            _signal_df = ctx.df
            if _signal_df is None or len(_signal_df) < 3:
                return None
            if not ctx.backtest_mode:
                _signal_df = _signal_df.iloc[:-1]
                if len(_signal_df) < 3:
                    return None

            _signal_row = _signal_df.iloc[-1]
            _signal_prev = _signal_df.iloc[-2]
            _rsi5 = float(_signal_row.get("rsi5", _signal_row.get("rsi", ctx.rsi5)))
            _stoch_k = float(_signal_row.get("stoch_k", ctx.stoch_k))
            _stoch_d = float(_signal_row.get("stoch_d", ctx.stoch_d))
            _macdh = float(_signal_row.get("macd_hist", ctx.macdh))
            _macdh_prev = float(_signal_prev.get("macd_hist", ctx.macdh_prev))
            _atr7 = float(_signal_row.get("atr7", _signal_row.get("atr", ctx.atr7)))
            _adx = float(_signal_row.get("adx", ctx.adx))
            _bar_id = ctx.bar_time if ctx.backtest_mode and ctx.bar_time is not None else _signal_df.index[-1]

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0

        # HTFからRSI/MACDを取得
        _htf_h1 = ctx.htf.get("h1", {})
        _htf_h4 = ctx.htf.get("h4", {})
        _htf_h1_rsi = _htf_h1.get("rsi", 50)
        _htf_h4_rsi = _htf_h4.get("rsi", 50)
        _htf_h1_score = _htf_h1.get("score", 0)

        # BUY: 複数時間軸でoversold + MACD反転
        # OR→AND修正: ORでは条件が甘すぎ（macdh>0だけで発火）
        _mtf_buy_rsi = (_rsi5 < 45 and _htf_h1_rsi < 48) or (_rsi5 < 40 and _htf_h4_rsi < 52)
        _mtf_buy_macd = _macdh > 0 and _macdh > _macdh_prev  # OR→AND: 両方成立を要求
        _mtf_buy_stoch = _stoch_k > _stoch_d and _stoch_k < 45

        if _mtf_buy_rsi and _mtf_buy_macd and _mtf_buy_stoch:
            signal = "BUY"
            score = 3.2
            # RSI一致ボーナス
            if _rsi5 < 35 and _htf_h1_rsi < 40:
                score += 0.8
                reasons.append(f"✅ MTF RSI一致 (1m={_rsi5:.0f}, 1H={_htf_h1_rsi:.0f})")
            else:
                score += 0.4
                reasons.append(f"✅ MTF RSI oversold (1m={_rsi5:.0f}, 1H={_htf_h1_rsi:.0f})")
            # 4H RSIも一致
            if _htf_h4_rsi < 45:
                score += 0.5
                reasons.append(f"✅ 4H RSI一致({_htf_h4_rsi:.0f})")
            # HTF MACDクロス一致
            if _htf_h1_score > 0:
                score += 0.5
                reasons.append("✅ 1H MACDブルクロス一致")
            reasons.append(f"✅ MACD-H反転({_macdh:.5f})")
            reasons.append(f"✅ Stoch反転({_stoch_k:.0f}>{_stoch_d:.0f})")
            if _v2:
                reasons.append("✅ redesign_v2 MR geometry: TP=0.8ATR / SL=1.2ATR")
            tp = _entry + _atr7 * (self.v2_tp_mult if _v2 else self.tp_mult)
            sl = _entry - _atr7 * (self.v2_sl_mult if _v2 else self.sl_mult)

        # SELL: 複数時間軸でoverbought + MACD反転
        _mtf_sell_rsi = (_rsi5 > 55 and _htf_h1_rsi > 52) or (_rsi5 > 60 and _htf_h4_rsi > 48)
        _mtf_sell_macd = _macdh < 0 and _macdh < _macdh_prev  # OR→AND: 両方成立を要求
        _mtf_sell_stoch = _stoch_k < _stoch_d and _stoch_k > 55

        if signal is None and _mtf_sell_rsi and _mtf_sell_macd and _mtf_sell_stoch:
            signal = "SELL"
            score = 3.2
            if _rsi5 > 65 and _htf_h1_rsi > 60:
                score += 0.8
                reasons.append(f"✅ MTF RSI一致 (1m={_rsi5:.0f}, 1H={_htf_h1_rsi:.0f})")
            else:
                score += 0.4
                reasons.append(f"✅ MTF RSI overbought (1m={_rsi5:.0f}, 1H={_htf_h1_rsi:.0f})")
            if _htf_h4_rsi > 55:
                score += 0.5
                reasons.append(f"✅ 4H RSI一致({_htf_h4_rsi:.0f})")
            if _htf_h1_score < 0:
                score += 0.5
                reasons.append("✅ 1H MACDベアクロス一致")
            reasons.append(f"✅ MACD-H反転({_macdh:.5f})")
            reasons.append(f"✅ Stoch反転({_stoch_k:.0f}<{_stoch_d:.0f})")
            if _v2:
                reasons.append("✅ redesign_v2 MR geometry: TP=0.8ATR / SL=1.2ATR")
            tp = _entry - _atr7 * (self.v2_tp_mult if _v2 else self.tp_mult)
            sl = _entry + _atr7 * (self.v2_sl_mult if _v2 else self.sl_mult)

        if signal is None or score < self.min_score:
            return None

        if _v2 and _bar_id is not None:
            _dedup_key = (ctx.symbol, self.name, _bar_id, signal)
            if self._dedup_state.get(_dedup_key):
                return None

        _legacy_conf = int(min(80, 40 + score * 5))
        conf = apply_penalty(_legacy_conf, self.strategy_type, _adx, conf_max=80)
        if _v2 and _bar_id is not None:
            self._dedup_state[(ctx.symbol, self.name, _bar_id, signal)] = True
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)
