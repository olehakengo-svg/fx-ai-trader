# FX AI Trader - Changelog

## 2026-04-07 SR決済ノイズフィルター — スコア閾値 + ADXレンジブロック + 詳細ログ

### 1. 逆転強度の閾値導入 (Score Threshold)
- **`_SR_SCORE_THRESHOLD = 2.0`**: 逆転シグナルのスコアが `abs(score) >= 2.0` を満たす場合のみSR決済を実行
- 弱い逆転シグナル(ノイズ)でのSR発動を防止 — 既存のconfidence閾値に加え、スコア品質でもフィルタリング
- 抑制時ログ: `🚫 SR抑制（スコア不足）: BUY→SELL [SR] Score: +1.20 | ADX: 25.1 | ...`

### 2. ADXによるSR制限 (Range Market Block)
- **`_SR_ADX_MIN = 20`**: ADX > 20 のトレンド相場でのみSR決済を許可
- レンジ相場(ADX≤20)では逆方向シグナルが頻発→往復ビンタの原因 → SL/TPに委ねる
- 抑制時ログ: `🚫 SR抑制（レンジ相場）: SELL→BUY [SR] Score: +2.80 | ADX: 15.2 | ...`

### 3. SR理由のログ詳細化
- **`[SR]` 詳細行**: SR決済実行後に根拠情報を1行出力
  - `[SR] Score: +2.50 | ADX: 28.3 | Conf: 65 | Trend_Mismatch: True | L1: bull | Type: sr_fib`
- **Trend Mismatch検出**: Layer1トレンド方向と反転シグナル方向の不一致を検出（bull + SELL = mismatch）
- フィルター通過・抑制いずれの場合もSR詳細を出力 → 後続分析に活用可能

### 4. BT同期
- **Scalp BT**: `run_scalp_backtest()` 内のSR判定に `score >= 2.0 AND ADX > 20` フィルター追加
- **DT BT**: `run_daytrade_backtest()` 内のSR判定に同一フィルター追加
- BT/本番の一貫性を維持 — フィルター非適用時は `pass` で通常SL/TP判定に継続

## 2026-04-07 OANDA Command Center — コントロールパネル & 連携ステータス完全可視化

### 1. OANDA 転送司令部 (Tri-state Control)
- **`/api/config/oanda_control`**: 戦略ごとに LIVE / SENTINEL / OFF / AUTO を即時切替
- **LIVE**: フルロットでOANDA転送（_FORCE_DEMOTED の手動昇格パスを含む）
- **SENTINEL**: 0.01lot固定でOANDA転送（データ収集モード）
- **OFF**: OANDA転送停止 / **AUTO**: 自動昇降格判定に委ねる
- **DB永続**: `oanda_settings.strategy_overrides` (JSON)
- **後方互換**: `/api/config/toggle_oanda` (ON/OFF) は引き続き利用可

### 2. 実行ログ 🔗 OANDA 連携ラベル
- **[SENT]**: OANDA注文送信時に即座にログ出力（ロット・SL/TP含む）
- **[FILLED]**: OANDA約定成功時にOrderID・約定価格・ロット倍率を1行出力
- **[FAILED]**: 約定失敗時にエラー理由を明示
- **[BLOCKED]**: Bridge非アクティブ or モード除外（Reason: bridge_inactive / mode_not_allowed）
- **[SKIP]**: 未昇格戦略（Reason: force_demoted / auto_demoted / 手動停止 / pending）
- **Execution Audit**: `/api/oanda/audit` でトレードごとの is_live / bridge_status / block_reason / oanda_trade_id を返却

### 3. スキャルプ v2 指値ログ
- **[LIMIT_PLACED]**: Confluence Scalp v2 の指値遅延エントリーで指値設置時にログ出力
- **[LIMIT_FILL]**: 価格が指値に到達し OANDA 注文が発火した時点でログ出力
- 両ログとも `🔗 OANDA:` プレフィックス付きで統一フォーマット

### 4. リアルタイム・ヘルスチェック
- **60秒間隔**: `_sltp_loop` から `run_heartbeat()` を120回(=60s)ごとに自動実行
- **計測項目**: API latency(ms) / balance / NAV / unrealized P/L / margin / open trade count
- **display文字列**: `OANDA: CONNECTED / LATENCY: 45ms / NAV: ¥467,608` フォーマット
- **`/api/oanda/heartbeat`**: 最新のハートビートを返却（?refresh=true で手動更新可）
- **`/api/oanda/status`**: audit_summary (live/demo比率) を含む統合ステータス

