# price_shock 5-seat exit-free fixed-horizon audit — 2026-07-24

**Task W0-2** — verification debt on the 5 promoted `price_shock_rev` seats (promoted 2026-05-18 off the 2021-12-24..2026-05-15 grid BT, BH-FDR m=3744, Wilson_lo>=0.58). Frozen production triggers (strategies/hourly/, `signal_mask_from_dataframe`) re-detected on ~12.6y MASSIVE H1 parquet (2013-12-16..2026-07-24); forward MFE/MAE/net move measured exit-free at fixed horizons {4h, 12h, 24h, 72h, 120h}. No BE/Trail, no TP/SL simulation, no new mining. Report-only: no tier action taken.

## Data-quality finding (affects the promoted cells themselves)

The MASSIVE H1 feed contains **Saturday-stamped rows** (FX closed) and **spike-and-revert bad prints** — e.g. EUR_GBP −23.7%/h (2022-06-17 20:00, 0.678 vs real ~0.856), USD_CAD −26.1%/h (2024-12-20 21:00), NZD_JPY −11.1%/h (2023-01-17 21:00), AUD_JPY bars on Saturday 2023-12-02 ~16% off market. A 1%-tile log-return shock trigger is a magnet for such prints: the bad low print triggers the seat, the instant revert books a fake MR profit that live OANDA execution could never capture. **The frozen grid-BT caches contain the same bars** (bad prints ≥5%/h: EUR_GBP 15, USD_CAD 18, NZD_JPY 17, AUD_JPY 10, EUR_AUD 0), so the promoted `ev_pip` values are partly artifact-inflated. All headline stats below therefore use a cleaned feed:

- drop Saturday rows (production OANDA H1 has none);
- exclude events on bad-print bars (|1h ret| ≥ 3% reverting ≥ 75% within 2 bars — validated to keep real shocks: Brexit AUD_JPY −5.6% 2016-06-24 stays IN);
- exclude events whose forward window crosses a bad-print bar (path artifact).

Raw-feed (grid-BT-equivalent) numbers are shown for contrast.

## Method

- Entry reference = event-bar Close; forward window = bars t+1..t+h (event bar excluded, asserted).
- Horizons are H1 *market* bars (== hours while market open; spans weekends).
- Bootstrap: one-sided p for mean(net)>0, B=10,000, seed=42; `p_noovl` = same test on cluster-thinned events (non-overlapping forward windows) — the honest N under event clustering.
- RT friction: task theoretical values where given (EUR_GBP 3.0p); otherwise repo-standard BT friction model (app.py `_bt_spread`+`_bt_get_slippage`) per-event median. Headroom = MFE_p50 / RT.
- Report-only flags: FLAG if bootstrap p >= 0.05, net median <= 0, net mean <= RT, or headroom < 2.0 at the seat's primary horizon (nearest fixed horizon to its frozen production time-stop). `promo-conc` = pre-promotion window (2013-2021, pure past-OOS) fails p<0.05 or its net mean <= RT — edge concentrated in the mined window.

## Seat verdict summary (primary horizon, full ~12.6y CLEAN window)

| Seat | Pair | Prod h | Audit h | N | net mean (p) | net p50 (p) | boot p | p_noovl | MFE p50 (p) | RT (p) | Headroom | raw mean (p) | Edge survives | promo-conc | FLAG |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| price_shock_rev_eur_gbp_h1_long | EUR_GBP | 3 | 4h | 615 | 17.98 | 7.80 | 0.0001 | 0.0001 | 19.40 | 3.00 | 6.47x | 29.59 | YES | ok | ok |
| price_shock_rev_eur_aud_h1_long | EUR_AUD | 12 | 12h | 663 | 31.89 | 14.00 | 0.0001 | 0.0001 | 54.20 | 1.55 | 34.97x | 36.44 | YES | ⚠️ | ok |
| price_shock_rev_usd_cad_h1_long | USD_CAD | 3 | 4h | 625 | 17.98 | 6.70 | 0.0001 | 0.0001 | 22.40 | 1.17 | 19.19x | 40.23 | YES | ⚠️ | ok |
| price_shock_rev_nzd_jpy_h1_long | NZD_JPY | 12 | 12h | 699 | 23.62 | 14.20 | 0.0001 | 0.0001 | 42.17 | 1.55 | 27.20x | 35.83 | YES | ok | ok |
| price_shock_rev_aud_jpy_h1_long | AUD_JPY | 12 | 12h | 1100 | 11.44 | 7.70 | 0.0001 | 0.0001 | 33.90 | 1.55 | 21.87x | 16.94 | YES | ⚠️ | ok |

