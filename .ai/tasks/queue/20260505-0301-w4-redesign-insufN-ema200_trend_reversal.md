---
id: 20260505-0301-w4-redesign-insufN-ema200_trend_reversal
title: "[W4-Redesign INSUFFICIENT_N] ema200_trend_reversal (Tier 1 (LIVE)) — design fix despite low N"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T03:01:00+0900
roadmap_gate: "W4 redesign — N不足を理由に除外していた 5 件の補完バッチ。設計欠陥があれば N に関係なく fix し、shadow で N 蓄積する正しい順序"
rule: R1
prereq_artifacts:
  - audits/edge_design/ema200_trend_reversal.md
related:
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
---

# 0. なぜこのタスクか

W4-EDA audit は **「設計が正しいか」** の検証。N 不足は採否ではなく shadow 期間延長で解決すべき問題で、**設計欠陥がある場合は N に関係なく修正する** のが正しい順序 (user feedback 2026-05-05)。

`audits/edge_design/ema200_trend_reversal.md` の verdict は `THESIS_VALID_INSUFFICIENT_EVIDENCE` だが、Rec=A の **明確な再設計提案** がある。N 不足を理由に redesign を保留するのではなく、修正してから shadow で N 蓄積する。

## Audit Axis 8 抜粋

> Tier 1 (LIVE) かつ pair_promoted だが、BT 365d 側は USDJPY 負 EV / PF<1 の記録があり、直近 R2 cell demotion lock でも hour 17/20 の小 N loss が WATCH、hour 13 の N=1 win が KEEP という粒度に分解されている。Axis 2/3/5 のコード設計は thesis と整合しており、破綻は trigger 数式そのものではない。失敗候補は Axis 4 の「必要な timing/session filter がコードにない」点と Axis 7 の decision-grade evidence 不足。

再設計案: trigger と R:R は維持し、USDJPY の live routing を暫定的に Overlap/NY-overlap 相当の `12 <= ctx.hour_utc < 16` に絞る timing filter を追加する。昇格根拠が Overlap N=7, WR=100%, EV_cost=+11.63p に集中しているため、全時間帯に同じ EMA200 retest thesis を強制するより、session-gated pullback として再定義して shadow / micro-live で N>=30 を蓄積する。

## Audit Redesign Recommendation 抜粋

> 最小の再設計は timing filter 1 系統。`evaluate()` の冒頭または `_crosses` 通過後に USDJPY pair-promoted 用の session gate を置き、`ctx.hour_utc` が Overlap/NY-overlap 外なら `return None` にする案が最も小さい。これにより、EMA200 retest trigger / MACD再加速 / 2:1 R:R は維持したまま、昇格根拠のある時間帯だけを live 対象にできる。

# 1. 制約 (Rule 1)

- 設計修正は最小差分 (audit が単一軸 fix を推奨)
- Pre-reg LOCK 必須
- 365d BT 比較 (現行 vs proposed)
- WF folds>=3 で stable 確認 (N 不足なら BT も低 N になり得る → "結果が positive 方向で safe" を確認)
- N 不足のままでも修正は実装する（shadow で N 蓄積開始が次フェーズ）
- Live 昇格 = 別タスク

# 2. Implementation Steps

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/ema200_trend_reversal-redesign-insufN-2026-05-05.md`:
- 現行 vs proposed の差分
- LOCK criteria (positive direction + no regression)
- N 蓄積期間目標 (例: shadow 30 trades or 60 days)

## Step 2: 失敗テスト追加

`tests/test_ema200_trend_reversal_redesign_insufN.py`

## Step 3: 実装 (audit 推奨に従い最小差分)

## Step 4: テスト緑

## Step 5: 365d BT 比較

`knowledge-base/raw/bt-results/ema200_trend_reversal-redesign-insufN-2026-05-05.json`

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
