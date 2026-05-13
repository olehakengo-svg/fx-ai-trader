# C2 vix_carry_unwind × USD_JPY × Overlap Re-promote Pilot Pre-Registration (2026-05-13)

## Status
**rule:R2 (Fast & Reactive exploration with R1-spirit guardrails)** — pre-reg LOCK at 2026-05-13 18 UTC.
0.05x defensive-minimum lot exploration pilot, Overlap (12-16 UTC) session-conditional.
**Implementation applied 2026-05-13 (user GO):** `modules/demo_trader.py` 5 spots edited
(remove from `_PAIR_DEMOTED`, add to `_PAIR_PROMOTED`, new `_PAIR_SESSION_FILTER` +
`_SESSION_BOUNDS_UTC`, session gate in `_promotion_allows_live`, `_PAIR_LOT_BOOST=0.05`).
Verification: `scripts/check.py` ✓ / `tier_integrity_check.py --check` ✓ /
`sync_kb_index.py --check` ✓ / `pytest tests/` 1458 passed.

## Why this is R2 exploration (NOT an R1 re-promotion)

R1 evidence requirements (Live N≥30 + Bonferroni + 365d BT gate PASS) are **not met**. This is a bounded-risk exploration bet under R2 規律, with R1-style pre-reg LOCK and demote insurance as guardrails.

### Three evidence layers (triangulation)

**1. 365d BT (cell-conditional, 2026-05-13 run)**
- vix_carry_unwind × USD_JPY aggregate: N=107 WR=72.9% EV=+0.74 PF=1.81
- Overlap cell: **N=22 WR=81.8% EV=+1.297** ← target (under R1 N≥30)
- London cell (original 2026-05-13 pre-reg target): N=18 WR=72.2% EV=+0.76 — gate **FAIL** (N<30)
- Asia: N=49 EV=+0.46 / NY: N=18 EV=+0.83 (positive aggregate)
- Source: `knowledge-base/raw/bt-results/cell-promotion-2026-05-13.json`

**2. Production Live (post-FLAG-DRIFT + FORCE-DEMOTED clean cohort)**
- vix×USD_JPY total: **N=11 WR=54.5% PnL=-23.7 EV=-2.15** (`demo_trader.py:6387-6391`) → R2 aggregate demote 2026-05-11 justified.
- Cell decomposition (from /api/demo/trades production query):
  - **Overlap (12-16 UTC): N=3 EV=+5.93 (3/3 wins)** ← pilot target
  - London (07-12 UTC): N=2 (0/2 losses, Wilson_LB=0%) — responsible for aggregate demote
  - Asia (00-07 UTC): N=5 EV=-2.64 — also contributed
- → 5/11 aggregate demote was driven by London 0/2 + Asia 5; Overlap 3/3 is clean.

**3. Shadow (referenced, NOT used as gate per `feedback_live_vs_shadow_strict_separation.md`)**
- N=58 EV=+9.54 PF=1.65 (consistent direction, but contamination history precludes gating)

### Honest assessment

- **Selective inference warning**: Overlap was NOT in the original 2026-05-13 pre-reg LOCK (London was). Re-cutting cells post-result is post-hoc selection.
- **N is thin**: BT cell N=22, Live cell N=3 — both well under R1 N≥30.
- **Direction-of-evidence convergence**: BT Overlap (N=22 EV+1.30), Live Overlap (N=3 3/3), and Shadow Overlap aggregate all point the same way.
- **Downside bounded** by 0.05x lot (defensive minimum, below standard 0.3 floor per `_lot_floor_ratio_for`).

**Classification**: R2 exploration with R1-spirit pre-reg LOCK + tight demote insurance, NOT an R1 promotion.

## Scope (LOCK)

| Field | Value |
|---|---|
| Strategy | `vix_carry_unwind` |
| Pair | USD_JPY |
| Session | **Overlap only** (12 ≤ UTC hour < 16) |
| Lot | **0.05x** (defensive minimum, sub-floor; `_PAIR_LOT_BOOST` mechanism) |
| OANDA forwarding | Live (cell-conditional) — Asia/London/NY emit blocked at promotion gate |

## Implementation spec (LOCK — code change pending user GO)

### `modules/demo_trader.py`

1. **Move `("vix_carry_unwind", "USD_JPY")` out of `_PAIR_DEMOTED`** (current line ~6392).
   Replace with comment block citing this pre-reg.

2. **Add `("vix_carry_unwind", "USD_JPY")` to `_PAIR_PROMOTED`** (current line ~6398-6507 block).
   Comment: `# C2 Overlap-only pilot, see decisions/vix-overlap-pilot-prereg-2026-05-13.md`

3. **Add new `_PAIR_SESSION_FILTER` mechanism** (minimal new attribute):
   ```python
   # Cell-conditional session filter for PAIR_PROMOTED entries.
   # When present, the (strategy, pair) is live ONLY in the listed UTC sessions.
   # See decisions/vix-overlap-pilot-prereg-2026-05-13.md
   _PAIR_SESSION_FILTER = {
       ("vix_carry_unwind", "USD_JPY"): {"Overlap"},  # 12 <= UTC hour < 16
   }
   _SESSION_BOUNDS_UTC = (
       ("Asia",    0,  7),
       ("London",  7, 12),
       ("Overlap",12, 16),
       ("NY",     16, 24),
   )
   ```

