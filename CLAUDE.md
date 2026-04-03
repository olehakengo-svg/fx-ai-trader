# FX AI Trader - Claude Development Notes

## Production Environment
- **URL**: https://fx-ai-trader.onrender.com
- **API**: https://fx-ai-trader.onrender.com/api/demo/status
- **Logs**: https://fx-ai-trader.onrender.com/api/demo/logs
- **Deploy**: Render **Proプラン** (auto-deploy from GitHub main branch)
- **DB**: SQLite on Render Disk (`/var/data/demo_trades.db`) — 永続ストレージ（1GB）。環境変数 `DB_PATH` で制御。ローカル開発時は `DB_PATH` 未設定でプロジェクト直下の `demo_trades.db` を使用
- **IMPORTANT**: Always reference production (Render) data for analysis, NOT the local development DB. Local DB is for dev/testing only.

## OANDA API Integration
- **ブローカー**: OANDA Japan（本番口座 — サブアカウント `Claude_auto_trade_KG`）
- **API**: OANDA v20 REST API (`https://api-fxtrade.oanda.com/v3/`)
- **認証**: Bearer token (`OANDA_TOKEN`) — サブアカウントから発行
- **アカウントID**: `001-009-21129155-002` (ヘッジング有効)
- **環境変数**: `OANDA_TOKEN`, `OANDA_ACCOUNT_ID`, `OANDA_LIVE=true`, `OANDA_UNITS=10000`(0.1 lot)
- **アーキテクチャ**: OandaClient(薄いAPIラッパー) → OandaBridge(ビジネスロジック, fire-and-forget) → demo_trader.py
- **設計**: デモシステムは独立稼働、OANDA連携はオプショナル。OANDA障害時もデモトレードは継続
- **連携ポイント**: エントリー(market_order) / SL/TP決済(close_trade) / シグナル反転(close_trade) / トレーリングSL(modify_trade) / 手動クローズ(close_trade)
- **ステータス**: `/api/oanda/status` で確認可能

## Design Principles
- **本番環境を常に参照**: 分析・データ取得はRender本番サーバーから行うこと（ローカルDBは開発用のみ）
- **BT/本番ロジック統一**: BT関数は本番のsignal関数を呼び出すこと。独自のエントリーロジックをBTに書かない
- **本番変更は必ずBTにも反映**: 本番で戦略の有効化/無効化、フィルター追加、パラメータ変更を行った場合、BT側のQUALIFIED_TYPESやフィルターも必ず同期すること。BT結果が本番と乖離しないようにする

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

## BT Performance (as of 2026-04-03, Scalp v2.4 + DT v2 + 1H Zone v4)
- Scalp: 676t WR=58.6% EV=+0.269 WF=3/3✅ (7d, 1m) — 7戦略アクティブ
- Daytrade 15m: 1435t WR=65.2% EV=+0.283 WF=3/3✅ (7d, 15m) — 3戦略
- Daytrade 1h(Zone): 22t WR=45.5% EV=+0.415 WF=3/3✅ (60d, 1h)
- Swing: 346t WR=36.7% EV=+0.154 WF=2/3✅ (730d, 1d)

## Scalp v2.4 Strategy Breakdown (7d BT)
- **bb_rsi_reversion**: 347t WR=58.5% EV=+0.247 — BB%B≤0.25/≥0.75, RSI<45/>55, Stoch<45/>55, ADX<32, Stochクロスギャップ>1.5
- **macdh_reversal**: 172t WR=57.6% EV=+0.175 — BB<0.25/>0.75, MACD-H方向転換（平均回帰戦略→ソフトペナルティ）
- **stoch_trend_pullback**: 85t WR=61.2% EV=+0.524 — ADX≥18, Stoch押し目回復
- **fib_reversal**: 61t WR=57.4% EV=+0.293 — フィボ38.2%/50%/61.8%反発, マルチルックバック(45/60)
- **bb_squeeze_breakout**: 5t WR=60.0% EV=+0.464 — BBスクイーズ後ブレイクアウト
- **v_reversal**: 5t WR=80.0% EV=+0.520 — V字反転
- **trend_rebound**: 1t — ADX≥35, 極端逆転（低頻度）
- **mtf_reversal_confluence**: ライブ専用（HTFキャッシュBT非対応）— RSI+MACD多時間軸一致
- **DISABLED**: rsi_divergence_sr (EV-0.607), engulfing_bb, sr_channel_reversal, hs_neckbreak
- **MAX_HOLD=40バー**, COOLDOWN=1, MIN_RR=1.2, ATR TP (Tier1:×2.0, Tier2:×1.5)
- **平均回帰戦略除外**: bb_rsi_reversion, macdh_reversal, v_reversal, trend_rebound はEMA200/HTFハードフィルター対象外（ソフトペナルティのみ）

