---
id: 20260505-0201-w4-redesign-recB-alpha_wick_imbalance
title: "[W4-Redesign Rec=B] alpha_wick_imbalance (Tier 2 (Shadow)) — multi-axis redesign"
owner: codex
status: queued
priority: P2
created_at: 2026-05-05T02:01:00+0900
roadmap_gate: "W4-EDA Wave 4 Rec=B batch — multi-axis redesign (heavier than S/A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/alpha_wick_imbalance.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/alpha_wick_imbalance.md`) で **THESIS_VALID_DESIGN_BROKEN** / 推奨度 **B** (複数軸の再設計が必要) と判定。
S/A タスクより複雑なので別バッチで処理。

## Audit Axis 8 抜粋

> Tier 2 (Shadow) / phase0_shadow で、入力 metric は 365d BT EV `—`。Tier 3/4 専用の復活診断ではないが、underperforming / evidence 欠落の shadow cell として failure mode を診断する。破綻軸は Axis 4 が主、Axis 3 と Axis 5 が副。Axis 2 の WIR trigger は thesis と合っているため維持候補だが、HTF Hard Block が MR の trend-tail reversal を切り、現在足 close 依存の timing と bar dedup 外部依存が live/shadow 記録を汚しうる。さらに MR に対して `TP > SL` の momentum-like geometry が mean-reversion の戻り幅と噛み合っていない。

再設計案は、HTF Hard Block を削除または soft penalty 化し、confirmation bar を closed bar に固定することを第一候補にする。コードレベルでは confirmation を `confirm = df.iloc[-2]` に移し、WIR lookback をその直前 window 本にずらして、entry は次足 `ctx.entry` に限定する variant を作る。Stop/TP は `SL=2.0ATR` 程度、`TP=1.0-1.3ATR` または wick imbalance の平均回帰 target に寄せ、現行の `TP > SL` geometry と比較する。本監査では新規 BT は実行しない。

## Audit Redesign Recommendation 抜粋

> Trigger は維持する。`WIR` はヒゲ偏りを直接数量化しており、`current_body` の反転方向確認も MR thesis と整合しているため、最初に壊すべき箇所ではない。

# 1. 制約 (Rule 1, B-tier complexity)

- **multi-axis 修正想定**: trigger / filter / timing / stop-TP の 2 軸以上
- **scope 制御必須**: 1 タスクで全部修正しようとせず、最も重要な 1-2 軸を選び他は別タスク化提案
- **Pre-reg LOCK** 必須
- **365d BT** + WF folds>=3 + Bonferroni
- Shadow stage のみ (Live promote = 別タスク)

# 2. Implementation Steps

## Step 1: Scope decision

audit Axis 8 を読み、本タスクで対応する 1-2 軸を選定。残りの軸は `knowledge-base/wiki/decisions/alpha_wick_imbalance-recB-deferred-axes-2026-05-05.md` に「次タスク候補」として記録。

## Step 2: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/alpha_wick_imbalance-redesign-recB-2026-05-05.md` に:
- 対応する軸の現行設計 vs proposed
- LOCK criteria

## Step 3: 失敗テスト追加

`tests/test_alpha_wick_imbalance_redesign_recB.py`

## Step 4: 実装 (選定軸のみ)

## Step 5: テスト緑

## Step 6: 365d BT 比較

`knowledge-base/raw/bt-results/alpha_wick_imbalance-redesign-recB-2026-05-05.json`

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
