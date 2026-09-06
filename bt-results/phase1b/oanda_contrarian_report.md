# Phase 1b OANDA Retail-Contrarian Sentiment BT

## Header
- Run timestamp UTC: 2026-09-06T01:51:57.355769+00:00
- Pair set (14): EUR_USD, USD_JPY, GBP_USD, AUD_USD, USD_CAD, USD_CHF, NZD_USD, EUR_JPY, GBP_JPY, AUD_JPY, EUR_AUD, EUR_GBP, EUR_CHF, GBP_CHF
- Cell grid: 14 pairs x 12 thresholds x 4 holdings = 672
- m_used (N >= 20): 117
- alpha_cell: 0.00007440
- Sentiment source: `history:data/sentiment/oanda_labs_h4_history.parquet` (rows used: 17710)
- Window: last 211 days from now

## Top-Level Verdict
**NULL**

Joined rows by pair:
- EUR_USD: 419
- USD_JPY: 425
- GBP_USD: 425
- AUD_USD: 391
- USD_CAD: 425
- USD_CHF: 421
- NZD_USD: 422
- EUR_JPY: 413
- GBP_JPY: 391
- AUD_JPY: 421
- EUR_AUD: 419
- EUR_GBP: 419
- EUR_CHF: 394
- GBP_CHF: 394

## Survivor Table
No cells passed all survivor gates.

## Per-Pair Best Cell
| pair | direction | threshold | holding | N | WR | Wilson_lo | EV(p) | PF | survivor |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EUR_USD | LONG | 65 | 2 | 114 | 0.360 | 0.277 | -4.35 | 0.60 | NO |
| USD_JPY | LONG | 65 | 2 | 78 | 0.487 | 0.379 | -19.41 | 0.35 | NO |
| GBP_USD | LONG | 65 | 1 | 0 | 0.000 | 0.000 | 0.00 | 0.00 | NO |
| AUD_USD | LONG | 65 | 12 | 5 | 0.600 | 0.231 | -1.36 | 0.87 | NO |
| USD_CAD | LONG | 65 | 4 | 48 | 0.542 | 0.403 | -5.18 | 0.63 | NO |
| USD_CHF | SHORT | 35 | 12 | 409 | 0.433 | 0.386 | -6.20 | 0.72 | NO |
| NZD_USD | SHORT | 35 | 4 | 201 | 0.453 | 0.385 | -6.66 | 0.59 | NO |
| EUR_JPY | LONG | 75 | 12 | 14 | 0.857 | 0.601 | 38.18 | 47.89 | NO |
| GBP_JPY | LONG | 65 | 2 | 7 | 0.857 | 0.487 | 12.36 | 15.18 | NO |
| AUD_JPY | LONG | 65 | 1 | 0 | 0.000 | 0.000 | 0.00 | 0.00 | NO |
| EUR_AUD | SHORT | 30 | 12 | 22 | 0.682 | 0.473 | 34.89 | 3.19 | NO |
| EUR_GBP | LONG | 65 | 4 | 204 | 0.407 | 0.342 | -3.00 | 0.57 | NO |
| EUR_CHF | SHORT | 10 | 4 | 227 | 0.463 | 0.399 | -1.50 | 0.82 | NO |
| GBP_CHF | SHORT | 35 | 12 | 382 | 0.442 | 0.393 | -5.07 | 0.71 | NO |

## Failure Mode Analysis
- Median Wilson_lo across all cells: 0.000
- Median PF across all cells: 0.000
- Direction-correct cells (EV>0 and PF>1.0): 8 / 672
- Direction-correct but underpowered cells (N<20): 7 / 8
- Powered cells counted in Bonferroni denominator: 117
- Regime split counts: {'<=1/3 noise': 661, '2/3 weak': 11}
- Interpretation: some cells point the right way but are mostly underpowered at the pre-registered thresholds.

## Where To Look Next
- Extend the sentiment history by cron polling; the current OANDA Labs endpoint only exposes the most recent 90 days.
- Test longer H4 holds beyond 12 bars after more history exists; the current run is deliberately conservative.
- Probe thresholds beyond 90/10 only after enough observations exist to avoid sparse-cell overfitting.
- Test cross-pair sentiment spreads as a separate pre-registered study rather than widening this grid post hoc.

## Honest Caveats
- The available sentiment window is short; OANDA Labs history starts around 2026-02-06 in this feed.
- MASSIVE cache coverage can be shorter than the sentiment feed for some pairs, so the effective BT window is the joined intersection.
- This is a sanity BT only; any survivor still needs shadow validation before strategy integration.
