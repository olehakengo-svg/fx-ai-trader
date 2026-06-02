---
id: 20260602-1715-sr-family-structural-defect-diagnosis-and-fix
priority: P1
gate: R3
rule: R3
status: queued
created: 2026-06-02
owner: claude
---

# SR Family — Structural Defect Diagnosis & Repair (post SR-weight Phase 1/2 audit)

**Rule classification**: R3 (Immediate — observation-confirmed silent failures in
the SR-weight pipeline; not strategy edge re-validation. Strategy ロジックの優劣
**ではなく** 候補評価 / shadow emit / `demo_trades` / `oanda_audit` の境界整合
バグ修復が本タスクの主目的)

## Context — what Claude has already established

User asked 2026-06-02: "直近のSR系戦略全てをshadowから抽出して、水平線の検出
重み付の仕組みを導入したと思うんだけど、実際その後どうワークしているか Cell
単位で抽出して欲しい".

Claude pulled fresh Render production data (NOT stale local DB) via
`/api/oanda/audit?limit=10000` (7,288 rows) and `/api/demo/trades` paginated
(7,725 rows since 2026-04-08). Joined by `demo_trade_id` ↔ `trade_id`,
filtered `is_shadow=1`, binned `sr_strength` into Phase 2 BT bins
([0,0.5)/[0.5,0.65)/[0.65,0.75)/[0.75,0.85)/[0.85,1.0]).

A first Codex rescue pass diagnosed the **local** DB (475 rows, latest
2026-04-30) and warned that `evaluated_candidates` ≠ shadow execution. That
warning is valid but its primary critique was based on stale local data —
Claude has since used Render-only sources. The current code path
(`_open_shadow_emit_trade()` at [modules/demo_trader.py:841](modules/demo_trader.py)
writes both `demo_trades` `is_shadow=True` AND `oanda_audit` `bridge_status='skipped'`
`block_reason='shadow_tracking'`, covering all strategies per
[modules/demo_trader.py:814](modules/demo_trader.py)) is confirmed-working for
6,251 shadow_tracking rows in audit.

## Three confirmed structural defects (from Render-only data)

### Defect #1: `sr_liquidity_grab` — total silence

Production data 2026-04-07 .. 2026-06-02:

- `oanda_audit.entry_type='sr_liquidity_grab'`: **0 rows**
- `demo_trades.entry_type='sr_liquidity_grab'`: **0 rows**

Strategy file exists at
[strategies/daytrade/sr_liquidity_grab.py](strategies/daytrade/sr_liquidity_grab.py):
class `SrLiquidityGrab`, `name = "sr_liquidity_grab"`.

Activation gated at [strategies/daytrade/__init__.py:421-423](strategies/daytrade/__init__.py):
```python
if (os.environ.get("SR_LIQUIDITY_GRAB_REDESIGN_V2") == "1"
        and os.environ.get("SR_LIQUIDITY_GRAB_REDESIGN_V2_SHADOW_PROMOTE") == "1"):
    _shadow_always = _shadow_always | {"sr_liquidity_grab"}
```

Hypotheses:

- **H_ENV_OFF**: env flags `SR_LIQUIDITY_GRAB_REDESIGN_V2=1` and
  `SR_LIQUIDITY_GRAB_REDESIGN_V2_SHADOW_PROMOTE=1` are not set on Render.
  Without `_shadow_always`, the strategy is filtered out before
  `_open_shadow_emit_trade` is called.
- **H_SIGNAL_DEAD**: the strategy is in `_shadow_always` but its `generate()`
  / `produce_candidate()` is returning `None` for every bar since 2026-04-07
  (~56 days). Inspect [strategies/daytrade/sr_liquidity_grab.py](strategies/daytrade/sr_liquidity_grab.py)
  filter chain.
