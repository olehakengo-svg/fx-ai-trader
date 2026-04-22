# Virtual Filter Simulation — 6 PRIME Strategies

**As of**: 2026-04-21 (UTC), **Scope**: Shadow only, XAU 除外
**Bonferroni α/M** (M=6 PRIMEs only): 0.0083
**Global quartile edges**: {'conf': [53.0, 61.0, 69.0], 'spread': [0.8, 0.8, 0.8], 'adx': [20.3, 25.3, 31.7], 'atr': [0.95, 1.01, 1.09], 'cvema': [-0.019, 0.001, 0.034]}

---

## stoch_trend_pullback_PRIME

- **Base**: stoch_trend_pullback (Shadow N=142, WR=28.9%)
- **Fire condition**: ATR_ratio Q1 (≤0.95) AND direction=BUY
- **Condition key**: `[('_atr_q', 'Q1'), ('direction', 'BUY')]`

### Virtual sim (all shadow)

| N | W | L | WR | Wilson下限 | Lift | PF | EV(pips) | Payoff | Kelly | Fire rate | Fisher p | Bonf? |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| 24 | 14 | 10 | 58.3% | 38.8% | 2.02x | 2.10 | +1.51 | 1.50 | 30.6% | 16.9% | 0.0010 | ✓ |

### Walk-forward split

| Period | N | W | WR | PF | EV(pips) |
|---|---:|---:|---:|---:|---:|
| pre-Cutoff | 15 | 9 | 60.0% | 2.00 | +1.53 |
| post-Cutoff | 9 | 5 | 55.6% | 2.35 | +1.47 |

### Verdict: **EV+ / PF>1 / WF再現 / Bonf有意**

---

## stoch_trend_pullback_LONDON_LOWVOL

- **Base**: stoch_trend_pullback (Shadow N=142, WR=28.9%)
- **Fire condition**: ATR_ratio Q1 (≤0.95) AND session=london
- **Condition key**: `[('_atr_q', 'Q1'), ('_session', 'london')]`

### Virtual sim (all shadow)

| N | W | L | WR | Wilson下限 | Lift | PF | EV(pips) | Payoff | Kelly | Fire rate | Fisher p | Bonf? |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| 11 | 7 | 4 | 63.6% | 35.4% | 2.20x | 2.43 | +2.06 | 1.39 | 37.4% | 7.7% | 0.0138 | ✗ |

### Walk-forward split

| Period | N | W | WR | PF | EV(pips) |
|---|---:|---:|---:|---:|---:|
| pre-Cutoff | 8 | 4 | 50.0% | 0.96 | -0.08 |
| post-Cutoff | 3 | 3 | 100.0% | ∞ | +7.77 |

### Verdict: **EV+ / PF>1 / WF再現 / Bonf非有意**

---

## fib_reversal_PRIME

- **Base**: fib_reversal (Shadow N=187, WR=35.3%)
- **Fire condition**: confidence Q3 (61-69) AND close_vs_ema200 Q3 (0.001-0.034)
- **Condition key**: `[('_conf_q', 'Q3'), ('_cvema_q', 'Q3')]`

### Virtual sim (all shadow)

| N | W | L | WR | Wilson下限 | Lift | PF | EV(pips) | Payoff | Kelly | Fire rate | Fisher p | Bonf? |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| 12 | 9 | 3 | 75.0% | 46.8% | 2.12x | 4.99 | +2.96 | 1.66 | 60.0% | 6.4% | 0.0046 | ✓ |

### Walk-forward split

| Period | N | W | WR | PF | EV(pips) |
|---|---:|---:|---:|---:|---:|
| pre-Cutoff | 9 | 6 | 66.7% | 3.12 | +2.10 |
| post-Cutoff | 3 | 3 | 100.0% | ∞ | +5.53 |

### Verdict: **EV+ / PF>1 / WF再現 / Bonf有意**

---

## bb_rsi_reversion_NY_ATRQ2

- **Base**: bb_rsi_reversion (Shadow N=128, WR=28.9%)
- **Fire condition**: hour_band 12-15 UTC AND ATR_ratio Q2 (0.95-1.01)
- **Condition key**: `[('_hour_band', '12-15'), ('_atr_q', 'Q2')]`

### Virtual sim (all shadow)

| N | W | L | WR | Wilson下限 | Lift | PF | EV(pips) | Payoff | Kelly | Fire rate | Fisher p | Bonf? |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| 18 | 10 | 8 | 55.6% | 33.7% | 1.92x | 1.30 | +0.82 | 1.04 | 12.9% | 14.1% | 0.0113 | ✗ |

