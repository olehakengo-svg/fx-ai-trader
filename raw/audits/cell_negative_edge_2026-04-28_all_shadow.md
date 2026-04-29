# Cell Negative Edge Audit (2026-04-28)

Scope: **shadow** | Window: **all** | Total trades scanned: **357**

- **Definitely-losing** (N≥10 AND Wilson upper < 50% AND ev_net<0): **52**
- **Likely-losing** (N≥10 AND Wilson upper < 55% AND ev_net<-1.0): **10**
- **Clustering = artifactual** (subset, prioritize): **3**

Bonferroni intentionally not applied — Wilson interval is itself conservative. Shadow continuation harmless; Live promotion NG.
Hour-aware friction (Phase 9 P5) used when cell key contains ``hour_bin``; falls back to session-level otherwise.

## Definitely-losing cells

| axis | cell_key | N | wins | WR | Wilson [lo, hi] | EV | EV_net | PF | clustering |
|---|---|---|---|---|---|---|---|---|---|
| by-strategy | sr_channel_reversal | 23 | 1 | 4.3% | [0.8%, 21.0%] | -3.59 | n/a | 0.04 | · weak_clustering |
| by-strategy-direction | sr_channel_reversal/BUY | 14 | 0 | 0.0% | [0.0%, 21.5%] | -3.43 | n/a | 0.00 | · weak_clustering |
| by-strategy-pair | sr_channel_reversal/USD_JPY | 11 | 0 | 0.0% | [0.0%, 25.9%] | -3.04 | -5.40 | 0.00 | · weak_clustering |
| by-hour-bin | h06-12 | 143 | 31 | 21.7% | [15.7%, 29.1%] | -4.56 | n/a | 0.39 | clean |
| by-pair-hour-bin | USD_JPY/h06-12 | 55 | 10 | 18.2% | [10.2%, 30.3%] | -5.64 | -7.76 | 0.41 | clean |
| by-pair | EUR_USD | 75 | 15 | 20.0% | [12.5%, 30.4%] | -2.48 | -4.68 | 0.27 | · weak_clustering |
| by-session | London | 127 | 29 | 22.8% | [16.4%, 30.9%] | -4.19 | n/a | 0.43 | clean |
| by-strategy-direction-hour-bin | ema_trend_scalp/SELL/h12-18 | 14 | 1 | 7.1% | [1.3%, 31.5%] | -2.66 | n/a | 0.13 | · weak_clustering |
| by-direction-hour-bin | SELL/h12-18 | 36 | 6 | 16.7% | [7.9%, 31.9%] | -3.66 | n/a | 0.27 | · weak_clustering |
| by-direction-hour-bin | BUY/h06-12 | 86 | 19 | 22.1% | [14.6%, 31.9%] | -6.97 | n/a | 0.25 | clean |
| by-direction-hour-bin | SELL/h06-12 | 57 | 12 | 21.1% | [12.5%, 33.3%] | -0.93 | n/a | 0.80 | clean |
| by-pair-direction | EUR_USD/BUY | 42 | 8 | 19.1% | [10.0%, 33.3%] | -2.89 | -5.09 | 0.21 | · weak_clustering |
| by-strategy | bb_squeeze_breakout | 13 | 1 | 7.7% | [1.4%, 33.3%] | -3.00 | n/a | 0.06 | clean |
| by-strategy-hour-bin | ema_trend_scalp/h12-18 | 30 | 5 | 16.7% | [7.3%, 33.6%] | -2.11 | n/a | 0.31 | · weak_clustering |
| by-strategy-session | ema_trend_scalp/Overlap | 29 | 5 | 17.2% | [7.6%, 34.5%] | -1.99 | n/a | 0.33 | · weak_clustering |
| by-strategy | ema_trend_scalp | 72 | 17 | 23.6% | [15.3%, 34.6%] | -1.43 | n/a | 0.52 | · weak_clustering |
| by-pair-hour-bin | EUR_USD/h12-18 | 36 | 7 | 19.4% | [9.8%, 35.0%] | -1.95 | -3.71 | 0.34 | · weak_clustering |
| by-strategy-direction | ema_trend_scalp/SELL | 36 | 7 | 19.4% | [9.8%, 35.0%] | -1.91 | n/a | 0.38 | · weak_clustering |
| by-pair-direction | USD_JPY/BUY | 93 | 24 | 25.8% | [18.0%, 35.5%] | -4.89 | -7.24 | 0.38 | clean |
| by-pair-session | EUR_USD/London | 39 | 8 | 20.5% | [10.8%, 35.5%] | -2.97 | -4.97 | 0.21 | clean |
| by-pair-hour-bin | EUR_USD/h06-12 | 39 | 8 | 20.5% | [10.8%, 35.5%] | -2.97 | -4.95 | 0.21 | clean |
| by-session | Overlap | 81 | 21 | 25.9% | [17.6%, 36.4%] | -2.56 | n/a | 0.44 | clean |
| by-direction | BUY | 222 | 67 | 30.2% | [24.5%, 36.5%] | -2.68 | n/a | 0.58 | clean |
| by-pair-session | USD_JPY/London | 41 | 9 | 21.9% | [12.0%, 36.7%] | -4.71 | -6.84 | 0.52 | clean |
| by-pair-session | EUR_USD/Overlap | 34 | 7 | 20.6% | [10.3%, 36.8%] | -1.78 | -3.98 | 0.38 | · weak_clustering |
| by-pair-direction | GBP_USD/SELL | 19 | 3 | 15.8% | [5.5%, 37.6%] | -4.00 | -8.98 | 0.25 | clean |
| by-pair-direction | EUR_USD/SELL | 33 | 7 | 21.2% | [10.7%, 37.8%] | -1.96 | -4.16 | 0.35 | clean |
| by-hour-bin | h12-18 | 109 | 32 | 29.4% | [21.6%, 38.5%] | -1.11 | n/a | 0.75 | clean |
| by-strategy-pair | ema_trend_scalp/EUR_USD | 28 | 6 | 21.4% | [10.2%, 39.5%] | -1.34 | -3.54 | 0.46 | · weak_clustering |
| by-strategy-hour-bin | sr_channel_reversal/h06-12 | 10 | 1 | 10.0% | [1.8%, 40.4%] | -3.29 | n/a | 0.10 | clean |
| by-strategy-session | ema_trend_scalp/London | 30 | 7 | 23.3% | [11.8%, 40.9%] | -1.23 | n/a | 0.59 | · weak_clustering |
| by-strategy-hour-bin | ema_trend_scalp/h06-12 | 33 | 8 | 24.2% | [12.8%, 41.0%] | -1.08 | n/a | 0.63 | · weak_clustering |
| by-pair-hour-bin | USD_JPY/h12-18 | 45 | 12 | 26.7% | [16.0%, 41.0%] | -2.51 | -4.39 | 0.56 | clean |
| by-pair | USD_JPY | 172 | 59 | 34.3% | [27.6%, 41.7%] | -1.41 | -3.77 | 0.77 | clean |
| by-pair-session | USD_JPY/Overlap | 35 | 9 | 25.7% | [14.2%, 42.1%] | -4.07 | -6.42 | 0.36 | clean |
| by-strategy-pair-hour-bin | ema_trend_scalp/EUR_USD/h12-18 | 16 | 3 | 18.8% | [6.6%, 43.0%] | -1.73 | -3.48 | 0.37 | · weak_clustering |
| by-strategy-direction-hour-bin | ema_trend_scalp/SELL/h06-12 | 19 | 4 | 21.1% | [8.5%, 43.3%] | -2.14 | n/a | 0.36 | ⚠️ artifactual |
| by-strategy-pair | ema_trend_scalp/USD_JPY | 22 | 5 | 22.7% | [10.1%, 43.4%] | -1.56 | -3.91 | 0.43 | · weak_clustering |
| by-pair-session | GBP_USD/London | 42 | 12 | 28.6% | [17.2%, 43.6%] | -3.44 | -7.97 | 0.53 | clean |
| by-strategy-direction | ema_trend_scalp/BUY | 36 | 10 | 27.8% | [15.8%, 44.0%] | -0.96 | n/a | 0.67 | clean |
| by-pair-hour-bin | GBP_USD/h06-12 | 44 | 13 | 29.5% | [18.2%, 44.2%] | -3.33 | -7.81 | 0.53 | clean |
| by-strategy-pair-direction | ema_trend_scalp/EUR_USD/BUY | 12 | 2 | 16.7% | [4.7%, 44.8%] | -1.79 | -3.99 | 0.34 | · weak_clustering |
| by-strategy | bb_rsi_reversion | 12 | 2 | 16.7% | [4.7%, 44.8%] | -3.05 | n/a | 0.25 | · weak_clustering |
| by-strategy-direction-hour-bin | sr_fib_confluence/BUY/h06-12 | 15 | 3 | 20.0% | [7.0%, 45.2%] | -13.31 | n/a | 0.19 | clean |
| by-direction-hour-bin | BUY/h00-06 | 49 | 16 | 32.6% | [21.2%, 46.6%] | -0.78 | n/a | 0.83 | clean |
| by-strategy-pair | sr_break_retest/USD_JPY | 11 | 2 | 18.2% | [5.1%, 47.7%] | -30.07 | -32.43 | 0.06 | ⚠️ artifactual |
| by-strategy-pair | ema_trend_scalp/GBP_USD | 22 | 6 | 27.3% | [13.2%, 48.1%] | -1.42 | -6.41 | 0.62 | · weak_clustering |
| by-strategy-direction | sr_fib_confluence/BUY | 24 | 7 | 29.2% | [14.9%, 49.2%] | -6.66 | n/a | 0.48 | clean |
| by-strategy-session | sr_fib_confluence/London | 16 | 4 | 25.0% | [10.2%, 49.5%] | -12.19 | n/a | 0.21 | clean |
| by-strategy-hour-bin | sr_fib_confluence/h06-12 | 16 | 4 | 25.0% | [10.2%, 49.5%] | -12.19 | n/a | 0.21 | clean |
| by-strategy-pair-direction | ema_trend_scalp/EUR_USD/SELL | 16 | 4 | 25.0% | [10.2%, 49.5%] | -0.99 | -3.19 | 0.57 | · weak_clustering |
| by-strategy-direction-hour-bin | ema_trend_scalp/BUY/h12-18 | 16 | 4 | 25.0% | [10.2%, 49.5%] | -1.62 | n/a | 0.47 | · weak_clustering |

