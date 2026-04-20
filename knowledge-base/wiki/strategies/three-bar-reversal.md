# Three Bar Reversal

## Overview
- **Entry Type**: `three_bar_reversal`
- **Category**: MR (Mean Reversion)
- **Timeframe**: DT 15m
- **Status**: Phase0 Shadow Gate (PP/EL 未指定 → 自動 Shadow, BT未検証)
- **Active Pairs**: None (全ペア自動 Shadow)
- **履歴**: Previously labeled UNIVERSAL_SENTINEL in strategy page; tier-master 実態は Phase0 Shadow Gate (scalp mode, PP/EL 指定なし)

## BT Performance (365d, 15m)
BT data not available for this entry_type

## Live Performance (post-cutoff)
Live data accumulating

## Signal Logic
Classic three-bar reversal pattern. Identifies a three-candle reversal formation (middle bar makes new high/low, third bar closes beyond first bar's range), entering in the reversal direction. Simple price action pattern with no indicator dependency.

## Current Configuration
- Lot Boost: default (1.0x)
- PAIR_DEMOTED: none
- PAIR_PROMOTED: none

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
