# FX Nexus Step 1 Pre-Registration LOCK

Date: 2026-05-04
Scope: FX Nexus Step 1 data-layer shadow audit for the 5-pair FX universe.

This document freezes the statistical gates before reading the Step 1 shadow
audit output. Post-hoc threshold changes are out of scope.

## Universe

- Pairs: USD_JPY, EUR_USD, GBP_USD, EUR_JPY, GBP_JPY
- Currencies: USD, EUR, GBP, JPY
- Horizon: H1 next bar
- Data separation: FX only, XAU excluded, LIVE and Shadow separated
- LIVE entry audit filter: `is_shadow=0` and non-empty `oanda_trade_id`

## H1 Currency Value V_ti

| Metric | ACCEPT | NEEDS_MORE | REJECT |
|---|---|---|---|
| MLE condition number | < 1e6 | 1e6-1e9 | > 1e9 |
| Correlation vs basket_strength | 0.7-0.99 | out of band | < 0.7 or > 0.99 |
| H1 next-bar predictive Wilson lower | >= 0.51 | 0.49-0.51 | < 0.49 |
| N | >= 4000 | 2000-4000 | < 2000 |

## H2 Alpha Residual

Alpha residual is defined as:

```text
alpha_tij = log(X_tij) - (log(V_i) - log(V_j))
```

| Metric | ACCEPT | NEEDS_MORE | REJECT |
|---|---|---|---|
| All 5-pair Bonferroni p, m=5 | < 0.01 all pairs | 1-4 pairs | 0 pairs |
| alpha magnitude vs spread correlation | < 0.30 | 0.30-0.50 | > 0.50 |
| alpha autocorrelation lag 1 H1 | < 0.50 | 0.50-0.70 | > 0.70 |
| LIVE entry alpha bias, Kruskal-Wallis | p < 0.05 | p < 0.10 | p >= 0.10 |

H2 ACCEPT is required before drafting a Wave 5 alpha reversion MR strategy spec.

## H3 Tau Exec Jitter

| Metric | ACCEPT | NEEDS_MORE | REJECT |
|---|---|---|---|
| squeeze_release_momentum PF drop, jitter ON vs OFF | >= 0.30 | 0.10-0.30 | < 0.10 |
| asia_range_fade_v1 PF drop | < 0.05 | 0.05-0.10 | >= 0.10 |

H1, H2, and H3 are independent verdicts.

## Forbidden During Step 1

- No LIVE strategy logic changes.
- No `basket_strength()` signature change.
- No XAU inclusion.
- No post-hoc selection after audit output is generated.
- No alpha residual live signalization.
