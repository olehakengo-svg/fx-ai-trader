---
id: 20260515-1702-price-shock-reversion-grid-bt
title: "[Price-Shock Reversion Grid BT] 価格分布モーメント駆動の急変後平均回帰エッジ発掘 — sentiment フリー grid (pair × horizon × percentile × vol_quintile)"
owner: codex
status: queued
priority: P1
created_at: 2026-05-15T17:02:00+0900
roadmap_gate: "Qiita『クオンツ入門 予測を捨て、分布を読め』(2026-05-15 司令塔読了) の枠組み移植。Phase 1b/2a の OANDA 小売 sentiment contrarian は 14 pair / 756 cell すべて NULL (project_phase2a_oanda_contrarian_v2_2026_05_13.md, project_phase1b_oanda_contrarian_bt_2026_05_07.md)。本タスクは sentiment 非依存で、価格自身の下位/上位分位 (1%/2.5%/5%) を起点とする mean reversion を grid 探索する。AUDJPY H4 で WR=60.06% / N=1,369 / EV=+0.2024% の事例が原典で報告されている。W3-5 FDR / W4-EDA / shadow-first quant architecture と整合。"
rule: pre-reg
related:
  - data/cache/massive/*_4h.parquet                              # primary TF (H4 = 240分足、原典準拠)
  - data/cache/massive/*_1h.parquet                              # secondary TF (sanity)
  - app.py:run_daytrade_backtest                                 # 既存 BT entry
  - tools/oanda_contrarian_bt.py                                 # Phase 1b/2a の grid runner 雛形 (cell 設計を再利用)
  - knowledge-base/wiki/decisions/phase2a-oanda-contrarian-v2-null.md
  - feedback_shadow_first_quant_architecture                     # BT は sanity filter、shadow が真の estimator
  - feedback_bt_must_use_massive                                 # MASSIVE parquet 必須、Yahoo 禁止
  - feedback_partial_quant_trap                                  # N/WR/EV だけ NG、PF/Wilson/Bonf/Kelly まで
  - feedback_label_empirical_audit                               # ラベル実測必須、演繹回答禁止
  - feedback_codex_mock_test_trap                                # mock-only テスト禁止、E2E 必須
  - feedback_codex_stash_leak                                    # stash 漏れ禁止、commit 必須
  - feedback_codex_schema_hallucination                          # CREATE TABLE 文を spec に直接貼る
  - feedback_live_shadow_separation                              # is_shadow=0 分離
  - feedback_exclude_xau                                         # XAU 除外
---

# 0. 思想 (Qiita 原典: 予測を捨て、分布を読め)

> 「価格予測ではなく、リターン分布のモーメント (歪度・尖度) と極値分位の挙動から、価格ショック後の平均回帰エッジを体系的に発掘する」

**FX 翻訳**:
- 下位 1%/2.5%/5% 急落 → 短期 (1〜48H) 平均回帰 → **LONG**
- 上位 1%/2.5%/5% 急騰 → 短期 (1〜48H) 平均回帰 → **SHORT**
- ボラ分位 (Q1〜Q5) で条件付け → 高ボラ域で EV 倍化の観測あり (原典: AUDJPY Q5 急落後 24H EV=+0.1446% → 48H EV=+0.2854%)

**OANDA contrarian (Phase 1b/2a) との違い**:
- Phase 1b/2a: **小売 sentiment** 起点 (外部データ依存、90 日窓のみ、14 pair / 756 cell すべて NULL)
- 本タスク: **価格自身の分位** 起点 (sentiment 不要、12.3y データ純度高、N 確保容易)

**W4-EDA との関係**:
- W4-EDA で 91% が「思想は正、設計が誤」と判明 (project_w4_eda_complete_2026_05_05.md)
- 本タスクは **戦略候補生成** であり、survivor はそのまま shadow promote 候補

# 1. 設計

## 1.1 Grid 定義 (post-hoc tune 禁止、pre-reg literal)

| 軸 | 値 | サンプル数 |
|---|---|---|
| pair | USD_JPY, EUR_USD, GBP_USD, AUD_USD, NZD_USD, USD_CAD, USD_CHF, EUR_JPY, GBP_JPY, AUD_JPY, NZD_JPY, EUR_GBP, EUR_AUD, GBP_JPY | 14 (XAU 除外) |
| TF | H4 (primary, 原典準拠), H1 (secondary sanity) | 2 |
| percentile | 1%, 2.5%, 5% (下側 LONG / 上側 SHORT) | 6 (3×2 direction) |
| horizon (bars) | 1, 3, 6, 12 (H4 で 4H/12H/24H/48H) | 4 |
| vol_quintile | ALL, Q1, Q2, Q3, Q4, Q5 (vol20 = rolling_std(log_return, 20)) | 6 |

**Total cells**: 14 × 2 × 6 × 4 × 6 = **4,032 cell**

**Pre-reg 多重検定補正**: BH-FDR (m=4032, q=0.10)。Bonferroni 厳格版 (α/m = 1.24e-5) も併報。

## 1.2 シグナル定義 (リーケージ排除)

```python
# 足 t の終値確定後、足 t+1 の始値でエントリー (next-bar-open)
# 足 t の log_return = log(close_t / close_{t-1})
# percentile は rolling 252 (≒1年) で計算、look-ahead 回避

log_return_t = log(close_t / close_{t-1})
lower_pct = rolling_quantile(log_return, window=252*4_or_252, pct)  # H4 なら 252 日 = 1512 bars
upper_pct = rolling_quantile(log_return, window=...,  1-pct)

if log_return_t <= lower_pct[t]:
    signal = "LONG_SHOCK"
    entry_price = open_{t+1}
elif log_return_t >= upper_pct[t]:
    signal = "SHORT_SHOCK"
    entry_price = open_{t+1}
else:
    signal = None

# ボラ分位も同様に look-ahead 回避
vol20 = rolling_std(log_return, 20)
vol_q = rolling_qcut(vol20, q=5, window=252*4)  # 過去 1 年で分位、当該 bar は除外
```

**Exit**: horizon bars 経過後の close (固定保有)。BT 段階では損切り/利確なし (原典準拠、純粋エッジ測定)。

## 1.3 BT 出力カラム (cell 単位)

各 cell に対し:
- `N` (trades 数)
- `WR` (勝率, exit close > entry open for LONG)
- `EV_pip`, `EV_pct` (平均リターン、pip と %)
- `PF` (profit factor)
- `Wilson_lower_95` (WR の Wilson 下限)
- `Sharpe` (年率, √252×4 補正)
- `Kelly_fraction` (f* = WR - (1-WR)/RR、RR は平均利益/平均損失)
- `max_drawdown_pct`
- `MAE_mean_pct`, `MAE_p5_pct` (最大逆行幅、平均と 5% 点)
- `MFE_mean_pct` (最大順行幅)
- `year_sign_flip_count` (年別 EV 符号が aggregate と異なる年数)
- `bonferroni_pass` (p < α/m)
- `bh_fdr_pass` (BH q=0.10)

## 1.4 サニティゲート (cell 採択条件、pre-reg)

| ゲート | 条件 | 根拠 |
|---|---|---|
| G1 N | N >= 30 | 統計的最小 |
| G2 Wilson | Wilson_lower_95(WR) >= 0.50 | partial_quant_trap 回避 |
| G3 PF | PF >= 1.20 | shadow-first sanity (Kelly 厳格化は shadow 後) |
| G4 BH-FDR | bh_fdr_pass = True (q=0.10) | 多重検定補正 |
| G5 year stability | year_sign_flip_count <= 1 | W3-3 S4 の post-hoc selection 罠回避 |
| G6 cost-aware | EV_pip >= 1.5 × typical_spread_pip(pair) | コスト超過リスク |

**G1-G6 すべて pass** → `SHADOW_CANDIDATE`
**G1-G4 pass, G5 or G6 fail** → `CONDITIONAL` (司令塔判定)
**G1-G4 のいずれか fail** → `REJECT`

## 1.5 DDL (Codex schema hallucination 防止のため直接貼付)

```sql
CREATE TABLE IF NOT EXISTS price_shock_grid_cells (
    cell_id          TEXT PRIMARY KEY,         -- "{pair}_{tf}_{direction}_{pct}_{horizon}_{vol_q}"
    pair             TEXT NOT NULL,
    tf               TEXT NOT NULL,            -- "H4" or "H1"
    direction        TEXT NOT NULL,            -- "LONG_SHOCK" or "SHORT_SHOCK"
    percentile       REAL NOT NULL,            -- 0.01, 0.025, 0.05
    horizon_bars     INTEGER NOT NULL,
    vol_quintile     TEXT NOT NULL,            -- "ALL", "Q1"..."Q5"
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
    verdict          TEXT NOT NULL,            -- "SHADOW_CANDIDATE" / "CONDITIONAL" / "REJECT"
    period_start     TEXT NOT NULL,
    period_end       TEXT NOT NULL,
    bt_data_source   TEXT NOT NULL,            -- "MASSIVE_parquet"
    generated_at     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_psg_verdict ON price_shock_grid_cells(verdict);
CREATE INDEX IF NOT EXISTS idx_psg_pair_tf ON price_shock_grid_cells(pair, tf);
```

## 1.6 報告物

`reports/price_shock_reversion_grid/` 配下:
1. `grid_full.csv` — 全 4,032 cell の raw stats
2. `survivors.md` — `SHADOW_CANDIDATE` cell list (verdict + 7 軸 evidence + 思想/設計欠陥/再設計案)
3. `conditional.md` — `CONDITIONAL` cell list (G5/G6 fail 詳細)
4. `null_summary.md` — 全 REJECT 統計、失敗パターン分類 (direction-led / N 不足 / Wilson fail / etc)
5. `SUMMARY.md` — 司令塔判定用ダイジェスト (W4-EDA 監査レポート形式: Verdict / Rec / 思想 / 設計欠陥 / 再設計案 + 🔴🟠 emoji + 太字 evidence)
6. `verdict.md` — 全体 GO/NO-GO + shadow promote 推奨 cell

# 2. 完了条件

1. `tools/price_shock_reversion_bt.py` 新規作成 (grid runner、MASSIVE parquet 必須、Yahoo 禁止)
2. `modules/price_shock_grid_db.py` DDL 適用 + insert helpers
3. `tests/test_price_shock_reversion_bt.py` (unit + **integration with real MASSIVE parquet**, mock-only 禁止)
4. 14 pair × 2 TF × 全 grid 実行、`reports/price_shock_reversion_grid/` 6 ファイル出力
5. `data/price_shock_grid_cells.db` (or 既存 fx_ai_trader.db に table 追加) で永続化
6. 生成物即 commit (--no-verify 可、ただし `.git/index.lock` blocked なら final.md 明記)
7. `final.md` には: 投入 cell 数、SHADOW_CANDIDATE 数、CONDITIONAL 数、REJECT 数、top 10 survivors の 1 行 evidence

# 3. 司令塔ガード (pre-flight checklist)

## 3.1 必須遵守 (違反 = ROLLBACK)

- [ ] **MASSIVE parquet 必須**: `data/cache/massive/*_4h.parquet`、Yahoo 禁止 (feedback_bt_must_use_massive)
- [ ] **XAU 除外** (feedback_exclude_xau)
- [ ] **next-bar-open エントリー** (look-ahead リーケージ排除)
- [ ] **rolling percentile / rolling vol_q** で当該 bar を含めず計算 (look-ahead 回避)
- [ ] **mock-only テスト禁止**: integration test は実 parquet 読み込み (feedback_codex_mock_test_trap)
- [ ] **stash 漏れ禁止**: 全変更を main branch に commit、`git status` clean で終了 (feedback_codex_stash_leak)
- [ ] **DDL は spec の §1.5 を literal 適用** (feedback_codex_schema_hallucination)
- [ ] **is_shadow 系混入なし**: 純粋 BT のみ、Live は別 (feedback_live_shadow_separation)

## 3.2 思想ガード (post-hoc tune 禁止)

- [ ] Grid は §1.1 literal、Codex で「N 不足だから q=0.20 に緩めた」等の post-hoc 改訂は **司令塔 review 必須** で final.md に明記
- [ ] G5 year_sign_flip も literal、cell-by-cell 例外不可
- [ ] survivor cell は **shadow promote 候補**であり、本 task で Live promote は禁止

## 3.3 失敗時の挙動

- 全 cell NULL → **正しい結果** として `null_summary.md` で失敗パターン分類して報告 (feedback_success_until_achieved の趣旨: closure 短絡は禁止だが、pre-reg NULL は科学的成果)
- pre-commit hook で blocked → `--no-verify` で commit、final.md に hook log 添付 + 司令塔へ後追い修正依頼
- MASSIVE parquet 不在 pair (XAU 等以外で見つかった場合) → final.md に skip 一覧記載、grid 出力は実在 pair のみ

# 4. 次フェーズ (本 task 完了後の司令塔判断材料)

- SHADOW_CANDIDATE >= 5 cell → Wave 2 で shadow promotion + 6 ヶ月 OOS 観測
- SHADOW_CANDIDATE 1-4 cell → 個別 cell 単体監査 (W4-EDA 形式) で thesis/design 切り分け
- SHADOW_CANDIDATE 0 cell → **Hypothesis kill**、Qiita 原典の AUDJPY 事例は 2022-2026 期間限定 / 単独事例の post-hoc selection と確定、関連方向 (extreme decile sanity) を諦めて他系統 (CAD-1 / SR Phase 2.5 / fx-nexus OOS) に集中

## 5. 想定実行時間

- BT runner 実装: 2-3 時間 (既存 oanda_contrarian_bt.py を骨格再利用)
- 14 pair × 2 TF × 4032 cell 実行: 1-2 時間 (parquet read + vectorized numpy)
- 報告物生成: 30 分
- **総計**: 4-6 時間 (1 セッション完結を目標)
