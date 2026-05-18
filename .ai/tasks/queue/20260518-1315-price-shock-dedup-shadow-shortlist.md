---
id: 20260518-1315-price-shock-dedup-shadow-shortlist
title: "[Price-Shock Dedup→Shortlist] 227 SHADOW_CANDIDATE を distinct family に dedup、shadow promote 上位 N 候補を選定"
owner: codex
status: queued
priority: P1
created_at: 2026-05-18T13:15:00+0900
roadmap_gate: "前 task 20260515-2222-price-shock-bt-data-backfill-rerun (commit f7f9cd5e) は MASSIVE backfill 完了 + 3,744 cell フルグリッドで 227 SHADOW_CANDIDATE / 15 CONDITIONAL / 3502 REJECT を出力。Qiita AUDJPY 主対象は WR/EV 完全再現 (60.00% vs 60.06%, 0.2148% vs 0.2024%) だが N gap (315 vs 1369) は methodology 差として説明済。survivor 227 cell の (pair, TF, direction) tuple は **23 distinct family** に集約可能で、多くは同一 underlying edge を異なる horizon/percentile/vol_q で観測した overlap。本 task は dedup + 代表 cell 選定 + 独立確認カウント + shadow promote 上位 shortlist 出力。実装 (strategy module 化 + demo_trader 統合) は別 task で行う (Phase B)。本 task は Phase A 分析専用。"
rule: pre-reg
related:
  - data/price_shock_grid_cells.db                         # 3,744 cell の raw stats、SQL クエリ対象
  - reports/price_shock_reversion_grid/survivors.md        # 227 cell リスト
  - reports/price_shock_reversion_grid/SUMMARY.md
  - reports/price_shock_reversion_grid/grid_full.csv
  - modules/price_shock_grid_db.py                         # DDL
  - tools/price_shock_reversion_bt.py                      # BT (再走不要、参照のみ)
  - feedback_shadow_first_quant_architecture
  - feedback_partial_quant_trap
  - feedback_label_empirical_audit
  - feedback_success_until_achieved
  - feedback_codex_stash_leak
  - project_price_shock_reversion_queued_2026_05_15
---

# 0. 思想

前 task は data backfill + フルグリッドで Qiita 再現 + 227 SHADOW_CANDIDATE を発見。
しかし 227 cell の多くは **同一 underlying edge を異なる cell で観測しただけ** (overlap)。
例: `EUR_GBP_H1_LONG_SHOCK` だけで 14+ cell が survivor。

**本 task の目的**: 
1. (pair, TF, direction) 単位で family を定義 → 23 distinct family
2. 各 family 内の代表 cell を選定 (max Wilson_lower、Bonf 優先)
3. 各 family の独立確認強度 (Bonf-passing cell 数) を集計
4. Top N (= max 10) shortlist を shadow promote 推奨 (Phase B 実装の入力)
5. 棄却 family の reason 記録

**Phase B との分離**: 戦略 code 化 + demo_trader 統合 + shadow 開始は本 task でやらない。本 task は **司令塔判断のための分析レポート専用**。

# 1. 設計

## 1.1 Family 定義

```python
family_key = (pair, tf, direction)
# 例: ("EUR_GBP", "H1", "LONG_SHOCK")
```

Survivor 227 cell を `family_key` で grouping。前 task の survivors.md から 23 family が既に確認済:
- LONG_SHOCK: 16 family (AUD_JPY H1/H4, AUD_USD H1, EUR_AUD H1/H4, EUR_GBP H1/H4, EUR_JPY H1/H4, EUR_USD H1, GBP_JPY H1, GBP_USD H1, NZD_JPY H1, NZD_USD H1, USD_CAD H1, USD_CHF H1)
- SHORT_SHOCK: 7 family (EUR_USD H1/H4, NZD_USD H1, USD_CAD H1, USD_CHF H1/H4, USD_JPY H4)

