---
id: 20260505-0112-w4-redesign-cpd_divergence
title: "[W4-Redesign #9] cpd_divergence (Tier 2 (Shadow)) — TIMING/A"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T01:12:00+0900
roadmap_gate: "W4-EDA Wave 4 redesign — REDESIGN_QUEUE rank #9 (A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/cpd_divergence.md
  - audits/edge_design/_REDESIGN_QUEUE.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - audits/edge_design/streak_reversal.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/cpd_divergence.md`) で **TIMING** / 推奨度 **A** と判定。
REDESIGN_QUEUE rank **#9** (Tier 2 (Shadow))。

「思想は正、設計が誤」仮説に基づく Wave 4 一括 redesign の一環。

## Audit Axis 8 抜粋

> Tier 2 Shadow だが、tier-master 365d BT EV は `—`、audit DB は 0 rows、G1 never-logged 診断は 30,592 eval / 0 signal なので、underperforming/insufficient cell として failure mode 診断対象にする。

破綻候補は Axis 3 と Axis 6。Axis 2 の trigger は thesis と整合しているが、現在足 `iloc[-1]` と leader cache `tail(120)` に依存し、closed-bar alignment と dedup が strategy 内にない。さらに task cell は `pairs: ALL` だが実装は GBPUSD 専用で、ALL routing では 4/5 pairs が必ず `return None` になる。Axis 4 は thesis を壊す MA/HMM 系 hard filter はなく、Axis 5 も大きな破綻ではない。

再設計案は timing/data alignment を先に直す。`ctx.df.iloc[-2]` と leader_df の同一 timestamp 以前だけで signal を作り、execution は次 bar の `ctx.entry` に固定する。併せて `(strategy, symbol, signal, signal_bar_time)` の per-bar dedup を入れる。pair scope は `ALL` ではなく `GBP_USD` cell として tier/audit を分離し、他 pairs は別 hypothesis として扱う。

## Audit Redesign Recommendation 抜粋

> 思想と trigger は維持する。修正対象は timing/data alignment の 1 系統を第一優先にする。具体的には、`b_ret` / `a_ret` の z-score と rolling correlation を `ctx.df.index[-2]` までの確定足で計算し、leader_df も `leader_df.loc[:signal_bar_time]` に切ってから reindex する。signal は確定足、entry は次 bar の `ctx.entry` に分離する。

# 1. 制約 (Rule R1)

- **No live promote** in this task. Shadow-stage 実装と BT 検証のみ。
- **Pre-reg LOCK** 必須: 仕様変更を `knowledge-base/wiki/decisions/` に記録してから実装。
- **365d BT 必須**: 現行版 vs proposed variant を A/B 比較。
- **WF folds >= 3, positive_ratio >= 0.67** で stable 確認。
- **Bonferroni-adjusted p < 0.05** または **Wilson lo current+0.05 以上** で有意性確認。
- **Kelly >= 0.40** が望ましい (lower bar OK if defensive narrowing)。

# 2. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/cpd_divergence-redesign-2026-05-05.md` に:
- 現行設計の問題点 (audit Axis 引用)
- proposed variant の仕様 (具体コード差分)
- 評価軸 (BT 指標 + 合否基準)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_cpd_divergence_redesign.py` に proposed variant の挙動テスト。

## Step 3: 実装

audit 推奨に従い変更。最小差分を優先。

## Step 4: テスト緑

## Step 5: 365d BT (現行 vs proposed)

`knowledge-base/raw/bt-results/cpd_divergence-redesign-2026-05-05.json` に保存。

## Step 6: LOCK criteria 判定

- PASS → commit + shadow promote 提案 (別タスクで live 昇格)
- FAIL → REJECT, 原因分析, Wave 4 別 candidate へ移行

## Step 7: Codex adversarial self-review

post-hoc selection / data leakage / look-ahead bias チェック。

# 3. Acceptance

- Pre-reg LOCK doc あり
- 失敗テスト → 緑
- BT 比較レポートあり
- LOCK criteria 判定 (PASS / FAIL) 明示
- Codex self-review 通過

# 4. Out of Scope

- Live 昇格 (本タスクは shadow promote 提案までで停止、user 承認後別タスク)
- 他 strategies の修正
- 新規 edge 探索

# 5. Notes

- このタスクは W4-Redesign 40 件一括 dispatch の一部。Codex は serial 処理で 1 件ずつ進めること。
- 実装が大規模 (Axis 2-5 全部修正等) になる場合は途中で abort し、scope を絞って別タスク化する。
- audit に書かれていない設計変更を勝手に追加しない (post-hoc justification 罠)。
