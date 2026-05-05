# W4-Redesign BT Source Spec (2026-05-05)

## Decision

W4-Redesign の全 BT は **MASSIVE 由来の local parquet cache** を正式データソースに統一する。

Required source:

```text
data/cache/massive/{PAIR}_{TF}.parquet
```

Examples:

```text
data/cache/massive/USD_JPY_15m.parquet
data/cache/massive/USD_JPY_5m.parquet
data/cache/massive/GBP_JPY_5m.parquet
```

Network providers are not primary BT sources. Yahoo/yfinance, OANDA, TwelveData, and live Massive API fetches may be used only to refresh or backfill the official parquet cache before the BT run. They must not silently determine a W4 verdict.

## Production Parity Contract

Each W4 BT must call the production signal and exit path with `backtest_mode=True`.

Required:

- Use `app.run_daytrade_backtest`, `app.run_scalp_backtest`, `app.run_1h_backtest`, or the closest production-equivalent runner.
- Preserve production signal arbitration, SL/TP, friction, cooldown, max-hold, and trade logging unless the redesign explicitly changes that component.
- Do not replace production logic with focused helper functions for LOCK verdicts.
- Do not resample inside the verdict runner as a substitute for the official TF cache.

Allowed:

- Materialize a missing TF cache before the BT run from MASSIVE source data.
- Use a harness only when it is documented as production-parity for the target strategy and calls the same production signal/exit semantics.
- Use focused runners for diagnostics only, with verdict clearly marked `DIAGNOSTIC_ONLY`.

## Current Cache State

Observed on 2026-05-05:

| Cache | Rows | Start UTC | End UTC | Columns |
|---|---:|---|---|---|
| `data/cache/massive/USD_JPY_5m.parquet` | 903,828 | 2014-01-02 04:55 | 2026-04-30 23:55 | lowercase polygon-style |
| `data/cache/massive/GBP_JPY_5m.parquet` | 925,109 | 2014-01-02 04:55 | 2026-04-30 23:55 | lowercase polygon-style |

Coverage is sufficient for 365d and multi-year BT on these two 5m caches. It is not sufficient for strict 15m production BT because `USD_JPY_15m.parquet` and `GBP_JPY_15m.parquet` are absent in this checkout.

Before any 15m W4 verdict, the task must either:

1. create the official `data/cache/massive/{PAIR}_15m.parquet` cache from MASSIVE, then run production BT against that cache, or
2. mark the result as diagnostic only.

## Runner Choice

Preferred runner for daytrade strategies:

```text
app.run_daytrade_backtest(..., interval="15m")
```

Preferred CLI wrapper after the data-path patch:

```text
BT_MODE=1 NO_AUTOSTART=1 .venv/bin/python tools/bt_365d_runner.py USDJPY
```

`modules/bt_vec_harness.py` is appropriate only for strategies already covered by its production-parity toggles. Its local cache loader is useful, but W4 verdicts must not use vectorized approximations unless equivalence is documented for the target strategy.

## Cell vs Aggregate

Each W4 verdict must state whether it evaluates:

- `aggregate`: all trades for the strategy/pair over the window, or
- `cell`: a filtered cohort from audit DB, such as pair/session/regime/feature bins.

If the audit evidence is cell-filtered, the redesign BT must re-run the same cell:

```yaml
cell:
  pair: USD_JPY
  tf: 15m
  session: London|NY|Tokyo|all
  filters:
    t1_aligned: ...
    d1_vol_z_bin: ...
    r1_hurst_bin: ...
```

If the audit evidence is aggregate, the redesign BT may evaluate aggregate first, then report cell breakdowns as secondary diagnostics.

## Window

Default evaluation window:

```yaml
lookback_days: 365
```

Optional robustness windows:

```yaml
lookback_days_extra:
  - 730
  - 1825
```

Longer windows are confirmatory. They do not replace the 365d primary verdict unless pre-registered.

## edge-lab vs W4P1 N Divergence

`knowledge-base/raw/bt-results/edge-lab-2026-04-23.md` states:

- generated: 2026-04-23 06:32 UTC
- lookback: 365d / 15m
- source: `tools/edge_lab.py`
- basis: `app.run_daytrade_backtest` trade_log
- pooled enriched trades: 8,391

The JSON file contains 5 pair blocks, but the cited `streak_reversal` N=468 is not multi-pair. It is exactly:

```yaml
pair: USD_JPY
strategy: streak_reversal
n: 468
wins: 339
wr: 0.7244
wilson_lo: 0.6822
pf: 3.0670
ev: 1.3666
kelly: 0.4882
```

Session split:

| Cell | N | WR | Wilson lo | PF | EV | Kelly |
|---|---:|---:|---:|---:|---:|---:|
| USD_JPY / London | 242 | 0.7190 | 0.6593 | 2.9114 | 1.1774 | 0.4720 |
| USD_JPY / NY | 118 | 0.7542 | 0.6694 | 3.0746 | 1.3219 | 0.5089 |
| USD_JPY / Tokyo | 104 | 0.6923 | 0.5981 | 2.8935 | 1.5504 | 0.4530 |
| USD_JPY / Off | 4 | 1.0000 | 0.5101 | inf | 9.3504 | n/a |

The W4P1 focused A/B used `data/cache/massive/USD_JPY_5m.parquet`, resampled to 15m, and measured an aggregate focused `streak_reversal` detector over 2025-05-01 03:00 UTC to 2026-04-30 23:45 UTC. That is not equivalent to the edge-lab cohort because:

- edge-lab is production `run_daytrade_backtest` trade_log; W4P1 was a focused detector.
- edge-lab stores pair/session/feature fields, but no per-trade timestamp in the JSON; exact date filtering cannot be reconstructed from JSON alone.
- edge-lab N=468 is USD_JPY aggregate across sessions, not all pairs.
- W4P1 included a larger candidate set: baseline N=1224 and proposed N=1564.
- W4P1 resampled 5m cache inside the focused runner because the strict 15m cache was missing.

Analytical estimate: re-running the same production path and same USD_JPY aggregate cell should move N toward 468 only if the current production logic, strategy enablement set, and data window match the 2026-04-23 edge-lab run. A W4P1 result with N above 1,000 is measuring a broader or different detector population, not merely a higher-frequency version of the same cell.

## Dispatch Script v2 Spec

Future `tools/w4_redesign_dispatch_v2.py` should:

1. Read `audits/edge_design/_REDESIGN_QUEUE.md` and per-strategy audit files.
2. Extract strategy, tier, recommendation, broken axes, pair hints, TF hints, and whether evidence is aggregate or cell-filtered.
3. Generate new task IDs without replacing `.ai/tasks/queue/_paused_w4_redesign/`.
4. Embed this BT source contract into every task:
   - MASSIVE parquet cache required.
   - exact `data/cache/massive/{PAIR}_{TF}.parquet` path required.
   - production signal/exit runner required.
   - helper/focused runner output is diagnostic only.
5. Embed LOCK criteria v2 from `knowledge-base/wiki/decisions/w4-redesign-lock-criteria-v2-2026-05-05.md`.
6. Add a required `cell_spec` section:
   - `aggregate` if audit evidence is aggregate.
   - explicit pair/session/regime filters if audit evidence is cell-filtered.
7. Add a `data_preflight` section:
   - assert cache file exists.
   - assert coverage >= 365d.
   - assert schema normalized to `Open/High/Low/Close/Volume`.
   - abort verdict if missing; do not fall back to Yahoo.

## Codex Self-Review

- The user concern is valid: W4P1 used MASSIVE-derived data, but not the strict production BT data path.
- The right correction is not to bless ad hoc 5m-to-15m resampling. The right correction is to make production BT consume the official MASSIVE parquet cache first.
- The edge-lab N=468 is logically explainable as a production USD_JPY aggregate trade-log cohort, while W4P1 N=1224/1564 is a broader focused detector population.
- Requiring cell/aggregate declaration prevents future audit values from being compared against a different estimand.
