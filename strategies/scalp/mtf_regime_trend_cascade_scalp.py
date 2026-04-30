"""MTF Moderate-Trend Cascade Scalp — data-driven 別軸 cascade scalp (rule:R1)

設計の歴史 (重要):
  v1 (2026-04-29 廃案): regime ∈ {trend_up, trend_down} で発火.
  v2 (2026-04-30): demo_trades.db (N=462) ラベル実測クエリで binary regime に簡素化.
    - trend_up_weak のみ edge。strong/range は実測で否定。
  v2.1 (2026-04-30, 現行): L3 緩和 + SL floor 修正 (rule:R3)
    - L3 ema_order 削除: 15m slope_dir が方向確定済み、1m EMA 順列は冗長 (→32件ブロック)
    - L3 ema9_touch 削除: 5m pullback が既に近接確認済み (→17件ブロック)
    - SL floor: max(atr7×0.3, 5pip) — EUR_USD 低ボラで 0.15pip SL になる実装バグ修正
    実測根拠: 180d USD_JPY L3 全廃で N=39 WR=38.5% PF=2.58 EV=+3.03p Kelly=+23.6%
    KB: knowledge-base/wiki/analyses/mtf-regime-trend-cascade-null-finding-2026-04-30.md

差別化 3 軸 (走行 BT vs 本戦略):
    1. spread_gate.should_block を最上位に置く (hour_mult≤0.85 + 4 重ゲート)
    2. 1m トリガーは ema_pullback の bounce 確認ロジックを継承 (L3 slim 化済)
    3. 15m regime == moderate_trend (ADX 18-25 + |slope|>0 + Hurst 0.40-0.55)
       のときのみ発火, BUY/SELL 方向は ema_slope 符号で決定

検証要件 (CLAUDE.md Rule 1):
  - 365 日 BT + Bonferroni 補正 + Walk-Forward + Pre-reg LOCK 14 日

KB references:
  - knowledge-base/wiki/decisions/regime-cascade-empirical-redesign-2026-04-30.md
  - knowledge-base/wiki/strategies/ema-pullback.md (継承元の挙動)
  - knowledge-base/wiki/analyses/friction-analysis.md
"""
from __future__ import annotations
from typing import Optional

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from modules.confidence_v2 import apply_penalty
from modules.spread_gate import should_block
from modules.regime_classifier import (
    classify_15m,
    slope_direction,
    REGIME_MODERATE_TREND,
)


_ALLOWED_PAIRS = {"USD_JPY", "EUR_USD"}
_RR_FLOOR = 1.3
_MIN_TP_ATR_MULT = 1.0
_MIN_SL_PIPS = 5  # SL floor: 低ボラ pair (EUR_USD) で sl_dist < spread 問題を防ぐ (rule:R3)


def _normalize_pair(symbol: str) -> str:
    s = (symbol or "").upper().replace("=X", "").replace("/", "_")
    if "_" in s:
        return s
    if len(s) == 6:
        return f"{s[:3]}_{s[3:]}"
    return s


