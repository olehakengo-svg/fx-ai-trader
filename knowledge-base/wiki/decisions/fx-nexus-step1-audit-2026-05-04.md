# FX Nexus Step 1 Shadow Audit

- Generated at: `2026-05-04T09:28:08.657198+00:00`
- Window: `2025-05-01` to `2026-05-01`
- Pairs: `USD_JPY,EUR_USD,GBP_USD,EUR_JPY,GBP_JPY`
- Scope: shadow measurement only; no LIVE intervention.

## Verdict Summary

| Hypothesis | Verdict | Key metric |
|---|---:|---|
| H1 V_ti | NEEDS_MORE | Wilson lower=0.5010, corr=0.9781, N=29968 |
| H2 alpha residual | NEEDS_MORE | significant pairs=2/5, KW p=1.0000 |
| H3 exec jitter | NEEDS_MORE | SRM PF drop=0.0000, healthy PF drop=0.0000 |

## H1 Currency Value

| Metric | Value |
|---|---:|
| condition number | 1.4142 |
| basket_strength correlation | 0.9781 |
| H1 next-bar predictive Wilson lower | 0.5010 |
| N | 29968 |

## H2 Alpha Residual

| Pair | N | MR success rate | p | Bonferroni p |
|---|---:|---:|---:|---:|
| USD_JPY | 6092 | 0.4854 | 0.9891 | 1.0000 |
| EUR_USD | 5634 | 0.5005 | 0.4734 | 1.0000 |
| GBP_USD | 6065 | 0.5222 | 0.0003 | 0.0014 |
| EUR_JPY | 6085 | 0.5241 | 0.0001 | 0.0005 |
| GBP_JPY | 6097 | 0.4945 | 0.8081 | 1.0000 |

| Metric | Value |
|---|---:|
| alpha magnitude vs spread proxy correlation | 0.0024 |
| alpha autocorrelation lag1 | 0.2567 |
| LIVE entry Kruskal-Wallis p | 1.0000 |

## H3 Tau Exec Jitter

| Strategy | PF off | PF on | N off | N on |
|---|---:|---:|---:|---:|
| squeeze_release_momentum | 0.0000 | 0.0000 | 0 | 0 |
| asia_range_fade_v1 | 0.0000 | 0.0000 | 0 | 0 |

H3 errors/warnings:
- All data sources failed for EURUSD=X/15m; local parquet cache unavailable
- All data sources failed for EURUSD=X/15m; local parquet cache unavailable
- All data sources failed for USDJPY=X/15m; local parquet cache unavailable
- All data sources failed for USDJPY=X/15m; local parquet cache unavailable
