# S6 Wave 2a Diagnosis — Spread-adjusted / 7-axis Cell Deepdive

**Date**: 2026-05-03  
**Scope**: USD_JPY M5 `isolated` only; no LIVE / Shadow exposure  
**Input**: existing `chart_pattern_bt_trades`; no new BT run  

## Frozen Table Check

| table | before | after | status |
|---|---:|---:|---|
| signals | 22094 | 22094 | UNCHANGED |
| trades | 42483 | 42483 | UNCHANGED |
| verdicts | 26 | 26 | UNCHANGED |

## Hypothesis Verdicts

| hypothesis | verdict | evidence |
|---|---|---|
| H1 spread profile rescues cell | REJECT | spread-adjusted flips=0; flat-1.5p REJECT remains valid |
| H2 measured-move TP too far | REJECT | best R:R EV max=0.57 pips; optimal multipliers are not below 1.0 |
| H3 hour bucket edge exists | ACCEPT | best hour-bucket EV max=3.76 pips |
| H4 ATR 12-pattern family should be parked if no axis rescues edge | ACCEPT | PROMOTE/SHADOW rows=0 |
| H5 triple_bottom WF1 macro sensitivity | INCONCLUSIVE | local VIX/DXY source not present; WF1 aggregate only |

## Empirical Spread Profile

| hour_utc | N | avg_rt_pips | median_rt_pips | p95_rt_pips |
|---:|---:|---:|---:|---:|
| 0 | 7 | 1.49 | 1.60 | 1.60 |
| 1 | 13 | 1.60 | 1.60 | 1.60 |
| 2 | 14 | 1.60 | 1.60 | 1.60 |
| 3 | 5 | 1.60 | 1.60 | 1.60 |
| 4 | 4 | 1.40 | 1.60 | 1.60 |
| 5 | 12 | 1.60 | 1.60 | 1.60 |
| 6 | 12 | 1.53 | 1.60 | 1.60 |
| 7 | 6 | 1.60 | 1.60 | 1.60 |
| 8 | 4 | 1.60 | 1.60 | 1.60 |
| 9 | 14 | 1.54 | 1.60 | 1.60 |
| 10 | 4 | 1.60 | 1.60 | 1.60 |
| 11 | 8 | 1.60 | 1.60 | 1.60 |
| 12 | 8 | 1.50 | 1.60 | 1.60 |
| 13 | 8 | 1.60 | 1.60 | 1.60 |
| 14 | 11 | 1.45 | 1.60 | 1.60 |
| 15 | 10 | 1.60 | 1.60 | 1.60 |
| 16 | 6 | 1.60 | 1.60 | 1.60 |
| 17 | 6 | 2.50 | 1.60 | 5.65 |
| 18 | 2 | 1.60 | 1.60 | 1.60 |
| 19 | 3 | 1.60 | 1.60 | 1.60 |
| 20 | 3 | 1.77 | 1.80 | 1.89 |
| 21 | 0 | 1.90 | 1.60 | 2.16 |
| 22 | 0 | 1.90 | 1.60 | 2.16 |
| 23 | 0 | 1.90 | 1.60 | 2.16 |

### Axis 1 Spread-adjusted EV

| pattern | sub_key | N | WR | EV | PF | Wilson_lo | BEV | Bonf_p | Kelly | verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| ascending_triangle | all | 3772 | 0.459 | -1.27 | 0.80 | 0.443 | 0.515 | 1.00e+00 | -0.114 | REJECT |
| rising_wedge | all | 1746 | 0.444 | -1.60 | 0.77 | 0.421 | 0.510 | 1.00e+00 | -0.135 | REJECT |
| bull_flag | all | 376 | 0.457 | -1.10 | 0.80 | 0.408 | 0.514 | 9.87e-01 | -0.115 | REJECT |
| descending_triangle | all | 2839 | 0.448 | -1.71 | 0.75 | 0.430 | 0.518 | 1.00e+00 | -0.146 | REJECT |
| falling_wedge | all | 1251 | 0.438 | -2.27 | 0.72 | 0.411 | 0.520 | 1.00e+00 | -0.170 | REJECT |
| bear_flag | all | 261 | 0.429 | -2.15 | 0.68 | 0.371 | 0.526 | 9.99e-01 | -0.205 | REJECT |
| double_bottom | all | 4666 | 0.512 | -1.57 | 0.73 | 0.497 | 0.590 | 1.00e+00 | -0.192 | REJECT |
| triple_bottom | all | 155 | 0.503 | -0.10 | 0.98 | 0.425 | 0.509 | 5.90e-01 | -0.012 | REJECT |
| inverse_head_shoulders | all | 999 | 0.461 | -1.31 | 0.79 | 0.431 | 0.521 | 1.00e+00 | -0.124 | REJECT |
| double_top | all | 4869 | 0.493 | -1.99 | 0.68 | 0.479 | 0.589 | 1.00e+00 | -0.232 | REJECT |
| triple_top | all | 142 | 0.500 | -1.23 | 0.76 | 0.419 | 0.569 | 9.58e-01 | -0.159 | REJECT |
| head_shoulders | all | 1017 | 0.478 | -1.44 | 0.78 | 0.447 | 0.540 | 1.00e+00 | -0.134 | REJECT |

