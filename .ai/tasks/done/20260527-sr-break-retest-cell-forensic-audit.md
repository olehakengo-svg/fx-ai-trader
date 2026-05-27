# sr_break_retest cell-level Win/Loss forensic audit

## Result

Run date: 2026-05-27 UTC.

Data source used: public read API backed by production `_db_path=/var/data/demo_trades.db`.

Local note: `/var/data/demo_trades.db` was not mounted in this Codex workspace. Local `demo_trades.db` had only 18 `demo_trades` rows and `oanda_audit=0`, so it was rejected as non-authoritative. The production API view was used read-only:

- `/api/demo/trades?status=closed&limit=1000&offset=...` fetched 7,500 closed demo rows.
- `/api/oanda/audit?limit=7000` fetched all 6,580 audit rows.
- `/api/oanda/trades?state=closed&limit=500&offset=...` fetched 763 OANDA closed rows.

Important reconciliation finding: the pre-registered prompt cohort is not present in the current production data. Current `demo_trades` has `sr_break_retest CLOSED N=262`, with `is_shadow=255` and `is_shadow=0` only `7`. Current OANDA broker table also has only `strategy='sr_break_retest' N=7`. Therefore the stated `demo N=82`, `USD_JPY/SELL demo N=26 WR=57.7% +35.5p`, and `GBP_USD demo 37 TP 0 / SL 37` cohort could not be reproduced from the current `/var/data/demo_trades.db` API view.

Additional API caveat: current `app.py` does not read a `strategy` query parameter in `/api/oanda/stats`; it accepts range/date/instrument/XAU filters only (`app.py:13907-13947`). So `/api/oanda/stats?strategy=sr_break_retest` is not strategy-filtered in this code path.

### Phase A: reconciliation matrix

| source | filter | N |
|---|---|---:|
| `demo_trades` API | `entry_type='sr_break_retest' AND status='CLOSED'` | 262 |
| `demo_trades` API | same, `is_shadow=1` | 255 |
| `demo_trades` API | same, `is_shadow=0` | 7 |
| `oanda_audit` API | `entry_type='sr_break_retest'` | 203 |
| `oanda_trades` API | `strategy='sr_break_retest'` | 7 |

Current `sr_break_retest` demo date range: `2026-04-06T13:00:40.755303+00:00` to `2026-05-27T01:52:35.513355+00:00`.

SR audit columns are unusable as expected: `sr_strength`, `sr_touches`, `sr_days_span`, `sr_is_strong`, `sr_distance_atr` are all NULL for all 203 `sr_break_retest` audit rows.

### Phase B: per-cell stats

Wilson lower uses standard 95% `z=1.96`. Bonferroni lower uses repo recovery convention `Z=3.29`, matching the existing FORCE_DEMOTED recovery documentation.

| instrument | dir | shadow | N | wins | WR | EV pips | total | PF | Wilson_lo | Wilson_bf_lo | EV 95% CI | normalized TP/SL/MC |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| EUR_JPY | BUY | 1 | 26 | 0 | 0.0% | -7.49 | -194.8 | 0.00 | 0.000 | 0.000 | [-9.40, -5.59] | 0/14/0 |
| EUR_JPY | SELL | 1 | 24 | 9 | 37.5% | +0.17 | +4.2 | 1.02 | 0.212 | 0.141 | [-6.70, +7.05] | 6/11/0 |
| GBP_JPY | BUY | 1 | 30 | 2 | 6.7% | -9.18 | -275.5 | 0.18 | 0.018 | 0.009 | [-13.56, -4.81] | 2/22/0 |
| GBP_JPY | SELL | 1 | 12 | 2 | 16.7% | -5.16 | -61.9 | 0.57 | 0.047 | 0.023 | [-17.80, +7.48] | 2/8/0 |
| GBP_USD | BUY | 0 | 2 | 1 | 50.0% | +0.95 | +1.9 | 1.16 | 0.095 | 0.041 | [-24.24, +26.14] | 1/1/0 |
| GBP_USD | BUY | 1 | 46 | 14 | 30.4% | -0.83 | -38.3 | 0.79 | 0.191 | 0.137 | [-3.48, +1.81] | 8/14/0 |
| GBP_USD | SELL | 0 | 1 | 1 | 100.0% | +16.30 | +16.3 | inf | 0.207 | 0.085 | [+16.30, +16.30] | 1/0/0 |
| GBP_USD | SELL | 1 | 30 | 9 | 30.0% | -3.29 | -98.7 | 0.55 | 0.167 | 0.111 | [-7.46, +0.88] | 9/21/0 |
| USD_JPY | BUY | 0 | 3 | 0 | 0.0% | -7.70 | -23.1 | 0.00 | 0.000 | 0.000 | [-14.46, -0.94] | 0/1/1 |
| USD_JPY | BUY | 1 | 66 | 22 | 33.3% | +0.42 | +27.4 | 1.11 | 0.232 | 0.178 | [-2.09, +2.92] | 15/24/0 |
| USD_JPY | SELL | 0 | 1 | 0 | 0.0% | -20.40 | -20.4 | 0.00 | 0.000 | 0.000 | [-20.40, -20.40] | 0/1/0 |
| USD_JPY | SELL | 1 | 21 | 0 | 0.0% | -8.50 | -178.4 | 0.00 | 0.000 | 0.000 | [-11.33, -5.66] | 0/16/0 |

