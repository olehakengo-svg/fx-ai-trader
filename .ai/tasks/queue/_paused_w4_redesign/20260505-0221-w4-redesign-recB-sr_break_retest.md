---
id: 20260505-0221-w4-redesign-recB-sr_break_retest
title: "[W4-Redesign Rec=B] sr_break_retest (Tier 3 (FORCE_DEMOTED)) — multi-axis redesign"
owner: codex
status: queued
priority: P2
created_at: 2026-05-05T02:21:00+0900
roadmap_gate: "W4-EDA Wave 4 Rec=B batch — multi-axis redesign (heavier than S/A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/sr_break_retest.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/sr_break_retest.md`) で **THESIS_VALID_DESIGN_BROKEN** / 推奨度 **B** (複数軸の再設計が必要) と判定。
S/A タスクより複雑なので別バッチで処理。

## Audit Axis 8 抜粋

> Tier 3 (FORCE_DEMOTED) なので failure mode 診断を適用する。破綻軸は主に Axis 3 と Axis 5、補助的に Axis 6。Axis 2 の trigger は SR breakout → retest → bounce を数学的に捕捉しており、Axis 4 の ADX/HTF/EMA filter も breakout continuation thesis を壊していない。一方で、retest/bounce を current bar の `ctx.entry` と `ctx.open_price` で判定するため、bar-close contract と dedup がない運用では未確定 bar 反転を拾う。さらに breakout continuation の利幅を伸ばす trailing がなく、固定 2ATR / 1.5R TP と SR 裏 0.3ATR SL に閉じている。

再設計案は、trigger の思想を維持しつつ timing と exit を変える。まず retest 反転確認を current tick から確定済み signal bar へ移し、`signal_bar = ctx.df.iloc[-2]` の `Close > Open`, `Close > SR`, `Close > EMA9` を BUY 条件、SELL は対称にする。`ctx.entry` は次 bar execution price としてのみ使い、Candidate または dispatch layer に `(symbol, entry_type, side, signal_bar_time, sr_level_bucket)` の dedup key を渡す。次に TP を fixed 2ATR から、初期 `1R` 到

## Audit Redesign Recommendation 抜粋

> 思想は有効候補として残す。SR breakout 後の retest continuation はコードから明確に導出でき、trigger/filter の中心部も thesis に沿っているため、`THESIS_INVALID` ではない。ただし FORCE_DEMOTED かつ既存 audit DB は negative partial evidence を示し、bar-close/dedup と exit geometry の 2 軸を直さない限り Shadow 復帰は弱い。

# 1. 制約 (Rule 1, B-tier complexity)

- **multi-axis 修正想定**: trigger / filter / timing / stop-TP の 2 軸以上
- **scope 制御必須**: 1 タスクで全部修正しようとせず、最も重要な 1-2 軸を選び他は別タスク化提案
- **Pre-reg LOCK** 必須
- **365d BT** + WF folds>=3 + Bonferroni
- Shadow stage のみ (Live promote = 別タスク)

# 2. Implementation Steps

## Step 1: Scope decision

audit Axis 8 を読み、本タスクで対応する 1-2 軸を選定。残りの軸は `knowledge-base/wiki/decisions/sr_break_retest-recB-deferred-axes-2026-05-05.md` に「次タスク候補」として記録。

## Step 2: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/sr_break_retest-redesign-recB-2026-05-05.md` に:
- 対応する軸の現行設計 vs proposed
- LOCK criteria

## Step 3: 失敗テスト追加

`tests/test_sr_break_retest_redesign_recB.py`

## Step 4: 実装 (選定軸のみ)

## Step 5: テスト緑

## Step 6: 365d BT 比較

`knowledge-base/raw/bt-results/sr_break_retest-redesign-recB-2026-05-05.json`

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
