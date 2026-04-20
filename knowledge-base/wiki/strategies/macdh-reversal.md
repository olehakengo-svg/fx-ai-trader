# MACDH Reversal

## Overview
- **Entry Type**: `macdh_reversal`
- **Category**: **TF** (Trend-Follow) — v9.3 P0 で MR → TF に再分類
- **Timeframe**: Scalp/DT
- **Status**: FORCE_DEMOTED (v6.8: N=86 WR=34.7% PnL=-40.6 PF<1)
- **Active Pairs**: None (FORCE_DEMOTED); GBP_USD also PAIR_DEMOTED

## BT Performance (365d, 15m)
BT data not available for this entry_type in comprehensive scan.

## Live Performance (post-cutoff)
N=86 WR=34.7% PnL=-40.6pip (FORCE_DEMOTED basis)

## Signal Logic
MACD histogram reversal strategy. Enters when MACD histogram shows divergence from price and reverses direction (histogram bars shrinking then flipping sign). Uses histogram momentum change as early reversal signal before MACD line crossover.

## Current Configuration
- Lot Boost: default (1.0x) — FORCE_DEMOTED
- PAIR_DEMOTED: GBP_USD (WR=40% EV=-0.818)
- PAIR_PROMOTED: none

## v9.3 P0: Family Reclassification (2026-04-17)

名称に「reversal」を含むが、Phase C N=109 forensics で **TF 挙動** と判定:
- `trend_up_*` BUY WR **36%** > SELL WR 27% (+9pp)
- `trend_down_*` SELL WR **48%** > BUY WR 30% (+18pp)

両方向で順張りが優位 → TF family に再分類。
現状 SHADOW 100% (LIVE トレードなし) のため再分類は LIVE 影響ゼロ。

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
- [[mtf-regime-validation-2026-04-17]] §C-3 — Mislabel 特定根拠
