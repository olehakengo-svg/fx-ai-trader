"""
Asia Range Fade v1 — UTC 02-06 アジア時間 range fade with rejection

Pre-Registration LOCK: 2026-04-26
LOCK doc: knowledge-base/wiki/decisions/pre-reg-asia-range-fade-v1-2026-04-26.md
Mechanism thesis (Lo & MacKinlay 1988):
  アジア時間 (00-07 UTC) の低 vol 環境で形成された range の high/low touch は、
  構造的に流動性吸収後に range 中央へ回帰する傾向が高い。touch + rejection で fade entry。

Entry conditions (LOCKED, 後付け変更禁止):
  SESSION:        UTC hour ∈ [02, 06]
  RANGE_FORMATION: last 24 bars で range_size ≤ 1.5×ATR AND range_size ≥ 5pip
                   AND bars_in_range_pct ≥ 0.80
  TOUCH:           BUY: current low ≤ range_low × (1 + 0.0005)
                   SELL: current high ≥ range_high × (1 - 0.0005)
  REJECTION:       下髭 / 上髭 比率 ≥ 0.4
  RSI(14):         BUY: RSI ≤ 30, SELL: RSI ≥ 70

Forbidden:
  - ATR(14) > 8 pip (vol expansion = range invalid)
  - 直近 4 bars 内に同方向 range fade entry (entry-side で対応)

Exit (LOCKED):
  TP: range center ((range_high + range_low) / 2)
      または entry ± 0.7 × range_size, 近い方
  SL: range_low - 0.5×ATR (BUY)
      range_high + 0.5×ATR (SELL)
  TIME_STOP: London open (07:00 UTC)

Validation: Phase 3 BT で N≥200, Wilson lower>50%, PF>1.40, 5-fold WF, Bonferroni α=0.005

References:
  - Lo & MacKinlay (1988) "Stock Market Prices Do Not Follow Random Walks"
  - knowledge-base/wiki/decisions/pre-reg-asia-range-fade-v1-2026-04-26.md
"""
from __future__ import annotations

from typing import Optional

from strategies.base import Candidate, StrategyBase
from strategies.context import SignalContext


