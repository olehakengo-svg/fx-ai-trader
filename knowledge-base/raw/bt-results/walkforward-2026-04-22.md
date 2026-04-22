# Walk-Forward Stability Scan

- **Generated**: 2026-04-22 13:14 UTC
- **Window size**: 30 days (rolling)
- **Verdict thresholds**:
  - **stable**: positive_ratio ≥ 0.67 AND CV(EV) < 1.0
  - **borderline**: positive_ratio ≥ 0.5
  - **unstable**: 上記どちらも満たさない

## Cross-Pair Strategy Stability
| Pair | Strategy | N | Overall EV | Windows | Pos.ratio | CV(EV) | Min/Max EV | Verdict |
|------|----------|--:|-----------:|--------:|----------:|-------:|:-----------|:-------:|
| GBP_USD | session_time_bias | 393 | -0.054 | 12 | 0.42 | 3.86 | -0.57/+0.44 | 🔴 unstable |
| GBP_USD | xs_momentum | 274 | -0.191 | 12 | 0.33 | 1.61 | -0.71/+0.15 | 🔴 unstable |
| GBP_USD | sr_fib_confluence | 257 | -0.054 | 12 | 0.33 | 4.37 | -0.57/+0.46 | 🔴 unstable |
| EUR_JPY | dt_sr_channel_reversal | 197 | -0.185 | 12 | 0.42 | 1.64 | -0.99/+0.30 | 🔴 unstable |
| GBP_JPY | dt_sr_channel_reversal | 161 | -0.084 | 12 | 0.33 | 2.69 | -0.46/+0.34 | 🔴 unstable |
| EUR_JPY | sr_break_retest | 156 | -0.067 | 12 | 0.42 | 5.84 | -0.76/+0.93 | 🔴 unstable |
| USD_JPY | sr_fib_confluence | 151 | -0.061 | 12 | 0.42 | 3.66 | -1.06/+0.59 | 🔴 unstable |
| EUR_JPY | dual_sr_bounce | 125 | +0.047 | 11 | 0.46 | 5.89 | -0.64/+0.98 | 🔴 unstable |
| GBP_USD | dt_bb_rsi_mr | 117 | -0.220 | 10 | 0.30 | 1.57 | -0.56/+0.30 | 🔴 unstable |
| EUR_JPY | dt_fib_reversal | 83 | -0.184 | 9 | 0.33 | 2.48 | -1.40/+0.66 | 🔴 unstable |
| USD_JPY | dual_sr_bounce | 82 | +0.020 | 6 | 0.33 | 11.44 | -0.31/+0.39 | 🔴 unstable |
| USD_JPY | intraday_seasonality | 81 | -0.061 | 9 | 0.44 | 3.16 | -1.95/+1.11 | 🔴 unstable |
| USD_JPY | dt_sr_channel_reversal | 76 | -0.368 | 7 | 0.14 | 0.80 | -1.06/+0.16 | 🔴 unstable |
| EUR_USD | dt_bb_rsi_mr | 69 | -0.194 | 8 | 0.25 | 1.54 | -0.74/+0.26 | 🔴 unstable |
| USD_JPY | vol_spike_mr | 68 | -0.213 | 7 | 0.29 | 3.24 | -0.77/+0.84 | 🔴 unstable |
| GBP_USD | dual_sr_bounce | 68 | -0.204 | 6 | 0.33 | 1.56 | -0.84/+0.12 | 🔴 unstable |
| GBP_USD | dt_sr_channel_reversal | 66 | -0.070 | 9 | 0.44 | 137.38 | -0.88/+1.14 | 🔴 unstable |
| GBP_USD | intraday_seasonality | 63 | -0.236 | 6 | 0.17 | 1.41 | -1.17/+0.77 | 🔴 unstable |
| GBP_USD | london_fix_reversal | 53 | -0.345 | 5 | 0.00 | 0.97 | -0.73/-0.01 | 🔴 unstable |
| EUR_USD | london_fix_reversal | 52 | -0.052 | 5 | 0.40 | 7.24 | -0.83/+0.62 | 🔴 unstable |
| GBP_USD | sr_break_retest | 48 | -0.461 | 3 | 0.33 | 1.02 | -1.88/+0.19 | 🔴 unstable |
| EUR_USD | intraday_seasonality | 45 | -0.216 | 5 | 0.40 | 15.82 | -0.52/+0.76 | 🔴 unstable |
| EUR_JPY | ema_cross | 41 | -0.116 | 3 | 0.33 | 4.24 | -0.40/+0.33 | 🔴 unstable |
| GBP_USD | ema200_trend_reversal | 39 | -0.225 | 4 | 0.25 | 1.89 | -1.41/+0.60 | 🔴 unstable |
| EUR_USD | dual_sr_bounce | 35 | -0.284 | 4 | 0.25 | 1.79 | -1.28/+0.25 | 🔴 unstable |
| EUR_USD | dt_sr_channel_reversal | 32 | +0.027 | 2 | 0.00 | 0.15 | -0.56/-0.42 | 🔴 unstable |
| USD_JPY | wick_imbalance_reversion | 30 | -0.461 | 2 | 0.00 | 0.68 | -1.67/-0.32 | 🔴 unstable |
| EUR_USD | session_time_bias | 403 | +0.151 | 12 | 0.75 | 2.13 | -0.29/+0.43 | 🟡 borderline |
| USD_JPY | session_time_bias | 342 | +0.168 | 12 | 0.75 | 1.91 | -0.49/+0.70 | 🟡 borderline |
| USD_JPY | xs_momentum | 287 | +0.117 | 12 | 0.58 | 4.50 | -0.48/+0.80 | 🟡 borderline |
| EUR_USD | sr_fib_confluence | 238 | -0.027 | 12 | 0.67 | 12.11 | -0.66/+0.40 | 🟡 borderline |
| EUR_USD | xs_momentum | 237 | +0.092 | 12 | 0.75 | 2.98 | -0.27/+0.61 | 🟡 borderline |
| EUR_JPY | sr_fib_confluence | 220 | -0.037 | 12 | 0.50 | 4.56 | -0.93/+0.48 | 🟡 borderline |
| GBP_JPY | sr_fib_confluence | 210 | +0.052 | 12 | 0.67 | 4.97 | -0.58/+0.48 | 🟡 borderline |
| EUR_USD | vwap_mean_reversion | 165 | +0.980 | 12 | 0.83 | 1.19 | -0.55/+2.83 | 🟡 borderline |
| GBP_JPY | sr_break_retest | 164 | +0.040 | 12 | 0.50 | 29.14 | -0.58/+0.61 | 🟡 borderline |
| GBP_JPY | dual_sr_bounce | 136 | +0.149 | 12 | 0.58 | 8.59 | -0.68/+0.59 | 🟡 borderline |
| EUR_JPY | intraday_seasonality | 126 | +0.191 | 10 | 0.70 | 2.06 | -0.53/+1.05 | 🟡 borderline |
| GBP_JPY | intraday_seasonality | 119 | +0.069 | 11 | 0.64 | 10.63 | -0.77/+0.70 | 🟡 borderline |
| USD_JPY | dt_bb_rsi_mr | 113 | -0.003 | 10 | 0.70 | 3.21 | -0.46/+0.41 | 🟡 borderline |
| GBP_USD | trendline_sweep | 108 | +0.338 | 12 | 0.75 | 1.24 | -0.36/+1.75 | 🟡 borderline |
| USD_JPY | vix_carry_unwind | 104 | +0.645 | 11 | 0.73 | 1.39 | -0.54/+2.40 | 🟡 borderline |
| GBP_USD | gbp_deep_pullback | 100 | +0.438 | 10 | 0.50 | 6.49 | -1.47/+2.34 | 🟡 borderline |
| GBP_JPY | wick_imbalance_reversion | 94 | +0.085 | 7 | 0.57 | 2.08 | -0.33/+0.53 | 🟡 borderline |
| EUR_JPY | wick_imbalance_reversion | 84 | +0.112 | 10 | 0.70 | 14.81 | -1.09/+1.35 | 🟡 borderline |
| USD_JPY | sr_break_retest | 72 | -0.121 | 8 | 0.50 | 17.89 | -0.70/+1.14 | 🟡 borderline |
| GBP_JPY | dt_fib_reversal | 68 | +0.301 | 8 | 0.75 | 1.74 | -0.46/+1.39 | 🟡 borderline |
| USD_JPY | london_fix_reversal | 50 | +0.107 | 4 | 0.50 | 47.14 | -0.37/+0.39 | 🟡 borderline |
| GBP_USD | turtle_soup | 50 | +0.530 | 4 | 0.50 | 5.27 | -0.60/+1.18 | 🟡 borderline |
| EUR_JPY | htf_false_breakout | 47 | +0.140 | 5 | 0.80 | 2.37 | -0.71/+0.69 | 🟡 borderline |
| GBP_JPY | ema_cross | 46 | +0.273 | 4 | 0.75 | 1.25 | -0.03/+0.71 | 🟡 borderline |
| GBP_JPY | ema200_trend_reversal | 45 | +0.292 | 5 | 0.60 | 2.52 | -0.46/+0.61 | 🟡 borderline |
| EUR_JPY | ema200_trend_reversal | 43 | +0.217 | 3 | 0.67 | 1.91 | -0.64/+1.00 | 🟡 borderline |
| EUR_USD | lin_reg_channel | 29 | +0.006 | 2 | 0.50 | 7.01 | -0.59/+0.79 | 🟡 borderline |
| USD_JPY | streak_reversal | 466 | +1.362 | 12 | 1.00 | 0.57 | +0.37/+3.22 | ✅ stable |
| GBP_JPY | vwap_mean_reversion | 270 | +1.018 | 12 | 1.00 | 0.45 | +0.38/+1.73 | ✅ stable |
| GBP_USD | vwap_mean_reversion | 178 | +0.804 | 12 | 0.83 | 0.93 | -0.30/+2.68 | ✅ stable |
| USD_JPY | vwap_mean_reversion | 123 | +1.111 | 11 | 1.00 | 0.38 | +0.17/+1.90 | ✅ stable |
| EUR_USD | trendline_sweep | 56 | +0.576 | 6 | 1.00 | 0.79 | +0.06/+1.38 | ✅ stable |
| GBP_USD | wick_imbalance_reversion | 38 | +0.378 | 4 | 1.00 | 0.62 | +0.13/+1.08 | ✅ stable |
| GBP_JPY | htf_false_breakout | 35 | +0.701 | 2 | 1.00 | 0.62 | +0.18/+0.79 | ✅ stable |
| EUR_USD | wick_imbalance_reversion | 33 | -0.064 | 1 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | orb_trap | 32 | -0.379 | 1 | — | — | —/— | ⚪ N_windows<2 |
| GBP_USD | dt_fib_reversal | 30 | -0.137 | 0 | — | — | —/— | ⚪ N_windows<2 |
| GBP_USD | orb_trap | 28 | +0.112 | 1 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | post_news_vol | 24 | +0.814 | 1 | — | — | —/— | ⚪ N_windows<2 |
| USD_JPY | ema200_trend_reversal | 23 | -0.136 | 1 | — | — | —/— | ⚪ N_windows<2 |
| GBP_USD | htf_false_breakout | 23 | -0.231 | 1 | — | — | —/— | ⚪ N_windows<2 |
| USD_JPY | dt_fib_reversal | 22 | +0.077 | 0 | — | — | —/— | ⚪ N_windows<2 |
| USD_JPY | ema_cross | 21 | -0.356 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | dt_fib_reversal | 21 | -0.034 | 0 | — | — | —/— | ⚪ N_windows<2 |
| GBP_USD | post_news_vol | 20 | +1.164 | 1 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | htf_false_breakout | 18 | +0.523 | 1 | — | — | —/— | ⚪ N_windows<2 |
| GBP_USD | doji_breakout | 18 | +0.172 | 1 | — | — | —/— | ⚪ N_windows<2 |
| USD_JPY | htf_false_breakout | 16 | +0.397 | 0 | — | — | —/— | ⚪ N_windows<2 |
| USD_JPY | post_news_vol | 16 | +1.113 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | adx_trend_continuation | 16 | -0.182 | 0 | — | — | —/— | ⚪ N_windows<2 |
| USD_JPY | orb_trap | 13 | -0.272 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | ema_cross | 13 | +0.021 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | squeeze_release_momentum | 12 | +0.331 | 0 | — | — | —/— | ⚪ N_windows<2 |
| GBP_USD | ema_cross | 12 | -0.319 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | ema200_trend_reversal | 11 | -0.495 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | doji_breakout | 11 | +1.100 | 1 | — | — | —/— | ⚪ N_windows<2 |
| EUR_JPY | jpy_basket_trend | 11 | -0.591 | 0 | — | — | —/— | ⚪ N_windows<2 |

