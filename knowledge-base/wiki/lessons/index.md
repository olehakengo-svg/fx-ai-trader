# Lessons Learned — 間違い・修正・教訓の蓄積

## なぜこのページが必要か
同じ間違いを繰り返さないために、「何を間違えて、なぜ間違えて、どう修正したか」を記録する。
次のセッション開始時にwiki/index.mdから辿れるようにすることで、判断の精度が複利で向上する。

## バグ・設計ミスの教訓

### [[lesson-shadow-contamination]]
**発見日**: 2026-04-10 | **修正**: v8.4
- 問題: get_stats()がShadowトレードを含めてWR/EVを算出 → 統計が実態を反映しない
- 症状: bb_rsi WR=52.2%(post-cut) vs 34.0%(current window)の矛盾
- 原因: is_shadow=0フィルターの欠如
- 修正: get_stats() + get_all_closed()にexclude_shadow=Trueデフォルト追加
- 教訓: **統計を出す前に「このデータに何が含まれているか」を常に確認する**

### [[lesson-xau-friction-distortion]]
**発見日**: 2026-04-10 | **修正**: v8.4
- 問題: avg_friction=7.04pip/tradeは「全戦略がフリクションに負けている」と誤解させた
- 実態: FX-only friction=2.14pip、XAU=217.5pip。XAUが平均を30倍に歪めていた
- 修正: XAU停止 + ペア別摩擦分離分析
- 教訓: **集計値は必ずセグメント分解する。平均値は嘘をつく**

### [[lesson-bt-endpoint-hardcoded]]
**発見日**: 2026-04-12 | **修正**: v8.5
- 問題: DTのBTエンドポイントがUSD_JPYハードコード → EUR/GBP/EURJPYのBTが不可能
- 発見経緯: 新エッジ戦略のBTで他ペアが動かずユーザーが指摘
- 修正: symbolとdaysをリクエストパラメータ化
- 教訓: **BT/本番統一原則は「ロジック統一」だけでなく「ペア・期間のパラメータ化」も含む**

### [[lesson-1m-scalp-not-the-problem]]
**発見日**: 2026-04-10 | **修正**: なし（誤った提案を却下）
- 問題: 独立監査が「1m scalpを全廃し15m DTへ移行」を勧告
- 実態: bb_rsi×JPYはPost-cutoffでPF>1の実測データがある唯一の戦略
- FX-onlyのPost-cutoff PnL=+96.8pip（黒字）→ 1m scalpは勝っている
- 教訓: **理論計算(friction/SL=43-71%)が実測データ(PF=1.13)と矛盾する場合、実測が正しい**

### [[lesson-macdh-absorption-risk]]
**発見日**: 2026-04-10 | **修正**: 提案を却下（独立監査勧告）
- 問題: macdh_reversalをbb_rsiに+0.5スコアボーナスとして吸収する提案
- リスク: 唯一のPF>1戦略(edge=0.45pip)を汚染し、エッジ消滅の可能性
- 教訓: **唯一の正エッジ戦略に対する実験は、リスク/リワードが非対称（最悪=エッジ消滅）**

### [[lesson-tier-classification-data-mixing]]
**発見日**: 2026-04-10
- 問題: bb_rsiを全ペア混合でWR=44.3%→「Tier 3」と分類
- 実態: USD_JPY限定ではWR=54.7% PF=1.13 → 正しくはTier 1
- 教訓: **ペア×戦略の粒度で評価しないと、「勝てるペア」と「勝てないペア」が相殺される**

## 開発プロセスの教訓

### [[lesson-bt-before-deploy]]
- ユーザー指摘: 「先にBTを行って欲しい」
- 問題: 6新エッジ戦略をBTなしでSentinelデプロイした
- 正しいフロー: 実装 → BT → BT結果で判断 → デプロイ
- 教訓: **Edge Pipeline Stage 2→3のGate（BT N≥30, WR>BEV+5pp）を飛ばさない**

### [[lesson-changelog-as-evaluation-anchor]]
- 発見: 「いつからのデータを使うか」で分析結論が180度変わる
- 例: bb_rsi WR=52.2%(post-cutoff) vs 34.0%(全体) → changelog参照で解決
- 教訓: **定量評価の最初のステップは「changelog.mdを読んでdate_fromを決める」**

## Related
- [[changelog]] — バージョン別変更タイムライン
- [[independent-audit-2026-04-10]] — 覆された判断の詳細
- [[edge-pipeline]] — Stage Gate（飛ばしてはいけない手順）
