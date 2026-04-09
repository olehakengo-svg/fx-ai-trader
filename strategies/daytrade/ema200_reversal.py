"""EMA200 Trend Reversal — EMA200ブレイク後リテスト反発"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class Ema200TrendReversal(StrategyBase):
    name = "ema200_trend_reversal"
    mode = "daytrade"
    enabled = True   # v7.0: Sentinel再有効化 — デモデータ蓄積で再検証

    # チューナブルパラメータ
    ema200_dist_max = 0.5  # ATR倍率
    cross_window = 5       # クロス検出ウィンドウ

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if ctx.df is None or len(ctx.df) < 20:
            return None

        signal = None
        score = 0.0
        reasons = []

        bull200 = ctx.ema9 > ctx.ema200 and ctx.ema21 > ctx.ema200
        _ema200_dist = (ctx.entry - ctx.ema200) / max(ctx.atr, 1e-8)

        # EMA200上昇チェック
        _ema200_rising = True
        if len(ctx.df) > 5 and "ema200" in ctx.df.columns:
            _ema200_rising = ctx.ema200 > float(ctx.df["ema200"].iloc[-3])

        # EMA200クロス検出
        _crosses = 0
        if len(ctx.df) > 2 and "ema200" in ctx.df.columns:
            for _ec in range(2, min(self.cross_window + 1, len(ctx.df))):
                _prev_c = float(ctx.df["Close"].iloc[-_ec - 1])
                _prev_e200 = float(ctx.df["ema200"].iloc[-_ec - 1])
                _curr_c = float(ctx.df["Close"].iloc[-_ec])
                _curr_e200 = float(ctx.df["ema200"].iloc[-_ec])
                if ((_prev_c < _prev_e200 and _curr_c > _curr_e200) or
                        (_prev_c > _prev_e200 and _curr_c < _curr_e200)):
                    _crosses += 1

        if _crosses < 1 or abs(_ema200_dist) >= self.ema200_dist_max:
            return None

        # BUY: 上抜けリテスト
        if (bull200 and 0 < _ema200_dist < self.ema200_dist_max
                and ctx.macdh > ctx.macdh_prev and ctx.rsi < 55):
            signal = "BUY"
            score = 3.5
            reasons.append(f"✅ EMA200上抜けリテスト({ctx.ema200:.3f}, dist={_ema200_dist:.2f}ATR)")
            if _ema200_rising:
                score += 0.5
                reasons.append("✅ EMA200上昇中: トレンド転換確認")
            tp = ctx.entry + ctx.atr7 * 2.0
            sl = ctx.entry - ctx.atr7 * 1.0

        # SELL: 下抜けリテスト
        elif (not bull200 and -self.ema200_dist_max < _ema200_dist < 0
                and ctx.macdh < ctx.macdh_prev and ctx.rsi > 45):
            signal = "SELL"
            score = 3.5
            reasons.append(f"✅ EMA200下抜けリテスト({ctx.ema200:.3f}, dist={_ema200_dist:.2f}ATR)")
            if not _ema200_rising:
                score += 0.5
                reasons.append("✅ EMA200下降中: トレンド転換確認")
            tp = ctx.entry - ctx.atr7 * 2.0
            sl = ctx.entry + ctx.atr7 * 1.0

        if signal is None:
            return None

        conf = int(min(75, 40 + score * 4))
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)
