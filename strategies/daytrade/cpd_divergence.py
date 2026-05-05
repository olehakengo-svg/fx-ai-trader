"""
CPD Divergence — Cross-Pair Divergence Convergence (15m daytrade)

仮説 (pre-registered, Avellaneda-Lee 2010):
  EUR_USD と GBP_USD は USD common driver で正相関 (typical 0.7+)。
  Rolling 4h 相関が breakdown (corr < 0.1) かつ price z-spread > 2.5σ で
  発散 → 数 bar 内に laggard が leader を追って収束する。

cpd_refine_audit (2026-04-27) 結果:
  ct=0.1, zt=2.5, fw=2: n=19/365d, WR 73.7%, Wilson_lo 51.2%,
  EV +1.00 pip net, PF 1.72, Kelly 0.26, quarterly all > BEV
  ✅ Wilson > BEV ∧ EV > 0 ∧ Quarterly stable ∧ Kelly > 0
  ✗ Bonferroni (36-grid penalty) — Sentinel deploy adequate

エントリ (laggard pair = GBP_USD のみ trade):
  - rolling 16-bar (4h) corr < 0.1
  - z_spread = a_z - b_z, |z_spread| > 2.5
  - laggard signal = sign(z_spread) → BUY if leader ahead, SELL if leader behind
  - SL = 1.0 ATR, TP = 1.5 ATR (RR 1.5)
  - Hold up to 2 bar (30 min)

Shadow only — PAIR_PROMOTED に追加しない。30 trade Live で再検証。
"""
from __future__ import annotations
from typing import Optional
import math
import os

import numpy as np
import pandas as pd

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext


