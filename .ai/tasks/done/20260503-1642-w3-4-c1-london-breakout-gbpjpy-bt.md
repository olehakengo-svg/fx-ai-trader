---
id: 20260503-1642-w3-4-c1-london-breakout-gbpjpy-bt
title: W3-4 — C-1 London Open Breakout BT (GBPJPY) pre-registered (Rule 1, Shadow promote 候補)
owner: codex
status: queued
priority: P0
created_at: 2026-05-03T16:42:00+0900
roadmap_gate: Gate 1 (新 alpha 候補 — Shadow 並走で N 蓄積)
rule: R1
parent_plan: /Users/jg-n-012/.claude/plans/find-out-way-of-fizzy-patterson.md
wave: W3 Tier 2 (parallel 2/3)
---

# Objective

カタログ §C-1 London Open Breakout (Asian Range Break) を **GBPJPY M5 約12年 (2014-01-01 〜 2026-04-30)** で内部 BT 検証する。Pre-registered な sensitivity grid 81 試行 + 統計ガード + validity check を一括実行し、Verdict matrix v1 の 7 軸で Scenario A (Shadow promote) / B (hold) / C (reject) を判定する。

H-1 audit (`knowledge-base/wiki/learning/h1-spread-time-audit-2026-05-03.md`) で GBPJPY 12-16 UTC が peak 帯と確認済 → London open (07-08 UTC) で Asian range break、12-16 UTC で利益確定の構造が現実的という前提検証。

**本タスクは BT のみ。Live promote / Shadow 投入は別タスク (Scenario A 確定時のみ)。**

# Hypothesis

