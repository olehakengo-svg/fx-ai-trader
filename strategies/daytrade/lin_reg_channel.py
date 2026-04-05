"""
Linear Regression Channel (LRC) — 線形回帰チャネル戦略

数学的基盤:
  - Gauss-Markov定理: 最小二乗法推定量はBLUE（最良線形不偏推定量）
  - Ramaswamy & Ramaswami (1999): 回帰チャネルのプライスアクション収束特性
  - Lo, Mamaysky & Wang (2000): テクニカルパターンの統計的有意性実証

数学的定義:
  過去 n 期間の終値 {c_1, ..., c_n} に対し最小二乗法で回帰直線を算出:
    y = alpha + beta * x    (x = 0, 1, ..., n-1)
  残差 e_i = c_i - (alpha + beta * i) の標準偏差 sigma を計算し、
  チャネル上限/下限を定義:
    Upper = alpha + beta * x + k * sigma
    Lower = alpha + beta * x - k * sigma
  ここで k = 2 (2標準偏差 = 約95%の価格を包含)

戦略コンセプト（2モード）:

  ■ Mode A: Mean Reversion (チャネル内順張り)
    - チャネル下限(-2σ)にタッチ後、内側へ反発 → 上位トレンド方向への押し目買い
    - 前提: チャネル傾き β が一定閾値以上（明確なトレンド）
    - Entry: Close が lower band にタッチ(BUY) / upper band にタッチ(SELL)
    - 確認: 反転バー（陽線/陰線）+ Close がバンド内に回復
    - SL: バンド外側 + ATR×0.3
    - TP: 回帰線(中央) or 反対側バンド

  ■ Mode B: Breakout (チャネルブレイク順張り)
    - チャネル上限(+2σ)を明確なモメンタムで実体ブレイク → 加速を狙う
    - 前提: ADX ≥ 25（強モメンタム）
    - Entry: Close が upper band を超過(BUY) / lower band を下抜け(SELL)
    - 確認: ブレイク足の実体 ≥ バーレンジの30%
    - SL: 回帰線(中央) or 反対側バンド
    - TP: ブレイク方向に ATR×2.5

  BT分析に基づき、有効なモードのみを有効化する設計。

設計方針:
  - 全ペア + ゴールド対応
  - R² (決定係数) によるチャネル品質チェック: R² ≥ 0.70 でのみシグナル生成
  - 傾き正規化: beta/ATR でボラティリティ非依存の傾き評価
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional
import numpy as np


class LinRegChannel(StrategyBase):
    name = "lin_reg_channel"
    mode = "daytrade"
    enabled = True

    # ══════════════════════════════════════════════════
    # パラメータ定数
    # ══════════════════════════════════════════════════

    # ── チャネル計算 ──
    LR_PERIOD = 40              # 回帰期間（15m×40 = 10H ≈ 半営業日）
    SIGMA_MULT = 2.0            # チャネル幅: ±2σ
    MIN_R2 = 0.60               # 最低決定係数（チャネル品質）
    MIN_SLOPE_ATR = 0.02        # 最低傾き: |beta| / ATR ≥ 0.02（トレンド存在）

    # ── Mean Reversion モード ──
    MR_ENABLED = True           # Mean Reversion有効化
    MR_ZONE_PCT = 0.25          # チャネル下/上位25%をエントリーゾーン
    MR_TP_TARGET = "midline"    # TP = 回帰線中央
    MR_MIN_RR = 1.5             # 最低リスクリワード比

    # ── Breakout モード ──
    BO_ENABLED = False          # DISABLED: R²崩壊問題（ブレイク=チャネル終了）
    BO_ADX_MIN = 25             # ブレイク用ADX閾値
    BO_BODY_MIN = 0.30          # ブレイク足実体 ≥ 30%
    BO_TP_ATR_MULT = 2.5        # TP = ATR × 2.5
    BO_MIN_RR = 1.5             # 最低リスクリワード比

    # ── 共通 ──
    SL_ATR_BUFFER = 0.3         # SLバッファ: ATR × 0.3
    MAX_HOLD_BARS = 12          # 最大保持: 12バー = 3H (15m)

    def _compute_lin_reg(self, closes: np.ndarray):
        """最小二乗法で線形回帰チャネルを計算。

        Returns:
            (alpha, beta, sigma, r_squared, upper_now, lower_now, mid_now)
            or None if data insufficient
        """
        n = len(closes)
        if n < 10:
            return None

        x = np.arange(n, dtype=float)
        y = closes.astype(float)

        # 最小二乗法: y = alpha + beta * x
        x_mean = x.mean()
        y_mean = y.mean()
        ss_xy = np.sum((x - x_mean) * (y - y_mean))
        ss_xx = np.sum((x - x_mean) ** 2)

        if ss_xx < 1e-10:
            return None

        beta = ss_xy / ss_xx
        alpha = y_mean - beta * x_mean

        # 残差と標準偏差
        y_pred = alpha + beta * x
        residuals = y - y_pred
        sigma = np.std(residuals, ddof=1) if n > 2 else np.std(residuals)

        if sigma < 1e-10:
            return None

        # 決定係数 R²
        ss_res = np.sum(residuals ** 2)
        ss_tot = np.sum((y - y_mean) ** 2)
        r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

        # 現在時点(x = n-1)のチャネル値
        x_now = float(n - 1)
        mid_now = alpha + beta * x_now
        upper_now = mid_now + self.SIGMA_MULT * sigma
        lower_now = mid_now - self.SIGMA_MULT * sigma

        return (alpha, beta, sigma, r_squared, upper_now, lower_now, mid_now)

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── ペア制限: EUR/USD + XAU/USD のみ ──
        # USD/JPY: 7t EV=-0.053 (負EV)
        # GBP/USD: 15t EV=+0.002 (ゼロ)
        # EUR/USD: 14t WR=64.3% EV=+0.298 → 採用
        # XAU/USD: 7t WR=71.4% EV=+0.471 → 採用
        # MR限定後の再BT: EUR/USD 22t WR=59.1% EV=+0.184 → 採用
        # XAU/USD MR: 21t WR=57.1% EV=-0.017 → MR単独では負EV
        _sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        if _sym not in ("EURUSD",):
            return None

        # ── DataFrame十分性チェック ──
        if ctx.df is None or len(ctx.df) < self.LR_PERIOD + 5:
            return None

        # ═══════════════════════════════════════════════════
        # チャネル計算
        # ═══════════════════════════════════════════════════
        _closes = ctx.df["Close"].iloc[-self.LR_PERIOD:].values
        _lr = self._compute_lin_reg(_closes)
        if _lr is None:
            return None

        alpha, beta, sigma, r2, upper, lower, mid = _lr

        # ── チャネル品質チェック: R² ≥ 0.70 ──
        if r2 < self.MIN_R2:
            return None

        # ── トレンド存在チェック: |beta|/ATR ≥ 閾値 ──
        _slope_norm = abs(beta) / ctx.atr if ctx.atr > 0 else 0
        if _slope_norm < self.MIN_SLOPE_ATR:
            return None

        # トレンド方向: beta > 0 = 上昇, beta < 0 = 下降
        _trend_up = beta > 0
        _trend_down = beta < 0

        # ═══════════════════════════════════════════════════
        # HTFフィルター
        # ═══════════════════════════════════════════════════
        _htf = ctx.htf or {}
        _agreement = _htf.get("agreement", "mixed")

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0

        _channel_width = upper - lower
        _mr_zone = _channel_width * self.MR_ZONE_PCT  # チャネル幅の25%

        # ═══════════════════════════════════════════════════
        # Mode A: Mean Reversion (チャネル内順張り)
        #   上昇トレンド: チャネル下位25% (lower ~ lower + 25%) でBUY
        #   下降トレンド: チャネル上位25% (upper - 25% ~ upper) でSELL
        # ═══════════════════════════════════════════════════
        if self.MR_ENABLED:
            # ── 上昇トレンド + 下限ゾーン → BUY ──
            if _trend_up and ctx.entry <= lower + _mr_zone:
                # 反転確認: 陽線 + Close > lower (チャネル内に回復)
                if ctx.entry > ctx.open_price and ctx.entry > lower:
                    if _agreement != "bear":
                        signal = "BUY"
                        score = 4.5
                        sl = lower - ctx.atr * self.SL_ATR_BUFFER
                        tp = mid  # 回帰線中央
                        reasons.append(
                            f"✅ LRC MR BUY: 上昇チャネル下限反発 "
                            f"(R²={r2:.2f}, slope={_slope_norm:.3f})"
                        )

            # ── 下降トレンド + 上限ゾーン → SELL ──
            elif _trend_down and ctx.entry >= upper - _mr_zone:
                if ctx.entry < ctx.open_price and ctx.entry < upper:
                    if _agreement != "bull":
                        signal = "SELL"
                        score = 4.5
                        sl = upper + ctx.atr * self.SL_ATR_BUFFER
                        tp = mid
                        reasons.append(
                            f"✅ LRC MR SELL: 下降チャネル上限反発 "
                            f"(R²={r2:.2f}, slope={_slope_norm:.3f})"
                        )

        # ═══════════════════════════════════════════════════
        # Mode B: Breakout (チャネルブレイク)
        # ═══════════════════════════════════════════════════
        if signal is None and self.BO_ENABLED and ctx.adx >= self.BO_ADX_MIN:
            _bar_range = ctx.prev_high - ctx.prev_low if ctx.prev_high > ctx.prev_low else 0
            _bar_body = abs(ctx.entry - ctx.open_price)
            _body_ok = (_bar_body / _bar_range >= self.BO_BODY_MIN) if _bar_range > 0 else False

            if _body_ok:
                # ── 上方ブレイク → BUY ──
                if ctx.entry > upper and _trend_up:
                    if _agreement != "bear":
                        signal = "BUY"
                        score = 4.0
                        sl = mid  # 回帰線中央をSL
                        tp = ctx.entry + ctx.atr * self.BO_TP_ATR_MULT
                        reasons.append(
                            f"✅ LRC BO BUY: 上方ブレイク "
                            f"(ADX={ctx.adx:.1f}, R²={r2:.2f})"
                        )

                # ── 下方ブレイク → SELL ──
                elif ctx.entry < lower and _trend_down:
                    if _agreement != "bull":
                        signal = "SELL"
                        score = 4.0
                        sl = mid
                        tp = ctx.entry - ctx.atr * self.BO_TP_ATR_MULT
                        reasons.append(
                            f"✅ LRC BO SELL: 下方ブレイク "
                            f"(ADX={ctx.adx:.1f}, R²={r2:.2f})"
                        )

        if signal is None:
            return None

        # ═══════════════════════════════════════════════════
        # RR検証
        # ═══════════════════════════════════════════════════
        _sl_dist = abs(ctx.entry - sl)
        _tp_dist = abs(tp - ctx.entry)
        _min_rr = self.MR_MIN_RR if "MR" in reasons[0] else self.BO_MIN_RR

        # RR不足時のTP補正
        if _sl_dist > 0 and _tp_dist / _sl_dist < _min_rr:
            _tp_dist = _sl_dist * _min_rr
            tp = ctx.entry + _tp_dist if signal == "BUY" else ctx.entry - _tp_dist

        # RR再確認
        if _sl_dist <= 0 or _tp_dist / _sl_dist < _min_rr:
            return None

        _rr = _tp_dist / _sl_dist

        # ═══════════════════════════════════════════════════
        # Reasons & ボーナス
        # ═══════════════════════════════════════════════════
        _dec = 3 if ctx.is_jpy or ctx.pip_mult == 100 else 5
        reasons.append(
            f"✅ チャネル: Upper={upper:.{_dec}f} Mid={mid:.{_dec}f} "
            f"Lower={lower:.{_dec}f} (width={_channel_width * ctx.pip_mult:.1f}pip)"
        )
        reasons.append(
            f"📊 RR={_rr:.1f} SL={sl:.{_dec}f} TP={tp:.{_dec}f}"
        )

        # R²ボーナス（高適合度）
        if r2 >= 0.85:
            score += 0.5
            reasons.append(f"✅ 高適合度(R²={r2:.2f}≥0.85)")

        # HTF方向一致ボーナス
        if (signal == "BUY" and _agreement == "bull") or \
           (signal == "SELL" and _agreement == "bear"):
            score += 0.5
            reasons.append(f"✅ HTF方向一致({_agreement})")

        # EMA方向一致ボーナス
        if (signal == "BUY" and ctx.ema9 > ctx.ema21) or \
           (signal == "SELL" and ctx.ema9 < ctx.ema21):
            score += 0.3
            reasons.append("✅ EMA短期方向一致")

        # 傾き強度ボーナス
        if _slope_norm >= 0.10:
            score += 0.3
            reasons.append(f"✅ 強トレンド(slope={_slope_norm:.3f})")

        conf = int(min(85, 50 + score * 4))
        return Candidate(
            signal=signal, confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score
        )
