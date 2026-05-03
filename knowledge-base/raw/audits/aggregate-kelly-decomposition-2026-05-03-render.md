> ⚠️ **Baseline drift acknowledged**: aggregate numbers diverge from the
> 2026-04-29 wiki System State block. Drift documented below; the
> decomposition uses the actual snapshot in the supplied `--db`.

### Drift vs wiki/index.md System State (2026-04-29)

- N mismatch: expected 286, got 346
- WR mismatch: expected 38.11%, got 42.77%
- PnL mismatch: expected -228.6, got -249.1
- Edge mismatch: expected -0.1804, got -0.1404

---
# Aggregate Kelly Decomposition Audit — 2026-05-03

Source DB: `demo_trades.db`
Cutoff: `entry_time >= 2026-04-08` | Scope: Live (`oanda_trade_id != ''`) | Excluded: XAU_USD, EUR_GBP

## Aggregate sanity check

- N=346, wins=148, losses=198, WR=42.77%
- EV=-0.72 pip/trade, PnL=-249.1 pip, edge=-14.04pp, Kelly=+0.0000
- Counts: DEMOTE=0, WATCH=25, OK=10 across 35 qualified cells

## Pair

| pair | N | wins | losses | WR | Wilson_lo_95 | Wilson_up_95 | EV_pip | PnL_pip | PF | BEV_WR | gap_to_BEV_pp | flag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| USD_JPY | 205 | 87 | 118 | 42.44% | 35.87% | 49.28% | -0.60 | -123.80 | 0.76 | 34.40% | +8.04 | WATCH |
| GBP_USD | 55 | 27 | 28 | 49.09% | 36.38% | 61.92% | -1.12 | -61.60 | 0.74 | 37.90% | +11.19 | WATCH |
| EUR_JPY | 6 | 2 | 4 | 33.33% | 9.68% | 70.00% | -9.63 | -57.80 | 0.06 | 33.70% | -0.37 | WATCH |
| EUR_USD | 77 | 31 | 46 | 40.26% | 30.02% | 51.42% | -0.24 | -18.50 | 0.89 | 39.70% | +0.56 | WATCH |

## Strategy x Pair

| entry_type | pair | N | wins | losses | WR | Wilson_lo_95 | Wilson_up_95 | EV_pip | PnL_pip | PF | BEV_WR | gap_to_BEV_pp | flag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vwap_mean_reversion | GBP_USD | 5 | 1 | 4 | 20.00% | 3.62% | 62.45% | -11.62 | -58.10 | 0.02 | 37.90% | -17.90 | WATCH |
| vix_carry_unwind | USD_JPY | 6 | 2 | 4 | 33.33% | 9.68% | 70.00% | -7.03 | -42.20 | 0.41 | 34.40% | -1.07 | WATCH |
| sr_channel_reversal | USD_JPY | 19 | 5 | 14 | 26.32% | 11.81% | 48.79% | -1.60 | -30.40 | 0.30 | 34.40% | -8.08 | WATCH |
| bb_rsi_reversion | USD_JPY | 55 | 23 | 32 | 41.82% | 29.74% | 54.97% | -0.54 | -29.50 | 0.73 | 34.40% | +7.42 | WATCH |
| session_time_bias | GBP_USD | 7 | 2 | 5 | 28.57% | 8.22% | 64.11% | -4.00 | -28.00 | 0.08 | 37.90% | -9.33 | WATCH |
| bb_squeeze_breakout | USD_JPY | 9 | 3 | 6 | 33.33% | 12.06% | 64.58% | -1.40 | -12.60 | 0.34 | 34.40% | -1.07 | WATCH |
| vol_momentum_scalp | USD_JPY | 13 | 8 | 5 | 61.54% | 35.52% | 82.29% | +0.90 | +11.70 | 1.60 | 34.40% | +27.14 | OK |
| vol_surge_detector | EUR_USD | 5 | 4 | 1 | 80.00% | 37.55% | 96.38% | +2.34 | +11.70 | 4.90 | 39.70% | +40.30 | OK |
| bb_rsi_reversion | EUR_USD | 10 | 3 | 7 | 30.00% | 10.78% | 60.32% | -1.14 | -11.40 | 0.53 | 39.70% | -9.70 | WATCH |
| dt_bb_rsi_mr | USD_JPY | 7 | 4 | 3 | 57.14% | 25.05% | 84.18% | +1.50 | +10.50 | 1.84 | 34.40% | +22.74 | OK |
| vol_surge_detector | USD_JPY | 24 | 12 | 12 | 50.00% | 31.43% | 68.57% | -0.37 | -8.80 | 0.80 | 34.40% | +15.60 | WATCH |
| engulfing_bb | USD_JPY | 9 | 3 | 6 | 33.33% | 12.06% | 64.58% | -0.83 | -7.50 | 0.52 | 34.40% | -1.07 | WATCH |
| engulfing_bb | EUR_USD | 5 | 1 | 4 | 20.00% | 3.62% | 62.45% | -1.10 | -5.50 | 0.54 | 39.70% | -19.70 | WATCH |
| v_reversal | USD_JPY | 5 | 1 | 4 | 20.00% | 3.62% | 62.45% | -0.98 | -4.90 | 0.64 | 34.40% | -14.40 | WATCH |
| trend_rebound | USD_JPY | 7 | 3 | 4 | 42.86% | 15.82% | 74.95% | -0.54 | -3.80 | 0.71 | 34.40% | +8.46 | WATCH |
| ema_trend_scalp | EUR_USD | 10 | 4 | 6 | 40.00% | 16.82% | 68.73% | +0.35 | +3.50 | 1.20 | 39.70% | +0.30 | OK |
| sr_channel_reversal | EUR_USD | 7 | 2 | 5 | 28.57% | 8.22% | 64.11% | -0.49 | -3.40 | 0.80 | 39.70% | -11.13 | WATCH |
| fib_reversal | EUR_USD | 12 | 6 | 6 | 50.00% | 25.38% | 74.62% | +0.26 | +3.10 | 1.11 | 39.70% | +10.30 | OK |
| bb_squeeze_breakout | EUR_USD | 5 | 2 | 3 | 40.00% | 11.76% | 76.93% | +0.56 | +2.80 | 1.35 | 39.70% | +0.30 | OK |
| trend_rebound | EUR_USD | 7 | 3 | 4 | 42.86% | 15.82% | 74.95% | +0.30 | +2.10 | 1.16 | 39.70% | +3.16 | OK |
| stoch_trend_pullback | EUR_USD | 8 | 3 | 5 | 37.50% | 13.68% | 69.43% | +0.25 | +2.00 | 1.13 | 39.70% | -2.20 | OK |
| stoch_trend_pullback | USD_JPY | 15 | 6 | 9 | 40.00% | 19.82% | 64.25% | -0.13 | -2.00 | 0.92 | 34.40% | +5.60 | WATCH |
| fib_reversal | USD_JPY | 11 | 5 | 6 | 45.45% | 21.27% | 71.99% | -0.17 | -1.90 | 0.92 | 34.40% | +11.05 | WATCH |

