# SHADOW_PROMOTE R2 Alert - 2026-07-27T09:47:43.183271+00:00

- Source: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=2000`
- Lookback: `30d`
- Filters: `is_shadow=1`, `pnl_pips IS NOT NULL`, `dedup_violation != 1`, XAU instruments excluded
- Gate: `N >= 10 and EV < 0` -> WARN; `N >= 30 and EV < 0` -> CRITICAL
- Mode: read-only; no env vars, strategy code, tier-master, or DB writes

## Summary

- Promoted strategies: 65
- Cells: 134
- OK: 95
- WARN: 28
- CRITICAL: 11

## WARN / CRITICAL

| Severity | Strategy | Instrument | N | EV | WR | Wilson lower | PF |
|---|---|---|---:|---:|---:|---:|---:|
| **WARN** | `donchian_momentum_breakout` | `AUD_JPY` | 15 | -2.353 | 66.7% | 41.7% | 0.64 |
| **WARN** | `donchian_momentum_breakout` | `USD_JPY` | 11 | -0.700 | 63.6% | 35.4% | 0.87 |
| **WARN** | `dt_bb_rsi_mr` | `GBP_USD` | 16 | -4.706 | 25.0% | 10.2% | 0.26 |
| **WARN** | `dt_sr_channel_reversal` | `EUR_GBP` | 20 | -0.200 | 50.0% | 29.9% | 0.91 |
| **WARN** | `dt_sr_channel_reversal` | `EUR_JPY` | 17 | -1.494 | 64.7% | 41.3% | 0.53 |
| **WARN** | `dt_sr_channel_reversal` | `EUR_USD` | 23 | -1.300 | 47.8% | 29.2% | 0.43 |
| **WARN** | `dt_sr_channel_reversal` | `GBP_JPY` | 19 | -1.247 | 63.2% | 41.0% | 0.62 |
| **WARN** | `dt_sr_channel_reversal` | `GBP_USD` | 17 | -0.424 | 47.1% | 26.2% | 0.87 |
| **WARN** | `dt_sr_channel_reversal` | `USD_JPY` | 13 | -2.662 | 46.2% | 23.2% | 0.40 |
| **WARN** | `ema200_trend_reversal` | `USD_JPY` | 21 | -1.348 | 52.4% | 32.4% | 0.58 |
| **CRITICAL** | `engulfing_bb` | `EUR_USD` | 86 | -0.987 | 38.4% | 28.8% | 0.49 |
| **CRITICAL** | `engulfing_bb` | `GBP_USD` | 32 | -1.156 | 40.6% | 25.5% | 0.55 |
| **WARN** | `lin_reg_channel` | `EUR_USD` | 23 | -1.626 | 52.2% | 33.0% | 0.39 |
| **WARN** | `london_breakout` | `EUR_USD` | 20 | -2.250 | 25.0% | 11.2% | 0.12 |
| **CRITICAL** | `london_breakout` | `GBP_USD` | 37 | -2.662 | 29.7% | 17.5% | 0.22 |
| **WARN** | `london_breakout` | `USD_JPY` | 15 | -3.013 | 26.7% | 10.9% | 0.11 |
| **CRITICAL** | `ma_regime_switch` | `USD_JPY` | 61 | -1.133 | 36.1% | 25.2% | 0.45 |
| **WARN** | `squeeze_release_momentum` | `EUR_USD` | 17 | -0.129 | 64.7% | 41.3% | 0.93 |
| **WARN** | `squeeze_release_momentum` | `GBP_USD` | 21 | -2.010 | 52.4% | 32.4% | 0.46 |
| **WARN** | `sr_anti_hunt_bounce` | `EUR_USD` | 15 | -3.433 | 46.7% | 24.8% | 0.19 |
| **WARN** | `sr_break_retest` | `AUD_JPY` | 21 | -1.700 | 61.9% | 40.9% | 0.48 |
| **CRITICAL** | `sr_break_retest` | `EUR_JPY` | 41 | -2.415 | 51.2% | 36.5% | 0.47 |
| **CRITICAL** | `sr_break_retest` | `GBP_JPY` | 31 | -4.442 | 64.5% | 46.9% | 0.29 |
| **CRITICAL** | `sr_break_retest` | `GBP_USD` | 36 | -2.053 | 50.0% | 34.5% | 0.43 |
| **WARN** | `sr_break_retest` | `USD_JPY` | 28 | -2.632 | 50.0% | 32.6% | 0.34 |
| **WARN** | `trend_rebound` | `USD_JPY` | 18 | -1.533 | 27.8% | 12.5% | 0.24 |
| **CRITICAL** | `trendline_sweep` | `EUR_GBP` | 31 | -1.948 | 48.4% | 32.0% | 0.32 |
| **WARN** | `trendline_sweep` | `EUR_USD` | 17 | -0.106 | 76.5% | 52.7% | 0.96 |
| **WARN** | `trendline_sweep` | `GBP_USD` | 12 | -3.267 | 66.7% | 39.1% | 0.25 |
| **CRITICAL** | `vol_momentum_scalp` | `USD_JPY` | 78 | -0.991 | 43.6% | 33.1% | 0.55 |
| **WARN** | `vol_surge_detector` | `EUR_USD` | 21 | -1.462 | 28.6% | 13.8% | 0.31 |
| **WARN** | `vol_surge_detector` | `GBP_USD` | 18 | -1.867 | 27.8% | 12.5% | 0.35 |
| **WARN** | `vol_surge_detector` | `USD_JPY` | 16 | -0.506 | 43.8% | 23.1% | 0.74 |
| **WARN** | `wick_imbalance_reversion` | `EUR_JPY` | 16 | -2.563 | 56.2% | 33.2% | 0.48 |
| **WARN** | `wick_imbalance_reversion` | `GBP_JPY` | 13 | -1.569 | 69.2% | 42.4% | 0.68 |
| **WARN** | `wick_imbalance_reversion` | `GBP_USD` | 10 | -4.740 | 50.0% | 23.7% | 0.15 |
| **WARN** | `wick_imbalance_reversion` | `USD_JPY` | 11 | -5.418 | 27.3% | 9.7% | 0.06 |
| **CRITICAL** | `xs_momentum` | `EUR_USD` | 35 | -2.489 | 51.4% | 35.6% | 0.34 |
| **CRITICAL** | `xs_momentum` | `USD_JPY` | 38 | -0.166 | 63.2% | 47.3% | 0.95 |

## R2 Demote Manual Action

For each CRITICAL cell, manually verify and then remove the relevant Render env var:

- `engulfing_bb` x `EUR_USD`: remove `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE`
- `engulfing_bb` x `GBP_USD`: remove `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE`
- `london_breakout` x `GBP_USD`: remove `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE`
- `ma_regime_switch` x `USD_JPY`: remove `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `EUR_JPY`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `GBP_JPY`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `GBP_USD`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `trendline_sweep` x `EUR_GBP`: remove `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE`
- `vol_momentum_scalp` x `USD_JPY`: remove `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`, `VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE`
- `xs_momentum` x `EUR_USD`: remove `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`
- `xs_momentum` x `USD_JPY`: remove `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`

