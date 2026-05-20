---
id: 20260520-bigbeluga-displacement-delta-bt
title: "[Bigbeluga Displacement + Volume Delta BT] Stage 0 pre-reg grid — H1 chart × M5 intrabar delta, 12.3y USDJPY/GBPJPY primary + 6-pair 1y secondary"
owner: codex
status: queued
priority: P1
created_at: 2026-05-20T12:00:00+0900
roadmap_gate: "TradingView 公開 indicator『Institutional Displacement & Volume Delta [Bigbeluga]』(2026-05-20 司令塔読了) を quant 検証。displacement (volume_spike + body% filter) + intrabar buy/sell delta の組合せが H1 次バー方向と相関するかを pre-reg grid で実測。SNS 由来戦略の前例 EMA10×M15 8-pattern (project_ema10_8pattern_2026_05_05.md) は 12.3y N=45,080 で PF=0.28 REJECT → 同水準の科学的監査を本 indicator にも適用。原典は M1 intrabar だが MASSIVE M1 parquet が 6.5 ヶ月のみのため、設計を A: M5-as-intrabar / H1 chart (12.3y) に変更 (司令塔 2026-05-20 判断)。M5 12.3y available は USD_JPY と GBP_JPY のみ確認済 → primary は 2 pair、secondary は M5 1y available の 6 pair で sanity check。"
rule: pre-reg
related:
  - data/cache/massive/USD_JPY_5m.parquet    # 12.3y primary (lowercase schema)
  - data/cache/massive/GBP_JPY_5m.parquet    # 12.3y primary (lowercase schema)
  - data/cache/massive/EUR_USD_5m.parquet    # 6mo secondary (uppercase schema)
  - data/cache/massive/GBP_USD_5m.parquet    # 6mo secondary
  - data/cache/massive/EUR_JPY_5m.parquet    # 6mo secondary
  - data/cache/massive/EUR_GBP_5m.parquet    # 1.1y secondary
  - data/cache/massive/AUD_CAD_5m.parquet    # 1.1y secondary
  - data/cache/massive/AUD_NZD_5m.parquet    # 1.1y secondary
  - data/cache/massive/NZD_CAD_5m.parquet    # 1.1y secondary
  - tools/price_shock_reversion_bt.py        # grid runner 雛形 (再利用)
  - tools/vol_exhaustion_fade_bt.py          # displacement 系 BT 前例
  - .ai/tasks/done/20260518-1900-highvol-continuation-bt-usdjpy-m5.md  # continuation 方向検証の対比対象
  - project_ema10_8pattern_2026_05_05         # SNS 由来戦略の REJECT 前例
  - feedback_shadow_first_quant_architecture
  - feedback_bt_must_use_massive
  - feedback_partial_quant_trap
  - feedback_label_empirical_audit
  - feedback_codex_mock_test_trap
  - feedback_codex_stash_leak
  - feedback_codex_schema_hallucination
  - feedback_exclude_xau
  - feedback_success_until_achieved
---

# 0. 思想 (Bigbeluga Pine 原典)

## 0.1 indicator ロジック (Pine v6 抽出)

```
volMult     = 2.0  (default, spec で sweep)
volLen      = 20
bodyPct     = 50%  (default, spec で sweep)
ltf         = "1"  (M1, 本 BT では M5 代用)

avgVol         = SMA(volume, 20)
highVol        = volume > avgVol * volMult
bodyRatio      = |close - open| / (high - low)
isDisplacement = bodyRatio >= bodyPct/100

bullShift = (close > open) AND highVol AND isDisplacement
bearShift = (close < open) AND highVol AND isDisplacement

# intrabar volume (M5 代用)
up_vol_per_intra   = volume_M5 if close_M5 > open_M5 else 0
down_vol_per_intra = volume_M5 if close_M5 < open_M5 else 0
buyVol             = Σ up_vol_per_intra within H1 bar
sellVol            = Σ down_vol_per_intra within H1 bar
deltaVol           = buyVol - sellVol
deltaRatio         = deltaVol / (buyVol + sellVol)   # [-1, +1]
```

## 0.2 BT で検証する仮説 (3 系統)

