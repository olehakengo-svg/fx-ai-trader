---
id: 20260515-2235-vol-exhaustion-fade-bt-usdjpy-m5
title: "[Vol Exhaustion Fade USDJPY M5] |body|≥K×SMA20(|body|) → 同方向 fade BT + 既存 v_reversal ablation"
owner: codex
status: queued
priority: P0
created_at: 2026-05-15T22:35:00+0900
roadmap_gate: "TV MCP で 500本 M5 USDJPY (~41h) を計測した結果、|body|/SMA20(|body|) ≥ 4× の extreme bin (N=17) が next-3-bar 同方向 P/L = -4.16 pip と robust に mean-revert。kurtosis tail の exhaustion 既知 (Cont 2001 / Jegadeesh & Titman 1993)。既存 strategies/scalp/v_reversal.py が直接の対応ファミリーだが W4-EDA 76 戦略監査範囲 — 本 task は (a) 既存 v_reversal の現行設計を抽出 (b) cutoff K と time-stop の 2D grid で MASSIVE 12.3y BT (c) 既存実装との ablation で「設計差分」を特定。観察 41h は statistical claim 不可、本 task で初の長期検証。"
rule: pre-reg
related:
  - strategies/scalp/v_reversal.py
  - strategies/scalp/vol_surge.py
  - strategies/scalp/vol_momentum.py
  - strategies/scalp/three_bar_reversal.py
  - tools/fetch_massive_data.py
  - modules/data.py
  - data/cache/massive/USD_JPY_M5.parquet
  - project_w4_eda_complete_2026_05_05
  - feedback_shadow_first_quant_architecture
  - feedback_bt_must_use_massive
  - feedback_partial_quant_trap
  - feedback_label_empirical_audit
  - feedback_success_until_achieved
  - feedback_ma_filter_breaks_mr
  - feedback_codex_mock_test_trap
  - feedback_codex_stash_leak
  - feedback_exclude_xau
---

# 0. 思想と背景

## 0.1 観察 (TV MCP 41h スナップショット 2026-05-15)

USDJPY M5、500本 (~41h) で |body|/SMA20(|body|) の 5-bin 集計:

| Regime | N | mean \|next3\| pip | mean same-dir P/L pip |
|---|---|---|---|
| low (<0.5×) | 168 | 4.47 | +0.12 |
| mid-lo (0.5-1.0×) | 129 | 5.15 | +0.11 |
| mid-hi (1.0-2.0×) | 121 | 4.33 | -0.08 |
| high (2.0-4.0×) | 42 | 6.34 | **+1.03 (cont)** |
| **extreme (≥4.0×)** | **17** | 10.47 | **-4.16 (revert)** |

**Cutoff 3-4× で continuation→reversal が反転** = Cont (2001) Empirical properties of asset returns: stylized facts と整合。
N=17 では pre-reg 不可、本 task が長期検証の初手。

## 0.2 既存戦略との関係

- `strategies/scalp/v_reversal.py` ("V-Reversal — 急落/急騰後の反転検出 Cont 2001, J&T 1993") が直接ファミリー
- W4-EDA (`project_w4_eda_complete_2026_05_05`) で 76 戦略監査済、v_reversal の verdict 抽出が前提作業

## 0.3 本 task の本質

「思想は正、設計が誤」91% 罠 (`project_w4_eda_complete_2026_05_05`) を避けるため、純粋仮説の BT と既存実装 ablation を **同 grid で** 並走。設計差分を埋めれば SHADOW 候補。

# 1. 設計

## 1.1 データ

- pair: **USD_JPY のみ** (本 task)、cross-pair OOS は Phase B で別 task
- TF: **M5**
- ソース: **MASSIVE Market Data API**, `data/cache/massive/USD_JPY_M5.parquet`
- 期間: 利用可能最古〜2026-05-14 (目安 12.3y)
- spread: 1.3 pip 固定 (entry/exit 両側に乗せ)
- XAU 含めない (feedback_exclude_xau)

不在/欠損時は `tools/fetch_massive_data.py` で backfill。`--allow-h4-from-h1` 等の partial 代替は使わない。

## 1.2 Hypothesis (純粋仮説 = Family A)

**Family A: Pure Vol Exhaustion Fade**

bar t で:

```
body_t   = |close_t - open_t|
sma20_t  = mean(body_{t-20..t-1})         # 20本 prior SMA, t は含まない
extreme  = body_t >= K * sma20_t
dir_t    = sign(close_t - open_t)
```