No cell has `Wilson_bf_lo > 0.50`. Rule 2 therefore keeps the whole strategy rejected / FORCE_DEMOTED.

Close-reason matrix highlights:

| instrument | dir | shadow | close_reason | N | wins | EV | total | Wilson_bf_lo | avg_spread | avg_MFE | avg_MAE |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| EUR_JPY | BUY | 1 | SIGNAL_REVERSE | 2 | 0 | -5.90 | -11.8 | 0.000 | 1.750 | 0.00 | 6.15 |
| EUR_JPY | BUY | 1 | SL_HIT | 14 | 0 | -10.93 | -153.0 | 0.000 | 1.786 | 2.84 | 10.93 |
| EUR_JPY | BUY | 1 | TIME_DECAY_EXIT | 10 | 0 | -3.00 | -30.0 | 0.000 | 1.100 | 6.08 | 4.22 |
| EUR_JPY | SELL | 1 | TP_HIT | 6 | 6 | +24.62 | +147.7 | 0.357 | 1.783 | 24.62 | 2.85 |
| EUR_JPY | SELL | 1 | SL_HIT | 11 | 0 | -14.16 | -155.8 | 0.000 | 1.736 | 3.90 | 14.16 |
| GBP_JPY | BUY | 1 | SL_HIT | 22 | 0 | -14.12 | -310.6 | 0.000 | 0.432 | 4.95 | 14.12 |
| GBP_JPY | SELL | 1 | SL_HIT | 8 | 0 | -17.09 | -136.7 | 0.000 | 2.913 | 2.17 | 17.09 |
| GBP_USD | BUY | 1 | SIGNAL_REVERSE | 18 | 5 | -2.21 | -39.7 | 0.074 | 0.361 | 2.87 | 4.46 |
| GBP_USD | BUY | 1 | SL_HIT | 14 | 0 | -9.26 | -129.6 | 0.000 | 0.371 | 2.86 | 9.26 |
| GBP_USD | BUY | 1 | TP_HIT | 8 | 8 | +16.59 | +132.7 | 0.425 | 1.137 | 16.59 | 2.54 |
| GBP_USD | SELL | 1 | SL_HIT | 21 | 0 | -10.53 | -221.2 | 0.000 | 0.000 | 0.02 | 10.53 |
| GBP_USD | SELL | 1 | TP_HIT | 9 | 9 | +13.61 | +122.5 | 0.454 | 0.000 | 13.61 | 7.26 |
| USD_JPY | BUY | 1 | TP_HIT | 15 | 15 | +16.07 | +241.0 | 0.581 | 0.533 | 16.07 | 0.47 |
| USD_JPY | BUY | 1 | SL_HIT | 24 | 0 | -9.32 | -223.8 | 0.000 | 0.533 | 4.08 | 9.32 |
| USD_JPY | SELL | 0 | SL_HIT | 1 | 0 | -20.40 | -20.4 | 0.000 | 0.800 | 3.50 | 20.40 |
| USD_JPY | SELL | 1 | SL_HIT | 16 | 0 | -10.62 | -169.9 | 0.000 | 0.400 | 1.16 | 10.62 |
| USD_JPY | SELL | 1 | SIGNAL_REVERSE | 3 | 0 | -2.00 | -6.0 | 0.000 | 0.533 | 1.80 | 5.70 |
| USD_JPY | SELL | 1 | TIME_DECAY_EXIT | 2 | 0 | -1.25 | -2.5 | 0.000 | 0.000 | 1.10 | 3.70 |

