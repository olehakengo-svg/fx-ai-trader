---
id: 20260503-1620-a2-fix-vec-harness-cli-chunked
title: A2-fix — vec_harness chunked CLI wrapper to unblock Scalp re-enable BT (Rule 3 + R1 prep)
owner: codex
status: queued
priority: P0
created_at: 2026-05-03T16:20:00+0900
roadmap_gate: Gate 1 (Scalp 枝 N-acceleration unblocker)
rule: R3
---

# Objective

Build a deterministic, **chunked, resumable CLI** that runs a 180-day vectorized BT for a single (strategy, pair, interval) tuple under the Codex sandbox 10-second-per-call wall-clock budget. The wrapper must wire `modules.bt_vec_harness.VecBacktestRunner` to the existing strategy registry, persist intermediate state to disk between chunks, and produce the **same artifact contract** that A2 (`tools/scalp_re_enable_bt.py`) consumes. This unblocks A2's pre-registration LOCK by removing the "engine unavailable" path. **No promotion / Tier change is performed in this task** — A2-rerun does that.

# Hypothesis (検証対象)

H1 — Chunked execution with persistent intermediate state can drive `VecBacktestRunner.run` over a 180d, 5m, USD_JPY universe to completion under a 10s/chunk sandbox budget without altering its semantics.

H2 — When H1 holds, A2's `Insufficient(N=0)` verdict is caused **purely** by the engine-unavailable path. After this fix, A2-rerun on `mtf_regime_trend_cascade_scalp` USD_JPY 5m 180d returns N>0 (any value, including N<30) and the LOCKED pre-reg verdict becomes data-driven.

If H1+H2 both hold → Gate 1 path (Scalp N-acceleration) is mechanically unblocked.
If H1 holds but H2 fails (engine completes but N still 0) → there is a **separate** Scalp signaling/QUALIFIED_TYPES drift bug — file as `A2-bug-2` and stop.
If H1 fails (chunked execution still cannot fit) → escalate to "raise execution budget outside sandbox" path; document precisely why.

# Context

- A2 (`.ai/runs/20260503-141535-…/final.md`) verdict = `Insufficient` because **both** `run_scalp_backtest` and `bt_vec_harness` exceeded the 10s timeout. No N was produced. Pre-reg LOCK doc was written but cannot drive any decision.
- `modules.bt_vec_harness.VecBacktestRunner.run(symbol, days)` is the public API. There is **no** module-level `run_vec_harness(...)` function — A2 attempted to import one. This task does **not** modify `modules/` (avoids review surface); instead it wires `VecBacktestRunner` directly from a tools-level CLI.
- Aggregate Kelly = 0 (Live N=29, edge=-20pp, Wilson [31.4%, 65.6%]) — surgical demote impossible. Scalp re-enable is the only Gate 1 unlock with bounded surface (`wiki/decisions/aggregate-kelly-decomposition-2026-05-03.md`).
- DD growing 28.01% → **40.65%** ⚠️⚠️ (`wiki/index.md:92` Render API 実測 2026-05-03). N-acceleration urgency is high.
- Memory `feedback_ma_filter_breaks_mr` / `feedback_hmm_gate_same_trap` — Live edges have repeatedly died in BT under conventional gates. **BT is sanity check only**; this task does not register anything Live.
- Memory `feedback_partial_quant_trap` — N/WR/EV alone insufficient. The CLI must surface PF / Wilson / WF / Bonferroni / Kelly fields to A2-rerun.
- Memory `feedback_label_empirical_audit` — verdict on whether the chunked BT produces "the same answer" as a single-shot run cannot be derived from code inspection. The CLI must self-validate against a short single-shot run on a small reference window.
- Sandbox constraint: each `python3 …` invocation has ~10s wall-clock. Loading 180d × 5m USD_JPY parquet alone (~36k bars + indicators) is near the budget. Strategy `.evaluate` per bar pushes it over.

# Scope

Codex MAY change:

- `tools/vec_harness_chunked_cli.py` (new) — chunked, resumable CLI.
- `tools/vec_harness_chunked_state/` (new) — checkpoint state directory (gitignored; create `.gitignore` entry).
- `tests/test_vec_harness_chunked_cli.py` (new) — unit tests including the equivalence test described below.
- `knowledge-base/raw/bt-results/vec-harness-chunked-validation-2026-05-03.{json,md}` (new) — the equivalence-test report.
- `.ai/runs/<new-run-dir>/final.md` (new) — run report.
- `.gitignore` only to add the checkpoint directory.

Codex MAY NOT change:

