# CMA loss_hunt — trendline_sweep GBP_USD → shadow-first conversion (FINAL VERDICT)

**Outcome mode:** loss_hunt — identify ONE LIVE losing factor and convert it to a shadow-first, rubric-verified edge.
**Coordinator (司令塔) run:** 2026-07-13. North star = monthly return; promotion = rubric-only; pre-reg written to ledger first.
**Pre-reg ledger id:** `trendline_sweep_gbpusd_pairscope_2026-07-13` (LOCK 2026-07-13T20:11:11Z; Amendment 1 20:21:45Z).
**Reviewer verdict:** **satisfied** (adversarial, independent recompute — no arithmetic errors).
**Terminal action:** DEMOTE `trendline_sweep` from ELITE_LIVE → shadow-first for ALL cells. Promote NOTHING. `propose_live_flip` fired: **NONE**.

---

## 1. Losing factor identified (PRIMARY data = Render production API, is_shadow separated)
`trendline_sweep` (SMC "liquidity sweep → reclaim → continuation", DT 15m) is **ELITE_LIVE**: it bypasses the
shadow→live promotion system and trades all allowed pairs on real money, earned ONLY on a favorable 365d backtest
(GBP_USD BT WR≈73% EV +0.60; EUR_USD BT WR≈81% EV +0.93; `modules/demo_trader.py:7410`). The rubric explicitly
bars a favorable BT as promotion evidence → the ELITE_LIVE seat is un-earned.

Forward reality (Render `/api/demo/factors` + `/api/demo/trades`):
| cell | cohort | N | WR | netEV | RR(realized) | MFE | note |
|---|---|--:|--:|--:|--:|--:|---|
| trendline_sweep GBP_USD | **LIVE** | 19 | 63.2% | **−2.35p** | 0.15 | +3.08 | avgWin +1.67 / avgLoss −11.07 |
| trendline_sweep GBP_USD | shadow | 39 | 61.5% | −3.49p | 0.15 | +3.02 | SL_HIT 33 / REVERSE 6 |
| trendline_sweep EUR_GBP | shadow | 49 | 57.1% | −1.52p | 0.31 | +2.23 | — |
| trendline_sweep EUR_USD | shadow | 40 | 80.0% | +1.72p | 0.44 | +6.90 | (looked +EV in fwd shadow) |

Root cause: designed TP = 2.5·ATR (~20p+) but GBP_USD price only reaches +3.08p favorable → winners scratched
tiny, losers run the wide sweep-based SL. High WR is a tiny-TP artifact, not directional edge. Research verdict:
**concept-broken (class c)**, NOT exit-repairable (the exit/geometry-repair path is R1-KILLED,
`exit-repair-tp-sl-prereg-2026-07-07`, 0/9 configs).

## 2. Pre-registration (written BEFORE the conversion BT — discipline intact)
Ledger entry `trendline_sweep_gbpusd_pairscope_2026-07-13` @ 2026-07-13T20:11:11Z + KB LOCK doc
`knowledge-base/wiki/learning/trendline-sweep-gbpusd-loss-conversion-prereg-2026-07-13.md`.
Gates (LOCKED): G1 netEV>0 | G2 BH-FDR q=0.10 survive | G3 WF≥3/4 folds | G4 Wilson_lo≥0.40 (AND WR≥BE-WR at
realized payoff, per Amendment 1) | G5 friction≤10% TP | G6 both-legs net≥0. m=3 (orig) / m_effective=4 (Amendment 1).
Framing LOCKED to DEMOTE / pair-scope re-qualification only. EUR_USD carved out as protected positive control (WS3 track).
Pre-registered prediction: EUR_USD PASS; GBP_USD FAIL→shadow; EUR_GBP FAIL→shadow.

## 3. Verification (dev, 12y MASSIVE 15m walk-forward, production trigger UNCHANGED)
Artifact: `bt-results/trendline_sweep-12y-pairscope-2026-07-13.json`; tool `tools/trendline_sweep_12y_pairscope_bt.py`
(dev branch `research/trendline-sweep-12y-pairscope-2026-07-13`, uncommitted — merge is human/CI). ~309k bars/pair.

