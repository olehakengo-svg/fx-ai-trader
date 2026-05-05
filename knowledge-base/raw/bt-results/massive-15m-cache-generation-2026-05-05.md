# MASSIVE 15m Cache Generation - 2026-05-05

## Summary

Task: generate 15m parquet cache for W4-Redesign pairs.

Environment result:
- `MASSIVE_API_KEY`: absent from process environment.
- `.env` `MASSIVE_API_KEY`: absent.
- Direct MASSIVE API generation was not possible in this run.
- Fallback resample was used only where local 5m parquet existed.

## Existing Cache State Before Generation

`data/cache/massive/*_15m.parquet` was empty before this task.

Available 5m source parquet:

| Pair | Source | Rows | Start | End |
|---|---:|---:|---|---|
| USD_JPY | `data/cache/massive/USD_JPY_5m.parquet` | 903,828 | 2014-01-02 04:55 UTC | 2026-04-30 23:55 UTC |
| GBP_JPY | `data/cache/massive/GBP_JPY_5m.parquet` | 925,109 | 2014-01-02 04:55 UTC | 2026-04-30 23:55 UTC |

No 5m source parquet existed for `EUR_USD`, `GBP_USD`, `EUR_JPY`, `EUR_GBP`, or `AUD_USD`.

## Generated Files

Generation method: 5m -> 15m resample fallback.

Resample rule:
- `resample("15min", label="right", closed="right")`
- `open`: first
- `high`: max
- `low`: min
- `close`: last
- `volume`: sum
- `n_transactions`: sum
- `vwap`: last 5m bar value in the 15m bucket

Schema was kept aligned with existing local MASSIVE cache files: lowercase `open`, `high`, `low`, `close`, `volume`, `vwap`, `n_transactions`. Runtime parquet fallback normalizes these to `Open`, `High`, `Low`, `Close`, `Volume`.

| Pair | Output | Method | Rows | Start | End | Span |
|---|---|---|---:|---|---|---:|
| USD_JPY | `data/cache/massive/USD_JPY_15m.parquet` | resample fallback | 302,916 | 2014-01-02 05:00 UTC | 2026-05-01 00:00 UTC | 4,501 days |
| GBP_JPY | `data/cache/massive/GBP_JPY_15m.parquet` | resample fallback | 316,841 | 2014-01-02 05:00 UTC | 2026-05-01 00:00 UTC | 4,501 days |

Both generated files meet the minimum acceptance period (`>= 1095` days) and the ideal period target (`4000+` days).

## Missing Files

These files could not be generated in this environment because `MASSIVE_API_KEY` was absent and there was no corresponding local 5m parquet source to resample:

| Pair | Required Output | Status |
|---|---|---|
| EUR_USD | `data/cache/massive/EUR_USD_15m.parquet` | missing |
| GBP_USD | `data/cache/massive/GBP_USD_15m.parquet` | missing |
| EUR_JPY | `data/cache/massive/EUR_JPY_15m.parquet` | missing |
| EUR_GBP | `data/cache/massive/EUR_GBP_15m.parquet` | missing |
| AUD_USD | `data/cache/massive/AUD_USD_15m.parquet` | missing |

Additional compatibility note: current `modules.data.fetch_ohlcv_massive` and `tools.bt_data_cache.PAIRS` mappings cover the six existing MASSIVE pairs but do not include `AUD_USD` / `AUDUSD=X`. Even with `MASSIVE_API_KEY` configured, `AUD_USD` needs mapping support before direct generation through the existing code path.

## API vs Resample Sanity Check

Direct API vs resample equivalence could not be checked because MASSIVE API access was unavailable.

Local saved-file sanity check:
- `USD_JPY_15m.parquet`: generated from `USD_JPY_5m.parquet`, 302,916 bars, 4,501-day span.
- `GBP_JPY_15m.parquet`: generated from `GBP_JPY_5m.parquet`, 316,841 bars, 4,501-day span.

Warning: resampled 15m bars may not be fully equivalent to production MASSIVE 15m bars if provider bar boundaries, aggregation rules, `vwap`, or transaction-count semantics differ. Direct MASSIVE API regeneration remains preferred.

## BT Verification

`BT_MODE=1` parquet read path was verified for `USDJPY=X` / `15m`:

| Check | Result |
|---|---|
| `fetch_ohlcv("USDJPY=X", period="30d", interval="15m")` | passed |
| Rows returned | 2,115 |
| Source marker | `massive-parquet` |
| Returned range | 2026-04-01 00:00 UTC to 2026-05-01 00:00 UTC |
| Returned columns | `Open`, `High`, `Low`, `Close`, `Volume`, `vwap`, `n_transactions` |

`run_daytrade_backtest("USDJPY=X", lookback_days=30, interval="15m")` also completed:

| Metric | Value |
|---|---:|
| Trades | 247 |
| Win rate | 61.9 |

Related tests:

```text
.venv/bin/python3 -m pytest tests/test_fetch_ohlcv_bt_mode.py tests/test_bt_data_loader_parquet_fallback.py tests/test_doji_breakout_redesign.py
8 passed
```

## Next Steps

1. Configure `MASSIVE_API_KEY` in the runtime environment or `.env`.
2. Add `AUD_USD` / `AUDUSD=X` mapping support if `AUD_USD_15m.parquet` is still required through `modules.data.fetch_ohlcv_massive` and `tools.bt_data_cache`.
3. Generate the remaining 15m files directly from MASSIVE API.
4. Re-run API-vs-resample comparison for `USD_JPY` and `GBP_JPY` once direct 15m API data is available.
