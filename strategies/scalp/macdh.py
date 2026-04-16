"""MACD Histogram Reversal at BB Extreme — モメンタム消耗 + 価格極端 = 高確率反転"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class MacdhReversal(StrategyBase):
    name = "macdh_reversal"
    mode = "scalp"

    # チューナブルパラメータ (v6.3 対策強化)
    bbpb_buy = 0.30       # BB%B BUY閾値（0.25→0.30緩和）
    bbpb_sell = 0.70      # BB%B SELL閾値（0.75→0.70緩和）
    rsi5_buy = 48         # RSI5 BUY閾値（42→48緩和）
    rsi5_sell = 52        # RSI5 SELL閾値（58→52緩和）
    tp_mult = 1.5         # TP倍率 (デフォルト)
    sl_mult = 1.0         # SL倍率
    # v6.3 追加パラメータ
    tier1_bbpb_buy = 0.15   # Tier1: BB極端ゾーン (v6.3: 高確信エントリー)
    tier1_bbpb_sell = 0.85  # Tier1: BB極端ゾーン
    tier1_tp_mult = 1.8     # Tier1: TP拡大 (反転確度↑ → より深い利確)
    min_macdh_delta = 0.5   # v6.3: MACD-H反転強度フィルター (前2本平均の50%以上)

    # ── ペア×セッションフィルター (v6.3: Death Valley全ペア適用) ──
    _disabled_symbols = frozenset({"EURGBP"})
    # v6.3: bb_rsiで効果実証済みのDeath Valley時間帯を全ペアに適用
    _death_valley_hours = frozenset({0, 1, 9, 12, 13, 14, 15, 16})
    _blocked_hours_by_pair = {
        "XAUUSD": frozenset(range(12, 16)),  # NY_Overlapブロック (既存)
        "USDJPY": frozenset({0, 1, 9}),      # v6.3: Death Valley部分適用
    }

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        _sym = ctx.symbol.upper().replace("=X", "").replace("_", "")
        if _sym in self._disabled_symbols:
            return None
        _blocked = self._blocked_hours_by_pair.get(_sym)
        if _blocked and ctx.hour_utc in _blocked:
            return None

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0

        # ── v6.3: MACD-H反転強度チェック ──
        _macdh_avg = (abs(ctx.macdh_prev) + abs(ctx.macdh_prev2)) / 2 if (ctx.macdh_prev2 != 0) else abs(ctx.macdh_prev)
        _macdh_delta = abs(ctx.macdh - ctx.macdh_prev)
        _macdh_strong = _macdh_delta >= _macdh_avg * self.min_macdh_delta if _macdh_avg > 0 else True

        # BUY: BB下限 + MACD-H上向き反転
        if (ctx.bbpb < self.bbpb_buy
                and ctx.macdh > ctx.macdh_prev
                and ctx.macdh_prev <= ctx.macdh_prev2
                and ctx.rsi5 < self.rsi5_buy
                and _macdh_strong):
            # v6.3: Tier判定 (BB極端ゾーン = 高確信)
            _is_tier1 = ctx.bbpb <= self.tier1_bbpb_buy
            _tp_m = self.tier1_tp_mult if _is_tier1 else self.tp_mult
            signal = "BUY"
            score = 4.0 if _is_tier1 else 3.5
            reasons.append(f"✅ MACD-Hモメンタム反転上昇(H={ctx.macdh:.4f}, 前={ctx.macdh_prev:.4f}, delta={_macdh_delta:.4f})")
            reasons.append(f"✅ BB下限圏(%B={ctx.bbpb:.2f}<{self.bbpb_buy}){' [Tier1]' if _is_tier1 else ''}")
            reasons.append(f"✅ RSI5売られすぎ({ctx.rsi5:.1f}<{self.rsi5_buy})")
            if ctx.stoch_k > ctx.stoch_d:
                score += 0.5
                reasons.append("✅ Stochゴールデンクロス(K>D)")
            tp = ctx.entry + ctx.atr7 * _tp_m
            sl = ctx.entry - ctx.atr7 * self.sl_mult

        # SELL: BB上限 + MACD-H下向き反転
        elif (ctx.bbpb > self.bbpb_sell
                and ctx.macdh < ctx.macdh_prev
                and ctx.macdh_prev >= ctx.macdh_prev2
                and ctx.rsi5 > self.rsi5_sell
                and _macdh_strong):
            _is_tier1 = ctx.bbpb >= self.tier1_bbpb_sell
            _tp_m = self.tier1_tp_mult if _is_tier1 else self.tp_mult
            signal = "SELL"
            score = 4.0 if _is_tier1 else 3.5
            reasons.append(f"✅ MACD-Hモメンタム反転下落(H={ctx.macdh:.4f}, 前={ctx.macdh_prev:.4f}, delta={_macdh_delta:.4f})")
            reasons.append(f"✅ BB上限圏(%B={ctx.bbpb:.2f}>{self.bbpb_sell}){' [Tier1]' if _is_tier1 else ''}")
            reasons.append(f"✅ RSI5買われすぎ({ctx.rsi5:.1f}>{self.rsi5_sell})")
            if ctx.stoch_k < ctx.stoch_d:
                score += 0.5
                reasons.append("✅ Stochデッドクロス(K<D)")
            tp = ctx.entry - ctx.atr7 * _tp_m
            sl = ctx.entry + ctx.atr7 * self.sl_mult

        if signal is None:
            return None

        conf = int(min(80, 45 + score * 4))
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)
