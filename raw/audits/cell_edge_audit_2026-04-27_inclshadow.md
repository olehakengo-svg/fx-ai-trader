# Cell-by-Cell Edge Audit (Q1', 2026-04-27)

Source: demo_trades.db, scope: Live + Shadow
Min N per cell: **10**
Total cells qualified: **9**
Promotion candidates (Wilson lower > 50% AND Bonferroni p < 0.05): **1**

## Promotion Candidates

| entry_type | session | quartile | mode | N | wins | WR | Wilson [lo, hi] | EV pip | PF | p (Bonf) |
|---|---|---|---|---|---|---|---|---|---|---|
| fib_reversal | Tokyo | q0 | Scalp | 24 | 21 | 87.5% | [69.0%, 95.7%] | +10.82 | 14.60 | 0.0022 |

## All Qualified Cells (sorted by Wilson lower)

| entry_type | session | quartile | mode | N (Live/Shadow) | WR | Wilson lower | EV pip | PF | p (raw / Bonf) |
|---|---|---|---|---|---|---|---|---|---|
| fib_reversal | Tokyo | q0 | Scalp | 24 (0/24) | 87.5% | 69.0% | +10.82 | 14.60 | 0.0002 / 0.0022 |
| bb_rsi_reversion | Tokyo | q0 | Scalp | 10 (10/0) | 70.0% | 39.7% | +4.09 | 3.32 | 0.2059 / 1.0000 |
| bb_rsi_reversion | London | q0 | Scalp | 13 (12/1) | 53.8% | 29.1% | +11.31 | 8.74 | 0.7815 / 1.0000 |
| ema_trend_scalp | Tokyo | q0 | Scalp | 10 (0/10) | 40.0% | 16.8% | -0.26 | 0.89 | 0.5271 / 1.0000 |
| fib_reversal | London | q0 | Scalp | 11 (0/11) | 36.4% | 15.2% | +10.44 | 5.88 | 0.3657 / 1.0000 |
| sr_fib_confluence | London | q0 | DT | 13 (0/13) | 30.8% | 12.7% | -10.90 | 0.27 | 0.1655 / 1.0000 |
| vol_surge_detector | Tokyo | q0 | Scalp | 10 (0/10) | 30.0% | 10.8% | -2.05 | 0.41 | 0.2059 / 1.0000 |
| ema_trend_scalp | Overlap | q0 | Scalp | 28 (0/28) | 17.9% | 7.9% | -1.89 | 0.35 | 0.0007 / 0.0060 |
| ema_trend_scalp | London | q0 | Scalp | 21 (0/21) | 14.3% | 5.0% | -2.52 | 0.23 | 0.0011 / 0.0096 |
