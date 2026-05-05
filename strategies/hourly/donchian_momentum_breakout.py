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
import os
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

    REDESIGN_V2_ENV = "DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2"
    _dedup_state: dict = {}

    @classmethod
    def reset_dedup_state(cls):
        cls._dedup_state.clear()

    def _redesign_v2_enabled(self) -> bool:
        return os.environ.get(self.REDESIGN_V2_ENV) == "1"

    def _breakout_buffer(self, ctx: SignalContext, atr: float) -> float:
        raw_spread = 0.015 if ctx.is_jpy else 0.00015
        try:
            session_spread = (ctx.session or {}).get("spread")
            if session_spread is not None:
                raw_spread = float(session_spread)
        except Exception:
            pass
        return max(raw_spread, atr * 0.05)

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        _v2 = self._redesign_v2_enabled()

        # ── DataFrame十分性チェック ──
        if ctx.df is None or len(ctx.df) < 52:
            return None
        if _v2 and len(ctx.df) < 53:
            return None
        if _v2 and not ctx.backtest_mode and ctx.bar_time is None:
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

        _signal_df = ctx.df
        _signal_pos = -2 if _v2 else -1
        _threshold_pos = -3 if _v2 else -2
        _fresh_prev_close_pos = -3 if _v2 else -2
        _fresh_threshold_pos = -4 if _v2 else -3
        _signal_row = _signal_df.iloc[_signal_pos]
        _signal_bar_id = None
        if _v2:
            try:
                _signal_bar_id = _signal_row.name
            except Exception:
                _signal_bar_id = ctx.bar_time

        _entry = float(_signal_row["Close"]) if _v2 else ctx.entry
        _open = float(_signal_row["Open"]) if _v2 else ctx.open_price
        _atr = float(_signal_row.get("atr", ctx.atr)) if _v2 else ctx.atr
        _adx = float(_signal_row.get("adx", ctx.adx)) if _v2 else ctx.adx
        _adx_pos = float(_signal_row.get("adx_pos", ctx.adx_pos)) if _v2 else ctx.adx_pos
        _adx_neg = float(_signal_row.get("adx_neg", ctx.adx_neg)) if _v2 else ctx.adx_neg
        _macdh = float(_signal_row.get("macd_hist", ctx.macdh)) if _v2 else ctx.macdh
        _ema9 = float(_signal_row.get("ema9", ctx.ema9)) if _v2 else ctx.ema9
        _ema21 = float(_signal_row.get("ema21", ctx.ema21)) if _v2 else ctx.ema21
        _ema50 = float(_signal_row.get("ema50", ctx.ema50)) if _v2 else ctx.ema50
        _ema200 = float(_signal_row.get("ema200", ctx.ema200)) if _v2 else ctx.ema200
        _prev_macdh = (
            float(_signal_df["macd_hist"].iloc[_signal_pos - 1])
            if "macd_hist" in _signal_df.columns and abs(_signal_pos - 1) <= len(_signal_df)
            else ctx.macdh_prev
        )

        if _atr <= 0:
            return None

        # ═══════════════════════════════════════════════════
        # 条件1: レンジ確立 — ドンチアン48レンジ幅チェック
        # ═══════════════════════════════════════════════════
        # V2では確定済みシグナル足の直前Donchian値を使用する。
        _prev_don_high = float(_signal_df["don_high48"].iloc[_threshold_pos])
        _prev_don_low = float(_signal_df["don_low48"].iloc[_threshold_pos])
        _prev_don_mid = float(_signal_df["don_mid48"].iloc[_threshold_pos])
        _don_range = _prev_don_high - _prev_don_low

        if _don_range < _atr * self.MIN_RANGE_ATR_MULT:
            return None  # レンジが狭すぎる = ノイズ

        # ═══════════════════════════════════════════════════
        # 条件2-3: ブレイクアウト検出 — 確定足Closeが直前Donchianを突破
        # ═══════════════════════════════════════════════════
        _close = _entry
        _buffer = self._breakout_buffer(ctx, _atr) if _v2 else 0.0

        _is_buy = _close > _prev_don_high + _buffer
        _is_sell = _close < _prev_don_low - _buffer

        if not _is_buy and not _is_sell:
            return None  # レンジ内 → ブレイクなし

        # ── 新鮮さチェック: 前足がすでにブレイクしていないこと ──
        # 2本前のドンチアンと前足Closeを比較
        if len(_signal_df) >= (5 if _v2 else 4):
            _prev2_don_high = float(_signal_df["don_high48"].iloc[_fresh_threshold_pos])
            _prev2_don_low = float(_signal_df["don_low48"].iloc[_fresh_threshold_pos])
            _prev_close = float(_signal_df["Close"].iloc[_fresh_prev_close_pos])

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
            if _adx < self.ADX_MIN_JPY_SELL:
                return None
            # 1D EMA50が明確に下向き (HTF経由)
            _htf_pre = ctx.htf or {}
            if not _htf_pre.get("d1_ema50_falling", False):
                return None

        # ═══════════════════════════════════════════════════
        # 条件4-5: ブレイク足の品質
        # ═══════════════════════════════════════════════════
        _bar_range = float(_signal_row["High"]) - float(_signal_row["Low"])
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
        if _is_buy and _adx_pos <= _adx_neg:
            return None  # +DI ≤ -DI → 買い圧力不足
        if _is_sell and _adx_neg <= _adx_pos:
            return None  # -DI ≤ +DI → 売り圧力不足

        # ═══════════════════════════════════════════════════
        # 条件7: ADXトレンド確認
        # ═══════════════════════════════════════════════════
        _adx_rising = False
        if len(_signal_df) >= 2 and "adx" in _signal_df.columns:
            _prev_adx = float(_signal_df["adx"].iloc[_signal_pos - 1])
            _adx_rising = (_adx - _prev_adx) >= self.ADX_RISE_THRESHOLD

        if _adx < _adx_min and not _adx_rising:
            return None

        # ═══════════════════════════════════════════════════
        # 条件8: MACD-H方向確認
        # ═══════════════════════════════════════════════════
        if _is_buy and _macdh <= 0:
            return None
        if _is_sell and _macdh >= 0:
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
        if _v2 and _signal_bar_id is not None:
            _dedup_key = (ctx.symbol, signal, _signal_bar_id, self.name)
            if self._dedup_state.get(_dedup_key):
                return None

        score = 5.0  # 1H戦略基本スコア
        reasons = []

        # ── SL: ドンチアン中央 (don_mid48) ± ATRバッファ、ATR×1.5で制限 ──
        # ドンチアン中央 = レンジの自然な無効化ポイント
        _max_sl_dist = _atr * self.SL_MAX_ATR_MULT
        if _is_buy:
            _sl_raw = _prev_don_mid - _atr * 0.3
            sl = max(_sl_raw, _entry - _max_sl_dist)
        else:
            _sl_raw = _prev_don_mid + _atr * 0.3
            sl = min(_sl_raw, _entry + _max_sl_dist)

        # ── TP: ATR × TP_MULT ──
        _sl_dist = abs(_entry - sl)
        _tp_target = _atr * _tp_mult
        _tp_min_rr = _sl_dist * self.MIN_RR
        _tp_dist = max(_tp_target, _tp_min_rr)

        if _is_buy:
            tp = _entry + _tp_dist
        else:
            tp = _entry - _tp_dist

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
            f"✅ ブレイク: Close={_entry:.3f} "
            f"{'>' if _is_buy else '<'} "
            f"Don{'High' if _is_buy else 'Low'}="
            f"{_prev_don_high if _is_buy else _prev_don_low:.3f}"
        )
        if _v2:
            reasons.append(
                f"✅ V2 closed-bar breakout + buffer={_buffer * ctx.pip_mult:.1f}pip"
            )
        reasons.append(
            f"✅ 実体比率: {_body_ratio:.0%}≥{self.BODY_RATIO_MIN:.0%}"
        )
        reasons.append(
            f"✅ DI方向一致: +DI={_adx_pos:.1f} "
            f"{'>' if _is_buy else '<'} "
            f"-DI={_adx_neg:.1f}"
        )
        reasons.append(
            f"📊 RR={_rr:.1f} SL={_sl_pip:.1f}pip TP={_tp_pip:.1f}pip ({_pair_label})"
        )

        # ── ボーナス条件 ──

        # EMA200方向一致ボーナス / ペナルティ
        _ema200_aligned = True
        if _is_buy and _entry < _ema200:
            _ema200_aligned = False
        if _is_sell and _entry > _ema200:
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
            reasons.append(f"✅ ADX急上昇(+{_adx - _prev_adx:.1f})")

        # HTF方向一致ボーナス
        if (_is_buy and _agreement == "bull") or \
           (_is_sell and _agreement == "bear"):
            score += 0.5
            reasons.append(f"✅ HTF方向一致({_agreement})")

        # EMAパーフェクトオーダーボーナス
        if _is_buy and _ema9 > _ema21 > _ema50:
            score += 0.3
            reasons.append("✅ EMAパーフェクトオーダー(9>21>50)")
        elif _is_sell and _ema9 < _ema21 < _ema50:
            score += 0.3
            reasons.append("✅ EMAパーフェクトオーダー(9<21<50)")

        # 広レンジボーナス: レンジ ≥ ATR×3.0 = 機関のストップが集中
        if _don_range >= _atr * 3.0:
            score += 0.5
            reasons.append(f"✅ 広レンジ({_range_pip:.0f}pip≥ATR×3) — ストップカスケード期待")

        # 高RRボーナス
        if _rr >= 2.5:
            score += 0.3
            reasons.append(f"✅ 高RR({_rr:.1f}≥2.5)")

        # MACD-H加速ボーナス
        if _is_buy and _macdh > _prev_macdh:
            score += 0.2
            reasons.append("✅ MACD-H加速(拡大中)")
        elif _is_sell and _macdh < _prev_macdh:
            score += 0.2
            reasons.append("✅ MACD-H加速(縮小中)")

        conf = int(min(90, 50 + score * 4))
        if _v2 and _signal_bar_id is not None:
            self._dedup_state[_dedup_key] = True
        return Candidate(
            signal=signal, confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score
        )
