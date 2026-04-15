# Turtle Soup

## Overview
- **Entry Type**: `turtle_soup`
- **Category**: MR (Mean Reversion) / SMC
- **Timeframe**: DT 15m
- **Status**: SHADOW (LOT_BOOST 1.5x but not in ELITE_LIVE or PAIR_PROMOTED)
- **Active Pairs**: Shadow on all pairs

## BT Performance (365d, 15m)
| Pair | N | WR | EV | PF | PnL |
|---|---|---|---|---|---|
| GBP_USD | 76 | 69.7% | +0.386 | 1.48 | +29.3p |

## Live Performance (post-cutoff)
Live data accumulating

## Signal Logic
Turtle Soup reversal strategy (Connors & Raschke). Fades false breakouts of N-period highs/lows. When price makes a new 20-period high/low but fails to sustain, enters reversal expecting the breakout to be a false signal that traps breakout traders.

## Current Configuration
- Lot Boost: 1.5x (GBP: EV=1.039, WR=79.3%, N=29)
- PAIR_DEMOTED: none
- PAIR_PROMOTED: none

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
