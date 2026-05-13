---
id: 20260513-2300-sr-weighted-break-shadow-strategy-new
title: "[SR-Redesign] sr_weighted_break 新戦略 Shadow-only 投入 — heavy wall breakout follow-through with composite weight gate"
owner: codex
status: queued
priority: P1
created_at: 2026-05-13T23:00:00+0900
roadmap_gate: "sr_weighted_bounce (commit 25a1617) で bounce family を Shadow 投入済。本タスクは family 分離思想 (memory: feedback_sr_weight_is_essence) の break family を完成させる。heavy wall を突破した bar の retest で順張りエントリ、role reversal SL geometry。既存 sr_break_retest (smoking gun: MIN_CLUSTERS=1) には一切触らない。"
rule: pre-reg
related:
  - strategies/daytrade/sr_weighted_bounce.py
  - strategies/daytrade/sr_break_retest.py
  - strategies/daytrade/__init__.py
  - strategies/base.py
  - strategies/context.py
  - modules/sr_detector.py
  - modules/indicators.py
  - modules/round_number.py
---

# 0. 背景

## 0.1 family 分離思想 (memory: feedback_sr_weight_is_essence)

> 重い壁の **突破=継続/bounce=反転** で 2 family 分離。bounce と break を 1 戦略に混ぜない (EV 相殺するため)。

`sr_weighted_bounce` (bounce family) は commit `25a1617` で Shadow 投入済。本タスクは **break family** を完成させる。

## 0.2 既存 `sr_break_retest` との差別化

| 項目 | 既存 sr_break_retest | 新規 sr_weighted_break |
|---|---|---|
| Level 取得 | 独自 Williams Fractal 検出 (`MIN_CLUSTERS=1` smoking gun) | `layer3.sr_weighted_levels` を消費、composite weight gate |
| Weight gate | なし (touches≥3 で +0.5 bonus のみ) | **composite_weight ≥ 3.0 AND 上位 30% percentile** |
| Family 分離 | break 単独 | break 単独 (bounce は sr_weighted_bounce) |
| Detector | Williams Fractal local | sr_detector / find_sr_levels_weighted (production と同経路) |

既存 `sr_break_retest` には **一切触らない**。並走して shadow data を蓄積し、後日 cell-level 比較で勝者を決める。

# 1. 目的

`strategies/daytrade/sr_weighted_break.py` を新規作成し、Shadow-only (Tier 0 audit_only) で 5 majors 全走。`sr_weighted_bounce` と family pair を成し、heavy wall の **両方向エッジ** を実トレードで検証。

# 2. 仕様

## 2.1 ファイル新規作成: `strategies/daytrade/sr_weighted_break.py`

```python
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
import os

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from modules.round_number import (
    expand_sl_for_round, shift_tp_inside, is_near_round,
)


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

    @classmethod
    def reset_dedup_state(cls):
        cls._v2_seen_closed_bar_keys.clear()

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
        if not weighted_levels:
            return []
        enriched = []
        for lv in weighted_levels:
            if not isinstance(lv, dict):
                continue
            w = self._compute_composite_weight(lv)
            enriched.append((w, lv))
        if not enriched:
            return []
        enriched.sort(key=lambda x: -x[0])
        n_top = max(1, int(len(enriched) * self.WEIGHT_PERCENTILE_TOP))
        cutoff_weight = enriched[n_top - 1][0]
        return [
            (w, lv) for (w, lv) in enriched
            if w >= self.K_ABS_THRESHOLD and w >= cutoff_weight
        ]

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
            return None

        # ── Weight gate: heavy weighted levels の集合 ──
        weighted_levels = (ctx.layer3 or {}).get("sr_weighted_levels", [])
        heavy_levels = self._heavy_weighted_levels(weighted_levels)
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
            return None

        signal, sr_level, composite_w, break_offset, level_meta = _best_signal

        # HTF 方向矛盾 block
        _htf = ctx.htf or {}
        _agreement = _htf.get("agreement", "mixed")
        if signal == "BUY" and _agreement == "bear":
            return None
        if signal == "SELL" and _agreement == "bull":
            return None

        # Per-bar dedup
        if not ctx.backtest_mode:
            _sr_bucket = f"{round(sr_level / max(signal_atr, 1e-9), 2):.2f}"
            dedup_key = (sym, self.name, signal, str(signal_bar_time), _sr_bucket)
            if dedup_key in self._v2_seen_closed_bar_keys:
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
            return None
        rr = reward / risk
        if rr < self.MIN_RR:
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
```

