# Qdrant Research Retrieval — Semantic Search Layer

## 目的（クオンツ判断）
- 既存 19 本の FX 学術ノート (`wiki/research/`) を semantic 検索可能にし、戦略設計時の先行研究引き込みを高速化する
- KB_SYNC hook は index/portfolio/lessons/unresolved のみ注入するため、`analyses/`・`decisions/`・`sessions/` の深い過去文脈は retrieval が必要
- Grep は完全一致、semantic は同義語/概念類似（例: 「止血判断」で `early_exit` / `損切り閾値` 等を引ける）

## 月利100%目標との整合
- **今は Live N 蓄積（Kelly Half 到達）が最優先**
- 本 retrieval 層は Phase 3（Kelly Half 以降の edge 発見加速）の基盤
- **現時点では live/BT logic 無触の ingest 基盤のみ整備**。retrieval の戦略設計 workflow 統合は Kelly Half 到達後

## アーキテクチャ
- **Storage**: embedded Qdrant at `knowledge-base/.qdrant/` (local file, `collections: fx-research`)
- **Embedding**: `sentence-transformers/all-MiniLM-L6-v2` (384 dim, fastembed)
- **MCP Query**: `qdrant-fx` MCP server (`~/.claude.json`) — `qdrant-find` ツール経由
- **Ingest**: `tools/qdrant_ingest_kb.py` (self-bootstrapping venv at `tools/.venv-qdrant-ingest/`)

## Ingest 手順（運用）
```bash
# 1. MCP qdrant-fx を停止（file lock 排他）
ps -ef | grep mcp-server-qdrant | grep -v grep    # プロセス確認
# /mcp disconnect qdrant-fx  （Claude Code UI から）または親 uvx を kill

# 2. Ingest 実行（初回は venv 自動構築 ~1min）
python3 tools/qdrant_ingest_kb.py

# 3. MCP 再接続
# /mcp  で qdrant-fx を reconnect
```

## 冪等性
- Point ID = `sha256(path#chunk_idx)` → 同一ファイルの再 ingest は upsert
- `--rebuild` でコレクション全削除→再構築
- file mtime を metadata に持つが、現時点では skip logic 未実装（将来追加可）

## Chunking
- 2000 chars / chunk、200 chars overlap
- 平均 file size 3.7 KB → 大半は 1 chunk、長い analyses は 2-3 chunks
- MiniLM-L6 の 512 token 制約に収まるサイズ

## 対象ディレクトリ（デフォルト）
- `wiki/research/` — 学術論文ノート（19 本）
- `wiki/lessons/` — 教訓（同じ間違い再発防止）
- `wiki/analyses/` — 分析（friction, bt-live-divergence, etc）
- `wiki/strategies/` — 戦略ページ（過去 BT/Live 履歴）
- `wiki/syntheses/` — ロードマップ、戦略統合
- `wiki/decisions/` — 意思決定履歴

計 ~170 ファイル / ~630 KB。

## 運用ルール
- **ingest は任意のタイミングで再実行可能（冪等）**。KB 更新後に `qdrant_ingest_kb.py` を回せば最新化される
- **retrieval の戦略設計 workflow 統合は Kelly Half 到達後に判断**（現時点で無理に使わない、lesson-reactive-changes 回避）
- MCP lock 競合時は `knowledge-base/.qdrant/.lock` を覗いて占有プロセスを特定

## 既知の制約
- Embedded Qdrant は **単一プロセス排他**。複数 Claude セッション並走時は lock 競合 → http daemon 化（将来）検討
- Fastembed モデルは初回 download ~100MB（以降 cache）
- `tools/.venv-qdrant-ingest/` は ~500MB（fastembed + torch/onnxruntime）→ `.gitignore` 済み

## 将来拡張（Kelly Half 以降）
- arxiv/SSRN からの外部論文自動 ingest pipeline
- `wiki-research` skill との統合（未使用 skill、現状は log 参照のみ）
- mtime-based incremental ingest（再計算コスト削減）
- 戦略設計プロトコルに「qdrant-find で先行研究確認」ステップ追加
