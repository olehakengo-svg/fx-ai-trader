---
id: 20260505-0108-w4-redesign-xs_momentum
title: "[W4-Redesign #5] xs_momentum (Tier 1 (LIVE)) — TIMING/A"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T01:08:00+0900
roadmap_gate: "W4-EDA Wave 4 redesign — REDESIGN_QUEUE rank #5 (A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/xs_momentum.md
  - audits/edge_design/_REDESIGN_QUEUE.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - audits/edge_design/streak_reversal.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/xs_momentum.md`) で **TIMING** / 推奨度 **A** と判定。
REDESIGN_QUEUE rank **#5** (Tier 1 (LIVE))。

「思想は正、設計が誤」仮説に基づく Wave 4 一括 redesign の一環。

## Audit Axis 8 抜粋

> Tier 3/4 ではないが、Tier 1 (LIVE) かつ GBP_USD の tier-master EV が `-0.013`、直近 live aggregate でも `xs_momentum` は N=4, WR=25.0%, Wilson lo=4.56%, EV=-5.40p, PF=0.507, Kelly=0.0000 と劣化しているため failure mode 診断対象とする。

破綻候補は Axis 3 が主因。現在の trigger は momentum thesis と整合しているが、closed-bar 化と per-bar dedup が strategy 内にないため、同一 momentum burst を 1 trade ではなく複数 entry に分割して浴びる構造になっている。Axis 5 は nominal には整合するが、Quick Harvest 後の実効 R:R が薄く、強い momentum を取り切る設計としては補助的な弱点がある。Axis 4 は hard break ではない。

再設計案は timing 修正を第一候補にする。`evaluate()` の trigger 後に `bar_id = ctx.bar_time or ctx.df.index[-1]` を使った `(symbol, signal, bar_id)` dedup を入れ、1本の 15m bar で同一方向を一度だけ emit する。より厳密には `df.iloc[-2]` を signal bar、現在の `ctx.entry` を次 bar execution として、`mom/EMA/足色/ADX` を確定足で計算する variant に切る。追加案として、`abs(_mom)` が極端な領域、例えば `> 3.0ATR` では cha

## Audit Redesign Recommendation 抜粋

> 思想と trigger の方向性は維持する。最小修正は timing 1 系統で、bar-close signal と per-bar dedup を strategy 側に持たせること。コードレベルでは `_mom` と `signal` が確定した直後に `bar_id` guard を置き、同一 `(ctx.symbol, signal, bar_id)` は `return None` にする案が最小差分になる。

# 1. 制約 (Rule R1)

- **No live promote** in this task. Shadow-stage 実装と BT 検証のみ。
- **Pre-reg LOCK** 必須: 仕様変更を `knowledge-base/wiki/decisions/` に記録してから実装。
- **365d BT 必須**: 現行版 vs proposed variant を A/B 比較。
- **WF folds >= 3, positive_ratio >= 0.67** で stable 確認。
- **Bonferroni-adjusted p < 0.05** または **Wilson lo current+0.05 以上** で有意性確認。
- **Kelly >= 0.40** が望ましい (lower bar OK if defensive narrowing)。

# 2. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/xs_momentum-redesign-2026-05-05.md` に:
- 現行設計の問題点 (audit Axis 引用)
- proposed variant の仕様 (具体コード差分)
- 評価軸 (BT 指標 + 合否基準)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_xs_momentum_redesign.py` に proposed variant の挙動テスト。

## Step 3: 実装

audit 推奨に従い変更。最小差分を優先。

## Step 4: テスト緑

## Step 5: 365d BT (現行 vs proposed)

`knowledge-base/raw/bt-results/xs_momentum-redesign-2026-05-05.json` に保存。

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