`extreme` 確定 → bar 終値で **反対方向** に entry。
- entry: bar t close
- TP: entry ± 1.0 * ATR14_t (long なら -dir に取る = fade)
- SL: entry ∓ 1.5 * ATR14_t
- Time stop: H bar 後に成行
- pyramiding: なし、cooldown 3bar (同 bar 連続 extreme でも 1 トレード)

## 1.3 Cell Grid

```
K        ∈ {3.0, 3.5, 4.0, 4.5}        # 4
H_bar    ∈ {3, 6, 12}                  # 3
session  ∈ {ALL, ASIAN_15-22_UTC, LONDON_07-14_UTC, NY_12-20_UTC}  # 4
```

合計 **4 × 3 × 4 = 48 cell**

Bonferroni: α = 0.05 / 48 = **0.00104**

## 1.4 Family B: 既存 v_reversal ablation

同 48 cell を `strategies/scalp/v_reversal.py` の現行ロジックでも実行。
Codex は v_reversal の `signal()` を読み、cell 適用方法を実装。差分項目を抽出:
- entry trigger (n-bar rule vs body-σ rule)
- direction (反転 vs continuation)
- exit (TP/SL/time)
- filter (MA/RSI/regime)

Family A vs B を per-cell で並走、`reports/vol_exhaustion_fade_bt/ablation.md` に diff 表。

## 1.5 Verdict Gate

各 cell ごとに:

| Gate | 条件 |
|---|---|
| G1 N | N ≥ 30 |
| G2 Wilson | Wilson_lower(WR, N) ≥ 0.50 |
| G3 EV | EV (pip / trade, after spread) > 0 |
| G4 Bonf | BH-FDR adjusted p < 0.00104 (m=48) |
| G5 PF | PF ≥ 1.20 |
| G6 Kelly | Kelly fraction ≥ 0.05 |
| G7 WF | 3-fold Walk-Forward 全 fold で EV>0 |

判定:
- **SHADOW_CANDIDATE**: G1-G7 全通過 → `strategies/scalp/vol_exhaustion_fade.py` 新規実装 + shadow 登録
- **NEEDS_MORE_EVIDENCE**: G1-G3 通過, G4-G7 のいずれか fail → 再 grid 案を report
- **REJECT**: G1 or G2 or G3 fail → null verdict, ablation 報告のみ

## 1.6 Anti-罠 チェック

- `feedback_ma_filter_breaks_mr`: MA trend filter を **足さない**
- `feedback_partial_quant_trap`: N/WR/EV だけで止めず PF/Wilson/Bonf/WF/Kelly まで報告
- `feedback_success_until_achieved`: Null/REJECT で短絡せず、ablation diff まで完走
- `feedback_codex_mock_test_trap`: 単体 mock test だけで PASS にしない、MASSIVE 実 parquet で E2E
- `feedback_codex_stash_leak`: 実装 commit を必ず repo に persist、stash 残置禁止
- `feedback_codex_schema_hallucination`: SQLite schema 参照箇所は `CREATE TABLE` を spec に貼り直す or 既存 DDL 読み込み

# 2. 成果物

```
tools/vol_exhaustion_fade_bt.py                     # grid runner
tools/vol_exhaustion_fade_ablation.py               # Family A vs v_reversal B
reports/vol_exhaustion_fade_bt/
  ├ summary.md              # cell 表 + verdict matrix
  ├ ablation.md             # Family A vs B diff
  ├ per_cell/*.json         # raw stats
  ├ wf_3fold/*.json         # walk-forward
  └ null_summary.md         # data 不在 / N不足 cell list
strategies/scalp/vol_exhaustion_fade.py             # SHADOW_CANDIDATE 時のみ
tests/test_vol_exhaustion_fade.py                   # MASSIVE 実 parquet E2E
```

verdict は queue file 末尾の Result section に追記:
- 投入 cell 数 / SHADOW_CANDIDATE / NEEDS / REJECT の数
- Top 3 cell の (K, H, session, N, WR, Wilson_lo, EV, PF, p_BH)
- ablation の主要差分
- 次 task 提案 (Phase B cross-pair OOS / cooldown sweep 等)

# 3. 禁止事項

- 本番 OANDA `.env` 触らない
- live SQLite (`data/fx_ai_trader.db`) への shadow 登録は別 task で人手 review 後
- XAU 含めない (feedback_exclude_xau)
- 既存 `v_reversal.py` の編集禁止 (ablation 比較のため現行版を不変前提)


## Error (2026-05-18T04:25:36Z)

```
orphaned: container restarted while task was running
```
