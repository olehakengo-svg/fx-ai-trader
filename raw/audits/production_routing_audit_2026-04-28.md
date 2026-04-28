# G0a: Production Routing Audit (2026-04-28)

- DB span: 2026-04-02 08:17:17 → 2026-04-28 09:04:36
- Total trades: 437 (Live: 36, Shadow: 401)
- Distinct entry_types in DB: 38
- Deployed (DT_QUALIFIED) strategies: 54
- Window for 'active': last 30 days

## Top finding

- **Live-active (≥1 Live trade in 30d)**: 6 / 54 (11%)
- **Shadow-only (any Shadow, 0 Live)**: 18
- **DB-silent in 30d but ever logged**: 0
- **Deployed but NEVER in DB (any time)**: 30 🔴

→ The most alarming bucket: strategies enabled in code but no DB row has *ever* appeared. Likely a routing-layer drop. These warrant the highest-priority pipeline trace.

## 🔴 Deployed but NEVER in DB (any time) (30)

| name | g1_bt_firing | g1_never_logged_flag |
|---|---|---|
| adx_trend_continuation | None | False |
| asia_range_fade_v1 | None | False |
| atr_regime_break | None | False |
| cpd_divergence | None | True |
| gbp_deep_pullback | None | False |
| gold_trend_momentum | None | False |
| gold_vol_break | None | False |
| gotobi_fix | None | False |
| hmm_regime_filter | None | False |
| htf_false_breakout | None | False |
| jpy_basket_trend | None | False |
| lin_reg_channel | None | False |
| london_close_reversal | None | False |
| london_close_reversal_v2 | None | False |
| london_fix_reversal | None | False |
| london_ny_swing | None | False |
| london_session_breakout | None | False |
| mqe_gbpusd_fix | 20 | True |
| ny_close_reversal | None | False |
| pd_eurjpy_h20_bbpb3_sell | None | False |
| pullback_to_liquidity_v1 | None | False |
| rsk_gbpjpy_reversion | 182 | True |
| sr_anti_hunt_bounce | None | True |
| sr_liquidity_grab | None | True |
| tokyo_nakane_momentum | None | False |
| tokyo_range_breakout_up | None | False |
| trendline_sweep | None | False |
| vdr_jpy | None | True |
| vsg_jpy_reversal | 331 | True |
| vwap_mean_reversion | None | False |

## 🟡 Deployed but DB-silent in last 30d (ever logged before) (0)

(empty)

## 🟢 Shadow-only in last 30d (no Live) (18)

| name | total | live_n | shadow_n | last_seen |
|---|---|---|---|---|
| dt_bb_rsi_mr | 16 | 0 | 16 | 2026-04-28 02:06:22 |
| dt_fib_reversal | 8 | 0 | 8 | 2026-04-27 19:31:30 |
| dual_sr_bounce | 2 | 0 | 2 | 2026-04-21 02:01:29 |
| ema200_trend_reversal | 16 | 0 | 16 | 2026-04-28 01:18:36 |
| ema_cross | 5 | 0 | 5 | 2026-04-27 08:55:35 |
| eurgbp_daily_mr | 1 | 0 | 1 | 2026-04-21 16:13:24 |
| inducement_ob | 1 | 0 | 1 | 2026-04-22 12:32:09 |
| intraday_seasonality | 6 | 0 | 6 | 2026-04-27 01:00:43 |
| liquidity_sweep | 1 | 0 | 1 | 2026-04-22 12:53:06 |
| orb_trap | 5 | 0 | 5 | 2026-04-24 15:41:39 |
| post_news_vol | 7 | 0 | 7 | 2026-04-28 04:12:21 |
| post_news_vol | 7 | 0 | 7 | 2026-04-28 04:12:21 |
| squeeze_release_momentum | 3 | 0 | 3 | 2026-04-28 00:00:14 |
| sr_break_retest | 16 | 0 | 16 | 2026-04-27 07:37:24 |
| sr_fib_confluence | 27 | 0 | 27 | 2026-04-28 08:45:30 |
| vol_spike_mr | 10 | 0 | 10 | 2026-04-24 11:29:38 |
| wick_imbalance_reversion | 1 | 0 | 1 | 2026-04-27 00:00:25 |
| xs_momentum | 1 | 0 | 1 | 2026-04-14 13:39:11 |

