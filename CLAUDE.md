# FX AI Trader - Claude Development Notes

## Production Environment
- **URL**: https://fx-ai-trader.onrender.com
- **API**: https://fx-ai-trader.onrender.com/api/demo/status
- **Logs**: https://fx-ai-trader.onrender.com/api/demo/logs
- **Deploy**: Render (auto-deploy from GitHub main branch)
- **IMPORTANT**: Always reference production (Render) data for analysis, NOT the local development DB. Local DB is for dev/testing only.

## Key Architecture
- Backend: Flask (app.py ~7800+ lines)
- Signal functions: compute_scalp_signal, compute_daytrade_signal, compute_swing_signal
- **BT/本番ロジック統一原則**: BT関数は本番のsignal関数を呼び出すこと（本番環境を正とする）
  - run_scalp_backtest → compute_scalp_signal(backtest_mode=True) を使用（統一済み）
  - run_daytrade_backtest, run_swing_backtest → 未統一（要対応）
- Demo trader: modules/demo_trader.py (background threads per mode)
- DB: SQLite WAL mode (modules/demo_db.py)
- Learning engine: modules/learning_engine.py

## Trading Modes
- scalp: 1m tf, 10s interval
- daytrade: 15m tf, 30s interval
- swing: 4h tf, 300s interval

## Design Principles
- **本番環境を常に参照**: 分析・データ取得はRender本番サーバーから行うこと（ローカルDBは開発用のみ）
- **BT/本番ロジック統一**: BT関数は本番のsignal関数を呼び出すこと。独自のエントリーロジックをBTに書かない

## Known Issues (as of 2026-03-31)
- ema_cross: ADX<15フィルター追加済み（旧WR 26.7% → 改善中）
- SELL方向: HTFソフトフィルター化でレンジ時BUY許容（改善済み）
- SL: ATR7×0.5→0.8に拡大、SLTPチェック間隔0.5秒化（改善済み）
- 時間帯フィルター: UTC 00,01,21禁止（損失94%集中帯）
- 連敗制御: 同方向3連敗で一時停止（追加済み）
