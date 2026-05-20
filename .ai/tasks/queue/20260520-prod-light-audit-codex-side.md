---
id: 20260520-prod-light-audit-codex-side
title: 本番ライト監査 — fx-ai-trader 直近7日 + 主要本番モジュール (Codex 側)
status: queued
priority: P1
rule: audit
gate: N/A
created: 2026-05-20
owner: codex-cloud
type: read-only-audit
estimated_minutes: 60
---

# 本番ライト監査 — fx-ai-trader 直近7日 + 主要本番モジュール (Codex 側)

## 背景

ユーザー指示で **Claude と Codex の独立並列監査** を実施中。あなたは Codex 側。Claude は同じチェックリストで静的解析を別途並走している。

**役割分担**: Codex は DB 実測・実コードの実行確認・E2E に強い側を担当。両者の結果は後で diff して突き合わせる。Claude が出さない実測 evidence (SQL 結果、pytest 実行ログ、curl/HTTP 応答) を主軸に。

## 共通ライト 8 軸チェックリスト

### 1. 直近 commit リスク
以下 3 commit の副作用・後退リスク:
- `a7b18453` fix(daytrade): LIVE_PROMOTE_LOSERS side-channel for prod 0-fire bug [rule:R3]
- `a94bf2b7` data(bt): phase1b daily re-run 2026-05-20 (102d window, verdict=NULL) — **12/14 pairs skipped: datetime64 UTC tz mismatch (ms vs ns)**
- `104c635e` Fix demo_trader py39 annotations guard

### 2. 未コミット変更の整合性
以下の現状 working tree dirty を確認 (本タスク push 時は stash されている前提、`git stash show -p stash@{0}` で参照可):
- `modules/demo_db.py`
- `modules/oanda_bridge.py`
- `AGENTS.md`
- 新規 test: `tests/test_oanda_strategy_nearest_sent_resolution.py`
- 新規 test: `tests/test_pyr_attribution.py`
- 新規 tool: `tools/backfill_oanda_strategy_2026_05_19.py`

### 3. 本番 Gate 整合
- **H1 Gate** (30/0.40/0.0 grandfather 13戦略, `project_w3_1_h1_gate_done`)
- **R2 15-cell lock** (SUPERSEDED 2026-05-11 a29a36b volume emergency 後)
- **R3 rsk per-bar dedup pending** (`project_rsk_gbpjpy_bar_close_gate_pending` で 76件 runaway / -813.7p)
- **Shadow ramp** の重複・矛盾・無効化バイパス

### 4. Shadow/Live 分離 ⚠️ memory feedback で景色反転前科あり
KPI 集計・demote/promote 判定・watchdog で `is_shadow=0` フィルタが必ずかかっているか。**SQLite DB 実測クエリで確認**。

### 5. 既知バグの未修正残り
- `/api/oanda/stats` **range 無視バグ** (2026-05-18, today/7d/30d/all 全て total=748 固定)
- rsk per-bar dedup
を実 API or テストで再現確認

### 6. 設定/secret/env 整合
- `.env*` リーク有無 (git tracked にないか)
- Render env と本番コードの不一致
- Price-Shock Phase B-1 (`35961351` / `458392d8`) で導入された **frozenset 強制 shadow 化** が実 DB で徹底されているか (oanda_audit クエリで `is_shadow` 列の実数値確認)

### 7. テスト健全性
- pre-commit 10件 pre-existing 失敗の現リスト
- 新規 test の実 pass 結果
- CI で `--no-verify` バイパス可能になっていないか

### 8. アーキ整合 (memory feedback 準拠)
- **Shadow-first 原則** (BT 軽量 sanity・Shadow が真 estimator) との乖離
- **MASSIVE BT 原則** (`data/cache/massive/*.parquet` 必須, Yahoo 60d 制限あり) との乖離
- **Codex mock-only 罠** の混入
- **MA トレンドフィルタが MR を破壊する罠** の再発

## Codex 側に特に期待すること (静的解析では詰められない部分)

