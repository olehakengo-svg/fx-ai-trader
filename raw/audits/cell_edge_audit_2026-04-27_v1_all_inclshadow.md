# Cell-by-Cell Edge Audit (v1, window=all, 2026-04-27)

Source: demo_trades.db, scope: Live + Shadow
Cell key dims: entry_type × session × **spread_quartile** × mode
Min N per cell: **20**, Time window: **all**
Total cells qualified: **3**
Promotion candidates (Wilson lower > 50% AND Bonferroni p < 0.05): **1**
WATCH candidates (BH FDR p < 0.05, Bonferroni 不通過): **0**

## Promotion Candidates

| entry_type | session | spread_quartile | mode | N | wins | WR | Wilson [lo, hi] | EV pip | PF | p (Bonf) |
|---|---|---|---|---|---|---|---|---|---|---|
| fib_reversal | Tokyo | q0 | Scalp | 24 | 21 | 87.5% | [69.0%, 95.7%] | +10.82 | 14.60 | 0.0007 |

## All Qualified Cells (sorted by Wilson lower)

| entry_type | session | spread_quartile | mode | N (Live/Shadow) | WR | Wilson lower | EV pip | PF | p (raw / Bonf / BH) |
|---|---|---|---|---|---|---|---|---|---|
| fib_reversal | Tokyo | q0 | Scalp | 24 (0/24) | 87.5% | 69.0% | +10.82 | 14.60 | 0.0002 / 0.0007 / 0.0007 |
| ema_trend_scalp | Overlap | q0 | Scalp | 28 (0/28) | 17.9% | 7.9% | -1.89 | 0.35 | 0.0007 / 0.0020 / 0.0010 |
| ema_trend_scalp | London | q0 | Scalp | 21 (0/21) | 14.3% | 5.0% | -2.52 | 0.23 | 0.0011 / 0.0032 / 0.0011 |
