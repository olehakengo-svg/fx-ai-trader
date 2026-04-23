# Pre-registration: Label Inversion Holdout (2026-05-07)

**Locked**: 2026-04-23
**Holdout window**: 2026-04-24 00:00 UTC – 2026-05-07 23:59 UTC (14 days)
**Second holdout (for category Kelly)**: 2026-05-08 – 2026-05-21

## Purpose

[[quant-validation-label-audit-2026-04-23]] で `方向一致` label のみ Bonferroni
α=1e-3 通過。他 6 件は候補止まり。holdout で confirmatory test 実施し、
code change を許可するか判定する。

## Binding criteria (decision-grade)

### H1: 方向一致 label 削除判断

**Test**: shadow-only / post-cutoff=2026-04-24 / XAU除外 で `方向一致` in reasons
の has/no 分割 × WR。Fisher exact 2-tail p.

**GO (label削除 + code change)**:
- p < 1e-3 (Bonferroni α=0.05/50)
- Δ WR_has − WR_no ≤ -5pp
- N_has ≥ 100
- 上記を **all met**

**HOLD (判定保留)**: いずれか 1 つ欠ける → 期間 14d 延長、再計測

**NO-GO (label 削除撤回)**:
- p ≥ 0.05 または
- Δ WR が正方向 (+1pp 以上) に反転

**TF subgroup 特別判定**: TF 内 Δ WR ≤ -10pp かつ p < 1e-3 なら、TF 戦略 17 ファイル
の `EMA方向一致` / `EMA200方向一致` label を一括削除 (cosmetic change only)。

### H2: 候補 6 件 (VWAPスロープ等) の再判定

**Test**: VWAPスロープ / 売り優勢 / 買い優勢 / 機関フロー / HVN / S/R確度UP /
ブレイク を同じ Fisher exact で再計測。

**GO (逆校正確定)**: 本 holdout で **新たに** p < 1e-3 を満たす label → 対策候補化
**STATUS QUO**: 現 KB に "inversion 候補" としてのみ記録、code change なし

### H3: カテゴリレベル Tier 降格

**Test**: カテゴリ C (TF/MR/OTHER) の shadow trades per-trade EV Wilson 95% CI。

**GO (live-weight zero 化)**:
- 本 holdout の Wilson 95% upper < 0 p
- かつ Kelly < 0
- **2 連続 holdout** (Apr 24-May 7 + May 8-May 21) で成立

**MAINTAIN**: 2 連続条件に 1 つでも fail → 現状維持 (shadow 継続)

## Non-binding observables (for transparency)

これらは decision には使わないが記録:

- Per-strategy × pair cell-level Kelly (>0 な cell が残っているか)
- Walk-forward WF_1/WF_2 での `方向一致` Δ WR (regime stability)
- MTF alignment × category × WR (既存仮説の holdout 確認)

## Parameters (locked)

| Parameter | Value | 変更禁止理由 |
|-----------|-------|--------------|
| XAU除外 | Y | 目標指標から除外確定 |
| is_shadow | =1 | live 混入による contamination 回避 |
| status | CLOSED | open 中の trade は outcome 未確定 |
| BT_COST | 1.0p | 保守的 spread 前提 |
| α family | 0.05 | 標準 |
| M (Bonferroni denom) | 50 | 計 26 label × 3 scope = 78 → 保守的に 50 (下限) |
| Fisher test | 2-tail | 方向不問 (逆校正か正校正か) |
| Δ threshold | 5pp | 経済的に意味のある gap |

## Post-hoc analyses disallowed

以下は holdout 後に実施しても binding decision には使えない:

- 他の label 追加検定 → M 増加で既存の threshold 緩くなる
- WF 3-bucket 以上分割 → overfitting
- 別の cutoff date 試す → snooping
- Category subdivision (TF → 前半TF / 後半TF) → fishing

新 hypothesis は **次の pre-registration** として別 doc にする。

## Failure modes to guard against

1. **Data contamination**: shadow ↔ live 混入 → `is_shadow=1` 固定で回避
2. **Multi-comparison creep**: 追加検定を "ついでに" 入れない
3. **Confidence-only selection**: 結果見た後に "実はこの subset だけ…" と切り替えない
4. **Kelly underestimate**: BT_COST=1 は保守的。実 spread 変動は separately log

## Execution checklist (2026-05-07)

- [ ] `python3 /tmp/quant_validation.py --cutoff 2026-04-24 --end 2026-05-07` 実行
  (現 script に cutoff 引数追加必要)
- [ ] 出力を [[quant-validation-holdout-2026-05-07]] に記録
- [ ] 上記 GO 条件ヒット label の code change を実装
- [ ] GO 条件 miss は "maintained candidate" として記録
- [ ] カテゴリ Kelly 判定は 2 連続 holdout 後のため、本回は observation only
- [ ] 次回 pre-registration doc を作成 (ある場合)

## Author accountability

**事前約束**: holdout 結果を選択的に解釈しない。上記 binding criteria のみで判定。
"N が足りない" を言い訳に延長する場合も、延長期間を事前 lock する
(= 本 doc の 14d rule でカバー)。

## References

- [[quant-validation-label-audit-2026-04-23]]
- [[lesson-premature-neutralization-2026-04-23]]
- [feedback_partial_quant_trap](/Users/jg-n-012/.claude/projects/-Users-jg-n-012-test/memory/feedback_partial_quant_trap.md)
- [[pre-registration-2026-04-21]] (先行例: bb_squeeze_breakout promotion)
