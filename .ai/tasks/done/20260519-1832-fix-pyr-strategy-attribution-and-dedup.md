---
id: 20260519-1832-fix-pyr-strategy-attribution-and-dedup
priority: P0
gate: R3
rule: R3
status: queued
created: 2026-05-19
owner: claude
---

# Fix PYR pyramid strategy attribution + dedup + UNKNOWN backfill

priority: P0
rule: R3 (immediate — strategy promote/demote 判断が systematically biased)
gate: N/A (correctness fix, validated by post-fix backfill stats)

## Why this is P0

Live audit of last 30 days (2026-04-19 to 2026-05-19) on Render fx-ai-trader.onrender.com revealed
**15 closed trades with `oanda_trades.strategy=NULL`**, totaling **-4,379 JPY (47% of 30d net loss)**.
These are filled OANDA trades that bypass strategy attribution, making them invisible to:

- per-strategy Wilson lower bound / Bonferroni gate calculations
- Kelly sizing (treated as 0 N for any strategy)
- promote/demote logic (`tier_live_drift.py`, `volume_live_promotion_watchdog.py`)
- Edge audit pipelines (W4-EDA, SR-weight Phase 2, etc.)

Empirical example after Δ<10min nearest-sent-row attribution:

| Strategy | 公式 30d | + UNKNOWN backfill (推定) | 真の 30d | 判断変化 |
|---|---|---|---|---|
| vix_carry_unwind | N=9 WR=66.7% +646 JPY | +5 (-90, -710, -570, +350, +160) | **N=14 / -214 JPY** | 🚨 promote → demote |
| trendline_sweep | N=9 / -87 JPY | +2 (-1119, -266) | **N=11 / -1472 JPY** | 既に赤字、悪化 |

This means the system is currently **promoting losers and demoting winners** based on an
attribution gap that has been silently growing.

## Symptom evidence (live audit 2026-05-19)

UNKNOWN 30d 15 trades classified by mechanism:

**Group A — PYR (pyramid add) with no parent strategy attribution (5+ trades)**:
parent strategy `sent (1000u, 戦略名)` → `filled (1000u, MODE)` → at **same second** another
`filled (10000u, MODE)` is written. The 10000u row is the PYR child created by
`demo_trader.py:2156-2169` via `_pyr_id = f"PYR_{trade_id}"`, but `open_trade()` is called
with `mode=mode` (MODE name) and no `entry_type` parameter, so the audit `bridge_status='sent'`
row for the PYR child either is not written or is written with MODE name instead of parent
strategy name. Result: `oanda_trades.strategy = NULL` after sync.

Example: `oanda_trade_id=403857` (2026-05-18 15:56:26, GBP_USD BUY 10000u, -286.4 JPY).
Within ±15min sent row: `doji_breakout 1000u` at Δ=-317s. PYR child landed without parent name.

**Group B — Same-second duplicate fire (2 pairs = 4 trades)**:
- 2026-04-28 09:34:14: `379982 + 379990 GBP_USD SELL 10000u` (both fillled at Δ=0s)
- 2026-04-28 09:56:31: `380004 + 380010 GBP_USD SELL 10000u` (both filled at Δ=0s)

For 09:34 the nearest sent is `session_time_bias 1000u SELL @ Δ=-641s` (~11 min earlier).
For 09:56 there is NO sent row in ±15 min window. Both pairs show two `filled 10000u` audit
rows at exactly Δ=0s — classic per-call dedup欠落 (memory `rsk bar-close gate 未修正 R3
pending` 同類; vsg-jpy-reversal の per-bar dedup 欠落と同根).

**Group C — Signal-less 10000u fire (2 trades)**:
2026-04-28 09:56:31 pair (380004/380010) — ±15min window has zero `bridge_status='sent'` rows
for instrument GBP_USD. Trades originate from a non-strategy code path. Candidates:
- `demo_trader.py:752` `_units_exp = _ot_exp.get("units", 10000)` (ExposureManager restart)
- `demo_trader.py:752` re-entry / exit-replay path
- `demo_trader.py:4994` `_base_units = int(_os.environ.get("OANDA_UNITS", "10000"))`
- watchdog / sentinel / hourly engine auto-fire

Codex must identify which path fires C-group and either add audit `sent` write or document why.

## Files & line refs

