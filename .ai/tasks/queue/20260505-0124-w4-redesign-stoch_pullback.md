---
id: 20260505-0124-w4-redesign-stoch_pullback
title: "[W4-Redesign #21] stoch_pullback (Tier 2 (Shadow)) — TIMING/A"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T01:24:00+0900
roadmap_gate: "W4-EDA Wave 4 redesign — REDESIGN_QUEUE rank #21 (A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/stoch_pullback.md
  - audits/edge_design/_REDESIGN_QUEUE.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - audits/edge_design/streak_reversal.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/stoch_pullback.md`) で **TIMING** / 推奨度 **A** と判定。
REDESIGN_QUEUE rank **#21** (Tier 2 (Shadow))。

「思想は正、設計が誤」仮説に基づく Wave 4 一括 redesign の一環。

## Audit Axis 8 抜粋

> Tier 2 (Shadow) 指定だが、同一実装の `entry_type` はコード上 `stoch_trend_pullback` で、tier-master には FORCE_DEMOTED および USDJPY PAIR_DEMOTED としても現れる。既存 audit でも全体 N=142 / PF=0.64 / Kelly=-16.2%、3month H1 bucket 合算近似 N=181 / PF=0.54 / Kelly=-18.7% と underperforming なので failure mode 診断対象とする。

破綻軸は主に Axis 3。Axis 2 の trigger は trend-pullback thesis を捕捉しており、Axis 4 の filter は thesis を直接壊していない。Axis 5 の nominal R:R=2.25 も順張り pullback としては整合する。にもかかわらず成績が崩れる理由は、現在足の Stoch/EMA/price を intrabar で読める構造と dedup 欠落により、Stoch cross の「確定後回復」ではなく未確定の揺れを拾うリスクがあるため。副次的には Axis 6 の ALL 一括適用が session/pair loss pocket を混入させている。

再設計案は timing 修正を第一優先にする。`ctx.df.iloc[-2]` を confirmation bar として Stoch K/D、EMA、RSI、BBPB、close をすべて確定足ベースに揃え、entry は次 bar open または実行層の確定後価格に限定する。さらに `(instrument, signal, bar_time)` dedup を strategy または disp

## Audit Redesign Recommendation 抜粋

> 思想は有効候補として残す。Stoch pullback recovery を EMA/ADX trend 方向に限定する設計は明確で、MA filter on MR や HMM hard gate のような thesis 破壊は見えない。現行の最大問題は「回復を確定足で見ているか」が strategy file から保証されず、未確定足の K/D cross と price/EMA 条件で入れること。

# 1. 制約 (Rule R1)

- **No live promote** in this task. Shadow-stage 実装と BT 検証のみ。
- **Pre-reg LOCK** 必須: 仕様変更を `knowledge-base/wiki/decisions/` に記録してから実装。
- **365d BT 必須**: 現行版 vs proposed variant を A/B 比較。
- **WF folds >= 3, positive_ratio >= 0.67** で stable 確認。
- **Bonferroni-adjusted p < 0.05** または **Wilson lo current+0.05 以上** で有意性確認。
- **Kelly >= 0.40** が望ましい (lower bar OK if defensive narrowing)。

# 2. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/stoch_pullback-redesign-2026-05-05.md` に:
- 現行設計の問題点 (audit Axis 引用)
- proposed variant の仕様 (具体コード差分)
- 評価軸 (BT 指標 + 合否基準)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_stoch_pullback_redesign.py` に proposed variant の挙動テスト。

## Step 3: 実装

audit 推奨に従い変更。最小差分を優先。

## Step 4: テスト緑

## Step 5: 365d BT (現行 vs proposed)

`knowledge-base/raw/bt-results/stoch_pullback-redesign-2026-05-05.json` に保存。

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
