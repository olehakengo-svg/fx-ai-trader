---
id: 20260503-1117-bt-scalp-mtf-cascade-validation
title: Validate BT scalp M15/M5 HTF inject — mtf_regime_trend_cascade_scalp end-to-end
owner: codex
status: queued
priority: P2
created_at: 2026-05-03T11:17:00+0900
roadmap_gate: Gate 0
rule: R3
---

# Objective

Confirm that the just-applied `_compute_bt_htf_bias(..., mode="scalp")` M15/M5 feature-cache fix (run `20260503-024932-...-bt-scalp-htf-m15-m5-inject`, status `partially_completed_by_parent_codex`) actually produces a non-zero qualifying signal count when `run_scalp_backtest` is executed on `mtf_regime_trend_cascade_scalp` for USD_JPY 180d, and quantify any N/PF gap against `modules/bt_vec_harness`. If N=0 because the strategy is missing from the standard BT `QUALIFIED_TYPES` gate (`app.py:5537`), document the gap precisely — do **not** modify the gate set in this task.

# Context

- Memory observation #980 (2026-05-03 02:57): tests `tests/test_bt_htf_m15_m5_inject.py` are 2/2 PASSED after the manual fix.
- Memory observation #981 (2026-05-03 02:58): `run_scalp_backtest`'s `QUALIFIED_TYPES` set does not include `mtf_regime_trend_cascade_scalp`, so the standard scalp BT may still return N=0 even with the M15/M5 cache populated. Suspected residual blocker.
- Codex's own `final.md` for run `20260503-024932-...` listed this exact validation as "Next recommended task" but did not execute it.
- Roadmap impact: Scalp枝 (枝 = +200pip/年想定) cannot be evaluated until the standard scalp BT path round-trips a positive-N result for at least one MTF cascade strategy.
- Rule 3: verification only. Output is markdown evidence + run report. QUALIFIED_TYPES registration decision is a separate task.

# Scope

Codex may change:

- `.ai/runs/<new-run-dir>/final.md` — run report.
- `knowledge-base/raw/bt-results/bt-scalp-mtf-cascade-validation-2026-05-03.md` — evidence note.

Codex may NOT change:

- `app.py` `QUALIFIED_TYPES` set or any strategy gate logic — registration decision deferred.
- `modules/bt_vec_harness.py`, `modules/demo_trader.py`, `modules/oanda_*.py`.
- Any strategy file under `strategies/`.
- `knowledge-base/wiki/**`.
- `.env`, OANDA credentials, production DBs (read-only fine).
- Existing uncommitted changes (see Codex Instructions).

# Required Reading

- `CLAUDE.md`
- `knowledge-base/wiki/syntheses/roadmap-v2.1.md` (Scalp枝 section)
- `app.py:5338` — `run_scalp_backtest` signature.
- `app.py:5537` — current `QUALIFIED_TYPES` set inside `run_scalp_backtest`.
- `tests/test_bt_htf_m15_m5_inject.py` — passing regression tests.
- `modules/bt_vec_harness.py` — vectorized harness oracle.

# Data Source

- Same Massive API + Parquet cache path that `run_scalp_backtest` already opens by default. Do NOT hit Render API.
- Symbol: `USDJPY=X`. Window: 180 days, 5m interval.

# Acceptance Criteria

- [ ] `tests/test_bt_htf_m15_m5_inject.py` re-runs green (regression).
- [ ] `run_scalp_backtest("USDJPY=X", lookback_days=180, interval="5m")` invoked; trade count for `entry_type == "mtf_regime_trend_cascade_scalp"` recorded (even if 0).
- [ ] Same window through `modules/bt_vec_harness` for the same strategy; N, PF, EV, WR recorded.
- [ ] Evidence note `knowledge-base/raw/bt-results/bt-scalp-mtf-cascade-validation-2026-05-03.md` contains:
  - Standard BT N / WR / EV / PF.
  - Vectorized harness N / WR / EV / PF.
  - Gap analysis if N differs by > 5%.
  - Verdict on whether M15/M5 cache fix is observable end-to-end.
  - If N=0 in standard BT: explicit "ROOT CAUSE: missing from QUALIFIED_TYPES at app.py:5537" or alternative diagnosis with line numbers.
- [ ] `.ai/runs/<new-run-dir>/final.md` includes status, files changed, the four numbers (std N/PF vs vec N/PF), root cause if N=0, next recommended task.
- [ ] No edits under `app.py`, `modules/`, `strategies/`, `knowledge-base/wiki/`.

# Verification Commands

```bash
python3 -m pytest tests/test_bt_htf_m15_m5_inject.py -v

python3 -c "
from app import run_scalp_backtest
r = run_scalp_backtest('USDJPY=X', lookback_days=180, interval='5m')
trades = r.get('trades') or r.get('records') or []
n = sum(1 for t in trades if t.get('entry_type') == 'mtf_regime_trend_cascade_scalp')
print('standard_bt_n_for_mtf_regime_trend_cascade_scalp:', n)
"

python3 -c "
from modules.bt_vec_harness import run_vec_harness
out = run_vec_harness('USD_JPY', '5m', lookback_days=180,
                      strategies=['mtf_regime_trend_cascade_scalp'])
print(out)
"

python3 -c "
import re, pathlib
src = pathlib.Path('app.py').read_text()
m = re.search(r'def run_scalp_backtest.*?QUALIFIED_TYPES = \\{(.*?)\\}', src, re.S)
print('mtf_regime_trend_cascade_scalp in run_scalp_backtest QUALIFIED_TYPES:',
      'mtf_regime_trend_cascade_scalp' in m.group(1))
"
```

If `run_vec_harness` import path differs, grep `modules/bt_vec_harness.py` for the actual function name and adapt — that's discovery, not scope creep. Document the call in the evidence note.

# Codex Instructions

Work in this repository. Respect existing uncommitted changes — do not touch `modules/demo_trader.py`, `knowledge-base/raw/hunt_events/2026-05-02.jsonl`, `knowledge-base/wiki/sessions/2026-05-03-session.md`, `tests/test_pyramiding_kill_switch.py`, untracked `raw/audits/cell_edge_audit_*` files, or `knowledge-base/raw/cell_deepdive/`.

Do not:

- modify `app.py` (especially not `QUALIFIED_TYPES`), even if a one-line addition would "fix" N=0
- modify any strategy file or any module under `modules/`
- write to any production DB
- send anything to OANDA
- edit `knowledge-base/wiki/**`

If standard BT returns N=0 because the strategy is missing from `QUALIFIED_TYPES`, that is a **finding** — report it with file:line reference and stop. Adding the strategy to `QUALIFIED_TYPES` requires human review (changes which strategies the standard BT counts) and is a separate task.

In the final report, include status, files changed, std-BT vs vec-harness numbers side by side, verdict on whether M15/M5 cache fix is observable end-to-end, root cause if N=0, remaining risks, next recommended task.
