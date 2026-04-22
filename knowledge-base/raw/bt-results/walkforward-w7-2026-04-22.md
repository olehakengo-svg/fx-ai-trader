# Walk-Forward Stability Scan

- **Generated**: 2026-04-22 15:40 UTC
- **Window size**: 7 days (rolling)
- **Verdict thresholds**:
  - **stable**: positive_ratio ≥ 0.67 AND CV(EV) < 1.0
  - **borderline**: positive_ratio ≥ 0.5
  - **unstable**: 上記どちらも満たさない

## Cross-Pair Strategy Stability
| Pair | Strategy | N | Overall EV | Windows | Pos.ratio | CV(EV) | Min/Max EV | Verdict |
|------|----------|--:|-----------:|--------:|----------:|-------:|:-----------|:-------:|
| GBP_USD | session_time_bias | 393 | -0.054 | 39 | 0.49 | 10.39 | -1.34/+0.90 | 🔴 unstable |
| GBP_USD | xs_momentum | 274 | -0.191 | 33 | 0.48 | 3.10 | -1.45/+1.02 | 🔴 unstable |
| GBP_USD | sr_fib_confluence | 257 | -0.054 | 25 | 0.36 | 5.56 | -1.08/+0.97 | 🔴 unstable |
| GBP_JPY | sr_fib_confluence | 210 | +0.052 | 22 | 0.46 | 4.91 | -0.65/+1.14 | 🔴 unstable |
| EUR_JPY | dt_sr_channel_reversal | 185 | +0.021 | 16 | 0.44 | 17.10 | -0.50/+0.59 | 🔴 unstable |
| EUR_JPY | sr_break_retest | 171 | -0.009 | 14 | 0.43 | 8.95 | -0.79/+1.10 | 🔴 unstable |
| GBP_JPY | sr_break_retest | 164 | +0.040 | 11 | 0.46 | 2.88 | -0.80/+1.03 | 🔴 unstable |
| GBP_JPY | dt_sr_channel_reversal | 161 | -0.084 | 12 | 0.33 | 1.77 | -1.12/+0.25 | 🔴 unstable |
| GBP_USD | dt_bb_rsi_mr | 117 | -0.220 | 5 | 0.20 | 0.86 | -1.32/+0.05 | 🔴 unstable |
| USD_JPY | dt_bb_rsi_mr | 103 | -0.251 | 3 | 0.00 | 0.73 | -0.70/-0.09 | 🔴 unstable |
| EUR_JPY | wick_imbalance_reversion | 94 | +0.033 | 3 | 0.00 | 0.56 | -0.99/-0.17 | 🔴 unstable |
| USD_JPY | intraday_seasonality | 74 | +0.056 | 2 | 0.00 | 0.60 | -0.47/-0.12 | 🔴 unstable |
| EUR_USD | session_time_bias | 463 | +0.088 | 39 | 0.54 | 7.06 | -0.97/+1.15 | 🟡 borderline |
| USD_JPY | session_time_bias | 334 | +0.076 | 39 | 0.61 | 5.67 | -1.98/+1.28 | 🟡 borderline |
| USD_JPY | xs_momentum | 309 | +0.081 | 36 | 0.56 | 5.68 | -1.16/+1.27 | 🟡 borderline |
| EUR_USD | sr_fib_confluence | 266 | +0.009 | 30 | 0.53 | 7.44 | -1.01/+1.05 | 🟡 borderline |
| EUR_USD | xs_momentum | 257 | +0.043 | 29 | 0.66 | 3.89 | -1.03/+1.08 | 🟡 borderline |
| EUR_JPY | sr_fib_confluence | 194 | +0.160 | 18 | 0.56 | 2.83 | -0.60/+0.86 | 🟡 borderline |
| GBP_USD | vwap_mean_reversion | 178 | +0.804 | 10 | 0.50 | 3.00 | -1.75/+3.00 | 🟡 borderline |
| USD_JPY | sr_fib_confluence | 158 | +0.000 | 13 | 0.61 | 2.59 | -0.70/+1.20 | 🟡 borderline |
| USD_JPY | vix_carry_unwind | 138 | +0.292 | 9 | 0.78 | 2.47 | -1.79/+2.29 | 🟡 borderline |
| GBP_JPY | dual_sr_bounce | 136 | +0.149 | 9 | 0.67 | 199.59 | -0.99/+0.75 | 🟡 borderline |
| GBP_USD | gbp_deep_pullback | 100 | +0.438 | 3 | 0.67 | 1.55 | -0.97/+3.17 | 🟡 borderline |
| EUR_JPY | intraday_seasonality | 88 | -0.030 | 2 | 0.50 | 5.64 | -0.94/+0.66 | 🟡 borderline |
| USD_JPY | vol_spike_mr | 85 | +0.129 | 2 | 0.50 | 2.42 | -0.94/+0.39 | 🟡 borderline |
| USD_JPY | streak_reversal | 498 | +1.427 | 49 | 0.86 | 0.97 | -0.92/+6.03 | ✅ stable |
| GBP_JPY | vwap_mean_reversion | 270 | +1.018 | 32 | 0.88 | 0.98 | -1.61/+2.51 | ✅ stable |
| EUR_JPY | vwap_mean_reversion | 225 | +0.688 | 23 | 0.91 | 0.84 | -0.07/+2.25 | ✅ stable |
| GBP_JPY | intraday_seasonality | 119 | +0.069 | 4 | 1.00 | 0.45 | +0.15/+0.83 | ✅ stable |
| EUR_JPY | dual_sr_bounce | 118 | +0.188 | 5 | 1.00 | 0.48 | +0.08/+0.61 | ✅ stable |
| GBP_JPY | wick_imbalance_reversion | 94 | +0.085 | 3 | 1.00 | 0.49 | +0.26/+0.70 | ✅ stable |
| EUR_USD | dt_bb_rsi_mr | 82 | -0.101 | 2 | 1.00 | 0.11 | +0.18/+0.23 | ✅ stable |
| GBP_USD | trendline_sweep | 108 | +0.338 | 1 | — | — | —/— | ⚪ N_windows<2 |
| USD_JPY | sr_break_retest | 78 | +0.238 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_JPY | dt_fib_reversal | 77 | -0.362 | 0 | — | — | —/— | ⚪ N_windows<2 |
| USD_JPY | dual_sr_bounce | 71 | -0.083 | 1 | — | — | —/— | ⚪ N_windows<2 |
| GBP_USD | dual_sr_bounce | 68 | -0.204 | 0 | — | — | —/— | ⚪ N_windows<2 |
| GBP_JPY | dt_fib_reversal | 68 | +0.301 | 1 | — | — | —/— | ⚪ N_windows<2 |
| USD_JPY | dt_sr_channel_reversal | 67 | -0.328 | 1 | — | — | —/— | ⚪ N_windows<2 |
| GBP_USD | dt_sr_channel_reversal | 66 | -0.070 | 0 | — | — | —/— | ⚪ N_windows<2 |
| GBP_USD | intraday_seasonality | 63 | -0.236 | 1 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | london_fix_reversal | 60 | -0.097 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | trendline_sweep | 59 | +0.267 | 1 | — | — | —/— | ⚪ N_windows<2 |
| USD_JPY | london_fix_reversal | 54 | -0.138 | 1 | — | — | —/— | ⚪ N_windows<2 |
| GBP_USD | london_fix_reversal | 53 | -0.345 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | post_news_vol | 51 | +1.056 | 0 | — | — | —/— | ⚪ N_windows<2 |
| USD_JPY | wick_imbalance_reversion | 50 | -0.228 | 0 | — | — | —/— | ⚪ N_windows<2 |
| GBP_USD | turtle_soup | 50 | +0.530 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | intraday_seasonality | 49 | -0.091 | 0 | — | — | —/— | ⚪ N_windows<2 |
| GBP_USD | sr_break_retest | 48 | -0.461 | 0 | — | — | —/— | ⚪ N_windows<2 |
| GBP_JPY | ema_cross | 46 | +0.273 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | wick_imbalance_reversion | 45 | -0.078 | 1 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | dual_sr_bounce | 45 | -0.029 | 0 | — | — | —/— | ⚪ N_windows<2 |
| GBP_JPY | ema200_trend_reversal | 45 | +0.292 | 1 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | orb_trap | 41 | -0.364 | 0 | — | — | —/— | ⚪ N_windows<2 |
| GBP_USD | ema200_trend_reversal | 39 | -0.225 | 0 | — | — | —/— | ⚪ N_windows<2 |
| GBP_USD | wick_imbalance_reversion | 38 | +0.378 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_JPY | ema200_trend_reversal | 38 | -0.019 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | lin_reg_channel | 36 | -0.062 | 0 | — | — | —/— | ⚪ N_windows<2 |
| GBP_JPY | htf_false_breakout | 35 | +0.701 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_JPY | htf_false_breakout | 34 | +0.087 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_JPY | ema_cross | 34 | -0.061 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | htf_false_breakout | 32 | +0.391 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | dt_sr_channel_reversal | 30 | -0.192 | 0 | — | — | —/— | ⚪ N_windows<2 |
| GBP_USD | dt_fib_reversal | 30 | -0.137 | 0 | — | — | —/— | ⚪ N_windows<2 |
| USD_JPY | dt_fib_reversal | 29 | -0.028 | 0 | — | — | —/— | ⚪ N_windows<2 |
| USD_JPY | post_news_vol | 28 | +0.267 | 0 | — | — | —/— | ⚪ N_windows<2 |
| GBP_USD | orb_trap | 28 | +0.112 | 0 | — | — | —/— | ⚪ N_windows<2 |
| USD_JPY | ema_cross | 27 | +0.174 | 0 | — | — | —/— | ⚪ N_windows<2 |
| USD_JPY | ema200_trend_reversal | 25 | +0.151 | 0 | — | — | —/— | ⚪ N_windows<2 |
| GBP_USD | htf_false_breakout | 23 | -0.231 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | dt_fib_reversal | 22 | +0.383 | 0 | — | — | —/— | ⚪ N_windows<2 |
| GBP_USD | post_news_vol | 20 | +1.164 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | ema_cross | 19 | +0.030 | 0 | — | — | —/— | ⚪ N_windows<2 |
| GBP_USD | doji_breakout | 18 | +0.172 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_JPY | jpy_basket_trend | 18 | +0.176 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | adx_trend_continuation | 14 | +0.017 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | ema200_trend_reversal | 12 | -0.139 | 0 | — | — | —/— | ⚪ N_windows<2 |
| GBP_USD | ema_cross | 12 | -0.319 | 0 | — | — | —/— | ⚪ N_windows<2 |
| USD_JPY | orb_trap | 11 | -0.717 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | squeeze_release_momentum | 10 | +0.368 | 0 | — | — | —/— | ⚪ N_windows<2 |

