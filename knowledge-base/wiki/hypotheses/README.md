# Hypotheses — エッジ仮説の仮置き場

## 用途
Edge Pipelineの **Stage 1 (DISCOVERED)** にある仮説をここに書く。
`templates/edge-hypothesis.md` をコピーして使用。

## いつ使うか
- 新しいエッジのアイデアが浮かんだとき
- 学術論文から着想を得たとき
- 本番データの異常パターンを発見したとき

## ライフサイクル
1. ここに仮説ファイルを作成 (Stage 1: DISCOVERED)
2. BT実行 → Stage 3到達時に `wiki/edges/` に昇格
3. Sentinel化 → Stage 4で `wiki/edges/` に正式登録
4. 不採用 → ファイル末尾に `## 却下理由` を追記して保存（学習資産として）

## Related
- [[edge-pipeline]] — 6段階評価プロセス
- `templates/edge-hypothesis.md` — テンプレート
