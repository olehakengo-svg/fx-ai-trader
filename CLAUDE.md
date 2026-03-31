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

## BT Performance (as of 2026-03-31, Scalp v2.1 multi-strategy)
- Scalp: 84t WR=52.4% EV=+0.126 WF=2/3✅ (7d, 1m) — 3戦略レジーム型
- Daytrade: 2821t WR=47.8% EV=+0.102 WF=3/3✅ (55d, 15m)
- Swing: 346t WR=36.7% EV=+0.154 WF=2/3✅ (730d, 1d)

## Weekly BT Sample (2026-03-23〜31)
- 月 +285p | 火 +987p | 水 +936p | 木 +466p | 金 +111p | 月 +1210p | 火 +103p
- 全日100p以上 ✅（金曜も+111pで目標達成）

## Scalp v2.1 Algorithm (Multi-Strategy Regime-Based)
- **bb_rsi_reversion** (Bollinger 2001 + Wilder 1978): Tier1/Tier2、BB%B≤0.12/≥0.88 + RSI5<32/>68 + Stochクロス + 反転キャンドル + MACD-H反転ボーナス → 73t/week, EV+0.125
- **three_bar_reversal**: 3連続陰/陽線後の反転足 at BB極端 → 7t/week, EV+0.232
- **engulfing_bb**: 包み足パターン at BB極端+RSI+Stoch → 4t/week
- **bb_squeeze_breakout** (BLL 1992 JoF): BB幅下位5%+ADX≥20（1m足では低頻度）
- **london_breakout** (Ito & Hashimoto 2006): 07-09UTC、アジアレンジ突破
- **DISABLED**: rsi_divergence_sr (EV-0.605), stoch_trend_pullback (EV-0.255), macdh_reversal独立版 (bb_rsi_reversionに統合)
- **エントリー品質ゲート**: QUALIFIED_TYPES のみ許可、理由✅1つ以上必須
- **TP固定/SL可変**: TPはシグナル技術ターゲット、SLはエントリーからRR比逆算

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
- **DB接続リーク修正(B3)**: 全DB操作に_safe_conn()コンテキストマネージャ導入（try/finally保証）
- **メインループ停止条件(B4)**: 全モード停止時にループスレッド終了（リソース解放）
- **ドローダウン制御**: 日次-30pip / 最大DD -100pipで自動停止
- **BT現実的スプレッド**: scalp 0.5pip→1.5pip（現実的スプレッド反映）
- **HTF lookahead修正**: BT時HTFキャッシュをneutral化（先読みバイアス排除）
