---
id: 20260505-0303-w4-redesign-insufN-tvsm
title: "[W4-Redesign INSUFFICIENT_N] tvsm (Tier 2 (Shadow)) — design fix despite low N"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T03:03:00+0900
roadmap_gate: "W4 redesign — N不足を理由に除外していた 5 件の補完バッチ。設計欠陥があれば N に関係なく fix し、shadow で N 蓄積する正しい順序"
rule: R1
prereq_artifacts:
  - audits/edge_design/tvsm.md
related:
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
---

# 0. なぜこのタスクか

W4-EDA audit は **「設計が正しいか」** の検証。N 不足は採否ではなく shadow 期間延長で解決すべき問題で、**設計欠陥がある場合は N に関係なく修正する** のが正しい順序 (user feedback 2026-05-05)。

`audits/edge_design/tvsm.md` の verdict は `THESIS_VALID_INSUFFICIENT_EVIDENCE` だが、Rec=A の **明確な再設計提案** がある。N 不足を理由に redesign を保留するのではなく、修正してから shadow で N 蓄積する。

## Audit Axis 8 抜粋

> Tier 2 (Shadow) / phase0_shadow で Tier 3/4 ではないが、入力 metric は 365d BT EV `—` で、audit DB に exact `tvsm` row もないため under-evidenced shadow cell として failure mode を診断する。破綻軸は Axis 2/3/4/5 ではなく Axis 7。設計上は momentum thesis、2 秒 confirmation、cost-aware SL、R:R gate が整合している一方、`ALL` pair に広げる実証根拠がない。

再設計案は、trigger 自体を大きく変えるより先に pair-regime/timing filter を 1 系統追加すること。具体的には `evaluate()` の前段または caller 側で、major pair whitelist、London/NY open など tick density の高い時間帯、`ATR/spread` または `ATR/entry_slip` の下限を同時に満たす時だけ TVSM を評価し、その限定 universe で 30d/365d 実 tick BT を作る。新規 BT は本 audit では実行しない。

## Audit Redesign Recommendation 抜粋

> 現行の中核 trigger は維持する。変更候補は trigger 条件そのものではなく、entry universe を「tick_volume shock が観測可能で、retail latency/cost を吸収できる pair-session-regime」に限定する timing/filter redesign である。コードレベルでは `z_spike >= spike_z` と同方向 2-bar confirmation の前に、pair whitelist と session gate、さらに `atr >= k * entry_slip_price` または `ATR/spread >= threshold` を追加する設計が妥当。

# 1. 制約 (Rule 1)

- 設計修正は最小差分 (audit が単一軸 fix を推奨)
- Pre-reg LOCK 必須
- 365d BT 比較 (現行 vs proposed)
- WF folds>=3 で stable 確認 (N 不足なら BT も低 N になり得る → "結果が positive 方向で safe" を確認)
- N 不足のままでも修正は実装する（shadow で N 蓄積開始が次フェーズ）
- Live 昇格 = 別タスク

# 2. Implementation Steps

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/tvsm-redesign-insufN-2026-05-05.md`:
- 現行 vs proposed の差分
- LOCK criteria (positive direction + no regression)
- N 蓄積期間目標 (例: shadow 30 trades or 60 days)

## Step 2: 失敗テスト追加

`tests/test_tvsm_redesign_insufN.py`

## Step 3: 実装 (audit 推奨に従い最小差分)

## Step 4: テスト緑

## Step 5: 365d BT 比較

`knowledge-base/raw/bt-results/tvsm-redesign-insufN-2026-05-05.json`

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
