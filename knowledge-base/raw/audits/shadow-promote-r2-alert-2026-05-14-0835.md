# SHADOW_PROMOTE R2 Alert - 2026-05-14T08:35:32.804053+00:00

- Source: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=2000`
- Lookback: `30d`
- Filters: `is_shadow=1`, `pnl_pips IS NOT NULL`, XAU instruments excluded
- Gate: `N >= 10 and EV < 0` -> WARN; `N >= 30 and EV < 0` -> CRITICAL
- Mode: read-only; no env vars, strategy code, tier-master, or DB writes

## Summary

- Promoted strategies: 66
- Cells: 132
- OK: 96
- WARN: 20
- CRITICAL: 16

## WARN / CRITICAL

| Severity | Strategy | Instrument | N | EV | WR | Wilson lower | PF |
|---|---|---|---:|---:|---:|---:|---:|
| **CRITICAL** | `bb_rsi_reversion` | `EUR_USD` | 37 | -0.016 | 40.5% | 26.3% | 0.99 |
| **CRITICAL** | `bb_rsi_reversion` | `GBP_USD` | 32 | -2.409 | 18.8% | 8.9% | 0.31 |
| **WARN** | `bb_squeeze_breakout` | `EUR_USD` | 12 | -0.192 | 8.3% | 1.5% | 0.93 |
| **WARN** | `dt_bb_rsi_mr` | `GBP_USD` | 14 | -5.871 | 14.3% | 4.0% | 0.17 |
| **CRITICAL** | `ema_trend_scalp` | `EUR_USD` | 64 | -0.553 | 21.9% | 13.5% | 0.77 |
| **CRITICAL** | `ema_trend_scalp` | `GBP_USD` | 69 | -0.893 | 20.3% | 12.5% | 0.73 |
| **CRITICAL** | `ema_trend_scalp` | `USD_JPY` | 192 | -1.933 | 19.3% | 14.3% | 0.51 |
| **WARN** | `engulfing_bb` | `EUR_USD` | 25 | -1.312 | 20.0% | 8.9% | 0.53 |
| **WARN** | `engulfing_bb` | `GBP_USD` | 13 | -4.400 | 7.7% | 1.4% | 0.15 |
| **CRITICAL** | `engulfing_bb` | `USD_JPY` | 30 | -2.067 | 20.0% | 9.5% | 0.59 |
| **WARN** | `lin_reg_channel` | `EUR_USD` | 21 | -3.071 | 28.6% | 13.8% | 0.39 |
| **WARN** | `london_breakout` | `GBP_USD` | 23 | -2.887 | 8.7% | 2.4% | 0.27 |
| **WARN** | `ma_regime_switch` | `USD_JPY` | 12 | -1.383 | 25.0% | 8.9% | 0.44 |
| **WARN** | `ob_retest` | `USD_JPY` | 14 | -8.643 | 0.0% | 0.0% | 0.00 |
| **WARN** | `sr_anti_hunt_bounce` | `EUR_USD` | 13 | -1.015 | 0.0% | 0.0% | 0.00 |
| **WARN** | `sr_break_retest` | `EUR_JPY` | 13 | -0.515 | 30.8% | 12.7% | 0.93 |
| **WARN** | `sr_break_retest` | `GBP_JPY` | 19 | -7.479 | 10.5% | 2.9% | 0.37 |
| **WARN** | `sr_break_retest` | `GBP_USD` | 26 | -3.492 | 34.6% | 19.4% | 0.53 |
| **WARN** | `sr_break_retest` | `USD_JPY` | 27 | -2.396 | 29.6% | 15.9% | 0.54 |
| **WARN** | `sr_channel_reversal` | `EUR_USD` | 25 | -2.536 | 12.0% | 4.2% | 0.29 |
| **CRITICAL** | `sr_channel_reversal` | `GBP_USD` | 40 | -2.620 | 20.0% | 10.5% | 0.41 |
| **CRITICAL** | `sr_channel_reversal` | `USD_JPY` | 45 | -2.076 | 20.0% | 10.9% | 0.41 |
| **WARN** | `sr_fib_confluence` | `EUR_GBP` | 19 | -0.263 | 21.1% | 8.5% | 0.90 |
| **CRITICAL** | `sr_fib_confluence` | `EUR_JPY` | 35 | -13.954 | 5.7% | 1.6% | 0.19 |
| **CRITICAL** | `sr_fib_confluence` | `EUR_USD` | 30 | -0.790 | 26.7% | 14.2% | 0.79 |
| **CRITICAL** | `sr_fib_confluence` | `GBP_JPY` | 64 | -10.156 | 12.5% | 6.5% | 0.39 |
| **CRITICAL** | `sr_fib_confluence` | `GBP_USD` | 44 | -1.675 | 25.0% | 14.6% | 0.73 |
| **CRITICAL** | `sr_fib_confluence` | `USD_JPY` | 32 | -5.494 | 15.6% | 6.9% | 0.55 |
| **WARN** | `stoch_trend_pullback` | `USD_JPY` | 13 | -5.423 | 15.4% | 4.3% | 0.32 |
| **CRITICAL** | `vol_momentum_scalp` | `GBP_USD` | 35 | -2.151 | 14.3% | 6.3% | 0.49 |
| **WARN** | `vol_surge_detector` | `GBP_USD` | 13 | -1.869 | 15.4% | 4.3% | 0.43 |
| **WARN** | `vol_surge_detector` | `USD_JPY` | 22 | -2.750 | 22.7% | 10.1% | 0.56 |
| **WARN** | `wick_imbalance_reversion` | `EUR_JPY` | 11 | -9.727 | 9.1% | 1.6% | 0.13 |
| **CRITICAL** | `xs_momentum` | `EUR_USD` | 30 | -2.440 | 23.3% | 11.8% | 0.62 |
| **CRITICAL** | `xs_momentum` | `GBP_USD` | 38 | -0.566 | 28.9% | 17.0% | 0.92 |
| **WARN** | `xs_momentum` | `USD_JPY` | 12 | -4.550 | 33.3% | 13.8% | 0.46 |

## R2 Demote Manual Action

For each CRITICAL cell, manually verify and then remove the relevant Render env var:

- `bb_rsi_reversion` x `EUR_USD`: remove `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE`
- `bb_rsi_reversion` x `GBP_USD`: remove `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE`
- `ema_trend_scalp` x `EUR_USD`: remove `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE`
- `ema_trend_scalp` x `GBP_USD`: remove `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE`
- `ema_trend_scalp` x `USD_JPY`: remove `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE`
- `engulfing_bb` x `USD_JPY`: remove `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE`
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
- Missing CRITICAL cells: `16`
- Add `('bb_rsi_reversion', 'EUR_USD')`
- Add `('bb_rsi_reversion', 'GBP_USD')`
- Add `('ema_trend_scalp', 'EUR_USD')`
- Add `('ema_trend_scalp', 'GBP_USD')`
- Add `('ema_trend_scalp', 'USD_JPY')`
- Add `('engulfing_bb', 'USD_JPY')`
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
| OK | `bb_rsi_ema_aligned` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `BB_RSI_EMA_ALIGNED_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `bb_rsi_reversion` | `EUR_USD` | 37 | 15 | 22 | -0.016 | 40.5% | 26.3%-56.5% | 0.99 | `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `bb_rsi_reversion` | `GBP_USD` | 32 | 6 | 26 | -2.409 | 18.8% | 8.9%-35.3% | 0.31 | `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_rsi_reversion` | `USD_JPY` | 69 | 31 | 38 | +0.099 | 44.9% | 33.8%-56.6% | 1.03 | `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `bb_squeeze_breakout` | `EUR_USD` | 12 | 1 | 11 | -0.192 | 8.3% | 1.5%-35.4% | 0.93 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `GBP_USD` | 6 | 3 | 3 | +2.067 | 50.0% | 18.8%-81.2% | 2.19 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `USD_JPY` | 1 | 0 | 1 | -3.700 | 0.0% | 0.0%-79.3% | 0.00 | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `confluence_scalp` | `EUR_USD` | 1 | 0 | 1 | -3.300 | 0.0% | 0.0%-79.3% | 0.00 | `CONFLUENCE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `cpd_divergence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CPD_DIVERGENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `EUR_USD` | 2 | 0 | 2 | -4.300 | 0.0% | 0.0%-65.8% | 0.00 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_bb_rsi_mr` | `GBP_USD` | 14 | 2 | 12 | -5.871 | 14.3% | 4.0%-39.9% | 0.17 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `USD_JPY` | 14 | 7 | 7 | +5.436 | 50.0% | 26.8%-73.2% | 3.23 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `EUR_JPY` | 5 | 1 | 4 | -8.720 | 20.0% | 3.6%-62.4% | 0.38 | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `GBP_JPY` | 1 | 0 | 1 | -20.000 | 0.0% | 0.0%-79.3% | 0.00 | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `GBP_USD` | 3 | 0 | 3 | -3.833 | 0.0% | 0.0%-56.2% | 0.00 | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `USD_JPY` | 2 | 1 | 1 | +7.800 | 50.0% | 9.5%-90.5% | n/a | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `EUR_JPY` | 15 | 7 | 8 | +6.773 | 46.7% | 24.8%-69.9% | 1.93 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `EUR_USD` | 2 | 1 | 1 | -0.300 | 50.0% | 9.5%-90.5% | 0.79 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `GBP_JPY` | 7 | 3 | 4 | -0.986 | 42.9% | 15.8%-75.0% | 0.90 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
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
| CRITICAL | `ema_trend_scalp` | `EUR_USD` | 64 | 14 | 50 | -0.553 | 21.9% | 13.5%-33.4% | 0.77 | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `ema_trend_scalp` | `GBP_USD` | 69 | 14 | 55 | -0.893 | 20.3% | 12.5%-31.2% | 0.73 | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `ema_trend_scalp` | `USD_JPY` | 192 | 37 | 155 | -1.933 | 19.3% | 14.3%-25.4% | 0.51 | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `engulfing_bb` | `EUR_USD` | 25 | 5 | 20 | -1.312 | 20.0% | 8.9%-39.1% | 0.53 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `engulfing_bb` | `GBP_USD` | 13 | 1 | 12 | -4.400 | 7.7% | 1.4%-33.3% | 0.15 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `engulfing_bb` | `USD_JPY` | 30 | 6 | 24 | -2.067 | 20.0% | 9.5%-37.3% | 0.59 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_pips_hunter` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_PIPS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_trend_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_TREND_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_vol_break` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_VOL_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `EUR_JPY` | 7 | 1 | 6 | -16.300 | 14.3% | 2.6%-51.3% | 0.01 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `EUR_USD` | 1 | 1 | 0 | +2.400 | 100.0% | 20.7%-100.0% | n/a | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_JPY` | 1 | 0 | 1 | -23.500 | 0.0% | 0.0%-79.3% | 0.00 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `USD_JPY` | 1 | 0 | 1 | -12.100 | 0.0% | 0.0%-79.3% | 0.00 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `GBP_USD` | 1 | 1 | 0 | +34.700 | 100.0% | 20.7%-100.0% | n/a | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `intraday_seasonality` | `GBP_USD` | 4 | 3 | 1 | +11.075 | 75.0% | 30.1%-95.4% | 14.84 | `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `jpy_basket_trend` | `EUR_JPY` | 6 | 1 | 5 | +1.000 | 16.7% | 3.0%-56.4% | 1.33 | `JPY_BASKET_TREND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `keltner_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `lin_reg_channel` | `EUR_USD` | 21 | 6 | 15 | -3.071 | 28.6% | 13.8%-50.0% | 0.39 | `LIN_REG_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_breakout` | `EUR_USD` | 2 | 1 | 1 | +0.400 | 50.0% | 9.5%-90.5% | 1.57 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `london_breakout` | `GBP_USD` | 23 | 2 | 21 | -2.887 | 8.7% | 2.4%-26.8% | 0.27 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_ny_swing` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_NY_SWING_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `GBP_USD` | 4 | 0 | 4 | -7.700 | 0.0% | 0.0%-49.0% | 0.00 | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_shrapnel` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_SHRAPNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_mr_hybrid` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_MR_HYBRID_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `ma_regime_switch` | `USD_JPY` | 12 | 3 | 9 | -1.383 | 25.0% | 8.9%-53.2% | 0.44 | `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_trend_perfect` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_TREND_PERFECT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `EUR_USD` | 3 | 1 | 2 | -1.233 | 33.3% | 6.1%-79.2% | 0.70 | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `USD_JPY` | 10 | 4 | 6 | +0.690 | 40.0% | 16.8%-68.7% | 1.29 | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_regime_range_cascade_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `EUR_USD` | 2 | 0 | 2 | -1.600 | 0.0% | 0.0%-65.8% | 0.00 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `GBP_USD` | 1 | 0 | 1 | -0.200 | 0.0% | 0.0%-79.3% | 0.00 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `GBP_JPY` | 1 | 1 | 0 | +57.000 | 100.0% | 20.7%-100.0% | n/a | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `GBP_USD` | 8 | 5 | 3 | +1.912 | 62.5% | 30.6%-86.3% | 1.35 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `ob_retest` | `USD_JPY` | 14 | 0 | 14 | -8.643 | 0.0% | 0.0%-21.5% | 0.00 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ofi_mr` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `OFI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `EUR_USD` | 7 | 1 | 6 | +0.343 | 14.3% | 2.6%-51.3% | 5.00 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `GBP_USD` | 11 | 6 | 5 | +4.227 | 54.5% | 28.0%-78.7% | 3.69 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `USD_JPY` | 2 | 0 | 2 | -7.100 | 0.0% | 0.0%-65.8% | 0.00 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `post_news_vol` | `EUR_USD` | 6 | 0 | 6 | -14.817 | 0.0% | 0.0%-39.0% | 0.00 | `POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `post_news_vol` | `GBP_USD` | 2 | 0 | 2 | -14.250 | 0.0% | 0.0%-65.8% | 0.00 | `POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `post_news_vol` | `USD_JPY` | 6 | 5 | 1 | +76.300 | 83.3% | 43.6%-97.0% | 200.04 | `POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `EUR_JPY` | 1 | 0 | 1 | -11.900 | 0.0% | 0.0%-79.3% | 0.00 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `EUR_USD` | 1 | 0 | 1 | -7.300 | 0.0% | 0.0%-79.3% | 0.00 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `session_vol_expansion` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SESSION_VOL_EXPANSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `squeeze_release_momentum` | `GBP_USD` | 7 | 1 | 6 | -5.329 | 14.3% | 2.6%-51.3% | 0.07 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `EUR_JPY` | 5 | 1 | 4 | -2.840 | 20.0% | 3.6%-62.4% | 0.43 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_anti_hunt_bounce` | `EUR_USD` | 13 | 0 | 13 | -1.015 | 0.0% | 0.0%-22.8% | 0.00 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_JPY` | 5 | 1 | 4 | +2.140 | 20.0% | 3.6%-62.4% | 1.33 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_USD` | 5 | 4 | 1 | +5.740 | 80.0% | 37.6%-96.4% | 6.04 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `USD_JPY` | 2 | 0 | 2 | -3.350 | 0.0% | 0.0%-65.8% | 0.00 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_break_retest` | `EUR_JPY` | 13 | 4 | 9 | -0.515 | 30.8% | 12.7%-57.6% | 0.93 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_break_retest` | `GBP_JPY` | 19 | 2 | 17 | -7.479 | 10.5% | 2.9%-31.4% | 0.37 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_break_retest` | `GBP_USD` | 26 | 9 | 17 | -3.492 | 34.6% | 19.4%-53.8% | 0.53 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_break_retest` | `USD_JPY` | 27 | 8 | 19 | -2.396 | 29.6% | 15.9%-48.5% | 0.54 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_channel_reversal` | `EUR_USD` | 25 | 3 | 22 | -2.536 | 12.0% | 4.2%-30.0% | 0.29 | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_channel_reversal` | `GBP_USD` | 40 | 8 | 32 | -2.620 | 20.0% | 10.5%-34.8% | 0.41 | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_channel_reversal` | `USD_JPY` | 45 | 9 | 36 | -2.076 | 20.0% | 10.9%-33.8% | 0.41 | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_fib_confluence` | `EUR_GBP` | 19 | 4 | 15 | -0.263 | 21.1% | 8.5%-43.3% | 0.90 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_fib_confluence` | `EUR_JPY` | 35 | 2 | 33 | -13.954 | 5.7% | 1.6%-18.6% | 0.19 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_fib_confluence` | `EUR_USD` | 30 | 8 | 22 | -0.790 | 26.7% | 14.2%-44.4% | 0.79 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_fib_confluence` | `GBP_JPY` | 64 | 8 | 56 | -10.156 | 12.5% | 6.5%-22.8% | 0.39 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_fib_confluence` | `GBP_USD` | 44 | 11 | 33 | -1.675 | 25.0% | 14.6%-39.4% | 0.73 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_fib_confluence` | `USD_JPY` | 32 | 5 | 27 | -5.494 | 15.6% | 6.9%-31.8% | 0.55 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_liquidity_grab` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_LIQUIDITY_GRAB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `stoch_trend_pullback` | `EUR_USD` | 9 | 1 | 8 | -1.644 | 11.1% | 2.0%-43.5% | 0.36 | `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `stoch_trend_pullback` | `GBP_USD` | 2 | 0 | 2 | -3.900 | 0.0% | 0.0%-65.8% | 0.00 | `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `stoch_trend_pullback` | `USD_JPY` | 13 | 2 | 11 | -5.423 | 15.4% | 4.3%-42.2% | 0.32 | `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `EUR_USD` | 3 | 0 | 3 | -5.433 | 0.0% | 0.0%-56.2% | 0.00 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `GBP_USD` | 1 | 0 | 1 | -5.300 | 0.0% | 0.0%-79.3% | 0.00 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `USD_JPY` | 1 | 0 | 1 | -0.300 | 0.0% | 0.0%-79.3% | 0.00 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_range_breakout_up` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_RANGE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `EUR_USD` | 4 | 1 | 3 | -0.775 | 25.0% | 4.6%-69.9% | 0.65 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `GBP_USD` | 2 | 2 | 0 | +14.500 | 100.0% | 34.2%-100.0% | n/a | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `USD_JPY` | 10 | 4 | 6 | +0.780 | 40.0% | 16.8%-68.7% | 1.26 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trendline_sweep` | `EUR_USD` | 3 | 1 | 2 | +3.500 | 33.3% | 6.1%-79.2% | 2.06 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `turtle_soup` | `GBP_USD` | 7 | 1 | 6 | -4.471 | 14.3% | 2.6%-51.3% | 0.43 | `TURTLE_SOUP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tvsm` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TVSM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `v_reversal` | `USD_JPY` | 1 | 1 | 0 | +5.600 | 100.0% | 20.7%-100.0% | n/a | `V_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vbp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `VBP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `EUR_JPY` | 1 | 0 | 1 | -8.400 | 0.0% | 0.0%-79.3% | 0.00 | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `USD_JPY` | 2 | 2 | 0 | +76.100 | 100.0% | 34.2%-100.0% | n/a | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `vol_momentum_scalp` | `GBP_USD` | 35 | 5 | 30 | -2.151 | 14.3% | 6.3%-29.4% | 0.49 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_momentum_scalp` | `USD_JPY` | 9 | 1 | 8 | -3.844 | 11.1% | 2.0%-43.5% | 0.18 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `EUR_USD` | 7 | 2 | 5 | -1.286 | 28.6% | 8.2%-64.1% | 0.62 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `GBP_USD` | 13 | 2 | 11 | -1.869 | 15.4% | 4.3%-42.2% | 0.43 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `USD_JPY` | 22 | 5 | 17 | -2.750 | 22.7% | 10.1%-43.4% | 0.56 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_JPY` | 2 | 0 | 2 | -20.250 | 0.0% | 0.0%-65.8% | 0.00 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `USD_JPY` | 1 | 1 | 0 | +22.000 | 100.0% | 20.7%-100.0% | n/a | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `EUR_JPY` | 11 | 1 | 10 | -9.727 | 9.1% | 1.6%-37.7% | 0.13 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_USD` | 4 | 0 | 4 | -5.750 | 0.0% | 0.0%-49.0% | 0.00 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `GBP_JPY` | 1 | 0 | 1 | -3.800 | 0.0% | 0.0%-79.3% | 0.00 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `GBP_USD` | 3 | 0 | 3 | -3.533 | 0.0% | 0.0%-56.2% | 0.00 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `USD_JPY` | 9 | 3 | 6 | -0.011 | 33.3% | 12.1%-64.6% | 1.00 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `EUR_USD` | 30 | 7 | 23 | -2.440 | 23.3% | 11.8%-40.9% | 0.62 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `GBP_USD` | 38 | 11 | 27 | -0.566 | 28.9% | 17.0%-44.8% | 0.92 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `xs_momentum` | `USD_JPY` | 12 | 4 | 8 | -4.550 | 33.3% | 13.8%-60.9% | 0.46 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
