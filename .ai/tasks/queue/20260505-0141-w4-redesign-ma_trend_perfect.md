---
id: 20260505-0141-w4-redesign-ma_trend_perfect
title: "[W4-Redesign #38] ma_trend_perfect (Tier 4 (SCALP_SENTINEL)) — TIMING/A"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T01:41:00+0900
roadmap_gate: "W4-EDA Wave 4 redesign — REDESIGN_QUEUE rank #38 (A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/ma_trend_perfect.md
  - audits/edge_design/_REDESIGN_QUEUE.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - audits/edge_design/streak_reversal.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/ma_trend_perfect.md`) で **TIMING** / 推奨度 **A** と判定。
REDESIGN_QUEUE rank **#38** (Tier 4 (SCALP_SENTINEL))。

「思想は正、設計が誤」仮説に基づく Wave 4 一括 redesign の一環。

## Audit Axis 8 抜粋

> Tier 4 (SCALP_SENTINEL) としての主破綻候補は Axis 3。Axis 2 は順張り再加速を数学的に捕捉し、Axis 4 の H1/M15/M5 フィルタは thesis を強化し、Axis 5 の `1.0ATR : 1.8ATR` は momentum scalp と整合する。一方で、1m 確認が current bar の `ctx.entry > ctx.open_price` / `ctx.entry < ctx.open_price` と MACD-H 増減に依存し、strategy 内に bar-close gating と dedup key がないため、BT の bar-close 仮定と live evaluation の intrabar 挙動がズレるリスクがある。

再設計案は `closed-bar M5 breakout + next-bar 1m confirmation + per-bar dedup`。M5 EMA21 再ブレイクと 1m candle/MACD-H 確認を確定足のみで評価し、entry は次 bar execution に分離する。Candidate または上位 execution 層に `(entry_type, symbol, signal, signal_bar_time)` を渡して同一 bar 多重発火を止める。filter と stop/TP は現行維持でよいが、Phase B 判定では Tokyo/London decay が観測済みなので、まず NY-only または Tokyo+NY 限定で closed-bar 版の既存 BT/Shadow 指標を再集計する必要がある。

## Audit Redesign Recommendation 抜粋

> 思想と trigger/filter/stop の骨格は維持する。修正対象は timing の 1 系統で、`ctx.entry > ctx.open_price` / `ctx.entry < ctx.open_price` と `ctx.macdh` 増減を評価する足を「直近確定 1m bar」に固定し、発注は次 bar 以降にする。M5 側も `m5_close` が確定済みであることをコンテキスト契約に明示し、未確定 M5 snapshot なら発火させない。

# 1. 制約 (Rule R1)

- **No live promote** in this task. Shadow-stage 実装と BT 検証のみ。
- **Pre-reg LOCK** 必須: 仕様変更を `knowledge-base/wiki/decisions/` に記録してから実装。
- **365d BT 必須**: 現行版 vs proposed variant を A/B 比較。
- **WF folds >= 3, positive_ratio >= 0.67** で stable 確認。
- **Bonferroni-adjusted p < 0.05** または **Wilson lo current+0.05 以上** で有意性確認。
- **Kelly >= 0.40** が望ましい (lower bar OK if defensive narrowing)。

# 2. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/ma_trend_perfect-redesign-2026-05-05.md` に:
- 現行設計の問題点 (audit Axis 引用)
- proposed variant の仕様 (具体コード差分)
- 評価軸 (BT 指標 + 合否基準)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_ma_trend_perfect_redesign.py` に proposed variant の挙動テスト。

## Step 3: 実装

audit 推奨に従い変更。最小差分を優先。

## Step 4: テスト緑

## Step 5: 365d BT (現行 vs proposed)

`knowledge-base/raw/bt-results/ma_trend_perfect-redesign-2026-05-05.json` に保存。

## Step 6: LOCK criteria 判定

- PASS → commit + shadow promote 提案 (別タスクで live 昇格)
- FAIL → REJECT, 原因分析, Wave 4 別 candidate へ移行

## Step 7: Codex adversarial self-review

post-hoc selection / data leakage / look-ahead bias チェック。

# 3. Acceptance

- Pre-reg LOCK doc あり
- 失敗テスト → 緑
- BT 比較レポートあり
- LOCK criteria 判定 (PASS / FAIL) 明示
- Codex self-review 通過

# 4. Out of Scope

- Live 昇格 (本タスクは shadow promote 提案までで停止、user 承認後別タスク)
- 他 strategies の修正
- 新規 edge 探索

# 5. Notes

- このタスクは W4-Redesign 40 件一括 dispatch の一部。Codex は serial 処理で 1 件ずつ進めること。
- 実装が大規模 (Axis 2-5 全部修正等) になる場合は途中で abort し、scope を絞って別タスク化する。
- audit に書かれていない設計変更を勝手に追加しない (post-hoc justification 罠)。
