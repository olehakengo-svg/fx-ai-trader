"""
SR Weighted Bounce — Heavy wall reversal with composite weight gate (15m daytrade)

設計思想 (2026-05-13 司令塔):
  - sr_detector / indicators が既に持つ touch_count / d1_touch / w1_touch /
    round_score / magnitude を **composite weight として gate** する
  - Family = bounce only (heavy wall rejection → contrarian reversal)
  - 既存 sr_anti_hunt_bounce (Phase 2 BT survivor) の anti-hunt SL geometry を継承
  - Shadow-first: BT に頼らず実トレードで heavy wall 仮説を検証

エントリ条件 (heavy wall rejection bounce):
  1. ペアフィルター: 5 majors (USDJPY/EURUSD/GBPUSD/EURJPY/GBPJPY)
  2. ADX < 30 (レンジ市場、survivor 整合)
  3. 近接 weighted level: |entry - level| < 0.4 ATR
  4. **Weight gate**:
     (a) composite_weight >= K_ABS_THRESHOLD (=3.0) AND
     (b) level が現在検出 weighted_levels の **上位 30% percentile rank** に入る
  5. 直近 2 本で SR 越えの hunt-style wick が無い (CONFIRMATION_BARS=2)
  6. 反転足確認: signal 方向と整合する実体 + BB%B 整合
  7. v2_redesign パターン: closed bar (df.iloc[-2]) で signal 確定、per-bar dedup

SL = level − sign × (P90_excursion + 0.5 × ATR)  ※anti-hunt placement、
     P90 値は survivor の 2026-Q1 calibration を流用、Shadow 蓄積後 re-audit 予定
TP = min(next_opposite_SR, entry + RR × SL_dist) で early target、RR=2.0、MIN_RR=1.5

composite_weight = 1.0 × own_touch + 3.0 × d1_touch + 5.0 × w1_touch +
                   2.0 × round_score + 1.5 × magnitude_score
"""
from __future__ import annotations
from typing import Optional
import os

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from modules.round_number import (
    expand_sl_for_round, shift_tp_inside, is_near_round,
)


