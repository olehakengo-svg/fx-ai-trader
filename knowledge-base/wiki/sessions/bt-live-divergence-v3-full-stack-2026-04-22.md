# Full-Stack Fresh BT vs Live Divergence (v3) — 2026-04-22

**BT sources** (all scopes)
- DT 15m × 365d: USD_JPY, EUR_USD, GBP_USD, EUR_JPY, GBP_JPY, EUR_GBP(0trades)
- Scalp 1m / 5m × 180d: 6 pairs (EUR_GBP=0trades)
**Live source**: /api/demo/trades N=2505 (all) / 412 (is_shadow=0 only, XAU excluded)
**Cutoff**: 2026-04-16 (post = entry_time > cutoff, fidelity)
**Cells**: BT=233, live-matched ALL=19, POST=0
**Ranking**: |ΔEV| × √N_live

## §A. ALL Live period (2026-04-02 ~ 2026-04-22)

## LIVE < BT (top 20)

| # | Strategy×Pair [scope] | BT(N/WR/EV) | Live(N/WR/EV) | ΔWR | ΔEV | z | p | Wilson95 | PnL |
|---|---|---|---|---:|---:|---:|---:|---|---:|
| 1 | dt_sr_channel_reversal×GBP_USD [DT_15m] | 56/55.4%/-0.079 | 4/0.0%/-8.950 | -55.4pp | -8.871 | -2.14 | 0.0322 | [0.0, 49.0] | -35.8 |
| 2 | session_time_bias×GBP_USD [DT_15m] | 384/58.1%/-0.034 | 4/0.0%/-6.450 | -58.1pp | -6.416 | -2.34 | 0.0194 | [0.0, 49.0] | -25.8 |
| 3 | v_reversal×USD_JPY [Scalp_1m] | 13/61.5%/-0.051 | 3/0.0%/-3.367 | -61.5pp | -3.316 | -1.92 | 0.0548 | [0.0, 56.2] | -10.1 |
| 4 | bb_rsi_reversion×EUR_USD [Scalp_5m] | 45/53.3%/-0.111 | 53/37.7%/-0.742 | -15.6pp | -0.631 | -1.54 | 0.1227 | [25.9, 51.2] | -39.3 |
| 5 | trend_rebound×EUR_USD [Scalp_1m] | 8/75.0%/+0.205 | 7/28.6%/-1.429 | -46.4pp | -1.634 | -1.80 | 0.0721 | [8.2, 64.1] | -10.0 |
| 6 | bb_rsi_reversion×EUR_USD [Scalp_1m] | 245/51.4%/-0.292 | 53/37.7%/-0.742 | -13.7pp | -0.450 | -1.80 | 0.0712 | [25.9, 51.2] | -39.3 |
| 7 | trend_rebound×USD_JPY [Scalp_1m] | 21/76.2%/+0.192 | 8/37.5%/-0.900 | -38.7pp | -1.092 | -1.96 | 0.0500 | [13.7, 69.4] | -7.2 |
| 8 | mtf_reversal_confluence×EUR_USD [Scalp_1m] | 7/71.4%/-0.007 | 3/33.3%/-0.800 | -38.1pp | -0.793 | -1.13 | 0.2602 | [6.1, 79.2] | -2.4 |
| 9 | vol_surge_detector×USD_JPY [Scalp_5m] | 19/57.9%/-0.096 | 33/45.5%/-0.236 | -12.4pp | -0.140 | -0.86 | 0.3874 | [29.8, 62.0] | -7.8 |

## LIVE > BT (top 10)

