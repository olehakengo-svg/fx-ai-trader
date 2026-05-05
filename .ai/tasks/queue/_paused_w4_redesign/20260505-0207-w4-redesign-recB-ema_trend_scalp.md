---
id: 20260505-0207-w4-redesign-recB-ema_trend_scalp
title: "[W4-Redesign Rec=B] ema_trend_scalp (Tier 3 (FORCE_DEMOTED)) — multi-axis redesign"
owner: codex
status: queued
priority: P2
created_at: 2026-05-05T02:07:00+0900
roadmap_gate: "W4-EDA Wave 4 Rec=B batch — multi-axis redesign (heavier than S/A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/ema_trend_scalp.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/ema_trend_scalp.md`) で **THESIS_VALID_DESIGN_BROKEN** / 推奨度 **B** (複数軸の再設計が必要) と判定。
S/A タスクより複雑なので別バッチで処理。

## Audit Axis 8 抜粋

> Tier 3 (FORCE_DEMOTED) の主破綻軸は Axis 3 と Axis 4、補助的に Axis 6。Axis 2 は EMA21 pullback continuation を数学的に捕捉しており、Axis 5 の `1.0ATR : 1.8ATR` も順張り continuation と整合する。一方、current bar の `entry/open_price` で bounce を見るため live では未確定足・同一 bar 再発火のリスクがあり、さらに強トレンドを `ADX>=30` bonus で報酬しながら `ADX>31` を pullback anti-trend として罰する矛盾がある。既存 evidence でも NY × high-vol / trend 系 cell の WR 15-17% が繰り返し出ており、思想より実装タイミングと regime handling の破綻が濃い。

再設計案は `closed-bar pullback + moderate-trend gate + pair/session scope`。Signal は直近確定足で `ema9 > ema21`、EMA21 zone、candle bounce、RSI/BBPB を評価し、entry は次 bar 以降に限定する。Candidate には少なくとも `(entry_type, symbol, direction, signal_bar_time)` 相当の dedup key を持たせ、同一 bar の再発火を止める。ADX は `15 <= ADX <= 31` を hard gate または score cap にし、`ADX>=30` bonus は削除する。scope は ALL ではなく、まず GBP_JPY と USD_JPY Lo

## Audit Redesign Recommendation 抜粋

> 思想は捨てないが、ALL strategy としての復活推奨度は高くない。現行 aggregate は force demoted 相応に negative で、EUR_USD / GBP_USD / USD_JPY 1m は明確に FORCED。復活候補は、BT で一貫 positive の GBP_JPY、または H1 bucket で弱く positive な USD_JPY London のような cell に限るべき。

# 1. 制約 (Rule 1, B-tier complexity)

- **multi-axis 修正想定**: trigger / filter / timing / stop-TP の 2 軸以上
- **scope 制御必須**: 1 タスクで全部修正しようとせず、最も重要な 1-2 軸を選び他は別タスク化提案
- **Pre-reg LOCK** 必須
- **365d BT** + WF folds>=3 + Bonferroni
- Shadow stage のみ (Live promote = 別タスク)

# 2. Implementation Steps

## Step 1: Scope decision

audit Axis 8 を読み、本タスクで対応する 1-2 軸を選定。残りの軸は `knowledge-base/wiki/decisions/ema_trend_scalp-recB-deferred-axes-2026-05-05.md` に「次タスク候補」として記録。

## Step 2: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/ema_trend_scalp-redesign-recB-2026-05-05.md` に:
- 対応する軸の現行設計 vs proposed
- LOCK criteria

## Step 3: 失敗テスト追加

`tests/test_ema_trend_scalp_redesign_recB.py`

## Step 4: 実装 (選定軸のみ)

## Step 5: テスト緑

## Step 6: 365d BT 比較

`knowledge-base/raw/bt-results/ema_trend_scalp-redesign-recB-2026-05-05.json`

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
