---
id: 20260503-1721-w3-4-data-gbpjpy-m5-12yr-backfill
title: W3-4-data — GBPJPY M5 12-year backfill (HistData/Dukascopy) で c1_london_breakout BT verdict を unblock
owner: codex
status: queued
priority: P0
created_at: 2026-05-03T17:21:00+0900
roadmap_gate: Gate 1 (W3-4 verdict unblocker)
rule: R3
parent_task: 20260503-1642-w3-4-c1-london-breakout-gbpjpy-bt
parent_run: .ai/runs/20260503-170452-20260503-1642-w3-4-c1-london-breakout-gbpjpy-bt
wave: W3 Tier 2 unblocker
---

# Objective

W3-4 (`20260503-1642-w3-4-c1-london-breakout-gbpjpy-bt`) は実装完了したが、**12 年 GBPJPY M5 データが parquet cache に存在しない** (現状 184/4503 日 = 4.09% カバレッジ) ため Scenario A/B/C verdict が出せず BLOCKED_DATA 状態。本タスクで:

1. HistData.com (一次) または Dukascopy (二次) から GBPJPY M1 12年 (2014-01-01 〜 2026-04-30) を取得
2. M1 → M5 にリサンプル
3. `data/cache/massive/GBP_JPY_5m.parquet` の Massive API 制約 (180-day max) を回避するため別 cache パス `data/cache/extended/GBP_JPY_5m_long.parquet` を新設
4. `tools/bt/c1_london_breakout.py` に long-history cache を auto-detect させる小改修
5. 同 seed で BT 再実行 → Scenario A/B/C 確定
6. (副次) `tools/render_trades_snapshot.py` をユーザー側で先に走らせた **rsk_gbpjpy_reversion 取引時系列 SQLite snapshot** を読み、V2 相関を確定

**本タスクは新戦略導入ではなく、W3-4 verdict 確定のためのデータ pipeline R3 補修。Tier 変更 / Live promote は依然禁止。**

# Hypothesis

- **H1**: HistData.com の M1 GBPJPY 12 年 (2014-2026 ZIP 月次配布) を Codex sandbox から HTTP で取得可能。
- **H2**: M1 → M5 リサンプル + DST/UTC 正規化で W3-4 BT runner の入力契約 (`DatetimeIndex UTC`, columns `Open/High/Low/Close/Volume`) と一致する parquet が作成可能。
- **H3**: 12 年フルデータでの primary cell 統計は W3-4 partial 統計 (4% カバレッジ N=29 / WR=44.83% / null bootstrap fail) と乖離する可能性あり。Bonferroni m=81 通過すれば Scenario A、null bootstrap 95th 未満が継続すれば Scenario C。

H1+H2 成立 → Scenario A/B/C のいずれか確定 (どれでも前進)。
H1 失敗 (HistData / Dukascopy 両方とも sandbox から到達不可) → 取得方法を `.ai/tasks/queue/` に diagnostic として記録し human-side acquisition を要求。

# Context

- 親タスク: `.ai/tasks/queue/20260503-1642-w3-4-c1-london-breakout-gbpjpy-bt.md`
- 親 run: `.ai/runs/20260503-170452-20260503-1642-w3-4-c1-london-breakout-gbpjpy-bt/final.md` (BLOCKED_DATA)
- 既存 W3-4 partial 統計 (4% カバレッジ): N=29 / WR=44.83% / Wilson lo=28.41% / PF=1.110 / OOS 0.00 / Bonf fail / Sharpe 0.67 / Kelly 0.0446 / null actual 1.11 vs null p95 2.30 (signal 不在のサイン)
- `tools/bt_data_cache.py:53` — Massive API の 5m max_days=180 が pre-existing 制約。これは API 側制約で本タスクでは触らない (副作用回避)
- `tools/render_trades_snapshot.py` — Render API → SQLite snapshot ツール。Codex sandbox で DNS 失敗するなら **Claude 側 (本セッション) で事前実行** し、生成 SQLite を Codex に渡す手順
- 既存 cache:
  - `data/cache/massive/GBP_JPY_5m.parquet` (36523 行, 2025-10-14 〜 2026-04-15, Massive API)
- 内部 KB:
  - `feedback_check_orphan_local_app` — Live 相関 source は **必ず Render API 一次ソース**。Local app.py orphan の sqlite を読むのは禁止
  - `feedback_live_shadow_separation` — rsk 相関は `is_shadow=0` Live のみで取る
  - `feedback_label_empirical_audit` — リサンプル正当性は **コード演繹だけでなく M1 cross-check で実測** (1 サンプル日について M1 raw vs M5 resampled の OHLC 整合確認)
  - `feedback_partial_quant_trap` — partial 統計の primary cell が W3-4 で B 帯失格 + null bootstrap 不在を示している。フルデータでも C 落ちる可能性が高い、verdict は「データ拡張で改善 / 維持 / 悪化」を等確率扱いで進める
