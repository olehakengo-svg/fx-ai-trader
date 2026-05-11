---
id: 20260511-1230-strategies-page-snapshot-diff
title: "[Strategies-UI] tier-master 日次スナップショット + /strategies 期間比較 UI"
owner: codex
status: queued
priority: P2
created_at: 2026-05-11T12:30:00+0900
roadmap_gate: "司令塔ロードマップ外の UX 改善。tier 状態遷移を可視化することで Rule 2 (即断) 判断速度向上。Phase 1c / W4 残件と独立、衝突なし。"
rule: R3
related:
  - app.py
  - templates/strategies.html
  - knowledge-base/wiki/tier-master.json
  - scripts/
  - tests/
---

# 0. 背景

司令塔監査 2026-05-11 で確定した UX 欠陥:

- `/strategies` ページの API `/api/strategies/status` (`app.py:10193`) は `tier-master.json` 全体の `generated_at` 1 件しか返さない。戦略ごと/cell ごとの最終更新日が不明。
- ユーザは「直近大幅にエッジ更新した戦略」と「変わっていない戦略」を切り分けたいが、現 UI では全戦略がフラットに並ぶ。
- `tier-master.json` に per-entry `updated_at` を足す案 (C) は `sync_kb_index.py` / 手動編集の追記規律に依存し、Shadow-first で 70+ 戦略を回している現運用と相性が悪い (memory: feedback_shadow_first_quant_architecture)。
- Git mtime (B) は `sync_kb_index.py` の stamp 更新と人手 PR を区別できず偽陽性。

採用案: **日次スナップショットアーカイブ + 任意期間差分**。`tier-master.json` の状態 (tier / pair_promoted / pair_demoted / lot_boost / FORCE_DEMOTED) を集合演算で diff、戦略行ごとに変化内容を返す。

ユーザ追加要件:
- 比較基準日付を任意選択可能 (date picker)
- 任意 2 日間の期間比較も可能 (compare_from + compare_to)

# 1. 仕様

## 1.1 スナップショット保存

**保存先**: `knowledge-base/wiki/snapshots/tier-master-YYYY-MM-DD.json`

**保存スクリプト**: `scripts/save_tier_master_snapshot.py` を新規作成。
- 引数なしで実行 → 現在の `knowledge-base/wiki/tier-master.json` を読み込み、UTC 日付で命名した snapshot ファイルへコピー。
- 既存 snapshot ファイルがあれば上書き (1 日に複数回呼ばれてもよい)。
- `--date YYYY-MM-DD` で日付指定可能 (テスト / 手動補完用)。
- ファイル内容は `tier-master.json` をそのままコピー + 末尾に `_snapshot_taken_at` (UTC ISO) を追加。

**自動化**: `scripts/` 配下に既存 cron スクリプト群があるため、`scripts/oanda_sentiment_cron.py` と同様の体裁で配置。Render cron 登録は別タスク (本タスクでは spec 化のみで OK)、ローカル実行 + テストで完結する設計。

**Retention**: 無制限 (ファイルサイズ < 10KB × 365 日 = 4MB 未満)。古いファイルを消すロジックは入れない。

## 1.2 API 改修 (`app.py` / `/api/strategies/status`)

**追加クエリパラメータ**:
- `since=YYYY-MM-DD`: current state vs `since` 日 snapshot を diff
- `compare_from=YYYY-MM-DD` + `compare_to=YYYY-MM-DD`: 2 日 snapshot 同士を diff (current は無視)
- 上記いずれも指定無し → 既存挙動を完全維持 (`changes` フィールド付与しない)
- `compare_from` のみで `compare_to` 無しはエラー (HTTP 400)

**フォールバック規律**:
- 要求日の snapshot が存在しなければ「直近過去の存在する日付」へ繰り上げ
- 繰り上げた場合、レスポンスに `actual_from` / `actual_to` を返す (UI 表示用)
- 全 snapshot が存在しない (初回起動) → `changes` 無しで current のみ返す + `warning: "no snapshot available"`

**`generated_at` 同値スキップ**:
- baseline snapshot の `generated_at` と比較先の `generated_at` が同一なら diff 計算をスキップ (admin regenerate の no-op で偽差分が出るのを防ぐ)
- スキップ時はレスポンスに `note: "snapshots have identical generated_at, no diff computed"`

**戦略行ごとの差分フィールド** (各 `strategies[]` 要素に追加):
```json
"changes": {
  "tier_changed": true,
  "tier_from": "ELITE_LIVE",
  "tier_to": "FORCE_DEMOTED",
  "pair_cells_added": [{"pair": "USD_JPY", "tier": "PAIR_PROMOTED"}],
  "pair_cells_removed": [{"pair": "GBP_USD", "tier": "PAIR_DEMOTED"}],
  "lot_boost_toggled": false,
  "lot_boost_from": false,
  "lot_boost_to": false,
  "is_new": false,  // baseline に存在しなかった戦略
  "is_removed": false  // baseline には在ったが現状に無い
}
```
変化なしの戦略は `"changes": null` で返す (UI 側で簡潔にフィルタ可能)。

**レスポンストップレベル追加フィールド**:
```json
"diff_mode": "since" | "compare" | null,
"baseline_date": "2026-05-04",         // 要求日
"actual_baseline_date": "2026-05-04",  // 実際使った日 (繰り上げ反映)
"compare_target_date": "2026-05-10",   // compare モードのみ
"actual_compare_target_date": "2026-05-10",
"changed_count": 7,                     // changes != null の件数
"new_count": 2,
"removed_count": 1
```

