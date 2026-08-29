# SHADOW_PROMOTE R2 Alert - 2026-08-29T05:39:32.435983+00:00

- Source: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=2000`
- Lookback: `30d`
- Filters: `is_shadow=1`, `pnl_pips IS NOT NULL`, `dedup_violation != 1`, XAU instruments excluded
- Gate: `N >= 10 and EV < 0` -> WARN; `N >= 30 and EV < 0` -> CRITICAL
- Mode: read-only; no env vars, strategy code, tier-master, or DB writes

## Summary

- Promoted strategies: 65
- Cells: 138
- OK: 107
- WARN: 23
- CRITICAL: 8

## WARN / CRITICAL

| Severity | Strategy | Instrument | N | EV | WR | Wilson lower | PF |
|---|---|---|---:|---:|---:|---:|---:|
| **WARN** | `donchian_momentum_breakout` | `AUD_USD` | 13 | -5.000 | 30.8% | 12.7% | 0.17 |
| **WARN** | `donchian_momentum_breakout` | `NZD_USD` | 15 | -1.487 | 60.0% | 35.7% | 0.75 |
| **WARN** | `dt_bb_rsi_mr` | `USD_JPY` | 19 | -0.479 | 57.9% | 36.3% | 0.84 |
| **WARN** | `dt_sr_channel_reversal` | `EUR_GBP` | 11 | -2.373 | 9.1% | 1.6% | 0.06 |
| **WARN** | `dt_sr_channel_reversal` | `EUR_JPY` | 21 | -2.233 | 38.1% | 20.8% | 0.60 |
| **WARN** | `dt_sr_channel_reversal` | `EUR_USD` | 25 | -0.188 | 44.0% | 26.7% | 0.93 |
| **WARN** | `dt_sr_channel_reversal` | `GBP_JPY` | 24 | -4.746 | 50.0% | 31.4% | 0.30 |
| **CRITICAL** | `dt_sr_channel_reversal` | `GBP_USD` | 31 | -0.532 | 45.2% | 29.2% | 0.82 |
| **CRITICAL** | `dt_sr_channel_reversal` | `USD_JPY` | 33 | -0.336 | 51.5% | 35.2% | 0.90 |
| **WARN** | `engulfing_bb` | `EUR_USD` | 23 | -1.635 | 26.1% | 12.5% | 0.24 |
| **WARN** | `engulfing_bb` | `GBP_USD` | 13 | -1.585 | 23.1% | 8.2% | 0.49 |
| **CRITICAL** | `london_breakout` | `EUR_USD` | 38 | -0.524 | 36.8% | 23.4% | 0.71 |
| **WARN** | `london_breakout` | `GBP_USD` | 15 | -2.707 | 26.7% | 10.9% | 0.10 |
| **WARN** | `ma_regime_switch` | `USD_JPY` | 22 | -1.468 | 50.0% | 30.7% | 0.67 |
| **WARN** | `ob_retest` | `USD_JPY` | 15 | -2.313 | 53.3% | 30.1% | 0.69 |
| **WARN** | `squeeze_release_momentum` | `EUR_USD` | 10 | -4.710 | 20.0% | 5.7% | 0.03 |
| **CRITICAL** | `sr_anti_hunt_bounce` | `EUR_JPY` | 38 | -0.650 | 52.6% | 37.3% | 0.82 |
| **WARN** | `sr_anti_hunt_bounce` | `GBP_JPY` | 18 | -0.833 | 61.1% | 38.6% | 0.79 |
| **CRITICAL** | `sr_break_retest` | `AUD_JPY` | 40 | -2.140 | 45.0% | 30.7% | 0.57 |
| **WARN** | `sr_break_retest` | `EUR_JPY` | 10 | -3.290 | 60.0% | 31.3% | 0.54 |
| **CRITICAL** | `sr_break_retest` | `USD_JPY` | 59 | -1.893 | 49.2% | 36.8% | 0.61 |
| **WARN** | `trend_rebound` | `USD_JPY` | 10 | -0.230 | 40.0% | 16.8% | 0.90 |
| **WARN** | `trendline_sweep` | `GBP_USD` | 24 | -4.967 | 41.7% | 24.5% | 0.10 |
| **WARN** | `vol_momentum_scalp` | `USD_JPY` | 25 | -3.756 | 32.0% | 17.2% | 0.34 |
| **WARN** | `vol_surge_detector` | `EUR_USD` | 24 | -1.167 | 20.8% | 9.2% | 0.44 |
| **WARN** | `vol_surge_detector` | `USD_JPY` | 13 | -1.415 | 30.8% | 12.7% | 0.58 |
| **CRITICAL** | `wick_imbalance_reversion` | `AUD_JPY` | 47 | -0.123 | 55.3% | 41.2% | 0.97 |
| **WARN** | `wick_imbalance_reversion` | `EUR_JPY` | 26 | -2.408 | 50.0% | 32.1% | 0.56 |
| **WARN** | `wick_imbalance_reversion` | `GBP_USD` | 24 | -3.121 | 37.5% | 21.2% | 0.27 |
| **WARN** | `xs_momentum` | `GBP_USD` | 22 | -1.609 | 59.1% | 38.7% | 0.59 |
| **CRITICAL** | `xs_momentum` | `USD_JPY` | 43 | -3.919 | 51.2% | 36.8% | 0.49 |

## R2 Demote Manual Action

For each CRITICAL cell, manually verify and then remove the relevant Render env var:

- `dt_sr_channel_reversal` x `GBP_USD`: remove `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE`
- `dt_sr_channel_reversal` x `USD_JPY`: remove `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE`
- `london_breakout` x `EUR_USD`: remove `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_anti_hunt_bounce` x `EUR_JPY`: remove `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `AUD_JPY`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `USD_JPY`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `wick_imbalance_reversion` x `AUD_JPY`: remove `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`, `WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE`
- `xs_momentum` x `USD_JPY`: remove `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`

