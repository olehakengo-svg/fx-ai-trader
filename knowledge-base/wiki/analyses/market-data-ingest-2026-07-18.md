# R3 market-data ingest — E7/E12 の read-only データ基盤 (2026-07-18)

**決裁枠**: [[e1-positioning-ingest-2026-07-14]] と同一 (rule:R3 データ基盤投資、live 無関係の read-only snapshot 蓄積)。
**起点**: [[external-hypothesis-scan-round2-2026-07-18]] §「今から始めないと不可逆なインフラ (infra_needed_now)」3 件の実装裁定。

## 1. 裁定サマリ

| # | round-2 の infra 項目 | 裁定 | 根拠 |
|---|---|---|---|
| (1) | FF Actual 補完 ingest (E7) | ✅ **実装** — faireconomy 公式 feed 6h capture + **翌期 previous 逆引き** reconcile + import 経路 | feed 実 fetch 再確認 (Actual フィールド無し)。FF 本体は Cloudflare challenge 403 実測 → 自動 scrape は不実装 (§3) |
| (2) | CME FX 先物 1h volume capture (E12) | ✅ **実装** — yfinance 60m を日次 capture、7 契約 | 実 fetch 検証済み (2026-07-18 smoke: 310 bars 保存成功)。730d rolling 窓は本セッションでも再確認 |
| (3) | CME オプション settlement/OI 日次 scrape (E9/E10/E14) | ❌ **不実装 — round-2 の前提を訂正** | probe が「scraping は CME Data Terms of Use で禁止」の**明示 403** を返却 (§4)。かつ Databento (licensed distributor) は**歴史を保持する**ため「今から貯めないと不可逆」は本項目には当てはまらない |

実装: `modules/market_data_ingest.py` (worker) / `tools/ff_calendar_import.py` (gap 合流) / `tests/test_market_data_ingest.py` (38 tests, offline)。
検証 API: `/api/marketdata/status`, `/api/marketdata/export?table=ff_events|cme_bars|health_log`。

## 2. データソースの敵対的 probe (2026-07-18 実測)

| ソース | 結果 | 帰結 |
|---|---|---|
| `nfs.faireconomy.media/ff_calendar_thisweek.json` | HTTP 200、98 events、keys = `country/date/forecast/impact/previous/title` — **actual 無し** | go-forward capture の一次ソース。**lastweek/nextweek は 404** (thisweek のみ提供) |
| 同 feed 2 回目 fetch (~30 分後) | **HTTP 429 Rate Limited** | per-IP throttle は厳格。poll は 6h (4 req/日) + 失敗時 retry 30 分に設定 — 本番 (Render 固定 egress) では十分低頻度 |
| `forexfactory.com/calendar?week=...` | **HTTP 403 Cloudflare challenge** ("Just a moment...") | サーバサイド自動 scrape は不可。**challenge bypass は構築しない** (方針、§3) |
| `cmegroup.com/ftp/pub/settle/stlcur` | **HTTP 403**: "Use of scripts, software, spiders, robots ... is strictly prohibited by CME Group's website Data Terms of Use" + IP block 宣言 | 無料 settlement scrape は ToS 違反経路 — 恒久 job として実装不可 (§4) |
| yfinance `6E=F` 60m `period=8d` | 155 bars、UTC index、非ゼロ volume 96% | E12 経路は健全。smoke で 2 symbol × 155 bars を SQLite 保存成功 |

## 3. FF カレンダー capture の設計 (E7)

**目的**: E7 (event-surprise directional) の clean OOS 蓄積 clock を今日開始する。surprise = actual − forecast の**発表前 forecast** と**発表後 actual** の両方が必要だが、feed に actual が無い。

