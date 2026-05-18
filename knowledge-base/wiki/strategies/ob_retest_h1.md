# ob_retest_h1

- **Status**: Disabled after pre-reg FAIL (2026-05-18)
**Mode**: hourly
**Class**: `strategies.hourly.ob_retest.ObRetestH1`
**Entry Type**: `ob_retest_h1`
**Decision**: [[pre-reg-ob-retest-h1-2026-05-18]]

## Thesis

M5 `ob_retest` failed structural validation because wick noise and spread occupancy dominated the stop geometry. The H1 migration tested whether wider SL/noise ratio and lower friction occupancy would allow order-block anchoring to survive after costs.

## Locked Parameters

| Parameter | Value |
|---|---:|
| IMPULSE_MIN_BARS | 3 |
| IMPULSE_ATR_MULT | 2.0 |
| OB_LOOKBACK | 60 |
| OB_FRESHNESS | 50 |
| OB_MAX_WIDTH_ATR | 2.0 |
| EMA_FAST | 9 |
| EMA_SLOW | 21 |
| RETEST_BUFFER_ATR | 0.10 |
| SL_BUFFER_ATR | 0.10 |
| TP_R_MULT | 1.5 |

Allowed pairs: USDJPY, EURUSD, GBPUSD, EURJPY, GBPJPY.

## Entry Summary

BUY requires a bearish candidate candle followed by 3 bullish impulse bars, impulse range ≥ ATR×2.0, OB width ≤ ATR×2.0, then a retest into the OB zone with bullish reversal and EMA9 > EMA21 / close > EMA21. SELL is symmetric.

SL is OB boundary ± ATR×0.10. TP is 1.5R from the entry price basis.

## 365d MASSIVE BT

Output: `raw/bt-results/ob_retest_h1_365d_2026_05_18.json`

| Pair | N | WR | Wilson_lo | EV pips | PF | PASS |
|---|---:|---:|---:|---:|---:|---|
| USD_JPY | 132 | 50.00% | 0.4159 | +6.5408 | 1.4083 | NO |
| EUR_USD | 120 | 48.33% | 0.3958 | +0.5452 | 1.0436 | NO |
| GBP_USD | 130 | 36.92% | 0.2911 | -3.0732 | 0.8178 | NO |
| EUR_JPY | 141 | 51.06% | 0.4289 | +4.8384 | 1.2600 | NO |
| GBP_JPY | 149 | 47.65% | 0.3979 | +2.2341 | 1.0902 | NO |

**Verdict**: FAIL. All pairs missed the locked N≥200 threshold; no post-hoc parameter loosening is allowed. Strategy remains registered but `enabled = False`.

## Related Routing

M5 `ob_retest` is FORCE_DEMOTED under rule:R2. The OB thesis is not promoted in any live or lot-boost list from this card.
