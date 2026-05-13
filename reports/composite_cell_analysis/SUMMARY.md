# Composite Cell Analysis Summary

VERDICT: HOLD_GAP5_COMPOSITE

This is a retrospective hypothesis-forming analysis on the frozen Phase B2.5 BT trade log. It must not be reused as Live promotion evidence or as proof that a Shadow gate is production-safe.

## Main Results

- Trades evaluated: 5617
- Composite global cells: 6 fixed dow_regime x v2_regime cells
- Bonferroni effective m: 46
- Bonferroni passing strategy composite cells: 10
- Best prediction model by Brier score: `v2_only`

## Global Composite Crosstab

| dow_regime | v2_regime | N | wins | WR | EV_pip | PF | Wilson_lo | Kelly |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TRENDING | moderate_trend | 98 | 59 | 0.602041 | 0.042813 | 1.04833 | 0.503048 | 0.027756 |
| TRENDING | no_go | 1070 | 663 | 0.619626 | 0.268257 | 1.38867 | 0.590158 | 0.173424 |
| RANGING | moderate_trend | 226 | 125 | 0.553097 | -0.076805 | 0.911703 | 0.487928 | -0.053567 |
| RANGING | no_go | 934 | 555 | 0.594218 | 0.139989 | 1.18782 | 0.562403 | 0.093959 |
| CHOP | moderate_trend | 481 | 270 | 0.561331 | -0.004808 | 0.994157 | 0.516671 | -0.003299 |
| CHOP | no_go | 2808 | 1693 | 0.60292 | 0.173538 | 1.23478 | 0.584694 | 0.114638 |

## Prediction Power

| model | features | N | brier_score | log_loss |
| --- | --- | --- | --- | --- |
| v2_only | v2_regime | 5617 | 0.240151 | 0.673315 |
| dow_only | dow_regime | 5617 | 0.240328 | 0.673684 |
| composite | dow_regime+v2_regime | 5617 | 0.240401 | 0.673833 |

## Recommendation

D: compositeではedgeが強化されていないため、Gap 5 / Phase Eの再定義は保留する。
