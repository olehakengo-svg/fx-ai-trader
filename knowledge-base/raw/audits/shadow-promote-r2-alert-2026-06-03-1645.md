# SHADOW_PROMOTE R2 Alert - 2026-06-03T16:45:29.819605+00:00

- Source: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=2000`
- Lookback: `30d`
- Filters: `is_shadow=1`, `pnl_pips IS NOT NULL`, XAU instruments excluded
- Gate: `N >= 10 and EV < 0` -> WARN; `N >= 30 and EV < 0` -> CRITICAL
- Mode: read-only; no env vars, strategy code, tier-master, or DB writes

## Summary

- Promoted strategies: 66
- Cells: 123
- OK: 91
- WARN: 15
- CRITICAL: 17

## WARN / CRITICAL

| Severity | Strategy | Instrument | N | EV | WR | Wilson lower | PF |
|---|---|---|---:|---:|---:|---:|---:|
| **CRITICAL** | `bb_rsi_reversion` | `USD_CHF` | 41 | -2.280 | 0.0% | 0.0% | 0.00 |
| **WARN** | `donchian_momentum_breakout` | `AUD_JPY` | 14 | -11.214 | 7.1% | 1.3% | 0.18 |
| **WARN** | `donchian_momentum_breakout` | `USD_CAD` | 11 | -9.045 | 27.3% | 9.7% | 0.23 |
| **CRITICAL** | `ema_trend_scalp` | `USD_CHF` | 66 | -1.824 | 4.5% | 1.6% | 0.23 |
| **CRITICAL** | `engulfing_bb` | `EUR_USD` | 33 | -0.818 | 30.3% | 17.4% | 0.63 |
| **WARN** | `engulfing_bb` | `GBP_USD` | 15 | -2.653 | 13.3% | 3.7% | 0.22 |
| **WARN** | `lin_reg_channel` | `EUR_USD` | 10 | -4.580 | 10.0% | 1.8% | 0.11 |
| **WARN** | `london_breakout` | `EUR_USD` | 25 | -2.584 | 8.0% | 2.2% | 0.16 |
| **WARN** | `london_breakout` | `GBP_USD` | 12 | -2.183 | 16.7% | 4.7% | 0.37 |
| **WARN** | `london_breakout` | `USD_CHF` | 14 | -2.129 | 0.0% | 0.0% | 0.00 |
| **CRITICAL** | `ma_regime_switch` | `USD_JPY` | 36 | -1.811 | 19.4% | 9.8% | 0.27 |
| **CRITICAL** | `ob_retest` | `EUR_USD` | 31 | -0.481 | 29.0% | 16.1% | 0.88 |
| **WARN** | `ob_retest` | `GBP_USD` | 10 | -2.210 | 40.0% | 16.8% | 0.60 |
| **WARN** | `ob_retest` | `USD_JPY` | 12 | -3.492 | 41.7% | 19.3% | 0.14 |
| **WARN** | `orb_trap` | `EUR_USD` | 15 | -3.087 | 13.3% | 3.7% | 0.28 |
| **WARN** | `sr_anti_hunt_bounce` | `EUR_USD` | 20 | -12.570 | 20.0% | 8.1% | 0.12 |
| **CRITICAL** | `sr_anti_hunt_bounce` | `USD_JPY` | 39 | -1.805 | 0.0% | 0.0% | 0.00 |
| **CRITICAL** | `sr_break_retest` | `EUR_JPY` | 30 | -3.987 | 20.0% | 9.5% | 0.44 |
| **CRITICAL** | `sr_break_retest` | `GBP_JPY` | 32 | -5.456 | 15.6% | 6.9% | 0.35 |
| **CRITICAL** | `sr_break_retest` | `GBP_USD` | 65 | -1.666 | 29.2% | 19.6% | 0.64 |
| **CRITICAL** | `sr_break_retest` | `USD_JPY` | 38 | -3.147 | 18.4% | 9.2% | 0.26 |
| **CRITICAL** | `sr_channel_reversal` | `GBP_USD` | 48 | -0.923 | 27.1% | 16.6% | 0.66 |
| **CRITICAL** | `sr_channel_reversal` | `USD_CHF` | 43 | -2.070 | 4.7% | 1.3% | 0.13 |
| **CRITICAL** | `sr_fib_confluence` | `EUR_USD` | 84 | -0.925 | 32.1% | 23.1% | 0.75 |
| **CRITICAL** | `sr_fib_confluence` | `GBP_USD` | 87 | -6.221 | 8.0% | 4.0% | 0.14 |
| **WARN** | `trendline_sweep` | `GBP_USD` | 27 | -15.241 | 11.1% | 3.9% | 0.02 |
| **WARN** | `vol_momentum_scalp` | `GBP_USD` | 25 | -4.388 | 4.0% | 0.7% | 0.05 |
| **WARN** | `vol_surge_detector` | `USD_CHF` | 10 | -2.580 | 0.0% | 0.0% | 0.00 |
| **WARN** | `wick_imbalance_reversion` | `EUR_JPY` | 11 | -8.618 | 9.1% | 1.6% | 0.10 |
| **CRITICAL** | `xs_momentum` | `EUR_USD` | 50 | -6.744 | 16.0% | 8.3% | 0.12 |
| **CRITICAL** | `xs_momentum` | `GBP_USD` | 40 | -1.872 | 37.5% | 24.2% | 0.67 |
| **CRITICAL** | `xs_momentum` | `USD_JPY` | 51 | -2.951 | 21.6% | 12.5% | 0.39 |

## R2 Demote Manual Action

For each CRITICAL cell, manually verify and then remove the relevant Render env var:

- `bb_rsi_reversion` x `USD_CHF`: remove `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE`
- `ema_trend_scalp` x `USD_CHF`: remove `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE`
- `engulfing_bb` x `EUR_USD`: remove `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE`
- `ma_regime_switch` x `USD_JPY`: remove `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE`
- `ob_retest` x `EUR_USD`: remove `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_anti_hunt_bounce` x `USD_JPY`: remove `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `EUR_JPY`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `GBP_JPY`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `GBP_USD`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `USD_JPY`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_channel_reversal` x `GBP_USD`: remove `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_channel_reversal` x `USD_CHF`: remove `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_fib_confluence` x `EUR_USD`: remove `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE`
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
- Missing CRITICAL cells: `17`
- Add `('bb_rsi_reversion', 'USD_CHF')`
- Add `('ema_trend_scalp', 'USD_CHF')`
- Add `('engulfing_bb', 'EUR_USD')`
- Add `('ma_regime_switch', 'USD_JPY')`
- Add `('ob_retest', 'EUR_USD')`
- Add `('sr_anti_hunt_bounce', 'USD_JPY')`
- Add `('sr_break_retest', 'EUR_JPY')`
- Add `('sr_break_retest', 'GBP_JPY')`
- Add `('sr_break_retest', 'GBP_USD')`
- Add `('sr_break_retest', 'USD_JPY')`
- Add `('sr_channel_reversal', 'GBP_USD')`
- Add `('sr_channel_reversal', 'USD_CHF')`
- Add `('sr_fib_confluence', 'EUR_USD')`
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
| OK | `bb_rsi_reversion` | `EUR_USD` | 1 | 0 | 1 | -3.000 | 0.0% | 0.0%-79.3% | 0.00 | `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `bb_rsi_reversion` | `USD_CHF` | 41 | 0 | 41 | -2.280 | 0.0% | 0.0%-8.6% | 0.00 | `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_rsi_reversion` | `USD_JPY` | 6 | 2 | 4 | -1.100 | 33.3% | 9.7%-70.0% | 0.54 | `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `confluence_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CONFLUENCE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `cpd_divergence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CPD_DIVERGENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `donchian_momentum_breakout` | `AUD_JPY` | 14 | 1 | 13 | -11.214 | 7.1% | 1.3%-31.5% | 0.18 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `AUD_USD` | 3 | 0 | 3 | -7.800 | 0.0% | 0.0%-56.2% | 0.00 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `EUR_AUD` | 9 | 4 | 5 | +6.767 | 44.4% | 18.9%-73.3% | 1.42 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `EUR_USD` | 4 | 0 | 4 | -10.600 | 0.0% | 0.0%-49.0% | 0.00 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `NZD_JPY` | 14 | 10 | 4 | +20.486 | 71.4% | 45.4%-88.3% | 4.99 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `NZD_USD` | 16 | 11 | 5 | +15.525 | 68.8% | 44.4%-85.8% | 7.16 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `donchian_momentum_breakout` | `USD_CAD` | 11 | 3 | 8 | -9.045 | 27.3% | 9.7%-56.6% | 0.23 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `USD_JPY` | 4 | 0 | 4 | -7.375 | 0.0% | 0.0%-49.0% | 0.00 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `EUR_USD` | 40 | 20 | 20 | +2.655 | 50.0% | 35.2%-64.8% | 2.29 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `GBP_USD` | 26 | 16 | 10 | +4.519 | 61.5% | 42.5%-77.6% | 3.55 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `USD_JPY` | 4 | 3 | 1 | +8.150 | 75.0% | 30.1%-95.4% | 327.00 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `EUR_GBP` | 4 | 2 | 2 | +2.200 | 50.0% | 15.0%-85.0% | 2.73 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `EUR_JPY` | 8 | 5 | 3 | +4.863 | 62.5% | 30.6%-86.3% | 2.83 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `GBP_JPY` | 4 | 2 | 2 | +2.725 | 50.0% | 15.0%-85.0% | 1.44 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `GBP_USD` | 7 | 3 | 4 | -1.686 | 42.9% | 15.8%-75.0% | 0.65 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `USD_JPY` | 6 | 4 | 2 | +5.033 | 66.7% | 30.0%-90.3% | 2.55 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema200_trend_reversal` | `USD_JPY` | 8 | 4 | 4 | -1.700 | 50.0% | 21.5%-78.5% | 0.21 | `EMA200_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`<br>`EMA200_TREND_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_ribbon_ride` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_RIBBON_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `ema_trend_scalp` | `USD_CHF` | 66 | 3 | 63 | -1.824 | 4.5% | 1.6%-12.5% | 0.23 | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `engulfing_bb` | `EUR_USD` | 33 | 10 | 23 | -0.818 | 30.3% | 17.4%-47.3% | 0.63 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `engulfing_bb` | `GBP_USD` | 15 | 2 | 13 | -2.653 | 13.3% | 3.7%-37.9% | 0.22 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `engulfing_bb` | `USD_CHF` | 7 | 0 | 7 | -1.600 | 0.0% | 0.0%-35.4% | 0.00 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_pips_hunter` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_PIPS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_trend_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_TREND_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_vol_break` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_VOL_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_USD` | 2 | 0 | 2 | -6.100 | 0.0% | 0.0%-65.8% | 0.00 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `GBP_USD` | 6 | 2 | 4 | +10.100 | 33.3% | 9.7%-70.0% | 3.91 | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `USD_JPY` | 1 | 0 | 1 | -1.500 | 0.0% | 0.0%-79.3% | 0.00 | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `intraday_seasonality` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `jpy_basket_trend` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `JPY_BASKET_TREND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `keltner_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `lin_reg_channel` | `EUR_USD` | 10 | 1 | 9 | -4.580 | 10.0% | 1.8%-40.4% | 0.11 | `LIN_REG_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `london_breakout` | `EUR_USD` | 25 | 2 | 23 | -2.584 | 8.0% | 2.2%-25.0% | 0.16 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `london_breakout` | `GBP_USD` | 12 | 2 | 10 | -2.183 | 16.7% | 4.7%-44.8% | 0.37 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `london_breakout` | `USD_CHF` | 14 | 0 | 14 | -2.129 | 0.0% | 0.0%-21.5% | 0.00 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_breakout` | `USD_JPY` | 1 | 0 | 1 | -7.800 | 0.0% | 0.0%-79.3% | 0.00 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_ny_swing` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_NY_SWING_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `GBP_USD` | 2 | 0 | 2 | -0.100 | 0.0% | 0.0%-65.8% | 0.00 | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_shrapnel` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_SHRAPNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_mr_hybrid` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_MR_HYBRID_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `ma_regime_switch` | `USD_JPY` | 36 | 7 | 29 | -1.811 | 19.4% | 9.8%-35.0% | 0.27 | `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_trend_perfect` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_TREND_PERFECT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `USD_JPY` | 6 | 0 | 6 | -2.700 | 0.0% | 0.0%-39.0% | 0.00 | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_regime_range_cascade_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `ob_retest` | `EUR_USD` | 31 | 9 | 22 | -0.481 | 29.0% | 16.1%-46.6% | 0.88 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `GBP_JPY` | 2 | 0 | 2 | -18.400 | 0.0% | 0.0%-65.8% | 0.00 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `ob_retest` | `GBP_USD` | 10 | 4 | 6 | -2.210 | 40.0% | 16.8%-68.7% | 0.60 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `ob_retest` | `USD_JPY` | 12 | 5 | 7 | -3.492 | 41.7% | 19.3%-68.0% | 0.14 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ofi_mr` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `OFI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `orb_trap` | `EUR_USD` | 15 | 2 | 13 | -3.087 | 13.3% | 3.7%-37.9% | 0.28 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `GBP_USD` | 11 | 11 | 0 | +13.245 | 100.0% | 74.1%-100.0% | n/a | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `post_news_vol` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `EUR_JPY` | 1 | 0 | 1 | -9.100 | 0.0% | 0.0%-79.3% | 0.00 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `EUR_USD` | 6 | 0 | 6 | -5.067 | 0.0% | 0.0%-39.0% | 0.00 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `GBP_JPY` | 3 | 0 | 3 | -10.700 | 0.0% | 0.0%-56.2% | 0.00 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `GBP_USD` | 3 | 2 | 1 | +4.833 | 66.7% | 20.8%-93.9% | 2.41 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `session_vol_expansion` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SESSION_VOL_EXPANSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `squeeze_release_momentum` | `EUR_USD` | 1 | 1 | 0 | +10.400 | 100.0% | 20.7%-100.0% | n/a | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `squeeze_release_momentum` | `GBP_USD` | 2 | 1 | 1 | +6.950 | 50.0% | 9.5%-90.5% | 7.04 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `EUR_JPY` | 16 | 14 | 2 | +21.244 | 87.5% | 64.0%-96.5% | 189.83 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_anti_hunt_bounce` | `EUR_USD` | 20 | 4 | 16 | -12.570 | 20.0% | 8.1%-41.6% | 0.12 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_JPY` | 9 | 2 | 7 | +2.233 | 22.2% | 6.3%-54.7% | 12.17 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_anti_hunt_bounce` | `USD_JPY` | 39 | 0 | 39 | -1.805 | 0.0% | 0.0%-9.0% | 0.00 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `EUR_JPY` | 30 | 6 | 24 | -3.987 | 20.0% | 9.5%-37.3% | 0.44 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `GBP_JPY` | 32 | 5 | 27 | -5.456 | 15.6% | 6.9%-31.8% | 0.35 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `GBP_USD` | 65 | 19 | 46 | -1.666 | 29.2% | 19.6%-41.2% | 0.64 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `USD_JPY` | 38 | 7 | 31 | -3.147 | 18.4% | 9.2%-33.4% | 0.26 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_channel_reversal` | `GBP_USD` | 48 | 13 | 35 | -0.923 | 27.1% | 16.6%-41.0% | 0.66 | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_channel_reversal` | `USD_CHF` | 43 | 2 | 41 | -2.070 | 4.7% | 1.3%-15.5% | 0.13 | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_fib_confluence` | `EUR_GBP` | 8 | 2 | 6 | -2.738 | 25.0% | 7.1%-59.1% | 0.22 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_fib_confluence` | `EUR_USD` | 84 | 27 | 57 | -0.925 | 32.1% | 23.1%-42.7% | 0.75 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_fib_confluence` | `GBP_USD` | 87 | 7 | 80 | -6.221 | 8.0% | 4.0%-15.7% | 0.14 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_liquidity_grab` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_LIQUIDITY_GRAB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `stoch_trend_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `EUR_USD` | 4 | 0 | 4 | -2.200 | 0.0% | 0.0%-49.0% | 0.00 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `GBP_USD` | 3 | 0 | 3 | -6.267 | 0.0% | 0.0%-56.2% | 0.00 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `USD_CHF` | 2 | 0 | 2 | -2.800 | 0.0% | 0.0%-65.8% | 0.00 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `USD_JPY` | 1 | 0 | 1 | -3.000 | 0.0% | 0.0%-79.3% | 0.00 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_range_breakout_up` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_RANGE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `USD_JPY` | 4 | 0 | 4 | -1.650 | 0.0% | 0.0%-49.0% | 0.00 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trendline_sweep` | `EUR_GBP` | 7 | 0 | 7 | -4.086 | 0.0% | 0.0%-35.4% | 0.00 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trendline_sweep` | `EUR_USD` | 25 | 10 | 15 | +1.480 | 40.0% | 23.4%-59.3% | 1.38 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `GBP_USD` | 27 | 3 | 24 | -15.241 | 11.1% | 3.9%-28.1% | 0.02 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `turtle_soup` | `GBP_USD` | 7 | 3 | 4 | -5.314 | 42.9% | 15.8%-75.0% | 0.17 | `TURTLE_SOUP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tvsm` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TVSM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `v_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `V_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vbp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `VBP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `USD_JPY` | 3 | 3 | 0 | +13.067 | 100.0% | 43.8%-100.0% | n/a | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_momentum_scalp` | `GBP_USD` | 25 | 1 | 24 | -4.388 | 4.0% | 0.7%-19.5% | 0.05 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_momentum_scalp` | `USD_JPY` | 6 | 0 | 6 | -2.500 | 0.0% | 0.0%-39.0% | 0.00 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `EUR_USD` | 9 | 1 | 8 | -2.878 | 11.1% | 2.0%-43.5% | 0.24 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `GBP_USD` | 5 | 1 | 4 | -2.240 | 20.0% | 3.6%-62.4% | 0.37 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `USD_CHF` | 10 | 0 | 10 | -2.580 | 0.0% | 0.0%-27.8% | 0.00 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `USD_JPY` | 9 | 1 | 8 | -2.222 | 11.1% | 2.0%-43.5% | 0.29 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_GBP` | 1 | 1 | 0 | +2.700 | 100.0% | 20.7%-100.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_JPY` | 2 | 1 | 1 | +2.050 | 50.0% | 9.5%-90.5% | 1.23 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_USD` | 1 | 0 | 1 | -0.200 | 0.0% | 0.0%-79.3% | 0.00 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `USD_JPY` | 1 | 1 | 0 | +9.300 | 100.0% | 20.7%-100.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_GBP` | 2 | 2 | 0 | +2.500 | 100.0% | 34.2%-100.0% | n/a | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `EUR_JPY` | 11 | 1 | 10 | -8.618 | 9.1% | 1.6%-37.7% | 0.10 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_USD` | 56 | 28 | 28 | +4.352 | 50.0% | 37.3%-62.7% | 3.94 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `GBP_JPY` | 3 | 2 | 1 | +1.700 | 66.7% | 20.8%-93.9% | 2.96 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `GBP_USD` | 39 | 12 | 27 | +0.108 | 30.8% | 18.6%-46.4% | 1.03 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `USD_JPY` | 8 | 1 | 7 | -3.575 | 12.5% | 2.2%-47.1% | 0.01 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `EUR_USD` | 50 | 8 | 42 | -6.744 | 16.0% | 8.3%-28.5% | 0.12 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `GBP_USD` | 40 | 15 | 25 | -1.872 | 37.5% | 24.2%-53.0% | 0.67 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `USD_JPY` | 51 | 11 | 40 | -2.951 | 21.6% | 12.5%-34.6% | 0.39 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
