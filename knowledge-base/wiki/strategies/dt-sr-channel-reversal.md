# DT SR Channel Reversal

## Overview
- **Entry Type**: `dt_sr_channel_reversal`
- **Category**: MR (Mean Reversion)
- **Timeframe**: DT 15m
- **Status**: UNIVERSAL_SENTINEL (未検証, Sentinel蓄積)
- **Active Pairs**: Sentinel on all pairs

## BT Performance (365d, 15m)
| Pair | N | WR | EV | PF | PnL |
|---|---|---|---|---|---|
| EUR_JPY | 362 | 63.8% | +0.178 | 1.39 | +64.6p |

## Live Performance (post-cutoff)
| Strategy | Pair | N | W | L | WR | PnL |
|---|---|---|---|---|---|---|
| dt_sr_channel | USD_JPY | 9 | 3 | 6 | 33% | -37.6p |
| dt_sr_channel | GBP_USD | 6 | 1 | 5 | 17% | -27.5p |

## Signal Logic
Support/resistance channel reversal for daytrade timeframe. Identifies horizontal SR zones and channel boundaries, entering reversal trades when price reaches channel extremes with confirmation. DT-tuned version of sr_channel_reversal.

## Current Configuration
- Lot Boost: default (1.0x)
- PAIR_DEMOTED: none
- PAIR_PROMOTED: none

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy

## 2026-07-02 LIVE demote (rule:R2)
`(dt_sr_channel_reversal, EUR_JPY)` を `_PAIR_PROMOTED` から除去。30d clean live N=10 WR=40% -30.9pip (Wlo=16.8 BFlo=9.5, 本番実測 2026-07-02)。昇格根拠 (shadow N=12 EV=+14.28 small-N / BT EV=+0.178 marginal) を live が反証。Shadow 継続。再昇格は R1 のみ。詳細: [[live-bleeder-demotions-2026-07-02]]
