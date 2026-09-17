# B3 Turtle Soup BT (USDJPY M5)

**Status**: OK
**Rule**: R1 Slow & Strict
**Bonferroni m**: 27
**Primary cell**: `{'failure_window': 12, 'exit_method': '100_trailing', 'session_boundary': 'London_close_16UTC'}`
**Catalog source**: `/Users/jg-n-012/test/wiki/learning/global-retail-fx-edges-2026-05-03.md`

## Strategy Spec
- Donchian: prev 20 trading days high/low.
- Failure trigger: close back through breakout level by 5 pip within `failure_window` M5 bars.
- Filters: prev_close < 158.000 and 8 BoJ intervention dates from catalog only. No HMM/MA/ATR gate.

## Sensitivity Grid
| failure_window | exit | boundary | N | Wilson_lo | PF | OOS/IS PF | Bonf p | Sharpe | Kelly | Max DD | Total pip | Verdict |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 6 | 50_trailing | NY_close_21UTC | 290 | 0.244 | 1.133 | 0.897 | 1.0000 | 0.602 | 0.033 | 811.9 | 535.4 | FAIL |
| 6 | 50_trailing | London_close_16UTC | 258 | 0.246 | 1.159 | 1.003 | 1.0000 | 0.727 | 0.037 | 804.4 | 549.6 | FAIL |
| 6 | 50_trailing | H24 | 319 | 0.256 | 1.129 | 0.852 | 1.0000 | 0.581 | 0.031 | 926.2 | 548.6 | FAIL |
| 6 | 100_trailing | NY_close_21UTC | 290 | 0.244 | 1.133 | 0.897 | 1.0000 | 0.602 | 0.033 | 811.9 | 535.4 | FAIL |
| 6 | 100_trailing | London_close_16UTC | 258 | 0.246 | 1.159 | 1.003 | 1.0000 | 0.727 | 0.037 | 804.4 | 549.6 | FAIL |
| 6 | 100_trailing | H24 | 319 | 0.256 | 1.129 | 0.852 | 1.0000 | 0.581 | 0.031 | 926.2 | 548.6 | FAIL |
| 6 | fixed_time | NY_close_21UTC | 290 | 0.244 | 1.133 | 0.897 | 1.0000 | 0.602 | 0.033 | 811.9 | 535.4 | FAIL |
| 6 | fixed_time | London_close_16UTC | 258 | 0.246 | 1.159 | 1.003 | 1.0000 | 0.727 | 0.037 | 804.4 | 549.6 | FAIL |
| 6 | fixed_time | H24 | 319 | 0.256 | 1.129 | 0.852 | 1.0000 | 0.581 | 0.031 | 926.2 | 548.6 | FAIL |
| 12 | 50_trailing | NY_close_21UTC | 367 | 0.250 | 1.100 | 0.975 | 1.0000 | 0.457 | 0.026 | 831.5 | 485.5 | FAIL |
| 12 | 50_trailing | London_close_16UTC | 331 | 0.252 | 1.116 | 1.055 | 1.0000 | 0.534 | 0.028 | 872.1 | 488.9 | FAIL |
| 12 | 50_trailing | H24 | 406 | 0.258 | 1.096 | 0.953 | 1.0000 | 0.440 | 0.024 | 888.7 | 498.4 | FAIL |
| 12 | 100_trailing | NY_close_21UTC | 367 | 0.250 | 1.100 | 0.975 | 1.0000 | 0.457 | 0.026 | 831.5 | 485.5 | FAIL |
| 12 | 100_trailing | London_close_16UTC | 331 | 0.252 | 1.116 | 1.055 | 1.0000 | 0.534 | 0.028 | 872.1 | 488.9 | FAIL |
| 12 | 100_trailing | H24 | 406 | 0.258 | 1.096 | 0.953 | 1.0000 | 0.440 | 0.024 | 888.7 | 498.4 | FAIL |
| 12 | fixed_time | NY_close_21UTC | 367 | 0.250 | 1.100 | 0.975 | 1.0000 | 0.457 | 0.026 | 831.5 | 485.5 | FAIL |
| 12 | fixed_time | London_close_16UTC | 331 | 0.252 | 1.116 | 1.055 | 1.0000 | 0.534 | 0.028 | 872.1 | 488.9 | FAIL |
| 12 | fixed_time | H24 | 406 | 0.258 | 1.096 | 0.953 | 1.0000 | 0.440 | 0.024 | 888.7 | 498.4 | FAIL |
| 24 | 50_trailing | NY_close_21UTC | 447 | 0.270 | 1.107 | 0.866 | 1.0000 | 0.498 | 0.029 | 909.9 | 606.1 | FAIL |
| 24 | 50_trailing | London_close_16UTC | 398 | 0.266 | 1.131 | 0.968 | 1.0000 | 0.612 | 0.033 | 718.3 | 642.3 | FAIL |
| 24 | 50_trailing | H24 | 493 | 0.273 | 1.096 | 0.841 | 1.0000 | 0.446 | 0.024 | 979.6 | 578.1 | FAIL |
| 24 | 100_trailing | NY_close_21UTC | 447 | 0.270 | 1.107 | 0.866 | 1.0000 | 0.498 | 0.029 | 909.9 | 606.1 | FAIL |
| 24 | 100_trailing | London_close_16UTC | 398 | 0.266 | 1.131 | 0.968 | 1.0000 | 0.612 | 0.033 | 718.3 | 642.3 | FAIL |
| 24 | 100_trailing | H24 | 493 | 0.273 | 1.096 | 0.841 | 1.0000 | 0.446 | 0.024 | 979.6 | 578.1 | FAIL |
| 24 | fixed_time | NY_close_21UTC | 447 | 0.270 | 1.107 | 0.866 | 1.0000 | 0.498 | 0.029 | 909.9 | 606.1 | FAIL |
| 24 | fixed_time | London_close_16UTC | 398 | 0.266 | 1.131 | 0.968 | 1.0000 | 0.612 | 0.033 | 718.3 | 642.3 | FAIL |
| 24 | fixed_time | H24 | 493 | 0.273 | 1.096 | 0.841 | 1.0000 | 0.446 | 0.024 | 979.6 | 578.1 | FAIL |

