# SHADOW_PROMOTE R2 Alert - 2026-11-19T05:55:24.630219+00:00

- Source: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=2000`
- Lookback: `30d`
- Filters: `is_shadow=1`, `pnl_pips IS NOT NULL`, `dedup_violation != 1`, XAU instruments excluded
- Gate: `N >= 10 and EV < 0` -> WARN; `N >= 30 and EV < 0` -> CRITICAL
- Mode: read-only; no env vars, strategy code, tier-master, or DB writes

## Summary

- Promoted strategies: 65
- Cells: 123
- OK: 100
- WARN: 17
- CRITICAL: 6

## WARN / CRITICAL

| Severity | Strategy | Instrument | N | EV | WR | Wilson lower | PF |
|---|---|---|---:|---:|---:|---:|---:|
| **WARN** | `bb_squeeze_breakout` | `EUR_USD` | 25 | -1.628 | 24.0% | 11.5% | 0.32 |
| **WARN** | `bb_squeeze_breakout` | `GBP_USD` | 10 | -0.200 | 40.0% | 16.8% | 0.90 |
| **WARN** | `donchian_momentum_breakout` | `NZD_USD` | 10 | -2.640 | 70.0% | 39.7% | 0.40 |
| **WARN** | `dt_sr_channel_reversal` | `EUR_USD` | 16 | -0.744 | 31.2% | 14.2% | 0.74 |
| **CRITICAL** | `dt_sr_channel_reversal` | `GBP_JPY` | 31 | -6.361 | 29.0% | 16.1% | 0.31 |
| **WARN** | `dt_sr_channel_reversal` | `GBP_USD` | 20 | -1.770 | 40.0% | 21.9% | 0.50 |
| **WARN** | `dt_sr_channel_reversal` | `USD_JPY` | 20 | -0.880 | 35.0% | 18.1% | 0.78 |
| **CRITICAL** | `london_breakout` | `EUR_USD` | 40 | -0.832 | 37.5% | 24.2% | 0.64 |
| **WARN** | `sr_anti_hunt_bounce` | `EUR_JPY` | 16 | -2.612 | 56.2% | 33.2% | 0.53 |
| **CRITICAL** | `sr_break_retest` | `AUD_JPY` | 43 | -3.374 | 41.9% | 28.4% | 0.48 |
| **CRITICAL** | `sr_break_retest` | `USD_JPY` | 31 | -0.500 | 48.4% | 32.0% | 0.88 |
| **WARN** | `three_bar_reversal` | `GBP_USD` | 10 | -1.430 | 30.0% | 10.8% | 0.55 |
| **CRITICAL** | `three_bar_reversal` | `USD_JPY` | 32 | -0.266 | 43.8% | 28.2% | 0.86 |
| **WARN** | `trend_rebound` | `USD_JPY` | 16 | -0.400 | 37.5% | 18.5% | 0.72 |
| **WARN** | `trendline_sweep` | `EUR_GBP` | 26 | -1.900 | 46.2% | 28.8% | 0.49 |
| **WARN** | `trendline_sweep` | `GBP_USD` | 20 | -1.075 | 75.0% | 53.1% | 0.49 |
| **WARN** | `vol_surge_detector` | `EUR_USD` | 20 | -1.805 | 20.0% | 8.1% | 0.25 |
| **WARN** | `vol_surge_detector` | `GBP_USD` | 15 | -1.767 | 40.0% | 19.8% | 0.38 |
| **CRITICAL** | `wick_imbalance_reversion` | `AUD_JPY` | 32 | -6.106 | 37.5% | 22.9% | 0.27 |
| **WARN** | `wick_imbalance_reversion` | `EUR_JPY` | 19 | -6.000 | 36.8% | 19.1% | 0.36 |
| **WARN** | `wick_imbalance_reversion` | `EUR_USD` | 18 | -1.128 | 50.0% | 29.0% | 0.64 |
| **WARN** | `wick_imbalance_reversion` | `GBP_JPY` | 17 | -2.647 | 47.1% | 26.2% | 0.71 |
| **WARN** | `wick_imbalance_reversion` | `GBP_USD` | 15 | -4.067 | 33.3% | 15.2% | 0.16 |

## R2 Demote Manual Action

For each CRITICAL cell, manually verify and then remove the relevant Render env var:

- `dt_sr_channel_reversal` x `GBP_JPY`: remove `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE`
- `london_breakout` x `EUR_USD`: remove `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `AUD_JPY`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `USD_JPY`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `three_bar_reversal` x `USD_JPY`: remove `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`
- `wick_imbalance_reversion` x `AUD_JPY`: remove `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`, `WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE`

