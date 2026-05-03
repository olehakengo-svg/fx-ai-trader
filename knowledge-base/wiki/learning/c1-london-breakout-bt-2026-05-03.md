# C-1 London Open Breakout BT (GBPJPY) — 2026-05-03 12yr Rerun

## Verdict

**Scenario: REJECT / Scenario C — catalog §C-1 academic only 降格候補**

12yr cache precondition は通過したが、pre-registered primary cell が Verdict matrix v1 の主要軸を満たさない。V2/V3 は sandbox network 制約で SKIP_NETWORK だが、H1/V1 の失格だけで REJECT 判定は確定する。Shadow promote / pre-registration LOCK は作成しない。

## Data Separation / Header

| Field | Value |
|---|---|
| data_source | `local_parquet:data/cache/massive/GBP_JPY_5m.parquet` |
| data_sha256 | `14d4ec64c99caea105f030ec079e53267e4c97770cc2ef38e5e5307d6cfb5bfe` |
| live_separation | `bt_only` |
| pair / interval | `GBP_JPY` / `M5` |
| requested window | 2014-01-01 to 2026-04-30 |
| actual bars | 925,109 (2014-01-02T04:55:00+00:00 to 2026-04-30T23:55:00+00:00) |
| git_sha / seed | `9d85bdcd9112e26cdb702572c50a3ffe41001809` / `20260503` |

## Precondition Gate

- Manifest check: `data/cache/massive/GBP_JPY_5m_2014_2026.parquet` and active `data/cache/massive/GBP_JPY_5m.parquet` both matched `sha256=14d4ec64c99c...`, `n_bars=925,109`.
- Loader check: `tools.bt.c1_london_breakout.load_local_cache("GBP_JPY")` read `data/cache/massive/GBP_JPY_5m.parquet`, 925,109 rows, 2014-01-02 04:55 UTC to 2026-04-30 23:55 UTC.
- V5 orphan check: `pgrep -f app.py` was attempted before BT and logged to `.ai/runs/20260503-183623-20260503-1830-w3-4-rerun-c1-london-breakout-gbpjpy-12yr/orphan_check.log`; sandbox returned `sysmond service not found`, so process-list cleanliness is not independently assertable in Codex.

## Primary Cell

Pre-registered primary: `(Asian 7h / M5 close break / range×1.0 exit / range >= median×1.0)`

| N | WR | Wilson lo | PF | OOS/IS | Bonf p | Bonf pass | Sharpe | Kelly | Raw pip | Net pip | Max DD |
|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| 662 | 45.62% | 41.86% | 1.012699 | 0.97 | 1 | False | 0.08 | 0.0057 | 734.15 | 164.83 | -1453.14 |

### Matrix Pass/Fail

| Axis | Threshold | Pass |
|---|---:|---|
| N | >=30 | True |
| Wilson lo | >=50% | False |
| PF | >=1.10 | False |
| OOS/IS PF | >=0.80 | True |
| Bonferroni p | <0.05/81 | False |
| Sharpe | >=0.5 | False |
| Kelly | >0 | True |

## Validity Checks

| Check | Result | Evidence |
|---|---|---|
| V1 null bootstrap | REJECT | actual PF=1.012699, null p95 PF=1.174465, actual_gt_p95=False |
| V2 rsk correlation | SKIP_NETWORK | Codex sandbox DNS/network blocked; Render rsk_gbpjpy_reversion correlation must be rerun outside sandbox. |
| V3 broker cross-check | SKIP_NETWORK | Codex sandbox DNS/network blocked; same-cache cross-check is invalid. |
| V4 cohort consistency | REJECT | max_abs_share=2.828929; net totalが小さく、複数cohortの損益寄与が50%を超過 |
| V5 orphan check | BLOCKED_BY_SANDBOX | process-list access failed; log path recorded |
| V6 spread profile | RECORDED | entry hour spread subtracted; source `fallback friction-analysis.md London FX-only 0.86pip; H-1 audit files absent` |

## Cohorts

