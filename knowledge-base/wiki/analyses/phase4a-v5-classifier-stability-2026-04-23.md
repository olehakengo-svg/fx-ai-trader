# Phase 4a v5 Classifier Stability Result (2026-04-23)

**Pre-registration**: [[pre-registration-phase4-adaptive-regime-v5-per-cell-rule-2026-04-23]]
**Script**: `/tmp/phase4a_v5_classifier_stability.py`
**Raw**: `/tmp/phase4a_v5_output.txt` / `/tmp/phase4a_v5_summary.json`
**Data**: OANDA 5m × 10 months × 2 pairs (N≈66k each、v1-v4 と同じ)

## Result: **PHASE_B FULL SCOPE AUTHORIZED (10 cells)**

| Pair | GO cells | FAIL cells | INSUFFICIENT |
|------|----------|------------|--------------|
| USD_JPY | **10** | 4 | 4 |
| EUR_USD | **12** | 3 | 3 |
| **Intersection (PHASE_B_CELLS)** | **10** | — | — |

### PHASE_B_CELLS (両 pair per-cell 3/3 GO)

```
R1_trend_up__V_low    R1_trend_up__V_mid    R1_trend_up__V_high
R2_trend_down__V_mid  R2_trend_down__V_high
R5_breakout__V_mid    R5_breakout__V_high
R6_reversal__V_low    R6_reversal__V_mid    R6_reversal__V_high
```

**Phase B Bonferroni**: M = 10 × 17 strategies = **170**, α_cell = **2.94e-4**.

## Hypothesis verification

- **H1 (strong)**: common 10 cells が intersection で authorize される
  → ✅ **完全一致**. v4 で identified された common 10 GO cells が v5 per-cell rule で
  exactly そのまま intersection に残った。

- **H2 (moderate)**: EUR_USD の S3 max_cv=0.447 cell (R3_V_mid) は common 10 外
  → ✅ **確認**. R3_range_tight__V_mid (EUR_USD, cv=0.447) が FAIL したが
  intersection には影響せず。

- **H3 (weak null)**: 予期せぬ cell で per-cell S2 FAIL により intersection 縮小
  → ❌ **起きず**. 全 S2 FAIL cell は S1 でも FAIL または INSUFFICIENT.

## Per-cell 詳細

### USD_JPY per-cell summary

| Cell | S1 | S2 | S3 | Verdict | Notes |
|------|----|----|----|---------|-------|
| R1_trend_up__V_low/mid/high | GO | GO | GO | ✅ GO | 全 vol bucket 通過 |
| R2_trend_down__V_high | GO | GO | GO | ✅ GO | S1 min_p=3.48e-4 |
| R2_trend_down__V_mid | GO | GO | GO | ✅ GO | |
| R2_trend_down__V_low | FAIL | GO | GO | ❌ FAIL | F3 drift 2025-06→07 |
| R3_range_tight__V_low | FAIL | GO | GO | ❌ FAIL | F3 drift 2025-11→12 |
| R3_range_tight__V_mid | INSUFF | GO | GO | — | N=122 |
| R3_range_tight__V_high | INSUFF | INSUFF | INSUFF | — | N=0 (structural) |
| R4_range_wide__V_high | FAIL | GO | GO | ❌ FAIL | F2 drift 2026-02→03 |
| R4_range_wide__V_mid | INSUFF | GO | GO | — | N=114 |
| R4_range_wide__V_low | INSUFF | INSUFF | INSUFF | — | N=0 (structural) |
| R5_breakout__V_high/mid | GO | GO | GO | ✅ GO | |
| R5_breakout__V_low | FAIL | GO | GO | ❌ FAIL | F2 drift 2025-06→07 |
| R6_reversal__V_low/mid/high | GO | GO | GO | ✅ GO | 全 vol bucket 通過 |

### EUR_USD per-cell summary

| Cell | S1 | S2 | S3 | Verdict | Notes |
|------|----|----|----|---------|-------|
| R1_trend_up__V_low/mid/high | GO | GO | GO | ✅ GO | 全 vol bucket 通過 |
| R2_trend_down__V_low/mid/high | GO | GO | GO | ✅ GO | 全 vol bucket 通過 |
| R3_range_tight__V_low | FAIL | GO | GO | ❌ FAIL | F3 drift 2026-02→03 |
| R3_range_tight__V_mid | INSUFF | GO | FAIL | ❌ FAIL | cv=0.447 (>0.4) |
| R3_range_tight__V_high | INSUFF | INSUFF | INSUFF | — | N=0 |
| R4_range_wide__V_high | FAIL | GO | GO | ❌ FAIL | F2 drift 2025-10→11 |
| R4_range_wide__V_mid | INSUFF | GO | GO | — | N=134 |
| R4_range_wide__V_low | INSUFF | INSUFF | INSUFF | — | N=0 |
| R5_breakout__V_low/mid/high | GO | GO | GO | ✅ GO | 全 vol bucket 通過 |
| R6_reversal__V_low/mid/high | GO | GO | GO | ✅ GO | 全 vol bucket 通過 |

