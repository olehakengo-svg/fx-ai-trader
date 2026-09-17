# SHADOW_PROMOTE R2 Alert - 2026-09-17T16:14:42.743779+00:00

- Source: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=2000`
- Lookback: `30d`
- Filters: `is_shadow=1`, `pnl_pips IS NOT NULL`, `dedup_violation != 1`, XAU instruments excluded
- Gate: `N >= 10 and EV < 0` -> WARN; `N >= 30 and EV < 0` -> CRITICAL
- Mode: read-only; no env vars, strategy code, tier-master, or DB writes

## Summary

- Promoted strategies: 65
- Cells: 127
- OK: 103
- WARN: 17
- CRITICAL: 7

## WARN / CRITICAL

| Severity | Strategy | Instrument | N | EV | WR | Wilson lower | PF |
|---|---|---|---:|---:|---:|---:|---:|
| **WARN** | `donchian_momentum_breakout` | `AUD_USD` | 11 | -3.582 | 45.5% | 21.3% | 0.27 |
| **WARN** | `donchian_momentum_breakout` | `NZD_USD` | 10 | -2.860 | 50.0% | 23.7% | 0.55 |
| **WARN** | `dt_bb_rsi_mr` | `GBP_USD` | 10 | -0.800 | 60.0% | 31.3% | 0.70 |
| **WARN** | `dt_bb_rsi_mr` | `USD_JPY` | 14 | -0.014 | 57.1% | 32.6% | 1.00 |
| **WARN** | `dt_sr_channel_reversal` | `EUR_GBP` | 12 | -2.050 | 25.0% | 8.9% | 0.31 |
| **CRITICAL** | `dt_sr_channel_reversal` | `EUR_JPY` | 33 | -3.945 | 39.4% | 24.7% | 0.35 |
| **WARN** | `dt_sr_channel_reversal` | `EUR_USD` | 15 | -1.573 | 40.0% | 19.8% | 0.56 |
| **CRITICAL** | `dt_sr_channel_reversal` | `GBP_JPY` | 37 | -4.197 | 45.9% | 31.0% | 0.28 |
| **WARN** | `dt_sr_channel_reversal` | `GBP_USD` | 25 | -1.504 | 40.0% | 23.4% | 0.44 |
| **CRITICAL** | `dt_sr_channel_reversal` | `USD_JPY` | 35 | -1.374 | 60.0% | 43.6% | 0.61 |
| **CRITICAL** | `london_breakout` | `EUR_USD` | 48 | -1.048 | 39.6% | 27.0% | 0.50 |
| **WARN** | `sr_anti_hunt_bounce` | `EUR_JPY` | 13 | -3.315 | 53.8% | 29.1% | 0.45 |
| **CRITICAL** | `sr_break_retest` | `AUD_JPY` | 48 | -0.773 | 54.2% | 40.3% | 0.83 |
| **CRITICAL** | `sr_break_retest` | `USD_JPY` | 33 | -2.479 | 42.4% | 27.2% | 0.48 |
| **WARN** | `three_bar_reversal` | `EUR_USD` | 11 | -1.000 | 36.4% | 15.2% | 0.58 |
| **WARN** | `three_bar_reversal` | `USD_JPY` | 28 | -0.111 | 46.4% | 29.5% | 0.95 |
| **WARN** | `trend_rebound` | `EUR_USD` | 17 | -0.241 | 35.3% | 17.3% | 0.84 |
| **WARN** | `trendline_sweep` | `GBP_USD` | 27 | -2.689 | 55.6% | 37.3% | 0.30 |
| **WARN** | `vol_surge_detector` | `EUR_USD` | 21 | -2.129 | 14.3% | 5.0% | 0.23 |
| **CRITICAL** | `wick_imbalance_reversion` | `AUD_JPY` | 56 | -1.202 | 55.4% | 42.4% | 0.73 |
| **WARN** | `wick_imbalance_reversion` | `EUR_JPY` | 16 | -2.775 | 50.0% | 28.0% | 0.54 |
| **WARN** | `wick_imbalance_reversion` | `EUR_USD` | 13 | -3.023 | 30.8% | 12.7% | 0.34 |
| **WARN** | `wick_imbalance_reversion` | `GBP_JPY` | 16 | -1.881 | 62.5% | 38.6% | 0.69 |
| **WARN** | `wick_imbalance_reversion` | `GBP_USD` | 25 | -3.080 | 32.0% | 17.2% | 0.18 |

## R2 Demote Manual Action

For each CRITICAL cell, manually verify and then remove the relevant Render env var:

- `dt_sr_channel_reversal` x `EUR_JPY`: remove `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE`
- `dt_sr_channel_reversal` x `GBP_JPY`: remove `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE`
- `dt_sr_channel_reversal` x `USD_JPY`: remove `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE`
- `london_breakout` x `EUR_USD`: remove `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `AUD_JPY`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `USD_JPY`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `wick_imbalance_reversion` x `AUD_JPY`: remove `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`, `WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE`