| pair | N | WR | netEV | grossEV(net+fric) | Wilson_lo | WF | fric/TP | p₁ | gates passed | verdict |
|---|--:|--:|--:|--:|--:|:--:|--:|--:|---|:--:|
| EUR_USD | 3036 | 43.8% | −0.483 | +0.945 | 0.4205 | 1/4 | 4.2% | 0.881 | G4,G5 | **FAIL** |
| GBP_USD | 4884 | 41.1% | −3.121 | **−0.095** | 0.3972 | 0/4 | 6.6% | 1.000 | G5 | **FAIL** |
| EUR_GBP | 2829 | 41.5% | −1.449 | +0.788 | 0.3973 | 0/4 | 8.7% | 1.000 | G5 | **FAIL** |

- BH-FDR q=0.10 (m=3 and m=4): **none survive**.
- GBP_USD both legs negative (BUY −3.46, SELL −2.79 pip/trade) → not a single-side artifact; genuinely no edge either way.
- **GBP_USD is gross-negative (−0.095)** → no friction level can rescue it (decisive for the LIVE loss factor).
- Favorable 365d BT (WR 73–81%) directly contradicted by 12y OOS (WR 41–44%, EV sign flips) = textbook selection bias.

## 4. Honesty note (anti-p-hack)
The pre-reg predicted **EUR_USD = PASS**; the 12y test measured **EUR_USD = FAIL** (netEV −0.48, WF 1/4, FDR fail).
Reported exactly as measured — no tuning, no goalpost-moving. This strengthens (not weakens) the conversion:
even the "best" cell does not deserve a favorable-BT LIVE seat.

## 5. Adversarial review (fxai-reviewer) — satisfied
Recomputed Wilson_lo / netEV / WF partition / BH-FDR by hand: no arithmetic errors. WF fold-N sums equal pair N
(complete non-overlapping partition on the 12y BT, not the shadow N → compliant). Friction production-faithful &
conservative. 300-bar ctx window verified signal-identical to production 3500. CONFIG_RAW EUR_USD/EUR_GBP BUY N=0
is an artifact defect but immaterial (BUY void by production SELL_ONLY; GBP_USD both legs captured & negative).
P-hack trap: clean (promotes nothing; demotes on 12y OOS + forward loss). **Verdict: satisfied. propose_live_flip: NONE.**

## 6. Conversion decision (rubric-compliant) & north-star linkage
1. **Remove the `trendline_sweep` ELITE_LIVE all-pairs bypass** (the losing factor). Consequence: every cell becomes
   shadow-first and rubric-gated.
2. **GBP_USD, EUR_GBP:** no edge (12y + forward) → **shadow-only**. Re-entry to LIVE requires forward shadow
   **N≥20 ∧ Wilson_lo≥0.40 (FDR) ∧ WR≥BE-WR at realized payoff** (Amendment-1 clause prevents a Wilson-technicality re-entry).
3. **EUR_USD:** also failed this 12y test; LIVE re-qualification deferred to its protected **WS3 track** — this 12y FAIL
   is logged there as evidence. No LIVE seat via favorable BT.
4. **No `propose_live_flip`, no `propose_sizing_change`.** Nothing qualifies.

North star: removing a proven real-money loss maker (GBP_USD ELITE_LIVE, forward −2.35 pip/trade, gross-negative) is a
direct, low-risk lift to monthly return, and it re-imposes the shadow-first discipline the ELITE_LIVE bypass had removed.
The "conversion" here is honest: an unverified LIVE bleeder → a shadow-first, rubric-gated cohort that currently holds
NO promotable edge. That is the correct outcome under the rubric ("BT+EV/月利達成 だけを満点にしない").

## 7. Follow-ups (housekeeping from review; none change the verdict)
- Routing change (remove ELITE_LIVE bypass + demote) = separate human/CI-reviewed PR; agents do not merge.
- Reconcile the BT tool (computes m=3 raw metrics + Wilson) with Amendment-1 (m=4, realized-payoff BE-WR) — gate
  interpretation applied at the coordinator/reviewer layer; verdict identical either way.
- Fix or relabel the CONFIG_RAW BUY-leg lift for structurally SELL-only pairs (cosmetic).