class CpdDivergence(StrategyBase):

    name = "cpd_divergence"
    mode = "daytrade"
    enabled = True   # Shadow 走行で per-cell 実測判定 (Bonferroni 不通過分は Live 蓄積で確認)
    strategy_type = "MR"

    # GBP_USD のみ trade (audit pre-registered laggard)
    _ALLOWED_SYMBOLS = frozenset({"GBPUSD"})
    LEADER_SYMBOL = "EURUSD=X"

    # Audit best params
    CORR_WINDOW_BARS = 16        # 4h rolling
    CORR_BREAKDOWN = 0.1
    Z_THRESHOLD = 2.5
    FORWARD_BARS = 2             # 30 min hold

    SL_ATR_MULT = 1.0
    TP_ATR_MULT = 1.5
    MIN_RR = 1.4

    MAX_HOLD_BARS = 2

    _dedup_state: dict = {}
    _leader_cache: dict = {}

    @classmethod
    def reset_dedup_state(cls):
        cls._dedup_state.clear()

    def _redesign_v2_enabled(self) -> bool:
        return os.environ.get("CPD_DIVERGENCE_REDESIGN_V2") == "1"

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        v2 = self._redesign_v2_enabled()
        sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        if sym not in self._ALLOWED_SYMBOLS:
            return None
        if ctx.df is None or len(ctx.df) < 80:
            return None

        signal_df = ctx.df
        signal_bar_time = None
        if v2:
            if ctx.bar_time is not None:
                try:
                    signal_df = ctx.df.loc[:ctx.bar_time]
                except Exception:
                    signal_df = ctx.df
            if signal_df is None or len(signal_df) < 81:
                return None
            signal_bar_time = signal_df.index[-2]
            signal_df = signal_df.iloc[:-1]

        # Build 60-bar return series for the laggard
        b_close = signal_df["Close"].astype(float)
        b_ret = b_close.pct_change()

        # Need leader (EUR_USD) data — load via ctx.htf or fallback to module-level cache
        leader_df = self._load_leader_aligned(ctx, signal_bar_time=signal_bar_time, redesign_v2=v2)
        if leader_df is None or len(leader_df) < 80:
            return None

        a_ret = leader_df["Close"].pct_change()

        # Align by latest 80 bars (matched datetime index)
        b_recent = b_ret.iloc[-80:]
        a_recent = a_ret.reindex(b_recent.index).dropna()
        if len(a_recent) < self.CORR_WINDOW_BARS + 60:
            return None
        b_recent = b_recent.loc[a_recent.index]

        # Rolling correlation
        rolling_corr = a_recent.rolling(self.CORR_WINDOW_BARS).corr(b_recent)
        latest_corr = rolling_corr.iloc[-1]
        if not np.isfinite(latest_corr):
            return None

        # Rolling z-spread
        a_60 = a_recent.iloc[-60:]
        b_60 = b_recent.iloc[-60:]
        a_z = (a_60.iloc[-1] - a_60.mean()) / (a_60.std() + 1e-9)
        b_z = (b_60.iloc[-1] - b_60.mean()) / (b_60.std() + 1e-9)
        z_spread = a_z - b_z

        # Trigger conditions (audit best params)
        if latest_corr >= self.CORR_BREAKDOWN:
            return None
        if abs(z_spread) <= self.Z_THRESHOLD:
            return None

        # Direction: laggard converges toward leader
        # If leader's z is high (rallying), expect b to follow up → BUY
        if z_spread > 0:
            signal = "BUY"
        else:
            signal = "SELL"

        atr = max(ctx.atr, 1e-9)
        if signal == "BUY":
            sl = ctx.entry - self.SL_ATR_MULT * atr
            tp = ctx.entry + self.TP_ATR_MULT * atr
        else:
            sl = ctx.entry + self.SL_ATR_MULT * atr
            tp = ctx.entry - self.TP_ATR_MULT * atr

        # RNR injection: TP away from round number
        try:
            from modules.round_number import shift_tp_inside
            tp = shift_tp_inside(tp, signal, pip=0.0001, shift_pips=3.0)
        except Exception:
            pass

        sl_dist = abs(ctx.entry - sl)
        tp_dist = abs(tp - ctx.entry)
        if sl_dist <= 0:
            return None
        rr = tp_dist / sl_dist
        if rr < self.MIN_RR:
            return None

        if v2:
            dedup_key = (self.name, sym, signal, str(signal_bar_time))
            if self._dedup_state.get(dedup_key):
                return None
            self._dedup_state[dedup_key] = True

        score = 4.0
        # Stronger score for more extreme z_spread or lower correlation
        if abs(z_spread) > 3.0:
            score += 0.5
        if latest_corr < 0.0:  # Truly negative correlation (anti-correlated moment)
            score += 0.3

        reasons = [
            f"✅ CPD divergence: corr={latest_corr:.2f}<{self.CORR_BREAKDOWN}",
            f"✅ z_spread={z_spread:+.2f} (|z|>{self.Z_THRESHOLD})",
            f"✅ Laggard {signal} converging to leader EURUSD",
            f"✅ RR={rr:.2f}, hold≤{self.MAX_HOLD_BARS}bar (30min)",
        ]

        return Candidate(
            signal=signal,
            confidence=min(100, int(score * 18)),
            sl=float(sl),
            tp=float(tp),
            reasons=reasons,
            entry_type=self.name,
            score=float(score),
        )

    def _load_leader_aligned(self, ctx: SignalContext, signal_bar_time=None,
                             redesign_v2: bool = False) -> Optional[pd.DataFrame]:
        """Load EUR_USD DataFrame aligned to ctx.df timestamps.

        Production path: cached BTDataCache call. Test path: ctx.layer3 may
        provide pre-loaded leader data via 'cpd_leader_df' key.
        """
        cached = ctx.layer3.get("cpd_leader_df") if ctx.layer3 else None
        if cached is not None:
            return self._cut_leader_to_signal_time(cached, signal_bar_time) if redesign_v2 else cached
        try:
            cache_key = ("EUR_USD", "15m", bool(redesign_v2),
                         os.environ.get("BT_REQUIRE_MASSIVE_CACHE") == "1")
            df = self._leader_cache.get(cache_key)
            if df is None:
                if os.environ.get("BT_REQUIRE_MASSIVE_CACHE") == "1":
                    from pathlib import Path
                    path = Path(__file__).resolve().parents[2] / "data/cache/massive/EUR_USD_15m.parquet"
                    if not path.exists():
                        return None
                    df = pd.read_parquet(path)
                else:
                    from tools.bt_data_cache import BTDataCache
                    cache = BTDataCache()
                    df = cache.get("EUR_USD", "15m", days=365 if redesign_v2 else 2)
                self._leader_cache[cache_key] = df
            if df.index.tz is None:
                df.index = df.index.tz_localize("UTC")
            if redesign_v2:
                return self._cut_leader_to_signal_time(df, signal_bar_time)
            # Align to ctx.df last 80 bars
            return df.tail(120)
        except Exception:
            return None

    @staticmethod
    def _cut_leader_to_signal_time(df: pd.DataFrame, signal_bar_time) -> pd.DataFrame:
        if signal_bar_time is None or df is None:
            return df
        aligned = df.copy()
        if aligned.index.tz is None:
            aligned.index = aligned.index.tz_localize("UTC")
        ts = pd.Timestamp(signal_bar_time)
        if ts.tzinfo is None and aligned.index.tz is not None:
            ts = ts.tz_localize(aligned.index.tz)
        elif ts.tzinfo is not None and aligned.index.tz is None:
            aligned.index = aligned.index.tz_localize(ts.tzinfo)
        elif ts.tzinfo is not None and aligned.index.tz is not None:
            ts = ts.tz_convert(aligned.index.tz)
        return aligned.loc[:ts]
