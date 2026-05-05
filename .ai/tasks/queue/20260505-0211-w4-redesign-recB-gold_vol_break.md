---
id: 20260505-0211-w4-redesign-recB-gold_vol_break
title: "[W4-Redesign Rec=B] gold_vol_break (Tier 2 (Shadow)) — multi-axis redesign"
owner: codex
status: queued
priority: P2
created_at: 2026-05-05T02:11:00+0900
roadmap_gate: "W4-EDA Wave 4 Rec=B batch — multi-axis redesign (heavier than S/A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/gold_vol_break.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/gold_vol_break.md`) で **THESIS_VALID_DESIGN_BROKEN** / 推奨度 **B** (複数軸の再設計が必要) と判定。
S/A タスクより複雑なので別バッチで処理。

## Audit Axis 8 抜粋

> Tier 3/4 ではなく Tier 2 Shadow だが、既存資料上は XAU production-excluded かつ promotion-grade empirical evidence がない。設計破綻候補は Axis 3 と Axis 5。Axis 2/4 は thesis と整合しており、MR に MA filter を足す型や HMM hard gate で regime tail を消す型ではない。一方、current context の未確定 15m 足で BB 突破・body・DI を評価でき、strategy 内に per-bar dedup がないため、bar-close 前提が崩れると一時的な spike を複数回 chase する。さらに breakout thesis に対して固定 3ATR TP / 1ATR SL は、XAU の retest と trend continuation の両方に中途半端で、伸びる局面を capped にし、初動 wick で切られやすい。

再設計案は timing と geometry の 2 点。Trigger は思想に合っているので維持し、`signal_bar = ctx.df.iloc[-2]` の確定足 close で BB(2.5σ) breakout、ATR surge、ADX/DI、body を評価する。Execution は次 bar の `ctx.entry` に限定し、`(symbol, strategy, signal_bar_time)` dedup を追加する。Stop/TP は fixed 3ATR/1ATR から、初期 SL を signal bar の反対側 wick または `1.2*ATR7` の広い方に置き、1R 到達後は ATR trailing に移行する 

## Audit Redesign Recommendation 抜粋

> 思想は維持する。最小変更は、未確定足依存を外して bar-close signal に固定すること。BUY は `signal_close > bb_upper_25_signal AND signal_close > signal_open AND +DI_signal > -DI_signal AND ATR7_signal > ATR14_signal*1.05`、SELL は対称条件にし、signal bar の次 bar でだけ Candidate を emit する。同一 `signal_bar_time` からの再 emit は拒否する。

# 1. 制約 (Rule 1, B-tier complexity)

- **multi-axis 修正想定**: trigger / filter / timing / stop-TP の 2 軸以上
- **scope 制御必須**: 1 タスクで全部修正しようとせず、最も重要な 1-2 軸を選び他は別タスク化提案
- **Pre-reg LOCK** 必須
- **365d BT** + WF folds>=3 + Bonferroni
- Shadow stage のみ (Live promote = 別タスク)

# 2. Implementation Steps

## Step 1: Scope decision

audit Axis 8 を読み、本タスクで対応する 1-2 軸を選定。残りの軸は `knowledge-base/wiki/decisions/gold_vol_break-recB-deferred-axes-2026-05-05.md` に「次タスク候補」として記録。

## Step 2: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/gold_vol_break-redesign-recB-2026-05-05.md` に:
- 対応する軸の現行設計 vs proposed
- LOCK criteria

## Step 3: 失敗テスト追加

`tests/test_gold_vol_break_redesign_recB.py`

## Step 4: 実装 (選定軸のみ)

## Step 5: テスト緑

## Step 6: 365d BT 比較

`knowledge-base/raw/bt-results/gold_vol_break-redesign-recB-2026-05-05.json`

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
