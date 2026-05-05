---
id: 20260505-0143-w4-redesign-mtf_regime_trend_cascade_scalp
title: "[W4-Redesign #40] mtf_regime_trend_cascade_scalp (Tier 4 (SCALP_SENTINEL)) — DESIGN/A"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T01:43:00+0900
roadmap_gate: "W4-EDA Wave 4 redesign — REDESIGN_QUEUE rank #40 (A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/mtf_regime_trend_cascade_scalp.md
  - audits/edge_design/_REDESIGN_QUEUE.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - audits/edge_design/streak_reversal.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/mtf_regime_trend_cascade_scalp.md`) で **DESIGN** / 推奨度 **A** と判定。
REDESIGN_QUEUE rank **#40** (Tier 4 (SCALP_SENTINEL))。

「思想は正、設計が誤」仮説に基づく Wave 4 一括 redesign の一環。

## Audit Axis 8 抜粋

> Tier 4 (SCALP_SENTINEL) なので failure mode 診断対象。主破綻軸は Axis 3 と Axis 5。Axis 2 は trend/pullback/bounce を数学的に捕捉しており PASS、Axis 4 も thesis と filter の方向性は概ね整合する。ただし現在足依存の 1m bounce 判定と bar dedup 欠落により、未確定足の一時的な EMA21 反発を signal 化するリスクがある。さらに stop/TP は trend continuation に対して固定 swing / RR 1.3 floor で、勝ちを伸ばす設計が弱い。

再設計案は、trigger の思想を維持したまま timing と exit geometry を変えること。BUY/SELL trigger は `df.iloc[-2]` の確定 1m 足で判定し、entry は次 bar open または確定足 close 後の execution に分離する。`signal_bar_time` を Candidate reason または実行層 key に渡し、`(symbol, strategy, signal, signal_bar_time)` dedup を必須にする。

Stop/TP は `SL = pullback swing +/- buffer` または `EMA21 +/- max(0.5ATR, spread-adjusted floor)` に整理し、TP は固定 swing 到達だけで終わらせず、半分を `1.0R-1.3R`、残りを M5 EMA/SMA trailing または `2.0R` まで伸ばす variant を検証する。現行 180d evidence は PF=0.741/OOS PF=

## Audit Redesign Recommendation 抜粋

> 思想は有効候補として残す。M15 moderate trend、H1 macro direction、M5 pullback、1m bounce という cascade はコードから一貫しており、trigger mismatch や MR に MA filter を被せる型の破壊ではない。一方で、現在足依存の bounce 判定と dedup 欠落、trend continuation に対して浅い固定 RR geometry が、Tier 4 に落ちた現行設計の具体的な破綻候補。

# 1. 制約 (Rule R1)

- **No live promote** in this task. Shadow-stage 実装と BT 検証のみ。
- **Pre-reg LOCK** 必須: 仕様変更を `knowledge-base/wiki/decisions/` に記録してから実装。
- **365d BT 必須**: 現行版 vs proposed variant を A/B 比較。
- **WF folds >= 3, positive_ratio >= 0.67** で stable 確認。
- **Bonferroni-adjusted p < 0.05** または **Wilson lo current+0.05 以上** で有意性確認。
- **Kelly >= 0.40** が望ましい (lower bar OK if defensive narrowing)。

# 2. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/mtf_regime_trend_cascade_scalp-redesign-2026-05-05.md` に:
- 現行設計の問題点 (audit Axis 引用)
- proposed variant の仕様 (具体コード差分)
- 評価軸 (BT 指標 + 合否基準)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_mtf_regime_trend_cascade_scalp_redesign.py` に proposed variant の挙動テスト。

## Step 3: 実装

audit 推奨に従い変更。最小差分を優先。

## Step 4: テスト緑

## Step 5: 365d BT (現行 vs proposed)

`knowledge-base/raw/bt-results/mtf_regime_trend_cascade_scalp-redesign-2026-05-05.json` に保存。

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
