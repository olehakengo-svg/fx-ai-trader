# FX AI Trader - Claude Development Notes

## Production Environment
- **URL**: https://fx-ai-trader.onrender.com
- **API**: https://fx-ai-trader.onrender.com/api/demo/status
- **Logs**: https://fx-ai-trader.onrender.com/api/demo/logs
- **Deploy**: Render (auto-deploy from GitHub main branch)
- **IMPORTANT**: Always reference production (Render) data for analysis, NOT the local development DB. Local DB is for dev/testing only.

## Design Principles
- **本番環境を常に参照**: 分析・データ取得はRender本番サーバーから行うこと（ローカルDBは開発用のみ）
- **BT/本番ロジック統一**: BT関数は本番のsignal関数を呼び出すこと。独自のエントリーロジックをBTに書かない

## Key Architecture
- Backend: Flask (app.py ~7500+ lines)
- Signal functions: compute_scalp_signal, compute_daytrade_signal, compute_swing_signal
- **BT/本番ロジック統一完了**: 全BT関数がsignal関数(backtest_mode=True)を使用
  - run_scalp_backtest → compute_scalp_signal(backtest_mode=True)
  - run_daytrade_backtest → compute_daytrade_signal(backtest_mode=True)
  - run_swing_backtest → compute_swing_signal(backtest_mode=True)
- Demo trader: modules/demo_trader.py (background threads per mode)
- DB: SQLite WAL mode (modules/demo_db.py)
- Learning engine: modules/learning_engine.py (10トレード毎に自動調整)
- Daily review: modules/daily_review.py (UTC 00:00に自動実行)

## Trading Modes
- scalp: 1m tf, 10s interval
- daytrade: 15m tf, 30s interval
- swing: 4h tf, 300s interval

## BT Performance (as of 2026-03-31, Friday fix applied)
- Scalp: 4281t WR=46.6% EV=+0.110 (7d, 1m)
- Daytrade: 3916t WR=41.7% EV=+0.168 (55d, 15m)
- Swing: 346t WR=36.7% EV=+0.154 (730d, 1d)

## Weekly BT Sample (2026-03-23〜31)
- 月 +285p | 火 +987p | 水 +936p | 木 +466p | 金 +111p | 月 +1210p | 火 +103p
- 全日100p以上 ✅（金曜も+111pで目標達成）

## Friday Filters (金曜対策)
- **Scalp**: 閾値0.6→3.5（高確信シグナルのみ）、tokyo_bb完全ブロック
- **DT (compute_daytrade_signal)**: 金曜UTC0-6のSR系(sr_fib_confluence等)ブロック、UTC18+全ブロック
- **DT (compute_signal)**: combined score減衰(×0.15)、Tokyo/NY午後ブロック
- **重要**: compute_daytrade_signalとcompute_signalは別関数。DT BTはcompute_daytrade_signalを使用

## Recent Fixes (2026-03-31)
- BT/本番ロジック統一: 3モード全てsignal関数を使用
- ema_cross: ADX<15フィルター追加（旧WR 26.7% → 改善済み）
- HTFフィルター: レンジ時(ADX<20)はソフトバイアスに変更（SELL偏重解消）
- SL: ATR7×0.5→0.8に拡大、SLTPチェック間隔0.5秒化
- 時間帯フィルター: UTC 00,01,21禁止（損失94%集中帯）
- 連敗制御: 同方向3連敗で一時停止
- 重複エントリー防止: 同方向ポジション+近接価格チェック
- SIGNAL_REVERSE最低保持時間: scalp 60s, daytrade 300s, swing 3600s
- Swing signal: 閾値0.15→2.5/6.0, SL/TP 2.5/4.5→1.0/2.5, SR近接スコアリング追加
- **金曜フィルター**: scalp閾値3倍、tokyo_bbブロック、DT SR系ブロック(UTC<7)
- **tokyo_bb entry_type修正**: 早期リターンにentry_type追加（BT分析精度向上）
- **HTF cache修正**: compute_daytrade_signalのHTFバイアスもhtf_cacheを使用（BT時）
- **EMA spread multiplier**: ema_pullbackスコアをEMA9-21スプレッドで調整
- **SL後クールダウン**: 直近exit後に同方向/同価格帯の即再エントリー禁止(scalp120s/DT600s/swing7200s)
- **SIGNAL_REVERSE保持延長**: scalp60→180s, DT300→600s（ウィップソー防止）
- **Layer1方向チェック**: demo_traderでlayer1(bull/bear)逆行トレードをブロック
- **sr_fib_confluence閾値**: 0.20→0.35 + EMA方向整合必須（本番0%WR対策）
- **dual_sr_bounce**: EMA方向一致を条件追加（本番0%WR対策）
- **自動起動**: サーバー起動時に全3モード自動起動（Render再起動対策）
- **スレッド耐性**: 連続エラー時のバックオフ追加（スレッド停止防止）
