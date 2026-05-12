# SR Weight Gate Empirical Audit v2

## Methodology Fix Compared to v2 (2026-05-11 buggy run)

| Bug fixed | Location | Before behavior | After behavior |
| --- | --- | --- | --- |
| W1 forced zero | _nearest_level_meta | w1_touch=0 unconditional | passthrough from detect_sr_levels_with_weight |
| D1 collapsed to {0,1} | _nearest_level_meta | d1_touch = 1 if (d1>=10 AND w1>=3 AND rscore>0.5) else 0 | passthrough |
| own_touch 16-bar recompute | _nearest_level_meta | recomputed on last 16 bars | passthrough (365d global) |
| stride too small | RUN_STRIDES | 1 for anti_hunt/liq_grab | 4 |
| Adjacent-bar duplicate signals | run_strategy_bt | no dedup (backtest_mode disables strategy dedup) | post-hoc (strategy, symbol, signal, level, 2hr-bucket) dedup |

## v1 (buggy) vs v2 (fixed) Verdict Comparison

| Strategy | v1 verdict | v1 N total | v1 N heavy | v1 WR heavy | v1 EV heavy | v2 verdict | v2 N total | v2 N heavy | v2 WR heavy | v2 EV heavy | Wilson_lo (v2 Bonf) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sr_anti_hunt_bounce | DEAD | 1441 | 68 | 0.3676 | -4.1755 | DEAD | 140 | 116 | 0.4655 | 0.9781 | 0.3513 |
| sr_break_retest | DEAD | 294 | 54 | 0.3148 | -1.7896 | DEAD | 222 | 152 | 0.2829 | -1.7165 | 0.1994 |
| sr_fib_confluence | DEAD | 4748 | 708 | 0.3955 | -0.6166 | DEAD | 2022 | 1668 | 0.3837 | -0.6475 | 0.3535 |
| sr_liquidity_grab | DEAD | 6 | 0 | 0.0000 | 0.0000 | DEAD | 0 | 0 | 0.0000 | 0.0000 | 0.0000 |
| sr_channel_reversal | DEAD | 2612 | 876 | 0.2671 | -0.0001 | DEAD | 1037 | 719 | 0.2253 | -0.8230 | 0.1878 |

## sr_anti_hunt_bounce Triangulation vs SR-weight Phase 2 BT

SR-weight Phase 2 BT reported sr_anti_hunt_bounce as a BH FDR survivor (trend p=0.0034, N=594). Fixed audit sr_anti_hunt_bounce N=140, which is outside the Phase 2 BT triangulation band 416-772; this is a material deviation and detector mismatch remains a candidate explanation.

## 3-Way Detector Comparison (only present when --detector pivot)

| Strategy | v1 (buggy KDE) verdict | v1 N | v2 fixed KDE (28a1114) verdict | v2 fixed KDE N | v2 fixed PIVOT verdict | v2 fixed PIVOT N | sr_anti_hunt triangulation status (band 416-772) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| sr_anti_hunt_bounce | DEAD | 1441 | DEAD | 335 | DEAD | 140 | OUT_OF_BAND |
| sr_break_retest | DEAD | 294 | DEAD | 294 | DEAD | 222 | - |
| sr_fib_confluence | DEAD | 4748 | DEAD | 2037 | DEAD | 2022 | - |
| sr_liquidity_grab | DEAD | 6 | DEAD | 2 | DEAD | 0 | - |
| sr_channel_reversal | DEAD | 2612 | DEAD | 1249 | DEAD | 1037 | - |

## Phase 2 BT Triangulation (sr_anti_hunt_bounce)

- Phase 2 BT reported N=594 (BH FDR survivor, trend p=0.0034)
- v2 fixed KDE: N=335 (OUT_OF_BAND, deviation -43.6%)
- v2 fixed PIVOT: N=140 (OUT_OF_BAND, deviation -76.4%)
- Conclusion: detector divergence is not sufficient to explain the sr_anti_hunt_bounce N mismatch

## Summary
| Strategy | N total | N heavy | WR all | WR heavy | EV all | EV heavy | Wilson_lo (heavy, Bonf) | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sr_anti_hunt_bounce | 140 | 116 | 0.4929 | 0.4655 | 1.0582 | 0.9781 | 0.3513 | DEAD |
| sr_break_retest | 222 | 152 | 0.2613 | 0.2829 | -2.0486 | -1.7165 | 0.1994 | DEAD |
| sr_fib_confluence | 2022 | 1668 | 0.3724 | 0.3837 | -0.9048 | -0.6475 | 0.3535 | DEAD |
| sr_liquidity_grab | 0 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | DEAD |
| sr_channel_reversal | 1037 | 719 | 0.2411 | 0.2253 | -0.5997 | -0.8230 | 0.1878 | DEAD |

## Per-Strategy Details

