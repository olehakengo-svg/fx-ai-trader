# SHADOW_PROMOTE R2 Alert - 2026-05-16T02:45:50.626788+00:00

- Source: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=2000`
- Lookback: `30d`
- Filters: `is_shadow=1`, `pnl_pips IS NOT NULL`, XAU instruments excluded
- Gate: `N >= 10 and EV < 0` -> WARN; `N >= 30 and EV < 0` -> CRITICAL
- Mode: read-only; no env vars, strategy code, tier-master, or DB writes

## Summary

- Promoted strategies: 66
- Cells: 136
- OK: 108
- WARN: 13
- CRITICAL: 15

## WARN / CRITICAL

| Severity | Strategy | Instrument | N | EV | WR | Wilson lower | PF |
|---|---|---|---:|---:|---:|---:|---:|
| **CRITICAL** | `bb_rsi_reversion` | `EUR_USD` | 33 | -0.336 | 36.4% | 22.2% | 0.83 |
| **CRITICAL** | `bb_rsi_reversion` | `GBP_USD` | 31 | -2.294 | 19.4% | 9.2% | 0.33 |
| **WARN** | `dt_bb_rsi_mr` | `GBP_USD` | 18 | -7.178 | 11.1% | 3.1% | 0.12 |
| **CRITICAL** | `ema_trend_scalp` | `EUR_USD` | 48 | -0.963 | 18.8% | 10.2% | 0.62 |
| **CRITICAL** | `ema_trend_scalp` | `GBP_USD` | 63 | -0.984 | 19.0% | 11.2% | 0.70 |
| **CRITICAL** | `ema_trend_scalp` | `USD_JPY` | 179 | -2.065 | 19.0% | 13.9% | 0.47 |
| **WARN** | `engulfing_bb` | `EUR_USD` | 25 | -1.440 | 16.0% | 6.4% | 0.44 |
| **WARN** | `engulfing_bb` | `GBP_USD` | 12 | -4.150 | 8.3% | 1.5% | 0.17 |
| **WARN** | `lin_reg_channel` | `EUR_USD` | 21 | -3.071 | 28.6% | 13.8% | 0.39 |
| **WARN** | `london_breakout` | `GBP_USD` | 28 | -3.221 | 7.1% | 2.0% | 0.21 |
| **WARN** | `ma_regime_switch` | `USD_JPY` | 16 | -1.462 | 25.0% | 10.2% | 0.36 |
| **WARN** | `sr_anti_hunt_bounce` | `EUR_USD` | 14 | -0.671 | 7.1% | 1.3% | 0.29 |
| **WARN** | `sr_break_retest` | `EUR_JPY` | 17 | -1.347 | 29.4% | 13.3% | 0.82 |
| **WARN** | `sr_break_retest` | `GBP_JPY` | 22 | -7.586 | 9.1% | 2.5% | 0.33 |
| **CRITICAL** | `sr_break_retest` | `GBP_USD` | 31 | -1.113 | 38.7% | 23.7% | 0.82 |
| **WARN** | `sr_channel_reversal` | `EUR_USD` | 15 | -0.680 | 20.0% | 7.0% | 0.72 |
| **CRITICAL** | `sr_channel_reversal` | `GBP_USD` | 37 | -2.795 | 18.9% | 9.5% | 0.37 |
| **CRITICAL** | `sr_channel_reversal` | `USD_JPY` | 43 | -1.770 | 20.9% | 11.4% | 0.46 |
| **WARN** | `sr_fib_confluence` | `EUR_GBP` | 19 | -0.263 | 21.1% | 8.5% | 0.90 |
| **CRITICAL** | `sr_fib_confluence` | `EUR_JPY` | 34 | -13.776 | 5.9% | 1.6% | 0.19 |
| **WARN** | `sr_fib_confluence` | `EUR_USD` | 26 | -0.577 | 26.9% | 13.7% | 0.85 |
| **CRITICAL** | `sr_fib_confluence` | `GBP_JPY` | 64 | -10.156 | 12.5% | 6.5% | 0.39 |
| **CRITICAL** | `sr_fib_confluence` | `GBP_USD` | 50 | -0.328 | 30.0% | 19.1% | 0.94 |
| **CRITICAL** | `sr_fib_confluence` | `USD_JPY` | 32 | -5.494 | 15.6% | 6.9% | 0.55 |
| **CRITICAL** | `vol_momentum_scalp` | `GBP_USD` | 39 | -0.931 | 20.5% | 10.8% | 0.76 |
| **WARN** | `vol_surge_detector` | `USD_JPY` | 22 | -2.750 | 22.7% | 10.1% | 0.56 |
| **CRITICAL** | `xs_momentum` | `EUR_USD` | 37 | -0.322 | 35.1% | 21.8% | 0.94 |
| **CRITICAL** | `xs_momentum` | `GBP_USD` | 38 | -1.466 | 28.9% | 17.0% | 0.81 |

## R2 Demote Manual Action

For each CRITICAL cell, manually verify and then remove the relevant Render env var:

- `bb_rsi_reversion` x `EUR_USD`: remove `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE`
- `bb_rsi_reversion` x `GBP_USD`: remove `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE`
- `ema_trend_scalp` x `EUR_USD`: remove `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE`
- `ema_trend_scalp` x `GBP_USD`: remove `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE`
- `ema_trend_scalp` x `USD_JPY`: remove `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `GBP_USD`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_channel_reversal` x `GBP_USD`: remove `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_channel_reversal` x `USD_JPY`: remove `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_fib_confluence` x `EUR_JPY`: remove `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE`
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
- Add `('bb_rsi_reversion', 'EUR_USD')`
- Add `('bb_rsi_reversion', 'GBP_USD')`
- Add `('ema_trend_scalp', 'EUR_USD')`
- Add `('ema_trend_scalp', 'GBP_USD')`
- Add `('ema_trend_scalp', 'USD_JPY')`
- Add `('sr_break_retest', 'GBP_USD')`
- Add `('sr_channel_reversal', 'GBP_USD')`
- Add `('sr_channel_reversal', 'USD_JPY')`
- Add `('sr_fib_confluence', 'EUR_JPY')`
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
| CRITICAL | `bb_rsi_reversion` | `EUR_USD` | 33 | 12 | 21 | -0.336 | 36.4% | 22.2%-53.4% | 0.83 | `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `bb_rsi_reversion` | `GBP_USD` | 31 | 6 | 25 | -2.294 | 19.4% | 9.2%-36.3% | 0.33 | `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_rsi_reversion` | `USD_JPY` | 65 | 30 | 35 | +0.200 | 46.2% | 34.6%-58.1% | 1.07 | `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `EUR_USD` | 11 | 1 | 10 | +0.073 | 9.1% | 1.6%-37.7% | 1.03 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `GBP_USD` | 6 | 3 | 3 | +2.067 | 50.0% | 18.8%-81.2% | 2.19 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `USD_JPY` | 1 | 0 | 1 | -3.700 | 0.0% | 0.0%-79.3% | 0.00 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `confluence_scalp` | `EUR_USD` | 1 | 0 | 1 | -3.300 | 0.0% | 0.0%-79.3% | 0.00 | `CONFLUENCE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `cpd_divergence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CPD_DIVERGENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `EUR_USD` | 2 | 0 | 2 | -4.300 | 0.0% | 0.0%-65.8% | 0.00 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_bb_rsi_mr` | `GBP_USD` | 18 | 2 | 16 | -7.178 | 11.1% | 3.1%-32.8% | 0.12 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `USD_JPY` | 14 | 7 | 7 | +5.436 | 50.0% | 26.8%-73.2% | 3.23 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `EUR_JPY` | 5 | 1 | 4 | -8.720 | 20.0% | 3.6%-62.4% | 0.38 | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `GBP_JPY` | 1 | 0 | 1 | -20.000 | 0.0% | 0.0%-79.3% | 0.00 | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `GBP_USD` | 3 | 0 | 3 | -3.833 | 0.0% | 0.0%-56.2% | 0.00 | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `USD_JPY` | 2 | 1 | 1 | +7.800 | 50.0% | 9.5%-90.5% | n/a | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `EUR_JPY` | 17 | 8 | 9 | +7.506 | 47.1% | 26.2%-69.0% | 2.39 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `EUR_USD` | 2 | 1 | 1 | -0.300 | 50.0% | 9.5%-90.5% | 0.79 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `GBP_JPY` | 6 | 3 | 3 | +2.200 | 50.0% | 18.8%-81.2% | 1.29 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `GBP_USD` | 6 | 0 | 6 | -8.450 | 0.0% | 0.0%-39.0% | 0.00 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `USD_JPY` | 7 | 1 | 6 | -6.643 | 14.3% | 2.6%-51.3% | 0.15 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema200_trend_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA200_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`<br>`EMA200_TREND_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `EUR_JPY` | 3 | 1 | 2 | +3.733 | 33.3% | 6.1%-79.2% | 1.51 | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `EUR_USD` | 2 | 1 | 1 | +5.550 | 50.0% | 9.5%-90.5% | 2.66 | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `GBP_JPY` | 3 | 0 | 3 | -20.100 | 0.0% | 0.0%-56.2% | 0.00 | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `GBP_USD` | 1 | 0 | 1 | -11.400 | 0.0% | 0.0%-79.3% | 0.00 | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `USD_JPY` | 1 | 0 | 1 | -10.400 | 0.0% | 0.0%-79.3% | 0.00 | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_pullback` | `USD_JPY` | 3 | 2 | 1 | +15.600 | 66.7% | 20.8%-93.9% | 59.50 | `EMA_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_ribbon_ride` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_RIBBON_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `ema_trend_scalp` | `EUR_USD` | 48 | 9 | 39 | -0.963 | 18.8% | 10.2%-31.9% | 0.62 | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `ema_trend_scalp` | `GBP_USD` | 63 | 12 | 51 | -0.984 | 19.0% | 11.2%-30.4% | 0.70 | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `ema_trend_scalp` | `USD_JPY` | 179 | 34 | 145 | -2.065 | 19.0% | 13.9%-25.4% | 0.47 | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `engulfing_bb` | `EUR_USD` | 25 | 4 | 21 | -1.440 | 16.0% | 6.4%-34.7% | 0.44 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `engulfing_bb` | `GBP_USD` | 12 | 1 | 11 | -4.150 | 8.3% | 1.5%-35.4% | 0.17 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `engulfing_bb` | `USD_JPY` | 23 | 6 | 17 | +0.922 | 26.1% | 12.5%-46.5% | 1.31 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_pips_hunter` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_PIPS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_trend_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_TREND_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_vol_break` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_VOL_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `EUR_JPY` | 2 | 1 | 1 | -5.450 | 50.0% | 9.5%-90.5% | 0.11 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `EUR_USD` | 1 | 1 | 0 | +2.400 | 100.0% | 20.7%-100.0% | n/a | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `USD_JPY` | 1 | 0 | 1 | -12.100 | 0.0% | 0.0%-79.3% | 0.00 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `GBP_USD` | 1 | 1 | 0 | +34.700 | 100.0% | 20.7%-100.0% | n/a | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `USD_JPY` | 1 | 1 | 0 | +24.800 | 100.0% | 20.7%-100.0% | n/a | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `intraday_seasonality` | `GBP_USD` | 4 | 3 | 1 | +11.075 | 75.0% | 30.1%-95.4% | 14.84 | `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `jpy_basket_trend` | `EUR_JPY` | 6 | 1 | 5 | +1.000 | 16.7% | 3.0%-56.4% | 1.33 | `JPY_BASKET_TREND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `keltner_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `lin_reg_channel` | `EUR_USD` | 21 | 6 | 15 | -3.071 | 28.6% | 13.8%-50.0% | 0.39 | `LIN_REG_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_breakout` | `EUR_USD` | 2 | 1 | 1 | +0.400 | 50.0% | 9.5%-90.5% | 1.57 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `london_breakout` | `GBP_USD` | 28 | 2 | 26 | -3.221 | 7.1% | 2.0%-22.6% | 0.21 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_ny_swing` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_NY_SWING_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `GBP_USD` | 4 | 0 | 4 | -7.700 | 0.0% | 0.0%-49.0% | 0.00 | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_shrapnel` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_SHRAPNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_mr_hybrid` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_MR_HYBRID_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `ma_regime_switch` | `USD_JPY` | 16 | 4 | 12 | -1.462 | 25.0% | 10.2%-49.5% | 0.36 | `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_trend_perfect` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_TREND_PERFECT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `EUR_USD` | 2 | 1 | 1 | +1.350 | 50.0% | 9.5%-90.5% | 1.45 | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `USD_JPY` | 9 | 4 | 5 | +1.678 | 44.4% | 18.9%-73.3% | 1.99 | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_regime_range_cascade_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `EUR_USD` | 2 | 0 | 2 | -1.600 | 0.0% | 0.0%-65.8% | 0.00 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `GBP_USD` | 1 | 0 | 1 | -0.200 | 0.0% | 0.0%-79.3% | 0.00 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `EUR_JPY` | 4 | 0 | 4 | -13.250 | 0.0% | 0.0%-49.0% | 0.00 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `GBP_JPY` | 1 | 1 | 0 | +57.000 | 100.0% | 20.7%-100.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `GBP_USD` | 14 | 7 | 7 | +0.407 | 50.0% | 26.8%-73.2% | 1.06 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `USD_JPY` | 23 | 9 | 14 | +4.235 | 39.1% | 22.2%-59.2% | 1.80 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ofi_mr` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `OFI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `EUR_USD` | 7 | 1 | 6 | +0.343 | 14.3% | 2.6%-51.3% | 5.00 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `GBP_USD` | 14 | 9 | 5 | +6.679 | 64.3% | 38.8%-83.7% | 6.40 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `USD_JPY` | 2 | 0 | 2 | -7.100 | 0.0% | 0.0%-65.8% | 0.00 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `post_news_vol` | `EUR_USD` | 3 | 0 | 3 | -16.767 | 0.0% | 0.0%-56.2% | 0.00 | `POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `post_news_vol` | `GBP_USD` | 1 | 0 | 1 | -10.700 | 0.0% | 0.0%-79.3% | 0.00 | `POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `post_news_vol` | `USD_JPY` | 3 | 2 | 1 | +13.233 | 66.7% | 20.8%-93.9% | 18.26 | `POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `EUR_JPY` | 1 | 0 | 1 | -11.900 | 0.0% | 0.0%-79.3% | 0.00 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `EUR_USD` | 1 | 0 | 1 | -7.300 | 0.0% | 0.0%-79.3% | 0.00 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `session_vol_expansion` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SESSION_VOL_EXPANSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `squeeze_release_momentum` | `GBP_USD` | 7 | 1 | 6 | -5.329 | 14.3% | 2.6%-51.3% | 0.07 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `EUR_JPY` | 5 | 1 | 4 | -2.840 | 20.0% | 3.6%-62.4% | 0.43 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_anti_hunt_bounce` | `EUR_USD` | 14 | 1 | 13 | -0.671 | 7.1% | 1.3%-31.5% | 0.29 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_JPY` | 5 | 1 | 4 | +2.140 | 20.0% | 3.6%-62.4% | 1.33 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_USD` | 7 | 6 | 1 | +7.214 | 85.7% | 48.7%-97.4% | 9.86 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `USD_JPY` | 2 | 0 | 2 | -3.350 | 0.0% | 0.0%-65.8% | 0.00 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_break_retest` | `EUR_JPY` | 17 | 5 | 12 | -1.347 | 29.4% | 13.3%-53.1% | 0.82 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_break_retest` | `GBP_JPY` | 22 | 2 | 20 | -7.586 | 9.1% | 2.5%-27.8% | 0.33 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `GBP_USD` | 31 | 12 | 19 | -1.113 | 38.7% | 23.7%-56.2% | 0.82 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_break_retest` | `USD_JPY` | 32 | 12 | 20 | +0.312 | 37.5% | 22.9%-54.7% | 1.07 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_channel_reversal` | `EUR_USD` | 15 | 3 | 12 | -0.680 | 20.0% | 7.0%-45.2% | 0.72 | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_channel_reversal` | `GBP_USD` | 37 | 7 | 30 | -2.795 | 18.9% | 9.5%-34.2% | 0.37 | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_channel_reversal` | `USD_JPY` | 43 | 9 | 34 | -1.770 | 20.9% | 11.4%-35.2% | 0.46 | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_fib_confluence` | `EUR_GBP` | 19 | 4 | 15 | -0.263 | 21.1% | 8.5%-43.3% | 0.90 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_fib_confluence` | `EUR_JPY` | 34 | 2 | 32 | -13.776 | 5.9% | 1.6%-19.1% | 0.19 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_fib_confluence` | `EUR_USD` | 26 | 7 | 19 | -0.577 | 26.9% | 13.7%-46.1% | 0.85 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_fib_confluence` | `GBP_JPY` | 64 | 8 | 56 | -10.156 | 12.5% | 6.5%-22.8% | 0.39 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_fib_confluence` | `GBP_USD` | 50 | 15 | 35 | -0.328 | 30.0% | 19.1%-43.8% | 0.94 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_fib_confluence` | `USD_JPY` | 32 | 5 | 27 | -5.494 | 15.6% | 6.9%-31.8% | 0.55 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_liquidity_grab` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_LIQUIDITY_GRAB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `stoch_trend_pullback` | `EUR_USD` | 4 | 0 | 4 | -3.375 | 0.0% | 0.0%-49.0% | 0.00 | `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `stoch_trend_pullback` | `GBP_USD` | 2 | 0 | 2 | -3.900 | 0.0% | 0.0%-65.8% | 0.00 | `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `stoch_trend_pullback` | `USD_JPY` | 9 | 1 | 8 | -8.156 | 11.1% | 2.0%-43.5% | 0.13 | `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `EUR_USD` | 3 | 0 | 3 | -5.433 | 0.0% | 0.0%-56.2% | 0.00 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `GBP_USD` | 1 | 0 | 1 | -5.300 | 0.0% | 0.0%-79.3% | 0.00 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_range_breakout_up` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_RANGE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `EUR_USD` | 4 | 1 | 3 | -0.775 | 25.0% | 4.6%-69.9% | 0.65 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `GBP_USD` | 1 | 1 | 0 | +12.700 | 100.0% | 20.7%-100.0% | n/a | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `USD_JPY` | 9 | 4 | 5 | +2.222 | 44.4% | 18.9%-73.3% | 2.10 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trendline_sweep` | `EUR_USD` | 5 | 2 | 3 | +6.180 | 40.0% | 11.8%-76.9% | 4.06 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trendline_sweep` | `GBP_USD` | 1 | 1 | 0 | +2.600 | 100.0% | 20.7%-100.0% | n/a | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `turtle_soup` | `GBP_USD` | 9 | 1 | 8 | -3.956 | 11.1% | 2.0%-43.5% | 0.40 | `TURTLE_SOUP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tvsm` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TVSM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `v_reversal` | `USD_JPY` | 1 | 1 | 0 | +5.600 | 100.0% | 20.7%-100.0% | n/a | `V_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vbp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `VBP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `EUR_JPY` | 1 | 0 | 1 | -8.400 | 0.0% | 0.0%-79.3% | 0.00 | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `USD_JPY` | 3 | 2 | 1 | +47.200 | 66.7% | 20.8%-93.9% | 14.36 | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `vol_momentum_scalp` | `GBP_USD` | 39 | 8 | 31 | -0.931 | 20.5% | 10.8%-35.5% | 0.76 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_momentum_scalp` | `USD_JPY` | 9 | 1 | 8 | -2.933 | 11.1% | 2.0%-43.5% | 0.22 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `EUR_USD` | 6 | 2 | 4 | -0.833 | 33.3% | 9.7%-70.0% | 0.75 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `GBP_USD` | 16 | 5 | 11 | +0.844 | 31.2% | 14.2%-55.6% | 1.32 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `USD_JPY` | 22 | 5 | 17 | -2.750 | 22.7% | 10.1%-43.4% | 0.56 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_JPY` | 2 | 0 | 2 | -20.250 | 0.0% | 0.0%-65.8% | 0.00 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_USD` | 1 | 1 | 0 | +1.700 | 100.0% | 20.7%-100.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `USD_JPY` | 1 | 1 | 0 | +22.000 | 100.0% | 20.7%-100.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_GBP` | 5 | 5 | 0 | +13.180 | 100.0% | 56.6%-100.0% | n/a | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_JPY` | 7 | 1 | 6 | -3.014 | 14.3% | 2.6%-51.3% | 0.42 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_USD` | 4 | 0 | 4 | -5.750 | 0.0% | 0.0%-49.0% | 0.00 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `GBP_JPY` | 4 | 0 | 4 | -14.775 | 0.0% | 0.0%-49.0% | 0.00 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `GBP_USD` | 6 | 3 | 3 | +7.300 | 50.0% | 18.8%-81.2% | 5.13 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `USD_JPY` | 9 | 3 | 6 | -0.011 | 33.3% | 12.1%-64.6% | 1.00 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `EUR_USD` | 37 | 13 | 24 | -0.322 | 35.1% | 21.8%-51.2% | 0.94 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `GBP_USD` | 38 | 11 | 27 | -1.466 | 28.9% | 17.0%-44.8% | 0.81 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `xs_momentum` | `USD_JPY` | 16 | 9 | 7 | +4.225 | 56.2% | 33.2%-76.9% | 1.84 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
