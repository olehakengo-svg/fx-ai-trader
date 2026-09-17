# S6 Wave 2b Pre-registration BT — Top-3 London_NY Overlap Candidates

**Date**: 2026-05-04  
**Rule**: R1 Slow & Strict  
**Scope**: USD_JPY M5, W2a top-3 diagnostic candidates only  
**Input**: `data/chart_patterns.db` frozen `chart_pattern_signals`; `data/cache/massive/USD_JPY_5m.parquet`  
**Verdict**: No PROMOTE / SHADOW. No LIVE / Shadow exposure.

## Locked Candidates

| ID | Cell | Pattern ID | Main OOS_1 verdict |
|---|---|---:|---|
| C1 | triple_bottom x London_NY_overlap x rr=1.25 | 8 | INSUFFICIENT |
| C2 | triple_top x London_NY_overlap x rr=1.25 | 11 | INSUFFICIENT |
| C3 | inverse_head_shoulders x London_NY_overlap x rr=1.25 | 9 | REJECT |

`head_shoulders x BEAR regime` remains out of scope because the W2a regime axis was inconclusive.

## Execution

- Engine: `tools/s6_w2b_pre_reg_bt.py`
- Driver: `tools/s6_run_w2b.py`
- DB append tables: `chart_pattern_w2b_trades`, `chart_pattern_w2b_verdicts`
- Entry: `signal_ts + 1 bar` open
- Time filter: London_NY overlap, with both signal and next-bar entry constrained to 12-15 UTC for the locked verification query
- Spread: W2a empirical hour-of-day profile from `chart_pattern_bt_spread_profile`
- SL: frozen `chart_pattern_signals.sl_px`
- TP: recomputed from entry and SL distance at `rr=1.25`
- Max hold: 30 bars
- Intrabar ambiguity: both `SL_FIRST` and `TP_FIRST` simulated

Frozen source table counts stayed unchanged:

| Table | Count |
|---|---:|
| chart_pattern_signals | 22094 |
| chart_pattern_bt_trades | 42483 |
| chart_pattern_bt_verdicts | 26 |
| chart_pattern_w2a_diagnosis | 229 |

## Verdict Rows

| Candidate | Resolve | Split | N | WR | EV | PF | Wilson_lo | Bonf_p | Kelly | Verdict |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| C1 | SL_FIRST | OOS_1 | 9 | 0.444 | -2.96 | 0.79 | 0.189 | 0.75461 | -0.121 | INSUFFICIENT |
| C1 | SL_FIRST | WF_1 | 3 | 0.667 | 10.19 | 4.51 | 0.208 | 0.22491 | 0.519 | INSUFFICIENT |
| C1 | SL_FIRST | WF_2 | 13 | 0.692 | 7.99 | 4.09 | 0.424 | 0.01383 | 0.523 | INSUFFICIENT |
| C1 | SL_FIRST | WF_3 | 9 | 0.444 | -2.96 | 0.79 | 0.189 | 0.75461 | -0.121 | INSUFFICIENT |
| C1 | TP_FIRST | OOS_1 | 9 | 0.444 | -2.96 | 0.79 | 0.189 | 0.75461 | -0.121 | INSUFFICIENT |
| C1 | TP_FIRST | WF_1 | 3 | 0.667 | 10.19 | 4.51 | 0.208 | 0.22491 | 0.519 | INSUFFICIENT |
| C1 | TP_FIRST | WF_2 | 13 | 0.692 | 7.99 | 4.09 | 0.424 | 0.01383 | 0.523 | INSUFFICIENT |
| C1 | TP_FIRST | WF_3 | 9 | 0.444 | -2.96 | 0.79 | 0.189 | 0.75461 | -0.121 | INSUFFICIENT |
| C2 | SL_FIRST | OOS_1 | 5 | 0.600 | 13.69 | 5.84 | 0.231 | 0.06134 | 0.497 | INSUFFICIENT |
| C2 | SL_FIRST | WF_1 | 1 | 0.000 | -9.75 | 0.00 | 0.000 | 1.00000 | 0.000 | INSUFFICIENT |
| C2 | SL_FIRST | WF_2 | 5 | 0.800 | 4.76 | 2.65 | 0.376 | 0.33920 | 0.498 | INSUFFICIENT |
| C2 | SL_FIRST | WF_3 | 5 | 0.600 | 13.69 | 5.84 | 0.231 | 0.06134 | 0.497 | INSUFFICIENT |
| C2 | TP_FIRST | OOS_1 | 5 | 0.600 | 13.69 | 5.84 | 0.231 | 0.06134 | 0.497 | INSUFFICIENT |
| C2 | TP_FIRST | WF_1 | 1 | 0.000 | -9.75 | 0.00 | 0.000 | 1.00000 | 0.000 | INSUFFICIENT |
| C2 | TP_FIRST | WF_2 | 5 | 0.800 | 4.76 | 2.65 | 0.376 | 0.33920 | 0.498 | INSUFFICIENT |
| C2 | TP_FIRST | WF_3 | 5 | 0.600 | 13.69 | 5.84 | 0.231 | 0.06134 | 0.497 | INSUFFICIENT |
| C3 | SL_FIRST | OOS_1 | 58 | 0.552 | 1.91 | 1.18 | 0.425 | 0.30464 | 0.086 | REJECT |
| C3 | SL_FIRST | WF_1 | 22 | 0.500 | 2.97 | 1.48 | 0.307 | 0.23833 | 0.162 | INSUFFICIENT |
| C3 | SL_FIRST | WF_2 | 38 | 0.342 | -3.44 | 0.57 | 0.212 | 0.96729 | -0.258 | REJECT |
| C3 | SL_FIRST | WF_3 | 58 | 0.552 | 1.91 | 1.18 | 0.425 | 0.30464 | 0.086 | REJECT |
| C3 | TP_FIRST | OOS_1 | 58 | 0.552 | 1.91 | 1.18 | 0.425 | 0.30464 | 0.086 | REJECT |
| C3 | TP_FIRST | WF_1 | 22 | 0.500 | 2.97 | 1.48 | 0.307 | 0.23833 | 0.162 | INSUFFICIENT |
| C3 | TP_FIRST | WF_2 | 38 | 0.342 | -3.44 | 0.57 | 0.212 | 0.96729 | -0.258 | REJECT |
| C3 | TP_FIRST | WF_3 | 58 | 0.552 | 1.91 | 1.18 | 0.425 | 0.30464 | 0.086 | REJECT |

## Intrabar Sensitivity

No row changed between `SL_FIRST` and `TP_FIRST`; no candidate is dependent on favorable same-bar ambiguity in this run.

## Decision

W2b does not create Shadow or LIVE eligibility. C1 and C2 are sample-size failures on OOS_1 despite attractive small-N cells. C3 has enough OOS samples but fails the PF gate (`1.18 < 1.2`) and has weak WF_2 (`PF=0.57`), so it is rejected under the locked pre-registration criteria.

Recommended next task: Wave 2c regime deepdive only if local regime data can be sourced cleanly; otherwise park S6 and do not proceed to W3 sweep.
