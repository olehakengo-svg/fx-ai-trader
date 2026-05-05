"""
Gold Pips Hunter — XAU/USD 1分足クイック順張り (5分足方向同期)

概要:
  5分足レベルのトレンド方向を判定し、1分足で「包み足」パターンが
  出現した瞬間にトレンド方向へクイックエントリー。
  ゴールドの爆発的なモメンタムを利益に変える。

学術的根拠:
  - Engulfing reversal: Nison (1991, "Japanese Candlestick Charting") — 信頼度76%
  - Multi-TF momentum: Jegadeesh & Titman (1993) — 短期モメンタム持続性
  - Gold volatility: Baur & Lucey (2010) — XAU/USD独自のボラ特性

エントリー:
  BUY:  5m方向=UP (5本平均のClose > Open) + 1m包み足(陽線包み)
        + ADX>=18 + Close > EMA21
  SELL: 5m方向=DOWN (5本平均のClose < Open) + 1m包み足(陰線包み)
        + ADX>=18 + Close < EMA21

決済:
  TP: ATR7 × 1.8 (ゴールドのモメンタム活用)
  SL: 包み足のLow/High ± ATR7×0.2
"""
import os
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class GoldPipsHunter(StrategyBase):
    name = "gold_pips_hunter"
    mode = "scalp"
    enabled = True

    # ── パラメータ ──
    adx_min = 18
    tp_mult = 1.8
    sl_buffer = 0.2      # ATR7倍率 SLバッファ
    min_body_atr = 0.3   # 包み足の最小ボディ(ATR7倍率)

    # XAU/USD のみ
    _enabled_symbols = frozenset({"XAUUSD"})

    # ── セッションフィルター (2026-04-06 Session Matrix BT) ──
    # Tokyo PF=1.57(28t) ✅, NY Overlap PF=0.53(17t) ❌, NY Late PF=0.61(12t) ❌
    # → Tokyo+London限定 (UTC 0-12)
    _active_hours = frozenset(range(0, 12))

    _dedup_state: dict = {}

    @classmethod
    def reset_dedup_state(cls):
        cls._dedup_state.clear()

    def _redesign_v2_enabled(self) -> bool:
        return os.environ.get("GOLD_PIPS_REDESIGN_V2") == "1"

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if self._redesign_v2_enabled():
            return self._evaluate_redesign_v2(ctx)

        # ── XAU/USDフィルター ──
        _sym = ctx.symbol.upper().replace("=X", "").replace("_", "")
        if _sym not in self._enabled_symbols:
            return None

        # ── セッションフィルター: NY時間帯は壊滅的 (PF<0.7) ──
        if ctx.hour_utc not in self._active_hours:
            return None

        if ctx.df is None or len(ctx.df) < 10:
            return None

        if ctx.adx < self.adx_min:
            return None

        if ctx.atr7 <= 0:
            return None

        # ── 5分足方向判定（1m足×5本で代替）──
        _last5 = ctx.df.iloc[-6:-1]  # 直前5本（現在足除く）
        if len(_last5) < 5:
            return None

        _5m_close_avg = float(_last5["Close"].mean())
        _5m_open_avg = float(_last5["Open"].mean())
        _5m_dir = "UP" if _5m_close_avg > _5m_open_avg else "DOWN"

        # 5m方向の強さ（連続性）
        _5m_bull_count = sum(1 for _, r in _last5.iterrows()
                            if float(r["Close"]) > float(r["Open"]))
        _5m_dir_strength = _5m_bull_count if _5m_dir == "UP" else (5 - _5m_bull_count)

        if _5m_dir_strength < 3:  # 5本中3本以上が方向一致
            return None

        # ── 1分足包み足判定 ──
        _cur_body = ctx.entry - ctx.open_price  # 正=陽線, 負=陰線
        _cur_body_abs = abs(_cur_body)
        _prev_body = ctx.prev_close - ctx.prev_open
        _prev_body_abs = abs(_prev_body)

        # 包み足条件: 現在足のボディが前足のボディを完全に包む
        _is_engulfing = (_cur_body_abs > _prev_body_abs
                         and _cur_body_abs >= ctx.atr7 * self.min_body_atr)

        if not _is_engulfing:
            return None

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0
        _min_sl = 0.030  # XAU/USD (JPYスケール: pip=0.01)

        _row = ctx.df.iloc[-1]
        _cur_high = float(_row["High"])
        _cur_low = float(_row["Low"])

        # ── BUY: 5m UP + 陽線包み足 + EMA21上 ──
        if (_5m_dir == "UP" and _cur_body > 0
                and ctx.entry > ctx.ema21):
            signal = "BUY"
            score = 3.5
            reasons.append(f"✅ 5m方向=UP({_5m_bull_count}/5陽線) — トレンド同期")
            reasons.append(f"✅ 1m陽線包み足(body={_cur_body_abs:.2f}>{_prev_body_abs:.2f})")
            reasons.append(f"✅ EMA21上(C={ctx.entry:.2f}>EMA21={ctx.ema21:.2f})")

            tp = ctx.entry + ctx.atr7 * self.tp_mult
            sl = _cur_low - ctx.atr7 * self.sl_buffer
            sl = min(sl, ctx.entry - _min_sl)

        # ── SELL: 5m DOWN + 陰線包み足 + EMA21下 ──
        elif (_5m_dir == "DOWN" and _cur_body < 0
              and ctx.entry < ctx.ema21):
            signal = "SELL"
            score = 3.5
            reasons.append(f"✅ 5m方向=DOWN({5 - _5m_bull_count}/5陰線) — トレンド同期")
            reasons.append(f"✅ 1m陰線包み足(body={_cur_body_abs:.2f}>{_prev_body_abs:.2f})")
            reasons.append(f"✅ EMA21下(C={ctx.entry:.2f}<EMA21={ctx.ema21:.2f})")

            tp = ctx.entry - ctx.atr7 * self.tp_mult
            sl = _cur_high + ctx.atr7 * self.sl_buffer
            sl = max(sl, ctx.entry + _min_sl)

        if signal is None:
            return None

        # ── スコアボーナス ──
        # ADX強度
        if ctx.adx >= 30:
            score += 0.6
            reasons.append(f"✅ ADX強トレンド({ctx.adx:.1f}≥30)")
        elif ctx.adx >= 25:
            score += 0.3

        # EMA9-21スプレッド
        _ema_spread = abs(ctx.ema9 - ctx.ema21) / ctx.atr7
        if _ema_spread >= 0.5:
            score += 0.3
            reasons.append(f"✅ EMAスプレッド良好({_ema_spread:.2f}ATR)")

        # MACD方向一致
        if signal == "BUY" and ctx.macdh > 0:
            score += 0.2
        elif signal == "SELL" and ctx.macdh < 0:
            score += 0.2

        # DI方向一致
        if signal == "BUY" and ctx.adx_pos > ctx.adx_neg:
            score += 0.3
            reasons.append(f"✅ DI方向一致(+DI={ctx.adx_pos:.1f}>-DI={ctx.adx_neg:.1f})")
        elif signal == "SELL" and ctx.adx_neg > ctx.adx_pos:
            score += 0.3
            reasons.append(f"✅ DI方向一致(-DI={ctx.adx_neg:.1f}>+DI={ctx.adx_pos:.1f})")

        conf = int(min(85, 50 + score * 4))

        return Candidate(
            signal=signal, confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score,
        )

    def _bar_id(self, ctx: SignalContext, signal_df, signal_idx: int):
        if hasattr(signal_df, "index") and len(signal_df.index) > abs(signal_idx):
            return signal_df.index[signal_idx]
        return ctx.bar_time

    def _dedup_seen(self, ctx: SignalContext, signal: str, bar_id) -> bool:
        key = (ctx.symbol.upper().replace("=X", "").replace("_", ""), signal, bar_id)
        if key in self._dedup_state:
            return True
        self._dedup_state[key] = True
        return False

    def _evaluate_redesign_v2(self, ctx: SignalContext) -> Optional[Candidate]:
        """V2 shadow-first variant: closed signal bar, next-bar execution, RR guard."""
        # ── XAU/USDフィルター ──
        _sym = ctx.symbol.upper().replace("=X", "").replace("_", "")
        if _sym not in self._enabled_symbols:
            return None

        # ── セッションフィルター: NY時間帯は壊滅的 (PF<0.7) ──
        if ctx.hour_utc not in self._active_hours:
            return None

        if ctx.df is None or len(ctx.df) < 10:
            return None

        # V2: signal は確定足 df[-2]、execution は ctx.entry に限定する。
        signal_bar = ctx.df.iloc[-2]
        prev_bar = ctx.df.iloc[-3]
        signal_bar_time = self._bar_id(ctx, ctx.df, -2)

        atr7 = float(signal_bar.get("atr7", signal_bar.get("atr", ctx.atr7)))
        if atr7 <= 0:
            return None

        adx = float(signal_bar.get("adx", ctx.adx))
        if adx < self.adx_min:
            return None

        # ── 5分足方向判定（signal bar 直前5本、signal bar自身は除外）──
        _last5 = ctx.df.iloc[-7:-2]
        if len(_last5) < 5:
            return None

        _5m_close_avg = float(_last5["Close"].mean())
        _5m_open_avg = float(_last5["Open"].mean())
        _5m_dir = "UP" if _5m_close_avg > _5m_open_avg else "DOWN"

        _5m_bull_count = sum(1 for _, r in _last5.iterrows()
                            if float(r["Close"]) > float(r["Open"]))
        _5m_dir_strength = _5m_bull_count if _5m_dir == "UP" else (5 - _5m_bull_count)
        if _5m_dir_strength < 3:
            return None

        sig_open = float(signal_bar["Open"])
        sig_close = float(signal_bar["Close"])
        sig_high = float(signal_bar["High"])
        sig_low = float(signal_bar["Low"])
        prev_open = float(prev_bar["Open"])
        prev_close = float(prev_bar["Close"])

        _sig_body = sig_close - sig_open
        _sig_body_abs = abs(_sig_body)
        _prev_body = prev_close - prev_open
        _prev_body_abs = abs(_prev_body)

        _is_engulfing = (
            _sig_body_abs > _prev_body_abs
            and _sig_body_abs >= atr7 * self.min_body_atr
        )
        if not _is_engulfing:
            return None

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0
        _min_sl = 0.030

        ema21 = float(signal_bar.get("ema21", ctx.ema21))
        entry = ctx.entry

        if (_5m_dir == "UP" and _sig_body > 0
                and entry > ema21):
            signal = "BUY"
            score = 3.5
            reasons.append(
                f"✅ GOLD_PIPS_REDESIGN_V2 closed-bar signal={signal_bar_time} "
                f"5m方向=UP({_5m_bull_count}/5陽線)"
            )
            reasons.append(f"✅ closed 1m陽線包み足(body={_sig_body_abs:.2f}>{_prev_body_abs:.2f})")
            reasons.append(f"✅ next-bar entry EMA21上(C={entry:.2f}>EMA21={ema21:.2f})")

            sl = sig_low - atr7 * self.sl_buffer
            sl = min(sl, entry - _min_sl)
            risk = entry - sl
            tp_distance = atr7 * self.tp_mult
            if risk <= 0 or tp_distance < 1.5 * risk:
                return None
            tp = entry + tp_distance

        elif (_5m_dir == "DOWN" and _sig_body < 0
              and entry < ema21):
            signal = "SELL"
            score = 3.5
            reasons.append(
                f"✅ GOLD_PIPS_REDESIGN_V2 closed-bar signal={signal_bar_time} "
                f"5m方向=DOWN({5 - _5m_bull_count}/5陰線)"
            )
            reasons.append(f"✅ closed 1m陰線包み足(body={_sig_body_abs:.2f}>{_prev_body_abs:.2f})")
            reasons.append(f"✅ next-bar entry EMA21下(C={entry:.2f}<EMA21={ema21:.2f})")

            sl = sig_high + atr7 * self.sl_buffer
            sl = max(sl, entry + _min_sl)
            risk = sl - entry
            tp_distance = atr7 * self.tp_mult
            if risk <= 0 or tp_distance < 1.5 * risk:
                return None
            tp = entry - tp_distance

        if signal is None:
            return None

        if self._dedup_seen(ctx, signal, signal_bar_time):
            return None

        if adx >= 30:
            score += 0.6
            reasons.append(f"✅ closed-bar ADX強トレンド({adx:.1f}≥30)")
        elif adx >= 25:
            score += 0.3

        ema9 = float(signal_bar.get("ema9", ctx.ema9))
        _ema_spread = abs(ema9 - ema21) / atr7
        if _ema_spread >= 0.5:
            score += 0.3
            reasons.append(f"✅ closed-bar EMAスプレッド良好({_ema_spread:.2f}ATR)")

        macdh = float(signal_bar.get("macd_hist", ctx.macdh))
        if signal == "BUY" and macdh > 0:
            score += 0.2
        elif signal == "SELL" and macdh < 0:
            score += 0.2

        adx_pos = float(signal_bar.get("adx_pos", ctx.adx_pos))
        adx_neg = float(signal_bar.get("adx_neg", ctx.adx_neg))
        if signal == "BUY" and adx_pos > adx_neg:
            score += 0.3
            reasons.append(f"✅ closed-bar DI方向一致(+DI={adx_pos:.1f}>-DI={adx_neg:.1f})")
        elif signal == "SELL" and adx_neg > adx_pos:
            score += 0.3
            reasons.append(f"✅ closed-bar DI方向一致(-DI={adx_neg:.1f}>+DI={adx_pos:.1f})")

        conf = int(min(85, 50 + score * 4))
        return Candidate(
            signal=signal, confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score,
        )