## 1.3 UI 改修 (`templates/strategies.html`)

**triage バーに 2 モード追加**:

1. **Since モード** (デフォルト、画面遷移時 7d 前を自動セット):
   - `<input type="date" id="changedSince">` + プリセット `1d / 7d / 30d / OFF`
   - 既存 chip エリアに `Changed since YYYY-MM-DD (N)` カウンタ
   - "Changed only" toggle chip で `changes != null` の戦略だけ表示

2. **Compare モード** (toggle で展開):
   - `from` + `to` の date input 2 個
   - 戦略カードのバッジが `→` 矢印付き表示に変化

**戦略カードのバッジ** (compare モード時):
- `TIER: ELITE_LIVE → FORCE_DEMOTED` (FORCE_DEMOTED 入りは `--block` 赤強調)
- `+CELL: USD_JPY` (緑 `--go`)
- `-CELL: GBP_USD` (オレンジ `--warn`)
- `LOT_BOOST: off → on` (`--info` 青)
- `NEW STRATEGY` / `REMOVED STRATEGY` chip

**ヘッダ注釈**:
- snapshot 取得タイミング明示: `Snapshots taken daily at 00:00 UTC`
- フォールバック発生時: `Baseline: 2026-05-04 (requested 2026-05-05, fallback)`

**XSS 注意**:
- API レスポンスの戦略名・pair 名はそのまま innerHTML に入れず、`textContent` 経由で挿入する (既存コードの慣習を踏襲)

## 1.4 テスト

**新規 unit test**: `tests/test_strategies_snapshot_diff.py`
- snapshot 保存スクリプトが正しい命名で書き出すか
- 同一 `generated_at` 同士の比較で `note: skipped` を返すか
- tier 変化のみ / pair_cells 増減のみ / lot_boost トグルのみの各単体ケース
- baseline 不在 → fallback で直近過去日付を返すか (3 日分用意して中間欠落のケース)
- `since` と `compare_from`+`compare_to` の排他 (両方指定時は compare 優先)
- `compare_from` のみで `compare_to` 無し → HTTP 400

**既存テスト**: `tests/test_strategies_drift_check.py` 等の既存戦略 API テストが落ちないこと (回帰確認)。

# 2. 受入基準

- [ ] `scripts/save_tier_master_snapshot.py` が `knowledge-base/wiki/snapshots/tier-master-2026-05-11.json` を生成し、`_snapshot_taken_at` 付き
- [ ] `curl localhost:5000/api/strategies/status?since=2026-05-04` で `changes` フィールドが含まれる
- [ ] `curl localhost:5000/api/strategies/status?compare_from=2026-05-01&compare_to=2026-05-08` で 2 日間差分が返る
- [ ] `since` 指定日に snapshot 無し → `actual_baseline_date` が直近過去日になる
- [ ] `/strategies` ページの triage バーに date picker + Compare toggle が出現
- [ ] Changed only toggle で `changes != null` の戦略のみ表示
- [ ] FORCE_DEMOTED 入りした戦略のバッジが赤強調
- [ ] `python3 -m pytest tests/test_strategies_snapshot_diff.py -x -q` 全 PASS
- [ ] `python3 -m pytest tests/ -x -q` 既存 92 テスト + 新規追加分すべて PASS
- [ ] `python3 scripts/check.py` PASS

# 3. 非ゴール (本タスクで触らない)

- Render cron 登録 (snapshot 保存の自動化は手動 or 別タスク)
- `tier-master.json` 自体のスキーマ変更 (per-entry `updated_at` 等は追加しない)
- `/api/admin/regenerate-tier-master` の挙動変更
- 過去日の snapshot バックフィル (本タスクは 2026-05-11 以降のフォワード蓄積のみ)
- shadow / live PnL 数値の表示変更 (純粋に tier 状態の diff UI のみ)

# 4. 実装ヒント

- `app.py:10193` の `api_strategies_status()` の末尾近くで `diff_mode` 判定を挟み、helper 関数 `_compute_strategies_diff(baseline_dict, target_dict)` に切り出すと clean
- baseline / target どちらも `tier-master.json` と同形なので、`elite`, `force_demoted`, `pair_promoted`, `pair_demoted`, `lot_boost` の set 演算で済む
- pair_cells_added/removed は `pair_promoted` と `pair_demoted` 両方のセット差分を取って tier 情報付き dict にする
- フロント側は既存の chip インフラ (`.chip` class, `slideIn` アニメ) を流用。新規 CSS は最小限
- date input のデフォルト値は JS で `new Date(Date.now() - 7*86400*1000).toISOString().slice(0,10)` で 7d 前固定

# 5. クオンツ的注意

- このタスクは UI 層のみで戦略ロジック・統計に影響しない。Rule 3 (即時) で進めて良い
- ただし「FORCE_DEMOTED 入り」の視認性は Rule 2 (損失停止) の判断速度に直結するので、赤強調の色は既存 `--block` (rgba(244,63,94)) を使い、ユーザの色彩記憶を壊さない
- snapshot 保存タイミングが UTC 00:00 = JST 09:00 のため、日中の tier 変更は翌日まで snapshot に反映されない。これは仕様として明示 (運用上、リアルタイム性が要るときは current state を見れば足りる)
