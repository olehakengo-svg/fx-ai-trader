# Wiki Ingest — 新しい知見をナレッジベースに取り込む

FXトレードシステムのナレッジベース（knowledge-base/）に新しい情報を取り込んでください。

## 手順

1. **データ取得**: 以下のAPIから最新データを取得
   - `https://fx-ai-trader.onrender.com/api/demo/stats?date_from=2026-04-08` (post-cutoff stats)
   - `https://fx-ai-trader.onrender.com/api/demo/learning` (learning engine)
   - `https://fx-ai-trader.onrender.com/api/risk/dashboard` (risk metrics)
   - `https://fx-ai-trader.onrender.com/api/oanda/audit?limit=30` (OANDA execution)

2. **wiki/index.md更新**: Tier分類テーブルを最新のWR/PnL/N数で更新

3. **戦略ページ更新**: 変動があった戦略のwiki/strategies/*.mdを更新
   - 新しいN数、WR、PnL
   - v8.3/v8.4以降の変化（確認足効果、XAU停止効果）

4. **新規知見の追加**: セッション中に発見した新しい知見があれば
   - concepts/ に新ページを作成
   - decisions/ に意思決定を記録
   - 既存ページへの[[内部リンク]]を追加

5. **wiki/log.mdに変更を記録**

6. **矛盾チェック**: 更新中に矛盾を発見したらlog.mdに⚠️フラグ

## ルール
- raw/ は読み取り専用（元データは書き換えない）
- wiki/ のみ書き込み可能
- ファイル名はケバブケース（例: bb-rsi-reversion.md）
- [[内部リンク]]を積極的に使う
- 各ページは200-500語を目安