### 5. インフラ変更
- **oanda_bridge.py**: `get_strategy_mode()`, `set_strategy_mode()`, `is_strategy_sentinel()` 追加
- **oanda_bridge.py**: `open_trade()` に `log_callback` + `lot_label` パラメータ追加
- **oanda_bridge.py**: `_add_audit()` に `oanda_trade_id` フィールド追加
- **oanda_bridge.py**: `get_heartbeat()` に `display` フォーマット済み文字列追加
- **demo_trader.py**: `_is_promoted()` v3 — tri-state対応（sentinel で手動昇格可能）
- **demo_trader.py**: OANDA実行セクション全面改修（🔗ラベル + SENTINEL lot override）
- **app.py**: `/api/config/oanda_control` 新エンドポイント + `_build_strategy_status_map()` 共通関数

## 2026-04-07 Confluence Scalp v2 — Triple Confluence + MSS + Profit Extender

### 1. Triple Confluence Gate (攻撃層)
- **新戦略 `confluence_scalp`** (`strategies/scalp/confluence_scalp.py`)
- **3理論族合意**: EMA9/21整列(Trend) + RSI5/BB%B極端(Oscillator) + MACD-H反転(Momentum)
- 単一指標のノイズエントリーを排除 — 既存Sentinel戦略の構造的欠陥(83.5% instant death)を解消

### 2. 防御層 (3段階ゲート)
- **Session Gate**: UTC 12-17のみ (London/NY overlap, instant death率最低)
- **MFE Guard**: ATR/Spread >= 10 (SAR<1.0の摩擦死を構造的に回避)
- **HTF Hard Block**: HTF逆行エントリーを完全ブロック (ソフトペナルティではなくハードブロック)
- `app.py`: confluence_scalp をEMA200/HTFソフトペナルティ適用外に設定 (内部で制御済み)

### 3. Market Structure Shift (MSS) — CHoCH/MSB検出
- **CHoCH (Change of Character)**: Fractal(n=3)スイングポイント → 実体で割れ = 構造転換 (Wyckoff 1931)
- **MSB (Market Structure Break)**: CHoCH後のHH/LL更新 = 新トレンド確認
- **detect_choch() / detect_msb() / detect_mss_state()**: DataFrame分析関数
- CHoCH検出でスコア+2.0, MSB確認で+1.0のボーナス

### 4. Profit Extender (利益延伸 + 動的エグジット)
- **TP延伸**: TP到達時にMSS継続(MSB=True) + ADX>30 → TP距離を2倍に拡大
- **強化トレイリング**: ATR*0.4幅 (通常Tier2のATR*0.5より狭く利益ロック)
- **Climax Exit**: RSI divergence + 大ウィック(70%以上) → 即利確
- **_mss_tracker**: 毎tick(10s)でMSS状態を更新、_check_sltp_realtime(0.5s)で参照
- **_profit_extended**: TP延伸済みtrade_idのSet追跡

### 5. Friction Minimizer (指値遅延エントリー)
- **compute_limit_entry_price()**: 直近3本のウィック中間点で有利な指値価格を計算
- **指値待ち**: 現在価格が指値より不利 → _pending_limits に保存 (5分期限)
- **指値約定**: 次tick以降で価格到達 → 自動エントリー実行
- **__LIMIT_ENTRY__マーカー**: signal reasonsに指値価格を埋め込み、demo_trader が解析

### 6. インフラ変更
- **demo_db.py**: `update_sl_tp()` メソッド追加 (Profit ExtenderのTP動的変更用)
- **demo_trader.py**: `_mss_tracker`, `_profit_extended`, `_pending_limits` 追加
- **QUALIFIED_TYPES**: `confluence_scalp` を登録
- **ScalperEngine**: `ConfluenceScalp` を戦略リストに追加 (14戦略目)

## 2026-04-07 Elite Selection & Portfolio Restructuring (摩擦v2 BT監査)

