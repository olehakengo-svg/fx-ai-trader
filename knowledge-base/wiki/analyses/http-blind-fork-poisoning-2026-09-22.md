# HTTP 全盲インシデント — gunicorn master の pre-fork 窓で SQLite が走っていた (2026-09-22, rule:R3)

**verdict: 構造バグを確定 → DailyReview スレッドを serving process へ defer (§11 パターン) + `/healthz/http` health check + 夜間 ingest パスの deploy 除外 + 検知器 `http_blind` 新設 + daily_report の原因捏造ガード**

関連: [[e1-positioning-ingest-2026-07-14]] §11 (同族の fork 問題、network 層) / [[deploy-churn-trading-gap-2026-08-21]] / [[disk-full-write-outage-2026-08-26]] / MEMORY `project_monitoring_blind_during_outage_2026_08_30` / `project_engine_reconstruction_live_dedup_dead`

## 0. 要約 (3 行)

1. Render の gunicorn は app.py を **master (PID 39) で import** し、その 20〜300 ms 後に HTTP worker を fork する。`DemoTrader.__init__` (= import 時) が起動する DailyReviewEngine スレッドは、**UTC 0 時台の起動では即座に**前日レビュー (24 モード × 全件スキャン) + C1 prune + 204 MB backup を master で回す。
2. fork がその最中に落ちると、子 (= worker) は SQLite のプロセス共有 mutex を locked のまま継承し、**DB を触る全 HTTP ルートが永久ハング**する。gthread の main loop は `notify()` を続けるので `--timeout 120` は発火せず、Render は TCP 疎通しか見ないため **3h19m〜3h31m** 放置された。**3 回発生** (09-12 / 09-15 / 09-22)、いずれも 0 時台デプロイ直後。master 側のエンジンは全期間 tick し続けていた (= 「engine は生きていて HTTP だけ盲目」)。
3. 副産物として **エンジンが master と worker の 2 プロセスで二重に走っている**ことを確定 (§6)。本 PR では修正せず registry に disposition 期日を置いた。

## 1. タイムライン (UTC、Render request/app ログ実測)

### 1.1 2026-09-22 (本件)

| 時刻 | 事象 | 出所 |
|---|---|---|
| 00:03:10 | 旧 instance `2c8lt` 最後の 200 (edge-cell-watchdog, 2.8 MB) | request log |
| 00:04:04→00:06:06 | deploy `85a823ce` "auto: rate anchor daily ingest" → instance `rtlsn` | deploy 一覧 |
| 00:05:56 / 00:05:56〜00:06:01 | `rtlsn` worker fork / `[Backup] Created` (fork は backup 窓の中) | app log |
| 00:06〜00:12 | `rtlsn` への外部リクエストは **0 本** (cron の谷) → 盲目か否か**判定不能** | request log |
| 00:12:50→00:14:47 | deploy `05450797` "data(mof-statements): daily collect" → instance `stfml` | deploy 一覧 |
| 00:14:41.75 | `[migration/dedup_backfill] starting...` (import 開始域) | app log |
| 00:14:46.16 | `[AutoStart] Waiting 5s ... (PID=39)` — **app.py は master (PID 39) で import 済み** | app log |
| 00:14:46.45 | `[positioning] thread start DEFERRED` = import 終了 | app log |
| **00:14:46.47** | `[131] Booting worker with pid: 131` = **fork** | app log |
| 00:14:42→00:14:51 | DailyReview: `_execute_daily_review` (24 モード全件スキャン) → `Completed review` 00:14:51.16 → `[Backup] Created` 00:14:51.39 (204 MB) → **fork は review の最中** | app log |
| 00:14:51.92 | `127.0.0.1 "HEAD / HTTP/1.1" 200` — worker は **DB を触らないルートなら応答できた** | gunicorn access log |
| 00:15:28 (499 @00:15:43) | 最初の外部リクエスト `/api/demo/trades?limit=500` が 15 s で client 切断 — 以後 **全 DB ルートが 499** | request log |
| 00:15〜03:33 | `[MainLoop] iter=…` / `[Watchdog/HB]` は**連続前進** (iter=2430 @02:00, 4440 @03:31)。`[API-SLOW]` **0 行** = ハンドラは「遅い」のではなく**戻らなかった**。`WORKER TIMEOUT` **0 行** | app log |
| 03:32:53〜03:33:26 | Render edge が 502 を返し始める (upstream から即時エラー、516 ms) | request log |
| **03:33:27** | `[39] Handling signal: term` — Render がインスタンスへ SIGTERM (deploy ではない) | app log |
| 03:33:38→03:33:45 | 同 instance 名 `stfml` で再起動 (PID 39 が再び master)、fork 03:33:45.44 — **0 時台でないので review は走らず**、fork 窓に SQLite なし | app log |
| 03:35:55 | 最初の 200 (`/api/demo/trades` 332 ms) | request log |
| 03:35:56 | `[StatusHeal] MainLoop dead — restarting` + 24 モード → **worker 側にも 2 本目のエンジン**が立つ (§6) | app log |

