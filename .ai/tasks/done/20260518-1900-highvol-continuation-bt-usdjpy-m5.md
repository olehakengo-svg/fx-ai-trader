---
id: 20260518-1900-highvol-continuation-bt-usdjpy-m5
title: "[HighVol Continuation USDJPY M5] body>=K*SMA20(body) at hours {9,11,15} UTC -> CONTINUATION direction BT (TV 1yr PF 1.234 確認済 candidate)"
owner: codex
status: queued
priority: P0
created_at: 2026-05-18T19:00:00+0900
roadmap_gate: "TV Strategy Tester 1 年 (May 2025 - May 2026) で USDJPY M5 を実機検証した結果、body/SMA20(body) >= K (K=3.5) で UTC hour ∈ {9, 11, 15} の bar 発生時、direction = bar の close>open 方向（=CONTINUATION）に entry / H=3 bar time-stop で N=141, WR=52.48%, PF=1.234, Net +120.40% を観測。K-sweep monotonic 改善（K=2.1: PF 0.99 → K=3.0: 1.124 → K=3.5: 1.234 → K=4.0: 1.241）が real signal の指紋。前 task 20260515-2235 (Vol Exhaustion FADE) は 48/48 REJECT だったが、本 task は逆方向 (continuation) を検証 — 既存 strategies/scalp/v_reversal.py は fade 方向、未テストの continuation 方向に edge がある可能性高。spread sensitivity: TV 計算で 0.43 pip round-trip 以下なら survives。Codex 12.3y MASSIVE + spread grid + WF 3-fold で formal verdict 取得。"
rule: pre-reg
related:
  - strategies/scalp/v_reversal.py
  - strategies/scalp/vol_surge.py
  - strategies/scalp/vol_momentum.py
  - strategies/scalp/three_bar_reversal.py
  - tools/vol_exhaustion_fade_bt.py
  - data/cache/massive/USD_JPY_5m_2014_2026.parquet
  - .ai/tasks/done/20260515-2235-vol-exhaustion-fade-bt-usdjpy-m5.md
  - reports/vol_exhaustion_fade_bt/
  - /tmp/usdjpy_m5_1yr_pattern.md
  - project_w4_eda_complete_2026_05_05
  - feedback_shadow_first_quant_architecture
  - feedback_bt_must_use_massive
  - feedback_partial_quant_trap
  - feedback_label_empirical_audit
  - feedback_success_until_achieved
  - feedback_ma_filter_breaks_mr
  - feedback_codex_mock_test_trap
  - feedback_codex_stash_leak
  - feedback_codex_schema_hallucination
  - feedback_exclude_xau
---

# 0. 思想と背景

## 0.1 TV Strategy Tester 1yr 実測 (2026-05-18)

USDJPY M5, 期間 2025-05-18 ~ 2026-05-18, hours UTC = {9, 11, 15}, direction = CONTINUATION (bar の close>open なら LONG / close<open なら SHORT), exit = H=3 bar time-stop, spread = 0 で K_mult をスイープ:

| K | N | WR | PF | Net | DD |
|---|---|---|---|---|---|
| 2.1 | 680 | 49.56% | 0.99  | -21%  | 205% |
| 3.0 | 211 | 50.24% | 1.124 | +97%  | 117% |
| **3.5** | **141** | **52.48%** | **1.234** | **+120%** | **83%** |
| 4.0 | 98  | 50.00% | 1.241 | +89%  | 67%  |

**Monotonic improvement** は real signal の典型指紋（noise なら non-monotonic）。
FADE 方向 (前 task 20260515-2235) は 48/48 全 cell REJECT、Wilson_lo 0.43、PF 0.41 → continuation 方向に edge が逆転している強い兆候。

## 0.2 直接比較 (TV ST 同 N=199 sample)

| Direction | WR | PF | Net |
|---|---|---|---|
| FADE        | 45.23% | 0.729 | -182% |
| CONTINUATION | 53.77% | 1.372 | +182% |

mirror image = signal は real, direction は continuation 確定。

## 0.3 Spread Sensitivity 手計算

- Breakeven round-trip spread = ¥12,040 / (141 × 2 × 10000 × ¥0.01) ≈ **0.43 pip**
- 国内 broker (GMO/DMM) 0.2 pip → 生存
- OANDA Japan 0.5 pip → marginal
- OANDA USA / TV ST 1.3 pip → 死亡

## 0.4 本 task の目的

