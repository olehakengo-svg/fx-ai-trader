# W3-1 H1 Hour-Bucket Counterfactual (3-month Render window)

- Generated: 2026-05-03
- Source: `/tmp/trades.json` Render `/api/demo/trades` dump; `/tmp/oanda_control.json`; `/tmp/oanda_audit.json`. Fresh Render fetch was attempted but DNS failed in this sandbox.
- Requested window: last 90 days from 2026-05-03 UTC; available Render dump range: 2026-04-02T08:18:04.028405+00:00 to 2026-05-01T16:02:18.686920+00:00.
- LIVE filter: `status=CLOSED`, `outcome in (WIN, LOSS)`, `pnl_pips != null`, `is_shadow=0`.
- Orphan check: `pgrep -f app.py` was attempted first and failed with `sysmond service not found`; no process list was available and no process was killed.
- OANDA audit disambiguation: bridge_status counts `{'skipped': 445, 'sent': 11, 'filled': 13, 'blocked': 31}`; `sent` strategy names=`['fib_reversal', 'gbp_deep_pullback', 'session_time_bias', 'streak_reversal', 'xs_momentum']`; `filled` mode names=`['daytrade', 'daytrade_gbpusd', 'scalp']`.
- Grandfather exclusion applied before `would_demote`: bb_rsi_reversion, gbp_deep_pullback, session_time_bias, trendline_sweep, bb_squeeze_breakout, doji_breakout, ema200_trend_reversal, squeeze_release_momentum, streak_reversal, vix_carry_unwind, vol_momentum_scalp, wick_imbalance_reversion, xs_momentum.
- Final thresholds: `H1_GATE_MIN_N=30`, `H1_GATE_WILSON_LO=0.4`, `H1_GATE_EV_CI_LO=0.0`.

## Summary

| metric | value |
|---|---:|
| LIVE trades evaluated | 454 |
| bucket cells evaluated | 81 |
| LIVE cells with N>=30 | 3 |
| would_demote after grandfather exclusion | 0 |
| false_demotion_rate | 0.0000 |

## Cells With N>=30

| strategy | pair | bucket | N | win_rate | Wilson lo | EV CI lo | current_tier | grandfathered | would_demote |
|---|---|---|---:|---:|---:|---:|---|---|---|
| bb_rsi_reversion | USD_JPY | A | 82 | 48.8% | 38.3% | -0.95 | sentinel/demoted | yes | false |
| bb_rsi_reversion | USD_JPY | B | 61 | 42.6% | 31.0% | -0.92 | sentinel/demoted | yes | false |
| bb_rsi_reversion | USD_JPY | C | 64 | 48.4% | 36.6% | -1.04 | sentinel/demoted | yes | false |

## All LIVE Bucket Cells

