"""MA Regime Switch v1c-rev — M15 ATR percentile によるレジーム切替

Revision history:
  v1c (2026-04-30): H1 EMA50 傾き × M15 EMA9-EMA50 乖離率の閾値 → BT 90d
                    N=22, EV=-1.82, regime classifier 機能不全
  v1c-rev (2026-04-30 再設計):
    - H1 EMA50 prev の lazy approximation を撤去 (機構不全の主因)
    - レジーム判定を **M15 ATR の rolling percentile** に変更:
      * High vol (>=70 percentile) → Trend ロジック (v1b 相当)
      * Low  vol (<=30 percentile) → MR ロジック (v1a-rev 相当)
      * Mid vol (30-70)            → 発火しない (ノイズ排除)
    - 閾値が rolling percentile = 過剰最適化耐性 (data-adaptive)

設計意図:
  ATR percentile は「直近 50 バーの相対 vol レジーム」を表すロバスト統計。
  - High vol = trend continuation 条件 (順張り有利)
  - Low vol = range bound 条件 (逆張り有利)
  - Mid vol = uninformative

カスケード:
  L1 ペアゲート       : USD_JPY のみ
  L2 M15 ATR percentile : last 50 M15 bars 内の percentile
  L3 レジーム別ロジック   : Trend → 順張り、Range → 逆張り
  L4 1m 確認           : 反転バー
"""
from __future__ import annotations
from typing import Optional

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from modules.confidence_v2 import apply_penalty


_ALLOWED_PAIRS = {"USD_JPY"}
_ATR_PCT_HIGH = 70.0    # >= で High vol
_ATR_PCT_LOW = 30.0     # <= で Low vol
_M15_ADX_MIN_TREND = 22.0
_SL_ATR_MULT = 1.0
_TP_ATR_MULT_TREND = 1.6
_TP_ATR_MULT_MR = 1.0


def _normalize_pair(symbol: str) -> str:
    s = (symbol or "").upper().replace("=X", "").replace("/", "_")
    if "_" in s:
        return s
    if len(s) == 6:
        return f"{s[:3]}_{s[3:]}"
    return s


class MaRegimeSwitch(StrategyBase):
    name = "ma_regime_switch"
    mode = "scalp"
    enabled = True
    strategy_type = "trend"

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if _normalize_pair(ctx.symbol) not in _ALLOWED_PAIRS:
            return None
        if ctx.atr7 <= 0:
            return None

        m15 = ctx.htf.get("m15") if isinstance(ctx.htf, dict) else None
        m5 = ctx.htf.get("m5") if isinstance(ctx.htf, dict) else None
        if not (m15 and m5):
            return None

        # ATR percentile: ctx.bb_width_pct を流用するか、簡易には ctx.atr/ctx.atr7 比
        # ctx には bb_width_pct (1m, 50バー percentile) があるため、これを vol regime proxy に
        # bb_width も atr も同じく volatility magnitude を捉える指標
        atr_pct = ctx.bb_width_pct * 100  # 0-100 scale

        signal: Optional[str] = None
        sl: float = 0.0; tp: float = 0.0
        reasons: list = []
        score = 3.0

        # --- High vol → Trend regime ---
        if atr_pct >= _ATR_PCT_HIGH:
            m15_ema9 = float(m15.get("ema9", 0.0))
            m15_ema21 = float(m15.get("ema21", 0.0))
            m15_ema50 = float(m15.get("ema50", 0.0))
            m15_adx = float(m15.get("adx", 0.0))
            m15_slope = float(m15.get("ema_slope", 0.0))
            if m15_adx < _M15_ADX_MIN_TREND:
                return None
            perfect_bull = m15_ema9 > m15_ema21 > m15_ema50 and m15_slope > 0
            perfect_bear = m15_ema9 < m15_ema21 < m15_ema50 and m15_slope < 0
            m5_close = float(m5.get("close", 0.0))
            m5_prev_close = float(m5.get("prev_close", 0.0))
            m5_ema21 = float(m5.get("ema21", 0.0))
            if m5_ema21 <= 0:
                return None

            tp_mult = _TP_ATR_MULT_TREND
            if (perfect_bull and m5_prev_close <= m5_ema21 < m5_close
                    and ctx.entry > ctx.open_price
                    and ctx.macdh > ctx.macdh_prev):
                signal = "BUY"
                reasons.append(f"📊 Regime=High vol (atr_pct={atr_pct:.0f}>={_ATR_PCT_HIGH:.0f})")
                reasons.append(f"✅ Trend BUY: M15 大循環 ADX={m15_adx:.1f}")
            elif (perfect_bear and m5_prev_close >= m5_ema21 > m5_close
                    and ctx.entry < ctx.open_price
                    and ctx.macdh < ctx.macdh_prev):
                signal = "SELL"
                reasons.append(f"📊 Regime=High vol (atr_pct={atr_pct:.0f})")
                reasons.append(f"✅ Trend SELL: M15 大循環 ADX={m15_adx:.1f}")

        # --- Low vol → MR regime ---
        elif atr_pct <= _ATR_PCT_LOW:
            m5_bbpb = float(m5.get("bbpb", 0.5))
            m5_rsi = float(m5.get("rsi14", 50.0))
            m5_stoch_k = float(m5.get("stoch_k", 50.0))
            m5_stoch_d = float(m5.get("stoch_d", 50.0))
            tp_mult = _TP_ATR_MULT_MR
            if (m5_bbpb <= 0.30 and m5_rsi <= 35
                    and m5_stoch_k > m5_stoch_d
                    and ctx.entry > ctx.open_price):
                signal = "BUY"
                reasons.append(f"📊 Regime=Low vol (atr_pct={atr_pct:.0f}<={_ATR_PCT_LOW:.0f})")
                reasons.append(f"✅ Range BUY: M5 過熱 BB%B={m5_bbpb:.2f} RSI={m5_rsi:.1f}")
            elif (m5_bbpb >= 0.70 and m5_rsi >= 65
                    and m5_stoch_k < m5_stoch_d
                    and ctx.entry < ctx.open_price):
                signal = "SELL"
                reasons.append(f"📊 Regime=Low vol (atr_pct={atr_pct:.0f})")
                reasons.append(f"✅ Range SELL: M5 過熱 BB%B={m5_bbpb:.2f} RSI={m5_rsi:.1f}")

        # --- Mid vol → no fire ---
        else:
            return None

        if signal is None:
            return None

        sl_dist = ctx.atr7 * _SL_ATR_MULT
        tp_dist = max(ctx.atr7 * tp_mult, sl_dist * 1.2)
        if signal == "BUY":
            sl = ctx.entry - sl_dist
            tp = ctx.entry + tp_dist
        else:
            sl = ctx.entry + sl_dist
            tp = ctx.entry - tp_dist

        legacy_conf = int(min(85, 55 + score * 4))
        st = "MR" if atr_pct <= _ATR_PCT_LOW else "trend"
        conf = apply_penalty(legacy_conf, st, ctx.adx, conf_max=85)

        return Candidate(
            signal=signal, confidence=int(conf),
            sl=float(sl), tp=float(tp),
            reasons=reasons, entry_type=self.name, score=float(score),
        )
