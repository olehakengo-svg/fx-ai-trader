# SHADOW_PROMOTE R2 Alert - 2026-08-19T18:31:49.815969+00:00

- Source: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=2000`
- Lookback: `30d`
- Filters: `is_shadow=1`, `pnl_pips IS NOT NULL`, `dedup_violation != 1`, XAU instruments excluded
- Gate: `N >= 10 and EV < 0` -> WARN; `N >= 30 and EV < 0` -> CRITICAL
- Mode: read-only; no env vars, strategy code, tier-master, or DB writes

## Summary

- Promoted strategies: 65
- Cells: 137
- OK: 104
- WARN: 24
- CRITICAL: 9

## WARN / CRITICAL

| Severity | Strategy | Instrument | N | EV | WR | Wilson lower | PF |
|---|---|---|---:|---:|---:|---:|---:|
| **WARN** | `dt_bb_rsi_mr` | `USD_JPY` | 17 | -0.482 | 58.8% | 36.0% | 0.84 |
| **WARN** | `dt_sr_channel_reversal` | `AUD_JPY` | 15 | -7.273 | 26.7% | 10.9% | 0.11 |
| **WARN** | `dt_sr_channel_reversal` | `EUR_GBP` | 17 | -2.706 | 17.6% | 6.2% | 0.11 |
| **WARN** | `dt_sr_channel_reversal` | `EUR_JPY` | 20 | -1.665 | 40.0% | 21.9% | 0.68 |
| **WARN** | `dt_sr_channel_reversal` | `EUR_USD` | 25 | -0.268 | 44.0% | 26.7% | 0.90 |
| **WARN** | `dt_sr_channel_reversal` | `GBP_JPY` | 23 | -3.917 | 52.2% | 33.0% | 0.38 |
| **WARN** | `dt_sr_channel_reversal` | `USD_JPY` | 29 | -0.724 | 51.7% | 34.4% | 0.79 |
| **CRITICAL** | `engulfing_bb` | `EUR_USD` | 46 | -1.980 | 19.6% | 10.7% | 0.16 |
| **WARN** | `engulfing_bb` | `GBP_USD` | 19 | -1.042 | 26.3% | 11.8% | 0.66 |
| **WARN** | `lin_reg_channel` | `EUR_USD` | 10 | -2.690 | 30.0% | 10.8% | 0.35 |
| **WARN** | `london_breakout` | `EUR_USD` | 18 | -0.256 | 27.8% | 12.5% | 0.80 |
| **WARN** | `london_breakout` | `GBP_USD` | 22 | -2.664 | 31.8% | 16.4% | 0.15 |
| **CRITICAL** | `ma_regime_switch` | `USD_JPY` | 32 | -1.313 | 46.9% | 30.9% | 0.66 |
| **WARN** | `ob_retest` | `USD_JPY` | 19 | -2.147 | 47.4% | 27.3% | 0.67 |
| **WARN** | `squeeze_release_momentum` | `EUR_USD` | 12 | -3.408 | 25.0% | 8.9% | 0.26 |
| **CRITICAL** | `sr_anti_hunt_bounce` | `EUR_JPY` | 31 | -0.897 | 48.4% | 32.0% | 0.76 |
| **WARN** | `sr_anti_hunt_bounce` | `GBP_JPY` | 17 | -1.594 | 58.8% | 36.0% | 0.62 |
| **CRITICAL** | `sr_break_retest` | `AUD_JPY` | 30 | -3.303 | 36.7% | 21.9% | 0.40 |
| **WARN** | `sr_break_retest` | `EUR_JPY` | 18 | -3.817 | 55.6% | 33.7% | 0.45 |
| **WARN** | `sr_break_retest` | `GBP_JPY` | 19 | -6.447 | 42.1% | 23.1% | 0.25 |
| **WARN** | `sr_break_retest` | `GBP_USD` | 11 | -1.882 | 54.5% | 28.0% | 0.43 |
| **CRITICAL** | `sr_break_retest` | `USD_JPY` | 53 | -1.798 | 50.9% | 37.9% | 0.62 |
| **WARN** | `trendline_sweep` | `GBP_USD` | 21 | -3.762 | 57.1% | 36.5% | 0.15 |
| **WARN** | `vol_momentum_scalp` | `GBP_USD` | 18 | -3.767 | 38.9% | 20.3% | 0.29 |
| **CRITICAL** | `vol_momentum_scalp` | `USD_JPY` | 41 | -1.732 | 34.1% | 21.6% | 0.59 |
| **WARN** | `vol_surge_detector` | `EUR_USD` | 21 | -0.895 | 23.8% | 10.6% | 0.54 |
| **WARN** | `vol_surge_detector` | `USD_JPY` | 12 | -0.900 | 33.3% | 13.8% | 0.70 |
| **CRITICAL** | `wick_imbalance_reversion` | `AUD_JPY` | 33 | -1.115 | 45.5% | 29.8% | 0.72 |
| **WARN** | `wick_imbalance_reversion` | `EUR_JPY` | 25 | -1.696 | 52.0% | 33.5% | 0.67 |
| **WARN** | `wick_imbalance_reversion` | `GBP_USD` | 21 | -3.310 | 33.3% | 17.2% | 0.28 |
| **WARN** | `xs_momentum` | `EUR_USD` | 18 | -2.456 | 55.6% | 33.7% | 0.39 |
| **CRITICAL** | `xs_momentum` | `GBP_USD` | 30 | -1.497 | 60.0% | 42.3% | 0.63 |
| **CRITICAL** | `xs_momentum` | `USD_JPY` | 49 | -3.112 | 53.1% | 39.4% | 0.58 |

## R2 Demote Manual Action

For each CRITICAL cell, manually verify and then remove the relevant Render env var:

- `engulfing_bb` x `EUR_USD`: remove `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE`
- `ma_regime_switch` x `USD_JPY`: remove `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_anti_hunt_bounce` x `EUR_JPY`: remove `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `AUD_JPY`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `USD_JPY`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `vol_momentum_scalp` x `USD_JPY`: remove `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`, `VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE`
- `wick_imbalance_reversion` x `AUD_JPY`: remove `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`, `WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE`
- `xs_momentum` x `GBP_USD`: remove `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`
- `xs_momentum` x `USD_JPY`: remove `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`

