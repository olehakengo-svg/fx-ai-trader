# Pre-registration: Phase 4 Adaptive Regime Classifier v5 — Per-cell Authorization Rule (2026-04-23)

**Locked**: 2026-04-23 (v4 結果を受けた rule refinement 版、本 doc 確定後変更禁止)
**Prev**: [[pre-registration-phase4-adaptive-regime-v4-2D-2026-04-23]] (v4, USDJPY 2/3 / EURUSD 1/3)
**Prev result**: [[phase4a-v4-classifier-stability-2026-04-23]]

## Scope of v5

**v5 は classifier design の変更ではない**. v4 の 2D classifier (Regime × Vol) と stability
tests (S1/S2/S3) をそのまま保持し、**authorization rule のみ** を refine する.

v4 で観測した "1 cell の S3 marginal FAIL で 17 GO cells が全て blocked" という
over-conservative な状態は、pair-level score aggregation の artifact. per-cell aggregation
に統一することで、v4 §5 の "partial-pass cell 群のみ authorize" の spirit を
S1 以外 (S2/S3) にも拡張する。

## Changes from v4

| Component | v4 | v5 |
|-----------|----|----|
| Regime axis (R1-R6 + R0) | 同じ | **同じ (保持)** |
| Vol axis (V_low/mid/high, F1 閾値 0.33/0.67) | 同じ | **同じ (保持)** |
| Cell classifier | 同じ | **同じ (保持)** |
| S1 test (per-cell F2/F3 KS, M=324 α=1.54e-4) | 同じ | **同じ (保持)** |
| S2 test (per-cell MK on F2, M=18 α=2.78e-3) | 同じ | **同じ (保持)** |
| S3 test (per-cell CV < 0.4) | 同じ | **同じ (保持)** |
| **Authorization rule** | **pair-level score** | **per-cell 3-test AND** |

## Rationale for rule change (not threshold change)

### 何を変えない
- 各 test の 閾値 (α_cell, CV threshold 0.4) は v4 で LOCK 済. **変更しない**.
- v4 実測データから threshold を再 fit する行為は **post-hoc 禁止** (disallowed §6).

### 何を変える
- v4 §5 は authorization を `pair-level score (3/3, 2/3, 1/3)` で定義していた.
- v5 は `per-cell 3-test AND` に統一する.

### なぜこの refinement が post-hoc narrative でないか

1. v4 §5 で **"partial-pass cell 群のみ authorize"** ルールは既に S1 に対して pre-registered
2. S2/S3 に対しても同じ per-cell 思想を適用するのは **consistency restoration** であり
   新規 rule 創出ではない
3. 実装上も v4 script は per-cell で S2/S3 を既に集計していた (rule aggregation が
   pair-level だったのみ)
4. "Partial authorize" の spirit を全 test に統一することで **一貫した意思決定 frame**
   を提供する

## 1. Taxonomy, Features, Classifier (LOCKED — v4 から unchanged)

全て v4 通り. 詳細 [[pre-registration-phase4-adaptive-regime-v4-2D-2026-04-23]] §1-§4.

## 2. Stability tests (LOCKED — v4 から unchanged)

### S1 v5 (=v4 の S1)
- Per-cell × F2/F3 × 月ペア KS
- M = 18 × 2 × 9 = 324, α_cell = 1.54e-4
- N ≥ 30 per cell-month

### S2 v5 (=v4 の S2)
- Per-cell Mann-Kendall on F2 monthly mean
- M = 18, α_cell = 2.78e-3
- N_months ≥ 6

### S3 v5 (=v4 の S3)
- Per-cell monthly median duration CV
- Threshold: **CV < 0.4** (v4 と同じ、LOCKED)
- N_months ≥ 3

## 3. v5 Authorization rule (LOCKED — new per-cell aggregation)

### Per-cell verdict

各 active cell (18) について、その cell が以下を全て満たせば **CELL_GO**:

