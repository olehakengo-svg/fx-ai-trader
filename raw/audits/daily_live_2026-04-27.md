# Daily Live Monitor — 2026-04-27

DB: demo_trades.db (closed trades total = 367, Live = 34)
Severity: **WARNING**

## C1-PROMOTE Live状況

| Cell | Live N | WR | Wilson lo | EV pip | tail LOSS | Shadow N (ref) |
|---|---|---|---|---|---|---|
| fib_reversal × Tokyo × q0 × Scalp | 0 | 0.0% | 0.0% | +0.00 | 0 | 24 |

## WATCH cells (PROMOTE 候補・Live N 蓄積待ち)

| Cell | Live N | WR | Wilson lo | EV pip |
|---|---|---|---|---|
| bb_rsi_reversion × Tokyo × q0 × Scalp | 9 | 77.8% | 45.3% | +4.61 |
| bb_rsi_reversion × London × q0 × Scalp | 11 | 54.5% | 28.0% | +1.46 |

## ELITE_LIVE 3戦略 (M1 修正効果監視)
M1 deploy: **2026-04-27T05:51:00 UTC** (commit 641bfe4)
Post-M1 total trades: 8

### 全期間 (BT-Live divergence baseline)

| Cell | Live N | WR | EV pip | Shadow N |
|---|---|---|---|---|
| session_time_bias (any pair) | 1 | 0.0% | -6.50 | 2 |
| trendline_sweep (any pair) | 0 | 0.0% | +0.00 | 0 |
| gbp_deep_pullback (any pair) | 0 | 0.0% | +0.00 | 0 |

### Post-M1 (修正後 only)

| Cell | Live N | WR | EV pip | Shadow N |
|---|---|---|---|---|
| session_time_bias (any pair) | 0 | 0.0% | +0.00 | 0 |
| trendline_sweep (any pair) | 0 | 0.0% | +0.00 | 0 |
| gbp_deep_pullback (any pair) | 0 | 0.0% | +0.00 | 0 |

## Alerts

- NET_EDGE bb_squeeze_breakout: -17.1pt (-1.64pip) N=15
- NET_EDGE dt_fib_reversal: -20.8pt (+1.09pip) N=6
- NET_EDGE orb_trap: -16.7pt (-8.18pip) N=5
- NET_EDGE post_news_vol: -50.0pt (-14.65pip) N=6
- NET_EDGE sr_channel_reversal: -15.3pt (-1.08pip) N=24

## Wave 2 gate firing rate (post-deploy 2026-04-27+, N=35)

| Gate | fired | rate | anomaly |
|---|---|---|---|
| A2 SL clamp | 0 | 0.0% | - |
| A3 cost throttle | 0 | 0.0% | - |
| A4 vol_scale | 0 | 0.0% | - |

_post-deploy N=35 < 50 のため、anomaly 判定はサンプル蓄積待ち_
