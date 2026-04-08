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
- **転送司令部 (Command Center)**: `/api/config/oanda_control` で戦略ごとに LIVE/SENTINEL/OFF/AUTO を即時切替
- **Tri-state制御**: LIVE(フルロット) / SENTINEL(0.01lot観測) / OFF(停止) / AUTO(自動昇降格判定)
- **実行監査**: `/api/oanda/audit` でトレードごとのOANDA連携成否・理由・OrderIDを確認
- **ヘルスチェック**: `/api/oanda/heartbeat` で60秒間隔のAPI接続状態・レイテンシ・口座残高を確認
- **🔗ログラベル**: エントリー時に `🔗 OANDA: [SENT/FILLED/FAILED/BLOCKED/SKIP]` ログを出力
- **指値ログ**: `🔗 OANDA: [LIMIT_PLACED]` (指値設置) / `🔗 OANDA: [LIMIT_FILL]` (指値到達→注文)

## Design Principles
- **本番環境を常に参照**: 分析・データ取得はRender本番サーバーから行うこと（ローカルDBは開発用のみ）
- **BT/本番ロジック統一**: BT関数は本番のsignal関数を呼び出すこと。独自のエントリーロジックをBTに書かない
- **本番変更は必ずBTにも反映**: 本番で戦略の有効化/無効化、フィルター追加、パラメータ変更を行った場合、BT側のQUALIFIED_TYPESやフィルターも必ず同期すること
- **カーブフィッティング禁止**: パラメータ調整フェーズ完了（2026-04-04）。今後は本番データ蓄積・摩擦監視フェーズ
- **BT摩擦モデルv2**: Phase A(ペア別spread+slippage), B(wick 0.3→0.1), C(SIGNAL_REVERSE BT実装), D(cascade CD+post-SL block) 全BT統合済み(2026-04-07)

## Key Architecture
- Backend: Flask (app.py ~7500+ lines)
- Signal functions: compute_scalp_signal, compute_daytrade_signal, compute_hourly_signal, compute_swing_signal
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
| Mode | TF | Interval | COOLDOWN | Status |
|---|---|---|---|---|
| scalp | 1m | 10s | 60s (1 bar, EXIT-based) | Active |
| daytrade | 15m | 30s | 900s (1 bar, EXIT-based) | Active |
| daytrade_1h | 1h | 60s | 3600s (EXIT-based) | **Active** — HourlyEngine v5.0 (KSB+DMB) |
| scalp_eurjpy | 1m | 10s | 60s (EXIT-based) | **Active** — UTC 12-15限定, bb_rsi |
| swing | 4h | 300s | 14400s (1 bar, EXIT-based) | Disabled |

## Daily Target
- **目標: 100 pips/日（±20 許容 = 80〜120 pips/日）**
- スキャルプ + デイトレで達成

## BT Performance (as of 2026-04-07, v5.95 統合監査 + Pair Lifecycle)
- **v5.95 統合BT**: 340t/14d (5m scalp + 15m DT), 摩擦モデルv2, SAR=1.57 (v5.5: 0.42, 3.7x改善)
- **月間PnL**: Raw +857pip → **LC適用 +1,831pip/月** (lifecycle uplift +107%)
- Scalp USD/JPY: 76t WR=65.8% EV=+0.211ATR (fib_reversal WR=86.7% → 1.5x boost)
- Scalp EUR/USD: 40t WR=57.5% (bb_rsi DEMOTED: WR=20% EV=-1.5)
- Scalp GBP/USD: 59t WR=50.8% (macdh DEMOTED: WR=40% EV=-0.818, limit-only enforcement)
- Scalp EUR/JPY: 59t WR=54.2% (vol_surge/bb_squeeze positive, bb_rsi negative)
- DT USD/JPY: 34t WR=61.8% (sr_fib_confluence WR=76.9% → 1.3x boost)
- DT EUR/USD: **27t WR=74.1% EV=+0.647ATR** (orb_trap/htf_fbk/london_ny 1.5x boost)
- DT GBP/USD: **45t WR=66.7% EV=+0.634ATR** (gbp_deep_pullback 2.0x, trendline_sweep 1.5x)
- **1H EUR/USD: 70t WR=50% +483pip** (120d, 1h, KSB+DMB)
- **1H USD/JPY: 40t WR=35% +181pip** (120d, 1h, DMB only, SELL非対称フィルター)
- **Scalp EUR/JPY: 250t WR=45.6% +300pip EV=+1.20** (60d, 5m, UTC 12-15限定)
- Swing: 346t WR=36.7% EV=+0.154 WF=2/3 (730d, 1d)

## Scalp v3.2 Strategy Breakdown (7d BT, bb_rsi Option C適用後)
| Strategy | Trades | WR | EV | Description |
|---|---|---|---|---|
| **bb_rsi_reversion** | **181** | **61.3%** | **+0.173** | **Option C: EUR ADX<25 / JPY ADX制限なし+Death Valley/Gold Hours** |
| macdh_reversal | 144 | 63.2% | +0.231 | BB<0.25/>0.75, MACD-H方向転換 (mean-reversion, soft penalty) |
| fib_reversal | 172 | 57.0% | +0.056 | Fib 38.2%/50%/61.8%反発, multi-lookback(45/60) |
| bb_squeeze_breakout | 19 | 36.8% | -0.799 | BB squeeze breakout, ADX>=20 |
| mtf_reversal_confluence | 4 | 50.0% | -0.187 | RSI+MACD AND (HTF cache incompatible with BT) |
| session_vol_expansion | EUR only | — | — | SVE: London open compression breakout (UTC 07:00-08:30) |