## 🔴 Unstable Strategies (12 cells)
これらは Overall EV が正でも窓間分散が大きい、
または勝ち窓が半数未満。Kelly Half 到達前の FORCE_DEMOTE 検討候補。

| Pair × Strategy | Overall EV | CV(EV) | Min EV | Max EV |
|-----------------|-----------:|-------:|-------:|-------:|
| GBP_USD × session_time_bias | -0.054 | 10.39 | -1.34 | +0.90 |
| GBP_USD × xs_momentum | -0.191 | 3.10 | -1.45 | +1.02 |
| GBP_USD × sr_fib_confluence | -0.054 | 5.56 | -1.08 | +0.97 |
| GBP_JPY × sr_fib_confluence | +0.052 | 4.91 | -0.65 | +1.14 |
| EUR_JPY × dt_sr_channel_reversal | +0.021 | 17.10 | -0.50 | +0.59 |
| EUR_JPY × sr_break_retest | -0.009 | 8.95 | -0.79 | +1.10 |
| GBP_JPY × sr_break_retest | +0.040 | 2.88 | -0.80 | +1.03 |
| GBP_JPY × dt_sr_channel_reversal | -0.084 | 1.77 | -1.12 | +0.25 |
| GBP_USD × dt_bb_rsi_mr | -0.220 | 0.86 | -1.32 | +0.05 |
| USD_JPY × dt_bb_rsi_mr | -0.251 | 0.73 | -0.70 | -0.09 |
| EUR_JPY × wick_imbalance_reversion | +0.033 | 0.56 | -0.99 | -0.17 |
| USD_JPY × intraday_seasonality | +0.056 | 0.60 | -0.47 | -0.12 |

## 判断プロトコル遵守 (CLAUDE.md)
- **本スキャンは 1 回 BT** → 実装判断は **保留** (lesson-reactive-changes)
- `unstable` 判定戦略も、post-hoc 分解のみで因果なし
- 次ステップ: Live N≥30 を経るか、別 BT 期間 (例 730d) で再検証

## Source
- pybroker walk-forward concept adapted for parameter-frozen regime
- Generated by: `tools/bt_walkforward.py`
