# Cell-by-Cell Edge Audit (v2, window=all, 2026-04-27)

Source: demo_trades.db, scope: Live + Shadow
Cell key dims: entry_type × session × **pair** × mode
Min N per cell: **10**, Time window: **all**
Total cells qualified: **5**
Promotion candidates (Wilson lower > 50% AND Bonferroni p < 0.05): **1**
WATCH candidates (BH FDR p < 0.05, Bonferroni 不通過): **0**

## Promotion Candidates

| entry_type | session | pair | mode | N | wins | WR | Wilson [lo, hi] | EV pip | PF | p (Bonf) |
|---|---|---|---|---|---|---|---|---|---|---|
| fib_reversal | Tokyo | USD_JPY | Scalp | 24 | 21 | 87.5% | [69.0%, 95.7%] | +10.82 | 14.60 | 0.0012 |

## All Qualified Cells (sorted by Wilson lower)

| entry_type | session | pair | mode | N (Live/Shadow) | WR | Wilson lower | EV pip | PF | p (raw / Bonf / BH) |
|---|---|---|---|---|---|---|---|---|---|
| fib_reversal | Tokyo | USD_JPY | Scalp | 24 (0/24) | 87.5% | 69.0% | +10.82 | 14.60 | 0.0002 / 0.0012 / 0.0012 |
| bb_rsi_reversion | Tokyo | USD_JPY | Scalp | 10 (10/0) | 70.0% | 39.7% | +4.09 | 3.32 | 0.2059 / 1.0000 / 0.2574 |
| bb_rsi_reversion | London | USD_JPY | Scalp | 11 (11/0) | 54.5% | 28.0% | +1.46 | 2.10 | 0.7630 / 1.0000 / 0.7630 |
| ema_trend_scalp | London | EUR_USD | Scalp | 12 (0/12) | 25.0% | 8.9% | -0.82 | 0.62 | 0.0833 / 0.4163 / 0.1388 |
| ema_trend_scalp | Overlap | EUR_USD | Scalp | 15 (0/15) | 20.0% | 7.0% | -1.47 | 0.42 | 0.0201 / 0.1007 / 0.0503 |
