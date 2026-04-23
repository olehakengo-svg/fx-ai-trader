# Quant Validation — Label Audit Bonferroni + Walk-forward + Economic Significance (2026-04-23)

**Scope**: shadow post-cutoff 2026-04-08 / XAU除外 / N=2066 (最新 fetch)
**Script**: `/tmp/quant_validation.py`
**Trigger**: [feedback_partial_quant_trap](/Users/jg-n-012/.claude/projects/-Users-jg-n-012-test/memory/feedback_partial_quant_trap.md)
の罠に再度はまっていた自己査察 → 厳密な統計検定で label audit の結論を再評価

## Executive summary

### 前回分析の訂正

[[full-label-audit-2026-04-23]] で 7 件の逆校正を報告したが、
**Bonferroni 補正 (α/M=1e-3, M=50) 後に生存するのは `方向一致` のみ**。

| Label | Scope | p-value | Bonferroni α=1e-3 |
|-------|-------|---------|-------------------|
| **方向一致** | overall | **1.89e-06** | ✓ 🚨 |
| **方向一致** | TF | **1.15e-04** | ✓ 🚨 |
| **方向一致** | WF_1 (Apr 8-15) | **2.19e-05** | ✓ 🚨 |
| 方向一致 | MR | 1.04e-02 | ✗ |
| 方向一致 | WF_2 (Apr 16-23) | 6.82e-03 | ✗ |
| VWAPスロープ | all scopes | >1e-2 | ✗ |
| 売り優勢 | all scopes | >1e-3 | ✗ |
| 機関フロー | overall | 1.91e-03 | ✗ (閾値近接) |
| HVN | overall | 1.80e-03 | ✗ (閾値近接) |
| S/R確度UP | overall | 2.52e-03 | ✗ |
| ブレイク | all scopes | >5e-2 | ✗ |

**結論**: `方向一致` label の逆校正は統計的に強固 (p=1.9e-06)。残り 6 件は
multiple testing の noise と分離できず、確定的 inversion 判定は取り下げる。

### Walk-forward stability (方向一致 only)

| Bucket | N_has | WR_has | Δ WR | p |
|--------|-------|--------|------|---|
| Apr 8-15 (WF_1) | 158 | 13.9% | **-17.0pp** | 2.19e-05 ✓ |
| Apr 16-23 (WF_2) | 933 | 20.6% | -6.2pp | 6.82e-03 ✗ |

**Regime-dependent**: inversion 強度が **前半で極端、後半で半減**。
WF_2 は Bonferroni 通らず → 単一 regime 現象の可能性高い。

### MTF alignment (direct column)

| Category | aligned | conflict | Δ WR | p | Bonferroni |
|----------|---------|----------|------|---|------------|
| TF | N=33 WR=12.1% [4.8, 27.3] | N=288 WR=20.8% [16.5, 25.9] | -8.7pp | 3.56e-01 | ✗ |
| MR | N=209 WR=30.1% [24.3, 36.7] | N=201 WR=19.4% [14.5, 25.4] | +10.7pp | 1.23e-02 | ✗ |

**両方 Bonferroni 通らず**。前回 [[mtf-gate-category-audit-2026-04-23]] で
"TF INVERSE / MR POSITIVE" と断言したが、**統計的には確立していない**。
TF aligned N=33 は検出力不足、MR aligned N=209 は Δ=+10.7pp だが Wilson CI overlap。

→ MTF category-dependent 結論は **仮説レベル**、Bonferroni-robust な主張ではない。

## Economic significance — 全カテゴリ崩壊

15-day shadow P&L (pips, XAU除外):

| Category | N | WR 95% CI | EV/trade | PF | Kelly | 15d total | Monthly est |
|----------|---|-----------|----------|-----|-------|-----------|-------------|
| TF | 577 | [19.5, 26.3] | -1.99p | 0.66 | **-0.119** | **-573p** | **-1,147p** |
| MR | 1107 | [23.1, 28.2] | -2.17p | 0.61 | **-0.161** | **-1,297p** | **-2,593p** |
| OTHER | 382 | [16.9, 25.0] | -3.37p | 0.53 | **-0.183** | **-907p** | **-1,814p** |
| **合計** | 2066 | | | | | **-2,777p** | **-5,554p** |

### 衝撃の再認識

- **TF だけでなく MR も OTHER も全カテゴリで Kelly ≤ 0 / PF < 1**
- MR は TF より **絶対 P&L 悪い** (monthly -2,593 vs -1,147)
  - N が大きい分 damage 倍
  - 当初 MR は aligned で +10.8pp 正校正と見なしていたが、全体としては負け組
- OTHER は per-trade EV 最悪 (-3.37p)

### 月利 100% 目標 (¥454,816/月) への寄与

