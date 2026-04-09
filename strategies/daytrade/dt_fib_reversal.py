"""DT Fibonacci Reversal — 15m足フィボナッチリトレースメント反発"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from strategies.scalp.fib import _calc_fibonacci_levels
from typing import Optional


class DtFibReversal(StrategyBase):
    name = "dt_fib_reversal"
    mode = "daytrade"
    enabled = True   # v7.0: Sentinel再有効化 — デモデータ蓄積で再検証

    # チューナブルパラメータ
    lookback = 80
    fib_proximity = 0.3  # ATR倍率

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if ctx.df is None or len(ctx.df) < self.lookback:
            return None

        _fib = _calc_fibonacci_levels(ctx.df, lookback=self.lookback)
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
            if _fv and abs(ctx.entry - _fv) < ctx.atr * self.fib_proximity:
                _fib_touch = (_fn, _fv)
                break

        if not _fib_touch:
            return None

        _fn, _fv = _fib_touch

        # 上昇トレンド押し目買い
        if _fib["trend"] == "up" and ctx.rsi < 45 and ctx.macdh > ctx.macdh_prev:
            signal = "BUY"
            score = 3.5
            reasons.append(f"✅ DT Fib {_fn}サポート反発({_fv:.3f})")
            if _fn == "61.8%":
                score += 0.8
                reasons.append("✅ Fib61.8%: 最高確率ゾーン")
            if ctx.ema9 > ctx.ema21:
                score += 0.5
                reasons.append("✅ EMA順列確認")
            tp = ctx.entry + ctx.atr7 * 2.0
            sl = ctx.entry - ctx.atr7 * 1.0

        # 下降トレンド戻り売り
        elif _fib["trend"] == "down" and ctx.rsi > 55 and ctx.macdh < ctx.macdh_prev:
            signal = "SELL"
            score = 3.5
            reasons.append(f"✅ DT Fib {_fn}レジスタンス反発({_fv:.3f})")
            if _fn == "61.8%":
                score += 0.8
                reasons.append("✅ Fib61.8%: 最高確率ゾーン")
            if ctx.ema9 < ctx.ema21:
                score += 0.5
                reasons.append("✅ EMA逆順列確認")
            tp = ctx.entry - ctx.atr7 * 2.0
            sl = ctx.entry + ctx.atr7 * 1.0

        if signal is None:
            return None

        conf = int(min(80, 45 + score * 4))
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)
