# Composite Cell Analysis Summary

VERDICT: HOLD_GAP5_COMPOSITE

feedback_label_empirical_audit: HOLD_GAP5_COMPOSITE

This is a retrospective hypothesis-forming analysis on the frozen Phase B2.5 BT trade log. It must not be reused as Live promotion evidence or as proof that a Shadow gate is production-safe.

## Main Results

- Trades evaluated: 5617
- Composite global cells: 6 fixed dow_regime x v2_regime cells
- Bonferroni effective m: 47
- Bonferroni passing strategy composite cells: 10
- Best prediction model by Brier score: `v2_only`
- Production guard: classifier thresholds, production code, DB, `.env`, and external credentials were not changed.

## Global Composite Crosstab

| dow_regime | v2_regime | N | wins | WR | EV_pip | PF | Wilson_lo | Kelly |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TRENDING | moderate_trend | 104 | 60 | 0.576923 | -0.051362 | 0.94377 | 0.480896 | -0.034373 |
| TRENDING | no_go | 1064 | 662 | 0.62218 | 0.278734 | 1.40608 | 0.592657 | 0.179688 |
| RANGING | moderate_trend | 232 | 137 | 0.590517 | 0.023542 | 1.02867 | 0.526266 | 0.016457 |
| RANGING | no_go | 928 | 543 | 0.585129 | 0.116304 | 1.1537 | 0.553141 | 0.077954 |
| CHOP | moderate_trend | 485 | 280 | 0.57732 | 0.030478 | 1.03809 | 0.532917 | 0.021185 |
| CHOP | no_go | 2804 | 1683 | 0.600214 | 0.167689 | 1.22569 | 0.581957 | 0.110521 |

## Prediction Power

| model | features | N | brier_score | log_loss |
| --- | --- | --- | --- | --- |
| v2_only | v2_regime | 5617 | 0.2403 | 0.673625 |
| dow_only | dow_regime | 5617 | 0.240328 | 0.673684 |
| composite | dow_regime+v2_regime | 5617 | 0.240512 | 0.674062 |

## Recommendation

D: compositeではedgeが強化されていないため、Gap 5 / Phase Eの再定義は保留する。
