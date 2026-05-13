---
id: 20260513-2200-sr-weighted-bounce-shadow-strategy-new
title: "[SR-Redesign] sr_weighted_bounce 新戦略 Shadow-only 投入 — heavy wall reversal with composite weight gate"
owner: codex
status: queued
priority: P1
created_at: 2026-05-13T22:00:00+0900
roadmap_gate: "SR weight redesign 仮説検証を BT ではなく Shadow で行う方針 (memory: feedback_shadow_first_quant_architecture)。既存 5 SR 戦略は触らず、weight gate + 2 family 分離 思想を体現した完全新規戦略 sr_weighted_bounce を Shadow-only で導入。N≥30 蓄積後 Wilson_lo + Bonferroni 通過で Tier 1 検討。"
rule: pre-reg
related:
  - strategies/daytrade/sr_anti_hunt_bounce.py
  - strategies/daytrade/__init__.py
  - strategies/base.py
  - strategies/context.py
  - modules/sr_detector.py
  - modules/indicators.py
  - modules/round_number.py
  - knowledge-base/wiki/strategies/sr-anti-hunt-bounce.md
---

# 0. 背景 (司令塔 2026-05-13)

## 0.1 これまでの SR redesign 経緯

| Phase | 結果 |
|---|---|
| Phase 2 BT (commit 1eabe84) | `sr_anti_hunt_bounce` のみ BH FDR survivor (N=594, p=0.0034)。残り 5 戦略 NULL |
| 実装監査 (司令塔 2026-05-11) | 5 NULL 戦略の **誰も touch_count を gate に使っていない**。sr_detector の weight info を捨てている smoking gun ([sr_break_retest.py:61](strategies/daytrade/sr_break_retest.py) `MIN_CLUSTERS=1 # 単一フラクタルも有効SR`) |
| v2 audit (synthetic) | 5/5 DEAD だが forensic (commit 28a1114 + b6ac007) で audit pipeline と Phase 2 BT pipeline は trade timestamps **Jaccard ≈ 0** と判明、信用できない |
| OANDA 公式記事 | Dow theory horizon: 「水平線は touches で重み付け」の思想を裏付け |

## 0.2 結論

BT 信頼性問題は別 backlog。**Shadow-first quant architecture** (`feedback_shadow_first_quant_architecture.md`) に従い、weight gate を体現した **完全新規戦略** を Shadow に投入し実トレードで検証する方が早い。既存 5 戦略は破壊しない。

# 1. 目的

`strategies/daytrade/sr_weighted_bounce.py` を新規作成し、Shadow-only (Tier 0 audit_only) で 5 majors 全走。N≥30 蓄積後に Wilson_lo + Bonferroni で再評価。

# 2. 仕様

## 2.1 ファイル新規作成: `strategies/daytrade/sr_weighted_bounce.py`

完全な戦略ファイルを以下のテンプレートで作成 (sr_anti_hunt_bounce.py の v2_redesign path をベース、weight gate 追加):

```python
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
        if rscore == 0.0 and "price" in level_meta:
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
```

## 2.2 Engine registration: `strategies/daytrade/__init__.py`

import セクション (sr_anti_hunt_bounce の直下に追加):

```python
# v11 (2026-05-13): SR Weighted Bounce — heavy wall reversal with composite weight gate (Shadow-only)
from strategies.daytrade.sr_weighted_bounce import SrWeightedBounce
```

`self.strategies` list (sr_anti_hunt_bounce の直下に追加):

```python
SrAntiHuntBounce(),            # SR Anti-Hunt Bounce: KDE+hunt-aware SL (5 majors Shadow 全走 2026-04-27)
SrLiquidityGrab(),             # SR Liquidity Grab: SMC post-hunt reversal (5 majors Shadow 全走 2026-04-27)
SrWeightedBounce(),            # 🆕 SR Weighted Bounce v1: heavy wall + composite weight gate (Shadow-only 2026-05-13)
```

SHADOW_ALWAYS_STRATEGIES env block の末尾 (リターン文の直前) に追加:

```python
if (os.environ.get("SR_WEIGHTED_BOUNCE_ENABLE") == "1"
        and os.environ.get("SR_WEIGHTED_BOUNCE_SHADOW_PROMOTE") == "1"):
    _shadow_always = _shadow_always | {"sr_weighted_bounce"}
```

戦略の `enabled` も env 経由で動的化したい場合は `evaluate_all` ループの前に処理を追加 (任意、現状の sr_anti_hunt_bounce が `enabled = True` 直書きなので、本戦略は **`enabled = False` 直書き + env=1 で SHADOW_ALWAYS に追加** という二段構成で十分)。

**重要**: Production `app.run_daytrade_backtest` / live demo_trader 経路で `sr_weighted_bounce` が evaluate される必要があるため、enabled は env 経由で動的に True にしたい。最小実装は `evaluate` 関数冒頭で:

```python
def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
    if os.environ.get("SR_WEIGHTED_BOUNCE_ENABLE") != "1":
        return None
    # ... 既存ロジック ...
```

これで env=1 でのみ実行される。デフォルト無効。

## 2.3 KB wiki: `knowledge-base/wiki/strategies/sr-weighted-bounce.md`

```markdown
---
name: sr_weighted_bounce
mode: daytrade
status: shadow_only_audit_only
created_at: 2026-05-13
strategy_type: MR
family: bounce
parent_lineage: sr_anti_hunt_bounce (Phase 2 BT survivor)
tier: 0 (audit_only)
---

# SR Weighted Bounce v1

## 思想
SR 水平線の重み (touch_count + D1/W1 confluence + round_number + rejection magnitude) で
gate された **heavy wall reversal**。survivor `sr_anti_hunt_bounce` の anti-hunt SL geometry
を継承しつつ、weight gate で sigal の母集団を絞り込む。

## 司令塔仮説 (2026-05-13)
- 既存 5 SR 戦略 (`sr_anti_hunt_bounce` 含む) は touch_count を gate に使っていなかった
- `sr_detector` / `find_sr_levels_weighted` の weight info を捨てている (smoking gun:
  sr_break_retest.py:61 `MIN_CLUSTERS=1`)
- 「重い壁ほど反発エッジが強い」を実トレードで検証

## エントリ条件
| # | 条件 | 値 |
|---|---|---|
| 1 | ペア | USDJPY/EURUSD/GBPUSD/EURJPY/GBPJPY |
| 2 | ADX | < 30 |
| 3 | composite_weight | >= 3.0 |
| 4 | weight percentile | 上位 30% |
| 5 | SR proximity | < 0.4 ATR |
| 6 | 反転足確認 | signal 方向の実体 |
| 7 | 直近 2 本に hunt wick | なし |

## Composite Weight
`1.0 × own_touch + 3.0 × d1_touch + 5.0 × w1_touch + 2.0 × round_score + 1.5 × magnitude_score`
(Wave 1 固定、post-hoc selection 罠回避のため sweep しない)

## SL/TP
- SL = level − sign × (P90_excursion + 0.5 × ATR) (2026-Q1 calibration、Shadow N>=30 後 re-audit)
- TP = min(next_opposite_SR, entry + 2.0 × SL_dist)、MIN_RR=1.5

## Shadow promotion gate (Tier 0 → 1)
- N >= 30 trades
- Wilson_lo (95% LB, Bonferroni m=2 (bounce/break 想定)) >= 0.40
- 単一年 WR>=90% 集中 flag が出ていない

## Live promotion gate (Tier 1 → 2)
- N >= 100 trades
- Bonferroni m=2 再現性
- WF 3+ folds pos_ratio >= 0.8
- Kelly >= 0.20

## 起源 / 関連
- 経緯: `wiki/decisions/2026-05-13-sr-weighted-bounce-shadow-injection.md` (生成予定)
- 親 lineage: sr_anti_hunt_bounce ([wiki/strategies/sr-anti-hunt-bounce.md](sr-anti-hunt-bounce.md))
- Phase 2 BT: `bt-results/sr-weight-phase2-bin-bhfdr-2026-05-11.json`
- audit v2 forensic: `reports/sr_phase2_vs_audit_v2_forensic_2026-05-13.md`

## 計装
- entry_type: `sr_weighted_bounce`
- sr_meta は既存 oanda_audit DDL (sr_strength/sr_touches/sr_days_span/sr_is_strong/sr_distance_atr)
  に composite_weight 追加列が要れば Phase 2.5 で別タスク化
```

