# SHADOW_PROMOTE R2 Alert - 2026-08-11T18:58:31.865447+00:00

- Source: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=2000`
- Lookback: `30d`
- Filters: `is_shadow=1`, `pnl_pips IS NOT NULL`, `dedup_violation != 1`, XAU instruments excluded
- Gate: `N >= 10 and EV < 0` -> WARN; `N >= 30 and EV < 0` -> CRITICAL
- Mode: read-only; no env vars, strategy code, tier-master, or DB writes

## Summary

- Promoted strategies: 65
- Cells: 138
- OK: 101
- WARN: 26
- CRITICAL: 11

## WARN / CRITICAL

| Severity | Strategy | Instrument | N | EV | WR | Wilson lower | PF |
|---|---|---|---:|---:|---:|---:|---:|
| **WARN** | `donchian_momentum_breakout` | `AUD_JPY` | 11 | -4.091 | 63.6% | 35.4% | 0.45 |
| **WARN** | `dt_sr_channel_reversal` | `AUD_JPY` | 23 | -4.452 | 43.5% | 25.6% | 0.22 |
| **WARN** | `dt_sr_channel_reversal` | `EUR_GBP` | 25 | -0.852 | 40.0% | 23.4% | 0.63 |
| **WARN** | `dt_sr_channel_reversal` | `EUR_JPY` | 23 | -2.609 | 34.8% | 18.8% | 0.53 |
| **WARN** | `dt_sr_channel_reversal` | `EUR_USD` | 23 | -0.426 | 47.8% | 29.2% | 0.84 |
| **WARN** | `dt_sr_channel_reversal` | `GBP_JPY` | 29 | -3.886 | 51.7% | 34.4% | 0.35 |
| **WARN** | `dt_sr_channel_reversal` | `USD_JPY` | 27 | -0.022 | 63.0% | 44.2% | 0.99 |
| **CRITICAL** | `engulfing_bb` | `EUR_USD` | 60 | -1.980 | 16.7% | 9.3% | 0.14 |
| **CRITICAL** | `engulfing_bb` | `GBP_USD` | 30 | -0.773 | 33.3% | 19.2% | 0.73 |
| **WARN** | `lin_reg_channel` | `EUR_USD` | 14 | -1.950 | 42.9% | 21.4% | 0.40 |
| **WARN** | `london_breakout` | `EUR_USD` | 16 | -1.669 | 25.0% | 10.2% | 0.15 |
| **CRITICAL** | `london_breakout` | `GBP_USD` | 47 | -2.323 | 29.8% | 18.7% | 0.27 |
| **WARN** | `london_breakout` | `USD_JPY` | 14 | -3.700 | 28.6% | 11.7% | 0.18 |
| **CRITICAL** | `ma_regime_switch` | `USD_JPY` | 46 | -1.072 | 43.5% | 30.2% | 0.65 |
| **WARN** | `ob_retest` | `USD_JPY` | 18 | -2.600 | 44.4% | 24.6% | 0.64 |
| **WARN** | `squeeze_release_momentum` | `EUR_USD` | 11 | -4.418 | 9.1% | 1.6% | 0.21 |
| **WARN** | `sr_anti_hunt_bounce` | `EUR_JPY` | 16 | -1.000 | 50.0% | 28.0% | 0.73 |
| **WARN** | `sr_anti_hunt_bounce` | `EUR_USD` | 15 | -1.647 | 53.3% | 30.1% | 0.53 |
| **WARN** | `sr_break_retest` | `AUD_JPY` | 25 | -2.292 | 44.0% | 26.7% | 0.50 |
| **CRITICAL** | `sr_break_retest` | `EUR_JPY` | 33 | -3.803 | 51.5% | 35.2% | 0.38 |
| **WARN** | `sr_break_retest` | `GBP_JPY` | 29 | -7.414 | 41.4% | 25.5% | 0.19 |
| **CRITICAL** | `sr_break_retest` | `GBP_USD` | 30 | -1.993 | 53.3% | 36.1% | 0.44 |
| **CRITICAL** | `sr_break_retest` | `USD_JPY` | 33 | -2.952 | 51.5% | 35.2% | 0.50 |
| **WARN** | `three_bar_reversal` | `EUR_USD` | 13 | -0.477 | 46.2% | 23.2% | 0.71 |
| **WARN** | `trendline_sweep` | `GBP_USD` | 19 | -3.668 | 63.2% | 41.0% | 0.18 |
| **CRITICAL** | `vol_momentum_scalp` | `GBP_USD` | 37 | -2.654 | 45.9% | 31.0% | 0.32 |
| **CRITICAL** | `vol_momentum_scalp` | `USD_JPY` | 59 | -1.564 | 37.3% | 26.1% | 0.56 |
| **WARN** | `vol_surge_detector` | `EUR_USD` | 16 | -1.600 | 25.0% | 10.2% | 0.37 |
| **WARN** | `vol_surge_detector` | `USD_JPY` | 12 | -0.742 | 33.3% | 13.8% | 0.77 |
| **WARN** | `wick_imbalance_reversion` | `AUD_JPY` | 17 | -3.541 | 29.4% | 13.3% | 0.34 |
| **WARN** | `wick_imbalance_reversion` | `EUR_JPY` | 20 | -0.845 | 60.0% | 38.7% | 0.82 |
| **WARN** | `wick_imbalance_reversion` | `GBP_JPY` | 11 | -0.827 | 72.7% | 43.4% | 0.81 |
| **WARN** | `wick_imbalance_reversion` | `GBP_USD` | 16 | -3.794 | 31.2% | 14.2% | 0.18 |
| **WARN** | `wick_imbalance_reversion` | `USD_JPY` | 16 | -1.625 | 50.0% | 28.0% | 0.70 |
| **WARN** | `xs_momentum` | `EUR_USD` | 25 | -3.092 | 52.0% | 33.5% | 0.30 |
| **CRITICAL** | `xs_momentum` | `GBP_USD` | 47 | -1.119 | 66.0% | 51.7% | 0.67 |
| **CRITICAL** | `xs_momentum` | `USD_JPY` | 65 | -1.503 | 58.5% | 46.3% | 0.75 |

## R2 Demote Manual Action

For each CRITICAL cell, manually verify and then remove the relevant Render env var:

- `engulfing_bb` x `EUR_USD`: remove `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE`
- `engulfing_bb` x `GBP_USD`: remove `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE`
- `london_breakout` x `GBP_USD`: remove `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE`
- `ma_regime_switch` x `USD_JPY`: remove `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `EUR_JPY`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `GBP_USD`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `USD_JPY`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `vol_momentum_scalp` x `GBP_USD`: remove `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`, `VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE`
- `vol_momentum_scalp` x `USD_JPY`: remove `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`, `VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE`
- `xs_momentum` x `GBP_USD`: remove `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`
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
- Add `('sr_break_retest', 'GBP_USD')`
- Add `('sr_break_retest', 'USD_JPY')`
- Add `('vol_momentum_scalp', 'GBP_USD')`
- Add `('vol_momentum_scalp', 'USD_JPY')`
- Add `('xs_momentum', 'GBP_USD')`
- Add `('xs_momentum', 'USD_JPY')`

