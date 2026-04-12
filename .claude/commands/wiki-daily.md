# Wiki Daily — 日次ナレッジ更新（Ingest + Lint統合）

毎日のトレード終了後に実行。最新データを取り込み、ナレッジベースの健全性を確認。

## 手順

### Phase 1: データ取得
APIから最新データを取得（/wiki-ingest と同じ）

### Phase 2: 日次レポートをraw/に保存
`knowledge-base/raw/trade-logs/YYYY-MM-DD.md` に以下を記録:
- 当日のトレード数、WR、PnL
- 戦略別パフォーマンス
- OANDA約定状況
- 特筆すべきイベント（新戦略発火、異常スプレッド等）

### Phase 3: wiki/更新
- index.md: Tier分類テーブル更新
- 変動戦略ページ: 新データ追加
- log.md: 更新内容を記録

### Phase 4: Lint
- /wiki-lint と同じチェックを実行
- ⚠️があればlog.mdに記録

### Phase 5: サマリー出力
以下のフォーマットで日次サマリーを出力:

```
## YYYY-MM-DD Daily Update
- Trades: N件 (WR: XX%)
- PnL: +/-XXpip
- Key changes: [戦略名のTier変更、新発見等]
- ⚠️ Lint warnings: [矛盾・ギャップがあれば]
- Next actions: [翌日に確認すべき事項]
```
