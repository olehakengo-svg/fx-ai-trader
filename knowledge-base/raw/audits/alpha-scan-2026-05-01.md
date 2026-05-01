# Alpha Scan: 2026-05-01

Source: `https://fx-ai-trader.onrender.com/api/demo/factors` | min_n=5

### strategy x instrument
| strategy | instrument | N | WR% | EV(pip) | PnL(pip) | PF |
|---|---|---|---|---|---|---|
| vol_surge_detector | EUR_USD | 7 | 57.1% | +1.20 | +8.4 | 2.33 |
| vol_momentum_scalp | USD_JPY | 15 | 53.3% | +0.30 | +4.5 | 1.17 |
| bb_rsi_reversion | USD_JPY | 132 | 39.4% | -0.15 | -20.3 | 0.93 |
| vol_surge_detector | USD_JPY | 35 | 42.9% | -0.24 | -8.4 | 0.87 |
| bb_rsi_reversion | EUR_USD | 30 | 36.7% | -0.30 | -9.0 | 0.84 |
| trend_rebound | USD_JPY | 10 | 30.0% | -0.78 | -7.8 | 0.54 |
| bb_rsi_reversion | GBP_USD | 7 | 28.6% | -1.14 | -8.0 | 0.59 |
| trend_rebound | EUR_USD | 6 | 16.7% | -1.85 | -11.1 | 0.28 |
| vix_carry_unwind | USD_JPY | 6 | 33.3% | -3.72 | -22.3 | 0.57 |
| session_time_bias | GBP_USD | 9 | 22.2% | -4.82 | -43.4 | 0.06 |

### hour x instrument
| hour | instrument | N | WR% | EV(pip) | PnL(pip) | PF |
|---|---|---|---|---|---|---|
| 13 | EUR_USD | 6 | 66.7% | +3.40 | +20.4 | 4.40 |
| 9 | USD_JPY | 5 | 60.0% | +2.18 | +10.9 | 2.79 |
| 15 | USD_JPY | 20 | 65.0% | +1.89 | +37.7 | 2.08 |
| 11 | USD_JPY | 16 | 56.2% | +1.22 | +19.5 | 1.85 |
| 2 | USD_JPY | 9 | 44.4% | +1.02 | +9.2 | 1.57 |
| 1 | USD_JPY | 9 | 66.7% | +1.01 | +9.1 | 1.88 |
| 4 | USD_JPY | 6 | 50.0% | +0.87 | +5.2 | 2.24 |
| 7 | USD_JPY | 11 | 54.5% | +0.83 | +9.1 | 1.46 |
| 6 | USD_JPY | 30 | 30.0% | -0.18 | -5.3 | 0.94 |
| 15 | EUR_USD | 9 | 44.4% | -0.26 | -2.3 | 0.83 |
| 10 | EUR_USD | 6 | 33.3% | -0.70 | -4.2 | 0.58 |
| 13 | USD_JPY | 6 | 50.0% | -0.70 | -4.2 | 0.64 |
| 3 | USD_JPY | 13 | 46.2% | -0.74 | -9.6 | 0.75 |
| 12 | USD_JPY | 10 | 30.0% | -0.97 | -9.7 | 0.61 |
| 9 | EUR_USD | 7 | 28.6% | -1.03 | -7.2 | 0.54 |
| 8 | USD_JPY | 11 | 45.5% | -1.34 | -14.8 | 0.66 |
| 12 | EUR_USD | 5 | 20.0% | -1.44 | -7.2 | 0.43 |
| 12 | GBP_USD | 7 | 28.6% | -1.73 | -12.1 | 0.49 |
| 5 | USD_JPY | 17 | 17.6% | -1.92 | -32.6 | 0.25 |
| 16 | USD_JPY | 11 | 27.3% | -2.04 | -22.5 | 0.15 |
| 0 | USD_JPY | 18 | 22.2% | -2.47 | -44.5 | 0.27 |
| 18 | USD_JPY | 8 | 25.0% | -2.61 | -20.9 | 0.31 |
| 17 | USD_JPY | 6 | 16.7% | -2.93 | -17.6 | 0.16 |
| 9 | GBP_USD | 5 | 40.0% | -4.32 | -21.6 | 0.30 |
| 11 | EUR_USD | 6 | 33.3% | -5.23 | -31.4 | 0.14 |
| 6 | GBP_USD | 8 | 12.5% | -7.76 | -62.1 | 0.02 |

### direction x instrument
| direction | instrument | N | WR% | EV(pip) | PnL(pip) | PF |
|---|---|---|---|---|---|---|
| BUY | EUR_USD | 30 | 50.0% | +0.12 | +3.5 | 1.06 |
| BUY | USD_JPY | 98 | 40.8% | -0.34 | -33.6 | 0.86 |
| SELL | USD_JPY | 120 | 39.2% | -0.43 | -51.2 | 0.83 |
| BUY | GBP_USD | 17 | 41.2% | -2.33 | -39.6 | 0.51 |
| SELL | EUR_USD | 19 | 15.8% | -2.50 | -47.5 | 0.19 |
| SELL | GBP_USD | 23 | 17.4% | -5.25 | -120.8 | 0.07 |

### direction x regime
| direction | regime | N | WR% | EV(pip) | PnL(pip) | PF |
|---|---|---|---|---|---|---|
| BUY | RANGE | 85 | 48.2% | +0.14 | +11.9 | 1.05 |
| BUY | TREND_BULL | 31 | 41.9% | +0.10 | +3.0 | 1.04 |
| BUY | TREND_BEAR | 33 | 36.4% | -0.68 | -22.3 | 0.70 |
| SELL | TREND_BULL | 38 | 28.9% | -0.89 | -33.9 | 0.67 |
| SELL | RANGE | 69 | 36.2% | -1.23 | -84.5 | 0.60 |
| SELL | TREND_BEAR | 56 | 32.1% | -1.99 | -111.2 | 0.38 |

## Top Positive EV Cells
- **13 x EUR_USD** — EV=+3.40 pip, N=6, WR=66.7%
- **9 x USD_JPY** — EV=+2.18 pip, N=5, WR=60.0%
- **15 x USD_JPY** — EV=+1.89 pip, N=20, WR=65.0%
- **11 x USD_JPY** — EV=+1.22 pip, N=16, WR=56.2%
- **vol_surge_detector x EUR_USD** — EV=+1.20 pip, N=7, WR=57.1%

## Top Toxic Cells (negative EV)
- **6 x GBP_USD** — EV=-7.76 pip, N=8, WR=12.5%
- **SELL x GBP_USD** — EV=-5.25 pip, N=23, WR=17.4%
- **11 x EUR_USD** — EV=-5.23 pip, N=6, WR=33.3%
- **session_time_bias x GBP_USD** — EV=-4.82 pip, N=9, WR=22.2%
- **9 x GBP_USD** — EV=-4.32 pip, N=5, WR=40.0%

## Related
- [[edge-pipeline]]
- [[changelog]]
- [[lessons/index]]
