# Walk-Forward Stability Scan

- **Generated**: 2026-04-22 15:40 UTC
- **Window size**: 90 days (rolling)
- **Verdict thresholds**:
  - **stable**: positive_ratio ≥ 0.67 AND CV(EV) < 1.0
  - **borderline**: positive_ratio ≥ 0.5
  - **unstable**: 上記どちらも満たさない

## Cross-Pair Strategy Stability
| Pair | Strategy | N | Overall EV | Windows | Pos.ratio | CV(EV) | Min/Max EV | Verdict |
|------|----------|--:|-----------:|--------:|----------:|-------:|:-----------|:-------:|
| GBP_USD | xs_momentum | 274 | -0.191 | 4 | 0.25 | 0.66 | -0.32/+0.01 | 🔴 unstable |
| GBP_USD | sr_fib_confluence | 257 | -0.054 | 4 | 0.25 | 1.36 | -0.22/+0.04 | 🔴 unstable |
| EUR_JPY | sr_break_retest | 171 | -0.009 | 4 | 0.25 | 235.10 | -0.27/+0.49 | 🔴 unstable |
| GBP_JPY | dt_sr_channel_reversal | 161 | -0.084 | 4 | 0.25 | 1.32 | -0.23/+0.02 | 🔴 unstable |
| USD_JPY | sr_fib_confluence | 158 | +0.000 | 4 | 0.25 | 5.36 | -0.32/+0.34 | 🔴 unstable |
| GBP_USD | dt_bb_rsi_mr | 117 | -0.220 | 4 | 0.25 | 1.13 | -0.46/+0.10 | 🔴 unstable |
| USD_JPY | dt_bb_rsi_mr | 103 | -0.251 | 4 | 0.00 | 0.40 | -0.43/-0.17 | 🔴 unstable |
| EUR_JPY | intraday_seasonality | 88 | -0.030 | 4 | 0.25 | 43.77 | -0.28/+0.42 | 🔴 unstable |
| EUR_JPY | dt_fib_reversal | 77 | -0.362 | 4 | 0.00 | 0.68 | -0.85/-0.07 | 🔴 unstable |
| GBP_USD | dual_sr_bounce | 68 | -0.204 | 4 | 0.25 | 1.51 | -0.32/+0.17 | 🔴 unstable |
| USD_JPY | dt_sr_channel_reversal | 67 | -0.328 | 4 | 0.25 | 0.95 | -0.68/+0.02 | 🔴 unstable |
| USD_JPY | london_fix_reversal | 54 | -0.138 | 4 | 0.25 | 1.59 | -1.08/+0.03 | 🔴 unstable |
| GBP_USD | london_fix_reversal | 53 | -0.345 | 4 | 0.00 | 0.21 | -0.45/-0.27 | 🔴 unstable |
| USD_JPY | wick_imbalance_reversion | 50 | -0.228 | 3 | 0.33 | 1.71 | -0.78/+0.41 | 🔴 unstable |
| GBP_USD | sr_break_retest | 48 | -0.461 | 4 | 0.00 | 0.49 | -0.85/-0.23 | 🔴 unstable |
| GBP_USD | ema200_trend_reversal | 39 | -0.225 | 4 | 0.25 | 2.69 | -0.95/+0.32 | 🔴 unstable |
| EUR_USD | dual_sr_bounce | 35 | -0.284 | 3 | 0.33 | 1.15 | -0.71/+0.09 | 🔴 unstable |
| EUR_JPY | ema_cross | 34 | -0.061 | 4 | 0.00 | 0.46 | -0.10/-0.02 | 🔴 unstable |
| EUR_USD | orb_trap | 32 | -0.379 | 3 | 0.33 | 2.24 | -1.08/+0.50 | 🔴 unstable |
| USD_JPY | dt_fib_reversal | 29 | -0.028 | 3 | 0.33 | 3.01 | -0.37/+0.27 | 🔴 unstable |
| EUR_USD | lin_reg_channel | 29 | +0.006 | 3 | 0.33 | 120.90 | -0.49/+0.49 | 🔴 unstable |
| GBP_USD | session_time_bias | 393 | -0.054 | 4 | 0.50 | 4.01 | -0.27/+0.18 | 🟡 borderline |
| USD_JPY | session_time_bias | 334 | +0.076 | 4 | 0.75 | 2.17 | -0.14/+0.25 | 🟡 borderline |
| USD_JPY | xs_momentum | 309 | +0.081 | 4 | 0.75 | 2.56 | -0.25/+0.33 | 🟡 borderline |
| EUR_USD | sr_fib_confluence | 238 | -0.027 | 4 | 0.75 | 774.40 | -0.33/+0.14 | 🟡 borderline |
| EUR_USD | xs_momentum | 237 | +0.092 | 4 | 0.75 | 1.33 | -0.09/+0.25 | 🟡 borderline |
| GBP_JPY | sr_fib_confluence | 210 | +0.052 | 4 | 0.75 | 3.66 | -0.20/+0.27 | 🟡 borderline |
| EUR_JPY | sr_fib_confluence | 194 | +0.160 | 4 | 0.50 | 1.44 | -0.11/+0.45 | 🟡 borderline |
| EUR_JPY | dt_sr_channel_reversal | 185 | +0.021 | 4 | 0.75 | 2.47 | -0.12/+0.10 | 🟡 borderline |
| GBP_JPY | sr_break_retest | 164 | +0.040 | 4 | 0.50 | 15.59 | -0.42/+0.28 | 🟡 borderline |
| GBP_JPY | dual_sr_bounce | 136 | +0.149 | 4 | 0.75 | 1.60 | -0.15/+0.39 | 🟡 borderline |
| GBP_JPY | intraday_seasonality | 119 | +0.069 | 4 | 0.75 | 1.70 | -0.08/+0.16 | 🟡 borderline |
| EUR_JPY | dual_sr_bounce | 118 | +0.188 | 4 | 0.75 | 1.10 | -0.10/+0.39 | 🟡 borderline |
| GBP_USD | gbp_deep_pullback | 100 | +0.438 | 4 | 0.50 | 1.21 | -0.16/+0.96 | 🟡 borderline |
| EUR_JPY | wick_imbalance_reversion | 94 | +0.033 | 4 | 0.50 | 10.27 | -0.45/+0.27 | 🟡 borderline |
| GBP_JPY | wick_imbalance_reversion | 94 | +0.085 | 4 | 0.50 | 3.81 | -0.26/+0.29 | 🟡 borderline |
| USD_JPY | vol_spike_mr | 85 | +0.129 | 4 | 0.75 | 2.01 | -0.23/+0.54 | 🟡 borderline |
| USD_JPY | sr_break_retest | 78 | +0.238 | 4 | 0.75 | 1.33 | -0.19/+0.62 | 🟡 borderline |
| USD_JPY | intraday_seasonality | 74 | +0.056 | 4 | 0.75 | 2.65 | -0.30/+0.37 | 🟡 borderline |
| USD_JPY | dual_sr_bounce | 71 | -0.083 | 4 | 0.50 | 3.43 | -0.79/+0.51 | 🟡 borderline |
| EUR_USD | dt_bb_rsi_mr | 69 | -0.194 | 4 | 0.50 | 1.49 | -0.45/+0.08 | 🟡 borderline |
| GBP_JPY | dt_fib_reversal | 68 | +0.301 | 4 | 0.50 | 1.05 | -0.02/+0.55 | 🟡 borderline |
| GBP_USD | dt_sr_channel_reversal | 66 | -0.070 | 4 | 0.50 | 4.21 | -0.46/+0.38 | 🟡 borderline |
| GBP_USD | intraday_seasonality | 63 | -0.236 | 4 | 0.50 | 1.31 | -0.67/+0.11 | 🟡 borderline |
| EUR_USD | london_fix_reversal | 52 | -0.052 | 4 | 0.50 | 6.19 | -0.53/+0.28 | 🟡 borderline |
| EUR_USD | intraday_seasonality | 45 | -0.216 | 4 | 0.50 | 3.41 | -0.74/+0.54 | 🟡 borderline |
| GBP_JPY | ema200_trend_reversal | 45 | +0.292 | 4 | 0.50 | 1.09 | -0.02/+0.67 | 🟡 borderline |
| EUR_JPY | ema200_trend_reversal | 38 | -0.019 | 4 | 0.75 | 4.77 | -0.37/+0.24 | 🟡 borderline |
| EUR_JPY | htf_false_breakout | 34 | +0.087 | 4 | 0.75 | 7.73 | -0.80/+0.61 | 🟡 borderline |
| EUR_USD | dt_sr_channel_reversal | 33 | +0.007 | 4 | 0.50 | 3.60 | -0.40/+0.45 | 🟡 borderline |
| EUR_USD | wick_imbalance_reversion | 33 | -0.064 | 4 | 0.50 | 13.03 | -0.26/+0.50 | 🟡 borderline |
| GBP_USD | dt_fib_reversal | 30 | -0.137 | 4 | 0.50 | 1.94 | -0.69/+0.28 | 🟡 borderline |
| USD_JPY | post_news_vol | 28 | +0.267 | 4 | 0.50 | 2.84 | -0.56/+1.89 | 🟡 borderline |
| GBP_USD | orb_trap | 28 | +0.112 | 4 | 0.75 | 2.07 | -0.46/+0.62 | 🟡 borderline |
| USD_JPY | ema_cross | 27 | +0.174 | 2 | 0.50 | 8.58 | -0.84/+1.06 | 🟡 borderline |
| GBP_USD | htf_false_breakout | 23 | -0.231 | 2 | 0.50 | 3.44 | -0.70/+0.38 | 🟡 borderline |
| EUR_USD | dt_fib_reversal | 21 | -0.034 | 2 | 0.50 | 4.83 | -0.43/+0.66 | 🟡 borderline |
| GBP_USD | doji_breakout | 18 | +0.172 | 2 | 0.50 | 2.17 | -0.53/+1.45 | 🟡 borderline |
| EUR_JPY | jpy_basket_trend | 18 | +0.176 | 2 | 0.50 | 1.17 | -0.25/+0.02 | 🟡 borderline |
| EUR_USD | ema_cross | 13 | +0.021 | 2 | 0.50 | 67.32 | -0.65/+0.63 | 🟡 borderline |
| USD_JPY | streak_reversal | 498 | +1.427 | 4 | 1.00 | 0.23 | +0.86/+1.66 | ✅ stable |
| EUR_USD | session_time_bias | 403 | +0.151 | 4 | 1.00 | 0.63 | +0.05/+0.29 | ✅ stable |
| GBP_JPY | vwap_mean_reversion | 270 | +1.018 | 4 | 1.00 | 0.42 | +0.58/+1.57 | ✅ stable |
| EUR_JPY | vwap_mean_reversion | 225 | +0.688 | 4 | 1.00 | 0.41 | +0.34/+1.11 | ✅ stable |
| GBP_USD | vwap_mean_reversion | 178 | +0.804 | 4 | 1.00 | 0.67 | +0.02/+1.68 | ✅ stable |
| EUR_USD | vwap_mean_reversion | 165 | +0.980 | 4 | 0.75 | 0.64 | -0.00/+1.70 | ✅ stable |
| USD_JPY | vix_carry_unwind | 138 | +0.292 | 4 | 0.75 | 0.90 | -0.07/+0.67 | ✅ stable |
| GBP_USD | trendline_sweep | 108 | +0.338 | 4 | 1.00 | 0.81 | +0.06/+0.85 | ✅ stable |
| EUR_USD | trendline_sweep | 56 | +0.576 | 4 | 1.00 | 0.17 | +0.49/+0.72 | ✅ stable |
| GBP_USD | turtle_soup | 50 | +0.530 | 4 | 0.75 | 0.89 | -0.07/+1.56 | ✅ stable |
| GBP_JPY | ema_cross | 46 | +0.273 | 4 | 0.75 | 0.99 | -0.22/+0.72 | ✅ stable |
| GBP_USD | wick_imbalance_reversion | 38 | +0.378 | 4 | 1.00 | 0.80 | +0.07/+0.71 | ✅ stable |
| GBP_JPY | htf_false_breakout | 35 | +0.701 | 4 | 1.00 | 0.38 | +0.41/+1.06 | ✅ stable |
| USD_JPY | ema200_trend_reversal | 25 | +0.151 | 2 | 1.00 | 0.87 | +0.04/+0.54 | ✅ stable |
| EUR_USD | post_news_vol | 24 | +0.814 | 3 | 1.00 | 0.61 | +0.12/+1.19 | ✅ stable |
| GBP_USD | post_news_vol | 20 | +1.164 | 3 | 1.00 | 0.93 | +0.04/+2.68 | ✅ stable |
| EUR_USD | htf_false_breakout | 18 | +0.523 | 2 | 1.00 | 0.22 | +0.33/+0.51 | ✅ stable |
| EUR_USD | adx_trend_continuation | 16 | -0.182 | 1 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | squeeze_release_momentum | 12 | +0.331 | 1 | — | — | —/— | ⚪ N_windows<2 |
| GBP_USD | ema_cross | 12 | -0.319 | 1 | — | — | —/— | ⚪ N_windows<2 |
| USD_JPY | orb_trap | 11 | -0.717 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | ema200_trend_reversal | 11 | -0.495 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | doji_breakout | 11 | +1.100 | 1 | — | — | —/— | ⚪ N_windows<2 |