| 系統 | エントリー条件 | 思想 |
|---|---|---|
| **H-A** Continuation | shift bar 確定後 next H1 open で **shift 方向に** entry | 大口の方向押し圧、追随で取る |
| **H-B** Reversion | shift bar 確定後 next H1 open で **shift 逆方向に** entry | 大口イベント後の平均回帰、絶頂で売り底で買う |
| **H-C** Delta-Confirmed | bullShift AND deltaRatio > +0.3 (LONG) / bearShift AND deltaRatio < -0.3 (SHORT) を **H-A 方向で** entry | Bigbeluga 原典の "institutional alignment" 解釈、shift と intrabar delta が同方向のときのみ trade |
| **H-D** Delta-Absorption | bullShift AND deltaRatio < -0.3 (= 売り吸収後の上抜け = 強い) / bearShift AND deltaRatio > +0.3 を **H-A 方向で** entry | order flow 解釈、shift 表面方向に対して delta が逆 = 吸収後の真ブレイク |

H-A, H-B は **delta 情報なし版** (negative control)、H-C/H-D が **delta の incremental edge** を測る本命系統。

## 0.3 前例との関係

- **highvol-continuation-bt-usdjpy-m5** (2026-05-18 ACCEPT-then-REJECT): K_mult sweep monotonic で PF 1.234 → 12.3y で大量集計時に regime fluke 確定。**H-A は同戦略の H1 版** であり、それが REJECT 既知なので **H-A 単独で PASS する見込みは低い**。本タスクの真の価値は **H-C/H-D で delta による discrimination が edge を生むか**。
- **EMA10×M15 8-pattern** (2026-05-05 REJECT): SNS 由来単純戦略の Stage 0 REJECT 前例。同じ枠組みで Bigbeluga も検証。

# 1. 設計

## 1.1 Grid 定義 (pre-reg literal)

### Primary (12.3y, USD_JPY + GBP_JPY)

| 軸 | 値 | 数 |
|---|---|---|
| pair | USD_JPY, GBP_JPY | 2 |
| chart TF | H1 | 1 |
| intrabar TF | M5 (12 bar / H1) | 1 |
| volMult | 1.5, 2.0, 2.5, 3.0 | 4 |
| bodyPct | 0.40, 0.50, 0.60 | 3 |
| hypothesis | H-A, H-B, H-C, H-D | 4 |
| horizon (H1 bars) | 1, 3, 6, 12 | 4 |

**Primary total**: 2 × 4 × 3 × 4 × 4 = **384 cells**

### Secondary (1.1y - 6mo, 6 pair)

USD_JPY/GBP_JPY を除く M5 available の 6 pair = EUR_USD, GBP_USD, EUR_JPY, EUR_GBP, AUD_CAD, AUD_NZD, NZD_CAD (7 pair)。各 pair で **primary grid を縮小** (volMult=2.0 固定, bodyPct=0.50 固定) で実行:

**Secondary total**: 7 × 1 × 1 × 4 × 4 = **112 cells** (sanity 用、Bonferroni には含めない)

### 多重検定補正

- **Primary 384 cells** に対し **BH-FDR (m=384, q=0.10)** → survivor 判定
- 厳格版併報: **Bonferroni α = 0.05/384 = 1.30e-4**
- **Secondary 112 cells** は **out-of-distribution sanity** として、primary survivor の H-C/H-D cell が secondary pair でも有意 trend を示すか確認 (formal verdict には含めない)

## 1.2 シグナル定義 (リーケージ排除)

