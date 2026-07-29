# SHADOW_PROMOTE R2 Alert - 2026-07-29T02:27:30.394275+00:00

- Source: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=2000`
- Lookback: `30d`
- Filters: `is_shadow=1`, `pnl_pips IS NOT NULL`, `dedup_violation != 1`, XAU instruments excluded
- Gate: `N >= 10 and EV < 0` -> WARN; `N >= 30 and EV < 0` -> CRITICAL
- Mode: read-only; no env vars, strategy code, tier-master, or DB writes

## Summary

- Promoted strategies: 65
- Cells: 132
- OK: 93
- WARN: 29
- CRITICAL: 10

## WARN / CRITICAL

| Severity | Strategy | Instrument | N | EV | WR | Wilson lower | PF |
|---|---|---|---:|---:|---:|---:|---:|
| **WARN** | `donchian_momentum_breakout` | `AUD_JPY` | 11 | -4.182 | 63.6% | 35.4% | 0.41 |
| **WARN** | `dt_bb_rsi_mr` | `GBP_USD` | 17 | -3.753 | 35.3% | 17.3% | 0.32 |
| **WARN** | `dt_sr_channel_reversal` | `AUD_JPY` | 28 | -1.189 | 57.1% | 39.1% | 0.64 |
| **WARN** | `dt_sr_channel_reversal` | `EUR_GBP` | 26 | -0.769 | 46.2% | 28.8% | 0.68 |
| **WARN** | `dt_sr_channel_reversal` | `EUR_JPY` | 17 | -2.747 | 52.9% | 31.0% | 0.26 |
| **WARN** | `dt_sr_channel_reversal` | `EUR_USD` | 19 | -1.053 | 47.4% | 27.3% | 0.53 |
| **WARN** | `dt_sr_channel_reversal` | `GBP_JPY` | 23 | -0.874 | 69.6% | 49.1% | 0.71 |
| **WARN** | `dt_sr_channel_reversal` | `USD_JPY` | 11 | -1.173 | 54.5% | 28.0% | 0.68 |
| **WARN** | `ema200_trend_reversal` | `USD_JPY` | 20 | -0.035 | 60.0% | 38.7% | 0.99 |
| **CRITICAL** | `engulfing_bb` | `EUR_USD` | 87 | -1.257 | 33.3% | 24.3% | 0.38 |
| **CRITICAL** | `engulfing_bb` | `GBP_USD` | 31 | -0.997 | 41.9% | 26.4% | 0.62 |
| **WARN** | `lin_reg_channel` | `EUR_USD` | 25 | -1.868 | 48.0% | 30.0% | 0.34 |
| **WARN** | `london_breakout` | `EUR_USD` | 20 | -2.250 | 25.0% | 11.2% | 0.12 |
| **CRITICAL** | `london_breakout` | `GBP_USD` | 45 | -2.244 | 33.3% | 21.4% | 0.31 |
| **WARN** | `london_breakout` | `USD_JPY` | 15 | -3.013 | 26.7% | 10.9% | 0.11 |
| **CRITICAL** | `ma_regime_switch` | `USD_JPY` | 52 | -0.988 | 36.5% | 24.8% | 0.49 |
| **WARN** | `squeeze_release_momentum` | `EUR_USD` | 16 | -0.250 | 62.5% | 38.6% | 0.87 |
| **WARN** | `squeeze_release_momentum` | `GBP_USD` | 19 | -1.426 | 57.9% | 36.3% | 0.57 |
| **WARN** | `sr_anti_hunt_bounce` | `EUR_USD` | 16 | -1.881 | 56.2% | 33.2% | 0.41 |
| **WARN** | `sr_break_retest` | `AUD_JPY` | 21 | -1.700 | 61.9% | 40.9% | 0.48 |
| **CRITICAL** | `sr_break_retest` | `EUR_JPY` | 48 | -2.971 | 47.9% | 34.5% | 0.39 |
| **CRITICAL** | `sr_break_retest` | `GBP_JPY` | 30 | -4.470 | 60.0% | 42.3% | 0.30 |
| **CRITICAL** | `sr_break_retest` | `GBP_USD` | 40 | -1.473 | 55.0% | 39.8% | 0.56 |
| **WARN** | `sr_break_retest` | `USD_JPY` | 22 | -2.914 | 40.9% | 23.3% | 0.29 |
| **WARN** | `three_bar_reversal` | `EUR_USD` | 12 | -0.525 | 58.3% | 32.0% | 0.66 |
| **WARN** | `trend_rebound` | `USD_JPY` | 15 | -1.093 | 33.3% | 15.2% | 0.35 |
| **WARN** | `trendline_sweep` | `EUR_GBP` | 25 | -2.544 | 40.0% | 23.4% | 0.23 |
| **WARN** | `trendline_sweep` | `EUR_USD` | 16 | -0.169 | 75.0% | 50.5% | 0.94 |
| **WARN** | `trendline_sweep` | `GBP_USD` | 14 | -2.736 | 71.4% | 45.4% | 0.27 |
| **CRITICAL** | `vol_momentum_scalp` | `USD_JPY` | 70 | -1.337 | 35.7% | 25.5% | 0.40 |
| **WARN** | `vol_surge_detector` | `EUR_USD` | 21 | -1.657 | 28.6% | 13.8% | 0.28 |
| **WARN** | `vol_surge_detector` | `GBP_USD` | 18 | -1.861 | 27.8% | 12.5% | 0.35 |
| **WARN** | `vol_surge_detector` | `USD_JPY` | 13 | -0.131 | 46.2% | 23.2% | 0.93 |
| **WARN** | `wick_imbalance_reversion` | `EUR_JPY` | 17 | -2.741 | 52.9% | 31.0% | 0.45 |
| **WARN** | `wick_imbalance_reversion` | `GBP_JPY` | 13 | -1.015 | 69.2% | 42.4% | 0.77 |
| **WARN** | `wick_imbalance_reversion` | `GBP_USD` | 11 | -4.918 | 45.5% | 21.3% | 0.13 |
| **WARN** | `wick_imbalance_reversion` | `USD_JPY` | 11 | -3.864 | 45.5% | 21.3% | 0.13 |
| **CRITICAL** | `xs_momentum` | `EUR_USD` | 37 | -2.070 | 56.8% | 40.9% | 0.40 |
| **CRITICAL** | `xs_momentum` | `USD_JPY` | 36 | -0.103 | 61.1% | 44.9% | 0.97 |

## R2 Demote Manual Action

For each CRITICAL cell, manually verify and then remove the relevant Render env var:

- `engulfing_bb` x `EUR_USD`: remove `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE`
- `engulfing_bb` x `GBP_USD`: remove `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE`
- `london_breakout` x `GBP_USD`: remove `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE`
- `ma_regime_switch` x `USD_JPY`: remove `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `EUR_JPY`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `GBP_JPY`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `GBP_USD`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `vol_momentum_scalp` x `USD_JPY`: remove `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`, `VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE`
- `xs_momentum` x `EUR_USD`: remove `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`
- `xs_momentum` x `USD_JPY`: remove `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`