### Axis 2 Exit Reason Distribution

| pattern | sub_key | N | WR | EV | PF | Wilson_lo | BEV | Bonf_p | Kelly | verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| ascending_triangle | distribution | 3772 | 0.466 | -1.11 | 0.82 | 0.450 | 0.515 | 1.00e+00 | -0.100 | REJECT |
| rising_wedge | distribution | 1746 | 0.454 | -1.44 | 0.79 | 0.430 | 0.513 | 1.00e+00 | -0.123 | REJECT |
| bull_flag | distribution | 376 | 0.465 | -0.94 | 0.82 | 0.416 | 0.514 | 9.72e-01 | -0.099 | REJECT |
| descending_triangle | distribution | 2839 | 0.453 | -1.56 | 0.77 | 0.435 | 0.517 | 1.00e+00 | -0.132 | REJECT |
| falling_wedge | distribution | 1251 | 0.442 | -2.13 | 0.74 | 0.415 | 0.519 | 1.00e+00 | -0.159 | REJECT |
| bear_flag | distribution | 261 | 0.429 | -1.96 | 0.70 | 0.371 | 0.518 | 9.98e-01 | -0.184 | REJECT |
| double_bottom | distribution | 4666 | 0.516 | -1.43 | 0.75 | 0.502 | 0.588 | 1.00e+00 | -0.174 | REJECT |
| triple_bottom | distribution | 155 | 0.510 | 0.05 | 1.01 | 0.432 | 0.507 | 5.02e-01 | 0.006 | REJECT |
| inverse_head_shoulders | distribution | 999 | 0.466 | -1.15 | 0.81 | 0.436 | 0.519 | 1.00e+00 | -0.109 | REJECT |
| double_top | distribution | 4869 | 0.496 | -1.84 | 0.70 | 0.482 | 0.584 | 1.00e+00 | -0.212 | REJECT |
| triple_top | distribution | 142 | 0.507 | -1.07 | 0.79 | 0.426 | 0.567 | 9.35e-01 | -0.138 | REJECT |
| head_shoulders | distribution | 1017 | 0.481 | -1.28 | 0.80 | 0.450 | 0.536 | 1.00e+00 | -0.119 | REJECT |

### Axis 3 MAFE/MFE Distribution

| pattern | summary |
|---|---|
| ascending_triangle | MAFE p25/med/p75/p95=3.50/7.60/14.70/33.49; MFE p25/med/p75/p95=3.30/8.00/14.50/31.54; avgTP=21.54; avgSL=26.40 |
| rising_wedge | MAFE p25/med/p75/p95=4.00/8.50/16.40/36.30; MFE p25/med/p75/p95=3.70/8.40/15.50/33.10; avgTP=25.58; avgSL=35.05 |
| bull_flag | MAFE p25/med/p75/p95=2.80/5.95/11.02/22.37; MFE p25/med/p75/p95=2.55/6.60/13.00/25.95; avgTP=14.63; avgSL=12.76 |
| descending_triangle | MAFE p25/med/p75/p95=3.40/8.00/15.15/33.21; MFE p25/med/p75/p95=3.80/8.30/15.40/32.61; avgTP=21.15; avgSL=26.09 |
| falling_wedge | MAFE p25/med/p75/p95=4.00/9.30/17.35/38.80; MFE p25/med/p75/p95=3.90/9.00/17.70/38.35; avgTP=25.86; avgSL=36.24 |
| bear_flag | MAFE p25/med/p75/p95=2.70/6.10/12.20/27.10; MFE p25/med/p75/p95=2.40/6.50/15.40/27.40; avgTP=18.01; avgSL=13.77 |
| double_bottom | MAFE p25/med/p75/p95=3.20/7.10/13.40/28.80; MFE p25/med/p75/p95=3.30/7.00/12.20/23.90; avgTP=12.18; avgSL=17.88 |
| triple_bottom | MAFE p25/med/p75/p95=4.20/6.50/11.60/24.62; MFE p25/med/p75/p95=3.20/7.20/13.15/20.63; avgTP=10.47; avgSL=16.62 |
| inverse_head_shoulders | MAFE p25/med/p75/p95=3.55/7.90/14.70/31.21; MFE p25/med/p75/p95=3.60/7.60/13.60/29.64; avgTP=16.64; avgSL=22.27 |
| double_top | MAFE p25/med/p75/p95=3.20/7.30/13.70/28.76; MFE p25/med/p75/p95=3.30/7.10/12.40/24.80; avgTP=11.99; avgSL=17.76 |
| triple_top | MAFE p25/med/p75/p95=3.33/7.20/10.57/20.34; MFE p25/med/p75/p95=3.23/5.80/11.95/24.18; avgTP=10.30; avgSL=15.60 |
| head_shoulders | MAFE p25/med/p75/p95=3.60/7.80/14.60/29.72; MFE p25/med/p75/p95=3.40/8.00/14.50/28.92; avgTP=15.64; avgSL=21.61 |

