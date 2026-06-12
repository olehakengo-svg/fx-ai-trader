# LDN Morning Size Lever - 2026-06-12

## Verdict

Implemented.

LIVE OANDA transfer now applies `0.5x` units only when:

- `edge_cell_id in {"E5", "E7", "E10"}`
- entry UTC hour is `07`, `08`, or `09`
- the trade is on the actual OANDA send path
- `LDN_MORNING_SIZE_LEVER` is not `"0"` (default enabled)

Shadow trades are unchanged. The lever is applied only after final OANDA gates confirm the trade will be sent.

## Code Changes

- `modules/demo_trader.py`
  - Added `LDN_MORNING_SIZE_LEVER_REASON`, target cell set, and target UTC hour set.
  - Added `_resolve_ldn_morning_size_lever(...)`.
  - Applied the lever immediately before OANDA send, after final gate/shadow escalation.
  - Added `[LDN_MORNING_SIZE]` log and `(LDN0.5x)` lot tag when applied.

- `modules/demo_db.py`
  - Added `append_trade_reason(...)` to append audit tags to `demo_trades.reasons` without duplicating them.

- `tests/test_ldn_morning_size_lever.py`
  - Covers E5/E7/E10 x UTC07/08/09.
  - Covers target cell UTC10 unchanged.
  - Covers E9 UTC08 unchanged.
  - Covers `is_shadow=True` unchanged.
  - Covers `LDN_MORNING_SIZE_LEVER=0` unchanged.
  - E2E verifies E5 OANDA units `5000 -> 2500` and `demo_trades.reasons` contains `ldn_morning_size_lever_0.5x`.
  - E2E verifies E9 remains `5000` and has no reason tag.

- `tests/test_edge_cell_force_live_override.py`
  - Updated the E5 force-live expected OANDA units from `5000` to `2500`.
  - E8/E3/E9 expectations remain `5000`.

## Lot Derivation

Order is:

`_PAIR_LOT_BOOST / _STRATEGY_LOT_BOOST -> N cap -> DD multiplier -> aggregate Kelly -> Kelly cap -> PRIME cap -> special fixed lots -> sentinel/FX rounding -> OANDA_FORCE_FLAT_UNITS -> hard cap -> Candidate.lot_multiplier -> final OANDA gates -> LDN morning 0.5x`

The LDN lever is last and LIVE-only, so it does not double-apply with edge-cell stage lots and does not affect shadow records.

## Non-Target Cells

No logic was added for E6, E9, E11, or any non-target cell. E9 is explicitly covered by tests and remains unchanged at UTC08. Existing E8/E3 force-live expectations also remain unchanged.

## Git Verification

`git log --oneline -5` before final update:

```text
7ac1c9e2 chore(codex): claim 20260612-1715-ldn-morning-size-lever
d94da4eb docs(prereg): T8 sweep/hull LIVE 初週監視 pre-reg LOCK (rule:R1 doc only)
3f5ac941 fix(shadow): bb_rsi_reversion consolidation retirement — Edge Factor Audit #2 (rule:R2)
4b40697f docs(tier): tier-master regen — sweep_reversion_eurgbp_late 静的tier反映 (rule:R3 doc)
403bdd98 fix(demo_trader): use module-level datetime in _is_promoted session gate (rule:R3)
```

`git diff` verified changed files:

- `modules/demo_db.py`
- `modules/demo_trader.py`
- `tests/test_edge_cell_force_live_override.py`
- `tests/test_ldn_morning_size_lever.py`
- `final.md`

## Verification

- `.venv/bin/pytest tests/test_ldn_morning_size_lever.py -q`
  - `7 passed`
- `.venv/bin/pytest tests/test_edge_cell_force_live_override.py tests/test_edge_cell_e2e_force_fire.py tests/test_demo_trader_lot_multiplier_integration.py -q`
  - `16 passed`
- `.venv/bin/pytest tests/ -x -q`
  - `1855 passed, 1 skipped, 1 xfailed in 274.88s`
- `.venv/bin/python scripts/check.py`
  - exit 0
  - `全6チェック通過`
  - Existing KB warnings were reported, but the checker verdict was OK.
