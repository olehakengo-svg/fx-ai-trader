"""V-Reversal — 急落/急騰後の反転検出 (Cont 2001, Jegadeesh & Titman 1993)"""
import os

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from modules.confidence_v2 import apply_penalty
from typing import Optional


class VReversal(StrategyBase):
    name = "v_reversal"
    mode = "scalp"
    enabled = True   # v7.0: Sentinel再有効化 — デモデータ蓄積優先
    strategy_type = "MR"   # v11: V-reversal = MR by construction

    # チューナブルパラメータ（緩和済み）
    min_drop_pip = 5.0     # 最低急落/急騰幅(pip)（8→5緩和）
    rsi_buy = 30           # RSI14閾値（25→30緩和）
    rsi_sell = 70           # （75→70緩和）
    bbpb_buy = 0.15        # （0.10→0.15緩和）
    bbpb_sell = 0.85        # （0.90→0.85緩和）
    stoch_buy = 20          # （15→20緩和）
    stoch_sell = 80          # （85→80緩和）
    body_ratio_min = 0.20  # 実体比率最低値（0.25→0.20緩和）
    tp_mult = 1.5
    sl_mult = 0.7
    _v2_seen_closed_bar_keys: set[tuple[str, str, str, str]] = set()

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if os.environ.get("V_REVERSAL_REDESIGN_V2") == "1":
            return self._evaluate_closed_bar_v2(ctx)

        if ctx.df is None or len(ctx.df) < 20:
            return None

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0

        # 直近10本の価格変動(pip)
        _lookback = min(10, len(ctx.df) - 1)
        _price_10 = float(ctx.df["Close"].iloc[-_lookback - 1])
        _drop = (_price_10 - ctx.entry) * 100    # 正=下落幅(pip)
        _surge = (ctx.entry - _price_10) * 100    # 正=上昇幅(pip)

        # RSIダイバージェンス検出(直近5本)
        _rsi_vals = [float(ctx.df.iloc[-j].get("rsi", 50)) for j in range(1, min(6, len(ctx.df)))]
        _price_vals = [float(ctx.df["Close"].iloc[-j]) for j in range(1, min(6, len(ctx.df)))]
        _rsi_min_idx = _rsi_vals.index(min(_rsi_vals)) if _rsi_vals else 0
        _price_min_idx = _price_vals.index(min(_price_vals)) if _price_vals else 0
        _rsi_max_idx = _rsi_vals.index(max(_rsi_vals)) if _rsi_vals else 0
        _price_max_idx = _price_vals.index(max(_price_vals)) if _price_vals else 0

        _prev_stoch = float(ctx.df.iloc[-2].get("stoch_k", 50)) if len(ctx.df) >= 2 else 50
        _prev_bbpb = float(ctx.df.iloc[-2].get("bb_pband", 0.5)) if len(ctx.df) >= 2 else 0.5

        # ボディ比率
        _high = float(ctx.df.iloc[-1]["High"])
        _low = float(ctx.df.iloc[-1]["Low"])
        _bar_range = _high - _low if _high > _low else 0.001
        _body_ratio = abs(ctx.entry - ctx.open_price) / _bar_range

        # V字底: BUY
        if (_drop >= self.min_drop_pip
                and ctx.rsi < self.rsi_buy
                and ctx.bbpb < self.bbpb_buy
                and ctx.stoch_k < self.stoch_buy
                and ctx.entry > ctx.open_price
                and _body_ratio >= self.body_ratio_min
                and ctx.stoch_k > _prev_stoch):
            signal = "BUY"
            score = 3.5
            reasons.append(f"✅ V字底検出: 直近{_lookback}本で-{_drop:.1f}pip急落 [Cont 2001]")
            reasons.append(f"✅ 3指標極端: RSI={ctx.rsi:.0f}<{self.rsi_buy}, BB%B={ctx.bbpb:.2f}<{self.bbpb_buy}, Stoch={ctx.stoch_k:.0f}<{self.stoch_buy}")
            reasons.append(f"✅ 陽線+Stoch回復確認(前={_prev_stoch:.0f}→{ctx.stoch_k:.0f})")
            # RSI Bullish Divergence
            if (_price_min_idx < _rsi_min_idx and len(_rsi_vals) >= 3
                    and _rsi_vals[0] > min(_rsi_vals)):
                score += 1.5
                reasons.append("✅ RSI Bullish Divergence: 価格新安値 vs RSI底上げ [Jegadeesh 1993]")
            if ctx.bbpb > _prev_bbpb:
                score += 0.5
                reasons.append(f"✅ BB%B回復({_prev_bbpb:.2f}→{ctx.bbpb:.2f})")
            if ctx.macdh > ctx.macdh_prev:
                score += 0.5
                reasons.append("✅ MACD-H反転上昇")
            tp = ctx.entry + ctx.atr7 * self.tp_mult
            _recent_low = float(ctx.df["Low"].iloc[-3:].min())
            sl = min(ctx.entry - ctx.atr7 * self.sl_mult, _recent_low - 0.002)

        # V字天井: SELL
        elif (_surge >= self.min_drop_pip
                and ctx.rsi > self.rsi_sell
                and ctx.bbpb > self.bbpb_sell
                and ctx.stoch_k > self.stoch_sell
                and ctx.entry < ctx.open_price
                and _body_ratio >= self.body_ratio_min
                and ctx.stoch_k < _prev_stoch):
            signal = "SELL"
            score = 3.5
            reasons.append(f"✅ V字天井検出: 直近{_lookback}本で+{_surge:.1f}pip急騰 [Cont 2001]")
            reasons.append(f"✅ 3指標極端: RSI={ctx.rsi:.0f}>{self.rsi_sell}, BB%B={ctx.bbpb:.2f}>{self.bbpb_sell}, Stoch={ctx.stoch_k:.0f}>{self.stoch_sell}")
            reasons.append(f"✅ 陰線+Stoch反落確認(前={_prev_stoch:.0f}→{ctx.stoch_k:.0f})")
            # RSI Bearish Divergence
            if (_price_max_idx < _rsi_max_idx and len(_rsi_vals) >= 3
                    and _rsi_vals[0] < max(_rsi_vals)):
                score += 1.5
                reasons.append("✅ RSI Bearish Divergence: 価格新高値 vs RSI天井下げ")
            if ctx.bbpb < _prev_bbpb:
                score += 0.5
                reasons.append(f"✅ BB%B反落({_prev_bbpb:.2f}→{ctx.bbpb:.2f})")
            if ctx.macdh < ctx.macdh_prev:
                score += 0.5
                reasons.append("✅ MACD-H反転下落")
            tp = ctx.entry - ctx.atr7 * self.tp_mult
            _recent_high = float(ctx.df["High"].iloc[-3:].max())
            sl = max(ctx.entry + ctx.atr7 * self.sl_mult, _recent_high + 0.002)

        if signal is None:
            return None

        _legacy_conf = int(min(85, 50 + score * 5))
        conf = apply_penalty(_legacy_conf, self.strategy_type, ctx.adx, conf_max=85)
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)

    def _evaluate_closed_bar_v2(self, ctx: SignalContext) -> Optional[Candidate]:
        if ctx.df is None or len(ctx.df) < 20:
            return None

        df = ctx.df
        signal_row = df.iloc[-2]
        prev_row = df.iloc[-3]
        signal_bar_time = df.index[-2] if hasattr(df, "index") else None

        signal_close = float(signal_row["Close"])
        signal_open = float(signal_row["Open"])
        signal_high = float(signal_row["High"])
        signal_low = float(signal_row["Low"])
        signal_rsi = float(signal_row.get("rsi", 50.0))
        signal_bbpb = float(signal_row.get("bb_pband", 0.5))
        signal_stoch = float(signal_row.get("stoch_k", 50.0))
        signal_macdh = float(signal_row.get("macd_hist", 0.0))
        prev_stoch = float(prev_row.get("stoch_k", 50.0))
        prev_bbpb = float(prev_row.get("bb_pband", 0.5))
        prev_macdh = float(prev_row.get("macd_hist", 0.0))

        signal_pos = len(df) - 2
        lookback = min(10, signal_pos)
        price_10 = float(df["Close"].iloc[signal_pos - lookback])
        drop = (price_10 - signal_close) * 100
        surge = (signal_close - price_10) * 100

        start = max(0, signal_pos - 4)
        recent = df.iloc[start:signal_pos + 1]
        rsi_source = recent["rsi"].tail(5) if "rsi" in recent.columns else []
        rsi_vals = [float(v) for v in rsi_source][::-1]
        price_vals = [float(v) for v in recent["Close"].tail(5)][::-1]
        rsi_min_idx = rsi_vals.index(min(rsi_vals)) if rsi_vals else 0
        price_min_idx = price_vals.index(min(price_vals)) if price_vals else 0
        rsi_max_idx = rsi_vals.index(max(rsi_vals)) if rsi_vals else 0
        price_max_idx = price_vals.index(max(price_vals)) if price_vals else 0

        bar_range = signal_high - signal_low if signal_high > signal_low else 0.001
        body_ratio = abs(signal_close - signal_open) / bar_range

        signal = None
        score = 0.0
        reasons = [
            f"V_REVERSAL_REDESIGN_V2 closed-bar signal: closed_bar_time={signal_bar_time}"
        ]
        sl = 0.0
        tp = 0.0

        if (drop >= self.min_drop_pip
                and signal_rsi < self.rsi_buy
                and signal_bbpb < self.bbpb_buy
                and signal_stoch < self.stoch_buy
                and signal_close > signal_open
                and body_ratio >= self.body_ratio_min
                and signal_stoch > prev_stoch):
            signal = "BUY"
            score = 3.5
            reasons.append(f"✅ V字底検出(確定足): 直近{lookback}本で-{drop:.1f}pip急落 [Cont 2001]")
            reasons.append(f"✅ 3指標極端(確定足): RSI={signal_rsi:.0f}<{self.rsi_buy}, BB%B={signal_bbpb:.2f}<{self.bbpb_buy}, Stoch={signal_stoch:.0f}<{self.stoch_buy}")
            reasons.append(f"✅ 陽線+Stoch回復確認(確定足 前={prev_stoch:.0f}→{signal_stoch:.0f})")
            if (price_min_idx < rsi_min_idx and len(rsi_vals) >= 3
                    and rsi_vals[0] > min(rsi_vals)):
                score += 1.5
                reasons.append("✅ RSI Bullish Divergence: 価格新安値 vs RSI底上げ [Jegadeesh 1993]")
            if signal_bbpb > prev_bbpb:
                score += 0.5
                reasons.append(f"✅ BB%B回復(確定足 {prev_bbpb:.2f}→{signal_bbpb:.2f})")
            if signal_macdh > prev_macdh:
                score += 0.5
                reasons.append("✅ MACD-H反転上昇(確定足)")
            tp = ctx.entry + ctx.atr7 * self.tp_mult
            recent_low = float(df["Low"].iloc[max(0, signal_pos - 2):signal_pos + 1].min())
            sl = min(ctx.entry - ctx.atr7 * self.sl_mult, recent_low - 0.002)

        elif (surge >= self.min_drop_pip
                and signal_rsi > self.rsi_sell
                and signal_bbpb > self.bbpb_sell
                and signal_stoch > self.stoch_sell
                and signal_close < signal_open
                and body_ratio >= self.body_ratio_min
                and signal_stoch < prev_stoch):
            signal = "SELL"
            score = 3.5
            reasons.append(f"✅ V字天井検出(確定足): 直近{lookback}本で+{surge:.1f}pip急騰 [Cont 2001]")
            reasons.append(f"✅ 3指標極端(確定足): RSI={signal_rsi:.0f}>{self.rsi_sell}, BB%B={signal_bbpb:.2f}>{self.bbpb_sell}, Stoch={signal_stoch:.0f}>{self.stoch_sell}")
            reasons.append(f"✅ 陰線+Stoch反落確認(確定足 前={prev_stoch:.0f}→{signal_stoch:.0f})")
            if (price_max_idx < rsi_max_idx and len(rsi_vals) >= 3
                    and rsi_vals[0] < max(rsi_vals)):
                score += 1.5
                reasons.append("✅ RSI Bearish Divergence: 価格新高値 vs RSI天井下げ")
            if signal_bbpb < prev_bbpb:
                score += 0.5
                reasons.append(f"✅ BB%B反落(確定足 {prev_bbpb:.2f}→{signal_bbpb:.2f})")
            if signal_macdh < prev_macdh:
                score += 0.5
                reasons.append("✅ MACD-H反転下落(確定足)")
            tp = ctx.entry - ctx.atr7 * self.tp_mult
            recent_high = float(df["High"].iloc[max(0, signal_pos - 2):signal_pos + 1].max())
            sl = max(ctx.entry + ctx.atr7 * self.sl_mult, recent_high + 0.002)

        if signal is None:
            return None

        if not ctx.backtest_mode:
            key = (self.name, str(ctx.symbol), signal, str(signal_bar_time))
            if key in self._v2_seen_closed_bar_keys:
                return None
            self._v2_seen_closed_bar_keys.add(key)

        legacy_conf = int(min(85, 50 + score * 5))
        conf = apply_penalty(legacy_conf, self.strategy_type, ctx.adx, conf_max=85)
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)
