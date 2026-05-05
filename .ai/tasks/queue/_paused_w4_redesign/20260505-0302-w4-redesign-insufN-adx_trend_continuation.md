---
id: 20260505-0302-w4-redesign-insufN-adx_trend_continuation
title: "[W4-Redesign INSUFFICIENT_N] adx_trend_continuation (Tier 2 (Shadow)) — design fix despite low N"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T03:02:00+0900
roadmap_gate: "W4 redesign — N不足を理由に除外していた 5 件の補完バッチ。設計欠陥があれば N に関係なく fix し、shadow で N 蓄積する正しい順序"
rule: R1
prereq_artifacts:
  - audits/edge_design/adx_trend_continuation.md
related:
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
---

# 0. なぜこのタスクか

W4-EDA audit は **「設計が正しいか」** の検証。N 不足は採否ではなく shadow 期間延長で解決すべき問題で、**設計欠陥がある場合は N に関係なく修正する** のが正しい順序 (user feedback 2026-05-05)。

`audits/edge_design/adx_trend_continuation.md` の verdict は `THESIS_VALID_INSUFFICIENT_EVIDENCE` だが、Rec=A の **明確な再設計提案** がある。N 不足を理由に redesign を保留するのではなく、修正してから shadow で N 蓄積する。

## Audit Axis 8 抜粋

> Tier 2 (Shadow) であり Tier 3/4 ではないが、phase0_shadow かつ empirical evidence が N=1 / tier-master EV `—` のため、昇格候補としての failure mode を診断する。

破綻候補は Axis 2/4/5 ではなく、Axis 3 と Axis 6/7。思想と trigger は整合しており、filter も momentum thesis を破壊していない。問題は、strategy 内で closed-bar / per-bar dedup が保証されず、現在足の `ctx.entry` と high/low 依存の geometry をそのまま使う点、さらに `ALL` cell として dispatch されているのに実装は EURUSD 専用である点、そして Wilson / PF / WF / Bonferroni / Kelly が decision-grade に不足している点。

再設計案は timing hardening と scope 明示の 2 点。まず trigger 判定を closed bar に固定し、`bar_id = ctx.bar_time or ctx.df.index[-1]` を使った `(symbol, signal, bar_id)` dedup を strategy または dispatch 層で必ず通す。次に audit / tier-master 上の cell を `ALL` ではなく `EURUSD` に切り、USDJPY/GBPUSD/EURGBP はコードコメントどおり BLOCKED として扱う。そのうえで EURUSD 365d + WF folds>=3 の既存ハーネス集計を取り直し、Wilson lower / PF

## Audit Redesign Recommendation 抜粋

> 思想は明確で、trigger/filter/stop は概ね整合しているため棄却ではない。最小の実装方針は、現在の ADX/DI/EMA/pullback/rebound 条件を維持したまま、signal を closed-bar 化し、同一 `(symbol, signal, bar_id)` の再 emit を禁止する timing guard を追加すること。具体的には現在足を confirmation bar とするなら、その bar が確定済みであることを実行層から `ctx.backtest_mode` / `ctx.bar_time` で保証し、live intrabar では `return None` にする。

# 1. 制約 (Rule 1)

- 設計修正は最小差分 (audit が単一軸 fix を推奨)
- Pre-reg LOCK 必須
- 365d BT 比較 (現行 vs proposed)
- WF folds>=3 で stable 確認 (N 不足なら BT も低 N になり得る → "結果が positive 方向で safe" を確認)
- N 不足のままでも修正は実装する（shadow で N 蓄積開始が次フェーズ）
- Live 昇格 = 別タスク

# 2. Implementation Steps

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/adx_trend_continuation-redesign-insufN-2026-05-05.md`:
- 現行 vs proposed の差分
- LOCK criteria (positive direction + no regression)
- N 蓄積期間目標 (例: shadow 30 trades or 60 days)

## Step 2: 失敗テスト追加

`tests/test_adx_trend_continuation_redesign_insufN.py`

## Step 3: 実装 (audit 推奨に従い最小差分)

## Step 4: テスト緑

## Step 5: 365d BT 比較

`knowledge-base/raw/bt-results/adx_trend_continuation-redesign-insufN-2026-05-05.json`

## Step 6: LOCK criteria 判定

PASS → shadow promote 提案（実装は merge、N 蓄積開始）
FAIL → REJECT + 原因分析

## Step 7: Codex adversarial review

# 3. Acceptance

- Pre-reg LOCK doc あり
- 失敗テスト → 緑
- BT 比較レポート (低 N でも positive direction なら OK)
- LOCK criteria 判定
- N 蓄積目標明示

# 4. Out of Scope

- N 蓄積のための新規 BT データ生成 (本タスクは現行 BT データで判定)
- Live 昇格
- 他 strategies

# 5. Notes

- このタスクは「設計監査の結論を N 不足で握りつぶさない」ためのフォロー dispatch。
- 修正後は shadow で N 蓄積、その後 N>=30 で promote 判断 (Rule 1 後段)。
- BT が低 N の場合は "regression なし" を確認できれば pass。