## 2.2 Engine registration: `strategies/daytrade/__init__.py`

import セクション (sr_weighted_bounce の直下に追加):

```python
# v11 (2026-05-13): SR Weighted Break — heavy wall breakout retest with composite weight gate (Shadow-only, break family pair of sr_weighted_bounce)
from strategies.daytrade.sr_weighted_break import SrWeightedBreak
```

`self.strategies` list (sr_weighted_bounce の直下に追加):

```python
SrWeightedBounce(),            # SR Weighted Bounce v1: heavy wall + composite weight gate (Shadow-only 2026-05-13)
SrWeightedBreak(),             # 🆕 SR Weighted Break v1: heavy wall breakout retest (Shadow-only 2026-05-13, break family pair)
```

`evaluate_all` 内の env gate (sr_weighted_bounce と同じ pattern で env=1 のみ評価対象):

既存の bounce で導入された if-block を **拡張** または **新 block 追加**。最小実装:

```python
# 既存 (sr_weighted_bounce 用):
if (os.environ.get("SR_WEIGHTED_BOUNCE_ENABLE") != "1"
        and strategy.name == "sr_weighted_bounce"):
    continue

# 追加 (sr_weighted_break 用、別 strategy.name で同パターン):
if (os.environ.get("SR_WEIGHTED_BREAK_ENABLE") != "1"
        and strategy.name == "sr_weighted_break"):
    continue
```

SHADOW_ALWAYS_STRATEGIES env block の末尾に追加:

```python
if (os.environ.get("SR_WEIGHTED_BREAK_ENABLE") == "1"
        and os.environ.get("SR_WEIGHTED_BREAK_SHADOW_PROMOTE") == "1"):
    _shadow_always = _shadow_always | {"sr_weighted_break"}
```

## 2.3 KB wiki: `knowledge-base/wiki/strategies/sr-weighted-break.md`

```markdown
---
name: sr_weighted_break
mode: daytrade
status: shadow_only_audit_only
created_at: 2026-05-13
strategy_type: pullback
family: break
family_pair: sr_weighted_bounce (bounce family)
parent_lineage: sr_break_retest (smoking gun MIN_CLUSTERS=1 を是正、weight gate 化)
tier: 0 (audit_only)
---

# SR Weighted Break v1

## 思想
SR 水平線の重み (touch_count + D1/W1 confluence + round_number + rejection magnitude)
で gate された **heavy wall breakout retest**。`sr_weighted_bounce` と family pair を
組み、heavy wall の両方向エッジ (反発 vs 突破) を Shadow で並走検証。

## 司令塔仮説 (2026-05-13)
- 既存 sr_break_retest は Williams Fractal 独自検出 + MIN_CLUSTERS=1 で軽い壁も拾う
- 本戦略は production と同 detector (sr_detector / find_sr_levels_weighted) を消費し、
  composite weight gate で母集団を絞り込む
- 「重い壁ほど breakout 後の retest follow-through が強い」を実トレードで検証

## エントリ条件
| # | 条件 | 値 |
|---|---|---|
| 1 | ペア | USDJPY/GBPUSD/EURJPY/GBPJPY (EUR/USD/EUR/GBP 除外) |
| 2 | ADX | >= 20 |
| 3 | composite_weight | >= 3.0 |
| 4 | weight percentile | 上位 30% |
| 5 | Break body | >= 25% range |
| 6 | Break margin | close > level + 0.05 ATR (BUY) |
| 7 | Retest zone | < 0.5 ATR from broken level |
| 8 | Retest EMA9 confirmation | close > EMA9 (BUY) |
| 9 | HTF 方向 | 矛盾 (bear/bull) なら block |

## SL/TP
- SL = broken_level ∓ 0.3 ATR (role reversal placement)
- TP = min(next opposite SR, entry + 2.0 × SL_dist)、MIN_RR=1.5

## Shadow promotion gate (Tier 0 → 1)
- N >= 30 trades
- Wilson_lo (95% LB, Bonferroni m=2 (bounce/break family-wise)) >= 0.40
- 単一年 WR>=90% 集中 flag が出ていない

## Live promotion gate (Tier 1 → 2)
- N >= 100 trades
- Bonferroni m=2 再現性
- WF 3+ folds pos_ratio >= 0.8
- Kelly >= 0.20

## 起源 / 関連
- Family pair: sr_weighted_bounce ([wiki/strategies/sr-weighted-bounce.md](sr-weighted-bounce.md))
- 親 lineage: sr_break_retest ([wiki/strategies/sr-break-retest.md](sr-break-retest.md))
  → MIN_CLUSTERS=1 smoking gun を是正
- Decision: `wiki/decisions/2026-05-13-sr-weighted-break-shadow-injection.md` (生成予定)
- 経緯: `reports/sr_phase2_vs_audit_v2_forensic_2026-05-13.md`
```