| strategy | pair | bucket | N | win_rate | Wilson lo | EV CI lo | current_tier | grandfathered | would_demote |
|---|---|---|---:|---:|---:|---:|---|---|---|
| bb_rsi_reversion | EUR_USD | A | 9 | 44.4% | 18.9% | -3.96 | demoted/demoted | yes | false |
| bb_rsi_reversion | EUR_USD | B | 19 | 36.8% | 19.1% | -2.33 | demoted/demoted | yes | false |
| bb_rsi_reversion | EUR_USD | C | 29 | 41.4% | 25.5% | -1.89 | demoted/demoted | yes | false |
| bb_rsi_reversion | EUR_USD | D | 2 | 0.0% | 0.0% | -2.92 | demoted/demoted | yes | false |
| bb_rsi_reversion | GBP_USD | B | 1 | 0.0% | 0.0% | -6.00 | demoted/demoted | yes | false |
| bb_rsi_reversion | GBP_USD | C | 4 | 50.0% | 15.0% | -7.27 | demoted/demoted | yes | false |
| bb_rsi_reversion | USD_JPY | A | 82 | 48.8% | 38.3% | -0.95 | sentinel/demoted | yes | false |
| bb_rsi_reversion | USD_JPY | B | 61 | 42.6% | 31.0% | -0.92 | sentinel/demoted | yes | false |
| bb_rsi_reversion | USD_JPY | C | 64 | 48.4% | 36.6% | -1.04 | sentinel/demoted | yes | false |
| bb_rsi_reversion | USD_JPY | D | 24 | 45.8% | 27.9% | -2.39 | sentinel/demoted | yes | false |
| bb_rsi_reversion | XAU_USD | B | 2 | 50.0% | 9.5% | -428.84 | sentinel/demoted | yes | false |
| doji_breakout | EUR_USD | B | 1 | 0.0% | 0.0% | -10.60 | sentinel/pending | yes | false |
| doji_breakout | USD_JPY | B | 1 | 100.0% | 20.7% | +12.40 | promoted/pending | yes | false |
| doji_breakout | USD_JPY | C | 1 | 100.0% | 20.7% | +9.20 | promoted/pending | yes | false |
| donchian_momentum_breakout | EUR_USD | B | 4 | 25.0% | 4.6% | -29.20 | active/active | no | false |
| donchian_momentum_breakout | EUR_USD | C | 2 | 50.0% | 9.5% | -12.06 | active/active | no | false |
| dt_fib_reversal | USD_JPY | A | 1 | 0.0% | 0.0% | -6.80 | ?/? | no | false |
| dt_sr_channel_reversal | EUR_JPY | B | 1 | 100.0% | 20.7% | +12.40 | ?/? | no | false |
| dt_sr_channel_reversal | GBP_JPY | B | 1 | 100.0% | 20.7% | +12.70 | ?/? | no | false |
| dt_sr_channel_reversal | GBP_USD | C | 2 | 0.0% | 0.0% | -11.07 | ?/? | no | false |
| dt_sr_channel_reversal | GBP_USD | D | 2 | 0.0% | 0.0% | -9.96 | ?/? | no | false |
| dt_sr_channel_reversal | USD_JPY | A | 2 | 50.0% | 9.5% | -11.78 | ?/? | no | false |
| dt_sr_channel_reversal | USD_JPY | B | 1 | 100.0% | 20.7% | +0.70 | ?/? | no | false |
| dt_sr_channel_reversal | USD_JPY | C | 1 | 100.0% | 20.7% | +16.30 | ?/? | no | false |
| ema200_trend_reversal | USD_JPY | C | 1 | 0.0% | 0.0% | -8.00 | ?/? | yes | false |
| ema200_trend_reversal | USD_JPY | D | 1 | 0.0% | 0.0% | -8.90 | ?/? | yes | false |
| gbp_deep_pullback | GBP_USD | B | 3 | 66.7% | 20.8% | -22.58 | active/pending | yes | false |
| gold_trend_momentum | XAU_USD | C | 3 | 66.7% | 20.8% | -1134.57 | ?/? | no | false |
| htf_false_breakout | EUR_USD | C | 1 | 100.0% | 20.7% | +2.00 | elite/active | no | false |
| liquidity_sweep | EUR_USD | C | 1 | 100.0% | 20.7% | +10.60 | ?/? | no | false |
| mtf_reversal_confluence | EUR_USD | A | 1 | 100.0% | 20.7% | +1.20 | active/active | no | false |
| mtf_reversal_confluence | EUR_USD | C | 2 | 0.0% | 0.0% | -4.15 | active/active | no | false |
| mtf_reversal_confluence | GBP_USD | C | 1 | 0.0% | 0.0% | -6.70 | active/active | no | false |
| mtf_reversal_confluence | USD_JPY | B | 1 | 100.0% | 20.7% | +1.20 | active/active | no | false |
| mtf_reversal_confluence | USD_JPY | C | 3 | 66.7% | 20.8% | -0.88 | active/active | no | false |
| mtf_reversal_confluence | USD_JPY | D | 1 | 100.0% | 20.7% | +3.20 | active/active | no | false |
| post_news_vol | GBP_USD | B | 2 | 50.0% | 9.5% | -11.28 | force_demoted/force_demoted | no | false |
| post_news_vol | USD_JPY | A | 2 | 50.0% | 9.5% | -9.98 | demoted/force_demoted | no | false |
| session_time_bias | GBP_USD | B | 6 | 33.3% | 9.7% | -6.66 | active/pending | yes | false |
| session_time_bias | GBP_USD | C | 2 | 0.0% | 0.0% | -5.59 | active/pending | yes | false |
| session_time_bias | GBP_USD | D | 1 | 0.0% | 0.0% | -12.90 | active/pending | yes | false |
| squeeze_release_momentum | GBP_USD | A | 1 | 0.0% | 0.0% | -5.10 | ?/? | yes | false |
| squeeze_release_momentum | GBP_USD | B | 1 | 0.0% | 0.0% | -6.10 | ?/? | yes | false |
| streak_reversal | USD_JPY | B | 1 | 0.0% | 0.0% | -23.40 | promoted/pending | yes | false |
| three_bar_reversal | USD_JPY | A | 1 | 0.0% | 0.0% | -3.20 | ?/? | no | false |
| three_bar_reversal | USD_JPY | C | 1 | 100.0% | 20.7% | +4.60 | ?/? | no | false |
| trend_rebound | EUR_USD | B | 6 | 16.7% | 3.0% | -3.75 | ?/? | no | false |
| trend_rebound | EUR_USD | C | 1 | 100.0% | 20.7% | +4.30 | ?/? | no | false |
| trend_rebound | GBP_USD | C | 1 | 0.0% | 0.0% | -7.10 | ?/? | no | false |
| trend_rebound | USD_JPY | A | 2 | 50.0% | 9.5% | -7.34 | ?/? | no | false |
| trend_rebound | USD_JPY | B | 3 | 33.3% | 6.1% | -5.64 | ?/? | no | false |
| trend_rebound | USD_JPY | C | 1 | 0.0% | 0.0% | -3.00 | ?/? | no | false |
| trend_rebound | USD_JPY | D | 2 | 50.0% | 9.5% | -5.32 | ?/? | no | false |
| trendline_sweep | EUR_GBP | A | 1 | 0.0% | 0.0% | -6.20 | active/pending | yes | false |
| trendline_sweep | GBP_USD | B | 3 | 33.3% | 6.1% | -5.05 | active/pending | yes | false |
| trendline_sweep | GBP_USD | D | 1 | 0.0% | 0.0% | -23.60 | active/pending | yes | false |
| v_reversal | USD_JPY | B | 1 | 0.0% | 0.0% | -3.00 | ?/? | no | false |
| v_reversal | USD_JPY | C | 2 | 0.0% | 0.0% | -4.43 | ?/? | no | false |
| vix_carry_unwind | USD_JPY | A | 2 | 50.0% | 9.5% | -38.20 | promoted/pending | yes | false |
| vix_carry_unwind | USD_JPY | B | 3 | 33.3% | 6.1% | -26.50 | promoted/pending | yes | false |
| vol_momentum_scalp | USD_JPY | A | 2 | 50.0% | 9.5% | -8.23 | active/active | yes | false |
| vol_momentum_scalp | USD_JPY | B | 6 | 66.7% | 30.0% | -2.46 | active/active | yes | false |
| vol_momentum_scalp | USD_JPY | C | 5 | 40.0% | 11.8% | -3.99 | active/active | yes | false |
| vol_momentum_scalp | USD_JPY | D | 2 | 50.0% | 9.5% | -7.38 | active/active | yes | false |
| vol_surge_detector | EUR_USD | B | 4 | 50.0% | 15.0% | -3.75 | sentinel/active | no | false |
| vol_surge_detector | EUR_USD | C | 3 | 66.7% | 20.8% | -4.64 | sentinel/active | no | false |
| vol_surge_detector | GBP_USD | B | 1 | 0.0% | 0.0% | -3.90 | sentinel/active | no | false |
| vol_surge_detector | GBP_USD | C | 1 | 100.0% | 20.7% | +1.00 | sentinel/active | no | false |
| vol_surge_detector | USD_JPY | A | 9 | 11.1% | 2.0% | -5.13 | sentinel/active | no | false |
| vol_surge_detector | USD_JPY | B | 15 | 46.7% | 24.8% | -1.46 | sentinel/active | no | false |
| vol_surge_detector | USD_JPY | C | 9 | 77.8% | 45.3% | -1.17 | sentinel/active | no | false |
| vol_surge_detector | XAU_USD | B | 1 | 100.0% | 20.7% | +10.00 | sentinel/active | no | false |
| vwap_mean_reversion | EUR_JPY | B | 1 | 0.0% | 0.0% | -22.60 | promoted/pending | no | false |
| vwap_mean_reversion | EUR_JPY | C | 3 | 66.7% | 20.8% | -9.95 | promoted/pending | no | false |
| vwap_mean_reversion | GBP_JPY | B | 1 | 100.0% | 20.7% | +44.20 | promoted/pending | no | false |
| vwap_mean_reversion | GBP_JPY | C | 1 | 0.0% | 0.0% | -20.10 | promoted/pending | no | false |
| vwap_mean_reversion | GBP_USD | B | 3 | 33.3% | 6.1% | -23.12 | promoted/pending | no | false |
| vwap_mean_reversion | GBP_USD | C | 1 | 0.0% | 0.0% | -14.10 | promoted/pending | no | false |
| xs_momentum | GBP_USD | C | 1 | 100.0% | 20.7% | +22.20 | promoted/pending | yes | false |
| xs_momentum | USD_JPY | B | 1 | 0.0% | 0.0% | -11.90 | demoted/pending | yes | false |
| xs_momentum | USD_JPY | C | 1 | 0.0% | 0.0% | -10.50 | demoted/pending | yes | false |
