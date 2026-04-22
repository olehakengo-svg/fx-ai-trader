# Walk-Forward Stability Scan

- **Generated**: 2026-04-22 15:39 UTC
- **Window size**: 60 days (rolling)
- **Verdict thresholds**:
  - **stable**: positive_ratio ≥ 0.67 AND CV(EV) < 1.0
  - **borderline**: positive_ratio ≥ 0.5
  - **unstable**: 上記どちらも満たさない

## Cross-Pair Strategy Stability
| Pair | Strategy | N | Overall EV | Windows | Pos.ratio | CV(EV) | Min/Max EV | Verdict |
|------|----------|--:|-----------:|--------:|----------:|-------:|:-----------|:-------:|
| GBP_USD | xs_momentum | 274 | -0.191 | 6 | 0.33 | 1.27 | -0.62/+0.12 | 🔴 unstable |
| GBP_USD | sr_fib_confluence | 257 | -0.054 | 6 | 0.33 | 3.23 | -0.30/+0.28 | 🔴 unstable |
| EUR_JPY | sr_break_retest | 171 | -0.009 | 6 | 0.33 | 5.73 | -0.70/+0.36 | 🔴 unstable |
| GBP_JPY | dt_sr_channel_reversal | 161 | -0.084 | 6 | 0.33 | 1.54 | -0.32/+0.04 | 🔴 unstable |
| USD_JPY | sr_fib_confluence | 158 | +0.000 | 6 | 0.33 | 12.49 | -0.13/+0.29 | 🔴 unstable |
| GBP_USD | dt_bb_rsi_mr | 117 | -0.220 | 6 | 0.33 | 1.63 | -0.50/+0.25 | 🔴 unstable |
| USD_JPY | dt_bb_rsi_mr | 103 | -0.251 | 6 | 0.00 | 0.60 | -0.61/-0.12 | 🔴 unstable |
| EUR_JPY | dt_fib_reversal | 77 | -0.362 | 6 | 0.17 | 0.77 | -0.85/+0.08 | 🔴 unstable |
| EUR_USD | dt_bb_rsi_mr | 69 | -0.194 | 6 | 0.17 | 2.42 | -0.50/+0.40 | 🔴 unstable |
| GBP_USD | dual_sr_bounce | 68 | -0.204 | 6 | 0.17 | 1.70 | -0.65/+0.27 | 🔴 unstable |
| USD_JPY | dt_sr_channel_reversal | 67 | -0.328 | 6 | 0.33 | 1.37 | -1.11/+0.21 | 🔴 unstable |
| GBP_USD | dt_sr_channel_reversal | 66 | -0.070 | 6 | 0.33 | 3.93 | -0.70/+0.44 | 🔴 unstable |
| GBP_USD | intraday_seasonality | 63 | -0.236 | 5 | 0.00 | 1.12 | -0.71/-0.00 | 🔴 unstable |
| USD_JPY | london_fix_reversal | 54 | -0.138 | 5 | 0.40 | 2.39 | -1.03/+0.20 | 🔴 unstable |
| GBP_USD | london_fix_reversal | 53 | -0.345 | 6 | 0.00 | 0.56 | -0.62/+0.00 | 🔴 unstable |
| EUR_USD | london_fix_reversal | 52 | -0.052 | 6 | 0.33 | 5.01 | -0.50/+0.49 | 🔴 unstable |
| USD_JPY | wick_imbalance_reversion | 50 | -0.228 | 5 | 0.40 | 3.29 | -1.01/+0.97 | 🔴 unstable |
| GBP_USD | sr_break_retest | 48 | -0.461 | 6 | 0.00 | 0.91 | -1.48/-0.07 | 🔴 unstable |
| EUR_USD | intraday_seasonality | 45 | -0.216 | 5 | 0.40 | 2.01 | -0.80/+0.48 | 🔴 unstable |
| GBP_USD | ema200_trend_reversal | 39 | -0.225 | 5 | 0.20 | 2.10 | -0.95/+0.60 | 🔴 unstable |
| EUR_USD | dual_sr_bounce | 35 | -0.284 | 3 | 0.33 | 3.81 | -0.93/+0.58 | 🔴 unstable |
| EUR_JPY | htf_false_breakout | 34 | +0.087 | 3 | 0.33 | 18.56 | -0.45/+0.52 | 🔴 unstable |
| EUR_USD | dt_sr_channel_reversal | 33 | +0.007 | 5 | 0.40 | 40.53 | -0.29/+0.46 | 🔴 unstable |
| EUR_USD | wick_imbalance_reversion | 33 | -0.064 | 3 | 0.33 | 4.67 | -0.39/+0.50 | 🔴 unstable |
| EUR_USD | orb_trap | 32 | -0.379 | 3 | 0.33 | 7.70 | -0.42/+0.37 | 🔴 unstable |
| GBP_USD | dt_fib_reversal | 30 | -0.137 | 5 | 0.40 | 7.31 | -0.69/+0.61 | 🔴 unstable |
| GBP_USD | orb_trap | 28 | +0.112 | 3 | 0.33 | 3.83 | -0.64/+0.38 | 🔴 unstable |
| EUR_USD | session_time_bias | 403 | +0.151 | 6 | 0.83 | 1.10 | -0.17/+0.31 | 🟡 borderline |
| GBP_USD | session_time_bias | 393 | -0.054 | 6 | 0.50 | 3.25 | -0.44/+0.38 | 🟡 borderline |
| USD_JPY | xs_momentum | 309 | +0.081 | 6 | 0.67 | 2.32 | -0.24/+0.35 | 🟡 borderline |
| EUR_USD | sr_fib_confluence | 238 | -0.027 | 6 | 0.50 | 144.71 | -0.31/+0.20 | 🟡 borderline |
| EUR_USD | xs_momentum | 237 | +0.092 | 6 | 0.83 | 1.76 | -0.12/+0.39 | 🟡 borderline |
| GBP_JPY | sr_fib_confluence | 210 | +0.052 | 6 | 0.83 | 5.28 | -0.36/+0.23 | 🟡 borderline |
| EUR_JPY | sr_fib_confluence | 194 | +0.160 | 6 | 0.83 | 1.52 | -0.31/+0.46 | 🟡 borderline |
| EUR_JPY | dt_sr_channel_reversal | 185 | +0.021 | 6 | 0.67 | 2.57 | -0.19/+0.13 | 🟡 borderline |
| EUR_USD | vwap_mean_reversion | 165 | +0.980 | 6 | 0.67 | 1.09 | -0.05/+2.71 | 🟡 borderline |
| GBP_JPY | sr_break_retest | 164 | +0.040 | 6 | 0.50 | 12.11 | -0.38/+0.46 | 🟡 borderline |
| USD_JPY | vix_carry_unwind | 138 | +0.292 | 6 | 0.50 | 1.97 | -0.33/+1.15 | 🟡 borderline |
| GBP_JPY | dual_sr_bounce | 136 | +0.149 | 6 | 0.67 | 2.24 | -0.26/+0.42 | 🟡 borderline |
| GBP_JPY | intraday_seasonality | 119 | +0.069 | 6 | 0.83 | 6.91 | -0.92/+0.25 | 🟡 borderline |
| EUR_JPY | dual_sr_bounce | 118 | +0.188 | 6 | 0.83 | 1.14 | -0.12/+0.44 | 🟡 borderline |
| GBP_USD | trendline_sweep | 108 | +0.338 | 6 | 0.83 | 1.01 | -0.34/+0.92 | 🟡 borderline |
| GBP_USD | gbp_deep_pullback | 100 | +0.438 | 6 | 0.67 | 3.52 | -1.55/+1.62 | 🟡 borderline |
| EUR_JPY | wick_imbalance_reversion | 94 | +0.033 | 6 | 0.50 | 6.97 | -1.20/+0.85 | 🟡 borderline |
| GBP_JPY | wick_imbalance_reversion | 94 | +0.085 | 6 | 0.67 | 4.66 | -0.25/+0.36 | 🟡 borderline |
| EUR_JPY | intraday_seasonality | 88 | -0.030 | 6 | 0.50 | 13.52 | -0.53/+0.59 | 🟡 borderline |
| USD_JPY | vol_spike_mr | 85 | +0.129 | 6 | 0.50 | 2.07 | -0.17/+0.78 | 🟡 borderline |
| USD_JPY | intraday_seasonality | 74 | +0.056 | 6 | 0.50 | 10.78 | -0.67/+0.91 | 🟡 borderline |
| USD_JPY | dual_sr_bounce | 71 | -0.083 | 6 | 0.50 | 7.95 | -1.18/+1.06 | 🟡 borderline |
| GBP_JPY | dt_fib_reversal | 68 | +0.301 | 6 | 0.50 | 1.73 | -0.15/+0.97 | 🟡 borderline |
| EUR_USD | trendline_sweep | 56 | +0.576 | 6 | 1.00 | 1.05 | +0.02/+1.69 | 🟡 borderline |
| GBP_USD | turtle_soup | 50 | +0.530 | 5 | 0.60 | 1.19 | -0.05/+1.61 | 🟡 borderline |
| GBP_JPY | ema_cross | 46 | +0.273 | 5 | 0.80 | 1.60 | -0.43/+0.94 | 🟡 borderline |
| EUR_JPY | ema200_trend_reversal | 38 | -0.019 | 4 | 0.75 | 3.24 | -0.29/+0.52 | 🟡 borderline |
| EUR_JPY | ema_cross | 34 | -0.061 | 4 | 0.50 | 4.26 | -1.09/+0.57 | 🟡 borderline |
| USD_JPY | dt_fib_reversal | 29 | -0.028 | 3 | 0.67 | 2.79 | -0.17/+0.23 | 🟡 borderline |
| EUR_USD | lin_reg_channel | 29 | +0.006 | 2 | 0.50 | 1.15 | -0.49/+0.04 | 🟡 borderline |
| USD_JPY | post_news_vol | 28 | +0.267 | 3 | 0.67 | 3.68 | -1.37/+1.48 | 🟡 borderline |
| USD_JPY | ema_cross | 27 | +0.174 | 3 | 0.67 | 10.55 | -1.05/+1.06 | 🟡 borderline |
| USD_JPY | ema200_trend_reversal | 25 | +0.151 | 2 | 0.50 | 323.67 | -0.48/+0.49 | 🟡 borderline |
| GBP_USD | htf_false_breakout | 23 | -0.231 | 2 | 0.50 | 1.06 | -0.02/+0.51 | 🟡 borderline |
| GBP_USD | doji_breakout | 18 | +0.172 | 2 | 0.50 | 2.17 | -0.53/+1.45 | 🟡 borderline |
| EUR_JPY | jpy_basket_trend | 18 | +0.176 | 2 | 0.50 | 1.13 | -0.31/+0.02 | 🟡 borderline |
| USD_JPY | streak_reversal | 498 | +1.427 | 6 | 1.00 | 0.29 | +0.69/+2.09 | ✅ stable |
| USD_JPY | session_time_bias | 334 | +0.076 | 6 | 0.83 | 0.87 | -0.05/+0.16 | ✅ stable |
| GBP_JPY | vwap_mean_reversion | 270 | +1.018 | 6 | 1.00 | 0.31 | +0.61/+1.53 | ✅ stable |
| EUR_JPY | vwap_mean_reversion | 225 | +0.688 | 6 | 0.83 | 0.74 | -0.25/+1.19 | ✅ stable |
| GBP_USD | vwap_mean_reversion | 178 | +0.804 | 6 | 0.83 | 0.71 | -0.15/+1.54 | ✅ stable |
| USD_JPY | sr_break_retest | 78 | +0.238 | 6 | 0.83 | 0.89 | -0.11/+0.59 | ✅ stable |
| GBP_JPY | ema200_trend_reversal | 45 | +0.292 | 5 | 0.80 | 0.65 | -0.00/+0.64 | ✅ stable |
| GBP_USD | wick_imbalance_reversion | 38 | +0.378 | 4 | 1.00 | 0.36 | +0.24/+0.65 | ✅ stable |
| GBP_JPY | htf_false_breakout | 35 | +0.701 | 4 | 1.00 | 0.81 | +0.01/+1.03 | ✅ stable |
| EUR_USD | post_news_vol | 24 | +0.814 | 2 | 1.00 | 0.47 | +0.66/+1.83 | ✅ stable |
| EUR_USD | dt_fib_reversal | 21 | -0.034 | 1 | — | — | —/— | ⚪ N_windows<2 |
| GBP_USD | post_news_vol | 20 | +1.164 | 1 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | htf_false_breakout | 18 | +0.523 | 1 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | adx_trend_continuation | 16 | -0.182 | 1 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | ema_cross | 13 | +0.021 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | squeeze_release_momentum | 12 | +0.331 | 0 | — | — | —/— | ⚪ N_windows<2 |
| GBP_USD | ema_cross | 12 | -0.319 | 0 | — | — | —/— | ⚪ N_windows<2 |
| USD_JPY | orb_trap | 11 | -0.717 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | ema200_trend_reversal | 11 | -0.495 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | doji_breakout | 11 | +1.100 | 1 | — | — | —/— | ⚪ N_windows<2 |

