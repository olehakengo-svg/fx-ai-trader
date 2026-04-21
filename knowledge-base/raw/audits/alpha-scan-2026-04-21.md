# Alpha Scan: 2026-04-21

Source: `https://fx-ai-trader.onrender.com/api/demo/factors` | min_n=5

### strategy x instrument
| strategy | instrument | N | WR% | EV(pip) | PnL(pip) | PF |
|---|---|---|---|---|---|---|
| vol_surge_detector | EUR_USD | 7 | 57.1% | +1.20 | +8.4 | 2.33 |
| vol_momentum_scalp | USD_JPY | 15 | 53.3% | +0.30 | +4.5 | 1.17 |
| bb_rsi_reversion | USD_JPY | 99 | 41.4% | -0.03 | -2.5 | 0.99 |
| vol_surge_detector | USD_JPY | 35 | 42.9% | -0.24 | -8.4 | 0.87 |
| bb_rsi_reversion | EUR_USD | 22 | 36.4% | -0.48 | -10.6 | 0.75 |
| trend_rebound | USD_JPY | 10 | 30.0% | -0.78 | -7.8 | 0.54 |
| trend_rebound | EUR_USD | 6 | 16.7% | -1.85 | -11.1 | 0.28 |

### hour x instrument
| hour | instrument | N | WR% | EV(pip) | PnL(pip) | PF |
|---|---|---|---|---|---|---|
| 9 | USD_JPY | 5 | 60.0% | +2.18 | +10.9 | 2.79 |
| 1 | USD_JPY | 8 | 75.0% | +1.56 | +12.5 | 2.79 |
| 2 | USD_JPY | 8 | 50.0% | +1.52 | +12.2 | 1.94 |
| 15 | USD_JPY | 18 | 61.1% | +1.52 | +27.3 | 1.78 |
| 11 | USD_JPY | 16 | 56.2% | +1.22 | +19.5 | 1.85 |
| 4 | USD_JPY | 5 | 60.0% | +1.16 | +5.8 | 2.61 |
| 6 | USD_JPY | 19 | 36.8% | +0.96 | +18.3 | 1.43 |
| 7 | USD_JPY | 8 | 62.5% | +0.94 | +7.5 | 1.52 |
| 8 | USD_JPY | 9 | 44.4% | -0.18 | -1.6 | 0.92 |
| 15 | EUR_USD | 8 | 50.0% | -0.28 | -2.2 | 0.84 |
| 13 | USD_JPY | 6 | 50.0% | -0.70 | -4.2 | 0.64 |
| 10 | EUR_USD | 5 | 40.0% | -0.78 | -3.9 | 0.60 |
| 12 | USD_JPY | 10 | 30.0% | -0.97 | -9.7 | 0.61 |
| 12 | GBP_USD | 6 | 33.3% | -1.00 | -6.0 | 0.66 |
| 9 | EUR_USD | 7 | 28.6% | -1.03 | -7.2 | 0.54 |
| 12 | EUR_USD | 5 | 20.0% | -1.44 | -7.2 | 0.43 |
| 3 | USD_JPY | 8 | 50.0% | -2.02 | -16.2 | 0.49 |
| 16 | USD_JPY | 11 | 27.3% | -2.04 | -22.5 | 0.15 |
| 5 | USD_JPY | 11 | 9.1% | -2.29 | -25.2 | 0.14 |
| 0 | USD_JPY | 15 | 20.0% | -2.54 | -38.1 | 0.20 |
| 18 | USD_JPY | 8 | 25.0% | -2.61 | -20.9 | 0.31 |
| 17 | USD_JPY | 6 | 16.7% | -2.93 | -17.6 | 0.16 |
| 11 | EUR_USD | 6 | 33.3% | -5.23 | -31.4 | 0.14 |

### direction x instrument
| direction | instrument | N | WR% | EV(pip) | PnL(pip) | PF |
|---|---|---|---|---|---|---|
| BUY | EUR_USD | 22 | 54.5% | +0.09 | +1.9 | 1.04 |
| BUY | USD_JPY | 74 | 41.9% | -0.20 | -14.8 | 0.91 |
| BUY | GBP_USD | 6 | 50.0% | -0.30 | -1.8 | 0.83 |
| SELL | USD_JPY | 105 | 40.0% | -0.44 | -46.6 | 0.81 |
| SELL | EUR_USD | 19 | 15.8% | -2.50 | -47.5 | 0.19 |
| SELL | GBP_USD | 15 | 6.7% | -6.00 | -90.0 | 0.05 |

### direction x regime
| direction | regime | N | WR% | EV(pip) | PnL(pip) | PF |
|---|---|---|---|---|---|---|
| BUY | RANGE | 51 | 56.9% | +1.88 | +96.0 | 2.00 |
| BUY | TREND_BULL | 23 | 43.5% | +0.49 | +11.3 | 1.38 |
| BUY | TREND_BEAR | 30 | 36.7% | -0.57 | -17.0 | 0.75 |
| SELL | TREND_BULL | 38 | 28.9% | -0.89 | -33.9 | 0.67 |
| SELL | TREND_BEAR | 45 | 35.6% | -1.36 | -61.0 | 0.52 |
| SELL | RANGE | 56 | 33.9% | -1.59 | -89.2 | 0.45 |

## Top Positive EV Cells
- **9 x USD_JPY** — EV=+2.18 pip, N=5, WR=60.0%
- **BUY x RANGE** — EV=+1.88 pip, N=51, WR=56.9%
- **1 x USD_JPY** — EV=+1.56 pip, N=8, WR=75.0%
- **2 x USD_JPY** — EV=+1.52 pip, N=8, WR=50.0%
- **15 x USD_JPY** — EV=+1.52 pip, N=18, WR=61.1%

## Top Toxic Cells (negative EV)
- **SELL x GBP_USD** — EV=-6.00 pip, N=15, WR=6.7%
- **11 x EUR_USD** — EV=-5.23 pip, N=6, WR=33.3%
- **17 x USD_JPY** — EV=-2.93 pip, N=6, WR=16.7%
- **18 x USD_JPY** — EV=-2.61 pip, N=8, WR=25.0%
- **0 x USD_JPY** — EV=-2.54 pip, N=15, WR=20.0%

## Related
- [[edge-pipeline]]
- [[changelog]]
- [[lessons/index]]
