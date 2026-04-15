# Trend Rebound

## Overview
- **Entry Type**: `trend_rebound`
- **Category**: MR (Mean Reversion)
- **Timeframe**: DT 15m
- **Status**: UNIVERSAL_SENTINEL; EUR_USD PAIR_DEMOTED
- **Active Pairs**: Sentinel on USD_JPY, GBP_USD, EUR_JPY, EUR_GBP

## BT Performance (365d, 15m)
BT data not available for this entry_type

## Live Performance (post-cutoff)
Live data accumulating. EUR_USD: N=6 WR=16.7% EV=-1.85 Kelly=-43.0% (PAIR_DEMOTED basis).

## Signal Logic
Counter-trend rebound in strong trending conditions. Enters against the prevailing trend when momentum indicators show extreme exhaustion (RSI extreme, extended from EMA). Academic edge questionable; Sentinel verification mode for data collection.

## Current Configuration
- Lot Boost: default (1.0x)
- PAIR_DEMOTED: EUR_USD (v8.9: N=6 WR=16.7% EV=-1.85 Kelly=-43.0%)
- PAIR_PROMOTED: none

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
