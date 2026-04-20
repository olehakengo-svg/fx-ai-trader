# EMA Pullback

## Overview
- **Entry Type**: `ema_pullback`
- **Category**: TF (Trend Following)
- **Timeframe**: Scalp/DT
- **Status**: FORCE_DEMOTED (全ペア強制 Shadow)
- **Active Pairs**: None (FORCE_DEMOTED — PAIR_PROMOTED / PAIR_LOT_BOOST 全削除 v9.1)

## BT Performance (365d, 15m)
BT data not available for this entry_type in comprehensive scan.

## Live Performance (post-cutoff)
USD_JPY: N=14 WR=42.9% EV=+1.09 Kelly=14.9% (PAIR_PROMOTED basis)

## Signal Logic
Enters on pullbacks to key EMA levels (EMA21/EMA50) within an established trend. Requires higher timeframe trend alignment and waits for price to retrace to EMA support/resistance before entering in the trend direction.

## Current Configuration
- Lot Boost: default (1.0x) globally — FORCE_DEMOTED
- PAIR_DEMOTED: none
- PAIR_PROMOTED: none (v9.1 removed — FORCE_DEMOTED 下で PP/LOT_BOOST は死コード。Historical: USD_JPY v8.9 N=14 WR=42.9% EV=+1.09 / EUR_USD PAIR_LOT_BOOST 1.5x)
- PAIR_LOT_BOOST: none (v9.1 removed)

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
