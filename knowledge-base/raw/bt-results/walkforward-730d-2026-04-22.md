# Walk-Forward Stability Scan

- **Generated**: 2026-04-23 01:15 UTC
- **Window size**: 30 days (rolling)
- **Verdict thresholds**:
  - **stable**: positive_ratio ≥ 0.67 AND CV(EV) < 1.0
  - **borderline**: positive_ratio ≥ 0.5
  - **unstable**: 上記どちらも満たさない

## Cross-Pair Strategy Stability
| Pair | Strategy | N | Overall EV | Windows | Pos.ratio | CV(EV) | Min/Max EV | Verdict |
|------|----------|--:|-----------:|--------:|----------:|-------:|:-----------|:-------:|
| GBP_USD | session_time_bias | 683 | -0.056 | 25 | 0.40 | 3.86 | -0.70/+0.38 | 🔴 unstable |
| USD_JPY | xs_momentum | 614 | +0.023 | 24 | 0.46 | 20.92 | -0.74/+0.77 | 🔴 unstable |
| USD_JPY | session_time_bias | 593 | -0.065 | 24 | 0.42 | 3.17 | -0.74/+0.64 | 🔴 unstable |
| GBP_USD | xs_momentum | 529 | -0.218 | 24 | 0.29 | 1.67 | -0.86/+0.34 | 🔴 unstable |
| GBP_USD | sr_fib_confluence | 526 | -0.170 | 25 | 0.28 | 1.78 | -0.74/+0.39 | 🔴 unstable |
| EUR_JPY | sr_break_retest | 318 | +0.003 | 22 | 0.46 | 9.49 | -1.19/+0.73 | 🔴 unstable |
| USD_JPY | dt_bb_rsi_mr | 229 | -0.150 | 23 | 0.43 | 2.96 | -0.73/+0.50 | 🔴 unstable |
| GBP_USD | dt_bb_rsi_mr | 226 | -0.172 | 24 | 0.29 | 2.22 | -0.62/+0.58 | 🔴 unstable |
| USD_JPY | vol_spike_mr | 185 | -0.054 | 22 | 0.46 | 5.82 | -1.25/+0.95 | 🔴 unstable |
| GBP_USD | intraday_seasonality | 135 | -0.151 | 14 | 0.43 | 3.79 | -1.62/+1.17 | 🔴 unstable |
| EUR_JPY | dt_fib_reversal | 129 | -0.267 | 15 | 0.20 | 1.12 | -0.95/+0.41 | 🔴 unstable |
| GBP_USD | dt_sr_channel_reversal | 125 | -0.313 | 16 | 0.44 | 3.05 | -1.28/+0.88 | 🔴 unstable |
| USD_JPY | dt_sr_channel_reversal | 124 | -0.140 | 12 | 0.25 | 4.70 | -1.17/+0.92 | 🔴 unstable |
| EUR_USD | dt_bb_rsi_mr | 119 | -0.086 | 12 | 0.33 | 2.22 | -1.07/+0.24 | 🔴 unstable |
| EUR_USD | intraday_seasonality | 108 | -0.138 | 12 | 0.33 | 4.03 | -0.83/+0.92 | 🔴 unstable |
| GBP_USD | sr_break_retest | 104 | -0.404 | 9 | 0.11 | 0.96 | -1.62/+0.33 | 🔴 unstable |
| GBP_USD | london_fix_reversal | 98 | -0.418 | 10 | 0.30 | 2.18 | -1.19/+0.84 | 🔴 unstable |
| EUR_USD | wick_imbalance_reversion | 74 | +0.092 | 5 | 0.40 | 26.35 | -1.04/+0.84 | 🔴 unstable |
| USD_JPY | post_news_vol | 65 | +0.890 | 3 | 0.33 | 2.35 | -2.17/+1.71 | 🔴 unstable |
| EUR_USD | dt_sr_channel_reversal | 63 | -0.113 | 3 | 0.00 | 0.25 | -0.33/-0.17 | 🔴 unstable |
| GBP_USD | ema200_trend_reversal | 49 | -0.228 | 2 | 0.00 | 0.68 | -1.30/-0.25 | 🔴 unstable |
| EUR_USD | session_time_bias | 729 | +0.082 | 24 | 0.75 | 3.75 | -0.69/+0.48 | 🟡 borderline |
| EUR_USD | xs_momentum | 491 | -0.002 | 24 | 0.54 | 24.94 | -0.81/+0.60 | 🟡 borderline |
| EUR_USD | sr_fib_confluence | 486 | -0.010 | 24 | 0.50 | 53.65 | -0.84/+0.78 | 🟡 borderline |
| EUR_JPY | sr_fib_confluence | 457 | +0.071 | 24 | 0.58 | 4.91 | -0.36/+0.51 | 🟡 borderline |
| GBP_JPY | sr_fib_confluence | 457 | +0.083 | 24 | 0.67 | 4.88 | -0.92/+0.89 | 🟡 borderline |
| USD_JPY | sr_fib_confluence | 349 | -0.084 | 24 | 0.50 | 4.76 | -0.79/+0.61 | 🟡 borderline |
| GBP_JPY | dt_sr_channel_reversal | 349 | +0.093 | 24 | 0.62 | 2.26 | -0.33/+0.70 | 🟡 borderline |
| USD_JPY | vix_carry_unwind | 340 | +0.565 | 22 | 0.77 | 1.86 | -1.02/+2.24 | 🟡 borderline |
| GBP_JPY | sr_break_retest | 317 | +0.048 | 24 | 0.50 | 18.89 | -0.67/+1.27 | 🟡 borderline |
| EUR_JPY | dual_sr_bounce | 312 | +0.168 | 23 | 0.70 | 3.23 | -1.17/+0.77 | 🟡 borderline |
| EUR_JPY | dt_sr_channel_reversal | 305 | +0.028 | 24 | 0.58 | 10.00 | -0.52/+0.51 | 🟡 borderline |
| GBP_JPY | dual_sr_bounce | 283 | +0.215 | 23 | 0.65 | 2.81 | -0.68/+0.97 | 🟡 borderline |
| GBP_JPY | wick_imbalance_reversion | 230 | +0.037 | 19 | 0.58 | 29.70 | -1.54/+0.57 | 🟡 borderline |
| GBP_JPY | intraday_seasonality | 225 | +0.218 | 23 | 0.65 | 1.94 | -0.99/+1.77 | 🟡 borderline |
| GBP_USD | trendline_sweep | 204 | +0.238 | 22 | 0.64 | 2.24 | -1.27/+2.28 | 🟡 borderline |
| EUR_JPY | intraday_seasonality | 180 | +0.173 | 20 | 0.60 | 3.32 | -0.87/+1.47 | 🟡 borderline |
| GBP_USD | gbp_deep_pullback | 179 | +0.926 | 21 | 0.67 | 1.82 | -2.10/+3.14 | 🟡 borderline |
| USD_JPY | sr_break_retest | 160 | +0.124 | 22 | 0.68 | 4.41 | -1.22/+1.12 | 🟡 borderline |
| EUR_JPY | wick_imbalance_reversion | 157 | +0.092 | 16 | 0.62 | 6.55 | -1.15/+0.87 | 🟡 borderline |
| GBP_USD | dual_sr_bounce | 141 | -0.123 | 16 | 0.56 | 8.22 | -0.92/+1.00 | 🟡 borderline |
| USD_JPY | dual_sr_bounce | 139 | +0.243 | 14 | 0.79 | 1.81 | -0.96/+1.65 | 🟡 borderline |
| USD_JPY | intraday_seasonality | 137 | -0.011 | 17 | 0.53 | 9.00 | -1.59/+1.11 | 🟡 borderline |
| GBP_JPY | dt_fib_reversal | 130 | +0.181 | 15 | 0.60 | 2.62 | -0.79/+0.97 | 🟡 borderline |
| GBP_USD | wick_imbalance_reversion | 104 | +0.142 | 9 | 0.67 | 8.86 | -0.82/+0.98 | 🟡 borderline |
| USD_JPY | wick_imbalance_reversion | 102 | -0.053 | 10 | 0.50 | 6.57 | -1.20/+1.21 | 🟡 borderline |
| GBP_USD | turtle_soup | 102 | +0.229 | 11 | 0.55 | 4.17 | -0.94/+1.80 | 🟡 borderline |
| GBP_JPY | ema200_trend_reversal | 92 | +0.202 | 7 | 0.57 | 5.16 | -0.61/+0.36 | 🟡 borderline |
| EUR_USD | dual_sr_bounce | 90 | -0.141 | 9 | 0.56 | 11.70 | -0.46/+0.42 | 🟡 borderline |
| GBP_JPY | ema_cross | 88 | +0.262 | 8 | 0.50 | 5.01 | -0.92/+1.26 | 🟡 borderline |
| USD_JPY | london_fix_reversal | 87 | -0.044 | 7 | 0.57 | 3.22 | -0.36/+0.67 | 🟡 borderline |
| EUR_USD | london_fix_reversal | 81 | -0.022 | 6 | 0.67 | 6.20 | -0.90/+0.85 | 🟡 borderline |
| EUR_JPY | ema_cross | 73 | -0.003 | 4 | 0.50 | 5.71 | -0.46/+0.28 | 🟡 borderline |
| GBP_USD | orb_trap | 60 | -0.028 | 3 | 0.67 | 2.68 | -0.34/+0.36 | 🟡 borderline |
| GBP_USD | post_news_vol | 57 | +0.608 | 3 | 0.67 | 2.90 | -1.76/+2.88 | 🟡 borderline |
| GBP_USD | htf_false_breakout | 49 | -0.264 | 2 | 0.50 | 3.34 | -0.28/+0.15 | 🟡 borderline |
| USD_JPY | ema200_trend_reversal | 46 | +0.218 | 2 | 0.50 | 11.28 | -0.59/+0.70 | 🟡 borderline |
| EUR_USD | dt_fib_reversal | 45 | -0.119 | 2 | 0.50 | 1.20 | -0.10/+1.14 | 🟡 borderline |
| USD_JPY | streak_reversal | 955 | +1.297 | 24 | 1.00 | 0.51 | +0.09/+2.77 | ✅ stable |
| GBP_JPY | vwap_mean_reversion | 540 | +0.818 | 25 | 0.96 | 0.70 | -0.14/+1.99 | ✅ stable |
| EUR_JPY | vwap_mean_reversion | 509 | +0.695 | 25 | 0.88 | 0.85 | -0.63/+2.34 | ✅ stable |
| GBP_USD | vwap_mean_reversion | 363 | +0.923 | 25 | 0.88 | 0.76 | -0.51/+2.02 | ✅ stable |
| EUR_USD | vwap_mean_reversion | 345 | +1.083 | 24 | 0.92 | 0.87 | -1.01/+3.10 | ✅ stable |
| EUR_USD | trendline_sweep | 106 | +0.787 | 9 | 1.00 | 0.68 | +0.10/+1.93 | ✅ stable |
| EUR_JPY | ema200_trend_reversal | 78 | +0.188 | 4 | 1.00 | 0.91 | +0.02/+1.27 | ✅ stable |
| GBP_USD | dt_fib_reversal | 69 | -0.118 | 3 | 1.00 | 0.32 | +0.09/+0.19 | ✅ stable |
| GBP_JPY | htf_false_breakout | 65 | +0.515 | 5 | 0.80 | 0.82 | -0.05/+1.07 | ✅ stable |
| USD_JPY | ema_cross | 58 | +0.157 | 4 | 1.00 | 0.13 | +0.78/+1.11 | ✅ stable |
| EUR_JPY | htf_false_breakout | 52 | +0.263 | 2 | 1.00 | 0.87 | +0.06/+0.86 | ✅ stable |
| EUR_USD | orb_trap | 64 | -0.446 | 1 | — | — | —/— | ⚪ N_windows<2 |
| USD_JPY | dt_fib_reversal | 57 | -0.105 | 1 | — | — | —/— | ⚪ N_windows<2 |
| EUR_JPY | jpy_basket_trend | 49 | +0.024 | 1 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | lin_reg_channel | 47 | -0.095 | 1 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | post_news_vol | 46 | +1.432 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | ema200_trend_reversal | 33 | -0.327 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | ema_cross | 33 | -0.210 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | squeeze_release_momentum | 32 | +0.048 | 0 | — | — | —/— | ⚪ N_windows<2 |
| GBP_USD | ema_cross | 32 | +0.010 | 1 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | htf_false_breakout | 31 | +0.298 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | adx_trend_continuation | 28 | -0.178 | 0 | — | — | —/— | ⚪ N_windows<2 |
| USD_JPY | orb_trap | 27 | -0.216 | 0 | — | — | —/— | ⚪ N_windows<2 |
| USD_JPY | htf_false_breakout | 22 | +0.233 | 0 | — | — | —/— | ⚪ N_windows<2 |
| GBP_USD | doji_breakout | 22 | +0.086 | 0 | — | — | —/— | ⚪ N_windows<2 |
| USD_JPY | doji_breakout | 18 | +1.203 | 0 | — | — | —/— | ⚪ N_windows<2 |
| GBP_USD | london_ny_swing | 17 | -0.312 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | doji_breakout | 16 | +0.673 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | london_ny_swing | 16 | +0.571 | 0 | — | — | —/— | ⚪ N_windows<2 |
| GBP_USD | squeeze_release_momentum | 13 | -0.004 | 0 | — | — | —/— | ⚪ N_windows<2 |
| GBP_USD | inducement_ob | 12 | +0.148 | 0 | — | — | —/— | ⚪ N_windows<2 |

