# Cell Deepdive — mqe_gbpusd_fix

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
| GBP_USD | overlap_LN | London | range | DT | BUY | 50 | 41 | 0.820 | 0.692 | 0.591 | +3.721 | 3.851 | -0.130 | 0.379 | 0.0000 | 0.0000 | 0.0001 | 0.0000 | +0.728 | ✓ | 4 | 0.667 | WATCH | ev_net=-0.13<=0 |
| GBP_USD | NY | NY_overlap | down_trend | Scalp | SELL | 20 | 3 | 0.150 | 0.052 | 0.028 | -3.816 | 5.708 | -9.524 | 0.379 | 0.0018 | 0.0035 | 0.0244 | 0.0018 | -1.960 | ✗ | 0 | 0.000 | DEAD | ev_net=-9.52<-1.0, kelly=-1.960<0 |