### 1. Elite Track ロットブースト (P0)
- **gbp_deep_pullback**: 2.0x (EV=2.903, WR=90.3%, N=31 — 最高エッジ)
- **turtle_soup/orb_trap/htf_false_breakout/trendline_sweep/london_ny_swing**: 1.5x
- **ロットclamp上限**: 2.0→2.5 (Elite 2.0x + vol_mult 1.5 = 3.0 → 2.5でcap)

### 2. Scalp Sentinel Mode (P0 — 摩擦死撤退)
- **8戦略を Sentinel 降格**: bb_rsi, fib, macdh, vol_momentum, stoch_trend, vol_surge, ema_ribbon, bb_squeeze
- **処置B**: OANDA継続 / lot=1000units(0.01lot)固定 / デモ継続
- **根拠**: scalp EV=-0.17(JPY), -0.40(EURJPY) — 摩擦がエッジを完全消失

### 3. DT Spread Guard 強化 (P1)
- **DT/1H**: spread_cost閾値 30%→20% (エリート戦略のエッジ防御)
- **Scalp**: 30%据え置き

### 4. Friction Ratio 監視タグ (P2)
- **FR = (spread_entry + spread_exit + slippage) / |PnL|**
- **FR > 100%**: ⚠️警告表示 (ブローカー貢献度超過)
- 決済ログに自動付与、戦略別の摩擦耐性を可視化

### 5. Equity Curve Protector (ディフェンシブモード)
- **DD > 5%** (50pip / 1000pip基準) → 全ロット50%強制縮小
- **DD回復** (2.5%以下) → 自動解除
- **累計PnL peak/current をリアルタイム追跡**、OANDA再開でリセット

## 2026-04-07 BT Friction Model v2 — Phase A-D Reality Sync (461t監査)

### Phase A: ペア別スプレッドモデル + スリッページ係数
- **_bt_spread() v2**: non-JPY一律モデル → EUR_GBP/GBP_USD/EUR_USD/EUR_JPY個別分離
  - EUR_GBP: 旧0.2-0.8pip → 新1.0-2.0pip (実測1.367pip)
  - GBP_USD: 旧0.2-0.8pip → 新0.8-1.8pip (実測1.300pip)
  - EUR_USD: 旧0.2-0.8pip → 新0.3-1.0pip (実測0.658pip)
  - USD_JPY: 旧0.2-0.8pip → 新0.3-1.0pip (実測0.677pip, 微調整)
- **_BT_SLIPPAGE**: ペア別スリッページ定数 (実測平均0.489pip×80%)
  - エントリー・決済の両側に加算 → 往復摩擦の完全再現
- **exit_friction_m**: 全トレードに決済時摩擦(half spread+slippage)をATR倍率で記録

### Phase B: SL判定厳格化
- **_sl_genuine_threshold**: 0.3→0.1 (scalp/DT/1H全BT)
  - 本番のtick-by-tick判定に近似。「ヒゲで助かった」BT楽観を排除

### Phase C: SIGNAL_REVERSE BT実装
- **Scalp BT**: min_hold=5bars(300s)経過後、3barごとにcompute_scalp_signalを再呼出
  - 逆シグナル検出時: close±摩擦で決済 → outcome/PnLを正確に記録
  - 検証結果: 201t中37t(18.4%)がSR決済 (本番40.1%の約半分、チェック間隔差)
- **DT BT**: 毎bar compute_daytrade_signalを再呼出 → 0% SR (15m足は保持期間内に反転しない = 正常)

### Phase D: 執行制限ロジック同期
- **カスケードCD**: SL後の全戦略クールダウン (scalp: 90bars, DT: 12bars@15m)
- **Post-SLブロック**: 同方向エントリー制限 (scalp: 120bars, DT: 40bars@15m)
- SL LOSSのみカスケード発動 (SR決済はカスケート非対象)

### Phase 5: EV計算リベース
- **PnL関数**: WIN=tp_m-exit_friction_m, LOSS=-(sl_m+exit_friction_m)
- **昇格基準**: 摩擦込みEV > 1.0 AND N≥10 → 「昇格候補」フラグ付与
- **verdict更新**: 全BT関数のverdict判定を摩擦込みEVベースに統一
- **結果例 (scalp USD/JPY 7d)**: 旧WR≈59% → 新WR=54.2%, EV=-0.171 (摩擦がエッジを完全消失)

