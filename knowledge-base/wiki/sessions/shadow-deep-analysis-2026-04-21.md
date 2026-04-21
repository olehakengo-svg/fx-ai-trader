# Shadow Deep Analysis (Tasks 1-4)

- Total shadow trades (is_shadow=1, outcome, XAU excluded): **1711**
- WIN: 474, LOSS: 1237
- Baseline WR: **27.70%**

- Distinct strategies with shadow data: **44**

## Deliverable 1: All-strategy Top WIN cell (pair × session × direction)

| Strategy | N | WR | Top cell | cell N | cell WR | Lift | Wilson 下限 | BEV | Wilson>BEV? |
|---|---:|---:|---|---:|---:|---:|---:|---:|:---:|
| ema_trend_scalp | 295 | 23.4% | GBP_USD×london×BUY | 6 | 50.0% | 2.14x | 18.8% | 36.0% | ✗ |
| fib_reversal | 187 | 35.3% | USD_JPY×london×BUY | 12 | 58.3% | 1.65x | 32.0% | 34.4% | ✗ |
| stoch_trend_pullback | 142 | 28.9% | EUR_USD×london×BUY | 8 | 50.0% | 1.73x | 21.5% | 36.0% | ✗ |
| bb_rsi_reversion | 128 | 28.9% | EUR_USD×ny×BUY | 5 | 80.0% | 2.77x | 37.6% | 36.0% | ✓ |
| sr_channel_reversal | 126 | 23.8% | GBP_USD×ny×SELL | 6 | 33.3% | 1.40x | 9.7% | 36.0% | ✗ |
| macdh_reversal | 109 | 27.5% | EUR_USD×ny×SELL | 6 | 50.0% | 1.82x | 18.8% | 36.0% | ✗ |
| sr_fib_confluence | 102 | 24.5% | GBP_USD×london×BUY | 14 | 50.0% | 2.04x | 26.8% | 36.0% | ✗ |
| engulfing_bb | 101 | 31.7% | USD_JPY×tokyo×BUY | 10 | 40.0% | 1.26x | 16.8% | 34.4% | ✗ |
| bb_squeeze_breakout | 83 | 25.3% | USD_JPY×ny×SELL | 8 | 50.0% | 1.98x | 21.5% | 34.4% | ✗ |
| ema_cross | 46 | 34.8% | USD_JPY×ny×SELL | 24 | 50.0% | 1.44x | 31.4% | 34.4% | ✗ |
| vol_surge_detector | 41 | 24.4% | USD_JPY×london×SELL | 5 | 60.0% | 2.46x | 23.1% | 34.4% | ✗ |
| dt_sr_channel_reversal | 38 | 31.6% | USD_JPY×london×BUY | 5 | 60.0% | 1.90x | 23.1% | 34.4% | ✗ |
| ema_pullback | 36 | 36.1% | USD_JPY×ny×SELL | 8 | 62.5% | 1.73x | 30.6% | 34.4% | ✗ |
| dt_bb_rsi_mr | 35 | 45.7% | GBP_USD×tokyo×BUY | 5 | 60.0% | 1.31x | 23.1% | 36.0% | ✗ |
| sr_break_retest | 24 | 12.5% | USD_JPY×tokyo×BUY | 6 | 16.7% | 1.33x | 3.0% | 34.4% | ✗ |
| trend_rebound | 22 | 40.9% | USD_JPY×ny×BUY | 3 | 66.7% | 1.63x | 20.8% | 34.4% | ✗ |
| dual_sr_bounce | 22 | 9.1% | USD_JPY×ny×BUY | 6 | 16.7% | 1.83x | 3.0% | 34.4% | ✗ |
| ema200_trend_reversal | 20 | 40.0% | USD_JPY×ny×SELL | 6 | 66.7% | 1.67x | 30.0% | 34.4% | ✗ |
| vol_momentum_scalp | 19 | 10.5% | GBP_USD×london×BUY | 7 | 14.3% | 1.36x | 2.6% | 36.0% | ✗ |
| xs_momentum | 14 | 21.4% | GBP_USD×ny×BUY | 6 | 50.0% | 2.33x | 18.8% | 36.0% | ✗ |
| v_reversal | 13 | 23.1% | USD_JPY×ny×BUY | 6 | 16.7% | 0.72x | 3.0% | 34.4% | ✗ |
| vwap_mean_reversion | 11 | 9.1% | USD_JPY×tokyo×BUY | 3 | 0.0% | 0.00x | 0.0% | 34.4% | ✗ |
| inducement_ob | 10 | 10.0% | EUR_GBP×ny×BUY | 4 | 0.0% | 0.00x | 0.0% | 36.0% | ✗ |
| ema_ribbon_ride | 10 | 20.0% | - | - | - | - | - | - | - |
| trendline_sweep | 8 | 37.5% | - | - | - | - | - | - | - |
| dt_fib_reversal | 7 | 28.6% | - | - | - | - | - | - | - |
| orb_trap | 7 | 57.1% | - | - | - | - | - | - | - |
| post_news_vol | 7 | 57.1% | GBP_USD×tokyo×BUY | 3 | 33.3% | 0.58x | 6.1% | 36.0% | ✗ |
| vix_carry_unwind | 6 | 33.3% | USD_JPY×tokyo×SELL | 5 | 20.0% | 0.60x | 3.6% | 34.4% | ✗ |
| pivot_breakout | 5 | 40.0% | USD_JPY×ny×BUY | 5 | 40.0% | 1.00x | 11.8% | 34.4% | ✗ |
| h1_fib_reversal | 5 | 20.0% | USD_JPY×london×SELL | 5 | 20.0% | 1.00x | 3.6% | 34.4% | ✗ |
| doji_breakout | 4 | 25.0% | - | - | - | - | - | - | - |
| ny_close_reversal | 4 | 25.0% | USD_JPY×ny×SELL | 4 | 25.0% | 1.00x | 4.6% | 34.4% | ✗ |
| streak_reversal | 4 | 0.0% | USD_JPY×tokyo×SELL | 3 | 0.0% | 0.00x | 0.0% | 34.4% | ✗ |
| lin_reg_channel | 4 | 25.0% | - | - | - | - | - | - | - |
| squeeze_release_momentum | 3 | 33.3% | - | - | - | - | - | - | - |
| vol_spike_mr | 3 | 0.0% | - | - | - | - | - | - | - |
| wick_imbalance_reversion | 2 | 0.0% | - | - | - | - | - | - | - |
| session_time_bias | 2 | 0.0% | - | - | - | - | - | - | - |
| donchian_momentum_breakout | 2 | 0.0% | - | - | - | - | - | - | - |
| intraday_seasonality | 1 | 0.0% | - | - | - | - | - | - | - |
| mtf_reversal_confluence | 1 | 0.0% | - | - | - | - | - | - | - |
| three_bar_reversal | 1 | 0.0% | - | - | - | - | - | - | - |
| htf_false_breakout | 1 | 0.0% | - | - | - | - | - | - | - |

