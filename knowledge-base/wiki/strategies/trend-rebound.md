# Trend Rebound

## Overview
- **Entry Type**: `trend_rebound`
- **Category**: MR (Mean Reversion)
- **Timeframe**: DT 15m
- **Status**: UNIVERSAL_SENTINEL; EUR_USD PAIR_DEMOTED
- **Active Pairs**: Sentinel on USD_JPY, GBP_USD, EUR_JPY, EUR_GBP

## BT Performance (365d, 15m)
BT data not available for this entry_type

## Live Performance (post-cutoff)
Live data accumulating. EUR_USD: N=6 WR=16.7% EV=-1.85 Kelly=-43.0% (PAIR_DEMOTED basis).

**v9.5 Live pair-level 実測 (2026-04-20)** — [[ema-tr-live-breakdown-2026-04-20]]:

| Pair | Live N | WR% | PnL | EV | Shadow N | Shadow EV | Note |
|---|---|---|---|---|---|---|---|
| USD_JPY | 10 | 30.0 | −7.8 | −0.78 | 12 | **+1.43** | **Live で符号逆転** — Gate 微不通過 (WR/PnL criteria) |
| EUR_USD | 7 | 28.6 | −10.0 | −1.43 | 7 | +1.16 | Live で符号逆転、N<10 |
| GBP_USD | 1 | 0.0 | −7.1 | −7.10 | 2 | −7.55 | Live/Shadow 共に N<3 で判定不能 |

**重要所見**: Shadow では USD_JPY/EUR_USD の trend_rebound が +EV に見えたが Live では両方とも負EV。
[[lesson-orb-trap-bt-divergence]] パターンの再現 (truncated sample bias at low N)。
trend_rebound × USD_JPY は Live N=10 で Gate 微不通過のため PAIR_DEMOTED 追加は保留、監視優先度 High。

## Signal Logic
Counter-trend rebound in strong trending conditions. Enters against the prevailing trend when momentum indicators show extreme exhaustion (RSI extreme, extended from EMA). Academic edge questionable; Sentinel verification mode for data collection.

## Current Configuration
- Lot Boost: default (1.0x)
- PAIR_DEMOTED: EUR_USD (v8.9: N=6 WR=16.7% EV=-1.85 Kelly=-43.0%)
- PAIR_PROMOTED: none
- Watch list (v9.5): USD_JPY (Live N=10 EV=−0.78, Gate 微不通過 — 次 N≥20 で再判定)

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
