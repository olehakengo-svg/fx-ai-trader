---
id: 20260503-1118-aggregate-kelly-decomposition
title: Decompose post-cutoff Live aggregate Kelly = 0 to find EV-destroying cells
owner: codex
status: queued
priority: P1
created_at: 2026-05-03T11:18:00+0900
roadmap_gate: Gate 1
rule: R2
---

# Objective

Produce a single audit report at `knowledge-base/raw/audits/aggregate-kelly-decomposition-2026-05-03.md` that decomposes the post-cutoff Live trade set (N=286, WR=38.11%, EV=-0.80, aggregate Kelly=0.0) into strategy × pair × session × regime cells, ranks cells by absolute PnL damage, and produces an R2-actionable demote list of cells whose Wilson-upper WR < BEV_WR by ≥ 5pp **and** N ≥ 8. The demote list must be small and surgical, not a blanket ban.

# Context

- Roadmap Gate 1 requires `Aggregate Kelly > 0` to unlock DD 0.2x → 0.3x. Current aggregate Kelly = 0.0 with edge ≈ -18.04% on N=286 post-cutoff Live trades (snapshot 2026-04-29 per `knowledge-base/wiki/index.md` System State block).
- The aggregate number is uninterpretable on its own. Lessons: "集計値は必ずセグメント分解する。平均値は嘘をつく" and "Aggregate label × WR だけでなく category × label × WR の 2D を常に見る".
- Prior audit `knowledge-base/raw/audits/2026-04-13-ev-decomposition.md` is the format precedent (3-week-old data, N=294). This task refreshes with N=286 and adds Wilson lower bounds + Bonferroni-corrected significance.
- Live filter: `oanda_trade_id IS NOT NULL` per lesson "`oanda_trade_id IS NOT NULL` で集計する」が正しい live 判定". Do NOT use `is_shadow=0` as the sole filter — those columns can drift (the gate0 production-safety task already audited that and the dedup-triage task `20260503-1116-...` confirmed all 46 dedup violations are shadow-only, so Live PnL is not duplicate-polluted).
- Per-pair friction (`knowledge-base/wiki/analyses/friction-analysis.md`): USD_JPY BEV_WR=34.4%, EUR_USD=39.7%, GBP_USD=37.9%, EUR_JPY=33.7%.
- Existing tooling Codex should reuse:
  - `tools/cell_edge_audit.py` (cell aggregation, supports `--shadow-only`)
  - `tools/cell_negative_edge_audit.py` (Wilson upper bound NG list, persists to `live_ng_cells`)
  - `tools/kelly_recompute_trigger.py` (Kelly aggregation logic)
  - `research/edge_discovery/power_analysis.py` (Wilson interval functions)
- Rule 2 audit. No strategy code or live behavior change. Output is the markdown audit + demote candidate list; demote actions are a separate next task.

# Scope

Codex may change:

- `knowledge-base/raw/audits/aggregate-kelly-decomposition-2026-05-03.md` — create.
- `tools/aggregate_kelly_decomposition_audit.py` — create as a thin wrapper that reuses `cell_edge_audit.py` + `cell_negative_edge_audit.py`. Do not duplicate logic.
- `.ai/runs/<new-run-dir>/final.md` — run report.

Codex may NOT change:

- live signal logic, OANDA modules, strategy parameters
- `.env`, OANDA keys, production DBs (write)
- `tools/cell_edge_audit.py` or `tools/cell_negative_edge_audit.py` core logic (use as libraries)
- `knowledge-base/wiki/index.md` — KB index updates by Claude after review
- `live_ng_cells` SQLite table (read-only allowed; write deferred to demote-action task)

# Required Reading

- `CLAUDE.md` (especially クオンツ判断 + KB read rules)
- `knowledge-base/wiki/syntheses/roadmap-v2.1.md`
- `knowledge-base/wiki/analyses/friction-analysis.md` (BEV_WR per pair)
- `knowledge-base/wiki/analyses/bt-live-divergence.md` (6 structural optimism biases)
- `knowledge-base/raw/audits/2026-04-13-ev-decomposition.md` (output format precedent)
- `knowledge-base/wiki/lessons/index.md` — at minimum:
  - "集計値は必ずセグメント分解する"
  - "ペア×戦略の粒度で評価しないと相殺される"
  - "促進判定 (Kelly)も逆校正判定 (Bonferroni) も同じ統計厳格さで行う"
  - "止血判定は EV 軸で行う。WR は補助指標"
- `tools/cell_edge_audit.py` and `tools/cell_negative_edge_audit.py`

# Data Source