## 2.4 Decision doc: `.ai/decisions/2026-05-13-sr-weighted-bounce-shadow-injection.md`

```markdown
---
id: 2026-05-13-sr-weighted-bounce-shadow-injection
title: SR Weighted Bounce Shadow Injection — Wave 1 (audit_only)
verdict: APPROVE
rule: R1
related_task: 20260513-2200-sr-weighted-bounce-shadow-strategy-new
audit_at: 2026-05-13T22:00:00+0900
auditor: Claude (司令塔)
---

# 監査 input
- Phase 2 BT survivor: sr_anti_hunt_bounce (N=594, p=0.0034)
- v2 audit forensic: BT pipeline と production pipeline は trade Jaccard ≈ 0
- OANDA 公式 Dow theory horizon 記事の thesis 支持
- 既存 5 SR 戦略の実装監査: 誰も touch_count を gate に使っていない

# 規律 checklist
| 規律 | 状態 |
|---|---|
| 既存 5 SR 戦略を破壊しない | ✅ 新規ファイルのみ |
| Shadow-first (BT に頼らない) | ✅ memory feedback_shadow_first_quant_architecture 準拠 |
| Wave 1 でパラメータ sweep しない | ✅ K=3.0 / percentile=30% 固定 |
| Family 分離 | ✅ bounce only (break は後続 task) |
| Live PnL 影響 | ✅ ゼロ (env=0 デフォルト、SHADOW_ALWAYS 経由 audit_only) |
| KB sync | ✅ wiki/strategies/sr-weighted-bounce.md 同コミット |

# Shadow → Live promotion gate (pre-reg)
N>=30 + Wilson_lo>=0.40 (Bonferroni m=2 補正) + WF 3+ folds pos_ratio>=0.8

# 残懸念
- audit v2 で composite weight quintile が WR を discriminate しなかった
  (synthetic universe での結果)。Shadow 実取引で再現するか観察
- P90 excursion pip table が 2026-Q1 calibration。Shadow N>=30 後に再 audit 必須
- detector 依存 (KDE vs PIVOT で trade Jaccard 0) は別 backlog
```

## 2.5 Unit tests: `tests/test_sr_weighted_bounce.py` (新規)

```python
"""Unit tests for sr_weighted_bounce strategy."""
import os
import pytest
import pandas as pd
from strategies.daytrade.sr_weighted_bounce import SrWeightedBounce


def _enable():
    os.environ["SR_WEIGHTED_BOUNCE_ENABLE"] = "1"


def _disable():
    os.environ.pop("SR_WEIGHTED_BOUNCE_ENABLE", None)


def test_composite_weight_formula():
    s = SrWeightedBounce()
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


def test_composite_weight_with_touches_alias():
    s = SrWeightedBounce()
    # find_sr_levels_weighted 互換 (touches キー)
    meta = {"price": 110.50, "touches": 4}
    expected = 1.0 * 4
    assert abs(s._compute_composite_weight(meta) - expected) < 1e-9


def test_select_heavy_level_gate_pass():
    s = SrWeightedBounce()
    # 4 levels: 1 heavy in top-30%, 1 below absolute threshold,
    # 1 outside proximity, 1 below percentile
    levels = [
        {"price": 110.50, "own_touch": 10, "d1_touch": 3, "w1_touch": 1,
         "round_score": 0.5, "magnitude_score": 0.5},
        {"price": 110.40, "own_touch": 2, "d1_touch": 0, "w1_touch": 0,
         "round_score": 0.0, "magnitude_score": 0.0},
        {"price": 115.00, "own_touch": 8, "d1_touch": 2, "w1_touch": 1,  # too far
         "round_score": 0.0, "magnitude_score": 0.5},
        {"price": 110.45, "own_touch": 3, "d1_touch": 0, "w1_touch": 0,
         "round_score": 0.0, "magnitude_score": 0.0},
    ]
    # ctx mock minimal
    class Ctx: pass
    ctx = Ctx()
    out = s._select_heavy_level(ctx, levels, signal_price=110.52, atr=0.1)
    assert out is not None
    assert out["price"] == 110.50


def test_select_heavy_level_gate_reject_below_abs():
    s = SrWeightedBounce()
    # All levels below K_ABS_THRESHOLD=3.0
    levels = [
        {"price": 110.50, "own_touch": 1, "round_score": 0.0, "magnitude_score": 0.0},
        {"price": 110.45, "own_touch": 2, "round_score": 0.0, "magnitude_score": 0.0},
    ]
    class Ctx: pass
    out = s._select_heavy_level(Ctx(), levels, signal_price=110.48, atr=0.1)
    assert out is None


def test_evaluate_returns_none_when_env_disabled():
    _disable()
    s = SrWeightedBounce()
    class Ctx: pass
    ctx = Ctx()
    ctx.symbol = "USDJPY=X"
    assert s.evaluate(ctx) is None


# integration sanity: enabled=False default
def test_strategy_disabled_by_default():
    s = SrWeightedBounce()
    assert s.enabled is False
```

