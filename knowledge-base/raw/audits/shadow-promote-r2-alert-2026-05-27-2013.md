# SHADOW_PROMOTE R2 Alert - 2026-05-27T20:13:30.824978+00:00

- Source: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=2000`
- Lookback: `30d`
- Filters: `is_shadow=1`, `pnl_pips IS NOT NULL`, XAU instruments excluded
- Gate: `N >= 10 and EV < 0` -> WARN; `N >= 30 and EV < 0` -> CRITICAL
- Mode: read-only; no env vars, strategy code, tier-master, or DB writes

## Summary

- Promoted strategies: 66
- Cells: 137
- OK: 102
- WARN: 17
- CRITICAL: 18

## WARN / CRITICAL

| Severity | Strategy | Instrument | N | EV | WR | Wilson lower | PF |
|---|---|---|---:|---:|---:|---:|---:|
| **WARN** | `bb_rsi_reversion` | `USD_CHF` | 29 | -2.534 | 0.0% | 0.0% | 0.00 |
| **WARN** | `dt_sr_channel_reversal` | `GBP_USD` | 10 | -9.200 | 0.0% | 0.0% | 0.00 |
| **CRITICAL** | `ema_trend_scalp` | `USD_CHF` | 38 | -2.303 | 0.0% | 0.0% | 0.00 |
| **CRITICAL** | `engulfing_bb` | `EUR_USD` | 36 | -0.403 | 27.8% | 15.8% | 0.82 |
| **WARN** | `engulfing_bb` | `GBP_USD` | 16 | -3.775 | 12.5% | 3.5% | 0.24 |
| **WARN** | `engulfing_bb` | `USD_CHF` | 10 | -1.430 | 0.0% | 0.0% | 0.00 |
| **WARN** | `lin_reg_channel` | `EUR_USD` | 15 | -0.747 | 33.3% | 15.2% | 0.72 |
| **WARN** | `london_breakout` | `EUR_USD` | 26 | -2.538 | 7.7% | 2.1% | 0.16 |
| **CRITICAL** | `london_breakout` | `GBP_USD` | 30 | -3.713 | 6.7% | 1.8% | 0.13 |
| **WARN** | `london_breakout` | `USD_CHF` | 12 | -2.458 | 0.0% | 0.0% | 0.00 |
| **CRITICAL** | `ma_regime_switch` | `USD_JPY` | 30 | -1.493 | 23.3% | 11.8% | 0.40 |
| **WARN** | `ob_retest` | `GBP_USD` | 18 | -0.772 | 50.0% | 29.0% | 0.88 |
| **WARN** | `orb_trap` | `EUR_USD` | 18 | -3.161 | 5.6% | 1.0% | 0.05 |
| **CRITICAL** | `sr_anti_hunt_bounce` | `EUR_USD` | 30 | -10.887 | 3.3% | 0.6% | 0.01 |
| **WARN** | `sr_anti_hunt_bounce` | `GBP_JPY` | 11 | -2.036 | 18.2% | 5.1% | 0.49 |
| **CRITICAL** | `sr_anti_hunt_bounce` | `USD_JPY` | 38 | -1.668 | 0.0% | 0.0% | 0.00 |
| **CRITICAL** | `sr_break_retest` | `EUR_JPY` | 33 | -2.918 | 24.2% | 12.8% | 0.59 |
| **CRITICAL** | `sr_break_retest` | `GBP_JPY` | 33 | -7.945 | 6.1% | 1.7% | 0.19 |
| **CRITICAL** | `sr_break_retest` | `GBP_USD` | 63 | -3.803 | 22.2% | 13.7% | 0.38 |
| **CRITICAL** | `sr_break_retest` | `USD_JPY` | 62 | -1.526 | 24.2% | 15.2% | 0.66 |
| **CRITICAL** | `sr_channel_reversal` | `GBP_USD` | 48 | -1.640 | 25.0% | 14.9% | 0.56 |
| **WARN** | `sr_channel_reversal` | `USD_CHF` | 16 | -1.312 | 0.0% | 0.0% | 0.00 |
| **WARN** | `sr_fib_confluence` | `EUR_GBP` | 26 | -0.815 | 23.1% | 11.0% | 0.71 |
| **CRITICAL** | `sr_fib_confluence` | `EUR_USD` | 52 | -1.827 | 23.1% | 13.7% | 0.58 |
| **CRITICAL** | `sr_fib_confluence` | `GBP_USD` | 72 | -3.154 | 20.8% | 13.1% | 0.52 |
| **WARN** | `trendline_sweep` | `GBP_USD` | 20 | -18.360 | 5.0% | 0.9% | 0.01 |
| **WARN** | `turtle_soup` | `GBP_USD` | 13 | -2.292 | 30.8% | 12.7% | 0.51 |
| **CRITICAL** | `vol_momentum_scalp` | `GBP_USD` | 41 | -1.788 | 19.5% | 10.2% | 0.57 |
| **WARN** | `vol_momentum_scalp` | `USD_JPY` | 10 | -2.940 | 0.0% | 0.0% | 0.00 |
| **WARN** | `vol_surge_detector` | `USD_JPY` | 10 | -1.880 | 20.0% | 5.7% | 0.41 |
| **WARN** | `wick_imbalance_reversion` | `EUR_JPY` | 19 | -3.279 | 21.1% | 8.5% | 0.52 |
| **CRITICAL** | `wick_imbalance_reversion` | `EUR_USD` | 31 | -1.042 | 25.8% | 13.7% | 0.66 |
| **CRITICAL** | `xs_momentum` | `EUR_USD` | 56 | -4.963 | 21.4% | 12.7% | 0.34 |
| **CRITICAL** | `xs_momentum` | `GBP_USD` | 44 | -1.298 | 29.5% | 18.2% | 0.80 |
| **CRITICAL** | `xs_momentum` | `USD_JPY` | 39 | -1.038 | 30.8% | 18.6% | 0.81 |

## R2 Demote Manual Action

For each CRITICAL cell, manually verify and then remove the relevant Render env var:

- `ema_trend_scalp` x `USD_CHF`: remove `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE`
- `engulfing_bb` x `EUR_USD`: remove `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE`
- `london_breakout` x `GBP_USD`: remove `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE`
- `ma_regime_switch` x `USD_JPY`: remove `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_anti_hunt_bounce` x `EUR_USD`: remove `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_anti_hunt_bounce` x `USD_JPY`: remove `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `EUR_JPY`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `GBP_JPY`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `GBP_USD`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_break_retest` x `USD_JPY`: remove `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_channel_reversal` x `GBP_USD`: remove `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_fib_confluence` x `EUR_USD`: remove `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE`
- `sr_fib_confluence` x `GBP_USD`: remove `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE`
- `vol_momentum_scalp` x `GBP_USD`: remove `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`, `VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE`
- `wick_imbalance_reversion` x `EUR_USD`: remove `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`, `WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE`
- `xs_momentum` x `EUR_USD`: remove `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`
- `xs_momentum` x `GBP_USD`: remove `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`
- `xs_momentum` x `USD_JPY`: remove `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`

Code review locations if manual demotion is chosen:
- `strategies/daytrade/__init__.py` `split_shadow_always` / `SHADOW_ALWAYS_STRATEGIES`
- `strategies/hourly/__init__.py` `split_shadow_always`
- `strategies/scalp/__init__.py` `split_shadow_always`

## Apply Demote Suggestion

- Registry: `/home/runner/work/fx-ai-trader/fx-ai-trader/modules/shadow_demote_registry.py`
- Missing CRITICAL cells: `18`
- Add `('ema_trend_scalp', 'USD_CHF')`
- Add `('engulfing_bb', 'EUR_USD')`
- Add `('london_breakout', 'GBP_USD')`
- Add `('ma_regime_switch', 'USD_JPY')`
- Add `('sr_anti_hunt_bounce', 'EUR_USD')`
- Add `('sr_anti_hunt_bounce', 'USD_JPY')`
- Add `('sr_break_retest', 'EUR_JPY')`
- Add `('sr_break_retest', 'GBP_JPY')`
- Add `('sr_break_retest', 'GBP_USD')`
- Add `('sr_break_retest', 'USD_JPY')`
- Add `('sr_channel_reversal', 'GBP_USD')`
- Add `('sr_fib_confluence', 'EUR_USD')`
- Add `('sr_fib_confluence', 'GBP_USD')`
- Add `('vol_momentum_scalp', 'GBP_USD')`
- Add `('wick_imbalance_reversion', 'EUR_USD')`
- Add `('xs_momentum', 'EUR_USD')`
- Add `('xs_momentum', 'GBP_USD')`
- Add `('xs_momentum', 'USD_JPY')`

## All Cells

| Severity | Strategy | Instrument | N | Wins | Losses | EV | WR | Wilson 95% | PF | Env |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| OK | `adx_trend_continuation` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ADX_TREND_CONTINUATION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `asia_range_fade_v1` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ASIA_RANGE_FADE_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `atr_regime_break` | `EUR_JPY` | 1 | 0 | 1 | -15.100 | 0.0% | 0.0%-79.3% | 0.00 | `ALPHA_ATR_REGIME_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `atr_regime_break` | `GBP_JPY` | 1 | 1 | 0 | +5.500 | 100.0% | 20.7%-100.0% | n/a | `ALPHA_ATR_REGIME_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `atr_regime_break` | `USD_JPY` | 2 | 1 | 1 | +2.850 | 50.0% | 9.5%-90.5% | 1.43 | `ALPHA_ATR_REGIME_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_rsi_ema_aligned` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `BB_RSI_EMA_ALIGNED_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_rsi_reversion` | `EUR_USD` | 6 | 2 | 4 | -1.000 | 33.3% | 9.7%-70.0% | 0.55 | `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_rsi_reversion` | `GBP_USD` | 7 | 3 | 4 | -0.714 | 42.9% | 15.8%-75.0% | 0.78 | `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `bb_rsi_reversion` | `USD_CHF` | 29 | 0 | 29 | -2.534 | 0.0% | 0.0%-11.7% | 0.00 | `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_rsi_reversion` | `USD_JPY` | 6 | 5 | 1 | +3.483 | 83.3% | 43.6%-97.0% | 7.53 | `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `bb_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `confluence_scalp` | `EUR_USD` | 1 | 0 | 1 | -3.300 | 0.0% | 0.0%-79.3% | 0.00 | `CONFLUENCE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `cpd_divergence` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `CPD_DIVERGENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `AUD_JPY` | 8 | 0 | 8 | -17.087 | 0.0% | 0.0%-32.4% | 0.00 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `AUD_USD` | 3 | 0 | 3 | -7.800 | 0.0% | 0.0%-56.2% | 0.00 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `EUR_AUD` | 9 | 4 | 5 | +6.767 | 44.4% | 18.9%-73.3% | 1.42 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `EUR_USD` | 2 | 0 | 2 | -12.900 | 0.0% | 0.0%-65.8% | 0.00 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `NZD_JPY` | 7 | 4 | 3 | +11.843 | 57.1% | 25.0%-84.2% | 2.31 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `NZD_USD` | 4 | 2 | 2 | +4.425 | 50.0% | 15.0%-85.0% | 1.53 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `USD_CAD` | 9 | 3 | 6 | -9.689 | 33.3% | 12.1%-64.6% | 0.25 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `donchian_momentum_breakout` | `USD_JPY` | 1 | 0 | 1 | -0.800 | 0.0% | 0.0%-79.3% | 0.00 | `DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `EUR_USD` | 32 | 18 | 14 | +3.109 | 56.2% | 39.3%-71.8% | 2.37 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `GBP_USD` | 39 | 18 | 21 | +0.877 | 46.2% | 31.6%-61.4% | 1.23 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_bb_rsi_mr` | `USD_JPY` | 6 | 1 | 5 | +1.100 | 16.7% | 3.0%-56.4% | 1.73 | `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_fib_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `FIB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `EUR_JPY` | 8 | 1 | 7 | -7.300 | 12.5% | 2.2%-47.1% | 0.13 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `EUR_USD` | 1 | 1 | 0 | +2.200 | 100.0% | 20.7%-100.0% | n/a | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `GBP_JPY` | 2 | 0 | 2 | -13.200 | 0.0% | 0.0%-65.8% | 0.00 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `dt_sr_channel_reversal` | `GBP_USD` | 10 | 0 | 10 | -9.200 | 0.0% | 0.0%-27.8% | 0.00 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `dt_sr_channel_reversal` | `USD_JPY` | 8 | 4 | 4 | +2.163 | 50.0% | 21.5%-78.5% | 1.53 | `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema200_trend_reversal` | `USD_JPY` | 3 | 0 | 3 | -3.733 | 0.0% | 0.0%-56.2% | 0.00 | `EMA200_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE`<br>`EMA200_TREND_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_cross` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_ribbon_ride` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `EMA_RIBBON_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_trend_scalp` | `EUR_USD` | 6 | 0 | 6 | -2.517 | 0.0% | 0.0%-39.0% | 0.00 | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_trend_scalp` | `GBP_USD` | 2 | 0 | 2 | -1.300 | 0.0% | 0.0%-65.8% | 0.00 | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `ema_trend_scalp` | `USD_CHF` | 38 | 0 | 38 | -2.303 | 0.0% | 0.0%-9.2% | 0.00 | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ema_trend_scalp` | `USD_JPY` | 16 | 6 | 10 | +1.225 | 37.5% | 18.5%-61.4% | 1.55 | `EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `engulfing_bb` | `EUR_USD` | 36 | 10 | 26 | -0.403 | 27.8% | 15.8%-44.0% | 0.82 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `engulfing_bb` | `GBP_USD` | 16 | 2 | 14 | -3.775 | 12.5% | 3.5%-36.0% | 0.24 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `engulfing_bb` | `USD_CHF` | 10 | 0 | 10 | -1.430 | 0.0% | 0.0%-27.8% | 0.00 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `engulfing_bb` | `USD_JPY` | 6 | 0 | 6 | -3.967 | 0.0% | 0.0%-39.0% | 0.00 | `ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_pips_hunter` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_PIPS_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_trend_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_TREND_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `gold_vol_break` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `GOLD_VOL_BREAK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `EUR_USD` | 1 | 1 | 0 | +2.400 | 100.0% | 20.7%-100.0% | n/a | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `GBP_USD` | 3 | 0 | 3 | -8.800 | 0.0% | 0.0%-56.2% | 0.00 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `htf_false_breakout` | `USD_JPY` | 1 | 0 | 1 | -12.100 | 0.0% | 0.0%-79.3% | 0.00 | `HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `GBP_USD` | 7 | 3 | 4 | +13.614 | 42.9% | 15.8%-75.0% | 5.58 | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `inducement_ob` | `USD_JPY` | 1 | 1 | 0 | +24.800 | 100.0% | 20.7%-100.0% | n/a | `INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `intraday_seasonality` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `jpy_basket_trend` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `JPY_BASKET_TREND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `keltner_squeeze_breakout` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `lin_reg_channel` | `EUR_USD` | 15 | 5 | 10 | -0.747 | 33.3% | 15.2%-58.3% | 0.72 | `LIN_REG_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `london_breakout` | `EUR_USD` | 26 | 2 | 24 | -2.538 | 7.7% | 2.1%-24.1% | 0.16 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `london_breakout` | `GBP_USD` | 30 | 2 | 28 | -3.713 | 6.7% | 1.8%-21.3% | 0.13 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `london_breakout` | `USD_CHF` | 12 | 0 | 12 | -2.458 | 0.0% | 0.0%-24.3% | 0.00 | `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_ny_swing` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_NY_SWING_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_session_breakout` | `GBP_USD` | 2 | 0 | 2 | -5.050 | 0.0% | 0.0%-65.8% | 0.00 | `LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `london_shrapnel` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `LONDON_SHRAPNEL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_mr_hybrid` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_MR_HYBRID_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `ma_regime_switch` | `USD_JPY` | 30 | 7 | 23 | -1.493 | 23.3% | 11.8%-40.9% | 0.40 | `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ma_trend_perfect` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MA_TREND_PERFECT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `macdh_reversal` | `USD_JPY` | 1 | 0 | 1 | -3.100 | 0.0% | 0.0%-79.3% | 0.00 | `MACDH_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_counter_trend_scalp` | `USD_JPY` | 1 | 0 | 1 | -1.700 | 0.0% | 0.0%-79.3% | 0.00 | `MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_regime_range_cascade_scalp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `mtf_reversal_confluence` | `EUR_USD` | 1 | 0 | 1 | -3.000 | 0.0% | 0.0%-79.3% | 0.00 | `MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `EUR_JPY` | 4 | 0 | 4 | -13.250 | 0.0% | 0.0%-49.0% | 0.00 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `EUR_USD` | 18 | 8 | 10 | +2.533 | 44.4% | 24.6%-66.3% | 1.76 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `GBP_JPY` | 3 | 1 | 2 | +6.733 | 33.3% | 6.1%-79.2% | 1.55 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `ob_retest` | `GBP_USD` | 18 | 9 | 9 | -0.772 | 50.0% | 29.0%-71.0% | 0.88 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ob_retest` | `USD_JPY` | 26 | 9 | 17 | +4.077 | 34.6% | 19.4%-53.8% | 1.94 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `ofi_mr` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `OFI_MR_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `orb_trap` | `EUR_USD` | 18 | 1 | 17 | -3.161 | 5.6% | 1.0%-25.8% | 0.05 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `GBP_USD` | 18 | 13 | 5 | +8.994 | 72.2% | 49.1%-87.5% | 10.36 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `orb_trap` | `USD_JPY` | 1 | 0 | 1 | -0.800 | 0.0% | 0.0%-79.3% | 0.00 | `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `post_news_vol` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `EUR_JPY` | 2 | 0 | 2 | -10.650 | 0.0% | 0.0%-65.8% | 0.00 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `EUR_USD` | 1 | 0 | 1 | -7.300 | 0.0% | 0.0%-79.3% | 0.00 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `GBP_JPY` | 3 | 0 | 3 | -10.700 | 0.0% | 0.0%-56.2% | 0.00 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `pullback_to_liquidity_v1` | `GBP_USD` | 3 | 2 | 1 | +4.833 | 66.7% | 20.8%-93.9% | 2.41 | `PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `session_vol_expansion` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SESSION_VOL_EXPANSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `squeeze_release_momentum` | `GBP_USD` | 6 | 1 | 5 | -4.750 | 16.7% | 3.0%-56.4% | 0.10 | `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `EUR_JPY` | 17 | 14 | 3 | +19.471 | 82.4% | 59.0%-93.8% | 31.93 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_anti_hunt_bounce` | `EUR_USD` | 30 | 1 | 29 | -10.887 | 3.3% | 0.6%-16.7% | 0.01 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_anti_hunt_bounce` | `GBP_JPY` | 11 | 2 | 9 | -2.036 | 18.2% | 5.1%-47.7% | 0.49 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_anti_hunt_bounce` | `GBP_USD` | 7 | 6 | 1 | +7.214 | 85.7% | 48.7%-97.4% | 9.86 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_anti_hunt_bounce` | `USD_JPY` | 38 | 0 | 38 | -1.668 | 0.0% | 0.0%-9.2% | 0.00 | `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `EUR_JPY` | 33 | 8 | 25 | -2.918 | 24.2% | 12.8%-41.0% | 0.59 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `GBP_JPY` | 33 | 2 | 31 | -7.945 | 6.1% | 1.7%-19.6% | 0.19 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `GBP_USD` | 63 | 14 | 49 | -3.803 | 22.2% | 13.7%-33.9% | 0.38 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_break_retest` | `USD_JPY` | 62 | 15 | 47 | -1.526 | 24.2% | 15.2%-36.2% | 0.66 | `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_channel_reversal` | `EUR_USD` | 1 | 0 | 1 | -4.700 | 0.0% | 0.0%-79.3% | 0.00 | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_channel_reversal` | `GBP_USD` | 48 | 12 | 36 | -1.640 | 25.0% | 14.9%-38.8% | 0.56 | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_channel_reversal` | `USD_CHF` | 16 | 0 | 16 | -1.312 | 0.0% | 0.0%-19.4% | 0.00 | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_channel_reversal` | `USD_JPY` | 4 | 1 | 3 | -0.025 | 25.0% | 4.6%-69.9% | 0.99 | `SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `sr_fib_confluence` | `EUR_GBP` | 26 | 6 | 20 | -0.815 | 23.1% | 11.0%-42.1% | 0.71 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_fib_confluence` | `EUR_USD` | 52 | 12 | 40 | -1.827 | 23.1% | 13.7%-36.1% | 0.58 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_fib_confluence` | `GBP_JPY` | 7 | 0 | 7 | -20.971 | 0.0% | 0.0%-35.4% | 0.00 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `sr_fib_confluence` | `GBP_USD` | 72 | 15 | 57 | -3.154 | 20.8% | 13.1%-31.6% | 0.52 | `SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `sr_liquidity_grab` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `SR_LIQUIDITY_GRAB_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `stoch_trend_pullback` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `EUR_USD` | 5 | 0 | 5 | -3.540 | 0.0% | 0.0%-43.4% | 0.00 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `GBP_USD` | 3 | 0 | 3 | -6.467 | 0.0% | 0.0%-56.2% | 0.00 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `USD_CHF` | 1 | 0 | 1 | -0.300 | 0.0% | 0.0%-79.3% | 0.00 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `three_bar_reversal` | `USD_JPY` | 1 | 0 | 1 | -0.300 | 0.0% | 0.0%-79.3% | 0.00 | `THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_nakane_momentum` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tokyo_range_breakout_up` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TOKYO_RANGE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `EUR_USD` | 1 | 0 | 1 | -0.100 | 0.0% | 0.0%-79.3% | 0.00 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trend_rebound` | `USD_JPY` | 2 | 0 | 2 | -0.200 | 0.0% | 0.0%-65.8% | 0.00 | `TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trendline_sweep` | `EUR_GBP` | 2 | 0 | 2 | -4.600 | 0.0% | 0.0%-65.8% | 0.00 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `trendline_sweep` | `EUR_USD` | 19 | 5 | 14 | +0.495 | 26.3% | 11.8%-48.8% | 1.12 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `trendline_sweep` | `GBP_USD` | 20 | 1 | 19 | -18.360 | 5.0% | 0.9%-23.6% | 0.01 | `TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `turtle_soup` | `GBP_USD` | 13 | 4 | 9 | -2.292 | 30.8% | 12.7%-57.6% | 0.51 | `TURTLE_SOUP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `tvsm` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `TVSM_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `v_reversal` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `V_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vbp` | `-` | 0 | 0 | 0 | +0.000 | 0.0% | 0.0%-0.0% | n/a | `VBP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `EUR_JPY` | 1 | 0 | 1 | -8.400 | 0.0% | 0.0%-79.3% | 0.00 | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vdr_jpy` | `USD_JPY` | 5 | 4 | 1 | +35.800 | 80.0% | 37.6%-96.4% | 17.89 | `VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `vol_momentum_scalp` | `GBP_USD` | 41 | 8 | 33 | -1.788 | 19.5% | 10.2%-34.0% | 0.57 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_momentum_scalp` | `USD_JPY` | 10 | 0 | 10 | -2.940 | 0.0% | 0.0%-27.8% | 0.00 | `VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE`<br>`VOL_MOMENTUM_SCALP_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `EUR_USD` | 2 | 0 | 2 | -3.050 | 0.0% | 0.0%-65.8% | 0.00 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `GBP_USD` | 7 | 5 | 2 | +7.329 | 71.4% | 35.9%-91.8% | 12.15 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vol_surge_detector` | `USD_CHF` | 2 | 0 | 2 | -3.100 | 0.0% | 0.0%-65.8% | 0.00 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `vol_surge_detector` | `USD_JPY` | 10 | 2 | 8 | -1.880 | 20.0% | 5.7%-51.0% | 0.41 | `VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_JPY` | 4 | 1 | 3 | -9.100 | 25.0% | 4.6%-69.9% | 0.38 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `GBP_USD` | 2 | 1 | 1 | +0.750 | 50.0% | 9.5%-90.5% | 8.50 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `vwap_mean_reversion` | `USD_JPY` | 2 | 1 | 1 | +0.950 | 50.0% | 9.5%-90.5% | 1.09 | `VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `EUR_GBP` | 7 | 7 | 0 | +10.129 | 100.0% | 64.6%-100.0% | n/a | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| WARN | `wick_imbalance_reversion` | `EUR_JPY` | 19 | 4 | 15 | -3.279 | 21.1% | 8.5%-43.3% | 0.52 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `wick_imbalance_reversion` | `EUR_USD` | 31 | 8 | 23 | -1.042 | 25.8% | 13.7%-43.2% | 0.66 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `GBP_JPY` | 7 | 2 | 5 | -1.886 | 28.6% | 8.2%-64.1% | 0.82 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `GBP_USD` | 27 | 10 | 17 | +2.896 | 37.0% | 21.5%-55.8% | 1.86 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| OK | `wick_imbalance_reversion` | `USD_JPY` | 14 | 4 | 10 | +0.079 | 28.6% | 11.7%-54.6% | 1.02 | `ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE`<br>`WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `EUR_USD` | 56 | 12 | 44 | -4.963 | 21.4% | 12.7%-33.8% | 0.34 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `GBP_USD` | 44 | 13 | 31 | -1.298 | 29.5% | 18.2%-44.2% | 0.80 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
| CRITICAL | `xs_momentum` | `USD_JPY` | 39 | 12 | 27 | -1.038 | 30.8% | 18.6%-46.4% | 0.81 | `XS_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE` |
