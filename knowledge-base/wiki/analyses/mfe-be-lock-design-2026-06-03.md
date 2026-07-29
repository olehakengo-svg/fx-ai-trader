---
title: MFE-pip Break-Even Lock — Design & Counterfactual
date: 2026-06-03
rule: R3
author: Claude (quant analyst mode)
status: CLOSED — A/B verdict FAIL / no promotion (2026-07-28, §8)
related:
  - knowledge-base/wiki/lessons/lesson-snapshot-survivorship-bias-2026-06-03.md
  - knowledge-base/wiki/analyses/system-reference.md
---

# MFE-pip Break-Even Lock (含み益ロック)

## 1. Problem

User observation (2026-06-03 session): the demo dashboard shows many shadow
positions with unrealized gains, but realized closed-trade EV is deeply
negative (`-1.49 pips/trade`, sumP `-10,896` pips on 7,311 post-2026-04-08
shadow trades). The "snapshot looks profitable" was a **survivorship bias** —
losers exit via SL_HIT and disappear from the open list, winners linger.

## 2. Diagnosis

Cell-level extraction with **BH-FDR (q=0.10, m=69)** yielded **0 survivors**:
no strategy×pair×direction cell beats multiple-testing correction in the
2-month shadow window. The Cable family (`wick_imbalance_reversion BUY`,
`dt_bb_rsi_mr SELL` on EUR_USD / GBP_USD) and `mqe_gbpusd_fix` were directionally
coherent but not significant.

The real leak is **exit logic, not selection**:

| Metric | Value |
|---|---|
| Average MFE (peak favorable) | **+4.90 pips** |
| Average final PnL | -1.49 pips |
| **Average giveback (MFE − final)** | **6.39 pips/trade** |

Lost-winner rate:

| MFE bucket | Reached | Lost (final<0) |
|---|---|---|
| MFE ≥ +2 pips | 47.5% | **50.9%** of reached |
| MFE ≥ +5 pips | 30.5% | 34.1% of reached |
| MFE ≥ +10 pips | 14.9% | 20.9% of reached |

Close-reason breakdown (avgMFE → avgPnL):

| close_reason | N | avgMFE | avgPnL | giveback |
|---|---|---|---|---|
| SL_HIT | 3,674 | 1.77 | -7.76 | **9.53** |
| TIME_DECAY_EXIT | 1,394 | 3.66 | -1.74 | **5.40** |
| SIGNAL_REVERSE | 570 | 2.47 | -3.40 | **5.87** |
| TP_HIT | 1,451 | 13.94 | 13.94 | 0.01 |

The existing ATR-based BE (ATR×0.8 → BE+spread at line 2070 of demo_trader.py)
fires too late: typical ATR×0.8 ≈ 8–15 pips, but the bulk of lost winners
peaked at MFE ≈ +2–3 pips and never reached the ATR threshold.

## 3. Counterfactual

Simulation: `if MFE ≥ trigger pips, simulated_pnl = max(real_pnl, lock_floor)`
(idealized — assumes BE-lock SL move is honored).

Aggregate pool (N=7,311):

| Trigger | Floor | mean | ΔEV | WR% | sumP | ΔsumP | PF |
|---|---|---|---|---|---|---|---|
| (baseline) | — | -1.49 | — | 23.7 | -10,896 | — | 0.675 |
| **+2** | +1 | **+0.06** | **+1.55** | **48.0** | **+468** | **+11,363** | **1.020** |
| +2 | +2 | +0.31 | +1.80 | — | +2,285 | +13,181 | 1.095 |
| +3 | +1 | -0.29 | +1.20 | 41.5 | -2,155 | +8,740 | 0.917 |
| +5 | +1 | -0.74 | +0.75 | 34.1 | -5,378 | +5,517 | 0.813 |
| +10 | +1 | -1.20 | +0.29 | 26.8 | -8,745 | +2,151 | 0.723 |

→ `trigger=+2 / floor=+1` flips the entire shadow pool from EV<0 to EV>0.

Per-cell tuning:

