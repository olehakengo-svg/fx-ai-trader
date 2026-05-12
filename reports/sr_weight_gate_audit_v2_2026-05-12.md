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
| sr_anti_hunt_bounce | DEAD | 1441 | 68 | 0.3676 | -4.1755 | DEAD | 335 | 329 | 0.4498 | -2.9272 | 0.3809 |
| sr_break_retest | DEAD | 294 | 54 | 0.3148 | -1.7896 | DEAD | 294 | 292 | 0.2945 | -0.8600 | 0.2310 |
| sr_fib_confluence | DEAD | 4748 | 708 | 0.3955 | -0.6166 | DEAD | 2037 | 2018 | 0.3726 | -0.8786 | 0.3454 |
| sr_liquidity_grab | DEAD | 6 | 0 | 0.0000 | 0.0000 | DEAD | 2 | 2 | 0.5000 | 25.7500 | 0.0617 |
| sr_channel_reversal | DEAD | 2612 | 876 | 0.2671 | -0.0001 | DEAD | 1249 | 1240 | 0.2516 | -0.3314 | 0.2212 |

## sr_anti_hunt_bounce Triangulation vs SR-weight Phase 2 BT

SR-weight Phase 2 BT reported sr_anti_hunt_bounce as a BH FDR survivor (trend p=0.0034, N=594). Fixed audit sr_anti_hunt_bounce N=335, which is outside the Phase 2 BT triangulation band 416-772; this is a material deviation and detector mismatch remains a candidate explanation.

Pivot triangulation skipped due to time budget; this run remains on the pre-existing KDE detector path.

## Summary
| Strategy | N total | N heavy | WR all | WR heavy | EV all | EV heavy | Wilson_lo (heavy, Bonf) | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sr_anti_hunt_bounce | 335 | 329 | 0.4478 | 0.4498 | -2.9064 | -2.9272 | 0.3809 | DEAD |
| sr_break_retest | 294 | 292 | 0.2925 | 0.2945 | -0.9291 | -0.8600 | 0.2310 | DEAD |
| sr_fib_confluence | 2037 | 2018 | 0.3741 | 0.3726 | -0.8160 | -0.8786 | 0.3454 | DEAD |
| sr_liquidity_grab | 2 | 2 | 0.5000 | 0.5000 | 25.7500 | 25.7500 | 0.0617 | DEAD |
| sr_channel_reversal | 1249 | 1240 | 0.2514 | 0.2516 | -0.3314 | -0.3314 | 0.2212 | DEAD |

## Per-Strategy Details

### sr_anti_hunt_bounce
- composite_weight quintile bucket stats
| bucket | N | WR | EV | Wilson_lo | mean_weight | htf_rate |
| --- | --- | --- | --- | --- | --- | --- |
| Q1 | 69 | 0.4493 | -0.7259 | 0.3063 | 36.1454 | 0.9130 |
| Q2 | 71 | 0.4366 | -1.5629 | 0.2969 | 50.8964 | 1.0000 |
| Q3 | 61 | 0.4918 | -6.0873 | 0.3360 | 69.1104 | 1.0000 |
| Q4 | 77 | 0.4286 | -4.3465 | 0.2947 | 99.4867 | 1.0000 |
| Q5 | 57 | 0.4386 | -1.8701 | 0.2846 | 154.5053 | 1.0000 |
- HTF source bucket stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| D1 only | 137 | 0.4088 | -4.4015 | 0.3072 |
| D1+W1 | 176 | 0.5000 | -1.3264 | 0.4047 |
| W1 only | 16 | 0.2500 | -7.9125 | 0.0777 |
| none | 6 | 0.3333 | -1.7667 | 0.0682 |
- own_touch bucket stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| 6+ | 335 | 0.4478 | -2.9064 | 0.3795 |
- magnitude quartile stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| ALL | 335 | 0.4478 | -2.9064 | 0.3795 |
- single-year concentration check: clear
- bootstrap EV diff CI (heavy+HTF minus all): [-3.7310, 3.7936]
- Redesign spec draft: not generated because verdict is DEAD.