## 🔴 Unstable Strategies (21 cells)
これらは Overall EV が正でも窓間分散が大きい、
または勝ち窓が半数未満。Kelly Half 到達前の FORCE_DEMOTE 検討候補。

| Pair × Strategy | Overall EV | CV(EV) | Min EV | Max EV |
|-----------------|-----------:|-------:|-------:|-------:|
| GBP_USD × session_time_bias | -0.056 | 3.86 | -0.70 | +0.38 |
| USD_JPY × xs_momentum | +0.023 | 20.92 | -0.74 | +0.77 |
| USD_JPY × session_time_bias | -0.065 | 3.17 | -0.74 | +0.64 |
| GBP_USD × xs_momentum | -0.218 | 1.67 | -0.86 | +0.34 |
| GBP_USD × sr_fib_confluence | -0.170 | 1.78 | -0.74 | +0.39 |
| EUR_JPY × sr_break_retest | +0.003 | 9.49 | -1.19 | +0.73 |
| USD_JPY × dt_bb_rsi_mr | -0.150 | 2.96 | -0.73 | +0.50 |
| GBP_USD × dt_bb_rsi_mr | -0.172 | 2.22 | -0.62 | +0.58 |
| USD_JPY × vol_spike_mr | -0.054 | 5.82 | -1.25 | +0.95 |
| GBP_USD × intraday_seasonality | -0.151 | 3.79 | -1.62 | +1.17 |
| EUR_JPY × dt_fib_reversal | -0.267 | 1.12 | -0.95 | +0.41 |
| GBP_USD × dt_sr_channel_reversal | -0.313 | 3.05 | -1.28 | +0.88 |
| USD_JPY × dt_sr_channel_reversal | -0.140 | 4.70 | -1.17 | +0.92 |
| EUR_USD × dt_bb_rsi_mr | -0.086 | 2.22 | -1.07 | +0.24 |
| EUR_USD × intraday_seasonality | -0.138 | 4.03 | -0.83 | +0.92 |
| GBP_USD × sr_break_retest | -0.404 | 0.96 | -1.62 | +0.33 |
| GBP_USD × london_fix_reversal | -0.418 | 2.18 | -1.19 | +0.84 |
| EUR_USD × wick_imbalance_reversion | +0.092 | 26.35 | -1.04 | +0.84 |
| USD_JPY × post_news_vol | +0.890 | 2.35 | -2.17 | +1.71 |
| EUR_USD × dt_sr_channel_reversal | -0.113 | 0.25 | -0.33 | -0.17 |
| GBP_USD × ema200_trend_reversal | -0.228 | 0.68 | -1.30 | -0.25 |

## 判断プロトコル遵守 (CLAUDE.md)
- **本スキャンは 1 回 BT** → 実装判断は **保留** (lesson-reactive-changes)
- `unstable` 判定戦略も、post-hoc 分解のみで因果なし
- 次ステップ: Live N≥30 を経るか、別 BT 期間 (例 730d) で再検証

## Source
- pybroker walk-forward concept adapted for parameter-frozen regime
- Generated by: `tools/bt_walkforward.py`
