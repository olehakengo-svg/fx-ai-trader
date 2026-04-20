# Trendline Sweep

## Overview
- **Entry Type**: `trendline_sweep`
- **Category**: SMC / TF (Trend Following)
- **Timeframe**: DT 15m
- **Status**: ELITE_LIVE (全ペア自動通過)
- **Active Pairs**: 全ペア (ELITE_LIVE bypasses promotion system)

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
- Lot Boost: default (1.0x)
- PAIR_DEMOTED: none
- PAIR_PROMOTED: none (ELITE_LIVE 所属のため PP 指定は冗長 — v9.0 で整理。Historical: EUR_USD v2.1 BT EV=+0.927 WR=80.8% / GBP_USD v2.1 BT EV=+0.599 WR=73.1%)
- 履歴: Previously FORCE_DEMOTED (Live N=2 WR=0% -29.8pip)。v9.0 で 365d BT GBP EV=+0.60 / EUR EV=+0.93 に基づき ELITE_LIVE 昇格、FORCE_DEMOTED / PAIR_PROMOTED 整理。

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
