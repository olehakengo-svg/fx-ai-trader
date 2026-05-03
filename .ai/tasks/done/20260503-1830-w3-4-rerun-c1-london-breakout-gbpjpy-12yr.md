---
id: 20260503-1830-w3-4-rerun-c1-london-breakout-gbpjpy-12yr
title: W3-4 RERUN — C-1 London Open Breakout BT (GBPJPY) on 12yr cache (BLOCKED_DATA → Verdict確定)
owner: codex
status: queued
priority: P0
created_at: 2026-05-03T18:30:00+0900
roadmap_gate: Gate 1 (新 alpha 候補 — Shadow 並走で N 蓄積加速)
rule: R1
parent_plan: /Users/jg-n-012/.claude/plans/find-out-way-of-fizzy-patterson.md
parent_task: 20260503-1642-w3-4-c1-london-breakout-gbpjpy-bt (done, BLOCKED_DATA)
data_prep_unblock: 20260503-1715-w3-data-prep-gbpjpy-usdjpy-m5-12y (done, .ai/runs/20260503-1800-w3-data-prep-gbpjpy-m5-12y/final.md)
wave: W3 Tier 2 (parallel 2/3)
---

# Objective

W3-4 親タスクは `data/cache/massive/GBP_JPY_5m.parquet` の 4.09% partial coverage により **BLOCKED_DATA** で保留された (parent run `.ai/runs/20260503-171210-20260503-1642-w3-4-c1-london-breakout-gbpjpy-bt/final.md`)。Claude メイン側で 2026-05-03 18:00-18:25 に Massive Market Data API から GBPJPY M5 12年 (925,109 bars, coverage 106.22% of weekday-only target) を取得済 → 12yr cache が hardcoded path にすでに置かれている。

本タスクは親タスクの BT/validity/test 実装 (`tools/bt/c1_london_breakout.py`, `tools/bt/c1_validity_checks.py`, `tests/test_c1_london_breakout.py` — done で merge 済) を **同じ seed `20260503` で 12yr cache に対して再実行** し、Verdict matrix v1 7 軸 + Validity V1/V4/V5/V6 (V2/V3 は network 制約で部分対応) で **Scenario A/B/C verdict** を出す。

**本タスクは BT のみ。Live promote / Shadow 投入は別タスク (Scenario A 確定時のみ)。**

# Hypothesis

親タスクと同一仮説 (LOCK)。再掲:

- **H1**: GBPJPY M5 12年で、07:00-08:00 UTC の Asian range break エントリーは Verdict matrix v1 の B 帯 (Wilson lo ≥ 50%, PF ≥ 1.10, OOS/IS PF ≥ 0.80, Bonf p < 0.05/m, Sharpe ≥ 0.5, Kelly > 0) を満たす独立 alpha である。
- **H2**: rsk_gbpjpy_reversion との rolling 30d correlation ρ < 0.3 で、戦略 alpha は独立。
- **H3**: 81 sensitivity 試行のうち pre-registered primary `(Asian 7h / M5 close break / range×1.0 exit / range≥median×1.0)` が B 帯を通過し、Bonferroni m=81 で耐性がある。

H1+H3 すべて true (V1/V4 ACCEPT 含む) → **Scenario A (Shadow promote 候補)**
B 帯境界 + Bonf 失格 / V4 cohort 集中 / V2-V3 network blocked → **Scenario B (hold + 再検証)**
H1 不成立 → **Scenario C (catalog §C-1 を academic only 降格)**

# Pre-condition (data_prep manifest verification — 必須)

実行前に `tools/bt/data_prep_manifest.json` を読み、以下が一致することを確認:

| Path | 期待 SHA256 (12) | 期待 n_bars |
|---|---|---|
| `data/cache/massive/GBP_JPY_5m_2014_2026.parquet` | `14d4ec64c99c` | 925,109 |
| `data/cache/massive/GBP_JPY_5m.parquet` (active) | `14d4ec64c99c` | 925,109 |

**SHA256 mismatch / n_bars mismatch → 即 abort + final.md に "BLOCKED_PRECONDITION" 記録**(stale-artifact gate)

# Scope

Codex MAY change:

- `knowledge-base/wiki/learning/c1-london-breakout-bt-2026-05-03.md` — partial verdict を 12yr verdict で **上書き** (旧 BLOCKED_DATA セクションは "Superseded by 12yr rerun on 2026-05-03 19:xx" と注記して残す)
- `knowledge-base/raw/bt-results/c1-london-breakout.{json,md}` — 上書き
- `knowledge-base/raw/bt-results/c1-london-breakout-validity.json` — 上書き
- `.ai/runs/<new-run-dir>/final.md` (new)
- `.ai/runs/<new-run-dir>/orphan_check.log` (new)
- (Scenario A 時のみ) `knowledge-base/wiki/decisions/c1-london-breakout-pre-registration-2026-05-03.md` — pre-registration LOCK 文書

Codex MAY NOT change:

- `tools/bt/c1_london_breakout.py`, `tools/bt/c1_validity_checks.py` — 親タスクで実装済、修正禁止 (再現性のため)
- `tests/test_c1_london_breakout.py` — 修正禁止
- `tools/data_prep/fetch_usdjpy_m5_2014_2026.py` — Claude side で refactor 済、Codex 触らない
- `app.py`, `modules/`, `strategies/` — BT のみ
- `knowledge-base/wiki/index.md`, `knowledge-base/wiki/tier-master.md` — Tier 変更禁止 (本タスクは BT 検証のみ)
- `data/cache/massive/*.parquet`, `tools/bt/price_cache/*.json`, `tools/bt/cot_cache/*.json` — read-only
- `tools/bt/data_prep_manifest.json` — read-only
- Render API 書き込み, 本番 DB, `.env`, OANDA secrets, OANDA endpoint
- `live_ng_cells` SQLite テーブル, `oanda_audit` テーブル
- 既存未コミット変更 (`modules/demo_trader.py`, `knowledge-base/raw/hunt_events/2026-05-02.jsonl`, `knowledge-base/wiki/sessions/2026-05-03-session.md`, `knowledge-base/raw/cell_deepdive/`)

# Required Reading

- `CLAUDE.md` (Rule 1 protocol、KB read rules)
- `knowledge-base/wiki/syntheses/roadmap-v2.1.md` (Gate 1 / Scalp 枝 / Track E)
- 親タスク `.ai/tasks/done/20260503-1642-w3-4-c1-london-breakout-gbpjpy-bt.md` (戦略仕様 LOCK の正本)
- 親 run report `.ai/runs/20260503-171210-20260503-1642-w3-4-c1-london-breakout-gbpjpy-bt/final.md`
- 親 partial verdict `knowledge-base/wiki/learning/c1-london-breakout-bt-2026-05-03.md`
- `tools/bt/data_prep_manifest.json` (12yr cache の SHA256/n_bars)
- `.ai/runs/20260503-1800-w3-data-prep-gbpjpy-m5-12y/final.md` (data prep 完了報告)
- `knowledge-base/wiki/learning/global-retail-fx-edges-2026-05-03.md` §C-1
- `knowledge-base/wiki/analyses/friction-analysis.md` (GBPJPY 摩擦 / spread profile)
- `knowledge-base/wiki/analyses/bt-live-divergence.md`
- `knowledge-base/wiki/lessons/index.md`
- 関連 lesson:
  - `feedback_partial_quant_trap` — N/WR/EV のみで判断不可、PF / Wilson / WF / Bonf / Kelly 必須
  - `feedback_check_orphan_local_app` — 分析前に `pgrep -f app.py`
  - `feedback_live_shadow_separation` — Live PnL 集計時 `is_shadow=0` 分離 (本タスクは BT only だが artifact tag 必須)
  - `feedback_spread_basis_for_mafe` — spread profile は entry_price 基準で差し引く

# 対象データ / Data Separation (厳守)

| 用途 | 出典 | 混入禁止対象 |
|---|---|---|
| BT bars (OHLCV M5) | `data/cache/massive/GBP_JPY_5m.parquet` (12yr, sha256=14d4ec64c99c..., 925,109 bars, 2014-01-02 04:55 UTC → 2026-04-30 23:55 UTC) | Render `oanda_audit`, `is_shadow=0` Live, OANDA fills |
| Asian range / breakout 計算 | BT bars のみ | Live decision history |
| spread profile 差し引き | H-1 audit / `friction-analysis.md` の hour-bucket spread 中央値 (broker realtime spread を使わない) | broker realtime spread |
| rsk_gbpjpy 相関 (V2) | Render `/api/demo/trades` (read-only スナップショット, `is_shadow=1` 含む全件) — **Codex sandbox は DNS blocked のため V2 は SKIP_NETWORK と記録** | ローカル app.py orphan データ |
| broker cross-check (V3) | yfinance / dukascopy 別ソース GBPJPY M5 — **Codex sandbox は DNS blocked のため V3 は SKIP_NETWORK と記録** | 同一 cache (= 確認にならない) |

