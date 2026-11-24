# Weekly cell deepdive — 2026-11-24 (7 strategies, 365d, PROD snapshot)

- Source: `/api/demo/trades` PROD, 21,246 rows fetched (closed 21,245 in 2 pages + open 1; completeness + membership proven, drift 0, as_of 2026-11-24T09:53Z). Target clean data span 2026-04-28 → 2026-11-18T17:46Z.
- Window [2025-11-25, 2026-11-25). Scope Live+Shadow (381/395 clean rows are shadow). XAU / dedup_violation / non-WIN-LOSS excluded.
- target raw 918 (+4 vs 11-16) → clean_N 395 (+4), locked rows routed out 76 (unchanged). m_global v2=**9** / v3=2 / family union=**11** (all unchanged vs 11-16).
- Tool: `tools/cell_deepdive_audit.py` (in-repo). The scheduled-task prompt's flags (`--strategies/--window/--regime-source`) do not exist; standard `--fetch-to` → audit flow used instead.

## PAIR_PROMOTED Candidates
**0 件** (11-02 / 11-11 / 11-16 も 0)。

## Per-strategy (clean_N, 11-16 → 11-24)
| strategy | raw | clean_N | WR | Wilson lo | EV_net | PF | u30 | u/wk (90d) | last unique fire |
|---|---|---|---|---|---|---|---|---|---|
| sr_anti_hunt_bounce | 512→515 | 227→230 | 0.522 | 0.457 | −2.70 | 0.54 | 26 | 6.14 | 2026-11-18 |
| sr_liquidity_grab | 4 | 2 | 1.00 | 0.342 | +1.95 | — | 0 | 0.00 | 2026-08-07 |
| cpd_divergence | 0 | 0 | — | — | — | — | 0 | 0.00 | never |
| vdr_jpy | 54 | 34 | 0.676 | 0.508 | +2.39 | 1.38 | 1 | 0.78 | 2026-11-13 |
| vsg_jpy_reversal | 90→91 | 61→62 | 0.629 | 0.505 | −0.47 | 0.91 | 3 | 1.48 | 2026-11-16 |
| rsk_gbpjpy_reversion | 166 | 61 | 0.541 | 0.417 | −3.50 | 0.53 | 6 | 1.63 | 2026-11-11 |
| mqe_gbpusd_fix | 88 | 6 | 0.667 | 0.300 | +5.85 | 2.53 | 0 | 0.08 | 2026-08-28 |

Accrual: +4 clean rows in 8 days (sr_anti_hunt_bounce +3, vsg_jpy_reversal +1) — the slowest week since the series began. **PROD itself is not quiet**: 205 rows entered 11-18..11-24 across all strategies (55/60/51/28/11 per trading day), but only **1** of them belongs to the 7 targets (sr_anti_hunt_bounce LOSS on 11-18). sr_anti_hunt_bounce u/wk fell 7.5 → 6.5 → 6.1 over three runs; rsk 1.9 → 1.6; vsg 1.6 → 1.5. No target fire at all on 11-19, 11-20, 11-23, 11-24. cpd_divergence still 0 in 365d; sr_liquidity_grab / mqe last fire Aug 2026.

## Non-candidate cells of note (not promoted; Bonferroni fail)
- sr_anti_hunt_bounce|GBP_JPY|London|BUY (v3): N=22 WR 0.773 Wlo 0.566 EV +1.62 PF 1.52 p_bonf **0.116** wf=True — unchanged from 11-16 (no new rows). Still the best non-LOCK cell.
- vsg_jpy_reversal|EUR_JPY|SELL (v2): N 24→25, WR 0.72, Wlo 0.524, EV +0.54, PF 1.16, p_bonf 0.454→**0.306** — the one cell that improved this week (new row was a win), but wf_stable=False and EV is thin.
- sr_anti_hunt_bounce|EUR_JPY|BUY (v2, LOCK-complement view only): N=39 p_bonf 0.071 unchanged — partial view, not the cell statistic.
- sr_anti_hunt_bounce|EUR_JPY|SELL: N 26→27, WR 0.333, EV −6.26, PF 0.20 — new row was another loss; worst cell in the grid, still degrading.
- rsk_gbpjpy_reversion|GBP_JPY|BUY: N=43 unchanged, EV −2.47 — no new rows.

## LOCK progress (counts only, outcome not computed — P-10)
- `sr-anti-hunt-eurjpy-buy-forward-confirm`: n_lock_population **48 / n_decide 40** (unchanged since 10-29). TRIGGERED. Verdict HELD pending two overdue user decisions (deadline 2026-10-12): `sr-anti-hunt-eurjpy-count-basis-declaration` (BREAKEVEN counting) and `sr-anti-hunt-eurjpy-lock-validity-disposition` (optional-stopping α). Do not judge before these.
- `ws3-t11-anti-hunt-usdjpy-recheck`: **28 / 30** (unchanged vs 11-16 — the "likely trigger next week" forecast did NOT materialise; USD_JPY accrual paused again).
- `hourblock-class-exempt-r2-rollback` marker: 7 / 10 (unchanged).
- Watcher divergence: none (pre-reg count == canonical watcher count for both shadow LOCKs).

Verdict: 依然 N 不足、shadow 蓄積継続中。ただし今週は 7 戦略の発火がほぼ停止 (+4 rows / 8 日、11-19 以降 0 件) で、PROD 全体は稼働中 (205 rows) なので **target 7 戦略側の signal 経路 / gate 詰まりを疑う**。到達済み LOCK (EUR_JPY BUY) は user 決裁 2 件待ちで判定保留 (6 週超過)。USD_JPY LOCK は 28/30 で足踏み。
