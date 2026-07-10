# WS3 MFE 分布スキャン (機械集計、rule:R3)

- 生成: 2026-07-10T07:54:15.994287+00:00 / entries=1390 / 365d baseline、診断窓除外、horizon 表は 24 bars (6h)

| cell | N | MFE p50 | p75 | p90 | P(≥15p) | P(≥20p) | MAE p50 |
|---|---|---|---|---|---|---|---|
| dt_sr_channel_reversal__GBP_JPY | 163 | 46.0 | 75.75 | 139.98 | 0.834 | 0.804 | 37.4 |
| sr_fib_confluence__GBP_JPY | 186 | 42.75 | 76.42 | 127.95 | 0.823 | 0.763 | 37.45 |
| dual_sr_bounce__GBP_JPY | 134 | 42.7 | 71.6 | 109.89 | 0.828 | 0.761 | 44.75 |
| sr_break_retest__GBP_JPY | 146 | 39.03 | 88.35 | 125.35 | 0.801 | 0.76 | 37.01 |
| wick_imbalance_reversion__GBP_JPY | 108 | 41.65 | 68.08 | 116.56 | 0.806 | 0.75 | 36.35 |
| sr_anti_hunt_bounce__GBP_JPY | 38 | 29.25 | 71.25 | 123.02 | 0.789 | 0.737 | 44.21 |
| dt_fib_reversal__GBP_JPY | 53 | 49.7 | 87.6 | 145.42 | 0.811 | 0.736 | 27.3 |
| htf_false_breakout__GBP_JPY | 30 | 39.6 | 75.27 | 142.47 | 0.8 | 0.733 | 40.3 |
| ema_cross__GBP_JPY | 34 | 35.8 | 93.92 | 144.08 | 0.794 | 0.706 | 41.2 |
| rsk_gbpjpy_reversion__GBP_JPY | 61 | 33.4 | 65.6 | 87.1 | 0.77 | 0.705 | 60.9 |
| intraday_seasonality__GBP_JPY | 91 | 41.1 | 76.5 | 114.5 | 0.758 | 0.703 | 45.5 |
| vsg_jpy_reversal__GBP_JPY | 308 | 37.7 | 74.97 | 121.43 | 0.773 | 0.688 | 47.15 |
| ema200_trend_reversal__GBP_JPY | 37 | 40.9 | 107.6 | 200.04 | 0.73 | 0.676 | 49.6 |

N<10 セルと他 horizon は JSON 参照。

## 方向分割セル (entry_type × pair × sig, h24)

| cell | N | MFE p50 | p75 | p90 | P(≥15p) | P(≥20p) | MAE p50 |
|---|---|---|---|---|---|---|---|
| sr_anti_hunt_bounce__GBP_JPY__BUY | 16 | 46.7 | 73.08 | 119.8 | 0.875 | 0.875 | 35.1 |
| dual_sr_bounce__GBP_JPY__SELL | 55 | 44.0 | 66.4 | 99.1 | 0.909 | 0.873 | 39.3 |
| dt_sr_channel_reversal__GBP_JPY__BUY | 75 | 37.0 | 68.85 | 148.3 | 0.867 | 0.813 | 39.0 |
| rsk_gbpjpy_reversion__GBP_JPY__SELL | 21 | 41.4 | 82.4 | 178.6 | 0.857 | 0.81 | 52.91 |
| dt_sr_channel_reversal__GBP_JPY__SELL | 88 | 52.55 | 79.75 | 137.38 | 0.807 | 0.795 | 33.6 |
| htf_false_breakout__GBP_JPY__BUY | 19 | 39.0 | 76.59 | 147.34 | 0.842 | 0.789 | 36.3 |
| sr_fib_confluence__GBP_JPY__BUY | 83 | 38.9 | 74.1 | 116.06 | 0.819 | 0.771 | 34.1 |
| ema200_trend_reversal__GBP_JPY__SELL | 21 | 85.8 | 198.66 | 221.7 | 0.81 | 0.762 | 33.9 |
| sr_break_retest__GBP_JPY__BUY | 84 | 39.03 | 81.9 | 107.66 | 0.81 | 0.762 | 34.75 |
| sr_break_retest__GBP_JPY__SELL | 62 | 41.19 | 95.67 | 174.34 | 0.79 | 0.758 | 41.5 |
| sr_fib_confluence__GBP_JPY__SELL | 103 | 43.5 | 81.65 | 146.74 | 0.825 | 0.757 | 41.7 |
| ema_cross__GBP_JPY__SELL | 20 | 56.3 | 94.75 | 118.82 | 0.85 | 0.75 | 44.9 |
| wick_imbalance_reversion__GBP_JPY__BUY | 101 | 41.7 | 77.3 | 116.7 | 0.802 | 0.743 | 34.1 |
| dt_fib_reversal__GBP_JPY__BUY | 23 | 40.0 | 96.69 | 125.29 | 0.826 | 0.739 | 25.7 |
| dt_fib_reversal__GBP_JPY__SELL | 30 | 59.3 | 81.02 | 179.48 | 0.8 | 0.733 | 46.3 |
| intraday_seasonality__GBP_JPY__SELL | 45 | 45.8 | 76.2 | 108.8 | 0.778 | 0.711 | 46.0 |
| intraday_seasonality__GBP_JPY__BUY | 46 | 39.8 | 75.53 | 122.0 | 0.739 | 0.696 | 44.95 |
| vsg_jpy_reversal__GBP_JPY__BUY | 191 | 35.56 | 66.52 | 106.2 | 0.764 | 0.696 | 42.7 |
| dual_sr_bounce__GBP_JPY__BUY | 79 | 41.9 | 73.5 | 128.3 | 0.772 | 0.684 | 48.7 |
| vsg_jpy_reversal__GBP_JPY__SELL | 117 | 44.4 | 88.8 | 166.94 | 0.786 | 0.675 | 50.3 |
| rsk_gbpjpy_reversion__GBP_JPY__BUY | 40 | 27.4 | 60.75 | 82.94 | 0.725 | 0.65 | 62.5 |
| ema_cross__GBP_JPY__BUY | 14 | 29.3 | 87.08 | 138.41 | 0.714 | 0.643 | 37.4 |
| htf_false_breakout__GBP_JPY__SELL | 11 | 40.2 | 61.05 | 110.2 | 0.727 | 0.636 | 79.6 |
| sr_anti_hunt_bounce__GBP_JPY__SELL | 22 | 23.5 | 59.05 | 110.31 | 0.727 | 0.636 | 68.65 |
| ema200_trend_reversal__GBP_JPY__BUY | 16 | 21.95 | 44.17 | 76.1 | 0.625 | 0.562 | 75.45 |