- **H_REGISTRY_MISS**: even though `name="sr_liquidity_grab"` is correct,
  there is a regression in [strategies/daytrade/__init__.py](strategies/daytrade/__init__.py)
  `__init__` registration list that omits this class from the active scheduler
  loop.

### Defect #2: `sr_weighted_bounce` / `sr_weighted_break` — Wave 1 silence after 2026-05-29

Production data:

| strategy | total audit | post-2026-05-27 | latest_ts |
|---|---:|---:|---|
| `sr_weighted_bounce` | 9 | **1** | 2026-05-29T03:46:45 |
| `sr_weighted_break` | 13 | **10** | 2026-05-29T08:47:01 |

Both have been silent **since 2026-05-29** (~5 days). All 9 + 13 trades closed
with `pnl_pips < 0`:

- `sr_weighted_bounce` 13/13 closed shadow trades: WR=0.0%, EV=−3.62, total
  −47.0 pip. Heavy cells (`[0.85,1.0]`): USD_JPY BUY 0/3, USD_JPY SELL 0/3,
  GBP_JPY BUY 0/1.
- `sr_weighted_break` 23/23 closed: WR=17.4%, EV=−3.53, total −81.1 pip.
  Worst cell: `GBP_JPY BUY [0.85,1.0]` N=8 WR=0% −61.3 pip.

env flags are confirmed live (otherwise audit would be 0). Hypotheses:

- **H_DETECTOR_DEPENDENT**: the weighted-level detector
  (`ctx.layer3['sr_weighted_levels']`) is empty for the most recent pair/TF
  states, blocking the entry condition at
  [strategies/daytrade/sr_weighted_bounce.py:176-179](strategies/daytrade/sr_weighted_bounce.py)
  `if not weighted_levels: return None`.
- **H_K_THRESHOLD**: `K_ABS_THRESHOLD=3.0` plus `percentile=30%` doubly-gated;
  in low-volume regime no level passes both filters.
- **H_PER_BAR_DEDUP**: v2 closed-bar dedup at line ~225 is leaking and
  blocking re-entry for the same bar timestamp across cold restarts.

### Defect #3: `sr_break_retest` post-Phase-1 weight-population gap

Production data:

- `oanda_audit.entry_type='sr_break_retest'`: 251 rows, post-2026-05-27 = 55,
  latest 2026-06-02T14:23:18 → **firing fine**.
- BUT `sr_strength` populated for **1 of 251 rows** (0.4%) on Render.

This was the post-Phase-1-ACCEPT (2026-05-11, commit 364027e) promise of
"SR-target 100% populated". Other strategies show better coverage:

| strategy | total | sr_strength populated |
|---|---:|---:|
| sr_anti_hunt_bounce | 88 | 72 (82%) |
| sr_fib_confluence | 442 | 137 (31%) |
| sr_channel_reversal | 519 | 62 (12%) |
| dt_sr_channel_reversal | 150 | 38 (25%) |
| **sr_break_retest** | **251** | **1 (0.4%)** ← anomaly |

The fact that 250 of 251 sr_break_retest audit rows lack `sr_strength` while
the same `oanda_audit` table receives populated values from other SR
strategies suggests the populate path (`extras['sr_strength']` etc.) is
**not wired into sr_break_retest's `Candidate` / `extras` emission**.
Locate where other SR strategies pass `sr_strength` to the audit row
upsert call (likely in `OandaBridge.record_audit()` reading from
candidate metadata) and compare against `sr_break_retest`.

## Key (non-defect) findings to preserve in the analysis

These are NOT bugs but quant findings — confirm them and persist into
`raw/audits/`:

1. **`sr_anti_hunt_bounce` Phase 2 BT survivor thesis IS reproducing in
   Live shadow**:
   - strong (sr_strength≥0.7) N=49 WR=26.5% **EV=+4.92 PF=4.24 Wilson_lo=0.162**
   - weak (<0.7) N=19 WR=15.8% EV=−13.61 PF=0.15
   - NULL N=81 WR=13.6% EV=−6.87 PF=0.20
   - Spread strong vs weak = +18.5 pip/trade, consistent with BH FDR survivor
     (Phase 2 ACCEPT 2026-05-11).
   - Cell `EUR_JPY BUY [0.85,1.0]` N=13 WR=100% +24.27 pip Wilson_lo=0.772
     (Bonferroni m=多数 補正前、post-hoc selection 注意).

2. **Other 4 SR strategies show no strong/weak discrimination**, matching
   Phase 2 BT NULL verdict — "思想は正、設計が誤" (W4-EDA 91%).

## Required investigation & repair (Codex)

### Step 0: Pre-completed by Claude (2026-06-02)

**Render env audit DONE via SSH** (srv-d6va1of5r7bs73en10vg):

```
SR_LIQUIDITY_GRAB_REDESIGN_V2=1
SR_LIQUIDITY_GRAB_REDESIGN_V2_SHADOW_PROMOTE=1
SR_WEIGHTED_BOUNCE_ENABLE=1
SR_WEIGHTED_BOUNCE_SHADOW_PROMOTE=1
SR_WEIGHTED_BREAK_ENABLE=1
SR_WEIGHTED_BREAK_SHADOW_PROMOTE=1
SR_ANTI_HUNT_BOUNCE_REDESIGN_V2=1
SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE=1
SR_BREAK_RETEST_REDESIGN_V2=1
SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE=1
SR_FIB_CONFLUENCE_REDESIGN_V2=1
SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE=1
```

→ **H_ENV_OFF REJECTED for all three defects**.

**Defect #3 ALREADY FIXED on branch** `fix/sr-break-retest-sr-meta-2026-06-02`
(commit 51f3ef11): Candidate.sr_meta_from_price added at
strategies/daytrade/sr_break_retest.py:409. Full suite 1709 passed.

Remaining investigation focus for Codex:

- **#1 H_SIGNAL_DEAD primary**: sr_liquidity_grab has 0 audit rows in 56
  days despite env enabled. Strategy file at
  strategies/daytrade/sr_liquidity_grab.py — instrument the `evaluate()`
  method to log once per bar (or once per N bars to avoid noise) whether
  it returned None vs Candidate. After 24h paper replay, if 0
  Candidates, deeper logic bug. If non-zero Candidates but 0 audit rows,
  shadow-emit gating bug downstream.

- **#2 H_DETECTOR_DEPENDENT primary**: sr_weighted_bounce/break silent
  since 2026-05-29 (5 days as of 2026-06-02). 22 audit rows in the prior
  19 days proves the gate CAN fire. Instrument
  strategies/daytrade/sr_weighted_bounce.py:175-184 (and the analogous
  point in sr_weighted_break.py) to count per bar:
  (a) weighted_levels empty count
  (b) K_ABS_THRESHOLD=3.0 rejection count
  (c) percentile=30% rejection count
  (d) post-weight ADX/BB%B/confirmation rejection count
  After 24h paper replay, the dominant rejection bucket tells the
  remediation direction.

### Step 1 (superseded by Step 0 — kept for reference)

Read the service environment for fx-ai-trader (srv-d6va1of5r7bs73en10vg)
and report the values of:

- `SR_LIQUIDITY_GRAB_REDESIGN_V2`
- `SR_LIQUIDITY_GRAB_REDESIGN_V2_SHADOW_PROMOTE`
- `SR_WEIGHTED_BOUNCE_ENABLE`
- `SR_WEIGHTED_BOUNCE_SHADOW_PROMOTE`
- `SR_WEIGHTED_BREAK_ENABLE`
- `SR_WEIGHTED_BREAK_SHADOW_PROMOTE`
- `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2`, `*_SHADOW_PROMOTE`
- `SR_BREAK_RETEST_REDESIGN_V2`, `*_SHADOW_PROMOTE`
- `SR_FIB_CONFLUENCE_REDESIGN_V2`, `*_SHADOW_PROMOTE`

