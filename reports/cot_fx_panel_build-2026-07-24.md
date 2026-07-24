# W1-F2: CFTC COT FX Weekly Panel Build — 2026-07-24

**Type: data ingest ONLY.** This line is QUEUED for pre-registered analysis. No edge
analysis, no IC computation, no forward-return joins were performed — explore degrees
of freedom are preserved for the pre-reg.

## Source

- CFTC Commitments of Traders, **legacy format, futures only**, annual compressed files
- URL: `https://www.cftc.gov/files/dea/history/deacot{year}.zip` (member `annual.txt`)
- Years fetched via curl: **2010–2026, all 17 succeeded** (2026 partial year)
- Raw zips cached: `data/external/cot_raw/deacot{year}.zip`

## Outputs

- Builder: `tools/build_cot_panel.py` (no module-top side effects; re-runnable, cached downloads, `--force-download` to refresh)
- Panel: `data/external/cot_fx_panel.parquet` (193,426 bytes, 5,178 rows)
- Schema: `report_date, currency, noncomm_long, noncomm_short, noncomm_net, open_interest, net_pct_oi`
- `noncomm_net = noncomm_long - noncomm_short`; `net_pct_oi = 100 * noncomm_net / open_interest`

Markets matched by stable **CFTC Contract Market Code** (names drift across years), with a
market-name sanity assertion per currency:

| Code | Currency | Market |
|---|---|---|
| 099741 | EUR | EURO FX - CME |
| 097741 | JPY | JAPANESE YEN - CME |
| 096742 | GBP | BRITISH POUND - CME |
| 232741 | AUD | AUSTRALIAN DOLLAR - CME |
| 090741 | CAD | CANADIAN DOLLAR - CME |
| 092741 | CHF | SWISS FRANC - CME |

## Validation

| Metric | Value |
|---|---|
| Rows total | 5,178 |
| Date span | 2010-01-05 .. 2026-07-14 |
| Weeks per currency | 863 (identical for all 6: AUD/CAD/CHF/EUR/GBP/JPY) |
| `net_pct_oi` NaN rows | 0 |
| Duplicate (date, currency) rows | 0 |
| Max inter-report gap | 8 days, every currency (holiday-shifted releases only; zero gaps > 14d) |

### noncomm_net range per currency (contracts)

| Currency | min | max |
|---|---:|---:|
| AUD | -107,538 | 103,376 |
| CAD | -196,263 | 111,881 |
| CHF | -49,793 | 27,640 |
| EUR | -226,560 | 211,752 |
| GBP | -107,844 | 142,183 |
| JPY | -184,223 | 179,212 |

### Spot-check: JPY record net short area (2024-04) — PASS

Expectation: strongly negative net and net_pct_oi (threshold < -30%).

| report_date | noncomm_net | open_interest | net_pct_oi |
|---|---:|---:|---:|
| 2024-04-02 | -143,230 | 316,809 | -45.2% |
| 2024-04-09 | -162,151 | 324,479 | -50.0% |
| 2024-04-16 | -165,619 | 331,110 | -50.0% |
| 2024-04-23 | -179,919 | 336,167 | **-53.5%** |
| 2024-04-30 | -168,388 | 334,848 | -50.3% |

All-time (in-panel) JPY record net short: **2024-07-02, -184,223 contracts (-52.7% of OI)** —
consistent with the well-documented 2024 yen-carry spec positioning extreme immediately
before the July–August 2024 unwind.

### Latest week in panel (2026-07-14)

| Currency | net_pct_oi |
|---|---:|
| EUR | -1.6% |
| JPY | -30.9% |
| GBP | -26.9% |
| AUD | -14.7% |
| CAD | -47.8% |
| CHF | -34.1% |

## Caveats (binding for the future pre-reg)

1. **Publication lag / lookahead**: `report_date` is the CFTC "as of" Tuesday; public release
   is typically **Friday ~15:30 ET (3-day lag)**. Any analysis MUST align signals to the
   release timestamp (report_date + 3 days, conservatively + 4), never to report_date itself.
2. 2026 is a partial year (28 weeks through 2026-07-14).
3. Legacy format is **futures only** (options excluded); noncommercial = large-speculator proxy.
4. `net_pct_oi` denominator is total OI across all trader categories.
5. No MFE/MAE / horizon / bootstrap statistics in this report by design — those belong to the
   pre-registered analysis phase (W1 queue).
