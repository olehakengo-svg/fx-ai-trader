---
id: 20260505-0122-w4-redesign-sr_anti_hunt_bounce
title: "[W4-Redesign #19] sr_anti_hunt_bounce (Tier 2 (Shadow)) — TIMING/A"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T01:22:00+0900
roadmap_gate: "W4-EDA Wave 4 redesign — REDESIGN_QUEUE rank #19 (A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/sr_anti_hunt_bounce.md
  - audits/edge_design/_REDESIGN_QUEUE.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - audits/edge_design/streak_reversal.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/sr_anti_hunt_bounce.md`) で **TIMING** / 推奨度 **A** と判定。
REDESIGN_QUEUE rank **#19** (Tier 2 (Shadow))。

「思想は正、設計が誤」仮説に基づく Wave 4 一括 redesign の一環。

## Audit Axis 8 抜粋

> Tier 2 (Shadow) だが、本番実測 N=300 / EV=-1.19p / sum=-355.7p で underperforming として failure mode 診断を適用する。破綻軸は Axis 3。Axis 2 は SR proximity + reversal body で thesis を捕捉しており、Axis 4 の ADX/range/hunt filters は MR thesis を破壊していない。Axis 5 も P90 hunt excursion 外側の wide stop で anti-hunt thesis と整合する。一方、15m 戦略として signal bar close / execution bar / per-bar dedup の contract が strategy file に無く、既存 production audit でも USD_JPY の同一 15m bar 再発火が大きな損失と統計汚染を作っている。

再設計案は timing を 1 系統で修正する。`evaluate()` は `ctx.df.iloc[-2]` を signal bar として SR proximity、反転足、BB%B bonus を判定し、`ctx.entry` は次 bar execution price として扱う。さらに `(symbol, strategy_name, signal_bar_time, signal)` の dedup key を strategy state か dispatch layer に渡し、同一 15m bar で BUY/SELL や複数 SR level が再 emit されないようにする。pair scope は redesign 検証では GBPUSD only、または Phase

## Audit Redesign Recommendation 抜粋

> 思想は維持する。SR 近接反転を low-ADX range で拾い、SL を P90 hunt excursion の外側へ置く thesis はコードから明確に導出でき、trigger/filter/SLTP の大枠も破綻していない。現状の負け方は、15m bar の確定性と emit 粒度が崩れて同一 bar の phantom entries を許した timing / execution contract の問題が主因と見る。

# 1. 制約 (Rule R1)

- **No live promote** in this task. Shadow-stage 実装と BT 検証のみ。
- **Pre-reg LOCK** 必須: 仕様変更を `knowledge-base/wiki/decisions/` に記録してから実装。
- **365d BT 必須**: 現行版 vs proposed variant を A/B 比較。
- **WF folds >= 3, positive_ratio >= 0.67** で stable 確認。
- **Bonferroni-adjusted p < 0.05** または **Wilson lo current+0.05 以上** で有意性確認。
- **Kelly >= 0.40** が望ましい (lower bar OK if defensive narrowing)。

# 2. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/sr_anti_hunt_bounce-redesign-2026-05-05.md` に:
- 現行設計の問題点 (audit Axis 引用)
- proposed variant の仕様 (具体コード差分)
- 評価軸 (BT 指標 + 合否基準)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_sr_anti_hunt_bounce_redesign.py` に proposed variant の挙動テスト。

## Step 3: 実装

audit 推奨に従い変更。最小差分を優先。

## Step 4: テスト緑

## Step 5: 365d BT (現行 vs proposed)

`knowledge-base/raw/bt-results/sr_anti_hunt_bounce-redesign-2026-05-05.json` に保存。

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