## DT v2 Strategy Breakdown (7d BT)
- **ema_cross**: 1184t WR=63.8% EV=+0.243 (ADX≥12)
- **sr_fib_confluence**: 249t WR=71.9% EV=+0.474
- **ihs_neckbreak**: 2t WR=50.0% EV=+0.285 — 低頻度
- **dt_fib_reversal**: フォールバック — フィボ38.2%/50%/61.8%反発
- **dt_sr_channel_reversal**: フォールバック — SR/チャネルバウンス
- **ema200_trend_reversal**: フォールバック — EMA200ブレイクリテスト
- ema_score THRESHOLD=0.20, ATR TP floor=×1.5, MAX_HOLD=24バー, ADX≥12

## 1H Zone Strategy v4 (SR Breakout Retest + HTFフィルター)
- **コンセプト**: 前日のPivot Point (H+L+C)/3 を境にBuy Zone / Sell Zoneを定義
- **ゾーン更新**: 毎日UTC 00:00に前日OHLCから再計算
- **戦略構成**:
  - **h1_breakout_retest**: 22t WR=45.5% EV=+0.415 — 強SR(strength≥0.5, touches≥3)ブレイク後リテスト
    - BUY: 14t WR=57% / SELL: 8t WR=25%
    - HTFトレンドフィルター: 4H(EMA9/21) + 1D(EMA50/200)方向整合
    - ブレイク品質フィルター: ブレイク足の実体>0.3-0.5ATR必須
    - SL=0.8ATR, TP=4.0ATR, inv=0.9ATR
    - 必須条件: 陽線+EMA9>21(BUY) / 陰線+EMA9<21(SELL)
  - **h1_fib_reversal**: フォールバック — フィボ120バー反発
  - **h1_ema200_trend_reversal**: フォールバック — EMA200リテスト, ADX≥15
- **DISABLED**: h1_sr_reversal (WR=25%), mtf_momentum, session_orb, pivot_breakout, pivot_reversion
- **MAX_HOLD**: 30バー, BE at 70% TP, Trail 1.2 ATR
- **BT(60d)**: 22t WR=45.5% EV=+0.415 WF=3/3✅ Sharpe=3.742 MaxDD=4.7pip
- **用途**: スキャルプ/DT補完、異なるタイムフレームでの分散

## Key Parameters
- **スプレッド**: デモ本番=OANDAリアルbid/ask（エントリーBUY=ask/SELL=bid、決済BUY=bid/SELL=ask）、BT=0.2pip固定
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
- **Scalp v2.3リバーサル追加**: sr_channel_reversal(SR/チャネル反発), fib_reversal(フィボ反発), mtf_reversal_confluence(MTF RSI+MACD一致)
- **DT v2リバーサル追加**: dt_fib_reversal, dt_sr_channel_reversal, ema200_trend_reversal（フォールバック戦略）
- **1H Zone v3**: h1_fib_reversal(フィボ120バー反発, EMA必須→ボーナス), h1_ema200_trend_reversal(EMA200リテスト, ADX≥15)
- **スレッド自己回復強化**: get_status()でMainLoop/Watchdog/SLTP/全モードを自動復旧、BaseException catch、request_tick fallback
- **Gunicorn gthread**: --worker-class gthread + timeout 300s（スレッド安定化）

## Recent Fixes (2026-04-03 本番データ分析ベース最適化)
- **DT HTFハードフィルター**: htf_agreement=bull時のSELL完全ブロック（スコア×0.50 → return WAIT）。本番12連敗-101pip防止
- **サーキットブレーカー実装**: _total_losses_windowを使い30分内N回負けでモード一時停止(scalp:4, DT:3, 1H:2)
- **DT同方向ポジ上限**: 5→2、同価格距離: 1.5→5pip、クールダウン: 300→600s（マシンガンエントリー防止）
- **pivot_breakout無効化**: 本番WR=0%(3t -66.4pip)、BT/本番両方のQUALIFIED_TYPESから除外
- **max_consecutive_losses**: 9999→3（同方向連敗制御を有効化）
- **スキャルプ強化**: 同方向ポジ2→3、同価格距離1.5→1.0pip、クールダウン120→60s（好調WR=56.4%のエントリー機会増）
- **BT QUALIFIED_TYPES統一**: scalp(engulfing_bb,hs_neckbreak,sr_channel_reversal無効化)、DT(hs_neckbreak,ob_retest無効化)、1H(pivot_breakout無効化)を本番と一致
- **スキャルプEMA200ハードフィルター**: EMA200上+スロープ上昇中のSELL完全ブロック（本番macdh_reversal|SELL WR=0% -15.4pip対策）
- **スキャルプHTFハードフィルター**: HTF bull時SELL完全ブロック、bear時BUY完全ブロック（ソフト減衰score×0.6→完全ブロック）
- **OANDA v20サブアカウント接続**: Claude_auto_trade_KG (001-009-21129155-002)、hedgingEnabled=true、APIトークン再発行で403解消

