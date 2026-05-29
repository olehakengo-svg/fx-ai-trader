---
id: 20260527-0230-sentinel-silent-block-instrumentation
priority: P0
gate: R3
rule: R3
status: queued
created: 2026-05-27
owner: claude
---

# Identify SENTINEL silent _block between Sentinel bypass (L3479) and MTF_MONITOR (L4196)

priority: P0
rule: R3 (immediate — Cluster A 15 SENTINEL strategies show MTF_MONITOR-pre signals dying in silent block, shadow.n permanently 0)
gate: N/A (instrumentation + diagnosis task; no algorithmic gate change in this task)

## Why this is P0 (post P0-1 deploy verification finding)

Post-deploy of commit `b8833bd3` (P0-1 fix: `_should_audit_shadow_emit` sr_-only restriction
removed) on 2026-05-26 ~16:55 UTC, production verification at 17:28 UTC shows:

**Cluster A SENTINEL strategies (15 strategies) all still shadow.n=0**:

| Strategy | tier | shadow.n |
|---|---|---|
| eurgbp_daily_mr | UNIVERSAL_SENTINEL | 0 |
| gotobi_fix, liquidity_sweep, ... (UNIVERSAL_SENTINEL ×9) | | 0 |
| bb_rsi_ema_aligned, ma_mr_hybrid, ... (SCALP_SENTINEL ×4) | | 0 |
| kalman_d7_{ema75_break,po_dn_flip,trail_atr} | UNIVERSAL_SENTINEL | 0 |

**Cluster C Phase B-1**: only `price_shock_rev_aud_jpy_h1_long` and `price_shock_rev_eur_gbp_h1_long` at N=1 (unchanged from pre-deploy).

Render log inspection (resource: `srv-d6va1of5r7bs73en10vg`) of `eurgbp_daily_mr` 17:08-17:30
UTC shows the same pattern repeats every 10-30 seconds:

```
[SCORE_GATE] Sentinel bypass: eurgbp_daily_mr score=0.32 misaligned with SELL | EUR_GBP daytrade_eurgbp (is_shadow will be enforced)
(no subsequent log for this strategy/instance)
```

**No `[MTF_MONITOR] EUR_GBP entry=eurgbp_daily_mr ...` log appears.**
**No `[REGIME] SQUEEZE detected — MR Blocked` log appears.**
**No `[SHADOW] GBP Asia bypass: eurgbp_daily_mr` log appears.**
**No `[REGIME] DT RANGE blocked: eurgbp_daily_mr` log appears.**
**No `🔗 OANDA: [SKIP] eurgbp_daily_mr — Reason: ...` log appears.**

This means signals are dying via a **silent `_block(reason)` call** (no log emitted, only
`_block_counts[k] += 1` per `modules/demo_trader.py:3423-3428`) somewhere in the gate stack
between line 3479 (Sentinel bypass log emission) and line 4196 (MTF_MONITOR log emission).

The P0-1 fix to `_should_audit_shadow_emit` does NOT help because
`_open_shadow_emit_trade()` is never reached — the signal is dropped earlier in
`_tick_entry()`.

## Investigation deliverables

### Step 1: Expose `_block_counts` for diagnosis

Add a read-only endpoint (or extend an existing one) that returns the current
`_demo_trader._block_counts` dict, broken down by mode×reason. Suggested:

```python
@app.route("/api/demo/block-counts")
def api_demo_block_counts():
    """Return _block_counts dict from _tick_entry gate evaluation."""
    if not hasattr(_demo_trader, "_block_counts"):
        return jsonify({"counts": {}, "total": 0})
    counts = dict(_demo_trader._block_counts)
    return jsonify({"counts": counts, "total": sum(counts.values())})
```

This is read-only and safe. Document in CLAUDE.md or analyses/.

### Step 2: Per-strategy block accounting

`_block_counts` keys are currently `f"{mode}:{reason.split('(')[0]}"`. This loses strategy
attribution. Extend to also track per-strategy:

```python
def _block(reason):
    k_mode = f"{mode}:{reason.split('(')[0]}"
    self._block_counts[k_mode] = self._block_counts.get(k_mode, 0) + 1
    # NEW: per-strategy attribution for SENTINEL diagnosis
    k_strat = f"{entry_type}:{reason.split('(')[0]}"
    self._block_counts_per_strategy = getattr(self, "_block_counts_per_strategy", {})
    self._block_counts_per_strategy[k_strat] = self._block_counts_per_strategy.get(k_strat, 0) + 1
    return
```

Expose via `/api/demo/block-counts?strategy=eurgbp_daily_mr` parameter.

### Step 3: Force-log block for SENTINEL strategies