メモリ 562 MB / 4 GB (OOM ではない)。deploy 03:56 / 04:09 / 06:01 は PR マージ。

### 1.2 同型の過去 2 件 (本調査で発見)

| 日付 | deploy (UTC 0 時台) | fork | Review/Backup 窓 | 最後の 200 → SIGTERM | 全盲時間 |
|---|---|---|---|---|---|
| 09-12 (土) | 00:00:56→00:03:21 | 00:03:12 | 00:03:12〜00:03:18 | 00:01:05 (旧 inst) → 03:34:50 | **3h31m** |
| 09-15 | 00:25:56→00:27:34 | 00:27:33 | 00:27:33〜00:27:39 | 00:25:53 (旧 inst) → 03:49:43 | **3h22m** |
| 09-22 | 00:12:50→00:14:47 | 00:14:46 | 00:14:42〜00:14:51 | 00:14:51 (HEAD /) → 03:33:27 | **3h19m** |

**対照**: 0 時台デプロイでも 09-16 (00:05) / 09-17 (00:14) / 09-18 (00:02) / 09-19 (00:01) は起動 ~10 分後に 200 を返した (fork は同じく review 窓内)。0 時台以外の起動 (09-21 ×4, 09-22 03:33 / 03:56 / 04:09 / 06:01) は **全て正常**。⇒ **0 時台起動 7 件中 3 件 (43%) が盲目、0 時台以外は 0 件** — 確率的な fork-into-held-mutex と整合。

## 2. 症状の estimand 分離

| 観測 | 意味 |
|---|---|
| `HEAD /` 200 (DB 非依存) | worker プロセス・Flask・before_request 連鎖は生きていた |
| `/api/demo/trades`, `/api/oanda/status`, `/api/demo/status`, `/api/admin/disk_status`, `/api/positioning/status`, `/api/admin/edge_cell/state` 全て 499 | **共通因子 = fresh `sqlite3.connect` or `_demo_db` 経由の SQLite** (各ハンドラのコード読みで確認)。5xx ではないので例外ではなくハング |
| `[API-SLOW]` 0 行 | after_request に到達していない = ハンドラ未完了 |
| `WORKER TIMEOUT` 0 行 | gthread main thread は `notify()` を続けた。`--timeout` は **main thread が止まったときだけ**効く (gunicorn `ThreadWorker.run` を読了) |
| `[MainLoop]` 連続 | エンジンは **master** で走っていた (worker では StatusHeal が 1 度も走っていない = 1 本も 200 が無かったので、worker 側エンジンは存在しなかった) |
| memory 562 MB / 4 GB | OOM ではない |

## 3. 根本原因の導出

### 3.1 プロセスモデル (実測)
- `[AutoStart] Waiting 5s ... (PID=39)` と `[39] [INFO] Starting gunicorn 26.2.0` / `Listening at` が**同じ PID 39** → app.py は arbiter (master) で import されている (preload 相当。Render の gunicorn 26.2.0 は `/opt/render/.gunicorn/gunicorn.ctl` control socket を持つ。ローカル gunicorn 23.0 の `Arbiter.setup` は `preload_app` 時のみ `app.wsgi()` を呼ぶ — Render 側の設定は非公開だが**挙動としては preload**)。
- KB [[e1-positioning-ingest-2026-07-14]] §8b/§11 は 2026-07-14/16 に同じ事実 (fork コピー・thread が serving process に残らない) を観測し、**network thread** を serving process へ defer した。**DB thread には同じ処置がされていなかった**。

### 3.2 fork 窓に何が走っていたか
`DemoTrader.__init__` → `self._daily_review.start()` → `_scheduler_loop`: `if now.hour == 0 and _last_review_date != today` → **起動直後に**レビュー。3 件とも `[DailyReview] Completed review` / `[Backup] Created` の時刻が fork を挟んでいる (§1.1/1.2)。他の import 時スレッド (autostart は 5 s sleep 中 / HMM autofit は価格データ / cfd scheduler は idle / OandaBridge は idle) は fork 時点で SQLite を触っていない。

