# 包括的BT スキャン結果 — 全戦略×全ペア (2026-04-14)

**データ**: Massive API 365日 15m足 (DT mode)
**ペア**: USD_JPY, EUR_USD, GBP_USD, EUR_JPY, EUR_GBP
**統計**: entry_type別 N/WR/EV/PF/PnL (摩擦込み)

## STRONG (N≥10, EV>0.3, PF>1.2)

| Strategy | Pair | N | WR | EV | PF | PnL |
|---|---|---|---|---|---|---|
| post_news_vol | GBP_USD | 26 | 88.5% | +1.762 | 4.38 | +45.8p |
| gbp_deep_pullback | GBP_USD | 77 | 75.3% | +1.064 | 2.00 | +81.9p |
| trendline_sweep | EUR_USD | 73 | 80.8% | +0.927 | 2.52 | +67.7p |
| orb_trap | USD_JPY | 19 | 84.2% | +0.866 | 3.66 | +16.5p |
| post_news_vol | EUR_USD | 28 | 71.4% | +0.817 | 1.68 | +22.9p |
| doji_breakout | GBP_USD | 23 | 78.3% | +0.724 | 2.47 | +16.7p |
| htf_false_breakout | USD_JPY | 20 | 80.0% | +0.660 | 3.16 | +13.2p |
| squeeze_release_momentum | EUR_USD | 15 | 73.3% | +0.656 | 2.68 | +9.8p |
| trendline_sweep | GBP_USD | 134 | 73.1% | +0.599 | 1.68 | +80.3p |
| **session_time_bias** | **USD_JPY** | **157** | **79.0%** | **+0.580** | **2.46** | **+91.1p** |
| htf_false_breakout | GBP_USD | 24 | 75.0% | +0.552 | 1.88 | +13.3p |
| ema200_trend_reversal | EUR_USD | 12 | 75.0% | +0.410 | 1.87 | +4.9p |
| dt_fib_reversal | EUR_USD | 10 | 80.0% | +0.407 | 1.96 | +4.1p |
| turtle_soup | GBP_USD | 76 | 69.7% | +0.386 | 1.48 | +29.3p |
| dt_fib_reversal | GBP_USD | 21 | 76.2% | +0.374 | 1.86 | +7.9p |
| london_ny_swing | GBP_USD | 11 | 72.7% | +0.362 | 1.47 | +4.0p |
| htf_false_breakout | EUR_USD | 15 | 80.0% | +0.352 | 1.42 | +5.3p |
| doji_breakout | USD_JPY | 21 | 61.9% | +0.338 | 1.40 | +7.1p |

## GOOD (N≥10, EV>0, PF>1.0)

| Strategy | Pair | N | WR | EV | PF | PnL |
|---|---|---|---|---|---|---|
| dual_sr_bounce | USD_JPY | 118 | 70.3% | +0.280 | 1.50 | +33.0p |
| xs_momentum | USD_JPY | 342 | 68.7% | +0.270 | 1.43 | +92.3p |
| sr_fib_confluence | USD_JPY | 220 | 67.7% | +0.252 | 1.44 | +55.4p |
| xs_momentum | EUR_USD | 228 | 68.0% | +0.225 | 1.36 | +51.4p |
| **session_time_bias** | **EUR_USD** | **566** | **69.6%** | **+0.215** | **1.34** | **+121.7p** |
| vix_carry_unwind | USD_JPY | 49 | 67.3% | +0.212 | 1.19 | +10.4p |
| dt_sr_channel_reversal | EUR_JPY | 362 | 63.8% | +0.178 | 1.39 | +64.6p |
| london_fix_reversal | EUR_USD | 48 | 66.7% | +0.161 | 1.33 | +7.7p |
| vol_spike_mr | USD_JPY | 130 | 64.6% | +0.148 | 1.26 | +19.3p |
| **session_time_bias** | **GBP_USD** | **516** | **67.1%** | **+0.113** | **1.16** | **+58.4p** |
| sr_fib_confluence | EUR_USD | 262 | 64.9% | +0.103 | 1.16 | +27.0p |
| london_fix_reversal | USD_JPY | 64 | 60.9% | +0.079 | 1.14 | +5.1p |

## AVOID (EV<0)

| Strategy | Pair | N | WR | EV | PF | PnL |
|---|---|---|---|---|---|---|
| dt_bb_rsi_mr | USD_JPY | 319 | 54.2% | -0.023 | 0.96 | -7.3p |
| dt_bb_rsi_mr | EUR_USD | 102 | 52.0% | -0.077 | 0.87 | -7.9p |
| dt_bb_rsi_mr | GBP_USD | 187 | 51.3% | -0.135 | 0.77 | -25.2p |
| london_fix_reversal | GBP_USD | 37 | 56.8% | -0.150 | 0.78 | -5.6p |
| ema200_trend_reversal | USD_JPY | 32 | 56.2% | -0.183 | 0.77 | -5.9p |
| dt_fib_reversal | EUR_JPY | 81 | 54.3% | -0.199 | 0.74 | -16.2p |

## クオンツ判断

### 精鋭候補 TOP 5 (N×EV×PF総合)
1. **session_time_bias × USD_JPY** — N=157, WR=79%, EV=+0.580, PF=2.46, PnL=+91p ★★★★★
2. **trendline_sweep × GBP_USD** — N=134, WR=73%, EV=+0.599, PF=1.68, PnL=+80p ★★★★
3. **gbp_deep_pullback × GBP_USD** — N=77, WR=75%, EV=+1.064, PF=2.00, PnL=+82p ★★★★
4. **session_time_bias × EUR_USD** — N=566, WR=70%, EV=+0.215, PF=1.34, PnL=+122p ★★★★
5. **xs_momentum × USD_JPY** — N=342, WR=69%, EV=+0.270, PF=1.43, PnL=+92p ★★★

### 注意: london_fix_reversal × GBP_USD は BT負EV
- ロードマップv2ではSENTINEL戦略だったが、365日BTでEV=-0.150
- 学術根拠は強い(★★★★★)が、BT実績が伴っていない
- Live Nで再判断が必要
