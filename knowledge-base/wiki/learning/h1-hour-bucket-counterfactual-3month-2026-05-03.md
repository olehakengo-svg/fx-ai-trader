# H1 Hour-Bucket 3-Month Counterfactual

- Generated: `2026-05-03T02:47:17.765825+00:00`
- Window: `2026-02-01` to `2026-05-01` (UTC, end-exclusive)
- OOS split: IS `2026-02-01` to `2026-03-31`, OOS `2026-04-01` to `2026-05-01`
- Status: `OK`
- Total closed rows in window: `4114`
- Strict LIVE rows: `662` (`is_shadow=0 AND oanda_trade_id IS NOT NULL`)
- Strict SHADOW rows: `3288` (`is_shadow=1`, non-XAU)
- Bonferroni family size (shadow): `216`

## Summary

- False demotion rate: `n/a` (`0/0`) -> `PASS` vs 20% threshold.
- Grandfather verification targets: `bb_rsi_reversion, bb_squeeze_breakout, doji_breakout, donchian_momentum_breakout, dt_bb_rsi_mr, dt_sr_channel_reversal, dual_sr_bounce, ema200_trend_reversal, ema_cross, ema_pullback, ema_ribbon_ride, ema_trend_scalp, engulfing_bb, fib_reversal, gbp_deep_pullback, htf_false_breakout, inducement_ob, lin_reg_channel, macdh_reversal, mtf_reversal_confluence, orb_trap, pivot_breakout, post_news_vol, session_time_bias, squeeze_release_momentum, sr_break_retest, sr_channel_reversal, sr_fib_confluence, stoch_trend_pullback, streak_reversal, three_bar_reversal, trend_rebound, trendline_sweep, v_reversal, vix_carry_unwind, vol_momentum_scalp, vol_surge_detector, vwap_mean_reversion, xs_momentum`
- Insufficient-data cells (`N<30`): `471`

## Live Grandfather Verification

| strategy | pair | bucket | N | WR | EV | WR Wilson lo | EV CI lo | result |
|---|---|---|---:|---:|---:|---:|---:|---|
| bb_rsi_reversion | EUR_USD | Asia | 11 | 27.3% | -0.627 | 0.097 | -3.430 | grandfather |
| bb_rsi_reversion | EUR_USD | London | 12 | 50.0% | -0.600 | 0.254 | -2.431 | grandfather |
| bb_rsi_reversion | EUR_USD | NY-overlap | 11 | 36.4% | -1.100 | 0.152 | -2.703 | grandfather |
| bb_rsi_reversion | EUR_USD | Off | 1 | 0.0% | -3.100 | 0.000 | -3.100 | grandfather |
| bb_rsi_reversion | GBP_USD | London | 1 | 0.0% | -6.100 | 0.000 | -6.100 | grandfather |
| bb_rsi_reversion | GBP_USD | NY-overlap | 3 | 66.7% | +2.833 | 0.208 | -6.628 | grandfather |
| bb_rsi_reversion | USD_JPY | Asia | 59 | 50.8% | -0.185 | 0.384 | -0.989 | grandfather |
| bb_rsi_reversion | USD_JPY | London | 23 | 47.8% | -0.157 | 0.292 | -1.643 | grandfather |
| bb_rsi_reversion | USD_JPY | NY-overlap | 28 | 35.7% | -1.286 | 0.207 | -2.833 | grandfather |
| bb_rsi_reversion | USD_JPY | Off | 24 | 50.0% | -0.175 | 0.314 | -1.534 | grandfather |
| bb_squeeze_breakout | EUR_USD | London | 2 | 50.0% | -0.100 | 0.095 | -3.432 | grandfather |
| bb_squeeze_breakout | EUR_USD | NY-overlap | 4 | 50.0% | +1.150 | 0.150 | -3.651 | grandfather |
| bb_squeeze_breakout | USD_JPY | Asia | 6 | 33.3% | -1.200 | 0.097 | -4.033 | grandfather |
| bb_squeeze_breakout | USD_JPY | London | 2 | 50.0% | -1.200 | 0.095 | -4.728 | grandfather |
| bb_squeeze_breakout | USD_JPY | Off | 1 | 0.0% | -3.000 | 0.000 | -3.000 | grandfather |
| doji_breakout | EUR_USD | London | 1 | 0.0% | -10.600 | 0.000 | -10.600 | grandfather |
| doji_breakout | GBP_USD | London | 1 | 0.0% | -10.100 | 0.000 | -10.100 | grandfather |
| doji_breakout | USD_JPY | London | 1 | 100.0% | +12.400 | 0.207 | +12.400 | grandfather |
| doji_breakout | USD_JPY | NY-overlap | 1 | 100.0% | +9.200 | 0.207 | +9.200 | grandfather |
| donchian_momentum_breakout | EUR_USD | London | 3 | 33.3% | -12.000 | 0.061 | -24.569 | grandfather |
| donchian_momentum_breakout | EUR_USD | NY-overlap | 1 | 100.0% | +17.100 | 0.207 | +17.100 | grandfather |
| dt_bb_rsi_mr | EUR_USD | London | 2 | 50.0% | +0.100 | 0.095 | -10.092 | grandfather |
| dt_bb_rsi_mr | EUR_USD | NY-overlap | 2 | 0.0% | -9.350 | 0.000 | -11.996 | grandfather |
| dt_bb_rsi_mr | GBP_USD | NY-overlap | 2 | 50.0% | -5.100 | 0.095 | -17.448 | grandfather |
| dt_bb_rsi_mr | GBP_USD | Off | 1 | 100.0% | +18.600 | 0.207 | +18.600 | grandfather |
| dt_bb_rsi_mr | USD_JPY | Asia | 1 | 0.0% | -6.200 | 0.000 | -6.200 | grandfather |
| dt_bb_rsi_mr | USD_JPY | London | 2 | 50.0% | -1.850 | 0.095 | -7.044 | grandfather |
| dt_bb_rsi_mr | USD_JPY | NY-overlap | 4 | 75.0% | +5.100 | 0.301 | -1.499 | grandfather |
| dt_sr_channel_reversal | EUR_JPY | NY-overlap | 1 | 0.0% | -17.400 | 0.000 | -17.400 | grandfather |
| dt_sr_channel_reversal | GBP_USD | Asia | 1 | 100.0% | +9.100 | 0.207 | +9.100 | grandfather |
| dt_sr_channel_reversal | GBP_USD | Off | 1 | 0.0% | -9.100 | 0.000 | -9.100 | grandfather |
| dt_sr_channel_reversal | USD_JPY | Asia | 2 | 50.0% | -3.450 | 0.095 | -11.780 | grandfather |
| dt_sr_channel_reversal | USD_JPY | London | 1 | 100.0% | +0.700 | 0.207 | +0.700 | grandfather |
| dt_sr_channel_reversal | USD_JPY | NY-overlap | 1 | 100.0% | +16.300 | 0.207 | +16.300 | grandfather |
| dual_sr_bounce | USD_JPY | Asia | 3 | 0.0% | -4.467 | 0.000 | -5.713 | grandfather |
| dual_sr_bounce | USD_JPY | NY-overlap | 2 | 0.0% | -5.250 | 0.000 | -5.740 | grandfather |
| ema200_trend_reversal | USD_JPY | NY-overlap | 1 | 100.0% | +0.800 | 0.207 | +0.800 | grandfather |
| ema_cross | GBP_USD | London | 1 | 100.0% | +1.300 | 0.207 | +1.300 | grandfather |
| ema_cross | GBP_USD | Off | 1 | 0.0% | -9.300 | 0.000 | -9.300 | grandfather |
| ema_cross | USD_JPY | Asia | 1 | 100.0% | +0.800 | 0.207 | +0.800 | grandfather |
| ema_cross | USD_JPY | NY-overlap | 15 | 26.7% | -4.007 | 0.109 | -8.033 | grandfather |
| ema_cross | USD_JPY | Off | 2 | 0.0% | -5.050 | 0.000 | -5.148 | grandfather |
| ema_pullback | EUR_USD | London | 3 | 0.0% | -2.733 | 0.000 | -3.256 | grandfather |
| ema_pullback | EUR_USD | NY-overlap | 2 | 50.0% | +0.400 | 0.095 | -1.560 | grandfather |
| ema_pullback | EUR_USD | Off | 1 | 0.0% | -1.000 | 0.000 | -1.000 | grandfather |
| ema_pullback | USD_JPY | London | 3 | 33.3% | +1.133 | 0.061 | -7.165 | grandfather |
| ema_pullback | USD_JPY | NY-overlap | 6 | 66.7% | +1.517 | 0.300 | -1.565 | grandfather |
| ema_pullback | USD_JPY | Off | 2 | 0.0% | -0.700 | 0.000 | -0.896 | grandfather |
| ema_ribbon_ride | EUR_USD | Off | 2 | 0.0% | -3.200 | 0.000 | -3.396 | grandfather |
| ema_ribbon_ride | USD_JPY | Asia | 1 | 0.0% | -3.000 | 0.000 | -3.000 | grandfather |
| ema_ribbon_ride | USD_JPY | Off | 1 | 0.0% | -3.300 | 0.000 | -3.300 | grandfather |
| ema_trend_scalp | EUR_USD | London | 8 | 37.5% | +0.588 | 0.137 | -3.130 | grandfather |
| ema_trend_scalp | EUR_USD | NY-overlap | 2 | 50.0% | -0.600 | 0.095 | -3.344 | grandfather |
| ema_trend_scalp | GBP_USD | Asia | 1 | 0.0% | -5.100 | 0.000 | -5.100 | grandfather |
| ema_trend_scalp | GBP_USD | NY-overlap | 1 | 0.0% | -5.500 | 0.000 | -5.500 | grandfather |
| ema_trend_scalp | USD_JPY | Asia | 1 | 0.0% | -3.100 | 0.000 | -3.100 | grandfather |
| ema_trend_scalp | USD_JPY | NY-overlap | 3 | 66.7% | +2.600 | 0.208 | -4.907 | grandfather |
| engulfing_bb | EUR_USD | London | 4 | 25.0% | -0.625 | 0.046 | -5.280 | grandfather |
| engulfing_bb | EUR_USD | NY-overlap | 1 | 0.0% | -3.000 | 0.000 | -3.000 | grandfather |
| engulfing_bb | GBP_USD | London | 1 | 100.0% | +1.300 | 0.207 | +1.300 | grandfather |
| engulfing_bb | USD_JPY | Asia | 1 | 0.0% | -0.800 | 0.000 | -0.800 | grandfather |
| engulfing_bb | USD_JPY | London | 3 | 33.3% | -1.767 | 0.061 | -4.283 | grandfather |
| engulfing_bb | USD_JPY | NY-overlap | 5 | 40.0% | -0.280 | 0.118 | -4.056 | grandfather |
| fib_reversal | EUR_USD | Asia | 7 | 42.9% | -1.057 | 0.158 | -2.664 | grandfather |
| fib_reversal | EUR_USD | London | 19 | 42.1% | -0.705 | 0.231 | -2.513 | grandfather |
| fib_reversal | EUR_USD | NY-overlap | 11 | 36.4% | -0.755 | 0.152 | -2.393 | grandfather |
| fib_reversal | EUR_USD | Off | 4 | 25.0% | -1.300 | 0.046 | -2.822 | grandfather |
| fib_reversal | GBP_USD | London | 1 | 100.0% | +7.000 | 0.207 | +7.000 | grandfather |
| fib_reversal | USD_JPY | Asia | 12 | 41.7% | -0.533 | 0.193 | -2.642 | grandfather |
| fib_reversal | USD_JPY | London | 4 | 25.0% | -1.175 | 0.046 | -6.271 | grandfather |
| fib_reversal | USD_JPY | NY-overlap | 14 | 42.9% | +0.200 | 0.214 | -2.049 | grandfather |
| fib_reversal | USD_JPY | Off | 5 | 0.0% | -2.960 | 0.000 | -3.941 | grandfather |
| gbp_deep_pullback | GBP_USD | London | 2 | 100.0% | +4.600 | 0.342 | -2.260 | grandfather |
| htf_false_breakout | EUR_USD | NY-overlap | 1 | 100.0% | +2.000 | 0.207 | +2.000 | grandfather |
| inducement_ob | EUR_GBP | Asia | 1 | 100.0% | +1.100 | 0.207 | +1.100 | grandfather |
| inducement_ob | EUR_GBP | London | 1 | 0.0% | -5.000 | 0.000 | -5.000 | grandfather |
| inducement_ob | EUR_GBP | NY-overlap | 4 | 0.0% | -5.150 | 0.000 | -5.383 | grandfather |
| inducement_ob | EUR_USD | Asia | 2 | 0.0% | -1.700 | 0.000 | -2.876 | grandfather |
| inducement_ob | GBP_USD | NY-overlap | 1 | 0.0% | -0.600 | 0.000 | -0.600 | grandfather |
| lin_reg_channel | EUR_USD | London | 1 | 0.0% | -9.600 | 0.000 | -9.600 | grandfather |
| lin_reg_channel | EUR_USD | NY-overlap | 1 | 100.0% | +8.800 | 0.207 | +8.800 | grandfather |
| macdh_reversal | EUR_USD | Asia | 5 | 20.0% | -2.280 | 0.036 | -3.890 | grandfather |
| macdh_reversal | EUR_USD | London | 14 | 42.9% | -0.664 | 0.214 | -2.486 | grandfather |
| macdh_reversal | EUR_USD | NY-overlap | 12 | 25.0% | -0.933 | 0.089 | -2.665 | grandfather |
| macdh_reversal | EUR_USD | Off | 1 | 100.0% | +2.800 | 0.207 | +2.800 | grandfather |
| macdh_reversal | USD_JPY | Asia | 4 | 25.0% | -2.425 | 0.046 | -4.491 | grandfather |
| macdh_reversal | USD_JPY | London | 3 | 0.0% | -1.800 | 0.000 | -2.976 | grandfather |
| macdh_reversal | USD_JPY | NY-overlap | 8 | 37.5% | -0.650 | 0.137 | -2.748 | grandfather |
| macdh_reversal | USD_JPY | Off | 10 | 20.0% | -0.750 | 0.057 | -2.907 | grandfather |
| mtf_reversal_confluence | EUR_USD | NY-overlap | 2 | 0.0% | -1.800 | 0.000 | -4.152 | grandfather |
| mtf_reversal_confluence | USD_JPY | NY-overlap | 1 | 100.0% | +4.200 | 0.207 | +4.200 | grandfather |
| mtf_reversal_confluence | USD_JPY | Off | 1 | 100.0% | +3.200 | 0.207 | +3.200 | grandfather |
| orb_trap | EUR_USD | NY-overlap | 1 | 100.0% | +11.900 | 0.207 | +11.900 | grandfather |
| orb_trap | GBP_USD | London | 1 | 100.0% | +16.100 | 0.207 | +16.100 | grandfather |
| orb_trap | GBP_USD | NY-overlap | 3 | 66.7% | +8.333 | 0.208 | -10.517 | grandfather |
| pivot_breakout | USD_JPY | NY-overlap | 1 | 0.0% | -19.900 | 0.000 | -19.900 | grandfather |
| post_news_vol | GBP_USD | London | 1 | 100.0% | +1.300 | 0.207 | +1.300 | grandfather |
| post_news_vol | USD_JPY | Asia | 1 | 100.0% | +17.700 | 0.207 | +17.700 | grandfather |
| session_time_bias | GBP_USD | Asia | 3 | 0.0% | -6.733 | 0.000 | -8.875 | grandfather |
| session_time_bias | GBP_USD | London | 4 | 50.0% | -1.950 | 0.150 | -5.631 | grandfather |
| squeeze_release_momentum | GBP_USD | Asia | 1 | 0.0% | -6.100 | 0.000 | -6.100 | grandfather |
| sr_break_retest | GBP_USD | NY-overlap | 3 | 66.7% | +6.067 | 0.208 | -11.597 | grandfather |
| sr_break_retest | USD_JPY | Asia | 2 | 0.0% | -6.000 | 0.000 | -16.192 | grandfather |
| sr_break_retest | USD_JPY | London | 1 | 0.0% | -11.100 | 0.000 | -11.100 | grandfather |
| sr_break_retest | USD_JPY | NY-overlap | 1 | 0.0% | -20.400 | 0.000 | -20.400 | grandfather |
| sr_channel_reversal | EUR_USD | London | 2 | 50.0% | +2.600 | 0.095 | -8.376 | grandfather |
| sr_channel_reversal | EUR_USD | NY-overlap | 5 | 20.0% | -1.720 | 0.036 | -5.052 | grandfather |
| sr_channel_reversal | GBP_USD | London | 2 | 50.0% | +2.250 | 0.095 | -12.744 | grandfather |
| sr_channel_reversal | GBP_USD | NY-overlap | 2 | 50.0% | +3.000 | 0.095 | -5.232 | grandfather |
| sr_channel_reversal | USD_JPY | Asia | 8 | 37.5% | -0.925 | 0.137 | -3.001 | grandfather |
| sr_channel_reversal | USD_JPY | London | 9 | 11.1% | -2.311 | 0.020 | -4.365 | grandfather |
| sr_channel_reversal | USD_JPY | Off | 2 | 50.0% | -1.100 | 0.095 | -5.608 | grandfather |
| sr_fib_confluence | EUR_JPY | Asia | 1 | 0.0% | -11.300 | 0.000 | -11.300 | grandfather |
| sr_fib_confluence | EUR_USD | Asia | 4 | 25.0% | -1.725 | 0.046 | -10.098 | grandfather |
| sr_fib_confluence | EUR_USD | London | 5 | 40.0% | +0.420 | 0.118 | -13.106 | grandfather |
| sr_fib_confluence | EUR_USD | NY-overlap | 3 | 66.7% | +3.033 | 0.208 | -13.819 | grandfather |
| sr_fib_confluence | GBP_JPY | Asia | 1 | 0.0% | -11.500 | 0.000 | -11.500 | grandfather |
| sr_fib_confluence | GBP_USD | Asia | 4 | 50.0% | +0.675 | 0.150 | -8.647 | grandfather |
| sr_fib_confluence | GBP_USD | London | 5 | 80.0% | +5.440 | 0.376 | -3.431 | grandfather |
| sr_fib_confluence | GBP_USD | NY-overlap | 1 | 0.0% | -10.100 | 0.000 | -10.100 | grandfather |
| sr_fib_confluence | GBP_USD | Off | 2 | 0.0% | -9.200 | 0.000 | -9.396 | grandfather |
| sr_fib_confluence | USD_JPY | Asia | 1 | 0.0% | -4.400 | 0.000 | -4.400 | grandfather |
| sr_fib_confluence | USD_JPY | London | 3 | 33.3% | -7.033 | 0.061 | -29.050 | grandfather |
| sr_fib_confluence | USD_JPY | NY-overlap | 5 | 40.0% | -4.240 | 0.118 | -9.699 | grandfather |
| stoch_trend_pullback | EUR_USD | London | 7 | 28.6% | -0.371 | 0.082 | -3.926 | grandfather |
| stoch_trend_pullback | EUR_USD | NY-overlap | 2 | 100.0% | +3.900 | 0.342 | +2.528 | grandfather |
| stoch_trend_pullback | EUR_USD | Off | 2 | 0.0% | -3.000 | 0.000 | -3.000 | grandfather |
| stoch_trend_pullback | USD_JPY | Asia | 7 | 71.4% | +2.100 | 0.359 | -0.721 | grandfather |
| stoch_trend_pullback | USD_JPY | London | 8 | 25.0% | -1.212 | 0.071 | -3.075 | grandfather |
| stoch_trend_pullback | USD_JPY | NY-overlap | 4 | 25.0% | -1.750 | 0.046 | -4.727 | grandfather |
| stoch_trend_pullback | USD_JPY | Off | 6 | 50.0% | +1.550 | 0.188 | -1.939 | grandfather |
| streak_reversal | USD_JPY | London | 1 | 0.0% | -23.400 | 0.000 | -23.400 | grandfather |
| three_bar_reversal | USD_JPY | Asia | 1 | 0.0% | -3.200 | 0.000 | -3.200 | grandfather |
| trend_rebound | EUR_USD | London | 4 | 25.0% | -1.000 | 0.046 | -4.986 | grandfather |
| trend_rebound | EUR_USD | NY-overlap | 3 | 66.7% | +2.033 | 0.208 | -4.150 | grandfather |
| trend_rebound | GBP_USD | NY-overlap | 1 | 0.0% | -7.100 | 0.000 | -7.100 | grandfather |
| trend_rebound | USD_JPY | Asia | 2 | 50.0% | +0.300 | 0.095 | -7.344 | grandfather |
| trend_rebound | USD_JPY | London | 3 | 33.3% | -0.533 | 0.061 | -5.368 | grandfather |
| trend_rebound | USD_JPY | Off | 2 | 50.0% | -1.400 | 0.095 | -5.320 | grandfather |
| trendline_sweep | GBP_USD | Asia | 1 | 100.0% | +1.400 | 0.207 | +1.400 | grandfather |
| trendline_sweep | GBP_USD | London | 3 | 33.3% | -1.767 | 0.061 | -5.051 | grandfather |
| v_reversal | USD_JPY | Asia | 1 | 0.0% | -3.000 | 0.000 | -3.000 | grandfather |
| v_reversal | USD_JPY | NY-overlap | 3 | 33.3% | +0.400 | 0.061 | -7.835 | grandfather |
| v_reversal | USD_JPY | Off | 1 | 0.0% | -3.100 | 0.000 | -3.100 | grandfather |
| vix_carry_unwind | USD_JPY | Asia | 2 | 50.0% | -6.550 | 0.095 | -38.203 | grandfather |
| vix_carry_unwind | USD_JPY | London | 1 | 0.0% | -8.200 | 0.000 | -8.200 | grandfather |
| vol_momentum_scalp | GBP_USD | London | 2 | 50.0% | +1.750 | 0.095 | -12.852 | grandfather |
| vol_momentum_scalp | GBP_USD | NY-overlap | 1 | 0.0% | -3.800 | 0.000 | -3.800 | grandfather |
| vol_momentum_scalp | USD_JPY | Asia | 1 | 100.0% | +4.200 | 0.207 | +4.200 | grandfather |
| vol_momentum_scalp | USD_JPY | London | 7 | 57.1% | +0.571 | 0.250 | -2.857 | grandfather |
| vol_momentum_scalp | USD_JPY | NY-overlap | 3 | 66.7% | +0.533 | 0.208 | -3.775 | grandfather |
| vol_momentum_scalp | USD_JPY | Off | 2 | 50.0% | +0.950 | 0.095 | -7.380 | grandfather |
| vol_surge_detector | EUR_USD | London | 3 | 66.7% | +0.667 | 0.208 | -3.409 | grandfather |
| vol_surge_detector | EUR_USD | NY-overlap | 3 | 66.7% | +2.233 | 0.208 | -4.645 | grandfather |
| vol_surge_detector | GBP_USD | London | 1 | 0.0% | -3.900 | 0.000 | -3.900 | grandfather |
| vol_surge_detector | GBP_USD | NY-overlap | 2 | 100.0% | +1.150 | 0.342 | +0.856 | grandfather |
| vol_surge_detector | USD_JPY | Asia | 10 | 40.0% | -0.970 | 0.168 | -3.610 | grandfather |
| vol_surge_detector | USD_JPY | London | 5 | 20.0% | -1.680 | 0.036 | -4.563 | grandfather |
| vol_surge_detector | USD_JPY | NY-overlap | 9 | 77.8% | +1.033 | 0.453 | -1.173 | grandfather |
| vwap_mean_reversion | EUR_JPY | London | 1 | 0.0% | -22.600 | 0.000 | -22.600 | grandfather |
| vwap_mean_reversion | EUR_JPY | NY-overlap | 2 | 50.0% | -4.300 | 0.095 | -15.668 | grandfather |
| vwap_mean_reversion | EUR_JPY | Off | 1 | 100.0% | +2.100 | 0.207 | +2.100 | grandfather |
| vwap_mean_reversion | GBP_JPY | Asia | 1 | 100.0% | +44.200 | 0.207 | +44.200 | grandfather |
| vwap_mean_reversion | GBP_JPY | London | 1 | 0.0% | -20.100 | 0.000 | -20.100 | grandfather |
| vwap_mean_reversion | GBP_USD | Asia | 2 | 50.0% | -3.050 | 0.095 | -11.380 | grandfather |
| vwap_mean_reversion | GBP_USD | London | 2 | 0.0% | -18.950 | 0.000 | -25.908 | grandfather |
| vwap_mean_reversion | GBP_USD | NY-overlap | 1 | 0.0% | -14.100 | 0.000 | -14.100 | grandfather |
| xs_momentum | GBP_USD | London | 1 | 0.0% | -21.400 | 0.000 | -21.400 | grandfather |
| xs_momentum | GBP_USD | NY-overlap | 1 | 100.0% | +22.200 | 0.207 | +22.200 | grandfather |

