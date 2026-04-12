# BT Friction Model v3 Results (2026-04-12)

## v2 vs v3 Comparison (same 55d period)

| Config | v2 N | v2 WR | v2 PF | v3 N | v3 WR | v3 PF | Change |
|--------|------|-------|-------|------|-------|-------|--------|
| USD_JPY DT | 285 | 59.6% | 1.00 | **219** | 58.4% | 0.95 | **-66t filtered** |
| EUR_USD DT | 199 | 69.8% | 1.63 | 201 | 68.2% | **1.41** | PF -13.5% (more realistic) |
| GBP_USD DT | 269 | 68.0% | 1.49 | 255 | 69.0% | 1.48 | Stable |
| EUR_JPY DT | 171 | 58.5% | 0.92 | **134** | 58.2% | 0.88 | **-37t filtered** |

## session_time_bias v3 improvement
| Pair | v2 EV | v3 EV | v3 N | v3 WR |
|------|-------|-------|------|-------|
| USD_JPY | +0.373 | **+0.966** | 13 | 92.3% |
| EUR_USD | +0.650 | +0.371 | 40 | 72.5% |
| GBP_USD | +0.266 | +0.130 | 37 | 67.6% |

## v3 removed biases
- Spread/SL Gate: USD_JPY -66t, EUR_JPY -37t (over-traded removed)
- RANGE TP Override: MR strategy TP shortened to BB_mid
- Quick-Harvest: non-MR TP shortened by 15%

## 120d BT: Render timeout (30s limit for 120d data fetch)
- Workaround needed: local BT or async endpoint
