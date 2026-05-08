"""MA-MR Hybrid v1a-rev — M15 短期トレンド × M5 過熱リバージョン (USD_JPY 限定)

Revision history:
  v1a (2026-04-30): H1 EMA200 整合 × M5 BB%B≤0.20/RSI≤30 過熱 → BT 90d N=66
                    EV=-0.51 で失敗 (閾値厳しすぎ N不足)
  v1a-rev (2026-04-30 再設計):
    - H1 EMA200 整合を撤去 (v1d 失敗で「EMA200 整合は MR エッジを破壊」確定)
    - 方向フィルタを M15 EMA21 vs price に変更 (短期メソトレンド整合)
    - 閾値を bb_rsi v7.0 (LIVE Kelly 0.43) と同水準に緩和
      BB%B 0.30/0.70, RSI 35/65 → カバレッジ +50% 想定
    - ADX>=30 ボーナス (LIVE bb_rsi USD_JPY での「トレンド中BB反発 WR=60%」条件)

設計意図:
  既存 bb_rsi_reversion との差別化点:
    1. M15 メソトレンド整合 (短期方向の追風) — H1 EMA200 ではなく短期軸
    2. ADX>=30 必須化ではなく重み付けで MR 機構を保護

カスケード:
  L1 ペアゲート       : USD_JPY のみ
  L2 M15 短期方向     : M15 close vs ema21 (BUY/SELL バイアス、>5bps gap)
  L3 M5 過熱判定      : BB%B≤0.30 / ≥0.70 + RSI(M5,14)≤35/≥65 + Stoch反転
  L4 1m 確認足        : 反転バー
  Bonus: ADX>=30      : trend-aware MR (LIVE 実証ボーナス)
"""
from __future__ import annotations
import os
from typing import Optional

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from modules.confidence_v2 import apply_penalty


def _v2_active() -> bool:
    """W4 redesign v2 gate. Default off; when on, M15 hard-gate becomes a soft
    score feature so the strategy can emit signals even on neutral M15 bias.
    Wired to ScalperEngine.split_shadow_always for shadow-promote enrolment."""
    return os.environ.get("MA_MR_HYBRID_REDESIGN_V2", "0").lower() in ("1", "true", "yes")


_ALLOWED_PAIRS = {"USD_JPY"}
_BBPB_BUY_MAX = 0.30      # 緩和 (was 0.20)
_BBPB_SELL_MIN = 0.70     # 緩和 (was 0.80)
_RSI_BUY_MAX = 35.0       # 緩和 (was 30.0)
_RSI_SELL_MIN = 65.0      # 緩和 (was 70.0)
_M15_BIAS_GAP_PCT = 0.0005   # 5bps (短期メソでは緩く)
_SL_ATR_MULT = 1.2
_TP_ATR_MULT = 1.0        # MR は早めに刈る
_RR_FLOOR = 1.0


def _normalize_pair(symbol: str) -> str:
    s = (symbol or "").upper().replace("=X", "").replace("/", "_")
    if "_" in s:
        return s
    if len(s) == 6:
        return f"{s[:3]}_{s[3:]}"
    return s