### Axis 4 R:R Optimal by Pattern

| pattern | sub_key | N | WR | EV | PF | Wilson_lo | BEV | Bonf_p | Kelly | verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| ascending_triangle | rr=1.25 | 3772 | 0.466 | -0.88 | 0.86 | 0.450 | 0.504 | 1.00e+00 | -0.077 | REJECT |
| rising_wedge | rr=1.25 | 1746 | 0.454 | -1.22 | 0.82 | 0.430 | 0.503 | 1.00e+00 | -0.100 | REJECT |
| bull_flag | rr=1.25 | 376 | 0.465 | -0.71 | 0.87 | 0.416 | 0.501 | 9.22e-01 | -0.070 | REJECT |
| descending_triangle | rr=1.25 | 2839 | 0.453 | -1.26 | 0.82 | 0.435 | 0.503 | 1.00e+00 | -0.101 | REJECT |
| falling_wedge | rr=1.25 | 1251 | 0.442 | -1.79 | 0.78 | 0.415 | 0.505 | 1.00e+00 | -0.127 | REJECT |
| bear_flag | rr=1.25 | 261 | 0.429 | -1.70 | 0.74 | 0.371 | 0.503 | 9.93e-01 | -0.150 | REJECT |
| double_bottom | rr=1.25 | 4666 | 0.516 | -1.06 | 0.81 | 0.502 | 0.568 | 1.00e+00 | -0.119 | REJECT |
| triple_bottom | rr=1.25 | 155 | 0.510 | 0.57 | 1.13 | 0.432 | 0.479 | 2.43e-01 | 0.060 | REJECT |
| inverse_head_shoulders | rr=1.25 | 999 | 0.466 | -0.84 | 0.86 | 0.436 | 0.503 | 9.91e-01 | -0.074 | REJECT |
| double_top | rr=1.25 | 4869 | 0.497 | -1.39 | 0.77 | 0.483 | 0.560 | 1.00e+00 | -0.145 | REJECT |
| triple_top | rr=1.25 | 142 | 0.507 | -0.58 | 0.89 | 0.426 | 0.537 | 7.91e-01 | -0.066 | REJECT |
| head_shoulders | rr=1.25 | 1017 | 0.481 | -0.94 | 0.85 | 0.450 | 0.520 | 9.94e-01 | -0.082 | REJECT |

### Axis 5 Best Hour Bucket by Pattern

