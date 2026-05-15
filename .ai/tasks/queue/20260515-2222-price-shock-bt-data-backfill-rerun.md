---
id: 20260515-2222-price-shock-bt-data-backfill-rerun
title: "[Price-Shock BT 完全再現] MASSIVE H4/H1 backfill + Qiita 期間で再 run — 前回 21% coverage / 全 864 reject は data 不在起因"
owner: codex
status: queued
priority: P1
created_at: 2026-05-15T22:22:00+0900
roadmap_gate: "前 task 20260515-1702-price-shock-reversion-grid-bt (commit 63c7cf18) は MASSIVE H4 parquet が 0/14 pair、H1 が 6/14 pair しか存在せず、4032 期待中 864 cell (21%) しか生成できなかった。Qiita 原典 (tikeda123/items/f3bead031159ee8ca1bf) の AUDJPY H4 下位5% 急落後 48H ロング WR=60.06% N=1,369 を含む 3 pair (USDJPY/EURUSD/AUDJPY) × H4 が完全未検証。これは hypothesis kill ではなく data 不在による partial test。完全再現には MASSIVE API から 14 pair × H4/H1 を Qiita 期間 (2022-01-02〜2026-04-02, ~1600 日) で取得し、同一 pre-reg grid を再走する必要がある。"
rule: pre-reg
related:
  - tools/price_shock_reversion_bt.py                     # 既存 grid runner、--allow-h4-from-h1 フラグ持ち
  - tools/fetch_massive_data.py                           # 既存 fetcher、現状 --tf choices は ["5m", "1h"] のみ → "4h" 追加必要
  - modules/data.py:fetch_ohlcv_massive                   # 既に 4h interval サポート (docstring に明記)
  - modules/price_shock_grid_db.py                        # DDL は前 task で作成済
  - reports/price_shock_reversion_grid/                   # 前回出力 (864 cell, 全 REJECT)
  - data/cache/massive/                                   # parquet 出力先
  - .ai/tasks/done/20260515-1702-price-shock-reversion-grid-bt.md  # 前 task 完了報告
  - feedback_shadow_first_quant_architecture
  - feedback_bt_must_use_massive
  - feedback_partial_quant_trap
  - feedback_label_empirical_audit
  - feedback_success_until_achieved                       # 「Null/Scenario A で closure 短絡禁止」
  - feedback_codex_mock_test_trap
  - feedback_codex_stash_leak
  - feedback_exclude_xau
  - project_phase2a_oanda_contrarian_v2_2026_05_13
  - project_price_shock_reversion_queued_2026_05_15
---

# 0. 思想と現状

## 0.1 前 task の真の結果

- 投入 cell: 864 (期待 4,032 の 21%)
- SHADOW_CANDIDATE: 0
- REJECT: 864 (BH_FDR_fail 100%, Wilson_lt_0.50 92%, N_lt_30 41%)
- **重要**: `null_summary.md` の skip list で 21 pair/TF が parquet 不在で skip
  - H4: **0/14 pair 存在** (USD_JPY/EUR_USD/GBP_USD/AUD_USD/NZD_USD/USD_CAD/USD_CHF/EUR_JPY/GBP_JPY/AUD_JPY/NZD_JPY/EUR_GBP/EUR_AUD 全 H4 missing)
  - H1: 7 pair missing (AUD_USD, NZD_USD, USD_CAD, USD_CHF, AUD_JPY, NZD_JPY, EUR_AUD)
  - GBP_JPY は spec の重複 entry で dedupe (本 task で確定 1 個に修正済 spec)

## 0.2 Qiita 原典 (再現対象)

URL: https://qiita.com/tikeda123/items/f3bead031159ee8ca1bf

| 項目 | 値 |
|---|---|
| 通貨ペア | USDJPY, EURUSD, **AUDJPY** |
| 足種 | **240 分足 (H4)** |
| 期間 | **2022-01-02 〜 2026-04-02** (~1,580 日) |
| 最有望 cell | AUDJPY H4 下位 5% 急落後 48H ロング: WR=**60.06%**, N=**1,369**, EV=+0.2024% |

**Wilson lower 試算** (Qiita stat → 我々の gate 通過判定):
- WR=0.6006, N=1369 → Wilson_lower ≈ 0.574 → **G2 (>=0.50) 通過**
- BH-FDR: p ≈ 1e-13 (z=7.44 vs null=0.5) → **G4 通過**
- 故に**完全再現できれば AUD_JPY cell は SHADOW_CANDIDATE 候補**

## 0.3 本 task の本質

「parquet 不在による partial test の closure 短絡」回避 (feedback_success_until_achieved)。
data 補完 → 完全 grid 再走 → 真の verdict 確定。

# 1. 設計

## 1.1 Backfill 仕様 (Step 1)

### 1.1.1 fetcher の H4 サポート追加 (1 行修正)

