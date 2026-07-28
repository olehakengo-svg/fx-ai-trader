# Donchian Momentum Breakout

## Overview
- **Entry Type**: `donchian_momentum_breakout`
- **Category**: Breakout / TF
- **Timeframe**: DT 15m
- **Status**: PAIR_PROMOTED (NZD_JPY / NZD_USD — 2026-05-27 R1-EXCEPTION)、他ペアは Shadow
- **Active Pairs**: NZD_JPY, NZD_USD (1000u 固定 sentinel)。**2026-07-28 live 再武装** — `_is_xau_inst` バグで昇格以来 live 送信死 (fill N=0) → PR #119 修復 + user 決裁で送信可 ([[lesson-preserve-sltp-unboundlocal-2026-07-28]])
- **History**: 2026-05-01 audit P0-8 で旧 FD 入り (Live N=3 WR=33.3% PnL=-32.1p) → 2026-05-18 Shadow ramp で FD 解除・shadow-always 移行 (v2.1 alpha absence reevaluation) → 2026-05-27 NZD×2 PAIR_PROMOTED (R1-EXCEPTION) ※本カードの旧記述が 2026-07-28 まで未更新だった (stale)
- **Exit 挙動 note (2026-07-28)**: BE_LOCK は trig 0.0 で OFF だが、共通 ATR-BE (0.8×ATR→建値) / ATR-trail (1.5×ATR) は適用される — shadow の `SL_HIT` 正値 close (+12.8p 等) は trail 由来。詳細: [[preserve-exit-overlay-2026-07-28]]

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