- `app.py`, anything under `modules/`, anything under `strategies/`.
- `knowledge-base/wiki/decisions/`, `knowledge-base/wiki/index.md`, `knowledge-base/wiki/strategies/`, `knowledge-base/wiki/learning/`, `knowledge-base/wiki/tier-master.md`.
- `tools/scalp_re_enable_bt.py` (A2's wrapper — only this task's CLI consumes it; A2-rerun is a separate task).
- Render API, production credentials, `.env`, production DB, `live_ng_cells` SQLite table.
- OANDA secrets / endpoints in any form.
- `modules/demo_trader.py`, `knowledge-base/raw/hunt_events/2026-05-02.jsonl`, `knowledge-base/wiki/sessions/2026-05-03-session.md`, `knowledge-base/raw/cell_deepdive/` (existing uncommitted changes).

# Required Reading

- `CLAUDE.md` (Rule 3 protocol; KB read rules)
- `knowledge-base/wiki/syntheses/roadmap-v2.1.md` (Scalp 枝 / Gate 1 / Track E)
- `knowledge-base/wiki/decisions/aggregate-kelly-decomposition-2026-05-03.md`
- `.ai/runs/20260503-141535-20260503-1525-a2-scalp-re-enable-pre-registration/final.md` (the blocker that this task removes)
- `modules/bt_vec_harness.py` — at minimum `_load_local_cache`, `load_1m`, `load_htf`, `compute_m15_features`, `compute_m5_features`, `compute_h1_features`, `simulate_outcome`, `VecBacktestRunner.run`, `HtfFeatureSpec`
- `tools/scalp_re_enable_bt.py` (consumer of this CLI's output contract)
- `wiki/lessons/index.md` for `feedback_partial_quant_trap`, `feedback_label_empirical_audit`

# 対象データ / Data Separation (厳守)

| 用途 | 出典 | 混入禁止対象 |
|---|---|---|
| BT bars | parquet cache (`_load_local_cache`) for `USD_JPY 5m 180d` | Render `oanda_audit`, `is_shadow=0` Live, OANDA fills |
| Strategy signal | strategy registry resolved from `strategies/` (read-only import) | Live decision history |
| Validation oracle (small-window reference) | same parquet cache, 30d window | full 180d (would defeat the equivalence test) |

The CLI MUST tag every artifact with `data_source="parquet_cache"` and `live_separation="bt_only"`. Any code path that touches Render API, `live_ng_cells`, or `oanda_audit` is a bug — fail loudly.

# Statistical Conditions

This is an **infrastructure** task (Rule 3) — no statistical promotion thresholds apply. However, the CLI's equivalence test is the gate:

- **Equivalence window**: 30 days, USD_JPY 5m, strategy `mtf_regime_trend_cascade_scalp`.
- **Single-shot reference**: one full `VecBacktestRunner.run(symbol, days=30)` (must complete; if it does not in this sandbox, document and fall back to 14d).
- **Chunked re-run**: same window, same strategy, executed via the new chunked CLI.
- **ACCEPT**: trade list (entry timestamp, side, exit pnl in pip) is **identical** between modes (count, ordering, per-trade pnl ≤ 1e-6 pip diff). N matches exactly.
- **NEEDS_MORE_EVIDENCE**: trade lists agree on N and per-trade pnl within 1e-3 pip but timestamps differ (timezone bug, document and fix).
- **REJECT**: any divergence in N, sign, or pnl >1e-3 pip → chunked execution alters semantics → STOP, do not run 180d.

If reference single-shot exceeds wall-clock even at 14d, run reference 7d only and document the budget; equivalence ACCEPT bar still applies on whichever window completes.

# Roadmap 寄与

Gate 0 → Gate 1 移行の唯一の能動 unblocker。Live N=29 でAggregate Kelly永久0 のまま自然蓄積を待つと数週間レベル。本タスク完了 → A2-rerun → 4 alternative scan (`bb_squeeze_breakout`, `engulfing_bb`, `fib_reversal`, `sr_channel_reversal`) の経路で **Bonferroni K=5** 下でも Promote / Shadow 候補が拾える可能性が出る。

# Decision Procedure (Rule 3)

## Step 1 — CLI design (chunked + resumable)

`tools/vec_harness_chunked_cli.py` MUST:

1. Accept exactly these flags:
   - `--pair USD_JPY` (required, validated against the parquet cache)
   - `--strategy <strategy_name>` (required, resolved via the strategy registry)
   - `--interval 5m` (required; 1m / M15 also valid for future re-use)
   - `--lookback <int>` (required; 7 / 14 / 30 / 60 / 90 / 180 supported)
   - `--chunk-days <int>` (default 30; allowed 7..60)
   - `--state-dir tools/vec_harness_chunked_state/<run-id>/` (default constructed from a content hash of the args; resumable on re-invocation)
   - `--output <path>` (output JSON; required)
   - `--validate-equivalence-window <int>` (optional; runs the equivalence test on this lookback and exits)
   - `--dry-run` (prints chunk plan + state-dir path; no execution)

2. Persist after each chunk:
   - the full trade list so far (append-only JSONL)
   - the last processed bar timestamp
   - a hash of `(pair, interval, strategy_name, lookback, chunk_days, harness_version)` so a stale state-dir refuses to merge
   - exit code 0 when a chunk completes; non-zero only on hard errors

3. Re-invocation idempotence: running the same command twice in a row MUST resume from the last checkpoint and produce a byte-identical final JSON (modulo `wall_clock_seconds`).

4. The final JSON contract (consumed by A2's wrapper):

   ```json
   {
     "schema_version": 1,
     "data_source": "parquet_cache",
     "live_separation": "bt_only",
     "pair": "USD_JPY",
     "strategy": "mtf_regime_trend_cascade_scalp",
     "interval": "5m",
     "lookback_days": 180,
     "chunk_days": 30,
     "n": 0,
     "wins": 0,
     "losses": 0,
     "wr": 0.0,
     "ev_pip": 0.0,
     "pf": null,
     "wilson_lo": 0.0,
     "wilson_hi": 0.0,
     "max_dd_pip": 0.0,
     "max_dd_pct": 0.0,
     "wf_50_50": {"is": {"n": 0, "pf": null, "wr": 0.0}, "oos": {"n": 0, "pf": null, "wr": 0.0}},
     "trades": [{"ts": "...", "side": "long|short", "pnl_pip": 0.0}],
     "harness_version": "<git rev or hash>",
     "wall_clock_seconds_total": 0.0,
     "chunks_completed": 0,
     "resumed_from_checkpoint": false
   }
   ```

5. Fields `pf`, `wf_50_50` MUST be computed deterministically from `trades`. The CLI MUST NOT compute Bonferroni / Kelly / verdict — those belong to A2's wrapper. Single Responsibility.

## Step 2 — Equivalence test (the ACCEPT gate)

`tests/test_vec_harness_chunked_cli.py` MUST contain:

- `test_chunked_equals_single_shot_30d` — runs the reference single-shot path, runs chunked path with `--chunk-days 10`, asserts trade lists are identical. If single-shot 30d exceeds budget, fall back to 14d, then 7d, and document.
- `test_resume_idempotence` — interrupt after first chunk (simulated by calling the chunk loop directly with a chunk cap of 1), re-invoke, assert the final JSON is byte-identical to a single-process completion.
- `test_state_dir_hash_mismatch_aborts` — change `chunk_days` between runs with the same `state_dir`; CLI MUST refuse and exit non-zero.
- `test_data_source_tag_is_parquet_only` — assert `data_source == "parquet_cache"` and that no `Render` / `oanda_audit` / `is_shadow` import was loaded by the CLI module.

## Step 3 — Production run on the unblocker target

After Step 2 passes, run:

```bash
python3 tools/vec_harness_chunked_cli.py \
  --pair USD_JPY --strategy mtf_regime_trend_cascade_scalp \
  --interval 5m --lookback 180 --chunk-days 30 \
  --output knowledge-base/raw/bt-results/vec-harness-chunked-USDJPY-5m-180d-2026-05-03.json
```

Resumption is **expected**. The CLI MUST be invoked repeatedly until `chunks_completed * chunk_days >= lookback_days`. Each invocation should emit a 1-line progress summary to stdout.

# Acceptance Criteria

- [ ] `tools/vec_harness_chunked_cli.py` exists, runs `--dry-run` in <2s, prints chunk plan + state-dir path.
- [ ] All four tests in `tests/test_vec_harness_chunked_cli.py` pass.
- [ ] `knowledge-base/raw/bt-results/vec-harness-chunked-validation-2026-05-03.md` documents the equivalence-test result with: reference window used, N reference, N chunked, per-trade pnl max abs diff, ACCEPT/REJECT verdict.
- [ ] `knowledge-base/raw/bt-results/vec-harness-chunked-USDJPY-5m-180d-2026-05-03.json` exists and conforms to the schema above.
- [ ] No edits to `app.py`, `modules/`, `strategies/`, `knowledge-base/wiki/decisions/`, `knowledge-base/wiki/index.md`, `knowledge-base/wiki/strategies/`, `knowledge-base/wiki/learning/`, `knowledge-base/wiki/tier-master.md`, or `tools/scalp_re_enable_bt.py`.
- [ ] `.gitignore` updated to exclude `tools/vec_harness_chunked_state/`.
- [ ] `.ai/runs/<run-dir>/final.md` reports: status, files changed, equivalence verdict, 180d run N + chunks_completed + total wall-clock, the next recommended task.

# Verification Commands

```bash
# 1. Dry-run shows chunk plan
python3 tools/vec_harness_chunked_cli.py \
  --pair USD_JPY --strategy mtf_regime_trend_cascade_scalp \
  --interval 5m --lookback 180 --chunk-days 30 --dry-run \
  --output /tmp/_dryrun.json

# 2. Equivalence test
python3 -m pytest -q tests/test_vec_harness_chunked_cli.py

# 3. 180d production run (idempotent re-invocation)
for i in 1 2 3 4 5 6; do
  python3 tools/vec_harness_chunked_cli.py \
    --pair USD_JPY --strategy mtf_regime_trend_cascade_scalp \
    --interval 5m --lookback 180 --chunk-days 30 \
    --output knowledge-base/raw/bt-results/vec-harness-chunked-USDJPY-5m-180d-2026-05-03.json \
    || break
done

# 4. Schema check
python3 -c "
import json, sys
d = json.load(open('knowledge-base/raw/bt-results/vec-harness-chunked-USDJPY-5m-180d-2026-05-03.json'))
assert d['schema_version'] == 1
assert d['data_source'] == 'parquet_cache'
assert d['live_separation'] == 'bt_only'
assert d['lookback_days'] == 180
assert isinstance(d['trades'], list)
print(f\"N={d['n']} chunks_completed={d['chunks_completed']} wall_clock={d['wall_clock_seconds_total']:.1f}s\")
"

# 5. No forbidden imports
python3 -c "
import importlib, sys
m = importlib.import_module('tools.vec_harness_chunked_cli')
forbidden = {'app', 'modules.demo_trader'}
loaded = {n.split('.')[0] + ('.' + n.split('.')[1] if '.' in n else '') for n in sys.modules}
hit = forbidden & loaded
assert not hit, f'forbidden imports loaded: {hit}'
print('imports clean')
"

# 6. File presence
test -s tools/vec_harness_chunked_cli.py
test -s tests/test_vec_harness_chunked_cli.py
test -s knowledge-base/raw/bt-results/vec-harness-chunked-validation-2026-05-03.md
test -s knowledge-base/raw/bt-results/vec-harness-chunked-USDJPY-5m-180d-2026-05-03.json
```

# Codex Instructions

Work in this repository. Respect existing uncommitted changes — do not touch the files listed in **Codex MAY NOT change**. The new tools `tools/render_trades_snapshot.py`, `tools/aggregate_kelly_decomposition_audit.py`, `tools/oanda_passthrough_gap_audit.py`, `tools/dedup_violation_triage.py`, `tools/h1_hour_bucket_counterfactual.py`, `tools/scalp_re_enable_bt.py` are read-only context.

This is a **Rule 3** task: structural / runtime infrastructure. No statistical promotion thresholds apply. The single hard ACCEPT gate is the **equivalence test** in Step 2 — chunked execution must produce trade-list identical results to a single-shot reference run on the same window. **A REJECT verdict on equivalence MUST stop the work**; do not soften the bar to ship.

Do not:

- import `app`, `modules.demo_trader`, `modules.oanda_*`, or anything that reaches Render / Postgres / OANDA at module import time
- mutate the parquet cache files
- use any timezone other than what `_load_local_cache` already returns (no silent UTC ↔ JST conversion)
- compute Bonferroni / Kelly / verdict in this CLI (A2's wrapper owns those)
- claim equivalence ACCEPT without the explicit per-trade pnl diff line in the validation md

If the parquet cache for USD_JPY 5m 180d is missing or short, document precisely the rows / span available, set `n=0`, set `chunks_completed=0`, and emit `data_status: "cache_short"` in the JSON. Do not fabricate.

In the final report under `.ai/runs/`, include: status (`ACCEPT|NEEDS_MORE_EVIDENCE|REJECT`), files changed, the equivalence-test diff line (max |pnl| diff), the 180d run N and chunks_completed and total wall-clock, the recommended next task. The next task after ACCEPT is **A2-rerun-with-chunked-cli** (re-runs `tools/scalp_re_enable_bt.py` against the chunked CLI's JSON contract for `mtf_regime_trend_cascade_scalp` and the four alternatives).