## Trigger fidelity + artifact contamination of the promoted cells (raw feed)

| Seat | DB cell | DB N | Re-detected N (promo win) | Ratio | artifact-triggered | artifact share | DB WR | DB ev_pip |
|---|---|---|---|---|---|---|---|---|
| price_shock_rev_eur_gbp_h1_long | EUR_GBP_H1_LONG_SHOCK_1_3_Q5 | 239 | 240 | 1.004 | 17 | 7.1% | 72.8% | 55.8 |
| price_shock_rev_eur_aud_h1_long | EUR_AUD_H1_LONG_SHOCK_1_12_Q5 | 262 | 263 | 1.004 | 19 | 7.2% | 67.6% | 58.8 |
| price_shock_rev_usd_cad_h1_long | USD_CAD_H1_LONG_SHOCK_1_3_Q5 | 247 | 252 | 1.020 | 10 | 4.0% | 66.4% | 28.7 |
| price_shock_rev_nzd_jpy_h1_long | NZD_JPY_H1_LONG_SHOCK_1_12_Q5 | 303 | 304 | 1.003 | 39 | 12.8% | 64.0% | 58.9 |
| price_shock_rev_aud_jpy_h1_long | AUD_JPY_H1_LONG_SHOCK_1_12_ALL | 426 | 428 | 1.005 | 17 | 4.0% | 63.8% | 32.3 |

## price_shock_rev_eur_gbp_h1_long (EUR_GBP, vol_q=Q5, prod horizon=3 bars)

Data: 78,274 clean H1 rows (215 Saturday rows dropped, 7 bad-print bars), 2013-12-16 00:00:00+00:00 .. 2026-07-24 10:00:00+00:00 (12.6y). Events: raw 628 -> clean 616 (7 trigger artifacts excluded).

### Full-window CLEAN exit-free stats by horizon

| h | N | excl_path | N_noovl | MFE p25/p50/p75 (p) | MAE p25/p50/p75 (p) | net mean (p) | net p50 (p) | net>0 % | boot p | p_noovl | RT (p) | Headroom | raw mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **4h** | 615 | 1 | 565 | 8.85/19.40/48.00 | 3.60/10.30/24.05 | 17.98 | 7.80 | 62.8 | 0.0001 | 0.0001 | 3.00 | 6.47x | 29.59 |
| 12h | 615 | 1 | 514 | 12.30/26.60/56.75 | 5.50/15.40/34.75 | 19.00 | 10.30 | 62.6 | 0.0001 | 0.0001 | 3.00 | 8.87x | 30.07 |
| 24h | 615 | 1 | 462 | 17.15/37.90/73.75 | 8.85/23.20/46.45 | 14.77 | 10.40 | 58.2 | 0.0001 | 0.0001 | 3.00 | 12.63x | 26.12 |
| 72h | 614 | 2 | 358 | 26.10/56.60/104.20 | 19.03/43.85/79.48 | 17.19 | 10.75 | 56.8 | 0.0001 | 0.0001 | 3.00 | 18.87x | 29.04 |
| 120h | 609 | 7 | 311 | 33.50/74.50/123.20 | 26.30/56.00/107.20 | 20.57 | 10.70 | 55.3 | 0.0001 | 0.0001 | 3.00 | 24.83x | 30.51 |

