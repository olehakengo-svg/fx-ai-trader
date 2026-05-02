# H-1 Hour-Bucket Counterfactual Replay Report

- **Generated**: 2026-05-02T19:45:05.053245Z
- **Source**: local SQLite (/Users/jg-n-012/test/fx-ai-trader/demo_trades.db)
- **Bucket mode**: 4_bucket
- **Total closed rows**: 475
- **Cells evaluated**: 164
- **Gate params**: N_min(live)=30, N_min(shadow)=20, wilson_lo>0.4, ev>-0.5pip

## Verdict distribution

| Verdict | Count |
|---|--:|
| n_below_min | 143 |
| grandfather | 20 |
| bucket_pass | 1 |

## Cells that would change tier (0)

(none)

## LIVE strategy regression check

✓ No non-grandfathered LIVE cells would demote.
