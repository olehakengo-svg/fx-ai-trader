# SHADOW_PROMOTE R2 Alert - 2026-10-14T16:32:33.785738+00:00

- Source: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=2000`
- Lookback: `30d`
- Filters: `is_shadow=1`, `pnl_pips IS NOT NULL`, `dedup_violation != 1`, XAU instruments excluded
- Gate: `N >= 10 and EV < 0` -> WARN; `N >= 30 and EV < 0` -> CRITICAL
- Mode: read-only; no env vars, strategy code, tier-master, or DB writes

## Summary

- Promoted strategies: 65
- Cells: 125
- OK: 100
- WARN: 17
- CRITICAL: 8

## WARN / CRITICAL

| Severity | Strategy | Instrument | N | EV | WR | Wilson lower | PF |
|---|---|---|---:|---:|---:|---:|---:|
| **CRITICAL** | `bb_squeeze_breakout` | `EUR_USD` | 47 | -0.855 | 31.9% | 20.4% | 0.50 |
| **WARN** | `bb_squeeze_breakout` | `GBP_USD` | 12 | -0.417 | 25.0% | 8.9% | 0.81 |
| **WARN** | `bb_squeeze_breakout` | `USD_JPY` | 21 | -1.267 | 23.8% | 10.6% | 0.41 |
| **WARN** | `donchian_momentum_breakout` | `USD_JPY` | 15 | -0.593 | 73.3% | 48.0% | 0.91 |
| **WARN** | `dt_bb_rsi_mr` | `USD_JPY` | 13 | -0.838 | 61.5% | 35.5% | 0.79 |
| **CRITICAL** | `dt_sr_channel_reversal` | `EUR_JPY` | 52 | -2.196 | 48.1% | 35.1% | 0.58 |
| **WARN** | `dt_sr_channel_reversal` | `EUR_USD` | 19 | -0.026 | 36.8% | 19.1% | 0.99 |
| **CRITICAL** | `dt_sr_channel_reversal` | `GBP_JPY` | 60 | -5.418 | 28.3% | 18.5% | 0.24 |
| **WARN** | `dt_sr_channel_reversal` | `GBP_USD` | 19 | -2.700 | 36.8% | 19.1% | 0.29 |
| **CRITICAL** | `dt_sr_channel_reversal` | `USD_JPY` | 34 | -2.521 | 50.0% | 34.1% | 0.51 |
| **WARN** | `lin_reg_channel` | `EUR_USD` | 20 | -2.275 | 35.0% | 18.1% | 0.47 |
| **WARN** | `london_breakout` | `USD_JPY` | 12 | -2.425 | 41.7% | 19.3% | 0.50 |
| **CRITICAL** | `sr_break_retest` | `AUD_JPY` | 53 | -1.251 | 47.2% | 34.4% | 0.75 |
| **CRITICAL** | `sr_break_retest` | `USD_JPY` | 37 | -3.762 | 35.1% | 21.8% | 0.31 |
| **WARN** | `three_bar_reversal` | `EUR_USD` | 11 | -3.155 | 18.2% | 5.1% | 0.04 |
| **CRITICAL** | `three_bar_reversal` | `USD_JPY` | 30 | -2.150 | 23.3% | 11.8% | 0.38 |
| **WARN** | `trendline_sweep` | `EUR_USD` | 12 | -3.367 | 58.3% | 32.0% | 0.12 |
| **WARN** | `trendline_sweep` | `GBP_USD` | 24 | -1.433 | 66.7% | 46.7% | 0.56 |
| **WARN** | `vol_surge_detector` | `EUR_USD` | 27 | -1.400 | 18.5% | 8.2% | 0.43 |
| **WARN** | `vol_surge_detector` | `GBP_USD` | 14 | -0.986 | 28.6% | 11.7% | 0.40 |
| **CRITICAL** | `wick_imbalance_reversion` | `AUD_JPY` | 43 | -4.458 | 32.6% | 20.5% | 0.38 |
| **WARN** | `wick_imbalance_reversion` | `EUR_JPY` | 13 | -2.600 | 46.2% | 23.2% | 0.52 |
| **WARN** | `wick_imbalance_reversion` | `EUR_USD` | 13 | -1.885 | 53.8% | 29.1% | 0.17 |
| **WARN** | `wick_imbalance_reversion` | `GBP_JPY` | 10 | -2.220 | 60.0% | 31.3% | 0.64 |
| **WARN** | `wick_imbalance_reversion` | `GBP_USD` | 17 | -3.971 | 29.4% | 13.3% | 0.21 |

## R2 Demote Manual Action

For each CRITICAL cell, manually verify and then remove the relevant Render env var:

- `bb_squeeze_breakout` x `EUR_USD`: remove `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE`
- `dt_sr_channel_reversal` x `EUR_JPY`: remove `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE`
- `dt_sr_channel_reversal` x `GBP_JPY`: remove `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE`
- `dt_sr_channel_reversal` x `USD_JPY`: remove `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE`
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
- Missing CRITICAL cells: `8`
- Add `('bb_squeeze_breakout', 'EUR_USD')`
- Add `('dt_sr_channel_reversal', 'EUR_JPY')`
- Add `('dt_sr_channel_reversal', 'GBP_JPY')`
- Add `('dt_sr_channel_reversal', 'USD_JPY')`
- Add `('sr_break_retest', 'AUD_JPY')`
- Add `('sr_break_retest', 'USD_JPY')`
- Add `('three_bar_reversal', 'USD_JPY')`
- Add `('wick_imbalance_reversion', 'AUD_JPY')`

## All Cells

| Severity | Strategy | Instrument | N | Wins | Losses | EV | WR | Wilson 95% | PF | Env |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| OK | `adx_trend_continuation` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ADX_TREND_CONTINUATION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `asia_range_fade_v1` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ASIA_RANGE_FADE_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `atr_regime_break` | `EUR_USD` | 1 | 1 | 0 | +19.200 | 100.0% | 20.7%-100.0% | n/a | `ALPHA_ATR_REGIME_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_rsi_ema_aligned` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `BB_RSI_EMA_ALIGNED_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `bb_squeeze_breakout` | `EUR_USD` | 47 | 15 | 32 | -0.855 | 31.9% | 20.4%-46.2% | 0.50 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `bb_squeeze_breakout` | `GBP_USD` | 12 | 3 | 9 | -0.417 | 25.0% | 8.9%-53.2% | 0.81 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `USD_CHF` | 2 | 0 | 2 | -2.350 | 0.0% | 0.0%-65.8% | 0.00 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `bb_squeeze_breakout` | `USD_JPY` | 21 | 5 | 16 | -1.267 | 23.8% | 10.6%-45.1% | 0.41 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `confluence_scalp` | `USD_JPY` | 1 | 1 | 0 | +9.500 | 100.0% | 20.7%-100.0% | n/a | `CONFLUENCE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `cpd_divergence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CPD_DIVERGENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `AUD_JPY` | 9 | 6 | 3 | +4.144 | 66.7% | 35.4%-87.9% | 3.89 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `AUD_USD` | 4 | 2 | 2 | -5.525 | 50.0% | 15.0%-85.0% | 0.11 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `NZD_USD` | 2 | 1 | 1 | -2.650 | 50.0% | 9.5%-90.5% | 0.22 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `donchian_momentum_breakout` | `USD_JPY` | 15 | 11 | 4 | -0.593 | 73.3% | 48.0%-89.1% | 0.91 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `EUR_USD` | 5 | 4 | 1 | +5.000 | 80.0% | 37.6%-96.4% | 11.00 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `GBP_USD` | 4 | 1 | 3 | -3.175 | 25.0% | 4.6%-69.9% | 0.41 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_bb_rsi_mr` | `USD_JPY` | 13 | 8 | 5 | -0.838 | 61.5% | 35.5%-82.3% | 0.79 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `EUR_GBP` | 8 | 3 | 5 | -1.500 | 37.5% | 13.7%-69.4% | 0.44 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `dt_sr_channel_reversal` | `EUR_JPY` | 52 | 25 | 27 | -2.196 | 48.1% | 35.1%-61.3% | 0.58 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_USD` | 19 | 7 | 12 | -0.026 | 36.8% | 19.1%-59.0% | 0.99 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `dt_sr_channel_reversal` | `GBP_JPY` | 60 | 17 | 43 | -5.418 | 28.3% | 18.5%-40.8% | 0.24 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `GBP_USD` | 19 | 7 | 12 | -2.700 | 36.8% | 19.1%-59.0% | 0.29 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `dt_sr_channel_reversal` | `USD_JPY` | 34 | 17 | 17 | -2.521 | 50.0% | 34.1%-65.9% | 0.51 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema200_trend_reversal` | `USD_JPY` | 7 | 5 | 2 | -1.314 | 71.4% | 35.9%-91.8% | 0.68 | `EMA200_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`<br>`EMA200_TREND_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_ribbon_ride` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_RIBBON_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_trend_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `engulfing_bb` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_pips_hunter` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_PIPS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_trend_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_TREND_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_vol_break` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_VOL_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `AUD_JPY` | 6 | 1 | 5 | -10.067 | 16.7% | 3.0%-56.4% | 0.03 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `EUR_JPY` | 5 | 3 | 2 | -2.960 | 60.0% | 23.1%-88.2% | 0.47 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `EUR_USD` | 1 | 0 | 1 | -6.000 | 0.0% | 0.0%-79.3% | 0.00 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_JPY` | 1 | 1 | 0 | +3.600 | 100.0% | 20.7%-100.0% | n/a | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_USD` | 4 | 3 | 1 | -2.050 | 75.0% | 30.1%-95.4% | 0.57 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `USD_JPY` | 6 | 3 | 3 | -6.600 | 50.0% | 18.8%-81.2% | 0.04 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `USD_JPY` | 3 | 3 | 0 | +0.567 | 100.0% | 43.8%-100.0% | n/a | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `intraday_seasonality` | `AUD_JPY` | 1 | 1 | 0 | +11.800 | 100.0% | 20.7%-100.0% | n/a | `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `intraday_seasonality` | `GBP_USD` | 2 | 1 | 1 | -2.100 | 50.0% | 9.5%-90.5% | 0.24 | `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `jpy_basket_trend` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `JPY_BASKET_TREND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `keltner_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `lin_reg_channel` | `EUR_USD` | 20 | 7 | 13 | -2.275 | 35.0% | 18.1%-56.7% | 0.47 | `LIN_REG_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_breakout` | `EUR_USD` | 23 | 14 | 9 | +0.070 | 60.9% | 40.8%-77.8% | 1.04 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `london_breakout` | `USD_JPY` | 12 | 5 | 7 | -2.425 | 41.7% | 19.3%-68.0% | 0.50 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_ny_swing` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_NY_SWING_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `EUR_USD` | 3 | 3 | 0 | +5.633 | 100.0% | 43.8%-100.0% | n/a | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `GBP_USD` | 5 | 5 | 0 | +1.040 | 100.0% | 56.6%-100.0% | n/a | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_shrapnel` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_SHRAPNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_mr_hybrid` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_MR_HYBRID_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_regime_switch` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_trend_perfect` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_TREND_PERFECT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `USD_CHF` | 2 | 0 | 2 | -4.250 | 0.0% | 0.0%-65.8% | 0.00 | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `USD_JPY` | 5 | 2 | 3 | -0.580 | 40.0% | 11.8%-76.9% | 0.69 | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `EUR_USD` | 1 | 1 | 0 | +0.600 | 100.0% | 20.7%-100.0% | n/a | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `USD_JPY` | 5 | 1 | 4 | -1.180 | 20.0% | 3.6%-62.4% | 0.64 | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_regime_range_cascade_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `EUR_USD` | 1 | 0 | 1 | -4.600 | 0.0% | 0.0%-79.3% | 0.00 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `GBP_USD` | 4 | 1 | 3 | +0.875 | 25.0% | 4.6%-69.9% | 1.37 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `USD_CHF` | 3 | 1 | 2 | -0.733 | 33.3% | 6.1%-79.2% | 0.44 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `USD_JPY` | 12 | 6 | 6 | +0.117 | 50.0% | 25.4%-74.6% | 1.07 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `EUR_JPY` | 1 | 1 | 0 | +9.800 | 100.0% | 20.7%-100.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `GBP_JPY` | 1 | 1 | 0 | +12.000 | 100.0% | 20.7%-100.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `GBP_USD` | 1 | 1 | 0 | +11.400 | 100.0% | 20.7%-100.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `USD_JPY` | 7 | 1 | 6 | -10.314 | 14.3% | 2.6%-51.3% | 0.01 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ofi_mr` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `OFI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `EUR_USD` | 3 | 2 | 1 | +6.100 | 66.7% | 20.8%-93.9% | 4.66 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `GBP_USD` | 6 | 3 | 3 | -2.767 | 50.0% | 18.8%-81.2% | 0.35 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `USD_JPY` | 2 | 1 | 1 | -5.250 | 50.0% | 9.5%-90.5% | 0.06 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `post_news_vol` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `EUR_JPY` | 2 | 2 | 0 | +6.550 | 100.0% | 34.2%-100.0% | n/a | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `EUR_USD` | 1 | 1 | 0 | +10.700 | 100.0% | 20.7%-100.0% | n/a | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `session_vol_expansion` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SESSION_VOL_EXPANSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `squeeze_release_momentum` | `EUR_USD` | 1 | 0 | 1 | -5.000 | 0.0% | 0.0%-79.3% | 0.00 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `squeeze_release_momentum` | `GBP_USD` | 1 | 1 | 0 | +1.200 | 100.0% | 20.7%-100.0% | n/a | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `EUR_JPY` | 11 | 7 | 4 | +0.191 | 63.6% | 35.4%-84.8% | 1.07 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_JPY` | 7 | 5 | 2 | +0.429 | 71.4% | 35.9%-91.8% | 1.14 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_USD` | 1 | 0 | 1 | -8.700 | 0.0% | 0.0%-79.3% | 0.00 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `USD_JPY` | 5 | 0 | 5 | -9.920 | 0.0% | 0.0%-43.4% | 0.00 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `AUD_JPY` | 53 | 25 | 28 | -1.251 | 47.2% | 34.4%-60.3% | 0.75 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `USD_JPY` | 37 | 13 | 24 | -3.762 | 35.1% | 21.8%-51.2% | 0.31 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_channel_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_fib_confluence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_liquidity_grab` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_LIQUIDITY_GRAB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `stoch_trend_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `three_bar_reversal` | `EUR_USD` | 11 | 2 | 9 | -3.155 | 18.2% | 5.1%-47.7% | 0.04 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `GBP_USD` | 8 | 4 | 4 | -1.887 | 50.0% | 21.5%-78.5% | 0.48 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `three_bar_reversal` | `USD_JPY` | 30 | 7 | 23 | -2.150 | 23.3% | 11.8%-40.9% | 0.38 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `AUD_JPY` | 3 | 1 | 2 | -9.333 | 33.3% | 6.1%-79.2% | 0.06 | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `EUR_JPY` | 4 | 1 | 3 | -12.875 | 25.0% | 4.6%-69.9% | 0.02 | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `USD_JPY` | 9 | 5 | 4 | +0.689 | 55.6% | 26.7%-81.1% | 1.11 | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_range_breakout_up` | `USD_JPY` | 1 | 1 | 0 | +0.800 | 100.0% | 20.7%-100.0% | n/a | `TOKYO_RANGE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `EUR_USD` | 11 | 5 | 6 | +0.236 | 45.5% | 21.3%-72.0% | 1.17 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `GBP_USD` | 4 | 0 | 4 | -2.100 | 0.0% | 0.0%-49.0% | 0.00 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `USD_JPY` | 4 | 3 | 1 | +1.900 | 75.0% | 30.1%-95.4% | 13.67 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trendline_sweep` | `EUR_GBP` | 16 | 10 | 6 | +0.637 | 62.5% | 38.6%-81.5% | 1.34 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `EUR_USD` | 12 | 7 | 5 | -3.367 | 58.3% | 32.0%-80.7% | 0.12 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `GBP_USD` | 24 | 16 | 8 | -1.433 | 66.7% | 46.7%-82.0% | 0.56 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `turtle_soup` | `GBP_USD` | 1 | 0 | 1 | -5.900 | 0.0% | 0.0%-79.3% | 0.00 | `TURTLE_SOUP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tvsm` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TVSM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `v_reversal` | `USD_JPY` | 9 | 4 | 5 | -1.378 | 44.4% | 18.9%-73.3% | 0.19 | `V_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vbp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `VBP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `GBP_JPY` | 3 | 3 | 0 | +9.133 | 100.0% | 43.8%-100.0% | n/a | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `USD_JPY` | 4 | 2 | 2 | +0.000 | 50.0% | 15.0%-85.0% | 1.00 | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_momentum_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `EUR_USD` | 27 | 5 | 22 | -1.400 | 18.5% | 8.2%-36.7% | 0.43 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `GBP_USD` | 14 | 4 | 10 | -0.986 | 28.6% | 11.7%-54.6% | 0.40 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `USD_JPY` | 3 | 2 | 1 | +1.500 | 66.7% | 20.8%-93.9% | 2.12 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `AUD_JPY` | 5 | 3 | 2 | +0.440 | 60.0% | 23.1%-88.2% | 1.10 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_GBP` | 5 | 0 | 5 | -2.540 | 0.0% | 0.0%-43.4% | 0.00 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_JPY` | 4 | 2 | 2 | -2.150 | 50.0% | 15.0%-85.0% | 0.67 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_USD` | 2 | 0 | 2 | -6.600 | 0.0% | 0.0%-65.8% | 0.00 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_JPY` | 2 | 2 | 0 | +10.250 | 100.0% | 34.2%-100.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_USD` | 4 | 1 | 3 | -3.950 | 25.0% | 4.6%-69.9% | 0.08 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `USD_JPY` | 3 | 2 | 1 | +7.500 | 66.7% | 20.8%-93.9% | 76.00 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `wick_imbalance_reversion` | `AUD_JPY` | 43 | 14 | 29 | -4.458 | 32.6% | 20.5%-47.5% | 0.38 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_GBP` | 1 | 0 | 1 | -6.300 | 0.0% | 0.0%-79.3% | 0.00 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `EUR_JPY` | 13 | 6 | 7 | -2.600 | 46.2% | 23.2%-70.9% | 0.52 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `EUR_USD` | 13 | 7 | 6 | -1.885 | 53.8% | 29.1%-76.8% | 0.17 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `GBP_JPY` | 10 | 6 | 4 | -2.220 | 60.0% | 31.3%-83.2% | 0.64 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `GBP_USD` | 17 | 5 | 12 | -3.971 | 29.4% | 13.3%-53.1% | 0.21 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `USD_JPY` | 7 | 7 | 0 | +3.857 | 100.0% | 64.6%-100.0% | n/a | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `xs_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
