---
id: 20260505-0116-w4-redesign-london_ny_swing
title: "[W4-Redesign #13] london_ny_swing (Tier 2 (Shadow)) — TIMING/A"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T01:16:00+0900
roadmap_gate: "W4-EDA Wave 4 redesign — REDESIGN_QUEUE rank #13 (A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/london_ny_swing.md
  - audits/edge_design/_REDESIGN_QUEUE.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - audits/edge_design/streak_reversal.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/london_ny_swing.md`) で **TIMING** / 推奨度 **A** と判定。
REDESIGN_QUEUE rank **#13** (Tier 2 (Shadow))。

「思想は正、設計が誤」仮説に基づく Wave 4 一括 redesign の一環。

## Audit Axis 8 抜粋

> Tier 2 (Shadow) のため昇格前 failure mode として診断する。主破綻は Axis 3。思想と trigger は明確で、filters も continuation thesis を破壊していないが、strategy 内では signal bar を確定足として固定する契約、signal→next-bar execution、同一bar dedup が保証されていない。副次的には Axis 6/7 で、tier-master 上は ALL / phase0_shadow として扱われる一方、コードは EURUSD/GBPUSD 専用で、さらに audit DB には対象行が 0 件である。

再設計案は timing hardening を最小単位にする。London range は現行どおり過去barから算出しつつ、trigger 判定を `signal_bar = ctx.df.iloc[-2]` の close/open に固定し、entry は次bar execution の `ctx.entry` として分離する。あわせて `(symbol, strategy, signal, bar_time)` の last-emitted guard を strategy または dispatch 層に置き、同一bar複数 Candidate を禁止する。BT は本監査では実行しないため、採用前には EURUSD/GBPUSD 別に既存 audit pipeline で Wilson lower / PF / WF folds>=3 / Bonferroni-adjusted p / Kelly fraction を再発行する必要がある。

## Audit Redesign Recommendation 抜粋

> Trigger の思想自体は維持する。修正対象は timing 1 系統で、`ctx.entry > _ldn_high + ATR*buffer` / `< _ldn_low - ATR*buffer` を current context の即時判定として扱うのではなく、確定済み signal bar の close で breakout と陽線/陰線を判定し、execution price は次barに分ける。これにより intrabar 更新や同一bar再評価での runaway を切れる。

# 1. 制約 (Rule R1)

- **No live promote** in this task. Shadow-stage 実装と BT 検証のみ。
- **Pre-reg LOCK** 必須: 仕様変更を `knowledge-base/wiki/decisions/` に記録してから実装。
- **365d BT 必須**: 現行版 vs proposed variant を A/B 比較。
- **WF folds >= 3, positive_ratio >= 0.67** で stable 確認。
- **Bonferroni-adjusted p < 0.05** または **Wilson lo current+0.05 以上** で有意性確認。
- **Kelly >= 0.40** が望ましい (lower bar OK if defensive narrowing)。

# 2. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/london_ny_swing-redesign-2026-05-05.md` に:
- 現行設計の問題点 (audit Axis 引用)
- proposed variant の仕様 (具体コード差分)
- 評価軸 (BT 指標 + 合否基準)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_london_ny_swing_redesign.py` に proposed variant の挙動テスト。

## Step 3: 実装

audit 推奨に従い変更。最小差分を優先。

## Step 4: テスト緑

## Step 5: 365d BT (現行 vs proposed)

`knowledge-base/raw/bt-results/london_ny_swing-redesign-2026-05-05.json` に保存。

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
