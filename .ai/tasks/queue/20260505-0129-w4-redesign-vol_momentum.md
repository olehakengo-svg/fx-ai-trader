---
id: 20260505-0129-w4-redesign-vol_momentum
title: "[W4-Redesign #26] vol_momentum (Tier 2 (Shadow)) — TIMING/A"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T01:29:00+0900
roadmap_gate: "W4-EDA Wave 4 redesign — REDESIGN_QUEUE rank #26 (A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/vol_momentum.md
  - audits/edge_design/_REDESIGN_QUEUE.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - audits/edge_design/streak_reversal.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/vol_momentum.md`) で **TIMING** / 推奨度 **A** と判定。
REDESIGN_QUEUE rank **#26** (Tier 2 (Shadow))。

「思想は正、設計が誤」仮説に基づく Wave 4 一括 redesign の一環。

## Audit Axis 8 抜粋

> Tier 2 (Shadow) かつ tier-master 由来 metrics が `—` の under-evidenced cell として診断する。Axis 2 は thesis と trigger が整合し、Axis 4/5 も大きく壊していない。破綻候補は Axis 3 で、closed-bar / next-bar execution / per-bar dedup の契約が strategy 内にないため、momentum breakout の「確定した伸び」を取る設計が、実行層次第で intrabar 飛び乗りや同一足多重発火へ変質しうる。

再設計案は timing hardening を最優先にする。`evaluate()` の signal 判定を確定済み足に寄せ、`signal_bar = ctx.df.iloc[-2]` 相当の %B・Open・Close・ADX/DI snapshot で BUY/SELL を確定し、約定は次 bar の `ctx.entry` に分離する。さらに `(symbol, self.name, signal, bar_id)` の last-emitted guard を strategy または dispatch 層に追加して、同一 5m bar の再 emit を防ぐ。

## Audit Redesign Recommendation 抜粋

> 思想と trigger/filter/stop geometry は概ね維持し、timing 契約だけを固める。具体的には、現行の `ctx.bbpb` / `ctx.entry` / `ctx.open_price` 直参照による signal 判定を「確定足 snapshot で判定、次足で約定」に変更し、signal bar id を持たせて同一 bar の重複 Candidate を抑止する。

# 1. 制約 (Rule R1)

- **No live promote** in this task. Shadow-stage 実装と BT 検証のみ。
- **Pre-reg LOCK** 必須: 仕様変更を `knowledge-base/wiki/decisions/` に記録してから実装。
- **365d BT 必須**: 現行版 vs proposed variant を A/B 比較。
- **WF folds >= 3, positive_ratio >= 0.67** で stable 確認。
- **Bonferroni-adjusted p < 0.05** または **Wilson lo current+0.05 以上** で有意性確認。
- **Kelly >= 0.40** が望ましい (lower bar OK if defensive narrowing)。

# 2. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/vol_momentum-redesign-2026-05-05.md` に:
- 現行設計の問題点 (audit Axis 引用)
- proposed variant の仕様 (具体コード差分)
- 評価軸 (BT 指標 + 合否基準)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_vol_momentum_redesign.py` に proposed variant の挙動テスト。

## Step 3: 実装

audit 推奨に従い変更。最小差分を優先。

## Step 4: テスト緑

## Step 5: 365d BT (現行 vs proposed)

`knowledge-base/raw/bt-results/vol_momentum-redesign-2026-05-05.json` に保存。

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
