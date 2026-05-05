---
id: 20260505-0100-w4p1-streak-reversal-htf-soft-penalty
title: "[W4 P1] streak_reversal HTF hard block → soft penalty (Rule 1 pre-reg)"
owner: codex
status: queued
priority: P0
created_at: 2026-05-05T01:00:00+0900
roadmap_gate: "W4-EDA Wave 4 Phase 1 — defensive patch for highest-evidence DESIGN_BROKEN strategy"
rule: R1
prereq_artifacts:
  - audits/edge_design/streak_reversal.md
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
related:
  - audits/edge_design/_REDESIGN_QUEUE.md
  - audits/edge_design/_TIER1_GATE.md
---

# 0. なぜこのタスクか

W4-EDA audit (76 戦略) で `streak_reversal` は **唯一 SUFFICIENT_EVIDENCE** を満たす Tier 1 戦略 (N=468, WR=72.2%, Wilson lo=68%, PF=3.07, Bonferroni p=1.3e-5, Kelly=0.487)。しかし daytrade variant の **HTF hard block** が MR の tail-event 反転を hard reject しており、Bonferroni-significant な edge tail を live routing から消している。

これは memory `feedback_ma_filter_breaks_mr.md` (bb_rsi_reversion: H1 EMA200 で Kelly 0.43→0) と `feedback_hmm_gate_same_trap.md` (USDJPY TF +478p→-4p) の **同型再現 第3例**。

audit 監査 (`audits/edge_design/streak_reversal.md`):
> 破綻軸は Axis 4 (BREAKS) — `_stk_htf_blocked` は HTF bull 中の SELL reversal と HTF bear 中の BUY reversal を拒否し、MR が依存する trend-tail reversal を切る。
> 推奨: hard reject → soft penalty (`conf = max(25, conf - _stk_bonus)` 相当)

# 1. 仮説

HTF hard block を soft penalty 化することで:
- BT 365d で aggregate WR / EV / PF が悪化しない（hard reject されていた tail event は元々 Bonferroni-significant edge の一部）
- Live shadow で N>=30 の段階的検証で同等以上のパフォーマンスが見込める

# 2. 制約 (Rule 1: Slow & Strict)

新戦略 / フィルタ変更 / Live behavior expansion に該当するため Rule 1:
- 365d BT 必須 (現行版 vs proposed soft-penalty variant の A/B)
- WF folds >= 3 で positive_ratio 確認
- Bonferroni-adjusted p で有意性確認
- Pre-registration LOCK (本タスクで仕様確定)
- Shadow N>=30 蓄積後に Live 昇格判断 (別タスク)

# 3. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書作成

`knowledge-base/wiki/decisions/streak-reversal-htf-soft-penalty-pre-reg.md` に:
- variant 仕様 (hard reject → `conf = max(25, conf - 25)` 相当)
- 評価軸 (365d BT / WF folds>=3 / Bonferroni / Wilson lo>=current+0.05 / Kelly>=0.40)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_streak_reversal_htf_soft_penalty.py`:
- HTF bull 中 SELL signal が `conf=25` で出力される (現行は None)
- HTF bear 中 BUY signal が `conf=25` で出力される

## Step 3: 実装

`app.py:3201-3260` (daytrade variant) で `_stk_htf_blocked` を soft penalty 化。
具体的には `if _stk_htf_blocked:` 分岐で `signal = WAIT` ではなく `conf = max(25, conf - 25)` に変更。
scalp variant `app.py:8707-8745` には HTF block が無いので変更不要。

## Step 4: テスト緑

## Step 5: 365d BT 比較 (modules/bt 経由 or backtest_mode=True)

- 現行 hard reject: N, WR, EV, PF, Wilson lo, WF folds, Bonferroni p
- Proposed soft penalty: 同上指標
- 比較レポートを `knowledge-base/raw/bt-results/streak-reversal-htf-soft-penalty-2026-05-05.json` に保存

## Step 6: Pre-reg LOCK criteria 満たすか判定

- 満たす → commit + PR 化、shadow promote 提案
- 満たさない → REJECT、原因分析、Wave 4 別 candidate へ移行

## Step 7: Codex adversarial review

実装と BT 結果を Codex 自己レビュー (post-hoc selection / data leakage / look-ahead bias チェック)。

# 4. Acceptance

- Pre-reg LOCK 文書あり
- 4 件失敗テスト → 緑
- 365d BT 比較レポートあり
- LOCK criteria 判定 (PASS / FAIL)
- Codex adversarial review pass

# 5. Out of Scope

- scalp variant (HTF block 無し)
- Stop/TP geometry 変更 (audit Axis 5 — 別 phase)
- Closed-bar 化 (audit Axis 3 — 別 phase)
- Live 昇格 (本タスクは shadow 提案までで停止、user 承認後別タスク)
