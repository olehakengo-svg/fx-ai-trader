---
id: 20260505-0219-w4-redesign-recB-ofi_mr
title: "[W4-Redesign Rec=B] ofi_mr (Tier 2 (Shadow)) — multi-axis redesign"
owner: codex
status: queued
priority: P2
created_at: 2026-05-05T02:19:00+0900
roadmap_gate: "W4-EDA Wave 4 Rec=B batch — multi-axis redesign (heavier than S/A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/ofi_mr.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/ofi_mr.md`) で **THESIS_VALID_DESIGN_BROKEN** / 推奨度 **B** (複数軸の再設計が必要) と判定。
S/A タスクより複雑なので別バッチで処理。

## Audit Axis 8 抜粋

> `ofi_mr` は Tier 2 (Shadow) / phase0_shadow で、tier-master 由来の 365d BT EV は欠落している。設計破綻の主軸は Axis 3 と Axis 5。Axis 2 の OFI 極端値 + VWAP 乖離 + fade trigger は thesis と整合しており、Axis 4 も trend hard block を持たないため壊していない。

再設計案は、まず timing を closed-bar / next-bar execution に固定すること。`current_window` と VWAP 計算を signal 判定用には `bars[-W-1:-1]` へずらし、entry reference は `bars[-1].close` ではなく次 tick/次 bar の約定として扱う。次に stop/TP を MR geometry に戻し、TP は原則 `vwap` まで、`min_tp_pips` で VWAP を越える場合は entry を拒否する。R:R gate は固定 `0.7` ではなく、cost-adjusted expected reversion distance と Wilson/PF 検証に移すべき。

## Audit Redesign Recommendation 抜粋

> Trigger の骨格は維持する。`abs(z_ofi) >= z_thresh` と `displacement` 同方向確認は、OFI 過剰偏りが価格に反映された後に fade するという thesis を直接表しているため、最初に壊すべき箇所ではない。

# 1. 制約 (Rule 1, B-tier complexity)

- **multi-axis 修正想定**: trigger / filter / timing / stop-TP の 2 軸以上
- **scope 制御必須**: 1 タスクで全部修正しようとせず、最も重要な 1-2 軸を選び他は別タスク化提案
- **Pre-reg LOCK** 必須
- **365d BT** + WF folds>=3 + Bonferroni
- Shadow stage のみ (Live promote = 別タスク)

# 2. Implementation Steps

## Step 1: Scope decision

audit Axis 8 を読み、本タスクで対応する 1-2 軸を選定。残りの軸は `knowledge-base/wiki/decisions/ofi_mr-recB-deferred-axes-2026-05-05.md` に「次タスク候補」として記録。

## Step 2: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/ofi_mr-redesign-recB-2026-05-05.md` に:
- 対応する軸の現行設計 vs proposed
- LOCK criteria

## Step 3: 失敗テスト追加

`tests/test_ofi_mr_redesign_recB.py`

## Step 4: 実装 (選定軸のみ)

## Step 5: テスト緑

## Step 6: 365d BT 比較

`knowledge-base/raw/bt-results/ofi_mr-redesign-recB-2026-05-05.json`

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
