# Phase 1b OANDA Retail-Contrarian Sentiment BT

## Header
- Run timestamp UTC: 2026-05-07T13:26:14.455882+00:00
- Pair set: EUR_USD, USD_JPY, GBP_USD, EUR_JPY, GBP_JPY, EUR_GBP
- Cell grid: 6 pairs x 12 thresholds x 4 holdings = 288
- m_used (N >= 20): 20
- alpha_cell: 0.00017361
- Sentiment cache: `data/sentiment/oanda_labs_h4_90d.parquet`

## Top-Level Verdict
**NULL**

Joined rows by pair:
- EUR_USD: 397
- USD_JPY: 397
- GBP_USD: 397
- EUR_JPY: 391
- GBP_JPY: 369
- EUR_GBP: 397

## Survivor Table
No cells passed all survivor gates.

## Per-Pair Best Cell
| pair | direction | threshold | holding | N | WR | Wilson_lo | EV(p) | PF | survivor |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EUR_USD | LONG | 65 | 2 | 107 | 0.393 | 0.305 | -3.85 | 0.64 | NO |
| USD_JPY | LONG | 65 | 2 | 77 | 0.494 | 0.385 | -19.77 | 0.34 | NO |
| GBP_USD | LONG | 65 | 1 | 0 | 0.000 | 0.000 | 0.00 | 0.00 | NO |
| EUR_JPY | LONG | 75 | 12 | 14 | 0.857 | 0.601 | 38.38 | 53.17 | NO |
| GBP_JPY | LONG | 65 | 2 | 7 | 0.857 | 0.487 | 12.57 | 20.56 | NO |
| EUR_GBP | LONG | 65 | 4 | 201 | 0.423 | 0.357 | -2.50 | 0.63 | NO |

## Failure Mode Analysis
- Median Wilson_lo across all cells: 0.000
- Median PF across all cells: 0.000
- Direction-correct cells (EV>0 and PF>1.0): 7 / 288
- Direction-correct but underpowered cells (N<20): 7 / 7
- Powered cells counted in Bonferroni denominator: 20
- Regime split counts: {'<=1/3 noise': 288}
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
