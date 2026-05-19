# HighVol Continuation USDJPY M5 BT Summary

Generated: 2026-05-18T10:36:29.788173+00:00
Data: MASSIVE_parquet data/cache/massive/USD_JPY_5m_2014_2026.parquet
Period: 2014-01-02T04:55:00+00:00 .. 2026-04-30T23:55:00+00:00
Pre-reg cells: 375, Bonferroni alpha: 0.00013333

## Verdict Matrix
- Family A cells: 375
- Family A SHADOW_CANDIDATE: 0
- Family A NEEDS_MORE_EVIDENCE: 0
- Family A REJECT: 375
- Family B ablation cells: 375

## Family A Top Cells All Spreads
- K=4.5 H=12 hourset=AGENT_9_11_15 spread=0 N=735 WR=0.494 Wilson_lo=0.458 EV=1.09pip PF=1.19 Kelly=0.077 p_BH=1.000000 G8=True Verdict=REJECT
- K=4.5 H=12 hourset=AGENT_9_11_15 spread=0.2 N=735 WR=0.482 Wilson_lo=0.446 EV=0.89pip PF=1.16 Kelly=0.065 p_BH=1.000000 G8=True Verdict=REJECT
- K=4.5 H=12 hourset=LONDON_07_14 spread=0 N=3444 WR=0.502 Wilson_lo=0.485 EV=0.75pip PF=1.11 Kelly=0.047 p_BH=1.000000 G8=True Verdict=REJECT
- K=4.5 H=3 hourset=AGENT_9_11_15 spread=0 N=735 WR=0.497 Wilson_lo=0.461 EV=0.68pip PF=1.23 Kelly=0.083 p_BH=1.000000 G8=True Verdict=REJECT
- K=4 H=12 hourset=LONDON_07_14 spread=0 N=4960 WR=0.495 Wilson_lo=0.481 EV=0.62pip PF=1.10 Kelly=0.041 p_BH=1.000000 G8=True Verdict=REJECT
- K=4.5 H=12 hourset=AGENT_9_11_15 spread=0.5 N=735 WR=0.467 Wilson_lo=0.431 EV=0.59pip PF=1.10 Kelly=0.043 p_BH=1.000000 G8=False Verdict=REJECT
- K=4.5 H=12 hourset=LONDON_07_14 spread=0.2 N=3444 WR=0.494 Wilson_lo=0.478 EV=0.55pip PF=1.08 Kelly=0.037 p_BH=1.000000 G8=True Verdict=REJECT
- K=4 H=3 hourset=AGENT_9_11_15 spread=0 N=1121 WR=0.483 Wilson_lo=0.453 EV=0.53pip PF=1.19 Kelly=0.069 p_BH=1.000000 G8=True Verdict=REJECT
- K=4 H=12 hourset=AGENT_9_11_15 spread=0 N=1121 WR=0.474 Wilson_lo=0.445 EV=0.52pip PF=1.09 Kelly=0.036 p_BH=1.000000 G8=True Verdict=REJECT
- K=4.5 H=3 hourset=AGENT_9_11_15 spread=0.2 N=735 WR=0.486 Wilson_lo=0.450 EV=0.48pip PF=1.16 Kelly=0.066 p_BH=1.000000 G8=True Verdict=REJECT

## Family A Top Cells Baseline Spread 0.5
- K=4.5 H=12 hourset=AGENT_9_11_15 spread=0.5 N=735 WR=0.467 Wilson_lo=0.431 EV=0.59pip PF=1.10 Kelly=0.043 p_BH=1.000000 G8=False Verdict=REJECT
- K=4.5 H=12 hourset=LONDON_07_14 spread=0.5 N=3444 WR=0.488 Wilson_lo=0.471 EV=0.25pip PF=1.04 Kelly=0.017 p_BH=1.000000 G8=False Verdict=REJECT
- K=4.5 H=3 hourset=AGENT_9_11_15 spread=0.5 N=735 WR=0.464 Wilson_lo=0.428 EV=0.18pip PF=1.06 Kelly=0.025 p_BH=1.000000 G8=True Verdict=REJECT
- K=4 H=12 hourset=LONDON_07_14 spread=0.5 N=4960 WR=0.477 Wilson_lo=0.464 EV=0.12pip PF=1.02 Kelly=0.009 p_BH=1.000000 G8=False Verdict=REJECT
- K=4 H=3 hourset=AGENT_9_11_15 spread=0.5 N=1121 WR=0.448 Wilson_lo=0.419 EV=0.03pip PF=1.01 Kelly=0.005 p_BH=1.000000 G8=True Verdict=REJECT
- K=4 H=12 hourset=AGENT_9_11_15 spread=0.5 N=1121 WR=0.450 Wilson_lo=0.422 EV=0.02pip PF=1.00 Kelly=0.001 p_BH=1.000000 G8=False Verdict=REJECT
- K=4.5 H=6 hourset=LONDON_07_14 spread=0.5 N=3444 WR=0.475 Wilson_lo=0.458 EV=-0.06pip PF=0.99 Kelly=-0.006 p_BH=1.000000 G8=False Verdict=REJECT
- K=3.5 H=12 hourset=AGENT_9_11_15 spread=0.5 N=1842 WR=0.454 Wilson_lo=0.432 EV=-0.07pip PF=0.99 Kelly=-0.006 p_BH=1.000000 G8=False Verdict=REJECT
- K=4 H=6 hourset=LONDON_07_14 spread=0.5 N=4960 WR=0.469 Wilson_lo=0.455 EV=-0.07pip PF=0.99 Kelly=-0.007 p_BH=1.000000 G8=False Verdict=REJECT
- K=3 H=3 hourset=AGENT_9_11_15 spread=0.5 N=3066 WR=0.445 Wilson_lo=0.428 EV=-0.16pip PF=0.94 Kelly=-0.027 p_BH=1.000000 G8=False Verdict=REJECT

## Gate Definitions
- G1 N: N >= 30
- G2 Wilson: Wilson lower 95% >= 0.50
- G3 EV: EV pip/trade after round-trip spread > 0
- G4 Bonf/BH: BH adjusted p < 0.00013333
- G5 PF: PF >= 1.20
- G6 Kelly: Kelly fraction >= 0.05
- G7 WF: 3 chronological folds all EV > 0
- G8 Direction-led null: both BUY-only and SELL-only EV are positive
