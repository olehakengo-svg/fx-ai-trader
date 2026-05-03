> ⚠️ **Baseline drift acknowledged**: aggregate numbers diverge from the
> 2026-04-29 wiki System State block. Drift documented below; the
> decomposition uses the actual snapshot in the supplied `--db`.

### Drift vs wiki/index.md System State (2026-04-29)

- N mismatch: expected 286, got 29
- WR mismatch: expected 38.11%, got 48.28%
- EV mismatch: expected -0.80, got -2.20
- PnL mismatch: expected -228.6, got -63.7
- Edge mismatch: expected -0.1804, got -0.2002

---
# Aggregate Kelly Decomposition Audit — 2026-05-03

Source DB: `demo_trades.db`
Cutoff: `entry_time >= 2026-04-08` | Scope: Live (`oanda_trade_id != ''`) | Excluded: XAU_USD, EUR_GBP

## Aggregate sanity check

- N=29, wins=14, losses=15, WR=48.28%
- EV=-2.20 pip/trade, PnL=-63.7 pip, edge=-20.02pp, Kelly=+0.0000
- Counts: DEMOTE=0, WATCH=7, OK=1 across 8 qualified cells

## Pair

| pair | N | wins | losses | WR | Wilson_lo_95 | Wilson_up_95 | EV_pip | PnL_pip | PF | BEV_WR | gap_to_BEV_pp | flag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GBP_USD | 11 | 5 | 6 | 45.45% | 21.27% | 71.99% | -1.96 | -21.60 | 0.61 | 37.90% | +7.55 | WATCH |
| USD_JPY | 15 | 8 | 7 | 53.33% | 30.12% | 75.19% | -1.27 | -19.10 | 0.76 | 34.40% | +18.93 | WATCH |

## Strategy x Pair

| entry_type | pair | N | wins | losses | WR | Wilson_lo_95 | Wilson_up_95 | EV_pip | PnL_pip | PF | BEV_WR | gap_to_BEV_pp | flag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| session_time_bias | GBP_USD | 5 | 2 | 3 | 40.00% | 11.76% | 76.93% | -3.52 | -17.60 | 0.13 | 37.90% | +2.10 | WATCH |
| fib_reversal | USD_JPY | 8 | 4 | 4 | 50.00% | 21.52% | 78.48% | +0.17 | +1.40 | 1.10 | 34.40% | +15.60 | OK |

## Session

| session | N | wins | losses | WR | Wilson_lo_95 | Wilson_up_95 | EV_pip | PnL_pip | PF | BEV_WR | gap_to_BEV_pp | flag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| London | 9 | 5 | 4 | 55.56% | 26.66% | 81.12% | -5.29 | -47.60 | 0.32 | 36.34% | +19.21 | WATCH |
| Tokyo | 15 | 6 | 9 | 40.00% | 19.82% | 64.25% | -2.33 | -35.00 | 0.55 | 35.33% | +4.67 | WATCH |

## MTF Regime label

| regime | N | wins | losses | WR | Wilson_lo_95 | Wilson_up_95 | EV_pip | PnL_pip | PF | BEV_WR | gap_to_BEV_pp | flag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bull | 8 | 3 | 5 | 37.50% | 13.68% | 69.43% | -4.42 | -35.40 | 0.32 | 37.16% | +0.34 | WATCH |
| range | 21 | 11 | 10 | 52.38% | 32.37% | 71.66% | -1.35 | -28.30 | 0.75 | 35.40% | +16.98 | WATCH |

## Top 5 PnL-destroyer cells

1. `session` session=London | N=9 | PnL=-47.6 | EV=-5.29 | WR=55.56% | flag=WATCH
2. `regime` regime=bull | N=8 | PnL=-35.4 | EV=-4.42 | WR=37.50% | flag=WATCH
3. `session` session=Tokyo | N=15 | PnL=-35.0 | EV=-2.33 | WR=40.00% | flag=WATCH
4. `regime` regime=range | N=21 | PnL=-28.3 | EV=-1.35 | WR=52.38% | flag=WATCH
5. `pair` pair=GBP_USD | N=11 | PnL=-21.6 | EV=-1.96 | WR=45.45% | flag=WATCH

## DEMOTE list

_No cells met the DEMOTE threshold._

## Sensitivity check

- Excluding all trades touched by DEMOTE cells removes 0 trades.
- Hypothetical aggregate after DEMOTE exclusion: N=29, WR=48.28%, EV=-2.20, PnL=-63.7, edge=-20.02pp, Kelly=+0.0000
- Kelly remains <= 0 unless the recomputed value above is strictly positive.

## Limitations

- Cells with N < 8 are WATCH-only even when they are economically negative.
- Session and regime rows use trade-count-weighted BEV_WR because they mix multiple pairs.
- DEMOTE cells overlap across axes; the sensitivity check excludes the union of affected trades.
