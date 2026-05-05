---
id: 20260505-0119-w4-redesign-pullback_to_liquidity_v1
title: "[W4-Redesign #16] pullback_to_liquidity_v1 (Tier 2 (Shadow)) — DESIGN/A"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T01:19:00+0900
roadmap_gate: "W4-EDA Wave 4 redesign — REDESIGN_QUEUE rank #16 (A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/pullback_to_liquidity_v1.md
  - audits/edge_design/_REDESIGN_QUEUE.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - audits/edge_design/streak_reversal.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/pullback_to_liquidity_v1.md`) で **DESIGN** / 推奨度 **A** と判定。
REDESIGN_QUEUE rank **#16** (Tier 2 (Shadow))。

「思想は正、設計が誤」仮説に基づく Wave 4 一括 redesign の一環。

## Audit Axis 8 抜粋

> Tier 2 (Shadow) / phase0_shadow で、Tier 3/4 専用の復活診断ではないが、入力 metrics は 365d BT EV `—` かつ audit DB hit 0 のため昇格前 failure mode として診断する。破綻軸は Axis 2 と Axis 3。思想は明確で、HTF trend pullback + liquidity rejection という thesis 自体は成立しうるが、liquidity touch が「固定 pip 近接」ではなく片側 percentage threshold になっており、pair 間で意味が変わる。加えて current bar の rejection close を見た同 bar entry と 4-bar same-direction dedup 未実装により、実運用/BT contract 次第で signal timing が汚れる。

再設計案は trigger/timing の 2 点。Trigger は `tolerance = 5 / ctx.pip_mult` のように fixed-pip 化し、BUY は `abs(current_low - swing_low) <= tolerance` または「下抜け許容は最大 1ATR/特定 pip まで」の bounded sweep にする。Timing は rejection bar を closed signal bar と明示し、execution は次 bar open/market に分離する。さらに `(instrument, signal, bar_time)` または `(instrument, signal, swing_idx)` ベースの last-emitted guard を strategy 

## Audit Redesign Recommendation 抜粋

> 思想は維持する。最小修正は liquidity touch の数学を「片側 percentage」から「pair-aware fixed pip 近接 + bounded sweep」に変えること。想定 diff は `LIQUIDITY_TOUCH_PCT` を廃止して `LIQUIDITY_TOUCH_PIPS = 5.0` を導入し、`tol = self.LIQUIDITY_TOUCH_PIPS / ctx.pip_mult` を使って BUY `abs(current_low - swing_price) <= tol`、SELL `abs(current_high - swing_price) <= tol` にする形。stop hunt 的な深い sweep を許容したいなら、別 thesis として `current_low <= swing_low + tol and current_low >= swing_low - 0.5 * atr` のように下限/上限を明示する。

# 1. 制約 (Rule R1)

- **No live promote** in this task. Shadow-stage 実装と BT 検証のみ。
- **Pre-reg LOCK** 必須: 仕様変更を `knowledge-base/wiki/decisions/` に記録してから実装。
- **365d BT 必須**: 現行版 vs proposed variant を A/B 比較。
- **WF folds >= 3, positive_ratio >= 0.67** で stable 確認。
- **Bonferroni-adjusted p < 0.05** または **Wilson lo current+0.05 以上** で有意性確認。
- **Kelly >= 0.40** が望ましい (lower bar OK if defensive narrowing)。

# 2. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/pullback_to_liquidity_v1-redesign-2026-05-05.md` に:
- 現行設計の問題点 (audit Axis 引用)
- proposed variant の仕様 (具体コード差分)
- 評価軸 (BT 指標 + 合否基準)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_pullback_to_liquidity_v1_redesign.py` に proposed variant の挙動テスト。

## Step 3: 実装

audit 推奨に従い変更。最小差分を優先。

## Step 4: テスト緑

## Step 5: 365d BT (現行 vs proposed)

`knowledge-base/raw/bt-results/pullback_to_liquidity_v1-redesign-2026-05-05.json` に保存。

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
