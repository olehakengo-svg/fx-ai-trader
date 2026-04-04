"""
ADX Trend Continuation (ADX TC) — トレンド押し目/戻り目エントリー

学術的根拠:
  - Wilder (1978): ADX≥25でトレンド存在を定量的に識別
  - Jegadeesh & Titman (1993): モメンタム効果（FX市場でも確認）
  - Menkhoff et al. (2012, Review of Financial Studies):
    FX市場における通貨モメンタムの普遍性を40年データで確認
  - Covel (2004): マルチタイムフレームトレンドフォロー原則

戦略コンセプト:
  ブレイクアウトではなくプルバック（押し目/戻り目）を狙う。
  トレンドが確立された後(ADX≥25, EMAパーフェクトオーダー)の
  一時的リトレースメントでエントリーすることで、偽ブレイクを構造的に回避。

  LSB失敗の教訓: ナイーブブレイクアウトはFX 15m足で偽ブレイク率が極めて高い。
  本戦略は「ブレイクアウト」ではなく「確立済みトレンドへの再乗車」であり、
  偽ブレイク問題が構造的に発生しない。

エントリーロジック（2段階検出）:
  ■ STEP1: トレンド+プルバック検出（前1-3本で確認）
    1. ADX(14) >= 閾値（ペア別定数）→ トレンド存在確認
    2. +DI > -DI (BUY) / -DI > +DI (SELL) → 方向判定
    3. EMA9 > EMA21 > EMA50 (BUY) → パーフェクトオーダー（厳格）
    4. 前1-3本のいずれかで価格がEMA9-EMA21ゾーンにタッチ/侵入
    5. 前1-3本のいずれかでRSIがプルバック水準まで低下

  ■ STEP2: リバウンド確認（現在足）
    6. 現在足が陽線(BUY)/陰線(SELL) — リバウンド開始
    7. 現在足Close > EMA9 (BUY) / Close < EMA9 (SELL) — EMA回復
    8. HTF agreement != 逆方向

設計方針:
  - USD/JPY・EUR/USD両対応
  - ペア別パラメータ分離（将来チューニング対応）
  - ema_crossとの差別化: クロスイベントではなくプルバック検出
  - プルバック検出と確認足を時間的に分離（同一足矛盾を解消）
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class AdxTrendContinuation(StrategyBase):
    name = "adx_trend_continuation"
    mode = "daytrade"
    enabled = True

    # ══════════════════════════════════════════════════
    # ペア別パラメータ定数（将来チューニング対応）
    # ══════════════════════════════════════════════════

    # ── ADX閾値 ──
    ADX_THRES_JPY = 25          # USD/JPY: トレンド確認閾値
    ADX_THRES_EUR = 25          # EUR/USD: トレンド確認閾値

    # ── RSIプルバック検出 (前N本で確認) ──
    #   BUY: 前N本でRSI < RSI_PB_THRES (上昇トレンド中の一時低下)
    #   SELL: 前N本でRSI > (100 - RSI_PB_THRES)
    RSI_PB_THRES_JPY = 55       # BUY: 直近バーでRSI < 55 = プルバック発生
    RSI_PB_THRES_EUR = 55       # (上昇トレンド中RSI平均=65なので55未満は有意な低下)

    # ── 現在足RSI回復確認 ──
    RSI_RECOVER_MIN_JPY = 45    # BUY: 現在RSI >= 45 (暴落中ではない)
    RSI_RECOVER_MIN_EUR = 45

    # ── プルバック検出ルックバック ──
    PB_LOOKBACK = 3             # 直近N本以内にプルバック発生

    # ── SL/TP ──
    SL_SWING_LOOKBACK = 8       # スイングロー/ハイ検出ルックバック
    SL_ATR_BUFFER = 0.3         # SL = スイング安値/高値 ± ATR×0.3
    TP_ATR_MULT = 2.5           # TP = ATR × 2.5
    MIN_RR = 1.5                # 最低リスクリワード比

    # ── 最大保持 ──
    MAX_HOLD_BARS = 12          # 12バー = 3時間 (15m足)

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── USD/JPY DISABLED: 15m足でのトレンドフォローはノイジー ──
        # BT結果: JPY 14t WR=50% EV=-0.719 (max_hold timeout多発)
        # EUR/USD: 14t WR=78.6% EV=+1.706 → EUR/USD専用で運用
        if ctx.is_jpy:
            return None

        # ── DataFrame十分性チェック ──
        _min_bars = max(self.SL_SWING_LOOKBACK, self.PB_LOOKBACK) + 3
        if ctx.df is None or len(ctx.df) < _min_bars:
            return None

        # ── ペア別パラメータ選択 ──
        _adx_thres = self.ADX_THRES_EUR
        _rsi_pb_thres = self.RSI_PB_THRES_EUR
        _rsi_recover = self.RSI_RECOVER_MIN_EUR

        # ═══════════════════════════════════════════════════
        # 条件1: ADX >= 閾値（トレンド存在確認）
        # ═══════════════════════════════════════════════════
        if ctx.adx < _adx_thres:
            return None

        # ═══════════════════════════════════════════════════
        # 条件2+3: 方向判定 + EMAパーフェクトオーダー
        # ═══════════════════════════════════════════════════
        _buy_direction = ctx.adx_pos > ctx.adx_neg
        _sell_direction = ctx.adx_neg > ctx.adx_pos

        _buy_perfect = ctx.ema9 > ctx.ema21 > ctx.ema50
        _sell_perfect = ctx.ema9 < ctx.ema21 < ctx.ema50

        _is_buy = _buy_direction and _buy_perfect
        _is_sell = _sell_direction and _sell_perfect

        if not _is_buy and not _is_sell:
            return None

        # ═══════════════════════════════════════════════════
        # 条件8: HTFハードフィルター（逆方向ブロック）
        # ═══════════════════════════════════════════════════
        _htf = ctx.htf or {}
        _agreement = _htf.get("agreement", "mixed")
        if _is_buy and _agreement == "bear":
            return None
        if _is_sell and _agreement == "bull":
            return None

        # ═══════════════════════════════════════════════════
        # STEP1: プルバック検出（前1-3本で確認）
        #   前N本のいずれかで:
        #     - 価格がEMA9-EMA21ゾーンにタッチ/侵入
        #     - RSIがプルバック水準まで低下
        # ═══════════════════════════════════════════════════
        _rsi_col = "rsi" if "rsi" in ctx.df.columns else None

        _pb_found = False
        _pb_rsi_val = 0.0
        _pb_price_val = 0.0

        for offset in range(1, self.PB_LOOKBACK + 1):
            idx = -(offset + 1)  # -2, -3, -4 (前1本, 前2本, 前3本)
            if abs(idx) > len(ctx.df):
                break
            _pb_bar = ctx.df.iloc[idx]
            _pb_rsi = float(_pb_bar[_rsi_col]) if _rsi_col else 50.0

            if _is_buy:
                _pb_low = float(_pb_bar["Low"])
                # EMA9ゾーンタッチ: Low <= EMA9 (価格がEMAまで下がった)
                _price_touched = _pb_low <= ctx.ema9
                # EMA21突き抜けすぎ防止
                _not_broken = _pb_low >= ctx.ema21 - ctx.atr * 0.5
                # RSIプルバック: RSI < 閾値
                _rsi_pulled = _pb_rsi < _rsi_pb_thres
            else:
                _pb_high = float(_pb_bar["High"])
                _price_touched = _pb_high >= ctx.ema9
                _not_broken = _pb_high <= ctx.ema21 + ctx.atr * 0.5
                _rsi_pulled = _pb_rsi > (100 - _rsi_pb_thres)  # > 45

            if _price_touched and _not_broken and _rsi_pulled:
                _pb_found = True
                _pb_rsi_val = _pb_rsi
                _pb_price_val = _pb_low if _is_buy else _pb_high
                break

        if not _pb_found:
            return None

        # ═══════════════════════════════════════════════════
        # STEP2: 現在足でリバウンド確認
        # ═══════════════════════════════════════════════════

        # ── 確認足: 陽線(BUY)/陰線(SELL) ──
        if _is_buy and ctx.entry <= ctx.open_price:
            return None  # 陰線 = リバウンド未確認
        if _is_sell and ctx.entry >= ctx.open_price:
            return None  # 陽線 = リバウンド未確認

        # ── 価格回復: Close > EMA9 (BUY) / Close < EMA9 (SELL) ──
        if _is_buy and ctx.entry <= ctx.ema9:
            return None  # EMA9未回復
        if _is_sell and ctx.entry >= ctx.ema9:
            return None  # EMA9未回復

        # ── RSI回復確認 ──
        _current_rsi = ctx.rsi
        if _is_buy and _current_rsi < _rsi_recover:
            return None  # RSI暴落中
        if _is_sell and _current_rsi > (100 - _rsi_recover):  # > 55
            return None

        # ═══════════════════════════════════════════════════
        # シグナル生成
        # ═══════════════════════════════════════════════════
        signal = "BUY" if _is_buy else "SELL"
        score = 4.5
        reasons = []

        # ── SL計算: スイングロー/ハイ - ATR×0.3バッファ ──
        _lookback = min(self.SL_SWING_LOOKBACK, len(ctx.df) - 1)
        if _is_buy:
            _swing_low = float(ctx.df["Low"].iloc[-_lookback:].min())
            sl = _swing_low - ctx.atr * self.SL_ATR_BUFFER
        else:
            _swing_high = float(ctx.df["High"].iloc[-_lookback:].max())
            sl = _swing_high + ctx.atr * self.SL_ATR_BUFFER

        # ── TP計算: ATR×2.5 (RR≥1.5保証) ──
        _sl_dist = abs(ctx.entry - sl)
        _tp_target = ctx.atr * self.TP_ATR_MULT
        _tp_min_rr = _sl_dist * self.MIN_RR
        _tp_dist = max(_tp_target, _tp_min_rr)

        if _is_buy:
            tp = ctx.entry + _tp_dist
        else:
            tp = ctx.entry - _tp_dist

        # ── RR最低保証チェック ──
        if _sl_dist <= 0 or _tp_dist / _sl_dist < self.MIN_RR:
            return None

        # ═══════════════════════════════════════════════════
        # Reasons & ボーナス
        # ═══════════════════════════════════════════════════
        _pair_label = "JPY" if ctx.is_jpy else "EUR"
        _rr = _tp_dist / _sl_dist if _sl_dist > 0 else 0

        reasons.append(
            f"✅ ADX TC {signal}: ADX={ctx.adx:.1f}≥{_adx_thres} "
            f"+DI={ctx.adx_pos:.1f} -DI={ctx.adx_neg:.1f} "
            f"(Wilder 1978 / Menkhoff 2012)"
        )
        reasons.append(
            f"✅ EMAパーフェクトオーダー: "
            f"EMA9={ctx.ema9:.3f} {'>' if _is_buy else '<'} "
            f"EMA21={ctx.ema21:.3f} {'>' if _is_buy else '<'} "
            f"EMA50={ctx.ema50:.3f}"
        )
        reasons.append(
            f"✅ プルバック検出: RSI={_pb_rsi_val:.1f}<{_rsi_pb_thres} "
            f"+ EMAゾーンタッチ({_pb_price_val:.3f}→EMA9={ctx.ema9:.3f})"
        )
        reasons.append(
            f"✅ リバウンド確認: Close={ctx.entry:.3f}>EMA9 "
            f"+ RSI回復={_current_rsi:.1f}≥{_rsi_recover}"
        )
        reasons.append(
            f"📊 RR={_rr:.1f} SL={sl:.3f} TP={tp:.3f} ({_pair_label})"
        )

        # ── ボーナス条件 ──

        # ADX強度ボーナス (≥35: 強トレンド)
        if ctx.adx >= 35:
            score += 0.5
            reasons.append(f"✅ 強トレンド(ADX={ctx.adx:.1f}≥35)")

        # HTF方向一致ボーナス
        if (_is_buy and _agreement == "bull") or \
           (_is_sell and _agreement == "bear"):
            score += 0.5
            reasons.append(f"✅ HTF方向一致({_agreement})")

        # EMA200方向一致ボーナス
        if (_is_buy and ctx.entry > ctx.ema200) or \
           (_is_sell and ctx.entry < ctx.ema200):
            score += 0.3
            reasons.append("✅ EMA200方向一致")

        # MACD-H方向一致ボーナス
        if (_is_buy and ctx.macdh > 0) or \
           (_is_sell and ctx.macdh < 0):
            score += 0.3
            reasons.append(f"✅ MACD-H方向一致({ctx.macdh:.4f})")

        # プルバック深度ボーナス: EMA21に近いほど良質
        _curr_low = float(ctx.df.iloc[-1]["Low"])
        _curr_high = float(ctx.df.iloc[-1]["High"])
        if _is_buy:
            _ema_spread = ctx.ema9 - ctx.ema21
            _pb_depth = (ctx.ema9 - _pb_price_val) / _ema_spread \
                if _ema_spread > 0 else 0
        else:
            _ema_spread = ctx.ema21 - ctx.ema9
            _pb_depth = (_pb_price_val - ctx.ema9) / _ema_spread \
                if _ema_spread > 0 else 0
        if _pb_depth >= 0.5:
            score += 0.3
            reasons.append(f"✅ 深いプルバック(depth={_pb_depth:.0%})")

        conf = int(min(85, 50 + score * 4))
        return Candidate(
            signal=signal, confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score
        )
