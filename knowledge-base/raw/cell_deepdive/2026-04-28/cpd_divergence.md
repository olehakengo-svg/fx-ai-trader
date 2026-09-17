# Cell Deepdive — cpd_divergence

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
| GBP_USD | overlap_LN | London | range | DT | BUY | 50 | 34 | 0.680 | 0.542 | 0.449 | +2.687 | 3.851 | -1.164 | 0.379 | 0.0109 | 0.0218 | 0.1527 | 0.0218 | +0.514 | ✓ | 4 | 0.583 | DEAD | ev_net=-1.16<-1.0 |
| GBP_USD | NY | NY_overlap | down_trend | Scalp | SELL | 20 | 5 | 0.250 | 0.112 | 0.067 | -3.307 | 5.708 | -9.015 | 0.379 | 0.0254 | 0.0507 | 0.3549 | 0.0254 | -1.946 | ✗ | 0 | 0.000 | DEAD | ev_net=-9.02<-1.0, kelly=-1.946<0 |
