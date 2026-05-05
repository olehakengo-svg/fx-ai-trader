---
id: 20260505-0105-w4-redesign-doji_breakout
title: "[W4-Redesign #1] doji_breakout (Tier 1 (LIVE)) — DESIGN/A"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T01:05:00+0900
roadmap_gate: "W4-EDA Wave 4 redesign — REDESIGN_QUEUE rank #1 (A)"
rule: R1
prereq_artifacts:
  - audits/edge_design/doji_breakout.md
  - audits/edge_design/_REDESIGN_QUEUE.md
related:
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_label_empirical_audit.md
  - audits/edge_design/streak_reversal.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/doji_breakout.md`) で **DESIGN** / 推奨度 **A** と判定。
REDESIGN_QUEUE rank **#1** (Tier 1 (LIVE))。

「思想は正、設計が誤」仮説に基づく Wave 4 一括 redesign の一環。

## Audit Axis 8 抜粋

> Tier 1 (LIVE) だが、GBP_USD は live divergence scan で BT 20/65.0%/+0.143 に対し live 3/0.0%/-8.800 と劣化し、USD_JPY も Audit B で N=7 まで低下して `insufficient` 扱いになっているため Axis 8 を適用する。破綻軸は Axis 2 と Axis 5。最大の問題は、Doji レンジ圧縮を検出しているのに breakout trigger がレンジ外 close を要求しない点で、large body candle を breakout と誤認する設計になっている。

再設計案は trigger を `BUY: bo_close > doji_high + buffer` / `SELL: bo_close < doji_low - buffer` に変更し、`buffer = max(spread, 0.1 * ATR)` 程度で false break を抑えること。加えて stop/TP は固定 TP のまま即変更せず、まず `tp = entry +/- 1.5ATR` 部分利確 + 残り trailing、または `trailing stop = breakout bar midpoint / 1ATR` の候補を shadow BT 対象にする。

## Audit Redesign Recommendation 抜粋

> 最優先の修正は trigger 1 系統。現在の `bo_body > ATR * 0.5` と candle direction は「勢いのある足」検出であって、「Doji レンジの外へ抜けた」ことを保証しない。`doji_high/doji_low` は既に計算済みなので、コードレベルでは `bo_close > doji_high + breakout_buffer` または `bo_close < doji_low - breakout_buffer` を Step 2 に追加するのが最小差分になる。

# 1. 制約 (Rule R1)

- **No live promote** in this task. Shadow-stage 実装と BT 検証のみ。
- **Pre-reg LOCK** 必須: 仕様変更を `knowledge-base/wiki/decisions/` に記録してから実装。
- **365d BT 必須**: 現行版 vs proposed variant を A/B 比較。
- **WF folds >= 3, positive_ratio >= 0.67** で stable 確認。
- **Bonferroni-adjusted p < 0.05** または **Wilson lo current+0.05 以上** で有意性確認。
- **Kelly >= 0.40** が望ましい (lower bar OK if defensive narrowing)。

# 2. Implementation Steps (TDD)

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/doji_breakout-redesign-2026-05-05.md` に:
- 現行設計の問題点 (audit Axis 引用)
- proposed variant の仕様 (具体コード差分)
- 評価軸 (BT 指標 + 合否基準)
- LOCK 日時 + 評価期限

## Step 2: 失敗テスト追加

`tests/test_doji_breakout_redesign.py` に proposed variant の挙動テスト。

## Step 3: 実装

audit 推奨に従い変更。最小差分を優先。

## Step 4: テスト緑

## Step 5: 365d BT (現行 vs proposed)

`knowledge-base/raw/bt-results/doji_breakout-redesign-2026-05-05.json` に保存。

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


## Result (2026-05-05T00:34:09Z)

exit=0 · 241s

```
完了しました。判定は **FAIL / REJECT** です。理由は proposed variant の 365d BT が両 target ともデータ取得不能で、LOCK criteria の WF / significance / Kelly を評価できなかったためです。

実施内容:
- Pre-reg LOCK 作成: [doji_breakout-redesign-2026-05-05.md](/data/repo/fx-ai-trader/knowledge-base/wiki/decisions/doji_breakout-redesign-2026-05-05.md)
- 失敗テスト追加 → 緑化: [test_doji_breakout_redesign.py](/data/repo/fx-ai-trader/tests/test_doji_breakout_redesign.py)
- proposed trigger 実装: [doji_breakout.py](/data/repo/fx-ai-trader/strategies/daytrade/doji_breakout.py:60)
  - default は現行挙動のまま
  - `require_range_close=True` または `DOJI_BREAKOUT_RANGE_CLOSE=1` の時だけ shadow proposed variant
  - `bo_close > doji_high + max(spread, 0.1ATR)` / `bo_close < doji_low - buffer`
- A/B BT runner 追加: [doji_breakout_redesign_bt.py](/data/repo/fx-ai-trader/tools/doji_breakout_redesign_bt.py)
- BT 結果保存: [doji_breakout-redesign-2026-05-05.json](/data/repo/fx-ai-trader/knowledge-base/raw/bt-results/doji_breakout-redesign-2026-05-05.json)

検証:
- `pytest tests/test_doji_breakout_redesign.py tests/test_edge_significance.py -q`
- 結果: `46 passed`
- `py_compile` も通過

BT 結果:
- `GBP_USD`: `All data sources failed for GBPUSD=X/15m; local parquet cache unavailable`
- `USD_JPY`: `All data sources failed for USDJPY=X/15m; local parquet cache unavailable`
- overall verdict: `FAIL`

Codex self-review:
- post-hoc selection: PASS
- data leakage: PASS
- look-ahead bias: PASS
- live promote: PASS

PASS ではないため **commit は作成していません**。Live 昇格もしていません。
```
