"""
Pullback to Liquidity v1 — HTF trend × M15 pullback × liquidity rejection

Pre-Registration LOCK: 2026-04-26
LOCK doc: knowledge-base/wiki/decisions/pre-reg-pullback-to-liquidity-v1-2026-04-26.md
Mechanism thesis (Moskowitz et al 2012, Time Series Momentum):
  HTF (H4) trend が確立した方向に対し、M15 swing low/high への pullback 局面では
  流動性供給により価格が再加速する。pullback 完了 + rejection で entry。

Entry conditions (LOCKED, 後付け変更禁止):
  HTF_BIAS:           ctx.htf.get("agreement") == "bull" (BUY) or "bear" (SELL)
  M15 swing detection: recent 20 bars に swing low/high (≥ 5 bar 前)
  LIQUIDITY_TOUCH:     current low/high ≤ swing ± 5pip
  REJECTION_CANDLE:    BUY: close>open AND (low-close)/(high-low) ≥ 0.4
                       SELL: close<open AND (high-close)/(high-low) ≥ 0.4
  VOLUME_CONFIRMATION: current volume ≥ 1.2 × avg(last 20)

Forbidden:
  - HTF agreement != "bull"/"bear"
  - ATR(14) < 5 pip
  - session "Asia_early" (UTC [00, 02])
  - 直近 4 bars 内に同方向 entry 済み (重複防止、entry-side で対応)

Exit (LOCKED):
  TP: entry ± 2.0 × ATR(14)
  SL: entry ∓ 1.0 × ATR(14)
  TIME_STOP: 24 bars (M15 × 6h)

Validation: Phase 3 BT で N≥200, Wilson lower>50%, PF>1.30, 5-fold WF, Bonferroni α=0.005

References:
  - Moskowitz, Ooi, Pedersen (2012) "Time Series Momentum"
  - knowledge-base/wiki/decisions/pre-reg-pullback-to-liquidity-v1-2026-04-26.md
"""
from __future__ import annotations

from typing import Optional

from strategies.base import Candidate, StrategyBase
from strategies.context import SignalContext


