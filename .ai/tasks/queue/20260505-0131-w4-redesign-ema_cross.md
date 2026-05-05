---
id: 20260505-0131-w4-redesign-ema_cross
title: "[W4-Redesign #28] ema_cross (Tier 3 (FORCE_DEMOTED)) — TIMING/A"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T01:31:00+0900
roadmap_gate: "W4-EDA Wave 4 redesign — REDESIGN_QUEUE rank #28 (A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/ema_cross.md
  - audits/edge_design/_REDESIGN_QUEUE.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - audits/edge_design/streak_reversal.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/ema_cross.md`) で **TIMING** / 推奨度 **A** と判定。
REDESIGN_QUEUE rank **#28** (Tier 3 (FORCE_DEMOTED))。

「思想は正、設計が誤」仮説に基づく Wave 4 一括 redesign の一環。

## Audit Axis 8 抜粋

> Tier 3 (FORCE_DEMOTED) のため failure mode を診断する。Axis 2/4/5 は strategy file 単体では大きく破綻していない。trigger は trend-retest を捕捉し、ADX/HTF filter は thesis を補強し、2:1 TP/SL も momentum geometry と整合する。

破綻軸は主に Axis 3。current-bar の `ctx.entry/open_price/macdh/rsi` による confirmation と strategy 内 dedup 欠落が、live intrabar では未確定足の見かけの再加速を拾う。加えてクロスから 2-8 本待つ retest 設計は thesis と矛盾しないが、既存 evidence の負け方を見る限り、発火が「再加速」ではなく「クロス後に伸び切った current-bar continuation」を追っている可能性が高い。Axis 6 の ALL forced scope も失敗を増幅しており、USDJPY の narrow SELL tail と London BUY の負けを同じ戦略集計に混ぜている。

再設計案は timing と cell scope の切り分けを最小単位にする。Trigger 本体は維持しつつ、confirmation を確定足 `ctx.df.iloc[-2]` ベースに固定し、次 bar 約定に分離する。strategy または dispatch 層で `(symbol, direction, signal_bar_time)` dedup を必須化する。さらに ALL をやめ、まずは既存 deep dive で唯一形のある `USD_JPY × NY × SELL` tail だけを pre

## Audit Redesign Recommendation 抜粋

> 思想は有効候補として残す。EMA cross + pullback + ADX/HTF alignment は trend-retest の入口として自然で、現行コードから thesis を捏造せずに読める。失敗の中心は trigger そのものより、未確定 current bar を confirmation として読む timing 契約と、ALL scope で tail と toxic cell を混ぜる運用設計にある。

# 1. 制約 (Rule R1)

- **No live promote** in this task. Shadow-stage 実装と BT 検証のみ。
- **Pre-reg LOCK** 必須: 仕様変更を `knowledge-base/wiki/decisions/` に記録してから実装。
- **365d BT 必須**: 現行版 vs proposed variant を A/B 比較。
- **WF folds >= 3, positive_ratio >= 0.67** で stable 確認。
- **Bonferroni-adjusted p < 0.05** または **Wilson lo current+0.05 以上** で有意性確認。
- **Kelly >= 0.40** が望ましい (lower bar OK if defensive narrowing)。

# 2. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/ema_cross-redesign-2026-05-05.md` に:
- 現行設計の問題点 (audit Axis 引用)
- proposed variant の仕様 (具体コード差分)
- 評価軸 (BT 指標 + 合否基準)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_ema_cross_redesign.py` に proposed variant の挙動テスト。

## Step 3: 実装

audit 推奨に従い変更。最小差分を優先。

## Step 4: テスト緑

## Step 5: 365d BT (現行 vs proposed)

`knowledge-base/raw/bt-results/ema_cross-redesign-2026-05-05.json` に保存。

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
