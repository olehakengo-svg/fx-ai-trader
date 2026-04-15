# NY Close Reversal

## Overview
- **Entry Type**: `ny_close_reversal`
- **Category**: Session / MR
- **Timeframe**: DT 15m
- **Status**: SHADOW (implemented from massive alpha scan)
- **Active Pairs**: Shadow on all pairs

## BT Performance (365d, 15m)
BT data not available for this entry_type in comprehensive scan.

## Live Performance (post-cutoff)
| UTC 20-22 | N | W | L | WR | PnL |
|---|---|---|---|---|---|
| All pairs | 5 | 0 | 5 | 0.0% | -7.0p |

## Signal Logic
NY session close (UTC 20:00-22:00) directional bias reversal. Enters counter-trend positions at NY close based on the day's directional movement, expecting overnight mean reversion. Implemented from massive alpha scan H20/H21 session bias findings.

## Current Configuration
- Lot Boost: default (1.0x)
- PAIR_DEMOTED: none
- PAIR_PROMOTED: none

## v2.1 Fix: TP/SL問題
- **問題**: TP_HITでPnL負の問題
- **原因**: TPがスプレッド以下に設定されていた（旧設定）
- **修正**: SL/TP をATR×1.0/1.5に設定（旧: TPがスプレッド以下）
- ATR×1.0 SL + ATR×1.5 TP でRR=1.5を確保

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