## 2.4 Decision doc: `.ai/decisions/2026-05-13-sr-weighted-break-shadow-injection.md`

```markdown
---
id: 2026-05-13-sr-weighted-break-shadow-injection
title: SR Weighted Break Shadow Injection — break family pair to sr_weighted_bounce
verdict: APPROVE
rule: R1
related_task: 20260513-2300-sr-weighted-break-shadow-strategy-new
audit_at: 2026-05-13T23:00:00+0900
auditor: Claude (司令塔)
---

# 監査 input
- sr_weighted_bounce Shadow 投入済 (commit 25a1617)
- Family 分離思想 (memory: feedback_sr_weight_is_essence): bounce と break を別戦略に
- 既存 sr_break_retest の smoking gun (MIN_CLUSTERS=1) は是正せず、新戦略で並走

# 規律 checklist
| 規律 | 状態 |
|---|---|
| 既存 SR 戦略を破壊しない | ✅ 新規ファイルのみ |
| Shadow-first (BT に頼らない) | ✅ memory feedback_shadow_first_quant_architecture 準拠 |
| Wave 1 でパラメータ sweep しない | ✅ 全 param 固定 |
| Family 分離 | ✅ break only (bounce は sr_weighted_bounce) |
| Live PnL 影響 | ✅ ゼロ (env=0 デフォルト) |
| KB sync | ✅ wiki + decision 同コミット |
| Composite weight 係数整合 | ✅ bounce と同式 (1:3:5:2:1.5) |

# Shadow → Live promotion gate (pre-reg)
N>=30 + Wilson_lo>=0.40 (Bonferroni m=2 補正、family-wise) + WF 3+ folds pos_ratio>=0.8

# 残懸念
- bounce と break で同一 heavy level が両方発火する可能性
  (例: 突破直後の retest BUY と、retest 失敗で反発 SELL が連続する)
  → cell stats で per-pair-direction observable、Phase 2 で family interaction 分析
- ADX>=20 が緩い可能性、Shadow 蓄積後に閾値 audit
- EUR/USD / EUR/GBP 除外は sr_break_retest 経験則の引継ぎ、Shadow 蓄積後に re-evaluate
```

## 2.5 Unit tests: `tests/test_sr_weighted_break.py` (新規)

