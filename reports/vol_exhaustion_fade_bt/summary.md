# Vol Exhaustion Fade BT Summary

Generated: 2026-05-18T04:51:39.746731+00:00
Data: MASSIVE_parquet USD_JPY M5, spread=1.3 pip per side
Period: 2014-01-02T04:55:00+00:00 .. 2026-04-30T23:55:00+00:00
Data caveat: local cache ends before target 2026-05-14; backfill required for exact target-window rerun.
Pre-reg m: 48, Bonferroni alpha: 0.00104167

## Verdict Matrix
- Family A SHADOW_CANDIDATE: 0
- Family A NEEDS_MORE_EVIDENCE: 0
- Family A REJECT: 48
- Family B generated cells: 48

## Family A Top Cells
- K=4.5 H=3 session=ASIAN_15-22_UTC N=3025 WR=0.447 Wilson_lo=0.430 EV=-1.99pip PF=0.41 Kelly=-0.645 p_BH=1.000000 WF=False Verdict=REJECT
- K=4.5 H=6 session=ASIAN_15-22_UTC N=3025 WR=0.491 Wilson_lo=0.473 EV=-2.05pip PF=0.42 Kelly=-0.664 p_BH=1.000000 WF=False Verdict=REJECT
- K=4 H=3 session=ASIAN_15-22_UTC N=4201 WR=0.418 Wilson_lo=0.403 EV=-2.06pip PF=0.38 Kelly=-0.686 p_BH=1.000000 WF=False Verdict=REJECT
- K=4.5 H=12 session=ASIAN_15-22_UTC N=3025 WR=0.517 Wilson_lo=0.500 EV=-2.09pip PF=0.44 Kelly=-0.671 p_BH=1.000000 WF=False Verdict=REJECT
- K=4 H=6 session=ASIAN_15-22_UTC N=4201 WR=0.470 Wilson_lo=0.455 EV=-2.10pip PF=0.40 Kelly=-0.698 p_BH=1.000000 WF=False Verdict=REJECT
- K=4 H=12 session=ASIAN_15-22_UTC N=4201 WR=0.508 Wilson_lo=0.493 EV=-2.11pip PF=0.42 Kelly=-0.694 p_BH=1.000000 WF=False Verdict=REJECT
- K=3.5 H=12 session=ASIAN_15-22_UTC N=6099 WR=0.506 Wilson_lo=0.494 EV=-2.11pip PF=0.41 Kelly=-0.722 p_BH=1.000000 WF=False Verdict=REJECT
- K=3.5 H=3 session=ASIAN_15-22_UTC N=6099 WR=0.399 Wilson_lo=0.386 EV=-2.11pip PF=0.35 Kelly=-0.738 p_BH=1.000000 WF=False Verdict=REJECT
- K=3.5 H=6 session=ASIAN_15-22_UTC N=6099 WR=0.463 Wilson_lo=0.450 EV=-2.12pip PF=0.39 Kelly=-0.736 p_BH=1.000000 WF=False Verdict=REJECT
- K=3 H=12 session=ASIAN_15-22_UTC N=9096 WR=0.498 Wilson_lo=0.487 EV=-2.14pip PF=0.40 Kelly=-0.737 p_BH=1.000000 WF=False Verdict=REJECT

## Family B Top Cells
- K=3 H=12 session=ASIAN_15-22_UTC N=459 WR=0.368 Wilson_lo=0.325 EV=-2.44pip PF=0.50 Kelly=-0.372 p_BH=1.000000 WF=False Verdict=REJECT
- K=3.5 H=12 session=ASIAN_15-22_UTC N=459 WR=0.368 Wilson_lo=0.325 EV=-2.44pip PF=0.50 Kelly=-0.372 p_BH=1.000000 WF=False Verdict=REJECT
- K=4 H=12 session=ASIAN_15-22_UTC N=459 WR=0.368 Wilson_lo=0.325 EV=-2.44pip PF=0.50 Kelly=-0.372 p_BH=1.000000 WF=False Verdict=REJECT
- K=4.5 H=12 session=ASIAN_15-22_UTC N=459 WR=0.368 Wilson_lo=0.325 EV=-2.44pip PF=0.50 Kelly=-0.372 p_BH=1.000000 WF=False Verdict=REJECT
- K=3 H=6 session=ASIAN_15-22_UTC N=459 WR=0.342 Wilson_lo=0.300 EV=-2.69pip PF=0.42 Kelly=-0.479 p_BH=1.000000 WF=False Verdict=REJECT

## Gate Definitions
- G1 N: N >= 30
- G2 Wilson: Wilson lower 95% >= 0.50
- G3 EV: EV pip/trade after round-trip spread > 0
- G4 Bonf/BH: BH adjusted p < 0.00104167
- G5 PF: PF >= 1.20
- G6 Kelly: Kelly fraction >= 0.05
- G7 WF: 3 chronological folds all EV > 0

## Re-grid Candidates
- Keep MA trend filters out; the current failure/survival pattern should be explored with K/cooldown/session/exit geometry only.
- Phase B candidates: cross-pair OOS on non-XAU FX majors and a cooldown sweep around 0/3/6 bars.