- 公開データソース (sandbox HTTP 到達想定):
  - HistData.com 月次 ZIP: `https://www.histdata.com/download-free-forex-historical-data/?/ascii/1-minute-bar-quotes/gbpjpy/{year}/{month}` (★ JS-protected の可能性、直 ZIP URL は `https://www.histdata.com/get.php?fname=DAT_ASCII_GBPJPY_M1_{year}{month}.zip`)
  - Dukascopy CSV: `https://www.dukascopy.com/swiss/english/marketwatch/historical/`
  - alpha-vantage / stooq (M5 12年は不可)

# Scope

Codex MAY change:

- `tools/data/fetch_gbpjpy_m5_long_history.py` (new) — HistData / Dukascopy から M1 ZIP を取得し M5 にリサンプル、parquet 出力
- `data/cache/extended/.gitkeep` (new) — long-history cache 用ディレクトリ (gitignored だが構造保持)
- `.gitignore` に `data/cache/extended/*.parquet` を追加
- `tools/bt/c1_london_breakout.py` (修正) — long-history cache が存在すれば優先利用、無ければ既存の Massive cache へフォールバック (signal/runner 本体は変更禁止)
- `tests/test_fetch_gbpjpy_m5_long_history.py` (new) — リサンプル正当性テスト (M1 cross-check, DST/UTC, 欠損処理)
- `tests/test_c1_long_history_integration.py` (new) — long-history cache 経由で BT runner が同 seed で実行できる integration テスト (small window で OK)
- `knowledge-base/raw/bt-results/c1-london-breakout.json/md` (上書き) — 12 年データでの再実行結果
- `knowledge-base/raw/bt-results/c1-london-breakout-validity.json` (上書き) — V1〜V6 再実行結果 (V2 は Render snapshot SQLite 入力)
- `knowledge-base/wiki/learning/c1-london-breakout-bt-2026-05-03.md` (修正) — Scenario A/B/C 確定 verdict + 12年カバレッジ記載
- `.ai/runs/<new-run-dir>/final.md` (new)
- (Scenario A 時のみ) `knowledge-base/wiki/decisions/c1-london-breakout-pre-registration-2026-05-03.md` (new) — Shadow tier pre-reg LOCK

Codex MAY NOT change:

- `app.py`, `modules/`, `strategies/` — 本番 signal / runner 領域
- `tools/bt_data_cache.py` — Massive API 制約は別問題 (副作用回避)
- `tools/render_trades_snapshot.py` — 本タスクではこのツールを **読み取り使用** するのみ
- `tools/bt/c1_validity_checks.py` — V1〜V6 framework は親タスクで完成済み、本タスクは入力データのみ更新
- `knowledge-base/wiki/index.md`, `knowledge-base/wiki/tier-master.md` — Tier 変更禁止
- 本番 DB / `live_ng_cells` / `oanda_audit` / `.env` / OANDA secrets / OANDA endpoint — 全部禁止
- 既存未コミット変更 (`modules/demo_trader.py`, `knowledge-base/raw/hunt_events/2026-05-02.jsonl`, `knowledge-base/wiki/sessions/2026-05-03-session.md`, `knowledge-base/raw/cell_deepdive/`)
- ユーザーが事前生成して渡す Render snapshot SQLite は **read-only**

# Required Reading

- `CLAUDE.md` (Rule 3 protocol — 構造補修)
- 親タスク `20260503-1642-w3-4-c1-london-breakout-gbpjpy-bt.md` 全体
- 親 run の `final.md` (BLOCKED_DATA 詳細)
- `tools/bt_data_cache.py` (cache 命名規約)
- `tools/render_trades_snapshot.py` (Render snapshot のスキーマ)
- `tools/bt/c1_london_breakout.py` (cache 読込パスの分岐点を確認)
- `knowledge-base/wiki/learning/c1-london-breakout-bt-2026-05-03.md` (現状 partial レポート)
- `knowledge-base/wiki/learning/h1-spread-time-audit-2026-05-03.md` (GBPJPY hour profile, spread 補正用)

# 対象データ / Data Separation (厳守)

