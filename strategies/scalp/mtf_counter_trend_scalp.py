"""MTF Counter-Trend Scalp — 教科書的 15m→5m→1m 逆張りカスケード

設計意図 (rule:R1, 2026-04-29):
  - 既存戦略 (bb_rsi, v_reversal, mtf_confluence 等) は 1m exhaustion を
    検出するが、5m 過熱検出 (BB%B + RSI divergence) を要求しない。
  - 本戦略は M15 でトレンド存在を確認 (ADX≥25)、M5 で BB%B≥0.92
    + RSI divergence を要求、M1 で engulfing / pin bar を引き金に逆張り。
  - 短命の exhaustion swing を狙うため固定小幅 TP (5-8 pip)。

ガード:
  - 通貨ペア: USD_JPY, EUR_USD のみ
  - 時間帯: friction_model_v2.hour_mult_for(hour_utc) <= 0.95
  - SL distance > 12pip なら過大として拒否

検証要件 (CLAUDE.md Rule 1):
  - 365 日 BT + Bonferroni 補正 + Pre-reg LOCK 14 日
  - strategy_type="MR" のため confidence_v2 が ADX>25 で penalty
"""
from __future__ import annotations
import os
from typing import Optional

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from modules.confidence_v2 import apply_penalty
from modules.friction_model_v2 import hour_mult_for


_ALLOWED_PAIRS = {"USD_JPY", "EUR_USD"}
_HOUR_MULT_MAX = 0.95
_HOUR_MULT_PEAK = 0.85
_M15_ADX_MIN = 25            # 明確なトレンド存在を要求
_M5_BBPB_OVERBOUGHT = 0.92
_M5_BBPB_OVERSOLD = 0.08
_RR_FLOOR = 1.2
_SL_MAX_PIPS = 12.0          # SL distance がこれ超なら exhaustion 失敗


# 固定小幅 TP (pips, ペア別)
_FIXED_TP_PIPS = {
    "USD_JPY": 6.0,
    "EUR_USD": 5.0,
}


def _normalize_pair(symbol: str) -> str:
    s = (symbol or "").upper().replace("=X", "").replace("/", "_")
    if "_" in s:
        return s
    if len(s) == 6:
        return f"{s[:3]}_{s[3:]}"
    return s


def _is_bearish_engulfing(df) -> bool:
    """直近2本: 前足陽線 → 当足陰線が前足を包む"""
    if df is None or len(df) < 2:
        return False
    p = df.iloc[-2]
    c = df.iloc[-1]
    p_open, p_close = float(p["Open"]), float(p["Close"])
    c_open, c_close = float(c["Open"]), float(c["Close"])
    return (p_close > p_open) and (c_close < c_open) and (c_open >= p_close) and (c_close <= p_open)


def _is_bullish_engulfing(df) -> bool:
    if df is None or len(df) < 2:
        return False
    p = df.iloc[-2]
    c = df.iloc[-1]
    p_open, p_close = float(p["Open"]), float(p["Close"])
    c_open, c_close = float(c["Open"]), float(c["Close"])
    return (p_close < p_open) and (c_close > c_open) and (c_open <= p_close) and (c_close >= p_open)


def _is_bearish_pin(df) -> bool:
    """上ヒゲ > range*0.65, 実体 < range*0.30"""
    if df is None or len(df) < 1:
        return False
    c = df.iloc[-1]
    high = float(c["High"]); low = float(c["Low"])
    o = float(c["Open"]); cl = float(c["Close"])
    rng = high - low
    if rng <= 0:
        return False
    upper_wick = high - max(o, cl)
    body = abs(cl - o)
    return (upper_wick / rng) > 0.65 and (body / rng) < 0.30


def _is_bullish_pin(df) -> bool:
    if df is None or len(df) < 1:
        return False
    c = df.iloc[-1]
    high = float(c["High"]); low = float(c["Low"])
    o = float(c["Open"]); cl = float(c["Close"])
    rng = high - low
    if rng <= 0:
        return False
    lower_wick = min(o, cl) - low
    body = abs(cl - o)
    return (lower_wick / rng) > 0.65 and (body / rng) < 0.30


