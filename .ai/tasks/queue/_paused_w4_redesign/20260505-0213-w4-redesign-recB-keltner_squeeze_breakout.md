---
id: 20260505-0213-w4-redesign-recB-keltner_squeeze_breakout
title: "[W4-Redesign Rec=B] keltner_squeeze_breakout (Tier 2 (Shadow)) — multi-axis redesign"
owner: codex
status: queued
priority: P2
created_at: 2026-05-05T02:13:00+0900
roadmap_gate: "W4-EDA Wave 4 Rec=B batch — multi-axis redesign (heavier than S/A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/keltner_squeeze_breakout.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/keltner_squeeze_breakout.md`) で **THESIS_VALID_DESIGN_BROKEN** / 推奨度 **B** (複数軸の再設計が必要) と判定。
S/A タスクより複雑なので別バッチで処理。

## Audit Axis 8 抜粋

> Tier 2 (Shadow) で Tier 3/4 ではないが、metrics が `—` / N=0 で昇格判断不能なため failure mode を診断する。Axis 2 は破綻していない。思想は明確で、trigger は squeeze release breakout を直接捉えている。Axis 4 も、HTF hard block の same-trap リスクは残るが、現時点で thesis を破壊する MA-on-MR 型の明確な BREAKS ではない。

破綻は Axis 3 と Axis 5。Axis 3 は strategy 内で closed 1H bar と per-bar dedup を保証せず、現在足の `ctx.entry` / `ctx.df.iloc[-1]` に依存して emit する点。Axis 5 は breakout thesis に必要な BE/trailing がコメントと定数だけで、Candidate 返却値に接続されていない点。再設計案は、(1) signal 判定を確定済み 1H bar のみに固定し、同一 `(instrument, strategy, bar_time)` の再 emit を抑止する、(2) fixed TP を「初期 target + BE + trailing」に変更し、TP 到達前後の winner を trailing で伸ばせる geometry にする、の 2 点である。

## Audit Redesign Recommendation 抜粋

> Trigger の核は維持する。`_sq_count >= _min_sq`、`_curr_squeeze == False`、Keltner 80% break、body ratio、MACD-H 加速、ADX rising の条件は breakout thesis と整合しているため、ここを大きく変える必要はない。修正優先は timing で、`evaluate()` が未確定足で呼ばれる live 経路では `return None` にし、確定済み bar_time を使って同一 bar の `Candidate` 再発行を禁止する。BT でも close signal を同じ close で約定させていないかを既存 harness 側で確認する必要がある。

# 1. 制約 (Rule 1, B-tier complexity)

- **multi-axis 修正想定**: trigger / filter / timing / stop-TP の 2 軸以上
- **scope 制御必須**: 1 タスクで全部修正しようとせず、最も重要な 1-2 軸を選び他は別タスク化提案
- **Pre-reg LOCK** 必須
- **365d BT** + WF folds>=3 + Bonferroni
- Shadow stage のみ (Live promote = 別タスク)

# 2. Implementation Steps

## Step 1: Scope decision

audit Axis 8 を読み、本タスクで対応する 1-2 軸を選定。残りの軸は `knowledge-base/wiki/decisions/keltner_squeeze_breakout-recB-deferred-axes-2026-05-05.md` に「次タスク候補」として記録。

## Step 2: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/keltner_squeeze_breakout-redesign-recB-2026-05-05.md` に:
- 対応する軸の現行設計 vs proposed
- LOCK criteria

## Step 3: 失敗テスト追加

`tests/test_keltner_squeeze_breakout_redesign_recB.py`

## Step 4: 実装 (選定軸のみ)

## Step 5: テスト緑

## Step 6: 365d BT 比較

`knowledge-base/raw/bt-results/keltner_squeeze_breakout-redesign-recB-2026-05-05.json`

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