| Cell | base EV | best trig | best EV | ΔEV |
|---|---|---|---|---|
| vix_carry_unwind / USD_JPY / SELL | 5.85 | **+3** | **15.11** | **+9.26** |
| mqe_gbpusd_fix / GBP_USD / SELL | 2.94 | +3 | 6.04 | +3.11 |
| sr_anti_hunt_bounce / EUR_JPY / BUY | 14.15 | +3–5 | 16.47 | +2.32 |
| orb_trap / GBP_USD / SELL | 8.99 | +3–5 | 9.98 | +0.98 |
| dt_bb_rsi_mr / EUR_USD / SELL | 2.34 | +3 | 3.07 | +0.73 |
| wick_imbalance_reversion / EUR_USD / BUY | 3.42 | +3 | 3.53 | +0.11 |
| **donchian_momentum_breakout / NZD_JPY / BUY** | 20.49 | — | 20.49 | **0** |

donchian already exits well — tighter trail would clip winners. It is the
single strategy explicitly **disabled** (`MFE_BE_LOCK_STRATEGY_TRIGGERS["donchian_momentum_breakout"] = 0.0`).

## 4. Implementation

### Components

| File | Role |
|---|---|
| `modules/demo_trader.py` | Module-level constants + pure helpers + SL-loop hook |
| `tests/test_mfe_be_lock.py` | 22 unit tests on the pure helpers |
| `tools/be_lock_ab_monitor.py` | Post-hoc A vs B comparison (Welch t-test + cell rollup) |

### Module-level API

```python
MFE_BE_LOCK_DEFAULT_TRIGGER_PIPS = 2.0   # MFE threshold to fire
MFE_BE_LOCK_DEFAULT_FLOOR_PIPS   = 1.0   # SL distance from entry once locked

MFE_BE_LOCK_STRATEGY_TRIGGERS = {        # per-strategy override
    "vix_carry_unwind": 3.0,
    "mqe_gbpusd_fix": 3.0,
    "dt_bb_rsi_mr": 3.0,
    "sr_anti_hunt_bounce": 3.0,
    "orb_trap": 3.0,
    "wick_imbalance_reversion": 3.0,
    "donchian_momentum_breakout": 0.0,   # OFF — already optimal
}

_mfe_be_lock_trigger_for(entry_type, default) -> float
_mfe_be_lock_group(trade_id, ab_fraction) -> "A" | "B"
_compute_mfe_be_lock_sl(direction, entry_price, current_sl,
                        mfe_favorable_price, instrument, spread_amt,
                        trigger_pips, floor_pips) -> (new_sl, fired)
```

### Env contract

| Variable | Default | Effect |
|---|---|---|
| `SHADOW_BE_LOCK_ENABLE` | `0` | Master switch. `1` to activate. |
| `SHADOW_BE_LOCK_AB_FRACTION` | `0.5` | Fraction of trades assigned to group B (BE-locked). Deterministic by `crc32(trade_id) % 1000`. |
| `SHADOW_BE_LOCK_TRIGGER_PIPS` | `2.0` | Default MFE trigger (overridden per strategy by the map above). |
| `SHADOW_BE_LOCK_FLOOR_PIPS` | `1.0` | SL distance from entry once locked. |

### Hook location

`modules/demo_trader.py::_sltp_loop` — injected immediately after the MAFE
tracker update and before the existing ATR-based BE block. The existing
`if new_sl > sl: sl = new_sl` guard ensures the BE-lock never *downgrades*
an already-tighter trail (composes cleanly with line-2070 ATR BE and the
SMC +3pip BE+0.1 logic).

### Telemetry

First fire per trade is logged as:
```
🔒 [BE_LOCK_B] {entry_type}×{pair} MFE={x}p≥trig{y}p → SL→entry+{floor}p (id=...)
```
and stored in-memory at `DemoTrader._be_lock_fired[trade_id]` (popped on close).

## 5. Validation plan (Phase D)

1. **Deploy with `SHADOW_BE_LOCK_ENABLE=1, SHADOW_BE_LOCK_AB_FRACTION=0.5`**
   — 50/50 A vs B split.
2. **30-day shadow accrual** (target N_B ≥ 1,000 per major cell).
3. **Run `tools/be_lock_ab_monitor.py --api … --since <deploy_date>`** weekly.
4. **Stat-sig criteria** for Live promotion:
   - Per-strategy: N_A ≥ 100, N_B ≥ 100, Welch p < 0.05, ΔEV > 0,
     Bonferroni-corrected at m = active-strategies-count.
   - Aggregate: pool-wide ΔEV > 0 with p < 0.01.
5. **Rule classification**: R3 (算数破綻 fix) — broad shadow-only deploy is
   not Rule-1-gated, but **Live promotion of the BE-lock setting** requires
   Rule-1 evidence (per-strategy N≥30 + Bonferroni).

