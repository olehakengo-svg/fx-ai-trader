# R2 cell-level 降格候補 LOCK list - 2026-05-03

Counterfactual: aggregate raw Kelly=-0.1737→-0.1381, MC60d=1.0000→0.9970, STOP_OANDA=15件, LOT_HALF=3件, KEEP=147件
Verdict: REJECT_INSUFFICIENT

## Source / pre-reg LOCK

- 一次ソース: `/tmp/live-trades-20260503.json`
- Live抽出: `is_shadow=0`, `status=CLOSED`, `outcome in (WIN, LOSS, BREAKEVEN)`, `pnl_pips != null`。
- XAU除外: `instrument NOT LIKE 'XAU%'`。
- Shadow行: 3930 件。R2判定・counterfactual集計には混入なし。
- Live N: 917 / Live期間: 2026-04-02T08:22:03.845542+00:00 -> 2026-05-01T16:32:18.959855+00:00。
- Bonferroni母数 m pre-reg LOCK: **394 cell**。alpha'=0.05/394=0.000127。事後変更なし。
- MC仕様: iterations=1000, horizon=60d, bootstrap=Live PnL分布, ruin=peak DD 50% of 1000 pips。
- `pgrep -f app.py`: sandbox-restricted-fallback (sysmon request failed with error: sysmond service not found; pgrep: Cannot get process list)
- OANDA転送停止・lot変更・本番DB書き込みは未実施。

## Aggregate counterfactual

Aggregate baseline: N=917, raw Kelly=-0.1737, clipped Kelly=0.0000, MC60d=1.0000, EV=-0.79p, Wilson_lo=0.3551, PF=0.695, maxDD=0.7480, total=-720.0p
Aggregate post-cut: N=808, raw Kelly=-0.1381, clipped Kelly=0.0000, MC60d=0.9970, EV=-0.63p, Wilson_lo=0.3653, PF=0.749, maxDD=0.5505, total=-512.0p

## STOP_OANDA

| action | entry_type | instrument | hour_bucket | N | WR | Wilson lo | EV pip | raw Kelly | total pip | PF | Bonf p(lower) | max DD | reason |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| STOP_OANDA | ema_cross | USD_JPY | 16 | 5 | 0.00% | 0.00% | -8.40 | +0.0000 | -42.0 | 0.000 | 1.0000 | 4.20% | counterfactual extension; LOCK threshold not fully met ext#1 |
| STOP_OANDA | vol_surge_detector | USD_JPY | 00 | 9 | 0.00% | 0.00% | -3.59 | +0.0000 | -32.3 | 0.000 | 1.0000 | 3.23% | counterfactual extension; LOCK threshold not fully met ext#2 |
| STOP_OANDA | bb_rsi_reversion | USD_JPY | 13 | 6 | 33.33% | 9.68% | -3.03 | -1.1667 | -18.2 | 0.222 | 1.0000 | 2.30% | LOCK threshold  |
| STOP_OANDA | bb_rsi_reversion | EUR_USD | 06 | 5 | 0.00% | 0.00% | -2.68 | +0.0000 | -13.4 | 0.000 | 1.0000 | 1.34% | counterfactual extension; LOCK threshold not fully met ext#3 |
| STOP_OANDA | bb_rsi_reversion | USD_JPY | 18 | 13 | 30.77% | 12.68% | -2.11 | -0.5696 | -27.4 | 0.351 | 1.0000 | 3.06% | LOCK threshold  |
| STOP_OANDA | fib_reversal | EUR_USD | 15 | 5 | 0.00% | 0.00% | -1.68 | +0.0000 | -8.4 | 0.000 | 1.0000 | 0.84% | counterfactual extension; LOCK threshold not fully met ext#4 |
| STOP_OANDA | macdh_reversal | EUR_USD | 07 | 5 | 40.00% | 11.76% | -1.52 | -1.1259 | -7.6 | 0.262 | 1.0000 | 0.95% | counterfactual extension; LOCK threshold not fully met ext#5 |
| STOP_OANDA | bb_rsi_reversion | USD_JPY | 10 | 6 | 16.67% | 3.01% | -1.35 | -0.2109 | -8.1 | 0.441 | 1.0000 | 1.12% | counterfactual extension; LOCK threshold not fully met ext#6 |
| STOP_OANDA | bb_rsi_reversion | USD_JPY | 11 | 8 | 37.50% | 13.68% | -0.96 | -0.3173 | -7.7 | 0.542 | 1.0000 | 1.38% | counterfactual extension; LOCK threshold not fully met ext#7 |
| STOP_OANDA | macdh_reversal | EUR_USD | 14 | 8 | 25.00% | 7.15% | -0.86 | -0.2240 | -6.9 | 0.527 | 1.0000 | 1.40% | counterfactual extension; LOCK threshold not fully met ext#8 |
| STOP_OANDA | bb_rsi_reversion | USD_JPY | 17 | 8 | 50.00% | 21.52% | -0.84 | -0.5492 | -6.7 | 0.477 | 1.0000 | 0.98% | counterfactual extension; LOCK threshold not fully met ext#9 |
| STOP_OANDA | bb_rsi_reversion | EUR_USD | 12 | 5 | 40.00% | 11.76% | -0.52 | -0.1405 | -2.6 | 0.740 | 1.0000 | 1.00% | counterfactual extension; LOCK threshold not fully met ext#10 |
| STOP_OANDA | bb_rsi_reversion | USD_JPY | 02 | 12 | 50.00% | 25.38% | -0.37 | -0.1746 | -4.4 | 0.741 | 1.0000 | 0.80% | counterfactual extension; LOCK threshold not fully met ext#11 |
| STOP_OANDA | fib_reversal | USD_JPY | 04 | 7 | 42.86% | 15.82% | -0.21 | -0.0765 | -1.5 | 0.848 | 1.0000 | 0.67% | counterfactual extension; LOCK threshold not fully met ext#12 |
| STOP_OANDA | bb_rsi_reversion | EUR_USD | 09 | 7 | 42.86% | 15.82% | -0.07 | -0.0228 | -0.5 | 0.949 | 1.0000 | 0.65% | counterfactual extension; LOCK threshold not fully met ext#13 |

## LOT_HALF

| action | entry_type | instrument | hour_bucket | N | WR | Wilson lo | EV pip | raw Kelly | total pip | PF | Bonf p(lower) | max DD | reason |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| LOT_HALF | bb_rsi_reversion | USD_JPY | 05 | 19 | 31.58% | 15.36% | -1.28 | -0.5727 | -24.3 | 0.355 | 1.0000 | 3.11% | LOCK threshold  |
| LOT_HALF | bb_rsi_reversion | USD_JPY | 16 | 15 | 40.00% | 19.82% | -0.59 | -0.1807 | -8.9 | 0.689 | 1.0000 | 2.52% | LOCK threshold  |
| LOT_HALF | bb_rsi_reversion | USD_JPY | 04 | 13 | 46.15% | 23.21% | -0.56 | -0.3584 | -7.3 | 0.563 | 1.0000 | 1.13% | LOCK threshold  |

## WATCH

