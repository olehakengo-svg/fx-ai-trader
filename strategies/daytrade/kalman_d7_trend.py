"""
Kalman D7 Trend-Following — Perfect Order EMA(25/75/200) regime transition

学術的根拠:
  - Murphy (1999): EMA perfect order = trend maturity
  - Wilder (1978): ADX/ATR for volatility regime
  - Trend-following payoff asymmetry: Covel (2004)

戦略コンセプト:
  Perfect Order UP (close > EMA25 > EMA75 > EMA200) の *transition (start)* で LONG。
  3 variants で exit pattern を分散 (portfolio of exit timings):
    - v17  : PO-DN flip (regime reversal) — approximated as TP=5×ATR / SL=1.5×ATR
    - v18f : EMA75 close break — approximated as TP=2.5×ATR / SL=2.5×ATR
    - v18e : tight trailing — TP=1.5×ATR + broker trail / SL=2.0×ATR

エントリー filters (v16 forensic 導出, 2026-05-20):
  1. Perfect Order UP の transition (前バー不成立 → 当バー成立)
  2. DIST: (close - ema200) / atr < 3.0  (早期トレンド)
  3. GAP : (ema25 - ema200) / atr < 3.0  (EMAまだ未開)
  4. ATR Q : Q2-Q4 (P20 ≤ atr < P80, 中ボラ)
  5. RSI < 70 (過熱回避)
  6. Session ∈ {ASN(0-7), LDN(7-12), NY(16-21)} UTC (OVL/DEAD除外)

BT (USDJPY M15, 2025-07-01〜2026-05-19, 10.5ヶ月):
  v17 PF=3.866 / WR=23.9% / N=46 / Net=+997 JPY
  v18f PF=2.087 / WR=30.9% / N=68 / Net=+568 JPY
  v18e PF=1.181 / WR=55.4% / N=65 / Net=+73 JPY

依存:
  - ctx.df から ta.ema(25), ta.ema(75) を計算 (ctx は 9/21/50/200 のみ)

Memory:
  - [[project_kalman_d7_regime_bound_live_2026_05_20]] — LIVE 投入決定経緯
  - [[feedback_shadow_first_quant_architecture]] — shadow-first quant の意図的例外
"""
from __future__ import annotations
import os
from typing import Optional

import pandas as pd

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext


def _kalman_d7_indicators(ctx: SignalContext) -> Optional[dict]:
    """Compute EMA25, EMA75, ATR Q gate, perfect order, transition.

    Returns None when ctx.df is unusable.
    """
    if ctx.df is None or len(ctx.df) < 210:
        return None
    try:
        df = ctx.df
        close_s = df["close"] if "close" in df.columns else df["Close"]
        high_s = df["high"] if "high" in df.columns else df["High"]
        low_s = df["low"] if "low" in df.columns else df["Low"]
    except (KeyError, AttributeError):
        return None
    if close_s is None or len(close_s) < 210:
        return None

    ema25 = close_s.ewm(span=25, adjust=False).mean()
    ema75 = close_s.ewm(span=75, adjust=False).mean()
    ema200_s = close_s.ewm(span=200, adjust=False).mean()

    last = ema25.iloc[-1]
    last_mid = ema75.iloc[-1]
    last_slow = ema200_s.iloc[-1]
    prev_fast = ema25.iloc[-2]
    prev_mid = ema75.iloc[-2]
    prev_slow = ema200_s.iloc[-2]
    last_close = float(close_s.iloc[-1])
    prev_close = float(close_s.iloc[-2])

    # Perfect Order UP (with close-above-EMA25 strict close)
    po_up_now = (last > last_mid) and (last_mid > last_slow) and (last_close > last)
    po_up_prev = (prev_fast > prev_mid) and (prev_mid > prev_slow) and (prev_close > prev_fast)
    po_up_start = po_up_now and not po_up_prev

    # ATR percentile gate (Q2-Q4, P20 <= atr < P80) using ctx.atr if available
    atr_val = float(ctx.atr) if ctx.atr else 0.0
    if atr_val <= 0:
        # Fallback: compute simple TR ATR(14)
        tr = pd.concat([
            high_s - low_s,
            (high_s - close_s.shift()).abs(),
            (low_s - close_s.shift()).abs(),
        ], axis=1).max(axis=1)
        atr_series = tr.ewm(alpha=1/14, adjust=False).mean()
        atr_val = float(atr_series.iloc[-1])
        atr_p20 = float(atr_series.tail(200).quantile(0.20))
        atr_p80 = float(atr_series.tail(200).quantile(0.80))
    else:
        # Use TR-based recalc for percentile reference
        tr = pd.concat([
            high_s - low_s,
            (high_s - close_s.shift()).abs(),
            (low_s - close_s.shift()).abs(),
        ], axis=1).max(axis=1)
        atr_series = tr.ewm(alpha=1/14, adjust=False).mean()
        atr_p20 = float(atr_series.tail(200).quantile(0.20))
        atr_p80 = float(atr_series.tail(200).quantile(0.80))

    if atr_val <= 0:
        return None

    return {
        "ema25": float(last),
        "ema75": float(last_mid),
        "ema200": float(last_slow),
        "po_up_now": bool(po_up_now),
        "po_up_start": bool(po_up_start),
        "atr": atr_val,
        "atr_p20": atr_p20,
        "atr_p80": atr_p80,
    }


