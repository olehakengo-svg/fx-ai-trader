# Changelog as Evaluation Anchor --- Changelog is the evaluation anchor

**発見日**: - | **修正**: -

## 何が起きたか
「いつからのデータを使うか」で分析結論が180度変わることが判明した。

## 根本原因
例: bb_rsi WR=52.2%(post-cutoff) vs 34.0%(全体)。カットオフ日の選択が結論を決定していた。

## 教訓
定量評価の最初のステップは「changelog.mdを読んでdate_fromを決める」。