class AsiaRangeFadeV1(StrategyBase):
    name = "asia_range_fade_v1"
    mode = "daytrade"
    enabled = True
    strategy_type = "MR"  # confidence_v2: ADX>25 で penalty (mean-reversion 戦略)

    # ── LOCKED parameters (Pre-Registration 2026-04-26) ──
    SESSION_HOUR_MIN = 2           # UTC [02, 06]
    SESSION_HOUR_MAX = 6           # exclusive (i.e., 02 ≤ h < 07)
    RANGE_LOOKBACK = 24            # M15 bars × 24 = 6h
    RANGE_SIZE_ATR_MULT_MAX = 1.5  # range_size ≤ 1.5 × ATR
    RANGE_SIZE_PIPS_MIN = 5.0      # range_size ≥ 5 pip
    BARS_IN_RANGE_PCT_MIN = 0.80   # 24 bar の 80% 以上が range 内
    TOUCH_TOLERANCE_PCT = 0.0005   # ±0.05% (USD_JPY 158 で約 0.79pip)
    REJECTION_WICK_RATIO = 0.40    # 下髭/上髭 比率 ≥ 0.4
    RSI_OVERSOLD_BUY = 30          # BUY entry: RSI ≤ 30
    RSI_OVERBOUGHT_SELL = 70       # SELL entry: RSI ≥ 70
    ATR_MAX_PIPS = 8.0             # ATR > 8pip → no entry (vol expansion)
    SL_ATR_BUFFER = 0.5            # SL = range_low - 0.5×ATR (BUY)
    TP_RANGE_FRACTION = 0.7        # TP candidate: entry ± 0.7 × range_size

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        df = ctx.df
        if df is None or len(df) < self.RANGE_LOOKBACK + 1:
            return None

        # ── SESSION_CONDITION ──
        h = ctx.hour_utc
        if not (self.SESSION_HOUR_MIN <= h <= self.SESSION_HOUR_MAX):
            return None

        # ── ATR Forbidden (vol expansion = range invalid) ──
        atr = ctx.atr
        atr_pips = atr * ctx.pip_mult
        if atr_pips > self.ATR_MAX_PIPS:
            return None

        # ── RANGE_FORMATION ──
        recent = df.iloc[-self.RANGE_LOOKBACK:]
        try:
            range_high = float(recent["High"].max())
            range_low = float(recent["Low"].min())
        except (KeyError, ValueError):
            return None

        range_size = range_high - range_low
        range_size_pips = range_size * ctx.pip_mult
        if range_size_pips < self.RANGE_SIZE_PIPS_MIN:
            return None  # 範囲が極小すぎる

        # range_size ≤ 1.5 × ATR
        if atr <= 0 or (range_size / atr) > self.RANGE_SIZE_ATR_MULT_MAX:
            return None

        # bars_in_range_pct: 各 bar の close が [range_low, range_high] 範囲内
        try:
            in_range_count = int(
                ((recent["Close"] >= range_low) & (recent["Close"] <= range_high)).sum()
            )
            bars_in_range_pct = in_range_count / float(len(recent))
        except (KeyError, ValueError):
            return None
        if bars_in_range_pct < self.BARS_IN_RANGE_PCT_MIN:
            return None

        # ── TOUCH_DETECTION ──
        try:
            last_row = df.iloc[-1]
            current_low = float(last_row["Low"])
            current_high = float(last_row["High"])
        except (KeyError, IndexError):
            return None

        touch_buy = current_low <= range_low * (1.0 + self.TOUCH_TOLERANCE_PCT)
        touch_sell = current_high >= range_high * (1.0 - self.TOUCH_TOLERANCE_PCT)

        if touch_buy and not touch_sell:
            sig = "BUY"
        elif touch_sell and not touch_buy:
            sig = "SELL"
        else:
            # 両方 touch (range 極小) or 両方 no-touch → entry なし
            return None

        # ── REJECTION_CANDLE ──
        bar_high = current_high
        bar_low = current_low
        bar_close = ctx.entry
        bar_open = ctx.open_price
        bar_range = max(bar_high - bar_low, 1e-9)

        if sig == "BUY":
            if bar_close <= bar_open:
                return None  # 陽線確認
            lower_shadow = min(bar_open, bar_close) - bar_low
            if lower_shadow / bar_range < self.REJECTION_WICK_RATIO:
                return None
        else:
            if bar_close >= bar_open:
                return None  # 陰線確認
            upper_shadow = bar_high - max(bar_open, bar_close)
            if upper_shadow / bar_range < self.REJECTION_WICK_RATIO:
                return None

        # ── RSI EXTRA_CONFIRMATION ──
        # ctx.rsi は M15 の RSI(14) (compute_daytrade_signal で計算)
        rsi = ctx.rsi
        if sig == "BUY":
            if rsi > self.RSI_OVERSOLD_BUY:
                return None
        else:
            if rsi < self.RSI_OVERBOUGHT_SELL:
                return None

        # ── Entry: TP/SL (LOCKED) ──
        # TP: range center または entry ± 0.7 × range_size, 近い方
        range_center = (range_high + range_low) / 2.0
        if sig == "BUY":
            tp_center = range_center
            tp_fixed = ctx.entry + self.TP_RANGE_FRACTION * range_size
            tp = min(tp_center, tp_fixed)  # 近い方 (BUY なので小さい方が "近い")
            sl = range_low - self.SL_ATR_BUFFER * atr
        else:
            tp_center = range_center
            tp_fixed = ctx.entry - self.TP_RANGE_FRACTION * range_size
            tp = max(tp_center, tp_fixed)  # SELL なので大きい方が "近い"
            sl = range_high + self.SL_ATR_BUFFER * atr

        # SL distance check (避: SL が極端に近い場合)
        if abs(ctx.entry - sl) < atr * 0.3:
            return None  # SL too tight (range_low/high が entry に近すぎ)

        reasons = [
            f"✅ session UTC h={h} ∈ [{self.SESSION_HOUR_MIN},{self.SESSION_HOUR_MAX}] "
            f"(LOCK condition)",
            f"✅ range_size {range_size_pips:.1f}pip ≤ {self.RANGE_SIZE_ATR_MULT_MAX}×ATR "
            f"({atr_pips * self.RANGE_SIZE_ATR_MULT_MAX:.1f}pip)",
            f"✅ bars_in_range {bars_in_range_pct*100:.0f}% ≥ "
            f"{self.BARS_IN_RANGE_PCT_MIN*100:.0f}%",
            f"✅ {('range_low' if sig == 'BUY' else 'range_high')} touch "
            f"@ {(range_low if sig == 'BUY' else range_high):.5f}",
            f"✅ rejection candle (wick ratio ≥ {self.REJECTION_WICK_RATIO})",
            f"✅ RSI={rsi:.1f} "
            f"({'≤' + str(self.RSI_OVERSOLD_BUY) if sig == 'BUY' else '≥' + str(self.RSI_OVERBOUGHT_SELL)})",
            f"TP={tp:.5f} (range center vs ±0.7×range, 近い方), "
            f"SL={sl:.5f} (range edge ± 0.5×ATR)",
        ]

        score = 4.0
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
