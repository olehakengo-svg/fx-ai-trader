# FORCE-DEMOTED Live Leak Fix Run Report

## Status

実装完了。`FORCE_DEMOTED` Live 混入の historical reclass、startup migration、admin diagnostic、dry-run safety script、OANDA 送信直前の depth-in-defense gate を追加した。

Note: 実測結果を task file §7 に追記しようとした時点で `.ai/tasks/queue/20260511-1610-force-demoted-live-leak-fix.md` が作業ツリーから消えていたため、この run report に同じ §7 相当の内容を保存する。

## Forensics

SSOT: `modules/demo_trader.py::DemoTrader._FORCE_DEMOTED` = 19 strategies.

Snapshot: `knowledge-base/raw/snapshots/render-demo-trades-20260503.db`, cutoff `2026-04-08T00:00:00`, FX only, `is_shadow=0`.

Q1 summary:

| entry_type | n | pnl_total | earliest | latest |
|---|---:|---:|---|---|
| vwap_mean_reversion | 11 | -63.1 | 2026-04-20T06:09:12.602821+00:00 | 2026-04-23T14:06:37.572835+00:00 |
| sr_break_retest | 4 | -44.2 | 2026-04-08T13:16:36.877413+00:00 | 2026-04-16T16:16:44.720995+00:00 |
| donchian_momentum_breakout | 3 | -32.1 | 2026-04-08T11:28:50.396163+00:00 | 2026-04-14T12:00:19.237422+00:00 |
| sr_channel_reversal | 34 | -24.2 | 2026-04-09T09:42:28.933400+00:00 | 2026-04-20T09:54:54.880180+00:00 |
| engulfing_bb | 16 | -12.1 | 2026-04-09T09:49:45.737659+00:00 | 2026-04-20T09:30:33.188751+00:00 |
| macdh_reversal | 3 | -9.4 | 2026-04-08T05:20:29.120938+00:00 | 2026-04-16T07:44:17.990973+00:00 |
| v_reversal | 5 | -4.9 | 2026-04-13T13:51:07.612315+00:00 | 2026-04-14T06:17:10.796666+00:00 |
| ema_trend_scalp | 16 | -2.4 | 2026-04-13T07:17:36.655632+00:00 | 2026-04-17T15:37:57.462495+00:00 |
| stoch_trend_pullback | 26 | -0.7 | 2026-04-08T01:57:34.551638+00:00 | 2026-04-29T06:05:39.924812+00:00 |

Total FORCE_DEMOTED Live in snapshot: N=155 / PnL=-112.8p.

Q2 vwap daily:

| date | n | pnl |
|---|---:|---:|
| 2026-04-20 | 3 | +21.5 |
| 2026-04-21 | 2 | +3.6 |
| 2026-04-22 | 3 | -59.2 |
| 2026-04-23 | 3 | -29.0 |

Q3 mode distribution: no `PYR_` marker. vwap is `daytrade_gbpusd=5`, `daytrade_eurjpy=4`, `daytrade_gbpjpy=2`; sr_channel is scalp-family; sr_break is daytrade-family.

Q4: snapshot lacks `flag_drift_backfilled`, so FLAG_DRIFT overlap is `insufficient data in source`. OANDA id distribution confirms vwap 11/11 with id, sr_channel 34/34 with id, sr_break 4/4 with id.

Hypothesis judgment:

- A: not supported by snapshot for vwap; no post-2026-04-24 vwap Live rows. Current Render freshness still needs deployment-side verification.
- B: supported for vwap; all vwap rows are historical pre-trip residue.
- C: possible in code because late bypasses can restore `_is_promoted=True`; fixed with downstream final gate.
- D: not supported by snapshot; no PYR marker in FORCE_DEMOTED Live rows.

## Migration Dry Run

Copy: `/private/tmp/force_demoted_leak_migration_check.db`.

Before startup migration: TRUE_LIVE_FX N=511 / PnL=-387.0p; FORCE_DEMOTED_LIVE N=155 / PnL=-112.8p; SHADOW_FX N=3820 / PnL=-4989.1p.

After startup migration chain: TRUE_LIVE_FX N=220 / PnL=-182.9p; FORCE_DEMOTED_LIVE N=0 / PnL=0.0p; SHADOW_FX N=4111 / PnL=-5193.2p; `force_demoted_live_leak=1` N=155 / PnL=-112.8p. Backfill status: `backfilled`, `fixed_count=155`, `unsafe_post_rule_fill_count=0`.

## Files Changed

- `modules/demo_db.py`: adds `force_demoted_live_leak`, startup backfill, status accessor, idempotent/unsafe states.
- `modules/demo_trader.py`: adds final FORCE_DEMOTED downstream gate and resend skip.
- `app.py`: adds `/api/admin/force_demoted_leak_status`.
- `scripts/check_force_demoted_leak_safety.py`: dry-run safety checker.
- `tests/test_force_demoted_leak_backfill.py`: backfill and final-gate tests.

## Verification

- `PYTHONPYCACHEPREFIX=/private/tmp/pycache-codex python3 -m pytest tests/test_force_demoted_leak_backfill.py -q` -> 4 passed.
- `PYTHONPYCACHEPREFIX=/private/tmp/pycache-codex python3 -m pytest tests/test_force_demoted_leak_backfill.py tests/test_demo_db.py tests/test_flag_drift_writepath.py tests/test_flag_drift_backfill.py -q` -> 30 passed.
- `PYTHONPYCACHEPREFIX=/private/tmp/pycache-codex python3 -m pytest tests/ -x -q` -> 1419 passed, 1 xfailed.
- `PYTHONPYCACHEPREFIX=/private/tmp/pycache-codex python3 scripts/check.py` -> all 6 checks passed; pre-existing KB warnings remained.

## Risks

- Render current-production log/API verification was not run from this sandbox; deployment review should confirm `/api/admin/force_demoted_leak_status` and fresh `/api/strategies/status`.
- Startup migration chain also applies older shadow/flag-drift migrations on the raw snapshot copy, so TRUE_LIVE_FX before/after movement is not solely this new backfill. The marker-specific count is the clean attribution: N=155 / -112.8p.

## Next Recommended Task

Deploy and verify on Render: call `/api/admin/force_demoted_leak_status`, confirm `remaining_force_demoted_live_leaks=0`, then re-pull `/api/strategies/status` clean Live KPI. After that, run the separate ELITE_LIVE / PAIR_PROMOTED worst-cell Wilson_BF/Kelly/WF audit noted in the task.
