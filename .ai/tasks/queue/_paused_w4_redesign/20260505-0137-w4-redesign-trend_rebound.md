---
id: 20260505-0137-w4-redesign-trend_rebound
title: "[W4-Redesign #34] trend_rebound (Tier 3 (FORCE_DEMOTED)) — DESIGN/A"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T01:37:00+0900
roadmap_gate: "W4-EDA Wave 4 redesign — REDESIGN_QUEUE rank #34 (A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/trend_rebound.md
  - audits/edge_design/_REDESIGN_QUEUE.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - audits/edge_design/streak_reversal.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/trend_rebound.md`) で **DESIGN** / 推奨度 **A** と判定。
REDESIGN_QUEUE rank **#34** (Tier 3 (FORCE_DEMOTED))。

「思想は正、設計が誤」仮説に基づく Wave 4 一括 redesign の一環。

## Audit Axis 8 抜粋

> `trend_rebound` is Tier 3 (FORCE_DEMOTED), so failure diagnosis is required. The thesis is valid enough to audit: strong-trend pullback/rebound is explicit in code and the trigger includes oversold/overbought plus reversal candle confirmation. The design break is concentrated in Axis 2 and Axis 5, with Axis 6 adding deployment risk.

破綻点は `momentum_limit` の符号設計である。現在の BUY 条件 `_momentum < +8` は「急落しすぎていない」ではなく「強い上昇ではない」だけを見ており、下降トレンド中にさらに強く落ちている足を許す。SELL 条件 `_momentum > -8` も同様に、上昇トレンド中にさらに強く上がっている足を許す。再設計案は、BUY を `-momentum_limit <= _momentum <= 0` または `_momentum > -momentum_limit` かつ `macdh > macdh_prev` 必須、SELL を `0 <= _momentum <= momentum_limit` または `_momentum < momentum_limit` かつ `macdh < macdh_prev` 必須に変更し、リバウンド開始前の tail continuation を落とすこと。

Stop/TP は、1ATR固定stopをやめ、MR用に `sl = entry ±

## Audit Redesign Recommendation 抜粋

> 修正優先は trigger の `momentum_limit` 条件である。BUY は oversold 条件を維持しつつ、10バーmomentumが過度な下降継続ではないことを両側または逆側下限で確認する。SELL も同様に、過度な上昇継続を除外する。加点扱いの MACD-H/Stoch 反転は、score bonus ではなく最小限の必須反転確認に昇格させる候補がある。

# 1. 制約 (Rule R1)

- **No live promote** in this task. Shadow-stage 実装と BT 検証のみ。
- **Pre-reg LOCK** 必須: 仕様変更を `knowledge-base/wiki/decisions/` に記録してから実装。
- **365d BT 必須**: 現行版 vs proposed variant を A/B 比較。
- **WF folds >= 3, positive_ratio >= 0.67** で stable 確認。
- **Bonferroni-adjusted p < 0.05** または **Wilson lo current+0.05 以上** で有意性確認。
- **Kelly >= 0.40** が望ましい (lower bar OK if defensive narrowing)。

# 2. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/trend_rebound-redesign-2026-05-05.md` に:
- 現行設計の問題点 (audit Axis 引用)
- proposed variant の仕様 (具体コード差分)
- 評価軸 (BT 指標 + 合否基準)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_trend_rebound_redesign.py` に proposed variant の挙動テスト。

## Step 3: 実装

audit 推奨に従い変更。最小差分を優先。

## Step 4: テスト緑

## Step 5: 365d BT (現行 vs proposed)

`knowledge-base/raw/bt-results/trend_rebound-redesign-2026-05-05.json` に保存。

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
