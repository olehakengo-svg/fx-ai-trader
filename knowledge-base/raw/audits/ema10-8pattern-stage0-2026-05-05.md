# EMA10 x M15 x 4-Pattern Pullback Stage 0 (2026-05-05)

## Verdict

**Verdict**: FAIL

| Gate | Pass | Observed |
|---|---:|---:|
| PF >= 1.10 | FAIL | 0.2835 |
| Wilson_lo_95 >= 0.50 | FAIL | 0.2593 |
| N >= 150 | PASS | 45080 |
| profit_year_concentration < 0.55 | FAIL | 1.0000 |
| EV_pip_per_trade > 0 | FAIL | -4.4038 |
| data missing_pct <= 2% | FAIL | 0.0295 |

Fail reasons: PF < 1.10, Wilson_lo_95 < 0.50, profit_year_concentration >= 0.55, EV_pip_per_trade <= 0, data_quality.missing_pct > 0.02

## Primary Cell Metrics

| Metric | Value |
|---|---:|
| n | 45080 |
| wr | 0.263398 |
| wilson_lo_95 | 0.259337 |
| pf | 0.283520 |
| ev_pip_per_trade | -4.403784 |
| avg_rr | 0.787667 |
| max_dd_pip | 198544.939846 |
| max_dd_pct | 19.854494 |
| sharpe | -6.946315 |
| profit_year_concentration | 1.000000 |

## Yearly Breakdown

| Year | N | PF | EV pip |
|---:|---:|---:|---:|
| 2014 | 3541 | 0.2055 | -4.2632 |
| 2015 | 3667 | 0.2534 | -4.5191 |
| 2016 | 3709 | 0.3169 | -4.6320 |
| 2017 | 3639 | 0.2401 | -4.6732 |
| 2018 | 3762 | 0.1782 | -4.4635 |
| 2019 | 3462 | 0.1380 | -4.4120 |
| 2020 | 3336 | 0.2224 | -4.0812 |
| 2021 | 4022 | 0.1576 | -4.1271 |
| 2022 | 3791 | 0.3713 | -4.4972 |
| 2023 | 3604 | 0.3846 | -4.1533 |
| 2024 | 3603 | 0.3904 | -4.3625 |
| 2025 | 3670 | 0.3847 | -4.5570 |
| 2026 | 1274 | 0.3092 | -4.6536 |

## Data Quality

- Source: `data/cache/massive/USD_JPY_5m.parquet`
- Expected M15 bars after weekend filter: 308717
- Actual M15 bars after weekend filter: 299622
- Missing pct: 0.029461
- Weekend filter applied: True
- Resample method: `M5 closed=left label=left -> M15`

## Equity Curve

```text
*
*******
*************
********************
**************************
********************************
***************************************
**********************************************
****************************************************
***********************************************************
*****************************************************************
************************************************************************
```

## Sample Trade Ledger

