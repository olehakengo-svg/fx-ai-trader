# FX AI Trader

AI駆動のFXトレーディングシステム。デモトレーダーによる自動シグナル生成・ポジション管理と、OANDA連携による実弾トレードをサポート。

## Quick Start (ローカル開発)

### 1. リポジトリのクローン

```bash
git clone https://github.com/olehakengo-svg/fx-ai-trader.git
cd fx-ai-trader
```

### 2. Python 環境セットアップ

```bash
python3.11 -m venv venv
source venv/bin/activate    # macOS/Linux
# venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

### 3. 環境変数 (ローカル開発ではオプション)

```bash
cp .env.example .env
# .env を編集 (ローカル開発では全項目オプション)
```

> OANDA認証情報なしでもデモトレーダーは完全に動作します。

### 4. 起動

```bash
python app.py
# → http://localhost:5000
```

### 5. テスト

```bash
pytest tests/ -v
```

## 開発フロー

### ブランチ戦略

```
main (本番) ← 直接pushは禁止
  ↑ PR + レビュー + CI通過
feature/xxx ← ここで開発
```

### 作業手順

```bash
# 1. 最新mainを取得
git checkout main && git pull

# 2. 作業ブランチ作成
git checkout -b feature/my-change

# 3. 実装 & テスト
pytest tests/ -v

# 4. コミット & プッシュ
git add <files>
git commit -m "feat: 変更内容の説明"
git push -u origin feature/my-change

# 5. GitHub でPR作成 → レビュー → マージ
```

### コミットメッセージ規約

```
feat: 新機能追加
fix: バグ修正
refactor: リファクタリング
test: テスト追加・修正
docs: ドキュメント更新
perf: パフォーマンス改善
```

## アーキテクチャ概要

```
app.py                    # Flask アプリケーション (API + UI)
modules/
  demo_trader.py          # デモトレーダー (バックグラウンドスレッド)
  demo_db.py              # SQLite データベース層
  oanda_client.py         # OANDA API クライアント (薄いラッパー)
  oanda_bridge.py         # OANDA ビジネスロジック (fire-and-forget)
  learning_engine.py      # 自動学習エンジン
  daily_review.py         # 日次レビュー
strategies/
  base.py                 # StrategyBase / Candidate 基底クラス
  context.py              # SignalContext (全戦略共通コンテキスト)
  scalp/                  # スキャルプ戦略群 (1m/5m)
  daytrade/               # デイトレ戦略群 (15m)
  hourly/                 # 1H戦略群
tests/                    # テストスイート
```

## 主要API エンドポイント

| エンドポイント | 説明 |
|---------------|------|
| `/api/demo/status` | デモトレーダー稼働状態 |
| `/api/demo/logs` | アクティビティログ |
| `/api/oanda/status` | OANDA接続ヘルスチェック |
| `/api/config/oanda_control` | 戦略別 LIVE/SENTINEL/OFF 制御 |
| `/api/oanda/audit` | トレード実行監査ログ |

## 本番環境 (Render)

- **URL**: Render ダッシュボードで確認
- **デプロイ**: main ブランチへのマージで自動デプロイ
- **DB**: `/var/data/demo_trades.db` (永続ディスク)
- **環境変数**: Render ダッシュボードで管理 (OANDA認証情報等)

## 注意事項

- 本番の OANDA 認証情報は**絶対に** Git にコミットしないこと
- ローカルの `demo_trades.db` は開発用。分析は本番データを参照
- 戦略パラメータの変更は CLAUDE.md の「Design Principles」を確認
- `QUALIFIED_TYPES` の変更はBT側との同期が必須