- **bb_rsi Option C (2026-04-04)**: USD/JPY ADX制限撤廃(トレンド中WR=60%), Death Valley(UTC 00-01,09,12-16)ブロック, Gold Hours(UTC 05-08,19-23)スコア+0.8(v6.3), ADX>=30スコア+0.6, Tier1 TP=2.2(v6.3)
- **Confluence Scalp v2 (2026-04-07)**: Triple Confluence + MSS戦略。Session Gate(UTC 12-17) + MFE Guard(ATR/Spread>=10) + HTF Hard Block + 3理論族合意(EMA+RSI/BB+MACD-H) + CHoCH/MSB構造転換検出。Profit Extender(TP延伸+Climax Exit), Friction Minimizer(指値遅延エントリー)

### v6.3 Sentinel対策 (2026-04-08) — 切除ではなく改善
**設計思想**: 負EV戦略を切除(FORCE_DEMOTED)するのではなく、根本原因(摩擦、パラメータ、フィルター不足)を特定し具体的に改善する。
- **ema_ribbon_ride**: Relaxed PO→**Strict PO(9>21>50)**, ADX 18→**25**, DI gap≥5必須, TP 1.5→**1.2**, UTC 0-6**完全ブロック**, BB幅≥0.35, 足実体≥40%
- **fib_reversal**: Fib proximity 0.50→**0.35**, SL 0.5→**0.7**ATR, **ペア別TP**(JPY=1.8/EUR,GBP=1.3), 足実体≥50%, EUR/GBP UTC 0-5ブロック
- **macdh_reversal**: **Tier化**(BB≤0.15=Tier1 TP1.8/通常TP1.5), MACD-H反転**強度フィルター**(delta≥平均50%), Death Valley(UTC 0,1,9 JPY)適用
- **vol_surge_detector**: 発火率改善: vol倍率 2.0→**1.7**, Climax BB%B 0.10→**0.15**, RSI 30→**35**, TP 1.0→**1.3**, JPYセッション 12-23→**17-23**縮小, バーレンジATR比率チェック追加
- **vol_momentum_scalp**: ADX 20→**25**, DI gap≥**8**必須, SL 0.8→**1.0**(pullback吸収), BB幅 0.35→**0.45**, RSI過熱 85/15→**80/20**
- **bb_rsi_reversion**: USD_JPY **PAIR_PROMOTED**(Sentinel bypass), Gold Hours +0.5→**+0.8**, Tier1 TP 2.0→**2.2**
- **Rolling EV Monitor**: `_check_rolling_ev()` — 戦略EV急落(drop≥0.2 & EV<-0.3)を自動検出・アラート
- **spread_at_exit修正**: OANDA決済パス+SIGNAL_REVERSE決済パスにspread_at_exit追加

- **DISABLED**: stoch_pullback, ema_pullback, trend_rebound, engulfing_bb, three_bar_reversal, sr_channel_reversal
- **SL floor**: ATR(14)x1.0 minimum (ScalperEngine/DaytradeEngine unified)
- **MAX_HOLD=40 bars**, MIN_RR=1.2

## DT v4.4 Strategy Breakdown (55d BT, +ORB Trap/GBP Deep PB採用)
| Strategy | EUR Trades | EUR WR | EUR EV | JPY Trades | JPY WR | JPY EV | GBP Trades | GBP WR | GBP EV | Description |
|---|---|---|---|---|---|---|---|---|---|---|
| sr_fib_confluence | 82 | 63.4% | +0.223 | 84 | 64.3% | +0.286 | 80 | 68.8% | +0.414 | ADX>=20, layer3 SR/Fib detection |
| **orb_trap** | **42** | **71.4%** | **+0.482** | **29** | **79.3%** | **+0.617** | **28** | **64.3%** | **+0.245** | **ORB Trap: Opening Range Fakeout Reversal** |
| **sr_break_retest** | **—** | **—** | **—** | **63** | **63.5%** | **+0.236** | **42** | **61.9%** | **+0.159** | **SBR: Fractal SR B&R (Edwards&Magee 1948)** |
| htf_false_breakout | 32 | 65.6% | +0.507 | 24 | 70.8% | +0.545 | 40 | 72.5% | +1.011 | FBF: 1H SR False Breakout Fade (Bulkowski 2005) |
| **gbp_deep_pullback** | **—** | **—** | **—** | **—** | **—** | **—** | **38** | **73.7%** | **+0.543** | **GBP Deep PB: BB-2σ/EMA50 deep pullback** |
| lin_reg_channel | 22 | 63.6% | +0.277 | — | — | — | — | — | — | LRC: Linear Regression Channel MR (EUR専用) |
| **adx_trend_continuation** | **14** | **85.7%** | **+2.045** | **—** | **—** | **—** | **—** | **—** | **—** | **ADX TC: EUR専用トレンド押し目 (Wilder 1978)** |
| **tokyo_nakane_momentum** | **—** | **—** | **—** | **10** | **70.0%** | **+0.086** | **—** | **—** | **—** | **TNM: 仲値DOWN→BUY専用 (Andersen 2003)** |
| ema_cross | 9 | 77.8% | +0.963 | 3 | 66.7% | +0.014 | 6 | 50.0% | +0.028 | **Hardened v2**: ADX≥25↑ OR 1H ADX≥22 |
| ~~london_close_reversal~~ | ~~11~~ | ~~54.5%~~ | ~~+0.019~~ | ~~—~~ | ~~—~~ | ~~—~~ | ~~—~~ | ~~—~~ | ~~—~~ | ~~DISABLED: 44t avg EV≈0, N不足~~ |
| ~~london_session_breakout~~ | ~~10~~ | ~~10%~~ | ~~-9.9~~ | ~~—~~ | ~~—~~ | ~~—~~ | ~~—~~ | ~~—~~ | ~~—~~ | ~~DISABLED: WR=10% — ORB Trapに置換~~ |