| Cohort | N | WR | PF | Net pip | Share |
|---|---:|---:|---:|---:|---:|
| 2014-2016 pre-Brexit | 129 | 46.51% | 1.098652 | 240.36 | 1.46 |
| 2016-2017 Brexit Vote | 67 | 43.28% | 0.800831 | -300.92 | -1.83 |
| 2018-2019 calm | 133 | 48.12% | 1.186544 | 412.42 | 2.50 |
| 2020 COVID | 61 | 34.43% | 0.683225 | -371.91 | -2.26 |
| 2021-2022 Truss budget | 108 | 44.44% | 0.808489 | -466.29 | -2.83 |
| 2023-2024 | 105 | 51.43% | 1.206289 | 461.15 | 2.80 |
| 2025-2026 | 59 | 44.07% | 1.194363 | 190.02 | 1.15 |

## 81 Cell Sensitivity Grid

| cell | N | WR | Wilson | PF | OOS/IS | Bonf p | Sharpe | Kelly | Net pip |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| aw6_close_time_12utc_rf1.0 | 820 | 42.80% | 39.46% | 1.01101 | 1.01 | 1 | 0.07 | 0.0047 | 186.23 |
| aw6_close_time_12utc_rf1.2 | 539 | 43.60% | 39.47% | 1.018835 | 0.84 | 1 | 0.12 | 0.0081 | 217.81 |
| aw6_close_time_12utc_rf1.5 | 285 | 44.56% | 38.90% | 1.057055 | 0.85 | 1 | 0.34 | 0.0241 | 374.18 |
| aw6_close_range_1.0_rf1.0 | 820 | 44.51% | 41.14% | 0.980717 | 0.98 | 1 | -0.13 | 0.0000 | -320.82 |
| aw6_close_range_1.0_rf1.2 | 539 | 44.90% | 40.75% | 1.003129 | 0.88 | 1 | 0.02 | 0.0014 | 35.87 |
| aw6_close_range_1.0_rf1.5 | 285 | 44.91% | 39.24% | 1.009976 | 0.88 | 1 | 0.06 | 0.0044 | 65.37 |
| aw6_close_range_1.5_rf1.0 | 820 | 43.29% | 39.94% | 1.040852 | 1.03 | 1 | 0.26 | 0.0170 | 687.18 |
| aw6_close_range_1.5_rf1.2 | 539 | 43.78% | 39.65% | 1.05374 | 0.92 | 1 | 0.33 | 0.0223 | 620.11 |
| aw6_close_range_1.5_rf1.5 | 285 | 44.56% | 38.90% | 1.100953 | 0.96 | 1 | 0.60 | 0.0409 | 662.07 |
| aw6_high_break_time_12utc_rf1.0 | 940 | 44.68% | 41.53% | 1.44089 | 0.92 | 1 | 2.18 | 0.1367 | 7174.55 |
| aw6_high_break_time_12utc_rf1.2 | 615 | 45.85% | 41.95% | 1.482161 | 0.75 | 1 | 2.34 | 0.1492 | 5399.50 |
| aw6_high_break_time_12utc_rf1.5 | 328 | 47.56% | 42.22% | 1.62721 | 0.83 | 1 | 2.85 | 0.1833 | 3957.20 |
| aw6_high_break_range_1.0_rf1.0 | 940 | 46.70% | 43.53% | 1.389365 | 0.97 | 1 | 2.15 | 0.1309 | 6175.37 |
| aw6_high_break_range_1.0_rf1.2 | 615 | 46.99% | 43.08% | 1.429741 | 0.81 | 1 | 2.30 | 0.1412 | 4744.44 |
| aw6_high_break_range_1.0_rf1.5 | 328 | 47.56% | 42.22% | 1.509162 | 0.84 | 1 | 2.58 | 0.1605 | 3212.41 |
| aw6_high_break_range_1.5_rf1.0 | 940 | 45.43% | 42.27% | 1.450385 | 1.00 | 1 | 2.31 | 0.1411 | 7262.10 |
| aw6_high_break_range_1.5_rf1.2 | 615 | 46.18% | 42.27% | 1.477768 | 0.84 | 1 | 2.39 | 0.1493 | 5326.03 |
| aw6_high_break_range_1.5_rf1.5 | 328 | 47.56% | 42.22% | 1.616552 | 0.90 | 1 | 2.89 | 0.1814 | 3889.96 |
| aw6_m1_close_time_12utc_rf1.0 | 820 | 42.80% | 39.46% | 1.01101 | 1.01 | 1 | 0.07 | 0.0047 | 186.23 |
| aw6_m1_close_time_12utc_rf1.2 | 539 | 43.60% | 39.47% | 1.018835 | 0.84 | 1 | 0.12 | 0.0081 | 217.81 |
| aw6_m1_close_time_12utc_rf1.5 | 285 | 44.56% | 38.90% | 1.057055 | 0.85 | 1 | 0.34 | 0.0241 | 374.18 |
| aw6_m1_close_range_1.0_rf1.0 | 820 | 44.51% | 41.14% | 0.980717 | 0.98 | 1 | -0.13 | 0.0000 | -320.82 |
| aw6_m1_close_range_1.0_rf1.2 | 539 | 44.90% | 40.75% | 1.003129 | 0.88 | 1 | 0.02 | 0.0014 | 35.87 |
| aw6_m1_close_range_1.0_rf1.5 | 285 | 44.91% | 39.24% | 1.009976 | 0.88 | 1 | 0.06 | 0.0044 | 65.37 |
| aw6_m1_close_range_1.5_rf1.0 | 820 | 43.29% | 39.94% | 1.040852 | 1.03 | 1 | 0.26 | 0.0170 | 687.18 |
| aw6_m1_close_range_1.5_rf1.2 | 539 | 43.78% | 39.65% | 1.05374 | 0.92 | 1 | 0.33 | 0.0223 | 620.11 |
| aw6_m1_close_range_1.5_rf1.5 | 285 | 44.56% | 38.90% | 1.100953 | 0.96 | 1 | 0.60 | 0.0409 | 662.07 |
| aw7_close_time_12utc_rf1.0 | 662 | 44.56% | 40.82% | 0.968905 | 0.97 | 1 | -0.20 | 0.0000 | -408.02 |
| aw7_close_time_12utc_rf1.2 | 423 | 45.86% | 41.17% | 1.0071 | 1.02 | 1 | 0.05 | 0.0032 | 62.68 |
| aw7_close_time_12utc_rf1.5 | 237 | 45.99% | 39.76% | 0.976438 | 0.93 | 1 | -0.15 | 0.0000 | -132.69 |
| aw7_close_range_1.0_rf1.0 **PRIMARY** | 662 | 45.62% | 41.86% | 1.012699 | 0.97 | 1 | 0.08 | 0.0057 | 164.83 |
| aw7_close_range_1.0_rf1.2 | 423 | 46.57% | 41.87% | 1.070431 | 1.04 | 1 | 0.44 | 0.0306 | 613.95 |
| aw7_close_range_1.0_rf1.5 | 237 | 46.41% | 40.17% | 1.040851 | 0.96 | 1 | 0.26 | 0.0182 | 228.56 |
| aw7_close_range_1.5_rf1.0 | 662 | 44.56% | 40.82% | 0.985098 | 1.00 | 1 | -0.10 | 0.0000 | -195.54 |
| aw7_close_range_1.5_rf1.2 | 423 | 45.86% | 41.17% | 1.045699 | 1.00 | 1 | 0.28 | 0.0200 | 403.41 |
| aw7_close_range_1.5_rf1.5 | 237 | 45.99% | 39.76% | 1.017074 | 0.90 | 1 | 0.11 | 0.0077 | 96.16 |
| aw7_high_break_time_12utc_rf1.0 | 817 | 42.47% | 39.13% | 0.956445 | 0.84 | 1 | -0.28 | 0.0000 | -727.93 |
| aw7_high_break_time_12utc_rf1.2 | 516 | 45.16% | 40.91% | 1.012366 | 0.92 | 1 | 0.08 | 0.0055 | 138.84 |
| aw7_high_break_time_12utc_rf1.5 | 301 | 42.52% | 37.07% | 0.902749 | 0.91 | 1 | -0.67 | 0.0000 | -759.42 |
| aw7_high_break_range_1.0_rf1.0 | 817 | 43.82% | 40.45% | 0.996675 | 0.79 | 1 | -0.02 | 0.0000 | -54.82 |
| aw7_high_break_range_1.0_rf1.2 | 516 | 46.12% | 41.87% | 1.051663 | 0.88 | 1 | 0.33 | 0.0227 | 573.00 |
| aw7_high_break_range_1.0_rf1.5 | 301 | 42.86% | 37.39% | 0.929147 | 0.91 | 1 | -0.49 | 0.0000 | -550.87 |
| aw7_high_break_range_1.5_rf1.0 | 817 | 42.47% | 39.13% | 0.973416 | 0.89 | 1 | -0.17 | 0.0000 | -444.30 |
| aw7_high_break_range_1.5_rf1.2 | 516 | 45.16% | 40.91% | 1.048102 | 0.91 | 1 | 0.30 | 0.0207 | 540.09 |
| aw7_high_break_range_1.5_rf1.5 | 301 | 42.52% | 37.07% | 0.948069 | 0.98 | 1 | -0.34 | 0.0000 | -405.52 |
| aw7_m1_close_time_12utc_rf1.0 | 662 | 44.56% | 40.82% | 0.968905 | 0.97 | 1 | -0.20 | 0.0000 | -408.02 |
| aw7_m1_close_time_12utc_rf1.2 | 423 | 45.86% | 41.17% | 1.0071 | 1.02 | 1 | 0.05 | 0.0032 | 62.68 |
| aw7_m1_close_time_12utc_rf1.5 | 237 | 45.99% | 39.76% | 0.976438 | 0.93 | 1 | -0.15 | 0.0000 | -132.69 |
| aw7_m1_close_range_1.0_rf1.0 | 662 | 45.62% | 41.86% | 1.012699 | 0.97 | 1 | 0.08 | 0.0057 | 164.83 |
| aw7_m1_close_range_1.0_rf1.2 | 423 | 46.57% | 41.87% | 1.070431 | 1.04 | 1 | 0.44 | 0.0306 | 613.95 |
| aw7_m1_close_range_1.0_rf1.5 | 237 | 46.41% | 40.17% | 1.040851 | 0.96 | 1 | 0.26 | 0.0182 | 228.56 |
| aw7_m1_close_range_1.5_rf1.0 | 662 | 44.56% | 40.82% | 0.985098 | 1.00 | 1 | -0.10 | 0.0000 | -195.54 |
| aw7_m1_close_range_1.5_rf1.2 | 423 | 45.86% | 41.17% | 1.045699 | 1.00 | 1 | 0.28 | 0.0200 | 403.41 |
| aw7_m1_close_range_1.5_rf1.5 | 237 | 45.99% | 39.76% | 1.017074 | 0.90 | 1 | 0.11 | 0.0077 | 96.16 |
| aw8_close_time_12utc_rf1.0 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_close_time_12utc_rf1.2 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_close_time_12utc_rf1.5 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_close_range_1.0_rf1.0 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_close_range_1.0_rf1.2 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_close_range_1.0_rf1.5 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_close_range_1.5_rf1.0 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_close_range_1.5_rf1.2 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_close_range_1.5_rf1.5 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_high_break_time_12utc_rf1.0 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_high_break_time_12utc_rf1.2 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_high_break_time_12utc_rf1.5 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_high_break_range_1.0_rf1.0 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_high_break_range_1.0_rf1.2 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_high_break_range_1.0_rf1.5 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_high_break_range_1.5_rf1.0 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_high_break_range_1.5_rf1.2 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_high_break_range_1.5_rf1.5 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_m1_close_time_12utc_rf1.0 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_m1_close_time_12utc_rf1.2 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_m1_close_time_12utc_rf1.5 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_m1_close_range_1.0_rf1.0 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_m1_close_range_1.0_rf1.2 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_m1_close_range_1.0_rf1.5 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_m1_close_range_1.5_rf1.0 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_m1_close_range_1.5_rf1.2 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_m1_close_range_1.5_rf1.5 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |

## Conclusion

- **Scenario C / REJECT**: primary cell は Wilson lo、PF、Bonferroni、Sharpe が不合格。V1 bootstrap も actual PF が null 95th percentile を下回る。
- 12yr data blocker は解消済み。今回のREJECTはデータ不足ではなく、pre-registered primaryの統計条件不成立によるもの。
- `knowledge-base/wiki/decisions/c1-london-breakout-pre-registration-2026-05-03.md` は Scenario A ではないため作成しない。
- 次アクション: `global-retail-fx-edges` の §C-1 を academic only / reject に更新する別タスク、または London Breakout を別pair/別仕様で扱うなら新pre-regとして切り直す。

## Artifacts

- Raw BT JSON: `knowledge-base/raw/bt-results/c1-london-breakout.json`
- Raw BT markdown: `knowledge-base/raw/bt-results/c1-london-breakout.md`
- Validity JSON: `knowledge-base/raw/bt-results/c1-london-breakout-validity.json`
- Run report: `.ai/runs/20260503-183623-20260503-1830-w3-4-rerun-c1-london-breakout-gbpjpy-12yr/final.md`

## Superseded Parent Partial Verdict

> Superseded by 12yr rerun on 2026-05-03 19:xx JST. Original parent BLOCKED_DATA section preserved below for audit trail.