- `modules/demo_trader.py:2140-2175` — PYR pyramid open_trade call site (Group A root cause)
- `modules/demo_trader.py:1686+` — `_sync_oanda_closures` (where filled→oanda_trades sync happens)
- `modules/demo_trader.py:745-760` — ExposureManager DB sync (Group C candidate)
- `modules/demo_trader.py:752` `_units_exp = _ot_exp.get("units", 10000)` (default 10000u)
- `modules/demo_trader.py:4994` / `5209` — `_base_units` env-default 10000u (LIVE base unit)
- `modules/demo_trader.py:3500` — `int(_os_exp.environ.get("OANDA_UNITS", "10000"))`
- `modules/oanda_bridge.py:562` — `_lot_disp = f"{_lot}u({_lot/10000:.2f}lot)"` (display only, ref)
- `modules/oanda_bridge.py` `open_trade()` — entry point for audit write (sent / filled rows)
- `modules/demo_db.py:2107+` — `get_oanda_trades`
- `modules/demo_db.py:355-383` — `oanda_trades` schema (CONFIRMED: has `strategy` column)
- audit table schema (paste schema from existing migrations if needed):
  - oanda_trade_id TEXT
  - instrument TEXT
  - direction TEXT
  - units INT
  - entry_type TEXT  (per memory: `bridge_status='sent'`=戦略名, `'filled'`=MODE 名, twin meaning)
  - bridge_status TEXT (`sent` / `filled` / `skipped`)
  - block_reason TEXT (`shadow_tracking` / empty)
  - is_live BOOLEAN
  - timestamp TEXT (ISO)
  - created_at TEXT
  - sr_* fields (for SR-weight)

## Required changes

### 1. PYR parent strategy attribution (Group A fix)

In `modules/demo_trader.py:2156-2169`:
- Resolve parent trade's strategy at PYR open time (lookup `oanda_trades` / `demo_trades` by `trade_id`)
- Pass parent strategy via a new `entry_type` parameter on `open_trade()`
- Ensure `OandaBridge.open_trade()` writes audit `bridge_status='sent'` row with the parent
  strategy name BEFORE the OANDA execution call

In `modules/oanda_bridge.py` `open_trade()`:
- Accept optional `entry_type` param (default: MODE name like today)
- Write `bridge_status='sent'` row with `entry_type=<parent strategy>` for PYR children
- Write `bridge_status='filled'` row as today (MODE-name keeps current behavior — twin
  meaning is preserved per memory `reference_oanda_audit_twin_meaning.md`)

### 2. PYR per-bar dedup (Group B fix)

In `modules/demo_trader.py` around the PYR call (line ~2130 `_pyr_favorable` check):
- Add per-trade-id-per-bar dedup: if PYR already executed for this `trade_id` in the current
  bar (use `self._pyramided_trades` set is the existing guard — verify it actually fires
  before the second open_trade), block re-fire
- Verify `self._pyramided_trades.add(trade_id)` is BEFORE the `_oanda.open_trade(...)` call,
  not after (current code at line 2170 is AFTER — race-condition possible)
- Add a stricter guard: bail if there's an in-flight PYR for this trade_id (lock or marker)

Empirical evidence: 2026-04-28 09:34:14 and 09:56:31 show two `filled 10000u` rows at exactly
the same second (audit Δ=0s) for the same instrument & direction. The current
`_pyramided_trades.add(trade_id)` on line 2170 happens AFTER the `_oanda.open_trade()` call on
line 2160 — if the trigger fires twice within the same tick (e.g., from 5m and 15m engines
hitting the same parent), both can pass the guard.

### 3. C 群 path identification + audit unification

Trace where 10000u trades originate WITHOUT a preceding strategy sent row. Candidates:
- `demo_trader.py:752` exit-replay default 10000u
- `demo_trader.py:4994` `_base_units` env default
- `demo_trader.py:3500` `OANDA_UNITS` env default

For each path that opens an OANDA trade, ensure `OandaBridge.open_trade()` is called with a
non-empty `entry_type` (either the strategy name or a clearly-labeled non-strategy tag like
`exit_replay` / `exposure_restore` / `manual` / `watchdog`). This lets the `oanda_trades.strategy`
sync logic know whether to backfill from sent or to mark explicitly as non-strategy.

### 4. `oanda_trades.strategy` resolution + backfill

In whatever code writes `oanda_trades.strategy` (search for the SQL that sets that column):
- When syncing a CLOSED OANDA trade, if the existing logic uses filled-row entry_type and gets
  a MODE name, walk back to the nearest `bridge_status='sent'` row within ±5 min for the same
  instrument+direction and use that strategy name instead.
- For backfill: add a one-shot script `tools/backfill_oanda_strategy_2026_05_19.py` that scans
  all existing `oanda_trades` rows where `strategy IS NULL` and applies the same nearest-sent
  resolution rule. Output: rows updated count, distinct strategies recovered, total PnL
  reattributed.

### 5. Tests

Add `tests/test_pyr_attribution.py`:
- Create parent oanda_trade via mocked OandaBridge
- Trigger PYR via `demo_trader._pyramid_trade_if_favorable` (or whatever the method is)
- Assert audit has TWO `sent` rows: one for parent strategy (1000u), one for PYR child
  (10000u) — both with `entry_type=<strategy_name>` not MODE name
- Assert `_pyramided_trades` is populated BEFORE second OANDA call (race fix)
- Simulate same-second double-fire and assert only one PYR open is sent to OANDA
- Assert `oanda_trades.strategy` ends up populated with parent strategy after sync

Add `tests/test_oanda_strategy_nearest_sent_resolution.py`:
- Insert `bridge_status='sent'` row at T-30s with `entry_type=vix_carry_unwind`
- Insert `bridge_status='filled'` row at T=0 with `entry_type=daytrade` (MODE), units=10000
- Run sync logic
- Assert `oanda_trades.strategy = vix_carry_unwind` (resolved from sent, not filled)

