# CMA loss_hunt — trendline_sweep GBP_USD -> shadow-first conversion (FINAL VERDICT)

Outcome: loss_hunt — identify ONE LIVE losing factor and convert it to a shadow-first, rubric-verified edge.
Coordinator run 2026-07-13. North star = monthly return; promotion = rubric-only; pre-reg written to ledger FIRST.
Pre-reg ledger id: trendline_sweep_gbpusd_pairscope_2026-07-13 (LOCK 2026-07-13T20:11:11Z; Amendment 1 20:21:45Z).
Reviewer verdict: SATISFIED (adversarial, independent recompute — no arithmetic errors).
Terminal action: DEMOTE trendline_sweep from ELITE_LIVE -> shadow-first for ALL cells. Promote NOTHING. propose_live_flip: NONE.

## 1. Losing factor (PRIMARY = Render API, is_shadow separated)
trendline_sweep (SMC sweep->reclaim->continuation, DT 15m) is ELITE_LIVE: bypasses the shadow->live promotion
system and trades all pairs on real money, earned ONLY on a favorable 365d BT (GBP_USD WR~73% EV+0.60; EUR_USD
WR~81% EV+0.93; modules/demo_trader.py:7410). The rubric bars a favorable BT as promotion evidence -> unearned seat.
Forward: GBP_USD LIVE n=19 WR63.2% netEV-2.35 realizedRR0.15 (avgWin+1.67/avgLoss-11.07) MFE+3.08; shadow n=39
netEV-3.49. EUR_GBP shadow n=49 netEV-1.52. EUR_USD shadow n=40 WR80% netEV+1.72 MFE+6.90.
Root cause: designed TP=2.5*ATR (~20p+) but GBP_USD only reaches +3.08p favorable -> winners scratched, losers run
the wide sweep SL. High WR is a tiny-TP artifact, not directional edge. Research: concept-broken (class c); NOT
exit-repairable (that path is R1-KILLED, exit-repair-tp-sl-prereg-2026-07-07, 0/9 configs).

## 2. Pre-registration (BEFORE the conversion BT)
Ledger trendline_sweep_gbpusd_pairscope_2026-07-13 @2026-07-13T20:11:11Z + KB LOCK doc
knowledge-base/wiki/learning/trendline-sweep-gbpusd-loss-conversion-prereg-2026-07-13.md.
Gates: G1 netEV>0 | G2 BH-FDR q0.10 survive | G3 WF>=3/4 | G4 Wilson_lo>=0.40 (AND WR>=BE-WR@realized payoff, Amdt1)
| G5 friction<=10% TP | G6 both-legs net>=0. m=3 orig / m_effective=4. Framing LOCKED to DEMOTE/pair-scope only.
Predicted: EUR_USD PASS; GBP_USD FAIL->shadow; EUR_GBP FAIL->shadow.

## 3. Verification (dev, 12y MASSIVE 15m WF, production trigger UNCHANGED) — bt-results/trendline_sweep-12y-pairscope-2026-07-13.json
pair | N | WR | netEV | grossEV | Wilson_lo | WF | fric/TP | p | verdict
EUR_USD | 3036 | 43.8% | -0.483 | +0.945 | 0.4205 | 1/4 | 4.2% | 0.881 | FAIL
GBP_USD | 4884 | 41.1% | -3.121 | -0.095 | 0.3972 | 0/4 | 6.6% | 1.000 | FAIL
EUR_GBP | 2829 | 41.5% | -1.449 | +0.788 | 0.3973 | 0/4 | 8.7% | 1.000 | FAIL
BH-FDR q0.10 (m=3 and m=4): none survive. GBP_USD both legs negative (BUY -3.46, SELL -2.79). GBP_USD gross-negative
-> no friction rescues it. Favorable 365d BT contradicted by 12y OOS (WR 73-81%->41-44%, EV sign flips) = selection bias.

## 4. Honesty (anti-p-hack)
Pre-reg predicted EUR_USD=PASS; 12y measured EUR_USD=FAIL (netEV-0.48, WF1/4, FDR fail). Reported as measured, no tuning.
Even the best cell does not deserve a favorable-BT LIVE seat.

## 5. Adversarial review (fxai-reviewer) = SATISFIED
Recomputed Wilson_lo/netEV/WF-partition/BH-FDR by hand: no errors. WF fold-N = pair N (complete non-overlapping
partition on 12y BT, not shadow N). Friction production-faithful & conservative. 300-bar ctx = signal-identical to
production 3500. CONFIG_RAW BUY N=0 artifact immaterial (BUY void by SELL_ONLY; GBP_USD both legs captured & negative).
P-hack trap clean. propose_live_flip: NONE.

## 6. Conversion decision (rubric-compliant) & north star
1. Remove trendline_sweep ELITE_LIVE all-pairs bypass (the losing factor) -> every cell shadow-first, rubric-gated.
2. GBP_USD, EUR_GBP: no edge -> shadow-only. Re-entry needs shadow N>=20 AND Wilson_lo>=0.40(FDR) AND WR>=BE-WR@realized-payoff.
3. EUR_USD: also failed 12y; LIVE re-qual deferred to protected WS3 track (12y FAIL logged as evidence).
4. No propose_live_flip, no propose_sizing_change — nothing qualifies.
North star: removing a proven real-money loss maker (GBP_USD ELITE_LIVE, -2.35 pip/trade, gross-negative) lifts monthly
return and re-imposes shadow-first discipline. The conversion is honest: an unverified LIVE bleeder -> a shadow-first,
rubric-gated cohort that currently holds NO promotable edge (correct under the rubric: do not score BT+EV alone).

## 7. Follow-ups (housekeeping; none change verdict)
- Routing change (remove bypass + demote) = separate human/CI PR; agents do not merge.
- Reconcile BT tool (m=3 raw metrics) with Amendment-1 (m=4, realized-payoff BE-WR) at the gate-interpretation layer.
- Fix/relabel CONFIG_RAW BUY-leg lift for SELL-only pairs (cosmetic).
