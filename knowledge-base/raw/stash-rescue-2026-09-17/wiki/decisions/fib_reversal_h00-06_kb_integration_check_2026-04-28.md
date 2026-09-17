# KB Integration Check: fib_reversal × USD_JPY × Tokyo (UTC 00–06)

- **Date**: 2026-04-28 (JST 17:00)
- **Trigger**: Shadow audit finding —
  - Aggregate cell (Tokyo prime, both directions): N=24, WR=87.5%, Wilson [69.0%, 95.7%], EV +11.03p, WF 4/4 stable
  - 3D STRICT cell (fib_reversal/Tokyo/USD_JPY/SELL/Scalp): N=20, WR=90%, Wilson [69.9%, 97.2%], 4/4 WF folds positive
- **Scope**: Read-only KB integrity audit. No KB updates performed.

---

## 1. Where fib_reversal currently sits

| KB file | Current state |
|---|---|
| `wiki/index.md` L67 | `fib-reversal — no BT data — FORCE_DEMOTED` |
| `wiki/tier-master.md` §B-1, line 55 | `8 fib_reversal — — —` (FORCE_DEMOTED, all pairs Shadow) |
| `wiki/strategies/fib-reversal.md` | Status: `FORCE_DEMOTED (Recovery Path Active — 全ペア強制 Shadow)`. Recovery path documented: `N≥30 & WR≥50% → SENTINEL 0.01 lot`. 2026-04-20 Priority 2 audit recorded a 60d→180d EV sign flip on EUR_USD Scalp 1m. |
| `wiki/decisions/pre-reg-cell-promotion-2026-04-27.md` | C1 cell `fib_reversal × Tokyo × q0 × Scalp` flagged as **C1-PROMOTE** at **0.01 lot SENTINEL** (Recovery Path-aligned). N=24, WR=87.5%, Wilson_BF=0.690, EV +10.82p, Bonferroni p=0.0007, single-cell Kelly_q=0.204. Caveat: 180d aggregate cache showed EV=−0.308. |
| `wiki/decisions/aggressive-edge-deployment-2026-04-28.md` (today) | A4 = sub-conditional Bonferroni → `Tokyo × SELL` only survivor at K=8 (Wilson_BF 0.706, EV_net +13.16p). Sentinel 0.01 lot Phase-1 recommendation. Caveats: N_live=0, WR=100% "too good", shadow spread ≈ 0. |

So the strategy is already on the radar at two recent decision pages; the **new** finding is functionally a re-confirmation with one extra week of shadow data and tighter Wilson bounds, not a brand-new edge.

## 2. KB on USD_JPY × Tokyo edges historically

- `wiki/analyses/friction-analysis.md` L26-31: London = lowest friction (0.86p), Tokyo = 3.14p (XAU-distorted; FX-only ≈ 2.5p). USD_JPY Tier-1 friction = 2.14p RT.
- claude-mem timeline (2026-04-26): `friction_model_v2 multiplier が Tokyo/NY セッションで実測の約半分に過小評価` — Tokyo friction is plausibly *higher* than the table shows.
- `wiki/decisions/vwap-mr-jpy-reconfirmation-2026-04-22.md` and `pre-reg-asia-range-fade-v1-2026-04-26.md`: prior Tokyo-window USD_JPY edges have been pre-registered before; track record is mixed.
- No prior KB page asserts "London should always beat Tokyo for fib_reversal". The friction-analysis "London best" line is about **slippage cost**, not about **edge gross**, so the new Tokyo dominance is **not** a contradiction.

## 3. KB on fib_reversal's prior performance

- Pre-cutoff: N=117, WR 25.6% (SLTP-bug contaminated).
- Post-cutoff v6.3: N=20 WR 55%, then N=32 WR 40.6% (latest shadow-excl).
- BT Scalp v3.2: N=172 WR 57% EV +0.056 ATR.
- 2026-04-20 Priority-2 audit: EUR_USD Scalp 1m 60d EV +0.271 → 180d EV −0.147 (ORB-trap divergence pattern).
- Instant-death (LOSS MFE=0): 75.9% pre-v8.3 → 71% post (≈ unchanged, per index.md L156).
- REGIME_ADAPTIVE asymmetry documented: BUY MR / SELL TF on `trend_down_*`. The new `Tokyo × SELL` survivor is consistent with this — Tokyo USD_JPY tends to mean-revert intraday, and SELL has historically been the asymmetric winner for fib_reversal.

## 4. Three most important alignment / discrepancy points

1. **Alignment — strongly confirms an edge already pre-registered.** Sub-conditional Bonferroni A4 (today) and Cell-Promotion C1 (Apr-27) both isolated the same `fib_reversal × USD_JPY × Tokyo × SELL × Scalp` micro-cell with Wilson_BF ≈ 0.69–0.71 and Bonferroni p ≈ 0.0007. The new shadow numbers (N=24/20, WR 87.5%/90%, WF 4/4) are a third independent re-confirmation. **Status of the edge in KB should be upgraded** from "no BT data / FORCE_DEMOTED aggregate" to "FORCE_DEMOTED aggregate but Shadow-confirmed conditional edge on Tokyo×SELL micro-cell, sentinel 0.01 deployed".

