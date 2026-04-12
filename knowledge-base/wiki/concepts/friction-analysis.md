# Friction Analysis

## Per-Pair Friction (RT = Round Trip)
| Pair | Spread | Slippage | RT Friction | BEV_WR | Notes |
|------|--------|----------|-------------|--------|-------|
| USD_JPY | 0.7pip | 0.5pip | **2.14pip** | 34.4% | Most efficient |
| EUR_USD | 0.7pip | 0.5pip | **2.00pip** | 39.7% | |
| GBP_USD | 1.3pip | 1.0pip | **4.53pip** | 37.9% | Limit-only enforced |
| EUR_JPY | 1.0pip | 0.5pip | **2.50pip** | 33.7% | |
| EUR_GBP | 1.5pip | - | **~3.0pip** | 57.1% | **STRUCTURALLY IMPOSSIBLE** (stopped) |
| XAU_USD | 86pip | 46pip | **217.5pip** | ~35% ATR-rel | **STOPPED v8.4** |

## Aggregate Friction
- Pre-v8.4: avg 7.04pip/trade (XAU-distorted)
- Post-v8.4 (FX only): est. 2.5-3.5pip/trade

## Key Insight: XAU Was 102% of Post-Cutoff Loss
```
Post-cutoff 237 trades:
  XAU loss:  -2,280pip
  FX profit: +96.8pip
  Total:     -2,183pip
```
XAU stop alone flips the system from deep loss to marginal profit.

## Friction by Session
| Session | Avg Slippage | Avg Spread | Total |
|---------|-------------|-----------|-------|
| London | 0.31pip | 0.55pip | **0.86pip** (best) |
| Tokyo | 1.04pip | 2.10pip | **3.14pip** |
| New York | 2.48pip | 4.82pip | **7.30pip** (XAU-inflated) |

## Related
- [[bb-rsi-reversion]] (edge=0.45pip vs friction 2.14pip)
- [[xau-stop-rationale]]
- [[independent-audit-2026-04-10]] (摩擦削減が最優先勧告)