(a) 12.3y MASSIVE で 1yr edge が persist するか formal verdict
(b) spread grid {0.0, 0.2, 0.5, 1.0, 1.3} pip で breakeven 確認
(c) Walk-Forward 3-fold で regime stability
(d) K / H / hour set / weekday cohort の Bonferroni-corrected grid sweep
(e) Family A (純粋 high-vol continuation) vs Family B (既存 v_reversal を direction-flip) ablation

# 1. 設計

## 1.1 データ

- pair: **USD_JPY のみ** (本 task), cross-pair OOS は Phase B
- TF: **M5**
- ソース: `data/cache/massive/USD_JPY_5m_2014_2026.parquet` (903,828 bars, 2014-01-02 ~ 2026-04-30 UTC)
- XAU 除外 (feedback_exclude_xau)

## 1.2 Hypothesis (Family A: 純粋 HighVol Continuation)

bar t で:

```
body_t   = |close_t - open_t|
sma20_t  = mean(body_{t-20..t-1})         # t 含まない
extreme  = body_t >= K * sma20_t
dir_t    = sign(close_t - open_t)
```

`extreme` and hour(t) in hourset → bar t close で `dir_t` 方向に entry。

- entry: bar t close (market order, slippage = spread_pip × pip_size 適用)
- exit: H_bar 後の close で成行
- cooldown: 3 bar (同 hour 内連続 extreme でも 1 トレード)

## 1.3 Cell Grid

```
K_mult     ∈ {2.5, 3.0, 3.5, 4.0, 4.5}        # 5
H_bar      ∈ {3, 6, 12}                       # 3
hourset    ∈ {AGENT_9_11_15, ALL, LONDON_07_14, NY_12_20, ASIAN_15_22}  # 5
spread_pip ∈ {0.0, 0.2, 0.5, 1.0, 1.3}        # 5
```

合計 cell = 5 × 3 × 5 × 5 = **375 cell**
Bonferroni: α = 0.05 / 375 = **0.000133**

## 1.4 Family B: 既存 v_reversal direction-flip ablation

`strategies/scalp/v_reversal.py` の signal 検出ロジックを使用し、direction を反転 (本来 reversal → continuation) して同 375 cell で run。
Family A vs B の per-cell diff を `reports/highvol_continuation_bt/ablation.md` に出力。

## 1.5 Verdict Gate (per cell, spread=0.5 pip baseline)

| Gate | 条件 |
|---|---|
| G1 N | N ≥ 30 |
| G2 Wilson | Wilson_lower(WR, N) ≥ 0.50 |
| G3 EV | EV (pip after spread) > 0 |
| G4 Bonf | BH-FDR adjusted p < 0.000133 (m=375) |
| G5 PF | PF ≥ 1.20 |
| G6 Kelly | Kelly fraction ≥ 0.05 |
| G7 WF | 3-fold Walk-Forward 全 fold で EV>0 (1yr OOS each) |
| G8 Direction-led null | Long-only と Short-only で sign 一致 = symmetric, 不一致 = drift-led (REJECT) |

判定:
- **SHADOW_CANDIDATE**: G1-G8 全通過 → `strategies/scalp/highvol_continuation_jpy_m5.py` 新規実装 + shadow 登録 spec
- **NEEDS_MORE_EVIDENCE**: G1-G3 通過, G4 or G5 or G6 fail → 再 grid 案 / spread sensitivity caveat
- **REJECT**: G1 or G2 or G3 fail or G8 direction-led null

## 1.6 Spread Sensitivity 報告

cells 全部について spread = {0.0, 0.2, 0.5, 1.0, 1.3} で EV/PF を出力し、各 cell の **breakeven spread (pip round-trip)** を計算。SHADOW_CANDIDATE cell については broker survival マッピング:
- GMO/DMM (0.2 pip): pass/fail
- OANDA Japan (0.5 pip): pass/fail
- OANDA USA (1.3+ pip): pass/fail

## 1.7 Anti-罠 チェック

- `feedback_ma_filter_breaks_mr`: MA trend filter を **足さない**
- `feedback_partial_quant_trap`: N/WR/EV だけで止めず PF/Wilson/Bonf/WF/Kelly まで報告
- `feedback_label_empirical_audit`: hourset の選択は agent 提案の {9,11,15} だけでなく ALL / LONDON / NY / ASIAN を含めて Bonferroni m=375 で公正比較 (post-hoc {9,11,15} pick の罠回避)
- `feedback_success_until_achieved`: 全 cell REJECT で短絡せず、ablation diff まで完走
- `feedback_codex_mock_test_trap`: 単体 mock test だけで PASS にしない、MASSIVE 実 parquet で E2E
- `feedback_codex_stash_leak`: 実装 commit を必ず repo に persist、stash 残置禁止
- `feedback_codex_schema_hallucination`: SQLite 触らない (BT のみ); CSV/JSON 出力