2. **Discrepancy / stale data — `index.md` L67 says "no BT data" and `tier-master.md` §B-1 line 55 leaves all three EV columns blank.** This is now demonstrably wrong: there is conditional BT/Shadow evidence, plus a 180d aggregate Scalp EV (−0.308) and a 365d sub-conditional positive (+13.16p). The aggregate row hides Simpson/Aggregate-Fallacy (per the CLAUDE.md "Aggregate Fallacy" note). Tier-master should at minimum carry a footnote pointing at the conditional cell.

3. **Risk flag — small-sample / shadow-only / friction underestimate.** Three KB items are directly relevant and **must be cited** in any update:
   - `lesson-orb-trap-bt-divergence` and `lesson-cell-audit-bt-required-2026-04-27` (60d positive → 180d negative pattern; same fib_reversal saw it in April).
   - claude-mem 2026-04-26 finding that Tokyo friction is **2× under-modelled** → shadow EV +11p could be +5–6p under v2 friction.
   - `lesson-shadow-vs-live-confusion-2026-04-28` (today's lesson) → Wilson_BF 0.69 in Shadow ≠ 0.69 in Live. Sentinel 0.01 lot is the right discount, not 0.05+.
   The `aggressive-edge-deployment-2026-04-28.md` doc already captures all three caveats; the new finding does **not** weaken them.

## 5. Does the new finding contradict / confirm / extend?

**Confirms + tightens, does not contradict.**

- *Confirms* the C1 / A4 cell with one more week of shadow data; Wilson bound improved from 0.690 → 0.706 → 0.69 (essentially stable at the 0.7 floor). 4/4 walk-forward folds = consistent with what `pre-reg-cell-promotion` and `aggressive-edge-deployment` already showed.
- *Tightens* the SELL-direction asymmetry: 3D STRICT cell at N=20 WR=90% is the SELL-only slice; aggregate N=24 WR=87.5% adds 4 BUY trades that drag WR slightly. Consistent with the fib_reversal REGIME_ADAPTIVE family (SELL aligned with intraday Tokyo MR).
- *Extends* nothing fundamentally new about fib_reversal's mechanism. Day-of-week (Wednesday concentration) is a **new** observation and is **not** in any KB page; it should be flagged as a **hypothesis to track**, not yet a confirmed feature, given N=24.
- No KB statement is overturned. The "London friction lowest" claim in friction-analysis is about cost, not gross edge, so Tokyo-prime gross WR being highest is fully compatible.

## 6. Concrete KB update proposals (NOT executed)

| File | Section | Proposed change |
|---|---|---|
| `wiki/index.md` | Row 67 (`fib-reversal`) | Change `no BT data` → `FORCE_DEMOTED aggregate; Tokyo×USD_JPY×SELL×Scalp shadow-confirmed (N=24 WR 87.5% Wilson_BF 0.69 EV +11.0p, sentinel 0.01)`. Add link to `aggressive-edge-deployment-2026-04-28`. |
| `wiki/tier-master.md` | §B-1 row 8 | Add a footnote `*` → "conditional cell promoted to SENTINEL 0.01 lot; see aggressive-edge-deployment-2026-04-28 / pre-reg-cell-promotion-2026-04-27". Aggregate row stays FORCE_DEMOTED. |
| `wiki/strategies/fib-reversal.md` | Top of file (after `Status:` line) | Add `## 2026-04-28 Conditional Edge (USD_JPY × Tokyo × SELL × Scalp)` block: shadow N=24/20, WR 87.5%/90%, Wilson_BF, WF 4/4, sentinel 0.01 lot, gating thresholds (Wilson_lower<40% or WR<50% on Live N≥10 → demote). Reference C1/A4. |
| `wiki/strategies/fib-reversal.md` | Performance table | Append row: `Shadow Tokyo×SELL × Scalp (3D STRICT)` N=20 WR=90% EV +13.16p Wilson_BF 0.706 K=8 Bonferroni-passed. |
| `wiki/analyses/friction-analysis.md` | After §"Friction by Session" | Cross-link sentence: "Tokyo session has highest measured friction in the table; v2 multiplier under-models Tokyo by ~2× (claude-mem 2026-04-26). fib_reversal Tokyo edge is gross +11.0p shadow → expect ~+5–6p net under corrected friction." |
| `wiki/lessons/` | New lesson **proposal** (not blocker) | `lesson-conditional-vs-aggregate-edge-2026-04-28.md` — fib_reversal aggregate is FORCE_DEMOTED but Bonferroni-significant sub-cell exists; document the Aggregate Fallacy in concrete terms. |
| `wiki/decisions/aggressive-edge-deployment-2026-04-28.md` | Add appendix | Note Wednesday-day-of-week concentration as a **hypothesis-to-track, N=24 too small to act on** (avoid HARKing). |

## 7. Open questions for the user (deferred)

- Should the day-of-week (Wednesday) concentration be pre-registered as a separate sub-grid, or watched silently until N≥40?
- Friction v2 fix (Tokyo 2× under-estimate) is a more general issue — propose separate Phase-8 track to refit the multipliers before scaling sentinel beyond 0.01 lot.

---

**Verdict**: The new shadow finding is a **confirmation**, not a contradiction. The KB has stale rows in `index.md` and `tier-master.md` that pre-date the C1/A4 conditional-edge findings; updating those is the highest-leverage change. The aggregate FORCE_DEMOTED status should remain — only the *conditional* cell graduates.
