# EMA200 Trend Reversal

## Overview
- **Entry Type**: `ema200_trend_reversal`
- **Category**: TF (Trend Following) / MR
- **Timeframe**: DT 15m
- **Status**: FORCE_DEMOTED (2026-04-22, H-2026-04-22-004 BT根拠)
- **Active Pairs**: 全ペアShadow、OANDA通過なし

## BT Performance (365d, 15m)
| Pair | N | WR | EV | PF | PnL |
|---|---|---|---|---|---|
| EUR_USD | 12 | 75.0% | +0.410 | 1.87 | +4.9p (旧: 小-N、撤回) |
| USD_JPY | 32 | 56.2% | -0.183 | 0.77 | -5.9p |

## H-2026-04-22-004 BT (拡張検証, 2026-04-22)
**Strict版** (abs(close-EMA200)/ATR<0.5 + first_touch=true + RSI divergence):
| Pair | TF | N | PF | EV_fric | 判定 |
|---|---|---|---|---|---|
| EUR_JPY | 1h | 2 | 0.00 | -1.34 | N不足 |
| EUR_JPY | 15m | 2 | 1.67 | +0.26 | N不足 |
| EUR_USD | 15m | 3 | 0.83 | -0.28 | N不足 |
| GBP_USD | 15m | 4 | 0.00 | -1.34 | N不足 |

**Relaxed版** (dist<1.0ATR, no first_touch, div lookback=10):
| Pair | TF | N | WR | PF | EV_fric | WF3 | 判定 |
|---|---|---|---|---|---|---|---|
| EUR_JPY | 1h | 159 | 32.1% | 0.76 | -0.34 | × | 負EV確定 |
| USD_JPY | 1h | 165 | 33.3% | 0.83 | -0.28 | × | 負EV確定 |
| EUR_USD | 1h | 262 | 28.6% | 0.64 | -0.45 | × 全負 | **明確な逆エッジ** |
| GBP_USD | 1h | 208 | 25.5% | 0.57 | -0.53 | × 全負 | **明確な逆エッジ** |
| EUR_JPY | 15m | 639 | 41.9% | 1.15 | -0.04 | ✓ | BE近辺（friction削減で黒字化可能性） |

**結論**: 緩和版でも全ペア×1hでPF<1。EUR_JPY 15mのみBE近辺。
→ FORCE_DEMOTED降格、全ペアOANDA通過停止。

## Live Performance (post-cutoff)
Live data accumulating

## Signal Logic
Enters reversal trades at the EMA200 level. When price breaks above/below EMA200 and retests it, enters in the breakout direction expecting EMA200 to act as new support/resistance. Requires EMA200 slope confirmation and RSI filter.

## Current Configuration
- Lot Boost: default (1.0x)
- PAIR_DEMOTED: USD_JPY (v8.8: 120d BT WR=0% EV=-1.887)
- PAIR_PROMOTED: none

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
