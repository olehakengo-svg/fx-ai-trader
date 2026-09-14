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

### Phase 2.5: 市場レビュー + 観測採集 + 執行QA
Protocol: `knowledge-base/wiki/analyses/daily-market-review-protocol.md` (統計規律 §2 を厳守)
- 前営業日レビュー (data-first): 主要ペアの日足OHLC / セッション分解 / 最大15mバー を `data/cache/massive/*_15m.parquet` から算出、指標時刻と付合せ
- 観測があれば `knowledge-base/wiki/research/daily-observations-YYYY-MM.md` に O-YYYY-MM-DD-n 形式で追記 (記述級のみ、p値計算禁止、0件の日は追記しない)
- **執行QA (毎日必須)**: 当時点の live-eligible セル (tier-master 参照) の発火条件成立 vs `/api/demo/trades` 実績 + block/abandon 理由を照合。乖離は観測として記録。**escalation 前に prereg-trigger-registry.json を当該 family で検索** — 事前コミット済み再審条件・監査 frame があればそこへ回付 (独自 R1 マークで前倒ししない)。凍結 look 保有 family の outcome 量は観測に書かない
- 月曜のみ: 先週分 family 集計 rollup を観測ファイル末尾に追記、卒業条件 (≥3独立観測) 到達 family を報告

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
