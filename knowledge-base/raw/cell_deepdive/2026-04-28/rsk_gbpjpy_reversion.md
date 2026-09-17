# Cell Deepdive — rsk_gbpjpy_reversion

- **Date (UTC)**: 2026-04-28
- **Window**: 365d  (2025-04-28T05:12:06.378391+00:00 → now)
- **Source**: smoke fixture  (regime: self_reported)
- **Cells displayed (n>=10)**: 2
- **PAIR_PROMOTED candidates (n>=30, all gates pass)**: 0
- **Bonferroni m (this strategy)**: 2  | **m global (7 strategies)**: 14

## PAIR_PROMOTED Candidates

_No cell passes all strict gates this run._

## All Cells (n >= 10), ranked by Wilson lower (BF, z=3.29)

| pair | session | hour_bin | regime | mode | direction | n | wins | wr | wilson_lower_95 | wilson_lower_bf | ev_pip | friction_pip | ev_net_pip | bev_wr | p_raw | p_bonf_strategy | p_bonf_global | p_bh_fdr | kelly_f | wf_stable | wf_folds_positive | wf_oos_wr_min | recommendation | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| GBP_JPY | overlap_LN | London | range | DT | BUY | 50 | 30 | 0.600 | 0.462 | 0.375 | +2.363 | 2.975 | -0.612 | 0.380 | 0.1573 | 0.3146 | 1.0000 | 0.1573 | +0.421 | ✓ | 4 | 0.500 | WATCH | wl_bf=0.375<=bev=0.380, p_bonf_strat=0.3146>=0.05, ev_net=-0.61<=0 |
| GBP_JPY | NY | NY_overlap | down_trend | Scalp | SELL | 20 | 4 | 0.200 | 0.081 | 0.046 | -3.943 | 4.410 | -8.353 | 0.380 | 0.0073 | 0.0146 | 0.1021 | 0.0146 | -2.258 | ✗ | 0 | 0.000 | DEAD | ev_net=-8.35<-1.0, kelly=-2.258<0 |
