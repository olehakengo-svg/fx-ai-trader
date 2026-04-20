# MCP Server Setup Guide

本プロジェクトで使う MCP サーバーの認証・Bot作成手順。

## 1. Sentry MCP — OAuth認証

### 前提
- Sentryアカウント作成済み（https://sentry.io）
- `fx-ai-trader` プロジェクト作成済み（Platform: Python/Flask）
- Render env var `SENTRY_DSN` 設定済み

### 認証手順
1. Claude Code セッションで Sentry MCP ツールを任意呼び出し
   - 例: "Sentry で最新のエラーを確認して"
2. ブラウザに Sentry OAuth 画面が自動で開く
3. Sentryアカウントでログイン → 権限許可
4. ターミナルに戻ると MCP が Connected 状態に変わる
5. 以降、Claude から直接 `find_issues` / `find_projects` などが使える

### トラブル時
- `claude mcp list` で sentry が "! Needs authentication" のままなら:
  - `claude mcp remove sentry -s user`
  - `claude mcp add --transport http sentry -s user https://mcp.sentry.dev/mcp`
  - セッション再起動

## 2. Discord Bot — 監視通知用

### 用途
- トレード開始/停止通知
- エラー/ドローダウン警告
- 日次レポート配信

### Bot作成手順
1. https://discord.com/developers/applications → **New Application**
2. 名前: `fx-ai-monitor`
3. 左メニュー **Bot** → ユーザー名設定
4. **Privileged Gateway Intents** → **Message Content Intent** を ON
5. **Token** セクション → **Reset Token** → コピー（1度しか表示されない）

### サーバー招待
1. 左メニュー **OAuth2 → URL Generator**
2. Scope: `bot`
3. Permissions:
   - View Channels
   - Send Messages
   - Send Messages in Threads
   - Read Message History
   - Attach Files
   - Add Reactions
4. Integration type: **Guild Install**
5. Generated URL をコピー → ブラウザで開いて自分のサーバーに追加

### Claudeへの接続
```bash
# Botトークンを plugin:discord 設定に投入
# 詳細: ~/.claude/plugins/cache/claude-plugins-official/discord/0.0.4/README.md
```

## 3. Qdrant MCP — 戦略リサーチ用ベクトル検索

### 用途
- 論文・BT結果のセマンティック検索
- 過去の類似戦略検索（"similar to bb_rsi_reversion"）

### 設定
- 既に `qdrant-fx` として登録済み（ローカル保存: `knowledge-base/.qdrant/`）
- Collection: `fx-research`
- Embedding: `sentence-transformers/all-MiniLM-L6-v2`

### 使い方
```
# Claudeに聞く
"qdrant-store で 2026-04-17 セッションの全BT結果を格納して"
"qdrant-find で session_time_bias に類似する戦略を検索"
```

## 4. Render MCP

### 用途
- Renderサービス管理（再起動、環境変数、ログ取得）
- PostgreSQL/Redis へのクエリ
- デプロイ状態確認

### 認証
- 初回 Render MCP ツール呼び出し時にブラウザで Render アカウントへの許可を求められる
- 1回認証すれば以降はClaudeから直接操作可能

## 5. GitHub MCP (github-pat)

### 用途
- PR作成、Issue管理、コード検索
- ワークフロー実行、組織ナビゲーション

### 認証
- 既に `gh` CLI のPAT経由で接続済み（scopes: gist, read:org, repo, workflow）
- トークン更新時は `claude mcp remove github-pat && claude mcp add github-pat ...`