### Walk-forward split

| Period | N | W | WR | PF | EV(pips) |
|---|---:|---:|---:|---:|---:|
| pre-Cutoff | 5 | 3 | 60.0% | 1.54 | +1.26 |
| post-Cutoff | 13 | 7 | 53.8% | 1.23 | +0.65 |

### Verdict: **EV+ / PF>1 / WF再現 / Bonf非有意**

---

## engulfing_bb_TOKYO_EARLY

- **Base**: engulfing_bb (Shadow N=101, WR=31.7%)
- **Fire condition**: session=tokyo AND hour_band 00-03 UTC
- **Condition key**: `[('_session', 'tokyo'), ('_hour_band', '00-03')]`

### Virtual sim (all shadow)

| N | W | L | WR | Wilson下限 | Lift | PF | EV(pips) | Payoff | Kelly | Fire rate | Fisher p | Bonf? |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| 9 | 5 | 4 | 55.6% | 26.7% | 1.75x | 2.73 | +2.18 | 2.19 | 35.2% | 8.9% | 0.1374 | ✗ |

### Walk-forward split

| Period | N | W | WR | PF | EV(pips) |
|---|---:|---:|---:|---:|---:|
| pre-Cutoff | 4 | 2 | 50.0% | 2.50 | +1.50 |
| post-Cutoff | 5 | 3 | 60.0% | 2.86 | +2.72 |

### Verdict: **EV+ / PF>1 / WF再現 / Bonf非有意**

---

## sr_fib_confluence_GBP_ADXQ2

- **Base**: sr_fib_confluence (Shadow N=102, WR=24.5%)
- **Fire condition**: instrument=GBP_USD AND ADX Q2 (20.3-25.3)
- **Condition key**: `[('instrument', 'GBP_USD'), ('_adx_q', 'Q2')]`

### Virtual sim (all shadow)

| N | W | L | WR | Wilson下限 | Lift | PF | EV(pips) | Payoff | Kelly | Fire rate | Fisher p | Bonf? |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| 13 | 7 | 6 | 53.8% | 29.1% | 2.20x | 1.46 | +1.75 | 1.25 | 16.9% | 12.7% | 0.0148 | ✗ |

### Walk-forward split

| Period | N | W | WR | PF | EV(pips) |
|---|---:|---:|---:|---:|---:|
| pre-Cutoff | 6 | 4 | 66.7% | 2.13 | +3.47 |
| post-Cutoff | 7 | 3 | 42.9% | 1.06 | +0.29 |

### Verdict: **EV+ / PF>1 / WF再現 / Bonf非有意**

---


## Virtual Sim Summary

| Strategy | N | WR | Wilson下限 | PF | EV | Kelly | pre/post WR | Fisher p | Bonf? | EV+ | PF>1 | WF再現 |
|---|---:|---:|---:|---:|---:|---:|---|---:|:---:|:---:|:---:|:---:|
| stoch_trend_pullback_PRIME | 24 | 58.3% | 38.8% | 2.10 | +1.51 | 30.6% | 60%(15)/56%(9) | 0.0010 | ✓ | ✓ | ✓ | ✓ |
| stoch_trend_pullback_LONDON_LOWVOL | 11 | 63.6% | 35.4% | 2.43 | +2.06 | 37.4% | 50%(8)/100%(3) | 0.0138 | ✗ | ✓ | ✓ | ✓ |
| fib_reversal_PRIME | 12 | 75.0% | 46.8% | 4.99 | +2.96 | 60.0% | 67%(9)/100%(3) | 0.0046 | ✓ | ✓ | ✓ | ✓ |
| bb_rsi_reversion_NY_ATRQ2 | 18 | 55.6% | 33.7% | 1.30 | +0.82 | 12.9% | 60%(5)/54%(13) | 0.0113 | ✗ | ✓ | ✓ | ✓ |
| engulfing_bb_TOKYO_EARLY | 9 | 55.6% | 26.7% | 2.73 | +2.18 | 35.2% | 50%(4)/60%(5) | 0.1374 | ✗ | ✓ | ✓ | ✓ |
| sr_fib_confluence_GBP_ADXQ2 | 13 | 53.8% | 29.1% | 1.46 | +1.75 | 16.9% | 67%(6)/43%(7) | 0.0148 | ✗ | ✓ | ✓ | ✓ |
