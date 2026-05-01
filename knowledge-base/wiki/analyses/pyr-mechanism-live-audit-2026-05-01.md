# PYR Mechanism Live Audit — 2026-05-01

**Audit window**: 2026-04-09 → 2026-04-30
**Total PYR Live trades**: 23
**Distinct parent strategies**: 7

## Source
- `/api/oanda/trades?state=ALL` joined to `/api/oanda/audit` where `demo_trade_id LIKE 'PYR_%'`
- Parent strategy resolved via `audit.demo_trade_id = 'PYR_<parent>'` → parent's `bridge_status='sent'` audit row's `entry_type` (filled-row entry_type is MODE name, not strategy)

## Hold-time distribution (BE-SL design implies short holds)

| Band | Count | % |
|---|---:|---:|
| <=5s | 15 | 65.2% |
| 5–60s | 8 | 34.8% |
| 1–10min | 0 | 0.0% |
| 10min–1h | 0 | 0.0% |
| >1h | 0 | 0.0% |

## Close-reason distribution

| Reason | Count | % |
|---|---:|---:|
| STOP_LOSS | 16 | 69.6% |
| MARKET_CLOSE | 6 | 26.1% |
| TAKE_PROFIT | 1 | 4.3% |

## Per parent strategy

| Parent | N | TP | SL | MKT | WR | EV(pip) | Total(pip) | Total(JPY) | Wilson_BF | Bonf p (vs 50%) | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| gbp_deep_pullback | 2 | 0 | 2 | 0 | 0.0% | -1.55 | -3.1 | -492 | 0.000 | 1 | insufficient (N<10) |
| orb_trap | 6 | 0 | 6 | 0 | 0.0% | -1.93 | -11.6 | -1849 | 0.000 | 0.1 | insufficient (N<10) |
| session_time_bias | 4 | 0 | 4 | 0 | 0.0% | -1.80 | -7.2 | -1151 | 0.000 | 0.319 | insufficient (N<10) |
| trendline_sweep | 1 | 0 | 1 | 0 | 0.0% | -7.00 | -7.0 | -1120 | 0.000 | 1 | insufficient (N<10) |
| vix_carry_unwind | 1 | 0 | 0 | 1 | 0.0% | -0.90 | -0.9 | -90 | 0.000 | 1 | insufficient (N<10) |
| vol_momentum_scalp | 8 | 1 | 2 | 5 | 33.3% | -0.60 | -4.8 | -657 | 0.027 | 1 | insufficient (N<10) |
| xs_momentum | 1 | 0 | 1 | 0 | 0.0% | -1.30 | -1.3 | -204 | 0.000 | 1 | insufficient (N<10) |

## Aggregate (all PYR)

- N: 23
- TP: 1 / SL: 16 / MKT: 6
- Decided WR: 5.9% (Wilson_BF lower @ Z=3.29: 0.005)
- EV per PYR: -1.56 pip
- Total: -35.9 pip / -5563 JPY

## Interpretation guide

- Risk-free design (SL=parent entry) implies losses should be small per-event but frequent (BE-SL is easy to hit). The question is whether net EV across the cohort is non-negative.
- If aggregate `Total(pip) < 0` AND `Bonf p < 0.05` against the 50% TP rate null, the PYR mechanism is structurally giving back parent profits. → flag-gate `_pyramid_trades` in `modules/demo_trader.py:1855-1917` pending design fix.
- If aggregate is unclear (Bonf p > 0.05 with mixed signal), recommend Shadow-only PYR for N≥30 accumulation before re-arming.
