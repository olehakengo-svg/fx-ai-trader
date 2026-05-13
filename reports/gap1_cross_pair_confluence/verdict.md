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
- `proposals.csv`
- `component_coverage.csv`

## Result

| confluence_score | N | wins | WR | EV_pip | PF | Wilson_lo |
| --- | --- | --- | --- | --- | --- | --- |
| MIXED | 3684 | 2055 | 0.557818 | 0.0214 | 1.02694 | 0.541728 |
| WEAK | 1933 | 1310 | 0.677703 | 0.419434 | 1.64193 | 0.656534 |

## Risk

Pairs with only two literal requirements cannot produce STRONG by the pre-registered 3-confirmation threshold. That is preserved rather than post-hoc tuned.
