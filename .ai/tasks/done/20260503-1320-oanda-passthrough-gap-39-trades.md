---
id: 20260503-1320-oanda-passthrough-gap-39-trades
title: Diagnose 39-trade gap between is_shadow=0 (N=68) and oanda_trade_id != '' (N=29)
owner: codex
status: queued
priority: P0
created_at: 2026-05-03T13:20:00+0900
roadmap_gate: Gate 1
rule: R2
---

# Objective

Classify the 39-trade gap between `is_shadow=0` (Render N=68) and `oanda_trade_id != ''` (Render N=29) — both filters intended to identify "Live" post-cutoff trades but giving 2.3× different N. Produce a per-trade classification of which gate / module / failure mode caused each non-OANDA-fill, plus a quant verdict on whether any gate is **systematically suppressing positive-edge trades** (in which case Gate 1 unlock has a structural fix beyond N-accumulation).

# Context

- Aggregate Kelly Decomposition (`knowledge-base/wiki/decisions/aggregate-kelly-decomposition-2026-05-03.md`) verdict: surgical demote impossible at N=29 because Wilson 95% CI [31.4%, 65.6%] straddles BEV_WR (~36%). Edge point estimate -20.02pp is statistically uninformative.
- The Aggregate Kelly gate (v9.0, blocks new OANDA trades when Kelly ≤ 0) plus other gates (MC ruin, spread/SL, Phase0, Q4) collectively form the OANDA pass-through filter.
- Memory `feedback_live_shadow_separation` says `is_shadow=0` is the legacy filter and can drift; `oanda_trade_id IS NOT NULL` (with empty-string exclusion) is the correct definition of "real Live" because empty `oanda_trade_id` means OANDA fill never happened.
- 39-trade gap (Render API 2026-05-03 実測): `is_shadow=0=68`, `oanda_trade_id != ''=29`. **39 trades were tagged Live but never reached OANDA**. This is the structural diagnostic question for Gate 1.
- Three hypothesis categories:
  - **H1 (gate suppression)**: Kelly / MC / spread-SL / Phase0 / Q4 gate fired and blocked send. If gate-suppressed trades systematically include positive-edge trades, the gates themselves are causing the apparent negative edge.
  - **H2 (bridge error)**: OANDA bridge transmission failure (network, auth, race condition, kill-switch). These are operational defects, not edge issues.
  - **H3 (legitimate non-Live)**: trade was correctly tagged shadow at decision time; `is_shadow=0` flag set later by some path-dependent logic. Indicates `is_shadow` field drift bug.
- This is a Rule 2 audit (Gate 1 condition diagnosis on existing data). No production code change. Output is markdown audit + classification table.
- The aggregate Kelly decomposition wrapper (`tools/aggregate_kelly_decomposition_audit.py`) and Render snapshot tool (`tools/render_trades_snapshot.py`) from 2026-05-03 session are reusable. Snapshot DB at `knowledge-base/raw/snapshots/render-demo-trades-20260503.db` already exists.

# Scope

Codex may change:

- `knowledge-base/raw/audits/oanda-passthrough-gap-2026-05-03.md` — create.
- `tools/oanda_passthrough_gap_audit.py` — create as a thin wrapper that reads the Render snapshot DB and the Render `/api/risk/dashboard` filter metadata. Reuse `tools/render_trades_snapshot.py` for fetch logic.
- `.ai/runs/<new-run-dir>/final.md` — run report.

Codex may NOT change:

- live signal logic, OANDA modules, strategy parameters, gate thresholds.
- `app.py`, `modules/oanda_*.py`, `modules/demo_trader.py`.
- `.env`, OANDA credentials, production DBs (write).
- `tools/render_trades_snapshot.py` core logic (use as library; if argparse insufficient, add a thin wrapper).
- `knowledge-base/wiki/**` — KB updates by Claude after review.
- `live_ng_cells` SQLite table.
- Existing uncommitted changes (see Codex Instructions).

# Required Reading

- `CLAUDE.md` (especially the クオンツ判断 section + KB read rules)
- `knowledge-base/wiki/decisions/aggregate-kelly-decomposition-2026-05-03.md`
- `knowledge-base/wiki/syntheses/roadmap-v2.1.md` (Gate 1 conditions)
- `knowledge-base/wiki/lessons/index.md` — at minimum:
  - "`oanda_trade_id IS NOT NULL` で集計する」が正しい live 判定"
  - "Live PnL 集計時は is_shadow=0 を必ず分離。混入で景色が反転"
  - "feedback_check_orphan_local_app — 一次ソースは常に Render API"
- `tools/aggregate_kelly_decomposition_audit.py` (the wrapper from 2026-05-03)
- `tools/render_trades_snapshot.py` (Render → SQLite mirror)
- `app.py` Aggregate Kelly gate location (search for `kelly` and `Kelly<0` to locate the production block)
- `modules/oanda_bridge.py` and `modules/oanda_client.py` — for understanding bridge_status semantics
- `oanda_audit` table definition (see memory `reference_oanda_audit_twin_meaning`: `entry_type` semantics differ by `bridge_status` — `'sent'`=戦略名 / `'filled'`=MODE名)

# Required Decomposition

For each of the 39 gap trades (`is_shadow=0` AND (`oanda_trade_id IS NULL` OR `oanda_trade_id == ''`)), produce a row with:

- `trade_id`, `entry_time`, `entry_type`, `instrument`, `direction`, `confidence`, `regime`
- `pnl_pips` (Live shadow outcome — what would have happened if sent)
- `outcome` (WIN/LOSS)
- `mode`, `gate_group`, `mtf_alignment`, `mtf_gate_action`
- `classification`: one of `H1_GATE_KELLY`, `H1_GATE_MC`, `H1_GATE_SPREAD_SL`, `H1_GATE_PHASE0`, `H1_GATE_Q4`, `H1_GATE_OTHER`, `H2_BRIDGE_ERROR`, `H3_FLAG_DRIFT`, `INDETERMINATE`
- `evidence` — the field/log line that supports the classification (e.g., `close_reason`, `mtf_gate_action`, `oanda_audit.bridge_status`, etc.)

If `oanda_audit` rows exist for these trades (search by trade_id or entry_time), include `bridge_status` and `oanda_audit.entry_type`. Per memory `reference_oanda_audit_twin_meaning`, GROUP BY must separate `bridge_status='sent'` from `bridge_status='filled'`.

# Required Verdict Sections

The audit markdown must include:

1. **Aggregate sanity check**: confirm Render snapshot returns N(`is_shadow=0`)=68 and N(`oanda_trade_id != ''`)=29; if drifted, document.
2. **Classification table**: all 39 rows with the columns above, sorted by `(classification, |pnl_pips|)` descending.
3. **Per-classification summary**: count, mean PnL, win rate, total PnL pip impact.
4. **Edge-suppression test (CRITICAL)**: For H1 categories with N≥10, compute Wilson 95% CI on WR of *gate-suppressed trades* and compare to Wilson 95% CI on WR of *OANDA-filled trades* (N=29). If gate-suppressed Wilson lower > OANDA-filled Wilson upper, the gate is **systematically blocking winners** — flag this as a structural Gate 1 unlock.
5. **Verdict**: one of:
   - `STRUCTURAL_BLOCKER_FOUND` — at least one H1 gate is statistically blocking winners (action: prepare gate-relax pre-registration)
   - `BENIGN_GATING` — gates fire on negative-edge trades correctly (action: focus on N-accumulation via Scalp re-enable)
   - `OPERATIONAL_DEFECT` — H2 dominates (action: bridge-error fix)
   - `FLAG_DRIFT_BUG` — H3 dominates (action: `is_shadow` field write-path audit)
   - `INDETERMINATE` — counts insufficient for classification
6. **Limitations**: data sources, what could not be determined.

# Acceptance Criteria

- [ ] `knowledge-base/raw/audits/oanda-passthrough-gap-2026-05-03.md` exists with all six sections and the 39-row classification table.
- [ ] `tools/oanda_passthrough_gap_audit.py` is deterministic on the snapshot DB.
- [ ] `python3 tools/oanda_passthrough_gap_audit.py --dry-run` exits non-zero if `is_shadow=0` count drifts from 68 by more than ±5 or `oanda_trade_id != ''` count drifts from 29 by more than ±3 (defends against snapshot drift).
- [ ] Edge-suppression test computes Wilson 95% CI for any H1 category with N≥10 and reports whether the bound separates from OANDA-filled CI [31.4%, 65.6%].
- [ ] Verdict is one of the five values above and is justified by the per-classification summary.
- [ ] `.ai/runs/<run-dir>/final.md` includes status, files changed, verdict, top-3 classifications by PnL impact, next recommended task.
- [ ] No write to production DB or `live_ng_cells`. No edits under `knowledge-base/wiki/`. No edits to `app.py` / `modules/`.

# Verification Commands

```bash
# 1. Aggregate sanity (must match Render snapshot)
python3 tools/oanda_passthrough_gap_audit.py --dry-run

# 2. Full audit (writes markdown)
python3 tools/oanda_passthrough_gap_audit.py \
  --db knowledge-base/raw/snapshots/render-demo-trades-20260503.db \
  --output knowledge-base/raw/audits/oanda-passthrough-gap-2026-05-03.md

# 3. Verify snapshot still represents Render (refresh if older than 6h is acceptable)
python3 tools/render_trades_snapshot.py \
  --output knowledge-base/raw/snapshots/render-demo-trades-20260503.db --limit 2000

# 4. Output presence
test -s knowledge-base/raw/audits/oanda-passthrough-gap-2026-05-03.md
```

If Codex sandbox blocks Render fetch, reuse the existing snapshot at `knowledge-base/raw/snapshots/render-demo-trades-20260503.db` (created 2026-05-03). Document staleness if applicable.

# Codex Instructions

Work in this repository. Respect existing uncommitted changes — do not touch `modules/demo_trader.py`, `knowledge-base/raw/hunt_events/2026-05-02.jsonl`, `knowledge-base/wiki/sessions/2026-05-03-session.md`, untracked `raw/audits/cell_edge_audit_*` files, or `knowledge-base/raw/cell_deepdive/`. The new `tools/render_trades_snapshot.py`, `tools/aggregate_kelly_decomposition_audit.py`, and snapshot DB at `knowledge-base/raw/snapshots/render-demo-trades-20260503.db` are read-only context for this task.

This is a Rule 2 read-only audit. Do not:

- modify any gate logic, even if data shows H1 suppression
- write to production DB or `oanda_audit` table
- send anything to OANDA
- edit `knowledge-base/wiki/**`
- modify `app.py`, `modules/`, or any strategy file

If sample size per H1 category is too small for Wilson CI separation (N<10 in every category), report `INDETERMINATE` and stop. Do not invent classifications. Do not propose gate parameter changes — that's a separate Rule 1 task that requires this audit's verdict first.

In the final report, include status, files changed, verdict, per-classification PnL summary, the H1 category with the largest absolute PnL impact, remaining risks, and the next recommended task (likely either: gate-relax pre-registration if STRUCTURAL_BLOCKER, Scalp re-enable Rule 1 if BENIGN_GATING, bridge-fix Rule 2 if OPERATIONAL_DEFECT, or shadow-flag write-path audit if FLAG_DRIFT_BUG).
