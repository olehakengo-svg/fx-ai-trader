# EMA Cross

## Overview
- **Entry Type**: `ema_cross`
- **Category**: TF (Trend Following)
- **Timeframe**: Scalp/DT
- **Status**: FORCE_DEMOTED
- **Active Pairs**: None (FORCE_DEMOTED); USD_JPY also PAIR_DEMOTED

## BT Performance (365d, 15m)
BT data not available for this entry_type

## Live Performance (post-cutoff)
USD_JPY: N=41 WR=34.1% PnL=-67.4pip (PAIR_DEMOTED basis)

## Signal Logic
Classic EMA crossover strategy. Enters long when fast EMA (e.g., EMA9) crosses above slow EMA (e.g., EMA21), and short on the opposite crossover. Simple trend-following signal with minimal additional filters.

## Current Configuration
- Lot Boost: default (1.0x) — FORCE_DEMOTED
- PAIR_DEMOTED: USD_JPY (N=41 WR=34.1% -67.4pip)
- PAIR_PROMOTED: none

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