4. **Inject session check into `_promotion_allows_live`** (current line ~6796), AFTER the PAIR_PROMOTED match and BEFORE returning True:
   ```python
   if instrument and (entry_type, instrument) in self._PAIR_PROMOTED:
       _sess_filter = self._PAIR_SESSION_FILTER.get((entry_type, instrument))
       if _sess_filter is not None:
           from datetime import datetime, timezone
           _hour_utc = datetime.now(timezone.utc).hour
           _curr_sess = next(
               (name for name, lo, hi in self._SESSION_BOUNDS_UTC if lo <= _hour_utc < hi),
               None,
           )
           if _curr_sess not in _sess_filter:
               return False  # cell-conditional gate: outside allowed window
       return True
   ```

5. **Add `_PAIR_LOT_BOOST` entry**:
   ```python
   ("vix_carry_unwind", "USD_JPY"): 0.05,  # Overlap pilot defensive lot
   ```

6. **Update inline comments** at the moved demote line and SHADOW_ALWAYS reference (line ~2870) to point to this pre-reg.

### Verification commands (post-edit)

```
python3 scripts/check.py
python3 tools/tier_integrity_check.py --check
python3 tools/sync_kb_index.py --check
python3 -m pytest tests/ -x -q
```

## Demote insurance (LOCK — frozen before execution)

Cell-scoped (Overlap-only) Live monitoring:

| Trigger | Action |
|---|---|
| Cell-Live N≥10 AND (EV<0 OR Wilson_LB < 34.4% (USD_JPY BEV)) | **Auto re-demote** → back to `_PAIR_DEMOTED`, pilot ends |
| Cell-Live N=5 with ≥3 consecutive losses | **Early abort (R2 fast)** |
| Cell-Live N=5 with 2 losses | **Yellow flag** — manual review (no auto action) |
| Any-session aggregate rolling 10 trades EV < -3.0p | **Pause pilot** (revert to PAIR_DEMOTED even if Overlap healthy) |

These thresholds are LOCKED. No post-result tweaking — failure = re-demote.

## Bonferroni / selective inference context

- Original 2026-05-13 pre-reg LOCK targeted 4 cells (London for vix). London FAILED gate.
- This pilot adds C2-Overlap as 5th post-hoc cell. Effective family ≈ 5 strategies × 4 sessions = 20 informal cells. Bonferroni α=0.05/20 = 0.0025.
- N=3 Live, N=22 BT — well below Bonferroni significance at any plausible threshold.
- **This pilot makes NO statistical-significance claim.** Lot 0.05x is the safety net for the absence of significance.

## Acceptance / completion criteria

- [x] Pre-reg LOCK doc reviewed and approved by user (2026-05-13)
- [x] `modules/demo_trader.py` edits applied (5 spots above) — 2026-05-13
- [x] `scripts/check.py` clean, `tier_integrity_check.py --check` ERROR=0 — verified 2026-05-13
- [x] `pytest tests/` 1458 passed — verified 2026-05-13
- [ ] Commit message includes `rule:R2 (pilot)` + this doc path
- [ ] First Overlap Live trade observed within 7d (else "no signal" audit)
- [ ] Demote insurance trigger paths verified via dry-run

## Related artifacts

- **Closes out**: `cell-promotion-prereg-2026-05-13.md` — C2 London R1 gate **FAILED**; this is the R2 fallback path.
- **C1 mqe×GBP×Overlap**: month-end strategy structural blocker (next window 2026-05-29-31), natural wait, **no code change**.
- **C3 sr_fib×GBP×Overlap**: BT cell N=87 EV=-0.10 — statistically clean FAIL, shadow continued.
- **C4 dt_sr_channel_reversal×EUR_JPY×Overlap**: R1 gate **PASS** (N=47 EV=+0.13 Wilson_LB=53.8%), separate promotion track to be drafted.
- **Lessons**:
  - [`../lessons/lesson-asymmetric-agility-2026-04-25.md`](../lessons/lesson-asymmetric-agility-2026-04-25.md) (R1/R2/R3 framework)
  - [`../lessons/lesson-cell-audit-bt-required-2026-04-27.md`](../lessons/lesson-cell-audit-bt-required-2026-04-27.md) (cell-level evidence required for re-promote)
  - Memory: `feedback_live_vs_shadow_strict_separation.md` (Live=oanda_trade_id strict separation)
- **Tier history**: `demo_trader.py:6387-6391` (2026-05-11 demote rationale)

## Owners

- 司令塔: Claude (LOCK 制定, verdict, KB 更新)
- 実装: `modules/demo_trader.py` — **user GO 待ち**

## Decision log

- **2026-05-13 17:39 UTC**: 365d cell-conditional BT completed. C2 London target FAIL (N<30). C2 Overlap N=22 EV+1.30 (NOT in original pre-reg scope).
- **2026-05-13 18:00 UTC**: Cell-decomposed Live evidence reviewed (Overlap 3/3 EV+5.93; London 0/2 drove aggregate demote).
- **2026-05-13 (this doc) LOCK**: R2 exploration at 0.05x Overlap-only, with tight cell-scoped demote insurance. Code edit deferred to user GO.
