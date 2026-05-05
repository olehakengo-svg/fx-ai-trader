---
id: 20260505-0135-w4-redesign-orb_trap
title: "[W4-Redesign #32] orb_trap (Tier 3 (FORCE_DEMOTED)) — DESIGN/A"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T01:35:00+0900
roadmap_gate: "W4-EDA Wave 4 redesign — REDESIGN_QUEUE rank #32 (A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/orb_trap.md
  - audits/edge_design/_REDESIGN_QUEUE.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - audits/edge_design/streak_reversal.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/orb_trap.md`) で **DESIGN** / 推奨度 **A** と判定。
REDESIGN_QUEUE rank **#32** (Tier 3 (FORCE_DEMOTED))。

「思想は正、設計が誤」仮説に基づく Wave 4 一括 redesign の一環。

## Audit Axis 8 抜粋

> Tier 3 (FORCE_DEMOTED) の failure mode は Axis 5 主体、補助的に Axis 6/7。Axis 2 の trigger は false breakout fade を捕捉しており、Axis 3 も bar-close confirmation として大きな破綻はない。Axis 4 の filters も entry universe を不自然に潰す MA/HMM 型の破壊ではなく、noise / whipsaw / true breakout 除外として概ね coherent。

破綻は exit geometry にある。コードは thesis 上の自然な利確点を OR 反対端に置くが、RR 最低値を満たさない場合に TP を OR 反対端の外へ動かす。これにより「レンジへ戻る」edge を取る MR ではなく、「レンジ回帰後もさらに同方向へ伸びる」edge を要求する設計になる。365d scan の全ペア負EVと、短期BTだけ好調だった履歴は、trigger ではなく TP geometry と pair/session 条件が相場局面に過適合していた可能性を示す。

再設計案は Stop/TP geometry を先に直すこと。具体的には、TP を常に `OR_low/OR_high` または `OR_mid` へ固定し、RR 不足時は TP 延伸ではなく signal reject にする。必要なら `MIN_RR` を撤去して、`reward_to_OR_edge / risk_to_break_extreme` が低い setup を別 bucket として記録し、SL は breakout 極値 + buffer のまま維持する。次点で pair/session を分け、USDJPY LDN、USDJPY NY、EU

## Audit Redesign Recommendation 抜粋

> 修正対象は主に stop/TP geometry の 1 系統。想定 diff は、`_rr < MIN_RR` の場合に `tp` を `ctx.entry +/- _sl_d * MIN_RR` へ延伸する処理を削除し、`return None` に変えるか、`MIN_RR` を `reward_to_or_edge / risk` の診断 metric に格下げする形。これで OR 反対端回帰という thesis と exit が一致する。

# 1. 制約 (Rule R1)

- **No live promote** in this task. Shadow-stage 実装と BT 検証のみ。
- **Pre-reg LOCK** 必須: 仕様変更を `knowledge-base/wiki/decisions/` に記録してから実装。
- **365d BT 必須**: 現行版 vs proposed variant を A/B 比較。
- **WF folds >= 3, positive_ratio >= 0.67** で stable 確認。
- **Bonferroni-adjusted p < 0.05** または **Wilson lo current+0.05 以上** で有意性確認。
- **Kelly >= 0.40** が望ましい (lower bar OK if defensive narrowing)。

# 2. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/orb_trap-redesign-2026-05-05.md` に:
- 現行設計の問題点 (audit Axis 引用)
- proposed variant の仕様 (具体コード差分)
- 評価軸 (BT 指標 + 合否基準)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_orb_trap_redesign.py` に proposed variant の挙動テスト。

## Step 3: 実装

audit 推奨に従い変更。最小差分を優先。

## Step 4: テスト緑

## Step 5: 365d BT (現行 vs proposed)

`knowledge-base/raw/bt-results/orb_trap-redesign-2026-05-05.json` に保存。

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
