# Trendline Sweep

## Overview
- **Entry Type**: `trendline_sweep`
- **Category**: SMC / TF (Trend Following)
- **Timeframe**: DT 15m
- **Status**: ELITE_LIVE (v2.1); FORCE_DEMOTED globally but PAIR_PROMOTED on EUR_USD, GBP_USD
- **Active Pairs**: EUR_USD (PAIR_PROMOTED), GBP_USD (PAIR_PROMOTED)

## BT Performance (365d, 15m)
| Pair | N | WR | EV | PF | PnL |
|---|---|---|---|---|---|
| EUR_USD | 73 | 80.8% | +0.927 | 2.52 | +67.7p |
| GBP_USD | 134 | 73.1% | +0.599 | 1.68 | +80.3p |

## Live Performance (post-cutoff)
Live N=2 WR=0% PnL=-29.8pip (basis for original FORCE_DEMOTION). BT 365d recovery path confirmed positive EV on EUR/GBP.

## Signal Logic
Trendline liquidity sweep strategy. Identifies trendlines where stop losses accumulate, enters after price sweeps beyond the trendline (triggering stops) then reverses back inside. Combines SMC stop-hunt logic with trendline-based entry zones.

## Current Configuration
- Lot Boost: default (1.0x) — was in LOT_BOOST but removed after FORCE_DEMOTION
- PAIR_DEMOTED: none explicit
- PAIR_PROMOTED: EUR_USD (v2.1: BT EV=+0.927 WR=80.8%), GBP_USD (v2.1: BT EV=+0.599 WR=73.1%)

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
