# Alpha Scan: 2026-04-30

Source: `https://fx-ai-trader.onrender.com/api/demo/factors` | min_n=5

### strategy x instrument
| strategy | instrument | N | WR% | EV(pip) | PnL(pip) | PF |
|---|---|---|---|---|---|---|
| vol_surge_detector | EUR_USD | 7 | 57.1% | +1.20 | +8.4 | 2.33 |
| vol_momentum_scalp | USD_JPY | 15 | 53.3% | +0.30 | +4.5 | 1.17 |
| bb_rsi_reversion | USD_JPY | 124 | 38.7% | -0.21 | -26.0 | 0.90 |
| vol_surge_detector | USD_JPY | 35 | 42.9% | -0.24 | -8.4 | 0.87 |
| bb_rsi_reversion | EUR_USD | 28 | 35.7% | -0.33 | -9.1 | 0.81 |
| trend_rebound | USD_JPY | 10 | 30.0% | -0.78 | -7.8 | 0.54 |
| bb_rsi_reversion | GBP_USD | 7 | 28.6% | -1.14 | -8.0 | 0.59 |
| trend_rebound | EUR_USD | 6 | 16.7% | -1.85 | -11.1 | 0.28 |
| session_time_bias | GBP_USD | 9 | 22.2% | -4.82 | -43.4 | 0.06 |

### hour x instrument
| hour | instrument | N | WR% | EV(pip) | PnL(pip) | PF |
|---|---|---|---|---|---|---|
| 13 | EUR_USD | 5 | 60.0% | +2.50 | +12.5 | 3.08 |
| 9 | USD_JPY | 5 | 60.0% | +2.18 | +10.9 | 2.79 |
| 15 | USD_JPY | 20 | 65.0% | +1.89 | +37.7 | 2.08 |
| 11 | USD_JPY | 16 | 56.2% | +1.22 | +19.5 | 1.85 |
| 2 | USD_JPY | 9 | 44.4% | +1.02 | +9.2 | 1.57 |
| 1 | USD_JPY | 9 | 66.7% | +1.01 | +9.1 | 1.88 |
| 7 | USD_JPY | 10 | 60.0% | +0.92 | +9.2 | 1.47 |
| 4 | USD_JPY | 6 | 50.0% | +0.87 | +5.2 | 2.24 |
| 6 | USD_JPY | 28 | 28.6% | -0.16 | -4.4 | 0.94 |
| 15 | EUR_USD | 9 | 44.4% | -0.26 | -2.3 | 0.83 |
| 10 | EUR_USD | 6 | 33.3% | -0.70 | -4.2 | 0.58 |
| 13 | USD_JPY | 6 | 50.0% | -0.70 | -4.2 | 0.64 |
| 3 | USD_JPY | 10 | 50.0% | -0.96 | -9.6 | 0.72 |
| 12 | USD_JPY | 10 | 30.0% | -0.97 | -9.7 | 0.61 |
| 9 | EUR_USD | 7 | 28.6% | -1.03 | -7.2 | 0.54 |
| 12 | EUR_USD | 5 | 20.0% | -1.44 | -7.2 | 0.43 |
| 12 | GBP_USD | 7 | 28.6% | -1.73 | -12.1 | 0.49 |
| 16 | USD_JPY | 11 | 27.3% | -2.04 | -22.5 | 0.15 |
| 5 | USD_JPY | 16 | 12.5% | -2.26 | -36.2 | 0.17 |
| 8 | USD_JPY | 10 | 40.0% | -2.50 | -25.0 | 0.42 |
| 18 | USD_JPY | 8 | 25.0% | -2.61 | -20.9 | 0.31 |
| 0 | USD_JPY | 16 | 18.8% | -2.66 | -42.5 | 0.18 |
| 17 | USD_JPY | 6 | 16.7% | -2.93 | -17.6 | 0.16 |
| 9 | GBP_USD | 5 | 40.0% | -4.32 | -21.6 | 0.30 |
| 11 | EUR_USD | 6 | 33.3% | -5.23 | -31.4 | 0.14 |
| 6 | GBP_USD | 7 | 14.3% | -5.66 | -39.6 | 0.03 |

### direction x instrument
| direction | instrument | N | WR% | EV(pip) | PnL(pip) | PF |
|---|---|---|---|---|---|---|
| BUY | EUR_USD | 28 | 50.0% | +0.12 | +3.4 | 1.06 |
| SELL | USD_JPY | 114 | 39.5% | -0.40 | -45.2 | 0.83 |
| BUY | USD_JPY | 93 | 39.8% | -0.48 | -44.3 | 0.81 |
| BUY | GBP_USD | 16 | 43.8% | -1.07 | -17.1 | 0.71 |
| SELL | EUR_USD | 19 | 15.8% | -2.50 | -47.5 | 0.19 |
| SELL | GBP_USD | 23 | 17.4% | -5.25 | -120.8 | 0.07 |

### direction x regime
| direction | regime | N | WR% | EV(pip) | PnL(pip) | PF |
|---|---|---|---|---|---|---|
| BUY | TREND_BULL | 29 | 44.8% | +0.91 | +26.5 | 1.59 |
| BUY | RANGE | 79 | 46.8% | +0.00 | +0.1 | 1.00 |
| BUY | TREND_BEAR | 33 | 36.4% | -0.68 | -22.3 | 0.70 |
| SELL | TREND_BULL | 38 | 28.9% | -0.89 | -33.9 | 0.67 |
| SELL | RANGE | 64 | 35.9% | -1.23 | -78.6 | 0.55 |
| SELL | TREND_BEAR | 55 | 32.7% | -2.02 | -111.1 | 0.38 |

## Top Positive EV Cells
- **13 x EUR_USD** — EV=+2.50 pip, N=5, WR=60.0%
- **9 x USD_JPY** — EV=+2.18 pip, N=5, WR=60.0%
- **15 x USD_JPY** — EV=+1.89 pip, N=20, WR=65.0%
- **11 x USD_JPY** — EV=+1.22 pip, N=16, WR=56.2%
- **vol_surge_detector x EUR_USD** — EV=+1.20 pip, N=7, WR=57.1%

## Top Toxic Cells (negative EV)
- **6 x GBP_USD** — EV=-5.66 pip, N=7, WR=14.3%
- **SELL x GBP_USD** — EV=-5.25 pip, N=23, WR=17.4%
- **11 x EUR_USD** — EV=-5.23 pip, N=6, WR=33.3%
- **session_time_bias x GBP_USD** — EV=-4.82 pip, N=9, WR=22.2%
- **9 x GBP_USD** — EV=-4.32 pip, N=5, WR=40.0%

## Related
- [[edge-pipeline]]
- [[changelog]]
- [[lessons/index]]
