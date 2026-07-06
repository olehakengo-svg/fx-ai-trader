# Cell-by-Cell Edge Audit (v3, window=365d, 2026-06-07)

Source: demo_trades.db, scope: Live + Shadow
Cell key dims: entry_type × session × **pair** × mode
Min N per cell: **20**, Time window: **365d**
Total cells qualified: **1**
Promotion candidates (Wilson lower > 50% AND Bonferroni p < 0.05): **1**
WATCH candidates (BH FDR p < 0.05, Bonferroni 不通過): **0**

## Promotion Candidates

| entry_type | session | pair | direction | mode | N | wins | WR | Wilson [lo, hi] | EV pip | PF | p (Bonf) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fib_reversal | Tokyo | USD_JPY | SELL | Scalp | 20 | 18 | 90.0% | [69.9%, 97.2%] | +12.56 | 20.94 | 0.0003 |

## All Qualified Cells (sorted by Wilson lower)

| entry_type | session | pair | direction | mode | N (Live/Shadow) | WR | Wilson lower | EV pip | PF | p (raw / Bonf / BH) |
|---|---|---|---|---|---|---|---|---|---|---|
| fib_reversal | Tokyo | USD_JPY | SELL | Scalp | 20 (0/20) | 90.0% | 69.9% | +12.56 | 20.94 | 0.0003 / 0.0003 / 0.0003 |
