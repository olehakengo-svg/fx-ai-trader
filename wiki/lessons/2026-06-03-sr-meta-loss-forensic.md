# 2026-06-03 sr_anti_hunt_bounce demo_trades metadata loss forensic

## Summary

`sr_anti_hunt_bounce` の post-2026-05-22 shadow cohort で `sr_basis`,
`edge_cell_id`, `spread_at_entry`, MTF labels, and `alpha_snapshot` が落ちた主因は
`shadow_emit_signals` の direct `open_trade()` side path だった。

`app.py` の daytrade signal builder は `sig["sr_entry_map"]["recommended"]` を
生成し続けていたが、敗北候補を `shadow_emit_signals` に詰める際に
`sr_entry_map` を payload にコピーしていなかった。さらに
`modules/demo_trader.py::_open_shadow_emit_trade()` は `_tick_entry()` の enrichment
経路を通らず、`sr_basis`, `edge_cell_id`, `signal_price`, `spread_at_entry`,
`regime`, `layer1_dir`, MTF fields を `DemoDB.open_trade()` に渡していなかった。

## Regression commit

Primary regression: `e8e707f4 fix(audit): restore SR shadow emit OANDA audit rows [rule:R3]`.

This commit added `_open_shadow_emit_trade()` and routed SR-family shadow emits
through it to restore OANDA audit rows. The audit row restoration worked, but
the new helper preserved only the minimal direct INSERT fields plus audit
metadata. It did not reproduce `_tick_entry()`'s metadata enrichment.

Other commits in the 2026-05-20..2026-05-25 window were checked:

- `a7b18453`: introduced `LIVE_PROMOTE_LOSERS`; live-promote emits go back
  through `_tick_entry()`, so not the SR shadow metadata-loss path.
- `747398af`: added Kalman D7 entries to `LIVE_PROMOTE_LOSERS`; no SR field
  propagation change.
- `1972bd8b`, `c7b4ab52`, `79600126`: Kalman D7 additions/refactor only.
- `e085ec09`: VIX carry lot boost only.
- `104c635e`, `8c182cc3`: py39 import/annotation guard fixes only.
- `b3efa69a`: task completion marker; no relevant modified target files.

Secondary independent bug: primary `_tick_entry()` wrote alpha snapshots with
`UPDATE demo_trades SET alpha_snapshot = ? WHERE id = ?`, but
`DemoDB.open_trade()` returns the string `trade_id`, not the integer `id`.
That UPDATE could silently affect zero rows. The fix changes it to
`WHERE trade_id = ?`.

## sr_entry_map producer

The only active producer found is `app.py` in `compute_daytrade_signal()`:

- `sr_entry_map = {"nearest_support": ..., "nearest_resistance": ..., "recommended": None}`
- `sr_entry_map["nearest_support"] = ...`
- `sr_entry_map["nearest_resistance"] = ...`
- `sr_entry_map["recommended"] = {"ema_confidence": ..., "sr_basis": rec["trigger_price"], ...}`
- returned as top-level `"sr_entry_map": sr_entry_map`

No producer exists under `strategies/daytrade/`; strategy `Candidate` objects
only carry `sr_meta`. Therefore SR loser candidates need the top-level
`sr_entry_map` copied into each `shadow_emit_signals[]` payload before
`demo_trader` consumes it.

## pyarrow / parquet root cause

`requirements.txt` had `pandas` but no parquet engine (`pyarrow` or
`fastparquet`). Local venv already had `pyarrow 24.0.0`, which explains why
local import smoke could pass while Render production could still raise:

`Unable to find a usable engine; tried using: 'pyarrow', 'fastparquet'`

Fix: add `pyarrow>=15.0.0` to `requirements.txt`.

The exact requested file `data/cache/massive/USDJPY_M15.parquet` is not present
in this checkout, so local smoke used the existing fixture
`tests/fixtures/usd_jpy_m15_2024q1.parquet` and `pd.read_parquet()` returned
shape `(6095, 5)`.

## Fix

- `app.py`: copy top-level `sr_entry_map` into each daytrade
  `shadow_emit_signals[]` payload.
- `modules/demo_trader.py::_open_shadow_emit_trade()`:
  - reads `sr_entry_map["recommended"]` into `ema_conf` and `sr_basis`;
  - resolves and records `edge_cell_id` for attribution, including E12 for
    `sr_anti_hunt_bounce` x `EUR_JPY`;
  - records `signal_price`, `spread_at_entry`, `regime`, `layer1_dir`,
    confluence, and MTF fields;
  - fetches spread as a fallback when not supplied;
  - writes `alpha_snapshot` after insert for 15m rows, keyed by `trade_id`.
- `modules/demo_trader.py::_tick_entry()`: alpha snapshot UPDATE now uses
  `WHERE trade_id = ?`.
- `requirements.txt`: adds `pyarrow>=15.0.0`.

## Regression test

Added `tests/test_sr_shadow_emit_metadata.py`.

The test creates a real SQLite `DemoDB`, calls
`DemoTrader._open_shadow_emit_trade(...)` for `sr_anti_hunt_bounce` x
`EUR_JPY`, then directly SELECTs `demo_trades` and asserts:

- `sr_basis != 0.0`
- `edge_cell_id == "E12"`
- `alpha_snapshot != ""`
- `spread_at_entry != 0.0`
- `mtf_alignment != ""`

Falling-first result before fix: failed with
`TypeError: DemoTrader._open_shadow_emit_trade() got an unexpected keyword argument 'sr_entry_map'`.
After fix: passed.

## Prevention

Any future side path that persists `demo_trades` must either route through
`_tick_entry()` or explicitly pass the same audit axes: SR basis, cell id,
spread, MTF, regime/layer, confluence, and alpha snapshot. Mock-only tests are
insufficient; use real SQLite INSERT + SELECT assertions for these invariants.
