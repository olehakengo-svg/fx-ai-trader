---
id: 20260505-0121-w4-redesign-squeeze
title: "[W4-Redesign #18] squeeze (Tier 2 (Shadow)) — DESIGN/A"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T01:21:00+0900
roadmap_gate: "W4-EDA Wave 4 redesign — REDESIGN_QUEUE rank #18 (A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/squeeze.md
  - audits/edge_design/_REDESIGN_QUEUE.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - audits/edge_design/streak_reversal.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/squeeze.md`) で **DESIGN** / 推奨度 **A** と判定。
REDESIGN_QUEUE rank **#18** (Tier 2 (Shadow))。

「思想は正、設計が誤」仮説に基づく Wave 4 一括 redesign の一環。

## Audit Axis 8 抜粋

> Tier 2 (Shadow) だが `bb_squeeze_breakout` は tier-master 上で主要 6 pair が PAIR_DEMOTED 扱いで、既存 audit artifact も negative / insufficient が混在するため failure mode を診断する。破綻軸は Axis 2, 3, 5。Axis 2 は「breakout」と称しながら BB 外・range 外への break を要求せず、BB 内 quartile + EMA 順列で入るため false breakout を多く拾う。Axis 3 は未確定足と同一 bar 再発火を strategy 内で抑止しない。Axis 5 は initial R:R こそ 2.5R だが fixed ATR TP/SL のみで、breakout tail を trailing で伸ばす構造ではない。

再設計案は 1 系統にまとめる。Trigger を `squeeze_precondition AND release_bar_closed AND actual_breakout` に変更し、BUY は `prev_close <= upper_band_prev AND signal_close > upper_band_signal` または `signal_close > rolling_high(N)`、SELL は対称条件にする。ADX は hard precondition から `adx rising OR adx >= threshold` の score/soft gate に落とし、確定済み signal bar の次 bar entry に固定する。Stop は squeeze range 反対側または ATR cap 付き swing stop、e

## Audit Redesign Recommendation 抜粋

> 思想は明確で、squeeze から volatility expansion を取る方向性自体は有効候補として残せる。ただし現行 trigger は breakout を数学的に捕捉していないため、最優先修正は Axis 2 の trigger 再定義。`bbpb > 0.75` / `< 0.25` を breakout proxy として使うのをやめ、確定足 close が BB upper/lower または squeeze range high/low を明確に抜けた時だけ signal にする。EMA9/EMA21 は hard gate として残すなら trend continuation filter、または score bonus に下げる。

# 1. 制約 (Rule R1)

- **No live promote** in this task. Shadow-stage 実装と BT 検証のみ。
- **Pre-reg LOCK** 必須: 仕様変更を `knowledge-base/wiki/decisions/` に記録してから実装。
- **365d BT 必須**: 現行版 vs proposed variant を A/B 比較。
- **WF folds >= 3, positive_ratio >= 0.67** で stable 確認。
- **Bonferroni-adjusted p < 0.05** または **Wilson lo current+0.05 以上** で有意性確認。
- **Kelly >= 0.40** が望ましい (lower bar OK if defensive narrowing)。

# 2. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/squeeze-redesign-2026-05-05.md` に:
- 現行設計の問題点 (audit Axis 引用)
- proposed variant の仕様 (具体コード差分)
- 評価軸 (BT 指標 + 合否基準)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_squeeze_redesign.py` に proposed variant の挙動テスト。

## Step 3: 実装

audit 推奨に従い変更。最小差分を優先。

## Step 4: テスト緑

## Step 5: 365d BT (現行 vs proposed)

`knowledge-base/raw/bt-results/squeeze-redesign-2026-05-05.json` に保存。

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
