# Donchian Momentum Breakout

## Overview
- **Entry Type**: `donchian_momentum_breakout`
- **Category**: Breakout / TF
- **Timeframe**: DT 15m
- **Status**: SHADOW (not in any promotion/demotion list)
- **Active Pairs**: Shadow on all pairs

## BT Performance (365d, 15m)
BT data not available for this entry_type

## Live Performance (post-cutoff)
| Strategy | Pair | N | W | L | WR | PnL |
|---|---|---|---|---|---|---|
| donchian_momentum | EUR_USD | 4 | 1 | 3 | 25% | -31.3p |

## Signal Logic
Enters on Donchian channel breakout (new N-period high/low) with momentum confirmation. Uses ATR-based stop loss and channel-width-based take profit. Filters false breakouts via volume/momentum divergence.

## Current Configuration
- Lot Boost: default (1.0x)
- PAIR_DEMOTED: none
- PAIR_PROMOTED: none

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
