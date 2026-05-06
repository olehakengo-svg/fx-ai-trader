"""MTF Regime-Aware Range Cascade Scalp — DISABLED by data (rule:R1)

設計の歴史 (重要):
  v1 (2026-04-29 廃案): regime == "range" 限定 MR cascade.
  v2 (2026-04-30, **enabled=False, deprecated**):
    demo_trades.db (N=462) ラベル実測クエリで仮説否定:
    - bb_rsi_reversion × range_tight: N=8  WR=12.5% (Wilson_lo=2.24%)
    - engulfing_bb     × range_tight: N=5  WR=20.0%
    - sr_channel_reversal × range_tight: N=10 WR=0.0% (Wilson_lo=0%)
    → 「range_tight regime での MR」は実測で構造的に負ける.
    moderate_trend (mtf_regime_trend_cascade_scalp v2) に edge を集約し、
    本戦略は **enabled=False** で残置 (将来再評価のため code は保持).

無効化理由:
  Rule 3 (Immediate, 算数破綻寄り): 既存戦略の同種 cell が WR<25% で
  Wilson_lo<10% — 365 日 BT を回す前に enable を外す方がコスト効率良い.
  失敗時継続検証で「別の range trigger (例: three_bar_reversal)」を
  試す場合は enabled=True に戻す.

KB references:
  - knowledge-base/wiki/decisions/regime-cascade-empirical-redesign-2026-04-30.md
"""
from __future__ import annotations
import os
from typing import Optional

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from modules.confidence_v2 import apply_penalty
from modules.spread_gate import should_block
from modules.regime_classifier import classify_15m, REGIME_RANGE, REGIME_MODERATE_TREND


_ALLOWED_PAIRS = {"USD_JPY", "EUR_USD"}
_RR_FLOOR_TIER1 = 3.0   # 極端ゾーン (BB%B≥0.95 / ≤0.05)
_RR_FLOOR_TIER2 = 2.5   # 通常 (bb_rsi_reversion v11.1 と同一基準)
_MAX_SL_PIPS = 12.0     # SL 距離 12pip 超は exhaustion 失敗 → reject


def _normalize_pair(symbol: str) -> str:
    s = (symbol or "").upper().replace("=X", "").replace("/", "_")
    if "_" in s:
        return s
    if len(s) == 6:
        return f"{s[:3]}_{s[3:]}"
    return s


