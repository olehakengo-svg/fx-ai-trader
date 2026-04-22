# EMA200 Trend Reversal

## Overview
- **Entry Type**: `ema200_trend_reversal`
- **Category**: TF (Trend Following) / MR
- **Timeframe**: DT 15m
- **Status**: PAIR_PROMOTED × USD_JPY (2026-04-23, shadow sub-cell分析)
- **Active Pairs**: USD_JPY 実弾、他ペアShadow継続

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
Live data accumulating (USD_JPY 2026-04-23〜)

## Shadow Sub-cell Analysis (2026-04-08 〜 2026-04-23, N=27)
BT negative にもかかわらず shadow で USD_JPY 特化エッジを検出:

| 切り口 | N | WR | EV_raw | EV_cost | PF | pos_r | Bootstrap 95% EV CI |
|---|---|---|---|---|---|---|---|
| 全体 | 27 | 40.7% | +1.17 | +0.17 | 1.23 | 0.70 | [-3.90, +6.33] |
| **USD_JPY 全セッション** | **13** | **61.5%** | +6.39 | **+5.39** | **4.76** | **0.89** | **[+1.12, +11.78]** ★ |
| **USD_JPY × Overlap (12-16 UTC)** | 7 | **100%** | +12.63 | **+11.63** | ∞ | 1.00 | [+7.84, +16.59] |

実測 spread+slip = 2.407p/trade (BT_COST 1.0p より重い) → それでも EV_raw 6.4p で吸収。
BT (Relaxed版 1h N=165 EV=-0.28) と反転している理由: shadow は 15m TF、Overlap session 集中で Live spread が BT より良好な時間帯をカバー。

詳細: [[shadow-subcell-analysis-2026-04-23]]

## Signal Logic
Enters reversal trades at the EMA200 level. When price breaks above/below EMA200 and retests it, enters in the breakout direction expecting EMA200 to act as new support/resistance. Requires EMA200 slope confirmation and RSI filter.

## Current Configuration (2026-04-23〜)
- **PAIR_PROMOTED: USD_JPY** (shadow N=13, Bootstrap EV CI [+1.12, +11.78])
- Lot Boost: default (1.0x, 既存 Kelly sizing ロジック)
- 他ペア: Shadow継続 (BT負EVのため実弾投入しない)
- **Guardrails**:
  - Live N=15 で EV_cost<-0.5p → 即 FORCE_DEMOTED 戻し
  - Live N=10 で WR<40% → pause
  - Daily DD>¥5,000 → pause

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
- [[shadow-subcell-analysis-2026-04-23]] — Promotion rationale & sub-cell analysis
