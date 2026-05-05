"""DT Fibonacci Reversal — 15m足フィボナッチリトレースメント反発"""
import os

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from strategies.scalp.fib import _calc_fibonacci_levels
from modules.round_number import shift_tp_inside, round_confluence_boost
from typing import Optional


class DtFibReversal(StrategyBase):
    name = "dt_fib_reversal"
    mode = "daytrade"
    enabled = True   # v7.0: Sentinel再有効化 — デモデータ蓄積で再検証
    strategy_type = "MR"   # v11: Q4 paradox fix — Fib reversal is MR by construction

    # チューナブルパラメータ
    lookback = 80
    fib_proximity = 0.3  # ATR倍率
    v2_sl_mult = 1.2
    v2_sl_fib_offset = 0.5

    _v2_seen_closed_bar_keys: set = set()

    @classmethod
    def reset_dedup_state(cls):
        cls._v2_seen_closed_bar_keys.clear()

    def _redesign_v2_enabled(self) -> bool:
        return os.environ.get("FIB_REDESIGN_V2") == "1"

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        _v2 = self._redesign_v2_enabled()
        if ctx.df is None or len(ctx.df) < self.lookback:
            return None

        _signal_df = ctx.df
        if _v2:
            if not ctx.backtest_mode and ctx.bar_time is None:
                return None
            if ctx.bar_time is not None:
                try:
                    _signal_df = ctx.df.loc[:ctx.bar_time]
                except Exception:
                    _signal_df = ctx.df
            if len(_signal_df) < self.lookback:
                return None

        _signal_row = _signal_df.iloc[-1]
        _prev_row = _signal_df.iloc[-2] if len(_signal_df) >= 2 else _signal_row
        _signal_entry = float(_signal_row["Close"]) if _v2 else ctx.entry
        _atr = float(_signal_row.get("atr", ctx.atr)) if _v2 else ctx.atr
        _atr7 = float(_signal_row.get("atr7", _atr)) if _v2 else ctx.atr7
        _rsi = float(_signal_row.get("rsi", ctx.rsi)) if _v2 else ctx.rsi
        _ema9 = float(_signal_row.get("ema9", ctx.ema9)) if _v2 else ctx.ema9
        _ema21 = float(_signal_row.get("ema21", ctx.ema21)) if _v2 else ctx.ema21
        _macdh = float(_signal_row.get("macd_hist", ctx.macdh)) if _v2 else ctx.macdh
        _macdh_prev = float(_prev_row.get("macd_hist", ctx.macdh_prev)) if _v2 else ctx.macdh_prev

        _fib = _calc_fibonacci_levels(_signal_df, lookback=self.lookback)
        if not _fib or not _fib.get("trend"):
            return None

        signal = None
        score = 0.0
        reasons = []

        _fib_levels = {
            "38.2%": _fib.get("r382", 0),
            "50.0%": _fib.get("r500", 0),
            "61.8%": _fib.get("r618", 0),
        }
        _fib_touch = None
        for _fn, _fv in _fib_levels.items():
            if _fv and abs(_signal_entry - _fv) < _atr * self.fib_proximity:
                _fib_touch = (_fn, _fv)
                break

        if not _fib_touch:
            return None

        _fn, _fv = _fib_touch

        # 上昇トレンド押し目買い
        if _fib["trend"] == "up" and _rsi < 45 and _macdh > _macdh_prev:
            signal = "BUY"
            score = 3.5
            reasons.append(f"✅ DT Fib {_fn}サポート反発({_fv:.3f})")
            if _fn == "61.8%":
                score += 0.8
                reasons.append("✅ Fib61.8%: 最高確率ゾーン")
            if _ema9 > _ema21:
                score += 0.5
                reasons.append("✅ EMA順列確認")
            tp = ctx.entry + _atr7 * 2.0
            if _v2:
                sl = min(
                    ctx.entry - _atr7 * self.v2_sl_mult,
                    _fv - _atr7 * self.v2_sl_fib_offset,
                )
            else:
                sl = ctx.entry - _atr7 * 1.0

        # 下降トレンド戻り売り
        elif _fib["trend"] == "down" and _rsi > 55 and _macdh < _macdh_prev:
            signal = "SELL"
            score = 3.5
            reasons.append(f"✅ DT Fib {_fn}レジスタンス反発({_fv:.3f})")
            if _fn == "61.8%":
                score += 0.8
                reasons.append("✅ Fib61.8%: 最高確率ゾーン")
            if _ema9 < _ema21:
                score += 0.5
                reasons.append("✅ EMA逆順列確認")
            tp = ctx.entry - _atr7 * 2.0
            if _v2:
                sl = max(
                    ctx.entry + _atr7 * self.v2_sl_mult,
                    _fv + _atr7 * self.v2_sl_fib_offset,
                )
            else:
                sl = ctx.entry + _atr7 * 1.0

        if signal is None:
            return None
        if _v2:
            try:
                _bar_id = ctx.bar_time or _signal_df.index[-1]
            except Exception:
                _bar_id = ctx.bar_time
            _dedup_key = (self.name, ctx.symbol, signal, _bar_id)
            if _dedup_key in self._v2_seen_closed_bar_keys:
                return None
            self._v2_seen_closed_bar_keys.add(_dedup_key)
            reasons.append(
                f"✅ FIB_REDESIGN_V2 closed-bar signal + wide SL({self.v2_sl_mult:.1f}ATR/Fib±{self.v2_sl_fib_offset:.1f}ATR)"
            )

        # RNR: TP shift away from round numbers (3pip 内側) + Fib×round confluence boost
        pip = 0.01 if "JPY" in ctx.symbol.upper() else 0.0001
        tp = shift_tp_inside(tp, signal, pip=pip, shift_pips=3.0)
        rn_boost = round_confluence_boost(_fv, pip=pip, threshold_pips=3.0)
        if rn_boost > 0:
            score += 0.3 * rn_boost
            reasons.append(f"✅ Fib×Round confluence (boost={0.3*rn_boost:.2f})")

        # v11: Confidence v2 — MR anti-trend penalty (ADX>25 reduces conf)
        from modules.confidence_v2 import apply_penalty
        _legacy_conf = int(min(80, 45 + score * 4))
        conf = apply_penalty(_legacy_conf, self.strategy_type, ctx.adx, conf_max=80)
        if conf != _legacy_conf:
            reasons.append(
                f"🔧 [v2] MR anti-trend: ADX={ctx.adx:.1f}>25 → conf {_legacy_conf}→{conf}"
            )
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)