class MtfRegimeRangeCascadeScalp(StrategyBase):
    name = "mtf_regime_range_cascade_scalp"
    mode = "scalp"
    # DEPRECATED 2026-04-30 — demo_trades 実測で range_tight regime の MR は
    # 構造的に負け (bb_rsi×range_tight WR=12.5%, sr_channel×range WR=0%) と
    # 確認されたため発火停止. moderate_trend (trend cascade) に edge 集約.
    enabled = False
    strategy_type = "MR"

    # bb_rsi_reversion 継承パラメータ
    bbpb_buy = 0.30
    bbpb_sell = 0.70
    rsi5_buy = 45
    rsi5_sell = 55
    stoch_buy = 45
    stoch_sell = 55
    _v2_dedup_state: set[tuple[str, str, str, str]] = set()

    @classmethod
    def reset_dedup_state(cls):
        cls._v2_dedup_state.clear()

    def _redesign_v2_enabled(self) -> bool:
        return os.environ.get("MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2") == "1"

    @staticmethod
    def _range_cohort(m15: dict) -> str:
        regime = classify_15m(m15)
        if regime == REGIME_MODERATE_TREND:
            return "moderate_trend"
        adx = float(m15.get("adx", 0.0) or 0.0)
        hurst = float(m15.get("hurst_64", 0.5) or 0.5)
        if adx < 18.0 and hurst < 0.75:
            return "range_tight_blocked"
        if adx < 18.0:
            return "range_wide"
        return "no_go"

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── ペアガード ──────────────────────────────────────
        pair = _normalize_pair(ctx.symbol)
        if pair not in _ALLOWED_PAIRS:
            return None

        # ── Layer 0: spread/friction hard gate ─────────────
        blocked, _info = should_block(pair, ctx.hour_utc, ctx.df, pip_mult=ctx.pip_mult)
        if blocked:
            return None

        # ── Layer 1: 15m regime == range ────────────────────
        m15 = ctx.htf.get("m15") if isinstance(ctx.htf, dict) else None
        m5 = ctx.htf.get("m5") if isinstance(ctx.htf, dict) else None
        if not m15 or not m5:
            return None
        redesign_v2 = self._redesign_v2_enabled()
        regime_cohort = self._range_cohort(m15)
        if not redesign_v2 and classify_15m(m15) != REGIME_RANGE:
            return None
        if redesign_v2 and regime_cohort not in {"range_wide", "moderate_trend"}:
            return None

        if ctx.df is None or len(ctx.df) < 5:
            return None
        if ctx.atr7 <= 0:
            return None

        # ── Layer 2: 5m exhaustion confirmation ────────────
        m5_bbpb = float(m5.get("bbpb", 0.5))
        m5_swing_high = float(m5.get("swing_high", 0.0))
        m5_swing_low = float(m5.get("swing_low", 0.0))
        m5_high = float(m5.get("high", 0.0))
        m5_low = float(m5.get("low", 0.0))
        m5_atr = float(m5.get("atr", 0.0))
        if m5_atr <= 0:
            return None

        signal_bar_time = None
        trigger_entry = ctx.entry
        trigger_open = ctx.open_price
        trigger_high = ctx.entry
        trigger_low = ctx.entry
        trigger_bbpb = ctx.bbpb
        trigger_bb_upper = ctx.bb_upper
        trigger_bb_lower = ctx.bb_lower
        trigger_rsi5 = ctx.rsi5
        trigger_stoch_k = ctx.stoch_k
        trigger_stoch_d = ctx.stoch_d
        trigger_atr7 = ctx.atr7
        prev_rsi5 = ctx.rsi5
        prev_stoch_d = ctx.stoch_d
        if redesign_v2:
            if len(ctx.df) < 6:
                return None
            if not ctx.backtest_mode and ctx.bar_time is None:
                return None
            signal_row = ctx.df.iloc[-2]
            prev_row = ctx.df.iloc[-3]
            signal_bar_time = getattr(signal_row, "name", None)
            trigger_entry = float(signal_row["Close"])
            trigger_open = float(signal_row["Open"])
            trigger_high = float(signal_row["High"])
            trigger_low = float(signal_row["Low"])
            trigger_bbpb = float(signal_row.get("bb_pband", signal_row.get("bbpb", ctx.bbpb)))
            trigger_bb_upper = float(signal_row.get("bb_upper", ctx.bb_upper))
            trigger_bb_lower = float(signal_row.get("bb_lower", ctx.bb_lower))
            trigger_rsi5 = float(signal_row.get("rsi5", signal_row.get("rsi", ctx.rsi5)))
            trigger_stoch_k = float(signal_row.get("stoch_k", ctx.stoch_k))
            trigger_stoch_d = float(signal_row.get("stoch_d", ctx.stoch_d))
            trigger_atr7 = float(signal_row.get("atr7", signal_row.get("atr", ctx.atr7)))
            prev_rsi5 = float(prev_row.get("rsi5", prev_row.get("rsi", ctx.rsi5)))
            prev_stoch_d = float(prev_row.get("stoch_d", ctx.stoch_d))

        # 1m prev stoch_k for crossover relaxation (bb_rsi_reversion 継承)
        prev_stoch_k = (
            float(ctx.df.iloc[-2].get("stoch_k", 50)) if len(ctx.df) >= 2 else 50.0
        )
        if redesign_v2:
            prev_stoch_k = float(ctx.df.iloc[-3].get("stoch_k", 50.0))

        signal: Optional[str] = None
        reasons: list = []
        sl: float = 0.0
        tp: float = 0.0
        bonus: float = 0.0

        # ─── BUY @ range bottom ─────────────────────────────
        if redesign_v2:
            buy_edge_sweep = trigger_low <= m5_swing_low or trigger_low <= trigger_bb_lower
            buy_closed_inside = trigger_entry > trigger_bb_lower
            buy_rsi_recross = prev_rsi5 < 30 <= trigger_rsi5
            buy_stoch_cross = prev_stoch_k <= prev_stoch_d and trigger_stoch_k > trigger_stoch_d
            buy_ok = (
                buy_edge_sweep
                and buy_closed_inside
                and (buy_rsi_recross or buy_stoch_cross)
            )
        else:
            # 5m: BB%B ≤ 0.08 (下限タッチ) かつ swing_low に近い
            # 1m: bb_rsi_reversion 継承 (BB%B / RSI5 / Stoch / 確認足陽線)
            buy_ok = (m5_bbpb <= 0.08
                and abs(m5_low - m5_swing_low) <= m5_atr * 0.3
                and trigger_bbpb <= self.bbpb_buy
                and trigger_rsi5 < self.rsi5_buy
                and trigger_stoch_k < self.stoch_buy
                and (trigger_stoch_k > trigger_stoch_d or trigger_stoch_k > prev_stoch_k)
                and trigger_entry > trigger_open)

        if buy_ok:
            signal = "BUY"
            tier1 = trigger_bbpb <= 0.05 and trigger_rsi5 < 25 and trigger_stoch_k < 20
            sl_dist = max(abs(ctx.entry - trigger_bb_lower) + trigger_atr7 * 0.3,
                          0.030 if ctx.pip_mult == 100 else 0.00030)
            sl = ctx.entry - sl_dist
            sl_pips = sl_dist * ctx.pip_mult
            if sl_pips > _MAX_SL_PIPS:
                return None
            rr_floor = _RR_FLOOR_TIER1 if tier1 else _RR_FLOOR_TIER2
            tp_dist = max(ctx.atr7 * 2.0, sl_dist * rr_floor)
            tp = ctx.entry + tp_dist
            reasons.append(f"✅ regime_cohort={regime_cohort}")
            if redesign_v2:
                reasons.append("✅ closed 1m range-edge reclaim BUY")
                reasons.append(
                    f"✅ sweep low={trigger_low:.5f} <= swing_low={m5_swing_low:.5f} or bb_lower={trigger_bb_lower:.5f}"
                )
                reasons.append(f"✅ RSI recross={buy_rsi_recross} / Stoch cross={buy_stoch_cross}")
            else:
                reasons.append(f"✅ M5 BB lower touch (%B={m5_bbpb:.2f}) at swing_low")
                reasons.append(f"✅ 1m BB%B={trigger_bbpb:.2f}≤{self.bbpb_buy} + RSI5={trigger_rsi5:.1f} (bb_rsi 継承)")
                reasons.append(f"✅ Stoch reversal + bullish bar")
            if tier1:
                reasons.append("🎯 Tier1 (極端ゾーン RR≥3.0)")
                bonus += 1.0

        # ─── SELL @ range top ───────────────────────────────
        if signal is None:
            if redesign_v2:
                sell_edge_sweep = trigger_high >= m5_swing_high or trigger_high >= trigger_bb_upper
                sell_closed_inside = trigger_entry < trigger_bb_upper
                sell_rsi_recross = prev_rsi5 > 70 >= trigger_rsi5
                sell_stoch_cross = prev_stoch_k >= prev_stoch_d and trigger_stoch_k < trigger_stoch_d
                sell_ok = (
                    sell_edge_sweep
                    and sell_closed_inside
                    and (sell_rsi_recross or sell_stoch_cross)
                )
            else:
                sell_ok = (m5_bbpb >= 0.92
                and abs(m5_high - m5_swing_high) <= m5_atr * 0.3
                and trigger_bbpb >= self.bbpb_sell
                and trigger_rsi5 > self.rsi5_sell
                and trigger_stoch_k > self.stoch_sell
                and (trigger_stoch_k < trigger_stoch_d or trigger_stoch_k < prev_stoch_k)
                and trigger_entry < trigger_open)
        else:
            sell_ok = False

        if sell_ok:
            signal = "SELL"
            tier1 = trigger_bbpb >= 0.95 and trigger_rsi5 > 75 and trigger_stoch_k > 80
            sl_dist = max(abs(trigger_bb_upper - ctx.entry) + trigger_atr7 * 0.3,
                          0.030 if ctx.pip_mult == 100 else 0.00030)
            sl = ctx.entry + sl_dist
            sl_pips = sl_dist * ctx.pip_mult
            if sl_pips > _MAX_SL_PIPS:
                return None
            rr_floor = _RR_FLOOR_TIER1 if tier1 else _RR_FLOOR_TIER2
            tp_dist = max(ctx.atr7 * 2.0, sl_dist * rr_floor)
            tp = ctx.entry - tp_dist
            reasons.append(f"✅ regime_cohort={regime_cohort}")
            if redesign_v2:
                reasons.append("✅ closed 1m range-edge reclaim SELL")
                reasons.append(
                    f"✅ sweep high={trigger_high:.5f} >= swing_high={m5_swing_high:.5f} or bb_upper={trigger_bb_upper:.5f}"
                )
                reasons.append(f"✅ RSI recross={sell_rsi_recross} / Stoch cross={sell_stoch_cross}")
            else:
                reasons.append(f"✅ M5 BB upper touch (%B={m5_bbpb:.2f}) at swing_high")
                reasons.append(f"✅ 1m BB%B={trigger_bbpb:.2f}≥{self.bbpb_sell} + RSI5={trigger_rsi5:.1f} (bb_rsi 継承)")
                reasons.append(f"✅ Stoch reversal + bearish bar")
            if tier1:
                reasons.append("🎯 Tier1 (極端ゾーン RR≥3.0)")
                bonus += 1.0

        if signal is None:
            return None
        if redesign_v2:
            if not ctx.backtest_mode:
                sym = _normalize_pair(ctx.symbol)
                key = (sym, self.name, signal, str(signal_bar_time))
                if key in self._v2_dedup_state:
                    return None
                self._v2_dedup_state.add(key)
            reasons.append(
                f"✅ MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2: "
                f"signal_bar_time={signal_bar_time} confirmed; execution uses current bar"
            )

        # ── confidence ─────────────────────────────────────
        conf = 55
        if bonus >= 1.0:
            conf += 10
        from modules.friction_model_v2 import hour_mult_for
        h_mult = hour_mult_for(ctx.hour_utc)
        if h_mult <= 0.80:
            conf += 5
            reasons.append(f"✅ peak liquidity (hour_mult={h_mult:.2f})")
        conf = apply_penalty(conf, self.strategy_type, ctx.adx, conf_max=80)

        # ── score (3.0-4.5 レンジ) ─────────────────────────
        score = 3.0 + (1.0 if bonus >= 1.0 else 0.5)

        return Candidate(
            signal=signal,
            confidence=int(conf),
            sl=float(sl),
            tp=float(tp),
            reasons=reasons,
            entry_type=self.name,
            score=float(score),
        )
