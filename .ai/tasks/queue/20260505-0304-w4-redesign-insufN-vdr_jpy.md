---
id: 20260505-0304-w4-redesign-insufN-vdr_jpy
title: "[W4-Redesign INSUFFICIENT_N] vdr_jpy (Tier 2 (Shadow)) — design fix despite low N"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T03:04:00+0900
roadmap_gate: "W4 redesign — N不足を理由に除外していた 5 件の補完バッチ。設計欠陥があれば N に関係なく fix し、shadow で N 蓄積する正しい順序"
rule: R1
prereq_artifacts:
  - audits/edge_design/vdr_jpy.md
related:
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
---

# 0. なぜこのタスクか

W4-EDA audit は **「設計が正しいか」** の検証。N 不足は採否ではなく shadow 期間延長で解決すべき問題で、**設計欠陥がある場合は N に関係なく修正する** のが正しい順序 (user feedback 2026-05-05)。

`audits/edge_design/vdr_jpy.md` の verdict は `THESIS_VALID_INSUFFICIENT_EVIDENCE` だが、Rec=A の **明確な再設計提案** がある。N 不足を理由に redesign を保留するのではなく、修正してから shadow で N 蓄積する。

## Audit Axis 8 抜粋

> `vdr_jpy` は Tier 2 (Shadow) / phase0_shadow。Axis 2 の VWAP deviation trigger、Axis 4 の JPY pair gate、Axis 5 の VWAP target geometry は thesis と概ね整合している。破綻候補は Axis 3 と Axis 7。コード上は反転 candle close 待ちで entry が遅れやすく、`MAX_HOLD_BARS = 4` が Candidate contract に載っていないため、raw audit の forward-bar edge を live execution に固定できていない。

再設計案は trigger/timing の一系統修正。まず pair-specific parameter を導入し、USDJPY は raw best に合わせて `DEV_SIGMA_THRESHOLD=2.0` と `forward_bars=2` 相当の time exit、EURJPY/GBPJPY は `DEV_SIGMA_THRESHOLD=1.5` を維持する variant を pre-register する。次に candle confirmation を hard gate から score penalty/bonus へ落とし、乖離成立 bar close で entry できる variant と、反転確認 bar close variant を分けて既存 audit DB に PF/WF/Kelly 付きで再検証する。

## Audit Redesign Recommendation 抜粋

> 思想と主要 trigger は残す。`dev_atr = (entry - vwap) / atr` と `signal = -sign(dev_atr)` は VWAP deviation reversion を直接表しており、MA/HMM 型 filter が thesis を壊している形跡もない。

# 1. 制約 (Rule 1)

- 設計修正は最小差分 (audit が単一軸 fix を推奨)
- Pre-reg LOCK 必須
- 365d BT 比較 (現行 vs proposed)
- WF folds>=3 で stable 確認 (N 不足なら BT も低 N になり得る → "結果が positive 方向で safe" を確認)
- N 不足のままでも修正は実装する（shadow で N 蓄積開始が次フェーズ）
- Live 昇格 = 別タスク

# 2. Implementation Steps

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/vdr_jpy-redesign-insufN-2026-05-05.md`:
- 現行 vs proposed の差分
- LOCK criteria (positive direction + no regression)
- N 蓄積期間目標 (例: shadow 30 trades or 60 days)

## Step 2: 失敗テスト追加

`tests/test_vdr_jpy_redesign_insufN.py`

## Step 3: 実装 (audit 推奨に従い最小差分)

## Step 4: テスト緑

## Step 5: 365d BT 比較

`knowledge-base/raw/bt-results/vdr_jpy-redesign-insufN-2026-05-05.json`

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
