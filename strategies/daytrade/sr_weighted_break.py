"""
SR Weighted Break — Heavy wall breakout follow-through with composite weight gate (15m daytrade)

設計思想 (2026-05-13 司令塔, family pair of sr_weighted_bounce):
  - heavy wall を **突破した bar の retest** で順張りエントリ (role reversal)
  - composite weight gate で軽い壁ブレイクのノイズを排除
  - 既存 sr_break_retest (smoking gun: MIN_CLUSTERS=1) を残置、本戦略は別物として並走

エントリ条件 (heavy wall breakout retest):
  1. ペアフィルター: 5 majors (USDJPY/EURUSD/GBPUSD/EURJPY/GBPJPY)
  2. ADX >= 20 (モメンタム裏付け、sr_break_retest 整合)
  3. **Weight gate**:
     (a) composite_weight >= K_ABS_THRESHOLD (=3.0) AND
     (b) level が現在 weighted_levels の上位 30% percentile に入る
  4. Break detected: 過去 2-10 本のいずれかの bar が
     close > level + 0.05 ATR (BUY) または close < level - 0.05 ATR (SELL)
     かつ break bar の body / range >= 0.25
  5. Retest: 現在価格が broken level の ±0.5 ATR 以内に戻っている
  6. Retest 反転足: BUY なら close > open AND close > EMA9、SELL は逆
  7. HTF 方向矛盾 block: htf.agreement が逆方向の場合は skip
  8. v2_redesign パターン: closed bar (df.iloc[-2]) で signal 確定、per-bar dedup

SL = broken level の反対側 ± SL_ATR_BUFFER (=0.3) × ATR  ※role reversal placement
TP = min(next opposite SR, entry + RR × SL_dist) で early target、RR=2.0、MIN_RR=1.5

composite_weight 計算は sr_weighted_bounce と同式 (Wave 1 固定):
  1.0 × own_touch + 3.0 × d1_touch + 5.0 × w1_touch +
  2.0 × round_score + 1.5 × magnitude_score
"""
from __future__ import annotations
from typing import Optional
import logging
import os

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from modules.round_number import (
    expand_sl_for_round, shift_tp_inside, is_near_round,
)

logger = logging.getLogger(__name__)


