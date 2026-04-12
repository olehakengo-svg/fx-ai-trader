# liquidity_sweep

## Status: Tier 2 (Sentinel, N=0, just deployed v8.2)
**New uncorrelated alpha source — institutional stop-hunt reversal.**

## Design (v8.2, 740 lines)
- **Academic basis**: Osler 2003, Kyle 1985, Bulkowski 2005
- **Core**: Williams Fractal swing H/L → wick rejection (>=60%) → next-bar entry
- **Regime**: ADX < 25 only (RANGE — trending markets produce real breakouts)
- **TF**: 15m DT (friction/SL = 11-18%)

## Entry Logic
1. Swing level detection (fractal N=5, lookback 60 bars, touches >= 2)
2. Sweep: price penetrates level via WICK (wick_ratio >= 0.60)
3. Volume proxy: bar_range / ATR >= 1.5
4. Close reclaims inside range
5. Next bar confirmation entry (not sweep bar)
6. Session filter: London/NY open 30min excluded

## Differentiation from Existing
| | Turtle Soup | ORB Trap | **Liquidity Sweep** |
|---|---|---|---|
| Detection | Close reclaim | Fixed OR fakeout | **Wick ratio >= 60%** |
| Regime | ADX 12-40 | Session-based | **ADX < 25 RANGE only** |
| Entry | Current bar | Current bar | **Next bar confirmation** |
| Correlation | - | r=+0.85 w/ ema_trend | **Low expected** |

## Friction Viability
- USD_JPY 15m: ATR ~12p, SL ~17.5p, friction 2.14p → friction/SL = 12.2%
- BEV_WR ≈ 35%, Expected WR: 60-70% (Bulkowski)
- Margin: +25-35pp ← high viability

## Risk
- N=0: completely unproven in live
- BT not yet run (needs 55d+ period, N>=30)
- Independent audit: "adding strategies to 85% ruin system requires caution"

## Related
- [[microstructure-stop-hunting]] — Research theme
- [[osler-2003]] — Primary academic reference
- [[orb-trap]] — Related but structurally different
- [[edge-pipeline]] — Stage 4: SENTINEL
