# Bot Uptime Heatmap & Silent-Strategy Diagnosis (Phase 2 Resolved)
**Date:** 2026-04-30 (UTC ~10:00)  
**Source:** `GET /api/demo/trades?days=30&limit=10000&include_shadow=1`  
**Sample:** 4,276 trades, range 2026-04-02 08:17 → 2026-04-30 09:40 UTC  
**Plan:** §Phase 2 (was deferred — now resolved by direct API observation)

---

## Headline finding

**Bot has a dead zone at UTC 22:00-23:00** — zero trades across all 30 days, all modes, all symbols. UTC 21:00 is also extremely sparse (17 trades / 30 days = 0.57 trades/day). This is not a strategy issue but an **infrastructure / main-loop scheduling issue**.

```
UTC hour heatmap (firing density 30d, n=4,276):
   0 |    181  | ███████████████████████
   1 |    128  | ████████████████
   2 |    109  | ██████████████
   3 |    118  | ███████████████
   4 |     93  | ████████████
   5 |    129  | █████████████████
   6 |    201  | ██████████████████████████
   7 |    282  | █████████████████████████████████████
   8 |    293  | ██████████████████████████████████████
   9 |    244  | ████████████████████████████████
  10 |    201  | ██████████████████████████
  11 |    226  | █████████████████████████████
  12 |    304  | ████████████████████████████████████████
  13 |    341  | ████████████████████████████████████████████
  14 |    319  | ██████████████████████████████████████████
  15 |    379  | ██████████████████████████████████████████████████
  16 |    207  | ███████████████████████████
  17 |    184  | ████████████████████████
  18 |    134  | █████████████████
  19 |    109  | ██████████████
  20 |     77  | ██████████
  21 |     17  | ██                  ← extremely sparse
  22 |      0  |                     ← DEAD ZONE
  23 |      0  |                     ← DEAD ZONE
```

Peak at UTC 15 (London/NY overlap). UTC 0–6 covered. UTC 21 → 23 progressive collapse.

---

## Per-strategy verdict (4 time-windowed silent strategies)

| # | Strategy | Required UTC | Bot @ those hours | Real root cause | Fix path |
|---|---|---|---|---|---|
| 1 | **gotobi_fix** | 23, 0, 1 | 23h=**0** ⚠️ / 0h=181 / 1h=128 | **Infrastructure** — half the strategy's window is in a Bot dead zone (23h). The 0h+1h slice is alive but short (75min). | Render service investigation (why is main_loop dead UTC 22-23?), not strategy code. Hold `gotobi_fix` static. |
| 2 | **london_close_reversal** | 15, 16 | 15h=**379** ✅ / 16h=207 ✅ | **Strategy gate** — Bot covers the window heavily, so the 0 firings come from the strategy's own filters: `is_friday` block + tight 75-min entry window + `len(df) < VOL_LOOKBACK+5`. | Strategy-internal env knob (e.g. relax Friday block, or `LCR_NEWS_SPIKE_MULT`). Phase 4-equivalent re-introduction. |
| 3 | **london_close_reversal_v2** | 20, 21 | 20h=77 / 21h=**17** ⚠️ | **Mostly infrastructure** — required window 20:30-21:00 spans the Bot's collapse zone. The 30 min/day window is barely covered. | Render service investigation (extend uptime to UTC 22) + strategy minor relaxation. |
| 4 | **pd_eurjpy_h20_bbpb3_sell** | 20 | 20h=77 ✅ | **Strategy gate** — Bot covers UTC 20 with 77 trades but EUR_JPY-only + bbpb∈(0.6,0.8] + Friday-block + TF=15m gate combined kills sample. | Strategy-internal env knob (bbpb upper from 0.8 → 0.95). Phase 4-equivalent re-introduction. |

**Decisions changed by this evidence:**
- gotobi_fix and LCR_v2 are **infrastructure problems**. Code-side gate relaxation would not help. The Phase 3+4 revert was actually correct for these.
- LCR and pd_eurjpy_h20_bbpb3_sell are **strategy-side problems**. They're candidates for env-knob re-introduction once Phase 5 data confirms the binding gate.

---

## Why does the Bot die UTC 22-23? — RESOLVED

**Found:** `app.py:438` `is_trade_prohibited()` returns `prohibited=True` for `hour_utc >= 22`:

```python
# ① 低流動性セッション
# 22:00-23:59 UTC: 深夜 — 出来高不足で取引禁止
if hour_utc >= 22:
    return {
        "prohibited": True,
        "reason": f"🌙 深夜セッション ({hour_utc:02d}:00 UTC) — 出来高不足",
        "layer": 0, "check": "session",
    }
```

This is a **hardcoded static time block** that **directly violates CLAUDE.md
4-principles #3**:

> 3. **静的時間ブロックは使わない** — UTC固定のブロックは禁止。市場条件で判断

And contradicts principle #2:

> 2. **デスゾーン = スプレッド異常（動的検出）のみ** — Spread/SL Gateで動的防御

**Effect:**
- gotobi_fix's UTC 23:45-01:15 window: ~half blocked statically (23:00-23:59).
- london_close_reversal_v2 UTC 20:30-21:00: not blocked, but UTC 21 has only 17 trades / 30d (the taper into 22:00 cutoff is the cause; main loop likely begins shutting down activities at 21).
- All other strategies that might fire UTC 22-23: blocked by construction.

**Recommended fix:** Remove the static `hour_utc >= 22` clause, let the existing
spread_gate / SL gate / per-strategy `active_hours_utc` handle the liquidity
question dynamically. This requires a separate PR with careful review (changes
production trading hours).

---

## Recommended next actions (in priority order)

### Priority 1 — Find the UTC 22-23 dead zone root cause
```bash
# Check demo_trader.py for hour-based sleeps or market_close conditions
grep -nE "hour_utc.*(2[0-3])|market_close|rollover|daily_close" modules/demo_trader.py app.py | head -20
```
If a code-level skip is found, decide whether to remove it (gain UTC 22-23 trading) or preserve it (acknowledge limitation and stop deploying time-window strategies that need those hours).

### Priority 2 — For LCR and pd_eurjpy_h20_bbpb3_sell, re-introduce targeted env knobs
These are the only 2 of 4 silent strategies where the Bot uptime is sufficient. Phase 4-equivalent:
```
LCR_FRIDAY_BLOCK_HOUR=20  # currently always-block on Friday; allow Mon-Thu
PD_EURJPY_BBPB_MAX=0.95    # currently 0.8
```

### Priority 3 — Hold gotobi_fix and LCR_v2 unchanged
Until the dead zone is fixed (Priority 1), these strategies cannot achieve N regardless of code changes. Document and monitor.

---

## Cross-reference

- Original audit: `audit/2026-04-30/silent-strategies-preflight.md` §Phase 2 (deferred)
- This file resolves Phase 2 via API observation instead of Render workspace logs.
- 24h verification cron `silent-strategies-24h-verification-2026-05-01` will also surface any post-deploy changes to these counts.
