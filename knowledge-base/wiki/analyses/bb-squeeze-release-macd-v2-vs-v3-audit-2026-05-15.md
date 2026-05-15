---
title: bb_squeeze_release_macd v2 vs v3 — TV BT comparison
date: 2026-05-15
status: AUDIT
related:
  - knowledge-base/wiki/strategies/bb-expansion-macd-cross.md
  - bt-results/tv-overlays/bb_squeeze_release_macd-v2.pine
  - bt-results/tv-overlays/bb_squeeze_release_macd-v3.pine
---

# Context

V2 (TTM-Squeeze + band-break + MACD crossover event) was visual-falsified 2026-05-14:
USDJPY 4H iter K config produced N=99 over 13.4y but only **1 visible entry** in the Oct'25-Feb'26 4-month window, against 15-20 obvious squeeze→release setups. Root cause: composite gate required `ta.crossover` (1-bar event) to coincide with `release_fired` (12-bar window) AND `hist_accel` AND EMA200 AND session — alignment too rare.

V3 redesign (user-approved path A, 2026-05-15): replace MACD crossover **event** with MACD **state + recency**:
```pine
macd_above = macd_line > signal_line
bars_since_macd_cross_up = ta.barssince(ta.crossover(macd_line, signal_line))
macd_buy = macd_above and bars_since_macd_cross_up <= macd_recall   // default 6
```
Mirrors v2 squeeze treatment (state + recency). Every gate is now a window, not a knife-edge.

# BT results (USDJPY 4H, OANDA friction 0.0068%)

Period: Jan 2, 2013 → May 15, 2026 (13.4y). Same chart, same parameters except MACD gate.

| Metric            | v2 iter K | v3 baseline | Δ        |
|-------------------|----------:|------------:|---------:|
| Total trades (N)  | 99        | **351**     | **+255% (3.55x)** |
| WR                | ~46%      | 38.18%      | -7.8pp   |
| PF                | 1.635     | 1.194       | -0.44    |
| Net P&L           | (TBD)     | +1.39% / +139.37 JPY | — |
| Max DD            | (TBD)     | 0.79%       | —        |
| Annualized N      | 7.4/yr    | 26.2/yr     | +18.8    |
| Realized RR       | ~2.0      | ~1.93       | -0.07R (friction) |

**Wilson 95% lower (WR)**: at WR=0.3818, N=351 → SE=0.0259, lo≈33.1%
**BEV_WR (USDJPY 4H, RR=1.93 realized)**: ≈ 1/(1+1.93) = 34.1%
**Margin above BEV**: ~4.1pp; Wilson_lo at BEV line → **marginal +EV**

# Visual audit (same Oct'25-Feb'26 4-month window)

- v2: **1 BUY entry visible** vs ~15-20 squeeze→release setups
- v3: **~6-7 entries visible** (mix of BUY/SELL, TP/SL)
- Saved: `bt-results/tv-overlays/v3-screenshots/v3-chart-oct25-feb26.png`

Confirmation: v3 entries fire DURING release window after squeeze ends (no longer mid-squeeze like v1, no longer missing the window like v2).

# Diagnosis

The v3 frequency lift came at expected cost:
- WR fell because MACD state ≠ MACD reversal momentum. Some entries fire mid-trend continuation with weaker pop than fresh crosses.
- PF fell because losers got proportionally larger share.
- But NetP positive, MaxDD tiny, statistical power 3.5x stronger.

This is a **statistically marginal but practically observable** edge — appropriate for SCALP_SENTINEL Live N accumulation, NOT for full deploy/lot-scaling.

# Open questions before Python production

1. **macd_recall sensitivity**: is K=6 optimal? K=3 (stricter) might recover PF at lower N.
2. **release_recall × macd_recall interaction**: tightening both might find a higher-PF sweet spot.
3. **hist_accel toggle**: with state-based MACD, is hist_accel still net-positive?
4. **Cross-pair**: v2 was USDJPY-only. v3 cross-pair validation needed before any non-USDJPY promotion.

# Recommendation

**Path forward (R1)**:
1. Run v3 ablation on USDJPY 4H: (macd_recall=3,6,9) × (release_recall=6,12,18) × (hist_accel ON/OFF) — 18 cells
2. Pick best (max PF s.t. N≥150) as v3-OPTIMAL
3. Python production class with v3-OPTIMAL config
4. Deploy to SCALP_SENTINEL (minimal lot, Live shadow)
5. Pre-reg stop conds:
   - Live N=10 with Wilson_lo < 28% → stop
   - Live N=20 with PF < 0.8 → stop
   - Live N=30 with EV < -1.0p → stop

**Alternative (faster)**: skip ablation, deploy v3 baseline (macd_recall=6) to SCALP_SENTINEL. Risk: a 30-min ablation could surface a materially better config.

# Asymmetric Agility classification

**R1 (Slow & Strict)** — new strategy promotion. 365d BT (covered by 13.4y TV run) + Bonferroni-conscious + pre-reg stop conds + Python tests.
