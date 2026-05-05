---
id: 20260505-0109-w4-redesign-alpha_intraday_seasonality
title: "[W4-Redesign #6] alpha_intraday_seasonality (Tier 2 (Shadow)) — DESIGN/A"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T01:09:00+0900
roadmap_gate: "W4-EDA Wave 4 redesign — REDESIGN_QUEUE rank #6 (A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/alpha_intraday_seasonality.md
  - audits/edge_design/_REDESIGN_QUEUE.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - audits/edge_design/streak_reversal.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/alpha_intraday_seasonality.md`) で **DESIGN** / 推奨度 **A** と判定。
REDESIGN_QUEUE rank **#6** (Tier 2 (Shadow))。

「思想は正、設計が誤」仮説に基づく Wave 4 一括 redesign の一環。

## Audit Axis 8 抜粋

> Tier 2 (Shadow) / phase0_shadow で、既存 evidence は昇格基準を満たさないため failure mode 診断対象とする。破綻軸は Axis 4 と Axis 5 が主、Axis 7 が補助。Axis 2 の trigger は seasonality thesis を直接捉えており、Axis 3 も trigger 統計には look-ahead がない。問題は、曜日×時間帯フローの tail を HTF Hard Block で削ることと、`Open→Close` 分布で推定した edge を ATR bracket exit で取りに行く geometry の不一致にある。

再設計案は 1 案目として「thin seasonality baseline」へ戻す。HTF Hard Block を削除または score feature に降格し、entry は同一曜日×時間帯の `mean_ret` が Bonferroni-aware な閾値を満たす場合だけ許可する。exit は thesis と合わせて time-based にし、signal 対象バーの close または最大 1 bar hold で決済する。保護 SL は同一 bucket の historical adverse quantile、または `k * std_ret * entry` から決め、TP も ATR ではなく bucket return distribution の上側分位に寄せる。

## Audit Redesign Recommendation 抜粋

> 思想と trigger 中核は有効候補。再設計の中心は trigger を新しく作ることではなく、HTF filter と exit geometry を thesis に合わせること。具体的には `ctx.htf["agreement"]` による hard return を外し、`mean_ret` / `std_ret` / `t_stat` / `cohens_d` は維持したまま、pair×weekday×hour ごとに最低 N を 30 以上へ上げる variant を作る。

# 1. 制約 (Rule R1)

- **No live promote** in this task. Shadow-stage 実装と BT 検証のみ。
- **Pre-reg LOCK** 必須: 仕様変更を `knowledge-base/wiki/decisions/` に記録してから実装。
- **365d BT 必須**: 現行版 vs proposed variant を A/B 比較。
- **WF folds >= 3, positive_ratio >= 0.67** で stable 確認。
- **Bonferroni-adjusted p < 0.05** または **Wilson lo current+0.05 以上** で有意性確認。
- **Kelly >= 0.40** が望ましい (lower bar OK if defensive narrowing)。

# 2. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/alpha_intraday_seasonality-redesign-2026-05-05.md` に:
- 現行設計の問題点 (audit Axis 引用)
- proposed variant の仕様 (具体コード差分)
- 評価軸 (BT 指標 + 合否基準)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_alpha_intraday_seasonality_redesign.py` に proposed variant の挙動テスト。

## Step 3: 実装

audit 推奨に従い変更。最小差分を優先。

## Step 4: テスト緑

## Step 5: 365d BT (現行 vs proposed)

`knowledge-base/raw/bt-results/alpha_intraday_seasonality-redesign-2026-05-05.json` に保存。

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