| # | Strategy×Pair [scope] | BT(N/WR/EV) | Live(N/WR/EV) | ΔWR | ΔEV | z | p | Wilson95 | PnL |
|---|---|---|---|---:|---:|---:|---:|---|---:|
| 1 | bb_rsi_reversion×USD_JPY [Scalp_1m] | 466/47.2%/-0.381 | 198/49.0%/+0.102 | +1.8pp | +0.483 | +0.42 | 0.6727 | [42.1, 55.9] | +20.2 |
| 2 | mtf_reversal_confluence×USD_JPY [Scalp_1m] | 21/57.1%/-0.230 | 5/80.0%/+2.800 | +22.9pp | +3.030 | +0.95 | 0.3443 | [37.6, 96.4] | +14.0 |
| 3 | mtf_reversal_confluence×USD_JPY [Scalp_5m] | 8/62.5%/+0.132 | 5/80.0%/+2.800 | +17.5pp | +2.668 | +0.67 | 0.5060 | [37.6, 96.4] | +14.0 |
| 4 | dt_sr_channel_reversal×USD_JPY [DT_15m] | 72/40.3%/-0.378 | 4/75.0%/+2.525 | +34.7pp | +2.903 | +1.37 | 0.1713 | [30.1, 95.4] | +10.1 |
| 5 | bb_rsi_reversion×USD_JPY [Scalp_5m] | 161/46.6%/-0.215 | 198/49.0%/+0.102 | +2.4pp | +0.317 | +0.45 | 0.6521 | [42.1, 55.9] | +20.2 |
| 6 | vol_surge_detector×EUR_USD [Scalp_1m] | 55/54.5%/-0.326 | 7/57.1%/+0.786 | +2.6pp | +1.112 | +0.13 | 0.8947 | [25.0, 84.2] | +5.5 |
| 7 | vol_surge_detector×EUR_USD [Scalp_5m] | 29/58.6%/-0.149 | 7/57.1%/+0.786 | -1.5pp | +0.935 | -0.07 | 0.9440 | [25.0, 84.2] | +5.5 |
| 8 | vol_surge_detector×USD_JPY [Scalp_1m] | 55/49.1%/-0.644 | 33/45.5%/-0.236 | -3.6pp | +0.408 | -0.33 | 0.7403 | [29.8, 62.0] | -7.8 |
| 9 | vol_momentum_scalp×USD_JPY [Scalp_5m] | 37/54.1%/-0.237 | 15/53.3%/+0.300 | -0.8pp | +0.537 | -0.05 | 0.9599 | [30.1, 75.2] | +4.5 |
| 10 | vol_momentum_scalp×USD_JPY [Scalp_1m] | 257/61.9%/-0.147 | 15/53.3%/+0.300 | -8.6pp | +0.447 | -0.66 | 0.5076 | [30.1, 75.2] | +4.5 |

## §B. POST-Cutoff (2026-04-17+)

## LIVE < BT (top 20)

| # | Strategy×Pair [scope] | BT(N/WR/EV) | Live(N/WR/EV) | ΔWR | ΔEV | z | p | Wilson95 | PnL |
|---|---|---|---|---:|---:|---:|---:|---|---:|

## LIVE > BT (top 10)

| # | Strategy×Pair [scope] | BT(N/WR/EV) | Live(N/WR/EV) | ΔWR | ΔEV | z | p | Wilson95 | PnL |
|---|---|---|---|---:|---:|---:|---:|---|---:|

## §C. Bonferroni-filtered significant (neg side)

**ALL**: M=14, α/M=0.00357

**POST**: M=0, α/M=0.05000

## §D. BT Scope Aggregates

| Scope | Cells | ΣN | mean_WR | mean_EV |
|---|---:|---:|---:|---:|
| DT_15m | 91 | 8308 | 62.0% | +0.217 |
| Scalp_1m | 63 | 11547 | 55.2% | -0.288 |
| Scalp_5m | 52 | 2765 | 56.6% | -0.115 |

## §E. Per-pair best/worst BT cells

