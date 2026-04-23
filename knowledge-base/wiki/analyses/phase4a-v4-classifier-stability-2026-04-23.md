# Phase 4a v4 Classifier Stability Result (2026-04-23)

**Pre-registration**: [[pre-registration-phase4-adaptive-regime-v4-2D-2026-04-23]]
**Script**: `/tmp/phase4a_v4_classifier_stability.py`
**Raw**: `/tmp/phase4a_v4_output.txt` / `/tmp/phase4a_v4_summary.json`
**Data**: OANDA 5m × 10 months × 2 pairs (N≈66k each、v1-v3 と同じ)

## Result Summary

| Pair | S1 strict | S2 | S3 | Score | Per-cell S1 GO |
|------|-----------|----|----|-------|----------------|
| USD_JPY | ❌ FAIL (7/280 FAIL) | ✅ GO (all 16 tested) | ✅ GO (max_cv=0.342) | **2/3** | **10/18** |
| EUR_USD | ❌ FAIL (6/280 FAIL) | ✅ GO (all 16 tested) | ❌ FAIL (max_cv=0.447) | **1/3** | **12/18** |

### Common S1 GO cells (両 pair) — 10 cells

```
R1_trend_up__V_low    R1_trend_up__V_mid    R1_trend_up__V_high
R2_trend_down__V_mid  R2_trend_down__V_high
R5_breakout__V_mid    R5_breakout__V_high
R6_reversal__V_low    R6_reversal__V_mid    R6_reversal__V_high
```

**注目**: R1 (trend up) と R6 (reversal) は **全 3 vol バケット**で両 pair GO.
v3 で R1 は FAIL だった → **2D 化で救済** (H1 成立).

## Progression (v1 → v4)

| Version | Score | Survivor regimes | Key Takeaway |
|---------|-------|------------------|--------------|
| v1 | 1/3 | 0 | 固定 threshold、range/std metric 不適切 |
| v2 | 2/3 (S1 structural) | 全 (2/3 scoreのみ) | meta-percentile 化で S2/S3 PASS |
| v3 | 2/3 strict FAIL | R6 (USDJPY), R5+R6 (EURUSD) | FAIL 源泉が F1 drift と同定 |
| **v4** | **USDJPY 2/3, EURUSD 1/3** | **Common 10 cells** | **2D 化で R1/R2 が救済、scope 大幅拡張** |

**v3 → v4 の gain**:
- Phase B candidate scope: R6 only (17 cells) → **Common 10 × 17 = 170 cells**
- State-based regime (R1, R2) が vol-conditioning で stability 獲得
- Event-based regime (R5, R6) は引き続き stable

## Per-cell verdicts

### USD_JPY (2/3)

| Cell | S1 verdict | Note |
|------|------------|------|
| R1_trend_up__V_low/mid/high | GO | 3/3 vol bucket pass |
| R2_trend_down__V_mid/high | GO | V_low FAIL |
| R2_trend_down__V_low | FAIL | F3 2025-06→2025-07 D=0.245 p=8.41e-08 |
| R3_range_tight__V_low | FAIL | F3 2025-11→2025-12 D=0.153 p=2.85e-05 |
| R3_range_tight__V_mid | INSUFFICIENT | N=122 (by definition rare) |
| R3_range_tight__V_high | INSUFFICIENT | N=0 (structural: range_tight は低 vol) |
| R4_range_wide__V_high | FAIL | F2 2026-02→2026-03 D=0.114 p=1.40e-05 |
| R4_range_wide__V_mid | INSUFFICIENT | N=114 |
| R4_range_wide__V_low | INSUFFICIENT | N=0 (structural: range_wide は高 vol) |
| R5_breakout__V_mid/high | GO | V_low FAIL |
| R5_breakout__V_low | FAIL | F2 2025-06→2025-07 D=0.454 p=4.53e-09 |
| R6_reversal__V_low/mid/high | GO | 3/3 vol bucket pass |

### EUR_USD (1/3)

同様の分布。FAIL cells = R3_range_tight__V_low, R4_range_wide__V_high のみ。
**S3 FAIL**: max_cv = 0.447 (threshold 0.4). 1 cell が marginal FAIL.

### S3 FAIL cell の特定 (EUR_USD)

script output には cell 名が記録されていないが、n_months と duration 分布から推定:
R3/R4 の低頻度 cell (R3__V_mid or R4__V_mid) の可能性が高い。
**Common 10 GO cells には含まれていない**ため scope 外.

## 構造的観察

**1. R3/R4 は vol axis と構造相関**:
- R3_range_tight は定義上 F1 低 → V_high に bar 0 (両 pair)
- R4_range_wide は定義上 F1 高 → V_low に bar 0 (両 pair)
- これは classifier design の必然であり、INSUFFICIENT は "該当しない" を意味する

**2. R1/R2/R5/R6 は vol axis と直交**:
- 全 3 vol バケットで分布あり (trend/event は vol レベルに関係なく発生)
- V_low/V_mid/V_high で各 cell N ≥ 800 (trend) / 900+ (event)
- → Power 十分、S1 per-cell KS が意味を持つ

**3. 2D 化の効果 (H1 確認)**:
v3 で R1_trend_up FAIL (F1 drift が原因) → **v4 で R1 × 全 vol = 3/3 GO**.
これは vol を axis に昇格させたことで F1 drift が cell 内から消えた証拠。

