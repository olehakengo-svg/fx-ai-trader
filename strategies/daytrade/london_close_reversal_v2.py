"""
London Close Reversal v2 (LCR v2) — H-2026-04-22-005 検証版

学術的根拠:
  - Hau (2001) FX order flow and price impact
  - Ito & Hashimoto (2006) intraday FX seasonality
  - Melvin & Prins (2015) London fixing flow reversal

微細構造仮説:
  UTC 20:30-21:00 (ユーザー定義 London close 前30分) に日中トレンドの
  終値ポジション調整が集中し、過剰方向への短期push(>0.8ATR)が
  RSI極値(>68/<32)と同時発生した場合、反転エッジが生じる。

BT結果 (5m, 183日):
  - GBP_USD: N=25, WR=60.0%, PF=2.45, EV_R_fric=+0.52, Kelly_h=0.178 (Tier1△ N未達)
  - EUR_USD: N=37, WR=51.4%, PF=1.62, EV_R_fric=+0.22, Kelly_h=0.108 (Sentinel許可)
  - GBP_JPY: N=34, WR=44.1%, PF=1.29, EV_R_fric=+0.064, Kelly_h=0.050 (Sentinel許可)
  - EUR_JPY: N=24, WR=37.5%, PF=0.98 → 棄却対象

実装差分 (原 london_close_reversal.py 比較):
  - ENTRY窓: UTC 15:00-16:15 → UTC 20:30-21:00 (ユーザー仮説準拠)
  - トリガー: wick≥60% → directional_push>0.8ATR + RSI極値
  - News proxy: なし → ATR-spike(>2.5x baseline)で代替ブロック

関連: knowledge-base/wiki/analyses/pre-registration-2026-04-22.md
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class LondonCloseReversalV2(StrategyBase):
    name = "london_close_reversal_v2"
    mode = "daytrade"
    enabled = True                # Sentinel発火許可（_UNIVERSAL_SENTINEL登録済）
    strategy_type = "reversal"    # ADX>25 で conf penalty (逆張りのため)

    # ── 時間帯 (UTC 通算分) ──
    ENTRY_START = 20 * 60 + 30    # UTC 20:30
    ENTRY_END   = 21 * 60         # UTC 21:00

    # ── エントリー条件 ──
    PUSH_LOOKBACK_BARS = 6        # 30min @ 5m = 6 bars (15m=2, 1h=1)
    PUSH_ATR_MULT      = 0.8      # |ΔClose| > ATR * 0.8
    RSI_OVERBOUGHT     = 68.0     # SELL条件: RSI > 68
    RSI_OVERSOLD       = 32.0     # BUY条件: RSI < 32

    # ── News proxy (ATR spike check) ──
    NEWS_BASELINE_BARS = 20       # ATR median baseline
    NEWS_SPIKE_MULT    = 2.5      # 直近 PUSH_LOOKBACK_BARS*2 bars の最大 bar range > 2.5x baseline → skip

    # ── SL/TP ──
    TP_ATR_MULT = 1.8
    SL_ATR_MULT = 1.1
    MIN_RR = 1.5                  # RR保証

    # ── 保持 ──
    MAX_HOLD_BARS = 36            # 3h @ 5m

    @staticmethod
    def _bar_minutes(bar_dt) -> int:
        if hasattr(bar_dt, 'hour') and hasattr(bar_dt, 'minute'):
            return bar_dt.hour * 60 + bar_dt.minute
        return -1

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if ctx.df is None or len(ctx.df) < self.NEWS_BASELINE_BARS + self.PUSH_LOOKBACK_BARS + 5:
            return None

        _bt = ctx.bar_time
        if _bt is None and hasattr(ctx.df.index[-1], 'minute'):
            _bt = ctx.df.index[-1]
        if _bt is None:
            return None

        _cur_min = self._bar_minutes(_bt)
        if _cur_min < 0:
            return None

        if not (self.ENTRY_START <= _cur_min < self.ENTRY_END):
            return None

        # ATR必須
        if ctx.atr <= 0:
            return None

        # TF自動調整: push_bars を TF別に最適化
        # 5m→6bars(30min), 15m→2bars(30min), 1h→1bar 代替せず原値
        _tf = (ctx.tf or "").lower()
        if _tf in ("15m",):
            push_bars = 2
        elif _tf in ("1h", "1hour"):
            push_bars = 1
        else:
            push_bars = self.PUSH_LOOKBACK_BARS  # default 5m向け

        if len(ctx.df) < push_bars + self.NEWS_BASELINE_BARS + 2:
            return None

        # ── directional push 計算 ──
        _close_now = ctx.entry
        _close_past = float(ctx.df["Close"].iloc[-1 - push_bars])
        _push = _close_now - _close_past
        if abs(_push) <= self.PUSH_ATR_MULT * ctx.atr:
            return None

        # ── RSI極値 ──
        signal = None
        if _push > 0 and ctx.rsi > self.RSI_OVERBOUGHT:
            signal = "SELL"
        elif _push < 0 and ctx.rsi < self.RSI_OVERSOLD:
            signal = "BUY"
        if signal is None:
            return None

        # ── News proxy: ATRスパイクブロック ──
        import numpy as _np
        _baseline_atr = float(ctx.df["atr"].iloc[-(self.NEWS_BASELINE_BARS+1):-1].median()) \
            if "atr" in ctx.df.columns else ctx.atr
        _lookback_bars = push_bars * 2
        if _lookback_bars > 0 and len(ctx.df) > _lookback_bars + 1:
            _recent_ranges = (ctx.df["High"].iloc[-_lookback_bars-1:-1]
                              - ctx.df["Low"].iloc[-_lookback_bars-1:-1])
            _max_range = float(_recent_ranges.max()) if len(_recent_ranges) else 0.0
            if _baseline_atr > 0 and _max_range > self.NEWS_SPIKE_MULT * _baseline_atr:
                return None

        # ── 金曜ブロック (London clode前のポジション解消で逆効果想定) ──
        if ctx.is_friday:
            return None

        # ── SL/TP ──
        _atr = ctx.atr
        if signal == "BUY":
            sl = ctx.entry - self.SL_ATR_MULT * _atr
            tp = ctx.entry + self.TP_ATR_MULT * _atr
        else:
            sl = ctx.entry + self.SL_ATR_MULT * _atr
            tp = ctx.entry - self.TP_ATR_MULT * _atr

        _sl_d = abs(ctx.entry - sl)
        _tp_d = abs(tp - ctx.entry)
        if _sl_d <= 0 or _tp_d / _sl_d < self.MIN_RR:
            return None

        _dec = 3 if ctx.is_jpy or ctx.pip_mult == 100 else 5
        score = 3.5
        reasons = [
            f"✅ LCR v2 {signal}: push={_push:+.{_dec}f} "
            f"({abs(_push)/_atr:.2f}×ATR), RSI={ctx.rsi:.0f}",
            f"📊 RR={_tp_d/_sl_d:.1f} SL={sl:.{_dec}f} TP={tp:.{_dec}f}",
        ]

        # 一致ボーナス (EMA短期方向と逆のシグナル = mean-reversion度高)
        if (signal == "SELL" and ctx.ema9 > ctx.ema21) or \
           (signal == "BUY" and ctx.ema9 < ctx.ema21):
            score += 0.3
            reasons.append("✅ EMA短期 逆張り度高")

        # RSI極端度ボーナス (>75 or <25)
        if (signal == "SELL" and ctx.rsi > 75) or \
           (signal == "BUY" and ctx.rsi < 25):
            score += 0.3
            reasons.append(f"✅ RSI極端({ctx.rsi:.0f})")

        conf = int(min(75, 45 + score * 4))
        return Candidate(
            signal=signal, confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score,
        )
