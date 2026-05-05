---
id: 20260505-0215-w4-redesign-recB-london_session_breakout
title: "[W4-Redesign Rec=B] london_session_breakout (Tier 2 (Shadow)) — multi-axis redesign"
owner: codex
status: queued
priority: P2
created_at: 2026-05-05T02:15:00+0900
roadmap_gate: "W4-EDA Wave 4 Rec=B batch — multi-axis redesign (heavier than S/A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/london_session_breakout.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/london_session_breakout.md`) で **THESIS_VALID_DESIGN_BROKEN** / 推奨度 **B** (複数軸の再設計が必要) と判定。
S/A タスクより複雑なので別バッチで処理。

## Audit Axis 8 抜粋

> Tier 2 (Shadow) だが、phase0_shadow かつ 365d BT EV `—` の under-evidenced cell なので failure mode を診断する。破綻軸は Axis 2、Axis 3、Axis 4、Axis 5。思想はコードから明確に導けるが、active path は hard disable により trigger/filter が全停止している。さらに停止理由コメント自体が、context fix 後の EUR WR=10% / JPY WR=0% として既存ロジックの実BT不良を示しているため、単純に `return None` を外すだけでは Shadow 復帰候補にできない。`strategies/daytrade/london_session_breakout.py:57`, `strategies/daytrade/london_session_breakout.py:58`, `strategies/daytrade/london_session_breakout.py:59`, `strategies/daytrade/london_session_breakout.py:60`

再設計案は、まず active disable を維持したまま dormant branch を v2 として分離し、EUR_USD / GBP_USD など非JPY London liquidity pair に限定して trigger/timing/exit を作り直すこと。Trigger は `07:00-08:00 UTC` の確定済み breakout bar close のみを採用し、`close > asia_high + max(spread, 0.1ATR)` / `close < asia_low - max

## Audit Redesign Recommendation 抜粋

> 思想は明確で、session breakout として再設計余地はある。ただし破綻は一箇所ではなく、active hard disable、bar-close/dedup、pair gating、exit geometry が同時に絡んでいるため、S/A ではなく B とする。

# 1. 制約 (Rule 1, B-tier complexity)

- **multi-axis 修正想定**: trigger / filter / timing / stop-TP の 2 軸以上
- **scope 制御必須**: 1 タスクで全部修正しようとせず、最も重要な 1-2 軸を選び他は別タスク化提案
- **Pre-reg LOCK** 必須
- **365d BT** + WF folds>=3 + Bonferroni
- Shadow stage のみ (Live promote = 別タスク)

# 2. Implementation Steps

## Step 1: Scope decision

audit Axis 8 を読み、本タスクで対応する 1-2 軸を選定。残りの軸は `knowledge-base/wiki/decisions/london_session_breakout-recB-deferred-axes-2026-05-05.md` に「次タスク候補」として記録。

## Step 2: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/london_session_breakout-redesign-recB-2026-05-05.md` に:
- 対応する軸の現行設計 vs proposed
- LOCK criteria

## Step 3: 失敗テスト追加

`tests/test_london_session_breakout_redesign_recB.py`

## Step 4: 実装 (選定軸のみ)

## Step 5: テスト緑

## Step 6: 365d BT 比較

`knowledge-base/raw/bt-results/london_session_breakout-redesign-recB-2026-05-05.json`

## Step 7: LOCK criteria 判定

PASS → shadow promote 提案 + 残り軸の次タスク提案
FAIL → REJECT + 原因分析

## Step 8: Codex adversarial review

# 3. Acceptance

- Scope decision 文書あり (どの軸を扱うか明示)
- Pre-reg LOCK doc あり
- 失敗テスト → 緑
- BT 比較レポートあり
- LOCK criteria 判定 (PASS / FAIL)
- 残り軸の deferred タスク提案あり

# 4. Out of Scope

- 全軸一括修正 (scope creep 防止)
- Live 昇格
- 他 strategies

# 5. Notes

- Rec=B は audit で「複数軸破綻」と判定された heavy case。1 タスクで完結しないことを最初から想定。
- 部分修正で BT が positive 改善を示せば成功。完全な edge restoration は次タスク以降で。
- post-hoc rationalization 厳禁: audit に書かれていない軸を勝手に追加しない。
