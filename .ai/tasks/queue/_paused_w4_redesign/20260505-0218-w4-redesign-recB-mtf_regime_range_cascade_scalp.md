---
id: 20260505-0218-w4-redesign-recB-mtf_regime_range_cascade_scalp
title: "[W4-Redesign Rec=B] mtf_regime_range_cascade_scalp (Tier 4 (SCALP_SENTINEL)) — multi-axis redesign"
owner: codex
status: queued
priority: P2
created_at: 2026-05-05T02:18:00+0900
roadmap_gate: "W4-EDA Wave 4 Rec=B batch — multi-axis redesign (heavier than S/A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/mtf_regime_range_cascade_scalp.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/mtf_regime_range_cascade_scalp.md`) で **THESIS_VALID_DESIGN_BROKEN** / 推奨度 **B** (複数軸の再設計が必要) と判定。
S/A タスクより複雑なので別バッチで処理。

## Audit Axis 8 抜粋

> Tier 4 (SCALP_SENTINEL) なので failure mode 診断対象。破綻軸は Axis 3 と Axis 4、補助的に Axis 2 の trigger 選択。Axis 2 は数式上は MR と整合するが、実際には `bb_rsi_reversion` 継承 trigger を range_tight に重ねた設計が既存ラベル実測で否定方向になっている。Axis 3 は現在足依存かつ dedup 欠落で、scalp の intrabar 再発火リスクが残る。Axis 4 は `REGIME_RANGE` hard gate が、コードコメント上すでに負けと記録された range_tight MR tail へ entry を固定している点が主破綻。

再設計案は、range hard gate をそのまま残して 1m bb_rsi trigger だけを薄く調整するのではなく、range edge を「レンジ端の reclaim」に再定義すること。具体的には BUY を `closed signal bar low <= m5_swing_low or bb_lower breach` かつ `closed back inside band` かつ `RSI5 recross 30 or Stoch K cross D`、SELL を対称条件にする。signal は `df.iloc[-2]` の確定足で判定し、entry は次 bar に分離し、`(symbol, strategy, signal, signal_bar_time)` dedup を必須にする。

Filter は `classify_15m == REGIME_RANGE` の単一 hard gateを廃止または分解し、少なくとも range_tight / range_wide

## Audit Redesign Recommendation 抜粋

> 思想は完全棄却ではなく、レンジ端の exhaustion から平均回帰を取る仮説としては再設計候補に残す。ただし現在の設計は、既に負けが観測された range_tight × inherited bb_rsi trigger へ hard gate で固定しており、未確定足依存も残る。単一行削除では足りず、trigger と timing と regime filter をまとめて直す必要がある。

# 1. 制約 (Rule 1, B-tier complexity)

- **multi-axis 修正想定**: trigger / filter / timing / stop-TP の 2 軸以上
- **scope 制御必須**: 1 タスクで全部修正しようとせず、最も重要な 1-2 軸を選び他は別タスク化提案
- **Pre-reg LOCK** 必須
- **365d BT** + WF folds>=3 + Bonferroni
- Shadow stage のみ (Live promote = 別タスク)

# 2. Implementation Steps

## Step 1: Scope decision

audit Axis 8 を読み、本タスクで対応する 1-2 軸を選定。残りの軸は `knowledge-base/wiki/decisions/mtf_regime_range_cascade_scalp-recB-deferred-axes-2026-05-05.md` に「次タスク候補」として記録。

## Step 2: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/mtf_regime_range_cascade_scalp-redesign-recB-2026-05-05.md` に:
- 対応する軸の現行設計 vs proposed
- LOCK criteria

## Step 3: 失敗テスト追加

`tests/test_mtf_regime_range_cascade_scalp_redesign_recB.py`

## Step 4: 実装 (選定軸のみ)

## Step 5: テスト緑

## Step 6: 365d BT 比較

`knowledge-base/raw/bt-results/mtf_regime_range_cascade_scalp-redesign-recB-2026-05-05.json`

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
