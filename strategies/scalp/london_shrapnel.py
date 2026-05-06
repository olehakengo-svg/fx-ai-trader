"""
London Shrapnel — ロンドン/NY重なり時間帯の異常ヒゲ反転スキャルプ

概要:
  London/NY overlap (UTC 12-17) に発生する異常なヒゲ（ATR×1.5以上）を
  ストップハント＝偽ブレイクアウトと解釈し、ヒゲの反対方向へ即座に逆張り。
  EUR/USD, GBP/USD 専用 — 流動性最大の時間帯で効果的。

学術的根拠:
  - Stop-run reversal: Osler (2005, RFS) — ストップロスクラスタ貫通後の反転
  - Wick rejection: Bulkowski (2005) — 長いヒゲは反転の前兆 (75%+)
  - London/NY overlap: King et al. (2012, BIS) — FX出来高の60%が集中

エントリー:
  BUY:  下ヒゲ ≥ ATR7×1.5 AND 下ヒゲ/ボディ ≥ 3.0 AND Close > BB_lower
        AND RSI5 < 40 (売られ過ぎ圏からの反発)
  SELL: 上ヒゲ ≥ ATR7×1.5 AND 上ヒゲ/ボディ ≥ 3.0 AND Close < BB_upper
        AND RSI5 > 60 (買われ過ぎ圏からの反落)

決済:
  TP: ATR7 × 0.8 (超高速: BB中央方向への即リバ)
  SL: ヒゲ先端 + ATR7 × 0.2 (ヒゲ再突破 = 本物のブレイク)
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
import os
from typing import Optional


class LondonShrapnel(StrategyBase):
    name = "london_shrapnel"
    mode = "scalp"
    enabled = True

    # ── パラメータ ──
    wick_atr_min = 1.5       # 最小ヒゲ長(ATR7倍率)
    wick_body_ratio = 3.0    # ヒゲ/ボディ比の最低値
    rsi_buy_max = 40         # BUY時RSI上限
    rsi_sell_min = 60        # SELL時RSI下限
    tp_mult = 0.8            # 超高速TP
    sl_buffer = 0.2          # SLバッファ(ATR7倍率)

    # 対象ペア
    _enabled_symbols = frozenset({"EURUSD", "GBPUSD"})
    # 稼働時間 (London/NY overlap)
    _active_hours = frozenset(range(12, 18))
    _dedup_seen: set[tuple[str, object, str]] = set()

    @classmethod
    def reset_dedup_state(cls):
        cls._dedup_seen.clear()

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── ペアフィルター ──
        _sym = ctx.symbol.upper().replace("=X", "").replace("_", "")
        if _sym not in self._enabled_symbols:
            return None

        # ── 時間帯フィルター: London/NY overlap のみ ──
        if ctx.hour_utc not in self._active_hours:
            return None

        if ctx.atr7 <= 0:
            return None

        if os.environ.get("LONDON_SHRAPNEL_REDESIGN_V2") == "1":
            return self._evaluate_redesign_v2(ctx, _sym)

        # ── ヒゲ計算 ──
        _body = abs(ctx.entry - ctx.open_price)
        _body = max(_body, ctx.atr7 * 0.01)  # ゼロ除算防止

        _high = ctx.prev_high if ctx.df is None else float(ctx.df["High"].iloc[-1])
        _low = ctx.prev_low if ctx.df is None else float(ctx.df["Low"].iloc[-1])
        # 現在足のHigh/Lowを使用
        if ctx.df is not None and len(ctx.df) >= 1:
            _row = ctx.df.iloc[-1]
            _high = float(_row["High"])
            _low = float(_row["Low"])

        _upper_wick = _high - max(ctx.entry, ctx.open_price)
        _lower_wick = min(ctx.entry, ctx.open_price) - _low

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0
        _min_sl = 0.00030  # EUR/GBP pairs

        # ── BUY: 巨大下ヒゲ (Pin Bar / Hammer) ──
        if (_lower_wick >= ctx.atr7 * self.wick_atr_min
                and _lower_wick / _body >= self.wick_body_ratio
                and ctx.entry > ctx.open_price       # 陽線（反転確認）
                and ctx.entry > ctx.bb_lower          # BBロワー突破からの回帰
                and ctx.rsi5 < self.rsi_buy_max):
            signal = "BUY"
            score = 4.0
            _wick_atr = round(_lower_wick / ctx.atr7, 1)
            _wick_body = round(_lower_wick / _body, 1)
            reasons.append(f"✅ 巨大下ヒゲ(={_wick_atr}ATR≥{self.wick_atr_min}) — ストップハント反転")
            reasons.append(f"✅ ヒゲ/ボディ比={_wick_body}x≥{self.wick_body_ratio}x — Pin Bar")
            reasons.append(f"✅ RSI5過売圏({ctx.rsi5:.1f}<{self.rsi_buy_max}) + 陽線反転")

            tp = ctx.entry + ctx.atr7 * self.tp_mult
            sl = _low - ctx.atr7 * self.sl_buffer
            sl = min(sl, ctx.entry - _min_sl)

        # ── SELL: 巨大上ヒゲ (Shooting Star) ──
        elif (_upper_wick >= ctx.atr7 * self.wick_atr_min
              and _upper_wick / _body >= self.wick_body_ratio
              and ctx.entry < ctx.open_price          # 陰線（反転確認）
              and ctx.entry < ctx.bb_upper             # BBアッパー突破からの回帰
              and ctx.rsi5 > self.rsi_sell_min):
            signal = "SELL"
            score = 4.0
            _wick_atr = round(_upper_wick / ctx.atr7, 1)
            _wick_body = round(_upper_wick / _body, 1)
            reasons.append(f"✅ 巨大上ヒゲ(={_wick_atr}ATR≥{self.wick_atr_min}) — ストップハント反転")
            reasons.append(f"✅ ヒゲ/ボディ比={_wick_body}x≥{self.wick_body_ratio}x — Shooting Star")
            reasons.append(f"✅ RSI5過買圏({ctx.rsi5:.1f}>{self.rsi_sell_min}) + 陰線反転")

            tp = ctx.entry - ctx.atr7 * self.tp_mult
            sl = _high + ctx.atr7 * self.sl_buffer
            sl = max(sl, ctx.entry + _min_sl)

        if signal is None:
            return None

        # ── スコアボーナス ──
        # BB距離ボーナス（BB端に近いほど高確率反転）
        if signal == "BUY" and ctx.bbpb < 0.15:
            score += 0.5
            reasons.append(f"✅ BB極端圏(%B={ctx.bbpb:.2f}<0.15) +0.5")
        elif signal == "SELL" and ctx.bbpb > 0.85:
            score += 0.5
            reasons.append(f"✅ BB極端圏(%B={ctx.bbpb:.2f}>0.85) +0.5")

        # Stoch確認
        if signal == "BUY" and ctx.stoch_k < 30 and ctx.stoch_k > ctx.stoch_d:
            score += 0.3
        elif signal == "SELL" and ctx.stoch_k > 70 and ctx.stoch_k < ctx.stoch_d:
            score += 0.3

        # MACD方向転換
        if signal == "BUY" and ctx.macdh > ctx.macdh_prev and ctx.macdh_prev < ctx.macdh_prev2:
            score += 0.3
            reasons.append("✅ MACD-H反転上昇")
        elif signal == "SELL" and ctx.macdh < ctx.macdh_prev and ctx.macdh_prev > ctx.macdh_prev2:
            score += 0.3
            reasons.append("✅ MACD-H反転下落")

        # GBP/USD ボラ特性ボーナス
        if "GBP" in _sym and ctx.adx >= 20:
            score += 0.3
            reasons.append(f"✅ GBPボラ環境(ADX={ctx.adx:.1f})")

        conf = int(min(85, 50 + score * 4))

        return Candidate(
            signal=signal, confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score,
        )

    def _evaluate_redesign_v2(self, ctx: SignalContext, sym: str) -> Optional[Candidate]:
        """V2: closed-bar stop sweep + reclaim instead of generic long-wick reversal."""
        if ctx.df is None or len(ctx.df) < 3:
            return None

        signal_row = ctx.df.iloc[-2]
        prior_row = ctx.df.iloc[-3]
        signal_time = ctx.df.index[-2] if hasattr(ctx.df, "index") else ctx.bar_time

        sig_open = float(signal_row["Open"])
        sig_close = float(signal_row["Close"])
        sig_high = float(signal_row["High"])
        sig_low = float(signal_row["Low"])
        prior_low = float(prior_row["Low"])
        prior_high = float(prior_row["High"])
        atr = float(signal_row.get("atr7", signal_row.get("atr", ctx.atr7)))
        if atr <= 0:
            return None

        bb_lower = float(signal_row.get("bb_lower", ctx.bb_lower))
        bb_mid = float(signal_row.get("bb_mid", ctx.bb_mid or sig_close))
        bb_upper = float(signal_row.get("bb_upper", ctx.bb_upper))
        rsi5 = float(signal_row.get("rsi5", ctx.rsi5))
        bbpb = float(signal_row.get("bb_pband", ctx.bbpb))

        body = max(abs(sig_close - sig_open), atr * 0.01)
        upper_wick = sig_high - max(sig_close, sig_open)
        lower_wick = min(sig_close, sig_open) - sig_low
        sweep_buffer = max(atr * 0.05, 0.00002)
        min_sl = 0.00030

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0
        liquidity_low = min(prior_low, bb_lower)
        liquidity_high = max(prior_high, bb_upper)

        if (lower_wick >= atr * self.wick_atr_min
                and lower_wick / body >= self.wick_body_ratio
                and sig_close > sig_open
                and sig_low < liquidity_low - sweep_buffer
                and sig_close > liquidity_low
                and rsi5 < self.rsi_buy_max):
            signal = "BUY"
            score = 4.0
            sl = min(sig_low - atr * self.sl_buffer, ctx.entry - min_sl)
            risk = max(ctx.entry - sl, min_sl)
            raw_tp = ctx.entry + atr * self.tp_mult
            rr_tp = ctx.entry + risk
            mid_tp = bb_mid if bb_mid > ctx.entry else raw_tp
            tp = min(raw_tp, rr_tp, mid_tp)
            reasons.append("✅ LONDON_SHRAPNEL_REDESIGN_V2 closed-bar lower sweep + reclaim")
            reasons.append(f"✅ sweep low {sig_low:.5f} < liquidity {liquidity_low:.5f}; close reclaimed {sig_close:.5f}")
            reasons.append(f"✅ lower wick={lower_wick / atr:.1f}ATR, wick/body={lower_wick / body:.1f}x, RSI5={rsi5:.1f}")

        elif (upper_wick >= atr * self.wick_atr_min
              and upper_wick / body >= self.wick_body_ratio
              and sig_close < sig_open
              and sig_high > liquidity_high + sweep_buffer
              and sig_close < liquidity_high
              and rsi5 > self.rsi_sell_min):
            signal = "SELL"
            score = 4.0
            sl = max(sig_high + atr * self.sl_buffer, ctx.entry + min_sl)
            risk = max(sl - ctx.entry, min_sl)
            raw_tp = ctx.entry - atr * self.tp_mult
            rr_tp = ctx.entry - risk
            mid_tp = bb_mid if bb_mid < ctx.entry else raw_tp
            tp = max(raw_tp, rr_tp, mid_tp)
            reasons.append("✅ LONDON_SHRAPNEL_REDESIGN_V2 closed-bar upper sweep + reclaim")
            reasons.append(f"✅ sweep high {sig_high:.5f} > liquidity {liquidity_high:.5f}; close reclaimed {sig_close:.5f}")
            reasons.append(f"✅ upper wick={upper_wick / atr:.1f}ATR, wick/body={upper_wick / body:.1f}x, RSI5={rsi5:.1f}")

        if signal is None:
            return None

        dedup_key = (sym, signal_time, signal)
        if dedup_key in self._dedup_seen:
            return None
        self._dedup_seen.add(dedup_key)

        if signal == "BUY" and bbpb < 0.15:
            score += 0.5
            reasons.append(f"✅ BB極端圏(%B={bbpb:.2f}<0.15) +0.5")
        elif signal == "SELL" and bbpb > 0.85:
            score += 0.5
            reasons.append(f"✅ BB極端圏(%B={bbpb:.2f}>0.85) +0.5")

        if "GBP" in sym and ctx.adx >= 20:
            score += 0.3
            reasons.append(f"✅ GBPボラ環境(ADX={ctx.adx:.1f})")

        conf = int(min(85, 50 + score * 4))
        return Candidate(
            signal=signal, confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score,
        )
