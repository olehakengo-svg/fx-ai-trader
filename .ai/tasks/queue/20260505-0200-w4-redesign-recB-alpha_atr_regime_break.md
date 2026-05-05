---
id: 20260505-0200-w4-redesign-recB-alpha_atr_regime_break
title: "[W4-Redesign Rec=B] alpha_atr_regime_break (Tier 2 (Shadow)) — multi-axis redesign"
owner: codex
status: queued
priority: P2
created_at: 2026-05-05T02:00:00+0900
roadmap_gate: "W4-EDA Wave 4 Rec=B batch — multi-axis redesign (heavier than S/A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/alpha_atr_regime_break.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/alpha_atr_regime_break.md`) で **THESIS_VALID_DESIGN_BROKEN** / 推奨度 **B** (複数軸の再設計が必要) と判定。
S/A タスクより複雑なので別バッチで処理。

## Audit Axis 8 抜粋

> Tier 2 (Shadow) / phase0_shadow で、実質的には FORCE_DEMOTED 系の低発火戦略として扱う。破綻軸は Axis 3 と Axis 4、補助的に Axis 7。Axis 2 の trigger は thesis を捉えており、Axis 5 の R:R も momentum breakout と整合するため、「思想は正、設計が誤」仮説に乗る候補ではある。ただし現行設計は quiet CV 下位 25% AND ATR 1.5x surge AND body/range gate AND HTF hard block の AND 過多で、既存 365d target BT は 3 pair 合計 N=1 に潰れている。

再設計案は filter と timing の 2 点を先に直す。第一に HTF Hard Block を削除し、必要なら hard gate ではなく score feature に降格する。regime 転換の初動は既存 HTF 方向と逆に出ることがあり、ここを切ると HMM regime gate same-trap と同じ構造で edge tail を失う。第二に signal bar を closed bar に固定し、`ctx.df.iloc[-2]` を signal、次 bar `ctx.entry` を execution とする variant を作る。併せて `(symbol, strategy, signal, bar_id)` の dedup を strategy または dispatch 層に追加する。

## Audit Redesign Recommendation 抜粋

> 思想は明確で trigger の中核も正しいため、完全棄却ではない。ただし現行の発火率は低すぎ、HTF hard block が regime tail を切る構造リスクを持つため、まずは「ATR quiet→surge→closed-bar direction」だけを残す薄い baseline に戻すべき。具体的には `ctx.htf["agreement"]` による逆方向 return を削除し、`bar_body >= 0.10ATR` と `bar_range >= 0.8ATR` は片方ずつ ablation できる feature に分離する。

# 1. 制約 (Rule 1, B-tier complexity)

- **multi-axis 修正想定**: trigger / filter / timing / stop-TP の 2 軸以上
- **scope 制御必須**: 1 タスクで全部修正しようとせず、最も重要な 1-2 軸を選び他は別タスク化提案
- **Pre-reg LOCK** 必須
- **365d BT** + WF folds>=3 + Bonferroni
- Shadow stage のみ (Live promote = 別タスク)

# 2. Implementation Steps

## Step 1: Scope decision

audit Axis 8 を読み、本タスクで対応する 1-2 軸を選定。残りの軸は `knowledge-base/wiki/decisions/alpha_atr_regime_break-recB-deferred-axes-2026-05-05.md` に「次タスク候補」として記録。

## Step 2: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/alpha_atr_regime_break-redesign-recB-2026-05-05.md` に:
- 対応する軸の現行設計 vs proposed
- LOCK criteria

## Step 3: 失敗テスト追加

`tests/test_alpha_atr_regime_break_redesign_recB.py`

## Step 4: 実装 (選定軸のみ)

## Step 5: テスト緑

## Step 6: 365d BT 比較

`knowledge-base/raw/bt-results/alpha_atr_regime_break-redesign-recB-2026-05-05.json`

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