- **ORB Trap (2026-04-05)**: Opening Range Breakout Trap。LDN(UTC 07:00-07:30)/NY(UTC 13:30-14:00)のORを計測→Close実体ブレイク→レンジ内回帰(フェイクアウト)→逆方向エントリー。LSB WR=10%の裏返し(90%のフェイクアウトを利用)。全3ペア対応、BUY WR=100%(JPY)が特徴的
- **GBP Deep PB (2026-04-05)**: ADX TCのGBP/USD特化版。ADX≥20+EMA9>21+BB-2σ(bbpb≤0.10)orEMA50ゾーン到達→反転足+EMA21回復確認。標準ADX TCのEMA9-21浅い押し目ではGBPのボラに対応不可→深い押し目(BB/EMA50)要求で解決
- **LCR DISABLED (2026-04-05)**: London Close Reversal。UTC 15:00-16:15のwick≥60%+range/ATR≥0.8で反転検出。15m BT: EUR 11t EV≈0, GBP 3t WR=0% → edge不十分、N不足。5m BT未実施
- **SBR (2026-04-05)**: SR Break & Retest。Fractal(n=3)でSR検出→Close実体ブレイク→±0.7ATRリテスト→反転確認。USD/JPY+GBP/USD専用(EUR/USD EV≈0で除外)。HFBの鏡像戦略=負相関で最大分散
- **ADX TC (2026-04-04)**: EUR/USD専用トレンドフォロー。ADX≥25+EMAパーフェクトオーダー(9>21>50)+前1-3本プルバック検出→現在足リバウンド確認。USD/JPYはDISABLED(WR=50%/EV=-0.719、15m足トレンドノイジー)
- **Mean-reversion exclusion**: bb_rsi, macdh, v_reversal, trend_rebound exempt from EMA200/HTF hard filter (soft penalty only)

## Key Parameters
- **Spread**: Production=OANDA real bid/ask (entry BUY=ask/SELL=bid, exit BUY=bid/SELL=ask)
- **BT spread v2**: ペア別実測値ベース (461t監査), EUR_GBP 1.0-2.0pip, GBP_USD 0.8-1.8pip, EUR_USD 0.3-1.0pip, EUR_JPY 0.5-1.5pip, USD_JPY 0.3-1.0pip, XAU 3.0-5.0pip
- **BT slippage**: ペア別定数 (_BT_SLIPPAGE), エントリー・決済の両側に加算
- **TP/SL**: TP=ATR-based technical target, SL=RR ratio inverse (MIN_RR=1.2)
- **SL floor**: ATR(14)x1.0 minimum distance (engine-level enforcement)
- **Entry quality gate**: QUALIFIED_TYPES only, at least 1 reason required
- **Strategy auto-promotion**: Demo N>=30 & EV≥1.0 -> OANDA promotion / EV<-0.5 -> demotion (every 10 trades, コスト補正1.0pip)
- **BT昇格基準 (Phase 5)**: 摩擦込みEV > 1.0 AND N≥10 を「昇格候補」として出力
- **Force-demoted (OANDA停止)**: sr_fib_confluence, ema_cross, inducement_ob, ema_ribbon_ride, h1_fib_reversal, pivot_breakout, ema_pullback — デモ継続・実弾停止 (Phase3: EMA系全滅確認)
- **Pair-Specific Lifecycle (2026-04-07)**: `(strategy, instrument)` tuple-based granular control — v5.95 BT audit 結果に基づく通貨ペア別戦略管理
  - **_PAIR_DEMOTED**: bb_rsi×EUR_USD (WR=20% EV=-1.5), macdh×GBP_USD (WR=40% EV=-0.818) → エントリー完全停止
  - **_PAIR_PROMOTED**: sr_fib_confluence×USD_JPY/EUR_USD/GBP_USD, **bb_rsi_reversion×USD_JPY (v6.3)** → FORCE_DEMOTED/SENTINEL bypass
  - **_PAIR_LOT_BOOST**: fib_reversal×USD_JPY=1.5x, sr_fib_confluence×USD_JPY=1.3x (ペア特化ブースト、グローバルブーストより優先)
  - **_UNIVERSAL_SENTINEL**: stoch_trend_pullback → 全モードでSentinel化 (Scalp限定→全モード拡張)
  - **_PAIR_SR_THRESHOLD**: USD_JPY=1.5 (デフォルト2.0→緩和、SR品質が高いため)
  - **_LIMIT_ONLY_SCALP**: GBP_USD → scalp成行注文禁止、指値のみ (RT friction=3.06pip対策)
  - **_N_LOT_TIERS (v6.1)**: N<10→max1.0x / 10≤N<30→max1.5x / N≥30→full (Confidence-based Lot)
  - **_PE_DT_ELIGIBLE (v6.1)**: orb_trap, london_ny_swing → DT Profit Extender対象
  - **_PE_ADX_THRESHOLD (v6.1)**: EUR_USD=25 (デフォルト30) → 緩やかトレンドでTP延伸許可
  - **_LIMIT_EXPIRE_CD_SEC (v6.1)**: 180s → GBP_USD指値失効後の追っかけ禁止
  - **_is_promoted() v4**: Bridge → PAIR_DEMOTED → PAIR_PROMOTED → FORCE_DEMOTED → auto_demotion → allow
