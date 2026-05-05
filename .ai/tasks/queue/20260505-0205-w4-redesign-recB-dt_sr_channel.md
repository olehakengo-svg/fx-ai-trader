---
id: 20260505-0205-w4-redesign-recB-dt_sr_channel
title: "[W4-Redesign Rec=B] dt_sr_channel (Tier 2 (Shadow)) — multi-axis redesign"
owner: codex
status: queued
priority: P2
created_at: 2026-05-05T02:05:00+0900
roadmap_gate: "W4-EDA Wave 4 Rec=B batch — multi-axis redesign (heavier than S/A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/dt_sr_channel.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/dt_sr_channel.md`) で **THESIS_VALID_DESIGN_BROKEN** / 推奨度 **B** (複数軸の再設計が必要) と判定。
S/A タスクより複雑なので別バッチで処理。

## Audit Axis 8 抜粋

> Tier 2 (Shadow) だが phase0_shadow / ALL で tier-master 365d BT EV は `—`、May 3 gate progression は PF=0.854 / raw Kelly=-0.0856、Apr 28 negative-edge audit では by-strategy PF=0.30 なので underperforming として failure mode 診断を適用する。

破綻軸は Axis 3 と Axis 5、補助的に Axis 6。Trigger は SR/channel 端 + RSI/MACD 反転で MR thesis と整合するが、closed-bar 化と per-bar dedup が戦略内にないため signal timing が実行層依存になっている。さらに stop/TP が 1ATR stop / 2ATR target の trend-follow 型 geometry で、SR/channel MR の「境界外まで耐えて mean 側へ戻る」構造と噛み合っていない。ALL scope も USD_JPY 以外の negative pockets を混ぜている。

再設計案は、まず closed-bar signal に固定し、`signal_bar = ctx.df.iloc[-2]` 相当の確定足で SR/channel proximity、RSI、MACDH turn を判定して次足 `ctx.entry` で候補化すること。併せて `(instrument, entry_type, signal_bar_time, direction)` の dedup を dispatch か strategy state に置く。次に geometry を MR 型へ寄せ、SL は s

## Audit Redesign Recommendation 抜粋

> 思想は有効候補として残す。SR/channel 端での反発を RSI/MACD 反転で拾う thesis はコードから明確に導出でき、trigger 自体も大枠では MR と整合している。一方で、現在の実装は signal timing と stop/TP geometry が MR 用に固定されておらず、ALL scope で負の pair/session を混ぜている。

# 1. 制約 (Rule 1, B-tier complexity)

- **multi-axis 修正想定**: trigger / filter / timing / stop-TP の 2 軸以上
- **scope 制御必須**: 1 タスクで全部修正しようとせず、最も重要な 1-2 軸を選び他は別タスク化提案
- **Pre-reg LOCK** 必須
- **365d BT** + WF folds>=3 + Bonferroni
- Shadow stage のみ (Live promote = 別タスク)

# 2. Implementation Steps

## Step 1: Scope decision

audit Axis 8 を読み、本タスクで対応する 1-2 軸を選定。残りの軸は `knowledge-base/wiki/decisions/dt_sr_channel-recB-deferred-axes-2026-05-05.md` に「次タスク候補」として記録。

## Step 2: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/dt_sr_channel-redesign-recB-2026-05-05.md` に:
- 対応する軸の現行設計 vs proposed
- LOCK criteria

## Step 3: 失敗テスト追加

`tests/test_dt_sr_channel_redesign_recB.py`

## Step 4: 実装 (選定軸のみ)

## Step 5: テスト緑

## Step 6: 365d BT 比較

`knowledge-base/raw/bt-results/dt_sr_channel-redesign-recB-2026-05-05.json`

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