| pattern | sub_key | N | WR | EV | PF | Wilson_lo | BEV | Bonf_p | Kelly | verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| ascending_triangle | London | 600 | 0.483 | -0.17 | 0.97 | 0.444 | 0.491 | 6.56e-01 | -0.015 | REJECT |
| rising_wedge | London | 260 | 0.492 | -0.15 | 0.97 | 0.432 | 0.499 | 6.09e-01 | -0.013 | REJECT |
| bull_flag | London | 71 | 0.535 | 0.58 | 1.11 | 0.420 | 0.509 | 3.73e-01 | 0.054 | INSUFFICIENT |
| descending_triangle | London_NY_overlap | 480 | 0.465 | -1.23 | 0.85 | 0.420 | 0.504 | 9.62e-01 | -0.079 | REJECT |
| falling_wedge | London_NY_overlap | 249 | 0.494 | 0.17 | 1.02 | 0.432 | 0.489 | 4.62e-01 | 0.010 | REJECT |
| bear_flag | London | 37 | 0.514 | 0.26 | 1.04 | 0.359 | 0.505 | 5.22e-01 | 0.018 | INSUFFICIENT |
| double_bottom | Asia | 1557 | 0.538 | -1.11 | 0.79 | 0.513 | 0.594 | 1.00e+00 | -0.139 | REJECT |
| triple_bottom | London_NY_overlap | 39 | 0.744 | 3.76 | 2.33 | 0.589 | 0.554 | 1.18e-02 | 0.425 | INSUFFICIENT |
| inverse_head_shoulders | London_NY_overlap | 203 | 0.586 | 1.82 | 1.30 | 0.517 | 0.522 | 3.90e-02 | 0.134 | REJECT |
| double_top | Asia | 1618 | 0.528 | -1.19 | 0.79 | 0.503 | 0.587 | 1.00e+00 | -0.142 | REJECT |
| triple_top | London_NY_overlap | 19 | 0.684 | 3.28 | 2.14 | 0.460 | 0.503 | 8.83e-02 | 0.364 | INSUFFICIENT |
| head_shoulders | London_NY_overlap | 194 | 0.521 | -0.02 | 1.00 | 0.451 | 0.521 | 5.38e-01 | -0.002 | REJECT |

### Axis 6 Early Hit Distribution

| pattern | sub_key | N | WR | EV | PF | Wilson_lo | BEV | Bonf_p | Kelly | verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| ascending_triangle | hold_bars | 3772 | 0.466 | -1.11 | 0.82 | 0.450 | 0.515 | 1.00e+00 | -0.100 | REJECT |
| rising_wedge | hold_bars | 1746 | 0.454 | -1.44 | 0.79 | 0.430 | 0.513 | 1.00e+00 | -0.123 | REJECT |
| bull_flag | hold_bars | 376 | 0.465 | -0.94 | 0.82 | 0.416 | 0.514 | 9.72e-01 | -0.099 | REJECT |
| descending_triangle | hold_bars | 2839 | 0.453 | -1.56 | 0.77 | 0.435 | 0.517 | 1.00e+00 | -0.132 | REJECT |
| falling_wedge | hold_bars | 1251 | 0.442 | -2.13 | 0.74 | 0.415 | 0.519 | 1.00e+00 | -0.159 | REJECT |
| bear_flag | hold_bars | 261 | 0.429 | -1.96 | 0.70 | 0.371 | 0.518 | 9.98e-01 | -0.184 | REJECT |
| double_bottom | hold_bars | 4666 | 0.516 | -1.43 | 0.75 | 0.502 | 0.588 | 1.00e+00 | -0.174 | REJECT |
| triple_bottom | hold_bars | 155 | 0.510 | 0.05 | 1.01 | 0.432 | 0.507 | 5.02e-01 | 0.006 | REJECT |
| inverse_head_shoulders | hold_bars | 999 | 0.466 | -1.15 | 0.81 | 0.436 | 0.519 | 1.00e+00 | -0.109 | REJECT |
| double_top | hold_bars | 4869 | 0.496 | -1.84 | 0.70 | 0.482 | 0.584 | 1.00e+00 | -0.212 | REJECT |
| triple_top | hold_bars | 142 | 0.507 | -1.07 | 0.79 | 0.426 | 0.567 | 9.35e-01 | -0.138 | REJECT |
| head_shoulders | hold_bars | 1017 | 0.481 | -1.28 | 0.80 | 0.450 | 0.536 | 1.00e+00 | -0.119 | REJECT |

### Axis 7 Best Pivot Quality Quartile by Pattern

