---
id: 20260505-0226-w4-redesign-recB-vol_surge
title: "[W4-Redesign Rec=B] vol_surge (Tier 2 (Shadow)) — multi-axis redesign"
owner: codex
status: queued
priority: P2
created_at: 2026-05-05T02:26:00+0900
roadmap_gate: "W4-EDA Wave 4 Rec=B batch — multi-axis redesign (heavier than S/A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/vol_surge.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/vol_surge.md`) で **THESIS_VALID_DESIGN_BROKEN** / 推奨度 **B** (複数軸の再設計が必要) と判定。
S/A タスクより複雑なので別バッチで処理。

## Audit Axis 8 抜粋

> Tier 2 (Shadow) かつ SCALP_SENTINEL / pair-demoted 履歴を持つ underperforming strategy として診断する。Axis 2 は二系統とも thesis と trigger が整合し、Axis 4 も hard に thesis を壊す filter は見えない。破綻候補は Axis 3 と Axis 5。未確定足の volume/range surge、BB %B、足色、ADX/DI を同一 evaluate で見て Candidate を返すため、intrabar spike の chase と同一 bar 多重 entry のリスクが残る。さらに Climax MR 側は `TP=1.3ATR / SL=0.6ATR` で、mean reversion が戻る前に浅い stop で切られる geometry になっている。

再設計案は二系統を分離して、まず timing を bar-close 化する。`signal_bar = ctx.df.iloc[-2]` 相当の確定足で surge、BB %B、RSI、足色、ADX/DI/EMA を判定し、次 bar の `ctx.entry` でだけ emit する。`(symbol, self.name, mode, signal_bar_time)` の last-emitted guard を strategy または dispatch 層に追加する。Climax branch は stop を `1.0-1.3*ATR7` 程度へ広げ、TP は BB mid / VWAP / EMA21 など平均回帰先に寄せるか、少なくとも `TP ~= 1.0ATR, SL >= 1.0ATR` の MR geometry variant を比較する。Momentu

## Audit Redesign Recommendation 抜粋

> 思想は捨てない。volume/range surge は event detector として残し、Climax MR と Momentum を同じ score/geometry で扱わないように分離する。Trigger は概ね維持し、Climax は `surge AND bbpb extreme AND RSI extreme AND confirmed reversal candle` を確定足で判定、Momentum は `surge AND ADX/DI AND EMA9/21 alignment AND confirmed directional candle` を確定足で判定する。

# 1. 制約 (Rule 1, B-tier complexity)

- **multi-axis 修正想定**: trigger / filter / timing / stop-TP の 2 軸以上
- **scope 制御必須**: 1 タスクで全部修正しようとせず、最も重要な 1-2 軸を選び他は別タスク化提案
- **Pre-reg LOCK** 必須
- **365d BT** + WF folds>=3 + Bonferroni
- Shadow stage のみ (Live promote = 別タスク)

# 2. Implementation Steps

## Step 1: Scope decision

audit Axis 8 を読み、本タスクで対応する 1-2 軸を選定。残りの軸は `knowledge-base/wiki/decisions/vol_surge-recB-deferred-axes-2026-05-05.md` に「次タスク候補」として記録。

## Step 2: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/vol_surge-redesign-recB-2026-05-05.md` に:
- 対応する軸の現行設計 vs proposed
- LOCK criteria

## Step 3: 失敗テスト追加

`tests/test_vol_surge_redesign_recB.py`

## Step 4: 実装 (選定軸のみ)

## Step 5: テスト緑

## Step 6: 365d BT 比較

`knowledge-base/raw/bt-results/vol_surge-redesign-recB-2026-05-05.json`

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
