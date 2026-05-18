# Lesson: PRIME gate order bug (2026-05-18)

## Observation

Pre-registered PRIME A/B cells were classified correctly, but later safety gates
(`EMERGENCY_TRIP`, Q4 gate, fallback shadow) could still set `_is_shadow=True`
before the PRIME override ran. The override required `not _is_shadow`, so PRIME
A/B became dead code even though `classify_prime()` fired.

## Rule

When adding a new safety gate after a pre-registered promotion path, explicitly
define precedence against every existing live path:

- ELITE_LIVE
- PAIR_PROMOTED
- GRAIL / C1 sentinel promotions
- PRIME A/B
- Tier C / shadow-only variants

Do not rely on a later override to recover from an earlier `_is_shadow=True`
write unless the override is intentionally allowed to clear shadow state.

## Implementation Pattern

Use an explicit lock flag for binding promotions:

```python
_prime_live_lock = bool(_prime_match and _prime_match.get("tier") in ("A", "B"))
```

Then each later gate must decide whether it respects that lock. For PRIME:

- A/B bypass emergency trip, Q4, fallback shadow, and Phase0.
- Tier C does not bypass and remains shadow-only.
- A kill-switch (`PRIME_OVERRIDE_ENABLED=0`) must disable the lock without
  changing the pure classifier or pre-registered thresholds.

## Review Checklist

Before merging a new gate, verify:

- Does it run before or after every pre-registered live promotion?
- Does it set `_is_shadow` or `_is_promoted`?
- Can a later path safely reverse it, or should the gate itself exempt the live path?
- Are shadow/live persistence fields updated after the final state?
- Is the gate covered by at least one regression test for promoted and non-promoted cells?