artifact JSON header 必須項目: `data_source`, `data_sha256` (manifest と一致), `live_separation="bt_only"`, `time_window`, `pair`, `interval`, `git_sha`, `seed=20260503`。

# Statistical Conditions (親タスクと同一 — LOCK)

各 cell および primary cell について以下を全部測定する:

1. **N** (trade count, ≥30 を最低条件)
2. **Wilson 95% lower bound (WR)** (≥ 50% で B 帯)
3. **PF** (Profit Factor, ≥ 1.10 で B 帯)
4. **OOS/IS PF ratio** (Walk-Forward 3 folds, ≥ 0.80)
5. **Bonferroni-corrected p** (m=81, p < 0.05/81 ≈ 6.17e-4)
6. **Sharpe** (annualized, ≥ 0.5)
7. **Kelly fraction** (> 0)

加えて補助指標 (max DD pip&%、avg holding bars、per-cell trade list、spread net PnL)。

# Validity Check (V1/V4/V5/V6 必須、V2/V3 sandbox制約で SKIP_NETWORK)

## V1 — null bootstrap (1000 試行) [必須]
- 各 cell について trade timestamp ランダムシャッフル → null distribution
- ACCEPT: actual PF が 95th percentile 超え

## V2 — rsk_gbpjpy_reversion 相関 [SKIP_NETWORK]
- Codex sandbox DNS blocked → `validity.json` に `"v2_status": "SKIP_NETWORK", "rerun_required_on": "claude_main"` を記録
- claude_main 側で別途 fetch + correlation 計算 (本タスクの後続)

## V3 — broker cross-check [SKIP_NETWORK]
- 同上、`"v3_status": "SKIP_NETWORK"` を記録

## V4 — 時間コホート整合 [必須]
- 親タスク仕様の 7 コホート (pre-Brexit / Brexit Vote / calm / COVID / Truss / 2023-2024 / 2025-2026)
- ACCEPT: 単一コホートに PnL 集中なし (どのコホートも全期間 PnL の 50% 未満)

## V5 — orphan check [必須]
- BT 開始前に `pgrep -f app.py` を実行、log に明記

## V6 — spread profile 補正 [必須]
- entry_price 基準で hour-bucket median spread を差し引いた net PnL を併記

# Decision Procedure (Rule 1 — Slow & Strict)

## Step 0 — Pre-condition gate
1. `tools/bt/data_prep_manifest.json` を読み、`GBP_JPY_5m.parquet` の sha256/n_bars が一致することを確認
2. mismatch → 即 abort、final.md に `BLOCKED_PRECONDITION` 記録
3. `pgrep -f app.py` 実行、orphan log 保存

## Step 1 — 81 cell BT 再実行
```bash
python3 tools/bt/c1_london_breakout.py \
  --pair GBP_JPY \
  --start 2014-01-01 \
  --end 2026-04-30 \
  --output knowledge-base/raw/bt-results/c1-london-breakout \
  --seed 20260503
```

## Step 2 — Validity check (V1/V4/V5/V6 のみ;V2/V3 は SKIP_NETWORK)
```bash
python3 tools/bt/c1_validity_checks.py \
  --bt-result knowledge-base/raw/bt-results/c1-london-breakout.json \
  --output knowledge-base/raw/bt-results/c1-london-breakout-validity.json \
  --bootstrap-n 1000 \
  --orphan-log .ai/runs/<run-dir>/orphan_check.log \
  --skip-v2-network --skip-v3-network
```
- もし `--skip-v2-network` / `--skip-v3-network` フラグが未実装なら、validity スクリプト内の対応セクションを **編集禁止**。代わりに stderr の SKIP_NETWORK ログを final.md に転記し、validity.json に手動で `"v2_status": "SKIP_NETWORK"`, `"v3_status": "SKIP_NETWORK"` をマージする (ファイル末尾のみ追記、本体 schema は触らない)。

