# Cell-by-Cell Edge Audit (v2, window=30d, 2026-04-27)

Source: demo_trades.db, scope: Live + Shadow
Cell key dims: entry_type × session × **pair** × mode
Min N per cell: **15**, Time window: **30d**
Total cells qualified: **2**
Promotion candidates (Wilson lower > 50% AND Bonferroni p < 0.05): **1**
WATCH candidates (BH FDR p < 0.05, Bonferroni 不通過): **0**

## Promotion Candidates

| entry_type | session | pair | mode | N | wins | WR | Wilson [lo, hi] | EV pip | PF | p (Bonf) |
|---|---|---|---|---|---|---|---|---|---|---|
| fib_reversal | Tokyo | USD_JPY | Scalp | 24 | 21 | 87.5% | [69.0%, 95.7%] | +10.82 | 14.60 | 0.0005 |

## All Qualified Cells (sorted by Wilson lower)

| entry_type | session | pair | mode | N (Live/Shadow) | WR | Wilson lower | EV pip | PF | p (raw / Bonf / BH) |
|---|---|---|---|---|---|---|---|---|---|
| fib_reversal | Tokyo | USD_JPY | Scalp | 24 (0/24) | 87.5% | 69.0% | +10.82 | 14.60 | 0.0002 / 0.0005 / 0.0005 |
| ema_trend_scalp | Overlap | EUR_USD | Scalp | 15 (0/15) | 20.0% | 7.0% | -1.47 | 0.42 | 0.0201 / 0.0403 / 0.0201 |
