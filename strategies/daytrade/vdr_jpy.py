"""
VDR JPY — VWAP Deviation Reversion (JPY crosses 限定, 15m daytrade)

仮説 (Madhavan-Smidt 1991, Almgren-Chriss 2001):
  Daily session VWAP からの ±1.5σ ATR 乖離は機関 benchmark 圧力で反転。
  JPY pairs では特に強い (institutional dealing が VWAP enforced)。

vdr_audit (2026-04-27, 365d) 結果:
  USD_JPY σ=2.0 fw=2: WR 63.6%, EV +12.46p (sim), PF 3.62, Kelly 0.39 (n=11)
  EUR_JPY σ=1.5 fw=2: WR 68.0%, n=25, p_raw 0.054
  GBP_JPY σ=1.5 fw=8: WR 66.7%, n=21
  → JPY pairs 全て positive edge、EUR_USD は anti-edge (除外)
  → Bonferroni narrow miss、Sentinel deploy adequate

エントリ:
  - Symbol filter: USDJPY/EURJPY/GBPJPY のみ
  - daily session VWAP からの (entry - VWAP) / ATR の絶対値 > 1.5
  - direction = -sign(deviation) → toward VWAP
  - SL = 1 ATR (反対方向)、TP = VWAP (or RR 1.5 のどちらか近い方)
  - Hold ≤ 4 bars (60 min)

Shadow: enabled=True, PAIR_PROMOTED 追加なし (default Sentinel 0.01lot)
"""
from __future__ import annotations
import os
from typing import Optional

import numpy as np

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from modules.round_number import shift_tp_inside


class VdrJpy(StrategyBase):

    name = "vdr_jpy"
    mode = "daytrade"
    enabled = True   # Shadow data accumulation
    strategy_type = "MR"

    _ALLOWED_SYMBOLS = frozenset({"USDJPY", "EURJPY", "GBPJPY"})

    DEV_SIGMA_THRESHOLD = 1.5      # |entry - VWAP| / ATR > 1.5
    V2_DEV_SIGMA_THRESHOLDS = {
        "USDJPY": 2.0,
        "EURJPY": 1.5,
        "GBPJPY": 1.5,
    }
    SL_ATR_MULT = 1.0
    MIN_RR = 1.2                   # VWAP target may be closer than RR=2 sometimes
    TARGET_RR_FALLBACK = 1.5       # if VWAP is not far enough

    MAX_HOLD_BARS = 4              # 60 min
    V2_USDJPY_MAX_HOLD_BARS = 2    # raw audit best: USD_JPY sigma=2.0 fw=2

    @staticmethod
    def _redesign_v2_enabled() -> bool:
        return os.environ.get("VDR_JPY_REDESIGN_V2", "0").lower() in ("1", "true", "yes")

    def _dev_sigma_threshold(self, sym: str) -> float:
        if self._redesign_v2_enabled():
            return self.V2_DEV_SIGMA_THRESHOLDS.get(sym, self.DEV_SIGMA_THRESHOLD)
        return self.DEV_SIGMA_THRESHOLD

    def _max_hold_bars(self, sym: str) -> Optional[int]:
        if not self._redesign_v2_enabled():
            return None
        if sym == "USDJPY":
            return self.V2_USDJPY_MAX_HOLD_BARS
        return self.MAX_HOLD_BARS

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        if sym not in self._ALLOWED_SYMBOLS:
            return None
        if ctx.df is None or len(ctx.df) < 50:
            return None

        # Compute today's session VWAP from ctx.df
        vwap = self._session_vwap(ctx)
        if vwap is None or vwap <= 0:
            return None

        atr = max(ctx.atr, 1e-9)
        deviation = ctx.entry - vwap
        dev_atr = deviation / atr
        dev_threshold = self._dev_sigma_threshold(sym)

        if abs(dev_atr) < dev_threshold:
            return None

        # Direction: toward VWAP
        if dev_atr > 0:
            signal = "SELL"   # entry above VWAP → expect drop
            sl = ctx.entry + self.SL_ATR_MULT * atr
            target_vwap_dist = ctx.entry - vwap
            rr_fallback_dist = self.TARGET_RR_FALLBACK * (sl - ctx.entry)
            tp_dist = max(target_vwap_dist, rr_fallback_dist)
            tp = ctx.entry - tp_dist
        else:
            signal = "BUY"
            sl = ctx.entry - self.SL_ATR_MULT * atr
            target_vwap_dist = vwap - ctx.entry
            rr_fallback_dist = self.TARGET_RR_FALLBACK * (ctx.entry - sl)
            tp_dist = max(target_vwap_dist, rr_fallback_dist)
            tp = ctx.entry + tp_dist

        # RNR: TP shift away from round numbers (JPY pip = 0.01)
        tp = shift_tp_inside(tp, signal, pip=0.01, shift_pips=3.0)

        sl_dist = abs(ctx.entry - sl)
        tp_dist = abs(tp - ctx.entry)
        if sl_dist <= 0:
            return None
        rr = tp_dist / sl_dist
        if rr < self.MIN_RR:
            return None

        # Confirmation: v1 uses a hard gate; v2 keeps the candidate and scores
        # the candle as evidence so entry timing can be observed in shadow.
        confirms_candle = (
            (signal == "BUY" and ctx.entry >= ctx.open_price)
            or (signal == "SELL" and ctx.entry <= ctx.open_price)
        )
        if not self._redesign_v2_enabled() and not confirms_candle:
            return None

        score = 4.0
        # Stronger deviations score higher
        if abs(dev_atr) > 2.0:
            score += 0.5
        if abs(dev_atr) > 2.5:
            score += 0.5
        if self._redesign_v2_enabled():
            score += 0.25 if confirms_candle else -0.50

        max_hold_bars = self._max_hold_bars(sym)
        reasons = [
            f"✅ VWAP deviation: {dev_atr:+.2f}×ATR (>{dev_threshold})",
            f"✅ {signal} toward VWAP {vwap:.3f} from entry {ctx.entry:.3f}",
            f"✅ RR={rr:.2f} (target VWAP, hold≤{max_hold_bars or self.MAX_HOLD_BARS}bar)",
        ]
        if self._redesign_v2_enabled():
            reasons.append("✅ VDR_JPY_REDESIGN_V2: pair-specific trigger/time-exit variant")
            if confirms_candle:
                reasons.append("✅ candle confirmation score bonus")
            else:
                reasons.append("⚠️ candle confirmation absent: score penalty, not hard gate")

        return Candidate(
            signal=signal,
            confidence=min(100, int(score * 18)),
            sl=float(sl),
            tp=float(tp),
            reasons=reasons,
            entry_type=self.name,
            score=float(score),
            max_hold_bars=max_hold_bars,
        )

    def _session_vwap(self, ctx: SignalContext) -> Optional[float]:
        """Compute current session (UTC day) cumulative VWAP."""
        df = ctx.df
        try:
            if "vwap" in df.columns:
                # Per-bar VWAP exists from cache — use the latest
                vwap_latest = float(df["vwap"].iloc[-1])
                if np.isfinite(vwap_latest) and vwap_latest > 0:
                    return vwap_latest
            # Fallback: compute session VWAP from current UTC date
            current_date = df.index[-1].date()
            session = df[df.index.date == current_date]
            if len(session) < 4:
                # Insufficient session bars → use last 30 bars as proxy
                session = df.tail(30)
            tpv = ((session["High"] + session["Low"] + session["Close"]) / 3
                   * session["Volume"]).sum()
            vol = session["Volume"].sum()
            if vol <= 0:
                return None
            return float(tpv / vol)
        except Exception:
            return None
