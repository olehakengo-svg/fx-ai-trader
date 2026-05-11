# SR Weight Gate Empirical Audit v2

## Summary
| Strategy | N total | N heavy | WR all | WR heavy | EV all | EV heavy | Wilson_lo (heavy, Bonf) | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sr_anti_hunt_bounce | 1441 | 68 | 0.4379 | 0.3676 | -2.0964 | -4.1755 | 0.2352 | DEAD |
| sr_break_retest | 294 | 54 | 0.2925 | 0.3148 | -0.9291 | -1.7896 | 0.1801 | DEAD |
| sr_fib_confluence | 4748 | 708 | 0.3602 | 0.3955 | -1.0904 | -0.6166 | 0.3493 | DEAD |
| sr_liquidity_grab | 6 | 0 | 0.6667 | 0.0000 | 11.8167 | 0.0000 | 0.0000 | DEAD |
| sr_channel_reversal | 2612 | 876 | 0.2695 | 0.2671 | -0.0312 | -0.0001 | 0.2305 | DEAD |

## Per-Strategy Details

### sr_anti_hunt_bounce
- composite_weight quintile bucket stats
| bucket | N | WR | EV | Wilson_lo | mean_weight | htf_rate |
| --- | --- | --- | --- | --- | --- | --- |
| Q1 | 297 | 0.4478 | -2.0790 | 0.3754 | 2.6251 | 0.0000 |
| Q2 | 313 | 0.4537 | -1.1327 | 0.3829 | 3.1844 | 0.0000 |
| Q3 | 257 | 0.4319 | -2.2647 | 0.3550 | 3.5134 | 0.0000 |
| Q4 | 291 | 0.4296 | -3.7787 | 0.3572 | 3.7677 | 0.0000 |
| Q5 | 283 | 0.4240 | -1.2980 | 0.3510 | 5.0346 | 0.2403 |
- HTF source bucket stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| D1 only | 68 | 0.3676 | -4.1755 | 0.2352 |
| none | 1373 | 0.4414 | -1.9934 | 0.4072 |
- own_touch bucket stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| 1 | 1210 | 0.4347 | -2.2160 | 0.3985 |
| 2 | 231 | 0.4545 | -1.4701 | 0.3726 |
- magnitude quartile stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| ALL | 1441 | 0.4379 | -2.0964 | 0.4046 |
- single-year concentration check: clear
- bootstrap EV diff CI (heavy+HTF minus all): [-6.5728, 2.1390]
- Redesign spec draft: not generated because verdict is DEAD.

### sr_break_retest
- composite_weight quintile bucket stats
| bucket | N | WR | EV | Wilson_lo | mean_weight | htf_rate |
| --- | --- | --- | --- | --- | --- | --- |
| Q1 | 61 | 0.2459 | -0.8466 | 0.1337 | 2.5689 | 0.0000 |
| Q2 | 58 | 0.3103 | 0.8979 | 0.1803 | 3.1719 | 0.0000 |
| Q3 | 58 | 0.2759 | -1.2143 | 0.1538 | 3.5423 | 0.0000 |
| Q4 | 58 | 0.3448 | -0.8223 | 0.2076 | 4.2756 | 0.0172 |
| Q5 | 59 | 0.2881 | -2.6352 | 0.1640 | 6.8888 | 0.9153 |
- HTF source bucket stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| D1 only | 55 | 0.3091 | -1.8589 | 0.1766 |
| none | 239 | 0.2887 | -0.7152 | 0.2197 |
- own_touch bucket stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| 1 | 259 | 0.2973 | -0.7603 | 0.2299 |
| 2 | 35 | 0.2571 | -2.1785 | 0.1171 |
- magnitude quartile stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| ALL | 294 | 0.2925 | -0.9291 | 0.2294 |
- single-year concentration check: clear
- bootstrap EV diff CI (heavy+HTF minus all): [-3.8982, 2.3849]
- Redesign spec draft: not generated because verdict is DEAD.

### sr_fib_confluence
- composite_weight quintile bucket stats
| bucket | N | WR | EV | Wilson_lo | mean_weight | htf_rate |
| --- | --- | --- | --- | --- | --- | --- |
| Q1 | 973 | 0.3834 | -0.4734 | 0.3441 | 0.5013 | 0.0000 |
| Q2 | 929 | 0.3477 | -1.3703 | 0.3086 | 2.1342 | 0.0000 |
| Q3 | 954 | 0.3302 | -1.5999 | 0.2923 | 3.1969 | 0.0000 |
| Q4 | 944 | 0.3528 | -1.2907 | 0.3138 | 3.9040 | 0.0890 |
| Q5 | 948 | 0.3861 | -0.7373 | 0.3463 | 6.4606 | 0.7574 |
- HTF source bucket stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| D1 only | 802 | 0.3965 | -0.6762 | 0.3530 |
| none | 3946 | 0.3528 | -1.1746 | 0.3334 |
- own_touch bucket stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| 1 | 4276 | 0.3590 | -1.1559 | 0.3403 |
| 2 | 468 | 0.3697 | -0.5858 | 0.3144 |
| 3 | 4 | 0.5000 | 9.8979 | 0.1051 |
- magnitude quartile stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| ALL | 4748 | 0.3602 | -1.0904 | 0.3424 |
- single-year concentration check: clear
- bootstrap EV diff CI (heavy+HTF minus all): [-0.6419, 1.6156]
- Redesign spec draft: not generated because verdict is DEAD.

