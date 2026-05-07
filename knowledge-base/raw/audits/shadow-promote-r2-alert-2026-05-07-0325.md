# SHADOW_PROMOTE R2 Alert - 2026-05-07T03:25:17.581202+00:00

- Source: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=2000`
- Lookback: `30d`
- Filters: `is_shadow=1`, `pnl_pips IS NOT NULL`, XAU instruments excluded
- Gate: `N >= 10 and EV < 0` -> WARN; `N >= 30 and EV < 0` -> CRITICAL
- Mode: read-only; no env vars, strategy code, tier-master, or DB writes

## Summary

- Promoted strategies: 64
- Cells: 115
- OK: 87
- WARN: 16
- CRITICAL: 12

## WARN / CRITICAL

| Severity | Strategy | Instrument | N | EV | WR | Wilson lower | PF |
|---|---|---|---:|---:|---:|---:|---:|
| **CRITICAL** | `bb_rsi_reversion` | `EUR_USD` | 51 | -0.749 | 31.4% | 20.3% | 0.66 |
| **CRITICAL** | `bb_rsi_reversion` | `GBP_USD` | 34 | -2.306 | 14.7% | 6.4% | 0.34 |
| **CRITICAL** | `bb_rsi_reversion` | `USD_JPY` | 86 | -0.278 | 39.5% | 29.9% | 0.90 |
| **CRITICAL** | `ema_trend_scalp` | `EUR_USD` | 79 | -0.906 | 19.0% | 11.9% | 0.63 |
| **CRITICAL** | `ema_trend_scalp` | `GBP_USD` | 98 | -0.783 | 21.4% | 14.5% | 0.75 |
| **CRITICAL** | `ema_trend_scalp` | `USD_JPY` | 215 | -1.438 | 23.3% | 18.1% | 0.61 |
| **WARN** | `engulfing_bb` | `EUR_USD` | 14 | -2.693 | 7.1% | 1.3% | 0.18 |
| **CRITICAL** | `engulfing_bb` | `USD_JPY` | 47 | -1.953 | 19.1% | 10.4% | 0.53 |
| **WARN** | `lin_reg_channel` | `EUR_USD` | 10 | -7.110 | 10.0% | 1.8% | 0.15 |
| **WARN** | `macdh_reversal` | `USD_JPY` | 16 | -0.762 | 25.0% | 10.2% | 0.71 |
| **WARN** | `sr_anti_hunt_bounce` | `USD_JPY` | 24 | -15.829 | 0.0% | 0.0% | 0.00 |
| **WARN** | `sr_break_retest` | `GBP_JPY` | 12 | -5.117 | 16.7% | 4.7% | 0.57 |
| **WARN** | `sr_break_retest` | `USD_JPY` | 11 | -1.218 | 36.4% | 15.2% | 0.73 |
| **CRITICAL** | `sr_channel_reversal` | `EUR_USD` | 31 | -1.177 | 25.8% | 13.7% | 0.62 |
| **WARN** | `sr_channel_reversal` | `GBP_USD` | 17 | -2.071 | 17.6% | 6.2% | 0.49 |
| **CRITICAL** | `sr_channel_reversal` | `USD_JPY` | 97 | -1.774 | 17.5% | 11.2% | 0.36 |
| **CRITICAL** | `sr_fib_confluence` | `EUR_JPY` | 43 | -13.063 | 4.7% | 1.3% | 0.17 |
| **WARN** | `sr_fib_confluence` | `EUR_USD` | 25 | -1.340 | 28.0% | 14.3% | 0.71 |
| **CRITICAL** | `sr_fib_confluence` | `GBP_JPY` | 63 | -6.706 | 17.5% | 10.0% | 0.55 |
| **CRITICAL** | `sr_fib_confluence` | `USD_JPY` | 30 | -3.707 | 20.0% | 9.5% | 0.67 |
| **WARN** | `stoch_trend_pullback` | `EUR_USD` | 12 | -2.083 | 8.3% | 1.5% | 0.25 |
| **WARN** | `stoch_trend_pullback` | `USD_JPY` | 24 | -3.783 | 16.7% | 6.7% | 0.35 |
| **WARN** | `vol_momentum_scalp` | `GBP_USD` | 29 | -2.131 | 13.8% | 5.5% | 0.47 |
| **WARN** | `vol_surge_detector` | `GBP_USD` | 14 | -4.250 | 0.0% | 0.0% | 0.00 |
| **WARN** | `vol_surge_detector` | `USD_JPY` | 20 | -3.270 | 15.0% | 5.2% | 0.49 |
| **WARN** | `wick_imbalance_reversion` | `GBP_JPY` | 12 | -4.333 | 8.3% | 1.5% | 0.43 |
| **WARN** | `xs_momentum` | `EUR_USD` | 17 | -2.341 | 23.5% | 9.6% | 0.64 |
| **WARN** | `xs_momentum` | `USD_JPY` | 10 | -1.660 | 40.0% | 16.8% | 0.73 |

## R2 Demote Manual Action

For each CRITICAL cell, manually verify and then remove the relevant Render env var:

- `bb_rsi_reversion` x `EUR_USD`: remove `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE`
- `bb_rsi_reversion` x `GBP_USD`: remove `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE`
- `bb_rsi_reversion` x `USD_JPY`: remove `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE`
- `ema_trend_scalp` x `EUR_USD`: remove `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE`
- `ema_trend_scalp` x `GBP_USD`: remove `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE`
- `ema_trend_scalp` x `USD_JPY`: remove `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE`
- `engulfing_bb` x `USD_JPY`: remove `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_channel_reversal` x `EUR_USD`: remove `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_channel_reversal` x `USD_JPY`: remove `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_fib_confluence` x `EUR_JPY`: remove `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_fib_confluence` x `GBP_JPY`: remove `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_fib_confluence` x `USD_JPY`: remove `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE`

Code review locations if manual demotion is chosen:
- `strategies/daytrade/__init__.py` `split_shadow_always` / `SHADOW_ALWAYS_STRATEGIES`
- `strategies/hourly/__init__.py` `split_shadow_always`
- `strategies/scalp/__init__.py` `split_shadow_always`

## All Cells

| Severity | Strategy | Instrument | N | Wins | Losses | EV | WR | Wilson 95% | PF | Env |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| OK | `adx_trend_continuation` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ADX_TREND_CONTINUATION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `asia_range_fade_v1` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ASIA_RANGE_FADE_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `atr_regime_break` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ALPHA_ATR_REGIME_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_rsi_ema_aligned` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `BB_RSI_EMA_ALIGNED_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `bb_rsi_reversion` | `EUR_USD` | 51 | 16 | 35 | -0.749 | 31.4% | 20.3%-45.0% | 0.66 | `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `bb_rsi_reversion` | `GBP_USD` | 34 | 5 | 29 | -2.306 | 14.7% | 6.4%-30.1% | 0.34 | `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `bb_rsi_reversion` | `USD_JPY` | 86 | 34 | 52 | -0.278 | 39.5% | 29.9%-50.1% | 0.90 | `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `EUR_USD` | 14 | 2 | 12 | +0.007 | 14.3% | 4.0%-39.9% | 1.00 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `GBP_USD` | 9 | 4 | 5 | +2.667 | 44.4% | 18.9%-73.3% | 2.63 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `USD_JPY` | 4 | 0 | 4 | -4.175 | 0.0% | 0.0%-49.0% | 0.00 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `confluence_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CONFLUENCE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `cpd_divergence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CPD_DIVERGENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `EUR_USD` | 1 | 1 | 0 | +16.200 | 100.0% | 20.7%-100.0% | n/a | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `GBP_USD` | 8 | 0 | 8 | -6.025 | 0.0% | 0.0%-32.4% | 0.00 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `USD_JPY` | 10 | 7 | 3 | +8.510 | 70.0% | 39.7%-89.2% | 4.38 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `EUR_JPY` | 8 | 3 | 5 | -0.287 | 37.5% | 13.7%-69.4% | 0.97 | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `GBP_JPY` | 1 | 0 | 1 | -20.000 | 0.0% | 0.0%-79.3% | 0.00 | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `GBP_USD` | 7 | 2 | 5 | +0.743 | 28.6% | 8.2%-64.1% | 1.21 | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `USD_JPY` | 3 | 2 | 1 | +11.000 | 66.7% | 20.8%-93.9% | n/a | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `EUR_JPY` | 12 | 8 | 4 | +14.283 | 66.7% | 39.1%-86.2% | 3.61 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `EUR_USD` | 3 | 0 | 3 | -2.167 | 0.0% | 0.0%-56.2% | 0.00 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `GBP_JPY` | 6 | 3 | 3 | +0.817 | 50.0% | 18.8%-81.2% | 1.09 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `GBP_USD` | 2 | 0 | 2 | -6.550 | 0.0% | 0.0%-65.8% | 0.00 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `USD_JPY` | 6 | 2 | 4 | -3.783 | 33.3% | 9.7%-70.0% | 0.45 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema200_trend_reversal` | `EUR_JPY` | 3 | 3 | 0 | +24.000 | 100.0% | 43.8%-100.0% | n/a | `EMA200_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`<br>`EMA200_TREND_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `EUR_JPY` | 4 | 1 | 3 | +0.200 | 25.0% | 4.6%-69.9% | 1.02 | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `EUR_USD` | 2 | 1 | 1 | +5.550 | 50.0% | 9.5%-90.5% | 2.66 | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `GBP_JPY` | 4 | 0 | 4 | -16.175 | 0.0% | 0.0%-49.0% | 0.00 | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `GBP_USD` | 1 | 0 | 1 | -11.400 | 0.0% | 0.0%-79.3% | 0.00 | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `USD_JPY` | 6 | 5 | 1 | +8.667 | 83.3% | 43.6%-97.0% | 6.00 | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_pullback` | `USD_JPY` | 3 | 2 | 1 | +15.600 | 66.7% | 20.8%-93.9% | 59.50 | `EMA_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_ribbon_ride` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_RIBBON_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `ema_trend_scalp` | `EUR_USD` | 79 | 15 | 64 | -0.906 | 19.0% | 11.9%-29.0% | 0.63 | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `ema_trend_scalp` | `GBP_USD` | 98 | 21 | 77 | -0.783 | 21.4% | 14.5%-30.5% | 0.75 | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `ema_trend_scalp` | `USD_JPY` | 215 | 50 | 165 | -1.438 | 23.3% | 18.1%-29.3% | 0.61 | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `engulfing_bb` | `EUR_USD` | 14 | 1 | 13 | -2.693 | 7.1% | 1.3%-31.5% | 0.18 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `engulfing_bb` | `GBP_USD` | 7 | 1 | 6 | -4.371 | 14.3% | 2.6%-51.3% | 0.07 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `engulfing_bb` | `USD_JPY` | 47 | 9 | 38 | -1.953 | 19.1% | 10.4%-32.5% | 0.53 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_pips_hunter` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_PIPS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_trend_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_TREND_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_vol_break` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_VOL_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `EUR_JPY` | 7 | 1 | 6 | -16.300 | 14.3% | 2.6%-51.3% | 0.01 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_JPY` | 1 | 0 | 1 | -23.500 | 0.0% | 0.0%-79.3% | 0.00 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_USD` | 1 | 1 | 0 | +2.300 | 100.0% | 20.7%-100.0% | n/a | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `intraday_seasonality` | `GBP_USD` | 9 | 4 | 5 | +2.100 | 44.4% | 18.9%-73.3% | 1.65 | `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `jpy_basket_trend` | `EUR_JPY` | 6 | 1 | 5 | +1.000 | 16.7% | 3.0%-56.4% | 1.33 | `JPY_BASKET_TREND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `keltner_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `lin_reg_channel` | `EUR_USD` | 10 | 1 | 9 | -7.110 | 10.0% | 1.8%-40.4% | 0.15 | `LIN_REG_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_ny_swing` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_NY_SWING_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_shrapnel` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_SHRAPNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_regime_switch` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `EUR_USD` | 3 | 1 | 2 | -1.233 | 33.3% | 6.1%-79.2% | 0.70 | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `macdh_reversal` | `USD_JPY` | 16 | 4 | 12 | -0.762 | 25.0% | 10.2%-49.5% | 0.71 | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_regime_range_cascade_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `GBP_USD` | 1 | 0 | 1 | -0.200 | 0.0% | 0.0%-79.3% | 0.00 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ofi_mr` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `OFI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `USD_JPY` | 1 | 0 | 1 | -13.400 | 0.0% | 0.0%-79.3% | 0.00 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `post_news_vol` | `EUR_USD` | 6 | 0 | 6 | -14.817 | 0.0% | 0.0%-39.0% | 0.00 | `POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `post_news_vol` | `GBP_USD` | 2 | 0 | 2 | -14.250 | 0.0% | 0.0%-65.8% | 0.00 | `POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `post_news_vol` | `USD_JPY` | 9 | 5 | 4 | +46.678 | 55.6% | 26.7%-81.1% | 11.50 | `POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `session_vol_expansion` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SESSION_VOL_EXPANSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `squeeze_release_momentum` | `GBP_USD` | 2 | 0 | 2 | -4.600 | 0.0% | 0.0%-65.8% | 0.00 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `EUR_JPY` | 7 | 1 | 6 | -9.086 | 14.3% | 2.6%-51.3% | 0.14 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_JPY` | 6 | 1 | 5 | -7.433 | 16.7% | 3.0%-56.4% | 0.49 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_anti_hunt_bounce` | `USD_JPY` | 24 | 0 | 24 | -15.829 | 0.0% | 0.0%-13.8% | 0.00 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_break_retest` | `EUR_JPY` | 9 | 2 | 7 | -1.278 | 22.2% | 6.3%-54.7% | 0.84 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_break_retest` | `GBP_JPY` | 12 | 2 | 10 | -5.117 | 16.7% | 4.7%-44.8% | 0.57 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_break_retest` | `GBP_USD` | 8 | 5 | 3 | +8.300 | 62.5% | 30.6%-86.3% | 5.05 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_break_retest` | `USD_JPY` | 11 | 4 | 7 | -1.218 | 36.4% | 15.2%-64.6% | 0.73 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_channel_reversal` | `EUR_USD` | 31 | 8 | 23 | -1.177 | 25.8% | 13.7%-43.2% | 0.62 | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_channel_reversal` | `GBP_USD` | 17 | 3 | 14 | -2.071 | 17.6% | 6.2%-41.0% | 0.49 | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_channel_reversal` | `USD_JPY` | 97 | 17 | 80 | -1.774 | 17.5% | 11.2%-26.3% | 0.36 | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_fib_confluence` | `EUR_JPY` | 43 | 2 | 41 | -13.063 | 4.7% | 1.3%-15.5% | 0.17 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_fib_confluence` | `EUR_USD` | 25 | 7 | 18 | -1.340 | 28.0% | 14.3%-47.6% | 0.71 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_fib_confluence` | `GBP_JPY` | 63 | 11 | 52 | -6.706 | 17.5% | 10.0%-28.6% | 0.55 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_fib_confluence` | `GBP_USD` | 35 | 14 | 21 | +2.534 | 40.0% | 25.6%-56.4% | 1.62 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_fib_confluence` | `USD_JPY` | 30 | 6 | 24 | -3.707 | 20.0% | 9.5%-37.3% | 0.67 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_liquidity_grab` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_LIQUIDITY_GRAB_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `stoch_trend_pullback` | `EUR_USD` | 12 | 1 | 11 | -2.083 | 8.3% | 1.5%-35.4% | 0.25 | `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `stoch_trend_pullback` | `GBP_USD` | 9 | 1 | 8 | -2.511 | 11.1% | 2.0%-43.5% | 0.22 | `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `stoch_trend_pullback` | `USD_JPY` | 24 | 4 | 20 | -3.783 | 16.7% | 6.7%-35.9% | 0.35 | `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `EUR_USD` | 1 | 0 | 1 | -5.800 | 0.0% | 0.0%-79.3% | 0.00 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `USD_JPY` | 1 | 0 | 1 | -0.300 | 0.0% | 0.0%-79.3% | 0.00 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_range_breakout_up` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_RANGE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `EUR_USD` | 5 | 1 | 4 | -1.960 | 20.0% | 3.6%-62.4% | 0.37 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `GBP_USD` | 4 | 2 | 2 | +5.725 | 50.0% | 15.0%-85.0% | 4.75 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `USD_JPY` | 17 | 7 | 10 | +1.141 | 41.2% | 21.6%-64.0% | 1.52 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trendline_sweep` | `EUR_USD` | 6 | 1 | 5 | -2.550 | 16.7% | 3.0%-56.4% | 0.57 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trendline_sweep` | `GBP_USD` | 1 | 0 | 1 | -5.100 | 0.0% | 0.0%-79.3% | 0.00 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `turtle_soup` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TURTLE_SOUP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tvsm` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TVSM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `v_reversal` | `USD_JPY` | 4 | 2 | 2 | +2.375 | 50.0% | 15.0%-85.0% | 4.06 | `V_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vbp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `VBP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_momentum_scalp` | `GBP_USD` | 29 | 4 | 25 | -2.131 | 13.8% | 5.5%-30.6% | 0.47 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_momentum_scalp` | `USD_JPY` | 8 | 1 | 7 | -3.862 | 12.5% | 2.2%-47.1% | 0.19 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `EUR_USD` | 7 | 3 | 4 | +0.100 | 42.9% | 15.8%-75.0% | 1.03 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `GBP_USD` | 14 | 0 | 14 | -4.250 | 0.0% | 0.0%-21.5% | 0.00 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `USD_JPY` | 20 | 3 | 17 | -3.270 | 15.0% | 5.2%-36.0% | 0.49 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_JPY` | 5 | 0 | 5 | -17.880 | 0.0% | 0.0%-43.4% | 0.00 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `GBP_JPY` | 12 | 1 | 11 | -4.333 | 8.3% | 1.5%-35.4% | 0.43 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `GBP_USD` | 3 | 1 | 2 | -1.933 | 33.3% | 6.1%-79.2% | 0.29 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `USD_JPY` | 3 | 2 | 1 | -3.500 | 66.7% | 20.8%-93.9% | 0.62 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `xs_momentum` | `EUR_USD` | 17 | 4 | 13 | -2.341 | 23.5% | 9.6%-47.3% | 0.64 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `xs_momentum` | `GBP_USD` | 29 | 9 | 20 | +0.472 | 31.0% | 17.3%-49.2% | 1.06 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `xs_momentum` | `USD_JPY` | 10 | 4 | 6 | -1.660 | 40.0% | 16.8%-68.7% | 0.73 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