| action | entry_type | instrument | hour_bucket | N | WR | Wilson lo | EV pip | raw Kelly | total pip | PF | Bonf p(lower) | max DD | reason |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| WATCH | donchian_momentum_breakout | EUR_USD | 11 | 1 | 0.00% | 0.00% | -30.30 | +0.0000 | -30.3 | 0.000 | 1.0000 | 3.03% | N<5, boundary, or threshold not met  |
| WATCH | trendline_sweep | GBP_USD | 18 | 1 | 0.00% | 0.00% | -23.60 | +0.0000 | -23.6 | 0.000 | 1.0000 | 2.36% | N<5, boundary, or threshold not met  |
| WATCH | streak_reversal | USD_JPY | 08 | 1 | 0.00% | 0.00% | -23.40 | +0.0000 | -23.4 | 0.000 | 1.0000 | 2.34% | N<5, boundary, or threshold not met  |
| WATCH | vwap_mean_reversion | EUR_JPY | 09 | 1 | 0.00% | 0.00% | -22.60 | +0.0000 | -22.6 | 0.000 | 1.0000 | 2.26% | N<5, boundary, or threshold not met  |
| WATCH | gbp_deep_pullback | GBP_USD | 06 | 1 | 0.00% | 0.00% | -22.50 | +0.0000 | -22.5 | 0.000 | 1.0000 | 2.25% | N<5, boundary, or threshold not met  |
| WATCH | xs_momentum | GBP_USD | 11 | 1 | 0.00% | 0.00% | -21.40 | +0.0000 | -21.4 | 0.000 | 1.0000 | 2.14% | N<5, boundary, or threshold not met  |
| WATCH | sr_break_retest | USD_JPY | 13 | 1 | 0.00% | 0.00% | -20.40 | +0.0000 | -20.4 | 0.000 | 1.0000 | 2.04% | N<5, boundary, or threshold not met  |
| WATCH | vwap_mean_reversion | GBP_JPY | 12 | 1 | 0.00% | 0.00% | -20.10 | +0.0000 | -20.1 | 0.000 | 1.0000 | 2.01% | N<5, boundary, or threshold not met  |
| WATCH | pivot_breakout | USD_JPY | 14 | 1 | 0.00% | 0.00% | -19.90 | +0.0000 | -19.9 | 0.000 | 1.0000 | 1.99% | N<5, boundary, or threshold not met  |
| WATCH | donchian_momentum_breakout | EUR_USD | 07 | 1 | 0.00% | 0.00% | -19.10 | +0.0000 | -19.1 | 0.000 | 1.0000 | 1.91% | N<5, boundary, or threshold not met  |
| WATCH | vwap_mean_reversion | GBP_USD | 09 | 2 | 0.00% | 0.00% | -18.95 | +0.0000 | -37.9 | 0.000 | 1.0000 | 3.79% | N<5, boundary, or threshold not met  |
| WATCH | sr_fib_confluence | EUR_USD | 10 | 1 | 0.00% | 0.00% | -18.20 | +0.0000 | -18.2 | 0.000 | 1.0000 | 1.82% | N<5, boundary, or threshold not met  |
| WATCH | donchian_momentum_breakout | EUR_USD | 08 | 1 | 0.00% | 0.00% | -17.70 | +0.0000 | -17.7 | 0.000 | 1.0000 | 1.77% | N<5, boundary, or threshold not met  |
| WATCH | dt_sr_channel_reversal | EUR_JPY | 15 | 1 | 0.00% | 0.00% | -17.40 | +0.0000 | -17.4 | 0.000 | 1.0000 | 1.74% | N<5, boundary, or threshold not met  |
| WATCH | sr_fib_confluence | USD_JPY | 11 | 2 | 0.00% | 0.00% | -16.90 | +0.0000 | -33.8 | 0.000 | 1.0000 | 3.38% | N<5, boundary, or threshold not met  |
| WATCH | vwap_mean_reversion | GBP_USD | 13 | 1 | 0.00% | 0.00% | -14.10 | +0.0000 | -14.1 | 0.000 | 1.0000 | 1.41% | N<5, boundary, or threshold not met  |
| WATCH | session_time_bias | GBP_USD | 19 | 1 | 0.00% | 0.00% | -12.90 | +0.0000 | -12.9 | 0.000 | 1.0000 | 1.29% | N<5, boundary, or threshold not met  |
| WATCH | xs_momentum | USD_JPY | 06 | 1 | 0.00% | 0.00% | -11.90 | +0.0000 | -11.9 | 0.000 | 1.0000 | 1.19% | N<5, boundary, or threshold not met  |
| WATCH | sr_fib_confluence | GBP_JPY | 03 | 1 | 0.00% | 0.00% | -11.50 | +0.0000 | -11.5 | 0.000 | 1.0000 | 1.15% | N<5, boundary, or threshold not met  |
| WATCH | sr_fib_confluence | USD_JPY | 15 | 1 | 0.00% | 0.00% | -11.40 | +0.0000 | -11.4 | 0.000 | 1.0000 | 1.14% | N<5, boundary, or threshold not met  |
| WATCH | sr_fib_confluence | EUR_JPY | 06 | 1 | 0.00% | 0.00% | -11.30 | +0.0000 | -11.3 | 0.000 | 1.0000 | 1.13% | N<5, boundary, or threshold not met  |
| WATCH | sr_break_retest | USD_JPY | 03 | 1 | 0.00% | 0.00% | -11.20 | +0.0000 | -11.2 | 0.000 | 1.0000 | 1.12% | N<5, boundary, or threshold not met  |
| WATCH | sr_break_retest | USD_JPY | 10 | 1 | 0.00% | 0.00% | -11.10 | +0.0000 | -11.1 | 0.000 | 1.0000 | 1.11% | N<5, boundary, or threshold not met  |
| WATCH | doji_breakout | EUR_USD | 07 | 1 | 0.00% | 0.00% | -10.60 | +0.0000 | -10.6 | 0.000 | 1.0000 | 1.06% | N<5, boundary, or threshold not met  |
| WATCH | xs_momentum | USD_JPY | 12 | 1 | 0.00% | 0.00% | -10.50 | +0.0000 | -10.5 | 0.000 | 1.0000 | 1.05% | N<5, boundary, or threshold not met  |
| WATCH | dt_sr_channel_reversal | GBP_USD | 14 | 1 | 0.00% | 0.00% | -10.40 | +0.0000 | -10.4 | 0.000 | 1.0000 | 1.04% | N<5, boundary, or threshold not met  |
| WATCH | vwap_mean_reversion | EUR_JPY | 14 | 1 | 0.00% | 0.00% | -10.10 | +0.0000 | -10.1 | 0.000 | 1.0000 | 1.01% | N<5, boundary, or threshold not met  |
| WATCH | doji_breakout | GBP_USD | 12 | 1 | 0.00% | 0.00% | -10.10 | +0.0000 | -10.1 | 0.000 | 1.0000 | 1.01% | N<5, boundary, or threshold not met  |
| WATCH | sr_fib_confluence | GBP_USD | 15 | 1 | 0.00% | 0.00% | -10.10 | +0.0000 | -10.1 | 0.000 | 1.0000 | 1.01% | N<5, boundary, or threshold not met  |
| WATCH | lin_reg_channel | EUR_USD | 10 | 1 | 0.00% | 0.00% | -9.60 | +0.0000 | -9.6 | 0.000 | 1.0000 | 0.96% | N<5, boundary, or threshold not met  |
| WATCH | ema_cross | USD_JPY | 15 | 4 | 0.00% | 0.00% | -9.50 | +0.0000 | -38.0 | 0.000 | 1.0000 | 3.80% | N<5, boundary, or threshold not met  |
| WATCH | vix_carry_unwind | USD_JPY | 07 | 3 | 0.00% | 0.00% | -9.43 | +0.0000 | -28.3 | 0.000 | 1.0000 | 2.83% | N<5, boundary, or threshold not met  |
| WATCH | dt_bb_rsi_mr | EUR_USD | 15 | 2 | 0.00% | 0.00% | -9.35 | +0.0000 | -18.7 | 0.000 | 1.0000 | 1.87% | N<5, boundary, or threshold not met  |
| WATCH | ema_cross | GBP_USD | 17 | 1 | 0.00% | 0.00% | -9.30 | +0.0000 | -9.3 | 0.000 | 1.0000 | 0.93% | N<5, boundary, or threshold not met  |
| WATCH | sr_fib_confluence | GBP_USD | 17 | 2 | 0.00% | 0.00% | -9.20 | +0.0000 | -18.4 | 0.000 | 1.0000 | 1.84% | N<5, boundary, or threshold not met  |
| WATCH | dt_sr_channel_reversal | GBP_USD | 20 | 1 | 0.00% | 0.00% | -9.10 | +0.0000 | -9.1 | 0.000 | 1.0000 | 0.91% | N<5, boundary, or threshold not met  |
| WATCH | dt_sr_channel_reversal | GBP_USD | 13 | 1 | 0.00% | 0.00% | -9.00 | +0.0000 | -9.0 | 0.000 | 1.0000 | 0.90% | N<5, boundary, or threshold not met  |
| WATCH | ema200_trend_reversal | USD_JPY | 20 | 1 | 0.00% | 0.00% | -8.90 | +0.0000 | -8.9 | 0.000 | 1.0000 | 0.89% | N<5, boundary, or threshold not met  |
| WATCH | ema200_trend_reversal | USD_JPY | 17 | 1 | 0.00% | 0.00% | -8.00 | +0.0000 | -8.0 | 0.000 | 1.0000 | 0.80% | N<5, boundary, or threshold not met  |
| WATCH | dt_sr_channel_reversal | GBP_USD | 18 | 1 | 0.00% | 0.00% | -7.30 | +0.0000 | -7.3 | 0.000 | 1.0000 | 0.73% | N<5, boundary, or threshold not met  |
| WATCH | post_news_vol | GBP_USD | 06 | 1 | 0.00% | 0.00% | -7.20 | +0.0000 | -7.2 | 0.000 | 1.0000 | 0.72% | N<5, boundary, or threshold not met  |
| WATCH | trend_rebound | GBP_USD | 16 | 1 | 0.00% | 0.00% | -7.10 | +0.0000 | -7.1 | 0.000 | 1.0000 | 0.71% | N<5, boundary, or threshold not met  |
| WATCH | dt_fib_reversal | USD_JPY | 00 | 1 | 0.00% | 0.00% | -6.80 | +0.0000 | -6.8 | 0.000 | 1.0000 | 0.68% | N<5, boundary, or threshold not met  |
| WATCH | session_time_bias | GBP_USD | 06 | 3 | 0.00% | 0.00% | -6.73 | +0.0000 | -20.2 | 0.000 | 1.0000 | 2.02% | N<5, boundary, or threshold not met  |
| WATCH | mtf_reversal_confluence | GBP_USD | 12 | 1 | 0.00% | 0.00% | -6.70 | +0.0000 | -6.7 | 0.000 | 1.0000 | 0.67% | N<5, boundary, or threshold not met  |
| WATCH | vix_carry_unwind | USD_JPY | 03 | 2 | 50.00% | 9.45% | -6.55 | -0.6823 | -13.1 | 0.423 | 1.0000 | 2.27% | N<5, boundary, or threshold not met  |
| WATCH | sr_fib_confluence | EUR_USD | 02 | 2 | 0.00% | 0.00% | -6.40 | +0.0000 | -12.8 | 0.000 | 1.0000 | 1.28% | N<5, boundary, or threshold not met  |
| WATCH | sr_fib_confluence | EUR_USD | 12 | 2 | 0.00% | 0.00% | -6.30 | +0.0000 | -12.6 | 0.000 | 1.0000 | 1.26% | N<5, boundary, or threshold not met  |
| WATCH | ema_cross | USD_JPY | 13 | 2 | 0.00% | 0.00% | -6.25 | +0.0000 | -12.5 | 0.000 | 1.0000 | 1.25% | N<5, boundary, or threshold not met  |
| WATCH | dt_bb_rsi_mr | USD_JPY | 06 | 1 | 0.00% | 0.00% | -6.20 | +0.0000 | -6.2 | 0.000 | 1.0000 | 0.62% | N<5, boundary, or threshold not met  |
| WATCH | vol_momentum_scalp | USD_JPY | 08 | 1 | 0.00% | 0.00% | -6.20 | +0.0000 | -6.2 | 0.000 | 1.0000 | 0.62% | N<5, boundary, or threshold not met  |
| WATCH | trendline_sweep | EUR_GBP | 04 | 1 | 0.00% | 0.00% | -6.20 | +0.0000 | -6.2 | 0.000 | 1.0000 | 0.62% | N<5, boundary, or threshold not met  |
| WATCH | squeeze_release_momentum | GBP_USD | 06 | 1 | 0.00% | 0.00% | -6.10 | +0.0000 | -6.1 | 0.000 | 1.0000 | 0.61% | N<5, boundary, or threshold not met  |
| WATCH | bb_rsi_reversion | GBP_USD | 09 | 1 | 0.00% | 0.00% | -6.00 | +0.0000 | -6.0 | 0.000 | 1.0000 | 0.60% | N<5, boundary, or threshold not met  |
| WATCH | sr_fib_confluence | GBP_USD | 06 | 1 | 0.00% | 0.00% | -5.90 | +0.0000 | -5.9 | 0.000 | 1.0000 | 0.59% | N<5, boundary, or threshold not met  |
| WATCH | vol_momentum_scalp | GBP_USD | 11 | 1 | 0.00% | 0.00% | -5.70 | +0.0000 | -5.7 | 0.000 | 1.0000 | 0.57% | N<5, boundary, or threshold not met  |
| WATCH | ema_trend_scalp | GBP_USD | 13 | 1 | 0.00% | 0.00% | -5.50 | +0.0000 | -5.5 | 0.000 | 1.0000 | 0.55% | N<5, boundary, or threshold not met  |
| WATCH | dual_sr_bounce | USD_JPY | 16 | 1 | 0.00% | 0.00% | -5.50 | +0.0000 | -5.5 | 0.000 | 1.0000 | 0.55% | N<5, boundary, or threshold not met  |
| WATCH | sr_channel_reversal | GBP_USD | 09 | 1 | 0.00% | 0.00% | -5.40 | +0.0000 | -5.4 | 0.000 | 1.0000 | 0.54% | N<5, boundary, or threshold not met  |
| WATCH | session_time_bias | GBP_USD | 12 | 2 | 0.00% | 0.00% | -5.20 | +0.0000 | -10.4 | 0.000 | 1.0000 | 1.04% | N<5, boundary, or threshold not met  |
| WATCH | inducement_ob | EUR_GBP | 14 | 3 | 0.00% | 0.00% | -5.17 | +0.0000 | -15.5 | 0.000 | 1.0000 | 1.55% | N<5, boundary, or threshold not met  |
| WATCH | dt_bb_rsi_mr | GBP_USD | 16 | 2 | 50.00% | 9.45% | -5.10 | -4.2500 | -10.2 | 0.105 | 1.0000 | 1.14% | N<5, boundary, or threshold not met  |
| WATCH | ema_trend_scalp | GBP_USD | 06 | 1 | 0.00% | 0.00% | -5.10 | +0.0000 | -5.1 | 0.000 | 1.0000 | 0.51% | N<5, boundary, or threshold not met  |
| WATCH | squeeze_release_momentum | GBP_USD | 02 | 1 | 0.00% | 0.00% | -5.10 | +0.0000 | -5.1 | 0.000 | 1.0000 | 0.51% | N<5, boundary, or threshold not met  |
| WATCH | inducement_ob | EUR_GBP | 15 | 1 | 0.00% | 0.00% | -5.10 | +0.0000 | -5.1 | 0.000 | 1.0000 | 0.51% | N<5, boundary, or threshold not met  |
| WATCH | sr_fib_confluence | EUR_USD | 06 | 1 | 0.00% | 0.00% | -5.10 | +0.0000 | -5.1 | 0.000 | 1.0000 | 0.51% | N<5, boundary, or threshold not met  |
| WATCH | ema_cross | USD_JPY | 17 | 2 | 0.00% | 0.00% | -5.05 | +0.0000 | -10.1 | 0.000 | 1.0000 | 1.01% | N<5, boundary, or threshold not met  |
| WATCH | dual_sr_bounce | USD_JPY | 13 | 1 | 0.00% | 0.00% | -5.00 | +0.0000 | -5.0 | 0.000 | 1.0000 | 0.50% | N<5, boundary, or threshold not met  |
| WATCH | inducement_ob | EUR_GBP | 09 | 1 | 0.00% | 0.00% | -5.00 | +0.0000 | -5.0 | 0.000 | 1.0000 | 0.50% | N<5, boundary, or threshold not met  |
| WATCH | ema_trend_scalp | USD_JPY | 14 | 1 | 0.00% | 0.00% | -4.90 | +0.0000 | -4.9 | 0.000 | 1.0000 | 0.49% | N<5, boundary, or threshold not met  |
| WATCH | dt_bb_rsi_mr | USD_JPY | 12 | 1 | 0.00% | 0.00% | -4.50 | +0.0000 | -4.5 | 0.000 | 1.0000 | 0.45% | N<5, boundary, or threshold not met  |
| WATCH | dual_sr_bounce | USD_JPY | 05 | 3 | 0.00% | 0.00% | -4.47 | +0.0000 | -13.4 | 0.000 | 1.0000 | 1.34% | N<5, boundary, or threshold not met  |
| WATCH | sr_fib_confluence | USD_JPY | 05 | 1 | 0.00% | 0.00% | -4.40 | +0.0000 | -4.4 | 0.000 | 1.0000 | 0.44% | N<5, boundary, or threshold not met  |
| WATCH | trendline_sweep | GBP_USD | 07 | 1 | 0.00% | 0.00% | -4.30 | +0.0000 | -4.3 | 0.000 | 1.0000 | 0.43% | N<5, boundary, or threshold not met  |
| WATCH | engulfing_bb | USD_JPY | 16 | 1 | 0.00% | 0.00% | -4.30 | +0.0000 | -4.3 | 0.000 | 1.0000 | 0.43% | N<5, boundary, or threshold not met  |
| WATCH | v_reversal | USD_JPY | 16 | 1 | 0.00% | 0.00% | -4.00 | +0.0000 | -4.0 | 0.000 | 1.0000 | 0.40% | N<5, boundary, or threshold not met  |
| WATCH | vol_surge_detector | GBP_USD | 08 | 1 | 0.00% | 0.00% | -3.90 | +0.0000 | -3.9 | 0.000 | 1.0000 | 0.39% | N<5, boundary, or threshold not met  |
| WATCH | fib_reversal | USD_JPY | 10 | 2 | 0.00% | 0.00% | -3.85 | +0.0000 | -7.7 | 0.000 | 1.0000 | 0.77% | N<5, boundary, or threshold not met  |
| WATCH | sr_channel_reversal | USD_JPY | 07 | 3 | 0.00% | 0.00% | -3.83 | +0.0000 | -11.5 | 0.000 | 1.0000 | 1.15% | N<5, boundary, or threshold not met  |
| WATCH | fib_reversal | USD_JPY | 20 | 2 | 0.00% | 0.00% | -3.80 | +0.0000 | -7.6 | 0.000 | 1.0000 | 0.76% | N<5, boundary, or threshold not met  |
| WATCH | vol_momentum_scalp | GBP_USD | 14 | 1 | 0.00% | 0.00% | -3.80 | +0.0000 | -3.8 | 0.000 | 1.0000 | 0.38% | N<5, boundary, or threshold not met  |
| WATCH | bb_rsi_reversion | EUR_USD | 02 | 2 | 0.00% | 0.00% | -3.70 | +0.0000 | -7.4 | 0.000 | 1.0000 | 0.74% | N<5, boundary, or threshold not met  |
| WATCH | fib_reversal | USD_JPY | 18 | 1 | 0.00% | 0.00% | -3.70 | +0.0000 | -3.7 | 0.000 | 1.0000 | 0.37% | N<5, boundary, or threshold not met  |
| WATCH | macdh_reversal | USD_JPY | 17 | 2 | 0.00% | 0.00% | -3.65 | +0.0000 | -7.3 | 0.000 | 1.0000 | 0.73% | N<5, boundary, or threshold not met  |
| WATCH | trend_rebound | USD_JPY | 05 | 1 | 0.00% | 0.00% | -3.60 | +0.0000 | -3.6 | 0.000 | 1.0000 | 0.36% | N<5, boundary, or threshold not met  |
| WATCH | v_reversal | USD_JPY | 13 | 1 | 0.00% | 0.00% | -3.60 | +0.0000 | -3.6 | 0.000 | 1.0000 | 0.36% | N<5, boundary, or threshold not met  |
| WATCH | macdh_reversal | USD_JPY | 16 | 1 | 0.00% | 0.00% | -3.60 | +0.0000 | -3.6 | 0.000 | 1.0000 | 0.36% | N<5, boundary, or threshold not met  |
| WATCH | bb_rsi_reversion | GBP_USD | 15 | 2 | 0.00% | 0.00% | -3.55 | +0.0000 | -7.1 | 0.000 | 1.0000 | 0.71% | N<5, boundary, or threshold not met  |
| WATCH | sr_fib_confluence | USD_JPY | 14 | 3 | 33.33% | 6.15% | -3.53 | -2.5238 | -10.6 | 0.117 | 1.0000 | 1.06% | N<5, boundary, or threshold not met  |
| WATCH | fib_reversal | USD_JPY | 14 | 4 | 0.00% | 0.00% | -3.52 | +0.0000 | -14.1 | 0.000 | 1.0000 | 1.41% | N<5, boundary, or threshold not met  |
| WATCH | bb_squeeze_breakout | USD_JPY | 00 | 1 | 0.00% | 0.00% | -3.50 | +0.0000 | -3.5 | 0.000 | 1.0000 | 0.35% | N<5, boundary, or threshold not met  |
| WATCH | dt_sr_channel_reversal | USD_JPY | 00 | 2 | 50.00% | 9.45% | -3.45 | -4.3125 | -6.9 | 0.104 | 1.0000 | 0.77% | N<5, boundary, or threshold not met  |
| WATCH | bb_squeeze_breakout | USD_JPY | 04 | 1 | 0.00% | 0.00% | -3.40 | +0.0000 | -3.4 | 0.000 | 1.0000 | 0.34% | N<5, boundary, or threshold not met  |
| WATCH | trend_rebound | USD_JPY | 10 | 1 | 0.00% | 0.00% | -3.40 | +0.0000 | -3.4 | 0.000 | 1.0000 | 0.34% | N<5, boundary, or threshold not met  |
| WATCH | trend_rebound | USD_JPY | 18 | 1 | 0.00% | 0.00% | -3.40 | +0.0000 | -3.4 | 0.000 | 1.0000 | 0.34% | N<5, boundary, or threshold not met  |
| WATCH | vol_momentum_scalp | USD_JPY | 12 | 2 | 0.00% | 0.00% | -3.30 | +0.0000 | -6.6 | 0.000 | 1.0000 | 0.66% | N<5, boundary, or threshold not met  |
| WATCH | ema_trend_scalp | EUR_USD | 10 | 1 | 0.00% | 0.00% | -3.30 | +0.0000 | -3.3 | 0.000 | 1.0000 | 0.33% | N<5, boundary, or threshold not met  |
| WATCH | ema_ribbon_ride | USD_JPY | 18 | 1 | 0.00% | 0.00% | -3.30 | +0.0000 | -3.3 | 0.000 | 1.0000 | 0.33% | N<5, boundary, or threshold not met  |
| WATCH | ema_ribbon_ride | EUR_USD | 18 | 1 | 0.00% | 0.00% | -3.30 | +0.0000 | -3.3 | 0.000 | 1.0000 | 0.33% | N<5, boundary, or threshold not met  |
| WATCH | sr_channel_reversal | EUR_USD | 14 | 1 | 0.00% | 0.00% | -3.20 | +0.0000 | -3.2 | 0.000 | 1.0000 | 0.32% | N<5, boundary, or threshold not met  |
| WATCH | three_bar_reversal | USD_JPY | 02 | 1 | 0.00% | 0.00% | -3.20 | +0.0000 | -3.2 | 0.000 | 1.0000 | 0.32% | N<5, boundary, or threshold not met  |
| WATCH | stoch_trend_pullback | USD_JPY | 14 | 1 | 0.00% | 0.00% | -3.20 | +0.0000 | -3.2 | 0.000 | 1.0000 | 0.32% | N<5, boundary, or threshold not met  |
| WATCH | vol_surge_detector | EUR_USD | 09 | 1 | 0.00% | 0.00% | -3.20 | +0.0000 | -3.2 | 0.000 | 1.0000 | 0.32% | N<5, boundary, or threshold not met  |
| WATCH | bb_squeeze_breakout | USD_JPY | 03 | 1 | 0.00% | 0.00% | -3.20 | +0.0000 | -3.2 | 0.000 | 1.0000 | 0.32% | N<5, boundary, or threshold not met  |
| WATCH | macdh_reversal | USD_JPY | 15 | 1 | 0.00% | 0.00% | -3.20 | +0.0000 | -3.2 | 0.000 | 1.0000 | 0.32% | N<5, boundary, or threshold not met  |
| WATCH | trend_rebound | EUR_USD | 09 | 2 | 0.00% | 0.00% | -3.15 | +0.0000 | -6.3 | 0.000 | 1.0000 | 0.63% | N<5, boundary, or threshold not met  |
| WATCH | ema_pullback | USD_JPY | 12 | 2 | 0.00% | 0.00% | -3.10 | +0.0000 | -6.2 | 0.000 | 1.0000 | 0.62% | N<5, boundary, or threshold not met  |
| WATCH | ema_trend_scalp | USD_JPY | 05 | 1 | 0.00% | 0.00% | -3.10 | +0.0000 | -3.1 | 0.000 | 1.0000 | 0.31% | N<5, boundary, or threshold not met  |
| WATCH | bb_squeeze_breakout | USD_JPY | 02 | 1 | 0.00% | 0.00% | -3.10 | +0.0000 | -3.1 | 0.000 | 1.0000 | 0.31% | N<5, boundary, or threshold not met  |
| WATCH | stoch_trend_pullback | USD_JPY | 13 | 1 | 0.00% | 0.00% | -3.10 | +0.0000 | -3.1 | 0.000 | 1.0000 | 0.31% | N<5, boundary, or threshold not met  |
| WATCH | v_reversal | USD_JPY | 17 | 1 | 0.00% | 0.00% | -3.10 | +0.0000 | -3.1 | 0.000 | 1.0000 | 0.31% | N<5, boundary, or threshold not met  |
| WATCH | ema_trend_scalp | EUR_USD | 08 | 1 | 0.00% | 0.00% | -3.10 | +0.0000 | -3.1 | 0.000 | 1.0000 | 0.31% | N<5, boundary, or threshold not met  |
| WATCH | ema_ribbon_ride | EUR_USD | 17 | 1 | 0.00% | 0.00% | -3.10 | +0.0000 | -3.1 | 0.000 | 1.0000 | 0.31% | N<5, boundary, or threshold not met  |
| WATCH | bb_rsi_reversion | EUR_USD | 17 | 1 | 0.00% | 0.00% | -3.10 | +0.0000 | -3.1 | 0.000 | 1.0000 | 0.31% | N<5, boundary, or threshold not met  |
| WATCH | ema_pullback | USD_JPY | 14 | 1 | 0.00% | 0.00% | -3.10 | +0.0000 | -3.1 | 0.000 | 1.0000 | 0.31% | N<5, boundary, or threshold not met  |
| WATCH | vwap_mean_reversion | GBP_USD | 06 | 2 | 50.00% | 9.45% | -3.05 | -2.5417 | -6.1 | 0.164 | 1.0000 | 0.73% | N<5, boundary, or threshold not met  |
| WATCH | sr_channel_reversal | USD_JPY | 06 | 2 | 0.00% | 0.00% | -3.00 | +0.0000 | -6.0 | 0.000 | 1.0000 | 0.60% | N<5, boundary, or threshold not met  |
| WATCH | vol_surge_detector | USD_JPY | 05 | 2 | 0.00% | 0.00% | -3.00 | +0.0000 | -6.0 | 0.000 | 1.0000 | 0.60% | N<5, boundary, or threshold not met  |
| WATCH | engulfing_bb | EUR_USD | 11 | 2 | 0.00% | 0.00% | -3.00 | +0.0000 | -6.0 | 0.000 | 1.0000 | 0.60% | N<5, boundary, or threshold not met  |
| WATCH | stoch_trend_pullback | EUR_USD | 17 | 2 | 0.00% | 0.00% | -3.00 | +0.0000 | -6.0 | 0.000 | 1.0000 | 0.60% | N<5, boundary, or threshold not met  |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | 109 rows omitted |