- **Elite Track (2026-04-07)**: gbp_deep_pullback=2.0x, turtle_soup/orb_trap/htf_false_breakout/trendline_sweep/london_ny_swing=1.5x
- **Legacy boost**: sr_break_retest, mtf_reversal_confluence → 1.3x, fib_reversal=1.3x (global default)
- **Scalp Sentinel**: bb_rsi/fib/macdh/vol_momentum等7戦略 → 1000units固定(0.01lot)、データ収集専用 (v6.3: bb_rsi USD_JPYはPAIR_PROMOTED bypass)
- **Rolling EV Monitor (v6.3)**: `_check_rolling_ev()` — EV急落検出(drop≥0.2 & EV<-0.3)→自動アラートログ
- **Equity Curve Protector**: DD>5%(50pip)→全ロット50%縮小、DD回復(2.5%以下)→自動解除
- **ATR Trailing Stop**: Tier1=ATR*0.8→BE, Tier2=ATR*1.5→Trail at price-ATR*0.5 (MFE逃し救済+64.7p推定)
- **Session×Pair filter**: EUR_GBP全停止(WR=11%), EUR_USD Tokyo(UTC0-7)/Late_NY(UTC17+)停止
- **SIGNAL_REVERSE min hold**: scalp 180→300s (ノイズ循環断切)

## Confluence Scalp v2 Architecture (2026-04-07)
- **File**: `strategies/scalp/confluence_scalp.py` (ConfluenceScalp + MSS検出関数群)
- **設計思想**: 既存Sentinel戦略の構造的欠陥(83.5% instant death, SAR<1.0)を解消する新世代スキャルプ
- **防御層 (3段階ゲート)**:
  1. Session Gate: UTC 12-17のみ (London/NY overlap = instant death率最低の時間帯)
  2. MFE Guard: ATR/Spread >= 10 (摩擦吸収余地の確保)
  3. HTF Hard Block: HTF方向に逆行するエントリーを完全ブロック (Sentinel戦略のソフトペナルティとは異なる)
- **攻撃層 (Triple Confluence Gate)**:
  - Family A (Trend): EMA9/21クロスまたは整列
  - Family B (Oscillator): RSI5極端 + BB%B極端
  - Family C (Momentum): MACD-H方向転換
  - 3理論族が全て同方向に合意した場合のみエントリー
- **MSS (Market Structure Shift)**:
  - CHoCH (Change of Character): スイングH/Lを実体で割れ → 構造転換検出 (Wyckoff 1931)
  - MSB (Market Structure Break): CHoCH後のHH/LL更新 → 新トレンド確認
  - detect_choch() / detect_msb() / detect_mss_state(): Fractal(n=3)ベースの構造分析
- **Profit Extender** (`demo_trader.py _check_sltp_realtime`):
  - TP到達時にMSS継続(MSB=True)+ADX>30: TP延伸(2x) + 強化トレイリング(ATR*0.4)
  - _mss_tracker: 毎tick(10s)でMSS状態を更新 → _check_sltp_realtime(0.5s)で参照
  - Climax Exit: RSI divergence + 大ウィック(70%以上) → 即利確
  - _profit_extended: TP延伸済みtrade_idのSet
- **Friction Minimizer** (指値遅延エントリー):
  - compute_limit_entry_price(): 直近3本のウィック中間点で指値価格を計算
  - 現在価格が指値より不利 → _pending_limits に保存、5分以内に到達で約定
  - __LIMIT_ENTRY__マーカーでsignal reasonsに指値価格を埋め込み
- **SL/TP**: SL=ATR7*1.2 (構造エントリー用に広め), TP=ATR7*2.5 (高RR)
- **app.py連携**: EMA200/HTFソフトペナルティを適用外 (内部でHTF Hard Block済み)
- **QUALIFIED_TYPES**: confluence_scalp を登録済み

## v6.5 Range Exit Optimization (2026-04-08)
- **Problem**: RANGE regime = 47.5% of trades, WR = 31.2% (worst regime). MR strategies use ATR*2.2 TP in RANGE, overshooting the natural mean-reversion target
- **Solution**: BB_mid TP Targeting + Range SL/TP Multipliers
- **Scope**: demo_trader.py entry path only (BT unchanged until validated)

### BB_mid TP Targeting
- **Trigger**: `regime == "RANGE"` AND `entry_type in {bb_rsi_reversion, macdh_reversal, fib_reversal, vol_surge_detector}`
- **BUY**: `TP = min(BB_mid, entry + ATR * 1.2)` — BB_midが近ければBB_mid、遠ければATR×1.2でキャップ
- **SELL**: `TP = max(BB_mid, entry - ATR * 1.2)` — 同上（対称）
- **Safeguard**: BB_mid must be on correct side of entry (BUY: above, SELL: below)
- **Telemetry**: `[RANGE_EXIT]` log with original TP, new TP, BB_mid, cap value
- **Non-impact**: Trend-following strategies (orb_trap, sr_fib_confluence, etc.) completely unaffected

### Range SL/TP Multipliers
- **SL widening**: Scalp ATR mult 0.8→1.0 in RANGE for MR strategies (noise tolerance toward opposite BB)
- **RR floor**: 0.8 (from 1.0) for RANGE MR — BB_mid TP shortening compensated by expected higher WR
- **SR SL RR**: SR-based SL selection RR threshold lowered to 0.8 for consistency
- **Telemetry**: `[RANGE_EXIT] SL widened:` log when mult changes

### Quick-Harvest Bypass (OANDA二重短縮防止)
- **問題**: BB_mid TP(既に短縮済み) × Quick-Harvest(×0.70) → 実効RR≈0.56 → 損益分岐WR=64% (非現実的)
- **対策**: `_is_range_mr == True` の場合、Quick-Harvest をバイパスし BB_mid TP をそのまま(×1.0)OANDA送信
- **結果**: OANDA実効RR = 0.8 → 損益分岐WR = 55.6% (戦える水準)
- **Telemetry**: `[RANGE_EXIT] Quick-Harvest bypassed — BB_mid TP preserved ×1.0`
- **既存免除**: `_QUICK_HARVEST_EXEMPT` (gbp_deep_pullback×GBP_USD) はそのまま維持

