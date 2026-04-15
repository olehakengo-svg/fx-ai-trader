# JPY Basket Trend

## Overview
- **Entry Type**: `jpy_basket_trend`
- **Category**: TF (Trend Following) / Cross-pair
- **Timeframe**: DT 15m / 1H
- **Status**: SHADOW (not in any promotion/demotion list)
- **Active Pairs**: Shadow on all pairs

## BT Performance (365d, 15m)
BT data not available for this entry_type

## Live Performance (post-cutoff)
Live data accumulating

## Signal Logic
JPY basket trend-following strategy. Monitors multiple JPY crosses (USD/JPY, EUR/JPY, GBP/JPY) for correlated JPY strength/weakness signals. Enters trades when the JPY basket shows unified directional momentum, filtering individual pair noise.

## Current Configuration
- Lot Boost: default (1.0x)
- PAIR_DEMOTED: none
- PAIR_PROMOTED: none

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