Do **not** print full values to logs; redact to `set` / `unset` / `0` / `1`
only. Do not commit secrets.

### Step 2: SQLite production DB introspection

SSH to web service (srv-d6va1of5r7bs73en10vg) and run on `/var/data/demo_trades.db`:

```sql
-- 2a: sr_liquidity_grab — search for any historical presence anywhere
SELECT 'audit' AS src, COUNT(*) FROM oanda_audit WHERE entry_type LIKE '%liquidity%';
SELECT 'demo_trades' AS src, COUNT(*) FROM demo_trades WHERE entry_type LIKE '%liquidity%';
SELECT 'evaluated_candidates' AS src, COUNT(*) FROM evaluated_candidates WHERE strategy_name LIKE '%liquidity%' OR entry_type LIKE '%liquidity%';

-- 2b: sr_weighted_* recent fire timestamps and per-pair distribution
SELECT entry_type, instrument, direction, COUNT(*), MAX(timestamp)
FROM oanda_audit
WHERE entry_type IN ('sr_weighted_bounce','sr_weighted_break')
GROUP BY entry_type, instrument, direction
ORDER BY 4 DESC;

-- 2c: sr_break_retest sr_strength populate gap detail
SELECT
    CASE WHEN sr_strength IS NULL THEN 'NULL' ELSE 'POP' END AS strength_state,
    COUNT(*) AS n,
    MIN(timestamp), MAX(timestamp)
FROM oanda_audit
WHERE entry_type = 'sr_break_retest'
GROUP BY 1;

-- 2d: For comparison, where IS sr_strength populated correctly?
SELECT entry_type, COUNT(*) AS n_total,
       SUM(CASE WHEN sr_strength IS NOT NULL THEN 1 ELSE 0 END) AS n_populated
FROM oanda_audit
WHERE entry_type LIKE 'sr_%' OR entry_type LIKE 'dt_sr_%'
GROUP BY entry_type
ORDER BY 2 DESC;
```

### Step 3: Code-path investigation

For each defect, trace the failure point:

**#1 sr_liquidity_grab**:
- Verify class is imported and instantiated by reading
  [strategies/daytrade/__init__.py](strategies/daytrade/__init__.py) (look
  for `from strategies.daytrade.sr_liquidity_grab import SrLiquidityGrab`
  AND its addition to the strategy list / registry returned to
  `demo_trader`).
- Add a debug log statement at the top of
  `SrLiquidityGrab.produce_candidate()` (or whichever method generates the
  candidate) that fires once per bar with `(symbol, bar_time, gate_state)`
  to prove whether it's being called at all. If not called, registry bug.
  If called but always returns None, signal-gen bug.
- Inspect `_open_shadow_emit_trade` path: if the strategy IS in
  `_shadow_always` but produces a candidate that gets filtered out before
  the emit, log where.

**#2 sr_weighted_bounce/break Wave 1 silence**:
- In [strategies/daytrade/sr_weighted_bounce.py:175-184](strategies/daytrade/sr_weighted_bounce.py),
  add instrumentation to count separately:
  (a) bars reaching weight_gate, (b) bars where `weighted_levels` was empty,
  (c) bars where `_select_heavy_level` returned None due to K_ABS_THRESHOLD,
  (d) bars rejected due to percentile cutoff, (e) bars passing weight_gate
  but failing later filter (ADX, BB%B, confirmation_bars).
- Run for 1 hour of paper-replay on USD_JPY M15 covering 2026-05-30 ..
  2026-06-02 and report counts per bucket.
- Same instrumentation for `sr_weighted_break.py`.

**#3 sr_break_retest sr_strength populate gap**:
- Find where `sr_strength` is set on the audit upsert. Likely flow:
  candidate emission → `OandaBridge.execute()` (or shadow-emit) →
  `record_audit()` → audit row insert. The `sr_strength` field needs to
  be populated from `candidate.sr_meta` or similar dict.
