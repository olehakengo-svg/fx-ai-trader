# BB Squeeze Breakout

## Overview
- **Entry Type**: `bb_squeeze_breakout`
- **Category**: Breakout / VOL
- **Timeframe**: Scalp 1m/5m, DT 15m
- **Status**: FORCE_DEMOTED (v8.2: BT EV=-0.799, structural deficit from max spread at breakout) / PAIR_PROMOTED on USD_JPY, EUR_USD
- **Active Pairs**: USD_JPY (PAIR_PROMOTED, 5m), EUR_USD (PAIR_PROMOTED, 1m)

## BT Performance (365d, 15m)
BT data not available for this entry_type in DT comprehensive scan.

## Live Performance (post-cutoff)
| Strategy | Pair | N | W | L | WR | PnL |
|---|---|---|---|---|---|---|
| bb_squeeze | EUR_USD | 8 | 0 | 8 | 0% | -25.7p |

## Signal Logic
Detects Bollinger Band squeeze (bandwidth contraction below threshold), then enters on the breakout direction when bands expand. Momentum confirmation via volume or candle body size filters breakout validity.

## Current Configuration
- Lot Boost: default (1.0x) — FORCE_DEMOTED globally
- PAIR_DEMOTED: none explicit (globally demoted)
- PAIR_PROMOTED: USD_JPY (5m EV=+1.030 WR=90.9%), EUR_USD (1m EV=+0.473 WR=73.7%)

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
