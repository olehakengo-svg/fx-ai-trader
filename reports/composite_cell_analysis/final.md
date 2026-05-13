# Composite Cell Retrospective Final

Artifact commit: `3665db2c analysis(codex): composite cell retrospective sanity`

## Scope

- Source: `reports/regime_gate_phase_b2/trade_log_tagged.csv`
- Trades evaluated: 5617
- Analysis type: retrospective hypothesis-forming EDA only.
- Live promotion evidence: no.
- Shadow admission proof: no.
- Production changes: none.

## Artifacts

- `crosstab_global.csv`
- `crosstab_by_strategy.csv`
- `crosstab_top_strategies.csv`
- `17_proposals_composite.csv`
- `bonferroni_evaluation.csv`
- `prediction_power_comparison.csv`
- `verdict.md`
- `SUMMARY.md`

## Verdict

VERDICT: `HOLD_GAP5_COMPOSITE`

feedback_label_empirical_audit: `HOLD_GAP5_COMPOSITE`

Recommendation: D. Composite did not improve prediction power over the single classifiers, so Gap 5 / Phase E composite redefinition should be held.

## Validation Snapshot

- Global composite rows: 6
- Proposal rows: 34
- Proposal count: 17
- Proposal split N sum check: true
- Bonferroni m_eff: 47
- Bonferroni passing strategy composite cells: 10
- Best prediction model by Brier score: `v2_only`

Prediction power:

| model | features | N | brier_score | log_loss |
| --- | --- | --- | --- | --- |
| v2_only | v2_regime | 5617 | 0.240300289 | 0.673625204 |
| dow_only | dow_regime | 5617 | 0.240327522 | 0.673683727 |
| composite | dow_regime+v2_regime | 5617 | 0.240512178 | 0.674062178 |

## Git Log Snapshot

```text
3665db2c analysis(codex): composite cell retrospective sanity
08a1bf95 chore(codex): claim 20260513-1830-composite-cell-retrospective-analysis
c037ad15 chore(codex): claim 20260513-1800-v2-regime-universal-tagging
d8199053 feat(codex): complete 20260513-1500-universal-dow-regime-tagging
ccb8f52d docs(codex): record dow_regime completion hash
```