### Phase C: USD_JPY/SELL ledger and verdict

Current production data has `USD_JPY/SELL N=22`, not the requested 26. Split: live `N=1`, shadow `N=21`.

| cohort | N | wins | WR | EV | total | Wilson_bf_lo | TP/SL/MC normalized |
|---|---:|---:|---:|---:|---:|---:|---|
| all | 22 | 0 | 0.0% | -9.04 | -198.8 | 0.000 | 0/17/0 |
| live (`is_shadow=0`) | 1 | 0 | 0.0% | -20.40 | -20.4 | 0.000 | 0/1/0 |
| shadow (`is_shadow=1`) | 21 | 0 | 0.0% | -8.50 | -178.4 | 0.000 | 0/16/0 |

Full current ledger:

| # | trade_id | entry_time | exit_time | pips | close | MFE | MAE | spread | slip | shadow | v2 |
|---:|---|---|---|---:|---|---:|---:|---:|---:|---:|---|
| 1 | 35f755b1-b15 | 2026-04-07T09:41:01.810938+00:00 | 2026-04-07T12:46:12.822459+00:00 | -24.7 | SL_HIT | 0.0 | 24.7 | 0.8 | 1.7 | 1 |  |
| 2 | 35f3fdb8-d40 | 2026-04-08T06:15:14.166350+00:00 | 2026-04-08T09:44:34.338991+00:00 | -22.4 | SL_HIT | 0.0 | 22.4 | 0.8 | 0.3 | 1 |  |
| 3 | 51355bf2-6cc | 2026-04-08T13:16:36.877413+00:00 | 2026-04-08T13:35:10.767547+00:00 | -20.4 | SL_HIT | 3.5 | 20.4 | 0.8 | 0.4 | 0 |  |
| 4 | ac2f7097-7a1 | 2026-04-16T00:31:37.373521+00:00 | 2026-04-16T02:39:20.691442+00:00 | 0.0 | SIGNAL_REVERSE | 4.0 | 3.8 | 0.8 | -0.4 | 1 |  |
| 5 | aa654334-266 | 2026-05-04T05:12:58.128550+00:00 | 2026-05-04T06:44:39.530364+00:00 | -19.7 | SL_HIT | 5.9 | 19.7 | 0.8 | 1.0 | 1 |  |
| 6 | 08c9166e-945 | 2026-05-08T08:39:33.589125+00:00 | 2026-05-08T10:55:09.660752+00:00 | -9.0 | SL_HIT | 5.1 | 9.0 | 0.8 | -0.1 | 1 |  |
| 7 | 6f35eda6-b27 | 2026-05-14T06:47:25.175524+00:00 | 2026-05-14T07:15:28.510537+00:00 | -7.2 | SL_HIT | 0.0 | 7.2 | 0.8 | -2.4 | 1 | no_go |
| 8 | 9e30532c-675 | 2026-05-14T07:46:12.166536+00:00 | 2026-05-14T08:04:56.477975+00:00 | -6.5 | SL_HIT | 5.1 | 6.5 | 0.8 | 0.0 | 1 | no_go |
| 9 | 71f76e8a-3c4 | 2026-05-14T07:54:03.653887+00:00 | 2026-05-14T07:58:17.907797+00:00 | -7.1 | SL_HIT | 0.1 | 7.1 | 0.8 | 0.5 | 1 | no_go |
| 10 | df89638b-f4d | 2026-05-14T09:33:04.980418+00:00 | 2026-05-14T10:20:19.672572+00:00 | -1.7 | SIGNAL_REVERSE | 1.4 | 4.2 | 0.8 | 0.2 | 1 | no_go |
| 11 | ffc4b306-f72 | 2026-05-20T16:20:04.951512+00:00 | 2026-05-20T16:25:12.055836+00:00 | -10.9 | SL_HIT | 0.0 | 10.9 | 0.0 | 0.0 | 1 | no_go |
| 12 | 5a0bbc10-dac | 2026-05-20T16:21:14.872334+00:00 | 2026-05-20T16:37:07.369370+00:00 | -4.3 | SIGNAL_REVERSE | 0.0 | 9.1 | 0.0 | 0.0 | 1 | no_go |
| 13 | 45dbebc6-7ac | 2026-05-21T18:46:38.375114+00:00 | 2026-05-21T18:52:15.213917+00:00 | -12.8 | SL_HIT | 0.0 | 12.8 | 0.8 | 0.3 | 1 | moderate_trend |
| 14 | 0a4aef76-0b9 | 2026-05-25T00:31:38.749627+00:00 | 2026-05-25T04:31:38.924857+00:00 | -1.5 | TIME_DECAY_EXIT | 1.1 | 3.7 | 0.0 | 0.0 | 1 | no_go |
| 15 | a888fad5-3b2 | 2026-05-25T00:31:49.384742+00:00 | 2026-05-25T04:31:49.670517+00:00 | -1.0 | TIME_DECAY_EXIT | 1.1 | 3.7 | 0.0 | 0.0 | 1 | no_go |
| 16 | 36141cfc-e4a | 2026-05-25T21:31:26.440598+00:00 | 2026-05-25T21:37:02.489803+00:00 | -5.6 | SL_HIT | 0.0 | 5.6 | 0.0 | 0.0 | 1 | no_go |
| 17 | 46d02c98-9e7 | 2026-05-25T21:31:40.903067+00:00 | 2026-05-25T21:37:02.486173+00:00 | -5.6 | SL_HIT | 0.0 | 5.6 | 0.0 | 0.0 | 1 | no_go |
| 18 | b77cfac7-01d | 2026-05-25T21:39:04.584808+00:00 | 2026-05-25T22:00:00.597590+00:00 | -6.6 | SL_HIT | 1.2 | 6.6 | 0.0 | 0.0 | 1 | no_go |
| 19 | a371428e-6e6 | 2026-05-25T21:39:19.547595+00:00 | 2026-05-25T22:00:00.273172+00:00 | -6.2 | SL_HIT | 1.2 | 6.2 | 0.0 | 0.0 | 1 | no_go |
| 20 | 2f2206cf-ae8 | 2026-05-25T21:46:42.978877+00:00 | 2026-05-25T22:00:00.269664+00:00 | -8.2 | SL_HIT | 0.0 | 8.2 | 0.0 | 0.0 | 1 | no_go |
| 21 | e166220f-5bf | 2026-05-25T21:46:54.588692+00:00 | 2026-05-25T22:00:00.262135+00:00 | -8.2 | SL_HIT | 0.0 | 8.2 | 0.0 | 0.0 | 1 | no_go |
| 22 | 93b558e1-381 | 2026-05-25T21:49:53.634280+00:00 | 2026-05-25T22:00:00.254672+00:00 | -9.2 | SL_HIT | 0.0 | 9.2 | 0.0 | 0.0 | 1 | no_go |

