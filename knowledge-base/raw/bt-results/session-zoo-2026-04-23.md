# Session-Decomposition BT Scan

- **Generated**: 2026-04-23 03:56 UTC
- **Lookback**: 365d / **Interval**: 15m
- **Min N per (strategy × pair)**: 10
- **Sessions** (UTC, non-overlap):
  - Tokyo: 00:00–07:00 / London: 07:00–13:00 / NY: 13:00–21:00 / Off: 21:00–24:00

## 目的
Tokyo 時間に edge がある戦略は存在するか？ portfolio の session-bias を可視化。

## 全セル一覧 (Session 分解 × Pair × Strategy)

| Pair | Strategy | All N | All EV | Tokyo (N / WR / EV) | London (N / WR / EV) | NY (N / WR / EV) | Off (N / WR / EV) |
|------|----------|------:|-------:|--------------------|---------------------|------------------|-------------------|
| USD_JPY | streak_reversal | 468 | +1.37 | 104 / 69% / +1.55 | 242 / 72% / +1.18 | 118 / 75% / +1.32 | 4 / 100% / +9.35 |
| EUR_USD | session_time_bias | 405 | +0.15 | — / — / — | 325 / 64% / +0.19 | 80 / 55% / -0.04 | — / — / — |
| GBP_USD | session_time_bias | 395 | -0.05 | — / — / — | 312 / 60% / +0.01 | 83 / 49% / -0.28 | — / — / — |
| USD_JPY | session_time_bias | 342 | +0.17 | 342 / 65% / +0.17 | — / — / — | — / — / — | — / — / — |
| USD_JPY | xs_momentum | 288 | +0.12 | — / — / — | 69 / 56% / -0.08 | 219 / 66% / +0.18 | — / — / — |
| GBP_USD | xs_momentum | 274 | -0.19 | — / — / — | 47 / 64% / -0.02 | 227 / 55% / -0.23 | — / — / — |
| GBP_JPY | vwap_mean_reversion | 271 | +1.04 | 49 / 69% / +0.10 | 130 / 82% / +1.33 | 92 / 78% / +1.12 | — / — / — |
| GBP_USD | sr_fib_confluence | 258 | -0.06 | 38 / 53% / -0.25 | 135 / 60% / -0.03 | 85 / 56% / -0.03 | — / — / — |
| EUR_USD | sr_fib_confluence | 241 | -0.03 | — / — / — | 136 / 62% / +0.15 | 105 / 50% / -0.26 | — / — / — |
| EUR_USD | xs_momentum | 237 | +0.09 | — / — / — | 60 / 65% / +0.20 | 177 / 61% / +0.05 | — / — / — |
| EUR_JPY | vwap_mean_reversion | 225 | +0.70 | 54 / 74% / +1.03 | 96 / 66% / +0.53 | 75 / 68% / +0.69 | — / — / — |
| GBP_JPY | sr_fib_confluence | 213 | +0.05 | 30 / 70% / +0.26 | 89 / 62% / +0.03 | 94 / 60% / +0.01 | — / — / — |
| EUR_JPY | sr_fib_confluence | 196 | +0.14 | 24 / 67% / +0.13 | 92 / 63% / +0.19 | 80 / 61% / +0.08 | — / — / — |
| EUR_JPY | dt_sr_channel_reversal | 185 | +0.02 | 50 / 52% / -0.03 | 66 / 67% / +0.03 | 61 / 56% / +0.01 | 8 / 75% / +0.37 |
| GBP_USD | vwap_mean_reversion | 178 | +0.80 | 42 / 60% / +0.70 | 93 / 70% / +1.02 | 43 / 58% / +0.43 | — / — / — |
| EUR_JPY | sr_break_retest | 172 | -0.02 | 41 / 76% / +0.37 | 74 / 60% / -0.07 | 57 / 51% / -0.23 | — / — / — |
| EUR_USD | vwap_mean_reversion | 165 | +0.98 | — / — / — | 119 / 68% / +0.92 | 46 / 78% / +1.15 | — / — / — |
| GBP_JPY | sr_break_retest | 163 | +0.03 | 40 / 55% / -0.04 | 62 / 64% / +0.16 | 61 / 57% / -0.05 | — / — / — |
| GBP_JPY | dt_sr_channel_reversal | 160 | -0.09 | 46 / 65% / +0.14 | 62 / 50% / -0.12 | 48 / 44% / -0.32 | 4 / 75% / +0.52 |
| USD_JPY | sr_fib_confluence | 151 | -0.06 | 23 / 44% / -0.40 | 78 / 59% / +0.09 | 50 / 52% / -0.14 | — / — / — |
| GBP_JPY | dual_sr_bounce | 136 | +0.15 | 20 / 65% / +0.07 | 67 / 70% / +0.31 | 49 / 57% / -0.04 | — / — / — |
| USD_JPY | vwap_mean_reversion | 123 | +1.11 | 30 / 80% / +1.71 | 45 / 62% / +0.44 | 48 / 77% / +1.37 | — / — / — |
| GBP_JPY | intraday_seasonality | 119 | +0.07 | 11 / 82% / +0.86 | 62 / 60% / -0.03 | 46 / 59% / +0.01 | — / — / — |
| EUR_JPY | dual_sr_bounce | 118 | +0.19 | 17 / 65% / +0.27 | 55 / 74% / +0.39 | 46 / 56% / -0.08 | — / — / — |
| GBP_USD | dt_bb_rsi_mr | 117 | -0.22 | 33 / 54% / -0.28 | 25 / 44% / -0.12 | 51 / 45% / -0.20 | 8 / 38% / -0.44 |
| USD_JPY | dt_bb_rsi_mr | 113 | -0.00 | 25 / 60% / -0.04 | 34 / 44% / -0.18 | 50 / 56% / +0.09 | 4 / 100% / +0.65 |
| GBP_USD | trendline_sweep | 108 | +0.34 | 18 / 67% / +0.31 | 56 / 66% / +0.06 | 34 / 74% / +0.81 | — / — / — |
| USD_JPY | vix_carry_unwind | 104 | +0.65 | 49 / 67% / +0.36 | 25 / 72% / +0.73 | 17 / 76% / +0.91 | 13 / 77% / +1.18 |
| GBP_USD | gbp_deep_pullback | 100 | +0.44 | 25 / 64% / +1.08 | 49 / 57% / +0.23 | 22 / 64% / +0.36 | 4 / 50% / -0.62 |
| EUR_JPY | wick_imbalance_reversion | 94 | +0.03 | 22 / 59% / -0.11 | 46 / 70% / +0.24 | 26 / 58% / -0.21 | — / — / — |
| GBP_JPY | wick_imbalance_reversion | 93 | +0.07 | 24 / 54% / -0.24 | 34 / 76% / +0.54 | 35 / 57% / -0.17 | — / — / — |
| EUR_JPY | intraday_seasonality | 88 | -0.03 | 9 / 56% / -0.23 | 49 / 63% / -0.03 | 30 / 63% / +0.02 | — / — / — |
| USD_JPY | dual_sr_bounce | 82 | +0.02 | 8 / 62% / +0.05 | 40 / 55% / -0.11 | 34 / 68% / +0.17 | — / — / — |
| USD_JPY | intraday_seasonality | 81 | -0.06 | 16 / 75% / +0.56 | 44 / 52% / -0.41 | 21 / 67% / +0.21 | — / — / — |
| USD_JPY | dt_sr_channel_reversal | 76 | -0.37 | 11 / 36% / -0.34 | 29 / 34% / -0.50 | 32 / 44% / -0.35 | 4 / 75% / +0.37 |
| EUR_JPY | dt_fib_reversal | 76 | -0.38 | 17 / 47% / -0.47 | 32 / 47% / -0.41 | 27 / 48% / -0.29 | — / — / — |
| USD_JPY | sr_break_retest | 72 | -0.12 | 15 / 40% / -0.57 | 41 / 61% / +0.00 | 16 / 62% / -0.02 | — / — / — |
| EUR_USD | dt_bb_rsi_mr | 69 | -0.19 | — / — / — | 38 / 45% / -0.21 | 31 / 48% / -0.17 | — / — / — |
| GBP_USD | dual_sr_bounce | 69 | -0.23 | 14 / 43% / -0.85 | 31 / 61% / -0.05 | 24 / 54% / -0.09 | — / — / — |
| USD_JPY | vol_spike_mr | 68 | -0.21 | 17 / 53% / +0.09 | 31 / 48% / -0.40 | 20 / 50% / -0.17 | — / — / — |
| GBP_JPY | dt_fib_reversal | 67 | +0.28 | 16 / 88% / +0.70 | 25 / 60% / -0.01 | 26 / 69% / +0.31 | — / — / — |
| GBP_USD | dt_sr_channel_reversal | 66 | -0.07 | 13 / 54% / -0.20 | 18 / 56% / +0.10 | 29 / 52% / -0.07 | 6 / 50% / -0.28 |
| GBP_USD | intraday_seasonality | 63 | -0.24 | 15 / 53% / -0.60 | 42 / 67% / +0.03 | 6 / 33% / -1.20 | — / — / — |
| EUR_USD | trendline_sweep | 57 | +0.60 | — / — / — | 43 / 74% / +0.59 | 14 / 79% / +0.66 | — / — / — |
| GBP_USD | london_fix_reversal | 54 | -0.32 | — / — / — | — / — / — | 54 / 43% / -0.32 | — / — / — |
| EUR_USD | london_fix_reversal | 52 | -0.05 | — / — / — | — / — / — | 52 / 56% / -0.05 | — / — / — |
| USD_JPY | london_fix_reversal | 50 | +0.11 | — / — / — | — / — / — | 50 / 60% / +0.11 | — / — / — |
| GBP_USD | turtle_soup | 50 | +0.53 | 9 / 56% / +1.05 | 19 / 53% / +0.07 | 22 / 77% / +0.71 | — / — / — |
| GBP_USD | sr_break_retest | 48 | -0.46 | 22 / 54% / -0.39 | 17 / 47% / -0.55 | 9 / 44% / -0.47 | — / — / — |
| GBP_JPY | ema200_trend_reversal | 47 | +0.27 | 4 / 75% / +0.32 | 30 / 70% / +0.22 | 13 / 77% / +0.35 | — / — / — |
| GBP_JPY | ema_cross | 46 | +0.27 | 7 / 71% / +0.15 | 22 / 73% / +0.42 | 17 / 65% / +0.14 | — / — / — |
| EUR_USD | intraday_seasonality | 45 | -0.22 | — / — / — | 26 / 58% / -0.17 | 19 / 42% / -0.29 | — / — / — |
| GBP_USD | ema200_trend_reversal | 40 | -0.20 | 13 / 62% / -0.14 | 10 / 80% / +0.48 | 17 / 41% / -0.64 | — / — / — |
| GBP_USD | wick_imbalance_reversion | 38 | +0.38 | 8 / 62% / -0.28 | 20 / 80% / +0.40 | 10 / 90% / +0.86 | — / — / — |
| EUR_JPY | ema200_trend_reversal | 37 | +0.08 | 7 / 71% / +0.25 | 17 / 59% / -0.05 | 13 / 69% / +0.16 | — / — / — |
| EUR_USD | dual_sr_bounce | 35 | -0.28 | — / — / — | 18 / 44% / -0.42 | 17 / 53% / -0.14 | — / — / — |
| GBP_JPY | htf_false_breakout | 35 | +0.70 | 4 / 75% / +0.57 | 18 / 78% / +0.78 | 13 / 77% / +0.63 | — / — / — |
| EUR_JPY | htf_false_breakout | 34 | +0.09 | 6 / 67% / +0.55 | 14 / 57% / -0.26 | 14 / 64% / +0.24 | — / — / — |
| EUR_JPY | ema_cross | 34 | -0.06 | 7 / 57% / -0.07 | 15 / 73% / +0.28 | 12 / 42% / -0.48 | — / — / — |
| EUR_USD | dt_sr_channel_reversal | 33 | +0.01 | — / — / — | 19 / 58% / -0.14 | 14 / 57% / +0.21 | — / — / — |
| EUR_USD | wick_imbalance_reversion | 33 | -0.06 | — / — / — | 19 / 63% / +0.07 | 14 / 43% / -0.24 | — / — / — |
| EUR_USD | orb_trap | 32 | -0.38 | — / — / — | 16 / 31% / -0.63 | 16 / 44% / -0.13 | — / — / — |
| USD_JPY | wick_imbalance_reversion | 30 | -0.46 | 3 / 67% / +0.08 | 14 / 57% / -0.18 | 13 / 31% / -0.89 | — / — / — |
| GBP_USD | dt_fib_reversal | 30 | -0.14 | 12 / 50% / -0.29 | 9 / 67% / +0.03 | 9 / 56% / -0.10 | — / — / — |
| EUR_USD | lin_reg_channel | 29 | +0.01 | — / — / — | 21 / 57% / -0.19 | 8 / 75% / +0.51 | — / — / — |
| GBP_USD | orb_trap | 28 | +0.11 | — / — / — | 10 / 70% / +0.32 | 18 / 61% / -0.00 | — / — / — |
| EUR_USD | post_news_vol | 24 | +0.81 | — / — / — | 20 / 70% / +0.77 | 4 / 75% / +1.05 | — / — / — |
| USD_JPY | ema200_trend_reversal | 23 | -0.14 | 3 / 67% / -0.04 | 11 / 36% / -0.66 | 9 / 78% / +0.47 | — / — / — |
| GBP_USD | htf_false_breakout | 23 | -0.23 | 5 / 100% / +0.82 | 6 / 50% / -0.47 | 12 / 42% / -0.55 | — / — / — |
| USD_JPY | dt_fib_reversal | 22 | +0.08 | 9 / 56% / -0.07 | 10 / 60% / -0.16 | 3 / 100% / +1.28 | — / — / — |
| USD_JPY | ema_cross | 21 | -0.36 | 7 / 29% / -1.07 | 10 / 50% / -0.24 | 4 / 75% / +0.62 | — / — / — |
| EUR_USD | dt_fib_reversal | 21 | -0.03 | — / — / — | 14 / 71% / +0.28 | 7 / 29% / -0.67 | — / — / — |
| GBP_USD | post_news_vol | 20 | +1.16 | 2 / 50% / -0.38 | 16 / 75% / +1.22 | 2 / 100% / +2.30 | — / — / — |
| EUR_USD | htf_false_breakout | 18 | +0.52 | — / — / — | 12 / 75% / +0.76 | 6 / 50% / +0.06 | — / — / — |
| GBP_USD | doji_breakout | 18 | +0.17 | 10 / 80% / +0.45 | 2 / 50% / -0.53 | 6 / 50% / -0.07 | — / — / — |
| EUR_JPY | jpy_basket_trend | 18 | +0.18 | 1 / 0% / -2.17 | 7 / 86% / +1.00 | 10 / 60% / -0.16 | — / — / — |
| USD_JPY | htf_false_breakout | 16 | +0.40 | 4 / 75% / +0.54 | 7 / 71% / +0.19 | 5 / 80% / +0.57 | — / — / — |
| USD_JPY | post_news_vol | 16 | +1.11 | — / — / — | 8 / 75% / +1.16 | 8 / 62% / +1.07 | — / — / — |
| EUR_USD | adx_trend_continuation | 16 | -0.18 | — / — / — | 15 / 47% / -0.37 | 1 / 100% / +2.64 | — / — / — |
| USD_JPY | orb_trap | 13 | -0.27 | — / — / — | 1 / 100% / +1.13 | 12 / 58% / -0.39 | — / — / — |
| EUR_USD | ema_cross | 13 | +0.02 | — / — / — | 9 / 67% / +0.13 | 4 / 50% / -0.23 | — / — / — |
| EUR_USD | squeeze_release_momentum | 12 | +0.33 | — / — / — | 9 / 78% / +0.64 | 3 / 33% / -0.59 | — / — / — |
| GBP_USD | ema_cross | 12 | -0.32 | 5 / 60% / +0.11 | 5 / 40% / -0.71 | 2 / 50% / -0.41 | — / — / — |
| EUR_USD | ema200_trend_reversal | 11 | -0.49 | — / — / — | 4 / 50% / -0.22 | 7 / 43% / -0.65 | — / — / — |
| EUR_USD | doji_breakout | 11 | +1.10 | — / — / — | 10 / 90% / +0.99 | 1 / 100% / +2.17 | — / — / — |