## Likely-losing cells

| axis | cell_key | N | wins | WR | Wilson [lo, hi] | EV | EV_net | PF | clustering |
|---|---|---|---|---|---|---|---|---|---|
| by-pair | GBP_USD | 95 | 38 | 40.0% | [30.7%, 50.0%] | +0.38 | -4.60 | 1.07 | clean |
| by-strategy-pair-direction | ema_trend_scalp/USD_JPY/SELL | 13 | 3 | 23.1% | [8.2%, 50.3%] | -1.32 | -3.68 | 0.54 | weak_clustering |
| by-strategy | dt_sr_channel_reversal | 13 | 3 | 23.1% | [8.2%, 50.3%] | -2.62 | n/a | 0.30 | clean |
| by-strategy-pair-direction | sr_break_retest/USD_JPY/BUY | 10 | 2 | 20.0% | [5.7%, 51.0%] | -30.60 | -32.95 | 0.06 | artifactual |
| by-strategy-hour-bin | sr_break_retest/h06-12 | 10 | 2 | 20.0% | [5.7%, 51.0%] | -27.98 | n/a | 0.10 | weak_clustering |
| by-pair | EUR_JPY | 10 | 2 | 20.0% | [5.7%, 51.0%] | -3.48 | -6.23 | 0.56 | clean |
| by-strategy-direction | dt_sr_channel_reversal/BUY | 10 | 2 | 20.0% | [5.7%, 51.0%] | -2.54 | n/a | 0.19 | clean |
| by-strategy | sr_fib_confluence | 25 | 8 | 32.0% | [17.2%, 51.6%] | -6.21 | n/a | 0.50 | clean |
| by-strategy-pair-hour-bin | ema_trend_scalp/EUR_USD/h06-12 | 12 | 3 | 25.0% | [8.9%, 53.2%] | -0.82 | -2.80 | 0.62 | weak_clustering |
| by-strategy-pair-hour-bin | ema_trend_scalp/GBP_USD/h06-12 | 14 | 4 | 28.6% | [11.7%, 54.6%] | -0.86 | -5.34 | 0.75 | weak_clustering |