Code review locations if manual demotion is chosen:
- `strategies/daytrade/__init__.py` `split_shadow_always` / `SHADOW_ALWAYS_STRATEGIES`
- `strategies/hourly/__init__.py` `split_shadow_always`
- `strategies/scalp/__init__.py` `split_shadow_always`

## Apply Demote Suggestion

- Registry: `/home/runner/work/fx-ai-trader/fx-ai-trader/modules/shadow_demote_registry.py`
- Missing CRITICAL cells: `8`
- Add `('dt_sr_channel_reversal', 'GBP_USD')`
- Add `('dt_sr_channel_reversal', 'USD_JPY')`
- Add `('london_breakout', 'EUR_USD')`
- Add `('sr_anti_hunt_bounce', 'EUR_JPY')`
- Add `('sr_break_retest', 'AUD_JPY')`
- Add `('sr_break_retest', 'USD_JPY')`
- Add `('wick_imbalance_reversion', 'AUD_JPY')`
- Add `('xs_momentum', 'USD_JPY')`

## All Cells

| Severity | Strategy | Instrument | N | Wins | Losses | EV | WR | Wilson 95% | PF | Env |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| OK | `adx_trend_continuation` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ADX_TREND_CONTINUATION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `asia_range_fade_v1` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ASIA_RANGE_FADE_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `atr_regime_break` | `EUR_JPY` | 1 | 1 | 0 | +1.400 | 100.0% | 20.7%-100.0% | n/a | `ALPHA_ATR_REGIME_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `atr_regime_break` | `GBP_JPY` | 2 | 2 | 0 | +3.150 | 100.0% | 34.2%-100.0% | n/a | `ALPHA_ATR_REGIME_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `atr_regime_break` | `GBP_USD` | 1 | 0 | 1 | -12.400 | 0.0% | 0.0%-79.3% | 0.00 | `ALPHA_ATR_REGIME_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_rsi_ema_aligned` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `BB_RSI_EMA_ALIGNED_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `confluence_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CONFLUENCE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `cpd_divergence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CPD_DIVERGENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `AUD_JPY` | 14 | 12 | 2 | +4.536 | 85.7% | 60.1%-96.0% | 2.49 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `donchian_momentum_breakout` | `AUD_USD` | 13 | 4 | 9 | -5.000 | 30.8% | 12.7%-57.6% | 0.17 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `EUR_USD` | 8 | 7 | 1 | +2.725 | 87.5% | 52.9%-97.8% | 2.41 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `NZD_JPY` | 1 | 0 | 1 | -2.800 | 0.0% | 0.0%-79.3% | 0.00 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `donchian_momentum_breakout` | `NZD_USD` | 15 | 9 | 6 | -1.487 | 60.0% | 35.7%-80.2% | 0.75 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `USD_JPY` | 7 | 3 | 4 | -6.886 | 42.9% | 15.8%-75.0% | 0.30 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `EUR_USD` | 4 | 1 | 3 | -3.025 | 25.0% | 4.6%-69.9% | 0.44 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `GBP_USD` | 9 | 5 | 4 | -0.200 | 55.6% | 26.7%-81.1% | 0.93 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_bb_rsi_mr` | `USD_JPY` | 19 | 11 | 8 | -0.479 | 57.9% | 36.3%-76.9% | 0.84 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `AUD_JPY` | 5 | 1 | 4 | -9.920 | 20.0% | 3.6%-62.4% | 0.13 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_GBP` | 11 | 1 | 10 | -2.373 | 9.1% | 1.6%-37.7% | 0.06 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_JPY` | 21 | 8 | 13 | -2.233 | 38.1% | 20.8%-59.1% | 0.60 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_USD` | 25 | 11 | 14 | -0.188 | 44.0% | 26.7%-62.9% | 0.93 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `GBP_JPY` | 24 | 12 | 12 | -4.746 | 50.0% | 31.4%-68.6% | 0.30 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `dt_sr_channel_reversal` | `GBP_USD` | 31 | 14 | 17 | -0.532 | 45.2% | 29.2%-62.2% | 0.82 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `dt_sr_channel_reversal` | `USD_JPY` | 33 | 17 | 16 | -0.336 | 51.5% | 35.2%-67.5% | 0.90 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema200_trend_reversal` | `USD_JPY` | 5 | 3 | 2 | -4.880 | 60.0% | 23.1%-88.2% | 0.08 | `EMA200_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`<br>`EMA200_TREND_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_ribbon_ride` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_RIBBON_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_trend_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `engulfing_bb` | `EUR_USD` | 23 | 6 | 17 | -1.635 | 26.1% | 12.5%-46.5% | 0.24 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `engulfing_bb` | `GBP_USD` | 13 | 3 | 10 | -1.585 | 23.1% | 8.2%-50.3% | 0.49 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_pips_hunter` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_PIPS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_trend_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_TREND_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_vol_break` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_VOL_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `AUD_JPY` | 1 | 0 | 1 | -6.500 | 0.0% | 0.0%-79.3% | 0.00 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `EUR_JPY` | 4 | 3 | 1 | +1.250 | 75.0% | 30.1%-95.4% | 1.37 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_USD` | 3 | 2 | 1 | -2.467 | 66.7% | 20.8%-93.9% | 0.18 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `EUR_GBP` | 3 | 1 | 2 | -2.500 | 33.3% | 6.1%-79.2% | 0.18 | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `GBP_USD` | 1 | 0 | 1 | -17.100 | 0.0% | 0.0%-79.3% | 0.00 | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `intraday_seasonality` | `EUR_GBP` | 2 | 0 | 2 | -2.950 | 0.0% | 0.0%-65.8% | 0.00 | `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `intraday_seasonality` | `GBP_USD` | 2 | 1 | 1 | -1.300 | 50.0% | 9.5%-90.5% | 0.33 | `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `jpy_basket_trend` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `JPY_BASKET_TREND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `keltner_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `lin_reg_channel` | `EUR_USD` | 5 | 1 | 4 | -4.540 | 20.0% | 3.6%-62.4% | 0.03 | `LIN_REG_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `london_breakout` | `EUR_USD` | 38 | 14 | 24 | -0.524 | 36.8% | 23.4%-52.7% | 0.71 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `london_breakout` | `GBP_USD` | 15 | 4 | 11 | -2.707 | 26.7% | 10.9%-52.0% | 0.10 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_breakout` | `USD_JPY` | 4 | 0 | 4 | -11.925 | 0.0% | 0.0%-49.0% | 0.00 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_ny_swing` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_NY_SWING_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `EUR_USD` | 4 | 3 | 1 | +5.325 | 75.0% | 30.1%-95.4% | 2.49 | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `GBP_USD` | 3 | 2 | 1 | +2.100 | 66.7% | 20.8%-93.9% | 1.74 | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_shrapnel` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_SHRAPNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_mr_hybrid` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_MR_HYBRID_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `ma_regime_switch` | `USD_JPY` | 22 | 11 | 11 | -1.468 | 50.0% | 30.7%-69.3% | 0.67 | `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_trend_perfect` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_TREND_PERFECT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `EUR_USD` | 4 | 1 | 3 | -2.825 | 25.0% | 4.6%-69.9% | 0.34 | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `GBP_USD` | 3 | 2 | 1 | +0.767 | 66.7% | 20.8%-93.9% | 1.53 | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `USD_JPY` | 2 | 2 | 0 | +2.350 | 100.0% | 34.2%-100.0% | n/a | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `EUR_USD` | 4 | 1 | 3 | -1.675 | 25.0% | 4.6%-69.9% | 0.09 | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `USD_JPY` | 1 | 0 | 1 | -6.600 | 0.0% | 0.0%-79.3% | 0.00 | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_regime_range_cascade_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `EUR_USD` | 4 | 3 | 1 | +0.625 | 75.0% | 30.1%-95.4% | 1.62 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `GBP_USD` | 5 | 1 | 4 | -1.840 | 20.0% | 3.6%-62.4% | 0.21 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `USD_CHF` | 2 | 0 | 2 | -1.150 | 0.0% | 0.0%-65.8% | 0.00 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `USD_JPY` | 3 | 3 | 0 | +6.633 | 100.0% | 43.8%-100.0% | n/a | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `AUD_JPY` | 6 | 6 | 0 | +13.467 | 100.0% | 61.0%-100.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `EUR_JPY` | 3 | 2 | 1 | -9.267 | 66.7% | 20.8%-93.9% | 0.36 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `GBP_JPY` | 11 | 10 | 1 | +2.700 | 90.9% | 62.3%-98.4% | 1.70 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `ob_retest` | `USD_JPY` | 15 | 8 | 7 | -2.313 | 53.3% | 30.1%-75.2% | 0.69 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ofi_mr` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `OFI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `EUR_USD` | 4 | 3 | 1 | +1.075 | 75.0% | 30.1%-95.4% | 1.55 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `GBP_USD` | 7 | 3 | 4 | -3.486 | 42.9% | 15.8%-75.0% | 0.28 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `USD_JPY` | 3 | 1 | 2 | -10.500 | 33.3% | 6.1%-79.2% | 0.20 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `post_news_vol` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `AUD_JPY` | 2 | 0 | 2 | -7.550 | 0.0% | 0.0%-65.8% | 0.00 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `EUR_JPY` | 1 | 0 | 1 | -8.200 | 0.0% | 0.0%-79.3% | 0.00 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `EUR_USD` | 4 | 1 | 3 | -4.375 | 25.0% | 4.6%-69.9% | 0.04 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `GBP_USD` | 3 | 1 | 2 | -5.467 | 33.3% | 6.1%-79.2% | 0.05 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `USD_JPY` | 1 | 0 | 1 | -6.700 | 0.0% | 0.0%-79.3% | 0.00 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `session_vol_expansion` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SESSION_VOL_EXPANSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `squeeze_release_momentum` | `EUR_USD` | 10 | 2 | 8 | -4.710 | 20.0% | 5.7%-51.0% | 0.03 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `squeeze_release_momentum` | `GBP_USD` | 3 | 0 | 3 | -8.300 | 0.0% | 0.0%-56.2% | 0.00 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_anti_hunt_bounce` | `EUR_JPY` | 38 | 20 | 18 | -0.650 | 52.6% | 37.3%-67.5% | 0.82 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `EUR_USD` | 2 | 1 | 1 | +2.650 | 50.0% | 9.5%-90.5% | 2.06 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_anti_hunt_bounce` | `GBP_JPY` | 18 | 11 | 7 | -0.833 | 61.1% | 38.6%-79.7% | 0.79 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_USD` | 8 | 2 | 6 | -1.825 | 25.0% | 7.1%-59.1% | 0.65 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `USD_JPY` | 5 | 3 | 2 | +4.680 | 60.0% | 23.1%-88.2% | 2.71 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `AUD_JPY` | 40 | 18 | 22 | -2.140 | 45.0% | 30.7%-60.2% | 0.57 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_break_retest` | `EUR_JPY` | 10 | 6 | 4 | -3.290 | 60.0% | 31.3%-83.2% | 0.54 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_break_retest` | `GBP_JPY` | 9 | 4 | 5 | -7.867 | 44.4% | 18.9%-73.3% | 0.26 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_break_retest` | `GBP_USD` | 4 | 2 | 2 | -1.400 | 50.0% | 15.0%-85.0% | 0.59 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `USD_JPY` | 59 | 29 | 30 | -1.893 | 49.2% | 36.8%-61.6% | 0.61 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_channel_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_fib_confluence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_liquidity_grab` | `EUR_JPY` | 1 | 1 | 0 | +1.700 | 100.0% | 20.7%-100.0% | n/a | `SR_LIQUIDITY_GRAB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `stoch_trend_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `EUR_USD` | 7 | 1 | 6 | -1.657 | 14.3% | 2.6%-51.3% | 0.29 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `GBP_USD` | 5 | 1 | 4 | -2.720 | 20.0% | 3.6%-62.4% | 0.36 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `USD_JPY` | 24 | 13 | 11 | +0.983 | 54.2% | 35.1%-72.1% | 1.55 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `AUD_JPY` | 3 | 2 | 1 | +1.433 | 66.7% | 20.8%-93.9% | 1.29 | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `EUR_JPY` | 4 | 3 | 1 | +2.025 | 75.0% | 30.1%-95.4% | 3.61 | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `USD_JPY` | 3 | 0 | 3 | -4.400 | 0.0% | 0.0%-56.2% | 0.00 | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_range_breakout_up` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_RANGE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `EUR_USD` | 10 | 4 | 6 | +0.250 | 40.0% | 16.8%-68.7% | 1.17 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `GBP_USD` | 2 | 0 | 2 | -4.200 | 0.0% | 0.0%-65.8% | 0.00 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trend_rebound` | `USD_JPY` | 10 | 4 | 6 | -0.230 | 40.0% | 16.8%-68.7% | 0.90 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trendline_sweep` | `EUR_GBP` | 7 | 1 | 6 | -4.329 | 14.3% | 2.6%-51.3% | 0.05 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trendline_sweep` | `EUR_USD` | 4 | 3 | 1 | +4.975 | 75.0% | 30.1%-95.4% | 9.29 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `GBP_USD` | 24 | 10 | 14 | -4.967 | 41.7% | 24.5%-61.2% | 0.10 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `turtle_soup` | `GBP_USD` | 4 | 2 | 2 | -1.275 | 50.0% | 15.0%-85.0% | 0.32 | `TURTLE_SOUP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tvsm` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TVSM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `v_reversal` | `USD_JPY` | 5 | 2 | 3 | +1.000 | 40.0% | 11.8%-76.9% | 1.68 | `V_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vbp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `VBP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `GBP_JPY` | 1 | 0 | 1 | -40.100 | 0.0% | 0.0%-79.3% | 0.00 | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `USD_JPY` | 3 | 2 | 1 | -5.967 | 66.7% | 20.8%-93.9% | 0.35 | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_momentum_scalp` | `GBP_USD` | 8 | 2 | 6 | -5.575 | 25.0% | 7.1%-59.1% | 0.04 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_momentum_scalp` | `USD_JPY` | 25 | 8 | 17 | -3.756 | 32.0% | 17.2%-51.6% | 0.34 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `EUR_USD` | 24 | 5 | 19 | -1.167 | 20.8% | 9.2%-40.5% | 0.44 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `GBP_USD` | 8 | 1 | 7 | -2.725 | 12.5% | 2.2%-47.1% | 0.18 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `USD_JPY` | 13 | 4 | 9 | -1.415 | 30.8% | 12.7%-57.6% | 0.58 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `AUD_JPY` | 1 | 0 | 1 | -20.000 | 0.0% | 0.0%-79.3% | 0.00 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_GBP` | 9 | 2 | 7 | -0.978 | 22.2% | 6.3%-54.7% | 0.65 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_JPY` | 5 | 4 | 1 | -0.200 | 80.0% | 37.6%-96.4% | 0.95 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_USD` | 6 | 3 | 3 | -0.750 | 50.0% | 18.8%-81.2% | 0.84 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_JPY` | 1 | 1 | 0 | +9.400 | 100.0% | 20.7%-100.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_USD` | 5 | 4 | 1 | +0.700 | 80.0% | 37.6%-96.4% | 1.20 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `USD_JPY` | 1 | 1 | 0 | +0.700 | 100.0% | 20.7%-100.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `wick_imbalance_reversion` | `AUD_JPY` | 47 | 26 | 21 | -0.123 | 55.3% | 41.2%-68.6% | 0.97 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_GBP` | 1 | 1 | 0 | +0.200 | 100.0% | 20.7%-100.0% | n/a | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `EUR_JPY` | 26 | 13 | 13 | -2.408 | 50.0% | 32.1%-67.9% | 0.56 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_USD` | 12 | 8 | 4 | +2.892 | 66.7% | 39.1%-86.2% | 2.25 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `GBP_JPY` | 23 | 17 | 6 | +0.817 | 73.9% | 53.5%-87.5% | 1.22 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `GBP_USD` | 24 | 9 | 15 | -3.121 | 37.5% | 21.2%-57.3% | 0.27 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `USD_JPY` | 26 | 17 | 9 | +2.615 | 65.4% | 46.2%-80.6% | 1.81 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `xs_momentum` | `EUR_USD` | 7 | 3 | 4 | -4.143 | 42.9% | 15.8%-75.0% | 0.30 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `xs_momentum` | `GBP_USD` | 22 | 13 | 9 | -1.609 | 59.1% | 38.7%-76.7% | 0.59 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `USD_JPY` | 43 | 22 | 21 | -3.919 | 51.2% | 36.8%-65.4% | 0.49 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
