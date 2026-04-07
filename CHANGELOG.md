# FX AI Trader - Changelog

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
