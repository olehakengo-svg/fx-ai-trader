# Month-End WMR Fix Drift/Reversion — pre-reg LOCK (2026-06-18)

> ## ⛔ VERDICT: NULL — REJECT both legs (2026-06-18, post-BT)
> Neither leg survives the locked gate stack. **Do NOT promote — not even shadow** (promotion policy: shadow only IF survives). Closed; no post-hoc rescue.
> | Leg | N | WR | Wilson_lo | net pip | gross pip | bootstrap p | WF | both-legs net+ | BH-FDR(m=2) |
> |---|---|---|---|---|---|---|---|---|---|
> | **H1 drift** | 144 | 53.5% | 0.453 | **−566.8** | −278.8 | 0.867 | 1/4 | ✗ (L −421 / S −146) | ✗ |
> | **H2 reversion** | 142 | 61.3% | 0.531 | +141.7 | +425.7 | 0.378 | 3/4 | ✗ (L −316 / S +458) | ✗ |
>
> - **H1**: net-negative even GROSS, p=0.87, WF 1/4, both signed legs negative. The hedge-rebalancing *drift* as specified does not exist (or is reversed) in EUR_USD 2014-2026.
> - **H2**: the only leg with a pulse (WF 3/4, mean +1.0 pip) but **fails gate 4** (bootstrap p=0.378 ≫ BH-FDR threshold 0.05) and **fails gate 5** — its entire PnL is a one-sided SHORT-EUR artifact (LONG leg −316 pip). Exactly the directional-bias trap the both-legs gate exists to catch. Not a symmetric, tradable edge.
> - **R3 bug fix mid-BT (documented for integrity):** first run silently dropped 44% of month-ends because FX H1 data stamps the Sunday-evening session-open (22:00-23:00 UTC) on a Sunday date, leaking Sundays into the "business day" set (no 16:00 fix bar → drop). Fixed to weekdays-only (`monthend_fix_bt.py` business-day filter). **The fix made the result MORE null** (H2 bootstrap p 0.19→0.38; both-legs flipped true→false) — i.e. the drop was spuriously *inflating* H2. This is a faithful-implementation bug fix of the locked spec ("business day"), not a hypothesis change.
> - **Independent adversarial review (default-to-reject): PASSED** — byte-identical reproduction, no look-ahead (signal & ATR strictly causal), DST/bar-close convention correct, side-sanity gate fired 0×, code faithful to locked spec. The NULL is real, not an artifact.
> - Result JSON: `raw/bt-results/monthend_fix_2026_06_18.json`. BT: `tools/monthend_fix_bt.py`.

**Status: LOCKED — committed BEFORE any backtest.** Post-hoc parameter tuning voids this pre-reg.
**Rule**: R1 (new strategy / new edge). **Campaign**: m=2 hypotheses, BH-FDR q=0.10.
**Source agent**: CMA research agent proposal 2026-06-18 ([[project_cma_fxai_autoimprove_2026_06_16]]).
**Implementation (planned)**: `tools/monthend_fix_bt.py` (Claude primary impl) | **Data fetch**: `tools/monthend_fix_fetch.py`

## Mechanism (academic basis)
Melvin & Prins (2015), *"Equity market shocks and the predictability of currency returns"* — passive
benchmark-tracking funds (and FX overlay hedges) mechanically rebalance currency exposure into the
**16:00 London WMR fix** on the **last business day of the month**. When an equity market has
outperformed over the month, hedgers must buy/sell the foreign currency to restore hedge ratios,
creating a **predictable order-flow drift into the fix** with a **partial reversal the next day**.

This is a **narrow mechanical-flow edge** — the archetype identified as the winning shape in
[[strategy-rethink-2026-06-08]] (flow/microstructure, NOT factor/risk premia, which went NULL in
[[d1-tsmom-basket-pre-reg-2026-06-08]]).

### DISTINCT from existing `london_fix_reversal`
`london_fix_reversal` is a **daily W-shape intraday scalp**, TP 8-12 pip, **friction-dead** (365d BT
EV=−0.150). This edge is a **monthly, cross-asset-conditioned, ~24-48h hold** with TP≈40-55 pip
(0.5-0.6×ATR(20,D1)). Different signal, different horizon, different friction regime. Not a re-propose.

## Hypotheses (FROZEN)

### H1 — `monthend_fix_drift` (the drift INTO the fix)
- **Instrument / TF**: EUR_USD, H1 bars.
- **Signal**: `rel = monthly_return(EURO_STOXX_50) − monthly_return(S&P500)` over the calendar month up to entry.
  - `rel > 0` → **SHORT** EUR_USD ; `rel < 0` → **LONG** EUR_USD.
  - Rationale: EU equity outperformance ⇒ foreign (US) hedgers of EU equity buy USD / sell EUR into the fix.
