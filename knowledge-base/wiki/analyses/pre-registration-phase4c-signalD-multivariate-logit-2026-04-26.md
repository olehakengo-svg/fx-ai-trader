# Pre-registration: Phase 4c Signal D — Multivariate Logit Variance Decomposition (2026-04-26)

**Locked**: 2026-04-26 (本 doc 確定後変更禁止)
**Track**: B / Phase II (per plan Section 2)
**Plan**: `/Users/jg-n-012/.claude/plans/mtf-rustling-candle.md`
**Upstream**:
- [[phase4c-signalC-field-ranking-result-2026-04-26]] (Scenario B, 4 CANDIDATE)
- [[phase4c-mtf-alignment-bug-audit-2026-04-26]] (Finding 1-4 confounder 設計に反映)

## 0. Rationale

Phase I (Signal C) で 4 CANDIDATE cell を検出した. これらが pair/session/spread/vol を
control 後も生き残るかを multivariate logit で判定する. **Audit findings を直接反映**:

- F1: `mtf_d1_label` は bear case が 0 件 → **本 phase では除外** (uninformative)
- F4: aligned subset の WR は GBP_USD × spread artifact → **pair, spread_quartile を
  必須 confounder に追加**
- F3: `mtf_alignment` は 04-20 以降のみ populate → **alignment 分析は subset で**

## 1. Population (LOCKED)

- Source: production API trades, 2026-04-08 以降, WIN/LOSS, 8 strategies, excl XAU
- 期待 N: ~1804 (Phase I scope)
- 各 trade に以下を attach: spread_at_entry → pair-conditional quartile, session_name,
  hour_of_day

## 2. Model spec (LOCKED)

### 2.1 Outcome
`win ∈ {0, 1}` (LOSS=0, WIN=1)

### 2.2 Confounders (always-in, M_C = 5 categorical features)
- `entry_type` (8-class, fixed effect)
- `instrument` (≤6-class)
- `session_name` (Tokyo/London/NewYork/Overlap; UTC hour-of-day から導出)
- `spread_q` (pair-internal quartile of spread_at_entry; 4-class)
- `mtf_vol_state` (squeeze/normal/expansion)

### 2.3 Regime features (test target, M_R = 3)
- `mtf_h4_label` (-1, 0, +1; 3=insufficient → excluded row)
- `range_sub_filled` (SQUEEZE/WIDE_RANGE/TRANSITION/NONE; NONE = trade not in
  range regime)
- `regime_4` (TREND_BULL/BEAR/RANGE/HIGH_VOL; from `regime.regime` JSON)

### 2.4 Interactions (test target, M_I = 1 set)
- `entry_type × mtf_h4_label` (Phase I で h4_label が最も汎用 → strategy 別効果検定)

### 2.5 Excluded a priori
- `mtf_d1_label` (audit F1: bear case 0 件で uninformative)
- `mtf_regime` (compose_regime composite, regime_4 と相関高、VIF 警戒)
- `mtf_alignment` (本 phase の primary model からは除外、§4 secondary で subset 検定)

## 3. Test design (LOCKED)

### 3.1 Primary: Likelihood Ratio test on regime block

```
Model_null:  win ~ confounders                    (df_null)
Model_full:  win ~ confounders + regime + interactions  (df_full)
LR = -2(LL_null - LL_full) ~ chi2(df_full - df_null)
```

α_primary = **0.05** (single hypothesis: "regime adds info beyond confounders").

### 3.2 Secondary 1: per-strategy interaction Wald test

各 8 strategy について `entry_type × mtf_h4_label` interaction の Wald test.
Bonferroni: M = 8, α_inter = 0.05/8 = **6.25e-3**.

### 3.3 Secondary 2: GBM feature importance

`sklearn.ensemble.GradientBoostingClassifier(n_estimators=200, max_depth=3,
random_state=42)` を **同じ feature set** で fit. permutation importance も並行算出.

判定 sub-rule (R1 認可の補強):
- regime block の **mean importance ≥ 5%** で "regime is non-trivial signal"
- < 5% で "regime is noise relative to confounders"

### 3.4 Tertiary: aligned subset analysis (audit F3 反映)

`entry_time >= 2026-04-20` subset (N≈368 aligned + others) で `mtf_alignment` を加えた
extended model:
```
Model_ext: confounders + regime + mtf_alignment + entry_type×mtf_alignment
```
LR vs Model_full. **α=0.05/3 = 0.0167** (Bonferroni against 3 secondary tests).

## 4. SURVIVOR / CANDIDATE / Scenario (LOCKED)

| Decision | Criteria |
|----------|----------|
| **SURVIVOR** | Primary LR p<0.05 ∧ GBM regime importance ≥5% ∧ ≥1 strategy interaction Bonferroni 通過 |
| **CANDIDATE** | Primary LR p<0.05 ∧ GBM importance ≥5% (interaction 未通過) |
| **WEAK** | Primary LR p<0.05 ∧ GBM importance <5% (Type I error 疑い) |
| **NULL** | Primary LR p≥0.05 |

| Scenario | Rule | Action |
|----------|------|--------|
| C | SURVIVOR | Phase III (per-pair) で deeper cut 認可 |
| B | CANDIDATE/WEAK | Phase IV (regime persistence) に移行、CANDIDATE 維持 |
| A | NULL | "regime route 全体は marginal effect 不在" の確定 evidence、Track B closure 検討 |

## 5. Disallowed

- §2 feature 追加・削除 (post-hoc)
- §3 α 緩和
- Confounder の事後除外
- Subset 取り直し (cherry-pick)
- LR / Wald 以外の test stat への変更

## 6. Pre-registered hypotheses

| H | Type | Prediction |
|---|------|-----------|
| H1 | strong | Primary LR p<0.05 (regime adds info) |
| H2 | moderate | GBM regime importance 5-15% (non-trivial だが confounder 主導) |
| H3 | weak | ≥1 strategy interaction が Bonferroni 通過 (bb_squeeze × h4_label が候補) |
| H4 | overall | Scenario B (CANDIDATE) — power-limited で SURVIVOR 不到達 |

## 7. Execution

- Script: `/tmp/phase4c_signalD_multivariate_logit.py`
- Output: `/tmp/phase4c_signalD_output.txt`, `/tmp/phase4c_signalD_summary.json`
- Result KB: `knowledge-base/wiki/analyses/phase4c-signalD-multivariate-result-2026-04-26.md`
- Libraries: `statsmodels.api.GLM` (Binomial), `sklearn.ensemble.GradientBoostingClassifier`

## References

- [[pre-registration-phase4c-signalC-field-ranking-2026-04-26]]
- [[phase4c-signalC-field-ranking-result-2026-04-26]]
- [[phase4c-mtf-alignment-bug-audit-2026-04-26]]
- `/Users/jg-n-012/.claude/plans/mtf-rustling-candle.md`
