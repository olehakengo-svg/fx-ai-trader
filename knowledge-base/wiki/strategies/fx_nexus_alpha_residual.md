# FX Nexus Alpha Residual

- **Status**: Shadow observation only. Not a LIVE signal.

The FX Nexus Step 1 residual is:

```text
alpha_tij = log(X_tij) - (log(V_i) - log(V_j))
```

`V_ti` is estimated from the 5-pair FX graph
USD_JPY, EUR_USD, GBP_USD, EUR_JPY, GBP_JPY under the normalization
`sum_i log(V_ti) = 0`.

Current scope:

- Compute `V_ti` and alpha residuals in the data layer.
- Measure H1 next-bar mean-reversion evidence.
- Audit alpha values around LIVE OANDA entries with strict Live/Shadow separation.
- Keep all strategy gates unchanged.

Promotion rule:

- Only if the locked H2 gate in
  `knowledge-base/wiki/decisions/fx-nexus-step1-prereg-2026-05-04.md`
  is ACCEPT should Wave 5 draft an alpha reversion MR strategy spec.
- If H2 is REJECT, alpha remains at most a candidate filter feature.