### Phase 1 Design Notes
- `_is_range_mr` flag: computed once (from Phase 2 variables), shared across TP override, SL widening, RR floor
- BB_mid sourced from `sig["indicators"]["bb_mid"]` (always available from compute_*_signal)
- Regime sourced from `sig["regime"]["regime"]` (detect_market_regime output)
- 1H Breakout (KSB/DMB) unaffected — `_1H_PRESERVE_SLTP` check is downstream

### Phase 2: Range Sub-classification & MR Score Control (2026-04-08)
- **Problem**: RANGE判定が粗く、SQUEEZE直前のMR逆張り(自殺行為)とWIDE_RANGE最適環境を区別できない
- **Solution**: `detect_market_regime` に `range_sub` フィールド追加 + demo_trader.py で動的スコア制御

#### Range Sub-types (`detect_market_regime` return → `range_sub`)
| Sub-type | Condition | 意味 | MR制御 |
|---|---|---|---|
| `SQUEEZE` | `bb_width_pct < 10` | BB極端圧縮→ブレイクアウト前夜 | **ブロック** (エントリー禁止) |
| `WIDE_RANGE` | `bb_width_pct >= 10 & ADX < 20` | オシレーション状態 | **ブースト** (Score+1.0, Conf+5) |
| `TRANSITION` | `ADX >= 20` (RANGE残留) | トレンド移行期 | パススルー (標準評価) |
| `None` | 非RANGEレジーム | N/A | N/A |

#### Entry Path Integration (demo_trader.py)
- **位置**: exposure check 直後、confidence threshold 直前 (Phase 2 block)
- **SQUEEZE**: `_block("regime_squeeze_mr"); return` — MR戦略の全シグナルを即座にブロック
- **WIDE_RANGE**: `confidence += 5` (最大100), `sig["score"] += 1.0` — 閾値通過率・OANDA転送確率を引き上げ
- **TRANSITION**: 調整なし — 標準評価ロジックがそのまま適用

#### Variable Sharing (Phase 2 → Phase 1)
- `_RANGE_MR_STRATEGIES`: Phase 2で定義、Phase 1 BB_mid TPで再利用 (重複排除)
- `_regime_type_r`, `_is_mr_entry`: Phase 2で計算、Phase 1で `_is_range_mr` 導出に使用
- `_range_sub`: Phase 2のみで使用 (SQUEEZE/WIDE_RANGE判定)

#### Telemetry
- `[REGIME] SQUEEZE detected — MR Blocked` — SQUEEZE時のブロックログ (bb_width_pct付き)
- `[REGIME] WIDE_RANGE detected — MR Score Boosted` — WIDE_RANGE時のブーストログ (Conf/Score変動値付き)

## Active Trading Rules & Constraints

### COOLDOWN (Re-entry Throttle)
- **Architecture**: EXIT-based (cooldown starts after trade close, not entry)
- **Scalp**: 60s (1 bar)
- **Daytrade 15m**: 900s (1 bar) — BT/Production unified
- **Swing**: 14400s (1 bar)
- **Cross-strategy cascade CD**: SL_HIT on same pair triggers cooldown for ALL strategies (scalp:90s, DT:180s)
- **Post-SL same-direction block**: Block same-direction/same-price re-entry after exit (scalp:120s, DT:600s, swing:7200s)

### Position Limits
- **Max open trades**: 4 (safety cap) + per-pair 1 position limit
- **DT same-direction**: max 2 positions, same price distance >=5pip
- **Scalp same-direction**: max 3 positions, same price distance >=1.0pip
- **bb_rsi/macdh mutual exclusion**: correlation 0.65 pair same direction within 3min -> only higher EV executes

### Circuit Breaker (Consecutive Loss Control)
- **All-direction breaker**: N losses in 30min pauses mode (scalp:4, DT:3)
- **Same-direction max**: 3 consecutive same-direction losses -> pause
- **Drawdown control**: Daily -30pip / Max DD -100pip -> auto-stop

### Friday Filters
- **Scalp**: Score threshold 0.6->3.5 (high conviction only), tokyo_bb fully blocked
- **DT (compute_daytrade_signal)**: Friday UTC 0-6 SR-based (sr_fib_confluence etc.) blocked, UTC 18+ fully blocked
- **DT (compute_signal)**: combined score decay (x0.15), Tokyo/NY afternoon blocked
- **Note**: compute_daytrade_signal and compute_signal are separate functions. DT BT uses compute_daytrade_signal

### HTF / EMA Hard Filters
- **DT HTF hard filter**: htf_agreement=bull blocks SELL completely (return WAIT)
- **Scalp EMA200 hard filter**: EMA200 above + slope rising blocks SELL completely
- **Scalp HTF hard filter**: HTF bull blocks SELL, bear blocks BUY completely
- **Mean-reversion exemption**: bb_rsi, macdh, v_reversal, trend_rebound use soft penalty only (not hard blocked)
- **Layer1 direction check**: demo_trader blocks L1 (bull/bear) counter-trend trades

### SL Hunting Countermeasures
- **Session SL widening**: UTC 0,1,18-21h: SL +ATRx0.2 (BT+Production)
- **Counter-trend buffer**: Mean-reversion strategies against L1: SL +ATRx0.25 (BT+Production)
- **Fast-SL adaptive defense**: Fast SL (<120s) in last 5min -> next SL +ATRx0.3 (Production only)
- **Spread filter (per-pair)**: USD/JPY 1.0p, EUR/USD 1.2p, GBP/USD 1.2p, EUR/GBP 1.2p, EUR/JPY 1.2p, XAU/USD 4.0p
- **Spike detection**: >0.5ATR move in 60s blocks entry
- **Round number SL avoidance**: .000/.500 nearby SL shifted 2.5pip outward
- **Time-based retreat**: 50% hold elapsed + unrealized loss -> early exit before SL (TIME_DECAY_EXIT)
- **動的ロットサイジング (2軸+戦略ブースト)**: Axis1=SL距離連動 × Axis2=ATR/Spread比 × 戦略ブースト(Elite 1.5-2.0x / Legacy 1.3x), combined 0.3-2.5x
- **DT spread guard**: 20%閾値 (往復spread/期待利益, scalp=30%)
- **Friction Ratio**: 決済ログに FR=(spread+slip)/|PnL| を付与、FR>100%で⚠️警告
- **SL cluster avoidance**: New SL within 2pip of existing position SL -> entry blocked
- **SL technical positioning**: SR-based (nearest SR - ATRx0.3) priority over ATR-based. RR>=1.0 guaranteed

