# Cell Deepdive Audit — 2026-07-02 (7 target strategies)

**Run date:** 2026-07-02 (scheduled weekly)
**Tool:** `cell_deepdive_audit.py` does **not exist** in repo. Re-implemented `cell_edge_audit.py` v2/v3 methodology against **Render PROD API** (script: `knowledge-base/raw/cell_deepdive/_run_deepdive_2026_07_02.py`).
**Data source:** `https://fx-ai-trader.onrender.com/api/demo/trades` (PROD `/var/data/demo_trades.db`). LOCAL `demo_trades.db` is **stale** — PROD API is the only valid source (memory: `feedback_check_orphan_local_app`).
**Window:** 365d (data span 2026-04-02 → 2026-07-02) | **Scope:** Live + Shadow (clean rows almost entirely shadow)
**Filters:** exclude_xau, **exclude dedup_violation=1** (R2-audit rule), outcome ∈ {WIN, LOSS}.
**Gate:** cell N≥20 ∧ Wilson_lo>0.50 ∧ Bonferroni p<0.05.

## PAIR_PROMOTED Candidates

**Count: 0.** No cell at v2 (entry_type×pair×direction) or v3 (+session) simultaneously satisfies N≥20 ∧ Wilson_lo>0.50 ∧ Bonferroni p<0.05.
- `m_global_v2 = 2` (first time any cell reached N≥20 — 2026-06-14 had 0), `m_global_v3 = 0`.

## 🔑 Headline change vs 2026-06-14 — shadow accumulation is compounding

| Metric | 2026-06-14 | 2026-07-02 | Delta |
|---|---|---|---|
| PROD closed trades fetched | 9,915 | **11,904** | +1,989 |
| Target-strategy rows (raw) | 422 | **505** | +83 |
| dedup_violation excluded | 292 | 314 | +22 |
| Clean N (post dedup + WIN/LOSS) | 114 | **173** | +59 |
| Cells reaching N≥20 (m_global_v2) | 0 | **2** | +2 |
| PAIR_PROMOTED candidates | 0 | 0 | 0 |

The accumulation pipeline continues to work. Two cells crossed N≥20 for the first time, and `vsg_jpy_reversal` crossed MIN_N at the strategy level (see below). No cell has yet cleared the Wilson_lo>0.50 ∧ Bonferroni bar.

## ⚠️ dedup_violation contamination — 62% (314/505)

Contamination remains extreme and roughly flat vs last run (was 69%). It continues to destroy usable sample on exactly these strategies. This is itself a data-quality flag consistent with `sr_anti_hunt_bounce demo_trades meta loss` memory (production pyarrow/confluence regression). **Recommend a Codex forensic task**: why are ~2 of every 3 target-strategy signals flagged duplicate?

## Clean strategy-level results (dedup-excluded, WIN/LOSS only)

| Strategy | raw N | clean N | WR | Wilson_lo | EV_net | PF | Verdict |
|---|---|---|---|---|---|---|---|
| sr_anti_hunt_bounce | 237 | 111 | 46.8% | 0.378 | −2.04p | 0.66 | 🔴 **NET-NEGATIVE** (WR ↑ vs 39.1% but PF ↓) |
| vsg_jpy_reversal | 59 | **30** | 70.0% | **0.521** | +2.77p | 1.65 | 🟢 +EV, **N=30 ∧ Wilson_lo>0.50 at strategy level** |
| rsk_gbpjpy_reversion | 106 | 16 | 31.2% | 0.142 | −6.67p | 0.39 | 🔴 **NET-NEGATIVE** |
| vdr_jpy | 14 | 10 | 80.0% | 0.490 | +12.76p | 7.72 | 🟢 +EV, tiny N=10 (USD_JPY/BUY N=7 WR86% +18.9p) |
| mqe_gbpusd_fix | 87 | 5 | 60.0% | 0.231 | +6.76p | 2.48 | 🟡 +EV, N=5 (82/87 dedup-excluded — unchanged) |
| sr_liquidity_grab | 2 | 1 | — | — | — | — | ⚫ barely firing (0→2 raw) |
| cpd_divergence | 0 | 0 | — | — | — | — | ⚫ NO TRADES — enablement check needed |

> Note: `vsg_jpy_reversal`'s strategy-level Wilson_lo>0.50 does **not** meet the promotion gate — the gate is defined per **cell** (pair×direction), and its 30 clean trades are split across pairs/directions (EUR_JPY SELL N=13, EUR_JPY BUY N=10, …), so no single cell reaches N≥20. It is the strongest overall signal and the most likely to produce the first real candidate.

## Eligible cells (N≥20)

| Cell | N | WR | Wilson_lo | EV_net | PF | p_bonf | Kelly | WF | Promoted |
|---|---|---|---|---|---|---|---|---|---|
| sr_anti_hunt_bounce \| EUR_JPY \| BUY | 24 | 62.5% | 0.427 | +5.85p | 2.33 | 0.441 | 0.36 | ✅ stable | ❌ (Wilson<0.50, p_bonf fail) |
| sr_anti_hunt_bounce \| GBP_JPY \| BUY | 24 | 54.2% | 0.351 | −1.83p | 0.67 | 1.000 | 0.00 | ❌ | ❌ |

**`sr_anti_hunt_bounce | EUR_JPY | BUY`** is the closest single-cell candidate: N=24, +5.85p EV, PF 2.33, WF-stable across the time-split, Kelly 0.36. It fails only on Wilson_lo (0.427 < 0.50) and Bonferroni — both of which tighten favorably if WR holds as N grows. This is the bright spot inside an otherwise net-losing strategy.

## Notable sub-cells (N<20, informational only)

- `vdr_jpy | USD_JPY | BUY`: N=7, WR 86%, EV +18.9p, PF 13.5, Wilson_lo 0.487 — tiny but very strong; watch as it grows.
- `vsg_jpy_reversal | EUR_JPY | SELL`: N=13, WR 69%, EV +1.6p, PF 1.52.
- `vsg_jpy_reversal | EUR_JPY | BUY`: N=10, WR 70%, EV +0.16p (near-zero net).

## Verdict & Next Actions

1. **No Pre-reg LOCK this week** — 0 candidates clear the cell-level gate.
2. **Shadow accumulation is compounding** (clean N 114→173, first two N≥20 cells). Realistic path to the first candidate: `sr_anti_hunt_bounce | EUR_JPY | BUY` (N=24, needs Wilson_lo to reach 0.50) and a concentrating `vsg_jpy_reversal` cell. Re-check next weekly run.
3. **🔴 dedup_violation=62%** is the single biggest blocker to reaching N≥20 candidates — worth a Codex forensic task on the duplicate-flagging root cause.
4. **cpd_divergence** still 0 trades; **sr_liquidity_grab** barely firing (raw 2). Separate enablement/plumbing check.
5. **sr_anti_hunt_bounce / rsk_gbpjpy_reversion net-losing** on clean data — monitor, do not promote.
