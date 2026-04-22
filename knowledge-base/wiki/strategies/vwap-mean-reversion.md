# VWAP Mean Reversion

## Overview
- **Entry Type**: `vwap_mean_reversion`
- **Category**: MR (Mean Reversion)
- **Timeframe**: Scalp 1m, DT 15m/1h
- **Status**: PAIR_PROMOTED (EUR_JPY, GBP_JPY); LOT_BOOST 1.5x
- **Active Pairs**: EUR_JPY (PAIR_PROMOTED), GBP_JPY (PAIR_PROMOTED)

## BT Performance (365d, 15m)
From massive alpha scan (Bonferroni significant, friction-adjusted):
| Edge | Pair | TF | Hold | N | fWR | fEV(pip) | Annual PnL |
|---|---|---|---|---|---|---|---|
| VW2s BUY | EUR_JPY | 15m | 16b(4h) | 737 | 55.8% | +3.85 | +2,837p |
| VW2s BUY | GBP_JPY | 15m | 16b(4h) | 740 | 56.2% | +5.17 | +3,827p |
| VW2s BUY | USD_JPY | 15m | 16b(4h) | 705 | 55.0% | +2.98 | +2,099p |
| VW2s BUY | GBP_JPY | 1h | 16b | 245 | 56.3% | +13.4 | +3,290p |
| VW2s BUY | EUR_JPY | 1h | 16b | 226 | 58.0% | +6.32 | +1,428p |

Scalp (Bonferroni significant):
| Edge | Pair | TF | Hold | N | fWR | fEV(pip) | Annual PnL |
|---|---|---|---|---|---|---|---|
| VW2s BUY | EUR_JPY | 1m | 16min | 2,574 | 56.5% | +0.81 | +2,087p |
| VW2s BUY | GBP_JPY | 1m | 16min | 2,028 | 53.6% | +0.48 | +975p |

## Live Performance (post-cutoff, 2026-04-08〜)
| Strategy | Pairs | N | WR | PnL |
|---|---|---|---|---|
| vwap_mean_reversion | all | 2 | 50.0% | +36.9 pip |

Top performer in post-cutoff period. Small N — continue monitoring.
Data source: /api/demo/stats?date_from=2026-04-08 (2026-04-21, no new trades)

## Signal Logic
VWAP 2-sigma mean reversion. Enters BUY when price drops below VWAP minus 2 standard deviations, expecting reversion to VWAP. Massive API exclusive alpha — requires intraday VWAP calculation from tick/volume data. Bonferroni-corrected p<10^-7 across JPY crosses.

## Current Configuration
- Lot Boost: 1.5x (strategy-level)
- PAIR_DEMOTED: none
- PAIR_PROMOTED: EUR_JPY (15m 16bar: annual +2,837pip), GBP_JPY (15m 16bar: annual +3,827pip, strongest alpha)
- PAIR_LOT_BOOST: EUR_JPY 1.8x, GBP_JPY 1.8x

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
