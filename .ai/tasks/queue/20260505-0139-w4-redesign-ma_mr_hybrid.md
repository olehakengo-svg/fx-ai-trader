---
id: 20260505-0139-w4-redesign-ma_mr_hybrid
title: "[W4-Redesign #36] ma_mr_hybrid (Tier 4 (SCALP_SENTINEL)) — DESIGN/A"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T01:39:00+0900
roadmap_gate: "W4-EDA Wave 4 redesign — REDESIGN_QUEUE rank #36 (A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/ma_mr_hybrid.md
  - audits/edge_design/_REDESIGN_QUEUE.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - audits/edge_design/streak_reversal.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/ma_mr_hybrid.md`) で **DESIGN** / 推奨度 **A** と判定。
REDESIGN_QUEUE rank **#36** (Tier 4 (SCALP_SENTINEL))。

「思想は正、設計が誤」仮説に基づく Wave 4 一括 redesign の一環。

## Audit Axis 8 抜粋

> Tier 4 (SCALP_SENTINEL) なので failure mode 診断対象。破綻軸は Axis 4 が主、Axis 3 と Axis 5 が副次。Axis 2 の trigger は M5 BB%B/RSI/Stoch を持つため思想の捕捉自体は成立しているが、M15 EMA21 5bps hard gate が MR の entry tail を過剰に削り、既存 audit では v1a-rev が 90d N=1 まで縮退している。さらに未確定 bar/dedup 不在の timing と、BB mid/VWAP/EMA などの mean target を使わない 1:1 ATR geometry が、scalp MR の cost-edge ratio を悪化させる。

再設計案は Filter 削除/置換を主軸にする。具体的には M15 bias hard gate を撤去し、方向は entry gate ではなく score feature に落とす。代替 trigger は `m5_bbpb <= 0.30 AND m5_rsi <= 35 AND stoch_k_cross_up` / `m5_bbpb >= 0.70 AND m5_rsi >= 65 AND stoch_k_cross_down` を bar-close 確定で判定し、M15 EMA gap は `abs(gap) <= 1bp` の neutral zone 許容または `ADX/VWAP distance` の soft score にする。Stop/TP は `TP = BB mid or VWAP/EMA mean target`、`SL = BB outer + ATR buffer` に変え、minimum net TP gate で spread 負けする候補を

## Audit Redesign Recommendation 抜粋

> 思想はコードから十分に導けるため `THESIS_INVALID` ではない。M5 過熱リバージョン trigger は成立しているが、M15 EMA21 5bps hard filter が MR edge を削る構造になっており、既存 audit の N=1 と整合する。まず `strategies/scalp/ma_mr_hybrid.py:75`-`strategies/scalp/ma_mr_hybrid.py:79` の bull/bear hard gate を entry 必須条件から外し、M15 gap は confidence/reason だけに使う設計へ移すのが最小修正。

# 1. 制約 (Rule R1)

- **No live promote** in this task. Shadow-stage 実装と BT 検証のみ。
- **Pre-reg LOCK** 必須: 仕様変更を `knowledge-base/wiki/decisions/` に記録してから実装。
- **365d BT 必須**: 現行版 vs proposed variant を A/B 比較。
- **WF folds >= 3, positive_ratio >= 0.67** で stable 確認。
- **Bonferroni-adjusted p < 0.05** または **Wilson lo current+0.05 以上** で有意性確認。
- **Kelly >= 0.40** が望ましい (lower bar OK if defensive narrowing)。

# 2. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/ma_mr_hybrid-redesign-2026-05-05.md` に:
- 現行設計の問題点 (audit Axis 引用)
- proposed variant の仕様 (具体コード差分)
- 評価軸 (BT 指標 + 合否基準)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_ma_mr_hybrid_redesign.py` に proposed variant の挙動テスト。

## Step 3: 実装

audit 推奨に従い変更。最小差分を優先。

## Step 4: テスト緑

## Step 5: 365d BT (現行 vs proposed)

`knowledge-base/raw/bt-results/ma_mr_hybrid-redesign-2026-05-05.json` に保存。

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