## ✅ Live-active in last 30d (6)

| name | total | live_n | shadow_n | last_seen |
|---|---|---|---|---|
| turtle_soup | 1 | 1 | 0 | 2026-04-07 07:05:33 |
| session_time_bias | 3 | 1 | 2 | 2026-04-15 07:56:54 |
| vix_carry_unwind | 1 | 1 | 0 | 2026-04-24 12:11:13 |
| doji_breakout | 4 | 1 | 3 | 2026-04-22 14:59:20 |
| dt_sr_channel_reversal | 17 | 1 | 16 | 2026-04-28 08:47:13 |
| streak_reversal | 1 | 1 | 0 | 2026-04-15 05:25:15 |

## ⚠️ In DB but NOT in DT_QUALIFIED (legacy or strategy renamed) (15)

| name | total | live_n | shadow_n | last_seen |
|---|---|---|---|---|
| bb_rsi_reversion | 36 | 22 | 14 | 2026-04-27 10:10:37 |
| bb_squeeze_breakout | 16 | 0 | 16 | 2026-04-27 10:32:46 |
| donchian_momentum_breakout | 1 | 0 | 1 | 2026-04-14 11:28:42 |
| ema_trend_scalp | 85 | 0 | 85 | 2026-04-27 12:42:30 |
| engulfing_bb | 22 | 0 | 22 | 2026-04-27 02:34:45 |
| fib_reversal | 47 | 0 | 47 | 2026-04-27 05:31:12 |
| h1_fib_reversal | 3 | 0 | 3 | 2026-04-02 09:38:10 |
| macdh_reversal | 9 | 0 | 9 | 2026-04-24 14:40:15 |
| mtf_reversal_confluence | 1 | 1 | 0 | 2026-04-02 10:19:04 |
| sr_channel_reversal | 25 | 0 | 25 | 2026-04-28 09:04:36 |
| stoch_trend_pullback | 17 | 0 | 17 | 2026-04-27 02:48:39 |
| trend_rebound | 4 | 2 | 2 | 2026-04-21 17:23:29 |
| v_reversal | 1 | 0 | 1 | 2026-04-21 08:32:23 |
| vol_momentum_scalp | 5 | 4 | 1 | 2026-04-24 12:31:26 |
| vol_surge_detector | 12 | 1 | 11 | 2026-04-27 01:15:51 |

## Cross-reference: G1 BT firing vs production

| Strategy | G1 BT signals (365d) | Prod total | Prod Live | verdict |
|---|---|---|---|---|
| vsg_jpy_reversal | 331 | 0 | 0 | 🔴 BT fires but **never in DB** — pipeline drop |
| rsk_gbpjpy_reversion | 182 | 0 | 0 | 🔴 BT fires but **never in DB** — pipeline drop |
| mqe_gbpusd_fix | 20 | 0 | 0 | 🔴 BT fires but **never in DB** — pipeline drop |

## Recommended next actions (Phase 10 reordered)

1. **G0b: trace pipeline drop** for any strategy in the 🔴 "NEVER in DB" bucket. Likely candidates:
   - Strategy class registered in `__init__.py` but missing from `DT_QUALIFIED` (gate filter)
   - tier-master.json gating before insert
   - DaytradeEngine signal aggregation suppressing cross-pair
   - Demo_trader QUALIFIED_TYPES check
2. **Pause new strategy adoption** until ≥80% of deployed strategies have ≥1 Shadow trade in 30 days.
3. **Re-run G1** with proper sr_levels for sr_anti_hunt_bounce / sr_liquidity_grab to disambiguate diagnostic harness limit vs real 0-firing.
