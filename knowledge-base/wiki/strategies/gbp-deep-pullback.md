# GBP Deep Pullback

## Overview
- **Entry Type**: `gbp_deep_pullback`
- **Category**: TF (Trend Following)
- **Timeframe**: DT 15m
- **Status**: ELITE_LIVE
- **Active Pairs**: GBP_USD

## BT Performance (365d, 15m)
| Pair | N | WR | EV | PF | PnL |
|---|---|---|---|---|---|
| GBP_USD | 77 | 75.3% | +1.064 | 2.00 | +81.9p |

## Live Performance (post-cutoff)
Live data accumulating (N<10, LOT_BOOST at 1.3x provisional)

## Signal Logic
GBP-specific deep pullback trend continuation. Enters when GBP_USD pulls back significantly within an established trend (deeper than standard pullback entries), using GBP-specific volatility thresholds. Targets larger moves with wider stops adjusted for GBP volatility.

## Current Configuration
- Lot Boost: 1.3x (provisional, N<10; upgrades to 2.0x at N>=15)
- PAIR_DEMOTED: none
- PAIR_PROMOTED: none (ELITE_LIVE bypasses promotion system)

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
