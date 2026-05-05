---
id: 20260505-0142-w4-redesign-mtf_counter_trend_scalp
title: "[W4-Redesign #39] mtf_counter_trend_scalp (Tier 4 (SCALP_SENTINEL)) — TIMING/A"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T01:42:00+0900
roadmap_gate: "W4-EDA Wave 4 redesign — REDESIGN_QUEUE rank #39 (A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/mtf_counter_trend_scalp.md
  - audits/edge_design/_REDESIGN_QUEUE.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - audits/edge_design/streak_reversal.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/mtf_counter_trend_scalp.md`) で **TIMING** / 推奨度 **A** と判定。
REDESIGN_QUEUE rank **#39** (Tier 4 (SCALP_SENTINEL))。

「思想は正、設計が誤」仮説に基づく Wave 4 一括 redesign の一環。

## Audit Axis 8 抜粋

> Tier 4 (SCALP_SENTINEL) なので failure mode 診断対象。破綻軸は Axis 3 が主で、Axis 7 が検証不足として残る。Axis 2 は MR exhaustion trigger と整合し、Axis 4 の filter は trend tail / cost / micro-reversal を強化し、Axis 5 の wick stop + 1.2R floor は短命 exhaustion swing と整合する。一方で、未確定 1m bar の engulfing/pin、足色、Stoch cross を同一 evaluate で読み、strategy 内に bar-close gate と dedup key がないため、BT/Shadow/Live で signal timing がズレるリスクがある。さらに `ctx.htf["m15"]` / `ctx.htf["m5"]` 欠落で no-trade になるデータ契約も過去に silent 化原因として観測されている。

再設計案は Timing/Data-contract 修正の 1 系統。M15/M5 は確定済み HTF feature だけを渡す契約にし、M1 engulfing/pin と Stoch/足色は直近確定 1m bar で評価、entry は次 bar execution に分離する。Candidate または routing 層に `entry_type + symbol + signal + signal_bar_time` の dedup key を持たせ、同一 signal bar の多重発火を止める。trigger/filter/stop は現行維持でよいが、修正後に 365d BT または少なくとも pre-registered 180

## Audit Redesign Recommendation 抜粋

> 思想は明確で、trigger/filter/stop の設計は大きく崩れていない。修正対象は timing/data contract に集中させる。具体的には `ctx.df.iloc[-1]` を「確定済み 1m signal bar」として扱える context を用意し、未確定 bar なら return する。HTF 側も `m15` / `m5` が close 済み feature であることを上位層で保証し、欠落時は silent no-trade ではなく監査可能な reject reason を残す。

# 1. 制約 (Rule R1)

- **No live promote** in this task. Shadow-stage 実装と BT 検証のみ。
- **Pre-reg LOCK** 必須: 仕様変更を `knowledge-base/wiki/decisions/` に記録してから実装。
- **365d BT 必須**: 現行版 vs proposed variant を A/B 比較。
- **WF folds >= 3, positive_ratio >= 0.67** で stable 確認。
- **Bonferroni-adjusted p < 0.05** または **Wilson lo current+0.05 以上** で有意性確認。
- **Kelly >= 0.40** が望ましい (lower bar OK if defensive narrowing)。

# 2. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/mtf_counter_trend_scalp-redesign-2026-05-05.md` に:
- 現行設計の問題点 (audit Axis 引用)
- proposed variant の仕様 (具体コード差分)
- 評価軸 (BT 指標 + 合否基準)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_mtf_counter_trend_scalp_redesign.py` に proposed variant の挙動テスト。

## Step 3: 実装

audit 推奨に従い変更。最小差分を優先。

## Step 4: テスト緑

## Step 5: 365d BT (現行 vs proposed)

`knowledge-base/raw/bt-results/mtf_counter_trend_scalp-redesign-2026-05-05.json` に保存。

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