class MtfRegimeTrendCascadeScalp(StrategyBase):
    name = "mtf_regime_trend_cascade_scalp"
    mode = "scalp"
    enabled = True
    strategy_type = "trend"

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── ペアガード ──────────────────────────────────────
        pair = _normalize_pair(ctx.symbol)
        if pair not in _ALLOWED_PAIRS:
            return None

        # ── Layer 0: spread/friction hard gate (最上位) ────
        blocked, _info = should_block(pair, ctx.hour_utc, ctx.df, pip_mult=ctx.pip_mult)
        if blocked:
            return None

        # ── Layer 1: 15m regime classifier (v2: binary moderate_trend) ─
        m15 = ctx.htf.get("m15") if isinstance(ctx.htf, dict) else None
        m5 = ctx.htf.get("m5") if isinstance(ctx.htf, dict) else None
        if not m15 or not m5:
            return None
        if classify_15m(m15) != REGIME_MODERATE_TREND:
            return None
        # 方向は slope 符号で決定 (data-driven simplification)
        slope_dir = slope_direction(m15)
        if slope_dir == 0:
            return None

        if ctx.df is None or len(ctx.df) < 5:
            return None
        if ctx.atr7 <= 0:
            return None

        m15_adx = float(m15.get("adx", 0.0))
        m15_slope = float(m15.get("ema_slope", 0.0))
        atr15 = float(m15.get("atr15", m15.get("atr", 0.0)))

        # ── Layer 2: 5m direction confirmation ─────────────
        m5_sma21 = float(m5.get("sma21", 0.0))
        m5_atr = float(m5.get("atr", 0.0))
        m5_prev_low = float(m5.get("prev_low", 0.0))
        m5_prev_high = float(m5.get("prev_high", 0.0))
        m5_prev_close = float(m5.get("prev_close", 0.0))
        m5_close = float(m5.get("close", 0.0))
        m5_swing_high = float(m5.get("swing_high", 0.0))
        m5_swing_low = float(m5.get("swing_low", 0.0))
        if m5_sma21 <= 0 or m5_atr <= 0:
            return None

        # ── Layer 3: 1m trigger (ema_pullback 継承の bounce 確認) ─
        signal: Optional[str] = None
        reasons: list = []
        sl: float = 0.0
        tp: float = 0.0
        bonus: float = 0.0

        # ─── BUY (slope_dir == +1, bullish moderate trend) ──
        if slope_dir > 0:
            # 5m: SMA21 タッチ → 反発
            pullback_ok = (m5_prev_low <= m5_sma21 + m5_atr * 0.3) and (m5_close > m5_prev_close)
            if not pullback_ok:
                return None
            # 1m: ema_pullback 継承トリガー (v2.1 slim: ema_order / ema9_touch 削除)
            #   (a) EMA21 から min_bounce 以上反発 (15m slope_dir + 5m pullback で方向確定済み)
            #   (b) 陽線方向
            #   (c) MACD-H > 0 上昇
            #   (d) Stoch K>D かつ K<75
            min_bounce = ctx.atr7 * 0.2
            if (ctx.entry - ctx.ema21) < min_bounce:
                return None
            if not (ctx.entry > ctx.prev_close and ctx.entry > ctx.open_price):
                return None
            if not (ctx.macdh > 0 and ctx.macdh > ctx.macdh_prev):
                return None
            if not (ctx.stoch_k > ctx.stoch_d and ctx.stoch_k < 75):
                return None
            signal = "BUY"
            pip_val = ctx.pip_mult if ctx.pip_mult else 0.0001
            sl_raw = ctx.ema21 - ctx.atr7 * 0.3
            sl_dist = max(ctx.entry - sl_raw, _MIN_SL_PIPS * pip_val)  # floor: 5pip最低保証
            sl = ctx.entry - sl_dist
            if sl_dist <= 0:
                return None
            tp_swing = m5_swing_high
            tp_rr = ctx.entry + sl_dist * _RR_FLOOR
            tp = max(tp_swing, tp_rr)
            if (tp - ctx.entry) < ctx.atr7 * _MIN_TP_ATR_MULT:
                return None
            reasons.append(f"✅ regime=moderate_trend BUY (M15 ADX={m15_adx:.1f} slope={m15_slope:.4f})")
            reasons.append(f"✅ M5 SMA21 pullback bounce")
            reasons.append(f"✅ 1m EMA21 タッチ→反発 + bullish bar (ema_pullback 継承)")
            reasons.append(f"✅ MACD-H rising + Stoch K>D")

        # ─── SELL (slope_dir == -1, bearish moderate trend) ──
        elif slope_dir < 0:
            pullback_ok = (m5_prev_high >= m5_sma21 - m5_atr * 0.3) and (m5_close < m5_prev_close)
            if not pullback_ok:
                return None
            # 1m: ema_pullback 継承トリガー (v2.1 slim: ema_order / ema9_touch 削除)
            #   (a) EMA21 から min_bounce 以上反落 (15m slope_dir + 5m pullback で方向確定済み)
            #   (b) 陰線方向
            #   (c) MACD-H < 0 下降
            #   (d) Stoch K<D かつ K>25
            min_bounce = ctx.atr7 * 0.2
            if (ctx.ema21 - ctx.entry) < min_bounce:
                return None
            if not (ctx.entry < ctx.prev_close and ctx.entry < ctx.open_price):
                return None
            if not (ctx.macdh < 0 and ctx.macdh < ctx.macdh_prev):
                return None
            if not (ctx.stoch_k < ctx.stoch_d and ctx.stoch_k > 25):
                return None
            signal = "SELL"
            pip_val = ctx.pip_mult if ctx.pip_mult else 0.0001
            sl_raw = ctx.ema21 + ctx.atr7 * 0.3
            sl_dist = max(sl_raw - ctx.entry, _MIN_SL_PIPS * pip_val)  # floor: 5pip最低保証
            sl = ctx.entry + sl_dist
            if sl_dist <= 0:
                return None
            tp_swing = m5_swing_low
            tp_rr = ctx.entry - sl_dist * _RR_FLOOR
            tp = min(tp_swing, tp_rr)
            if (ctx.entry - tp) < ctx.atr7 * _MIN_TP_ATR_MULT:
                return None
            reasons.append(f"✅ regime=moderate_trend SELL (M15 ADX={m15_adx:.1f} slope={m15_slope:.4f})")
            reasons.append(f"✅ M5 SMA21 戻り反落")
            reasons.append(f"✅ 1m EMA21 戻り→反落 + bearish bar (ema_pullback 継承)")
            reasons.append(f"✅ MACD-H falling + Stoch K<D")

        if signal is None:
            return None

        # ── confidence (moderate_trend 専用、v2 スコア体系) ─
        # 注: m15_adx は 18-25 にクランプ済 (regime gate 通過時)
        conf = 60
        if 21 <= m15_adx <= 24:
            # 中庸帯のスイートスポット (実測 trend_up_weak 相当)
            conf += 10
            bonus += 1.0
            reasons.append(f"✅ ADX sweet-spot {m15_adx:.1f} (moderate trend center)")
        from modules.friction_model_v2 import hour_mult_for
        h_mult = hour_mult_for(ctx.hour_utc)
        if h_mult <= 0.80:
            conf += 5
            bonus += 0.5
            reasons.append(f"✅ peak liquidity (hour_mult={h_mult:.2f})")
        if abs(m15_slope) > 0.5 * (atr15 / ctx.pip_mult if ctx.pip_mult else 1.0):
            conf += 5
            reasons.append("✅ steep M15 slope (within moderate band)")
        conf = apply_penalty(conf, self.strategy_type, ctx.adx, conf_max=85)

        # ── score (3.0-4.5 レンジ): ADX 18-25 → score 3.0-3.7 + bonus ──
        score = 3.0 + min((m15_adx - 18.0) * 0.10, 0.7) + bonus * 0.3

        return Candidate(
            signal=signal,
            confidence=int(conf),
            sl=float(sl),
            tp=float(tp),
            reasons=reasons,
            entry_type=self.name,
            score=float(score),
        )
