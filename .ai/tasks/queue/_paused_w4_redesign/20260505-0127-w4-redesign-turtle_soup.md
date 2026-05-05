---
id: 20260505-0127-w4-redesign-turtle_soup
title: "[W4-Redesign #24] turtle_soup (Tier 2 (Shadow)) — TIMING/A"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T01:27:00+0900
roadmap_gate: "W4-EDA Wave 4 redesign — REDESIGN_QUEUE rank #24 (A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/turtle_soup.md
  - audits/edge_design/_REDESIGN_QUEUE.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - audits/edge_design/streak_reversal.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/turtle_soup.md`) で **TIMING** / 推奨度 **A** と判定。
REDESIGN_QUEUE rank **#24** (Tier 2 (Shadow))。

「思想は正、設計が誤」仮説に基づく Wave 4 一括 redesign の一環。

## Audit Axis 8 抜粋

> Tier 2 (Shadow) だが、latest audit aggregate は N=1 / WR=0% / PF=0 / Bonferroni p=1.0000 で、tier-master 365d BT EV も `—`。したがって under-evidenced shadow かつ latest metric deteriorated として failure mode 診断対象にする。

破綻軸は Axis 3 と Axis 6/7。Axis 2 の trigger は sweep + reclaim を数学的に捉えており、Axis 4 の ADX/time/pair filters は thesis を明確には破壊していない。Axis 5 も sweep extreme 外側 SL と対面 fractal TP で概ね整合する。主問題は、current bar の reclaim をそのまま signal 化する一方で closed-bar / next-bar execution / dedup 契約が strategy 内にないこと、そして tier cell が `ALL` なのに code scope は GBPUSD/XAUUSD/EURGBP へ狭く、現行 audit evidence がその scope を支えていないこと。

再設計案は timing hardening を第一優先にする。`_detect_sweep_and_reclaim()` の `cur_*` を確定 signal bar、entry を次 bar execution として分離し、Candidate 生成時または dispatcher で `(symbol, entry_type, signal, signal_bar_time)` の 1 bar 1 emit を保証

## Audit Redesign Recommendation 抜粋

> 思想と trigger は明確で、旧 GBPUSD BT/WF には復活候補として見るだけの参考値があるため棄却しない。修正優先度は timing 1 系統で、closed-bar 化、next-bar execution、per-bar dedup を入れるだけで現行 thesis を保ったまま検証できる。

# 1. 制約 (Rule R1)

- **No live promote** in this task. Shadow-stage 実装と BT 検証のみ。
- **Pre-reg LOCK** 必須: 仕様変更を `knowledge-base/wiki/decisions/` に記録してから実装。
- **365d BT 必須**: 現行版 vs proposed variant を A/B 比較。
- **WF folds >= 3, positive_ratio >= 0.67** で stable 確認。
- **Bonferroni-adjusted p < 0.05** または **Wilson lo current+0.05 以上** で有意性確認。
- **Kelly >= 0.40** が望ましい (lower bar OK if defensive narrowing)。

# 2. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/turtle_soup-redesign-2026-05-05.md` に:
- 現行設計の問題点 (audit Axis 引用)
- proposed variant の仕様 (具体コード差分)
- 評価軸 (BT 指標 + 合否基準)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_turtle_soup_redesign.py` に proposed variant の挙動テスト。

## Step 3: 実装

audit 推奨に従い変更。最小差分を優先。

## Step 4: テスト緑

## Step 5: 365d BT (現行 vs proposed)

`knowledge-base/raw/bt-results/turtle_soup-redesign-2026-05-05.json` に保存。

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
