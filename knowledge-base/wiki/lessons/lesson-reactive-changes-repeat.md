### [[lesson-reactive-changes-repeat]]
**発見日**: 2026-04-16 | **修正**: ADX gate revert
- 問題: lesson-reactive-changesと同じ失敗を翌日に繰り返した。4日間N=628のインサンプルデータでADX>30閾値を3戦略に実装→即デプロイ→ユーザー指摘で巻き戻し
- 原因: IC分析・MAFE分析の「発見の興奮」で判断プロトコルを飛ばした。KBを1ページも読まずに実装に突入
- 修正: ADX gate revert。分析結果はKBに記録、実装はBT検証後に保留
- 教訓: **lesson-reactive-changesが存在するにも関わらず再発 = 判断プロトコルの遵守が構造的に担保されていない。pre-commitにKB参照チェックを入れるか、判断前の強制pause機構が必要**