## Acceptance criteria

1. After deploy, `/api/oanda/stats?range=30d` → run backfill script → re-query → fewer
   UNKNOWN trades, more strategies populated. Report old vs new for each strategy.
2. New tests pass: `python3 -m pytest tests/test_pyr_attribution.py tests/test_oanda_strategy_nearest_sent_resolution.py -v`
3. Full suite: `python3 -m pytest tests/ -x -q` (1518+ existing pass)
4. `scripts/check.py`: 6/6 pass
5. No regressions in `oanda_audit` schema (twin meaning preserved per memory)
6. Backfill script reports total trades reattributed and per-strategy PnL deltas
7. Codex final report includes table: **strategy | old N | new N | old EV | new EV | delta**
   for at least vix_carry_unwind, trendline_sweep, doji_breakout, gbp_deep_pullback,
   session_time_bias (the strategies most affected by attribution gap)

## Out of scope (explicitly NOT do)

- DO NOT modify pyramid trigger condition (`_pyr_favorable` ATR-based criterion).
- DO NOT change PYR units default 10000 — that's a separate sizing question.
- DO NOT modify oanda_audit twin-meaning convention (memory: bridge_status='sent'=戦略名 /
  'filled'=MODE 名 is intentional and consumed elsewhere).
- DO NOT touch OANDA bridge heartbeat / shadow_tracking — orthogonal issue.

## Memory references

- `feedback_live_shadow_separation.md` (2026-04-30) — Live/Shadow分離が必要、景色反転事例
- `feedback_label_empirical_audit.md` — ラベル実測主義 (本件 attribution gap がこれの violation)
- `oanda_audit.entry_type 二義性` — `bridge_status='sent'`=戦略名 / `'filled'`=MODE 名。PYR は filled のみで親解決が要 (まさにこの事例)
- `rsk bar-close gate 未修正 R3 pending` (2026-04-30) — vsg と同根、per-bar dedup 欠落で 76 件 runaway。Group B はこれと同類
- `feedback_codex_stash_leak.md` — Codex 実装後の verify は `git stash list`/`git diff` 必須

## Verification (Codex must run before reporting done)

```bash
python3 -m pytest tests/test_pyr_attribution.py tests/test_oanda_strategy_nearest_sent_resolution.py -v
python3 -m pytest tests/ -x -q
python3 scripts/check.py
python3 tools/backfill_oanda_strategy_2026_05_19.py --dry-run    # report what WOULD change
python3 tools/backfill_oanda_strategy_2026_05_19.py --apply       # apply
git diff --stat HEAD
git status
```

All must pass. Final.md MUST include the **strategy old-vs-new comparison table**
(acceptance criterion 7) — that is the quant proof the fix worked.


## Result (2026-05-29T08:26:15Z)

exit=0 · 230s

```
Implemented the PYR attribution/dedup correction.

Changes:
- [modules/oanda_bridge.py](/data/repo/fx-ai-trader/modules/oanda_bridge.py:511): `open_trade()` accepts `entry_type` for strategy-labeled `sent` audit rows before broker execution.
- [modules/oanda_bridge.py](/data/repo/fx-ai-trader/modules/oanda_bridge.py:667): `filled` rows now preserve the OANDA mode label, keeping the audit twin-meaning invariant intact.
- [modules/demo_trader.py](/data/repo/fx-ai-trader/modules/demo_trader.py:741): added `_pyramid_inflight`.
- [modules/demo_trader.py](/data/repo/fx-ai-trader/modules/demo_trader.py:2218): PYR now reserves `_pyramid_inflight` and `_pyramided_trades` under lock before SL move / broker open, blocking same-second double-fire.
- [modules/demo_trader.py](/data/repo/fx-ai-trader/modules/demo_trader.py:2261): PYR child passes parent `entry_type` to bridge.
- [tests/test_pyr_attribution.py](/data/repo/fx-ai-trader/tests/test_pyr_attribution.py:36): tests now assert PYR child attribution, in-flight marker timing, dedup, and audit twin meaning.

C-group path check:
- `_oanda.open_trade()` call sites are main entry, resend pending, and PYR.
- ExposureManager restart sync at line ~752 does not open OANDA trades; it only restores exposure state.
- Main entry writes its own `sent` audit row with strategy and calls bridge with `skip_sent_audit=True`.
- Resend pending now passes `entry_type` or `resend_pending`.
- PYR now passes parent strategy.

Verification:
- `.venv/bin/python -m pytest tests/test_pyr_attribution.py tests/test_oanda_strategy_nearest_sent_resolution.py -v`: 5 passed.
- `.venv/bin/python -m pytest tests/test_oanda_strategy_chain_resolution.py tests/test_oanda_audit_join_invariant.py tests/test_pyr_attribution.py tests/test_oanda_strategy_nearest_sent_resolution.py -q`: 14 passed.
- `.venv/bin/python -m pytest tests/ -x -q`: stopped on missing fixture `data/cache/massive/USD_JPY_5m.parquet`; 88 passed, 1 skipped b
…(truncated)