## Deliverable 2: Branch 1 — Threshold adjustment / LIVE promotion candidates

Gate criteria: cell N≥10, cell WR≥50%, Lift≥1.5, Wilson≥95%下限>BEV

| Strategy | Cell (pair×session×dir) | N | WR | Lift | Wilson下限 | BEV | Fisher p | Pass? |
|---|---|---:|---:|---:|---:|---:|---:|:---:|
| fib_reversal | USD_JPY×london×BUY | 12 | 58.3% | 1.65x | 32.0% | 34.4% | 0.1172 | ✗ |
| sr_fib_confluence | GBP_USD×london×BUY | 14 | 50.0% | 2.04x | 26.8% | 36.0% | 0.0386 | ✗ |

(no cells pass all 4 gates — mostly N insufficient; continue shadow accumulation)


## Deliverable 3: Branch 2 — LOSS-exclusion → WIN conversion (ALL strategies)

CORE QUESTION: LOSS条件排除後の WR ≥ 50% か?

| Strategy | baseline N | base WR | Excluded cells | N_post | WR_post | Wilson下限 | Verdict | 新戦略名候補 |
|---|---:|---:|---|---:|---:|---:|---|---|
| ema_trend_scalp | 295 | 23.4% | GBP_USD×tokyo×SELL, GBP_USD×london×SELL, USD_JPY×tokyo×BUY, EUR_USD×london×SE... | 228 | 28.1% | 22.6% | UNSALVAGEABLE | - |
| fib_reversal | 187 | 35.3% | USD_JPY×london×SELL | 176 | 36.4% | 29.6% | UNSALVAGEABLE | - |
| stoch_trend_pullback | 142 | 28.9% | USD_JPY×ny×SELL | 117 | 32.5% | 24.7% | UNSALVAGEABLE | - |
| bb_rsi_reversion | 128 | 28.9% | EUR_USD×london×SELL, USD_JPY×tokyo×SELL | 105 | 34.3% | 25.9% | UNSALVAGEABLE | - |
| sr_channel_reversal | 126 | 23.8% | USD_JPY×tokyo×BUY | 111 | 25.2% | 18.1% | UNSALVAGEABLE | - |
| macdh_reversal | 109 | 27.5% | EUR_USD×tokyo×BUY, USD_JPY×tokyo×BUY | 93 | 30.1% | 21.7% | UNSALVAGEABLE | - |
| sr_fib_confluence | 102 | 24.5% | EUR_JPY×tokyo×BUY, USD_JPY×tokyo×SELL, EUR_JPY×london×BUY | 84 | 29.8% | 21.0% | UNSALVAGEABLE | - |
| engulfing_bb | 101 | 31.7% | USD_JPY×london×BUY | 93 | 33.3% | 24.6% | UNSALVAGEABLE | - |
| bb_squeeze_breakout | 83 | 25.3% | EUR_USD×ny×SELL, USD_JPY×london×BUY, EUR_USD×london×BUY | 63 | 31.7% | 21.6% | UNSALVAGEABLE | - |
| ema_cross | 46 | 34.8% | USD_JPY×london×BUY | 35 | 40.0% | 25.6% | MARGINAL_IMPROVEMENT | - |
| vol_surge_detector | 41 | 24.4% | USD_JPY×tokyo×SELL | 31 | 29.0% | 16.1% | UNSALVAGEABLE | - |
| dt_sr_channel_reversal | 38 | 31.6% | - | 38 | 31.6% | 19.1% | UNSALVAGEABLE | - |
| ema_pullback | 36 | 36.1% | - | 36 | 36.1% | 22.5% | UNSALVAGEABLE | - |
| dt_bb_rsi_mr | 35 | 45.7% | - | 35 | 45.7% | 30.5% | MARGINAL_IMPROVEMENT | - |
| sr_break_retest | 24 | 12.5% | USD_JPY×london×BUY | 19 | 15.8% | 5.5% | INSUFFICIENT_N_POST | - |
| trend_rebound | 22 | 40.9% | - | 22 | 40.9% | 23.3% | NEEDS_MORE_DATA | - |
| dual_sr_bounce | 22 | 9.1% | - | 22 | 9.1% | 2.5% | NEEDS_MORE_DATA | - |
| ema200_trend_reversal | 20 | 40.0% | - | 20 | 40.0% | 21.9% | NEEDS_MORE_DATA | - |
| vol_momentum_scalp | 19 | 10.5% | - | 19 | 10.5% | 2.9% | INSUFFICIENT_N_POST | - |
| xs_momentum | 14 | 21.4% | - | 14 | 21.4% | 7.6% | INSUFFICIENT_N_POST | - |
| v_reversal | 13 | 23.1% | - | 13 | 23.1% | 8.2% | INSUFFICIENT_N_POST | - |
| vwap_mean_reversion | 11 | 9.1% | - | 11 | 9.1% | 1.6% | INSUFFICIENT_N_POST | - |
| inducement_ob | 10 | 10.0% | - | 10 | 10.0% | 1.8% | INSUFFICIENT_N_POST | - |
| ema_ribbon_ride | 10 | 20.0% | - | 10 | 20.0% | 5.7% | INSUFFICIENT_N_POST | - |
| trendline_sweep | 8 | 37.5% | - | 8 | 37.5% | 13.7% | INSUFFICIENT_N_POST | - |
| dt_fib_reversal | 7 | 28.6% | - | 7 | 28.6% | 8.2% | INSUFFICIENT_N_POST | - |
| orb_trap | 7 | 57.1% | - | 7 | 57.1% | 25.0% | INSUFFICIENT_N_POST | - |
| post_news_vol | 7 | 57.1% | - | 7 | 57.1% | 25.0% | INSUFFICIENT_N_POST | - |
| vix_carry_unwind | 6 | 33.3% | - | 6 | 33.3% | 9.7% | INSUFFICIENT_N_POST | - |
| pivot_breakout | 5 | 40.0% | - | 5 | 40.0% | 11.8% | INSUFFICIENT_N_POST | - |
| h1_fib_reversal | 5 | 20.0% | - | 5 | 20.0% | 3.6% | INSUFFICIENT_N_POST | - |
| doji_breakout | 4 | 25.0% | - | 4 | 25.0% | 4.6% | INSUFFICIENT_N_POST | - |
| ny_close_reversal | 4 | 25.0% | - | 4 | 25.0% | 4.6% | INSUFFICIENT_N_POST | - |
| streak_reversal | 4 | 0.0% | - | 4 | 0.0% | 0.0% | INSUFFICIENT_N_POST | - |
| lin_reg_channel | 4 | 25.0% | - | 4 | 25.0% | 4.6% | INSUFFICIENT_N_POST | - |
| squeeze_release_momentum | 3 | 33.3% | - | 3 | 33.3% | 6.1% | INSUFFICIENT_N_POST | - |
| vol_spike_mr | 3 | 0.0% | - | 3 | 0.0% | 0.0% | INSUFFICIENT_N_POST | - |
| wick_imbalance_reversion | 2 | 0.0% | - | 2 | 0.0% | 0.0% | INSUFFICIENT_N_POST | - |
| session_time_bias | 2 | 0.0% | - | 2 | 0.0% | 0.0% | INSUFFICIENT_N_POST | - |
| donchian_momentum_breakout | 2 | 0.0% | - | 2 | 0.0% | 0.0% | INSUFFICIENT_N_POST | - |
| intraday_seasonality | 1 | 0.0% | - | 1 | 0.0% | 0.0% | INSUFFICIENT_N_POST | - |
| mtf_reversal_confluence | 1 | 0.0% | - | 1 | 0.0% | 0.0% | INSUFFICIENT_N_POST | - |
| three_bar_reversal | 1 | 0.0% | - | 1 | 0.0% | 0.0% | INSUFFICIENT_N_POST | - |
| htf_false_breakout | 1 | 0.0% | - | 1 | 0.0% | 0.0% | INSUFFICIENT_N_POST | - |

