"""
MACD + RSI Pullback (USD_JPY 1H 専用ライブ)

bb_rsi_reversion (PAIR_DEMOTED, 全 cell -EV 確認済み) の trend-following 後継戦略.
TV Strategy Tester (USD_JPY 1H, 3.5y, OANDA friction 2.14p RT) で +EV 確認.

ロジック (TV Pine `macd_rsi_pullback-replica.pine` を Python に翻訳):
  - Base TF: 1H (ctx.df 15m を 1H にリサンプル → 最新 closed bar で判定)
  - H1 RSI bias gate: BUY >= 60, SELL <= 40
  - 1H RSI pullback (prev bar): BUY 30-55 / SELL 45-70
  - MACD hist_dir: hist > 0 BUY / hist < 0 SELL  (state filter, not event)
  - Pullback resumption: rsi > rsi_prev BUY / rsi < rsi_prev SELL
  - Session: London + NY (UTC 7-22)
  - Confirmation candle: 1H bar close > open BUY / close < open SELL
  - SL = ATR(14,1H) * 1.0, TP = ATR(14,1H) * 2.0  (RR=2.0, BEV_WR=33.3%)

TV BT (USD_JPY 1H, 2023-01-02 → 2026-05-14, OANDA friction baked in):
  | Config (H1 RSI) | N | WR | PF | Net | MaxDD |
  |---|---|---|---|---|---|
  | Loose 55/45 | 708 | 36.72% | 1.007 | +0.06% | 0.74% |
  | Canonical 60/40 | 196 | 39.29% | 1.161 | +0.36% | 0.39% |
  | High-conviction 65/35 | 58 | 43.10% | 1.327 | +0.21% | 0.18% |

Cross-pair (canonical config, all -EV):
  EUR_USD: N=199 WR=32.16% PF=0.761
  GBP_USD: N=178 WR=35.39% PF=0.974
  EUR_JPY: N=157 WR=29.94% PF=0.774
  → USD_JPY-specific edge. _enabled_symbols = ("USDJPY",).

なぜ Python BT を走らせず Live 適用するか:
  - user feedback memory `feedback_tv_edge_discovery_loop` で
    "TV BT を canonical, Python BT は乖離時のみ疑う" と確認済み.
  - TV 3.5y BT は Python BT 365 日相当の根拠.
  - SCALP_SENTINEL (Shadow 最小ロット) で開始, Live N≥30 で gate 再判定.

詳細: knowledge-base/wiki/analyses/macd-rsi-pullback-h1-audit-2026-05-14.md
"""
from __future__ import annotations

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional, Tuple


