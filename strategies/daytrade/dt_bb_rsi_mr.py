"""
DT BB RSI Mean-Reversion — 15分足ボリンジャーバンド + RSI 平均回帰戦略

学術的根拠:
  - Bollinger Bands (Bollinger 1992, 2001): 価格はBBの2標準偏差帯に約95%の
    時間収まる。BB%B < 0.20 (下限接近) またはBB%B > 0.80 (上限接近) で
    平均(BB中心線)への回帰が統計的に期待される。
  - RSI (Wilder 1978): Relative Strength Index 14期間。
    RSI < 35 = 売られすぎ → 反発期待、RSI > 65 = 買われすぎ → 反落期待。
  - Stochastic Oscillator (Lane 1984): ゴールデン/デッドクロスまたは
    反転方向への推移による短期モメンタム転換の確認。v7.0で厳密なクロス要件を
    緩和し、K上昇中/下落中でも許容 (15m足でクロス瞬間は1日0-2回と希少)。

設計思想:
  - Scalp bb_rsi_reversion (1m, PF=1.13) のコアロジックを15m足に移植。
  - 15m足はノイズが少なく、BB%BとRSIの信号品質が向上する反面、
    ATRが大きいためSL/TPを適切に拡大する必要がある。
  - RANGE/WIDE_RANGEレジーム専用 (ADX < 25)。トレンド環境ではBB反発が
    フェイルする確率が高いため、TF戦略に委ねる。
  - demo_trader.py の RANGE Exit Optimization (BB_mid TP, SL widening) が
    自動適用されるため、TP は ATR ベースで保守的に設定。

対象ペア:
  - USD/JPY, EUR/USD, GBP/USD (EUR/GBP は eurgbp_daily_mr が専用で対応)

リスク管理:
  - SL: ATR(14) x 1.2 (15m足ノイズ吸収に十分な距離)
  - TP: ATR(14) x 1.5 (BB_mid targeting は demo_trader が適用)
  - MIN_RR: 1.2
  - MAX_HOLD: 8 bars (= 2時間 @ 15m足)

Sentinel 戦略:
  - 初期は 0.01 lot 観測モード (_UNIVERSAL_SENTINEL に登録)
  - N >= 30 到達後に本番データで WFO / MC 再評価
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class DtBbRsiMR(StrategyBase):
    """DT BB RSI Mean-Reversion: 15分足 BB%B + RSI14 + Stoch 平均回帰。"""

    name = "dt_bb_rsi_mr"
    mode = "daytrade"
    enabled = True

    # ══════════════════════════════════════════════════
    # パラメータ定数 (チューナブル)
    # ══════════════════════════════════════════════════

    # ── BB%B閾値 (Bollinger 1992) ──
    # BB%B < BUY閾値: 下限バンド接近 → BUY (平均回帰)
    # BB%B > SELL閾値: 上限バンド接近 → SELL (平均回帰)
    # v7.0: 0.20/0.80→0.30/0.70 (N=0発火率改善, バンド下位30%で十分な偏り)
    BBPB_BUY_THRES  = 0.30      # BB%B BUY閾値 (下位30%)
    BBPB_SELL_THRES = 0.70      # BB%B SELL閾値 (上位70%)
    BBPB_EXTREME_BUY  = 0.10    # v7.0: 0.05→0.10 極端ゾーン (Tier1)
    BBPB_EXTREME_SELL = 0.90    # v7.0: 0.95→0.90 極端ゾーン (Tier1)

    # ── RSI閾値 (Wilder 1978) ──
    # 15m足ではRSI14を使用 (Scalp版のRSI5より長周期で安定)
    # v7.0: 40/60→45/55 (15m RSI14は安定しており45でも方向バイアス確認として十分)
    RSI_BUY_THRES  = 45         # RSI14 BUY閾値 (売られすぎ側)
    RSI_SELL_THRES = 55         # RSI14 SELL閾値 (買われすぎ側)
    RSI_EXTREME_BUY  = 30       # v7.0: 25→30 極端RSI (Tier1)
    RSI_EXTREME_SELL = 70       # v7.0: 75→70 極端RSI (Tier1)

    # ── Stochastic閾値 (Lane 1984) ──
    # v7.0: クロスオーバー要件を緩和 (K>D strict → K>D OR K上昇中)
    # 厳密なクロスは15m足で1日0-2回のみ → 反転方向に動いていれば十分
    STOCH_BUY_THRES  = 40       # StochK BUY閾値 (過売り圏)
    STOCH_SELL_THRES = 60       # StochK SELL閾値 (過買い圏)
    STOCH_EXTREME_BUY  = 20     # 極端Stoch (Tier1)
    STOCH_EXTREME_SELL = 80     # 極端Stoch (Tier1)

    # ── レジームフィルター ──
    ADX_MAX = 25                # ADX < 25: レンジ環境のみ (Wilder ADX基準)

    # ── SL/TP (ATR倍率) ──
    SL_ATR_MULT = 1.2           # SL = ATR(14) x 1.2 (15m足ノイズ吸収)
    TP_ATR_MULT = 1.5           # TP = ATR(14) x 1.5 (BB_mid targeting は別途適用)
    MIN_RR = 1.2                # 最低リスクリワード比

    # ── 保持 ──
    MAX_HOLD_BARS = 8           # 最大8バー (= 2時間 @ 15m足)

    # ── ペアフィルター ──
    # EUR/GBP は eurgbp_daily_mr 専用 → 除外
    # USD/JPY, EUR/USD, GBP/USD のみ対象
    _ALLOWED_SYMBOLS = frozenset({"USDJPY", "EURUSD", "GBPUSD"})

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        """
        15m足 BB RSI Mean-Reversion シグナル評価。

        条件:
          1. ペアフィルター: USD/JPY, EUR/USD, GBP/USD のみ
          2. レジームフィルター: ADX < 25 (RANGE/WIDE_RANGE)
          3. BB%B 偏位: BUY ≤ 0.30 / SELL ≥ 0.70 (v7.0: 0.20/0.80→緩和)
          4. RSI14 方向確認: BUY < 45 / SELL > 55 (v7.0: 40/60→緩和)
          5. Stoch反転: BUY: K<40 & (K>D OR K↑) / SELL: K>60 & (K<D OR K↓)
          6. 反転足確認: BUY: Close > Open / SELL: Close < Open
          7. RR >= 1.2

        Returns:
            Candidate or None
        """
        # ═══════════════════════════════════════════════════
        # STEP 1: ペアフィルター
        # EUR/GBP は eurgbp_daily_mr が専用で対応するため除外
        # ═══════════════════════════════════════════════════
        _sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        if _sym not in self._ALLOWED_SYMBOLS:
            return None

        # ═══════════════════════════════════════════════════
        # STEP 2: レジームフィルター (ADX < 25)
        # Wilder (1978): ADX >= 25 はトレンド領域。
        # 平均回帰はレンジ環境でのみ統計的に有効。
        # TREND/HIGH_VOL ではBB反発がフェイルする確率が高い。
        # ═══════════════════════════════════════════════════
        if ctx.adx >= self.ADX_MAX:
            return None

        # ═══════════════════════════════════════════════════
        # STEP 3: シグナル判定
        # BB%B + RSI14 + Stochastic の3指標合致
        # ═══════════════════════════════════════════════════
        signal = None
        score = 0.0
        reasons = []

        # SL最低距離フロア (JPY/XAU vs 非JPY)
        _min_sl = 0.030 if ctx.pip_mult == 100 else 0.00030

        # v7.0: prev_stoch_k — Stochクロスオーバー緩和用
        # 厳密なK>D(クロス瞬間)ではなく、K上昇中(反転方向)でも許容
        _prev_stoch_k = (
            float(ctx.df.iloc[-2].get("stoch_k", 50))
            if ctx.df is not None and len(ctx.df) >= 2
            else 50.0
        )

        # ── BUY判定 ──
        # BB%B ≤ 0.30 (BB下限接近) + RSI14 < 45 + StochK < 40
        # + Stoch反転確認: K > D (ゴールデンクロス) OR K上昇中 (K > prev_K)
        if (ctx.bbpb <= self.BBPB_BUY_THRES
                and ctx.rsi < self.RSI_BUY_THRES
                and ctx.stoch_k < self.STOCH_BUY_THRES
                and (ctx.stoch_k > ctx.stoch_d
                     or ctx.stoch_k > _prev_stoch_k)):

            # ── 反転足確認: 現在バー陽線 (Close > Open) ──
            # 15m足の実体で反転方向を確認 (ノイズ低減)
            if ctx.entry <= ctx.open_price:
                return None

            signal = "BUY"

            # Tier1 判定: 極端ゾーン (高確信)
            _tier1 = (ctx.bbpb <= self.BBPB_EXTREME_BUY
                      and ctx.rsi < self.RSI_EXTREME_BUY
                      and ctx.stoch_k < self.STOCH_EXTREME_BUY)

            score = 4.5 if _tier1 else 3.0
            # RSI深度ボーナス: RSIが低いほどスコア加算
            score += (self.RSI_BUY_THRES - ctx.rsi) * 0.04

            reasons.append(
                f"✅ BB下限接近(BB%B={ctx.bbpb:.2f}≤{self.BBPB_BUY_THRES}) "
                f"— 平均回帰 (Bollinger 1992)"
            )
            reasons.append(f"✅ RSI14売られすぎ({ctx.rsi:.1f}<{self.RSI_BUY_THRES}) (Wilder 1978)")
            _stoch_cross = ctx.stoch_k > ctx.stoch_d
            _stoch_rising = ctx.stoch_k > _prev_stoch_k
            reasons.append(
                f"✅ Stoch反転確認(K={ctx.stoch_k:.0f}"
                f"{'>D=' + str(int(ctx.stoch_d)) if _stoch_cross else ''}"
                f"{'↑prev=' + str(int(_prev_stoch_k)) if _stoch_rising else ''}"
                f") — 過売り圏反転 (Lane 1984)"
            )
            reasons.append(
                f"✅ 反転足確認: Close={ctx.entry:.5f} > Open={ctx.open_price:.5f}"
            )

            # Stochクロスギャップボーナス
            _gap = ctx.stoch_k - ctx.stoch_d
            if _gap > 2.0:
                score += 0.5
                reasons.append(f"✅ Stochクロスギャップ大({_gap:.1f}>2.0)")

            if _tier1:
                reasons.append("🎯 Tier1: 極端条件（高確信 — BB%B<0.10, RSI<30, Stoch<20）")

            # MACD方向ボーナス (モメンタム転換確認)
            if ctx.macdh > 0:
                score += 0.4
                reasons.append("✅ MACDヒストグラム正（上昇モメンタム）")
            if ctx.macdh > ctx.macdh_prev and ctx.macdh_prev <= ctx.macdh_prev2:
                score += 0.5
                reasons.append("✅ MACD-H反転上昇（モメンタム消耗→回復）")

            # SL/TP計算
            _sl_dist = max(ctx.atr * self.SL_ATR_MULT, _min_sl)
            _tp_dist = ctx.atr * self.TP_ATR_MULT
            sl = ctx.entry - _sl_dist
            tp = ctx.entry + _tp_dist

        # ── SELL判定 ──
        # BB%B ≥ 0.70 (BB上限接近) + RSI14 > 55 + StochK > 60
        # + Stoch反転確認: K < D (デッドクロス) OR K下落中 (K < prev_K)
        elif (ctx.bbpb >= self.BBPB_SELL_THRES
                and ctx.rsi > self.RSI_SELL_THRES
                and ctx.stoch_k > self.STOCH_SELL_THRES
                and (ctx.stoch_k < ctx.stoch_d
                     or ctx.stoch_k < _prev_stoch_k)):

            # ── 反転足確認: 現在バー陰線 (Close < Open) ──
            if ctx.entry >= ctx.open_price:
                return None

            signal = "SELL"

            # Tier1 判定: 極端ゾーン
            _tier1 = (ctx.bbpb >= self.BBPB_EXTREME_SELL
                      and ctx.rsi > self.RSI_EXTREME_SELL
                      and ctx.stoch_k > self.STOCH_EXTREME_SELL)

            score = 4.5 if _tier1 else 3.0
            # RSI深度ボーナス: RSIが高いほどスコア加算
            score += (ctx.rsi - self.RSI_SELL_THRES) * 0.04

            reasons.append(
                f"✅ BB上限接近(BB%B={ctx.bbpb:.2f}≥{self.BBPB_SELL_THRES}) "
                f"— 平均回帰 (Bollinger 1992)"
            )
            reasons.append(f"✅ RSI14買われすぎ({ctx.rsi:.1f}>{self.RSI_SELL_THRES}) (Wilder 1978)")
            _stoch_cross = ctx.stoch_k < ctx.stoch_d
            _stoch_falling = ctx.stoch_k < _prev_stoch_k
            reasons.append(
                f"✅ Stoch反転確認(K={ctx.stoch_k:.0f}"
                f"{'<D=' + str(int(ctx.stoch_d)) if _stoch_cross else ''}"
                f"{'↓prev=' + str(int(_prev_stoch_k)) if _stoch_falling else ''}"
                f") — 過買い圏反転 (Lane 1984)"
            )
            reasons.append(
                f"✅ 反転足確認: Close={ctx.entry:.5f} < Open={ctx.open_price:.5f}"
            )

            # Stochクロスギャップボーナス
            _gap = ctx.stoch_d - ctx.stoch_k
            if _gap > 2.0:
                score += 0.5
                reasons.append(f"✅ Stochクロスギャップ大({_gap:.1f}>2.0)")

            if _tier1:
                reasons.append("🎯 Tier1: 極端条件（高確信 — BB%B>0.90, RSI>70, Stoch>80）")

            # MACD方向ボーナス
            if ctx.macdh < 0:
                score += 0.4
                reasons.append("✅ MACDヒストグラム負（下落モメンタム）")
            if ctx.macdh < ctx.macdh_prev and ctx.macdh_prev >= ctx.macdh_prev2:
                score += 0.5
                reasons.append("✅ MACD-H反転下落（モメンタム消耗→回復）")

            # SL/TP計算
            _sl_dist = max(ctx.atr * self.SL_ATR_MULT, _min_sl)
            _tp_dist = ctx.atr * self.TP_ATR_MULT
            sl = ctx.entry + _sl_dist
            tp = ctx.entry - _tp_dist

        # ═══════════════════════════════════════════════════
        # シグナルなし → None
        # ═══════════════════════════════════════════════════
        if signal is None:
            return None

        # ═══════════════════════════════════════════════════
        # STEP 4: RR確認
        # MIN_RR = 1.2 を満たさない場合はスキップ
        # ═══════════════════════════════════════════════════
        _sl_dist_final = abs(ctx.entry - sl)
        _tp_dist_final = abs(tp - ctx.entry)
        if _sl_dist_final <= 0 or _tp_dist_final / _sl_dist_final < self.MIN_RR:
            return None

        _rr = _tp_dist_final / _sl_dist_final

        # ═══════════════════════════════════════════════════
        # STEP 5: ボーナス & ペナルティ
        # ═══════════════════════════════════════════════════

        # ── BB幅確認: バンド幅が狭すぎる場合はSQUEEZE接近 ──
        # bb_width_pct < 0.15 → ブレイクアウト前夜の可能性 (MR危険)
        if ctx.bb_width_pct < 0.15:
            score -= 0.5
            reasons.append(
                f"⚠️ BB幅狭(bb_width_pct={ctx.bb_width_pct:.2f}<0.15) "
                f"— SQUEEZE接近リスク"
            )

        # ── ADX低め確認: レンジ確度ボーナス ──
        if ctx.adx < 20:
            score += 0.3
            reasons.append(f"✅ 強レンジ確認: ADX={ctx.adx:.1f}<20")

        # ── HTFフィルター (ソフトペナルティ: MR戦略なのでハードブロックしない) ──
        _htf = ctx.htf or {}
        _agr = _htf.get("agreement", "mixed")
        if signal == "BUY" and _agr == "bear":
            score -= 0.5
            reasons.append(f"⚠️ HTF逆行: {_agr} (ソフトペナルティ)")
        elif signal == "SELL" and _agr == "bull":
            score -= 0.5
            reasons.append(f"⚠️ HTF逆行: {_agr} (ソフトペナルティ)")

        # ── RR / レジーム情報 ──
        reasons.append(
            f"📊 RR={_rr:.1f} SL={sl:.5f} TP={tp:.5f} | "
            f"レジーム: レンジ(ADX={ctx.adx:.1f}<{self.ADX_MAX})"
        )

        # ── Confidence計算 ──
        conf = int(min(85, 50 + score * 4))

        return Candidate(
            signal=signal,
            confidence=conf,
            sl=sl,
            tp=tp,
            reasons=reasons,
            entry_type=self.name,
            score=score,
        )