## Step 3 — Verdict 確定 + レポート
- `c1-london-breakout-bt-2026-05-03.md` の partial-verdict セクションを "Superseded 2026-05-03 19:xx — 12yr rerun" 注記し、新しい 12yr verdict を末尾に追加
- 81-cell sensitivity grid 表 (cell ごとに N/WR/Wilson/PF/OOS-IS/Bonf/Sharpe/Kelly)
- primary cell 詳細
- V1/V4/V5/V6 結果 + V2/V3 SKIP_NETWORK 注記
- cohort 別 PF/WR 表
- spread net PnL
- Scenario A/B/C verdict + 根拠

## Step 4 — (Scenario A 時のみ) pre-registration LOCK
- `knowledge-base/wiki/decisions/c1-london-breakout-pre-registration-2026-05-03.md` を作成
- 時間帯分離 (rsk_gbpjpy = 全時間帯, c1-london-breakout = 07-17 UTC のみ)
- Shadow tier 投入条件 (V2 ρ<0.3 確認後 promote、V2 未確認なら HOLD)

# 採用/保留/棄却条件

| Verdict | 条件 |
|---|---|
| **ACCEPT (Scenario A — Shadow promote 候補)** | primary cell が N≥30 / Wilson lo ≥ 50% / PF ≥ 1.10 / OOS/IS PF ≥ 0.80 / Bonf p < 0.05/81 / Sharpe ≥ 0.5 / Kelly > 0 を**全部**満たし、V1 (null bootstrap 95th 超え) + V4 (cohort 集中なし) + V5 (orphan log clean) + V6 (spread net PnL ≥ 0) も全 ACCEPT。**V2/V3 は SKIP_NETWORK だが Scenario A 認定可** (pre-registration LOCK 文書に "V2/V3 confirmation pending on claude_main" と明記し、Shadow promote は V2 ρ<0.3 確認後の別タスク) |
| **NEEDS_MORE_EVIDENCE (Scenario B)** | primary cell が B 帯境界 (1-2 軸 fail) または V4 cohort 集中懸念 / V1 null bootstrap 90-95th 帯 |
| **REJECT (Scenario C — academic only)** | primary cell が Wilson lo < 50% or Kelly ≤ 0 or V1 null 95th 未満 or V4 単一 cohort に PnL 70% 超集中 or V5 orphan kill 失敗 |

# 受け入れ条件 (Acceptance Criteria)

1. `tools/bt/data_prep_manifest.json` の sha256/n_bars 一致確認 log が final.md に記載
2. 81 cell 全部の統計が JSON artifact に出力される (`live_separation="bt_only"`, `data_sha256` header)
3. primary cell の Verdict matrix v1 7 軸が全部出力される (BLOCKED_DATA ではなく実数値)
4. Validity V1/V4/V5/V6 が ACCEPT/HOLD/REJECT で出力される (V2/V3 は SKIP_NETWORK)
5. `c1-london-breakout-bt-2026-05-03.md` に Scenario verdict + 根拠が日本語で記載 (旧 BLOCKED_DATA セクションは "Superseded" 注記で残す)
6. Scenario A 時のみ `knowledge-base/wiki/decisions/c1-london-breakout-pre-registration-2026-05-03.md` 作成
7. すべての artifact に `data_source`, `data_sha256`, `live_separation="bt_only"`, `pair`, `interval`, `time_window`, `git_sha`, `seed=20260503` が JSON header で記録
8. 再現性: `seed=20260503` で再実行した時に JSON sha256 が一致 (Codex 内で 2回実行して比較)
9. `pgrep -f app.py` 実行 log が `.ai/runs/<run-dir>/orphan_check.log` に保存
10. final.md に Scenario verdict + 次アクション (Scenario A → V2/V3 補完タスク作成提案 / Scenario B → 追加分析提案 / Scenario C → catalog §C-1 降格提案)

# 検証コマンド

