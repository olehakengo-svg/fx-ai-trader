# Gap 1 Cross-Pair Confluence Summary

VERDICT: CONDITIONAL_EDA_CANDIDATE

## Scope

- Source: `reports/regime_gate_phase_b2/trade_log_tagged.csv`
- Trades evaluated: 5617
- Cache: local MASSIVE 1h parquet; DXY uses proxy when no `DXY_1h.parquet` exists.
- Live impact: none. This is retrospective EDA and observation-layer tagging only.

## Global Crosstab

| confluence_score | N | wins | WR | EV_pip | PF | Wilson_lo |
| --- | --- | --- | --- | --- | --- | --- |
| MIXED | 3392 | 1867 | 0.550413 | 0.00514 | 1.0064 | 0.533624 |
| STRONG | 541 | 368 | 0.680222 | 0.345456 | 1.51312 | 0.639768 |
| WEAK | 1684 | 1130 | 0.671021 | 0.406934 | 1.62309 | 0.648214 |

## Bonferroni

- strategy x confluence eligible cells: 36
- passing strategy x confluence cells: 13
- strategy x dow x v2 x confluence eligible cells: 44
- passing strategy x dow x v2 x confluence cells: 8

Top adjusted rows:

| entry_type | dow_regime | v2_regime | confluence_score | N | wins | WR | EV_pip | PF | Wilson_lo | m_eff | alpha_prime | p_value | bonferroni_pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| streak_reversal | CHOP | no_go | MIXED | 166 | 116 | 0.698795 | 0.882467 | 2.14647 | 0.625154 | 44 | 0.00113636 | 1.60542e-07 | True |
| session_time_bias | CHOP | no_go | WEAK | 168 | 116 | 0.690476 | 0.32494 | 1.53188 | 0.616965 | 44 | 0.00113636 | 4.36957e-07 | True |
| xs_momentum | CHOP | no_go | WEAK | 215 | 139 | 0.646512 | 0.152556 | 1.23087 | 0.580549 | 44 | 0.00113636 | 1.03643e-05 | True |
| streak_reversal | CHOP | no_go | WEAK | 58 | 43 | 0.741379 | 1.20579 | 2.86079 | 0.616224 | 44 | 0.00113636 | 0.000153474 | True |
| xs_momentum | TRENDING | no_go | WEAK | 166 | 106 | 0.638554 | 0.19346 | 1.31532 | 0.5631 | 44 | 0.00113636 | 0.000221663 | True |
| streak_reversal | TRENDING | no_go | MIXED | 62 | 45 | 0.725806 | 1.03112 | 2.66627 | 0.604072 | 44 | 0.00113636 | 0.000248546 | True |
| streak_reversal | RANGING | no_go | MIXED | 51 | 38 | 0.745098 | 0.961583 | 2.06787 | 0.611315 | 44 | 0.00113636 | 0.000310522 | True |
| session_time_bias | RANGING | no_go | MIXED | 137 | 88 | 0.642336 | 0.185867 | 1.28146 | 0.559198 | 44 | 0.00113636 | 0.000545512 | True |
| session_time_bias | CHOP | no_go | MIXED | 434 | 251 | 0.578341 | -0.035985 | 0.953972 | 0.531392 | 44 | 0.00113636 | 0.000636668 | False |
| session_time_bias | TRENDING | no_go | MIXED | 119 | 76 | 0.638655 | 0.188724 | 1.28825 | 0.549256 | 44 | 0.00113636 | 0.00159159 | False |
| sr_fib_confluence | RANGING | no_go | WEAK | 54 | 38 | 0.703704 | 0.272495 | 1.57116 | 0.571722 | 44 | 0.00113636 | 0.00191913 | False |
| xs_momentum | TRENDING | no_go | STRONG | 63 | 43 | 0.68254 | 0.203166 | 1.3348 | 0.559962 | 44 | 0.00113636 | 0.0025762 | False |

## Confluence Distribution

- STRONG N: 541
- WEAK N: 1684
- MIXED N: 3392

## Next Action

forward Shadow accumulation only; do not convert confluence into a universal gate.
