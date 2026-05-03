# H1 Hour-Bucket Design — Revised 3-Month Counterfactual

**Date**: 2026-05-03
**Status**: Revised design prepared; production counterfactual fetch blocked in this sandbox
**Task**: `.ai/tasks/queue/20260503-1135-h1-hour-bucket-3month-counterfactual.md`
**W2-4 reference**: commit `5150a1e`

## Objective

Extend the W2-4 H1 hour-bucket gate review from the original short-window check to a 3-month counterfactual over `2026-02-01` to `2026-05-01`, using production trade data only. The gate remains a promotion-path control, not a signal-stage time filter.

## Design Decisions

1. Bucket layout stays at 4 buckets by default:
   - Asia: `00-06 UTC`
   - London: `07-12 UTC`
   - NY-overlap: `13-16 UTC`
   - Off: `17-23 UTC`
2. Revised per-cell gate for the counterfactual:
   - `N >= 30`
   - `WR Wilson 95% lower > 0.40`
   - `EV 95% CI lower >= 0`
3. `N < 30` is always `insufficient data`, never an automatic reject.
4. Existing LIVE strategies are protected by grandfather logic. Verification target remains `bb_rsi_reversion/USD_JPY`, but any strategy observed as strict LIVE in the analysis window is treated as protected in the dry-run.
5. False demotion is measured against the existing shadow promotion gate: if the old logic would promote a strategy to LIVE, but the new bucket gate demotes an evaluated cell, that cell counts toward the false-demotion numerator.

## Implementation Scope

- New tool: [tools/h1_hour_bucket_counterfactual.py](/Users/jg-n-012/test/fx-ai-trader/tools/h1_hour_bucket_counterfactual.py)
- New tests: [tests/test_h1_hour_bucket_counterfactual.py](/Users/jg-n-012/test/fx-ai-trader/tests/test_h1_hour_bucket_counterfactual.py)
- Output report: [knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.md](/Users/jg-n-012/test/fx-ai-trader/knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.md)

No runtime promotion logic, OANDA modules, secrets, or production DB write paths are modified.

## Data Source Contract

- Primary source: Render production `/api/demo/trades`
- Strict LIVE filter: `is_shadow=0 AND oanda_trade_id IS NOT NULL`
- Strict SHADOW filter: `is_shadow=1`, non-XAU, `WIN/LOSS` only
- OOS split for reporting: IS `2026-02-01` to `2026-03-31`, OOS `2026-04-01` to `2026-05-01`

## A/B Plan

1. Control: existing promotion logic only.
2. Treatment: existing promotion logic plus H1 4-bucket cell gate.
3. Run mode: production remains control; treatment is evaluated by counterfactual replay on the same production trade window.
4. Monthly acceptance:
   - false demotion rate `< 20%`
   - no grandfathered LIVE regression
   - insufficient-data cells explicitly skipped
5. If false demotion rate is `>= 20%`, adjust thresholds or bucket boundaries before enabling any runtime gate.

## Current Blocker

This sandbox cannot resolve `fx-ai-trader.onrender.com`, so the required production fetch cannot complete here. The analyzer writes a blocked report with the exact failing fetch context rather than substituting local DB data.
