# Cell Deepdive — sr_liquidity_grab

- **Date (UTC)**: 2026-04-28
- **Window**: 365d  (2025-04-28T05:12:06.378391+00:00 → now)
- **Source**: smoke fixture  (regime: self_reported)
- **Cells displayed (n>=10)**: 2
- **PAIR_PROMOTED candidates (n>=30, all gates pass)**: 1
- **Bonferroni m (this strategy)**: 2  | **m global (7 strategies)**: 14

## PAIR_PROMOTED Candidates

| pair | session | hour_bin | regime | mode | direction | n | wins | wr | wilson_lower_95 | wilson_lower_bf | ev_pip | friction_pip | ev_net_pip | bev_wr | p_raw | p_bonf_strategy | p_bonf_global | p_bh_fdr | kelly_f | wf_stable | wf_folds_positive | wf_oos_wr_min | recommendation | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| USD_JPY | overlap_LN | London | range | DT | BUY | 50 | 37 | 0.740 | 0.605 | 0.507 | +3.094 | 1.819 | +1.275 | 0.344 | 0.0007 | 0.0014 | 0.0096 | 0.0014 | +0.596 | ✓ | 3 | 0.333 | PAIR_PROMOTED_CANDIDATE | — |

## All Cells (n >= 10), ranked by Wilson lower (BF, z=3.29)

| pair | session | hour_bin | regime | mode | direction | n | wins | wr | wilson_lower_95 | wilson_lower_bf | ev_pip | friction_pip | ev_net_pip | bev_wr | p_raw | p_bonf_strategy | p_bonf_global | p_bh_fdr | kelly_f | wf_stable | wf_folds_positive | wf_oos_wr_min | recommendation | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| USD_JPY | overlap_LN | London | range | DT | BUY | 50 | 37 | 0.740 | 0.605 | 0.507 | +3.094 | 1.819 | +1.275 | 0.344 | 0.0007 | 0.0014 | 0.0096 | 0.0014 | +0.596 | ✓ | 3 | 0.333 | PAIR_PROMOTED_CANDIDATE | — |
| GBP_JPY | NY | NY_overlap | down_trend | Scalp | SELL | 20 | 8 | 0.400 | 0.219 | 0.143 | -2.159 | 4.410 | -6.569 | 0.380 | 0.3711 | 0.7422 | 1.0000 | 0.3711 | -1.188 | ✗ | 0 | 0.200 | DEAD | ev_net=-6.57<-1.0, kelly=-1.188<0 |
