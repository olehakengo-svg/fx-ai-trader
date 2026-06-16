# SHADOW_PROMOTE R2 Alert - 2026-06-16T11:07:29.444390+00:00

- Source: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=2000`
- Lookback: `30d`
- Filters: `is_shadow=1`, `pnl_pips IS NOT NULL`, `dedup_violation != 1`, XAU instruments excluded
- Gate: `N >= 10 and EV < 0` -> WARN; `N >= 30 and EV < 0` -> CRITICAL
- Mode: read-only; no env vars, strategy code, tier-master, or DB writes

## Summary

- Promoted strategies: 66
- Cells: 131
- OK: 104
- WARN: 17
- CRITICAL: 10

## WARN / CRITICAL

| Severity | Strategy | Instrument | N | EV | WR | Wilson lower | PF |
|---|---|---|---:|---:|---:|---:|---:|
| **WARN** | `dt_bb_rsi_mr` | `GBP_USD` | 11 | -2.091 | 45.5% | 21.3% | 0.39 |
| **WARN** | `dt_sr_channel_reversal` | `EUR_GBP` | 10 | -2.500 | 20.0% | 5.7% | 0.13 |
| **WARN** | `dt_sr_channel_reversal` | `EUR_JPY` | 12 | -3.700 | 50.0% | 25.4% | 0.27 |
| **WARN** | `dt_sr_channel_reversal` | `GBP_JPY` | 19 | -9.200 | 26.3% | 11.8% | 0.11 |
| **WARN** | `dt_sr_channel_reversal` | `GBP_USD` | 11 | -2.755 | 45.5% | 21.3% | 0.23 |
| **CRITICAL** | `ema_trend_scalp` | `USD_CHF` | 32 | -2.519 | 6.2% | 1.7% | 0.05 |
| **CRITICAL** | `engulfing_bb` | `EUR_USD` | 42 | -0.943 | 35.7% | 23.0% | 0.53 |
| **WARN** | `engulfing_bb` | `GBP_USD` | 26 | -2.981 | 26.9% | 13.7% | 0.15 |
| **WARN** | `london_breakout` | `EUR_USD` | 25 | -0.224 | 48.0% | 30.0% | 0.87 |
| **WARN** | `london_breakout` | `GBP_USD` | 18 | -1.267 | 44.4% | 24.6% | 0.50 |
| **WARN** | `london_breakout` | `USD_CHF` | 11 | -3.282 | 27.3% | 9.7% | 0.14 |
| **CRITICAL** | `ma_regime_switch` | `USD_JPY` | 53 | -0.840 | 34.0% | 22.7% | 0.46 |
| **WARN** | `sr_break_retest` | `EUR_JPY` | 25 | -2.196 | 64.0% | 44.5% | 0.41 |
| **CRITICAL** | `sr_break_retest` | `GBP_JPY` | 41 | -5.478 | 48.8% | 34.3% | 0.27 |
| **CRITICAL** | `sr_break_retest` | `GBP_USD` | 36 | -3.839 | 33.3% | 20.2% | 0.27 |
| **WARN** | `sr_break_retest` | `USD_JPY` | 16 | -0.975 | 68.8% | 44.4% | 0.56 |
| **CRITICAL** | `sr_channel_reversal` | `GBP_USD` | 94 | -0.539 | 48.9% | 39.1% | 0.76 |
| **CRITICAL** | `sr_channel_reversal` | `USD_CHF` | 30 | -0.660 | 23.3% | 11.8% | 0.60 |
| **WARN** | `sr_fib_confluence` | `GBP_USD` | 17 | -1.365 | 47.1% | 26.2% | 0.60 |
| **WARN** | `trendline_sweep` | `EUR_GBP` | 14 | -2.471 | 57.1% | 32.6% | 0.30 |
| **CRITICAL** | `vol_momentum_scalp` | `GBP_USD` | 31 | -1.803 | 35.5% | 21.1% | 0.38 |
| **WARN** | `vol_surge_detector` | `EUR_USD` | 16 | -1.444 | 37.5% | 18.5% | 0.23 |
| **WARN** | `wick_imbalance_reversion` | `GBP_USD` | 12 | -1.133 | 41.7% | 19.3% | 0.55 |
| **WARN** | `wick_imbalance_reversion` | `USD_JPY` | 10 | -3.030 | 60.0% | 31.3% | 0.32 |
| **CRITICAL** | `xs_momentum` | `EUR_USD` | 33 | -0.758 | 57.6% | 40.8% | 0.78 |
| **CRITICAL** | `xs_momentum` | `GBP_USD` | 31 | -1.255 | 64.5% | 46.9% | 0.64 |
| **WARN** | `xs_momentum` | `USD_JPY` | 19 | -1.758 | 52.6% | 31.7% | 0.53 |

## R2 Demote Manual Action

For each CRITICAL cell, manually verify and then remove the relevant Render env var:

- `ema_trend_scalp` x `USD_CHF`: remove `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE`
- `engulfing_bb` x `EUR_USD`: remove `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE`
- `ma_regime_switch` x `USD_JPY`: remove `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `GBP_JPY`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `GBP_USD`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_channel_reversal` x `GBP_USD`: remove `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_channel_reversal` x `USD_CHF`: remove `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`
- `vol_momentum_scalp` x `GBP_USD`: remove `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`, `VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE`
- `xs_momentum` x `EUR_USD`: remove `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`
- `xs_momentum` x `GBP_USD`: remove `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`

Code review locations if manual demotion is chosen:
- `strategies/daytrade/__init__.py` `split_shadow_always` / `SHADOW_ALWAYS_STRATEGIES`
- `strategies/hourly/__init__.py` `split_shadow_always`
- `strategies/scalp/__init__.py` `split_shadow_always`

## Apply Demote Suggestion

- Registry: `/home/runner/work/fx-ai-trader/fx-ai-trader/modules/shadow_demote_registry.py`
- Missing CRITICAL cells: `10`
- Add `('ema_trend_scalp', 'USD_CHF')`
- Add `('engulfing_bb', 'EUR_USD')`
- Add `('ma_regime_switch', 'USD_JPY')`
- Add `('sr_break_retest', 'GBP_JPY')`
- Add `('sr_break_retest', 'GBP_USD')`
- Add `('sr_channel_reversal', 'GBP_USD')`
- Add `('sr_channel_reversal', 'USD_CHF')`
- Add `('vol_momentum_scalp', 'GBP_USD')`
- Add `('xs_momentum', 'EUR_USD')`
- Add `('xs_momentum', 'GBP_USD')`

## All Cells

| Severity | Strategy | Instrument | N | Wins | Losses | EV | WR | Wilson 95% | PF | Env |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| OK | `adx_trend_continuation` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ADX_TREND_CONTINUATION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `asia_range_fade_v1` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ASIA_RANGE_FADE_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `atr_regime_break` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ALPHA_ATR_REGIME_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_rsi_ema_aligned` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `BB_RSI_EMA_ALIGNED_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_rsi_reversion` | `EUR_USD` | 2 | 0 | 2 | -3.350 | 0.0% | 0.0%-65.8% | 0.00 | `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_rsi_reversion` | `USD_CHF` | 6 | 0 | 6 | -1.900 | 0.0% | 0.0%-39.0% | 0.00 | `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_rsi_reversion` | `USD_JPY` | 3 | 0 | 3 | -3.633 | 0.0% | 0.0%-56.2% | 0.00 | `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `confluence_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CONFLUENCE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `cpd_divergence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CPD_DIVERGENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `AUD_JPY` | 5 | 1 | 4 | -7.260 | 20.0% | 3.6%-62.4% | 0.04 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `AUD_USD` | 2 | 1 | 1 | -4.500 | 50.0% | 9.5%-90.5% | 0.49 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `NZD_USD` | 1 | 1 | 0 | +1.700 | 100.0% | 20.7%-100.0% | n/a | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `USD_JPY` | 1 | 0 | 1 | -11.500 | 0.0% | 0.0%-79.3% | 0.00 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `EUR_USD` | 12 | 8 | 4 | +2.742 | 66.7% | 39.1%-86.2% | 2.70 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_bb_rsi_mr` | `GBP_USD` | 11 | 5 | 6 | -2.091 | 45.5% | 21.3%-72.0% | 0.39 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `USD_JPY` | 2 | 1 | 1 | -2.950 | 50.0% | 9.5%-90.5% | 0.12 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_GBP` | 10 | 2 | 8 | -2.500 | 20.0% | 5.7%-51.0% | 0.13 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_JPY` | 12 | 6 | 6 | -3.700 | 50.0% | 25.4%-74.6% | 0.27 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `EUR_USD` | 19 | 12 | 7 | +0.605 | 63.2% | 41.0%-80.9% | 1.24 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `GBP_JPY` | 19 | 5 | 14 | -9.200 | 26.3% | 11.8%-48.8% | 0.11 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `GBP_USD` | 11 | 5 | 6 | -2.755 | 45.5% | 21.3%-72.0% | 0.23 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `USD_JPY` | 9 | 5 | 4 | +0.911 | 55.6% | 26.7%-81.1% | 1.52 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema200_trend_reversal` | `USD_JPY` | 9 | 7 | 2 | +0.267 | 77.8% | 45.3%-93.7% | 1.37 | `EMA200_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`<br>`EMA200_TREND_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_ribbon_ride` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_RIBBON_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `ema_trend_scalp` | `USD_CHF` | 32 | 2 | 30 | -2.519 | 6.2% | 1.7%-20.1% | 0.05 | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `engulfing_bb` | `EUR_USD` | 42 | 15 | 27 | -0.943 | 35.7% | 23.0%-50.8% | 0.53 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `engulfing_bb` | `GBP_USD` | 26 | 7 | 19 | -2.981 | 26.9% | 13.7%-46.1% | 0.15 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `engulfing_bb` | `USD_CHF` | 3 | 0 | 3 | -1.733 | 0.0% | 0.0%-56.2% | 0.00 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_pips_hunter` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_PIPS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_trend_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_TREND_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_vol_break` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_VOL_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `EUR_JPY` | 1 | 0 | 1 | -15.400 | 0.0% | 0.0%-79.3% | 0.00 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_JPY` | 1 | 1 | 0 | +2.600 | 100.0% | 20.7%-100.0% | n/a | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_USD` | 2 | 2 | 0 | +1.700 | 100.0% | 34.2%-100.0% | n/a | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `EUR_USD` | 1 | 1 | 0 | +21.100 | 100.0% | 20.7%-100.0% | n/a | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `GBP_USD` | 2 | 2 | 0 | +1.650 | 100.0% | 34.2%-100.0% | n/a | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `USD_JPY` | 2 | 2 | 0 | +1.300 | 100.0% | 34.2%-100.0% | n/a | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `intraday_seasonality` | `EUR_GBP` | 2 | 1 | 1 | -3.200 | 50.0% | 9.5%-90.5% | 0.24 | `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `intraday_seasonality` | `GBP_USD` | 2 | 1 | 1 | -1.400 | 50.0% | 9.5%-90.5% | 0.77 | `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `jpy_basket_trend` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `JPY_BASKET_TREND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `keltner_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `lin_reg_channel` | `EUR_USD` | 7 | 3 | 4 | -2.643 | 42.9% | 15.8%-75.0% | 0.33 | `LIN_REG_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `london_breakout` | `EUR_USD` | 25 | 12 | 13 | -0.224 | 48.0% | 30.0%-66.5% | 0.87 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `london_breakout` | `GBP_USD` | 18 | 8 | 10 | -1.267 | 44.4% | 24.6%-66.3% | 0.50 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `london_breakout` | `USD_CHF` | 11 | 3 | 8 | -3.282 | 27.3% | 9.7%-56.6% | 0.14 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_breakout` | `USD_JPY` | 3 | 0 | 3 | -2.800 | 0.0% | 0.0%-56.2% | 0.00 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_ny_swing` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_NY_SWING_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `EUR_USD` | 1 | 1 | 0 | +1.800 | 100.0% | 20.7%-100.0% | n/a | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `GBP_USD` | 2 | 2 | 0 | +2.100 | 100.0% | 34.2%-100.0% | n/a | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_shrapnel` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_SHRAPNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_mr_hybrid` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_MR_HYBRID_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `ma_regime_switch` | `USD_JPY` | 53 | 18 | 35 | -0.840 | 34.0% | 22.7%-47.4% | 0.46 | `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_trend_perfect` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_TREND_PERFECT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `GBP_USD` | 1 | 1 | 0 | +2.100 | 100.0% | 20.7%-100.0% | n/a | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `USD_JPY` | 1 | 0 | 1 | -8.500 | 0.0% | 0.0%-79.3% | 0.00 | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `EUR_USD` | 1 | 1 | 0 | +1.800 | 100.0% | 20.7%-100.0% | n/a | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `USD_JPY` | 3 | 0 | 3 | -1.267 | 0.0% | 0.0%-56.2% | 0.00 | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_regime_range_cascade_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `GBP_USD` | 1 | 1 | 0 | +2.100 | 100.0% | 20.7%-100.0% | n/a | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `USD_JPY` | 1 | 1 | 0 | +1.500 | 100.0% | 20.7%-100.0% | n/a | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `EUR_USD` | 8 | 1 | 7 | -1.300 | 12.5% | 2.2%-47.1% | 0.15 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `GBP_JPY` | 1 | 1 | 0 | +2.000 | 100.0% | 20.7%-100.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `USD_JPY` | 19 | 13 | 6 | +0.279 | 68.4% | 46.0%-84.6% | 1.17 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ofi_mr` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `OFI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `EUR_USD` | 3 | 1 | 2 | +0.133 | 33.3% | 6.1%-79.2% | 1.05 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `GBP_USD` | 3 | 3 | 0 | +9.867 | 100.0% | 43.8%-100.0% | n/a | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `USD_JPY` | 1 | 0 | 1 | -7.600 | 0.0% | 0.0%-79.3% | 0.00 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `post_news_vol` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `EUR_USD` | 5 | 1 | 4 | -4.440 | 20.0% | 3.6%-62.4% | 0.07 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `GBP_USD` | 1 | 1 | 0 | +2.000 | 100.0% | 20.7%-100.0% | n/a | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `session_vol_expansion` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SESSION_VOL_EXPANSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `squeeze_release_momentum` | `EUR_USD` | 9 | 3 | 6 | -2.711 | 33.3% | 12.1%-64.6% | 0.30 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `squeeze_release_momentum` | `GBP_USD` | 4 | 4 | 0 | +3.675 | 100.0% | 51.0%-100.0% | n/a | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `EUR_JPY` | 2 | 0 | 2 | -15.000 | 0.0% | 0.0%-65.8% | 0.00 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `EUR_USD` | 3 | 3 | 0 | +5.433 | 100.0% | 43.8%-100.0% | n/a | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_JPY` | 5 | 5 | 0 | +3.260 | 100.0% | 56.6%-100.0% | n/a | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_USD` | 1 | 0 | 1 | -51.300 | 0.0% | 0.0%-79.3% | 0.00 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `USD_JPY` | 2 | 2 | 0 | +1.750 | 100.0% | 34.2%-100.0% | n/a | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_break_retest` | `EUR_JPY` | 25 | 16 | 9 | -2.196 | 64.0% | 44.5%-79.8% | 0.41 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `GBP_JPY` | 41 | 20 | 21 | -5.478 | 48.8% | 34.3%-63.5% | 0.27 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `GBP_USD` | 36 | 12 | 24 | -3.839 | 33.3% | 20.2%-49.7% | 0.27 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_break_retest` | `USD_JPY` | 16 | 11 | 5 | -0.975 | 68.8% | 44.4%-85.8% | 0.56 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_channel_reversal` | `GBP_USD` | 94 | 46 | 48 | -0.539 | 48.9% | 39.1%-58.9% | 0.76 | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_channel_reversal` | `USD_CHF` | 30 | 7 | 23 | -0.660 | 23.3% | 11.8%-40.9% | 0.60 | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_fib_confluence` | `EUR_GBP` | 3 | 1 | 2 | -1.333 | 33.3% | 6.1%-79.2% | 0.33 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_fib_confluence` | `EUR_USD` | 24 | 17 | 7 | +2.254 | 70.8% | 50.8%-85.1% | 2.29 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_fib_confluence` | `GBP_USD` | 17 | 8 | 9 | -1.365 | 47.1% | 26.2%-69.0% | 0.60 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_liquidity_grab` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_LIQUIDITY_GRAB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `stoch_trend_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `EUR_USD` | 5 | 1 | 4 | -1.960 | 20.0% | 3.6%-62.4% | 0.08 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `GBP_USD` | 6 | 2 | 4 | -3.000 | 33.3% | 9.7%-70.0% | 0.16 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `USD_CHF` | 2 | 0 | 2 | -2.750 | 0.0% | 0.0%-65.8% | 0.00 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_range_breakout_up` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_RANGE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `EUR_USD` | 2 | 0 | 2 | -4.250 | 0.0% | 0.0%-65.8% | 0.00 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `GBP_USD` | 1 | 0 | 1 | -3.900 | 0.0% | 0.0%-79.3% | 0.00 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `USD_JPY` | 5 | 1 | 4 | -2.760 | 20.0% | 3.6%-62.4% | 0.11 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `EUR_GBP` | 14 | 8 | 6 | -2.471 | 57.1% | 32.6%-78.6% | 0.30 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trendline_sweep` | `EUR_USD` | 9 | 8 | 1 | +4.344 | 88.9% | 56.5%-98.0% | 4.40 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trendline_sweep` | `GBP_USD` | 8 | 3 | 5 | -6.850 | 37.5% | 13.7%-69.4% | 0.11 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `turtle_soup` | `GBP_USD` | 5 | 3 | 2 | -2.680 | 60.0% | 23.1%-88.2% | 0.26 | `TURTLE_SOUP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tvsm` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TVSM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `v_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `V_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vbp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `VBP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `GBP_JPY` | 1 | 1 | 0 | +2.000 | 100.0% | 20.7%-100.0% | n/a | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `USD_JPY` | 3 | 3 | 0 | +9.967 | 100.0% | 43.8%-100.0% | n/a | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `vol_momentum_scalp` | `GBP_USD` | 31 | 11 | 20 | -1.803 | 35.5% | 21.1%-53.1% | 0.38 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_momentum_scalp` | `USD_JPY` | 9 | 3 | 6 | -1.033 | 33.3% | 12.1%-64.6% | 0.37 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `EUR_USD` | 16 | 6 | 10 | -1.444 | 37.5% | 18.5%-61.4% | 0.23 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `GBP_USD` | 5 | 1 | 4 | -3.100 | 20.0% | 3.6%-62.4% | 0.07 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `USD_CHF` | 4 | 0 | 4 | -7.150 | 0.0% | 0.0%-49.0% | 0.00 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `USD_JPY` | 4 | 1 | 3 | -2.500 | 25.0% | 4.6%-69.9% | 0.07 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_GBP` | 3 | 1 | 2 | -2.833 | 33.3% | 6.1%-79.2% | 0.24 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_JPY` | 2 | 0 | 2 | -20.650 | 0.0% | 0.0%-65.8% | 0.00 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_USD` | 1 | 1 | 0 | +0.800 | 100.0% | 20.7%-100.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_JPY` | 1 | 1 | 0 | +8.400 | 100.0% | 20.7%-100.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_USD` | 1 | 1 | 0 | +2.300 | 100.0% | 20.7%-100.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `USD_JPY` | 3 | 1 | 2 | -8.033 | 33.3% | 6.1%-79.2% | 0.06 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_GBP` | 1 | 0 | 1 | -3.100 | 0.0% | 0.0%-79.3% | 0.00 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_JPY` | 6 | 4 | 2 | -0.767 | 66.7% | 30.0%-90.3% | 0.68 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_USD` | 3 | 2 | 1 | +0.867 | 66.7% | 20.8%-93.9% | 3.89 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `GBP_JPY` | 5 | 2 | 3 | -6.860 | 40.0% | 11.8%-76.9% | 0.14 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `GBP_USD` | 12 | 5 | 7 | -1.133 | 41.7% | 19.3%-68.0% | 0.55 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `USD_JPY` | 10 | 6 | 4 | -3.030 | 60.0% | 31.3%-83.2% | 0.32 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `EUR_USD` | 33 | 19 | 14 | -0.758 | 57.6% | 40.8%-72.8% | 0.78 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `GBP_USD` | 31 | 20 | 11 | -1.255 | 64.5% | 46.9%-78.9% | 0.64 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `xs_momentum` | `USD_JPY` | 19 | 10 | 9 | -1.758 | 52.6% | 31.7%-72.7% | 0.53 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