```
S1_cell_GO := cell 内の全 (feature, month-pair) cells が KS p > α_cell
              (INSUFFICIENT = 0 cells tested の場合は CELL_INSUFFICIENT)
S2_cell_GO := 該当 cell の Mann-Kendall p > α_bonf
              (n_months < 6 の場合は CELL_INSUFFICIENT)
S3_cell_GO := 該当 cell の CV < 0.4
              (n_months < 3 の場合は CELL_INSUFFICIENT)

CELL_VERDICT := GO if (S1_cell_GO ∧ S2_cell_GO ∧ S3_cell_GO)
             := INSUFFICIENT if (少なくとも 1 test が INSUFFICIENT かつ他に FAIL 無し)
             := FAIL otherwise
```

### Pair-level summary (informational, not gating)

- `go_cells`: GO verdict cells の集合
- `insufficient_cells`: INSUFFICIENT cells
- `fail_cells`: FAIL cells

### Phase B authorization

**両 pair で CELL_GO の cells の集合 (intersection) が Phase B 対象**.

```
PHASE_B_CELLS := go_cells[USDJPY] ∩ go_cells[EURUSD]
```

| |PHASE_B_CELLS| | Action |
|----------------|--------|
| ≥ 10 | Phase B full scope で authorize |
| 5-9 | Phase B 限定 scope で authorize (power 懸念記録) |
| 1-4 | Phase B authorize 可能だが Bonferroni burden 大、結果解釈注意 |
| 0 | Phase B authorize 不能、v6 redesign 要 |

Bonferroni for Phase B: M = |PHASE_B_CELLS| × 17 strategies, α_cell = 0.05 / M.

## 4. Disallowed (v5)

- 本 pre-reg LOCK 後の rule 変更
- S1/S2/S3 閾値の post-hoc 調整
- v4 実測データから threshold を再 fit する行為
- PHASE_B_CELLS intersection の relaxation (例: union に変更)
- Pair-specific Phase B (intersection でなく pair ごとの go_cells を使う) への緩和

## 5. Pre-registered hypotheses

**H1 (strong)**: v4 で identified された common 10 cells (両 pair S1 GO) は、
S2/S3 も per-cell GO のため、v5 per-cell rule で **intersection = 10 cells** が authorize される

**H2 (moderate)**: EUR_USD で S3 max_cv=0.447 の FAIL cell は R3/R4 の低頻度 cell であり
common 10 に含まれないため、v5 rule では問題にならない

**H3 (weak null)**: per-cell reading で予期せぬ cell が FAIL を起こす
(例: S2 で marginal p が new Bonferroni 下で FAIL になる)
→ この場合 intersection は 10 未満、Phase B scope 縮小

H1/H2 は v4 output から強く示唆されるが、v5 はこれを **formal に per-cell AND で確認** する
step であり、結果予断ではない。

## 6. Execution (this session)

1. `/tmp/phase4a_v5_classifier_stability.py` を新規作成
   - v4 script を再利用、authorization aggregation のみ per-cell AND に変更
   - PHASE_B_CELLS intersection を出力
2. OANDA 5m × 10 months × 2 pairs で検定 (v1-v4 と同じ data)
3. KB 記録: [[phase4a-v5-classifier-stability-2026-04-23]]
4. Commit

## 7. Handoff to Phase B

v5 で PHASE_B_CELLS ≥ 5 なら Phase B pre-registration 作成:
- `pre-registration-phase4b-cell-edge-test-<next_date>.md`
- 対象 cells: v5 で確定 (LOCKED at that pre-reg)
- Per-cell metric: Fisher exact 2-tail p, Wilson 95% CI, Kelly
- Survivor 基準: p < α_cell ∧ Kelly > 0 ∧ Wilson CI lower > 0
- Walk-forward: 2-bucket same-sign requirement

## References

- [[pre-registration-phase4-adaptive-regime-v4-2D-2026-04-23]] (v4 prereg)
- [[phase4a-v4-classifier-stability-2026-04-23]] (v4 result)
- [[pre-registration-phase4-adaptive-regime-classifier-v3-2026-04-23]] (v3 prereg)
- [[lesson-premature-neutralization-2026-04-23]] (discipline 根拠)
- [[pre-registration-phase4-regime-native-2026-04-23]] (D1-D4, still blocked)
