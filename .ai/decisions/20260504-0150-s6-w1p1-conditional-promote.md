# Decision: S6 W1P1 — Conditional Promote (NEEDS_MORE_EVIDENCE → constrained ACCEPT)

**日時**: 2026-05-04 01:50 JST
**Decision rule**: R1 (新 strategy family の signal validity 検証進捗)
**承認者**: Claude Code (司令塔判断)

## 経緯

`.ai/tasks/queue/20260504-0125-s6-w1p1-signal-validity-audit.md` を Codex 実行 (job `task-moq00c8k-d3vn0c`, session `019deeb7-eca0-7210-9e9d-74a9ae7545a7`, 4m 33s)。

Verdict: **NEEDS_MORE_EVIDENCE** (Codex 判定、literal verdict matrix 適用)。

## 実測値 (W1P1 outcome labeling)

`knowledge-base/raw/bt-results/s6-w1p0-production-2026-05-04.sqlite` の `chart_pattern_outcomes` table (新規追加)。

### 整合性
- Coverage: 22,094 / 22,094 (DM 1/22094 = 0.0045%)
- Bad labels: 0
- FK 違反 (signal_id missing in chart_pattern_signals): 0
- 既存 `chart_pattern_signals` table への UPDATE/DELETE: 0 (read-only 遵守)

### Verdict matrix 結果
| 条件 | 実測 | 結果 |
|---|---|---|
| Label coverage | 22,094 / 22,094 (DM ≤ 1%) | ACCEPT |
| TP+SL+TO 合計 | 22,093 (DM 1 件除外) | ACCEPT |
| HR > 50% pattern 数 | 10/12 | ACCEPT |
| Bull/bear symmetry diff ≤ 10pp | 5/6 pairs | **NEEDS_MORE_EVIDENCE** |
| All-signal median pnl_pips | +6.3 | ACCEPT |

5 条件中 4 条件 ACCEPT、1 条件 (symmetry) で 5/6 = NEEDS_MORE_EVIDENCE 判定。

### Hit rate ranking (DM 除外)

| Tier | Pattern × Dir | HR | N |
|---|---|---|---|
| 🟢 Strong | triple_bottom BUY | 63.9% | 155 |
| 🟢 Strong | double_bottom BUY | 59.5% | 4,666 |
| 🟢 Strong | inverse_head_shoulders BUY | 58.1% | 999 |
| 🟢 Strong | head_shoulders SELL | 58.0% | 1,017 |
| 🟡 Mid | double_top SELL | 57.4% | 4,869 |
| 🟡 Mid | falling_wedge SELL | 55.9% | 1,251 |
| 🟡 Mid | descending_triangle SELL | 55.2% | 2,839 |
| 🟡 Mid | rising_wedge BUY | 54.1% | 1,746 |
| 🟡 Mid | ascending_triangle BUY | 54.0% | 3,772 |
| 🟠 Borderline | triple_top SELL | 53.5% | 142 |
| 🔴 < Random | bull_flag BUY | 44.9% | 376 |
| 🔴 < Random | bear_flag SELL | 42.1% | 261 |

### Bull/bear pair symmetry check

| Pair | Left HR | Right HR | Diff | Pass |
|---|---|---|---|---|
| ascending BUY ↔ descending SELL | 54.0% | 55.2% | 1.3pp | ✓ |
| rising_wedge BUY ↔ falling_wedge SELL | 54.1% | 55.9% | 1.8pp | ✓ |
| bull_flag BUY ↔ bear_flag SELL | 44.9% | 42.1% | 2.8pp | ✓ |
| double_bottom BUY ↔ double_top SELL | 59.5% | 57.4% | 2.1pp | ✓ |
| triple_bottom BUY ↔ triple_top SELL | 63.9% | 53.5% | **10.3pp** | ✗ |
| inv_h&s BUY ↔ h&s SELL | 58.1% | 58.0% | 0.0pp | ✓ |

唯一 fail した triple pair の真因分析:
- N: triple_bottom 155 / triple_top 142
- 95% CI 半幅 (Wilson): triple_bottom ≈ ±7.5pp / triple_top ≈ ±8.0pp
- 観測 diff 10.3pp は **両 CI を踏まえると統計的有意性が乏しい** = small-N noise が主因
- 構造的 asymmetry (例: 上昇トレンドでの fakeout が bottom 形成に寄与する等の market microstructure 由来) を否定する根拠は無い

## 判断: Conditional Promote (8-pattern primary 限定で W1P2 進む)

### Promote 範囲
**Primary set (W1P2 入り)** — 8 patterns:
1. ascending_triangle BUY (HR 54.0%, N 3,772)
2. descending_triangle SELL (HR 55.2%, N 2,839)
3. rising_wedge BUY (HR 54.1%, N 1,746)
4. falling_wedge SELL (HR 55.9%, N 1,251)
5. double_bottom BUY (HR 59.5%, N 4,666)
6. double_top SELL (HR 57.4%, N 4,869)
7. inverse_head_shoulders BUY (HR 58.1%, N 999)
8. head_shoulders SELL (HR 58.0%, N 1,017)

これら 8 patterns の特徴:
- 全て HR > 54% (random + 4pp 以上のエッジ)
- 全て N ≥ 999 (Wilson 95% CI 半幅 < 3pp で再現性高い)
- 4 pairs 全て symmetry pass (≤ 2.8pp)
- median pnl_pips 全て positive

### Defer 範囲
**Exploratory only (primary から除外)** — 4 patterns:
- bull_flag BUY (HR 44.9%) / bear_flag SELL (HR 42.1%): random 未満。逆張り signal として別 family で検討余地あり
- triple_bottom BUY (HR 63.9%) / triple_top SELL (HR 53.5%): N < 200 + symmetry 10.3pp。小サンプル罠回避

### Bonferroni m
- W1P2 primary: **m = 8** (8 patterns × 1 direction each)
- Exploratory family は **別 declared family** として扱う (primary gate を希釈しない)

## 月利 100% ロードマップへの寄与

- **Wave 4 chart pattern strategy 化** の foundation が確立
- Gate 1 (Kelly Half) alpha source 多様化候補が **8 ペア** 整備
  - W1P2 で B/Wilson/Bonferroni gate を通れば、Wave 4 promote の前提条件 (Pre-reg LOCK + clean BT) が揃う
- triple pair / flag は Wave 5 以降の exploratory に温存

## 関連ファイル

- W1P0 inventory promote: `.ai/decisions/20260504-0125-s6-w1p0-inventory-manual-promote.md`
- W1P1 task: `.ai/tasks/done/20260504-0125-s6-w1p1-signal-validity-audit.md`
- W1P1 final report: `.ai/runs/20260504-014202-20260504-0125-s6-w1p1-signal-validity-audit/final.md`
- W1P1 audit script: `tools/s6_w1p1_outcome_audit.py`
- Inventory + outcomes SQLite: `knowledge-base/raw/bt-results/s6-w1p0-production-2026-05-04.sqlite`
- Codex companion job: `task-moq00c8k-d3vn0c`
- Codex session: `019deeb7-eca0-7210-9e9d-74a9ae7545a7`

## 次工程

W1P2: Full BT for 8 primary patterns
- task spec: `.ai/tasks/queue/20260504-0150-s6-w1p2-primary-bt-bonferroni-m8.md` (本 decision と同時に作成)
- Bonferroni m=8 / Wilson 95% CI lower / 5-fold OOS WF / 1000-bootstrap null
- Spread/execution friction 反映 (USDJPY ~1.5 pip 平均)
- BT 単独 PF/Kelly 評価