- Render-mirrored local DB at the project default path (the same path `cell_edge_audit.py` opens). Do NOT hit Render API.
- Live filter: `outcome IN ('WIN','LOSS') AND oanda_trade_id IS NOT NULL`.
- Time filter: `entry_time >= '2026-04-08'` (post-cutoff). Confirm cutoff via `knowledge-base/wiki/changelog.md`; if it differs, use the changelog value and document the discrepancy.
- Pair filter: exclude `XAU_USD` and `EUR_GBP`.

# Required Decomposition Axes

For each axis, table sorted by |PnL| descending. Include only cells with N ≥ 5.

1. **Pair** (5 cells): USD_JPY, EUR_USD, GBP_USD, EUR_JPY, GBP_JPY.
2. **Strategy × Pair** (2D): every combination present.
3. **Session** (Tokyo / London / NY / overlap_LN / Asia_early / Sydney) — UTC hour mapping per `app.py::_bt_classify_session` (`app.py:4786`).
4. **MTF Regime label** (regime engine output: bull / bear / range / mixed / unknown).

Per-cell columns: `N | wins | losses | WR | Wilson_lo_95 | Wilson_up_95 | EV_pip | PnL_pip | PF | BEV_WR | gap_to_BEV_pp | flag`.

`flag` values:
- `DEMOTE` if N ≥ 8 and Wilson_up_95 < (BEV_WR + 5pp).
- `WATCH` if N ≥ 5 and EV_pip < 0 but does not meet DEMOTE.
- `OK` otherwise.

Final section must include:

- **Aggregate sanity check**: N, WR, EV, PnL, Kelly recomputed locally — must match the System State block within rounding (or document discrepancy).
- **Top 5 PnL-destroyer cells** with their decomposition.
- **DEMOTE list**: every cell flagged DEMOTE, formatted for the next demote-action task verbatim. Include Bonferroni-adjusted p-value of `(WR < BEV_WR)` using one-sided binomial, α corrected by total cells across all four axes.
- **Sensitivity check**: re-run aggregate Kelly with DEMOTE cells excluded. Report what aggregate Kelly would be. If not "Kelly > 0", say so loudly.
- **Limitations**: cells with N < 8 → WATCH list, not DEMOTE.

# Acceptance Criteria

- [ ] `knowledge-base/raw/audits/aggregate-kelly-decomposition-2026-05-03.md` exists with all four axis tables, aggregate sanity check, top-5 destroyers, DEMOTE list, sensitivity recompute, limitations.
- [ ] `tools/aggregate_kelly_decomposition_audit.py` exists and is deterministic on a fixed snapshot.
- [ ] `python3 tools/aggregate_kelly_decomposition_audit.py --dry-run` prints aggregate sanity-check numbers and exits non-zero if they don't match System State within ±0.5pp / ±0.5pp%.
- [ ] No write to `live_ng_cells` or any production DB.
- [ ] No edits under `knowledge-base/wiki/`.
- [ ] Run report under `.ai/runs/` with: status, files changed, aggregate sanity-check pass/fail, count of DEMOTE cells, hypothetical aggregate Kelly after demote, remaining risks, next recommended task.

# Verification Commands

```bash
python3 tools/aggregate_kelly_decomposition_audit.py --dry-run

python3 tools/aggregate_kelly_decomposition_audit.py --window post-cutoff --output knowledge-base/raw/audits/aggregate-kelly-decomposition-2026-05-03.md

python3 tools/cell_edge_audit.py --help
python3 tools/cell_negative_edge_audit.py --help

test -s knowledge-base/raw/audits/aggregate-kelly-decomposition-2026-05-03.md
```

# Codex Instructions

Work in this repository. Respect existing uncommitted changes — do not touch `modules/demo_trader.py`, `knowledge-base/raw/hunt_events/2026-05-02.jsonl`, `knowledge-base/wiki/sessions/2026-05-03-session.md`, `tests/test_pyramiding_kill_switch.py`, untracked `raw/audits/cell_edge_audit_*` files, or `knowledge-base/raw/cell_deepdive/`.

Read-only audit. Do not:

- write to production DB or `live_ng_cells`
- send anything to OANDA
- edit `knowledge-base/wiki/**`
- demote any strategy or change any flag

If aggregate Kelly is broken across many cells (no surgical demote restores Kelly > 0), report that and stop. Do not invent new strategies, propose parameter tweaks, or modify gate logic. Demoting cells is a separate decision requiring this audit's evidence first.

In the final report: status, files changed, aggregate sanity-check pass/fail with numbers, counts of DEMOTE/WATCH/OK, hypothetical aggregate Kelly after applying DEMOTE, top blocker for Gate 1 unlock, remaining risks, next recommended task (likely either: execute the demote list as Rule 2, or run a portfolio-level review if bleeding is too broad to fix surgically).
