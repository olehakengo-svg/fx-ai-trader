"""
Squeeze Release Momentum (SRM-DT) — BB圧縮→解放のトレンド初動を捕捉

v3 (2026-04-08): Option D 検証結果に基づくフィルター最適化
  - 5段フィルター → 2段に削減 (N数確保 + OOS検証可能化)
  - 対象ペア: EUR/USD, GBP/USD のみ (USD/JPY: WR=50% 摩擦負け → 除外)
  - BT結果: 24t WR=66.7% EV=+0.45 Sharpe=4.95 PF=1.86

学術的根拠:
  - Bollinger (2001): Bandwidth squeeze → volatility expansion cycle
  - KSB (1H WR=50% +483pip) の成功原理を 15m足に適用

設計経緯:
  v1 (5段フィルター): N=4 → 統計検証不能, 発火率 0.03t/pair-day
  v2 (パラメータ緩和): N=5 → 依然不足, WFO/MC算出不可
  v3 (2段フィルター): N=24 → WFO/MC算出可能, 発火率 6.0x改善
    削除フィルター: body_ratio, MACD-H, ADX, HTF, freshness
    保持フィルター: squeeze_bars≥3 + BB拡大 + bbpb方向 + 陽陰線確認
    除外ペア: USD/JPY (WR=50%→摩擦込み負EV, BEV=53%を下回る)

  Option C (SRM-1H) は WR=10% で即却下。
  BB幅拡大トリガーは1H足では過度に反応し偽シグナル大量発生。
  1H足でのSQUEEZE捕捉は KSB (Keltner二重エンベロープ) が必要条件。

MR戦略ではないため:
  - _RANGE_MR_STRATEGIES に含めない
  - BB_mid TP / SL widening / RR floor 0.8 の対象外
  - Profit Extender / Pyramiding 完全対応

SL/TP:
  SL = Swing H/L (8本) ± ATR×0.3, max ATR×1.5, min ATR×0.8
  TP = ATR×2.5 (MIN_RR=1.5 保証)
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class SqueezeReleaseMomentum(StrategyBase):
    name = "squeeze_release_momentum"
    mode = "daytrade"
    enabled = True

    # ══════════════════════════════════════════════════
    # パラメータ定数
    # ══════════════════════════════════════════════════

    # ── Pre-condition: SQUEEZE蓄積 ──
    MIN_SQUEEZE_BARS = 3          # 15m × 3 = 45分以上の圧縮
    MAX_SQUEEZE_BARS = 40         # デッドマーケット排除

    # ── Trigger: BB Release + bbpb方向 ──
    BBPB_BUY_THRES = 0.75        # BB上方離脱
    BBPB_SELL_THRES = 0.25       # BB下方離脱

    # ── SL/TP ──
    SL_SWING_LOOKBACK = 8
    SL_ATR_BUFFER = 0.3
    SL_ATR_MAX = 1.5
    SL_ATR_MIN = 0.8
    TP_ATR_MULT = 2.5
    MIN_RR = 1.5

    # ── Session (流動性ゲート) ──
    ACTIVE_HOURS_START = 7        # UTC
    ACTIVE_HOURS_END = 17
    FRIDAY_BLOCK_AFTER = 13

    SCORE_BASE = 4.5

    # ── 対象ペア: EUR/USD, GBP/USD のみ ──
    # USD/JPY: BT WR=50% (14t), BEV=53% → 摩擦込み負EV確定 → 除外
    _ALLOWED_PAIRS = ("EURUSD", "GBPUSD")

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        """2段フィルターによるSqueeze Release Momentum検出。"""

        # ══════════════════════════════════════
        # ペアフィルター: EUR/USD, GBP/USD のみ
        # ══════════════════════════════════════
        _sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        if _sym not in self._ALLOWED_PAIRS:
            return None

        # ── DataFrame十分性 ──
        if ctx.df is None or len(ctx.df) < 10:
            return None

        # ── セッションフィルター (流動性ゲート) ──
        if ctx.hour_utc < self.ACTIVE_HOURS_START or ctx.hour_utc >= self.ACTIVE_HOURS_END:
            return None
        if ctx.is_friday and ctx.hour_utc >= self.FRIDAY_BLOCK_AFTER:
            return None

        # ══════════════════════════════════════
        # FILTER 1: squeeze_bars >= 3
        # 45分以上の圧縮蓄積（エネルギー充填）
        # ══════════════════════════════════════
        _regime = ctx.regime or {}
        _squeeze_bars = _regime.get("squeeze_bars", 0)

        if _squeeze_bars < self.MIN_SQUEEZE_BARS:
            return None
        if _squeeze_bars > self.MAX_SQUEEZE_BARS:
            return None  # デッドマーケット

        # ══════════════════════════════════════
        # FILTER 2: BB拡大 + bbpb方向
        # BB幅が前足より拡大（Release開始）かつ
        # 価格がBB上端/下端に位置（方向確定）
        # ══════════════════════════════════════
        if len(ctx.df) < 2:
            return None
        _prev = ctx.df.iloc[-2]
        _prev_bb_width = float(_prev.get("bb_width", 0))

        # Release判定: BB幅が前足より拡大
        if _prev_bb_width <= 0 or ctx.bb_width < _prev_bb_width:
            return None  # BB未拡大 → Release未発生

        # 方向判定 (bbpb)
        _is_buy = ctx.bbpb > self.BBPB_BUY_THRES
        _is_sell = ctx.bbpb < self.BBPB_SELL_THRES
        if not _is_buy and not _is_sell:
            return None

        # 陽線/陰線確認（最低限のノイズ排除）
        if _is_buy and ctx.entry <= ctx.open_price:
            return None  # BUYなのに陰線
        if _is_sell and ctx.entry >= ctx.open_price:
            return None  # SELLなのに陽線

        # ══════════════════════════════════════
        # SL計算: Swing H/L ± ATR×0.3
        # ══════════════════════════════════════
        signal = "BUY" if _is_buy else "SELL"
        _lookback = min(self.SL_SWING_LOOKBACK, len(ctx.df) - 1)

        if _is_buy:
            _swing = float(ctx.df["Low"].iloc[-_lookback:].min())
            sl = _swing - ctx.atr * self.SL_ATR_BUFFER
        else:
            _swing = float(ctx.df["High"].iloc[-_lookback:].max())
            sl = _swing + ctx.atr * self.SL_ATR_BUFFER

        # SLキャップ: ATR×0.8 ≤ SL距離 ≤ ATR×1.5
        _sl_dist = abs(ctx.entry - sl)
        _sl_max = ctx.atr * self.SL_ATR_MAX
        _sl_min = ctx.atr * self.SL_ATR_MIN
        if _sl_dist > _sl_max:
            sl = ctx.entry - _sl_max if _is_buy else ctx.entry + _sl_max
            _sl_dist = _sl_max
        elif _sl_dist < _sl_min:
            sl = ctx.entry - _sl_min if _is_buy else ctx.entry + _sl_min
            _sl_dist = _sl_min

        # ── TP計算: ATR×2.5 (MIN_RR保証) ──
        _tp_target = ctx.atr * self.TP_ATR_MULT
        _tp_min_rr = _sl_dist * self.MIN_RR
        _tp_dist = max(_tp_target, _tp_min_rr)
        tp = ctx.entry + _tp_dist if _is_buy else ctx.entry - _tp_dist

        _rr = _tp_dist / _sl_dist if _sl_dist > 0 else 0
        if _rr < self.MIN_RR:
            return None

        # ══════════════════════════════════════
        # Reasons (テレメトリ)
        # ══════════════════════════════════════
        _bb_pct = _regime.get("bb_width_pct", 50.0)
        _prec = 3 if ctx.is_jpy else 5

        reasons = [
            f"✅ SRM {signal}: squeeze_bars={_squeeze_bars} "
            f"(≥{self.MIN_SQUEEZE_BARS}) bb_pct={_bb_pct:.1f}",
            f"✅ BB Release: width {_prev_bb_width:.{_prec}f}"
            f"→{ctx.bb_width:.{_prec}f} (拡大) bbpb={ctx.bbpb:.2f}",
            f"📊 RR={_rr:.1f} SL={sl:.{_prec}f} TP={tp:.{_prec}f} "
            f"(Swing={'L' if _is_buy else 'H'}={_swing:.{_prec}f})",
        ]

        # ── スコアボーナス ──
        score = self.SCORE_BASE

        # squeeze_bars 長期蓄積 (6本=1.5h以上)
        if _squeeze_bars >= 6:
            score += 0.5
            reasons.append(f"✅ 長期圧縮({_squeeze_bars}本≥6)")

        # EMA200方向一致
        if (_is_buy and ctx.entry > ctx.ema200) or \
           (_is_sell and ctx.entry < ctx.ema200):
            score += 0.3
            reasons.append("✅ EMA200方向一致")

        # EMA整列 (パーフェクトオーダー)
        if _is_buy and ctx.ema9 > ctx.ema21 > ctx.ema50:
            score += 0.3
            reasons.append("✅ EMA PO (9>21>50)")
        elif _is_sell and ctx.ema9 < ctx.ema21 < ctx.ema50:
            score += 0.3
            reasons.append("✅ EMA PO (9<21<50)")

        conf = int(min(80, 45 + score * 4))

        return Candidate(
            signal=signal,
            confidence=conf,
            sl=sl,
            tp=tp,
            reasons=reasons,
            entry_type=self.name,
            score=score,
        )
