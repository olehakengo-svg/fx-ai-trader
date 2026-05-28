"""
ZZ Pivot v60 SizeReduce — EUR_USD M15 Mean-Reversion at Trend Extreme
=======================================================================

LIVE intentional exception (Path B / Rule 1 override) per user judgment 2026-05-28.
Same pattern as Kalman D7 v18e (2026-05-20), vix_carry 1.0x (2026-05-21),
and pivot_detector_v2_5 (2026-05-26).

## TV Pine source of truth
- Slot: USER;978a118f17884c19a823b262a8aceb5a (TradingView Desktop)
- Title: "Trade-Level Loser Analysis v70.4 (WFO)"

## TV BT validation (EURUSD M15, 2025-05-26 → 2026-05-26, 1y OOS)

| Variant | PF | Total PnL | WR | Trades | Max DD |
|---------|------|------|-------|--------|--------|
| Baseline (v60) | 1.222 | +$57.73 | 48.31% | 207 | 0.22% |
| SizeReduce (5%/10%) | **1.294** | **+$65.10** | 48.31% | 207 | 0.24% |

WFO 3-fold (Baseline vs SizeReduce simulation):
- Fold 1 (May-Sep): ΔPF +24.9%
- Fold 2 (Sep-Jan): ΔPF +4.0%
- Fold 3 (Jan-May): ΔPF +7.6%
- All 3 folds directional win (Sign test p=0.125 — NOT statistically significant)

## Rule 1 状態 (memory feedback_partial_quant_trap)
- N=207 / WR=48.31% / Wilson_lo ≈ 0.434 (FAIL ≥0.50)
- PF=1.222 (baseline) → 1.294 (SizeReduce)
- Bonferroni 未適用 (WFO 3-fold sign test p=0.125)
- Kelly 未算
- Independent OOS 未 (1y は derived data)

## Pre-reg withdrawal conditions (memory project_zz_pivot_v60_sr_live_queue_2026_05_28)

- N=30 で WR < 35% → user manual demote
- N=30 で PF < 1.0 → user manual demote
- 30d MaxDD > 1% → user manual stop
- 14日 consecutive PnL マイナス → user manual stop
- Watchdog: tools/zz_pivot_live_monitor.py (TBD v2)

## Strategy logic (Pine source 完全 port)

### Trend filter (M15)
- trend_ema = EMA(close, 50)
- uptrend = close > trend_ema
- downtrend = close < trend_ema

### Peak detection (SHORT during uptrend)
4 detection types — ANY of:
- pA: dynamic + absolute RSI/BB/RCI extreme + near 20-bar high + RSI accel<0
- pB: 30-bar HH + RSI divergence (HH but RSI<HH_RSI-10) + bbpb≥0.90
- pE: 30-bar HH + MACD-hist divergence + bbpb≥0.85
- pF: prior swing high retest (highest(high[20], 30) ± 0.2 ATR) + bbpb≥0.88

### Trough detection (LONG during downtrend) — mirror

### SizeReduce loser zone (THE INNOVATION)
loser_zone = (RSI<30 AND macd_hist<0) OR (atr_ratio ≥ 1.6)
- Normal entry: entry_type="zz_pivot_v60_sr" (1.0x lot)
- Loser zone:   entry_type="zz_pivot_v60_sr_lo" (0.5x lot via _PAIR_LOT_BOOST)

## Deviations from Pine spec (MVP v1)
- Pine: exit on opposite extreme + min_hold>=5 bars (no TP)
- MVP:  TP=6×ATR (RR≈1.5) + SL=4×ATR (Pine emergency) + max_hold=24 bars
- TODO v2: implement exact "opposite extreme exit" logic via post-trade hook

Pair: EUR_USD ONLY (TV 検証唯一)
TF: 15m
Direction: BOTH (peak→SHORT, trough→LONG)
"""
from __future__ import annotations

from typing import Optional, Tuple

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext


class ZzPivotV60Sr(StrategyBase):
    """ZZ Pivot v60 Mean-Reversion at Trend Extreme + SizeReduce."""

    name = "zz_pivot_v60_sr"           # Normal-zone entry_type (1.0x lot)
    LOSER_ZONE_NAME = "zz_pivot_v60_sr_lo"  # Loser-zone entry_type (0.5x lot via _PAIR_LOT_BOOST)

    mode = "daytrade"
    enabled = True
    strategy_type = "MR"  # MR anti-trend penalty applied if ADX>25

    # ── Pair / TF filter ──
    _ALLOWED_SYMBOLS = frozenset({"EURUSD"})
    _ALLOWED_TF = frozenset({"15m", "M15", "15"})

    # ── Trend filter ──
    TREND_EMA_LEN = 50

    # ── Peak/trough thresholds (Pine v70.4 と同値) ──
    NEAR_HIGH_ATR = 0.5    # high - max_20[1] <= 0.5 * ATR
    NEAR_LOW_ATR = 0.5

    # pA / tA (dynamic + absolute)
    PA_RSI_DELTA_MIN = 2.0   # rsi - rsi[5] > 2
    PA_RCI_DELTA_MAX = -25.0
    PA_BBP_DELTA_MIN = 0.08
    PA_CLZ_DELTA_MIN = 0.02
    PA_RSI_ABS_MIN = 60.0    # rsi >= 60
    PA_BBP_ABS_MIN = 0.80
    PA_RCI_ABS_MAX = -30.0
    PA_STREAK_MIN = 2

    TA_RSI_DELTA_MAX = -2.0
    TA_RCI_DELTA_MIN = 25.0
    TA_BBP_DELTA_MAX = -0.08
    TA_CLZ_DELTA_MAX = -0.02
    TA_RSI_ABS_MAX = 40.0
    TA_BBP_ABS_MAX = 0.20
    TA_RCI_ABS_MIN = 30.0

    # pB / tB (HH/RSI divergence)
    PB_BBP_MIN = 0.90
    PB_RSI_MIN = 63.0
    PB_RSI_DIV_DELTA = 10.0
    TB_BBP_MAX = 0.08
    TB_RSI_MAX = 35.0
    TB_RSI_DIV_DELTA = 12.0

    # pE (MACD divergence) — peak only
    PE_BBP_MIN = 0.85
    PE_RSI_MIN = 60.0
    PE_MACD_DELTA = 0.00025

    # tD (volume spike trough)
    TD_VOL_Z_MIN = 2.7
    TD_RSI_MAX = 33.0
    TD_BBP_MAX = 0.30
    TD_BODY_ATR_MIN = 0.5

    # pF / tF (prior swing retest)
    PF_PROXIMITY_ATR = 0.2
    PF_BBP_MIN = 0.88
    PF_RSI_MIN = 62.0
    TF_PROXIMITY_ATR = 0.15
    TF_BBP_MAX = 0.10
    TF_RSI_MAX = 35.0

    # ── SizeReduce loser zone (memory feedback_size_lever_beats_skip_filter) ──
    LOSER_F1_RSI_MAX = 30.0     # F1: RSI<30 AND MACD<0
    LOSER_F3_ATR_MIN = 1.6      # F3: atr_ratio >= 1.6
    ATR_BASELINE_LEN = 100      # EMA(ATR, 100) for atr_ratio

    # ── Risk parameters (MVP v1 — Pine "opposite extreme exit" は max_hold で近似) ──
    SL_ATR_MULT = 4.0       # Stop = 4 × ATR(14) (Pine emergency SL と同値)
    TP_ATR_MULT = 6.0       # TP = 6 × ATR(14); RR=1.5 (Pine spec は no-TP だが MVP では設定)
    MIN_RR = 1.4
    MAX_HOLD_BARS = 24      # 6h max @ M15 (Pine: opposite extreme + min_hold=5)

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── Pair filter ──
        _sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        if _sym not in self._ALLOWED_SYMBOLS:
            return None

        # ── TF filter (M15 only) ──
        if ctx.tf not in self._ALLOWED_TF:
            return None

        # ── DataFrame check ──
        if ctx.df is None or len(ctx.df) < max(self.TREND_EMA_LEN, self.ATR_BASELINE_LEN) + 30:
            return None

        df = ctx.df

        # ── Trend filter ──
        try:
            trend_ema = float(df["Close"].ewm(span=self.TREND_EMA_LEN, adjust=False).mean().iloc[-1])
        except Exception:
            return None
        uptrend = ctx.entry > trend_ema
        downtrend = ctx.entry < trend_ema
        if not (uptrend or downtrend):
            return None

        # ── ATR baseline (atr_ratio for loser zone F3) ──
        try:
            atr_series = self._compute_atr_series(df, 14)
            atr_baseline = float(atr_series.ewm(span=self.ATR_BASELINE_LEN, adjust=False).mean().iloc[-1])
            atr_ratio = ctx.atr / atr_baseline if atr_baseline > 0 else 1.0
        except Exception:
            atr_ratio = 1.0

        # ── Indicators (5-bar deltas, streaks, near-high/low) ──
        try:
            features = self._compute_features(df, ctx)
        except Exception as e:
            return None

        # ── Peak detection (SHORT during uptrend) ──
        peak_type = None
        if uptrend:
            peak_type = self._detect_peak(ctx, features, df)

        # ── Trough detection (LONG during downtrend) ──
        trough_type = None
        if downtrend:
            trough_type = self._detect_trough(ctx, features, df)

        if peak_type is None and trough_type is None:
            return None

        # ── Determine signal direction ──
        if peak_type is not None:
            signal = "SELL"
            det_type = peak_type
            sl = ctx.entry + ctx.atr * self.SL_ATR_MULT
            tp = ctx.entry - ctx.atr * self.TP_ATR_MULT
        else:
            signal = "BUY"
            det_type = trough_type
            sl = ctx.entry - ctx.atr * self.SL_ATR_MULT
            tp = ctx.entry + ctx.atr * self.TP_ATR_MULT

        # ── ATR guard ──
        if ctx.atr <= 0:
            return None

        _sl_dist = abs(ctx.entry - sl)
        _tp_dist = abs(tp - ctx.entry)
        _rr = _tp_dist / _sl_dist if _sl_dist > 0 else 0.0
        if _rr < self.MIN_RR:
            return None

        # ── SizeReduce loser zone detection ──
        # F1: RSI<30 AND macd_hist<0 (capitulation in active downtrend → bounce 来ず)
        # F3: atr_ratio >= 1.6 (extreme volatility regime → MR 崩壊)
        in_f1 = ctx.rsi < self.LOSER_F1_RSI_MAX and ctx.macdh < 0
        in_f3 = atr_ratio >= self.LOSER_F3_ATR_MIN
        in_loser_zone = in_f1 or in_f3

        # Entry type — dual-name approach for SizeReduce (no demo_trader.py modification)
        entry_type = self.LOSER_ZONE_NAME if in_loser_zone else self.name

        # ── Build reasons ──
        det_names = {
            "pA": "A (dyn+abs RSI/BB/RCI extreme)",
            "pB": "B (HH + RSI divergence)",
            "pE": "E (HH + MACD divergence)",
            "pF": "F (prior swing retest)",
            "tA": "A (dyn+abs RSI/BB/RCI extreme)",
            "tB": "B (LL + RSI divergence)",
            "tD": "D (vol spike capitulation)",
            "tF": "F (prior swing retest)",
        }
        reasons = [
            f"✅ ZZ Pivot v60 {('SHORT' if signal=='SELL' else 'LONG')} — det={det_names.get(det_type, det_type)}",
            f"✅ Trend filter: close={ctx.entry:.5f} {'>' if uptrend else '<'} EMA({self.TREND_EMA_LEN})={trend_ema:.5f}",
            f"📊 RSI={ctx.rsi:.1f} bbpb={ctx.bbpb:.2f} ATR_ratio={atr_ratio:.2f} MACDh={ctx.macdh:+.5f}",
            f"📊 RR={_rr:.2f} SL={sl:.5f} ({self.SL_ATR_MULT}×ATR) TP={tp:.5f} ({self.TP_ATR_MULT}×ATR)",
        ]
        if in_loser_zone:
            zone_tags = []
            if in_f1:
                zone_tags.append(f"F1 RSI<30∩MACD<0")
            if in_f3:
                zone_tags.append(f"F3 ATR_ratio={atr_ratio:.2f}≥{self.LOSER_F3_ATR_MIN}")
            reasons.append(
                f"⚠️ LOSER ZONE ({' OR '.join(zone_tags)}) → entry_type={entry_type} (0.5x lot via _PAIR_LOT_BOOST)"
            )
        else:
            reasons.append(f"🟢 NORMAL ZONE → entry_type={entry_type} (1.0x lot)")
        reasons.append(
            "🔖 LIVE intentional exception — TV 1y OOS PF 1.294 / WFO 3/3 directional win (p=0.125 not sig.)"
        )

        # ── Score (mid-tier, similar to pivot_detector_v2_5) ──
        score = 4.0
        # Peak detector A or F is the strongest (Pine BT: WR 55%/52%)
        if det_type in ("pA", "tA", "pF", "tF"):
            score += 0.5
        # Loser zone score penalty (small) — lot reduction handles risk
        if in_loser_zone:
            score -= 0.2

        # ── Confidence ──
        try:
            from modules.confidence_v2 import apply_penalty
            _legacy_conf = int(min(85, 50 + score * 4))
            conf = apply_penalty(_legacy_conf, self.strategy_type, ctx.adx, conf_max=85)
            if conf != _legacy_conf:
                reasons.append(
                    f"🔧 [v2] MR anti-trend: ADX={ctx.adx:.1f} → conf {_legacy_conf}→{conf}"
                )
        except Exception:
            conf = int(min(85, 50 + score * 4))

        return Candidate(
            signal=signal,
            confidence=conf,
            sl=sl,
            tp=tp,
            reasons=reasons,
            entry_type=entry_type,    # zz_pivot_v60_sr OR zz_pivot_v60_sr_lo (SizeReduce)
            score=score,
            max_hold_bars=self.MAX_HOLD_BARS,
        )

    # ──────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _compute_atr_series(df, length: int = 14):
        """True ATR series via Wilder smoothing."""
        import pandas as pd
        high = df["High"].astype(float)
        low = df["Low"].astype(float)
        close = df["Close"].astype(float)
        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        # Wilder smoothing = EMA with alpha = 1/length
        return tr.ewm(alpha=1.0 / length, adjust=False).mean()

    def _compute_features(self, df, ctx) -> dict:
        """Compute 5-bar deltas, streaks, near-high/low for peak/trough detection."""
        if len(df) < 32:
            raise ValueError("not enough bars")

        close = df["Close"].astype(float)
        high = df["High"].astype(float)
        low = df["Low"].astype(float)

        # ── 5-bar deltas ──
        rsi_d5 = ctx.rsi - float(df["rsi"].iloc[-6]) if "rsi" in df.columns else 0.0
        bbp_d5 = ctx.bbpb - float(df["bb_pband"].iloc[-6]) if "bb_pband" in df.columns else 0.0
        clz_d5 = (float(close.iloc[-1]) - float(close.iloc[-6])) / float(close.iloc[-6]) * 100.0

        # RCI(9) — Rank Correlation Index (Pine v70.4 implementation)
        rci9_now = self._rci(close.iloc[-9:].values, 9)
        rci9_prev5 = self._rci(close.iloc[-14:-5].values, 9) if len(close) >= 14 else rci9_now
        rci_d5 = rci9_now - rci9_prev5

        # RSI accel (rsi_d5 - rsi_d5[5])
        if "rsi" in df.columns and len(df) >= 12:
            rsi_d5_prev = float(df["rsi"].iloc[-6]) - float(df["rsi"].iloc[-11])
        else:
            rsi_d5_prev = 0.0
        rsi_accel = rsi_d5 - rsi_d5_prev

        # ── Streaks (consecutive close > close[1]) ──
        up_streak = 0
        dn_streak = 0
        for i in range(len(close) - 1, 0, -1):
            if close.iloc[i] > close.iloc[i - 1]:
                up_streak += 1
                if dn_streak == 0:
                    pass
                else:
                    break
            elif close.iloc[i] < close.iloc[i - 1]:
                if up_streak == 0:
                    dn_streak += 1
                else:
                    break
            else:
                break

        # ── 20-bar prior high/low ──
        prev_high_20 = float(high.iloc[-21:-1].max())
        prev_low_20 = float(low.iloc[-21:-1].min())
        near_high = (prev_high_20 - float(high.iloc[-1])) <= self.NEAR_HIGH_ATR * ctx.atr
        near_low = (float(low.iloc[-1]) - prev_low_20) <= self.NEAR_LOW_ATR * ctx.atr

        # ── 30-bar prior HH / RSI max / MACDh max / LL / RSI min ──
        prev_hh_30 = float(high.iloc[-31:-1].max())
        prev_ll_30 = float(low.iloc[-31:-1].min())
        prev_rsi_max_30 = float(df["rsi"].iloc[-31:-1].max()) if "rsi" in df.columns else 50.0
        prev_rsi_min_30 = float(df["rsi"].iloc[-31:-1].min()) if "rsi" in df.columns else 50.0
        if "macd_hist" in df.columns:
            prev_macd_max_30 = float(df["macd_hist"].iloc[-31:-1].max())
        else:
            prev_macd_max_30 = 0.0

        # ── Prior swing high/low (highest(high[20], 30) — high shifted 20 bars back) ──
        if len(high) >= 50:
            prior_high_window = high.iloc[-50:-20]  # bars [t-50, t-20)
            prior_low_window = low.iloc[-50:-20]
            prior_swing_high = float(prior_high_window.max())
            prior_swing_low = float(prior_low_window.min())
        else:
            prior_swing_high = float(high.max())
            prior_swing_low = float(low.min())

        # ── Volume z-score (TD detector) ──
        try:
            vol = df["Volume"].astype(float)
            vol_mu = float(vol.iloc[-21:-1].mean())
            vol_sd = float(vol.iloc[-21:-1].std(ddof=0))
            vol_z = (float(vol.iloc[-1]) - vol_mu) / vol_sd if vol_sd > 0 else 0.0
        except Exception:
            vol_z = 0.0

        # ── Body size & bull/bear bar ──
        body_size = abs(ctx.entry - ctx.open_price)
        bullish_bar = ctx.entry > ctx.open_price
        bearish_bar = ctx.entry < ctx.open_price

        return {
            "rsi_d5": rsi_d5,
            "rci_d5": rci_d5,
            "bbp_d5": bbp_d5,
            "clz_d5": clz_d5,
            "rci9": rci9_now,
            "rsi_accel": rsi_accel,
            "up_streak": up_streak,
            "dn_streak": dn_streak,
            "prev_high_20": prev_high_20,
            "prev_low_20": prev_low_20,
            "near_high": near_high,
            "near_low": near_low,
            "prev_hh_30": prev_hh_30,
            "prev_ll_30": prev_ll_30,
            "prev_rsi_max_30": prev_rsi_max_30,
            "prev_rsi_min_30": prev_rsi_min_30,
            "prev_macd_max_30": prev_macd_max_30,
            "prior_swing_high": prior_swing_high,
            "prior_swing_low": prior_swing_low,
            "vol_z": vol_z,
            "body_size": body_size,
            "bullish_bar": bullish_bar,
            "bearish_bar": bearish_bar,
            "high_now": float(df["High"].iloc[-1]),
            "low_now": float(df["Low"].iloc[-1]),
        }

    @staticmethod
    def _rci(prices, length: int) -> float:
        """Rank Correlation Index (Pine v70.4 implementation)."""
        if len(prices) < length or length < 2:
            return 0.0
        sum_d2 = 0.0
        for i in range(length):
            t_rank = length - i
            p_rank_count = sum(1 for j in range(length) if prices[j] > prices[i])
            p_rank = p_rank_count + 1
            d = t_rank - p_rank
            sum_d2 += d * d
        return (1.0 - 6.0 * sum_d2 / (length * (length * length - 1))) * 100.0

    def _detect_peak(self, ctx, f: dict, df) -> Optional[str]:
        """Detect peak (SHORT signal) — returns det type 'pA'/'pB'/'pE'/'pF' or None."""
        # pA: dynamic + absolute
        pA_dyn = (
            f["rsi_d5"] > self.PA_RSI_DELTA_MIN and
            f["rci_d5"] < self.PA_RCI_DELTA_MAX and
            f["bbp_d5"] > self.PA_BBP_DELTA_MIN and
            f["clz_d5"] > self.PA_CLZ_DELTA_MIN
        )
        pA_abs = (
            ctx.rsi >= self.PA_RSI_ABS_MIN and
            ctx.bbpb >= self.PA_BBP_ABS_MIN and
            f["rci9"] <= self.PA_RCI_ABS_MAX
        )
        if (pA_dyn and pA_abs and f["near_high"] and
                f["rsi_accel"] < 0 and f["up_streak"] >= self.PA_STREAK_MIN):
            return "pA"

        # pB: 30-bar HH + RSI divergence
        if (f["high_now"] >= f["prev_hh_30"] and
                ctx.rsi < (f["prev_rsi_max_30"] - self.PB_RSI_DIV_DELTA) and
                ctx.bbpb >= self.PB_BBP_MIN and
                ctx.rsi >= self.PB_RSI_MIN):
            return "pB"

        # pE: 30-bar HH + MACD-hist divergence
        if (f["high_now"] >= f["prev_hh_30"] and
                ctx.macdh < (f["prev_macd_max_30"] - self.PE_MACD_DELTA) and
                ctx.bbpb >= self.PE_BBP_MIN and
                ctx.rsi >= self.PE_RSI_MIN):
            return "pE"

        # pF: prior swing retest
        pf_lo = f["prior_swing_high"] - self.PF_PROXIMITY_ATR * ctx.atr
        pf_hi = f["prior_swing_high"] + self.PF_PROXIMITY_ATR * ctx.atr
        if (pf_lo <= f["high_now"] <= pf_hi and
                ctx.bbpb >= self.PF_BBP_MIN and
                ctx.rsi >= self.PF_RSI_MIN):
            return "pF"

        return None

    def _detect_trough(self, ctx, f: dict, df) -> Optional[str]:
        """Detect trough (LONG signal) — returns det type 'tA'/'tB'/'tD'/'tF' or None."""
        # tA: dynamic + absolute (mirror of pA)
        tA_dyn = (
            f["rsi_d5"] < self.TA_RSI_DELTA_MAX and
            f["rci_d5"] > self.TA_RCI_DELTA_MIN and
            f["bbp_d5"] < self.TA_BBP_DELTA_MAX and
            f["clz_d5"] < self.TA_CLZ_DELTA_MAX
        )
        tA_abs = (
            ctx.rsi <= self.TA_RSI_ABS_MAX and
            ctx.bbpb <= self.TA_BBP_ABS_MAX and
            f["rci9"] >= self.TA_RCI_ABS_MIN
        )
        if (tA_dyn and tA_abs and f["near_low"] and
                f["rsi_accel"] > 0 and f["dn_streak"] >= self.PA_STREAK_MIN):
            return "tA"

        # tB: 30-bar LL + RSI divergence
        if (f["low_now"] <= f["prev_ll_30"] and
                ctx.rsi > (f["prev_rsi_min_30"] + self.TB_RSI_DIV_DELTA) and
                ctx.bbpb <= self.TB_BBP_MAX and
                ctx.rsi <= self.TB_RSI_MAX):
            return "tB"

        # tD: volume spike trough
        if (f["vol_z"] >= self.TD_VOL_Z_MIN and
                ctx.rsi <= self.TD_RSI_MAX and
                ctx.bbpb <= self.TD_BBP_MAX and
                f["bearish_bar"] and
                f["body_size"] >= self.TD_BODY_ATR_MIN * ctx.atr):
            return "tD"

        # tF: prior swing low retest
        tf_lo = f["prior_swing_low"] - self.TF_PROXIMITY_ATR * ctx.atr
        tf_hi = f["prior_swing_low"] + self.TF_PROXIMITY_ATR * ctx.atr
        if (tf_lo <= f["low_now"] <= tf_hi and
                ctx.bbpb <= self.TF_BBP_MAX and
                ctx.rsi <= self.TF_RSI_MAX):
            return "tF"

        return None
