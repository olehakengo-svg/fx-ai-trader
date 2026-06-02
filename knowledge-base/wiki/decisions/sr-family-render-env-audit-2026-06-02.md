---
id: sr-family-render-env-audit-2026-06-02
title: SR Family Render Env Audit - Redacted
verdict: ACCEPT_ENV_ON
rule: R3
audit_at: 2026-06-02T18:10:00Z
auditor: Claude commander SSH audit, recorded by Codex
---

# Scope

Read-only Render environment audit for SR-family shadow flags. Values are
recorded only as `1` / `0` / `set` / `unset`; no secrets are included.

# Result

| key | redacted_state |
|---|---|
| SR_LIQUIDITY_GRAB_REDESIGN_V2 | 1 |
| SR_LIQUIDITY_GRAB_REDESIGN_V2_SHADOW_PROMOTE | 1 |
| SR_WEIGHTED_BOUNCE_ENABLE | 1 |
| SR_WEIGHTED_BOUNCE_SHADOW_PROMOTE | 1 |
| SR_WEIGHTED_BREAK_ENABLE | 1 |
| SR_WEIGHTED_BREAK_SHADOW_PROMOTE | 1 |
| SR_ANTI_HUNT_BOUNCE_REDESIGN_V2 | 1 |
| SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE | 1 |
| SR_BREAK_RETEST_REDESIGN_V2 | 1 |
| SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE | 1 |
| SR_FIB_CONFLUENCE_REDESIGN_V2 | 1 |
| SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE | 1 |

# Decision

`H_ENV_OFF` is rejected for the three SR structural defects. Remaining
diagnosis must focus on signal generation, detector output, and candidate
metadata wiring.

# Tooling Note

This Codex container did not have `ssh` or `sqlite3` in PATH, so Codex did not
re-run the SSH command. The table records the commander audit already performed
for service `srv-d6va1of5r7bs73en10vg`.
