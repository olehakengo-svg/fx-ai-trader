# Independent Audit Results (2026-04-10)

## Auditors
1. Risk Committee Quantitative Analyst
2. Independent Strategy Architect

## Binding Recommendations (MUST follow)

### Overturned Proposals
| Proposal | Verdict | Reason |
|----------|---------|--------|
| P1: macdh -> bb_rsi +0.5 score absorption | **REJECTED** | Contaminates only PF>1 strategy. Edge=0.45pip could vanish. Learning engine could auto-demote bb_rsi |
| P2: lin_reg_channel 1H redesign | **REJECTED** | 85% ruin probability -> resource allocation to new strategies is irrational. Focus on bb_rsi protection |

### Approved Actions
| Action | Verdict |
|--------|---------|
| XAU full stop | **APPROVED** (implemented v8.4) |
| Shadow filter on get_stats() | **APPROVED** (implemented v8.4) |
| vol_momentum 2.0x -> 1.0x | **APPROVED** (implemented v8.2) |
| FORCE_DEMOTED 7 strategies maintained | **APPROVED** |
| orb_trap PAIR_PROMOTED (N>=10 threshold too low, recommend N>=30) | **CONDITIONAL** |

### Top Priority
> "The single most important action is protecting the only positive-edge strategy (bb_rsi x USD_JPY). No experiments that risk this edge are justified."

### Statistical Findings
| Metric | Value | Significance |
|--------|-------|-------------|
| vol_momentum Kelly CI (N=11) | [-9.9%, +81.1%] | Kelly discussion meaningless at N=11 |
| bb_rsi post-cut vs BEV_WR | z=1.794, p=0.036 | Barely significant above break-even |
| bb_rsi vs random (50%) | z=0.209, p=0.417 | NOT significant above random |
| fib_reversal improvement | z=3.013, p<0.002 | Statistically significant improvement |
| CVaR/VaR ratio | 8.9x (normal=1.6x) | Extreme fat tail risk |

## Strategy Architect Findings

### Hypothesis Framework
- "Same hypothesis = redundant" is partially valid but NOT a substitute for measured return correlation
- sr_fib_confluence kill reason should be "BT/live 36pp divergence", NOT "Fibonacci has no academic backing"
- MACD-H absorption carries highest execution risk of all proposals (P1)

### Shadow Recording
- Continue for: engulfing_bb (control group), sr_fib_confluence (overfitting study), lin_reg_channel (baseline)
- May stop for: inducement_ob, trendline_sweep (replaced by orb_trap/liquidity_sweep)
- However: FORCE_DEMOTED shadow has zero harm -> maintain all

## Related
- [[bb-rsi-reversion]]
- [[friction-analysis]]
- [[mfe-zero-analysis]]