class PullbackToLiquidityV1(StrategyBase):
    name = "pullback_to_liquidity_v1"
    mode = "daytrade"
    enabled = True
    strategy_type = "pullback"  # confidence_v2: ADX>31 で sharp penalty (pullback 戦略)

    # ── LOCKED parameters (Pre-Registration 2026-04-26) ──
    SWING_LOOKBACK = 20            # M15 bars
    SWING_MIN_AGE = 5              # swing は ≥ 5 bar 前であること
    LIQUIDITY_TOUCH_PCT = 0.001    # ±5pip (USD_JPY 158 で約 0.158)
    REJECTION_WICK_RATIO = 0.40    # 下髭/上髭 比率 ≥ 0.4
    VOLUME_BOOST = 1.20            # 直近 20 bar 平均の 1.2 倍以上
    VOLUME_LOOKBACK = 20
    ATR_MIN_PIPS = 5.0
    TP_MULT = 2.0                  # ATR × 2.0
    SL_MULT = 1.0                  # ATR × 1.0

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        df = ctx.df
        if df is None or len(df) < max(self.SWING_LOOKBACK, self.VOLUME_LOOKBACK) + 2:
            return None

        # ── Forbidden: Asia_early (UTC [00, 02]) ──
        h = ctx.hour_utc
        if 0 <= h < 2:
            return None

        # ── Forbidden: ATR too low ──
        atr_pips = ctx.atr * ctx.pip_mult  # ATR を pip 単位に
        if atr_pips < self.ATR_MIN_PIPS:
            return None

        # ── HTF bias 判定 (LOCKED: bull/bear のみ entry) ──
        htf_agreement = (ctx.htf or {}).get("agreement", "mixed")
        if htf_agreement == "bull":
            sig = "BUY"
        elif htf_agreement == "bear":
            sig = "SELL"
        else:
            return None  # neutral / mixed: entry なし

        # ── M15 swing 検出 (last SWING_LOOKBACK bars 内) ──
        # `df` は最新足を含む。直近 SWING_LOOKBACK bars (含む現在) を検査。
        recent = df.iloc[-self.SWING_LOOKBACK:]
        if sig == "BUY":
            swing_idx = recent["Low"].idxmin()
            swing_price = float(recent["Low"].min())
        else:
            swing_idx = recent["High"].idxmax()
            swing_price = float(recent["High"].max())

        # swing が現足から ≥ SWING_MIN_AGE bars 前 (現在の bar = idx[-1])
        try:
            swing_pos = df.index.get_loc(swing_idx)
            current_pos = len(df) - 1
            swing_age_bars = current_pos - swing_pos
        except (KeyError, TypeError):
            return None
        if swing_age_bars < self.SWING_MIN_AGE:
            return None

        # ── LIQUIDITY_TOUCH (current bar が swing 付近) ──
        # row["Low"] (BUY) ≤ swing_low * (1 + tolerance)
        current_low = ctx.entry  # fallback (実際の bar は df.iloc[-1] から)
        current_high = ctx.entry
        try:
            last_row = df.iloc[-1]
            current_low = float(last_row["Low"])
            current_high = float(last_row["High"])
        except (KeyError, IndexError):
            return None

        if sig == "BUY":
            if current_low > swing_price * (1.0 + self.LIQUIDITY_TOUCH_PCT):
                return None
        else:
            if current_high < swing_price * (1.0 - self.LIQUIDITY_TOUCH_PCT):
                return None

        # ── REJECTION_CANDLE (wick ratio ≥ 0.4) ──
        bar_high = current_high
        bar_low = current_low
        bar_close = ctx.entry
        bar_open = ctx.open_price
        bar_range = max(bar_high - bar_low, 1e-9)

        if sig == "BUY":
            if bar_close <= bar_open:
                return None
            wick_ratio = (bar_low - bar_close) / bar_range  # bar_low < bar_close so this is negative
            wick_ratio_signed = (bar_close - bar_low) / bar_range  # 正方向
            # 仕様: (low - close) / (high - low) ≥ 0.4 → close からどれだけ low が遠いか
            # 下髭 (lower shadow) = min(open, close) - low
            lower_shadow = min(bar_open, bar_close) - bar_low
            if lower_shadow / bar_range < self.REJECTION_WICK_RATIO:
                return None
        else:
            if bar_close >= bar_open:
                return None
            upper_shadow = bar_high - max(bar_open, bar_close)
            if upper_shadow / bar_range < self.REJECTION_WICK_RATIO:
                return None

        # ── VOLUME_CONFIRMATION (≥ 1.2 × avg(last 20)) ──
        try:
            vol_recent = df["Volume"].iloc[-self.VOLUME_LOOKBACK:]
            vol_current = float(df["Volume"].iloc[-1])
            vol_avg = float(vol_recent.mean())
            if vol_avg <= 0:
                # volume データ無効 → fail-soft で skip
                return None
            if vol_current < vol_avg * self.VOLUME_BOOST:
                return None
        except (KeyError, IndexError, ValueError):
            # Volume カラム不在 → fail-soft (BT data によっては Volume が無い)
            # Pre-reg LOCK では VOLUME 必須だが、データ不在時は skip して安全側
            return None

        # ── Entry (TP/SL LOCKED) ──
        atr = ctx.atr
        if sig == "BUY":
            tp = ctx.entry + atr * self.TP_MULT
            sl = ctx.entry - atr * self.SL_MULT
        else:
            tp = ctx.entry - atr * self.TP_MULT
            sl = ctx.entry + atr * self.SL_MULT

        reasons = [
            f"✅ HTF agreement={htf_agreement} (LOCK condition)",
            f"✅ M15 swing {('low' if sig == 'BUY' else 'high')} @ {swing_price:.5f} "
            f"({swing_age_bars} bars 前)",
            f"✅ liquidity touch (current {('low' if sig == 'BUY' else 'high')} "
            f"= {(current_low if sig == 'BUY' else current_high):.5f})",
            f"✅ rejection candle (wick ratio ≥ {self.REJECTION_WICK_RATIO})",
            f"✅ volume {vol_current:.0f} ≥ {self.VOLUME_BOOST}× avg {vol_avg:.0f}",
            f"TP={tp:.5f} (ATR×{self.TP_MULT}), SL={sl:.5f} (ATR×{self.SL_MULT})",
        ]

        # Confidence: pre-reg では明記無し、structural mechanism strength から 70 default
        # (HTF + 5 conditions all pass の高品質 entry)
        score = 4.0  # 多条件 AND pass
        confidence = 70

        return Candidate(
            signal=sig,
            confidence=confidence,
            sl=sl,
            tp=tp,
            reasons=reasons,
            entry_type=self.name,
            score=score,
        )
