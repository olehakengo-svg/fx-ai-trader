---
id: 20260505-0140-w4-redesign-ma_regime_switch
title: "[W4-Redesign #37] ma_regime_switch (Tier 4 (SCALP_SENTINEL)) — DESIGN/A"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T01:40:00+0900
roadmap_gate: "W4-EDA Wave 4 redesign — REDESIGN_QUEUE rank #37 (A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/ma_regime_switch.md
  - audits/edge_design/_REDESIGN_QUEUE.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - audits/edge_design/streak_reversal.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/ma_regime_switch.md`) で **DESIGN** / 推奨度 **A** と判定。
REDESIGN_QUEUE rank **#37** (Tier 4 (SCALP_SENTINEL))。

「思想は正、設計が誤」仮説に基づく Wave 4 一括 redesign の一環。

## Audit Axis 8 抜粋

> Tier 4 (SCALP_SENTINEL) なので failure mode 診断対象。破綻軸は Axis 2 と Axis 4 が主、Axis 3 と Axis 5 が副次。思想は明確で、Trend branch と MR branch の局所 trigger もそれぞれ EMA/ADX continuation と BB%B/RSI/Stoch reversion を持つため、edge thesis 自体は捨てない。一方、中心の regime switch が M15 ATR rolling percentile ではなく 1m BB width percentile proxy で分岐しており、レジーム誤分類で Trend/MR の適用先を壊す。さらに bar-close/dedup 不在と、MR 側が mean target を持たない ATR 1.2R TP で、scalp の cost-edge ratio を吸収しにくい。

再設計案は Trigger/Filter 置換を主軸にする。`atr_pct = ctx.bb_width_pct * 100` を廃止し、実際の M15 ATR rolling percentile または少なくとも M15 BB/ATR percentile の同一時間足 proxy に置換する。High/Low/Mid の hard threshold は 70/30 固定ではなく、まず `High vol AND ADX percentile high` を Trend、`Low vol AND ADX low/flat` を MR に分け、Mid no-fire は残す。Timing は signal を M5/M15 close 確定後の次 1m bar で一度だけ評価し、routing または strategy stat

## Audit Redesign Recommendation 抜粋

> 思想はコードから十分に導けるため `THESIS_INVALID` ではない。現行 v1c-rev は旧 v1c の N=22 機能不全から N=397 へ改善しているが、PF=0.939 / Kelly=0.0 / raw p=0.99999 で edge には届いていない。主因は hybrid thesis そのものより、regime trigger が thesis の M15 ATR percentile から 1m BB width proxy にすり替わっている点と、MR exit が mean-reversion geometry になっていない点にある。

# 1. 制約 (Rule R1)

- **No live promote** in this task. Shadow-stage 実装と BT 検証のみ。
- **Pre-reg LOCK** 必須: 仕様変更を `knowledge-base/wiki/decisions/` に記録してから実装。
- **365d BT 必須**: 現行版 vs proposed variant を A/B 比較。
- **WF folds >= 3, positive_ratio >= 0.67** で stable 確認。
- **Bonferroni-adjusted p < 0.05** または **Wilson lo current+0.05 以上** で有意性確認。
- **Kelly >= 0.40** が望ましい (lower bar OK if defensive narrowing)。

# 2. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/ma_regime_switch-redesign-2026-05-05.md` に:
- 現行設計の問題点 (audit Axis 引用)
- proposed variant の仕様 (具体コード差分)
- 評価軸 (BT 指標 + 合否基準)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_ma_regime_switch_redesign.py` に proposed variant の挙動テスト。

## Step 3: 実装

audit 推奨に従い変更。最小差分を優先。

## Step 4: テスト緑

## Step 5: 365d BT (現行 vs proposed)

`knowledge-base/raw/bt-results/ma_regime_switch-redesign-2026-05-05.json` に保存。

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
