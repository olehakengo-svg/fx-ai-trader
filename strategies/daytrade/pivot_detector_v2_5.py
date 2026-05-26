"""
Pivot Detector v2.5 — EUR_USD M15 Long-Only Mean-Reversion
================================================================

LIVE intentional exception (Path B / Rule 1 override) per user judgment 2026-05-26.
Same pattern as Kalman D7 v18e LIVE (2026-05-20) and vix_carry 1.0x (2026-05-21).

TradingView in-house validation (TV M15 EURUSD, MASSIVE未):
  - IS 6mo (Aug 2025 - Jan 2026): PF 2.30, WR 76.67%, N=30, DD 0.03%
  - OOS 4mo (Feb-May 2026):        PF 1.544, WR 64.29%, N=28, DD 0.04%
  - Wilson lower 95% (OOS N=28, WR 64.3%) ≈ 0.46

Rule 1 状態:
  - Wilson_lo 0.46 (FAIL ≥0.50)
  - Bonferroni 未適用 (multi-pair / multi-hypothesis 未)
  - Kelly 未算
  - Pre-reg LOCK 済み (wiki/decisions/pivot_detector_v2_5_live_exception_2026_05_26.md)

Pre-reg withdrawal conditions (LOCK 2026-05-26):
  - N=30 で WR < 35%  → Shadow demote
  - N=30 で PF < 1.0  → Shadow demote
  - N=50 で PF < 1.1  → Manual review
  - Max DD > 8%       → Emergency stop
  - Consecutive 15 losses → Pause 24h

Entry (LONG only):
  - low  <= BB_lower(20, 2σ)
  - RSI(14) <= 30
  - close < EMA(25)
  - vol_z(20) >= 1.5
  - 7 <= UTC hour <= 21

Exit:
  - Hard stop: 3 × ATR(14)
  - TP: 6 × ATR(14) (RR ≈ 2.0; trailing は demo_trader profit extender 経由)

Pair: EUR_USD ONLY (TV 検証唯一)
TF: 15m
Direction: LONG only (Short は TV で PF 0.884)
"""
from __future__ import annotations

from typing import Optional

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext


class PivotDetectorV25(StrategyBase):
    """EUR_USD M15 mean-reversion long, BB+RSI+EMA25+volZ+session filter."""

    name = "pivot_detector_v2_5"
    mode = "daytrade"
    enabled = True
    strategy_type = "MR"

    # ── Pair filter (EUR_USD only — TV 検証唯一) ──
    _ALLOWED_SYMBOLS = frozenset({"EURUSD"})

    # ── Entry thresholds (TV v2.5 と同値) ──
    RSI_MAX = 30.0          # RSI(14) <= 30 (oversold)
    VOL_Z_MIN = 1.5         # vol_z >= 1.5 (volume spike confirmation)
    EMA_LEN = 25            # EMA(25) — close < EMA(25) (downtrend context)
    VOL_LOOKBACK = 20       # volume z-score window
    SESSION_HOUR_FROM = 7   # London open (UTC)
    SESSION_HOUR_TO = 21    # NY close (UTC)

    # ── Risk parameters ──
    SL_ATR_MULT = 3.0       # Stop = 3 × ATR(14) (Pine v2.5 と同値)
    TP_ATR_MULT = 6.0       # TP = 6 × ATR(14); RR=2.0
    MIN_RR = 1.8

    # ── Holding ──
    MAX_HOLD_BARS = 12      # 3h max @ M15

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ───────────────────────────────────────────────
        # STEP 1: Pair filter (EUR_USD only)
        # ───────────────────────────────────────────────
        _sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        if _sym not in self._ALLOWED_SYMBOLS:
            return None

        # ───────────────────────────────────────────────
        # STEP 2: Session filter (7-21 UTC)
        # ───────────────────────────────────────────────
        if not (self.SESSION_HOUR_FROM <= ctx.hour_utc <= self.SESSION_HOUR_TO):
            return None

        # ───────────────────────────────────────────────
        # STEP 3: Need DataFrame for vol_z and EMA(25)
        # ───────────────────────────────────────────────
        if ctx.df is None or len(ctx.df) < max(self.EMA_LEN, self.VOL_LOOKBACK + 1):
            return None

        # ───────────────────────────────────────────────
        # STEP 4: BB lower breach (entry bar low <= BB_lower)
        # ───────────────────────────────────────────────
        # ctx.bb_lower is the current bar's BB lower band (20-bar SMA - 2σ)
        # We check the current bar's low against it.
        _cur_low = float(ctx.df.iloc[-1].get("Low", ctx.entry))
        if _cur_low > ctx.bb_lower:
            return None

        # ───────────────────────────────────────────────
        # STEP 5: RSI(14) <= 30 (oversold)
        # ───────────────────────────────────────────────
        if ctx.rsi > self.RSI_MAX:
            return None

        # ───────────────────────────────────────────────
        # STEP 6: close < EMA(25) (downtrend context — confirms exhaustion)
        # ───────────────────────────────────────────────
        try:
            _close_series = ctx.df["Close"]
            _ema25 = float(_close_series.ewm(span=self.EMA_LEN, adjust=False).mean().iloc[-1])
        except Exception:
            return None
        if ctx.entry >= _ema25:
            return None

        # ───────────────────────────────────────────────
        # STEP 7: vol_z(20) >= 1.5 (volume spike)
        # ───────────────────────────────────────────────
        try:
            _vol_series = ctx.df["Volume"].astype(float)
            if len(_vol_series) < self.VOL_LOOKBACK + 1:
                return None
            _vol_window = _vol_series.iloc[-(self.VOL_LOOKBACK + 1):-1]  # 20 prior bars
            _vol_mu = float(_vol_window.mean())
            _vol_sd = float(_vol_window.std(ddof=0))
            _vol_now = float(_vol_series.iloc[-1])
            _vol_z = (_vol_now - _vol_mu) / _vol_sd if _vol_sd > 0 else 0.0
        except Exception:
            return None
        if _vol_z < self.VOL_Z_MIN:
            return None

        # ───────────────────────────────────────────────
        # STEP 8: SL/TP calculation (Pine v2.5 と同値)
        # ───────────────────────────────────────────────
        if ctx.atr <= 0:
            return None

        _sl_dist = ctx.atr * self.SL_ATR_MULT
        _tp_dist = ctx.atr * self.TP_ATR_MULT
        sl = ctx.entry - _sl_dist
        tp = ctx.entry + _tp_dist

        _rr = _tp_dist / _sl_dist if _sl_dist > 0 else 0.0
        if _rr < self.MIN_RR:
            return None

        # ───────────────────────────────────────────────
        # STEP 9: Build Candidate
        # ───────────────────────────────────────────────
        reasons = [
            f"✅ BB下抜け: Low={_cur_low:.5f} <= BB_lower={ctx.bb_lower:.5f} (Bollinger 1992)",
            f"✅ RSI売られすぎ: RSI={ctx.rsi:.1f} <= {self.RSI_MAX} (Wilder 1978)",
            f"✅ 下降トレンド文脈: Close={ctx.entry:.5f} < EMA({self.EMA_LEN})={_ema25:.5f}",
            f"✅ Volume spike: vol_z={_vol_z:.2f} >= {self.VOL_Z_MIN}",
            f"✅ Session: UTC hour={ctx.hour_utc} in [{self.SESSION_HOUR_FROM},{self.SESSION_HOUR_TO}]",
            f"📊 RR={_rr:.1f} SL={sl:.5f} (3×ATR={_sl_dist:.5f}) TP={tp:.5f} (6×ATR)",
            "🔖 LIVE intentional exception (Rule 1 override) — TV OOS PF 1.544 / WR 64.29% / N=28",
        ]

        # Score base: 4.0 (mid-tier)
        score = 4.0

        # Bonus: deeper RSI
        if ctx.rsi <= 25:
            score += 0.5
            reasons.append("🎯 Tier1: RSI<=25 (deep oversold)")
        if _vol_z >= 2.0:
            score += 0.5
            reasons.append("🎯 Tier1: vol_z>=2σ (strong volume spike)")

        # Confidence (with v2 MR anti-trend penalty if ADX high)
        from modules.confidence_v2 import apply_penalty
        _legacy_conf = int(min(85, 50 + score * 4))
        conf = apply_penalty(_legacy_conf, self.strategy_type, ctx.adx, conf_max=85)
        if conf != _legacy_conf:
            reasons.append(
                f"🔧 [v2] MR anti-trend: ADX={ctx.adx:.1f}>25 → conf {_legacy_conf}→{conf}"
            )

        return Candidate(
            signal="BUY",  # Long only
            confidence=conf,
            sl=sl,
            tp=tp,
            reasons=reasons,
            entry_type=self.name,
            score=score,
        )