### 3.3 なぜ「ハング」で「例外」ではないか
SQLite は unix VFS の inode/shm 情報とメモリ統計 mutex (`mem0.mutex`、既定 `SQLITE_DEFAULT_MEMSTATUS=1` で**全 malloc が通る**) を**プロセス共有**で持つ。fork は親スレッドが保持中の pthread mutex を locked 状態でコピーし、子にはそれを解放するスレッドが存在しない → 子の最初の `sqlite3_open`/alloc が `sqlite3_mutex_enter` で**永久待ち** (busy_timeout はロック競合用で、mutex 待ちには効かない)。親 (master) は無傷。これが「HTTP 層だけ死ぬ / 5xx が出ない / master エンジンは元気」を全て説明する。

**局所再現 (macOS, Python 3.9, SQLite 3.43.2)**: 親で backup + 読み書きスレッドを回しながら 60 回 fork → 子の fresh 接続が **6/60 (10%) で `disk I/O error`**、対照 (親スレッドなし) は **0/60**。macOS では失敗モードが例外 (Linux の mutex 継承と挙動が違う) で、**ハングそのものの Linux 再現は未実施**。本番 3/7 (43%) との差はレビューが alloc 集約的で保持率が高いことで説明可能だが、**比率は引用禁止** (n が薄い)。

### 3.4 なぜ 3h20m で Render が再起動したか (推定、契機は Render 非公開)
gthread は `accept()` ごとに `nr_conns += 1` し、完了しないハンドラの future は永久に減算されない (`finish_request` 未到達)。`nr_conns >= worker_connections (既定 1000)` で **`accept` を止める** → kernel backlog が埋まり TCP 疎通が落ちる → Render が unhealthy 判定 → edge 502 (03:32:53〜) → SIGTERM (03:33:27)。3 件とも外部リクエスト ~310 本 + Render/edge の probe 接続 (推定 ~17 s 間隔) で ≈1000 に到達する 3.3 h と整合。**検証は未了** (probe 間隔は Render 非公開)。

## 4. 修正 (rule:R3 — 取引パラメータ・gate・lot 不変)

| # | 変更 | 根拠 |
|---|---|---|
| F1 | `DailyReviewEngine.start(defer=True)` を `DemoTrader.__init__` で使用。実起動は app.py `_positioning_heartbeat` (before_request) → `DemoTrader.ensure_daily_review_running()` → `ensure_running()` | §11 と同じ「serving process で heal 起動」。request を処理するプロセス = fork 後の worker が構造的に保証される。StatusHeal (`get_status`) からは呼ばない — master 側 AutoStart/Verify も呼ぶので master に戻る |
| F2 | `/healthz/http` (fresh `sqlite3.connect` + `SELECT name FROM sqlite_master LIMIT 1`、StatusHeal/tick 非接触) + render.yaml `healthCheckPath: /healthz/http` | ハングした worker では connect 自体が返らない → health check timeout → 数分で再起動。/healthz を使わない理由: StatusHeal 副作用で worker エンジン起動が決定的になる (§6) |
| F3 | render.yaml ignoredPaths += `data/external/rate_anchor/**`, `data/external/mof_statements/**`, `data/cache/yield/ZN_F_1h.parquet` | 夜間 ingest 2 commit (21:15Z / 21:30Z) が**毎晩 2 回**エンジンを再起動していた。app/modules/strategies からの参照ゼロ (全数 grep、pin: `test_nightly_ingest_data_paths_are_ignored`)。`data/cache/yield/*.json` は取引パス read なので**ディレクトリごと ignore しない** |
| F4 | `freshness_policy.classify_fetch_failure / classify_outage` (SSOT) + anomaly_watcher `http_blind` イベント | 全滅かつ全て read-timeout = 接続成立・無応答 = **プロセスは listen / HTTP 層のみ死** ↔ 接続拒否 / 5xx = api_down。**engine の生死は外部から不明**と明記し Render ログ [MainLoop] へ導く |
| F5 | daily_report: `FetchResult` (ok/payload/error_class 分離) + DATA FETCH テーブル (決定的) + 規則 5 + 原因捏造の出力後検査 → 生成器注記で訂正 | 09-22 03:11Z レポートは「Render 無料 tier のスリープ」(Pro plan、存在しない原因) を書いた。原因は観測から導けない → 「unreachable, cause unknown (class)」のみ |

**trade-off (F2)**: health check 由来の再起動は in-memory dedup/cooldown を消す (MEMORY `project_engine_reconstruction_live_dedup_dead`、commit `ebf4a5235`)。ただし再起動が起きるのは HTTP 層が既に死んだ状態 = 監視・OANDA 監査・edge-cell watchdog が**全て盲目**の状態であり、dedup は起動時 DB hydrate (`[startup/dedup_hydrate]`) を持つ。3 時間の全盲より安い。

