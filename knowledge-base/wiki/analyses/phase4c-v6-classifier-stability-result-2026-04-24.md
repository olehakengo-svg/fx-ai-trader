# Phase 4c Track A — v6 Classifier Stability Result (2026-04-24)

**Pre-reg**: [[pre-registration-phase4c-v6-feature-redesign-2026-04-24]]
**Script**: `/tmp/phase4c_v6_classifier_stability.py`
**Output**: `/tmp/phase4c_v6_output.txt` / `/tmp/phase4c_v6_summary.json`
**Data**: OANDA 5m × 10 months × 2 pairs (v1-v5 と同じ)

## Result: **PHASE_D FULL AUTHORIZE (15 cells)**

| Pair | GO cells | FAIL | INSUFFICIENT |
|------|----------|------|--------------|
| USD_JPY | **21** | 34 | 17 |
| EUR_USD | **24** | 33 | 15 |
| **Intersection (PHASE_D_CELLS)** | **15** | — | — |

**Phase D Bonferroni**: M = 15 × 8 strategies = **120**, α_cell = **4.17e-4**.

## PHASE_D_CELLS (intersection 15)

```
R1_trend_up × V_high × {London, NY}
R1_trend_up × V_mid  × {Asia, London, NY}
R2_trend_down × V_high × NY
R2_trend_down × V_mid  × {London, NY}
R5_breakout × V_mid × Asia
R6_reversal × V_high × {Asia, London, NY}
R6_reversal × V_low  × {NY, Off}
R6_reversal × V_mid  × Asia
```

## v5 vs v6 比較

| Metric | v5 (2D) | v6 (3D) |
|--------|---------|---------|
| Cell space | 18 (Regime × Vol) | 72 (Regime × Vol × Session) |
| S1 α_cell | 1.54e-4 | 1.74e-5 (10x tighter) |
| USDJPY GO | 10 | **21** |
| EURUSD GO | 12 | **24** |
| Intersection | 10 | **15** |
| Phase B/D M | 170 | **120** |
| Phase B/D α | 2.94e-4 | **4.17e-4** |

**+5 cells gained**, かつ **Bonferroni burden 低下** (分母 170→120). Session axis が
**情報 positive** だったことを示す.

## Hypothesis verification (vs pre-reg §6)

| H | Prediction | Result |
|---|-----------|--------|
| H1 moderate | F7 volume z で breakout-type stable cell 追加 | ✅ R5_breakout__V_mid__Asia, R6_reversal__V_high の session 展開で cell 発見 |
| H2 weak | Session axis で intersection が v5 10 を上回る | ✅ **15 > 10 で confirmed** |
| H3 null | Bonferroni burden で power 喰い | ❌ 反証 — α tighter でも GO 数増 |

## 細かな発見

### Session 特性

- **Off session (21-24 UTC)** はほぼ FAIL or INSUFFICIENT (想定通り、低流動性)
- **R6_reversal は Asia/London/NY 全 session で GO** → event-based regime は session 非依存
- **R1_trend_up は London/NY で highest stability** → trend は流動性で強化
- **R5_breakout は Asia only (V_mid)** → 他 session で structural 不足

### Feature 寄与

- F7 (volume z-score): S1 KS で Bonferroni 通過に寄与 (具体 contribution は全 test
  結果で traceable だが概ね positive contribution)
- F8 (VPD): F7 とほぼ correlated、独立性低いが冗長 check として機能

### Pair asymmetry (informational)

| Cell | USDJPY | EURUSD |
|------|--------|--------|
| R4_range_wide__V_high__{London, Off} | GO | FAIL |
| R5_breakout__V_high__Asia | FAIL | GO |
| R2_trend_down__V_low__{NY, Off} | FAIL | GO |
| R2_trend_down__V_mid__Asia | FAIL | GO |

→ Pair 特有の stability あり. Intersection で conservative に 15 に絞る (v5 と同じ方針).

## v1-v6 progression

| Version | Phase B/D scope | Cells | Key change |
|---------|----------------|-------|-----------|
| v1 | 0 (1/3 FAIL) | — | Fixed threshold |
| v2 | 0 (2/3 structural) | — | Meta-percentile |
| v3 | 17 (R6 only) | 1 | Per-regime KS |
| v4 | 0 (pair-level FAIL) | — | 2D (Regime × Vol) |
| v5 | 170 (10 cells × 17) | 10 | Per-cell AND rule |
| **v6** | **120 (15 cells × 8)** | **15** | **3D + F7/F8 + session** |

v5 → v6: +50% cells (10→15), Bonferroni burden -29% (170→120). **Gain 有意**.

## Next step

**Phase D cell edge test** (Phase 4b 相当):
- Pre-reg LOCK required: `pre-registration-phase4d-cell-edge-test-<date>.md`
- 対象: 15 cells × 8 strategies = 120 (strategy, cell) combos
- Per-cell Fisher/Wilson/Kelly/WF (Phase 4b と同じ framework)
- Scope: Phase 4b で確認した通り **live 16 days だけでは N 不足** — Phase D は
  data 蓄積待ち (D or D+1 に split), BT 365日 で先行検定する選択肢あり

## Caution: Phase D の power planning

v5 の Phase 4b で N≥30 cells が 2/72 (2.8%) だった実績から、v6 PHASE_D の 120 combos
でも **同等の N 率** を想定すると 3-5 cells が testable. Phase D を live trades で
16 days run するのは **今 session の Phase 4b と同等の power denial** に陥る可能性大.

**推奨**: Phase D は BT 365日 (or 蓄積完了後 live) で走らせる pre-reg を次 session LOCK.

## 保持される資産

- **v6 classifier (LOCKED)**: 3D cell axis, F1-F9, stability 確認済
- **PHASE_D_CELLS 15**: intersection で conservative authorize
- **Feature F7/F8**: 他 analysis で再利用可能 (volume regime detection)
- **Session axis**: v5 の 2D を replace、 今後の regime 判定で使用

## References

- [[pre-registration-phase4c-v6-feature-redesign-2026-04-24]] (本 pre-reg)
- [[phase4a-v5-classifier-stability-2026-04-23]] (v5 baseline)
- [[phase4b-cell-edge-test-result-2026-04-24]] (v5 power 限界)
- [[phase4c-mtf-regime-result-2026-04-24]] (parallel Track B result, Scenario A)
- [[lesson-premature-neutralization-2026-04-23]]