Add a debug log emission in `_block()` when the strategy is in
`_UNIVERSAL_SENTINEL | _SCALP_SENTINEL`:

```python
def _block(reason):
    k = f"{mode}:{reason.split('(')[0]}"
    self._block_counts[k] = self._block_counts.get(k, 0) + 1
    # NEW: SENTINEL diagnostic — these strategies are expected to reach shadow_emit
    # but currently silently dropped. Force-log to identify the gate.
    if entry_type in self._UNIVERSAL_SENTINEL or entry_type in self._SCALP_SENTINEL:
        self._add_log(f"[SENTINEL_BLOCK_DIAG] {entry_type} blocked at: {reason}")
    return
```

This is observation-only; does NOT change gate behavior. Time-bounded: remove after diagnosis
(Codex must include rollback instructions).

### Step 4: Diagnose & report

After deploy of steps 1-3, monitor Render logs for 30-60 minutes and capture:

- Which specific `reason` kills `eurgbp_daily_mr` after Sentinel bypass?
- Are all 15 Cluster A strategies dying at the same gate, or different ones?
- Does the gate name align with any known design intent (squeeze block? range gate? GBP Asia?
  or something unexpected)?

Produce a report in `final.md`:

- Per-strategy gate diagnosis table
- Root cause hypothesis (which gate is the right one to fix)
- Recommended P0-4 follow-up task spec (instrumentation removal + actual gate fix)

## Files & line refs

- `modules/demo_trader.py:3423-3428` — `_block()` definition (instrument)
- `modules/demo_trader.py:3479-3482` — Sentinel bypass log emission (entry point of trace)
- `modules/demo_trader.py:4196` — MTF_MONITOR log emission (exit point if successful)
- Between 3482 and 4196 — ~700 lines of gate code (the suspect range)
- `app.py:13823+` — endpoints area (add new diagnostic endpoint here)
- `modules/demo_trader.py:7119-7176` — `_UNIVERSAL_SENTINEL`, `_SCALP_SENTINEL` sets

## Validation

1. **Pre-deploy local**: pytest baseline + post-instrumentation, no new failures.
2. **Post-deploy probe**:
   ```bash
   curl -s 'https://fx-ai-trader.onrender.com/api/demo/block-counts' | jq .
   ```
3. **Per-strategy probe**:
   ```bash
   curl -s 'https://fx-ai-trader.onrender.com/api/demo/block-counts?strategy=eurgbp_daily_mr' | jq .
   ```
4. **Render log search** (30-60 min after deploy):
   `[SENTINEL_BLOCK_DIAG] eurgbp_daily_mr blocked at: <reason>`
5. **Pre-reg**: by `2026-05-27 12:00 UTC` (12 hours post-deploy) we should have at least 50
   `SENTINEL_BLOCK_DIAG` log entries for `eurgbp_daily_mr`. If 0 — the strategy isn't even
   reaching `_block()` (means it's dying at the Sentinel bypass log point or before, which
   contradicts our current evidence; trigger a different investigation).

## Out of scope (do NOT do)

- Do NOT change gate behavior or thresholds in this task — diagnose only.
- Do NOT touch `_tick_entry` flow logic, only add instrumentation.
- Do NOT remove the P0-1 commit `b8833bd3` — it's still correct for the
  `_open_shadow_emit_trade` path, just doesn't help Cluster A SENTINEL.
- Do NOT change `_UNIVERSAL_SENTINEL` / `_SCALP_SENTINEL` membership.

## Commit message template

```
feat(diag): expose _block_counts + SENTINEL block-point logging [rule:R3]

Post-deploy of b8833bd3 shows Cluster A SENTINEL strategies (eurgbp_daily_mr
et al.) still at shadow.n=0 because signals are killed by silent _block()
between Sentinel bypass (L3479) and MTF_MONITOR (L4196). The P0-1 audit gate
fix doesn't help here because _open_shadow_emit_trade() is never reached.

Add:
- /api/demo/block-counts endpoint (read-only)
- Per-strategy block_counts tracking
- [SENTINEL_BLOCK_DIAG] force-log for SENTINEL strategies

This is observation-only. After diagnosis (P0-4), instrumentation removed
or downgraded.

Refs: ai/tasks queue 20260527-0230

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

## Acceptance

Codex returns:
- Diff of `app.py` (new endpoint) and `modules/demo_trader.py` (instrumentation)
- Pytest output showing no regressions
- Deploy plan + log monitoring protocol
- After 30-60 min monitoring: `final.md` with per-strategy gate diagnosis table for at least
  `eurgbp_daily_mr` + 2 other Cluster A strategies
- Follow-up P0-4 task spec draft to actually FIX the identified gate (handle by Sentinel
  bypass path)
