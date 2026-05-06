"""MTF Moderate-Trend Cascade Scalp — data-driven 別軸 cascade scalp (rule:R1)

設計の歴史 (重要):
  v1 (2026-04-29 廃案): regime ∈ {trend_up, trend_down} で発火.
  v2 (2026-04-30): demo_trades.db (N=462) ラベル実測クエリで binary regime に簡素化.
    - trend_up_weak のみ edge。strong/range は実測で否定。
  v2.1 (2026-04-30): L3 緩和 (ema_order/ema9_touch 削除) + SL floor 追加 試案 — 実測 N=0
  v2.3 (2026-04-30, 現行): rule:R3 — v2.1 の 2 つの実装バグを実測根拠で修正
    Bug 1 (SL formula): pip_val=pip_mult (=100/10000) の単位ミスで SL=±500 価格単位
                       → pip_size = 1.0/pip_mult に修正、5pip floor 正しく機能
    Bug 2 (L3 macdh+stoch): 1m oscillator 系で 358/800 候補を消滅
                       → macdh / stoch を完全廃止 (15m moderate_trend + 5m pullback +
                         1m candle direction が方向確定に十分、1m oscillator は noise)
    実測根拠 (instrumented BT 180d USD_JPY):
      - L0 通過: 31749/179296
      - L1 (moderate_trend): 3401 通過
      - L2 (5m pullback): 800 通過
      - L3 v2.1 で 800/800 ブロック (macdh > 0 必須 + SL formula bug)
      - L3 v2.3 で 358/800 通過 (~2 trade/day 想定)
    KB: knowledge-base/wiki/analyses/mtf-regime-trend-cascade-null-finding-2026-04-30.md

差別化 3 軸 (走行 BT vs 本戦略):
    1. spread_gate.should_block を最上位に置く (hour_mult≤0.85 + 4 重ゲート)
    2. 1m トリガーは price-action only (candle direction + bounce strength)
    3. 15m regime == moderate_trend (ADX 18-25 + |slope|>0 + Hurst 0.40-0.55)
       のときのみ発火, BUY/SELL 方向は ema_slope 符号で決定

検証要件 (CLAUDE.md Rule 1):
  - 365 日 BT + Bonferroni 補正 (cell=6, α=0.00833) + Walk-Forward + Pre-reg LOCK 14 日

KB references:
  - knowledge-base/wiki/decisions/regime-cascade-empirical-redesign-2026-04-30.md
  - knowledge-base/wiki/strategies/ema-pullback.md (v2.1 までの継承元)
  - knowledge-base/wiki/analyses/friction-analysis.md
"""
from __future__ import annotations
import os
from typing import Optional

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from modules.confidence_v2 import apply_penalty
from modules.spread_gate import should_block
from modules.regime_classifier import (
    classify_15m,
    slope_direction,
    slope_direction_macro_gated,
    REGIME_MODERATE_TREND,
)


