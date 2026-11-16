# Weekly cell deepdive — 2026-11-16 (7 strategies, 365d, PROD snapshot)

- Source: `/api/demo/trades` PROD, 20,957 rows fetched (completeness + membership proven, 2 pages, drift 0), data span 2026-04-28 → 2026-11-13T17:17Z.
- Window [2025-11-17, 2026-11-17). Scope Live+Shadow (377/391 clean rows are shadow). XAU / dedup_violation / non-WIN-LOSS excluded.
- target raw 914 → clean_N 391 (+5 vs 11-11), locked rows routed out 76 (+3). m_global v2=**9** (11-11: 8) / v3=2 / family union=**11** (11-11: 10) — one more v2 cell crossed min_n=20, so the Bonferroni denominator grew.

## PAIR_PROMOTED Candidates
**0 件** (11-02 / 11-11 も 0)。

## Per-strategy (clean_N, 11-11 → 11-16)
| strategy | raw | clean_N | WR | Wilson lo | EV_net | PF | u30 | u/wk (90d) | last unique fire |
|---|---|---|---|---|---|---|---|---|---|
| sr_anti_hunt_bounce | 506→512 | 224→227 | 0.529 | 0.464 | −2.63 | 0.55 | 34 | 6.46 | 2026-11-13 |
| sr_liquidity_grab | 4 | 2 | 1.00 | 0.342 | +1.95 | — | 0 | 0.00 | 2026-08-07 |
| cpd_divergence | 0 | 0 | — | — | — | — | 0 | 0.00 | never |
| vdr_jpy | 53→54 | 33→34 | 0.676 | 0.508 | +2.39 | 1.38 | 1 | 0.78 | 2026-11-13 |
| vsg_jpy_reversal | 90 | 61 | 0.623 | 0.497 | −0.51 | 0.90 | 4 | 1.56 | 2026-11-11 |
| rsk_gbpjpy_reversion | 165→166 | 60→61 | 0.541 | 0.417 | −3.50 | 0.53 | 7 | 1.94 | 2026-11-11 |
| mqe_gbpusd_fix | 88 | 6 | 0.667 | 0.300 | +5.85 | 2.53 | 0 | 0.08 | 2026-08-28 |

Accrual: only sr_anti_hunt_bounce (6.5 unique/wk, down from 7.5) plus rsk (1.9/wk) and vsg (1.6/wk) are live. vdr_jpy fired once (first since 10-09). cpd_divergence still 0 in 365d; sr_liquidity_grab / mqe last fire Aug 2026. Snapshot ends 11-13 (weekend), so this is a 2-trading-day increment over 11-11.

## Non-candidate cells of note (not promoted; Bonferroni fail)
- sr_anti_hunt_bounce|GBP_JPY|London|BUY (v3): N=22 WR 0.773 Wlo 0.566 EV +1.62 PF 1.52 p_bonf **0.116** (11-11: 0.105) wf=True — best non-LOCK cell; unchanged N, p_bonf drifted up only because m grew.
- sr_anti_hunt_bounce|EUR_JPY|BUY (v2, LOCK-complement view only): N=39 p_bonf 0.071 (11-11: 0.065) — partial view, not the cell statistic.
- rsk_gbpjpy_reversion|GBP_JPY|BUY: N 42→43, WR 0.619→0.605, EV −2.23→−2.47 — the new row was a loss; cell keeps degrading.
- sr_anti_hunt_bounce|EUR_JPY|SELL: N 25→26, WR 0.346, EV −6.07, PF 0.21 — worst cell in the grid, consistently negative.

## LOCK progress (counts only, outcome not computed — P-10)
- `sr-anti-hunt-eurjpy-buy-forward-confirm`: n_lock_population **48 / n_decide 40** (unchanged). TRIGGERED since 10-29. Verdict HELD pending two overdue user decisions (deadline 2026-10-12): `sr-anti-hunt-eurjpy-count-basis-declaration` (BREAKEVEN counting) and `sr-anti-hunt-eurjpy-lock-validity-disposition` (optional-stopping α). Do not judge before these.
- `ws3-t11-anti-hunt-usdjpy-recheck`: **28 / 30** (11-11: 25, +3 — USD_JPY accrual resumed). At the current pace it reaches n_decide within ~1 week; next weekly run is the likely trigger.
- `hourblock-class-exempt-r2-rollback` marker: 7 / 10 (unchanged).
- Watcher divergence: none (pre-reg count == canonical watcher count for both shadow LOCKs).

Verdict: 依然 N 不足、shadow 蓄積継続中。到達済み LOCK (EUR_JPY BUY) は user 決裁 2 件待ちで判定保留。USD_JPY LOCK が 28/30 で次週到達見込み。
