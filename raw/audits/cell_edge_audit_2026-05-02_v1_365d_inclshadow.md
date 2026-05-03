# Cell-by-Cell Edge Audit (v1, window=365d, 2026-05-02)

Source: demo_trades.db, scope: Live + Shadow
Cell key dims: entry_type × session × **spread_quartile** × mode
Min N per cell: **20**, Time window: **365d**
Total cells qualified: **3**
Promotion candidates (Wilson lower > 50% AND Bonferroni p < 0.05): **1**
WATCH candidates (BH FDR p < 0.05, Bonferroni 不通過): **0**

## Promotion Candidates

| entry_type | session | spread_quartile | mode | N | wins | WR | Wilson [lo, hi] | EV pip | PF | p (Bonf) |
|---|---|---|---|---|---|---|---|---|---|---|
| fib_reversal | Tokyo | q0 | Scalp | 25 | 21 | 84.0% | [65.3%, 93.6%] | +10.24 | 12.18 | 0.0020 |

## All Qualified Cells (sorted by Wilson lower)

| entry_type | session | spread_quartile | mode | N (Live/Shadow) | WR | Wilson lower | EV pip | PF | p (raw / Bonf / BH) |
|---|---|---|---|---|---|---|---|---|---|
| fib_reversal | Tokyo | q0 | Scalp | 25 (0/25) | 84.0% | 65.3% | +10.24 | 12.18 | 0.0007 / 0.0020 / 0.0010 |
| ema_trend_scalp | London | q0 | Scalp | 33 (0/33) | 24.2% | 12.8% | -1.16 | 0.60 | 0.0031 / 0.0092 / 0.0031 |
| ema_trend_scalp | Overlap | q0 | Scalp | 29 (0/29) | 17.2% | 7.6% | -1.99 | 0.33 | 0.0004 / 0.0013 / 0.0010 |
