# Walk-Forward Stability Scan

- **Generated**: 2026-04-22 12:26 UTC
- **Window size**: 30 days (rolling)
- **Verdict thresholds**:
  - **stable**: positive_ratio ≥ 0.67 AND CV(EV) < 1.0
  - **borderline**: positive_ratio ≥ 0.5
  - **unstable**: 上記どちらも満たさない

## Cross-Pair Strategy Stability
| Pair | Strategy | N | Overall EV | Windows | Pos.ratio | CV(EV) | Min/Max EV | Verdict |
|------|----------|--:|-----------:|--------:|----------:|-------:|:-----------|:-------:|
| USD_JPY | xs_momentum | 410 | -0.160 | 7 | 0.14 | 0.97 | -0.73/+0.07 | 🔴 unstable |
| EUR_USD | sr_fib_confluence | 338 | -0.052 | 7 | 0.29 | 6.10 | -0.11/+0.47 | 🔴 unstable |
| USD_JPY | sr_fib_confluence | 324 | -0.088 | 7 | 0.29 | 2.52 | -0.26/+0.28 | 🔴 unstable |
| EUR_USD | xs_momentum | 312 | -0.099 | 6 | 0.33 | 1.84 | -0.54/+0.38 | 🔴 unstable |
| USD_JPY | dt_bb_rsi_mr | 187 | -0.133 | 6 | 0.17 | 1.39 | -0.27/+0.22 | 🔴 unstable |
| USD_JPY | sr_break_retest | 116 | -0.133 | 6 | 0.33 | 2.88 | -0.53/+0.40 | 🔴 unstable |
| USD_JPY | dt_sr_channel_reversal | 114 | -0.084 | 6 | 0.33 | 2.82 | -0.49/+0.34 | 🔴 unstable |
| USD_JPY | intraday_seasonality | 105 | -0.204 | 6 | 0.33 | 2.14 | -2.06/+0.56 | 🔴 unstable |
| USD_JPY | dual_sr_bounce | 95 | -0.109 | 6 | 0.17 | 2.28 | -0.78/+0.45 | 🔴 unstable |
| EUR_USD | dt_bb_rsi_mr | 79 | -0.167 | 6 | 0.17 | 1.59 | -0.52/+0.39 | 🔴 unstable |
| EUR_USD | dt_sr_channel_reversal | 66 | -0.271 | 6 | 0.00 | 0.74 | -0.68/-0.02 | 🔴 unstable |
| EUR_USD | wick_imbalance_reversion | 66 | -0.318 | 5 | 0.20 | 1.48 | -1.04/+0.55 | 🔴 unstable |
| EUR_USD | dual_sr_bounce | 47 | +0.048 | 6 | 0.33 | 51.17 | -0.75/+1.19 | 🔴 unstable |
| EUR_USD | intraday_seasonality | 47 | +0.031 | 5 | 0.20 | 23.10 | -0.35/+0.70 | 🔴 unstable |
| USD_JPY | ema_cross | 42 | -0.403 | 5 | 0.00 | 0.70 | -0.85/-0.03 | 🔴 unstable |
| USD_JPY | wick_imbalance_reversion | 41 | -0.244 | 5 | 0.40 | 1.69 | -1.18/+0.46 | 🔴 unstable |
| EUR_USD | lin_reg_channel | 35 | +0.144 | 5 | 0.40 | 12.28 | -1.01/+1.10 | 🔴 unstable |
| EUR_USD | dt_fib_reversal | 30 | -0.016 | 5 | 0.40 | 17.76 | -0.95/+0.65 | 🔴 unstable |
| EUR_USD | htf_false_breakout | 28 | -0.202 | 3 | 0.00 | 0.41 | -0.24/-0.09 | 🔴 unstable |
| EUR_USD | ema200_trend_reversal | 27 | -0.214 | 3 | 0.00 | 0.87 | -0.61/-0.07 | 🔴 unstable |
| EUR_USD | london_fix_reversal | 27 | -0.221 | 3 | 0.00 | 1.05 | -0.68/-0.05 | 🔴 unstable |
| EUR_USD | session_time_bias | 608 | +0.059 | 7 | 0.71 | 9.04 | -0.23/+0.20 | 🟡 borderline |
| USD_JPY | session_time_bias | 314 | +0.016 | 6 | 0.67 | 10.31 | -0.33/+0.25 | 🟡 borderline |
| EUR_USD | vwap_mean_reversion | 123 | +0.755 | 6 | 0.83 | 1.73 | -1.17/+2.35 | 🟡 borderline |
| USD_JPY | vol_spike_mr | 80 | -0.132 | 5 | 0.60 | 2.82 | -0.36/+0.23 | 🟡 borderline |
| USD_JPY | dt_fib_reversal | 40 | +0.051 | 4 | 0.50 | 7.51 | -0.36/+0.58 | 🟡 borderline |
| USD_JPY | ema200_trend_reversal | 29 | -0.102 | 4 | 0.50 | 15.65 | -0.62/+0.76 | 🟡 borderline |
| USD_JPY | post_news_vol | 27 | +0.706 | 4 | 0.50 | 3.93 | -0.94/+1.88 | 🟡 borderline |
| EUR_USD | orb_trap | 26 | +0.452 | 3 | 0.67 | 0.96 | -0.16/+0.84 | 🟡 borderline |
| USD_JPY | htf_false_breakout | 25 | +0.236 | 3 | 0.67 | 1.40 | -0.28/+2.13 | 🟡 borderline |
| EUR_USD | adx_trend_continuation | 25 | +0.466 | 3 | 0.67 | 1.37 | -0.48/+1.31 | 🟡 borderline |
| USD_JPY | streak_reversal | 693 | +0.948 | 7 | 1.00 | 0.62 | +0.69/+3.00 | ✅ stable |
| USD_JPY | vwap_mean_reversion | 155 | +0.925 | 6 | 1.00 | 0.51 | +0.43/+2.02 | ✅ stable |
| USD_JPY | vix_carry_unwind | 90 | +0.972 | 6 | 1.00 | 0.68 | +0.01/+2.07 | ✅ stable |
| EUR_USD | trendline_sweep | 43 | +0.749 | 6 | 1.00 | 0.64 | +0.28/+1.60 | ✅ stable |
| EUR_USD | squeeze_release_momentum | 23 | +0.332 | 3 | 1.00 | 0.83 | +0.03/+0.64 | ✅ stable |
| USD_JPY | london_fix_reversal | 22 | +0.691 | 3 | 1.00 | 0.84 | +0.20/+1.22 | ✅ stable |
| USD_JPY | orb_trap | 14 | +0.120 | 1 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | doji_breakout | 14 | -0.684 | 0 | — | — | —/— | ⚪ N_windows<2 |
| EUR_USD | ema_cross | 14 | -0.016 | 0 | — | — | —/— | ⚪ N_windows<2 |
| USD_JPY | doji_breakout | 13 | -0.478 | 0 | — | — | —/— | ⚪ N_windows<2 |

