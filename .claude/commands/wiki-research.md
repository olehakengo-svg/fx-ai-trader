# Wiki Research — 学術文献からエッジを発見する

FXトレーディングの新しいエッジを学術論文から発見し、ナレッジベースに構造化して記録する。

## 引数
$ARGUMENTS — 研究テーマまたは論文タイトル（例: "FX dealer inventory management" / "carry trade unwinding"）

## 手順

### Phase 1: 文献サーチ
WebSearchで以下を検索:
- "$ARGUMENTS" site:ssrn.com OR site:nber.org OR site:sciencedirect.com
- "$ARGUMENTS" FX foreign exchange trading strategy
- "$ARGUMENTS" intraday returns anomaly

### Phase 2: 論文要約
発見した論文ごとに `knowledge-base/raw/papers/author-year-short-title.md` を作成。
テンプレート: `knowledge-base/templates/paper-summary.md` を使用。

### Phase 3: エッジ仮説の抽出
論文からFXトレーディングに応用可能なエッジ仮説を抽出。
各仮説を `knowledge-base/wiki/edges/edge-name.md` に記録。
テンプレート: `knowledge-base/templates/edge-hypothesis.md` を使用。

### Phase 4: 既存知識との統合
- `knowledge-base/wiki/research/index.md` のPapers Readテーブルに追加
- 関連する研究テーマページ（wiki/research/theme-name.md）を更新
- 既存戦略との関連性を[[内部リンク]]で接続
- edge-pipeline.md のStage 1: DISCOVEREDに追加

### Phase 5: 実装可能性の即時評価
発見したエッジ仮説について以下を評価:
- 摩擦耐性: 推定SL距離 vs ペア別RT friction → BEV_WR算出
- 既存戦略との相関: 同じ市場状況で発火するか？
- タイムフレーム適合性: 15m以上で実装可能か？
- OANDA制約: リテールブローカーで実行可能か？

### Phase 6: ログ更新
- `knowledge-base/wiki/log.md` に研究セッションを記録
- 発見の要約とnext stepsを記述

## ルール
- raw/papers/ は原典保管（要約のみ、著作権に配慮）
- 各論文の要約は200-500語
- エッジ仮説は必ず「数学的定義」（疑似コード）まで落とし込む
- 「面白いが実装不可能」なものは明示的にREJECTED理由を記録
- [[内部リンク]]を積極的に使い、知識のネットワークを構築
