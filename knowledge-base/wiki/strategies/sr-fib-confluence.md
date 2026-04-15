# SR Fib Confluence

## Overview
- **Entry Type**: `sr_fib_confluence`
- **Category**: MR (Mean Reversion)
- **Timeframe**: DT 15m
- **Status**: FORCE_DEMOTED
- **Active Pairs**: None (FORCE_DEMOTED)

## BT Performance (365d, 15m)
| Pair | N | WR | EV | PF | PnL |
|---|---|---|---|---|---|
| USD_JPY | 220 | 67.7% | +0.252 | 1.44 | +55.4p |
| EUR_USD | 262 | 64.9% | +0.103 | 1.16 | +27.0p |

## Live Performance (post-cutoff)
N=40 WR=28.9% PnL=-92.8pip (BT divergence confirmed, PAIR_PROMOTED removed in v6.8)

## Signal Logic
Support/resistance + Fibonacci level confluence strategy. Enters reversal trades at zones where horizontal SR levels coincide with Fibonacci retracement levels (38.2%, 50%, 61.8%). The confluence of two independent methods provides higher-confidence reversal zones.

## Current Configuration
- Lot Boost: default (1.0x) — FORCE_DEMOTED
- PAIR_DEMOTED: none explicit (globally demoted)
- PAIR_PROMOTED: none (all removed in v6.8)

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
