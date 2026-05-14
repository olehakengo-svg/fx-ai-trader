# Phase 1b OANDA Retail-Contrarian Sentiment BT

## Header
- Run timestamp UTC: 2026-05-14T22:50:14.687593+00:00
- Pair set (14): EUR_USD, USD_JPY, GBP_USD, AUD_USD, USD_CAD, USD_CHF, NZD_USD, EUR_JPY, GBP_JPY, AUD_JPY, EUR_AUD, EUR_GBP, EUR_CHF, GBP_CHF
- Cell grid: 14 pairs x 12 thresholds x 4 holdings = 672
- m_used (N >= 20): 111
- alpha_cell: 0.00007440
- Sentiment source: `history:data/sentiment/oanda_labs_h4_history.parquet` (rows used: 8148)
- Window: last 97 days from now

## Top-Level Verdict
**NULL**

Joined rows by pair:
- EUR_USD: 394
- USD_JPY: 394
- GBP_USD: 394
- AUD_USD: 366
- USD_CAD: 394
- USD_CHF: 394
- NZD_USD: 394
- EUR_JPY: 388
- GBP_JPY: 366
- AUD_JPY: 394
- EUR_AUD: 394
- EUR_GBP: 394
- EUR_CHF: 394
- GBP_CHF: 394

## Survivor Table
No cells passed all survivor gates.

## Per-Pair Best Cell
| pair | direction | threshold | holding | N | WR | Wilson_lo | EV(p) | PF | survivor |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EUR_USD | LONG | 65 | 2 | 104 | 0.385 | 0.297 | -3.97 | 0.63 | NO |
| USD_JPY | LONG | 65 | 2 | 77 | 0.494 | 0.385 | -19.77 | 0.34 | NO |
| GBP_USD | LONG | 65 | 1 | 0 | 0.000 | 0.000 | 0.00 | 0.00 | NO |
| AUD_USD | LONG | 65 | 1 | 4 | 0.500 | 0.150 | 0.10 | 1.02 | NO |
| USD_CAD | LONG | 65 | 4 | 48 | 0.542 | 0.403 | -5.13 | 0.63 | NO |
| USD_CHF | SHORT | 35 | 12 | 382 | 0.445 | 0.396 | -5.39 | 0.75 | NO |
| NZD_USD | SHORT | 35 | 4 | 201 | 0.463 | 0.395 | -6.63 | 0.59 | NO |
| EUR_JPY | LONG | 75 | 12 | 14 | 0.857 | 0.601 | 38.38 | 53.17 | NO |
| GBP_JPY | LONG | 65 | 2 | 7 | 0.857 | 0.487 | 12.57 | 20.56 | NO |
| AUD_JPY | LONG | 65 | 1 | 0 | 0.000 | 0.000 | 0.00 | 0.00 | NO |
| EUR_AUD | SHORT | 25 | 2 | 6 | 0.833 | 0.436 | 1.20 | 1.17 | NO |
| EUR_GBP | LONG | 65 | 4 | 198 | 0.414 | 0.348 | -2.83 | 0.59 | NO |
| EUR_CHF | SHORT | 10 | 4 | 227 | 0.463 | 0.399 | -1.50 | 0.82 | NO |
| GBP_CHF | SHORT | 35 | 12 | 382 | 0.442 | 0.393 | -5.07 | 0.71 | NO |

## Failure Mode Analysis
- Median Wilson_lo across all cells: 0.000
- Median PF across all cells: 0.000
- Direction-correct cells (EV>0 and PF>1.0): 12 / 672
- Direction-correct but underpowered cells (N<20): 12 / 12
- Powered cells counted in Bonferroni denominator: 111
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
