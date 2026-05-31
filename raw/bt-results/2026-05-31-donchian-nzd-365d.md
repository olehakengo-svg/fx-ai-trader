# Donchian x NZD pair 365d BT pre-reg evidence (2026-05-31)

- Strategy: `donchian_momentum_breakout` via production `DonchianMomentumBreakout.evaluate(... backtest_mode=True)`.
- Data source: `data/cache/massive/{PAIR}_15m.parquet` only; Yahoo fallback is not used.
- Lookback request: `utcnow - 365d` to `utcnow`; available MASSIVE bars end at each cache's latest timestamp.
- Bonferroni: m=9, alpha=0.005556, z=2.539. Bootstrap EV CI uses 10,000 resamples.

## Source coverage

| Pair | Source | Bars | From | To | pip_mult |
|---|---|---:|---|---|---:|
| NZD_JPY | `data/cache/massive/NZD_JPY_15m.parquet` | 24433 | 2025-06-03T22:45:00+00:00 | 2026-05-29T20:45:00+00:00 | 100 |
| NZD_USD | `data/cache/massive/NZD_USD_15m.parquet` | 24378 | 2025-06-03T22:45:00+00:00 | 2026-05-29T20:45:00+00:00 | 10000 |
| AUD_JPY | `data/cache/massive/AUD_JPY_15m.parquet` | 24354 | 2025-06-03T22:45:00+00:00 | 2026-05-29T20:45:00+00:00 | 100 |
| USD_CAD | `data/cache/massive/USD_CAD_15m.parquet` | 24433 | 2025-06-03T22:45:00+00:00 | 2026-05-29T20:45:00+00:00 | 10000 |

## Overall and direction split

| Pair/Cohort | N | WR | EV(pips) | PF | Wilson_lo | BFlo | Kelly | HalfKelly | MaxDD(pips) | Bootstrap EV 95% CI |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| NZD_JPY Overall | 136 | 33.1% | -4.64 | 0.57 | 0.257 | 0.238 | -0.246 | -0.123 | 698.82 | [-7.65, -1.49] |
| NZD_JPY BUY | 119 | 34.5% | -4.70 | 0.57 | 0.265 | 0.244 | -0.263 | -0.131 | 627.11 | [-7.95, -1.36] |
| NZD_JPY SELL | 17 | 23.5% | -4.22 | 0.62 | 0.096 | 0.074 | -0.144 | -0.072 | 142.15 | [-12.92, 5.84] |
| NZD_USD Overall | 236 | 29.2% | -3.95 | 0.55 | 0.238 | 0.224 | -0.236 | -0.118 | 957.02 | [-5.78, -2.05] |
| NZD_USD BUY | 134 | 22.4% | -5.27 | 0.44 | 0.162 | 0.146 | -0.282 | -0.141 | 726.54 | [-7.55, -2.84] |
| NZD_USD SELL | 102 | 38.2% | -2.22 | 0.73 | 0.294 | 0.271 | -0.145 | -0.072 | 244.91 | [-5.13, 0.76] |
| AUD_JPY Overall | 195 | 35.9% | -2.76 | 0.73 | 0.295 | 0.278 | -0.131 | -0.065 | 694.52 | [-5.51, 0.12] |
| AUD_JPY BUY | 192 | 35.9% | -2.83 | 0.73 | 0.295 | 0.277 | -0.136 | -0.068 | 699.71 | [-5.57, -0.04] |
| AUD_JPY SELL | 3 | 33.3% | 1.73 | 1.15 | 0.061 | 0.041 | 0.044 | 0.022 | 17.81 | [-17.81, 39.05] |
| USD_CAD Overall | 306 | 27.5% | -3.58 | 0.59 | 0.228 | 0.215 | -0.188 | -0.094 | 1123.30 | [-5.22, -1.87] |
| USD_CAD BUY | 184 | 21.2% | -5.86 | 0.39 | 0.159 | 0.146 | -0.335 | -0.168 | 1099.94 | [-7.69, -3.94] |
| USD_CAD SELL | 122 | 36.9% | -0.14 | 0.98 | 0.288 | 0.267 | -0.007 | -0.003 | 139.97 | [-3.10, 2.97] |

## Direction x session cells

