---
id: 20260503-1340-bt-scalp-data-loader-restore-A1
title: A1 — Restore BT scalp test + add parquet fallback to data loader (3 blockers from 1117)
owner: codex
status: queued
priority: P0
created_at: 2026-05-03T13:40:00+0900
roadmap_gate: Gate 1 (Scalp 枝 prerequisite)
rule: R3
---

# Objective

Resolve the three blockers that prevent end-to-end validation of the BT scalp M15/M5 cache fix, identified by Codex run `20260503-130202-...-1117`. After this task, `python3 -c "from app import run_scalp_backtest; run_scalp_backtest('USDJPY=X', lookback_days=180, interval='5m')"` must complete without "All data sources failed" and the regression test must pass. **`QUALIFIED_TYPES` registration of `mtf_regime_trend_cascade_scalp` is OUT OF SCOPE for this task** — that's a quant decision deferred to A2.

# Context

- 1117 final.md: `tests/test_bt_htf_m15_m5_inject.py` is missing in the worktree. It was created in the 2026-05-03 02:57 session by parent Codex but lost in a subsequent reset.
- 1117 final.md: `modules/data.py:587` only tries Massive/OANDA/yfinance and never falls back to local parquet cache at `data/cache/massive/`. This means offline BT validation is impossible, which causes "All data sources failed for USDJPY=X/5m".
- 1117 final.md: `mtf_regime_trend_cascade_scalp` is not in `QUALIFIED_TYPES` at `app.py:5537` — handled separately in A2.
- Rule 3: code restoration + minimal addition. No strategy logic, no live behavior change, no gate change.
- Roadmap dependency: A2 (Scalp re-enable pre-registration) cannot start until A1 unblocks the BT validation path.
- Memory `feedback_check_orphan_local_app`: `pgrep -f app.py` before analysis. The local parquet cache is dev-only; do NOT replace Render API as primary source.
- Memory `feedback_partial_quant_trap`: full BT runs require the data loader to deterministically reproduce N/PF/EV/WR; current "all sources failed" makes any quant verdict on Scalp impossible.

# Scope

Codex may change:

- `modules/data.py` — add a final fallback that reads from `data/cache/massive/` parquet files when Massive/OANDA/yfinance all fail. The fallback must:
  - Be the LAST option, after all online sources fail
  - Print a clear warning that this is offline-cached data with a timestamp
  - Honor the existing function signature; no API change
  - Skip silently if the parquet file does not exist
- `tests/test_bt_htf_m15_m5_inject.py` — recreate based on the 2026-05-03 02:57 session's test logic. The test must verify:
  - `_compute_bt_htf_bias(..., mode="scalp")` returns dicts with both `m15` and `m5` keys populated (non-empty feature dicts)
  - The M15/M5 feature shape mirrors `modules.bt_vec_harness` fields: at minimum `hurst_64`, `range_20`, `sma21`, swing levels, previous M5 bar fields
- `tests/test_bt_data_loader_parquet_fallback.py` — new test for the fallback path
- `.ai/runs/<new-run-dir>/final.md` — run report

Codex may NOT change:

- `app.py` `QUALIFIED_TYPES` set — A2's territory
- Any strategy file under `strategies/`
- Any module under `modules/oanda_*`
- Render API behavior or any production credential
- `knowledge-base/wiki/**`
- Existing uncommitted changes (see Codex Instructions)

# Required Reading

- `CLAUDE.md` — especially the "本番(Render)データを使用" principle and the クオンツ判断 protocol
- `knowledge-base/wiki/decisions/aggregate-kelly-decomposition-2026-05-03.md` — context for why A1 is gating Scalp re-enable
- `.ai/runs/20260503-130202-20260503-1117-bt-scalp-mtf-cascade-validation/final.md` — 1117 verdict (the blockers list)
- `modules/data.py:587` — current loader fallback chain
- `modules/bt_vec_harness.py` — M15/M5 feature schema reference
- `app.py:5338` — `run_scalp_backtest` signature, `_compute_bt_htf_bias` callsite
- `app.py` — search `_compute_bt_htf_bias` definition for the M15/M5 cache logic to test

