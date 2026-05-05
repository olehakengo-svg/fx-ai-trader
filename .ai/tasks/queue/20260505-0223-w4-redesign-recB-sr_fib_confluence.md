---
id: 20260505-0223-w4-redesign-recB-sr_fib_confluence
title: "[W4-Redesign Rec=B] sr_fib_confluence (Tier 3 (FORCE_DEMOTED)) — multi-axis redesign"
owner: codex
status: queued
priority: P2
created_at: 2026-05-05T02:23:00+0900
roadmap_gate: "W4-EDA Wave 4 Rec=B batch — multi-axis redesign (heavier than S/A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/sr_fib_confluence.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/sr_fib_confluence.md`) で **THESIS_VALID_DESIGN_BROKEN** / 推奨度 **B** (複数軸の再設計が必要) と判定。
S/A タスクより複雑なので別バッチで処理。

## Audit Axis 8 抜粋

> Tier 3 (FORCE_DEMOTED) なので failure mode 診断を適用する。破綻軸は Axis 2、Axis 3、Axis 4、補助的に Axis 6。Axis 5 の 2:1 前後の geometry は trend-aligned thesis と大きく矛盾しないが、trigger が SR/Fib/OB の数値条件ではなく上流 reason の文字列パースで、closed-bar / dedup の契約も strategy 内に存在しない。過去 audit にある「理由文字列パースに依存（実装の構造的欠陥）」という評価とも一致する。

再設計案は、思想を維持して trigger と timing を作り直すこと。`dt_reasons` 文字列ではなく、上流 DT layer から `fib_level`, `sr_level`, `ob_zone_low/high`, `confluence_type`, `signal_bar_time` のような構造化 feature を `ctx.layer3` に渡し、この file では `abs(ctx.entry - fib_level) <= 0.35*ATR` または `ob_zone_low <= entry <= ob_zone_high` を hard gate にする。さらに EMA direction は残しつつ、signal 判定を確定済み bar に固定し、execution は次 bar の `ctx.entry` に分離する。dedup key は `(sr_fib_confluence, symbol, signal, signal_bar_time, confluence_type)` が最低限必要。

## Audit Redesign Recommendation 抜粋

> 思想は棄却しない。SR/Fib/OB confluence を trend direction に乗せる仮説はコードから導出でき、ADX/EMA と 2:1 geometry も大枠では thesis に沿っている。一方で、edge の中核である confluence 判定が文字列 reason による proxy で、bar-close / dedup contract も file 内にないため、単一 filter 削除では復活しない。

# 1. 制約 (Rule 1, B-tier complexity)

- **multi-axis 修正想定**: trigger / filter / timing / stop-TP の 2 軸以上
- **scope 制御必須**: 1 タスクで全部修正しようとせず、最も重要な 1-2 軸を選び他は別タスク化提案
- **Pre-reg LOCK** 必須
- **365d BT** + WF folds>=3 + Bonferroni
- Shadow stage のみ (Live promote = 別タスク)

# 2. Implementation Steps

## Step 1: Scope decision

audit Axis 8 を読み、本タスクで対応する 1-2 軸を選定。残りの軸は `knowledge-base/wiki/decisions/sr_fib_confluence-recB-deferred-axes-2026-05-05.md` に「次タスク候補」として記録。

## Step 2: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/sr_fib_confluence-redesign-recB-2026-05-05.md` に:
- 対応する軸の現行設計 vs proposed
- LOCK criteria

## Step 3: 失敗テスト追加

`tests/test_sr_fib_confluence_redesign_recB.py`

## Step 4: 実装 (選定軸のみ)

## Step 5: テスト緑

## Step 6: 365d BT 比較

`knowledge-base/raw/bt-results/sr_fib_confluence-redesign-recB-2026-05-05.json`

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
