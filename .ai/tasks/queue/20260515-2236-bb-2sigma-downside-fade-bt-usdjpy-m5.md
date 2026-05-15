---
id: 20260515-2236-bb-2sigma-downside-fade-bt-usdjpy-m5
title: "[BB 2σ Down-Fade USDJPY M5] close<BB_lo & RSI極端 → long-only fade BT + 既存 bb_rsi ablation"
owner: codex
status: queued
priority: P1
created_at: 2026-05-15T22:36:00+0900
roadmap_gate: "TV MCP 500本 M5 USDJPY snapshot で BB(20,2σ) close-outside-band fade を down-side 14 / up-side 36 で N=50 集計、long側 (down-fade) mean +6.08 pip / 6bar、short側 (up-fade) +1.75 pip / 6bar。Asymmetric は USDJPY uptrend bias 由来の可能性大。既存 strategies/scalp/bb_rsi.py が直接対応だが W4-EDA で long-only 切り出し検証は未済。本 task は (a) BB len/mult/RSI threshold/time-stop の 4D grid を MASSIVE 12.3y で長期 BT (b) long-only と long+short の bias 分離 (c) 既存 bb_rsi 実装との ablation。MA trend filter は MR 破壊が既知 (feedback_ma_filter_breaks_mr) なので追加しない。"
rule: pre-reg
related:
  - strategies/scalp/bb_rsi.py
  - strategies/scalp/bb_rsi_ema_aligned.py
  - strategies/scalp/engulfing_bb.py
  - tools/fetch_massive_data.py
  - data/cache/massive/USD_JPY_M5.parquet
  - project_w4_eda_complete_2026_05_05
  - feedback_shadow_first_quant_architecture
  - feedback_bt_must_use_massive
  - feedback_partial_quant_trap
  - feedback_ma_filter_breaks_mr
  - feedback_codex_mock_test_trap
  - feedback_codex_stash_leak
  - feedback_exclude_xau
  - project_sr_weight_phase2_accept_2026_05_11
---

# 0. 思想と背景

## 0.1 観察 (TV MCP 41h snapshot 2026-05-15)

USDJPY M5, BB(20, 2σ) close-outside band 50 イベント、time-stop 6bar:

| Side | N | revert-to-SMA% / 6bar | mean P/L pip |
|---|---|---|---|
| Up overshoot (short) | 36 | 33.3% | +1.75 |
| **Down overshoot (long)** | **14** | 35.7% | **+6.08** |
| All | 50 | 34.0% | +2.96 |

Long側が rich だが 41h で USDJPY が +0.4% drift していたため "long the dip" バイアスを拾った可能性大。
本 task で 12.3y 長期に asymmetry が persist するか検証。

## 0.2 既存戦略との関係

- `strategies/scalp/bb_rsi.py` (BB + RSI MR の M5 実装) が直接対応
- `bb_rsi_ema_aligned.py`: EMA filter 版 — `feedback_ma_filter_breaks_mr` (MA trend filter で MR の Kelly 0.43→0) で edge 破壊が既知、ablation の **反例** として比較

## 0.3 本 task の本質

W4-EDA 「思想は正、設計が誤」91% 罠回避。
- 既存 bb_rsi は **長短両方向** で EV 評価されてきた → long-only 切り出しでの本当の edge を分離測定
- MR filter は MA を **足さない**

# 1. 設計

## 1.1 データ

- pair: USD_JPY のみ、TF M5
- ソース: MASSIVE `data/cache/massive/USD_JPY_M5.parquet`、12.3y
- spread 1.3 pip 両側、XAU 除外

## 1.2 Hypothesis Family A (純粋 long-only)

bar t:

```
mid, up, lo = BB(close, len=L, mult=M)
rsi_t       = RSI(close, 14)
trigger_L   = close_t < lo_t and rsi_t < R
trigger_S   = close_t > up_t and rsi_t > (100-R)
```

`trigger_L` → bar t close で **long entry**
`trigger_S` → bar t close で **short entry** (Family A2)
- TP: mid touch or +1.0 * ATR14
- SL: -1.5 * ATR14
- Time stop: H bar
- cooldown: 3 bar

## 1.3 Cell Grid

```
L        ∈ {20, 30}                  # 2 BB len
M        ∈ {2.0, 2.5}                # 2 BB mult
R        ∈ {25, 30}                  # 2 RSI threshold
H_bar    ∈ {6, 12}                   # 2 time stop
session  ∈ {ALL, LONDON_07-14_UTC}   # 2
```

`Family A_long` (long-only) と `Family A_short` (short-only) を **per cell で独立評価**。
合計 cell: 2 × 2 × 2 × 2 × 2 × 2 (side) = **64 cell**
Bonferroni: α = 0.05 / 64 = **0.00078**

## 1.4 Family B: 既存 bb_rsi ablation

`strategies/scalp/bb_rsi.py` の `signal()` を同 cell パラメータで再走、long-only と short-only に分離。差分項目:
- entry condition の追加 filter (EMA / engulfing / volume)
- exit (TP/SL units)
- direction logic
Family A vs B per cell の WR/EV/PF 差分を `ablation.md` に。

## 1.5 Verdict Gate

| Gate | 条件 |
|---|---|
| G1 | N ≥ 30 / cell |
| G2 | Wilson_lower ≥ 0.50 |
| G3 | EV (pip after spread) > 0 |
| G4 | BH-FDR p < 0.00078 (m=64) |
| G5 | PF ≥ 1.20 |
| G6 | Kelly ≥ 0.05 |
| G7 | 3-fold WF 全 fold EV>0 |
| G8 | **Long-only と Short-only で sign 一致** = symmetric edge / **不一致** = direction-led null 警戒 |

判定:
- **SHADOW_CANDIDATE**: G1-G7 通過 → long と short どちらかが survivor なら `strategies/scalp/bb_2sigma_fade_l.py` or `_s.py` 新規
- **DIRECTION_LED_NULL**: G1-G3 通過, G4 fail かつ G8 sign 不一致 → drift 由来と判定、REJECT 扱い
- **REJECT**: G1 or G2 or G3 fail

## 1.6 Anti-罠

- **MA filter 禁止** (feedback_ma_filter_breaks_mr)
- long と short の bias を必ず分離測定 (Phase 1c で direction-led null を検出した教訓: project_phase1b_oanda_contrarian_bt_2026_05_07)
- Family A vs B ablation で「既存 bb_rsi のどの設計要素が edge を殺しているか」明示

# 2. 成果物

```
tools/bb_2sigma_fade_bt.py
tools/bb_2sigma_fade_ablation.py
reports/bb_2sigma_fade_bt/
  ├ summary.md
  ├ ablation.md
  ├ per_cell/*.json
  ├ wf_3fold/*.json
  └ null_summary.md
strategies/scalp/bb_2sigma_fade_l.py    # G1-G7 通過時のみ
strategies/scalp/bb_2sigma_fade_s.py    # 同上 (short)
tests/test_bb_2sigma_fade.py
```

# 3. 禁止事項

- `bb_rsi.py` / `bb_rsi_ema_aligned.py` 既存ファイル編集禁止 (ablation の現行 baseline 不変)
- MA trend filter 追加禁止 (`feedback_ma_filter_breaks_mr`)
- 本番 `.env` / OANDA / live DB 触らない
- XAU 除外
