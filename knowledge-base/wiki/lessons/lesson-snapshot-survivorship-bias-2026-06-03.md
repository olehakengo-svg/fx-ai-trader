---
title: Snapshot Survivorship Bias — Demo Open-Position View Misled Cell-Edge Hypothesis
date: 2026-06-03
trigger_quote: "現在のデモページを参照するとshadowで含み益が多い"
verdict: hypothesis_rejected_at_cell_level; structural_fix_identified
---

# Lesson: Snapshot of open positions ≠ population truth

## What happened

User looked at `/demo-analysis` and noticed many open shadow positions
showing unrealized gains (12 winners / 4 losers, +39.8 pips snapshot).
Reasonable hypothesis: "cell-level extraction should find winning cells."

Closed-trade audit (`is_shadow=1`, post-FIDELITY_CUTOFF, no XAU, N=7,311):

- WR 23.7% / EV −1.49p / sumP −10,896p / PF 0.675
- BH-FDR (q=0.10) over 69 cells (N≥30) → **0 survivors**

The snapshot was **survivor-biased**: SL_HIT losers exit and disappear from
the open list, while winners linger awaiting TP. The static view is the
**ratio of remaining trades**, not the **ratio of all trades**.

## What was actually broken

Cell selection wasn't the problem — **exit logic** was. Average MFE
peaks at +4.90p but average final lands at −1.49p, a 6.39p/trade
"giveback". 47.5% of trades reach MFE ≥ +2p; **50.9% of those still close
at loss**. Existing ATR×0.8 BE fires too late for the +2p MFE class.

Counterfactual (`if MFE ≥ +2, lock SL at entry+1`) flips the entire pool:
EV −1.49 → +0.06, sumP −10,896 → +468, PF 0.675 → 1.020.

## The discipline failure to avoid

1. **Don't read snapshot stats as population stats.** Open-position views
   over-represent winners structurally. Always cross-check against closed
   data for the same time window.
2. **Cell extraction was the right diagnostic but the wrong fix locus.**
   The cells weren't broken; the exit was. Cell-level FDR-zero ≠ "no
   edge anywhere" — it can mean "edge exists but is structurally
   bled away before close."
3. **Average MFE >> average PnL is a giveback signature.** Whenever the
   ratio mean(MFE) / mean(|PnL|) exceeds ~3, suspect exit-logic decay
   before testing entry-side hypotheses.

## Fix applied

See `wiki/analyses/mfe-be-lock-design-2026-06-03.md`. Shipped as Rule-3
(算数破綻) shadow-only A/B with `SHADOW_BE_LOCK_AB_FRACTION=0.5` and
`SHADOW_BE_LOCK_ENABLE=1` env on Render. Live promotion gated by Rule-1
evidence (`tools/be_lock_ab_monitor.py` 30-day Welch t-test).

## Heuristic for next time

When the user (or you) point at a snapshot metric:

> **"Is this metric computed from snapshot of currently-open positions,
> or from the closed-trade population over a fixed window?"**

Always answer this *before* forming the next hypothesis.
