# Alpha Scan: 2026-04-29

Source: `https://fx-ai-trader.onrender.com/api/demo/factors` | min_n=5

### strategy x instrument
| strategy | instrument | N | WR% | EV(pip) | PnL(pip) | PF |
|---|---|---|---|---|---|---|
| vol_surge_detector | EUR_USD | 7 | 57.1% | +1.20 | +8.4 | 2.33 |
| vol_momentum_scalp | USD_JPY | 15 | 53.3% | +0.30 | +4.5 | 1.17 |
| vol_surge_detector | USD_JPY | 35 | 42.9% | -0.24 | -8.4 | 0.87 |
| bb_rsi_reversion | USD_JPY | 121 | 38.0% | -0.28 | -33.5 | 0.87 |
| bb_rsi_reversion | GBP_USD | 6 | 33.3% | -0.33 | -2.0 | 0.85 |
| bb_rsi_reversion | EUR_USD | 27 | 33.3% | -0.50 | -13.4 | 0.73 |
| trend_rebound | USD_JPY | 10 | 30.0% | -0.78 | -7.8 | 0.54 |
| trend_rebound | EUR_USD | 6 | 16.7% | -1.85 | -11.1 | 0.28 |
| session_time_bias | GBP_USD | 6 | 16.7% | -5.57 | -33.4 | 0.04 |

### hour x instrument
| hour | instrument | N | WR% | EV(pip) | PnL(pip) | PF |
|---|---|---|---|---|---|---|
| 9 | USD_JPY | 5 | 60.0% | +2.18 | +10.9 | 2.79 |
| 15 | USD_JPY | 20 | 65.0% | +1.89 | +37.7 | 2.08 |
| 11 | USD_JPY | 16 | 56.2% | +1.22 | +19.5 | 1.85 |
| 2 | USD_JPY | 9 | 44.4% | +1.02 | +9.2 | 1.57 |
| 1 | USD_JPY | 9 | 66.7% | +1.01 | +9.1 | 1.88 |
| 4 | USD_JPY | 6 | 50.0% | +0.87 | +5.2 | 2.24 |
| 7 | USD_JPY | 9 | 55.6% | +0.26 | +2.3 | 1.12 |
| 8 | USD_JPY | 9 | 44.4% | -0.18 | -1.6 | 0.92 |
| 6 | USD_JPY | 26 | 26.9% | -0.19 | -5.0 | 0.92 |
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
| 18 | USD_JPY | 8 | 25.0% | -2.61 | -20.9 | 0.31 |
| 0 | USD_JPY | 16 | 18.8% | -2.66 | -42.5 | 0.18 |
| 17 | USD_JPY | 6 | 16.7% | -2.93 | -17.6 | 0.16 |
| 11 | EUR_USD | 6 | 33.3% | -5.23 | -31.4 | 0.14 |
| 6 | GBP_USD | 5 | 20.0% | -5.66 | -28.3 | 0.04 |

### direction x instrument
| direction | instrument | N | WR% | EV(pip) | PnL(pip) | PF |
|---|---|---|---|---|---|---|
| BUY | EUR_USD | 27 | 48.1% | -0.03 | -0.9 | 0.98 |
| BUY | USD_JPY | 89 | 39.3% | -0.32 | -28.4 | 0.86 |
| SELL | USD_JPY | 114 | 39.5% | -0.40 | -45.2 | 0.83 |
| SELL | EUR_USD | 19 | 15.8% | -2.50 | -47.5 | 0.19 |
| BUY | GBP_USD | 13 | 38.5% | -2.65 | -34.4 | 0.34 |
| SELL | GBP_USD | 20 | 15.0% | -5.54 | -110.8 | 0.06 |

### direction x regime
| direction | regime | N | WR% | EV(pip) | PnL(pip) | PF |
|---|---|---|---|---|---|---|
| BUY | TREND_BULL | 26 | 42.3% | +0.35 | +9.2 | 1.24 |
| BUY | RANGE | 74 | 45.9% | +0.16 | +11.7 | 1.06 |
| BUY | TREND_BEAR | 33 | 36.4% | -0.68 | -22.3 | 0.70 |
| SELL | TREND_BULL | 38 | 28.9% | -0.89 | -33.9 | 0.67 |
| SELL | RANGE | 63 | 34.9% | -1.27 | -79.9 | 0.54 |
| SELL | TREND_BEAR | 53 | 34.0% | -1.88 | -99.8 | 0.41 |

## Top Positive EV Cells
- **9 x USD_JPY** — EV=+2.18 pip, N=5, WR=60.0%
- **15 x USD_JPY** — EV=+1.89 pip, N=20, WR=65.0%
- **11 x USD_JPY** — EV=+1.22 pip, N=16, WR=56.2%
- **vol_surge_detector x EUR_USD** — EV=+1.20 pip, N=7, WR=57.1%
- **2 x USD_JPY** — EV=+1.02 pip, N=9, WR=44.4%

## Top Toxic Cells (negative EV)
- **6 x GBP_USD** — EV=-5.66 pip, N=5, WR=20.0%
- **session_time_bias x GBP_USD** — EV=-5.57 pip, N=6, WR=16.7%
- **SELL x GBP_USD** — EV=-5.54 pip, N=20, WR=15.0%
- **11 x EUR_USD** — EV=-5.23 pip, N=6, WR=33.3%
- **17 x USD_JPY** — EV=-2.93 pip, N=6, WR=16.7%

## Related
- [[edge-pipeline]]
- [[changelog]]
- [[lessons/index]]
