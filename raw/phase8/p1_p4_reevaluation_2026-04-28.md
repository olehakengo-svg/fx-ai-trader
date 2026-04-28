# Phase 8 Re-evaluation under P1 (n-scaled Wilson) + P4 (per-track Bonferroni)

- Date: 2026-04-28
- target_wr: 0.5
- alpha: 0.05
- Original Phase 8 master gate: ``Wilson_lower_holdout > 0.48`` fixed
- New gates: P1 = ``Wilson_lower(n) > wilson_lower_at(target_wr=0.5, n)``; P4 = Bonferroni per track

## Per-track summary

| Track | Stage1 n_tests | Bonf thresh | P1+Bonf survivors | P1+BH-FDR(0.10) survivors |
|---|---|---|---|---|
| A | 720 | 6.94e-05 | 2 | 5 |
| B | 2087 | 2.40e-05 | 0 | 0 |
| C | 1200 | 4.17e-05 | 0 | 0 |
| D | 180 | 2.78e-04 | 0 | 0 |
| E | 846 | 5.91e-05 | 0 | 0 |

## Survivors detail (Bonferroni per-track, top 20 per track by Wilson_lower)

### Track A
| n | wr | wilson_lower_actual | wilson_lower_gate | p_value | pair | triplet | buckets | direction | forward_bars | ev_net_pip | pf |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 104 | 0.7115 | 0.6181 | 0.4056 | 1.9e-05 | GBP_JPY | ['hour_utc', 'bbpb_15m_b'] | [20, 3] | SELL | 8 | 7.144 | 2.496 |
| 104 | 0.7115 | 0.6181 | 0.4056 | 1.9e-05 | GBP_JPY | ['hour_utc', 'bbpb_15m_b'] | [20, 3] | SELL | 12 | 7.058 | 2.418 |

### Track B
(no survivors)

### Track C
(no survivors)

### Track D
(no survivors)

### Track E
(no survivors)

## Survivors detail (BH-FDR(0.10) per-track, top 20 per track by Wilson_lower)

### Track A
| n | wr | wilson_lower_actual | wilson_lower_gate | p_value | pair | triplet | buckets | direction | forward_bars | ev_net_pip | pf |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 104 | 0.7115 | 0.6181 | 0.4056 | 1.9e-05 | GBP_JPY | ['hour_utc', 'bbpb_15m_b'] | [20, 3] | SELL | 8 | 7.144 | 2.496 |
| 104 | 0.7115 | 0.6181 | 0.4056 | 1.9e-05 | GBP_JPY | ['hour_utc', 'bbpb_15m_b'] | [20, 3] | SELL | 12 | 7.058 | 2.418 |
| 102 | 0.6176 | 0.5207 | 0.4047 | 0.022298 | EUR_JPY | ['hour_utc', 'bbpb_15m_b'] | [20, 3] | SELL | 12 | 3.171 | 1.596 |
| 104 | 0.6154 | 0.5194 | 0.4056 | 0.023646 | GBP_JPY | ['hour_utc', 'bbpb_15m_b'] | [20, 3] | SELL | 4 | 4.476 | 1.929 |
| 102 | 0.6078 | 0.5108 | 0.4047 | 0.037067 | EUR_JPY | ['hour_utc', 'bbpb_15m_b'] | [20, 3] | SELL | 8 | 2.888 | 1.552 |

### Track B
(no survivors)

### Track C
(no survivors)

### Track D
(no survivors)

### Track E
(no survivors)
