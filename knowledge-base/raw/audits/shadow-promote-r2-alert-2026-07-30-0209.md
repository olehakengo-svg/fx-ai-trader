# SHADOW_PROMOTE R2 Alert - 2026-07-30T02:09:34.493904+00:00

- Source: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=2000`
- Lookback: `30d`
- Filters: `is_shadow=1`, `pnl_pips IS NOT NULL`, `dedup_violation != 1`, XAU instruments excluded
- Gate: `N >= 10 and EV < 0` -> WARN; `N >= 30 and EV < 0` -> CRITICAL
- Mode: read-only; no env vars, strategy code, tier-master, or DB writes

## Summary

- Promoted strategies: 65
- Cells: 133
- OK: 96
- WARN: 25
- CRITICAL: 12

## WARN / CRITICAL

| Severity | Strategy | Instrument | N | EV | WR | Wilson lower | PF |
|---|---|---|---:|---:|---:|---:|---:|
| **WARN** | `donchian_momentum_breakout` | `AUD_JPY` | 11 | -4.182 | 63.6% | 35.4% | 0.41 |
| **WARN** | `dt_bb_rsi_mr` | `GBP_USD` | 16 | -1.006 | 50.0% | 28.0% | 0.72 |
| **CRITICAL** | `dt_sr_channel_reversal` | `AUD_JPY` | 32 | -1.703 | 53.1% | 36.4% | 0.53 |
| **WARN** | `dt_sr_channel_reversal` | `EUR_GBP` | 26 | -0.769 | 46.2% | 28.8% | 0.68 |
| **WARN** | `dt_sr_channel_reversal` | `EUR_JPY` | 17 | -2.747 | 52.9% | 31.0% | 0.26 |
| **WARN** | `dt_sr_channel_reversal` | `EUR_USD` | 21 | -0.590 | 52.4% | 32.4% | 0.71 |
| **WARN** | `dt_sr_channel_reversal` | `GBP_JPY` | 24 | -1.038 | 66.7% | 46.7% | 0.66 |
| **WARN** | `dt_sr_channel_reversal` | `USD_JPY` | 12 | -1.525 | 50.0% | 25.4% | 0.60 |
| **CRITICAL** | `engulfing_bb` | `EUR_USD` | 87 | -1.624 | 31.0% | 22.3% | 0.27 |
| **CRITICAL** | `engulfing_bb` | `GBP_USD` | 33 | -1.573 | 36.4% | 22.2% | 0.45 |
| **WARN** | `lin_reg_channel` | `EUR_USD` | 26 | -1.535 | 50.0% | 32.1% | 0.47 |
| **WARN** | `london_breakout` | `EUR_USD` | 19 | -2.032 | 26.3% | 11.8% | 0.14 |
| **CRITICAL** | `london_breakout` | `GBP_USD` | 41 | -1.995 | 34.1% | 21.6% | 0.35 |
| **WARN** | `london_breakout` | `USD_JPY` | 15 | -3.013 | 26.7% | 10.9% | 0.11 |
| **CRITICAL** | `ma_regime_switch` | `USD_JPY` | 53 | -1.143 | 34.0% | 22.7% | 0.45 |
| **WARN** | `squeeze_release_momentum` | `EUR_USD` | 16 | -0.250 | 62.5% | 38.6% | 0.87 |
| **WARN** | `squeeze_release_momentum` | `GBP_USD` | 18 | -1.178 | 61.1% | 38.6% | 0.63 |
| **WARN** | `sr_anti_hunt_bounce` | `EUR_USD` | 16 | -1.881 | 56.2% | 33.2% | 0.41 |
| **WARN** | `sr_break_retest` | `AUD_JPY` | 25 | -2.332 | 56.0% | 37.1% | 0.37 |
| **CRITICAL** | `sr_break_retest` | `EUR_JPY` | 45 | -2.031 | 53.3% | 39.1% | 0.53 |
| **CRITICAL** | `sr_break_retest` | `GBP_JPY` | 31 | -4.903 | 54.8% | 37.8% | 0.25 |
| **CRITICAL** | `sr_break_retest` | `GBP_USD` | 39 | -1.815 | 51.3% | 36.2% | 0.50 |
| **WARN** | `sr_break_retest` | `USD_JPY` | 27 | -2.181 | 40.7% | 24.5% | 0.40 |
| **WARN** | `trend_rebound` | `USD_JPY` | 15 | -0.960 | 40.0% | 19.8% | 0.40 |
| **WARN** | `trendline_sweep` | `EUR_GBP` | 22 | -2.495 | 40.9% | 23.3% | 0.24 |
| **WARN** | `trendline_sweep` | `GBP_USD` | 14 | -1.943 | 71.4% | 45.4% | 0.34 |
| **CRITICAL** | `vol_momentum_scalp` | `GBP_USD` | 58 | -0.355 | 53.4% | 40.8% | 0.88 |
| **CRITICAL** | `vol_momentum_scalp` | `USD_JPY` | 70 | -1.180 | 35.7% | 25.5% | 0.45 |
| **WARN** | `vol_surge_detector` | `EUR_USD` | 21 | -1.305 | 33.3% | 17.2% | 0.35 |
| **WARN** | `vol_surge_detector` | `GBP_USD` | 17 | -1.788 | 29.4% | 13.3% | 0.37 |
| **WARN** | `vol_surge_detector` | `USD_JPY` | 10 | -0.620 | 40.0% | 16.8% | 0.69 |
| **WARN** | `wick_imbalance_reversion` | `EUR_JPY` | 16 | -3.056 | 50.0% | 28.0% | 0.42 |
| **WARN** | `wick_imbalance_reversion` | `GBP_JPY` | 13 | -1.015 | 69.2% | 42.4% | 0.77 |
| **WARN** | `wick_imbalance_reversion` | `GBP_USD` | 13 | -4.415 | 38.5% | 17.7% | 0.12 |
| **WARN** | `wick_imbalance_reversion` | `USD_JPY` | 10 | -4.350 | 40.0% | 16.8% | 0.11 |
| **CRITICAL** | `xs_momentum` | `EUR_USD` | 40 | -1.910 | 57.5% | 42.2% | 0.41 |
| **CRITICAL** | `xs_momentum` | `USD_JPY` | 36 | -0.672 | 58.3% | 42.2% | 0.84 |

## R2 Demote Manual Action

For each CRITICAL cell, manually verify and then remove the relevant Render env var:

- `dt_sr_channel_reversal` x `AUD_JPY`: remove `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE`
- `engulfing_bb` x `EUR_USD`: remove `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE`
- `engulfing_bb` x `GBP_USD`: remove `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE`
- `london_breakout` x `GBP_USD`: remove `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE`
- `ma_regime_switch` x `USD_JPY`: remove `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `EUR_JPY`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `GBP_JPY`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `GBP_USD`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `vol_momentum_scalp` x `GBP_USD`: remove `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`, `VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE`
- `vol_momentum_scalp` x `USD_JPY`: remove `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`, `VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE`
- `xs_momentum` x `EUR_USD`: remove `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`
- `xs_momentum` x `USD_JPY`: remove `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`

