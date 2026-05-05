---
id: 20260505-0214-w4-redesign-recB-london_breakout
title: "[W4-Redesign Rec=B] london_breakout (Tier 2 (Shadow)) — multi-axis redesign"
owner: codex
status: queued
priority: P2
created_at: 2026-05-05T02:14:00+0900
roadmap_gate: "W4-EDA Wave 4 Rec=B batch — multi-axis redesign (heavier than S/A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/london_breakout.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/london_breakout.md`) で **THESIS_VALID_DESIGN_BROKEN** / 推奨度 **B** (複数軸の再設計が必要) と判定。
S/A タスクより複雑なので別バッチで処理。

## Audit Axis 8 抜粋

> Tier 2 (Shadow) だが、tier-master の 365d BT EV が `—` で昇格根拠がなく、関連 C-1 GBP_JPY 12yr primary も Wilson lo/PF/Bonferroni/Sharpe が不合格なので failure mode 診断を適用する。破綻軸は Axis 2、Axis 3、Axis 5。思想は「London open における Asia range breakout」で明確だが、現コードは Asia session 固定窓ではなく rolling 120 bars を使い、確定bar/entry timing/dedup の契約も strategy 内にない。さらに fixed TP/SL のみで breakout continuation を伸ばす exit geometry になっていない。

再設計案は、まず trigger/timing を同時に閉じること。`asia_high/asia_low` は `00:00-06:59 UTC` などの prior session fixed window から確定済みbarだけで計算し、entry は `last_closed_close > asia_high + buffer` / `< asia_low - buffer` の bar-close trigger にする。`buffer = max(0.1ATR, spread)` とし、同一 pair/date/session で1回だけ発火する dedup key を実行層または strategy state に置く。

## Audit Redesign Recommendation 抜粋

> Trigger は rolling range から fixed Asia session range へ変える。コードレベルでは `ctx.df.iloc[-self.asia_bars:]` をやめ、UTC timestamp index から London 当日の `00:00 <= t < 07:00` または broker定義の Asia window を切り出す。判定は current/intrabar `ctx.entry` ではなく、確定済み signal bar の close が `asia_high + buffer` / `asia_low - buffer` を超えた時だけに寄せる。

# 1. 制約 (Rule 1, B-tier complexity)

- **multi-axis 修正想定**: trigger / filter / timing / stop-TP の 2 軸以上
- **scope 制御必須**: 1 タスクで全部修正しようとせず、最も重要な 1-2 軸を選び他は別タスク化提案
- **Pre-reg LOCK** 必須
- **365d BT** + WF folds>=3 + Bonferroni
- Shadow stage のみ (Live promote = 別タスク)

# 2. Implementation Steps

## Step 1: Scope decision

audit Axis 8 を読み、本タスクで対応する 1-2 軸を選定。残りの軸は `knowledge-base/wiki/decisions/london_breakout-recB-deferred-axes-2026-05-05.md` に「次タスク候補」として記録。

## Step 2: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/london_breakout-redesign-recB-2026-05-05.md` に:
- 対応する軸の現行設計 vs proposed
- LOCK criteria

## Step 3: 失敗テスト追加

`tests/test_london_breakout_redesign_recB.py`

## Step 4: 実装 (選定軸のみ)

## Step 5: テスト緑

## Step 6: 365d BT 比較

`knowledge-base/raw/bt-results/london_breakout-redesign-recB-2026-05-05.json`

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