## Shadow Dry-Run

| strategy | pair | bucket | baseline | new | N | WR | EV | PF | Kelly | WR Wilson lo | EV CI lo | p_bonf | IS N/EV | OOS N/EV | reason |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| bb_rsi_reversion | EUR_USD | London | pending | pending | 44 | 29.5% | -1.234 | 0.53 | -0.260 | 0.182 | -2.479 | 1.0000 | 0/+0.000 | 44/-1.234 | grandfather |
| bb_rsi_reversion | EUR_USD | NY-overlap | pending | pending | 27 | 44.4% | -0.167 | 0.94 | -0.031 | 0.276 | -2.172 | 1.0000 | 0/+0.000 | 27/-0.167 | grandfather |
| bb_rsi_reversion | GBP_USD | Asia | pending | pending | 4 | 0.0% | -4.250 | 0.00 | - | 0.000 | -6.100 | 1.0000 | 0/+0.000 | 4/-4.250 | grandfather |
| bb_rsi_reversion | GBP_USD | London | pending | pending | 13 | 7.7% | -5.515 | 0.09 | -0.745 | 0.014 | -7.716 | 0.4929 | 0/+0.000 | 13/-5.515 | grandfather |
| bb_rsi_reversion | GBP_USD | NY-overlap | pending | pending | 17 | 11.8% | -4.953 | 0.16 | -0.608 | 0.033 | -7.417 | 0.3491 | 0/+0.000 | 17/-4.953 | grandfather |
| bb_rsi_reversion | GBP_USD | Off | pending | pending | 3 | 100.0% | +11.133 | inf | - | 0.439 | +9.252 | 1.0000 | 0/+0.000 | 3/+11.133 | grandfather |
| bb_rsi_reversion | USD_JPY | Asia | pending | pending | 38 | 21.1% | -1.729 | 0.38 | -0.350 | 0.111 | -2.907 | 0.0774 | 0/+0.000 | 38/-1.729 | grandfather |
| bb_rsi_reversion | USD_JPY | London | pending | pending | 55 | 30.9% | -1.540 | 0.50 | -0.307 | 0.203 | -2.828 | 1.0000 | 0/+0.000 | 55/-1.540 | grandfather |
| bb_rsi_reversion | USD_JPY | NY-overlap | pending | pending | 57 | 38.6% | -0.660 | 0.79 | -0.104 | 0.271 | -2.217 | 1.0000 | 0/+0.000 | 57/-0.660 | grandfather |
| bb_rsi_reversion | USD_JPY | Off | pending | pending | 34 | 32.4% | -1.679 | 0.46 | -0.378 | 0.191 | -3.320 | 1.0000 | 0/+0.000 | 34/-1.679 | grandfather |
| bb_squeeze_breakout | EUR_USD | London | pending | pending | 19 | 5.3% | -2.679 | 0.13 | -0.357 | 0.009 | -3.880 | 0.0208 | 0/+0.000 | 19/-2.679 | grandfather |
| bb_squeeze_breakout | EUR_USD | NY-overlap | pending | pending | 16 | 12.5% | -0.894 | 0.70 | -0.055 | 0.035 | -5.035 | 0.5832 | 0/+0.000 | 16/-0.894 | grandfather |
| bb_squeeze_breakout | GBP_USD | Asia | pending | pending | 1 | 0.0% | -5.000 | 0.00 | - | 0.000 | -5.000 | 1.0000 | 0/+0.000 | 1/-5.000 | grandfather |
| bb_squeeze_breakout | GBP_USD | London | pending | pending | 2 | 50.0% | +5.800 | 3.70 | 0.365 | 0.095 | -13.996 | 1.0000 | 0/+0.000 | 2/+5.800 | grandfather |
| bb_squeeze_breakout | GBP_USD | NY-overlap | pending | pending | 2 | 0.0% | -4.700 | 0.00 | - | 0.000 | -6.464 | 1.0000 | 0/+0.000 | 2/-4.700 | grandfather |
| bb_squeeze_breakout | GBP_USD | Off | pending | pending | 7 | 42.9% | +5.200 | 3.09 | 0.290 | 0.158 | -3.738 | 1.0000 | 0/+0.000 | 7/+5.200 | grandfather |
| bb_squeeze_breakout | USD_JPY | Asia | pending | pending | 15 | 26.7% | -1.020 | 0.58 | -0.193 | 0.109 | -3.111 | 1.0000 | 0/+0.000 | 15/-1.020 | grandfather |
| bb_squeeze_breakout | USD_JPY | London | pending | pending | 17 | 11.8% | -1.776 | 0.43 | -0.154 | 0.033 | -4.376 | 0.3491 | 0/+0.000 | 17/-1.776 | grandfather |
| bb_squeeze_breakout | USD_JPY | NY-overlap | pending | pending | 10 | 60.0% | +7.560 | 5.04 | 0.481 | 0.313 | +0.515 | 1.0000 | 0/+0.000 | 10/+7.560 | grandfather |
| bb_squeeze_breakout | USD_JPY | Off | pending | pending | 10 | 20.0% | -1.140 | 0.59 | -0.140 | 0.057 | -4.232 | 1.0000 | 0/+0.000 | 10/-1.140 | grandfather |
| confluence_scalp | EUR_USD | London | pending | pending | 1 | 0.0% | -0.600 | 0.00 | - | 0.000 | -0.600 | 1.0000 | 0/+0.000 | 1/-0.600 | insufficient_data |
| doji_breakout | GBP_USD | London | pending | pending | 1 | 0.0% | -5.000 | 0.00 | - | 0.000 | -5.000 | 1.0000 | 0/+0.000 | 1/-5.000 | grandfather |
| doji_breakout | GBP_USD | NY-overlap | pending | pending | 1 | 0.0% | -11.300 | 0.00 | - | 0.000 | -11.300 | 1.0000 | 0/+0.000 | 1/-11.300 | grandfather |
| doji_breakout | USD_JPY | Asia | pending | pending | 1 | 100.0% | +9.100 | inf | - | 0.207 | +9.100 | 1.0000 | 0/+0.000 | 1/+9.100 | grandfather |
| doji_breakout | USD_JPY | London | pending | pending | 1 | 100.0% | +24.800 | inf | - | 0.207 | +24.800 | 1.0000 | 0/+0.000 | 1/+24.800 | grandfather |
| donchian_momentum_breakout | EUR_USD | London | pending | pending | 1 | 0.0% | -7.900 | 0.00 | - | 0.000 | -7.900 | 1.0000 | 0/+0.000 | 1/-7.900 | grandfather |
| donchian_momentum_breakout | EUR_USD | NY-overlap | pending | pending | 1 | 0.0% | -21.600 | 0.00 | - | 0.000 | -21.600 | 1.0000 | 0/+0.000 | 1/-21.600 | grandfather |
| dt_bb_rsi_mr | EUR_USD | London | pending | pending | 7 | 57.1% | +3.343 | 2.38 | 0.332 | 0.250 | -3.559 | 1.0000 | 0/+0.000 | 7/+3.343 | grandfather |
| dt_bb_rsi_mr | EUR_USD | NY-overlap | pending | pending | 1 | 0.0% | -3.200 | 0.00 | - | 0.000 | -3.200 | 1.0000 | 0/+0.000 | 1/-3.200 | grandfather |
| dt_bb_rsi_mr | GBP_USD | Asia | pending | pending | 10 | 30.0% | -0.940 | 0.74 | -0.105 | 0.108 | -5.342 | 1.0000 | 0/+0.000 | 10/-0.940 | grandfather |
| dt_bb_rsi_mr | GBP_USD | London | pending | pending | 4 | 25.0% | -3.400 | 0.46 | -0.296 | 0.046 | -13.145 | 1.0000 | 0/+0.000 | 4/-3.400 | grandfather |
| dt_bb_rsi_mr | GBP_USD | NY-overlap | pending | pending | 2 | 100.0% | +7.550 | inf | - | 0.342 | -2.740 | 1.0000 | 0/+0.000 | 2/+7.550 | grandfather |
| dt_bb_rsi_mr | GBP_USD | Off | pending | pending | 5 | 60.0% | +7.060 | 2.84 | 0.389 | 0.231 | -6.806 | 1.0000 | 0/+0.000 | 5/+7.060 | grandfather |
| dt_bb_rsi_mr | USD_JPY | Asia | pending | pending | 3 | 33.3% | +0.233 | 1.07 | 0.021 | 0.061 | -11.394 | 1.0000 | 0/+0.000 | 3/+0.233 | grandfather |
| dt_bb_rsi_mr | USD_JPY | London | pending | pending | 6 | 33.3% | -1.183 | 0.66 | -0.174 | 0.097 | -6.650 | 1.0000 | 0/+0.000 | 6/-1.183 | grandfather |
| dt_bb_rsi_mr | USD_JPY | NY-overlap | pending | pending | 1 | 0.0% | -1.800 | 0.00 | - | 0.000 | -1.800 | 1.0000 | 0/+0.000 | 1/-1.800 | grandfather |
| dt_bb_rsi_mr | USD_JPY | Off | pending | pending | 1 | 0.0% | -8.200 | 0.00 | - | 0.000 | -8.200 | 1.0000 | 0/+0.000 | 1/-8.200 | grandfather |
| dt_fib_reversal | EUR_JPY | Asia | pending | pending | 3 | 66.7% | +13.767 | 15.75 | 0.624 | 0.208 | -2.551 | 1.0000 | 0/+0.000 | 3/+13.767 | insufficient_data |
| dt_fib_reversal | EUR_JPY | London | pending | pending | 1 | 0.0% | -15.000 | 0.00 | - | 0.000 | -15.000 | 1.0000 | 0/+0.000 | 1/-15.000 | insufficient_data |
| dt_fib_reversal | EUR_JPY | NY-overlap | pending | pending | 1 | 100.0% | +22.300 | inf | - | 0.207 | +22.300 | 1.0000 | 0/+0.000 | 1/+22.300 | insufficient_data |
| dt_fib_reversal | EUR_JPY | Off | pending | pending | 2 | 0.0% | -6.500 | 0.00 | - | 0.000 | -14.340 | 1.0000 | 0/+0.000 | 2/-6.500 | insufficient_data |
| dt_fib_reversal | EUR_USD | London | pending | pending | 2 | 50.0% | +1.800 | 1.50 | 0.167 | 0.095 | -15.840 | 1.0000 | 0/+0.000 | 2/+1.800 | insufficient_data |
| dt_fib_reversal | EUR_USD | NY-overlap | pending | pending | 1 | 0.0% | -10.600 | 0.00 | - | 0.000 | -10.600 | 1.0000 | 0/+0.000 | 1/-10.600 | insufficient_data |
| dt_fib_reversal | GBP_USD | Asia | pending | pending | 2 | 100.0% | +14.850 | inf | - | 0.342 | +14.556 | 1.0000 | 0/+0.000 | 2/+14.850 | insufficient_data |
| dt_fib_reversal | GBP_USD | London | pending | pending | 2 | 0.0% | -6.500 | 0.00 | - | 0.000 | -13.752 | 1.0000 | 0/+0.000 | 2/-6.500 | insufficient_data |
| dt_fib_reversal | GBP_USD | NY-overlap | pending | pending | 1 | 0.0% | -0.800 | 0.00 | - | 0.000 | -0.800 | 1.0000 | 0/+0.000 | 1/-0.800 | insufficient_data |
| dt_fib_reversal | GBP_USD | Off | pending | pending | 1 | 0.0% | -1.400 | 0.00 | - | 0.000 | -1.400 | 1.0000 | 0/+0.000 | 1/-1.400 | insufficient_data |
| dt_fib_reversal | USD_JPY | Asia | pending | pending | 5 | 20.0% | -3.060 | 0.53 | -0.176 | 0.036 | -13.231 | 1.0000 | 0/+0.000 | 5/-3.060 | insufficient_data |
| dt_fib_reversal | USD_JPY | London | pending | pending | 2 | 0.0% | -8.500 | 0.00 | - | 0.000 | -8.696 | 1.0000 | 0/+0.000 | 2/-8.500 | insufficient_data |
| dt_fib_reversal | USD_JPY | NY-overlap | pending | pending | 2 | 50.0% | +4.400 | 2.37 | 0.289 | 0.095 | -16.768 | 1.0000 | 0/+0.000 | 2/+4.400 | insufficient_data |
| dt_fib_reversal | USD_JPY | Off | pending | pending | 2 | 0.0% | -5.450 | 0.00 | - | 0.000 | -8.880 | 1.0000 | 0/+0.000 | 2/-5.450 | insufficient_data |
| dt_sr_channel_reversal | EUR_JPY | Asia | pending | pending | 1 | 0.0% | -8.300 | 0.00 | - | 0.000 | -8.300 | 1.0000 | 0/+0.000 | 1/-8.300 | grandfather |
| dt_sr_channel_reversal | EUR_JPY | London | pending | pending | 7 | 28.6% | -1.443 | 0.74 | -0.099 | 0.082 | -11.229 | 1.0000 | 0/+0.000 | 7/-1.443 | grandfather |
| dt_sr_channel_reversal | EUR_JPY | NY-overlap | pending | pending | 12 | 33.3% | +3.233 | 1.44 | 0.102 | 0.138 | -10.729 | 1.0000 | 0/+0.000 | 12/+3.233 | grandfather |
| dt_sr_channel_reversal | EUR_USD | London | pending | pending | 9 | 33.3% | -1.022 | 0.67 | -0.165 | 0.121 | -5.454 | 1.0000 | 0/+0.000 | 9/-1.022 | grandfather |
| dt_sr_channel_reversal | EUR_USD | NY-overlap | pending | pending | 2 | 0.0% | -3.200 | 0.00 | - | 0.000 | -7.708 | 1.0000 | 0/+0.000 | 2/-3.200 | grandfather |
| dt_sr_channel_reversal | GBP_JPY | London | pending | pending | 1 | 0.0% | -20.100 | 0.00 | - | 0.000 | -20.100 | 1.0000 | 0/+0.000 | 1/-20.100 | grandfather |
| dt_sr_channel_reversal | GBP_JPY | NY-overlap | pending | pending | 2 | 100.0% | +8.550 | inf | - | 0.342 | -0.564 | 1.0000 | 0/+0.000 | 2/+8.550 | grandfather |
| dt_sr_channel_reversal | GBP_USD | Asia | pending | pending | 2 | 100.0% | +2.800 | inf | - | 0.342 | +2.604 | 1.0000 | 0/+0.000 | 2/+2.800 | grandfather |
| dt_sr_channel_reversal | GBP_USD | London | pending | pending | 7 | 14.3% | -3.914 | 0.07 | -1.864 | 0.026 | -7.049 | 1.0000 | 0/+0.000 | 7/-3.914 | grandfather |
| dt_sr_channel_reversal | GBP_USD | NY-overlap | pending | pending | 5 | 0.0% | -5.080 | 0.00 | - | 0.000 | -8.335 | 1.0000 | 0/+0.000 | 5/-5.080 | grandfather |
| dt_sr_channel_reversal | GBP_USD | Off | pending | pending | 1 | 100.0% | +2.900 | inf | - | 0.207 | +2.900 | 1.0000 | 0/+0.000 | 1/+2.900 | grandfather |
| dt_sr_channel_reversal | USD_JPY | Asia | pending | pending | 6 | 50.0% | +0.283 | 1.08 | 0.038 | 0.188 | -6.618 | 1.0000 | 0/+0.000 | 6/+0.283 | grandfather |
| dt_sr_channel_reversal | USD_JPY | London | pending | pending | 5 | 60.0% | +3.120 | 2.22 | 0.330 | 0.231 | -6.183 | 1.0000 | 0/+0.000 | 5/+3.120 | grandfather |
| dt_sr_channel_reversal | USD_JPY | NY-overlap | pending | pending | 4 | 25.0% | +2.900 | 2.35 | 0.144 | 0.046 | -8.453 | 1.0000 | 0/+0.000 | 4/+2.900 | grandfather |
| dt_sr_channel_reversal | USD_JPY | Off | pending | pending | 2 | 50.0% | +0.000 | 1.00 | 0.000 | 0.095 | -5.292 | 1.0000 | 0/+0.000 | 2/+0.000 | grandfather |
| dual_sr_bounce | EUR_JPY | Asia | pending | pending | 1 | 0.0% | -13.100 | 0.00 | - | 0.000 | -13.100 | 1.0000 | 0/+0.000 | 1/-13.100 | grandfather |
| dual_sr_bounce | EUR_JPY | London | pending | pending | 1 | 0.0% | -5.100 | 0.00 | - | 0.000 | -5.100 | 1.0000 | 0/+0.000 | 1/-5.100 | grandfather |
| dual_sr_bounce | EUR_JPY | NY-overlap | pending | pending | 3 | 33.3% | +1.267 | 1.12 | 0.035 | 0.061 | -33.494 | 1.0000 | 0/+0.000 | 3/+1.267 | grandfather |
| dual_sr_bounce | EUR_JPY | Off | pending | pending | 2 | 0.0% | -6.000 | 0.00 | - | 0.000 | -11.292 | 1.0000 | 0/+0.000 | 2/-6.000 | grandfather |
| dual_sr_bounce | GBP_JPY | Asia | pending | pending | 2 | 0.0% | -7.800 | 0.00 | - | 0.000 | -19.560 | 1.0000 | 0/+0.000 | 2/-7.800 | grandfather |
| dual_sr_bounce | GBP_JPY | London | pending | pending | 1 | 0.0% | -10.600 | 0.00 | - | 0.000 | -10.600 | 1.0000 | 0/+0.000 | 1/-10.600 | grandfather |
| dual_sr_bounce | GBP_JPY | Off | pending | pending | 3 | 0.0% | -20.467 | 0.00 | - | 0.000 | -27.887 | 1.0000 | 0/+0.000 | 3/-20.467 | grandfather |
| dual_sr_bounce | GBP_USD | London | pending | pending | 2 | 0.0% | -9.650 | 0.00 | - | 0.000 | -12.688 | 1.0000 | 0/+0.000 | 2/-9.650 | grandfather |
| dual_sr_bounce | GBP_USD | NY-overlap | pending | pending | 4 | 0.0% | -11.925 | 0.00 | - | 0.000 | -16.701 | 1.0000 | 0/+0.000 | 4/-11.925 | grandfather |
| dual_sr_bounce | GBP_USD | Off | pending | pending | 3 | 0.0% | -5.467 | 0.00 | - | 0.000 | -7.341 | 1.0000 | 0/+0.000 | 3/-5.467 | grandfather |
| dual_sr_bounce | USD_JPY | Asia | pending | pending | 1 | 100.0% | +21.400 | inf | - | 0.207 | +21.400 | 1.0000 | 0/+0.000 | 1/+21.400 | grandfather |
| dual_sr_bounce | USD_JPY | London | pending | pending | 2 | 0.0% | -7.200 | 0.00 | - | 0.000 | -7.396 | 1.0000 | 0/+0.000 | 2/-7.200 | grandfather |
| dual_sr_bounce | USD_JPY | NY-overlap | pending | pending | 3 | 33.3% | -2.000 | 0.72 | -0.127 | 0.061 | -19.348 | 1.0000 | 0/+0.000 | 3/-2.000 | grandfather |
| dual_sr_bounce | USD_JPY | Off | pending | pending | 1 | 0.0% | -5.000 | 0.00 | - | 0.000 | -5.000 | 1.0000 | 0/+0.000 | 1/-5.000 | grandfather |
| ema200_trend_reversal | EUR_JPY | Asia | pending | pending | 3 | 0.0% | -18.167 | 0.00 | - | 0.000 | -25.673 | 1.0000 | 0/+0.000 | 3/-18.167 | grandfather |
| ema200_trend_reversal | EUR_JPY | London | pending | pending | 6 | 66.7% | +13.450 | 6.24 | 0.560 | 0.300 | -2.676 | 1.0000 | 0/+0.000 | 6/+13.450 | grandfather |
| ema200_trend_reversal | EUR_JPY | Off | pending | pending | 3 | 0.0% | -15.000 | 0.00 | - | 0.000 | -20.150 | 1.0000 | 0/+0.000 | 3/-15.000 | grandfather |
| ema200_trend_reversal | EUR_USD | London | pending | pending | 1 | 0.0% | -8.300 | 0.00 | - | 0.000 | -8.300 | 1.0000 | 0/+0.000 | 1/-8.300 | grandfather |
| ema200_trend_reversal | EUR_USD | NY-overlap | pending | pending | 1 | 0.0% | -3.000 | 0.00 | - | 0.000 | -3.000 | 1.0000 | 0/+0.000 | 1/-3.000 | grandfather |
| ema200_trend_reversal | GBP_JPY | London | pending | pending | 1 | 100.0% | +28.300 | inf | - | 0.207 | +28.300 | 1.0000 | 0/+0.000 | 1/+28.300 | grandfather |
| ema200_trend_reversal | GBP_JPY | NY-overlap | pending | pending | 2 | 0.0% | -9.500 | 0.00 | - | 0.000 | -23.612 | 1.0000 | 0/+0.000 | 2/-9.500 | grandfather |
| ema200_trend_reversal | GBP_USD | Asia | pending | pending | 1 | 0.0% | -7.200 | 0.00 | - | 0.000 | -7.200 | 1.0000 | 0/+0.000 | 1/-7.200 | grandfather |
| ema200_trend_reversal | GBP_USD | London | pending | pending | 2 | 50.0% | +2.950 | 1.70 | 0.206 | 0.095 | -19.296 | 1.0000 | 0/+0.000 | 2/+2.950 | grandfather |
| ema200_trend_reversal | USD_JPY | Asia | pending | pending | 1 | 0.0% | -0.900 | 0.00 | - | 0.000 | -0.900 | 1.0000 | 0/+0.000 | 1/-0.900 | grandfather |
| ema200_trend_reversal | USD_JPY | London | pending | pending | 4 | 50.0% | +2.200 | 1.51 | 0.169 | 0.150 | -10.248 | 1.0000 | 0/+0.000 | 4/+2.200 | grandfather |
| ema200_trend_reversal | USD_JPY | NY-overlap | pending | pending | 4 | 100.0% | +15.400 | inf | - | 0.510 | +10.481 | 1.0000 | 0/+0.000 | 4/+15.400 | grandfather |
| ema200_trend_reversal | USD_JPY | Off | pending | pending | 3 | 33.3% | +4.267 | 4.20 | 0.254 | 0.061 | -8.118 | 1.0000 | 0/+0.000 | 3/+4.267 | grandfather |
| ema_cross | EUR_JPY | NY-overlap | pending | pending | 1 | 0.0% | -9.200 | 0.00 | - | 0.000 | -9.200 | 1.0000 | 0/+0.000 | 1/-9.200 | grandfather |
| ema_cross | EUR_JPY | Off | pending | pending | 1 | 0.0% | -10.400 | 0.00 | - | 0.000 | -10.400 | 1.0000 | 0/+0.000 | 1/-10.400 | grandfather |
| ema_cross | GBP_JPY | London | pending | pending | 1 | 0.0% | -14.800 | 0.00 | - | 0.000 | -14.800 | 1.0000 | 0/+0.000 | 1/-14.800 | grandfather |
| ema_cross | GBP_JPY | NY-overlap | pending | pending | 2 | 0.0% | -11.800 | 0.00 | - | 0.000 | -26.304 | 1.0000 | 0/+0.000 | 2/-11.800 | grandfather |
| ema_cross | GBP_USD | London | pending | pending | 1 | 100.0% | +16.500 | inf | - | 0.207 | +16.500 | 1.0000 | 0/+0.000 | 1/+16.500 | grandfather |
| ema_cross | USD_JPY | Asia | pending | pending | 6 | 83.3% | +9.333 | 9.75 | 0.748 | 0.436 | +1.466 | 1.0000 | 0/+0.000 | 6/+9.333 | grandfather |
| ema_cross | USD_JPY | London | pending | pending | 12 | 16.7% | -4.617 | 0.36 | -0.291 | 0.047 | -10.375 | 1.0000 | 0/+0.000 | 12/-4.617 | grandfather |
| ema_cross | USD_JPY | NY-overlap | pending | pending | 5 | 100.0% | +16.400 | inf | - | 0.566 | +12.405 | 1.0000 | 0/+0.000 | 5/+16.400 | grandfather |
| ema_cross | USD_JPY | Off | pending | pending | 6 | 50.0% | -0.833 | 0.61 | -0.321 | 0.188 | -4.028 | 1.0000 | 0/+0.000 | 6/-0.833 | grandfather |
| ema_pullback | EUR_USD | London | pending | pending | 3 | 0.0% | -2.200 | 0.00 | - | 0.000 | -3.016 | 1.0000 | 0/+0.000 | 3/-2.200 | grandfather |
| ema_pullback | EUR_USD | NY-overlap | pending | pending | 2 | 100.0% | +5.650 | inf | - | 0.342 | +5.160 | 1.0000 | 0/+0.000 | 2/+5.650 | grandfather |
| ema_pullback | GBP_USD | Asia | pending | pending | 1 | 0.0% | -5.200 | 0.00 | - | 0.000 | -5.200 | 1.0000 | 0/+0.000 | 1/-5.200 | grandfather |
| ema_pullback | USD_JPY | London | pending | pending | 7 | 14.3% | -2.614 | 0.23 | -0.475 | 0.026 | -5.342 | 1.0000 | 0/+0.000 | 7/-2.614 | grandfather |
| ema_pullback | USD_JPY | NY-overlap | pending | pending | 3 | 66.7% | +4.400 | 4.00 | 0.500 | 0.208 | -4.868 | 1.0000 | 0/+0.000 | 3/+4.400 | grandfather |
| ema_pullback | USD_JPY | Off | pending | pending | 4 | 50.0% | +1.225 | 1.63 | 0.193 | 0.150 | -4.662 | 1.0000 | 0/+0.000 | 4/+1.225 | grandfather |
| ema_ribbon_ride | EUR_USD | Asia | pending | pending | 2 | 0.0% | -1.900 | 0.00 | - | 0.000 | -3.664 | 1.0000 | 0/+0.000 | 2/-1.900 | grandfather |
| ema_ribbon_ride | EUR_USD | London | pending | pending | 2 | 50.0% | -0.200 | 0.89 | -0.059 | 0.095 | -7.256 | 1.0000 | 0/+0.000 | 2/-0.200 | grandfather |
| ema_ribbon_ride | USD_JPY | London | pending | pending | 2 | 50.0% | +1.400 | 1.93 | 0.241 | 0.095 | -7.224 | 1.0000 | 0/+0.000 | 2/+1.400 | grandfather |
| ema_trend_scalp | EUR_USD | London | pending | pending | 139 | 25.2% | -0.857 | 0.66 | -0.132 | 0.187 | -1.604 | 0.0000 | 0/+0.000 | 139/-0.857 | grandfather |
| ema_trend_scalp | EUR_USD | NY-overlap | pending | pending | 120 | 21.7% | -1.669 | 0.45 | -0.267 | 0.152 | -2.472 | 0.0000 | 0/+0.000 | 120/-1.669 | grandfather |
| ema_trend_scalp | GBP_USD | Asia | pending | pending | 29 | 17.2% | -2.272 | 0.39 | -0.270 | 0.076 | -4.137 | 0.0904 | 0/+0.000 | 29/-2.272 | grandfather |
| ema_trend_scalp | GBP_USD | London | pending | pending | 71 | 21.1% | -1.613 | 0.54 | -0.181 | 0.132 | -2.951 | 0.0002 | 0/+0.000 | 71/-1.613 | grandfather |
| ema_trend_scalp | GBP_USD | NY-overlap | pending | pending | 38 | 13.2% | -3.447 | 0.34 | -0.257 | 0.058 | -5.677 | 0.0012 | 0/+0.000 | 38/-3.447 | grandfather |
| ema_trend_scalp | GBP_USD | Off | pending | pending | 19 | 36.8% | +0.274 | 1.09 | 0.031 | 0.191 | -3.150 | 1.0000 | 0/+0.000 | 19/+0.274 | grandfather |
| ema_trend_scalp | USD_JPY | Asia | pending | pending | 80 | 23.8% | -1.255 | 0.56 | -0.188 | 0.158 | -2.278 | 0.0006 | 0/+0.000 | 80/-1.255 | grandfather |
| ema_trend_scalp | USD_JPY | London | pending | pending | 97 | 33.0% | +0.135 | 1.05 | 0.017 | 0.244 | -1.032 | 0.1741 | 0/+0.000 | 97/+0.135 | grandfather |
| ema_trend_scalp | USD_JPY | NY-overlap | pending | pending | 122 | 18.9% | -1.689 | 0.53 | -0.167 | 0.129 | -2.853 | 0.0000 | 0/+0.000 | 122/-1.689 | grandfather |
| ema_trend_scalp | USD_JPY | Off | pending | pending | 55 | 20.0% | -1.964 | 0.45 | -0.242 | 0.116 | -3.457 | 0.0019 | 0/+0.000 | 55/-1.964 | grandfather |
| engulfing_bb | EUR_USD | London | pending | pending | 31 | 22.6% | -0.874 | 0.68 | -0.108 | 0.114 | -2.696 | 0.4889 | 0/+0.000 | 31/-0.874 | grandfather |
| engulfing_bb | EUR_USD | NY-overlap | pending | pending | 13 | 30.8% | -0.492 | 0.80 | -0.077 | 0.127 | -3.247 | 1.0000 | 0/+0.000 | 13/-0.492 | grandfather |
| engulfing_bb | GBP_USD | Asia | pending | pending | 5 | 40.0% | -1.780 | 0.41 | -0.565 | 0.118 | -5.807 | 1.0000 | 0/+0.000 | 5/-1.780 | grandfather |
| engulfing_bb | GBP_USD | London | pending | pending | 9 | 22.2% | -1.822 | 0.56 | -0.172 | 0.063 | -6.461 | 1.0000 | 0/+0.000 | 9/-1.822 | grandfather |
| engulfing_bb | GBP_USD | NY-overlap | pending | pending | 6 | 16.7% | -3.333 | 0.34 | -0.330 | 0.030 | -8.631 | 1.0000 | 0/+0.000 | 6/-3.333 | grandfather |
| engulfing_bb | GBP_USD | Off | pending | pending | 3 | 66.7% | +6.967 | 3.49 | 0.476 | 0.208 | -8.948 | 1.0000 | 0/+0.000 | 3/+6.967 | grandfather |
| engulfing_bb | USD_JPY | Asia | pending | pending | 39 | 30.8% | -0.969 | 0.65 | -0.168 | 0.186 | -2.477 | 1.0000 | 0/+0.000 | 39/-0.969 | grandfather |
| engulfing_bb | USD_JPY | London | pending | pending | 37 | 21.6% | -2.332 | 0.38 | -0.351 | 0.114 | -4.476 | 0.1200 | 0/+0.000 | 37/-2.332 | grandfather |
| engulfing_bb | USD_JPY | NY-overlap | pending | pending | 32 | 18.8% | -2.403 | 0.30 | -0.438 | 0.089 | -3.854 | 0.0879 | 0/+0.000 | 32/-2.403 | grandfather |
| engulfing_bb | USD_JPY | Off | pending | pending | 23 | 39.1% | +0.200 | 1.09 | 0.031 | 0.222 | -2.250 | 1.0000 | 0/+0.000 | 23/+0.200 | grandfather |
| eurgbp_daily_mr | EUR_GBP | NY-overlap | pending | pending | 1 | 0.0% | -3.500 | 0.00 | - | 0.000 | -3.500 | 1.0000 | 0/+0.000 | 1/-3.500 | insufficient_data |
| fib_reversal | EUR_JPY | NY-overlap | pending | pending | 1 | 0.0% | -4.400 | 0.00 | - | 0.000 | -4.400 | 1.0000 | 0/+0.000 | 1/-4.400 | grandfather |
| fib_reversal | EUR_USD | Asia | pending | pending | 5 | 0.0% | -1.780 | 0.00 | - | 0.000 | -2.706 | 1.0000 | 0/+0.000 | 5/-1.780 | grandfather |
| fib_reversal | EUR_USD | London | pending | pending | 33 | 30.3% | -0.994 | 0.57 | -0.232 | 0.174 | -2.407 | 1.0000 | 0/+0.000 | 33/-0.994 | grandfather |
| fib_reversal | EUR_USD | NY-overlap | pending | pending | 14 | 50.0% | +0.371 | 1.15 | 0.064 | 0.268 | -2.685 | 1.0000 | 0/+0.000 | 14/+0.371 | grandfather |
| fib_reversal | EUR_USD | Off | pending | pending | 1 | 0.0% | -2.500 | 0.00 | - | 0.000 | -2.500 | 1.0000 | 0/+0.000 | 1/-2.500 | grandfather |
| fib_reversal | GBP_USD | London | pending | pending | 3 | 33.3% | +1.633 | 1.74 | 0.142 | 0.061 | -8.474 | 1.0000 | 0/+0.000 | 3/+1.633 | grandfather |
| fib_reversal | GBP_USD | NY-overlap | pending | pending | 4 | 25.0% | -3.700 | 0.33 | -0.514 | 0.046 | -11.683 | 1.0000 | 0/+0.000 | 4/-3.700 | grandfather |
| fib_reversal | GBP_USD | Off | pending | pending | 1 | 100.0% | +7.900 | inf | - | 0.207 | +7.900 | 1.0000 | 0/+0.000 | 1/+7.900 | grandfather |
| fib_reversal | USD_JPY | Asia | pending | pending | 36 | 25.0% | -0.578 | 0.76 | -0.078 | 0.138 | -2.271 | 0.5832 | 0/+0.000 | 36/-0.578 | grandfather |
| fib_reversal | USD_JPY | London | pending | pending | 38 | 36.8% | -0.924 | 0.67 | -0.180 | 0.234 | -2.489 | 1.0000 | 0/+0.000 | 38/-0.924 | grandfather |
| fib_reversal | USD_JPY | NY-overlap | pending | pending | 30 | 36.7% | -0.757 | 0.70 | -0.154 | 0.219 | -2.471 | 1.0000 | 0/+0.000 | 30/-0.757 | grandfather |
| fib_reversal | USD_JPY | Off | pending | pending | 26 | 34.6% | -0.165 | 0.93 | -0.027 | 0.194 | -2.192 | 1.0000 | 0/+0.000 | 26/-0.165 | grandfather |
| gbp_deep_pullback | GBP_USD | London | pending | pending | 1 | 0.0% | -20.000 | 0.00 | - | 0.000 | -20.000 | 1.0000 | 0/+0.000 | 1/-20.000 | grandfather |
| h1_fib_reversal | USD_JPY | London | pending | pending | 5 | 20.0% | -4.180 | 0.13 | -1.393 | 0.036 | -8.583 | 1.0000 | 0/+0.000 | 5/-4.180 | insufficient_data |
| htf_false_breakout | EUR_JPY | London | pending | pending | 5 | 0.0% | -20.640 | 0.00 | - | 0.000 | -20.893 | 1.0000 | 0/+0.000 | 5/-20.640 | grandfather |
| htf_false_breakout | GBP_JPY | London | pending | pending | 1 | 0.0% | -23.500 | 0.00 | - | 0.000 | -23.500 | 1.0000 | 0/+0.000 | 1/-23.500 | grandfather |
| htf_false_breakout | GBP_USD | London | pending | pending | 1 | 100.0% | +2.300 | inf | - | 0.207 | +2.300 | 1.0000 | 0/+0.000 | 1/+2.300 | grandfather |
| htf_false_breakout | USD_JPY | Asia | pending | pending | 1 | 0.0% | -7.100 | 0.00 | - | 0.000 | -7.100 | 1.0000 | 0/+0.000 | 1/-7.100 | grandfather |
| inducement_ob | GBP_USD | Asia | pending | pending | 3 | 0.0% | -6.233 | 0.00 | - | 0.000 | -9.484 | 1.0000 | 0/+0.000 | 3/-6.233 | grandfather |
| inducement_ob | USD_JPY | London | pending | pending | 1 | 0.0% | -7.400 | 0.00 | - | 0.000 | -7.400 | 1.0000 | 0/+0.000 | 1/-7.400 | grandfather |
| intraday_seasonality | GBP_USD | Asia | pending | pending | 7 | 42.9% | +2.729 | 1.68 | 0.174 | 0.158 | -6.360 | 1.0000 | 0/+0.000 | 7/+2.729 | insufficient_data |
| intraday_seasonality | GBP_USD | NY-overlap | pending | pending | 1 | 0.0% | -5.600 | 0.00 | - | 0.000 | -5.600 | 1.0000 | 0/+0.000 | 1/-5.600 | insufficient_data |
| intraday_seasonality | GBP_USD | Off | pending | pending | 2 | 0.0% | -6.750 | 0.00 | - | 0.000 | -15.864 | 1.0000 | 0/+0.000 | 2/-6.750 | insufficient_data |
| lin_reg_channel | EUR_USD | Asia | pending | pending | 1 | 0.0% | -20.900 | 0.00 | - | 0.000 | -20.900 | 1.0000 | 0/+0.000 | 1/-20.900 | grandfather |
| lin_reg_channel | EUR_USD | London | pending | pending | 1 | 0.0% | -6.600 | 0.00 | - | 0.000 | -6.600 | 1.0000 | 0/+0.000 | 1/-6.600 | grandfather |
| lin_reg_channel | EUR_USD | NY-overlap | pending | pending | 1 | 0.0% | -7.200 | 0.00 | - | 0.000 | -7.200 | 1.0000 | 0/+0.000 | 1/-7.200 | grandfather |
| liquidity_sweep | USD_JPY | London | pending | pending | 1 | 0.0% | -7.600 | 0.00 | - | 0.000 | -7.600 | 1.0000 | 0/+0.000 | 1/-7.600 | insufficient_data |
| london_fix_reversal | EUR_USD | NY-overlap | pending | pending | 2 | 0.0% | -3.250 | 0.00 | - | 0.000 | -4.132 | 1.0000 | 0/+0.000 | 2/-3.250 | insufficient_data |
| london_fix_reversal | GBP_USD | NY-overlap | pending | pending | 3 | 0.0% | -8.033 | 0.00 | - | 0.000 | -14.163 | 1.0000 | 0/+0.000 | 3/-8.033 | insufficient_data |
| london_fix_reversal | GBP_USD | Off | pending | pending | 1 | 0.0% | -10.300 | 0.00 | - | 0.000 | -10.300 | 1.0000 | 0/+0.000 | 1/-10.300 | insufficient_data |
| macdh_reversal | EUR_USD | Asia | pending | pending | 6 | 16.7% | -0.983 | 0.09 | -1.639 | 0.030 | -1.858 | 1.0000 | 0/+0.000 | 6/-0.983 | grandfather |
| macdh_reversal | EUR_USD | London | pending | pending | 12 | 25.0% | -1.908 | 0.16 | -1.331 | 0.089 | -3.414 | 1.0000 | 0/+0.000 | 12/-1.908 | grandfather |
| macdh_reversal | EUR_USD | NY-overlap | pending | pending | 5 | 40.0% | +1.120 | 1.48 | 0.130 | 0.118 | -5.150 | 1.0000 | 0/+0.000 | 5/+1.120 | grandfather |
| macdh_reversal | GBP_USD | London | pending | pending | 4 | 25.0% | -1.550 | 0.57 | -0.187 | 0.046 | -7.986 | 1.0000 | 0/+0.000 | 4/-1.550 | grandfather |
| macdh_reversal | GBP_USD | NY-overlap | pending | pending | 2 | 50.0% | +2.900 | 2.18 | 0.271 | 0.095 | -12.388 | 1.0000 | 0/+0.000 | 2/+2.900 | grandfather |
| macdh_reversal | USD_JPY | Asia | pending | pending | 14 | 14.3% | -1.593 | 0.28 | -0.366 | 0.040 | -3.208 | 1.0000 | 0/+0.000 | 14/-1.593 | grandfather |
| macdh_reversal | USD_JPY | London | pending | pending | 11 | 36.4% | -0.418 | 0.83 | -0.074 | 0.152 | -3.422 | 1.0000 | 0/+0.000 | 11/-0.418 | grandfather |
| macdh_reversal | USD_JPY | NY-overlap | pending | pending | 15 | 26.7% | -3.900 | 0.25 | -0.812 | 0.109 | -7.167 | 1.0000 | 0/+0.000 | 15/-3.900 | grandfather |
| macdh_reversal | USD_JPY | Off | pending | pending | 7 | 0.0% | -3.614 | 0.00 | - | 0.000 | -4.012 | 1.0000 | 0/+0.000 | 7/-3.614 | grandfather |
| mqe_gbpusd_fix | GBP_USD | NY-overlap | pending | demoted | 87 | 47.1% | +1.808 | 1.30 | 0.110 | 0.370 | -1.120 | 1.0000 | 0/+0.000 | 87/+1.808 | bucket_fail_demote_from_shadow |
| mtf_reversal_confluence | EUR_USD | London | pending | pending | 1 | 0.0% | -6.300 | 0.00 | - | 0.000 | -6.300 | 1.0000 | 0/+0.000 | 1/-6.300 | grandfather |
| mtf_trend_follow_scalp | USD_JPY | London | pending | pending | 1 | 0.0% | -3.200 | 0.00 | - | 0.000 | -3.200 | 1.0000 | 0/+0.000 | 1/-3.200 | insufficient_data |
| mtf_trend_follow_scalp | USD_JPY | NY-overlap | pending | pending | 2 | 0.0% | -8.150 | 0.00 | - | 0.000 | -8.248 | 1.0000 | 0/+0.000 | 2/-8.150 | insufficient_data |
| ny_close_reversal | GBP_USD | Off | pending | pending | 1 | 0.0% | -24.600 | 0.00 | - | 0.000 | -24.600 | 1.0000 | 0/+0.000 | 1/-24.600 | insufficient_data |
| ny_close_reversal | USD_JPY | Off | pending | pending | 4 | 25.0% | +2.150 | 4.58 | 0.195 | 0.046 | -3.632 | 1.0000 | 0/+0.000 | 4/+2.150 | insufficient_data |
| orb_trap | EUR_USD | London | pending | pending | 1 | 0.0% | -7.100 | 0.00 | - | 0.000 | -7.100 | 1.0000 | 0/+0.000 | 1/-7.100 | grandfather |
| orb_trap | EUR_USD | NY-overlap | pending | pending | 1 | 0.0% | -10.600 | 0.00 | - | 0.000 | -10.600 | 1.0000 | 0/+0.000 | 1/-10.600 | grandfather |
| orb_trap | GBP_USD | London | pending | pending | 1 | 0.0% | -5.000 | 0.00 | - | 0.000 | -5.000 | 1.0000 | 0/+0.000 | 1/-5.000 | grandfather |
| orb_trap | USD_JPY | NY-overlap | pending | pending | 2 | 50.0% | -2.050 | 0.80 | -0.127 | 0.095 | -37.623 | 1.0000 | 0/+0.000 | 2/-2.050 | grandfather |
| pivot_breakout | USD_JPY | NY-overlap | pending | pending | 4 | 50.0% | -5.725 | 0.51 | -0.485 | 0.150 | -28.243 | 1.0000 | 0/+0.000 | 4/-5.725 | grandfather |
| post_news_vol | EUR_USD | London | pending | pending | 7 | 14.3% | -4.871 | 0.32 | -0.297 | 0.026 | -13.151 | 1.0000 | 0/+0.000 | 7/-4.871 | grandfather |
| post_news_vol | EUR_USD | NY-overlap | pending | pending | 1 | 100.0% | +19.300 | inf | - | 0.207 | +19.300 | 1.0000 | 0/+0.000 | 1/+19.300 | grandfather |
| post_news_vol | GBP_USD | Asia | pending | pending | 2 | 0.0% | -20.050 | 0.00 | - | 0.000 | -20.148 | 1.0000 | 0/+0.000 | 2/-20.050 | grandfather |
| post_news_vol | GBP_USD | London | pending | pending | 2 | 50.0% | +5.750 | 1.65 | 0.196 | 0.095 | -40.407 | 1.0000 | 0/+0.000 | 2/+5.750 | grandfather |
| post_news_vol | GBP_USD | NY-overlap | pending | pending | 2 | 0.0% | -15.800 | 0.00 | - | 0.000 | -28.932 | 1.0000 | 0/+0.000 | 2/-15.800 | grandfather |
| post_news_vol | USD_JPY | Asia | pending | pending | 3 | 0.0% | -9.667 | 0.00 | - | 0.000 | -20.828 | 1.0000 | 0/+0.000 | 3/-9.667 | grandfather |
| post_news_vol | USD_JPY | London | pending | pending | 6 | 66.7% | +70.417 | 20.93 | 0.635 | 0.300 | +3.708 | 1.0000 | 0/+0.000 | 6/+70.417 | grandfather |
| post_news_vol | USD_JPY | Off | pending | pending | 5 | 0.0% | -16.020 | 0.00 | - | 0.000 | -22.912 | 1.0000 | 0/+0.000 | 5/-16.020 | grandfather |
| rsk_gbpjpy_reversion | GBP_JPY | London | pending | pending | 12 | 0.0% | -24.442 | 0.00 | - | 0.000 | -25.207 | 0.1149 | 0/+0.000 | 12/-24.442 | insufficient_data |
| rsk_gbpjpy_reversion | GBP_JPY | Off | pending | demoted | 64 | 0.0% | -8.131 | 0.00 | - | 0.000 | -9.756 | 0.0000 | 0/+0.000 | 64/-8.131 | bucket_fail_demote_from_shadow |
| session_time_bias | EUR_USD | London | pending | pending | 7 | 42.9% | +2.943 | 2.02 | 0.217 | 0.158 | -5.811 | 1.0000 | 0/+0.000 | 7/+2.943 | grandfather |
| session_time_bias | EUR_USD | NY-overlap | pending | pending | 3 | 33.3% | -5.267 | 0.16 | -1.756 | 0.061 | -13.371 | 1.0000 | 0/+0.000 | 3/-5.267 | grandfather |
| session_time_bias | GBP_USD | London | pending | pending | 2 | 50.0% | +2.650 | 1.68 | 0.202 | 0.095 | -17.832 | 1.0000 | 0/+0.000 | 2/+2.650 | grandfather |
| session_time_bias | GBP_USD | NY-overlap | pending | pending | 4 | 50.0% | +2.500 | 1.52 | 0.172 | 0.150 | -11.179 | 1.0000 | 0/+0.000 | 4/+2.500 | grandfather |
| session_time_bias | GBP_USD | Off | pending | pending | 8 | 12.5% | -6.850 | 0.29 | -0.302 | 0.022 | -15.785 | 1.0000 | 0/+0.000 | 8/-6.850 | grandfather |
| squeeze_release_momentum | GBP_USD | Asia | pending | pending | 5 | 40.0% | -1.480 | 0.74 | -0.138 | 0.118 | -12.770 | 1.0000 | 0/+0.000 | 5/-1.480 | grandfather |
| squeeze_release_momentum | GBP_USD | Off | pending | pending | 2 | 0.0% | -6.200 | 0.00 | - | 0.000 | -15.804 | 1.0000 | 0/+0.000 | 2/-6.200 | grandfather |
| sr_anti_hunt_bounce | EUR_JPY | Asia | pending | pending | 3 | 0.0% | -14.833 | 0.00 | - | 0.000 | -24.345 | 1.0000 | 0/+0.000 | 3/-14.833 | insufficient_data |
| sr_anti_hunt_bounce | EUR_JPY | NY-overlap | pending | pending | 1 | 0.0% | -20.500 | 0.00 | - | 0.000 | -20.500 | 1.0000 | 0/+0.000 | 1/-20.500 | insufficient_data |
| sr_anti_hunt_bounce | GBP_JPY | Asia | pending | pending | 2 | 0.0% | -19.650 | 0.00 | - | 0.000 | -23.472 | 1.0000 | 0/+0.000 | 2/-19.650 | insufficient_data |
| sr_anti_hunt_bounce | GBP_JPY | Off | pending | pending | 1 | 0.0% | -24.600 | 0.00 | - | 0.000 | -24.600 | 1.0000 | 0/+0.000 | 1/-24.600 | insufficient_data |
| sr_anti_hunt_bounce | USD_JPY | London | pending | pending | 22 | 0.0% | -16.964 | 0.00 | - | 0.000 | -17.177 | 0.0006 | 0/+0.000 | 22/-16.964 | insufficient_data |
| sr_break_retest | EUR_JPY | Asia | pending | pending | 5 | 0.0% | -8.700 | 0.00 | - | 0.000 | -12.122 | 1.0000 | 0/+0.000 | 5/-8.700 | grandfather |
| sr_break_retest | EUR_JPY | London | pending | pending | 3 | 0.0% | -10.533 | 0.00 | - | 0.000 | -10.860 | 1.0000 | 0/+0.000 | 3/-10.533 | grandfather |
| sr_break_retest | EUR_JPY | NY-overlap | pending | pending | 4 | 0.0% | -8.925 | 0.00 | - | 0.000 | -15.491 | 1.0000 | 0/+0.000 | 4/-8.925 | grandfather |
| sr_break_retest | EUR_JPY | Off | pending | pending | 2 | 0.0% | -1.650 | 0.00 | - | 0.000 | -3.512 | 1.0000 | 0/+0.000 | 2/-1.650 | grandfather |
| sr_break_retest | GBP_JPY | London | pending | pending | 2 | 0.0% | -11.300 | 0.00 | - | 0.000 | -19.728 | 1.0000 | 0/+0.000 | 2/-11.300 | grandfather |
| sr_break_retest | GBP_JPY | NY-overlap | pending | pending | 2 | 0.0% | -15.550 | 0.00 | - | 0.000 | -15.648 | 1.0000 | 0/+0.000 | 2/-15.550 | grandfather |
| sr_break_retest | GBP_JPY | Off | pending | pending | 3 | 0.0% | -23.100 | 0.00 | - | 0.000 | -29.176 | 1.0000 | 0/+0.000 | 3/-23.100 | grandfather |
| sr_break_retest | GBP_USD | Asia | pending | pending | 2 | 50.0% | +5.550 | 4.17 | 0.380 | 0.095 | -12.188 | 1.0000 | 0/+0.000 | 2/+5.550 | grandfather |
| sr_break_retest | GBP_USD | London | pending | pending | 1 | 100.0% | +1.400 | inf | - | 0.207 | +1.400 | 1.0000 | 0/+0.000 | 1/+1.400 | grandfather |
| sr_break_retest | GBP_USD | NY-overlap | pending | pending | 1 | 100.0% | +19.400 | inf | - | 0.207 | +19.400 | 1.0000 | 0/+0.000 | 1/+19.400 | grandfather |
| sr_break_retest | GBP_USD | Off | pending | pending | 2 | 50.0% | -0.200 | 0.91 | -0.047 | 0.095 | -9.020 | 1.0000 | 0/+0.000 | 2/-0.200 | grandfather |
| sr_break_retest | USD_JPY | Asia | pending | pending | 12 | 33.3% | -1.692 | 0.70 | -0.143 | 0.138 | -8.385 | 1.0000 | 0/+0.000 | 12/-1.692 | grandfather |
| sr_break_retest | USD_JPY | London | pending | pending | 8 | 12.5% | -5.425 | 0.32 | -0.267 | 0.022 | -14.173 | 1.0000 | 0/+0.000 | 8/-5.425 | grandfather |
| sr_break_retest | USD_JPY | NY-overlap | pending | pending | 1 | 100.0% | +19.800 | inf | - | 0.207 | +19.800 | 1.0000 | 0/+0.000 | 1/+19.800 | grandfather |
| sr_break_retest | USD_JPY | Off | pending | pending | 3 | 66.7% | +0.967 | 2.21 | 0.365 | 0.208 | -2.356 | 1.0000 | 0/+0.000 | 3/+0.967 | grandfather |
| sr_channel_reversal | EUR_USD | London | pending | pending | 21 | 14.3% | -2.819 | 0.28 | -0.376 | 0.050 | -4.791 | 0.2296 | 0/+0.000 | 21/-2.819 | grandfather |
| sr_channel_reversal | EUR_USD | NY-overlap | pending | pending | 25 | 32.0% | -0.460 | 0.82 | -0.070 | 0.172 | -2.496 | 1.0000 | 0/+0.000 | 25/-0.460 | grandfather |
| sr_channel_reversal | GBP_USD | Asia | pending | pending | 1 | 0.0% | -0.600 | 0.00 | - | 0.000 | -0.600 | 1.0000 | 0/+0.000 | 1/-0.600 | grandfather |
| sr_channel_reversal | GBP_USD | London | pending | pending | 14 | 7.1% | -3.907 | 0.16 | -0.365 | 0.013 | -6.229 | 0.2896 | 0/+0.000 | 14/-3.907 | grandfather |
| sr_channel_reversal | GBP_USD | NY-overlap | pending | pending | 15 | 40.0% | +0.607 | 1.17 | 0.057 | 0.198 | -3.753 | 1.0000 | 0/+0.000 | 15/+0.607 | grandfather |
| sr_channel_reversal | GBP_USD | Off | pending | pending | 6 | 66.7% | +8.400 | 6.36 | 0.562 | 0.300 | -0.145 | 1.0000 | 0/+0.000 | 6/+8.400 | grandfather |
| sr_channel_reversal | USD_JPY | Asia | pending | pending | 67 | 22.4% | -1.430 | 0.44 | -0.290 | 0.141 | -2.341 | 0.0013 | 0/+0.000 | 67/-1.430 | grandfather |
| sr_channel_reversal | USD_JPY | London | pending | pending | 59 | 27.1% | -1.053 | 0.59 | -0.189 | 0.174 | -2.187 | 0.0950 | 0/+0.000 | 59/-1.053 | grandfather |
| sr_channel_reversal | USD_JPY | NY-overlap | pending | pending | 40 | 20.0% | -1.840 | 0.43 | -0.265 | 0.105 | -3.314 | 0.0319 | 0/+0.000 | 40/-1.840 | grandfather |
| sr_channel_reversal | USD_JPY | Off | pending | pending | 44 | 29.5% | -0.634 | 0.74 | -0.101 | 0.182 | -2.163 | 1.0000 | 0/+0.000 | 44/-0.634 | grandfather |
| sr_fib_confluence | EUR_GBP | London | pending | pending | 1 | 0.0% | -5.100 | 0.00 | - | 0.000 | -5.100 | 1.0000 | 0/+0.000 | 1/-5.100 | grandfather |
| sr_fib_confluence | EUR_JPY | Asia | pending | pending | 11 | 18.2% | -7.736 | 0.28 | -0.479 | 0.051 | -14.987 | 1.0000 | 0/+0.000 | 11/-7.736 | grandfather |
| sr_fib_confluence | EUR_JPY | London | pending | pending | 13 | 0.0% | -12.908 | 0.00 | - | 0.000 | -15.695 | 0.0673 | 0/+0.000 | 13/-12.908 | grandfather |
| sr_fib_confluence | EUR_JPY | NY-overlap | pending | pending | 7 | 14.3% | -3.957 | 0.30 | -0.330 | 0.026 | -10.135 | 1.0000 | 0/+0.000 | 7/-3.957 | grandfather |
| sr_fib_confluence | EUR_JPY | Off | pending | pending | 2 | 0.0% | -10.100 | 0.00 | - | 0.000 | -24.212 | 1.0000 | 0/+0.000 | 2/-10.100 | grandfather |
| sr_fib_confluence | EUR_USD | London | pending | pending | 22 | 36.4% | +0.882 | 1.22 | 0.066 | 0.197 | -3.532 | 1.0000 | 0/+0.000 | 22/+0.882 | grandfather |
| sr_fib_confluence | EUR_USD | NY-overlap | pending | pending | 13 | 23.1% | -3.192 | 0.52 | -0.212 | 0.082 | -9.818 | 1.0000 | 0/+0.000 | 13/-3.192 | grandfather |
| sr_fib_confluence | GBP_JPY | Asia | pending | pending | 5 | 20.0% | -2.120 | 0.79 | -0.054 | 0.036 | -23.030 | 1.0000 | 0/+0.000 | 5/-2.120 | grandfather |
| sr_fib_confluence | GBP_JPY | London | pending | pending | 2 | 0.0% | -11.650 | 0.00 | - | 0.000 | -26.448 | 1.0000 | 0/+0.000 | 2/-11.650 | grandfather |
| sr_fib_confluence | GBP_JPY | NY-overlap | pending | pending | 4 | 50.0% | +15.050 | 10.56 | 0.453 | 0.150 | -5.638 | 1.0000 | 0/+0.000 | 4/+15.050 | grandfather |
| sr_fib_confluence | GBP_JPY | Off | pending | pending | 3 | 100.0% | +42.100 | inf | - | 0.439 | +35.760 | 1.0000 | 0/+0.000 | 3/+42.100 | grandfather |
| sr_fib_confluence | GBP_USD | Asia | pending | pending | 3 | 33.3% | -4.467 | 0.07 | -4.467 | 0.061 | -10.327 | 1.0000 | 0/+0.000 | 3/-4.467 | grandfather |
| sr_fib_confluence | GBP_USD | London | pending | pending | 23 | 39.1% | +1.374 | 1.31 | 0.091 | 0.222 | -3.778 | 1.0000 | 0/+0.000 | 23/+1.374 | grandfather |
| sr_fib_confluence | GBP_USD | NY-overlap | pending | pending | 12 | 58.3% | +6.208 | 2.24 | 0.323 | 0.320 | -4.499 | 1.0000 | 0/+0.000 | 12/+6.208 | grandfather |
| sr_fib_confluence | USD_JPY | Asia | pending | pending | 9 | 22.2% | -1.878 | 0.71 | -0.092 | 0.063 | -10.349 | 1.0000 | 0/+0.000 | 9/-1.878 | grandfather |
| sr_fib_confluence | USD_JPY | London | pending | pending | 7 | 0.0% | -11.914 | 0.00 | - | 0.000 | -17.184 | 1.0000 | 0/+0.000 | 7/-11.914 | grandfather |
| sr_fib_confluence | USD_JPY | NY-overlap | pending | pending | 8 | 12.5% | -7.250 | 0.21 | -0.465 | 0.022 | -15.299 | 1.0000 | 0/+0.000 | 8/-7.250 | grandfather |
| sr_fib_confluence | USD_JPY | Off | pending | pending | 7 | 71.4% | +11.600 | 4.50 | 0.556 | 0.359 | -2.313 | 1.0000 | 0/+0.000 | 7/+11.600 | grandfather |
| stoch_trend_pullback | EUR_USD | London | pending | pending | 19 | 26.3% | -0.832 | 0.65 | -0.140 | 0.118 | -2.732 | 1.0000 | 0/+0.000 | 19/-0.832 | grandfather |
| stoch_trend_pullback | EUR_USD | NY-overlap | pending | pending | 10 | 20.0% | -0.530 | 0.80 | -0.051 | 0.057 | -4.089 | 1.0000 | 0/+0.000 | 10/-0.530 | grandfather |
| stoch_trend_pullback | GBP_USD | Asia | pending | pending | 5 | 0.0% | -5.100 | 0.00 | - | 0.000 | -5.801 | 1.0000 | 0/+0.000 | 5/-5.100 | grandfather |
| stoch_trend_pullback | GBP_USD | London | pending | pending | 8 | 50.0% | +4.175 | 3.90 | 0.372 | 0.215 | -1.143 | 1.0000 | 0/+0.000 | 8/+4.175 | grandfather |
| stoch_trend_pullback | GBP_USD | NY-overlap | pending | pending | 8 | 12.5% | -3.500 | 0.26 | -0.357 | 0.022 | -7.791 | 1.0000 | 0/+0.000 | 8/-3.500 | grandfather |
| stoch_trend_pullback | GBP_USD | Off | pending | pending | 4 | 25.0% | -1.450 | 0.53 | -0.223 | 0.046 | -7.207 | 1.0000 | 0/+0.000 | 4/-1.450 | grandfather |
| stoch_trend_pullback | USD_JPY | Asia | pending | pending | 37 | 18.9% | -1.416 | 0.47 | -0.216 | 0.095 | -2.745 | 0.0337 | 0/+0.000 | 37/-1.416 | grandfather |
| stoch_trend_pullback | USD_JPY | London | pending | pending | 31 | 35.5% | +0.429 | 1.16 | 0.049 | 0.211 | -2.068 | 1.0000 | 0/+0.000 | 31/+0.429 | grandfather |
| stoch_trend_pullback | USD_JPY | NY-overlap | pending | pending | 33 | 6.1% | -4.242 | 0.07 | -0.771 | 0.017 | -5.500 | 0.0001 | 0/+0.000 | 33/-4.242 | grandfather |
| stoch_trend_pullback | USD_JPY | Off | pending | pending | 26 | 26.9% | -1.146 | 0.55 | -0.219 | 0.137 | -2.793 | 1.0000 | 0/+0.000 | 26/-1.146 | grandfather |
| streak_reversal | USD_JPY | Asia | pending | pending | 5 | 0.0% | -4.980 | 0.00 | - | 0.000 | -13.124 | 1.0000 | 0/+0.000 | 5/-4.980 | grandfather |
| streak_reversal | USD_JPY | NY-overlap | pending | pending | 2 | 0.0% | -5.650 | 0.00 | - | 0.000 | -13.980 | 1.0000 | 0/+0.000 | 2/-5.650 | grandfather |
| three_bar_reversal | USD_JPY | London | pending | pending | 1 | 0.0% | -3.400 | 0.00 | - | 0.000 | -3.400 | 1.0000 | 0/+0.000 | 1/-3.400 | grandfather |
| trend_rebound | EUR_USD | London | pending | pending | 4 | 25.0% | -1.350 | 0.50 | -0.255 | 0.046 | -5.707 | 1.0000 | 0/+0.000 | 4/-1.350 | grandfather |
| trend_rebound | EUR_USD | NY-overlap | pending | pending | 1 | 0.0% | -3.000 | 0.00 | - | 0.000 | -3.000 | 1.0000 | 0/+0.000 | 1/-3.000 | grandfather |
| trend_rebound | GBP_USD | Asia | pending | pending | 1 | 0.0% | -6.000 | 0.00 | - | 0.000 | -6.000 | 1.0000 | 0/+0.000 | 1/-6.000 | grandfather |
| trend_rebound | GBP_USD | London | pending | pending | 2 | 0.0% | -5.150 | 0.00 | - | 0.000 | -6.032 | 1.0000 | 0/+0.000 | 2/-5.150 | grandfather |
| trend_rebound | GBP_USD | NY-overlap | pending | pending | 3 | 66.7% | +4.500 | 2.42 | 0.391 | 0.208 | -10.256 | 1.0000 | 0/+0.000 | 3/+4.500 | grandfather |
| trend_rebound | USD_JPY | Asia | pending | pending | 11 | 36.4% | -0.064 | 0.96 | -0.014 | 0.152 | -2.340 | 1.0000 | 0/+0.000 | 11/-0.064 | grandfather |
| trend_rebound | USD_JPY | London | pending | pending | 10 | 30.0% | -0.920 | 0.70 | -0.129 | 0.108 | -4.896 | 1.0000 | 0/+0.000 | 10/-0.920 | grandfather |
| trend_rebound | USD_JPY | NY-overlap | pending | pending | 6 | 50.0% | +3.633 | 2.77 | 0.320 | 0.188 | -3.635 | 1.0000 | 0/+0.000 | 6/+3.633 | grandfather |
| trend_rebound | USD_JPY | Off | pending | pending | 6 | 16.7% | -0.483 | 0.87 | -0.026 | 0.030 | -8.118 | 1.0000 | 0/+0.000 | 6/-0.483 | grandfather |
| trendline_sweep | EUR_USD | London | pending | pending | 2 | 0.0% | -6.900 | 0.00 | - | 0.000 | -7.488 | 1.0000 | 0/+0.000 | 2/-6.900 | grandfather |
| trendline_sweep | EUR_USD | NY-overlap | pending | pending | 2 | 0.0% | -9.600 | 0.00 | - | 0.000 | -12.344 | 1.0000 | 0/+0.000 | 2/-9.600 | grandfather |
| trendline_sweep | GBP_USD | London | pending | pending | 6 | 33.3% | +6.333 | 2.54 | 0.202 | 0.097 | -9.671 | 1.0000 | 0/+0.000 | 6/+6.333 | grandfather |
| trendline_sweep | GBP_USD | NY-overlap | pending | pending | 1 | 0.0% | -8.900 | 0.00 | - | 0.000 | -8.900 | 1.0000 | 0/+0.000 | 1/-8.900 | grandfather |
| v_reversal | USD_JPY | Asia | pending | pending | 2 | 50.0% | +2.300 | 2.21 | 0.274 | 0.095 | -9.656 | 1.0000 | 0/+0.000 | 2/+2.300 | grandfather |
| v_reversal | USD_JPY | London | pending | pending | 9 | 22.2% | -2.178 | 0.40 | -0.332 | 0.063 | -5.711 | 1.0000 | 0/+0.000 | 9/-2.178 | grandfather |
| v_reversal | USD_JPY | NY-overlap | pending | pending | 6 | 16.7% | -3.183 | 0.23 | -0.568 | 0.030 | -7.419 | 1.0000 | 0/+0.000 | 6/-3.183 | grandfather |
| v_reversal | USD_JPY | Off | pending | pending | 1 | 100.0% | +7.000 | inf | - | 0.207 | +7.000 | 1.0000 | 0/+0.000 | 1/+7.000 | grandfather |
| vix_carry_unwind | USD_JPY | Asia | pending | pending | 4 | 0.0% | -21.250 | 0.00 | - | 0.000 | -23.105 | 1.0000 | 0/+0.000 | 4/-21.250 | grandfather |
| vix_carry_unwind | USD_JPY | London | pending | pending | 36 | 33.3% | +17.272 | 2.31 | 0.189 | 0.202 | -1.592 | 1.0000 | 0/+0.000 | 36/+17.272 | grandfather |
| vol_momentum_scalp | GBP_USD | Asia | pending | pending | 4 | 25.0% | -0.975 | 0.69 | -0.115 | 0.046 | -7.168 | 1.0000 | 0/+0.000 | 4/-0.975 | grandfather |
| vol_momentum_scalp | GBP_USD | London | pending | pending | 27 | 3.7% | -4.096 | 0.11 | -0.303 | 0.007 | -5.620 | 0.0003 | 0/+0.000 | 27/-4.096 | grandfather |
| vol_momentum_scalp | GBP_USD | NY-overlap | pending | pending | 7 | 14.3% | -1.757 | 0.66 | -0.075 | 0.026 | -10.031 | 1.0000 | 0/+0.000 | 7/-1.757 | grandfather |
| vol_momentum_scalp | GBP_USD | Off | pending | pending | 7 | 28.6% | -1.457 | 0.66 | -0.149 | 0.082 | -7.401 | 1.0000 | 0/+0.000 | 7/-1.457 | grandfather |
| vol_momentum_scalp | USD_JPY | Asia | pending | pending | 4 | 25.0% | +1.675 | 1.70 | 0.103 | 0.046 | -7.881 | 1.0000 | 0/+0.000 | 4/+1.675 | grandfather |
| vol_momentum_scalp | USD_JPY | London | pending | pending | 3 | 0.0% | -6.067 | 0.00 | - | 0.000 | -9.575 | 1.0000 | 0/+0.000 | 3/-6.067 | grandfather |
| vol_momentum_scalp | USD_JPY | NY-overlap | pending | pending | 4 | 50.0% | +2.000 | 2.33 | 0.286 | 0.150 | -3.801 | 1.0000 | 0/+0.000 | 4/+2.000 | grandfather |
| vol_spike_mr | USD_JPY | Asia | pending | pending | 6 | 33.3% | -0.800 | 0.87 | -0.048 | 0.097 | -11.746 | 1.0000 | 0/+0.000 | 6/-0.800 | insufficient_data |
| vol_spike_mr | USD_JPY | London | pending | pending | 7 | 14.3% | -5.943 | 0.22 | -0.508 | 0.026 | -12.160 | 1.0000 | 0/+0.000 | 7/-5.943 | insufficient_data |
| vol_surge_detector | EUR_USD | London | pending | pending | 16 | 31.2% | -0.031 | 0.99 | -0.004 | 0.142 | -3.362 | 1.0000 | 0/+0.000 | 16/-0.031 | grandfather |
| vol_surge_detector | EUR_USD | NY-overlap | pending | pending | 4 | 0.0% | -5.050 | 0.00 | - | 0.000 | -8.722 | 1.0000 | 0/+0.000 | 4/-5.050 | grandfather |
| vol_surge_detector | GBP_USD | Asia | pending | pending | 14 | 0.0% | -5.800 | 0.00 | - | 0.000 | -6.642 | 0.0395 | 0/+0.000 | 14/-5.800 | grandfather |
| vol_surge_detector | GBP_USD | London | pending | pending | 4 | 0.0% | -2.375 | 0.00 | - | 0.000 | -3.836 | 1.0000 | 0/+0.000 | 4/-2.375 | grandfather |
| vol_surge_detector | USD_JPY | Asia | pending | pending | 48 | 31.2% | -0.729 | 0.76 | -0.099 | 0.199 | -2.467 | 1.0000 | 0/+0.000 | 48/-0.729 | grandfather |
| vol_surge_detector | USD_JPY | London | pending | pending | 8 | 50.0% | +7.912 | 4.84 | 0.397 | 0.215 | -2.523 | 1.0000 | 0/+0.000 | 8/+7.912 | grandfather |
| vsg_jpy_reversal | EUR_JPY | Asia | pending | pending | 4 | 100.0% | +22.800 | inf | - | 0.510 | +22.800 | 1.0000 | 0/+0.000 | 4/+22.800 | insufficient_data |
| vsg_jpy_reversal | EUR_JPY | London | pending | pending | 5 | 0.0% | -17.720 | 0.00 | - | 0.000 | -19.142 | 1.0000 | 0/+0.000 | 5/-17.720 | insufficient_data |
| vsg_jpy_reversal | EUR_JPY | Off | pending | pending | 4 | 100.0% | +8.400 | inf | - | 0.510 | +8.400 | 1.0000 | 0/+0.000 | 4/+8.400 | insufficient_data |
| vsg_jpy_reversal | GBP_JPY | London | pending | pending | 3 | 0.0% | -24.833 | 0.00 | - | 0.000 | -25.095 | 1.0000 | 0/+0.000 | 3/-24.833 | insufficient_data |
| vsg_jpy_reversal | GBP_JPY | NY-overlap | pending | pending | 2 | 100.0% | +27.500 | inf | - | 0.342 | +27.500 | 1.0000 | 0/+0.000 | 2/+27.500 | insufficient_data |
| vwap_mean_reversion | EUR_JPY | Asia | pending | pending | 2 | 0.0% | -11.150 | 0.00 | - | 0.000 | -11.444 | 1.0000 | 0/+0.000 | 2/-11.150 | grandfather |
| vwap_mean_reversion | EUR_JPY | London | pending | pending | 5 | 0.0% | -11.100 | 0.00 | - | 0.000 | -17.913 | 1.0000 | 0/+0.000 | 5/-11.100 | grandfather |
| vwap_mean_reversion | EUR_JPY | NY-overlap | pending | pending | 1 | 0.0% | -20.000 | 0.00 | - | 0.000 | -20.000 | 1.0000 | 0/+0.000 | 1/-20.000 | grandfather |
| vwap_mean_reversion | EUR_USD | London | pending | pending | 5 | 20.0% | -2.900 | 0.34 | -0.382 | 0.036 | -8.376 | 1.0000 | 0/+0.000 | 5/-2.900 | grandfather |
| vwap_mean_reversion | EUR_USD | NY-overlap | pending | pending | 2 | 50.0% | +14.850 | 6.60 | 0.424 | 0.095 | -24.643 | 1.0000 | 0/+0.000 | 2/+14.850 | grandfather |
| vwap_mean_reversion | GBP_JPY | London | pending | pending | 4 | 50.0% | +10.150 | 2.43 | 0.294 | 0.150 | -17.911 | 1.0000 | 0/+0.000 | 4/+10.150 | grandfather |
| vwap_mean_reversion | GBP_JPY | NY-overlap | pending | pending | 2 | 50.0% | +5.100 | 1.51 | 0.169 | 0.095 | -44.095 | 1.0000 | 0/+0.000 | 2/+5.100 | grandfather |
| vwap_mean_reversion | GBP_JPY | Off | pending | pending | 1 | 100.0% | +0.600 | inf | - | 0.207 | +0.600 | 1.0000 | 0/+0.000 | 1/+0.600 | grandfather |
| vwap_mean_reversion | GBP_USD | Asia | pending | pending | 1 | 100.0% | +33.100 | inf | - | 0.207 | +33.100 | 1.0000 | 0/+0.000 | 1/+33.100 | grandfather |
| vwap_mean_reversion | GBP_USD | London | pending | pending | 1 | 0.0% | -20.100 | 0.00 | - | 0.000 | -20.100 | 1.0000 | 0/+0.000 | 1/-20.100 | grandfather |
| vwap_mean_reversion | GBP_USD | NY-overlap | pending | pending | 5 | 20.0% | -4.060 | 0.05 | -3.691 | 0.036 | -9.427 | 1.0000 | 0/+0.000 | 5/-4.060 | grandfather |
| vwap_mean_reversion | GBP_USD | Off | pending | pending | 1 | 100.0% | +8.500 | inf | - | 0.207 | +8.500 | 1.0000 | 0/+0.000 | 1/+8.500 | grandfather |
| vwap_mean_reversion | USD_JPY | Asia | pending | pending | 3 | 0.0% | -0.800 | 0.00 | - | 0.000 | -0.800 | 1.0000 | 0/+0.000 | 3/-0.800 | grandfather |
| wick_imbalance_reversion | EUR_JPY | Asia | pending | pending | 1 | 100.0% | +14.700 | inf | - | 0.207 | +14.700 | 1.0000 | 0/+0.000 | 1/+14.700 | insufficient_data |
| wick_imbalance_reversion | EUR_JPY | London | pending | pending | 4 | 0.0% | -21.475 | 0.00 | - | 0.000 | -24.521 | 1.0000 | 0/+0.000 | 4/-21.475 | insufficient_data |
| wick_imbalance_reversion | EUR_USD | London | pending | pending | 3 | 33.3% | -7.933 | 0.04 | -7.933 | 0.061 | -20.048 | 1.0000 | 0/+0.000 | 3/-7.933 | insufficient_data |
| wick_imbalance_reversion | EUR_USD | NY-overlap | pending | pending | 1 | 0.0% | -1.400 | 0.00 | - | 0.000 | -1.400 | 1.0000 | 0/+0.000 | 1/-1.400 | insufficient_data |
| wick_imbalance_reversion | GBP_JPY | Asia | pending | pending | 1 | 0.0% | -11.400 | 0.00 | - | 0.000 | -11.400 | 1.0000 | 0/+0.000 | 1/-11.400 | insufficient_data |
| wick_imbalance_reversion | GBP_JPY | London | pending | pending | 4 | 25.0% | +7.125 | 3.64 | 0.181 | 0.046 | -14.181 | 1.0000 | 0/+0.000 | 4/+7.125 | insufficient_data |
| wick_imbalance_reversion | GBP_JPY | NY-overlap | pending | pending | 4 | 0.0% | -11.525 | 0.00 | - | 0.000 | -19.821 | 1.0000 | 0/+0.000 | 4/-11.525 | insufficient_data |
| wick_imbalance_reversion | GBP_JPY | Off | pending | pending | 2 | 0.0% | -17.900 | 0.00 | - | 0.000 | -27.308 | 1.0000 | 0/+0.000 | 2/-17.900 | insufficient_data |
| wick_imbalance_reversion | GBP_USD | Asia | pending | pending | 3 | 33.3% | +2.900 | 2.24 | 0.185 | 0.061 | -9.846 | 1.0000 | 0/+0.000 | 3/+2.900 | insufficient_data |
| wick_imbalance_reversion | GBP_USD | London | pending | pending | 2 | 50.0% | -0.150 | 0.89 | -0.062 | 0.095 | -5.148 | 1.0000 | 0/+0.000 | 2/-0.150 | insufficient_data |
| wick_imbalance_reversion | GBP_USD | Off | pending | pending | 1 | 0.0% | -8.300 | 0.00 | - | 0.000 | -8.300 | 1.0000 | 0/+0.000 | 1/-8.300 | insufficient_data |
| wick_imbalance_reversion | USD_JPY | Asia | pending | pending | 1 | 100.0% | +12.200 | inf | - | 0.207 | +12.200 | 1.0000 | 0/+0.000 | 1/+12.200 | insufficient_data |
| wick_imbalance_reversion | USD_JPY | London | pending | pending | 2 | 100.0% | +8.500 | inf | - | 0.342 | +4.384 | 1.0000 | 0/+0.000 | 2/+8.500 | insufficient_data |
| wick_imbalance_reversion | USD_JPY | NY-overlap | pending | pending | 1 | 0.0% | -8.400 | 0.00 | - | 0.000 | -8.400 | 1.0000 | 0/+0.000 | 1/-8.400 | insufficient_data |
| xs_momentum | EUR_USD | London | pending | pending | 1 | 0.0% | -5.000 | 0.00 | - | 0.000 | -5.000 | 1.0000 | 0/+0.000 | 1/-5.000 | grandfather |
| xs_momentum | EUR_USD | NY-overlap | pending | pending | 10 | 30.0% | +0.480 | 1.13 | 0.035 | 0.108 | -6.332 | 1.0000 | 0/+0.000 | 10/+0.480 | grandfather |
| xs_momentum | GBP_USD | Asia | pending | pending | 2 | 0.0% | -10.650 | 0.00 | - | 0.000 | -12.904 | 1.0000 | 0/+0.000 | 2/-10.650 | grandfather |
| xs_momentum | GBP_USD | London | pending | pending | 8 | 0.0% | -8.012 | 0.00 | - | 0.000 | -8.543 | 1.0000 | 0/+0.000 | 8/-8.012 | grandfather |
| xs_momentum | GBP_USD | NY-overlap | pending | pending | 16 | 50.0% | +8.650 | 2.43 | 0.295 | 0.280 | -2.440 | 1.0000 | 0/+0.000 | 16/+8.650 | grandfather |
| xs_momentum | GBP_USD | Off | pending | pending | 1 | 100.0% | +28.700 | inf | - | 0.207 | +28.700 | 1.0000 | 0/+0.000 | 1/+28.700 | grandfather |
| xs_momentum | USD_JPY | Asia | pending | pending | 2 | 0.0% | -3.650 | 0.00 | - | 0.000 | -6.492 | 1.0000 | 0/+0.000 | 2/-3.650 | grandfather |
| xs_momentum | USD_JPY | NY-overlap | pending | pending | 9 | 44.4% | -1.067 | 0.82 | -0.095 | 0.189 | -9.389 | 1.0000 | 0/+0.000 | 9/-1.067 | grandfather |
| xs_momentum | USD_JPY | Off | pending | pending | 1 | 0.0% | -8.200 | 0.00 | - | 0.000 | -8.200 | 1.0000 | 0/+0.000 | 1/-8.200 | grandfather |

