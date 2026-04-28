"""
SR Anti-Hunt Bounce — Stop-hunt-aware S/R reversal strategy (15m daytrade)

設計思想:
  - SL を「nearest swing 直外」ではなく「P90 hunt wick excursion + 0.5 ATR」に置く
  - Shadow で 5 majors 全走、real-time data 蓄積を最優先 (CLAUDE.md 4原則:攻撃は最大の防御)
  - 30 trade 蓄積後に net_edge_audit / cell_edge_audit で per-pair 判定

エントリ条件 (defensive bounce):
  1. ペアフィルター: 5 majors 全部 (USDJPY/EURUSD/GBPUSD/EURJPY/GBPJPY)
  2. 近接 SR level: |entry - level| < 0.4 ATR
  3. 直近 N=2 本で SR 越えの hunt-style wick が無い
  4. レジーム: ADX < 30
  5. 反転足確認: signal 方向と整合する実体

SL = level − sign × (P90_excursion + 0.5 × ATR)  ※anti-hunt placement
TP: 直近の対側 SR or RR=2.0 / MIN_RR=1.5
"""
from __future__ import annotations
from typing import Optional

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from modules.round_number import (
    expand_sl_for_round, shift_tp_inside, is_near_round,
)


class SrAntiHuntBounce(StrategyBase):

    name = "sr_anti_hunt_bounce"
    mode = "daytrade"
    enabled = True   # Shadow 全走で data 蓄積 (PAIR_PROMOTED 不在で OANDA は default Sentinel)
    strategy_type = "MR"

    # 5 majors 全部 — Shadow data で per-pair edge を実測判定する
    _ALLOWED_SYMBOLS = frozenset({"USDJPY", "EURUSD", "GBPUSD", "EURJPY", "GBPJPY"})

    SR_PROXIMITY_ATR = 0.4
    ADX_MAX = 30
    CONFIRMATION_BARS = 2

    # Phase 2 audit (k=2.0) 由来 P90 excursion (pip)
    _P90_EXCURSION_PIP = {
        "EURUSD": 37.0,
        "GBPUSD": 53.0,
        "USDJPY": 50.0,
        "EURJPY": 49.0,  # audit 値、Shadow real-time で再評価
        "GBPJPY": 59.0,
    }
    SL_ATR_BUFFER = 0.5
    SL_FALLBACK_ATR = 1.5

    MIN_RR = 1.5
    TARGET_RR = 2.0

    MAX_HOLD_BARS = 12

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        if sym not in self._ALLOWED_SYMBOLS:
            return None
        if not ctx.sr_levels:
            return None
        if ctx.adx >= self.ADX_MAX:
            return None

        atr = max(ctx.atr, 1e-9)
        proximity_distance = self.SR_PROXIMITY_ATR * atr
        nearest_level = None
        nearest_dist = float("inf")
        for lv in ctx.sr_levels:
            price = float(lv.get("price", 0.0)) if isinstance(lv, dict) else float(lv)
            d = abs(ctx.entry - price)
            if d < nearest_dist:
                nearest_dist = d
                nearest_level = price
        if nearest_level is None or nearest_dist > proximity_distance:
            return None

        if ctx.entry > nearest_level:
            side = "support"
            signal = "BUY"
        else:
            side = "resistance"
            signal = "SELL"

        if signal == "BUY" and ctx.entry <= ctx.open_price:
            return None
        if signal == "SELL" and ctx.entry >= ctx.open_price:
            return None

        if not self._confirmed_no_recent_hunt(ctx, nearest_level, side):
            return None

        sl, tp = self._compute_sl_tp(ctx, nearest_level, signal, sym)
        if sl is None or tp is None:
            return None

        if signal == "BUY":
            risk = ctx.entry - sl
            reward = tp - ctx.entry
        else:
            risk = sl - ctx.entry
            reward = ctx.entry - tp
        if risk <= 0 or reward <= 0:
            return None
        rr = reward / risk
        if rr < self.MIN_RR:
            return None

        score = 3.0
        reasons = [
            f"✅ SR近接({nearest_level:.5f}, dist={nearest_dist/atr:.2f}ATR) bounce候補",
            f"✅ {side}側、{signal} シグナル, RR={rr:.2f}",
            f"✅ Anti-hunt SL: {sl:.5f}（P90+ATR バッファ）",
            f"✅ レジーム OK (ADX={ctx.adx:.1f}<{self.ADX_MAX})",
        ]
        if signal == "BUY" and ctx.bbpb < 0.3:
            score += 0.5
            reasons.append(f"✅ BB下限一致 (BB%B={ctx.bbpb:.2f})")
        elif signal == "SELL" and ctx.bbpb > 0.7:
            score += 0.5
            reasons.append(f"✅ BB上限一致 (BB%B={ctx.bbpb:.2f})")

        # 2026-04-28: hunt event log for sr_audit Stage A+B
        try:
            from modules.hunt_event_logger import log_hunt_event
            log_hunt_event(
                strategy=self.name, instrument=ctx.symbol, direction=signal,
                entry_price=float(ctx.entry), sl=float(sl), tp=float(tp),
                level=float(nearest_level), side=side, atr_price=float(atr),
                extra={"adx": float(ctx.adx), "bbpb": float(ctx.bbpb),
                       "rr": float(rr), "score": float(score)},
            )
        except Exception:
            pass  # never let logging break the strategy

        return Candidate(
            signal=signal,
            confidence=min(100, int(score * 20)),
            sl=float(sl),
            tp=float(tp),
            reasons=reasons,
            entry_type=self.name,
            score=float(score),
        )

    def _confirmed_no_recent_hunt(self, ctx: SignalContext,
                                   level: float, side: str) -> bool:
        if ctx.df is None or len(ctx.df) < self.CONFIRMATION_BARS + 1:
            return False
        recent = ctx.df.iloc[-(self.CONFIRMATION_BARS + 1):-1]
        atr = max(ctx.atr, 1e-9)
        threshold = 1.0 * atr
        for _, row in recent.iterrows():
            high = float(row["High"])
            low = float(row["Low"])
            close = float(row["Close"])
            if side == "resistance":
                if high > level and close < level and (high - level) > threshold:
                    return False
            else:
                if low < level and close > level and (level - low) > threshold:
                    return False
        return True

    def _compute_sl_tp(self, ctx: SignalContext, level: float,
                       signal: str, sym: str):
        atr = max(ctx.atr, 1e-9)
        pip_size = 0.01 if "JPY" in sym else 0.0001

        p90_pip = self._P90_EXCURSION_PIP.get(sym)
        if p90_pip is not None:
            p90_price = p90_pip * pip_size
        else:
            p90_price = self.SL_FALLBACK_ATR * atr

        sl_buffer = p90_price + self.SL_ATR_BUFFER * atr

        if signal == "BUY":
            sl = level - sl_buffer
            # RNR: round-number 近傍の SR は更に深い SL (狩り集中)
            sl = expand_sl_for_round(sl, level, "BUY", pip=pip_size,
                                       expand_factor=1.3, atr=atr)
            sl_dist = ctx.entry - sl
            target_above = [float(lv["price"]) if isinstance(lv, dict) else float(lv)
                            for lv in ctx.sr_levels
                            if (float(lv["price"]) if isinstance(lv, dict)
                                else float(lv)) > ctx.entry + 0.3 * atr]
            rr_tp = ctx.entry + self.TARGET_RR * sl_dist
            tp = min(target_above + [rr_tp]) if target_above else rr_tp
            # RNR: TP が round number 越えなら 3 pip 内側に
            tp = shift_tp_inside(tp, "BUY", pip=pip_size, shift_pips=3.0)
        else:
            sl = level + sl_buffer
            sl = expand_sl_for_round(sl, level, "SELL", pip=pip_size,
                                       expand_factor=1.3, atr=atr)
            sl_dist = sl - ctx.entry
            target_below = [float(lv["price"]) if isinstance(lv, dict) else float(lv)
                            for lv in ctx.sr_levels
                            if (float(lv["price"]) if isinstance(lv, dict)
                                else float(lv)) < ctx.entry - 0.3 * atr]
            rr_tp = ctx.entry - self.TARGET_RR * sl_dist
            tp = max(target_below + [rr_tp]) if target_below else rr_tp
            tp = shift_tp_inside(tp, "SELL", pip=pip_size, shift_pips=3.0)

        return sl, tp
