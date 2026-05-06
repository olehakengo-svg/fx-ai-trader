"""Three-Bar Reversal — 3本足反転パターン"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from modules.confidence_v2 import apply_penalty
from typing import Optional
import os


class ThreeBarReversal(StrategyBase):
    name = "three_bar_reversal"
    mode = "scalp"
    enabled = True   # v7.0: Sentinel再有効化 — デモデータ蓄積で検証
    strategy_type = "MR"   # v11: 3-bar reversal = MR

    # チューナブルパラメータ
    bbpb_buy = 0.35
    bbpb_sell = 0.65
    rsi5_buy = 42
    rsi5_sell = 58
    tp_mult = 1.5
    sl_offset = 0.15  # ATR倍率
    _v2_seen_bar_keys: set[tuple[str, str, str, str]] = set()

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if ctx.is_friday:
            return None
        if ctx.df is None or len(ctx.df) < 4:
            return None

        if os.environ.get("THREE_BAR_REVERSAL_REDESIGN_V2") == "1":
            return self._evaluate_redesign_v2(ctx)

        return self._evaluate_legacy(ctx)

    def _evaluate_legacy(self, ctx: SignalContext) -> Optional[Candidate]:

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0

        _c3 = float(ctx.df.iloc[-4]["Close"]); _o3 = float(ctx.df.iloc[-4]["Open"])
        _c2 = float(ctx.df.iloc[-3]["Close"]); _o2 = float(ctx.df.iloc[-3]["Open"])
        _c1 = float(ctx.df.iloc[-2]["Close"]); _o1 = float(ctx.df.iloc[-2]["Open"])

        _three_bear = (_c3 < _o3) and (_c2 < _o2) and (_c1 < _o1)
        _three_bull = (_c3 > _o3) and (_c2 > _o2) and (_c1 > _o1)

        # BUY: 3連続陰線→陽線
        _curr_bull = ctx.entry > ctx.open_price
        if (_three_bear and _curr_bull
                and ctx.entry > float(ctx.df.iloc[-2]["High"])
                and ctx.bbpb < self.bbpb_buy
                and ctx.rsi5 < self.rsi5_buy):
            signal = "BUY"
            score = 3.3
            reasons.append("✅ 3本足反転: 3連続陰線→陽線突破")
            reasons.append(f"✅ 前足高値{float(ctx.df.iloc[-2]['High']):.3f}超え — 反転確認")
            reasons.append(f"✅ BB下半分(%B={ctx.bbpb:.2f}) + RSI={ctx.rsi5:.0f}")
            if ctx.stoch_k > ctx.stoch_d:
                score += 0.4
                reasons.append("✅ Stochクロス確認")
            tp = ctx.entry + ctx.atr7 * self.tp_mult
            sl = min(float(ctx.df.iloc[-2]["Low"]), float(ctx.df.iloc[-3]["Low"])) - ctx.atr7 * self.sl_offset

        # SELL: 3連続陽線→陰線
        _curr_bear = ctx.entry < ctx.open_price
        if (signal is None and _three_bull and _curr_bear
                and ctx.entry < float(ctx.df.iloc[-2]["Low"])
                and ctx.bbpb > self.bbpb_sell
                and ctx.rsi5 > self.rsi5_sell):
            signal = "SELL"
            score = 3.3
            reasons.append("✅ 3本足反転: 3連続陽線→陰線突破")
            reasons.append(f"✅ 前足安値{float(ctx.df.iloc[-2]['Low']):.3f}割れ — 反転確認")
            reasons.append(f"✅ BB上半分(%B={ctx.bbpb:.2f}) + RSI={ctx.rsi5:.0f}")
            if ctx.stoch_k < ctx.stoch_d:
                score += 0.4
                reasons.append("✅ Stochデッドクロス確認")
            tp = ctx.entry - ctx.atr7 * self.tp_mult
            sl = max(float(ctx.df.iloc[-2]["High"]), float(ctx.df.iloc[-3]["High"])) + ctx.atr7 * self.sl_offset

        if signal is None:
            return None

        _legacy_conf = int(min(78, 45 + score * 4))
        conf = apply_penalty(_legacy_conf, self.strategy_type, ctx.adx, conf_max=78)
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)

    def _evaluate_redesign_v2(self, ctx: SignalContext) -> Optional[Candidate]:
        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0

        _c3 = float(ctx.df.iloc[-4]["Close"]); _o3 = float(ctx.df.iloc[-4]["Open"])
        _c2 = float(ctx.df.iloc[-3]["Close"]); _o2 = float(ctx.df.iloc[-3]["Open"])
        _c1 = float(ctx.df.iloc[-2]["Close"]); _o1 = float(ctx.df.iloc[-2]["Open"])
        _prev_high = float(ctx.df.iloc[-2]["High"])
        _prev_low = float(ctx.df.iloc[-2]["Low"])

        _three_bear = (_c3 < _o3) and (_c2 < _o2) and (_c1 < _o1)
        _three_bull = (_c3 > _o3) and (_c2 > _o2) and (_c1 > _o1)
        _prev_open = float(ctx.df.iloc[-2]["Open"])

        _curr_bull = ctx.entry > ctx.open_price
        if (_three_bear and _curr_bull
                and ctx.entry > _prev_open
                and ctx.bbpb < 0.40
                and ctx.rsi5 < 45):
            signal = "BUY"
            score = 3.3
            reasons.append("✅ THREE_BAR_REVERSAL_REDESIGN_V2: 3連続陰線→陽線")
            reasons.append(f"✅ 前足Open{_prev_open:.3f}回復 — 反転初動確認")
            reasons.append(f"✅ BB下側(%B={ctx.bbpb:.2f}<0.40) + RSI5={ctx.rsi5:.0f}<45")
            if ctx.stoch_k > ctx.stoch_d:
                score += 0.4
                reasons.append("✅ Stochクロス確認")
            tp = ctx.entry + ctx.atr7 * self.tp_mult
            sl = min(_prev_low, float(ctx.df.iloc[-3]["Low"])) - ctx.atr7 * self.sl_offset

        _curr_bear = ctx.entry < ctx.open_price
        if (signal is None and _three_bull and _curr_bear
                and ctx.entry < _prev_open
                and ctx.bbpb > 0.60
                and ctx.rsi5 > 55):
            signal = "SELL"
            score = 3.3
            reasons.append("✅ THREE_BAR_REVERSAL_REDESIGN_V2: 3連続陽線→陰線")
            reasons.append(f"✅ 前足Open{_prev_open:.3f}割れ — 反転初動確認")
            reasons.append(f"✅ BB上側(%B={ctx.bbpb:.2f}>0.60) + RSI5={ctx.rsi5:.0f}>55")
            if ctx.stoch_k < ctx.stoch_d:
                score += 0.4
                reasons.append("✅ Stochデッドクロス確認")
            tp = ctx.entry - ctx.atr7 * self.tp_mult
            sl = max(_prev_high, float(ctx.df.iloc[-3]["High"])) + ctx.atr7 * self.sl_offset

        if signal is None:
            return None

        if not ctx.backtest_mode:
            _sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
            _key = (_sym, self.name, str(ctx.bar_time), signal)
            if _key in self._v2_seen_bar_keys:
                return None
            self._v2_seen_bar_keys.add(_key)

        _legacy_conf = int(min(78, 45 + score * 4))
        conf = apply_penalty(_legacy_conf, self.strategy_type, ctx.adx, conf_max=78)
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)