class SrWeightedBreak(StrategyBase):

    name = "sr_weighted_break"
    mode = "daytrade"
    enabled = False   # Shadow-only スタート、env SR_WEIGHTED_BREAK_ENABLE=1 で有効化
    strategy_type = "pullback"   # break→retest→continuation = pullback by construction

    _ALLOWED_SYMBOLS = frozenset({"USDJPY", "EURUSD", "GBPUSD", "EURJPY", "GBPJPY"})

    # Weight gate (Wave 1 固定、sr_weighted_bounce と同値)
    K_ABS_THRESHOLD = 3.0
    WEIGHT_PERCENTILE_TOP = 0.30
    W_OWN = 1.0
    W_D1 = 3.0
    W_W1 = 5.0
    W_ROUND = 2.0
    W_MAGNITUDE = 1.5

    # Break detection (sr_break_retest 整合)
    ADX_MIN = 20
    BREAK_LOOKBACK_MIN = 2
    BREAK_LOOKBACK_MAX = 10
    BREAK_BODY_MIN = 0.25
    BREAK_MARGIN_ATR = 0.05
    RETEST_ZONE_ATR = 0.5
    RETEST_BOUNCE_EMA = True

    # SL/TP geometry
    SL_ATR_BUFFER = 0.3
    TARGET_RR = 2.0
    MIN_RR = 1.5

    MAX_HOLD_BARS = 12
    _v2_seen_closed_bar_keys: set[tuple[str, str, str, str, str]] = set()
    _diag_counts: dict[tuple[str, str], int] = {}
    _diag_last_logged: set[tuple[str, str, str]] = set()

    @classmethod
    def reset_dedup_state(cls):
        cls._v2_seen_closed_bar_keys.clear()

    @classmethod
    def reset_diagnostics(cls):
        cls._diag_counts.clear()
        cls._diag_last_logged.clear()

    @classmethod
    def diagnostics_snapshot(cls) -> dict[str, int]:
        return {f"{sym}:{state}": n for (sym, state), n in sorted(cls._diag_counts.items())}

    def _diag(self, ctx: SignalContext, state: str, bar_time=None) -> None:
        sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        self._diag_counts[(sym, state)] = self._diag_counts.get((sym, state), 0) + 1
        if os.environ.get("SR_WEIGHTED_BREAK_DIAG_LOG") != "1":
            return
        key = (sym, str(bar_time), state)
        if key in self._diag_last_logged:
            return
        self._diag_last_logged.add(key)
        logger.info(
            "[SR_WEIGHTED_BREAK_DIAG] symbol=%s bar_time=%s state=%s count=%s",
            sym, bar_time, state, self._diag_counts[(sym, state)],
        )

    def _env_enabled(self) -> bool:
        return os.environ.get("SR_WEIGHTED_BREAK_ENABLE") == "1"

    def _compute_composite_weight(self, level_meta: dict) -> float:
        own = int(level_meta.get("own_touch",
                                 level_meta.get("touch_count",
                                                level_meta.get("touches", 0))) or 0)
        d1 = int(level_meta.get("d1_touch", 0) or 0)
        w1 = int(level_meta.get("w1_touch", 0) or 0)
        rscore = float(level_meta.get("round_score", 0.0) or 0.0)
        mscore = float(level_meta.get("magnitude_score", 0.0) or 0.0)
        if rscore == 0.0 and "price" in level_meta:
            pip = 0.01 if abs(float(level_meta["price"])) > 10 else 0.0001
            rscore = 1.0 if is_near_round(float(level_meta["price"]),
                                          pip=pip, threshold_pips=3.0) else 0.0
        return (self.W_OWN * own + self.W_D1 * d1 + self.W_W1 * w1 +
                self.W_ROUND * rscore + self.W_MAGNITUDE * mscore)

    def _heavy_weighted_levels(self, weighted_levels: list) -> list[tuple[float, dict]]:
        """gate 通過 (weight>=K AND 上位 percentile) levels を (weight, dict) で返す。"""
        heavy, _reason = self._heavy_weighted_levels_with_reason(weighted_levels)
        return heavy

    def _heavy_weighted_levels_with_reason(self, weighted_levels: list) -> tuple[list[tuple[float, dict]], str]:
        if not weighted_levels:
            return [], "weighted_levels_empty"
        enriched = []
        for lv in weighted_levels:
            if not isinstance(lv, dict):
                continue
            w = self._compute_composite_weight(lv)
            enriched.append((w, lv))
        if not enriched:
            return [], "weighted_levels_invalid"
        enriched.sort(key=lambda x: -x[0])
        n_top = max(1, int(len(enriched) * self.WEIGHT_PERCENTILE_TOP))
        cutoff_weight = enriched[n_top - 1][0]
        abs_pass = [(w, lv) for (w, lv) in enriched if w >= self.K_ABS_THRESHOLD]
        if not abs_pass:
            return [], "weight_abs_reject"
        percentile_pass = [(w, lv) for (w, lv) in abs_pass if w >= cutoff_weight]
        if not percentile_pass:
            return [], "weight_percentile_reject"
        return percentile_pass, "weight_gate_pass"

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if not self._env_enabled():
            return None

        sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        if sym not in self._ALLOWED_SYMBOLS:
            return None

        # ── EUR/USD除外: sr_break_retest 経験則 (EV≈0, スプレッド負担) ──
        if sym in ("EURUSD", "EURGBP"):
            return None

        if ctx.df is None or len(ctx.df) < self.BREAK_LOOKBACK_MAX + 3:
            return None

        signal_bar = ctx.df.iloc[-2]
        signal_bar_time = getattr(signal_bar, "name", None)
        signal_close = float(signal_bar["Close"])
        signal_open = float(signal_bar["Open"])
        signal_atr = max(float(signal_bar.get("atr", ctx.atr)), 1e-9)
        signal_adx = float(signal_bar.get("adx", ctx.adx))
        signal_ema9 = float(signal_bar.get("ema9", ctx.ema9))

        if signal_adx < self.ADX_MIN:
            self._diag(ctx, "reject_adx", signal_bar_time)
            return None

        # ── Weight gate: heavy weighted levels の集合 ──
        self._diag(ctx, "weight_gate_seen", signal_bar_time)
        weighted_levels = (ctx.layer3 or {}).get("sr_weighted_levels", [])
        heavy_levels, gate_reason = self._heavy_weighted_levels_with_reason(weighted_levels)
        self._diag(ctx, gate_reason, signal_bar_time)
        if not heavy_levels:
            return None

        # ── Break + Retest 検出 (各 heavy level について過去 lookback 内で break を探す) ──
        _break_margin = signal_atr * self.BREAK_MARGIN_ATR
        _retest_zone = signal_atr * self.RETEST_ZONE_ATR

        _best_signal = None  # (signal, level_price, composite_w, break_bar_offset, level_dict)

        # closed bar 基準で過去 N 本を見る (df.iloc[-2-offset])
        for composite_w, level_meta in heavy_levels:
            sr_level = float(level_meta["price"])
            for offset in range(self.BREAK_LOOKBACK_MIN,
                                min(self.BREAK_LOOKBACK_MAX + 1, len(ctx.df) - 1)):
                bar = ctx.df.iloc[-(offset + 2)]   # closed bar 基準なので +2
                bar_open = float(bar["Open"])
                bar_close = float(bar["Close"])
                bar_high = float(bar["High"])
                bar_low = float(bar["Low"])
                bar_range = bar_high - bar_low
                bar_body = abs(bar_close - bar_open)
                if bar_range <= 0:
                    continue
                if bar_body / bar_range < self.BREAK_BODY_MIN:
                    continue

                # 上方ブレイク → BUY 候補
                if bar_close > sr_level + _break_margin:
                    # ブレイク前 (1 本前) はまだ break 未達成のはず
                    pre_iloc = -(offset + 3)
                    if abs(pre_iloc) > len(ctx.df):
                        continue
                    pre_bar = ctx.df.iloc[pre_iloc]
                    if float(pre_bar["Close"]) > sr_level + _break_margin:
                        continue  # 既に過去で break 済み

                    # Retest 確認
                    if abs(signal_close - sr_level) <= _retest_zone:
                        if (signal_close > signal_open
                                and signal_close > sr_level
                                and (not self.RETEST_BOUNCE_EMA or signal_close > signal_ema9)):
                            if _best_signal is None or composite_w > _best_signal[2]:
                                _best_signal = ("BUY", sr_level, composite_w, offset, level_meta)
                    break  # この level での最初の break のみ評価

                # 下方ブレイク → SELL 候補
                elif bar_close < sr_level - _break_margin:
                    pre_iloc = -(offset + 3)
                    if abs(pre_iloc) > len(ctx.df):
                        continue
                    pre_bar = ctx.df.iloc[pre_iloc]
                    if float(pre_bar["Close"]) < sr_level - _break_margin:
                        continue

                    if abs(signal_close - sr_level) <= _retest_zone:
                        if (signal_close < signal_open
                                and signal_close < sr_level
                                and (not self.RETEST_BOUNCE_EMA or signal_close < signal_ema9)):
                            if _best_signal is None or composite_w > _best_signal[2]:
                                _best_signal = ("SELL", sr_level, composite_w, offset, level_meta)
                    break

        if _best_signal is None:
            self._diag(ctx, "post_weight_reject_break_retest", signal_bar_time)
            return None

        signal, sr_level, composite_w, break_offset, level_meta = _best_signal

        # HTF 方向矛盾 block
        _htf = ctx.htf or {}
        _agreement = _htf.get("agreement", "mixed")
        if signal == "BUY" and _agreement == "bear":
            self._diag(ctx, "post_weight_reject_htf", signal_bar_time)
            return None
        if signal == "SELL" and _agreement == "bull":
            self._diag(ctx, "post_weight_reject_htf", signal_bar_time)
            return None

        # Per-bar dedup
        if not ctx.backtest_mode:
            _sr_bucket = f"{round(sr_level / max(signal_atr, 1e-9), 2):.2f}"
            dedup_key = (sym, self.name, signal, str(signal_bar_time), _sr_bucket)
            if dedup_key in self._v2_seen_closed_bar_keys:
                self._diag(ctx, "post_weight_reject_dedup", signal_bar_time)
                return None
            self._v2_seen_closed_bar_keys.add(dedup_key)

        # SL/TP 計算 (role reversal SL + next opposite SR cap)
        pip_size = 0.01 if "JPY" in sym else 0.0001
        if signal == "BUY":
            sl = sr_level - signal_atr * self.SL_ATR_BUFFER
            sl = expand_sl_for_round(sl, sr_level, "BUY", pip=pip_size,
                                      expand_factor=1.3, atr=signal_atr)
            sl_dist = ctx.entry - sl
            target_above = [
                float(lv["price"]) if isinstance(lv, dict) else float(lv)
                for lv in ctx.sr_levels
                if (float(lv["price"]) if isinstance(lv, dict)
                    else float(lv)) > ctx.entry + 0.3 * signal_atr
            ]
            rr_tp = ctx.entry + self.TARGET_RR * sl_dist
            tp = min(target_above + [rr_tp]) if target_above else rr_tp
            tp = shift_tp_inside(tp, "BUY", pip=pip_size, shift_pips=3.0)
        else:
            sl = sr_level + signal_atr * self.SL_ATR_BUFFER
            sl = expand_sl_for_round(sl, sr_level, "SELL", pip=pip_size,
                                      expand_factor=1.3, atr=signal_atr)
            sl_dist = sl - ctx.entry
            target_below = [
                float(lv["price"]) if isinstance(lv, dict) else float(lv)
                for lv in ctx.sr_levels
                if (float(lv["price"]) if isinstance(lv, dict)
                    else float(lv)) < ctx.entry - 0.3 * signal_atr
            ]
            rr_tp = ctx.entry - self.TARGET_RR * sl_dist
            tp = max(target_below + [rr_tp]) if target_below else rr_tp
            tp = shift_tp_inside(tp, "SELL", pip=pip_size, shift_pips=3.0)

        # RR 最低保証
        if signal == "BUY":
            risk = ctx.entry - sl
            reward = tp - ctx.entry
        else:
            risk = sl - ctx.entry
            reward = ctx.entry - tp
        if risk <= 0 or reward <= 0:
            self._diag(ctx, "post_weight_reject_bad_risk_reward", signal_bar_time)
            return None
        rr = reward / risk
        if rr < self.MIN_RR:
            self._diag(ctx, "post_weight_reject_rr", signal_bar_time)
            return None

        score = 3.0 + min(2.0, composite_w / 10.0)
        reasons = [
            f"✅ Heavy SR break&retest({sr_level:.5f}, "
            f"composite_weight={composite_w:.2f}, top-30%, abs>={self.K_ABS_THRESHOLD}) continuation",
            f"✅ {signal} シグナル, RR={rr:.2f}",
            f"✅ Break 確認: {break_offset}本前に実体ブレイク (body/range>=0.25)",
            f"✅ Retest 反転: closed_bar={signal_bar_time} で {signal} 整合",
            f"✅ Role reversal SL: {sl:.5f}",
            f"✅ モメンタム OK (closed ADX={signal_adx:.1f}>={self.ADX_MIN})",
            f"✅ SR_WEIGHTED_BREAK v1",
        ]

        self._diag(ctx, "candidate", signal_bar_time)
        return Candidate(
            signal=signal,
            confidence=min(85, int(50 + score * 4)),
            sl=float(sl),
            tp=float(tp),
            reasons=reasons,
            entry_type=self.name,
            score=float(score),
            sr_meta=Candidate.sr_meta_from_price(
                weighted_levels, sr_level, signal_close, signal_atr,
            ),
        )
