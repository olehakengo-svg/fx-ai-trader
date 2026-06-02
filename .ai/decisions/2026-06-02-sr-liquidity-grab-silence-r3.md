---
id: 2026-06-02-sr-liquidity-grab-silence-r3
title: sr_liquidity_grab total silence - structural diagnosis
verdict: NEEDS_MORE_DATA_SIGNAL_PATH
rule: R3
audit_at: 2026-06-02T18:10:00Z
related_artifact: raw/audits/sr-family-structural-audit-2026-06-02.md
---

# Evidence

- Render env flags are `1`, so `H_ENV_OFF` is rejected.
- Local registry check confirms `SrLiquidityGrab` is imported and instantiated
  in `strategies/daytrade/__init__.py`.
- Fresh production API audit still has exact `sr_liquidity_grab` count = 0 in
  `oanda_audit` and closed `demo_trades`.
- `evaluated_candidates` cannot be checked from this Codex container because
  direct SSH/SQLite access is unavailable.

# Code Action

Added V2 diagnostics to `strategies/daytrade/sr_liquidity_grab.py`.

Enable logs with:

```sh
SR_LIQUIDITY_GRAB_DIAG_LOG=1
```

The strategy records per-symbol buckets such as `called`,
`reject_no_sr_levels`, `reject_sr_proximity`, `reject_no_hunt`, `reject_rr`,
`reject_dedup`, and `candidate`.

# Decision

No threshold tuning. Run 24h paper replay or live shadow observation with the
diagnostic flag enabled.

- If `called = 0`, investigate scheduler/runtime registry.
- If `called > 0` and `candidate = 0`, inspect the dominant signal filter.
- If `candidate > 0` but audit remains 0, inspect downstream shadow emit gating.