| Pair/Cell | N | WR | EV(pips) | PF | Wilson_lo | BFlo | Kelly | HalfKelly | MaxDD(pips) | Bootstrap EV 95% CI |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| NZD_JPY BUY Asia | 51 | 37.3% | -4.49 | 0.58 | 0.253 | 0.224 | -0.266 | -0.133 | 298.20 | [-9.34, 0.59] |
| NZD_JPY BUY London | 26 | 34.6% | -3.65 | 0.65 | 0.194 | 0.162 | -0.189 | -0.095 | 187.11 | [-10.36, 3.78] |
| NZD_JPY BUY Overlap | 24 | 37.5% | -2.74 | 0.73 | 0.212 | 0.177 | -0.138 | -0.069 | 95.61 | [-9.89, 5.04] |
| NZD_JPY BUY NY | 18 | 22.2% | -9.42 | 0.26 | 0.090 | 0.070 | -0.630 | -0.315 | 177.70 | [-15.69, -2.32] |
| NZD_JPY SELL Asia | 6 | 16.7% | -4.05 | 0.64 | 0.030 | 0.020 | -0.093 | -0.046 | 67.98 | [-16.32, 16.35] |
| NZD_JPY SELL London | 2 | 50.0% | -1.92 | 0.78 | 0.095 | 0.063 | -0.138 | -0.069 | 17.75 | [-17.75, 13.90] |
| NZD_JPY SELL Overlap | 4 | 25.0% | -1.97 | 0.77 | 0.046 | 0.031 | -0.074 | -0.037 | 34.64 | [-17.19, 15.89] |
| NZD_JPY SELL NY | 5 | 20.0% | -7.14 | 0.48 | 0.036 | 0.024 | -0.218 | -0.109 | 68.38 | [-18.32, 13.13] |
| NZD_USD BUY Asia | 39 | 25.6% | -5.24 | 0.44 | 0.146 | 0.123 | -0.327 | -0.163 | 221.52 | [-9.38, -0.70] |
| NZD_USD BUY London | 33 | 24.2% | -3.95 | 0.57 | 0.128 | 0.106 | -0.185 | -0.093 | 183.51 | [-8.66, 1.27] |
| NZD_USD BUY Overlap | 42 | 11.9% | -7.46 | 0.26 | 0.052 | 0.041 | -0.340 | -0.170 | 326.72 | [-10.73, -3.79] |
| NZD_USD BUY NY | 20 | 35.0% | -2.87 | 0.67 | 0.181 | 0.148 | -0.169 | -0.085 | 95.98 | [-9.75, 5.25] |
| NZD_USD SELL Asia | 26 | 53.8% | 3.44 | 1.65 | 0.355 | 0.308 | 0.212 | 0.106 | 56.02 | [-2.53, 9.53] |
| NZD_USD SELL London | 17 | 23.5% | -8.85 | 0.19 | 0.096 | 0.074 | -1.030 | -0.515 | 150.51 | [-13.64, -3.23] |
| NZD_USD SELL Overlap | 32 | 43.8% | -0.71 | 0.90 | 0.282 | 0.245 | -0.048 | -0.024 | 77.69 | [-5.88, 4.59] |
| NZD_USD SELL NY | 27 | 25.9% | -5.29 | 0.47 | 0.132 | 0.108 | -0.288 | -0.144 | 185.35 | [-10.58, 0.69] |
| AUD_JPY BUY Asia | 79 | 40.5% | -1.27 | 0.86 | 0.304 | 0.277 | -0.064 | -0.032 | 290.26 | [-5.33, 3.08] |
| AUD_JPY BUY London | 37 | 35.1% | -1.29 | 0.87 | 0.218 | 0.188 | -0.055 | -0.027 | 186.87 | [-7.67, 5.80] |
| AUD_JPY BUY Overlap | 45 | 40.0% | -1.05 | 0.90 | 0.270 | 0.239 | -0.045 | -0.022 | 245.43 | [-7.30, 5.35] |
| AUD_JPY BUY NY | 31 | 19.4% | -11.26 | 0.19 | 0.092 | 0.074 | -0.834 | -0.417 | 348.92 | [-15.81, -5.86] |
| AUD_JPY SELL Asia | 2 | 50.0% | 10.62 | 2.19 | 0.095 | 0.063 | 0.272 | 0.136 | 17.81 | [-17.81, 39.05] |
| AUD_JPY SELL London | 0 | 0.0% | 0.00 | 0.00 | 0.000 | 0.000 | 0.000 | 0.000 | 0.00 | [0.00, 0.00] |
| AUD_JPY SELL Overlap | 1 | 0.0% | -16.05 | 0.00 | 0.000 | 0.000 | 0.000 | 0.000 | 16.05 | [-16.05, -16.05] |
| AUD_JPY SELL NY | 0 | 0.0% | 0.00 | 0.00 | 0.000 | 0.000 | 0.000 | 0.000 | 0.00 | [0.00, 0.00] |
| USD_CAD BUY Asia | 35 | 25.7% | -5.69 | 0.37 | 0.142 | 0.118 | -0.438 | -0.219 | 217.57 | [-9.57, -1.54] |
| USD_CAD BUY London | 58 | 20.7% | -4.88 | 0.44 | 0.123 | 0.105 | -0.268 | -0.134 | 329.31 | [-7.81, -1.75] |
| USD_CAD BUY Overlap | 62 | 21.0% | -6.31 | 0.37 | 0.127 | 0.109 | -0.351 | -0.176 | 424.18 | [-9.48, -2.82] |
| USD_CAD BUY NY | 29 | 17.2% | -7.05 | 0.35 | 0.076 | 0.060 | -0.314 | -0.157 | 236.48 | [-11.98, -1.16] |
| USD_CAD SELL Asia | 12 | 25.0% | -3.68 | 0.47 | 0.089 | 0.067 | -0.287 | -0.143 | 72.04 | [-8.90, 2.41] |
| USD_CAD SELL London | 30 | 33.3% | -1.68 | 0.77 | 0.192 | 0.162 | -0.099 | -0.050 | 103.82 | [-6.41, 3.35] |
| USD_CAD SELL Overlap | 62 | 38.7% | 0.50 | 1.06 | 0.276 | 0.248 | 0.023 | 0.011 | 95.89 | [-3.95, 5.16] |
| USD_CAD SELL NY | 18 | 44.4% | 2.62 | 1.34 | 0.246 | 0.203 | 0.114 | 0.057 | 39.79 | [-6.51, 12.36] |