Code review locations if manual demotion is chosen:
- `strategies/daytrade/__init__.py` `split_shadow_always` / `SHADOW_ALWAYS_STRATEGIES`
- `strategies/hourly/__init__.py` `split_shadow_always`
- `strategies/scalp/__init__.py` `split_shadow_always`

## Apply Demote Suggestion

- Registry: `/home/runner/work/fx-ai-trader/fx-ai-trader/modules/shadow_demote_registry.py`
- Missing CRITICAL cells: `6`
- Add `('dt_sr_channel_reversal', 'GBP_JPY')`
- Add `('london_breakout', 'EUR_USD')`
- Add `('sr_break_retest', 'AUD_JPY')`
- Add `('sr_break_retest', 'USD_JPY')`
- Add `('three_bar_reversal', 'USD_JPY')`
- Add `('wick_imbalance_reversion', 'AUD_JPY')`

## All Cells

| Severity | Strategy | Instrument | N | Wins | Losses | EV | WR | Wilson 95% | PF | Env |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| OK | `adx_trend_continuation` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ADX_TREND_CONTINUATION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `asia_range_fade_v1` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ASIA_RANGE_FADE_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `atr_regime_break` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ALPHA_ATR_REGIME_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_rsi_ema_aligned` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `BB_RSI_EMA_ALIGNED_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `bb_squeeze_breakout` | `EUR_USD` | 25 | 6 | 19 | -1.628 | 24.0% | 11.5%-43.4% | 0.32 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `bb_squeeze_breakout` | `GBP_USD` | 10 | 4 | 6 | -0.200 | 40.0% | 16.8%-68.7% | 0.90 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `USD_CHF` | 3 | 0 | 3 | -2.333 | 0.0% | 0.0%-56.2% | 0.00 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `USD_JPY` | 16 | 8 | 8 | +0.013 | 50.0% | 28.0%-72.0% | 1.01 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `confluence_scalp` | `USD_JPY` | 1 | 0 | 1 | -3.400 | 0.0% | 0.0%-79.3% | 0.00 | `CONFLUENCE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `cpd_divergence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CPD_DIVERGENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `AUD_JPY` | 5 | 1 | 4 | -15.840 | 20.0% | 3.6%-62.4% | 0.02 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `AUD_USD` | 4 | 1 | 3 | -1.425 | 25.0% | 4.6%-69.9% | 0.76 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `EUR_USD` | 3 | 2 | 1 | -6.433 | 66.7% | 20.8%-93.9% | 0.37 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `donchian_momentum_breakout` | `NZD_USD` | 10 | 7 | 3 | -2.640 | 70.0% | 39.7%-89.2% | 0.40 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `USD_JPY` | 8 | 4 | 4 | -4.613 | 50.0% | 21.5%-78.5% | 0.43 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `EUR_USD` | 4 | 2 | 2 | -1.000 | 50.0% | 15.0%-85.0% | 0.46 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `GBP_USD` | 5 | 2 | 3 | -3.560 | 40.0% | 11.8%-76.9% | 0.11 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `USD_JPY` | 7 | 4 | 3 | +2.414 | 57.1% | 25.0%-84.2% | 3.68 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `EUR_GBP` | 7 | 3 | 4 | -0.243 | 42.9% | 15.8%-75.0% | 0.92 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `EUR_JPY` | 30 | 15 | 15 | +0.000 | 50.0% | 33.2%-66.8% | 1.00 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_USD` | 16 | 5 | 11 | -0.744 | 31.2% | 14.2%-55.6% | 0.74 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `dt_sr_channel_reversal` | `GBP_JPY` | 31 | 9 | 22 | -6.361 | 29.0% | 16.1%-46.6% | 0.31 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `GBP_USD` | 20 | 8 | 12 | -1.770 | 40.0% | 21.9%-61.3% | 0.50 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `USD_JPY` | 20 | 7 | 13 | -0.880 | 35.0% | 18.1%-56.7% | 0.78 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema200_trend_reversal` | `USD_JPY` | 2 | 2 | 0 | +5.000 | 100.0% | 34.2%-100.0% | n/a | `EMA200_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`<br>`EMA200_TREND_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_ribbon_ride` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_RIBBON_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_trend_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `engulfing_bb` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_pips_hunter` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_PIPS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_trend_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_TREND_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_vol_break` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_VOL_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `AUD_JPY` | 4 | 2 | 2 | +1.150 | 50.0% | 15.0%-85.0% | 1.24 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `EUR_JPY` | 6 | 3 | 3 | +3.767 | 50.0% | 18.8%-81.2% | 1.54 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `EUR_USD` | 1 | 1 | 0 | +0.800 | 100.0% | 20.7%-100.0% | n/a | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_JPY` | 1 | 1 | 0 | +3.000 | 100.0% | 20.7%-100.0% | n/a | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_USD` | 1 | 1 | 0 | +17.400 | 100.0% | 20.7%-100.0% | n/a | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `USD_JPY` | 1 | 0 | 1 | -10.000 | 0.0% | 0.0%-79.3% | 0.00 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `EUR_GBP` | 1 | 0 | 1 | -1.300 | 0.0% | 0.0%-79.3% | 0.00 | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `EUR_USD` | 3 | 3 | 0 | +0.800 | 100.0% | 43.8%-100.0% | n/a | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `USD_JPY` | 1 | 1 | 0 | +0.800 | 100.0% | 20.7%-100.0% | n/a | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `intraday_seasonality` | `AUD_JPY` | 1 | 0 | 1 | -23.400 | 0.0% | 0.0%-79.3% | 0.00 | `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `intraday_seasonality` | `GBP_USD` | 1 | 0 | 1 | -10.000 | 0.0% | 0.0%-79.3% | 0.00 | `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `jpy_basket_trend` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `JPY_BASKET_TREND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `keltner_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `lin_reg_channel` | `EUR_USD` | 28 | 19 | 9 | +1.539 | 67.9% | 49.3%-82.1% | 1.92 | `LIN_REG_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `london_breakout` | `EUR_USD` | 40 | 15 | 25 | -0.832 | 37.5% | 24.2%-53.0% | 0.64 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_breakout` | `USD_JPY` | 9 | 3 | 6 | -2.189 | 33.3% | 12.1%-64.6% | 0.26 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_ny_swing` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_NY_SWING_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `EUR_USD` | 5 | 4 | 1 | +1.700 | 80.0% | 37.6%-96.4% | 22.25 | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `GBP_USD` | 7 | 6 | 1 | +1.957 | 85.7% | 48.7%-97.4% | 1.69 | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_shrapnel` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_SHRAPNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_mr_hybrid` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_MR_HYBRID_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_regime_switch` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_trend_perfect` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_TREND_PERFECT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `EUR_USD` | 2 | 0 | 2 | -3.450 | 0.0% | 0.0%-65.8% | 0.00 | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `EUR_USD` | 6 | 3 | 3 | +0.433 | 50.0% | 18.8%-81.2% | 1.28 | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_regime_range_cascade_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `EUR_USD` | 3 | 1 | 2 | -2.233 | 33.3% | 6.1%-79.2% | 0.06 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `GBP_USD` | 1 | 0 | 1 | -5.800 | 0.0% | 0.0%-79.3% | 0.00 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `USD_JPY` | 5 | 1 | 4 | -2.540 | 20.0% | 3.6%-62.4% | 0.06 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `AUD_JPY` | 2 | 1 | 1 | -4.750 | 50.0% | 9.5%-90.5% | 0.14 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `EUR_JPY` | 3 | 3 | 0 | +5.600 | 100.0% | 43.8%-100.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `EUR_USD` | 4 | 2 | 2 | -6.100 | 50.0% | 15.0%-85.0% | 0.05 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `USD_JPY` | 3 | 1 | 2 | -3.800 | 33.3% | 6.1%-79.2% | 0.45 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ofi_mr` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `OFI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `EUR_USD` | 5 | 0 | 5 | -7.720 | 0.0% | 0.0%-43.4% | 0.00 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `GBP_USD` | 6 | 4 | 2 | -0.900 | 66.7% | 30.0%-90.3% | 0.71 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `USD_JPY` | 1 | 1 | 0 | +0.800 | 100.0% | 20.7%-100.0% | n/a | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `post_news_vol` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `AUD_JPY` | 1 | 1 | 0 | +10.300 | 100.0% | 20.7%-100.0% | n/a | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `EUR_JPY` | 1 | 1 | 0 | +9.900 | 100.0% | 20.7%-100.0% | n/a | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `session_vol_expansion` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SESSION_VOL_EXPANSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `squeeze_release_momentum` | `EUR_USD` | 3 | 2 | 1 | +1.733 | 66.7% | 20.8%-93.9% | 1.65 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_anti_hunt_bounce` | `EUR_JPY` | 16 | 9 | 7 | -2.612 | 56.2% | 33.2%-76.9% | 0.53 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `EUR_USD` | 3 | 3 | 0 | +4.200 | 100.0% | 43.8%-100.0% | n/a | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_JPY` | 8 | 3 | 5 | -9.762 | 37.5% | 13.7%-69.4% | 0.32 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_USD` | 3 | 1 | 2 | -3.767 | 33.3% | 6.1%-79.2% | 0.10 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `USD_JPY` | 3 | 0 | 3 | -15.833 | 0.0% | 0.0%-56.2% | 0.00 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `AUD_JPY` | 43 | 18 | 25 | -3.374 | 41.9% | 28.4%-56.7% | 0.48 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `USD_JPY` | 31 | 15 | 16 | -0.500 | 48.4% | 32.0%-65.2% | 0.88 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_channel_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_fib_confluence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_liquidity_grab` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_LIQUIDITY_GRAB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `stoch_trend_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `EUR_USD` | 12 | 7 | 5 | +1.250 | 58.3% | 32.0%-80.7% | 1.87 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `three_bar_reversal` | `GBP_USD` | 10 | 3 | 7 | -1.430 | 30.0% | 10.8%-60.3% | 0.55 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `three_bar_reversal` | `USD_JPY` | 32 | 14 | 18 | -0.266 | 43.8% | 28.2%-60.7% | 0.86 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `AUD_JPY` | 7 | 5 | 2 | -4.071 | 71.4% | 35.9%-91.8% | 0.22 | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `EUR_JPY` | 1 | 0 | 1 | -13.100 | 0.0% | 0.0%-79.3% | 0.00 | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `USD_JPY` | 6 | 3 | 3 | -8.417 | 50.0% | 18.8%-81.2% | 0.02 | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_range_breakout_up` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_RANGE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `EUR_USD` | 8 | 3 | 5 | -0.950 | 37.5% | 13.7%-69.4% | 0.57 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `GBP_USD` | 5 | 3 | 2 | -0.520 | 60.0% | 23.1%-88.2% | 0.59 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trend_rebound` | `USD_JPY` | 16 | 6 | 10 | -0.400 | 37.5% | 18.5%-61.4% | 0.72 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `EUR_GBP` | 26 | 12 | 14 | -1.900 | 46.2% | 28.8%-64.5% | 0.49 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trendline_sweep` | `EUR_USD` | 8 | 6 | 2 | +2.687 | 75.0% | 40.9%-92.9% | 2.29 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `GBP_USD` | 20 | 15 | 5 | -1.075 | 75.0% | 53.1%-88.8% | 0.49 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `turtle_soup` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TURTLE_SOUP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tvsm` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TVSM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `v_reversal` | `USD_JPY` | 3 | 2 | 1 | +1.733 | 66.7% | 20.8%-93.9% | 2.24 | `V_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vbp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `VBP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `EUR_JPY` | 1 | 1 | 0 | +6.800 | 100.0% | 20.7%-100.0% | n/a | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_momentum_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `EUR_USD` | 20 | 4 | 16 | -1.805 | 20.0% | 8.1%-41.6% | 0.25 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `GBP_USD` | 15 | 6 | 9 | -1.767 | 40.0% | 19.8%-64.3% | 0.38 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `USD_JPY` | 2 | 1 | 1 | +0.100 | 50.0% | 9.5%-90.5% | 1.04 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `AUD_JPY` | 2 | 2 | 0 | +1.650 | 100.0% | 34.2%-100.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_GBP` | 2 | 1 | 1 | -2.250 | 50.0% | 9.5%-90.5% | 0.24 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_JPY` | 2 | 0 | 2 | -20.450 | 0.0% | 0.0%-65.8% | 0.00 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_USD` | 6 | 3 | 3 | -2.817 | 50.0% | 18.8%-81.2% | 0.12 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_JPY` | 5 | 2 | 3 | -5.820 | 40.0% | 11.8%-76.9% | 0.52 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_USD` | 4 | 3 | 1 | -0.400 | 75.0% | 30.1%-95.4% | 0.69 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `wick_imbalance_reversion` | `AUD_JPY` | 32 | 12 | 20 | -6.106 | 37.5% | 22.9%-54.7% | 0.27 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_GBP` | 1 | 0 | 1 | -4.300 | 0.0% | 0.0%-79.3% | 0.00 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `EUR_JPY` | 19 | 7 | 12 | -6.000 | 36.8% | 19.1%-59.0% | 0.36 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `EUR_USD` | 18 | 9 | 9 | -1.128 | 50.0% | 29.0%-71.0% | 0.64 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `GBP_JPY` | 17 | 8 | 9 | -2.647 | 47.1% | 26.2%-69.0% | 0.71 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `GBP_USD` | 15 | 5 | 10 | -4.067 | 33.3% | 15.2%-58.3% | 0.16 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `USD_JPY` | 6 | 2 | 4 | -5.950 | 33.3% | 9.7%-70.0% | 0.04 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `xs_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