## 2026-04-07 461t Quant Analysis — Win-Rate Reversal Engineering

- **ATR Trailing Stop (Tier2)**: ATR*0.8→BE(Tier1)に加え、ATR*1.5→Trail(price-ATR*0.5)を導入
  - MFE>0→LOSS 18件の64.7p損失を救済。利益ロックイン機構
  - Tier1とTier2はシームレスに切替: BE→TS→TS(ラチェットアップ)
- **Session×Pair exclusion**: EUR_GBP全停止(WR=11%), EUR_USD Tokyo/Late_NY停止
  - コントラリアン(逆張り)検証済み: spread二重控除後 -1.1p → 逆張りもエッジなし → 除外が正解
  - EUR_USD 75t (54+21) の -88.7p + EUR_GBP 9t の -29.9p = -118.6p 遮断
- **SIGNAL_REVERSE min hold**: scalp 180→300s
  - <5m SIGNAL_REVERSE 72件: PnL≈0のノイズ循環。5-10m(WR=53.7%, +51.9p)は有効ゾーン
- **Phase3 Force-demote**: ema_pullback(WR=19%, EV=-0.77) → EMA系3戦略(cross/ribbon/pullback)全滅確認
- **461t構造分析**: MAFE有効率4/7で97.3%に改善、即死率67.3%(93%→補正)、BE救済3.6%

## 2026-04-07 448t Production Audit — Surgical Strategy Triage

- **Phase2 Force-demote**: ema_ribbon_ride(EV=-2.75), h1_fib_reversal(EV=-4.18), pivot_breakout(EV=-8.56) -> OANDA停止
  - 3戦略合計92t、全損失の54%(-198.5p)を生産。即時遮断で最大インパクト
- **Lot boost追加**: mtf_reversal_confluence -> 1.3x (EV=+1.49, WR=57%, instant-death率29%=最低)
- **監視継続**: fib_reversal(EV=-0.54, N=76), ema_pullback(EV=-0.77, N=21) — EV<1.0で自動昇格ブロック済み
- **448t統計**: WR=35%, PnL=-364.6p, PF=0.66, 93%の損失がMFE=0(instant death)
  - BE guard効果は限定的(6%, 23.3p) — 根本原因はエントリー品質
  - London session WR=27-30%(最悪), GBP/USD NY slippage=1.11p(最大)

## 2026-04-04 P0 BT<>Production Gap Fix + Monitoring Phase

- **Root Cause: COOLDOWN mismatch**: BT=1 bar (15min) vs Production=30s -> 30x faster re-entry -> WR 62%->40% gap
- **DT COOLDOWN unification**: 30s -> 900s (1 bar=15min) -- BT/Production fully synced
- **1H/Swing COOLDOWN unification**: 1H=3600s, Swing=14400s -- matching bar length per TF
- **All BT EXIT-based cooldown**: `last_bar = i` -> `i+1+bars_held` (prevent overlapping trades during hold)
  - BT DT: 344t->62t (-82%), MaxDD 18.4%->3.97% (-78%), ema_cross WR stable 62%
- **SL floor**: ScalperEngine/DaytradeEngine: ATR(14)x1.0 minimum SL distance
- **ADX academic thresholds**: Trend strategies ADX>=20 (stoch/ema_pullback/squeeze/ema_cross/sr_fib), Range bb_rsi ADX<25
- **mtf_confluence MACD condition**: OR->AND (macdh>0 OR macdh>prev was non-functional filter)
- **trend_rebound disabled**: Counter-trend in strong trends has no academic edge (Moskowitz 2012)
- **stoch_pullback disabled**: ADX>=20 yields EV=-0.130, 1min ADX lag makes edge insufficient
- **ema_pullback disabled**: ADX>=20 yields WR=51.1% EV~0, same family, insufficient edge
- **P0 monitoring logging**:
  - Slippage: signal_price vs entry_price diff (pips) saved to DB + logged
  - COOLDOWN proof: seconds since last exit saved to DB + logged (900s compliance)
  - Spread: OANDA real spread at entry/exit saved to DB + logged
  - New DB columns: signal_price, spread_at_entry, spread_at_exit, slippage_pips, cooldown_elapsed
- **Phase transition**: Parameter tuning complete -> Production data accumulation & friction monitoring phase

## 2026-04-03 FX Analyst Review