_ALLOWED_PAIRS = {"USD_JPY", "EUR_USD"}
_RR_FLOOR = 1.3
_MIN_TP_ATR_MULT = 1.0
_MIN_SL_PIPS = 5  # SL floor: 低ボラ pair で sl_dist < spread 問題を防ぐ (rule:R3)


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
    _v2_dedup_state: set[tuple[str, str, str, str]] = set()

    @classmethod
    def reset_dedup_state(cls):
        cls._v2_dedup_state.clear()

    def _redesign_v2_enabled(self) -> bool:
        return os.environ.get("MTF_REGIME_TREND_CASCADE_SCALP_REDESIGN_V2") == "1"

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── ペアガード ──────────────────────────────────────
        pair = _normalize_pair(ctx.symbol)
        if pair not in _ALLOWED_PAIRS:
            return None

        # ── Layer 0: spread/friction hard gate (最上位) ────
        blocked, _info = should_block(pair, ctx.hour_utc, ctx.df, pip_mult=ctx.pip_mult)
        if blocked:
            return None

        # ── Layer 1: 15m regime classifier (binary moderate_trend) ─
        m15 = ctx.htf.get("m15") if isinstance(ctx.htf, dict) else None
        m5 = ctx.htf.get("m5") if isinstance(ctx.htf, dict) else None
        if not m15 or not m5:
            return None
        if classify_15m(m15) != REGIME_MODERATE_TREND:
            return None
        # 方向決定: H1 macro trend gate 付き slope direction (rule:R3, 2026-04-30)
        # USD_JPY 60d edge collapse 解析で M15 短期 slope 単独はマクロ
        # トレンドと逆向き発火 → systematic LOSS の構造を確認.
        # H1 EMA21 vs EMA50 で macro 方向と整合する方向のみ許可する.
        h1 = ctx.htf.get("h1") if isinstance(ctx.htf, dict) else None
        slope_dir = slope_direction_macro_gated(m15, h1)
        if slope_dir == 0:
            return None

        if ctx.df is None or len(ctx.df) < 5:
            return None
        if ctx.atr7 <= 0:
            return None

        redesign_v2 = self._redesign_v2_enabled()
        signal_bar_time = None
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
            trigger_prev_close = float(prev_row["Close"])
            trigger_ema21 = float(signal_row.get("ema21", ctx.ema21))
            trigger_atr7 = float(signal_row.get("atr7", ctx.atr7))
        else:
            trigger_entry = ctx.entry
            trigger_open = ctx.open_price
            trigger_prev_close = ctx.prev_close
            trigger_ema21 = ctx.ema21
            trigger_atr7 = ctx.atr7

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

        # ── Layer 3: 1m bounce 確認 (v2.3: oscillator 系を完全廃止) ─
        signal: Optional[str] = None
        reasons: list = []
        sl: float = 0.0
        tp: float = 0.0
        bonus: float = 0.0
        # pip_size: pip → price units 換算 (rule:R3 — v2.1 bug 修正)
        pip_size = (1.0 / ctx.pip_mult) if ctx.pip_mult else 0.0001

        # ─── BUY (slope_dir == +1, bullish moderate trend) ──
        if slope_dir > 0:
            # 5m: SMA21 タッチ → 反発
            pullback_ok = (m5_prev_low <= m5_sma21 + m5_atr * 0.3) and (m5_close > m5_prev_close)
            if not pullback_ok:
                return None
            # 1m: bounce 確認 (price-action only)
            #   (a) EMA21 から min_bounce 以上反発
            #   (b) 陽線方向 (entry > prev_close + entry > open)
            min_bounce = trigger_atr7 * 0.2
            if (trigger_entry - trigger_ema21) < min_bounce:
                return None
            if not (trigger_entry > trigger_prev_close and trigger_entry > trigger_open):
                return None
            signal = "BUY"
            sl_raw = trigger_ema21 - trigger_atr7 * 0.3
            sl_dist = max(ctx.entry - sl_raw, _MIN_SL_PIPS * pip_size)  # floor: 5pip
            sl = ctx.entry - sl_dist
            if sl_dist <= 0:
                return None
            tp_swing = m5_swing_high
            tp_rr = ctx.entry + sl_dist * _RR_FLOOR
            tp = max(tp_swing, tp_rr)
            if (tp - ctx.entry) < trigger_atr7 * _MIN_TP_ATR_MULT:
                return None
            reasons.append(f"✅ regime=moderate_trend BUY (M15 ADX={m15_adx:.1f} slope={m15_slope:.4f})")
            reasons.append(f"✅ M5 SMA21 pullback bounce")
            reasons.append(f"✅ 1m bullish bar + min_bounce {min_bounce*ctx.pip_mult:.1f}pip")

        # ─── SELL (slope_dir == -1, bearish moderate trend) ──
        elif slope_dir < 0:
            pullback_ok = (m5_prev_high >= m5_sma21 - m5_atr * 0.3) and (m5_close < m5_prev_close)
            if not pullback_ok:
                return None
            min_bounce = trigger_atr7 * 0.2
            if (trigger_ema21 - trigger_entry) < min_bounce:
                return None
            if not (trigger_entry < trigger_prev_close and trigger_entry < trigger_open):
                return None
            signal = "SELL"
            sl_raw = trigger_ema21 + trigger_atr7 * 0.3
            sl_dist = max(sl_raw - ctx.entry, _MIN_SL_PIPS * pip_size)  # floor: 5pip
            sl = ctx.entry + sl_dist
            if sl_dist <= 0:
                return None
            tp_swing = m5_swing_low
            tp_rr = ctx.entry - sl_dist * _RR_FLOOR
            tp = min(tp_swing, tp_rr)
            if (ctx.entry - tp) < trigger_atr7 * _MIN_TP_ATR_MULT:
                return None
            reasons.append(f"✅ regime=moderate_trend SELL (M15 ADX={m15_adx:.1f} slope={m15_slope:.4f})")
            reasons.append(f"✅ M5 SMA21 戻り反落")
            reasons.append(f"✅ 1m bearish bar + min_bounce {min_bounce*ctx.pip_mult:.1f}pip")

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
                f"✅ MTF_REGIME_TREND_CASCADE_SCALP_REDESIGN_V2: "
                f"signal_bar_time={signal_bar_time} confirmed; execution uses current bar"
            )

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
