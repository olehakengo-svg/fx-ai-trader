# Streak Reversal

## Overview
- **Entry Type**: `streak_reversal`
- **Category**: MR (Mean Reversion)
- **Timeframe**: DT 15m
- **Status**: PAIR_PROMOTED (USD_JPY) — 2026-04-22 二重WF昇格
- **Active Pairs**: USD_JPY (PAIR_PROMOTED), 他ペアは Phase0 auto-Shadow 継続

## Previously
- 〜2026-04-22: Phase0 auto-Shadow (PP/EL未指定) 全ペア

## BT Performance (365d, 15m)
From massive alpha scan (Bonferroni significant):
| Edge | Pair | N | WR | p-value |
|---|---|---|---|---|
| 5streak BUY | USD_JPY | 586 | 58.7% | 1.3x10^-5 |

## Live Performance (post-cutoff)
Live data accumulating

## Signal Logic
Consecutive candle streak reversal (3-5 candle streak). Enters counter-direction after a series of consecutive same-direction candles, expecting mean reversion. Statistically significant reversal bias after extended unidirectional runs.

## Walk-Forward Stability (2026-04-22)
二重 WF クロスTF検証で pos_ratio=1.00 (全窓正) を達成:

| TF | Period | Window | N | Overall EV | pos_ratio | CV(EV) | Verdict |
|---|---|---|--:|--:|--:|--:|:-:|
| 15m | 365d | 20d (18窓) | 466 | +1.362 | **1.00** | 0.65 | ✅ stable |
| 5m  | 180d | 30d (7窓) | 693 | +0.948 | **1.00** | 0.62 | ✅ stable |

- Bonferroni 有意 BT (5streak BUY USD_JPY 15m): N=586 WR=58.7% p=1.3×10⁻⁵
- 単一TF根拠を超えたクロスTF確証 → PAIR_PROMOTED 昇格
- 詳細: `raw/analysis/roadmap-acceleration-synthesis-2026-04-22.md`

## Current Configuration
- Lot Boost: default (1.0x)
- PAIR_DEMOTED: none
- PAIR_PROMOTED: USD_JPY (v9.x 2026-04-22)

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
