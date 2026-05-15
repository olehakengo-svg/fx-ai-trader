---
id: 20260515-2237-hourly-bias-utc-bt-usdjpy-m5
title: "[Hourly Bias UTC USDJPY M5] hour-of-day × weekday cohort EV grid + 既存 london_breakout / session_vol_expansion ablation"
owner: codex
status: queued
priority: P2
created_at: 2026-05-15T22:37:00+0900
roadmap_gate: "TV MCP 41h M5 snapshot で hour-of-day bias を集計し、UTC 06h = -0.676 bp / WR 29.2% (Tokyo→London 移行 fade)、05h = +0.345 bp / WR 70.8%、11h = +0.637 bp / WR 70.8% (London momentum) が観察。各 hour N=24 bar (= 2 日分) で statistical claim 不可。既存 strategies/scalp/london_breakout.py と session_vol_expansion.py が直接対応。本 task は (a) hour-of-day × weekday cohort 120 cell を MASSIVE 12.3y で BT (b) 既存 london_breakout ablation (c) Bonferroni m=120 厳格化 — session_vol_expansion / london_breakout の現行 verdict と整合性確認まで。低 priority だが session-based edge 探索の系統的 sanity check。"
rule: pre-reg
related:
  - strategies/scalp/london_breakout.py
  - strategies/scalp/session_vol_expansion.py
  - strategies/scalp/london_shrapnel.py
  - tools/fetch_massive_data.py
  - data/cache/massive/USD_JPY_M5.parquet
  - project_w4_eda_complete_2026_05_05
  - feedback_shadow_first_quant_architecture
  - feedback_bt_must_use_massive
  - feedback_partial_quant_trap
  - feedback_cohort_time_check
  - feedback_codex_mock_test_trap
  - feedback_codex_stash_leak
  - feedback_exclude_xau
---

# 0. 思想と背景

## 0.1 観察 (TV MCP 41h snapshot 2026-05-15)

USDJPY M5、各 UTC hour の log-return / WR (N=24 bar = 2日):

| Hour UTC | mean log-ret bp | WR% close>open |
|---|---|---|
| 01 | +0.329 | 66.7 |
| 05 | +0.345 | 70.8 |
| **06** | **-0.676** | **29.2** |
| **11** | **+0.637** | **70.8** |
| 21 | -0.040 | 37.5 |
| 22 | -0.019 | 33.3 |

Sign は明確だが N=24 で statistical claim 不可、本 task が長期検証の初手。

## 0.2 既存戦略との関係

- `strategies/scalp/london_breakout.py` (Ito & Hashimoto 2006) = London session opening break
- `strategies/scalp/session_vol_expansion.py` = session 切替時の vol expansion
- `strategies/scalp/london_shrapnel.py` = London follow-through

W4-EDA で監査済 (`project_w4_eda_complete_2026_05_05`)、現行 verdict と本 task の hourly grid 結果を整合性確認。

## 0.3 本 task の本質

- Cohort 整合性 (`feedback_cohort_time_check`): hour × weekday で時間帯偏りを排除
- 既存 london_breakout/session_vol_expansion の "session" 定義粒度を hourly に分解して edge 局在化

# 1. 設計

## 1.1 データ

- pair: USD_JPY、TF M5
- ソース: MASSIVE `data/cache/massive/USD_JPY_M5.parquet`、12.3y
- spread 1.3 pip 両側、XAU 除外

## 1.2 Hypothesis Family A (Pure hourly directional)

bar t の hour-of-day (UTC) と weekday (Mon-Fri):

```
cell(h, d) = bars where hour(t) == h and weekday(t) == d
```

各 cell で 2 種類の "trade" を測定:
- **Trade_L**: hour h の最初の bar open で long、hour h の最後の bar close で flat
- **Trade_S**: 同 hour で short

Cell ごとに per-day 1 トレード (long と short 別評価)、N = 営業日数 × ~12年 ≈ 3000日 / cell。

## 1.3 Cell Grid

```
hour    ∈ {0..23}        # 24
weekday ∈ {Mon..Fri}     # 5
side    ∈ {Long, Short}  # 2
```

= **24 × 5 × 2 = 240 cell**
Bonferroni: α = 0.05 / 240 = **0.000208**

## 1.4 Family B: 既存 london_breakout / session_vol_expansion ablation

両戦略の `signal()` を同 12.3y 期間で再走、hour × weekday cohort 分解して per-hour PF/EV を出す。Family A の "naive hourly long/short" との差分 (どの hour が既存 strategy で活用 / 未活用) を `ablation.md`。

## 1.5 Verdict Gate

per cell:

| Gate | 条件 |
|---|---|
| G1 | N ≥ 100 trade |
| G2 | Wilson_lower ≥ 0.55 (hourly edge は higher bar) |
| G3 | EV (pip after spread) > 0.5 (hourly のため厳しめ) |
| G4 | BH-FDR p < 0.000208 (m=240) |
| G5 | PF ≥ 1.30 |
| G6 | Kelly ≥ 0.08 |
| G7 | 3-fold WF 全 fold EV>0 |
| G8 | 同 hour の Long と Short が **sign 反対** = symmetric (drift-free) / **同 sign** = drift-led 警戒 |

判定:
- **SHADOW_CANDIDATE**: G1-G7 通過 → `strategies/scalp/hourly_bias_<hour>_<wd>.py` (combined hour-band 提案も可)
- **DRIFT_LED_NULL**: G1-G3 通過 G4 fail で G8 同 sign → long-term drift 由来、REJECT
- **REJECT**: G1 or G2 or G3 fail

## 1.6 Anti-罠

- `feedback_cohort_time_check`: hour 単独でなく weekday cohort と必ず分解
- `feedback_partial_quant_trap`: WR/EV 単独で結論しない
- post-hoc selection 罠 (`project_w3_3_s4_connors_raschke_queued` の教訓): grid 全 240 cell 一括 BH-FDR、top-N pick だけの cherry-pick 禁止

# 2. 成果物

```
tools/hourly_bias_bt.py
tools/hourly_bias_ablation.py
reports/hourly_bias_bt/
  ├ summary.md
  ├ ablation.md                 # vs london_breakout / session_vol_expansion
  ├ heatmap_hour_x_weekday.md   # PF table 24h × 5wd
  ├ per_cell/*.json
  ├ wf_3fold/*.json
  └ null_summary.md
strategies/scalp/hourly_bias_<cell>.py    # G1-G7 通過 cell のみ
tests/test_hourly_bias.py
```

# 3. 禁止事項

- `london_breakout.py` / `session_vol_expansion.py` / `london_shrapnel.py` 既存ファイル編集禁止 (ablation 不変前提)
- weekday を無視した hour-only 集計禁止 (cohort 罠)
- post-hoc に top-3 cell だけ pick して "edge 発見" の結論禁止
- XAU 除外、本番 `.env` / OANDA / live DB 触らない


## Error (2026-05-15T15:12:51Z)

```
orphaned: container restarted while task was running
```