## Primary Deep Dive
{
  "n": 331,
  "wins": 99,
  "wr": 0.2990936555891239,
  "wilson_lo": 0.2523022924554468,
  "pf": 1.115886033943302,
  "oos_is_pf_ratio": 1.054692806869163,
  "is_pf": 1.082704334699159,
  "oos_pf": 1.1419204737732658,
  "bonferroni_p": 1.0,
  "raw_p": 0.9634498380157313,
  "sharpe": 0.5342391442080033,
  "kelly": 0.0275,
  "max_dd_pip": 872.1,
  "total_pip": 488.89999999999986
}

## Null Bootstrap
{
  "iterations": 1000,
  "actual_pf": 1.115886033943302,
  "mean_pf": 1.3595528054218788,
  "median_pf": 0.9885151792715174,
  "empirical_pf_percentile": 0.549,
  "two_sided_p": 0.902
}

## Time Cohorts
max_year_share=1.446, cohort_concentrated=True

| year | pnl_pip | n |
|---:|---:|---:|
| 2014 | -29.2 | 18 |
| 2015 | 262.0 | 26 |
| 2016 | 18.8 | 26 |
| 2017 | -23.5 | 33 |
| 2018 | -41.8 | 24 |
| 2019 | 16.3 | 16 |
| 2020 | -54.9 | 14 |
| 2021 | 31.2 | 31 |
| 2022 | -52.9 | 26 |
| 2023 | -152.5 | 53 |
| 2024 | -71.2 | 28 |
| 2025 | 706.8 | 32 |
| 2026 | -120.2 | 4 |

## Scenario Verdict
Scenario C — primary FAIL OR null bootstrap p>=0.05 OR max_year_share>=0.70. REJECT; catalog §B-3 academic-only candidate.

## Deferred Validity Markers
- D S2 Turtle anti-correlation: DEFERRED to Claude; use primary trade-list and daily-PnL parquet.
- E fib_reversal LIVE corr: DEFERRED to Claude/Render.
- F yfinance broker cross-check: DEFERRED to Claude.

## Rejected Alternative Variables
- failure_window expansion beyond 24 bars requires fresh pre-registration.
- ATR-based failure buffer would be a new strategy definition.
- Pair extension to GBPJPY requires full 12-year M5 cache.