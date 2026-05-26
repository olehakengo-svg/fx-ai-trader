---
id: 20260526-1130-edge-cells-stage3-live-promote
title: Edge-Cell Stage-3 Direct LIVE Promotion — implement promote engine + watchdog
status: queued
priority: P1
rule: R1-EXCEPTION
gate: pre-reg-LOCK
created: 2026-05-26
owner: codex-cloud
type: feature-implementation
estimated_minutes: 90
---

# Edge-Cell Stage-3 Direct LIVE Promotion

priority: P1
rule: R1-EXCEPTION (intentional shadow-first exception, user judgment)
gate: pre-reg LOCK at `knowledge-base/wiki/decisions/edge-cells-stage3-live-promote-2026-05-26.md`
status: queued

## Context

Pre-reg LOCK doc:
`knowledge-base/wiki/decisions/edge-cells-stage3-live-promote-2026-05-26.md`

Source data: Render `/api/demo/trades` is_shadow=1, 2026-05-06 → 2026-05-26 (N=1,795 closed shadow trades). Analysis identified **12 edge cells** with Wilson_lo ≥ 0.30, union N=156, WR=57.7%, EV=+13.45p win / -6.10p loss, R:R=2.21.

User instruction: skip Stages 0-2 (forward shadow / micro-live) and start at Stage 3 with Kelly Half haircut. Lot ladder S1=5,000 → S2=7,500 → S3=10,000 units. Withdrawal triggers (DD>5%, PF<1.0, WR<28%, account DD>8%) executed automatically by a new 15-min cron watchdog.

This is the **same pattern as Kalman D7 (2026-05-20) and vix_carry 1.0x exception (2026-05-21)** — shadow-first paradigm の意図的例外。

## Task

Implement 7 deliverables. Code-level details follow.

### D1. `modules/edge_cell_promote.py` (NEW)

Define 12 cell filters and matching/lot-selection logic.

```python
# modules/edge_cell_promote.py
"""Edge cell matching for Stage-3 direct LIVE promotion.

Spec: knowledge-base/wiki/decisions/edge-cells-stage3-live-promote-2026-05-26.md
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

# Session bounds (UTC) — LOCK
def session_of(ts: datetime) -> str:
    h = ts.astimezone(timezone.utc).hour
    if 0 <= h < 7:   return "ASN"
    if 7 <= h < 13:  return "LDN"
    if 13 <= h < 21: return "NY"
    return "LATE"

@dataclass(frozen=True)
class EdgeCell:
    cell_id: str
    filters: dict  # keys: strategy, symbol, session, direction, v2_regime, mtf_gate_action
    base_lot: int = 5000  # S1 baseline, can be overridden by ladder state in system_kv

EDGE_CELLS: list[EdgeCell] = [
    EdgeCell("E1",  {"strategy":"dt_bb_rsi_mr","session":"ASN","direction":"SELL"}),
    EdgeCell("E2",  {"strategy":"session_time_bias","symbol":"EUR_USD","session":"LDN","mtf_gate_action":"live_tier_exempt"}),
    EdgeCell("E3",  {"strategy":"dt_bb_rsi_mr","symbol":"EUR_USD","direction":"SELL"}),
    EdgeCell("E4",  {"strategy":"bb_rsi_reversion","session":"NY","direction":"SELL"}),
    EdgeCell("E5",  {"strategy":"dt_bb_rsi_mr","symbol":"GBP_USD","direction":"SELL"}),
    EdgeCell("E6",  {"strategy":"rsk_gbpjpy_reversion","symbol":"GBP_JPY","direction":"BUY"}),
    EdgeCell("E7",  {"strategy":"dt_bb_rsi_mr","symbol":"GBP_USD","session":"ASN"}),
    EdgeCell("E8",  {"strategy":"session_time_bias","symbol":"EUR_USD","session":"LDN"}),
    EdgeCell("E9",  {"strategy":"orb_trap","symbol":"GBP_USD","direction":"SELL"}),
    EdgeCell("E10", {"strategy":"wick_imbalance_reversion","symbol":"GBP_USD","v2_regime":"no_go"}),
    EdgeCell("E11", {"strategy":"dt_bb_rsi_mr","session":"NY","direction":"SELL"}),
    EdgeCell("E12", {"strategy":"sr_anti_hunt_bounce","symbol":"EUR_JPY"}),
]

LADDER_LOTS = {1: 5000, 2: 7500, 3: 10000}  # S1, S2, S3
DISABLED_STAGE = 0  # shadow-only fallback

def match(*, strategy: str, symbol: str, entry_time: datetime,
          direction: str, v2_regime: str = "", mtf_gate_action: str = "") -> Optional[EdgeCell]:
    """Return first matching cell (priority E1 > E2 > ... > E12) or None."""
    sess = session_of(entry_time)
    for cell in EDGE_CELLS:
        ok = True
        for k, v in cell.filters.items():
            if k == "strategy" and strategy != v: ok = False; break
            if k == "symbol" and symbol != v: ok = False; break
            if k == "session" and sess != v: ok = False; break
            if k == "direction" and direction != v: ok = False; break
            if k == "v2_regime" and v2_regime != v: ok = False; break
            if k == "mtf_gate_action" and mtf_gate_action != v: ok = False; break
        if ok:
            return cell
    return None

def get_cell_lot(cell_id: str, demo_db) -> int:
    """Read ladder stage from system_kv, return units. 0 = disabled."""
    key = f"edge_cell_stage:{cell_id}"
    raw = demo_db.kv_get(key, default="1")  # default stage S1
    try:
        stage = int(raw)
    except (TypeError, ValueError):
        stage = 1
    if stage == DISABLED_STAGE:
        return 0
    return LADDER_LOTS.get(stage, 5000)
```