- Compare `sr_anti_hunt_bounce.py` (82% populate) emission vs.
  `sr_break_retest.py` (0.4% populate) emission. Likely missing field
  in the Candidate `sr_meta` builder. Note
  [strategies/base.py](strategies/base.py) `Candidate.sr_meta_from_price`
  classmethod referenced in `sr_weighted_bounce.py` line 257.

### Step 4: Repair (if scope allows in 1 session)

- **#1 sr_liquidity_grab**: if H_ENV_OFF confirmed, this is a knowledge-only
  finding — file `wiki/decisions/sr-liquidity-grab-env-disabled-2026-06-02.md`
  documenting that the strategy is currently dormant by design. If H_SIGNAL_DEAD
  or H_REGISTRY_MISS, propose the minimal code fix and commit on a branch
  (do NOT push directly to main). Acceptance: a 24h paper-replay generates
  ≥1 shadow audit row for `sr_liquidity_grab`.

- **#3 sr_break_retest sr_strength populate**: add the missing `sr_strength`
  /`sr_touches`/`sr_days_span`/`sr_distance_atr`/`sr_is_strong` field to
  the strategy's candidate metadata so the audit upsert can read it.
  Commit on a branch. Acceptance: after deploy, new
  `sr_break_retest` rows in `oanda_audit` have non-NULL `sr_strength`
  (verify with a follow-up `SELECT` after 1 hour of live market).

- **#2 sr_weighted_bounce/break Wave 1 silence**: instrumentation only,
  NO threshold tuning in this session (post-hoc selection 罠 + Wave 1
  parameter sweep 禁止 per
  [.ai/decisions/2026-05-13-sr-weighted-bounce-shadow-injection.md](.ai/decisions/2026-05-13-sr-weighted-bounce-shadow-injection.md)).
  Output: instrumented counts go to wiki/learning/, decide in next session
  whether the gate is too tight or the detector is broken.

## Acceptance criteria (verdict for the Codex run)

`ACCEPT` requires **all** of:

1. Render env flag report (Step 1) committed to wiki/decisions/ as redacted
   set/unset table.
2. SQL output for Steps 2a–2d saved to `raw/audits/sr-family-structural-audit-2026-06-02.md`.
3. Hypothesis verdict for each of Defects #1, #2, #3 (one of
   `CONFIRMED_*`, `REJECTED`, `NEEDS_MORE_DATA`).
4. For Defect #3 specifically: a code fix on a feature branch (NOT main)
   that demonstrably adds `sr_strength` to `sr_break_retest` candidate
   metadata, verified by a unit test mock.
5. Defect #1 #2 #3 next-step decision documented as Rule-1/2/3 decision
   memos in `.ai/decisions/`.

`NEEDS_MORE_EVIDENCE` if any of the above blockers cannot be cleared
within the allotted runtime (likely Step 1 env access).

`REJECT` if Codex concludes the Claude-side diagnosis is wrong about all
three defects (i.e. there are no structural defects). In that case Codex
must provide the contradicting evidence with timestamps.

## Forbidden actions

- Do NOT modify production env vars on Render. Read-only.
- Do NOT delete or rewrite historical `oanda_audit` rows.
- Do NOT sweep `K_ABS_THRESHOLD` / `percentile` / `ADX_MAX` parameters
  for `sr_weighted_bounce`/`sr_weighted_break` (Wave 1 lock).
- Do NOT push to main. Feature branch + PR only for code changes.
- Do NOT commit secrets (`OANDA_API_KEY`, `OPENAI_API_KEY`, `sk-*`,
  `rnd_*`, `ghp_*`).

## Pre-registered metrics (for Step 2 SQL output)

