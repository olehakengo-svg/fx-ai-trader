# Kalman D7 v18e JPY Cross-Pair MASSIVE 12y BT

Generated: 2026-06-07T06:18:40.540896+00:00

## 1. Replication of v18e Pine Logic in Python

Pseudocode:

```text
for each M15 bar:
  ema25 = EMA(close, 25), ema75 = EMA(close, 75), ema200 = EMA(close, 200)
  atr = Wilder RMA(true_range, 14)
  rsi = Wilder RSI(close, 14)
  atr_p20/p80 = rolling percentile(atr, 200, 20/80)
  perfect_up = ema25 > ema75 > ema200 and close > ema25
  po_up_start = perfect_up and not perfect_up[1]
  entry_signal = po_up_start
    and (close - ema200) / atr < 3.0
    and (ema25 - ema200) / atr < 3.0
    and atr_p20 <= atr < atr_p80
    and rsi < 70
    and UTC hour in [0,12) or [16,21)
  enter long on next bar open with 10% equity, 1 tick adverse slippage
  place initial stop entry - 2.0*ATR
  activate trailing after entry + round(1.0*ATR/mintick)
  trailing stop = highest high since activation - round(0.5*ATR/mintick)
```

Key discrepancies vs Pine / TV:

- The canonical Pine file `/Users/jg-n-012/test/kalman_d7_strategies/v18e_05ATR_trail.pine` was not present in this container, so this port uses the locked rule text from the task.
- EMA uses pandas `ewm(span, adjust=False, min_periods=period)`, matching the usual recursive EMA form but not TV warmup bit-for-bit.
- ATR/RSI use Wilder RMA via `ewm(alpha=1/length, adjust=False)`, the closest deterministic match to `ta.atr`/`ta.rsi`.
- ATR percentile uses pandas rolling quantile. Pine percentile interpolation may differ by one tick around the P20/P80 boundary.
- TradingView intrabar trailing path is not observable from OHLC. The simulator checks stops before same-bar new trail activation, then permits same-bar trail activation and hit if high/low both cross.
- TV trade timestamp replication could not be measured because no exported TV trade list was available in the repo.
- Data-source discrepancy: requested no-underscore M15 paths are absent. The runner records whether it used a repo-native underscore M15 alias or a MASSIVE 5m-to-M15 resample.

## 2. Per-Pair BT Summary

| Pair | Source | Years | N | WR | W95 LB | PF | p(logPF) | Net JPY | MaxDD | Sharpe | Avg Win | Avg Loss | Avg Bars |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| USDJPY | massive_5m_resampled_to_m15 | 12.32 | 922 | 65.94% | 62.82% | 0.861 | 0.9977 | -601.96 | 0.77% | -1.05 | 6.12 | -13.76 | 8.6 |
| EURJPY | alias_native_m15 | 12.33 | 1334 | 67.69% | 65.13% | 0.792 | 0.9982 | -1609.21 | 1.80% | -1.16 | 6.79 | -17.97 | 10.7 |
| GBPJPY | massive_5m_resampled_to_m15 | 12.32 | 1277 | 65.00% | 62.34% | 0.732 | 1.0000 | -2296.70 | 2.32% | -2.10 | 7.56 | -19.17 | 9.8 |
| AUDJPY | alias_native_m15 | 1.00 | 126 | 62.70% | 54.00% | 0.675 | 0.9939 | -321.81 | 0.40% | -2.79 | 8.45 | -21.05 | 9.2 |

## 3. WFO 3-Fold Per Pair

### USDJPY

Method: expanding train / next-quarter test; fixed parameters, no optimization

| Fold | Train | Test | N | PF | Net | PF>1 |
|---:|---|---|---:|---:|---:|---|
| 1 | 2014-01-31 -> 2017-02-20 | 2017-02-20 -> 2020-03-30 | 199 | 0.831 | -139.39 | FAIL |
| 2 | 2014-01-31 -> 2020-03-30 | 2020-03-31 -> 2023-05-11 | 270 | 0.742 | -367.98 | FAIL |
| 3 | 2014-01-31 -> 2023-05-11 | 2023-05-11 -> 2026-05-29 | 270 | 0.970 | -36.81 | FAIL |

All-fold PF > 1.0: FAIL

### EURJPY

Method: expanding train / next-quarter test; fixed parameters, no optimization

| Fold | Train | Test | N | PF | Net | PF>1 |
|---:|---|---|---:|---:|---:|---|
| 1 | 2014-01-05 -> 2017-03-14 | 2017-03-14 -> 2020-05-22 | 280 | 0.889 | -143.73 | FAIL |
| 2 | 2014-01-05 -> 2020-05-22 | 2020-05-22 -> 2023-04-03 | 350 | 0.835 | -340.57 | FAIL |
| 3 | 2014-01-05 -> 2023-04-03 | 2023-04-03 -> 2026-05-05 | 399 | 0.585 | -1195.47 | FAIL |