- **P0 BE spread correction**: BE move uses BUY=entry+spread, SELL=entry-spread (prevent false BE wins)
- **P1 BT time-varying spread**: `_bt_spread(bar_time, symbol)` -- Tokyo early 0.8pip, LDN/NY 0.2pip, NY late 0.8pip. Applied to all 8 BT functions
- **P1 per-pair position management**: max_open_trades=4 (safety cap) + per-pair 1 position limit. USD/JPY and EUR/USD independent
- **P2 SL technical positioning**: SR-based (nearest_support/resistance - ATRx0.3) > ATR-based (x0.8/1.0/1.5) priority. RR>=1.0 guaranteed
- **P2 strategy auto-promotion**: All strategies trade in demo -> N>=30 & EV>0 promotes to OANDA / EV<-0.5 demotes. Re-evaluated every 10 trades
  - `/api/demo/status` -> `strategy_promotion`
  - Demo=data accumulation, OANDA=performance-based selection
- **BT/Production param unification**: BE=60% (no trailing), cooldown=1 bar, no time restrictions
- **EUR/USD pips calc fix**: realized_pl/units -> price-diff method (demo_db.py)
- **EUR/USD rounding fix**: round(x,3) -> _rp(x,symbol) for 5-digit pairs (app.py all signal functions)

## 2026-04-03 SL Hunting Countermeasures + Strategy Consolidation

- **SL hunting #1**: Cross-strategy cascade CD -- SL_HIT on same pair triggers cooldown for all strategies (scalp:90s, DT:180s)
- **SL hunting #2**: Session transition SL widening -- UTC 0,1,18-21h: SL +ATRx0.2 (BT+Production)
- **SL hunting #3**: Fast-SL adaptive defense -- fast SL (<120s) in last 5min -> next SL +ATRx0.3 (Production only)
- **SL hunting #4**: Counter-trend buffer -- 5 mean-reversion strategies against L1 -> SL +ATRx0.25 (BT+Production)
- **SL hunting E1**: Spread filter -- spread>1.2pip(JPY)/1.5pip(EUR) blocks entry
- **SL hunting A1**: Spike detection -- >0.5ATR move in 60s blocks entry
- **SL hunting B1**: Round number SL avoidance -- .000/.500 nearby SL shifted 2.5pip outward
- **SL hunting C1**: Time-based retreat -- 50% hold elapsed + unrealized loss -> early exit before SL (TIME_DECAY_EXIT)
- **SL hunting D1**: SL-distance lot sizing -- OANDA lot 0.5-1.5x based on SL vs 3.5pip reference
- **SL hunting F1**: SL cluster avoidance -- new SL within 2pip of existing position SL -> entry blocked
- **Strategy consolidation (33->9)**: Major consolidation based on FX analyst review
  - Scalp 7: bb_rsi, macdh, stoch_pullback, bb_squeeze, london_bo, tokyo_bb, mtf_reversal
  - DT 2: sr_fib_confluence, ema_cross
  - 1H Zone: **Entire mode DISABLED** (0.15pip/day, resource cost unjustified)
  - Removed: v1-compat 6, trend_rebound, ihs_neckbreak(scalp), sr_touch_bounce, DT ihs_neckbreak, DT fallback 3
  - Planned merge: fib_reversal->bb_rsi, v_reversal->bb_rsi
- **bb_rsi/macdh mutual exclusion**: correlation 0.65 pair firing same direction within 3min -> only higher EV executes
- **BT SL hunting applied**: Scalp/DT BT with #2 #4 -> Scalp WR 58.6->60.1% EV +0.269->+0.314, DT WR 65.2->73.5% EV +0.283->+0.524

## 2026-04-03 OANDA Spread + Position Sync

- **OANDA real spread integration**: Demo entry/exit uses OANDA bid/ask (fixed mid -> real spread)
  - Entry: BUY=ask, SELL=bid (same as OANDA execution logic)
  - SL/TP: BUY position=bid, SELL position=ask (exit also reflects spread)
  - SIGNAL_REVERSE / manual close also use bid/ask
  - `fetch_oanda_bid_ask()` added -> returns bid/ask/spread/mid
- **Demo->OANDA position sync**: Orphan positions (demo CLOSED but OANDA OPEN) detected every 5s and auto-closed
  - `_sync_demo_to_oanda()`: fetches OANDA openTrades, closes unmapped trades
  - Demo as source of truth, resolves OANDA orphans
