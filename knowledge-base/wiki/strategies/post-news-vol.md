# Post News Vol

## Overview
- **Entry Type**: `post_news_vol`
- **Category**: VOL (Volatility)
- **Timeframe**: DT 15m
- **Status**: UNIVERSAL_SENTINEL (全モード Sentinel) + PAIR_PROMOTED (GBP_USD, EUR_USD) + PAIR_DEMOTED (USD_JPY)
- **Active Pairs**: GBP_USD, EUR_USD (PAIR_PROMOTED で実弾通過); USD_JPY は PAIR_DEMOTED 明示 Shadow

## BT Performance (365d, 15m)
| Pair | N | WR | EV | PF | PnL |
|---|---|---|---|---|---|
| GBP_USD | 26 | 88.5% | +1.762 | 4.38 | +45.8p |
| EUR_USD | 28 | 71.4% | +0.817 | 1.68 | +22.9p |

## Live Performance (post-cutoff)
| Strategy | Pair | N | W | L | WR | PnL |
|---|---|---|---|---|---|---|
| post_news_vol | GBP_USD | 1 | 1 | 0 | 100% | +29.3p |
| post_news_vol | USD_JPY | 2 | 1 | 1 | 50% | +24.6p |

## Signal Logic
Post-news volatility fade strategy. Enters after major news releases once initial volatility spike subsides, trading the reversion or continuation of the post-news move. Uses volatility spike detection and directional momentum filtering to time entries after the noise settles.

## Current Configuration
- Lot Boost: default (1.0x)
- PAIR_DEMOTED: USD_JPY (v8.8: 120d BT WR=0% EV=-3.706)
- PAIR_PROMOTED: GBP_USD (v2.1: BT EV=+1.762), EUR_USD (v2.1: BT EV=+0.817)

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
