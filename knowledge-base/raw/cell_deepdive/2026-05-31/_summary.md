# Cell Deepdive Audit — 2026-05-31

**Run date:** 2026-05-31
**Tool:** cell_edge_audit v2/v3 (cell_deepdive_audit.py not yet implemented — using cell_edge_audit.py as proxy)
**Window:** 365d | **Scope:** Live + Shadow | **DB:** demo_trades.db

## Meta

| Metric | Value |
|---|---|
| Trades total (DB) | 475 |
| Trades live (is_shadow=0) | 11 |
| Trades shadow (is_shadow=1) | 464 |
| Trades in 365d window (non-XAU) | 426 |
| **Last DB entry** | **2026-04-30** (no new trades since) |
| Qualified cells v2 (N≥10) | 7 |
| Qualified cells v3 (N≥10, direction-split) | 1 |
| m_global (v2) | 7 |
| Date range | 2026-04-02 → 2026-04-30 |

## ⚠️ System State — DEFENSIVE MODE

**Critical finding:** `demo_trades` table has received **zero new entries since 2026-04-30** despite
`evaluated_candidates` showing active signals through 2026-05-28 (sr_anti_hunt_bounce: 18,633 candidates).

| Key | Value |
|---|---|
| defensive_mode | **1 (ACTIVE)** |
| eq_peak | 11.4 |
| eq_current | **-48.9** |
| dd_lot_mult | 0.4 |
| Implied drawdown | ~530% from peak |

Signals are being evaluated and scored but NOT being persisted as demo_trades entries.
This is a systemic blocker — the 7 target strategies cannot accumulate shadow data until this is resolved.

## PAIR_PROMOTED Candidates

**Count: 1** (same candidate as 2026-05-03 — no new trades to change this)

### v2 Result (entry_type × session × pair × mode)

| entry_type | session | pair | mode | N (L/S) | WR | Wilson [lo, hi] | EV pip | PF | p_bonf |
|---|---|---|---|---|---|---|---|---|---|
| fib_reversal | Tokyo | USD_JPY | Scalp | 25 (0/25) | 84.0% | [65.3%, 93.6%] | +10.24 | 12.18 | 0.0047 |

### v3 Result (+ direction dimension)

| entry_type | session | pair | direction | mode | N (L/S) | WR | Wilson [lo, hi] | EV pip | PF | p_bonf |
|---|---|---|---|---|---|---|---|---|---|---|
| fib_reversal | Tokyo | USD_JPY | SELL | Scalp | 20 (0/20) | 90.0% | [69.9%, 97.2%] | +12.56 | 20.94 | 0.0003 |

**Note:** The SELL direction drives the edge (WR 90% vs combined 84%). The BUY side is weaker (N=5, WR=60%).

### Recommendation for fib_reversal / Tokyo / USD_JPY / SELL

- **Action: Pre-reg LOCK** — parameters must be locked before any further tuning
- **Promote via Rule 1 (Slow & Strict)**: start at 0.25 lot, evaluate 30 live trades before full sizing
- All 25 (SELL:20 + BUY:5) are shadow-only (live_n=0)
- p_bonf=0.0003 clears Bonferroni at α=0.05 with a 10× margin
- Wilson lower 69.9% >> 50% threshold for SELL-only direction

## 7 Target Strategies Status

| Strategy | Trades (365d) | evaluated_candidates | Last signal | Status |
|---|---|---|---|---|
| sr_anti_hunt_bounce | **0** | 18,633 | 2026-05-28 | Signals fire, NOT persisted to demo_trades |
| sr_liquidity_grab | **0** | 276 | 2026-05-11 | Signals fire, NOT persisted |
| cpd_divergence | **0** | 0 | None | No signals generated |
| vdr_jpy | **0** | 0 | None | No signals generated |
| vsg_jpy_reversal | **0** | 2,061 | 2026-05-04 | Signals fire, NOT persisted |
| rsk_gbpjpy_reversion | **0** | 644 | 2026-04-30 | Signals fire, NOT persisted |
| mqe_gbpusd_fix | **0** | 346 | 2026-04-30 | Signals fire, NOT persisted |

**Root cause hypothesis:** `defensive_mode=1` or the trade execution bridge is suppressing all new `demo_trades` inserts.
The `strategy_n_cache` in system_kv does not include any of the 7 target strategies, confirming they are not in the
active execution pool.

## Negative-Edge Cells (unchanged from 2026-05-03)

| entry_type | session | pair | mode | N | WR | Wilson lower | PF | p_bonf | Action |
|---|---|---|---|---|---|---|---|---|---|
| ema_trend_scalp | London | GBP_USD | Scalp | 16 | 25.0% | 10.2% | 0.66 | 0.3185 | Monitor |
| ema_trend_scalp | London | EUR_USD | Scalp | 12 | 25.0% | 8.9% | 0.62 | 0.5828 | Monitor |
| ema_trend_scalp | Overlap | EUR_USD | Scalp | 15 | 20.0% | 7.0% | 0.42 | 0.1410 | Monitor |

## Week-over-Week Change (vs 2026-05-03)

| Metric | 2026-05-03 | 2026-05-31 | Delta |
|---|---|---|---|
| Total trades | 475 | 475 | **0** (no new trades in 4 weeks) |
| Shadow trades | 439→464 | 464 | (same — no new shadow since Apr 30) |
| 7 strategies N | 0 | 0 | **no change** |
| PAIR_PROMOTED candidates | 1 | 1 | same (fib_reversal unchanged) |
| m_global | 3 | 7 | increased (min_n=10 vs 20) |

## Next Actions

1. **BLOCKER — Demo trade bridge investigation**: `demo_trades` frozen since 2026-04-30 with equity at -48.9.
   Check app.py / Render logs for why signals from `evaluated_candidates` are not being converted to `demo_trades`.
   Possible causes: (a) `defensive_mode` gate blocking all new trades; (b) Render worker crashed/restarted;
   (c) Trade execution pipeline disabled after drawdown event.

2. **fib_reversal/Tokyo/USD_JPY/SELL**: Pre-reg LOCK should already be in place (flagged 2026-05-03).
   Consider starting Rule 1 promotion since p_bonf=0.0003 and N=20 SELL-direction shadow.

3. **7 target strategies**: Cannot progress until blocker #1 is resolved.
   Strategy signals ARE generating (sr_anti_hunt_bounce: 18,633 candidates), confirming strategy logic works.

4. **cpd_divergence, vdr_jpy**: Zero candidates in evaluated_candidates — strategy is not even evaluating.
   Separate investigation needed to determine if these strategies are enabled in the pipeline.
