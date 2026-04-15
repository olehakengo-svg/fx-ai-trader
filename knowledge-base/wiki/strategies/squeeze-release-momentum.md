# Squeeze Release Momentum

## Overview
- **Entry Type**: `squeeze_release_momentum`
- **Category**: VOL / Breakout
- **Timeframe**: DT 15m
- **Status**: UNIVERSAL_SENTINEL (SRM v3: BT N=24 WR=66.7% OOS unconfirmed)
- **Active Pairs**: Sentinel on all pairs

## BT Performance (365d, 15m)
| Pair | N | WR | EV | PF | PnL |
|---|---|---|---|---|---|
| EUR_USD | 15 | 73.3% | +0.656 | 2.68 | +9.8p |

## Live Performance (post-cutoff)
Live data accumulating

## Signal Logic
Bollinger Band squeeze detection followed by momentum-based directional entry on release. Identifies low-volatility compression (BB bandwidth below threshold), then enters when bands expand with momentum confirmation (MACD histogram, volume surge). Variant of bb_squeeze_breakout with enhanced momentum filtering.

## Current Configuration
- Lot Boost: default (1.0x) — UNIVERSAL_SENTINEL
- PAIR_DEMOTED: none
- PAIR_PROMOTED: none

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
