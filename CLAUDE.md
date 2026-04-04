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
| Mode | TF | Interval | COOLDOWN | Status |
|---|---|---|---|---|
| scalp | 1m | 10s | 60s (1 bar, EXIT-based) | Active |
| daytrade | 15m | 30s | 900s (1 bar, EXIT-based) | Active |
| daytrade_1h | 1h | 60s | 3600s | **DISABLED** (resource cost unjustified) |
| swing | 4h | 300s | 14400s (1 bar, EXIT-based) | Active |

## Daily Target
- **目標: 100 pips/日（±20 許容 = 80〜120 pips/日）**
- スキャルプ + デイトレで達成

## BT Performance (as of 2026-04-04, EUR/USD新戦略追加後)
- Scalp: 354t WR=58.5% EV=+0.152 WF=3/3 (7d, 1m) — 8 strategies active (+SVE)
- DT EUR/USD: **152t WR=68.4% EV=+0.456 Sharpe=4.944 WF=3/3** (55d, 15m)
- DT USD/JPY: **135t WR=68.1% EV=+0.393** (55d, 15m)
- Swing: 346t WR=36.7% EV=+0.154 WF=2/3 (730d, 1d)

## Scalp v3.1 Strategy Breakdown (7d BT)
| Strategy | Trades | WR | EV | Description |
|---|---|---|---|---|
| bb_rsi_reversion | 105 | 62.9% | +0.356 | BB%B<=0.25/>=0.75, RSI<45/>55, Stoch<45/>55, ADX<25 |
| macdh_reversal | 92 | 62.0% | +0.163 | BB<0.25/>0.75, MACD-H方向転換 (mean-reversion, soft penalty) |
| fib_reversal | 84 | 58.3% | +0.142 | Fib 38.2%/50%/61.8%反発, multi-lookback(45/60) |
| bb_squeeze_breakout | 8 | 37.5% | — | BB squeeze breakout, ADX>=20 |
| v_reversal | low freq | — | — | V-shape reversal |
| london_breakout | low freq | — | — | London session breakout |
| mtf_reversal_confluence | live only | — | — | RSI+MACD AND (HTF cache incompatible with BT) |
| **session_vol_expansion** | **EUR only** | — | — | **SVE: London open compression breakout (UTC 07:00-08:30)** |

- **DISABLED**: stoch_pullback (ADX>=20 EV<0), ema_pullback (EV~0), trend_rebound (no academic edge), engulfing_bb, three_bar_reversal, sr_channel_reversal
- **SL floor**: ATR(14)x1.0 minimum (ScalperEngine/DaytradeEngine unified)
- **MAX_HOLD=40 bars**, MIN_RR=1.2

## DT v4.0 Strategy Breakdown (55d BT, EUR/USD新戦略追加)
| Strategy | EUR Trades | EUR WR | EUR EV | JPY Trades | JPY WR | JPY EV | Description |
|---|---|---|---|---|---|---|---|
| sr_fib_confluence | 85 | 61.2% | +0.159 | 68 | 61.8% | +0.196 | ADX>=20, layer3 SR/Fib detection |
| **htf_false_breakout** | **42** | **71.4%** | **+0.555** | 37 | 78.4% | +0.712 | **FBF: 1H SR False Breakout Fade (Bulkowski 2005)** |
| ema_cross | 25 | 88.0% | +1.297 | 30 | 70.0% | +0.447 | ADX>=20, cross_window=8, pullback=0.3ATR |
| **london_session_breakout** | **—** | **—** | **—** | — | — | — | **LSB: Asia range -> London breakout (UTC 07-09)** |

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
- **SL-distance lot sizing**: OANDA lot 0.5-1.5x based on SL vs 3.5pip reference
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
- **FBF (HTF False Breakout Fade)**: 15m DT, 1H SR(20-bar) close-based break detection -> 15m reversion, MTF 4H/1D filter, WR=71-78%
- **LSB (London Session Breakout)**: 15m/1H DT, Asia range(00-07 UTC) -> London break, range>=20-day median x1.0, body>=40%, MTF required

## Production Monitoring (P0 — Active since 2026-04-04)
- **Slippage**: signal_price vs entry_price diff (pips) -> DB column `slippage_pips` + log
- **COOLDOWN compliance**: Seconds since last exit -> DB column `cooldown_elapsed` + log (900s compliance for DT)
- **Spread**: OANDA real spread at entry/exit -> DB columns `spread_at_entry`, `spread_at_exit` + log
- **DB columns**: signal_price, spread_at_entry, spread_at_exit, slippage_pips, cooldown_elapsed
- **Pending task**: Periodic production report (slippage/spread/COOLDOWN analysis) after 50-100 trades accumulate

## Changelog
Full change history: [CHANGELOG.md](CHANGELOG.md)
