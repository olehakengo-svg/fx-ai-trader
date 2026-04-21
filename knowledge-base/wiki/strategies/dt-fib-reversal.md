# DT Fib Reversal

## Overview
- **Entry Type**: `dt_fib_reversal`
- **Category**: MR (Mean Reversion)
- **Timeframe**: DT 15m
- **Status**: UNIVERSAL_SENTINEL (全ペア shadow) — 2026-04-21 GBP_USD PAIR_PROMOTE 撤回
- **Active Pairs**: Sentinel on all pairs

## 2026-04-21 Audit B: PAIR_PROMOTE 撤回判断

**撤回根拠 (365d 15m BT 再走)**:
| 時点 | N | WR | EV | 判定 |
|---|---|---|---|---|
| promotion時 (旧 BT) | 22 | 72.7% | +0.310 | 正 |
| **2026-04-21 audit** | **30** | **53.3%** | **-0.224** | **劣化確認** |

- Wilson 95% CI [35.5%, 70.4%] → 下限 < GBP_USD BEV 37.9% → **edge 非有意**
- LIVE 側: GBP_USD N=0 (promotion 後未発火) → 安全弁として撤回可能
- 撤回 = UNIVERSAL_SENTINEL 復帰 (shadow のみ). 再昇格条件: 365d BT で Wilson 下限 > BEV を復旧し、かつ Live shadow で N≥20 EV>0 確認

詳細: [[pre-registration-2026-04-21]] と対称. **promoted 戦略への同水準の quant rigor 適用**.

## BT Performance (365d, 15m)
| Pair | N | WR | EV | PF | PnL |
|---|---|---|---|---|---|
| EUR_USD | 10 | 80.0% | +0.407 | 1.96 | +4.1p |
| GBP_USD (旧) | 22 | 72.7% | +0.374 | 1.86 | +7.9p |
| **GBP_USD (2026-04-21)** | **30** | **53.3%** | **-0.224** | <1.0 | **-6.7p** |
| EUR_JPY | 81 | 54.3% | -0.199 | 0.74 | -16.2p |

## Live Performance (post-cutoff)
Live data accumulating

## Signal Logic
Fibonacci retracement-based reversal for daytrade timeframe. Identifies swing high/low, calculates Fib levels (38.2%, 50%, 61.8%), and enters reversal trades at key retracement levels with confirmation from price action or momentum indicators.

## Current Configuration
- Lot Boost: default (1.0x)
- PAIR_DEMOTED: none
- PAIR_PROMOTED: none

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