```python
# H1 bar t の確定後、H1 bar t+1 の open で entry (next-bar-open)
# intrabar M5 12 本は H1 bar t 内側を集計 (look-ahead なし、t 確定時点で全 M5 確定済)

# H1 構築 (M5 から resample)
h1_open  = M5[t_start].open
h1_high  = M5[t_start:t_end].high.max()
h1_low   = M5[t_start:t_end].low.min()
h1_close = M5[t_end-1].close
h1_volume = M5[t_start:t_end].volume.sum()

# displacement filter
avgVol = SMA(h1_volume, 20)            # rolling, t 含めず t-20..t-1 で計算
highVol = h1_volume[t] > avgVol[t] * volMult
bodyRatio = abs(h1_close - h1_open) / (h1_high - h1_low)
isDisplacement = bodyRatio >= bodyPct

# intrabar delta (M5 集計)
m5_in_h1 = M5[t_start:t_end]
buyVol = m5_in_h1[m5_in_h1.close > m5_in_h1.open].volume.sum()
sellVol = m5_in_h1[m5_in_h1.close < m5_in_h1.open].volume.sum()
deltaRatio = (buyVol - sellVol) / (buyVol + sellVol) if (buyVol+sellVol) > 0 else 0

# signal
bullShift = (h1_close > h1_open) and highVol and isDisplacement
bearShift = (h1_close < h1_open) and highVol and isDisplacement

# hypothesis 別 entry
if hypothesis == "H-A":  # continuation
    if bullShift: entry_side = "LONG"
    elif bearShift: entry_side = "SHORT"
elif hypothesis == "H-B":  # reversion
    if bullShift: entry_side = "SHORT"
    elif bearShift: entry_side = "LONG"
elif hypothesis == "H-C":  # delta-confirmed continuation
    if bullShift and deltaRatio > +0.3: entry_side = "LONG"
    elif bearShift and deltaRatio < -0.3: entry_side = "SHORT"
elif hypothesis == "H-D":  # delta-absorption continuation
    if bullShift and deltaRatio < -0.3: entry_side = "LONG"
    elif bearShift and deltaRatio > +0.3: entry_side = "SHORT"

# Entry: H1 bar t+1 open
# Exit: H1 bar t+1+horizon close (固定保有、SL/TP なし — 純粋エッジ測定)
```

## 1.3 BT 出力 (cell 単位)

| カラム | 説明 |
|---|---|
| N | trades 数 |
| WR | 勝率 |
| EV_pip, EV_pct | 平均リターン (pip / %) |
| PF | profit factor |
| Wilson_lower_95 | WR Wilson 下限 |
| Sharpe_annual | √(252×24) 補正 |
| Kelly_fraction | f* = WR - (1-WR)/RR |
| max_dd_pct | 最大 DD |
| MAE_mean_pct, MAE_p5_pct | 最大逆行幅 |
| MFE_mean_pct | 最大順行幅 |
| year_sign_flip_count | 年別 EV 符号が aggregate と異なる年数 |
| p_value | 二項検定 (両側) |
| bonferroni_pass | p < 1.30e-4 |
| bh_fdr_pass | BH q=0.10 |
| verdict | SHADOW_CANDIDATE / CONDITIONAL / REJECT |

## 1.4 サニティゲート (pre-reg)

| ゲート | 条件 | 根拠 |
|---|---|---|
| G1 N | N >= 30 (primary は >= 100 推奨) | 統計的最小 |
| G2 Wilson | Wilson_lower_95(WR) >= 0.50 | partial_quant_trap |
| G3 PF | PF >= 1.20 | shadow-first sanity |
| G4 BH-FDR | bh_fdr_pass = True | 多重検定 |
| G5 year stability | year_sign_flip_count <= 1 (12.3y で) | post-hoc selection 罠 |
| G6 cost-aware | EV_pip >= 1.5 × typical_spread_pip(pair) | コスト |
| **G7 delta incremental** | H-C or H-D の cell が PASS する場合、**同 (pair, volMult, bodyPct, horizon)** で H-A が REJECT であること | delta による真の discrimination 証明 (delta 抜き版で同等以上に勝つなら delta は意味なし) |

**G1-G6 すべて pass** + **(hypothesis ∈ {H-A, H-B} OR G7 pass)** → `SHADOW_CANDIDATE`
**G1-G4 pass, G5/G6/G7 fail** → `CONDITIONAL`
**G1-G4 のいずれか fail** → `REJECT`

## 1.5 DDL (Codex schema hallucination 防止のため literal 適用)