`tools/fetch_massive_data.py` の argparse `--tf` choices を `["5m", "1h"]` → `["5m", "1h", "4h"]` に拡張。
`audit_frame` の `minutes` dict も `"4h": 240` を追加。
`fetch_ohlcv_massive` 自体は既に 4h サポート済 (modules/data.py docstring 明記)。

### 1.1.2 取得対象 (14 pair × 2 TF = 28 ファイル)

```
pairs = ["USD_JPY", "EUR_USD", "GBP_USD", "AUD_USD", "NZD_USD", "USD_CAD", "USD_CHF",
         "EUR_JPY", "GBP_JPY", "AUD_JPY", "NZD_JPY", "EUR_GBP", "EUR_AUD"]
# 13 pairs (前 spec の GBP_JPY 重複は本 task で 1 個に確定)
# XAU 除外 (feedback_exclude_xau)
```

**取得期間**: `--days 1600` (Qiita 期間 ~1,580 日をカバー、安全マージン込み)

**ファイル命名**:
- `data/cache/massive/{PAIR}_4h.parquet` (新規作成)
- `data/cache/massive/{PAIR}_1h.parquet` (既存ある場合は上書き、無い場合は新規)

**既存 H1 parquet の扱い**: USD_JPY/EUR_USD などは 526 日しか持っていない。1600 日で **強制上書き** (BT が期間統一されるため)。

### 1.1.3 fetch スクリプト (新規 or 既存 wrapper)

```python
# tools/price_shock_backfill_data.py (新規) または bash ループ
for pair in pairs:
    for tf in ["4h", "1h"]:
        out = f"data/cache/massive/{pair}_{tf.replace('h','h')}.parquet"
        # tf="4h" → "_4h.parquet", tf="1h" → "_1h.parquet"
        subprocess.run([
            ".venv/bin/python", "tools/fetch_massive_data.py",
            "--pair", pair, "--tf", tf,
            "--days", "1600", "--out", out
        ])
```

**MASSIVE_API_KEY**: 環境変数。Render worker 側で既に設定済の前提 (前 task で `Yahoo fallback は使っていません。MASSIVE parquet のみです。` と報告された = MASSIVE 接続成功実績あり)。

### 1.1.4 取得後の audit

各 parquet について `*.audit.json` (既存 fetcher が自動生成):
- rows >= ~9,000 (H4 で 1600 日 = ~2,300 / H1 で 1600 日 = ~9,600)
- completeness_pct >= 95% (weekend gap 補正後)
- start <= 2022-01-02、end >= 2026-04-02 (Qiita 期間カバー)

**Audit fail → final.md に明記、当該 pair/TF は skip でなく fail 扱い (司令塔判断必要)**。

## 1.2 BT 再 run 仕様 (Step 2)

```bash
.venv/bin/python tools/price_shock_reversion_bt.py \
    --cache-dir data/cache/massive \
    --out-dir reports/price_shock_reversion_grid \
    --db data/price_shock_grid_cells.db \
    --allow-h4-from-h1
```

**注**: `--allow-h4-from-h1` は H4 parquet 不在時の fallback として残すが、本 task では H4 を直接 fetch するので fallback 発動しないはず。
**注**: 既存 DB (`price_shock_grid_cells.db`) は前 task の 864 行を保持。本 task の run は `replace_cells` で全置換 (前回データを上書き)。

### 1.2.1 期待値

- 投入 cell: **4,032** (13 pair × 2 TF × 6 percentile × 4 horizon × 6 vol_q = 3,744 ... ちょっと違う、計算: 13 × 2 × 3 × 2 × 4 × 6 = 3,744。spec の 4032 は GBP_JPY 重複ありの 14 pair で 14×2×3×2×4×6=4032)
- 実際の grid サイズ: 13 pair × 2 TF × 6 percentile × 4 horizon × 6 vol_q = **3,744 cell**
- BH-FDR 補正: m=3744, q=0.10
- Bonferroni: α/m = 1.335e-5

**Pre-reg gate (前 task spec §1.4 から literal 継承)**:
- G1 N >= 30
- G2 Wilson_lower_95(WR) >= 0.50
- G3 PF >= 1.20
- G4 BH-FDR pass (q=0.10, m=3744)
- G5 year_sign_flip_count <= 1
- G6 EV_pip >= 1.5 × typical_spread_pip(pair)

### 1.2.2 司令塔向け追加報告

`reports/price_shock_reversion_grid/SUMMARY.md` の Evidence セクションに、Qiita 該当 cell を **明示的に列挙**:

```markdown
## Qiita Reproduction Verification
| Cell | Spec | Qiita Reported | Our BT | Match? |
|---|---|---|---|---|
| AUD_JPY_H4_LONG_SHOCK_5_12_ALL | 下位5% 48H | WR=60.06% N=1369 EV=+0.2024% | <our N/WR/EV> | <pass/fail> |
| AUD_JPY_H4_LONG_SHOCK_1_12_ALL | 下位1% 48H | WR=62.32% N=69 EV=+0.3856% | <our N/WR/EV> | <pass/fail> |
| USD_JPY_H4_*  | 同 horizon | (Qiita: 反発弱い) | <our> | - |
| EUR_USD_H4_*  | 同 horizon | (Qiita: 値幅小) | <our> | - |
```

