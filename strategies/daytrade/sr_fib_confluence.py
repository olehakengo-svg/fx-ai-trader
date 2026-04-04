"""SR + Fibonacci Confluence — SR/Fibコンフルエンス (15m足)"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class SrFibConfluence(StrategyBase):
    name = "sr_fib_confluence"
    mode = "daytrade"

    # チューナブルパラメータ
    adx_min = 20           # ADXトレンド閾値（12→20: 学術水準復元）
    ema_score_threshold = 0.28

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if ctx.adx < self.adx_min:
            return None

        signal = None
        score = 0.0
        reasons = []

        # SR/Fib情報: DT関数の蓄積reasonsまたはlayer3から取得
        _all_reasons = ctx.layer3.get("dt_reasons", ctx.layer3.get("reasons", []))
        _has_sr_fib = any("Fib" in r or "フィボ" in r for r in _all_reasons)
        _has_ob = any("OB" in r or "オーダーブロック" in r for r in _all_reasons)

        if not _has_sr_fib and not _has_ob:
            return None

        # EMAスコア: DT関数から渡される複合スコア
        ema_score = ctx.ema_score if ctx.ema_score != 0.0 else (ctx.ema9 - ctx.ema21) / max(ctx.atr, 1e-8)

        if ema_score > self.ema_score_threshold and ctx.ema9 > ctx.ema21:
            signal = "BUY"
            score = 3.0 + abs(ema_score) * 2
            reasons.append("✅ SR/Fibコンフルエンス + EMA順列確認")
            reasons.extend([r for r in _all_reasons if "✅" in r][:3])
            tp = ctx.entry + ctx.atr7 * 2.0
            sl = ctx.entry - ctx.atr7 * 1.0
        elif ema_score < -self.ema_score_threshold and ctx.ema9 < ctx.ema21:
            signal = "SELL"
            score = 3.0 + abs(ema_score) * 2
            reasons.append("✅ SR/Fibコンフルエンス + EMA逆順列確認")
            reasons.extend([r for r in _all_reasons if "✅" in r][:3])
            tp = ctx.entry - ctx.atr7 * 2.0
            sl = ctx.entry + ctx.atr7 * 1.0

        if signal is None:
            return None

        _entry_type = "sr_fib_confluence" if _has_sr_fib else "ob_retest"
        conf = int(min(80, 45 + score * 4))
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=_entry_type, score=score)