## 5b. Post-deploy bug & fix (2026-06-03, ~02:55 UTC)

After env activation, live verification showed 2 group-B trades with
unrealized_pips ≥ trigger but unchanged SL. Root cause: the shared SL
mirror block at line ~2416 of demo_trader.py was rolling back ALL SL
modifications for shadow trades because `OandaBridge.modify_sl_sync`
returns False when no `oanda_trade_id` mapping exists. Affected EVERY
SL-modifying logic on shadow stream (BE-lock, ATR-BE, ATR-trail, SMC-BE,
v6.4 TP extender) — not just this commit.

Fix: branch on `trade["is_shadow"]`. Shadow path persists the new SL via
`self._db.update_sl_tp(trade_id, sl, tp)` (no OANDA mirror needed). LIVE
path unchanged. Details: `wiki/lessons/lesson-shadow-sl-rollback-bug-2026-06-03.md`.

Implication for the audit baseline: pre-fix shadow had **no** SL
protection at all (despite the code). Post-fix group A inherits the
existing ATR-based BE/trail. The marginal A vs B effect we measure is
the BE-lock contribution **on top of** existing trail/BE — which is the
correct quantity for the promotion decision.

## 6. Known caveats

- **Idealized simulation**. Counterfactual assumes the post-lock SL is
  honored on a 0.5-sec loop; real execution slippage may add −0.5 to −1 pip
  per locked exit. Lock floor `+1` may need to widen to `+2` if observed.
- **In-sample regime**. 2 months of shadow data; possible over-fit. OOS
  validation = the 30-day live A/B itself.
- **Per-strategy table is a hypothesis**, not a proven optimum. Some cells
  in the override map have N < 50 in the source audit — the +3 trigger
  may need re-tuning after Phase D N accrues.
- **Composition with existing logic**: SMC's +3pip BE+0.1 is now dominated
  by our +2pip BE+1 (we fire first, with a higher floor). This is
  intentional but worth re-examining if SMC strategies regress.

## 7. References

- Source data: `/api/demo/trades?limit=20000&status=closed&shadow=1` (snapshot 2026-06-03 ~03:00 JST)
- Cell extraction: `/tmp/cell_extract.py`, output `/tmp/cell_extract_out.json`
- Giveback analysis: `/tmp/giveback_analysis.py`
- Audit comment block in source: `modules/demo_trader.py` lines 78–105

## 8. Verdict — FAIL / no promotion, experiment CLOSED (2026-07-28)

§5 の stat-sig criteria に対する実測 (`tools/be_lock_ab_monitor.py`、deploy 2026-06-03 から 55 日、N_A=2,906 / N_B=2,986 shadow 非XAU):

| §5 基準 | 実測 | 判定 |
|---|---|---|
| Aggregate ΔEV > 0 ∧ p < 0.01 | **ΔEV(B−A) = −0.034 p/t、Welch p = 0.855** | ❌ |
| Per-strategy Welch p<0.05 ∧ ΔEV>0 ∧ Bonferroni | 全戦略不成立 (price_shock は N<10 で判定不能) | ❌ |
| 補助観測 | WR A 45.4% → B 60.5% (+15pp) / **PF A 0.635 → B 0.505 (悪化)** | 勝ちクリップの実 live 版 (MEMORY `project_be_trail_inflates_python_bt_wr` と同型) |

- 30-day 判定期日 (~2026-07-03) を **25 日超過**しての執行 (pre-reg 執行規律、T5 前例)。発見経緯: [[preserve-exit-overlay-2026-07-28]] §3.2
- **Verdict: Live promotion 不成立 → 実験クローズ、env OFF (`SHADOW_BE_LOCK_ENABLE=0` = 全 A 化)**
- code (helpers / hook / tests) は残置 — 再実験は本設計の §5 基準 + R1 で再起案が条件
- price_shock_rev ×5 は verdict と独立に `MFE_BE_LOCK_STRATEGY_TRIGGERS` 0.0 で恒久 code pin ([[preserve-exit-overlay-2026-07-28]] §7 — env 再有効化でも estimand を汚染しない)
- §6 caveat「idealized simulation」は §3 counterfactual (+1.55 ΔEV 予測) に対し実測 −0.034 で確定的に反証 — snapshot counterfactual の楽観バイアス事例として [[lesson-snapshot-survivorship-bias-2026-06-03]] に連なる
