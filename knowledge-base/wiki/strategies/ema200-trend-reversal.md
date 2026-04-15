# EMA200 Trend Reversal

## Overview
- **Entry Type**: `ema200_trend_reversal`
- **Category**: TF (Trend Following) / MR
- **Timeframe**: DT 15m
- **Status**: UNIVERSAL_SENTINEL; USD_JPY PAIR_DEMOTED
- **Active Pairs**: Sentinel on EUR_USD, GBP_USD, EUR_JPY, EUR_GBP

## BT Performance (365d, 15m)
| Pair | N | WR | EV | PF | PnL |
|---|---|---|---|---|---|
| EUR_USD | 12 | 75.0% | +0.410 | 1.87 | +4.9p |
| USD_JPY | 32 | 56.2% | -0.183 | 0.77 | -5.9p |

## Live Performance (post-cutoff)
Live data accumulating

## Signal Logic
Enters reversal trades at the EMA200 level. When price breaks above/below EMA200 and retests it, enters in the breakout direction expecting EMA200 to act as new support/resistance. Requires EMA200 slope confirmation and RSI filter.

## Current Configuration
- Lot Boost: default (1.0x)
- PAIR_DEMOTED: USD_JPY (v8.8: 120d BT WR=0% EV=-1.887)
- PAIR_PROMOTED: none

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
