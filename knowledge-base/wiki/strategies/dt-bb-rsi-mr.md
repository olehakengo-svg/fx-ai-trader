# DT BB RSI Mean Reversion

## Overview
- **Entry Type**: `dt_bb_rsi_mr`
- **Category**: MR (Mean Reversion)
- **Timeframe**: DT 15m
- **Status**: PAIR_PROMOTED × USD_JPY (2026-05-07 volume emergency promote — EV/PF shadow exception)
- **Active Pairs**: USD_JPY (PROMOTED); EUR_USD (PAIR_DEMOTED)
- **Auto-demote guard**: R2 live N>=10 EV<0 で自動降格

## Previously
- ~2026-05-06: FORCE_DEMOTED (v8.9 Post-cut N=7 WR=14.3% EV=-4.09 PnL=-28.6 — 365d BT 全ペア負EV)
- 2026-05-07 volume emergency: USD_JPY のみ PAIR_PROMOTED として復帰 (shadow exception)

## BT Performance (365d, 15m)
| Pair | N | WR | EV | PF | PnL |
|---|---|---|---|---|---|
| USD_JPY | 319 | 54.2% | -0.023 | 0.96 | -7.3p |
| EUR_USD | 102 | 52.0% | -0.077 | 0.87 | -7.9p |
| GBP_USD | 187 | 51.3% | -0.135 | 0.77 | -25.2p |

## Live Performance (post-cutoff)
Live data confirms negative EV across all pairs. EUR_USD: N=7 WR=14.3% EV=-4.09.

## Signal Logic
Bollinger Band + RSI mean reversion for daytrade timeframe. Enters when price touches BB outer band with RSI at oversold/overbought extremes, expecting reversion to BB midline. DT-specific parameter tuning differentiates from scalp bb_rsi_reversion.

## Current Configuration
- Lot Boost: default (1.0x) — FORCE_DEMOTED
- PAIR_DEMOTED: EUR_USD (v8.9: N=8 WR=25.0% EV=-2.83 Kelly=-50.0%)
- PAIR_PROMOTED: none

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
