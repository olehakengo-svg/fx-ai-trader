# bb_rsi_reversion

## Status: Tier 1 (PAIR_PROMOTED x USD_JPY)
**The only strategy with PF > 1 in 556t production audit.**

## Performance History
| Period | N | WR | PnL | PF | Notes |
|--------|---|-----|-----|-----|-------|
| Pre-cutoff (all) | 212 | 44.3% | -274.2 | <1 | All pairs mixed |
| Pre-cutoff (USD_JPY) | 123 | 54.7% | +54.8 | 1.13 | **Only PF>1** |
| Post-cutoff (shadow-excluded) | 77 | 36.4% | -42.2 | - | v8.4 shadow filter applied |
| BT (v3.2, 7d) | 181 | 61.3% | - | - | EV=+0.173 ATR |

## v8.3 Changes (2026-04-10)
- Added confirmation candle: `ctx.entry > ctx.open_price` (BUY) / `< open` (SELL)
- Counter-trend filter: TREND_BULL blocks SELL, TREND_BEAR blocks BUY
- ADX floor: JPY ADX < 15 -> return None
- **Expected**: instant death 77.6% -> 20-25%, WR -> 58-62%
- **Status**: OOS verification pending (data accumulating)

## MAFE Profile
- WIN: avg MAE=1.1pip, avg MFE=3.7pip (entry precision ratio=3.36)
- LOSS: avg MAE=3.2pip (=SL), avg MFE=0.3pip (instant death)
- 77.6% of losses have MFE=0 (never favorable)

## Friction
- USD_JPY: spread 0.7 + slip 0.5 = 2.14pip RT
- BEV_WR = 34.4%
- Edge = 0.45pip/trade (extremely thin)

## Key Risk
- Post-cutoff WR=36.4% is only 2pp above BEV_WR=34.4%
- Independent audit warning: "edge could vanish with slight spread increase"
- v8.3 confirmation candle effect is UNVERIFIED

## Related
- [[friction-analysis]]
- [[mfe-zero-analysis]]
- [[independent-audit-2026-04-10]]