Code review locations if manual demotion is chosen:
- `strategies/daytrade/__init__.py` `split_shadow_always` / `SHADOW_ALWAYS_STRATEGIES`
- `strategies/hourly/__init__.py` `split_shadow_always`
- `strategies/scalp/__init__.py` `split_shadow_always`

## Apply Demote Suggestion

- Registry: `/home/runner/work/fx-ai-trader/fx-ai-trader/modules/shadow_demote_registry.py`
- Missing CRITICAL cells: `11`
- Add `('engulfing_bb', 'EUR_USD')`
- Add `('engulfing_bb', 'GBP_USD')`
- Add `('london_breakout', 'GBP_USD')`
- Add `('ma_regime_switch', 'USD_JPY')`
- Add `('sr_break_retest', 'EUR_JPY')`
- Add `('sr_break_retest', 'GBP_JPY')`
- Add `('sr_break_retest', 'GBP_USD')`
- Add `('trendline_sweep', 'EUR_GBP')`
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
| WARN | `donchian_momentum_breakout` | `AUD_JPY` | 15 | 10 | 5 | -2.353 | 66.7% | 41.7%-84.8% | 0.64 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `AUD_USD` | 9 | 3 | 6 | -6.367 | 33.3% | 12.1%-64.6% | 0.23 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `NZD_JPY` | 1 | 1 | 0 | +2.900 | 100.0% | 20.7%-100.0% | n/a | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `NZD_USD` | 13 | 10 | 3 | +0.162 | 76.9% | 49.7%-91.8% | 1.04 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `donchian_momentum_breakout` | `USD_JPY` | 11 | 7 | 4 | -0.700 | 63.6% | 35.4%-84.8% | 0.87 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `EUR_USD` | 6 | 4 | 2 | +2.067 | 66.7% | 30.0%-90.3% | 2.57 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_bb_rsi_mr` | `GBP_USD` | 16 | 4 | 12 | -4.706 | 25.0% | 10.2%-49.5% | 0.26 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `USD_JPY` | 5 | 3 | 2 | +0.120 | 60.0% | 23.1%-88.2% | 1.05 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `AUD_JPY` | 21 | 13 | 8 | +0.033 | 61.9% | 40.9%-79.2% | 1.01 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_GBP` | 20 | 10 | 10 | -0.200 | 50.0% | 29.9%-70.1% | 0.91 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_JPY` | 17 | 11 | 6 | -1.494 | 64.7% | 41.3%-82.7% | 0.53 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_USD` | 23 | 11 | 12 | -1.300 | 47.8% | 29.2%-67.0% | 0.43 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `GBP_JPY` | 19 | 12 | 7 | -1.247 | 63.2% | 41.0%-80.9% | 0.62 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `GBP_USD` | 17 | 8 | 9 | -0.424 | 47.1% | 26.2%-69.0% | 0.87 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `USD_JPY` | 13 | 6 | 7 | -2.662 | 46.2% | 23.2%-70.9% | 0.40 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `ema200_trend_reversal` | `USD_JPY` | 21 | 11 | 10 | -1.348 | 52.4% | 32.4%-71.7% | 0.58 | `EMA200_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`<br>`EMA200_TREND_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_ribbon_ride` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_RIBBON_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_trend_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `engulfing_bb` | `EUR_USD` | 86 | 33 | 53 | -0.987 | 38.4% | 28.8%-48.9% | 0.49 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `engulfing_bb` | `GBP_USD` | 32 | 13 | 19 | -1.156 | 40.6% | 25.5%-57.7% | 0.55 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_pips_hunter` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_PIPS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_trend_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_TREND_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_vol_break` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_VOL_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `AUD_JPY` | 1 | 1 | 0 | +2.100 | 100.0% | 20.7%-100.0% | n/a | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `EUR_JPY` | 1 | 0 | 1 | -10.500 | 0.0% | 0.0%-79.3% | 0.00 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_JPY` | 1 | 1 | 0 | +2.000 | 100.0% | 20.7%-100.0% | n/a | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_USD` | 3 | 3 | 0 | +1.867 | 100.0% | 43.8%-100.0% | n/a | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `USD_JPY` | 1 | 1 | 0 | +0.600 | 100.0% | 20.7%-100.0% | n/a | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `EUR_USD` | 2 | 1 | 1 | -3.500 | 50.0% | 9.5%-90.5% | 0.05 | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `GBP_USD` | 5 | 2 | 3 | -4.860 | 40.0% | 11.8%-76.9% | 0.14 | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `intraday_seasonality` | `AUD_JPY` | 1 | 1 | 0 | +1.600 | 100.0% | 20.7%-100.0% | n/a | `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `intraday_seasonality` | `EUR_GBP` | 1 | 0 | 1 | -1.900 | 0.0% | 0.0%-79.3% | 0.00 | `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `jpy_basket_trend` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `JPY_BASKET_TREND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `keltner_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `lin_reg_channel` | `EUR_USD` | 23 | 12 | 11 | -1.626 | 52.2% | 33.0%-70.8% | 0.39 | `LIN_REG_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `london_breakout` | `EUR_USD` | 20 | 5 | 15 | -2.250 | 25.0% | 11.2%-46.9% | 0.12 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `london_breakout` | `GBP_USD` | 37 | 11 | 26 | -2.662 | 29.7% | 17.5%-45.8% | 0.22 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `london_breakout` | `USD_JPY` | 15 | 4 | 11 | -3.013 | 26.7% | 10.9%-52.0% | 0.11 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_ny_swing` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_NY_SWING_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `EUR_USD` | 3 | 1 | 2 | -1.500 | 33.3% | 6.1%-79.2% | 0.75 | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `GBP_USD` | 2 | 2 | 0 | +1.300 | 100.0% | 34.2%-100.0% | n/a | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_shrapnel` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_SHRAPNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_mr_hybrid` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_MR_HYBRID_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `ma_regime_switch` | `USD_JPY` | 61 | 22 | 39 | -1.133 | 36.1% | 25.2%-48.6% | 0.45 | `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_trend_perfect` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_TREND_PERFECT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `GBP_USD` | 2 | 0 | 2 | -2.700 | 0.0% | 0.0%-65.8% | 0.00 | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `EUR_USD` | 2 | 0 | 2 | -3.450 | 0.0% | 0.0%-65.8% | 0.00 | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `USD_JPY` | 3 | 2 | 1 | +3.967 | 66.7% | 20.8%-93.9% | 12.90 | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_regime_range_cascade_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `GBP_USD` | 1 | 0 | 1 | -4.100 | 0.0% | 0.0%-79.3% | 0.00 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `USD_JPY` | 5 | 2 | 3 | -1.640 | 40.0% | 11.8%-76.9% | 0.38 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `AUD_JPY` | 3 | 1 | 2 | -2.433 | 33.3% | 6.1%-79.2% | 0.25 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `EUR_GBP` | 2 | 2 | 0 | +8.750 | 100.0% | 34.2%-100.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `EUR_JPY` | 2 | 1 | 1 | -1.450 | 50.0% | 9.5%-90.5% | 0.43 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `EUR_USD` | 2 | 2 | 0 | +6.000 | 100.0% | 34.2%-100.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `GBP_JPY` | 3 | 3 | 0 | +2.800 | 100.0% | 43.8%-100.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `GBP_USD` | 4 | 4 | 0 | +1.650 | 100.0% | 51.0%-100.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `USD_JPY` | 1 | 0 | 1 | -9.200 | 0.0% | 0.0%-79.3% | 0.00 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
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
| WARN | `squeeze_release_momentum` | `EUR_USD` | 17 | 11 | 6 | -0.129 | 64.7% | 41.3%-82.7% | 0.93 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `squeeze_release_momentum` | `GBP_USD` | 21 | 11 | 10 | -2.010 | 52.4% | 32.4%-71.7% | 0.46 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `EUR_JPY` | 15 | 12 | 3 | +1.133 | 80.0% | 54.8%-93.0% | 1.82 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_anti_hunt_bounce` | `EUR_USD` | 15 | 7 | 8 | -3.433 | 46.7% | 24.8%-69.9% | 0.19 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_JPY` | 3 | 1 | 2 | -8.267 | 33.3% | 6.1%-79.2% | 0.11 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_USD` | 2 | 2 | 0 | +2.150 | 100.0% | 34.2%-100.0% | n/a | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `USD_JPY` | 8 | 6 | 2 | +1.475 | 75.0% | 40.9%-92.9% | 3.19 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_break_retest` | `AUD_JPY` | 21 | 13 | 8 | -1.700 | 61.9% | 40.9%-79.2% | 0.48 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `EUR_JPY` | 41 | 21 | 20 | -2.415 | 51.2% | 36.5%-65.7% | 0.47 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `GBP_JPY` | 31 | 20 | 11 | -4.442 | 64.5% | 46.9%-78.9% | 0.29 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `GBP_USD` | 36 | 18 | 18 | -2.053 | 50.0% | 34.5%-65.5% | 0.43 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_break_retest` | `USD_JPY` | 28 | 14 | 14 | -2.632 | 50.0% | 32.6%-67.4% | 0.34 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_channel_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_fib_confluence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_liquidity_grab` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_LIQUIDITY_GRAB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `stoch_trend_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `EUR_USD` | 9 | 5 | 4 | -0.711 | 55.6% | 26.7%-81.1% | 0.58 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `GBP_USD` | 8 | 2 | 6 | -2.800 | 25.0% | 7.1%-59.1% | 0.35 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `USD_JPY` | 8 | 4 | 4 | +0.637 | 50.0% | 21.5%-78.5% | 1.40 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_range_breakout_up` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_RANGE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `EUR_USD` | 6 | 3 | 3 | +0.500 | 50.0% | 18.8%-81.2% | 1.37 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `GBP_USD` | 2 | 1 | 1 | +0.950 | 50.0% | 9.5%-90.5% | 7.33 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trend_rebound` | `USD_JPY` | 18 | 5 | 13 | -1.533 | 27.8% | 12.5%-50.9% | 0.24 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `trendline_sweep` | `EUR_GBP` | 31 | 15 | 16 | -1.948 | 48.4% | 32.0%-65.2% | 0.32 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `EUR_USD` | 17 | 13 | 4 | -0.106 | 76.5% | 52.7%-90.4% | 0.96 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `GBP_USD` | 12 | 8 | 4 | -3.267 | 66.7% | 39.1%-86.2% | 0.25 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `turtle_soup` | `EUR_GBP` | 1 | 1 | 0 | +1.500 | 100.0% | 20.7%-100.0% | n/a | `TURTLE_SOUP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `turtle_soup` | `GBP_USD` | 6 | 6 | 0 | +1.467 | 100.0% | 61.0%-100.0% | n/a | `TURTLE_SOUP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tvsm` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TVSM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `v_reversal` | `USD_JPY` | 3 | 1 | 2 | -0.967 | 33.3% | 6.1%-79.2% | 0.63 | `V_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vbp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `VBP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `GBP_JPY` | 4 | 4 | 0 | +10.700 | 100.0% | 51.0%-100.0% | n/a | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `USD_JPY` | 2 | 2 | 0 | +1.550 | 100.0% | 34.2%-100.0% | n/a | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_momentum_scalp` | `GBP_USD` | 53 | 31 | 22 | +0.606 | 58.5% | 45.1%-70.7% | 1.27 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `vol_momentum_scalp` | `USD_JPY` | 78 | 34 | 44 | -0.991 | 43.6% | 33.1%-54.6% | 0.55 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `EUR_USD` | 21 | 6 | 15 | -1.462 | 28.6% | 13.8%-50.0% | 0.31 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `GBP_USD` | 18 | 5 | 13 | -1.867 | 27.8% | 12.5%-50.9% | 0.35 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `USD_JPY` | 16 | 7 | 9 | -0.506 | 43.8% | 23.1%-66.8% | 0.74 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_GBP` | 6 | 4 | 2 | +1.100 | 66.7% | 30.0%-90.3% | 1.71 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_JPY` | 1 | 1 | 0 | +7.100 | 100.0% | 20.7%-100.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_USD` | 1 | 0 | 1 | -5.400 | 0.0% | 0.0%-79.3% | 0.00 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_JPY` | 3 | 2 | 1 | -5.167 | 66.7% | 20.8%-93.9% | 0.23 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_USD` | 4 | 3 | 1 | +0.975 | 75.0% | 30.1%-95.4% | 1.52 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `USD_JPY` | 3 | 3 | 0 | +1.333 | 100.0% | 43.8%-100.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `AUD_JPY` | 4 | 0 | 4 | -6.425 | 0.0% | 0.0%-49.0% | 0.00 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_GBP` | 1 | 0 | 1 | -0.300 | 0.0% | 0.0%-79.3% | 0.00 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `EUR_JPY` | 16 | 9 | 7 | -2.563 | 56.2% | 33.2%-76.9% | 0.48 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_USD` | 8 | 6 | 2 | +1.363 | 75.0% | 40.9%-92.9% | 1.48 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `GBP_JPY` | 13 | 9 | 4 | -1.569 | 69.2% | 42.4%-87.3% | 0.68 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `GBP_USD` | 10 | 5 | 5 | -4.740 | 50.0% | 23.7%-76.3% | 0.15 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `USD_JPY` | 11 | 3 | 8 | -5.418 | 27.3% | 9.7%-56.6% | 0.06 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `EUR_USD` | 35 | 18 | 17 | -2.489 | 51.4% | 35.6%-67.0% | 0.34 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `xs_momentum` | `GBP_USD` | 42 | 29 | 13 | +1.112 | 69.0% | 54.0%-80.9% | 1.33 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `USD_JPY` | 38 | 24 | 14 | -0.166 | 63.2% | 47.3%-76.6% | 0.95 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
