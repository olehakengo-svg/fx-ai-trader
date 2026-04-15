# Dual SR Bounce

## Overview
- **Entry Type**: `dual_sr_bounce`
- **Category**: MR (Mean Reversion)
- **Timeframe**: DT 15m
- **Status**: FORCE_DEMOTED (v6.8+)
- **Active Pairs**: None (FORCE_DEMOTED)

## BT Performance (365d, 15m)
| Pair | N | WR | EV | PF | PnL |
|---|---|---|---|---|---|
| USD_JPY | 118 | 70.3% | +0.280 | 1.50 | +33.0p |

## Live Performance (post-cutoff)
| Strategy | Pair | N | W | L | WR | PnL |
|---|---|---|---|---|---|---|
| dual_sr_bounce | USD_JPY | 1 | 1 | 0 | 100% | +21.4p |
| dual_sr_bounce | EUR_JPY | 2 | 0 | 2 | 0% | -32.7p |

## Signal Logic
Dual support/resistance bounce strategy. Enters when price bounces off a confluence of two independent SR levels (e.g., horizontal SR + Fibonacci level, or pivot + previous day high/low). Requires both levels to align within a tight zone for high-confidence reversal.

## Current Configuration
- Lot Boost: default (1.0x) — FORCE_DEMOTED
- PAIR_DEMOTED: none explicit (globally demoted)
- PAIR_PROMOTED: none

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
