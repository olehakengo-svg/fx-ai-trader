# Weekly cell deepdive — 2026-11-11 (7 strategies, 365d, PROD snapshot)

- Source: `/api/demo/trades` PROD, 20,772 rows fetched (completeness + membership proven), data span 2026-04-28 → 2026-11-11T02:33Z.
- Window [2025-11-12, 2026-11-12). Scope Live+Shadow (372/386 clean rows are shadow). XAU / dedup_violation / non-WIN-LOSS excluded.
- target raw 906 → clean_N 386 (+10 vs 11-02), locked rows routed out 73 (+3). m_global v2=8 / v3=2 / family union=10 (unchanged).

## PAIR_PROMOTED Candidates
**0 件** (11-02 も 0)。

## Per-strategy (clean_N, 11-02 → 11-11)
| strategy | raw | clean_N | WR | EV_net | PF | u30 |
|---|---|---|---|---|---|---|
| sr_anti_hunt_bounce | 497→506 | 219→224 | 0.527 | −2.78 | 0.53 | 30 |
| sr_liquidity_grab | 4 | 2 | 1.00 | +1.95 | — | 0 |
| cpd_divergence | 0 | 0 | — | — | — | 0 |
| vdr_jpy | 53 | 33 | 0.667 | +2.25 | 1.35 | 0 |
| vsg_jpy_reversal | 89→90 | 60→61 | 0.623 | −0.51 | 0.90 | 5 |
| rsk_gbpjpy_reversion | 161→165 | 56→60 | 0.550 | −3.35 | 0.54 | 6 |
| mqe_gbpusd_fix | 88 | 6 | 0.667 | +5.85 | 2.53 | 0 |

Accrual: only sr_anti_hunt_bounce (7.5 unique/wk) and rsk (1.9/wk), vsg (1.6/wk) are live. cpd_divergence still 0 in 365d; sr_liquidity_grab / mqe last fire Aug 2026; vdr_jpy last fire 2026-10-09 (0 in 30d).

## Non-candidate cells of note (not promoted; Bonferroni fail)
- sr_anti_hunt_bounce|GBP_JPY|London|BUY (v3): N=22 WR 0.773 Wlo 0.566 EV +1.62 PF 1.52 p_bonf 0.105 wf=True — best non-LOCK cell, p_bonf not < 0.05.
- sr_anti_hunt_bounce|EUR_JPY|BUY (v2, LOCK-complement view only): N=39 p_bonf 0.065 — partial view, not the cell statistic.

## LOCK progress (counts only, outcome not computed — P-10)
- `sr-anti-hunt-eurjpy-buy-forward-confirm`: n_lock_population **48 / n_decide 40** (11-02: 45). TRIGGERED since 10-29. Verdict is HELD pending two overdue user decisions (deadline 2026-10-12): `sr-anti-hunt-eurjpy-count-basis-declaration` (BREAKEVEN counting) and `sr-anti-hunt-eurjpy-lock-validity-disposition` (optional-stopping α). Do not judge before these.
- `ws3-t11-anti-hunt-usdjpy-recheck`: 25 / 30 (unchanged; USD_JPY accrual ~0 this period).
- `hourblock-class-exempt-r2-rollback` marker: 7 / 10 (unchanged).

Verdict: 依然 N 不足、shadow 蓄積継続中。唯一の到達済み LOCK (EUR_JPY BUY) は user 決裁 2 件待ちで判定保留。
