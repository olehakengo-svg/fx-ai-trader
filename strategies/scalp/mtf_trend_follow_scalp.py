"""MTF Trend Follow Scalp — 教科書的 15m→5m→1m 順張りカスケード

設計意図 (rule:R1, 2026-04-29):
  - 既存 22 個の scalp 戦略はいずれも 1m 単独 + ぼんやりした H1/H4 HTF で
    評価しており、教科書的な M15→M5→M1 3 段カスケードを厳密に踏む戦略が
    存在しなかった。
  - 本戦略は M15 で trend identification (ADX + EMA slope)、
    M5 で SMA21 プルバック反発、M1 で micro pivot break を順に要求し、
    誤シグナルを段階的に削って WR を上げることを狙う。

ガード:
  - 通貨ペア: USD_JPY, EUR_USD のみ (友 friction_model_v2 で 0.7pip 最低)
  - 時間帯: friction_model_v2.hour_mult_for(hour_utc) <= 0.95 のみ発火
    (London open / overlap / NY peak / London close fix のみ)
  - 動的スプレッド遮断は demo_trader の spread_guard / spread_sl_gate に依存

検証要件 (CLAUDE.md Rule 1):
  - 365 日 BT + Bonferroni 補正 + Pre-reg LOCK 14 日
"""
from __future__ import annotations
from typing import Optional

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from modules.confidence_v2 import apply_penalty
from modules.friction_model_v2 import hour_mult_for


_ALLOWED_PAIRS = {"USD_JPY", "EUR_USD"}
_HOUR_MULT_MAX = 0.95   # 0.95 以下 (低スプレッド) のみ発火
_HOUR_MULT_PEAK = 0.85  # London-NY overlap など最良時間帯
_M15_ADX_MIN = 22
_M15_ADX_STRONG = 28
_RR_FLOOR = 1.3
_MIN_TP_ATR_MULT = 1.0   # TP - entry < ATR7 * 1.0 なら弱すぎ → reject


def _normalize_pair(symbol: str) -> str:
    s = (symbol or "").upper().replace("=X", "").replace("/", "_")
    if "_" in s:
        return s
    if len(s) == 6:
        return f"{s[:3]}_{s[3:]}"
    return s


