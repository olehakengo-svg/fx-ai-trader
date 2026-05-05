# NSG-1 Retrospective — W3-3 S4 / Turtle S2 / doji_breakout

**Date**: 2026-05-04  
**Implementation**: `tools/audit/neighborhood_stability.py`  
**Summary JSON**: `knowledge-base/raw/audits/nsg1-retrospective-summary-2026-05-04.json`

## Scope

This retrospective applies NSG-1 to three historical cases:

| Case | Target | Expected |
|---|---|---|
| A | W3-3 S4 Connors-Raschke primary fail / grid-selection trap | FAIL |
| B | W3-2 S2 Turtle confirmation | PASS |
| C | Tier 1 `doji_breakout` confirmation | PASS |

## Data Sources And Limitations

- The current `knowledge-base/raw/bt-results/s4-connors-raschke-2026-05-03.json` is the earlier `INTERVENTION_LIST_MISSING` stub, so the full 27-cell raw grid is not available in the working tree.
- The completed S4 result is recoverable from committed decision `1d0459c` / `.ai/decisions/20260503-2330-w3-3-s4-scenario-c-rejected.md`: primary N=468, Wilson_lo=0.390, PF=1.083, Kelly=0.030, null bootstrap p=0.906, 2024 profit concentration 90.7%, and grid observation `FAIL=9`, `B-marg=12`, `B=6`, `A=0`.
- W3-2 Turtle raw Wave 1 BT report is documented as absent. The subset uses the documented accepted cell stats in `knowledge-base/wiki/learning/s2-turtle-verdict-pre-registration-2026-05-03.md`.
- `doji_breakout` uses real 365d BT cell stats from `knowledge-base/raw/bt-results/bt-365d-2026-04-22.json`. That source has N/WR/EV but not a raw payoff distribution, so Wilson_lo was recomputed from N/WR and Kelly was represented by a conservative EV-consistent proxy.

## Retrospective Verdict Table

| Case | Source basis | median_lift | sign_agreement | variance_cv | A | B | C | Overall | Expected |
|---|---|---:|---:|---:|---|---|---|---|---|
| A: W3-3 S4 | Recovered S4 subset from committed Scenario C decision | 0.995 | 1.000 | 1.785 | PASS | PASS | **FAIL** | **FAIL** | FAIL |
| B: W3-2 Turtle | Documented USDJPY S2 BT stats, reconstructed local neighborhood | 0.986 | 1.000 | 0.025 | PASS | PASS | PASS | **PASS** | PASS |
| C: doji_breakout | 365d BT pair cells, `GBP_USD` primary | 1.041 | 1.000 | 0.141 | PASS | PASS | PASS | **PASS** | PASS |

No threshold sweep was needed because all outcomes matched the expected retrospective verdicts.

## Case A — W3-3 S4 Connors-Raschke

Primary cell: `penetration_tick=10`, `exit_method=50_trailing`, `session_boundary=NY_close_21UTC`.

Documented primary result:

| Metric | Value |
|---|---:|
| N | 468 |
| Wilson_lo | 0.390 |
| PF | 1.083 |
| Kelly | 0.030 |
| Null bootstrap p | 0.906 |
| 2024 profit concentration | 90.7% |

NSG-1 recovered-subset result: **FAIL**, driven by C (`variance_cv=1.785`). This is directionally aligned with the original W3-3 failure mode: the primary cell itself failed the pre-registered matrix, while the wider grid still contained 6 B-tier cells. NSG-1 would force the parameter surface to show stable neighboring Kelly, not just isolated alternate winners.

Limitation: the full 27-cell raw table is not present in the working tree, so this is a recovered subset, not a byte-for-byte rerun of the original grid JSON.

## Case B — W3-2 S2 Turtle

Primary cell: `lookback_days=55`, `pair=USD_JPY`.

Documented source stats:

| Metric | Value |
|---|---:|
| N | 50 |
| PF | 1.99 |
| OOS PF / IS PF | 1.99 / 1.99 |
| Wilson_lo | 0.21 |
| Sharpe | 0.21 |

NSG-1 result: **PASS**. The reconstructed neighborhood preserves the documented stable Turtle profile: median lift stays at 98.6%, all neighbors remain above the low-frequency BEV proxy, and Kelly CV is only 0.025.

## Case C — Tier 1 doji_breakout

Primary cell: `pair=GBP_USD`, from 365d BT entry breakdown.

Input pair cells:

| Pair | N | WR | Recomputed Wilson_lo |
|---|---:|---:|---:|
| EUR_USD | 10 | 90.0% | 0.596 |
| GBP_USD | 20 | 65.0% | 0.433 |
| USD_JPY | 8 | 62.5% | 0.306 |

NSG-1 result: **PASS**. The primary `GBP_USD` cell is not a single spike relative to adjacent pair cells: median lift is 1.041, sign agreement is 1.000 with BEV_WR=0.30, and Kelly CV is 0.141.

## Conclusion

NSG-1 matches the desired retrospective behavior:

- It catches the W3-3 S4 post-hoc grid-selection trap through unstable neighbor Kelly.
- It does not reject the Turtle S2 low-frequency profile when documented neighbors are stable.
- It does not reject the Tier 1 `doji_breakout` pair surface under latest available 365d BT cell stats.
