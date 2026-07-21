# SHADOW_PROMOTE R2 Alert - 2026-07-21T08:24:23.163829+00:00

- Source: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=2000`
- Lookback: `30d`
- Filters: `is_shadow=1`, `pnl_pips IS NOT NULL`, `dedup_violation != 1`, XAU instruments excluded
- Gate: `N >= 10 and EV < 0` -> WARN; `N >= 30 and EV < 0` -> CRITICAL
- Mode: read-only; no env vars, strategy code, tier-master, or DB writes

## Summary

- Promoted strategies: 65
- Cells: 130
- OK: 96
- WARN: 24
- CRITICAL: 10

## WARN / CRITICAL

| Severity | Strategy | Instrument | N | EV | WR | Wilson lower | PF |
|---|---|---|---:|---:|---:|---:|---:|
| **WARN** | `donchian_momentum_breakout` | `AUD_USD` | 10 | -6.440 | 40.0% | 16.8% | 0.23 |
| **WARN** | `dt_bb_rsi_mr` | `GBP_USD` | 17 | -5.447 | 23.5% | 9.6% | 0.08 |
| **WARN** | `dt_sr_channel_reversal` | `AUD_JPY` | 15 | -0.300 | 53.3% | 30.1% | 0.90 |
| **WARN** | `dt_sr_channel_reversal` | `EUR_JPY` | 20 | -1.410 | 65.0% | 43.3% | 0.53 |
| **WARN** | `dt_sr_channel_reversal` | `EUR_USD` | 23 | -1.409 | 43.5% | 25.6% | 0.40 |
| **WARN** | `dt_sr_channel_reversal` | `GBP_JPY` | 19 | -0.279 | 68.4% | 46.0% | 0.91 |
| **WARN** | `dt_sr_channel_reversal` | `GBP_USD` | 28 | -0.943 | 50.0% | 32.6% | 0.70 |
| **WARN** | `dt_sr_channel_reversal` | `USD_JPY` | 16 | -0.988 | 43.8% | 23.1% | 0.75 |
| **CRITICAL** | `engulfing_bb` | `EUR_USD` | 86 | -0.737 | 44.2% | 34.2% | 0.63 |
| **CRITICAL** | `engulfing_bb` | `GBP_USD` | 30 | -1.490 | 43.3% | 27.4% | 0.40 |
| **WARN** | `lin_reg_channel` | `EUR_USD` | 20 | -1.485 | 50.0% | 29.9% | 0.47 |
| **WARN** | `london_breakout` | `EUR_USD` | 15 | -1.747 | 33.3% | 15.2% | 0.30 |
| **WARN** | `london_breakout` | `GBP_USD` | 18 | -2.906 | 38.9% | 20.3% | 0.21 |
| **CRITICAL** | `ma_regime_switch` | `USD_JPY` | 69 | -1.367 | 37.7% | 27.2% | 0.39 |
| **WARN** | `ob_retest` | `EUR_USD` | 13 | -1.100 | 69.2% | 42.4% | 0.66 |
| **WARN** | `squeeze_release_momentum` | `GBP_USD` | 21 | -1.386 | 61.9% | 40.9% | 0.58 |
| **WARN** | `sr_break_retest` | `AUD_JPY` | 17 | -2.800 | 52.9% | 31.0% | 0.31 |
| **CRITICAL** | `sr_break_retest` | `EUR_JPY` | 34 | -1.876 | 52.9% | 36.7% | 0.54 |
| **CRITICAL** | `sr_break_retest` | `GBP_JPY` | 31 | -2.265 | 74.2% | 56.8% | 0.48 |
| **CRITICAL** | `sr_break_retest` | `GBP_USD` | 33 | -1.118 | 57.6% | 40.8% | 0.64 |
| **CRITICAL** | `sr_break_retest` | `USD_JPY` | 32 | -3.284 | 43.8% | 28.2% | 0.26 |
| **WARN** | `trend_rebound` | `USD_JPY` | 15 | -1.360 | 33.3% | 15.2% | 0.32 |
| **WARN** | `trendline_sweep` | `EUR_GBP` | 29 | -1.545 | 51.7% | 34.4% | 0.39 |
| **WARN** | `trendline_sweep` | `EUR_USD` | 16 | -0.294 | 75.0% | 50.5% | 0.87 |
| **WARN** | `trendline_sweep` | `GBP_USD` | 11 | -2.564 | 63.6% | 35.4% | 0.27 |
| **CRITICAL** | `vol_momentum_scalp` | `USD_JPY` | 65 | -1.117 | 40.0% | 29.0% | 0.53 |
| **WARN** | `vol_surge_detector` | `EUR_USD` | 24 | -2.367 | 25.0% | 12.0% | 0.14 |
| **WARN** | `vol_surge_detector` | `GBP_USD` | 13 | -1.100 | 38.5% | 17.7% | 0.59 |
| **WARN** | `vol_surge_detector` | `USD_JPY` | 13 | -0.523 | 46.2% | 23.2% | 0.73 |
| **WARN** | `wick_imbalance_reversion` | `EUR_JPY` | 18 | -0.656 | 66.7% | 43.7% | 0.80 |
| **WARN** | `wick_imbalance_reversion` | `USD_JPY` | 15 | -3.593 | 40.0% | 19.8% | 0.12 |
| **CRITICAL** | `xs_momentum` | `EUR_USD` | 38 | -2.382 | 55.3% | 39.7% | 0.36 |
| **CRITICAL** | `xs_momentum` | `GBP_USD` | 39 | -1.359 | 59.0% | 43.4% | 0.74 |
| **WARN** | `xs_momentum` | `USD_JPY` | 28 | -2.764 | 57.1% | 39.1% | 0.30 |

## R2 Demote Manual Action

For each CRITICAL cell, manually verify and then remove the relevant Render env var:

- `engulfing_bb` x `EUR_USD`: remove `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE`
- `engulfing_bb` x `GBP_USD`: remove `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE`
- `ma_regime_switch` x `USD_JPY`: remove `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `EUR_JPY`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `GBP_JPY`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `GBP_USD`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `USD_JPY`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `vol_momentum_scalp` x `USD_JPY`: remove `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`, `VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE`
- `xs_momentum` x `EUR_USD`: remove `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`
- `xs_momentum` x `GBP_USD`: remove `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`