```python
"""Unit tests for sr_weighted_break strategy."""
import os
import pandas as pd
from strategies.daytrade.sr_weighted_break import SrWeightedBreak


def _enable():
    os.environ["SR_WEIGHTED_BREAK_ENABLE"] = "1"


def _disable():
    os.environ.pop("SR_WEIGHTED_BREAK_ENABLE", None)


def test_composite_weight_formula():
    s = SrWeightedBreak()
    meta = {
        "price": 110.50,
        "own_touch": 3,
        "d1_touch": 2,
        "w1_touch": 1,
        "round_score": 0.5,
        "magnitude_score": 0.6,
    }
    expected = 1.0*3 + 3.0*2 + 5.0*1 + 2.0*0.5 + 1.5*0.6  # = 15.9
    assert abs(s._compute_composite_weight(meta) - expected) < 1e-9


def test_heavy_weighted_levels_gate():
    s = SrWeightedBreak()
    levels = [
        {"price": 110.50, "own_touch": 10, "d1_touch": 3, "w1_touch": 1,
         "round_score": 0.5, "magnitude_score": 0.5},
        {"price": 110.40, "own_touch": 2, "d1_touch": 0, "w1_touch": 0,
         "round_score": 0.0, "magnitude_score": 0.0},
        {"price": 111.00, "own_touch": 1, "d1_touch": 0, "w1_touch": 0,
         "round_score": 0.0, "magnitude_score": 0.0},
    ]
    heavy = s._heavy_weighted_levels(levels)
    # 上位 30% = 1 level (= max(1, int(3*0.3)) = 1)、かつ weight>=3.0
    assert len(heavy) == 1
    assert heavy[0][1]["price"] == 110.50


def test_heavy_weighted_levels_empty():
    s = SrWeightedBreak()
    assert s._heavy_weighted_levels([]) == []


def test_evaluate_returns_none_when_env_disabled():
    _disable()
    s = SrWeightedBreak()
    class Ctx:
        pass
    ctx = Ctx()
    ctx.symbol = "USDJPY=X"
    assert s.evaluate(ctx) is None


def test_strategy_disabled_by_default():
    s = SrWeightedBreak()
    assert s.enabled is False


def test_eurusd_and_eurgbp_excluded():
    _enable()
    s = SrWeightedBreak()

    class Ctx:
        pass

    ctx = Ctx()
    ctx.symbol = "EURUSD=X"
    ctx.df = None  # 早期 return される
    assert s.evaluate(ctx) is None

    ctx2 = Ctx()
    ctx2.symbol = "EURGBP=X"
    ctx2.df = None
    assert s.evaluate(ctx2) is None
    _disable()
```

## 2.6 Integration test: `tests/test_sr_weighted_break_integration.py`

```python
"""Integration test: sr_weighted_break minimal signal generation sanity."""
import os
import pandas as pd
import pytest
from strategies.daytrade.sr_weighted_break import SrWeightedBreak


@pytest.fixture
def enable_env():
    os.environ["SR_WEIGHTED_BREAK_ENABLE"] = "1"
    yield
    os.environ.pop("SR_WEIGHTED_BREAK_ENABLE", None)


def test_evaluate_runs_without_error_on_synthetic_data(enable_env):
    """Build minimal synthetic ctx that includes a break-and-retest setup near a heavy level.

    Verify evaluate returns Candidate or None without exception.
    """
    from strategies.context import SignalContext

    idx = pd.date_range("2026-01-01", periods=20, freq="15min", tz="UTC")
    # Setup: SR=110.40, break on bar -8 (close=110.55 > 110.40+margin), retest current at 110.42
    close_series = [110.30] * 10 + [110.55] * 6 + [110.45, 110.43, 110.42, 110.42]
    open_series  = [110.30] * 10 + [110.40] * 6 + [110.50, 110.45, 110.43, 110.41]
    high_series = [c + 0.02 for c in close_series]
    low_series = [o - 0.02 for o in open_series]

    df = pd.DataFrame({
        "Open":  open_series,
        "High":  high_series,
        "Low":   low_series,
        "Close": close_series,
        "atr":   [0.10] * 20,
        "atr7":  [0.10] * 20,
        "adx":   [25.0] * 20,
        "adx_pos": [25.0] * 20,
        "adx_neg": [22.0] * 20,
        "ema9":  [110.40] * 20,
        "ema21": [110.38] * 20,
        "ema50": [110.35] * 20,
        "ema200":[110.30] * 20,
        "macd_hist": [0.001] * 20,
        "bb_pband": [0.5] * 20,
        "bb_upper": [110.60] * 20,
        "bb_mid": [110.45] * 20,
        "bb_lower": [110.30] * 20,
        "bb_width": [0.01] * 20,
        "rsi": [50.0] * 20,
    }, index=idx)

    heavy_level = {
        "price": 110.40,
        "own_touch": 8,
        "d1_touch": 2,
        "w1_touch": 1,
        "round_score": 0.5,
        "magnitude_score": 0.5,
    }

    ctx = SignalContext(
        entry=110.42, open_price=110.41, atr=0.10, atr7=0.10,
        ema9=110.40, ema21=110.38, ema50=110.35, ema200=110.30,
        rsi=50.0, adx=25.0, adx_pos=25.0, adx_neg=22.0,
        macdh=0.001, macdh_prev=0.0,
        bbpb=0.5, bb_upper=110.60, bb_mid=110.45, bb_lower=110.30, bb_width=0.01,
        prev_close=110.43, prev_open=110.45, prev_high=110.45, prev_low=110.41,
        symbol="USDJPY=X", tf="15m", is_jpy=True, pip_mult=100,
        df=df,
        sr_levels=[110.40, 111.00],
        layer3={"sr_weighted_levels": [heavy_level]},
        regime={"regime": "TREND"},
        htf={"agreement": "mixed"},
        backtest_mode=True,
        bar_time=df.index[-1],
        hour_utc=12,
    )

    s = SrWeightedBreak()
    result = s.evaluate(ctx)
    # exception 投げないこと
    assert result is None or hasattr(result, "signal")


def test_evaluate_skips_when_env_disabled():
    os.environ.pop("SR_WEIGHTED_BREAK_ENABLE", None)
    class Ctx:
        pass
    ctx = Ctx()
    ctx.symbol = "USDJPY=X"
    s = SrWeightedBreak()
    assert s.evaluate(ctx) is None
```