# Acceptance Criteria

- [ ] `tests/test_bt_htf_m15_m5_inject.py` exists and passes 2/2 tests verifying M15/M5 cache contents (matching the 2026-05-03 02:57 implementation behavior — re-derive the assertions from `app.py` `_compute_bt_htf_bias`).
- [ ] `tests/test_bt_data_loader_parquet_fallback.py` exists and passes, verifying:
  - Online sources tried first (mock to fail)
  - Parquet cache used when online sources fail
  - Function returns empty/raises clear error when parquet cache also missing (not "All data sources failed" silent error)
- [ ] `python3 -m pytest tests/test_bt_htf_m15_m5_inject.py tests/test_bt_data_loader_parquet_fallback.py -v` exits 0 with all tests passing.
- [ ] `python3 -c "from app import run_scalp_backtest; r = run_scalp_backtest('USDJPY=X', lookback_days=180, interval='5m'); print(len(r.get('trades') or r.get('records') or []))"` completes without raising "All data sources failed". The trade count may be 0 (because `mtf_regime_trend_cascade_scalp` is still missing from `QUALIFIED_TYPES` — that's A2's job), but the function must not error on data loading.
- [ ] `data/cache/massive/` is read-only — no new files written there; Codex must inspect what files actually exist before assuming the parquet path layout.
- [ ] Run report in `.ai/runs/` includes status, files changed, the three blocker resolutions (test restored / fallback added / verification command output), and confirmation that `mtf_regime_trend_cascade_scalp` registration is **deferred to A2 by design**.

# Verification Commands

```bash
# 1. Restored regression test
python3 -m pytest tests/test_bt_htf_m15_m5_inject.py -v

# 2. New parquet fallback test
python3 -m pytest tests/test_bt_data_loader_parquet_fallback.py -v

# 3. End-to-end loader works (no "All data sources failed" error)
python3 -c "
from app import run_scalp_backtest
r = run_scalp_backtest('USDJPY=X', lookback_days=180, interval='5m')
trades = r.get('trades') or r.get('records') or []
print(f'trades_loaded: {len(trades)}')
print(f'mtf_regime_trend_cascade_scalp_count:', sum(1 for t in trades if t.get('entry_type') == 'mtf_regime_trend_cascade_scalp'))
"

# 4. Inspect parquet cache layout
ls -la data/cache/massive/ | head -20
```

# Codex Instructions

Work in this repository. Respect existing uncommitted changes — do not touch `modules/demo_trader.py`, `knowledge-base/raw/hunt_events/2026-05-02.jsonl`, `knowledge-base/wiki/sessions/2026-05-03-session.md`, untracked `raw/audits/cell_edge_audit_*` files, or `knowledge-base/raw/cell_deepdive/`. The new tools `tools/render_trades_snapshot.py`, `tools/aggregate_kelly_decomposition_audit.py`, `tools/oanda_passthrough_gap_audit.py`, and `tools/dedup_violation_triage.py` are read-only context.

This is a Rule 3 task. Do not:

- modify `app.py` `QUALIFIED_TYPES` (deferred to A2)
- modify any strategy file or any module under `modules/oanda_*`
- write to `data/cache/massive/` (read-only fallback)
- send anything to OANDA
- edit `knowledge-base/wiki/**`

If `data/cache/massive/` does not contain the expected files for USDJPY=X 5m, document that and propose what files would be needed for a populated fallback (skip the verification command 3, but A1 still PASSes — A2 will then need a separate cache-population task).

If the original `tests/test_bt_htf_m15_m5_inject.py` cannot be reconstructed from current `app.py` `_compute_bt_htf_bias` definition (e.g., the function signature changed), document that as a finding and write the closest reasonable test from current code. The point is end-to-end loader works AND there's a regression net for the M15/M5 inject behavior, not a verbatim restore.

In the final report, include status, files changed, the three blocker resolutions in order, the parquet cache layout summary, the verification command outputs, remaining risks, and the next recommended task (A2 — Scalp re-enable pre-registration with `mtf_regime_trend_cascade_scalp` registration decision).
