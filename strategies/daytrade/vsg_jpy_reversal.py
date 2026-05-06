"""
VSG JPY Reversal — EWMA-forecast Vol Surprise Reversal (15m daytrade)

仮説 (Engle-Patton 2001 + 実測):
  Realized return が EWMA(λ=0.94) forecast に対し
  (realized - forecast) / forecast > 1.5  (= realized/forecast > 2.5×)
  となる「vol surprise」発生時、JPY crosses (EUR_JPY, GBP_JPY) は
  **fade** する (mean reversion)。panic / carry unwind 系 event は
  overshoot → 反転構造。

vsg_audit (2026-04-27, 365d) 結果 — 同一の (realized-forecast)/forecast 式で取得:
  EUR_JPY reversal th=1.5 fw=2: WR 58.1%, n=718, p_bonf 0.00081 ✅
  EUR_JPY reversal th=2.0 fw=2: WR 59.4%, n=367, p_bonf 0.01674 ✅
  GBP_JPY reversal th=1.0 fw=4: WR 55.6%, n=1439, p_bonf 0.00108 ✅
  → Bonferroni 90-test family で 7 combo 通過 — 真のエッジ確定

エントリ:
  - Symbol: EUR_JPY, GBP_JPY のみ (Bonferroni 通過 pair)
  - 直前 bar の (|realized_ret| - EWMA_forecast) / EWMA_forecast > 1.5
    (= realized が forecast の 2.5x を超える surprise event)
  - direction = -sign(realized_ret) → fade 方向
  - SL = 1 ATR、TP = 1.5 ATR (RR 1.5)
  - Hold ≤ 4 bars (60 min)

Live/BT 整合 (rule:R1, 2026-04-30):
  - BT: ctx.df.iloc[-1] = closed bar t → realized=iloc[-1], forecast=iloc[-2]
  - Live: ctx.df.iloc[-1] = 進行中バー → realized=iloc[-2], forecast=iloc[-3]
    (closed bar t-1 を評価。audit と同じ semantics)
  - 同一 closed bar への重複 emit は per-bar dedup でブロック
    (BT/Live 共通で 1 bar 1 emit を保証)

Shadow: enabled=True、PAIR_PROMOTED 追加なし default Sentinel
"""
from __future__ import annotations
import os
from typing import Optional

import numpy as np

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from modules.round_number import shift_tp_inside


