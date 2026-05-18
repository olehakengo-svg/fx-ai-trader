# Pre-Registration LOCK: ob_retest_h1 1095d Re-Test

**LOCK Date**: 2026-05-18
**Type**: H1 Order Block Retest 2nd attempt, data-budget extension only
**Category**: Pullback / Order Block Retest
**Status**: FAIL. LOCKED criteria were not met; `ObRetestH1.enabled = False` remains.
**Rule**: R1

## 1. Hypothesis

H1 TF improves SL/noise ratio (~30-50 pip SL vs ~5-8 pip wick noise) and spread occupancy (0.7 pip / 40 pip SL = 1.75%), allowing institutional anchoring in OB structure to function. In the 365d first attempt, USD_JPY and EUR_JPY were qualitatively near the PASS region but failed only because N<200. If the same edge persisted over a 3y data budget, at least one pair should satisfy the locked WR/Wilson/EV/PF/WF criteria with N>=200.

## 2. Locked Criteria

This 2nd attempt changes only the validation period. Pair set, parameters, friction, and PASS/FAIL criteria are identical to the 365d first attempt.

**PASS**: at least 1 of USD_JPY, EUR_USD, GBP_USD, EUR_JPY, GBP_JPY satisfies all:

- N >= 200
- WR >= 44.0%
- Wilson_lo (95% CI) >= 0.40
- EV >= +0.20 pip/trade after spread + slippage friction
- PF >= 1.10
- WF 3 folds h1 / h2 / h3 all EV >= 0

**FAIL**: no pair satisfies all criteria. `enabled = False` remains.

Bonferroni: m=5 pair tests, alpha=0.05/5=0.01. Wilson_bf_lo is reported separately with z=2.576.

No parameter sweep, post-hoc pair exclusion, or period-adjacent tweak is allowed. GBP_USD remains in the full 5-pair BT set.

## 3. BT Setup

Output: `raw/bt-results/ob_retest_h1_1095d_2026_05_18.json`

- Data source: `data/cache/massive/{PAIR}_1h.parquet`
- Requested period: 2023-05-15 13:00 UTC to 2026-05-15 13:00 UTC
- WF folds: 3 chronological folds across the requested 1095d period
- Spread: USD_JPY=0.7, EUR_USD=0.6, GBP_USD=1.0, EUR_JPY=1.0, GBP_JPY=1.5 pip
- Slippage: 0.2 pip
- Commission: 0
- Wrapper: `tools/ob_retest_h1_1095d_bt.py`

The wrapper was cross-checked against the existing 365d JSON and reproduced all five 365d pair summaries exactly.

## 4. Result

| Pair | N | WR | Wilson_lo | Wilson_bf_lo | EV pips | PF | WF EV h1/h2/h3 | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|---|
| USD_JPY | 414 | 45.65% | 0.4092 | 0.3946 | +2.8951 | 1.1553 | -1.8146 / +3.5031 / +6.9309 | FAIL (WF h1<0) |
| EUR_USD | 432 | 42.36% | 0.3779 | 0.3640 | -0.9552 | 0.9289 | +0.9074 / -3.6705 / -0.0215 | FAIL |
| GBP_USD | 415 | 37.35% | 0.3283 | 0.3148 | -6.6765 | 0.6671 | -6.2136 / -11.1539 / -2.8529 | FAIL |
| EUR_JPY | 431 | 41.76% | 0.3720 | 0.3581 | -8.1947 | 0.7230 | -19.5619 / -10.1784 / +4.2653 | FAIL |
| GBP_JPY | 447 | 41.61% | 0.3713 | 0.3577 | -8.7883 | 0.7562 | -21.7919 / -7.6656 / +2.3618 | FAIL |

**Pre-reg verdict**: FAIL.

USD_JPY cleared the aggregate N, WR, Wilson_lo, EV, and PF thresholds, but failed the locked walk-forward requirement because h1 EV was negative. Every other pair failed multiple aggregate criteria. Therefore no pair satisfies all locked PASS criteria.

## 5. Decision

`strategies/hourly/ob_retest.py` remains `enabled = False`.

The 365d first attempt is unchanged and remains FAIL due to N<200. This 1095d second attempt had enough N for all pairs and still failed the locked criteria, so the OB retest family is retired as a promotion candidate:

- M5 `ob_retest` remains FORCE_DEMOTED.
- H1 `ob_retest_h1` remains registered only for auditability, disabled for live/shadow emission.
- No OB retest parameter relaxation is authorized from this result.
