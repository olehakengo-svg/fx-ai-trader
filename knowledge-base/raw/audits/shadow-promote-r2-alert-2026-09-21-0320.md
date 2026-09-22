# SHADOW_PROMOTE R2 Alert - 2026-09-21T03:20:53.444920+00:00

- Source: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=2000`
- Lookback: `30d`
- Filters: `is_shadow=1`, `pnl_pips IS NOT NULL`, `dedup_violation != 1`, XAU instruments excluded
- Gate: `N >= 10 and EV < 0` -> WARN; `N >= 30 and EV < 0` -> CRITICAL
- Mode: read-only; no env vars, strategy code, tier-master, or DB writes

## Summary

- Promoted strategies: 65
- Cells: 125
- OK: 105
- WARN: 14
- CRITICAL: 6

## WARN / CRITICAL

| Severity | Strategy | Instrument | N | EV | WR | Wilson lower | PF |
|---|---|---|---:|---:|---:|---:|---:|
| **WARN** | `bb_squeeze_breakout` | `EUR_USD` | 10 | -2.370 | 10.0% | 1.8% | 0.03 |
| **WARN** | `dt_sr_channel_reversal` | `EUR_GBP` | 10 | -1.450 | 30.0% | 10.8% | 0.43 |
| **CRITICAL** | `dt_sr_channel_reversal` | `EUR_JPY` | 34 | -4.897 | 38.2% | 23.9% | 0.30 |
| **WARN** | `dt_sr_channel_reversal` | `EUR_USD` | 11 | -2.282 | 36.4% | 15.2% | 0.35 |
| **CRITICAL** | `dt_sr_channel_reversal` | `GBP_JPY` | 37 | -5.143 | 40.5% | 26.3% | 0.22 |
| **WARN** | `dt_sr_channel_reversal` | `GBP_USD` | 27 | -1.596 | 37.0% | 21.5% | 0.45 |
| **CRITICAL** | `dt_sr_channel_reversal` | `USD_JPY` | 32 | -2.706 | 59.4% | 42.3% | 0.36 |
| **CRITICAL** | `london_breakout` | `EUR_USD` | 33 | -1.091 | 39.4% | 24.7% | 0.42 |
| **WARN** | `sr_anti_hunt_bounce` | `EUR_JPY` | 11 | -4.091 | 54.5% | 28.0% | 0.30 |
| **CRITICAL** | `sr_break_retest` | `AUD_JPY` | 38 | -0.497 | 55.3% | 39.7% | 0.89 |
| **WARN** | `sr_break_retest` | `USD_JPY` | 23 | -4.083 | 34.8% | 18.8% | 0.26 |
| **WARN** | `three_bar_reversal` | `EUR_USD` | 12 | -1.225 | 33.3% | 13.8% | 0.51 |
| **WARN** | `three_bar_reversal` | `USD_JPY` | 19 | -0.079 | 36.8% | 19.1% | 0.97 |
| **WARN** | `trend_rebound` | `EUR_USD` | 17 | -0.241 | 35.3% | 17.3% | 0.84 |
| **WARN** | `trendline_sweep` | `GBP_USD` | 24 | -1.829 | 58.3% | 38.8% | 0.40 |
| **WARN** | `vol_surge_detector` | `EUR_USD` | 18 | -2.922 | 11.1% | 3.1% | 0.03 |
| **CRITICAL** | `wick_imbalance_reversion` | `AUD_JPY` | 49 | -1.892 | 53.1% | 39.4% | 0.60 |
| **WARN** | `wick_imbalance_reversion` | `EUR_USD` | 12 | -4.050 | 25.0% | 8.9% | 0.18 |
| **WARN** | `wick_imbalance_reversion` | `GBP_JPY` | 11 | -3.073 | 54.5% | 28.0% | 0.57 |
| **WARN** | `wick_imbalance_reversion` | `GBP_USD` | 23 | -3.074 | 30.4% | 15.6% | 0.19 |

## R2 Demote Manual Action

For each CRITICAL cell, manually verify and then remove the relevant Render env var:

- `dt_sr_channel_reversal` x `EUR_JPY`: remove `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE`
- `dt_sr_channel_reversal` x `GBP_JPY`: remove `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE`
- `dt_sr_channel_reversal` x `USD_JPY`: remove `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE`
- `london_breakout` x `EUR_USD`: remove `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `AUD_JPY`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `wick_imbalance_reversion` x `AUD_JPY`: remove `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`, `WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE`

Code review locations if manual demotion is chosen:
- `strategies/daytrade/__init__.py` `split_shadow_always` / `SHADOW_ALWAYS_STRATEGIES`
- `strategies/hourly/__init__.py` `split_shadow_always`
- `strategies/scalp/__init__.py` `split_shadow_always`

