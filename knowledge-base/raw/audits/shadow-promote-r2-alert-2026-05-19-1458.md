# SHADOW_PROMOTE R2 Alert - 2026-05-19T14:58:27.686548+00:00

- Source: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=2000`
- Lookback: `30d`
- Filters: `is_shadow=1`, `pnl_pips IS NOT NULL`, XAU instruments excluded
- Gate: `N >= 10 and EV < 0` -> WARN; `N >= 30 and EV < 0` -> CRITICAL
- Mode: read-only; no env vars, strategy code, tier-master, or DB writes

## Summary

- Promoted strategies: 66
- Cells: 143
- OK: 111
- WARN: 17
- CRITICAL: 15

## WARN / CRITICAL

| Severity | Strategy | Instrument | N | EV | WR | Wilson lower | PF |
|---|---|---|---:|---:|---:|---:|---:|
| **WARN** | `bb_rsi_reversion` | `EUR_USD` | 28 | -0.564 | 35.7% | 20.7% | 0.74 |
| **WARN** | `bb_rsi_reversion` | `GBP_USD` | 29 | -2.303 | 20.7% | 9.8% | 0.34 |
| **WARN** | `bb_rsi_reversion` | `USD_CHF` | 12 | -3.358 | 0.0% | 0.0% | 0.00 |
| **WARN** | `bb_squeeze_breakout` | `EUR_USD` | 10 | -2.940 | 0.0% | 0.0% | 0.00 |
| **WARN** | `dt_bb_rsi_mr` | `GBP_USD` | 22 | -6.545 | 9.1% | 2.5% | 0.11 |
| **CRITICAL** | `ema_trend_scalp` | `EUR_USD` | 42 | -0.919 | 19.0% | 10.0% | 0.64 |
| **CRITICAL** | `ema_trend_scalp` | `GBP_USD` | 59 | -0.997 | 18.6% | 10.7% | 0.70 |
| **CRITICAL** | `ema_trend_scalp` | `USD_JPY` | 142 | -1.760 | 20.4% | 14.6% | 0.54 |
| **CRITICAL** | `engulfing_bb` | `EUR_USD` | 30 | -0.923 | 23.3% | 11.8% | 0.63 |
| **WARN** | `engulfing_bb` | `GBP_USD` | 14 | -3.386 | 14.3% | 4.0% | 0.29 |
| **WARN** | `lin_reg_channel` | `EUR_USD` | 21 | -3.071 | 28.6% | 13.8% | 0.39 |
| **WARN** | `london_breakout` | `GBP_USD` | 28 | -3.221 | 7.1% | 2.0% | 0.21 |
| **WARN** | `ma_regime_switch` | `USD_JPY` | 21 | -1.700 | 23.8% | 10.6% | 0.37 |
| **WARN** | `sr_anti_hunt_bounce` | `EUR_USD` | 18 | -5.278 | 5.6% | 1.0% | 0.04 |
| **WARN** | `sr_break_retest` | `EUR_JPY` | 20 | -4.615 | 20.0% | 8.1% | 0.44 |
| **WARN** | `sr_break_retest` | `GBP_JPY` | 23 | -3.617 | 17.4% | 7.0% | 0.63 |
| **CRITICAL** | `sr_break_retest` | `GBP_USD` | 37 | -1.181 | 37.8% | 24.1% | 0.81 |
| **WARN** | `sr_channel_reversal` | `EUR_USD` | 14 | -0.507 | 21.4% | 7.6% | 0.79 |
| **CRITICAL** | `sr_channel_reversal` | `GBP_USD` | 47 | -2.449 | 21.3% | 12.0% | 0.42 |
| **CRITICAL** | `sr_channel_reversal` | `USD_JPY` | 38 | -2.211 | 15.8% | 7.4% | 0.35 |
| **WARN** | `sr_fib_confluence` | `EUR_GBP` | 21 | -0.743 | 19.0% | 7.7% | 0.74 |
| **CRITICAL** | `sr_fib_confluence` | `EUR_JPY` | 31 | -13.132 | 6.5% | 1.8% | 0.22 |
| **CRITICAL** | `sr_fib_confluence` | `EUR_USD` | 32 | -0.428 | 28.1% | 15.6% | 0.89 |
| **CRITICAL** | `sr_fib_confluence` | `GBP_JPY` | 59 | -12.727 | 8.5% | 3.7% | 0.27 |
| **CRITICAL** | `sr_fib_confluence` | `GBP_USD` | 65 | -2.820 | 23.1% | 14.5% | 0.60 |
| **CRITICAL** | `sr_fib_confluence` | `USD_JPY` | 32 | -5.494 | 15.6% | 6.9% | 0.55 |
| **CRITICAL** | `vol_momentum_scalp` | `GBP_USD` | 42 | -1.352 | 21.4% | 11.7% | 0.66 |
| **WARN** | `vol_momentum_scalp` | `USD_JPY` | 12 | -3.058 | 8.3% | 1.5% | 0.17 |
| **WARN** | `vol_surge_detector` | `USD_JPY` | 14 | -4.993 | 14.3% | 4.0% | 0.16 |
| **WARN** | `wick_imbalance_reversion` | `USD_JPY` | 10 | -1.720 | 30.0% | 10.8% | 0.78 |
| **CRITICAL** | `xs_momentum` | `EUR_USD` | 36 | -1.294 | 30.6% | 18.0% | 0.79 |
| **CRITICAL** | `xs_momentum` | `GBP_USD` | 36 | -3.733 | 25.0% | 13.8% | 0.56 |

## R2 Demote Manual Action

For each CRITICAL cell, manually verify and then remove the relevant Render env var:

- `ema_trend_scalp` x `EUR_USD`: remove `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE`
- `ema_trend_scalp` x `GBP_USD`: remove `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE`
- `ema_trend_scalp` x `USD_JPY`: remove `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE`
- `engulfing_bb` x `EUR_USD`: remove `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `GBP_USD`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_channel_reversal` x `GBP_USD`: remove `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_channel_reversal` x `USD_JPY`: remove `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_fib_confluence` x `EUR_JPY`: remove `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_fib_confluence` x `EUR_USD`: remove `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_fib_confluence` x `GBP_JPY`: remove `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_fib_confluence` x `GBP_USD`: remove `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_fib_confluence` x `USD_JPY`: remove `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE`
- `vol_momentum_scalp` x `GBP_USD`: remove `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`, `VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE`
- `xs_momentum` x `EUR_USD`: remove `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`
- `xs_momentum` x `GBP_USD`: remove `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`

Code review locations if manual demotion is chosen:
- `strategies/daytrade/__init__.py` `split_shadow_always` / `SHADOW_ALWAYS_STRATEGIES`
- `strategies/hourly/__init__.py` `split_shadow_always`
- `strategies/scalp/__init__.py` `split_shadow_always`

## Apply Demote Suggestion

- Registry: `/home/runner/work/fx-ai-trader/fx-ai-trader/modules/shadow_demote_registry.py`
- Missing CRITICAL cells: `15`
- Add `('ema_trend_scalp', 'EUR_USD')`
- Add `('ema_trend_scalp', 'GBP_USD')`
- Add `('ema_trend_scalp', 'USD_JPY')`
- Add `('engulfing_bb', 'EUR_USD')`
- Add `('sr_break_retest', 'GBP_USD')`
- Add `('sr_channel_reversal', 'GBP_USD')`
- Add `('sr_channel_reversal', 'USD_JPY')`
- Add `('sr_fib_confluence', 'EUR_JPY')`
- Add `('sr_fib_confluence', 'EUR_USD')`
- Add `('sr_fib_confluence', 'GBP_JPY')`
- Add `('sr_fib_confluence', 'GBP_USD')`
- Add `('sr_fib_confluence', 'USD_JPY')`
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
| WARN | `bb_rsi_reversion` | `EUR_USD` | 28 | 10 | 18 | -0.564 | 35.7% | 20.7%-54.2% | 0.74 | `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `bb_rsi_reversion` | `GBP_USD` | 29 | 6 | 23 | -2.303 | 20.7% | 9.8%-38.4% | 0.34 | `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `bb_rsi_reversion` | `USD_CHF` | 12 | 0 | 12 | -3.358 | 0.0% | 0.0%-24.3% | 0.00 | `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_rsi_reversion` | `USD_JPY` | 48 | 23 | 25 | +0.471 | 47.9% | 34.5%-61.7% | 1.17 | `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `bb_squeeze_breakout` | `EUR_USD` | 10 | 0 | 10 | -2.940 | 0.0% | 0.0%-27.8% | 0.00 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `GBP_USD` | 5 | 3 | 2 | +3.680 | 60.0% | 23.1%-88.2% | 5.18 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `USD_JPY` | 1 | 0 | 1 | -3.700 | 0.0% | 0.0%-79.3% | 0.00 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `confluence_scalp` | `EUR_USD` | 1 | 0 | 1 | -3.300 | 0.0% | 0.0%-79.3% | 0.00 | `CONFLUENCE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `cpd_divergence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CPD_DIVERGENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `EUR_AUD` | 3 | 3 | 0 | +54.367 | 100.0% | 43.8%-100.0% | n/a | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `USD_CAD` | 1 | 0 | 1 | -23.900 | 0.0% | 0.0%-79.3% | 0.00 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `EUR_USD` | 5 | 2 | 3 | +1.640 | 40.0% | 11.8%-76.9% | 1.53 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_bb_rsi_mr` | `GBP_USD` | 22 | 2 | 20 | -6.545 | 9.1% | 2.5%-27.8% | 0.11 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `USD_JPY` | 14 | 7 | 7 | +5.436 | 50.0% | 26.8%-73.2% | 3.23 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `EUR_JPY` | 2 | 1 | 1 | +12.700 | 50.0% | 9.5%-90.5% | 15.94 | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `GBP_JPY` | 1 | 0 | 1 | -20.000 | 0.0% | 0.0%-79.3% | 0.00 | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `GBP_USD` | 3 | 0 | 3 | -3.833 | 0.0% | 0.0%-56.2% | 0.00 | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `USD_JPY` | 2 | 1 | 1 | +7.800 | 50.0% | 9.5%-90.5% | n/a | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `EUR_JPY` | 14 | 5 | 9 | +0.093 | 35.7% | 16.3%-61.2% | 1.01 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `EUR_USD` | 2 | 1 | 1 | -0.300 | 50.0% | 9.5%-90.5% | 0.79 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `GBP_JPY` | 7 | 3 | 4 | -0.200 | 42.9% | 15.8%-75.0% | 0.98 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `GBP_USD` | 9 | 0 | 9 | -9.544 | 0.0% | 0.0%-29.9% | 0.00 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `USD_JPY` | 5 | 1 | 4 | -4.820 | 20.0% | 3.6%-62.4% | 0.28 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema200_trend_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA200_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`<br>`EMA200_TREND_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `EUR_JPY` | 3 | 1 | 2 | +3.733 | 33.3% | 6.1%-79.2% | 1.51 | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `EUR_USD` | 2 | 1 | 1 | +5.550 | 50.0% | 9.5%-90.5% | 2.66 | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `GBP_JPY` | 3 | 0 | 3 | -20.100 | 0.0% | 0.0%-56.2% | 0.00 | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `GBP_USD` | 1 | 0 | 1 | -11.400 | 0.0% | 0.0%-79.3% | 0.00 | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `USD_JPY` | 1 | 0 | 1 | -10.400 | 0.0% | 0.0%-79.3% | 0.00 | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_pullback` | `USD_JPY` | 3 | 2 | 1 | +15.600 | 66.7% | 20.8%-93.9% | 59.50 | `EMA_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_ribbon_ride` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_RIBBON_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `ema_trend_scalp` | `EUR_USD` | 42 | 8 | 34 | -0.919 | 19.0% | 10.0%-33.3% | 0.64 | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `ema_trend_scalp` | `GBP_USD` | 59 | 11 | 48 | -0.997 | 18.6% | 10.7%-30.4% | 0.70 | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `ema_trend_scalp` | `USD_JPY` | 142 | 29 | 113 | -1.760 | 20.4% | 14.6%-27.8% | 0.54 | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `engulfing_bb` | `EUR_USD` | 30 | 7 | 23 | -0.923 | 23.3% | 11.8%-40.9% | 0.63 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `engulfing_bb` | `GBP_USD` | 14 | 2 | 12 | -3.386 | 14.3% | 4.0%-39.9% | 0.29 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `engulfing_bb` | `USD_CHF` | 3 | 0 | 3 | -1.033 | 0.0% | 0.0%-56.2% | 0.00 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `engulfing_bb` | `USD_JPY` | 20 | 5 | 15 | +1.105 | 25.0% | 11.2%-46.9% | 1.37 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_pips_hunter` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_PIPS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_trend_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_TREND_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_vol_break` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_VOL_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `EUR_JPY` | 2 | 1 | 1 | -5.450 | 50.0% | 9.5%-90.5% | 0.11 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `EUR_USD` | 1 | 1 | 0 | +2.400 | 100.0% | 20.7%-100.0% | n/a | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_USD` | 1 | 0 | 1 | -14.200 | 0.0% | 0.0%-79.3% | 0.00 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `USD_JPY` | 1 | 0 | 1 | -12.100 | 0.0% | 0.0%-79.3% | 0.00 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `GBP_USD` | 1 | 1 | 0 | +34.700 | 100.0% | 20.7%-100.0% | n/a | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `USD_JPY` | 1 | 1 | 0 | +24.800 | 100.0% | 20.7%-100.0% | n/a | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `intraday_seasonality` | `GBP_USD` | 4 | 3 | 1 | +11.075 | 75.0% | 30.1%-95.4% | 14.84 | `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `jpy_basket_trend` | `EUR_JPY` | 6 | 1 | 5 | +1.000 | 16.7% | 3.0%-56.4% | 1.33 | `JPY_BASKET_TREND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `keltner_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `lin_reg_channel` | `EUR_USD` | 21 | 6 | 15 | -3.071 | 28.6% | 13.8%-50.0% | 0.39 | `LIN_REG_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_breakout` | `EUR_USD` | 2 | 1 | 1 | +0.400 | 50.0% | 9.5%-90.5% | 1.57 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `london_breakout` | `GBP_USD` | 28 | 2 | 26 | -3.221 | 7.1% | 2.0%-22.6% | 0.21 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_breakout` | `USD_CHF` | 1 | 0 | 1 | -2.400 | 0.0% | 0.0%-79.3% | 0.00 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_ny_swing` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_NY_SWING_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `GBP_USD` | 4 | 0 | 4 | -7.700 | 0.0% | 0.0%-49.0% | 0.00 | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_shrapnel` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_SHRAPNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_mr_hybrid` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_MR_HYBRID_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `ma_regime_switch` | `USD_JPY` | 21 | 5 | 16 | -1.700 | 23.8% | 10.6%-45.1% | 0.37 | `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_trend_perfect` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_TREND_PERFECT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `EUR_USD` | 2 | 1 | 1 | +1.350 | 50.0% | 9.5%-90.5% | 1.45 | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `USD_JPY` | 8 | 3 | 5 | +1.050 | 37.5% | 13.7%-69.4% | 1.55 | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_regime_range_cascade_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `EUR_USD` | 2 | 0 | 2 | -1.600 | 0.0% | 0.0%-65.8% | 0.00 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `EUR_JPY` | 4 | 0 | 4 | -13.250 | 0.0% | 0.0%-49.0% | 0.00 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `EUR_USD` | 18 | 8 | 10 | +2.533 | 44.4% | 24.6%-66.3% | 1.76 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `GBP_JPY` | 1 | 1 | 0 | +57.000 | 100.0% | 20.7%-100.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `GBP_USD` | 14 | 7 | 7 | +0.407 | 50.0% | 26.8%-73.2% | 1.06 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `USD_JPY` | 25 | 9 | 16 | +3.264 | 36.0% | 20.2%-55.5% | 1.60 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ofi_mr` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `OFI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `EUR_USD` | 7 | 1 | 6 | +0.343 | 14.3% | 2.6%-51.3% | 5.00 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `GBP_USD` | 14 | 9 | 5 | +6.679 | 64.3% | 38.8%-83.7% | 6.40 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `USD_JPY` | 2 | 0 | 2 | -7.100 | 0.0% | 0.0%-65.8% | 0.00 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `post_news_vol` | `EUR_USD` | 3 | 0 | 3 | -16.767 | 0.0% | 0.0%-56.2% | 0.00 | `POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `post_news_vol` | `GBP_USD` | 1 | 0 | 1 | -10.700 | 0.0% | 0.0%-79.3% | 0.00 | `POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `post_news_vol` | `USD_JPY` | 3 | 2 | 1 | +13.233 | 66.7% | 20.8%-93.9% | 18.26 | `POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `EUR_JPY` | 2 | 0 | 2 | -10.650 | 0.0% | 0.0%-65.8% | 0.00 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `EUR_USD` | 1 | 0 | 1 | -7.300 | 0.0% | 0.0%-79.3% | 0.00 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `session_vol_expansion` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SESSION_VOL_EXPANSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `squeeze_release_momentum` | `GBP_USD` | 7 | 1 | 6 | -5.329 | 14.3% | 2.6%-51.3% | 0.07 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `EUR_JPY` | 5 | 1 | 4 | -2.840 | 20.0% | 3.6%-62.4% | 0.43 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_anti_hunt_bounce` | `EUR_USD` | 18 | 1 | 17 | -5.278 | 5.6% | 1.0%-25.8% | 0.04 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_JPY` | 7 | 1 | 6 | -3.443 | 14.3% | 2.6%-51.3% | 0.64 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_USD` | 7 | 6 | 1 | +7.214 | 85.7% | 48.7%-97.4% | 9.86 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `USD_JPY` | 5 | 0 | 5 | -2.780 | 0.0% | 0.0%-43.4% | 0.00 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_break_retest` | `EUR_JPY` | 20 | 4 | 16 | -4.615 | 20.0% | 8.1%-41.6% | 0.44 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_break_retest` | `GBP_JPY` | 23 | 4 | 19 | -3.617 | 17.4% | 7.0%-37.1% | 0.63 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `GBP_USD` | 37 | 14 | 23 | -1.181 | 37.8% | 24.1%-53.9% | 0.81 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_break_retest` | `USD_JPY` | 34 | 13 | 21 | +0.429 | 38.2% | 23.9%-55.0% | 1.09 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_channel_reversal` | `EUR_USD` | 14 | 3 | 11 | -0.507 | 21.4% | 7.6%-47.6% | 0.79 | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_channel_reversal` | `GBP_USD` | 47 | 10 | 37 | -2.449 | 21.3% | 12.0%-34.9% | 0.42 | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_channel_reversal` | `USD_CHF` | 7 | 0 | 7 | -2.229 | 0.0% | 0.0%-35.4% | 0.00 | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_channel_reversal` | `USD_JPY` | 38 | 6 | 32 | -2.211 | 15.8% | 7.4%-30.4% | 0.35 | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_fib_confluence` | `EUR_GBP` | 21 | 4 | 17 | -0.743 | 19.0% | 7.7%-40.0% | 0.74 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_fib_confluence` | `EUR_JPY` | 31 | 2 | 29 | -13.132 | 6.5% | 1.8%-20.7% | 0.22 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_fib_confluence` | `EUR_USD` | 32 | 9 | 23 | -0.428 | 28.1% | 15.6%-45.4% | 0.89 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_fib_confluence` | `GBP_JPY` | 59 | 5 | 54 | -12.727 | 8.5% | 3.7%-18.4% | 0.27 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_fib_confluence` | `GBP_USD` | 65 | 15 | 50 | -2.820 | 23.1% | 14.5%-34.6% | 0.60 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_fib_confluence` | `USD_JPY` | 32 | 5 | 27 | -5.494 | 15.6% | 6.9%-31.8% | 0.55 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_liquidity_grab` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_LIQUIDITY_GRAB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `stoch_trend_pullback` | `EUR_USD` | 4 | 0 | 4 | -3.375 | 0.0% | 0.0%-49.0% | 0.00 | `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `stoch_trend_pullback` | `GBP_USD` | 2 | 0 | 2 | -3.900 | 0.0% | 0.0%-65.8% | 0.00 | `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `stoch_trend_pullback` | `USD_JPY` | 7 | 0 | 7 | -11.014 | 0.0% | 0.0%-35.4% | 0.00 | `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `EUR_USD` | 7 | 0 | 7 | -4.157 | 0.0% | 0.0%-35.4% | 0.00 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `GBP_USD` | 1 | 0 | 1 | -5.300 | 0.0% | 0.0%-79.3% | 0.00 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `USD_JPY` | 1 | 0 | 1 | -0.300 | 0.0% | 0.0%-79.3% | 0.00 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_range_breakout_up` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_RANGE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `EUR_USD` | 4 | 1 | 3 | -0.775 | 25.0% | 4.6%-69.9% | 0.65 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `GBP_USD` | 1 | 1 | 0 | +12.700 | 100.0% | 20.7%-100.0% | n/a | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `USD_JPY` | 9 | 3 | 6 | +1.656 | 33.3% | 12.1%-64.6% | 1.81 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trendline_sweep` | `EUR_USD` | 5 | 2 | 3 | +6.180 | 40.0% | 11.8%-76.9% | 4.06 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trendline_sweep` | `GBP_USD` | 1 | 1 | 0 | +2.600 | 100.0% | 20.7%-100.0% | n/a | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `turtle_soup` | `GBP_USD` | 9 | 1 | 8 | -3.956 | 11.1% | 2.0%-43.5% | 0.40 | `TURTLE_SOUP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tvsm` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TVSM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `v_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `V_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vbp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `VBP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `EUR_JPY` | 1 | 0 | 1 | -8.400 | 0.0% | 0.0%-79.3% | 0.00 | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `USD_JPY` | 3 | 2 | 1 | +47.200 | 66.7% | 20.8%-93.9% | 14.36 | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `vol_momentum_scalp` | `GBP_USD` | 42 | 9 | 33 | -1.352 | 21.4% | 11.7%-35.9% | 0.66 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_momentum_scalp` | `USD_JPY` | 12 | 1 | 11 | -3.058 | 8.3% | 1.5%-35.4% | 0.17 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `EUR_USD` | 6 | 2 | 4 | -0.833 | 33.3% | 9.7%-70.0% | 0.75 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `GBP_USD` | 15 | 5 | 10 | +1.280 | 33.3% | 15.2%-58.3% | 1.52 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `USD_JPY` | 14 | 2 | 12 | -4.993 | 14.3% | 4.0%-39.9% | 0.16 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_JPY` | 3 | 0 | 3 | -19.500 | 0.0% | 0.0%-56.2% | 0.00 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_USD` | 1 | 1 | 0 | +1.700 | 100.0% | 20.7%-100.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `USD_JPY` | 2 | 1 | 1 | +0.950 | 50.0% | 9.5%-90.5% | 1.09 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_GBP` | 5 | 5 | 0 | +13.180 | 100.0% | 56.6%-100.0% | n/a | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_JPY` | 10 | 3 | 7 | +2.030 | 30.0% | 10.8%-60.3% | 1.55 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_USD` | 4 | 0 | 4 | -5.750 | 0.0% | 0.0%-49.0% | 0.00 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `GBP_JPY` | 7 | 2 | 5 | -1.886 | 28.6% | 8.2%-64.1% | 0.82 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `GBP_USD` | 13 | 8 | 5 | +8.700 | 61.5% | 35.5%-82.3% | 6.57 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `USD_JPY` | 10 | 3 | 7 | -1.720 | 30.0% | 10.8%-60.3% | 0.78 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `EUR_USD` | 36 | 11 | 25 | -1.294 | 30.6% | 18.0%-46.9% | 0.79 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `GBP_USD` | 36 | 9 | 27 | -3.733 | 25.0% | 13.8%-41.1% | 0.56 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `xs_momentum` | `USD_JPY` | 16 | 7 | 9 | +1.050 | 43.8% | 23.1%-66.8% | 1.15 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
