# Cell Deepdive Audit — 2026-05-03

**Run date:** 2026-05-03
**Tool:** cell_edge_audit v1 (cell_deepdive_audit.py not yet implemented — using cell_edge_audit.py as proxy)
**Window:** 365d | **Scope:** Live + Shadow | **DB:** demo_trades.db

## Meta

| Metric | Value |
|---|---|
| Trades total | 475 |
| Trades live (is_shadow=0) | 36 |
| Trades shadow (is_shadow=1) | 439 |
| Trades in 365d window (non-XAU) | 426 |
| Qualified cells (N≥20) | 3 |
| m_global | 3 |
| Date range | 2026-04-02 → 2026-05-02 |

## PAIR_PROMOTED Candidates

**Count: 1**

| entry_type | session | spread_q | mode | N (L/S) | WR | Wilson [lo, hi] | EV pip | PF | p_bonf | Kelly | WF |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fib_reversal | Tokyo | q0 | Scalp | 25 (0/25) | 84.0% | [65.3%, 93.6%] | +10.24 | 12.18 | 0.0020 | ~42.5%* | n/a |

*Kelly computed from overall fib_reversal shadow (N=49): WR=63.3%, RR=1.77, Kelly=42.5%, PF=3.04. Cell-specific Kelly not extractable without direction split.*

### Recommendation for fib_reversal / Tokyo / q0 / Scalp

- **Action: Pre-reg LOCK** — lock parameters as-is before any further tuning
- **Promote via Rule 1 (Slow & Strict)**: start at 0.25 lot, evaluate 30 live trades before full sizing
- All 25 trades are shadow-only (live_n=0); p_bonf=0.0020 clears Bonferroni at α=0.05
- Wilson lower 65.3% >> 50% threshold — robust even accounting for multiple testing
- Note: USD_JPY dominates fib_reversal (N=33 shadow, +333.5p); EUR_USD leg is flat (N=15, -7.1p)

## Negative-Edge Cells (Demote Candidates)

| entry_type | session | spread_q | mode | N | WR | Wilson lower | PF | p_bonf | Action |
|---|---|---|---|---|---|---|---|---|---|
| ema_trend_scalp | London | q0 | Scalp | 33 | 24.2% | 12.8% | 0.60 | 0.0092 | DEMOTE candidate |
| ema_trend_scalp | Overlap | q0 | Scalp | 29 | 17.2% | 7.6% | 0.33 | 0.0013 | DEMOTE candidate |

## 7 Target Strategies Status

| Strategy | Trades (365d) | Status |
|---|---|---|
| sr_anti_hunt_bounce | 0 | No signals fired — signal path issue unresolved |
| sr_liquidity_grab | 0 | No signals fired — signal path issue unresolved |
| cpd_divergence | 0 | No signals fired — signal path issue unresolved |
| vdr_jpy | 0 | No signals fired — signal path issue unresolved |
| vsg_jpy_reversal | 0 | No signals fired — signal path issue unresolved |
| rsk_gbpjpy_reversion | 0 | No signals fired — signal path issue unresolved |
| mqe_gbpusd_fix | 0 | No signals fired — signal path issue unresolved |

**All 7 target strategies remain at 0 trades.** Shadow accumulation cannot begin until the signal fire path issue is resolved. This was known as of 2026-04-28 and is still pending investigation.

## Top Strategies by N (365d, shadow)

| Strategy | N | WR% | Total pips | Status |
|---|---|---|---|---|
| ema_trend_scalp | 88 | 20.5% | -107.3 | Negative edge confirmed (see above) |
| fib_reversal | 49 | 63.3% | +336.8 | **PAIR_PROMOTED candidate** |
| sr_fib_confluence | 34 | 23.5% | -500.9 | Below N≥20 threshold per cell |
| sr_channel_reversal | 28 | 3.6% | -99.2 | Negative edge |
| engulfing_bb | 23 | 26.1% | +17.5 | N borderline, no qualified cell |
| bb_rsi_reversion | 22 (live) | 63.6% | +192.3 | Separate live audit needed |

## Next Actions

1. **fib_reversal/Tokyo/q0/Scalp**: Issue Pre-reg LOCK, start Rule 1 (Slow & Strict) promotion to live at 0.25 lot
2. **ema_trend_scalp London+Overlap**: Flag for demotion review
3. **7 target strategies**: Escalate signal-path investigation; no shadow data can accumulate until signals fire
4. **bb_rsi_reversion live**: 22 live trades at 63.6% WR — run separate live-only cell audit
5. **cell_deepdive_audit.py**: Implement proper tool with `--strategies`, `--regime-source`, `--window` args for future scheduled runs
