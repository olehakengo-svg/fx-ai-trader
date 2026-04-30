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
from typing import Optional

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from modules.confidence_v2 import apply_penalty
from modules.spread_gate import should_block
from modules.regime_classifier import classify_15m, REGIME_RANGE


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
        if classify_15m(m15) != REGIME_RANGE:
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

        # 1m prev stoch_k for crossover relaxation (bb_rsi_reversion 継承)
        prev_stoch_k = (
            float(ctx.df.iloc[-2].get("stoch_k", 50)) if len(ctx.df) >= 2 else 50.0
        )

        signal: Optional[str] = None
        reasons: list = []
        sl: float = 0.0
        tp: float = 0.0
        bonus: float = 0.0

        # ─── BUY @ range bottom ─────────────────────────────
        # 5m: BB%B ≤ 0.08 (下限タッチ) かつ swing_low に近い
        # 1m: bb_rsi_reversion 継承 (BB%B / RSI5 / Stoch / 確認足陽線)
        if (m5_bbpb <= 0.08
                and abs(m5_low - m5_swing_low) <= m5_atr * 0.3
                and ctx.bbpb <= self.bbpb_buy
                and ctx.rsi5 < self.rsi5_buy
                and ctx.stoch_k < self.stoch_buy
                and (ctx.stoch_k > ctx.stoch_d or ctx.stoch_k > prev_stoch_k)
                and ctx.entry > ctx.open_price):
            signal = "BUY"
            tier1 = ctx.bbpb <= 0.05 and ctx.rsi5 < 25 and ctx.stoch_k < 20
            sl_dist = max(abs(ctx.entry - ctx.bb_lower) + ctx.atr7 * 0.3,
                          0.030 if ctx.pip_mult == 100 else 0.00030)
            sl = ctx.entry - sl_dist
            sl_pips = sl_dist * ctx.pip_mult
            if sl_pips > _MAX_SL_PIPS:
                return None
            rr_floor = _RR_FLOOR_TIER1 if tier1 else _RR_FLOOR_TIER2
            tp_dist = max(ctx.atr7 * 2.0, sl_dist * rr_floor)
            tp = ctx.entry + tp_dist
            reasons.append(f"✅ regime=range (M15 ADX<20, Hurst~0.5)")
            reasons.append(f"✅ M5 BB lower touch (%B={m5_bbpb:.2f}) at swing_low")
            reasons.append(f"✅ 1m BB%B={ctx.bbpb:.2f}≤{self.bbpb_buy} + RSI5={ctx.rsi5:.1f} (bb_rsi 継承)")
            reasons.append(f"✅ Stoch reversal + bullish bar")
            if tier1:
                reasons.append("🎯 Tier1 (極端ゾーン RR≥3.0)")
                bonus += 1.0

        # ─── SELL @ range top ───────────────────────────────
        elif (m5_bbpb >= 0.92
                and abs(m5_high - m5_swing_high) <= m5_atr * 0.3
                and ctx.bbpb >= self.bbpb_sell
                and ctx.rsi5 > self.rsi5_sell
                and ctx.stoch_k > self.stoch_sell
                and (ctx.stoch_k < ctx.stoch_d or ctx.stoch_k < prev_stoch_k)
                and ctx.entry < ctx.open_price):
            signal = "SELL"
            tier1 = ctx.bbpb >= 0.95 and ctx.rsi5 > 75 and ctx.stoch_k > 80
            sl_dist = max(abs(ctx.bb_upper - ctx.entry) + ctx.atr7 * 0.3,
                          0.030 if ctx.pip_mult == 100 else 0.00030)
            sl = ctx.entry + sl_dist
            sl_pips = sl_dist * ctx.pip_mult
            if sl_pips > _MAX_SL_PIPS:
                return None
            rr_floor = _RR_FLOOR_TIER1 if tier1 else _RR_FLOOR_TIER2
            tp_dist = max(ctx.atr7 * 2.0, sl_dist * rr_floor)
            tp = ctx.entry - tp_dist
            reasons.append(f"✅ regime=range (M15 ADX<20, Hurst~0.5)")
            reasons.append(f"✅ M5 BB upper touch (%B={m5_bbpb:.2f}) at swing_high")
            reasons.append(f"✅ 1m BB%B={ctx.bbpb:.2f}≥{self.bbpb_sell} + RSI5={ctx.rsi5:.1f} (bb_rsi 継承)")
            reasons.append(f"✅ Stoch reversal + bearish bar")
            if tier1:
                reasons.append("🎯 Tier1 (極端ゾーン RR≥3.0)")
                bonus += 1.0

        if signal is None:
            return None

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
