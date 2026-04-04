"""EMA Cross Retest — リテスト確認型EMAクロス (15m足)"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class EmaCross(StrategyBase):
    name = "ema_cross"
    mode = "daytrade"

    # チューナブルパラメータ
    adx_min = 20           # ADXトレンド閾値（12→20: 学術水準、本番WR33%→改善）
    cross_window = 8       # クロス検出ウィンドウ（本数）
    pullback_min = 0.3     # ATR倍率
    ema_score_threshold = 0.30  # EMAスコア閾値
    rsi_buy_max = 70
    rsi_sell_min = 30

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if ctx.adx < self.adx_min:
            return None
        if ctx.df is None or len(ctx.df) < 10:
            return None

        signal = None
        score = 0.0
        reasons = []

        # EMAスコア: DT関数から渡される複合スコア、なければローカル計算
        ema_score = ctx.ema_score if ctx.ema_score != 0.0 else (ctx.ema9 - ctx.ema21) / max(ctx.atr, 1e-8)

        # (1) 直近N本以内にEMAクロスが発生したか
        _cross_dir = None
        _cross_bar = None
        for _cb in range(2, min(self.cross_window + 1, len(ctx.df))):
            _e9p = float(ctx.df["ema9"].iloc[-_cb - 1])
            _e21p = float(ctx.df["ema21"].iloc[-_cb - 1])
            _e9c = float(ctx.df["ema9"].iloc[-_cb])
            _e21c = float(ctx.df["ema21"].iloc[-_cb])
            if _e9p <= _e21p and _e9c > _e21c:
                _cross_dir = "BUY"
                _cross_bar = _cb
            elif _e9p >= _e21p and _e9c < _e21c:
                _cross_dir = "SELL"
                _cross_bar = _cb
                break

        if not _cross_dir or not _cross_bar:
            return None

        # (2) プルバック確認
        if _cross_dir == "BUY":
            _pb_low = min(float(ctx.df["Low"].iloc[-j]) for j in range(1, _cross_bar))
            _pullback_depth = (float(ctx.df["High"].iloc[-_cross_bar]) - _pb_low) / max(ctx.atr, 1e-8)
            _pullback_ok = _pullback_depth >= self.pullback_min and ctx.entry > ctx.ema21
        else:
            _pb_high = max(float(ctx.df["High"].iloc[-j]) for j in range(1, _cross_bar))
            _pullback_depth = (_pb_high - float(ctx.df["Low"].iloc[-_cross_bar])) / max(ctx.atr, 1e-8)
            _pullback_ok = _pullback_depth >= self.pullback_min and ctx.entry < ctx.ema21

        if not _pullback_ok:
            return None

        # (3) 方向再確認
        _candle_bull = ctx.entry > ctx.open_price
        _candle_bear = ctx.entry < ctx.open_price
        _rsi_ok_buy = ctx.rsi < self.rsi_buy_max
        _rsi_ok_sell = ctx.rsi > self.rsi_sell_min

        if (_cross_dir == "BUY" and ctx.ema9 > ctx.ema21 and _candle_bull
                and ctx.macdh > 0 and _rsi_ok_buy and ema_score > self.ema_score_threshold):
            signal = "BUY"
            score = 3.5 + min((ctx.adx - self.adx_min) * 0.03, 0.8)
            reasons.append(f"✅ EMAクロスリテスト: 9/21 GC {_cross_bar}本前, PB={_pullback_depth:.1f}ATR")
            reasons.append(f"✅ 5条件一致: ADX≥{self.adx_min}({ctx.adx:.0f}), MACD+, RSI({ctx.rsi:.0f}), 陽線, EMA維持")
            tp = ctx.entry + ctx.atr7 * 2.0
            sl = ctx.entry - ctx.atr7 * 1.0

        elif (_cross_dir == "SELL" and ctx.ema9 < ctx.ema21 and _candle_bear
                and ctx.macdh < 0 and _rsi_ok_sell and ema_score < -self.ema_score_threshold):
            signal = "SELL"
            score = 3.5 + min((ctx.adx - self.adx_min) * 0.03, 0.8)
            reasons.append(f"✅ EMAクロスリテスト: 9/21 DC {_cross_bar}本前, PB={_pullback_depth:.1f}ATR")
            reasons.append(f"✅ 5条件一致: ADX≥{self.adx_min}({ctx.adx:.0f}), MACD-, RSI({ctx.rsi:.0f}), 陰線, EMA維持")
            tp = ctx.entry - ctx.atr7 * 2.0
            sl = ctx.entry + ctx.atr7 * 1.0

        if signal is None:
            return None

        conf = int(min(80, 45 + score * 4))
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)