- **H1**: GBPJPY M5 12年で、07:00-08:00 UTC の Asian range break エントリーは Verdict matrix v1 の B 帯 (Wilson lo ≥ 50%, PF ≥ 1.10, OOS/IS PF ≥ 0.80, Bonf p < 0.05/m, Sharpe ≥ 0.5, Kelly > 0) を満たす独立 alpha である。
- **H2**: rsk_gbpjpy_reversion (R3 PR #12 修正待ち) との rolling 30d correlation ρ < 0.3 で、戦略 alpha は独立。
- **H3**: 81 sensitivity 試行のうち pre-registered primary `(Asian 7h / M5 close break / range×1.0 exit / range≥median×1.0)` が B 帯を通過し、Bonferroni m=81 で耐性がある。

H1+H2+H3 すべて true → **Scenario A (Shadow promote 候補)**
B 帯境界 + Bonf 失格 / 相関 0.3-0.5 → **Scenario B (hold + 再検証)**
H1 不成立 (Wilson lo < 50% or Kelly ≤ 0 or null bootstrap 95th 未満) → **Scenario C (catalog §C-1 を academic only 降格)**

# Context

- 親プラン: `/Users/jg-n-012/.claude/plans/find-out-way-of-fizzy-patterson.md`
- カタログ §C-1: `knowledge-base/wiki/learning/global-retail-fx-edges-2026-05-03.md`
- H-1 audit: `knowledge-base/wiki/learning/h1-spread-time-audit-2026-05-03.md` (GBPJPY hour profile, 5/16/17/22 UTC に spread 谷)
- Codex review: `knowledge-base/wiki/learning/codex-review-wave1-2026-05-03.md`
- Wave 1 内部 KB:
  - `project_w3_2_s2_verdict_pre_reg` — B-帯 pre-reg 緩和指針
  - `project_rsk_gbpjpy_bar_close_gate_pending` — rsk_gbpjpy R3 PR #12 修正待ち、Shadow tier で時間帯分離が要件
  - `feedback_partial_quant_trap` — N/WR/EV のみで判断不可、PF / Wilson / WF / Bonf / Kelly 必須
  - `feedback_label_empirical_audit` — コード演繹禁止、ラベル×WR 実測
  - `feedback_check_orphan_local_app` — 分析前に `pgrep -f app.py` で orphan 検出 + Render API を一次ソース化
  - `feedback_live_shadow_separation` — Live PnL は `is_shadow=0` 分離 (本タスクは BT only なので該当しないが artifact 記録時はタグ必須)
  - `feedback_cohort_time_check` — BoE 政策変動期 (2016 Brexit, 2022 Truss budget) に PnL 集中なし確認
  - `feedback_ma_filter_breaks_mr` / `feedback_hmm_gate_same_trap` — conventional gate を素直に積むと edge 消滅。本タスクの Asian-range-median filter は単独 cell 実測必須
  - `feedback_spread_basis_for_mafe` — spread profile 差し引きは entry_price 基準
- Wave 1 並走: rsk_gbpjpy_reversion R3 PR #12 (時間帯分離で衝突回避必須)
- 公開実証 (★ webfetch bot block 多い):
  - https://www.quantifiedstrategies.com/london-breakout-strategy/
  - https://forextester.com/blog/opening-range-breakout-trading-strategies/ (ORB N=114, WR=74.56%)
  - https://www.fxcc.com/london-breakout-strategy

# Scope

Codex MAY change:

- `tools/bt/c1_london_breakout.py` (new) — 81-cell sensitivity BT runner、deterministic seed、reproducible
- `tools/bt/c1_validity_checks.py` (new) — null bootstrap 1000 回 / rsk 相関 / cohort 検証 / spread profile 差し引き
- `tests/test_c1_london_breakout.py` (new) — Asian range 計算 / breakout 判定 / time gate / Bonferroni 適用の単体テスト
- `knowledge-base/wiki/learning/c1-london-breakout-bt-2026-05-03.md` (new) — BT レポート (sensitivity grid 81 行表 + Scenario verdict)
- `knowledge-base/raw/bt-results/c1-london-breakout-{json,md}` (new) — 生 artifact
- `.ai/runs/<new-run-dir>/final.md` (new) — 実行レポート
- (Scenario A 時のみ) `knowledge-base/wiki/decisions/c1-london-breakout-pre-registration-2026-05-03.md` — pre-registration LOCK 文書

Codex MAY NOT change:

- `app.py`, `modules/`, `strategies/` — BT のみ。本番 signal 関数を読むのは可だが書き換え禁止
- `knowledge-base/wiki/index.md`, `knowledge-base/wiki/tier-master.md` — Tier 変更禁止 (本タスクは BT 検証のみ)
- `tools/scalp_re_enable_bt.py`, `tools/vec_harness_chunked_cli.py` — A1/A2 領域に触らない
- Render API 書き込み, 本番 DB, `.env`, OANDA secrets, OANDA endpoint
- `live_ng_cells` SQLite テーブル, `oanda_audit` テーブル
- 既存未コミット変更 (`modules/demo_trader.py`, `knowledge-base/raw/hunt_events/2026-05-02.jsonl`, `knowledge-base/wiki/sessions/2026-05-03-session.md`, `knowledge-base/raw/cell_deepdive/`)

# Required Reading

- `CLAUDE.md` (Rule 1 protocol、KB read rules)
- `knowledge-base/wiki/syntheses/roadmap-v2.1.md` (Gate 1 / Scalp 枝 / Track E)
- `knowledge-base/wiki/learning/global-retail-fx-edges-2026-05-03.md` §C-1
- `knowledge-base/wiki/learning/h1-spread-time-audit-2026-05-03.md` (GBPJPY hour profile)
- `knowledge-base/wiki/learning/codex-review-wave1-2026-05-03.md`
- `knowledge-base/wiki/analyses/friction-analysis.md` (GBPJPY 摩擦 / spread profile)
- `knowledge-base/wiki/analyses/bt-live-divergence.md` (6 つの構造的楽観バイアス)
- `knowledge-base/wiki/lessons/index.md` (関連 lesson)
- `modules/bt_vec_harness.py` — `_load_local_cache`, `load_1m`, `simulate_outcome`, `VecBacktestRunner` (signal は外部だが OHLCV/spread profile 取得 API を参照)

# 対象データ / Data Separation (厳守)

| 用途 | 出典 | 混入禁止対象 |
|---|---|---|
| BT bars (OHLCV M5) | Massive Market Data MCP / 既存 parquet cache for `GBPJPY 5m 12yr` | Render `oanda_audit`, `is_shadow=0` Live, OANDA fills |
| Asian range / breakout 計算 | BT bars のみ | Live decision history |
| spread profile 差し引き | H-1 audit / `friction-analysis.md` の hour-bucket spread 中央値 | broker realtime spread |
| rsk_gbpjpy 相関 | Render API or 本番 DB read-only スナップショット (`is_shadow=1` 含む全件) → ローカルにコピーして比較 | ローカル app.py orphan データ (必ず `pgrep -f app.py` で確認、orphan は kill 不可なので Render API 一次ソース) |
| broker cross-check | yfinance / dukascopy / 別ソース GBPJPY M5 | 同一 cache (= 確認にならない) |

artifact は `data_source`, `live_separation="bt_only"`, `time_window`, `pair`, `interval` をすべて JSON header に明記。

# データ取得仕様

- pair: `GBP_JPY`
- interval: `M5`
- 期間: 2014-01-01 〜 2026-04-30 (約 12.3 年)
- 平日のみ、年末年始 (12/24-1/3) 除外
- BoJ 介入日除外 (USDJPY と同基準。GBPJPY も影響波及)
- BoE 決定日 / UK CPI 日 / NFP 日の ±30min 除外オプション (sensitivity 母数には含めない、感度確認のみ)

# 戦略仕様 (Pre-Registered Default — LOCK)

## Asian Range 定義
- window: 00:00-07:00 UTC (Tokyo session)
- range: window 内の high と low

## エントリー
- time gate: 07:00-08:00 UTC (London open) のみ
- LONG: M5 close > Asian high で BUY
- SHORT: M5 close < Asian low で SELL
- 必須フィルタ: Asian range > Asian range の 60-day rolling median (低ボラ日除外)

## エグジット
- 利食い: 12:00 UTC または entry から Asian range × 1.0 達成 (どちらか早い方)
- ストップ: break point から Asian range × 0.5 反対側
- 強制 close: 17:00 UTC (London close)

## Pre-Registered Primary Cell
**(Asian 7h / M5 close break / range×1.0 exit / range ≥ median×1.0)**

## Sensitivity 軸 (Bonferroni 母数 m=81 を pre-reg LOCK)

| 軸 | 値 (3段階) |
|---|---|
| Asian window | 6h / **7h** / 8h |
| breakout entry | **M5 close** / M5 high break / M1 close |
| exit | time-based 12 UTC / **range×1.0** / range×1.5 |
| Asian range filter | **median×1.0** / 1.2 / 1.5 |

合計 3×3×3×3 = **81 cell**。Bonferroni 補正は m=81 で固定。primary cell は太字。

# Statistical Conditions (Verdict matrix v1 — 主軸 7 軸 必須)

各 cell および primary cell について以下を全部測定する:

1. **N** (trade count, ≥30 を最低条件)
2. **Wilson 95% lower bound (WR)** (≥ 50% で B 帯)
3. **PF** (Profit Factor, ≥ 1.10 で B 帯)
4. **OOS/IS PF ratio** (Walk-Forward 3+ folds, ≥ 0.80)
5. **Bonferroni-corrected p** (m=81, p < 0.05/81 ≈ 6.17e-4)
6. **Sharpe** (annualized, ≥ 0.5)
7. **Kelly fraction** (> 0)

加えて以下を補助指標として記録:
- max DD (pip & %)
- avg holding bars
- per-cell trade list (timestamp, side, entry, exit, pnl_pip, asian_range_pip)
- spread profile を entry_price 基準で差し引いた net PnL (`feedback_spread_basis_for_mafe`)

# Validity Check

## V1 — null bootstrap (1000 試行)
- 各 cell について trade timestamp をランダムシャッフル → null distribution 構築
- ACCEPT: actual PF が 95th percentile 超え

## V2 — rsk_gbpjpy_reversion 相関
- rsk_gbpjpy_reversion (R3 PR #12 未 merge だが現行 main の Live PnL 系列を Render API で取得) との rolling 30-day Pearson 相関
- ACCEPT: |ρ| < 0.3 (独立 alpha)
- HOLD: 0.3 ≤ |ρ| < 0.5
- REJECT: |ρ| ≥ 0.5 (重複 alpha)

## V3 — broker cross-check
- yfinance または dukascopy で同期間の GBPJPY M5 を取得
- primary cell BT を別ソースで再実行 → trade list の sign / direction が同じこと
- WR / PF が ±10% 以内に収まること

## V4 — 時間コホート整合
- 期間を以下のサブコホートに分割し PF/WR を集計:
  - 2014-2016 pre-Brexit
  - 2016-2017 Brexit Vote 期
  - 2018-2019 (calm)
  - 2020 COVID
  - 2021-2022 (Truss budget)
  - 2023-2024
  - 2025-2026
- ACCEPT: 単一コホートに PnL 集中なし (どのコホートも全期間 PnL の 50% 未満)

## V5 — orphan check
- BT 開始前に `pgrep -f app.py` を実行、orphan があれば log に明記
- rsk_gbpjpy 相関のための Live データは **必ず Render API を一次ソース** として取得 (`feedback_check_orphan_local_app`)

## V6 — spread profile 補正
- entry_price 基準で hour-bucket median spread を差し引いた net PnL を必ず併記
- raw PnL (spread 込み) と net PnL の両方を artifact に記録

# Roadmap 寄与

Gate 1 = 新 alpha 候補による N-acceleration / DD 縮小経路。本タスクで Scenario A 確定 → 次タスクで Shadow tier 投入 (時間帯分離: rsk_gbpjpy = 全時間帯, c1-london-breakout = 07-17 UTC のみ) → Live N≥15 + Wilson lo ≥ 60% で Live promote 検討。月利 100% ロードマップに対し:
- Scenario A 確定確率 (事前): 30-40% (公開実証は信頼度低 / GBPJPY 特有の Brexit / Truss コホート歪み懸念)
- 確定時の月間寄与推定: 50-150 pip (small 1 trade/day × 60% pass × 7 pip net)

# Decision Procedure (Rule 1 — Slow & Strict)

## Step 1 — データ準備
1. `pgrep -f app.py` で orphan 検出、log に記録
2. `Massive Market Data MCP` で GBPJPY M5 12yr を取得 → parquet cache 化
3. broker cross-check 用に yfinance or dukascopy から同期間取得
4. spread profile を H-1 audit から hour-bucket median として読み込み
5. rsk_gbpjpy_reversion の Live PnL 時系列を **Render API から取得** (`/api/demo/trades` + `is_shadow=0` 含む全件)

## Step 2 — 81 cell BT 実行
- `tools/bt/c1_london_breakout.py` で deterministic seed で実行
- 各 cell について 7 軸統計を計算
- Bonferroni m=81 適用
- Walk-Forward 3 folds (4yr train / 4yr test 重複なし) を全 cell に適用
- artifact を `knowledge-base/raw/bt-results/c1-london-breakout-{json,md}` に保存

## Step 3 — Validity check
- V1〜V6 すべて実行
- primary cell が V1+V2+V3+V4 すべて ACCEPT → Scenario A 候補
- どれか HOLD → Scenario B
- どれか REJECT → Scenario C

## Step 4 — Verdict 確定 + レポート
- `knowledge-base/wiki/learning/c1-london-breakout-bt-2026-05-03.md` に以下を記載:
  - sensitivity grid 81 行表 (cell ごとに N/WR/Wilson/PF/OOS-IS/Bonf/Sharpe/Kelly)
  - primary cell の詳細
  - Validity check V1〜V6 結果
  - rsk_gbpjpy 相関図
  - cohort 別 PF/WR 表
  - spread profile 補正前後 PnL
  - Scenario A/B/C verdict + 根拠
- Scenario A 時は `knowledge-base/wiki/decisions/c1-london-breakout-pre-registration-2026-05-03.md` に LOCK 文書作成 (時間帯分離 + Shadow tier 投入条件)
- catalog §C-1 ステータス更新提案を `knowledge-base/wiki/learning/global-retail-fx-edges-2026-05-03.md` 末尾に追記

# 採用/保留/棄却条件

| Verdict | 条件 |
|---|---|
| **ACCEPT (Scenario A — Shadow promote 候補)** | primary cell が N≥30 / Wilson lo ≥ 50% / PF ≥ 1.10 / OOS/IS PF ≥ 0.80 / Bonf p < 0.05/81 / Sharpe ≥ 0.5 / Kelly > 0 を**全部**満たし、V1 (null bootstrap 95th 超え) + V2 (rsk 相関 < 0.3) + V3 (broker 一致) + V4 (cohort 集中なし) も全 ACCEPT |
| **NEEDS_MORE_EVIDENCE (Scenario B)** | primary cell が B 帯境界 (1-2 軸 fail) または V2 相関 0.3-0.5 / V4 cohort 集中懸念 / V3 broker 差異 ±10-20% |
| **REJECT (Scenario C — academic only)** | primary cell が Wilson lo < 50% or Kelly ≤ 0 or V1 null 95th 未満 or V3 broker 反転 or V4 単一 cohort に PnL 70% 超集中 |

# 受け入れ条件 (Acceptance Criteria)

1. `tools/bt/c1_london_breakout.py` が deterministic seed で再実行可能、CLI 仕様: `python3 tools/bt/c1_london_breakout.py --pair GBP_JPY --start 2014-01-01 --end 2026-04-30 --output knowledge-base/raw/bt-results/c1-london-breakout`
2. 81 cell 全部の統計が JSON artifact に出力される
3. primary cell の Verdict matrix v1 7 軸が全部出力される
4. Validity V1〜V6 が `tools/bt/c1_validity_checks.py` で実行できる
5. `tests/test_c1_london_breakout.py` が pass (Asian range 計算 / breakout 判定 / time gate / Bonferroni / null bootstrap の境界ケース)
6. `knowledge-base/wiki/learning/c1-london-breakout-bt-2026-05-03.md` に Scenario verdict + 根拠が日本語で記載
7. catalog §C-1 ステータス更新案が `global-retail-fx-edges-2026-05-03.md` 末尾に追記
8. すべての artifact に `data_source`, `live_separation="bt_only"`, `pair`, `interval`, `time_window`, `git_sha` が JSON header で記録
9. `pgrep -f app.py` 実行 log が `.ai/runs/<run-dir>/orphan_check.log` に保存

# 検証コマンド

```bash
# orphan check
pgrep -f app.py | tee .ai/runs/<run-dir>/orphan_check.log

# 単体テスト
python3 -m pytest tests/test_c1_london_breakout.py -v

# BT 実行 (deterministic)
python3 tools/bt/c1_london_breakout.py \
  --pair GBP_JPY \
  --start 2014-01-01 \
  --end 2026-04-30 \
  --output knowledge-base/raw/bt-results/c1-london-breakout \
  --seed 20260503

# Validity check
python3 tools/bt/c1_validity_checks.py \
  --bt-result knowledge-base/raw/bt-results/c1-london-breakout.json \
  --rsk-source render_api \
  --broker-cross yfinance \
  --bootstrap-n 1000 \
  --output knowledge-base/raw/bt-results/c1-london-breakout-validity.json

# 再現性確認 (seed 固定で同 hash)
sha256sum knowledge-base/raw/bt-results/c1-london-breakout.json
python3 tools/bt/c1_london_breakout.py --pair GBP_JPY --start 2014-01-01 --end 2026-04-30 --output /tmp/c1-rerun --seed 20260503
sha256sum /tmp/c1-rerun.json  # ↑と一致すること
```

# 禁止事項 (Safety)

- **本番 DB / `oanda_audit` / `live_ng_cells` への書き込み禁止**
- **`.env` / OANDA API key の変更・出力禁止**
- **OANDA endpoint への order 送信禁止** (BT only)
- **既存未コミット変更を破壊しない** (`git status` で事前確認、`modules/demo_trader.py` 等)
- **Tier-master / index.md / tier-master.md の編集禁止** (本タスクは BT のみ、promote は別タスク)
- **rsk_gbpjpy_reversion R3 PR #12 へのコミット禁止** (隣接 PR を触らない)
- **ローカル app.py orphan を kill しない** (調査のみ。Render API を一次ソースで使うこと)
- **報告は必ず日本語**

# Out of scope (本タスクで実施しない)

- Shadow tier への投入 (Scenario A 確定時に別タスク)
- Live promote 判断 (Shadow N≥15 後に別タスク)
- rsk_gbpjpy_reversion R3 修正 (PR #12 で別途進行中)
- 他通貨ペアへの拡張 (W3 後の Wave 4 課題)
- HMM / regime gate 追加 (`feedback_hmm_gate_same_trap` の罠回避、conventional gate 積み上げ禁止)

# Done definition

- 上記 Acceptance Criteria 1-9 すべて満たす
- `.ai/runs/<run-dir>/final.md` に Scenario verdict + 次アクション提案
- task ファイルを `.ai/tasks/done/` に移動 (実装完了後)