- **OANDA integration points**: Entry(ask/bid) / SL/TP(bid/ask) / Signal reverse(bid/ask) / Manual(bid/ask) / Orphan close(5s)

## 2026-04-03 1H Zone v4 + Scalp Optimization

- **1H Zone v4 rewrite**: Deprecated 6 strategies (mtf_momentum, session_orb, pivot_breakout, etc.), rebuilt around h1_breakout_retest
  - **h1_breakout_retest**: Strong SR (strength>=0.5, touches>=3) breakout retest entry (Bulkowski 2005)
  - Break quality filter: break candle body >0.3-0.5ATR required (noise break elimination)
  - HTF trend filter: 4H(EMA9/21) + 1D(EMA50/200 + EMA50 slope 24 bars) alignment
  - Strong bull blocks SELL / Strong bear blocks BUY
  - HTF trend bonus: 4H+1D match +0.5, 1D match +0.3
  - SL=0.8ATR (0.5 causes 1-bar stops on 1H noise, 1.0 degrades WR)
  - TP=4.0ATR, BE at 70%TP, Trail 1.2ATR, MAX_HOLD=30 bars
  - h1_sr_reversal disabled (WR=25%)
- **bb_rsi_reversion ADX threshold**: 35->28->32 (28 halves count, 32 optimal frequency/WR balance)
- **bb_rsi_reversion Stoch cross gap**: (stoch_k - stoch_d) > 1.5 required (noise cross elimination)
- **bb_rsi_reversion prev-bar direction**: BUY requires prev bearish, SELL requires prev bullish
- **stoch_trend_pullback frequency increase**: ADX threshold 20->18, RSI/Stoch/BBpb ranges expanded
- **fib_reversal multi-lookback**: lookback 60->[45,60], Fib proximity 0.25->0.35ATR
- **macdh_reversal mean-reversion reclassification**: Added to _mean_reversion_types (EMA200/HTF hard filter -> soft penalty)
  - Before: 56t WR=53.6% EV=+0.171 -> After: 172t WR=57.6% EV=+0.175 (BUY WR 44%->62% recovered)
- **Async chunked BT**: /api/backtest-long endpoint, 7-day chunk async BT (30d+ BT Render timeout workaround)
- **BT mode=daytrade_1h added**: /api/backtest?mode=daytrade_1h calls run_1h_backtest

## 2026-04-03 Production Data Analysis Optimization

- **DT HTF hard filter**: htf_agreement=bull blocks SELL completely (score x0.50 -> return WAIT). Prevents 12-loss -101pip streak
- **Circuit breaker implementation**: _total_losses_window: N losses in 30min pauses mode (scalp:4, DT:3, 1H:2)
- **DT same-direction position limit**: 5->2, same price distance: 1.5->5pip, cooldown: 300->600s (machine-gun entry prevention)
- **pivot_breakout disabled**: Production WR=0% (3t -66.4pip), removed from BT/Production QUALIFIED_TYPES
- **max_consecutive_losses**: 9999->3 (same-direction consecutive loss control activated)
- **Scalp enhancement**: same-dir positions 2->3, same price distance 1.5->1.0pip, cooldown 120->60s (good WR=56.4% more entries)
- **BT QUALIFIED_TYPES unification**: scalp(engulfing_bb,hs_neckbreak,sr_channel_reversal disabled), DT(hs_neckbreak,ob_retest disabled), 1H(pivot_breakout disabled) -- matched to production
- **Scalp EMA200 hard filter**: EMA200 above + slope rising blocks SELL completely (production macdh_reversal|SELL WR=0% -15.4pip fix)
- **Scalp HTF hard filter**: HTF bull blocks SELL, bear blocks BUY completely (soft decay score x0.6 -> full block)
- **OANDA v20 sub-account connection**: Claude_auto_trade_KG (001-009-21129155-002), hedgingEnabled=true, API token reissue resolved 403

## 2026-03-31 v2 Major Refactor

