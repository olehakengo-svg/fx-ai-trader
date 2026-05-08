"""SR/Channel Bounce Reversal — 水平線・並行チャネル反発 (Osler 2000)"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from modules.confidence_v2 import apply_penalty
from typing import Optional
import os


class SrChannelReversal(StrategyBase):
    name = "sr_channel_reversal"
    mode = "scalp"
    enabled = True   # v7.0: Sentinel再有効化 — デモデータ蓄積で検証
    strategy_type = "MR"   # v11: S/R bounce = MR by construction

    # チューナブルパラメータ
    sr_proximity = 0.3    # ATR倍率
    rsi5_buy = 45
    rsi5_sell = 55
    tp_mult = 1.5
    sl_mult = 0.5
    sl_sr_offset = 0.15  # ATR倍率
    min_score = 3.0
    v2_sl_boundary_buffer = 1.3  # ATR7倍率: SR/channel境界の外側
    v2_tp_mean_atr = 0.9  # ATR7倍率: mean-side target fallback
    _v2_seen_closed_bar_keys: set[tuple[str, str, str, str]] = set()

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if ctx.is_friday:
            return None
        if not ctx.sr_levels or ctx.df is None or len(ctx.df) < 10:
            return None

        if os.environ.get("SR_CHANNEL_REVERSAL_REDESIGN_V2") == "1":
            return self._evaluate_redesign_v2(ctx)

        return self._evaluate_legacy(ctx)

    def _channel(self, df):
        try:
            from app import find_parallel_channel
            _lookback = min(100, len(df) - 1)
            return find_parallel_channel(df.tail(_lookback), window=5, lookback=_lookback)
        except ImportError:
            return None

    def _evaluate_legacy(self, ctx: SignalContext) -> Optional[Candidate]:
        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0

        # 並行チャネル検出（app.pyのfind_parallel_channelを使用）
        try:
            from app import find_parallel_channel
            _channel = find_parallel_channel(ctx.df, window=5, lookback=min(100, len(ctx.df) - 1))
        except ImportError:
            _channel = None
        _ch_upper = float(_channel["upper"][-1]["value"]) if _channel else None
        _ch_lower = float(_channel["lower"][-1]["value"]) if _channel else None

        # SR近接判定
        _sr_weighted = (ctx.layer3 or {}).get("sr_weighted_levels", [])
        _sr_buy = [l for l in ctx.sr_levels if 0 < ctx.entry - l < ctx.atr * self.sr_proximity]
        _sr_sell = [l for l in ctx.sr_levels if 0 < l - ctx.entry < ctx.atr * self.sr_proximity]
        _at_ch_lower = _ch_lower and abs(ctx.entry - _ch_lower) < ctx.atr * self.sr_proximity
        _at_ch_upper = _ch_upper and abs(ctx.entry - _ch_upper) < ctx.atr * self.sr_proximity

        # BUY
        if (_sr_buy or _at_ch_lower) and ctx.rsi5 < self.rsi5_buy and ctx.stoch_k > ctx.stoch_d:
            score = 3.0
            signal = "BUY"
            if _sr_buy:
                _nearest = max(_sr_buy)
                _sr_level = _nearest
                _dist = abs(ctx.entry - _nearest) / ctx.atr
                score += max(0, (0.3 - _dist) * 3.0)
                reasons.append(f"✅ SRサポート反発({_nearest:.3f}, dist={_dist:.2f}ATR)")
            if _at_ch_lower:
                score += 0.8
                reasons.append(f"✅ チャネル下限反発({_ch_lower:.3f})")
            if ctx.rsi5 < 35:
                score += 0.5
                reasons.append(f"✅ RSI5過売({ctx.rsi5:.0f})")
            if ctx.stoch_k < 30 and ctx.stoch_k > ctx.stoch_d:
                score += 0.5
                reasons.append(f"✅ Stoch反転上昇({ctx.stoch_k:.0f}>{ctx.stoch_d:.0f})")
            if ctx.macdh > 0 or ctx.macdh > ctx.macdh_prev:
                score += 0.4
                reasons.append("✅ MACD-H反転上昇")
            if ctx.entry > ctx.open_price:
                score += 0.3
            tp = ctx.entry + ctx.atr7 * self.tp_mult
            _nearest_sup = max(_sr_buy) if _sr_buy else (_ch_lower if _ch_lower else ctx.entry - ctx.atr7 * self.sl_mult)
            sl = min(ctx.entry - ctx.atr7 * self.sl_mult, _nearest_sup - ctx.atr7 * self.sl_sr_offset)

        # SELL
        elif (_sr_sell or _at_ch_upper) and ctx.rsi5 > self.rsi5_sell and ctx.stoch_k < ctx.stoch_d:
            score = 3.0
            signal = "SELL"
            if _sr_sell:
                _nearest = min(_sr_sell)
                _sr_level = _nearest
                _dist = abs(_nearest - ctx.entry) / ctx.atr
                score += max(0, (0.3 - _dist) * 3.0)
                reasons.append(f"✅ SRレジスタンス反発({_nearest:.3f}, dist={_dist:.2f}ATR)")
            if _at_ch_upper:
                score += 0.8
                reasons.append(f"✅ チャネル上限反発({_ch_upper:.3f})")
            if ctx.rsi5 > 65:
                score += 0.5
                reasons.append(f"✅ RSI5過買({ctx.rsi5:.0f})")
            if ctx.stoch_k > 70 and ctx.stoch_k < ctx.stoch_d:
                score += 0.5
                reasons.append(f"✅ Stoch反転下降({ctx.stoch_k:.0f}<{ctx.stoch_d:.0f})")
            if ctx.macdh < 0 or ctx.macdh < ctx.macdh_prev:
                score += 0.4
                reasons.append("✅ MACD-H反転下降")
            if ctx.entry < ctx.open_price:
                score += 0.3
            tp = ctx.entry - ctx.atr7 * self.tp_mult
            _nearest_res = min(_sr_sell) if _sr_sell else (_ch_upper if _ch_upper else ctx.entry + ctx.atr7 * self.sl_mult)
            sl = max(ctx.entry + ctx.atr7 * self.sl_mult, _nearest_res + ctx.atr7 * self.sl_sr_offset)

        if signal is None or score < self.min_score:
            return None

        _legacy_conf = int(min(85, 45 + score * 5))
        conf = apply_penalty(_legacy_conf, self.strategy_type, ctx.adx, conf_max=85)
        _meta_level = (_sr_level if "_sr_level" in locals()
                       else (_ch_lower if signal == "BUY" else _ch_upper))
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score,
                         sr_meta=Candidate.sr_meta_from_price(
                             _sr_weighted, _meta_level, ctx.entry, ctx.atr))

    def _evaluate_redesign_v2(self, ctx: SignalContext) -> Optional[Candidate]:
        if ctx.df is None or len(ctx.df) < 11:
            return None

        signal_df = ctx.df.iloc[:-1]
        signal_bar = ctx.df.iloc[-2]
        prev_signal_bar = ctx.df.iloc[-3]
        signal_bar_time = getattr(signal_bar, "name", None)
        signal_price = float(signal_bar["Close"])
        signal_open = float(signal_bar["Open"])
        signal_atr = float(signal_bar.get("atr", ctx.atr))
        signal_atr7 = float(signal_bar.get("atr7", signal_atr))
        signal_rsi5 = float(signal_bar.get("rsi5", signal_bar.get("rsi", ctx.rsi5)))
        signal_stoch_k = float(signal_bar.get("stoch_k", ctx.stoch_k))
        signal_stoch_d = float(signal_bar.get("stoch_d", ctx.stoch_d))
        prev_stoch_k = float(prev_signal_bar.get("stoch_k", ctx.stoch_k))
        prev_stoch_d = float(prev_signal_bar.get("stoch_d", ctx.stoch_d))
        signal_macdh = float(signal_bar.get("macd_hist", ctx.macdh))
        signal_macdh_prev = float(prev_signal_bar.get("macd_hist", ctx.macdh_prev))

        _channel = self._channel(signal_df)
        _ch_upper = float(_channel["upper"][-1]["value"]) if _channel else None
        _ch_lower = float(_channel["lower"][-1]["value"]) if _channel else None
        _ch_mid = (
            (_ch_upper + _ch_lower) / 2.0
            if _ch_upper is not None and _ch_lower is not None
            else None
        )

        _sr_prices = [s["price"] if isinstance(s, dict) else s for s in ctx.sr_levels]
        _sr_weighted = (ctx.layer3 or {}).get("sr_weighted_levels", [])
        _sr_buy = [l for l in _sr_prices if 0 < signal_price - l < signal_atr * self.sr_proximity]
        _sr_sell = [l for l in _sr_prices if 0 < l - signal_price < signal_atr * self.sr_proximity]
        _at_ch_lower = (
            _ch_lower is not None
            and abs(signal_price - _ch_lower) < signal_atr * self.sr_proximity
        )
        _at_ch_upper = (
            _ch_upper is not None
            and abs(signal_price - _ch_upper) < signal_atr * self.sr_proximity
        )

        signal = None
        score = 0.0
        reasons = []
        sl = None
        tp = None

        stoch_cross_up = signal_stoch_k > signal_stoch_d and prev_stoch_k <= prev_stoch_d
        stoch_cross_down = signal_stoch_k < signal_stoch_d and prev_stoch_k >= prev_stoch_d
        macdh_turn_up = signal_macdh > signal_macdh_prev or signal_macdh > 0
        macdh_turn_down = signal_macdh < signal_macdh_prev or signal_macdh < 0

        if ((_sr_buy or _at_ch_lower)
                and signal_rsi5 < self.rsi5_buy
                and stoch_cross_up
                and macdh_turn_up):
            score = 3.0
            signal = "BUY"
            boundary_candidates = list(_sr_buy)
            if _at_ch_lower:
                boundary_candidates.append(_ch_lower)
            boundary = max(boundary_candidates)
            sl = boundary - signal_atr7 * self.v2_sl_boundary_buffer

            mean_targets = [ctx.entry + signal_atr7 * self.v2_tp_mean_atr]
            if _ch_mid is not None and _ch_mid > ctx.entry:
                mean_targets.append(_ch_mid)
            mean_targets.extend(l for l in _sr_prices if l > ctx.entry)
            tp = min(mean_targets)

            if _sr_buy:
                _nearest = max(_sr_buy)
                _sr_level = _nearest
                _dist = abs(signal_price - _nearest) / signal_atr
                score += max(0, (0.3 - _dist) * 3.0)
                reasons.append(f"✅ SRサポート反発(closed {_nearest:.3f}, dist={_dist:.2f}ATR)")
            if _at_ch_lower:
                score += 0.8
                reasons.append(f"✅ チャネル下限反発(closed {_ch_lower:.3f})")
            if signal_rsi5 < 35:
                score += 0.5
                reasons.append(f"✅ RSI5過売(closed {signal_rsi5:.0f})")
            if signal_stoch_k < 30:
                score += 0.5
                reasons.append(f"✅ Stoch反転上昇(closed {signal_stoch_k:.0f}>{signal_stoch_d:.0f})")
            if signal_price > signal_open:
                score += 0.3

        elif ((_sr_sell or _at_ch_upper)
                and signal_rsi5 > self.rsi5_sell
                and stoch_cross_down
                and macdh_turn_down):
            score = 3.0
            signal = "SELL"
            boundary_candidates = list(_sr_sell)
            if _at_ch_upper:
                boundary_candidates.append(_ch_upper)
            boundary = min(boundary_candidates)
            sl = boundary + signal_atr7 * self.v2_sl_boundary_buffer

            mean_targets = [ctx.entry - signal_atr7 * self.v2_tp_mean_atr]
            if _ch_mid is not None and _ch_mid < ctx.entry:
                mean_targets.append(_ch_mid)
            mean_targets.extend(l for l in _sr_prices if l < ctx.entry)
            tp = max(mean_targets)

            if _sr_sell:
                _nearest = min(_sr_sell)
                _sr_level = _nearest
                _dist = abs(_nearest - signal_price) / signal_atr
                score += max(0, (0.3 - _dist) * 3.0)
                reasons.append(f"✅ SRレジスタンス反発(closed {_nearest:.3f}, dist={_dist:.2f}ATR)")
            if _at_ch_upper:
                score += 0.8
                reasons.append(f"✅ チャネル上限反発(closed {_ch_upper:.3f})")
            if signal_rsi5 > 65:
                score += 0.5
                reasons.append(f"✅ RSI5過買(closed {signal_rsi5:.0f})")
            if signal_stoch_k > 70:
                score += 0.5
                reasons.append(f"✅ Stoch反転下降(closed {signal_stoch_k:.0f}<{signal_stoch_d:.0f})")
            if signal_price < signal_open:
                score += 0.3

        if signal is None or score < self.min_score:
            return None

        if not ctx.backtest_mode:
            _sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
            _key = (_sym, self.name, str(signal_bar_time), signal)
            if _key in self._v2_seen_closed_bar_keys:
                return None
            self._v2_seen_closed_bar_keys.add(_key)

        reasons.append(
            f"✅ SR_CHANNEL_REVERSAL_REDESIGN_V2: closed_bar_time={signal_bar_time} "
            "で確定し次バー約定"
        )
        reasons.append(
            f"✅ MR geometry: boundary_outside_SL={sl:.5f} mean_side_TP={tp:.5f} "
            f"ATR7={signal_atr7:.5f}"
        )

        _legacy_conf = int(min(85, 45 + score * 5))
        conf = apply_penalty(_legacy_conf, self.strategy_type, ctx.adx, conf_max=85)
        _meta_level = (_sr_level if "_sr_level" in locals()
                       else (_ch_lower if signal == "BUY" else _ch_upper))
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score,
                         sr_meta=Candidate.sr_meta_from_price(
                             _sr_weighted, _meta_level, signal_price, signal_atr))
