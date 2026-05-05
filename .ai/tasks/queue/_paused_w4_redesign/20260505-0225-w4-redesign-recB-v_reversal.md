---
id: 20260505-0225-w4-redesign-recB-v_reversal
title: "[W4-Redesign Rec=B] v_reversal (Tier 3 (FORCE_DEMOTED)) — multi-axis redesign"
owner: codex
status: queued
priority: P2
created_at: 2026-05-05T02:25:00+0900
roadmap_gate: "W4-EDA Wave 4 Rec=B batch — multi-axis redesign (heavier than S/A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/v_reversal.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/v_reversal.md`) で **THESIS_VALID_DESIGN_BROKEN** / 推奨度 **B** (複数軸の再設計が必要) と判定。
S/A タスクより複雑なので別バッチで処理。

## Audit Axis 8 抜粋

> Tier 3 (FORCE_DEMOTED) なので failure mode 診断対象。破綻軸は主に Axis 3 と Axis 5、補助的に Axis 6。Axis 2 の trigger は MR thesis を数学的に捕捉しており、Axis 4 でも MA filter / HMM gate のような thesis 破壊は見えない。したがって「思想は正、設計が誤」の候補として扱えるが、現行は現在足の反転を未確定のまま拾える timing と、固定 ATR target / recent extreme stop の geometry が scalp MR と噛み合っていない。

再設計案は、まず closed-bar 化すること。signal bar を `df.iloc[-2]` に固定し、`rsi`, `bb_pband`, `stoch_k`, `Open/Close/High/Low`, body ratio, MACD-H turn をすべて確定足から読む。entry は次 bar execution に分離し、dispatcher または strategy 側で `(v_reversal, instrument, signal, signal_bar_time)` dedup を必須にする。

次に geometry を mean-reversion target に寄せる。BUY の TP は `min(entry + 1.0ATR7, bb_mid or pre-drop midpoint)`、SELL は `max(entry - 1.0ATR7, bb_mid or pre-surge midpoint)` のように mean target を参照し、SL は直近 3 本 extreme 外側を維持しつつ最大許容幅を ATR で cap する 

## Audit Redesign Recommendation 抜粋

> 思想は維持候補。コードから V 字 MR thesis は明確に導出でき、trigger も oversold/overbought と反転確認を含むため、thesis 自体を棄却する根拠はない。一方で、closed-bar / dedup / signal-to-execution 分離が strategy file から保証されず、現在足の揺れを反転として認識する構造がある。

# 1. 制約 (Rule 1, B-tier complexity)

- **multi-axis 修正想定**: trigger / filter / timing / stop-TP の 2 軸以上
- **scope 制御必須**: 1 タスクで全部修正しようとせず、最も重要な 1-2 軸を選び他は別タスク化提案
- **Pre-reg LOCK** 必須
- **365d BT** + WF folds>=3 + Bonferroni
- Shadow stage のみ (Live promote = 別タスク)

# 2. Implementation Steps

## Step 1: Scope decision

audit Axis 8 を読み、本タスクで対応する 1-2 軸を選定。残りの軸は `knowledge-base/wiki/decisions/v_reversal-recB-deferred-axes-2026-05-05.md` に「次タスク候補」として記録。

## Step 2: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/v_reversal-redesign-recB-2026-05-05.md` に:
- 対応する軸の現行設計 vs proposed
- LOCK criteria

## Step 3: 失敗テスト追加

`tests/test_v_reversal_redesign_recB.py`

## Step 4: 実装 (選定軸のみ)

## Step 5: テスト緑

## Step 6: 365d BT 比較

`knowledge-base/raw/bt-results/v_reversal-redesign-recB-2026-05-05.json`

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
