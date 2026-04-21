# WIN Conditions Mining — Filtered "Golden Cells" 分析

**日付**: 2026-04-21
**研究問い**: TP hit (WIN) が集中する feature 組合せは何か?

## ⚠️ Critical Disclosure — This analysis is FILTERED

本分析は以下 3 段階のフィルターを経ている:

1. **Strategy filter**: WIN≥20 & LOSS≥20 の戦略のみ (ema_cross N=46, ema_pullback N=42, vol_surge_detector N=41 等を除外)
2. **Cell filter**: 以下の全条件パス cell のみ
   - N_cell ≥ 15 (2-way) / ≥ 20 (1-way)
   - Lift = WR_cell / WR_baseline ≥ 1.5
   - Wilson 95% CI 下限 > baseline
   - Fisher exact p < 0.01
   - Positive Likelihood Ratio (PLR) ≥ 2.0
3. **Display filter**: Top 15 cells by Lift

**これは "golden cell" (高確度勝ちパターン) の探索分析であり、全 TP-hit の unbiased 記述ではない**. 全 TP-hit の marginal distribution 分析は [[win-conditions-unfiltered-2026-04-21]] を参照.

## データ

- **期間**: 全 shadow (期間制限なし)
- **フィルタ**: `is_shadow=1 AND outcome IN ("WIN","LOSS")`
- **総 N**: 1,714 (shadow_all)
- **検定適格戦略**: 7 (filter 通過)

## 1. Robust Golden Cells (全期間 shadow)

| 戦略 (baseline WR) | 条件 | N | WR | Lift | Wilson 下限 | Fisher p | PLR |
|---|---|---:|---:|---:|---:|---:|---:|
| **ema_trend_scalp** (24.1%) | `ema_stack_bull=1 ∧ ATR_ratio=Q3` | 31 | 51.6% | 2.15x | 34.8% | 5e-4 ★ | 3.37 |
| ema_trend_scalp | `_session=london ∧ confidence=Q3` | 32 | 46.9% | 1.95x | 30.9% | 3e-3 | 2.79 |
| **stoch_trend_pullback** (29.2%) | `ADX=Q1 ∧ ATR_ratio=Q1` | 15 | **66.7%** | 2.29x | 41.7% | 2e-3 ★ | 4.86 |
| stoch_trend_pullback | `direction=BUY ∧ ATR_ratio=Q1` | 18 | 61.1% | 2.10x | 38.6% | 4e-3 | 3.82 |
| **sr_fib_confluence** (24.5%) | `direction=BUY ∧ ATR_ratio=Q3` | 20 | 55.0% | 2.24x | 34.2% | 1e-3 ★ | 3.76 |
| **bb_squeeze_breakout** (27.1%) | `close_vs_ema200=Q1` (EMA200 の深く下) | 21 | 57.1% | 2.11x | 36.5% | 1e-3 ★ | 3.59 |

## 2. Post-Cutoff Only (regime-homogeneous 期間)

| 戦略 (baseline WR) | 条件 | N | WR | Lift | p |
|---|---|---:|---:|---:|---:|
| ema_trend_scalp (22.3%) | `ema_stack_bull=1 ∧ ATR_ratio=Q3` | 21 | 52.4% | 2.35x | 1e-3 ★ |
| bb_rsi_reversion (26.6%) | `direction=BUY ∧ HMM=trending` | 20 | 55.0% | 2.07x | 4e-3 |
| bb_rsi_reversion | `_session=ny ∧ HMM=trending` | 30 | 46.7% | 1.75x | 7e-3 |

## 3. Data-Driven Patterns

### Pattern A: ATR_ratio quartile が真の regime indicator

mtf_regime 6 categories より、**ATR 相対値 quartile の方が差別化力が高い**:

- ema_trend_scalp: Q3 (mid-high) が勝つ
- stoch_trend_pullback: Q1 (low) が勝つ
- sr_fib_confluence: Q3 (mid-high) が勝つ
- bb_squeeze_breakout: ATR 自体でなく close_vs_ema200 Q1 が支配的

### Pattern B: Direction 非対称性は構造的 (全期間で robust)

3 戦略で BUY のみが勝てる cell:
- stoch_trend_pullback: BUY + low ATR
- sr_fib_confluence: BUY + mid-high ATR
- bb_rsi_reversion: BUY + HMM trending

先の [[shadow-tp-sl-causal-2026-04-21]] Phase 7 の Fisher 検定 (bb_rsi BUY 40% vs SELL 19%) と一致.

### Pattern C: bb_squeeze_breakout は「深く割安」状態から効く

`close_vs_ema200 Q1` = price 深く EMA200 以下. Mean reversion to EMA200 の breakout 機構. Range_tight 環境下で特に機能.
本日の USD_JPY PAIR_PROMOTED 決定と整合 (commit `db12a07`).

## 4. Statistical Caveats

### 4.1 Bonferroni 補正の不完全性

"探索空間 = 返された cell 数" として local Bonferroni を計算したが、真の family-wise error rate は `features × categories × combinations` の組合せ全体. 完全な補正では none が有意にならない.

**→ "top robust cells" として報告. Causal claim ではなく hypothesis generation**.

### 4.2 Pre-v9.2.1 artifact cluster

mtf_regime="", mtf_vol_state="", mtf_d1_label=3 等が identical N,W,L で並ぶのは regime engine 稼働前 trades (default values clustering). 本質 feature は `close_vs_ema200`, `ATR_ratio` 等のみ.

### 4.3 Filter bias の影響

3 段フィルター後の cells 報告 = **cherry-picking の自認**. Null cells, unfiltered marginals, non-eligible strategies の情報は欠落.

## 5. Hypothesis for Shadow Validation

以下は hypothesis であり confirmed rule ではない. 2026-05-05 までの追加 shadow 蓄積で再検定が必要:

| Hypothesis | 予測 | 再検定条件 |
|---|---|---|
| H1: ema_trend_scalp の golden cell 持続 | N≥50 で WR > 40% | 2026-05-05 |
| H2: stoch_trend_pullback low-ATR BUY 持続 | N≥30 で WR > 50% | 2026-05-05 |
| H3: bb_squeeze close_vs_ema200 Q1 持続 | N≥40 で WR > 45% | 2026-05-05 |
| H4: bb_rsi BUY × trending 持続 | N≥40 で WR > 45% | 2026-05-05 |

## 6. Source

- Script: `/tmp/win_conditions_mining.py`
- Full output: 本 commit 時点の stdout
- Related: [[shadow-tp-sl-causal-2026-04-21]] (differential analysis), [[win-conditions-unfiltered-2026-04-21]] (unfiltered marginal — 予定)