| 用途 | 出典 | 混入禁止対象 |
|---|---|---|
| 12 年 M5 OHLCV | HistData (一次) または Dukascopy (二次) | OANDA Live, Render `oanda_audit`, `is_shadow=0` Live trades |
| リサンプル sanity check | 同じ HistData M1 raw を 1 サンプル日サブセット | 別 broker のデータ (cross-check には可だが sanity には不可) |
| V2 相関 (rsk_gbpjpy) | **ユーザー側で事前生成済み** Render snapshot SQLite (`knowledge-base/raw/snapshots/render-demo-trades-20260503.db`, 4872 trades, rsk_gbpjpy_reversion=85件) — **rsk は現状 Shadow-only 戦略 (is_shadow=1)** なので `entry_type='rsk_gbpjpy_reversion'` で全件抽出する。`feedback_live_shadow_separation` の "Live PnL 集計時に Shadow 混入禁止" は本タスクの相関検査 (broker-isolated counterfactual) には該当しない。artifact に `rsk_source_is_shadow="1 (rsk is Shadow-tier as of 2026-05-03)"` を明記 | local `demo_trades.db` (orphan 汚染リスク), Live-tier 戦略の is_shadow=1 (それは混入禁止) |
| broker cross-check (V3) | Dukascopy (HistData の対) | HistData 自身 (循環) |
| spread profile 補正 | `knowledge-base/wiki/learning/h1-spread-time-audit-2026-05-03.md` の hour-bucket median | broker realtime spread |

artifact JSON header に `data_source="histdata|dukascopy"`, `live_separation="bt_only"`, `coverage_days`, `coverage_pct`, `git_sha` を必ず記録。

# Statistical Conditions

本タスクは R3 (データ pipeline 補修) だが、最終 deliverable は親 R1 タスクの verdict なので Verdict matrix v1 7 軸を再算出する:

primary cell `(7h Asian / M5 close / range×1.0 / median×1.0)` で:

| 指標 | ACCEPT (Scenario A) | NEEDS_MORE (Scenario B) | REJECT (Scenario C) |
|---|---|---|---|
| N | ≥30 | 30-50 境界 | <30 (12 年 + filter pass で <30 なら戦略破綻) |
| Wilson lo (WR) | ≥50% | 45-50% | <45% |
| PF | ≥1.10 | 1.00-1.10 | <1.00 |
| OOS/IS PF (WF 3 folds) | ≥0.80 | 0.50-0.80 | <0.50 |
| Bonferroni p (m=81) | <6.17e-4 | <0.05 (raw) | ≥0.05 (raw) |
| Sharpe | ≥0.5 | 0.0-0.5 | <0.0 |
| Kelly | >0 | 0 | <0 |
| V1 null bootstrap | actual PF > null p95 | actual ≈ null p90-p95 | actual < null p90 |
| V2 rsk 相関 | < 0.3 | 0.3-0.5 | ≥ 0.5 |
| V3 broker cross | sign + WR/PF ±10% 一致 | ±10-20% | sign 反転 or ±20%超 |
| V4 cohort 集中 | どのコホートも全 PnL の 50% 未満 | 単一コホート 50-70% | 単一コホート >70% |

採用判定:
- **ACCEPT**: 主軸 7 軸 + V1+V2+V3+V4 全部 ACCEPT 列
- **NEEDS_MORE_EVIDENCE**: 1-3 軸 NEEDS_MORE
- **REJECT**: 1 軸でも REJECT 列

# Roadmap 寄与

Gate 1 = 新 alpha 候補 / DD 縮小経路。本タスクで:
- Scenario A → Shadow tier 投入 (rsk と時間帯分離) → 月間 +50-150 pip 寄与候補
- Scenario B → catalog §C-1 を hold、別 catalog 候補へ予算移動
- Scenario C → catalog §C-1 academic only 降格、W3 Tier 2 残り 2 戦略 (W3-3 Connors-Raschke, W3-5 S3 Pair-Pool) に集中
**どの結果でも Gate 1 議論を前進させる**。

# Decision Procedure (Rule 3 + Rule 1 verdict)

## Step 1 — Pre-flight (Codex sandbox network probe)

```bash
# HistData 直 ZIP URL の HEAD で 200 を確認
curl -sIL "https://www.histdata.com/get.php?fname=DAT_ASCII_GBPJPY_M1_201401.zip" | head -1

# Dukascopy index reachability
curl -sIL "https://datafeed.dukascopy.com/datafeed/GBPJPY/2014/00/00/00h_ticks.bi5" | head -1
```

両方 fail → diagnostic タスクを `.ai/tasks/queue/20260503-XXXX-w3-4-data-acquisition-human.md` に書き、本タスクは BLOCKED_NETWORK で停止。
1 つでも 200 → 進行。

## Step 2 — Data acquisition

`tools/data/fetch_gbpjpy_m5_long_history.py` を実装:

1. HistData 月次 ZIP を 2014-01 〜 2026-04 全 148 ヶ月ぶん取得 (rate-limit に配慮、sleep 1s 間隔)
2. ZIP 解凍 → CSV パース (HistData 形式: `YYYYMMDD HHMMSS;O;H;L;C;V`)
3. UTC 正規化 (HistData は EST、DST 込み)
4. M1 → M5 リサンプル (`pandas.resample('5min').agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'})`)
5. 平日のみ (土日除外、年末年始 12/24-1/3 除外)
6. BoJ 介入日除外 (親タスクの除外日リスト互換)
7. parquet 保存 → `data/cache/extended/GBP_JPY_5m_long.parquet`

CLI:
```
python3 tools/data/fetch_gbpjpy_m5_long_history.py \
  --source histdata \
  --start 2014-01 \
  --end 2026-04 \
  --output data/cache/extended/GBP_JPY_5m_long.parquet \
  --rate-limit 1.0
```

Determinism: 同 input 月 ZIP に対し同 sha256 parquet を出力 (sort 順 + UTC 統一)。

## Step 3 — Resample sanity check (`feedback_label_empirical_audit`)

`tests/test_fetch_gbpjpy_m5_long_history.py`:
- 1 サンプル日 (例: 2018-06-15) について HistData M1 raw を直接読み、5 本ずつグループ化した OHLC が parquet M5 と完全一致
- DST 切替日 (2017-03-12, 2017-11-05 等) で時刻ズレなし
- 平日抜けなし、土日除外正しい
- カバレッジ ≥ 90% (期待 12yr × 5 weekday × 24h × 12 (M5/h) = 374,400 bar 程度、欠損 10% 以内)

## Step 4 — c1_london_breakout.py 統合

`tools/bt/c1_london_breakout.py` の cache 読込部を:
```python
LONG_CACHE = Path("data/cache/extended/GBP_JPY_5m_long.parquet")
DEFAULT_CACHE = Path("data/cache/massive/GBP_JPY_5m.parquet")
cache = LONG_CACHE if LONG_CACHE.exists() else DEFAULT_CACHE
```
に変更。signal / runner 本体は触らない。

## Step 5 — Render snapshot 入力 (V2 相関)

ユーザー (Claude 主セッション) が事前に下記を実行し、SQLite を `knowledge-base/raw/snapshots/render-demo-trades-20260503.db` に保存しておく:

```bash
python3 tools/render_trades_snapshot.py \
  --output knowledge-base/raw/snapshots/render-demo-trades-20260503.db \
  --limit 10000
```

Codex 側は `tools/bt/c1_validity_checks.py --rsk-source render_snapshot --rsk-snapshot knowledge-base/raw/snapshots/render-demo-trades-20260503.db` で読み込む形に小改修 (オプション追加のみ、既存ロジック保持)。**rsk_gbpjpy_reversion は現状 Shadow-only 戦略のため `entry_type='rsk_gbpjpy_reversion'` で is_shadow フィルタ無し**で抽出する (snapshot 確認済み: 85 件すべて is_shadow=1)。

Snapshot 不在 → V2 を BLOCKED として記録、verdict は V1+V3+V4 で確定 (Scenario A は V2 必須、A 候補なら V2 を後付け要求)。
**Snapshot 既存**: `knowledge-base/raw/snapshots/render-demo-trades-20260503.db` (2026-05-03 17:26 取得済、4872 件、rsk_gbpjpy_reversion=85 件)。Codex はこれを read-only で利用すること。

## Step 6 — BT 再実行 + verdict

```bash
python3 tools/bt/c1_london_breakout.py \
  --pair GBP_JPY --start 2014-01-01 --end 2026-04-30 \
  --output knowledge-base/raw/bt-results/c1-london-breakout \
  --seed 20260503

python3 tools/bt/c1_validity_checks.py \
  --bt-result knowledge-base/raw/bt-results/c1-london-breakout.json \
  --rsk-source render_snapshot \
  --rsk-snapshot knowledge-base/raw/snapshots/render-demo-trades-20260503.db \
  --broker-cross dukascopy \
  --bootstrap-n 1000 \
  --output knowledge-base/raw/bt-results/c1-london-breakout-validity.json
```

`knowledge-base/wiki/learning/c1-london-breakout-bt-2026-05-03.md` に Scenario A/B/C 確定 verdict + 81-cell 表 + V1〜V6 結果 + cohort 別 PF/WR + spread 補正前後 PnL を記載。

# 受け入れ条件 (Acceptance Criteria)