```bash
# Step 0 — preconditions
pgrep -f app.py | tee .ai/runs/<run-dir>/orphan_check.log
python3 -c "
import json
m = json.load(open('tools/bt/data_prep_manifest.json'))
gbp = next(a for a in m['artifacts'] if a.get('path')=='data/cache/massive/GBP_JPY_5m.parquet')
assert gbp['n_bars'] == 925109, f'n_bars mismatch: {gbp[\"n_bars\"]}'
assert gbp['sha256'].startswith('14d4ec64c99c'), f'sha256 mismatch: {gbp[\"sha256\"][:12]}'
print(f'OK: GBP_JPY_5m.parquet sha256={gbp[\"sha256\"][:12]} n_bars={gbp[\"n_bars\"]:,}')
"

# Step 1 — BT (12yr)
python3 tools/bt/c1_london_breakout.py \
  --pair GBP_JPY \
  --start 2014-01-01 \
  --end 2026-04-30 \
  --output knowledge-base/raw/bt-results/c1-london-breakout \
  --seed 20260503

# Step 2 — Validity (V1/V4/V5/V6 必須、V2/V3 SKIP_NETWORK)
python3 tools/bt/c1_validity_checks.py \
  --bt-result knowledge-base/raw/bt-results/c1-london-breakout.json \
  --output knowledge-base/raw/bt-results/c1-london-breakout-validity.json \
  --bootstrap-n 1000 \
  --orphan-log .ai/runs/<run-dir>/orphan_check.log

# 単体テスト (親タスクの実装が壊れていないこと)
python3 -m pytest tests/test_c1_london_breakout.py -v

# 再現性確認 (seed 固定で同 hash)
sha256sum knowledge-base/raw/bt-results/c1-london-breakout.json
python3 tools/bt/c1_london_breakout.py --pair GBP_JPY --start 2014-01-01 --end 2026-04-30 --output /tmp/c1-rerun --seed 20260503
sha256sum /tmp/c1-rerun.json  # ↑と一致すること
```

# 禁止事項 (Safety)

- **本番 DB / `oanda_audit` / `live_ng_cells` への書き込み禁止**
- **`.env` / OANDA API key / `MASSIVE_API_KEY` の変更・出力禁止**
- **OANDA endpoint への order 送信禁止** (BT only)
- **Massive Market Data API への新規 fetch 禁止** (Codex sandbox は DNS blocked、claude_main 側で完了済)
- **既存未コミット変更を破壊しない** (`git status` で事前確認)
- **Tier-master / index.md / tier-master.md の編集禁止**
- **`tools/bt/c1_london_breakout.py`, `tools/bt/c1_validity_checks.py`, `tests/test_c1_london_breakout.py` の編集禁止** (親タスクで実装済、再現性のため)
- **`data/cache/massive/*.parquet` の上書き禁止** (read-only として扱う)
- **`tools/bt/data_prep_manifest.json` の編集禁止** (read-only)
- **rsk_gbpjpy_reversion R3 PR #12 へのコミット禁止**
- **ローカル app.py orphan を kill しない** (調査のみ)
- **報告は必ず日本語**

# Out of scope

- Shadow tier への投入 (Scenario A 確定 + V2/V3 補完後に別タスク)
- Live promote 判断 (Shadow N≥15 後に別タスク)
- V2 (rsk_gbpjpy 相関) / V3 (broker cross-check) — claude_main 側で別タスク (network 必須)
- rsk_gbpjpy_reversion R3 修正 (PR #12 で別途進行中)
- 他通貨ペア / 他 TF への拡張 (W3-3 USDJPY, W3-5 S3 で別タスク)
- HMM / regime gate 追加 (`feedback_hmm_gate_same_trap` の罠回避)
- Massive API 再 fetch (claude_main 完了済、cache 利用)

# Roadmap 寄与

Gate 1 = 新 alpha 候補による N-acceleration / DD 縮小経路。本タスクで Scenario A 確定 → 後続 V2/V3 補完 → Shadow tier 投入 (時間帯分離: 07-17 UTC) → Live N≥15 + Wilson lo ≥ 60% で Live promote 検討。月利 100% ロードマップに対し:
- Scenario A 確定確率 (12yr で再評価): partial では未達だったが 12yr で N が増えるため confidence band 縮小 → 確定確率 +10-15pp 上昇予想
- 確定時の月間寄与推定: 50-150 pip (small 1 trade/day × 60% pass × 7 pip net)
- データ汚染リスク: Massive feed の Polygon source は institutional 系で品質高 (broker cross-check V3 は SKIP_NETWORK だが 12yr coverage で sample bias ほぼ排除)

# Done definition

- 上記 Acceptance Criteria 1-10 すべて満たす
- `.ai/runs/<run-dir>/final.md` に Scenario verdict + 次アクション提案 (V2/V3 補完 or Scenario B/C 場合の対処)
- task ファイルを `.ai/tasks/done/` に移動 (実装完了後)
