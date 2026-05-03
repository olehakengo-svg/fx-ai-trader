# Scalp alt pre-registration — 2026-05-03

**Rule**: `R1 Slow & Strict`
**Decision lineage**: `complex-gate-edge-destruction-pattern-2026-05-03` simple-first principle

## LOCKED thresholds

- Promote: N>=30, PF>=1.3, Wilson_lo > BEV_WR + 5pp, WF PF_IS>=1.2 and PF_OOS>=1.2, Bonferroni p<0.01250, max DD<=30%.
- Shadow: N>=30, PF>=1.1, Wilson_lo > BEV_WR, WF PF_IS>=1.0 and PF_OOS>=1.0, max DD<=30%.
- Reject: any other configuration. Insufficient: N<30.
- OVERFIT_SUSPECTED: OOS PF < IS PF x 0.85 triggers a one-tier downgrade.

## Bonferroni K=4 justification

- Decision pool fixed ex ante as 4 simple-structure scalp candidates: bb_squeeze_breakout, engulfing_bb, fib_reversal, sr_channel_reversal.
- Alpha/K = 0.01250.

## Summary table

| Strategy | Pair | TF | Roadmap EV | Complexity | Verdict | Flags | N | PF | Bonf p |
|---|---|---|---:|---|---|---|---:|---:|---:|
| `sr_channel_reversal` | `EUR_USD` | `5m` | 0.231 | SR / channel bounce (1 level set) | Promote | none | 52 | 2.724 | 0.00418322 |
| `fib_reversal` | `EUR_USD` | `1m` | 0.426 | Fib retracement (1 level set) | Reject | none | 101 | 3.150 | 0.00015895 |
| `engulfing_bb` | `USD_JPY` | `5m` | 0.677 | engulfing candle + BB extreme (2 conditions) | Reject | none | 30 | 1.557 | 0.09299531 |
| `bb_squeeze_breakout` | `USD_JPY` | `5m` | 1.030 | BB + squeeze (1 indicator + 1 condition) | Insufficient | none | 24 | 4.872 | 0.00023226 |

## Per-candidate quant table

| Strategy | Verdict | Flags | N | Wins/Losses | WR | EV pip/trade | PF | Wilson 95% CI | Max DD pip | Max DD % | WF PF IS/OOS | WF WR IS/OOS | Bonferroni one-sided p | half-Kelly |
|---|---|---|---:|---|---:|---:|---:|---|---:|---:|---|---|---:|---:|
| `sr_channel_reversal` | Promote | none | 52 | 32 / 20 | 61.538% | 0.373 | 2.724 | [47.960%, 73.530%] | 3.022 | 14.841 | 2.557 / 2.889 | 61.538% / 61.538% | 0.00418322 | 0.194700 |
Verdict note: all pre-registered conditions passed
| `fib_reversal` | Reject | none | 101 | 60 / 41 | 59.406% | 0.388 | 3.150 | [49.655%, 68.468%] | 2.983 | 220.963 | 2.157 / 4.956 | 50.000% / 68.627% | 0.00015895 | 0.202700 |
Verdict note: max DD > 30% or undefined
| `engulfing_bb` | Reject | none | 30 | 16 / 14 | 53.333% | 0.212 | 1.557 | [36.142%, 69.768%] | 7.566 | 188.209 | 1.162 / 1.948 | 40.000% / 66.667% | 0.09299531 | 0.095400 |
Verdict note: max DD > 30% or undefined, Bonferroni threshold failed for Promote
| `bb_squeeze_breakout` | Insufficient | none | 24 | 18 / 6 | 75.000% | 0.913 | 4.872 | [55.100%, 88.001%] | 2.976 | 26.731 | 2.442 / inf | 75.000% / 75.000% | 0.00023226 | 0.298000 |
Verdict note: N<30, gap_to_30=6

## Promote cap

- Promote candidates identified: 1 (at most one allowed by decision policy).
- Top ranked candidate: `sr_channel_reversal`.

## Recommendation

- Next recommended task: A3-simple — register the Promote candidate to OANDA bridge with monitoring
