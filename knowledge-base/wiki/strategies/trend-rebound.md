# Trend Rebound

## Overview
- **Entry Type**: `trend_rebound`
- **Category**: MR (Mean Reversion)
- **Timeframe**: DT 15m
- **Status**: PAIR_PROMOTED × USD_JPY (2026-05-07 volume emergency promote — shadow N=17 EV=+1.14 PF=1.52, EV/PF shadow exception)
- **Active Pairs**: USD_JPY (PROMOTED); EUR_USD (PAIR_DEMOTED)
- **Auto-demote guard**: R2 live N>=10 EV<0 で自動降格

## Previously
- 〜2026-04-26: UNIVERSAL_SENTINEL; EUR_USD PAIR_DEMOTED
- 2026-04-27: tier-master.json で FORCE_DEMOTED に変更 (前セッションでの整理)
- 2026-05-01 audit P0-8: FORCE_DEMOTED 確定 (Live N=17 WR=23.5% PnL=-26.0p)
- 2026-05-07 volume emergency: USD_JPY のみ PAIR_PROMOTED として復帰 (shadow exception)

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
- PAIR_DEMOTED: (FORCE_DEMOTED 一括化により撤去)
- PAIR_PROMOTED: none
- Status: **FORCE_DEMOTED** (OANDA 送信全ペア停止、Shadow 蓄積継続)

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