### sr_anti_hunt_bounce
- composite_weight quintile bucket stats
| bucket | N | WR | EV | Wilson_lo | mean_weight | htf_rate |
| --- | --- | --- | --- | --- | --- | --- |
| Q1 | 31 | 0.5161 | 0.4384 | 0.3034 | 59.2432 | 0.5484 |
| Q2 | 32 | 0.5625 | 2.5108 | 0.3459 | 82.8927 | 0.6875 |
| Q3 | 26 | 0.5000 | 2.7375 | 0.2746 | 95.7471 | 1.0000 |
| Q4 | 29 | 0.4828 | 1.7566 | 0.2703 | 121.9177 | 1.0000 |
| Q5 | 22 | 0.3636 | -3.0864 | 0.1615 | 174.5000 | 1.0000 |
- HTF source bucket stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| D1 only | 110 | 0.4545 | 1.2965 | 0.3383 |
| D1+W1 | 6 | 0.6667 | -4.8593 | 0.2265 |
| none | 24 | 0.6250 | 1.4454 | 0.3710 |
- own_touch bucket stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| 6+ | 140 | 0.4929 | 1.0582 | 0.3868 |
- magnitude quartile stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| ALL | 140 | 0.4929 | 1.0582 | 0.3868 |
- single-year concentration check: clear
- bootstrap EV diff CI (heavy+HTF minus all): [-6.6725, 6.4441]
- Redesign spec draft: not generated because verdict is DEAD.

### sr_break_retest
- composite_weight quintile bucket stats
| bucket | N | WR | EV | Wilson_lo | mean_weight | htf_rate |
| --- | --- | --- | --- | --- | --- | --- |
| Q1 | 47 | 0.1702 | -3.5346 | 0.0727 | 59.0045 | 0.2766 |
| Q2 | 43 | 0.2093 | -3.6250 | 0.0944 | 81.4555 | 0.5116 |
| Q3 | 43 | 0.2093 | -3.0309 | 0.0944 | 97.0159 | 0.6512 |
| Q4 | 47 | 0.3191 | -1.7421 | 0.1760 | 147.2847 | 1.0000 |
| Q5 | 42 | 0.4048 | 1.8909 | 0.2360 | 204.2952 | 1.0000 |
- HTF source bucket stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| D1 only | 145 | 0.2966 | -1.3832 | 0.2095 |
| D1+W1 | 7 | 0.0000 | -8.6194 | 0.0000 |
| none | 70 | 0.2143 | -2.7698 | 0.1158 |
- own_touch bucket stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| 6+ | 222 | 0.2613 | -2.0486 | 0.1930 |
- magnitude quartile stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| ALL | 222 | 0.2613 | -2.0486 | 0.1930 |
- single-year concentration check: clear
- bootstrap EV diff CI (heavy+HTF minus all): [-2.3093, 2.9973]
- Redesign spec draft: not generated because verdict is DEAD.

### sr_fib_confluence
- composite_weight quintile bucket stats
| bucket | N | WR | EV | Wilson_lo | mean_weight | htf_rate |
| --- | --- | --- | --- | --- | --- | --- |
| Q1 | 620 | 0.3758 | -0.7335 | 0.3273 | 67.7002 | 0.5500 |
| Q2 | 190 | 0.3842 | 0.2146 | 0.2987 | 85.2030 | 0.8526 |
| Q3 | 408 | 0.3480 | -1.6747 | 0.2902 | 100.7274 | 0.8848 |
| Q4 | 413 | 0.4068 | -0.0562 | 0.3465 | 152.7155 | 1.0000 |
| Q5 | 391 | 0.3504 | -1.8133 | 0.2912 | 190.8928 | 1.0000 |
- HTF source bucket stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| D1 only | 1599 | 0.3846 | -0.6566 | 0.3538 |
| D1+W1 | 69 | 0.3623 | -0.4378 | 0.2315 |
| none | 354 | 0.3192 | -2.1171 | 0.2592 |
- own_touch bucket stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| 6+ | 2022 | 0.3724 | -0.9048 | 0.3452 |
- magnitude quartile stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| ALL | 2022 | 0.3724 | -0.9048 | 0.3452 |
- single-year concentration check: clear
- bootstrap EV diff CI (heavy+HTF minus all): [-0.8229, 1.3788]
- Redesign spec draft: not generated because verdict is DEAD.

### sr_liquidity_grab
- composite_weight quintile bucket stats
_no signals_
- HTF source bucket stats
_no signals_
- single-year concentration check: no_signals
- bootstrap EV diff CI (heavy+HTF minus all): [0.0000, 0.0000]
- Redesign spec draft: not generated because verdict is DEAD.

