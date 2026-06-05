# TP-HIT 12-cell portfolio validation

- status: OK
- source: Render Production demo_trades.db shadow CLOSED rows
- generated_at: 2026-06-05T04:41:23Z
- promote_recommended: none
- rerun_access_note: 2026-06-05 current container could not re-fetch Production: ssh binary/key unavailable and /api/demo/trades returned HTTP 502; this file preserves the existing same-day Production shadow result generated at 2026-06-05T04:41:23Z.
- bt_sanity_role: BT sanity data availability only; exact per-strategy BT is substituted by shadow realized daily PnL when no unified frozen-cell runner exists.
- massive_all_required_pair_tf_available: False
- massive_missing: data/cache/massive/EUR_JPY_5m.parquet, data/cache/massive/EUR_USD_5m.parquet, data/cache/massive/GBP_USD_5m.parquet, data/cache/massive/USD_JPY_15m.parquet

## Gate table

| cell | N | WR | PF | Wilson95 lo | Bonf lo | EV | Kelly | WF +folds | H1 | verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| dt_bb_rsi_mr\|EUR_USD\|SELL | 38 | 0.526 | 2.083045 | 0.373 | 0.272 | 2.471 | 0.259 | 3/3 | FAIL | REJECT |
| dt_sr_channel_reversal\|USD_JPY\|BUY | 24 | 0.458 | 1.468886 | 0.279 | 0.181 | 1.350 | 0.146 | 2/3 | FAIL | REJECT |
| dt_bb_rsi_mr\|GBP_USD\|SELL | 38 | 0.579 | 1.801527 | 0.422 | 0.314 | 2.211 | 0.258 | 2/3 | PASS | REJECT |
| wick_imbalance_reversion\|EUR_USD\|BUY | 64 | 0.484 | 2.779221 | 0.366 | 0.286 | 3.425 | 0.305 | 2/3 | FAIL | REJECT |
| sr_fib_confluence\|EUR_USD\|BUY | 77 | 0.377 | 1.217593 | 0.277 | 0.213 | 0.732 | 0.067 | 1/3 | FAIL | REJECT |
| orb_trap\|GBP_USD\|SELL | 23 | 0.783 | 13.566474 | 0.581 | 0.420 | 9.452 | 0.725 | 3/3 | FAIL | REJECT |
| wick_imbalance_reversion\|GBP_USD\|BUY | 61 | 0.426 | 1.80963 | 0.310 | 0.235 | 2.370 | 0.191 | 2/3 | FAIL | REJECT |
| trendline_sweep\|EUR_USD\|SELL | 34 | 0.353 | 1.249108 | 0.215 | 0.142 | 1.026 | 0.070 | 2/3 | FAIL | REJECT |
| dual_sr_bounce\|EUR_JPY\|SELL | 27 | 0.444 | 0.984698 | 0.276 | 0.183 | -0.063 | -0.007 | 1/3 | FAIL | REJECT |
| sr_anti_hunt_bounce\|EUR_JPY\|BUY | 21 | 0.714 | 6.384058 | 0.500 | 0.348 | 14.152 | 0.602 | 2/3 | FAIL | REJECT |
| dt_sr_channel_reversal\|EUR_JPY\|BUY | 28 | 0.393 | 1.491171 | 0.236 | 0.153 | 2.682 | 0.129 | 2/3 | FAIL | REJECT |
| rsk_gbpjpy_reversion\|GBP_JPY\|BUY | 35 | 0.400 | 0.977119 | 0.256 | 0.174 | -0.309 | -0.009 | 2/3 | FAIL | REJECT |

## Portfolio

- status: OK
- cells: 12
- days: 41
- maxDD_pips: 13.933661
- calmar: 38.202788
- monthly_sharpe: 2.472281
- dd20_monthly_expectancy_raw_pips: 44.358726
- dd20_monthly_expectancy_bonf_0_5_pips: 22.179363

## Rejections

- `dt_bb_rsi_mr|EUR_USD|SELL`: Wilson95 lower <0.40, Bonferroni Wilson lower <0.40
- `dt_sr_channel_reversal|USD_JPY|BUY`: N<30, Wilson95 lower <0.40, WF 3-fold sign not all positive, Bonferroni Wilson lower <0.40
- `dt_bb_rsi_mr|GBP_USD|SELL`: WF 3-fold sign not all positive, Bonferroni Wilson lower <0.40
- `wick_imbalance_reversion|EUR_USD|BUY`: Wilson95 lower <0.40, WF 3-fold sign not all positive, Bonferroni Wilson lower <0.40
- `sr_fib_confluence|EUR_USD|BUY`: Wilson95 lower <0.40, WF 3-fold sign not all positive, Bonferroni Wilson lower <0.40
- `orb_trap|GBP_USD|SELL`: N<30
- `wick_imbalance_reversion|GBP_USD|BUY`: Wilson95 lower <0.40, WF 3-fold sign not all positive, Bonferroni Wilson lower <0.40
- `trendline_sweep|EUR_USD|SELL`: Wilson95 lower <0.40, WF 3-fold sign not all positive, Bonferroni Wilson lower <0.40
- `dual_sr_bounce|EUR_JPY|SELL`: N<30, Wilson95 lower <0.40, EV<0, WF 3-fold sign not all positive, Bonferroni Wilson lower <0.40
- `sr_anti_hunt_bounce|EUR_JPY|BUY`: N<30, WF 3-fold sign not all positive, Bonferroni Wilson lower <0.40
- `dt_sr_channel_reversal|EUR_JPY|BUY`: N<30, Wilson95 lower <0.40, WF 3-fold sign not all positive, Bonferroni Wilson lower <0.40
- `rsk_gbpjpy_reversion|GBP_JPY|BUY`: Wilson95 lower <0.40, EV<0, WF 3-fold sign not all positive, Bonferroni Wilson lower <0.40
