# Turtle System 2 — 55-day Donchian D1 (USDJPY long-only Shadow)

- **Status**: SHADOW (Wave 1 BT verdict B, Shadow-promote candidate, 2026-05-03)
- **Stage**: Pre-Live — `is_shadow=1` only, live promotion blocked until live shadow N≥80 + Bonferroni p<0.10
- **Family entry_types**: `turtle_s2_unit_1`, `turtle_s2_unit_2`, `turtle_s2_unit_3`, `turtle_s2_unit_4`
- **Mode / TF**: daytrade / D1 (NY 17:00 close ≈ 21:00 UTC)
- **Pair whitelist**: `USD_JPY` (long only)

## Wave 1 BT result (15.3y D1)

| Cell | N | WR | Wilson 95% lo–hi | EV (pips) | PF | OOS PF | Sharpe | Kelly | Bonf p (K=2) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **USDJPY long S2** | 50 | 0.320 | 0.208–0.458 | **+207** | **1.99** | **1.99** | 0.21 | +0.16 | **0.172** |
| USDJPY short S2 | 29 | 0.207 | 0.098–0.384 | -87 | 0.73 | — | — | -0.08 | 1.000 |
| GBPJPY (any side) | 75 | 0.240 | 0.158–0.348 | -188 | 0.68 | 0.50 | -0.28 | -0.11 | 1.000 |

Source: `wiki/learning/s2-turtle-55day-bt-2026-05-03.md`

**Decision rationale**:
- USDJPY long passes Wilson lo > 0, PF > 1.5, OOS PF > IS PF (anti-overfit), Half-Kelly mandatory.
- Bonferroni p=0.172 fails the 0.20 relaxed gate by a hair → `B` not `A` → **Shadow-only** until N grows.
- USDJPY short / GBPJPY both directions clean reject (Wave 1 BT §3.1, §3.2).

## Strategy spec (Pre-reg LOCK 2026-05-03)

| Parameter | Value | Notes |
|---|---|---|
| Donchian length | 55 (D1 bars) | uses `shift(1)` so current bar excluded |
| ATR (N) length | 20 (D1) | Wilder smoothing (alpha=1/20, adjust=False) |
| Initial stop | entry − 2N | per unit, **independent** of other units |
| Pyramid step | +0.5N favourable | from prior unit's entry |
| Max units | 4 (default) → 2 (158 ≤ close < 160) → 0 (close ≥ 160) | BoJ regime gate |
| Exit (full) | D1 close < prior 20-day low | closes ALL units atomically |
| MA filter | none | per `feedback_ma_filter_breaks_mr` |
| Skip-after-winner | none | this is System 2, not System 1 |
| Live promotion gate | live shadow N≥80 + Bonferroni p<0.10 + OOS PF maintained | external |

## Anti-Martingale guard (vs halt-pyramid 2026-05-01)

Each unit's stop is computed from **its own entry**, not trailed up from a prior unit. This preserves unit-level loss budgets. The 2026-05-01 halt-pyramid audit removed the classical "risk-free pyramiding" mechanism that moved prior stops to break-even after a new unit was added — that mechanism is **not** reintroduced here.

## File map

| Path | Purpose |
|---|---|
| `strategies/daytrade/turtle_s2_donchian.py` | D1 evaluator, regime gate, exit rule, signal struct |
| `modules/turtle_s2_pyramid.py` | Pyramid unit manager (per-unit stop, atomic exit) |
| `tools/turtle_s2_d1_runner.py` | Daily runner (cron / manual) — opens Shadow trades only |
| `tests/test_turtle_s2_donchian.py` | 19 unit tests covering entry / exit / pyramid / regime gate |
| `data/turtle_s2_state/USD_JPY.json` | runtime state file (auto-created) |
| `data/USD_JPY_d1.parquet` | D1 OHLCV cache (built by Wave-1 BT) |

## Operational guardrails

1. **BoJ intervention zone**: USDJPY ≥ 158.0 → `max_units` halved (4 → 2).
   USDJPY ≥ 160.0 → entry blocked outright. (Spec note 3, not BT-validated.)
2. **Intervention day skip**: any D1 within ±1 day of a known BoJ intervention is skipped on entry AND blocked from pyramid additions. Caller passes the registry via `--intervention-day` CLI flag.
3. **Spread > 3p USDJPY** (system dynamic spread gate) — handled upstream by `oanda_bridge`, not duplicated here.
4. **Patience**: Sharpe 0.21 → 1–2 year flat periods are normal (Turtle classical literature). Do not demote on flat stretches alone.
5. **`is_shadow=1` integrity**: every unit row hard-codes `is_shadow=True` in `TurtleS2PyramidManager._persist_unit`. There is no live OANDA bridge path. Confirmed by `tests/test_turtle_s2_donchian.py::TestPyramidManager::test_open_initial_persists_unit_1_as_shadow`.

## Live-promotion checklist (do NOT activate without all ✅)

- [ ] Live shadow N ≥ 80 (combined with BT N=50 for combined Wilson CI)
- [ ] Bonferroni p < 0.10 (K=2 USDJPY × directions)
- [ ] OOS PF maintained > 1.5 vs Wave-1 BT baseline 1.99
- [ ] Live × Shadow separation honoured (`feedback_live_shadow_separation`) — analysis filters `is_shadow=0` for any Live PnL claim
- [ ] Time-cohort integrity (`feedback_cohort_time_check`) — promote/demote history time-aligned
- [ ] Codex independent review on PR (queued for 2026-05-07 schedule)

## Monthly Shadow report

Generated under `wiki/learning/s2-shadow-monthly-YYYY-MM.md` after each calendar month with at least 1 fired unit. Template fields:

- N (this month) / N (cumulative live shadow) / N (combined with BT)
- WR / EV / Wilson 95% CI / Bonferroni p (combined)
- OOS PF (rolling 60-trade window) — must remain > 1.0 for promotion candidacy
- Drawdown windows (>30 days flat is normal, document anyway)
- Per-unit attribution — which unit indices are doing the work

## Related

- Parent plan: `~/.claude/plans/find-out-way-of-fizzy-patterson.md`
- Catalogue: `wiki/learning/global-retail-fx-edges-2026-05-03.md` §B-1
- BT report: `wiki/learning/s2-turtle-55day-bt-2026-05-03.md`
- KB feedback: `feedback_partial_quant_trap`, `feedback_live_shadow_separation`, `feedback_ma_filter_breaks_mr`, `feedback_check_orphan_local_app`
- Lesson on halt-pyramid: see 2026-05-01 obs#838-843 (per-unit stops independent)

`rule:R1` (slow & strict) — Pre-reg LOCK frozen 2026-05-03.
