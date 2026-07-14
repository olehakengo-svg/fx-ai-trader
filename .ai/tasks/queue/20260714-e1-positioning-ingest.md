---
id: 20260714-e1-positioning-ingest
title: "[v2.3 WS3/供給ライン] E1 positioning ingest — OANDA 建玉/注文比率の時系列蓄積基盤"
owner: claude
status: done
priority: P1
created_at: 2026-07-14T12:00:00+0900
roadmap_gate: "トラックB 供給ライン。round-3 §4 固定分岐 (price-modality 3周 FAIL → E1 格上げ)。user GO 2026-07-14 ([[external-hypothesis-scan-2026-07-13]] §6)。live/shadow/Kelly 変更なし (rule:R3 データ基盤)"
rule: R3
executor_note: "claude 直接実行 (本ファイル作成と同一 PR で claim→完了)。ローカル OANDA token 失効のため実データ検証は本番デプロイ後 (/api/positioning/status)"
prereq_artifacts:
  - knowledge-base/wiki/research/external-hypothesis-scan-2026-07-13.md   # §6 = user 決裁根拠
  - knowledge-base/wiki/analyses/e1-positioning-ingest-2026-07-14.md      # 設計/schema/監視/検証手順
related:
  - knowledge-base/wiki/decisions/ws3-round3-crossasset-divergence-prereg-2026-07-13.md
  - knowledge-base/wiki/decisions/shortest-path-decision-memo-2026-07-10.md
---

# 要求仕様

1. `modules/positioning_ingest.py` 新設 — background thread、`POSITIONING_INGEST_ENABLE` (default "1")、6 instruments (env override 可)、poll 20 分 + jitter、book.time dedup、fail-loud (連続失敗カウント露出、silent except 禁止)、モジュールトップ副作用禁止。
2. 永続化: 既存 SQLite に `positioning_snapshots` + UNIQUE(instrument, book_type, snapshot_time)。buckets mid ±3% trim + 集計列 (pct_long_total / pct_short_total / near_imbalance)。demo_db.py migration パターン準拠。
3. 検証 API: `/api/positioning/status` / `/api/positioning/export`。
4. 監視: registry `e1-positioning-ingest-freshness` (2h 超 stale = 要調査)。
5. テスト offline/deterministic (parse/trim/集計、dedup、UNIQUE、ENABLE off) + 既存 green + check.py。
6. KB 同一コミット (analyses ページ + changelog + 本 task)。

---

## 完了記録 (2026-07-14, claude)

✅ 全 6 項目完遂 (単一 PR):

- **実装**: `modules/positioning_ingest.py` (worker + 純関数 parse/trim/集計 + singleton) / `modules/oanda_client.py` に `get_position_book`・`get_order_book` (read-only GET) / `modules/demo_db.py` `_init_tables` から schema 冪等作成 / `app.py` status+export API と autostart gate 内 thread 起動 (テスト/BT プロセスでは不起動)。
- **dedup 3 層**: book.time メモリ比較 + 再起動時 DB seed + UNIQUE(INSERT OR IGNORE)。
- **監視**: registry エントリ追加 + `tools/prereg_trigger_watch.py` に info/conditional_info type (unknown-type UNAVAILABLE ノイズ解消)。
- **テスト**: `tests/test_positioning_ingest.py` 17 本 (fixture book で trim 境界/near 帯/集計、4xx unsupported、429 非永久 skip、token 欠落 fail-loud、API 契約) + `tests/test_prereg_trigger_watch.py` +2 本。
- **未検証 (構造的)**: OANDA 実レスポンスとの疎通 — ローカル token 失効 (401) のため**本番デプロイ後に** `/api/positioning/status` で検証する (手順: KB ページ §5)。エンドポイント可用性マップも同時に確認。
- KB: [[e1-positioning-ingest-2026-07-14]] / changelog 2026-07-14 / [[external-hypothesis-scan-2026-07-13]] §6 に決裁追記 / [[shortest-path-decision-memo-2026-07-10]] §7 追記。