| pattern | sub_key | N | WR | EV | PF | Wilson_lo | BEV | Bonf_p | Kelly | verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| ascending_triangle | q2 | 943 | 0.478 | -0.78 | 0.86 | 0.447 | 0.515 | 9.89e-01 | -0.076 | REJECT |
| rising_wedge | q1 | 437 | 0.501 | -0.82 | 0.86 | 0.454 | 0.539 | 9.47e-01 | -0.081 | REJECT |
| bull_flag | q3 | 94 | 0.553 | 1.46 | 1.29 | 0.453 | 0.489 | 1.28e-01 | 0.125 | INSUFFICIENT |
| descending_triangle | q2 | 710 | 0.469 | -0.80 | 0.88 | 0.433 | 0.502 | 9.63e-01 | -0.066 | REJECT |
| falling_wedge | q1 | 313 | 0.530 | -0.50 | 0.92 | 0.475 | 0.552 | 7.95e-01 | -0.048 | REJECT |
| bear_flag | q2 | 65 | 0.492 | 0.38 | 1.08 | 0.375 | 0.473 | 4.26e-01 | 0.036 | INSUFFICIENT |
| double_bottom | q1 | 1167 | 0.554 | -1.02 | 0.78 | 0.526 | 0.614 | 1.00e+00 | -0.155 | REJECT |
| triple_bottom | q1 | 39 | 0.615 | 2.23 | 1.91 | 0.459 | 0.455 | 3.26e-02 | 0.294 | INSUFFICIENT |
| inverse_head_shoulders | q4 | 250 | 0.432 | -0.81 | 0.88 | 0.372 | 0.465 | 8.64e-01 | -0.061 | REJECT |
| double_top | q4 | 1217 | 0.467 | -1.54 | 0.78 | 0.439 | 0.530 | 1.00e+00 | -0.135 | REJECT |
| triple_top | q3 | 35 | 0.514 | 1.27 | 1.31 | 0.356 | 0.447 | 2.63e-01 | 0.122 | INSUFFICIENT |
| head_shoulders | q3 | 254 | 0.484 | -0.70 | 0.90 | 0.423 | 0.511 | 8.23e-01 | -0.055 | REJECT |

### Axis 8 Best D1 EMA200 Regime by Pattern

| pattern | sub_key | N | WR | EV | PF | Wilson_lo | BEV | Bonf_p | Kelly | verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| ascending_triangle | BULL | 2299 | 0.478 | -0.65 | 0.89 | 0.458 | 0.507 | 9.97e-01 | -0.059 | REJECT |
| rising_wedge | BULL | 1066 | 0.459 | -1.21 | 0.82 | 0.429 | 0.509 | 1.00e+00 | -0.102 | REJECT |
| bull_flag | BULL | 228 | 0.491 | -0.30 | 0.94 | 0.427 | 0.507 | 7.07e-01 | -0.032 | REJECT |
| descending_triangle | BEAR | 1141 | 0.474 | -1.10 | 0.84 | 0.445 | 0.517 | 9.98e-01 | -0.088 | REJECT |
| falling_wedge | BEAR | 538 | 0.487 | -1.05 | 0.87 | 0.445 | 0.523 | 9.56e-01 | -0.075 | REJECT |
| bear_flag | BEAR | 122 | 0.451 | -1.38 | 0.80 | 0.365 | 0.507 | 9.10e-01 | -0.115 | REJECT |
| double_bottom | BULL | 2762 | 0.529 | -1.22 | 0.78 | 0.510 | 0.590 | 1.00e+00 | -0.150 | REJECT |
| triple_bottom | BULL | 90 | 0.567 | 1.12 | 1.31 | 0.464 | 0.499 | 1.18e-01 | 0.135 | INSUFFICIENT |
| inverse_head_shoulders | BULL | 606 | 0.474 | -1.05 | 0.81 | 0.434 | 0.525 | 9.95e-01 | -0.108 | REJECT |
| double_top | BULL | 2820 | 0.505 | -1.63 | 0.73 | 0.486 | 0.583 | 1.00e+00 | -0.187 | REJECT |
| triple_top | BULL | 90 | 0.522 | -0.16 | 0.96 | 0.420 | 0.531 | 6.09e-01 | -0.019 | INSUFFICIENT |
| head_shoulders | BEAR | 364 | 0.503 | 0.32 | 1.05 | 0.452 | 0.490 | 3.37e-01 | 0.024 | REJECT |

### Axis 9 Triple Bottom WF1 Deepdive

| pattern | sub_key | N | WR | EV | PF | Wilson_lo | BEV | Bonf_p | Kelly | verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| triple_bottom | 2019-2020 | 21 | 0.286 | -3.09 | 0.33 | 0.138 | 0.550 | 9.96e-01 | -0.587 | INSUFFICIENT |

## Spread-adjusted Verdict Comparison

