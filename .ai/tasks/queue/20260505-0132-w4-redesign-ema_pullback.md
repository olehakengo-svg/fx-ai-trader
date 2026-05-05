---
id: 20260505-0132-w4-redesign-ema_pullback
title: "[W4-Redesign #29] ema_pullback (Tier 3 (FORCE_DEMOTED)) — DESIGN/A"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T01:32:00+0900
roadmap_gate: "W4-EDA Wave 4 redesign — REDESIGN_QUEUE rank #29 (A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/ema_pullback.md
  - audits/edge_design/_REDESIGN_QUEUE.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - audits/edge_design/streak_reversal.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/ema_pullback.md`) で **DESIGN** / 推奨度 **A** と判定。
REDESIGN_QUEUE rank **#29** (Tier 3 (FORCE_DEMOTED))。

「思想は正、設計が誤」仮説に基づく Wave 4 一括 redesign の一環。

## Audit Axis 8 抜粋

> Tier 3 (FORCE_DEMOTED) の failure mode は Axis 3 と Axis 5 が主因、Axis 6/7 が昇格阻害要因。Axis 2 の thesis/trigger は trend pullback を概ね捕捉しており、Axis 4 の filters も hard regime trap ではないため、思想自体は棄却しない。

再設計案は closed-bar + structure stop + pair/session split。Signal 判定を確定済み signal bar に固定し、`entry > prev_close` / body ratio / current high-low 判定を signal bar snapshot から計算する。Candidate には `(entry_type, symbol, signal_bar_time, direction)` dedup key 相当を渡し、同一 bar 再発火を止める。Stop は `ema21 ± 0.3ATR` 固定ではなく、BUY なら `min(signal_low, ema21 - 0.6ATR)`、SELL なら `max(signal_high, ema21 + 0.6ATR)` のように pullback structure の外へ置く variant を比較する。

## Audit Redesign Recommendation 抜粋

> 思想と trigger 骨格は維持する。変更はまず timing を closed-bar 化し、現バーの `ctx.entry/open/high/low` 混在を signal bar と execution bar に分離する。具体的には signal bar の `Close > PrevClose`、`abs(Close-Open)/(High-Low) >= 0.35`、MACD-H/Stoch を確定足で評価し、次 bar の `ctx.entry` で Candidate を返す形にする。

# 1. 制約 (Rule R1)

- **No live promote** in this task. Shadow-stage 実装と BT 検証のみ。
- **Pre-reg LOCK** 必須: 仕様変更を `knowledge-base/wiki/decisions/` に記録してから実装。
- **365d BT 必須**: 現行版 vs proposed variant を A/B 比較。
- **WF folds >= 3, positive_ratio >= 0.67** で stable 確認。
- **Bonferroni-adjusted p < 0.05** または **Wilson lo current+0.05 以上** で有意性確認。
- **Kelly >= 0.40** が望ましい (lower bar OK if defensive narrowing)。

# 2. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/ema_pullback-redesign-2026-05-05.md` に:
- 現行設計の問題点 (audit Axis 引用)
- proposed variant の仕様 (具体コード差分)
- 評価軸 (BT 指標 + 合否基準)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_ema_pullback_redesign.py` に proposed variant の挙動テスト。

## Step 3: 実装

audit 推奨に従い変更。最小差分を優先。

## Step 4: テスト緑

## Step 5: 365d BT (現行 vs proposed)

`knowledge-base/raw/bt-results/ema_pullback-redesign-2026-05-05.json` に保存。

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