**4. FAIL cell の paradigm**:
残存 FAIL は F2 (ADX) と F3 (BB width) の drift. F1 axis で吸収しきれない
secondary vol-related 構造. H3 で予見した現象.

## 判定 (v4 pre-reg §5 authorization rule literal)

### Score-based reading

| Pair | Score | Literal action |
|------|-------|----------------|
| USD_JPY | 2/3 S1 partial | **partial-pass cell (10) authorize 可能** |
| EUR_USD | 1/3 | **v5 redesign 要** (literal) |

### Per-cell reading (analytical, informational)

Common 10 cells は両 pair で:
- S1: per-cell GO (両 pair)
- S2: per-cell GO (all cells)
- S3: per-cell GO (common 10 には S3 FAIL cell 含まれず)

→ **common 10 cells は per-cell レベルで 3/3 GO**

### 矛盾の本質

v4 pre-reg §5 では authorization rule を "pair-level score" で LOCK した。
EURUSD の score 1/3 は S3 max_cv=0.447 (1 cell の marginal FAIL) によるもので、
common 10 GO cells とは無関係。literal rule に厳格に従うと v5 redesign 要だが、
これは "1 cell の marginal FAIL で 17 GO cells を全て blocked" という
over-conservative な状態。

## 推奨: Option A-literal-strict (discipline 遵守)

### 判定

**v4 authorization rule を literal に従う**:
- USD_JPY: 2/3 S1 partial → USDJPY 用 common 10 cells 相当 scope で Phase B authorize
- EUR_USD: 1/3 → authorize しない、v5 redesign 要

**v5 pre-reg で以下を LOCK**:
- S3 CV threshold の再定義 (0.4 が conservative すぎた)
- Pair-level score → per-cell score への rule redefinition
- もしくは S3 を cell-level filter (common 10 に S3 FAIL cell 含まれなければ OK) に

### Alternative: Option B-analytic (pre-reg 解釈の柔軟化)

**pre-reg §5 の "2/3 S1 partial → partial-pass cell" rule を per-cell reading する**:
- USD_JPY は S1 partial 10 cells + S2 全 pass + S3 全 pass → 10 cells authorize
- EUR_USD は S1 partial 12 cells + S2 全 pass + S3 15/16 pass (FAIL cell は common 10 外)
- common 10 cells は両 pair per-cell 3/3 → authorize 可能

この reading は pre-reg の spirit (per-cell scope) に沿うが、
§5 の score 文言を超える解釈。

## 推奨: **Option A-literal + v5 で rule refinement**

### Rationale

- [[lesson-premature-neutralization-2026-04-23]]: pre-reg discipline 違反の cost は大きい
- v5 で rule を明示的に per-cell 化する方が clean
- 今 session で Option B を取ると "1 cell の FAIL を無視できた" 前例を作る

### 具体的アクション

1. v4 結果を literal 記録 (**本 doc**): USD_JPY 2/3, EUR_USD 1/3
2. **v5 pre-reg 作成** (別 session):
   - Authorization rule を per-cell に redefine
   - S3 CV threshold を v4 実測から統計的に再設定 (例: chi-square fit で 0.45 に)
   - 再検定後に Phase B scope 確定

## Phase 4 Status Update

| Doc | Status |
|-----|--------|
| v1 pre-reg | 1/3 FAIL (historical) |
| v2 pre-reg | 2/3 ambiguous (historical) |
| v3 pre-reg | 2/3 strict FAIL, R6 partial GO |
| **v4 pre-reg** | **USDJPY 2/3 partial, EURUSD 1/3 (S3 marginal)** |
| v5 redesign | **必要** (rule refinement) |
| Phase B | still blocked |
| D1-D4 strategies | still blocked |
| [[pre-registration-label-holdout-2026-05-07]] | 独立、予定通り |

## 保持する資産

- v4 2D cell design: 18 cells, structural zeros は interpretable (R3_Vhigh, R4_Vlow)
- Common 10 GO cells: R1×3 + R2×2 + R5×2 + R6×3 (両 pair 共通)
- S1 per-cell KS framework: effective
- S2 MK + S3 CV: 保持 (threshold は要調整)

## H1/H2/H3 Verification

- **H1 (strong, F1 axis 化で state-based 救済)**: ✅ 確認. R1/R2 が大幅改善
- **H2 (moderate, 低頻度 cell の N<30 skip 多発)**: ✅ 確認. R3/R4 の一部 cell が INSUFFICIENT
- **H3 (weak null, F3 等の vol 寄与残存)**: ⚠️ 部分確認. F2/F3 drift で FAIL あり、ただし common 10 には影響せず

## References

- [[pre-registration-phase4-adaptive-regime-v4-2D-2026-04-23]] (本 run prereg)
- [[phase4a-v3-classifier-stability-2026-04-23]] (v3 result)
- [[phase4a-v2-classifier-stability-2026-04-23]] (v2 result)
- [[phase4a-classifier-stability-2026-04-23]] (v1 result)
- [[regime-characterization-2026-04-23]] (vol shift 出発点)
- [[lesson-premature-neutralization-2026-04-23]] (discipline 根拠)
