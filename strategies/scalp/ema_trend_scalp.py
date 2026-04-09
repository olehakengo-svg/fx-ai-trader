"""
EMA Trend Scalp — トレンド中のEMAプルバック順張りスキャルプ

学術的根拠:
  - Time Series Momentum (Moskowitz, Ooi, Pedersen 2012):
    トレンド資産はトレンド継続する傾向 → 押し目買い/戻り売りに正のEV
  - EMAの動的S/R (Murphy 1999, Technical Analysis of the Financial Markets):
    EMA21はトレンド中の動的サポート/レジスタンスとして機能
  - トレンド継続パターン (Edwards & Magee 1948):
    健全なトレンドは浅い押し目→EMA反発→高値更新のサイクルを繰り返す

設計思想:
  - bb_rsi (MR, BB極端) と vol_momentum (TF, BBブレイクアウト) のGAPを埋める
  - ADX 20-40, BB%B 0.25-0.80 の「トレンド中間帯」を攻略
  - EMA21付近へのプルバック → バウンス確認 → トレンド方向にエントリー
  - bb_rsiと負相関 → ポートフォリオ分散効果

4原則準拠:
  - 静的時間ブロックなし — マーケット開いてる間は攻める
  - Spread/SL Gateが動的防御を担う
  - 攻撃は最大の防御

SL/TP:
  - SL: ATR7 × 1.0 (トレンド中のノイズ吸収)
  - TP: ATR7 × 1.8 (トレンド継続分を取る)
  - MIN_RR: 1.2

Sentinel戦略:
  - 初期は 0.01 lot (_UNIVERSAL_SENTINEL)
  - N >= 30 到達後に本番データで WFO / MC 再評価
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class EmaTrendScalp(StrategyBase):
    """EMA Trend Scalp: トレンド中のEMA21プルバック順張り。"""

    name = "ema_trend_scalp"
    mode = "scalp"
    enabled = True

    # ══════════════════════════════════════════════════
    # パラメータ
    # ══════════════════════════════════════════════════

    # ── トレンド確認 ──
    ADX_MIN = 20            # ADX ≥ 20: トレンド存在の最低条件

    # ── EMA プルバックゾーン (ATR7倍率) ──
    # 価格がEMA21から±この範囲内 = プルバック中と判定
    PB_ABOVE_MULT = 0.5     # EMA21 + ATR7×0.5 まで (上)
    PB_BELOW_MULT = 0.3     # EMA21 - ATR7×0.3 まで (下)

    # ── RSI5フィルター ──
    RSI_BUY_MIN = 30        # BUY: RSI下限 (深い過売りはbb_rsi領域)
    RSI_BUY_MAX = 65        # BUY: RSI上限 (過買い圏は伸びしろなし)
    RSI_SELL_MIN = 35       # SELL: RSI下限
    RSI_SELL_MAX = 70       # SELL: RSI上限

    # ── BB%B 中間帯フィルター ──
    # bb_rsi (≤0.25/≥0.75) と vol_momentum (≥0.90/≤0.10) のGAPを埋める
    BBPB_BUY_MIN = 0.25     # BUY: BB下限 (これ以下はbb_rsi領域)
    BBPB_BUY_MAX = 0.75     # BUY: BB上限 (これ以上は過買い接近)
    BBPB_SELL_MIN = 0.25    # SELL: BB下限
    BBPB_SELL_MAX = 0.75    # SELL: BB上限

    # ── SL/TP ──
    SL_ATR_MULT = 1.0       # SL = ATR7 × 1.0
    TP_ATR_MULT = 1.8       # TP = ATR7 × 1.8 (トレンド継続分)
    MIN_RR = 1.2

    # ── ペアフィルター ──
    _DISABLED_SYMBOLS = frozenset({"EURGBP"})   # EUR/GBP構造的不可能

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        """
        EMA21プルバック順張りシグナル評価。

        条件:
          1. ペアフィルター: EUR/GBP除外
          2. ADX ≥ 20 (トレンド存在)
          3. EMA方向: BUY=EMA9>EMA21, SELL=EMA9<EMA21
          4. EMA21プルバック: 価格がEMA21付近 (ATR7×0.5以内)
          5. 反転足確認: BUY=陽線, SELL=陰線
          6. RSI5: 過熱圏でない (伸びしろ確認)
          7. BB%B: 中間帯 (bb_rsi/vol_momentumとの競合回避)
        """
        # ═══════════════════════════════════════════
        # STEP 1: ペアフィルター
        # ═══════════════════════════════════════════
        _sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        if _sym in self._DISABLED_SYMBOLS:
            return None

        # ═══════════════════════════════════════════
        # STEP 2: ADXトレンド確認
        # ═══════════════════════════════════════════
        if ctx.adx < self.ADX_MIN:
            return None

        # ═══════════════════════════════════════════
        # STEP 3: EMA方向 + プルバック検出
        # ═══════════════════════════════════════════
        _atr = ctx.atr7 if ctx.atr7 > 0 else ctx.atr
        if _atr <= 0:
            return None

        _min_sl = 0.030 if ctx.pip_mult == 100 else 0.00030

        signal = None
        score = 0.0
        reasons = []

        # ── BUY: EMA9 > EMA21 + 価格がEMA21付近にプルバック ──
        if ctx.ema9 > ctx.ema21:
            _upper = ctx.ema21 + _atr * self.PB_ABOVE_MULT
            _lower = ctx.ema21 - _atr * self.PB_BELOW_MULT
            if _lower <= ctx.entry <= _upper:
                # 反転足: 陽線 (Close > Open)
                if ctx.entry <= ctx.open_price:
                    return None
                # RSI: 過買いでない
                if not (self.RSI_BUY_MIN <= ctx.rsi5 <= self.RSI_BUY_MAX):
                    return None
                # BB%B: 中間帯
                if not (self.BBPB_BUY_MIN <= ctx.bbpb <= self.BBPB_BUY_MAX):
                    return None

                signal = "BUY"
                score = 3.0
                reasons.append(
                    f"✅ EMA上昇トレンド(EMA9={ctx.ema9:.3f}>EMA21={ctx.ema21:.3f})"
                )
                reasons.append(
                    f"✅ EMA21プルバック(価格={ctx.entry:.3f}, "
                    f"zone=[{_lower:.3f},{_upper:.3f}])"
                )
                reasons.append(f"✅ 陽線バウンス(C={ctx.entry:.3f}>O={ctx.open_price:.3f})")
                reasons.append(f"✅ RSI5={ctx.rsi5:.1f} (伸びしろあり)")

                # SL/TP — SLフロア適用時はTPもスケールしてRR維持
                _sl_dist = max(_atr * self.SL_ATR_MULT, _min_sl)
                _tp_dist = max(_atr * self.TP_ATR_MULT, _sl_dist * self.MIN_RR)
                sl = ctx.entry - _sl_dist
                tp = ctx.entry + _tp_dist

        # ── SELL: EMA9 < EMA21 + 価格がEMA21付近に戻り ──
        if signal is None and ctx.ema9 < ctx.ema21:
            _upper = ctx.ema21 + _atr * self.PB_BELOW_MULT
            _lower = ctx.ema21 - _atr * self.PB_ABOVE_MULT
            if _lower <= ctx.entry <= _upper:
                # 反転足: 陰線 (Close < Open)
                if ctx.entry >= ctx.open_price:
                    return None
                # RSI
                if not (self.RSI_SELL_MIN <= ctx.rsi5 <= self.RSI_SELL_MAX):
                    return None
                # BB%B
                if not (self.BBPB_SELL_MIN <= ctx.bbpb <= self.BBPB_SELL_MAX):
                    return None

                signal = "SELL"
                score = 3.0
                reasons.append(
                    f"✅ EMA下降トレンド(EMA9={ctx.ema9:.3f}<EMA21={ctx.ema21:.3f})"
                )
                reasons.append(
                    f"✅ EMA21戻り(価格={ctx.entry:.3f}, "
                    f"zone=[{_lower:.3f},{_upper:.3f}])"
                )
                reasons.append(f"✅ 陰線反落(C={ctx.entry:.3f}<O={ctx.open_price:.3f})")
                reasons.append(f"✅ RSI5={ctx.rsi5:.1f} (下落余地あり)")

                # SL/TP — SLフロア適用時はTPもスケールしてRR維持
                _sl_dist = max(_atr * self.SL_ATR_MULT, _min_sl)
                _tp_dist = max(_atr * self.TP_ATR_MULT, _sl_dist * self.MIN_RR)
                sl = ctx.entry + _sl_dist
                tp = ctx.entry - _tp_dist

        if signal is None:
            return None

        # ═══════════════════════════════════════════
        # STEP 4: RR確認
        # ═══════════════════════════════════════════
        _sl_dist_final = abs(ctx.entry - sl)
        _tp_dist_final = abs(tp - ctx.entry)
        if _sl_dist_final <= 0 or _tp_dist_final / _sl_dist_final < self.MIN_RR:
            return None
        _rr = _tp_dist_final / _sl_dist_final

        # ═══════════════════════════════════════════
        # STEP 5: ボーナス
        # ═══════════════════════════════════════════

        # ── ADX強度ボーナス (Wilder 1978) ──
        if ctx.adx >= 30:
            score += 0.5
            reasons.append(f"✅ 強トレンド(ADX={ctx.adx:.1f}>=30)")

        # ── EMA50整列ボーナス (パーフェクトオーダー) ──
        if signal == "BUY" and ctx.ema9 > ctx.ema21 > ctx.ema50:
            score += 0.5
            reasons.append("✅ EMAパーフェクトオーダー(9>21>50)")
        elif signal == "SELL" and ctx.ema9 < ctx.ema21 < ctx.ema50:
            score += 0.5
            reasons.append("✅ EMAパーフェクトオーダー(9<21<50)")

        # ── MACD方向ボーナス ──
        if signal == "BUY" and ctx.macdh > 0:
            score += 0.4
            reasons.append("✅ MACD-H正(上昇モメンタム)")
        elif signal == "SELL" and ctx.macdh < 0:
            score += 0.4
            reasons.append("✅ MACD-H負(下落モメンタム)")

        # ── MACD-H反転ボーナス (モメンタム回復) ──
        if signal == "BUY" and ctx.macdh > ctx.macdh_prev:
            score += 0.3
            reasons.append("✅ MACD-H上昇中(モメンタム回復)")
        elif signal == "SELL" and ctx.macdh < ctx.macdh_prev:
            score += 0.3
            reasons.append("✅ MACD-H下落中(モメンタム回復)")

        # ── DI方向一致ボーナス ──
        if signal == "BUY" and ctx.adx_pos > ctx.adx_neg:
            score += 0.3
            reasons.append(f"✅ +DI>{int(ctx.adx_pos)}>-DI{int(ctx.adx_neg)}(方向一致)")
        elif signal == "SELL" and ctx.adx_neg > ctx.adx_pos:
            score += 0.3
            reasons.append(f"✅ -DI>{int(ctx.adx_neg)}>+DI{int(ctx.adx_pos)}(方向一致)")

        # ── RR情報 ──
        reasons.append(
            f"📊 RR={_rr:.1f} SL={sl:.5f} TP={tp:.5f} | "
            f"ADX={ctx.adx:.1f} BB%B={ctx.bbpb:.2f}"
        )

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
