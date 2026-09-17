# Cell Deepdive — vsg_jpy_reversal

- **Date (UTC)**: 2026-04-28
- **Window**: 365d  (2025-04-28T05:12:06.378391+00:00 → now)
- **Source**: smoke fixture  (regime: self_reported)
- **Cells displayed (n>=10)**: 2
- **PAIR_PROMOTED candidates (n>=30, all gates pass)**: 1
- **Bonferroni m (this strategy)**: 2  | **m global (7 strategies)**: 14

## PAIR_PROMOTED Candidates

| pair | session | hour_bin | regime | mode | direction | n | wins | wr | wilson_lower_95 | wilson_lower_bf | ev_pip | friction_pip | ev_net_pip | bev_wr | p_raw | p_bonf_strategy | p_bonf_global | p_bh_fdr | kelly_f | wf_stable | wf_folds_positive | wf_oos_wr_min | recommendation | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EUR_JPY | overlap_LN | London | range | DT | BUY | 50 | 40 | 0.800 | 0.670 | 0.570 | +3.542 | 2.125 | +1.417 | 0.337 | 0.0000 | 0.0000 | 0.0003 | 0.0000 | +0.700 | ✓ | 4 | 0.714 | PAIR_PROMOTED_CANDIDATE | — |

## All Cells (n >= 10), ranked by Wilson lower (BF, z=3.29)

| pair | session | hour_bin | regime | mode | direction | n | wins | wr | wilson_lower_95 | wilson_lower_bf | ev_pip | friction_pip | ev_net_pip | bev_wr | p_raw | p_bonf_strategy | p_bonf_global | p_bh_fdr | kelly_f | wf_stable | wf_folds_positive | wf_oos_wr_min | recommendation | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EUR_JPY | overlap_LN | London | range | DT | BUY | 50 | 40 | 0.800 | 0.670 | 0.570 | +3.542 | 2.125 | +1.417 | 0.337 | 0.0000 | 0.0000 | 0.0003 | 0.0000 | +0.700 | ✓ | 4 | 0.714 | PAIR_PROMOTED_CANDIDATE | — |
| GBP_JPY | NY | NY_overlap | down_trend | Scalp | SELL | 20 | 5 | 0.250 | 0.112 | 0.067 | -3.202 | 4.410 | -7.612 | 0.380 | 0.0254 | 0.0507 | 0.3549 | 0.0254 | -1.656 | ✗ | 0 | 0.000 | DEAD | ev_net=-7.61<-1.0, kelly=-1.656<0 |
