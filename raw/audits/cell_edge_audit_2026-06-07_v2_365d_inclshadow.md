# Cell-by-Cell Edge Audit (v2, window=365d, 2026-06-07)

Source: demo_trades.db, scope: Live + Shadow
Cell key dims: entry_type × session × **pair** × mode
Min N per cell: **20**, Time window: **365d**
Total cells qualified: **1**
Promotion candidates (Wilson lower > 50% AND Bonferroni p < 0.05): **1**
WATCH candidates (BH FDR p < 0.05, Bonferroni 不通過): **0**

## Promotion Candidates

| entry_type | session | pair | mode | N | wins | WR | Wilson [lo, hi] | EV pip | PF | p (Bonf) |
|---|---|---|---|---|---|---|---|---|---|---|
| fib_reversal | Tokyo | USD_JPY | Scalp | 25 | 21 | 84.0% | [65.3%, 93.6%] | +10.24 | 12.18 | 0.0007 |

## All Qualified Cells (sorted by Wilson lower)

| entry_type | session | pair | mode | N (Live/Shadow) | WR | Wilson lower | EV pip | PF | p (raw / Bonf / BH) |
|---|---|---|---|---|---|---|---|---|---|
| fib_reversal | Tokyo | USD_JPY | Scalp | 25 (0/25) | 84.0% | 65.3% | +10.24 | 12.18 | 0.0007 / 0.0007 / 0.0007 |
