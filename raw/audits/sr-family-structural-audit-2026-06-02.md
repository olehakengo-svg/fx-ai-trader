# SR Family Structural Audit - 2026-06-02

- Generated: 2026-06-02T18:10:00Z
- Source audit API: `https://fx-ai-trader.onrender.com/api/oanda/audit?limit=10000` -> rows=7314, total=7314
- Source trades API: `https://fx-ai-trader.onrender.com/api/demo/trades?status=closed&limit=10000&date_from=2026-04-08` -> closed rows=7732, count=7732
- Note: direct SSH/SQLite access to `/var/data/demo_trades.db` was not available in this Codex container (`ssh` and `sqlite3` not in PATH), so `evaluated_candidates` is not reproduced here. Production `oanda_audit` and `demo_trades` are fresh Render API reads.

## Step 2 API Equivalents

### 2a liquidity historical presence

| source | count |
|---|---:|
| oanda_audit entry_type = sr_liquidity_grab | 0 |
| demo_trades entry_type = sr_liquidity_grab (closed API slice) | 0 |
| oanda_audit entry_type LIKE %liquidity% | 15 |
| demo_trades entry_type LIKE %liquidity% (closed API slice) | 19 |
| evaluated_candidates strategy/entry LIKE %liquidity% | BLOCKED_NO_SSH_SQLITE |

The `LIKE %liquidity%` counts are not `sr_liquidity_grab`; they come from other liquidity-named strategies in the production API slice. The exact target strategy remains absent.

### 2b weighted recent fire distribution

| entry_type | instrument | direction | count | latest_ts |
|---|---|---|---:|---|
| sr_weighted_bounce | USD_JPY | SELL | 4 | 2026-05-25T15:47:01.858613+00:00 |
| sr_weighted_bounce | USD_JPY | BUY | 3 | 2026-05-29T03:46:45.695045+00:00 |
| sr_weighted_bounce | EUR_JPY | BUY | 1 | 2026-05-26T02:01:11.548555+00:00 |
| sr_weighted_bounce | GBP_JPY | BUY | 1 | 2026-05-20T15:03:49.059604+00:00 |
| sr_weighted_break | GBP_JPY | BUY | 8 | 2026-05-28T19:01:59.072217+00:00 |
| sr_weighted_break | USD_JPY | SELL | 3 | 2026-05-25T21:46:54.685202+00:00 |
| sr_weighted_break | GBP_USD | SELL | 2 | 2026-05-29T08:47:01.044025+00:00 |

### 2c sr_break_retest sr_strength state

| strength_state | n | min_ts | max_ts |
|---|---:|---|---|
| NULL | 250 | 2026-04-08T13:16:36.885389+00:00 | 2026-06-02T14:23:18.469729+00:00 |
| POP | 1 | 2026-05-29T00:01:16.620159+00:00 | 2026-05-29T00:01:16.620159+00:00 |

### 2d SR audit population by strategy

| entry_type | n_total | n_populated | populated_pct |
|---|---:|---:|---:|
| sr_channel_reversal | 523 | 66 | 12.6% |
| sr_fib_confluence | 443 | 138 | 31.2% |
| sr_break_retest | 251 | 1 | 0.4% |
| dt_sr_channel_reversal | 151 | 39 | 25.8% |
| sr_anti_hunt_bounce | 88 | 72 | 81.8% |
| sr_weighted_break | 13 | 13 | 100.0% |
| sr_weighted_bounce | 9 | 9 | 100.0% |

## Pre-registered Shadow Metrics

Closed `demo_trades` rows where `is_shadow=1`, joined to `oanda_audit` by `trade_id`/`demo_trade_id`.

