# Price Shock Dedup Phase A Final

Generated: 2026-05-18

## Outputs
- `tools/price_shock_dedup_analysis.py`
- `reports/price_shock_reversion_grid/dedup_families.csv`
- `reports/price_shock_reversion_grid/shadow_promote_shortlist.md`
- `reports/price_shock_reversion_grid/dedup_audit.md`
- `tests/test_price_shock_dedup_analysis.py`

## Tier Counts
- Tier 1: 5 family
- Tier 2: 0 family
- Tier 3: 5 family
- Tier 4: 13 family
- Tier 1+2+3 total: 10 family / max 15

Tier 2 is 0 because every Bonferroni-positive family that met Tier 2 also met Tier 1 thresholds; Tier 1 is capped at 5 and cap overflow is rejected rather than post-hoc downgraded.

## Tier 1 Top 3
1. `EUR_GBP`, `H1`, `LONG_SHOCK`
2. `EUR_AUD`, `H1`, `LONG_SHOCK`
3. `USD_CAD`, `H1`, `LONG_SHOCK`

## Audit
- DB SHADOW_CANDIDATE cell count: 227
- Family count: 23
- Representative spot checks: PASS
- Tier cap check: PASS

## Verification
- `python3 tools/price_shock_dedup_analysis.py` passed.
- `python3 -m py_compile tools/price_shock_dedup_analysis.py tests/test_price_shock_dedup_analysis.py` passed.
- `python3 -m pytest -q tests/test_price_shock_dedup_analysis.py` could not run because pytest is not installed in this environment.
- Direct execution of all three test functions passed with the real DB.