For each strategy in `sr_anti_hunt_bounce`, `sr_fib_confluence`,
`sr_break_retest`, `sr_liquidity_grab`, `sr_channel_reversal`,
`dt_sr_channel_reversal`, `sr_weighted_bounce`, `sr_weighted_break`:

- `N` (Shadow only, `is_shadow=1`)
- `WR`
- `EV` (mean pnl_pips)
- `PF` (gross_profit / gross_loss)
- `Wilson_lo` (95% lower bound of WR)
- `Kelly` (full Kelly fraction)
- `total_pip`
- post-2026-05-27 sub-counts

Output to `raw/audits/sr-family-structural-audit-2026-06-02.md` as a
markdown table per strategy.

## References

- Claude session diagnostic raw data: `/tmp/sr_extract/` (audit.json,
  demo_trades.json, analyze.py — Claude-local, not in repo).
- Phase 1 ACCEPT decision:
  `.ai/decisions/2026-05-11-1430-sr-weight-phase1-postdeploy-accept.md`.
- Phase 2 ACCEPT decision:
  `.ai/decisions/2026-05-11-1800-sr-weight-phase2-accept.md`.
- Wave 1 SR-weighted-bounce shadow injection:
  `.ai/decisions/2026-05-13-sr-weighted-bounce-shadow-injection.md`.
- Wave 1 SR-weighted-break shadow injection:
  `.ai/decisions/2026-05-13-sr-weighted-break-shadow-injection.md`.
- Phase 2 forensic divergence: `reports/sr_phase2_vs_audit_v2_forensic_2026-05-13.md`.
- Shadow-first architecture memory: `feedback_shadow_first_quant_architecture`.
- SR audit gap memory (now disputed by current data):
  `project_sr_family_audit_gap_2026_05_21` — this task is the resolution.


## Result (2026-06-02T18:10:28Z)

exit=0 · 716s

```
Implemented and committed on branch `fix/sr-family-structural-2026-06-02`.

Commit: `70c43bae fix(sr): instrument structural audit gaps`

What changed:
- Fixed `sr_break_retest` candidate metadata wiring so `sr_meta` is emitted via `Candidate.sr_meta_from_price(...)`.
- Added unit coverage verifying `sr_strength`/touch/span/strong/distance metadata.
- Added gated diagnostics for:
  - `sr_liquidity_grab`
  - `sr_weighted_bounce`
  - `sr_weighted_break`
- Added audit/decision artifacts:
  - [SR structural audit](/data/repo/fx-ai-trader/raw/audits/sr-family-structural-audit-2026-06-02.md)
  - [Render env audit](/data/repo/fx-ai-trader/knowledge-base/wiki/decisions/sr-family-render-env-audit-2026-06-02.md)
  - [.ai decisions](/data/repo/fx-ai-trader/.ai/decisions/2026-06-02-sr-break-retest-sr-meta-r3.md)
  - [diagnostics note](/data/repo/fx-ai-trader/knowledge-base/wiki/learning/sr-family-diagnostics-instrumentation-2026-06-02.md)

Verdicts:
- `sr_liquidity_grab`: `NEEDS_MORE_DATA_SIGNAL_PATH`
- `sr_weighted_bounce/break`: `NEEDS_MORE_DATA_DETECTOR_GATE`
- `sr_break_retest`: `CONFIRMED_STRATEGY_METADATA_WIRING_FIXED`

Verification:
- Targeted SR/audit tests: `28 passed`
- `py_compile` on touched strategy modules: passed
- Full suite: `3 failed, 1866 passed, 2 skipped, 1 xfailed`
  - The 3 failures reproduce in isolation and are edge-cell shield logging tests, outside the SR files touched here.

Run verdict: `NEEDS_MORE_EVIDENCE`, because this container lacked `ssh`/`sqlite3`, so direct production DB `evaluated_candidates` SQL and the requested replay-count run could not be completed here. No push to `main` was performed.
```