## 🔴 Unstable Strategies (27 cells)
これらは Overall EV が正でも窓間分散が大きい、
または勝ち窓が半数未満。Kelly Half 到達前の FORCE_DEMOTE 検討候補。

| Pair × Strategy | Overall EV | CV(EV) | Min EV | Max EV |
|-----------------|-----------:|-------:|-------:|-------:|
| GBP_USD × xs_momentum | -0.191 | 1.27 | -0.62 | +0.12 |
| GBP_USD × sr_fib_confluence | -0.054 | 3.23 | -0.30 | +0.28 |
| EUR_JPY × sr_break_retest | -0.009 | 5.73 | -0.70 | +0.36 |
| GBP_JPY × dt_sr_channel_reversal | -0.084 | 1.54 | -0.32 | +0.04 |
| USD_JPY × sr_fib_confluence | +0.000 | 12.49 | -0.13 | +0.29 |
| GBP_USD × dt_bb_rsi_mr | -0.220 | 1.63 | -0.50 | +0.25 |
| USD_JPY × dt_bb_rsi_mr | -0.251 | 0.60 | -0.61 | -0.12 |
| EUR_JPY × dt_fib_reversal | -0.362 | 0.77 | -0.85 | +0.08 |
| EUR_USD × dt_bb_rsi_mr | -0.194 | 2.42 | -0.50 | +0.40 |
| GBP_USD × dual_sr_bounce | -0.204 | 1.70 | -0.65 | +0.27 |
| USD_JPY × dt_sr_channel_reversal | -0.328 | 1.37 | -1.11 | +0.21 |
| GBP_USD × dt_sr_channel_reversal | -0.070 | 3.93 | -0.70 | +0.44 |
| GBP_USD × intraday_seasonality | -0.236 | 1.12 | -0.71 | -0.00 |
| USD_JPY × london_fix_reversal | -0.138 | 2.39 | -1.03 | +0.20 |
| GBP_USD × london_fix_reversal | -0.345 | 0.56 | -0.62 | +0.00 |
| EUR_USD × london_fix_reversal | -0.052 | 5.01 | -0.50 | +0.49 |
| USD_JPY × wick_imbalance_reversion | -0.228 | 3.29 | -1.01 | +0.97 |
| GBP_USD × sr_break_retest | -0.461 | 0.91 | -1.48 | -0.07 |
| EUR_USD × intraday_seasonality | -0.216 | 2.01 | -0.80 | +0.48 |
| GBP_USD × ema200_trend_reversal | -0.225 | 2.10 | -0.95 | +0.60 |
| EUR_USD × dual_sr_bounce | -0.284 | 3.81 | -0.93 | +0.58 |
| EUR_JPY × htf_false_breakout | +0.087 | 18.56 | -0.45 | +0.52 |
| EUR_USD × dt_sr_channel_reversal | +0.007 | 40.53 | -0.29 | +0.46 |
| EUR_USD × wick_imbalance_reversion | -0.064 | 4.67 | -0.39 | +0.50 |
| EUR_USD × orb_trap | -0.379 | 7.70 | -0.42 | +0.37 |
| GBP_USD × dt_fib_reversal | -0.137 | 7.31 | -0.69 | +0.61 |
| GBP_USD × orb_trap | +0.112 | 3.83 | -0.64 | +0.38 |

## 判断プロトコル遵守 (CLAUDE.md)
- **本スキャンは 1 回 BT** → 実装判断は **保留** (lesson-reactive-changes)
- `unstable` 判定戦略も、post-hoc 分解のみで因果なし
- 次ステップ: Live N≥30 を経るか、別 BT 期間 (例 730d) で再検証

## Source
- pybroker walk-forward concept adapted for parameter-frozen regime
- Generated by: `tools/bt_walkforward.py`