```sql
CREATE TABLE IF NOT EXISTS bigbeluga_disp_delta_cells (
    cell_id          TEXT PRIMARY KEY,         -- "{pair}_{hypothesis}_{volMult}_{bodyPct}_{horizon}"
    pair             TEXT NOT NULL,
    tf               TEXT NOT NULL,            -- "H1"
    intrabar_tf      TEXT NOT NULL,            -- "M5"
    hypothesis       TEXT NOT NULL,            -- "H-A" / "H-B" / "H-C" / "H-D"
    vol_mult         REAL NOT NULL,
    body_pct         REAL NOT NULL,
    horizon_bars     INTEGER NOT NULL,
    cohort           TEXT NOT NULL,            -- "primary_12y" or "secondary_1y"
    n_trades         INTEGER NOT NULL,
    win_rate         REAL,
    ev_pip           REAL,
    ev_pct           REAL,
    profit_factor    REAL,
    wilson_lower_95  REAL,
    sharpe_annual    REAL,
    kelly_fraction   REAL,
    max_dd_pct       REAL,
    mae_mean_pct     REAL,
    mae_p5_pct       REAL,
    mfe_mean_pct     REAL,
    year_flip_count  INTEGER,
    p_value          REAL,
    bonferroni_pass  INTEGER,                  -- 0/1
    bh_fdr_pass      INTEGER,                  -- 0/1
    g7_delta_incremental INTEGER,              -- 0/1, H-A/H-B では NULL
    verdict          TEXT NOT NULL,            -- "SHADOW_CANDIDATE"/"CONDITIONAL"/"REJECT"
    period_start     TEXT NOT NULL,
    period_end       TEXT NOT NULL,
    bt_data_source   TEXT NOT NULL DEFAULT 'MASSIVE_parquet',
    generated_at     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_bbdd_verdict ON bigbeluga_disp_delta_cells(verdict);
CREATE INDEX IF NOT EXISTS idx_bbdd_pair_hyp ON bigbeluga_disp_delta_cells(pair, hypothesis);
CREATE INDEX IF NOT EXISTS idx_bbdd_cohort ON bigbeluga_disp_delta_cells(cohort);
```

## 1.6 報告物

`reports/bigbeluga_displacement_delta/` 配下:
1. `grid_full.csv` — primary 384 + secondary 112 = 496 cell raw stats
2. `survivors.md` — `SHADOW_CANDIDATE` cell list (W4-EDA フォーマット: Verdict / Rec / 思想 / 設計欠陥 / 再設計案、🔴🟠 emoji)
3. `conditional.md` — `CONDITIONAL` cell + G5/G6/G7 fail 詳細
4. `null_summary.md` — REJECT 統計、失敗パターン分類 (G1 N不足 / G2 Wilson / G3 PF / G4 BH / G5 year / G6 cost / G7 delta)
5. `hypothesis_comparison.md` — H-A vs H-B vs H-C vs H-D の 4 系統比較サマリ (delta の incremental edge を quantify)
6. `secondary_sanity.md` — secondary 6+1 pair で primary survivor の方向が再現するか
7. `SUMMARY.md` — 司令塔判定用ダイジェスト
8. `verdict.md` — 全体 GO/NO-GO + shadow promote 推奨 cell

## 1.7 schema 不整合の取り扱い (重要)

MASSIVE M5 parquet は 2 系統:
- **lowercase** (`open/high/low/close/volume`): USD_JPY, GBP_JPY (12.3y 系)
- **uppercase** (`Open/High/Low/Close/Volume`): EUR_USD, GBP_USD, EUR_JPY, EUR_GBP, AUD_CAD, AUD_NZD, NZD_CAD (短期系)

loader は `pair_schema_map = {"USD_JPY": "lower", "GBP_JPY": "lower", ...}` で明示分岐すること。自動検出ではなく明示。**timestamp_utc column** (lowercase) vs **DatetimeIndex** (uppercase) も pair で差異あり、loader で正規化する。

# 2. 完了条件

