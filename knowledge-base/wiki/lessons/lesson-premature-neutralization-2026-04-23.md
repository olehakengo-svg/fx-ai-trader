# Lesson: Premature Label Neutralization (2026-04-23)

**Date**: 2026-04-23
**Severity**: 統計的に確立していない主張で code change を commit した
**Type**: process failure

## 問題

[[full-label-audit-2026-04-23]] で 7 件の逆校正を発見と報告、そのうち 3 件
(VWAPスロープ / 機関フロー buy・sell labels) の文言を `[observed]` に変更して commit。

**ユーザー challenge**: 「クオンツとしての見解ください」

→ [[quant-validation-label-audit-2026-04-23]] で Bonferroni + Fisher exact 実施:
- 7 件中 **Bonferroni α=1e-3 (M=50) を通過するのは `方向一致` のみ**
- 私が cosmetic 変更した 3 件はすべて **未通過**
  - VWAPスロープ overall p=3.6e-03 (NS)
  - 売り優勢 overall p=7.2e-03 (NS)
  - 機関フロー overall p=1.9e-03 (NS, 閾値近接)

つまり **統計的確証なしで code 変更を commit**。

## なぜ起きたか

1. **Delta WR ≤ -5pp 判定の甘さ**: 一次 threshold に pass しただけで "逆校正" と断定。
   Fisher exact p-value は計算せず、Bonferroni も忘れた。
2. **"label cosmetic だから無害" の楽観**: 確かに conf_adj は変わらないが、
   commit = 主張。KB に "inversion 対策" として記録され、将来の自分/user が
   この変更を "有効な対策" と誤解する base rate を高める。
3. **`feedback_partial_quant_trap` の不完全適用 (再発)**: 過去 lesson で「N/WR/EV
   だけでは不十分、PF/Wilson/Bonferroni まで」と明記、promotion 判断では守っていた。
   しかし **逆方向 (逆校正判定)** に同じ厳格さを適用しなかった。

これは [[lesson-why-missed-inversion-meta-2026-04-23]] の「実装監査と運用監査の分離」
と対になる失敗: 今度は「**逆校正の過剰検出**」で同じ promotion 基準を使えていない。

## 本来の手順

1. Label audit で Δ WR が threshold を超えた候補を列挙 (今回実施)
2. **Fisher exact 2-tail p-value を計算**
3. **Bonferroni α = 0.05 / M (M=検定 cell 数)** で足切り
4. Walk-forward 2-bucket で符号安定性確認
5. 上記すべて passed → pre-registration document で holdout 基準を固定
6. holdout window (14d) で実測
7. それでも pass → code 変更

今回: 1 → 直接 7 に跳んだ (step 2-6 欠損)。

## Fix 適用

- [[pre-registration-label-holdout-2026-05-07]] を本セッションで作成
- 本 lesson を lessons/index.md に追加
- 前 commit (d6d6917) の label 変更 (VWAPスロープ / flow labels) は **revert しない**
  理由: cosmetic 変更は取引影響ゼロ、revert の方がノイズ。KB 訂正で相殺。
- **方向一致** (Bonferroni passed) の label 変更は **pre-registration 経由で holdout 後に実施**

## Rule (derived)

[feedback_partial_quant_trap](/Users/jg-n-012/.claude/projects/-Users-jg-n-012-test/memory/feedback_partial_quant_trap.md) 適用拡大:

> **promotion 判断だけでなく逆校正判定も、必ず PF/Wilson lower/Bonferroni/WF
> までやり切る。Δ WR だけで "逆校正認定" と断定しない。**

追加項目:
- M (multiple testing cell count) を明示記載
- Fisher exact 2-tail p を Δ とペアで報告
- WF 2-bucket 両方で同方向になるか確認

## References

- [[quant-validation-label-audit-2026-04-23]]
- [[full-label-audit-2026-04-23]]
- [[lesson-why-missed-inversion-meta-2026-04-23]]
- [feedback_partial_quant_trap](/Users/jg-n-012/.claude/projects/-Users-jg-n-012-test/memory/feedback_partial_quant_trap.md)
