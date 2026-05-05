---
id: 20260505-0114-w4-redesign-gold_trend_momentum
title: "[W4-Redesign #11] gold_trend_momentum (Tier 2 (Shadow)) — TIMING/A"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T01:14:00+0900
roadmap_gate: "W4-EDA Wave 4 redesign — REDESIGN_QUEUE rank #11 (A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/gold_trend_momentum.md
  - audits/edge_design/_REDESIGN_QUEUE.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - audits/edge_design/streak_reversal.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/gold_trend_momentum.md`) で **TIMING** / 推奨度 **A** と判定。
REDESIGN_QUEUE rank **#11** (Tier 2 (Shadow))。

「思想は正、設計が誤」仮説に基づく Wave 4 一括 redesign の一環。

## Audit Axis 8 抜粋

> Tier 3/4 ではなく Tier 2 Shadow だが、既存資料上は XAU production-excluded かつ promotion-grade empirical evidence が不足している。設計破綻の主因候補は Axis 3。Trigger、filter、stop/TP geometry は XAU momentum thesis と概ね整合している一方、pullback 判定、confirmation candle、MACD-H、swing stop が current bar を含みうるため、bar-close 前提が崩れると「EMA21 に触れたように見える未確定足」「陽線/陰線が途中で反転する足」「同一 15m bar での重複発火」を拾う。

再設計案は timing 変更に絞る。Signal 判定は `signal_bar = ctx.df.iloc[-2]` に固定し、pullback window も `[-PB_LOOKBACK-1:-1]` の確定足だけを見る。Execution は次 bar の `ctx.entry` に限定し、`(symbol, strategy, signal_bar_time)` の per-bar dedup を実行層または strategy state に追加する。Stop も signal bar 以前の swing high/low で計算し、current bar high/low を含めない。

## Audit Redesign Recommendation 抜粋

> 思想は維持する。変更対象は trigger の方向性や filter ではなく、bar-close 化と dedup。具体的には、EMA/ADX/DI/MACD は close 確定済みの `signal_bar` で評価し、pullback 判定は current bar を除外した直近 8 本に限定する。BUY なら `signal_close > signal_open` と `signal_close > EMA9_signal`、SELL なら対称条件で確定足 confirmation を作り、次 bar open/現在 `ctx.entry` で Candidate を emit する。

# 1. 制約 (Rule R1)

- **No live promote** in this task. Shadow-stage 実装と BT 検証のみ。
- **Pre-reg LOCK** 必須: 仕様変更を `knowledge-base/wiki/decisions/` に記録してから実装。
- **365d BT 必須**: 現行版 vs proposed variant を A/B 比較。
- **WF folds >= 3, positive_ratio >= 0.67** で stable 確認。
- **Bonferroni-adjusted p < 0.05** または **Wilson lo current+0.05 以上** で有意性確認。
- **Kelly >= 0.40** が望ましい (lower bar OK if defensive narrowing)。

# 2. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/gold_trend_momentum-redesign-2026-05-05.md` に:
- 現行設計の問題点 (audit Axis 引用)
- proposed variant の仕様 (具体コード差分)
- 評価軸 (BT 指標 + 合否基準)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_gold_trend_momentum_redesign.py` に proposed variant の挙動テスト。

## Step 3: 実装

audit 推奨に従い変更。最小差分を優先。

## Step 4: テスト緑

## Step 5: 365d BT (現行 vs proposed)

`knowledge-base/raw/bt-results/gold_trend_momentum-redesign-2026-05-05.json` に保存。

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
