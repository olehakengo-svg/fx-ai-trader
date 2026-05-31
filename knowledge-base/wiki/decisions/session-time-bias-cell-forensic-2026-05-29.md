# session_time_bias — Lot Boost 1.3→1.0 + EUR_USD Cell-Conditional (rule:R2)

**Date**: 2026-05-29
**Rule**: R2 (Fast & Reactive demote/restructure, cell forensic supported)
**Author**: Claude (司令塔) / Cell forensic project_cell_forensic_2026_05_29

## Decision

1. `_STRATEGY_LOT_BOOST["session_time_bias"]`: **1.3 → 1.0** (cell-blind boost 解除)
2. `_PAIR_SESSION_FILTER` に `("session_time_bias", "EUR_USD"): {"London"}` 追加 (cell-conditional Live)
3. GBP_USD は既存 `_PAIR_DEMOTED` 維持 (2026-05-03 R2 LOCK)
4. USD_JPY は Shadow N=0、戦略本体 signal 上 fire していない (status quo)

## Context

- 2026-05-29 backfill で session_time_bias old N=7 EV=-111.34 → new N=11 EV=-175.50 (Δ EV=-64.16)。
- User 指摘: 「集計じゃなく cell で見るべき、Shadow に勝ち cell がある」
- Cell forensic で **EUR_USD London** が明確な edge と判明。

## Evidence (Cell Forensic)

### Live (post-backfill, ALL pre-R2 LOCK cohort)
- N=5 全て GBP_USD SELL (Asia/London) ← Live sample が毒 cell に集中
- WR=40.0% EV=-3.52pip PF=0.13 (PF<1 = 損失リスク>>利益)
- GBP_USD は既に `_PAIR_DEMOTED` (2026-05-03)、Live fire 停止済

### Shadow cells (pair × session)
| cell | N | WR | Wilson_lo | EV (pip) | PF | 判定 |
|---|---|---|---|---|---|---|
| **EUR_USD London** | **58** | **44.8%** | **0.327** | **+1.44** | **1.41** | ✅ **edge confirmed** |
| GBP_USD London | 45 | 37.8% | 0.251 | +0.98 | 1.19 | 🟢 (借 borderline) |
| EUR_USD NY | 5 | 20.0% | 0.036 | -0.12 | 0.97 | ⚪ small |
| EUR_USD Overlap | 34 | 26.5% | 0.146 | -1.88 | 0.63 | 🔴 |
| GBP_USD Overlap | 53 | 24.5% | 0.149 | -2.86 | 0.63 | 🔴 |
| **GBP_USD Asia** | **47** | **4.3%** | 0.012 | **-6.10** | 0.06 | 🔴 **toxic** |
| **GBP_USD NY** | 15 | 6.7% | 0.012 | **-7.03** | 0.18 | 🔴 **toxic** |

### Cohort 安定性 (Shadow only)
| cohort | N | WR | EV |
|---|---|---|---|
| pre_H1gate | 22 | 36.4% | -0.66 |
| H1gate | 66 | 21.2% | -3.44 |
| post_R2lock | 92 | 27.2% | -1.54 |
| current | 79 | 27.8% | -1.36 |

Aggregate は毒 cell 偏向で安定的に EV<0、しかし cell-level では **EUR_USD London は安定して edge** (cohort 分解時も 40%+ WR 維持確認)。

## Why Lot Boost 1.3× is Wrong

Boost は **戦略 × 全 cell に一律適用**:
- EUR_USD London (+1.44 EV) → boost で +1.87 EV (改善)
- EUR_USD Overlap (-1.88 EV) → boost で -2.44 EV (悪化)
- GBP_USD Overlap/Asia/NY (デモ済だが万一復活時) → 損失 1.3 倍

Boost は **cell-blind weapon**。memory `[feedback_size_lever_beats_skip_filter]` (2026-05-28 ZZ Pivot v60 で確立) は「SIZE lever > SKIP filter」を述べるが、これは **同一 cell 内の loser zone を SIZE で殺す** 文脈。Cell-blind aggregate boost には適用されない。

正解は memory `[vix_carry_unwind Overlap pilot]` (2026-05-13) と同じパターン:
- Aggregate EV<0 でも cell に edge があれば cell-conditional 維持
- Boost は edge cell が N≥30 + Wilson_lo>0.40 確認後

## Action

```python
# modules/demo_trader.py L6850
- "session_time_bias": 1.3,
+ "session_time_bias": 1.0,    # was 1.3 — cell-blind boost 解除

# modules/demo_trader.py L7154 _PAIR_SESSION_FILTER に追加
  _PAIR_SESSION_FILTER = {
      ("vix_carry_unwind", "USD_JPY"): {"Overlap"},
+     ("session_time_bias", "EUR_USD"): {"London"},  # 7 <= UTC hour < 12
  }
```

EUR_USD は `_PAIR_PROMOTED` (line 7035, shadow N=23 EV=+0.63 PF=1.15 旧根拠) に残るが、session filter で London のみ Live 発火。Asia/Overlap/NY は自動的に Shadow tracking。

GBP_USD は `_PAIR_DEMOTED` 維持 (2026-05-03 R2 LOCK 妥当性が cell forensic で再確認: Asia/NY/Overlap 全て toxic)。

## Reinstatement Conditions (Pre-reg LOCK)

Lot boost 復活条件:
1. EUR_USD London Live N≥30 + Wilson_lo>0.40 + EV>+1.0 pip
2. Bonferroni m=4 (London/Overlap/NY/Asia) で p<0.05
3. 3 cohort 連続で London edge 維持

GBP_USD London cell 復活条件:
1. Shadow N≥45 → 60 で WR≥40% 維持確認
2. Bonferroni m=4 で London のみ p<0.05
3. `_PAIR_SESSION_FILTER` 追加 (`("session_time_bias", "GBP_USD"): {"London"}`)
4. `_PAIR_DEMOTED` から条件付き解除

## Cross-References

- Memory: `project_cell_forensic_2026_05_29.md`
- Sibling decision: `xs-momentum-pair-demote-2026-05-29.md`
- Related memory: `[vix_carry_unwind Overlap pilot]`, `[feedback_ma_filter_breaks_mr]`
- v8.6 original basis (now superseded): "全3ペアBT正EV (JPY+0.427, EUR+0.650, GBP+0.266) — Breedon 2013"
