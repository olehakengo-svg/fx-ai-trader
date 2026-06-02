# SHADOW_PROMOTE R2 Alert - 2026-06-02T20:46:43.452179+00:00

- Source: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=2000`
- Lookback: `30d`
- Filters: `is_shadow=1`, `pnl_pips IS NOT NULL`, XAU instruments excluded
- Gate: `N >= 10 and EV < 0` -> WARN; `N >= 30 and EV < 0` -> CRITICAL
- Mode: read-only; no env vars, strategy code, tier-master, or DB writes

## Summary

- Promoted strategies: 66
- Cells: 122
- OK: 89
- WARN: 17
- CRITICAL: 16

## WARN / CRITICAL

| Severity | Strategy | Instrument | N | EV | WR | Wilson lower | PF |
|---|---|---|---:|---:|---:|---:|---:|
| **CRITICAL** | `bb_rsi_reversion` | `USD_CHF` | 35 | -2.460 | 0.0% | 0.0% | 0.00 |
| **WARN** | `donchian_momentum_breakout` | `AUD_JPY` | 13 | -11.877 | 7.7% | 1.4% | 0.18 |
| **WARN** | `donchian_momentum_breakout` | `USD_CAD` | 11 | -9.045 | 27.3% | 9.7% | 0.23 |
| **CRITICAL** | `ema_trend_scalp` | `USD_CHF` | 65 | -1.885 | 3.1% | 0.8% | 0.22 |
| **CRITICAL** | `engulfing_bb` | `EUR_USD` | 34 | -0.738 | 26.5% | 14.6% | 0.68 |
| **WARN** | `engulfing_bb` | `GBP_USD` | 14 | -2.264 | 14.3% | 4.0% | 0.36 |
| **WARN** | `engulfing_bb` | `USD_CHF` | 10 | -1.430 | 0.0% | 0.0% | 0.00 |
| **WARN** | `london_breakout` | `EUR_USD` | 25 | -2.584 | 8.0% | 2.2% | 0.16 |
| **WARN** | `london_breakout` | `GBP_USD` | 12 | -2.183 | 16.7% | 4.7% | 0.37 |
| **WARN** | `london_breakout` | `USD_CHF` | 14 | -2.129 | 0.0% | 0.0% | 0.00 |
| **CRITICAL** | `ma_regime_switch` | `USD_JPY` | 38 | -1.797 | 18.4% | 9.2% | 0.29 |
| **WARN** | `ob_retest` | `EUR_USD` | 28 | -0.568 | 28.6% | 15.3% | 0.87 |
| **WARN** | `ob_retest` | `GBP_USD` | 14 | -0.450 | 42.9% | 21.4% | 0.92 |
| **WARN** | `orb_trap` | `EUR_USD` | 13 | -4.962 | 0.0% | 0.0% | 0.00 |
| **WARN** | `sr_anti_hunt_bounce` | `EUR_USD` | 23 | -15.104 | 13.0% | 4.5% | 0.07 |
| **WARN** | `sr_anti_hunt_bounce` | `GBP_JPY` | 11 | -1.336 | 18.2% | 5.1% | 0.60 |
| **CRITICAL** | `sr_anti_hunt_bounce` | `USD_JPY` | 40 | -1.935 | 0.0% | 0.0% | 0.00 |
| **CRITICAL** | `sr_break_retest` | `EUR_JPY` | 33 | -3.858 | 21.2% | 10.7% | 0.47 |
| **WARN** | `sr_break_retest` | `GBP_JPY` | 29 | -4.645 | 13.8% | 5.5% | 0.41 |
| **CRITICAL** | `sr_break_retest` | `GBP_USD` | 64 | -0.355 | 32.8% | 22.6% | 0.92 |
| **CRITICAL** | `sr_break_retest` | `USD_JPY` | 39 | -1.626 | 17.9% | 9.0% | 0.63 |
| **CRITICAL** | `sr_channel_reversal` | `GBP_USD` | 45 | -1.202 | 22.2% | 12.5% | 0.60 |
| **CRITICAL** | `sr_channel_reversal` | `USD_CHF` | 33 | -1.655 | 3.0% | 0.5% | 0.17 |
| **CRITICAL** | `sr_fib_confluence` | `EUR_USD` | 84 | -0.506 | 33.3% | 24.2% | 0.86 |
| **CRITICAL** | `sr_fib_confluence` | `GBP_USD` | 88 | -4.642 | 13.6% | 8.0% | 0.32 |
| **WARN** | `trendline_sweep` | `EUR_USD` | 21 | -0.533 | 23.8% | 10.6% | 0.88 |
| **WARN** | `trendline_sweep` | `GBP_USD` | 22 | -18.450 | 0.0% | 0.0% | 0.00 |
| **CRITICAL** | `vol_momentum_scalp` | `GBP_USD` | 34 | -2.038 | 17.6% | 8.3% | 0.51 |
| **WARN** | `vol_momentum_scalp` | `USD_JPY` | 10 | -2.910 | 0.0% | 0.0% | 0.00 |
| **WARN** | `wick_imbalance_reversion` | `EUR_JPY` | 14 | -3.814 | 21.4% | 7.6% | 0.49 |
| **CRITICAL** | `xs_momentum` | `EUR_USD` | 51 | -5.645 | 17.6% | 9.6% | 0.25 |
| **CRITICAL** | `xs_momentum` | `GBP_USD` | 38 | -0.161 | 31.6% | 19.1% | 0.98 |
| **CRITICAL** | `xs_momentum` | `USD_JPY` | 56 | -0.870 | 28.6% | 18.4% | 0.80 |

## R2 Demote Manual Action

For each CRITICAL cell, manually verify and then remove the relevant Render env var:

- `bb_rsi_reversion` x `USD_CHF`: remove `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE`
- `ema_trend_scalp` x `USD_CHF`: remove `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE`
- `engulfing_bb` x `EUR_USD`: remove `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE`
- `ma_regime_switch` x `USD_JPY`: remove `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_anti_hunt_bounce` x `USD_JPY`: remove `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `EUR_JPY`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `GBP_USD`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `USD_JPY`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_channel_reversal` x `GBP_USD`: remove `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_channel_reversal` x `USD_CHF`: remove `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_fib_confluence` x `EUR_USD`: remove `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_fib_confluence` x `GBP_USD`: remove `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE`
- `vol_momentum_scalp` x `GBP_USD`: remove `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`, `VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE`
- `xs_momentum` x `EUR_USD`: remove `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`
- `xs_momentum` x `GBP_USD`: remove `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`
- `xs_momentum` x `USD_JPY`: remove `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`

Code review locations if manual demotion is chosen:
- `strategies/daytrade/__init__.py` `split_shadow_always` / `SHADOW_ALWAYS_STRATEGIES`
- `strategies/hourly/__init__.py` `split_shadow_always`
- `strategies/scalp/__init__.py` `split_shadow_always`

## Apply Demote Suggestion

- Registry: `/home/runner/work/fx-ai-trader/fx-ai-trader/modules/shadow_demote_registry.py`
- Missing CRITICAL cells: `16`
- Add `('bb_rsi_reversion', 'USD_CHF')`
- Add `('ema_trend_scalp', 'USD_CHF')`
- Add `('engulfing_bb', 'EUR_USD')`
- Add `('ma_regime_switch', 'USD_JPY')`
- Add `('sr_anti_hunt_bounce', 'USD_JPY')`
- Add `('sr_break_retest', 'EUR_JPY')`
- Add `('sr_break_retest', 'GBP_USD')`
- Add `('sr_break_retest', 'USD_JPY')`
- Add `('sr_channel_reversal', 'GBP_USD')`
- Add `('sr_channel_reversal', 'USD_CHF')`
- Add `('sr_fib_confluence', 'EUR_USD')`
- Add `('sr_fib_confluence', 'GBP_USD')`
- Add `('vol_momentum_scalp', 'GBP_USD')`
- Add `('xs_momentum', 'EUR_USD')`
- Add `('xs_momentum', 'GBP_USD')`
- Add `('xs_momentum', 'USD_JPY')`

## All Cells

| Severity | Strategy | Instrument | N | Wins | Losses | EV | WR | Wilson 95% | PF | Env |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| OK | `adx_trend_continuation` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ADX_TREND_CONTINUATION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `asia_range_fade_v1` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ASIA_RANGE_FADE_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `atr_regime_break` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ALPHA_ATR_REGIME_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_rsi_ema_aligned` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `BB_RSI_EMA_ALIGNED_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `bb_rsi_reversion` | `USD_CHF` | 35 | 0 | 35 | -2.460 | 0.0% | 0.0%-9.9% | 0.00 | `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_rsi_reversion` | `USD_JPY` | 3 | 2 | 1 | +1.433 | 66.7% | 20.8%-93.9% | 2.19 | `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `confluence_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CONFLUENCE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `cpd_divergence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CPD_DIVERGENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `donchian_momentum_breakout` | `AUD_JPY` | 13 | 1 | 12 | -11.877 | 7.7% | 1.4%-33.3% | 0.18 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `AUD_USD` | 3 | 0 | 3 | -7.800 | 0.0% | 0.0%-56.2% | 0.00 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `EUR_AUD` | 9 | 4 | 5 | +6.767 | 44.4% | 18.9%-73.3% | 1.42 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `EUR_USD` | 4 | 0 | 4 | -10.600 | 0.0% | 0.0%-49.0% | 0.00 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `NZD_JPY` | 14 | 10 | 4 | +20.486 | 71.4% | 45.4%-88.3% | 4.99 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `NZD_USD` | 16 | 11 | 5 | +15.525 | 68.8% | 44.4%-85.8% | 7.16 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `donchian_momentum_breakout` | `USD_CAD` | 11 | 3 | 8 | -9.045 | 27.3% | 9.7%-56.6% | 0.23 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `USD_JPY` | 3 | 0 | 3 | -6.000 | 0.0% | 0.0%-56.2% | 0.00 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `EUR_USD` | 41 | 20 | 21 | +2.420 | 48.8% | 34.3%-63.5% | 2.11 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `GBP_USD` | 26 | 16 | 10 | +4.519 | 61.5% | 42.5%-77.6% | 3.55 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `USD_JPY` | 4 | 3 | 1 | +8.150 | 75.0% | 30.1%-95.4% | 327.00 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `EUR_GBP` | 4 | 2 | 2 | +2.200 | 50.0% | 15.0%-85.0% | 2.73 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `EUR_JPY` | 9 | 5 | 4 | +4.044 | 55.6% | 26.7%-81.1% | 2.13 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `GBP_JPY` | 3 | 2 | 1 | +7.067 | 66.7% | 20.8%-93.9% | 2.45 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `GBP_USD` | 9 | 3 | 6 | -3.733 | 33.3% | 12.1%-64.6% | 0.39 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `USD_JPY` | 6 | 4 | 2 | +5.033 | 66.7% | 30.0%-90.3% | 2.55 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema200_trend_reversal` | `USD_JPY` | 4 | 0 | 4 | -4.300 | 0.0% | 0.0%-49.0% | 0.00 | `EMA200_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`<br>`EMA200_TREND_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_ribbon_ride` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_RIBBON_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `ema_trend_scalp` | `USD_CHF` | 65 | 2 | 63 | -1.885 | 3.1% | 0.8%-10.5% | 0.22 | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `engulfing_bb` | `EUR_USD` | 34 | 9 | 25 | -0.738 | 26.5% | 14.6%-43.1% | 0.68 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `engulfing_bb` | `GBP_USD` | 14 | 2 | 12 | -2.264 | 14.3% | 4.0%-39.9% | 0.36 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `engulfing_bb` | `USD_CHF` | 10 | 0 | 10 | -1.430 | 0.0% | 0.0%-27.8% | 0.00 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_pips_hunter` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_PIPS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_trend_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_TREND_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_vol_break` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_VOL_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_USD` | 3 | 0 | 3 | -8.800 | 0.0% | 0.0%-56.2% | 0.00 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `GBP_USD` | 6 | 2 | 4 | +10.100 | 33.3% | 9.7%-70.0% | 3.91 | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `USD_JPY` | 2 | 1 | 1 | +11.650 | 50.0% | 9.5%-90.5% | 16.53 | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `intraday_seasonality` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `jpy_basket_trend` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `JPY_BASKET_TREND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `keltner_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `lin_reg_channel` | `EUR_USD` | 8 | 1 | 7 | -4.150 | 12.5% | 2.2%-47.1% | 0.15 | `LIN_REG_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `london_breakout` | `EUR_USD` | 25 | 2 | 23 | -2.584 | 8.0% | 2.2%-25.0% | 0.16 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `london_breakout` | `GBP_USD` | 12 | 2 | 10 | -2.183 | 16.7% | 4.7%-44.8% | 0.37 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `london_breakout` | `USD_CHF` | 14 | 0 | 14 | -2.129 | 0.0% | 0.0%-21.5% | 0.00 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_ny_swing` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_NY_SWING_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `GBP_USD` | 2 | 0 | 2 | -0.100 | 0.0% | 0.0%-65.8% | 0.00 | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_shrapnel` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_SHRAPNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_mr_hybrid` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_MR_HYBRID_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `ma_regime_switch` | `USD_JPY` | 38 | 7 | 31 | -1.797 | 18.4% | 9.2%-33.4% | 0.29 | `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_trend_perfect` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_TREND_PERFECT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `USD_JPY` | 5 | 0 | 5 | -3.160 | 0.0% | 0.0%-43.4% | 0.00 | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_regime_range_cascade_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `EUR_JPY` | 4 | 0 | 4 | -13.250 | 0.0% | 0.0%-49.0% | 0.00 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `ob_retest` | `EUR_USD` | 28 | 8 | 20 | -0.568 | 28.6% | 15.3%-47.1% | 0.87 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `GBP_JPY` | 2 | 0 | 2 | -18.400 | 0.0% | 0.0%-65.8% | 0.00 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `ob_retest` | `GBP_USD` | 14 | 6 | 8 | -0.450 | 42.9% | 21.4%-67.4% | 0.92 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `USD_JPY` | 16 | 9 | 7 | +10.600 | 56.2% | 33.2%-76.9% | 4.48 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ofi_mr` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `OFI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `orb_trap` | `EUR_USD` | 13 | 0 | 13 | -4.962 | 0.0% | 0.0%-22.8% | 0.00 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `GBP_USD` | 9 | 9 | 0 | +15.244 | 100.0% | 70.1%-100.0% | n/a | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `post_news_vol` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `EUR_JPY` | 2 | 0 | 2 | -9.250 | 0.0% | 0.0%-65.8% | 0.00 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `EUR_USD` | 6 | 0 | 6 | -5.067 | 0.0% | 0.0%-39.0% | 0.00 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `GBP_JPY` | 3 | 0 | 3 | -10.700 | 0.0% | 0.0%-56.2% | 0.00 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `GBP_USD` | 3 | 2 | 1 | +4.833 | 66.7% | 20.8%-93.9% | 2.41 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `session_vol_expansion` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SESSION_VOL_EXPANSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `squeeze_release_momentum` | `EUR_USD` | 1 | 1 | 0 | +10.400 | 100.0% | 20.7%-100.0% | n/a | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `squeeze_release_momentum` | `GBP_USD` | 2 | 1 | 1 | +6.950 | 50.0% | 9.5%-90.5% | 7.04 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `EUR_JPY` | 16 | 14 | 2 | +21.244 | 87.5% | 64.0%-96.5% | 189.83 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_anti_hunt_bounce` | `EUR_USD` | 23 | 3 | 20 | -15.104 | 13.0% | 4.5%-32.1% | 0.07 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_anti_hunt_bounce` | `GBP_JPY` | 11 | 2 | 9 | -1.336 | 18.2% | 5.1%-47.7% | 0.60 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_USD` | 2 | 2 | 0 | +10.900 | 100.0% | 34.2%-100.0% | n/a | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_anti_hunt_bounce` | `USD_JPY` | 40 | 0 | 40 | -1.935 | 0.0% | 0.0%-8.8% | 0.00 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `EUR_JPY` | 33 | 7 | 26 | -3.858 | 21.2% | 10.7%-37.8% | 0.47 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_break_retest` | `GBP_JPY` | 29 | 4 | 25 | -4.645 | 13.8% | 5.5%-30.6% | 0.41 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `GBP_USD` | 64 | 21 | 43 | -0.355 | 32.8% | 22.6%-45.0% | 0.92 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `USD_JPY` | 39 | 7 | 32 | -1.626 | 17.9% | 9.0%-32.7% | 0.63 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_channel_reversal` | `GBP_USD` | 45 | 10 | 35 | -1.202 | 22.2% | 12.5%-36.3% | 0.60 | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_channel_reversal` | `USD_CHF` | 33 | 1 | 32 | -1.655 | 3.0% | 0.5%-15.3% | 0.17 | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_fib_confluence` | `EUR_GBP` | 8 | 2 | 6 | -2.738 | 25.0% | 7.1%-59.1% | 0.22 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_fib_confluence` | `EUR_USD` | 84 | 28 | 56 | -0.506 | 33.3% | 24.2%-43.9% | 0.86 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_fib_confluence` | `GBP_USD` | 88 | 12 | 76 | -4.642 | 13.6% | 8.0%-22.3% | 0.32 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_liquidity_grab` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_LIQUIDITY_GRAB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `stoch_trend_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `EUR_USD` | 6 | 0 | 6 | -2.900 | 0.0% | 0.0%-39.0% | 0.00 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `GBP_USD` | 3 | 0 | 3 | -6.267 | 0.0% | 0.0%-56.2% | 0.00 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `USD_CHF` | 2 | 0 | 2 | -2.800 | 0.0% | 0.0%-65.8% | 0.00 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `USD_JPY` | 2 | 0 | 2 | -1.650 | 0.0% | 0.0%-65.8% | 0.00 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_range_breakout_up` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_RANGE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `USD_JPY` | 4 | 0 | 4 | -1.650 | 0.0% | 0.0%-49.0% | 0.00 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trendline_sweep` | `EUR_GBP` | 7 | 0 | 7 | -4.086 | 0.0% | 0.0%-35.4% | 0.00 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `EUR_USD` | 21 | 5 | 16 | -0.533 | 23.8% | 10.6%-45.1% | 0.88 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `GBP_USD` | 22 | 0 | 22 | -18.450 | 0.0% | 0.0%-14.9% | 0.00 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `turtle_soup` | `GBP_USD` | 7 | 3 | 4 | -5.314 | 42.9% | 15.8%-75.0% | 0.17 | `TURTLE_SOUP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tvsm` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TVSM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `v_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `V_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vbp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `VBP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `USD_JPY` | 2 | 2 | 0 | +18.700 | 100.0% | 34.2%-100.0% | n/a | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `vol_momentum_scalp` | `GBP_USD` | 34 | 6 | 28 | -2.038 | 17.6% | 8.3%-33.5% | 0.51 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_momentum_scalp` | `USD_JPY` | 10 | 0 | 10 | -2.910 | 0.0% | 0.0%-27.8% | 0.00 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `EUR_USD` | 6 | 1 | 5 | -2.283 | 16.7% | 3.0%-56.4% | 0.38 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `GBP_USD` | 8 | 4 | 4 | +3.325 | 50.0% | 21.5%-78.5% | 2.49 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `USD_CHF` | 8 | 0 | 8 | -2.138 | 0.0% | 0.0%-32.4% | 0.00 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `USD_JPY` | 8 | 1 | 7 | -2.100 | 12.5% | 2.2%-47.1% | 0.33 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_JPY` | 2 | 1 | 1 | +2.050 | 50.0% | 9.5%-90.5% | 1.23 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_USD` | 1 | 0 | 1 | -0.200 | 0.0% | 0.0%-79.3% | 0.00 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `USD_JPY` | 2 | 1 | 1 | -5.400 | 50.0% | 9.5%-90.5% | 0.46 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_GBP` | 7 | 7 | 0 | +10.129 | 100.0% | 64.6%-100.0% | n/a | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `EUR_JPY` | 14 | 3 | 11 | -3.814 | 21.4% | 7.6%-47.6% | 0.49 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_USD` | 53 | 26 | 27 | +4.549 | 49.1% | 36.1%-62.1% | 3.94 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `GBP_JPY` | 9 | 4 | 5 | -0.478 | 44.4% | 18.9%-73.3% | 0.94 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `GBP_USD` | 40 | 18 | 22 | +3.845 | 45.0% | 30.7%-60.2% | 2.17 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `USD_JPY` | 8 | 1 | 7 | -3.575 | 12.5% | 2.2%-47.1% | 0.01 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `EUR_USD` | 51 | 9 | 42 | -5.645 | 17.6% | 9.6%-30.3% | 0.25 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `GBP_USD` | 38 | 12 | 26 | -0.161 | 31.6% | 19.1%-47.5% | 0.98 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `USD_JPY` | 56 | 16 | 40 | -0.870 | 28.6% | 18.4%-41.5% | 0.80 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