## Session

| session | N | wins | losses | WR | Wilson_lo_95 | Wilson_up_95 | EV_pip | PnL_pip | PF | BEV_WR | gap_to_BEV_pp | flag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| London | 143 | 59 | 84 | 41.26% | 33.52% | 49.45% | -1.16 | -165.80 | 0.63 | 36.91% | +4.35 | WATCH |
| Tokyo | 72 | 25 | 47 | 34.72% | 24.75% | 46.24% | -1.03 | -74.10 | 0.70 | 34.83% | -0.11 | WATCH |
| Asia_early | 16 | 9 | 7 | 56.25% | 33.18% | 76.90% | -0.47 | -7.50 | 0.77 | 34.62% | +21.63 | WATCH |
| NY | 18 | 7 | 11 | 38.89% | 20.30% | 61.38% | -0.27 | -4.80 | 0.88 | 34.75% | +4.14 | WATCH |
| overlap_LN | 97 | 48 | 49 | 49.48% | 39.75% | 59.26% | +0.03 | +3.10 | 1.01 | 36.43% | +13.05 | OK |

## MTF Regime label

| regime | N | wins | losses | WR | Wilson_lo_95 | Wilson_up_95 | EV_pip | PnL_pip | PF | BEV_WR | gap_to_BEV_pp | flag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| range | 173 | 70 | 103 | 40.46% | 33.43% | 47.91% | -0.94 | -162.10 | 0.72 | 37.43% | +3.03 | WATCH |
| bull | 98 | 40 | 58 | 40.82% | 31.61% | 50.71% | -1.04 | -101.60 | 0.66 | 35.13% | +5.69 | WATCH |
| mixed | 75 | 38 | 37 | 50.67% | 39.60% | 61.67% | +0.19 | +14.60 | 1.10 | 34.40% | +16.27 | OK |

## Top 5 PnL-destroyer cells

1. `session` session=London | N=143 | PnL=-165.8 | EV=-1.16 | WR=41.26% | flag=WATCH
2. `regime` regime=range | N=173 | PnL=-162.1 | EV=-0.94 | WR=40.46% | flag=WATCH
3. `pair` pair=USD_JPY | N=205 | PnL=-123.8 | EV=-0.60 | WR=42.44% | flag=WATCH
4. `regime` regime=bull | N=98 | PnL=-101.6 | EV=-1.04 | WR=40.82% | flag=WATCH
5. `session` session=Tokyo | N=72 | PnL=-74.1 | EV=-1.03 | WR=34.72% | flag=WATCH

## DEMOTE list

_No cells met the DEMOTE threshold._

## Sensitivity check

- Excluding all trades touched by DEMOTE cells removes 0 trades.
- Hypothetical aggregate after DEMOTE exclusion: N=346, WR=42.77%, EV=-0.72, PnL=-249.1, edge=-14.04pp, Kelly=+0.0000
- Kelly remains <= 0 unless the recomputed value above is strictly positive.

## Limitations

- Cells with N < 8 are WATCH-only even when they are economically negative.
- Session and regime rows use trade-count-weighted BEV_WR because they mix multiple pairs.
- DEMOTE cells overlap across axes; the sensitivity check excludes the union of affected trades.
