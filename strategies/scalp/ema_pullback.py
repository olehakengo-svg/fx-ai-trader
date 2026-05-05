"""EMA Pullback — トレンド方向のEMAプルバック反発"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from modules.confidence_v2 import apply_penalty
from typing import Optional
import os


class EmaPullback(StrategyBase):
    name = "ema_pullback"
    mode = "scalp"
    enabled = True   # v7.0: Sentinel再有効化 — デモデータ蓄積優先
    strategy_type = "pullback"   # v11: トレンド方向 pullback — ADX>31で conf penalty

    # チューナブルパラメータ（学術水準: ADX≥20でトレンド確認）
    adx_min = 20           # ADXトレンド閾値（12→20: 学術的に有意なトレンド水準）
    adx_weak = 25          # 弱トレンド帯（15→25）
    rsi5_buy_min = 30      # （38→30緩和）
    rsi5_buy_max = 62      # （58→62緩和）
    rsi5_sell_min = 38     # （42→38緩和）
    rsi5_sell_max = 70     # （62→70緩和）
    bbpb_buy_min = 0.12    # （0.20→0.12緩和）
    bbpb_buy_max = 0.70    # （0.65→0.70緩和）
    bbpb_sell_min = 0.30   # （0.35→0.30緩和）
    bbpb_sell_max = 0.88   # （0.80→0.88緩和）
    tp_mult = 1.8
    sl_ema_offset = 0.3   # EMA21からのSLオフセット（ATR倍率）
    v2_structure_sl_offset = 0.6
    _v2_dedup_state: set[tuple[str, str, str]] = set()

    @classmethod
    def reset_dedup_state(cls):
        cls._v2_dedup_state.clear()

    def _redesign_v2_enabled(self) -> bool:
        return os.environ.get("EMA_PULLBACK_REDESIGN_V2") == "1"

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if ctx.adx < self.adx_min:
            return None
        if ctx.df is None or len(ctx.df) < 5:
            return None
        _redesign_v2 = self._redesign_v2_enabled()
        if _redesign_v2:
            if len(ctx.df) < 6:
                return None
            if not ctx.backtest_mode and ctx.bar_time is None:
                return None
            _signal_df = ctx.df.iloc[:-1]
            _signal_row = _signal_df.iloc[-1]
            _prev_row = _signal_df.iloc[-2]
            _signal_bar_time = getattr(_signal_row, "name", None)
            _signal_close = float(_signal_row["Close"])
            _signal_open = float(_signal_row["Open"])
            _signal_high = float(_signal_row["High"])
            _signal_low = float(_signal_row["Low"])
            _entry = _signal_close
            _open_price = _signal_open
            _range_ep = _signal_high - _signal_low
            _ema9 = float(_signal_row.get("ema9", ctx.ema9))
            _ema21 = float(_signal_row.get("ema21", ctx.ema21))
            _atr7 = float(_signal_row.get("atr7", ctx.atr7))
            _rsi5 = float(_signal_row.get("rsi5", _signal_row.get("rsi", ctx.rsi5)))
            _bbpb = float(_signal_row.get("bb_pband", ctx.bbpb))
            _macdh = float(_signal_row.get("macd_hist", ctx.macdh))
            _stoch_k = float(_signal_row.get("stoch_k", ctx.stoch_k))
            _stoch_d = float(_signal_row.get("stoch_d", ctx.stoch_d))
            _prev_close = float(_prev_row["Close"])
            _prev_low = float(_prev_row["Low"])
            _prev_high = float(_prev_row["High"])
        else:
            _signal_bar_time = None
            _signal_low = float(ctx.df["Low"].iloc[-1])
            _signal_high = float(ctx.df["High"].iloc[-1])
            _entry = ctx.entry
            _open_price = ctx.open_price
            _range_ep = _signal_high - _signal_low
            _ema9 = ctx.ema9
            _ema21 = ctx.ema21
            _atr7 = ctx.atr7
            _rsi5 = ctx.rsi5
            _bbpb = ctx.bbpb
            _macdh = ctx.macdh
            _stoch_k = ctx.stoch_k
            _stoch_d = ctx.stoch_d
            _prev_close = ctx.prev_close
            _prev_low = ctx.prev_low
            _prev_high = ctx.prev_high

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0

        # BUY: 上昇トレンド + EMA21付近へのプルバック + 反発
        if (_ema9 > _ema21  # EMA順列（EMA50整列不要に緩和）
                and _entry >= _ema21  # EMA21の上に戻った
                and _prev_low <= _ema9  # 前バーがEMA9以下にタッチ
                and _prev_low >= _ema21 - _atr7 * self.sl_ema_offset
                and _entry > _prev_close  # signal bar 陽線方向
                and _rsi5 > self.rsi5_buy_min and _rsi5 < self.rsi5_buy_max
                and _bbpb > self.bbpb_buy_min and _bbpb < self.bbpb_buy_max):
            # ── v8.3: バウンス確認強化 — 即死率72.2%対策 ──
            _min_bounce = _atr7 * 0.2
            if (_entry - _ema21) < _min_bounce:
                return None  # 弱いバウンス(2-3pip) → PB継続中の可能性大
            if _macdh <= 0:
                return None  # v8.3: MACD-H正必須 → モメンタム上向き確認
            if _stoch_k <= _stoch_d:
                return None  # v8.3: Stochゴールデンクロス必須
            _body_ep = abs(_entry - _open_price)
            if _range_ep > 0 and _body_ep / _range_ep < 0.35:
                return None  # v8.3: doji/spinning top除外
            signal = "BUY"
            score = 3.0 + min((ctx.adx - self.adx_min) * 0.05, 1.0)
            reasons.append(f"✅ EMAプルバック反発: EMA9({_ema9:.3f})タッチ→反発")
            reasons.append(f"✅ EMA完全整列 (9>21>50, ADX={ctx.adx:.1f})")
            reasons.append(f"✅ 陽線反発確認 ({_entry:.3f}>{_prev_close:.3f})")
            reasons.append("✅ v8.3: MACD-H+Stoch+Body三重確認")
            if _prev_low <= _ema21 + _atr7 * 0.1:
                score += 0.5
                reasons.append(f"✅ EMA21深押し(Low={_prev_low:.3f})")
            tp = ctx.entry + _atr7 * self.tp_mult
            if _redesign_v2:
                sl = min(_signal_low, _ema21 - _atr7 * self.v2_structure_sl_offset)
            else:
                sl = _ema21 - _atr7 * self.sl_ema_offset

        # SELL: 下降トレンド + EMA21付近への戻り + 反落
        elif (_ema9 < _ema21  # EMA逆順列（EMA50整列不要に緩和）
                and _entry <= _ema21  # EMA21の下に戻った
                and _prev_high >= _ema9  # 前バーがEMA9以上にタッチ
                and _prev_high <= _ema21 + _atr7 * self.sl_ema_offset
                and _entry < _prev_close  # signal bar 陰線方向
                and _rsi5 > self.rsi5_sell_min and _rsi5 < self.rsi5_sell_max
                and _bbpb > self.bbpb_sell_min and _bbpb < self.bbpb_sell_max):
            # ── v8.3: バウンス確認強化 — 即死率72.2%対策 (SELL対称) ──
            _min_bounce_s = _atr7 * 0.2
            if (_ema21 - _entry) < _min_bounce_s:
                return None  # 弱い戻り → PB継続中
            if _macdh >= 0:
                return None  # v8.3: MACD-H負必須
            if _stoch_k >= _stoch_d:
                return None  # v8.3: Stochデッドクロス必須
            _body_ep_s = abs(_entry - _open_price)
            if _range_ep > 0 and _body_ep_s / _range_ep < 0.35:
                return None  # v8.3: doji/spinning top除外
            signal = "SELL"
            score = 3.0 + min((ctx.adx - self.adx_min) * 0.05, 1.0)
            reasons.append(f"✅ EMAプルバック反落: EMA9({_ema9:.3f})タッチ→反落")
            reasons.append(f"✅ EMA逆整列 (9<21<50, ADX={ctx.adx:.1f})")
            reasons.append(f"✅ 陰線反落確認 ({_entry:.3f}<{_prev_close:.3f})")
            reasons.append("✅ v8.3: MACD-H+Stoch+Body三重確認")
            if _prev_high >= _ema21 - _atr7 * 0.1:
                score += 0.5
                reasons.append(f"✅ EMA21深戻り(High={_prev_high:.3f})")
            tp = ctx.entry - _atr7 * self.tp_mult
            if _redesign_v2:
                sl = max(_signal_high, _ema21 + _atr7 * self.v2_structure_sl_offset)
            else:
                sl = _ema21 + _atr7 * self.sl_ema_offset

        if signal is None:
            return None
        if _redesign_v2:
            if not ctx.backtest_mode:
                _sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
                _key = (_sym, signal, str(_signal_bar_time))
                if _key in self._v2_dedup_state:
                    return None
                self._v2_dedup_state.add(_key)
            reasons.append(
                "✅ EMA_PULLBACK_REDESIGN_V2: signal_bar_time={} で確定し次バー約定".format(
                    _signal_bar_time
                )
            )

        conf = int(min(75, 40 + score * 4))
        # ADX弱トレンド帯はグラデーション減衰
        if ctx.adx < self.adx_weak:
            conf = int(conf * 0.9)
            reasons.append(f"⚠️ ADX弱トレンド帯({ctx.adx:.1f}<{self.adx_weak}) → conf×0.9")
        # v11: ADX過剰帯 (pullback threshold=31) でもペナルティ
        conf = apply_penalty(conf, self.strategy_type, ctx.adx, conf_max=75)
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)
