---
id: 20260505-0117-w4-redesign-mqe_gbpusd_fix
title: "[W4-Redesign #14] mqe_gbpusd_fix (Tier 2 (Shadow)) — DESIGN/A"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T01:17:00+0900
roadmap_gate: "W4-EDA Wave 4 redesign — REDESIGN_QUEUE rank #14 (A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/mqe_gbpusd_fix.md
  - audits/edge_design/_REDESIGN_QUEUE.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - audits/edge_design/streak_reversal.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/mqe_gbpusd_fix.md`) で **DESIGN** / 推奨度 **A** と判定。
REDESIGN_QUEUE rank **#14** (Tier 2 (Shadow))。

「思想は正、設計が誤」仮説に基づく Wave 4 一括 redesign の一環。

## Audit Axis 8 抜粋

> Tier 2 (Shadow) / phase0_shadow で、tier-master 365d BT EV が `—` のため昇格判断は不足だが、設計破綻は主に Axis 5、補助的に Axis 3 にある。Axis 2 は thesis を直接捕捉し、Axis 4 も generic MA/HMM filter で edge tail を潰す形ではない。破綻は「fw=6 の event reversal として検証された edge」を、実装では time stop なしの ATR bracket と 15:00-16:00 全時間発火に落としている点。

再設計案は、trigger 中核は維持しつつ、entry/timing と exit を audit 設計に合わせること。具体的には window を code comment と audit note に合わせて `15:30 <= ts.time < 16:00` に狭め、同一 `(symbol, month_end_date, fix_window)` の 1 trade/day dedup を追加する。Exit は `MAX_HOLD_BARS=6` を実行層に渡せる設計へ変更し、TP/SL 到達がなくても 6 bar で time close する。ATR bracket は保護 stop として残すなら、TP は固定 1.5ATR ではなく、fw=6 の observed move distribution または time-close を主 exit にする。

## Audit Redesign Recommendation 抜粋

> 思想と trigger は有効候補。GBPUSD 月末 London fix fade はコード内 thesis と既存 `mqe_audit` の Bonferroni 通過が一致しており、棄却対象ではない。再設計の中心は trigger 条件を作り直すことではなく、検証された horizon と live 実装の exit/timing を一致させること。

# 1. 制約 (Rule R1)

- **No live promote** in this task. Shadow-stage 実装と BT 検証のみ。
- **Pre-reg LOCK** 必須: 仕様変更を `knowledge-base/wiki/decisions/` に記録してから実装。
- **365d BT 必須**: 現行版 vs proposed variant を A/B 比較。
- **WF folds >= 3, positive_ratio >= 0.67** で stable 確認。
- **Bonferroni-adjusted p < 0.05** または **Wilson lo current+0.05 以上** で有意性確認。
- **Kelly >= 0.40** が望ましい (lower bar OK if defensive narrowing)。

# 2. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/mqe_gbpusd_fix-redesign-2026-05-05.md` に:
- 現行設計の問題点 (audit Axis 引用)
- proposed variant の仕様 (具体コード差分)
- 評価軸 (BT 指標 + 合否基準)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_mqe_gbpusd_fix_redesign.py` に proposed variant の挙動テスト。

## Step 3: 実装

audit 推奨に従い変更。最小差分を優先。

## Step 4: テスト緑

## Step 5: 365d BT (現行 vs proposed)

`knowledge-base/raw/bt-results/mqe_gbpusd_fix-redesign-2026-05-05.json` に保存。

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
