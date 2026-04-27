# Daily Live Monitor — 2026-04-27

DB: demo_trades.db (closed trades total = 359, Live = 34)
Severity: **OK**

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
Post-M1 total trades: 0

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

_No alerts._

## Wave 2 gate firing rate (post-deploy 2026-04-27+, N=27)

| Gate | fired | rate | anomaly |
|---|---|---|---|
| A2 SL clamp | 0 | 0.0% | - |
| A3 cost throttle | 0 | 0.0% | - |
| A4 vol_scale | 0 | 0.0% | - |

_post-deploy N=27 < 50 のため、anomaly 判定はサンプル蓄積待ち_
