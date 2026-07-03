# Cell Deepdive Audit — 2026-06-14 (7 target strategies)

**Run date:** 2026-06-14 (scheduled weekly)
**Tool:** `cell_deepdive_audit.py` does **not exist** in repo. Re-implemented `cell_edge_audit.py` v2/v3 methodology against **Render PROD API**.
**Data source:** `https://fx-ai-trader.onrender.com/api/demo/trades` (PROD `/var/data/demo_trades.db`).
**Window:** 365d (data span 2026-04-02 → 2026-06-12) | **Scope:** Live + Shadow
**Filters:** exclude_xau, **exclude dedup_violation=1** (R2-audit rule), outcome ∈ {WIN, LOSS}.

> ⚠️ The LOCAL `demo_trades.db` is **STALE — frozen at 2026-04-30 (475 rows)**, identical to the 2026-05-31 run. Per memory rule (`feedback_check_orphan_local_app` / Cell-Edge audit 2026-06-08), the **PROD API is the only valid source**. This run pulled 9,915 closed trades from PROD.

## 🔑 Headline change vs 2026-05-31 — PRODUCTION FREEZE RESOLVED

The prior two weekly runs (2026-05-03, 2026-05-31) read the **stale local DB** and reported "0 trades, demo_trades frozen since 2026-04-30, systemic blocker." That blocker description was a **local-DB artifact**. PROD has been accumulating the whole time:

| Metric | 2026-05-31 (local, stale) | 2026-06-14 (PROD API) | Delta |
|---|---|---|---|
| Closed trades visible | 475 | **9,915** | +9,440 |
| Data max date | 2026-04-30 | **2026-06-12** | +43d |
| Target strategies with data | 0/7 | **5/7** | +5 |

5 of 7 target strategies are now firing into `demo_trades`. `sr_liquidity_grab` and `cpd_divergence` remain at **0 trades**.

## ⚠️ dedup_violation contamination — 69%

**292 of 422** target-strategy rows carry `dedup_violation=1` and were excluded (memory: `R2 audit dedup 汚染` — must exclude or N is inflated). Per strategy: mqe 82/87, rsk 89/103, sr_anti_hunt 90/174, vsg 28/47, vdr 3/11. After also dropping 38 BREAKEVENs, **clean N = 114**. This contamination level is extreme and is itself a data-quality flag (consistent with `sr_anti_hunt_bounce demo_trades meta loss` memory).

## PAIR_PROMOTED Candidates

**Count: 0.** No cell at v2 (entry_type×pair×direction) or v3 (entry_type×pair×session×direction) reaches **N≥20 ∧ Wilson_lo>0.50 ∧ Bonferroni p<0.05**. m_global = 0 (no cell even hit N≥20 once dedup contamination is stripped).

## Clean strategy-level results (dedup-excluded, WIN/LOSS only)

| Strategy | raw N | clean N | WR | Wilson_lo | EV_net | PF | Verdict |
|---|---|---|---|---|---|---|---|
| sr_anti_hunt_bounce | 174 | 69 | 39.1% | 0.285 | −1.33p | 0.80 | 🔴 **NET-NEGATIVE** |
| rsk_gbpjpy_reversion | 103 | 14 | 28.6% | 0.117 | −5.74p | 0.45 | 🔴 **NET-NEGATIVE** |
| mqe_gbpusd_fix | 87 | 5 | 60.0% | 0.231 | +6.76p | 2.48 | 🟡 +EV, N=5 (82 dedup-excl) |
| vsg_jpy_reversal | 47 | 18 | 66.7% | 0.437 | +5.43p | 2.05 | 🟢 +EV, **N=18 closest to MIN_N** |
| vdr_jpy | 11 | 8 | 75.0% | 0.409 | +13.46p | 6.67 | 🟢 +EV, tiny N=8 |
| sr_liquidity_grab | 0 | 0 | — | — | — | — | ⚫ NO TRADES |
| cpd_divergence | 0 | 0 | — | — | — | — | ⚫ NO TRADES |

### Notable sub-cells (all N<20, informational only)
- `sr_anti_hunt_bounce | EUR_JPY | BUY`: N=16, WR 62%, EV +10.4p — only bright spot in an otherwise losing strategy.
- `vsg_jpy_reversal | EUR_JPY | SELL`: N=5, WR 80%, +8.9p.
- `vdr_jpy | USD_JPY | BUY`: N=5, WR 80%, +22.5p.

## Verdict & Next Actions

1. **No Pre-reg LOCK this week** — 0 candidates. Clean N too low after dedup strip.
2. **Shadow accumulation IS now working** (freeze resolved). Realistic timeline: vsg_jpy_reversal (N=18) and the sr_anti_hunt EUR_JPY/BUY cell (N=16) should cross N≥20–30 within 2–4 more weeks at current fire rates → re-check next weekly run.
3. **🔴 Investigate dedup_violation=69%** — this is destroying usable sample on exactly these strategies. Likely the per-bar dedup / production pyarrow-confluence regression noted in `sr_anti_hunt_demo_trades_meta_loss` memory. Worth a Codex forensic task: why are 2 of every 3 target-strategy signals flagged duplicate?
4. **sr_liquidity_grab / cpd_divergence**: still 0 demo_trades despite resumed pipeline. Separate enablement check needed.
5. **sr_anti_hunt_bounce / rsk_gbpjpy_reversion are net-losing** on clean data — monitor, do not promote.
