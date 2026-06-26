# SHADOW_PROMOTE R2 Alert - 2026-06-26T09:22:10.375080+00:00

- Source: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=2000`
- Lookback: `30d`
- Filters: `is_shadow=1`, `pnl_pips IS NOT NULL`, `dedup_violation != 1`, XAU instruments excluded
- Gate: `N >= 10 and EV < 0` -> WARN; `N >= 30 and EV < 0` -> CRITICAL
- Mode: read-only; no env vars, strategy code, tier-master, or DB writes

## Summary

- Promoted strategies: 66
- Cells: 128
- OK: 100
- WARN: 18
- CRITICAL: 10

## WARN / CRITICAL

| Severity | Strategy | Instrument | N | EV | WR | Wilson lower | PF |
|---|---|---|---:|---:|---:|---:|---:|
| **WARN** | `dt_sr_channel_reversal` | `EUR_GBP` | 11 | -3.218 | 9.1% | 1.6% | 0.06 |
| **WARN** | `dt_sr_channel_reversal` | `EUR_JPY` | 17 | -5.571 | 41.2% | 21.6% | 0.14 |
| **CRITICAL** | `dt_sr_channel_reversal` | `GBP_JPY` | 34 | -3.097 | 52.9% | 36.7% | 0.48 |
| **WARN** | `dt_sr_channel_reversal` | `GBP_USD` | 16 | -1.037 | 68.8% | 44.4% | 0.57 |
| **WARN** | `dt_sr_channel_reversal` | `USD_JPY` | 14 | -0.543 | 50.0% | 26.8% | 0.80 |
| **WARN** | `ema200_trend_reversal` | `USD_JPY` | 11 | -0.091 | 63.6% | 35.4% | 0.96 |
| **CRITICAL** | `engulfing_bb` | `EUR_USD` | 87 | -1.036 | 39.1% | 29.5% | 0.50 |
| **CRITICAL** | `engulfing_bb` | `GBP_USD` | 42 | -0.376 | 47.6% | 33.4% | 0.82 |
| **WARN** | `lin_reg_channel` | `EUR_USD` | 12 | -4.033 | 33.3% | 13.8% | 0.12 |
| **WARN** | `london_breakout` | `USD_CHF` | 21 | -2.305 | 28.6% | 13.8% | 0.20 |
| **CRITICAL** | `ma_regime_switch` | `USD_JPY` | 54 | -1.307 | 35.2% | 23.8% | 0.35 |
| **WARN** | `squeeze_release_momentum` | `EUR_USD` | 16 | -3.100 | 37.5% | 18.5% | 0.16 |
| **WARN** | `squeeze_release_momentum` | `GBP_USD` | 13 | -0.431 | 69.2% | 42.4% | 0.81 |
| **CRITICAL** | `sr_break_retest` | `EUR_JPY` | 45 | -1.418 | 71.1% | 56.6% | 0.58 |
| **CRITICAL** | `sr_break_retest` | `GBP_JPY` | 42 | -3.245 | 61.9% | 46.8% | 0.43 |
| **CRITICAL** | `sr_break_retest` | `GBP_USD` | 41 | -1.849 | 53.7% | 38.7% | 0.51 |
| **CRITICAL** | `sr_channel_reversal` | `GBP_USD` | 49 | -0.698 | 46.9% | 33.7% | 0.71 |
| **WARN** | `trendline_sweep` | `EUR_GBP` | 14 | -1.893 | 57.1% | 32.6% | 0.36 |
| **WARN** | `trendline_sweep` | `EUR_USD` | 14 | -0.364 | 71.4% | 45.4% | 0.88 |
| **WARN** | `trendline_sweep` | `GBP_USD` | 14 | -2.386 | 64.3% | 38.8% | 0.29 |
| **CRITICAL** | `vol_momentum_scalp` | `GBP_USD` | 37 | -3.392 | 24.3% | 13.4% | 0.15 |
| **WARN** | `vol_surge_detector` | `EUR_USD` | 16 | -1.025 | 50.0% | 28.0% | 0.44 |
| **WARN** | `vol_surge_detector` | `GBP_USD` | 10 | -2.240 | 30.0% | 10.8% | 0.20 |
| **WARN** | `vol_surge_detector` | `USD_JPY` | 10 | -0.230 | 60.0% | 31.3% | 0.83 |
| **WARN** | `wick_imbalance_reversion` | `EUR_JPY` | 10 | -5.490 | 30.0% | 10.8% | 0.22 |
| **WARN** | `wick_imbalance_reversion` | `GBP_JPY` | 14 | -5.436 | 50.0% | 26.8% | 0.27 |
| **WARN** | `xs_momentum` | `EUR_USD` | 25 | -4.996 | 40.0% | 23.4% | 0.21 |
| **CRITICAL** | `xs_momentum` | `GBP_USD` | 30 | -4.053 | 56.7% | 39.2% | 0.28 |

## R2 Demote Manual Action

For each CRITICAL cell, manually verify and then remove the relevant Render env var:

- `dt_sr_channel_reversal` x `GBP_JPY`: remove `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE`
- `engulfing_bb` x `EUR_USD`: remove `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE`
- `engulfing_bb` x `GBP_USD`: remove `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE`
- `ma_regime_switch` x `USD_JPY`: remove `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `EUR_JPY`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `GBP_JPY`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `GBP_USD`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_channel_reversal` x `GBP_USD`: remove `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`
- `vol_momentum_scalp` x `GBP_USD`: remove `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`, `VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE`
- `xs_momentum` x `GBP_USD`: remove `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`

Code review locations if manual demotion is chosen:
- `strategies/daytrade/__init__.py` `split_shadow_always` / `SHADOW_ALWAYS_STRATEGIES`
- `strategies/hourly/__init__.py` `split_shadow_always`
- `strategies/scalp/__init__.py` `split_shadow_always`

## Apply Demote Suggestion

- Registry: `/home/runner/work/fx-ai-trader/fx-ai-trader/modules/shadow_demote_registry.py`
- Missing CRITICAL cells: `10`
- Add `('dt_sr_channel_reversal', 'GBP_JPY')`
- Add `('engulfing_bb', 'EUR_USD')`
- Add `('engulfing_bb', 'GBP_USD')`
- Add `('ma_regime_switch', 'USD_JPY')`
- Add `('sr_break_retest', 'EUR_JPY')`
- Add `('sr_break_retest', 'GBP_JPY')`
- Add `('sr_break_retest', 'GBP_USD')`
- Add `('sr_channel_reversal', 'GBP_USD')`
- Add `('vol_momentum_scalp', 'GBP_USD')`
- Add `('xs_momentum', 'GBP_USD')`

## All Cells

| Severity | Strategy | Instrument | N | Wins | Losses | EV | WR | Wilson 95% | PF | Env |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| OK | `adx_trend_continuation` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ADX_TREND_CONTINUATION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `asia_range_fade_v1` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ASIA_RANGE_FADE_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `atr_regime_break` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ALPHA_ATR_REGIME_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_rsi_ema_aligned` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `BB_RSI_EMA_ALIGNED_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_rsi_reversion` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `confluence_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CONFLUENCE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `cpd_divergence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CPD_DIVERGENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `AUD_JPY` | 5 | 2 | 3 | -11.360 | 40.0% | 11.8%-76.9% | 0.05 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `AUD_USD` | 3 | 1 | 2 | -9.133 | 33.3% | 6.1%-79.2% | 0.24 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `EUR_USD` | 1 | 0 | 1 | -23.700 | 0.0% | 0.0%-79.3% | 0.00 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `NZD_USD` | 1 | 1 | 0 | +1.700 | 100.0% | 20.7%-100.0% | n/a | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `USD_JPY` | 2 | 1 | 1 | +0.200 | 50.0% | 9.5%-90.5% | 2.00 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `EUR_USD` | 14 | 7 | 7 | +0.907 | 50.0% | 26.8%-73.2% | 1.33 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `GBP_USD` | 9 | 4 | 5 | -0.133 | 44.4% | 18.9%-73.3% | 0.96 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `USD_JPY` | 2 | 1 | 1 | -2.950 | 50.0% | 9.5%-90.5% | 0.12 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_GBP` | 11 | 1 | 10 | -3.218 | 9.1% | 1.6%-37.7% | 0.06 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_JPY` | 17 | 7 | 10 | -5.571 | 41.2% | 21.6%-64.0% | 0.14 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `EUR_USD` | 19 | 16 | 3 | +1.374 | 84.2% | 62.4%-94.5% | 2.18 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `dt_sr_channel_reversal` | `GBP_JPY` | 34 | 18 | 16 | -3.097 | 52.9% | 36.7%-68.5% | 0.48 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `GBP_USD` | 16 | 11 | 5 | -1.037 | 68.8% | 44.4%-85.8% | 0.57 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `USD_JPY` | 14 | 7 | 7 | -0.543 | 50.0% | 26.8%-73.2% | 0.80 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `ema200_trend_reversal` | `USD_JPY` | 11 | 7 | 4 | -0.091 | 63.6% | 35.4%-84.8% | 0.96 | `EMA200_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`<br>`EMA200_TREND_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_ribbon_ride` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_RIBBON_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_trend_scalp` | `USD_CHF` | 5 | 0 | 5 | -4.320 | 0.0% | 0.0%-43.4% | 0.00 | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `engulfing_bb` | `EUR_USD` | 87 | 34 | 53 | -1.036 | 39.1% | 29.5%-49.6% | 0.50 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `engulfing_bb` | `GBP_USD` | 42 | 20 | 22 | -0.376 | 47.6% | 33.4%-62.3% | 0.82 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `engulfing_bb` | `USD_CHF` | 2 | 0 | 2 | -2.550 | 0.0% | 0.0%-65.8% | 0.00 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_pips_hunter` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_PIPS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_trend_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_TREND_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_vol_break` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_VOL_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `EUR_JPY` | 4 | 2 | 2 | -4.575 | 50.0% | 15.0%-85.0% | 0.21 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_JPY` | 1 | 1 | 0 | +2.200 | 100.0% | 20.7%-100.0% | n/a | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_USD` | 2 | 2 | 0 | +1.700 | 100.0% | 34.2%-100.0% | n/a | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `EUR_USD` | 2 | 2 | 0 | +11.450 | 100.0% | 34.2%-100.0% | n/a | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `GBP_USD` | 4 | 4 | 0 | +2.075 | 100.0% | 51.0%-100.0% | n/a | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `USD_JPY` | 2 | 2 | 0 | +1.750 | 100.0% | 34.2%-100.0% | n/a | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `intraday_seasonality` | `EUR_GBP` | 3 | 3 | 0 | +8.667 | 100.0% | 43.8%-100.0% | n/a | `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `intraday_seasonality` | `GBP_USD` | 1 | 1 | 0 | +9.500 | 100.0% | 20.7%-100.0% | n/a | `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `jpy_basket_trend` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `JPY_BASKET_TREND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `keltner_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `lin_reg_channel` | `EUR_USD` | 12 | 4 | 8 | -4.033 | 33.3% | 13.8%-60.9% | 0.12 | `LIN_REG_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_breakout` | `EUR_USD` | 42 | 22 | 20 | +0.310 | 52.4% | 37.7%-66.6% | 1.16 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_breakout` | `GBP_USD` | 53 | 32 | 21 | +0.064 | 60.4% | 46.9%-72.4% | 1.03 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `london_breakout` | `USD_CHF` | 21 | 6 | 15 | -2.305 | 28.6% | 13.8%-50.0% | 0.20 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_breakout` | `USD_JPY` | 4 | 2 | 2 | -1.300 | 50.0% | 15.0%-85.0% | 0.33 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_ny_swing` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_NY_SWING_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `EUR_USD` | 2 | 2 | 0 | +9.400 | 100.0% | 34.2%-100.0% | n/a | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `GBP_USD` | 2 | 2 | 0 | +1.750 | 100.0% | 34.2%-100.0% | n/a | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_shrapnel` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_SHRAPNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_mr_hybrid` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_MR_HYBRID_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `ma_regime_switch` | `USD_JPY` | 54 | 19 | 35 | -1.307 | 35.2% | 23.8%-48.5% | 0.35 | `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_trend_perfect` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_TREND_PERFECT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `GBP_USD` | 1 | 1 | 0 | +2.100 | 100.0% | 20.7%-100.0% | n/a | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `USD_JPY` | 1 | 0 | 1 | -8.500 | 0.0% | 0.0%-79.3% | 0.00 | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `USD_JPY` | 1 | 0 | 1 | -3.100 | 0.0% | 0.0%-79.3% | 0.00 | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_regime_range_cascade_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `GBP_USD` | 1 | 1 | 0 | +2.100 | 100.0% | 20.7%-100.0% | n/a | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `USD_JPY` | 1 | 1 | 0 | +1.500 | 100.0% | 20.7%-100.0% | n/a | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `EUR_JPY` | 2 | 2 | 0 | +2.150 | 100.0% | 34.2%-100.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `EUR_USD` | 1 | 1 | 0 | +11.400 | 100.0% | 20.7%-100.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `GBP_JPY` | 2 | 1 | 1 | -9.400 | 50.0% | 9.5%-90.5% | 0.10 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `GBP_USD` | 8 | 4 | 4 | -5.775 | 50.0% | 21.5%-78.5% | 0.15 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `USD_JPY` | 3 | 1 | 2 | -5.100 | 33.3% | 6.1%-79.2% | 0.11 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ofi_mr` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `OFI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `EUR_USD` | 5 | 3 | 2 | +0.660 | 60.0% | 23.1%-88.2% | 1.23 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `GBP_USD` | 1 | 1 | 0 | +10.300 | 100.0% | 20.7%-100.0% | n/a | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `post_news_vol` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `EUR_JPY` | 4 | 3 | 1 | -1.075 | 75.0% | 30.1%-95.4% | 0.61 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `EUR_USD` | 2 | 2 | 0 | +7.550 | 100.0% | 34.2%-100.0% | n/a | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `session_vol_expansion` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SESSION_VOL_EXPANSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `squeeze_release_momentum` | `EUR_USD` | 16 | 6 | 10 | -3.100 | 37.5% | 18.5%-61.4% | 0.16 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `squeeze_release_momentum` | `GBP_USD` | 13 | 9 | 4 | -0.431 | 69.2% | 42.4%-87.3% | 0.81 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `EUR_JPY` | 4 | 1 | 3 | -9.075 | 25.0% | 4.6%-69.9% | 0.05 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `EUR_USD` | 8 | 6 | 2 | -2.462 | 75.0% | 40.9%-92.9% | 0.58 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_JPY` | 8 | 6 | 2 | -1.575 | 75.0% | 40.9%-92.9% | 0.61 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_USD` | 5 | 2 | 3 | -3.520 | 40.0% | 11.8%-76.9% | 0.19 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `USD_JPY` | 4 | 2 | 2 | -1.500 | 50.0% | 15.0%-85.0% | 0.29 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `EUR_JPY` | 45 | 32 | 13 | -1.418 | 71.1% | 56.6%-82.3% | 0.58 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `GBP_JPY` | 42 | 26 | 16 | -3.245 | 61.9% | 46.8%-75.0% | 0.43 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `GBP_USD` | 41 | 22 | 19 | -1.849 | 53.7% | 38.7%-67.9% | 0.51 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_break_retest` | `USD_JPY` | 19 | 12 | 7 | +0.058 | 63.2% | 41.0%-80.9% | 1.02 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_channel_reversal` | `GBP_USD` | 49 | 23 | 26 | -0.698 | 46.9% | 33.7%-60.6% | 0.71 | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_channel_reversal` | `USD_CHF` | 15 | 6 | 9 | +0.387 | 40.0% | 19.8%-64.3% | 1.26 | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_fib_confluence` | `EUR_GBP` | 4 | 2 | 2 | -0.500 | 50.0% | 15.0%-85.0% | 0.67 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_fib_confluence` | `EUR_USD` | 8 | 4 | 4 | -2.800 | 50.0% | 21.5%-78.5% | 0.37 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_fib_confluence` | `GBP_USD` | 15 | 11 | 4 | +1.913 | 73.3% | 48.0%-89.1% | 2.33 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_liquidity_grab` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_LIQUIDITY_GRAB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `stoch_trend_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `EUR_USD` | 9 | 2 | 7 | -2.367 | 22.2% | 6.3%-54.7% | 0.10 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `GBP_USD` | 5 | 2 | 3 | -3.080 | 40.0% | 11.8%-76.9% | 0.17 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `USD_CHF` | 3 | 0 | 3 | -3.633 | 0.0% | 0.0%-56.2% | 0.00 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_range_breakout_up` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_RANGE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `EUR_USD` | 6 | 3 | 3 | -1.467 | 50.0% | 18.8%-81.2% | 0.27 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `USD_JPY` | 9 | 3 | 6 | -1.311 | 33.3% | 12.1%-64.6% | 0.28 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `EUR_GBP` | 14 | 8 | 6 | -1.893 | 57.1% | 32.6%-78.6% | 0.36 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `EUR_USD` | 14 | 10 | 4 | -0.364 | 71.4% | 45.4%-88.3% | 0.88 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `GBP_USD` | 14 | 9 | 5 | -2.386 | 64.3% | 38.8%-83.7% | 0.29 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `turtle_soup` | `GBP_USD` | 5 | 4 | 1 | -1.860 | 80.0% | 37.6%-96.4% | 0.42 | `TURTLE_SOUP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tvsm` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TVSM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `v_reversal` | `USD_JPY` | 7 | 2 | 5 | -3.614 | 28.6% | 8.2%-64.1% | 0.09 | `V_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vbp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `VBP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `USD_JPY` | 2 | 2 | 0 | +11.750 | 100.0% | 34.2%-100.0% | n/a | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `vol_momentum_scalp` | `GBP_USD` | 37 | 9 | 28 | -3.392 | 24.3% | 13.4%-40.1% | 0.15 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_momentum_scalp` | `USD_JPY` | 6 | 2 | 4 | +0.300 | 33.3% | 9.7%-70.0% | 1.22 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `EUR_USD` | 16 | 8 | 8 | -1.025 | 50.0% | 28.0%-72.0% | 0.44 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `GBP_USD` | 10 | 3 | 7 | -2.240 | 30.0% | 10.8%-60.3% | 0.20 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `USD_CHF` | 2 | 2 | 0 | +2.050 | 100.0% | 34.2%-100.0% | n/a | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `USD_JPY` | 10 | 6 | 4 | -0.230 | 60.0% | 31.3%-83.2% | 0.83 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_GBP` | 2 | 1 | 1 | -1.050 | 50.0% | 9.5%-90.5% | 0.43 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_JPY` | 4 | 2 | 2 | -9.400 | 50.0% | 15.0%-85.0% | 0.09 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_USD` | 2 | 1 | 1 | -3.450 | 50.0% | 9.5%-90.5% | 0.10 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_JPY` | 4 | 4 | 0 | +7.375 | 100.0% | 51.0%-100.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_USD` | 2 | 2 | 0 | +8.700 | 100.0% | 34.2%-100.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `USD_JPY` | 6 | 3 | 3 | -2.083 | 50.0% | 18.8%-81.2% | 0.56 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_GBP` | 1 | 0 | 1 | -3.100 | 0.0% | 0.0%-79.3% | 0.00 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `EUR_JPY` | 10 | 3 | 7 | -5.490 | 30.0% | 10.8%-60.3% | 0.22 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_USD` | 4 | 2 | 2 | -3.025 | 50.0% | 15.0%-85.0% | 0.12 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `GBP_JPY` | 14 | 7 | 7 | -5.436 | 50.0% | 26.8%-73.2% | 0.27 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `GBP_USD` | 8 | 2 | 6 | -3.787 | 25.0% | 7.1%-59.1% | 0.07 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `USD_JPY` | 6 | 4 | 2 | +1.450 | 66.7% | 30.0%-90.3% | 1.81 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `xs_momentum` | `EUR_USD` | 25 | 10 | 15 | -4.996 | 40.0% | 23.4%-59.3% | 0.21 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `GBP_USD` | 30 | 17 | 13 | -4.053 | 56.7% | 39.2%-72.6% | 0.28 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `xs_momentum` | `USD_JPY` | 7 | 6 | 1 | +3.529 | 85.7% | 48.7%-97.4% | 14.72 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
