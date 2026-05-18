# Pre-Registration LOCK: ob_retest_h1

**LOCK Date**: 2026-05-18
**Type**: H1 Order Block Retest migration from failed M5 structure
**Category**: Pullback / Order Block Retest
**Status**: 🔒 LOCKED — parameters, pair set, PASS/FAIL criteria fixed before BT. Post-hoc modification prohibited.

## 0. Background Audit

### 0.1 TV Pine BT Observation

TV Pine BT, USDJPY 2026-02-09 → 2026-05-19, same period / same parameters:

| Setting | N | WR | Wilson_lo | z vs baseline | p | Bonferroni m=3 |
|---|---:|---:|---:|---:|---:|---|
| Baseline (filters off) | 733 | 38.74% | 0.353 | — | — | — |
| + Filter A (H1 EMA50 gate) | 519 | 38.34% | 0.343 | -0.143 | 0.886 | NO |
| + Filter B (ADX ≥ 20 gate) | 451 | 39.47% | 0.351 | +0.250 | 0.803 | NO |

Conclusion: under the M5 structure, no filter significantly lifts WR. Even before Bonferroni correction at α=0.05, all null. H1 Gate (Wilson_lo ≥ 0.40) needs WR 45.5% at N=300 or 44.3% at N=500; current result is blocked by a +6-7 pp gap.

### 0.2 TF Comparison BT

Same Pine, same parameters, USDJPY only:

| TF | Result |
|---|---|
| M5 | WR 38.7%, EV<0, ~-0.69%/y over 3.5mo BT |
| M15 | WR 40.8%, breakeven, ~+0.24%/y over 10.5mo BT |
| H1 | WR 41.8%, +1.35% / 3.4y, ~+0.40%/y peak |
| H4 | WR 42.8%, +2.62% / 13.4y, ~+0.20%/y |

H1 is the sweet spot. M5 is structurally disadvantaged by SL/noise ratio (~3-6 pip SL vs 1-3 pip wick) and spread occupancy (0.7 pip / 5 pip = 14%); this is not fixable by entry filters.

### 0.3 Shadow Status

Render API, 2026-05-15:

- `ob_retest` tier=PHASE0_SHADOW, N=36, WR=47.2%, +186.7 pips
- USD_JPY/BUY cell N=17 WR=52.9%, Wilson_lo=0.3096
- H1 Gate FAIL (Wilson_lo 0.32 ≪ 0.40), WF h1_avg=-0.522 (regime fit)
- Shadow vs M5 BT WR (47.2% vs 38.7%) is about 1.04σ upside noise

## 1. Implementation LOCK

### 1.1 Strategy

File: `strategies/hourly/ob_retest.py`

```python
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext


class ObRetestH1(StrategyBase):
    name = "ob_retest_h1"
    mode = "hourly"
    enabled = True
```

### 1.2 Parameters

LOCKED — post-hoc modification prohibited:

```python
# OB detection
IMPULSE_MIN_BARS = 3
IMPULSE_ATR_MULT = 2.0
OB_LOOKBACK = 60
OB_FRESHNESS = 50
OB_MAX_WIDTH_ATR = 2.0

# Entry confirmation
EMA_FAST = 9
EMA_SLOW = 21
RETEST_BUFFER_ATR = 0.10

# Risk
SL_BUFFER_ATR = 0.10
TP_R_MULT = 1.5

# Pairs
ALLOWED_PAIRS = {"USDJPY", "EURUSD", "GBPUSD", "EURJPY", "GBPJPY"}
```

### 1.3 Entry Logic

USD_JPY/BUY reference; SELL is symmetric.

```text
1. OB detection: candidate bar = current - (IMPULSE_MIN_BARS+1)
   - candidate is bearish (close < open)
   - followed by IMPULSE_MIN_BARS consecutive bullish bars
   - total consecutive bullish range >= ATR * IMPULSE_ATR_MULT
   - candidate bar range <= ATR * OB_MAX_WIDTH_ATR
   -> push bullish OB {high, low, age=0}

2. Age management: expire OB when age > OB_FRESHNESS

3. Retest condition (BUY):
   - low <= ob_high + RETEST_BUFFER_ATR * ATR
   - low >= ob_low  - RETEST_BUFFER_ATR * ATR
   - close > open (bullish reversal candle)
   - EMA9 > EMA21 AND close > EMA21

4. SL/TP, entry_price basis:
   - SL = ob_low - SL_BUFFER_ATR * ATR
   - risk = entry_price - SL
   - TP = entry_price + risk * TP_R_MULT
```

### 1.4 Engine Registration

Register `ObRetestH1()` in `HourlyEngine().strategies` after `DonchianMomentumBreakout()`.

### 1.5 M5 Demotion

Add `ob_retest` to `DemoTrader._FORCE_DEMOTED` under rule:R2. OB thesis migrates to `ob_retest_h1` for pre-registered validation.

## 2. Validation LOCK

### 2.1 Hypothesis

