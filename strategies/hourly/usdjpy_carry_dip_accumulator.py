"""
USDJPY Carry Dip-Accumulator (H1) — regime-fit long-only dip buy.

思想 (2026-06-08, session: USDJPY「勝てるインジケーター」):
  現レジーム = 155-160.7 の高位レンジ。160 = MOF/BOJ 介入の政策壁 (2024 介入水準)。
  ドリフトは**上** (因果2本):
    (1) 日米金利差キャリー: 米 10Y 4.47 / 2Y 4.05 高止まり、BOJ は 0.75% で正常化は緩慢。
    (2) コストプッシュ: 2026 イラン戦争/ホルムズ封鎖オイルショック → 資源輸入の日本は
        貿易赤字拡大 → 実需の円売り。円は逃避通貨の地位を喪失 (有事ドル買い=円売り)。
  介入は「方向転換」でなく「天井で撃ち落とす単発イベント」(4月 160.7→155.5 は1日で回復基調)。
  → 正解 = ドリフト順張りロング + 押し目を拾う、160壁に張り付かない (撃たれる位置を避ける)。

エントリ (stateless 単発 dip-buy):
  - USD_JPY のみ。
  - 押し目: RSI(14, closed bar) < RSI_BUY(45)。
  - 天井回避: closed close < CEILING(159.5) — 壁直下では新規ロングしない。
  - イベント遮断: BOJ/Fed 会合窓 (2026-06-15..18 UTC) は新規停止。
  - SL = entry - SL_YEN(1.5) … 介入ギャップ前提の per-trade テールキャップ。
  - TP = entry + TP_YEN(0.8) … 押して拾って戻りで利確 (高WR/低RR プロファイル)。
  - hold ≤ MAX_HOLD_BARS(24 H1 = ~2日)。

検証 (2026-06-08, Claude 直接実装・一次データ):
  - オフライン BT (TV H4 500本, 4月介入クラッシュ込み, MtM DD): tail-capped v3 =
    90.9% WR / PF 4.35 / 最悪テール -2.0円ハードキャップ (制御なしは構造テール -14円)。
  - H1 (May08-Jun08) 再検証: 月2-3 発火・max同時トランシェ=1 → 現レジームでは単発に縮退。
    N は TF でなくレジームが律速 (低頻度は構造的)。
  - sanity PASS 止まり (N≈10, 単一4ヶ月レジーム)。統計証明ではない。

LIVE 例外 (User 判断 2026-06-08):
  低頻度ゆえ shadow でも蓄積速度は同じ → 小ロット LIVE で実 fill を貯める判断。
  Kalman D7 / vix_carry / ZZ v60 と同系の「意図的 LIVE 例外」。
  retreat 条件 (どれか → kill):
    (1) BOJ ガチ利上げ/タカ派転換でドリフト反転、(2) オイル完全沈静化で円高転換、
    (3) 累積 LIVE DD が閾値超 (watchdog)。
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import pandas as pd

from strategies.base import Candidate, StrategyBase
from strategies.context import SignalContext
from modules.round_number import shift_tp_inside

logger = logging.getLogger("usdjpy_carry_dip_accumulator")


class UsdjpyCarryDipAccumulator(StrategyBase):

    name = "usdjpy_carry_dip_accumulator"
    mode = "hourly"
    enabled = True
    strategy_type = "MR"

    _ALLOWED_SYMBOLS = frozenset({"USDJPY"})

    RSI_LEN = 14
    RSI_BUY = 45.0
    CEILING = 159.50          # 壁直下では新規ロングしない
    SL_YEN = 1.50             # per-trade テールキャップ (介入ギャップ前提)
    TP_YEN = 0.80
    MAX_HOLD_BARS = 24        # ~2 日 (H1)
    COOLDOWN_BARS = 12        # 同一押し目クラスタを1エントリーに畳む re-entry 抑制 (H1=12h)
    MIN_HISTORY = RSI_LEN + 5

    # BOJ/Fed イベント遮断窓 (UTC)
    _BLACKOUT_START = pd.Timestamp("2026-06-15T00:00:00", tz="UTC")
    _BLACKOUT_END = pd.Timestamp("2026-06-18T00:00:00", tz="UTC")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_emit_bar_ts: dict = {}
        self._last_emit_ts = None  # re-entry cooldown anchor
        self._last_qualbar_logged = None  # QUALBAR log per-bar dedup (T7 telemetry)

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        if sym not in self._ALLOWED_SYMBOLS:
            return None
        if not getattr(self, "enabled", True):
            return None
        if ctx.df is None or len(ctx.df) < self.MIN_HISTORY:
            return None

        # R3 (2026-04-30): BT は iloc[-1]=closed bar、Live は iloc[-1]=進行中 → closed=iloc[-2]
        closed_idx = -1 if getattr(ctx, "backtest_mode", False) else -2

        close_s = ctx.df["Close"]
        if len(close_s) < self.RSI_LEN + abs(closed_idx) + 1:
            return None

        rsi = self._wilder_rsi(close_s, self.RSI_LEN)
        rsi_closed = float(rsi.iloc[closed_idx])
        rsi_prev = float(rsi.iloc[closed_idx - 1])
        closed_close = float(close_s.iloc[closed_idx])
        if not (rsi_closed == rsi_closed and rsi_prev == rsi_prev):  # NaN guard
            return None

        # ── エントリ条件 ──
        # dip 入口の EDGE だけ拾う: RSI が RSI_BUY を「下抜けた瞬間」のみ emit。
        # (level トリガだと RSI<45 が続く間、毎バー emit して over-trade になる — fire
        #  test 2026-06-08 で 49 emits/月 を観測し修正。「押し目1回」の cadence に戻す)
        if not (rsi_prev >= self.RSI_BUY and rsi_closed < self.RSI_BUY):
            return None

        # ── ここから下は「トリガー成立バー」= 発火期待値の分母 (roadmap T7) ──
        # 後段 filter の pass/fail を QUALBAR 1行に集約して log し、
        # 「シグナルは出たが filter で落ちた」を production ログで観測可能にする。
        # (2026-07-02 診断: CEILING 静的壁が dip cross 22 回を silent drop していた)
        bar_id = None
        bar_ts = None
        try:
            bar_id = ctx.df.index[closed_idx]
            bar_ts = pd.Timestamp(bar_id)
            if bar_ts.tzinfo is None:
                bar_ts = bar_ts.tz_localize("UTC")
        except Exception:
            bar_ts = None

        ceiling_pass = closed_close < self.CEILING          # 壁直下回避
        blackout_pass = not (
            bar_ts is not None
            and self._BLACKOUT_START <= bar_ts < self._BLACKOUT_END
        )
        # per-bar dedup (30s polling × in-progress bar の runaway 防止: R3)
        dedup_key = (ctx.symbol, "BUY")
        dedup_pass = not (
            bar_id is not None
            and self._last_emit_bar_ts.get(dedup_key) == bar_id
        )
        # re-entry cooldown: 同一押し目クラスタを1エントリーに畳む
        cooldown_pass = not (
            bar_ts is not None
            and self._last_emit_ts is not None
            and (bar_ts - self._last_emit_ts) < pd.Timedelta(hours=self.COOLDOWN_BARS)
        )
        emit_expected = ceiling_pass and blackout_pass and dedup_pass and cooldown_pass

        # QUALBAR log: 同一 closed bar への再 poll では重複させない
        if self._last_qualbar_logged != bar_id:
            self._last_qualbar_logged = bar_id
            # print() 必須: 本番 (gunicorn) は logging handler 未設定で INFO が破棄される
            # (app.py 2026-07-02 コメント参照。logger.info 時代は T7 E2E 検証が構造的に不可能だった)
            print(
                "[%s] QUALBAR bar=%s rsi=%.1f close=%.3f ceiling_pass=%s "
                "blackout_pass=%s dedup_pass=%s cooldown_pass=%s emit=%s"
                % (self.name, bar_id, rsi_closed, closed_close, ceiling_pass,
                   blackout_pass, dedup_pass, cooldown_pass, emit_expected),
                flush=True,
            )

        if not emit_expected:
            return None

        entry = float(ctx.entry) if getattr(ctx, "entry", 0) else closed_close
        sl = entry - self.SL_YEN
        tp = entry + self.TP_YEN
        tp = shift_tp_inside(tp, "BUY", pip=0.01, shift_pips=3.0)
        if sl <= 0 or tp <= entry:
            return None

        score = 3.0 + min(2.0, (self.RSI_BUY - rsi_closed) / 10.0)
        if bar_id is not None:
            self._last_emit_bar_ts[dedup_key] = bar_id
        if bar_ts is not None:
            self._last_emit_ts = bar_ts

        return Candidate(
            signal="BUY",
            confidence=65,
            sl=sl,
            tp=tp,
            reasons=[
                "✅ Carry+cost-push UP drift 順張りロング",
                f"✅ 押し目 RSI(14)={rsi_closed:.1f} < {self.RSI_BUY:.0f}",
                f"✅ 壁直下回避 close {closed_close:.3f} < {self.CEILING:.1f}",
                f"✅ tail-cap SL=-{self.SL_YEN:.1f}円 / TP=+{self.TP_YEN:.1f}円 / hold≤{self.MAX_HOLD_BARS}bar",
            ],
            entry_type=self.name,
            score=score,
            max_hold_bars=self.MAX_HOLD_BARS,
            sr_meta={
                "thesis": "carry_costpush_up_drift_intervention_capped",
                "rsi_closed": round(rsi_closed, 2),
                "ceiling": self.CEILING,
                "exit_kind": "tp_or_sl_or_hold",
            },
        )

    @staticmethod
    def _wilder_rsi(close: pd.Series, length: int) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0.0)
        loss = (-delta).clip(lower=0.0)
        avg_gain = gain.ewm(alpha=1.0 / length, min_periods=length, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1.0 / length, min_periods=length, adjust=False).mean()
        rs = avg_gain / (avg_loss + 1e-12)
        return 100.0 - 100.0 / (1.0 + rs)