Code review locations if manual demotion is chosen:
- `strategies/daytrade/__init__.py` `split_shadow_always` / `SHADOW_ALWAYS_STRATEGIES`
- `strategies/hourly/__init__.py` `split_shadow_always`
- `strategies/scalp/__init__.py` `split_shadow_always`

## Apply Demote Suggestion

- Registry: `/home/runner/work/fx-ai-trader/fx-ai-trader/modules/shadow_demote_registry.py`
- Missing CRITICAL cells: `10`
- Add `('engulfing_bb', 'EUR_USD')`
- Add `('engulfing_bb', 'GBP_USD')`
- Add `('london_breakout', 'GBP_USD')`
- Add `('ma_regime_switch', 'USD_JPY')`
- Add `('sr_break_retest', 'EUR_JPY')`
- Add `('sr_break_retest', 'GBP_JPY')`
- Add `('sr_break_retest', 'GBP_USD')`
- Add `('vol_momentum_scalp', 'USD_JPY')`
- Add `('xs_momentum', 'EUR_USD')`
- Add `('xs_momentum', 'USD_JPY')`

## All Cells

| Severity | Strategy | Instrument | N | Wins | Losses | EV | WR | Wilson 95% | PF | Env |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| OK | `adx_trend_continuation` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ADX_TREND_CONTINUATION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `asia_range_fade_v1` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ASIA_RANGE_FADE_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `atr_regime_break` | `USD_JPY` | 1 | 1 | 0 | +1.800 | 100.0% | 20.7%-100.0% | n/a | `ALPHA_ATR_REGIME_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_rsi_ema_aligned` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `BB_RSI_EMA_ALIGNED_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `confluence_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CONFLUENCE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `cpd_divergence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CPD_DIVERGENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `donchian_momentum_breakout` | `AUD_JPY` | 11 | 7 | 4 | -4.182 | 63.6% | 35.4%-84.8% | 0.41 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `AUD_USD` | 6 | 3 | 3 | -4.267 | 50.0% | 18.8%-81.2% | 0.41 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `NZD_JPY` | 1 | 1 | 0 | +2.900 | 100.0% | 20.7%-100.0% | n/a | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `NZD_USD` | 12 | 10 | 2 | +1.525 | 83.3% | 55.2%-95.3% | 1.55 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `USD_JPY` | 10 | 6 | 4 | +0.020 | 60.0% | 31.3%-83.2% | 1.00 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `EUR_USD` | 7 | 5 | 2 | +1.800 | 71.4% | 35.9%-91.8% | 2.59 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_bb_rsi_mr` | `GBP_USD` | 17 | 6 | 11 | -3.753 | 35.3% | 17.3%-58.7% | 0.32 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `USD_JPY` | 6 | 4 | 2 | +1.000 | 66.7% | 30.0%-90.3% | 1.52 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `AUD_JPY` | 28 | 16 | 12 | -1.189 | 57.1% | 39.1%-73.5% | 0.64 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_GBP` | 26 | 12 | 14 | -0.769 | 46.2% | 28.8%-64.5% | 0.68 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_JPY` | 17 | 9 | 8 | -2.747 | 52.9% | 31.0%-73.8% | 0.26 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_USD` | 19 | 9 | 10 | -1.053 | 47.4% | 27.3%-68.3% | 0.53 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `GBP_JPY` | 23 | 16 | 7 | -0.874 | 69.6% | 49.1%-84.4% | 0.71 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `GBP_USD` | 15 | 7 | 8 | +0.207 | 46.7% | 24.8%-69.9% | 1.06 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `USD_JPY` | 11 | 6 | 5 | -1.173 | 54.5% | 28.0%-78.7% | 0.68 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `ema200_trend_reversal` | `USD_JPY` | 20 | 12 | 8 | -0.035 | 60.0% | 38.7%-78.1% | 0.99 | `EMA200_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`<br>`EMA200_TREND_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_ribbon_ride` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_RIBBON_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_trend_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `engulfing_bb` | `EUR_USD` | 87 | 29 | 58 | -1.257 | 33.3% | 24.3%-43.8% | 0.38 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `engulfing_bb` | `GBP_USD` | 31 | 13 | 18 | -0.997 | 41.9% | 26.4%-59.2% | 0.62 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_pips_hunter` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_PIPS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_trend_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_TREND_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_vol_break` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_VOL_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `AUD_JPY` | 2 | 2 | 0 | +2.050 | 100.0% | 34.2%-100.0% | n/a | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_JPY` | 1 | 1 | 0 | +2.000 | 100.0% | 20.7%-100.0% | n/a | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_USD` | 2 | 2 | 0 | +2.150 | 100.0% | 34.2%-100.0% | n/a | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `USD_JPY` | 1 | 1 | 0 | +0.600 | 100.0% | 20.7%-100.0% | n/a | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `EUR_USD` | 2 | 1 | 1 | -3.500 | 50.0% | 9.5%-90.5% | 0.05 | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `GBP_USD` | 5 | 2 | 3 | -4.860 | 40.0% | 11.8%-76.9% | 0.14 | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `intraday_seasonality` | `AUD_JPY` | 1 | 1 | 0 | +1.600 | 100.0% | 20.7%-100.0% | n/a | `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `intraday_seasonality` | `EUR_GBP` | 1 | 0 | 1 | -1.900 | 0.0% | 0.0%-79.3% | 0.00 | `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `jpy_basket_trend` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `JPY_BASKET_TREND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `keltner_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `lin_reg_channel` | `EUR_USD` | 25 | 12 | 13 | -1.868 | 48.0% | 30.0%-66.5% | 0.34 | `LIN_REG_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `london_breakout` | `EUR_USD` | 20 | 5 | 15 | -2.250 | 25.0% | 11.2%-46.9% | 0.12 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `london_breakout` | `GBP_USD` | 45 | 15 | 30 | -2.244 | 33.3% | 21.4%-47.9% | 0.31 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `london_breakout` | `USD_JPY` | 15 | 4 | 11 | -3.013 | 26.7% | 10.9%-52.0% | 0.11 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_ny_swing` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_NY_SWING_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `EUR_USD` | 3 | 1 | 2 | -1.500 | 33.3% | 6.1%-79.2% | 0.75 | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `GBP_USD` | 2 | 2 | 0 | +1.300 | 100.0% | 34.2%-100.0% | n/a | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_shrapnel` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_SHRAPNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_mr_hybrid` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_MR_HYBRID_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `ma_regime_switch` | `USD_JPY` | 52 | 19 | 33 | -0.988 | 36.5% | 24.8%-50.1% | 0.49 | `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_trend_perfect` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_TREND_PERFECT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `GBP_USD` | 2 | 0 | 2 | -2.700 | 0.0% | 0.0%-65.8% | 0.00 | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `EUR_USD` | 2 | 0 | 2 | -3.450 | 0.0% | 0.0%-65.8% | 0.00 | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `USD_JPY` | 1 | 1 | 0 | +7.300 | 100.0% | 20.7%-100.0% | n/a | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_regime_range_cascade_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `GBP_USD` | 1 | 0 | 1 | -4.100 | 0.0% | 0.0%-79.3% | 0.00 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `USD_JPY` | 4 | 2 | 2 | -1.175 | 50.0% | 15.0%-85.0% | 0.52 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `AUD_JPY` | 3 | 1 | 2 | -2.433 | 33.3% | 6.1%-79.2% | 0.25 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `EUR_GBP` | 2 | 2 | 0 | +8.750 | 100.0% | 34.2%-100.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `EUR_JPY` | 2 | 1 | 1 | -1.450 | 50.0% | 9.5%-90.5% | 0.43 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `EUR_USD` | 2 | 2 | 0 | +6.000 | 100.0% | 34.2%-100.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `GBP_JPY` | 3 | 3 | 0 | +2.800 | 100.0% | 43.8%-100.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `GBP_USD` | 4 | 4 | 0 | +1.650 | 100.0% | 51.0%-100.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `USD_JPY` | 2 | 0 | 2 | -5.400 | 0.0% | 0.0%-65.8% | 0.00 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ofi_mr` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `OFI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `EUR_USD` | 4 | 2 | 2 | -2.275 | 50.0% | 15.0%-85.0% | 0.08 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `GBP_USD` | 3 | 3 | 0 | +4.767 | 100.0% | 43.8%-100.0% | n/a | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `USD_JPY` | 2 | 2 | 0 | +15.750 | 100.0% | 34.2%-100.0% | n/a | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `post_news_vol` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `AUD_JPY` | 1 | 1 | 0 | +2.000 | 100.0% | 20.7%-100.0% | n/a | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `EUR_JPY` | 2 | 1 | 1 | -7.550 | 50.0% | 9.5%-90.5% | 0.12 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `GBP_JPY` | 1 | 1 | 0 | +2.900 | 100.0% | 20.7%-100.0% | n/a | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `GBP_USD` | 1 | 1 | 0 | +13.100 | 100.0% | 20.7%-100.0% | n/a | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `USD_JPY` | 1 | 1 | 0 | +0.300 | 100.0% | 20.7%-100.0% | n/a | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `session_vol_expansion` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SESSION_VOL_EXPANSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `squeeze_release_momentum` | `EUR_USD` | 16 | 10 | 6 | -0.250 | 62.5% | 38.6%-81.5% | 0.87 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `squeeze_release_momentum` | `GBP_USD` | 19 | 11 | 8 | -1.426 | 57.9% | 36.3%-76.9% | 0.57 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `EUR_JPY` | 15 | 12 | 3 | +1.133 | 80.0% | 54.8%-93.0% | 1.82 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_anti_hunt_bounce` | `EUR_USD` | 16 | 9 | 7 | -1.881 | 56.2% | 33.2%-76.9% | 0.41 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_JPY` | 3 | 1 | 2 | -8.267 | 33.3% | 6.1%-79.2% | 0.11 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_USD` | 2 | 2 | 0 | +2.150 | 100.0% | 34.2%-100.0% | n/a | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `USD_JPY` | 8 | 6 | 2 | +1.475 | 75.0% | 40.9%-92.9% | 3.19 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_break_retest` | `AUD_JPY` | 21 | 13 | 8 | -1.700 | 61.9% | 40.9%-79.2% | 0.48 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `EUR_JPY` | 48 | 23 | 25 | -2.971 | 47.9% | 34.5%-61.7% | 0.39 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `GBP_JPY` | 30 | 18 | 12 | -4.470 | 60.0% | 42.3%-75.4% | 0.30 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `GBP_USD` | 40 | 22 | 18 | -1.473 | 55.0% | 39.8%-69.3% | 0.56 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_break_retest` | `USD_JPY` | 22 | 9 | 13 | -2.914 | 40.9% | 23.3%-61.3% | 0.29 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_channel_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_fib_confluence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_liquidity_grab` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_LIQUIDITY_GRAB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `stoch_trend_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `three_bar_reversal` | `EUR_USD` | 12 | 7 | 5 | -0.525 | 58.3% | 32.0%-80.7% | 0.66 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `GBP_USD` | 8 | 2 | 6 | -2.775 | 25.0% | 7.1%-59.1% | 0.35 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `USD_JPY` | 10 | 6 | 4 | +1.240 | 60.0% | 31.3%-83.2% | 1.98 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_range_breakout_up` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_RANGE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `EUR_USD` | 5 | 3 | 2 | +1.200 | 60.0% | 23.1%-88.2% | 2.15 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `GBP_USD` | 2 | 1 | 1 | +0.950 | 50.0% | 9.5%-90.5% | 7.33 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trend_rebound` | `USD_JPY` | 15 | 5 | 10 | -1.093 | 33.3% | 15.2%-58.3% | 0.35 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `EUR_GBP` | 25 | 10 | 15 | -2.544 | 40.0% | 23.4%-59.3% | 0.23 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `EUR_USD` | 16 | 12 | 4 | -0.169 | 75.0% | 50.5%-89.8% | 0.94 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `GBP_USD` | 14 | 10 | 4 | -2.736 | 71.4% | 45.4%-88.3% | 0.27 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `turtle_soup` | `GBP_USD` | 6 | 6 | 0 | +1.467 | 100.0% | 61.0%-100.0% | n/a | `TURTLE_SOUP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tvsm` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TVSM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `v_reversal` | `USD_JPY` | 3 | 1 | 2 | -0.967 | 33.3% | 6.1%-79.2% | 0.63 | `V_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vbp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `VBP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `GBP_JPY` | 5 | 4 | 1 | +6.720 | 80.0% | 37.6%-96.4% | 4.65 | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `USD_JPY` | 2 | 2 | 0 | +1.550 | 100.0% | 34.2%-100.0% | n/a | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_momentum_scalp` | `GBP_USD` | 54 | 31 | 23 | +0.554 | 57.4% | 44.2%-69.7% | 1.24 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `vol_momentum_scalp` | `USD_JPY` | 70 | 25 | 45 | -1.337 | 35.7% | 25.5%-47.4% | 0.40 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `EUR_USD` | 21 | 6 | 15 | -1.657 | 28.6% | 13.8%-50.0% | 0.28 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `GBP_USD` | 18 | 5 | 13 | -1.861 | 27.8% | 12.5%-50.9% | 0.35 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `USD_JPY` | 13 | 6 | 7 | -0.131 | 46.2% | 23.2%-70.9% | 0.93 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_GBP` | 5 | 4 | 1 | +2.140 | 80.0% | 37.6%-96.4% | 3.06 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_JPY` | 1 | 1 | 0 | +7.100 | 100.0% | 20.7%-100.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_USD` | 1 | 0 | 1 | -5.400 | 0.0% | 0.0%-79.3% | 0.00 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_JPY` | 3 | 2 | 1 | -5.167 | 66.7% | 20.8%-93.9% | 0.23 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_USD` | 2 | 1 | 1 | -2.600 | 50.0% | 9.5%-90.5% | 0.31 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `USD_JPY` | 3 | 3 | 0 | +1.333 | 100.0% | 43.8%-100.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `AUD_JPY` | 4 | 0 | 4 | -6.425 | 0.0% | 0.0%-49.0% | 0.00 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_GBP` | 1 | 0 | 1 | -0.300 | 0.0% | 0.0%-79.3% | 0.00 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `EUR_JPY` | 17 | 9 | 8 | -2.741 | 52.9% | 31.0%-73.8% | 0.45 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_USD` | 8 | 6 | 2 | +1.363 | 75.0% | 40.9%-92.9% | 1.48 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `GBP_JPY` | 13 | 9 | 4 | -1.015 | 69.2% | 42.4%-87.3% | 0.77 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `GBP_USD` | 11 | 5 | 6 | -4.918 | 45.5% | 21.3%-72.0% | 0.13 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `USD_JPY` | 11 | 5 | 6 | -3.864 | 45.5% | 21.3%-72.0% | 0.13 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `EUR_USD` | 37 | 21 | 16 | -2.070 | 56.8% | 40.9%-71.3% | 0.40 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `xs_momentum` | `GBP_USD` | 51 | 35 | 16 | +0.300 | 68.6% | 55.0%-79.7% | 1.09 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `USD_JPY` | 36 | 22 | 14 | -0.103 | 61.1% | 44.9%-75.2% | 0.97 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