- **capture**: faireconomy 公式配信 feed (widget 用に公開されているもの) を 6h 毎 fetch。生 feed は `ff_feed_snapshots` に content-hash dedup で全量温存 (parse バグからの全量リカバリ経路 — positioning の buckets_json 温存と同じ ethos)
- **forecast 凍結**: `UNIQUE(country, title, event_time_utc)` で upsert し、**event_time 通過後は forecast/previous/impact を更新しない**。発表前の最終 forecast が surprise の estimand — 事後の feed 側改変が estimand を汚染しないよう構造で防ぐ (単なる運用規約ではなく code 強制)
- **actual 補完 = 翌期 previous 逆引き**: 同一系列 (country, title) の次回発表行の `previous` は前回の actual。reconcile は actual IS NULL かつ発表済みの行のみ埋める (冪等、`actual_source='next_previous'` で来歴明示)
- **既知の限界 (E7 pre-reg で宣言必須)**:
  1. 逆引き actual は「次回発表時点の**改定値**」— first print ではない。US 系は ALFRED vintage で first print を別途復元可能 (research 時タスク)
  2. actual 確定は次回発表まで遅延 (月次指標なら ~1 ヶ月)。OOS 判定時点で直近 1 期の actual が未充填になる — verdict 時は充填済み区間で判定
  3. 日程変更 (tentative) は新 event_time で別行になる — 旧行は actual 未充填のまま残る (ノイズとして許容、reconcile は埋めない)
- **FF 本体 scrape は不実装**: Cloudflare challenge の機械的回避 (cloudscraper/headless challenge solver) は構築しない。発表直後の actual 即時性が E7 検証に必須になった場合は、正規 API (ALFRED/FRED、TradingEconomics 有償等) を別途裁定する
- **歴史 gap (2023-04〜、~170 週)**: `tools/ff_calendar_import.py` で正規入手 dump (EPSOFT 延長 / 公開 dataset / 手動 export) を同一テーブルへ合流。`actual_source='import:<tag>'` で来歴分離、**既存 actual は上書きしない**。gap は BT discovery 深度の問題であり、不可逆なのは go-forward clock の方 — 本 PR で clock は開始済み

## 4. CME settlement/OI (round-2 infra (3)) の訂正

round-2 は「CME 無料 settlement は ~7 日窓のみ → 今から貯める以外に無料経路が無い = 不可逆」と裁定したが、probe で 2 点の事実が確定:

1. **無料経路は ToS 禁止**: CME の 403 応答はレート制限ではなく「automated means での取得は Data Terms of Use で禁止、商用/自動取得は GCC へ問い合わせよ」という**方針の明文**。恒久 daily scrape job をこの明文に反して回すことはしない (コンプライアンス + Render egress IP の block リスク)
2. **「不可逆」前提は不成立**: Databento は CME の licensed distributor で **settlement/OI を含む statistics schema の歴史を保持・販売**している。E9 無料 probe (EVZCLS×MASSIVE) → 正なら Databento サインアップ、という round-2 自身の順序決定に従えば、サインアップ時点で **forward も歴史も両方**入手できる。「今から貯めないと消える」のは faireconomy feed (誰も歴史を配らない) と yfinance 730d 窓 (rolling で消える) であり、CME settlement には当てはまらない

→ **E9/E10/E14 の forward データは Databento 一本化** (クレジット 6 ヶ月失効のため E9 probe を 2026-Q4 までに判定、の既決裁は不変)。[[external-hypothesis-scan-round2-2026-07-18]] の infra_needed_now (3) はこの doc で上書き。

## 5. CME 1h volume capture の設計 (E12)

- 7 契約 (`6E=F 6J=F 6B=F 6A=F 6C=F 6S=F 6N=F`) = 13 ペア universe の対 USD base 通貨を網羅。追加コストは 1 req/契約/日
- 日次 capture、`period=8d` overlap で週末/障害を跨いでも欠落しない。**形成中 bar は保存しない** (partial volume の凍結防止、`filter_closed_bars`)
- `INSERT OR IGNORE` = **初回 capture 値を凍結**。yfinance の事後補正で歴史が動くと BT 再現性が壊れるため、first-capture 主義 (乖離が疑われたら export で再検証)
- 730d rolling 窓の左端 (実測 2024-02-23) は毎日 1 日ずつ消える — capture 開始日 (2026-07-18) 以降、検証歴史は 2y から単調延伸する。**深い歴史 backfill (2024-02 までの 2y 分) は次回 deploy 後の初回 cycle が自動で取る訳ではない** (period=8d)。必要なら一度だけ `period=730d` の手動 backfill を Render console で実行する (次アクション §7) → ✅ **実行済み 2026-07-21** (§7 (2) に結果記録)

