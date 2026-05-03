# Scalp re-enable pre-registration — 2026-05-03

**Strategy**: `mtf_regime_trend_cascade_scalp` on `USD_JPY` `5m`
**Rule**: `R1 Slow & Strict`
**BT engine of record**: `vec_harness`
**Current verdict**: `Reject`

## 1. Strategy

- Objective: evaluate whether `mtf_regime_trend_cascade_scalp` should be re-enabled for Scalp N-acceleration without editing `app.py` in this task.
- BT source of truth for the decision is the 180d deterministic local-cache run, cross-checked against the vector harness oracle.
- Live remains the source of truth for any later production promotion; this document only locks the decision thresholds and the BT evidence.

## 2. Pre-registered thresholds

- Promote: N>=30, PF>=1.3, Wilson_lo > BEV_WR + 5pp, WF PF_IS>=1.2 and PF_OOS>=1.2, Bonferroni p<0.01000, max DD<=30%.
- Shadow: N>=30, PF>=1.1, Wilson_lo > BEV_WR, WF PF_IS>=1.0 and PF_OOS>=1.0, max DD<=30%.
- Reject: any other configuration. Insufficient: N<30.

## 3. BT evidence

- Engine selected for verdict: `vec_harness`. Standard BT strategy N=0; vec harness strategy N=34.
- Standard BT availability: `False`; reason: standard run_scalp_backtest exceeded 600s timeout.
- Vec harness availability: `True`; reason: completed.
- N / Wins / Losses: 34 / 14 / 20
- WR: 41.176%
- EV: -1.242 pip/trade
- PF: 0.741
- Wilson 95% CI: [26.366%, 57.778%]
- BEV_WR (USD_JPY): 34.400%
- Bonferroni one-sided p: 0.25743375
- Kelly half: 0.000000
- Max DD: 75.809 pip / 364.261%

## 4. Walk-Forward summary

- Split: 50/50 time split at 2026-01-31T20:59:00+00:00
- IS: N=14, WR=50.000%, PF=1.083, EV=0.322
- OOS: N=20, WR=35.000%, PF=0.571, EV=-2.337

## 5. Bonferroni K-value justification

- K=5. Decision pool fixed ex ante as 5 scalp candidates: primary mtf_regime_trend_cascade_scalp plus 4 roadmap-v2.1 alternatives (bb_squeeze_breakout, engulfing_bb, fib_reversal, sr_channel_reversal).
- Alpha/K = 0.01000.

## 6. Verdict

- Locked verdict: `Reject`.
- Deterministic reasons: PF<1.1, Wilson_lo<=BEV_WR, WF shadow threshold failed, max DD > 30% or undefined, Bonferroni threshold failed for Promote
- Live-comparable subset from 2026-04-08T00:00:00+00:00: N=1, WR=100.000%, EV=12.760, PF=inf.

## 7. Lock statement

- The thresholds above were encoded in `tools/scalp_re_enable_bt.py` before the BT output was reviewed.
- This task does not edit `app.py` `QUALIFIED_TYPES`; any later registration must happen in a separate reviewed task.

## 8. Alternative candidate scan

- `bb_squeeze_breakout` USD_JPY 5m: verdict `Insufficient`, N=0, PF=n/a, WR=0.000%, EV=0.000
- `engulfing_bb` USD_JPY 5m: verdict `Insufficient`, N=0, PF=n/a, WR=0.000%, EV=0.000
- `fib_reversal` EUR_USD 1m: verdict `Insufficient`, N=0, PF=n/a, WR=0.000%, EV=0.000
- `sr_channel_reversal` EUR_USD 5m: verdict `Insufficient`, N=0, PF=n/a, WR=0.000%, EV=0.000

## 9. Live N target

- Minimum live target after any registration step: N>=30 before claiming Promote-quality evidence from Live.
- If registered as Shadow, lot remains 0.1 until live N and BT/live drift checks are reviewed separately.

## 10. Stopping criteria

- Stop and do not re-enable if live N stays below 30 or drift shows PF<1.0 after enough observations.
- If primary remains Reject or Insufficient, advance the next Scalp candidate instead of weakening thresholds.
