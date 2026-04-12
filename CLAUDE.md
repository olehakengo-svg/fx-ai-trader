# FX AI Trader - Claude Development Notes

## セッション開始プロトコル
> SessionStart hookが自動で以下をコンテキストに注入済み:
> index.md(Tier+State) / 未解決事項 / lessons / 最新daily report / analyst-memory

追加で確認すべきこと:
1. `git log --oneline -10` でコード変更を確認
2. changelog最新バージョンと wiki/index.md の整合を確認

## 4原則（絶対遵守）
1. **マーケット開いてる間は攻める** — トレード機会を逃すのが最大の敵
2. **デスゾーン = スプレッド異常（動的検出）のみ** — Spread/SL Gateで動的防御
3. **静的時間ブロックは使わない** — UTC固定のブロックは禁止。市場条件で判断
4. **攻撃は最大の防御** — 防御フィルターの積み上げよりデータ蓄積を優先

## 最重要目標（全施策の判断基準）
**月利100%（¥454,816/月）→ 年利1,200%**
- 現在地: DD防御1.0x (v8.9 Equity Reset済) → 月利235%（BT推定）
- Phase 3 (Kelly Half): 月利594%
- ロードマップ: `knowledge-base/wiki/syntheses/roadmap-to-100pct.md`
- **全ての施策提案はこの目標への寄与度で優先順位を判断すること**
- **クリーンデータ蓄積が最優先** — Kelly Half到達の前提条件

## Knowledge Base (Obsidian Vault)
**詳細な知見・分析・意思決定の根拠は `knowledge-base/` に構造化して保存。**
| ディレクトリ | 内容 |
|---|---|
| `wiki/index.md` | 全戦略Tier分類、システム状態、ポートフォリオ |
| `wiki/strategies/` | 全戦略詳細 + エッジ仮説 + パイプライン（統合済み） |
| `wiki/concepts/` | 摩擦分析、取引ルール、**system-reference.md（全パラメータ）** |
| `wiki/decisions/` | 独立監査結果、覆された判断 |
| `wiki/lessons/` | 過去の間違い・修正・教訓 |
| `wiki/research/` | 学術文献インデックス（25論文） |
| `wiki/sessions/` | セッションログ（時系列作業記録） |
| `raw/` | BT結果、トレードログ、論文サマリ |

### KB運用ルール
- **CLAUDE.mdは150行以内のスキーマとして維持** — 詳細はKBに書く
- feat()コミット時に関連するchangelog/wiki更新も同じコミットに含める
- セッション終了が近い場合はコード変更よりKB更新を優先する

## 独立クオンツ監査（拘束力のある勧告）
詳細: `knowledge-base/wiki/decisions/independent-audit-2026-04-10.md`
- **bb_rsi × USD_JPYの保護が最優先** — フィルター実験は行わない
- **macdh→bb_rsi吸収は禁止** — 唯一のPF>1戦略を汚染するリスク
- **摩擦コスト削減が戦略改善に優先**

## Production Environment
- **URL**: https://fx-ai-trader.onrender.com
- **API**: `/api/demo/status`, `/api/demo/trades`, `/api/demo/logs`
- **Risk**: `/api/risk/dashboard` (VaR/CVaR/Kelly/MC/DD)
- **Deploy**: Render Proプラン (auto-deploy from GitHub main)
- **DB**: SQLite on Render Disk (`/var/data/demo_trades.db`)
- **IMPORTANT**: 分析は本番(Render)データを使用。ローカルDBは開発用のみ

## OANDA API Integration
- **ブローカー**: OANDA Japan（本番口座 `Claude_auto_trade_KG`）
- **API**: OANDA v20 REST API (`https://api-fxtrade.oanda.com/v3/`)
- **環境変数**: `OANDA_TOKEN`, `OANDA_ACCOUNT_ID`, `OANDA_LIVE=true`, `OANDA_UNITS=10000`
- **アーキテクチャ**: OandaClient → OandaBridge(fire-and-forget) → demo_trader.py
- **Tri-state制御**: LIVE / SENTINEL(0.01lot) / OFF / AUTO
- **ステータス**: `/api/oanda/status`, `/api/oanda/audit`, `/api/oanda/heartbeat`
- 詳細: `knowledge-base/wiki/concepts/system-reference.md`

## Design Principles
- **本番環境を常に参照**: 分析・データ取得はRender本番サーバーから
- **BT/本番ロジック統一**: BT関数は本番signal関数(backtest_mode=True)を使用
- **本番変更は必ずBTにも反映**: QUALIFIED_TYPES/フィルターの同期必須
- **カーブフィッティング禁止**: パラメータ調整完了(2026-04-04)。データ蓄積フェーズ

## Key Architecture
- Backend: Flask (app.py ~7500+ lines)
- Signal: compute_scalp_signal, compute_daytrade_signal, compute_hourly_signal, compute_swing_signal
- Demo trader: modules/demo_trader.py (background threads per mode)
- DB: SQLite WAL mode (modules/demo_db.py)
- Learning engine: modules/learning_engine.py (10トレード毎に自動調整)
- Risk: modules/risk_analytics.py (VaR/CVaR/Kelly/MC)
- Daily review: modules/daily_review.py (UTC 00:00自動実行)

## Trading Modes
| Mode | TF | Status |
|---|---|---|
| scalp | 1m | Active |
| scalp_5m | 5m | Active (Sentinel A/Bテスト) |
| scalp_eurjpy | 1m | Active (UTC 12-15限定) |
| daytrade | 15m | Active |
| daytrade_1h | 1h | Active (KSB+DMB) |
| swing | 4h | Disabled |

## 詳細リファレンス（KB移行済み）
- **全パラメータ・取引ルール・バージョン履歴**: `knowledge-base/wiki/concepts/system-reference.md`
- **バージョン別変更タイムライン**: `knowledge-base/wiki/changelog.md`
- **BT結果・戦略パフォーマンス**: `knowledge-base/raw/bt-results/`
- **戦略詳細**: `knowledge-base/wiki/strategies/`

## Changelog
Full change history: [CHANGELOG.md](CHANGELOG.md)