### Sub-window CLEAN net move at primary horizon (4h)

| Window | N | net mean (p) | net p50 (p) | boot p | p_noovl |
|---|---|---|---|---|---|
| full | 615 | 17.98 | 7.80 | 0.0001 | 0.0001 |
| pre_promo | 377 | 6.11 | 3.10 | 0.0004 | 0.0002 |
| promo_2021_2026 | 227 | 38.45 | 23.40 | 0.0001 | 0.0001 |
| post_promo | 11 | 2.06 | 1.30 | 0.3486 | 0.2622 |

## price_shock_rev_eur_aud_h1_long (EUR_AUD, vol_q=Q5, prod horizon=12 bars)

Data: 78,701 clean H1 rows (935 Saturday rows dropped, 2 bad-print bars), 2013-12-16 00:00:00+00:00 .. 2026-07-24 10:00:00+00:00 (12.6y). Events: raw 678 -> clean 663 (2 trigger artifacts excluded).

### Full-window CLEAN exit-free stats by horizon

| h | N | excl_path | N_noovl | MFE p25/p50/p75 (p) | MAE p25/p50/p75 (p) | net mean (p) | net p50 (p) | net>0 % | boot p | p_noovl | RT (p) | Headroom | raw mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4h | 663 | 0 | 610 | 14.80/33.50/73.65 | 9.60/23.40/43.75 | 29.41 | 9.70 | 59.0 | 0.0001 | 0.0001 | 1.39 | 24.19x | 32.83 |
| **12h** | 663 | 0 | 543 | 21.35/54.20/116.70 | 15.10/38.00/74.75 | 31.89 | 14.00 | 59.7 | 0.0001 | 0.0001 | 1.55 | 34.97x | 36.44 |
| 24h | 662 | 1 | 477 | 32.03/75.55/152.45 | 22.07/52.95/101.87 | 35.42 | 25.10 | 60.3 | 0.0001 | 0.0001 | 1.28 | 59.02x | 39.59 |
| 72h | 656 | 6 | 371 | 55.20/129.50/244.52 | 37.90/94.05/172.83 | 40.08 | 20.35 | 55.5 | 0.0001 | 0.0001 | 1.32 | 98.01x | 43.57 |
| 120h | 653 | 8 | 310 | 74.60/161.30/288.20 | 48.20/121.00/218.40 | 48.59 | 33.60 | 56.2 | 0.0001 | 0.0003 | 1.39 | 116.46x | 48.93 |

### Sub-window CLEAN net move at primary horizon (12h)

| Window | N | net mean (p) | net p50 (p) | boot p | p_noovl |
|---|---|---|---|---|---|
| full | 663 | 31.89 | 14.00 | 0.0001 | 0.0001 |
| pre_promo | 401 | 6.48 | 1.40 | 0.0645 | 0.0777 |
| promo_2021_2026 | 254 | 72.69 | 49.60 | 0.0001 | 0.0001 |
| post_promo | 8 | 10.51 | 6.85 | 0.2158 | 0.2336 |

## price_shock_rev_usd_cad_h1_long (USD_CAD, vol_q=Q5, prod horizon=3 bars)

Data: 77,723 clean H1 rows (81 Saturday rows dropped, 11 bad-print bars), 2013-12-16 00:00:00+00:00 .. 2026-07-24 10:00:00+00:00 (12.6y). Events: raw 638 -> clean 625 (11 trigger artifacts excluded).

### Full-window CLEAN exit-free stats by horizon

