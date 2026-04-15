# MACDH Reversal

## Overview
- **Entry Type**: `macdh_reversal`
- **Category**: MR (Mean Reversion)
- **Timeframe**: Scalp/DT
- **Status**: FORCE_DEMOTED (v6.8: N=86 WR=34.7% PnL=-40.6 PF<1)
- **Active Pairs**: None (FORCE_DEMOTED); GBP_USD also PAIR_DEMOTED

## BT Performance (365d, 15m)
BT data not available for this entry_type in comprehensive scan.

## Live Performance (post-cutoff)
N=86 WR=34.7% PnL=-40.6pip (FORCE_DEMOTED basis)

## Signal Logic
MACD histogram reversal strategy. Enters when MACD histogram shows divergence from price and reverses direction (histogram bars shrinking then flipping sign). Uses histogram momentum change as early reversal signal before MACD line crossover.

## Current Configuration
- Lot Boost: default (1.0x) — FORCE_DEMOTED
- PAIR_DEMOTED: GBP_USD (WR=40% EV=-0.818)
- PAIR_PROMOTED: none

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