## All Cells

| Severity | Strategy | Instrument | N | Wins | Losses | EV | WR | Wilson 95% | PF | Env |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| OK | `adx_trend_continuation` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ADX_TREND_CONTINUATION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `asia_range_fade_v1` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ASIA_RANGE_FADE_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `atr_regime_break` | `AUD_JPY` | 1 | 1 | 0 | +2.500 | 100.0% | 20.7%-100.0% | n/a | `ALPHA_ATR_REGIME_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `atr_regime_break` | `GBP_JPY` | 2 | 2 | 0 | +4.150 | 100.0% | 34.2%-100.0% | n/a | `ALPHA_ATR_REGIME_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `atr_regime_break` | `GBP_USD` | 1 | 0 | 1 | -12.400 | 0.0% | 0.0%-79.3% | 0.00 | `ALPHA_ATR_REGIME_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `atr_regime_break` | `USD_JPY` | 2 | 2 | 0 | +1.850 | 100.0% | 34.2%-100.0% | n/a | `ALPHA_ATR_REGIME_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_rsi_ema_aligned` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `BB_RSI_EMA_ALIGNED_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `confluence_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CONFLUENCE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `cpd_divergence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CPD_DIVERGENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `donchian_momentum_breakout` | `AUD_JPY` | 11 | 7 | 4 | -4.091 | 63.6% | 35.4%-84.8% | 0.45 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `AUD_USD` | 5 | 2 | 3 | -1.540 | 40.0% | 11.8%-76.9% | 0.56 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `EUR_USD` | 4 | 4 | 0 | +8.275 | 100.0% | 51.0%-100.0% | n/a | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `NZD_JPY` | 3 | 2 | 1 | +0.867 | 66.7% | 20.8%-93.9% | 1.93 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `NZD_USD` | 5 | 2 | 3 | -5.940 | 40.0% | 11.8%-76.9% | 0.46 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `USD_JPY` | 7 | 3 | 4 | -0.600 | 42.9% | 15.8%-75.0% | 0.89 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `EUR_USD` | 4 | 3 | 1 | +2.775 | 75.0% | 30.1%-95.4% | 2.34 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `GBP_USD` | 15 | 12 | 3 | +2.080 | 80.0% | 54.8%-93.0% | 2.37 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `USD_JPY` | 15 | 10 | 5 | +0.453 | 66.7% | 41.7%-84.8% | 1.19 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `AUD_JPY` | 23 | 10 | 13 | -4.452 | 43.5% | 25.6%-63.2% | 0.22 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_GBP` | 25 | 10 | 15 | -0.852 | 40.0% | 23.4%-59.3% | 0.63 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_JPY` | 23 | 8 | 15 | -2.609 | 34.8% | 18.8%-55.1% | 0.53 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_USD` | 23 | 11 | 12 | -0.426 | 47.8% | 29.2%-67.0% | 0.84 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `GBP_JPY` | 29 | 15 | 14 | -3.886 | 51.7% | 34.4%-68.6% | 0.35 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `GBP_USD` | 21 | 13 | 8 | +2.219 | 61.9% | 40.9%-79.2% | 2.01 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `USD_JPY` | 27 | 17 | 10 | -0.022 | 63.0% | 44.2%-78.5% | 0.99 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema200_trend_reversal` | `USD_JPY` | 7 | 4 | 3 | -1.329 | 57.1% | 25.0%-84.2% | 0.60 | `EMA200_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`<br>`EMA200_TREND_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_ribbon_ride` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_RIBBON_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_trend_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `engulfing_bb` | `EUR_USD` | 60 | 10 | 50 | -1.980 | 16.7% | 9.3%-28.0% | 0.14 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `engulfing_bb` | `GBP_USD` | 30 | 10 | 20 | -0.773 | 33.3% | 19.2%-51.2% | 0.73 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_pips_hunter` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_PIPS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_trend_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_TREND_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_vol_break` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_VOL_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `AUD_JPY` | 4 | 3 | 1 | +1.550 | 75.0% | 30.1%-95.4% | 1.95 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `EUR_JPY` | 4 | 3 | 1 | +1.250 | 75.0% | 30.1%-95.4% | 1.37 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `EUR_USD` | 1 | 0 | 1 | -5.000 | 0.0% | 0.0%-79.3% | 0.00 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_USD` | 3 | 3 | 0 | +0.800 | 100.0% | 43.8%-100.0% | n/a | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `EUR_GBP` | 3 | 2 | 1 | -1.067 | 66.7% | 20.8%-93.9% | 0.49 | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `EUR_USD` | 2 | 1 | 1 | -3.500 | 50.0% | 9.5%-90.5% | 0.05 | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `GBP_USD` | 1 | 1 | 0 | +2.100 | 100.0% | 20.7%-100.0% | n/a | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `intraday_seasonality` | `EUR_GBP` | 2 | 0 | 2 | -1.400 | 0.0% | 0.0%-65.8% | 0.00 | `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `intraday_seasonality` | `GBP_USD` | 2 | 1 | 1 | -1.300 | 50.0% | 9.5%-90.5% | 0.33 | `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `jpy_basket_trend` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `JPY_BASKET_TREND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `keltner_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `lin_reg_channel` | `EUR_USD` | 14 | 6 | 8 | -1.950 | 42.9% | 21.4%-67.4% | 0.40 | `LIN_REG_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `london_breakout` | `EUR_USD` | 16 | 4 | 12 | -1.669 | 25.0% | 10.2%-49.5% | 0.15 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `london_breakout` | `GBP_USD` | 47 | 14 | 33 | -2.323 | 29.8% | 18.7%-44.0% | 0.27 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `london_breakout` | `USD_JPY` | 14 | 4 | 10 | -3.700 | 28.6% | 11.7%-54.6% | 0.18 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_ny_swing` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_NY_SWING_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `EUR_USD` | 2 | 0 | 2 | -8.850 | 0.0% | 0.0%-65.8% | 0.00 | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `GBP_USD` | 1 | 1 | 0 | +1.300 | 100.0% | 20.7%-100.0% | n/a | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_shrapnel` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_SHRAPNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_mr_hybrid` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_MR_HYBRID_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `ma_regime_switch` | `USD_JPY` | 46 | 20 | 26 | -1.072 | 43.5% | 30.2%-57.8% | 0.65 | `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_trend_perfect` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_TREND_PERFECT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `EUR_USD` | 1 | 1 | 0 | +5.800 | 100.0% | 20.7%-100.0% | n/a | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `GBP_USD` | 2 | 1 | 1 | +0.000 | 50.0% | 9.5%-90.5% | 1.00 | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `USD_JPY` | 2 | 2 | 0 | +2.350 | 100.0% | 34.2%-100.0% | n/a | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `EUR_USD` | 3 | 1 | 2 | -1.367 | 33.3% | 6.1%-79.2% | 0.15 | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `USD_JPY` | 1 | 0 | 1 | -6.600 | 0.0% | 0.0%-79.3% | 0.00 | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_regime_range_cascade_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `EUR_USD` | 1 | 1 | 0 | +0.800 | 100.0% | 20.7%-100.0% | n/a | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `GBP_USD` | 4 | 0 | 4 | -2.925 | 0.0% | 0.0%-49.0% | 0.00 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `USD_JPY` | 3 | 3 | 0 | +6.633 | 100.0% | 43.8%-100.0% | n/a | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `AUD_JPY` | 9 | 7 | 2 | +6.933 | 77.8% | 45.3%-93.7% | 4.12 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `EUR_GBP` | 2 | 2 | 0 | +8.750 | 100.0% | 34.2%-100.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `EUR_JPY` | 4 | 2 | 2 | -8.200 | 50.0% | 15.0%-85.0% | 0.32 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `GBP_JPY` | 7 | 6 | 1 | -1.829 | 85.7% | 48.7%-97.4% | 0.70 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `ob_retest` | `USD_JPY` | 18 | 8 | 10 | -2.600 | 44.4% | 24.6%-66.3% | 0.64 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ofi_mr` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `OFI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `EUR_USD` | 2 | 1 | 1 | -3.300 | 50.0% | 9.5%-90.5% | 0.08 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `GBP_USD` | 4 | 1 | 3 | -7.325 | 25.0% | 4.6%-69.9% | 0.04 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `USD_JPY` | 2 | 0 | 2 | -19.750 | 0.0% | 0.0%-65.8% | 0.00 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `post_news_vol` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `EUR_JPY` | 2 | 2 | 0 | +2.100 | 100.0% | 34.2%-100.0% | n/a | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `EUR_USD` | 1 | 0 | 1 | -5.600 | 0.0% | 0.0%-79.3% | 0.00 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `GBP_USD` | 1 | 0 | 1 | -7.900 | 0.0% | 0.0%-79.3% | 0.00 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `USD_JPY` | 1 | 0 | 1 | -6.700 | 0.0% | 0.0%-79.3% | 0.00 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `session_vol_expansion` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SESSION_VOL_EXPANSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `squeeze_release_momentum` | `EUR_USD` | 11 | 1 | 10 | -4.418 | 9.1% | 1.6%-37.7% | 0.21 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `squeeze_release_momentum` | `GBP_USD` | 9 | 1 | 8 | -6.567 | 11.1% | 2.0%-43.5% | 0.03 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_anti_hunt_bounce` | `EUR_JPY` | 16 | 8 | 8 | -1.000 | 50.0% | 28.0%-72.0% | 0.73 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_anti_hunt_bounce` | `EUR_USD` | 15 | 8 | 7 | -1.647 | 53.3% | 30.1%-75.2% | 0.53 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_JPY` | 6 | 5 | 1 | +3.433 | 83.3% | 43.6%-97.0% | 18.17 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_USD` | 2 | 0 | 2 | -11.450 | 0.0% | 0.0%-65.8% | 0.00 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `USD_JPY` | 4 | 2 | 2 | +5.875 | 50.0% | 15.0%-85.0% | 5.35 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_break_retest` | `AUD_JPY` | 25 | 11 | 14 | -2.292 | 44.0% | 26.7%-62.9% | 0.50 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `EUR_JPY` | 33 | 17 | 16 | -3.803 | 51.5% | 35.2%-67.5% | 0.38 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_break_retest` | `GBP_JPY` | 29 | 12 | 17 | -7.414 | 41.4% | 25.5%-59.3% | 0.19 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `GBP_USD` | 30 | 16 | 14 | -1.993 | 53.3% | 36.1%-69.8% | 0.44 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `USD_JPY` | 33 | 17 | 16 | -2.952 | 51.5% | 35.2%-67.5% | 0.50 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_channel_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_fib_confluence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_liquidity_grab` | `EUR_JPY` | 1 | 1 | 0 | +1.700 | 100.0% | 20.7%-100.0% | n/a | `SR_LIQUIDITY_GRAB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `stoch_trend_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `three_bar_reversal` | `EUR_USD` | 13 | 6 | 7 | -0.477 | 46.2% | 23.2%-70.9% | 0.71 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `GBP_USD` | 5 | 1 | 4 | -3.940 | 20.0% | 3.6%-62.4% | 0.10 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `USD_JPY` | 14 | 9 | 5 | +2.671 | 64.3% | 38.8%-83.7% | 2.76 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `AUD_JPY` | 1 | 1 | 0 | +18.500 | 100.0% | 20.7%-100.0% | n/a | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `EUR_JPY` | 1 | 1 | 0 | +7.300 | 100.0% | 20.7%-100.0% | n/a | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `USD_JPY` | 1 | 0 | 1 | -5.400 | 0.0% | 0.0%-79.3% | 0.00 | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_range_breakout_up` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_RANGE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `EUR_USD` | 9 | 4 | 5 | +0.711 | 44.4% | 18.9%-73.3% | 1.39 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `GBP_USD` | 1 | 0 | 1 | -3.900 | 0.0% | 0.0%-79.3% | 0.00 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `USD_JPY` | 7 | 4 | 3 | +0.700 | 57.1% | 25.0%-84.2% | 1.45 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trendline_sweep` | `EUR_GBP` | 9 | 1 | 8 | -5.033 | 11.1% | 2.0%-43.5% | 0.03 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trendline_sweep` | `EUR_USD` | 3 | 2 | 1 | +1.033 | 66.7% | 20.8%-93.9% | 1.25 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `GBP_USD` | 19 | 12 | 7 | -3.668 | 63.2% | 41.0%-80.9% | 0.18 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `turtle_soup` | `GBP_USD` | 2 | 1 | 1 | +0.650 | 50.0% | 9.5%-90.5% | 2.62 | `TURTLE_SOUP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tvsm` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TVSM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `v_reversal` | `USD_JPY` | 4 | 1 | 3 | -0.050 | 25.0% | 4.6%-69.9% | 0.97 | `V_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vbp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `VBP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `GBP_JPY` | 2 | 1 | 1 | +9.850 | 50.0% | 9.5%-90.5% | 3.14 | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `USD_JPY` | 4 | 2 | 2 | -18.075 | 50.0% | 15.0%-85.0% | 0.12 | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `vol_momentum_scalp` | `GBP_USD` | 37 | 17 | 20 | -2.654 | 45.9% | 31.0%-61.6% | 0.32 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `vol_momentum_scalp` | `USD_JPY` | 59 | 22 | 37 | -1.564 | 37.3% | 26.1%-50.0% | 0.56 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `EUR_USD` | 16 | 4 | 12 | -1.600 | 25.0% | 10.2%-49.5% | 0.37 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `GBP_USD` | 9 | 1 | 8 | -3.000 | 11.1% | 2.0%-43.5% | 0.07 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `USD_JPY` | 12 | 4 | 8 | -0.742 | 33.3% | 13.8%-60.9% | 0.77 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_GBP` | 5 | 2 | 3 | -0.480 | 40.0% | 11.8%-76.9% | 0.80 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_JPY` | 3 | 2 | 1 | +0.800 | 66.7% | 20.8%-93.9% | 1.12 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_USD` | 3 | 2 | 1 | -1.133 | 66.7% | 20.8%-93.9% | 0.83 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_USD` | 4 | 3 | 1 | -1.650 | 75.0% | 30.1%-95.4% | 0.61 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `USD_JPY` | 2 | 2 | 0 | +1.200 | 100.0% | 34.2%-100.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `AUD_JPY` | 17 | 5 | 12 | -3.541 | 29.4% | 13.3%-53.1% | 0.34 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_GBP` | 1 | 1 | 0 | +0.200 | 100.0% | 20.7%-100.0% | n/a | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `EUR_JPY` | 20 | 12 | 8 | -0.845 | 60.0% | 38.7%-78.1% | 0.82 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_USD` | 10 | 6 | 4 | +1.320 | 60.0% | 31.3%-83.2% | 1.59 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `GBP_JPY` | 11 | 8 | 3 | -0.827 | 72.7% | 43.4%-90.3% | 0.81 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `GBP_USD` | 16 | 5 | 11 | -3.794 | 31.2% | 14.2%-55.6% | 0.18 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `USD_JPY` | 16 | 8 | 8 | -1.625 | 50.0% | 28.0%-72.0% | 0.70 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `xs_momentum` | `EUR_USD` | 25 | 13 | 12 | -3.092 | 52.0% | 33.5%-70.0% | 0.30 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `GBP_USD` | 47 | 31 | 16 | -1.119 | 66.0% | 51.7%-77.8% | 0.67 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `USD_JPY` | 65 | 38 | 27 | -1.503 | 58.5% | 46.3%-69.6% | 0.75 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