| h | N | excl_path | N_noovl | MFE p25/p50/p75 (p) | MAE p25/p50/p75 (p) | net mean (p) | net p50 (p) | net>0 % | boot p | p_noovl | RT (p) | Headroom | raw mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **4h** | 625 | 0 | 565 | 10.70/22.40/46.30 | 6.10/16.60/33.10 | 17.98 | 6.70 | 62.1 | 0.0001 | 0.0001 | 1.17 | 19.19x | 40.23 |
| 12h | 625 | 0 | 524 | 15.40/32.00/62.00 | 9.10/24.30/46.80 | 18.49 | 7.90 | 58.9 | 0.0001 | 0.0001 | 1.48 | 21.69x | 40.86 |
| 24h | 625 | 0 | 479 | 21.70/45.40/83.70 | 15.40/38.50/71.80 | 15.46 | 8.80 | 56.3 | 0.0002 | 0.0001 | 1.10 | 41.27x | 37.54 |
| 72h | 620 | 5 | 372 | 36.98/74.75/137.80 | 26.70/61.25/112.85 | 20.42 | 13.35 | 54.5 | 0.0005 | 0.0001 | 1.10 | 67.95x | 42.55 |
| 120h | 617 | 8 | 306 | 49.40/96.10/168.40 | 39.10/85.70/150.80 | 23.51 | 22.30 | 55.8 | 0.0002 | 0.0003 | 1.10 | 87.36x | 34.04 |

### Sub-window CLEAN net move at primary horizon (4h)

| Window | N | net mean (p) | net p50 (p) | boot p | p_noovl |
|---|---|---|---|---|---|
| full | 625 | 17.98 | 6.70 | 0.0001 | 0.0001 |
| pre_promo | 376 | 2.56 | 2.35 | 0.0662 | 0.1622 |
| promo_2021_2026 | 240 | 42.35 | 19.20 | 0.0001 | 0.0001 |
| post_promo | 9 | 12.42 | 8.20 | 0.0775 | 0.0736 |

## price_shock_rev_nzd_jpy_h1_long (NZD_JPY, vol_q=Q5, prod horizon=12 bars)

Data: 80,047 clean H1 rows (3497 Saturday rows dropped, 25 bad-print bars), 2013-12-16 00:00:00+00:00 .. 2026-07-24 10:00:00+00:00 (12.6y). Events: raw 771 -> clean 699 (24 trigger artifacts excluded).

### Full-window CLEAN exit-free stats by horizon

| h | N | excl_path | N_noovl | MFE p25/p50/p75 (p) | MAE p25/p50/p75 (p) | net mean (p) | net p50 (p) | net>0 % | boot p | p_noovl | RT (p) | Headroom | raw mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4h | 699 | 0 | 623 | 11.35/27.52/62.03 | 5.00/15.90/34.50 | 21.79 | 10.60 | 63.8 | 0.0001 | 0.0001 | 1.64 | 16.78x | 31.45 |
| **12h** | 699 | 0 | 542 | 19.20/42.17/76.40 | 8.75/25.90/57.15 | 23.62 | 14.20 | 61.9 | 0.0001 | 0.0001 | 1.55 | 27.20x | 35.83 |
| 24h | 697 | 2 | 476 | 25.70/55.12/96.30 | 14.40/37.60/79.90 | 24.94 | 21.80 | 63.4 | 0.0001 | 0.0001 | 1.52 | 36.14x | 36.10 |
| 72h | 692 | 7 | 364 | 39.30/85.08/144.60 | 24.18/64.00/140.65 | 22.22 | 20.35 | 58.1 | 0.0001 | 0.0002 | 1.52 | 55.79x | 37.76 |
| 120h | 686 | 13 | 304 | 47.85/97.50/174.93 | 36.76/93.95/191.97 | 20.45 | 22.30 | 56.9 | 0.0003 | 0.0033 | 1.52 | 63.93x | 39.98 |

### Sub-window CLEAN net move at primary horizon (12h)

| Window | N | net mean (p) | net p50 (p) | boot p | p_noovl |
|---|---|---|---|---|---|
| full | 699 | 23.62 | 14.20 | 0.0001 | 0.0001 |
| pre_promo | 434 | 9.36 | 7.50 | 0.0011 | 0.0274 |
| promo_2021_2026 | 260 | 47.38 | 35.86 | 0.0001 | 0.0001 |
| post_promo | 5 | 26.41 | 10.20 | 0.0001 | 0.0001 |

