---
id: 20260505-0106-w4-redesign-squeeze_release_momentum
title: "[W4-Redesign #2] squeeze_release_momentum (Tier 1 (LIVE)) — TIMING/A"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T01:06:00+0900
roadmap_gate: "W4-EDA Wave 4 redesign — REDESIGN_QUEUE rank #2 (A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/squeeze_release_momentum.md
  - audits/edge_design/_REDESIGN_QUEUE.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - audits/edge_design/streak_reversal.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/squeeze_release_momentum.md`) で **TIMING** / 推奨度 **A** と判定。
REDESIGN_QUEUE rank **#2** (Tier 1 (LIVE))。

「思想は正、設計が誤」仮説に基づく Wave 4 一括 redesign の一環。

## Audit Axis 8 抜粋

> Tier 3/4 ではないが、Tier 1 (LIVE) で Axis 7 が insufficient、かつ Axis 3 に timing 実装リスクがあるため診断対象とする。思想と trigger/filter/SLTP の方向性は整合しており、破綻候補は Axis 3 の intrabar / same-bar 重複リスク。特に SRM は「BB 幅が前足より拡大したか」と「足色」を現在 ctx 値で判定するため、closed-bar 前提が崩れると release 確認が未確定足の途中経過になる。

再設計案は timing hardening 1 系統。`ctx.bar_time` または `ctx.df.index[-1]` を使った per-bar dedup を strategy 内に持たせ、同一 symbol/signal/bar では一度しか emit しない。加えて trigger 判定は closed bar の `df.iloc[-2]` を signal bar、`ctx.entry` を次 bar entry として明示する variant を作る。新規 BT は本タスクでは実行せず、既存 positive signal を壊さないかを 365d + WF folds>=3 + Bonferroni/Kelly で検証する必要がある。

## Audit Redesign Recommendation 抜粋

> 最小修正は timing 1 系統。現在の thesis と trigger は維持し、closed-bar 化と per-bar dedup を追加する。コードレベルでは `evaluate()` 冒頭で `bar_id = ctx.bar_time or ctx.df.index[-1]` を得て、`(ctx.symbol, signal, bar_id)` の last-emitted guard を置く案が最小差分になる。ただし signal は trigger 後に確定するため、guard は `_is_buy/_is_sell` 判定直後に配置するのが自然。

# 1. 制約 (Rule R1)

- **No live promote** in this task. Shadow-stage 実装と BT 検証のみ。
- **Pre-reg LOCK** 必須: 仕様変更を `knowledge-base/wiki/decisions/` に記録してから実装。
- **365d BT 必須**: 現行版 vs proposed variant を A/B 比較。
- **WF folds >= 3, positive_ratio >= 0.67** で stable 確認。
- **Bonferroni-adjusted p < 0.05** または **Wilson lo current+0.05 以上** で有意性確認。
- **Kelly >= 0.40** が望ましい (lower bar OK if defensive narrowing)。

# 2. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/squeeze_release_momentum-redesign-2026-05-05.md` に:
- 現行設計の問題点 (audit Axis 引用)
- proposed variant の仕様 (具体コード差分)
- 評価軸 (BT 指標 + 合否基準)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_squeeze_release_momentum_redesign.py` に proposed variant の挙動テスト。

## Step 3: 実装

audit 推奨に従い変更。最小差分を優先。

## Step 4: テスト緑

## Step 5: 365d BT (現行 vs proposed)

`knowledge-base/raw/bt-results/squeeze_release_momentum-redesign-2026-05-05.json` に保存。

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