## 1.2 代表 cell 選定アルゴリズム (pre-reg literal)

各 family について以下を順に試し、最初に該当した cell を representative とする:

```sql
-- 優先順位:
-- 1) Bonferroni passing (bonferroni_pass=1) cell の中で wilson_lower_95 最大
-- 2) なければ BH-FDR passing (bh_fdr_pass=1) cell の中で wilson_lower_95 最大
-- 3) tie-break: ev_pct 最大 → N 最大 → cell_id 辞書順

WITH family_ranked AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY pair, tf, direction
            ORDER BY 
                bonferroni_pass DESC,        -- Bonf pass を最優先
                bh_fdr_pass DESC,            -- 次に BH-FDR
                wilson_lower_95 DESC,        -- Wilson 下限
                ev_pct DESC,                 -- EV%
                n_trades DESC,               -- N
                cell_id ASC                  -- 辞書順
        ) AS rn
    FROM price_shock_grid_cells
    WHERE verdict = 'SHADOW_CANDIDATE'
)
SELECT * FROM family_ranked WHERE rn = 1;
```

## 1.3 独立確認強度 (Family Robustness Score)

各 family について追加で集計:

| メトリック | 定義 |
|---|---|
| `family_cell_count` | family 内の SHADOW_CANDIDATE cell 数 (overlap 含む) |
| `bonf_pass_count` | family 内で bonferroni_pass=1 の cell 数 |
| `bh_pass_count` | family 内で bh_fdr_pass=1 の cell 数 |
| `wilson_lo_mean` | family 内 cell の wilson_lower_95 平均 |
| `wilson_lo_max` | family 内 cell の wilson_lower_95 最大 (= 代表 cell の値) |
| `ev_pct_mean` | family 内 cell の ev_pct 平均 |
| `n_trades_max` | family 内 cell の n_trades 最大 |
| `n_trades_min` | family 内 cell の n_trades 最小 |
| `horizon_coverage` | family 内 cell が cover している horizon の数 (1/3/6/12 の何個) |
| `percentile_coverage` | family 内 cell が cover している percentile の数 (1/2.5/5 の何個) |
| `vol_q_coverage` | family 内 cell が cover している vol_quintile の数 (ALL/Q1-Q5 の何個) |

**解釈**:
- `bonf_pass_count >= 3` → 強い独立確認 (異なる horizon/percentile で同じ edge が再現)
- `bonf_pass_count = 1` のみ → cell selection effect の可能性、慎重
- `horizon_coverage >= 3` AND `percentile_coverage >= 2` → edge は parameter robust

## 1.4 Shortlist 選定基準 (pre-reg)

Family を以下の rule で 4 tier に分類:

### Tier 1 (TOP PROMOTE) — Phase B で実装最優先 (max 5 family)
- bonf_pass_count >= 3
- wilson_lo_max >= 0.55
- n_trades_max >= 100

### Tier 2 (PROMOTE) — Phase B で次優先 (max 5 family)
- bonf_pass_count >= 1
- wilson_lo_max >= 0.52
- n_trades_max >= 60
- Tier 1 を除く

### Tier 3 (WATCH) — Shadow 観測のみ、自動執行なし (max 5 family)
- bh_pass_count >= 1
- wilson_lo_max >= 0.50
- n_trades_max >= 30
- Tier 1/2 を除く

### Tier 4 (REJECT) — 棄却
- 上記条件不満足の family
- 棄却理由を明記

**全 family の Tier 1+2+3 合計は最大 15 family**。残り 8 family は Tier 4 (理由付き)。

## 1.5 出力物

### 1.5.1 `reports/price_shock_reversion_grid/dedup_families.csv`

