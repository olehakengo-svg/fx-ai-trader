---
id: 20260503-1700-a2-alt-simple-structure-scalp-pre-reg
title: A2-alt — Pre-registered BT for 4 simple-structure Scalp candidates (post complex-gate decision)
owner: codex
status: queued
priority: P0
created_at: 2026-05-03T17:00:00+0900
roadmap_gate: Gate 1 (Scalp 枝 N-acceleration, simple-first principle)
rule: R1
---

# Objective

Apply the simple-first principle established in `wiki/decisions/complex-gate-edge-destruction-pattern-2026-05-03.md` by producing a **single LOCKED pre-registration document** evaluating 4 simple-structure Scalp candidates via the standard `run_scalp_backtest` engine. Each candidate gets full quant rigor (N, WR, EV, PF, Wilson 95% CI, max DD, IS/OOS Walk-Forward, Bonferroni p adjusted by K=4). Output: a verdict table identifying at most ONE Promote candidate. **No `app.py` `QUALIFIED_TYPES` change in this task** — the 4 candidates are already registered. Registration to OANDA bridge is a separate task gated on this verdict.

# Why this task (vs 1620 chunked CLI)

- 1620 (`a2-fix-vec-harness-cli-chunked`) builds chunked vec_harness CLI to unblock MTF cascade BT under sandbox.
- The complex-gate decision doc (`wiki/decisions/complex-gate-edge-destruction-pattern-2026-05-03.md`) ruled MTF cascades into **default Reject** territory — the chunked CLI's primary use case is therefore lower priority.
- Standard BT (`run_scalp_backtest`) handles the 4 simple candidates without vec_harness. Foreground execution by parent Claude has been demonstrated to complete (`modules/data.py` parquet fallback wired by A1, USD_JPY 5m loads 36,060 bars from cache).
- A2-alt is the **direct simple-first execution** of the meta-decision; 1620 is infrastructure for an obsolescent path. Both can coexist; this task ranks ahead.

# Pre-registered candidate pool

| # | Strategy | Pair | Interval | Roadmap-v2.1 BT EV | Structure complexity |
|---|---|---|---|---|---|
| 1 | `bb_squeeze_breakout` | USD_JPY | 5m | +1.030 | BB + squeeze (1 indicator + 1 condition) |
| 2 | `engulfing_bb` | USD_JPY | 5m | +0.677 | engulfing candle + BB extreme (2 conditions) |
| 3 | `fib_reversal` | EUR_USD | 1m | +0.426 | Fib retracement (1 level set) |
| 4 | `sr_channel_reversal` | EUR_USD | 5m | +0.231 | SR / channel bounce (1 level set) |

Bonferroni K = **4** (this candidate pool is fixed ex ante). Alpha/K = 0.05/4 = 0.0125.

# Pre-registered thresholds (LOCKED, must encode as constants BEFORE BT)

| Verdict | All conditions must hold |
|---|---|
| **Promote (LIVE register)** | N≥30, PF≥1.30, Wilson_lo > BEV_WR + 5pp, WF: PF_IS≥1.20 AND PF_OOS≥1.20, Bonferroni p < 0.0125, max DD ≤ 30% |
| **Shadow (lot=0.1)** | N≥30, PF≥1.10, Wilson_lo > BEV_WR, WF: PF_IS≥1.00 AND PF_OOS≥1.00, max DD ≤ 30% |
| **Reject** | any other configuration |
| **Insufficient** | N<30 (defer with explicit gap-to-30 reporting) |

`OOS PF ≥ IS PF × 0.85` stability check is **also pre-registered**: any candidate where OOS PF degrades by >15% from IS PF gets auto-flagged with `OVERFIT_SUSPECTED` regardless of other thresholds.

BEV_WR per pair (from `wiki/analyses/friction-analysis.md`):
- USD_JPY: 34.4%
- EUR_USD: 39.7%

# Required quant fields per candidate (12 fields total)

