"""H1 Order Block Retest strategy.

Pre-registered on 2026-05-18. Parameters are LOCKED; do not tune post-hoc.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext


@dataclass(frozen=True)
class _OrderBlock:
    side: str
    high: float
    low: float
    age: int
    index: int


class ObRetestH1(StrategyBase):
    name = "ob_retest_h1"
    mode = "hourly"
    # Pre-reg 365d BT on 2026-05-18 failed LOCK criteria (all pairs N<200).
    # Keep registered for future review, but do not emit live/shadow candidates.
    enabled = False

    # OB detection
    IMPULSE_MIN_BARS = 3
    IMPULSE_ATR_MULT = 2.0
    OB_LOOKBACK = 60
    OB_FRESHNESS = 50
    OB_MAX_WIDTH_ATR = 2.0

    # Entry confirmation
    EMA_FAST = 9
    EMA_SLOW = 21
    RETEST_BUFFER_ATR = 0.10

    # Risk
    SL_BUFFER_ATR = 0.10
    TP_R_MULT = 1.5

    # Pairs
    ALLOWED_PAIRS = {"USDJPY", "EURUSD", "GBPUSD", "EURJPY", "GBPJPY"}

    MAX_HOLD_BARS = 24

    def _pair_key(self, ctx: SignalContext) -> str:
        symbol = (ctx.symbol or "").upper()
        return symbol.replace("=X", "").replace("/", "").replace("_", "")

    def _find_order_blocks(self, ctx: SignalContext) -> list[_OrderBlock]:
        df = ctx.df
        if df is None or len(df) < self.IMPULSE_MIN_BARS + 2:
            return []

        current_idx = len(df) - 1
        first_idx = max(0, current_idx - self.OB_LOOKBACK)
        last_candidate = current_idx - self.IMPULSE_MIN_BARS - 1
        if last_candidate < first_idx:
            return []

        blocks: list[_OrderBlock] = []
        for idx in range(first_idx, last_candidate + 1):
            candidate = df.iloc[idx]
            impulse = df.iloc[idx + 1:idx + 1 + self.IMPULSE_MIN_BARS]
            if len(impulse) < self.IMPULSE_MIN_BARS:
                continue

            atr = float(candidate.get("atr", ctx.atr))
            if atr <= 0:
                continue

            ob_high = float(candidate["High"])
            ob_low = float(candidate["Low"])
            ob_range = ob_high - ob_low
            if ob_range <= 0 or ob_range > atr * self.OB_MAX_WIDTH_ATR:
                continue

            age = current_idx - (idx + self.IMPULSE_MIN_BARS)
            if age > self.OB_FRESHNESS:
                continue

            cand_open = float(candidate["Open"])
            cand_close = float(candidate["Close"])
            impulse_range = float(impulse["High"].max()) - float(impulse["Low"].min())

            if cand_close < cand_open:
                all_bullish = bool((impulse["Close"] > impulse["Open"]).all())
                if all_bullish and impulse_range >= atr * self.IMPULSE_ATR_MULT:
                    blocks.append(_OrderBlock("BUY", ob_high, ob_low, age, idx))

            if cand_close > cand_open:
                all_bearish = bool((impulse["Close"] < impulse["Open"]).all())
                if all_bearish and impulse_range >= atr * self.IMPULSE_ATR_MULT:
                    blocks.append(_OrderBlock("SELL", ob_high, ob_low, age, idx))

        return blocks

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if self._pair_key(ctx) not in self.ALLOWED_PAIRS:
            return None
        if ctx.df is None or len(ctx.df) < self.OB_LOOKBACK:
            return None

        row = ctx.df.iloc[-1]
        entry = float(ctx.entry if ctx.entry else row["Close"])
        open_price = float(ctx.open_price if ctx.open_price else row["Open"])
        close = float(row["Close"])
        high = float(row["High"])
        low = float(row["Low"])
        atr = float(row.get("atr", ctx.atr))
        ema_fast = float(row.get(f"ema{self.EMA_FAST}", ctx.ema9))
        ema_slow = float(row.get(f"ema{self.EMA_SLOW}", ctx.ema21))
        if atr <= 0:
            return None

        buffer = self.RETEST_BUFFER_ATR * atr
        sl_buffer = self.SL_BUFFER_ATR * atr
        blocks = self._find_order_blocks(ctx)
        if not blocks:
            return None

        # Prefer the freshest valid block; ties choose the narrower zone.
        blocks = sorted(blocks, key=lambda ob: (ob.age, ob.high - ob.low))
        for ob in blocks:
            if ob.side == "BUY":
                touched = low <= ob.high + buffer and low >= ob.low - buffer
                confirmed = close > open_price and ema_fast > ema_slow and close > ema_slow
                if not (touched and confirmed):
                    continue
                sl = ob.low - sl_buffer
                risk = entry - sl
                if risk <= 0:
                    continue
                tp = entry + risk * self.TP_R_MULT
                return self._candidate("BUY", entry, sl, tp, atr, ob, ctx)

            touched = high >= ob.low - buffer and high <= ob.high + buffer
            confirmed = close < open_price and ema_fast < ema_slow and close < ema_slow
            if not (touched and confirmed):
                continue
            sl = ob.high + sl_buffer
            risk = sl - entry
            if risk <= 0:
                continue
            tp = entry - risk * self.TP_R_MULT
            return self._candidate("SELL", entry, sl, tp, atr, ob, ctx)

        return None

    def _candidate(self, signal: str, entry: float, sl: float, tp: float,
                   atr: float, ob: _OrderBlock, ctx: SignalContext) -> Candidate:
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        rr = reward / risk if risk > 0 else 0.0
        sl_pips = risk * ctx.pip_mult
        tp_pips = reward * ctx.pip_mult
        score = 5.0
        reasons = [
            f"✅ OB Retest H1 {signal}: fresh OB age={ob.age}",
            f"✅ Retest confirmed: EMA{self.EMA_FAST}/EMA{self.EMA_SLOW} aligned",
            f"📊 RR={rr:.2f} SL={sl_pips:.1f}pip TP={tp_pips:.1f}pip ATR={atr * ctx.pip_mult:.1f}pip",
        ]
        confidence = int(min(85, 50 + score * 4))
        return Candidate(
            signal=signal,
            confidence=confidence,
            sl=sl,
            tp=tp,
            reasons=reasons,
            entry_type=self.name,
            score=score,
            max_hold_bars=self.MAX_HOLD_BARS,
        )