**Summary**: NEW_STRATEGY=0, NEW_STRATEGY_TENTATIVE=0, MARGINAL=2, UNSALVAGEABLE=12, INSUFF_N=27, NEEDS_MORE=3


## Deliverable 4: SL-hit fingerprint (LOSS top 3 per strategy, N≥5)

| Strategy | Rank | Cell | N | cell WR | LOSS_LR |
|---|---:|---|---:|---:|---:|
| ema_trend_scalp | 1 | GBP_USD×tokyo×SELL | 11 | 0.0% | ∞ |
| ema_trend_scalp | 2 | GBP_USD×london×SELL | 8 | 0.0% | ∞ |
| ema_trend_scalp | 3 | USD_JPY×tokyo×BUY | 14 | 7.1% | 3.97 |
| fib_reversal | 1 | USD_JPY×london×SELL | 11 | 18.2% | 2.45 |
| fib_reversal | 2 | USD_JPY×tokyo×BUY | 17 | 23.5% | 1.77 |
| fib_reversal | 3 | USD_JPY×ny×SELL | 24 | 29.2% | 1.32 |
| stoch_trend_pullback | 1 | USD_JPY×ny×SELL | 25 | 12.0% | 2.98 |
| stoch_trend_pullback | 2 | EUR_USD×ny×BUY | 5 | 20.0% | 1.62 |
| stoch_trend_pullback | 3 | USD_JPY×tokyo×SELL | 19 | 26.3% | 1.14 |
| bb_rsi_reversion | 1 | EUR_USD×london×SELL | 11 | 0.0% | ∞ |
| bb_rsi_reversion | 2 | USD_JPY×tokyo×SELL | 12 | 8.3% | 4.47 |
| bb_rsi_reversion | 3 | USD_JPY×tokyo×BUY | 18 | 22.2% | 1.42 |
| sr_channel_reversal | 1 | USD_JPY×tokyo×BUY | 15 | 13.3% | 2.03 |
| sr_channel_reversal | 2 | USD_JPY×tokyo×SELL | 16 | 18.8% | 1.35 |
| sr_channel_reversal | 3 | EUR_USD×ny×SELL | 10 | 20.0% | 1.25 |
| macdh_reversal | 1 | EUR_USD×tokyo×BUY | 9 | 11.1% | 3.04 |
| macdh_reversal | 2 | USD_JPY×tokyo×BUY | 7 | 14.3% | 2.28 |
| macdh_reversal | 3 | USD_JPY×ny×SELL | 15 | 20.0% | 1.52 |
| sr_fib_confluence | 1 | EUR_JPY×tokyo×BUY | 7 | 0.0% | ∞ |
| sr_fib_confluence | 2 | USD_JPY×tokyo×SELL | 6 | 0.0% | ∞ |
| sr_fib_confluence | 3 | EUR_JPY×london×BUY | 5 | 0.0% | ∞ |
| engulfing_bb | 1 | USD_JPY×london×BUY | 8 | 12.5% | 3.25 |
| engulfing_bb | 2 | EUR_USD×london×SELL | 5 | 20.0% | 1.86 |
| engulfing_bb | 3 | USD_JPY×ny×BUY | 20 | 25.0% | 1.39 |
| bb_squeeze_breakout | 1 | EUR_USD×ny×SELL | 7 | 0.0% | ∞ |
| bb_squeeze_breakout | 2 | USD_JPY×london×BUY | 6 | 0.0% | ∞ |
| bb_squeeze_breakout | 3 | EUR_USD×london×BUY | 7 | 14.3% | 2.03 |
| ema_cross | 1 | USD_JPY×london×BUY | 11 | 18.2% | 2.40 |
| ema_cross | 2 | USD_JPY×ny×SELL | 24 | 50.0% | 0.53 |
| vol_surge_detector | 1 | USD_JPY×tokyo×SELL | 10 | 10.0% | 2.90 |
| vol_surge_detector | 2 | USD_JPY×tokyo×BUY | 9 | 33.3% | 0.65 |
| vol_surge_detector | 3 | USD_JPY×london×SELL | 5 | 60.0% | 0.22 |
| dt_sr_channel_reversal | 1 | USD_JPY×london×BUY | 5 | 60.0% | 0.31 |
| ema_pullback | 1 | USD_JPY×london×SELL | 7 | 28.6% | 1.41 |
| ema_pullback | 2 | USD_JPY×ny×BUY | 7 | 42.9% | 0.75 |
| ema_pullback | 3 | USD_JPY×ny×SELL | 8 | 62.5% | 0.34 |
| dt_bb_rsi_mr | 1 | USD_JPY×london×SELL | 6 | 50.0% | 0.84 |
| dt_bb_rsi_mr | 2 | GBP_USD×tokyo×BUY | 5 | 60.0% | 0.56 |
| sr_break_retest | 1 | USD_JPY×london×BUY | 5 | 0.0% | ∞ |
| sr_break_retest | 2 | USD_JPY×tokyo×BUY | 6 | 16.7% | 0.71 |
| trend_rebound | - | (no cell N≥5) | - | - | - |
| dual_sr_bounce | 1 | USD_JPY×ny×BUY | 6 | 16.7% | 0.50 |
| ema200_trend_reversal | 1 | USD_JPY×ny×SELL | 6 | 66.7% | 0.33 |
| vol_momentum_scalp | 1 | GBP_USD×london×BUY | 7 | 14.3% | 0.71 |
| xs_momentum | 1 | GBP_USD×ny×BUY | 6 | 50.0% | 0.27 |
| v_reversal | 1 | USD_JPY×ny×BUY | 6 | 16.7% | 1.50 |
| vwap_mean_reversion | - | (no cell N≥5) | - | - | - |
| inducement_ob | - | (no cell N≥5) | - | - | - |
| ema_ribbon_ride | - | (no cell N≥5) | - | - | - |
| trendline_sweep | - | (no cell N≥5) | - | - | - |
| dt_fib_reversal | - | (no cell N≥5) | - | - | - |
| orb_trap | - | (no cell N≥5) | - | - | - |
| post_news_vol | - | (no cell N≥5) | - | - | - |
| vix_carry_unwind | 1 | USD_JPY×tokyo×SELL | 5 | 20.0% | 2.00 |
| pivot_breakout | 1 | USD_JPY×ny×BUY | 5 | 40.0% | 1.00 |
| h1_fib_reversal | 1 | USD_JPY×london×SELL | 5 | 20.0% | 1.00 |
| doji_breakout | - | (no cell N≥5) | - | - | - |
| ny_close_reversal | - | (no cell N≥5) | - | - | - |
| streak_reversal | - | (no cell N≥5) | - | - | - |
| lin_reg_channel | - | (no cell N≥5) | - | - | - |
| squeeze_release_momentum | - | (no cell N≥5) | - | - | - |
| vol_spike_mr | - | (no cell N≥5) | - | - | - |
| wick_imbalance_reversion | - | (no cell N≥5) | - | - | - |
| session_time_bias | - | (no cell N≥5) | - | - | - |
| donchian_momentum_breakout | - | (no cell N≥5) | - | - | - |
| intraday_seasonality | - | (no cell N≥5) | - | - | - |
| mtf_reversal_confluence | - | (no cell N≥5) | - | - | - |
| three_bar_reversal | - | (no cell N≥5) | - | - | - |
| htf_false_breakout | - | (no cell N≥5) | - | - | - |
