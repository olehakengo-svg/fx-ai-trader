# Pre-registration: Cell-level Survivor Scan (Phase 2)

**Locked**: 2026-04-23 (本 doc 確定以降、binding criteria 変更禁止)
**Scan mode**: observational only (code change なし)
**Scope**: shadow post-cutoff=2026-04-08 / XAU除外 / is_shadow=1 / status=closed

## Purpose

[[quant-validation-label-audit-2026-04-23]] で **全カテゴリ Kelly ≤ 0** が
判明し、[[phase0-data-integrity-2026-04-23]] でデータ健全性を確認。
残る仮説は **"全体 broken でも cell レベル (strategy × instrument × regime) に
生存者が居る可能性"**。

本 scan は「全滅か部分生存か」の観察のみ。code 変更 / live-weight 調整には
Phase 1 holdout ([[pre-registration-label-holdout-2026-05-07]]) 通過を要求する。

## Hypothesis

**H_cell**: 少なくとも 1 つの (strategy, instrument, regime) cell が、
current 市場で statistically + economically significant な edge を保持する。

Null: 全 cell が random (WR ≤ BEV_WR) または赤字 (Kelly ≤ 0)。

## Test Design

### Cell definition

```
cell = (strategy_name, instrument, session_regime)
```

- **strategy_name**: entry_type 値 (17 strategies)
- **instrument**: USD_JPY / EUR_USD / GBP_USD / EUR_JPY / GBP_JPY (XAU除外, 5 pairs)
- **session_regime**:
  - `asia`: entry_time hour ∈ [0, 8) UTC
  - `london`: [8, 13) UTC
  - `ny`: [13, 22) UTC
  - `off`: [22, 24) UTC
  - → 4 regimes

**Total cells (upper bound)**: 17 × 5 × 4 = 340
**Expected active cells** (N≥10): ~50-100 (多くは sparse)
**M for Bonferroni**: 340 (保守的上限)

### Per-cell metrics

| Metric | Formula |
|--------|---------|
| N | cell 内 closed trade 数 |
| WR | wins / N |
| Wilson 95% CI | [lower, upper] for WR |
| BEV_WR (cell-specific) | median tp_pips / (median tp_pips + median |sl_pips|) for that cell |
| PF | Σ(pnl>0) / |Σ(pnl<0)| |
| Kelly | max(0, wr × 1/BT_COST_cell − (1−wr)) — simplified fractional |
| Fisher p | vs pooled baseline (within same category) |
| WF sign | first-half vs second-half cell WR, 符号一致 Y/N |

**BT_COST_cell**: per-instrument spread p50 を使用:
- USD_JPY: 0.8 / EUR_USD: 0.8 / GBP_USD: 1.3 / EUR_JPY: 1.9 / GBP_JPY: 2.8

## Binding criteria (decision-grade, locked)

### GO (Phase 1 holdout 候補化)

**全 5 条件を満たす cell のみ生存者とする**:

1. **N ≥ 30** (小-N 排除、[[feedback_partial_quant_trap]] 原則)
2. **Wilson 95% lower > BEV_WR_cell + 0.03** (経済的マージン 3pp 確保)
3. **Fisher exact p < 2.5e-4** (Bonferroni α=0.05/M, M=340 ≈ 1.47e-4; 本 scan では 2.5e-4 で保守寄り)
4. **Kelly > 0.05** (BT_COST_cell 減算後も正期待値)
5. **WF 2-bucket 同符号** (前半 WR − BEV ≥ 0 かつ 後半 WR − BEV ≥ 0)

### CANDIDATE (observation のみ記録、action なし)

以下に該当する cell は "observation" として記録するが本 scan では action なし:
- GO 条件の 4-5 項通過 (1-2 項 miss)
- N ∈ [20, 30) で他 4 項通過

→ 次の holdout 窓 (Apr 24–May 7) で独立再検定

### FAIL (記録なし)

上記 2 分類に該当しない cell。

## Post-scan action rules (locked)

scan 実行後、以下に従う:

### Scenario A: 生存者 0 (GO 0 件 AND CANDIDATE 0 件)

→ **全面 regime mismatch** 確定。Phase 3 stopping rule 発動候補:
  - 現 shadow システム全体が current 市場で dead
  - [[pre-registration-label-holdout-2026-05-07]] H3 (category 降格)
    の確実性が極めて高い
  - 新戦略設計 (Phase 4) を即時着手判断材料

### Scenario B: GO 0 件 + CANDIDATE 1-5 件

→ **部分的生存候補あり**。ただし本 scan では live-weight 変更禁止。
  Phase 1 holdout で confirmatory test 必要。

### Scenario C: GO 1-5 件

→ **統計的+経済的 survivor 確認**。ただしそれでも:
  - 本 scan 結果のみでは live-weight 変更不可
  - Holdout 窓 (Apr 24–May 7) で独立に同 cell の GO 条件を再満足
    する必要あり (multi-testing floor)
  - 満足した場合のみ live-weight 調整の decision-grade 材料となる

### Scenario D: GO > 5 件

→ **警告: over-discovery**. α=2.5e-4 は保守的だが false positive を
  疑う。Bonferroni を M=680 (cell 全上限 + observables 340) で
  再計算し再判定。

## Disallowed (post-hoc fishing 防止)

以下は scan 実行後に発見しても binding criteria 変更には使えない:

- session_regime の再分割 (例: asia → tokyo_am / tokyo_pm)
- instrument pair の再組合せ (例: JPY-cross 統合)
- 別 cutoff date 試行 (snooping)
- N<30 cell の "実質活発" などの ex-post 正当化
- WF 分割を 2-bucket → 3-bucket 以上に細分化 (overfitting)

新 hypothesis は **次の pre-registration** として別 doc を作成する。

## Parameters (locked)

| Parameter | Value |
|-----------|-------|
| shadow cutoff | 2026-04-08 |
| exclusion | XAU含む instrument / is_shadow≠1 / status≠CLOSED |
| α family | 0.05 |
| M (cells upper bound) | 340 |
| α_cell | 2.5e-4 (Bonferroni 保守) |
| WF 2-bucket | median entry_time split (equal-N) |
| BEV margin | +3pp on Wilson lower |
| Kelly threshold | > 0.05 (BT_COST_cell 減算後) |
| WF requirement | 2-bucket 同符号 (両 bucket で WR ≥ BEV) |
| Fisher alternative | 2-tail (edge 方向不問、ただし Wilson lower > BEV で正方向絞り) |

## Execution

### Script

`/tmp/cell_level_scan.py` (新規作成予定、コード変更なし、API read-only)

### Input

Render production API:
`https://fx-ai-trader.onrender.com/api/demo/trades?status=closed&date_from=2026-04-08`

### Output

- Raw: `/tmp/cell_level_scan_output.txt`
- KB: [[cell-level-scan-2026-04-23]] (結果記録)

## Accountability

**事前約束**:
- scan 結果を見てから binding criteria を変更しない
- N が足りない cell に対して「実質有望」などの ex-post 正当化をしない
- scenario B/C でも holdout 以前に code 変更 / live-weight 調整しない
- scenario D の over-discovery suspicion を無視しない

## References

- [[phase0-data-integrity-2026-04-23]]
- [[quant-validation-label-audit-2026-04-23]]
- [[pre-registration-label-holdout-2026-05-07]]
- [feedback_partial_quant_trap](/Users/jg-n-012/.claude/projects/-Users-jg-n-012-test/memory/feedback_partial_quant_trap.md)
- [[lesson-premature-neutralization-2026-04-23]]