## price_shock_rev_aud_jpy_h1_long (AUD_JPY, vol_q=ALL, prod horizon=12 bars)

Data: 79,915 clean H1 rows (3006 Saturday rows dropped, 8 bad-print bars), 2013-12-16 00:00:00+00:00 .. 2026-07-24 10:00:00+00:00 (12.6y). Events: raw 1150 -> clean 1101 (8 trigger artifacts excluded).

### Full-window CLEAN exit-free stats by horizon

| h | N | excl_path | N_noovl | MFE p25/p50/p75 (p) | MAE p25/p50/p75 (p) | net mean (p) | net p50 (p) | net>0 % | boot p | p_noovl | RT (p) | Headroom | raw mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4h | 1100 | 1 | 993 | 9.00/21.25/42.65 | 8.20/18.45/38.33 | 10.24 | 5.31 | 56.9 | 0.0001 | 0.0001 | 1.52 | 13.93x | 15.45 |
| **12h** | 1100 | 1 | 876 | 14.57/33.90/61.60 | 11.98/30.75/60.90 | 11.44 | 7.70 | 56.5 | 0.0001 | 0.0001 | 1.55 | 21.87x | 16.94 |
| 24h | 1100 | 1 | 756 | 20.67/45.55/83.82 | 16.28/41.65/84.60 | 10.49 | 9.55 | 57.3 | 0.0001 | 0.0001 | 1.52 | 29.87x | 18.02 |
| 72h | 1098 | 3 | 505 | 31.53/75.15/133.27 | 30.62/71.70/146.70 | 5.77 | 9.95 | 53.9 | 0.0671 | 0.0019 | 1.52 | 49.28x | 12.98 |
| 120h | 1092 | 8 | 402 | 41.42/93.51/163.10 | 40.62/93.85/178.68 | 7.64 | 12.14 | 53.7 | 0.0403 | 0.0103 | 1.52 | 61.32x | 14.80 |

### Sub-window CLEAN net move at primary horizon (12h)

| Window | N | net mean (p) | net p50 (p) | boot p | p_noovl |
|---|---|---|---|---|---|
| full | 1100 | 11.44 | 7.70 | 0.0001 | 0.0001 |
| pre_promo | 694 | 1.86 | 2.05 | 0.1915 | 0.2319 |
| promo_2021_2026 | 391 | 28.52 | 24.80 | 0.0001 | 0.0001 |
| post_promo | 15 | 9.03 | 26.00 | 0.1858 | 0.1867 |

## Method caveats

- Exit-free net move is NOT the production payoff: production seats exit at horizon close or a catastrophic -2xATR-proxy stop. Exit-free removes the stop, so tail losses here can exceed production; conversely winners are never cut. This is the assumption-free view of whether the raw directional edge exists.
- Overlapping events (shock clusters) share forward windows; the all-events bootstrap overstates significance. `p_noovl` is the honest lower bound.
- RT for EUR_AUD/USD_CAD/NZD_JPY/AUD_JPY uses the repo BT friction model (else-branch/JPY-branch base spreads). For EUR_AUD this is likely optimistic (real EUR_AUD spreads run wider than majors); headroom should be read with margin. Additionally, Q5-vol shock bars have spreads far above session averages (death-zone regime), so ALL headroom numbers are upper bounds.
- The bad-print detector is conservative (3%/h + 75% revert in 2 bars); residual sub-3% artifacts may remain in both clean stats and the grid cells.
- Grid-BT DB window is 2021-12-24..2026-05-15 (~4.4y), not 12.3y; this audit extends the same frozen triggers back to 2013-12 (pre_promo = pure past-OOS) and forward past promotion (post_promo, small N).
