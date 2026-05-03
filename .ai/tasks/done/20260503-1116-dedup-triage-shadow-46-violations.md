---
id: 20260503-1116-dedup-triage-shadow-46-violations
title: Triage 46 unflagged shadow per-bar dedup violations — historical vs active classification
owner: codex
status: queued
priority: P0
created_at: 2026-05-03T11:16:00+0900
roadmap_gate: Gate 0
rule: R3
---

# Objective

Classify the 46 unflagged per-bar dedup violations surfaced by `tools/per_bar_dedup_audit.py` (run `20260503-111131-...0237-gate0-production-safety-audit/final.md`) into **historical-only** (pre-fix legacy duplicates) vs **active gap** (current per-bar dedup gate still missing for some strategy/TF) categories. Output a markdown triage report and an explicit "active gap" list; do **not** modify dedup logic in this task.

# Context

- The Gate 0 audit `tools/per_bar_dedup_audit.py --json` (executed 2026-05-03 11:11) reports `total_violations=46, flagged_dedup_violation=0, violations_with_oanda_fill=0`. All 46 are `is_shadow=1` (Live OANDA fills not affected).
- 22 strategy×pair combos affected, spanning TF 1m / 5m / 15m. Window sizes are TF-aware (1m=60s, 5m=300s, 15m=900s) per memory observation #943 and lesson `wiki/lessons/lesson-per-bar-dedup-tf-aware-2026-05-03.md`.
- Top combos by N (from JSON output of the Gate 0 audit run):
  - `fib_reversal/USD_JPY` n=9 tf=1m pnl=+137.7p
  - `vol_spike_mr/USD_JPY` n=4 tf=15m pnl=-9.3p
  - `sr_break_retest/USD_JPY` n=3 tf=15m pnl=-144.9p
  - `dt_bb_rsi_mr/GBP_USD` n=3 tf=15m pnl=+71.8p
  - `sr_fib_confluence/USD_JPY` n=3 tf=15m pnl=+30.5p
  - others: 1-2 each across `vol_surge_detector`, `ema_trend_scalp`, `engulfing_bb`, `dt_sr_channel_reversal`, `session_time_bias`, `ema200_trend_reversal`, `doji_breakout`, `post_news_vol`, `sr_fib_confluence/GBP_USD`, `intraday_seasonality`, `sr_fib_confluence/GBP_JPY`, `dt_fib_reversal/EUR_JPY`, `vol_surge_detector/GBP_USD`, `ema_cross/GBP_USD`, `sr_break_retest/GBP_JPY`, `ema200_trend_reversal/GBP_USD`, `stoch_trend_pullback/USD_JPY`, `intraday_seasonality/GBP_USD`.
- This affects shadow→Live promotion math: shadow PnL/N for promotion-candidate combos may be inflated by undeduplicated bars, biasing Wilson lower bound and EV estimation.
- Specifically these are **promotion-relevant** if they appear in PAIR_PROMOTED / ELITE_LIVE: `session_time_bias/GBP_USD` (ELITE), `doji_breakout/USD_JPY` (PAIR_PROMOTED), `post_news_vol/USD_JPY` (FORCE_DEMOTED but tier-master B-1), `ema200_trend_reversal/GBP_USD` (PAIR_PROMOTED USD_JPY only — GBP_USD is shadow). Confirm by reading `knowledge-base/wiki/tier-master.md`.
- Rule 3: read-only forensic audit. No code changes to dedup logic.

# Scope

Codex may change:

- `knowledge-base/raw/audits/dedup-violation-triage-2026-05-03.md` — create.
- `tools/dedup_violation_triage.py` — create as a thin classifier that consumes `per_bar_dedup_audit.py --json` output (subprocess) and emits per-violation records: `(strategy, pair, tf, ts, signal_price, action, exit_status, pnl, classification)`.
- `.ai/runs/<new-run-dir>/final.md` — run report.

Codex may NOT change:

- `app.py` per-bar dedup gate or any strategy logic.
- `tools/per_bar_dedup_audit.py` (use as-is — call it as a subprocess or import as a library).
- `modules/demo_db.py` schema or `dedup_violation` table contents (read-only fine).
- `.env`, OANDA credentials, production DBs (write).
- `knowledge-base/wiki/**` — KB updates by Claude after review.
- `live_ng_cells` SQLite table (read-only fine).
- Existing uncommitted changes (see Codex Instructions).

# Required Reading

- `CLAUDE.md`
- `knowledge-base/wiki/lessons/lesson-per-bar-dedup-tf-aware-2026-05-03.md`
- `knowledge-base/wiki/tier-master.md` — to identify promotion-relevant combos.
- `tools/per_bar_dedup_audit.py` (top-level docstring + main flow).
- `.ai/runs/20260503-111131-20260503-0237-gate0-production-safety-audit/final.md` — original finding.

