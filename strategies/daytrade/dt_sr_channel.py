"""DT SR/Channel Reversal — 15m足SR/チャネルバウンス"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional
import os


class DtSrChannelReversal(StrategyBase):
    name = "dt_sr_channel_reversal"
    mode = "daytrade"
    enabled = True   # v7.0: Sentinel再有効化 — デモデータ蓄積で再検証
    strategy_type = "MR"

    # チューナブルパラメータ
    sr_proximity = 0.4  # ATR倍率
    v2_sl_boundary_buffer = 1.3  # ATR7倍率: SR/channel境界の外側
    v2_tp_mean_atr = 1.0  # ATR7倍率: mean-side target fallback
    _v2_seen_closed_bar_keys: set[tuple[str, str, str, str]] = set()

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if not ctx.sr_levels or ctx.df is None or len(ctx.df) < 20:
            return None

        if os.environ.get("DT_SR_CHANNEL_REDESIGN_V2") == "1":
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
        if not ctx.sr_levels or ctx.df is None or len(ctx.df) < 20:
            return None

        # ── v9.1: HTF Hard Block (戦略内self-contained) ──
        # GBP_USD Live: HTF=bull時にSELL 4/4全敗の根本原因対策
        _htf = ctx.htf or {}
        _htf_agreement = _htf.get("agreement", "mixed")

        signal = None
        score = 0.0
        reasons = []

        # チャネル検出
        _ch = self._channel(ctx.df)
        _ch_upper = float(_ch["upper"][-1]["value"]) if _ch else None
        _ch_lower = float(_ch["lower"][-1]["value"]) if _ch else None

        _sr_prices = [s["price"] if isinstance(s, dict) else s for s in ctx.sr_levels]
        _sr_weighted = (ctx.layer3 or {}).get("sr_weighted_levels", [])
        _sr_buy = [l for l in _sr_prices if 0 < ctx.entry - l < ctx.atr * self.sr_proximity]
        _sr_sell = [l for l in _sr_prices if 0 < l - ctx.entry < ctx.atr * self.sr_proximity]
        _at_ch_lower = _ch_lower and abs(ctx.entry - _ch_lower) < ctx.atr * self.sr_proximity
        _at_ch_upper = _ch_upper and abs(ctx.entry - _ch_upper) < ctx.atr * self.sr_proximity

        # BUY (HTF bear → block)
        if (_htf_agreement != "bear"
                and (_sr_buy or _at_ch_lower)
                and ctx.rsi < 45 and ctx.macdh > ctx.macdh_prev):
            signal = "BUY"
            score = 3.2
            if _sr_buy:
                _sr_level = max(_sr_buy)
                reasons.append(f"✅ DT SRサポート反発({_sr_level:.3f})")
            if _at_ch_lower:
                score += 0.5
                reasons.append(f"✅ DT チャネル下限反発({_ch_lower:.3f})")
            if ctx.ema9 > ctx.ema21:
                score += 0.5
                reasons.append("✅ EMA順列確認")
            tp = ctx.entry + ctx.atr7 * 2.0
            sl = ctx.entry - ctx.atr7 * 1.0

        # SELL (HTF bull → block)
        elif (_htf_agreement != "bull"
                and (_sr_sell or _at_ch_upper)
                and ctx.rsi > 55 and ctx.macdh < ctx.macdh_prev):
            signal = "SELL"
            score = 3.2
            if _sr_sell:
                _sr_level = min(_sr_sell)
                reasons.append(f"✅ DT SRレジスタンス反発({_sr_level:.3f})")
            if _at_ch_upper:
                score += 0.5
                reasons.append(f"✅ DT チャネル上限反発({_ch_upper:.3f})")
            if ctx.ema9 < ctx.ema21:
                score += 0.5
                reasons.append("✅ EMA逆順列確認")
            tp = ctx.entry - ctx.atr7 * 2.0
            sl = ctx.entry + ctx.atr7 * 1.0

        if signal is None:
            return None

        conf = int(min(75, 40 + score * 4))
        _meta_level = (_sr_level if "_sr_level" in locals()
                       else (_ch_lower if signal == "BUY" else _ch_upper))
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score,
                         sr_meta=Candidate.sr_meta_from_price(
                             _sr_weighted, _meta_level, ctx.entry, ctx.atr))

    def _evaluate_redesign_v2(self, ctx: SignalContext) -> Optional[Candidate]:
        if ctx.df is None or len(ctx.df) < 21:
            return None

        signal_df = ctx.df.iloc[:-1]
        signal_bar = ctx.df.iloc[-2]
        prev_signal_bar = ctx.df.iloc[-3]
        signal_bar_time = getattr(signal_bar, "name", None)
        signal_price = float(signal_bar["Close"])
        signal_atr = float(signal_bar.get("atr", ctx.atr))
        signal_atr7 = float(signal_bar.get("atr7", signal_atr))
        signal_rsi = float(signal_bar.get("rsi", ctx.rsi))
        signal_macdh = float(signal_bar.get("macd_hist", ctx.macdh))
        signal_macdh_prev = float(prev_signal_bar.get("macd_hist", ctx.macdh_prev))
        signal_ema9 = float(signal_bar.get("ema9", ctx.ema9))
        signal_ema21 = float(signal_bar.get("ema21", ctx.ema21))

        _htf = ctx.htf or {}
        _htf_agreement = _htf.get("agreement", "mixed")

        _ch = self._channel(signal_df)
        _ch_upper = float(_ch["upper"][-1]["value"]) if _ch else None
        _ch_lower = float(_ch["lower"][-1]["value"]) if _ch else None
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

        if (_htf_agreement != "bear"
                and (_sr_buy or _at_ch_lower)
                and signal_rsi < 45 and signal_macdh > signal_macdh_prev):
            signal = "BUY"
            score = 3.2
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
                _sr_level = max(_sr_buy)
                reasons.append(f"✅ DT SRサポート反発(closed {_sr_level:.3f})")
            if _at_ch_lower:
                score += 0.5
                reasons.append(f"✅ DT チャネル下限反発(closed {_ch_lower:.3f})")
            if signal_ema9 > signal_ema21:
                score += 0.5
                reasons.append("✅ EMA順列確認(closed)")

        elif (_htf_agreement != "bull"
                and (_sr_sell or _at_ch_upper)
                and signal_rsi > 55 and signal_macdh < signal_macdh_prev):
            signal = "SELL"
            score = 3.2
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
                _sr_level = min(_sr_sell)
                reasons.append(f"✅ DT SRレジスタンス反発(closed {_sr_level:.3f})")
            if _at_ch_upper:
                score += 0.5
                reasons.append(f"✅ DT チャネル上限反発(closed {_ch_upper:.3f})")
            if signal_ema9 < signal_ema21:
                score += 0.5
                reasons.append("✅ EMA逆順列確認(closed)")

        if signal is None:
            return None

        if not ctx.backtest_mode:
            _sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
            _key = (_sym, self.name, str(signal_bar_time), signal)
            if _key in self._v2_seen_closed_bar_keys:
                return None
            self._v2_seen_closed_bar_keys.add(_key)

        reasons.append(
            f"✅ DT_SR_CHANNEL_REDESIGN_V2: closed_bar_time={signal_bar_time} "
            "で確定し次バー約定"
        )
        reasons.append(
            f"✅ MR geometry: boundary_outside_SL={sl:.5f} mean_side_TP={tp:.5f} "
            f"ATR7={signal_atr7:.5f}"
        )

        conf = int(min(75, 40 + score * 4))
        _meta_level = (_sr_level if "_sr_level" in locals()
                       else (_ch_lower if signal == "BUY" else _ch_upper))
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score,
                         sr_meta=Candidate.sr_meta_from_price(
                             _sr_weighted, _meta_level, signal_price, signal_atr))