### Breakeven & Trailing Stop
- **BE trigger (共通建値ガード)**: Tier1: ATR*0.8到達 → SL→BE(entry+spread). Tier2: ATR*1.5到達 → Trail(price-ATR*0.5). SMC: FX=3pip即BE / XAU=10pip.
- **No trailing stop**: BE=ATR*0.8 only (trailing removed per BT/Production param unification)
- **Price velocity filter**: >8pip move in 10min blocks counter-direction entry [Cont 2001]
- **ADX regime block**: ADX>=35 strong trend blocks counter-trend entry

### SIGNAL_REVERSE
- **Minimum hold**: scalp 180s, DT 600s, swing 3600s (whipsaw prevention)
- **Score threshold (2026-04-07)**: `abs(score) >= 2.0` — 弱い逆転シグナル(スコア<2.0)ではSR発動しない（ノイズ防止）
- **ADX filter (2026-04-07)**: `ADX > 20` — レンジ相場(ADX≤20)ではSR禁止、SL/TPに委ねる（往復ビンタ防止）
- **Trend Mismatch log**: Layer1方向 vs 反転シグナル方向の不一致を検出・ログ出力（情報用）
- **SR詳細ログ**: `[SR] Score: +2.50 | ADX: 28.3 | Conf: 65 | Trend_Mismatch: True | L1: bull | Type: sr_fib`
- **抑制ログ**: `🚫 SR抑制（スコア不足）` / `🚫 SR抑制（レンジ相場）` — フィルター発動理由を明示
- **BT同期**: Scalp BT + DT BT にも同一フィルター(score>=2.0 + ADX>20)を適用済み

### OANDA Position Sync
- **Demo -> OANDA sync**: Orphan positions (demo CLOSED, OANDA OPEN) detected every 5s and auto-closed
- **Demo as source of truth**: OANDA orphans resolved by demo state

## EUR/USD New Strategies (2026-04-04)
- **Root cause of EUR/USD losses**: ATR is half of USD/JPY -> spread burden 2x, BB mean-reversion WR~50% (no edge), Asia session EUR/USD effectively dead (4.5pip range)
- **SVE (Session Volatility Expansion)**: 1m scalp, UTC 07:00-08:30 only, Asia compression -> London breakout, spread<=0.5pip hard filter
- **FBF (HTF False Breakout Fade)**: 15m DT, 1H SR(20-bar) close-based break detection -> 15m reversion, MTF 4H/1D filter
- **ADX TC (ADX Trend Continuation)**: 15m DT, EUR/USD専用。ADX≥25+EMAパーフェクトオーダー+プルバック→リバウンド確認。WR=78.6% EV=+1.706。USD/JPY DISABLED(15m足トレンドノイジー)
- **LSB (London Session Breakout)**: **DISABLED** — ctx fix後初BTでWR=10%/0% → Asia compression→London breakout ロジック要再設計

## USD/JPY New Strategies & Enhancements (2026-04-04)
- **TNM (Tokyo Nakane Momentum)**: 15m DT, UTC 00:45-01:15, BUY方向のみ（非対称設計）。Pre-fix DOWN→Post-fix BUY reversal。月曜/金曜除外。USD/JPY専用
- **bb_rsi Option C**: USD/JPY専用環境最適化。ADX制限撤廃(ADX>=30で逆にWR=60%), Death Valley(UTC 00-01,09,12-16)完全ブロック, Gold Hours(UTC 05-08,19-23)スコアボーナス。EUR/USDは従来通りADX<25維持
- **DaytradeEngine ctx fix**: compute_daytrade_signal内のDaytradeEngineフォールバックコンテキストに hour_utc, is_friday, prev_close/open/high/low を追加。時間帯フィルター戦略(TNM/LSB)が正しく動作可能に
- **DT BT session filter例外**: USD/JPY UTC 00-01をセッションフィルター(UTC<5ブロック)から除外。仲値時間帯のBT評価を可能に

## 1H Breakout Mode v5.0 (Active since 2026-04-05)
- **Architecture**: HourlyEngine (StrategyBase/Engine pattern) → compute_hourly_signal → demo_trader
- **HTF**: Real 4H+1D data via resample from 1H bars (_compute_1h_htf_bias)
- **SL/TP**: Strategy-calculated, preserved in demo_trader (_1H_PRESERVE_SLTP)
- **BE/Trailing**: BE at 50% TP → trailing stop (recent H/L - ATR×1.5)

### KSB (Keltner Squeeze Breakout) — EUR/USD専用
- **BT**: 10t WR=50% +92pip/120d, RR=2.0, Avg Hold=6.2h
- **Concept**: BB squeeze (BB inside Keltner) → release → Keltner(80%) breakout
- **Key params**: MIN_SQUEEZE=3, KELT_BREAK_MULT=0.80, ADX_MIN=15, BODY_RATIO≥0.35
- **SL**: Squeeze期間のswing L/H ± ATR×0.3, max ATR×1.5
- **USD/JPY**: DISABLED (WR=33.3%, スリッページで負EV転落リスク)