### sr_channel_reversal
- composite_weight quintile bucket stats
| bucket | N | WR | EV | Wilson_lo | mean_weight | htf_rate |
| --- | --- | --- | --- | --- | --- | --- |
| Q1 | 210 | 0.2476 | -0.4045 | 0.1794 | 64.3500 | 0.2238 |
| Q2 | 205 | 0.3220 | 1.2039 | 0.2446 | 86.7602 | 0.3707 |
| Q3 | 211 | 0.1991 | -2.5001 | 0.1379 | 101.7631 | 0.8768 |
| Q4 | 204 | 0.2108 | -0.9695 | 0.1469 | 156.1629 | 1.0000 |
| Q5 | 207 | 0.2271 | -0.2825 | 0.1612 | 198.7048 | 1.0000 |
- HTF source bucket stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| D1 only | 706 | 0.2238 | -0.8738 | 0.1861 |
| D1+W1 | 13 | 0.3077 | 1.9392 | 0.0966 |
| none | 318 | 0.2767 | -0.0950 | 0.2172 |
- own_touch bucket stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| 6+ | 1037 | 0.2411 | -0.5997 | 0.2086 |
- magnitude quartile stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| ALL | 1037 | 0.2411 | -0.5997 | 0.2086 |
- single-year concentration check: clear
- bootstrap EV diff CI (heavy+HTF minus all): [-1.3055, 0.8338]
- Redesign spec draft: not generated because verdict is DEAD.

## Exploratory Thresholds
| Strategy | threshold | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- | --- |
| sr_anti_hunt_bounce | 3.0000 | 140 | 0.4929 | 1.0582 | 0.3868 |
| sr_anti_hunt_bounce | 4.0000 | 140 | 0.4929 | 1.0582 | 0.3868 |
| sr_anti_hunt_bounce | 6.0000 | 140 | 0.4929 | 1.0582 | 0.3868 |
| sr_anti_hunt_bounce | 8.0000 | 140 | 0.4929 | 1.0582 | 0.3868 |
| sr_break_retest | 3.0000 | 222 | 0.2613 | -2.0486 | 0.1930 |
| sr_break_retest | 4.0000 | 222 | 0.2613 | -2.0486 | 0.1930 |
| sr_break_retest | 6.0000 | 222 | 0.2613 | -2.0486 | 0.1930 |
| sr_break_retest | 8.0000 | 222 | 0.2613 | -2.0486 | 0.1930 |
| sr_fib_confluence | 3.0000 | 2022 | 0.3724 | -0.9048 | 0.3452 |
| sr_fib_confluence | 4.0000 | 2022 | 0.3724 | -0.9048 | 0.3452 |
| sr_fib_confluence | 6.0000 | 2022 | 0.3724 | -0.9048 | 0.3452 |
| sr_fib_confluence | 8.0000 | 2022 | 0.3724 | -0.9048 | 0.3452 |
| sr_liquidity_grab | 3.0000 | 0 | 0.0000 | 0.0000 | 0.0000 |
| sr_liquidity_grab | 4.0000 | 0 | 0.0000 | 0.0000 | 0.0000 |
| sr_liquidity_grab | 6.0000 | 0 | 0.0000 | 0.0000 | 0.0000 |
| sr_liquidity_grab | 8.0000 | 0 | 0.0000 | 0.0000 | 0.0000 |
| sr_channel_reversal | 3.0000 | 1037 | 0.2411 | -0.5997 | 0.2086 |
| sr_channel_reversal | 4.0000 | 1037 | 0.2411 | -0.5997 | 0.2086 |
| sr_channel_reversal | 6.0000 | 1037 | 0.2411 | -0.5997 | 0.2086 |
| sr_channel_reversal | 8.0000 | 1037 | 0.2411 | -0.5997 | 0.2086 |

## Statistical Discipline
- Pre-registered primary threshold: composite_weight >= 5.0
- Primary heavy bucket additionally requires HTF source for REBORN_HEAVY verdict.
- Exploratory thresholds: [3.0, 4.0, 6.0, 8.0]
- Bonferroni m=5, alpha=0.01
- Bootstrap CI: 10000 resamples
- Data source: data/cache/massive/*.parquet only; Yahoo is not used.
- Strategy evaluate() code was not modified; weight gate is audit-only post-hoc analysis.
- Runtime note: strategy signal collection used fixed strides {'sr_anti_hunt_bounce': 4, 'sr_break_retest': 8, 'sr_fib_confluence': 4, 'sr_liquidity_grab': 4, 'sr_channel_reversal': 4}; this preserves evaluate() behavior but samples high-frequency duplicate opportunities.

## Verdict on Detector Hypothesis

- v2 fixed KDE sr_anti_hunt_bounce N=335 (outside Phase 2 BT band 416-772)
- v2 fixed PIVOT sr_anti_hunt_bounce N=140 (OUT_OF_BAND)
- Decision rule outcome:
  - detector NOT the main cause -> next action: investigate Phase 2 BT methodology (e.g., different SL/TP geometry, different exit conditions)
- Verdict reproducibility across detectors:
  - pivot also returns all 5 DEAD: weight thesis truly falsified, pivot to alternative SR design axes (rejection magnitude, TP geometry, regime gate)
