"""SR + Fibonacci Confluence — SR/Fibコンフルエンス (15m足)"""
import os

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from modules.round_number import shift_tp_inside, round_confluence_boost, is_near_round
from typing import Optional


class SrFibConfluence(StrategyBase):
    name = "sr_fib_confluence"
    mode = "daytrade"

    # チューナブルパラメータ
    adx_min = 20           # ADXトレンド閾値（12→20: 学術水準復元）
    ema_score_threshold = 0.28
    structured_proximity_atr = 0.35

    _v2_seen_signal_keys: set = set()

    @classmethod
    def reset_dedup_state(cls):
        cls._v2_seen_signal_keys.clear()

    def _redesign_v2_enabled(self) -> bool:
        return os.environ.get("SR_FIB_CONFLUENCE_REDESIGN_V2") == "1"

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if self._redesign_v2_enabled():
            return self._evaluate_redesign_v2(ctx)
        return self._evaluate_legacy(ctx)

    def _evaluate_legacy(self, ctx: SignalContext) -> Optional[Candidate]:
        if ctx.adx < self.adx_min:
            return None

        signal = None
        score = 0.0
        reasons = []

        # SR/Fib情報: DT関数の蓄積reasonsまたはlayer3から取得
        _all_reasons = ctx.layer3.get("dt_reasons", ctx.layer3.get("reasons", []))
        _has_sr_fib = any("Fib" in r or "フィボ" in r for r in _all_reasons)
        _has_ob = any("OB" in r or "オーダーブロック" in r for r in _all_reasons)

        if not _has_sr_fib and not _has_ob:
            return None

        # EMAスコア: DT関数から渡される複合スコア
        ema_score = ctx.ema_score if ctx.ema_score != 0.0 else (ctx.ema9 - ctx.ema21) / max(ctx.atr, 1e-8)

        if ema_score > self.ema_score_threshold and ctx.ema9 > ctx.ema21:
            signal = "BUY"
            score = 3.0 + abs(ema_score) * 2
            reasons.append("✅ SR/Fibコンフルエンス + EMA順列確認")
            reasons.extend([r for r in _all_reasons if "✅" in r][:3])
            tp = ctx.entry + ctx.atr7 * 2.0
            sl = ctx.entry - ctx.atr7 * 1.0
        elif ema_score < -self.ema_score_threshold and ctx.ema9 < ctx.ema21:
            signal = "SELL"
            score = 3.0 + abs(ema_score) * 2
            reasons.append("✅ SR/Fibコンフルエンス + EMA逆順列確認")
            reasons.extend([r for r in _all_reasons if "✅" in r][:3])
            tp = ctx.entry - ctx.atr7 * 2.0
            sl = ctx.entry + ctx.atr7 * 1.0

        if signal is None:
            return None

        # RNR: TP shift away from round numbers
        pip = 0.01 if "JPY" in ctx.symbol.upper() else 0.0001
        tp = shift_tp_inside(tp, signal, pip=pip, shift_pips=3.0)
        # entry が round number 近傍なら confidence boost (psychological double-confluence)
        if is_near_round(ctx.entry, pip=pip, threshold_pips=3.0):
            score += 0.3
            reasons.append("✅ Round number 近傍コンフルエンス")
            # SL を round number 越えに更に深く
            if signal == "BUY":
                sl -= 0.3 * ctx.atr7
            else:
                sl += 0.3 * ctx.atr7

        _entry_type = "sr_fib_confluence" if _has_sr_fib else "ob_retest"
        conf = int(min(80, 45 + score * 4))
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=_entry_type, score=score)

    def _get_structured_confluence(self, ctx: SignalContext, entry: float,
                                   atr: float) -> Optional[dict]:
        layer3 = ctx.layer3 or {}
        tol = max(atr, 1e-8) * self.structured_proximity_atr

        blocks = []
        for key in ("sr_fib", "confluence", "structured_confluence"):
            value = layer3.get(key)
            if isinstance(value, dict):
                blocks.append(value)

        flat = {
            "fib_level": layer3.get("fib_level"),
            "sr_level": layer3.get("sr_level"),
            "ob_zone_low": layer3.get("ob_zone_low"),
            "ob_zone_high": layer3.get("ob_zone_high"),
            "confluence_type": layer3.get("confluence_type"),
            "signal_bar_time": layer3.get("signal_bar_time"),
        }
        if any(v is not None for v in flat.values()):
            blocks.append(flat)

        for block in blocks:
            ctype = str(block.get("confluence_type") or block.get("kind") or "structured")
            fib_level = block.get("fib_level", block.get("level"))
            if fib_level is not None:
                fib_level = float(fib_level)
                if abs(entry - fib_level) <= tol:
                    return {
                        "kind": ctype if "fib" in ctype.lower() else "sr_fib",
                        "entry_type": "sr_fib_confluence",
                        "level": fib_level,
                        "distance_atr": abs(entry - fib_level) / max(atr, 1e-8),
                        "signal_bar_time": block.get("signal_bar_time"),
                    }

            ob_low = block.get("ob_zone_low", block.get("low"))
            ob_high = block.get("ob_zone_high", block.get("high"))
            if ob_low is not None and ob_high is not None:
                ob_low = float(ob_low)
                ob_high = float(ob_high)
                zone_low, zone_high = min(ob_low, ob_high), max(ob_low, ob_high)
                if zone_low <= entry <= zone_high:
                    return {
                        "kind": ctype if "ob" in ctype.lower() else "ob_retest",
                        "entry_type": "ob_retest",
                        "zone_low": zone_low,
                        "zone_high": zone_high,
                        "signal_bar_time": block.get("signal_bar_time"),
                    }

        return None

    def _evaluate_redesign_v2(self, ctx: SignalContext) -> Optional[Candidate]:
        signal_df = ctx.df
        if signal_df is None or len(signal_df) < 3:
            return None
        if not ctx.backtest_mode:
            signal_df = signal_df.iloc[:-1]
            if len(signal_df) < 3:
                return None

        signal_row = signal_df.iloc[-1]
        signal_prev = signal_df.iloc[-2]
        signal_bar_time = getattr(signal_row, "name", None)
        signal_atr = float(signal_row.get("atr", ctx.atr))
        signal_atr7 = float(signal_row.get("atr7", signal_atr))
        signal_adx = float(signal_row.get("adx", ctx.adx))
        signal_ema9 = float(signal_row.get("ema9", ctx.ema9))
        signal_ema21 = float(signal_row.get("ema21", ctx.ema21))
        prev_ema9 = float(signal_prev.get("ema9", ctx.ema9_prev))
        prev_ema21 = float(signal_prev.get("ema21", ctx.ema21_prev))

        if signal_adx < self.adx_min:
            return None

        ema_score = (signal_ema9 - signal_ema21) / max(signal_atr, 1e-8)
        if ctx.backtest_mode and ctx.ema_score != 0.0:
            ema_score = ctx.ema_score
        if signal_ema9 == signal_ema21:
            ema_score = (prev_ema9 - prev_ema21) / max(signal_atr, 1e-8)

        confluence = self._get_structured_confluence(ctx, ctx.entry, signal_atr)
        if confluence is None:
            return None

        signal = None
        score = 0.0
        reasons = []
        if ema_score > self.ema_score_threshold and signal_ema9 > signal_ema21:
            signal = "BUY"
            score = 3.0 + abs(ema_score) * 2
            tp = ctx.entry + signal_atr7 * 2.0
            sl = ctx.entry - signal_atr7 * 1.0
            reasons.append("✅ SR_FIB_CONFLUENCE_REDESIGN_V2 structured confluence + EMA順列")
        elif ema_score < -self.ema_score_threshold and signal_ema9 < signal_ema21:
            signal = "SELL"
            score = 3.0 + abs(ema_score) * 2
            tp = ctx.entry - signal_atr7 * 2.0
            sl = ctx.entry + signal_atr7 * 1.0
            reasons.append("✅ SR_FIB_CONFLUENCE_REDESIGN_V2 structured confluence + EMA逆順列")

        if signal is None:
            return None

        dedup_bar = confluence.get("signal_bar_time") or signal_bar_time
        dedup_key = (
            ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", ""),
            self.name,
            signal,
            str(dedup_bar),
            confluence["kind"],
        )
        if dedup_key in self._v2_seen_signal_keys:
            return None

        if "level" in confluence:
            reasons.append(
                f"✅ structured {confluence['kind']}: level={confluence['level']:.5f} "
                f"distance={confluence['distance_atr']:.2f}ATR"
            )
        else:
            reasons.append(
                f"✅ structured {confluence['kind']}: "
                f"OB zone {confluence['zone_low']:.5f}-{confluence['zone_high']:.5f}"
            )
        reasons.append(f"✅ closed_signal_bar={dedup_bar}")

        pip = 0.01 if "JPY" in ctx.symbol.upper() else 0.0001
        tp = shift_tp_inside(tp, signal, pip=pip, shift_pips=3.0)
        if is_near_round(ctx.entry, pip=pip, threshold_pips=3.0):
            score += 0.3
            reasons.append("✅ Round number 近傍コンフルエンス")
            if signal == "BUY":
                sl -= 0.3 * signal_atr7
            else:
                sl += 0.3 * signal_atr7

        self._v2_seen_signal_keys.add(dedup_key)
        conf = int(min(80, 45 + score * 4))
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=confluence["entry_type"], score=score)
