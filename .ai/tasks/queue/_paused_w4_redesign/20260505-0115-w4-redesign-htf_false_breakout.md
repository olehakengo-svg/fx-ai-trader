---
id: 20260505-0115-w4-redesign-htf_false_breakout
title: "[W4-Redesign #12] htf_false_breakout (Tier 2 (Shadow)) — DESIGN/A"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T01:15:00+0900
roadmap_gate: "W4-EDA Wave 4 redesign — REDESIGN_QUEUE rank #12 (A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/htf_false_breakout.md
  - audits/edge_design/_REDESIGN_QUEUE.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - audits/edge_design/streak_reversal.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/htf_false_breakout.md`) で **DESIGN** / 推奨度 **A** と判定。
REDESIGN_QUEUE rank **#12** (Tier 2 (Shadow))。

「思想は正、設計が誤」仮説に基づく Wave 4 一括 redesign の一環。

## Audit Axis 8 抜粋

> Tier 2 Shadow だが、既存 evidence は N=1 の小標本で、phase0_shadow のまま昇格判断に耐えない。破綻軸は Axis 2 と Axis 3。思想は false breakout fade として明確だが、実装は 1H close breakout を数学的に作らず、15m 単体 close を疑似 1H として扱っている。さらに SR slice が breakout 候補 bar を混ぜるため、breakout 検出窓がコメント通りの 1-4本確認になっていない。

再設計案は、trigger/timing を一体で直すこと。15m df から明示的に 1H OHLC を resample/aggregate し、SR は breakout 1H bar より前の 20本だけで計算する。その後、breakout 1H bar の close が SR 外へ出たことを state として保持し、次の 1-4本の closed 15m bar で SR 内へ戻った最初の close だけを entry signal とする。ALL 運用ではなく、既存 WF が安定している GBP_JPY/EUR_JPY を優先 shadow cell に絞り、GBP_USD/EUR_USD/USD_JPY は redesign 後 BT で再判定する。

## Audit Redesign Recommendation 抜粋

> Trigger/timing の 1 系統修正で復活余地がある。具体的には、`_sr_slice` を現在時点基準ではなく breakout 候補 1H bar 基準に変更し、`for _offset in range(...)` で 15m 単体 bar を見る処理を廃止する。想定 diff は、1H resample 済み series から `break_h1 = h1.iloc[-2]` などの closed H1 bar を選び、`sr_high/low = h1.iloc[-22:-2].High/Low` のように breakout bar を含めない窓で計算し、15m re-entry は breakout 後の closed 15m bars のみを対象にする形。

# 1. 制約 (Rule R1)

- **No live promote** in this task. Shadow-stage 実装と BT 検証のみ。
- **Pre-reg LOCK** 必須: 仕様変更を `knowledge-base/wiki/decisions/` に記録してから実装。
- **365d BT 必須**: 現行版 vs proposed variant を A/B 比較。
- **WF folds >= 3, positive_ratio >= 0.67** で stable 確認。
- **Bonferroni-adjusted p < 0.05** または **Wilson lo current+0.05 以上** で有意性確認。
- **Kelly >= 0.40** が望ましい (lower bar OK if defensive narrowing)。

# 2. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/htf_false_breakout-redesign-2026-05-05.md` に:
- 現行設計の問題点 (audit Axis 引用)
- proposed variant の仕様 (具体コード差分)
- 評価軸 (BT 指標 + 合否基準)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_htf_false_breakout_redesign.py` に proposed variant の挙動テスト。

## Step 3: 実装

audit 推奨に従い変更。最小差分を優先。

## Step 4: テスト緑

## Step 5: 365d BT (現行 vs proposed)

`knowledge-base/raw/bt-results/htf_false_breakout-redesign-2026-05-05.json` に保存。

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
