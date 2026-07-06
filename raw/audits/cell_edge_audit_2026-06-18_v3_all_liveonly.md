# Cell-by-Cell Edge Audit (v3, window=all, 2026-06-18)

Source: demo_trades.db, scope: Live only
Cell key dims: entry_type × session × **pair** × mode
Min N per cell: **1**, Time window: **all**
Total cells qualified: **5**
Promotion candidates (Wilson lower > 50% AND Bonferroni p < 0.05): **0**
WATCH candidates (BH FDR p < 0.05, Bonferroni 不通過): **0**

## Promotion Candidates

_No cells passed promotion criteria._

## All Qualified Cells (sorted by Wilson lower)

| entry_type | session | pair | direction | mode | N (Live/Shadow) | WR | Wilson lower | EV pip | PF | p (raw / Bonf / BH) |
|---|---|---|---|---|---|---|---|---|---|---|
| orb_trap | London | GBP_USD | BUY | DT | 1 (1/0) | 100.0% | 20.6% | +16.10 | inf | 0.3173 / 1.0000 / 0.3966 |
| orb_trap | Overlap | GBP_USD | BUY | DT | 1 (1/0) | 100.0% | 20.6% | +18.20 | inf | 0.3173 / 1.0000 / 0.3966 |
| orb_trap | Overlap | EUR_USD | SELL | DT | 1 (1/0) | 100.0% | 20.6% | +11.90 | inf | 0.3173 / 1.0000 / 0.3966 |
| orb_trap | Overlap | GBP_USD | SELL | DT | 2 (2/0) | 50.0% | 9.4% | +3.40 | 1.62 | 1.0000 / 1.0000 / 1.0000 |
| orb_trap | London | GBP_USD | SELL | DT | 1 (1/0) | 0.0% | 0.0% | -7.50 | 0.00 | 0.3173 / 1.0000 / 0.3966 |