(Qiita 記事では Q5 高ボラの cell も列挙されているが、horizon=24H/48H で WR 高い旨。明確な N/WR が記載されている cell のみ表に。)

## 1.3 完了条件

1. `tools/fetch_massive_data.py` の `--tf` choices と `audit_frame` の `minutes` dict に "4h" 追加
2. 14 pair × {H4, H1} = 28 parquet が `data/cache/massive/` に存在 (1600 日)
3. 各 parquet の audit.json で `start <= 2022-01-04` (UTC、Qiita 2022-01-02 + 2日 buffer)
4. `tools/price_shock_reversion_bt.py` を `--allow-h4-from-h1` 付きで実行
5. `reports/price_shock_reversion_grid/SUMMARY.md` 更新:
   - Qiita Reproduction Verification table (上記 §1.2.2)
   - Verdict (SHADOW_CANDIDATE 数で GO/CONDITIONAL/NO-GO)
6. `data/price_shock_grid_cells.db` 全置換 (3,744 行を期待)
7. `final.md` に: 投入 cell 数 / SHADOW_CANDIDATE 数 / AUDJPY H4 5% 48H の実測 WR/N/EV
8. 生成物即 commit (--no-verify 可、blocked なら final.md 明記)

# 2. 司令塔ガード

## 2.1 必須遵守

- [ ] **MASSIVE API のみ**: Yahoo fallback 禁止 (feedback_bt_must_use_massive)
- [ ] **XAU 除外** (feedback_exclude_xau)
- [ ] **pair list は §1.1.2 literal 13 pair**: 前 spec の GBP_JPY 重複は本 task で 1 個に確定 ← post-hoc 改訂は司令塔 review 必須
- [ ] **--days 1600 を literal**: post-hoc で期間短縮/延長は禁止 (Qiita 完全再現を最優先)
- [ ] **next-bar-open + rolling percentile**: 既存 BT tool の look-ahead 回避設計は変更しない
- [ ] **stash 漏れ禁止** (feedback_codex_stash_leak): 全変更を main に commit、`git status` clean で終了
- [ ] **mock-only 禁止** (feedback_codex_mock_test_trap): integration test は既存 `test_price_shock_reversion_bt.py` を再走、新規データに対し PASS 必須

## 2.2 失敗時挙動

- MASSIVE API 503/rate limit → リトライ 3 回まで、それでも全 fail なら部分結果で final.md 報告、司令塔判断
- 一部 pair の Qiita 期間 (2022-01-02) より historical data が無い → audit.json の `start` で明示、final.md に「earliest_start=YYYY-MM-DD」記載 (Qiita 完全再現でなく partial reproduction であることを明示)
- `replace_cells` でテーブル整合性エラー → DDL を見直すのではなく **DB 削除 → 新規作成 → INSERT** で対処

## 2.3 SHADOW_CANDIDATE 0 だった場合の判定 (前 task と区別)

前 task NULL は data 不在起因 → 本 task NULL は **真の hypothesis kill 候補**。
ただし以下も report 必須:
- AUDJPY H4 5% 48H の実測 (Qiita との **数値比較**): WR/N/EV/Wilson_lower
- もし Qiita stat (WR=60.06%, N=1369) と我々の実測が大きく乖離 → methodology 差 (rolling vs fixed percentile, look-ahead 排除など) を分析
- 我々の方法論で再現できない = post-hoc selection の罠だった可能性高 (Qiita 著者の特定期間/特定 cell cherry-pick)

# 3. 期待効果と次フェーズ

## 3.1 期待される verdict 分岐

- **AUDJPY H4 5% 48H が SHADOW_CANDIDATE**: Qiita 再現成功、shadow promote へ
- **AUDJPY H4 5% 48H が REJECT, 他に SHADOW_CANDIDATE 存在**: Qiita 著者の cell は単発だったが、別 cell に edge → 当該 cell shadow promote
- **全 REJECT (3,744 cell)**: Qiita stat の post-hoc selection 確定、price-shock reversion thesis を **真の hypothesis kill**、CAD-1/SR Phase 2.5/fx-nexus OOS に集中

## 3.2 想定実行時間

- fetcher 修正: 5 分
- 28 parquet fetch (MASSIVE API rate limit 込み): 30-60 分
- BT 再走 (3744 cell): 30-60 分
- 報告物生成: 15 分
- **総計**: 1.5-2.5 時間

## 3.3 リソース

- MASSIVE API quota: 28 fetch (1 fetch = ~2-3 chunk request) ≈ 60-100 API calls. 通常 rate limit 内
- disk: H4 ~50KB × 13 + H1 ~400KB × 13 ≈ 6 MB 追加。問題なし