| pattern | flat-1.5p verdict | spread-adj verdict | flip |
|---|---|---|---|
| ascending_triangle | REJECT | REJECT | none |
| rising_wedge | REJECT | REJECT | none |
| bull_flag | REJECT | REJECT | none |
| descending_triangle | REJECT | REJECT | none |
| falling_wedge | REJECT | REJECT | none |
| bear_flag | REJECT | REJECT | none |
| double_bottom | REJECT | REJECT | none |
| triple_bottom | REJECT | REJECT | none |
| inverse_head_shoulders | REJECT | REJECT | none |
| double_top | REJECT | REJECT | none |
| triple_top | REJECT | REJECT | none |
| head_shoulders | REJECT | REJECT | none |

Spread-adjusted EV did not rescue any cell. Current evidence supports that the flat-1.5p W2 REJECT was directionally valid.

## Cell Root Cause and Wave 2b Proposed Fix

| pattern | root cause | proposed fix |
|---|---|---|
| ascending_triangle | negative spread-adjusted EV; R:R sensitive (larger TP was less bad, best rr=1.25) | test W2b geometry with rr=1.25, London, q2 as pre-registered diagnostic filters only |
| rising_wedge | negative spread-adjusted EV; R:R sensitive (larger TP was less bad, best rr=1.25) | test W2b geometry with rr=1.25, London, q1 as pre-registered diagnostic filters only |
| bull_flag | negative spread-adjusted EV; R:R sensitive (larger TP was less bad, best rr=1.25); hour-local edge only in London; pivot quality sensitive (q3) | test W2b geometry with rr=1.25, London, q3 as pre-registered diagnostic filters only |
| descending_triangle | negative spread-adjusted EV; R:R sensitive (larger TP was less bad, best rr=1.25) | test W2b geometry with rr=1.25, London_NY_overlap, q2 as pre-registered diagnostic filters only |
| falling_wedge | negative spread-adjusted EV; R:R sensitive (larger TP was less bad, best rr=1.25); hour-local edge only in London_NY_overlap | test W2b geometry with rr=1.25, London_NY_overlap, q1 as pre-registered diagnostic filters only |
| bear_flag | negative spread-adjusted EV; R:R sensitive (larger TP was less bad, best rr=1.25); hour-local edge only in London; pivot quality sensitive (q2) | test W2b geometry with rr=1.25, London, q2 as pre-registered diagnostic filters only |
| double_bottom | negative spread-adjusted EV; R:R sensitive (larger TP was less bad, best rr=1.25) | test W2b geometry with rr=1.25, Asia, q1 as pre-registered diagnostic filters only |
| triple_bottom | negative spread-adjusted EV; R:R sensitive (larger TP was less bad, best rr=1.25); hour-local edge only in London_NY_overlap; pivot quality sensitive (q1) | test W2b geometry with rr=1.25, London_NY_overlap, q1 as pre-registered diagnostic filters only |
| inverse_head_shoulders | negative spread-adjusted EV; R:R sensitive (larger TP was less bad, best rr=1.25); hour-local edge only in London_NY_overlap | test W2b geometry with rr=1.25, London_NY_overlap, q4 as pre-registered diagnostic filters only |
| double_top | negative spread-adjusted EV; R:R sensitive (larger TP was less bad, best rr=1.25) | test W2b geometry with rr=1.25, Asia, q4 as pre-registered diagnostic filters only |
| triple_top | negative spread-adjusted EV; R:R sensitive (larger TP was less bad, best rr=1.25); hour-local edge only in London_NY_overlap; pivot quality sensitive (q3) | test W2b geometry with rr=1.25, London_NY_overlap, q3 as pre-registered diagnostic filters only |
| head_shoulders | negative spread-adjusted EV; R:R sensitive (larger TP was less bad, best rr=1.25) | test W2b geometry with rr=1.25, London_NY_overlap, q3 as pre-registered diagnostic filters only |

## Prioritized Wave 2b Candidate List

| rank | pattern | axis | sub_key | N | EV | PF | proposed W2b test |
|---:|---|---|---|---:|---:|---:|---|
| 1 | inverse_head_shoulders | hour_bucket | London_NY_overlap | 203 | 1.82 | 1.30 | lock as diagnostic candidate; rerun out-of-sample only before eligibility |
| 2 | triple_bottom | rr_optimal | rr=1.25 | 155 | 0.57 | 1.13 | lock as diagnostic candidate; rerun out-of-sample only before eligibility |
| 3 | head_shoulders | regime | BEAR | 364 | 0.32 | 1.05 | lock as diagnostic candidate; rerun out-of-sample only before eligibility |

## Decision

No LIVE or Shadow eligibility is created by this task. Wave 2b should remain a detector-geometry diagnosis, not a filter-stacking promotion path.
