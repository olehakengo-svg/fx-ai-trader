# Gap 1 Cross-Pair Confluence Verdict

VERDICT: CONDITIONAL_EDA_CANDIDATE

This run does not authorize Live promotion or a universal confluence gate. It only adds the observation tag and checks whether the frozen Phase B2.5 trade log shows enough retrospective structure to justify forward collection.

## Artifacts

- `trade_log_with_confluence.csv`
- `crosstab_global.csv`
- `crosstab_by_strategy.csv`
- `composite_4axis_strategy_dow_v2_confluence.csv`
- `bonferroni_by_strategy_confluence.csv`
- `bonferroni_by_strategy_dow_v2_confluence.csv`

## Result

| confluence_score | N | wins | WR | EV_pip | PF | Wilson_lo |
| --- | --- | --- | --- | --- | --- | --- |
| MIXED | 3392 | 1867 | 0.550413 | 0.00514 | 1.0064 | 0.533624 |
| STRONG | 541 | 368 | 0.680222 | 0.345456 | 1.51312 | 0.639768 |
| WEAK | 1684 | 1130 | 0.671021 | 0.406934 | 1.62309 | 0.648214 |

## Risk

Pairs with only two literal requirements cannot produce STRONG by the pre-registered 3-confirmation threshold. That is preserved rather than post-hoc tuned.