class MacdRsiPullback(StrategyBase):
    name = "macd_rsi_pullback"
    mode = "daytrade"
    enabled = True
    strategy_type = "pullback"

    # pair scope: USD_JPY 専用 (TV cross-pair で他ペア全て -EV)
    _enabled_symbols = ("USDJPY",)

    # H1 RSI directional gate (TV canonical 60/40)
    H1_RSI_BUY_MIN  = 60.0
    H1_RSI_SELL_MAX = 40.0

    # 1H RSI pullback bands (prev closed bar value)
    PB_BUY_LOW   = 30.0
    PB_BUY_HIGH  = 55.0
    PB_SELL_LOW  = 45.0
    PB_SELL_HIGH = 70.0

    # MACD params (TV defaults)
    MACD_FAST   = 12
    MACD_SLOW   = 26
    MACD_SIGNAL = 9

    # Risk
    SL_ATR_MULT = 1.0
    TP_ATR_MULT = 2.0
    ATR_LEN     = 14

    # Session (UTC) — London + NY
    SESS_START_HOUR = 7
    SESS_END_HOUR   = 22

    # 1H bars needed for MACD(12,26,9) stability (~ 26+9 + buffer)
    MIN_H1_BARS = 50
    # 15m bars to cover MIN_H1_BARS × 4 + buffer
    MIN_15M_BARS = 220

    # ──────────────────────────────────────────────────
    # Resample / indicator helpers
    # ──────────────────────────────────────────────────

    def _resample_h1(self, df):
        """ctx.df (15m) を 1H にリサンプル. 進行中 15m bar は除外 (look-ahead 防止)."""
        try:
            from modules.data import resample_df
            if df is None or len(df) < self.MIN_15M_BARS:
                return None
            df_past = df.iloc[:-1]
            if len(df_past) < self.MIN_15M_BARS:
                return None
            df_h1 = resample_df(df_past, "1h")
            if df_h1 is None or len(df_h1) < self.MIN_H1_BARS:
                return None
            return df_h1
        except Exception:
            return None

    def _calc_indicators(self, df_h1) -> Optional[Tuple[float, ...]]:
        """1H closed-bar indicators.

        Returns (rsi_now, rsi_prev, hist_now, atr_now,
                 open_now, close_now, bull_bar, bear_bar) or None.
        """
        try:
            from ta.momentum import RSIIndicator
            from ta.trend import MACD
            from ta.volatility import AverageTrueRange
            close = df_h1["Close"]
            high  = df_h1["High"]
            low   = df_h1["Low"]
            open_ = df_h1["Open"]

            rsi = RSIIndicator(close, window=14).rsi()
            macd_obj = MACD(close,
                            window_slow=self.MACD_SLOW,
                            window_fast=self.MACD_FAST,
                            window_sign=self.MACD_SIGNAL)
            hist = macd_obj.macd_diff()
            atr = AverageTrueRange(high=high, low=low, close=close,
                                   window=self.ATR_LEN).average_true_range()

            rsi_now = rsi.iloc[-1]
            rsi_prev = rsi.iloc[-2]
            hist_now = hist.iloc[-1]
            atr_now = atr.iloc[-1]

            # NaN / invalid guards
            if rsi_now != rsi_now or rsi_prev != rsi_prev:
                return None
            if hist_now != hist_now:
                return None
            if atr_now != atr_now or atr_now <= 0:
                return None

            o = float(open_.iloc[-1])
            c = float(close.iloc[-1])
            bull = c > o
            bear = c < o

            return (
                float(rsi_now), float(rsi_prev), float(hist_now), float(atr_now),
                o, c, bull, bear,
            )
        except Exception:
            return None

    # ──────────────────────────────────────────────────
    # Main
    # ──────────────────────────────────────────────────

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        _sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        if _sym not in self._enabled_symbols:
            return None

        if ctx.df is None or len(ctx.df) < self.MIN_15M_BARS:
            return None
        if ctx.atr <= 0:
            return None

        df_h1 = self._resample_h1(ctx.df)
        if df_h1 is None:
            return None

        ind = self._calc_indicators(df_h1)
        if ind is None:
            return None
        (rsi_now, rsi_prev, hist_now, atr_h1,
         open_h1, close_h1, bull_bar, bear_bar) = ind

        # H1 RSI bias gate (Pine: in_bull / in_bear)
        in_bull = rsi_now >= self.H1_RSI_BUY_MIN
        in_bear = rsi_now <= self.H1_RSI_SELL_MAX
        if not (in_bull or in_bear):
            return None

        # Pullback prev-bar window (Pine: buy_pullback / sell_pullback)
        buy_pullback  = self.PB_BUY_LOW  <= rsi_prev <= self.PB_BUY_HIGH
        sell_pullback = self.PB_SELL_LOW <= rsi_prev <= self.PB_SELL_HIGH

        # MACD state filter (Pine: hist_dir mode)
        macd_buy_state  = hist_now > 0
        macd_sell_state = hist_now < 0

        # Pullback resumption (Pine: rsi_resume_buy / rsi_resume_sell)
        rsi_resume_buy  = rsi_now > rsi_prev
        rsi_resume_sell = rsi_now < rsi_prev

        # Session gate (Pine: in_session = hour in [7,22))
        bar_time = ctx.bar_time
        if bar_time is None and ctx.df is not None and len(ctx.df) > 0:
            bar_time = ctx.df.index[-1]
        if bar_time is not None:
            try:
                _h = bar_time.hour if hasattr(bar_time, "hour") else int(str(bar_time)[11:13])
                if _h < self.SESS_START_HOUR or _h >= self.SESS_END_HOUR:
                    return None
            except (ValueError, IndexError):
                pass

        # Direction
        signal = None
        if in_bull and buy_pullback and macd_buy_state and rsi_resume_buy and bull_bar:
            signal = "BUY"
        elif in_bear and sell_pullback and macd_sell_state and rsi_resume_sell and bear_bar:
            signal = "SELL"
        else:
            return None

        # SL/TP from H1 ATR (TV parity), applied at ctx.entry (15m fill price)
        _sl_dist = atr_h1 * self.SL_ATR_MULT
        _tp_dist = atr_h1 * self.TP_ATR_MULT
        if signal == "BUY":
            sl = ctx.entry - _sl_dist
            tp = ctx.entry + _tp_dist
        else:
            sl = ctx.entry + _sl_dist
            tp = ctx.entry - _tp_dist
        if abs(ctx.entry - sl) <= 0:
            return None

        _dec = 3 if ctx.is_jpy or ctx.pip_mult == 100 else 5

        # Score
        score = 4.0
        reasons = []
        rsi_strength = abs(rsi_now - 50.0)
        score += min(1.0, rsi_strength / 20.0)
        reasons.append(
            f"{signal} macd_rsi_pullback (1H): rsi_h1={rsi_now:.1f} "
            f"({'>=' + str(int(self.H1_RSI_BUY_MIN)) if signal == 'BUY' else '<=' + str(int(self.H1_RSI_SELL_MAX))})"
        )
        reasons.append(
            f"Pullback prev RSI={rsi_prev:.1f} in "
            f"[{int(self.PB_BUY_LOW if signal == 'BUY' else self.PB_SELL_LOW)},"
            f"{int(self.PB_BUY_HIGH if signal == 'BUY' else self.PB_SELL_HIGH)}]"
        )
        reasons.append(f"MACD hist={hist_now:+.4f} ({'>0 BUY' if signal == 'BUY' else '<0 SELL'})")
        reasons.append(
            f"RSI resumption: now {rsi_now:.1f} "
            f"{'>' if signal == 'BUY' else '<'} prev {rsi_prev:.1f}"
        )
        reasons.append(
            f"H1 bar {'bull' if bull_bar else 'bear'} "
            f"(close={close_h1:.{_dec}f} {'>' if bull_bar else '<'} open={open_h1:.{_dec}f})"
        )
        reasons.append(
            f"ATR(14,H1)={atr_h1:.{_dec}f} "
            f"SL=ATR*{self.SL_ATR_MULT} TP=ATR*{self.TP_ATR_MULT}"
        )
        reasons.append(f"RR=2.0 SL={sl:.{_dec}f} TP={tp:.{_dec}f}")

        # Deep H1 RSI bonus (high-conviction subset territory in TV BT)
        if signal == "BUY" and rsi_now >= 65:
            score += 0.3
            reasons.append(f"H1 RSI deep bull ({rsi_now:.1f}>=65)")
        elif signal == "SELL" and rsi_now <= 35:
            score += 0.3
            reasons.append(f"H1 RSI deep bear ({rsi_now:.1f}<=35)")

        # HTF agreement bonus
        _htf = ctx.htf or {}
        _agr = _htf.get("agreement", "mixed")
        if (signal == "BUY" and _agr == "bull") or (signal == "SELL" and _agr == "bear"):
            score += 0.5
            reasons.append(f"HTF alignment ({_agr})")

        conf = int(min(85, 50 + score * 4))
        return Candidate(
            signal=signal, confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score,
        )
