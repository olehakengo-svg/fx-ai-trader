---
id: 20260505-0123-w4-redesign-sr_liquidity_grab
title: "[W4-Redesign #20] sr_liquidity_grab (Tier 2 (Shadow)) — TIMING/A"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T01:23:00+0900
roadmap_gate: "W4-EDA Wave 4 redesign — REDESIGN_QUEUE rank #20 (A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/sr_liquidity_grab.md
  - audits/edge_design/_REDESIGN_QUEUE.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - audits/edge_design/streak_reversal.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/sr_liquidity_grab.md`) で **TIMING** / 推奨度 **A** と判定。
REDESIGN_QUEUE rank **#20** (Tier 2 (Shadow))。

「思想は正、設計が誤」仮説に基づく Wave 4 一括 redesign の一環。

## Audit Axis 8 抜粋

> Tier 2 (Shadow) だが、既存 production 実測 N=300 / EV=-0.65p / sum=-390.8p で underperforming として failure mode 診断を適用する。破綻軸は主に Axis 3 と Axis 6。Axis 2 は SR sweep + close-back-inside + reversal body で thesis を直接捕捉し、Axis 4 の ADX/SR/round-number filter も thesis を破壊していない。Axis 5 も hunt extreme 外側 SL と 1.5R / opposite SR TP で大枠は整合する。一方、現在足の `ctx.entry` と `ctx.open_price` で反転確認する設計は bar-close contract がなく、実行層次第で intrabar 変動と同一 bar 多重 entry に寄る。また 5 majors 一括 whitelist は production 実測の pair 差を無視しており、GBPUSD 以外を同じ threshold で流すのは FORCED。

再設計案は timing と pair scope を絞る。`_find_recent_hunt()` は過去確定 bar の hunt 検出として維持し、反転確認だけを current tick から確定済み signal bar へ移す。具体的には `ctx.df.iloc[-2]` を signal bar として `Close > Open` / `< Open` と `Close` の level reclaim を判定し、`ctx.entry` は次 bar execution price として使う。さらに dispatch la

## Audit Redesign Recommendation 抜粋

> 思想は維持する。SR に紐づく liquidity grab を、低 ADX の中で hunt 後の反転として取る thesis はコードから明確に導出でき、trigger/filter/SLTP の大枠も破綻していない。現状の負け方は、反転確認が未確定 current bar に依存していることと、pair scope が一括許可になっていることが主因と見る。

# 1. 制約 (Rule R1)

- **No live promote** in this task. Shadow-stage 実装と BT 検証のみ。
- **Pre-reg LOCK** 必須: 仕様変更を `knowledge-base/wiki/decisions/` に記録してから実装。
- **365d BT 必須**: 現行版 vs proposed variant を A/B 比較。
- **WF folds >= 3, positive_ratio >= 0.67** で stable 確認。
- **Bonferroni-adjusted p < 0.05** または **Wilson lo current+0.05 以上** で有意性確認。
- **Kelly >= 0.40** が望ましい (lower bar OK if defensive narrowing)。

# 2. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/sr_liquidity_grab-redesign-2026-05-05.md` に:
- 現行設計の問題点 (audit Axis 引用)
- proposed variant の仕様 (具体コード差分)
- 評価軸 (BT 指標 + 合否基準)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_sr_liquidity_grab_redesign.py` に proposed variant の挙動テスト。

## Step 3: 実装

audit 推奨に従い変更。最小差分を優先。

## Step 4: テスト緑

## Step 5: 365d BT (現行 vs proposed)

`knowledge-base/raw/bt-results/sr_liquidity_grab-redesign-2026-05-05.json` に保存。

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