class VsgJpyReversal(StrategyBase):

    name = "vsg_jpy_reversal"
    mode = "daytrade"
    enabled = True   # Bonferroni-significant edge — Shadow data 蓄積で確認
    strategy_type = "MR"

    # Bonferroni 通過 pair のみ (USD_JPY は EWMA surprise で edge 弱い)
    _ALLOWED_SYMBOLS = frozenset({"EURJPY", "GBPJPY"})

    SURPRISE_THRESHOLD = 1.5      # (|realized| - forecast) / forecast > 1.5  (= realized/forecast > 2.5x)
    EWMA_LAMBDA = 0.94            # RiskMetrics standard

    SL_ATR_MULT = 1.0
    TP_ATR_MULT = 1.5
    MIN_RR = 1.4

    MAX_HOLD_BARS = 4
    REDESIGN_V2_SL_ATR_MULT = 1.8
    REDESIGN_V2_TP_ATR_MULT = 0.9
    REDESIGN_V2_THRESHOLDS = {
        "EURJPY": 1.5,
        "GBPJPY": 1.0,
    }
    REDESIGN_V2_MAX_HOLD_BARS = {
        "EURJPY": 2,
        "GBPJPY": 4,
    }

    @staticmethod
    def _redesign_v2_enabled() -> bool:
        return os.environ.get("VSG_JPY_REVERSAL_REDESIGN_V2", "0").lower() in ("1", "true", "yes")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs) if hasattr(super(), "__init__") else None
        # rule:R1 (2026-04-30): per-bar dedup — same closed bar can only emit once
        # per (symbol, direction). Prevents intra-bar multi-emit when polled at 30s.
        self._last_emit_bar: dict = {}

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        if sym not in self._ALLOWED_SYMBOLS:
            return None
        if ctx.df is None or len(ctx.df) < 31:
            return None

        # ── Live/BT 整合 (rule:R1, 2026-04-30) ──
        # BT: iloc[-1] は "現在評価中の closed bar" (audit と同じ)
        # Live: iloc[-1] は in-progress bar → 1 つ手前 (iloc[-2]) が closed bar
        if ctx.backtest_mode:
            realized_idx, forecast_idx = -1, -2
        else:
            realized_idx, forecast_idx = -2, -3

        returns = ctx.df["Close"].pct_change().fillna(0)
        sq_ret = returns ** 2
        ewma_var = sq_ret.ewm(alpha=1 - self.EWMA_LAMBDA, adjust=False).mean()
        forecast = float(np.sqrt(ewma_var.iloc[forecast_idx]))
        realized = float(abs(returns.iloc[realized_idx]))

        if forecast <= 1e-9:
            return None
        surprise = (realized - forecast) / forecast

        redesign_v2 = self._redesign_v2_enabled()
        surprise_threshold = (
            self.REDESIGN_V2_THRESHOLDS.get(sym, self.SURPRISE_THRESHOLD)
            if redesign_v2 else self.SURPRISE_THRESHOLD
        )

        if surprise <= surprise_threshold:
            return None

        # Direction: fade
        last_ret = float(returns.iloc[realized_idx])
        if last_ret == 0:
            return None
        signal = "SELL" if last_ret > 0 else "BUY"

        # Per-bar dedup: same closed bar + same symbol + same direction → block.
        # Intra-bar polling (30s cadence) hits same closed bar repeatedly; without
        # this, we get up to N emits per bar (observed 2026-04-30: 5/bar).
        try:
            bar_id = ctx.df.index[realized_idx]
        except Exception:
            bar_id = None
        dedup_key = (ctx.symbol, signal)
        if bar_id is not None and self._last_emit_bar.get(dedup_key) == bar_id:
            return None

        atr = max(ctx.atr, 1e-9)
        sl_atr_mult = self.REDESIGN_V2_SL_ATR_MULT if redesign_v2 else self.SL_ATR_MULT
        tp_atr_mult = self.REDESIGN_V2_TP_ATR_MULT if redesign_v2 else self.TP_ATR_MULT
        if signal == "BUY":
            sl = ctx.entry - sl_atr_mult * atr
            tp = ctx.entry + tp_atr_mult * atr
        else:
            sl = ctx.entry + sl_atr_mult * atr
            tp = ctx.entry - tp_atr_mult * atr

        # RNR: TP shift away from round numbers
        tp = shift_tp_inside(tp, signal, pip=0.01, shift_pips=3.0)

        sl_dist = abs(ctx.entry - sl)
        tp_dist = abs(tp - ctx.entry)
        if sl_dist <= 0:
            return None
        rr = tp_dist / sl_dist
        if tp_dist <= 0:
            return None
        if not redesign_v2 and rr < self.MIN_RR:
            return None

        score = 4.0 + min(2.0, surprise - 1.0)   # bigger surprise → higher score

        ratio = 1.0 + surprise   # realized / forecast
        max_hold_bars = (
            self.REDESIGN_V2_MAX_HOLD_BARS.get(sym, self.MAX_HOLD_BARS)
            if redesign_v2 else None
        )
        reasons = [
            f"✅ Vol surprise: realized/forecast={ratio:.2f}x (>{1+surprise_threshold:.1f}x)",
            f"✅ Fade {signal} (last_ret={last_ret*100:+.3f}%)",
            (
                f"✅ VSG_JPY_REVERSAL_REDESIGN_V2 geometry "
                f"SL={sl_atr_mult:.1f}ATR TP={tp_atr_mult:.1f}ATR "
                f"RR={rr:.2f} hold≤{max_hold_bars}bar"
            ) if redesign_v2 else f"✅ RR={rr:.2f} hold≤{self.MAX_HOLD_BARS}bar",
        ]

        # Mark this closed bar as emitted so subsequent intra-bar polls are no-ops.
        if bar_id is not None:
            self._last_emit_bar[dedup_key] = bar_id

        return Candidate(
            signal=signal,
            confidence=min(100, int(score * 16)),
            sl=float(sl),
            tp=float(tp),
            reasons=reasons,
            entry_type=self.name,
            score=float(score),
            max_hold_bars=max_hold_bars,
        )
