# EV Decomposition — 2026-04-13

## Post-Cutoff FX-Only (XAU excluded, Shadow excluded)
Period: >= 2026-04-08, N=294, WR=35.7%, PnL=-160.1pip

### Pair-Level Summary
| Pair | N | WR | PnL | Avg/trade | PF |
|------|---|-----|------|-----------|-----|
| USD_JPY | 215 | 38.6% | -57.5 | -0.27 | 0.88 |
| EUR_USD | 70 | 27.1% | -102.5 | -1.46 | 0.48 |
| GBP_USD | 8 | 37.5% | +4.3 | +0.54 | 1.13 |

### Mode-Level Summary
| Mode | N | WR | PnL | Avg/trade |
|------|---|-----|------|-----------|
| scalp (1m) | 152 | 42.8% | +40.4 | +0.27 |
| daytrade_gbpusd | 7 | 42.9% | +8.2 | +1.17 |
| scalp_5m | 51 | 23.5% | -65.7 | -1.29 |
| scalp_eur | 53 | 30.2% | -33.6 | -0.63 |
| daytrade | 12 | 50.0% | -32.2 | -2.68 |
| daytrade_eur | 10 | 20.0% | -28.2 | -2.82 |

### Negative EV Hit List (N>=5, sorted by damage)
| Strategy | Pair | N | WR | EV | PnL | Action |
|----------|------|---|-----|------|------|--------|
| dt_bb_rsi_mr | EUR_USD | 7 | 14.3% | -4.09 | -28.6 | **FORCE_DEMOTED** |
| sr_channel_reversal | USD_JPY | 16 | 18.8% | -1.49 | -23.9 | Already FORCE_DEMOTED |
| bb_rsi_reversion | USD_JPY | 76 | 38.2% | -0.28 | -21.0 | **PAIR_DEMOTED** |
| stoch_trend_pullback | USD_JPY | 19 | 31.6% | -0.97 | -18.5 | **FORCE_DEMOTED** |
| ema_trend_scalp | USD_JPY | 7 | 14.3% | -1.81 | -12.7 | boost 1.0x済 |
| bb_rsi_reversion | EUR_USD | 9 | 22.2% | -1.33 | -12.0 | N不足/監視 |
| stoch_trend_pullback | EUR_USD | 9 | 22.2% | -1.02 | -9.2 | FORCE_DEMOTED (global) |

Top 8 negative EV combos = -133.2pip (83% of total loss)

### Positive EV Candidates (N>=5)
| Strategy | Pair | N | WR | EV | PnL |
|----------|------|---|-----|------|------|
| vol_momentum_scalp | USD_JPY | 11 | 72.7% | +1.69 | +18.6 |
| ema_pullback | USD_JPY | 14 | 42.9% | +1.09 | +15.3 |
| fib_reversal | USD_JPY | 25 | 36.0% | +0.94 | +23.4 |
| vol_surge_detector | USD_JPY | 15 | 46.7% | +0.13 | +1.9 |

### Actions Taken (commit e467706)
1. Shadow slot bypass — 全戦略がスロット埋まり時にshadowで入れるように (N蓄積加速)
2. stoch_trend_pullback: UNIVERSAL_SENTINEL→FORCE_DEMOTED
3. dt_bb_rsi_mr: UNIVERSAL_SENTINEL→FORCE_DEMOTED
4. bb_rsi_reversion×USD_JPY: PAIR_PROMOTED→PAIR_DEMOTED

### Key Insight
- Only profitable mode: scalp 1m (+40.4pip, N=152)
- Only profitable pair: GBP_USD (+4.3pip, N=8, insufficient)
- Cutting top 8 negative EV combos would reduce period loss from -160pip to ~-27pip
