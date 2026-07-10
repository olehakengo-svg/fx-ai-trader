# Phase 1b OANDA Retail-Contrarian Sentiment BT

## Header
- Run timestamp UTC: 2026-07-09T21:53:57.171294+00:00
- Pair set (14): EUR_USD, USD_JPY, GBP_USD, AUD_USD, USD_CAD, USD_CHF, NZD_USD, EUR_JPY, GBP_JPY, AUD_JPY, EUR_AUD, EUR_GBP, EUR_CHF, GBP_CHF
- Cell grid: 14 pairs x 12 thresholds x 4 holdings = 672
- m_used (N >= 20): 48
- alpha_cell: 0.00007440
- Sentiment source: `history:data/sentiment/oanda_labs_h4_history.parquet` (rows used: 12858)
- Window: last 153 days from now

## Top-Level Verdict
**NULL**

Skipped pairs:
- EUR_USD: incompatible merge keys [0] datetime64[ms, UTC] and datetime64[ns, UTC], must be the same type
- USD_JPY: incompatible merge keys [0] datetime64[ms, UTC] and datetime64[ns, UTC], must be the same type
- GBP_USD: incompatible merge keys [0] datetime64[ms, UTC] and datetime64[ns, UTC], must be the same type
- AUD_USD: incompatible merge keys [0] datetime64[ms, UTC] and datetime64[ns, UTC], must be the same type
- USD_CAD: incompatible merge keys [0] datetime64[ms, UTC] and datetime64[ns, UTC], must be the same type
- USD_CHF: incompatible merge keys [0] datetime64[ms, UTC] and datetime64[ns, UTC], must be the same type
- NZD_USD: incompatible merge keys [0] datetime64[ms, UTC] and datetime64[ns, UTC], must be the same type
- EUR_JPY: incompatible merge keys [0] datetime64[ms, UTC] and datetime64[ns, UTC], must be the same type
- GBP_JPY: incompatible merge keys [0] datetime64[ms, UTC] and datetime64[ns, UTC], must be the same type
- AUD_JPY: incompatible merge keys [0] datetime64[ms, UTC] and datetime64[ns, UTC], must be the same type
- EUR_AUD: incompatible merge keys [0] datetime64[ms, UTC] and datetime64[ns, UTC], must be the same type
- EUR_GBP: incompatible merge keys [0] datetime64[ms, UTC] and datetime64[ns, UTC], must be the same type

Joined rows by pair:
- EUR_USD: 0
- USD_JPY: 0
- GBP_USD: 0
- AUD_USD: 0
- USD_CAD: 0
- USD_CHF: 0
- NZD_USD: 0
- EUR_JPY: 0
- GBP_JPY: 0
- AUD_JPY: 0
- EUR_AUD: 0
- EUR_GBP: 0
- EUR_CHF: 395
- GBP_CHF: 395

## Survivor Table
No cells passed all survivor gates.

## Per-Pair Best Cell
| pair | direction | threshold | holding | N | WR | Wilson_lo | EV(p) | PF | survivor |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EUR_USD | LONG | 65 | 1 | 0 | 0.000 | 0.000 | 0.00 | 0.00 | NO |
| USD_JPY | LONG | 65 | 1 | 0 | 0.000 | 0.000 | 0.00 | 0.00 | NO |
| GBP_USD | LONG | 65 | 1 | 0 | 0.000 | 0.000 | 0.00 | 0.00 | NO |
| AUD_USD | LONG | 65 | 1 | 0 | 0.000 | 0.000 | 0.00 | 0.00 | NO |
| USD_CAD | LONG | 65 | 1 | 0 | 0.000 | 0.000 | 0.00 | 0.00 | NO |
| USD_CHF | LONG | 65 | 1 | 0 | 0.000 | 0.000 | 0.00 | 0.00 | NO |
| NZD_USD | LONG | 65 | 1 | 0 | 0.000 | 0.000 | 0.00 | 0.00 | NO |
| EUR_JPY | LONG | 65 | 1 | 0 | 0.000 | 0.000 | 0.00 | 0.00 | NO |
| GBP_JPY | LONG | 65 | 1 | 0 | 0.000 | 0.000 | 0.00 | 0.00 | NO |
| AUD_JPY | LONG | 65 | 1 | 0 | 0.000 | 0.000 | 0.00 | 0.00 | NO |
| EUR_AUD | LONG | 65 | 1 | 0 | 0.000 | 0.000 | 0.00 | 0.00 | NO |
| EUR_GBP | LONG | 65 | 1 | 0 | 0.000 | 0.000 | 0.00 | 0.00 | NO |
| EUR_CHF | SHORT | 10 | 4 | 228 | 0.465 | 0.401 | -1.44 | 0.83 | NO |
| GBP_CHF | SHORT | 35 | 12 | 383 | 0.444 | 0.395 | -4.86 | 0.72 | NO |

## Failure Mode Analysis
- Median Wilson_lo across all cells: 0.000
- Median PF across all cells: 0.000
- Direction-correct cells (EV>0 and PF>1.0): 0 / 672
- Direction-correct but underpowered cells (N<20): 0 / 0
- Powered cells counted in Bonferroni denominator: 48
- Regime split counts: {'<=1/3 noise': 662, '2/3 weak': 10}
- Interpretation: rejection is direction-led in this 90d slice; the raw contrarian sign is not consistently positive.

## Where To Look Next
- Extend the sentiment history by cron polling; the current OANDA Labs endpoint only exposes the most recent 90 days.
- Test longer H4 holds beyond 12 bars after more history exists; the current run is deliberately conservative.
- Probe thresholds beyond 90/10 only after enough observations exist to avoid sparse-cell overfitting.
- Test cross-pair sentiment spreads as a separate pre-registered study rather than widening this grid post hoc.

## Honest Caveats
- The available sentiment window is short; OANDA Labs history starts around 2026-02-06 in this feed.
- MASSIVE cache coverage can be shorter than the sentiment feed for some pairs, so the effective BT window is the joined intersection.
- This is a sanity BT only; any survivor still needs shadow validation before strategy integration.
