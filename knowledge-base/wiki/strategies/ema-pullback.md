# EMA Pullback

## Overview
- **Entry Type**: `ema_pullback`
- **Category**: TF (Trend Following)
- **Timeframe**: Scalp/DT
- **Status**: FORCE_DEMOTED globally; USD_JPY PAIR_PROMOTED (v8.9 recovery)
- **Active Pairs**: USD_JPY (PAIR_PROMOTED, Sentinel lot), EUR_USD (PAIR_LOT_BOOST 1.5x)

## BT Performance (365d, 15m)
BT data not available for this entry_type in comprehensive scan.

## Live Performance (post-cutoff)
USD_JPY: N=14 WR=42.9% EV=+1.09 Kelly=14.9% (PAIR_PROMOTED basis)

## Signal Logic
Enters on pullbacks to key EMA levels (EMA21/EMA50) within an established trend. Requires higher timeframe trend alignment and waits for price to retrace to EMA support/resistance before entering in the trend direction.

## Current Configuration
- Lot Boost: default (1.0x) globally — FORCE_DEMOTED
- PAIR_DEMOTED: none
- PAIR_PROMOTED: USD_JPY (v8.9: N=14 WR=42.9% EV=+1.09), EUR_USD (PAIR_LOT_BOOST 1.5x)
- PAIR_LOT_BOOST: USD_JPY 2.0x, EUR_USD 1.5x

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
