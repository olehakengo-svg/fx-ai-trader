# EMA Cross

## Overview
- **Entry Type**: `ema_cross`
- **Category**: **MR** (Mean Reversion) — v9.3 P0 で TF → MR に再分類
- **Timeframe**: Scalp/DT
- **Status**: FORCE_DEMOTED
- **Active Pairs**: None (FORCE_DEMOTED); USD_JPY also PAIR_DEMOTED

## BT Performance (365d, 15m)
BT data not available for this entry_type

## Live Performance (post-cutoff)
USD_JPY: N=41 WR=34.1% PnL=-67.4pip (PAIR_DEMOTED basis)

## Signal Logic
Classic EMA crossover strategy. Enters long when fast EMA (e.g., EMA9) crosses above slow EMA (e.g., EMA21), and short on the opposite crossover. Simple trend-following signal with minimal additional filters.

## Current Configuration
- Lot Boost: default (1.0x) — FORCE_DEMOTED
- PAIR_DEMOTED: USD_JPY (N=41 WR=34.1% -67.4pip)
- PAIR_PROMOTED: none

## v9.3 P0: Family Reclassification (2026-04-17)

名称通りの「EMA クロス順張り」だが、Phase C N=47 forensics で **MR 挙動**と判定:
- `trend_up_*` BUY WR 17% < SELL WR **46%** (-29pp, 強い逆相関)

仮説: クロスが発生する時点は既に「動いた後」で、M30/H1 スケールでは
ピークキャッチ → mean revert が支配的。TF 前提の alignment では誤分類していた。

SHADOW 100% のため再分類は LIVE 影響ゼロ。

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
- [[mtf-regime-validation-2026-04-17]] §C-3