H1 TF improves SL/noise ratio (~30-50 pip SL vs ~5-8 pip wick noise) and spread occupancy (0.7 pip / 40 pip SL = 1.75%), allowing institutional anchoring in OB structure to function. For USD_JPY/BUY direction, expected threshold is **WR ≥ 44%, Wilson_lo ≥ 0.40, EV ≥ +0.20 pip/trade**.

### 2.2 PASS / FAIL Criteria

365d MASSIVE BT (USD_JPY, EUR_USD, GBP_USD, EUR_JPY, GBP_JPY), 5 pairs:

**PASS**: across all 5 pairs, at least 1 pair satisfies all:

- N ≥ 200
- WR ≥ 44.0%
- Wilson_lo (95% CI) ≥ 0.40
- EV ≥ +0.20 pip/trade after spread + slippage friction
- PF ≥ 1.10
- WF (walk-forward, 3+ folds) h1 / h2 / h3 all EV ≥ 0

**FAIL**: if any condition above is not satisfied, rollback:

- Change `strategies/hourly/ob_retest.py` to `enabled = False`
- Keep HourlyEngine registration for future reevaluation
- Append failure evidence to this pre-reg LOCK document

### 2.3 Bonferroni Correction

m=5 pair tests, so 1-pair PASS α = 0.05/5 = 0.01. Wilson_lo remains 95% CI; Wilson_bf_lo is separately calculated and reported with z=2.575 (99%).

### 2.4 Multiple Testing Scope

No parameter sweep is allowed in this BT. One-shot validation with LOCKED parameters across the 5-pair set. Any future sweep requires a separate pre-reg LOCK and increased Bonferroni m.

## 3. BT Evidence Appended 2026-05-18

Data source check before BT: all target `data/cache/massive/{PAIR}_1h.parquet` files existed. Local MASSIVE cache latest bar was 2026-05-15 13:00 UTC for all target pairs, so the requested 2025-05-18 → 2026-05-18 run used all available cached rows inside the requested window without excluding any pair.

Output: `raw/bt-results/ob_retest_h1_365d_2026_05_18.json`

| Pair | N | WR | Wilson_lo | Wilson_bf_lo | EV pips | PF | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| USD_JPY | 132 | 50.00% | 0.4159 | 0.3906 | +6.5408 | 1.4083 | FAIL (N<200) |
| EUR_USD | 120 | 48.33% | 0.3958 | 0.3685 | +0.5452 | 1.0436 | FAIL |
| GBP_USD | 130 | 36.92% | 0.2911 | 0.2678 | -3.0732 | 0.8178 | FAIL |
| EUR_JPY | 141 | 51.06% | 0.4289 | 0.4044 | +4.8384 | 1.2600 | FAIL (N<200) |
| GBP_JPY | 149 | 47.65% | 0.3979 | 0.3736 | +2.2341 | 1.0902 | FAIL |

**Pre-reg verdict**: FAIL. No pair reached N≥200, so the locked PASS condition is not satisfied even where WR/EV looked promising. Per rollback rule, `ObRetestH1.enabled = False` while HourlyEngine registration is retained.

## 4. 1095d Re-Test Evidence Appended 2026-05-18

Decision: [[pre-reg-ob-retest-h1-1095d-2026-05-18]]

The 2nd attempt extended only the data budget to 2023-05-15 13:00 UTC → 2026-05-15 13:00 UTC. Parameters, pair set, friction model, Bonferroni m=5, and PASS/FAIL criteria were unchanged.

Output: `raw/bt-results/ob_retest_h1_1095d_2026_05_18.json`

| Pair | N | WR | Wilson_lo | Wilson_bf_lo | EV pips | PF | WF EV h1/h2/h3 | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|---|
| USD_JPY | 414 | 45.65% | 0.4092 | 0.3946 | +2.8951 | 1.1553 | -1.8146 / +3.5031 / +6.9309 | FAIL (WF h1<0) |
| EUR_USD | 432 | 42.36% | 0.3779 | 0.3640 | -0.9552 | 0.9289 | +0.9074 / -3.6705 / -0.0215 | FAIL |
| GBP_USD | 415 | 37.35% | 0.3283 | 0.3148 | -6.6765 | 0.6671 | -6.2136 / -11.1539 / -2.8529 | FAIL |
| EUR_JPY | 431 | 41.76% | 0.3720 | 0.3581 | -8.1947 | 0.7230 | -19.5619 / -10.1784 / +4.2653 | FAIL |
| GBP_JPY | 447 | 41.61% | 0.3713 | 0.3577 | -8.7883 | 0.7562 | -21.7919 / -7.6656 / +2.3618 | FAIL |

**2nd pre-reg verdict**: FAIL. USD_JPY passed the aggregate N/WR/Wilson_lo/EV/PF thresholds but failed the locked WF requirement because h1 EV<0. No pair satisfies all PASS criteria.

`ObRetestH1.enabled = False` remains. With enough 3y N now available, the OB retest family is recorded as retired as a promotion candidate. M5 `ob_retest` remains FORCE_DEMOTED.
