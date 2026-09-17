# Cell Deepdive — vdr_jpy

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
| USD_JPY | overlap_LN | London | range | DT | BUY | 50 | 32 | 0.640 | 0.501 | 0.411 | +2.665 | 1.819 | +0.846 | 0.344 | 0.0477 | 0.0954 | 0.6680 | 0.0477 | +0.489 | ✓ | 4 | 0.500 | WATCH | p_bonf_strat=0.0954>=0.05 |
| GBP_JPY | NY | NY_overlap | down_trend | Scalp | SELL | 20 | 4 | 0.200 | 0.081 | 0.046 | -3.736 | 4.410 | -8.146 | 0.380 | 0.0073 | 0.0146 | 0.1021 | 0.0146 | -1.786 | ✗ | 0 | 0.000 | DEAD | ev_net=-8.15<-1.0, kelly=-1.786<0 |