### sr_break_retest
- composite_weight quintile bucket stats
| bucket | N | WR | EV | Wilson_lo | mean_weight | htf_rate |
| --- | --- | --- | --- | --- | --- | --- |
| Q1 | 62 | 0.2581 | -0.9442 | 0.1434 | 48.6308 | 0.9677 |
| Q2 | 56 | 0.3036 | -0.6058 | 0.1733 | 78.1424 | 1.0000 |
| Q3 | 63 | 0.2857 | -1.8344 | 0.1652 | 106.1696 | 1.0000 |
| Q4 | 57 | 0.2105 | -2.8205 | 0.1057 | 155.7552 | 1.0000 |
| Q5 | 56 | 0.4107 | 1.7076 | 0.2598 | 225.3502 | 1.0000 |
- HTF source bucket stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| D1 only | 94 | 0.2553 | -1.3708 | 0.1583 |
| D1+W1 | 194 | 0.3093 | -0.6875 | 0.2313 |
| W1 only | 4 | 0.5000 | 2.7772 | 0.1051 |
| none | 2 | 0.0000 | -11.0219 | 0.0000 |
- own_touch bucket stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| 6+ | 294 | 0.2925 | -0.9291 | 0.2294 |
- magnitude quartile stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| ALL | 294 | 0.2925 | -0.9291 | 0.2294 |
- single-year concentration check: clear
- bootstrap EV diff CI (heavy+HTF minus all): [-2.2038, 2.4282]
- Redesign spec draft: not generated because verdict is DEAD.

### sr_fib_confluence
- composite_weight quintile bucket stats
| bucket | N | WR | EV | Wilson_lo | mean_weight | htf_rate |
| --- | --- | --- | --- | --- | --- | --- |
| Q1 | 414 | 0.3913 | -0.2006 | 0.3317 | 47.6400 | 0.9541 |
| Q2 | 401 | 0.3591 | -0.8420 | 0.3001 | 78.7490 | 1.0000 |
| Q3 | 459 | 0.3529 | -1.6136 | 0.2980 | 111.4494 | 1.0000 |
| Q4 | 410 | 0.3951 | -0.2840 | 0.3351 | 166.2896 | 1.0000 |
| Q5 | 353 | 0.3739 | -1.0889 | 0.3105 | 213.7796 | 1.0000 |
- HTF source bucket stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| D1 only | 725 | 0.3697 | -0.8915 | 0.3249 |
| D1+W1 | 1227 | 0.3684 | -1.0716 | 0.3337 |
| W1 only | 66 | 0.4848 | 2.8497 | 0.3352 |
| none | 19 | 0.5263 | 5.8391 | 0.2654 |
- own_touch bucket stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| 6+ | 2037 | 0.3741 | -0.8160 | 0.3469 |
- magnitude quartile stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| ALL | 2037 | 0.3741 | -0.8160 | 0.3469 |
- single-year concentration check: clear
- bootstrap EV diff CI (heavy+HTF minus all): [-1.0999, 0.9802]
- Redesign spec draft: not generated because verdict is DEAD.

### sr_liquidity_grab
- composite_weight quintile bucket stats
| bucket | N | WR | EV | Wilson_lo | mean_weight | htf_rate |
| --- | --- | --- | --- | --- | --- | --- |
| Q1 | 1 | 0.0000 | -9.5000 | 0.0000 | 39.6261 | 1.0000 |
| Q2 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | nan |
| Q3 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | nan |
| Q4 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | nan |
| Q5 | 1 | 1.0000 | 61.0000 | 0.1310 | 58.7354 | 1.0000 |
- HTF source bucket stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| D1+W1 | 1 | 0.0000 | -9.5000 | 0.0000 |
| W1 only | 1 | 1.0000 | 61.0000 | 0.1310 |
- own_touch bucket stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| 6+ | 2 | 0.5000 | 25.7500 | 0.0617 |
- magnitude quartile stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| ALL | 2 | 0.5000 | 25.7500 | 0.0617 |
- single-year concentration check: clear
- bootstrap EV diff CI (heavy+HTF minus all): [-70.5000, 70.5000]
- Redesign spec draft: not generated because verdict is DEAD.

