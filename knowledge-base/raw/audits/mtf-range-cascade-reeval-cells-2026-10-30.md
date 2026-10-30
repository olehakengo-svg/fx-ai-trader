# mtf_regime_range_cascade_scalp 再評価 — production 180d range-regime cell table (2026-10-30)

- Source: `GET https://fx-ai-trader.onrender.com/api/demo/trades?status=closed&date_from=2026-05-03&date_to=2026-10-30` (paginated, 15,375 closed rows, pulled 2026-10-30 01:50Z)
- Filters: outcome ∈ {WIN, LOSS}, instrument ≠ XAU*, `dedup_violation` = 0 → 12,025 rows (dedup_violation flagged: 2,408)
- is_shadow: 15,127 / 15,375 rows are shadow (Shadow が estimator、LIVE 混入はほぼ無し)
- Cells: entry_type × mtf_regime ∈ {range_tight, range_wide}, N ≥ 5 → m = 114 cells; Bonferroni α = 0.05/114 = 0.00044 (z = 3.516)
- Companion lesson: `knowledge-base/wiki/lessons/lesson-mtf-regime-range-cascade-2026-10-30.md`

| entry_type | regime | N | WR% | Wilson95 lo% | Wilson_BF lo% | EV pips | PF |
|---|---|---:|---:|---:|---:|---:|---:|
| session_time_bias | range_wide | 300 | 39.0 | 33.7 | 29.7 | -1.95 | 0.57 |
| sr_break_retest | range_tight | 252 | 56.7 | 50.6 | 45.7 | -2.66 | 0.45 |
| dual_sr_bounce | range_wide | 241 | 44.8 | 38.7 | 34.1 | -1.65 | 0.65 |
| sr_break_retest | range_wide | 225 | 47.1 | 40.7 | 35.9 | -1.84 | 0.59 |
| dt_sr_channel_reversal | range_tight | 214 | 46.3 | 39.7 | 34.8 | -2.72 | 0.42 |
| dual_sr_bounce | range_tight | 180 | 49.4 | 42.2 | 36.8 | -2.94 | 0.45 |
| wick_imbalance_reversion | range_wide | 177 | 53.1 | 45.8 | 40.2 | -0.88 | 0.79 |
| dt_sr_channel_reversal | range_wide | 147 | 46.9 | 39.1 | 33.3 | -0.89 | 0.78 |
| xs_momentum | range_wide | 146 | 54.8 | 46.7 | 40.5 | -2.42 | 0.52 |
| london_breakout | range_wide | 116 | 40.5 | 32.0 | 26.2 | -1.69 | 0.44 |
| wick_imbalance_reversion | range_tight | 115 | 59.1 | 50.0 | 42.9 | -2.28 | 0.51 |
| vol_momentum_scalp | range_wide | 111 | 36.0 | 27.7 | 22.2 | -1.68 | 0.52 |
| sr_channel_reversal | range_tight | 107 | 35.5 | 27.1 | 21.5 | -1.33 | 0.56 |
| fib_reversal | range_wide | 107 | 31.8 | 23.7 | 18.6 | -1.45 | 0.45 |
| streak_reversal | range_wide | 88 | 56.8 | 46.4 | 38.6 | -1.78 | 0.63 |
| vol_momentum_scalp | range_tight | 84 | 33.3 | 24.2 | 18.5 | -1.52 | 0.52 |
| sr_channel_reversal | range_wide | 82 | 35.4 | 25.9 | 19.9 | -1.36 | 0.56 |
| session_time_bias | range_tight | 77 | 39.0 | 28.8 | 22.3 | -1.35 | 0.75 |
| vol_surge_detector | range_wide | 74 | 25.7 | 17.1 | 12.3 | -2.02 | 0.37 |
| engulfing_bb | range_wide | 74 | 28.4 | 19.4 | 14.1 | -1.92 | 0.41 |
| trendline_sweep | range_tight | 72 | 56.9 | 45.4 | 36.9 | -2.14 | 0.36 |
| london_breakout | range_tight | 69 | 36.2 | 25.9 | 19.5 | -1.76 | 0.49 |
| sr_anti_hunt_bounce | range_wide | 67 | 55.2 | 43.4 | 34.8 | -1.99 | 0.60 |
| donchian_momentum_breakout | range_wide | 65 | 58.5 | 46.3 | 37.4 | +0.06 | 1.01 |
| xs_momentum | range_tight | 65 | 64.6 | 52.5 | 43.0 | +0.88 | 1.24 |
| trendline_sweep | range_wide | 62 | 58.1 | 45.7 | 36.6 | -2.44 | 0.39 |
| ma_regime_switch | range_tight | 61 | 42.6 | 31.0 | 23.5 | -0.88 | 0.52 |
| vix_carry_unwind | range_tight | 60 | 58.3 | 45.7 | 36.5 | -0.61 | 0.90 |
| donchian_momentum_breakout | range_tight | 60 | 45.0 | 33.1 | 25.3 | -1.62 | 0.80 |
| xs_momentum_rsi | range_wide | 59 | 66.1 | 53.4 | 43.4 | -0.02 | 1.00 |
| three_bar_reversal | range_wide | 58 | 29.3 | 19.2 | 13.5 | -2.03 | 0.39 |
| streak_reversal | range_tight | 55 | 60.0 | 46.8 | 37.1 | -1.27 | 0.73 |
| gbp_deep_pullback | range_wide | 54 | 46.3 | 33.7 | 25.5 | -4.18 | 0.32 |
| ema_trend_scalp | range_tight | 53 | 11.3 | 5.3 | 3.0 | -2.91 | 0.24 |
| sr_anti_hunt_bounce | range_tight | 48 | 64.6 | 50.4 | 39.7 | -3.66 | 0.36 |
| eurgbp_daily_mr | range_tight | 48 | 35.4 | 23.4 | 16.6 | -2.16 | 0.27 |
| ma_regime_switch | range_wide | 48 | 22.9 | 13.3 | 8.7 | -2.13 | 0.23 |
| dt_bb_rsi_mr | range_wide | 46 | 58.7 | 44.3 | 34.1 | -0.47 | 0.85 |
| fib_reversal | range_tight | 45 | 22.2 | 12.5 | 8.0 | -2.63 | 0.28 |
| ob_retest | range_wide | 44 | 65.9 | 51.1 | 39.9 | +0.56 | 1.25 |
| engulfing_bb | range_tight | 43 | 32.6 | 20.5 | 14.0 | -1.73 | 0.44 |
| vol_surge_detector | range_tight | 40 | 35.0 | 22.1 | 15.1 | -1.50 | 0.56 |
| vix_carry_unwind | range_wide | 38 | 55.3 | 39.7 | 29.3 | -0.39 | 0.92 |
| vwap_mean_reversion | range_tight | 37 | 62.2 | 46.1 | 34.7 | +0.77 | 1.34 |
| vol_spike_mr | range_wide | 37 | 45.9 | 31.0 | 22.0 | -2.06 | 0.62 |
| ema_trend_scalp | range_wide | 36 | 19.4 | 9.8 | 5.8 | -1.37 | 0.61 |
| gbp_deep_pullback | range_tight | 35 | 74.3 | 57.9 | 44.7 | +4.05 | 2.60 |
| sr_fib_confluence | range_wide | 33 | 45.5 | 29.8 | 20.7 | -0.95 | 0.74 |
| xs_momentum_rsi | range_tight | 32 | 43.8 | 28.2 | 19.2 | -4.77 | 0.37 |
| bb_rsi_reversion | range_tight | 32 | 28.1 | 15.6 | 9.7 | -1.30 | 0.55 |
| bb_rsi_reversion | range_wide | 32 | 31.2 | 18.0 | 11.5 | -1.45 | 0.45 |
| three_bar_reversal | range_tight | 31 | 22.6 | 11.4 | 6.7 | -2.91 | 0.16 |
| sr_fib_confluence | range_tight | 30 | 60.0 | 42.3 | 30.5 | +0.66 | 1.22 |
| dt_bb_rsi_mr | range_tight | 26 | 53.8 | 35.5 | 24.3 | -0.31 | 0.91 |
| squeeze_release_momentum | range_wide | 26 | 46.2 | 28.8 | 19.1 | -2.11 | 0.49 |
| usdjpy_carry_dip_accumulator | range_wide | 25 | 52.0 | 33.5 | 22.6 | +3.79 | 1.51 |
| vsg_jpy_reversal | range_tight | 22 | 63.6 | 43.0 | 29.5 | -3.68 | 0.32 |
| trend_rebound | range_wide | 22 | 31.8 | 16.4 | 9.7 | -0.85 | 0.65 |
| bb_squeeze_breakout | range_wide | 22 | 27.3 | 13.2 | 7.5 | -1.27 | 0.45 |
| vol_spike_mr | range_tight | 21 | 57.1 | 36.5 | 24.3 | -0.80 | 0.77 |
| vwap_mean_reversion | range_wide | 21 | 71.4 | 50.0 | 34.9 | +1.51 | 1.53 |
| sr_weighted_bounce | range_wide | 21 | 52.4 | 32.4 | 21.1 | -3.07 | 0.31 |
| trend_rebound | range_tight | 20 | 30.0 | 14.5 | 8.3 | -1.45 | 0.28 |
| london_fix_reversal | range_wide | 20 | 55.0 | 34.2 | 22.3 | -0.57 | 0.84 |
| mtf_trend_follow_scalp | range_wide | 19 | 26.3 | 11.8 | 6.5 | -0.79 | 0.66 |
| sr_weighted_break | range_wide | 19 | 31.6 | 15.4 | 8.8 | -4.04 | 0.27 |
| ema200_trend_reversal | range_tight | 17 | 64.7 | 41.3 | 26.9 | +0.54 | 1.25 |
| sr_weighted_break | range_tight | 17 | 64.7 | 41.3 | 26.9 | -0.30 | 0.90 |
| htf_false_breakout | range_tight | 17 | 58.8 | 36.0 | 23.0 | -3.48 | 0.32 |
| rnb_support_bounce | range_wide | 16 | 56.2 | 33.2 | 20.7 | -3.38 | 0.34 |
| tokyo_nakane_momentum | range_wide | 16 | 37.5 | 18.5 | 10.5 | -2.06 | 0.60 |
| eurgbp_daily_mr | range_wide | 16 | 56.2 | 33.2 | 20.7 | -0.94 | 0.58 |
| ob_retest | range_tight | 16 | 43.8 | 23.1 | 13.6 | -5.34 | 0.15 |
| kalman_d7_po_dn_flip | range_wide | 15 | 80.0 | 54.8 | 36.3 | +1.00 | 1.42 |
| london_fix_reversal | range_tight | 14 | 28.6 | 11.7 | 6.1 | -6.15 | 0.05 |
| orb_trap | range_wide | 13 | 53.8 | 29.1 | 17.1 | -0.09 | 0.98 |
| htf_false_breakout | range_wide | 13 | 46.2 | 23.2 | 13.2 | -3.50 | 0.35 |
| squeeze_release_momentum | range_tight | 13 | 46.2 | 23.2 | 13.2 | -1.22 | 0.55 |
| macd_rsi_pullback | range_tight | 12 | 83.3 | 55.2 | 34.9 | +2.76 | 3.33 |
| intraday_seasonality | range_tight | 12 | 50.0 | 25.4 | 14.4 | +0.31 | 1.09 |
| pullback_to_liquidity_v1 | range_tight | 11 | 72.7 | 43.4 | 26.1 | -0.25 | 0.93 |
| rnb_support_bounce | range_tight | 11 | 45.5 | 21.3 | 11.6 | -3.57 | 0.46 |
| gotobi_fix | range_wide | 11 | 9.1 | 1.6 | 0.6 | -11.51 | 0.01 |
| doji_breakout | range_wide | 11 | 36.4 | 15.2 | 7.9 | -2.52 | 0.38 |
| rsk_gbpjpy_reversion | range_wide | 11 | 54.5 | 28.0 | 15.8 | -5.55 | 0.37 |
| bb_squeeze_breakout | range_tight | 10 | 30.0 | 10.8 | 5.2 | -1.36 | 0.38 |
| doji_breakout | range_tight | 10 | 30.0 | 10.8 | 5.2 | -8.80 | 0.05 |
| ny_close_reversal | range_tight | 10 | 60.0 | 31.3 | 17.6 | -0.54 | 0.92 |
| ema200_trend_reversal | range_wide | 10 | 60.0 | 31.3 | 17.6 | -1.97 | 0.46 |
| price_shock_rev_eur_gbp_h1_long | range_tight | 10 | 30.0 | 10.8 | 5.2 | -3.50 | 0.23 |
| v_reversal | range_tight | 9 | 22.2 | 6.3 | 2.8 | -3.82 | 0.07 |
| mtf_reversal_confluence | range_wide | 9 | 44.4 | 18.9 | 9.7 | +0.14 | 1.06 |
| mtf_trend_follow_scalp | range_tight | 8 | 37.5 | 13.7 | 6.6 | -1.55 | 0.37 |
| v_reversal | range_wide | 8 | 37.5 | 13.7 | 6.6 | -0.44 | 0.79 |
| turtle_soup | range_wide | 8 | 75.0 | 40.9 | 22.8 | +0.10 | 1.10 |
| pullback_to_liquidity_v1 | range_wide | 8 | 50.0 | 21.5 | 11.0 | -1.18 | 0.68 |
| macd_rsi_pullback | range_wide | 7 | 42.9 | 15.8 | 7.6 | -3.71 | 0.29 |
| london_session_breakout | range_wide | 7 | 100.0 | 64.6 | 36.2 | +2.46 | ∞ |
| sr_weighted_bounce | range_tight | 7 | 71.4 | 35.9 | 19.1 | -4.34 | 0.27 |
| rsk_gbpjpy_reversion | range_tight | 7 | 57.1 | 25.0 | 12.8 | -5.99 | 0.17 |
| gotobi_fix | range_tight | 6 | 50.0 | 18.8 | 9.0 | -3.02 | 0.30 |
| orb_trap | range_tight | 6 | 16.7 | 3.0 | 1.2 | -7.37 | 0.19 |
| mtf_reversal_confluence | range_tight | 6 | 50.0 | 18.8 | 9.0 | -1.07 | 0.41 |
| ny_close_reversal | range_wide | 6 | 50.0 | 18.8 | 9.0 | -0.72 | 0.86 |
| vdr_jpy | range_wide | 6 | 66.7 | 30.0 | 15.2 | -5.03 | 0.55 |
| inducement_ob | range_wide | 6 | 16.7 | 3.0 | 1.2 | -1.32 | 0.76 |
| intraday_seasonality | range_wide | 6 | 66.7 | 30.0 | 15.2 | +7.45 | 11.90 |
| turtle_soup | range_tight | 6 | 66.7 | 30.0 | 15.2 | -1.77 | 0.37 |
| inducement_ob | range_tight | 6 | 100.0 | 61.0 | 32.7 | +7.07 | ∞ |
| usdjpy_carry_dip_accumulator | range_tight | 5 | 80.0 | 37.6 | 18.7 | +12.70 | 6.93 |
| tokyo_nakane_momentum | range_tight | 5 | 60.0 | 23.1 | 10.9 | -6.88 | 0.13 |
| mtf_counter_trend_scalp | range_wide | 5 | 0.0 | 0.0 | 0.0 | -4.98 | 0.00 |
| vsg_jpy_reversal | range_wide | 5 | 60.0 | 23.1 | 10.9 | +0.24 | 1.11 |
| macdh_reversal | range_tight | 5 | 60.0 | 23.1 | 10.9 | -0.22 | 0.92 |

**Re-enable 閾値 (Wilson_BF_lower ≥ 0.50 AND N ≥ 50) を満たす cell: 0 / 114**
