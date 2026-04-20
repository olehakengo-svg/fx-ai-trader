# SR Channel Reversal

## Overview
- **Entry Type**: `sr_channel_reversal`
- **Category**: MR (Mean Reversion)
- **Timeframe**: Scalp/DT
- **Status**: FORCE_DEMOTED (global) — v9.1 PAIR_PROMOTED 死コード削除; v9.x (2026-04-20) demo_db legacy override も削除
- **Active Pairs**: none (shadow only)

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
- PAIR_PROMOTED: **なし** (v9.1 で EUR_USD 削除, v9.x 2026-04-20 で demo_db legacy override も削除)

## 2026-04-20 判断履歴 (Priority 2 PAIR_PROMOTED 監査)
EUR_USD BT は 365d DT 15m で発火 0, 180d Scalp も GBP_JPY 5m (N=70 EV=+0.122) のみ正EV で
Gate1 (EV≥+0.2) 未通過。

**Live 実績 (EUR_USD, post 2026-04-07):**
- N=26 (shadow=18, live=8) WR=19.2% EV=-1.196 PnL=-31.1p — **壊滅的**

全 Gate 不通過 → demo_db legacy override 削除。参照: [[pair-promoted-candidates-2026-04-20]]

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
