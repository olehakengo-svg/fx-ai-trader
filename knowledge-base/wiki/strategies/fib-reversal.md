# fib_reversal

## Status: Tier 2 (FORCE_DEMOTED → Recovery Path Active)
**Dramatic improvement post-cutoff: WR 25.6% → 55.0% (v6.3 parameter effect confirmed)**

## Performance
| Period | N | WR | PnL | Notes |
|--------|---|-----|-----|-------|
| Pre-cutoff (all) | 117 | 25.6% | -18.0 | Contaminated by SLTP bug |
| **Post-cutoff** | **20** | **55.0%** | **+35.6** | v6.3 params working |
| Post-cutoff (shadow-excl, latest) | 32 | 40.6% | +21.9 | More data, still positive |
| BT (Scalp v3.2) | 172 | 57.0% | - | EV=+0.056 ATR |

## Recovery Path
```
Current: FORCE_DEMOTED (N=32, WR=40.6%)
  N>=30 & WR>=50% → SENTINEL (0.01 lot)       ← approaching
  N>=50 & WR>=52% & PF>1.1 → PAIR_PROMOTED    ← target
```

## v6.3 Changes That Caused Improvement
| Parameter | Before | After | Effect |
|-----------|--------|-------|--------|
| proximity | 0.50 ATR | **0.35 ATR** | Entry at actual Fib level, not "near" |
| SL | 0.5 ATR | **0.7 ATR** | Survives initial shakeout |
| TP | 1.8 all | **JPY=1.8, EUR/GBP=1.3** | Friction-aware |
| body_ratio | none | **>=0.50 (v6.3), >=0.60 (v8.3)** | Confirmation candle |

## v8.3 Changes (instant death reduction)
- Fib hierarchy: 38.2% score>=4.5, 50% >=3.5, 61.8% >=3.0
- MACD-H required for non-Tier1 extreme entries
- body_ratio 0.50 → 0.60
- Expected: instant death 75.9% → 25-35%

## Statistical Significance (Independent Audit)
- WR=25.6% → 55.0%: z=3.013, **p<0.002 (significant)**
- Wilson 95% CI: [34.2%, 74.2%] (wide — N=20)
- Conclusion: "Improvement is statistically significant but true WR could be 35-55%"

## MAFE
- WIN avg MFE: 3.57pip
- LOSS 75.9% instant death (MFE=0)
- v8.3 targets 25-35% instant death

## Related
- [[mfe-zero-analysis]] — 75.9% instant death analysis
- [[bb-rsi-reversion]] — Similar MR strategy (77.6% instant death)
- [[independent-audit-2026-04-10]] — Statistical validation
