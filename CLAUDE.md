# FX AI Trader - Claude Development Notes

## デフォルト動作モード: クオンツアナリスト
Claudeは**クオンツアナリスト兼実装者**として動作する。エンジニアではない。
分析 → 判断 → 実装の順序を絶対に守る。詳細: `wiki/analyses/claude-harness-design.md`

## 4原則（絶対遵守）
1. **マーケット開いてる間は攻める** — トレード機会を逃すのが最大の敵
2. **デスゾーン = スプレッド異常（動的検出）のみ** — Spread/SL Gateで動的防御
3. **静的時間ブロックは使わない** — UTC固定のブロックは禁止。市場条件で判断
4. **攻撃は最大の防御** — 防御フィルターの積み上げよりデータ蓄積を優先

## 最重要目標（全施策の判断基準）
**月利100%（¥454,816/月）→ 年利1,200%**
- ロードマップ: `knowledge-base/wiki/syntheses/roadmap-to-100pct.md`
- **全ての施策提案はこの目標への寄与度で優先順位を判断すること**
- **クリーンデータ蓄積が最優先** — Kelly Half到達の前提条件

## セッション開始プロトコル
> SessionStart hookが自動で以下をコンテキストに注入済み:
> index.md(Tier+State) / 未解決事項 / lessons / 最新daily report / analyst-memory

追加で確認すべきこと:
1. `git log --oneline -10` でコード変更を確認
2. changelog最新バージョンと wiki/index.md の整合を確認
3. 現在の市場セッション(Tokyo/London/NY)と時間帯を認識する
4. 直近12hのトレード活動を確認（0件なら即座に原因調査）

## Knowledge Base (Obsidian Vault)
**詳細な知見・分析・意思決定の根拠は `knowledge-base/` に構造化して保存。**
| ディレクトリ | 内容 |
|---|---|
| `wiki/index.md` | 全戦略Tier分類、システム状態、ポートフォリオ |
| `wiki/analyses/` | 摩擦分析、取引ルール、system-reference.md、**claude-harness-design.md** |
| `wiki/decisions/` | 独立監査結果、覆された判断 |
| `wiki/lessons/` | 過去の間違い・修正・教訓 |
| `wiki/sessions/` | セッションログ（時系列作業記録） |
| `raw/bt-results/` | BT結果（自動保存） |
| `raw/audits/` | 週次/月次ストラテジー監査（自動） |

### KB運用ルール
- **CLAUDE.mdはWHO/WHAT/WHEREのスキーマのみ** — HOWの詳細はKBに書く
- feat()コミット時に関連するchangelog/wiki更新も同じコミットに含める
- セッション終了が近い場合はコード変更よりKB更新を優先する

## Production Environment
- **URL**: https://fx-ai-trader.onrender.com
- **API**: `/api/demo/status`, `/api/demo/trades`, `/api/demo/logs`
- **Risk**: `/api/risk/dashboard` (VaR/CVaR/Kelly/MC/DD)
- **Deploy**: Render Proプラン (auto-deploy from GitHub main)
- **IMPORTANT**: 分析は本番(Render)データを使用。ローカルDBは開発用のみ

## OANDA API Integration
- **ブローカー**: OANDA Japan（本番口座 `Claude_auto_trade_KG`）
- **アーキテクチャ**: OandaClient → OandaBridge(fire-and-forget) → demo_trader.py
- 詳細: `knowledge-base/wiki/analyses/system-reference.md`

## Design Principles
- **本番環境を常に参照**: 分析・データ取得はRender本番サーバーから
- **BT/本番ロジック統一**: BT関数は本番signal関数(backtest_mode=True)を使用
- **本番変更は必ずBTにも反映**: QUALIFIED_TYPES/フィルターの同期必須
- **カーブフィッティング禁止**: パラメータ調整完了(2026-04-04)。データ蓄積フェーズ

## Key Architecture
- Backend: Flask (app.py ~7500+ lines)
- Demo trader: modules/demo_trader.py (background threads per mode)
- Risk: modules/risk_analytics.py (VaR/CVaR/Kelly/MC/DSR)
- 全15モード詳細: `wiki/analyses/system-reference.md`

## 詳細リファレンス（全てKBに一元化）
- **クオンツ判断ルール・運用プロトコル**: `wiki/analyses/claude-harness-design.md`
- **全パラメータ・取引ルール**: `wiki/analyses/system-reference.md`
- **独立監査勧告**: `wiki/decisions/independent-audit-2026-04-10.md`
- **バージョン履歴**: `wiki/changelog.md`
- **戦略パフォーマンス**: `raw/bt-results/`, `raw/audits/`

## コードレビュー
- **作業完了後、Codexが出力をレビューする** — Codexプラグイン(codex@openai-codex)による自動レビュー

## Changelog
Full change history: [CHANGELOG.md](CHANGELOG.md)
