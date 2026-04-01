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
  - run_1h_backtest → compute_1h_zone_signal(backtest_mode=True)
  - run_swing_backtest → compute_swing_signal(backtest_mode=True)
- Demo trader: modules/demo_trader.py (background threads per mode)
- DB: SQLite WAL mode (modules/demo_db.py)
- Learning engine: modules/learning_engine.py (10トレード毎に自動調整)
- Daily review: modules/daily_review.py (UTC 00:00に自動実行)

## Trading Modes
- scalp: 1m tf, 10s interval
- daytrade: 15m tf, 30s interval
- daytrade_1h: 1h tf, 60s interval (Zone-based補完DT)
- swing: 4h tf, 300s interval

## Daily Target
- **目標: 100 pips/日（±20 許容 = 80〜120 pips/日）**
- スキャルプ + デイトレで達成
- スプレッド: 0.2 pip

## BT Performance (as of 2026-03-31, Scalp v2.2 + DT optimized + 1H Zone v2)
- **Combined: 92.7 ATR/day（目標80-120 達成）**
- Scalp: 1569t WR=63.5% EV=+0.359 WF=3/3✅ (7d, 1m) — 6戦略アクティブ
- Daytrade 15m: 149t WR=72.5% EV=+0.597 WF=3/3✅ (7d, 15m)
- Daytrade 1h(Zone): 158t WR=43.7% EV=+0.151 WF=3/3✅ (30d, 1h) — 39.5 pip/day
- Swing: 346t WR=36.7% EV=+0.154 WF=2/3✅ (730d, 1d)

## Scalp v2.2 Strategy Breakdown (7d BT)
- **bb_rsi_reversion**: 1077t WR=64.4% EV=+0.381 PnL=410.8p — BB%B≤0.25/≥0.75, RSI<45/>55, Stoch<45/>55
- **macdh_reversal**: 239t WR=61.1% EV=+0.336 PnL=80.2p — BB<0.25/>0.75, MACD-H方向転換
- **engulfing_bb**: 124t WR=60.5% EV=+0.192 PnL=23.8p — 包み足 at BB<0.30/>0.70
- **stoch_trend_pullback**: 107t WR=65.4% EV=+0.486 PnL=52.0p — ADX≥20, Stoch押し目回復
- **trend_rebound**: 5t WR=80.0% EV=+0.696 PnL=3.5p — ADX≥35, Stoch<12/>88, RSI<28/>72, BB<0.12/>0.88, 陽陰線確認
- **three_bar_reversal**: 4t — 低頻度
- **DISABLED**: rsi_divergence_sr (EV-0.607, ATR TPでも改善せず)
- **MAX_HOLD=40バー**, COOLDOWN=1, MIN_RR=1.2, ATR TP (Tier1:×2.0, Tier2:×1.5)

## DT Strategy Breakdown (7d BT)
- **sr_fib_confluence**: 31t WR=90.3% EV=+1.197 PnL=37.1p
- **ema_cross**: 105t WR=67.6% EV=+0.406 PnL=42.6p (ADX≥12)
- **dual_sr_bounce**: 12t WR=66.7% EV=+0.663 PnL=8.0p
- ema_score THRESHOLD=0.20, ATR TP floor=×1.5, MAX_HOLD=24バー, ADX≥12

## 1H Zone Strategy v2 (学術論文ベース)
- **コンセプト**: 前日のPivot Point (H+L+C)/3 を境にBuy Zone / Sell Zoneを定義
- **ゾーン更新**: 毎日UTC 00:00に前日OHLCから再計算
- **2戦略アクティブ** (4戦略中):
  - **mtf_momentum**: EMA9>21>50 + プルバック反発 (Moskowitz 2012 JFE) → 111t WR=45.0% ATR=19.2
  - **pivot_breakout**: R1/S1突破 + EMA整合 (Osler 2000 NY Fed) → 47t WR=40.4% ATR=4.7
- **DISABLED**: session_orb (WR=36.6% → ATR EVドラッグ), pivot_reversion (WR=30%)
- **MAX_HOLD**: 18バー（18時間、TP到達時間確保）
- **BT(30d)**: 158t WR=43.7% EV=+0.151 WF=3/3✅ (39.5 pip/day raw)
- **用途**: スキャルプ/DT補完、異なるタイムフレームでの分散

## Key Parameters
- **スプレッド**: 0.2 pip (全BT統一)
- **TP固定/SL可変**: TPはATRベース技術ターゲット、SLはRR比逆算(MIN_RR=1.2)
- **エントリー品質ゲート**: QUALIFIED_TYPES のみ許可、理由✅1つ以上必須

## Friday Filters (金曜対策)
- **Scalp**: 閾値0.6→3.5（高確信シグナルのみ）、tokyo_bb完全ブロック
- **DT (compute_daytrade_signal)**: 金曜UTC0-6のSR系(sr_fib_confluence等)ブロック、UTC18+全ブロック
- **DT (compute_signal)**: combined score減衰(×0.15)、Tokyo/NY午後ブロック
- **重要**: compute_daytrade_signalとcompute_signalは別関数。DT BTはcompute_daytrade_signalを使用

## Recent Fixes (2026-03-31 v2)
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
- **ウォッチドッグ自動復旧**: 60秒毎にrunning=Falseモードを自動復旧（B4 breakバグ対策）
- **max_open_trades**: 3→20（同モード重複エントリー許可、エントリーポイント発生時は複数ポジションOK）
- **auto_start二重起動防止**: _auto_start_doneフラグ（モジュール二重importレース対策）
- **stop()時_started_modes除去**: ウォッチドッグが明示stop済みモードを復旧しない
- **ドローダウン制御**: 日次-30pip / 最大DD -100pipで自動停止
- **BT現実的スプレッド**: scalp 0.5pip→1.5pip（現実的スプレッド反映）
- **HTF lookahead修正**: BT時HTFキャッシュをneutral化（先読みバイアス排除）
- **1H Zone v2**: compute_1h_zone_signal完全書き換え（学術論文ベース4戦略）
  - mtf_momentum (Moskowitz 2012), session_orb (Ito 2006), pivot_breakout (Osler 2000), pivot_reversion
  - session_orb, pivot_reversion はBT結果に基づきDISABLED
  - ゾーン制約: mtf_momentumはゾーン不問（トレンドフォロー）、pivot_breakoutはEMA整合必須
  - MAX_HOLD: 12→18バー（TP到達時間確保で WR +3%, ATR EV +75%）
- **DT 15m最適化**: ema_cross ADX閾値15→12, ema_score THRESHOLD 0.25→0.20
- **QUALIFIED_TYPES更新**: 1h新entry_types（mtf_momentum, session_orb, pivot_breakout, pivot_reversion）
- **リバウンド対策①**: 全方向サーキットブレーカー — 方向問わず直近30分N回負けでモード一時停止(scalp:4, DT:3)
- **リバウンド対策②**: 価格ベロシティフィルター — 直近10分で+8pip以上の急動方向に逆行するエントリーをブロック [Cont 2001]
- **リバウンド対策③**: ADXレジーム逆行ブロック — ADX≥35の強トレンド中にトレンド逆行エントリーを抑制(trend_rebound除く)
- **リバウンド対策④**: ブレイクイーブン+トレーリングストップ — 60%TP到達でSLをBE+0.5pip、80%TP到達でSLをTP50%地点に移動