## 6. 実装の構造 (positioning_ingest パターン準拠)

- fail-loud: 連続失敗カウント / last_error / phase を status 露出、silent except ゼロ
- モジュールトップ副作用禁止、fetch/env 解決は全て関数内
- `defer_thread=True` で gunicorn master では thread 不起動 (fork-safety [[e1-positioning-ingest-2026-07-14]] §11 と同一根拠)、before_request heartbeat + status API が self-heal 経路
- health: `market_ingest_health` (upsert) + `market_ingest_health_log` (同一トランザクション append) — dedup skip と fetch 失敗を DB の行だけから識別可能
- restart 跨ぎ: `_seed_next_due()` が health の verified から due を温める — 頻繁な fork/restart で外部 API を叩き直さない (faireconomy 429 対策も兼ねる)
- env: `MARKET_INGEST_ENABLE` (default 1) / `FF_CALENDAR_POLL_SEC` (default 21600, ≥3600 clamp) / `CME_BARS_POLL_SEC` (default 86400, ≥21600 clamp) / `CME_BARS_SYMBOLS` / `FF_CALENDAR_URL`

## 7. 監視と次アクション

- **監視**: `/api/marketdata/status` — stale 基準 ff_calendar 24h / cme_bars 72h (週末市場閉鎖を跨いでも誤警報しない)。✅ **registry へ freshness watch 追加済み (2026-07-21)**: `r3-market-data-ingest-freshness` — E1 `e1-positioning-ingest-freshness` と同型の ingest 鮮度 watch だが、こちらは**機械評価** (`tools/prereg_trigger_watch.py` の type=`ingest_freshness` が health の verified:* age を毎日判定)。キー欠落・7 契約未満 (min_keys) も fail-loud で TRIGGERED (worker 未稼働/thread 死の検出 — E1 thread 死教訓)。API 不達/health DB エラーは DATA_UNAVAILABLE (「stale 確定」と区別)。閾値/契約数は `STALE_ALERT_*_SEC` / `DEFAULT_CME_SYMBOLS` とテストで整合固定 (`tests/test_prereg_trigger_watch.py::test_ingest_freshness_registry_matches_module_constants`)
- **次アクション**:
  1. ~~deploy 後検証~~ → ✅ **2026-07-21 確認済み**: running=true、verified:ff_calendar=2026-07-21T10:55Z + cme 7 契約全 verified (同時刻)。初回の 6E=F yfinance empty (10:22Z) は retry で自己回復済み (restarts=1、last_error に痕跡)
  2. CME 1h の深い backfill: Render console で一度だけ `period="730d"` fetch (2024-02〜の 2y を確保)。go-forward は日次 job が維持
     → ✅ **完了 2026-07-21 11:10Z** (Render SSH で `yf_fetch_bars(sym, period="730d")` + `filter_closed_bars` + `save_bars` を 7 契約実行)。結果: 新規 **95,069 行** / dedup 1,008 (go-forward 既存 144 行/契約 × 7 は INSERT OR IGNORE で凍結維持) / 失敗 0。全 7 契約 **first_bar = 2024-02-27T05:00Z** (実行時点の yfinance 60m 左端) 〜 latest 2026-07-21T10:00Z、~13.7k bars/契約。`/api/marketdata/status` + `/api/marketdata/export?table=cme_bars` の両経路で検証済み。以後の歴史延伸は日次 job (period=8d) の単調 capture のみ — **再実行不要** (730d 窓はこれ以上左に伸びない)
  3. FF 歴史 gap: EPSOFT 延長入手 or 正規 dataset を裁定 → `tools/ff_calendar_import.py` で合流
  4. E7+E15 イベントモダリティ・プログラムの pre-reg 起案 (round-2 の次アクション (1)、本 doc の §3 限界 1〜3 を宣言に含める)

## 8. 評価への影響

**なし** — read-only 蓄積 + 検証 API + import ツールのみ。live 発注経路・戦略・Kelly・shadow・BT 関数いずれも不変。
