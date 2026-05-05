---
id: 20260505-0227-w4-redesign-recB-vwap_mean_reversion
title: "[W4-Redesign Rec=B] vwap_mean_reversion (Tier 3 (FORCE_DEMOTED)) — multi-axis redesign"
owner: codex
status: queued
priority: P2
created_at: 2026-05-05T02:27:00+0900
roadmap_gate: "W4-EDA Wave 4 Rec=B batch — multi-axis redesign (heavier than S/A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/vwap_mean_reversion.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/vwap_mean_reversion.md`) で **THESIS_VALID_DESIGN_BROKEN** / 推奨度 **B** (複数軸の再設計が必要) と判定。
S/A タスクより複雑なので別バッチで処理。

## Audit Axis 8 抜粋

> `vwap_mean_reversion` は Tier 3 (FORCE_DEMOTED) なので failure mode 診断対象。破綻軸は Axis 3 / Axis 4 / Axis 5。Axis 2 の VWAP 2σ extension trigger は thesis と整合しているため、思想そのものは棄却しない。

最大の実害は Axis 3。停止コメントが示すとおり、同一 bar の multiple evaluate による連続発火と live 負 edge が既に発生している。次に Axis 4 の HTF Hard Block が、MR が取りたい counter-trend extension を削る。さらに Axis 5 で TP が VWAP mean ではなく ATR 固定になり、SL も 0.5ATR と狭いため、mean 到達前の noise で切られやすい。

再設計案は、trigger 本体は維持し、signal feature を確定済み bar のみで計算して next-bar / next-tick execution に固定すること。HTF hard direction block は削除し、代わりに ADX/slope を soft score または no-trade threshold として検証する。TP は VWAP、または VWAP までの距離が cost 未満なら entry 拒否に変更し、SL は 2σ 外側または recent swing + ATR buffer に置く。

## Audit Redesign Recommendation 抜粋

> Trigger は `_vmr_dev < -2σ -> BUY` / `_vmr_dev > +2σ -> SELL` のまま残す。これはコードから導ける thesis と整合しており、最初に直す対象ではない。

# 1. 制約 (Rule 1, B-tier complexity)

- **multi-axis 修正想定**: trigger / filter / timing / stop-TP の 2 軸以上
- **scope 制御必須**: 1 タスクで全部修正しようとせず、最も重要な 1-2 軸を選び他は別タスク化提案
- **Pre-reg LOCK** 必須
- **365d BT** + WF folds>=3 + Bonferroni
- Shadow stage のみ (Live promote = 別タスク)

# 2. Implementation Steps

## Step 1: Scope decision

audit Axis 8 を読み、本タスクで対応する 1-2 軸を選定。残りの軸は `knowledge-base/wiki/decisions/vwap_mean_reversion-recB-deferred-axes-2026-05-05.md` に「次タスク候補」として記録。

## Step 2: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/vwap_mean_reversion-redesign-recB-2026-05-05.md` に:
- 対応する軸の現行設計 vs proposed
- LOCK criteria

## Step 3: 失敗テスト追加

`tests/test_vwap_mean_reversion_redesign_recB.py`

## Step 4: 実装 (選定軸のみ)

## Step 5: テスト緑

## Step 6: 365d BT 比較

`knowledge-base/raw/bt-results/vwap_mean_reversion-redesign-recB-2026-05-05.json`

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
