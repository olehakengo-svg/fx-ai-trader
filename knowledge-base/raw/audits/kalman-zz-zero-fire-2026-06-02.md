# Kalman D7 / ZZ Pivot v60 SR Zero-Fire Root Cause Audit

Date: 2026-06-02  
Rule: R3  
Scope: `kalman_d7_trail_atr`, `zz_pivot_v60_sr`, `zz_pivot_v60_sr_lo`

## Executive Summary

- `kalman_d7_*`: post-live window has **0 filter-pass bars**. Root cause is filter rejection, mainly no new Perfect Order UP transition after the deploy window. Verdict: `MARKET_WAIT`.
- `zz_pivot_v60_sr*`: strategy filters produced **6 pass bars since 2026-05-28**, but production audit has only **1 row**, and that row is `skipped/shadow_tracking`, not OANDA `sent/filled`. Verdict: `SILENT_DROP_V3`.
- Patch added: diagnostic-only `[SENTINEL_BLOCK_DIAG]` logs for Kalman/ZZ early blocks and candidate-built shadow downgrades. No filter threshold, shadow-first, or lot-size behavior was changed.

## Step 1: oanda_audit / shadow_audit Enumeration

Direct shell/SQLite status:

```text
$ ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 srv-d6va1of5r7bs73en10vg@ssh.oregon.render.com 'hostname; pwd; find /var/data -name "*.db" 2>/dev/null; env | grep -iE "kalman|zz|d7|live_enable|oanda|shadow" | sort'
/bin/sh: 1: ssh: not found
```

This Codex runner is `srv-d7rjnfn7f7vs73d1e6ig`; it has no `ssh` client and no mounted user private key. `apt-get install openssh-client sqlite3` is blocked by non-root permissions. Therefore direct `/var/data/*.db` SQL and parallel table enumeration could not be executed from this runner.

Production API fallback used:

```text
$ curl -sS --max-time 30 'https://fx-ai-trader.onrender.com/api/oanda/audit?limit=10000' -o /tmp/oanda_audit.json -w '%{http_code} %{size_download}\n'
200 2946403

total_api 7283 rows_returned 7283
match_count_returned 1
counter {('zz_pivot_v60_sr', 'skipped', False): 1}
```

API-equivalent grouped output:

```text
API equivalent: since 2026-05-28
('zz_pivot_v60_sr', 'skipped', False) 1 2026-05-28T12:08:46.076445+00:00 2026-05-28T12:08:46.076445+00:00
API equivalent: all-time
('zz_pivot_v60_sr', 'skipped', False) 1 2026-05-28T12:08:46.076445+00:00 2026-05-28T12:08:46.076445+00:00
```

Matched production row:

```json
{"block_reason": "shadow_tracking", "bridge_status": "skipped", "created_at": "2026-05-28 12:08:46", "demo_trade_id": "f086d522-6d5", "direction": "SELL", "entry_type": "zz_pivot_v60_sr", "id": 6744, "instrument": "EUR_USD", "is_live": false, "oanda_trade_id": "", "sr_days_span": null, "sr_distance_atr": null, "sr_is_strong": null, "sr_strength": null, "sr_touches": null, "timestamp": "2026-05-28T12:08:46.076445+00:00", "units": 3000}
```

## Step 2: Render Env Verification

Direct web-service env verification was blocked for the same reason as Step 1. Runner-local env is not authoritative for the web service:

```text
$ env | grep -iE 'kalman|zz|d7|live_enable|oanda|shadow' | sort | sed ...
HOSTNAME=***REDACTED***
OANDA_ACCOUNT_ID=***REDACTED***
OANDA_API_KEY=***REDACTED***
OPENAI_API_KEY=***REDACTED***
RENDER_INSTANCE_ID=***REDACTED***
RENDER_INTERNAL_HOSTNAME=***REDACTED***
RENDER_SERVICE_ID=***REDACTED***
```

Interpretation: `KALMAN_D7_LIVE_ENABLE` could not be verified inside the web service. However, the post-2026-05-28 Kalman probe has 0 filter passes, so the current Kalman zero-live symptom is explained before env/live routing is reached.

## Step 3: Filter-Rejection Probe

Data source:

```text
$ .venv/bin/python tools/fetch_massive_data.py --pair USD_JPY --tf 5m --days 10 --out data/cache/massive/USD_JPY_5m_latest_tmp.parquet
{"completeness_pct": 95.9028, "completeness_pct_naive": 70.3336, "days_requested": 10, "end": "2026-06-02T15:10:00+00:00", "pair": "USD_JPY", "rows": 2762, "source": "MASSIVE", "start": "2026-05-20T00:00:00+00:00", "tf": "5m", "trading_days": 10}

$ .venv/bin/python tools/fetch_massive_data.py --pair EUR_USD --tf 5m --days 10 --out data/cache/massive/EUR_USD_5m_latest_tmp.parquet
{"completeness_pct": 96.1111, "completeness_pct_naive": 70.4864, "days_requested": 10, "end": "2026-06-02T15:10:00+00:00", "pair": "EUR_USD", "rows": 2768, "source": "MASSIVE", "start": "2026-05-20T00:00:00+00:00", "tf": "5m", "trading_days": 10}
```

The expected local `USD_JPY_15m.parquet` was absent, and existing `EUR_USD_15m.parquet` ended at 2026-05-29. Probe therefore resampled fresh 5m MASSIVE data to M15.

### Kalman D7, 2026-05-26 to 2026-06-02

Bars evaluated: 539  
Filter pass count: 1

| first_filter_failed | bars | pct |
|---|---:|---:|
| `po_up_not_started` | 513 | 95.18 |
| `dist_out_of_range(>3 or <=0)` | 18 | 3.34 |
| `atr_outside_q2q4` | 7 | 1.30 |
| `PASS` | 1 | 0.19 |

Latest telemetry by category:

```json
{
  "PASS": {"bar_time": "2026-05-27 05:00:00+00:00", "entry_price": 159.25, "ema200": 159.13524, "atr": 0.04594, "dist_atr": 2.4977, "gap_atr": 2.2771, "rsi": 51.63, "hour_utc": 5, "regime_po": "UP", "regime_po_start_up": true},
  "atr_outside_q2q4": {"bar_time": "2026-06-01 22:15:00+00:00", "entry_price": 159.652, "ema200": 159.45827, "atr": 0.07255, "dist_atr": 2.6703, "gap_atr": 2.4979, "rsi": 52.36, "hour_utc": 22, "reason": "⛔ ATR 0.0726 outside Q2-Q4 [0.0430, 0.0591)"},
  "dist_out_of_range(>3 or <=0)": {"bar_time": "2026-06-02 11:15:00+00:00", "entry_price": 159.731, "ema200": 159.55774, "atr": 0.03423, "dist_atr": 5.0611, "gap_atr": 4.6372, "rsi": 54.45, "hour_utc": 11, "reason": "⛔ DIST 5.06 ATR out of [0,3]"},
  "po_up_not_started": {"bar_time": "2026-06-02 15:00:00+00:00", "entry_price": 159.878, "ema200": 159.59098, "atr": 0.03902, "dist_atr": 7.3556, "gap_atr": 4.8869, "rsi": 70.51, "hour_utc": 15, "regime_po": "UP", "regime_po_start_up": false}
}
```

Post-live window, 2026-05-28 to 2026-06-02:

| first_filter_failed | bars | pct |
|---|---:|---:|
| `po_up_not_started` | 331 | 95.39 |
| `dist_out_of_range(>3 or <=0)` | 12 | 3.46 |
| `atr_outside_q2q4` | 4 | 1.15 |

Post-live pass events: `[]`

### ZZ Pivot v60 SR, 2026-05-26 to 2026-06-02

Bars evaluated: 539  
Filter pass count: 6

| first_filter_failed | bars | pct |
|---|---:|---:|
| `no_peak_no_trough` | 533 | 98.89 |
| `PASS` | 6 | 1.11 |

Latest PASS telemetry:

```json
{
  "bar_time": "2026-06-02 12:30:00+00:00",
  "entry_price": 1.16508,
  "ema200": 1.16408,
  "atr": 0.00056,
  "atr_ratio": 0.992,
  "rsi": 65.13,
  "hour_utc": 12,
  "entry_type": "zz_pivot_v60_sr",
  "signal": "SELL",
  "trend_ema": 1.16422,
  "peak_type_attempts": {"pA": false, "pB": true, "pE": false, "pF": false, "tA": false, "tB": false, "tD": false, "tF": false}
}
```

Post-2026-05-28 pass events:

```text
2026-05-28 03:30 UTC  zz_pivot_v60_sr_lo  BUY   tD  RSI=20.05 ATR_ratio=0.9893
2026-05-28 12:15 UTC  zz_pivot_v60_sr     SELL  pE  RSI=64.13 ATR_ratio=1.0739
2026-06-01 13:00 UTC  zz_pivot_v60_sr_lo  BUY   tD  RSI=28.12 ATR_ratio=1.1526
2026-06-01 13:15 UTC  zz_pivot_v60_sr_lo  BUY   tD  RSI=24.64 ATR_ratio=1.2172
2026-06-02 11:45 UTC  zz_pivot_v60_sr     SELL  pB  RSI=65.59 ATR_ratio=0.9337
2026-06-02 12:30 UTC  zz_pivot_v60_sr     SELL  pB  RSI=65.13 ATR_ratio=0.9920
```

Latest no-signal telemetry:

```json
{
  "bar_time": "2026-06-02 15:00:00+00:00",
  "entry_price": 1.16413,
  "ema200": 1.16412,
  "atr": 0.00065,
  "atr_ratio": 1.145,
  "rsi": 44.14,
  "hour_utc": 15,
  "trend_ema": 1.16428,
  "uptrend": false,
  "downtrend": true,
  "peak_type_attempts": {"pA": false, "pB": false, "pE": false, "pF": false, "tA": false, "tB": false, "tD": false, "tF": false}
}
```

## Step 4: Verdict

| Strategy | Bars in 7d | Filter pass count | First-fail histogram | Audit rows | Verdict |
|---|---:|---:|---|---:|---|
| `kalman_d7_trail_atr` / shared D7 filter | 539 | 1 total; 0 since 2026-05-28 | `po_up_not_started` 513, `dist_out_of_range` 18, `atr_outside_q2q4` 7, `PASS` 1 | 0 | `MARKET_WAIT` |
| `zz_pivot_v60_sr` / `_lo` | 539 | 6 | `no_peak_no_trough` 533, `PASS` 6 | 1 skipped/shadow, 0 sent/filled | `SILENT_DROP_V3` |

Kalman plain-language summary: the only 7-day pass was 2026-05-27 05:00 UTC, before the stated 2026-05-28 live env activation. From 2026-05-28 onward, all evaluated bars failed before candidate construction, mostly because a new Perfect Order UP transition did not occur; later UP bars were already in-regime and failed `po_up_not_started`, and some were too far from EMA200.

ZZ Pivot plain-language summary: market filters are not the zero-fire cause. The probe found six post-2026-05-28 candidate bars, including normal and loser-zone entry types. Production has only one matching audit row and it was downgraded to `shadow_tracking`, so the live zero-fire symptom is downstream of strategy evaluation.

## Step 5: Instrumentation Patch

Changed files:

- `modules/demo_trader.py`
- `tools/kalman_zz_zero_fire_probe.py`
- `knowledge-base/wiki/audit-index.md`

Instrumentation behavior:

- `_block()` now emits `[SENTINEL_BLOCK_DIAG] <entry_type> blocked at: <reason>` for `kalman_d7_*`, `zz_pivot_v60_sr`, and `zz_pivot_v60_sr_lo`.
- Candidate-built but shadow-downgraded watched entries log:
  - `[SENTINEL_BLOCK_DIAG] <entry_type> candidate built but shadow-downgraded before OANDA promotion (...)`
  - `[SENTINEL_BLOCK_DIAG] <entry_type> OANDA skipped after candidate build: <reason> (...)`

Verification:

```text
$ .venv/bin/python -m py_compile modules/demo_trader.py tools/kalman_zz_zero_fire_probe.py strategies/daytrade/kalman_d7_trend.py strategies/daytrade/zz_pivot_v60_sr.py
# exit 0

$ grep -n "SENTINEL_BLOCK_DIAG.*candidate built\|SENTINEL_BLOCK_DIAG.*OANDA skipped\|SILENT_DROP_DIAG_TYPES" modules/demo_trader.py
3477:                or entry_type in self._SILENT_DROP_DIAG_TYPES
5357:            entry_type in self._SILENT_DROP_DIAG_TYPES
5377:                    f"[SENTINEL_BLOCK_DIAG] {entry_type} candidate built but "
5805:                    f"[SENTINEL_BLOCK_DIAG] {entry_type} OANDA skipped after "
7528:    _SILENT_DROP_DIAG_TYPES = _KALMAN_D7_LIVE_OVERRIDE | frozenset({
```

No filter parameters, shadow-first behavior, or LIVE lot booster values were changed.
