# Full BT Audit: All Pairs x All Strategies (2026-04-12)
**Purpose**: 時間制限による発火率低下の影響を含めた全戦略評価

## USD_JPY DT 55d (274t, WR=60.2%, PF=1.02)
| Strategy | WR | EV(ATR) | Time Avail | Verdict |
|----------|-----|---------|-----------|---------|
| vix_carry_unwind | 100% | +2.222 | Event-driven | ★★★★★ |
| orb_trap | 100% | +1.443 | 5h/day | ★★★★ |
| dual_sr_bounce | 76.0% | +0.703 | 24h | ★★★ |
| sr_break_retest | 80.0% | +0.512 | 24h | ★★★ |
| htf_false_breakout | 60.0% | +0.317 | 24h | ★★★ |
| dt_bb_rsi_mr | 64.2% | +0.156 | 24h(RANGE限定) | ★★ |
| session_time_bias | 66.7% | +0.143 | **5h/day** | ★★ |
| dt_sr_channel_reversal | 60.0% | +0.115 | 24h | ★★ |
| xs_momentum | 58.3% | -0.133 | 24h | ✗ |
| london_fix_reversal | 33.3% | -0.569 | **30min/day** | ✗ |
| gotobi_fix | 0.0% | -2.692 | **1h/月6日** | ✗(N不足) |

## EUR_USD DT 55d (185t, WR=68.6%, PF=1.546, Sharpe=3.231 ★★★)
| Strategy | WR | EV(ATR) | Verdict |
|----------|-----|---------|---------|
| htf_false_breakout | 100% | +2.693 | ★★★★★ |
| trendline_sweep | 90.9% | +1.932 | ★★★★★ |
| post_news_vol | 75.0% | +1.643 | ★★★★ |
| squeeze_release_momentum | 100% | +1.491 | ★★★★ |
| **session_time_bias** | **87.5%** | **+0.993** | **★★★★★** |
| lin_reg_channel | 100% | +0.950 | ★★★★ |
| ema200_trend_reversal | 100% | +0.948 | ★★★★ |
| sr_fib_confluence | 73.3% | +0.407 | ★★★ |
| xs_momentum | 65.3% | +0.192 | ★★ |
| dt_bb_rsi_mr | 47.1% | -0.457 | ✗ |

## GBP_USD DT 55d (260t, WR=67.7%, PF=1.486, Sharpe=2.954 ★★★)
| Strategy | WR | EV(ATR) | Verdict |
|----------|-----|---------|---------|
| gbp_deep_pullback | 100% | +3.203 | ★★★★★ |
| post_news_vol | 100% | +3.145 | ★★★★★ |
| ema_cross | 100% | +1.952 | ★★★★ |
| orb_trap | 100% | +1.765 | ★★★★ |
| squeeze_release_momentum | 100% | +1.445 | ★★★★ |
| dt_fib_reversal | 100% | +1.240 | ★★★★ |
| london_ny_swing | 100% | +1.145 | ★★★★ |
| **london_fix_reversal** | **100%** | **+1.009** | **★★★★** |
| dt_sr_channel_reversal | 71.4% | +0.206 | ★★ |
| session_time_bias | 60.0% | -0.047 | △ |

## USD_JPY Scalp 7d (104t, WR=58.7%, PF=0.756)
| Strategy | WR | EV(ATR) | Verdict |
|----------|-----|---------|---------|
| bb_squeeze_breakout | 100% | +1.681 | ★★★★ |
| v_reversal | 100% | +1.257 | ★★★ |
| engulfing_bb | 83.3% | +0.892 | ★★★ |
| vol_momentum_scalp | 66.7% | +0.387 | ★★ |
| fib_reversal | 72.7% | +0.066 | ★ |
| bb_rsi_reversion | 52.4% | **-0.522** | **✗ BT負EV** |

## EUR_USD Scalp 7d (59t, WR=61.0%, PF=0.889)
| Strategy | WR | EV(ATR) | Verdict |
|----------|-----|---------|---------|
| bb_rsi_reversion | 83.3% | +0.943 | ★★★ |
| vol_surge_detector | 69.2% | +0.242 | ★★ |

## 時間制限の影響まとめ
| 戦略 | 1日の稼働時間 | N蓄積速度 | N=30到達推定 |
|------|-------------|----------|------------|
| session_time_bias | 5h (21%) | 0.3t/日 | **100日** |
| gotobi_fix | 1h×月6日 (0.8%) | 0.2t/日 | **150日** |
| london_fix_reversal | 30min (2.1%) | 0.1t/日 | **300日** |
| orb_trap | 5h (21%) | 0.4t/日 | **75日** |
| liquidity_sweep | 14h (58%) | 0.5t/日 | **60日** |
| xs_momentum | 24h (100%) | 1.7t/日 | **18日** |
| bb_rsi×JPY | 24h (100%) | 2.5t/日 | **12日** |
