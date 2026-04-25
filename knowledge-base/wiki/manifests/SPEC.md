# EDGE.md Manifest Specification (v0.1)

Inspired by [DESIGN.md](https://github.com/google-labs-code/design.md). Defines
a manifest format for `(strategy, cell)` routing in FX AI Trader.

## Purpose

Single source of truth for cell-aware routing. A strategy × cell3d combination
gets a `status` (statistical verdict), a `routing` (production action), and a
`source_*` link back to the pre-registration and result that authorized it.

## File Structure

YAML front matter + Markdown prose. The YAML is normative.

```markdown
---
version: "0.1"
classifier: "v6"
classifier_source: "[[phase4c-v6-classifier-stability-result-2026-04-24]]"
edges_updated_at: "2026-04-26T00:00:00Z"
edges:
  - strategy: <string>
    cell: <string>            # cell3d format e.g. R2_trend_down__V_high__NY
    status: <Status>
    n: <int>
    wr: <float>               # 0..1
    bev_wr: <float>           # 0..1
    fisher_p: <float>
    kelly: <float>            # may be negative
    bonferroni_passed: <bool>
    routing: <Routing>
    routing_lot_multiplier: <float>  # optional, only with KELLY_HALF/FULL
    source_prereg: "[[wikilink]]"
    source_result: "[[wikilink]]"
    expires_at: "<ISO8601>"
---

## Overview
... prose ...
```

## Token Types

### Status

| value | meaning | required conditions |
|---|---|---|
| `SURVIVOR` | positive edge, Bonferroni passed | N≥30, Wilson_lo>BEV+0.03, Fisher<α_cell, Kelly>0.05, WF same-sign |
| `CANDIDATE` | provisional positive | N≥30, Wilson_lo>BEV+0.03, Kelly>0.05 |
| `REJECT` | negative edge, Bonferroni passed | N≥30, Wilson_hi<BEV-0.03, Fisher<α_cell, Kelly<-0.05 |
| `REJECT_CANDIDATE` | direction negative, Bonferroni not passed | N≥10, WR<BEV |

### Routing

| value | runtime effect |
|---|---|
| `NONE` | informational only — no production effect |
| `BLOCK` | `_is_promoted()` returns False (OANDA send blocked, demo continues) |
| `KELLY_HALF` | OANDA send allowed, lot × 0.5 |
| `KELLY_FULL` | OANDA send allowed, lot × full Kelly |

### Cell

`{regime}__{vol_bucket}__{session}` per v6 classifier. See
[[phase4c-v6-classifier-stability-result-2026-04-24]] for the 72 nominal cells.

## Linting Rules

| Rule | Severity | Check |
|---|---|---|
| `E1 broken-source` | error | `source_prereg` / `source_result` wikilink does not resolve to a file in `knowledge-base/wiki/analyses/` |
| `E2 expired` | error | `expires_at < now` |
| `E3 routing-status-mismatch` | error | `routing=BLOCK` but `status != REJECT`; or `routing=KELLY_*` but `status != SURVIVOR`; or `status in {SURVIVOR,REJECT}` but `bonferroni_passed != true` |
| `E4 cell-validity` | error | `cell` is not in the v6 enumerated set (regime ∈ R0..R6, vol ∈ V_low/V_mid/V_high, session ∈ Asia/London/NY/Off, joined by `__`) |
| `E5 strategy-validity` | error | `strategy` is not in `_FORCE_DEMOTED ∪ QUALIFIED_TYPES` parsed from `modules/demo_trader.py` |
| `W1 stale` | warning | `edges_updated_at` older than 30 days |
| `W2 source-divergence` | warning | numeric fields (`n`, `wr`, `kelly`, `fisher_p`) not present in or different from `source_result` (best-effort scan) |

## Section Order

| # | Section | Required |
|---|---|---|
| 1 | Overview | yes |
| 2 | Routing values | yes |
| 3 | Status | yes |
| 4 | Why cell × strategy | optional |
| 5 | Operational notes | optional |

## Consumer Behavior

| scenario | behavior |
|---|---|
| Unknown YAML key under `edges[]` | preserve, warn |
| Duplicate `(strategy, cell)` pair | error |
| `routing: BLOCK` with `bonferroni_passed: false` | error E3 |
| Empty `edges: []` | accept (initial state) |

## CLI

```bash
# Validate
python3 tools/edge_md_lint.py --check knowledge-base/wiki/manifests/EDGE.md

# Export to runtime
python3 tools/edge_md_export.py knowledge-base/wiki/manifests/EDGE.md \
    > modules/routing_table.json
```

## Integration Points

- `modules/cell_routing.py` — runtime loader (60s cache)
- `modules/demo_trader.py::_is_promoted()` — calls `get_routing()` for BLOCK
- `tools/tier_integrity_check.py` — peer linter (does not validate EDGE.md;
  EDGE.md has its own linter)

## Versioning

`version` follows semver-ish. v0.1 is alpha. Breaking changes bump major.