Code review locations if manual demotion is chosen:
- `strategies/daytrade/__init__.py` `split_shadow_always` / `SHADOW_ALWAYS_STRATEGIES`
- `strategies/hourly/__init__.py` `split_shadow_always`
- `strategies/scalp/__init__.py` `split_shadow_always`

## Apply Demote Suggestion

- Registry: `/home/runner/work/fx-ai-trader/fx-ai-trader/modules/shadow_demote_registry.py`
- Missing CRITICAL cells: `7`
- Add `('dt_sr_channel_reversal', 'EUR_JPY')`
- Add `('dt_sr_channel_reversal', 'GBP_JPY')`
- Add `('dt_sr_channel_reversal', 'USD_JPY')`
- Add `('london_breakout', 'EUR_USD')`
- Add `('sr_break_retest', 'AUD_JPY')`
- Add `('sr_break_retest', 'USD_JPY')`
- Add `('wick_imbalance_reversion', 'AUD_JPY')`

## All Cells

| Severity | Strategy | Instrument | N | Wins | Losses | EV | WR | Wilson 95% | PF | Env |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| OK | `adx_trend_continuation` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ADX_TREND_CONTINUATION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `asia_range_fade_v1` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ASIA_RANGE_FADE_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `atr_regime_break` | `EUR_JPY` | 1 | 1 | 0 | +2.100 | 100.0% | 20.7%-100.0% | n/a | `ALPHA_ATR_REGIME_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_rsi_ema_aligned` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `BB_RSI_EMA_ALIGNED_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `EUR_USD` | 9 | 0 | 9 | -2.722 | 0.0% | 0.0%-29.9% | 0.00 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `GBP_USD` | 3 | 0 | 3 | -4.367 | 0.0% | 0.0%-56.2% | 0.00 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `USD_CHF` | 1 | 0 | 1 | -2.000 | 0.0% | 0.0%-79.3% | 0.00 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `USD_JPY` | 9 | 3 | 6 | -0.711 | 33.3% | 12.1%-64.6% | 0.73 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `confluence_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CONFLUENCE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `cpd_divergence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CPD_DIVERGENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `AUD_JPY` | 6 | 6 | 0 | +9.983 | 100.0% | 61.0%-100.0% | n/a | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `donchian_momentum_breakout` | `AUD_USD` | 11 | 5 | 6 | -3.582 | 45.5% | 21.3%-72.0% | 0.27 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `EUR_USD` | 6 | 4 | 2 | -1.150 | 66.7% | 30.0%-90.3% | 0.79 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `donchian_momentum_breakout` | `NZD_USD` | 10 | 5 | 5 | -2.860 | 50.0% | 23.7%-76.3% | 0.55 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `USD_JPY` | 9 | 8 | 1 | +1.011 | 88.9% | 56.5%-98.0% | 1.26 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `EUR_USD` | 9 | 6 | 3 | +3.133 | 66.7% | 35.4%-87.9% | 2.68 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_bb_rsi_mr` | `GBP_USD` | 10 | 6 | 4 | -0.800 | 60.0% | 31.3%-83.2% | 0.70 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_bb_rsi_mr` | `USD_JPY` | 14 | 8 | 6 | -0.014 | 57.1% | 32.6%-78.6% | 1.00 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_GBP` | 12 | 3 | 9 | -2.050 | 25.0% | 8.9%-53.2% | 0.31 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `dt_sr_channel_reversal` | `EUR_JPY` | 33 | 13 | 20 | -3.945 | 39.4% | 24.7%-56.3% | 0.35 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_USD` | 15 | 6 | 9 | -1.573 | 40.0% | 19.8%-64.3% | 0.56 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `dt_sr_channel_reversal` | `GBP_JPY` | 37 | 17 | 20 | -4.197 | 45.9% | 31.0%-61.6% | 0.28 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `GBP_USD` | 25 | 10 | 15 | -1.504 | 40.0% | 23.4%-59.3% | 0.44 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `dt_sr_channel_reversal` | `USD_JPY` | 35 | 21 | 14 | -1.374 | 60.0% | 43.6%-74.4% | 0.61 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema200_trend_reversal` | `USD_JPY` | 1 | 1 | 0 | +11.000 | 100.0% | 20.7%-100.0% | n/a | `EMA200_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`<br>`EMA200_TREND_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_ribbon_ride` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_RIBBON_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_trend_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `engulfing_bb` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_pips_hunter` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_PIPS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_trend_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_TREND_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_vol_break` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_VOL_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `AUD_JPY` | 3 | 1 | 2 | -3.267 | 33.3% | 6.1%-79.2% | 0.51 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `EUR_JPY` | 2 | 1 | 1 | -2.750 | 50.0% | 9.5%-90.5% | 0.29 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_JPY` | 1 | 0 | 1 | -16.700 | 0.0% | 0.0%-79.3% | 0.00 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_USD` | 1 | 0 | 1 | -9.000 | 0.0% | 0.0%-79.3% | 0.00 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `USD_JPY` | 2 | 1 | 1 | -6.400 | 50.0% | 9.5%-90.5% | 0.05 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `GBP_USD` | 3 | 2 | 1 | -4.900 | 66.7% | 20.8%-93.9% | 0.14 | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `intraday_seasonality` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `jpy_basket_trend` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `JPY_BASKET_TREND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `keltner_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `lin_reg_channel` | `EUR_USD` | 12 | 8 | 4 | +1.017 | 66.7% | 39.1%-86.2% | 1.64 | `LIN_REG_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `london_breakout` | `EUR_USD` | 48 | 19 | 29 | -1.048 | 39.6% | 27.0%-53.7% | 0.50 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_breakout` | `USD_JPY` | 8 | 5 | 3 | +3.325 | 62.5% | 30.6%-86.3% | 1.91 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_ny_swing` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_NY_SWING_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `EUR_USD` | 2 | 1 | 1 | +6.150 | 50.0% | 9.5%-90.5% | 4.00 | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `GBP_USD` | 4 | 2 | 2 | -2.075 | 50.0% | 15.0%-85.0% | 0.73 | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_shrapnel` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_SHRAPNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_mr_hybrid` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_MR_HYBRID_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_regime_switch` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_trend_perfect` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_TREND_PERFECT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `EUR_USD` | 3 | 0 | 3 | -5.700 | 0.0% | 0.0%-56.2% | 0.00 | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `GBP_USD` | 1 | 1 | 0 | +1.300 | 100.0% | 20.7%-100.0% | n/a | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `USD_JPY` | 2 | 1 | 1 | -1.500 | 50.0% | 9.5%-90.5% | 0.12 | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `EUR_USD` | 8 | 2 | 6 | -1.575 | 25.0% | 7.1%-59.1% | 0.10 | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `USD_JPY` | 1 | 0 | 1 | -6.500 | 0.0% | 0.0%-79.3% | 0.00 | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_regime_range_cascade_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `EUR_USD` | 4 | 2 | 2 | +0.425 | 50.0% | 15.0%-85.0% | 1.41 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `GBP_USD` | 1 | 1 | 0 | +2.500 | 100.0% | 20.7%-100.0% | n/a | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `USD_CHF` | 2 | 0 | 2 | -1.150 | 0.0% | 0.0%-65.8% | 0.00 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `USD_JPY` | 1 | 1 | 0 | +0.800 | 100.0% | 20.7%-100.0% | n/a | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `EUR_JPY` | 1 | 1 | 0 | +9.800 | 100.0% | 20.7%-100.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `GBP_JPY` | 4 | 4 | 0 | +10.625 | 100.0% | 51.0%-100.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `GBP_USD` | 1 | 0 | 1 | -7.600 | 0.0% | 0.0%-79.3% | 0.00 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `USD_JPY` | 1 | 0 | 1 | -20.900 | 0.0% | 0.0%-79.3% | 0.00 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ofi_mr` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `OFI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `EUR_USD` | 4 | 2 | 2 | -2.425 | 50.0% | 15.0%-85.0% | 0.54 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `GBP_USD` | 6 | 4 | 2 | -0.033 | 66.7% | 30.0%-90.3% | 0.98 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `USD_JPY` | 3 | 1 | 2 | -10.567 | 33.3% | 6.1%-79.2% | 0.02 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `post_news_vol` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `AUD_JPY` | 1 | 0 | 1 | -8.300 | 0.0% | 0.0%-79.3% | 0.00 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `EUR_USD` | 2 | 0 | 2 | -6.350 | 0.0% | 0.0%-65.8% | 0.00 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `GBP_USD` | 1 | 1 | 0 | +0.800 | 100.0% | 20.7%-100.0% | n/a | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `USD_JPY` | 1 | 1 | 0 | +10.300 | 100.0% | 20.7%-100.0% | n/a | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `session_vol_expansion` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SESSION_VOL_EXPANSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `squeeze_release_momentum` | `EUR_USD` | 1 | 0 | 1 | -7.800 | 0.0% | 0.0%-79.3% | 0.00 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `squeeze_release_momentum` | `GBP_USD` | 1 | 0 | 1 | -14.300 | 0.0% | 0.0%-79.3% | 0.00 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_anti_hunt_bounce` | `EUR_JPY` | 13 | 7 | 6 | -3.315 | 53.8% | 29.1%-76.8% | 0.45 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `EUR_USD` | 7 | 4 | 3 | -7.057 | 57.1% | 25.0%-84.2% | 0.06 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_JPY` | 7 | 6 | 1 | +2.657 | 85.7% | 48.7%-97.4% | 2.68 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_USD` | 3 | 1 | 2 | +2.433 | 33.3% | 6.1%-79.2% | 2.26 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `USD_JPY` | 3 | 1 | 2 | -8.467 | 33.3% | 6.1%-79.2% | 0.03 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `AUD_JPY` | 48 | 26 | 22 | -0.773 | 54.2% | 40.3%-67.4% | 0.83 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `USD_JPY` | 33 | 14 | 19 | -2.479 | 42.4% | 27.2%-59.2% | 0.48 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_channel_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_fib_confluence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_liquidity_grab` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_LIQUIDITY_GRAB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `stoch_trend_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `three_bar_reversal` | `EUR_USD` | 11 | 4 | 7 | -1.000 | 36.4% | 15.2%-64.6% | 0.58 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `GBP_USD` | 8 | 2 | 6 | -2.538 | 25.0% | 7.1%-59.1% | 0.29 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `three_bar_reversal` | `USD_JPY` | 28 | 13 | 15 | -0.111 | 46.4% | 29.5%-64.2% | 0.95 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `AUD_JPY` | 5 | 2 | 3 | -3.840 | 40.0% | 11.8%-76.9% | 0.40 | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `EUR_JPY` | 5 | 0 | 5 | -9.040 | 0.0% | 0.0%-43.4% | 0.00 | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `USD_JPY` | 3 | 0 | 3 | -6.000 | 0.0% | 0.0%-56.2% | 0.00 | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_range_breakout_up` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_RANGE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trend_rebound` | `EUR_USD` | 17 | 6 | 11 | -0.241 | 35.3% | 17.3%-58.7% | 0.84 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `GBP_USD` | 1 | 1 | 0 | +6.400 | 100.0% | 20.7%-100.0% | n/a | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `USD_JPY` | 9 | 3 | 6 | -2.156 | 33.3% | 12.1%-64.6% | 0.11 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trendline_sweep` | `EUR_GBP` | 7 | 1 | 6 | -4.286 | 14.3% | 2.6%-51.3% | 0.07 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trendline_sweep` | `EUR_USD` | 8 | 4 | 4 | +0.788 | 50.0% | 21.5%-78.5% | 1.19 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `GBP_USD` | 27 | 15 | 12 | -2.689 | 55.6% | 37.3%-72.4% | 0.30 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `turtle_soup` | `GBP_USD` | 5 | 4 | 1 | -0.300 | 80.0% | 37.6%-96.4% | 0.78 | `TURTLE_SOUP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tvsm` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TVSM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `v_reversal` | `USD_JPY` | 7 | 4 | 3 | -0.243 | 57.1% | 25.0%-84.2% | 0.88 | `V_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vbp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `VBP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `EUR_JPY` | 1 | 1 | 0 | +9.300 | 100.0% | 20.7%-100.0% | n/a | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `USD_JPY` | 1 | 0 | 1 | -2.500 | 0.0% | 0.0%-79.3% | 0.00 | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_momentum_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `EUR_USD` | 21 | 3 | 18 | -2.129 | 14.3% | 5.0%-34.6% | 0.23 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `GBP_USD` | 7 | 4 | 3 | +0.629 | 57.1% | 25.0%-84.2% | 1.48 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `USD_JPY` | 8 | 4 | 4 | -2.025 | 50.0% | 21.5%-78.5% | 0.45 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `AUD_JPY` | 5 | 4 | 1 | -1.160 | 80.0% | 37.6%-96.4% | 0.71 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_GBP` | 8 | 2 | 6 | -0.837 | 25.0% | 7.1%-59.1% | 0.64 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_JPY` | 4 | 3 | 1 | +1.775 | 75.0% | 30.1%-95.4% | 1.77 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_USD` | 2 | 0 | 2 | -4.450 | 0.0% | 0.0%-65.8% | 0.00 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_JPY` | 1 | 1 | 0 | +11.200 | 100.0% | 20.7%-100.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_USD` | 3 | 2 | 1 | +2.433 | 66.7% | 20.8%-93.9% | 2.43 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `USD_JPY` | 2 | 0 | 2 | -4.100 | 0.0% | 0.0%-65.8% | 0.00 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `wick_imbalance_reversion` | `AUD_JPY` | 56 | 31 | 25 | -1.202 | 55.4% | 42.4%-67.6% | 0.73 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `EUR_JPY` | 16 | 8 | 8 | -2.775 | 50.0% | 28.0%-72.0% | 0.54 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `EUR_USD` | 13 | 4 | 9 | -3.023 | 30.8% | 12.7%-57.6% | 0.34 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `GBP_JPY` | 16 | 10 | 6 | -1.881 | 62.5% | 38.6%-81.5% | 0.69 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `GBP_USD` | 25 | 8 | 17 | -3.080 | 32.0% | 17.2%-51.6% | 0.18 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `USD_JPY` | 24 | 17 | 7 | +2.292 | 70.8% | 50.8%-85.1% | 2.02 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `xs_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
