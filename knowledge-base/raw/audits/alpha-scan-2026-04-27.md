# Alpha Scan: 2026-04-27

Source: `https://fx-ai-trader.onrender.com/api/demo/factors` | min_n=5

### strategy x instrument
| strategy | instrument | N | WR% | EV(pip) | PnL(pip) | PF |
|---|---|---|---|---|---|---|
| vol_surge_detector | EUR_USD | 7 | 57.1% | +1.20 | +8.4 | 2.33 |
| vol_momentum_scalp | USD_JPY | 15 | 53.3% | +0.30 | +4.5 | 1.17 |
| bb_rsi_reversion | USD_JPY | 110 | 40.9% | -0.04 | -4.7 | 0.98 |
| vol_surge_detector | USD_JPY | 35 | 42.9% | -0.24 | -8.4 | 0.87 |
| bb_rsi_reversion | GBP_USD | 6 | 33.3% | -0.33 | -2.0 | 0.85 |
| bb_rsi_reversion | EUR_USD | 27 | 33.3% | -0.50 | -13.4 | 0.73 |
| trend_rebound | USD_JPY | 10 | 30.0% | -0.78 | -7.8 | 0.54 |
| trend_rebound | EUR_USD | 6 | 16.7% | -1.85 | -11.1 | 0.28 |

### hour x instrument
| hour | instrument | N | WR% | EV(pip) | PnL(pip) | PF |
|---|---|---|---|---|---|---|
| 9 | USD_JPY | 5 | 60.0% | +2.18 | +10.9 | 2.79 |
| 15 | USD_JPY | 20 | 65.0% | +1.89 | +37.7 | 2.08 |
| 1 | USD_JPY | 8 | 75.0% | +1.56 | +12.5 | 2.79 |
| 11 | USD_JPY | 16 | 56.2% | +1.22 | +19.5 | 1.85 |
| 4 | USD_JPY | 5 | 60.0% | +1.16 | +5.8 | 2.61 |
| 2 | USD_JPY | 9 | 44.4% | +1.02 | +9.2 | 1.57 |
| 6 | USD_JPY | 22 | 31.8% | +0.35 | +7.8 | 1.15 |
| 7 | USD_JPY | 9 | 55.6% | +0.26 | +2.3 | 1.12 |
| 8 | USD_JPY | 9 | 44.4% | -0.18 | -1.6 | 0.92 |
| 15 | EUR_USD | 9 | 44.4% | -0.26 | -2.3 | 0.83 |
| 10 | EUR_USD | 6 | 33.3% | -0.70 | -4.2 | 0.58 |
| 13 | USD_JPY | 6 | 50.0% | -0.70 | -4.2 | 0.64 |
| 12 | USD_JPY | 10 | 30.0% | -0.97 | -9.7 | 0.61 |
| 9 | EUR_USD | 7 | 28.6% | -1.03 | -7.2 | 0.54 |
| 12 | EUR_USD | 5 | 20.0% | -1.44 | -7.2 | 0.43 |
| 12 | GBP_USD | 7 | 28.6% | -1.73 | -12.1 | 0.49 |
| 16 | USD_JPY | 11 | 27.3% | -2.04 | -22.5 | 0.15 |
| 3 | USD_JPY | 9 | 44.4% | -2.13 | -19.2 | 0.45 |
| 5 | USD_JPY | 12 | 8.3% | -2.38 | -28.6 | 0.13 |
| 0 | USD_JPY | 15 | 20.0% | -2.54 | -38.1 | 0.20 |
| 18 | USD_JPY | 8 | 25.0% | -2.61 | -20.9 | 0.31 |
| 17 | USD_JPY | 6 | 16.7% | -2.93 | -17.6 | 0.16 |
| 11 | EUR_USD | 6 | 33.3% | -5.23 | -31.4 | 0.14 |

### direction x instrument
| direction | instrument | N | WR% | EV(pip) | PnL(pip) | PF |
|---|---|---|---|---|---|---|
| BUY | EUR_USD | 27 | 48.1% | -0.03 | -0.9 | 0.98 |
| BUY | USD_JPY | 82 | 41.5% | -0.13 | -10.9 | 0.94 |
| SELL | USD_JPY | 109 | 40.4% | -0.40 | -43.5 | 0.82 |
| SELL | EUR_USD | 19 | 15.8% | -2.50 | -47.5 | 0.19 |
| BUY | GBP_USD | 13 | 38.5% | -2.65 | -34.4 | 0.34 |
| SELL | GBP_USD | 18 | 11.1% | -5.73 | -103.2 | 0.06 |

### direction x regime
| direction | regime | N | WR% | EV(pip) | PnL(pip) | PF |
|---|---|---|---|---|---|---|
| BUY | TREND_BULL | 25 | 44.0% | +0.50 | +12.6 | 1.35 |
| BUY | RANGE | 68 | 48.5% | +0.38 | +25.8 | 1.13 |
| BUY | TREND_BEAR | 33 | 36.4% | -0.68 | -22.3 | 0.70 |
| SELL | TREND_BULL | 38 | 28.9% | -0.89 | -33.9 | 0.67 |
| SELL | RANGE | 60 | 35.0% | -1.39 | -83.4 | 0.50 |
| SELL | TREND_BEAR | 49 | 34.7% | -1.78 | -87.0 | 0.44 |

## Top Positive EV Cells
- **9 x USD_JPY** — EV=+2.18 pip, N=5, WR=60.0%
- **15 x USD_JPY** — EV=+1.89 pip, N=20, WR=65.0%
- **1 x USD_JPY** — EV=+1.56 pip, N=8, WR=75.0%
- **11 x USD_JPY** — EV=+1.22 pip, N=16, WR=56.2%
- **vol_surge_detector x EUR_USD** — EV=+1.20 pip, N=7, WR=57.1%

## Top Toxic Cells (negative EV)
- **SELL x GBP_USD** — EV=-5.73 pip, N=18, WR=11.1%
- **11 x EUR_USD** — EV=-5.23 pip, N=6, WR=33.3%
- **17 x USD_JPY** — EV=-2.93 pip, N=6, WR=16.7%
- **BUY x GBP_USD** — EV=-2.65 pip, N=13, WR=38.5%
- **18 x USD_JPY** — EV=-2.61 pip, N=8, WR=25.0%

## Related
- [[edge-pipeline]]
- [[changelog]]
- [[lessons/index]]
