"""
BB + RSI Mean Reversion — ペア別最適化 (Bollinger 2001 + Wilder 1978)

Option C 統合改修 (2026-04-04 USD/JPY解剖レポート):
  EUR/USD: ADX<25 レンジ環境限定（従来通り）
  USD/JPY: ADX制限撤廃 + Death Valleyブロック + Gold Hoursボーナス

データ裏付け (USD/JPY 15m, 59日間):
  - ADX<20  WR=49.2% (エッジなし)
  - ADX>=30 WR=60.0% avg=+3.45pip (トレンド中BB反発が最も有効)
  - Death Valley (UTC 00-01,09,12-16): BB reversion EV 強ネガティブ
  - Gold Hours (UTC 05-08,19-23): WR=60-85%, レンジ8-10pip→高速反転

EUR/USD比較:
  - ADX>=30 WR=49.3% (トレンド中エッジなし — 構造的差異)
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class BBRsiReversion(StrategyBase):
    name = "bb_rsi_reversion"
    mode = "scalp"

    # チューナブルパラメータ
    adx_max = 25          # EUR/USD用: レンジ判定上限（学術水準 ADX≥25はトレンド領域）
    bbpb_buy = 0.25       # BB%B BUY閾値
    bbpb_sell = 0.75      # BB%B SELL閾値
    rsi5_buy = 45         # RSI5 BUY閾値
    rsi5_sell = 55        # RSI5 SELL閾値
    stoch_buy = 45        # Stoch BUY閾値
    stoch_sell = 55       # Stoch SELL閾値
    tp_mult_tier1 = 2.0   # TP倍率 (Tier1)
    tp_mult_tier2 = 1.5   # TP倍率 (Tier2)

    # ── USD/JPY専用: Death Valley / Gold Hours (Option C) ──
    # 構造的理由: セッション流動性プロファイルに基づく環境最適化
    _death_valley_hours = frozenset({0, 1, 9, 12, 13, 14, 15, 16})
    _gold_hours = frozenset({5, 6, 7, 8, 19, 20, 21, 22, 23})

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── ペア別ADX / 時間帯フィルター (Option C) ──
        if ctx.is_jpy:
            # USD/JPY: Death Valley完全ブロック
            if ctx.hour_utc in self._death_valley_hours:
                return None
            # USD/JPY: ADX制限なし（トレンド中BB反発 WR=60% — 逆にエッジ増大）
        else:
            # EUR/USD: 従来通り ADX<25 レンジ環境のみ
            if ctx.adx >= self.adx_max:
                return None

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0

        _min_sl = 0.030 if ctx.is_jpy else 0.00030

        # ── BUY判定 ──
        if (ctx.bbpb <= self.bbpb_buy and ctx.rsi5 < self.rsi5_buy
                and ctx.stoch_k < self.stoch_buy and ctx.stoch_k > ctx.stoch_d):
            signal = "BUY"
            tier1 = ctx.bbpb <= 0.05 and ctx.rsi5 < 25 and ctx.stoch_k < 20
            score = (4.5 if tier1 else 3.0) + (38 - ctx.rsi5) * 0.06
            reasons.append(f"✅ BB下限(%B={ctx.bbpb:.2f}≤{self.bbpb_buy}) — 平均回帰 (Bollinger 2001)")
            reasons.append(f"✅ RSI5売られすぎ({ctx.rsi5:.1f}<{self.rsi5_buy})")
            reasons.append(f"✅ Stochゴールデンクロス(K={ctx.stoch_k:.0f}>D={ctx.stoch_d:.0f})")
            # Stochクロスギャップボーナス（条件→ボーナスに緩和）
            gap = ctx.stoch_k - ctx.stoch_d
            if gap > 1.5:
                score += 0.6
                reasons.append(f"✅ Stochクロスギャップ大({gap:.1f}>1.5)")
            elif gap > 0.5:
                score += 0.3
                reasons.append(f"✅ Stochクロスギャップ中({gap:.1f}>0.5)")
            # 前バー陰線ボーナス（条件→ボーナスに緩和）
            if ctx.prev_close <= ctx.prev_open:
                score += 0.3
                reasons.append("✅ 前バー陰線（プルバック確認）")
            if tier1:
                reasons.append("🎯 Tier1: 極端条件（高確信）")
            # MACD方向ボーナス
            if ctx.macdh > 0:
                score += 0.5
                reasons.append("✅ MACDヒストグラム上昇")
            # MACD-H反転ボーナス
            if ctx.macdh > ctx.macdh_prev and ctx.macdh_prev <= ctx.macdh_prev2:
                score += 0.6
                reasons.append("✅ MACD-H反転上昇（モメンタム消耗→回復）")
            # SL/TP
            tp_mult = self.tp_mult_tier1 if tier1 else self.tp_mult_tier2
            tp = ctx.entry + ctx.atr7 * tp_mult
            sl_dist = max(abs(ctx.entry - ctx.bb_lower) + ctx.atr7 * 0.3, _min_sl)
            sl = ctx.entry - sl_dist

        # ── SELL判定 ──
        if (signal is None and ctx.bbpb >= self.bbpb_sell
                and ctx.rsi5 > self.rsi5_sell and ctx.stoch_k > self.stoch_sell
                and ctx.stoch_k < ctx.stoch_d):
            signal = "SELL"
            tier1 = ctx.bbpb >= 0.95 and ctx.rsi5 > 75 and ctx.stoch_k > 80
            score = (4.5 if tier1 else 3.0) + (ctx.rsi5 - 58) * 0.06
            reasons.append(f"✅ BB上限(%B={ctx.bbpb:.2f}≥{self.bbpb_sell}) — 平均回帰 (Bollinger 2001)")
            reasons.append(f"✅ RSI5買われすぎ({ctx.rsi5:.1f}>{self.rsi5_sell})")
            reasons.append(f"✅ Stochデッドクロス(K={ctx.stoch_k:.0f}<D={ctx.stoch_d:.0f})")
            gap = ctx.stoch_d - ctx.stoch_k
            if gap > 1.5:
                score += 0.6
                reasons.append(f"✅ Stochクロスギャップ大({gap:.1f}>1.5)")
            if ctx.prev_close >= ctx.prev_open:
                score += 0.3
                reasons.append("✅ 前バー陽線（戻り確認）")
            if tier1:
                reasons.append("🎯 Tier1: 極端条件（高確信）")
            if ctx.macdh < 0:
                score += 0.5
                reasons.append("✅ MACDヒストグラム下落")
            if ctx.macdh < ctx.macdh_prev and ctx.macdh_prev >= ctx.macdh_prev2:
                score += 0.6
                reasons.append("✅ MACD-H反転下落（モメンタム消耗→回復）")
            tp_mult = self.tp_mult_tier1 if tier1 else self.tp_mult_tier2
            tp = ctx.entry - ctx.atr7 * tp_mult
            sl_dist = max(abs(ctx.bb_upper - ctx.entry) + ctx.atr7 * 0.3, _min_sl)
            sl = ctx.entry + sl_dist

        if signal is None:
            return None

        # ── USD/JPY専用ボーナス (Option C) ──
        if ctx.is_jpy:
            # Gold Hours bonus: UTC 05-08, 19-23 (WR=60-85%, 低ボラ高速反転)
            if ctx.hour_utc in self._gold_hours:
                score += 0.5
                reasons.append(f"✅ Gold Hour(UTC {ctx.hour_utc:02d}) — USD/JPY高WR時間帯")
            # ADX>=30 trend BB reversion bonus (USD/JPY独自: トレンド中BB反発 WR=60%)
            if ctx.adx >= 30:
                score += 0.6
                reasons.append(
                    f"✅ トレンド中BB反発(ADX={ctx.adx:.1f}>=30) — "
                    f"USD/JPY高WR条件"
                )

        conf = int(min(85, 50 + score * 4))
        # ── レジーム情報 (ペア別表示) ──
        if ctx.is_jpy:
            reasons.append(
                f"📊 レジーム: USD/JPY最適化(ADX={ctx.adx:.1f}, "
                f"UTC={ctx.hour_utc:02d})"
            )
        else:
            reasons.append(
                f"📊 レジーム: レンジ(ADX={ctx.adx:.1f}<{self.adx_max})"
            )
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)