Time cohort split:

| cohort | half | N | wins | WR | EV | total |
|---|---|---:|---:|---:|---:|---:|
| all | first_half | 11 | 0 | 0.0% | -11.78 | -129.6 |
| all | second_half | 11 | 0 | 0.0% | -6.29 | -69.2 |
| live | first_half | 0 | 0 | 0.0% | 0.00 | 0.0 |
| live | second_half | 1 | 0 | 0.0% | -20.40 | -20.4 |
| shadow | first_half | 10 | 0 | 0.0% | -10.92 | -109.2 |
| shadow | second_half | 11 | 0 | 0.0% | -6.29 | -69.2 |

Rule 1 verdict for USD_JPY/SELL:

| condition | required | observed | pass |
|---|---|---|---|
| live N | `>=24` | 1 | no |
| Wilson_bf_lo | `>=0.50` | 0.000 | no |
| avg_pips | `>=+0.5` | -20.40 | no |
| time-cohort WR | both halves `>=50%` | live only 1 trade, loser | no |
| TP ratio | `>=25%` | 0/1 = 0% | no |

Result: `REJECT` for USD_JPY/SELL single-cell revival under current production data.

### Phase D: GBP_USD TP reach analysis

The requested `TP 0 / SL 37` cohort is not present in current data. Current `sr_break_retest GBP_USD` has `N=79`: live 3, shadow 76. Normalized TP counts are non-zero.