| Slice | Side | Pattern | Signal UTC | Entry UTC | Exit UTC | Entry | Exit | SL | TP | PnL pip | Reason | OHLC exit |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|---|---|
| first | short | S3_bearish_engulfing | 2014-01-02 05:30:00+00:00 | 2014-01-02 05:45:00+00:00 | 2014-01-02 06:00:00+00:00 | 105.255 | 105.312 | 105.308 | 105.176 | -5.70 | trend_cross | O=105.292 H=105.309 L=105.278 C=105.291 |
| first | long | L2_bear_hammer | 2014-01-02 06:00:00+00:00 | 2014-01-02 06:15:00+00:00 | 2014-01-02 06:30:00+00:00 | 105.311 | 105.273 | 105.270 | 105.311 | -3.80 | trend_cross | O=105.293 H=105.302 L=105.270 C=105.282 |
| first | long | L3_bullish_engulfing | 2014-01-02 06:45:00+00:00 | 2014-01-02 07:00:00+00:00 | 2014-01-02 10:30:00+00:00 | 105.334 | 105.308 | 105.270 | 105.413 | -2.60 | trend_cross | O=105.328 H=105.351 L=105.313 C=105.332 |
| first | short | S2_bull_hammer | 2014-01-02 10:30:00+00:00 | 2014-01-02 10:45:00+00:00 | 2014-01-02 11:00:00+00:00 | 105.312 | 105.400 | 105.402 | 105.303 | -8.80 | trend_cross | O=105.380 H=105.432 L=105.367 C=105.409 |
| first | long | L2_bear_hammer | 2014-01-02 11:45:00+00:00 | 2014-01-02 12:00:00+00:00 | 2014-01-02 13:00:00+00:00 | 105.405 | 105.353 | 105.313 | 105.432 | -5.20 | trend_cross | O=105.373 H=105.383 L=105.281 C=105.287 |
| last | long | L4_bullish_harami_breakout | 2026-04-30 16:15:00+00:00 | 2026-04-30 16:30:00+00:00 | 2026-04-30 16:45:00+00:00 | 156.730 | 156.596 | 156.502 | 156.959 | -13.40 | trend_cross | O=156.616 H=156.651 L=156.543 C=156.576 |
| last | short | S3_bearish_engulfing | 2026-04-30 17:15:00+00:00 | 2026-04-30 17:30:00+00:00 | 2026-04-30 17:30:00+00:00 | 156.501 | 156.469 | 156.959 | 156.449 | 3.20 | tp | O=156.521 H=156.525 L=156.419 C=156.475 |
| last | long | L4_bullish_harami_breakout | 2026-04-30 19:15:00+00:00 | 2026-04-30 19:30:00+00:00 | 2026-04-30 19:45:00+00:00 | 156.498 | 156.431 | 156.303 | 156.705 | -6.70 | trend_cross | O=156.451 H=156.564 L=156.439 C=156.562 |
| last | long | L4_bullish_harami_breakout | 2026-04-30 19:45:00+00:00 | 2026-04-30 20:00:00+00:00 | 2026-04-30 23:00:00+00:00 | 156.580 | 156.752 | 156.303 | 156.772 | 17.16 | tp | O=156.649 H=156.776 L=156.633 C=156.764 |
| last | long | L3_bullish_engulfing | 2026-04-30 23:30:00+00:00 | 2026-04-30 23:45:00+00:00 | 2026-04-30 23:45:00+00:00 | 156.906 | 156.958 | 156.633 | 157.109 | 5.20 | eod | O=156.886 H=157.019 L=156.883 C=156.978 |

## Sanity Checks

### Pattern Trigger Breakdown

| Pattern | Count |
|---|---:|
| L1 | 6070 |
| L2 | 4148 |
| L3 | 9082 |
| L4 | 3988 |
| S1 | 5013 |
| S2 | 3408 |
| S3 | 9884 |
| S4 | 3487 |

### Exit Breakdown

| Exit reason | Count | Ratio |
|---|---:|---:|
| eod | 1 | 0.0000 |
| sl | 772 | 0.0171 |
| tp | 15985 | 0.3546 |
| trend_cross | 28322 | 0.6283 |

- Trend cross forced close ratio: 0.6283
- Pullback touch count: 105797
- Long confirmed count: 23288
- Short confirmed count: 21792

## Reproducibility

```bash
python tools/bt/ema10_8pattern_pullback.py --stage 0 --pair USD_JPY --start 2014-01-02 --end 2026-04-30 --pattern-set all_four --sl-mult 1.0 --tp-lookback 20 --spread-pip 1.5 --slippage-pip 0.5 --output-md knowledge-base/raw/audits/ema10-8pattern-stage0-2026-05-05.md --output-json knowledge-base/raw/audits/ema10-8pattern-stage0-2026-05-05.json
```

- Git SHA: `9ccf54b`

## Open Questions

- Pre-reg named cache `data/cache/massive/USD_JPY_5m_2014_2026.parquet` was absent; used matching real cache `data/cache/massive/USD_JPY_5m.parquet`.
