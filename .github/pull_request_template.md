<!--
PR テンプレート (rule:R3, 2026-09-10 — process-meta-audit-2026-09-07 §4.2 R3)
通常の feat/docs PR は「概要」だけ書けばよい。
下の「修理 3 フィールド」は **bugfix (fix:/修理系) のときのみ必須**。
-->

## 概要

<!-- 何を・なぜ。KB 参照 (analyses/decisions/lessons) と rule:R[1|2|3] を明示 -->

## 修理 3 フィールド (bugfix のときのみ記入)

<!--
バグ潜伏期間の分布 (中央値 124 日、QA 起点発見 0/8 — メタ監査 2026-09-07) を
測定可能にするための欄。bugfix 以外の PR では「N/A」のまま残してよい。
- 混入日: バグが最初に main に入った commit/日付 (git log -S / blame で特定。不明なら「不明 (根拠)」)
- 発見日: 異常に気付いた日 (修理日ではない)
- 発見手段: alert 名 / テスト名 / counterfactual / 人手レビュー / 偶然 — どの経路が仕事をしたか
-->

| フィールド | 値 |
|---|---|
| 混入日 | N/A |
| 発見日 | N/A |
| 発見手段 | N/A |

## 検知器を追加/変更した場合のチェックリスト

<!-- monitoring/estimand_declarations.yml の運用ルール。該当しなければ削除してよい -->

- [ ] `monitoring/estimand_declarations.yml` に宣言を追加/更新した (claims/population/clock/threshold_source/reader/counterfactual_test)
- [ ] reader (読み手) の配線と counterfactual test を**同一コミット**に含めた
- [ ] `python3 tools/estimand_declaration_check.py` が ERROR 0 で通る