1. **SQLite DB 実クエリ** — テーブル定義は `.schema <table>` で必ず実取得してから書く (schema ハルシネーション罠回避):
   - `is_shadow` 列の分布 (`SELECT is_shadow, COUNT(*) FROM oanda_audit GROUP BY is_shadow`)
   - 最新 30 件 audit の shadow フラグ
   - KPI 集計が `is_shadow=0` で絞っているか (`/api/oanda/stats` 実装と SQL を突き合わせ)
2. **新規 test 2 件** を `pytest -xvs` で実行し pass/fail 報告:
   - `tests/test_oanda_strategy_nearest_sent_resolution.py`
   - `tests/test_pyr_attribution.py`
3. **pre-commit** を `--all-files` で空走させ、現状 failing test の具体リスト取得
4. **`/api/oanda/stats?range=today|7d|30d|all`** を実 hit (or 該当ハンドラ unit test) で range 無視を実証 (今日/7d/30d/all で `total` が同じ値になることを SQL 結果で示す)
5. **`data/cache/massive/*.parquet`** の存在と最新更新日 (`ls -la`)、BT で実際に使われている経路を grep で確認 (Yahoo フォールバックが残っていないか)
6. **Phase 1b cron 結果** (`.ai/tasks/done/` の 2026-05-20 final.md) を読み datetime tz fix の必要性確認
7. **`oanda_audit` の Price-Shock Phase B-1 戦略行**: frozenset 強制 shadow 化が `is_shadow=1` で記録されているか実 SQL で確認

## 出力形式 (W4-EDA 形式準拠)

final.md は `.ai/tasks/done/20260520-prod-light-audit-codex-side.md` に **Result** section を追記する形で:

各軸につき:
- **Verdict**: 🟢OK / 🟡Concern / 🟠High / 🔴Critical / ⚫Blocker
- **Evidence**: file:line または commit hash、SQL 結果、pytest 出力など実測値
- **Why it matters**: 本番影響の説明 (1-2 文)
- **Recommended action**: 具体的修正方針 (実装は本タスクでは禁止、方針のみ)

最後に **「Claude 側でこそ確認してほしい (静的整合・アーキ乖離) 項目」を 5-10 個** リストアップ。

## 制約 (絶対遵守)

- ⛔ **修正実装は禁止** (read-only audit、queue cleanup や hygiene fix も含めて変更コミット禁止)
- ⛔ 確信度の低いものは observation 止まり、claim にしない
- ⛔ **mock-only テストで PASS 報告する罠** (`feedback_codex_mock_test_trap`) を絶対回避。実 DB・実 API 応答ベースで evidence を出すこと
- ⛔ **schema ハルシネーション罠** (`feedback_codex_schema_hallucination`) 回避: テーブル定義は `.schema` で実取得してから書く
- ⛔ 本番 DB / `.env` / OANDA 秘密情報を破壊しうる操作禁止

## ACCEPT 条件

- 8 軸全てに Verdict + Evidence + Why + Action が記載
- 実 SQL クエリ結果 (少なくとも 5 個) と実 pytest 出力 (新規 test 2 件分) を Evidence として含む
- 「Claude 側でこそ確認してほしい項目」を 5 個以上リスト
- 修正 commit が 0 (read-only audit の遵守)

## NEEDS_MORE_EVIDENCE / REJECT 条件

- 推測ベースの記述が混じる
- mock-only での PASS 報告
- schema を読まずに SQL を書いた跡 (column 名 typo など)
- 本タスクで修正 commit が発生

## 関連メモリ参照
- `feedback_live_shadow_separation` — Shadow/Live 分離必須
- `feedback_codex_mock_test_trap` — Codex mock-only テストの罠
- `feedback_codex_schema_hallucination` — schema ハルシネーション
- `feedback_shadow_first_quant_architecture` — Shadow-first quant architecture
- `feedback_bt_must_use_massive` — BT は MASSIVE 必須
- `project_oanda_stats_range_ignored_2026_05_18` — /api/oanda/stats range バグ
- `project_rsk_gbpjpy_bar_close_gate_pending` — R3 rsk dedup pending
- `project_price_shock_phase_b1_done_2026_05_18` — Price-Shock Phase B-1
