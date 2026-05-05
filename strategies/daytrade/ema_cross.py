"""EMA Cross Retest — リテスト確認型EMAクロス (15m足)

Hardened v2 (2026-04-05):
  - ADX趨勢フィルター: (1H ADX ≥ 22) OR (15m ADX ≥ 25 & 上昇中)
  - HTFパーフェクトオーダー: クロス方向と4H/1D EMA配列の完全一致必須
  - レンジ相場での発火を物理的にブロック (本番5日 WR=32% → 改善)

References:
  - Wilder 1978: ADX ≥ 25 = トレンド確認閾値
  - Menkhoff 2012: 上位足トレンドとの一致がFX収益性を決定
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional
import logging
import os

logger = logging.getLogger("ema_cross")


class EmaCross(StrategyBase):
    name = "ema_cross"
    mode = "daytrade"
    strategy_type = "trend"   # v10: trend-follow formula is structurally correct
                              # (the bug was daytrade-layer override, now fixed in app.py L2772)

    # ── チューナブルパラメータ ──
    adx_floor = 15         # 15m ADX 絶対最低ライン (完全レンジ排除)
    adx_min_15m = 25       # 15m ADX 閾値（上昇要件付き, 旧20→25厳格化）
    adx_min_1h = 22        # 1H ADX 閾値 (リサンプリング算出)
    cross_window = 8       # クロス検出ウィンドウ（本数）
    pullback_min = 0.3     # ATR倍率
    ema_score_threshold = 0.30  # EMAスコア閾値
    rsi_buy_max = 70
    rsi_sell_min = 30
    htf_score_threshold = 0.6  # HTFパーフェクトオーダー代替閾値
    _v2_dedup_state: set[tuple[str, str, str]] = set()

    @classmethod
    def reset_dedup_state(cls):
        cls._v2_dedup_state.clear()

    def _redesign_v2_enabled(self) -> bool:
        return os.environ.get("EMA_CROSS_REDESIGN_V2") == "1"

    # ── 1H ADX算出 ──────────────────────────────────

    def _compute_1h_adx(self, df_15m):
        """15m DataFrameから1H ADXを算出（リサンプリング + ta.ADXIndicator）。
        Returns: float or None
        """
        try:
            from ta.trend import ADXIndicator
            df_1h = df_15m.resample('1h').agg({
                'Open': 'first', 'High': 'max', 'Low': 'min',
                'Close': 'last',
            }).dropna()
            if len(df_1h) < 20:
                return None
            adx_ind = ADXIndicator(df_1h['High'], df_1h['Low'], df_1h['Close'], window=14)
            adx_vals = adx_ind.adx()
            if adx_vals is None or len(adx_vals) == 0:
                return None
            val = float(adx_vals.iloc[-1])
            if val != val:  # NaN check
                return None
            return val
        except Exception as e:
            logger.debug("[EmaCross] 1H ADX計算失敗: %s", e)
            return None

    # ── ADX趨勢フィルター ──────────────────────────

    def _check_adx_trend_filter(self, ctx):
        """
        ADX趨勢フィルター (Wilder 1978 強化版):
        条件A: 1H ADX ≥ 22 — 上位足がトレンド確認済み
        条件B: 15m ADX ≥ 25 かつ上昇中 — 15mでトレンド明確化
        いずれかが真ならOK。15m ADX < 15 は無条件ブロック。
        Returns: (passed: bool, reason: str)
        """
        # 絶対最低ライン: 15m ADX < 15 = 完全レンジ → 即ブロック
        if ctx.adx < self.adx_floor:
            return False, "15m ADX={:.0f}<{}: 完全レンジ".format(ctx.adx, self.adx_floor)

        # 条件B: 15m ADX ≥ 25 かつ上昇中
        if ctx.adx >= self.adx_min_15m:
            if ctx.df is not None and "adx" in ctx.df.columns and len(ctx.df) >= 4:
                _adx_prev = float(ctx.df["adx"].iloc[-4])
                if ctx.adx > _adx_prev:
                    return True, "15m ADX={:.0f}>={}+rising({}>{:.0f})".format(
                        ctx.adx, self.adx_min_15m, int(ctx.adx), _adx_prev)
            # スロープ判定不能だが ADX >= 30 なら強トレンド → 無条件通過
            if ctx.adx >= 30:
                return True, "15m ADX={:.0f}>=30: 強トレンド".format(ctx.adx)

        # 条件A: 1H ADX ≥ 22
        if ctx.df is not None and len(ctx.df) >= 60:
            _adx_1h = self._compute_1h_adx(ctx.df)
            if _adx_1h is not None and _adx_1h >= self.adx_min_1h:
                return True, "1H ADX={:.0f}>={}".format(_adx_1h, self.adx_min_1h)

        return False, "ADX不通過(15m={:.0f}, 1H=N/A)".format(ctx.adx)

    # ── HTFパーフェクトオーダー整合 ──────────────────

    def _check_htf_perfect_order(self, ctx, direction):
        """
        4H + 1D 方向整合チェック (EMAパーフェクトオーダー重視):

        Case A (1Dデータあり — 本番/BT後半):
          - agreement がクロス方向一致必須 (bull=BUY, bear=SELL, mixed不可)
          - 4H or 1D いずれかが score >= 0.6 (強アライメント)
        Case B (1Dデータ不足 — BT前半):
          - 4H 単独で score >= 0.6 ならOK
        Returns: (passed: bool, reason: str)
        """
        htf = ctx.htf
        if not htf:
            return False, "HTFデータなし"

        agreement = htf.get("agreement", "mixed")
        h4 = htf.get("h4", {})
        d1 = htf.get("d1", {})
        h4_sc = h4.get("score", 0)
        d1_sc = d1.get("score", 0)
        _d1_lbl = d1.get("label", "")
        d1_available = "データ不足" not in _d1_lbl and "計算失敗" not in _d1_lbl

        _thr = self.htf_score_threshold  # 0.6

        if direction == "BUY":
            if d1_available:
                # Case A: full HTF — agreement must be "bull"
                if agreement != "bull":
                    return False, "HTF非bull({}): BUYブロック".format(agreement)
                if h4_sc >= _thr or d1_sc >= _thr:
                    return True, "HTF BUY: 4H({:.1f})+1D({:.1f})".format(h4_sc, d1_sc)
                return False, "HTF弱BUY(4H={:.1f} 1D={:.1f})".format(h4_sc, d1_sc)
            else:
                # Case B: d1 unavailable — h4 only
                if h4_sc >= _thr:
                    return True, "HTF BUY(4H): {:.1f}".format(h4_sc)
                return False, "HTF BUY不足(4H={:.1f})".format(h4_sc)

        elif direction == "SELL":
            if d1_available:
                if agreement != "bear":
                    return False, "HTF非bear({}): SELLブロック".format(agreement)
                if h4_sc <= -_thr or d1_sc <= -_thr:
                    return True, "HTF SELL: 4H({:.1f})+1D({:.1f})".format(h4_sc, d1_sc)
                return False, "HTF弱SELL(4H={:.1f} 1D={:.1f})".format(h4_sc, d1_sc)
            else:
                if h4_sc <= -_thr:
                    return True, "HTF SELL(4H): {:.1f}".format(h4_sc)
                return False, "HTF SELL不足(4H={:.1f})".format(h4_sc)

        return False, "unknown direction"

    # ── メイン評価 ──────────────────────────────────

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        _redesign_v2 = self._redesign_v2_enabled()

        # ═══ Phase 1: ADX趨勢ハードフィルター ═══
        _adx_ok, _adx_reason = self._check_adx_trend_filter(ctx)
        if not _adx_ok:
            return None

        if ctx.df is None or len(ctx.df) < 10:
            return None
        if _redesign_v2:
            if len(ctx.df) < 11:
                return None
            if not ctx.backtest_mode and ctx.bar_time is None:
                return None
            _signal_df = ctx.df.iloc[:-1]
            _signal_row = _signal_df.iloc[-1]
            _signal_bar_time = getattr(_signal_row, "name", None)
            _entry = float(_signal_row["Close"])
            _open_price = float(_signal_row["Open"])
            _atr = float(_signal_row.get("atr", ctx.atr))
            _atr7 = float(_signal_row.get("atr7", ctx.atr7))
            _ema9 = float(_signal_row.get("ema9", ctx.ema9))
            _ema21 = float(_signal_row.get("ema21", ctx.ema21))
            _macdh = float(_signal_row.get("macd_hist", ctx.macdh))
            _rsi = float(_signal_row.get("rsi", ctx.rsi))
            _ema_score = (_ema9 - _ema21) / max(_atr, 1e-8)
        else:
            _signal_df = ctx.df
            _signal_bar_time = None
            _entry = ctx.entry
            _open_price = ctx.open_price
            _atr = ctx.atr
            _atr7 = ctx.atr7
            _ema9 = ctx.ema9
            _ema21 = ctx.ema21
            _macdh = ctx.macdh
            _rsi = ctx.rsi
            _ema_score = ctx.ema_score if ctx.ema_score != 0.0 else (ctx.ema9 - ctx.ema21) / max(ctx.atr, 1e-8)

        signal = None
        score = 0.0
        reasons = []

        # (1) 直近N本以内にEMAクロスが発生したか
        _cross_dir = None
        _cross_bar = None
        for _cb in range(2, min(self.cross_window + 1, len(_signal_df))):
            _e9p = float(_signal_df["ema9"].iloc[-_cb - 1])
            _e21p = float(_signal_df["ema21"].iloc[-_cb - 1])
            _e9c = float(_signal_df["ema9"].iloc[-_cb])
            _e21c = float(_signal_df["ema21"].iloc[-_cb])
            if _e9p <= _e21p and _e9c > _e21c:
                _cross_dir = "BUY"
                _cross_bar = _cb
            elif _e9p >= _e21p and _e9c < _e21c:
                _cross_dir = "SELL"
                _cross_bar = _cb
                break

        if not _cross_dir or not _cross_bar:
            return None

        # ═══ Phase 2: HTFパーフェクトオーダー整合チェック ═══
        _htf_ok, _htf_reason = self._check_htf_perfect_order(ctx, _cross_dir)
        if not _htf_ok:
            return None

        # (2) プルバック確認
        if _cross_dir == "BUY":
            _pb_low = min(float(_signal_df["Low"].iloc[-j]) for j in range(1, _cross_bar))
            _pullback_depth = (float(_signal_df["High"].iloc[-_cross_bar]) - _pb_low) / max(_atr, 1e-8)
            _pullback_ok = _pullback_depth >= self.pullback_min and _entry > _ema21
        else:
            _pb_high = max(float(_signal_df["High"].iloc[-j]) for j in range(1, _cross_bar))
            _pullback_depth = (_pb_high - float(_signal_df["Low"].iloc[-_cross_bar])) / max(_atr, 1e-8)
            _pullback_ok = _pullback_depth >= self.pullback_min and _entry < _ema21

        if not _pullback_ok:
            return None

        # (3) 方向再確認 + エントリー条件
        _candle_bull = _entry > _open_price
        _candle_bear = _entry < _open_price
        _rsi_ok_buy = _rsi < self.rsi_buy_max
        _rsi_ok_sell = _rsi > self.rsi_sell_min

        # ADXボーナス（20を基準にスコア加算、max 0.8）
        _adx_bonus = max(0, min((ctx.adx - 20) * 0.03, 0.8))

        if (_cross_dir == "BUY" and _ema9 > _ema21 and _candle_bull
                and _macdh > 0 and _rsi_ok_buy and _ema_score > self.ema_score_threshold):
            signal = "BUY"
            score = 3.5 + _adx_bonus
            reasons.append("✅ EMAクロスリテスト: 9/21 GC {}本前, PB={:.1f}ATR".format(
                _cross_bar, _pullback_depth))
            reasons.append("✅ ADXトレンド: {}".format(_adx_reason))
            reasons.append("✅ {}".format(_htf_reason))
            reasons.append("✅ 5条件: ADX({:.0f}), MACD+, RSI({:.0f}), 陽線, EMA維持".format(
                ctx.adx, _rsi))
            tp = ctx.entry + _atr7 * 2.0
            sl = ctx.entry - _atr7 * 1.0

        elif (_cross_dir == "SELL" and _ema9 < _ema21 and _candle_bear
                and _macdh < 0 and _rsi_ok_sell and _ema_score < -self.ema_score_threshold):
            signal = "SELL"
            score = 3.5 + _adx_bonus
            reasons.append("✅ EMAクロスリテスト: 9/21 DC {}本前, PB={:.1f}ATR".format(
                _cross_bar, _pullback_depth))
            reasons.append("✅ ADXトレンド: {}".format(_adx_reason))
            reasons.append("✅ {}".format(_htf_reason))
            reasons.append("✅ 5条件: ADX({:.0f}), MACD-, RSI({:.0f}), 陰線, EMA維持".format(
                ctx.adx, _rsi))
            tp = ctx.entry - _atr7 * 2.0
            sl = ctx.entry + _atr7 * 1.0

        if signal is None:
            return None
        if _redesign_v2:
            if not ctx.backtest_mode:
                _sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
                _key = (_sym, signal, str(_signal_bar_time))
                if _key in self._v2_dedup_state:
                    return None
                self._v2_dedup_state.add(_key)
            reasons.append(
                "✅ EMA_CROSS_REDESIGN_V2: signal_bar_time={} で確定し次バー約定".format(
                    _signal_bar_time
                )
            )

        conf = int(min(80, 45 + score * 4))
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)
