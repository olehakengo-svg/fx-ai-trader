"""
Donchian Momentum Breakout (DMB) — 1H足多日レンジ突破

学術的根拠:
  - Dennis & Eckhardt (1983): タートルズのドンチアンブレイクアウト戦略
  - Brock, Lakonishok & LeBaron (1992, JoF): チャネルブレイクアウトの統計的有意性
  - Schulmeister (2009): FXテクニカルルールの1H以上TFでの有効性
  - Hurst (1951): チャネル幅がATR×1.5以上の場合、偽ブレイク率低下

戦略コンセプト:
  48本(≈2営業日)のドンチアンチャネルを突破する「レンジブレイクアウト」を狙う。
  KSBが「ボラ圧縮→爆発(初動)」を狙うのに対し、DMBは「多日レンジの明確な壁突破」を狙う。

  USD/JPYの優位性:
  - 日米金利差やマクロ要因で「数日にわたる明確なトレンド」が発生しやすい
  - 48期間レンジの壁は機関投資家のストップロスが集中 → 突破後にカスケードが発生
  - KSBではWR=33.3%で不採用だったJPYでも、異なるアプローチで再評価

エントリーロジック:
  ■ レンジ確立 (前N本):
    1. Donchian48レンジ幅 ≥ ATR × MIN_RANGE_ATR_MULT (ノイズ排除)
    2. 前足Close = レンジ内 (新鮮なブレイク確認)

  ■ ブレイクアウト (現在足):
    3. Close > 前足don_high48 (BUY) or Close < 前足don_low48 (SELL)
    4. ブレイク足の実体 ≥ バーレンジの BODY_RATIO_MIN
    5. ブレイク足が方向一致の陽線/陰線

  ■ モメンタム確認:
    6. +DI > -DI (BUY) or -DI > +DI (SELL) — 方向性確認
    7. ADX ≥ ADX_MIN or ADX前足比+2.0上昇 (トレンド開始)
    8. MACD-H: 方向一致

  ■ HTFフィルター (実4H+1Dデータ使用):
    9. htf agreement != 逆方向

SL/TP:
  SL: 前足ドンチアン中央 (don_mid48) - ATR×0.3、最大ATR×SL_MAX_ATR_MULT(1.5)で制限
  TP: ATR(14) × TP_ATR_MULT (50pip+目標)
  BE: TP×BE_TRIGGER_PCT到達でSL→BE+1pip
  Trailing: BE後、直近N本の安値/高値 - ATR×TRAIL_ATR_MULT で追従
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class DonchianMomentumBreakout(StrategyBase):
    name = "donchian_momentum_breakout"
    mode = "hourly"
    enabled = True

    # ══════════════════════════════════════════════════
    # ペア別パラメータ定数
    # ══════════════════════════════════════════════════

    # ── レンジ確立 ──
    MIN_RANGE_ATR_MULT = 1.5    # ドンチアンレンジ ≥ ATR×1.5 (ノイズ排除)

    # ── ブレイク品質 ──
    BODY_RATIO_MIN = 0.40       # ブレイク足の実体 ≥ バーレンジの40%

    # ── ADX / DI ──
    ADX_MIN_JPY = 18            # USD/JPY BUY: トレンド確認
    ADX_MIN_EUR = 18            # EUR/USD: トレンド確認
    ADX_MIN_JPY_SELL = 25       # USD/JPY SELL: 金利差逆行のため厳格化
    ADX_RISE_THRESHOLD = 2.0    # ADX前足比で+2以上 = トレンド開始

    # ── SL/TP ──
    SL_MAX_ATR_MULT = 1.5       # SL最大距離 = ATR × 1.5
    TP_ATR_MULT_JPY = 3.0       # TP = ATR × 3.0
    TP_ATR_MULT_EUR = 3.0       # TP = ATR × 3.0
    MIN_RR = 1.5                # 最低リスクリワード比

    # ── BE / トレーリング ──
    BE_TRIGGER_PCT = 0.50       # TP50%到達でSL→BE+1pip
    TRAIL_ATR_MULT = 1.5        # トレーリング: 直近高値/安値 - ATR×1.5

    # ── 最大保持 ──
    MAX_HOLD_BARS = 24          # 24時間

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── DataFrame十分性チェック ──
        if ctx.df is None or len(ctx.df) < 52:
            return None

        # ── ドンチアン列の存在チェック ──
        if "don_high48" not in ctx.df.columns:
            return None
        if "don_low48" not in ctx.df.columns:
            return None

        # ── ペア別パラメータ選択 ──
        if ctx.is_jpy:
            _adx_min = self.ADX_MIN_JPY
            _tp_mult = self.TP_ATR_MULT_JPY
        else:
            _adx_min = self.ADX_MIN_EUR
            _tp_mult = self.TP_ATR_MULT_EUR

        # ═══════════════════════════════════════════════════
        # 条件1: レンジ確立 — ドンチアン48レンジ幅チェック
        # ═══════════════════════════════════════════════════
        # 前足のドンチアン値を使用（現在足のHigh/Lowは含まれない）
        _prev_don_high = float(ctx.df["don_high48"].iloc[-2])
        _prev_don_low = float(ctx.df["don_low48"].iloc[-2])
        _prev_don_mid = float(ctx.df["don_mid48"].iloc[-2])
        _don_range = _prev_don_high - _prev_don_low

        if _don_range < ctx.atr * self.MIN_RANGE_ATR_MULT:
            return None  # レンジが狭すぎる = ノイズ

        # ═══════════════════════════════════════════════════
        # 条件2-3: ブレイクアウト検出 — 現在足Closeが前足ドンチアンを突破
        # ═══════════════════════════════════════════════════
        _close = ctx.entry
        _open = ctx.open_price

        _is_buy = _close > _prev_don_high
        _is_sell = _close < _prev_don_low

        if not _is_buy and not _is_sell:
            return None  # レンジ内 → ブレイクなし

        # ── 新鮮さチェック: 前足がすでにブレイクしていないこと ──
        # 2本前のドンチアンと前足Closeを比較
        if len(ctx.df) >= 4:
            _prev2_don_high = float(ctx.df["don_high48"].iloc[-3])
            _prev2_don_low = float(ctx.df["don_low48"].iloc[-3])
            _prev_close = float(ctx.df["Close"].iloc[-2])

            if _is_buy and _prev_close > _prev2_don_high:
                return None  # 前足ですでにブレイク済み → 追っかけ
            if _is_sell and _prev_close < _prev2_don_low:
                return None

        # ═══════════════════════════════════════════════════
        # 条件★: USD/JPY SELL非対称フィルター
        # ドル円ショートは金利差に逆行 → 強モメンタム時のみ許可
        # ═══════════════════════════════════════════════════
        if ctx.is_jpy and _is_sell:
            # ADX≥25必須 (BUY方向の18より厳格)
            if ctx.adx < self.ADX_MIN_JPY_SELL:
                return None
            # 1D EMA50が明確に下向き (HTF経由)
            _htf_pre = ctx.htf or {}
            if not _htf_pre.get("d1_ema50_falling", False):
                return None

        # ═══════════════════════════════════════════════════
        # 条件4-5: ブレイク足の品質
        # ═══════════════════════════════════════════════════
        _bar_range = float(ctx.df.iloc[-1]["High"]) - float(ctx.df.iloc[-1]["Low"])
        _body = abs(_close - _open)
        _body_ratio = _body / _bar_range if _bar_range > 0 else 0

        if _body_ratio < self.BODY_RATIO_MIN:
            return None

        # 方向確認: ブレイク足が陽線(BUY)/陰線(SELL)
        if _is_buy and _close <= _open:
            return None
        if _is_sell and _close >= _open:
            return None

        # ═══════════════════════════════════════════════════
        # 条件6: DI方向性確認 (Wilder 1978)
        # ═══════════════════════════════════════════════════
        if _is_buy and ctx.adx_pos <= ctx.adx_neg:
            return None  # +DI ≤ -DI → 買い圧力不足
        if _is_sell and ctx.adx_neg <= ctx.adx_pos:
            return None  # -DI ≤ +DI → 売り圧力不足

        # ═══════════════════════════════════════════════════
        # 条件7: ADXトレンド確認
        # ═══════════════════════════════════════════════════
        _adx_rising = False
        if len(ctx.df) >= 2 and "adx" in ctx.df.columns:
            _prev_adx = float(ctx.df["adx"].iloc[-2])
            _adx_rising = (ctx.adx - _prev_adx) >= self.ADX_RISE_THRESHOLD

        if ctx.adx < _adx_min and not _adx_rising:
            return None

        # ═══════════════════════════════════════════════════
        # 条件8: MACD-H方向確認
        # ═══════════════════════════════════════════════════
        if _is_buy and ctx.macdh <= 0:
            return None
        if _is_sell and ctx.macdh >= 0:
            return None

        # ═══════════════════════════════════════════════════
        # 条件9: HTFハードフィルター
        # ═══════════════════════════════════════════════════
        _htf = ctx.htf or {}
        _agreement = _htf.get("agreement", "mixed")
        if _is_buy and _agreement == "bear":
            return None
        if _is_sell and _agreement == "bull":
            return None

        # ═══════════════════════════════════════════════════
        # シグナル生成
        # ═══════════════════════════════════════════════════
        signal = "BUY" if _is_buy else "SELL"
        score = 5.0  # 1H戦略基本スコア
        reasons = []

        # ── SL: ドンチアン中央 (don_mid48) ± ATRバッファ、ATR×1.5で制限 ──
        # ドンチアン中央 = レンジの自然な無効化ポイント
        _max_sl_dist = ctx.atr * self.SL_MAX_ATR_MULT
        if _is_buy:
            _sl_raw = _prev_don_mid - ctx.atr * 0.3
            sl = max(_sl_raw, ctx.entry - _max_sl_dist)
        else:
            _sl_raw = _prev_don_mid + ctx.atr * 0.3
            sl = min(_sl_raw, ctx.entry + _max_sl_dist)

        # ── TP: ATR × TP_MULT ──
        _sl_dist = abs(ctx.entry - sl)
        _tp_target = ctx.atr * _tp_mult
        _tp_min_rr = _sl_dist * self.MIN_RR
        _tp_dist = max(_tp_target, _tp_min_rr)

        if _is_buy:
            tp = ctx.entry + _tp_dist
        else:
            tp = ctx.entry - _tp_dist

        # ── RR最低保証 ──
        if _sl_dist <= 0 or _tp_dist / _sl_dist < self.MIN_RR:
            return None

        # ═══════════════════════════════════════════════════
        # Reasons & ボーナス
        # ═══════════════════════════════════════════════════
        _pair_label = "JPY" if ctx.is_jpy else "EUR"
        _rr = _tp_dist / _sl_dist if _sl_dist > 0 else 0
        _sl_pip = _sl_dist * ctx.pip_mult
        _tp_pip = _tp_dist * ctx.pip_mult
        _range_pip = _don_range * ctx.pip_mult

        reasons.append(
            f"✅ DMB {signal}: Don48({_range_pip:.0f}pip)ブレイク "
            f"(Dennis & Eckhardt 1983 / Brock 1992)"
        )
        reasons.append(
            f"✅ ブレイク: Close={ctx.entry:.3f} "
            f"{'>' if _is_buy else '<'} "
            f"Don{'High' if _is_buy else 'Low'}="
            f"{_prev_don_high if _is_buy else _prev_don_low:.3f}"
        )
        reasons.append(
            f"✅ 実体比率: {_body_ratio:.0%}≥{self.BODY_RATIO_MIN:.0%}"
        )
        reasons.append(
            f"✅ DI方向一致: +DI={ctx.adx_pos:.1f} "
            f"{'>' if _is_buy else '<'} "
            f"-DI={ctx.adx_neg:.1f}"
        )
        reasons.append(
            f"📊 RR={_rr:.1f} SL={_sl_pip:.1f}pip TP={_tp_pip:.1f}pip ({_pair_label})"
        )

        # ── ボーナス条件 ──

        # EMA200方向一致ボーナス / ペナルティ
        _ema200_aligned = True
        if _is_buy and ctx.entry < ctx.ema200:
            _ema200_aligned = False
        if _is_sell and ctx.entry > ctx.ema200:
            _ema200_aligned = False

        if _ema200_aligned:
            score += 0.3
            reasons.append("✅ EMA200方向一致")
        else:
            score -= 0.3
            reasons.append("⚠️ EMA200逆方向 (ペナルティ)")

        # ADX上昇ボーナス
        if _adx_rising:
            score += 0.5
            reasons.append(f"✅ ADX急上昇(+{ctx.adx - _prev_adx:.1f})")

        # HTF方向一致ボーナス
        if (_is_buy and _agreement == "bull") or \
           (_is_sell and _agreement == "bear"):
            score += 0.5
            reasons.append(f"✅ HTF方向一致({_agreement})")

        # EMAパーフェクトオーダーボーナス
        if _is_buy and ctx.ema9 > ctx.ema21 > ctx.ema50:
            score += 0.3
            reasons.append("✅ EMAパーフェクトオーダー(9>21>50)")
        elif _is_sell and ctx.ema9 < ctx.ema21 < ctx.ema50:
            score += 0.3
            reasons.append("✅ EMAパーフェクトオーダー(9<21<50)")

        # 広レンジボーナス: レンジ ≥ ATR×3.0 = 機関のストップが集中
        if _don_range >= ctx.atr * 3.0:
            score += 0.5
            reasons.append(f"✅ 広レンジ({_range_pip:.0f}pip≥ATR×3) — ストップカスケード期待")

        # 高RRボーナス
        if _rr >= 2.5:
            score += 0.3
            reasons.append(f"✅ 高RR({_rr:.1f}≥2.5)")

        # MACD-H加速ボーナス
        if _is_buy and ctx.macdh > ctx.macdh_prev:
            score += 0.2
            reasons.append("✅ MACD-H加速(拡大中)")
        elif _is_sell and ctx.macdh < ctx.macdh_prev:
            score += 0.2
            reasons.append("✅ MACD-H加速(縮小中)")

        conf = int(min(90, 50 + score * 4))
        return Candidate(
            signal=signal, confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score
        )