- BT/Production logic unification: All 3 modes use signal functions
- ema_cross: ADX<15 filter added (old WR 26.7% -> improved)
- HTF filter: Range (ADX<20) uses soft bias (SELL bias eliminated)
- SL: ATR7x0.5->0.8 expanded, SLTP check interval 0.5s
- Time filter: UTC 00,01,21 blocked (94% loss concentration)
- Consecutive loss control: 3 same-direction losses pauses
- Duplicate entry prevention: same-direction position + price proximity check
- SIGNAL_REVERSE minimum hold: scalp 60s, daytrade 300s, swing 3600s
- Swing signal: threshold 0.15->2.5/6.0, SL/TP 2.5/4.5->1.0/2.5, SR proximity scoring
- **Friday filter**: scalp threshold 3x, tokyo_bb blocked, DT SR blocked (UTC<7)
- **tokyo_bb entry_type fix**: early return includes entry_type (BT analysis accuracy)
- **HTF cache fix**: compute_daytrade_signal HTF bias uses htf_cache (BT)
- **EMA spread multiplier**: ema_pullback score adjusted by EMA9-21 spread
- **Post-SL cooldown**: Block same-direction/same-price re-entry after exit (scalp:120s, DT:600s, swing:7200s)
- **SIGNAL_REVERSE hold extension**: scalp 60->180s, DT 300->600s (whipsaw prevention)
- **Layer1 direction check**: demo_trader blocks L1 (bull/bear) counter-trend trades
- **sr_fib_confluence threshold**: 0.20->0.35 + EMA direction alignment required (production 0% WR fix)
- **dual_sr_bounce**: EMA direction alignment required (production 0% WR fix)
- **Auto-start**: All 3 modes auto-start on server boot (Render restart resilience)
- **Thread resilience**: Backoff on consecutive errors (thread crash prevention)
- **DB connection leak fix (B3)**: _safe_conn() context manager for all DB ops (try/finally guaranteed)
- **Watchdog auto-recovery**: Every 60s recovers running=False modes (B4 break bug fix)
- **max_open_trades**: 3->20 (allow multiple positions per mode)
- **auto_start dedup**: _auto_start_done flag (double-import race prevention)
- **stop() clears _started_modes**: Watchdog doesn't recover explicitly stopped modes
- **Drawdown control**: Daily -30pip / Max DD -100pip auto-stop
- **BT realistic spread**: scalp 0.5pip->1.5pip (realistic spread)
- **HTF lookahead fix**: BT HTF cache neutralized (lookahead bias removal)
- **1H Zone v2**: compute_1h_zone_signal full rewrite (academic paper-based 4 strategies)
  - mtf_momentum (Moskowitz 2012), session_orb (Ito 2006), pivot_breakout (Osler 2000), pivot_reversion
  - session_orb, pivot_reversion disabled based on BT results
  - Zone constraints: mtf_momentum zone-agnostic (trend-follow), pivot_breakout requires EMA alignment
  - MAX_HOLD: 12->18 bars (WR +3%, ATR EV +75%)
- **DT 15m optimization**: ema_cross ADX threshold 15->12, ema_score THRESHOLD 0.25->0.20
- **QUALIFIED_TYPES update**: 1h new entry_types (mtf_momentum, session_orb, pivot_breakout, pivot_reversion)
- **Rebound fix #1**: All-direction circuit breaker -- N losses in 30min pauses mode (scalp:4, DT:3)
- **Rebound fix #2**: Price velocity filter -- >8pip move in 10min blocks counter-direction entry [Cont 2001]
- **Rebound fix #3**: ADX regime counter-trend block -- ADX>=35 strong trend blocks counter-trend entry (except trend_rebound)
- **Rebound fix #4**: Breakeven + trailing stop -- 60%TP: SL->BE+0.5pip, 80%TP: SL->TP 50% level
- **Scalp v2.3 reversals**: sr_channel_reversal, fib_reversal, mtf_reversal_confluence added
- **DT v2 reversals**: dt_fib_reversal, dt_sr_channel_reversal, ema200_trend_reversal (fallback strategies)
- **1H Zone v3**: h1_fib_reversal (Fib 120-bar, EMA required->bonus), h1_ema200_trend_reversal (EMA200 retest, ADX>=15)
- **Thread self-recovery**: get_status() auto-recovers MainLoop/Watchdog/SLTP/all modes, BaseException catch, request_tick fallback
- **Gunicorn gthread**: --worker-class gthread + timeout 300s (thread stabilization)
