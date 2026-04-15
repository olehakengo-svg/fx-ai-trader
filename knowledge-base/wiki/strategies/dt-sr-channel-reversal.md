# DT SR Channel Reversal

## Overview
- **Entry Type**: `dt_sr_channel_reversal`
- **Category**: MR (Mean Reversion)
- **Timeframe**: DT 15m
- **Status**: UNIVERSAL_SENTINEL (未検証, Sentinel蓄積)
- **Active Pairs**: Sentinel on all pairs

## BT Performance (365d, 15m)
| Pair | N | WR | EV | PF | PnL |
|---|---|---|---|---|---|
| EUR_JPY | 362 | 63.8% | +0.178 | 1.39 | +64.6p |

## Live Performance (post-cutoff)
| Strategy | Pair | N | W | L | WR | PnL |
|---|---|---|---|---|---|---|
| dt_sr_channel | USD_JPY | 9 | 3 | 6 | 33% | -37.6p |
| dt_sr_channel | GBP_USD | 6 | 1 | 5 | 17% | -27.5p |

## Signal Logic
Support/resistance channel reversal for daytrade timeframe. Identifies horizontal SR zones and channel boundaries, entering reversal trades when price reaches channel extremes with confirmation. DT-tuned version of sr_channel_reversal.

## Current Configuration
- Lot Boost: default (1.0x)
- PAIR_DEMOTED: none
- PAIR_PROMOTED: none

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
