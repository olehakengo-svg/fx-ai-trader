# HTF False Breakout

## Overview
- **Entry Type**: `htf_false_breakout`
- **Category**: MR (Mean Reversion) / SMC
- **Timeframe**: DT 15m
- **Status**: SHADOW (LOT_BOOST 1.5x but not in ELITE_LIVE or PAIR_PROMOTED)
- **Active Pairs**: Shadow on all pairs

## BT Performance (365d, 15m)
| Pair | N | WR | EV | PF | PnL |
|---|---|---|---|---|---|
| USD_JPY | 20 | 80.0% | +0.660 | 3.16 | +13.2p |
| GBP_USD | 24 | 75.0% | +0.552 | 1.88 | +13.3p |
| EUR_USD | 15 | 80.0% | +0.352 | 1.42 | +5.3p |

## Live Performance (post-cutoff)
Live data accumulating

## Signal Logic
Higher timeframe false breakout reversal. Identifies when price breaks a significant HTF level (daily high/low, weekly level) but fails to sustain, then enters reversal trade. Uses multi-timeframe confluence to confirm the false breakout pattern.

## Current Configuration
- Lot Boost: 1.5x (EUR EV=0.614, GBP EV=0.034)
- PAIR_DEMOTED: none
- PAIR_PROMOTED: none

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
