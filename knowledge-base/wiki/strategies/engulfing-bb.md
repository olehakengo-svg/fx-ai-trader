# Engulfing BB

## Overview
- **Entry Type**: `engulfing_bb`
- **Category**: **TF** (Trend-Follow) — v9.3 P0 で MR → TF に再分類
- **Timeframe**: Scalp 1m/5m, DT 15m
- **Status**: FORCE_DEMOTED (v8.0: WR=14.3% PnL=-$353.5); EUR_USD PAIR_PROMOTED
- **Active Pairs**: EUR_USD (PAIR_PROMOTED)

## BT Performance (365d, 15m)
BT data not available for this entry_type in comprehensive scan.

## Live Performance (post-cutoff)
| Strategy | Pair | N | W | L | WR | PnL |
|---|---|---|---|---|---|---|
| engulfing_bb | EUR_USD | 6 | 4 | 2 | 66.7% | +32.9p |

## Signal Logic
Engulfing candle pattern at Bollinger Band extremes. Enters reversal when a bullish/bearish engulfing pattern forms at the lower/upper BB, confirming mean reversion potential. Combines candlestick pattern recognition with volatility-based entry zones.

## Current Configuration
- Lot Boost: default (1.0x) — FORCE_DEMOTED globally
- PAIR_DEMOTED: USD_JPY (v8.9: N=14 WR=28.6% Kelly=-14.7%), EUR_USD (v8.9: N=9 WR=11.1% EV=-1.42 — but also PAIR_PROMOTED for different timeframe)
- PAIR_PROMOTED: EUR_USD (4/14 analysis: WR=67% +33pip, BT 1m EV=+0.163 N=47)

## v9.3 P0: Family Reclassification (2026-04-17)

Phase C N=79 forensics で **TF 挙動**と判定:
- `trend_up_*` BUY WR **43%** > SELL WR 0% (+43pp)

Engulfing pattern が BB 端で発生した場合、「既存トレンドの一時的な押し戻し後の継続」
として機能している可能性が高い。MR 前提の alignment では逆方向に分類していた。

SHADOW 100% のため再分類は LIVE 影響ゼロ。

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
- [[mtf-regime-validation-2026-04-17]] §C-3
