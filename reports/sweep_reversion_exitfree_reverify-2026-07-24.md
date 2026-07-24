# sweep_reversion_eurgbp_late — exit-free 12.4y re-verification (2026-07-24)

Data: `EUR_GBP_15m.parquet` 305817 bars, 2014-01-05 22:00:00+00:00 → 2026-05-05 06:00:00+00:00 (12.33y)
Frozen trigger: LATE 21-24 UTC / BUY / low < swing_lo(96) − 0.05×ATR14 ∧ close > swing_lo / dedup 12 bars / entry next-bar open
Events: **N=543** (~3.67/month)

## 1. Trigger replication check vs registered claim (H=48 close, −1.5p)

| metric | re-run | registered (2026-06-12) |
|---|--:|--:|
| N | 543 | 543 |
| WR | 0.597 | 0.597 |
| mean net pip | +6.22 | +6.22 |
| t-stat | 4.46 | 4.46 |

## 2. Exit-free forward horizons (gross pips, no exit design)

| h | N | MFE p25/p50/p75 | MAE p25/p50/p75 | net mean | net median | pos% | boot p (mean>0) | MFE/MAE p50 | headroom (MFE_p50/RT3.0) |
|---|--:|---|---|--:|--:|--:|--:|--:|--:|
| 4h | 543 | 6.5/9.7/14.0 | 3.4/8.4/17.1 | +6.20 | +3.40 | 72.2 | 0.0000 | 1.155 | 3.23x |
| 12h | 543 | 10.5/16.6/28.0 | 7.1/13.3/25.8 | +7.72 | +5.10 | 62.6 | 0.0000 | 1.248 | 5.53x |
| 24h | 543 | 13.8/25.5/41.5 | 11.8/27.2/48.5 | +5.09 | +3.70 | 55.8 | 0.0022 | 0.937 | 8.50x |
| 72h | 542 | 21.0/39.2/65.7 | 25.4/49.2/99.4 | +7.45 | +1.70 | 51.8 | 0.0025 | 0.796 | 13.07x |
| 120h | 541 | 27.3/47.9/87.5 | 34.4/71.5/125.4 | +10.07 | +5.40 | 53.2 | 0.0016 | 0.67 | 15.97x |

Friction: RT theoretical EUR_GBP 3.0p / measured floor 1.3p / original scan assumed 1.5p. `net_mean_minus_rt` (mean − 3.0p): 4h +3.20p, 12h +4.72p, 24h +2.09p, 72h +4.45p, 120h +7.07p

## 3. Per-year stability (gross pips)

| year | N | net12h mean | net12h med | MFE12h p50 | net24h mean | net24h med | MFE24h p50 |
|---|--:|--:|--:|--:|--:|--:|--:|
| 2014 | 19 | -0.82 | -3.60 | +11.50 | -4.15 | +4.10 | +13.50 |
| 2015 | 14 | +20.88 | +24.50 | +37.45 | +19.96 | +6.90 | +50.60 |
| 2016 | 20 | +4.82 | +12.05 | +30.40 | +5.47 | +12.20 | +45.90 |
| 2017 | 16 | -2.11 | -3.85 | +14.55 | +3.16 | +4.80 | +20.70 |
| 2018 | 21 | +2.60 | +5.90 | +15.70 | -3.50 | -3.90 | +26.90 |
| 2019 | 15 | +8.17 | +8.70 | +26.30 | -5.18 | -4.20 | +31.40 |
| 2020 | 16 | +10.71 | +10.70 | +17.50 | +6.83 | +5.20 | +27.60 |
| 2021 | 54 | +8.57 | +5.65 | +16.75 | -0.91 | -7.10 | +23.15 |
| 2022 | 65 | +7.26 | +2.90 | +21.60 | +10.12 | +10.10 | +33.50 |
| 2023 | 99 | +5.98 | +5.80 | +18.20 | +3.63 | +4.10 | +26.10 |
| 2024 | 103 | +9.85 | +1.80 | +12.10 | +9.77 | -0.50 | +17.00 |
| 2025 | 74 | +11.58 | +10.70 | +20.70 | +7.93 | +8.65 | +31.00 |
| 2026 | 27 | +3.96 | +2.40 | +13.70 | -4.25 | +1.80 | +17.00 |

## 4. Caveats

- Bootstrap p is iid-resample; at 72h/120h forward windows of adjacent events can overlap (events avg ~5.5 days apart but clustered 2021+), so long-horizon p-values understate dependence. 4h/12h are near-clean.
- Event frequency regime shift stands: 78% of events fall in 2021-2026 (54-103/yr) vs 14-21/yr in 2014-2020. Per-event edge is positive in most thin years too, but N there is small.
- MFE/MAE p50 asymmetry favors BUY only at 4h (1.16) and 12h (1.25); it inverts at >=24h — the edge is a ~12h mean-reversion, consistent with the pre-reg 12h-hold design horizon.