## KEEP

| action | entry_type | instrument | hour_bucket | N | WR | Wilson lo | EV pip | raw Kelly | total pip | PF | Bonf p(lower) | max DD | reason |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| KEEP | bb_rsi_reversion | USD_JPY | 06 | 24 | 29.17% | 14.91% | +0.04 | +0.0053 | +1.0 | 1.019 | 1.0000 | 3.99% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | stoch_trend_pullback | EUR_USD | 14 | 1 | 100.00% | 20.65% | +0.10 | +0.0000 | +0.1 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | dt_bb_rsi_mr | EUR_USD | 08 | 2 | 50.00% | 9.45% | +0.10 | +0.0189 | +0.2 | 1.039 | 1.0000 | 0.51% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | USD_JPY | 03 | 20 | 50.00% | 29.93% | +0.10 | +0.0355 | +2.1 | 1.076 | 1.0000 | 1.57% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | trend_rebound | USD_JPY | 20 | 2 | 50.00% | 9.45% | +0.20 | +0.3333 | +0.4 | 3.000 | 1.0000 | 0.02% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | EUR_USD | 15 | 10 | 50.00% | 23.66% | +0.27 | +0.0833 | +2.7 | 1.200 | 1.0000 | 1.34% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | sr_channel_reversal | EUR_USD | 16 | 2 | 50.00% | 9.45% | +0.30 | +0.0600 | +0.6 | 1.136 | 1.0000 | 0.44% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | fib_reversal | EUR_USD | 14 | 4 | 50.00% | 15.00% | +0.33 | +0.0890 | +1.3 | 1.217 | 1.0000 | 0.60% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | USD_JPY | 19 | 6 | 66.67% | 30.00% | +0.37 | +0.1528 | +2.2 | 1.297 | 1.0000 | 0.74% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | EUR_USD | 13 | 9 | 44.44% | 18.88% | +0.39 | +0.0931 | +3.5 | 1.265 | 1.0000 | 0.87% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | USD_JPY | 01 | 12 | 58.33% | 31.95% | +0.40 | +0.1393 | +4.8 | 1.314 | 1.0000 | 0.45% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | USD_JPY | 20 | 4 | 50.00% | 15.00% | +0.45 | +0.1385 | +1.8 | 1.383 | 1.0000 | 0.47% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | USD_JPY | 14 | 5 | 60.00% | 23.07% | +0.46 | +0.0857 | +2.3 | 1.167 | 1.0000 | 0.77% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | vol_surge_detector | EUR_USD | 11 | 4 | 50.00% | 15.00% | +0.48 | +0.1900 | +1.9 | 1.613 | 1.0000 | 0.31% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | vol_momentum_scalp | USD_JPY | 15 | 3 | 66.67% | 20.77% | +0.53 | +0.2133 | +1.6 | 1.471 | 1.0000 | 0.34% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_squeeze_breakout | USD_JPY | 12 | 1 | 100.00% | 20.65% | +0.60 | +0.0000 | +0.6 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | EUR_USD | 00 | 1 | 100.00% | 20.65% | +0.60 | +0.0000 | +0.6 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | sr_channel_reversal | USD_JPY | 00 | 3 | 66.67% | 20.77% | +0.63 | +0.2184 | +1.9 | 1.487 | 1.0000 | 0.39% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | dt_sr_channel_reversal | USD_JPY | 08 | 1 | 100.00% | 20.65% | +0.70 | +0.0000 | +0.7 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | trend_rebound | USD_JPY | 08 | 2 | 50.00% | 9.45% | +0.70 | +0.1591 | +1.4 | 1.467 | 1.0000 | 0.30% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | USD_JPY | 12 | 14 | 42.86% | 21.38% | +0.74 | +0.1491 | +10.4 | 1.533 | 1.0000 | 0.63% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_squeeze_breakout | EUR_USD | 16 | 2 | 50.00% | 9.45% | +0.75 | +0.1667 | +1.5 | 1.500 | 1.0000 | 0.30% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | ema200_trend_reversal | USD_JPY | 13 | 1 | 100.00% | 20.65% | +0.80 | +0.0000 | +0.8 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | ema_trend_scalp | EUR_USD | 14 | 1 | 100.00% | 20.65% | +0.80 | +0.0000 | +0.8 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | donchian_momentum_breakout | EUR_USD | 10 | 1 | 100.00% | 20.65% | +0.80 | +0.0000 | +0.8 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | sr_channel_reversal | USD_JPY | 01 | 1 | 100.00% | 20.65% | +0.80 | +0.0000 | +0.8 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | dt_bb_rsi_mr | USD_JPY | 16 | 1 | 100.00% | 20.65% | +0.80 | +0.0000 | +0.8 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | dt_bb_rsi_mr | USD_JPY | 08 | 1 | 100.00% | 20.65% | +0.80 | +0.0000 | +0.8 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | vol_surge_detector | EUR_USD | 15 | 1 | 100.00% | 20.65% | +0.80 | +0.0000 | +0.8 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | engulfing_bb | USD_JPY | 15 | 1 | 100.00% | 20.65% | +0.80 | +0.0000 | +0.8 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | sr_fib_confluence | USD_JPY | 13 | 1 | 100.00% | 20.65% | +0.80 | +0.0000 | +0.8 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | ema_cross | USD_JPY | 05 | 1 | 100.00% | 20.65% | +0.80 | +0.0000 | +0.8 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | stoch_trend_pullback | EUR_USD | 07 | 3 | 33.33% | 6.15% | +0.83 | +0.0969 | +2.5 | 1.410 | 1.0000 | 0.61% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | ema_pullback | EUR_USD | 15 | 2 | 100.00% | 34.24% | +0.85 | +0.0000 | +1.7 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | trend_rebound | EUR_USD | 14 | 2 | 50.00% | 9.45% | +0.90 | +0.1500 | +1.8 | 1.429 | 1.0000 | 0.42% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | fib_reversal | EUR_USD | 13 | 6 | 50.00% | 18.76% | +0.93 | +0.3043 | +5.6 | 2.556 | 1.0000 | 0.35% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | USD_JPY | 07 | 11 | 63.64% | 35.38% | +0.94 | +0.2521 | +10.3 | 1.656 | 1.0000 | 0.98% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | vol_momentum_scalp | USD_JPY | 18 | 2 | 50.00% | 9.45% | +0.95 | +0.1827 | +1.9 | 1.576 | 1.0000 | 0.33% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | macdh_reversal | EUR_USD | 08 | 4 | 50.00% | 15.00% | +1.00 | +0.1739 | +4.0 | 1.533 | 1.0000 | 0.42% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | vol_surge_detector | USD_JPY | 13 | 4 | 75.00% | 30.06% | +1.05 | +0.4257 | +4.2 | 2.312 | 1.0000 | 0.32% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | USD_JPY | 00 | 12 | 58.33% | 31.95% | +1.07 | +0.2090 | +12.9 | 1.558 | 1.0000 | 1.35% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | gbp_deep_pullback | GBP_USD | 10 | 1 | 100.00% | 20.65% | +1.10 | +0.0000 | +1.1 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | sr_fib_confluence | GBP_USD | 11 | 1 | 100.00% | 20.65% | +1.10 | +0.0000 | +1.1 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | inducement_ob | EUR_GBP | 06 | 1 | 100.00% | 20.65% | +1.10 | +0.0000 | +1.1 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | trend_rebound | EUR_USD | 07 | 1 | 100.00% | 20.65% | +1.10 | +0.0000 | +1.1 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | stoch_trend_pullback | USD_JPY | 18 | 4 | 50.00% | 15.00% | +1.10 | +0.2037 | +4.4 | 1.688 | 1.0000 | 0.64% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | vol_surge_detector | GBP_USD | 13 | 2 | 100.00% | 34.24% | +1.15 | +0.0000 | +2.3 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | ema_trend_scalp | EUR_USD | 12 | 3 | 33.33% | 6.15% | +1.17 | +0.1178 | +3.5 | 1.547 | 1.0000 | 0.64% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | mtf_reversal_confluence | EUR_USD | 02 | 1 | 100.00% | 20.65% | +1.20 | +0.0000 | +1.2 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | mtf_reversal_confluence | USD_JPY | 10 | 1 | 100.00% | 20.65% | +1.20 | +0.0000 | +1.2 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | vol_surge_detector | USD_JPY | 06 | 7 | 57.14% | 25.05% | +1.27 | +0.2779 | +8.9 | 1.947 | 1.0000 | 0.32% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | session_time_bias | GBP_USD | 08 | 1 | 100.00% | 20.65% | +1.30 | +0.0000 | +1.3 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | post_news_vol | GBP_USD | 10 | 1 | 100.00% | 20.65% | +1.30 | +0.0000 | +1.3 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | engulfing_bb | GBP_USD | 10 | 1 | 100.00% | 20.65% | +1.30 | +0.0000 | +1.3 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | ema_cross | GBP_USD | 07 | 1 | 100.00% | 20.65% | +1.30 | +0.0000 | +1.3 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | sr_fib_confluence | GBP_USD | 02 | 1 | 100.00% | 20.65% | +1.30 | +0.0000 | +1.3 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | USD_JPY | 15 | 20 | 60.00% | 38.66% | +1.32 | +0.2454 | +26.5 | 1.692 | 1.0000 | 2.32% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | trendline_sweep | GBP_USD | 01 | 1 | 100.00% | 20.65% | +1.40 | +0.0000 | +1.4 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | fib_reversal | USD_JPY | 03 | 2 | 50.00% | 9.45% | +1.45 | +0.4265 | +2.9 | 6.800 | 1.0000 | 0.05% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | vol_surge_detector | USD_JPY | 07 | 2 | 50.00% | 9.45% | +1.45 | +0.2339 | +2.9 | 1.879 | 1.0000 | 0.33% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | vwap_mean_reversion | EUR_JPY | 15 | 1 | 100.00% | 20.65% | +1.50 | +0.0000 | +1.5 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | stoch_trend_pullback | USD_JPY | 02 | 1 | 100.00% | 20.65% | +1.50 | +0.0000 | +1.5 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | USD_JPY | 09 | 5 | 60.00% | 23.07% | +1.50 | +0.3191 | +7.5 | 2.136 | 1.0000 | 0.36% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_squeeze_breakout | EUR_USD | 15 | 2 | 50.00% | 9.45% | +1.55 | +0.2500 | +3.1 | 2.000 | 1.0000 | 0.31% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | sr_channel_reversal | EUR_USD | 07 | 3 | 33.33% | 6.15% | +1.57 | +0.1911 | +4.7 | 2.343 | 1.0000 | 0.35% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_squeeze_breakout | EUR_USD | 08 | 1 | 100.00% | 20.65% | +1.60 | +0.0000 | +1.6 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | macdh_reversal | USD_JPY | 19 | 4 | 50.00% | 15.00% | +1.60 | +0.2963 | +6.4 | 2.455 | 1.0000 | 0.36% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | fib_reversal | USD_JPY | 13 | 3 | 66.67% | 20.77% | +1.67 | +0.4115 | +5.0 | 2.613 | 1.0000 | 0.31% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | engulfing_bb | USD_JPY | 14 | 2 | 50.00% | 9.45% | +1.70 | +0.2576 | +3.4 | 2.062 | 1.0000 | 0.32% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | engulfing_bb | EUR_USD | 09 | 2 | 50.00% | 9.45% | +1.75 | +0.2692 | +3.5 | 2.167 | 1.0000 | 0.30% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | GBP_USD | 12 | 3 | 66.67% | 20.77% | +1.77 | +0.3099 | +5.3 | 1.869 | 1.0000 | 0.61% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | EUR_USD | 03 | 6 | 33.33% | 9.68% | +1.83 | +0.1724 | +11.0 | 4.143 | 1.0000 | 0.35% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | ema_pullback | USD_JPY | 13 | 2 | 100.00% | 34.24% | +1.85 | +0.0000 | +3.7 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | USD_JPY | 08 | 9 | 55.56% | 26.66% | +1.99 | +0.3098 | +17.9 | 2.261 | 1.0000 | 0.82% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | htf_false_breakout | EUR_USD | 15 | 1 | 100.00% | 20.65% | +2.00 | +0.0000 | +2.0 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | macdh_reversal | USD_JPY | 14 | 3 | 66.67% | 20.77% | +2.00 | +0.6061 | +6.0 | 11.000 | 1.0000 | 0.06% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | vwap_mean_reversion | EUR_JPY | 17 | 1 | 100.00% | 20.65% | +2.10 | +0.0000 | +2.1 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | mtf_reversal_confluence | USD_JPY | 15 | 2 | 50.00% | 9.45% | +2.10 | +0.0000 | +4.2 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | fib_reversal | EUR_USD | 07 | 5 | 60.00% | 23.07% | +2.14 | +0.3326 | +10.7 | 2.244 | 1.0000 | 0.55% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | stoch_trend_pullback | USD_JPY | 06 | 3 | 66.67% | 20.77% | +2.17 | +0.4467 | +6.5 | 3.031 | 1.0000 | 0.32% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | sr_break_retest | GBP_USD | 16 | 2 | 50.00% | 9.45% | +2.20 | +0.1350 | +4.4 | 1.370 | 1.0000 | 1.19% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | stoch_trend_pullback | EUR_USD | 13 | 2 | 50.00% | 9.45% | +2.25 | +0.4891 | +4.5 | 46.000 | 1.0000 | 0.01% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | stoch_trend_pullback | USD_JPY | 19 | 2 | 50.00% | 9.45% | +2.45 | +0.4455 | +4.9 | 9.167 | 1.0000 | 0.06% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | ema_trend_scalp | EUR_USD | 07 | 3 | 66.67% | 20.77% | +2.53 | +0.4780 | +7.6 | 3.533 | 1.0000 | 0.30% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | sr_fib_confluence | GBP_USD | 07 | 2 | 50.00% | 9.45% | +2.55 | +0.2297 | +5.1 | 1.850 | 1.0000 | 0.60% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | vol_surge_detector | USD_JPY | 15 | 3 | 100.00% | 43.85% | +2.67 | +0.0000 | +8.0 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | mtf_reversal_confluence | USD_JPY | 17 | 2 | 50.00% | 9.45% | +2.70 | +0.4355 | +5.4 | 7.750 | 1.0000 | 0.08% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | macdh_reversal | EUR_USD | 17 | 1 | 100.00% | 20.65% | +2.80 | +0.0000 | +2.8 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | fib_reversal | USD_JPY | 15 | 4 | 75.00% | 30.06% | +2.85 | +0.5897 | +11.4 | 4.677 | 1.0000 | 0.31% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | EUR_USD | 04 | 1 | 100.00% | 20.65% | +3.00 | +0.0000 | +3.0 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_squeeze_breakout | USD_JPY | 06 | 2 | 100.00% | 34.24% | +3.00 | +0.0000 | +6.0 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | vol_surge_detector | USD_JPY | 09 | 2 | 50.00% | 9.45% | +3.05 | +0.3315 | +6.1 | 2.968 | 1.0000 | 0.31% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | vol_surge_detector | USD_JPY | 01 | 1 | 100.00% | 20.65% | +3.20 | +0.0000 | +3.2 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | stoch_trend_pullback | EUR_USD | 15 | 1 | 100.00% | 20.65% | +3.20 | +0.0000 | +3.2 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | mtf_reversal_confluence | USD_JPY | 19 | 1 | 100.00% | 20.65% | +3.20 | +0.0000 | +3.2 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | orb_trap | GBP_USD | 14 | 2 | 50.00% | 9.45% | +3.40 | +0.1921 | +6.8 | 1.624 | 1.0000 | 1.09% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | dt_bb_rsi_mr | USD_JPY | 14 | 2 | 50.00% | 9.45% | +3.50 | +0.3977 | +7.0 | 4.889 | 1.0000 | 0.18% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | sr_fib_confluence | GBP_USD | 03 | 2 | 50.00% | 9.45% | +3.65 | +0.2626 | +7.3 | 2.106 | 1.0000 | 0.66% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | stoch_trend_pullback | USD_JPY | 07 | 1 | 100.00% | 20.65% | +4.20 | +0.0000 | +4.2 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | trend_rebound | USD_JPY | 04 | 1 | 100.00% | 20.65% | +4.20 | +0.0000 | +4.2 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | vol_momentum_scalp | USD_JPY | 05 | 1 | 100.00% | 20.65% | +4.20 | +0.0000 | +4.2 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | stoch_trend_pullback | USD_JPY | 05 | 1 | 100.00% | 20.65% | +4.20 | +0.0000 | +4.2 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | vol_momentum_scalp | USD_JPY | 11 | 4 | 100.00% | 51.01% | +4.20 | +0.0000 | +16.8 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | trend_rebound | EUR_USD | 16 | 1 | 100.00% | 20.65% | +4.30 | +0.0000 | +4.3 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | three_bar_reversal | USD_JPY | 17 | 1 | 100.00% | 20.65% | +4.60 | +0.0000 | +4.6 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | ema_pullback | USD_JPY | 15 | 2 | 100.00% | 34.24% | +4.80 | +0.0000 | +9.6 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | ema_trend_scalp | USD_JPY | 16 | 1 | 100.00% | 20.65% | +5.00 | +0.0000 | +5.0 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | sr_channel_reversal | USD_JPY | 12 | 1 | 100.00% | 20.65% | +5.00 | +0.0000 | +5.0 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | stoch_trend_pullback | USD_JPY | 01 | 1 | 100.00% | 20.65% | +5.50 | +0.0000 | +5.5 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | fib_reversal | USD_JPY | 01 | 2 | 100.00% | 34.24% | +5.70 | +0.0000 | +11.4 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | fib_reversal | USD_JPY | 09 | 1 | 100.00% | 20.65% | +6.00 | +0.0000 | +6.0 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | fib_reversal | GBP_USD | 07 | 1 | 100.00% | 20.65% | +7.00 | +0.0000 | +7.0 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | GBP_USD | 13 | 1 | 100.00% | 20.65% | +7.10 | +0.0000 | +7.1 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | sr_channel_reversal | GBP_USD | 13 | 1 | 100.00% | 20.65% | +7.20 | +0.0000 | +7.2 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | ema_trend_scalp | USD_JPY | 15 | 1 | 100.00% | 20.65% | +7.70 | +0.0000 | +7.7 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | gbp_deep_pullback | GBP_USD | 09 | 1 | 100.00% | 20.65% | +8.10 | +0.0000 | +8.1 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | ema_cross | USD_JPY | 14 | 4 | 100.00% | 51.01% | +8.10 | +0.0000 | +32.4 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | GBP_USD | 16 | 1 | 100.00% | 20.65% | +8.20 | +0.0000 | +8.2 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | v_reversal | USD_JPY | 14 | 1 | 100.00% | 20.65% | +8.80 | +0.0000 | +8.8 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | lin_reg_channel | EUR_USD | 15 | 1 | 100.00% | 20.65% | +8.80 | +0.0000 | +8.8 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | 27 rows omitted |

