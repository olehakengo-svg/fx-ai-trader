# feat(sr-redesign): sr_weighted_break shadow-only strategy (heavy wall breakout retest, break family pair)

## PR Description

Adds `sr_weighted_break` as a Shadow-only daytrade strategy for the break family pair of `sr_weighted_bounce`.
The strategy consumes `layer3.sr_weighted_levels`, applies the same composite weight formula as bounce
(`own_touch:d1_touch:w1_touch:round_score:magnitude_score = 1:3:5:2:1.5`), and looks for heavy-wall
breakout retests with ADX momentum confirmation, HTF contradiction blocking, role-reversal SL, and RR-gated TP.

## Family Pair

- `sr_weighted_bounce`: bounce family, heavy wall rejection.
- `sr_weighted_break`: break family, heavy wall breakout retest.
- Existing SR strategies, including `sr_break_retest`, are left unchanged so shadow data can be compared later.

## Tier Promotion Gate

- Tier 0 audit_only by default (`enabled = False` and env-gated).
- Shadow activation path:
  - `SR_WEIGHTED_BREAK_ENABLE=1`
  - `SR_WEIGHTED_BREAK_SHADOW_PROMOTE=1`
- Tier 0 to Tier 1 requires N>=30, Wilson_lo>=0.40 with Bonferroni m=2 for bounce/break family-wise testing, and no single-year WR>=90% concentration flag.
- Tier 1 to Tier 2 requires N>=100, Bonferroni m=2 reproducibility, WF 3+ folds pos_ratio>=0.8, and Kelly>=0.20.

## Shadow Injection Path

- `strategies/daytrade/__init__.py` imports and registers `SrWeightedBreak`.
- `evaluate_all` enables it only when `SR_WEIGHTED_BREAK_ENABLE=1`.
- `split_shadow_always` emits it through the shadow-always path only when both enable and promote env vars are set.

## Verification

Commands run:

```text
python3 -m pytest tests/test_sr_weighted_break.py tests/test_sr_weighted_break_integration.py -x -v
/usr/bin/python3: No module named pytest

./.venv/bin/python -m pytest tests/test_sr_weighted_break.py tests/test_sr_weighted_break_integration.py -x -v
8 passed in 0.31s

. .venv/bin/activate && python3 -m pytest tests/test_sr_weighted_break.py tests/test_sr_weighted_break_integration.py -x -v
8 passed in 0.31s

python3 scripts/check.py
✅ 全6チェック通過 — 整合性OK
```

`python3 scripts/check.py` emitted existing warnings for disabled strategy QUALIFIED_TYPES registration and KB drift, but exited 0.

Final git verification:

```text
git log --oneline -5
3d2ddba chore(codex): claim 20260513-2300-sr-weighted-break-shadow-strategy-new
27288fe task(codex): queue sr_weighted_break shadow-only new strategy (break family pair) [rule:R1]
25a1617 feat(codex): complete 20260513-2200-sr-weighted-bounce-shadow-strategy-new
389ebe3 chore(codex): claim 20260513-2200-sr-weighted-bounce-shadow-strategy-new
7404a93 task(codex): queue sr_weighted_bounce shadow-only new strategy [rule:R1]

git stash list
# no output

git status --short
 M final.md
 M strategies/daytrade/__init__.py
?? .ai/decisions/2026-05-13-sr-weighted-break-shadow-injection.md
?? knowledge-base/wiki/strategies/sr-weighted-break.md
?? strategies/daytrade/sr_weighted_break.py
?? tests/test_sr_weighted_break.py
?? tests/test_sr_weighted_break_integration.py
```
