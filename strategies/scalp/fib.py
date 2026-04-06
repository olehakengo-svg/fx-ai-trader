"""Fibonacci Reversal — フィボナッチリトレースメント反発"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


def _calc_fibonacci_levels(df, lookback=60):
    """フィボナッチリトレースメントレベルを計算。
    df の直近 lookback バーから高値/安値を特定し、
    38.2%, 50%, 61.8% のリトレースメントレベルを返す。
    """
    if df is None or len(df) < lookback:
        return None
    _sub = df.iloc[-lookback:]
    _high = float(_sub["High"].max())
    _low = float(_sub["Low"].min())
    _high_idx = _sub["High"].idxmax()
    _low_idx = _sub["Low"].idxmin()

    if _high == _low:
        return None

    # トレンド方向: 高値が後なら上昇、低値が後なら下降
    if _high_idx > _low_idx:
        trend = "up"
        diff = _high - _low
        r382 = _high - diff * 0.382
        r500 = _high - diff * 0.500
        r618 = _high - diff * 0.618
    else:
        trend = "down"
        diff = _high - _low
        r382 = _low + diff * 0.382
        r500 = _low + diff * 0.500
        r618 = _low + diff * 0.618

    return {"trend": trend, "high": _high, "low": _low,
            "r382": r382, "r500": r500, "r618": r618}


class FibReversal(StrategyBase):
    name = "fib_reversal"
    mode = "scalp"

    # チューナブルパラメータ
    min_lookback = 45
    lookbacks = [45, 60]
    fib_proximity = 0.50   # ATR倍率での近接判定（0.35→0.50緩和）
    rsi5_buy = 48          # （45→48緩和）
    rsi5_sell = 52         # （55→52緩和）
    tp_mult = 1.8
    sl_mult = 0.5
    sl_fib_offset = 0.2    # フィボレベルからのSLオフセット（ATR倍率）

    # ── ペア別無効化 (BT検証 2026-04-06) ──
    # EUR/GBP: 53t WR=43.4% EV=-0.719 → ペア全体PnLを毀損
    _disabled_symbols = frozenset({"EURGBP"})

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── ペアフィルター: BT負EVペアは発火停止 ──
        _sym_clean = ctx.symbol.upper().replace("=X", "").replace("_", "")
        if _sym_clean in self._disabled_symbols:
            return None

        if ctx.df is None or len(ctx.df) < self.min_lookback:
            return None

        # 複数lookbackでフィボ検出
        _fib = None
        _lookbacks = self.lookbacks if len(ctx.df) >= max(self.lookbacks) else [self.min_lookback]
        for lb in _lookbacks:
            if len(ctx.df) < lb:
                continue
            _fib_try = _calc_fibonacci_levels(ctx.df, lookback=lb)
            if _fib_try and _fib_try.get("trend"):
                _fib = _fib_try
                break

        if not _fib or not _fib.get("trend"):
            return None

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0

        _fib_trend = _fib["trend"]
        _fib_levels = {
            "38.2%": _fib.get("r382", 0),
            "50.0%": _fib.get("r500", 0),
            "61.8%": _fib.get("r618", 0),
        }

        # 各フィボレベルとの近接チェック
        _fib_touch = None
        for _fib_name, _fib_val in _fib_levels.items():
            if _fib_val and abs(ctx.entry - _fib_val) < ctx.atr * self.fib_proximity:
                _fib_touch = (_fib_name, _fib_val)
                break

        if not _fib_touch:
            return None

        _fn, _fv = _fib_touch
        _fib_dist = abs(ctx.entry - _fv) / ctx.atr if ctx.atr > 0 else 0

        # 上昇トレンドの押し目買い
        if _fib_trend == "up" and ctx.rsi5 < self.rsi5_buy and ctx.stoch_k > ctx.stoch_d:
            signal = "BUY"
            score = 3.5
            reasons.append(f"✅ Fib {_fn}サポート({_fv:.3f}, dist={_fib_dist:.2f}ATR)")
            if _fn == "61.8%":
                score += 0.8
                reasons.append("✅ Fib61.8%: 最高確率リバーサルゾーン")
            elif _fn == "50.0%":
                score += 0.5
            if ctx.rsi5 < 35:
                score += 0.5
            if ctx.entry > ctx.open_price:
                score += 0.3
                reasons.append("✅ 陽線確認")
            if ctx.macdh > ctx.macdh_prev:
                score += 0.4
                reasons.append("✅ MACD-H反転上昇")
            tp = ctx.entry + ctx.atr7 * self.tp_mult
            sl = min(ctx.entry - ctx.atr7 * self.sl_mult, _fv - ctx.atr7 * self.sl_fib_offset)

        # 下降トレンドの戻り売り
        elif _fib_trend == "down" and ctx.rsi5 > self.rsi5_sell and ctx.stoch_k < ctx.stoch_d:
            signal = "SELL"
            score = 3.5
            reasons.append(f"✅ Fib {_fn}レジスタンス({_fv:.3f}, dist={_fib_dist:.2f}ATR)")
            if _fn == "61.8%":
                score += 0.8
                reasons.append("✅ Fib61.8%: 最高確率リバーサルゾーン")
            elif _fn == "50.0%":
                score += 0.5
            if ctx.rsi5 > 65:
                score += 0.5
            if ctx.entry < ctx.open_price:
                score += 0.3
                reasons.append("✅ 陰線確認")
            if ctx.macdh < ctx.macdh_prev:
                score += 0.4
                reasons.append("✅ MACD-H反転下降")
            tp = ctx.entry - ctx.atr7 * self.tp_mult
            sl = max(ctx.entry + ctx.atr7 * self.sl_mult, _fv + ctx.atr7 * self.sl_fib_offset)

        if signal is None or score < 3.0:
            return None

        conf = int(min(85, 45 + score * 5))
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)
