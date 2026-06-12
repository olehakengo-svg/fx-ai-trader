"""
Hull x Donchian FADE (EUR_USD M15) — compression-gated dual-confirmation fade.

思想 (2026-06-12, session: TV Hull Suite + Donchian Trend Ribbon 1m 探索):
  1m で momentum (Hull色flip ∧ Donchianブレイク同方向) を検証した結果 THESIS_INVALID
  (3ペア全ホライズンで forward return 負 = ブレイクは継続せず反転する)。
  逆に FADE (二重確認シグナルの完全逆張り) に方向エッジが実在するが、
  1m では gross +0.5p < spread 0.6-1.2p で friction-killed。
  TF スイープで「fade gross は TF と共に成長 / spread は固定」を確認、15m で壁を超える。
  深掘り (train 2014-2022 探索 → holdout 2022-2026 一発 confirm):
    - 唯一 transfer した構造 = 「チャネル圧縮時のみ張る」(width/ATR ≤ train-q33)。
      広いチャネル = トレンド進行中の fade は構造的に轢かれる。
    - exit は Donchian basis (中央線) 回帰。ATR2 ストップは MR を破壊 (一時逆行を実損化)。

検証 (Claude 直接実装・一次データ、repo: /Users/jg-n-012/test/hull-donchian-1m-validation):
  - MASSIVE 12.4y EUR_USD 15m、spread 0.6p 控除済。
  - Holdout (2022-01..2026-06, untouched): N=2133 WR=0.692 net_EV=+0.903p PF=1.156
    p=0.0146 (BH-FDR m=2 生存)、L/S 両side正。
  - 実装忠実度 BT (本番メカニクス: TP=entry-bar basis 静的, SL=4xATR intrabar SL-first,
    max_hold=96bar): holdout N=1833 WR=0.780 net_EV=+1.342p PF=1.191 p=0.0005、
    LONG +1.05p / SHORT +1.57p。bar-close 動的 basis exit より改善 (指値が intrabar
    タッチを拾うため)。SL=4xATR は 3/4/5 の中央デフォルト、追加最適化なし。
  - TV 独立再現: EURUSD 15m 365d WR 68.49% PF 1.167 (OANDA feed, Python 値とほぼ一致)。
  - 既知の弱点 cell (holdout 実測): SHORT x macro-UP (trailing 90d 上昇) = EV -0.10p
    (≈フラット、出血ではない)。watchdog 監視対象。

LIVE 例外 (User 判断 2026-06-12):
  shadow 経由せず小ロット実弾検証 (Kalman D7 / carry_dip / ZZ v60 と同型の意図的例外)。
  MIN lot 1000u 固定、env HULL_DONCHIAN_FADE_LIVE_ENABLE=1 でのみ LIVE 転送。
  retreat 条件 (pre-reg, どれか成立 → demote/kill):
    (1) Live N>=10 で net EV < 0 (Rule 2 即断)
    (2) Live N>=30 で WR < 55% or PF < 1.0
    (3) SHORT x macro-UP cell が N>=30 で EV < -0.5p → SHORT 側のみ lot 0.5x (SIZE lever,
        SKIP はしない — feedback_size_lever_beats_skip_filter)
    (4) 既存 CB (日次 -30pip) / DD ゲートは無条件で優先
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np
import pandas as pd

from strategies.base import Candidate, StrategyBase
from strategies.context import SignalContext


class HullDonchianFade(StrategyBase):

    name = "hull_donchian_fade"
    mode = "daytrade"
    enabled = True
    strategy_type = "MR"

    _ALLOWED_SYMBOLS = frozenset({"EURUSD"})

    # ── frozen spec (train 2014-2022 で機械選定、holdout で confirm 済。再最適化禁止) ──
    HULL_LEN = 55
    DON_LEN = 20
    ATR_LEN = 14                  # SMA of TR (検証エンジンと同一。Wilder RMA ではない)
    MAX_WIDTH_ATR = 3.8558        # train-q33 凍結値 (width/ATR がこれ以下 = 圧縮 = 張ってよい)
    SL_ATR_MULT = 4.0             # 災害ストップ (MR ノイズの外側)
    MAX_HOLD_BARS = 96            # 1 取引日 (15m x 96 = 24h) バックストップ
    MIN_HISTORY = 90              # HMA55(+sqrt窓+shift2) + Donchian20 + ATR14 + closed offset

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_emit_bar_ts: dict = {}

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "") if ctx.symbol else ""
        if sym not in self._ALLOWED_SYMBOLS:
            return None
        if not getattr(self, "enabled", True):
            return None
        if ctx.df is None or len(ctx.df) < self.MIN_HISTORY:
            return None

        # R3 (2026-04-30): BT は iloc[-1]=closed bar、Live は iloc[-1]=進行中 → closed=iloc[-2]
        closed_idx = -1 if getattr(ctx, "backtest_mode", False) else -2
        end = len(ctx.df) + closed_idx + 1
        if end < self.MIN_HISTORY:
            return None
        sub = ctx.df.iloc[:end]

        close = sub["Close"]
        high = sub["High"]
        low = sub["Low"]
        c0 = float(close.iloc[-1])

        # ── Hull trend: HMA[0] vs HMA[2] (Hull Suite 規約) ──
        tail = close.iloc[-(self.HULL_LEN + 16):]
        h = self._hma(tail, self.HULL_LEN)
        if len(h.dropna()) < 3:
            return None
        h0, h2 = float(h.iloc[-1]), float(h.iloc[-3])
        if not (math.isfinite(h0) and math.isfinite(h2)):
            return None
        bull = h0 > h2
        bear = h0 < h2

        # ── Donchian: 前バー時点のチャネル (breakout 判定) と現 closed バーのチャネル ──
        upper_prev = float(high.iloc[-(self.DON_LEN + 1):-1].max())
        lower_prev = float(low.iloc[-(self.DON_LEN + 1):-1].min())
        upper_now = float(high.iloc[-self.DON_LEN:].max())
        lower_now = float(low.iloc[-self.DON_LEN:].min())
        basis_now = (upper_now + lower_now) / 2.0

        # ── ATR14 (SMA of TR、検証エンジン同一) & 圧縮フィルタ ──
        pc = close.shift(1)
        tr = pd.concat([high - low, (high - pc).abs(), (low - pc).abs()], axis=1).max(axis=1)
        atr_now = float(tr.iloc[-self.ATR_LEN:].mean())
        if not math.isfinite(atr_now) or atr_now <= 0:
            return None
        width_atr = (upper_now - lower_now) / atr_now
        if width_atr > self.MAX_WIDTH_ATR:
            return None  # 非圧縮 (トレンド進行) regime では張らない

        # ── FADE 二重確認: momentum シグナルの完全逆張り ──
        long_break = c0 > upper_prev
        short_break = c0 < lower_prev
        signal = None
        if long_break and bull:
            signal = "SELL"          # 上方ブレイク+Hull bull を売る
        elif short_break and bear:
            signal = "BUY"           # 下方ブレイク+Hull bear を買う
        if signal is None:
            return None

        # ── per-bar dedup (30s polling x in-progress bar の runaway 防止: R3) ──
        bar_id = None
        try:
            bar_id = sub.index[-1]
        except Exception:
            pass
        dedup_key = (ctx.symbol, signal)
        if bar_id is not None and self._last_emit_bar_ts.get(dedup_key) == bar_id:
            return None

        entry = float(ctx.entry) if getattr(ctx, "entry", 0) else c0
        if signal == "SELL":
            tp = basis_now
            sl = entry + self.SL_ATR_MULT * atr_now
            if not (tp < entry < sl):
                return None          # basis が entry の正しい側にない異常 bar は見送り
        else:
            tp = basis_now
            sl = entry - self.SL_ATR_MULT * atr_now
            if not (sl < entry < tp):
                return None

        if bar_id is not None:
            self._last_emit_bar_ts[dedup_key] = bar_id

        score = 3.0 + max(0.0, min(2.0, (self.MAX_WIDTH_ATR - width_atr)))
        return Candidate(
            signal=signal,
            confidence=65,
            sl=sl,
            tp=tp,
            reasons=[
                "✅ 圧縮チャネル fade (width/ATR "
                f"{width_atr:.2f} <= {self.MAX_WIDTH_ATR:.2f})",
                f"✅ 二重確認 {'上方' if signal == 'SELL' else '下方'}ブレイク x Hull "
                f"{'bull' if bull else 'bear'} を逆張り",
                f"✅ TP=Donchian basis {basis_now:.5f} / SL={self.SL_ATR_MULT:.0f}xATR / "
                f"hold<={self.MAX_HOLD_BARS}bar",
                "✅ holdout 12.4y: WR 78% / net+1.34p / PF 1.19 (忠実度BT)",
            ],
            entry_type=self.name,
            score=score,
            max_hold_bars=self.MAX_HOLD_BARS,
            sr_meta={
                "thesis": "compression_gated_dual_confirmation_fade",
                "width_atr": round(width_atr, 4),
                "basis": round(basis_now, 6),
                "hull_bull": bool(bull),
                "exit_kind": "tp_basis_or_sl_or_hold",
            },
        )

    # ── indicators (検証エンジン /hull-donchian-1m-validation/indicators.py と同一定義) ──
    @staticmethod
    def _wma(series: pd.Series, length: int) -> pd.Series:
        weights = np.arange(1, length + 1, dtype=float)
        wsum = weights.sum()
        return series.rolling(length).apply(lambda x: np.dot(x, weights) / wsum, raw=True)

    @classmethod
    def _hma(cls, series: pd.Series, length: int) -> pd.Series:
        half = int(length / 2)
        sqrt_len = int(round(math.sqrt(length)))
        return cls._wma(2 * cls._wma(series, half) - cls._wma(series, length), sqrt_len)
