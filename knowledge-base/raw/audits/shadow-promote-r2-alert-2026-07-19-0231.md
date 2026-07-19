# SHADOW_PROMOTE R2 Alert - 2026-07-19T02:31:45.820297+00:00

- Source: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=2000`
- Lookback: `30d`
- Filters: `is_shadow=1`, `pnl_pips IS NOT NULL`, `dedup_violation != 1`, XAU instruments excluded
- Gate: `N >= 10 and EV < 0` -> WARN; `N >= 30 and EV < 0` -> CRITICAL
- Mode: read-only; no env vars, strategy code, tier-master, or DB writes

## Summary

- Promoted strategies: 65
- Cells: 128
- OK: 94
- WARN: 25
- CRITICAL: 9

## WARN / CRITICAL

| Severity | Strategy | Instrument | N | EV | WR | Wilson lower | PF |
|---|---|---|---:|---:|---:|---:|---:|
| **WARN** | `dt_bb_rsi_mr` | `GBP_USD` | 15 | -5.840 | 20.0% | 7.0% | 0.06 |
| **WARN** | `dt_sr_channel_reversal` | `AUD_JPY` | 15 | -0.300 | 53.3% | 30.1% | 0.90 |
| **WARN** | `dt_sr_channel_reversal` | `EUR_JPY` | 16 | -1.819 | 62.5% | 38.6% | 0.47 |
| **WARN** | `dt_sr_channel_reversal` | `EUR_USD` | 26 | -1.600 | 38.5% | 22.4% | 0.34 |
| **WARN** | `dt_sr_channel_reversal` | `GBP_JPY` | 18 | -0.450 | 66.7% | 43.7% | 0.86 |
| **WARN** | `dt_sr_channel_reversal` | `GBP_USD` | 29 | -1.234 | 48.3% | 31.4% | 0.64 |
| **WARN** | `dt_sr_channel_reversal` | `USD_JPY` | 16 | -0.988 | 43.8% | 23.1% | 0.75 |
| **CRITICAL** | `engulfing_bb` | `EUR_USD` | 85 | -0.698 | 45.9% | 35.7% | 0.65 |
| **WARN** | `engulfing_bb` | `GBP_USD` | 29 | -1.507 | 44.8% | 28.4% | 0.41 |
| **WARN** | `lin_reg_channel` | `EUR_USD` | 18 | -1.006 | 55.6% | 33.7% | 0.60 |
| **WARN** | `london_breakout` | `EUR_USD` | 12 | -1.825 | 33.3% | 13.8% | 0.30 |
| **WARN** | `london_breakout` | `GBP_USD` | 18 | -2.906 | 38.9% | 20.3% | 0.21 |
| **CRITICAL** | `ma_regime_switch` | `USD_JPY` | 79 | -1.490 | 35.4% | 25.8% | 0.37 |
| **WARN** | `ob_retest` | `EUR_USD` | 13 | -1.100 | 69.2% | 42.4% | 0.66 |
| **WARN** | `squeeze_release_momentum` | `GBP_USD` | 16 | -1.419 | 56.2% | 33.2% | 0.58 |
| **WARN** | `sr_anti_hunt_bounce` | `GBP_JPY` | 12 | -10.767 | 41.7% | 19.3% | 0.11 |
| **WARN** | `sr_break_retest` | `AUD_JPY` | 16 | -3.100 | 50.0% | 28.0% | 0.28 |
| **CRITICAL** | `sr_break_retest` | `EUR_JPY` | 33 | -2.000 | 51.5% | 35.2% | 0.53 |
| **CRITICAL** | `sr_break_retest` | `GBP_JPY` | 33 | -2.042 | 75.8% | 59.0% | 0.51 |
| **CRITICAL** | `sr_break_retest` | `GBP_USD` | 34 | -0.303 | 64.7% | 47.9% | 0.88 |
| **CRITICAL** | `sr_break_retest` | `USD_JPY` | 35 | -3.420 | 42.9% | 28.0% | 0.30 |
| **WARN** | `trend_rebound` | `USD_JPY` | 15 | -1.180 | 33.3% | 15.2% | 0.36 |
| **WARN** | `trendline_sweep` | `EUR_GBP` | 27 | -1.707 | 48.1% | 30.7% | 0.35 |
| **WARN** | `trendline_sweep` | `EUR_USD` | 15 | -0.373 | 73.3% | 48.0% | 0.85 |
| **WARN** | `trendline_sweep` | `GBP_USD` | 10 | -2.950 | 60.0% | 31.3% | 0.24 |
| **CRITICAL** | `vol_momentum_scalp` | `USD_JPY` | 60 | -1.165 | 41.7% | 30.1% | 0.53 |
| **WARN** | `vol_surge_detector` | `EUR_USD` | 24 | -2.642 | 20.8% | 9.2% | 0.08 |
| **WARN** | `vol_surge_detector` | `GBP_USD` | 12 | -0.850 | 41.7% | 19.3% | 0.67 |
| **WARN** | `wick_imbalance_reversion` | `EUR_JPY` | 23 | -0.622 | 69.6% | 49.1% | 0.80 |
| **WARN** | `wick_imbalance_reversion` | `GBP_JPY` | 23 | -0.970 | 73.9% | 53.5% | 0.79 |
| **WARN** | `wick_imbalance_reversion` | `USD_JPY` | 16 | -3.263 | 43.8% | 23.1% | 0.15 |
| **CRITICAL** | `xs_momentum` | `EUR_USD` | 37 | -2.878 | 54.1% | 38.4% | 0.27 |
| **CRITICAL** | `xs_momentum` | `GBP_USD` | 38 | -1.053 | 63.2% | 47.3% | 0.79 |
| **WARN** | `xs_momentum` | `USD_JPY` | 29 | -2.834 | 55.2% | 37.5% | 0.29 |

## R2 Demote Manual Action

For each CRITICAL cell, manually verify and then remove the relevant Render env var:

- `engulfing_bb` x `EUR_USD`: remove `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE`
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
- Missing CRITICAL cells: `9`
- Add `('engulfing_bb', 'EUR_USD')`
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
| OK | `donchian_momentum_breakout` | `AUD_JPY` | 9 | 7 | 2 | +1.044 | 77.8% | 45.3%-93.7% | 1.22 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `AUD_USD` | 8 | 3 | 5 | -6.250 | 37.5% | 13.7%-69.4% | 0.26 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `EUR_USD` | 2 | 0 | 2 | -24.100 | 0.0% | 0.0%-65.8% | 0.00 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `NZD_JPY` | 1 | 1 | 0 | +2.900 | 100.0% | 20.7%-100.0% | n/a | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `NZD_USD` | 15 | 12 | 3 | +1.040 | 80.0% | 54.8%-93.0% | 1.31 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `USD_JPY` | 7 | 3 | 4 | -9.443 | 42.9% | 15.8%-75.0% | 0.22 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `EUR_USD` | 7 | 4 | 3 | +0.657 | 57.1% | 25.0%-84.2% | 1.29 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_bb_rsi_mr` | `GBP_USD` | 15 | 3 | 12 | -5.840 | 20.0% | 7.0%-45.2% | 0.06 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `USD_JPY` | 4 | 2 | 2 | -0.900 | 50.0% | 15.0%-85.0% | 0.74 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `AUD_JPY` | 15 | 8 | 7 | -0.300 | 53.3% | 30.1%-75.2% | 0.90 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `EUR_GBP` | 9 | 6 | 3 | +0.789 | 66.7% | 35.4%-87.9% | 1.52 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_JPY` | 16 | 10 | 6 | -1.819 | 62.5% | 38.6%-81.5% | 0.47 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_USD` | 26 | 10 | 16 | -1.600 | 38.5% | 22.4%-57.5% | 0.34 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `GBP_JPY` | 18 | 12 | 6 | -0.450 | 66.7% | 43.7%-83.7% | 0.86 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `GBP_USD` | 29 | 14 | 15 | -1.234 | 48.3% | 31.4%-65.6% | 0.64 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `USD_JPY` | 16 | 7 | 9 | -0.988 | 43.8% | 23.1%-66.8% | 0.75 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema200_trend_reversal` | `USD_JPY` | 20 | 11 | 9 | +0.000 | 55.0% | 34.2%-74.2% | 1.00 | `EMA200_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`<br>`EMA200_TREND_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_ribbon_ride` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_RIBBON_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_trend_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `engulfing_bb` | `EUR_USD` | 85 | 39 | 46 | -0.698 | 45.9% | 35.7%-56.4% | 0.65 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `engulfing_bb` | `GBP_USD` | 29 | 13 | 16 | -1.507 | 44.8% | 28.4%-62.5% | 0.41 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
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
| WARN | `lin_reg_channel` | `EUR_USD` | 18 | 10 | 8 | -1.006 | 55.6% | 33.7%-75.4% | 0.60 | `LIN_REG_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `london_breakout` | `EUR_USD` | 12 | 4 | 8 | -1.825 | 33.3% | 13.8%-60.9% | 0.30 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `london_breakout` | `GBP_USD` | 18 | 7 | 11 | -2.906 | 38.9% | 20.3%-61.4% | 0.21 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_breakout` | `USD_CHF` | 8 | 3 | 5 | -0.263 | 37.5% | 13.7%-69.4% | 0.76 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_breakout` | `USD_JPY` | 3 | 1 | 2 | -2.300 | 33.3% | 6.1%-79.2% | 0.21 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_ny_swing` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_NY_SWING_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `EUR_USD` | 2 | 1 | 1 | +4.750 | 50.0% | 9.5%-90.5% | 3.32 | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `GBP_USD` | 1 | 1 | 0 | +16.300 | 100.0% | 20.7%-100.0% | n/a | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_shrapnel` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_SHRAPNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_mr_hybrid` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_MR_HYBRID_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `ma_regime_switch` | `USD_JPY` | 79 | 28 | 51 | -1.490 | 35.4% | 25.8%-46.4% | 0.37 | `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE` |
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
| OK | `session_vol_expansion` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SESSION_VOL_EXPANSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `squeeze_release_momentum` | `EUR_USD` | 21 | 14 | 7 | +0.462 | 66.7% | 45.4%-82.8% | 1.26 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `squeeze_release_momentum` | `GBP_USD` | 16 | 9 | 7 | -1.419 | 56.2% | 33.2%-76.9% | 0.58 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `EUR_JPY` | 16 | 15 | 1 | +2.444 | 93.8% | 71.7%-98.9% | 7.74 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `EUR_USD` | 5 | 3 | 2 | -2.380 | 60.0% | 23.1%-88.2% | 0.26 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_anti_hunt_bounce` | `GBP_JPY` | 12 | 5 | 7 | -10.767 | 41.7% | 19.3%-68.0% | 0.11 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_USD` | 2 | 2 | 0 | +2.150 | 100.0% | 34.2%-100.0% | n/a | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `USD_JPY` | 4 | 4 | 0 | +1.525 | 100.0% | 51.0%-100.0% | n/a | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_break_retest` | `AUD_JPY` | 16 | 8 | 8 | -3.100 | 50.0% | 28.0%-72.0% | 0.28 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `EUR_JPY` | 33 | 17 | 16 | -2.000 | 51.5% | 35.2%-67.5% | 0.53 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `GBP_JPY` | 33 | 25 | 8 | -2.042 | 75.8% | 59.0%-87.2% | 0.51 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `GBP_USD` | 34 | 22 | 12 | -0.303 | 64.7% | 47.9%-78.5% | 0.88 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `USD_JPY` | 35 | 15 | 20 | -3.420 | 42.9% | 28.0%-59.1% | 0.30 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_channel_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_fib_confluence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_liquidity_grab` | `EUR_JPY` | 1 | 1 | 0 | +2.200 | 100.0% | 20.7%-100.0% | n/a | `SR_LIQUIDITY_GRAB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `stoch_trend_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `EUR_USD` | 8 | 3 | 5 | -1.863 | 37.5% | 13.7%-69.4% | 0.21 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `GBP_USD` | 8 | 2 | 6 | -2.650 | 25.0% | 7.1%-59.1% | 0.36 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `USD_CHF` | 1 | 0 | 1 | -0.700 | 0.0% | 0.0%-79.3% | 0.00 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `USD_JPY` | 5 | 3 | 2 | +2.700 | 60.0% | 23.1%-88.2% | 3.41 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_range_breakout_up` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_RANGE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `EUR_USD` | 3 | 2 | 1 | +1.533 | 66.7% | 20.8%-93.9% | 2.53 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `GBP_USD` | 3 | 1 | 2 | -2.733 | 33.3% | 6.1%-79.2% | 0.21 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trend_rebound` | `USD_JPY` | 15 | 5 | 10 | -1.180 | 33.3% | 15.2%-58.3% | 0.36 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `EUR_GBP` | 27 | 13 | 14 | -1.707 | 48.1% | 30.7%-66.0% | 0.35 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `EUR_USD` | 15 | 11 | 4 | -0.373 | 73.3% | 48.0%-89.1% | 0.85 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `GBP_USD` | 10 | 6 | 4 | -2.950 | 60.0% | 31.3%-83.2% | 0.24 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `turtle_soup` | `EUR_GBP` | 1 | 1 | 0 | +1.500 | 100.0% | 20.7%-100.0% | n/a | `TURTLE_SOUP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `turtle_soup` | `GBP_USD` | 6 | 5 | 1 | -1.150 | 83.3% | 43.6%-97.0% | 0.49 | `TURTLE_SOUP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tvsm` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TVSM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `v_reversal` | `USD_JPY` | 3 | 1 | 2 | -0.333 | 33.3% | 6.1%-79.2% | 0.83 | `V_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vbp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `VBP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `GBP_JPY` | 3 | 3 | 0 | +6.533 | 100.0% | 43.8%-100.0% | n/a | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `USD_JPY` | 4 | 3 | 1 | -0.525 | 75.0% | 30.1%-95.4% | 0.84 | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_momentum_scalp` | `GBP_USD` | 35 | 18 | 17 | +0.683 | 51.4% | 35.6%-67.0% | 1.25 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `vol_momentum_scalp` | `USD_JPY` | 60 | 25 | 35 | -1.165 | 41.7% | 30.1%-54.3% | 0.53 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `EUR_USD` | 24 | 5 | 19 | -2.642 | 20.8% | 9.2%-40.5% | 0.08 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `GBP_USD` | 12 | 5 | 7 | -0.850 | 41.7% | 19.3%-68.0% | 0.67 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `USD_CHF` | 1 | 1 | 0 | +2.000 | 100.0% | 20.7%-100.0% | n/a | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `USD_JPY` | 12 | 6 | 6 | +0.000 | 50.0% | 25.4%-74.6% | 1.00 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_GBP` | 4 | 2 | 2 | -2.025 | 50.0% | 15.0%-85.0% | 0.31 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_JPY` | 1 | 1 | 0 | +7.100 | 100.0% | 20.7%-100.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_USD` | 1 | 0 | 1 | -5.400 | 0.0% | 0.0%-79.3% | 0.00 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_JPY` | 4 | 3 | 1 | -3.375 | 75.0% | 30.1%-95.4% | 0.33 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_USD` | 3 | 2 | 1 | +0.533 | 66.7% | 20.8%-93.9% | 1.21 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_GBP` | 1 | 0 | 1 | -0.300 | 0.0% | 0.0%-79.3% | 0.00 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `EUR_JPY` | 23 | 16 | 7 | -0.622 | 69.6% | 49.1%-84.4% | 0.80 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_USD` | 9 | 7 | 2 | +2.144 | 77.8% | 45.3%-93.7% | 2.33 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `GBP_JPY` | 23 | 17 | 6 | -0.970 | 73.9% | 53.5%-87.5% | 0.79 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `GBP_USD` | 9 | 2 | 7 | -7.956 | 22.2% | 6.3%-54.7% | 0.03 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `USD_JPY` | 16 | 7 | 9 | -3.263 | 43.8% | 23.1%-66.8% | 0.15 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `EUR_USD` | 37 | 20 | 17 | -2.878 | 54.1% | 38.4%-69.0% | 0.27 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `GBP_USD` | 38 | 24 | 14 | -1.053 | 63.2% | 47.3%-76.6% | 0.79 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `xs_momentum` | `USD_JPY` | 29 | 16 | 13 | -2.834 | 55.2% | 37.5%-71.6% | 0.29 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
