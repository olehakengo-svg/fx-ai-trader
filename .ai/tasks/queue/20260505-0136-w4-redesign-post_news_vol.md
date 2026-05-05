---
id: 20260505-0136-w4-redesign-post_news_vol
title: "[W4-Redesign #33] post_news_vol (Tier 3 (FORCE_DEMOTED)) — DESIGN/A"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T01:36:00+0900
roadmap_gate: "W4-EDA Wave 4 redesign — REDESIGN_QUEUE rank #33 (A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/post_news_vol.md
  - audits/edge_design/_REDESIGN_QUEUE.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - audits/edge_design/streak_reversal.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/post_news_vol.md`) で **DESIGN** / 推奨度 **A** と判定。
REDESIGN_QUEUE rank **#33** (Tier 3 (FORCE_DEMOTED))。

「思想は正、設計が誤」仮説に基づく Wave 4 一括 redesign の一環。

## Audit Axis 8 抜粋

> Tier 3 (FORCE_DEMOTED) としての破綻軸は Axis 2 / 3 / 5、補助的に Axis 4。思想はコードから明確に導出でき、post-news volatility continuation 自体は tier-master / WF の一部で支持されるが、現行 trigger は「news後」ではなく「任意のATR spike後」を拾う。さらに current bar の follow-through を直接読むため bar-close / next-bar execution / dedup 契約が弱く、出口は fixed TP で post-news run の右尾を伸ばせない。

再設計案は v2 を event-window + closed-bar continuation + trailing geometry に分離すること。具体的には `event_window = high_impact_calendar_event within [-5m,+45m]` を spike trigger の必須条件にし、signal は `df.iloc[-2]` の確定 follow bar で `close[-2] > spike_close + buffer` / `< spike_close - buffer` を判定、execution は次 bar の `ctx.entry` に分離する。ADX は `ADX_MIN` のみ残すか `ADX_MAX` を削除し、tail を落とす gate を避ける。

## Audit Redesign Recommendation 抜粋

> 思想は明確で、volatility spike + follow-through という trigger 骨格も momentum continuation を捕捉している。ただし `post_news` の中核条件が実装されていないため、最優先修正は trigger の event-window 化である。`_find_spike_bars()` の前段または `evaluate()` 冒頭に high-impact economic calendar gate を追加し、calendar がない場合は `post_news_vol` ではなく `generic_vol_spike_followthrough` として別戦略に分離するのが筋が良い。

# 1. 制約 (Rule R1)

- **No live promote** in this task. Shadow-stage 実装と BT 検証のみ。
- **Pre-reg LOCK** 必須: 仕様変更を `knowledge-base/wiki/decisions/` に記録してから実装。
- **365d BT 必須**: 現行版 vs proposed variant を A/B 比較。
- **WF folds >= 3, positive_ratio >= 0.67** で stable 確認。
- **Bonferroni-adjusted p < 0.05** または **Wilson lo current+0.05 以上** で有意性確認。
- **Kelly >= 0.40** が望ましい (lower bar OK if defensive narrowing)。

# 2. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/post_news_vol-redesign-2026-05-05.md` に:
- 現行設計の問題点 (audit Axis 引用)
- proposed variant の仕様 (具体コード差分)
- 評価軸 (BT 指標 + 合否基準)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_post_news_vol_redesign.py` に proposed variant の挙動テスト。

## Step 3: 実装

audit 推奨に従い変更。最小差分を優先。

## Step 4: テスト緑

## Step 5: 365d BT (現行 vs proposed)

`knowledge-base/raw/bt-results/post_news_vol-redesign-2026-05-05.json` に保存。

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