## Insufficient Data Cells

| scope | strategy | pair | bucket | N | WR | EV | note |
|---|---|---|---|---:|---:|---:|---|
| shadow | bb_rsi_reversion | EUR_USD | NY-overlap | 27 | 44.4% | -0.167 | insufficient data |
| shadow | bb_rsi_reversion | GBP_USD | Asia | 4 | 0.0% | -4.250 | insufficient data |
| shadow | bb_rsi_reversion | GBP_USD | London | 13 | 7.7% | -5.515 | insufficient data |
| shadow | bb_rsi_reversion | GBP_USD | NY-overlap | 17 | 11.8% | -4.953 | insufficient data |
| shadow | bb_rsi_reversion | GBP_USD | Off | 3 | 100.0% | +11.133 | insufficient data |
| shadow | bb_squeeze_breakout | EUR_USD | London | 19 | 5.3% | -2.679 | insufficient data |
| shadow | bb_squeeze_breakout | EUR_USD | NY-overlap | 16 | 12.5% | -0.894 | insufficient data |
| shadow | bb_squeeze_breakout | GBP_USD | Asia | 1 | 0.0% | -5.000 | insufficient data |
| shadow | bb_squeeze_breakout | GBP_USD | London | 2 | 50.0% | +5.800 | insufficient data |
| shadow | bb_squeeze_breakout | GBP_USD | NY-overlap | 2 | 0.0% | -4.700 | insufficient data |
| shadow | bb_squeeze_breakout | GBP_USD | Off | 7 | 42.9% | +5.200 | insufficient data |
| shadow | bb_squeeze_breakout | USD_JPY | Asia | 15 | 26.7% | -1.020 | insufficient data |
| shadow | bb_squeeze_breakout | USD_JPY | London | 17 | 11.8% | -1.776 | insufficient data |
| shadow | bb_squeeze_breakout | USD_JPY | NY-overlap | 10 | 60.0% | +7.560 | insufficient data |
| shadow | bb_squeeze_breakout | USD_JPY | Off | 10 | 20.0% | -1.140 | insufficient data |
| shadow | confluence_scalp | EUR_USD | London | 1 | 0.0% | -0.600 | insufficient data |
| shadow | doji_breakout | GBP_USD | London | 1 | 0.0% | -5.000 | insufficient data |
| shadow | doji_breakout | GBP_USD | NY-overlap | 1 | 0.0% | -11.300 | insufficient data |
| shadow | doji_breakout | USD_JPY | Asia | 1 | 100.0% | +9.100 | insufficient data |
| shadow | doji_breakout | USD_JPY | London | 1 | 100.0% | +24.800 | insufficient data |
| shadow | donchian_momentum_breakout | EUR_USD | London | 1 | 0.0% | -7.900 | insufficient data |
| shadow | donchian_momentum_breakout | EUR_USD | NY-overlap | 1 | 0.0% | -21.600 | insufficient data |
| shadow | dt_bb_rsi_mr | EUR_USD | London | 7 | 57.1% | +3.343 | insufficient data |
| shadow | dt_bb_rsi_mr | EUR_USD | NY-overlap | 1 | 0.0% | -3.200 | insufficient data |
| shadow | dt_bb_rsi_mr | GBP_USD | Asia | 10 | 30.0% | -0.940 | insufficient data |
| shadow | dt_bb_rsi_mr | GBP_USD | London | 4 | 25.0% | -3.400 | insufficient data |
| shadow | dt_bb_rsi_mr | GBP_USD | NY-overlap | 2 | 100.0% | +7.550 | insufficient data |
| shadow | dt_bb_rsi_mr | GBP_USD | Off | 5 | 60.0% | +7.060 | insufficient data |
| shadow | dt_bb_rsi_mr | USD_JPY | Asia | 3 | 33.3% | +0.233 | insufficient data |
| shadow | dt_bb_rsi_mr | USD_JPY | London | 6 | 33.3% | -1.183 | insufficient data |
| shadow | dt_bb_rsi_mr | USD_JPY | NY-overlap | 1 | 0.0% | -1.800 | insufficient data |
| shadow | dt_bb_rsi_mr | USD_JPY | Off | 1 | 0.0% | -8.200 | insufficient data |
| shadow | dt_fib_reversal | EUR_JPY | Asia | 3 | 66.7% | +13.767 | insufficient data |
| shadow | dt_fib_reversal | EUR_JPY | London | 1 | 0.0% | -15.000 | insufficient data |
| shadow | dt_fib_reversal | EUR_JPY | NY-overlap | 1 | 100.0% | +22.300 | insufficient data |
| shadow | dt_fib_reversal | EUR_JPY | Off | 2 | 0.0% | -6.500 | insufficient data |
| shadow | dt_fib_reversal | EUR_USD | London | 2 | 50.0% | +1.800 | insufficient data |
| shadow | dt_fib_reversal | EUR_USD | NY-overlap | 1 | 0.0% | -10.600 | insufficient data |
| shadow | dt_fib_reversal | GBP_USD | Asia | 2 | 100.0% | +14.850 | insufficient data |
| shadow | dt_fib_reversal | GBP_USD | London | 2 | 0.0% | -6.500 | insufficient data |
| shadow | dt_fib_reversal | GBP_USD | NY-overlap | 1 | 0.0% | -0.800 | insufficient data |
| shadow | dt_fib_reversal | GBP_USD | Off | 1 | 0.0% | -1.400 | insufficient data |
| shadow | dt_fib_reversal | USD_JPY | Asia | 5 | 20.0% | -3.060 | insufficient data |
| shadow | dt_fib_reversal | USD_JPY | London | 2 | 0.0% | -8.500 | insufficient data |
| shadow | dt_fib_reversal | USD_JPY | NY-overlap | 2 | 50.0% | +4.400 | insufficient data |
| shadow | dt_fib_reversal | USD_JPY | Off | 2 | 0.0% | -5.450 | insufficient data |
| shadow | dt_sr_channel_reversal | EUR_JPY | Asia | 1 | 0.0% | -8.300 | insufficient data |
| shadow | dt_sr_channel_reversal | EUR_JPY | London | 7 | 28.6% | -1.443 | insufficient data |
| shadow | dt_sr_channel_reversal | EUR_JPY | NY-overlap | 12 | 33.3% | +3.233 | insufficient data |
| shadow | dt_sr_channel_reversal | EUR_USD | London | 9 | 33.3% | -1.022 | insufficient data |
| shadow | dt_sr_channel_reversal | EUR_USD | NY-overlap | 2 | 0.0% | -3.200 | insufficient data |
| shadow | dt_sr_channel_reversal | GBP_JPY | London | 1 | 0.0% | -20.100 | insufficient data |
| shadow | dt_sr_channel_reversal | GBP_JPY | NY-overlap | 2 | 100.0% | +8.550 | insufficient data |
| shadow | dt_sr_channel_reversal | GBP_USD | Asia | 2 | 100.0% | +2.800 | insufficient data |
| shadow | dt_sr_channel_reversal | GBP_USD | London | 7 | 14.3% | -3.914 | insufficient data |
| shadow | dt_sr_channel_reversal | GBP_USD | NY-overlap | 5 | 0.0% | -5.080 | insufficient data |
| shadow | dt_sr_channel_reversal | GBP_USD | Off | 1 | 100.0% | +2.900 | insufficient data |
| shadow | dt_sr_channel_reversal | USD_JPY | Asia | 6 | 50.0% | +0.283 | insufficient data |
| shadow | dt_sr_channel_reversal | USD_JPY | London | 5 | 60.0% | +3.120 | insufficient data |
| shadow | dt_sr_channel_reversal | USD_JPY | NY-overlap | 4 | 25.0% | +2.900 | insufficient data |
| shadow | dt_sr_channel_reversal | USD_JPY | Off | 2 | 50.0% | +0.000 | insufficient data |
| shadow | dual_sr_bounce | EUR_JPY | Asia | 1 | 0.0% | -13.100 | insufficient data |
| shadow | dual_sr_bounce | EUR_JPY | London | 1 | 0.0% | -5.100 | insufficient data |
| shadow | dual_sr_bounce | EUR_JPY | NY-overlap | 3 | 33.3% | +1.267 | insufficient data |
| shadow | dual_sr_bounce | EUR_JPY | Off | 2 | 0.0% | -6.000 | insufficient data |
| shadow | dual_sr_bounce | GBP_JPY | Asia | 2 | 0.0% | -7.800 | insufficient data |
| shadow | dual_sr_bounce | GBP_JPY | London | 1 | 0.0% | -10.600 | insufficient data |
| shadow | dual_sr_bounce | GBP_JPY | Off | 3 | 0.0% | -20.467 | insufficient data |
| shadow | dual_sr_bounce | GBP_USD | London | 2 | 0.0% | -9.650 | insufficient data |
| shadow | dual_sr_bounce | GBP_USD | NY-overlap | 4 | 0.0% | -11.925 | insufficient data |
| shadow | dual_sr_bounce | GBP_USD | Off | 3 | 0.0% | -5.467 | insufficient data |
| shadow | dual_sr_bounce | USD_JPY | Asia | 1 | 100.0% | +21.400 | insufficient data |
| shadow | dual_sr_bounce | USD_JPY | London | 2 | 0.0% | -7.200 | insufficient data |
| shadow | dual_sr_bounce | USD_JPY | NY-overlap | 3 | 33.3% | -2.000 | insufficient data |
| shadow | dual_sr_bounce | USD_JPY | Off | 1 | 0.0% | -5.000 | insufficient data |
| shadow | ema200_trend_reversal | EUR_JPY | Asia | 3 | 0.0% | -18.167 | insufficient data |
| shadow | ema200_trend_reversal | EUR_JPY | London | 6 | 66.7% | +13.450 | insufficient data |
| shadow | ema200_trend_reversal | EUR_JPY | Off | 3 | 0.0% | -15.000 | insufficient data |
| shadow | ema200_trend_reversal | EUR_USD | London | 1 | 0.0% | -8.300 | insufficient data |
| shadow | ema200_trend_reversal | EUR_USD | NY-overlap | 1 | 0.0% | -3.000 | insufficient data |
| shadow | ema200_trend_reversal | GBP_JPY | London | 1 | 100.0% | +28.300 | insufficient data |
| shadow | ema200_trend_reversal | GBP_JPY | NY-overlap | 2 | 0.0% | -9.500 | insufficient data |
| shadow | ema200_trend_reversal | GBP_USD | Asia | 1 | 0.0% | -7.200 | insufficient data |
| shadow | ema200_trend_reversal | GBP_USD | London | 2 | 50.0% | +2.950 | insufficient data |
| shadow | ema200_trend_reversal | USD_JPY | Asia | 1 | 0.0% | -0.900 | insufficient data |
| shadow | ema200_trend_reversal | USD_JPY | London | 4 | 50.0% | +2.200 | insufficient data |
| shadow | ema200_trend_reversal | USD_JPY | NY-overlap | 4 | 100.0% | +15.400 | insufficient data |
| shadow | ema200_trend_reversal | USD_JPY | Off | 3 | 33.3% | +4.267 | insufficient data |
| shadow | ema_cross | EUR_JPY | NY-overlap | 1 | 0.0% | -9.200 | insufficient data |
| shadow | ema_cross | EUR_JPY | Off | 1 | 0.0% | -10.400 | insufficient data |
| shadow | ema_cross | GBP_JPY | London | 1 | 0.0% | -14.800 | insufficient data |
| shadow | ema_cross | GBP_JPY | NY-overlap | 2 | 0.0% | -11.800 | insufficient data |
| shadow | ema_cross | GBP_USD | London | 1 | 100.0% | +16.500 | insufficient data |
| shadow | ema_cross | USD_JPY | Asia | 6 | 83.3% | +9.333 | insufficient data |
| shadow | ema_cross | USD_JPY | London | 12 | 16.7% | -4.617 | insufficient data |
| shadow | ema_cross | USD_JPY | NY-overlap | 5 | 100.0% | +16.400 | insufficient data |
| shadow | ema_cross | USD_JPY | Off | 6 | 50.0% | -0.833 | insufficient data |
| shadow | ema_pullback | EUR_USD | London | 3 | 0.0% | -2.200 | insufficient data |
| shadow | ema_pullback | EUR_USD | NY-overlap | 2 | 100.0% | +5.650 | insufficient data |
| shadow | ema_pullback | GBP_USD | Asia | 1 | 0.0% | -5.200 | insufficient data |
| shadow | ema_pullback | USD_JPY | London | 7 | 14.3% | -2.614 | insufficient data |
| shadow | ema_pullback | USD_JPY | NY-overlap | 3 | 66.7% | +4.400 | insufficient data |
| shadow | ema_pullback | USD_JPY | Off | 4 | 50.0% | +1.225 | insufficient data |
| shadow | ema_ribbon_ride | EUR_USD | Asia | 2 | 0.0% | -1.900 | insufficient data |
| shadow | ema_ribbon_ride | EUR_USD | London | 2 | 50.0% | -0.200 | insufficient data |
| shadow | ema_ribbon_ride | USD_JPY | London | 2 | 50.0% | +1.400 | insufficient data |
| shadow | ema_trend_scalp | GBP_USD | Asia | 29 | 17.2% | -2.272 | insufficient data |
| shadow | ema_trend_scalp | GBP_USD | Off | 19 | 36.8% | +0.274 | insufficient data |
| shadow | engulfing_bb | EUR_USD | NY-overlap | 13 | 30.8% | -0.492 | insufficient data |
| shadow | engulfing_bb | GBP_USD | Asia | 5 | 40.0% | -1.780 | insufficient data |
| shadow | engulfing_bb | GBP_USD | London | 9 | 22.2% | -1.822 | insufficient data |
| shadow | engulfing_bb | GBP_USD | NY-overlap | 6 | 16.7% | -3.333 | insufficient data |
| shadow | engulfing_bb | GBP_USD | Off | 3 | 66.7% | +6.967 | insufficient data |
| shadow | engulfing_bb | USD_JPY | Off | 23 | 39.1% | +0.200 | insufficient data |
| shadow | eurgbp_daily_mr | EUR_GBP | NY-overlap | 1 | 0.0% | -3.500 | insufficient data |
| shadow | fib_reversal | EUR_JPY | NY-overlap | 1 | 0.0% | -4.400 | insufficient data |
| shadow | fib_reversal | EUR_USD | Asia | 5 | 0.0% | -1.780 | insufficient data |
| shadow | fib_reversal | EUR_USD | NY-overlap | 14 | 50.0% | +0.371 | insufficient data |
| shadow | fib_reversal | EUR_USD | Off | 1 | 0.0% | -2.500 | insufficient data |
| shadow | fib_reversal | GBP_USD | London | 3 | 33.3% | +1.633 | insufficient data |
| shadow | fib_reversal | GBP_USD | NY-overlap | 4 | 25.0% | -3.700 | insufficient data |
| shadow | fib_reversal | GBP_USD | Off | 1 | 100.0% | +7.900 | insufficient data |
| shadow | fib_reversal | USD_JPY | Off | 26 | 34.6% | -0.165 | insufficient data |
| shadow | gbp_deep_pullback | GBP_USD | London | 1 | 0.0% | -20.000 | insufficient data |
| shadow | h1_fib_reversal | USD_JPY | London | 5 | 20.0% | -4.180 | insufficient data |
| shadow | htf_false_breakout | EUR_JPY | London | 5 | 0.0% | -20.640 | insufficient data |
| shadow | htf_false_breakout | GBP_JPY | London | 1 | 0.0% | -23.500 | insufficient data |
| shadow | htf_false_breakout | GBP_USD | London | 1 | 100.0% | +2.300 | insufficient data |
| shadow | htf_false_breakout | USD_JPY | Asia | 1 | 0.0% | -7.100 | insufficient data |
| shadow | inducement_ob | GBP_USD | Asia | 3 | 0.0% | -6.233 | insufficient data |
| shadow | inducement_ob | USD_JPY | London | 1 | 0.0% | -7.400 | insufficient data |
| shadow | intraday_seasonality | GBP_USD | Asia | 7 | 42.9% | +2.729 | insufficient data |
| shadow | intraday_seasonality | GBP_USD | NY-overlap | 1 | 0.0% | -5.600 | insufficient data |
| shadow | intraday_seasonality | GBP_USD | Off | 2 | 0.0% | -6.750 | insufficient data |
| shadow | lin_reg_channel | EUR_USD | Asia | 1 | 0.0% | -20.900 | insufficient data |
| shadow | lin_reg_channel | EUR_USD | London | 1 | 0.0% | -6.600 | insufficient data |
| shadow | lin_reg_channel | EUR_USD | NY-overlap | 1 | 0.0% | -7.200 | insufficient data |
| shadow | liquidity_sweep | USD_JPY | London | 1 | 0.0% | -7.600 | insufficient data |
| shadow | london_fix_reversal | EUR_USD | NY-overlap | 2 | 0.0% | -3.250 | insufficient data |
| shadow | london_fix_reversal | GBP_USD | NY-overlap | 3 | 0.0% | -8.033 | insufficient data |
| shadow | london_fix_reversal | GBP_USD | Off | 1 | 0.0% | -10.300 | insufficient data |
| shadow | macdh_reversal | EUR_USD | Asia | 6 | 16.7% | -0.983 | insufficient data |
| shadow | macdh_reversal | EUR_USD | London | 12 | 25.0% | -1.908 | insufficient data |
| shadow | macdh_reversal | EUR_USD | NY-overlap | 5 | 40.0% | +1.120 | insufficient data |
| shadow | macdh_reversal | GBP_USD | London | 4 | 25.0% | -1.550 | insufficient data |
| shadow | macdh_reversal | GBP_USD | NY-overlap | 2 | 50.0% | +2.900 | insufficient data |
| shadow | macdh_reversal | USD_JPY | Asia | 14 | 14.3% | -1.593 | insufficient data |
| shadow | macdh_reversal | USD_JPY | London | 11 | 36.4% | -0.418 | insufficient data |
| shadow | macdh_reversal | USD_JPY | NY-overlap | 15 | 26.7% | -3.900 | insufficient data |
| shadow | macdh_reversal | USD_JPY | Off | 7 | 0.0% | -3.614 | insufficient data |
| shadow | mtf_reversal_confluence | EUR_USD | London | 1 | 0.0% | -6.300 | insufficient data |
| shadow | mtf_trend_follow_scalp | USD_JPY | London | 1 | 0.0% | -3.200 | insufficient data |
| shadow | mtf_trend_follow_scalp | USD_JPY | NY-overlap | 2 | 0.0% | -8.150 | insufficient data |
| shadow | ny_close_reversal | GBP_USD | Off | 1 | 0.0% | -24.600 | insufficient data |
| shadow | ny_close_reversal | USD_JPY | Off | 4 | 25.0% | +2.150 | insufficient data |
| shadow | orb_trap | EUR_USD | London | 1 | 0.0% | -7.100 | insufficient data |
| shadow | orb_trap | EUR_USD | NY-overlap | 1 | 0.0% | -10.600 | insufficient data |
| shadow | orb_trap | GBP_USD | London | 1 | 0.0% | -5.000 | insufficient data |
| shadow | orb_trap | USD_JPY | NY-overlap | 2 | 50.0% | -2.050 | insufficient data |
| shadow | pivot_breakout | USD_JPY | NY-overlap | 4 | 50.0% | -5.725 | insufficient data |
| shadow | post_news_vol | EUR_USD | London | 7 | 14.3% | -4.871 | insufficient data |
| shadow | post_news_vol | EUR_USD | NY-overlap | 1 | 100.0% | +19.300 | insufficient data |
| shadow | post_news_vol | GBP_USD | Asia | 2 | 0.0% | -20.050 | insufficient data |
| shadow | post_news_vol | GBP_USD | London | 2 | 50.0% | +5.750 | insufficient data |
| shadow | post_news_vol | GBP_USD | NY-overlap | 2 | 0.0% | -15.800 | insufficient data |
| shadow | post_news_vol | USD_JPY | Asia | 3 | 0.0% | -9.667 | insufficient data |
| shadow | post_news_vol | USD_JPY | London | 6 | 66.7% | +70.417 | insufficient data |
| shadow | post_news_vol | USD_JPY | Off | 5 | 0.0% | -16.020 | insufficient data |
| shadow | rsk_gbpjpy_reversion | GBP_JPY | London | 12 | 0.0% | -24.442 | insufficient data |
| shadow | session_time_bias | EUR_USD | London | 7 | 42.9% | +2.943 | insufficient data |
| shadow | session_time_bias | EUR_USD | NY-overlap | 3 | 33.3% | -5.267 | insufficient data |
| shadow | session_time_bias | GBP_USD | London | 2 | 50.0% | +2.650 | insufficient data |
| shadow | session_time_bias | GBP_USD | NY-overlap | 4 | 50.0% | +2.500 | insufficient data |
| shadow | session_time_bias | GBP_USD | Off | 8 | 12.5% | -6.850 | insufficient data |
| shadow | squeeze_release_momentum | GBP_USD | Asia | 5 | 40.0% | -1.480 | insufficient data |
| shadow | squeeze_release_momentum | GBP_USD | Off | 2 | 0.0% | -6.200 | insufficient data |
| shadow | sr_anti_hunt_bounce | EUR_JPY | Asia | 3 | 0.0% | -14.833 | insufficient data |
| shadow | sr_anti_hunt_bounce | EUR_JPY | NY-overlap | 1 | 0.0% | -20.500 | insufficient data |
| shadow | sr_anti_hunt_bounce | GBP_JPY | Asia | 2 | 0.0% | -19.650 | insufficient data |
| shadow | sr_anti_hunt_bounce | GBP_JPY | Off | 1 | 0.0% | -24.600 | insufficient data |
| shadow | sr_anti_hunt_bounce | USD_JPY | London | 22 | 0.0% | -16.964 | insufficient data |
| shadow | sr_break_retest | EUR_JPY | Asia | 5 | 0.0% | -8.700 | insufficient data |
| shadow | sr_break_retest | EUR_JPY | London | 3 | 0.0% | -10.533 | insufficient data |
| shadow | sr_break_retest | EUR_JPY | NY-overlap | 4 | 0.0% | -8.925 | insufficient data |
| shadow | sr_break_retest | EUR_JPY | Off | 2 | 0.0% | -1.650 | insufficient data |
| shadow | sr_break_retest | GBP_JPY | London | 2 | 0.0% | -11.300 | insufficient data |
| shadow | sr_break_retest | GBP_JPY | NY-overlap | 2 | 0.0% | -15.550 | insufficient data |
| shadow | sr_break_retest | GBP_JPY | Off | 3 | 0.0% | -23.100 | insufficient data |
| shadow | sr_break_retest | GBP_USD | Asia | 2 | 50.0% | +5.550 | insufficient data |
| shadow | sr_break_retest | GBP_USD | London | 1 | 100.0% | +1.400 | insufficient data |
| shadow | sr_break_retest | GBP_USD | NY-overlap | 1 | 100.0% | +19.400 | insufficient data |
| shadow | sr_break_retest | GBP_USD | Off | 2 | 50.0% | -0.200 | insufficient data |
| shadow | sr_break_retest | USD_JPY | Asia | 12 | 33.3% | -1.692 | insufficient data |
| shadow | sr_break_retest | USD_JPY | London | 8 | 12.5% | -5.425 | insufficient data |
| shadow | sr_break_retest | USD_JPY | NY-overlap | 1 | 100.0% | +19.800 | insufficient data |
| shadow | sr_break_retest | USD_JPY | Off | 3 | 66.7% | +0.967 | insufficient data |
| shadow | sr_channel_reversal | EUR_USD | London | 21 | 14.3% | -2.819 | insufficient data |
| shadow | sr_channel_reversal | EUR_USD | NY-overlap | 25 | 32.0% | -0.460 | insufficient data |
| shadow | sr_channel_reversal | GBP_USD | Asia | 1 | 0.0% | -0.600 | insufficient data |
| shadow | sr_channel_reversal | GBP_USD | London | 14 | 7.1% | -3.907 | insufficient data |
| shadow | sr_channel_reversal | GBP_USD | NY-overlap | 15 | 40.0% | +0.607 | insufficient data |
| shadow | sr_channel_reversal | GBP_USD | Off | 6 | 66.7% | +8.400 | insufficient data |
| shadow | sr_fib_confluence | EUR_GBP | London | 1 | 0.0% | -5.100 | insufficient data |
| shadow | sr_fib_confluence | EUR_JPY | Asia | 11 | 18.2% | -7.736 | insufficient data |
| shadow | sr_fib_confluence | EUR_JPY | London | 13 | 0.0% | -12.908 | insufficient data |
| shadow | sr_fib_confluence | EUR_JPY | NY-overlap | 7 | 14.3% | -3.957 | insufficient data |
| shadow | sr_fib_confluence | EUR_JPY | Off | 2 | 0.0% | -10.100 | insufficient data |
| shadow | sr_fib_confluence | EUR_USD | London | 22 | 36.4% | +0.882 | insufficient data |
| shadow | sr_fib_confluence | EUR_USD | NY-overlap | 13 | 23.1% | -3.192 | insufficient data |
| shadow | sr_fib_confluence | GBP_JPY | Asia | 5 | 20.0% | -2.120 | insufficient data |
| shadow | sr_fib_confluence | GBP_JPY | London | 2 | 0.0% | -11.650 | insufficient data |
| shadow | sr_fib_confluence | GBP_JPY | NY-overlap | 4 | 50.0% | +15.050 | insufficient data |
| shadow | sr_fib_confluence | GBP_JPY | Off | 3 | 100.0% | +42.100 | insufficient data |
| shadow | sr_fib_confluence | GBP_USD | Asia | 3 | 33.3% | -4.467 | insufficient data |
| shadow | sr_fib_confluence | GBP_USD | London | 23 | 39.1% | +1.374 | insufficient data |
| shadow | sr_fib_confluence | GBP_USD | NY-overlap | 12 | 58.3% | +6.208 | insufficient data |
| shadow | sr_fib_confluence | USD_JPY | Asia | 9 | 22.2% | -1.878 | insufficient data |
| shadow | sr_fib_confluence | USD_JPY | London | 7 | 0.0% | -11.914 | insufficient data |
| shadow | sr_fib_confluence | USD_JPY | NY-overlap | 8 | 12.5% | -7.250 | insufficient data |
| shadow | sr_fib_confluence | USD_JPY | Off | 7 | 71.4% | +11.600 | insufficient data |
| shadow | stoch_trend_pullback | EUR_USD | London | 19 | 26.3% | -0.832 | insufficient data |
| shadow | stoch_trend_pullback | EUR_USD | NY-overlap | 10 | 20.0% | -0.530 | insufficient data |
| shadow | stoch_trend_pullback | GBP_USD | Asia | 5 | 0.0% | -5.100 | insufficient data |
| shadow | stoch_trend_pullback | GBP_USD | London | 8 | 50.0% | +4.175 | insufficient data |
| shadow | stoch_trend_pullback | GBP_USD | NY-overlap | 8 | 12.5% | -3.500 | insufficient data |
| shadow | stoch_trend_pullback | GBP_USD | Off | 4 | 25.0% | -1.450 | insufficient data |
| shadow | stoch_trend_pullback | USD_JPY | Off | 26 | 26.9% | -1.146 | insufficient data |
| shadow | streak_reversal | USD_JPY | Asia | 5 | 0.0% | -4.980 | insufficient data |
| shadow | streak_reversal | USD_JPY | NY-overlap | 2 | 0.0% | -5.650 | insufficient data |
| shadow | three_bar_reversal | USD_JPY | London | 1 | 0.0% | -3.400 | insufficient data |
| shadow | trend_rebound | EUR_USD | London | 4 | 25.0% | -1.350 | insufficient data |
| shadow | trend_rebound | EUR_USD | NY-overlap | 1 | 0.0% | -3.000 | insufficient data |
| shadow | trend_rebound | GBP_USD | Asia | 1 | 0.0% | -6.000 | insufficient data |
| shadow | trend_rebound | GBP_USD | London | 2 | 0.0% | -5.150 | insufficient data |
| shadow | trend_rebound | GBP_USD | NY-overlap | 3 | 66.7% | +4.500 | insufficient data |
| shadow | trend_rebound | USD_JPY | Asia | 11 | 36.4% | -0.064 | insufficient data |
| shadow | trend_rebound | USD_JPY | London | 10 | 30.0% | -0.920 | insufficient data |
| shadow | trend_rebound | USD_JPY | NY-overlap | 6 | 50.0% | +3.633 | insufficient data |
| shadow | trend_rebound | USD_JPY | Off | 6 | 16.7% | -0.483 | insufficient data |
| shadow | trendline_sweep | EUR_USD | London | 2 | 0.0% | -6.900 | insufficient data |
| shadow | trendline_sweep | EUR_USD | NY-overlap | 2 | 0.0% | -9.600 | insufficient data |
| shadow | trendline_sweep | GBP_USD | London | 6 | 33.3% | +6.333 | insufficient data |
| shadow | trendline_sweep | GBP_USD | NY-overlap | 1 | 0.0% | -8.900 | insufficient data |
| shadow | v_reversal | USD_JPY | Asia | 2 | 50.0% | +2.300 | insufficient data |
| shadow | v_reversal | USD_JPY | London | 9 | 22.2% | -2.178 | insufficient data |
| shadow | v_reversal | USD_JPY | NY-overlap | 6 | 16.7% | -3.183 | insufficient data |
| shadow | v_reversal | USD_JPY | Off | 1 | 100.0% | +7.000 | insufficient data |
| shadow | vix_carry_unwind | USD_JPY | Asia | 4 | 0.0% | -21.250 | insufficient data |
| shadow | vol_momentum_scalp | GBP_USD | Asia | 4 | 25.0% | -0.975 | insufficient data |
| shadow | vol_momentum_scalp | GBP_USD | London | 27 | 3.7% | -4.096 | insufficient data |
| shadow | vol_momentum_scalp | GBP_USD | NY-overlap | 7 | 14.3% | -1.757 | insufficient data |
| shadow | vol_momentum_scalp | GBP_USD | Off | 7 | 28.6% | -1.457 | insufficient data |
| shadow | vol_momentum_scalp | USD_JPY | Asia | 4 | 25.0% | +1.675 | insufficient data |
| shadow | vol_momentum_scalp | USD_JPY | London | 3 | 0.0% | -6.067 | insufficient data |
| shadow | vol_momentum_scalp | USD_JPY | NY-overlap | 4 | 50.0% | +2.000 | insufficient data |
| shadow | vol_spike_mr | USD_JPY | Asia | 6 | 33.3% | -0.800 | insufficient data |
| shadow | vol_spike_mr | USD_JPY | London | 7 | 14.3% | -5.943 | insufficient data |
| shadow | vol_surge_detector | EUR_USD | London | 16 | 31.2% | -0.031 | insufficient data |
| shadow | vol_surge_detector | EUR_USD | NY-overlap | 4 | 0.0% | -5.050 | insufficient data |
| shadow | vol_surge_detector | GBP_USD | Asia | 14 | 0.0% | -5.800 | insufficient data |
| shadow | vol_surge_detector | GBP_USD | London | 4 | 0.0% | -2.375 | insufficient data |
| shadow | vol_surge_detector | USD_JPY | London | 8 | 50.0% | +7.912 | insufficient data |
| shadow | vsg_jpy_reversal | EUR_JPY | Asia | 4 | 100.0% | +22.800 | insufficient data |
| shadow | vsg_jpy_reversal | EUR_JPY | London | 5 | 0.0% | -17.720 | insufficient data |
| shadow | vsg_jpy_reversal | EUR_JPY | Off | 4 | 100.0% | +8.400 | insufficient data |
| shadow | vsg_jpy_reversal | GBP_JPY | London | 3 | 0.0% | -24.833 | insufficient data |
| shadow | vsg_jpy_reversal | GBP_JPY | NY-overlap | 2 | 100.0% | +27.500 | insufficient data |
| shadow | vwap_mean_reversion | EUR_JPY | Asia | 2 | 0.0% | -11.150 | insufficient data |
| shadow | vwap_mean_reversion | EUR_JPY | London | 5 | 0.0% | -11.100 | insufficient data |
| shadow | vwap_mean_reversion | EUR_JPY | NY-overlap | 1 | 0.0% | -20.000 | insufficient data |
| shadow | vwap_mean_reversion | EUR_USD | London | 5 | 20.0% | -2.900 | insufficient data |
| shadow | vwap_mean_reversion | EUR_USD | NY-overlap | 2 | 50.0% | +14.850 | insufficient data |
| shadow | vwap_mean_reversion | GBP_JPY | London | 4 | 50.0% | +10.150 | insufficient data |
| shadow | vwap_mean_reversion | GBP_JPY | NY-overlap | 2 | 50.0% | +5.100 | insufficient data |
| shadow | vwap_mean_reversion | GBP_JPY | Off | 1 | 100.0% | +0.600 | insufficient data |
| shadow | vwap_mean_reversion | GBP_USD | Asia | 1 | 100.0% | +33.100 | insufficient data |
| shadow | vwap_mean_reversion | GBP_USD | London | 1 | 0.0% | -20.100 | insufficient data |
| shadow | vwap_mean_reversion | GBP_USD | NY-overlap | 5 | 20.0% | -4.060 | insufficient data |
| shadow | vwap_mean_reversion | GBP_USD | Off | 1 | 100.0% | +8.500 | insufficient data |
| shadow | vwap_mean_reversion | USD_JPY | Asia | 3 | 0.0% | -0.800 | insufficient data |
| shadow | wick_imbalance_reversion | EUR_JPY | Asia | 1 | 100.0% | +14.700 | insufficient data |
| shadow | wick_imbalance_reversion | EUR_JPY | London | 4 | 0.0% | -21.475 | insufficient data |
| shadow | wick_imbalance_reversion | EUR_USD | London | 3 | 33.3% | -7.933 | insufficient data |
| shadow | wick_imbalance_reversion | EUR_USD | NY-overlap | 1 | 0.0% | -1.400 | insufficient data |
| shadow | wick_imbalance_reversion | GBP_JPY | Asia | 1 | 0.0% | -11.400 | insufficient data |
| shadow | wick_imbalance_reversion | GBP_JPY | London | 4 | 25.0% | +7.125 | insufficient data |
| shadow | wick_imbalance_reversion | GBP_JPY | NY-overlap | 4 | 0.0% | -11.525 | insufficient data |
| shadow | wick_imbalance_reversion | GBP_JPY | Off | 2 | 0.0% | -17.900 | insufficient data |
| shadow | wick_imbalance_reversion | GBP_USD | Asia | 3 | 33.3% | +2.900 | insufficient data |
| shadow | wick_imbalance_reversion | GBP_USD | London | 2 | 50.0% | -0.150 | insufficient data |
| shadow | wick_imbalance_reversion | GBP_USD | Off | 1 | 0.0% | -8.300 | insufficient data |
| shadow | wick_imbalance_reversion | USD_JPY | Asia | 1 | 100.0% | +12.200 | insufficient data |
| shadow | wick_imbalance_reversion | USD_JPY | London | 2 | 100.0% | +8.500 | insufficient data |
| shadow | wick_imbalance_reversion | USD_JPY | NY-overlap | 1 | 0.0% | -8.400 | insufficient data |
| shadow | xs_momentum | EUR_USD | London | 1 | 0.0% | -5.000 | insufficient data |
| shadow | xs_momentum | EUR_USD | NY-overlap | 10 | 30.0% | +0.480 | insufficient data |
| shadow | xs_momentum | GBP_USD | Asia | 2 | 0.0% | -10.650 | insufficient data |
| shadow | xs_momentum | GBP_USD | London | 8 | 0.0% | -8.012 | insufficient data |
| shadow | xs_momentum | GBP_USD | NY-overlap | 16 | 50.0% | +8.650 | insufficient data |
| shadow | xs_momentum | GBP_USD | Off | 1 | 100.0% | +28.700 | insufficient data |
| shadow | xs_momentum | USD_JPY | Asia | 2 | 0.0% | -3.650 | insufficient data |
| shadow | xs_momentum | USD_JPY | NY-overlap | 9 | 44.4% | -1.067 | insufficient data |
| shadow | xs_momentum | USD_JPY | Off | 1 | 0.0% | -8.200 | insufficient data |
| live | bb_rsi_reversion | EUR_USD | Asia | 11 | 27.3% | -0.627 | insufficient data |
| live | bb_rsi_reversion | EUR_USD | London | 12 | 50.0% | -0.600 | insufficient data |
| live | bb_rsi_reversion | EUR_USD | NY-overlap | 11 | 36.4% | -1.100 | insufficient data |
| live | bb_rsi_reversion | EUR_USD | Off | 1 | 0.0% | -3.100 | insufficient data |
| live | bb_rsi_reversion | GBP_USD | London | 1 | 0.0% | -6.100 | insufficient data |
| live | bb_rsi_reversion | GBP_USD | NY-overlap | 3 | 66.7% | +2.833 | insufficient data |
| live | bb_rsi_reversion | USD_JPY | London | 23 | 47.8% | -0.157 | insufficient data |
| live | bb_rsi_reversion | USD_JPY | NY-overlap | 28 | 35.7% | -1.286 | insufficient data |
| live | bb_rsi_reversion | USD_JPY | Off | 24 | 50.0% | -0.175 | insufficient data |
| live | bb_squeeze_breakout | EUR_USD | London | 2 | 50.0% | -0.100 | insufficient data |
| live | bb_squeeze_breakout | EUR_USD | NY-overlap | 4 | 50.0% | +1.150 | insufficient data |
| live | bb_squeeze_breakout | USD_JPY | Asia | 6 | 33.3% | -1.200 | insufficient data |
| live | bb_squeeze_breakout | USD_JPY | London | 2 | 50.0% | -1.200 | insufficient data |
| live | bb_squeeze_breakout | USD_JPY | Off | 1 | 0.0% | -3.000 | insufficient data |
| live | doji_breakout | EUR_USD | London | 1 | 0.0% | -10.600 | insufficient data |
| live | doji_breakout | GBP_USD | London | 1 | 0.0% | -10.100 | insufficient data |
| live | doji_breakout | USD_JPY | London | 1 | 100.0% | +12.400 | insufficient data |
| live | doji_breakout | USD_JPY | NY-overlap | 1 | 100.0% | +9.200 | insufficient data |
| live | donchian_momentum_breakout | EUR_USD | London | 3 | 33.3% | -12.000 | insufficient data |
| live | donchian_momentum_breakout | EUR_USD | NY-overlap | 1 | 100.0% | +17.100 | insufficient data |
| live | dt_bb_rsi_mr | EUR_USD | London | 2 | 50.0% | +0.100 | insufficient data |
| live | dt_bb_rsi_mr | EUR_USD | NY-overlap | 2 | 0.0% | -9.350 | insufficient data |
| live | dt_bb_rsi_mr | GBP_USD | NY-overlap | 2 | 50.0% | -5.100 | insufficient data |
| live | dt_bb_rsi_mr | GBP_USD | Off | 1 | 100.0% | +18.600 | insufficient data |
| live | dt_bb_rsi_mr | USD_JPY | Asia | 1 | 0.0% | -6.200 | insufficient data |
| live | dt_bb_rsi_mr | USD_JPY | London | 2 | 50.0% | -1.850 | insufficient data |
| live | dt_bb_rsi_mr | USD_JPY | NY-overlap | 4 | 75.0% | +5.100 | insufficient data |
| live | dt_sr_channel_reversal | EUR_JPY | NY-overlap | 1 | 0.0% | -17.400 | insufficient data |
| live | dt_sr_channel_reversal | GBP_USD | Asia | 1 | 100.0% | +9.100 | insufficient data |
| live | dt_sr_channel_reversal | GBP_USD | Off | 1 | 0.0% | -9.100 | insufficient data |
| live | dt_sr_channel_reversal | USD_JPY | Asia | 2 | 50.0% | -3.450 | insufficient data |
| live | dt_sr_channel_reversal | USD_JPY | London | 1 | 100.0% | +0.700 | insufficient data |
| live | dt_sr_channel_reversal | USD_JPY | NY-overlap | 1 | 100.0% | +16.300 | insufficient data |
| live | dual_sr_bounce | USD_JPY | Asia | 3 | 0.0% | -4.467 | insufficient data |
| live | dual_sr_bounce | USD_JPY | NY-overlap | 2 | 0.0% | -5.250 | insufficient data |
| live | ema200_trend_reversal | USD_JPY | NY-overlap | 1 | 100.0% | +0.800 | insufficient data |
| live | ema_cross | GBP_USD | London | 1 | 100.0% | +1.300 | insufficient data |
| live | ema_cross | GBP_USD | Off | 1 | 0.0% | -9.300 | insufficient data |
| live | ema_cross | USD_JPY | Asia | 1 | 100.0% | +0.800 | insufficient data |
| live | ema_cross | USD_JPY | NY-overlap | 15 | 26.7% | -4.007 | insufficient data |
| live | ema_cross | USD_JPY | Off | 2 | 0.0% | -5.050 | insufficient data |
| live | ema_pullback | EUR_USD | London | 3 | 0.0% | -2.733 | insufficient data |
| live | ema_pullback | EUR_USD | NY-overlap | 2 | 50.0% | +0.400 | insufficient data |
| live | ema_pullback | EUR_USD | Off | 1 | 0.0% | -1.000 | insufficient data |
| live | ema_pullback | USD_JPY | London | 3 | 33.3% | +1.133 | insufficient data |
| live | ema_pullback | USD_JPY | NY-overlap | 6 | 66.7% | +1.517 | insufficient data |
| live | ema_pullback | USD_JPY | Off | 2 | 0.0% | -0.700 | insufficient data |
| live | ema_ribbon_ride | EUR_USD | Off | 2 | 0.0% | -3.200 | insufficient data |
| live | ema_ribbon_ride | USD_JPY | Asia | 1 | 0.0% | -3.000 | insufficient data |
| live | ema_ribbon_ride | USD_JPY | Off | 1 | 0.0% | -3.300 | insufficient data |
| live | ema_trend_scalp | EUR_USD | London | 8 | 37.5% | +0.588 | insufficient data |
| live | ema_trend_scalp | EUR_USD | NY-overlap | 2 | 50.0% | -0.600 | insufficient data |
| live | ema_trend_scalp | GBP_USD | Asia | 1 | 0.0% | -5.100 | insufficient data |
| live | ema_trend_scalp | GBP_USD | NY-overlap | 1 | 0.0% | -5.500 | insufficient data |
| live | ema_trend_scalp | USD_JPY | Asia | 1 | 0.0% | -3.100 | insufficient data |
| live | ema_trend_scalp | USD_JPY | NY-overlap | 3 | 66.7% | +2.600 | insufficient data |
| live | engulfing_bb | EUR_USD | London | 4 | 25.0% | -0.625 | insufficient data |
| live | engulfing_bb | EUR_USD | NY-overlap | 1 | 0.0% | -3.000 | insufficient data |
| live | engulfing_bb | GBP_USD | London | 1 | 100.0% | +1.300 | insufficient data |
| live | engulfing_bb | USD_JPY | Asia | 1 | 0.0% | -0.800 | insufficient data |
| live | engulfing_bb | USD_JPY | London | 3 | 33.3% | -1.767 | insufficient data |
| live | engulfing_bb | USD_JPY | NY-overlap | 5 | 40.0% | -0.280 | insufficient data |
| live | fib_reversal | EUR_USD | Asia | 7 | 42.9% | -1.057 | insufficient data |
| live | fib_reversal | EUR_USD | London | 19 | 42.1% | -0.705 | insufficient data |
| live | fib_reversal | EUR_USD | NY-overlap | 11 | 36.4% | -0.755 | insufficient data |
| live | fib_reversal | EUR_USD | Off | 4 | 25.0% | -1.300 | insufficient data |
| live | fib_reversal | GBP_USD | London | 1 | 100.0% | +7.000 | insufficient data |
| live | fib_reversal | USD_JPY | Asia | 12 | 41.7% | -0.533 | insufficient data |
| live | fib_reversal | USD_JPY | London | 4 | 25.0% | -1.175 | insufficient data |
| live | fib_reversal | USD_JPY | NY-overlap | 14 | 42.9% | +0.200 | insufficient data |
| live | fib_reversal | USD_JPY | Off | 5 | 0.0% | -2.960 | insufficient data |
| live | gbp_deep_pullback | GBP_USD | London | 2 | 100.0% | +4.600 | insufficient data |
| live | htf_false_breakout | EUR_USD | NY-overlap | 1 | 100.0% | +2.000 | insufficient data |
| live | inducement_ob | EUR_GBP | Asia | 1 | 100.0% | +1.100 | insufficient data |
| live | inducement_ob | EUR_GBP | London | 1 | 0.0% | -5.000 | insufficient data |
| live | inducement_ob | EUR_GBP | NY-overlap | 4 | 0.0% | -5.150 | insufficient data |
| live | inducement_ob | EUR_USD | Asia | 2 | 0.0% | -1.700 | insufficient data |
| live | inducement_ob | GBP_USD | NY-overlap | 1 | 0.0% | -0.600 | insufficient data |
| live | lin_reg_channel | EUR_USD | London | 1 | 0.0% | -9.600 | insufficient data |
| live | lin_reg_channel | EUR_USD | NY-overlap | 1 | 100.0% | +8.800 | insufficient data |
| live | macdh_reversal | EUR_USD | Asia | 5 | 20.0% | -2.280 | insufficient data |
| live | macdh_reversal | EUR_USD | London | 14 | 42.9% | -0.664 | insufficient data |
| live | macdh_reversal | EUR_USD | NY-overlap | 12 | 25.0% | -0.933 | insufficient data |
| live | macdh_reversal | EUR_USD | Off | 1 | 100.0% | +2.800 | insufficient data |
| live | macdh_reversal | USD_JPY | Asia | 4 | 25.0% | -2.425 | insufficient data |
| live | macdh_reversal | USD_JPY | London | 3 | 0.0% | -1.800 | insufficient data |
| live | macdh_reversal | USD_JPY | NY-overlap | 8 | 37.5% | -0.650 | insufficient data |
| live | macdh_reversal | USD_JPY | Off | 10 | 20.0% | -0.750 | insufficient data |
| live | mtf_reversal_confluence | EUR_USD | NY-overlap | 2 | 0.0% | -1.800 | insufficient data |
| live | mtf_reversal_confluence | USD_JPY | NY-overlap | 1 | 100.0% | +4.200 | insufficient data |
| live | mtf_reversal_confluence | USD_JPY | Off | 1 | 100.0% | +3.200 | insufficient data |
| live | orb_trap | EUR_USD | NY-overlap | 1 | 100.0% | +11.900 | insufficient data |
| live | orb_trap | GBP_USD | London | 1 | 100.0% | +16.100 | insufficient data |
| live | orb_trap | GBP_USD | NY-overlap | 3 | 66.7% | +8.333 | insufficient data |
| live | pivot_breakout | USD_JPY | NY-overlap | 1 | 0.0% | -19.900 | insufficient data |
| live | post_news_vol | GBP_USD | London | 1 | 100.0% | +1.300 | insufficient data |
| live | post_news_vol | USD_JPY | Asia | 1 | 100.0% | +17.700 | insufficient data |
| live | session_time_bias | GBP_USD | Asia | 3 | 0.0% | -6.733 | insufficient data |
| live | session_time_bias | GBP_USD | London | 4 | 50.0% | -1.950 | insufficient data |
| live | squeeze_release_momentum | GBP_USD | Asia | 1 | 0.0% | -6.100 | insufficient data |
| live | sr_break_retest | GBP_USD | NY-overlap | 3 | 66.7% | +6.067 | insufficient data |
| live | sr_break_retest | USD_JPY | Asia | 2 | 0.0% | -6.000 | insufficient data |
| live | sr_break_retest | USD_JPY | London | 1 | 0.0% | -11.100 | insufficient data |
| live | sr_break_retest | USD_JPY | NY-overlap | 1 | 0.0% | -20.400 | insufficient data |
| live | sr_channel_reversal | EUR_USD | London | 2 | 50.0% | +2.600 | insufficient data |
| live | sr_channel_reversal | EUR_USD | NY-overlap | 5 | 20.0% | -1.720 | insufficient data |
| live | sr_channel_reversal | GBP_USD | London | 2 | 50.0% | +2.250 | insufficient data |
| live | sr_channel_reversal | GBP_USD | NY-overlap | 2 | 50.0% | +3.000 | insufficient data |
| live | sr_channel_reversal | USD_JPY | Asia | 8 | 37.5% | -0.925 | insufficient data |
| live | sr_channel_reversal | USD_JPY | London | 9 | 11.1% | -2.311 | insufficient data |
| live | sr_channel_reversal | USD_JPY | Off | 2 | 50.0% | -1.100 | insufficient data |
| live | sr_fib_confluence | EUR_JPY | Asia | 1 | 0.0% | -11.300 | insufficient data |
| live | sr_fib_confluence | EUR_USD | Asia | 4 | 25.0% | -1.725 | insufficient data |
| live | sr_fib_confluence | EUR_USD | London | 5 | 40.0% | +0.420 | insufficient data |
| live | sr_fib_confluence | EUR_USD | NY-overlap | 3 | 66.7% | +3.033 | insufficient data |
| live | sr_fib_confluence | GBP_JPY | Asia | 1 | 0.0% | -11.500 | insufficient data |
| live | sr_fib_confluence | GBP_USD | Asia | 4 | 50.0% | +0.675 | insufficient data |
| live | sr_fib_confluence | GBP_USD | London | 5 | 80.0% | +5.440 | insufficient data |
| live | sr_fib_confluence | GBP_USD | NY-overlap | 1 | 0.0% | -10.100 | insufficient data |
| live | sr_fib_confluence | GBP_USD | Off | 2 | 0.0% | -9.200 | insufficient data |
| live | sr_fib_confluence | USD_JPY | Asia | 1 | 0.0% | -4.400 | insufficient data |
| live | sr_fib_confluence | USD_JPY | London | 3 | 33.3% | -7.033 | insufficient data |
| live | sr_fib_confluence | USD_JPY | NY-overlap | 5 | 40.0% | -4.240 | insufficient data |
| live | stoch_trend_pullback | EUR_USD | London | 7 | 28.6% | -0.371 | insufficient data |
| live | stoch_trend_pullback | EUR_USD | NY-overlap | 2 | 100.0% | +3.900 | insufficient data |
| live | stoch_trend_pullback | EUR_USD | Off | 2 | 0.0% | -3.000 | insufficient data |
| live | stoch_trend_pullback | USD_JPY | Asia | 7 | 71.4% | +2.100 | insufficient data |
| live | stoch_trend_pullback | USD_JPY | London | 8 | 25.0% | -1.212 | insufficient data |
| live | stoch_trend_pullback | USD_JPY | NY-overlap | 4 | 25.0% | -1.750 | insufficient data |
| live | stoch_trend_pullback | USD_JPY | Off | 6 | 50.0% | +1.550 | insufficient data |
| live | streak_reversal | USD_JPY | London | 1 | 0.0% | -23.400 | insufficient data |
| live | three_bar_reversal | USD_JPY | Asia | 1 | 0.0% | -3.200 | insufficient data |
| live | trend_rebound | EUR_USD | London | 4 | 25.0% | -1.000 | insufficient data |
| live | trend_rebound | EUR_USD | NY-overlap | 3 | 66.7% | +2.033 | insufficient data |
| live | trend_rebound | GBP_USD | NY-overlap | 1 | 0.0% | -7.100 | insufficient data |
| live | trend_rebound | USD_JPY | Asia | 2 | 50.0% | +0.300 | insufficient data |
| live | trend_rebound | USD_JPY | London | 3 | 33.3% | -0.533 | insufficient data |
| live | trend_rebound | USD_JPY | Off | 2 | 50.0% | -1.400 | insufficient data |
| live | trendline_sweep | GBP_USD | Asia | 1 | 100.0% | +1.400 | insufficient data |
| live | trendline_sweep | GBP_USD | London | 3 | 33.3% | -1.767 | insufficient data |
| live | v_reversal | USD_JPY | Asia | 1 | 0.0% | -3.000 | insufficient data |
| live | v_reversal | USD_JPY | NY-overlap | 3 | 33.3% | +0.400 | insufficient data |
| live | v_reversal | USD_JPY | Off | 1 | 0.0% | -3.100 | insufficient data |
| live | vix_carry_unwind | USD_JPY | Asia | 2 | 50.0% | -6.550 | insufficient data |
| live | vix_carry_unwind | USD_JPY | London | 1 | 0.0% | -8.200 | insufficient data |
| live | vol_momentum_scalp | GBP_USD | London | 2 | 50.0% | +1.750 | insufficient data |
| live | vol_momentum_scalp | GBP_USD | NY-overlap | 1 | 0.0% | -3.800 | insufficient data |
| live | vol_momentum_scalp | USD_JPY | Asia | 1 | 100.0% | +4.200 | insufficient data |
| live | vol_momentum_scalp | USD_JPY | London | 7 | 57.1% | +0.571 | insufficient data |
| live | vol_momentum_scalp | USD_JPY | NY-overlap | 3 | 66.7% | +0.533 | insufficient data |
| live | vol_momentum_scalp | USD_JPY | Off | 2 | 50.0% | +0.950 | insufficient data |
| live | vol_surge_detector | EUR_USD | London | 3 | 66.7% | +0.667 | insufficient data |
| live | vol_surge_detector | EUR_USD | NY-overlap | 3 | 66.7% | +2.233 | insufficient data |
| live | vol_surge_detector | GBP_USD | London | 1 | 0.0% | -3.900 | insufficient data |
| live | vol_surge_detector | GBP_USD | NY-overlap | 2 | 100.0% | +1.150 | insufficient data |
| live | vol_surge_detector | USD_JPY | Asia | 10 | 40.0% | -0.970 | insufficient data |
| live | vol_surge_detector | USD_JPY | London | 5 | 20.0% | -1.680 | insufficient data |
| live | vol_surge_detector | USD_JPY | NY-overlap | 9 | 77.8% | +1.033 | insufficient data |
| live | vwap_mean_reversion | EUR_JPY | London | 1 | 0.0% | -22.600 | insufficient data |
| live | vwap_mean_reversion | EUR_JPY | NY-overlap | 2 | 50.0% | -4.300 | insufficient data |
| live | vwap_mean_reversion | EUR_JPY | Off | 1 | 100.0% | +2.100 | insufficient data |
| live | vwap_mean_reversion | GBP_JPY | Asia | 1 | 100.0% | +44.200 | insufficient data |
| live | vwap_mean_reversion | GBP_JPY | London | 1 | 0.0% | -20.100 | insufficient data |
| live | vwap_mean_reversion | GBP_USD | Asia | 2 | 50.0% | -3.050 | insufficient data |
| live | vwap_mean_reversion | GBP_USD | London | 2 | 0.0% | -18.950 | insufficient data |
| live | vwap_mean_reversion | GBP_USD | NY-overlap | 1 | 0.0% | -14.100 | insufficient data |
| live | xs_momentum | GBP_USD | London | 1 | 0.0% | -21.400 | insufficient data |
| live | xs_momentum | GBP_USD | NY-overlap | 1 | 100.0% | +22.200 | insufficient data |