## 2.6 Integration test: `tests/test_sr_weighted_bounce_integration.py` (新規)

```python
"""Integration test: sr_weighted_bounce minimal signal generation sanity."""
import os
import pandas as pd
import pytest
from strategies.daytrade.sr_weighted_bounce import SrWeightedBounce


@pytest.fixture
def enable_env():
    os.environ["SR_WEIGHTED_BOUNCE_ENABLE"] = "1"
    yield
    os.environ.pop("SR_WEIGHTED_BOUNCE_ENABLE", None)


def test_evaluate_runs_without_error_on_synthetic_data(enable_env):
    """Build minimal synthetic ctx with weighted level near price, ADX<30, no recent hunt.

    Verify evaluate returns Candidate or None without exception.
    """
    from strategies.context import SignalContext

    idx = pd.date_range("2026-01-01", periods=20, freq="15min", tz="UTC")
    df = pd.DataFrame({
        "Open":  [110.45] * 20,
        "High":  [110.55] * 20,
        "Low":   [110.40] * 20,
        "Close": [110.50] * 20,
        "atr":   [0.10] * 20,
        "atr7":  [0.10] * 20,
        "adx":   [22.0] * 20,
        "adx_pos": [22.0] * 20,
        "adx_neg": [20.0] * 20,
        "ema9":  [110.49] * 20,
        "ema21": [110.48] * 20,
        "ema50": [110.45] * 20,
        "ema200":[110.40] * 20,
        "macd_hist": [0.001] * 20,
        "bb_pband": [0.2] * 20,
        "bb_upper": [110.55] * 20,
        "bb_mid": [110.50] * 20,
        "bb_lower": [110.45] * 20,
        "bb_width": [0.01] * 20,
        "rsi": [50.0] * 20,
    }, index=idx)

    heavy_level = {
        "price": 110.45,
        "own_touch": 8,
        "d1_touch": 2,
        "w1_touch": 1,
        "round_score": 0.5,
        "magnitude_score": 0.5,
    }
    light_level = {
        "price": 109.00,
        "own_touch": 1,
        "d1_touch": 0,
        "w1_touch": 0,
        "round_score": 0.0,
        "magnitude_score": 0.0,
    }

    ctx = SignalContext(
        entry=110.50, open_price=110.45, atr=0.10, atr7=0.10,
        ema9=110.49, ema21=110.48, ema50=110.45, ema200=110.40,
        rsi=50.0, adx=22.0, adx_pos=22.0, adx_neg=20.0,
        macdh=0.001, macdh_prev=0.0,
        bbpb=0.2, bb_upper=110.55, bb_mid=110.50, bb_lower=110.45, bb_width=0.01,
        prev_close=110.50, prev_open=110.45, prev_high=110.55, prev_low=110.40,
        symbol="USDJPY=X", tf="15m", is_jpy=True, pip_mult=100,
        df=df,
        sr_levels=[110.45, 109.00],
        layer3={"sr_weighted_levels": [heavy_level, light_level]},
        regime={"regime": "RANGE"},
        htf={"agreement": "mixed"},
        backtest_mode=True,
        bar_time=df.index[-1],
        hour_utc=12,
    )

    s = SrWeightedBounce()
    result = s.evaluate(ctx)
    # 結果は None または Candidate のどちらでも OK (gate logic 通過にあらゆる field が要るため)
    # 重要: exception を投げないこと
    assert result is None or hasattr(result, "signal")


def test_evaluate_skips_when_env_disabled():
    os.environ.pop("SR_WEIGHTED_BOUNCE_ENABLE", None)
    # ctx は最小限で OK (early return が env check で起こる)
    class Ctx:
        pass
    ctx = Ctx()
    ctx.symbol = "USDJPY=X"
    s = SrWeightedBounce()
    assert s.evaluate(ctx) is None
```

