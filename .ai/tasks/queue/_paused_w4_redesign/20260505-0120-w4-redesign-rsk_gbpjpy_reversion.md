---
id: 20260505-0120-w4-redesign-rsk_gbpjpy_reversion
title: "[W4-Redesign #17] rsk_gbpjpy_reversion (Tier 2 (Shadow)) — DESIGN/A"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T01:20:00+0900
roadmap_gate: "W4-EDA Wave 4 redesign — REDESIGN_QUEUE rank #17 (A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/rsk_gbpjpy_reversion.md
  - audits/edge_design/_REDESIGN_QUEUE.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - audits/edge_design/streak_reversal.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/rsk_gbpjpy_reversion.md`) で **DESIGN** / 推奨度 **A** と判定。
REDESIGN_QUEUE rank **#17** (Tier 2 (Shadow))。

「思想は正、設計が誤」仮説に基づく Wave 4 一括 redesign の一環。

## Audit Axis 8 抜粋

> `rsk_gbpjpy_reversion` は Tier 2 (Shadow) / phase0_shadow。破綻軸は Axis 5。Axis 2 の realized skewness extreme fade は thesis と一致し、Axis 3 の bar-close/dedup 問題も現コードでは修正済み。Axis 4 も MR を壊す MA/HMM 型 filter ではなく、GBPJPY 限定と反転確認で概ね thesis を補強している。

再設計案は stop/TP geometry の単独修正を第一候補にする。現行の `TP_ATR_MULT = 1.5`, `SL_ATR_MULT = 1.0`, `MIN_RR = 1.4` を前提にした「遠い TP / 近い SL」ではなく、MR 用に `TP = entry ± k * ATR` を縮めるか、skew_z の mean reversion 完了を proxy する target（例: `abs(skew_z)` が低下するまでの time exit / half-ATR target）へ変える。GBPJPY noise を許容するため stop は 1.5-2.0ATR 側へ広げ、`MAX_HOLD_BARS = 6` の time stop を主 exit に近づける variant を pre-register して比較すべき。

## Audit Redesign Recommendation 抜粋

> Trigger と pair gate は維持する。`abs(latest_z) >= 2.0` と `signal = -sign(skew_z)` は、realized skewness exhaustion を fade する thesis を直接表しており、ここを大きく変える理由はコード・既存 rsk audit の範囲では薄い。

# 1. 制約 (Rule R1)

- **No live promote** in this task. Shadow-stage 実装と BT 検証のみ。
- **Pre-reg LOCK** 必須: 仕様変更を `knowledge-base/wiki/decisions/` に記録してから実装。
- **365d BT 必須**: 現行版 vs proposed variant を A/B 比較。
- **WF folds >= 3, positive_ratio >= 0.67** で stable 確認。
- **Bonferroni-adjusted p < 0.05** または **Wilson lo current+0.05 以上** で有意性確認。
- **Kelly >= 0.40** が望ましい (lower bar OK if defensive narrowing)。

# 2. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/rsk_gbpjpy_reversion-redesign-2026-05-05.md` に:
- 現行設計の問題点 (audit Axis 引用)
- proposed variant の仕様 (具体コード差分)
- 評価軸 (BT 指標 + 合否基準)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_rsk_gbpjpy_reversion_redesign.py` に proposed variant の挙動テスト。

## Step 3: 実装

audit 推奨に従い変更。最小差分を優先。

## Step 4: テスト緑

## Step 5: 365d BT (現行 vs proposed)

`knowledge-base/raw/bt-results/rsk_gbpjpy_reversion-redesign-2026-05-05.json` に保存。

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