Code review locations if manual demotion is chosen:
- `strategies/daytrade/__init__.py` `split_shadow_always` / `SHADOW_ALWAYS_STRATEGIES`
- `strategies/hourly/__init__.py` `split_shadow_always`
- `strategies/scalp/__init__.py` `split_shadow_always`

## Apply Demote Suggestion

- Registry: `/home/runner/work/fx-ai-trader/fx-ai-trader/modules/shadow_demote_registry.py`
- Missing CRITICAL cells: `10`
- Add `('engulfing_bb', 'EUR_USD')`
- Add `('engulfing_bb', 'GBP_USD')`
- Add `('ma_regime_switch', 'USD_JPY')`
- Add `('sr_break_retest', 'EUR_JPY')`
- Add `('sr_break_retest', 'GBP_JPY')`
- Add `('sr_break_retest', 'GBP_USD')`
- Add `('sr_break_retest', 'USD_JPY')`
- Add `('vol_momentum_scalp', 'USD_JPY')`
- Add `('xs_momentum', 'EUR_USD')`
- Add `('xs_momentum', 'GBP_USD')`

## All Cells

| Severity | Strategy | Instrument | N | Wins | Losses | EV | WR | Wilson 95% | PF | Env |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| OK | `adx_trend_continuation` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ADX_TREND_CONTINUATION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `asia_range_fade_v1` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ASIA_RANGE_FADE_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `atr_regime_break` | `GBP_JPY` | 1 | 1 | 0 | +2.000 | 100.0% | 20.7%-100.0% | n/a | `ALPHA_ATR_REGIME_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_rsi_ema_aligned` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `BB_RSI_EMA_ALIGNED_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `confluence_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CONFLUENCE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `cpd_divergence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CPD_DIVERGENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `AUD_JPY` | 11 | 9 | 2 | +1.673 | 81.8% | 52.3%-94.9% | 1.43 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `donchian_momentum_breakout` | `AUD_USD` | 10 | 4 | 6 | -6.440 | 40.0% | 16.8%-68.7% | 0.23 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `EUR_USD` | 2 | 0 | 2 | -24.100 | 0.0% | 0.0%-65.8% | 0.00 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `NZD_JPY` | 1 | 1 | 0 | +2.900 | 100.0% | 20.7%-100.0% | n/a | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `NZD_USD` | 15 | 12 | 3 | +1.040 | 80.0% | 54.8%-93.0% | 1.31 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `USD_JPY` | 7 | 3 | 4 | -9.443 | 42.9% | 15.8%-75.0% | 0.22 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `EUR_USD` | 6 | 4 | 2 | +2.067 | 66.7% | 30.0%-90.3% | 2.57 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_bb_rsi_mr` | `GBP_USD` | 17 | 4 | 13 | -5.447 | 23.5% | 9.6%-47.3% | 0.08 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `USD_JPY` | 4 | 2 | 2 | -0.900 | 50.0% | 15.0%-85.0% | 0.74 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `AUD_JPY` | 15 | 8 | 7 | -0.300 | 53.3% | 30.1%-75.2% | 0.90 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `EUR_GBP` | 9 | 6 | 3 | +0.789 | 66.7% | 35.4%-87.9% | 1.52 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_JPY` | 20 | 13 | 7 | -1.410 | 65.0% | 43.3%-81.9% | 0.53 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_USD` | 23 | 10 | 13 | -1.409 | 43.5% | 25.6%-63.2% | 0.40 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `GBP_JPY` | 19 | 13 | 6 | -0.279 | 68.4% | 46.0%-84.6% | 0.91 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `GBP_USD` | 28 | 14 | 14 | -0.943 | 50.0% | 32.6%-67.4% | 0.70 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `USD_JPY` | 16 | 7 | 9 | -0.988 | 43.8% | 23.1%-66.8% | 0.75 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema200_trend_reversal` | `USD_JPY` | 22 | 13 | 9 | +0.518 | 59.1% | 38.7%-76.7% | 1.19 | `EMA200_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`<br>`EMA200_TREND_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_ribbon_ride` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_RIBBON_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_trend_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `engulfing_bb` | `EUR_USD` | 86 | 38 | 48 | -0.737 | 44.2% | 34.2%-54.7% | 0.63 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `engulfing_bb` | `GBP_USD` | 30 | 13 | 17 | -1.490 | 43.3% | 27.4%-60.8% | 0.40 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `engulfing_bb` | `USD_CHF` | 1 | 1 | 0 | +1.600 | 100.0% | 20.7%-100.0% | n/a | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_pips_hunter` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_PIPS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_trend_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_TREND_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_vol_break` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_VOL_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `EUR_JPY` | 2 | 1 | 1 | +0.200 | 50.0% | 9.5%-90.5% | 1.04 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_JPY` | 1 | 1 | 0 | +2.000 | 100.0% | 20.7%-100.0% | n/a | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_USD` | 5 | 5 | 0 | +3.140 | 100.0% | 56.6%-100.0% | n/a | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `USD_JPY` | 1 | 1 | 0 | +0.600 | 100.0% | 20.7%-100.0% | n/a | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `GBP_USD` | 3 | 1 | 2 | -7.333 | 33.3% | 6.1%-79.2% | 0.08 | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `intraday_seasonality` | `AUD_JPY` | 1 | 1 | 0 | +1.600 | 100.0% | 20.7%-100.0% | n/a | `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `jpy_basket_trend` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `JPY_BASKET_TREND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `keltner_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `lin_reg_channel` | `EUR_USD` | 20 | 10 | 10 | -1.485 | 50.0% | 29.9%-70.1% | 0.47 | `LIN_REG_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `london_breakout` | `EUR_USD` | 15 | 5 | 10 | -1.747 | 33.3% | 15.2%-58.3% | 0.30 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `london_breakout` | `GBP_USD` | 18 | 7 | 11 | -2.906 | 38.9% | 20.3%-61.4% | 0.21 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_breakout` | `USD_CHF` | 8 | 3 | 5 | -0.263 | 37.5% | 13.7%-69.4% | 0.76 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_breakout` | `USD_JPY` | 3 | 1 | 2 | -2.300 | 33.3% | 6.1%-79.2% | 0.21 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_ny_swing` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_NY_SWING_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `EUR_USD` | 3 | 1 | 2 | -1.500 | 33.3% | 6.1%-79.2% | 0.75 | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `GBP_USD` | 2 | 2 | 0 | +8.800 | 100.0% | 34.2%-100.0% | n/a | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_shrapnel` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_SHRAPNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_mr_hybrid` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_MR_HYBRID_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `ma_regime_switch` | `USD_JPY` | 69 | 26 | 43 | -1.367 | 37.7% | 27.2%-49.5% | 0.39 | `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_trend_perfect` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_TREND_PERFECT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `GBP_USD` | 1 | 0 | 1 | -0.100 | 0.0% | 0.0%-79.3% | 0.00 | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `USD_JPY` | 3 | 1 | 2 | +0.233 | 33.3% | 6.1%-79.2% | 1.14 | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_regime_range_cascade_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `USD_JPY` | 3 | 1 | 2 | -0.733 | 33.3% | 6.1%-79.2% | 0.66 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `AUD_JPY` | 3 | 1 | 2 | -2.433 | 33.3% | 6.1%-79.2% | 0.25 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `EUR_JPY` | 1 | 0 | 1 | -16.000 | 0.0% | 0.0%-79.3% | 0.00 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `ob_retest` | `EUR_USD` | 13 | 9 | 4 | -1.100 | 69.2% | 42.4%-87.3% | 0.66 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `GBP_JPY` | 3 | 3 | 0 | +2.800 | 100.0% | 43.8%-100.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `GBP_USD` | 4 | 4 | 0 | +1.650 | 100.0% | 51.0%-100.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ofi_mr` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `OFI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `EUR_USD` | 4 | 2 | 2 | -2.275 | 50.0% | 15.0%-85.0% | 0.08 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `GBP_USD` | 3 | 2 | 1 | +0.100 | 66.7% | 20.8%-93.9% | 1.03 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `USD_JPY` | 2 | 2 | 0 | +15.750 | 100.0% | 34.2%-100.0% | n/a | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `post_news_vol` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `AUD_JPY` | 1 | 1 | 0 | +2.000 | 100.0% | 20.7%-100.0% | n/a | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `EUR_JPY` | 1 | 0 | 1 | -17.200 | 0.0% | 0.0%-79.3% | 0.00 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `GBP_JPY` | 1 | 1 | 0 | +2.900 | 100.0% | 20.7%-100.0% | n/a | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `GBP_USD` | 1 | 1 | 0 | +13.100 | 100.0% | 20.7%-100.0% | n/a | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `USD_JPY` | 1 | 1 | 0 | +0.300 | 100.0% | 20.7%-100.0% | n/a | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `session_vol_expansion` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SESSION_VOL_EXPANSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `squeeze_release_momentum` | `EUR_USD` | 22 | 14 | 8 | +0.191 | 63.6% | 43.0%-80.3% | 1.09 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `squeeze_release_momentum` | `GBP_USD` | 21 | 13 | 8 | -1.386 | 61.9% | 40.9%-79.2% | 0.58 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `EUR_JPY` | 15 | 14 | 1 | +2.440 | 93.3% | 70.2%-98.8% | 7.31 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `EUR_USD` | 5 | 3 | 2 | -2.380 | 60.0% | 23.1%-88.2% | 0.26 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_JPY` | 8 | 2 | 6 | -15.562 | 25.0% | 7.1%-59.1% | 0.05 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_USD` | 2 | 2 | 0 | +2.150 | 100.0% | 34.2%-100.0% | n/a | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `USD_JPY` | 4 | 4 | 0 | +1.525 | 100.0% | 51.0%-100.0% | n/a | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_break_retest` | `AUD_JPY` | 17 | 9 | 8 | -2.800 | 52.9% | 31.0%-73.8% | 0.31 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `EUR_JPY` | 34 | 18 | 16 | -1.876 | 52.9% | 36.7%-68.5% | 0.54 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `GBP_JPY` | 31 | 23 | 8 | -2.265 | 74.2% | 56.8%-86.3% | 0.48 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `GBP_USD` | 33 | 19 | 14 | -1.118 | 57.6% | 40.8%-72.8% | 0.64 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `USD_JPY` | 32 | 14 | 18 | -3.284 | 43.8% | 28.2%-60.7% | 0.26 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_channel_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_fib_confluence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_liquidity_grab` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_LIQUIDITY_GRAB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `stoch_trend_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `EUR_USD` | 8 | 3 | 5 | -1.863 | 37.5% | 13.7%-69.4% | 0.21 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `GBP_USD` | 8 | 2 | 6 | -2.650 | 25.0% | 7.1%-59.1% | 0.36 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `USD_JPY` | 6 | 3 | 3 | +1.250 | 50.0% | 18.8%-81.2% | 1.78 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_range_breakout_up` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_RANGE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `EUR_USD` | 6 | 3 | 3 | +0.500 | 50.0% | 18.8%-81.2% | 1.37 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `GBP_USD` | 4 | 1 | 3 | -2.125 | 25.0% | 4.6%-69.9% | 0.21 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trend_rebound` | `USD_JPY` | 15 | 5 | 10 | -1.360 | 33.3% | 15.2%-58.3% | 0.32 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `EUR_GBP` | 29 | 15 | 14 | -1.545 | 51.7% | 34.4%-68.6% | 0.39 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `EUR_USD` | 16 | 12 | 4 | -0.294 | 75.0% | 50.5%-89.8% | 0.87 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `GBP_USD` | 11 | 7 | 4 | -2.564 | 63.6% | 35.4%-84.8% | 0.27 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `turtle_soup` | `EUR_GBP` | 1 | 1 | 0 | +1.500 | 100.0% | 20.7%-100.0% | n/a | `TURTLE_SOUP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `turtle_soup` | `GBP_USD` | 6 | 5 | 1 | -1.150 | 83.3% | 43.6%-97.0% | 0.49 | `TURTLE_SOUP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tvsm` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TVSM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `v_reversal` | `USD_JPY` | 3 | 1 | 2 | -0.333 | 33.3% | 6.1%-79.2% | 0.83 | `V_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vbp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `VBP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `GBP_JPY` | 3 | 3 | 0 | +6.533 | 100.0% | 43.8%-100.0% | n/a | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `USD_JPY` | 3 | 2 | 1 | -3.233 | 66.7% | 20.8%-93.9% | 0.24 | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_momentum_scalp` | `GBP_USD` | 34 | 19 | 15 | +1.153 | 55.9% | 39.5%-71.1% | 1.46 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `vol_momentum_scalp` | `USD_JPY` | 65 | 26 | 39 | -1.117 | 40.0% | 29.0%-52.1% | 0.53 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `EUR_USD` | 24 | 6 | 18 | -2.367 | 25.0% | 12.0%-44.9% | 0.14 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `GBP_USD` | 13 | 5 | 8 | -1.100 | 38.5% | 17.7%-64.5% | 0.59 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `USD_CHF` | 1 | 1 | 0 | +2.000 | 100.0% | 20.7%-100.0% | n/a | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `USD_JPY` | 13 | 6 | 7 | -0.523 | 46.2% | 23.2%-70.9% | 0.73 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_GBP` | 6 | 3 | 3 | -0.500 | 50.0% | 18.8%-81.2% | 0.82 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_JPY` | 1 | 1 | 0 | +7.100 | 100.0% | 20.7%-100.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_USD` | 1 | 0 | 1 | -5.400 | 0.0% | 0.0%-79.3% | 0.00 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_JPY` | 4 | 3 | 1 | -3.375 | 75.0% | 30.1%-95.4% | 0.33 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_USD` | 3 | 2 | 1 | +0.533 | 66.7% | 20.8%-93.9% | 1.21 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `USD_JPY` | 1 | 1 | 0 | +0.600 | 100.0% | 20.7%-100.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_GBP` | 1 | 0 | 1 | -0.300 | 0.0% | 0.0%-79.3% | 0.00 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `EUR_JPY` | 18 | 12 | 6 | -0.656 | 66.7% | 43.7%-83.7% | 0.80 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_USD` | 6 | 5 | 1 | +3.700 | 83.3% | 43.6%-97.0% | 3.34 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `GBP_JPY` | 22 | 17 | 5 | +0.755 | 77.3% | 56.6%-89.9% | 1.23 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `GBP_USD` | 8 | 3 | 5 | -6.925 | 37.5% | 13.7%-69.4% | 0.07 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `USD_JPY` | 15 | 6 | 9 | -3.593 | 40.0% | 19.8%-64.3% | 0.12 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `EUR_USD` | 38 | 21 | 17 | -2.382 | 55.3% | 39.7%-69.9% | 0.36 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `GBP_USD` | 39 | 23 | 16 | -1.359 | 59.0% | 43.4%-72.9% | 0.74 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `xs_momentum` | `USD_JPY` | 28 | 16 | 12 | -2.764 | 57.1% | 39.1%-73.5% | 0.30 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