## 🗼 Tokyo-Session Edge Candidates (N≥10, EV>0)

| Pair | Strategy | Tokyo N | Tokyo EV | London EV | NY EV | 備考 |
|------|----------|--------:|---------:|----------:|------:|------|
| USD_JPY | vwap_mean_reversion | 30 | +1.71 | +0.44 | +1.37 | Tokyo 優位 |
| USD_JPY | streak_reversal | 104 | +1.55 | +1.18 | +1.32 | Tokyo 優位 |
| GBP_USD | gbp_deep_pullback | 25 | +1.08 | +0.23 | +0.36 | Tokyo 優位 |
| EUR_JPY | vwap_mean_reversion | 54 | +1.03 | +0.53 | +0.69 | Tokyo 優位 |
| GBP_JPY | intraday_seasonality | 11 | +0.86 | -0.03 | +0.01 |  |
| GBP_USD | vwap_mean_reversion | 42 | +0.70 | +1.02 | +0.43 |  |
| GBP_JPY | dt_fib_reversal | 16 | +0.70 | -0.01 | +0.31 |  |
| USD_JPY | intraday_seasonality | 16 | +0.56 | -0.41 | +0.21 |  |
| GBP_USD | doji_breakout | 10 | +0.45 | -0.53 | -0.07 | **Tokyo-only edge** |
| EUR_JPY | sr_break_retest | 41 | +0.37 | -0.07 | -0.23 | **Tokyo-only edge** |
| USD_JPY | vix_carry_unwind | 49 | +0.36 | +0.73 | +0.91 |  |
| GBP_USD | trendline_sweep | 18 | +0.31 | +0.06 | +0.81 |  |
| EUR_JPY | dual_sr_bounce | 17 | +0.27 | +0.39 | -0.08 |  |
| GBP_JPY | sr_fib_confluence | 30 | +0.26 | +0.03 | +0.01 | Tokyo 優位 |
| USD_JPY | session_time_bias | 342 | +0.17 | — | — | **Tokyo-only edge** |
| GBP_JPY | dt_sr_channel_reversal | 46 | +0.14 | -0.12 | -0.32 | **Tokyo-only edge** |
| EUR_JPY | sr_fib_confluence | 24 | +0.13 | +0.19 | +0.08 |  |
| GBP_JPY | vwap_mean_reversion | 49 | +0.10 | +1.33 | +1.12 |  |
| USD_JPY | vol_spike_mr | 17 | +0.09 | -0.40 | -0.17 | **Tokyo-only edge** |
| GBP_JPY | dual_sr_bounce | 20 | +0.07 | +0.31 | -0.04 |  |

## Portfolio Session Aggregate (全 pair × 全 strategy)

| Session | Total N | WR | Weighted EV | Total PnL | Share of N |
|---------|--------:|---:|------------:|----------:|-----------:|
| Tokyo | 1456 | 62.1% | +0.273 | +397.47 | 17.5% |
| London | 3758 | 62.6% | +0.256 | +961.06 | 45.1% |
| NY | 3065 | 58.4% | +0.123 | +376.38 | 36.8% |
| Off | 55 | 67.3% | +0.987 | +54.27 | 0.7% |

## 判断プロトコル遵守 (CLAUDE.md)
- 本スキャンは 1 回 BT の post-hoc 分解 → 実装判断は **保留** (lesson-reactive-changes)
- Tokyo-edge 発見 → 別期間 (730d or w60 walk-forward) で再検証必須
- session-specific filter 実装前に Shadow N≥30 での確認が必要

## Source
- Post-hoc classification of `app.run_daytrade_backtest` trade_log by entry_time hour (UTC)
- Generated by: `tools/bt_session_zoo.py`
