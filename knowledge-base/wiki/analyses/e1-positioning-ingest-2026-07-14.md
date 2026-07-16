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

> ⚠️ **2026-07-14 追記**: 本節 2. の「401 = token 失効を疑う」は §8 で棄却された (401 の真の帰属は OANDA の book 提供終了)。手順は歴史記録として残す。

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

## 8. 本番実証 (2026-07-14) — 2 問題の帰属確定と修正 (rule:R3)

デプロイ後検証 (§5) で 2 問題を確認。いずれも当日中に帰属確定。

### 8a. 全 12 book が HTTP 401 → 帰属 = **OANDA retail API の book 提供終了** (token/区分の問題ではない)

**観測**: Render ログ (srv-d6va1of5r7bs73en10vg) 2026-07-14T08:03Z / 08:20Z の 2 デプロイとも、worker 起動直後に 6 ペア × position/order 全 12 book が `UNSUPPORTED http=401`。本番 token は発注では有効。

**当初仮説「OANDA Japan 区分の book 提供制限」は棄却**。確定した事実:

| 証拠 | 内容 |
|---|---|
| **公式告知 (一次ソース)** | OANDA Japan 2024-08-30 告知 ([oanda.jp/info/1193](https://www.oanda.jp/info/1193)): 「OANDA APIで提供しているオーダーブックの情報は、9月14日（土）を持ちましてサービス終了とさせていただきます。」= **2024-09-14 に API での book 提供自体が終了** (2026-07-14 原文を直接確認) |
| **独立実測 (2026-07-14)** | v20 book は **no-token / garbage-token でも同一の generic 401** (`Insufficient authorization to perform request.` — /v3/accounts の garbage-token 応答と同一文言)。つまり 401 単体は認可ゲートの共通応答で、token 有効性を判別できない |
| **fxlabs は既に廃止** | `/labs/v1/orderbook_data` は 2020-01 廃止 (公式回答: [oanda-api-v20#156](https://github.com/hootnot/oanda-api-v20/issues/156))。2026-07-14 実測で **403 HTML (WAF)** = ルート自体が消滅。practice host も同様 |
| **platform-wide の傍証** | 非日本ユーザーも 2024-09 末に同時遮断 ([dekalogblog 2024-09-27](https://dekalogblog.blogspot.com/2024/09/discontinuation-of-oandas-orderbook-and.html)、OANDA 回答は「business decision」)。developer.oanda.com から Instrument endpoints ページ削除 (404)。「全区分」は推定 (公式文言は Japan 告知のみ) だが三角測量は強い |

**機械確認手段 (本 PR 追加)**: `GET /api/positioning/probe?run=1` — v3/accounts を統制 (発注系と同じ認証) にした read-only probe。本番 token で `accounts 200 + book 401` が出れば「token 有効なのに book だけ拒否」= 提供終了帰属が機械的に確定する。**token / 口座 ID はレスポンスに一切含めない契約 (テストで pin)**。

**✅ 本番 probe 実行結果 (2026-07-14T10:48:19Z、PR #84 デプロイ後)** — 帰属確定:
- `v3_accounts` = **200** (accounts=2、token 有効)
- `v3_position_book` / `v3_order_book` = **401** `"Invalid authentication credentials"` — 有効 token でも book のみ拒否。no-token 時の generic 文言 (`Insufficient authorization...`) と異なる = 認証ヘッダは受理された上で**この資源への資格が無い** (entitlement 拒否)
- `labs_v1_orderbook_data` = **403 HTML** (WAF、ルート消滅)
- probe interpretation: 「token 有効 (v3/accounts 200) だが v20 book が 401 → OANDA の retail API book 提供終了 (2024-09-14) に合致」

**含意**: **現行 ingest は auth 修理 (token 更新・区分変更) では直らない。データソース交換が必要** (§8c)。OANDA 側で bucket 級データが残る正規経路は有償 OANDA Data Services のみ (~$1,850/月・12ヶ月契約、伝聞。2024-05 以降のデータ品質劣化報告あり)。

### 8b. worker thread がプロセスライフサイクルで死ぬ → self-heal 実装

**観測**: status API が `started_at: 08:20:17Z` (worker start 時刻と一致) を返すのに `running:false / poll_cycles:0 / unsupported:null` で恒常不変 (応答 2039B 固定)。一方 Render ログには同時刻に UNSUPPORTED ×12 が出ている = **poll を実行した process の状態が、HTTP を返す process に存在しない** (fork copy のみ残存)。

**帰属**: app.py import 時 (module-level autostart gate) に起動した thread は、gunicorn (`--workers 1 --threads 8 gthread`) の process ライフサイクルで request-serving process に生き残らない。**demo_trader が同条件で生きているのは `get_status()` 内 StatusHeal (request 駆動の is_alive→再起動) があるから** — positioning worker にはこの経路がなかった。

**修正 (本 PR, rule:R3)** — demo_trader StatusHeal パターン準拠:
1. `PositioningIngestWorker.ensure_running()` — 「start() 済み (started_at あり) なのに thread 死」のみ heal。明示 `stop()` 後・未 start は復活させない。`_heal_lock` で二重起動防止、`_seed_last_saved()` で dedup を DB から温め直す
2. `status()` 冒頭で StatusHeal — 観測経路そのものを復活経路にする
3. app.py `before_request` heartbeat (60s throttle) — **Render health check を恒常 heal 経路化** (外部監視・cron に依存しない)
4. 可観測性: status に `restarts` / `last_restart_at` を追加

**✅ 本番実証 (2026-07-14T10:47Z、PR #84 デプロイ後)**: デプロイ直後の status で `running:true / restarts:1 / last_restart_at:10:47:21Z / poll_cycles:1` — heartbeat が即座に heal し、**serving process から 12/12 book の unavailable マップが初めて可視化** (PR #83 時代の「401 を記録した process と HTTP を返す process が別」の観測不整合も解消)。restarts が単調増加し続ける場合は thread が繰り返し死んでいるサイン (要再調査)。

### 8c. 代替ソース比較 (user 決裁用) — 2026-07-14 調査

E1 の一次統計のうち **near_imbalance (現値近傍の偏り) は price-bucket 級データが必須**だが、無料の bucket 級ソースはもう存在しない。比較:

| ソース | データ形状 | bucket級? | 取得 | 制約 | E1 適合 |
|---|---|---|---|---|---|
| **OANDA practice token** | (生きていれば) v20 book そのもの | ✅ | user が無料 practice account 作成 → token | **platform-wide 提供終了のためほぼ確実に死亡** (未実測)。検証 5 分 | 期待値低 |
| **OANDA Data Services (有償)** | v20 book 相当 | ✅ | 有償契約 | ~$1,850/月・12ヶ月縛り (伝聞)。品質劣化報告 (2024-05〜) | M1 段階でコスト非対称 |
| **Myfxbook Community Outlook** | long/short % + volume + positions + **avgLong/ShortPrice** (全 symbol 一括) | ❌ (avg 価格 1 点/side のみ) | 無料 account → login.json → get-community-outlook.json | **100 req/24h** (≈15分間隔、現行 20 分 poll と整合)。session が IP-bound (Render egress IP 変動に注意)。API 利用は無料ソフト限定 ToS (内部 quant 利用は可) | **推奨 fallback** — 全体 skew + avg 価格距離で E1 を aggregate 版に再設計 |
| **IG client sentiment** | long/short % のみ | ❌ | IG account + API key | **IG証券 (日本) は retail API 提供なし** → 日本居住では実質不可 | 不可 |
| **Dukascopy SWFX** | long/short % (30分更新) | ❌ | JForex (Java) Strategy API | Python stack と不整合、widget scrape は ToS-gray | 弱 |
| その他 (FXCM SSI / FXSSI / aggregators) | aggregate | ❌ | 有償 or API なし or 低信頼 | — | 弱 |

**決裁オプション (推奨順)**:
- **A (推奨): Myfxbook で E1 を aggregate 版に転換** — near_imbalance は放棄し、全体 skew (`pct_long_total−pct_short_total` 相当) + 現値 vs avgLong/ShortPrice 距離を一次統計に再定義。user アクション: Myfxbook 無料 account 作成 + credentials を Render env へ。schema は `positioning_snapshots` を流用可能 (buckets_json 空、pct_long/short + avg 価格)
- **B: practice account 5 分検証** — 期待値は低いが安価。A と並行可 (`/api/positioning/probe?run=1` を practice token で実行するだけ)
- **C: OANDA Data Services 有償契約** — bucket 級が本当に必要になった段階 (E1 が aggregate 版で PASS した後) まで保留を推奨
- **D: E1 閉鎖して別モダリティへ** — round-4 (EUR ペア価格系) は cache 延伸待ち。E1 を試さず閉鎖する積極的理由は現状ない

**registry への影響**: `e1-positioning-ingest-freshness` は蓄積ゼロが**既知状態**になった (12/12 book 提供終了)。user 決裁までは stale が正常 — 毎日の調査は不要。決裁後に鮮度監視を再開する (registry message を本コミットで更新済み)。

---

## 9. 決裁と実装 — Myfxbook aggregate 転換 (2026-07-15、オプション A 採択)

**決裁**: user は 2026-07-15 に「最短がオーダーなので、やり方は任せる」と全面委任
(mission memory: 運用判断は Claude に全面委任、実行者選定含む — 2026-07-08)。
§8c 推奨順に基づき **オプション A (Myfxbook Community Outlook への aggregate 転換)
を採択** (rule:R3 — データ基盤の交換、エッジ主張ゼロ)。B (practice 検証) は期待値低で
A と競合しないため保留、C (有償 $1,850/月) は M1 段階でコスト非対称、D (閉鎖) は
price-modality 3周 FAIL 後の唯一の主戦線を閉じる積極的理由なし。

### 実装 (PR: feat/e1-myfxbook-aggregate-2026-07-15)
- **`modules/myfxbook_client.py` (新規)**: login.json → session、
  get-community-outlook.json → 全 symbol 一括。session 失効 (IP-bound) は
  1 回だけ自動 re-login。secrets (email/password/session) はレスポンス/ログ/
  status に一切含めない (テストで pin)。requests 必須 (urllib fallback なし)
- **`modules/positioning_ingest.py`**: ソース抽象 —
  `POSITIONING_SOURCE` 明示 > `MYFXBOOK_EMAIL`/`MYFXBOOK_PASSWORD` 自動検出 >
  oanda default。myfxbook 時は book_type=`"outlook"` (1 instrument = 1 book)、
  poll ≥900s clamp (rate limit 100 req/24h → ≤96 req/日)
- **schema 流用** (migration なし): `positioning_snapshots` に
  book_type='outlook' 行。`pct_long_total`/`pct_short_total` =
  longPercentage/shortPercentage、`near_imbalance` = **NULL (bucket 級放棄の明示)**、
  `buckets_json` = raw payload の JSON **object** (avgLong/ShortPrice, volume,
  positions を研究用に温存 — OANDA 行の JSON array と型で区別可能)
- **dedup**: outlook は snapshot 時刻を持たない → content-hash (sha256) で
  「内容が変わったら新規行」。再起動時は最新行の buckets_json から再計算 (seed)。
  snapshot_time は fetch 時刻 (microsecond 精度 — 同一秒内の content 変化が
  UNIQUE 制約で silent drop されるのを防ぐ)
- **可観測性**: status に `source` + `myfxbook.{configured, waiting_for_credentials,
  logged_in, logins_total, last_login_at, requests_total}`。credentials 未設定は
  「E1 waiting for credentials」を毎 cycle loud に出す既知状態
- **受け入れ確認**: `/api/positioning/probe?run=1&source=myfxbook` — login +
  outlook 1 回で credentials を検証 (rate limit を消費するため常時監視には使わない)
- self-heal (§8b) はソース非依存でそのまま有効

### E1 一次統計の再定義 (aggregate 版)
near_imbalance (bucket 級) は放棄。候補一次統計:
1. **全体 skew**: `pct_long_total − pct_short_total` の水準/変化率 (contrarian)
2. **avg 価格距離**: 現値 vs `avgLongPrice`/`avgShortPrice` (含み損側の偏り =
   squeeze 圧力 proxy)
3. orderBook vs positionBook 乖離は取得不能になったため**候補から除外**

エッジ検証 gate は §6 の接続計画のまま: 蓄積 2–3 ヶ月 → discovery→凍結→clean OOS
(BH-FDR + first-touch EV + ナイフエッジ 3 点検査) の pre-reg 起案。

### user アクション (これだけで E1 が動き出す、~5 分)
1. https://www.myfxbook.com で無料アカウント作成 (メール認証まで)
2. Render web service `srv-d6va1of5r7bs73en10vg` の env に
   `MYFXBOOK_EMAIL` / `MYFXBOOK_PASSWORD` を追加 (または credentials を
   Claude に渡せば Render MCP で設定可)
3. デプロイ後 `https://fx-ai-trader.onrender.com/api/positioning/probe?run=1&source=myfxbook`
   で `outlook_ok:true` を確認 (Claude が実行可)

**蓄積が始まらない限り M1 タイムラインが 1 日ずつ後ろにずれる** (history は
今からしか貯まらない、§4) — 最短経路上の唯一の user 依存点。

---

## 10. 本番実証 2 バグ修正 — session 二重エンコード + fork-unsafe HTTP Session (2026-07-16, rule:R3)

credentials 投入 (2026-07-16T05:54Z) 後の初回稼働で 2 バグを実証・修正:

**(a) session 二重エンコード → 全 API "Invalid session."**
Myfxbook の session は**発行時点で URL-encoded 済み** (`%` を含む 94 文字)。
requests の `params=` 経由で渡すと再エンコード (`%`→`%25`) され、outlook が
"Invalid session." を返す。ローカル切り分けで確定: encoded 渡し=error /
**raw 渡し=成功**。修正 = `_get` を組立済み query 文字列方式に変更 — login は
urlencode (raw 値のため)、session は raw 付加。回帰 pin:
`test_myfxbook_session_passed_raw_not_double_encoded`

**(b) fork 継承 requests.Session → healed thread 無期限ハング**
gunicorn master で生成した Session の urllib3 pool lock が locked のまま
子プロセスへ複製され、self-heal 後の thread の request がブロックし続けた
(本番観測: requests_total=2 / poll_cycles=0 / last_error="" が 15 分不変。
timeout はソケット待ち専用で lock 待ちには効かない)。§8b (worker thread 死)
と同族の fork 問題の HTTP 層残存。修正 = pid 変化検知で Session を lazy
再生成 (`_http_session()`)。回帰 pin: `test_myfxbook_http_session_rebuilt_on_pid_change`

**修正版の実 API 検証 (デプロイ前、ローカル)**: login 1 回 → outlook 成功、
186 symbols、対象 6 instrument 全取得、payload keys = name/long%/short%/
volumes/positions/avgLong/ShortPrice (設計 §9 と一致)。

**教訓**: 外部 API の token/session を「再エンコードして良い raw 値」と仮定しない
— 発行値をそのまま echo する契約かを最初の統合テストで確認する。fork 問題は
thread だけでなく **プロセス間で共有される全ての stateful オブジェクト**
(HTTP Session/DB conn/lock) に及ぶ。

---

## 11. defer_thread — import 時 thread 起動の廃止 (2026-07-16 第2修正, rule:R3)

**§10 デプロイ後の観測**: master (import 時) thread の初回 cycle は成功
(saved=6, t0=2026-07-16T06:33:31Z) したが、serving プロセスの healed thread は
2 リクエスト目で再びハング (poll_cycles=0 が 30 分不変、last_error 空)。
§10(b) の pid 検知 Session 再生成では不十分だった。

**帰属**: fork の瞬間に master の thread が HTTP 実行中だと、socket/ssl
モジュール内部の lock が locked のまま子プロセスへ複製される (fork+threads の
古典問題)。Session オブジェクトを作り直しても、モジュールレベルの複製済み
lock 状態は直らない。

**根治 (構造対策)**: **master では network thread を一切起動しない**。
`start_positioning_ingest(defer_thread=True)` — schema/seed + started_at
(heal の arm) のみ行い、thread 起動は serving プロセスの初回 heal
(status()/before_request heartbeat、§8b で実装済み) に一本化。fork 時に
実行中の HTTP が存在しなくなるため、lock 複製事故が構造的に起こらない。

**可観測性**: status に `current_phase`/`phase_since` を追加 — 今後ハングが
起きても「どの step で止まっているか」が status から直接読める
(counter は fork コピーで信用できない教訓の適用)。

**教訓**: pre-fork サーバでは「import 時に起動する network thread」自体が
禁忌。§8b (self-heal) は復活経路として正しいが、fork 前に thread を走らせて
良い理由にはならない — 起動経路は serving プロセス内に一本化する。

---

## 12. instrument 拡張 6→13 (2026-07-16, rule:R3)

**動機 (最短経路)**: §8c で「history は今から蓄積する以外に入手不可」が確定して
いる以上、**将来セル候補になり得るペアは今日 clock を始めた分だけ discovery が
早く始まる**。outlook は全 symbol 一括 1 リクエスト (probe 2026-07-16:
n_symbols=186) のため、instrument 追加の API 予算コストは**ゼロ**。増えるのは
DB 行のみ (~13 rows/20min ≈ 940 rows/日、SQLite には無視できる規模)。

**追加 7 ペア** (engine モード/Phase B-1 slot が既存 = 将来 live 化の配管が存在):
AUD_USD, NZD_USD, USD_CAD, USD_CHF, NZD_JPY, EUR_AUD, EUR_GBP

**選定規準と注記**:
- EUR_GBP は live 摩擦が構造的不利 (BEV_WR 57.1%) だが、蓄積コストゼロ +
  BEV_WR は対称 R:R 近似 (lesson: 高 R:R 戦略の正エッジ誤殺) のため**データは取る**。
  live 化判断は将来の pre-reg 側で行う
- 蓄積ペア数 ≠ 検定セル数。discovery/pre-reg 時にどのペアを検定するかは
  その時点の設計が決める (多重性補正の負担はデータ保有ではなく仮説選択に付く)
- 各ペアの t0 は蓄積開始日ベース: 初期 6 ペア = 2026-07-16T06:33Z、
  追加 7 ペア = 本 PR デプロイ時刻。**pre-reg の窓設計はペア別 t0 を必ず参照**

**検証**: デプロイ後 `/api/positioning/status` の books に 13 instrument が
現れ、rows が cycle 毎に増えること。symbol 欠落は fail-loud で status に出る。