BT_COST=1.0 pip 仮定で shadow 全カテゴリ 月次 **-5,554 pips**。
1pip ≈ 10 円/0.01lot で、0.1 lot 規模でも -¥55,540/月。
**現状 shadow は目標の逆方向に寄与**。

目標到達のためには:
- Kelly ≤ 0 カテゴリは **sizing ゼロ** にすべき (既 shadow 分離済だが、
  live への promotion 条件を厳格化)
- 個別 strategy レベルで Kelly > 0 な生き残りを抽出 → aggregate でなく per-strategy 判定
- カテゴリ全体の blanket demotion ではなく **cell-level (strategy × pair × regime)** で判定

## Tier 降格判定 — pre-registration

### 方向一致 inversion の holdout test

pre-registered decision rule (2026-05-07 実測時):

**Binding criteria**:
1. Apr 24 – May 7 の next-14d shadow で `方向一致` label 付与 trades を再計測
2. 以下を **すべて満たす** 場合: TF 戦略の共通 label 削除に踏み切る
   - Fisher 2-tail p < 1e-3 (Bonferroni α/50)
   - Δ WR ≤ -5pp
   - N_has ≥ 100
3. 1 つでも欠けた場合: 判定保留、さらに 14 日延長

**Non-binding (but recorded)**:
- `方向一致` label 削除は TF strategy files で 15 箇所 (`EMA方向一致` / `EMA200方向一致`)
- 削除により conf_adj 変動なし (cosmetic 変更のみ)、ただし UI / ML feature 下流で消費される可能性

### カテゴリ降格の pre-registration

**Binding criteria** (2026-05-07 holdout):
- カテゴリ C の per-trade EV 95% upper < 0 かつ Kelly < 0 が **2 連続 buckets (各 14d)** で成立
- この条件満たす C は **live-weight ゼロ化** (shadow 継続)
- 条件満たさない C は維持

現状 WF_1 / WF_2 で TF/MR/OTHER すべて Kelly < 0 だが、holdout 期間として
Apr 24 – May 7 + May 8 – May 21 の 2 連続で再確認して確定。

## Corrections applied

### 過剰主張の訂正

[[full-label-audit-2026-04-23]]:
- "7 件逆校正" → "**1 件 (方向一致) のみ Bonferroni robust**, 残り 6 件は閾値届かず候補止まり"

[[mtf-gate-category-audit-2026-04-23]]:
- "TF INVERSE (確定)" → "N=33 で p=0.36, **Bonferroni 未通過、仮説段階**"
- "MR POSITIVE (確定)" → "Δ=+10.7pp だが p=0.012, **Bonferroni 未通過**"

[[layer1-bias-direct-audit-2026-04-23]]:
- "+18.3pp 正校正" → "N=13 match vs 16 conflict で **p ≈ 0.26, 統計的判定不能**"

### Label 観察記法化 commit (d6d6917) の評価

- VWAPスロープ / 売り優勢 / 買い優勢 を `[observed] xxx` に変更
- これらは Bonferroni **通過していない**、つまり逆校正の確定的証拠なし
- しかし cosmetic 変更 (reasons label のみ) で取引意思決定に影響しないため、
  commit は **無害だが不必要** だった (premature action)

教訓: KB 変更は許容されるが、code change は pre-registration 後にすべき。

## Next actions (priority order)

### Immediate (本 commit)

- [x] 本分析 KB 作成
- [ ] [[lesson-premature-neutralization-2026-04-23]] 新規: "Bonferroni 通らない label を
  観察化するのは premature"
- [ ] pre-registration KB [[pre-registration-label-holdout-2026-05-07]]

### Holdout window (2026-05-07)

- [ ] 方向一致 label の再計測 (pre-registered criteria)
- [ ] TF/MR/OTHER per-trade EV Wilson CI の再計測
- [ ] Per-strategy × pair × regime cell-level Kelly 計算

### Long-term (user decision required)

- [ ] 全カテゴリ Kelly<0 への対応: live-weight ゼロ化 or selective promotion?
- [ ] shadow 継続 vs 止血: 目標月利 100% から逆行している以上、continuation 判断必要

## References

- [feedback_partial_quant_trap](/Users/jg-n-012/.claude/projects/-Users-jg-n-012-test/memory/feedback_partial_quant_trap.md)
- [feedback_label_empirical_audit](/Users/jg-n-012/.claude/projects/-Users-jg-n-012-test/memory/feedback_label_empirical_audit.md)
- [[full-label-audit-2026-04-23]]
- [[mtf-gate-category-audit-2026-04-23]]
- [[layer1-bias-direct-audit-2026-04-23]]
- Script: `/tmp/quant_validation.py`
- Raw output: `/tmp/quant_validation_output.txt`
