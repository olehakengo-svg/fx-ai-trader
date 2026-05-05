---
id: 20260505-0110-w4-redesign-asia_range_fade_v1
title: "[W4-Redesign #7] asia_range_fade_v1 (Tier 2 (Shadow)) — TIMING/A"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T01:10:00+0900
roadmap_gate: "W4-EDA Wave 4 redesign — REDESIGN_QUEUE rank #7 (A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/asia_range_fade_v1.md
  - audits/edge_design/_REDESIGN_QUEUE.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - audits/edge_design/streak_reversal.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/asia_range_fade_v1.md`) で **TIMING** / 推奨度 **A** と判定。
REDESIGN_QUEUE rank **#7** (Tier 2 (Shadow))。

「思想は正、設計が誤」仮説に基づく Wave 4 一括 redesign の一環。

## Audit Axis 8 抜粋

> Tier 2 (Shadow) / phase0_shadow で、Tier 3/4 専用の復活診断ではないが、入力 metric は 365d BT EV `—` で evidence 欠落の shadow cell として failure mode を診断する。破綻候補は Axis 3 が主。Axis 2 の trigger と Axis 4 の filter は thesis と整合し、Axis 5 の exit geometry も MR と大きく矛盾しない。一方で range formation が current bar を含むため、touch/rejection bar 自身が range boundary を作る設計になっており、「形成済み range の端を fade する」という因果順序を汚している。さらに docstring の 4-bar same-direction entry 禁止が未実装で、bar-close / per-bar dedup の外部依存が残る。

再設計案は timing 1 系統。range formation を `df.iloc[-(RANGE_LOOKBACK + 1):-1]` の closed prior window に固定し、touch/rejection は `df.iloc[-1]` の確定 signal bar、entry は次 bar execution に分離する。あわせて `(instrument, signal, range_low/high bucket, bar_time)` または最低限 `(instrument, signal, bar_time)` の last-emitted guard を追加し、docstring の「直近 4 bars 内に同方向 entry 禁止」を実装する。本監

## Audit Redesign Recommendation 抜粋

> Trigger/filter/stop は維持候補にする。`touch + rejection + RSI extreme` は MR thesis を直接捕捉しており、MA/HMM 型の thesis 破壊 filter は見当たらない。最初に直すべき箇所は、range 算定と signal/execution の時系列分離である。

# 1. 制約 (Rule R1)

- **No live promote** in this task. Shadow-stage 実装と BT 検証のみ。
- **Pre-reg LOCK** 必須: 仕様変更を `knowledge-base/wiki/decisions/` に記録してから実装。
- **365d BT 必須**: 現行版 vs proposed variant を A/B 比較。
- **WF folds >= 3, positive_ratio >= 0.67** で stable 確認。
- **Bonferroni-adjusted p < 0.05** または **Wilson lo current+0.05 以上** で有意性確認。
- **Kelly >= 0.40** が望ましい (lower bar OK if defensive narrowing)。

# 2. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/asia_range_fade_v1-redesign-2026-05-05.md` に:
- 現行設計の問題点 (audit Axis 引用)
- proposed variant の仕様 (具体コード差分)
- 評価軸 (BT 指標 + 合否基準)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_asia_range_fade_v1_redesign.py` に proposed variant の挙動テスト。

## Step 3: 実装

audit 推奨に従い変更。最小差分を優先。

## Step 4: テスト緑

## Step 5: 365d BT (現行 vs proposed)

`knowledge-base/raw/bt-results/asia_range_fade_v1-redesign-2026-05-05.json` に保存。

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