## Recent Fixes (2026-04-03 1H Zone v4 + Scalp最適化)
- **1H Zone v4完全書き換え**: 旧6戦略(mtf_momentum,session_orb,pivot_breakout等)を廃止、h1_breakout_retest中心に再構築
  - **h1_breakout_retest**: 強SR(strength≥0.5, touches≥3)ブレイク後のリテストエントリー(Bulkowski 2005)
  - ブレイク品質フィルター: ブレイク足実体>0.3-0.5ATR必須（ノイズブレイク排除）
  - HTFトレンドフィルター: 4H(EMA9/21) + 1D(EMA50/200 + EMA50スロープ24本)方向整合
  - Strong bullトレンド中のSELLブロック / Strong bearトレンド中のBUYブロック
  - HTFトレンドボーナス: 4H+1D合致で+0.5、1D合致で+0.3
  - SL=0.8ATR（0.5は1Hノイズで1barストップ多発、1.0はWR崩壊）
  - TP=4.0ATR、BE at 70%TP、Trail 1.2ATR、MAX_HOLD=30バー
  - h1_sr_reversal無効化（WR=25%）
- **bb_rsi_reversion ADX閾値**: 35→28→32（28では件数半減、32で頻度とWRのバランス最適化）
- **bb_rsi_reversion Stochクロスギャップ**: (stoch_k - stoch_d) > 1.5 必須（ノイズクロス排除）
- **bb_rsi_reversion 前バー方向確認**: BUY時は前バー陰線、SELL時は前バー陽線を必須化
- **stoch_trend_pullback頻度増加**: ADX閾値20→18、RSI/Stoch/BBpbレンジ拡大
- **fib_reversalマルチルックバック**: lookback 60→[45,60]、フィボ近接判定0.25→0.35ATR
- **macdh_reversal平均回帰分類修正**: _mean_reversion_typesに追加（EMA200/HTFハードフィルター→ソフトペナルティ）
  - 修正前: 56t WR=53.6% EV=+0.171 → 修正後: 172t WR=57.6% EV=+0.175（BUY WR 44%→62%回復）
- **Async chunked BT**: /api/backtest-long エンドポイント追加、7日チャンクの非同期BT処理（30日+BTのRenderタイムアウト回避）
- **BT mode=daytrade_1h追加**: /api/backtest?mode=daytrade_1h でrun_1h_backtest呼び出し可能に

## Recent Fixes (2026-04-03 OANDA Spread + Position Sync)
- **OANDAリアルスプレッド反映**: デモのエントリー/決済にOANDA bid/askを使用（固定mid→実スプレッド）
  - エントリー: BUY=ask価格, SELL=bid価格（OANDAと同じ約定ロジック）
  - SL/TP判定: BUYポジ=bid, SELLポジ=ask（決済もスプレッド反映）
  - SIGNAL_REVERSE/手動クローズも同様にbid/ask決済
  - `fetch_oanda_bid_ask()` 新設 → bid/ask/spread/midを返す
- **Demo→OANDAポジション同期**: デモ側CLOSEだがOANDA側OPENの孤児ポジを5秒毎に検出・自動クローズ
  - `_sync_demo_to_oanda()`: OANDA openTradesを取得、デモ側マッピングにないトレードをクローズ
  - デモを正（source of truth）として、OANDA孤児を解消
- **OANDA連携ポイント**: エントリー(ask/bid) / SL/TP(bid/ask) / シグナル反転(bid/ask) / 手動(bid/ask) / 孤児クローズ(5秒毎)

## Recent Fixes (2026-04-03 FXアナリストレビュー対応)
- **P0 BEスプレッド補正**: BE移動時にBUY=entry+spread, SELL=entry-spread（偽BE勝ち防止）
- **P1 BT時間帯変動スプレッド**: `_bt_spread(bar_time, symbol)` — 東京早朝0.8pip, LDN/NY 0.2pip, NY終盤0.8pip。全8BT関数に適用
- **P1 通貨ペア別ポジション管理**: max_open_trades=4(安全上限) + 通貨ペア別1本制限。USD/JPYとEUR/USDが独立稼働
- **P2 SL技術的位置決め**: SR外側(nearest_support/resistance - ATR×0.3) > ATRベース(×0.8/1.0/1.5) の優先順。RR>=1.0保証
- **P2 戦略自動昇格**: デモで全戦略トレード → N≥30かつEV>0でOANDA昇格 / EV<-0.5で降格。10トレードごとに再評価
  - `/api/demo/status` の `strategy_promotion` で確認可能
  - デモ=データ蓄積、OANDA=実績ベース選別
- **BT/本番パラメータ統一**: BE=60%(トレーリングなし)、クールダウン=1バー、時間帯制限なし
- **EUR/USD pips計算修正**: realized_pl/units→price-diff方式（demo_db.py）
- **EUR/USD丸め修正**: round(x,3)→_rp(x,symbol)で5桁対応（app.py全signal関数）
