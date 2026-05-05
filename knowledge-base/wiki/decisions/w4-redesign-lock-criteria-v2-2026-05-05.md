# W4-Redesign LOCK Criteria v2 (2026-05-05)

## Decision

Replace the W4 mass-dispatch absolute `Kelly >= 0.40` gate with relative improvement gates plus minimum sanity floors.

Rationale:

- W4 covers heterogeneous strategies with different baseline WR, payoff ratio, PF, Kelly, and N.
- A universal `Kelly >= 0.40` threshold was overfit to the `streak_reversal` audit reference and is not a general redesign criterion.
- Redesign should first prove no regression, then positive direction, then statistical support, then minimum deployability.

## LOCK Criteria

```yaml
lock_criteria:
  regression_check:
    - pf_change >= 0
    - wilson_lo_change >= -0.02
    - ev_change >= 0

  positive_direction:
    - n_change_pct >= -10
    - one_of:
      - wilson_lo_change >= +0.02
      - ev_change_pct >= +10
      - pf_change >= +0.05

  significance:
    - cell_level_bonferroni_p < 0.05

  sanity_floor:
    - wilson_lo_proposed >= 0.40
    - pf_proposed >= 1.0
```

## Definitions

```yaml
pf_change: pf_proposed - pf_current
wilson_lo_change: wilson_lo_proposed - wilson_lo_current
ev_change: ev_proposed - ev_current
ev_change_pct: 100 * (ev_proposed - ev_current) / abs(ev_current)
n_change_pct: 100 * (n_proposed - n_current) / n_current
cell_level_bonferroni_p: raw cell p-value adjusted by number of tested cells in the locked family
```

If `ev_current == 0`, use absolute `ev_change >= +0.10R` or a pre-registered strategy-specific minimum instead of `ev_change_pct`.

## Interpretation

All four sections must pass for LOCK PASS.

Possible verdicts:

- `PASS`: all criteria pass.
- `BORDERLINE_REJECT`: regression, direction, and significance pass, but one sanity floor misses by a small margin.
- `REJECT`: any regression, direction, or significance criterion fails, or sanity floor is materially below threshold.
- `DIAGNOSTIC_ONLY`: production runner or official MASSIVE cache contract was not met.

## Why This Is Not Post-hoc Loosening

This v2 gate is stricter in the places that matter for general W4:

- It does not allow PF or EV regression.
- It limits Wilson lower-bound deterioration to 2pp.
- It requires at least one positive movement in Wilson, EV, or PF.
- It requires Bonferroni significance at the cell level.
- It retains deployability floors: Wilson lower >= 0.40 and PF >= 1.0.

The change removes only the universal high-Kelly requirement. Kelly remains reportable, but not an absolute pass/fail gate, because Kelly is highly sensitive to payoff geometry and can be structurally low for high-N, low-edge defensive strategies.

## W4P1 streak_reversal Re-evaluation Estimate

Source: `knowledge-base/raw/bt-results/streak-reversal-htf-soft-penalty-2026-05-05.json`.

Current baseline:

```yaml
n: 1224
wr: 0.3799
ev: 0.3952
pf: 1.0366
wilson_lo: 0.3531
kelly: 0.0134
```

Proposed soft penalty:

```yaml
n: 1564
wr: 0.3996
ev: 0.7754
pf: 1.0735
wilson_lo: 0.3756
kelly: 0.0273
```

Delta:

```yaml
n_change_pct: +27.8
ev_change: +0.3803
ev_change_pct: +96.2
pf_change: +0.0369
wilson_lo_change: +0.0225
```

v2 criteria estimate:

```yaml
regression_check:
  pf_change >= 0: PASS
  wilson_lo_change >= -0.02: PASS
  ev_change >= 0: PASS

positive_direction:
  n_change_pct >= -10: PASS
  one_of:
    wilson_lo_change >= +0.02: PASS
    ev_change_pct >= +10: PASS
    pf_change >= +0.05: FAIL

significance:
  cell_level_bonferroni_p < 0.05: FAIL_OR_NOT_ESTABLISHED
  note: W4P1 recorded Bonferroni p for WR > 50% as 1.0. The raw p in the report is directionally significant for WR < 50%, which is not the locked positive thesis.

sanity_floor:
  wilson_lo_proposed >= 0.40: FAIL (0.3756; short by 0.0244)
  pf_proposed >= 1.0: PASS
```

Verdict estimate:

```yaml
verdict: REJECT
near_miss: true
reason:
  - production data contract was not met by the focused runner
  - cell-level positive-direction Bonferroni was not established
  - sanity floor missed: Wilson lo 0.3756 < 0.40
```

If the only failure after a strict production-cache rerun is `wilson_lo_proposed` near 0.376, the correct decision is not to lower the floor immediately. The correct next step is to run the proper production/cell BT first. A future floor of 0.35 can be discussed only as a portfolio-level policy for low-WR/high-R strategies, not as a W4P1 rescue.

## Required Reporting Template

Every W4 redesign report must include:

```yaml
data_contract:
  source: massive_parquet
  path: data/cache/massive/{PAIR}_{TF}.parquet
  production_runner: true
  helper_runner: false
  verdict_eligible: true

cell_spec:
  estimand: aggregate|cell
  pair: ...
  tf: ...
  session: all|Tokyo|London|NY|Off
  filters: {}

metrics:
  current: {n, wins, wr, wilson_lo, ev, pf, kelly}
  proposed: {n, wins, wr, wilson_lo, ev, pf, kelly}
  deltas: {n_change_pct, wilson_lo_change, ev_change, ev_change_pct, pf_change}
  significance: {raw_p, bonferroni_p, family_size}

lock_verdict:
  regression_check: PASS|FAIL
  positive_direction: PASS|FAIL
  significance: PASS|FAIL
  sanity_floor: PASS|FAIL
  final: PASS|BORDERLINE_REJECT|REJECT|DIAGNOSTIC_ONLY
```

## Codex Self-Review

- v2 does not make W4P1 pass; it still rejects the soft-penalty result under the proposed sanity and significance requirements.
- The criteria are less overfit because they evaluate improvement relative to each strategy baseline.
- The sanity floor prevents noisy, statistically fragile improvements from passing.
- The Bonferroni requirement remains strict enough to avoid selecting noise from 72 redesign attempts.