| cohort | N | wins | WR | EV | total | Wilson_bf_lo | normalized TP/SL/MC | avg TP dist | avg MFE | avg MFE/TP |
|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|
| all | 79 | 25 | 31.6% | -1.50 | -118.8 | 0.176 | 19/36/0 | 16.95 | 5.13 | 0.353 |
| live | 3 | 2 | 66.7% | +6.07 | +18.2 | 0.099 | 2/1/0 | 16.00 | 10.03 | 0.688 |
| shadow | 76 | 23 | 30.3% | -1.80 | -137.0 | 0.163 | 17/35/0 | 16.99 | 4.94 | 0.340 |

Interpretation:

- Current shadow GBP_USD still shows a structural reach problem: average MFE/TP is 0.340, below the 0.5 threshold. Many trades do not travel half the required TP distance before adverse/exit.
- Current live GBP_USD does not reproduce the `TP 0/37` failure. It has only 3 trades, 2 winners, and normalized TP ratio 66.7%. This is too small to approve, but it contradicts the supplied failure cohort.
- The structural concern remains valid for shadow simulation, not for current live proof.

### Phase E: shadow vs live divergence

USD_JPY/SELL current divergence check:

| cohort | N | wins | WR | EV | total | avg_entry | avg_spread | avg_MFE | avg_MAE | entry range |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| live | 1 | 0 | 0.0% | -20.40 | -20.4 | 158.00200 | 0.800 | 3.50 | 20.40 | 2026-04-08 only |
| shadow | 21 | 0 | 0.0% | -8.50 | -178.4 | 158.47452 | 0.381 | 1.25 | 9.26 | 2026-04-07 to 2026-05-25 |

Rule 3 requires shadow WR < 30% and live WR > 50%. Current data has shadow WR 0.0% and live WR 0.0%, so simulator divergence is not confirmed. Instead, the supplied 26-trade profitable live cohort is absent/stale/not strategy-filtered under the current production API view.

Audit join evidence for USD_JPY/SELL:

| trade_id | shadow | pips | close | bridge_status | block_reason | is_live | units |
|---|---:|---:|---|---|---|---|---:|
| 35f755b1-b15 | 1 | -24.7 | SL_HIT |  |  |  |  |
| 35f3fdb8-d40 | 1 | -22.4 | SL_HIT |  |  |  |  |
| 51355bf2-6cc | 0 | -20.4 | SL_HIT | sent |  | True | 1000 |
| ac2f7097-7a1 | 1 | 0.0 | SIGNAL_REVERSE | skipped | shadow_tracking | False | 1000 |
| aa654334-266 | 1 | -19.7 | SL_HIT | skipped | shadow_tracking | False | 1000 |
| 08c9166e-945 | 1 | -9.0 | SL_HIT | skipped | shadow_tracking | False | 1000 |
| 6f35eda6-b27 | 1 | -7.2 | SL_HIT | skipped | shadow_tracking | False | 1000 |
| 9e30532c-675 | 1 | -6.5 | SL_HIT | skipped | shadow_tracking | False | 1000 |
| 71f76e8a-3c4 | 1 | -7.1 | SL_HIT | skipped | shadow_tracking | False | 1000 |
| df89638b-f4d | 1 | -1.7 | SIGNAL_REVERSE | skipped | shadow_tracking | False | 1000 |
| 45dbebc6-7ac | 1 | -12.8 | SL_HIT | skipped | shadow_tracking | False | 1000 |
| 0a4aef76-0b9 | 1 | -1.5 | TIME_DECAY_EXIT | skipped | shadow_tracking | False |  |
| a888fad5-3b2 | 1 | -1.0 | TIME_DECAY_EXIT | skipped | shadow_tracking | False |  |
| 36141cfc-e4a | 1 | -5.6 | SL_HIT | skipped | shadow_tracking | False |  |
| 46d02c98-9e7 | 1 | -5.6 | SL_HIT | skipped | shadow_tracking | False |  |
| b77cfac7-01d | 1 | -6.6 | SL_HIT | skipped | shadow_tracking | False |  |
| a371428e-6e6 | 1 | -6.2 | SL_HIT | skipped | shadow_tracking | False |  |
| 2f2206cf-ae8 | 1 | -8.2 | SL_HIT | skipped | shadow_tracking | False |  |
| e166220f-5bf | 1 | -8.2 | SL_HIT | skipped | shadow_tracking | False |  |
| 93b558e1-381 | 1 | -9.2 | SL_HIT | skipped | shadow_tracking | False |  |

