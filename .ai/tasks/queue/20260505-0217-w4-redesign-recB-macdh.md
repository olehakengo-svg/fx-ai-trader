---
id: 20260505-0217-w4-redesign-recB-macdh
title: "[W4-Redesign Rec=B] macdh (Tier 2 (Shadow)) — multi-axis redesign"
owner: codex
status: queued
priority: P2
created_at: 2026-05-05T02:17:00+0900
roadmap_gate: "W4-EDA Wave 4 Rec=B batch — multi-axis redesign (heavier than S/A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/macdh.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/macdh.md`) で **THESIS_VALID_DESIGN_BROKEN** / 推奨度 **B** (複数軸の再設計が必要) と判定。
S/A タスクより複雑なので別バッチで処理。

## Audit Axis 8 抜粋

> Tier 2 (Shadow) 指定だが、現行 tier-master では force_demoted と pair_demoted(GBP_USD) にも現れ、strategy aggregate は N=62, WR=32.26%, Wilson lo=21.95%, EV=-0.90, PF=0.468, Kelly=0.0000, Bonferroni p=1.0000。failure mode 診断対象として扱う。

破綻軸は Axis 3 と Axis 5。Axis 2 の thesis/trigger はコードから明確で、BB/RSI extreme と MACD-H exhaustion reversal は MR と整合している。Axis 4 の pair/time filter も大きくは破壊していない。一方、MACD-H 反転を current context で読み、bar-close/dedup 契約が strategy 内にないため、実運用では未確定足反転または同 bar 多重 entry の timing risk が残る。さらに 1ATR stop / 1.5ATR TP は、実測 WR 32.26% と摩擦負けに対して損益分岐を満たせず、MR が平均へ戻る前に切られる geometry になっている。

再設計案は、MACD-H 反転の「1本早い検出」という思想だけ残し、entry を確定足の次 bar に固定した 5m variant へ分離すること。Trigger は `signal_row = closed[-2]` で `bbpb <= 0.15/0.85` の Tier1 のみ、かつ `rsi5` を現行 48/52 からより extreme 側へ戻す。Filter は ALL ではなく EUR_USD NY/ATR高位または 

## Audit Redesign Recommendation 抜粋

> 思想は捨てない。コードからは「BB/RSI extreme の中で MACD-H の反転を他の MR より早く拾う」という thesis が直接読め、Axis 2 は成立している。ただし現行の `ALL` scope、current-bar timing 契約、1ATR/1.5ATR geometry の組み合わせは既存実測の低 WR・低 PF と整合せず、単一行削除では復活しない。

# 1. 制約 (Rule 1, B-tier complexity)

- **multi-axis 修正想定**: trigger / filter / timing / stop-TP の 2 軸以上
- **scope 制御必須**: 1 タスクで全部修正しようとせず、最も重要な 1-2 軸を選び他は別タスク化提案
- **Pre-reg LOCK** 必須
- **365d BT** + WF folds>=3 + Bonferroni
- Shadow stage のみ (Live promote = 別タスク)

# 2. Implementation Steps

## Step 1: Scope decision

audit Axis 8 を読み、本タスクで対応する 1-2 軸を選定。残りの軸は `knowledge-base/wiki/decisions/macdh-recB-deferred-axes-2026-05-05.md` に「次タスク候補」として記録。

## Step 2: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/macdh-redesign-recB-2026-05-05.md` に:
- 対応する軸の現行設計 vs proposed
- LOCK criteria

## Step 3: 失敗テスト追加

`tests/test_macdh_redesign_recB.py`

## Step 4: 実装 (選定軸のみ)

## Step 5: テスト緑

## Step 6: 365d BT 比較

`knowledge-base/raw/bt-results/macdh-redesign-recB-2026-05-05.json`

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
