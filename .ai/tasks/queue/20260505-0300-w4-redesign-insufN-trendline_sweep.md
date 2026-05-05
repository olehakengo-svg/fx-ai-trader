---
id: 20260505-0300-w4-redesign-insufN-trendline_sweep
title: "[W4-Redesign INSUFFICIENT_N] trendline_sweep (Tier 1 (LIVE)) — design fix despite low N"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T03:00:00+0900
roadmap_gate: "W4 redesign — N不足を理由に除外していた 5 件の補完バッチ。設計欠陥があれば N に関係なく fix し、shadow で N 蓄積する正しい順序"
rule: R1
prereq_artifacts:
  - audits/edge_design/trendline_sweep.md
related:
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
---

# 0. なぜこのタスクか

W4-EDA audit は **「設計が正しいか」** の検証。N 不足は採否ではなく shadow 期間延長で解決すべき問題で、**設計欠陥がある場合は N に関係なく修正する** のが正しい順序 (user feedback 2026-05-05)。

`audits/edge_design/trendline_sweep.md` の verdict は `THESIS_VALID_INSUFFICIENT_EVIDENCE` だが、Rec=A の **明確な再設計提案** がある。N 不足を理由に redesign を保留するのではなく、修正してから shadow で N 蓄積する。

## Audit Axis 8 抜粋

> Tier 1 LIVE だが、直近監査 metrics は劣化しているため Axis 8 を適用する。Axis 2/3/4/5 のコード設計そのものは破綻していない。破綻箇所は Axis 7 の evidence 不足と Axis 6 の `ALL` live scope で、特に EURGBP/XAUUSD まで elite_live として扱うには、この task の入力と audit DB から Wilson/PF/Kelly が確認できない。

再設計案: trigger/timing/stop は維持し、live routing scope を「tier-master と WF で根拠がある EURUSD / GBPUSD」に限定する。EURGBP/XAUUSD は SELL-only のまま shadow に落とし、N>=30 かつ Wilson lo / PF / Bonferroni / Kelly が揃うまで elite_live の `ALL` 扱いから外す。

## Audit Redesign Recommendation 抜粋

> コードレベルでは `_detect_sweep_reclaim()` の条件式や SL/TP geometry は変えない。変更候補は routing/pair filter のみで、`ALLOWED_PAIRS` または live 側 tier routing を EURUSD / GBPUSD に縮小し、EURGBP / XAUUSD は shadow evidence collection に戻す。これは thesis 修正ではなく、evidence のない pair-regime exposure を切る防御的な設計変更である。

# 1. 制約 (Rule 1)

- 設計修正は最小差分 (audit が単一軸 fix を推奨)
- Pre-reg LOCK 必須
- 365d BT 比較 (現行 vs proposed)
- WF folds>=3 で stable 確認 (N 不足なら BT も低 N になり得る → "結果が positive 方向で safe" を確認)
- N 不足のままでも修正は実装する（shadow で N 蓄積開始が次フェーズ）
- Live 昇格 = 別タスク

# 2. Implementation Steps

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/trendline_sweep-redesign-insufN-2026-05-05.md`:
- 現行 vs proposed の差分
- LOCK criteria (positive direction + no regression)
- N 蓄積期間目標 (例: shadow 30 trades or 60 days)

## Step 2: 失敗テスト追加

`tests/test_trendline_sweep_redesign_insufN.py`

## Step 3: 実装 (audit 推奨に従い最小差分)

## Step 4: テスト緑

## Step 5: 365d BT 比較

`knowledge-base/raw/bt-results/trendline_sweep-redesign-insufN-2026-05-05.json`

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