All-fold PF > 1.0: FAIL

### GBPJPY

Method: expanding train / next-quarter test; fixed parameters, no optimization

| Fold | Train | Test | N | PF | Net | PF>1 |
|---:|---|---|---:|---:|---:|---|
| 1 | 2014-01-31 -> 2017-04-07 | 2017-04-07 -> 2020-06-15 | 242 | 0.779 | -331.16 | FAIL |
| 2 | 2014-01-31 -> 2020-06-15 | 2020-06-15 -> 2023-04-19 | 376 | 0.629 | -1088.78 | FAIL |
| 3 | 2014-01-31 -> 2023-04-19 | 2023-04-19 -> 2026-05-29 | 387 | 0.762 | -599.86 | FAIL |

All-fold PF > 1.0: FAIL

### AUDJPY

Method: expanding train / next-quarter test; fixed parameters, no optimization

| Fold | Train | Test | N | PF | Net | PF>1 |
|---:|---|---|---:|---:|---:|---|
| 1 | 2025-05-28 -> 2025-08-26 | 2025-08-26 -> 2025-11-25 | 22 | 1.516 | 68.03 | PASS |
| 2 | 2025-05-28 -> 2025-11-25 | 2025-11-25 -> 2026-02-26 | 34 | 0.877 | -25.42 | FAIL |
| 3 | 2025-05-28 -> 2026-02-26 | 2026-02-26 -> 2026-05-29 | 30 | 0.515 | -119.37 | FAIL |

All-fold PF > 1.0: FAIL


## 4. Pairwise PnL Correlation Matrix + Effective Bonferroni

| Pair | USDJPY | EURJPY | GBPJPY | AUDJPY |
|---|---:|---:|---:|---:|
| USDJPY | 1.000 | 0.011 | 0.124 | 0.204 |
| EURJPY | 0.011 | 1.000 | 0.083 | 0.007 |
| GBPJPY | 0.124 | 0.083 | 1.000 | 0.106 |
| AUDJPY | 0.204 | 0.007 | 0.106 | 1.000 |

Max pairwise corr=0.204. Adjustment: max corr <= 0.50; pre-registered Bonferroni m=4. effective_m=4.000, alpha_eff=0.01250.

## 5. Per-Pair Pre-Reg Verdict

### USDJPY: REJECT

Source: Requested/native M15 parquet missing; used MASSIVE 5m cache resampled to M15, not Yahoo/OANDA.
Core stats: PF=0.861, WR=65.94%, Wilson95 LB=62.82%, N=922, Net=-601.96, MaxDD=0.77%.
Failed criteria: pf_ge_1_20; wfo_all_fold_pf_gt_1; pvalue_lt_alpha_eff; catastrophic_net_not_negative; catastrophic_pf_not_below_1.

### EURJPY: REJECT

Source: Requested no-underscore M15 parquet missing; used repo-native underscore M15 MASSIVE alias.
Core stats: PF=0.792, WR=67.69%, Wilson95 LB=65.13%, N=1334, Net=-1609.21, MaxDD=1.80%.
Failed criteria: pf_ge_1_20; wfo_all_fold_pf_gt_1; pvalue_lt_alpha_eff; catastrophic_net_not_negative; catastrophic_pf_not_below_1.

### GBPJPY: REJECT

Source: Requested/native M15 parquet missing; used MASSIVE 5m cache resampled to M15, not Yahoo/OANDA.
Core stats: PF=0.732, WR=65.00%, Wilson95 LB=62.34%, N=1277, Net=-2296.70, MaxDD=2.32%.
Failed criteria: pf_ge_1_20; wfo_all_fold_pf_gt_1; pvalue_lt_alpha_eff; catastrophic_net_not_negative; catastrophic_pf_not_below_1.

### AUDJPY: REJECT

Source: Requested no-underscore M15 parquet missing; used repo-native underscore M15 MASSIVE alias. Coverage is below the 12y target; pre-reg coverage gate fails.
Core stats: PF=0.675, WR=62.70%, Wilson95 LB=54.00%, N=126, Net=-321.81, MaxDD=0.40%.
Failed criteria: coverage_years_ge_10_8; pf_ge_1_20; wfo_all_fold_pf_gt_1; pvalue_lt_alpha_eff; catastrophic_net_not_negative; catastrophic_pf_not_below_1.


## 6. Recommendation

No pair qualifies for PASS_SHADOW_PROMOTE under the locked criteria. Marginal watchlist: none. Rejected: USDJPY, EURJPY, GBPJPY, AUDJPY. LIVE pair extension should wait for Stage 1 shadow evidence (N>=30 per pair) and a rerun with native 12y M15 inventory for any pair currently using partial or resampled candles.