# Classification Rules

For each violation row produced by `per_bar_dedup_audit.py`, assign one of:

1. `HISTORICAL_LEGACY` — entry timestamp is **before** the per-bar dedup TF-awareness fix landing date. Use the date range from the lesson page; if uncertain, use commit date of the lesson file as the cutoff.
2. `ACTIVE_GAP_PROBABLE` — entry timestamp is **after** the cutoff, AND the strategy is currently registered (search `app.py` `QUALIFIED_TYPES` and `modules/demo_trader.py` strategy registry — read-only). These suggest an active gate gap.
3. `INDETERMINATE` — entry timestamp is after cutoff but strategy is FORCE_DEMOTED or unregistered (no current production firing). Lower priority but still recorded.

# Acceptance Criteria

- [ ] `knowledge-base/raw/audits/dedup-violation-triage-2026-05-03.md` exists with:
  - Summary table: counts of HISTORICAL_LEGACY / ACTIVE_GAP_PROBABLE / INDETERMINATE.
  - Per-combo table sorted by `(classification, |pnl|)` descending.
  - **ACTIVE_GAP list**: every combo with ≥1 ACTIVE_GAP_PROBABLE row, with strategy/pair/TF and the count, formatted so it can be fed verbatim to a follow-up gate-fix task.
  - **Promotion-impact section**: combos that intersect PAIR_PROMOTED or ELITE_LIVE in `tier-master.md` get a separate flag, with a note on how much of their shadow PnL is duplicated.
  - **Cutoff-date sensitivity**: re-run classification with cutoff ±3 days; report whether the ACTIVE_GAP count changes. If it does, the result is brittle — say so.
- [ ] `tools/dedup_violation_triage.py --json` produces deterministic output on a fixed snapshot.
- [ ] `python3 tools/dedup_violation_triage.py --dry-run` prints the summary counts and exits non-zero if `total != 46` or `live_count != 0` (defends against drift in the underlying audit).
- [ ] `.ai/runs/<new-run-dir>/final.md` contains: status, files changed, summary counts (HIST / ACTIVE / INDET), top 3 ACTIVE_GAP combos, promotion-impact verdict, remaining risks, next recommended task.
- [ ] No edits to `app.py`, `modules/`, `tools/per_bar_dedup_audit.py`, `knowledge-base/wiki/`, `.env`, or any production DB.

# Verification Commands

```bash
# 1. Refresh the dedup audit (must match findings in the report)
python3 tools/per_bar_dedup_audit.py --json | python3 -c "import sys,json; d=json.load(sys.stdin); print('total=', d['summary']['total_violations'], 'live=', d['summary']['violations_with_oanda_fill'])"

# 2. Run the classifier dry-run (must exit 0)
python3 tools/dedup_violation_triage.py --dry-run

# 3. Generate the triage markdown
python3 tools/dedup_violation_triage.py --output knowledge-base/raw/audits/dedup-violation-triage-2026-05-03.md

# 4. File presence
test -s knowledge-base/raw/audits/dedup-violation-triage-2026-05-03.md
```

# Codex Instructions

Work in this repository. Respect existing uncommitted changes — do not touch `modules/demo_trader.py`, `knowledge-base/raw/hunt_events/2026-05-02.jsonl`, `knowledge-base/wiki/sessions/2026-05-03-session.md`, `tests/test_pyramiding_kill_switch.py`, or untracked `raw/audits/cell_edge_audit_2026-05-02_v1_365d_inclshadow.{json,md}` and `knowledge-base/raw/cell_deepdive/`.

This is a read-only forensic task. Do not:

- modify per-bar dedup gate logic, even if you believe ACTIVE_GAP rows justify it
- write to `dedup_violation` table or any production DB
- send anything to OANDA
- edit `knowledge-base/wiki/**`
- modify `tools/per_bar_dedup_audit.py`

If the data shows zero ACTIVE_GAP rows (all 46 are HISTORICAL_LEGACY), report that and stop — the shadow stats only need a one-time backfill, not a gate fix. If ≥1 ACTIVE_GAP row exists, list them precisely so the next task can wire the missing TF-aware gate for exactly those strategy×TF combos.

In the final report, include status, files changed, summary counts, top 3 ACTIVE_GAP combos with rationale, promotion-impact verdict (does any ELITE_LIVE / PAIR_PROMOTED combo get its Wilson_lo_95 shifted by deduplication?), remaining risks, and next recommended task (likely either: per-bar dedup backfill of `dedup_violation` table for HISTORICAL rows, or a narrow per-strategy gate fix for ACTIVE rows).