class SrWeightedBounce(StrategyBase):

    name = "sr_weighted_bounce"
    mode = "daytrade"
    enabled = False   # Shadow-only スタート、env SR_WEIGHTED_BOUNCE_ENABLE=1 で有効化
    strategy_type = "MR"

    # 5 majors 全部 — Shadow data で per-pair edge を実測判定
    _ALLOWED_SYMBOLS = frozenset({"USDJPY", "EURUSD", "GBPUSD", "EURJPY", "GBPJPY"})

    SR_PROXIMITY_ATR = 0.4
    ADX_MAX = 30
    CONFIRMATION_BARS = 2

    # Composite weight gate (Wave 1 固定、post-hoc selection 罠回避のため sweep しない)
    K_ABS_THRESHOLD = 3.0
    WEIGHT_PERCENTILE_TOP = 0.30   # 上位 30% (rank <= len*0.3)

    # Composite weight 係数 (audit v2 と同式、Wave 1 固定)
    W_OWN = 1.0
    W_D1 = 3.0
    W_W1 = 5.0
    W_ROUND = 2.0
    W_MAGNITUDE = 1.5

    # Phase 2 audit (k=2.0) 由来 P90 excursion (pip) — 2026-Q1 calibration
    # Shadow N>=30 蓄積後に再 audit して per-pair update する
    _P90_EXCURSION_PIP = {
        "EURUSD": 37.0,
        "GBPUSD": 53.0,
        "USDJPY": 50.0,
        "EURJPY": 49.0,
        "GBPJPY": 59.0,
    }
    SL_ATR_BUFFER = 0.5
    SL_FALLBACK_ATR = 1.5

    MIN_RR = 1.5
    TARGET_RR = 2.0

    MAX_HOLD_BARS = 12
    _v2_seen_closed_bar_keys: set[tuple[str, str, str, str]] = set()

    @classmethod
    def reset_dedup_state(cls):
        cls._v2_seen_closed_bar_keys.clear()

    def _compute_composite_weight(self, level_meta: dict) -> float:
        """sr_weighted_levels の 1 level dict から composite_weight を計算。

        level_meta keys (sr_detector / indicators.find_sr_levels_weighted 由来):
          own_touch / touch_count / touches: int
          d1_touch: int (optional, default 0)
          w1_touch: int (optional, default 0)
          round_score: float in [0,1] (optional, default 0 で is_near_round から推定)
          magnitude_score: float in [0,1] (optional)
          price: float
        """
        own = int(level_meta.get("own_touch",
                                 level_meta.get("touch_count",
                                                level_meta.get("touches", 0))) or 0)
        d1 = int(level_meta.get("d1_touch", 0) or 0)
        w1 = int(level_meta.get("w1_touch", 0) or 0)
        rscore = float(level_meta.get("round_score", 0.0) or 0.0)
        mscore = float(level_meta.get("magnitude_score", 0.0) or 0.0)
        # round_score が無ければ price から推定
        if "round_score" not in level_meta and "price" in level_meta:
            pip = 0.01 if abs(float(level_meta["price"])) > 10 else 0.0001
            rscore = 1.0 if is_near_round(float(level_meta["price"]),
                                          pip=pip, threshold_pips=3.0) else 0.0
        return (self.W_OWN * own + self.W_D1 * d1 + self.W_W1 * w1 +
                self.W_ROUND * rscore + self.W_MAGNITUDE * mscore)

    def _select_heavy_level(self, ctx: SignalContext, weighted_levels: list,
                            signal_price: float, atr: float) -> Optional[dict]:
        """weighted_levels から composite_weight gate 通過の nearest level を返す。

        gate:
          (a) composite_weight >= K_ABS_THRESHOLD
          (b) level が現在 levels の上位 WEIGHT_PERCENTILE_TOP に入る
          (c) |signal_price - level.price| < SR_PROXIMITY_ATR * atr
        """
        if not weighted_levels:
            return None
        # 全 level の composite_weight 計算
        enriched = []
        for lv in weighted_levels:
            if not isinstance(lv, dict):
                continue
            w = self._compute_composite_weight(lv)
            enriched.append((w, lv))
        if not enriched:
            return None
        # 上位 30% の cutoff weight 算出
        enriched.sort(key=lambda x: -x[0])
        n_top = max(1, int(len(enriched) * self.WEIGHT_PERCENTILE_TOP))
        cutoff_weight = enriched[n_top - 1][0]
        # gate 通過 candidates
        proximity = self.SR_PROXIMITY_ATR * atr
        candidates = [
            (w, lv) for (w, lv) in enriched
            if w >= self.K_ABS_THRESHOLD
            and w >= cutoff_weight
            and abs(signal_price - float(lv["price"])) < proximity
        ]
        if not candidates:
            return None
        # nearest
        best = min(candidates, key=lambda x: abs(signal_price - float(x[1]["price"])))
        out = dict(best[1])
        out["__composite_weight__"] = best[0]
        return out

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if os.environ.get("SR_WEIGHTED_BOUNCE_ENABLE") != "1":
            return None

        sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        if sym not in self._ALLOWED_SYMBOLS:
            return None
        if ctx.df is None or len(ctx.df) < self.CONFIRMATION_BARS + 2:
            return None

        # v2 redesign パターン: closed bar (df.iloc[-2]) で signal 確定
        signal_bar = ctx.df.iloc[-2]
        signal_bar_time = getattr(signal_bar, "name", None)
        signal_close = float(signal_bar["Close"])
        signal_open = float(signal_bar["Open"])
        signal_atr = max(float(signal_bar.get("atr", ctx.atr)), 1e-9)
        signal_adx = float(signal_bar.get("adx", ctx.adx))
        signal_bbpb = float(signal_bar.get("bb_pband", ctx.bbpb))

        if signal_adx >= self.ADX_MAX:
            return None

        # ── Weight gate: layer3.sr_weighted_levels から heavy level 選択 ──
        weighted_levels = (ctx.layer3 or {}).get("sr_weighted_levels", [])
        if not weighted_levels:
            return None
        heavy = self._select_heavy_level(ctx, weighted_levels, signal_close, signal_atr)
        if heavy is None:
            return None

        nearest_level = float(heavy["price"])
        composite_w = float(heavy["__composite_weight__"])

        # bounce 方向決定
        if signal_close > nearest_level:
            side = "support"
            signal = "BUY"
        else:
            side = "resistance"
            signal = "SELL"

        # 反転足確認
        if signal == "BUY" and signal_close <= signal_open:
            return None
        if signal == "SELL" and signal_close >= signal_open:
            return None

        # 直近 2 本に hunt-style wick が無いことを確認
        if not self._confirmed_no_recent_hunt(ctx, nearest_level, side, end_iloc=-1,
                                              atr_override=signal_atr):
            return None

        # SL/TP 計算 (sr_anti_hunt_bounce 流用)
        sl, tp = self._compute_sl_tp(ctx, nearest_level, signal, sym,
                                     atr_override=signal_atr)
        if sl is None or tp is None:
            return None

        if signal == "BUY":
            risk = ctx.entry - sl
            reward = tp - ctx.entry
        else:
            risk = sl - ctx.entry
            reward = ctx.entry - tp
        if risk <= 0 or reward <= 0:
            return None
        rr = reward / risk
        if rr < self.MIN_RR:
            return None

        # Per-bar dedup (v2 redesign パターン)
        if not ctx.backtest_mode:
            dedup_key = (sym, self.name, str(signal_bar_time), signal)
            if dedup_key in self._v2_seen_closed_bar_keys:
                return None
            self._v2_seen_closed_bar_keys.add(dedup_key)

        score = 3.0 + min(2.0, composite_w / 10.0)   # weight が大きいほど +score (上限 +2.0)
        reasons = [
            f"✅ Heavy SR rejection({nearest_level:.5f}, "
            f"composite_weight={composite_w:.2f}, top-30%, abs>={self.K_ABS_THRESHOLD}) bounce",
            f"✅ {side}側、{signal} シグナル, RR={rr:.2f}",
            f"✅ Anti-hunt SL: {sl:.5f}（P90+ATR バッファ, 2026-Q1 calibration）",
            f"✅ レジーム OK (closed ADX={signal_adx:.1f}<{self.ADX_MAX})",
            f"✅ SR_WEIGHTED_BOUNCE v1: closed_bar_time={signal_bar_time} で確定し次バー約定",
        ]
        if signal == "BUY" and signal_bbpb < 0.3:
            score += 0.5
            reasons.append(f"✅ BB下限一致(closed BB%B={signal_bbpb:.2f})")
        elif signal == "SELL" and signal_bbpb > 0.7:
            score += 0.5
            reasons.append(f"✅ BB上限一致(closed BB%B={signal_bbpb:.2f})")

        return Candidate(
            signal=signal,
            confidence=min(100, int(score * 20)),
            sl=float(sl),
            tp=float(tp),
            reasons=reasons,
            entry_type=self.name,
            score=float(score),
            sr_meta=Candidate.sr_meta_from_price(
                weighted_levels, nearest_level, signal_close, signal_atr,
            ),
        )

    def _confirmed_no_recent_hunt(self, ctx: SignalContext, level: float, side: str,
                                   end_iloc: int | None = None,
                                   atr_override: float | None = None) -> bool:
        if ctx.df is None or len(ctx.df) < self.CONFIRMATION_BARS + 1:
            return False
        if end_iloc is None:
            recent = ctx.df.iloc[-(self.CONFIRMATION_BARS + 1):-1]
        else:
            start_iloc = end_iloc - self.CONFIRMATION_BARS
            recent = ctx.df.iloc[start_iloc:end_iloc]
        atr = max(atr_override if atr_override is not None else ctx.atr, 1e-9)
        threshold = 1.0 * atr
        for _, row in recent.iterrows():
            high = float(row["High"])
            low = float(row["Low"])
            close = float(row["Close"])
            if side == "resistance":
                if high > level and close < level and (high - level) > threshold:
                    return False
            else:
                if low < level and close > level and (level - low) > threshold:
                    return False
        return True

    def _compute_sl_tp(self, ctx: SignalContext, level: float,
                       signal: str, sym: str, atr_override: float | None = None):
        atr = max(atr_override if atr_override is not None else ctx.atr, 1e-9)
        pip_size = 0.01 if "JPY" in sym else 0.0001

        p90_pip = self._P90_EXCURSION_PIP.get(sym)
        if p90_pip is not None:
            p90_price = p90_pip * pip_size
        else:
            p90_price = self.SL_FALLBACK_ATR * atr

        sl_buffer = p90_price + self.SL_ATR_BUFFER * atr

        if signal == "BUY":
            sl = level - sl_buffer
            sl = expand_sl_for_round(sl, level, "BUY", pip=pip_size,
                                       expand_factor=1.3, atr=atr)
            sl_dist = ctx.entry - sl
            target_above = [
                float(lv["price"]) if isinstance(lv, dict) else float(lv)
                for lv in ctx.sr_levels
                if (float(lv["price"]) if isinstance(lv, dict)
                    else float(lv)) > ctx.entry + 0.3 * atr
            ]
            rr_tp = ctx.entry + self.TARGET_RR * sl_dist
            tp = min(target_above + [rr_tp]) if target_above else rr_tp
            tp = shift_tp_inside(tp, "BUY", pip=pip_size, shift_pips=3.0)
        else:
            sl = level + sl_buffer
            sl = expand_sl_for_round(sl, level, "SELL", pip=pip_size,
                                       expand_factor=1.3, atr=atr)
            sl_dist = sl - ctx.entry
            target_below = [
                float(lv["price"]) if isinstance(lv, dict) else float(lv)
                for lv in ctx.sr_levels
                if (float(lv["price"]) if isinstance(lv, dict)
                    else float(lv)) < ctx.entry - 0.3 * atr
            ]
            rr_tp = ctx.entry - self.TARGET_RR * sl_dist
            tp = max(target_below + [rr_tp]) if target_below else rr_tp
            tp = shift_tp_inside(tp, "SELL", pip=pip_size, shift_pips=3.0)

        return sl, tp
