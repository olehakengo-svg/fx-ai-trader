# feat(sr-redesign): pivot detector triangulation for weight-gate audit v2

## PR Description

Adds a `--detector {kde,pivot}` switch to `tools/sr_weight_gate_audit_v2.py` and reruns the v2 fixed audit with the production-style pivot detector (`modules.indicators.find_sr_levels_weighted`). KDE remains the default path and existing KDE outputs were not overwritten.

## 3-Way Verdict Table

| Strategy | v1 buggy KDE verdict | v1 N | v2 fixed KDE verdict | v2 fixed KDE N | v2 fixed PIVOT verdict | v2 fixed PIVOT N | Triangulation |
|---|---|---:|---|---:|---|---:|---|
| sr_anti_hunt_bounce | DEAD | 1441 | DEAD | 335 | DEAD | 140 | OUT_OF_BAND |
| sr_break_retest | DEAD | 294 | DEAD | 294 | DEAD | 222 | - |
| sr_fib_confluence | DEAD | 4748 | DEAD | 2037 | DEAD | 2022 | - |
| sr_liquidity_grab | DEAD | 6 | DEAD | 2 | DEAD | 0 | - |
| sr_channel_reversal | DEAD | 2612 | DEAD | 1249 | DEAD | 1037 | - |

## sr_anti_hunt_bounce Triangulation

- Phase 2 BT: N=594, triangulation band [416, 772].
- v2 fixed KDE: N=335, OUT_OF_BAND, deviation -43.6%.
- v2 fixed PIVOT: N=140, OUT_OF_BAND, deviation -76.4%.
- Decision: detector mismatch is not sufficient to explain the Phase 2 BT N divergence.
- Verdict reproducibility: pivot also returns all 5 DEAD, so the weight thesis remains falsified across detectors.

## Outputs

- `reports/sr_weight_gate_audit_v2_pivot_2026-05-12.md`
- `raw/audits/sr_weight_gate_v2_pivot_2026-05-12.parquet`

## Verification

Commands run:

```text
.venv/bin/python -m py_compile tools/sr_weight_gate_audit_v2.py
.venv/bin/python tools/sr_weight_gate_audit_v2.py --unit-tests
[unit] PASS (incl. bug 1+2 regression + pivot adapter)

.venv/bin/python tools/sr_weight_gate_audit_v2.py --integration-tests --detector pivot
[integration] PASS (detector=pivot)

.venv/bin/python tools/sr_weight_gate_audit_v2.py --all --detector pivot
[audit] wrote raw/audits/sr_weight_gate_v2_pivot_2026-05-12.parquet
[audit] wrote reports/sr_weight_gate_audit_v2_pivot_2026-05-12.md
```

Post-run parquet check:

```text
rows 3421
sr_anti_hunt_bounce     140
sr_break_retest         222
sr_channel_reversal    1037
sr_fib_confluence      2022
```

Existing KDE output diff check:

```text
git diff -- reports/sr_weight_gate_audit_v2_2026-05-12.md raw/audits/sr_weight_gate_v2_2026-05-12.parquet
# no output
```

Final git verification performed after commit:

```text
git log --oneline -5
git stash list
git status --short
```