# C-1 London Open Breakout BT (GBPJPY) — 2026-05-03

## Verdict

**Scenario: BLOCKED_DATA / 判定保留**

要求は GBPJPY M5 2014-01-01〜2026-04-30 の約12年検証だが、このcheckoutの local Massive parquet は 2025-10-14T00:00:00+00:00〜2026-04-15T01:45:00+00:00 の 36,523 bars / 184日分のみ。要求 4503日への coverage は 4.09% なので、Rule 1 の採用/棄却判定には使えない。

## Primary Cell

Pre-registered primary: `(Asian 7h / M5 close break / range×1.0 exit / range >= median×1.0)`

| N | WR | Wilson lo | PF | OOS/IS | Bonf p | Bonf pass | Sharpe | Kelly | Raw pip | Net pip | Max DD |
|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| 29 | 44.83% | 28.41% | 1.110465 | 0.00 | 1 | False | 0.67 | 0.0446 | 80.23 | 55.29 | -194.73 |

Matrix pass/fail:

| Axis | Pass |
|---|---|
| bonferroni_pass | False |
| kelly_gt_0 | True |
| n_ge_30 | False |
| oos_is_ge_0_80 | False |
| pf_ge_1_10 | True |
| sharpe_ge_0_5 | True |
| wilson_lo_ge_50 | False |

