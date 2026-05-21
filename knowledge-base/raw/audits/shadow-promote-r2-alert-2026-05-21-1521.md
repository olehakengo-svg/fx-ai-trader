# SHADOW_PROMOTE R2 Alert - 2026-05-21T15:21:20.794313+00:00

- Source: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=2000`
- Lookback: `30d`
- Filters: `is_shadow=1`, `pnl_pips IS NOT NULL`, XAU instruments excluded
- Gate: `N >= 10 and EV < 0` -> WARN; `N >= 30 and EV < 0` -> CRITICAL
- Mode: read-only; no env vars, strategy code, tier-master, or DB writes

## Summary

- Promoted strategies: 66
- Cells: 143
- OK: 107
- WARN: 23
- CRITICAL: 13

## WARN / CRITICAL

| Severity | Strategy | Instrument | N | EV | WR | Wilson lower | PF |
|---|---|---|---:|---:|---:|---:|---:|
| **WARN** | `bb_rsi_reversion` | `GBP_USD` | 21 | -1.681 | 28.6% | 13.8% | 0.50 |
| **WARN** | `bb_rsi_reversion` | `USD_CHF` | 12 | -3.358 | 0.0% | 0.0% | 0.00 |
| **WARN** | `dt_bb_rsi_mr` | `GBP_USD` | 27 | -1.748 | 29.6% | 15.9% | 0.65 |
| **WARN** | `dt_sr_channel_reversal` | `EUR_JPY` | 10 | -8.290 | 10.0% | 1.8% | 0.10 |
| **WARN** | `ema_trend_scalp` | `EUR_USD` | 19 | -0.663 | 21.1% | 8.5% | 0.69 |
| **CRITICAL** | `ema_trend_scalp` | `GBP_USD` | 39 | -1.103 | 17.9% | 9.0% | 0.64 |
| **CRITICAL** | `ema_trend_scalp` | `USD_JPY` | 82 | -1.399 | 17.1% | 10.5% | 0.57 |
| **CRITICAL** | `engulfing_bb` | `EUR_USD` | 33 | -0.700 | 24.2% | 12.8% | 0.70 |
| **WARN** | `engulfing_bb` | `GBP_USD` | 14 | -3.800 | 14.3% | 4.0% | 0.27 |
| **WARN** | `lin_reg_channel` | `EUR_USD` | 25 | -3.292 | 24.0% | 11.5% | 0.33 |
| **CRITICAL** | `london_breakout` | `GBP_USD` | 30 | -3.450 | 6.7% | 1.8% | 0.19 |
| **WARN** | `ma_regime_switch` | `USD_JPY` | 25 | -1.856 | 20.0% | 8.9% | 0.31 |
| **WARN** | `sr_anti_hunt_bounce` | `EUR_USD` | 22 | -4.473 | 4.5% | 0.8% | 0.04 |
| **WARN** | `sr_anti_hunt_bounce` | `GBP_JPY` | 13 | -0.215 | 23.1% | 8.2% | 0.96 |
| **WARN** | `sr_anti_hunt_bounce` | `USD_JPY` | 15 | -2.220 | 0.0% | 0.0% | 0.00 |
| **WARN** | `sr_break_retest` | `EUR_JPY` | 24 | -2.017 | 29.2% | 14.9% | 0.71 |
| **WARN** | `sr_break_retest` | `GBP_JPY` | 26 | -7.981 | 7.7% | 2.1% | 0.22 |
| **CRITICAL** | `sr_break_retest` | `GBP_USD` | 44 | -3.041 | 27.3% | 16.3% | 0.52 |
| **WARN** | `sr_channel_reversal` | `EUR_USD` | 14 | -0.507 | 21.4% | 7.6% | 0.79 |
| **CRITICAL** | `sr_channel_reversal` | `GBP_USD` | 55 | -2.009 | 23.6% | 14.4% | 0.50 |
| **WARN** | `sr_channel_reversal` | `USD_CHF` | 11 | -1.500 | 0.0% | 0.0% | 0.00 |
| **CRITICAL** | `sr_channel_reversal` | `USD_JPY` | 38 | -2.211 | 15.8% | 7.4% | 0.35 |
| **WARN** | `sr_fib_confluence` | `EUR_GBP` | 24 | -1.146 | 16.7% | 6.7% | 0.62 |
| **WARN** | `sr_fib_confluence` | `EUR_JPY` | 17 | -7.912 | 11.8% | 3.3% | 0.46 |
| **CRITICAL** | `sr_fib_confluence` | `EUR_USD` | 39 | -1.718 | 23.1% | 12.6% | 0.58 |
| **CRITICAL** | `sr_fib_confluence` | `GBP_JPY` | 41 | -9.329 | 12.2% | 5.3% | 0.42 |
| **CRITICAL** | `sr_fib_confluence` | `GBP_USD` | 72 | -3.554 | 19.4% | 12.0% | 0.50 |
| **WARN** | `trendline_sweep` | `GBP_USD` | 11 | -14.982 | 9.1% | 1.6% | 0.02 |
| **CRITICAL** | `vol_momentum_scalp` | `GBP_USD` | 44 | -1.889 | 18.2% | 9.5% | 0.54 |
| **WARN** | `vol_momentum_scalp` | `USD_JPY` | 14 | -3.179 | 7.1% | 1.3% | 0.14 |
| **WARN** | `vol_surge_detector` | `USD_JPY` | 12 | -3.383 | 16.7% | 4.7% | 0.24 |
| **WARN** | `wick_imbalance_reversion` | `EUR_JPY` | 14 | -2.100 | 21.4% | 7.6% | 0.66 |
| **WARN** | `wick_imbalance_reversion` | `EUR_USD` | 14 | -1.307 | 21.4% | 7.6% | 0.65 |
| **WARN** | `wick_imbalance_reversion` | `USD_JPY` | 14 | -1.900 | 21.4% | 7.6% | 0.70 |
| **CRITICAL** | `xs_momentum` | `EUR_USD` | 33 | -0.864 | 30.3% | 17.4% | 0.83 |
| **CRITICAL** | `xs_momentum` | `GBP_USD` | 31 | -3.555 | 25.8% | 13.7% | 0.57 |

## R2 Demote Manual Action

For each CRITICAL cell, manually verify and then remove the relevant Render env var:

- `ema_trend_scalp` x `GBP_USD`: remove `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE`
- `ema_trend_scalp` x `USD_JPY`: remove `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE`
- `engulfing_bb` x `EUR_USD`: remove `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE`
- `london_breakout` x `GBP_USD`: remove `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `GBP_USD`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_channel_reversal` x `GBP_USD`: remove `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_channel_reversal` x `USD_JPY`: remove `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_fib_confluence` x `EUR_USD`: remove `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_fib_confluence` x `GBP_JPY`: remove `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_fib_confluence` x `GBP_USD`: remove `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE`
- `vol_momentum_scalp` x `GBP_USD`: remove `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`, `VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE`
- `xs_momentum` x `EUR_USD`: remove `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`
- `xs_momentum` x `GBP_USD`: remove `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`

Code review locations if manual demotion is chosen:
- `strategies/daytrade/__init__.py` `split_shadow_always` / `SHADOW_ALWAYS_STRATEGIES`
- `strategies/hourly/__init__.py` `split_shadow_always`
- `strategies/scalp/__init__.py` `split_shadow_always`

## Apply Demote Suggestion

- Registry: `/home/runner/work/fx-ai-trader/fx-ai-trader/modules/shadow_demote_registry.py`
- Missing CRITICAL cells: `13`
- Add `('ema_trend_scalp', 'GBP_USD')`
- Add `('ema_trend_scalp', 'USD_JPY')`
- Add `('engulfing_bb', 'EUR_USD')`
- Add `('london_breakout', 'GBP_USD')`
- Add `('sr_break_retest', 'GBP_USD')`
- Add `('sr_channel_reversal', 'GBP_USD')`
- Add `('sr_channel_reversal', 'USD_JPY')`
- Add `('sr_fib_confluence', 'EUR_USD')`
- Add `('sr_fib_confluence', 'GBP_JPY')`
- Add `('sr_fib_confluence', 'GBP_USD')`
- Add `('vol_momentum_scalp', 'GBP_USD')`
- Add `('xs_momentum', 'EUR_USD')`
- Add `('xs_momentum', 'GBP_USD')`

## All Cells

| Severity | Strategy | Instrument | N | Wins | Losses | EV | WR | Wilson 95% | PF | Env |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| OK | `adx_trend_continuation` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ADX_TREND_CONTINUATION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `asia_range_fade_v1` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ASIA_RANGE_FADE_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `atr_regime_break` | `EUR_JPY` | 1 | 0 | 1 | -15.100 | 0.0% | 0.0%-79.3% | 0.00 | `ALPHA_ATR_REGIME_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `atr_regime_break` | `GBP_JPY` | 1 | 1 | 0 | +5.500 | 100.0% | 20.7%-100.0% | n/a | `ALPHA_ATR_REGIME_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `atr_regime_break` | `USD_JPY` | 2 | 1 | 1 | +2.850 | 50.0% | 9.5%-90.5% | 1.43 | `ALPHA_ATR_REGIME_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_rsi_ema_aligned` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `BB_RSI_EMA_ALIGNED_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_rsi_reversion` | `EUR_USD` | 21 | 9 | 12 | +0.014 | 42.9% | 24.5%-63.5% | 1.01 | `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `bb_rsi_reversion` | `GBP_USD` | 21 | 6 | 15 | -1.681 | 28.6% | 13.8%-50.0% | 0.50 | `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `bb_rsi_reversion` | `USD_CHF` | 12 | 0 | 12 | -3.358 | 0.0% | 0.0%-24.3% | 0.00 | `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_rsi_reversion` | `USD_JPY` | 32 | 15 | 17 | +0.397 | 46.9% | 30.9%-63.6% | 1.16 | `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `EUR_USD` | 7 | 0 | 7 | -2.886 | 0.0% | 0.0%-35.4% | 0.00 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `GBP_USD` | 1 | 1 | 0 | +2.500 | 100.0% | 20.7%-100.0% | n/a | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `USD_JPY` | 1 | 0 | 1 | -3.700 | 0.0% | 0.0%-79.3% | 0.00 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `confluence_scalp` | `EUR_USD` | 1 | 0 | 1 | -3.300 | 0.0% | 0.0%-79.3% | 0.00 | `CONFLUENCE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `cpd_divergence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CPD_DIVERGENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `EUR_AUD` | 6 | 3 | 3 | +12.550 | 50.0% | 18.8%-81.2% | 1.86 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `NZD_USD` | 1 | 0 | 1 | -18.400 | 0.0% | 0.0%-79.3% | 0.00 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `USD_CAD` | 3 | 0 | 3 | -23.400 | 0.0% | 0.0%-56.2% | 0.00 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `EUR_USD` | 10 | 7 | 3 | +5.380 | 70.0% | 39.7%-89.2% | 4.45 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_bb_rsi_mr` | `GBP_USD` | 27 | 8 | 19 | -1.748 | 29.6% | 15.9%-48.5% | 0.65 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `USD_JPY` | 12 | 5 | 7 | +5.475 | 41.7% | 19.3%-68.0% | 4.11 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `EUR_JPY` | 2 | 1 | 1 | +12.700 | 50.0% | 9.5%-90.5% | 15.94 | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `GBP_USD` | 3 | 0 | 3 | -3.833 | 0.0% | 0.0%-56.2% | 0.00 | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `USD_JPY` | 2 | 1 | 1 | +7.800 | 50.0% | 9.5%-90.5% | n/a | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `EUR_JPY` | 10 | 1 | 9 | -8.290 | 10.0% | 1.8%-40.4% | 0.10 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `EUR_USD` | 2 | 1 | 1 | -0.300 | 50.0% | 9.5%-90.5% | 0.79 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `GBP_JPY` | 3 | 0 | 3 | -13.367 | 0.0% | 0.0%-56.2% | 0.00 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `GBP_USD` | 9 | 0 | 9 | -9.544 | 0.0% | 0.0%-29.9% | 0.00 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `USD_JPY` | 7 | 4 | 3 | +4.543 | 57.1% | 25.0%-84.2% | 2.78 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema200_trend_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA200_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`<br>`EMA200_TREND_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `EUR_JPY` | 3 | 1 | 2 | +3.733 | 33.3% | 6.1%-79.2% | 1.51 | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `GBP_JPY` | 2 | 0 | 2 | -19.850 | 0.0% | 0.0%-65.8% | 0.00 | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `USD_JPY` | 1 | 0 | 1 | -10.400 | 0.0% | 0.0%-79.3% | 0.00 | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_pullback` | `USD_JPY` | 1 | 0 | 1 | -0.800 | 0.0% | 0.0%-79.3% | 0.00 | `EMA_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_ribbon_ride` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_RIBBON_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `ema_trend_scalp` | `EUR_USD` | 19 | 4 | 15 | -0.663 | 21.1% | 8.5%-43.3% | 0.69 | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `ema_trend_scalp` | `GBP_USD` | 39 | 7 | 32 | -1.103 | 17.9% | 9.0%-32.7% | 0.64 | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_trend_scalp` | `USD_CHF` | 1 | 0 | 1 | -0.100 | 0.0% | 0.0%-79.3% | 0.00 | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `ema_trend_scalp` | `USD_JPY` | 82 | 14 | 68 | -1.399 | 17.1% | 10.5%-26.6% | 0.57 | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `engulfing_bb` | `EUR_USD` | 33 | 8 | 25 | -0.700 | 24.2% | 12.8%-41.0% | 0.70 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `engulfing_bb` | `GBP_USD` | 14 | 2 | 12 | -3.800 | 14.3% | 4.0%-39.9% | 0.27 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `engulfing_bb` | `USD_CHF` | 6 | 0 | 6 | -1.550 | 0.0% | 0.0%-39.0% | 0.00 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `engulfing_bb` | `USD_JPY` | 19 | 5 | 14 | +1.384 | 26.3% | 11.8%-48.8% | 1.47 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_pips_hunter` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_PIPS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_trend_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_TREND_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_vol_break` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_VOL_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `EUR_JPY` | 2 | 1 | 1 | -5.450 | 50.0% | 9.5%-90.5% | 0.11 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `EUR_USD` | 1 | 1 | 0 | +2.400 | 100.0% | 20.7%-100.0% | n/a | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_USD` | 1 | 0 | 1 | -14.200 | 0.0% | 0.0%-79.3% | 0.00 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `USD_JPY` | 1 | 0 | 1 | -12.100 | 0.0% | 0.0%-79.3% | 0.00 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `GBP_USD` | 3 | 3 | 0 | +38.700 | 100.0% | 43.8%-100.0% | n/a | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `USD_JPY` | 1 | 1 | 0 | +24.800 | 100.0% | 20.7%-100.0% | n/a | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `intraday_seasonality` | `GBP_USD` | 4 | 3 | 1 | +11.075 | 75.0% | 30.1%-95.4% | 14.84 | `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `jpy_basket_trend` | `EUR_JPY` | 5 | 0 | 5 | -3.620 | 0.0% | 0.0%-43.4% | 0.00 | `JPY_BASKET_TREND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `keltner_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `lin_reg_channel` | `EUR_USD` | 25 | 6 | 19 | -3.292 | 24.0% | 11.5%-43.4% | 0.33 | `LIN_REG_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_breakout` | `EUR_USD` | 6 | 1 | 5 | -3.333 | 16.7% | 3.0%-56.4% | 0.10 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `london_breakout` | `GBP_USD` | 30 | 2 | 28 | -3.450 | 6.7% | 1.8%-21.3% | 0.19 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_breakout` | `USD_CHF` | 3 | 0 | 3 | -2.700 | 0.0% | 0.0%-56.2% | 0.00 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_ny_swing` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_NY_SWING_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `GBP_USD` | 4 | 0 | 4 | -7.700 | 0.0% | 0.0%-49.0% | 0.00 | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_shrapnel` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_SHRAPNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_mr_hybrid` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_MR_HYBRID_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `ma_regime_switch` | `USD_JPY` | 25 | 5 | 20 | -1.856 | 20.0% | 8.9%-39.1% | 0.31 | `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_trend_perfect` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_TREND_PERFECT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `EUR_USD` | 1 | 1 | 0 | +8.700 | 100.0% | 20.7%-100.0% | n/a | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `USD_JPY` | 4 | 1 | 3 | -0.825 | 25.0% | 4.6%-69.9% | 0.64 | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_regime_range_cascade_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `EUR_USD` | 2 | 0 | 2 | -1.600 | 0.0% | 0.0%-65.8% | 0.00 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `EUR_JPY` | 4 | 0 | 4 | -13.250 | 0.0% | 0.0%-49.0% | 0.00 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `EUR_USD` | 18 | 8 | 10 | +2.533 | 44.4% | 24.6%-66.3% | 1.76 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `GBP_JPY` | 3 | 1 | 2 | +6.733 | 33.3% | 6.1%-79.2% | 1.55 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `GBP_USD` | 14 | 7 | 7 | +0.407 | 50.0% | 26.8%-73.2% | 1.06 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `USD_JPY` | 30 | 9 | 21 | +1.620 | 30.0% | 16.7%-47.9% | 1.29 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ofi_mr` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `OFI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `EUR_USD` | 7 | 1 | 6 | +0.343 | 14.3% | 2.6%-51.3% | 5.00 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `GBP_USD` | 16 | 11 | 5 | +8.969 | 68.8% | 44.4%-85.8% | 9.29 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `USD_JPY` | 2 | 0 | 2 | -7.100 | 0.0% | 0.0%-65.8% | 0.00 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `post_news_vol` | `EUR_USD` | 3 | 0 | 3 | -16.767 | 0.0% | 0.0%-56.2% | 0.00 | `POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `post_news_vol` | `GBP_USD` | 1 | 0 | 1 | -10.700 | 0.0% | 0.0%-79.3% | 0.00 | `POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `post_news_vol` | `USD_JPY` | 3 | 2 | 1 | +13.233 | 66.7% | 20.8%-93.9% | 18.26 | `POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `EUR_JPY` | 2 | 0 | 2 | -10.650 | 0.0% | 0.0%-65.8% | 0.00 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `EUR_USD` | 1 | 0 | 1 | -7.300 | 0.0% | 0.0%-79.3% | 0.00 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `GBP_USD` | 1 | 0 | 1 | -10.300 | 0.0% | 0.0%-79.3% | 0.00 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `session_vol_expansion` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SESSION_VOL_EXPANSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `squeeze_release_momentum` | `GBP_USD` | 6 | 1 | 5 | -4.900 | 16.7% | 3.0%-56.4% | 0.09 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `EUR_JPY` | 5 | 1 | 4 | -2.840 | 20.0% | 3.6%-62.4% | 0.43 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_anti_hunt_bounce` | `EUR_USD` | 22 | 1 | 21 | -4.473 | 4.5% | 0.8%-21.8% | 0.04 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_anti_hunt_bounce` | `GBP_JPY` | 13 | 3 | 10 | -0.215 | 23.1% | 8.2%-50.3% | 0.96 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_USD` | 7 | 6 | 1 | +7.214 | 85.7% | 48.7%-97.4% | 9.86 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_anti_hunt_bounce` | `USD_JPY` | 15 | 0 | 15 | -2.220 | 0.0% | 0.0%-20.4% | 0.00 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_break_retest` | `EUR_JPY` | 24 | 7 | 17 | -2.017 | 29.2% | 14.9%-49.2% | 0.71 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_break_retest` | `GBP_JPY` | 26 | 2 | 24 | -7.981 | 7.7% | 2.1%-24.1% | 0.22 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `GBP_USD` | 44 | 12 | 32 | -3.041 | 27.3% | 16.3%-41.8% | 0.52 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_break_retest` | `USD_JPY` | 39 | 14 | 25 | +0.485 | 35.9% | 22.7%-51.6% | 1.12 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_channel_reversal` | `EUR_USD` | 14 | 3 | 11 | -0.507 | 21.4% | 7.6%-47.6% | 0.79 | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_channel_reversal` | `GBP_USD` | 55 | 13 | 42 | -2.009 | 23.6% | 14.4%-36.3% | 0.50 | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_channel_reversal` | `USD_CHF` | 11 | 0 | 11 | -1.500 | 0.0% | 0.0%-25.9% | 0.00 | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_channel_reversal` | `USD_JPY` | 38 | 6 | 32 | -2.211 | 15.8% | 7.4%-30.4% | 0.35 | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_fib_confluence` | `EUR_GBP` | 24 | 4 | 20 | -1.146 | 16.7% | 6.7%-35.9% | 0.62 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_fib_confluence` | `EUR_JPY` | 17 | 2 | 15 | -7.912 | 11.8% | 3.3%-34.3% | 0.46 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_fib_confluence` | `EUR_USD` | 39 | 9 | 30 | -1.718 | 23.1% | 12.6%-38.3% | 0.58 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_fib_confluence` | `GBP_JPY` | 41 | 5 | 36 | -9.329 | 12.2% | 5.3%-25.5% | 0.42 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_fib_confluence` | `GBP_USD` | 72 | 14 | 58 | -3.554 | 19.4% | 12.0%-30.0% | 0.50 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_fib_confluence` | `USD_JPY` | 19 | 5 | 14 | +2.105 | 26.3% | 11.8%-48.8% | 1.23 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_liquidity_grab` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_LIQUIDITY_GRAB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `stoch_trend_pullback` | `EUR_USD` | 3 | 0 | 3 | -3.500 | 0.0% | 0.0%-56.2% | 0.00 | `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `stoch_trend_pullback` | `USD_JPY` | 2 | 0 | 2 | -2.650 | 0.0% | 0.0%-65.8% | 0.00 | `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `EUR_USD` | 7 | 0 | 7 | -4.157 | 0.0% | 0.0%-35.4% | 0.00 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `GBP_USD` | 3 | 0 | 3 | -6.467 | 0.0% | 0.0%-56.2% | 0.00 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `USD_JPY` | 1 | 0 | 1 | -0.300 | 0.0% | 0.0%-79.3% | 0.00 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_range_breakout_up` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_RANGE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `EUR_USD` | 2 | 0 | 2 | -1.600 | 0.0% | 0.0%-65.8% | 0.00 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `USD_JPY` | 5 | 2 | 3 | +2.900 | 40.0% | 11.8%-76.9% | 2.73 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trendline_sweep` | `EUR_GBP` | 2 | 0 | 2 | -4.600 | 0.0% | 0.0%-65.8% | 0.00 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trendline_sweep` | `EUR_USD` | 18 | 6 | 12 | +1.422 | 33.3% | 16.3%-56.3% | 1.32 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `GBP_USD` | 11 | 1 | 10 | -14.982 | 9.1% | 1.6%-37.7% | 0.02 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `turtle_soup` | `GBP_USD` | 9 | 1 | 8 | -3.956 | 11.1% | 2.0%-43.5% | 0.40 | `TURTLE_SOUP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tvsm` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TVSM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `v_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `V_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vbp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `VBP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `EUR_JPY` | 1 | 0 | 1 | -8.400 | 0.0% | 0.0%-79.3% | 0.00 | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `USD_JPY` | 3 | 2 | 1 | +47.200 | 66.7% | 20.8%-93.9% | 14.36 | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `vol_momentum_scalp` | `GBP_USD` | 44 | 8 | 36 | -1.889 | 18.2% | 9.5%-32.0% | 0.54 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_momentum_scalp` | `USD_JPY` | 14 | 1 | 13 | -3.179 | 7.1% | 1.3%-31.5% | 0.14 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `EUR_USD` | 3 | 0 | 3 | -4.933 | 0.0% | 0.0%-56.2% | 0.00 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `GBP_USD` | 11 | 5 | 6 | +2.864 | 45.5% | 21.3%-72.0% | 2.29 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `USD_CHF` | 2 | 0 | 2 | -3.100 | 0.0% | 0.0%-65.8% | 0.00 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `USD_JPY` | 12 | 2 | 10 | -3.383 | 16.7% | 4.7%-44.8% | 0.24 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_JPY` | 3 | 0 | 3 | -19.500 | 0.0% | 0.0%-56.2% | 0.00 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_USD` | 1 | 1 | 0 | +1.700 | 100.0% | 20.7%-100.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `USD_JPY` | 2 | 1 | 1 | +0.950 | 50.0% | 9.5%-90.5% | 1.09 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_GBP` | 5 | 5 | 0 | +13.180 | 100.0% | 56.6%-100.0% | n/a | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `EUR_JPY` | 14 | 3 | 11 | -2.100 | 21.4% | 7.6%-47.6% | 0.66 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `EUR_USD` | 14 | 3 | 11 | -1.307 | 21.4% | 7.6%-47.6% | 0.65 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `GBP_JPY` | 7 | 2 | 5 | -1.886 | 28.6% | 8.2%-64.1% | 0.82 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `GBP_USD` | 20 | 10 | 10 | +5.055 | 50.0% | 29.9%-70.1% | 2.48 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `USD_JPY` | 14 | 3 | 11 | -1.900 | 21.4% | 7.6%-47.6% | 0.70 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `EUR_USD` | 33 | 10 | 23 | -0.864 | 30.3% | 17.4%-47.3% | 0.83 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `GBP_USD` | 31 | 8 | 23 | -3.555 | 25.8% | 13.7%-43.2% | 0.57 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `xs_momentum` | `USD_JPY` | 21 | 9 | 12 | +0.890 | 42.9% | 24.5%-63.5% | 1.14 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
