# Streak Reversal

## Overview
- **Entry Type**: `streak_reversal`
- **Category**: MR (Mean Reversion)
- **Timeframe**: DT 15m
- **Status**: PAIR_DEMOTED (USD_JPY) — 2026-05-11 clean-live audit demote (rule:R2)
- **Active Pairs**: USD_JPY (PAIR_DEMOTED), 他ペアは Phase0 auto-Shadow 継続

## Previously
- 〜2026-04-22: Phase0 auto-Shadow (PP/EL未指定) 全ペア
- 2026-04-22: PAIR_PROMOTED × USD_JPY (二重WF昇格)
- 2026-05-04: c52d8e3 r2-15cell-LOCK Gate 0 ACCEPT 蘇生組
- 2026-05-11: clean-live audit demote — post-FLAG-DRIFT/FORCE-DEMOTED backfill 後の
  production /api/strategies/status で Live N=4 PnL=-27.5p WR=50%
  (BEV>=60% 未達)、Wilson_BF_lo=0.084、c52d8e3 8日 review-gate 早期撤回

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
