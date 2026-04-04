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
- **本番変更は必ずBTにも反映**: 本番で戦略の有効化/無効化、フィルター追加、パラメータ変更を行った場合、BT側のQUALIFIED_TYPESやフィルターも必ず同期すること
- **カーブフィッティング禁止**: パラメータ調整フェーズ完了（2026-04-04）。今後は本番データ蓄積・摩擦監視フェーズ

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

## BT Performance (as of 2026-04-04, +ADX TC EUR/USD採用)
- Scalp: 520t WR=59.4% Sharpe=0.064 (7d, 1m) — bb_rsi 181t(Option C拡大), macdh 144t, fib 172t
- DT EUR/USD: **153t WR=66.0% Sharpe=3.50** (55d, 15m, +ADX TC)
- DT USD/JPY: **155t WR=67.1% Sharpe=3.42** (55d, 15m, +TNM)
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

- **bb_rsi Option C (2026-04-04)**: USD/JPY ADX制限撤廃(トレンド中WR=60%), Death Valley(UTC 00-01,09,12-16)ブロック, Gold Hours(UTC 05-08,19-23)スコア+0.5, ADX>=30スコア+0.6
- **DISABLED**: stoch_pullback, ema_pullback, trend_rebound, engulfing_bb, three_bar_reversal, sr_channel_reversal
- **SL floor**: ATR(14)x1.0 minimum (ScalperEngine/DaytradeEngine unified)
- **MAX_HOLD=40 bars**, MIN_RR=1.2

## DT v4.2 Strategy Breakdown (55d BT, +ADX TC EUR/USD採用)
| Strategy | EUR Trades | EUR WR | EUR EV | JPY Trades | JPY WR | JPY EV | Description |
|---|---|---|---|---|---|---|---|
| sr_fib_confluence | 79 | 59.5% | +0.109 | 83 | 63.9% | +0.240 | ADX>=20, layer3 SR/Fib detection |
| htf_false_breakout | 35 | 62.9% | +0.276 | 28 | 71.4% | +0.739 | FBF: 1H SR False Breakout Fade (Bulkowski 2005) |
| ema_cross | 25 | 84.0% | +1.114 | 34 | 70.6% | +0.444 | ADX>=20, cross_window=8, pullback=0.3ATR |
| **adx_trend_continuation** | **14** | **78.6%** | **+1.706** | **—** | **—** | **—** | **ADX TC: EUR専用トレンド押し目 (Wilder 1978 / Menkhoff 2012)** |
| **tokyo_nakane_momentum** | **—** | **—** | **—** | **10** | **70.0%** | **+0.086** | **TNM: 仲値DOWN→BUY専用 (Andersen 2003)** |
| ~~london_session_breakout~~ | ~~10~~ | ~~10%~~ | ~~-9.9~~ | ~~—~~ | ~~—~~ | ~~—~~ | ~~DISABLED: ctx fix後初BTでWR=10% — 要再設計~~ |

- **ADX TC (2026-04-04)**: EUR/USD専用トレンドフォロー。ADX≥25+EMAパーフェクトオーダー(9>21>50)+前1-3本プルバック検出→現在足リバウンド確認。USD/JPYはDISABLED(WR=50%/EV=-0.719、15m足トレンドノイジー)
- **ctx fix (2026-04-04)**: DaytradeEngine fallbackコンテキストに hour_utc, is_friday, prev_close/open/high/low を追加。LSB/TNM等の時間帯フィルター戦略が正しく動作可能に
- **LSB DISABLED**: hour_utc未設定バグにより未テストだった。修正後初BT: EUR WR=10% ev=-9.9, JPY WR=0% ev=-10.7 → 要再設計
- **Mean-reversion exclusion**: bb_rsi, macdh, v_reversal, trend_rebound exempt from EMA200/HTF hard filter (soft penalty only)

## Key Parameters
- **Spread**: Production=OANDA real bid/ask (entry BUY=ask/SELL=bid, exit BUY=bid/SELL=ask), BT=0.2pip fixed
- **BT time-varying spread**: Tokyo early 0.8pip, LDN/NY 0.2pip, NY late 0.8pip
- **TP/SL**: TP=ATR-based technical target, SL=RR ratio inverse (MIN_RR=1.2)
- **SL floor**: ATR(14)x1.0 minimum distance (engine-level enforcement)
- **Entry quality gate**: QUALIFIED_TYPES only, at least 1 reason required
- **Strategy auto-promotion**: Demo N>=30 & EV>0 -> OANDA promotion / EV<-0.5 -> demotion (every 10 trades)

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
- **Spread filter**: spread >1.2pip(JPY) / >1.5pip(EUR) blocks entry
- **Spike detection**: >0.5ATR move in 60s blocks entry
- **Round number SL avoidance**: .000/.500 nearby SL shifted 2.5pip outward
- **Time-based retreat**: 50% hold elapsed + unrealized loss -> early exit before SL (TIME_DECAY_EXIT)
- **動的ロットサイジング (2軸)**: Axis1=SL距離連動(base_sl_pips/actual_sl), Axis2=ATR/Spread比(edge_ratio→vol_mult 0.5-1.5x), combined 0.3-2.0x
- **SL cluster avoidance**: New SL within 2pip of existing position SL -> entry blocked
- **SL technical positioning**: SR-based (nearest SR - ATRx0.3) priority over ATR-based. RR>=1.0 guaranteed

### Breakeven & Trailing Stop
- **BE trigger**: 60%TP reached -> SL moves to BE+0.5pip (with spread correction: BUY=entry+spread, SELL=entry-spread)
- **No trailing stop**: BE=60% only (trailing removed per BT/Production param unification)
- **Price velocity filter**: >8pip move in 10min blocks counter-direction entry [Cont 2001]
- **ADX regime block**: ADX>=35 strong trend blocks counter-trend entry

### SIGNAL_REVERSE
- **Minimum hold**: scalp 180s, DT 600s, swing 3600s (whipsaw prevention)

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

## Volatility Adaptive Lot Sizing (Active since 2026-04-05)
- **2軸制御**: Axis1 SL距離(base_sl_pips/actual_sl, 0.5-1.5) × Axis2 ATR/Spread比(vol_mult 0.5-1.5)
- **Final**: clamp(sl_ratio × vol_mult, 0.3, 2.0)
- **base_sl_pips**: scalp=3.5, DT=15, 1H=30 (MODE_CONFIG per-mode)
- **edge_ratio thresholds**: ≥15→1.5x, ≥10→1.3x, ≥6→1.0x, ≥3→0.7x, <3→0.5x
- **効果**: USD/JPY scalp (edge_ratio~17) → 1.5x boost, EUR/JPY (ratio~3) → 0.7x reduce
- **_get_base_mode()**: mode suffix removal helper (scalp_eur→scalp, scalp_eurjpy→scalp)

## Production Monitoring (P0 — Active since 2026-04-04)
- **Slippage**: signal_price vs entry_price diff (pips) -> DB column `slippage_pips` + log
- **COOLDOWN compliance**: Seconds since last exit -> DB column `cooldown_elapsed` + log (900s compliance for DT)
- **Spread**: OANDA real spread at entry/exit -> DB columns `spread_at_entry`, `spread_at_exit` + log
- **DB columns**: signal_price, spread_at_entry, spread_at_exit, slippage_pips, cooldown_elapsed
- **Pending task**: Periodic production report (slippage/spread/COOLDOWN analysis) after 50-100 trades accumulate

## Changelog
Full change history: [CHANGELOG.md](CHANGELOG.md)