### EUR_JPY
| Strategy | Scope | N | WR | EV | PnL_est |
|---|---|---:|---:|---:|---:|
| vwap_mean_reversion | DT_15m | 223 | 68.2% | **+0.672** | +149.9 |
| vol_momentum_scalp | Scalp_5m | 41 | 80.5% | **+0.550** | +22.6 |
| dual_sr_bounce | DT_15m | 118 | 66.1% | **+0.188** | +22.2 |
| sr_fib_confluence | DT_15m | 193 | 63.2% | **+0.152** | +29.3 |
| htf_false_breakout | DT_15m | 34 | 61.8% | **+0.087** | +3.0 |
*... bottom 3:*
| vol_surge_detector | Scalp_1m | 42 | 54.8% | -0.357 | -15.0 |
| dt_fib_reversal | DT_15m | 77 | 48.1% | -0.362 | -27.9 |
| fib_reversal | Scalp_1m | 227 | 44.1% | -0.407 | -92.4 |
### EUR_USD
| Strategy | Scope | N | WR | EV | PnL_est |
|---|---|---:|---:|---:|---:|
| vwap_mean_reversion | DT_15m | 203 | 70.9% | **+0.934** | +189.6 |
| post_news_vol | DT_15m | 24 | 70.8% | **+0.814** | +19.5 |
| trendline_sweep | DT_15m | 51 | 78.4% | **+0.676** | +34.5 |
| session_time_bias | DT_15m | 391 | 63.7% | **+0.180** | +70.4 |
| xs_momentum | DT_15m | 237 | 62.4% | **+0.103** | +24.4 |
*... bottom 3:*
| vol_surge_detector | Scalp_1m | 55 | 54.5% | -0.326 | -17.9 |
| orb_trap | DT_15m | 29 | 34.5% | -0.465 | -13.5 |
| macdh_reversal | Scalp_1m | 23 | 34.8% | -0.707 | -16.3 |
### GBP_JPY
| Strategy | Scope | N | WR | EV | PnL_est |
|---|---|---:|---:|---:|---:|
| vwap_mean_reversion | DT_15m | 267 | 78.3% | **+1.025** | +273.7 |
| htf_false_breakout | DT_15m | 34 | 76.5% | **+0.683** | +23.2 |
| bb_squeeze_breakout | Scalp_1m | 58 | 72.4% | **+0.312** | +18.1 |
| dt_fib_reversal | DT_15m | 68 | 70.6% | **+0.301** | +20.5 |
| ema200_trend_reversal | DT_15m | 45 | 73.3% | **+0.292** | +13.1 |
*... bottom 3:*
| stoch_trend_pullback | Scalp_5m | 20 | 50.0% | -0.178 | -3.6 |
| sr_channel_reversal | Scalp_5m | 62 | 51.6% | -0.209 | -13.0 |
| vol_surge_detector | Scalp_1m | 42 | 50.0% | -0.397 | -16.7 |
### GBP_USD
| Strategy | Scope | N | WR | EV | PnL_est |
|---|---|---:|---:|---:|---:|
| vwap_mean_reversion | DT_15m | 214 | 67.3% | **+0.848** | +181.5 |
| turtle_soup | DT_15m | 46 | 67.4% | **+0.543** | +25.0 |
| gbp_deep_pullback | DT_15m | 100 | 60.0% | **+0.499** | +49.9 |
| wick_imbalance_reversion | DT_15m | 38 | 81.6% | **+0.463** | +17.6 |
| trendline_sweep | DT_15m | 101 | 69.3% | **+0.368** | +37.2 |
*... bottom 3:*
| bb_rsi_reversion | Scalp_1m | 327 | 37.3% | -0.837 | -273.7 |
| vol_surge_detector | Scalp_1m | 79 | 44.3% | -1.018 | -80.4 |
| macdh_reversal | Scalp_1m | 33 | 33.3% | -1.027 | -33.9 |
### USD_JPY
| Strategy | Scope | N | WR | EV | PnL_est |
|---|---|---:|---:|---:|---:|
| streak_reversal | DT_15m | 462 | 72.1% | **+1.339** | +618.6 |
| vwap_mean_reversion | DT_15m | 130 | 71.5% | **+1.036** | +134.7 |
| vix_carry_unwind | DT_15m | 106 | 69.8% | **+0.574** | +60.8 |
| bb_squeeze_breakout | Scalp_5m | 22 | 72.7% | **+0.252** | +5.5 |
| trend_rebound | Scalp_1m | 21 | 76.2% | **+0.192** | +4.0 |
*... bottom 3:*
| fib_reversal | Scalp_1m | 154 | 48.7% | -0.430 | -66.2 |
| vol_surge_detector | Scalp_1m | 55 | 49.1% | -0.644 | -35.4 |
| macdh_reversal | Scalp_1m | 35 | 42.9% | -0.650 | -22.8 |