## Walk-forward 3-fold

| Pair | Fold | N | EV | BUY_EV | SELL_EV |
|---|---:|---:|---:|---:|---:|
| NZD_JPY | 1 | 45 | -4.77 | -5.62 | -0.87 |
| NZD_JPY | 2 | 46 | -6.15 | -6.75 | 7.11 |
| NZD_JPY | 3 | 45 | -2.95 | -1.42 | -11.28 |
| NZD_JPY | sign-test | 0/3 positive folds | p=1.000 |  |  |
| NZD_USD | 1 | 79 | -4.44 | -7.50 | -0.60 |
| NZD_USD | 2 | 78 | -2.62 | -3.72 | -0.30 |
| NZD_USD | 3 | 79 | -4.76 | -4.82 | -4.72 |
| NZD_USD | sign-test | 0/3 positive folds | p=1.000 |  |  |
| AUD_JPY | 1 | 65 | -5.34 | -5.14 | -17.81 |
| AUD_JPY | 2 | 65 | -2.93 | -3.59 | 39.05 |
| AUD_JPY | 3 | 65 | -0.03 | 0.22 | -16.05 |
| AUD_JPY | sign-test | 0/3 positive folds | p=1.000 |  |  |
| USD_CAD | 1 | 102 | -2.25 | -2.90 | -1.22 |
| USD_CAD | 2 | 102 | -3.33 | -5.13 | -0.44 |
| USD_CAD | 3 | 102 | -5.14 | -9.87 | 1.09 |
| USD_CAD | sign-test | 0/3 positive folds | p=1.000 |  |  |

## Control comparison

| Pair | Role | N | WR | EV(pips) | Total(pips) | BFlo | Verdict |
|---|---|---:|---:|---:|---:|---:|---|
| NZD_JPY | LIVE target | 136 | 33.1% | -4.64 | -630.68 | 0.238 | PRE_REG_FAIL |
| NZD_USD | LIVE target | 236 | 29.2% | -3.95 | -932.04 | 0.224 | PRE_REG_FAIL |
| AUD_JPY | control | 195 | 35.9% | -2.76 | -539.01 | 0.278 | PRE_REG_FAIL |
| USD_CAD | control | 306 | 27.5% | -3.58 | -1094.28 | 0.215 | PRE_REG_FAIL |

## Shadow vs BT degradation

| Pair | Shadow N | Shadow WR | Shadow EV | Shadow Total | BT N | BT WR | BT EV | BT Total | EV delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| NZD_JPY | 14 | 71.4% | 20.49 | 287.00 | 136 | 33.1% | -4.64 | -630.68 | -25.13 |
| NZD_USD | 16 | 68.8% | 15.52 | 248.00 | 236 | 29.2% | -3.95 | -932.04 | -19.47 |
| AUD_JPY | 10 | 10.0% | -12.18 | -122.00 | 195 | 35.9% | -2.76 | -539.01 | 9.42 |
| USD_CAD | 11 | 27.3% | -9.05 | -100.00 | 306 | 27.5% | -3.58 | -1094.28 | 5.47 |

## Final verdict cells

| Cell | N | WR | EV | BFlo | WF | Bootstrap CI | Verdict | Action proposal |
|---|---:|---:|---:|---:|---|---|---|---|
| NZD_JPY overall | 136 | 33.1% | -4.64 | 0.238 | 0/3 p=1.000 | [-7.65, -1.49] | PRE_REG_FAIL | propose immediate demote to 0.05x and trigger Live N=10 withdrawal check |
| NZD_JPY best-cell (SELL London) | 2 | 50.0% | -1.92 | 0.063 | n/a | [-17.75, 13.90] | PRE_REG_FAIL | best-cell only; do not change LIVE routing without new pre-reg |
| NZD_USD overall | 236 | 29.2% | -3.95 | 0.224 | 0/3 p=1.000 | [-5.78, -2.05] | PRE_REG_FAIL | propose immediate demote to 0.05x and trigger Live N=10 withdrawal check |
| NZD_USD best-cell (SELL Asia) | 26 | 53.8% | 3.44 | 0.308 | n/a | [-2.53, 9.53] | PRE_REG_FAIL | best-cell only; do not change LIVE routing without new pre-reg |

## Notes

- `BT_REQUIRE_MASSIVE_CACHE=1` is set before imports; if a required parquet is absent, the runner raises instead of falling back to Yahoo.
- The generic `app.run_daytrade_backtest` path is not used because its DT whitelist does not include `donchian_momentum_breakout`; this runner calls the production strategy evaluator directly with `backtest_mode=True` and uses app spread/slippage helpers.
- Controls are sanity floors only. They are not candidates for LIVE changes in this task.