Code review locations if manual demotion is chosen:
- `strategies/daytrade/__init__.py` `split_shadow_always` / `SHADOW_ALWAYS_STRATEGIES`
- `strategies/hourly/__init__.py` `split_shadow_always`
- `strategies/scalp/__init__.py` `split_shadow_always`

## Apply Demote Suggestion

- Registry: `/home/runner/work/fx-ai-trader/fx-ai-trader/modules/shadow_demote_registry.py`
- Missing CRITICAL cells: `12`
- Add `('dt_sr_channel_reversal', 'AUD_JPY')`
- Add `('engulfing_bb', 'EUR_USD')`
- Add `('engulfing_bb', 'GBP_USD')`
- Add `('london_breakout', 'GBP_USD')`
- Add `('ma_regime_switch', 'USD_JPY')`
- Add `('sr_break_retest', 'EUR_JPY')`
- Add `('sr_break_retest', 'GBP_JPY')`
- Add `('sr_break_retest', 'GBP_USD')`
- Add `('vol_momentum_scalp', 'GBP_USD')`
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
| OK | `donchian_momentum_breakout` | `NZD_JPY` | 2 | 2 | 0 | +2.900 | 100.0% | 34.2%-100.0% | n/a | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `NZD_USD` | 10 | 8 | 2 | +0.870 | 80.0% | 49.0%-94.3% | 1.26 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `USD_JPY` | 9 | 6 | 3 | +3.044 | 66.7% | 35.4%-87.9% | 2.23 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `EUR_USD` | 7 | 5 | 2 | +1.800 | 71.4% | 35.9%-91.8% | 2.59 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_bb_rsi_mr` | `GBP_USD` | 16 | 8 | 8 | -1.006 | 50.0% | 28.0%-72.0% | 0.72 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `USD_JPY` | 7 | 4 | 3 | -0.143 | 57.1% | 25.0%-84.2% | 0.95 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `dt_sr_channel_reversal` | `AUD_JPY` | 32 | 17 | 15 | -1.703 | 53.1% | 36.4%-69.1% | 0.53 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_GBP` | 26 | 12 | 14 | -0.769 | 46.2% | 28.8%-64.5% | 0.68 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_JPY` | 17 | 9 | 8 | -2.747 | 52.9% | 31.0%-73.8% | 0.26 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_USD` | 21 | 11 | 10 | -0.590 | 52.4% | 32.4%-71.7% | 0.71 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `GBP_JPY` | 24 | 16 | 8 | -1.038 | 66.7% | 46.7%-82.0% | 0.66 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `GBP_USD` | 17 | 9 | 8 | +0.359 | 52.9% | 31.0%-73.8% | 1.12 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `USD_JPY` | 12 | 6 | 6 | -1.525 | 50.0% | 25.4%-74.6% | 0.60 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema200_trend_reversal` | `USD_JPY` | 18 | 11 | 7 | +0.356 | 61.1% | 38.6%-79.7% | 1.15 | `EMA200_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`<br>`EMA200_TREND_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_ribbon_ride` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_RIBBON_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_trend_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `engulfing_bb` | `EUR_USD` | 87 | 27 | 60 | -1.624 | 31.0% | 22.3%-41.4% | 0.27 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `engulfing_bb` | `GBP_USD` | 33 | 12 | 21 | -1.573 | 36.4% | 22.2%-53.4% | 0.45 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_pips_hunter` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_PIPS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_trend_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_TREND_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_vol_break` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_VOL_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `AUD_JPY` | 3 | 3 | 0 | +4.233 | 100.0% | 43.8%-100.0% | n/a | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_JPY` | 1 | 1 | 0 | +2.000 | 100.0% | 20.7%-100.0% | n/a | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_USD` | 1 | 1 | 0 | +2.000 | 100.0% | 20.7%-100.0% | n/a | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `USD_JPY` | 1 | 1 | 0 | +0.600 | 100.0% | 20.7%-100.0% | n/a | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `EUR_GBP` | 1 | 1 | 0 | +1.500 | 100.0% | 20.7%-100.0% | n/a | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `EUR_USD` | 2 | 1 | 1 | -3.500 | 50.0% | 9.5%-90.5% | 0.05 | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `GBP_USD` | 3 | 2 | 1 | -0.100 | 66.7% | 20.8%-93.9% | 0.93 | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `intraday_seasonality` | `AUD_JPY` | 1 | 1 | 0 | +1.600 | 100.0% | 20.7%-100.0% | n/a | `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `intraday_seasonality` | `EUR_GBP` | 1 | 0 | 1 | -1.900 | 0.0% | 0.0%-79.3% | 0.00 | `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `jpy_basket_trend` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `JPY_BASKET_TREND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `keltner_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `lin_reg_channel` | `EUR_USD` | 26 | 13 | 13 | -1.535 | 50.0% | 32.1%-67.9% | 0.47 | `LIN_REG_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `london_breakout` | `EUR_USD` | 19 | 5 | 14 | -2.032 | 26.3% | 11.8%-48.8% | 0.14 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `london_breakout` | `GBP_USD` | 41 | 14 | 27 | -1.995 | 34.1% | 21.6%-49.5% | 0.35 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `london_breakout` | `USD_JPY` | 15 | 4 | 11 | -3.013 | 26.7% | 10.9%-52.0% | 0.11 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_ny_swing` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_NY_SWING_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `EUR_USD` | 2 | 1 | 1 | -0.200 | 50.0% | 9.5%-90.5% | 0.97 | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `GBP_USD` | 2 | 2 | 0 | +1.300 | 100.0% | 34.2%-100.0% | n/a | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_shrapnel` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_SHRAPNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_mr_hybrid` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_MR_HYBRID_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `ma_regime_switch` | `USD_JPY` | 53 | 18 | 35 | -1.143 | 34.0% | 22.7%-47.4% | 0.45 | `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_trend_perfect` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_TREND_PERFECT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `GBP_USD` | 2 | 0 | 2 | -2.700 | 0.0% | 0.0%-65.8% | 0.00 | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `EUR_USD` | 2 | 0 | 2 | -3.450 | 0.0% | 0.0%-65.8% | 0.00 | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `USD_JPY` | 1 | 1 | 0 | +7.300 | 100.0% | 20.7%-100.0% | n/a | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_regime_range_cascade_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `GBP_USD` | 1 | 0 | 1 | -4.100 | 0.0% | 0.0%-79.3% | 0.00 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `USD_JPY` | 4 | 2 | 2 | -1.175 | 50.0% | 15.0%-85.0% | 0.52 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `AUD_JPY` | 4 | 1 | 3 | -3.825 | 25.0% | 4.6%-69.9% | 0.14 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `EUR_GBP` | 2 | 2 | 0 | +8.750 | 100.0% | 34.2%-100.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `EUR_JPY` | 2 | 1 | 1 | -1.450 | 50.0% | 9.5%-90.5% | 0.43 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `EUR_USD` | 2 | 2 | 0 | +6.000 | 100.0% | 34.2%-100.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `GBP_JPY` | 3 | 3 | 0 | +2.800 | 100.0% | 43.8%-100.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `GBP_USD` | 4 | 4 | 0 | +1.650 | 100.0% | 51.0%-100.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `USD_JPY` | 4 | 0 | 4 | -5.600 | 0.0% | 0.0%-49.0% | 0.00 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ofi_mr` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `OFI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `EUR_USD` | 3 | 1 | 2 | -3.100 | 33.3% | 6.1%-79.2% | 0.06 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `GBP_USD` | 2 | 2 | 0 | +2.300 | 100.0% | 34.2%-100.0% | n/a | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `USD_JPY` | 2 | 2 | 0 | +15.750 | 100.0% | 34.2%-100.0% | n/a | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `post_news_vol` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `AUD_JPY` | 1 | 1 | 0 | +2.000 | 100.0% | 20.7%-100.0% | n/a | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `EUR_JPY` | 2 | 1 | 1 | -7.550 | 50.0% | 9.5%-90.5% | 0.12 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `GBP_JPY` | 1 | 1 | 0 | +2.900 | 100.0% | 20.7%-100.0% | n/a | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `GBP_USD` | 1 | 1 | 0 | +13.100 | 100.0% | 20.7%-100.0% | n/a | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `USD_JPY` | 1 | 1 | 0 | +0.300 | 100.0% | 20.7%-100.0% | n/a | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `session_vol_expansion` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SESSION_VOL_EXPANSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `squeeze_release_momentum` | `EUR_USD` | 16 | 10 | 6 | -0.250 | 62.5% | 38.6%-81.5% | 0.87 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `squeeze_release_momentum` | `GBP_USD` | 18 | 11 | 7 | -1.178 | 61.1% | 38.6%-79.7% | 0.63 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `EUR_JPY` | 15 | 12 | 3 | +1.133 | 80.0% | 54.8%-93.0% | 1.82 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_anti_hunt_bounce` | `EUR_USD` | 16 | 9 | 7 | -1.881 | 56.2% | 33.2%-76.9% | 0.41 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_JPY` | 4 | 2 | 2 | -5.500 | 50.0% | 15.0%-85.0% | 0.21 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_USD` | 2 | 2 | 0 | +2.150 | 100.0% | 34.2%-100.0% | n/a | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `USD_JPY` | 8 | 6 | 2 | +1.475 | 75.0% | 40.9%-92.9% | 3.19 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_break_retest` | `AUD_JPY` | 25 | 14 | 11 | -2.332 | 56.0% | 37.1%-73.3% | 0.37 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `EUR_JPY` | 45 | 24 | 21 | -2.031 | 53.3% | 39.1%-67.1% | 0.53 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `GBP_JPY` | 31 | 17 | 14 | -4.903 | 54.8% | 37.8%-70.8% | 0.25 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `GBP_USD` | 39 | 20 | 19 | -1.815 | 51.3% | 36.2%-66.1% | 0.50 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_break_retest` | `USD_JPY` | 27 | 11 | 16 | -2.181 | 40.7% | 24.5%-59.3% | 0.40 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_channel_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_fib_confluence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_liquidity_grab` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_LIQUIDITY_GRAB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `stoch_trend_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `EUR_USD` | 12 | 7 | 5 | +0.008 | 58.3% | 32.0%-80.7% | 1.01 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `GBP_USD` | 7 | 1 | 6 | -4.586 | 14.3% | 2.6%-51.3% | 0.07 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `USD_JPY` | 9 | 5 | 4 | +0.756 | 55.6% | 26.7%-81.1% | 1.54 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_range_breakout_up` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_RANGE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `EUR_USD` | 6 | 3 | 3 | +0.717 | 50.0% | 18.8%-81.2% | 1.62 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `GBP_USD` | 2 | 1 | 1 | +0.950 | 50.0% | 9.5%-90.5% | 7.33 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trend_rebound` | `USD_JPY` | 15 | 6 | 9 | -0.960 | 40.0% | 19.8%-64.3% | 0.40 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `EUR_GBP` | 22 | 9 | 13 | -2.495 | 40.9% | 23.3%-61.3% | 0.24 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trendline_sweep` | `EUR_USD` | 10 | 7 | 3 | +0.130 | 70.0% | 39.7%-89.2% | 1.03 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `GBP_USD` | 14 | 10 | 4 | -1.943 | 71.4% | 45.4%-88.3% | 0.34 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `turtle_soup` | `GBP_USD` | 5 | 5 | 0 | +1.620 | 100.0% | 56.6%-100.0% | n/a | `TURTLE_SOUP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tvsm` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TVSM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `v_reversal` | `USD_JPY` | 2 | 0 | 2 | -3.950 | 0.0% | 0.0%-65.8% | 0.00 | `V_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vbp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `VBP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `GBP_JPY` | 6 | 5 | 1 | +10.417 | 83.3% | 43.6%-97.0% | 7.79 | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `USD_JPY` | 2 | 2 | 0 | +1.550 | 100.0% | 34.2%-100.0% | n/a | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `vol_momentum_scalp` | `GBP_USD` | 58 | 31 | 27 | -0.355 | 53.4% | 40.8%-65.7% | 0.88 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `vol_momentum_scalp` | `USD_JPY` | 70 | 25 | 45 | -1.180 | 35.7% | 25.5%-47.4% | 0.45 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `EUR_USD` | 21 | 7 | 14 | -1.305 | 33.3% | 17.2%-54.6% | 0.35 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `GBP_USD` | 17 | 5 | 12 | -1.788 | 29.4% | 13.3%-53.1% | 0.37 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `USD_JPY` | 10 | 4 | 6 | -0.620 | 40.0% | 16.8%-68.7% | 0.69 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_GBP` | 3 | 2 | 1 | +2.367 | 66.7% | 20.8%-93.9% | 2.37 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_JPY` | 1 | 1 | 0 | +7.100 | 100.0% | 20.7%-100.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_USD` | 1 | 0 | 1 | -5.400 | 0.0% | 0.0%-79.3% | 0.00 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_JPY` | 2 | 1 | 1 | -9.100 | 50.0% | 9.5%-90.5% | 0.09 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_USD` | 2 | 1 | 1 | -2.600 | 50.0% | 9.5%-90.5% | 0.31 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `USD_JPY` | 3 | 3 | 0 | +1.333 | 100.0% | 43.8%-100.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `AUD_JPY` | 4 | 0 | 4 | -6.425 | 0.0% | 0.0%-49.0% | 0.00 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_GBP` | 1 | 0 | 1 | -0.300 | 0.0% | 0.0%-79.3% | 0.00 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `EUR_JPY` | 16 | 8 | 8 | -3.056 | 50.0% | 28.0%-72.0% | 0.42 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_USD` | 9 | 6 | 3 | +0.844 | 66.7% | 35.4%-87.9% | 1.29 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `GBP_JPY` | 13 | 9 | 4 | -1.015 | 69.2% | 42.4%-87.3% | 0.77 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `GBP_USD` | 13 | 5 | 8 | -4.415 | 38.5% | 17.7%-64.5% | 0.12 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `USD_JPY` | 10 | 4 | 6 | -4.350 | 40.0% | 16.8%-68.7% | 0.11 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `EUR_USD` | 40 | 23 | 17 | -1.910 | 57.5% | 42.2%-71.5% | 0.41 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `xs_momentum` | `GBP_USD` | 54 | 37 | 17 | +0.402 | 68.5% | 55.3%-79.3% | 1.12 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `USD_JPY` | 36 | 21 | 15 | -0.672 | 58.3% | 42.2%-72.9% | 0.84 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
