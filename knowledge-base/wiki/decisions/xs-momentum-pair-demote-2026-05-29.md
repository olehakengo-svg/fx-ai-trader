# xs_momentum × EUR_USD / GBP_USD — Pair Demote (rule:R2)

**Date**: 2026-05-29
**Rule**: R2 (Fast & Reactive demote, cell forensic supported)
**Author**: Claude (司令塔) / Cell forensic project_cell_forensic_2026_05_29

## Decision

`("xs_momentum", "EUR_USD")` および `("xs_momentum", "GBP_USD")` を `_PAIR_PROMOTED` から `_PAIR_DEMOTED` へ移動。USD_JPY は既に PAIR_DEMOTED (v8.6) のため、戦略全体が Shadow only に転落。

## Context

- 2026-05-29 `tools/backfill_oanda_strategy_2026_05_19.py --apply` で過去 13 件 (16 件 chain hits 含む) の `oanda_trades.strategy=NULL` を再帰属。`xs_momentum` は old N=7 EV=+19.76 → new N=9 EV=-39.14 (Δ EV=-58.91)。
- User 指摘「期間で考えると調整したやつしてないやつが混在、cell が悪いだけかも」を受け、cell forensic 実施。

## Evidence (Cell Forensic)

### Live (post-backfill)
- N=7 (一部新規 fire 含む現時点で N=10) WR=42.9% EV=+0.56pip PF=1.12
- 内訳: pre-H1gate +22p×1 (大勝)、H1gate -16.9p (3 件)、post_R2lock -1.4p (3 件)
- Live の正 EV は **pre-H1gate 単発 +22p の outlier** が押し上げ。残り 6 件は EV<0。

### Shadow cells (pair × direction, N≥10)
| cell | N | WR | Wilson_lo | EV (pip) | PF | 判定 |
|---|---|---|---|---|---|---|
| USD_JPY BUY | 36 | 33.3% | 0.20 | +0.39 | 1.09 | ⚪ noise (Wlo<0.30) |
| GBP_USD SELL | 26 | 38.5% | 0.22 | +0.21 | 1.03 | ⚪ noise |
| GBP_USD BUY | 55 | 21.8% | 0.13 | **-2.25** | 0.67 | 🔴 |
| USD_JPY SELL | 22 | 18.2% | 0.07 | **-5.87** | 0.26 | 🔴 |
| EUR_USD BUY | 42 | 16.7% | 0.08 | **-3.41** | 0.39 | 🔴 |
| EUR_USD SELL | 43 | 20.9% | 0.11 | **-5.47** | 0.35 | 🔴 |

**No cell with Wilson_lo>0.30**. Bonferroni-corrected (m=6 cells, alpha=0.05/6) で全 cell 棄却。

### Cohort × Shadow
| cohort | N | WR | EV (pip) |
|---|---|---|---|
| pre_H1gate | 53 | 30.2% | -0.25 |
| H1gate | 39 | 23.1% | -5.27 |
| post_R2lock | 41 | 39.0% | +1.85 |
| **current (post 2026-05-21)** | **91** | **14.3%** | **-5.15** 🚨 |

`current` cohort で **完全崩壊**。Regime change により設計 (cross-sectional momentum) の edge が失われた可能性。

## Rationale

Memory `[監査=設計の正誤、N不足は別問題]` (W4-EDA 2026-05-05) によれば、設計監査と N 蓄積は別軸。本件は:
- 設計監査: Shadow cell decomposition で edge cell 0 件 (Wilson_lo>0.30 通過なし)
- N: Shadow 各 cell N≥40 — 十分蓄積済
- 結論: **設計が現 regime で失効**

Memory `[Shadow-first quant architecture]` も「BT は軽量 sanity filter、Shadow が真の estimator」と規定。Shadow で edge 喪失 = 戦略全体が機能していない。

## Action

```python
# modules/demo_trader.py
# _PAIR_PROMOTED (around L7014-7018) — REMOVED
- ("xs_momentum", "GBP_USD"),
- ("xs_momentum", "EUR_USD"),

# _PAIR_DEMOTED (after line 6902) — ADDED
+ ("xs_momentum", "EUR_USD"),
+ ("xs_momentum", "GBP_USD"),
```

USD_JPY は既存 PAIR_DEMOTED (line 6902, v8.6) なので 3 ペア全てが Shadow only。Shadow 蓄積は継続 (regime 復活時に検出可能、`current` cohort EV<0 が解消すれば再評価)。

## Reinstatement Conditions (Pre-reg LOCK)

`current` cohort Shadow で以下を全て満たした場合のみ再評価:
1. 任意の pair × direction cell で N≥30 + Wilson_lo>0.40 + EV>+1.0 pip
2. Bonferroni-corrected p<0.05 (m=6 cells)
3. 3 cohort 連続で同一 cell が edge 維持
4. 365d BT で同方向 edge 確認

## Cross-References

- Memory: `project_cell_forensic_2026_05_29.md` (この commit と同時投入予定)
- Backfill: `tools/backfill_oanda_strategy_2026_05_19.py` apply 2026-05-29
- Cell forensic script: `/tmp/cell_forensic.py` (Claude local analysis)
- Related: `feedback_cohort_time_check.md` (memory)、`feedback_label_empirical_audit.md`