**レビュー消化 (Codex P2 × 2、どちらも正しかった)**: (a) `classify_outage` が「timeout ゼロ」の混在を全て api_down に畳んでいた — `connection + JSON 壊れ` や `全 endpoint 401` が「プロセス停止」と報告される。⇒ api_down は connection / 5xx **のみ**の集合に限定し、4xx は `FAIL_HTTP_4XX` / 全 4xx は `http_error` (serving 中)、それ以外は mixed。(b) 捏造ガードが analyst_report だけに掛かり、その本文を入力に受け取る strategy planner が同じ捏造を再生産できた ⇒ 両レポートを同じ出口 `finalize_llm_report` に通し、planner prompt にも原因禁止規則を追加。🔑 「片側だけ塞いだ fail-closed」の再演 (MEMORY `feedback_check_the_symmetric_side_2026_09_19`) — 同じ PR の中で 2 回目。

**レビュー消化 3 巡目 (Codex P2 × 3、いずれも正しい)**: (c) `preprocess_fetch_status` / watcher が**失敗した部分集合だけ**を `classify_outage` に渡していた — 1 本の timeout + 4 本成功で「HTTP 全盲」と要約。⇒ `classify_outage(reasons, n_ok=)` に成功数を渡し、n_ok>0 は `partial` (endpoint 固有) に限定。(d) 公開 URL (`*.onrender.com`) への read-timeout は **edge までの接続**しか証明しない — edge→origin が 502 を返さず停止しても同じ観測。⇒ `http_blind` を「観測クラス」に格下げし、summary / event 文言から「プロセスは listen 中」を除去、Render health check と app ログでの裏取りを明記 (09-22 の listen 判定は `HEAD /` 200 と `[MainLoop]` から)。(e) 捏造ガードが fetch 成功時にも掛かり、否定文 (「スリープではない」「ruled out」) も脚注していた。⇒ `finalize_llm_report` は `n_failed>0` のときだけ、判定は文単位で否定マーカーを除く `freshness_policy.find_invented_causes` (SSOT)。英語パターンは `sleep` 単語から句 (`sleep mode` 等) へ。

**レビュー消化 4 巡目 (Codex P2 × 2、いずれも正しい)**: (f) 5xx を全て「origin 応答なし」に数えていた — app 由来の 500 (Flask hook の例外等) でも「停止」と報告される。⇒ `api_down` は **connection のみ**、全 5xx は `http_5xx` (応答あり、edge 502/503/504 か app 500 かは状態コードで判別不能 — app ログの traceback で裏取り)。(g) 否定判定を文全体で見ていたため「ネットワーク障害ではなく、無料 tier のスリープが原因」が否定文として素通りした。⇒ 否定は**原因語と同じ節** (、/,/; 区切り) にあるときだけ効く。🔑 4 巡で 7 件、全て estimand 境界: 「何が観測され、何が含意されるか」を 1 対 1 で書き、含意を観測の名前に混ぜない。

**レビュー消化 5 巡目 (Codex P2 × 2、いずれも正しい)**: (h) 分類器は `http_error` / `http_5xx` を返すのに、watcher が両方を `api_unreachable` に畳み、通知文が「到達できない → サービス/デプロイ復旧」へ誘導していた (全 401 = 認証切れを見誤る)。⇒ 応答あり失敗は専用 event `api_http_error` (4xx は認証/パス、5xx は edge/app 判別不能と明記)。(i) 否定判定を節単位にしても「API が応答**しない**のはスリープが原因」の汎用「しない」が原因語を隠した。⇒ 否定は**原因語そのものに結び付く形** (直後窓の「ではない」等 / 英語の前置 not) だけを認める — 文単位 → 節単位 → 語束縛と 3 段で狭めた。🔑 5 巡 9 件: 分類の後段 (通知文・ガード) は分類器と**同じ粒度**を保たないと、前段で分けた情報を後段が再び畳む。

**レビュー消化 6 巡目 (Codex P2 × 1、正しい)**: (j) プローブ文 `SELECT 1` は定数評価で **DB の読取りロックを取らない** — ファイルロック / 詰まったトランザクションで DB ルートが全滞留していても 200 を返し、Render は再起動しない。⇒ `SELECT name FROM sqlite_master LIMIT 1` (shared lock + page read = DB ルートと同じ資源で待つ)。fork 中毒の場面では connect 自体が返らないので両者に差は無いが、health check の estimand を「DB を実際に読めるか」に揃えた。

