# Cell-by-Cell Edge Audit (v3, window=all, 2026-06-18)

Source: demo_trades.db, scope: Live + Shadow
Cell key dims: entry_type × session × **pair** × mode
Min N per cell: **1**, Time window: **all**
Total cells qualified: **12**
Promotion candidates (Wilson lower > 50% AND Bonferroni p < 0.05): **0**
WATCH candidates (BH FDR p < 0.05, Bonferroni 不通過): **0**

## Promotion Candidates

_No cells passed promotion criteria._

## All Qualified Cells (sorted by Wilson lower)

| entry_type | session | pair | direction | mode | N (Live/Shadow) | WR | Wilson lower | EV pip | PF | p (raw / Bonf / BH) |
|---|---|---|---|---|---|---|---|---|---|---|
| orb_trap | Overlap | GBP_USD | SELL | DT | 19 (2/17) | 73.7% | 51.2% | +9.44 | 9.04 | 0.0389 / 0.4674 / 0.2337 |
| orb_trap | London | GBP_USD | BUY | DT | 4 (1/3) | 75.0% | 30.1% | +8.22 | 7.58 | 0.3173 / 1.0000 / 0.4760 |
| orb_trap | London | GBP_USD | SELL | DT | 3 (1/2) | 66.7% | 20.8% | +14.17 | 6.67 | 0.5637 / 1.0000 / 0.7516 |
| orb_trap | Overlap | GBP_USD | BUY | DT | 1 (1/0) | 100.0% | 20.6% | +18.20 | inf | 0.3173 / 1.0000 / 0.4760 |
| orb_trap | Overlap | EUR_USD | SELL | DT | 4 (1/3) | 50.0% | 15.0% | -0.62 | 0.85 | 1.0000 / 1.0000 / 1.0000 |
| orb_trap | Overlap | EUR_USD | BUY | DT | 2 (0/2) | 50.0% | 9.4% | -3.80 | 0.28 | 1.0000 / 1.0000 / 1.0000 |
| orb_trap | Overlap | USD_JPY | BUY | DT | 2 (0/2) | 50.0% | 9.4% | -2.05 | 0.80 | 1.0000 / 1.0000 / 1.0000 |
| orb_trap | London | EUR_USD | SELL | DT | 13 (0/13) | 15.4% | 4.3% | -4.02 | 0.26 | 0.0126 / 0.1507 / 0.1507 |
| orb_trap | London | USD_JPY | BUY | DT | 1 (0/1) | 0.0% | 0.0% | -7.60 | 0.00 | 0.3173 / 1.0000 / 0.4760 |
| orb_trap | London | EUR_USD | BUY | DT | 3 (0/3) | 0.0% | 0.0% | -4.10 | 0.00 | 0.0833 / 0.9992 / 0.3331 |
| orb_trap | Overlap | USD_JPY | SELL | DT | 2 (0/2) | 0.0% | 0.0% | -7.10 | 0.00 | 0.1573 / 1.0000 / 0.4719 |
| orb_trap | NewYork | GBP_USD | SELL | DT | 1 (0/1) | 0.0% | 0.0% | -5.90 | 0.00 | 0.3173 / 1.0000 / 0.4760 |
