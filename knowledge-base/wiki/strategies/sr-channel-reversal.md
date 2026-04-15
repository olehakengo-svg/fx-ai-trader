# SR Channel Reversal

## Overview
- **Entry Type**: `sr_channel_reversal`
- **Category**: MR (Mean Reversion)
- **Timeframe**: Scalp/DT
- **Status**: FORCE_DEMOTED (v8.9: Post-cut N=17 WR=11.8% instant death 87.5%); EUR_USD PAIR_PROMOTED
- **Active Pairs**: EUR_USD (PAIR_PROMOTED, 5m EV=+0.231 WR=70.6%)

## BT Performance (365d, 15m)
BT data not available for this entry_type in comprehensive scan.

## Live Performance (post-cutoff)
| Strategy | Pair | N | W | L | WR | PnL |
|---|---|---|---|---|---|---|
| sr_channel | USD_JPY | 10 | 1 | 9 | 10% | -25.3p |

## Signal Logic
Support/resistance channel reversal. Identifies price channels bounded by SR levels and enters reversal trades when price reaches channel boundaries. Expects price to oscillate within the channel, fading moves to the extremes.

## Current Configuration
- Lot Boost: default (1.0x) — FORCE_DEMOTED globally
- PAIR_DEMOTED: none explicit (globally demoted)
- PAIR_PROMOTED: EUR_USD (5m: EV=+0.231 N=17 WR=70.6%)

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