全 23 family の代表 cell + Robustness Score 集計。CSV header:
```
family_key,pair,tf,direction,
rep_cell_id,rep_percentile,rep_horizon,rep_vol_q,
n_trades,win_rate,wilson_lower_95,profit_factor,ev_pct,ev_pip,
bonferroni_pass,bh_fdr_pass,
family_cell_count,bonf_pass_count,bh_pass_count,
wilson_lo_mean,wilson_lo_max,ev_pct_mean,n_trades_max,n_trades_min,
horizon_coverage,percentile_coverage,vol_q_coverage,
tier,tier_reason
```

### 1.5.2 `reports/price_shock_reversion_grid/shadow_promote_shortlist.md`

司令塔判断用 narrative report。構造:

```markdown
# Shadow Promote Shortlist (Phase A 分析)

## Verdict
**Tier 1 N family / Tier 2 N family / Tier 3 N family / Tier 4 N family**

## Tier 1 (TOP PROMOTE) — Phase B 実装最優先

### {pair}_{tf}_{direction}
- **Rep cell**: `{cell_id}` — pct={pct}, horizon={h}, vol_q={q}
- **Stats**: N={N}, WR={WR}, Wilson_lo={wlo}, PF={PF}, EV={ev_pct}% ({ev_pip}pip)
- **Robustness**: bonf={bonf_count}/family={family_count} cell, horizon_cov={h_cov}/4, pct_cov={p_cov}/3
- **思想**: 価格が下位{pct}% percentile 急落 + vol_q={q} → next bar open ロング → {h} bars 後 close
- **Phase B 実装要点**: 
  - Strategy file: `strategies/{daytrade or scalp}/price_shock_rev_{pair_lc}_{direction_lc}.py`
  - Entry signal: rolling 1512-bar (H4) or 252-bar (H1) percentile + ATR/vol filter
  - Exit: fixed bar count (no SL/TP in BT、但し Shadow では Live SL/TP 司令塔別途決定)
  - Pair scope: {pair} only (cross-pair 拡張は別 BT 必要)

(以下 Tier 1 family を Wilson_lo 降順で全件)

## Tier 2 (PROMOTE)
(同形式)

## Tier 3 (WATCH)
(同形式、Phase B 実装は司令塔 review 待ち)

## Tier 4 (REJECT)
| Family | Rep Wilson_lo | Rep N | bonf_pass | Reason |
|---|---|---|---|---|
(全 reject family、reason は基準どれが不満足か明記)

## 思想
価格自身の極値分位後 mean reversion edge。Family 単位で dedup し、horizon/percentile/vol_q overlap を真の独立 edge から切り分けた。

## 設計欠陥 (現時点で見える)
- BT は固定 horizon exit (動的 SL/TP なし) — Live では cost-aware exit が edge を削る可能性
- Q5 (高ボラ) 集中 — vol 分位の look-ahead 排除確認済 (rolling 1512-bar) だが、Live regime shift で Q5 定義が変動するリスク
- Cross-pair correlation 未補正 — EUR_GBP / EUR_AUD / EUR_USD 同時 trigger で portfolio concentration risk

## Phase B 推奨スケジュール
1. **Week 1**: Tier 1 上位 3 family を strategy module 化、unit test
2. **Week 2**: demo_trader 統合 + shadow execution 開始
3. **Week 3-6**: N >= 30 Live Shadow 蓄積、Wilson_lo 維持確認
4. **Week 7**: Live promote 判定 (R1: 365日BT + Bonferroni、または Live N >= 30 + Wilson_lo >= 0.50)
```

### 1.5.3 `reports/price_shock_reversion_grid/dedup_audit.md`

methodology audit:
- 全 SHADOW_CANDIDATE cell 数 (DB クエリ結果と survivors.md の一致確認)
- Family count 検証 (23 と一致するか)
- Tier 振り分け数 (上限超えていないか)
- 各 Tier の代表 cell が selection rule 通り選ばれているか抜き打ち確認 (3 cell)

# 2. 完了条件