## KEEP protection / feedback_ma_filter_breaks_mr

- KEEP cell数: 147。EV>0 / Wilson_lo>0.50 / raw Kelly>0 の cell は R2対象外として明示維持。
- Bonferroni-significant候補またはEV>0のKEEP表示対象: 147。
- STOP_OANDA / LOT_HALF の選定は cell 単位で、entry_type 全体停止は提案していない。

| action | entry_type | instrument | hour_bucket | N | WR | Wilson lo | EV pip | raw Kelly | total pip | PF | Bonf p(lower) | max DD | reason |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| KEEP | bb_rsi_reversion | USD_JPY | 06 | 24 | 29.17% | 14.91% | +0.04 | +0.0053 | +1.0 | 1.019 | 1.0000 | 3.99% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | stoch_trend_pullback | EUR_USD | 14 | 1 | 100.00% | 20.65% | +0.10 | +0.0000 | +0.1 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | dt_bb_rsi_mr | EUR_USD | 08 | 2 | 50.00% | 9.45% | +0.10 | +0.0189 | +0.2 | 1.039 | 1.0000 | 0.51% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | USD_JPY | 03 | 20 | 50.00% | 29.93% | +0.10 | +0.0355 | +2.1 | 1.076 | 1.0000 | 1.57% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | trend_rebound | USD_JPY | 20 | 2 | 50.00% | 9.45% | +0.20 | +0.3333 | +0.4 | 3.000 | 1.0000 | 0.02% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | EUR_USD | 15 | 10 | 50.00% | 23.66% | +0.27 | +0.0833 | +2.7 | 1.200 | 1.0000 | 1.34% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | sr_channel_reversal | EUR_USD | 16 | 2 | 50.00% | 9.45% | +0.30 | +0.0600 | +0.6 | 1.136 | 1.0000 | 0.44% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | fib_reversal | EUR_USD | 14 | 4 | 50.00% | 15.00% | +0.33 | +0.0890 | +1.3 | 1.217 | 1.0000 | 0.60% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | USD_JPY | 19 | 6 | 66.67% | 30.00% | +0.37 | +0.1528 | +2.2 | 1.297 | 1.0000 | 0.74% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | EUR_USD | 13 | 9 | 44.44% | 18.88% | +0.39 | +0.0931 | +3.5 | 1.265 | 1.0000 | 0.87% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | USD_JPY | 01 | 12 | 58.33% | 31.95% | +0.40 | +0.1393 | +4.8 | 1.314 | 1.0000 | 0.45% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | USD_JPY | 20 | 4 | 50.00% | 15.00% | +0.45 | +0.1385 | +1.8 | 1.383 | 1.0000 | 0.47% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | USD_JPY | 14 | 5 | 60.00% | 23.07% | +0.46 | +0.0857 | +2.3 | 1.167 | 1.0000 | 0.77% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | vol_surge_detector | EUR_USD | 11 | 4 | 50.00% | 15.00% | +0.48 | +0.1900 | +1.9 | 1.613 | 1.0000 | 0.31% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | vol_momentum_scalp | USD_JPY | 15 | 3 | 66.67% | 20.77% | +0.53 | +0.2133 | +1.6 | 1.471 | 1.0000 | 0.34% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_squeeze_breakout | USD_JPY | 12 | 1 | 100.00% | 20.65% | +0.60 | +0.0000 | +0.6 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | EUR_USD | 00 | 1 | 100.00% | 20.65% | +0.60 | +0.0000 | +0.6 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | sr_channel_reversal | USD_JPY | 00 | 3 | 66.67% | 20.77% | +0.63 | +0.2184 | +1.9 | 1.487 | 1.0000 | 0.39% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | dt_sr_channel_reversal | USD_JPY | 08 | 1 | 100.00% | 20.65% | +0.70 | +0.0000 | +0.7 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | trend_rebound | USD_JPY | 08 | 2 | 50.00% | 9.45% | +0.70 | +0.1591 | +1.4 | 1.467 | 1.0000 | 0.30% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | USD_JPY | 12 | 14 | 42.86% | 21.38% | +0.74 | +0.1491 | +10.4 | 1.533 | 1.0000 | 0.63% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_squeeze_breakout | EUR_USD | 16 | 2 | 50.00% | 9.45% | +0.75 | +0.1667 | +1.5 | 1.500 | 1.0000 | 0.30% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | ema200_trend_reversal | USD_JPY | 13 | 1 | 100.00% | 20.65% | +0.80 | +0.0000 | +0.8 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | ema_trend_scalp | EUR_USD | 14 | 1 | 100.00% | 20.65% | +0.80 | +0.0000 | +0.8 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | donchian_momentum_breakout | EUR_USD | 10 | 1 | 100.00% | 20.65% | +0.80 | +0.0000 | +0.8 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | sr_channel_reversal | USD_JPY | 01 | 1 | 100.00% | 20.65% | +0.80 | +0.0000 | +0.8 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | dt_bb_rsi_mr | USD_JPY | 16 | 1 | 100.00% | 20.65% | +0.80 | +0.0000 | +0.8 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | dt_bb_rsi_mr | USD_JPY | 08 | 1 | 100.00% | 20.65% | +0.80 | +0.0000 | +0.8 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | vol_surge_detector | EUR_USD | 15 | 1 | 100.00% | 20.65% | +0.80 | +0.0000 | +0.8 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | engulfing_bb | USD_JPY | 15 | 1 | 100.00% | 20.65% | +0.80 | +0.0000 | +0.8 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | sr_fib_confluence | USD_JPY | 13 | 1 | 100.00% | 20.65% | +0.80 | +0.0000 | +0.8 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | ema_cross | USD_JPY | 05 | 1 | 100.00% | 20.65% | +0.80 | +0.0000 | +0.8 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | stoch_trend_pullback | EUR_USD | 07 | 3 | 33.33% | 6.15% | +0.83 | +0.0969 | +2.5 | 1.410 | 1.0000 | 0.61% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | ema_pullback | EUR_USD | 15 | 2 | 100.00% | 34.24% | +0.85 | +0.0000 | +1.7 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | trend_rebound | EUR_USD | 14 | 2 | 50.00% | 9.45% | +0.90 | +0.1500 | +1.8 | 1.429 | 1.0000 | 0.42% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | fib_reversal | EUR_USD | 13 | 6 | 50.00% | 18.76% | +0.93 | +0.3043 | +5.6 | 2.556 | 1.0000 | 0.35% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | USD_JPY | 07 | 11 | 63.64% | 35.38% | +0.94 | +0.2521 | +10.3 | 1.656 | 1.0000 | 0.98% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | vol_momentum_scalp | USD_JPY | 18 | 2 | 50.00% | 9.45% | +0.95 | +0.1827 | +1.9 | 1.576 | 1.0000 | 0.33% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | macdh_reversal | EUR_USD | 08 | 4 | 50.00% | 15.00% | +1.00 | +0.1739 | +4.0 | 1.533 | 1.0000 | 0.42% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | vol_surge_detector | USD_JPY | 13 | 4 | 75.00% | 30.06% | +1.05 | +0.4257 | +4.2 | 2.312 | 1.0000 | 0.32% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | USD_JPY | 00 | 12 | 58.33% | 31.95% | +1.07 | +0.2090 | +12.9 | 1.558 | 1.0000 | 1.35% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | gbp_deep_pullback | GBP_USD | 10 | 1 | 100.00% | 20.65% | +1.10 | +0.0000 | +1.1 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | sr_fib_confluence | GBP_USD | 11 | 1 | 100.00% | 20.65% | +1.10 | +0.0000 | +1.1 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | inducement_ob | EUR_GBP | 06 | 1 | 100.00% | 20.65% | +1.10 | +0.0000 | +1.1 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | trend_rebound | EUR_USD | 07 | 1 | 100.00% | 20.65% | +1.10 | +0.0000 | +1.1 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | stoch_trend_pullback | USD_JPY | 18 | 4 | 50.00% | 15.00% | +1.10 | +0.2037 | +4.4 | 1.688 | 1.0000 | 0.64% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | vol_surge_detector | GBP_USD | 13 | 2 | 100.00% | 34.24% | +1.15 | +0.0000 | +2.3 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | ema_trend_scalp | EUR_USD | 12 | 3 | 33.33% | 6.15% | +1.17 | +0.1178 | +3.5 | 1.547 | 1.0000 | 0.64% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | mtf_reversal_confluence | EUR_USD | 02 | 1 | 100.00% | 20.65% | +1.20 | +0.0000 | +1.2 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | mtf_reversal_confluence | USD_JPY | 10 | 1 | 100.00% | 20.65% | +1.20 | +0.0000 | +1.2 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | vol_surge_detector | USD_JPY | 06 | 7 | 57.14% | 25.05% | +1.27 | +0.2779 | +8.9 | 1.947 | 1.0000 | 0.32% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | session_time_bias | GBP_USD | 08 | 1 | 100.00% | 20.65% | +1.30 | +0.0000 | +1.3 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | post_news_vol | GBP_USD | 10 | 1 | 100.00% | 20.65% | +1.30 | +0.0000 | +1.3 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | engulfing_bb | GBP_USD | 10 | 1 | 100.00% | 20.65% | +1.30 | +0.0000 | +1.3 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | ema_cross | GBP_USD | 07 | 1 | 100.00% | 20.65% | +1.30 | +0.0000 | +1.3 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | sr_fib_confluence | GBP_USD | 02 | 1 | 100.00% | 20.65% | +1.30 | +0.0000 | +1.3 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | USD_JPY | 15 | 20 | 60.00% | 38.66% | +1.32 | +0.2454 | +26.5 | 1.692 | 1.0000 | 2.32% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | trendline_sweep | GBP_USD | 01 | 1 | 100.00% | 20.65% | +1.40 | +0.0000 | +1.4 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | fib_reversal | USD_JPY | 03 | 2 | 50.00% | 9.45% | +1.45 | +0.4265 | +2.9 | 6.800 | 1.0000 | 0.05% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | vol_surge_detector | USD_JPY | 07 | 2 | 50.00% | 9.45% | +1.45 | +0.2339 | +2.9 | 1.879 | 1.0000 | 0.33% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | vwap_mean_reversion | EUR_JPY | 15 | 1 | 100.00% | 20.65% | +1.50 | +0.0000 | +1.5 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | stoch_trend_pullback | USD_JPY | 02 | 1 | 100.00% | 20.65% | +1.50 | +0.0000 | +1.5 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | USD_JPY | 09 | 5 | 60.00% | 23.07% | +1.50 | +0.3191 | +7.5 | 2.136 | 1.0000 | 0.36% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_squeeze_breakout | EUR_USD | 15 | 2 | 50.00% | 9.45% | +1.55 | +0.2500 | +3.1 | 2.000 | 1.0000 | 0.31% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | sr_channel_reversal | EUR_USD | 07 | 3 | 33.33% | 6.15% | +1.57 | +0.1911 | +4.7 | 2.343 | 1.0000 | 0.35% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_squeeze_breakout | EUR_USD | 08 | 1 | 100.00% | 20.65% | +1.60 | +0.0000 | +1.6 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | macdh_reversal | USD_JPY | 19 | 4 | 50.00% | 15.00% | +1.60 | +0.2963 | +6.4 | 2.455 | 1.0000 | 0.36% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | fib_reversal | USD_JPY | 13 | 3 | 66.67% | 20.77% | +1.67 | +0.4115 | +5.0 | 2.613 | 1.0000 | 0.31% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | engulfing_bb | USD_JPY | 14 | 2 | 50.00% | 9.45% | +1.70 | +0.2576 | +3.4 | 2.062 | 1.0000 | 0.32% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | engulfing_bb | EUR_USD | 09 | 2 | 50.00% | 9.45% | +1.75 | +0.2692 | +3.5 | 2.167 | 1.0000 | 0.30% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | GBP_USD | 12 | 3 | 66.67% | 20.77% | +1.77 | +0.3099 | +5.3 | 1.869 | 1.0000 | 0.61% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | EUR_USD | 03 | 6 | 33.33% | 9.68% | +1.83 | +0.1724 | +11.0 | 4.143 | 1.0000 | 0.35% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | ema_pullback | USD_JPY | 13 | 2 | 100.00% | 34.24% | +1.85 | +0.0000 | +3.7 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | bb_rsi_reversion | USD_JPY | 08 | 9 | 55.56% | 26.66% | +1.99 | +0.3098 | +17.9 | 2.261 | 1.0000 | 0.82% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | htf_false_breakout | EUR_USD | 15 | 1 | 100.00% | 20.65% | +2.00 | +0.0000 | +2.0 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | macdh_reversal | USD_JPY | 14 | 3 | 66.67% | 20.77% | +2.00 | +0.6061 | +6.0 | 11.000 | 1.0000 | 0.06% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | vwap_mean_reversion | EUR_JPY | 17 | 1 | 100.00% | 20.65% | +2.10 | +0.0000 | +2.1 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | mtf_reversal_confluence | USD_JPY | 15 | 2 | 50.00% | 9.45% | +2.10 | +0.0000 | +4.2 | inf | 1.0000 | 0.00% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | fib_reversal | EUR_USD | 07 | 5 | 60.00% | 23.07% | +2.14 | +0.3326 | +10.7 | 2.244 | 1.0000 | 0.55% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| KEEP | stoch_trend_pullback | USD_JPY | 06 | 3 | 66.67% | 20.77% | +2.17 | +0.4467 | +6.5 | 3.031 | 1.0000 | 0.32% | EV>0 or Wilson_lo>0.50 or raw Kelly>0  |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | 67 rows omitted |

## PR template (司令塔承認後の別PR)

- branch: `feat/r2-cell-demotion-2026-05-03`
- scope: R2 cell-level OANDA routing override only; no strategy-wide demotion.
- proposed STOP_OANDA: 上表 `STOP_OANDA` cell を `entry_type + instrument + UTC hour_bucket` 条件で lot=0。
- proposed LOT_HALF: 上表 `LOT_HALF` cell を現在 lot x 0.5。
- shadow logging: 継続。Live/OANDA転送のみ停止または半減。
- pre-merge evidence: 本レポート、前段 Gate Progression Audit、司令塔承認コメント。

## Risks / blockers

- max_cuts=30 適用後も raw Kelly は負。R2 cell cut だけでは Gate 0 復帰不足。
- 一部 STOP_OANDA は counterfactual 復帰用の拡張候補で、LOCK STOP閾値を全て満たすわけではない。司令塔レビュー必須。
- hour_bucket は UTC hour。実装PRでは注文生成時の timestamp 基準と同じ UTC に固定する必要がある。
- LOT_HALF counterfactual は該当 cell の実測 pnl_pips を 0.5 倍して近似。約定品質やスリッページ非線形性は未反映。