Code review locations if manual demotion is chosen:
- `strategies/daytrade/__init__.py` `split_shadow_always` / `SHADOW_ALWAYS_STRATEGIES`
- `strategies/hourly/__init__.py` `split_shadow_always`
- `strategies/scalp/__init__.py` `split_shadow_always`

## Apply Demote Suggestion

- Registry: `/home/runner/work/fx-ai-trader/fx-ai-trader/modules/shadow_demote_registry.py`
- Missing CRITICAL cells: `9`
- Add `('engulfing_bb', 'EUR_USD')`
- Add `('ma_regime_switch', 'USD_JPY')`
- Add `('sr_anti_hunt_bounce', 'EUR_JPY')`
- Add `('sr_break_retest', 'AUD_JPY')`
- Add `('sr_break_retest', 'USD_JPY')`
- Add `('vol_momentum_scalp', 'USD_JPY')`
- Add `('wick_imbalance_reversion', 'AUD_JPY')`
- Add `('xs_momentum', 'GBP_USD')`
- Add `('xs_momentum', 'USD_JPY')`

## All Cells

| Severity | Strategy | Instrument | N | Wins | Losses | EV | WR | Wilson 95% | PF | Env |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| OK | `adx_trend_continuation` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ADX_TREND_CONTINUATION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `asia_range_fade_v1` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ASIA_RANGE_FADE_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `atr_regime_break` | `AUD_JPY` | 1 | 1 | 0 | +2.500 | 100.0% | 20.7%-100.0% | n/a | `ALPHA_ATR_REGIME_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `atr_regime_break` | `EUR_JPY` | 1 | 1 | 0 | +1.400 | 100.0% | 20.7%-100.0% | n/a | `ALPHA_ATR_REGIME_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `atr_regime_break` | `GBP_JPY` | 3 | 3 | 0 | +3.700 | 100.0% | 43.8%-100.0% | n/a | `ALPHA_ATR_REGIME_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `atr_regime_break` | `GBP_USD` | 1 | 0 | 1 | -12.400 | 0.0% | 0.0%-79.3% | 0.00 | `ALPHA_ATR_REGIME_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `atr_regime_break` | `USD_JPY` | 1 | 1 | 0 | +1.900 | 100.0% | 20.7%-100.0% | n/a | `ALPHA_ATR_REGIME_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_rsi_ema_aligned` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `BB_RSI_EMA_ALIGNED_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `confluence_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CONFLUENCE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `cpd_divergence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CPD_DIVERGENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `AUD_JPY` | 9 | 7 | 2 | +0.578 | 77.8% | 45.3%-93.7% | 1.12 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `AUD_USD` | 8 | 2 | 6 | -7.275 | 25.0% | 7.1%-59.1% | 0.14 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `EUR_USD` | 9 | 8 | 1 | +3.489 | 88.9% | 56.5%-98.0% | 3.03 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `NZD_JPY` | 3 | 2 | 1 | +0.867 | 66.7% | 20.8%-93.9% | 1.93 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `NZD_USD` | 10 | 7 | 3 | +0.470 | 70.0% | 39.7%-89.2% | 1.09 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `USD_JPY` | 8 | 3 | 5 | -7.850 | 37.5% | 13.7%-69.4% | 0.25 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `EUR_USD` | 4 | 2 | 2 | +1.225 | 50.0% | 15.0%-85.0% | 1.34 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `GBP_USD` | 13 | 9 | 4 | +0.208 | 69.2% | 42.4%-87.3% | 1.10 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_bb_rsi_mr` | `USD_JPY` | 17 | 10 | 7 | -0.482 | 58.8% | 36.0%-78.4% | 0.84 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `AUD_JPY` | 15 | 4 | 11 | -7.273 | 26.7% | 10.9%-52.0% | 0.11 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_GBP` | 17 | 3 | 14 | -2.706 | 17.6% | 6.2%-41.0% | 0.11 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_JPY` | 20 | 8 | 12 | -1.665 | 40.0% | 21.9%-61.3% | 0.68 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_USD` | 25 | 11 | 14 | -0.268 | 44.0% | 26.7%-62.9% | 0.90 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `GBP_JPY` | 23 | 12 | 11 | -3.917 | 52.2% | 33.0%-70.8% | 0.38 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `GBP_USD` | 27 | 15 | 12 | +0.993 | 55.6% | 37.3%-72.4% | 1.39 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `USD_JPY` | 29 | 15 | 14 | -0.724 | 51.7% | 34.4%-68.6% | 0.79 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema200_trend_reversal` | `USD_JPY` | 8 | 5 | 3 | -2.350 | 62.5% | 30.6%-86.3% | 0.43 | `EMA200_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`<br>`EMA200_TREND_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_ribbon_ride` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_RIBBON_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_trend_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `engulfing_bb` | `EUR_USD` | 46 | 9 | 37 | -1.980 | 19.6% | 10.7%-33.2% | 0.16 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `engulfing_bb` | `GBP_USD` | 19 | 5 | 14 | -1.042 | 26.3% | 11.8%-48.8% | 0.66 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_pips_hunter` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_PIPS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_trend_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_TREND_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_vol_break` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_VOL_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `AUD_JPY` | 3 | 2 | 1 | +1.367 | 66.7% | 20.8%-93.9% | 1.63 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `EUR_JPY` | 4 | 3 | 1 | +1.250 | 75.0% | 30.1%-95.4% | 1.37 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `EUR_USD` | 1 | 0 | 1 | -5.000 | 0.0% | 0.0%-79.3% | 0.00 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_USD` | 3 | 3 | 0 | +0.800 | 100.0% | 43.8%-100.0% | n/a | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `EUR_GBP` | 4 | 2 | 2 | -1.500 | 50.0% | 15.0%-85.0% | 0.34 | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `intraday_seasonality` | `EUR_GBP` | 2 | 0 | 2 | -2.950 | 0.0% | 0.0%-65.8% | 0.00 | `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `intraday_seasonality` | `GBP_USD` | 2 | 1 | 1 | -1.300 | 50.0% | 9.5%-90.5% | 0.33 | `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `jpy_basket_trend` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `JPY_BASKET_TREND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `keltner_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `lin_reg_channel` | `EUR_USD` | 10 | 3 | 7 | -2.690 | 30.0% | 10.8%-60.3% | 0.35 | `LIN_REG_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `london_breakout` | `EUR_USD` | 18 | 5 | 13 | -0.256 | 27.8% | 12.5%-50.9% | 0.80 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `london_breakout` | `GBP_USD` | 22 | 7 | 15 | -2.664 | 31.8% | 16.4%-52.7% | 0.15 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_breakout` | `USD_JPY` | 5 | 1 | 4 | -6.860 | 20.0% | 3.6%-62.4% | 0.19 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_ny_swing` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_NY_SWING_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `EUR_USD` | 4 | 2 | 2 | +0.375 | 50.0% | 15.0%-85.0% | 1.08 | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `GBP_USD` | 2 | 1 | 1 | -3.700 | 50.0% | 9.5%-90.5% | 0.13 | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_shrapnel` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_SHRAPNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_mr_hybrid` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_MR_HYBRID_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `ma_regime_switch` | `USD_JPY` | 32 | 15 | 17 | -1.313 | 46.9% | 30.9%-63.6% | 0.66 | `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_trend_perfect` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_TREND_PERFECT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `EUR_USD` | 1 | 1 | 0 | +5.800 | 100.0% | 20.7%-100.0% | n/a | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `GBP_USD` | 3 | 2 | 1 | +0.767 | 66.7% | 20.8%-93.9% | 1.53 | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `USD_JPY` | 2 | 2 | 0 | +2.350 | 100.0% | 34.2%-100.0% | n/a | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `EUR_USD` | 3 | 1 | 2 | -1.233 | 33.3% | 6.1%-79.2% | 0.16 | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `USD_JPY` | 1 | 0 | 1 | -6.600 | 0.0% | 0.0%-79.3% | 0.00 | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_regime_range_cascade_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `EUR_USD` | 3 | 3 | 0 | +2.167 | 100.0% | 43.8%-100.0% | n/a | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `GBP_USD` | 4 | 0 | 4 | -2.925 | 0.0% | 0.0%-49.0% | 0.00 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `USD_JPY` | 2 | 2 | 0 | +9.550 | 100.0% | 34.2%-100.0% | n/a | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `AUD_JPY` | 9 | 7 | 2 | +6.933 | 77.8% | 45.3%-93.7% | 4.12 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `EUR_JPY` | 3 | 2 | 1 | -9.267 | 66.7% | 20.8%-93.9% | 0.36 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `GBP_JPY` | 7 | 6 | 1 | -1.829 | 85.7% | 48.7%-97.4% | 0.70 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `ob_retest` | `USD_JPY` | 19 | 9 | 10 | -2.147 | 47.4% | 27.3%-68.3% | 0.67 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ofi_mr` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `OFI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `EUR_USD` | 3 | 1 | 2 | -4.800 | 33.3% | 6.1%-79.2% | 0.04 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `GBP_USD` | 5 | 2 | 3 | -5.620 | 40.0% | 11.8%-76.9% | 0.08 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `USD_JPY` | 3 | 1 | 2 | -10.500 | 33.3% | 6.1%-79.2% | 0.20 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `post_news_vol` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `AUD_JPY` | 1 | 0 | 1 | -6.800 | 0.0% | 0.0%-79.3% | 0.00 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `EUR_JPY` | 2 | 1 | 1 | -3.050 | 50.0% | 9.5%-90.5% | 0.26 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `EUR_USD` | 2 | 1 | 1 | -2.400 | 50.0% | 9.5%-90.5% | 0.14 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `GBP_USD` | 2 | 0 | 2 | -8.600 | 0.0% | 0.0%-65.8% | 0.00 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `USD_JPY` | 1 | 0 | 1 | -6.700 | 0.0% | 0.0%-79.3% | 0.00 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `session_vol_expansion` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SESSION_VOL_EXPANSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `squeeze_release_momentum` | `EUR_USD` | 12 | 3 | 9 | -3.408 | 25.0% | 8.9%-53.2% | 0.26 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `squeeze_release_momentum` | `GBP_USD` | 5 | 0 | 5 | -8.360 | 0.0% | 0.0%-43.4% | 0.00 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_anti_hunt_bounce` | `EUR_JPY` | 31 | 15 | 16 | -0.897 | 48.4% | 32.0%-65.2% | 0.76 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `EUR_USD` | 3 | 2 | 1 | +2.367 | 66.7% | 20.8%-93.9% | 2.42 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_anti_hunt_bounce` | `GBP_JPY` | 17 | 10 | 7 | -1.594 | 58.8% | 36.0%-78.4% | 0.62 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_USD` | 6 | 2 | 4 | -1.467 | 33.3% | 9.7%-70.0% | 0.76 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `USD_JPY` | 5 | 3 | 2 | +4.680 | 60.0% | 23.1%-88.2% | 2.71 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `AUD_JPY` | 30 | 11 | 19 | -3.303 | 36.7% | 21.9%-54.5% | 0.40 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_break_retest` | `EUR_JPY` | 18 | 10 | 8 | -3.817 | 55.6% | 33.7%-75.4% | 0.45 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_break_retest` | `GBP_JPY` | 19 | 8 | 11 | -6.447 | 42.1% | 23.1%-63.7% | 0.25 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_break_retest` | `GBP_USD` | 11 | 6 | 5 | -1.882 | 54.5% | 28.0%-78.7% | 0.43 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `USD_JPY` | 53 | 27 | 26 | -1.798 | 50.9% | 37.9%-63.9% | 0.62 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_channel_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_fib_confluence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_liquidity_grab` | `EUR_JPY` | 1 | 1 | 0 | +1.700 | 100.0% | 20.7%-100.0% | n/a | `SR_LIQUIDITY_GRAB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `stoch_trend_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `EUR_USD` | 9 | 2 | 7 | -1.422 | 22.2% | 6.3%-54.7% | 0.34 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `GBP_USD` | 6 | 1 | 5 | -3.300 | 16.7% | 3.0%-56.4% | 0.28 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `USD_JPY` | 16 | 8 | 8 | +1.344 | 50.0% | 28.0%-72.0% | 1.68 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `AUD_JPY` | 2 | 1 | 1 | +1.750 | 50.0% | 9.5%-90.5% | 1.23 | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `EUR_JPY` | 3 | 3 | 0 | +3.733 | 100.0% | 43.8%-100.0% | n/a | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `USD_JPY` | 2 | 0 | 2 | -3.900 | 0.0% | 0.0%-65.8% | 0.00 | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_range_breakout_up` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_RANGE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `EUR_USD` | 11 | 4 | 7 | +0.300 | 36.4% | 15.2%-64.6% | 1.17 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `GBP_USD` | 2 | 0 | 2 | -4.200 | 0.0% | 0.0%-65.8% | 0.00 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `USD_JPY` | 10 | 5 | 5 | +0.200 | 50.0% | 23.7%-76.3% | 1.11 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trendline_sweep` | `EUR_GBP` | 7 | 1 | 6 | -4.329 | 14.3% | 2.6%-51.3% | 0.05 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `GBP_USD` | 21 | 12 | 9 | -3.762 | 57.1% | 36.5%-75.5% | 0.15 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `turtle_soup` | `GBP_USD` | 1 | 0 | 1 | -0.800 | 0.0% | 0.0%-79.3% | 0.00 | `TURTLE_SOUP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tvsm` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TVSM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `v_reversal` | `USD_JPY` | 3 | 1 | 2 | +1.567 | 33.3% | 6.1%-79.2% | 3.76 | `V_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vbp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `VBP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `GBP_JPY` | 2 | 1 | 1 | -5.600 | 50.0% | 9.5%-90.5% | 0.72 | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `USD_JPY` | 5 | 2 | 3 | -20.000 | 40.0% | 11.8%-76.9% | 0.09 | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_momentum_scalp` | `GBP_USD` | 18 | 7 | 11 | -3.767 | 38.9% | 20.3%-61.4% | 0.29 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `vol_momentum_scalp` | `USD_JPY` | 41 | 14 | 27 | -1.732 | 34.1% | 21.6%-49.5% | 0.59 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `EUR_USD` | 21 | 5 | 16 | -0.895 | 23.8% | 10.6%-45.1% | 0.54 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `GBP_USD` | 7 | 1 | 6 | -2.386 | 14.3% | 2.6%-51.3% | 0.23 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `USD_JPY` | 12 | 4 | 8 | -0.900 | 33.3% | 13.8%-60.9% | 0.70 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_GBP` | 6 | 2 | 4 | +0.650 | 33.3% | 9.7%-70.0% | 1.32 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_JPY` | 5 | 4 | 1 | +2.300 | 80.0% | 37.6%-96.4% | 1.56 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_USD` | 4 | 3 | 1 | +1.100 | 75.0% | 30.1%-95.4% | 1.22 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_JPY` | 1 | 1 | 0 | +9.400 | 100.0% | 20.7%-100.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_USD` | 3 | 2 | 1 | -2.967 | 66.7% | 20.8%-93.9% | 0.48 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `USD_JPY` | 1 | 1 | 0 | +0.700 | 100.0% | 20.7%-100.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `wick_imbalance_reversion` | `AUD_JPY` | 33 | 15 | 18 | -1.115 | 45.5% | 29.8%-62.0% | 0.72 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_GBP` | 1 | 1 | 0 | +0.200 | 100.0% | 20.7%-100.0% | n/a | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `EUR_JPY` | 25 | 13 | 12 | -1.696 | 52.0% | 33.5%-70.0% | 0.67 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_USD` | 12 | 7 | 5 | +1.842 | 58.3% | 32.0%-80.7% | 1.71 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `GBP_JPY` | 17 | 13 | 4 | +0.371 | 76.5% | 52.7%-90.4% | 1.10 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `GBP_USD` | 21 | 7 | 14 | -3.310 | 33.3% | 17.2%-54.6% | 0.28 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `USD_JPY` | 24 | 15 | 9 | +0.650 | 62.5% | 42.7%-78.8% | 1.19 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `xs_momentum` | `EUR_USD` | 18 | 10 | 8 | -2.456 | 55.6% | 33.7%-75.4% | 0.39 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `GBP_USD` | 30 | 18 | 12 | -1.497 | 60.0% | 42.3%-75.4% | 0.63 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `USD_JPY` | 49 | 26 | 23 | -3.112 | 53.1% | 39.4%-66.3% | 0.58 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