| # | Field | Source |
|---|---|---|
| 1 | N (total trades) | `run_scalp_backtest` result count for `entry_type == strategy` |
| 2 | Wins / Losses | outcome WIN/LOSS |
| 3 | WR | wins/N |
| 4 | EV pip/trade | mean(pnl_pips) |
| 5 | PF | sum(positive PnL) / abs(sum(negative PnL)) |
| 6 | Wilson 95% CI [lo, hi] | reuse `tools/cell_edge_audit.wilson_lower` + `tools/cell_negative_edge_audit.wilson_upper_at` |
| 7 | max DD pip | running peak-drawdown calc on cumulative PnL |
| 8 | max DD % | DD pip / max equity peak (or initial capital surrogate) |
| 9 | WF IS PF / OOS PF | 50/50 chronological split |
| 10 | WF IS WR / OOS WR | same split |
| 11 | Bonferroni one-sided p | `binomial_one_sided_p(wins, N, BEV_WR)` × K=4, capped at 1.0 |
| 12 | half-Kelly | `modules.stats_utils.kelly_criterion` |

# Engine selection rule

- Primary engine: `run_scalp_backtest` (standard BT). 4 candidates are all in `QUALIFIED_TYPES` (verified at `app.py:5537`).
- If `run_scalp_backtest` returns N=0 for a strategy that IS in QUALIFIED_TYPES, document the strategy's gate chain failure (likely `_compute_bt_htf_bias` issue, friction gate, or signal-confirmation count). Do NOT fall back to `bt_vec_harness` — vec_harness is for MTF strategies and would return N=0 for these.
- BT execution may take >30s per candidate. **Parent Claude will execute the BT in foreground** (proven path); Codex builds the wrapper and verdict generator only.

# Scope

Codex MAY change:

- `tools/scalp_alt_pre_reg_bt.py` (new) — wrapper that:
  - Encodes the LOCKED thresholds and K=4 Bonferroni as module-level constants
  - For each of the 4 candidates: calls `run_scalp_backtest`, computes 12 quant fields, applies threshold logic, emits verdict
  - Supports `--dry-run` (prints constants and exits 0)
  - Supports `--candidate <strategy>` for single-candidate execution (so each candidate can be run separately if needed)
  - Supports `--engine-timeout <seconds>` (default 600, NOT 10)
  - Reuses `tools/scalp_re_enable_bt.py` helpers where structurally possible (Wilson, Walk-Forward, half-Kelly)
- `tests/test_scalp_alt_pre_reg_bt.py` (new) — unit tests for the threshold logic and Bonferroni K=4
- `knowledge-base/wiki/learning/scalp-alt-pre-registration-2026-05-03.md` — LOCKED pre-reg doc with all 4 verdicts + summary table
- `knowledge-base/raw/bt-results/scalp-alt-180d-2026-05-03.json` + `.md` — raw BT result aggregate
- `.ai/runs/<new-run-dir>/final.md` — run report

Codex MAY NOT change:

- `app.py` (especially not `QUALIFIED_TYPES` — they're already registered)
- `modules/data.py`, `modules/bt_vec_harness.py`, or any other module
- Any strategy file under `strategies/`
- `tools/scalp_re_enable_bt.py` (read-only reference for helpers)
- `knowledge-base/wiki/decisions/`, `wiki/index.md`, `wiki/strategies/`
- `.env`, OANDA credentials, production DB
- Existing uncommitted changes (see Codex Instructions)

# Required Reading

- `CLAUDE.md` (Rule 1 Slow & Strict, クオンツ判断 protocol)
- `knowledge-base/wiki/decisions/complex-gate-edge-destruction-pattern-2026-05-03.md` — **the meta-decision driving this task**
- `knowledge-base/wiki/decisions/aggregate-kelly-decomposition-2026-05-03.md` — Live picture
- `knowledge-base/wiki/learning/scalp-re-enable-pre-registration-2026-05-03.md` — A2 LOCKED format precedent
- `knowledge-base/raw/bt-results/scalp-mtf-cascade-180d-2026-05-03.{md,json}` — A2 Reject evidence
- `knowledge-base/wiki/syntheses/roadmap-v2.1.md` — Scalp 枝 BT EV reference
- `knowledge-base/wiki/analyses/friction-analysis.md` — BEV_WR per pair
- `tools/scalp_re_enable_bt.py` — helper functions (Wilson, WF, Kelly)
- `tools/cell_edge_audit.py` and `tools/cell_negative_edge_audit.py` — Wilson helpers
- `app.py:5338` (`run_scalp_backtest` signature), `app.py:5537` (`QUALIFIED_TYPES` set)

# Acceptance Criteria

- [ ] `tools/scalp_alt_pre_reg_bt.py` exists with LOCKED constants and is deterministic.
- [ ] `python3 tools/scalp_alt_pre_reg_bt.py --dry-run` prints the 4 candidates, the 4 thresholds, K=4, BEV_WR per pair, and exits 0.
- [ ] `tests/test_scalp_alt_pre_reg_bt.py` exists and passes, covering: threshold logic on synthetic inputs, K=4 Bonferroni computation, OVERFIT_SUSPECTED flag triggering at IS/OOS PF degradation > 15%, candidate metadata correctness.
- [ ] **Parent Claude executes** `python3 tools/scalp_alt_pre_reg_bt.py --candidate <each>` in foreground (not Codex) and writes the JSON result. Codex's wrapper must support this split — parsing the JSON when generating the markdown verdict doc.
- [ ] `knowledge-base/wiki/learning/scalp-alt-pre-registration-2026-05-03.md` exists with: LOCKED thresholds section, K=4 Bonferroni justification, per-candidate quant table (all 12 fields), verdict per candidate, summary table, simple-first decision lineage citing complex-gate decision doc.
- [ ] `knowledge-base/raw/bt-results/scalp-alt-180d-2026-05-03.{json,md}` exist with raw BT results for all 4 candidates.
- [ ] `.ai/runs/<run-dir>/final.md` includes status, files changed, the verdict per candidate (Promote / Shadow / Reject / Insufficient / OVERFIT_SUSPECTED), the Bonferroni K and per-candidate p, the recommended next task (A3 register only the Promote candidate, or A2-alt2 if all Reject).
- [ ] No edits under `app.py`, `modules/`, `strategies/`, `wiki/decisions/`, `wiki/index.md`, `wiki/strategies/`.

# Verification Commands

```bash
# 1. Dry-run prints the LOCKED thresholds and exits 0
python3 tools/scalp_alt_pre_reg_bt.py --dry-run

# 2. Single-candidate runs (parent Claude will execute these in foreground)
python3 tools/scalp_alt_pre_reg_bt.py --candidate bb_squeeze_breakout --engine-timeout 600 \
  --output knowledge-base/raw/bt-results/scalp-alt-bb_squeeze-2026-05-03.json
python3 tools/scalp_alt_pre_reg_bt.py --candidate engulfing_bb --engine-timeout 600 \
  --output knowledge-base/raw/bt-results/scalp-alt-engulfing-2026-05-03.json
python3 tools/scalp_alt_pre_reg_bt.py --candidate fib_reversal --engine-timeout 600 \
  --output knowledge-base/raw/bt-results/scalp-alt-fib-2026-05-03.json
python3 tools/scalp_alt_pre_reg_bt.py --candidate sr_channel_reversal --engine-timeout 600 \
  --output knowledge-base/raw/bt-results/scalp-alt-sr-2026-05-03.json

# 3. Aggregate verdict doc (consumes the 4 JSON files above)
python3 tools/scalp_alt_pre_reg_bt.py --aggregate \
  --output knowledge-base/wiki/learning/scalp-alt-pre-registration-2026-05-03.md

# 4. Unit tests
python3 -m pytest tests/test_scalp_alt_pre_reg_bt.py -v
```

# Codex Instructions

Work in this repository. Respect existing uncommitted changes — do not touch `modules/demo_trader.py`, `knowledge-base/raw/hunt_events/2026-05-02.jsonl`, `knowledge-base/wiki/sessions/2026-05-03-session.md`, or `knowledge-base/raw/cell_deepdive/`. The new `tools/scalp_re_enable_bt.py`, `tools/render_trades_snapshot.py`, `tools/aggregate_kelly_decomposition_audit.py`, etc. are read-only context.

This is a Rule 1 task. Thresholds in the wrapper MUST be encoded as constants BEFORE running BT. Walk-Forward 50/50 split is also pre-registered. Bonferroni K=4 is fixed ex ante.

Do not:

- modify `app.py` `QUALIFIED_TYPES` (already correct)
- modify any strategy file
- skip Bonferroni correction or claim K=1
- soften thresholds based on observed BT numbers
- attempt long BT execution inside Codex sandbox — design the wrapper to accept an externally-generated JSON for the `--aggregate` step
- close on "all Reject" without explicitly recommending the next pre-reg candidate (per `feedback_success_until_achieved`)

If a candidate's `run_scalp_backtest` returns N=0 even though the strategy is in `QUALIFIED_TYPES`, classify as `BT_GATE_BLOCKED` (separate from Insufficient) and document which gate likely fired (signal confirmation count, friction, spread/SL gate, Phase0 gate). This is data for a follow-up gate-relax task, not a verdict.

If OOS PF degrades by >15% from IS PF on any candidate, flag `OVERFIT_SUSPECTED` and downgrade verdict by one tier (Promote → Shadow, Shadow → Reject). This is in the LOCKED rule per the complex-gate decision doc.

In the final report: status, files changed, the verdict per candidate, the K=4 Bonferroni table, the OVERFIT_SUSPECTED flags, the recommended next task. The next task after at least one Promote/Shadow is **A3-simple — register the Promote candidate to OANDA bridge with monitoring**; otherwise **A2-alt2 — pre-register the next simple candidate from the broader Scalp pool**.


## Result (2026-05-03T13:17:06Z)

exit=0 · 252s

```
Implemented the pre-reg wrapper and pending aggregate artifacts without touching forbidden areas (`app.py`, `modules/`, `strategies/`, decisions/index/strategy wiki).

Changed:
- [tools/scalp_alt_pre_reg_bt.py](/data/repo/fx-ai-trader/tools/scalp_alt_pre_reg_bt.py)
- [tests/test_scalp_alt_pre_reg_bt.py](/data/repo/fx-ai-trader/tests/test_scalp_alt_pre_reg_bt.py)
- [scalp-alt-pre-registration-2026-05-03.md](/data/repo/fx-ai-trader/knowledge-base/wiki/learning/scalp-alt-pre-registration-2026-05-03.md)
- [scalp-alt-180d-2026-05-03.json](/data/repo/fx-ai-trader/knowledge-base/raw/bt-results/scalp-alt-180d-2026-05-03.json)
- [scalp-alt-180d-2026-05-03.md](/data/repo/fx-ai-trader/knowledge-base/raw/bt-results/scalp-alt-180d-2026-05-03.md)
- [.ai run report](/data/repo/fx-ai-trader/.ai/runs/20260503-1700-a2-alt-simple-structure-scalp-pre-reg/final.md)

Current verdicts are `BT_PENDING` for all four because I did not run the long foreground BT commands per the task split:

| Strategy | Verdict | Bonf p | Overfit |
|---|---:|---:|---|
| `bb_squeeze_breakout` | BT_PENDING | NA | false |
| `engulfing_bb` | BT_PENDING | NA | false |
| `fib_reversal` | BT_PENDING | NA | false |
| `sr_channel_reversal` | BT_PENDING | NA | false |

Verification:
- Passed: `python3 tools/scalp_alt_pre_reg_bt.py --dry-run`
- Passed: direct assertion harness for all new tests
- Passed: `python3 -m py_compile tools/scalp_alt_pre_reg_bt.py tests/test_scalp_alt_pre_reg_bt.py`
- Blocked: `python3 -m pytest tests/test_scalp_alt_pre_reg_bt.py -v` because `pytest` is not installed in this environment.

Next task: Parent Claude should run the four `--candidate` commands in foreground, then rerun `--aggregate`. After actual verdicts exist: `A3-simple` if one candidate is Promote; otherwise `A2-alt2` if all are Reject/Insufficient/BT_GATE_BLOCKED.
```