| strategy | N | WR | EV | PF | Wilson_lo | Kelly | total_pip | post_2026_05_27_N |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| sr_anti_hunt_bounce | 151 | 17.9% | -3.81 | 0.46 | 0.126 | 0.000 | -574.6 | 11 |
| sr_fib_confluence | 543 | 21.7% | -4.04 | 0.50 | 0.185 | 0.000 | -2194.7 | 72 |
| sr_break_retest | 306 | 24.5% | -2.74 | 0.56 | 0.200 | 0.000 | -837.1 | 55 |
| sr_liquidity_grab | 0 | 0.0% | NA | NA | NA | 0.000 | NA | 0 |
| sr_channel_reversal | 488 | 20.7% | -1.29 | 0.54 | 0.173 | 0.000 | -631.4 | 41 |
| dt_sr_channel_reversal | 139 | 35.3% | -0.22 | 0.95 | 0.278 | 0.000 | -30.8 | 14 |
| sr_weighted_bounce | 13 | 0.0% | -3.62 | 0.00 | 0.000 | 0.000 | -47.0 | 1 |
| sr_weighted_break | 23 | 17.4% | -3.53 | 0.40 | 0.070 | 0.000 | -81.3 | 10 |

## sr_anti_hunt_bounce Strength Split

| bucket | N | WR | EV | PF | Wilson_lo | Kelly | total_pip |
|---|---:|---:|---:|---:|---:|---:|---:|
| strong(sr_strength>=0.7) | 49 | 26.5% | 4.92 | 4.24 | 0.162 | 0.203 | 241.1 |
| weak(sr_strength<0.7) | 21 | 14.3% | -12.35 | 0.15 | 0.050 | 0.000 | -259.4 |
| NULL | 81 | 13.6% | -6.87 | 0.20 | 0.078 | 0.000 | -556.3 |

Top populated anti-hunt cells (N>=3, sorted by EV):

| instrument | direction | sr_strength_bin | N | WR | EV | Wilson_lo | total_pip |
|---|---|---|---:|---:|---:|---:|---:|
| EUR_JPY | BUY | [0.85,1.0] | 13 | 100.0% | 24.27 | 0.772 | 315.5 |
| USD_JPY | SELL | [0.85,1.0] | 19 | 0.0% | -1.76 | 0.000 | -33.5 |
| GBP_JPY | BUY | [0.5,0.65) | 4 | 0.0% | -2.38 | 0.000 | -9.5 |
| USD_JPY | BUY | [0.85,1.0] | 6 | 0.0% | -2.47 | 0.000 | -14.8 |
| EUR_USD | BUY | [0,0.5) | 4 | 0.0% | -13.77 | 0.000 | -55.1 |
| EUR_USD | SELL | [0.65,0.75) | 8 | 0.0% | -28.52 | 0.000 | -228.2 |

## Hypothesis Verdicts

| defect | verdict | evidence | next action |
|---|---|---|---|
| #1 sr_liquidity_grab total silence | NEEDS_MORE_DATA_SIGNAL_PATH | Env was reported set by commander; registry import/instantiation exists locally; production API still has 0 exact `sr_liquidity_grab` audit/demo rows; evaluated_candidates SQL is blocked here. | Deploy V2 diagnostics and run 24h paper replay; if `called>0` and `candidate=0`, inspect signal filters; if `called=0`, scheduler/registry runtime bug. |
| #2 sr_weighted_bounce/break wave-1 silence | NEEDS_MORE_DATA_DETECTOR_GATE | Production audit has bounce=9 latest=2026-05-29T03:46:45.695045+00:00; break=13 latest=2026-05-29T08:47:01.044025+00:00; no rows after 2026-05-29 in current API. | Deploy bucketed diagnostics; do not tune thresholds until detector-empty vs K/percentile/post-weight rejection is measured. |
| #3 sr_break_retest SR metadata gap | CONFIRMED_STRATEGY_METADATA_WIRING | Production API: sr_break_retest audit rows=251, populated=1, NULL=250. Bridge/DB already write metadata when `Candidate.sr_meta` exists. | Fixed on feature branch by adding `Candidate.sr_meta_from_price(...)` to `sr_break_retest`; unit test added. |

## Non-defect Quant Findings

- `sr_anti_hunt_bounce` remains the only SR family member showing clear strong/weak discrimination in this production API extract. The exact counts differ from the commander snapshot because this report was regenerated later on 2026-06-02, but the direction is preserved when comparing populated strong rows to weak/NULL rows.
- Other SR strategies still do not show a comparable strong/weak discriminator in this artifact; this remains consistent with the Phase 2 NULL verdict for those designs.
