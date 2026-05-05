# BT MASSIVE Cache Default Patch Proposal (2026-05-05)

## Problem

Production BT reaches Yahoo/yfinance during 365d daytrade backtests, even though the repo has MASSIVE-derived local parquet cache as the intended BT data source.

The standard path is:

```text
tools/bt_365d_runner.py:63
  -> app.run_daytrade_backtest(symbol, lookback_days=365, interval="15m")
     -> app.py:6128 fetch_ohlcv(symbol, period="365d", interval="15m")
        -> modules/data.py:679-684 live Massive API only if MASSIVE_API_KEY is set
        -> modules/data.py:697-702 OANDA only if OANDA_TOKEN is set
        -> modules/data.py:715-720 TwelveData only if TWELVEDATA_API_KEY is set
        -> modules/data.py:738-740 yfinance _fetch_raw(...)
        -> modules/data.py:752-755 local parquet fallback
```

The actual Yahoo call is:

```text
modules/data.py:101-109 _fetch_raw()
```

The 365d daytrade BT entrypoint is:

```text
app.py:6109-6128 run_daytrade_backtest()
```

The app/API wrapper also routes daytrade mode through the same function:

```text
app.py:11346-11351 /api/backtest daytrade mode
app.py:11513-11520 _run_bt_by_mode()
```

## Root Cause

There are two separate issues.

1. `fetch_ohlcv()` treats local parquet as the final fallback, not the BT default.
2. The current checkout only has 5m parquet files:

```text
data/cache/massive/USD_JPY_5m.parquet
data/cache/massive/GBP_JPY_5m.parquet
```

For `interval="15m"`, `_load_parquet_cache_fallback()` looks for:

```text
data/cache/massive/USD_JPY_15m.parquet
```

That file is absent, so a strict daytrade 15m BT cannot use the official `{PAIR}_{TF}` cache until the 15m cache is materialized.

The W4P1 focused runner used MASSIVE-derived 5m data and resampled to 15m. That is useful as a diagnostic, but it is not the same as the production BT path.

## Fix Direction

Make BT mode use local MASSIVE parquet cache first.

Policy:

- In `BT_MODE=1`, try `data/cache/massive/{PAIR}_{TF}.parquet` before network providers.
- If the exact TF cache is missing, fail clearly for verdict-eligible BT.
- Do not silently fall through to Yahoo for W4 verdicts.
- Keep Yahoo/yfinance only as non-BT fallback or explicit development fallback.

## Patch Sketch

Target file:

```text
modules/data.py
```

Patch concept:

```diff
diff --git a/modules/data.py b/modules/data.py
--- a/modules/data.py
+++ b/modules/data.py
@@
 def fetch_ohlcv(symbol="USDJPY=X", period="5d", interval="1m") -> pd.DataFrame:
@@
     days = _period_to_days(period)
@@
     min_bars = max(100, expected * 0.30)
+
+    # -- BT mode: official MASSIVE parquet cache is the primary data source --
+    if os.environ.get("BT_MODE") == "1":
+        parquet_df, parquet_ts = _load_parquet_cache_fallback(
+            symbol, interval, days, min_bars
+        )
+        if parquet_df is not None:
+            _last_data_source[interval] = "massive-parquet"
+            print(
+                f"[massive-parquet/{interval}] {symbol} {len(parquet_df)} bars "
+                f"(cache_ts={parquet_ts.isoformat()})"
+            )
+            with _cache_lock:
+                _data_cache[key] = (parquet_df, now)
+            return parquet_df.copy()
+
+        if os.environ.get("BT_REQUIRE_MASSIVE_CACHE", "1") == "1":
+            raise ValueError(
+                f"BT requires local MASSIVE parquet cache for {symbol}/{interval}; "
+                f"expected data/cache/massive/{{PAIR}}_{interval}.parquet"
+            )
 
     # -- (0) Massive API 最優先: 全FXペア × 全TF (有料契約、高品質データ) --
```

Optional non-strict behavior:

```text
BT_REQUIRE_MASSIVE_CACHE=0
```

Only this opt-out should allow network fallback in BT mode.

## Data Prep Required Before Patch Use

Materialize exact TF caches for verdict runs:

```text
data/cache/massive/USD_JPY_15m.parquet
data/cache/massive/GBP_JPY_15m.parquet
```

Preferred source:

```text
tools/bt_data_cache.py
modules/data.py:fetch_ohlcv_massive
```

If 15m is derived from 5m cache rather than fetched directly, the resulting file must still be written as the official cache artifact and documented as MASSIVE-derived 5m-to-15m materialization. Verdict runners should then read the 15m file, not resample internally.

## Verification Plan

1. Add a unit test that sets `BT_MODE=1` and asserts `fetch_ohlcv("USDJPY=X", "365d", "15m")` reads parquet before `_fetch_raw`.
2. Add a unit test that sets `BT_MODE=1`, `BT_REQUIRE_MASSIVE_CACHE=1`, removes/mocks the exact TF cache, and asserts a clear `ValueError`.
3. Run:

```text
NO_AUTOSTART=1 BT_MODE=1 .venv/bin/pytest -q tests/test_bt_data_loader_parquet_fallback.py
```

4. Run a small smoke test with an available exact TF cache.

## Rule 3 Candidate

This is a structural BT data-path bug:

- It can change W4 verdicts by changing the broker/source/time coverage.
- It exposes Yahoo intraday limits in a path that should be source-stable.
- It creates non-reproducible behavior depending on env vars and network availability.

Recommended priority: Rule 3, surgical patch after exact TF cache materialization is defined.

## Codex Self-Review

- The patch proposal does not remove live data paths for production UI use.
- It changes only `BT_MODE=1` semantics by default.
- It fails closed when the exact official TF cache is absent, preventing accidental Yahoo-backed verdicts.
- It does not implement ad hoc resampling in production BT; cache materialization remains a separate data-prep step.
