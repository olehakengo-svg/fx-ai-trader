# Scalp Re-enable BT Summary — 2026-05-03

Strategy: `mtf_regime_trend_cascade_scalp`
Pair: `USD_JPY`
Interval: `5m`
Lookback: `180d`
Verdict: `Reject`

## Pre-registered thresholds

- Promote: N>=30, PF>=1.3, Wilson_lo > BEV+5pp, WF PF_IS/OOS>=1.2, Bonferroni p<0.01000, max DD<=30%
- Shadow: N>=30, PF>=1.1, Wilson_lo > BEV, WF PF_IS/OOS>=1.0, max DD<=30%
- Reject: anything else. Insufficient: N<30.

## Selected engine stats

- Engine: `vec_harness`
- N/W/L: 34 / 14 / 20
- WR: 41.176%
- EV: -1.242 pip/trade
- PF: 0.741
- Wilson 95%: [26.366%, 57.778%]
- BEV_WR: 34.400%
- Bonferroni: K=5, p=0.25743375, alpha/K=0.01
- Kelly half: 0.000000
- Max DD: 75.809 pip, 364.261%

## Walk-forward 50/50

- IS: N=14, WR=50.000%, PF=1.083, EV=0.322
- OOS: N=20, WR=35.000%, PF=0.571, EV=-2.337

## Engine comparison

- Standard BT N: 0
- Standard BT: unavailable (standard run_scalp_backtest exceeded 600s timeout)
- Vec harness N: 34
- N gap: 100.000%
- Oracle selection: `vec_harness`

## Live-comparable subset

- Cutoff: `2026-04-08T00:00:00+00:00`
- N/W/L: 1 / 1 / 0
- WR: 100.000%
- EV: 12.760
- PF: inf