1. `tools/data/fetch_gbpjpy_m5_long_history.py` が deterministic で同 input 同 hash 出力
2. `data/cache/extended/GBP_JPY_5m_long.parquet` のカバレッジ ≥ 90% (期待 374k bar の 90% 以上)
3. リサンプル sanity check `tests/test_fetch_gbpjpy_m5_long_history.py` 全 pass
4. `tests/test_c1_long_history_integration.py` で long cache 経由の BT が動く
5. 12 年再実行で primary cell の N/WR/Wilson/PF/OOS/Bonf/Sharpe/Kelly が出力 (artifact JSON header に `coverage_pct ≥ 90` を記録)
6. V1 null bootstrap (1000 試行) / V3 broker cross / V4 cohort 整合 / V5 orphan log / V6 spread 補正 全実施
7. V2 rsk 相関は Render snapshot 存在時に実施、不在時は BLOCKED として明示記録
8. `knowledge-base/wiki/learning/c1-london-breakout-bt-2026-05-03.md` に Scenario A/B/C verdict + 根拠が **日本語で**明示
9. (Scenario A 時のみ) pre-registration LOCK 文書を `knowledge-base/wiki/decisions/c1-london-breakout-pre-registration-2026-05-03.md` に作成 (時間帯分離 07-17 UTC + Shadow tier 条件)
10. 全 artifact に `data_source` / `live_separation="bt_only"` / `coverage_pct` / `git_sha` を JSON header 記録
11. `pgrep -f app.py` 不能ログを `.ai/runs/<run-dir>/orphan_check.log` に保持 (sysmon 制約は親 run と同様、生 log 残す)

# 検証コマンド

```bash
# Pre-flight
curl -sIL "https://www.histdata.com/get.php?fname=DAT_ASCII_GBPJPY_M1_201401.zip" | head -1

# データ取得
python3 tools/data/fetch_gbpjpy_m5_long_history.py \
  --source histdata --start 2014-01 --end 2026-04 \
  --output data/cache/extended/GBP_JPY_5m_long.parquet --rate-limit 1.0

# テスト
python3 -m pytest tests/test_fetch_gbpjpy_m5_long_history.py tests/test_c1_long_history_integration.py -v

# BT 再実行 (deterministic)
python3 tools/bt/c1_london_breakout.py --pair GBP_JPY --start 2014-01-01 --end 2026-04-30 \
  --output knowledge-base/raw/bt-results/c1-london-breakout --seed 20260503

# Validity
python3 tools/bt/c1_validity_checks.py \
  --bt-result knowledge-base/raw/bt-results/c1-london-breakout.json \
  --rsk-source render_snapshot \
  --rsk-snapshot knowledge-base/raw/snapshots/render-demo-trades-20260503.db \
  --broker-cross dukascopy --bootstrap-n 1000 \
  --output knowledge-base/raw/bt-results/c1-london-breakout-validity.json

# Determinism
sha256sum data/cache/extended/GBP_JPY_5m_long.parquet
sha256sum knowledge-base/raw/bt-results/c1-london-breakout.json
```

# 禁止事項 (Safety)

- **本番 DB / `oanda_audit` / `live_ng_cells` への書き込み禁止**
- **`.env` / OANDA API key の変更・出力禁止**
- **OANDA endpoint への order 送信禁止**
- **既存未コミット変更を破壊しない** (`git status` 事前確認)
- **Tier-master / index.md / tier-master.md の編集禁止**
- **`tools/bt_data_cache.py` / `tools/render_trades_snapshot.py` を改変しない** (read-only)
- **HistData / Dukascopy への大量並列リクエスト禁止** (rate-limit 1.0s 以上)
- **取得した HistData ZIP / 中間 CSV を repo にコミットしない** (`.gitignore` 必須)
- **ローカル app.py orphan を kill しない**
- **報告は必ず日本語**

# Out of scope

- W3-3 (S4 Connors-Raschke) / W3-5 (S3 Pair-Pool) / A2 / A2-fix への波及
- Scenario A 確定後の Shadow tier 投入 (別タスク)
- HistData / Dukascopy の認証付き API 利用 (無料公開 ZIP のみ)
- 他通貨ペア (本タスクは GBPJPY のみ)
- M1 / M15 / H1 などの他 TF (本タスクは M5 のみ)

# Done definition

- Acceptance Criteria 1-11 すべて満たす
- `.ai/runs/<run-dir>/final.md` に Scenario A/B/C verdict + 次アクション
- 親タスク `20260503-1642-w3-4-c1-london-breakout-gbpjpy-bt.md` を `.ai/tasks/done/` に移動
- 本タスクを `.ai/tasks/done/` に移動
