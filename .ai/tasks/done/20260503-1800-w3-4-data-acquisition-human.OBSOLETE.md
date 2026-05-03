---
id: 20260503-1800-w3-4-data-acquisition-human
title: W3-4-data acquisition human — GBPJPY M1/M5 2014-2026 source files needed
owner: human
status: queued
priority: P0
created_at: 2026-05-03T18:00:00+0900
roadmap_gate: Gate 1 (W3-4 verdict unblocker)
rule: R3
parent_task: 20260503-1721-w3-4-data-gbpjpy-m5-12yr-backfill
---

# Objective

Codex sandbox could not resolve either HistData or Dukascopy hosts, so the W3-4 GBPJPY 12-year data backfill cannot proceed from this environment. Provide an offline/source-acquired 2014-01 through 2026-04 GBPJPY M1 dataset, or a validated M5 parquet, so `c1_london_breakout` can be rerun with coverage >= 90%.

# Blocking Evidence

Executed from `/Users/jg-n-012/test/fx-ai-trader` on 2026-05-03:

```bash
curl -sSIL --max-time 20 -w '\nexit=%{exitcode} http_code=%{http_code} remote_ip=%{remote_ip} err=%{errormsg}\n' \
  "https://www.histdata.com/get.php?fname=DAT_ASCII_GBPJPY_M1_201401.zip"
```

Result:

```text
curl: (6) Could not resolve host: www.histdata.com
exit=6 http_code=000 remote_ip= err=Could not resolve host: www.histdata.com
```

```bash
curl -sSIL --max-time 20 -w '\nexit=%{exitcode} http_code=%{http_code} remote_ip=%{remote_ip} err=%{errormsg}\n' \
  "https://datafeed.dukascopy.com/datafeed/GBPJPY/2014/00/00/00h_ticks.bi5"
```

Result:

```text
curl: (6) Could not resolve host: datafeed.dukascopy.com
exit=6 http_code=000 remote_ip= err=Could not resolve host: datafeed.dukascopy.com
```

# Required Evidence Next

Preferred input:

- HistData monthly ZIP files for `DAT_ASCII_GBPJPY_M1_YYYYMM.zip`, 2014-01 through 2026-04.
- Place them under a local staging directory such as `data/vendor/histdata/GBPJPY/M1/`.

Acceptable input:

- Dukascopy GBPJPY tick/M1 source files covering 2014-01-01 through 2026-04-30.
- Or a prebuilt parquet at `data/cache/extended/GBP_JPY_5m_long.parquet` with:
  - UTC `DatetimeIndex`
  - columns compatible with existing BT loader: `Open/High/Low/Close/Volume` or lower-case equivalents
  - 5-minute bars
  - coverage >= 90% for 2014-01-01 through 2026-04-30

# Resume Command

After source files or parquet are available, resume parent task:

```bash
python3 tools/bt/c1_london_breakout.py \
  --pair GBP_JPY --start 2014-01-01 --end 2026-04-30 \
  --output knowledge-base/raw/bt-results/c1-london-breakout \
  --seed 20260503
```

Then run validity with the existing Render snapshot:

```bash
python3 tools/bt/c1_validity_checks.py \
  --bt-result knowledge-base/raw/bt-results/c1-london-breakout.json \
  --rsk-source render_snapshot \
  --rsk-snapshot knowledge-base/raw/snapshots/render-demo-trades-20260503.db \
  --broker-cross dukascopy \
  --bootstrap-n 1000 \
  --output knowledge-base/raw/bt-results/c1-london-breakout-validity.json
```