## 81 Cell Sensitivity Grid

| cell | N | WR | Wilson | PF | OOS/IS | Bonf p | Sharpe | Kelly | Net pip |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| aw6_close_time_12utc_rf1.0 | 37 | 40.54% | 26.35% | 1.175717 | 1.42 | 1 | 0.98 | 0.0606 | 110.94 |
| aw6_close_time_12utc_rf1.2 | 27 | 40.74% | 24.51% | 0.926011 | 0.00 | 1 | -0.50 | 0.0000 | -38.46 |
| aw6_close_time_12utc_rf1.5 | 19 | 42.11% | 23.14% | 1.112733 | 0.00 | 1 | 0.67 | 0.0427 | 36.91 |
| aw6_close_range_1.0_rf1.0 | 37 | 40.54% | 26.35% | 1.04811 | 0.93 | 1 | 0.30 | 0.0186 | 30.37 |
| aw6_close_range_1.0_rf1.2 | 27 | 40.74% | 24.51% | 0.932744 | 0.00 | 1 | -0.45 | 0.0000 | -34.96 |
| aw6_close_range_1.0_rf1.5 | 19 | 42.11% | 23.14% | 1.101127 | 0.00 | 1 | 0.61 | 0.0387 | 33.11 |
| aw6_close_range_1.5_rf1.0 | 37 | 40.54% | 26.35% | 1.151803 | 1.12 | 1 | 0.88 | 0.0534 | 95.84 |
| aw6_close_range_1.5_rf1.2 | 27 | 40.74% | 24.51% | 0.926011 | 0.00 | 1 | -0.50 | 0.0000 | -38.46 |
| aw6_close_range_1.5_rf1.5 | 19 | 42.11% | 23.14% | 1.112733 | 0.00 | 1 | 0.67 | 0.0427 | 36.91 |
| aw6_high_break_time_12utc_rf1.0 | 44 | 56.82% | 42.22% | 1.941107 | 0.62 | 1 | 3.82 | 0.2755 | 500.31 |
| aw6_high_break_time_12utc_rf1.2 | 34 | 55.88% | 39.45% | 1.679612 | 0.32 | 1 | 3.16 | 0.2261 | 297.54 |
| aw6_high_break_time_12utc_rf1.5 | 23 | 56.52% | 36.81% | 2.045123 | 0.00 | 1 | 4.28 | 0.2888 | 292.11 |
| aw6_high_break_range_1.0_rf1.0 | 44 | 61.36% | 46.62% | 2.282067 | 0.43 | 1 | 5.16 | 0.3447 | 609.88 |
| aw6_high_break_range_1.0_rf1.2 | 34 | 61.76% | 45.04% | 2.337402 | 0.17 | 1 | 5.36 | 0.3534 | 510.74 |
| aw6_high_break_range_1.0_rf1.5 | 23 | 60.87% | 40.79% | 2.656081 | 0.00 | 1 | 6.11 | 0.3795 | 410.11 |
| aw6_high_break_range_1.5_rf1.0 | 44 | 59.09% | 44.41% | 2.17986 | 0.47 | 1 | 4.61 | 0.3198 | 589.65 |
| aw6_high_break_range_1.5_rf1.2 | 34 | 58.82% | 42.22% | 2.038406 | 0.23 | 1 | 4.31 | 0.2997 | 421.54 |
| aw6_high_break_range_1.5_rf1.5 | 23 | 60.87% | 40.79% | 2.68031 | 0.00 | 1 | 5.88 | 0.3816 | 416.11 |
| aw6_m1_close_time_12utc_rf1.0 | 37 | 40.54% | 26.35% | 1.175717 | 1.42 | 1 | 0.98 | 0.0606 | 110.94 |
| aw6_m1_close_time_12utc_rf1.2 | 27 | 40.74% | 24.51% | 0.926011 | 0.00 | 1 | -0.50 | 0.0000 | -38.46 |
| aw6_m1_close_time_12utc_rf1.5 | 19 | 42.11% | 23.14% | 1.112733 | 0.00 | 1 | 0.67 | 0.0427 | 36.91 |
| aw6_m1_close_range_1.0_rf1.0 | 37 | 40.54% | 26.35% | 1.04811 | 0.93 | 1 | 0.30 | 0.0186 | 30.37 |
| aw6_m1_close_range_1.0_rf1.2 | 27 | 40.74% | 24.51% | 0.932744 | 0.00 | 1 | -0.45 | 0.0000 | -34.96 |
| aw6_m1_close_range_1.0_rf1.5 | 19 | 42.11% | 23.14% | 1.101127 | 0.00 | 1 | 0.61 | 0.0387 | 33.11 |
| aw6_m1_close_range_1.5_rf1.0 | 37 | 40.54% | 26.35% | 1.151803 | 1.12 | 1 | 0.88 | 0.0534 | 95.84 |
| aw6_m1_close_range_1.5_rf1.2 | 27 | 40.74% | 24.51% | 0.926011 | 0.00 | 1 | -0.50 | 0.0000 | -38.46 |
| aw6_m1_close_range_1.5_rf1.5 | 19 | 42.11% | 23.14% | 1.112733 | 0.00 | 1 | 0.67 | 0.0427 | 36.91 |
| aw7_close_time_12utc_rf1.0 | 29 | 44.83% | 28.41% | 1.138964 | 0.00 | 1 | 0.82 | 0.0547 | 69.56 |
| aw7_close_time_12utc_rf1.2 | 21 | 42.86% | 24.47% | 1.063244 | 0.00 | 1 | 0.39 | 0.0255 | 25.89 |
| aw7_close_time_12utc_rf1.5 | 14 | 50.00% | 26.80% | 1.506428 | 0.00 | 1 | 2.51 | 0.1681 | 116.21 |
| aw7_close_range_1.0_rf1.0 PRIMARY | 29 | 44.83% | 28.41% | 1.110465 | 0.00 | 1 | 0.67 | 0.0446 | 55.29 |
| aw7_close_range_1.0_rf1.2 | 21 | 42.86% | 24.47% | 1.03393 | 0.00 | 1 | 0.22 | 0.0141 | 13.89 |
| aw7_close_range_1.0_rf1.5 | 14 | 50.00% | 26.80% | 1.422321 | 0.00 | 1 | 2.22 | 0.1485 | 96.91 |
| aw7_close_range_1.5_rf1.0 | 29 | 44.83% | 28.41% | 1.206792 | 0.00 | 1 | 1.17 | 0.0768 | 103.51 |
| aw7_close_range_1.5_rf1.2 | 21 | 42.86% | 24.47% | 1.063244 | 0.00 | 1 | 0.39 | 0.0255 | 25.89 |
| aw7_close_range_1.5_rf1.5 | 14 | 50.00% | 26.80% | 1.506428 | 0.00 | 1 | 2.51 | 0.1681 | 116.21 |
| aw7_high_break_time_12utc_rf1.0 | 39 | 43.59% | 29.30% | 1.067556 | 1.51 | 1 | 0.41 | 0.0276 | 45.49 |
| aw7_high_break_time_12utc_rf1.2 | 27 | 37.04% | 21.53% | 0.912151 | 0.00 | 1 | -0.58 | 0.0000 | -48.72 |
| aw7_high_break_time_12utc_rf1.5 | 20 | 40.00% | 21.88% | 1.00523 | 0.00 | 1 | 0.03 | 0.0021 | 2.10 |
| aw7_high_break_range_1.0_rf1.0 | 39 | 43.59% | 29.30% | 1.011379 | 1.52 | 1 | 0.07 | 0.0049 | 7.66 |
| aw7_high_break_range_1.0_rf1.2 | 27 | 37.04% | 21.53% | 0.870501 | 0.00 | 1 | -0.90 | 0.0000 | -71.82 |
| aw7_high_break_range_1.0_rf1.5 | 20 | 40.00% | 21.88% | 0.946616 | 0.00 | 1 | -0.35 | 0.0000 | -21.40 |
| aw7_high_break_range_1.5_rf1.0 | 39 | 43.59% | 29.30% | 1.099461 | 1.61 | 1 | 0.59 | 0.0394 | 66.98 |
| aw7_high_break_range_1.5_rf1.2 | 27 | 37.04% | 21.53% | 0.912151 | 0.00 | 1 | -0.58 | 0.0000 | -48.72 |
| aw7_high_break_range_1.5_rf1.5 | 20 | 40.00% | 21.88% | 1.00523 | 0.00 | 1 | 0.03 | 0.0021 | 2.10 |
| aw7_m1_close_time_12utc_rf1.0 | 29 | 44.83% | 28.41% | 1.138964 | 0.00 | 1 | 0.82 | 0.0547 | 69.56 |
| aw7_m1_close_time_12utc_rf1.2 | 21 | 42.86% | 24.47% | 1.063244 | 0.00 | 1 | 0.39 | 0.0255 | 25.89 |
| aw7_m1_close_time_12utc_rf1.5 | 14 | 50.00% | 26.80% | 1.506428 | 0.00 | 1 | 2.51 | 0.1681 | 116.21 |
| aw7_m1_close_range_1.0_rf1.0 | 29 | 44.83% | 28.41% | 1.110465 | 0.00 | 1 | 0.67 | 0.0446 | 55.29 |
| aw7_m1_close_range_1.0_rf1.2 | 21 | 42.86% | 24.47% | 1.03393 | 0.00 | 1 | 0.22 | 0.0141 | 13.89 |
| aw7_m1_close_range_1.0_rf1.5 | 14 | 50.00% | 26.80% | 1.422321 | 0.00 | 1 | 2.22 | 0.1485 | 96.91 |
| aw7_m1_close_range_1.5_rf1.0 | 29 | 44.83% | 28.41% | 1.206792 | 0.00 | 1 | 1.17 | 0.0768 | 103.51 |
| aw7_m1_close_range_1.5_rf1.2 | 21 | 42.86% | 24.47% | 1.063244 | 0.00 | 1 | 0.39 | 0.0255 | 25.89 |
| aw7_m1_close_range_1.5_rf1.5 | 14 | 50.00% | 26.80% | 1.506428 | 0.00 | 1 | 2.51 | 0.1681 | 116.21 |
| aw8_close_time_12utc_rf1.0 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_close_time_12utc_rf1.2 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_close_time_12utc_rf1.5 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_close_range_1.0_rf1.0 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_close_range_1.0_rf1.2 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_close_range_1.0_rf1.5 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_close_range_1.5_rf1.0 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_close_range_1.5_rf1.2 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_close_range_1.5_rf1.5 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_high_break_time_12utc_rf1.0 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_high_break_time_12utc_rf1.2 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_high_break_time_12utc_rf1.5 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_high_break_range_1.0_rf1.0 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_high_break_range_1.0_rf1.2 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_high_break_range_1.0_rf1.5 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_high_break_range_1.5_rf1.0 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_high_break_range_1.5_rf1.2 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_high_break_range_1.5_rf1.5 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_m1_close_time_12utc_rf1.0 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_m1_close_time_12utc_rf1.2 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_m1_close_time_12utc_rf1.5 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_m1_close_range_1.0_rf1.0 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_m1_close_range_1.0_rf1.2 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_m1_close_range_1.0_rf1.5 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_m1_close_range_1.5_rf1.0 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_m1_close_range_1.5_rf1.2 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |
| aw8_m1_close_range_1.5_rf1.5 | 0 | 0.00% | 0.00% | 0.0 | 0.00 | 1 | 0.00 | 0.0000 | 0.00 |