**counterfactual pin** (tests): `test_daily_review_fork_safety.py` (construction で thread 起動なし / heal 冪等 / heartbeat 到達 / StatusHeal 非接触)、`test_http_blind_detector.py` (ReadTimeout 全滅 → `http_blind`、5xx → `api_unreachable`、混在 → mixed、SSOT 使用)、`test_healthz_http.py` (200 + db_ok / StatusHeal 非接触 / healthCheckPath 配線)、`test_daily_report_fetch_status.py` (失敗と空の分離 / 原因語ゼロの prompt 実捕捉 / 捏造検出→脚注)、`test_render_build_filter.py::test_nightly_ingest_data_paths_are_ignored`。

## 5. 残余リスク (修正していないもの)

1. **master エンジン下での worker 再 fork**: autostart のエンジン (24 thread、SQLite 常時稼働) は依然 **master** で走る。gunicorn が worker を再 fork する事象 (worker crash / `WORKER TIMEOUT`) が起きれば、**ほぼ確実に**同じ全盲が再発する。実測では再 fork は起きていない (Booting worker は起動時のみ)。F2 が発生時の被害を数分に短縮する。根治は §6 の disposition。
2. Render 再起動契機 (§3.4) は推定。F2 で契機自体を置き換える。
3. `nav_floor_projection.csv` の 09-22 行欠落は fetch 失敗の直接結果 (未修正・KB 記録のみ)。

## 6. 副産物: エンジンが master と worker で二重に走っている (要 disposition)

- 証拠 A: 全盲期間 (00:15〜03:33) は worker で **1 本も** リクエストが完了せず StatusHeal は走っていないのに `[MainLoop] iter=` は前進 → **master のエンジン**。
- 証拠 B: 03:35:56 `[StatusHeal] Healed: ['MainLoop', 'Watchdog', 'SLTP', 24 modes]` 以後、`[MainLoop] iter=240` が **03:45:27 と 03:46:15 に 2 回** (ticks 値が異なる = 別プロセスの別カウンタ) → **master + worker の 2 エンジン**。
- 含意: 同一シグナルを 2 プロセスが評価・emit する。in-memory の `ORDER_BAR_DEDUP` はプロセス内のみ。DB write-time の `dedup_violation` フラグ (PR #220 系、`tests/test_shadow_dedup_write_time_flag.py`) はクロスプロセス dup を**フラグする**が**防がない**。LIVE 送信の二重化リスクは未評価。`/api/demo/status` が返すのは worker 側エンジンの状態のみで、master エンジンは API から不可視。
- app.py:13855-13859 / §11 の当時の解釈「demo_trader が生きているのは StatusHeal のおかげ」は**不完全**だった — master でも生きていた。
- **本 PR では変更しない** (プロセス配置の変更は shadow N の生成率を変える regime break を伴い、pre-reg 群の窓設計に触る)。registry `dual-engine-master-worker-disposition` (期日 2026-10-06) で (a) dup 率の実測 (b) 単一エンジン化 (gunicorn `post_worker_init` で worker 起動 / master は import のみ) の設計と regime break の記録方法を決める。

## 7. 教訓

- **pre-fork サーバでは「import 時に起動するスレッド」は network も DB も禁忌** — §11 は network だけを塞いだ。「対称に処置せよ」(MEMORY `feedback_check_the_symmetric_side_2026_09_19`) の 3 例目: 同じ fork 問題が resource の種類を替えて再発した。
- **`--timeout` は worker main thread の生存しか見ない**。gthread のハンドラ全滞留は gunicorn からも Render (TCP) からも見えない。HTTP health check は「必要なら設定」ではなく「無いと数時間盲目」。
- **外部から見えるのは失敗クラスだけ**。read-timeout と connection error は別の estimand。LLM に「原因」欄を埋めさせるなら、材料が無いことを材料として渡す。
- 月 1 回級の確率的事象は「直後に 200 が返った」1 回で否定できない。0 時台起動 7 件を並べて初めて 3/7 が見えた。

## 8. 検証計画

- registry `http-blind-fix-verification-hour0-boots` (期日 2026-10-06): 0 時台デプロイ ≥3 件で (a) `[DailyReview] starting scheduler in serving process` が worker 側で出る (b) 起動 ≤10 分で 200 が返る (c) `[Backup] Created` が fork より後。1 件でも盲目なら §3.3 の帰属を再検討 (他の import 時 SQLite 経路を疑う)。
- `/healthz/http` の Render health check が deploy を妨げないこと (deploy 後 `Your service is live` までの時間を従来と比較)。
