# FORCE_DEMOTED Strategies

## 15 strategies currently stopped from OANDA execution (demo Shadow continues)

### Instant Death Rate 100% — Permanently Dead
| Strategy | N | WR | Instant Death | Root Cause | Rehab Score |
|----------|---|-----|-------------|-----------|-------------|
| engulfing_bb | 5L | 14.3% | 100% | 1m engulfing = noise (Marshall 2006) | 1/5 |
| ema_ribbon_ride | 8L | 20% | 100% | 1m PO = spread-dominated | 2/5 |
| inducement_ob | 8L | 10% | 100% | SL=2pip fixed → instant SL hit | 2/5 |
| lin_reg_channel | 3L | 0% | 100% | Hindsight bias in channel detection | 2/5 |
| trendline_sweep | 2L | 0% | 100% | TL subjectivity, respect count=1 too weak | 3/5 |

### Instant Death Rate 80%+ — Data Watching
| Strategy | N | WR | Instant Death | Rehab Potential |
|----------|---|-----|-------------|-----------------|
| sr_fib_confluence | 20L | 28.9% | 85% | 2/5 — BT/live 36pp gap, layer3 dependency |
| macdh_reversal | 38L | 34.7% | 84% | 3/5 — **Best rehab candidate** (confirmation candle + Tier1 限定) |
| sr_break_retest | 5L | 28.6% | 60% | 2/5 — N too low to judge |

### Structural Failures
| Strategy | Root Issue |
|----------|-----------|
| bb_squeeze_breakout | BT EV=-0.799 ATR, breakout timing = max spread |
| dual_sr_bounce | WR=0%, N=3 |
| sr_channel_reversal | WR=0%, N=5 |

### Other DEMOTED
| Strategy | Reason |
|----------|--------|
| ema_pullback | WR=34.8%, MFE=7.33p on wins (best!) but 72% instant death on losses. v8.3 fixes deployed |
| ema_cross | WR=32.6%, N=43, edge=-0.24 |

## Independent Audit Decisions
- **macdh → bb_rsi absorption: REJECTED** (contaminates only PF>1 strategy)
- **lin_reg_channel 1H redesign: REJECTED** (85% ruin → no new strategy resources)
- Shadow recording continues for: engulfing_bb (control group), sr_fib_confluence (overfitting study), lin_reg_channel (baseline)
- See [[independent-audit-2026-04-10]]

## Hypothesis Map (7 strategies → 4 hypotheses)
| Hypothesis | Dead Strategies | Already Covered By |
|---|---|---|
| MR at extremes | engulfing_bb, macdh, sr_fib_confluence | [[bb-rsi-reversion]] |
| Trend pullback | ema_ribbon_ride | adx_trend_continuation + [[vol-momentum-scalp]] |
| False breakout | inducement_ob, trendline_sweep | [[orb-trap]] + [[liquidity-sweep]] |
| Regression channel MR | lin_reg_channel | Nothing (unique) — but REJECTED by audit |