### DMB (Donchian Momentum Breakout) — 両ペア
- **BT EUR**: 60t WR=50% +391pip/120d, RR=2.0, Avg Hold=5.5h
- **BT JPY**: 40t WR=35% +181pip/120d, RR=2.0, Avg Hold=6.9h
- **Concept**: Donchian 48-bar (≈2営業日) range breakout + DI momentum
- **Key params**: MIN_RANGE≥ATR×1.5, ADX_MIN=18, BODY_RATIO≥0.40
- **SL**: don_mid48 ± ATR×0.3, max ATR×1.5
- **USD/JPY SELL非対称フィルター**: ADX≥25 + 1D EMA50 falling required (金利差逆行対策)
- **Freshness check**: Previous bar must not have already broken Donchian

## EUR/JPY Scalp Mode (Active since 2026-04-05)
- **Architecture**: 既存compute_scalp_signal + UTC 12-15ハードフィルター (active_hours_utc in MODE_CONFIG)
- **ペア**: EUR/JPY (EURJPY=X / EUR_JPY)
- **稼働時間**: UTC 12-15のみ (London/NY overlap, spread最狭1.5pip)
- **BT**: 250t WR=45.6% +300pip EV=+1.20/trade (60d, 5m検証)
- **BT 1m**: 118t WR=61.9% +115pip EV=+0.97/trade (7d)
- **根拠**: UTC 15 = London fixing反転効果 (全利益の60%, EV=+3.14/trade)
- **ロット**: ATR/Spread比 ~3.3 → vol_mult=0.7 → 自動的に0.6x前後に縮小

## Lot Sizing v6.2: 3-Factor Model (Active since 2026-04-07)
- **3-Factor Model**: Risk(SL距離) × Edge(ATR/Spread) × Boost(戦略×N制限×DD防御)
- **Final**: clamp(risk_factor × edge_factor × boost_factor, 0.3, 2.5)
- **Risk factor**: base_sl_pips / actual_sl (0.5-1.5), scalp=3.5, DT=15, 1H=30
- **Edge factor**: ATR/Spread thresholds — ≥15→1.5x, ≥10→1.3x, ≥6→1.0x, ≥3→0.7x, <3→0.5x
- **Boost factor**: strat_boost × N_cap × (0.5 if defensive else 1.0)
- **ログ透明化**: エントリーログに `📐 0.70R×1.3E×1.50B=1.37 → 13000u [N=51 edge=17]` 形式で内訳表示
- **Sentinel bypass (v6.2)**: _PAIR_LOT_BOOST / _PAIR_PROMOTED に登録されたペア×戦略は SCALP_SENTINEL をバイパス
- **N<10 Safety (v6.2)**: 本番N<10の未検証戦略は自動Sentinel (0.01lot)。PAIR_PROMOTED免除
- **_get_base_mode()**: mode suffix removal helper (scalp_eur→scalp, scalp_eurjpy→scalp)

## Deploy-Safe State Persistence (v6.2)
- **system_kv テーブル**: SQLite永続化でデプロイ後も状態維持
- **Equity Protector**: _eq_peak / _eq_current / _defensive_mode → 決済ごとにDB保存、起動時に復元
- **N Cache**: _strategy_n_cache → _evaluate_promotions() でDB保存、起動時にDB復元 → 直後にDB集計で上書き
- **OANDA Audit**: oanda_audit テーブル (v6.1) — デプロイ後も監査ログ保持

## Production Monitoring (P0 — Active since 2026-04-04)
- **Slippage**: signal_price vs entry_price diff (pips) -> DB column `slippage_pips` + log
- **COOLDOWN compliance**: Seconds since last exit -> DB column `cooldown_elapsed` + log (900s compliance for DT)
- **Spread**: OANDA real spread at entry/exit -> DB columns `spread_at_entry`, `spread_at_exit` + log
- **DB columns**: signal_price, spread_at_entry, spread_at_exit, slippage_pips, cooldown_elapsed
- **Pending task**: Periodic production report (slippage/spread/COOLDOWN analysis) after 50-100 trades accumulate

## v6.4 SHIELD + 非対称攻撃 (2026-04-08)

### Phase 1: 絶対防御 (P0)
- **OANDA Lot Hard Cap**: `_OANDA_LOT_CAP = 10000` — 3-Factor Model計算後にmax 10,000u強制。19000u災害防止。`[SHIELD]`ログ
- **EUR_USD DT/1H OANDA遮断**: `_OANDA_MODE_BLOCKED = {daytrade_eur, daytrade_1h_eur}` — EUR_USD scalp継続、DT/1HのOANDA送信をブロック (WR=29.2%対策)
- **Quick-Harvest TP**: `_QUICK_HARVEST_MULT = 0.70` — OANDA TP = demo TP × 0.70 (TP hit率 3.75%→早期利確)。`_QUICK_HARVEST_EXEMPT`で gbp_deep_pullback×GBP_USD は全TP許可。`[SHIELD]`ログ

### Phase 2: 計測 (P0-P1)
- **Fidelity Cutoff**: `_FIDELITY_CUTOFF = "2026-04-08T00:00:00+00:00"` — `_evaluate_promotions()` + `LearningEngine` がv6.3パラメータ変更後のトレードのみ評価。旧320t汚染データ排除。`get_trades_for_learning(after_date=)`で実装
- **Execution Telemetry**: `[TELEMETRY] signal=X fill=Y slip=Zpip` — OandaBridge `open_trade`に`signal_price`引数追加。約定時にsignal price vs fill priceのスリッページをpip単位で記録

