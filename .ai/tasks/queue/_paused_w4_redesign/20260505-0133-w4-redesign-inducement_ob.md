---
id: 20260505-0133-w4-redesign-inducement_ob
title: "[W4-Redesign #30] inducement_ob (Tier 3 (FORCE_DEMOTED)) — DESIGN/A"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T01:33:00+0900
roadmap_gate: "W4-EDA Wave 4 redesign — REDESIGN_QUEUE rank #30 (A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/inducement_ob.md
  - audits/edge_design/_REDESIGN_QUEUE.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - audits/edge_design/streak_reversal.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/inducement_ob.md`) で **DESIGN** / 推奨度 **A** と判定。
REDESIGN_QUEUE rank **#30** (Tier 3 (FORCE_DEMOTED))。

「思想は正、設計が誤」仮説に基づく Wave 4 一括 redesign の一環。

## Audit Axis 8 抜粋

> Tier 3 (FORCE_DEMOTED) なので failure mode を適用する。破綻軸は Axis 3 / Axis 4 / Axis 5。Axis 2 の thesis 捕捉は比較的明確で、OB impulse、inducement sweep、20-bar liquidity grab、reclaim、HTF OB zone まで要求している。一方、Axis 3 は current bar OHLC を signal / reclaim に使い、bar-close contract と per-bar dedup がない。Axis 4 は symmetric SMC thesis に対して USDJPY BUY only / EURUSD SELL only の根拠不明な hard direction gate を入れている。Axis 5 は最大の実害で、trigger 側では 1.5ATR 以上の sweep 足を大口関与として要求するのに、stop は actual sweep extreme 外ではなく OB 境界 + 固定 2 pip なので、stop-hunt 後の二度目の wick で即死しやすい。

再設計案は、思想は維持しつつ timing と stop geometry を先に直す。`_check_liquidity_grab()` と `_check_entry()` は確定済み signal bar を対象にし、`ctx.df.iloc[-2]` を reclaim / reversal bar、`ctx.entry` を次 bar execution として扱う。Candidate か dispatch layer に `signal_bar_time` を渡し、`(symbol, entry_type, side, signal_b

## Audit Redesign Recommendation 抜粋

> 思想は捨てない。コードから導出できる thesis は、liquidity sweep と OB reclaim を使う stop-hunt reversal として明確で、trigger も thesis の主要成分を捕捉している。失敗は主に実行設計で、未確定 bar 依存、根拠不明な hard direction filter、そして actual sweep volatility に対して狭すぎる stop geometry が force_demoted の中核。

# 1. 制約 (Rule R1)

- **No live promote** in this task. Shadow-stage 実装と BT 検証のみ。
- **Pre-reg LOCK** 必須: 仕様変更を `knowledge-base/wiki/decisions/` に記録してから実装。
- **365d BT 必須**: 現行版 vs proposed variant を A/B 比較。
- **WF folds >= 3, positive_ratio >= 0.67** で stable 確認。
- **Bonferroni-adjusted p < 0.05** または **Wilson lo current+0.05 以上** で有意性確認。
- **Kelly >= 0.40** が望ましい (lower bar OK if defensive narrowing)。

# 2. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/inducement_ob-redesign-2026-05-05.md` に:
- 現行設計の問題点 (audit Axis 引用)
- proposed variant の仕様 (具体コード差分)
- 評価軸 (BT 指標 + 合否基準)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_inducement_ob_redesign.py` に proposed variant の挙動テスト。

## Step 3: 実装

audit 推奨に従い変更。最小差分を優先。

## Step 4: テスト緑

## Step 5: 365d BT (現行 vs proposed)

`knowledge-base/raw/bt-results/inducement_ob-redesign-2026-05-05.json` に保存。

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
