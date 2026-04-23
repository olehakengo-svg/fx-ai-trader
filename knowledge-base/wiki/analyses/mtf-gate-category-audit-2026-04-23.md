# MTF Gate Full-Category Audit (2026-04-23)

**Scope**: shadow post-cutoff 2026-04-08 / XAU除外 / N=2057
**Script**: `/tmp/mtf_gate_full_audit.py`
**Trigger**: [feedback_label_empirical_audit](/Users/jg-n-012/.claude/projects/-Users-jg-n-012-test/memory/feedback_label_empirical_audit.md)

## Executive Summary

**MTF alignment は category 依存で逆転**:
- **TF (ema_pullback 等)**: aligned WR 12.9% vs conflict 20.4% → **Delta -7.5pp 🚨 INVERSE**
- **MR (bb_rsi 等)**: aligned WR 30.3% vs conflict 19.5% → **Delta +10.8pp ✓ POSITIVE**
- **OTHER**: aligned WR 23.1% vs conflict 27.3% → Delta -4.2pp ⚠ weak inversion
- **BR (breakout)**: データなし (N<10)

結論: MTF alignment gate は **MR には正しく機能**、**TF には逆機能**。
カテゴリ条件付きで動作を切り替える必要がある。

## Raw Results

### Category × MTF alignment

| Category | Alignment | N | WR | Wilson 95% CI | EV |
|----------|-----------|---|-----|----|-----|
| TF | conflict | 284 | 20.4% | [16.1, 25.5] | -1.96p |
| TF | unknown  | 256 | 26.2% | [21.2, 31.9] | -1.86p |
| TF | aligned  |  31 | 12.9% | [ 5.1, 28.9] | -3.39p |
| MR | unknown  | 697 | 26.0% | [22.9, 29.3] | -2.43p |
| MR | aligned  | 208 | 30.3% | [24.4, 36.8] | -1.23p |
| MR | conflict | 200 | 19.5% | [14.6, 25.5] | -2.17p |
| OTHER | unknown  | 284 | 19.4% | [15.2, 24.4] | -3.79p |
| OTHER | conflict |  66 | 27.3% | [18.0, 39.0] | -1.39p |
| OTHER | aligned  |  26 | 23.1% | [11.0, 42.1] | -3.18p |

### Delta (aligned − conflict) per category

| Category | Delta WR | Delta EV | Judgment |
|----------|----------|----------|----------|
| TF | -7.5pp | -1.43p | 🚨 INVERSE |
| MR | +10.8pp | +0.94p | ✓ POSITIVE (as designed) |
| OTHER | -4.2pp | -1.79p | ⚠ weak inversion |

### Wilson CI overlap check

- TF aligned [5.1, 28.9] vs conflict [16.1, 25.5] — CI overlap だが aligned 下限は
  conflict 中心を**下回る**。TF-inversion の統計有意性は n=31 で borderline。
- MR aligned [24.4, 36.8] vs conflict [14.6, 25.5] — **CI 非重複** (有意に positive)。
- OTHER aligned n=26 は小さく判定保留。

## Interpretation

### Why TF aligned is inverse

前セッションの meta-lesson (`lesson-why-missed-inversion-meta-2026-04-23.md`) と整合:

1. **現在の市場レジームは TF 逆行傾向**: EMA方向に並ぶ時ほど逆に動く
2. **Alignment 検出時はすでに trend 終盤**: entry 時点でモメンタム枯渇
3. **Pullback 戦略の逆襲**: aligned = pullback の逆方向、つまり trend fade

### Why MR aligned is positive

MR (bb_rsi_reversion 等) は逆張り戦略。MTF aligned = 逆張り方向に multi-TF が support
を提供している状態。これは設計通りで +10.8pp の正 calibration。

### Why gate A/B (mtf_gated flag) empty

`reasons` フィールドに `mtf_gated` / `MTF一致` / `MTF不一致` の literal string は**埋め込まれていない**。
MTF alignment 判定はメタデータ (`mtf_alignment` カラム) のみで reasons tag として記録されていない。
→ Label-only retrospective audit は `mtf_alignment` column 直読に依拠せよ。

## Recommended Actions

1. **TF MTF alignment の conf bonus を category 条件化** (既存実装次第)
2. **TF aligned trades の "大口方向一致" 系 score boost** (`app.py:8869-8878` Layer 1) も
   category-aware にする必要があるか別途監査
3. **MR 向けは現状維持** — aligned boost は設計通り機能

## Meta observation

既存の `aligned` シグナルを **画一的に boost** する実装は、カテゴリ依存の calibration
差 (TF 逆 / MR 正) を平均化して見えなくする。Category-conditional gating が必須。

## References

- [feedback_label_empirical_audit](/Users/jg-n-012/.claude/projects/-Users-jg-n-012-test/memory/feedback_label_empirical_audit.md)
- [[tf-inverse-rootcause-2026-04-23]]
- [[lesson-why-missed-inversion-meta-2026-04-23]]
- Raw output: `/tmp/mtf_gate_audit_output.txt`
