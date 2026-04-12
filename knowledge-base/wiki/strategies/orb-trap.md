# orb_trap

## Status: Tier 1 (PAIR_PROMOTED x USD_JPY, EUR_USD, GBP_USD)
**Highest BT margin over BEV_WR (+50pp). Zero live data divergence confirmed yet.**

## Performance
| Source | Pair | N | WR | EV |
|--------|------|---|-----|-----|
| BT (55d) | USD_JPY | 29 | 79.3% | +0.617 ATR |
| BT (55d) | EUR_USD | 42 | 71.4% | +0.482 ATR |
| BT (55d) | GBP_USD | 28 | 64.3% | +0.245 ATR |
| Live (post-cutoff) | Mixed | 2 | 50% | +7.6pip |

## Design
- Opening Range Breakout Fakeout Reversal
- Session windows: LDN 07:30-10:00, NY 14:00-16:00 (4.5h/day)
- 8-step cascading filter (ORB range quality, trap detection, HTF filter, RR validation)
- Correlation: ema_trend_scalp r=+0.851, inducement_ob r=+0.875

## N=2 Investigation (2026-04-10)
- No code blocker found
- Low N is BY DESIGN: 4.5h/day opportunity window x strict filters
- Expected: N>=10 in 10-15 trading days
- N_LOT_TIERS: N<10 -> max 1.0x, N>=10 -> 1.5x

## BT/Live Divergence Risk
- bb_rsi: BT 61.3% -> Live 46.2% (-15pp)
- If same degradation: orb_trap 79% -> ~64% (still well above BEV)
- Independent audit: "BT-only Tier 1 is unacceptable" -> valid concern

## Related
- [[bt-live-divergence]]
- [[independent-audit-2026-04-10]]