1. `tools/bigbeluga_displacement_delta_bt.py` 新規作成 (grid runner、price_shock_reversion_bt.py 骨格再利用可)
2. `modules/bigbeluga_grid_db.py` DDL §1.5 literal 適用 + insert helpers
3. `tests/test_bigbeluga_displacement_delta_bt.py` (unit + **integration with real MASSIVE parquet**、mock-only 禁止)
4. 2 pair primary + 7 pair secondary 全実行、`reports/bigbeluga_displacement_delta/` 8 ファイル出力
5. DB persist (既存 fx_ai_trader.db に table 追加 or 新規 `data/bigbeluga_grid_cells.db`)
6. 生成物即 commit (--no-verify 可、ただし `.git/index.lock` blocked なら final.md 明記)
7. `final.md` には: 投入 cell 数 (primary/secondary 別)、SHADOW_CANDIDATE 数、CONDITIONAL 数、REJECT 数、top 5 H-C/H-D survivors の 1 行 evidence、G7 (delta incremental) PASS 数

# 3. 司令塔ガード (pre-flight checklist)

## 3.1 必須遵守 (違反 = ROLLBACK)

- [ ] **MASSIVE parquet 必須**: Yahoo 禁止 (feedback_bt_must_use_massive)
- [ ] **XAU 除外** (feedback_exclude_xau) ※本タスクは XAU 元から含まず
- [ ] **next-bar-open エントリー** (look-ahead リーケージ排除)
- [ ] **rolling SMA(volume, 20)** で当該 bar を含めず計算
- [ ] **mock-only テスト禁止**: integration test は実 parquet (feedback_codex_mock_test_trap)
- [ ] **stash 漏れ禁止**: 全変更を main branch に commit、`git status` clean (feedback_codex_stash_leak)
- [ ] **DDL は §1.5 literal 適用** (feedback_codex_schema_hallucination)
- [ ] **schema 分岐は §1.7 literal** (lower/upper case schema map で明示)
- [ ] **is_shadow 混入なし**: 純粋 BT、Live は別 (feedback_live_shadow_separation)
- [ ] **既存 task と並走可** (P0 fix-pyr-strategy-attribution と無干渉、別 DB table)

## 3.2 思想ガード (post-hoc tune 禁止)

- [ ] Grid は §1.1 literal、Codex で「N 不足だから q=0.20」等の post-hoc 改訂は **司令塔 review 必須**
- [ ] G7 (delta incremental) literal、cell-by-cell 例外不可
- [ ] survivor cell は **shadow promote 候補**であり、本 task で Live promote は禁止
- [ ] H-A 単独 survivor は前例 (highvol-continuation regime fluke) を鑑み **要警戒** flag を survivor.md に付ける

## 3.3 失敗時の挙動

- 全 cell NULL → **正しい結果**として `null_summary.md` で失敗パターン分類報告 (feedback_success_until_achieved: pre-reg NULL は科学的成果、closure 短絡禁止)
- H-A/H-B のみ survivor で H-C/H-D 全 NULL → **delta 情報は edge を生まない** と結論、Bigbeluga indicator の "institutional alignment" 解釈は否定される
- H-C/H-D survivor 多数 + G7 PASS → **真の delta edge 候補**、次フェーズで Wave 1 shadow promotion へ
- pre-commit hook で blocked → `--no-verify` で commit、final.md に hook log 添付

# 4. 次フェーズ (本 task 完了後の司令塔判断材料)

- **G7 PASS H-C/H-D survivor >= 3 cell** → Wave 1 で shadow promotion + 6 ヶ月 OOS 観測、本 indicator は **edge 候補確定**
- **H-A/H-B only survivor (G7 N/A)** → delta 情報なし版で勝てるなら Bigbeluga 本体ではなく displacement filter 単体が edge 源、別戦略として再構築検討
- **全 NULL** → **Hypothesis kill**、Bigbeluga indicator は EMA10×M15 と同枠 (SNS 由来の visual fluke)、次系統 (CAD-1 / SR Phase 2.5 / fx-nexus OOS) に集中

## 5. 想定実行時間

- BT runner 実装: 2-3 時間 (price_shock_reversion_bt.py 骨格再利用)
- 2 pair × 384 cell primary + 7 pair × 112 secondary 実行: 1-2 時間 (vectorized numpy + parquet read cache)
- 報告物生成 (8 ファイル): 30 分
- **総計**: 4-6 時間 (1 セッション完結目標)