1. `tools/price_shock_dedup_analysis.py` 新規作成 (SQL クエリ + 集計 + Tier 振り分け + report 生成)
2. `reports/price_shock_reversion_grid/dedup_families.csv` 生成 (23 行 + header)
3. `reports/price_shock_reversion_grid/shadow_promote_shortlist.md` 生成 (司令塔判断用 narrative)
4. `reports/price_shock_reversion_grid/dedup_audit.md` 生成 (methodology audit)
5. `tests/test_price_shock_dedup_analysis.py` (unit + integration with real DB, mock 禁止)
6. `final.md` に: Tier 1/2/3/4 family count、Tier 1 上位 3 family の (pair, TF, direction) 一覧
7. 生成物即 commit、`git status` clean

# 3. 司令塔ガード

## 3.1 必須遵守

- [ ] **DB は `data/price_shock_grid_cells.db` を使う** (前 task 出力、再 BT 不要)
- [ ] **Tier 振り分け rule は §1.4 literal** (Wilson_lo / N / bonf_count threshold を post-hoc 緩和禁止)
- [ ] **Tier 1+2+3 合計 max 15 family**: 残り 8 は必ず Tier 4
- [ ] **family_key 定義は §1.1 literal**: (pair, tf, direction) tuple のみ。percentile/horizon/vol_q では grouping しない
- [ ] **代表 cell 選定の tie-break ロジックは §1.2 literal**
- [ ] **mock 禁止** (feedback_codex_mock_test_trap)
- [ ] **stash 漏れ禁止** (feedback_codex_stash_leak)

## 3.2 Phase B 禁止項目 (本 task でやらない)

- [ ] Strategy module の新規実装 (Phase B 対象)
- [ ] demo_trader 統合 (Phase B 対象)
- [ ] Shadow execution 開始 (Phase B 対象)
- [ ] tier-master.md 更新 (Phase B 対象)
- [ ] Live SL/TP 設計 (Phase B 対象)
- [ ] Q5 vol_quintile の Live 計算ロジック (Phase B 対象)

本 task が触っていいのは:
- 新規 tool/test ファイル
- `reports/price_shock_reversion_grid/` の新規 markdown/csv
- `final.md` (commit summary)

## 3.3 失敗時挙動

- DB queryで cell 数が survivors.md と乖離 → audit md に明記、司令塔に報告 (Codex side で勝手に修正しない)
- Tier 1 が 0 件 → reject ではなく、しきい値 (wilson_lo>=0.55) のリテラル違反として final.md に明記
- pre-commit hook fail → `--no-verify` で commit、hook log 添付

# 4. 期待効果

## 4.1 想定 Tier 分布 (司令塔事前推測)

| Tier | 推測 family 数 | 代表例 |
|---|---|---|
| 1 | 3-5 | EUR_GBP H1 LONG, NZD_JPY H1 LONG, EUR_AUD H1 LONG (highest bonf_pass + wilson_lo > 0.60) |
| 2 | 3-5 | NZD_USD H1, AUD_JPY H1, EUR_JPY H4 (mid-tier wilson_lo 0.52-0.60) |
| 3 | 3-5 | USD_CHF H4, USD_JPY H4 SHORT etc. (BH only, small N) |
| 4 | 8-10 | SHORT_SHOCK 系の一部、cross-pair で N 小さい family |

実測で大きく外れた場合は司令塔 review 必須。

## 4.2 Phase B 入力としての shortlist 品質

- Tier 1 family の Wilson_lo > 0.55 = Live Shadow で N=30 蓄積後も >= 0.50 を維持する可能性高
- bonf_pass_count >= 3 = horizon/percentile robust → parameter brittleness 低
- これが next phase の strategy implementation 着手判断の根拠になる

## 4.3 想定実行時間

- SQL クエリ + 集計 ロジック実装: 30 分
- Test 作成: 15 分
- Report 生成 + commit: 15 分
- **総計**: 1 時間以内
