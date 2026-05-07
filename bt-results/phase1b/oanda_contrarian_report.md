# Phase 1b OANDA Retail-Contrarian Sentiment BT

## Header
- Run timestamp UTC: 2026-05-07T12:49:11.298806+00:00
- Pair set: EUR_USD, USD_JPY, GBP_USD, EUR_JPY, GBP_JPY, EUR_GBP
- Cell grid: 6 pairs x 12 thresholds x 4 holdings = 288
- m_used (N >= 20): 19
- alpha_cell: 0.00017361
- Sentiment cache: `data/sentiment/oanda_labs_h4_90d.parquet`

## Top-Level Verdict
**NULL**

Joined rows by pair:
- EUR_USD: 262
- USD_JPY: 263
- GBP_USD: 267
- EUR_JPY: 292
- GBP_JPY: 292
- EUR_GBP: 248

## Survivor Table
No cells passed all survivor gates.

## Per-Pair Best Cell
| pair | direction | threshold | holding | N | WR | Wilson_lo | EV(p) | PF | survivor |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EUR_USD | LONG | 65 | 4 | 49 | 0.388 | 0.264 | -4.48 | 0.68 | NO |
| USD_JPY | LONG | 65 | 2 | 63 | 0.524 | 0.403 | -8.35 | 0.57 | NO |
| GBP_USD | LONG | 65 | 1 | 0 | 0.000 | 0.000 | 0.00 | 0.00 | NO |
| EUR_JPY | LONG | 70 | 1 | 24 | 0.708 | 0.508 | 5.57 | 1.93 | NO |
| GBP_JPY | LONG | 65 | 2 | 1 | 1.000 | 0.207 | 2.30 | inf | NO |
| EUR_GBP | LONG | 65 | 4 | 112 | 0.473 | 0.383 | -0.43 | 0.94 | NO |

## Failure Mode Analysis
- Median Wilson_lo across all cells: 0.000
- Median PF across all cells: 0.000
- Direction-correct cells (EV>0 and PF>1.0): 7 / 288
- Direction-correct but underpowered cells (N<20): 4 / 7
- Powered cells counted in Bonferroni denominator: 19
- Regime split counts: {'<=1/3 noise': 287, '2/3 weak': 1}
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
