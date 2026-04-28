"""
SR Liquidity Grab — Stop-hunt reversal entry (15m daytrade) — Smart Money Concept 流

Shadow 5 majors 全走 — 30 trade 蓄積で per-pair edge 実測判定
"""
from __future__ import annotations
from typing import Optional

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from modules.round_number import shift_tp_inside, round_confluence_boost, is_near_round


class SrLiquidityGrab(StrategyBase):

    name = "sr_liquidity_grab"
    mode = "daytrade"
    enabled = True   # Shadow 全走で data 蓄積
    strategy_type = "reversal"

    _ALLOWED_SYMBOLS = frozenset({"USDJPY", "EURUSD", "GBPUSD", "EURJPY", "GBPJPY"})

    SR_PROXIMITY_ATR = 0.5
    ADX_MAX = 30
    HUNT_K_ATR = 2.0
    HUNT_LOOKBACK = 2
    SL_BUFFER_ATR = 0.3
    TARGET_RR = 1.5
    MAX_HOLD_BARS = 8

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        if sym not in self._ALLOWED_SYMBOLS:
            return None
        if not ctx.sr_levels:
            return None
        if ctx.adx >= self.ADX_MAX:
            return None
        if ctx.df is None or len(ctx.df) < self.HUNT_LOOKBACK + 1:
            return None

        atr = max(ctx.atr, 1e-9)

        nearest_level = None
        nearest_dist = float("inf")
        for lv in ctx.sr_levels:
            price = float(lv.get("price", 0.0)) if isinstance(lv, dict) else float(lv)
            d = abs(ctx.entry - price)
            if d < nearest_dist:
                nearest_dist = d
                nearest_level = price
        if nearest_level is None or nearest_dist > self.SR_PROXIMITY_ATR * atr:
            return None

        hunt_event = self._find_recent_hunt(ctx, nearest_level, atr)
        if hunt_event is None:
            return None

        side = hunt_event["side"]
        if side == "resistance":
            if ctx.entry >= ctx.open_price or ctx.entry >= nearest_level:
                return None
            signal = "SELL"
            sl = hunt_event["extreme"] + self.SL_BUFFER_ATR * atr
        else:
            if ctx.entry <= ctx.open_price or ctx.entry <= nearest_level:
                return None
            signal = "BUY"
            sl = hunt_event["extreme"] - self.SL_BUFFER_ATR * atr

        pip = 0.01 if "JPY" in sym else 0.0001
        if signal == "BUY":
            sl_dist = ctx.entry - sl
            target_above = [
                float(lv["price"]) if isinstance(lv, dict) else float(lv)
                for lv in ctx.sr_levels
                if (float(lv["price"]) if isinstance(lv, dict)
                    else float(lv)) > ctx.entry + 0.3 * atr
            ]
            rr_tp = ctx.entry + self.TARGET_RR * sl_dist
            tp = min(target_above + [rr_tp]) if target_above else rr_tp
            # RNR: TP shift away from round number where stops cluster
            tp = shift_tp_inside(tp, "BUY", pip=pip, shift_pips=3.0)
        else:
            sl_dist = sl - ctx.entry
            target_below = [
                float(lv["price"]) if isinstance(lv, dict) else float(lv)
                for lv in ctx.sr_levels
                if (float(lv["price"]) if isinstance(lv, dict)
                    else float(lv)) < ctx.entry - 0.3 * atr
            ]
            rr_tp = ctx.entry - self.TARGET_RR * sl_dist
            tp = max(target_below + [rr_tp]) if target_below else rr_tp
            tp = shift_tp_inside(tp, "SELL", pip=pip, shift_pips=3.0)

        if signal == "BUY":
            risk = ctx.entry - sl
            reward = tp - ctx.entry
        else:
            risk = sl - ctx.entry
            reward = ctx.entry - tp
        if risk <= 0 or reward <= 0:
            return None
        rr = reward / risk
        if rr < self.TARGET_RR * 0.9:
            return None

        score = 3.5
        if hunt_event["excursion_atr_ratio"] > 2.5:
            score += 0.5
        # RNR: round-number 近傍 hunt は機関 stop が集中 = 強い liquidity grab edge
        rn_boost = round_confluence_boost(nearest_level, pip, threshold_pips=3.0)
        if rn_boost > 0:
            score += 0.5 * rn_boost  # up to +0.5 score for exact round number

        reasons = [
            f"✅ Hunt 検出: {side}, excursion={hunt_event['excursion']:.5f} "
            f"(={hunt_event['excursion_atr_ratio']:.2f}×ATR)",
            f"✅ Liquidity grab {signal}, level={nearest_level:.5f}",
            f"✅ Anti-hunt SL: {sl:.5f} (hunt_extreme±0.3 ATR)",
            f"✅ RR={rr:.2f} ≥ {self.TARGET_RR}",
        ]

        # 2026-04-28: hunt event log for sr_audit Stage A+B
        try:
            from modules.hunt_event_logger import log_hunt_event
            log_hunt_event(
                strategy=self.name, instrument=ctx.symbol, direction=signal,
                entry_price=float(ctx.entry), sl=float(sl), tp=float(tp),
                level=float(nearest_level), side=side, atr_price=float(atr),
                extra={
                    "adx": float(ctx.adx),
                    "rr": float(rr), "score": float(score),
                    "hunt_extreme_price": float(hunt_event["extreme"]),
                    "hunt_excursion": float(hunt_event["excursion"]),
                    "hunt_excursion_atr_ratio": float(hunt_event["excursion_atr_ratio"]),
                },
            )
        except Exception:
            pass

        return Candidate(
            signal=signal,
            confidence=min(100, int(score * 20)),
            sl=float(sl),
            tp=float(tp),
            reasons=reasons,
            entry_type=self.name,
            score=float(score),
        )

    def _find_recent_hunt(self, ctx: SignalContext, level: float,
                           atr: float) -> Optional[dict]:
        threshold = self.HUNT_K_ATR * atr
        for i in range(1, self.HUNT_LOOKBACK + 1):
            if i >= len(ctx.df):
                break
            row = ctx.df.iloc[-1 - i]
            high = float(row["High"])
            low = float(row["Low"])
            close = float(row["Close"])
            if high > level and close < level and (high - level) > threshold:
                excursion = high - level
                return {
                    "side": "resistance",
                    "extreme": high,
                    "excursion": excursion,
                    "excursion_atr_ratio": excursion / atr,
                    "bars_ago": i,
                }
            if low < level and close > level and (level - low) > threshold:
                excursion = level - low
                return {
                    "side": "support",
                    "extreme": low,
                    "excursion": excursion,
                    "excursion_atr_ratio": excursion / atr,
                    "bars_ago": i,
                }
        return None