## Apply Demote Suggestion

- Registry: `/home/runner/work/fx-ai-trader/fx-ai-trader/modules/shadow_demote_registry.py`
- Missing CRITICAL cells: `6`
- Add `('dt_sr_channel_reversal', 'EUR_JPY')`
- Add `('dt_sr_channel_reversal', 'GBP_JPY')`
- Add `('dt_sr_channel_reversal', 'USD_JPY')`
- Add `('london_breakout', 'EUR_USD')`
- Add `('sr_break_retest', 'AUD_JPY')`
- Add `('wick_imbalance_reversion', 'AUD_JPY')`

## All Cells

| Severity | Strategy | Instrument | N | Wins | Losses | EV | WR | Wilson 95% | PF | Env |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| OK | `adx_trend_continuation` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ADX_TREND_CONTINUATION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `asia_range_fade_v1` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ASIA_RANGE_FADE_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `atr_regime_break` | `EUR_JPY` | 1 | 1 | 0 | +2.100 | 100.0% | 20.7%-100.0% | n/a | `ALPHA_ATR_REGIME_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_rsi_ema_aligned` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `BB_RSI_EMA_ALIGNED_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `bb_squeeze_breakout` | `EUR_USD` | 10 | 1 | 9 | -2.370 | 10.0% | 1.8%-40.4% | 0.03 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `GBP_USD` | 4 | 0 | 4 | -3.800 | 0.0% | 0.0%-49.0% | 0.00 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `USD_CHF` | 1 | 0 | 1 | -2.000 | 0.0% | 0.0%-79.3% | 0.00 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `USD_JPY` | 9 | 3 | 6 | -0.711 | 33.3% | 12.1%-64.6% | 0.73 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `confluence_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CONFLUENCE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `cpd_divergence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CPD_DIVERGENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `AUD_JPY` | 3 | 3 | 0 | +4.567 | 100.0% | 43.8%-100.0% | n/a | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `AUD_USD` | 6 | 2 | 4 | -6.883 | 33.3% | 9.7%-70.0% | 0.06 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `EUR_USD` | 4 | 2 | 2 | -4.775 | 50.0% | 15.0%-85.0% | 0.41 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `NZD_USD` | 3 | 0 | 3 | -12.400 | 0.0% | 0.0%-56.2% | 0.00 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `USD_JPY` | 12 | 11 | 1 | +3.325 | 91.7% | 64.6%-98.5% | 2.13 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `EUR_USD` | 8 | 6 | 2 | +4.438 | 75.0% | 40.9%-92.9% | 4.74 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `GBP_USD` | 9 | 5 | 4 | -2.233 | 55.6% | 26.7%-81.1% | 0.24 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `USD_JPY` | 14 | 8 | 6 | +0.457 | 57.1% | 32.6%-78.6% | 1.11 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_GBP` | 10 | 3 | 7 | -1.450 | 30.0% | 10.8%-60.3% | 0.43 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `dt_sr_channel_reversal` | `EUR_JPY` | 34 | 13 | 21 | -4.897 | 38.2% | 23.9%-55.0% | 0.30 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_USD` | 11 | 4 | 7 | -2.282 | 36.4% | 15.2%-64.6% | 0.35 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `dt_sr_channel_reversal` | `GBP_JPY` | 37 | 15 | 22 | -5.143 | 40.5% | 26.3%-56.5% | 0.22 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `GBP_USD` | 27 | 10 | 17 | -1.596 | 37.0% | 21.5%-55.8% | 0.45 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `dt_sr_channel_reversal` | `USD_JPY` | 32 | 19 | 13 | -2.706 | 59.4% | 42.3%-74.5% | 0.36 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema200_trend_reversal` | `USD_JPY` | 1 | 1 | 0 | +11.000 | 100.0% | 20.7%-100.0% | n/a | `EMA200_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`<br>`EMA200_TREND_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_ribbon_ride` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_RIBBON_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_trend_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `engulfing_bb` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_pips_hunter` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_PIPS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_trend_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_TREND_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_vol_break` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_VOL_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `AUD_JPY` | 4 | 1 | 3 | -5.350 | 25.0% | 4.6%-69.9% | 0.33 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `EUR_JPY` | 5 | 3 | 2 | -2.960 | 60.0% | 23.1%-88.2% | 0.47 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_JPY` | 1 | 0 | 1 | -16.700 | 0.0% | 0.0%-79.3% | 0.00 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_USD` | 1 | 0 | 1 | -9.000 | 0.0% | 0.0%-79.3% | 0.00 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `USD_JPY` | 6 | 3 | 3 | -6.550 | 50.0% | 18.8%-81.2% | 0.05 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `GBP_USD` | 3 | 2 | 1 | -4.900 | 66.7% | 20.8%-93.9% | 0.14 | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `intraday_seasonality` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `jpy_basket_trend` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `JPY_BASKET_TREND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `keltner_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `lin_reg_channel` | `EUR_USD` | 10 | 7 | 3 | +1.900 | 70.0% | 39.7%-89.2% | 2.65 | `LIN_REG_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `london_breakout` | `EUR_USD` | 33 | 13 | 20 | -1.091 | 39.4% | 24.7%-56.3% | 0.42 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_breakout` | `USD_JPY` | 7 | 5 | 2 | +5.171 | 71.4% | 35.9%-91.8% | 2.85 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_ny_swing` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_NY_SWING_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `EUR_USD` | 1 | 0 | 1 | -4.100 | 0.0% | 0.0%-79.3% | 0.00 | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `GBP_USD` | 3 | 1 | 2 | -7.333 | 33.3% | 6.1%-79.2% | 0.27 | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_shrapnel` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_SHRAPNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_mr_hybrid` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_MR_HYBRID_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_regime_switch` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_trend_perfect` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_TREND_PERFECT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `EUR_USD` | 3 | 0 | 3 | -5.700 | 0.0% | 0.0%-56.2% | 0.00 | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `GBP_USD` | 1 | 1 | 0 | +1.300 | 100.0% | 20.7%-100.0% | n/a | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `USD_JPY` | 2 | 1 | 1 | -1.500 | 50.0% | 9.5%-90.5% | 0.12 | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `EUR_USD` | 6 | 2 | 4 | -1.100 | 33.3% | 9.7%-70.0% | 0.17 | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `USD_JPY` | 1 | 0 | 1 | -6.500 | 0.0% | 0.0%-79.3% | 0.00 | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_regime_range_cascade_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `EUR_USD` | 3 | 1 | 2 | -1.100 | 33.3% | 6.1%-79.2% | 0.20 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `GBP_USD` | 1 | 0 | 1 | -1.000 | 0.0% | 0.0%-79.3% | 0.00 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `USD_CHF` | 2 | 0 | 2 | -1.150 | 0.0% | 0.0%-65.8% | 0.00 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `USD_JPY` | 1 | 1 | 0 | +0.800 | 100.0% | 20.7%-100.0% | n/a | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `EUR_JPY` | 1 | 1 | 0 | +9.800 | 100.0% | 20.7%-100.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `GBP_JPY` | 1 | 1 | 0 | +12.000 | 100.0% | 20.7%-100.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `GBP_USD` | 1 | 0 | 1 | -7.600 | 0.0% | 0.0%-79.3% | 0.00 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `USD_JPY` | 1 | 0 | 1 | -20.900 | 0.0% | 0.0%-79.3% | 0.00 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ofi_mr` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `OFI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `EUR_USD` | 3 | 1 | 2 | -6.200 | 33.3% | 6.1%-79.2% | 0.12 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `GBP_USD` | 5 | 3 | 2 | -1.480 | 60.0% | 23.1%-88.2% | 0.27 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `USD_JPY` | 3 | 1 | 2 | -10.567 | 33.3% | 6.1%-79.2% | 0.02 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `post_news_vol` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `AUD_JPY` | 1 | 0 | 1 | -8.300 | 0.0% | 0.0%-79.3% | 0.00 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `USD_JPY` | 1 | 1 | 0 | +10.300 | 100.0% | 20.7%-100.0% | n/a | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `session_vol_expansion` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SESSION_VOL_EXPANSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `squeeze_release_momentum` | `EUR_USD` | 1 | 0 | 1 | -7.800 | 0.0% | 0.0%-79.3% | 0.00 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `squeeze_release_momentum` | `GBP_USD` | 1 | 0 | 1 | -14.300 | 0.0% | 0.0%-79.3% | 0.00 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_anti_hunt_bounce` | `EUR_JPY` | 11 | 6 | 5 | -4.091 | 54.5% | 28.0%-78.7% | 0.30 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `EUR_USD` | 7 | 4 | 3 | -7.057 | 57.1% | 25.0%-84.2% | 0.06 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_JPY` | 4 | 3 | 1 | +0.450 | 75.0% | 30.1%-95.4% | 1.16 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_USD` | 2 | 0 | 2 | -2.900 | 0.0% | 0.0%-65.8% | 0.00 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `USD_JPY` | 3 | 1 | 2 | -8.467 | 33.3% | 6.1%-79.2% | 0.03 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `AUD_JPY` | 38 | 21 | 17 | -0.497 | 55.3% | 39.7%-69.9% | 0.89 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_break_retest` | `USD_JPY` | 23 | 8 | 15 | -4.083 | 34.8% | 18.8%-55.1% | 0.26 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_channel_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_fib_confluence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_liquidity_grab` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_LIQUIDITY_GRAB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `stoch_trend_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `three_bar_reversal` | `EUR_USD` | 12 | 4 | 8 | -1.225 | 33.3% | 13.8%-60.9% | 0.51 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `GBP_USD` | 5 | 2 | 3 | -0.740 | 40.0% | 11.8%-76.9% | 0.69 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `three_bar_reversal` | `USD_JPY` | 19 | 7 | 12 | -0.079 | 36.8% | 19.1%-59.0% | 0.97 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `AUD_JPY` | 6 | 3 | 3 | -2.683 | 50.0% | 18.8%-81.2% | 0.47 | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `EUR_JPY` | 8 | 1 | 7 | -10.512 | 12.5% | 2.2%-47.1% | 0.02 | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `USD_JPY` | 5 | 1 | 4 | -9.640 | 20.0% | 3.6%-62.4% | 0.13 | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_range_breakout_up` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_RANGE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trend_rebound` | `EUR_USD` | 17 | 6 | 11 | -0.241 | 35.3% | 17.3%-58.7% | 0.84 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `GBP_USD` | 1 | 1 | 0 | +6.400 | 100.0% | 20.7%-100.0% | n/a | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `USD_JPY` | 9 | 3 | 6 | -2.156 | 33.3% | 12.1%-64.6% | 0.11 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trendline_sweep` | `EUR_GBP` | 6 | 1 | 5 | -4.167 | 16.7% | 3.0%-56.4% | 0.08 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trendline_sweep` | `EUR_USD` | 8 | 4 | 4 | +0.788 | 50.0% | 21.5%-78.5% | 1.19 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `GBP_USD` | 24 | 14 | 10 | -1.829 | 58.3% | 38.8%-75.5% | 0.40 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `turtle_soup` | `GBP_USD` | 4 | 3 | 1 | -0.700 | 75.0% | 30.1%-95.4% | 0.58 | `TURTLE_SOUP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tvsm` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TVSM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `v_reversal` | `USD_JPY` | 7 | 4 | 3 | -0.243 | 57.1% | 25.0%-84.2% | 0.88 | `V_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vbp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `VBP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `EUR_JPY` | 1 | 1 | 0 | +9.300 | 100.0% | 20.7%-100.0% | n/a | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `USD_JPY` | 2 | 0 | 2 | -2.500 | 0.0% | 0.0%-65.8% | 0.00 | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_momentum_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `EUR_USD` | 18 | 2 | 16 | -2.922 | 11.1% | 3.1%-32.8% | 0.03 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `GBP_USD` | 4 | 3 | 1 | +2.125 | 75.0% | 30.1%-95.4% | 86.00 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `USD_JPY` | 8 | 4 | 4 | -2.025 | 50.0% | 21.5%-78.5% | 0.45 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `AUD_JPY` | 5 | 4 | 1 | -1.160 | 80.0% | 37.6%-96.4% | 0.71 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_GBP` | 7 | 1 | 6 | -2.229 | 14.3% | 2.6%-51.3% | 0.17 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_JPY` | 4 | 3 | 1 | +1.775 | 75.0% | 30.1%-95.4% | 1.77 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `EUR_USD` | 2 | 0 | 2 | -4.450 | 0.0% | 0.0%-65.8% | 0.00 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_JPY` | 1 | 1 | 0 | +11.200 | 100.0% | 20.7%-100.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_USD` | 1 | 0 | 1 | -5.100 | 0.0% | 0.0%-79.3% | 0.00 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `USD_JPY` | 2 | 0 | 2 | -4.100 | 0.0% | 0.0%-65.8% | 0.00 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `wick_imbalance_reversion` | `AUD_JPY` | 49 | 26 | 23 | -1.892 | 53.1% | 39.4%-66.3% | 0.60 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_JPY` | 10 | 6 | 4 | +0.090 | 60.0% | 31.3%-83.2% | 1.02 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `EUR_USD` | 12 | 3 | 9 | -4.050 | 25.0% | 8.9%-53.2% | 0.18 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `GBP_JPY` | 11 | 6 | 5 | -3.073 | 54.5% | 28.0%-78.7% | 0.57 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `GBP_USD` | 23 | 7 | 16 | -3.074 | 30.4% | 15.6%-50.9% | 0.19 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `USD_JPY` | 19 | 14 | 5 | +2.705 | 73.7% | 51.2%-88.2% | 2.36 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `xs_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
