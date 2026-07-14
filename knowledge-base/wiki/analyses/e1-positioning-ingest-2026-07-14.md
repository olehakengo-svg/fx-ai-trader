# E1 positioning ingest — OANDA 建玉/注文比率の時系列蓄積基盤 (2026-07-14)

> **rule:R3 (データ基盤、live 無関係)** — **user GO 2026-07-14**。決裁根拠: [[external-hypothesis-scan-2026-07-13]] §6 (E1 positioning-ingest 提案)。
> **これは戦略ではない。** retail-positioning contrarian (E1) 検証のための read-only データ収集。live 発注経路・戦略・Kelly には一切触れない。
> **関連**: [[shortest-path-decision-memo-2026-07-10]] トラックB (供給ライン) / [[roadmap-v2.3-payoff-friction-repair]] WS3 / MEMORY `project_ws3_external_hypothesis_transition_2026_07_13`

## 1. なぜ今か (背景)

- WS3 price-modality 探索は**内部 2 周 + 外部 cross-asset 1 周 = 計 3 周 FAIL** ([[ws3-round3-crossasset-divergence-prereg-2026-07-13]] §8、2026-07-14 PR #82) で枯渇確定。round-3 pre-reg §4 の固定分岐により **E1 positioning (非価格モダリティ) が供給ラインの主戦線**。
- E1 の学術根拠 (*News and intraday retail investor order flow in FX*, JIFMIM 101, 2025): 個人フローの逆側に intraday 予測性。検証には positioning の**時系列**が必須。
- **history は今から蓄積する以外に入手不可** — broker 建玉の過去分は非公開。着手が 1 日遅れるほど OOS 検証開始が 1 日後ろ倒し。→ 稼働開始が最優先 (user GO の核心)。

## 2. 何を集めるか

- **ソース**: OANDA v20 `GET /v3/instruments/{instrument}/positionBook` / `orderBook` (read-only、token のみ、account 不要)。OANDA 側 snapshot は約 20 分毎更新。
- **対象 instruments** (default): USD_JPY, EUR_USD, GBP_USD, EUR_JPY, GBP_JPY, AUD_JPY — env `POSITIONING_INSTRUMENTS` (カンマ区切り) で override 可。
- **poll**: 20 分 (`POSITIONING_POLL_SEC`, default 1200) + jitter (<120s)。**dedup**: book の `time` が前回保存と同一なら skip (メモリ + 再起動時は DB seed + UNIQUE の 3 層)。
- **有効化**: env `POSITIONING_INGEST_ENABLE` (default "1")。thread 起動は app.py の autostart gate 内 (`RENDER=1` or `FORCE_AUTOSTART=1`) — テスト/BT プロセスでは起動しない。

## 3. Schema (`positioning_snapshots`, 既存 SQLite = Render `/var/data/demo_trades.db`)

DDL 単一ソース: `modules/positioning_ingest.py` (`demo_db.py _init_tables` から冪等呼び出し)。

| 列 | 意味 |
|---|---|
| `instrument`, `book_type` | ペア × 'position'\|'order' |
| `snapshot_time` | OANDA book.time (RFC3339)。**UNIQUE(instrument, book_type, snapshot_time)** |
| `price`, `bucket_width` | book anchor 価格 / bucket 幅 |
| `buckets_json` | `[ [price, longPct, shortPct], ... ]` — **mid ±3% に trim して保存** (容量 <5MB/月/instrument 目標) |
| `pct_long_total`, `pct_short_total` | **trim 前の全帯域**合計 (全体 long/short 比率) |
| `near_imbalance` | mid ±0.5% 帯の long−short (現値近傍の偏り = contrarian シグナル候補の一次統計) |
| `fetched_at` | 取得時刻 (UTC) |

**サイズ試算**: trim 後 ~120 buckets × ~30B × 2 books × 72 snap/日 ≈ 0.5MB/日/instrument 上限 → 実際は dedup (OANDA 更新 ~20 分毎 = 上限 72/日) と JSON compact 化で目標内。

## 4. 可観測性 (fail-loud 設計)

- **`GET /api/positioning/status`**: worker 状態 (running / poll_cycles / last_error / consecutive_cycle_failures) + instrument×book 毎の {rows, latest_snapshot_time, stale_seconds, consecutive_failures, available, unsupported}。worker 未起動でも DB 側 books を返し「thread 死」と「未起動」を外部から区別可能。
- **`GET /api/positioning/export?instrument=&book=&from=&limit=`**: 研究用 JSON export (snapshot_time 昇順、buckets JSON roundtrip 済み)。
- **エンドポイント非対応** instrument は初回 4xx (429 以外) を記録して以後 skip — 可用性マップとして status に露出。429/5xx/timeout は一時障害扱いでリトライ継続。
- **silent except 禁止**: 全失敗が consecutive_failures / last_error / stdout `[positioning]` 行に出る (lesson: watchdog DECREMENT / 0-price ガード)。
- **監視主体の併設 (T5 教訓)**: registry `e1-positioning-ingest-freshness` (type: info) — **最終 snapshot が 2h 超 stale なら要調査** (OANDA 更新 ~20 分毎の 6 倍マージン)。`tools/prereg_trigger_watch.py` に info/conditional_info type を追加し daily report で常時 watching 表示。

## 5. 本番デプロイ後の検証手順

1. `https://fx-ai-trader.onrender.com/api/positioning/status` — `enabled:true / running:true` と、初回 poll 後に各 instrument×book の `latest_snapshot_time` が現在時刻 ±30 分内であること。
2. `consecutive_failures` / `consecutive_cycle_failures` が 0 に収束すること。**401 が続く場合は本番 OANDA_TOKEN の失効を疑う** (ローカル .env token は失効確認済み — 本番でのみ実データ検証可能)。
3. `available:false` の book があれば `unsupported.code` を確認 (OANDA が book を提供しない instrument の可能性 — 事実として KB に追記)。
4. 24h 後: 各 instrument×book で rows ≈ 60–72/日 (dedup 後) であること。`/api/positioning/export?instrument=USD_JPY&book=position&limit=5` で buckets / near_imbalance が妥当な値か目視。
5. 1 週間後: DB サイズ増分を確認 (目標 <5MB/月/instrument)。超過時は trim 幅 (±3%) or 対象 instruments を再検討。

## 6. E1 検証への接続 (次のステップ、本 PR の範囲外)

- 蓄積 N が揃い次第 (目安: 2–3 ヶ月で 15m–1h horizon の OOS 検定に足る系列)、round-1〜3 と同一方法論 (discovery→凍結→clean OOS、BH-FDR + first-touch EV + ナイフエッジ 3 点) で pre-reg 起案。
- 候補一次統計: `near_imbalance` (現値近傍の偏りの逆張り) / `pct_long_total − pct_short_total` (全体 skew) / orderBook vs positionBook の乖離。**本ページはデータ基盤の記録であり、エッジ主張はゼロ。**

## 7. 実装 (2026-07-14, 本 PR)

- `modules/positioning_ingest.py` — parse/trim/集計 (純関数) + `PositioningIngestWorker` + module singleton
- `modules/oanda_client.py` — `get_position_book` / `get_order_book` (read-only GET)
- `modules/demo_db.py` — `_init_tables` から schema 冪等作成 (fail-loud)
- `app.py` — status/export API + autostart gate 内 thread 起動
- `tools/prereg_trigger_watch.py` — info/conditional_info type (+ registry エントリ)
- tests: `tests/test_positioning_ingest.py` (17) + `tests/test_prereg_trigger_watch.py` (+2)
