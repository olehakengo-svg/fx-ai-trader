"""Stochastic Trend Pullback — トレンド方向のStoch押し目/戻り"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from modules.confidence_v2 import apply_penalty
from typing import Optional
import os


class StochTrendPullback(StrategyBase):
    name = "stoch_trend_pullback"
    mode = "scalp"
    enabled = True   # 復帰 (2026-04-07): 本番13t WR=46.2% EV=+1.08 — 全scalp戦略中最良EV
    strategy_type = "pullback"   # v11: トレンド方向 Stoch pullback — ADX>31で conf penalty

    # チューナブルパラメータ（学術水準: ADX≥20でトレンド確認）
    adx_min = 20          # ADXトレンド閾値（12→20: 学術的に有意なトレンド水準）
    adx_weak = 25         # 弱トレンド帯（15→25: ADX20-25は弱トレンド）
    prev_stoch_buy = 48   # 前バーStoch売られすぎ閾値（42→48緩和）
    prev_stoch_sell = 52  # 前バーStoch買われすぎ閾値（58→52緩和）
    stoch_max_buy = 70    # Stoch上昇余地（65→70緩和）
    stoch_min_sell = 30   # Stoch下落余地（35→30緩和）
    tp_mult = 1.8
    sl_mult = 0.8
    _v2_dedup_state: set[tuple[str, str, str]] = set()

    @classmethod
    def reset_dedup_state(cls):
        cls._v2_dedup_state.clear()

    def _redesign_v2_enabled(self) -> bool:
        return os.environ.get("STOCH_PULLBACK_REDESIGN_V2") == "1"

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if ctx.adx < self.adx_min:
            return None
        if ctx.df is None or len(ctx.df) < 5:
            return None
        _redesign_v2 = self._redesign_v2_enabled()
        if _redesign_v2:
            if len(ctx.df) < 6:
                return None
            if not ctx.backtest_mode and ctx.bar_time is None:
                return None
            _signal_df = ctx.df.iloc[:-1]
            _signal_row = _signal_df.iloc[-1]
            _prev_row = _signal_df.iloc[-2]
            _signal_bar_time = getattr(_signal_row, "name", None)
            _entry = float(_signal_row["Close"])
            _ema9 = float(_signal_row.get("ema9", ctx.ema9))
            _ema21 = float(_signal_row.get("ema21", ctx.ema21))
            _atr7 = float(_signal_row.get("atr7", ctx.atr7))
            _stoch_k = float(_signal_row.get("stoch_k", ctx.stoch_k))
            _stoch_d = float(_signal_row.get("stoch_d", ctx.stoch_d))
            _rsi5 = float(_signal_row.get("rsi5", _signal_row.get("rsi", ctx.rsi5)))
            _bbpb = float(_signal_row.get("bb_pband", ctx.bbpb))
            _prev_stoch_k = float(_prev_row.get("stoch_k", 50.0))
        else:
            _signal_bar_time = None
            _entry = ctx.entry
            _ema9 = ctx.ema9
            _ema21 = ctx.ema21
            _atr7 = ctx.atr7
            _stoch_k = ctx.stoch_k
            _stoch_d = ctx.stoch_d
            _rsi5 = ctx.rsi5
            _bbpb = ctx.bbpb
            _prev_stoch_k = float(ctx.df.iloc[-2].get("stoch_k", 50)) if len(ctx.df) >= 2 else 50

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0

        # BUY: 上昇トレンド中のStoch売られすぎ回復
        if (_ema9 > _ema21 and _entry > _ema21
                and _stoch_k > _stoch_d
                and _prev_stoch_k < self.prev_stoch_buy
                and _stoch_k < self.stoch_max_buy
                and _rsi5 > 28 and _rsi5 < 62
                and _bbpb > 0.10 and _bbpb < 0.70):
            signal = "BUY"
            score = 3.2 + min((ctx.adx - self.adx_min) * 0.04, 0.8)
            reasons.append(f"✅ トレンドプルバック: Stoch売られすぎ回復(K={_stoch_k:.0f}, 前={_prev_stoch_k:.0f})")
            reasons.append(f"✅ 上昇トレンド確認 (EMA9>21, ADX={ctx.adx:.1f}≥{self.adx_min})")
            reasons.append(f"✅ Stochゴールデンクロス(K>D: {_stoch_k:.0f}>{_stoch_d:.0f})")
            tp = ctx.entry + _atr7 * self.tp_mult
            sl = ctx.entry - _atr7 * self.sl_mult

        # SELL: 下降トレンド中のStoch買われすぎ回復
        elif (_ema9 < _ema21 and _entry < _ema21
                and _stoch_k < _stoch_d
                and _prev_stoch_k > self.prev_stoch_sell
                and _stoch_k > self.stoch_min_sell
                and _rsi5 > 38 and _rsi5 < 72
                and _bbpb > 0.30 and _bbpb < 0.90):
            signal = "SELL"
            score = 3.2 + min((ctx.adx - self.adx_min) * 0.04, 0.8)
            reasons.append(f"✅ トレンドプルバック: Stoch買われすぎ回復(K={_stoch_k:.0f}, 前={_prev_stoch_k:.0f})")
            reasons.append(f"✅ 下降トレンド確認 (EMA9<21, ADX={ctx.adx:.1f}≥{self.adx_min})")
            reasons.append(f"✅ Stochデッドクロス(K<D: {_stoch_k:.0f}<{_stoch_d:.0f})")
            tp = ctx.entry - _atr7 * self.tp_mult
            sl = ctx.entry + _atr7 * self.sl_mult

        if signal is None:
            return None
        if _redesign_v2:
            if not ctx.backtest_mode:
                _sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
                _key = (_sym, signal, str(_signal_bar_time))
                if _key in self._v2_dedup_state:
                    return None
                self._v2_dedup_state.add(_key)
            reasons.append(
                "✅ STOCH_PULLBACK_REDESIGN_V2: signal_bar_time={} で確定し次バー約定".format(
                    _signal_bar_time
                )
            )

        conf = int(min(80, 45 + score * 4))
        # ADX弱トレンド帯はグラデーション減衰
        if ctx.adx < self.adx_weak:
            conf = int(conf * 0.9)
            reasons.append(f"⚠️ ADX弱トレンド帯({ctx.adx:.1f}<{self.adx_weak}) → conf×0.9")
        reasons.append(f"📊 レジーム: トレンド(ADX={ctx.adx:.1f}≥{self.adx_min})")
        # v11: ADX過剰帯 (pullback threshold=31) でもペナルティ
        conf = apply_penalty(conf, self.strategy_type, ctx.adx, conf_max=80)
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)