class MtfTrendFollowScalp(StrategyBase):
    name = "mtf_trend_follow_scalp"
    mode = "scalp"
    enabled = True
    strategy_type = "trend"

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── ペアガード (低スプレッド限定) ───────────────────────
        pair = _normalize_pair(ctx.symbol)
        if pair not in _ALLOWED_PAIRS:
            return None

        # ── 時間帯ガード (動的、低スプレッド時間帯のみ) ──────
        h_mult = hour_mult_for(ctx.hour_utc)
        if h_mult > _HOUR_MULT_MAX:
            return None

        # ── HTF data: M15 + M5 必須 ────────────────────────────
        m15 = ctx.htf.get("m15") if isinstance(ctx.htf, dict) else None
        m5 = ctx.htf.get("m5") if isinstance(ctx.htf, dict) else None
        if not m15 or not m5:
            return None

        if ctx.df is None or len(ctx.df) < 5:
            return None
        if ctx.atr7 <= 0:
            return None

        m15_adx = float(m15.get("adx", 0.0))
        m15_ema9 = float(m15.get("ema9", 0.0))
        m15_ema21 = float(m15.get("ema21", 0.0))
        m15_slope = float(m15.get("ema_slope", 0.0))

        # 15m トレンドゲート
        if m15_adx < _M15_ADX_MIN:
            return None

        m5_sma21 = float(m5.get("sma21", 0.0))
        m5_prev_low = float(m5.get("prev_low", 0.0))
        m5_prev_close = float(m5.get("prev_close", 0.0))
        m5_prev_high = float(m5.get("prev_high", 0.0))
        m5_close = float(m5.get("close", 0.0))
        m5_atr = float(m5.get("atr", 0.0))
        m5_bbpb = float(m5.get("bbpb", 0.5))
        m5_swing_high = float(m5.get("swing_high", 0.0))
        m5_swing_low = float(m5.get("swing_low", 0.0))

        if m5_sma21 <= 0 or m5_atr <= 0:
            return None

        df = ctx.df
        # 直前 3 本の 1m 高値・安値
        recent_high = float(df["High"].iloc[-4:-1].max())  # 直前3本
        recent_low = float(df["Low"].iloc[-4:-1].min())

        signal: Optional[str] = None
        reasons: list = []
        sl: float = 0.0
        tp: float = 0.0
        bonus: float = 0.0

        # ─── BUY (uptrend) ──────────────────────────────────
        if (m15_ema9 > m15_ema21 and m15_slope > 0):
            # 5m プルバック確認: 直前 5m が SMA21 タッチ → 当バー反発
            pullback_ok = (m5_prev_low <= m5_sma21 + m5_atr * 0.3) and (m5_close > m5_prev_close)
            mid_zone = 0.20 <= m5_bbpb <= 0.65
            if not (pullback_ok and mid_zone):
                return None
            # 1m micro pivot break + モメンタム確認
            if not (ctx.entry > recent_high):
                return None
            if not (ctx.macdh > 0 and ctx.macdh > ctx.macdh_prev):
                return None
            if not (ctx.stoch_k > ctx.stoch_d and ctx.stoch_k < 75):
                return None
            if not (ctx.entry > ctx.open_price):
                return None
            signal = "BUY"
            sl = recent_low - (1.0 / ctx.pip_mult)  # 1pip buffer
            sl_dist = ctx.entry - sl
            if sl_dist <= 0:
                return None
            tp_swing = m5_swing_high
            tp_rr = ctx.entry + sl_dist * _RR_FLOOR
            tp = max(tp_swing, tp_rr)
            if (tp - ctx.entry) < ctx.atr7 * _MIN_TP_ATR_MULT:
                return None
            reasons.append(f"✅ M15 trend: ADX={m15_adx:.1f} EMA9>21 slope={m15_slope:.4f}")
            reasons.append(f"✅ M5 SMA21 pullback bounce (prev_low={m5_prev_low:.4f} ≤ sma21={m5_sma21:.4f})")
            reasons.append(f"✅ 1m micro pivot break {ctx.entry:.4f} > 3-bar high {recent_high:.4f}")
            reasons.append(f"✅ MACD-H rising + Stoch K>D + bullish bar")

        # ─── SELL (downtrend) ───────────────────────────────
        elif (m15_ema9 < m15_ema21 and m15_slope < 0):
            pullback_ok = (m5_prev_high >= m5_sma21 - m5_atr * 0.3) and (m5_close < m5_prev_close)
            mid_zone = 0.35 <= m5_bbpb <= 0.80
            if not (pullback_ok and mid_zone):
                return None
            if not (ctx.entry < recent_low):
                return None
            if not (ctx.macdh < 0 and ctx.macdh < ctx.macdh_prev):
                return None
            if not (ctx.stoch_k < ctx.stoch_d and ctx.stoch_k > 25):
                return None
            if not (ctx.entry < ctx.open_price):
                return None
            signal = "SELL"
            sl = recent_high + (1.0 / ctx.pip_mult)
            sl_dist = sl - ctx.entry
            if sl_dist <= 0:
                return None
            tp_swing = m5_swing_low
            tp_rr = ctx.entry - sl_dist * _RR_FLOOR
            tp = min(tp_swing, tp_rr)
            if (ctx.entry - tp) < ctx.atr7 * _MIN_TP_ATR_MULT:
                return None
            reasons.append(f"✅ M15 trend: ADX={m15_adx:.1f} EMA9<21 slope={m15_slope:.4f}")
            reasons.append(f"✅ M5 SMA21 戻り反落 (prev_high={m5_prev_high:.4f} ≥ sma21={m5_sma21:.4f})")
            reasons.append(f"✅ 1m micro pivot break {ctx.entry:.4f} < 3-bar low {recent_low:.4f}")
            reasons.append(f"✅ MACD-H falling + Stoch K<D + bearish bar")

        if signal is None:
            return None

        # ── confidence ──────────────────────────────────────
        conf = 60
        if m15_adx >= _M15_ADX_STRONG:
            conf += 10
            bonus += 1.0
            reasons.append(f"✅ M15 strong trend (ADX≥{_M15_ADX_STRONG})")
        if h_mult <= _HOUR_MULT_PEAK:
            conf += 5
            bonus += 0.5
            reasons.append(f"✅ peak liquidity hour (mult={h_mult:.2f})")
        if abs(m15_slope) > 0.5 * (m5_atr / ctx.pip_mult if ctx.pip_mult else 1.0):
            conf += 5
            reasons.append("✅ steep M15 slope")
        conf = apply_penalty(conf, self.strategy_type, ctx.adx, conf_max=85)

        # ── score: 既存戦略と同じ 3.0-4.5 レンジで正規化 ────
        # ema_pullback: 3.0 + min((adx-20)*0.05, 1.0) ≒ 3.0-4.0
        # 本戦略は 3 段カスケードで条件が厳しい分、最大値を僅かに高めに設定
        score = 3.0 + min((m15_adx - _M15_ADX_MIN) * 0.05, 1.0) + bonus * 0.3

        return Candidate(
            signal=signal,
            confidence=int(conf),
            sl=float(sl),
            tp=float(tp),
            reasons=reasons,
            entry_type=self.name,
            score=float(score),
        )
