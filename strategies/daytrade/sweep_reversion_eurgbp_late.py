"""Sweep-Reversion EUR_GBP LATE (15m) — thin-session stop-hunt reversal BUY.

発見 (2026-06-12, 12y-first grid scan — research script が先、production は後):
  `tools/research_sweep_reversion_grid_12y.py` の m=1,728 cell grid で
  **唯一の Bonferroni 生存 cell** (z_bonf=4.02):
    EUR_GBP 15m / swing L=96 / depth 0.05×ATR / BUY (low-sweep) / H=48 / LATE
    N=543 (12.4y) / WR 59.7% / mean +6.22p (net 1.5p spread) / t=4.46
    WFO 3-fold: +4.98 / +5.30 / +8.37 (全 fold 正、後半ほど強い) / 年次 11/13 正
  result: bt-results/sweep-reversion-grid-scan-12y.{json,md} (commit 874bc2df)

機序:
  21-24 UTC は EUR_GBP の最薄商い時間 (London/NY とも閉場)。そこでの安値 sweep
  (直近 96 bars の swing low を一瞬割って同バーで reclaim) = thin market での
  stop 狩り。Asia/London の流動性回帰とともに ~12h で平均回帰する。
  Top-10 の 8/10 が同 family (隣接 L/d/H) = param 空間で robust。

反証チェック (3/3 通過, 2026-06-12):
  (1) sweep 条件は無条件 LATE BUY (+1.97p) の 3 倍のエッジ → session drift でない
  (2) spread 感度: 3.5p でも +4.22p (t=3.02)。OANDA EUR_GBP LATE 実勢 1.5-3p
  (3) データ密度 98-101% 均一 → 2021+ のイベント急増 (19→103/年) は実 regime 変化

⚠️ Caveat (撤退判断の根拠):
  - エッジは 2021-2026 に集中 (2014-2020 は N=14-21/年で mixed)。
    「12y 一様」でなく「直近 5y regime」のエッジ → regime 反転 = 撤退トリガー。
  - H=48 (12h 保有) は overnight financing を跨ぐ (EUR_GBP swap は小さいが非ゼロ)。

LIVE 例外 (User 判断 2026-06-12):
  Kalman D7 / carry dip と同系の「意図的 LIVE 例外」(Path B)。
  MIN lot (1000u) 固定 + env flag SWEEP_REVERSION_EURGBP_LIVE_ENABLE 制御 +
  watchdog 撤退条件。pre-reg LOCK:
  knowledge-base/wiki/decisions/sweep-reversion-eurgbp-late-live-2026-06-12.md

Exit 設計 (research との整合):
  research は TP/SL なしの 48-bar close-to-close 計測 (出口バイアス排除)。
  production は time-stop 48 bars (12h, _ENTRY_TYPE_MAX_HOLD=43200s) を一次 exit、
  SL = entry − 4×ATR / TP = entry + 6×ATR は稀にしか触れない tail-cap として配置
  (research の分布をなるべく保存する)。
"""
from __future__ import annotations

import os
from typing import Optional

import pandas as pd

from strategies.base import Candidate, StrategyBase
from strategies.context import SignalContext


