---
id: 20260505-0210-w4-redesign-recB-gold_pips
title: "[W4-Redesign Rec=B] gold_pips (Tier 2 (Shadow)) — multi-axis redesign"
owner: codex
status: queued
priority: P2
created_at: 2026-05-05T02:10:00+0900
roadmap_gate: "W4-EDA Wave 4 Rec=B batch — multi-axis redesign (heavier than S/A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/gold_pips.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/gold_pips.md`) で **THESIS_VALID_DESIGN_BROKEN** / 推奨度 **B** (複数軸の再設計が必要) と判定。
S/A タスクより複雑なので別バッチで処理。

## Audit Axis 8 抜粋

> Tier 3/4 ではなく Tier 2 Shadow で、metrics 劣化を判定できる既存数値もない。ただし設計上の破綻候補は Axis 3 と Axis 5 に集中する。Trigger/filter は momentum thesis と概ね整合している一方、現在足の body/high/low を未確定のまま使える構造と per-bar dedup 欠落が、1m XAU の高ボラ局面で signal の多重発火や chase entry を起こしうる。さらに fixed TP=1.8ATR に対し、stop は包み足全体の high/low 依存で R:R が保証されない。

再設計案は、まず signal bar を確定足に固定し、`df.iloc[-2]` で body/engulfing/high/low を計算して次 bar の `ctx.entry` で約定する variant に切ること。加えて `(ctx.symbol, signal, bar_id)` の per-bar dedup を入れ、同一 1m bar では一度しか emit しない。Stop/TP は `risk = abs(entry - sl)` を計算して `tp_distance >= 1.5*risk` を満たさない場合は skip、または TP を `max(1.8ATR, 1.5*risk)` に引き上げる。

## Audit Redesign Recommendation 抜粋

> 思想は維持する。変更対象は trigger の大枠ではなく、timing と stop/TP geometry。最小 redesign は、包み足判定を未確定の `ctx.entry - ctx.open_price` から確定足ベースへ移し、`signal_bar = ctx.df.iloc[-2]`、`prev_bar = ctx.df.iloc[-3]` で body engulfing と signal high/low を計算する。Execution は次 bar の `ctx.entry` に限定し、同一 `(symbol, signal, signal_bar_time)` の再発火を拒否する。

# 1. 制約 (Rule 1, B-tier complexity)

- **multi-axis 修正想定**: trigger / filter / timing / stop-TP の 2 軸以上
- **scope 制御必須**: 1 タスクで全部修正しようとせず、最も重要な 1-2 軸を選び他は別タスク化提案
- **Pre-reg LOCK** 必須
- **365d BT** + WF folds>=3 + Bonferroni
- Shadow stage のみ (Live promote = 別タスク)

# 2. Implementation Steps

## Step 1: Scope decision

audit Axis 8 を読み、本タスクで対応する 1-2 軸を選定。残りの軸は `knowledge-base/wiki/decisions/gold_pips-recB-deferred-axes-2026-05-05.md` に「次タスク候補」として記録。

## Step 2: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/gold_pips-redesign-recB-2026-05-05.md` に:
- 対応する軸の現行設計 vs proposed
- LOCK criteria

## Step 3: 失敗テスト追加

`tests/test_gold_pips_redesign_recB.py`

## Step 4: 実装 (選定軸のみ)

## Step 5: テスト緑

## Step 6: 365d BT 比較

`knowledge-base/raw/bt-results/gold_pips-redesign-recB-2026-05-05.json`

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
