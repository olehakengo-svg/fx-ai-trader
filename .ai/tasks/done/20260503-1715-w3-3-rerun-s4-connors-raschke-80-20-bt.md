---
id: 20260503-1715-w3-3-rerun-s4-connors-raschke-80-20-bt
title: W3-3-rerun — S4 Connors-Raschke 80-20 (USDJPY M5) BT — fx-ai-trader scope, cached data, post-hoc validity (Rule 1)
owner: codex
status: queued
priority: P1
created_at: 2026-05-03T17:15:00+0900
roadmap_gate: Wave 3 Tier 2 — 新規 alpha source 補充 (1/3 並列)
rule: R1
supersedes: .ai/tasks/failed/20260503-1640-w3-3-s4-connors-raschke-80-20-bt.md
prereq_artifacts:
  - data/cache/massive/USD_JPY_5m_2014_2026.parquet  # Claude (Massive MCP) で fetch 済み 2026-05-03 17:08。903,828 bars, 2014-01-02..2026-04-30
  - data/cache/massive/USD_JPY_5m_2014_2026.audit.json
---

# Objective

Pre-registered Backtest of S4 — Connors & Raschke "80-20" — on USDJPY M5 over 2014-01-02..2026-04-30 (~12.3 years), producing:

1. A 27-cell sensitivity grid (penetration tick × exit method × session boundary, 3×3×3) with **all 5 self-contained quant axes per cell**: N / Wilson_lo / PF / OOS-IS PF / Bonferroni p (m=27). Sharpe, Kelly, max DD also reported per cell.
2. A null-bootstrap (1000 shuffles) significance test for the **pre-registered primary cell** `(10 tick, 50% trailing, NY close)`.
3. A primary-cell deep dive (12.3y annual cohort table, walk-forward 50/50 IS/OOS).
4. **Post-hoc deferral markers** for fib_reversal LIVE correlation (Validity #2) and yfinance broker cross-check (Validity #4) — Codex emits the **inputs** Claude will need (signal list with timestamps, daily PnL series), but does NOT compute correlation or yfinance fetch (Codex sandbox has no network).
5. A Scenario A-pending / B / C verdict against the verdict matrix v1; if A-pending, the report explicitly states "post-hoc Validity #2 + #4 must clear before LOCK".

This is **Rule 1 Slow & Strict**. Thresholds and Bonferroni m=27 are pre-registered below and **must be encoded as constants in the BT script before BT runs**.

# Context — Why this is a rerun

- Initial run `task-mopgysld-71znyk` (2026-05-03 16:48) was BLOCKED_BY_SANDBOX_WRITE_SCOPE: original task spec required writes to `/Users/jg-n-012/test/tools/bt/` and `wiki/learning/`, outside the Codex sandbox. Decision: `.ai/decisions/20260503-1648-w3-3-s4-changes-requested.md`.
- Resolved by relocating all outputs under `fx-ai-trader/` (matches W3-4/W3-5 convention).
- Data unavailability also blocked initial run (~6 months of M5 cache only). Resolved by Claude (Massive MCP host) pre-fetching the full 2014-01-01..2026-04-30 M5 cache via `tools/data_prep/fetch_usdjpy_m5_2014_2026.py`. Cache **now exists** at `data/cache/massive/USD_JPY_5m_2014_2026.parquet` (903,828 bars, 21.3 MB).
- LIVE/yfinance unavailability resolved by **post-hoc validity split**: Codex emits the inputs, Claude post-processes off-sandbox.

# Strategy specification (PRE-REGISTERED, do not modify)

## Setup (previous-day daily candle structure)

Compute previous trading day daily OHLC from the M5 parquet (resample to D1, UTC day boundaries). A trading day = any UTC date with ≥ 1 M5 bar present.

- `prev_range = prev_high - prev_low`
- `open_pct  = (prev_open  - prev_low) / prev_range`
- `close_pct = (prev_close - prev_low) / prev_range`
- **Bearish setup**: `open_pct >= 0.80 AND close_pct <= 0.20` (open in top 20%, close in bottom 80% — i.e. open near top, close near bottom)
- **Bullish setup**: `open_pct <= 0.20 AND close_pct >= 0.80`

(Note: a "close in bottom 80%" reading is symmetric to "close in lower portion of range". The Connors-Raschke literal phrasing is: open within the top 20% AND close within the bottom 80% — meaning the bar opened high then sold off heavily. This script encodes that literal directional setup.)

## Entry (next trading day, intraday on M5)

For each setup-day's next trading day:

- **Bearish setup → SHORT entry**: scan M5 bars in chronological order. The first bar whose **low** crosses below `prev_low - penetration_tick * 0.001` arms the trigger. The next bar whose **close** is at or above `prev_low` fires the SHORT (entry price = that bar's close). One trade per day max.
- **Bullish setup → LONG entry**: symmetric (penetrate above prev_high then close back below) → LONG.
- If the trigger never fires within the day (defined by `session_boundary`), no trade.

## Exit

- **Stop loss**: setup candle's opposite extreme ± 5 pip (= ± 0.050). For SHORT: stop = setup_high + 0.050. For LONG: stop = setup_low - 0.050. Static.
- **Profit target / time stop** depends on `exit_method`:
  - `50% trailing`: trail by `0.5 * prev_range` from current best price (best=lowest for SHORT, highest for LONG). When price reverses by that amount from best, exit at the bar close.
  - `100% trailing`: trail by `1.0 * prev_range` (more permissive).
  - `fixed-time`: no trailing — exit at session-end close (defined by `session_boundary`).
- **Hard time stop**: when the day's `session_boundary` cutoff is reached, force-close at that bar's close.

## Filters / regime exclusions (no others)

- **Intervention zone OFF**: when **prev_close > 158.000** (USDJPY), strategy is gated OFF for that next day.
- **Intervention dates excluded**: a literal date list. If the catalog `/Users/jg-n-012/test/wiki/learning/global-retail-fx-edges-2026-05-03.md` has a definitive 8-event list, use it; if not, fail loudly with `INTERVENTION_LIST_MISSING` and abort. Do not improvise dates.
- **No HMM gate. No MA gate. No ATR gate. No additional session-time filter** beyond the 3 boundary cells. Adding filters mid-task = pre-reg violation.

# Sensitivity grid (Bonferroni m=27, PRE-REGISTERED)

| Axis | Levels |
|---|---|
| `penetration_tick` | 5 / 10 / 15 (tick = 0.001) |
| `exit_method` | `50_trailing` / `100_trailing` / `fixed_time` |
| `session_boundary` | `NY_close_21UTC` / `London_close_16UTC` / `H24` |

Total cells = **27**. Pre-registered primary = `(10, 50_trailing, NY_close_21UTC)`.

Bonferroni denominator m = **27** (locked). α = 0.05.

# Verdict matrix v1 — axes per cell

For every cell (and especially primary), report:

| Axis | Threshold tier (B-marg / B / A) |
|---|---|
| 1. N (executed trades) | ≥50 / ≥100 / ≥200 |
| 2. Wilson 95% lo (WR) | >0.40 / >0.42 / >0.45 |
| 3. PF | >1.0 / >1.2 / >1.5 |
| 4. OOS PF / IS PF (50/50 walk-forward, time-ordered) | >0.4 / >0.6 / >0.8 |
| 5. Bonferroni-adjusted p (m=27, one-sided WR > BEV_WR=34.4%) | <0.20 / <0.10 / <0.01 |
| 6. Sharpe (annualized, daily PnL) | >0.0 / >0.5 / >1.0 |
| 7. Kelly fraction | >0 / >0.05 / >0.10 |

A cell qualifies for a tier only if **all 7 axes** clear that tier's threshold.

Per-cell verdict: `B-marg / B / A / FAIL`.

# Scenario verdict logic (with post-hoc deferral)

Codex emits a **provisional** Scenario verdict; final A requires Claude post-hoc validity:

- **Scenario A-pending**: primary cell ≥ B AND null bootstrap p < 0.05 AND no time-cohort violation.
  - Codex output: "A-pending — post-hoc Validity #2 (fib_reversal LIVE corr) + #4 (yfinance cross-check) required for final LOCK".
  - Codex MUST NOT write `pre-registration.md` itself; Claude writes it after post-hoc clears.
- **Scenario B**: primary cell == B-marginal OR cohort concentration warning.
  - hold; recommend Wave 4 grid expansion.
- **Scenario C**: primary cell FAIL OR null bootstrap p ≥ 0.05.
  - Reject; recommend catalog §B-2 → "academic only".

If results land between, default stricter (A→B→C) and document why.

# Validity checks split

## Codex-side (executable now, cache only)

1. **Null bootstrap (primary cell)**: shuffle setup labels (bullish / bearish / none) randomly across all setup-eligible days × 1000 iterations. For each shuffle, recompute primary-cell PF. Report empirical PF percentile, 2-sided p, distribution mean/median.
2. **Time-cohort integrity**: annual PnL by year (2014..2026), monthly PnL heatmap, regime concentration check (no single year > 50% of total PnL — flag if violated, ref `feedback_cohort_time_check`).
3. **Spread sanity (BEV adherence)**: confirm BEV_WR_USDJPY=34.4% from `wiki/analyses/friction-analysis.md` (read-only) and use it as the null WR for axis 5.

## Claude-side post-hoc (Codex emits inputs)

Codex MUST emit (alongside the BT report) two artifacts that let Claude do post-hoc validity later:

4. `knowledge-base/raw/bt-results/s4-primary-trade-list-2026-05-03.parquet` — primary-cell trades with columns: `entry_ts_utc`, `exit_ts_utc`, `direction`, `pnl_pip`, `pnl_pct`, `holding_minutes`, `setup_day_utc`. Used by Claude for fib_reversal correlation (Validity #2) and yfinance cross-check (Validity #4).
5. `knowledge-base/raw/bt-results/s4-primary-daily-pnl-2026-05-03.parquet` — daily aggregated PnL series for the 12.3y window, indexed by UTC date.

Codex **does not** call Render API, does not call yfinance, does not call pgrep. Markers in the BT report make clear these are deferred to Claude.

# Data

- **Source (REQUIRED)**: `data/cache/massive/USD_JPY_5m_2014_2026.parquet` (already populated by `tools/data_prep/fetch_usdjpy_m5_2014_2026.py`, audit JSON sibling).
- **Verify on first read**: row count ≥ 900,000, min ts ≤ 2014-01-31 UTC, max ts ≥ 2026-04-29 UTC. If not, abort with `CACHE_INSUFFICIENT` and request re-prep.
- Do not call Massive API. Do not call any external API.

# Scope

Codex MAY change:

- `tools/bt/s4_connors_raschke.py` (NEW) — BT script. Pre-reg constants at module top.
- `tools/bt/s4_validity_inputs.py` (NEW, optional helper) — exports trade-list and daily-PnL parquets used by Claude post-hoc validity.
- `tests/test_s4_connors_raschke.py` (NEW) — unit tests for setup detection, entry trigger, exit logic, Bonferroni application, walk-forward split.
- `knowledge-base/wiki/learning/s4-connors-raschke-bt-2026-05-03.md` (NEW) — readable BT report.
- `knowledge-base/raw/bt-results/s4-connors-raschke-2026-05-03.json` — raw 27-cell results + null-bootstrap distribution.
- `knowledge-base/raw/bt-results/s4-connors-raschke-2026-05-03.md` — readable raw summary.
- `knowledge-base/raw/bt-results/s4-primary-trade-list-2026-05-03.parquet` (NEW) — Claude post-hoc input.
- `knowledge-base/raw/bt-results/s4-primary-daily-pnl-2026-05-03.parquet` (NEW) — Claude post-hoc input.
- `.ai/runs/<new-run-dir>/final.md`.

Codex MUST NOT change:

- `data/cache/massive/USD_JPY_5m_2014_2026.parquet` and its `.audit.json` — read-only Phase 0 artifact.
- `tools/data_prep/fetch_usdjpy_m5_2014_2026.py` — Phase 0 fetch script (Claude side).
- `app.py`, `modules/`, `strategies/`, `live_ng_cells` table, Render API, OANDA endpoints, `.env`, production DB.
- `knowledge-base/wiki/decisions/`, `wiki/index.md`, `wiki/strategies/`, `wiki/tier-master.md`.
- `knowledge-base/wiki/learning/global-retail-fx-edges-2026-05-03.md` (catalog — Claude updates after review).
- `knowledge-base/wiki/learning/verdict-threshold-matrix-v1-2026-05-03.md` (matrix v1).
- The W3-2 / W3-1 / Wave-1 reports.
- Existing uncommitted changes outside this task's scope.
- `pre-registration.md` for this strategy — Claude writes it post-hoc if A clears.

# Required Reading

- `/Users/jg-n-012/test/wiki/learning/global-retail-fx-edges-2026-05-03.md` (catalog §B-2)
- `/Users/jg-n-012/test/wiki/learning/verdict-threshold-matrix-v1-2026-05-03.md`
- `/Users/jg-n-012/test/wiki/learning/codex-review-wave1-2026-05-03.md`
- `knowledge-base/wiki/learning/s2-turtle-verdict-pre-registration-2026-05-03.md` (Scenario A format precedent — for Claude post-hoc reference, NOT for Codex to copy)
- `tools/bt/c1_london_breakout.py` if present (W3-4 sibling, similar structure) — read-only style precedent
- `CLAUDE.md` (Rule 1 Slow & Strict, KB read rules)
- `knowledge-base/wiki/lessons/index.md` — at minimum:
  - `feedback_partial_quant_trap`
  - `feedback_label_empirical_audit`
  - `feedback_cohort_time_check`
  - `feedback_success_until_achieved`
  - `feedback_codex_mock_test_trap`
- `knowledge-base/wiki/analyses/friction-analysis.md` — for BEV_WR_USDJPY confirmation
- `.ai/decisions/20260503-1648-w3-3-s4-changes-requested.md` (this rerun's predecessor)

# Acceptance Criteria

- [ ] `tools/bt/s4_connors_raschke.py` exists. `python3 tools/bt/s4_connors_raschke.py --dry-run` prints the 27-cell grid, primary cell, Bonferroni m=27, all 7 verdict thresholds; exits 0.
- [ ] `python3 tools/bt/s4_connors_raschke.py --cache data/cache/massive/USD_JPY_5m_2014_2026.parquet --output-prefix knowledge-base/raw/bt-results/s4-connors-raschke-2026-05-03 --report knowledge-base/wiki/learning/s4-connors-raschke-bt-2026-05-03.md` writes the artifacts.
- [ ] BT report contains: strategy spec, sensitivity grid table (27 rows × 7 axes + per-cell verdict), primary deep dive, null bootstrap, time-cohort table, Scenario verdict (A-pending / B / C with post-hoc markers).
- [ ] Trade-list and daily-PnL parquets exist for primary cell (Claude post-hoc inputs).
- [ ] BT script encodes thresholds & m as module-level constants **before** BT runs (verifiable via `--dry-run`).
- [ ] All 7 axes reported per cell — partial-quant trap blocked (`feedback_partial_quant_trap`).
- [ ] No catalog file edit, no matrix v1 edit, no `pre-registration.md` (Claude post-hoc only).
- [ ] If `INTERVENTION_LIST_MISSING`: BT aborted, no fabricated dates, BT report explicitly notes the abort.
- [ ] `tests/test_s4_connors_raschke.py`: setup-detection, entry-trigger, exit-logic, Bonferroni, walk-forward unit tests pass.
- [ ] Run report `.ai/runs/<dir>/final.md`: status, files changed, primary verdict (7 axes), Bonferroni m=27 confirmation, null bootstrap p, max DD, Scenario verdict, recommended next task (post-hoc Validity dispatch).

# Verification Commands

```bash
# 1. Dry-run prints LOCKED grid + thresholds
python3 tools/bt/s4_connors_raschke.py --dry-run

# 2. Sanity check cache before BT
python3 -c "
import pandas as pd
df = pd.read_parquet('data/cache/massive/USD_JPY_5m_2014_2026.parquet')
assert len(df) >= 900_000, f'cache too small: {len(df)}'
assert str(df.index.min())[:10] <= '2014-01-31', f'cache start late: {df.index.min()}'
assert str(df.index.max())[:10] >= '2026-04-29', f'cache end early: {df.index.max()}'
print(f'OK: {len(df):,} bars, {df.index.min()} .. {df.index.max()}')
"

# 3. Full BT
python3 tools/bt/s4_connors_raschke.py \
  --cache data/cache/massive/USD_JPY_5m_2014_2026.parquet \
  --output-prefix knowledge-base/raw/bt-results/s4-connors-raschke-2026-05-03 \
  --report knowledge-base/wiki/learning/s4-connors-raschke-bt-2026-05-03.md

# 4. Files present
test -s knowledge-base/wiki/learning/s4-connors-raschke-bt-2026-05-03.md
test -s knowledge-base/raw/bt-results/s4-connors-raschke-2026-05-03.json
test -s knowledge-base/raw/bt-results/s4-connors-raschke-2026-05-03.md
test -s knowledge-base/raw/bt-results/s4-primary-trade-list-2026-05-03.parquet
test -s knowledge-base/raw/bt-results/s4-primary-daily-pnl-2026-05-03.parquet

# 5. Tests
python3 -m pytest tests/test_s4_connors_raschke.py -v
```

# Codex Instructions

Operate from `/Users/jg-n-012/test/fx-ai-trader/`. **Do NOT touch the parent `/Users/jg-n-012/test/` workspace** — it is read-only reference (catalog, matrix v1, codex-review). Outputs all under fx-ai-trader/.

This is **Rule 1 Slow & Strict**. The 27-cell grid, m=27, primary cell `(10, 50_trailing, NY_close_21UTC)`, all 7 axes, and verdict thresholds are PRE-REGISTERED. Encode them as module-level constants in `s4_connors_raschke.py` **before** BT runs. Result MUST NOT modify them.

**Cache verification first.** If `data/cache/massive/USD_JPY_5m_2014_2026.parquet` row count < 900,000 OR min_ts > 2014-01-31 OR max_ts < 2026-04-29, abort with `CACHE_INSUFFICIENT` — do NOT proceed with partial data, do NOT fabricate.

**No external network calls.** No Massive API, no Render API, no yfinance, no pgrep. fib_reversal LIVE corr (Validity #2) and yfinance cross-check (Validity #4) are deferred to Claude. Emit the **inputs** for them (primary-cell trade list parquet + daily-PnL parquet) and **mark them deferred** in the BT report.

Reuse helpers where possible: `wilson_lower`/`wilson_upper_at` from `tools/cell_edge_audit.py`, `kelly_criterion` from `modules/stats_utils.py`. Do not reimplement statistical primitives.

Do not:

- silently add filters not in the spec (no HMM, no MA, no ATR — only 158+ regime gate and intervention-date list)
- soften thresholds based on observed BT numbers
- treat Scenario A as default; require A-pending tag explicitly when post-hoc validity is unsigned
- short-circuit on Scenario C — `feedback_success_until_achieved`: enumerate at least one alternative spec variant in the report
- write `pre-registration.md` for S4 (Claude does this post-hoc on A-pending)
- write to the catalog file or matrix v1
- write to `data/cache/massive/USD_JPY_5m_2014_2026.parquet` or its audit.json

If the catalog's intervention-date list is missing or ambiguous, abort with `INTERVENTION_LIST_MISSING` and report the catalog section that should have it. Do not improvise dates.

In the final run report, include: status, files changed, primary cell verdict (all 7 axes + max DD + Sharpe), Bonferroni m=27 confirmation, null bootstrap p, time-cohort concentration check, deferred-validity markers (#2, #4), Scenario verdict (A-pending / B / C), recommended next task — typically:

- After **A-pending**: `W3-3-posthoc — Claude runs Validity #2 (fib_reversal LIVE corr via Render API + pgrep) + #4 (yfinance USDJPY=X cross-check) on emitted parquets; if both clear, write LOCKED pre-registration.md`
- After **B**: `W4-S4-grid-expand — extend sensitivity to 5×5×5 (m=125) and add GBPJPY pair extension`
- After **C**: `W3-3-alt — pre-reg next §B candidate OR catalog §B-2 demote to academic-only`
