# Cell Deepdive — sr_anti_hunt_bounce

- **Date (UTC)**: 2026-04-28
- **Window**: 365d  (2025-04-28T05:12:06.378391+00:00 → now)
- **Source**: smoke fixture  (regime: self_reported)
- **Cells displayed (n>=10)**: 2
- **PAIR_PROMOTED candidates (n>=30, all gates pass)**: 1
- **Bonferroni m (this strategy)**: 2  | **m global (7 strategies)**: 14

## PAIR_PROMOTED Candidates

| pair | session | hour_bin | regime | mode | direction | n | wins | wr | wilson_lower_95 | wilson_lower_bf | ev_pip | friction_pip | ev_net_pip | bev_wr | p_raw | p_bonf_strategy | p_bonf_global | p_bh_fdr | kelly_f | wf_stable | wf_folds_positive | wf_oos_wr_min | recommendation | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| USD_JPY | overlap_LN | London | range | DT | BUY | 50 | 40 | 0.800 | 0.670 | 0.570 | +3.987 | 1.819 | +2.168 | 0.344 | 0.0000 | 0.0000 | 0.0003 | 0.0000 | +0.711 | ✓ | 4 | 0.583 | PAIR_PROMOTED_CANDIDATE | — |

## All Cells (n >= 10), ranked by Wilson lower (BF, z=3.29)

| pair | session | hour_bin | regime | mode | direction | n | wins | wr | wilson_lower_95 | wilson_lower_bf | ev_pip | friction_pip | ev_net_pip | bev_wr | p_raw | p_bonf_strategy | p_bonf_global | p_bh_fdr | kelly_f | wf_stable | wf_folds_positive | wf_oos_wr_min | recommendation | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| USD_JPY | overlap_LN | London | range | DT | BUY | 50 | 40 | 0.800 | 0.670 | 0.570 | +3.987 | 1.819 | +2.168 | 0.344 | 0.0000 | 0.0000 | 0.0003 | 0.0000 | +0.711 | ✓ | 4 | 0.583 | PAIR_PROMOTED_CANDIDATE | — |
| GBP_JPY | NY | NY_overlap | down_trend | Scalp | SELL | 20 | 4 | 0.200 | 0.081 | 0.046 | -3.831 | 4.410 | -8.241 | 0.380 | 0.0073 | 0.0146 | 0.1021 | 0.0073 | -2.494 | ✗ | 0 | 0.000 | DEAD | ev_net=-8.24<-1.0, kelly=-2.494<0 |
