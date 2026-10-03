# SHADOW_PROMOTE R2 Alert - 2026-10-03T03:48:56.536518+00:00

- Source: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=2000`
- Lookback: `30d`
- Filters: `is_shadow=1`, `pnl_pips IS NOT NULL`, `dedup_violation != 1`, XAU instruments excluded
- Gate: `N >= 10 and EV < 0` -> WARN; `N >= 30 and EV < 0` -> CRITICAL
- Mode: read-only; no env vars, strategy code, tier-master, or DB writes

## Summary

- Promoted strategies: 65
- Cells: 124
- OK: 97
- WARN: 19
- CRITICAL: 8

## WARN / CRITICAL

| Severity | Strategy | Instrument | N | EV | WR | Wilson lower | PF |
|---|---|---|---:|---:|---:|---:|---:|
| **CRITICAL** | `bb_squeeze_breakout` | `EUR_USD` | 31 | -1.132 | 25.8% | 13.7% | 0.35 |
| **WARN** | `bb_squeeze_breakout` | `GBP_USD` | 11 | -1.573 | 18.2% | 5.1% | 0.43 |
| **WARN** | `bb_squeeze_breakout` | `USD_JPY` | 17 | -1.229 | 29.4% | 13.3% | 0.51 |
| **WARN** | `dt_bb_rsi_mr` | `GBP_USD` | 10 | -4.390 | 30.0% | 10.8% | 0.09 |
| **WARN** | `dt_bb_rsi_mr` | `USD_JPY` | 17 | -0.076 | 58.8% | 36.0% | 0.98 |
| **CRITICAL** | `dt_sr_channel_reversal` | `EUR_JPY` | 63 | -3.283 | 47.6% | 35.8% | 0.42 |
| **WARN** | `dt_sr_channel_reversal` | `EUR_USD` | 15 | -0.433 | 33.3% | 15.2% | 0.87 |
| **CRITICAL** | `dt_sr_channel_reversal` | `GBP_JPY` | 52 | -4.698 | 38.5% | 26.5% | 0.26 |
| **WARN** | `dt_sr_channel_reversal` | `GBP_USD` | 20 | -1.580 | 40.0% | 21.9% | 0.54 |
| **CRITICAL** | `dt_sr_channel_reversal` | `USD_JPY` | 46 | -2.157 | 56.5% | 42.2% | 0.53 |
| **CRITICAL** | `london_breakout` | `EUR_USD` | 33 | -0.424 | 48.5% | 32.5% | 0.76 |
| **WARN** | `sr_anti_hunt_bounce` | `EUR_JPY` | 13 | -3.054 | 53.8% | 29.1% | 0.46 |
| **CRITICAL** | `sr_break_retest` | `AUD_JPY` | 40 | -2.903 | 45.0% | 30.7% | 0.48 |
| **CRITICAL** | `sr_break_retest` | `USD_JPY` | 36 | -3.097 | 41.7% | 27.1% | 0.40 |
| **WARN** | `three_bar_reversal` | `EUR_USD` | 15 | -1.400 | 40.0% | 19.8% | 0.44 |
| **WARN** | `three_bar_reversal` | `GBP_USD` | 11 | -0.900 | 45.5% | 21.3% | 0.68 |
| **WARN** | `three_bar_reversal` | `USD_JPY` | 27 | -1.648 | 29.6% | 15.9% | 0.46 |
| **WARN** | `trend_rebound` | `EUR_USD` | 18 | -0.117 | 38.9% | 20.3% | 0.92 |
| **WARN** | `trendline_sweep` | `EUR_GBP` | 18 | -1.028 | 50.0% | 29.0% | 0.62 |
| **WARN** | `trendline_sweep` | `GBP_USD` | 26 | -1.065 | 69.2% | 50.0% | 0.63 |
| **WARN** | `v_reversal` | `USD_JPY` | 11 | -0.809 | 54.5% | 28.0% | 0.48 |
| **WARN** | `vol_surge_detector` | `EUR_USD` | 26 | -3.131 | 7.7% | 2.1% | 0.05 |
| **CRITICAL** | `wick_imbalance_reversion` | `AUD_JPY` | 42 | -2.574 | 45.2% | 31.2% | 0.55 |
| **WARN** | `wick_imbalance_reversion` | `EUR_JPY` | 16 | -0.700 | 56.2% | 33.2% | 0.83 |
| **WARN** | `wick_imbalance_reversion` | `EUR_USD` | 20 | -3.370 | 40.0% | 21.9% | 0.18 |
| **WARN** | `wick_imbalance_reversion` | `GBP_JPY` | 11 | -5.591 | 54.5% | 28.0% | 0.35 |
| **WARN** | `wick_imbalance_reversion` | `GBP_USD` | 23 | -2.857 | 34.8% | 18.8% | 0.33 |

## R2 Demote Manual Action

For each CRITICAL cell, manually verify and then remove the relevant Render env var:

- `bb_squeeze_breakout` x `EUR_USD`: remove `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE`
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
- Missing CRITICAL cells: `8`
- Add `('bb_squeeze_breakout', 'EUR_USD')`
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
| OK | `atr_regime_break` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ALPHA_ATR_REGIME_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_rsi_ema_aligned` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `BB_RSI_EMA_ALIGNED_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `bb_squeeze_breakout` | `EUR_USD` | 31 | 8 | 23 | -1.132 | 25.8% | 13.7%-43.2% | 0.35 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `bb_squeeze_breakout` | `GBP_USD` | 11 | 2 | 9 | -1.573 | 18.2% | 5.1%-47.7% | 0.43 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `USD_CHF` | 2 | 0 | 2 | -2.350 | 0.0% | 0.0%-65.8% | 0.00 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `bb_squeeze_breakout` | `USD_JPY` | 17 | 5 | 12 | -1.229 | 29.4% | 13.3%-53.1% | 0.51 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `confluence_scalp` | `USD_JPY` | 1 | 1 | 0 | +9.500 | 100.0% | 20.7%-100.0% | n/a | `CONFLUENCE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `cpd_divergence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CPD_DIVERGENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `AUD_JPY` | 3 | 3 | 0 | +4.567 | 100.0% | 43.8%-100.0% | n/a | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `AUD_USD` | 5 | 2 | 3 | -8.240 | 40.0% | 11.8%-76.9% | 0.06 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `EUR_USD` | 3 | 2 | 1 | -1.167 | 66.7% | 20.8%-93.9% | 0.79 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `NZD_USD` | 2 | 0 | 2 | -14.200 | 0.0% | 0.0%-65.8% | 0.00 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `USD_JPY` | 17 | 14 | 3 | +0.453 | 82.4% | 59.0%-93.8% | 1.08 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `EUR_USD` | 8 | 7 | 1 | +6.250 | 87.5% | 52.9%-97.8% | 16.15 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_bb_rsi_mr` | `GBP_USD` | 10 | 3 | 7 | -4.390 | 30.0% | 10.8%-60.3% | 0.09 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_bb_rsi_mr` | `USD_JPY` | 17 | 10 | 7 | -0.076 | 58.8% | 36.0%-78.4% | 0.98 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `EUR_GBP` | 9 | 3 | 6 | -1.656 | 33.3% | 12.1%-64.6% | 0.39 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `dt_sr_channel_reversal` | `EUR_JPY` | 63 | 30 | 33 | -3.283 | 47.6% | 35.8%-59.7% | 0.42 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_USD` | 15 | 5 | 10 | -0.433 | 33.3% | 15.2%-58.3% | 0.87 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `dt_sr_channel_reversal` | `GBP_JPY` | 52 | 20 | 32 | -4.698 | 38.5% | 26.5%-52.0% | 0.26 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `GBP_USD` | 20 | 8 | 12 | -1.580 | 40.0% | 21.9%-61.3% | 0.54 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `dt_sr_channel_reversal` | `USD_JPY` | 46 | 26 | 20 | -2.157 | 56.5% | 42.2%-69.8% | 0.53 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema200_trend_reversal` | `USD_JPY` | 6 | 5 | 1 | -0.867 | 83.3% | 43.6%-97.0% | 0.79 | `EMA200_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`<br>`EMA200_TREND_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_ribbon_ride` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_RIBBON_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_trend_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `engulfing_bb` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_pips_hunter` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_PIPS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_trend_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_TREND_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_vol_break` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_VOL_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `AUD_JPY` | 7 | 2 | 5 | -7.143 | 28.6% | 8.2%-64.1% | 0.19 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `EUR_JPY` | 5 | 3 | 2 | -2.960 | 60.0% | 23.1%-88.2% | 0.47 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `EUR_USD` | 1 | 0 | 1 | -6.000 | 0.0% | 0.0%-79.3% | 0.00 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_JPY` | 2 | 1 | 1 | -6.550 | 50.0% | 9.5%-90.5% | 0.22 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_USD` | 3 | 2 | 1 | -3.167 | 66.7% | 20.8%-93.9% | 0.50 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `USD_JPY` | 6 | 3 | 3 | -6.550 | 50.0% | 18.8%-81.2% | 0.05 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `USD_JPY` | 2 | 2 | 0 | +0.800 | 100.0% | 34.2%-100.0% | n/a | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `intraday_seasonality` | `AUD_JPY` | 1 | 1 | 0 | +11.800 | 100.0% | 20.7%-100.0% | n/a | `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `jpy_basket_trend` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `JPY_BASKET_TREND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `keltner_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `lin_reg_channel` | `EUR_USD` | 16 | 8 | 8 | +0.875 | 50.0% | 28.0%-72.0% | 1.52 | `LIN_REG_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `london_breakout` | `EUR_USD` | 33 | 16 | 17 | -0.424 | 48.5% | 32.5%-64.8% | 0.76 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_breakout` | `USD_JPY` | 12 | 7 | 5 | +1.775 | 58.3% | 32.0%-80.7% | 1.44 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_ny_swing` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_NY_SWING_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `EUR_USD` | 2 | 2 | 0 | +5.100 | 100.0% | 34.2%-100.0% | n/a | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `GBP_USD` | 6 | 4 | 2 | -3.200 | 66.7% | 30.0%-90.3% | 0.36 | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_shrapnel` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_SHRAPNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_mr_hybrid` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_MR_HYBRID_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_regime_switch` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_trend_perfect` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_TREND_PERFECT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `USD_CHF` | 2 | 0 | 2 | -4.250 | 0.0% | 0.0%-65.8% | 0.00 | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `USD_JPY` | 5 | 2 | 3 | -0.580 | 40.0% | 11.8%-76.9% | 0.69 | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `EUR_USD` | 5 | 2 | 3 | -0.680 | 40.0% | 11.8%-76.9% | 0.29 | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `USD_JPY` | 5 | 1 | 4 | -1.560 | 20.0% | 3.6%-62.4% | 0.57 | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_regime_range_cascade_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `EUR_USD` | 2 | 1 | 1 | -1.900 | 50.0% | 9.5%-90.5% | 0.17 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `GBP_USD` | 3 | 0 | 3 | -3.133 | 0.0% | 0.0%-56.2% | 0.00 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `USD_CHF` | 3 | 1 | 2 | -0.733 | 33.3% | 6.1%-79.2% | 0.44 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `USD_JPY` | 9 | 4 | 5 | -1.044 | 44.4% | 18.9%-73.3% | 0.43 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `EUR_JPY` | 1 | 1 | 0 | +9.800 | 100.0% | 20.7%-100.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `GBP_JPY` | 1 | 1 | 0 | +12.000 | 100.0% | 20.7%-100.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `USD_JPY` | 5 | 1 | 4 | -11.020 | 20.0% | 3.6%-62.4% | 0.01 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ofi_mr` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `OFI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `EUR_USD` | 5 | 2 | 3 | -0.580 | 40.0% | 11.8%-76.9% | 0.89 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `GBP_USD` | 5 | 4 | 1 | +0.660 | 80.0% | 37.6%-96.4% | 1.49 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `USD_JPY` | 4 | 1 | 3 | -10.725 | 25.0% | 4.6%-69.9% | 0.02 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `post_news_vol` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `EUR_JPY` | 2 | 2 | 0 | +6.550 | 100.0% | 34.2%-100.0% | n/a | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `EUR_USD` | 1 | 1 | 0 | +10.700 | 100.0% | 20.7%-100.0% | n/a | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `USD_JPY` | 1 | 1 | 0 | +10.300 | 100.0% | 20.7%-100.0% | n/a | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `session_vol_expansion` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SESSION_VOL_EXPANSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `squeeze_release_momentum` | `EUR_USD` | 1 | 0 | 1 | -5.000 | 0.0% | 0.0%-79.3% | 0.00 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `squeeze_release_momentum` | `GBP_USD` | 1 | 1 | 0 | +1.200 | 100.0% | 20.7%-100.0% | n/a | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_anti_hunt_bounce` | `EUR_JPY` | 13 | 7 | 6 | -3.054 | 53.8% | 29.1%-76.8% | 0.46 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `EUR_USD` | 7 | 4 | 3 | -7.057 | 57.1% | 25.0%-84.2% | 0.06 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_JPY` | 5 | 3 | 2 | -1.800 | 60.0% | 23.1%-88.2% | 0.59 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `USD_JPY` | 5 | 1 | 4 | -8.660 | 20.0% | 3.6%-62.4% | 0.02 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `AUD_JPY` | 40 | 18 | 22 | -2.903 | 45.0% | 30.7%-60.2% | 0.48 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `USD_JPY` | 36 | 15 | 21 | -3.097 | 41.7% | 27.1%-57.8% | 0.40 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_channel_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_fib_confluence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_liquidity_grab` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_LIQUIDITY_GRAB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `stoch_trend_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `three_bar_reversal` | `EUR_USD` | 15 | 6 | 9 | -1.400 | 40.0% | 19.8%-64.3% | 0.44 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `three_bar_reversal` | `GBP_USD` | 11 | 5 | 6 | -0.900 | 45.5% | 21.3%-72.0% | 0.68 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `three_bar_reversal` | `USD_JPY` | 27 | 8 | 19 | -1.648 | 29.6% | 15.9%-48.5% | 0.46 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `AUD_JPY` | 2 | 1 | 1 | -5.950 | 50.0% | 9.5%-90.5% | 0.12 | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `EUR_JPY` | 4 | 1 | 3 | -12.875 | 25.0% | 4.6%-69.9% | 0.02 | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `USD_JPY` | 6 | 4 | 2 | +0.850 | 66.7% | 30.0%-90.3% | 1.13 | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_range_breakout_up` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_RANGE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trend_rebound` | `EUR_USD` | 18 | 7 | 11 | -0.117 | 38.9% | 20.3%-61.4% | 0.92 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `GBP_USD` | 3 | 1 | 2 | +0.767 | 33.3% | 6.1%-79.2% | 1.56 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `USD_JPY` | 7 | 4 | 3 | -0.357 | 57.1% | 25.0%-84.2% | 0.79 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `EUR_GBP` | 18 | 9 | 9 | -1.028 | 50.0% | 29.0%-71.0% | 0.62 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trendline_sweep` | `EUR_USD` | 9 | 5 | 4 | -4.356 | 55.6% | 26.7%-81.1% | 0.09 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `GBP_USD` | 26 | 18 | 8 | -1.065 | 69.2% | 50.0%-83.5% | 0.63 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `turtle_soup` | `GBP_USD` | 2 | 1 | 1 | -2.350 | 50.0% | 9.5%-90.5% | 0.20 | `TURTLE_SOUP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tvsm` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TVSM_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `v_reversal` | `USD_JPY` | 11 | 6 | 5 | -0.809 | 54.5% | 28.0%-78.7% | 0.48 | `V_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vbp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `VBP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `GBP_JPY` | 1 | 1 | 0 | +13.100 | 100.0% | 20.7%-100.0% | n/a | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `USD_JPY` | 4 | 2 | 2 | +0.000 | 50.0% | 15.0%-85.0% | 1.00 | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_momentum_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `EUR_USD` | 26 | 2 | 24 | -3.131 | 7.7% | 2.1%-24.1% | 0.05 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `GBP_USD` | 10 | 6 | 4 | +0.680 | 60.0% | 31.3%-83.2% | 1.69 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `USD_JPY` | 8 | 5 | 3 | -0.738 | 62.5% | 30.6%-86.3% | 0.73 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `AUD_JPY` | 6 | 4 | 2 | -1.350 | 66.7% | 30.0%-90.3% | 0.64 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_GBP` | 4 | 1 | 3 | -0.325 | 25.0% | 4.6%-69.9% | 0.72 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_JPY` | 4 | 3 | 1 | +2.150 | 75.0% | 30.1%-95.4% | 1.42 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_USD` | 2 | 0 | 2 | -6.600 | 0.0% | 0.0%-65.8% | 0.00 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_JPY` | 2 | 2 | 0 | +10.250 | 100.0% | 34.2%-100.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_USD` | 4 | 1 | 3 | -5.225 | 25.0% | 4.6%-69.9% | 0.06 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `USD_JPY` | 1 | 0 | 1 | -0.300 | 0.0% | 0.0%-79.3% | 0.00 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `wick_imbalance_reversion` | `AUD_JPY` | 42 | 19 | 23 | -2.574 | 45.2% | 31.2%-60.1% | 0.55 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `EUR_JPY` | 16 | 9 | 7 | -0.700 | 56.2% | 33.2%-76.9% | 0.83 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `EUR_USD` | 20 | 8 | 12 | -3.370 | 40.0% | 21.9%-61.3% | 0.18 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `GBP_JPY` | 11 | 6 | 5 | -5.591 | 54.5% | 28.0%-78.7% | 0.35 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `GBP_USD` | 23 | 8 | 15 | -2.857 | 34.8% | 18.8%-55.1% | 0.33 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `USD_JPY` | 17 | 14 | 3 | +1.688 | 82.4% | 59.0%-93.8% | 2.06 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `xs_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
