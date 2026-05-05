# Neighborhood Stability Gate (NSG-1 Protocol) — 2026-05-04

**Status**: recovered working copy for Codex implementation  
**Note**: The task referenced this decision as pre-existing, but it was absent from the working tree. This file records the NSG-1 implementation contract used by Codex and appends the required retrospective summary table.

## 1. Purpose

NSG-1 prevents post-hoc parameter selection traps where the locked primary cell fails but nearby or wider-grid cells look attractive after the result is known. A promotion candidate must show stable local parameter behavior around the pre-registered primary cell.

## 2. Metrics

Given a parameter grid with a primary cell and Hamming-distance-1 neighbors:

| Metric | Definition | Pass threshold |
|---|---|---|
| NSG-1.A `median_lift` | median neighbor `wilson_lo` divided by primary `wilson_lo` | `>= 0.80` |
| NSG-1.B `sign_agreement` | fraction of eligible neighbors with `wilson_lo >= BEV_WR` | `> 0.50` |
| NSG-1.C `variance_cv` | stdev of neighbor Kelly divided by `max(abs(primary_kelly), 0.01)` | `<= 1.00` |

Neighbor cells with `N < 5` are excluded. Axes with fewer than 3 grid steps are excluded from metric A and recorded in `skipped_axes`.

## 3. Retrospective Test Cases

| Case | Target | Expected |
|---|---|---|
| A | W3-3 S4 Connors-Raschke primary fail / grid-selection trap | FAIL |
| B | W3-2 S2 Turtle confirmation | PASS |
| C | Tier 1 `doji_breakout` confirmation | PASS |

NSG-1 retrospective summary table:

| Case | Source basis | median_lift | sign_agreement | variance_cv | Verdict | Expected | Match |
|---|---|---:|---:|---:|---|---|---|
| A: W3-3 S4 | Recovered S4 subset from committed Scenario C decision | 0.995 | 1.000 | 1.785 | FAIL | FAIL | yes |
| B: W3-2 Turtle | Documented S2 BT stats, reconstructed local neighborhood | 0.986 | 1.000 | 0.025 | PASS | PASS | yes |
| C: doji_breakout | 365d BT pair cells, `GBP_USD` primary | 1.041 | 1.000 | 0.141 | PASS | PASS | yes |

## 4. Threshold Sweep Rule

If any retrospective case diverges from expected behavior, run one threshold sweep only and document the result in the retrospective report. No sweep was needed for the initial implementation because all cases matched.

## 5. Acceptance Criteria

- `tools/audit/neighborhood_stability.py` implements the pure NSG-1 classifier.
- Unit tests cover smooth pass, A fail, B fail, C fail, boundary handling, small-N exclusion, and missing primary handling.
- `tools/audit/gate0_evaluator.py --require-nsg1 --help` works.
- Retrospective MD and JSON reports are present.