## Validity Checks

| Check | Result | Evidence |
|---|---|---|
| V1 null bootstrap | REJECT | actual PF=1.110465, null p95 PF=2.299736, iterations=1000 |
| V2 rsk correlation | BLOCKED | Render API fetch failed in this environment: URLError: <urlopen error [Errno 8] nodename nor servname provided, or not known> |
| V3 broker cross-check | BLOCKED | insufficient intraday bars for 12-year cross-check |
| V4 cohort consistency | REJECT/BLOCKED_BY_COVERAGE | max_abs_share=1.0; local data is only 2025-2026 so older cohorts N=0 |
| V5 orphan check | BLOCKED_BY_SANDBOX | `pgrep -f app.py` could not access the process list (`sysmond service not found`); see `.ai/runs/20260503-171210-20260503-1642-w3-4-c1-london-breakout-gbpjpy-bt/orphan_check.log` |
| V6 spread profile | RECORDED | entry hour spread was subtracted from net PnL; fallback 0.86pip due missing H-1 audit file |

## Cohorts

| Cohort | N | WR | PF | Net pip | Share |
|---|---:|---:|---:|---:|---:|
| 2014-2016 pre-Brexit | 0 | 0.00% | 0.0 | 0.00 | 0.00 |
| 2016-2017 Brexit Vote | 0 | 0.00% | 0.0 | 0.00 | 0.00 |
| 2018-2019 calm | 0 | 0.00% | 0.0 | 0.00 | 0.00 |
| 2020 COVID | 0 | 0.00% | 0.0 | 0.00 | 0.00 |
| 2021-2022 Truss budget | 0 | 0.00% | 0.0 | 0.00 | 0.00 |
| 2023-2024 | 0 | 0.00% | 0.0 | 0.00 | 0.00 |
| 2025-2026 | 29 | 44.83% | 1.110465 | 55.29 | 1.00 |


## Artifacts

- Raw BT JSON: `knowledge-base/raw/bt-results/c1-london-breakout.json`
- Raw BT markdown: `knowledge-base/raw/bt-results/c1-london-breakout.md`
- Validity JSON: `knowledge-base/raw/bt-results/c1-london-breakout-validity.json`
- Run orphan log: `.ai/runs/20260503-171210-20260503-1642-w3-4-c1-london-breakout-gbpjpy-bt/orphan_check.log`

## Conclusion

現時点では **Shadow promote 候補にできない**。これは戦略の棄却ではなく、12年M5データ、Render API rsk系列、別broker M5 cross-checkが揃っていないための Rule 1 data blocker。

次アクションは GBPJPY M5 2014-01-01〜2026-04-30 の完全cacheを補充し、同じコマンド・同じseedで再実行すること。
