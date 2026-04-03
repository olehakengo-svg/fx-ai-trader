"""London Breakout — セッション開始ブレイクアウト (Ito & Hashimoto 2006)"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class LondonBreakout(StrategyBase):
    name = "london_breakout"
    mode = "scalp"

    # チューナブルパラメータ
    hour_start = 7
    hour_end = 10          # （9→10緩和、3時間ウィンドウ）
    asia_bars = 120        # アジアセッンレンジ（直近120バー=2時間分1m足）
    asia_range_min = 0.5   # ATR倍率
    asia_range_max = 4.0   # ATR倍率
    breakout_offset = 0.1  # ATR倍率
    tp_asia_mult = 1.5     # アジアレンジ倍率
    tp_atr_mult = 2.0      # ATR倍率（最低TP）
    sl_offset = 0.3        # ATR倍率
    vol_mult = 1.3         # ボリューム倍率閾値

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if not (self.hour_start <= ctx.hour_utc <= self.hour_end):
            return None
        if ctx.df is None or len(ctx.df) < self.asia_bars:
            return None

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0

        # アジアセッションレンジ計算
        _asia = ctx.df.iloc[-self.asia_bars:]
        _asia_high = float(_asia["High"].max())
        _asia_low = float(_asia["Low"].min())
        _asia_range = _asia_high - _asia_low

        if _asia_range <= ctx.atr7 * self.asia_range_min or _asia_range >= ctx.atr7 * self.asia_range_max:
            return None

        # ブレイクアウト検出
        if ctx.entry > _asia_high + ctx.atr7 * self.breakout_offset and ctx.ema9 > ctx.ema21:
            signal = "BUY"
            score = 4.0
            reasons.append(f"✅ ロンドンブレイクアウト: アジア高値{_asia_high:.3f}突破 (Ito 2006)")
            reasons.append(f"✅ EMA順列確認 (9={ctx.ema9:.3f}>21={ctx.ema21:.3f})")
            tp = ctx.entry + max(_asia_range * self.tp_asia_mult, ctx.atr7 * self.tp_atr_mult)
            sl = _asia_high - ctx.atr7 * self.sl_offset
        elif ctx.entry < _asia_low - ctx.atr7 * self.breakout_offset and ctx.ema9 < ctx.ema21:
            signal = "SELL"
            score = 4.0
            reasons.append(f"✅ ロンドンブレイクアウト: アジア安値{_asia_low:.3f}下抜け (Ito 2006)")
            reasons.append(f"✅ EMA逆順列確認 (9={ctx.ema9:.3f}<21={ctx.ema21:.3f})")
            tp = ctx.entry - max(_asia_range * self.tp_asia_mult, ctx.atr7 * self.tp_atr_mult)
            sl = _asia_low + ctx.atr7 * self.sl_offset

        if signal is None:
            return None

        if ctx.adx > 18:
            score += 0.5
            reasons.append(f"✅ ADXモメンタム({ctx.adx:.1f}>18)")
        # ボリューム確認（ボーナスのみ）
        if ctx.df is not None and "Volume" in ctx.df.columns:
            _vol = float(ctx.df.iloc[-1]["Volume"])
            _vol_avg = float(ctx.df["Volume"].iloc[-60:].mean()) if len(ctx.df) >= 60 else _vol
            if _vol > _vol_avg * self.vol_mult:
                score += 0.8
                reasons.append("✅ 出来高急増（ロンドン参入）")

        conf = int(min(85, 50 + score * 4))
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)
