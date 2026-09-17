# Cell Deepdive — Cross-Strategy Summary

- **Date (UTC)**: 2026-04-28
- **Window**: 365d  (2025-04-28T05:12:06.378391+00:00 → now)
- **Source**: smoke fixture  (regime: self_reported)
- **Strategies audited**: sr_anti_hunt_bounce, sr_liquidity_grab, cpd_divergence, vdr_jpy, vsg_jpy_reversal, rsk_gbpjpy_reversion, mqe_gbpusd_fix

## Bonferroni m by strategy

| strategy | m (cells with n>=10) | candidates (n>=30 + all gates) |
|---|---|---|
| sr_anti_hunt_bounce | 2 | 1 |
| sr_liquidity_grab | 2 | 1 |
| cpd_divergence | 2 | 0 |
| vdr_jpy | 2 | 0 |
| vsg_jpy_reversal | 2 | 1 |
| rsk_gbpjpy_reversion | 2 | 0 |
| mqe_gbpusd_fix | 2 | 0 |
| **TOTAL (m_global)** | **14** | **3** |

## PAIR_PROMOTED Candidates (cross-strategy, ranked by Wilson_lower_BF)

| strategy | pair | session | hour_bin | regime | mode | direction | n | wins | wr | wilson_lower_95 | wilson_lower_bf | ev_pip | friction_pip | ev_net_pip | bev_wr | p_raw | p_bonf_strategy | p_bonf_global | p_bh_fdr | kelly_f | wf_stable | wf_folds_positive | wf_oos_wr_min | recommendation | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sr_anti_hunt_bounce | USD_JPY | overlap_LN | London | range | DT | BUY | 50 | 40 | 0.800 | 0.670 | 0.570 | +3.987 | 1.819 | +2.168 | 0.344 | 0.0000 | 0.0000 | 0.0003 | 0.0000 | +0.711 | ✓ | 4 | 0.583 | PAIR_PROMOTED_CANDIDATE | — |
| vsg_jpy_reversal | EUR_JPY | overlap_LN | London | range | DT | BUY | 50 | 40 | 0.800 | 0.670 | 0.570 | +3.542 | 2.125 | +1.417 | 0.337 | 0.0000 | 0.0000 | 0.0003 | 0.0000 | +0.700 | ✓ | 4 | 0.714 | PAIR_PROMOTED_CANDIDATE | — |
| sr_liquidity_grab | USD_JPY | overlap_LN | London | range | DT | BUY | 50 | 37 | 0.740 | 0.605 | 0.507 | +3.094 | 1.819 | +1.275 | 0.344 | 0.0007 | 0.0014 | 0.0096 | 0.0014 | +0.596 | ✓ | 3 | 0.333 | PAIR_PROMOTED_CANDIDATE | — |

## Notes on statistical philosophy

- `p_bonf_strategy` uses m = (cells with n>=10 within that strategy). This matches per-strategy decision boundaries (Aggregate Fallacy 回避: CLAUDE.md クオンツ判断プロトコル).
- `p_bonf_global` uses m_global = Σ m_strategy across all 7. Treats the audit as one family — useful when comparing candidates across strategies. PAIR_PROMOTED_CANDIDATE flag uses the per-strategy column by design.
- `wilson_lower_bf` uses z=3.29 (≈ alpha=0.001) for a stricter lower bound that survives multiple-testing scrutiny.
