# Price Shock Dedup Audit

## Source Counts
- DB SHADOW_CANDIDATE cell count: 227
- survivors.md expected count: 227
- Count match: PASS
- Family count: 23
- Expected family count: 23
- Family count match: PASS

## Tier Counts
- Tier 1: 5
- Tier 2: 0
- Tier 3: 5
- Tier 4: 13
- Tier 1+2+3 total: 10 / max 15
- Tier cap check: PASS

## Representative Selection Spot Check
- PASS: EUR_GBP_H1_LONG_SHOCK representative `EUR_GBP_H1_LONG_SHOCK_1_3_Q5`
- PASS: USD_CAD_H1_SHORT_SHOCK representative `USD_CAD_H1_SHORT_SHOCK_1_1_Q4`
- PASS: EUR_AUD_H1_LONG_SHOCK representative `EUR_AUD_H1_LONG_SHOCK_1_12_Q5`

## Method
- Family key is literal `(pair, tf, direction)`.
- Representative selection order is Bonferroni pass, BH-FDR pass, Wilson lower 95, EV%, N, cell_id.
- Tier thresholds are literal pre-registration rules; caps are max 5 families per Tier 1/2/3.