class MaMrHybrid(StrategyBase):
    name = "ma_mr_hybrid"
    mode = "scalp"
    enabled = True
    strategy_type = "MR"

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if _normalize_pair(ctx.symbol) not in _ALLOWED_PAIRS:
            return None
        if ctx.atr7 <= 0 or ctx.atr <= 0:
            return None

        m15 = ctx.htf.get("m15") if isinstance(ctx.htf, dict) else None
        m5 = ctx.htf.get("m5") if isinstance(ctx.htf, dict) else None
        if not (m15 and m5):
            return None

        # L2: M15 メソトレンド (short-term)
        m15_close = float(m15.get("close", 0.0))
        m15_ema21 = float(m15.get("ema21", 0.0))
        if m15_close <= 0 or m15_ema21 <= 0:
            return None
        m15_gap_pct = (m15_close - m15_ema21) / m15_close
        bull_bias = m15_gap_pct > _M15_BIAS_GAP_PCT
        bear_bias = m15_gap_pct < -_M15_BIAS_GAP_PCT
        v2 = _v2_active()
        if not (bull_bias or bear_bias) and not v2:
            return None
        if v2 and not (bull_bias or bear_bias):
            # In v2 the M15 bias is no longer a hard gate. Direction is taken
            # purely from M5 over-extension; bias is folded into score below.
            bull_bias = bear_bias = False

        # L3: M5 過熱
        m5_bbpb = float(m5.get("bbpb", 0.5))
        m5_rsi = float(m5.get("rsi14", 50.0))
        m5_stoch_k = float(m5.get("stoch_k", 50.0))
        m5_stoch_d = float(m5.get("stoch_d", 50.0))

        signal: Optional[str] = None
        sl: float = 0.0; tp: float = 0.0
        reasons: list = []
        score = 3.0

        _min_sl = 0.030 if ctx.pip_mult == 100 else 0.00030

        buy_dir_ok = bull_bias or v2
        sell_dir_ok = bear_bias or v2

        if (buy_dir_ok
                and m5_bbpb <= _BBPB_BUY_MAX
                and m5_rsi <= _RSI_BUY_MAX
                and m5_stoch_k > m5_stoch_d
                and ctx.entry > ctx.open_price):
            signal = "BUY"
            sl_dist = max(ctx.atr7 * _SL_ATR_MULT, _min_sl)
            sl = ctx.entry - sl_dist
            tp_dist = max(ctx.atr7 * _TP_ATR_MULT, sl_dist * _RR_FLOOR)
            tp = ctx.entry + tp_dist
            if v2:
                reasons.append("✅ [MA_MR_HYBRID_REDESIGN_V2] M15 bias gate -> soft score")
                if bull_bias:
                    score += 0.5
                    reasons.append(f"✅ M15 短期上向き soft-bonus ({m15_gap_pct*100:.2f}%)")
            else:
                reasons.append(f"✅ M15 短期上向き ({m15_gap_pct*100:.2f}%)")
            reasons.append(f"✅ M5 過熱 BB%B={m5_bbpb:.2f}≤{_BBPB_BUY_MAX} RSI={m5_rsi:.1f}≤{_RSI_BUY_MAX}")
            reasons.append(f"✅ Stoch反転 K={m5_stoch_k:.0f}>D={m5_stoch_d:.0f}")
            reasons.append("✅ 1m 陽線確認")
            if m5_bbpb <= 0.10 and m5_rsi <= 25:
                score += 1.0
                reasons.append("🎯 Tier1: 極端ゾーン")

        elif (sell_dir_ok
                and m5_bbpb >= _BBPB_SELL_MIN
                and m5_rsi >= _RSI_SELL_MIN
                and m5_stoch_k < m5_stoch_d
                and ctx.entry < ctx.open_price):
            signal = "SELL"
            sl_dist = max(ctx.atr7 * _SL_ATR_MULT, _min_sl)
            sl = ctx.entry + sl_dist
            tp_dist = max(ctx.atr7 * _TP_ATR_MULT, sl_dist * _RR_FLOOR)
            tp = ctx.entry - tp_dist
            if v2:
                reasons.append("✅ [MA_MR_HYBRID_REDESIGN_V2] M15 bias gate -> soft score")
                if bear_bias:
                    score += 0.5
                    reasons.append(f"✅ M15 短期下向き soft-bonus ({m15_gap_pct*100:.2f}%)")
            else:
                reasons.append(f"✅ M15 短期下向き ({m15_gap_pct*100:.2f}%)")
            reasons.append(f"✅ M5 過熱 BB%B={m5_bbpb:.2f}≥{_BBPB_SELL_MIN} RSI={m5_rsi:.1f}≥{_RSI_SELL_MIN}")
            reasons.append(f"✅ Stoch反転 K={m5_stoch_k:.0f}<D={m5_stoch_d:.0f}")
            reasons.append("✅ 1m 陰線確認")
            if m5_bbpb >= 0.90 and m5_rsi >= 75:
                score += 1.0
                reasons.append("🎯 Tier1: 極端ゾーン")

        if signal is None:
            return None

        # ADX>=30 ボーナス (LIVE bb_rsi USD_JPY での「トレンド中BB反発 WR=60%」条件)
        if ctx.adx >= 30:
            score += 0.6
            reasons.append(f"✅ ADX={ctx.adx:.1f}>=30 (LIVE 高 WR 条件)")

        legacy_conf = int(min(85, 55 + score * 4))
        conf = apply_penalty(legacy_conf, self.strategy_type, ctx.adx, conf_max=85)

        return Candidate(
            signal=signal, confidence=int(conf),
            sl=float(sl), tp=float(tp),
            reasons=reasons, entry_type=self.name, score=float(score),
        )