## 🔴 Unstable Strategies (21 cells)
これらは Overall EV が正でも窓間分散が大きい、
または勝ち窓が半数未満。Kelly Half 到達前の FORCE_DEMOTE 検討候補。

| Pair × Strategy | Overall EV | CV(EV) | Min EV | Max EV |
|-----------------|-----------:|-------:|-------:|-------:|
| GBP_USD × xs_momentum | -0.191 | 0.66 | -0.32 | +0.01 |
| GBP_USD × sr_fib_confluence | -0.054 | 1.36 | -0.22 | +0.04 |
| EUR_JPY × sr_break_retest | -0.009 | 235.10 | -0.27 | +0.49 |
| GBP_JPY × dt_sr_channel_reversal | -0.084 | 1.32 | -0.23 | +0.02 |
| USD_JPY × sr_fib_confluence | +0.000 | 5.36 | -0.32 | +0.34 |
| GBP_USD × dt_bb_rsi_mr | -0.220 | 1.13 | -0.46 | +0.10 |
| USD_JPY × dt_bb_rsi_mr | -0.251 | 0.40 | -0.43 | -0.17 |
| EUR_JPY × intraday_seasonality | -0.030 | 43.77 | -0.28 | +0.42 |
| EUR_JPY × dt_fib_reversal | -0.362 | 0.68 | -0.85 | -0.07 |
| GBP_USD × dual_sr_bounce | -0.204 | 1.51 | -0.32 | +0.17 |
| USD_JPY × dt_sr_channel_reversal | -0.328 | 0.95 | -0.68 | +0.02 |
| USD_JPY × london_fix_reversal | -0.138 | 1.59 | -1.08 | +0.03 |
| GBP_USD × london_fix_reversal | -0.345 | 0.21 | -0.45 | -0.27 |
| USD_JPY × wick_imbalance_reversion | -0.228 | 1.71 | -0.78 | +0.41 |
| GBP_USD × sr_break_retest | -0.461 | 0.49 | -0.85 | -0.23 |
| GBP_USD × ema200_trend_reversal | -0.225 | 2.69 | -0.95 | +0.32 |
| EUR_USD × dual_sr_bounce | -0.284 | 1.15 | -0.71 | +0.09 |
| EUR_JPY × ema_cross | -0.061 | 0.46 | -0.10 | -0.02 |
| EUR_USD × orb_trap | -0.379 | 2.24 | -1.08 | +0.50 |
| USD_JPY × dt_fib_reversal | -0.028 | 3.01 | -0.37 | +0.27 |
| EUR_USD × lin_reg_channel | +0.006 | 120.90 | -0.49 | +0.49 |

## 判断プロトコル遵守 (CLAUDE.md)
- **本スキャンは 1 回 BT** → 実装判断は **保留** (lesson-reactive-changes)
- `unstable` 判定戦略も、post-hoc 分解のみで因果なし
- 次ステップ: Live N≥30 を経るか、別 BT 期間 (例 730d) で再検証

## Source
- pybroker walk-forward concept adapted for parameter-frozen regime
- Generated by: `tools/bt_walkforward.py`