### D2. `modules/demo_trader.py` PATCH

Locate the function that handles each new signal (search for `_pair_promoted_check` or the Tier gate evaluation). **Before** the existing Tier gate, insert:

```python
from modules import edge_cell_promote
cell = edge_cell_promote.match(
    strategy=entry_type,
    symbol=instrument,
    entry_time=entry_time,
    direction=direction,
    v2_regime=v2_regime or "",
    mtf_gate_action=mtf_gate_action or "",
)
if cell is not None:
    cell_lot = edge_cell_promote.get_cell_lot(cell.cell_id, _demo_db)
    if cell_lot > 0:
        # force-live promotion: bypass Tier gate and MTF gate
        units = cell_lot
        force_live = True
        edge_cell_id = cell.cell_id
        # skip remaining gate checks, go straight to OANDA submit
        # (preserve existing spread/dedup guards — only bypass Tier/MTF)
```

**Critical**: bypass only **Tier gate** and **MTF gate**. Keep:
- Spread/SL Gate (動的デスゾーン検出, 4原則#2 per CLAUDE.md)
- Per-bar dedup (vsg/rsk bug history per memory)
- account DD guards (existing _ACCOUNT_DD_LIMIT)

Pass `entry_type` + `edge_cell_id` through to `_demo_db.add_trade()` (新規 column).

### D3. DB migration: add `edge_cell_id` to `demo_trades`

```sql
ALTER TABLE demo_trades ADD COLUMN edge_cell_id TEXT DEFAULT '';
CREATE INDEX IF NOT EXISTS idx_trades_edge_cell ON demo_trades(edge_cell_id);
```

Migration file: `migrations/2026_05_26_edge_cell_id.py` following existing migration pattern (search for `migrate_seed.py` and `*alter*` to find the convention).

**WARNING**: Migration must be idempotent (re-runnable). Use `PRAGMA table_info(demo_trades)` to check column existence before ALTER.

### D4. `tools/edge_cell_watchdog.py` (NEW)

Template: copy structure from `tools/volume_live_promotion_watchdog.py`. 15-min cron. Logic:

1. Fetch `/api/demo/trades?limit=10000&date_from=2026-05-26` (LOCK date).
2. Filter to **Live** trades (is_shadow=0) only — **CRITICAL** per [LIVE/Shadow 分離必須](memory).
3. Per cell_id, compute: N, wins, WR, EV(pips), PF, 5d rolling DD.
4. Apply withdrawal logic:
   - PF<1.0 (N≥10) OR 5d DD>5% → `_decrement_stage(cell_id)` (S3→S2→S1)
   - WR<28% (N≥10) OR EV<-1.0p (N≥10) OR 単日 cell pnl_jpy_sum<-6,822 → `_disable_cell(cell_id)` (set stage=0)
   - 7d 連続 N=0 → cell pause (alert only, no auto-disable)
5. Global check: account 30d DD>8% → set `_disable_all_cells()`.
6. Write decision log to `knowledge-base/raw/audits/edge-cell-watchdog/YYYY-MM-DD.json`.
7. Post Discord notification on **state change only** (not every run).

Stage state persisted in `system_kv` table:
- `edge_cell_stage:E1` = "1" / "2" / "3" / "0" (disabled)
- `edge_cell_stage_changed_at:E1` = ISO timestamp
- `edge_cell_disabled_reason:E1` = "WR_BELOW_28" / "EV_NEGATIVE" / etc.

CLI:
```
python3 tools/edge_cell_watchdog.py --api https://fx-ai-trader.onrender.com [--apply] [--to-discord]
```
- Default `--dry-run` (no KV writes). Cron uses `--apply --to-discord`.

### D5. `render.yaml` cron addition

```yaml
- type: cron
  name: fx-ai-edge-cell-watchdog
  runtime: python
  buildCommand: pip install -r requirements.txt
  startCommand: python3 tools/edge_cell_watchdog.py --apply --to-discord
  schedule: "3,18,33,48 * * * *"  # 15-min offset from existing crons
  envVars:
    - fromGroup: fx-ai-trader-env  # if exists; else inline
```

Verify no slot collision with `*/15`-class crons (existing: anomaly_watcher `*/15 * * * *`). Use `:03/:18/:33/:48` offset.

### D6. `tests/test_edge_cell_promote.py` (NEW)

Test cases (E2E force-fire, **not** mock-only per [feedback_codex_mock_test_trap](memory)):
1. `match()` correctness for all 12 cells (fixture trade per cell, expect cell_id).
2. Priority: a trade matching multiple cells (e.g. dt_bb_rsi_mr/GBP_USD/SELL during ASN → matches E1 first, not E5 or E7).
3. Non-match: a wick_imbalance_reversion/GBP_USD/v2_regime=moderate_trend → None.
4. `get_cell_lot()` ladder transitions: S1=5000, S2=7500, S3=10000, disabled=0.
5. **E2E**: spin up a fake `_demo_db` in-memory, push a synthetic signal that matches E3, assert `demo_trader._handle_signal()` calls OANDA bridge with 5000 units and `edge_cell_id="E3"` (use bridge mock at *boundary*, not strategy logic). Mark this test skip-if-no-OANDA-mock-bridge available.

### D7. `wiki/index.md` + `wiki/tier-master.md` UPDATE

Add a new "Stage-3 Edge Cells" section listing E1-E12 with current stage, link to LOCK doc. Tier-master entry per cell.

## Constraints

- **MASSIVE parquet 必須** for any BT validation if needed: data/cache/massive/*.parquet ([feedback_bt_must_use_massive](memory))
- **demo_trades schema (current, LOCK)**:
  ```
  CREATE TABLE demo_trades (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      trade_id TEXT UNIQUE,
      status TEXT DEFAULT 'OPEN',
      direction TEXT,
      entry_price REAL, entry_time TEXT, exit_price REAL, exit_time TEXT,
      sl REAL, tp REAL, pnl_pips REAL, pnl_r REAL,
      outcome TEXT, entry_type TEXT, confidence INTEGER, tf TEXT DEFAULT '15m',
      reasons TEXT, regime TEXT, layer1_dir TEXT, score REAL, close_reason TEXT,
      ema_conf INTEGER, sr_basis REAL, created_at TEXT DEFAULT (datetime('now')),
      mode TEXT DEFAULT '', oanda_trade_id TEXT DEFAULT '',
      instrument TEXT DEFAULT 'USD_JPY', signal_price REAL DEFAULT 0,
      spread_at_entry REAL DEFAULT 0, spread_at_exit REAL DEFAULT 0,
      slippage_pips REAL DEFAULT 0, cooldown_elapsed REAL DEFAULT 0,
      close_analysis TEXT DEFAULT '', mafe_adverse_pips REAL DEFAULT 0,
      mafe_favorable_pips REAL DEFAULT 0, is_shadow INTEGER DEFAULT 0,
      mtf_regime TEXT DEFAULT '', mtf_d1_label INTEGER DEFAULT 3,
      mtf_h4_label INTEGER DEFAULT 3, mtf_vol_state TEXT DEFAULT '',
      gate_group TEXT DEFAULT '', mtf_alignment TEXT DEFAULT '',
      mtf_gate_action TEXT DEFAULT '', alpha_snapshot TEXT DEFAULT '',
      dedup_violation INTEGER DEFAULT 0, flag_drift_backfilled INTEGER DEFAULT 0,
      force_demoted_live_leak INTEGER DEFAULT 0, dow_regime TEXT,
      v2_regime TEXT, confluence_score TEXT, confluence_details TEXT
      -- NEW: edge_cell_id TEXT DEFAULT ''
  );
  ```
- **system_kv schema**: `(key TEXT PRIMARY KEY, value TEXT DEFAULT '')`.
- **No prod data writes from tests** — tests must use in-memory or `tests/fixtures/*.db`.
- **Repo persistence verified** ([feedback_codex_stash_leak](memory)): final.md must include `git log -5 --oneline` AND `git diff --stat origin/main..HEAD` proving the diff is on a real branch, not stashed.
- **No `--apply` of watchdog in CI** — watchdog `--apply` runs only as the Render cron after merge.

## Acceptance criteria (verification matrix)

| Item | Pass condition |
|---|---|
| D1 import OK | `python3 -c "from modules.edge_cell_promote import match, EDGE_CELLS; assert len(EDGE_CELLS)==12"` |
| D2 patch | `grep -n "edge_cell_promote.match" modules/demo_trader.py` returns at least 1 line |
| D3 migration | After running migration on a fresh demo_trades.db, `sqlite3 demo_trades.db ".schema demo_trades" \| grep edge_cell_id` non-empty |
| D4 watchdog dry-run | `python3 tools/edge_cell_watchdog.py --dry-run` exits 0, prints per-cell stats, no Discord call |
| D5 render.yaml | YAML parses, schedule slot non-conflicting |
| D6 tests | `pytest tests/test_edge_cell_promote.py -x` all green (≥10 tests, ≥1 E2E) |
| D7 KB | `wiki/index.md` shows "Stage-3 Edge Cells" section, links resolve |
| Pre-commit | `python3 scripts/check.py` exits 0 |

## Forbidden actions

- Do **NOT** auto-`--apply` the watchdog in CI or in this Codex run.
- Do **NOT** flip any cell to stage=3 by default. **Initial state = S1 (5000 units) for all 12 cells**.
- Do **NOT** modify the existing Tier gate or MTF gate logic. The edge_cell_promote path **adds** a new pre-gate, leaving the existing gate untouched for non-matching signals.
- Do **NOT** modify watchdog cells lists outside `tools/edge_cell_watchdog.py`. (volume_live_promotion_watchdog, post_promotion_watchdog stay as-is.)
- Do **NOT** push secrets, OANDA tokens, or `.env`.
- Do **NOT** create or merge a PR. Push to a branch named `feat/edge-cells-stage3-2026-05-26` and let claude review the diff before merge.

## Output expectations

`final.md` must include:

1. **Diff verification**:
   - `git log --oneline -5` (proves commits are real, not stashed)
   - `git diff --stat main..feat/edge-cells-stage3-2026-05-26`
   - List of new files / modified files
2. **Test output**:
   - Full pytest output for `test_edge_cell_promote.py`
   - `scripts/check.py` output
3. **Migration check**:
   - Output of `sqlite3 <test-db> ".schema demo_trades" | grep edge_cell_id`
4. **Watchdog dry-run sample**:
   - Sample JSON from `tools/edge_cell_watchdog.py --dry-run` against current Render API
5. **Sign-off checklist** copied from LOCK doc with timestamps.
6. **Branch URL** (GitHub URL of the branch tip, not a PR).

## Post-merge follow-ups (out of scope for this task)

- Manual: claude reviews diff → user signs off → merge to main → Render auto-deploy.
- Manual: Verify watchdog cron first run (Render dashboard).
- Day-1 monitor: 24h after deploy, check `edge_cell_stage:*` KV values and Discord notifications.
- Day-7 review: spawn `edge-cell-stage3-w1-review` task.
- Day-28 (2026-06-23): full evaluation per LOCK success criteria.

## Quant checkpoints

- Wilson_lo per cell (Live trades after deploy) re-computed at W1, W2, W4.
- account DD baseline at LOCK time: report this in final.md (read from `/api/risk/dashboard`).
- N target by W4: union N ≥ 60 (currently 156 shadow, expect ~30% fire rate in live = 47 → conservative 60 over 4 weeks).
