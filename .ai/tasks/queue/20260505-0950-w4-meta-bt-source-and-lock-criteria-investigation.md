---
id: 20260505-0950-w4-meta-bt-source-and-lock-criteria-investigation
title: "[W4-Meta] BT データソース乖離 + LOCK criteria 緩和案 (W4P1 後の root cause)"
owner: codex
status: queued
priority: P0
created_at: 2026-05-05T09:50:00+0900
roadmap_gate: "W4-Redesign 72 件 mass batch を再開する前の前提条件整備"
rule: R1
prereq_artifacts:
  - .ai/tasks/done/20260505-0100-w4p1-streak-reversal-htf-soft-penalty.md
  - knowledge-base/raw/bt-results/streak-reversal-htf-soft-penalty-2026-05-05.json
  - knowledge-base/wiki/decisions/streak-reversal-htf-soft-penalty-pre-reg.md
  - audits/edge_design/streak_reversal.md
related:
  - knowledge-base/raw/bt-results/edge-lab-2026-04-23.json
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
---

# 0. なぜこのタスクか

W4P1 streak_reversal で **FAIL** が出たが、内容は不可解:

**Audit が引用した数値 (edge-lab-2026-04-23.json):**
- N=468, WR=72.2%, PF=3.07, Wilson lo=68%, Bonferroni p=1.3e-5, Kelly=0.487

**W4P1 の Codex BT (USD_JPY_5m parquet→15m resample, focused A/B):**
- baseline (現行 hard reject): N=1224, WR=37.99%, EV=+0.395, PF=1.037, Wilson lo=0.353, Kelly=0.013
- proposed (soft penalty): N=1564, WR=39.96%, EV=+0.775, PF=1.073, Wilson lo=0.376, Kelly=0.027

完全に別の母集団。soft penalty は positive direction だが Pre-reg LOCK 絶対基準（Kelly>=0.40 等）に届かず FAIL。

72 件の mass batch を再開する前に、**(A) BT データソース整合性** と **(B) LOCK criteria の妥当性** を整理する必要がある。

# 1. 仮説

## A. BT データソース乖離の原因候補

1. **edge-lab-2026-04-23.json は cell 別 (filtered) 集計**: 特定の hour bucket / session / pair filter 後の N=468 — つまり「特定 cohort で WR=72%」
2. **W4P1 BT は無 filter aggregate**: USD_JPY 全時間帯 15m re-sampled → N=1224 → WR=38% に下がる (signal の発火タイミングが幅広く拾われた)
3. つまり **同じ戦略の `aggregate` vs `cell-filtered`** の違い。Audit は cell-filtered を引用していた可能性。

## B. LOCK criteria (Kelly>=0.40 等) は厳しすぎ

mass dispatch のテンプレで「Kelly >= 0.40 が望ましい」と書いたが、これは streak_reversal の audit 数値 (Kelly=0.487) を念頭にした標準。実際の baseline Kelly がそもそも低い戦略 (例: 0.013) では、改善しても 0.40 に届かない。

**正しい LOCK criteria 設計:**
- 絶対基準: 戦略毎に baseline を測ってから設定 (impossible to set globally)
- **相対基準を主軸に**:
  - regression なし (PF, Wilson lo, EV が悪化しない)
  - positive direction (改善方向で 95% CI 上限が現行を上回る)
  - cell-level Bonferroni 有意 (multiple testing 補正後 p<0.05)
- **絶対 floor**: Wilson lo >= 0.45, PF >= 1.0 など最低限の sanity

# 2. このタスクの目的

1. **edge-lab-2026-04-23.json と W4P1 BT の差分原因を特定**
2. **W4-Redesign 全 72 件で使うべき統一 BT データソース指定**
3. **LOCK criteria を相対基準ベースに改訂した spec template 提案**
4. **改訂版 dispatch script も成果物に含める** (Claude が再実行できるように)

# 3. Investigation Steps

## Step 1: edge-lab-2026-04-23.json の中身確認

- N=468 はどの cohort/filter で出たか
- 何の指標か (cell-filtered? hour-bucket? session-only?)
- streak_reversal だけでなく他戦略も同様の cell vs aggregate の乖離があるか

## Step 2: W4P1 BT path の確認

- USD_JPY_5m → 15m リサンプルが production の `run_daytrade_backtest` と等価か
- 5m → 15m リサンプル時に発火タイミングが変わって N が増えるのは正しいか
- production 経路で 365d full BT が完走できない原因 (Yahoo 60d 制限) の回避策

## Step 3: 統一 BT データソース提案

選択肢:
- **A**: 現行 `run_daytrade_backtest` 経路 + 90d window (Yahoo 60d 制限内で複数 fold)
- **B**: repo 内 parquet (USD_JPY_5m, etc.) を base に長期 BT
- **C**: edge-lab cell-filtered 系を再利用 (cohort 仕様明示)

各選択肢の長所/短所をまとめ、推奨 + spec を出す。

## Step 4: LOCK criteria 改訂 template

例:
```yaml
lock_criteria:
  regression_check:
    - pf_change >= 0  # PF 悪化なし
    - wilson_lo_change >= -0.02  # 2pp 以内の悪化なら許容
    - ev_change >= 0  # EV 悪化なし
  positive_direction:
    - n_change_pct >= -10  # 発火数大幅減少なし
    - one_of: [wilson_lo_change >= +0.02, ev_change_pct >= +10, pf_change >= +0.05]
  significance:
    - cell_level_bonferroni_p < 0.05  # cell 別 Bonferroni
  sanity_floor:
    - wilson_lo_proposed >= 0.40
    - pf_proposed >= 1.0
```

戦略毎に絶対 Kelly 基準を要求する代わりに、relative + sanity の組み合わせ。

## Step 5: 改訂 dispatch script 提案

`tools/w4_redesign_dispatch_v2.py` で:
- audit から redesign axis を抽出
- 統一 BT データソース指定を埋め込む
- 改訂 LOCK criteria を埋め込む
- 72 件分の queue file を再生成

実装はしない (Claude が走らせる側)、提案 spec のみ。

## Step 6: Codex 自己レビュー

- BT 乖離の説明が論理的か
- LOCK criteria が緩すぎず厳しすぎないか (W4P1 の soft penalty が PASS するレベルになるか)
- post-hoc adjustment になっていないか (W4P1 を救済する目的で基準を緩めていないか)

# 4. Acceptance

- `knowledge-base/wiki/analyses/w4-redesign-bt-source-and-lock-criteria-2026-05-05.md` に:
  - BT データソース乖離の原因分析
  - 統一 BT データソース推奨
  - 改訂 LOCK criteria template
  - dispatch script v2 spec
  - W4P1 streak_reversal を改訂基準で再評価したらどうなるか試算
- 既存 W4P1 の判定 (FAIL) を覆すかどうかの推奨

# 5. Out of Scope

- W4P1 の再 BT 実行 (Step 6 試算のみ)
- 72 件の re-dispatch (Claude が別タスクで実行)
- audit DB の再構築

# 6. Notes

- post-hoc justification 罠注意: W4P1 を pass させるためだけに基準を緩めるのではなく、汎用的に正しい基準を提案
- audit は user 仮説 ("思想は正、設計が誤") を前提に行われた。LOCK criteria が厳しすぎて全件 FAIL になると audit の意義が消える
- 同時に、緩すぎて noise を拾うのも危険 (post-hoc selection)