Rows without audit joins are older than, or missing from, the retained `oanda_audit` rows; this does not affect the outcome stats because `demo_trades` contains the closed outcome.

### Repro SQL / API-equivalent checks

If direct Render disk access is available, rerun the supplied SQL against:

```sh
sqlite3 'file:/var/data/demo_trades.db?mode=ro' -readonly
```

Also verify whether the claimed 82-trade table came from `oanda_trades`, a stale snapshot, or a non-strategy-filtered `/api/oanda/stats` response. In the current code, a strategy filter for `/api/oanda/stats` would need to be added before that endpoint can support `?strategy=sr_break_retest`.

### Recommend

Decision: keep `sr_break_retest` rejected / FORCE_DEMOTED. Do not revive USD_JPY/SELL.

Reasons:

- Current live USD_JPY/SELL is `N=1`, not `N=26`.
- Current live USD_JPY/SELL is 0/1, `EV=-20.4p`, `Wilson_bf_lo=0.000`.
- Current shadow USD_JPY/SELL is also 0/21, `EV=-8.50p`.
- No `instrument x direction x is_shadow` cell has `Wilson_bf_lo > 0.50`.
- Current data does not satisfy simulator bug Rule 3 because live WR is not >50%.

Config/env points if a future verified cohort supports shadow-only revival:

- Existing shadow gate for this redesign lives at `strategies/daytrade/__init__.py:399-401`:
  - `SR_BREAK_RETEST_REDESIGN_V2=1`
  - `SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE=1`
- There is no current edge-cell entry for `sr_break_retest` in `modules/edge_cell_promote.py:32-45`. A USD_JPY/SELL-only direct cell would need a new `EdgeCell(... {"strategy": "sr_break_retest", "symbol": "USD_JPY", "direction": "SELL"})`, but this should not be added from current evidence.
- `/api/oanda/stats` strategy filtering is absent at `app.py:13907-13947`; if users rely on `?strategy=...`, add and test an explicit strategy parameter in `get_oanda_stats`/route before using that endpoint for per-strategy forensic decisions.

Simulator bug path:

1. First restore/reproduce the missing cohort: prove `USD_JPY/SELL live N=26` from either a DB snapshot or a corrected strategy-filtered broker query.
2. If reproduced, join `demo_trades.oanda_trade_id`/`oanda_audit.oanda_trade_id` and compare identical entry timestamps against shadow records.
3. Only escalate R3 simulator hot-fix if the same cohort satisfies: shadow WR <30%, live WR >50%, and time-cohort halves remain stable.

Archive memo for next session:

- Current production DB view rejects the original premise. The old 82-trade demo table is likely stale, from a different DB snapshot, or from `/api/oanda/stats?strategy=sr_break_retest` where `strategy` was ignored.
- Do not change live tier, force-demote config, `.env`, OANDA settings, or edge-cell config from this audit.
