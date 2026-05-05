---
id: 20260505-1102-w4-meta-B-streak-reversal-same-estimand-rebt
title: "[W4-Meta B] streak_reversal 再 BT — same estimand (production trade_log) で v2 LOCK 判定"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T11:02:00+0900
roadmap_gate: "W4P1 verdict を正しい estimand で確定、改訂 LOCK の妥当性検証"
rule: R1
prereq_artifacts:
  - .ai/tasks/done/20260505-0100-w4p1-streak-reversal-htf-soft-penalty.md
  - .ai/tasks/done/20260505-1100-w4-meta-A-bt-massive-first-patch.md
  - .ai/tasks/done/20260505-1101-w4-meta-C-massive-15m-cache-generation.md
  - knowledge-base/raw/bt-results/edge-lab-2026-04-23.json
  - knowledge-base/wiki/decisions/w4-redesign-lock-criteria-v2-2026-05-05.md
  - audits/edge_design/streak_reversal.md
related:
  - knowledge-base/raw/bt-results/streak-reversal-htf-soft-penalty-2026-05-05.json
---

# 0. なぜこのタスクか

W4P1 streak_reversal は v1 LOCK で FAIL、v2 でも `wilson_lo_proposed=0.376<0.40` で REJECT 試算。
ただし W4-Meta investigation で **estimand 違い** が判明:

- **edge-lab N=468/Kelly=0.487**: USD_JPY production trade_log cohort (実 live 履歴)
- **W4P1 BT N=1224/Kelly=0.013**: focused detector + 5m→15m resample の signal-level simulation

別の世界の数字を比較していた → W4P1 の REJECT 判定は estimand 違いに起因する可能性大。

このタスクで:
1. Task A (BT_MODE patch) 完了後の MASSIVE-first 経路で
2. Task C (15m cache) 完了後の strict 15m TF で
3. **same estimand (production trade_log cohort) で再 BT**
4. v2 LOCK criteria で再判定

# 1. 仕様

## 1.1 Same-estimand BT

audit DB と同じ cohort 定義で BT を実行:
- pair: USD_JPY (audit と同じ)
- TF: 15m (audit が 15m の場合)
- 期間: 2024-04-23〜2026-04-23 (365d × 2、edge-lab と同等期間)
- フィルタ: live trade_log と同等の `is_shadow=0` 相当 + 全 hour bucket aggregate
- BT framework: `run_daytrade_backtest()` (`BT_MODE=1`) — production 完全等価

## 1.2 A/B 比較

- baseline: 現行 hard reject (HTF block enabled)
- proposed: soft penalty (`STREAK_REVERSAL_HTF_SOFT_PENALTY=1`)

両方とも production 経路で BT。

## 1.3 v2 LOCK criteria 適用

`knowledge-base/wiki/decisions/w4-redesign-lock-criteria-v2-2026-05-05.md` の基準で判定:
- regression_check
- positive_direction
- significance (cell-level Bonferroni)
- sanity_floor (Wilson lo >= 0.40, PF >= 1.0)

## 1.4 Estimand 整合確認

audit DB N=468 が再現できるか (or なぜ N が違うか) 説明する。

# 2. Implementation Steps

## Step 1: 前提タスク完了確認

- Task A: `BT_MODE=1` で MASSIVE first 経路が動作する
- Task C: USD_JPY_15m parquet が存在し、必要期間カバー

両方完了していなければ STOP し user に報告。

## Step 2: BT 実行 (baseline)

```bash
BT_MODE=1 python3 -c "
from app import run_daytrade_backtest
result = run_daytrade_backtest(
    pair='USD_JPY', tf='15m', days=730,
    strategies=['streak_reversal'],
    is_shadow=0,  # live cohort 同等
    htf_soft_penalty=False,  # baseline
)
# save trade log + summary
"
```

## Step 3: BT 実行 (proposed)

同上、`htf_soft_penalty=True` (or env `STREAK_REVERSAL_HTF_SOFT_PENALTY=1`)。

## Step 4: edge-lab N=468 再現確認

baseline BT の N と edge-lab N=468 を比較:
- 一致 (±5%) → estimand 整合、v2 LOCK 判定が信頼できる
- 大幅乖離 → cohort 定義に他の filter (entry_type 内訳、TP/SL hit 条件等) があり追加調査必要

## Step 5: v2 LOCK criteria 判定

baseline vs proposed の比較で:
- regression_check: 各指標悪化なし
- positive_direction: 改善方向のいずれか
- significance: cell-level Bonferroni
- sanity_floor: Wilson lo >= 0.40, PF >= 1.0

判定: PASS / borderline / REJECT

## Step 6: 結果保存

- BT 詳細: `knowledge-base/raw/bt-results/streak-reversal-same-estimand-2026-05-05.json`
- 判定文書: `knowledge-base/wiki/decisions/streak-reversal-htf-soft-penalty-v2-verdict-2026-05-05.md`
- baseline N が 468 に近いか + LOCK v2 verdict + W4-Redesign 72 件 dispatch 再開可否

## Step 7: Codex self-review

- estimand が正しく整合しているか
- post-hoc adjustment になっていないか
- Bonferroni m (multiple testing 母数) を audit と同じく取っているか

# 3. Acceptance

- BT 結果 (baseline + proposed) が `bt-results/` に保存
- edge-lab N=468 との照合結果
- v2 LOCK verdict (PASS/borderline/REJECT)
- 72 件 mass batch を re-dispatch する判断材料 (LOCK v2 で他戦略も pass 見込みか)

# 4. Out of Scope

- 他戦略の BT (本 task は streak_reversal のみ)
- 72 件 re-dispatch (Claude が後続 task で実行)
- live promote 判断

# 5. Notes

- Task A + C 両方完了が前提。worker は serial 処理なので順序は保たれる
- baseline N が 468 と乖離する場合は estimand 定義をさらに絞る必要 → 報告して停止
- v2 で REJECT なら、(a) v2 基準を更に緩めるべきか, (b) streak_reversal の patch が本質的に効果薄か を user に判断仰ぐ