## 🔴 Unstable Strategies (27 cells)
これらは Overall EV が正でも窓間分散が大きい、
または勝ち窓が半数未満。Kelly Half 到達前の FORCE_DEMOTE 検討候補。

| Pair × Strategy | Overall EV | CV(EV) | Min EV | Max EV |
|-----------------|-----------:|-------:|-------:|-------:|
| GBP_USD × session_time_bias | -0.054 | 3.86 | -0.57 | +0.44 |
| GBP_USD × xs_momentum | -0.191 | 1.61 | -0.71 | +0.15 |
| GBP_USD × sr_fib_confluence | -0.054 | 4.37 | -0.57 | +0.46 |
| EUR_JPY × dt_sr_channel_reversal | -0.185 | 1.64 | -0.99 | +0.30 |
| GBP_JPY × dt_sr_channel_reversal | -0.084 | 2.69 | -0.46 | +0.34 |
| EUR_JPY × sr_break_retest | -0.067 | 5.84 | -0.76 | +0.93 |
| USD_JPY × sr_fib_confluence | -0.061 | 3.66 | -1.06 | +0.59 |
| EUR_JPY × dual_sr_bounce | +0.047 | 5.89 | -0.64 | +0.98 |
| GBP_USD × dt_bb_rsi_mr | -0.220 | 1.57 | -0.56 | +0.30 |
| EUR_JPY × dt_fib_reversal | -0.184 | 2.48 | -1.40 | +0.66 |
| USD_JPY × dual_sr_bounce | +0.020 | 11.44 | -0.31 | +0.39 |
| USD_JPY × intraday_seasonality | -0.061 | 3.16 | -1.95 | +1.11 |
| USD_JPY × dt_sr_channel_reversal | -0.368 | 0.80 | -1.06 | +0.16 |
| EUR_USD × dt_bb_rsi_mr | -0.194 | 1.54 | -0.74 | +0.26 |
| USD_JPY × vol_spike_mr | -0.213 | 3.24 | -0.77 | +0.84 |
| GBP_USD × dual_sr_bounce | -0.204 | 1.56 | -0.84 | +0.12 |
| GBP_USD × dt_sr_channel_reversal | -0.070 | 137.38 | -0.88 | +1.14 |
| GBP_USD × intraday_seasonality | -0.236 | 1.41 | -1.17 | +0.77 |
| GBP_USD × london_fix_reversal | -0.345 | 0.97 | -0.73 | -0.01 |
| EUR_USD × london_fix_reversal | -0.052 | 7.24 | -0.83 | +0.62 |
| GBP_USD × sr_break_retest | -0.461 | 1.02 | -1.88 | +0.19 |
| EUR_USD × intraday_seasonality | -0.216 | 15.82 | -0.52 | +0.76 |
| EUR_JPY × ema_cross | -0.116 | 4.24 | -0.40 | +0.33 |
| GBP_USD × ema200_trend_reversal | -0.225 | 1.89 | -1.41 | +0.60 |
| EUR_USD × dual_sr_bounce | -0.284 | 1.79 | -1.28 | +0.25 |
| EUR_USD × dt_sr_channel_reversal | +0.027 | 0.15 | -0.56 | -0.42 |
| USD_JPY × wick_imbalance_reversion | -0.461 | 0.68 | -1.67 | -0.32 |

## 判断プロトコル遵守 (CLAUDE.md)
- **本スキャンは 1 回 BT** → 実装判断は **保留** (lesson-reactive-changes)
- `unstable` 判定戦略も、post-hoc 分解のみで因果なし
- 次ステップ: Live N≥30 を経るか、別 BT 期間 (例 730d) で再検証

## Source
- pybroker walk-forward concept adapted for parameter-frozen regime
- Generated by: `tools/bt_walkforward.py`
