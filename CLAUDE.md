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
- BT functions: run_scalp_backtest, run_daytrade_backtest, run_swing_backtest (have their OWN entry logic separate from signal functions)
- Demo trader: modules/demo_trader.py (background threads per mode)
- DB: SQLite WAL mode (modules/demo_db.py)
- Learning engine: modules/learning_engine.py

## Trading Modes
- scalp: 1m tf, 10s interval
- daytrade: 15m tf, 30s interval
- swing: 4h tf, 300s interval

## Known Issues (as of 2026-03-31)
- ema_cross accounts for 66% of entries but has WR 26.7% and EV -1.0 (worst performer)
- SELL direction WR=23% vs BUY WR=32% - directional imbalance
- 13-trade losing streak observed (trades #89-101, all SELL SL_HIT)
- SL too tight on scalp (ATR7 x 0.5 = ~1.3 pips) causing high SL_HIT rate
- HTF hard filter forces single direction, missing range reversals