## 1.8 Walk-Forward 3-fold

- データ全期間 (~12.3y) を 3 fold に分割
- 各 fold: 前半 8.2y in-sample で best K/H/hourset を pick, 後半 4.1y OOS で同 cell の PF/EV/Wilson を測定
- Top-1 cell の OOS PF >= 1.0 を 3 fold すべてで通過する必要

# 2. 成果物

```
tools/highvol_continuation_bt.py                    # grid runner
tools/highvol_continuation_ablation.py              # Family A vs v_reversal-flipped B
reports/highvol_continuation_bt/
  ├ summary.md              # 375 cell verdict matrix
  ├ ablation.md             # Family A vs B diff
  ├ spread_sensitivity.md   # spread × cell × broker survival
  ├ per_cell/*.json         # raw stats (375 files)
  ├ wf_3fold/*.json         # walk-forward (top N cells)
  └ null_summary.md         # REJECT cell reasons
strategies/scalp/highvol_continuation_jpy_m5.py     # SHADOW_CANDIDATE 時のみ
tests/test_highvol_continuation.py                  # MASSIVE 実 parquet E2E
```

Result section (queue file 末尾追記):
- 投入 cell 数 / SHADOW_CANDIDATE / NEEDS / REJECT の数
- Top 5 cell の (K, H, hourset, spread, N, WR, Wilson_lo, EV pip, PF, p_BH)
- Family A vs B ablation 主要差分
- Spread breakeven pip ranking
- 次 task 提案 (Phase B: cross-pair OOS / live shadow init)

# 3. 禁止事項

- 本番 OANDA `.env` 触らない
- live SQLite (`data/fx_ai_trader.db`) への shadow 登録は別 task で人手 review 後
- XAU 含めない (feedback_exclude_xau)
- 既存 `v_reversal.py` の編集禁止 (ablation の現行 baseline 不変前提)
- post-hoc に {9,11,15} hourset の verdict だけ pick しない (Bonferroni m=375 で全 hourset 公正比較)
- spread = 0 の数字を SHADOW_CANDIDATE 判定に使わない (現実 broker spread での EV>0 必須)

<!-- highvol_continuation_bt_result -->
## Result: HighVol Continuation BT

Generated: 2026-05-18T10:36:29.788173+00:00
投入 cell 数: 375
SHADOW_CANDIDATE: 0
NEEDS_MORE_EVIDENCE: 0
REJECT: 375

Top 5 cell:
- K=4.5, H=12, hourset=AGENT_9_11_15, spread=0, N=735, WR=0.494, Wilson_lo=0.458, EV=1.09, PF=1.19, p_BH=1.000000
- K=4.5, H=12, hourset=AGENT_9_11_15, spread=0.2, N=735, WR=0.482, Wilson_lo=0.446, EV=0.89, PF=1.16, p_BH=1.000000
- K=4.5, H=12, hourset=LONDON_07_14, spread=0, N=3444, WR=0.502, Wilson_lo=0.485, EV=0.75, PF=1.11, p_BH=1.000000
- K=4.5, H=3, hourset=AGENT_9_11_15, spread=0, N=735, WR=0.497, Wilson_lo=0.461, EV=0.68, PF=1.23, p_BH=1.000000
- K=4, H=12, hourset=LONDON_07_14, spread=0, N=4960, WR=0.495, Wilson_lo=0.481, EV=0.62, PF=1.10, p_BH=1.000000

Family A vs B ablation major diff: Family A uses direct body/SMA20 continuation; Family B reuses current v_reversal trigger and flips its direction, so K is an inert comparison label for B.

Spread breakeven pip ranking:
- K=4.5, H=12, hourset=AGENT_9_11_15: 1.09 pip RT
- K=4.5, H=12, hourset=LONDON_07_14: 0.75 pip RT
- K=4.5, H=3, hourset=AGENT_9_11_15: 0.68 pip RT
- K=4, H=12, hourset=LONDON_07_14: 0.62 pip RT
- K=4, H=3, hourset=AGENT_9_11_15: 0.53 pip RT

Next task: Phase B cross-pair OOS and exact TV 1yr window reconciliation if local May 2026 cache is backfilled.