- **θ = 0** (sign-only). Magnitude `|rel|` is a SIZE lever — **report-only**, not a gate.
- **Entry**: H1 close nearest 16:00 **London** (DST-aware: 15:00 UTC summer / 16:00 UTC winter) on the
  **2nd-to-last business day** of the month.
- **Exit**: hard time-exit at 16:00 London on the **last business day** of the month (~24h).
- **TP** = +0.6×ATR(20, D1) ; **SL** = −0.8×ATR(20, D1). ATR computed on D1 bars as of entry day.
- **Fill model**: intrabar **SL-first** (conservative); **TP/SL side-sanity gate** (TP on profit side, SL on loss side relative to direction).

### H2 — `monthend_fix_reversion` (the reversal AFTER the fix)
- **Instrument / TF**: EUR_USD, H1 bars.
- **Signal**: **opposite direction** to H1 (`rel > 0` → LONG EUR_USD ; `rel < 0` → SHORT) — fades the fix drift.
- **Entry**: H1 close nearest 16:00 London on the **last business day** of the month.
- **Exit**: hard time-exit at 16:00 London on the **first business day of the next month** (~24-48h).
- **TP** = +0.5×ATR(20, D1) ; **SL** = −0.7×ATR(20, D1). Intrabar SL-first, side-sanity gate.

## Data (Phase 0 — fetched & audited 2026-06-18, BEFORE this lock)
| Series | Source | Window | Rows | Quality |
|---|---|---|---|---|
| EUR_USD H1 (traded) | MASSIVE (Polygon-compat) | 2014-05-29 → 2026-06-18 | 74,957 | 99.28% complete, 789 intra-week gaps (~1%) |
| EUR_USD D1 (ATR20) | MASSIVE | 2014-05-29 → 2026-06-18 | 3,805 | 100% complete |
| ^GSPC (S&P 500, signal) | yfinance | 2014-05-29 → 2026-06-17 | 3,032 | 146 distinct months, 0 NA |
| ^STOXX50E (EURO STOXX 50, signal) | yfinance | 2014-05-30 → 2026-06-18 | 3,024 | 146 distinct months, 0 NA |

- **N ≈ 144 month-ends / 12.05y** (146 months − ~1 ATR(20,D1) warmup − partial first/last). **Low-N caveat applies** (each fold ≈ 36).
- Indices used **only** to build the monthly-return signal (not traded) ⇒ external public source acceptable. Traded leg uses in-system MASSIVE provider (same as [[d1-tsmom-basket-pre-reg-2026-06-08]]).
- Audit: `data/cache/research/monthend_fix/phase0_audit.json`.

## Family prior (NOT naive — campaign m=2 is the formal correction, but the program prior is wider)
This is **at least the ~7th** fix/session/time-of-day timing attempt in this system. Prior attempts mostly
failed or were friction-dead:
`london_fix_reversal` (BT EV=−0.150, friction-dead) · `session_time_bias` · `asia_range` · `ny_close` ·
`session_pair` · `gbp_asia_flash_crash` · `vix_carry_unwind`.
⇒ A single marginally-surviving p-value here should be read against this backdrop. BH-FDR m=2 corrects
the two legs of THIS campaign; the broader timing-family base rate is **low**, so we require the FULL gate
stack (below), not just BH-FDR survival.

## Decision gates (ALL must pass for SURVIVE)
1. **Win-rate floor**: Wilson_lo(WR, 95%) ≥ **0.40** (state low-N caveat at N≈144 / fold≈36).
2. **Friction**: RT ≤ **10% of TP**. EUR_USD RT ≈ 1.5-2 pip vs TP ≈ 40-55 pip ≈ 4-5% ✓ (pre-filter pass).
3. **Walk-forward**: ≥ **3/4** time-folds net-positive.
4. **Bootstrap**: stationary/IID bootstrap p (10k resamples, **seed=42**) survives **BH-FDR(m=2, q=0.10)**.
5. **Both signed legs net-positive**: LONG-only and SHORT-only sub-samples each net-positive (no single-side artifact).
6. **Regime concentration**: per-year PnL report — **no single-year dependence** (drop-one-year robustness).

A leg that fails any gate → that leg REJECT. Both legs may pass/fail independently under BH-FDR.

## Promotion policy
- If SURVIVE → **shadow-first**, never auto-LIVE. LIVE promotion is **user-decreed only**.
- If NULL → close & document (no post-hoc rescue in this pre-reg; structural re-angles become a NEW pre-reg).

## Constraints honored
XAU excluded · Render = data primary for any LIVE stats · NOT a positioning/COT contrarian (kill-list respected) ·
not a re-propose of `london_fix_reversal`.

## Related
- [[strategy-rethink-2026-06-08]] (mechanical-flow = winning shape)
- [[d1-tsmom-basket-pre-reg-2026-06-08]] (risk-premia NULL — the foil)
- [[roadmap-v2.2-win-conversion]] (月利21.6% 目標への寄与: 新規 +EV mechanical edge 候補)
