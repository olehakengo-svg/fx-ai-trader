# DT Fib Reversal

## Overview
- **Entry Type**: `dt_fib_reversal`
- **Category**: MR (Mean Reversion)
- **Timeframe**: DT 15m
- **Status**: UNIVERSAL_SENTINEL (未検証, Sentinel蓄積)
- **Active Pairs**: Sentinel on all pairs

## BT Performance (365d, 15m)
| Pair | N | WR | EV | PF | PnL |
|---|---|---|---|---|---|
| EUR_USD | 10 | 80.0% | +0.407 | 1.96 | +4.1p |
| GBP_USD | 21 | 76.2% | +0.374 | 1.86 | +7.9p |
| EUR_JPY | 81 | 54.3% | -0.199 | 0.74 | -16.2p |

## Live Performance (post-cutoff)
Live data accumulating

## Signal Logic
Fibonacci retracement-based reversal for daytrade timeframe. Identifies swing high/low, calculates Fib levels (38.2%, 50%, 61.8%), and enters reversal trades at key retracement levels with confirmation from price action or momentum indicators.

## Current Configuration
- Lot Boost: default (1.0x)
- PAIR_DEMOTED: none
- PAIR_PROMOTED: none

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