# 3. 不変条件 (絶対遵守)

- ✋ 既存 5 SR 戦略 (`sr_anti_hunt_bounce` / `sr_break_retest` / `sr_fib_confluence` / `sr_liquidity_grab` / `sr_channel_reversal`) のコードを **絶対に変更しない**
- ✋ `enabled = False` をデフォルトとし、env `SR_WEIGHTED_BOUNCE_ENABLE=1` 未設定時は evaluate 早期 None
- ✋ パラメータ sweep 禁止 — K=3.0 / percentile=30% / composite weight 係数 (1:3:5:2:1.5) は Wave 1 固定
- ✋ 既存 BT pipeline / audit v2 ツールへの統合は本タスクでは行わない (Shadow 実行のみ)
- ✋ Yahoo データ参照禁止
- ✋ stash leak 禁止 — final.md で `git log` / `git stash list` (空) / `git status` (新規 .py + wiki + decision + tests) 実 verify
- ✋ wiki + decision doc は **同コミット内で作成** (KB sync 規律)

# 4. 完了条件

1. `strategies/daytrade/sr_weighted_bounce.py` が §2.1 仕様通り作成 (env gate 含む)
2. `strategies/daytrade/__init__.py` が §2.2 通り更新 (import / strategies list / SHADOW_ALWAYS block)
3. `knowledge-base/wiki/strategies/sr-weighted-bounce.md` が §2.3 通り作成
4. `.ai/decisions/2026-05-13-sr-weighted-bounce-shadow-injection.md` が §2.4 通り作成
5. `tests/test_sr_weighted_bounce.py` および `tests/test_sr_weighted_bounce_integration.py` 作成 + 全 PASS
6. `python3 -m pytest tests/test_sr_weighted_bounce.py tests/test_sr_weighted_bounce_integration.py -x -v` 完走
7. `python3 scripts/check.py` PASS (existing strategies list integrity)
8. PR タイトル: `feat(sr-redesign): sr_weighted_bounce shadow-only strategy (heavy wall reversal with composite weight gate)`
9. PR description に思想要約 + Tier promotion gate + Shadow injection 経路 (env 1 → SHADOW_ALWAYS) を明記
10. final.md に `git log --oneline -5` / `git stash list` (空) / `git status` (5 ファイル新規) 実 verify 証跡

# 5. 後続タスクとの接続

Shadow 投入後の流れ:
1. 本タスク merge → 即時 `SR_WEIGHTED_BOUNCE_ENABLE=1` + `SR_WEIGHTED_BOUNCE_SHADOW_PROMOTE=1` を Render env に追加 (user 手動)
2. 2-3 週で N>=30/pair 蓄積
3. cell_edge_audit / per-pair Wilson_lo + Bonferroni 評価 (司令塔別タスク)
4. promote 候補 cell が出れば Tier 1 (shadow_active) 検討、Live 昇格は更に厳格 gate
5. 並行で **break family (sr_weighted_break)** を後追い投入 (本タスク完了後)
