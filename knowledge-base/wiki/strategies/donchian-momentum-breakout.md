# Donchian Momentum Breakout

## Overview
- **Entry Type**: `donchian_momentum_breakout`
- **Category**: Breakout / TF
- **Timeframe**: DT 15m
- **Status**: SHADOW (HourlyEngine `_shadow_always` ramp 2026-05-18 — decisions/hourly-engine-shadow-ramp-2026-05-18.md)
- **Active Pairs**: None (Shadow accumulation only)
- **History**: 2026-05-01 audit P0-8 で旧 FD 入り (Live N=3 WR=33.3% PnL=-32.1p) → 2026-05-18 Shadow ramp で FD 解除・shadow-always 移行 (v2.1 alpha absence reevaluation)

## BT Performance (365d, 15m)
BT data not available for this entry_type

## Live Performance (post-cutoff, 2026-04-08〜)
| Strategy | Pair | N | W | L | WR | PnL |
|---|---|---|---|---|---|---|
| donchian_momentum | EUR_USD | 4 | 1 | 3 | 25% | -31.3p |
| donchian_momentum_breakout | all | 3 | 1 | 2 | 33.3% | -32.1 pip |

Note: aggregate N=3 from /api/demo/stats may reflect partially overlapping period with EUR_USD detail above.
Data source: /api/demo/stats?date_from=2026-04-08 (2026-04-20)

## Signal Logic
Enters on Donchian channel breakout (new N-period high/low) with momentum confirmation. Uses ATR-based stop loss and channel-width-based take profit. Filters false breakouts via volume/momentum divergence.

## Current Configuration
- Lot Boost: default (1.0x)
- PAIR_DEMOTED: none
- PAIR_PROMOTED: none
- Status: **FORCE_DEMOTED**

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