## 🔴 Unstable Strategies (21 cells)
これらは Overall EV が正でも窓間分散が大きい、
または勝ち窓が半数未満。Kelly Half 到達前の FORCE_DEMOTE 検討候補。

| Pair × Strategy | Overall EV | CV(EV) | Min EV | Max EV |
|-----------------|-----------:|-------:|-------:|-------:|
| USD_JPY × xs_momentum | -0.160 | 0.97 | -0.73 | +0.07 |
| EUR_USD × sr_fib_confluence | -0.052 | 6.10 | -0.11 | +0.47 |
| USD_JPY × sr_fib_confluence | -0.088 | 2.52 | -0.26 | +0.28 |
| EUR_USD × xs_momentum | -0.099 | 1.84 | -0.54 | +0.38 |
| USD_JPY × dt_bb_rsi_mr | -0.133 | 1.39 | -0.27 | +0.22 |
| USD_JPY × sr_break_retest | -0.133 | 2.88 | -0.53 | +0.40 |
| USD_JPY × dt_sr_channel_reversal | -0.084 | 2.82 | -0.49 | +0.34 |
| USD_JPY × intraday_seasonality | -0.204 | 2.14 | -2.06 | +0.56 |
| USD_JPY × dual_sr_bounce | -0.109 | 2.28 | -0.78 | +0.45 |
| EUR_USD × dt_bb_rsi_mr | -0.167 | 1.59 | -0.52 | +0.39 |
| EUR_USD × dt_sr_channel_reversal | -0.271 | 0.74 | -0.68 | -0.02 |
| EUR_USD × wick_imbalance_reversion | -0.318 | 1.48 | -1.04 | +0.55 |
| EUR_USD × dual_sr_bounce | +0.048 | 51.17 | -0.75 | +1.19 |
| EUR_USD × intraday_seasonality | +0.031 | 23.10 | -0.35 | +0.70 |
| USD_JPY × ema_cross | -0.403 | 0.70 | -0.85 | -0.03 |
| USD_JPY × wick_imbalance_reversion | -0.244 | 1.69 | -1.18 | +0.46 |
| EUR_USD × lin_reg_channel | +0.144 | 12.28 | -1.01 | +1.10 |
| EUR_USD × dt_fib_reversal | -0.016 | 17.76 | -0.95 | +0.65 |
| EUR_USD × htf_false_breakout | -0.202 | 0.41 | -0.24 | -0.09 |
| EUR_USD × ema200_trend_reversal | -0.214 | 0.87 | -0.61 | -0.07 |
| EUR_USD × london_fix_reversal | -0.221 | 1.05 | -0.68 | -0.05 |

## 判断プロトコル遵守 (CLAUDE.md)
- **本スキャンは 1 回 BT** → 実装判断は **保留** (lesson-reactive-changes)
- `unstable` 判定戦略も、post-hoc 分解のみで因果なし
- 次ステップ: Live N≥30 を経るか、別 BT 期間 (例 730d) で再検証

## Source
- pybroker walk-forward concept adapted for parameter-frozen regime
- Generated by: `tools/bt_walkforward.py`