class MtfCounterTrendScalp(StrategyBase):
    name = "mtf_counter_trend_scalp"
    mode = "scalp"
    enabled = True
    strategy_type = "MR"
    _v2_dedup_state: set[tuple[str, str, str, str]] = set()

    @classmethod
    def reset_dedup_state(cls):
        cls._v2_dedup_state.clear()

    def _redesign_v2_enabled(self) -> bool:
        return os.environ.get("MTF_COUNTER_TREND_SCALP_REDESIGN_V2") == "1"

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        redesign_v2 = self._redesign_v2_enabled()

        # ── ペアガード ──────────────────────────────────────
        pair = _normalize_pair(ctx.symbol)
        if pair not in _ALLOWED_PAIRS:
            return None

        # ── 時間帯ガード ─────────────────────────────────────
        h_mult = hour_mult_for(ctx.hour_utc)
        if h_mult > _HOUR_MULT_MAX:
            return None

        # ── HTF data ────────────────────────────────────────
        m15 = ctx.htf.get("m15") if isinstance(ctx.htf, dict) else None
        m5 = ctx.htf.get("m5") if isinstance(ctx.htf, dict) else None
        if not m15 or not m5:
            return None
        if redesign_v2 and (m15.get("is_closed") is False or m5.get("is_closed") is False):
            return None
        if ctx.df is None or len(ctx.df) < 3:
            return None
        if redesign_v2 and len(ctx.df) < 3:
            return None

        m15_adx = float(m15.get("adx", 0.0))
        m15_ema9 = float(m15.get("ema9", 0.0))
        m15_ema21 = float(m15.get("ema21", 0.0))

        if m15_adx < _M15_ADX_MIN:
            return None

        m5_bbpb = float(m5.get("bbpb", 0.5))
        m5_high = float(m5.get("high", 0.0))
        m5_low = float(m5.get("low", 0.0))
        m5_div_bear = bool(m5.get("rsi_div_bear", False))
        m5_div_bull = bool(m5.get("rsi_div_bull", False))

        signal_df = ctx.df
        signal_bar_time = getattr(ctx.df.iloc[-1], "name", None)
        trigger_entry = ctx.entry
        trigger_open = ctx.open_price
        trigger_stoch_k = ctx.stoch_k
        trigger_stoch_d = ctx.stoch_d
        trigger_adx = ctx.adx
        if redesign_v2:
            # V2: iloc[-2] is the last closed 1m signal bar; ctx.entry remains
            # the next/current bar execution price.
            signal_df = ctx.df.iloc[:-1]
            if len(signal_df) < 2:
                return None
            signal_row = signal_df.iloc[-1]
            signal_bar_time = getattr(signal_row, "name", None)
            trigger_entry = float(signal_row["Close"])
            trigger_open = float(signal_row["Open"])
            trigger_stoch_k = float(signal_row.get("stoch_k", ctx.stoch_k))
            trigger_stoch_d = float(signal_row.get("stoch_d", ctx.stoch_d))
            trigger_adx = float(signal_row.get("adx", ctx.adx))

        signal: Optional[str] = None
        reasons: list = []
        sl: float = 0.0
        tp: float = 0.0
        bonus: float = 0.0

        # ─── SELL: uptrend で 5m 上方 exhaustion ────────────
        if m15_ema9 > m15_ema21:
            if m5_bbpb < _M5_BBPB_OVERBOUGHT:
                return None
            if not m5_div_bear:
                return None
            # 1m 反転トリガ
            if not (_is_bearish_engulfing(signal_df) or _is_bearish_pin(signal_df)):
                return None
            if not (trigger_stoch_k < trigger_stoch_d):
                return None
            if not (trigger_entry < trigger_open):
                return None
            signal = "SELL"
            sl = m5_high + (1.0 / ctx.pip_mult)
            sl_dist = sl - ctx.entry
            if sl_dist <= 0:
                return None
            sl_dist_pips = sl_dist * ctx.pip_mult
            if sl_dist_pips > _SL_MAX_PIPS:
                return None
            fixed_tp_pips = _FIXED_TP_PIPS.get(pair, 5.0)
            tp_fixed = ctx.entry - fixed_tp_pips / ctx.pip_mult
            tp_rr = ctx.entry - sl_dist * _RR_FLOOR
            tp = min(tp_fixed, tp_rr)  # SELL: lower tp = larger profit
            reasons.append(f"✅ M15 uptrend (ADX={m15_adx:.1f}) → counter SELL")
            reasons.append(f"✅ M5 BB%B={m5_bbpb:.2f} ≥ {_M5_BBPB_OVERBOUGHT} + RSI bear divergence")
            reasons.append("✅ 1m bearish engulfing/pin + Stoch dead cross")

        # ─── BUY: downtrend で 5m 下方 exhaustion ───────────
        elif m15_ema9 < m15_ema21:
            if m5_bbpb > _M5_BBPB_OVERSOLD:
                return None
            if not m5_div_bull:
                return None
            if not (_is_bullish_engulfing(signal_df) or _is_bullish_pin(signal_df)):
                return None
            if not (trigger_stoch_k > trigger_stoch_d):
                return None
            if not (trigger_entry > trigger_open):
                return None
            signal = "BUY"
            sl = m5_low - (1.0 / ctx.pip_mult)
            sl_dist = ctx.entry - sl
            if sl_dist <= 0:
                return None
            sl_dist_pips = sl_dist * ctx.pip_mult
            if sl_dist_pips > _SL_MAX_PIPS:
                return None
            fixed_tp_pips = _FIXED_TP_PIPS.get(pair, 5.0)
            tp_fixed = ctx.entry + fixed_tp_pips / ctx.pip_mult
            tp_rr = ctx.entry + sl_dist * _RR_FLOOR
            tp = max(tp_fixed, tp_rr)
            reasons.append(f"✅ M15 downtrend (ADX={m15_adx:.1f}) → counter BUY")
            reasons.append(f"✅ M5 BB%B={m5_bbpb:.2f} ≤ {_M5_BBPB_OVERSOLD} + RSI bull divergence")
            reasons.append("✅ 1m bullish engulfing/pin + Stoch golden cross")

        if signal is None:
            return None
        # MR 戦略: ADX が高すぎると確率的に勝てない (1m ADX>35 で reject)
        if trigger_adx > 35:
            return None
        if redesign_v2:
            if not ctx.backtest_mode:
                key = (pair, self.name, signal, str(signal_bar_time))
                if key in self._v2_dedup_state:
                    return None
                self._v2_dedup_state.add(key)
            reasons.append(
                f"✅ MTF_COUNTER_TREND_SCALP_REDESIGN_V2: "
                f"closed 1m signal_bar_time={signal_bar_time}; execution uses current bar"
            )

        # ── confidence (counter-trend なので 55 start) ───────
        conf = 55
        # RSI div 強度: 5m RSI 値そのものが極値に達しているほど加点
        m5_rsi = float(m5.get("rsi14", 50.0))
        if (signal == "SELL" and m5_rsi >= 70) or (signal == "BUY" and m5_rsi <= 30):
            conf += 10
            bonus += 1.0
            reasons.append(f"✅ M5 RSI extreme={m5_rsi:.1f}")
        if h_mult <= _HOUR_MULT_PEAK:
            conf += 5
            bonus += 0.5
            reasons.append(f"✅ peak liquidity hour (mult={h_mult:.2f})")
        conf = apply_penalty(conf, self.strategy_type, trigger_adx, conf_max=80)

        # ── score: bb_rsi 範囲に揃える (3.5-5.5) ────────────
        # bb_rsi_reversion: 3.0-15 (extreme zone で大加点)
        # 本戦略は M15+M5 dual gate を通過した時点で confidence 高い
        # ので 3.5 base + bonus (extreme RSI / peak hour) で +0.5 ずつ
        score = 3.5 + bonus * 0.5

        return Candidate(
            signal=signal,
            confidence=int(conf),
            sl=float(sl),
            tp=float(tp),
            reasons=reasons,
            entry_type=self.name,
            score=float(score),
        )
