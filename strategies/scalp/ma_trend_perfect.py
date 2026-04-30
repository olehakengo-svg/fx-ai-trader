"""MA Trend-Follow Perfect Order (v1b) — H1 EMA200 + M15 大循環 順張り再加速

設計意図 (rule:R1, 2026-04-30, ma_generic_family_v1):
  - ema_trend_scalp の負け要因は「pullback 構造ゆえ ADX>31 で confidence
    ペナルティ → 強トレンド中は発火停止／弱トレンドではダマシ」という
    pullback 型固有の構造。
  - 純粋順張り (パーフェクトオーダー維持時のブレイク再加速) は反証されて
    いないため、ユーザ提示の「移動平均線大循環分析」を素直に実装し
    Shadow 統計でエッジ有無を確定する。

カスケード:
  L1 ペアゲート       : USD_JPY のみ
  L2 H1 マクロ方向    : H1 EMA200 上下 + EMA200 slope (>0 で BUY 側)
  L3 M15 大循環確認   : EMA9>EMA21>EMA50 (BUY) / EMA9<EMA21<EMA50 (SELL) パーフェクトオーダー
                        + M15 ADX≥22 (トレンド強度)
  L4 M5 順張り再加速  : 直前 M5 が EMA21 を再ブレイク → 当バー方向継続
  L5 1m 確認          : 反転バー / MACD-H 同方向

検証要件:
  - 90d × WF 3-fold + Bonferroni
  - スプレッド注入後の PF/Wilson/Kelly で評価
"""
from __future__ import annotations
from typing import Optional

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from modules.confidence_v2 import apply_penalty


_ALLOWED_PAIRS = {"USD_JPY"}
_M15_ADX_MIN = 22.0
_M15_ADX_STRONG = 28.0
_SL_ATR_MULT = 1.0
_TP_ATR_MULT = 1.8
_RR_FLOOR = 1.5
_H1_BIAS_GAP_PCT = 0.001    # 10bps


def _normalize_pair(symbol: str) -> str:
    s = (symbol or "").upper().replace("=X", "").replace("/", "_")
    if "_" in s:
        return s
    if len(s) == 6:
        return f"{s[:3]}_{s[3:]}"
    return s


class MaTrendPerfect(StrategyBase):
    name = "ma_trend_perfect"
    mode = "scalp"
    enabled = True
    strategy_type = "trend"

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if _normalize_pair(ctx.symbol) not in _ALLOWED_PAIRS:
            return None
        if ctx.atr7 <= 0:
            return None

        h1 = ctx.htf.get("h1") if isinstance(ctx.htf, dict) else None
        m15 = ctx.htf.get("m15") if isinstance(ctx.htf, dict) else None
        m5 = ctx.htf.get("m5") if isinstance(ctx.htf, dict) else None
        if not (h1 and m15 and m5):
            return None

        # L2: H1 マクロ方向 (close vs ema200)
        h1_close = float(h1.get("close", 0.0))
        h1_ema200 = float(h1.get("ema200", 0.0))
        if h1_close <= 0 or h1_ema200 <= 0:
            return None
        h1_gap_pct = (h1_close - h1_ema200) / h1_close
        bull_bias = h1_gap_pct > _H1_BIAS_GAP_PCT
        bear_bias = h1_gap_pct < -_H1_BIAS_GAP_PCT
        if not (bull_bias or bear_bias):
            return None

        # L3: M15 大循環 + ADX
        m15_ema9 = float(m15.get("ema9", 0.0))
        m15_ema21 = float(m15.get("ema21", 0.0))
        m15_ema50 = float(m15.get("ema50", 0.0))
        m15_adx = float(m15.get("adx", 0.0))
        m15_slope = float(m15.get("ema_slope", 0.0))
        if m15_adx < _M15_ADX_MIN:
            return None

        perfect_bull = m15_ema9 > m15_ema21 > m15_ema50 and m15_slope > 0
        perfect_bear = m15_ema9 < m15_ema21 < m15_ema50 and m15_slope < 0

        # L4: M5 EMA21 再ブレイク確認 (直前 M5 が ema21 を割って or 抜けて、当バーで方向回復)
        m5_close = float(m5.get("close", 0.0))
        m5_prev_close = float(m5.get("prev_close", 0.0))
        m5_ema21 = float(m5.get("ema21", 0.0))
        if m5_close <= 0 or m5_ema21 <= 0:
            return None

        signal: Optional[str] = None
        sl: float = 0.0
        tp: float = 0.0
        reasons: list = []
        score = 3.0

        # BUY: bull bias × M15 大循環 × M5 EMA21 上抜け再加速 × 1m 確認
        if (bull_bias and perfect_bull
                and m5_prev_close <= m5_ema21
                and m5_close > m5_ema21
                and ctx.entry > ctx.open_price
                and ctx.macdh > ctx.macdh_prev):
            signal = "BUY"
            sl_dist = ctx.atr7 * _SL_ATR_MULT
            sl = ctx.entry - sl_dist
            tp_dist = max(ctx.atr7 * _TP_ATR_MULT, sl_dist * _RR_FLOOR)
            tp = ctx.entry + tp_dist
            reasons.append(f"✅ H1 EMA200 上向き ({h1_gap_pct*100:.2f}%)")
            reasons.append(f"✅ M15 大循環 BUY EMA9>21>50 ADX={m15_adx:.1f} slope={m15_slope:.4f}")
            reasons.append(f"✅ M5 EMA21 上抜け再加速 (prev_close={m5_prev_close:.4f}≤ema21={m5_ema21:.4f}<close={m5_close:.4f})")
            reasons.append("✅ 1m 陽線 + MACD-H 上昇")
            if m15_adx >= _M15_ADX_STRONG:
                score += 0.8
                reasons.append(f"✅ M15 強トレンド (ADX≥{_M15_ADX_STRONG})")

        elif (bear_bias and perfect_bear
                and m5_prev_close >= m5_ema21
                and m5_close < m5_ema21
                and ctx.entry < ctx.open_price
                and ctx.macdh < ctx.macdh_prev):
            signal = "SELL"
            sl_dist = ctx.atr7 * _SL_ATR_MULT
            sl = ctx.entry + sl_dist
            tp_dist = max(ctx.atr7 * _TP_ATR_MULT, sl_dist * _RR_FLOOR)
            tp = ctx.entry - tp_dist
            reasons.append(f"✅ H1 EMA200 下向き ({h1_gap_pct*100:.2f}%)")
            reasons.append(f"✅ M15 大循環 SELL EMA9<21<50 ADX={m15_adx:.1f} slope={m15_slope:.4f}")
            reasons.append(f"✅ M5 EMA21 下抜け再加速 (prev_close={m5_prev_close:.4f}≥ema21={m5_ema21:.4f}>close={m5_close:.4f})")
            reasons.append("✅ 1m 陰線 + MACD-H 下落")
            if m15_adx >= _M15_ADX_STRONG:
                score += 0.8
                reasons.append(f"✅ M15 強トレンド (ADX≥{_M15_ADX_STRONG})")

        if signal is None:
            return None

        legacy_conf = int(min(85, 55 + score * 4))
        conf = apply_penalty(legacy_conf, self.strategy_type, ctx.adx, conf_max=85)

        return Candidate(
            signal=signal, confidence=int(conf),
            sl=float(sl), tp=float(tp),
            reasons=reasons, entry_type=self.name, score=float(score),
        )