# 3. 不変条件 (絶対遵守)

- ✋ 既存 SR 戦略 (`sr_anti_hunt_bounce` / `sr_break_retest` / `sr_fib_confluence` / `sr_liquidity_grab` / `sr_channel_reversal` / `sr_weighted_bounce`) のコードを **絶対に変更しない**
- ✋ `enabled = False` をデフォルトとし、env `SR_WEIGHTED_BREAK_ENABLE=1` 未設定時は evaluate 早期 None
- ✋ パラメータ sweep 禁止 — K=3.0 / percentile=30% / ADX>=20 / Body>=0.25 / Retest=0.5 ATR は Wave 1 固定
- ✋ composite weight 係数は sr_weighted_bounce と完全一致 (1:3:5:2:1.5)
- ✋ Yahoo データ参照禁止
- ✋ stash leak 禁止 — final.md で `git log` / `git stash list` (空) / `git status` (新規 .py + wiki + decision + tests + __init__.py 変更) 実 verify
- ✋ wiki + decision doc は **同コミット内で作成**

# 4. 完了条件

1. `strategies/daytrade/sr_weighted_break.py` が §2.1 仕様通り作成
2. `strategies/daytrade/__init__.py` が §2.2 通り更新 (sr_weighted_bounce の構造を踏襲)
3. `knowledge-base/wiki/strategies/sr-weighted-break.md` 作成
4. `.ai/decisions/2026-05-13-sr-weighted-break-shadow-injection.md` 作成
5. `tests/test_sr_weighted_break.py` および `tests/test_sr_weighted_break_integration.py` 作成 + 全 PASS
6. `python3 -m pytest tests/test_sr_weighted_break.py tests/test_sr_weighted_break_integration.py -x -v` 完走
7. `python3 scripts/check.py` PASS
8. PR タイトル: `feat(sr-redesign): sr_weighted_break shadow-only strategy (heavy wall breakout retest, break family pair)`
9. PR description に思想要約 + family pair (sr_weighted_bounce との関係) + Tier promotion gate + Shadow injection 経路
10. final.md に `git log --oneline -5` / `git stash list` (空) / `git status` (新規 5 ファイル + __init__.py 変更) 実 verify

# 5. 後続タスクとの接続

Shadow 投入後:
1. 本タスク merge → user 手動で Render env 追加:
   - `SR_WEIGHTED_BREAK_ENABLE=1`
   - `SR_WEIGHTED_BREAK_SHADOW_PROMOTE=1`
2. 2-3 週で N>=30/pair 蓄積
3. cell_edge_audit で bounce / break family-wise 比較
4. promote 候補 cell が出れば Tier 1 (shadow_active) 検討
5. **family interaction 分析** (別タスク): 同一 heavy level で bounce と break が連続発火するパターンがあるか確認、あれば EV 相殺の有無を実測