### sr_liquidity_grab
- composite_weight quintile bucket stats
| bucket | N | WR | EV | Wilson_lo | mean_weight | htf_rate |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | 6 | 0.6667 | 11.8167 | 0.2265 | 3.2351 | 0.0000 |
- HTF source bucket stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| none | 6 | 0.6667 | 11.8167 | 0.2265 |
- own_touch bucket stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| 1 | 4 | 1.0000 | 23.5750 | 0.3761 |
| 2 | 2 | 0.0000 | -11.7000 | 0.0000 |
- magnitude quartile stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| ALL | 6 | 0.6667 | 11.8167 | 0.2265 |
- single-year concentration check: clear
- bootstrap EV diff CI (heavy+HTF minus all): [0.0000, 0.0000]
- Redesign spec draft: not generated because verdict is DEAD.

### sr_channel_reversal
- composite_weight quintile bucket stats
| bucket | N | WR | EV | Wilson_lo | mean_weight | htf_rate |
| --- | --- | --- | --- | --- | --- | --- |
| Q1 | 523 | 0.2983 | 0.4452 | 0.2495 | 2.6788 | 0.0000 |
| Q2 | 526 | 0.2414 | -0.3430 | 0.1968 | 3.2153 | 0.0000 |
| Q3 | 566 | 0.2739 | -0.1375 | 0.2284 | 4.0394 | 0.0141 |
| Q4 | 480 | 0.2625 | -0.0930 | 0.2143 | 6.1115 | 0.7729 |
| Q5 | 517 | 0.2708 | -0.0224 | 0.2236 | 7.2943 | 1.0000 |
- HTF source bucket stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| D1 only | 896 | 0.2679 | 0.0301 | 0.2316 |
| none | 1716 | 0.2704 | -0.0633 | 0.2437 |
- own_touch bucket stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| 1 | 2038 | 0.2699 | 0.0429 | 0.2453 |
| 2 | 572 | 0.2675 | -0.3104 | 0.2227 |
| 3 | 2 | 0.5000 | 4.2076 | 0.0617 |
- magnitude quartile stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| ALL | 2612 | 0.2695 | -0.0312 | 0.2478 |
- single-year concentration check: clear
- bootstrap EV diff CI (heavy+HTF minus all): [-0.7230, 0.8046]
- Redesign spec draft: not generated because verdict is DEAD.

## Exploratory Thresholds
| Strategy | threshold | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- | --- |
| sr_anti_hunt_bounce | 3.0000 | 1042 | 0.4338 | -2.1417 | 0.3948 |
| sr_anti_hunt_bounce | 4.0000 | 283 | 0.4240 | -1.2980 | 0.3510 |
| sr_anti_hunt_bounce | 6.0000 | 68 | 0.3676 | -4.1755 | 0.2352 |
| sr_anti_hunt_bounce | 8.0000 | 0 | 0.0000 | 0.0000 | 0.0000 |
| sr_break_retest | 3.0000 | 219 | 0.3151 | -0.8625 | 0.2407 |
| sr_break_retest | 4.0000 | 103 | 0.3107 | -1.7772 | 0.2077 |
| sr_break_retest | 6.0000 | 54 | 0.3148 | -1.7896 | 0.1801 |
| sr_break_retest | 8.0000 | 1 | 0.0000 | -8.0873 | 0.0000 |
| sr_fib_confluence | 3.0000 | 2601 | 0.3583 | -1.1887 | 0.3345 |
| sr_fib_confluence | 4.0000 | 1290 | 0.3775 | -0.9040 | 0.3435 |
| sr_fib_confluence | 6.0000 | 694 | 0.3991 | -0.5254 | 0.3524 |
| sr_fib_confluence | 8.0000 | 34 | 0.4706 | 2.5219 | 0.2736 |
| sr_liquidity_grab | 3.0000 | 4 | 0.5000 | 1.3000 | 0.1051 |
| sr_liquidity_grab | 4.0000 | 0 | 0.0000 | 0.0000 | 0.0000 |
| sr_liquidity_grab | 6.0000 | 0 | 0.0000 | 0.0000 | 0.0000 |
| sr_liquidity_grab | 8.0000 | 0 | 0.0000 | 0.0000 | 0.0000 |
| sr_channel_reversal | 3.0000 | 1971 | 0.2648 | -0.1319 | 0.2401 |
| sr_channel_reversal | 4.0000 | 1269 | 0.2695 | 0.0044 | 0.2387 |
| sr_channel_reversal | 6.0000 | 850 | 0.2729 | 0.0813 | 0.2355 |
| sr_channel_reversal | 8.0000 | 33 | 0.2121 | -1.7274 | 0.0862 |

## Statistical Discipline
- Pre-registered primary threshold: composite_weight >= 5.0
- Primary heavy bucket additionally requires HTF source for REBORN_HEAVY verdict.
- Exploratory thresholds: [3.0, 4.0, 6.0, 8.0]
- Bonferroni m=5, alpha=0.01
- Bootstrap CI: 10000 resamples
- Data source: data/cache/massive/*.parquet only; Yahoo is not used.
- Strategy evaluate() code was not modified; weight gate is audit-only post-hoc analysis.
- Runtime note: strategy signal collection used fixed strides {'sr_anti_hunt_bounce': 1, 'sr_break_retest': 8, 'sr_fib_confluence': 2, 'sr_liquidity_grab': 1, 'sr_channel_reversal': 2}; this preserves evaluate() behavior but samples high-frequency duplicate opportunities.
