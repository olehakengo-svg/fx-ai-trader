"""BB Squeeze Breakout — 圧縮→拡大ブレイクアウト (BLL 1992 JoF)"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class BBSqueezeBreakout(StrategyBase):
    name = "bb_squeeze_breakout"
    mode = "scalp"

    # チューナブルパラメータ（緩和済み）
    bb_width_pct_max = 0.10  # BB幅パーセンタイル閾値（5→10%緩和）
    adx_min = 15             # ADXトレンド確認（20→15緩和）
    vol_mult = 1.2           # ボリューム倍率閾値
    tp_mult = 3.0
    sl_mult = 1.2

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if ctx.bb_width_pct >= self.bb_width_pct_max:
            return None
        if ctx.adx < self.adx_min:
            return None
        if ctx.df is None or len(ctx.df) < 2:
            return None

        signal = None
        score = 0.0
        reasons = []

        # スクイーズ中に方向を判定
        _prev_bb_width = float(ctx.df["bb_width"].iloc[-2]) if "bb_width" in ctx.df.columns else ctx.bb_width
        _bb_expanding = ctx.bb_width > _prev_bb_width

        if not _bb_expanding:
            return None

        # ボリューム確認（ボーナスに緩和、ブロックしない）
        _vol_bonus = False
        if "Volume" in ctx.df.columns:
            _vol = float(ctx.df.iloc[-1]["Volume"])
            _vol_avg = float(ctx.df["Volume"].iloc[-20:].mean()) if len(ctx.df) >= 20 else _vol
            _vol_bonus = _vol > _vol_avg * self.vol_mult

        # ブレイクアウト方向判定
        if ctx.bbpb > 0.75 and ctx.entry > ctx.ema9 and ctx.ema9 > ctx.ema21:
            signal = "BUY"
            score = 3.5
            reasons.append("✅ BBスクイーズブレイクアウト上抜け (BLL 1992 JoF)")
            reasons.append(f"✅ BB幅{ctx.bb_width_pct*100:.0f}%ile → 拡大開始")
            reasons.append("✅ EMA順列 (9>21) + 価格>EMA9")
            tp = ctx.entry + ctx.atr7 * self.tp_mult
            sl = ctx.entry - ctx.atr7 * self.sl_mult
        elif ctx.bbpb < 0.25 and ctx.entry < ctx.ema9 and ctx.ema9 < ctx.ema21:
            signal = "SELL"
            score = 3.5
            reasons.append("✅ BBスクイーズブレイクアウト下抜け (BLL 1992 JoF)")
            reasons.append(f"✅ BB幅{ctx.bb_width_pct*100:.0f}%ile → 拡大開始")
            reasons.append("✅ EMA逆順列 (9<21) + 価格<EMA9")
            tp = ctx.entry - ctx.atr7 * self.tp_mult
            sl = ctx.entry + ctx.atr7 * self.sl_mult

        if signal is None:
            return None

        if _vol_bonus:
            score += 0.5
            reasons.append("✅ 出来高急増")
        if ctx.adx > 20:
            score += 1.0
            reasons.append(f"✅ ADXトレンド確認({ctx.adx:.1f}>20)")

        conf = int(min(85, 50 + score * 4))
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)