class SweepReversionEurgbpLate(StrategyBase):

    name = "sweep_reversion_eurgbp_late"
    mode = "daytrade"
    enabled = True
    strategy_type = "MR"

    _ALLOWED_SYMBOLS = frozenset({"EURGBP"})

    SWING_LOOKBACK = 96       # bars (15m) — survivor cell L
    SWEEP_DEPTH_ATR = 0.05    # pierce threshold ×ATR14 — survivor cell d
    ATR_LEN = 14
    ENTRY_HOUR_START = 21     # LATE session (UTC), signal bar hour ∈ [21, 24)
    ENTRY_HOUR_END = 24
    MAX_HOLD_BARS = 48        # 12h @15m — survivor cell H (time-stop が一次 exit)
    SL_ATR_MULT = 4.0         # emergency tail-cap (research 分布保存のため広め)
    TP_ATR_MULT = 6.0         # 稀にしか触れない (time-stop dominant)
    COOLDOWN_BARS = 12        # research scan と同一 dedup gap
    MIN_HISTORY = SWING_LOOKBACK + ATR_LEN + 5

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_emit_bar_ts: dict = {}
        self._last_emit_ts = None

    @staticmethod
    def _wilder_atr(df: pd.DataFrame, length: int) -> pd.Series:
        prev_close = df["Close"].shift(1)
        tr = pd.concat(
            [df["High"] - df["Low"],
             (df["High"] - prev_close).abs(),
             (df["Low"] - prev_close).abs()], axis=1,
        ).max(axis=1)
        return tr.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        if sym not in self._ALLOWED_SYMBOLS:
            return None
        if not getattr(self, "enabled", True):
            return None
        if os.environ.get("SWEEP_REVERSION_EURGBP_ENABLE", "1") == "0":
            return None  # signal-level kill switch (rollback path)
        if ctx.df is None or len(ctx.df) < self.MIN_HISTORY:
            return None

        # R3: BT は iloc[-1]=closed bar、Live は iloc[-1]=進行中 → closed=iloc[-2]
        closed_idx = -1 if getattr(ctx, "backtest_mode", False) else -2

        df = ctx.df
        low_s, high_s, close_s = df["Low"], df["High"], df["Close"]

        # ── LATE session window (signal bar の UTC hour) ──
        try:
            bar_id = df.index[closed_idx]
            bar_ts = pd.Timestamp(bar_id)
            if bar_ts.tzinfo is None:
                bar_ts = bar_ts.tz_localize("UTC")
            else:
                bar_ts = bar_ts.tz_convert("UTC")
        except Exception:
            return None
        if not (self.ENTRY_HOUR_START <= bar_ts.hour < self.ENTRY_HOUR_END):
            return None

        # ── sweep 検出 (research と同一定義) ──
        # swing_lo = closed bar を除く直近 L bars の min(Low)
        window_lo = low_s.iloc[closed_idx - self.SWING_LOOKBACK: closed_idx]
        if len(window_lo) < self.SWING_LOOKBACK:
            return None
        swing_lo = float(window_lo.min())

        atr = self._wilder_atr(df, self.ATR_LEN)
        atr_closed = float(atr.iloc[closed_idx])
        if not (atr_closed == atr_closed) or atr_closed <= 0:  # NaN guard
            return None

        closed_low = float(low_s.iloc[closed_idx])
        closed_close = float(close_s.iloc[closed_idx])
        swept = closed_low < swing_lo - self.SWEEP_DEPTH_ATR * atr_closed
        reclaimed = closed_close > swing_lo
        if not (swept and reclaimed):
            return None

        # ── per-bar dedup (30s polling runaway 防止: R3) ──
        dedup_key = (ctx.symbol, "BUY")
        if self._last_emit_bar_ts.get(dedup_key) == bar_id:
            return None

        # ── re-entry cooldown 12 bars (=3h @15m, research dedup gap と同一) ──
        if self._last_emit_ts is not None:
            if (bar_ts - self._last_emit_ts) < pd.Timedelta(minutes=15 * self.COOLDOWN_BARS):
                return None

        entry = float(ctx.entry) if getattr(ctx, "entry", 0) else closed_close
        sl = entry - self.SL_ATR_MULT * atr_closed
        tp = entry + self.TP_ATR_MULT * atr_closed
        if sl <= 0 or tp <= entry:
            return None

        sweep_depth_pips = (swing_lo - closed_low) / 0.0001
        score = 3.0 + min(2.0, sweep_depth_pips / 5.0)

        self._last_emit_bar_ts[dedup_key] = bar_id
        self._last_emit_ts = bar_ts

        return Candidate(
            signal="BUY",
            confidence=65,
            sl=sl,
            tp=tp,
            reasons=[
                "✅ EUR_GBP LATE thin-session low-sweep reclaim (stop-hunt 戻り)",
                f"✅ sweep depth {sweep_depth_pips:.1f}p below swing_lo({swing_lo:.5f}), "
                f"close reclaim {closed_close:.5f}",
                f"✅ LATE window h={bar_ts.hour} UTC (21-24=最薄商い)",
                f"📊 12y grid survivor: N=543 WR=59.7% +6.22p t=4.46 (Bonferroni m=1728)",
                f"⏱ time-stop 48bars(12h) 一次exit / SL=4×ATR tail-cap",
            ],
            entry_type=self.name,
            score=score,
            max_hold_bars=self.MAX_HOLD_BARS,
        )
