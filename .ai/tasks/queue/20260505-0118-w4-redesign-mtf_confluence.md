---
id: 20260505-0118-w4-redesign-mtf_confluence
title: "[W4-Redesign #15] mtf_confluence (Tier 2 (Shadow)) — DESIGN/A"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T01:18:00+0900
roadmap_gate: "W4-EDA Wave 4 redesign — REDESIGN_QUEUE rank #15 (A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/mtf_confluence.md
  - audits/edge_design/_REDESIGN_QUEUE.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - audits/edge_design/streak_reversal.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/mtf_confluence.md`) で **DESIGN** / 推奨度 **A** と判定。
REDESIGN_QUEUE rank **#15** (Tier 2 (Shadow))。

「思想は正、設計が誤」仮説に基づく Wave 4 一括 redesign の一環。

## Audit Axis 8 抜粋

> Tier 2 (Shadow) だが、tier-master 365d BT EV が `—` で、既存集計も N=10 / Bonferroni p=1.0000 / WF folds 欠落のため、metrics 劣化または under-evidenced shadow として failure mode を診断する。

破綻軸は Axis 3 と Axis 5。Axis 2 の trigger は MTF RSI extreme + MACD-H/Stoch 反転で MR thesis と整合し、Axis 4 の filter も hard gate で edge tail を消す構造は明確ではない。主問題は、strategy file 内に closed-bar/dedup の担保がなく intrabar 多重 emit リスクがあることと、MR なのに 0.5ATR stop / 1.5ATR TP の tight-stop 3R geometry を採用していること。

再設計案は、まず signal 判定を確定足に寄せ、同一 `(instrument, strategy, bar_time, signal)` の再 emit を禁止する。次に TP/SL を MR 形状へ反転し、例として `sl_mult` を 1.0-1.5ATR、`tp_mult` を 0.6-1.0ATR または BB/EMA mean 到達ベースへ変更する。MACD-H/Stoch は entry の瞬間確認として残し、TP は「平均へ戻ったら利確」、SL は「MTF RSI thesis が否定される深い伸び」で切る形にする。

## Audit Redesign Recommendation 抜粋

> 思想は明確で、trigger も MR と整合しているため棄却しない。修正優先度は stop/TP geometry と timing の 2 点だが、どちらも戦略思想を変えずに実装可能なため `A` とする。

# 1. 制約 (Rule R1)

- **No live promote** in this task. Shadow-stage 実装と BT 検証のみ。
- **Pre-reg LOCK** 必須: 仕様変更を `knowledge-base/wiki/decisions/` に記録してから実装。
- **365d BT 必須**: 現行版 vs proposed variant を A/B 比較。
- **WF folds >= 3, positive_ratio >= 0.67** で stable 確認。
- **Bonferroni-adjusted p < 0.05** または **Wilson lo current+0.05 以上** で有意性確認。
- **Kelly >= 0.40** が望ましい (lower bar OK if defensive narrowing)。

# 2. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/mtf_confluence-redesign-2026-05-05.md` に:
- 現行設計の問題点 (audit Axis 引用)
- proposed variant の仕様 (具体コード差分)
- 評価軸 (BT 指標 + 合否基準)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_mtf_confluence_redesign.py` に proposed variant の挙動テスト。

## Step 3: 実装

audit 推奨に従い変更。最小差分を優先。

## Step 4: テスト緑

## Step 5: 365d BT (現行 vs proposed)

`knowledge-base/raw/bt-results/mtf_confluence-redesign-2026-05-05.json` に保存。

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