### EUR_USD only GO (intersection 外)

- `R2_trend_down__V_low`: USDJPY で S1 FAIL, EURUSD で GO. **pair-specific stability**.
- `R5_breakout__V_low`: 同上.

→ これらは intersection の conservatism で除外される. pair-specific Phase B は v5 で
disallowed. 将来 v6 で個別 pair authorize を検討する選択肢は残る.

## Progression summary (v1 → v5)

| Version | Phase B scope | Notes |
|---------|--------------|-------|
| v1 | 0 (1/3 FAIL) | 固定 threshold |
| v2 | 0 (2/3 structural FAIL) | meta-percentile |
| v3 | 17 (R6 only) | per-regime KS |
| v4 | 0 (EURUSD 1/3) | 2D 化、but pair-level rule で blocked |
| **v5** | **170 (10 cells × 17 strategies)** | **per-cell rule で refinement** |

**v4 → v5 の gain**: 実質的に Phase B scope が unlock. classifier/tests は不変、
rule aggregation のみ一貫性 restore.

## Key achievement: 2D classifier が semantic-stable で authorize された

- **Regime × Vol の 2D 分類** で各 cell が独立した semantic content を持つ
- **10 cells** が両 pair で per-cell 3/3 GO
  - Trend (R1 × 3, R2 × 2): state-based regime も vol conditioning で stable
  - Event (R5 × 2, R6 × 3): event-based regime は引き続き robust
- **R3/R4 は構造的に限定的 N** で authorize 外 (classifier design の制約を honest に認識)

## Phase B execution plan

### 次 session アクション

1. `pre-registration-phase4b-cell-edge-test-<next_date>.md` LOCK
   - 対象: v5 PHASE_B_CELLS 10 cells × 17 strategies = 170
   - Bonferroni M = 170, α_cell = 2.94e-4
   - Per-cell metric: Fisher exact 2-tail p, Wilson 95% CI, Kelly
   - Survivor 基準: p < α_cell ∧ Kelly > 0 ∧ Wilson CI lower > 0
   - Walk-forward: 2-bucket same-sign (前半/後半)

2. 実装 + 検定
   - 既存 17 strategies の trade log を v5 cell label で re-bucket
   - cell ごとに N / WR / EV / PF / Wilson CI / Kelly 計算
   - Bonferroni 通過 cell 同定

3. Strategy routing table 構築
   - Live で bar の cell 判定 → survivor cell のみ entry 許可
   - R0/ FAIL cell は neutral (no entry)

### 想定 survivor

- N per cell: 各 strategy で約 10-40 trades (5% × 10 months × Bonferroni 生存率から)
- Edge detection power: α=2.94e-4 は厳しいが |PHASE_B_CELLS|=10 で overall rate 十分
- 想定 survivor: **1-5 cells/strategy**

## Phase 4 Status Update

| Doc | Status |
|-----|--------|
| v1 pre-reg | 1/3 FAIL (historical) |
| v2 pre-reg | 2/3 structural (historical) |
| v3 pre-reg | 2/3 strict FAIL, R6 only (historical) |
| v4 pre-reg | USDJPY 2/3 / EURUSD 1/3 (historical, common 10 identified) |
| **v5 pre-reg** | **PHASE_B FULL SCOPE AUTHORIZED (10 cells)** |
| Phase B pre-reg | **次 session で LOCK** |
| D1-D4 strategies | Phase B 結果後に design (依然 blocked) |
| [[pre-registration-label-holdout-2026-05-07]] | 独立、予定通り |

## 保持する資産 (Phase 4a 完了時点)

- **v4 2D classifier** (LOCKED): Regime × Vol = 18 cells, 構造的 zero interpretable
- **v5 per-cell rule** (LOCKED): AND aggregation + intersection
- **PHASE_B_CELLS**: 10 cells, Bonferroni M=170, α=2.94e-4
- **Feature set F1-F6 + meta-percentile thresholds**: 変更不要
- **Stability framework**: S1 KS + S2 MK + S3 CV, 各 per-cell で再利用可能
- **Negative knowledge**:
  - R3_tight__V_low / R4_wide__V_high: F3/F2 drift で FAIL, Phase B 対象外
  - R2__V_low / R5__V_low: pair-specific, intersection disallowed
  - R3__V_mid / R4__V_mid / R3__V_high / R4__V_low: N 不足で判定不能

## References

- [[pre-registration-phase4-adaptive-regime-v5-per-cell-rule-2026-04-23]] (本 run prereg)
- [[phase4a-v4-classifier-stability-2026-04-23]] (v4 result)
- [[phase4a-v3-classifier-stability-2026-04-23]] (v3 result)
- [[pre-registration-phase4-adaptive-regime-v4-2D-2026-04-23]] (v4 prereg)
- [[regime-characterization-2026-04-23]] (vol shift 出発点)
- [[lesson-premature-neutralization-2026-04-23]] (discipline 根拠)
- [[pre-registration-phase4-regime-native-2026-04-23]] (D1-D4, Phase B 後)
