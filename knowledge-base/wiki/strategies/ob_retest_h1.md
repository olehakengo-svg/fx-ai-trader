# ob_retest_h1

- **Status**: Disabled after pre-reg 365d and 1095d FAIL (2026-05-18)
**Mode**: hourly
**Class**: `strategies.hourly.ob_retest.ObRetestH1`
**Entry Type**: `ob_retest_h1`
**Decision**: [[pre-reg-ob-retest-h1-2026-05-18]]
**1095d Decision**: [[pre-reg-ob-retest-h1-1095d-2026-05-18]]

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

## 1095d MASSIVE BT

Output: `raw/bt-results/ob_retest_h1_1095d_2026_05_18.json`

Period: 2023-05-15 13:00 UTC to 2026-05-15 13:00 UTC. Same locked parameters, pair set, friction model, and PASS/FAIL criteria as the 365d attempt.

| Pair | N | WR | Wilson_lo | Wilson_bf_lo | EV pips | PF | WF EV h1/h2/h3 | PASS |
|---|---:|---:|---:|---:|---:|---:|---|---|
| USD_JPY | 414 | 45.65% | 0.4092 | 0.3946 | +2.8951 | 1.1553 | -1.8146 / +3.5031 / +6.9309 | NO |
| EUR_USD | 432 | 42.36% | 0.3779 | 0.3640 | -0.9552 | 0.9289 | +0.9074 / -3.6705 / -0.0215 | NO |
| GBP_USD | 415 | 37.35% | 0.3283 | 0.3148 | -6.6765 | 0.6671 | -6.2136 / -11.1539 / -2.8529 | NO |
| EUR_JPY | 431 | 41.76% | 0.3720 | 0.3581 | -8.1947 | 0.7230 | -19.5619 / -10.1784 / +4.2653 | NO |
| GBP_JPY | 447 | 41.61% | 0.3713 | 0.3577 | -8.7883 | 0.7562 | -21.7919 / -7.6656 / +2.3618 | NO |

**Verdict**: FAIL. USD_JPY reached the aggregate N/WR/Wilson_lo/EV/PF thresholds, but failed the locked walk-forward requirement because h1 EV was negative. All other pairs failed multiple aggregate criteria.

## 365d vs 1095d Comparison

| Pair | 365d N | 365d WR | 365d EV | 365d PF | 1095d N | 1095d WR | 1095d EV | 1095d PF | 1095d Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| USD_JPY | 132 | 50.00% | +6.5408 | 1.4083 | 414 | 45.65% | +2.8951 | 1.1553 | FAIL (WF h1<0) |
| EUR_USD | 120 | 48.33% | +0.5452 | 1.0436 | 432 | 42.36% | -0.9552 | 0.9289 | FAIL |
| GBP_USD | 130 | 36.92% | -3.0732 | 0.8178 | 415 | 37.35% | -6.6765 | 0.6671 | FAIL |
| EUR_JPY | 141 | 51.06% | +4.8384 | 1.2600 | 431 | 41.76% | -8.1947 | 0.7230 | FAIL |
| GBP_JPY | 149 | 47.65% | +2.2341 | 1.0902 | 447 | 41.61% | -8.7883 | 0.7562 | FAIL |

## Related Routing

M5 `ob_retest` is FORCE_DEMOTED under rule:R2. H1 `ob_retest_h1` is disabled. The OB retest thesis is retired as a promotion candidate and is not promoted in any live, shadow, or lot-boost list from this card.
