# Kalman/ZZ Zero-Fire Local Probe 2026-06-02

Window: 2026-05-27 through 2026-06-02 UTC. Today fixed at `pd.Timestamp('2026-06-02')`.

## Kalman D7 USDJPY M15
ERROR: no bars in requested window 2026-05-27..2026-06-02 (cache last=2026-04-28 08:45:00+00:00)
| first_filter_failed | bars_count (%) |
|---|---:|
| po_up_not_started | 0 (0.0%) |
| dist_out_of_range | 0 (0.0%) |
| gap_too_wide | 0 (0.0%) |
| atr_outside_q2q4 | 0 (0.0%) |
| rsi_overbought | 0 (0.0%) |
| session_excluded | 0 (0.0%) |
| ALL_PASS | 0 (0.0%) |

Latest rejection rows:
_No rows._

## ZZ Pivot v60 EUR_USD M15
| first_filter_failed | bars_count (%) |
|---|---:|
| tf_or_pair_miss | 0 (0.0%) |
| df_too_short | 148 (35.7%) |
| no_trend | 0 (0.0%) |
| no_peak_no_trough | 264 (63.8%) |
| rr_below_min | 0 (0.0%) |
| ALL_PASS | 2 (0.5%) |

Latest rejection rows:
| timestamp | close | ema50 | atr | bbp_b | rci | atr_ratio | hour_utc |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-06-02T06:45:00+00:00 | 1.16503 | 1.163637 | 0.000509 | 1.045907 | 68.333333 | 0.871014 | 6 |
| 2026-06-02T07:00:00+00:00 | 1.16463 | 1.163676 | 0.000516 | 0.837425 | 73.333333 | 0.884172 | 7 |
| 2026-06-02T07:15:00+00:00 | 1.16467 | 1.163715 | 0.000512 | 0.817444 | 68.333333 | 0.879489 | 7 |
| 2026-06-02T07:30:00+00:00 | 1.16483 | 1.163759 | 0.000511 | 0.844844 | 58.333333 | 0.880178 | 7 |
| 2026-06-02T07:45:00+00:00 | 1.16477 | 1.163798 | 0.000506 | 0.793035 | 33.333333 | 0.87368 | 7 |

## Code-Level Cross-Check
- No additional silent-drop path identified after candidate receipt for these strategies outside the known fixes.
- Pre-trade shared `_block()` returns at `modules/demo_trader.py:3463` only increment in-memory block counters; they do not write `oanda_audit`/`shadow_audit`, but they also occur before trade creation/OANDA routing.
- Kalman LIVE bypass is explicit at `modules/demo_trader.py:5444` and `modules/demo_trader.py:5455`; ZZ EUR DT mode bypass is whitelisted at `modules/demo_trader.py:7622`.
- Post-promotion Kelly/MC blocks write `oanda_audit` at `modules/demo_trader.py:5632` and `modules/demo_trader.py:5656`; post-gate escalation persists shadow at `modules/demo_trader.py:5670`.

## Verdict
| Strategy | Bars in 7d | Filter pass count | First-fail top-2 | Verdict |
|---|---:|---:|---|---|
| kalman_d7_trail_atr | 0 | 0 | none | INCONCLUSIVE |
| zz_pivot_v60_sr / zz_pivot_v60_sr_lo | 414 | 2 | no_peak_no_trough=264, df_too_short=148 | SILENT_DROP_V3_SUSPECTED |

Kalman D7: local USDJPY cache cannot test the deployment window because the parquet has no bars in the fixed 7-day window. Verdict is inconclusive until the M15 cache is refreshed through 2026-06-02.

ZZ Pivot v60: the local EURUSD window is populated, but first-fail distribution is dominated by `no_peak_no_trough`. The strategy produced 2 bar-level passes under the ported detector.

Root-cause hypothesis: Kalman is blocked by stale local cache evidence; ZZ zero-fire is primarily strategy-filter scarcity unless any ALL_PASS rows failed to appear in audits.
