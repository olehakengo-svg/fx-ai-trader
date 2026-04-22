"""
BB + RSI Mean Reversion — ペア別最適化 (Bollinger 2001 + Wilder 1978)

Option C 統合改修 (2026-04-04 USD/JPY解剖レポート):
  EUR/USD: ADX<25 レンジ環境限定（従来通り）
  USD/JPY: ADX制限撤廃 + Death Valleyブロック + Gold Hoursボーナス

v7.0 Stochクロスオーバー緩和:
  K>D/K<D strict → K>D OR K上昇中 / K<D OR K下落中
  理由: 1m足でもK=90時にD<Kが数分持続し、最良エントリーを逃す。
  反転方向に動いていれば十分な確認（dt_bb_rsi_mrと同一修正）。

v8.3 即死率改善 (77.6%→目標20-25%):
  Fix1: 確認足フィルター — BUY: Close>Open(陽線), SELL: Close<Open(陰線)
        極端値に「居る」だけでなく「反転し始めた」確認。最大インパクト
  Fix2: TREND逆張りブロック — TREND_BULLでSELL、TREND_BEARでBUYをブロック
        即死の40%がトレンド逆張り。RANGEとトレンド順方向のみ許可
  Fix3: JPY ADXフロア — ADX<15でブロック (極端チョッピー=純ノイズ)

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
    strategy_type = "MR"   # v10: Q4 paradox fix — ADX>25 → conf penalty

    # チューナブルパラメータ
    adx_max = 25          # EUR/USD用: レンジ判定上限（学術水準 ADX≥25はトレンド領域）
    bbpb_buy = 0.30       # BB%B BUY閾値 (v7.0: 0.25→0.30 カバレッジ+7.8%)
    bbpb_sell = 0.70      # BB%B SELL閾値 (v7.0: 0.75→0.70 カバレッジ+5.2%)
    rsi5_buy = 45         # RSI5 BUY閾値
    rsi5_sell = 55        # RSI5 SELL閾値
    stoch_buy = 45        # Stoch BUY閾値
    stoch_sell = 55       # Stoch SELL閾値
    tp_mult_tier1 = 2.2   # TP倍率 (Tier1) v6.3: 2.0→2.2 極端ゾーン反転幅大
    tp_mult_tier2 = 1.5   # TP倍率 (Tier2)

    # ── USD/JPY専用: Gold Hours (Option C + v6.3強化) ──
    # v7.0: Death Valley撤廃 — マーケット開いてる間は攻める。
    # 静的時間ブロックではなくSpread/SL Gate(動的)が防御を担う。
    # 旧Death Valley {0,1,9,12,13,14,15,16} は8h/日ブロック → 攻撃機会の致命的損失
    _gold_hours = frozenset({5, 6, 7, 8, 19, 20, 21, 22, 23})

    # ── ペアフィルター (2026-04-06 Session Matrix BT) ──
    # EUR/GBP: 全セッション壊滅 (Tokyo PF=0.29, NY Overlap PF=0.53) → 完全無効化
    _disabled_symbols = frozenset({"EURGBP"})

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── EUR/GBP無効化: 全セッションPF<0.7 ──
        _sym = ctx.symbol.upper().replace("=X", "").replace("_", "")
        if _sym in self._disabled_symbols:
            return None

        # ── ペア別ADXフィルター (Option C) ──
        if ctx.is_jpy:
            # USD/JPY: ADX制限なし（トレンド中BB反発 WR=60% — 逆にエッジ増大）
            # v7.0: Death Valley撤廃 — Spread/SL Gateが動的防御を担う
            # v8.3 Fix3: ADXフロア — 極端チョッピー(ADX<15)は純ノイズ、エッジゼロ
            if ctx.adx < 15:
                return None
        else:
            # EUR/USD: 従来通り ADX<25 レンジ環境のみ
            if ctx.adx >= self.adx_max:
                return None

        # v8.3 Fix2: TREND逆張りブロック — 即死の40%がトレンド逆張り
        # TREND_BULLでSELL、TREND_BEARでBUYをブロック。RANGEとトレンド順方向のみ許可
        _regime = (ctx.regime or {}).get("regime", "") if isinstance(ctx.regime, dict) else ""

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0

        _min_sl = 0.030 if ctx.pip_mult == 100 else 0.00030  # JPY+XAU: pip=0.01

        # v7.0: prev_stoch_k — Stochクロスオーバー緩和用
        # 厳密なK>D/K<D(クロス瞬間)ではなく、K反転方向でも許容
        # 1m足でもK=90時にD<Kが数分持続→最良エントリーを逃す問題を解消
        _prev_stoch_k = (
            float(ctx.df.iloc[-2].get("stoch_k", 50))
            if ctx.df is not None and len(ctx.df) >= 2
            else 50.0
        )

        # ── BUY判定 ──
        # v7.0: Stoch K>D strict → K>D OR K上昇中（反転方向で許容）
        # v8.3 Fix1: 確認足フィルター — Close>Open(陽線)で反転開始を確認
        # v8.3 Fix2: TREND_BEARでBUYブロック（トレンド逆張り排除）
        if (ctx.bbpb <= self.bbpb_buy and ctx.rsi5 < self.rsi5_buy
                and ctx.stoch_k < self.stoch_buy
                and (ctx.stoch_k > ctx.stoch_d or ctx.stoch_k > _prev_stoch_k)
                and ctx.entry > ctx.open_price
                and _regime != "TREND_BEAR"):
            signal = "BUY"
            tier1 = ctx.bbpb <= 0.05 and ctx.rsi5 < 25 and ctx.stoch_k < 20
            score = (4.5 if tier1 else 3.0) + (38 - ctx.rsi5) * 0.06
            reasons.append(f"✅ BB下限(%B={ctx.bbpb:.2f}≤{self.bbpb_buy}) — 平均回帰 (Bollinger 2001)")
            reasons.append(f"✅ RSI5売られすぎ({ctx.rsi5:.1f}<{self.rsi5_buy})")
            reasons.append(f"✅ 確認足陽線(C={ctx.entry:.5g}>O={ctx.open_price:.5g}) — v8.3反転確認")
            _buy_cross = ctx.stoch_k > ctx.stoch_d
            _buy_rising = ctx.stoch_k > _prev_stoch_k
            reasons.append(
                f"✅ Stoch反転確認(K={ctx.stoch_k:.0f}"
                f"{'>D=' + str(int(ctx.stoch_d)) if _buy_cross else ''}"
                f"{'↑prev=' + str(int(_prev_stoch_k)) if _buy_rising else ''}"
                f")"
            )
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
        # v7.0: Stoch K<D strict → K<D OR K下落中（反転方向で許容）
        # v8.3 Fix1: 確認足フィルター — Close<Open(陰線)で反転開始を確認
        # v8.3 Fix2: TREND_BULLでSELLブロック（トレンド逆張り排除）
        if (signal is None and ctx.bbpb >= self.bbpb_sell
                and ctx.rsi5 > self.rsi5_sell and ctx.stoch_k > self.stoch_sell
                and (ctx.stoch_k < ctx.stoch_d or ctx.stoch_k < _prev_stoch_k)
                and ctx.entry < ctx.open_price
                and _regime != "TREND_BULL"):
            signal = "SELL"
            tier1 = ctx.bbpb >= 0.95 and ctx.rsi5 > 75 and ctx.stoch_k > 80
            score = (4.5 if tier1 else 3.0) + (ctx.rsi5 - 58) * 0.06
            reasons.append(f"✅ BB上限(%B={ctx.bbpb:.2f}≥{self.bbpb_sell}) — 平均回帰 (Bollinger 2001)")
            reasons.append(f"✅ RSI5買われすぎ({ctx.rsi5:.1f}>{self.rsi5_sell})")
            reasons.append(f"✅ 確認足陰線(C={ctx.entry:.5g}<O={ctx.open_price:.5g}) — v8.3反転確認")
            _sell_cross = ctx.stoch_k < ctx.stoch_d
            _sell_falling = ctx.stoch_k < _prev_stoch_k
            reasons.append(
                f"✅ Stoch反転確認(K={ctx.stoch_k:.0f}"
                f"{'<D=' + str(int(ctx.stoch_d)) if _sell_cross else ''}"
                f"{'↓prev=' + str(int(_prev_stoch_k)) if _sell_falling else ''}"
                f")"
            )
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

        # ── USD/JPY専用ボーナス (Option C + v6.3強化) ──
        if ctx.is_jpy:
            # Gold Hours bonus (v6.3: 0.5→0.8 集中度↑)
            if ctx.hour_utc in self._gold_hours:
                score += 0.8
                reasons.append(f"✅ Gold Hour(UTC {ctx.hour_utc:02d}) — USD/JPY高WR時間帯 +0.8")
            # ADX>=30 trend BB reversion bonus (USD/JPY独自: トレンド中BB反発 WR=60%)
            if ctx.adx >= 30:
                score += 0.6
                reasons.append(
                    f"✅ トレンド中BB反発(ADX={ctx.adx:.1f}>=30) — "
                    f"USD/JPY高WR条件"
                )

        # v10: Confidence v2 — MR anti-trend penalty (ADX>25 reduces conf)
        # Root-cause: strong trend features are inverse-edge for MR. Legacy formula
        # pushed MR entries to Q4 when they should be deprioritized.
        from modules.confidence_v2 import apply_penalty
        _legacy_conf = int(min(85, 50 + score * 4))
        conf = apply_penalty(_legacy_conf, self.strategy_type, ctx.adx, conf_max=85)
        if conf != _legacy_conf:
            reasons.append(
                f"🔧 [v2] MR anti-trend: ADX={ctx.adx:.1f}>25 → conf {_legacy_conf}→{conf}"
            )
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