### Phase 3: 非対称攻撃 (P1-P2)
- **50% TP Profit Extender**: `_PE_50PCT_ELIGIBLE` — トレンドフォロー戦略でTP距離の50%到達 + entry ADX>30 → TP200%延伸 + ATR×0.5トレイリング。`_entry_adx`でエントリー時ADXを保存。**NOTE: Demo TPは延伸されるがOANDA TPは70%のまま（設計通り: OANDAは早期利確、Demoは研究用延伸）**
- **Risk-Free Pyramiding**: 1.0 ATR有利方向移動 + OANDA昇格済み → 追加10000uポジション開設 + 元トレードSL→BE(建値+スプレッド)。`_pyramided_trades`で重複防止。`[PYRAMID]`ログ
- **Quick-Harvest Exemption**: gbp_deep_pullback × GBP_USD は `_QUICK_HARVEST_EXEMPT`により全TP適用

### v6.4 Key Constants (demo_trader.py)
- `_OANDA_LOT_CAP = 10000`
- `_OANDA_MODE_BLOCKED = {"daytrade_eur", "daytrade_1h_eur"}`
- `_QUICK_HARVEST_MULT = 0.70`
- `_QUICK_HARVEST_EXEMPT = {("gbp_deep_pullback", "GBP_USD")}`
- `_FIDELITY_CUTOFF = "2026-04-08T00:00:00+00:00"`
- `_PE_50PCT_ELIGIBLE`: vol_momentum_scalp, confluence_scalp, orb_trap, london_ny_swing, sr_fib_confluence, htf_false_breakout, gbp_deep_pullback, turtle_soup, trendline_sweep, sr_break_retest, adx_trend_continuation, ema_cross

## v6.5 Quant Infrastructure (2026-04-08)

### New Modules
- **`modules/exposure_manager.py`**: Cross-pair currency exposure tracking. Net exposure per currency (USD/EUR/GBP/JPY/XAU), 20,000u single-currency limit, max 3 same-direction positions. Prevents USD concentration risk across correlated pairs.
- **`modules/alert_manager.py`**: Discord Webhook external alerting. Rate-limited (5min cooldown per type). Triggers: DD threshold, OANDA disconnect/kill, consecutive losses, EV drop, exposure block. Env var `DISCORD_WEBHOOK_URL`.
- **`modules/stats_utils.py`**: Statistical utilities (scipy-free). Binomial test, Bayesian WR posterior (Beta-Binomial), Bootstrap EV CI, Sortino/Calmar/Profit Factor, Kelly Criterion, Risk of Ruin, MAFE distribution analysis, exponential decay weights.

### Tier 0: Cross-pair Exposure Management
- **ExposureManager** integrated into demo_trader entry path (before lot calculation)
- Currency decomposition: BUY USD_JPY = +USD -JPY, SELL EUR_USD = -EUR +USD
- Blocked trades logged with `exposure:` prefix + Discord alert
- Exposure tracking: add on open, remove on all 3 close paths (OANDA SL/TP, demo SLTP, SIGNAL_REVERSE)

### Tier 0: External Alerting (Discord Webhook)
- `AlertManager` initialized in DemoTrader.__init__
- Hooks: `_oanda_kill()` → `alert_oanda_kill()`, `_check_rolling_ev()` → `alert_ev_drop()`, exposure block → `alert_exposure_blocked()`
- Fire-and-forget async (non-blocking to trade threads)
- Set `DISCORD_WEBHOOK_URL` env var on Render to activate

### Tier 1: Statistical Significance in Learning Engine
- **Binomial test**: H0: WR<=45%, α=0.10. Normal approx for N>=20, exact for smaller N
- **Bayesian posterior**: Beta(1,1) prior → P(WR>45%) and 90% credible interval
- **Bootstrap EV CI**: 3000 resamples, 90% percentile CI, flags `ev_significantly_positive`
- **Per-strategy**: Kelly criterion, Risk of Ruin, Bayesian WR for each strategy with N>=10
- All results in `quant_analysis` dict returned from `evaluate()`

### Tier 1: MAFE-driven SL/TP Analysis
- `analyze_mafe()` called on closed trades in learning engine
- Returns: MAE/MFE percentiles (P25/P50/P75/P90), SL recommendation (MAE P75 + 10%), TP recommendation (MFE P50), TP efficiency (captured/available)
- Insight output: `[MAFE] SL推奨=X TP推奨=Y`

### Tier 2: Risk-Adjusted Performance Metrics
- **KPI** (`app.py calculate_kpi`): Added Sortino ratio, Calmar ratio, Profit Factor
- **Learning Engine**: Added Sortino/Calmar/PF to `quant_analysis.risk_metrics`
- Sharpe annualization note: sqrt(252) for daily-frequency assumption

### Tier 2: Regime-Conditioned Evaluation
- Bayesian posterior computed per regime (TREND_BULL/BEAR, RANGE, HIGH_VOL)
- P(WR>45%) reported in regime insights
- `quant_analysis.by_regime` contains per-regime Bayesian analysis

### Tier 2: Exponential Decay Weighting
- `exponential_decay_weights(n, half_life=30)` — latest trade weight=1.0, decays exponentially
- Decay-weighted EV vs equal-weighted EV reported in insights
- Detects recent performance divergence from all-time average

### Tier 2: Kelly Criterion & Risk of Ruin
- Per-strategy Kelly (full + half) computed when N>=10
- Risk of Ruin: RoR = ((1-edge)/(1+edge))^(ruin_level/risk_per_trade)
- Results in `quant_analysis.by_strategy[name].kelly` and `.risk_of_ruin`

### Tier 2: DD Phase Tagging (Demo DD Breaker Alternative)
- `_dd_phase_at_entry[trade_id]` records defensive_mode at entry time
- Cleaned up at all 3 close paths
- Design: データを切らずにデータを豊かにする (enrich, don't censor)

### Tier 2: MARKET_CLOSE Entry Prevention
- New entries blocked 30 minutes before session end (`active_hours_utc[1]`)
- Prevents MARKET_CLOSE forced-close losses (-2,506 JPY cumulative in pre-v6.5)

## Changelog
Full change history: [CHANGELOG.md](CHANGELOG.md)
