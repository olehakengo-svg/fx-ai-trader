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
| MIXED | 3684 | 2055 | 0.557818 | 0.0214 | 1.02694 | 0.541728 |
| WEAK | 1933 | 1310 | 0.677703 | 0.419434 | 1.64193 | 0.656534 |

## Bonferroni

- strategy x confluence eligible cells: 33
- passing strategy x confluence cells: 10
- strategy x dow x v2 x confluence eligible cells: 46
- passing strategy x dow x v2 x confluence cells: 11

Top adjusted rows:

| entry_type | dow_regime | v2_regime | confluence_score | N | wins | WR | EV_pip | PF | Wilson_lo | m_eff | alpha_prime | p_value | bonferroni_pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| session_time_bias | CHOP | no_go | WEAK | 179 | 126 | 0.703911 | 0.34642 | 1.57687 | 0.633314 | 46 | 0.00108696 | 2.43416e-08 | True |
| xs_momentum | CHOP | no_go | WEAK | 262 | 172 | 0.656489 | 0.166228 | 1.25727 | 0.597097 | 46 | 0.00108696 | 2.28125e-07 | True |
| streak_reversal | CHOP | no_go | MIXED | 164 | 114 | 0.695122 | 0.874845 | 2.19459 | 0.620866 | 46 | 0.00108696 | 3.1658e-07 | True |
| xs_momentum | TRENDING | no_go | WEAK | 217 | 141 | 0.64977 | 0.18571 | 1.30085 | 0.584193 | 46 | 0.00108696 | 6.06028e-06 | True |
| sr_fib_confluence | CHOP | no_go | WEAK | 144 | 97 | 0.673611 | 0.192545 | 1.33608 | 0.593381 | 46 | 0.00108696 | 1.87785e-05 | True |
| streak_reversal | CHOP | no_go | WEAK | 78 | 56 | 0.717949 | 1.15285 | 2.78458 | 0.609689 | 46 | 0.00108696 | 7.47408e-05 | True |
| streak_reversal | TRENDING | no_go | WEAK | 34 | 28 | 0.823529 | 1.83502 | 6.13618 | 0.664859 | 46 | 0.00108696 | 9.75628e-05 | True |
| trendline_sweep | CHOP | no_go | MIXED | 66 | 48 | 0.727273 | 0.796683 | 2.15316 | 0.609575 | 46 | 0.00108696 | 0.000143559 | True |
| session_time_bias | TRENDING | no_go | MIXED | 131 | 85 | 0.648855 | 0.219232 | 1.34726 | 0.563935 | 46 | 0.00108696 | 0.000416021 | True |
| streak_reversal | TRENDING | no_go | MIXED | 63 | 45 | 0.714286 | 1.03026 | 2.64351 | 0.59297 | 46 | 0.00108696 | 0.000449024 | True |
| streak_reversal | RANGING | no_go | MIXED | 50 | 37 | 0.74 | 1.01324 | 2.15227 | 0.604466 | 46 | 0.00108696 | 0.000468111 | True |
| session_time_bias | CHOP | no_go | MIXED | 466 | 271 | 0.581545 | -0.033204 | 0.957526 | 0.536267 | 46 | 0.00108696 | 0.000249539 | False |

## Component Coverage

| component | N | confirmed | missing_or_error | flat | confirm_rate | missing_error_rate |
| --- | --- | --- | --- | --- | --- | --- |
| USD_CHF | 5617 | 0 | 5617 | 0 | 0 | 1 |
| DXY | 5617 | 3035 | 0 | 556 | 0.540324 | 0 |
| EUR_JPY | 1520 | 722 | 0 | 151 | 0.475 | 0 |
| EUR_USD | 2130 | 1029 | 0 | 228 | 0.483099 | 0 |
| GBP_JPY | 1967 | 927 | 0 | 209 | 0.471276 | 0 |

Missing/error components are not imputed and do not confirm confluence. The mapping remains literal; no post-hoc replacement is applied.

## Confluence Distribution

- STRONG N: 0
- WEAK N: 1933
- MIXED N: 3684

## Next Action

forward Shadow accumulation only; do not convert confluence into a universal gate.
