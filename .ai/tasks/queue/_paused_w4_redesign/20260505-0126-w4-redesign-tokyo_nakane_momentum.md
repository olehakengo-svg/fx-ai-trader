---
id: 20260505-0126-w4-redesign-tokyo_nakane_momentum
title: "[W4-Redesign #23] tokyo_nakane_momentum (Tier 2 (Shadow)) — DESIGN/A"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T01:26:00+0900
roadmap_gate: "W4-EDA Wave 4 redesign — REDESIGN_QUEUE rank #23 (A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/tokyo_nakane_momentum.md
  - audits/edge_design/_REDESIGN_QUEUE.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - audits/edge_design/streak_reversal.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/tokyo_nakane_momentum.md`) で **DESIGN** / 推奨度 **A** と判定。
REDESIGN_QUEUE rank **#23** (Tier 2 (Shadow))。

「思想は正、設計が誤」仮説に基づく Wave 4 一括 redesign の一環。

## Audit Axis 8 抜粋

> Tier 2 (Shadow) / phase0_shadow であり、tier-master 365d evidence が `—` のため昇格根拠は不足している。破綻軸は Axis 4 が主、Axis 6 と Axis 7 が補助。Axis 2 の DOWN→BUY trigger と Axis 5 の pre-fix low / half-retracement geometry は thesis と概ね整合する。一方で、USD/JPY 固有の実需フローを `ctx.is_jpy` で JPY cross 全体へ広げ、さらに HTF bearish agreement を hard block しているため、event-driven MR の tail を削る可能性が高い。

再設計案は「USDJPY-only thin fixing reversal」。`ctx.is_jpy` gate を USDJPY 明示 gate に置換し、HTF bear hard return は削除して score penalty へ降格する。entry は post-fix bar-close に固定し、00:45/01:00/01:15 の timestamp 解釈を backtest/router と合わせて 1 回だけ発火する形にする。既存 BT は不要条件だが、採用判断には 365d USDJPY-only で Wilson lower / PF / WF folds>=3 / Bonferroni-adjusted p / Kelly を出し直す必要がある。

## Audit Redesign Recommendation 抜粋

> 思想と中核 trigger は復活 candidate として残す価値がある。最優先は filter/pair gate の修正で、`ctx.is_jpy` を USDJPY 明示条件へ狭め、`_agreement == "bear"` の hard block を削除または `score -= 0.5` 程度の soft penalty に落とす。これはコードコメントの「HTF は soft penalty/bonus」「実需フローはトレンドに逆行可能」とも整合する。

# 1. 制約 (Rule R1)

- **No live promote** in this task. Shadow-stage 実装と BT 検証のみ。
- **Pre-reg LOCK** 必須: 仕様変更を `knowledge-base/wiki/decisions/` に記録してから実装。
- **365d BT 必須**: 現行版 vs proposed variant を A/B 比較。
- **WF folds >= 3, positive_ratio >= 0.67** で stable 確認。
- **Bonferroni-adjusted p < 0.05** または **Wilson lo current+0.05 以上** で有意性確認。
- **Kelly >= 0.40** が望ましい (lower bar OK if defensive narrowing)。

# 2. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/tokyo_nakane_momentum-redesign-2026-05-05.md` に:
- 現行設計の問題点 (audit Axis 引用)
- proposed variant の仕様 (具体コード差分)
- 評価軸 (BT 指標 + 合否基準)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_tokyo_nakane_momentum_redesign.py` に proposed variant の挙動テスト。

## Step 3: 実装

audit 推奨に従い変更。最小差分を優先。

## Step 4: テスト緑

## Step 5: 365d BT (現行 vs proposed)

`knowledge-base/raw/bt-results/tokyo_nakane_momentum-redesign-2026-05-05.json` に保存。

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