### sr_channel_reversal
- composite_weight quintile bucket stats
| bucket | N | WR | EV | Wilson_lo | mean_weight | htf_rate |
| --- | --- | --- | --- | --- | --- | --- |
| Q1 | 251 | 0.2271 | -1.3881 | 0.1665 | 56.9946 | 0.9641 |
| Q2 | 251 | 0.2869 | 0.5912 | 0.2196 | 107.0715 | 1.0000 |
| Q3 | 252 | 0.2619 | -0.1114 | 0.1973 | 176.1344 | 1.0000 |
| Q4 | 253 | 0.2332 | -0.7165 | 0.1721 | 195.4928 | 1.0000 |
| Q5 | 242 | 0.2479 | -0.0190 | 0.1838 | 228.3424 | 1.0000 |
- HTF source bucket stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| D1 only | 210 | 0.2524 | -0.7073 | 0.1836 |
| D1+W1 | 1016 | 0.2539 | -0.1600 | 0.2204 |
| W1 only | 14 | 0.0714 | -7.1296 | 0.0084 |
| none | 9 | 0.2222 | -0.3402 | 0.0447 |
- own_touch bucket stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| 6+ | 1249 | 0.2514 | -0.3314 | 0.2212 |
- magnitude quartile stats
| bucket | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- |
| ALL | 1249 | 0.2514 | -0.3314 | 0.2212 |
- single-year concentration check: clear
- bootstrap EV diff CI (heavy+HTF minus all): [-0.8599, 0.8646]
- Redesign spec draft: not generated because verdict is DEAD.

## Exploratory Thresholds
| Strategy | threshold | N | WR | EV | Wilson_lo |
| --- | --- | --- | --- | --- | --- |
| sr_anti_hunt_bounce | 3.0000 | 335 | 0.4478 | -2.9064 | 0.3795 |
| sr_anti_hunt_bounce | 4.0000 | 335 | 0.4478 | -2.9064 | 0.3795 |
| sr_anti_hunt_bounce | 6.0000 | 335 | 0.4478 | -2.9064 | 0.3795 |
| sr_anti_hunt_bounce | 8.0000 | 335 | 0.4478 | -2.9064 | 0.3795 |
| sr_break_retest | 3.0000 | 294 | 0.2925 | -0.9291 | 0.2294 |
| sr_break_retest | 4.0000 | 294 | 0.2925 | -0.9291 | 0.2294 |
| sr_break_retest | 6.0000 | 294 | 0.2925 | -0.9291 | 0.2294 |
| sr_break_retest | 8.0000 | 294 | 0.2925 | -0.9291 | 0.2294 |
| sr_fib_confluence | 3.0000 | 2037 | 0.3741 | -0.8160 | 0.3469 |
| sr_fib_confluence | 4.0000 | 2037 | 0.3741 | -0.8160 | 0.3469 |
| sr_fib_confluence | 6.0000 | 2037 | 0.3741 | -0.8160 | 0.3469 |
| sr_fib_confluence | 8.0000 | 2037 | 0.3741 | -0.8160 | 0.3469 |
| sr_liquidity_grab | 3.0000 | 2 | 0.5000 | 25.7500 | 0.0617 |
| sr_liquidity_grab | 4.0000 | 2 | 0.5000 | 25.7500 | 0.0617 |
| sr_liquidity_grab | 6.0000 | 2 | 0.5000 | 25.7500 | 0.0617 |
| sr_liquidity_grab | 8.0000 | 2 | 0.5000 | 25.7500 | 0.0617 |
| sr_channel_reversal | 3.0000 | 1249 | 0.2514 | -0.3314 | 0.2212 |
| sr_channel_reversal | 4.0000 | 1249 | 0.2514 | -0.3314 | 0.2212 |
| sr_channel_reversal | 6.0000 | 1249 | 0.2514 | -0.3314 | 0.2212 |
| sr_channel_reversal | 8.0000 | 1249 | 0.2514 | -0.3314 | 0.2212 |

## Statistical Discipline
- Pre-registered primary threshold: composite_weight >= 5.0
- Primary heavy bucket additionally requires HTF source for REBORN_HEAVY verdict.
- Exploratory thresholds: [3.0, 4.0, 6.0, 8.0]
- Bonferroni m=5, alpha=0.01
- Bootstrap CI: 10000 resamples
- Data source: data/cache/massive/*.parquet only; Yahoo is not used.
- Strategy evaluate() code was not modified; weight gate is audit-only post-hoc analysis.
- Runtime note: strategy signal collection used fixed strides {'sr_anti_hunt_bounce': 4, 'sr_break_retest': 8, 'sr_fib_confluence': 4, 'sr_liquidity_grab': 4, 'sr_channel_reversal': 4}; this preserves evaluate() behavior but samples high-frequency duplicate opportunities.
