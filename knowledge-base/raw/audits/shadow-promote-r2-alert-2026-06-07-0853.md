# SHADOW_PROMOTE R2 Alert - 2026-06-07T08:53:44.844503+00:00

- Source: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=2000`
- Lookback: `30d`
- Filters: `is_shadow=1`, `pnl_pips IS NOT NULL`, XAU instruments excluded
- Gate: `N >= 10 and EV < 0` -> WARN; `N >= 30 and EV < 0` -> CRITICAL
- Mode: read-only; no env vars, strategy code, tier-master, or DB writes

## Summary

- Promoted strategies: 66
- Cells: 127
- OK: 93
- WARN: 21
- CRITICAL: 13

## WARN / CRITICAL

| Severity | Strategy | Instrument | N | EV | WR | Wilson lower | PF |
|---|---|---|---:|---:|---:|---:|---:|
| **CRITICAL** | `bb_rsi_reversion` | `USD_CHF` | 39 | -1.767 | 5.1% | 1.4% | 0.06 |
| **WARN** | `donchian_momentum_breakout` | `AUD_JPY` | 14 | -11.214 | 7.1% | 1.3% | 0.18 |
| **WARN** | `dt_sr_channel_reversal` | `GBP_JPY` | 13 | -6.192 | 38.5% | 17.7% | 0.35 |
| **WARN** | `ema200_trend_reversal` | `USD_JPY` | 12 | -1.450 | 50.0% | 25.4% | 0.29 |
| **CRITICAL** | `ema_trend_scalp` | `USD_CHF` | 97 | -1.796 | 4.1% | 1.6% | 0.19 |
| **WARN** | `engulfing_bb` | `EUR_USD` | 27 | -1.074 | 29.6% | 15.9% | 0.52 |
| **WARN** | `engulfing_bb` | `GBP_USD` | 15 | -2.227 | 13.3% | 3.7% | 0.25 |
| **CRITICAL** | `london_breakout` | `EUR_USD` | 38 | -0.818 | 28.9% | 17.0% | 0.60 |
| **WARN** | `london_breakout` | `GBP_USD` | 20 | -0.535 | 35.0% | 18.1% | 0.75 |
| **WARN** | `london_breakout` | `USD_CHF` | 16 | -1.756 | 12.5% | 3.5% | 0.12 |
| **CRITICAL** | `ma_regime_switch` | `USD_JPY` | 43 | -1.170 | 27.9% | 16.7% | 0.40 |
| **WARN** | `ob_retest` | `EUR_USD` | 23 | -3.517 | 4.3% | 0.8% | 0.02 |
| **WARN** | `ob_retest` | `GBP_USD` | 10 | -2.210 | 40.0% | 16.8% | 0.60 |
| **WARN** | `ob_retest` | `USD_JPY` | 21 | -0.071 | 71.4% | 50.0% | 0.96 |
| **WARN** | `orb_trap` | `EUR_USD` | 15 | -3.087 | 13.3% | 3.7% | 0.28 |
| **WARN** | `pullback_to_liquidity_v1` | `EUR_USD` | 10 | -4.040 | 20.0% | 5.7% | 0.08 |
| **WARN** | `sr_anti_hunt_bounce` | `EUR_USD` | 18 | -13.956 | 22.2% | 9.0% | 0.12 |
| **WARN** | `sr_anti_hunt_bounce` | `USD_JPY` | 29 | -1.631 | 6.9% | 1.9% | 0.07 |
| **WARN** | `sr_break_retest` | `EUR_JPY` | 24 | -6.171 | 16.7% | 6.7% | 0.14 |
| **CRITICAL** | `sr_break_retest` | `GBP_JPY` | 32 | -6.797 | 18.8% | 8.9% | 0.17 |
| **CRITICAL** | `sr_break_retest` | `GBP_USD` | 62 | -2.135 | 30.6% | 20.6% | 0.56 |
| **CRITICAL** | `sr_break_retest` | `USD_JPY` | 42 | -2.688 | 28.6% | 17.2% | 0.28 |
| **CRITICAL** | `sr_channel_reversal` | `GBP_USD` | 40 | -1.062 | 30.0% | 18.1% | 0.57 |
| **CRITICAL** | `sr_channel_reversal` | `USD_CHF` | 35 | -2.149 | 5.7% | 1.6% | 0.15 |
| **CRITICAL** | `sr_fib_confluence` | `GBP_USD` | 67 | -4.255 | 16.4% | 9.4% | 0.26 |
| **WARN** | `trendline_sweep` | `GBP_USD` | 19 | -15.374 | 15.8% | 5.5% | 0.03 |
| **WARN** | `vol_momentum_scalp` | `GBP_USD` | 26 | -3.238 | 15.4% | 6.1% | 0.20 |
| **WARN** | `vol_surge_detector` | `EUR_USD` | 15 | -2.593 | 20.0% | 7.0% | 0.22 |
| **WARN** | `vol_surge_detector` | `USD_CHF` | 10 | -3.950 | 0.0% | 0.0% | 0.00 |
| **WARN** | `vol_surge_detector` | `USD_JPY` | 10 | -1.920 | 20.0% | 5.7% | 0.32 |
| **WARN** | `wick_imbalance_reversion` | `USD_JPY` | 19 | -2.789 | 63.2% | 41.0% | 0.27 |
| **CRITICAL** | `xs_momentum` | `EUR_USD` | 68 | -3.990 | 33.8% | 23.7% | 0.30 |
| **CRITICAL** | `xs_momentum` | `GBP_USD` | 51 | -0.410 | 49.0% | 35.9% | 0.90 |
| **CRITICAL** | `xs_momentum` | `USD_JPY` | 61 | -3.516 | 31.1% | 20.9% | 0.33 |

## R2 Demote Manual Action

For each CRITICAL cell, manually verify and then remove the relevant Render env var:

- `bb_rsi_reversion` x `USD_CHF`: remove `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE`
- `ema_trend_scalp` x `USD_CHF`: remove `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE`
- `london_breakout` x `EUR_USD`: remove `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE`
- `ma_regime_switch` x `USD_JPY`: remove `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `GBP_JPY`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `GBP_USD`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `USD_JPY`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_channel_reversal` x `GBP_USD`: remove `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_channel_reversal` x `USD_CHF`: remove `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_fib_confluence` x `GBP_USD`: remove `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE`
- `xs_momentum` x `EUR_USD`: remove `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`
- `xs_momentum` x `GBP_USD`: remove `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`
- `xs_momentum` x `USD_JPY`: remove `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`

Code review locations if manual demotion is chosen:
- `strategies/daytrade/__init__.py` `split_shadow_always` / `SHADOW_ALWAYS_STRATEGIES`
- `strategies/hourly/__init__.py` `split_shadow_always`
- `strategies/scalp/__init__.py` `split_shadow_always`

## Apply Demote Suggestion

- Registry: `/home/runner/work/fx-ai-trader/fx-ai-trader/modules/shadow_demote_registry.py`
- Missing CRITICAL cells: `13`
- Add `('bb_rsi_reversion', 'USD_CHF')`
- Add `('ema_trend_scalp', 'USD_CHF')`
- Add `('london_breakout', 'EUR_USD')`
- Add `('ma_regime_switch', 'USD_JPY')`
- Add `('sr_break_retest', 'GBP_JPY')`
- Add `('sr_break_retest', 'GBP_USD')`
- Add `('sr_break_retest', 'USD_JPY')`
- Add `('sr_channel_reversal', 'GBP_USD')`
- Add `('sr_channel_reversal', 'USD_CHF')`
- Add `('sr_fib_confluence', 'GBP_USD')`
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
| OK | `bb_rsi_reversion` | `EUR_USD` | 2 | 0 | 2 | -3.350 | 0.0% | 0.0%-65.8% | 0.00 | `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `bb_rsi_reversion` | `USD_CHF` | 39 | 2 | 37 | -1.767 | 5.1% | 1.4%-16.9% | 0.06 | `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_rsi_reversion` | `USD_JPY` | 6 | 2 | 4 | -1.100 | 33.3% | 9.7%-70.0% | 0.54 | `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `confluence_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CONFLUENCE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `cpd_divergence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CPD_DIVERGENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `donchian_momentum_breakout` | `AUD_JPY` | 14 | 1 | 13 | -11.214 | 7.1% | 1.3%-31.5% | 0.18 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `AUD_USD` | 3 | 0 | 3 | -7.800 | 0.0% | 0.0%-56.2% | 0.00 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `EUR_AUD` | 3 | 1 | 2 | -4.800 | 33.3% | 6.1%-79.2% | 0.74 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `EUR_USD` | 4 | 0 | 4 | -10.600 | 0.0% | 0.0%-49.0% | 0.00 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `NZD_JPY` | 14 | 10 | 4 | +20.486 | 71.4% | 45.4%-88.3% | 4.99 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `NZD_USD` | 15 | 11 | 4 | +17.787 | 73.3% | 48.0%-89.1% | 13.18 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `USD_CAD` | 8 | 3 | 5 | -3.663 | 37.5% | 13.7%-69.4% | 0.50 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `USD_JPY` | 4 | 0 | 4 | -7.375 | 0.0% | 0.0%-49.0% | 0.00 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `EUR_USD` | 35 | 15 | 20 | +1.329 | 42.9% | 28.0%-59.1% | 1.57 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `GBP_USD` | 21 | 14 | 7 | +2.452 | 66.7% | 45.4%-82.8% | 2.04 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `USD_JPY` | 2 | 2 | 0 | +8.500 | 100.0% | 34.2%-100.0% | n/a | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `EUR_GBP` | 6 | 2 | 4 | -0.400 | 33.3% | 9.7%-70.0% | 0.85 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `EUR_JPY` | 9 | 5 | 4 | +2.811 | 55.6% | 26.7%-81.1% | 1.72 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `EUR_USD` | 2 | 2 | 0 | +7.900 | 100.0% | 34.2%-100.0% | n/a | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `GBP_JPY` | 13 | 5 | 8 | -6.192 | 38.5% | 17.7%-64.5% | 0.35 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `GBP_USD` | 6 | 3 | 3 | +0.267 | 50.0% | 18.8%-81.2% | 1.08 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `USD_JPY` | 5 | 1 | 4 | -4.380 | 20.0% | 3.6%-62.4% | 0.26 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `ema200_trend_reversal` | `USD_JPY` | 12 | 6 | 6 | -1.450 | 50.0% | 25.4%-74.6% | 0.29 | `EMA200_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`<br>`EMA200_TREND_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_ribbon_ride` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_RIBBON_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `ema_trend_scalp` | `USD_CHF` | 97 | 4 | 93 | -1.796 | 4.1% | 1.6%-10.1% | 0.19 | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `engulfing_bb` | `EUR_USD` | 27 | 8 | 19 | -1.074 | 29.6% | 15.9%-48.5% | 0.52 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `engulfing_bb` | `GBP_USD` | 15 | 2 | 13 | -2.227 | 13.3% | 3.7%-37.9% | 0.25 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `engulfing_bb` | `USD_CHF` | 4 | 0 | 4 | -1.250 | 0.0% | 0.0%-49.0% | 0.00 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_pips_hunter` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_PIPS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_trend_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_TREND_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_vol_break` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_VOL_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `EUR_JPY` | 1 | 0 | 1 | -15.400 | 0.0% | 0.0%-79.3% | 0.00 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_JPY` | 1 | 1 | 0 | +2.600 | 100.0% | 20.7%-100.0% | n/a | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_USD` | 2 | 0 | 2 | -6.100 | 0.0% | 0.0%-65.8% | 0.00 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `GBP_USD` | 6 | 2 | 4 | +10.100 | 33.3% | 9.7%-70.0% | 3.91 | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `USD_JPY` | 1 | 0 | 1 | -1.500 | 0.0% | 0.0%-79.3% | 0.00 | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `intraday_seasonality` | `EUR_GBP` | 1 | 0 | 1 | -8.400 | 0.0% | 0.0%-79.3% | 0.00 | `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `jpy_basket_trend` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `JPY_BASKET_TREND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `keltner_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `lin_reg_channel` | `EUR_USD` | 6 | 1 | 5 | -4.667 | 16.7% | 3.0%-56.4% | 0.17 | `LIN_REG_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `london_breakout` | `EUR_USD` | 38 | 11 | 27 | -0.818 | 28.9% | 17.0%-44.8% | 0.60 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `london_breakout` | `GBP_USD` | 20 | 7 | 13 | -0.535 | 35.0% | 18.1%-56.7% | 0.75 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `london_breakout` | `USD_CHF` | 16 | 2 | 14 | -1.756 | 12.5% | 3.5%-36.0% | 0.12 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_breakout` | `USD_JPY` | 1 | 0 | 1 | -7.800 | 0.0% | 0.0%-79.3% | 0.00 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_ny_swing` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_NY_SWING_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `EUR_USD` | 1 | 1 | 0 | +1.800 | 100.0% | 20.7%-100.0% | n/a | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `GBP_USD` | 4 | 2 | 2 | +1.000 | 50.0% | 15.0%-85.0% | 21.00 | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_shrapnel` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_SHRAPNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_mr_hybrid` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_MR_HYBRID_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `ma_regime_switch` | `USD_JPY` | 43 | 12 | 31 | -1.170 | 27.9% | 16.7%-42.7% | 0.40 | `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_trend_perfect` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_TREND_PERFECT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `USD_JPY` | 6 | 0 | 6 | -2.700 | 0.0% | 0.0%-39.0% | 0.00 | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_regime_range_cascade_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `ob_retest` | `EUR_USD` | 23 | 1 | 22 | -3.517 | 4.3% | 0.8%-21.0% | 0.02 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `ob_retest` | `GBP_USD` | 10 | 4 | 6 | -2.210 | 40.0% | 16.8%-68.7% | 0.60 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `ob_retest` | `USD_JPY` | 21 | 15 | 6 | -0.071 | 71.4% | 50.0%-86.2% | 0.96 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ofi_mr` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `OFI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `orb_trap` | `EUR_USD` | 15 | 2 | 13 | -3.087 | 13.3% | 3.7%-37.9% | 0.28 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `GBP_USD` | 11 | 11 | 0 | +13.245 | 100.0% | 74.1%-100.0% | n/a | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `USD_JPY` | 1 | 0 | 1 | -7.600 | 0.0% | 0.0%-79.3% | 0.00 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `post_news_vol` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `EUR_JPY` | 1 | 0 | 1 | -9.100 | 0.0% | 0.0%-79.3% | 0.00 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `pullback_to_liquidity_v1` | `EUR_USD` | 10 | 2 | 8 | -4.040 | 20.0% | 5.7%-51.0% | 0.08 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `GBP_JPY` | 3 | 0 | 3 | -10.700 | 0.0% | 0.0%-56.2% | 0.00 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `GBP_USD` | 2 | 2 | 0 | +12.400 | 100.0% | 34.2%-100.0% | n/a | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `session_vol_expansion` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SESSION_VOL_EXPANSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `squeeze_release_momentum` | `EUR_USD` | 1 | 1 | 0 | +10.400 | 100.0% | 20.7%-100.0% | n/a | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `squeeze_release_momentum` | `GBP_USD` | 2 | 1 | 1 | +6.950 | 50.0% | 9.5%-90.5% | 7.04 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `EUR_JPY` | 16 | 14 | 2 | +21.244 | 87.5% | 64.0%-96.5% | 189.83 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_anti_hunt_bounce` | `EUR_USD` | 18 | 4 | 14 | -13.956 | 22.2% | 9.0%-45.2% | 0.12 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_JPY` | 5 | 0 | 5 | -0.320 | 0.0% | 0.0%-43.4% | 0.00 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_anti_hunt_bounce` | `USD_JPY` | 29 | 2 | 27 | -1.631 | 6.9% | 1.9%-22.0% | 0.07 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_break_retest` | `EUR_JPY` | 24 | 4 | 20 | -6.171 | 16.7% | 6.7%-35.9% | 0.14 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `GBP_JPY` | 32 | 6 | 26 | -6.797 | 18.8% | 8.9%-35.3% | 0.17 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `GBP_USD` | 62 | 19 | 43 | -2.135 | 30.6% | 20.6%-43.0% | 0.56 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `USD_JPY` | 42 | 12 | 30 | -2.688 | 28.6% | 17.2%-43.6% | 0.28 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_channel_reversal` | `GBP_USD` | 40 | 12 | 28 | -1.062 | 30.0% | 18.1%-45.4% | 0.57 | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_channel_reversal` | `USD_CHF` | 35 | 2 | 33 | -2.149 | 5.7% | 1.6%-18.6% | 0.15 | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_fib_confluence` | `EUR_GBP` | 3 | 2 | 1 | +0.200 | 66.7% | 20.8%-93.9% | 1.11 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_fib_confluence` | `EUR_USD` | 86 | 36 | 50 | +0.306 | 41.9% | 32.0%-52.4% | 1.11 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_fib_confluence` | `GBP_USD` | 67 | 11 | 56 | -4.255 | 16.4% | 9.4%-27.1% | 0.26 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_liquidity_grab` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_LIQUIDITY_GRAB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `stoch_trend_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `EUR_USD` | 3 | 0 | 3 | -2.533 | 0.0% | 0.0%-56.2% | 0.00 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `GBP_USD` | 2 | 0 | 2 | -4.400 | 0.0% | 0.0%-65.8% | 0.00 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `USD_CHF` | 2 | 0 | 2 | -2.800 | 0.0% | 0.0%-65.8% | 0.00 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `USD_JPY` | 1 | 0 | 1 | -3.000 | 0.0% | 0.0%-79.3% | 0.00 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_range_breakout_up` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_RANGE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `USD_JPY` | 4 | 0 | 4 | -3.600 | 0.0% | 0.0%-49.0% | 0.00 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trendline_sweep` | `EUR_GBP` | 9 | 2 | 7 | -2.411 | 22.2% | 6.3%-54.7% | 0.14 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trendline_sweep` | `EUR_USD` | 12 | 6 | 6 | +3.525 | 50.0% | 25.4%-74.6% | 2.61 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `GBP_USD` | 19 | 3 | 16 | -15.374 | 15.8% | 5.5%-37.6% | 0.03 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `turtle_soup` | `GBP_USD` | 9 | 4 | 5 | -4.211 | 44.4% | 18.9%-73.3% | 0.19 | `TURTLE_SOUP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tvsm` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TVSM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `v_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `V_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vbp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `VBP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `USD_JPY` | 5 | 5 | 0 | +14.600 | 100.0% | 56.6%-100.0% | n/a | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_momentum_scalp` | `GBP_USD` | 26 | 4 | 22 | -3.238 | 15.4% | 6.1%-33.5% | 0.20 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_momentum_scalp` | `USD_JPY` | 3 | 0 | 3 | -2.233 | 0.0% | 0.0%-56.2% | 0.00 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `EUR_USD` | 15 | 3 | 12 | -2.593 | 20.0% | 7.0%-45.2% | 0.22 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `GBP_USD` | 6 | 1 | 5 | -2.567 | 16.7% | 3.0%-56.4% | 0.30 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `USD_CHF` | 10 | 0 | 10 | -3.950 | 0.0% | 0.0%-27.8% | 0.00 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `USD_JPY` | 10 | 2 | 8 | -1.920 | 20.0% | 5.7%-51.0% | 0.32 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_GBP` | 2 | 1 | 1 | -2.400 | 50.0% | 9.5%-90.5% | 0.36 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_JPY` | 1 | 1 | 0 | +22.100 | 100.0% | 20.7%-100.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_USD` | 1 | 0 | 1 | -0.200 | 0.0% | 0.0%-79.3% | 0.00 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `USD_JPY` | 1 | 1 | 0 | +9.300 | 100.0% | 20.7%-100.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_GBP` | 2 | 2 | 0 | +2.500 | 100.0% | 34.2%-100.0% | n/a | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_JPY` | 8 | 2 | 6 | -5.300 | 25.0% | 7.1%-59.1% | 0.24 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_USD` | 48 | 27 | 21 | +5.290 | 56.2% | 42.3%-69.3% | 5.71 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `GBP_JPY` | 4 | 2 | 2 | -1.700 | 50.0% | 15.0%-85.0% | 0.53 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `GBP_USD` | 38 | 14 | 24 | +0.432 | 36.8% | 23.4%-52.7% | 1.14 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `USD_JPY` | 19 | 12 | 7 | -2.789 | 63.2% | 41.0%-80.9% | 0.27 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `EUR_USD` | 68 | 23 | 45 | -3.990 | 33.8% | 23.7%-45.7% | 0.30 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `GBP_USD` | 51 | 25 | 26 | -0.410 | 49.0% | 35.9%-62.3% | 0.90 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `USD_JPY` | 61 | 19 | 42 | -3.516 | 31.1% | 20.9%-43.6% | 0.33 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