def _kalman_d7_passes_filters(ctx: SignalContext, ind: dict) -> tuple[bool, list]:
    """Apply entry filters. Returns (pass, reason_list)."""
    reasons = []
    if not ind["po_up_start"]:
        return False, ["⛔ Perfect Order UP not started this bar"]

    dist_atr = (ctx.entry - ind["ema200"]) / ind["atr"]
    if not (0 < dist_atr < 3.0):
        return False, [f"⛔ DIST {dist_atr:.2f} ATR out of [0,3]"]
    reasons.append(f"✅ DIST {dist_atr:.2f} ATR (< 3)")

    gap_atr = (ind["ema25"] - ind["ema200"]) / ind["atr"]
    if gap_atr >= 3.0:
        return False, [f"⛔ GAP {gap_atr:.2f} ATR (>= 3, EMAs too spread)"]
    reasons.append(f"✅ GAP {gap_atr:.2f} ATR (< 3, early trend)")

    if not (ind["atr_p20"] <= ind["atr"] < ind["atr_p80"]):
        return False, [f"⛔ ATR {ind['atr']:.4f} outside Q2-Q4 [{ind['atr_p20']:.4f}, {ind['atr_p80']:.4f})"]
    reasons.append(f"✅ ATR Q2-Q4 (mid-vol)")

    if ctx.rsi >= 70:
        return False, [f"⛔ RSI {ctx.rsi:.1f} ≥ 70 (overbought)"]
    reasons.append(f"✅ RSI {ctx.rsi:.1f} < 70")

    h = int(ctx.hour_utc) if ctx.hour_utc is not None else 12
    if not ((h < 7) or (7 <= h < 12) or (16 <= h < 21)):
        return False, [f"⛔ session UTC {h:02d} excluded (OVL/DEAD)"]
    reasons.append(f"✅ session UTC {h:02d} (ASN/LDN/NY)")

    reasons.append(f"✅ Perfect Order UP started — EMA25 > EMA75 > EMA200, close > EMA25")
    return True, reasons


class KalmanD7Base(StrategyBase):
    """Base — entry logic shared. Subclasses set name/SL/TP profiles."""
    mode = "daytrade"
    enabled = True
    strategy_type = "trend"  # confidence_v2: legacy formula (trend-follow consistent)

    # Subclasses override
    sl_atr_mul: float = 2.0
    tp_atr_mul: float = 2.5
    max_hold_bars_v: int = 200

    _enabled_symbols = frozenset({"USDJPY"})
    _dedup_state: dict = {}

    @classmethod
    def reset_dedup_state(cls):
        cls._dedup_state.clear()

    def _env_disabled(self) -> bool:
        flag = f"KALMAN_D7_DISABLED"  # global kill-switch
        return os.environ.get(flag) == "1"

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if self._env_disabled():
            return None

        sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        if sym not in self._enabled_symbols:
            return None

        if ctx.tf not in ("15m", "M15"):
            return None

        ind = _kalman_d7_indicators(ctx)
        if ind is None:
            return None

        ok, reasons = _kalman_d7_passes_filters(ctx, ind)
        if not ok:
            return None

        atr = ind["atr"]
        sl = ctx.entry - self.sl_atr_mul * atr
        tp = ctx.entry + self.tp_atr_mul * atr

        # Ensure min RR ~1.0
        if (tp - ctx.entry) < (ctx.entry - sl) * 0.8:
            tp = ctx.entry + (ctx.entry - sl) * 1.2

        reasons.append(f"📐 SL = entry − {self.sl_atr_mul}×ATR = {sl:.3f}")
        reasons.append(f"🎯 TP = entry + {self.tp_atr_mul}×ATR = {tp:.3f}")

        # Score: high confidence given all forensic filters passed
        score = 4.0
        # Bonus if ema200 trend rising
        if ctx.ema200_bull:
            score += 0.3
            reasons.append(f"✅ EMA200 bull (long-term uptrend agree)")
        if ctx.adx >= 25:
            score += 0.3
            reasons.append(f"✅ ADX {ctx.adx:.1f} ≥ 25 (trend confirmed)")
        # MACD histogram positive
        if ctx.macdh > 0 and ctx.macdh > ctx.macdh_prev:
            score += 0.2

        conf = int(min(85, 55 + score * 5))

        return Candidate(
            signal="BUY",
            confidence=conf,
            sl=float(sl),
            tp=float(tp),
            reasons=reasons,
            entry_type=self.name,
            score=float(score),
            max_hold_bars=self.max_hold_bars_v,
        )


class KalmanD7PODNFlip(KalmanD7Base):
    """v17 — wide TP (5×ATR) approximates PO-DN flip exit hold.
    BT: PF 3.866 / WR 23.9% / 巨大 winner ride 型"""
    name = "kalman_d7_po_dn_flip"
    sl_atr_mul = 1.5
    tp_atr_mul = 5.0
    max_hold_bars_v = 480  # ~120h


class KalmanD7EMA75Break(KalmanD7Base):
    """v18f — moderate TP (2.5×ATR) approximates EMA75 break exit timing.
    BT: PF 2.087 / WR 30.9% / 中サイズ winner"""
    name = "kalman_d7_ema75_break"
    sl_atr_mul = 2.5
    tp_atr_mul = 2.5
    max_hold_bars_v = 120  # ~30h


class KalmanD7TrailATR(KalmanD7Base):
    """v18e — tight TP (1.5×ATR), small winner mass production.
    BT: PF 1.181 / WR 55.4% / 高 WR
    Broker-side trailing stop (0.5×ATR) recommended."""
    name = "kalman_d7_trail_atr"
    sl_atr_mul = 2.0
    tp_atr_mul = 1.5
    max_hold_bars_v = 60  # ~15h
