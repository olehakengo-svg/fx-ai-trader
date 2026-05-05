---
id: 20260505-0125-w4-redesign-three_bar_reversal
title: "[W4-Redesign #22] three_bar_reversal (Tier 2 (Shadow)) — TIMING/A"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T01:25:00+0900
roadmap_gate: "W4-EDA Wave 4 redesign — REDESIGN_QUEUE rank #22 (A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/three_bar_reversal.md
  - audits/edge_design/_REDESIGN_QUEUE.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - audits/edge_design/streak_reversal.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/three_bar_reversal.md`) で **TIMING** / 推奨度 **A** と判定。
REDESIGN_QUEUE rank **#22** (Tier 2 (Shadow))。

「思想は正、設計が誤」仮説に基づく Wave 4 一括 redesign の一環。

## Audit Axis 8 抜粋

> Tier 2 Shadow の underperforming/low-evidence cell として診断する。破綻軸は主に Axis 3、補助的に Axis 2 の trigger 過密化である。思想は「3本足の過伸展を逆張る」MR として妥当だが、現行 trigger は `3本連続足 + 現在足反転色 + 前足高値/安値突破 + BB%B + RSI5` を同時要求するため、反転の初動ではなく確認後の遅い場所に寄り、既存 decomposition でも「4条件同時必須 → 180日でN=6、年間N=12では統計検証不能」と記録されている。

再設計案は1案に絞る。過伸展条件は維持し、entry confirmation を「前足高値/安値 breakout」から「現在足が反対色で、前足実体 midpoint または前足 open を回復/割れ」に緩める。具体的には BUY を `_three_bear and _curr_bull and ctx.entry > float(ctx.df.iloc[-2]["Open"]) and ctx.bbpb < 0.40 and ctx.rsi5 < 45`、SELL を対称条件にする。これにより MR の反転初動を拾い、bar-close variant では `df.iloc[-2]` 確定足で反転確認、intrabar variant では `symbol + tf + bar_time + entry_type` dedup を必須にする。

## Audit Redesign Recommendation 抜粋

> Trigger の思想自体は残す。変更対象は confirmation timing で、前足高値/安値の完全突破を必須にする現行条件を、前足実体の回復/割れまたは前足 midpoint cross に置き換える。BB%B と RSI5 は過伸展 gate として維持しつつ、閾値は `0.35/0.65, 42/58` から `0.40/0.60, 45/55` 程度に緩める候補を pre-register する。

# 1. 制約 (Rule R1)

- **No live promote** in this task. Shadow-stage 実装と BT 検証のみ。
- **Pre-reg LOCK** 必須: 仕様変更を `knowledge-base/wiki/decisions/` に記録してから実装。
- **365d BT 必須**: 現行版 vs proposed variant を A/B 比較。
- **WF folds >= 3, positive_ratio >= 0.67** で stable 確認。
- **Bonferroni-adjusted p < 0.05** または **Wilson lo current+0.05 以上** で有意性確認。
- **Kelly >= 0.40** が望ましい (lower bar OK if defensive narrowing)。

# 2. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/three_bar_reversal-redesign-2026-05-05.md` に:
- 現行設計の問題点 (audit Axis 引用)
- proposed variant の仕様 (具体コード差分)
- 評価軸 (BT 指標 + 合否基準)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_three_bar_reversal_redesign.py` に proposed variant の挙動テスト。

## Step 3: 実装

audit 推奨に従い変更。最小差分を優先。

## Step 4: テスト緑

## Step 5: 365d BT (現行 vs proposed)

`knowledge-base/raw/bt-results/three_bar_reversal-redesign-2026-05-05.json` に保存。

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
