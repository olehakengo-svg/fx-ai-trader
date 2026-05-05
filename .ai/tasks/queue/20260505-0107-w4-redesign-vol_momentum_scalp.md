---
id: 20260505-0107-w4-redesign-vol_momentum_scalp
title: "[W4-Redesign #4] vol_momentum_scalp (Tier 1 (LIVE)) — TIMING/A"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T01:07:00+0900
roadmap_gate: "W4-EDA Wave 4 redesign — REDESIGN_QUEUE rank #4 (A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/vol_momentum_scalp.md
  - audits/edge_design/_REDESIGN_QUEUE.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - audits/edge_design/streak_reversal.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/vol_momentum_scalp.md`) で **TIMING** / 推奨度 **A** と判定。
REDESIGN_QUEUE rank **#4** (Tier 1 (LIVE))。

「思想は正、設計が誤」仮説に基づく Wave 4 一括 redesign の一環。

## Audit Axis 8 抜粋

> Tier 3/4 ではないが、Tier 1 (LIVE) で Axis 7 が insufficient、かつ Axis 3 に timing 実装リスクがあるため診断対象とする。Axis 2/4/5 は momentum breakout thesis と整合しており、現時点で「思想は正、trigger/filter/geometry も概ね正」と見る。破綻候補は Axis 3 の closed-bar / per-bar dedup 不在で、live 実行層が intrabar evaluate する場合に BB %B と足色が未確定のまま発火する。

再設計案は timing hardening 1 系統。`evaluate()` 内で signal bar を closed bar に固定し、`ctx.entry` は次 bar execution として扱う。さらに `(symbol, strategy, signal, bar_id)` の last-emitted guard を strategy または実行層に持たせ、同一 5m bar の多重 Candidate を防ぐ。既存 positive pocket を壊す可能性があるため、本監査では実装せず、365d + WF folds>=3 + Bonferroni/Kelly で再検証する。

## Audit Redesign Recommendation 抜粋

> 最小修正は trigger の思想を変えず、timing だけを固めること。コードレベルでは `evaluate()` 冒頭または signal 確定直後に `bar_id = ctx.bar_time or ctx.df.index[-1]` 相当を得て、同一 `(ctx.symbol, self.name, signal, bar_id)` を再 emit しない guard を追加する案が第一候補になる。

# 1. 制約 (Rule R1)

- **No live promote** in this task. Shadow-stage 実装と BT 検証のみ。
- **Pre-reg LOCK** 必須: 仕様変更を `knowledge-base/wiki/decisions/` に記録してから実装。
- **365d BT 必須**: 現行版 vs proposed variant を A/B 比較。
- **WF folds >= 3, positive_ratio >= 0.67** で stable 確認。
- **Bonferroni-adjusted p < 0.05** または **Wilson lo current+0.05 以上** で有意性確認。
- **Kelly >= 0.40** が望ましい (lower bar OK if defensive narrowing)。

# 2. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/vol_momentum_scalp-redesign-2026-05-05.md` に:
- 現行設計の問題点 (audit Axis 引用)
- proposed variant の仕様 (具体コード差分)
- 評価軸 (BT 指標 + 合否基準)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_vol_momentum_scalp_redesign.py` に proposed variant の挙動テスト。

## Step 3: 実装

audit 推奨に従い変更。最小差分を優先。

## Step 4: テスト緑

## Step 5: 365d BT (現行 vs proposed)

`knowledge-base/raw/bt-results/vol_momentum_scalp-redesign-2026-05-05.json` に保存。

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
