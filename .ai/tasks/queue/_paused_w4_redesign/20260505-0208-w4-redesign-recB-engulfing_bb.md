---
id: 20260505-0208-w4-redesign-recB-engulfing_bb
title: "[W4-Redesign Rec=B] engulfing_bb (Tier 3 (FORCE_DEMOTED)) — multi-axis redesign"
owner: codex
status: queued
priority: P2
created_at: 2026-05-05T02:08:00+0900
roadmap_gate: "W4-EDA Wave 4 Rec=B batch — multi-axis redesign (heavier than S/A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/engulfing_bb.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/engulfing_bb.md`) で **THESIS_VALID_DESIGN_BROKEN** / 推奨度 **B** (複数軸の再設計が必要) と判定。
S/A タスクより複雑なので別バッチで処理。

## Audit Axis 8 抜粋

> Tier 3 (FORCE_DEMOTED) なので failure mode 診断対象。破綻軸は主に Axis 3 と Axis 5、補助的に Axis 6。Axis 2 の BB%B + RSI5 + 包み足 trigger は MR thesis と方向としては整合するが、すべて現在足依存で signal と execution が分離されていない。さらに `1.5ATR` TP / 実効 `0.95ATR+` SL は、shallow BB/RSI extension の scalp MR に対して必要勝率と摩擦負担を上げる。

再設計案は、まず timing を closed-bar 化すること。`df.iloc[-2]` を signal bar とし、包み足判定、BB%B、RSI5、Stoch K/D、High/Low range をすべて確定足から読む。entry は次 bar execution に分離し、`(engulfing_bb, instrument, signal, signal_bar_time)` dedup を strategy または dispatcher 層で必須にする。

次に trigger と geometry を MR 向けに寄せる。BUY は概念的に `prev1_bbpb < 0.15 AND prev1_rsi5 < 35 AND bullish_engulfing_closed`、SELL は `prev1_bbpb > 0.85 AND prev1_rsi5 > 65 AND bearish_engulfing_closed` へ狭め、current-bar body pattern の偶発発火を減らす。SL は candle low/high 依存の可変幅を明示的に制限し、TP は `1.0-1.2ATR` または 

## Audit Redesign Recommendation 抜粋

> 思想は維持候補。BB extreme + RSI extension + reversal candle という MR thesis はコードから明確に導出でき、MA/HMM 型の破壊的 filter は見えない。ただし復活には timing closed-bar 化、trigger 閾値の再設計、stop/TP geometry の再設計、pair scope 分離の複数軸修正が必要なので `B` とする。

# 1. 制約 (Rule 1, B-tier complexity)

- **multi-axis 修正想定**: trigger / filter / timing / stop-TP の 2 軸以上
- **scope 制御必須**: 1 タスクで全部修正しようとせず、最も重要な 1-2 軸を選び他は別タスク化提案
- **Pre-reg LOCK** 必須
- **365d BT** + WF folds>=3 + Bonferroni
- Shadow stage のみ (Live promote = 別タスク)

# 2. Implementation Steps

## Step 1: Scope decision

audit Axis 8 を読み、本タスクで対応する 1-2 軸を選定。残りの軸は `knowledge-base/wiki/decisions/engulfing_bb-recB-deferred-axes-2026-05-05.md` に「次タスク候補」として記録。

## Step 2: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/engulfing_bb-redesign-recB-2026-05-05.md` に:
- 対応する軸の現行設計 vs proposed
- LOCK criteria

## Step 3: 失敗テスト追加

`tests/test_engulfing_bb_redesign_recB.py`

## Step 4: 実装 (選定軸のみ)

## Step 5: テスト緑

## Step 6: 365d BT 比較

`knowledge-base/raw/bt-results/engulfing_bb-redesign-recB-2026-05-05.json`

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
