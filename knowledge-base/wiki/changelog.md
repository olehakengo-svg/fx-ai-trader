# Changelog — バージョン別変更と評価基準日

<<<<<<< HEAD
## 2026-09-24 — fix(render): 日報 commit の F4 CSV (`data/monitoring/**`) を ignoredPaths へ — 本番を 1 日 4 回再デプロイしていた取りこぼし (rule:R3)

- **実測**: Render deploy 一覧 (09-23T05:27 → 09-24T03:02) の 5 件中 4 件が `docs(KB): daily report` commit 起点 (00:20Z / 03:02Z / 11:12Z / 19:22Z)。commit 内の `data/monitoring/nav_floor_projection.csv` (F4 資金時計、`daily-report.yml` が `--append`) 1 パスだけが ignoredPaths に無かった。web プロセス非参照 (app.py / modules/ 出現ゼロ)、読み手は tools + registry csv_row_match (cron 側)
- **害**: 1 日 4 回のエンジン再起動 (二重エンジン再生成 + in-memory 状態リセット) + **00:20Z boot = fork 窓 hour-0 の再露出** ([[http-blind-fork-poisoning-2026-09-22]] §3.3)
- **対策**: `data/monitoring/**` 追加。pin `tests/test_render_build_filter.py::test_daily_report_monitoring_csv_is_ignored` (ignore / 読み手ゼロ / `data/cache/**` 非巻き込み)。詳細 [[deploy-churn-trading-gap-2026-08-21]] §9 / [[dual-engine-dup-rate-readout-2026-09-24]] §7
=======
## 2026-09-24 — fix(engine): 二重エンジン (gunicorn master + worker) のプロセス帰属計装 + dup 率/LIVE 二重送信の実測 — registry 10-06 disposition の (1)(2) 前倒し (rule:R3)

- **背景**: [[http-blind-fork-poisoning-2026-09-22]] §6 で「取引エンジンが master と worker の 2 プロセスで走っている」を確定したが、dup 率・LIVE 二重送信リスク・単一化の regime break は未評価だった (registry `dual-engine-master-worker-disposition`、期日 10-06)
- **実測 (30d、本番 API + Render ログ)**: 現行 instance でも `[MainLoop] iter=810`/`630`/`840` の 2 カウンタ、`tick #70` と `tick #50` が 1.0 秒差で**二重は現在も継続**。shadow 近接ペア (同 type×pair×dir、Δ≤45s) **133 ペア/30d = kept 1,670 行の 8.0%**、全取引日 3–17 ペアで恒常。**両方 `dedup_violation=0` は 0 ペア** = write-time フラグ (2026-09-02) が cross-process dup を全件捕捉 → **dedup=0 の N は非膨張**。**LIVE 二重送信 0 件** (live 11 行に Δ≤120s twin なし、audit sent 12 / filled 11 の差 1 は 09-06 wg 既知)。自然実験: master 単独の HTTP 全盲窓 (09-15/09-22 00:15–03:33Z) の kept 行 **12 / 10** vs 二重平日同窓 平均 **9.75** (N=2、記述級) = 単一化で生成率が落ちる兆候なし。機構: count ゲートが DB の `get_open_trades()` を読むため 2 本目は race 窓以外 block される
- **計装 (record-only、取引挙動・gate・dedup 不変)**: `engine_process_role()` (import 時 PID 凍結、`import`=master / `forked`=worker) + 起動経路 `_engine_start_origin` (`autostart` = app.py import 時 thread、モード起動前に刻む / `statusheal` = MainLoop 再起動分岐) → 両方の `open_trade` call site で row reasons に `[EMIT_PROC] <role>:<origin>` marker / `[MainLoop] iter=`・tick・`[StatusHeal] Healed`・`[AutoStart] Starting` に `pid=`/`role=`/`origin=` / `get_status()` に `engine_pid`・`engine_process_role`・`engine_import_pid` (self-check 用)・`engine_start_origin`
- **pin**: `tests/test_dual_engine_process_attribution.py` 17 本 (role 2 値を**実 fork**で検査 / marker に PID 桁なし / origin が autostart・statusheal で刻まれる / call site 2 箇所の対称 append / record-only / ログ 4 行 / status 4 key / 永続 row の marker 両側)。counterfactual: 片側の append を外すと 3 本落ちる (pycache purge、sha 一致 restore)
- **Codex review P1 (4089913868) 消化**: 「gunicorn 既定では worker が import するので `_MODULE_IMPORT_PID` が worker 自身になり `forked` が現れない」— 本番ログは master import (AutoStart PID=64 → 0.3 秒後 `Booting worker with pid: 131`) を示すが、**トポロジ前提に依存して黙って誤分類する設計**である点は正しい → origin 軸 (起動経路の事実) を併記 + status `engine_import_pid` で読み手が self-check + 実 fork テスト
- **設計 (別 PR)**: 案 A = `gunicorn.conf.py` `post_worker_init` で worker 起動、master は import のみ、StatusHeal は残す。層別 = marker (一次) + deploy 時刻 (二次)。user 決裁不要 (Rule 3 ∧ N 非膨張・非低下) — 統合パケットに **D16 record** を追加。registry: 親 entry 追記 + `dual-engine-emit-proc-attribution-readout` (10-01) 新設
- **副産物**: `docs(KB): daily report` commit が `data/monitoring/nav_floor_projection.csv` (ignoredPaths 漏れ) で**本番を 1 日 4 回再デプロイ** (00:20Z boot = fork 窓 hour-0 の再露出) → 別 PR で ignore 追加
- **引用規律**: 「二重で shadow N 2 倍」は禁止 (膨張は dedup 込み生 row の +8% のみ) / 自然実験は記述級 / 09-24 以前の row は marker `none`
- 詳細: [[dual-engine-dup-rate-readout-2026-09-24]]
>>>>>>> origin/main

## 2026-09-23 — fix(nav_floor): F4 資金時計の edge 残差から入出金 (OANDA TRANSFER_FUNDS) を差し引く — 入金で F4 が最長 30 日盲目化する構造バグ (rule:R3)

- **欠陥**: `edge_jpy = (nav_now − nav_start) + keeper 窓内支出` は broker NAV Δ の残差で、入出金調整が repo 全体で 0 件。入金 ¥D が窓 (30 日) に入ると burn_edge −D/span (¥100k → −3,333/日 ≫ keeper 68.3) で合計 burn ≤ 0 → `project()` が sentinel 99999 → registry F4 (≤90 日) が発火不能、窓を抜けると逆に跳ねる。出金は偽早期発火。[[path-to-win-reassessment-2026-09-22]] §9-5 / [[integrated-decision-packet-d1-d12-2026-09-22]] D1 (入金が M2 を虚偽達成) と同根 — U3 入金の決裁時にこそ壊れる
- **修正**: 本番 `GET /api/oanda/transfers?from&to` (app.py、read-only、`OandaClient.list_transactions_full` = TransactionList pages → idrange) から窓内 TRANSFER_FUNDS を取り `edge_jpy` から差し引く。bridge に `heartbeat.nav_at` (成功 heartbeat で nav と同時にだけ更新) を追加 — 失敗 heartbeat の `last_check` を NAV の時刻と読むと障害中に窓境界がずれる (PR #295 P2)。窓の両端は **NAV 採取時刻** (heartbeat.nav_at [成功 heartbeat で nav と同時にだけ更新、PR #295 P2] → 新列 `nav_ts_utc`、既存 6 列不変) で判定、時刻の無い legacy 端の同日 tx は unavailable (両端対称)。台帳取得不能は `unavailable:transfers_unavailable` (入出金ゼロと偽らない、keeper 分は残る)。basis に `transfers_jpy=±X,n_transfers=k`
- **pin**: `tests/test_nav_floor_projection_f4.py` §14 (11 本: 入金 ¥100k / 出金 ¥50k で burn 不変・窓の出入りで跳ねない・台帳なしで sentinel = 既知 NG・境界 fail-closed・main 配線・route 配線・registry) + client 3 本 + route 5 本。counterfactual 2 本 (差し引き除去 → 4 本落ち / None をゼロ扱い → 1 本落ち、pycache purge + sha 一致 restore)。全 suite 3,924 passed
- **移行**: route は merge → Render deploy 後に生きる (それまで keeper のみ = 現状値と同じ)。legacy 行が start_row の間 (10 月下旬まで) は start 日に入出金があれば unavailable。発火日再現値 (09-22) は入出金ゼロ前提で不変。registry F4 message 追記 (condition 不変)
- 詳細: [[nav-floor-f4-transfer-funds-adjustment-2026-09-23]]

## 2026-09-23 — fix(engine): 送信前拒否・shadow 化の観測性 5 件を修復 — weekend_gap_fade / 共有 `_tick_entry` 経路 (rule:R3、PR #293)

- **背景**: [[weekend-gap-execution-modality-r1-redraft-DRAFT-2026-09-22]] §2「不成立 (v) PRE_SEND_GUARD」行 (PR #289、Codex 3 巡 + 敵対的レビュー) が確定した帰属欠陥 — G0' event #2 (09-27 21:00Z) が broker 到達証拠なしで終端した場合、亜種 (a)〜(d) を事後に識別する一次ソースが (a-後) `order_bar_dedup` 上書き / (b) 8000 行刈り込み DB logs のみ / (c3) 無記録 / (d) 現在 mode からの推定、で欠けていた。分析: [[pre-send-guard-observability-r3-2026-09-23]]
- **変更 (record-only、判定・戻り値・is_shadow 最終値・行数は不変)**: (1) demo_trader pre-check (`_bridge_active` 偽 / `is_mode_allowed` 偽) を bridge 拒否経路と対称に shadow 化 (`_exposure_mgr.set_shadow_status` + `[SHADOW_FIX] Pre-send guard` ログ); (2) `OandaBridge.open_trade` の無 audit False 経路 3 つに `blocked` audit (`bridge_inactive_race` / `mode_<mode>_not_allowed_race` / `unsupported_instrument(<inst>)`); (3) `_is_promoted_ex` の block cause を event 時点で row reasons `[PROMO_BLOCK] <cause>` + audit `shadow_tracking(promo_block:<cause>)` + DB log に永続 (全 flip 完了後の 1 箇所、`_shadow_at_open` 偽 ∧ 最終 shadow ∧ 非 promoted ∧ shadow_only mode でない); (4) `[SHADOW] <gate> bypass:` 23 サイトで row reasons に `[SHADOW_BYPASS] <gate>` (`[SHADOW_RELAX]` と同型、`max_open` の無ログ shadow 化にもログ追加); (5) order-bar 予約後の最初の terminal `_block` を `gate_block_daily` reason_key `order_bar_dedup_first:<reason_key>` に 1 回だけ永続 + dedup ログに `first_block=` 併記 (既存 reason 正規化、キー空間は既存 reason 数で有界)
- **DRAFT 訂正 2 件 (テストで実測)**: (c2) の「`oanda_trade_id` 空の非 shadow row が残る」は DB row については 48025ebd3 (2026-05-11 write-time invariant) 以降 stale — 欠陥は in-memory / ExposureManager / marker ログ側。(d) の「`[SHADOW_FIX] Post-gate escalation` が event 時点記録」は mode_off では発火しない (無ログの v8.9 fallback 7680 が先に shadow 化) — 一次ソースを `[PROMO_BLOCK]` marker / audit variant へ差替え。§2 (v) 行 / §6 転記項目 / §7 禁止事項を新観測面に同期、凍結値・分類・消費規則は不変
- **pin**: `tests/test_pre_send_guard_observability_r3.py` 26 本 (review P2 消化 4 本を含む) — counterfactual 10 (修復前 RED を実測) / 対称側・恒真でない側 10 (bridge 拒否・accept 経路 / daily-loss `blocked` 1 行 / gate 通過 `blocked` 0 行 / promoted row に marker 無し / 上流 bypass row の audit 素の shadow_tracking / 非 sentinel hard block 不変 / 予約前・bar_ts なし block は未記録 / サイト数 23 スコープ) / **shadow_only 母集団不変 2** (rnb relax 行 1 行・`[SHADOW_RELAX]` 従来どおり・新 marker 無し / daytrade_audjpy は mode off でも 1 行・素の shadow_tracking・`[PROMO_BLOCK]` 無し)。関連既存 22 ファイル 322 本 + full suite 通過
- **Codex review P2 (4078290940) 消化**: `session_filter` の audit は legacy `shadow_tracking(session_filter_out)` (P-V4 契約、exact pin) のまま維持し、消費側正規化 helper `promo_block_cause_from_audit()` (legacy alias → `session_filter`、`promo_block:<cause>` → `<cause>`) + session_filter 行の pin (legacy audit key ∧ row `[PROMO_BLOCK] session_filter`) を追加。DRAFT §6 (d) に alias 読み替えを明記。**2 巡目 P2 (4078373240) 消化**: (d) 帰属条件の「書込み時 live 意図」を可変の `_shadow_at_open` (trip / GRAIL・C1・PRIME / FD 最終ゲートが書き換える) から不変 snapshot `_live_intent_at_open` へ — live 復活後に FD 最終ゲートで shadow 化される row (`[PROMO_BLOCK] force_demoted`) の取り逃しを修正、実機構順序 (GRAIL → `[FORCE_DEMOTED_GATE]`) を踏む pin を追加。**3 巡目 P2 (4078430621) 消化**: first-block 記録を終端 `_block` に限定 (`terminal=False` は非終端の `session_filter_live_downgrade` 1 箇所のみ) — 成功した shadow 降格を偽の first terminal block として記録していた
- 残置: 永続 first-qualification ts (DRAFT §4 row 8、別 R3) / SHIELD・VWAP trip 由来 escalation の audit variant / 2026-09-23 以前の row は従来どおり `bypass:UNKNOWN` `promo:UNKNOWN`
## 2026-09-23 — fix(engine): WAIT tick が count ゲートの block 帰属を汚染していた — 計数器契約バグ 3 例目 (rule:R3)

- **発見**: `_tick_entry` の `if signal == "WAIT": return` guard (コメント「WAITはカウントしない（大半がWAIT）」) が 3 つの count ゲート (`max_per_mode_pair` / `hedge_block` / `max_open`) の**後ろ**にあり、建玉がある限り WAIT tick が毎 tick それらの理由名で計上されていた。`hedge_block` の述語 `_ot["direction"] != signal` は signal="WAIT" で**恒真**、`max_open` の述語は signal 非依存
- **本番実測** (`gate_block_daily` 30d、2026-08-24〜09-23): `hedge_block` 59,881 件中 **55,219 件 (92.2%)**、`max_open` 6,501 件中 **5,928 件 (91.2%)** が entry_type unknown/wait。**他の 20+ reason は汚染 0.0%** — 汚染は「WAIT で述語が真になるゲート」に厳密に限られる
- **補正後の順位**: `hedge_block` は **#1 (27.3%) → #5 (3.0%)** へ降格。真の #1 は `r2_shadow_demoted_cell` (36.4%)、以下 `no_signal` (25.0%) / `order_bar_dedup` (24.9%) / `score_gate` (6.4%)
- **estimand 検査**: `_record_entry_block` は `reason.split('(')[0]` で引数を捨てるためカウンタ自身は `:WAIT` を区別できない。判別は別経路で確定 — entry_type unknown/wait が現れる reason は `hedge_block` と `max_open` の **2 つだけ**で、方向や実体を要求する 20+ の reason には 1 件も現れない / 30d の記録 trade 1,800 本に unknown・wait は **0 本**。⚠️ Render ログの `:WAIT)` grep 0 件は**反証にならない** (`SENTINEL_BLOCK_DIAG` は sentinel entry_type にしか出ない)。実 entry_type で WAIT を返す戦略がある分、真の件数 4,662 / 573 は**上界**
- **修理**: guard を 3 つの count ゲートの直前へ移動。**取引挙動は不変** (WAIT は元々エントリーしない / 移動区間に予約・dedup・DB 書込みの副作用なし)、変わるのは block カウンタと 3 ゲートの診断ログのみ。汚染ゼロだったゲート (`score_gate` / `r2_shadow_demoted_cell`) は guard より前のまま = スコープ最小化
- **pin**: `tests/test_wait_tick_block_attribution.py` 6 本 — 振る舞い 2 (count ゲート不計上 / trade・送信ゼロ) + **NG を返す既知の入力** (本物の逆方向 SELL は従来どおり `hedge_block`、「全部素通し」でも通るテストにしない) + 性質 3 (順序 / 出現回数 1 / 汚染ゼロゲートが guard 前のままというスコープ pin)。**counterfactual 実測** (bytecode purge 後): guard を旧位置に戻すと 2 本が落ち、本番と同型の `hedge_block(daytrade/USD_JPY:WAIT)` を返す。挙動不変 pin は両方で通る
- **引用規律**: 2026-09-23 より前の `hedge_block` / `max_open` の**件数**は WAIT を除いた再計算なしに引用しない。他 reason の件数は汚染ゼロでそのまま引用可。消費者への caveat 追記は registry `block-counter-wait-contamination-recite-audit` (期日 10-13) が読む。⚠️ [[ps-seat-supply-remeasure-2026-09-10]] §8 の**結論** (hedge_block 寄与 = 0 本) は `MODE_CONFIG` の構造由来で**本汚染では覆らない** — 覆るのは併記された件数のみ
- **副産物 (未執行・R1 候補)**: hedge 抑制の継続長は dedup の 60s ではなく**建玉保有時間** — 中央値 **22.0 分** (2026-04-30 H2 が置いた上界 60s の約 22 倍) / p90 132.2 分 / max 720 分 / **≤60s は 1.61%**。片方向被拘束は daytrade/USD_JPY 218.0h (窓 720h の 30.3%、うち shadow 単独 213.0h)。建玉 1,798 本中 1,788 本が shadow。**ただし経済的重みは被拘束時間ではなく真の 4,662 件/30d (3.0%)** であり、`_COUNT_GATE_BYPASS_LIVE_EXCEPTIONS` の 6 type (kalman_d7 ×3 ほか) は hedge を bypass する = **今月唯一 live 約定した kalman_d7 は免除側**。緩和は live 経路を含むゲート変更 = **Rule 1** につき本 PR では触らず registry `hedge-gate-duration-vs-2026-04-30-premise` (期日 10-20) に凍結
- **教訓**: 早期 return が「これは数えない」と宣言しても、その return より前のゲートには効かない。**述語が対象外入力で自明に真になるゲート (方向比較・総数比較) は、ガードの後ろに置かれた瞬間に別物を数え始める**。ゲートを追加・移動したら、上流の早期 return の宣言がまだ成り立つかを確認する
- 詳細: [[wait-tick-block-attribution-2026-09-23]]
## 2026-09-23 — docs(decisions): UD1 結果 = GOLD (user 画面確認) を registry / 決裁パケットに記録 (rule:R3)

- `ud1-gold-screen-check` resolved: OANDA status 画面で 9 月 keeper ($520k) 算入・**GOLD** 表示。SILVER 分岐 (packet v0.1 書き直し) は不発、v0 前提のまま確定版 10-08 へ。keeper 10 月 run 継続
- 併記: [[integrated-decision-packet-d1-d12-2026-09-22]] 末尾 / [[path-to-win-reassessment-2026-09-22]] 末尾
- registry 新規 `oanda-gold-monthly-status-record-2026-10` (期日 09-30 → 10-01 判定): 10 月ランクの user 確認・記録義務の読み手 (Codex P2: 参照していた「10-01 項目」は未存在だった)

## 2026-09-23 — fix(engine): rnb_usdjpy (shadow_only) 限定で下流 live 保護 gate 3 つを shadow 化 — shadow レーン行ゼロの真因修理 (rule:R3)

- **背景**: [[rnb-shadow-lane-health-precheck-2026-09-22]] §6 — 09-12 以降の rnb BUY bar 6/6 が `_tick_entry` 下流の velocity_down / mtf_strong_bias / 1h_rr_low で hard block、closed shadow N=2 のまま (checkpoint-1 09-24 n_floor 3 は 09-25 00:20Z 判定で TRIGGERED 見込み)。shadow_only mode は OANDA 送信が構造的にゼロで、これらの gate が守る資本は無い。365d ablated BT は同 gate を適用していない (BT⇄live 母集団の非同期 = 構造欠陥、R3)
- **変更** (`modules/demo_trader.py`): `_SHADOW_ONLY_DOWNSTREAM_RELAX_MODES = frozenset({"rnb_usdjpy"})` + `_mode_downstream_relax()` (allowlist ∧ 実状態 shadow_only=True の AND = fail-closed)。参照は 3 gate のみ、`_block(); return` → `_is_shadow=True` + `[SHADOW] <gate> relax:` ログ。`_is_shadow_eligible_full` (9 経路) / `_mode_is_shadow_only` 汎用化 (daytrade_audjpy の WS3 stage-2 母集団に触る) / session_hours / 閾値 / `_UNIVERSAL_SENTINEL` は不変
- **pin**: `tests/test_rnb_shadow_only_downstream_relax.py` 20 本 — 3 gate の shadow 化 (a) / allowlist 空で従来 block (control) / shadow_only=False で迂回消滅 (fail-closed) / daytrade_audjpy 不変 (第 2 の対称側) / OANDA 送信ゼロ / 21 時台は session_hours で block / spike は hard block のまま / `_downstream_relax` 参照数 = 4 のスコープ pin / relax 行の `[SHADOW_RELAX] <gate>` marker (+ 恒真でない対称側)
- **per-row provenance**: relax 分岐は reasons に `[SHADOW_RELAX] <gate>` を永続 (`[HOURBLOCK_CLASS_EXEMPT]` と同型) — LOCK 層別の一次キー。二次 (デプロイ前/後) の追記義務は新 registry `rnb-relax-deploy-stamp-record` (09-24) が読む。敵対的 3 レンズレビュー (Codex は指摘ゼロ) で一致した P2「層別キーが後追記の deploy 時刻だけに依存」への対応
- **registry**: LOCK `rnb-support-bounce-shadow-forward` に 🔒 AMENDMENT 事前宣言 (変更前 N=2 snapshot、旧/新 gate 構成は**層別既定**・除外しない、n_decide 41 は総数、一次キー marker / 二次キー デプロイ時刻) / checkpoint-1・-2 に混合読み注記 + 新構成行で『通過』した場合の引用制限 (n_floor・期日不変) / 新規 `rnb-relax-deploy-stamp-record` (09-24) / `review-backlog-sprint0922-p2-deferrals-1003` resolved (β 分岐不採用で PR #283 comment 4070561551 は moot)
- **判断の位置づけ**: checkpoint-1 の自動判定 (09-25) を待たずに執行 — 真因は機構帰属済み・判定主体は Claude (R3 自走可)・user 委任「推奨で進めて」。「TRIGGERED」は名乗らず、自動判定の resolution に旧/新層別 N を記す (precheck §11)
- 残置 (範囲外): precheck §8 (iii) データ鮮度読み手 / (iv) TACTICAL_BIAS writer ログ / (v) watcher 厳格 shadow 選択子
- **デプロイ記録 (follow-up docs PR)**: merge `0033a883` 2026-09-22T20:04:54Z → Render `dep-dapduq2jnfac73caav30` live **2026-09-22T20:06:42Z** を LOCK message に追記、`rnb-relax-deploy-stamp-record` resolved。Codex 2 巡 (171c5ab / 863eb21f) とも指摘ゼロ、敵対的 3 レンズ workflow の P2 (per-row provenance) は marker で消化
## 2026-09-23 — docs(wg): R1 再審 DRAFT に pre-send guard 未到達の分類規則 + 候補 2d 送信適格化を追記 (PR #281 P2 消化、rule:R3)
- 6 巡目 P2 (4076386272): fill の証拠に broker 確認ログ `[OandaBridge] OPEN … → OANDA #<id>` と broker open trades 突合を追加 (persistence callback 失敗時に UNKNOWN(infra) へ誤分類しない)。**P2 巡目上限 (6) 到達 — 以後は打ち切り規則 (1 行修正 + review-ack + CI green で --admin マージ)**

- **§2 不成立 (v) 「未到達 `PRE_SEND_GUARD(<reason>)`」行を新設** ([[weekend-gap-execution-modality-r1-redraft-DRAFT-2026-09-22]]、PR #289): qualifying ログ後に `[WEEKEND_GAP][EXEC_B] decision=SEND` を通過したのに OANDA 送信試行 (demo_trader.py 7876) に到達せず終端した pair-event。4 亜種 = (a) 早期 `_block` return (row/latch なし、`gate_block_daily` のみ — order-bar 予約 5523–5531 の**前**の blocker は再評価あり、**後**の blocker は以後 `order_bar_dedup` 5532–5537 で窓内固定、帰属は初出の非 dedup 理由) / (b) slot 由来 shadow 化 (row あり・`oanda_trade_id` 空・latch `EXECUTED`・audit `shadow_tracking`) / (c) bridge-refused (daily-loss gate `blocked` oanda_bridge.py 668–690 / pre-check `bridge_inactive`・`mode_<mode>_not_allowed` 7941–7955 / 無 audit race 649・658 → `[SHADOW_FIX] Bridge refused transmission` 7925–7940) / (d) 手動停止 mode_off ほか promotion gate 由来 (`_is_promoted_ex` 10429 → post-gate escalation 7790–7798 `[SHADOW_FIX] Post-gate escalation` → audit `skipped`/`shadow_tracking`、`手動停止` 7977 は PRIME lock 下のみ)。**現行契約 (packet §6 表 L114–115 / registry g0prime message) 下では不成立として G0' event を消費する** — fill 経路の (i)〜(iv) と区別して記録、event #2 が (v) なら契約どおり R1 再審 packet を 7 日以内に起案し modality 型 / 容量・設定型を分けて提示。行番号は main `7145a93c` 実測
- **非消費・繰越案は AMENDMENT 提案 A-1 (§4 row 4) へ移管、user 承認まで無効** — Codex 2 巡目 P1 (4075480956) を受け入れ方針転換: 承認済み契約の非消費は cap skip・正当放棄・NO-QUALIFY に限られ、未到達を分母から外すのは決定境界の変更 = R1 + user (autopilot R3 では不可)。理由 (modality 未検証・容量 outcome の誤帰属) と付帯 (同一 reason 2 回で R3 レビュー / 持続型は G0' が永久に閉じない) は A-1 に保存
- **§3 候補 2d**: 効果セル「有効 (09-13 型は fill する)」→「**送信適格化のみ (fill ではない)**」。下流に `SKIPPED_SPREAD` (demo_trader.py 6229–6249 / 6313–6326)、bridge daily-loss `blocked` (= §2 (v) 亜種 (c))、FOK cancel 2 回目 `MARKET_HALTED` / 別 reason cancel / `ok but no tradeID` / `OPEN … FAILED` (oanda_bridge.py 751–909) が残り **fill 率は forward 計測**。暫定評価「F2 を確実に resolve」→「resolve し得る」、表の読み方「live fill に変えられる」→「送信判定まで到達させられる」
- **§0 / §4 row 8 / §6 / §7**: サマリ・first-qualification ts との整合・転記名 `不成立(v) PRE_SEND_GUARD(<reason>)`・禁止事項 (「未到達を user 承認前に分母外として扱う / 未分類で置く」「2d を fill / F2 resolve と読む」)。凍結値 (+15 分 / +8.0p / 60s / 10s / 10.0p / 1000u / 4h / 150p / qualify 閾値 / G1 / G2) と OOS 数値は不変更、2a 行の fill 成立率見積りも不変。registry `weekend-gap-execution-amendment-g0prime` / F2 entry は不変 (契約不変)
- registry `review-backlog-sprint0922-p2-deferrals-0926` → `active:false` / `resolved: 2026-09-23` (期日 09-26、event #2 = 09-27 21:00Z 前)。PR #281 thread 2 件 (4070529776 / 4070529787) と PR #289 review 1 巡目 P1 (4075088689) / 2 巡目 P1 4075480956・P2 4075480961・4075480969 へ返信
- **3 巡目 (P2 4075642842 / 4075642847) + 親セッション敵対的レビュー所見 6 件**: (b) を「row あり shadow 化 (slot 由来ほか上流 shadow bypass)」に一般化 — wg ∈ `_UNIVERSAL_SENTINEL` (9927) で `recent_emit` 5552–5558 / `spike` 6357–6362 / `velocity_*` 6390–6404 / `regime_guardrail` 6176–6181 / `session_pair`・alpha_scan 5933–6083 は `_block` でなく bypass 分岐 (row + latch `EXECUTED` + audit `shadow_tracking` + SENTINEL_BLOCK_DIAG 7372/7999)、帰属は `[SHADOW] <gate>` ログのみ → `bypass:<gate>`。(d) の帰属は event 時点記録 (`[SHADOW_FIX] Post-gate escalation` timestamp / audit block_reason) のみ、現在 mode からの推定禁止・記録なしは `promo:UNKNOWN` (`_promo_block_cause` 永続化は別 R3 chip)。所見: ABANDONED 後 pre-row `_block` = 不成立 (i) `PRE_ROW_BLOCK` (4254–4267 → 5234–5299) / `drawdown` 5302–5303 は dead code (`_check_drawdown` 全 False、CB は `_oanda_kill` 3952–3965 → (c2) `mode_<mode>_not_allowed`) / SEND→guard→ABANDONED は (v) 主・ABANDONED 従で併記 / `[SENTINEL_BLOCK_DIAG] blocked at:` 1366 を (a) 一次ソース / `<reason>` は `order_bar_dedup`・`recent_emit` 以外の初出 + 全併記 / 旧行番号 (oanda_bridge 680–719 / 797–808 / 809–826 / 669–719、demo_trader 4246–4250 / 5282–5286 / 7908–7915 / 7921–7938 / 7939–7952) を 7145a93c 実測に統一
- **4 巡目 (P2 4076004076)**: 未到達 (v) の上位述語を「OANDA への実送信 (oanda_audit `sent` 行) が無い」で再定義 — 旧「`open_trade` 7876 に到達せず」は bridge 内 gate で `False` を受ける (c1)/(c3) と矛盾していた。(a)(b)(d) は open_trade 未到達、(c) は到達だが未送信、いずれも `sent` 無し (`sent` は `_send_accepted` 真のみ 7911–7918)。§2 (v) 行 / 不成立行 (v) 要約 / (iv) / §7 を同期。merge origin/main (#290/#291) — registry は main 側を採り本 PR の entry 変更のみ再適用 (91 entry、lint 0)、changelog / CHANGELOG / session log は union
- **5 巡目 (P2 4076293714)**: 上位述語を「**broker 到達の証拠が無い**」へ — `open_trade` は `_fire(_do)` で worker を起動し即 `True` (oanda_bridge.py 911–912)、`sent` audit はその後に呼び出し側が書く (demo_trader.py 7911–7918、7145a93c 基準) = dispatch 受理であり境界にしない。証拠 = fill / cancel tx / `OPEN … FAILED` / `pending_oanda_ops` terminal (`pending_op_create` 703–718 → `done` 877 / `failed` 889・906、demo_db.py 1833–1879)。`sent` あり ∧ 証拠なし = **`不成立(vi) UNKNOWN(infra)`** (消費するが modality 失敗に数えない、packet §1 に infra 型)、`sent` なし ∧ 証拠あり = 証拠で分類。§0 / §2 / §4 row 1 / §6 / §7 同期。registry 不変

## 2026-09-22 — docs(KB): スプリント 0922 終結 — registry 統合 (繰延 9 を索引 + 期日別 sub-entry 4 / 更新 9 / 新規 6) + index/changelog/session 同期 (rule:R3)

- **同日マージ 11 PR (#277〜#287) の KB 統合**。code PR 4 本の要点:
  - fix(nav_floor) **F4 資金時計 burn を decomposed (keeper 確定分 + edge 30d) に分解、fit は参考列へ** (PR #285、[[nav-floor-f4-estimator-decomposition-2026-09-22]]) — registry F4 の condition 不変、発火日は幅で引用 (keeper のみ 2027-01-05 / drift 込み 2026-12-04)。`tests/test_nav_floor_projection_f4.py` が再現値と安定性を pin
  - feat(e1) **凍結 export tool `tools/e1_positioning_frozen_export.py` + first look 手順書** (PR #286、[[e1-first-look-runbook-2026-09-22]]) — pre-reg §2.5-6「1 回だけ + sha256」の機械担保 (marker / attempt 台帳 hash chain / preflight / staging 公開)、判定器 `load_bars` の epoch 分解能バグ修復 (ns/us/ms で pin)
  - fix(oanda_bridge) **SL replacement storm guard 4 点 (breaker → 冪等 → 単調性 → dead-band)、既定は検知のみ** (PR #287、[[storm-guard-design-2026-09-22]]) — `STORM_GUARD_ENFORCE=1` で有効化、判断期日は registry `storm-guard-enforce-decision` (10-20)。レビュー依頼 18 回 / inline P1 18 件全修正 (繰延は P2 のみ)
  - fix(fork-safety) HTTP 全盲根因修復 (PR #277) は上のエントリ参照
- **docs 群**: 再評価 (#278 [[path-to-win-reassessment-2026-09-22]]) / 統合決裁パケット D1〜D12 DRAFT v0 (#279 [[integrated-decision-packet-d1-d12-2026-09-22]]) / 30 日 triage + PR 規律 (#280 [[sprint-triage-pr-discipline-2026-09-22]]) / wg card 09-13・09-20 転記 + R1 再審骨子 DRAFT (#281 [[weekend-gap-execution-modality-r1-redraft-DRAFT-2026-09-22]]) / carry_dip broker 突合 14/14 (#282 [[carry-dip-broker-reconcile-2026-09-22]]) / rnb lane-health 事前調査 (#283 [[rnb-shadow-lane-health-precheck-2026-09-22]]) / 臨時スキャン #29 step 0 (#284 [[adhoc-scan-29-step0-2026-09-22]])
- **registry** (`prereg-trigger-registry.json`、80 → 90 entry): 新規 `review-backlog-sprint0922-p2-deferrals` (索引 10-17 + 期日別 sub-entry `-0926/-1003/-1005/-1007` (09-26 = event #2 (09-27; 09-20 NO-QUALIFY は分母外) 前日、cron 判定は翌 00:20Z); 旧記載 10-08 は Codex P2 で訂正、P2 巡目上限到達で未修正のまま繰延した 9 件 — 全て実欠陥、個別期日 09-27 / 10-03 / 10-06 / 10-17) / `ud1-gold-screen-check` (09-23、user) / `e1-first-look-freeze-due` (10-08) / `storm-guard-enforce-decision` (10-20) / `wg-dst-cutoff-basis-r3` (10-25) / `sprint-0922-triage-close` (10-22)。既存 9 entry へ 09-22 追記 (message のみ、condition / since 不変): g0prime (g0prime 期日は 09-28 のまま (10-05 繰越は Codex P2 で撤回)) / F2 / carry-dip-v3-revival-watch (broker realized 併記、凍結 estimand 不変) / rnb checkpoint-1・-2・shadow-forward (期日 ≠ 判定日、厳格 shadow 再計数) / edge-supply-scan-monthly (臨時スキャン記録) / review-backlog-253-257-digest (消化順序) / e1-prereg-verdict-deadline (手順書・tool)
- **render.yaml ignoredPaths** += `knowledge-base/raw/alpha_budget/**` / `knowledge-base/wiki/research/**` — `auto: KB session-end save` (b53fd5cd 06:24Z) が alpha_budget json 1 ファイルで本番を再デプロイしていた残余 churn。web プロセス (app.py / modules/) からの参照ゼロを grep で確認 (読み手は cron service の tools/quant_gate_status.py / scripts/daily_hypothesis_scan.py と手動 tools/qdrant_ingest_kb.py のみ、cron service は buildFilter を持たず毎 push で再デプロイされる)。pin: `tests/test_render_build_filter.py::test_cron_only_kb_state_paths_are_ignored`
- hot file 同期: index.md System State 先頭ブロック / research/index.md (adhoc-scan link) / audit-index.md (3 行) / sessions/2026-09-22 Phase 32
- ⚠️ 未解決のまま registry に置いたもの: engine 二重起動 (`dual-engine-master-worker-disposition` 10-06) / UD1 user 未回答 / 繰延 P2 9 件

## 2026-09-22 — fix(fork-safety): 本番 HTTP 全盲 3h18m の根本原因 — gunicorn master の pre-fork 窓で DailyReview が SQLite を回していた (rule:R3)

- **事故**: 00:12:50 デプロイ直後〜03:33Z、全 API が 499 (client timeout)。`[MainLoop]` は連続、`[API-SLOW]` 0 / `WORKER TIMEOUT` 0 / memory 562MB。Render が 03:33:27 に SIGTERM → 復旧。**同型が 09-12 (3h31m) / 09-15 (3h22m) にも発生** (本調査で発見)。3 件とも UTC 0 時台デプロイ直後、0 時台起動 7 件中 3 件が盲目、0 時台以外は 0 件
- 🔑 **根本原因**: Render の gunicorn は app.py を **master (PID 39) で import** し直後に worker を fork。`DemoTrader.__init__` が import 時に起動する DailyReviewEngine は 0 時台起動で即座に全件スキャン + 204MB backup を master で走らせ、fork がその最中に落ちる → worker は SQLite のプロセス共有 mutex を locked のまま継承 → **DB を触る全ルートが永久ハング** (`HEAD /` は 200)。gthread の `--timeout` は main thread 生存しか見ず、Render は TCP 疎通しか見ない
- ✅ **F1** `DailyReviewEngine.start(defer=True)` + app.py heartbeat → `DemoTrader.ensure_daily_review_running()` (positioning §11 と同型。StatusHeal からは呼ばない — master 側 AutoStart/Verify も呼ぶため)
- ✅ **F2** `/healthz/http` (fresh `sqlite3.connect` + `sqlite_master` 1 行 read、StatusHeal/tick 非接触) + render.yaml `healthCheckPath: /healthz/http` — ハングした worker では connect が返らず数分で再起動。trade-off (in-memory dedup 消失、DB hydrate あり) は analyses に明記
- ✅ **F3** render.yaml ignoredPaths += `data/external/rate_anchor/**` / `data/external/mof_statements/**` / `data/cache/yield/ZN_F_1h.parquet` — 夜間 ingest 2 commit が**毎晩 2 回**エンジンを再デプロイしていた (runtime 参照ゼロ、pin 付き)
- ✅ **F4** `modules/freshness_policy.classify_fetch_failure / classify_outage` (SSOT) + `scripts/anomaly_watcher.py` に **`http_blind`** イベント (read-timeout 全滅 = listen 中・HTTP 無応答・engine 生死は外部から不明 ↔ 接続拒否/5xx = `api_unreachable`)
- ✅ **F5** `scripts/daily_report.py`: `FetchResult` で失敗と空を分離、DATA FETCH テーブルを prompt 先頭に、規則 5 (原因を書かない)、出力後に原因捏造語を検出したら**生成器注記で訂正** (09-22 03:11Z レポートの「Render 無料 tier スリープ」は捏造 — Pro plan)
- **pin**: `tests/test_daily_review_fork_safety.py` / `test_http_blind_detector.py` / `test_healthz_http.py` / `test_daily_report_fetch_status.py` / `test_render_build_filter.py::test_nightly_ingest_data_paths_are_ignored` — counterfactual 5 本実測
- 🔴 **副産物 (未修正)**: エンジンが **master と worker の 2 プロセスで二重に走っている** (全盲中は master のみ前進 / StatusHeal 後は `iter=240` が 2 回)。単一エンジン化は shadow N の regime break を伴うため registry `dual-engine-master-worker-disposition` (10-06)。修復の forward 検証は `http-blind-fix-verification-hour0-boots` (10-06)
- 🟠 **レビュー P2 × 2 消化** (Codex、どちらも正しい): `classify_outage` の api_down を connection/5xx のみに限定 (4xx = `http_error` serving 中 / other 混在 = mixed) / 捏造ガードを strategy_report にも同じ出口 (`finalize_llm_report`) で適用 + planner prompt に原因禁止規則。同 PR 内で「片側だけ塞ぐ」を 2 回踏んだ
- 🟠 **レビュー 3 巡目 P2 × 3 消化**: `classify_outage(n_ok=)` で部分失敗を `partial` に限定 (失敗分だけ渡して 1 本の timeout を全盲と要約していた) / `http_blind` を観測クラスに格下げ (read-timeout は edge までの接続しか証明しない — origin 状態は health check と app ログで裏取り) / 捏造ガードを fetch 失敗時のみ + 否定文除外 (`find_invented_causes` SSOT)
- 🟠 **レビュー 4 巡目 P2 × 2 消化**: `api_down` を connection のみに限定 (全 5xx は `http_5xx` = 応答あり、edge/app 判別不能) / 捏造ガードの否定判定を文→節単位へ (別節の否定が肯定断定を隠していた)
- 🟠 **レビュー 5 巡目 P2 × 2 消化**: 応答あり失敗 (全 4xx / 全 5xx) を `api_unreachable` に畳まず専用 event `api_http_error` へ (4xx=認証/パス、5xx=edge/app 判別不能) / 捏造ガードの否定を原因語束縛へ (「応答しない」の汎用否定が断定を隠していた)
- 🟠 **レビュー 6 巡目 P2 × 1 消化**: health check プローブを `SELECT 1` (DB を触らない定数評価) から `sqlite_master` の実 read へ
- 導出: [[http-blind-fork-poisoning-2026-09-22]] / 教訓: [[lesson-prefork-master-must-not-touch-db-2026-09-22]]

## 2026-09-22 — fix(hooks): main 乖離の**発生源**を塞いだ + 座礁 KB の救済 + committed conflict marker の修復 (rule:R3)

- **背景**: autopilot 起動時、作業が **3 箇所で座礁**していた — ローカル `main` が origin に対し **ahead 8 / behind 112**、PR #272 に未 push commit 1 本、PR #273 worktree に未コミット実装 (pin が赤のまま)。前 2 者は本日 #272/#273 として着地済み
- 🔴 **発生源の特定と修復 (本エントリの主題)**: `scripts/hooks/session-end-save.sh` は step 2 で KB 変更を **HEAD (主 checkout では `main`) へ直接コミット**し、step 3 の `git push origin main` は **local main が behind だと必ず失敗**する。失敗は stderr に出すだけだったので「**コミットは main に積まれ、push は落ちる**」が毎日繰り返され、**乖離が再生産**されていた。2026-09-17 に PR #264 で*backlog* は掃除したが*ジェネレータ*は残っており、5 日で ahead 8 まで再蓄積した (09-21 の daily review が同じ機構を独立に特定していた — [[2026-09-21]])
  - ✅ **修復**: main への push が失敗したら、**その commit を `kb-rescue/<branch>-<date>` として origin へ退避**する。**成功時の挙動は一切変えない**。これで「ローカルにしか無い KB コミット」が原理的に残らず、次セッションが PR に畳める。`--force` は使わず origin/main は不変
  - 🔵 **pre-commit が私のテストの欠陥を捕まえた**: 初版は `GIT_DIR` / `GIT_INDEX_FILE` の**環境変数リーク**を考慮しておらず、**pre-commit 経由 (= `git commit` の中から pytest が走る) では temp repo でなく実リポジトリを操作**して実 pre-commit を temp ディレクトリに対して発火させていた (単体実行では通るので気づけない)。`GIT_*` を除去し `core.hooksPath=/dev/null` を当てて hermetic 化し、**リーク環境を再現した状態でも通ることを実測**。🔑 テストを足したら「**CI/pre-commit が呼ぶ経路でも同じ結論か**」を確認する
  - **pin** `tests/test_session_end_save_rescue.py` (**3 本**) — **grep pin ではなく実 git repo + bare remote に対して実スクリプトを走らせる** (「正しいメッセージを出しつつ commit を座礁させる」実装は grep では通ってしまう)。NG 状態 (behind main) で rescue ブランチに**当の commit sha** が届くことを assert + counter-pin 2 本 (happy path で rescue ブランチを作らない / KB が clean なら空コミットを作らない)。counterfactual 確認済 (fallback を外すと `origin has only {'main'}` で落ちる)
- ✅ **座礁 KB の救済**: local-only 8 commit のうち、**main 側が既に上位互換だったもの (session log 4 本 / cell_deepdive summary 2 本) は main を採用**し、**実質的に失われていた 4 ファイルのみ**を救済 — `raw/trade-logs/2026-09-21.md` (362 行) / `wiki/index.md` の 09-21 System State (LIVE fill 10.03 日停止 / learner 6.02 日 stale / `tokyo_nakane_momentum` のクラスタ分析 / **main 乖離再発の診断**) / `wiki/log.md` / `wiki/strategies/tokyo-nakane-momentum.md`
  - 🔵 **救済した分析の中身が今日の作業と噛み合っている**: 09-21 の review は「`tokyo_nakane_momentum` の 8 発火は 59 分以内・3 ペア・全 BUY = **独立 8 標本ではなく『JPY 売り』1 ベットの 8 重複**」「勝ち 3 本の `close_reason` が全て `SL_HIT` = ラベル破綻の 3 例目」を記録していた。**昇格審査でクラスタ性を N から割り引く前処理が必須**という論点は保存された
- 🔴 **committed conflict marker の修復**: `wiki/sessions/2026-08-30-session.md` に **`<<<<<<< Updated upstream` / `>>>>>>> Stashed changes` が 2 箇所コミットされたまま** 3 週間 main に載っていた (解決されなかった `git stash pop` の産物)。narrative 側を採り、stub 側の unique な内容 (コミット一覧) を明示ラベル付きで併置して union 解決。**KB 全体で marker ゼロを確認**
- 🔴🔴 **その環境変数リークは診断した直後に実害を出した (同一セッション内)**: hermetic 化**前**のテスト実行が pre-commit 経由で走った際、リークした `GIT_INDEX_FILE` 越しに**実リポジトリの index へ `git add -A` を適用**しており、直後の commit がその index を拾って **3,568 files / −1,156,926 行 (`tools/` `tests/` `reports/` `data/` ほぼ全部) を削除する commit** を作っていた。`git show --stat` の規模が異常だったため**push 前に検知**し `reset --mixed` で撤回、**ファイル名を列挙して再 stage** した (working tree は無傷 = index のみの汚染)。🔑 **(1) テストが実リポジトリを触りうる形なら CI/pre-commit 経由で実際に触る** — hermetic 化は品質ではなく**安全性**の問題。**(2) commit 後に `--stat` の規模を必ず見る** — exit 0 は「意図した範囲」を保証しない
- 🟠 **connector レビュー (Codex P1 + P2、どちらも正しかった) — 私の修復自体が「頼まれていない公開」を作っていた**:
  (a) 🔴 **P1: feature ブランチから退避してはいけない** — `git push origin main` は
  **ローカルの main ref** を押すので、**HEAD が feature の時も (main が behind なら) 失敗
  しうる**。そこで HEAD を退避すると **その feature の未公開 WIP コミットまで origin に
  publish** してしまう = **誰も頼んでいない公開**。しかも HEAD が main でなければ step 2 の
  KB コミットはその feature ブランチ上にあり、**当人の PR で push されるので座礁しない** ⇒
  **退避は HEAD==main のときだけ**に限定し、それ以外は理由を stderr に出して何もしない
  (b) **P2: 退避 ref に短縮 sha を入れる** — 同日に 2 つの stale な main checkout が走ると
  `kb-rescue/main-<date>` が衝突し、**2 本目は non-fast-forward で拒否されてローカルに座礁
  したまま**になる (= 修復が目的を達しない)。`-f` は他人の退避を壊すので使わず、**名前を
  一意にする方**で解いた
- 🔑 **「座礁を防ぐ」修復が「公開してしまう」副作用を持っていた** — 安全側に倒したつもりの
  fallback が、**別の種類の不可逆操作**を生んでいた。⇒ fallback を書くときは
  「**何を origin に足すのか**」を操作単位で列挙する。pin 3 → **5 本**、2 件とも
  counterfactual 確認済 (P1 を戻すと `origin gained {'kb-rescue/main-...'}`、
  P2 を戻すと `len({...}) == 1` で落ちる)
- 🔴 **レビュー 2 巡目 (Codex P1、これも正しかった) — main 上でも「hook の KB コミットだけ」を証明していなかった**: 1 巡目の `BRANCH == main` ガードは feature ケースを塞いだが、**local main 自体に未公開の非 KB コミット** (誰かが main に直接コミットした作業) があれば、`HEAD:refs/heads/...` は**それも一緒に publish** する。しかも**本ランが KB を 1 件もコミットしていなくても発火**していた。⇒ 2 段のガードを追加:
  (a) **本ランが実際にコミットしたか**を `HEAD` の前後比較で判定 (`exit 0` は commit 成功を意味しない — pre-commit の `Commit blocked` も 0)。コミットしていなければ退避しない
  (b) **`origin/main..HEAD` の全コミットが「hook 製の KB コミット」であること**を検査 — subject が `auto: KB session-end save` で始まり、**かつ `git diff-tree` が `knowledge-base/` 以外に触っていない** (subject は自称なのでパスも見る)。混在 / 比較不能なら **publish せず理由を出して止まる**
- 🔑 **公開は不可逆なので、ここだけは fail-closed の向きが「退避しない」** — 座礁 (回復可能) と publish (回復不可能) では安全な向きが逆になる。**「安全側」は一意でなく、何が不可逆かで決まる**
- pin 5 → **7 本**。2 件とも counterfactual 確認済 ((b) を外すと `origin gained {'kb-rescue/...'}`、(a) を外すと新規コミット無しでも退避が走る)
- 🟠 **レビュー 3 巡目 (Codex P2) — 一意性が目的なら省略形を使ってはいけない**: 退避 ref の sha を `git rev-parse --short` で作っていたが、**`--short` は `core.abbrev` に従う**ので 4 桁まで縮みうる ⇒ 前置が衝突して**2 巡目で直したはずの non-fast-forward 座礁が再発**する。完全 sha (40 桁) に変更し、**pin も「ref が 40 桁 sha を含む」ことを assert** する形へ (counterfactual: `--short=4` に戻すと `got 'f269'` で落ちる)。pin 7 本のまま
- 🔴 **レビュー 4 巡目 (Codex P1、これも正しかった) — ガードが「存在意義そのものの場面」で反転していた**: 混在検査を `git diff-tree ... | grep -qv '^knowledge-base/'` と**パイプで**書いていたため、**非 KB パスが早い位置にあり後続 KB パスがパイプバッファ (64KiB) を埋めるほど多い**とき、`grep -q` が先に exit して `git` が **SIGPIPE (141)** を受ける。本スクリプトは `pipefail` なのでパイプライン status が 141 = 非ゼロになり **`if` は偽** ⇒ **混在履歴を「KB だけ」と判定して publish** する。⚠️ **仮想的な話ではない** — 本セッションで実際に作ってしまった **3,568 files の混在コミットがまさにこの形**。⇒ パイプを廃し変数に取ってシェルで走査。**pin は 600 個の長名 KB ファイル + 早くソートされる `app.py`** で当該条件を再現し、counterfactual で**パイプ版が実際に publish してしまうことを実測**した (pin 7 → **8 本**)
- 🔴 **レビュー 5 巡目 (Codex P1 + P2) — 検査した sha を押す / 残り 1 件は明示的に繰延**: (a) **P1: refspec の source を固定 sha に** — `HEAD` は symbolic なので、収集〜検査の間に**別エージェントがこの共有 checkout へコミット**すると、検査は旧履歴に対して行われたのに `HEAD:refs/heads/...` は**新しい HEAD を publish** する。この repo は並行エージェント前提なので実在のリスク ⇒ `VALIDATED` を検査**前**に固定し、push もそれを明示的に押す
  🔵 **この pin は「機構 pin」だと明示した** — 当該 race には**決定的な注入点が無い** (rev-list 完了と push 開始の間に git hook は無く、それより早く注入すると混在ガードが先に捕まえる)。実際 `HEAD:` に戻しても behavioural pin は緑のままだったので、**恒真な pin を『検証済み』と偽らずに機構 assertion (refspec source が `HEAD` でない ∧ sha が検査前に固定されている) へ書き換え、限界を docstring に明記した**
  (b) **P2 は意図的に繰延** — post-commit が**コミット作成後**に session log へ追記するため **末尾差分が必ず 1 本ローカルに残る** (本セッションで merge を 2 回ブロックした実害)。ただしこれは **PR #276 が作った欠陥ではなく post-commit hook の既存設計**なので同 PR では直さず、registry `kb-session-log-postcommit-trailing-edit` (**期日 2026-10-13**) に (a) pre-commit へ移す / (b) 生成物扱い / (c) 仕様として文書化 の三択で繰延した
- 🔑 **pin 8 → 10 本**。「振る舞いで確かめられないものを振る舞い pin のふりで置かない」— 恒真 pin は**検知していないことを検知したと錯覚させる**ので、[[project_review_gate_vacuous_2026_09_11]] と同じ害になる
- 🔑 **教訓: 「backlog を掃除した」と「ジェネレータを止めた」は別** — 09-17 の CLOSED 判定は前者だけで出されており、5 日で再発した。**再発する欠陥は、事象ではなく発生機構に対して pin を置く**
- ⚠️ **ローカル `main` の 0/0 復帰は、内容が origin に到達したことを確認した後に行う** — 2026-09-17 は先に `reset` して未コミットの `index.md` 編集を破壊し System State を 13 日巻き戻した ([[2026-09-21]] が記録)。本 PR がマージされてから reset する順序を厳守した

## 2026-09-21 — readout(ps 席): 帰属完了 = **下流 100%、3 席は `spread_wide` で 6/6 全滅** + gate block の magnitude 計装 (rule:R3、live 挙動不変)

- **registry `ps-seat-supply-hourly-c1-coverage` を期日 09-25 の 4 日前倒しで resolve**。3 点すべて判定、roll なし。09-11 の REJECT verdict が残した「未帰属残余 ~100%」が**帰属済み**になった。詳細: [[ps-seat-supply-remeasure-2026-09-10]] §11
- **(i) 計装到達 = PASS** — `view=summary&days=14` の `n_strategies=50` に `price_shock_rev_*` **5 席すべて出現**。09-11 に敷いた HourlyEngine C1 計装は本番に届いている。⚠️ **期日を待たずに手順 1 だけ先に叩いたのが効いた** — 配線落ちだった場合ここで判明し、09-25 まで気づかず 14 日失う分岐を回避できた (手順 1 は「届いていなければ以降が無意味」な gating check なので前倒しコストがゼロ)
- **(ii) 書込み量 = 見積り範囲内、retention 短縮不要** — `evaluated_candidates` **325,530 行** (first 2026-06-23 / last 09-21T01:05:30Z) / disk `used_pct` **60.4%** (`level=ok`、warn 75 / critical 90) / `c1_retention_days` 90 / `write_probe` ok。§9 の「見積りのまま放置しない」を実測で履行
- 🔴 **(iii) 帰属 = (B) 下流で確定、(A) 上流は棄却** — 5 席とも **Σblocks が C1 行数と厳密一致** (= order 層に到達した候補ゼロ) かつ `selected=1` が **141/141** (席優先 select は一度も負けていない)。内訳: nzd_jpy 42 行 / eur_aud 24 / usd_cad 39 / aud_jpy 15 / eur_gbp 21
- ⚠️ **機会の単位は行ではなく `bar_time`** — 生 **141 行 → distinct bar 10 本 = 14.1 倍の重複膨張**。C1 の estimand は per-tick (~30s poll) なので、`usd_cad` の 39 行は**すべて同一バー** (09-17 12:00Z) であり行数で数えると 1 機会を 39 と誤読する (hunt_events の N 膨張と同型 — [[project_hunt_events_dataset_readout_2026_09_19]])。**`order_bar_dedup` 107 + `recent_emit` 4 は同バー重複の抑制であって attrition ではない**
- 🔴 **終端 gate は席ごとに違う** — 対象 3 席 (NZD_JPY / EUR_AUD / USD_CAD) は **distinct bar 機会 6/6 が `spread_wide`**、aud_jpy は `velocity_down` 2/2、eur_gbp は `gbp_asia_flash_crash` (2 本とも **21:00 UTC** = Asia 開始、4原則#3 に沿った**意図された**静的ブロックなので欠陥ではない)
- **算術一致を機構で裏取りした** — Σblocks == 行数だけでは偶然を排除できないので、`_maybe_reserve_order_bar_emit` (1 バー 1 予約、初回は通過) の call site **5491 行**が `spread_wide` 判定 **6244 行より前**であることをソースで確認。この順序を当てると「終端 gate 発火数 ≒ distinct bar 数」が導かれ nzd_jpy 2/2・eur_aud 3/3・aud_jpy 2/2 で実測と一致する。さらに **eur_gbp の `order_bar_dedup` が 0** で `gbp_asia_flash_crash` が全 21 行 = この guard は予約より前、という gate 順序が**本番データ側からも独立に読める**。⚠️ usd_cad のみ bar 1 に対し `spread_wide` 2 (+1) — in-memory の `_order_bar_signal_emits` が再起動で消えた説が最も素直だが**独立確認はしていない**と明記 (帰属の向きは変わらない)
- 🔴 **これは配線バグではなく設計レベルの衝突** — 3 席は `log_return ≤ 252 バー rolling 1%-tile` **かつ `vol_q="Q5"`** = 最高ボラ分位の極端下落でのみ発火する (`strategies/hourly/price_shock_reversion_base.py`)。一方 `spread_wide` 閾値は**静的な per-pair 定数** (USD_CAD **1.5p** / EUR_AUD **2.0p** / NZD_JPY **3.0p**、平常時基準)。**スプレッドはショック時に拡大するので entry 条件と block 条件が構造的に正相関している** — 席の設計が gate の弾く状態を狙って撃っている。同型は他 2 席にも出る (aud_jpy の `velocity_down` = 急落速度でショック条件と同軸)。⇒ **ps 席が clean live N を産まないのは供給不足ではなく「ショックを狙う戦略」と「ショック時に閉じる保護 gate 群」の衝突**
- 🟣 **実装 (同一コミット、rule:R3 — live 挙動不変): gate block の magnitude を永続化** — 「marginal (3.1p vs 3.0p limit = 調整可能)」と「absolute (15p = 構造的)」は **disposition を正反対にする**のに判定できなかった: `gate_block_daily` が `reason.split('(')[0]` 正規化で `spread_wide(4.2pip>3.0)` の **4.2 を捨てていた** (in-memory counter のキー爆発防止が永続面まで波及)。Render ログも ~2 週で失効し 09-17/18 のバーは既に取れない
  - `modules/block_event_logger.py`: `metric_n / metric_sum / metric_min / metric_max` を追加 + `parse_reason_metric()` (**reason ごとの測定値フィールド allowlist、宣言の無い reason は None = fail-closed**)。既存本番テーブルは `_ensure_metric_columns` で **idempotent に ALTER** (`PRAGMA table_info` 差分のみ)、**過去行は NULL のまま = 「測っていない」を 0 と捏造しない**
  - `modules/demo_trader.py::_record_entry_block`: raw `reason` から magnitude を抜いて渡す。**in-memory キーは従来どおり `'('` 前で正規化 = 挙動不変。PRIMARY KEY も不変**なので magnitude は行を増やさず min/sum/max に畳まれる (キー空間不変を test で pin)
  - **読み手を同一コミットで併設** — `query_block_counts` が `per_cell_metrics` (`{n, min, mean, max}`) を返し `/api/demo/block-counts` が **top-level キーとしても明示露出**する。収集だけ足して読み手を足さないのが本プロジェクト再発の write-only 欠陥 ([[c1-candidate-readout-hull-funnel-2026-08-24]])
  - ⚠️ **初版は `persisted` 経由の dict 透過で済ませようとして pre-commit に止められた** — estimand 宣言 `gate_block_attribution` の reader 配線検査が「読み手がコード上のどこにも**名前で**現れない」を ERROR にした。**暗黙の透過は「読み手あり」ではない**ので宣言を緩めずコード側を直した。検査が設計の弱点を捕まえた事例
  - ⚠️ **magnitude の単位は reason ごとに違う** — `spread_wide`=pip / `cooldown`=秒 / `velocity_down`=pip / `gbp_asia_flash_crash`=**UTC 時**。キーが reason を含むので同一 reason 内では一貫するが **reason を跨いだ平均は無意味** (pin 済)
  - 🔴 **Codex P2 (PR #275) 対応 — 初版の貪欲 regex は測定値でない数字を掴んでいた**: 本番 reason は括弧内の先頭に識別子を置くものが多く、その識別子が数字を含む。実測 `recent_emit(price_shock_rev_nzd_jpy_h1_long,35s<3600s)` → **1.0** (`h1` の 1、正は 35) / `layer_trade_not_ok(ema200_trend_reversal)` → **200.0** / `alpha_scan(EUR_USD_SELL,N=43,EV=-2.714)` → **43.0**。値は min/sum/max に**不可逆に畳まれる**ため消費側が偽と本物を区別できない = 計測面の汚染。**fail-closed allowlist へ置換** (パターンは `_block(f"...")` 実形から採取)。`gbp_asia_flash_crash(UTC21)` の 21 は UTC 時刻なので拾わない側へ変更。🔵 **教訓: 初版は「数字を持たない括弧」側は pin していたが「数字を持つが測定値でない括弧」という対称な反対側を確認していなかった** — [[feedback_check_the_symmetric_side_2026_09_19]] と同型を 2 日で再発
  - pin: `tests/test_gate_block_metric.py` (13 tests)。**counterfactual を実測確認** — `_persist_gate_block` の metric passthrough を外すと `test_spread_wide_magnitude_survives_entry_block_path` が落ちる (恒真な pin ではない)。**「NG を返す既知の入力」も同時に pin** (`order_bar_dedup` / `hedge_block(daytrade/EUR_USD:BUY)` = 括弧内に数値なし → None) — [[project_review_gate_vacuous_2026_09_11]]
- 🔵 **所見**: `confidence=70` / `score=1.0` が 141 行すべてで定数なのは `price_shock_reversion_base.py:88` のハードコード = **設計どおり**で、「定数なら異常」の不変条件に対する**文書化された例外** (次の読み手が再フラグしないよう記録)。機会バー 10 本は 09-15/16/17/18 に集中し 09-11〜14 と 09-19〜21 はゼロ = **バースト構造**
- ⚠️ **盛っていない点**: 供給量は「(A) が律速ではない」までしか言わない。3 席 design 17 本/30d → 11 日窓の期待 ≈ 6.2 に対し実測 distinct bar **6** は Poisson(6.2) と整合するが、**N=6 では ~2 倍の不足も排除できない** (§2 の分子/分母 disjoint と同じ規律)
- **範囲を越えていない**: gate は一切変更していない。3 席の disposition = (a) 退役 / (b) per-strategy cap の pre-reg (`weekend_gap_fade` の専用 cap 10.0p が同型の前例) / (c) 静的閾値の動的化 — **いずれも Rule 1 (365d BT + Bonferroni + pre-reg LOCK + user 最終承認) で autopilot は執行しない**。EV/WR/PnL も未計算 = `ps-carveout-regate-post-172` の凍結 look は未消費 (P-10 型 ban 準拠)
- 後続 registry **`ps-seat-spread-magnitude-readout` 新設 (期日 2026-10-19 = 計装 deploy + 4 週)** — magnitude 分布 (n/min/mean/max) を読んでから disposition を起案する。n=0 で期日到達時は「4 週ショックを引かなかった」と「配線落ち」の二択なので、まず `per_cell_metrics` キーの存在を確認して R3 再修理 → +4 週 roll (推測で起案しない)
- `python3 -m pytest tests/ -q` **3,416 passed / 17 skipped / 1 xfailed** / `python3 scripts/check.py` **全10チェック通過** (prereg registry lint OK)
- queue タスク `20260911-0200-ps-seat-hourly-c1-coverage-readout` を **done へ移動** (`## Claude Review` 付き、SLA 10 日滞留を解消)

## 2026-09-20 — fix(tools): weekly deepdive を in-repo 化 — **dedup 除外率の estimand 訂正** + **pre-reg LOCK セルの毎週再計算を停止** (rule:R3)

- **背景**: `tools/cell_deepdive_audit.py` は repo に存在せず、weekly scheduled run が **10 週連続** (2026-07-02〜09-20) で ad-hoc スクリプト (`knowledge-base/raw/cell_deepdive/_run_deepdive_<date>.py`) を打ち直して実行していた。テストが無いまま 2 欠陥が生存
- 🔴 **欠陥 A — pre-reg LOCK 下のセルの outcome 統計を毎週公表していた (P-10 違反)**: `sr_anti_hunt_bounce × EUR_JPY × BUY` (本体セル、LOCK `sr-anti-hunt-eurjpy-buy-forward-confirm`) / その Tokyo sub-cell / `× USD_JPY × BUY` (LOCK `ws3-t11-anti-hunt-usdjpy-recheck`) の WR/EV/PF/Wilson/p を印刷。**露出は今週分ではなく 2026-08-23 / 08-30 / 09-06 / 09-13 / 09-20 の 5 週分が既に main にある** (LOCK 発効 2026-08-05) ⇒ **「fresh N≥40 到達時に 1 回限り判定」という前提は本 PR 以前に実質崩れていた**。危険の向きは**偽陽性** (optional stopping で α が成立しない)。⚠️ レポート自身が「ツール自体が LOCK と構造的に衝突」と散文で認識しながら数値は出し続けていた = **検知ではなく作文**
- ✅ **修正**: `tools/cell_deepdive_audit.py` を新設し registry から active な `*_count_decision` の LOCK セル `(entry_type, instrument, direction)` を読む (`None` = ワイルドカード)。一致セル**およびその refinement (sub-cell)** の `wr/wilson_lo/ev_net/pf/p_raw/p_bonf/kelly/wf_stable/promoted/wins` を出力から除去し **`n` のみ残す** (トリガが数えるのは N なので運用は止まらない)。strict な super-set (戦略集計) は別 estimand につき対象外、`*_count_info` (頻度監視) も対象外。実測で **3 セル redact / `candidates` 1 → 0**。meta 計数 (raw 834 / dedup 427 / non-WL 22 / clean 385 / m_v2 7 / m_v3 1) は ad-hoc 版と完全一致 = 移植は忠実
- 🔴 **欠陥 B — 「N 枯渇の真因は発火数でなく dedup 除外率」は falsified**: `dedup_violation=1` は「直前の**採用**行から TF 窓以内」にのみ付き各窓の先頭は必ず残る (`modules/demo_db.py` write-time L1114-1145 / boot backfill L701-766)。実測でも flag 行は直前の採用行から **中央値 14-25 秒 / p90 ≤ 50 秒** (窓 900 秒、対象は全 tf=15m) = 同一バー内の tick 重複、かつ**採用行どうしの間隔は 1 件も窓を下回らない** (過剰抑制なし) ⇒ **独立観測を 1 件も取り除かず unique N の蓄積速度に影響しない**。`dedup_excluded / raw` を枯渇の指標に使ったのは分母の取り違え
- 🔵 **`mqe_gbpusd_fix` の 93.2% の正体**: 88 行中 **86 行が dedup ゲート導入 (commit 6a45bb2、2026-04-30T02:42Z) 以前**の凍結アーティファクトで **post-fix 除外率 0.0%** (post-fix raw = 2 行)。月次 `2026-04:87 / 2026-08:1` = **2026-05 以降 4.7 ヶ月で発火 2 本**。真因はレポートが否定した側の**発火枯渇そのもの** (unique 90d = 1 本 = **0.08 本/週**、最終 unique 発火 2026-08-28T15:31)。引用されていた「outcome は WIN 42 / LOSS 46 と拮抗」も大半が 4 月バースト由来で現状記述に使えない。`rsk_gbpjpy_reversion` の 68.4% は post-fix でも高いが月次で 90% → 22% へ減衰済み
- ✅ **正しい指標を出力**: `unique_accrual` (unique/週 90d: sr_anti_hunt 13.22 / rsk 2.57 / vsg 2.49 / vdr 1.48 / **mqe 0.08**) と `dedup_era_breakdown` (pre/post ゲート導入の分割) を新設し、除外率単独の提示をやめた。**M3 のスループット律速は「dedup 構造の是正」ではなく引き続きシグナル供給** — 本行のボトルネック帰属 (摩擦調整 EV 不在の帰結) は不変
- 🟠 **付随発見 — LOCK トリガの計数基準が読み手間で不一致 (未解決)**: `prereg_trigger_watch` は **36** (registry `closed_only: true` = CLOSED 全件)、weekly deepdive は **35** (`outcome ∈ {WIN,LOSS}`)。差 1 行は `outcome=BREAKEVEN`。pre-reg 原文は BREAKEVEN の扱いを規定していない (`closed_only` 自体 registry 側の補間)。判定式 ② `Wilson_lo(95%) > 38.7%` は WIN/LOSS の二値分母を要するため **トリガが N=40 で発火しても ② の実 N は ≤39** = 「宣言した N で判定した」前提が崩れる
- 🔴 **開示 (P-10 抵触)**: 上記の計数照合中に Claude が本セル fresh 行の WIN/LOSS 内訳を **1 回観測**。これにより計数基準の確定は Claude 単独では中立でない ⇒ **user 決裁へ**。ただし**重大なのは本観測ではなく 5 週の systematic exposure の方**
- **user 決裁点 2 件を registry へ追加 (いずれも期日 2026-10-12 = 本体トリガ ETA 2026-10 中旬の手前)**: `sr-anti-hunt-eurjpy-count-basis-declaration` (BREAKEVEN の扱い — **決め方は ② の分母定義との整合のみで行い outcome から優劣を判断しない**) / `sr-anti-hunt-eurjpy-lock-validity-disposition` (5 週露出を受けて凍結 α のまま判定してよいか)。**期日を超過して N≥40 が先に来た場合、判定は確定まで保留**
- ⚠️ **引用規律**: 本セルの今後の verdict を引用する際は 5 週の optional stopping 露出を必ず併記する。露出を伏せた「Bonferroni 通過」型の引用は禁止
- 🟠 **connector レビュー対応 (Codex P1×2 / P2×1、PR #273) — 3 件とも妥当につき修正**:
  (a) **LOCK 判定を統計計算の前に**移動 — 禁じられているのは「**再計算**」であって印字ではない。
  該当セルは `cell_stats`/`wf_stable`/Bonferroni を一切呼ばず `n` だけの record を作る
  (b) **registry 読み込み失敗を fail-closed 化** (`LockRegistryUnavailable`) — 旧実装は `[]` を
  返し**全 LOCK を黙って無効化**していた
  (c) **365d 窓を実際に適用** — 旧実装は `run_date` と比較せず「365d 監査」を名乗っていた
- 🔵 **(a) の pin (spy) が自分では見つけていなかった leak を 1 件露出**: **戦略レベル集計**が
  落ちた。「strict な super-set は別 estimand」の免除は**他ペアに行があるときだけ**成立し、
  ある戦略の行が全て LOCK セルに属すれば「集計」は **LOCK セルそのもの**になる
  (**leak 条件がデータ依存** = 静かに壊れる型)。⇒ 集計前に LOCK 行を除外し
  `locked_rows_excluded` を併記。`sr_anti_hunt_bounce` の集計 clean_N 247 → **135**。
  meta 計数は不変 (窓 filter は現データで no-op) で移植の忠実性の主張は維持
- 🟠 **レビュー第2波 (Codex P2×2) — 「N の estimand」が本 PR 自身にもあった**:
  (d) **LOCK の N を LOCK 自身の母集団で数える** — count-only record が `n=74`
  (セルの 365d Live+Shadow 行数) を**判定閾値 N=40 の隣**に出しており、
  **既に gate を通過したかのように読めた**。LOCK 母集団 (`since`=2026-08-05 以降の
  CLOSED shadow・`dedup_violation=0`) の実数は **36**。registry の母集団述語を保持・適用し
  `n_lock_population` / `n_decide` / `n_rows_in_window` に分離、曖昧な `n` は廃止
  (e) **inclusive 窓が 366 日だったのを 365 日に** (`window_days − 1`)
- ✅ **独立クロスバリデーション**: `lock_population_count` が `prereg_trigger_watch` と
  一致 (EUR_JPY **36/40** / ws3-t11 **22/30**) — 別実装の読み手が同じ数を出した
- 🔴 **本 PR だけで「隣に置いた閾値と estimand が合わない計数」が 3 例**
  (35 vs 36 / dedup 除外率の分母 / `n=74` vs 36)。**同じ病は、それを指摘している
  当の PR にも出る**
- 🔴 **レビュー第3波 (Codex P1 + P2) — fail-open の「対称な反対側」を塞いでいなかった**:
  (f) **構造的に不正な registry も拒否**: 第1波の fail-closed は「読めない」しか塞いでおらず、
  `{"triggers": "oops"}` / `[42]` は **JSON として妥当**なので通過し全 LOCK が消えていた。
  root / `triggers` の list 性と要素の object 性を検証し違反は `LockRegistryUnavailable`
  (g) **prefix LOCK を尊重**: registry の `match: "prefix"` (`prereg_trigger_watch` が実使用) を
  無視しており `kalman_d7_variant_a` 等が LOCK を素通りしていた。`_entry_type_matches` を新設し
  `lock_for_cell` と `lock_population_count` の**両方**に適用
- 🔴 **[[feedback_check_the_symmetric_side_2026_09_19]] の 3 度目の実例** — 自分で書いた教訓を、
  その教訓を引用している PR の中で踏んだ。✅ prefix 指摘は額面で受けず registry を実査して確認
- 🔴 **レビュー第4波 (Codex P1 + P2×2) — 欠陥の主系統は正本 `prereg_trigger_watch` との契約ズレ**
  (registry と正本ハーネスを実査して 3 件とも事実確認後に修正):
  (h) **marker 定義 LOCK を落としていた** — `hourblock-class-exempt-r2-rollback` は active で
  `entry_type` が空・`reasons_marker` で母集団を定義し正本も対応済みだが、本ツールは
  `entry_type` 空で `continue` して **active な decision LOCK を丸ごと無視**。marker LOCK は
  行集合なので `clean` を組む前に該当行を除去する方式に
  (i) **live LOCK の計数から重複行を無条件除外** — `count_live_matching` は無条件除外するのに
  本ツールは registry 明示時のみ。重複 live 行が `n_lock_population` を正本より大きくし
  **n_decide 到達に見せうる**。shadow 側も `count_basis == "unique"` を honor
  (j) **`active` 省略 = active** — 正本は `.get("active", True)`、本ツールは省略を非 active 扱い
  (現 registry に省略 0 件で実害は未発生、潜在的 fail-open)
- ✅ **3 度目の独立クロスバリデーション**: marker LOCK の `n_lock_population` = **2** が
  watcher の `live N=2/10` と一致。EUR_JPY **36/40** / ws3-t11 **22/30** と合わせ 3 本とも一致
- 🔴 **教訓: 同じ registry を読む 2 つ目の実装を書くときは、フィールド一覧ではなく
  正本の読み取りコードを仕様として読む**
- 🔴 **レビュー第5波 (Codex P1 + P2×2) — 「検査不能を異常なしに畳まない」の徹底**:
  (k) **`triggers` の欠落/空を拒否** — 正本 `load_registry_raw` は root 非 dict / キー欠落 /
  非 list / **空** の 4 つを全て拒否するのに、本ツールは `.get("triggers", [])` のままで
  `{"trigers": []}` も `{"triggers": []}` も空台帳に畳んで全 LOCK を消していた。
  正本契約を 1:1 移植 (綴り違いヒント込み)。🔴 **第3波で書いた pin「空 registry は正当」は
  誤りにつき撤回** — 正本契約に反し fail-open 自体を pin していた
  (l) **marker 除外にも LOCK の述語を適用** — reasons 文字列一致のみで `kind`/`since`/
  instrument/direction を見ておらず、live 限定・`since` 後の hourblock LOCK に対し
  **LOCK 外の shadow 行や `since` 前の行まで監査から削除**していた。
  `row_in_lock_population()` を単一の真実として抽出し N と除外の両方で共用
  (m) **`trades` を欠く API 応答を拒否** — エラーオブジェクトを空データセットに畳み、
  「0 行・候補なし」の**もっともらしい週次レポートで上書き**していた (実測 exit 1)
- 🔴 **over-exclusion は leak の鏡像** — P-10 的には安全側でも、実在する観測を黙って
  レポートから消すという別の嘘。片側だけ見ているともう片側を見落とす
- 🔴 **fail-open クラスはこれで 3 度目** (読めない → 構造不正 → キー欠落/空)。
  **「検査不能を異常なしに畳まない」は 1 つの不変条件で、入力形状ごとの個別対応ではない**
- 🔴 **レビュー第6波 (Codex P1×2) — 計数自体が outcome の関数だった**:
  (n) **LOCK 行を outcome を読む前に分岐** — LOCK セルの行も先に WIN/LOSS フィルタを通って
  いたため **出力される計数そのものが `outcome` の関数**だった (BREAKEVEN 1 本で計数も
  セルの出現可否も変わる)。**これは本 PR が §4 で指摘している 35 vs 36 そのもので、
  それを直すためのツールの中で再現していた**。raw 段階で分岐し `outcome`/`pnl_pips` を
  一度も読まず count-only record を作る。計数は `n_unique_rows_in_window` に改名
  (o) **selector 無しの active decision を拒否** — 綴り違い/削除された selector が
  構造検査を通って黙って捨てられ、**LOCK を消したまま監査は当該母集団を公表**していた
- 🔵 **実測の裏付け**: 修正後 `sr_anti_hunt_bounce × EUR_JPY × BUY` の計数が **74 → 75**、
  **増えた 1 本がまさに BREAKEVEN 行** = §4 の「35 vs 36」の差分と同一行。
  `× USD_JPY × BUY` も 28 → 35
- ⚠️ **「移植は忠実」の主張を更新**: 本修正で `clean_N` **385 → 273** (LOCK 行 215 を
  routing 除外)。**「ad-hoc 版と同一」はもはや成立しない** — 同一なのは非 LOCK セルの統計
  (`sr_anti_hunt_bounce` 集計 clean_N 135 / WR 0.519 / EV −4.27 / PF 0.37) と
  `m_v2`=7 / `m_v3`=1 / `candidates`=0。多重度は保守側を取り LOCK セルも `m` に数え続ける
  (外すと `m` が縮み他セルの `p_bonf` が通りやすくなる)
- 🔴 **レビュー第7波 (Codex P1×1) — meta 診断値にも outcome が漏れていた**:
  (p) `meta.non_winloss_excluded` が `target_all` (LOCK 行込み) で `outcome` を読んでおり、
  LOCK 行 1 本を WIN→BREAKEVEN にすると **count-only record は不変なのにメタデータが 0→1**
  に動いていた。`open_raw` から計算するよう変更 (実測 **22 → 13**)。
  `dedup_violation_excluded` は outcome 非依存につき全行対象のまま
- 🔑 **不変条件を「性質」として pin し直した** — フィールドを列挙せず
  **「LOCK 行の outcome を反転させてもレポート JSON 全体が 1 バイトも変わらない」**を
  直接 assert。本 PR が主張する性質そのもので、フィールドが増えても自動で守られる
  ([[lesson_validity_check_pins_proxy_2026_09_02]] の適用)
- 🔴 **レビュー第8波 (Codex P1 + P2) — 多重度族の分割 = 本 PR で最も statistically 重い欠陥**:
  (q) **v2 と v3 を 1 つの多重度族で補正** — 別々の `m` を当てて結果を merge していたため
  **単独の v3 sub-cell が多重度ペナルティをほぼ受けずに通る** (`m_v3=1` ⇒ `p_bonf=p_raw`)。
  🔴 **これが Tokyo sub-cell が 4 週連続「候補」に出ていた機構**で、しかも
  **レポート本文は「v2∪v3 (m=8) なら p_bonf=0.0720 → FAIL」と正しく書いていた**。
  `m_family = m_v2 + m_v3` を単一族として適用 (実測 m_family = **8** = 本文と一致)
  (r) **accrual 窓を名乗った長さに** — `>= as_of − d 日` が両端込みで d+1 日を数え、
  signal 枯渇の診断に使う accrual rate を過大に出していた
- ⚠️ **引用値の訂正** (行アンカー完全一致 + `--word-diff` 全数照合):
  `sr_anti_hunt_bounce` 13.46→**13.22 本/週**、`vdr_jpy` 1.56→**1.48**。
  **`mqe_gbpusd_fix` の 0.08 は不変**で §1.4 の結論に影響なし
- 🔴 **「文章では正しく、コードでは違う」の 3 例目** (LOCK 衝突の認識 / 正本契約 / 多重度族)
- 🟠 **レビュー第9波 (Codex P2) — 正本の方が pre-reg から外れていた例**:
  (s) shadow LOCK の母集団が pre-reg 原文 (**shadow rows のみ**) と正本
  `count_matching` (**`oanda_trade_id` で絞らない**) で食い違う。現データは
  **両者 36 で一致**しており潜在だが、本セルが live fill を取れば
  **watcher が先に発火したのに監査は未達と表示する**事故になる。
  **どちらも採らず両方を出力** (`n_lock_population` / `n_lock_population_watcher` /
  `watcher_divergence` / `watcher_divergent_locks`) し、決裁点
  `sr-anti-hunt-eurjpy-count-basis-declaration` に第 2 の論点として追記
  (BREAKEVEN の扱いと **1 回で決める**)
- 🔑 **「正本の読み取りコードを仕様として読め」(第4波) は「正本が常に正しい」ではない** —
  正本と凍結文書が食い違ったら、勝手にどちらかへ寄せず**両方出して決裁に上げる**
- 🟠 **レビュー第10波 (Codex P2×2) — 厳格 shadow の定義と as-of 上界**:
  (t) **厳格 shadow は `is_shadow` も要る** — `rnb-support-bounce-shadow-forward` の LOCK 文が
  逐語で「厳格 shadow = is_shadow=1 ∧ oanda_trade_id 空」と定義しているのに OANDA id しか
  見ておらず、**flag-drift 行 (id 空 ∧ is_shadow=0) を shadow として数えて**いた。
  **PROD に該当行が実際に 47 本存在**。faithful 側に `is_shadow` を追加、
  `watcher_compat` は正本の広い挙動を維持
  (u) **LOCK 計数に監査の as-of 上界** — payload 全体を数えており、過去日付の `--run-date` を
  現スナップショットで再実行すると run 後の行まで数えていた。`since` は下界として独立維持
- 実測: PROD の LOCK 計数は **36/36・22/22・marker 2 のまま不変** — 修正は将来の事故を
  塞ぐもので今回の数値解釈には影響しない
- 🔑 **指摘を仮説として受け取らず PROD を数えた**ことで、理論上の穴ではなく
  「いつ踏んでもおかしくない穴」と確定できた
- 🟠 **レビュー第11波 (Codex P2×2) — 過剰 redaction と過少報告 (いずれも leak の鏡像)**:
  (v) **redaction を本物の outcome LOCK に限定** — 全 `*_count_decision` を redact していたが
  **3 件は件数監視のみで凍結 outcome look を持たない** (lane-health checkpoint ×2 /
  weekend_gap 転換監視)。**正当な監査結果と昇格候補まで握り潰していた**。
  registry に `outcome_lock` フラグを新設し 3 件に `false` を明示、**既定は redact** で保守側。
  `prereg_trigger_watch` の key allowlist にも登録
  (w) **min_n 未満の LOCK セルも報告** — 在庫が `min_n=20` 以上に限られ、自分の閾値が
  min_n 未満の LOCK (kalman `n_decide=10`) は宣言 look 到達でも**何も表示されなかった**。
  在庫は全非空 LOCK 群から作り `min_n` は多重度資格にのみ使う (redacted 3 → **15** セル)
- 🔴 **文面推測の実装は実際に誤分類した** — 「count のみ」で grep すると
  **`rnb-support-bounce-shadow-forward` (本物の outcome LOCK) を件数のみと誤判定**
  (その文言は同エントリが併設する checkpoint の説明だった) ⇒ **明示フラグで表明する**
- ✅ registry lint が新キーを正しく弾いた (reject-by-default が設計どおり機能)
- 🟠 **レビュー第12波 (Codex P2) — 新フラグに型検査が無かった**: 第11波で足した
  `outcome_lock` を `META_FIELDS` にだけ登録したため lint が `"false"` / `0` / `null` を
  素通りさせ、`is False` 判定の opt-out が効かず**件数モニタが黙って outcome lock 扱いに
  戻る**状態だった。`BOOL_FIELDS` へ追加 (3 形状すべて lint 拒否を実測、真 bool と
  キー未記載は通る)
- 🔑 **ガードを足したら、そのガード自身の入力も検査する** — `closed_only: "false"` の穴は
  registry lint が既に塞いでいたのに、**同じ穴を新フラグで作り直した**
- 🟠 **レビュー第13波 (Codex P2) — まだ始まっていない LOCK が過去を消していた**:
  (x) LOCK の `since` より前で終わる窓を再実行しても セル一致だけで routing しており、
  **未発効の LOCK が過去の監査結果を redact** していた (実測 `--run-date 2026-07-01` で
  **14 セル redact / 全て `n_lock_population: 0`**)。`since >= 窓の上界` の LOCK を
  routing 前に除外し、除外分を `locks_not_yet_started` に列挙して省略を可視化。
  検証: 07-01 は redact **0** / clean_N 173、09-20 は redact **15** / clean_N 273 で不変
- 🔑 **over-redaction は本 PR で 3 度出た** (件数モニタ / min_n 未満 / 未発効 LOCK) —
  **leak を塞ぐガードは塞ぎすぎる方向にも同じ数だけ穴を開ける**。「redact する条件」を
  足すたびに「redact してはいけない条件」を対で確認する
- 🟠 **レビュー第14波 (Codex P2×2) — routing が母集団でなくセルで切っていた**:
  (y) **LOCK 母集団の行だけを routing** — `(entry_type, instrument, direction)` だけで
  退避しており、**LOCK の `kind`/`since`/`closed_only`/dedup を満たさない同一セル行まで
  巻き込んで**いた。⚠️ **指摘は本 PR が公開した出力を証拠にしている**
  (「in-window unique **75** を退避、LOCK 母集団は **36**」)。`row_in_lock_population` を
  routing に適用し、母集団外は **unlocked complement** として評価継続 +
  `lock_complement_only` で部分ビューと明示
  (z) **完全なスナップショットを要求** — `/api/demo/trades` は **default limit=50** で、
  help どおり素朴に curl すると truncate された監査が週次サマリを上書きしていた。
  50 行ちょうど / `--min-rows` (既定 1000) 未満 / `count != len(trades)` を fail-loud に
- **実測**: `locked_rows_routed_out` **215 → 58** / `clean_N` **273 → 335** /
  EUR_JPY BUY の redacted 記録は **uniq 75 → 36** で `n_lock_population` と一致
- 🔑 **「LOCK が覆う範囲」と「LOCK セルの全行」は別物** — over-redaction の 4 度目。
  母集団述語を 1 箇所に集約してあったので routing 側 1 行で整合した
- 🔴 **レビュー第15波 (Codex P1 + P2×2) — 最小値は完全性の証明ではない**:
  (aa) **壊れた `match` 選択子で fail closed** — `"prefx"` 等が黙って exact に落ち、
  prefix LOCK が variant を覆わず**凍結統計を公表**しうる状態だった
  (bb) **最小行数は完全性の証明でない** — `?limit=1000` は 1000 行ちょうどを返し
  `count` も page 長なので `--min-rows 1000` を素通りする。**short page でのみ完全性を
  証明**する `--fetch-limit` を導入 (`paginate_closed_trades` と同じ idiom)
  (cc) **訂正文が機械可読側と食い違っていた** — 週次レポートの訂正節が `clean_N=273 /
  routed 215` のままで `_summary.json` は **335 / 58**。§2.3o の routing narrowing で
  陳腐化。**335 / 58 へ更新 + prose ↔ JSON 一致の pin を追加**
- 🔴 **「文章では正しく、コードでは違う」の 4 度目 — 今回は自分の KB 記述**。
  同じ病を 3 回コード側で指摘しておきながら訂正文が数値ドリフトした ⇒
  散文の数値主張を **JSON から機械検査**する pin を置いた
- 🔑 **「閾値を超えた」は「正しい」ではない** — full page はいつでも閾値を超える。
  完全性は「短いページ」でしか証明できない
- 🔴 **レビュー第16波 (Codex P1 + P2) — 自前ガードは正本を追い越せない / 表明は証拠でない**:
  (dd) **綴り違いの selector キーも拒否** — 第15波で `match` の「値」を検証したが
  `"mtach": "prefix"` は「キー不在」枝で **exact lock** になっていた。
  **自前検証をやめ正本 `lint_registry` に委譲** (unknown key の reject-by-default を継承)
  (ee) **完全性は snapshot が運ぶ** — `--fetch-limit` はファイルに記録されない値についての
  caller の表明にすぎず、`?limit=1000` 取得を CLI 既定で監査すると通ってしまう。
  `paginate_trades()` で **short page を実見してから** `_fetch_meta.complete=true` を書き、
  監査側はそれのみを証拠として受理 (`--fetch-to` / `--allow-unverified-snapshot`)
- 🔑 **個別の穴を塞ぎ続ける限り常に 1 歩後ろ** — 正本 linter を呼べば将来の規則も自動で効く
- 🔑 **表明は証拠ではない** — 完全性のような性質は**生成時に確立して成果物に埋め込む**
- 🔴 **レビュー第17波 (Codex P2) — 自分で足した pagination が行を落としていた**:
  (ff) 第16波の `paginate_trades` が既定 `status=all` で叩いており、`app.py` は
  `status=all` で **`open_t + closed_t`** を返す (= 全 open 行を毎ページ先頭に付ける)。
  offset を累積長で進めるため **closed を K 行スキップ**し open は重複、
  それでも short page で `complete=true` が立つ ⇒ **「完全性を証明した」スナップショットが
  outcome を欠落**。closed は `status=closed` でページング、open は一度だけ取得して結合
- 🔑 **完全性の「証明」はページング意味論の正しさを前提にしている** — 第16波で
  「表明でなく証拠を」と正した直後に**その証拠の作り方が壊れていた**。
  証拠を生成する経路も検証対象
- 🟠 **レビュー第18波 (Codex P2×2) — fetch 経路と help が契約に追いついていなかった**:
  (gg) **壊れたページで abort** — `payload.get("trades", [])` が HTTP-200 のエラー
  オブジェクトを `[]` にし、`paginate_trades` がそれを**データ終端**と読んで
  成功済みページだけで `complete=true` を立てていた ⇒ truncate された snapshot が
  「証明済み」になる。list 値の `trades` を検証し無ければ `SystemExit`
  (hh) **help の例が契約を満たしていない** — bare curl を案内したままで CLI はそれを拒否、
  手順どおり実行すると必ず落ちる。`--fetch-to` → 監査 の 2 段手順へ
- 🔑 **契約を強めたら、その契約を語る文書も同じコミットで更新する** — 第16波で導入した
  完全性契約に help を合わせず、**公式手順が常に失敗する**状態を 2 波放置していた
  (§2.3n の「文章が正しくコードが違う」と**向きが逆の同型**)
- 🔵 **pin が自分のバグを即座に捕捉**: help の `$(date -u +%F)` が argparse の
  %-formatting で `TypeError` → `format_help()` を呼ぶ pin が落ちた (`%%F` へ修正)
- 🔴 **レビュー第19波 (Codex P1) — 「最初に一致した LOCK」しか見ていなかった**:
  (ii) 同一セルを**異なる母集団の 2 つの active LOCK** が覆う場合、live 行が先頭の
  shadow LOCK の母集団検査に落ちて **complement に回り WR/EV が公表**されていた
  (実際には 2 つ目の live LOCK に属する)。正本 linter は selector 重複を禁じていない。
  `locks_for_cell()` を新設し「**いずれかの LOCK の母集団に入るなら退避**」へ変更、
  複数が覆うセルは `covering_locks` に LOCK ごとの母集団と n_decide を個別出力
- ⚠️ **現 registry では実害ゼロ** (active outcome LOCK 7 件に selector 重複 **0 件**を実測)
  — 潜在的欠陥で、修正は将来の重複登録への予防
- 🔑 **over-routing を直すと under-routing が生まれる** — §2.3o で「母集団で切れ」と
  直した際、**その母集団検査をどの LOCK に対して行うかを 1 つに固定**したままだった
- 🟠 **レビュー第20波 (Codex P2 + P3) — そして指摘の「残り半分」を自分の pin が反証した**:
  (jj) **page drift の de-dup + カーソルを「配信済み行数」に** — `get_closed_trades` は
  keyset も snapshot も無い素の `ORDER BY exit_time DESC LIMIT ? OFFSET ?` なので、
  フェッチ中に約定が CLOSE すると先頭に挿入され、通過済みの行が 1 offset ずれて
  **境界行が再読される**。未 de-dup では N / 多重度族 / LOCK 母集団計数が膨らむのに
  `complete=true` が保証していた。カーソルは**サーバが配信した行数**でなければならない
  (採用行数で進めると同じ offset を無限に再要求する)
  (kk) **P3: 広告された `--min-rows 0` を実際に到達可能に** — 50 行ちょうどの truncation
  署名検査が `--min-rows` 検査より前で**無条件**に走っていたため、エラー文が名指しする
  脱出口が原理的に効かなかった。`--min-rows` の default を `None` にし
  「呼び手が何も言っていない」と「意図的に下げた」を区別
- 🔴 **指摘は欠陥の半分しか述べていなかった (本波で最も重い所見)**: Codex P2 は drift を
  「**重複する**」としか書かず、こちらもそれを受けて docstring に
  「*drift duplicates, it never skips … de-dup すれば union は exact*」と**書いてしまった**。
  **これは偽**。前方挿入された当の行は**カーソルが既に通過した offset に着地する**ので
  **一度も配信されない = SKIP される**。de-dup は膨張を直すが**欠落は直さない** ⇒
  drift した pass の union は exact ではなく、**最新の CLOSE 済み約定を欠いたまま**
  短ページが終端を「証明」する。🔴 **残差の向きは UNDER-count** = 「取引が無かった」と
  読める方向 ([[project_hunt_events_dataset_readout_2026_09_19]] と同じ偽陰性の向き)
- ✅ **修正 = 「de-dup して complete と名乗る」から「drift-free な pass を要求する」へ**:
  重複を 1 件でも落とした pass は**証拠つきで破棄して再実行** (その時点で挿入行は安定
  offset に居るので再走が拾う)、全試行が drift したら `SystemExit`。成功時の meta に
  `attempts` と破棄した pass の `drift_observed` を残し、**黙って吸収しない**。
  実測 pin: drift 1 回 → `attempts=2` / `drift_observed=[1]` / 挿入行 99 も収集
- 🔵 **副次効果**: `status=all` ページング形状 (open 行が全ページに前置される) は
  毎試行 drift 証拠を出すため、**第16波で「危険だがそのまま complete=true を返す」と
  pin していた経路が fail-loud になった** — pin を新挙動へ更新
- 🔑 **教訓: 指摘された欠陥の「対称な残り半分」を自分で確認する** — 当の pin
  (`test_pagination_dedups_drift_and_uses_a_served_row_cursor`) は
  「99 も 1 度だけ収集される」と assert しており**最初から落ちていた**。つまり
  **前回セッションは自分の pin が赤のまま作業を置いていた** ⇒
  [[feedback_commit_exit0_lies_autosaver_bypasses_precommit]] の「suite green は
  測ったツリー状態でのみ有効」と [[feedback_check_the_symmetric_side_2026_09_19]] の
  2 例目。**レビューが片側を指摘したら対称側は自分で測る**
- 🟠 **レビュー第21波 (Codex P2×3) — 3 件とも妥当、うち 1 件は第20波の穴の「隣」だった**:
  (ll) **open 行を closed ページング の前に取る** — 旧順序では closed pass 終了後・open
  要求前に CLOSE した約定が**両方の集合から欠落**する (closed を読んだ時点では open、
  open を要求した時点では既に closed) のに `complete=true` が保証していた。
  🔴 **第20波の retry はこの窓を塞がない** — retry が見るのは closed pass 内部の drift だけ。
  open を先に取ると同じ窓が**穴から重複へ**変わり `merge_open_into_closed` が identity で
  解消できる (**重複は修復可能、穴は検出さえできない**)
  (mm) **redact されたセルの primary を「実際に一致した LOCK」に** — routing は「いずれかの
  覆う LOCK の母集団に入れば退避」なので、**registry 順で先頭の LOCK が 1 行も持たない**
  ことがある。`covering[0]` を primary にしていたため compact な `redacted_cells`
  (`covering_locks` を落とす) が**無関係な LOCK の registry_id / 閾値 / 母集団 0** を
  redaction の原因として公表し、トリガ進捗を誤って伝えていた。matched 数の argmax
  (同数は registry 順) を primary にし `n_rows_matched` / `primary` を併記
  (nn) **as-run レポートの手順も bare curl のままだった** — 第18波で `--help` を直したのに
  **週次オペレータが従えと明記されている当のレポート**が残っていた (同型の 2 例目)
- 🔑 **pin は「性質」で、しかもスコープを絞って書いた**: 「**このツールに言及する doc は
  `/api/demo/trades` への runnable curl を含まない**」を全 KB に対して assert。
  他用途の curl と歴史記録は対象外 (書き換えてはいけない) — [[lesson_validity_check_pins_proxy_2026_09_02]]
- ✅ **3 件とも counterfactual で確認** (修正を戻すと当該 pin が落ちる): 順序 pin は
  **機構 (呼び出し順) より先に実体 (`[8] == [8, 9]` = 約定 9 の消失)** を assert するよう
  並べ替え — 回帰時に「並べ替えた」ではなく「データを失った」と報告される
- 🟠 **レビュー第22波 (Codex P2×2) — 第21波の修正が生んだ鏡像と、第11波の取りこぼし**:
  (oo) **fetch を「open → closed → open」の bracket に** — 🔴 **第21波 (ll) で
  closed→open の穴を塞いだら、open→closed の鏡像の穴が開いていた**: パス中に
  **新規 OPEN した**約定は open 要求時点では未存在、CLOSE しないので closed ページにも
  現れず、**どちらの集合にも入らない**まま `complete=true` が保証していた。
  ⇒ closed パスを **2 回の open 読み取りで挟む**。`open_before ∪ open_after` が
  mid-pass open を捕まえ、かつ **open_before に居て open_after にも closed にも
  居ない行 = 窓の内側で CLOSE して誰にも配信されなかった行 = 穴**として検出可能になる。
  穴は証拠なので attempt を破棄して再走、全試行で穴なら `SystemExit` (第20波 drift と
  同じ規律)。meta に `open_attempts` / `open_opened_midfetch` / `holes_observed`
  (nn2) **全行が dedup repeat の LOCK が棚卸しから消えていた** — 棚卸しの**キー集合**を
  dedup 後の行から作っていたため、`dedup_violation=1` の行しか持たない LOCK は
  `redacted_cells` から**丸ごと消滅**し `n_lock_population` の record が 1 件も出なかった。
  `ws3-*` shadow decision は unique/dedup 述語を宣言しないので**正本 watcher はその行を
  数える** ⇒ **LOCK が `n_decide` に到達しているのに監査が何も報告しない**状態になりうる。
  キー集合は raw 行から、計数は dedup 後から (**別の問い**) に分離し、
  `n_unique_rows_in_window=0` を正直に出す。帰属 (第21波 mm) も raw 行で計算する
  (unique が空だと argmax が registry 順に退化するため)
- 🔴 **教訓の 3 例目: 片側の穴を塞ぐと鏡像が開く** — 第21波 (ll) は Codex の指摘どおり
  「closed→open の穴」を直したが、**順序を入れ替えるという形の修正は窓を消さず移動させる**
  だけだった。窓そのものを消すには**両端を測る (bracket)** しかない。
  [[feedback_check_the_symmetric_side_2026_09_19]] の 3 例目で、今回は
  **自分の修正が生んだ**鏡像 — 「対称側を確認する」は修正前の状態だけでなく
  **修正後の状態に対しても**回す必要がある
- 🔴 **危険の向きは一貫して UNDER-count** (第20波 skip / 第21波 hole / 第22波 mirror hole /
  (nn2) の LOCK 消滅)。**この PR の欠陥族は全て「無かったことになる」方向**に倒れていた
- pin 63 → **66 本**。4 件すべて counterfactual 確認済 (修正を戻すと当該 pin が
  実体のメッセージ付きで落ちる — 「棚卸しから消えた」「mid-pass open が入っていない」)
- 🟠 **レビュー第23波 (Codex P2) — 契約を強めた当の関数に fail-open が残っていた**:
  (pp) **endpoint からの top-level list を拒否** — 第18波 (gg) で「`trades` を欠く応答を
  拒否」を入れたのに、その直前で **`isinstance(payload, list)` を無条件に通す**分岐が
  残っていた。`/api/demo/trades` は常に `trades` を持つ**オブジェクト**を返すので
  (app.py)、bare list は**定義上 malformed 応答しか通さない** — そして HTTP-200 の
  `[]` (proxy ノイズ等) が来ると `_paginate_pass` がそれを**短ページ = データ終端**と
  読み、既に取得した部分ページを保持して `complete=true` を立てる。
  **塞いだはずの穴を、同じ関数の 3 行上が開けていた**
- 🔑 **ただし「保存済み snapshot の reader」は bare array を受け続ける (意図的)** —
  ローカルファイルは**別母集団**で、手作りや `jq '.trades'` の出力は正当。完全性は
  `_fetch_meta` で別途 gate される。**どの規約がどの母集団に固有かは母集団ごとに
  決める** ([[feedback_check_the_symmetric_side_2026_09_19]])。pin は両方を主張
  (endpoint は SystemExit / local reader は list 受理を維持)
- pin 66 → **67 本**。counterfactual 確認済 (passthrough を戻すと `DID NOT RAISE`)
- 🟠 **レビュー第24波 (Codex P2×2) — 完全性の主張を「発見的」から「証明」に上げた**:
  (qq) **v3 の帰属は自分の session の行だけで計算する** — v3 キーから `session` を落として
  `locked_raw` を引いた後、**親セル全体の行**で `matched` を計算していたため、
  **セル内の全 v3 record が同じ「セル全体の primary」を選ぶ**。shadow LOCK が Tokyo に、
  live LOCK が London に集中していると、**少なくとも一方の session が他方の
  registry_id / n_decide / n_rows_matched を報告する**。落とした次元で絞り直す
  (rr) 🔵 **bracket 内で「生まれて死んだ」約定を検出可能にした** — `open_before` の後に
  OPEN し `open_after` の前に CLOSE し、かつ closed カーソルが挿入点を通過済みだと、
  **3 つの読み取りすべてに現れない** ⇒ open 行を起点にした穴検査では**原理的に見えない**。
  ⇒ **確認用の 2 回目 closed pass** を追加。**CLOSED 行は append-only (削除されない)** ので
  `confirm ⊇ closed` が常に成り立ち、**差集合はちょうど bracket 中に CLOSE した集合**になる。
  したがって**一致は「窓の内側で何も CLOSE しなかった」ことの証明**であって発見的規則ではない。
  🔑 **これで完全性の意味が「4 読み取りが整合した」= 検証可能な主張に変わった**
- 🔑 **穴の 2 信号は合算せず別々に報告** (`open_rows_lost` / `closed_during_bracket`) —
  **同一の約定が両方を立てる**ので、足すと「取り逃した行数」を過大に言うことになる。
  pin が最初に捕まえたのはこの二重計上だった
- pin 67 → **69 本**。2 件とも counterfactual 確認済 (v3 を親セルへ戻すと
  `got live-london`、確認 pass を外すと `holes_observed == []`)
- 🔴 **レビュー第25波 (Codex P2) — 「重複の片方を選ぶ」は無害な選択ではなかった**:
  (ss) **2 回の open 読み取りで同じ identity が両方に出たら `open_after` を採る** —
  旧実装は `open_before` 側を残していた。open 行は**通常の live 経路で変化する**:
  OANDA callback の `DemoDB.set_oanda_trade_id()` が**行が OPEN のまま**
  `oanda_trade_id` を埋め `is_shadow` を反転させる。bracket は identity を
  比較するので**この変化はどの穴検査にも掛からず**、古い copy を残すと
  **live 約定を shadow として報告する** — 本プロジェクトが最も load-bearing と
  扱っている区別そのもの ([[feedback_live_vs_shadow_strict_separation]] /
  混同事故 [[project_live_fill_estimand_shadow_conflation_2026_09_03]])。
  新しい読み取りは snapshot 時点の真実に厳密に近いので `open_after` が勝つ。
  変化数は `open_mutated_midfetch` として meta に残す (**identity ベースの検査には
  映らないので、記録しなければどこにも残らない**)
- 🔑 **dedup/union を書くときは「どちらの copy を残すか」を必ず意味で決める** —
  第21波の `merge_open_into_closed` では「CLOSED 側が exit_time を持つから勝つ」と
  意味で決めていたのに、第22波で足した open 側の union では**先に入れた方が残る**
  という実装の副作用に任せていた。**同じ PR の中で規律が片側にしか適用されていなかった**
- pin 69 → **70 本**。counterfactual 確認済 (古い copy を残すと
  `got {'is_shadow': 1, 'oanda_trade_id': ''}` で落ちる)
- 🔴 **レビュー第26波 (Codex P2) — 第25波の修正の鏡像を、自分で確認していなかった**:
  (tt) **確認用 closed pass は「値」でも勝つ** — 第25波で open 行について
  「新しい読み取りが勝つ」と決めたのに、**closed 2 パスは identity しか比較せず
  古い `payload` を返していた**。closed 行も通常の非同期 OANDA 経路で変化する:
  `DemoDB.set_oanda_trade_id()` は **status を条件にしていない**ので、速く CLOSE した
  約定が closed 集合に入った**後**に `oanda_trade_id` / `is_shadow` を書き換えられる。
  キー集合が一致すると完全性チェックは通り、**古い shadow 表現が `complete=true` の
  下で書き出される** ⇒ live/shadow の LOCK 母集団が誤る。⇒ 値でも confirm を採り
  `closed_mutated_midfetch` を計上、confirm pass 自身の drift 証拠も
  `confirm_pass` として保存 (完全性の論拠の一部なので捨てられない)
- 🔴 **「対称側を確認する」は修正後の状態にも回す — これで本 PR 3 例目**
  (第21波→第22波の鏡像 / 第25波→第26波の鏡像)。**自分が直した直後のコードが
  次の非対称の発生源になる**というのが本 PR で最も再現性の高いパターンだった。
  ⇒ dedup/union/2-pass を書いたら「**どちらの copy が勝つか**」を
  **両方の集合について**明示的に決めたか、を修正の完了条件に加える
- pin 70 → **71 本**。counterfactual 確認済 (古い pass を返すと
  `got {'is_shadow': 1, 'oanda_trade_id': ''}` で落ちる)
- 🟠 **レビュー第27波 (Codex P2×2) — 読み取りを足すのをやめて「as-of を定義」した / 正本との乖離は片側を選ばず両方出す**:
  (uu) **末尾の open 読み取りを最後に置き、スナップショット境界を明文化** — 第26波で
  `open_after` の**後ろ**に confirm pass を足したため、**confirm 実行中に OPEN した約定**が
  どの読み取りにも入らなくなっていた。🔑 **読み取りを 1 本足すと窓が 1 つ後ろへ移るだけ**で、
  これは無限後退する形。⇒ 順序を `open → closed → closed(confirm) → open` に変え、
  **末尾 open の瞬間を snapshot の as-of と定義**した。「as-of の後に OPEN して CLOSE しない
  約定はこの snapshot に含まれない」は**欠陥ではなく境界**であり (非 atomic な読み取り列で
  含める方法は存在しない)、**欠陥なのは「as-of より前に存在したのに欠けている行」**
  — 2 つの検査はまさにそれを見ている。**完全性の主張を「as-of 相対」で述べ直した**
  (vv) **`since` 前に OPEN した live 約定を watcher に合わせる** — live LOCK について
  正本 watcher は `fetch_trades_window()` に `date_from` を渡すが、endpoint の **OPEN 分岐は
  そのパラメータを無視する**ので `count_live_matching()` は**当該行を数える**。本ツールは
  除外していた。**どちらが正しいとも言えない** (pre-reg 原文は `since` で母集団を切り、
  watcher はトリガを実際に発火させる側) ⇒ **§9 と同じ規律で片側を選ばず両方出す**
  (`n_lock_population` vs `n_lock_population_watcher` を並置)。決着は
  `sr-anti-hunt-eurjpy-count-basis-declaration` に委ねる
- 🔵 **vacuous pin を counterfactual が捕まえた** — (uu) の pin は当初 open 呼び出し回数で
  分岐する stub を使っていたため、**修正を戻しても通ってしまった**。stub を
  「**closed pass が 2 本終わったか**」で分岐する形に直して初めて `[] == [6]` で落ちた。
  **「pin を書いた」と「pin が効く」は別** — 全 pin に counterfactual を回す理由がこれ
- pin 71 → **73 本**。2 件とも counterfactual 確認済
- **pin** `tests/test_cell_deepdive_lock_redaction.py` (**73 本**、buggy shape を再現して比較): redaction の assertion はすべて**非 redaction の counter-pin と対** (全部 redact / 何も redact しない の双方が落ちる) + 実 registry ロード検査 (LOCK を含む ∧ `*_fire-info` を含まない ∧ 解決済みを含まない) + **算術 pin** (`DEDUP_GATE_FIX_TS` ≡ `DemoDB._DEDUP_BACKFILL_CUTOFF`)。教訓「検知器には NG を返す既知の入力を同じコミットで pin せよ」の適用
- **残課題**: 他の読み手 (`r2_cell_demotion_audit` / `alpha_scan_block_recalibration` / `cell_edge_audit`) の LOCK セル露出の横展開 grep は**本 PR では未実施** (deepdive 経路のみ封鎖) / LOCK セル用「`n` だけを返す」計数ヘルパ (ad-hoc クエリ経路の封鎖) / `mqe_gbpusd_fix` の発火枯渇の signal 側調査
- 成果物: `tools/cell_deepdive_audit.py` / `tests/test_cell_deepdive_lock_redaction.py` / [[deepdive-dedup-estimand-and-lock-redaction-2026-09-20]] / `knowledge-base/raw/cell_deepdive/2026-09-20/` (as-run 保存 + 訂正 addendum) / roadmap v2.3 M3 行 追補

## 2026-09-19 — fix(monitoring/KB): 未消化レビュー指摘の消化 ② — GDELT の soft 分類が全例外を飲んでいた + 撤回済み主張が見出しに残っていた (rule:R3)

**PR #261 / #263 / #264 の未消化 P1/P2 指摘 6 件の消化。** (① = hunt_events readout、別 PR)

### GDELT (PR #261 Codex P2) — 分類が広すぎ、かつ第 3 の失敗形が見えていなかった

- **指摘**: `_SOFT_SOURCES = {"gdelt"}` により `run_gdelt` の**全例外**が soft に落ち、`main()` が exit 0 になるため workflow の `Notify failure` が走らない。恒久的な API/schema 変更や書込み失敗でも CSV が無期限 stale で残る。✅ **確定**
- **対処 ①**: soft 判定を「ソース名」から「**ソース名 ∧ 例外形状**」へ。`ing.is_transient_fetch_error()` に集約し、`TransientFetchError` (429/500/502/503/504 と curl 7/28/52/55/56) のみ soft。`unexpected GDELT response` (上流恒久変更の署名) と `OSError` (書込み失敗) は **hard**。**列挙に無い形状は hard = fail-closed** — 上流がエラー表現を変えたら過剰 alert 側に倒れる方が、黙って stale で残るより安全 (文字列判定である以上この向きは崩せない)
- 🔵 **対処 ②: 指摘が名指ししていない第 3 の失敗形を実測で発見した** — GDELT は **HTTP 200 + 正当な CSV ヘッダのまま系列が進まない**ことがあり、その形は**例外軸からは永久に見えない**。実測: committed CSV の末尾は **2026-09-13** で 3,518 行、**09-18 の run は "success" で同一の 3,518 行を書き diff ゼロ**。つまり本日 (09-19) 時点で **6 日 stale なのに監視は何も言っていない**。soft 分類の前提「全範囲を毎回再取得するので自己修復する」は、**上流が進まない場合には成立しない**
- **閾値は仮定せず実測した**: `commit 日 − 系列末尾日` を CSV の git 履歴 **16 commit** で測ると **median 0 日 / max 1 日** ⇒ 内在ラグはほぼゼロ。`GDELT_STALE_DAYS_MAX = 3` は観測 max の **3 倍**で内在ラグでは誤発火しない。⚠️ 誤発火が出たら閾値は**上げる** (下げると何も検知しなくなる)。取得成功後に `gdelt_freshness()` を検査し、超過なら **hard** で raise
- ⚠️ **自己訂正**: 当初「GDELT は 5-6 日ラグがあるはず」と推測したが、ラグ分布を実測したら **0 日**で、推測は誤り。stale は内在ラグではなく**実際の異常**だった。**閾値を置く前にラグ分布を測る**ことで、誤った threshold (5-6 日) と誤った安心の両方を回避できた
- **pin 19 本** (`tests/test_mof_statements_daily_isolation.py`): 分類は**実観測の curl メッセージ**で固定 (作り物の文字列は「429 は soft」という覆域の錯覚だけを残すので使わない — 既存 pin の `"http 429"` を 09-17 run 35287482585 の実ログへ差し替え)。NG 入力 = `unexpected GDELT response` → hard / `OSError` → hard / hard ソースの 429 → hard / 404·403·未知形状 → hard。鮮度側は **凍結系列 (本番の現状) → NG** と **内在ラグ 1 日 → 誤発火しない**の両側を pin

### KB 整合 (PR #263 / #264 Codex P2) — 撤回済みの主張が見出し・表・ロードマップ行に残っていた

**2026-09-18 に 3 例出た「訂正を本文に書いても canonical な読み口が旧主張を返す」族の、4-6 例目。** 撤回は旧文の横に置くのではなく**旧文を置き換える** ([[lesson-unscoped-global-replace-2026-09-18]])。

- **roadmap T6 行 (PR #263)**: P-S1(a) は 2026-09-17 に user 決裁 Option C = retire で確定しているのに、canonical roadmap の T6 行は「執行停止 / 残る選択 = user 決裁」+ 失効した期日 2026-09-30 のままだった ⇒ ロードマップから計画する読み手は**解決済みの退役を進行中の作業として扱う**。行を退役クローズへ書き換え [[ps1a-option-c-retire-2026-09-17]] をリンク。併せて「multi-bar cooldown の order 層実装」(唯一の要求元が T6) を不要化として明示
- **carry カード §(1) 見出し (PR #264)**: 見出しが「storm は初 fill から**毎回**起きている」のまま、訂正 (実証は 11 fill 中 5) は直下の注記にあった ⇒ **見出しだけを読む読み手には撤回済みの主張が残る**。見出しを「確認済みだけで 11 fill 中 5 fill (45%)」へ差し替え。本文の「実発生率は fill あたりほぼ 1」も訂正 (上表が実証しない — 5 fill に storm 証拠なし、#893161 は本頁自身が storm 非該当と認定)
- **carry カード broker 行 (PR #264)**: 09-17 に注記で訂正済みだったが**表の行は `N=14` のまま**で、表だけを読むと broker サンプル 14 が存在するように見えた (N≥30 live 判定の入力になる数字)。行名に「broker N ではない」を入れ、**broker 実測 N=7 を独立行として併記**

### ① 側のレビュー 1 巡目 — 自分が 09-18 に書いた教訓をそのまま踏んだ (P1 ×2 / P2 ×1、全て正しかった)

- 🔴 **P1 2 件は同じ形: primary 側だけ fail-closed にして対称な benchmark 側を自分で確認しなかった。** (a) CLI が `bench_prepared["ok"]` を読まず空 benchmark を渡すと `net_edge=None` になり**明示的に要求された baseline 比較なしで promotion ゲートが通る** / (b) `stage_a_audit` が benchmark のラベルを検査しないため **未ラベル行が `bench_n` に入り `bench_wins` から落ちて net_edge が過大**になる。readout §2 の「統計関数側で fail-closed にしたのでどの呼び出し元からも再発できない」は benchmark 経路では**偽**だった
- **2026-09-18 に自分で定式化した「レビューが片側の穴を指摘したら対称な反対側を自分で確認する」(family A A-8) の翌日再発。** 教訓を書くことと次の設計でそれを検索することは別の作業。修正は両側を同じループで検査し `unlabeled_in` でどちらが汚染源かを返す形に。pin も両側に置いた
- **P2**: `load_rows` の初版が先頭 `[` のときだけ単一ドキュメントとして読んでいたため、旧 CLI が受けていた `{"events": [...]}` wrapper が 1 event 扱いで隔離される回帰。判定を「ドキュメント全体が 1 個の JSON として読めるか」+「dict なら `events` メンバを持つか」に変更し、**1 行だけの JSONL が壊れない**ことも pin (fall-through)
- pin 30 → **37 本**
- 🔴 **レビュー 2 巡目 (P2、これも正しかった) — 1 巡目の修正で「対称にする」を 1 段取り違えていた**: benchmark を**同じ `prepare()` に通した**ため、`hunt_event_logger` 固有の provenance 規約 (feed-symbol `^[A-Z]{6}=X$`) が「SR 近接 全 bar」という別母集団に課され、**repo 慣行の `instrument: "USD_JPY"` 表記のラベル完備 baseline が全行隔離されて exit 5** になっていた。対称にすべき軸 (D4 ラベル検査 / D3 独立観測の単位 / D5 cell 絞り — いずれも算数が母集団に依らず壊れる) と、**母集団固有の軸 (D2 provenance)** を区別していなかった。`enforce_provenance=False` を追加して benchmark はラベル・dedup・cell 絞りのみ通す形に。pin 37 → **41 本**。**教訓: 「対称に処置せよ」は「同じ関数に通せ」ではない** — どの規約がどの母集団に固有かを先に列挙する ([[lesson-symmetric-side-check-2026-09-19]])。同じ指摘の周りで **1 巡目は片側を忘れ、2 巡目は対称化を取り違える**という 2 種類の間違いを続けてやった
- 🔴 **レビュー 3 巡目 (P2、これも正しかった) — dedup が「意味を持ち始める日」に静かに壊れる設計だった**: `collapse_repeats` の identity に post-hoc の outcome 列 (`reversal` / `actual_outcome` / `actual_pnl_pips`) が 残っていたため、labeler が反復発火に異なるラベルを付けた瞬間に collapse が止まり、**N 膨張が復活するのは validity gate が通り始めるのと同じタイミング**だった。今日は全行未ラベルなので実害ゼロ = **だから気づけなかった** — 本 PR で診断した D4 (未ラベル) が D3 (dedup) の欠陥を隠しており、D1 が D4 を隠していたのと同じ入れ子構造が**自分の書いたコードの中に**もう一段あった。修正 = identity を **signal 時点のフィールドのみ**に。代表行はグループ内の非 None ラベルを引き継ぎ (観測を捨てない)、**同一 signal に 2 通りの outcome があれば衝突として gate で止める** (labeler のバグを片方採用で潰さない)。pin 41 → **48 本** (うち「ラベル付き重複 120 行 → distinct 40」は修正前に 120 を返す NG 入力)
- 🔴 **レビュー 4 巡目 (P2、これも正しかった) — `entry_time` の意味が母集団で違った (同じ根の 3 例目)**: 3 巡目の修正は hunt_events には正しかったが **benchmark には壊れた** — benchmark は 1 bar 1 行で `entry_time` が **bar の identity** なので、これを除外すると**相異なる bar が全部 1 群に潰れ**、偽の outcome 衝突で N が床を割り exit 5 になる。`DEDUP_MODES` ("signal" / "bar") を導入し 母集団ごとに粒度を選ぶ形に。pin 48 → **51 本**。
- 🔴 **レビュー 5 巡目 (P2 ×2、どちらも正しかった) — 3 巡目で足した衝突検出器が広すぎた**: (a) `(True, None, None)` と `(True, "WIN", 10.0)` をタプル一致で比較していたため**部分帰属を衝突扱い** (logger は 3 列を独立に初期化し、反復発火のうち実約定に対応するのは 1 本だけ = 正常状態) / (b) `collapse_repeats` は `select_cell` の**前**に走るので**別ペアの衝突 1 件で無関係な clean セルが DATA-BLOCKED** になる。修正 = `merge_outcomes()` でフィールドごとにマージ (同一フィールドの非 None 不一致のみ衝突) + gate は選択セルの衝突だけを数える (全セル分は `outcome_conflicts_all_cells` に分離)。pin 51 → **56 本**。
- 🔴🔴 **レビュー 6 巡目 (P2) — 私が公表した数字が誤りだった (本 PR 内で全波及を訂正済み)**: `signal` 粒度は唯一の時刻を identity から外すので `collapse_repeats` が**全ファイル横断**で潰し、**同一 identity の群が 2026-05-01〜2026-07-08 = 68.5 日**にまたがっていた。2 ヶ月離れた別 bar の同一 payload は**独立な 2 観測**であり、payload 一致は全期間の観測 identity ではない。⇒ `DEDUP_WINDOW_SEC` (既定 3600 秒、anchored) を導入し窓を跨ぐ同一 payload は別観測として残す。**初版の「9,946 / 7.0 倍」は窓無し = 最も攻撃的な端を点推定として公表したもので誤り**。訂正値 = 既定窓 1h で **20,642 / 3.37 倍**、感度表を readout §D3 に併記し点推定での引用を禁止。波及訂正: readout / changelog / session log / strategy card / logger docstring / registry / MEMORY。pin 56 → **62 本**。🔴 **教訓: 自分で書いた caveat を自分の結論で踏み潰していた** — §D3 に「重複群のスパンは単一 bar の再評価では説明できない」と書いた直後に「原因に依らず成立する」と続けて点推定を publish した。**caveat は書いた本人が最初の読み手であるべき**🔴 **パターン: 自分が足したガードはほぼ毎回「広すぎる」方向の新しい欠陥を作った** (3 巡目の検出器→5 巡目で 2 件 / 2 巡目の対称化→4 巡目で 1 件)。**fail-closed は安全側だが倒しすぎると「正常入力を止める」別の故障になる — NG 入力の pin と対になる PASS 入力の pin が必須**⚠️ **2 巡目で「provenance だけが母集団固有」と表を書いたが、`entry_time` の意味論も母集団固有だった** = 表そのものが不完全だった。**「対称にすべき軸」の列挙は仮説であって検証ではない** — 列挙が網羅的である保証をどこからも得ていなかった。**教訓: ガードが「今は効いている」ことと「効き続ける」ことは別 — 今日たまたま無害にしている前提が 解消された日に何が起こるかを、書いた時点で 1 回シミュレートする**
- 🔴 **レビュー 7 巡目 (P2、これも正しかった) — 6 巡目の訂正が「ツール自身のコメント」を洗い漏らしていた**: 6 巡目で readout / changelog / registry / strategy card / MEMORY は訂正値に揃えたのに、**`tools/hunt_event_dataset.py` の感度表だけ旧値 (15m 24,356 / 1h 18,812 / 4h 13,208 / 24h 11,213) が残っていた**。独立に再計算して確認 (provenance フィルタ後 **69,576 行** = collected 69,577 − 合成行 1): 正は **15m 27,335 (2.55x) / 1h 20,642 (3.37x) / 4h 14,953 (4.65x) / 24h 11,614 (5.99x) / 無制限 9,946 (7.00x)** = readout と registry の値に一致。🔵 **旧値の正体 = 窓を chaining する旧実装の出力** — 5 巡目で anchored に変えたときに再計算しなかった。chaining は窓内に次の行が来る限り窓を延長するので**より多く潰す** ⇒ distinct が小さく出る。**無制限 (9,946) だけ一致していたのは、その列が窓に依存しない唯一の列だったから** = 部分一致が「表全体が生きている」ように見せていた。🔴 **これは本 changelog が PR #230 の欄に自分で書いた教訓の再発** — 「主張を撤回したら、その主張を運んでいる全ての readout 面 (**docstring / markdown / MEMORY**) を同じコミットで洗う」。**ツールのコメントは readout 面である**。🔑 pin は**相互整合**で置いた (62 → **63 本**): ツールの 1h 値と readout の `膨張係数 = <基数> / <1h distinct>` が一致し、基数も一致し、倍率が**その 2 数の算術**であることを assert。両側が静的テキストなのでデータが増えても壊れず、**旧値を戻すと落ちる**ことを counterfactual で確認済み。⚠️ 数値は **estimator が変わった瞬間に陳腐化する** ので、表に **as-of 日付と基数と estimator 名**を併記した
- 🔴🔴 **レビュー 8 巡目 (P1 + P2、どちらも正しかった) — 公表数字がまた動いた。今度は推定量が到着順に依存していた**: (a) **anchored 窓は行の到着順に依存する** — `(ts - anchor)` を見るので**古い timestamp の行が後から来ると差が負になり、どれだけ離れていても現在の窓に入る** (24h 離れた 2 観測が Jan2 → Jan1 の順なら 1 件に潰れる)。`load_rows()` は入力順を保つため実データで発現しており、**9,946 identity のうち 205 件が逆順ペアを含む** (計 429 箇所) = 理論上の懸念ではなく**現に N を過小計数していた**。⇒ `collapse_repeats()` を **identity ごとに時刻昇順へ並べてから窓を張る** (stable sort なので同時刻行の代表選択は不変)。**訂正値**: 15m **27,565 (2.52x)** / 1h **20,692 (3.36x)** / 4h 14,953 (4.65x) / 24h 11,614 (5.99x) / 無制限 9,946 (7.00x)。4h 以降が不変なのは逆順ペアの間隔が 4h 未満だったため。🔵 **必要 WR 51.025% は不変** — あれは訂正後 N=20,692 での値で、N=20,642 だと 51.027% だった (**偶然、旧 N で publish した数字が新 N で正しい**)。波及訂正: tool コメント表 / readout (§D3 表 + 膨張係数 + corrigendum) / registry `current_state` / strategy card / session log。⚠️ readout 内の `[sr_audit] dataset: ...` ブロックは **as-run の記録なので書き換えていない** (旧推定量の出力である旨を明記)
- 🔴 **レビュー 9 巡目 (P1 + P2×2、全て正しかった) — 3 件とも「8 巡目の修正が届いていなかった隣」**: (c) 🔴 **P1: 鮮度は被覆を保証しない** — `gdelt_freshness()` は**末尾日しか見ない**ので、構文が正当で**末尾だけ新しい部分系列**は 8 巡目で入れた検証を通り、そのまま**完全な履歴ファイルを置き換える**。⇒ `gdelt_coverage()` を新設し昇格前に **行数と開始日**を保存系列と比較、縮んだら raise (全範囲を毎回取り直す設計なので被覆は縮まないはず = 縮みは応答の異常の証拠)。**「鮮度 OK」と「被覆 OK」は別の検査**だった (d) **後続 slug の fetch 失敗で候補が staged tree に残る** — 候補を `GDELT_DIR` 内に書き cleanup をループ**後**に置いていたため、slug 1 成功 / slug 2 で raise すると候補が残り、workflow は失敗時も `git add data/external/mof_statements/` するので**候補が corpus としてコミットされる**。⇒ 候補を **system temp dir** (`tempfile.mkdtemp()`) へ移し `finally` で rmtree。**`finally` だけでは不十分で「`git add` の見えない場所に置く」のが本質** (昇格は同一 FS の `.promoting` 経由 `os.replace` で atomic、これも finally で掃除) (e) **tz-aware と naive の混在で sort が TypeError** — 8 巡目で入れた時刻昇順ソートは `_parse_entry_time()` の戻り値を比較するので、`+00:00` 付きと naive が 1 件混ざるだけで **監査全体が異常終了**する (identity が同じである必要さえない)。⇒ **正規化を `_parse_entry_time()` 自身に置いた** — sort と窓の減算 `(ts - anchor)` の**両方**が同じ値を使うので、呼び出し側ごとに直すと片方が漏れる。naive は logger が書く UTC として扱い、aware は UTC へ変換して naive 化。🔵 **公表値は不変** (現コーパスは全 naive)
- 🔴 **レビュー 10 巡目 (P1 + P2、どちらも正しかった) — 被覆は「集計量」では守れない / 同じ数字が 4 巡連続で動いた**: (f) 🔴 **P1: 行数と開始日の一致は被覆を保証しない** — 9 巡目で入れた被覆ゲートは **行数 ≥ かつ 開始日 ≤** しか見ていないので、候補が**歴史の途中の日付を落としつつ同数の新しい日付を末尾に足す**と `candidate_rows == stored_rows` ∧ `candidate_first == stored_first` が成立して通り、**内部に穴のある系列で完全な履歴を置き換える**。⇒ `gdelt_coverage()` が**日付集合**を返すようにし、ゲートを **集合包含** (`stored_dates ⊆ candidate_dates`) へ。併せて**候補内の日付重複**も拒否 (重複は行数を嵩上げして非退行を偽装する)。**「集計量が悪化していない」は「情報が失われていない」ではない** (g) **D3 契約節の数字が 4 巡目分の訂正から取り残されていた** — 7 巡目で感度表を、8 巡目で readout/registry/card を直したのに、**観測単位そのものを定義している docstring 冒頭の契約節**が `57,656 / 82.9% / 5.8 倍` のままだった。独立に再計算すると**現行のどのモードにも一致しない** (既定 1h = 48,884 / 70.3% / 3.36 倍、窓なし = 59,630 / 85.7% / 7.00 倍) — あれは identity に post-hoc outcome 列が残っていた頃の推定量の出力。**この節を読んだ読み手は誤った有効 N を引用する**
- 🔴 **レビュー 11 巡目 (P2×2、どちらも正しかった) — 「観測を捨てない」を promotion ゲートに持ち込んでいた / 3 つ目の読み手面**: (h) 🔴 **`entry_time` が読めない行を独立観測として数えていた** — `collapse_repeats` は時刻の読めない行を**各行 1 観測として残す** (collapser の内部では正しい = 黙って観測を消さない)。しかし `prepare()` はそれを隔離しないので、**`entry_time: "bad"` のラベル付き重複 30 行が「独立な 30 イベント」として N の床を通り、偽の有意を製造できた**。⇒ 窓を使う場合は `prepare()` で **fail closed** (`quarantined_undatable`)。**同じ「独立性を検査できない」入力に対し、collapser では『残す』、ゲートでは『入れない』が正しい — 層ごとに安全な向きが逆**。🔵 **現コーパスには該当 0 行**なので公表値は動かない。⚠️ **この欠陥は本 PR のテスト fixture 内に生きていた** — `test_benchmark_prepare_passes_with_bar_dedup` が `2026-09-01T24:00:00`〜`T39:00:00` を生成しており、**16 行の不正時刻が 16 独立観測として通っていた** (fixture を翌日へ roll over して修正) (i) **logger docstring が 3 つ目の読み手面だった** — 7/8/10 巡で tool コメント表・readout・registry・card・D3 契約節を揃えたのに、`modules/hunt_event_logger.py` が `20,642` のまま「これを使え」と指示していた
- 🔴 **レビュー 12 巡目 (P2×2、どちらも正しかった) — 前巡で足したガードが 2 つとも「広すぎる」方向に倒れていた**: (j) **時刻不正のブロック理由をセルに絞る** — 11 巡目の fail-closed は `select_cell()` の**前**に全体を走査していたので、**別ペア/別 side の不正行 1 件で、それに影響され得ない 30 行の clean な USD_JPY/support 監査が reject** された。⇒ **除外は全体** (どこでも dedup できないので) **ブロック理由はセル内のみ** に分離 (`quarantined_undatable` と `quarantined_undatable_in_cell` を両方出す)。🔴 **これは 5 巡目 (b) の「collapse が select_cell の前に走るので別ペアの衝突 1 件で無関係な clean セルが DATA-BLOCKED」と完全に同型** — **同じ間違いを、その修正を参照しながら書いた新しいガードで再発させた** (k) **昇格を全 slug で all-or-nothing に** — `os.replace` はファイル単位では atomic だが**ファイル間では違う**。slug 1 を置換して slug 2 で失敗すると data ディレクトリが**世代混在**になり、workflow は `if: ${{ !cancelled() }}` で hard 失敗後も全部 stage するので**混在がコミットされる**。⇒ 各宛先を system temp に backup してから置換し、どれかが raise したら**全部ロールバック** (`.restoring` 中間物も外側の `finally` で掃除)
- 🔑 **「fail-closed は安全側」だけでは設計が決まらない** — 6 巡目にも書いた通り、倒しすぎると「正常入力を止める」別の故障になる。**今回はその教訓を書いた本人が、次の巡で足したガード 2 本で両方やった**。⇒ ガードを足すときの完了条件に「**この検査はどの母集団に対して真であるべきか**」を明記する (全体 / セル / ファイル単位) を加える
- pin 74 → **77 本**。2 件とも counterfactual 確認済 ((j) はセル絞りを外すと `0 row(s) in this cell ...` という**自己矛盾したブロック理由**で落ちる = 絞りが効いていない証拠、(k) はロールバックを外すと `yen_intervention.csv` が新世代のまま残る)
- 🔑 **pin を「読み手面の集合」に対して張り直した** — 相互整合 pin が見るのは **tool 契約節 + tool 感度表 + readout + logger docstring** の 4 面。**changelog / session log は訂正の歴史記録なので意図的に pin しない** (書き換えてはいけない側)。⇒ 「読み手に指示する面」と「起こったことの記録」を分けたので、次の推定量変更でも**指示面だけが機械的に守られる**
- pin 72 → **74 本**。2 件とも counterfactual 確認済 ((h) は fail-closed を外すと `ok is True` = 30 行が床を通る)
- 🔑 **再発を止めたのは文言修正ではなく pin の拡張** — 7 巡目の相互整合 pin は**感度表しか見ていなかった**ので、その 3 行上の契約節が独立にドリフトできた。pin を**契約節にも**広げ、`collapse == 基数 − distinct` / `% == collapse/基数` / `倍率 == 基数/distinct` を**算術として**assert。⇒ 次に推定量が変われば**どの面を直し忘れても CI が落ちる**。実際この pin は作業中に**自分の誤った backup 復元で契約節が巻き戻ったのを即座に検出した** (`the D3 contract's 1h distinct (11,920) disagrees with ... (20,692)`) = 恒真でない証拠
- pin 69 → **72 本**。3 件すべて counterfactual 確認済 ((f) は集計量のみのゲートに戻すと `DID NOT RAISE` ×2)
- 🔑 **「1 箇所直したら同型の兄弟を同じ PR で grep して掃く」の実演になった 3 例** — 8 巡目の 3 修正 (validate-before-replace / 到着順ソート) がそれぞれ**隣に 1 つずつ穴を残していた** (被覆未検査 / 候補の置き場所 / 時刻の正規化)。[[project_mof_ingest_defect_family_2026_09_17]] の教訓は「直した箇所の周囲」にも適用される
- pin 66 → **69 本**。3 件すべて counterfactual 確認済 — (d) は**当時の実装を忠実に再現** (候補を data dir へ + cleanup をループ後) して `found ['yen_intervention.csv', 'keep.csv']` で落ちることを確認
- 🔴 **同じ数字が 3 巡連続で動いた (6 巡目: 窓無し→1h / 7 巡目: chaining→anchored の洗い漏れ / 8 巡目: 到着順依存)。教訓は「数字を直す」ではなく「推定量を凍結してから数字を出す」** — 6・7・8 巡目はいずれも**推定量の定義がまだ動いている間に点推定を publish していた**ことの帰結。⇒ 今回は**相互整合の pin** (tool 表 ↔ readout の基数・1h 値・倍率の算術) を置いたので、次に推定量が変われば**片側だけ直すと CI が落ちる**
  (b) 🔴 **P1: GDELT が「検証前に保存系列を上書き」していた** — 宛先 CSV を `"w"` で開いた**後**に鮮度検査をしていたため、構文は正当だが stale/truncate された応答が**既に保存系列を壊しており**、その後の raise は元に戻さない。さらに `.github/workflows/mof-statements-daily.yml` の commit step は `if: ${{ !cancelled() }}` で data ディレクトリ全体を stage するので、**hard 失敗のまま退行がコミットされていた**。⇒ 候補を `.{slug}.tmp.csv` (系列ファイルに見えない名前) へ書き、**候補に対して**鮮度を判定し、通ったものだけ `os.replace` で atomic に昇格。落ちたら候補を削除し保存系列は無改変。**「全範囲を毎回取り直すので自己修復する」は上流アーカイブの性質であって writer の性質ではない** ([[project_mof_ingest_defect_family_2026_09_17]] と同型)
- pin 63 → **66 本**。3 件すべて counterfactual 確認済 — 特に (b) は**当時の実装を忠実に再現** (宛先へ直書き + cleanup なし) して「保存系列が上書きされた」で落ちることを確認した

**検証**: `tests/test_hunt_event_dataset.py` 37 passed / `tests/test_mof_statements_daily_isolation.py` 19 passed、`scripts/check.py` 全 10 チェック通過。破損 wikilink は **382 → 373** (相対形 `[[../dir/name]]` が本 checker で解決しないため bare stem へ統一、既存 2 件も同時に解消)。live / tier / lot / 価格データには触れていない

## 2026-09-19 — fix(hunt_events): 観測データセットの読み手が 5 層で壊れていた — 書き手だけが 144 日動いていた (rule:R3)

- **起点 = 未消化レビュー指摘の消化**。PR #267 (09-18) がマージゲートの findings 軸が導入以来**恒真**だったことを明かし、過去 10 PR に **未消化の connector P1/P2 指摘 19 件**が残っていた (MEMORY `project_review_gate_vacuous_2026_09_11`)。本 PR は PR #253 / #264 の hunt_events 系 4 件を消化したもので、**指摘より深い場所に 6 層の欠陥** (根因 D0 + 読み手 D1-D5) が見つかった。readout: [[hunt-events-dataset-readout-2026-09-19]]
- **D0 (根因)**: `modules/hunt_event_logger.py` docstring が「`reversal` は `tools/attribute_hunt_outcomes.py` が後で埋める (deferred)」と書いた labeler が、2026-04-28 から **144 日経っても存在しない**
- **D1**: documented consumer が documented dataset を**読めない** — `tools/sr_audit.py` は `json.loads(whole_file)` でデータセットは JSONL なので必ず 2 行目で `JSONDecodeError`。痕跡 = `raw/audits/sr_audit_*` の出力が **5 ヶ月で 1 件もゼロ**
- **D2**: 合成行 1 行が残存 (`2026-04-28.jsonl`)。**旧署名 (`adx` 整数 ∧ `atr_price == 0.001`) では捕まらない** (adx=18.5 / atr=0.12)。代わりに **feed-symbol 不変条件** (`^[A-Z]{6}=X$`) を使うと **69,577 行中ちょうど 1 行**が落ちる — 値ではなく**収集経路の構造**なので値域が増えても破れない。会計: 当該ファイルは `e0836eff3` 時点で 301 行、PR #264 は旧署名合致の 300 行を正しく除去し 1 行を取り逃していた
- **D3 (算数破綻)**: `entry_time` 以外が完全一致する重複評価が **48,934 / 69,576 (70.3%)**。相異なる観測は **20,642** のみで **N 膨張 3.37 倍** (既定 dedup 窓 1h)。🔴 **訂正 (2026-09-22、8/10 巡目)**: この行の **20,642 / 3.37 倍 / 48,934** は**到着順依存の過小計数**であり撤回。正 = **20,692 / 3.36 倍 / 48,884** (identity ごとに時刻昇順へ並べてから窓を張る修正後、基数 69,576)。**引用は訂正値で行うこと**。🔴 **膨張率は窓に強く依存する — 点推定で引用しない** (15m 27,335 / 2.55x・1h 20,642 / 3.37x・4h 14,953 / 4.65x・24h 11,614 / 5.99x・無制限 9,946 / 7.00x)。**本 changelog の初版は窓無しの 7.0 倍を点推定として公表しており、誤りだった** (下記 6 巡目)。`sr_audit.py:127` の `n = len(events)` は Wilson 下限と二項検定の分母に直入するため、Stage A strict (`wilson_lower_bf40 > 50%`) の通過必要 WR が **既定窓の N=20,642 で 51.025% → 膨張後 N=69,577 で 50.558%** に下がる = 真 WR 50.8% のノイズセルが promotion ゲートを通る。重複群の `entry_time` スパンは中央値 **125 分** (最大 21h) で、原因 (bar 凍結の可能性) は**本 readout では未特定** — 独立観測でないことは原因に依らず成立するので dedup は原因特定を待たない
- **D4 (最重量)**: `reversal` が **69,577 / 69,577 で None**。旧実装の分子 `sum(... if e.get("reversal"))` は None を分子から落としつつ**分母には数える**ので、未ラベル観測が自動的に敗北票になる。⚠️ **危険の向きは偽陽性でなく偽陰性** — 実データ全量なら **WR 0.00% / z = −263.8 / Wilson 上限 95% 0.0055% / p = 0**、つまり sr hunt 仮説を虚構の圧倒的証拠で**棄却**する経路だった。D1 (読めない) が偶然 D4 を隠していた
- **D5**: `--pair` / `--side` / `--window` が出力ラベルにしか効かず**母集団を絞っていなかった** — 全ペア pooled の結果に単一ペア名が付く。「名乗る estimand を測っているか」欠陥族の 1 例追加
- **対処**: `tools/hunt_event_dataset.py` (新規) に読み取り規約 D1-D5 を凍結 (`load_rows` / `split_provenance` / `collapse_repeats` / `select_cell` / `split_labels` / `prepare` + validity gate)。`tools/sr_audit.py` は読み取りを委譲し、**`stage_a_audit` 自体を fail-closed** に (未ラベル行を 1 行でも含む母集団は `verdict="data_blocked"` / `n=0`) — `prepare()` を飛ばした呼び出し元からも再発できない。**raw ファイルは書き換えない** (観測記録は as-collected で保存、除去は読み取り時。合成行 1 行は恒久 negative-control fixture として残す)
- **pin 30 本** (`tests/test_hunt_event_dataset.py`) — MEMORY の「**検知器には NG を返す既知の入力を同じコミットで pin せよ**」に従い 5 層それぞれの**落ちるべき入力**を固定。恒真 NG でないことの pin も併設 (全行ラベル付き → PASS)。実データセットへの pin 2 本は **labeler が実装された日に落ちて readout 更新を促す**。counterfactual: pre-fix `stage_a_audit` に未ラベル 100 行で `n=100` / `verdict` キー無しが返ることを実測、D4 pin 3 本が落ちる
- **未解決 (registry `hunt-events-labeler-disposition`、期日 2026-10-20)**: labeler を作って観測系として生かすか、退役させるかの二択。**決めずに期日を roll するのは禁止** (write-only を 4 段目まで放置した本件そのものの再発)。現状は validity gate が DATA-BLOCKED を返し続けるので**この経路から誤った verdict は出ない**
- ⚠️ **引用規律**: 本データセットを使った過去の N 主張は再確認が必要。[[sr-strategies-signal-track-2026-04-28]] Step 1 の「81 events = 81 actual signal emissions」は**合成行を数えていた可能性が高い** (git に残る同ファイルの全スナップショットが旧合成署名に全行合致) — 同文書の結論は Step 3 の score 分布から独立に導かれるため揺らがない。決定文書は不改変、corrigendum は readout §5
- **検証**: full suite **3,436 passed / 17 skipped / 1 xfailed**、実行後に `raw/hunt_events/` 無変化 (PR #266 の書込み抑止が効いていることを再確認)

## 2026-09-18 — research(family A): ❌ explore verdict = **FAIL** — 梯子は 2022 の 2 発だけを説明していた (rule:R1 手続き、純研究)

- **期日 09-28 の 10 日前倒しで verdict 確定**。J = P(armed｜介入日) − P(armed｜非介入日) = **0.2978** / permutation p (片側、circular shift 全 **1,107** 通り) = **0.1074** > α=0.05 ⇒ §10.4 固定分岐により **FAIL**。2×2 = **TPR 3/7 / FPR 144/1101** (armed 147 / 1,108 営業日)
- 🔴 **初版の「検出力不足ではない」を撤回 (Codex P2 / PR #270 第4波)** — positive control (ほぼ完全な検出器 J=0.87 が p=0.019) は「**ほぼ完全な効果なら検出できる**」を示すだけで、**現実的な効果量に対する検出力の証拠にならない**。post-hoc の**検出力曲線**を実測 (実 armed 系列 147/1,108 + 合成ラベル、陽性 7、600 反復): 効果量の軸 = armed に入る **episode block** 数 (実ラベルの block 構造 **[3,1,2,1]** を保存 — 一様散布は独立試行を仮定し検出力を過大評価する、Codex P2 第5波): **0/4・1/4 で 0.000 / 観測値 2/4 で 0.130 (87.0% 取り逃す) / 3/4 で 0.727 / 全 block hit 4/4 で 0.953**。hit/miss は生成位置の**全日を検査して強制** + **episode-gap 近傍を棄却し完成サンプルが 4 block であることを検証** (第7波) (先頭日のみの判定は miss 指定 block が armed に掛かる、Codex P2 第6波)。⇒ **観測された効果が実在しても 87.0% の確率で取り逃す設計**だった。⚠️ **ただし全 block hit 級 (感度 0.953) についても「効果が無い」とは言わない** — **非有意≠不在** (その効果が真でも 4.7% は非有意)。不在の主張には同等性検定/信頼区間が要り、本 pre-reg は未規定なので主張しない (Codex P2 第7波 — 推論誤りの訂正中に同型の推論誤りをしていた)。**本 FAIL が意味するのは「凍結 α 規則を満たさなかった」だけ** — 全 block hit 級に対しても **「不在」は言わない** (感度 0.953 は弱い反証にすぎず、その効果が真でも 4.7% は非有意。同等性検定/信頼区間は未規定) し、「分離が無い/検出器に情報が無い」は言えない。⚠️ **凍結時に power analysis を規定しなかったこと自体が設計の不足** — 「記述級」と宣言することと、どの効果量なら検出できるかを事前に数値化することは別物。曲線は post-hoc で **verdict 判定には未使用** (FAIL は凍結規則のまま)。次の pre-reg では凍結時に検出力曲線を計算する
- 🔵 **secondary (記述): pass-1 の話者交絡 caveat が悪い方向に的中** — 2022 (鈴木期) J=**0.2494** (2 event、**hit した event 1** / hit 日 2) vs 2026 (片山期) J=**0.0484** (5 event、**hit した event 1** / hit 日 1)。⚠️ **event 数と介入「日」数の混同を訂正** (Codex P2 / PR #270): 初版は「2022 = 2 event / 2 hit」と書いたが、2022-09-29 の **1 event が 10-21 と 10-24 の両方を覆う**ため hit 日が 2 になるだけで **hit した event は 1/2** (2022-05-19 は空振り)。**全 7 event のうち何かを当てたのは 2 本だけ**で、2022 の優位は初版に書いたより更に薄い。pass-1 で「2022 の 2 本だけで結論が反転しないか点検せよ」と書いた点検の答えは「**全体 J のほぼ全てを 2022 の 1 event が担っている**」。検出器は「介入前の梯子」ではなく、せいぜい **2022 の 1 回のエスカレーションの記述**。リードは 15 営業日 (2022-09-29→10-21) / 3 営業日 (2026-04-24→04-30) で、**7 event 中 5 が false alarm** = まさに family A が測ろうとした較正結果そのもの
- 🔴 **凍結仕様の欠陥 ② — null が 4 block を厳密には保たない (第8波)**: 凍結 null は「ラベル系列の一様 circular shift」で実装はそのとおりだが、**営業日 index 上の一様シフトは暦日ベースの episode 規約 (gap≥30d) を保たない** — span 20 営業日の block が祝日の多い区間に落ちると 2 episode に割れる。実測 (signal 非参照の構造診断、Jもpも計算せず): **1,107 シフト中 225 本 (20.3%) が 5 block**、p=0.1074 はその混合の上の値。**§10.5 により直さない** — null を変えれば p が変わる = 凍結 primary の作り替えであり、カレンダー欠陥を直さなかったのと同じ理由で拒否する。バイアスの向きは再計算なしには判定不能で、再計算は 2 度目の look。⚠️ **凍結欠陥 2 件はどちらも「凍結文の意図」と「凍結文が指定する操作」のズレ** — 凍結前に操作を実データ上で 1 回走らせて性質を確認していれば両方見つかった
- 🔴 **凍結仕様の欠陥を測定時に発見 (自己申告)** — 介入日 10 のうち **3 日 (2024-04-29 昭和の日 / 2026-05-04 みどりの日 / 2026-05-06 振替休日) が凍結営業日カレンダーから落ち、陽性が 7 になっていた**。A-8 で非営業日の**会見 (signal)** は翌営業日へ roll forward すると決めたのに、非営業日の**介入 (label)** は営業日インデックスに無いため黙って捨てる — **非対称な実装**だった。FX 市場は日本の祝日でも開いており MoF は実際に祝日に介入している
- ⚠️ **事後修正はしない** — §10.5 がカレンダーの凍結後変更を禁止しており、補正して再計算することは **explore の 2 度目の look = 窓を焼く行為**。**verdict は FAIL のまま確定させ、バイアスの向きは「判定不能」と明記**した (「補正すれば通ったはず」も「補正しても通らない」も、言うには禁止された再計算が要る)。再挑戦は label 側のカレンダー規則も明示した**新規 pre-reg のみ**
- **§5 FAIL 分岐の執行**: ladder 検出器は介入確率に情報なしと記録 / **family B は発言層なしで設計** (or 独立裁定) / **lexicon 基盤の収集は継続** (`mof-statements-daily` cron 維持、アーカイブ価値は判定と独立)。explore 枠は凍結時に消費済みで追加消費なし
- ⚠️ **引用規律**: 否定されたのは「**凍結 ladder 検出器 (L≥4 遷移 / T,R,H=5,20,20 / retrospective L5 降格 / 凍結営業日カレンダー) が 2022-01-07〜2026-07-29 で MoF 公式円買い介入日と day-level で分離する**」という一点のみ。**「口先介入に情報がない」ではない** (有効 N=4 blocks / 陽性 7 日の記述級)。引用時は**カレンダー欠陥を必ず併記** ([[feedback_audit_past_verdicts_2026_08_05]])
- **forward 期 (2026-07-30〜) は未接触のまま凍結維持** — 将来の新 pre-reg が同じ窓を genuine OOS として使える状態を保つため、P-10 型 ban は解除しない
- 🔴 **Codex P2 第 2 波 ×3 対応 — うち 2 件は公表した数値が誤りだった (primary J/p は不変)**:
  - **(1) 話者層別が層別になっていなかった** — per-year の J は armed だけを年で絞り**ラベルは全年のまま**だったため、分母が全 7 陽性の「**寄与**分解」であって within-year の層別 J ではなかった。**「片山期 J はほぼゼロ (0.0484)」は誤り** — 層別で測ると **2026 = 0.2464**。`contribution_j_labels_all_years` と `stratified_j_within_year` を別フィールドに分離。🔵 **訂正して初めて見えた最強の所見 = 2024**: 介入 4 日 (営業日系列上 3 日) があるのに **event ゼロ / 層別 J = 0.0** — L4「断固」が 2023–2025 に皆無で **検出器がまる 1 年沈黙**していた。これが「話者/時代に縛られた検出器」の最も直接的な証拠であり全体 FAIL の主因。層別 J は 2022 **0.4972** > 2026 **0.2464** で話者勾配は実在するが初版が書いたほど極端ではない (かつ 2026 は営業日系列上の陽性 1 日のみで点推定はほぼ無意味)
  - **(2) positive control の p=0.0027 が誤り** — あの値は**合成の等間隔 armed マスク**上のもので、**凍結検出器の実 armed 系列**ではなかった。circular-shift の有意性は armed 窓の位置と間隔に依存する。実系列で取り直すと **各 event 窓に陽性 1 つ (k=7) で p=0.0190** / armed 全日陽性で p=0.0009。**結論 (検出力はあった) は不変**だが数値を訂正し、回帰 pin を**凍結 events から armed を再構成する**形に作り直した
  - **(3) registry / 台帳の resolution に旧解釈が残存** — 他ファイルを訂正しても canonical な registry と台帳が「2022 = 2 event / 2 hit」「片山期ほぼゼロ」を保持しており、読み手は訂正前の解釈を受け取る状態だった。両方を訂正
- 🟠 **Codex P2 ×3 対応 (いずれも記述の正確さ、primary 統計 J/p は不変)**: (a) 上記 event/日 の混同を `events_with_hit` / `hit_days` に分離 + 回帰 2 本 pin / (b) 台帳 #27 の **verdict 列が「未測定」のままだった** → FAIL を verdict 列へ移動 (状態列だけ直しても canonical ledger の読み手には未測定に見える) / (c) **session log §6「触っていないもの」が「介入ラベルとのジョイント計算」を残したまま**で、look 消費後に**偽**になっていた → 「触った」節を新設。**peek 会計の記述は look を消費した時点で同じコミット内で更新する** (放置すると「窓は焼いていない」という最重要の主張が嘘のまま残る)
- 🔴 **Codex P2 第12波 — レビュー対応そのものが無関係な記録を改竄していた (自己申告、rule:R3)**: 第11波で検出力曲線の数値を更新する際、**スコープを絞らない全文置換**を KB 4 ファイル全体に当てた結果、`0.132`→`0.130` が **Gate A の実測 `0.1327`** (147/1,108 bd) に、`4.2%`→`4.7%` が **2026-08-07 の SL_HIT 実測 `54.2%`** (WIN 1792/3308) に部分文字列として食い込み、**pre-reg §10.3 の凍結表 / 台帳 #27 / changelog の計 5 箇所を改竄**していた。置換は成功し CI も pre-commit も通るため静かに壊れ、**捕捉したのは connector レビュー**。真値を分子・分母から再計算して復旧し、コミット全体を `--word-diff` でトークン全数照合 (意図外は 5 箇所のみ、他 8 組は波及なし)。再発防止は**算術の pin** `tests/test_kb_numeric_consistency.py` — 「割合の主張はその場の分子・分母と一致する」「件数なしの引用は件数付きの正本と一致する」を性質として検査 (語句 grep 型 pin は本 PR で 2 度誤爆しているため採らない)。破損コミット `3bec6df3` に対し 3 本とも落ちることを counterfactual 確認。さらに同波で **台帳 #27 に撤回済の旧 verdict ブロックが並存していたのを除去** — 第2波の訂正が「旧文を残して新文を追記」になっており、canonical 台帳の読み手は **最初に「検出力不足ではない」「p=0.0027」「2022 = 2/2 hit」という撤回済の記述を受け取る**状態だった。撤回は**旧文の横に置くのではなく旧文を置き換える** (撤回マーカーを含む新文に一本化)。🔴 **第14波 — 凍結ラベルが基数でしか pin されていなかった + 検出力の向きを断定していた**: (a) `family_a_pass2.py` のラベルガードは「10 日 / 4 block」しか見ておらず、**同じ block 内で介入日が 1 日入れ替わっても ABORT しない** — 陰性マスクも J も p も secondary も変わるのに通る。「一度限りの凍結測定」を名乗る以上母集団は**実体**で pin すべきで、順序つき介入日リストの指紋 `EXPECTED_IV_SHA16` を追加 (block を保ったまま 1 日ずらす counterfactual で ABORT を確認)。指紋関数は本体と pin で**同じものを共有** (テスト側で再実装すると両方同じく壊れる)。(b) verdict の検出力節で **「カレンダー欠陥が検出力をさらに削っている」と断定していたのを撤回** — §3 で「バイアスの向きは判定不能」と書きながら同じ欠陥の**検出力への向きだけを断定**していた矛盾。落ちた 3 日を戻せば armed 包含と block 構造次第で**強まりもすれば薄まりもする** ⇒ 向きも「不明」。🟠 **第13波 — 同型の 3 例目: pre-reg の status バナーが「凍結済・未測定」のまま**だった (§11 に verdict を書いた後も)。**§11 まで読まない読み手/ツールは canonical pre-reg を未測定と分類し続ける**。H1 と Status を ❌ FAIL へ更新 (凍結時の記述は details で不改変保存)。本 PR だけで **台帳 verdict 列 / 台帳の旧 verdict 並存 / status バナー** の 3 例が出たので、構造 pin `tests/test_kb_status_banner_consistency.py` を新設 — 「**verdict 見出しを持つ decision doc の status バナーは未測定を名乗らない**」(過去の記述を畳む `<details>` は検査外 = 不改変保存規約と両立)。decisions 168 doc で誤爆 0 / 修正前の doc に対して落ちることを counterfactual 確認。教訓 = [[lesson-unscoped-global-replace-2026-09-18]]。**primary (J=0.2978 / p=0.1074) と verdict (FAIL) は不変**
- 成果物: `tools/family_a_pass2.py` (凍結測定ハーネス) / 回帰 pin `tests/test_family_a_pass2.py` (13 本) / verdict [[family-a-pass2-verdict-2026-09-18]] / 生値 JSON / pre-reg §11 / registry `family-a-explore-verdict-deadline` resolved / 台帳 #27

## 2026-09-18 — research(family A): pass-1 執行 — Gate A / Gate B ともに PASS、**pass-2 解錠** (rule:R1 手続き、label 非接触)

- ✅ **凍結検出器でイベント列挙 + gate 判定を実行** (`tools/family_a_pass1.py`)。**label 非接触** — 参照したのは `lexicon_scores.csv` のみで `interventions_daily.csv` は開いていない (`tests/test_family_a_pass1.py` で構造 pin)。pass-1 の存在理由は「explore outcome に触れずに park 判定できること」(pre-reg §10.3)
- **Gate A (特異度) PASS**: armed 営業日率 **0.1327** (147 / 1,108 bd) ≤ 0.25。凍結時に論拠として書いた設計期待 (event 5–8 本 × 21bd / 約 1,120bd = **9–15%**) の中に着地 — **データを見ずに置いた閾値が実測と整合**しており、事後的に緩めた閾値ではない
- **Gate B (供給) PASS**: event **7** 本 ≥ 5、相異なる暦年 **2** (2022, 2026) ≥ 2 → **pass-2 解錠**
- event = `2022-05-19 / 2022-09-29 / 2026-01-16 / 2026-03-17 / 2026-04-24 / 2026-05-29 / 2026-06-30`
- 窓内サマリ (explore 2022-01-07〜2026-07-29、営業日 1,108 / 会見 464): 実効水準 L0:287 / L1:22 / L2:37 / L3:101 / **L4:17 / L5:0**。**L5 が 0 件**なのは A-1 remap が効いているため (corpus の L5 は全て retrospective で talk 水準へ降格、`レートチェック` は窓内に 1 件も出現せず)。非営業日会見 13 件は A-8 の roll-forward で readout に明示
- ⚠️ **凍結条件を満たした上での正直な power 所見 (verdict で必ず併記)**: **Gate B は下限ぎりぎり** — 暦年ちょうど 2、内訳 **2022:2 / 2026:5** で供給の 5/7 が片山期に集中する (L4「断固」年次 2022:3 / 2023-25:0 / 2026:13)。Gate B の「暦年 ≥ 2」はまさにこの交絡分離のために置いた条件であり**通ったのだから解錠する**が、「話者非依存の検出器である」ことを示したわけではない。verdict では **speaker-stratified な記述 (secondary)** を併記し **2022 の 2 本だけで結論が反転しないか**を点検する。**閾値の事後強化は §10.5 で禁止** — ゴールポストの移動であり caveat として書くのであって gate は変えない
- **次 = pass-2 (測定)**: day-level Youden **J = P(armed｜介入日) − P(armed｜非介入日)** + episode-block circular-shift **B=10,000**、α=0.05 片側、verdict 分岐 §10.4。期日 registry `family-a-explore-verdict-deadline` (**2026-09-28**)。**本 readout の main 着地後に 1 回だけ走らせる** (イベント集合を先に凍結してから outcome に触れる = event set チューニング防止)
- 主張上限は不変 — 有効 N = 4 episode blocks につき **PASS しても記述級**、edge 主張・live 変更ゼロ
- 🟠 **Codex P2 対応**: docstring に書いた `python3 tools/family_a_pass1.py` が **実際には ModuleNotFoundError で動かなかった** (直接実行だと `sys.path[0]` が `tools/` になり `from tools import ...` が解決できない)。`__main__` ガード内でのみリポジトリルートを `sys.path` に足して修復 — **ライブラリ import 時の副作用はゼロ** (CLAUDE.md「tools/*.py はスクリプトでありライブラリでもある」規律)。回帰 2 本 (**2 形態を実際に subprocess 起動して rc=0 と出力を確認** / sys.path 操作が `__main__` ガード外に出ていないことの構造 pin、5 → 7)
- doc: [[family-a-pass1-gates-2026-09-18]] / 凍結 [[family-a-statement-ladder-prereg-2026-08-19]] §10.3
## 2026-09-18 — fix(process): マージゲートの findings 軸が導入以来ずっと恒真だった — 第 3 の空振り形状 (rule:R3)

- 🔴 **`tools/pr_review_gate.py` は P1/P2 を 1 件も観測していなかった** — connector は指摘を **inline review comment (review thread)** で投げるが、旧実装は `gh pr view --json reviews,comments` しか読まない。`reviews` に入るのは review の**本文**であって thread 本文ではないため、**findings は構造的に空**。「P1/P2 指摘なし — マージ可」は**恒真命題**だった
- **実測 (10 PR)**: #264:6 / #257:7 / #253:6 / #256:3 / #249:2 / #263,#261,#258,#250,#265 各 1 = **inline に 29 件、top-level review 本文に 0 件**。2026-09-11 の 2 度の修理は**到着軸だけ**を直しており、findings 軸には触れていなかった
- **差分検証 (同一 PR、旧 vs 新)**: #264/#257/#253 は「マージ可」→「未消化 4/7/6 件」。一方 **#265 は「1 件は対応 commit で消化済み — マージ可」** = 消化の検出も効いており、何でもブロックする実装にはなっていない
- 🟣 **修理**: `fetch_review_threads()` 新設 (GraphQL `reviewThreads`、`isResolved`/`isOutdated` は消化の positive evidence として除外) / **取得失敗は exit 4 の fail-closed** (「取れなかった」を「指摘なし」に折り畳まない) / inline finding の存在を到着判定にも算入 / 成功メッセージを「**review 本文 + inline thread N 件を検査**」に変更 — 恒真メッセージは探索範囲を名乗らないから恒真だと気付けない
- 🔵 **プロセス所見**: 同等実装は **PR #227 に存在し 18 巡のレビュー後 CLOSED (未マージ)**。main に着地したのは #231 由来の簡易版で、既存テスト冒頭に「#227 版テスト (GraphQL reviewThreads …) は盲目移植していない」と明記されていた。**正しい設計は書かれ、レビューされ、捨てられていた**
- 🔵 **修理版が自分自身の PR で同型 4 例目を拾った (Codex P2 / PR #267)** — 「修理 PR 自身をそのゲートに通せ」を実行したら **exit 3**。`reviewThreads(first:100)` がページングしておらず、**thread 100 超の PR では先頭ページだけを静かに返す** = 2 ページ目以降の未解決 P1/P2 を「なし」と誤報しうる。**修理そのものの中に同じ欠陥族が埋まっていた**。`pageInfo`/`after` で全ページ走査 + `hasNextPage` なのに cursor が無い場合とページ上限到達は **None で fail-closed** (切り詰めリストを「全部見た」と名乗らせない)。⚠️ #227 版にはページングがあった = 捨てられた設計から性質を 1 つ取りこぼしていた
- 🟠 **5 例目の指摘 (Codex P1) — 推奨は採用、severity の主張は実測で反証**: 「1 ページ目に空文字 cursor を渡しており GitHub が拒否 → 全 PR で exit 4」。**PR #264 に対し 3 形態を直接実行して反証** (`-F after=` 空文字 / 引数なし / `after=null` のいずれも rc=0・nodes=6)。実際 §3 の差分判定はこの指摘以前から正しく出ていた (壊れていたら差分は出ない)。**それでも修正は入れた** — 空文字が通るのは文書化されていない挙動で依存する理由がなく、1 ページ目は `after` を付けない (`$after` は nullable) のが正しくコストゼロ。⚠️ **「P1 と書いてあるから現に壊れている」と記録すると、後続が「ゲートは一度全 PR で exit 4 だった」という存在しない履歴を引用することになる** — レビューは検証してから採る
- 回帰 pin `tests/test_pr_review_gate_inline.py` 18 本 (open thread = finding / resolved・outdated は非ブロッキング / 非 connector 無視 / severity 無し無視 / **top-level clean + inline finding で exit 3 = 旧恒真形状の再現** / 対応 commit で消化 / inline 単独でも到着 / **取得失敗 exit 4** / 成功メッセージが探索範囲を名乗る / **fetcher が実際に呼ばれる配線 pin** / 全ページ取得 / **2 ページ目だけに finding がある失敗シナリオ** / cursor 欠落・ページ上限・repo 解決失敗の fail-closed 3 本)。既存 24 本は autouse stub で維持
- 教訓: **検知器を作ったら「それが NG を返す実例」を同じコミットで pin する。「異常なし」メッセージには探索範囲を書く — 書けないなら探索していない**
- doc: [[pr-review-gate-inline-blindness-2026-09-18]]

## 2026-09-18 — fix(hunt_events): pytest 汚染を logger 側で遮断 — 判別署名は 1/3 しか捕まえていなかった (rule:R3)

- 🔴 **判別署名の過小検出を実測** — PR #264 は既存の合成 15,649 行を除去したが **logger は未修正**で、以後も pytest のたび再混入していた。運用上の緩和策として記録していた判別署名「adx が整数 ∧ atr_price==0.001」を 2026-09-18 の実 run で検証すると、生成 36 行のうち**合致は 12 行のみ (33%)**。残り 24 行は実バーを再生する fixture 由来で **adx/atr が実測値らしい float** を持つ。⇒ **事後の署名フィルタは防御になりえない。書込みそのものを止める必要がある**
- 🟣 **修正** `modules/hunt_event_logger.py`: `HUNT_EVENT_LOG_MODE` (`auto` 既定 / `on` / `off`) を追加し、`auto` では pytest 実行中 (`PYTEST_CURRENT_TEST` ∨ `sys.modules` に pytest) の書込みを抑止。logger 自身のテスト用に `HUNT_EVENT_LOG_DIR` で出力先を差し替え可能に (`mode=on` + tmp_path)。戻り値の契約を「書いた=True / 抑止 or 失敗=False」に明文化。**戦略評価パスは従来どおり never-raise**
- **実測検証**: full suite (3,332 tests) 実行後に `knowledge-base/raw/hunt_events/` が**無変化** (新規ファイルゼロ、git status clean)
- 回帰 pin `tests/test_hunt_event_logger_suppression.py` 11 本 — 既定抑止 / 実 log dir 無変化 / mode 環境変数 5 ケース / `mode=on` の実書込み内容 / dir override / 失敗時 never-raise / **戦略 2 ファイルが logger を迂回して直接書いていないことの構造 pin**
- ⚠️ 本 PR は観測データの**将来の汚染**を止めるもので、既存行の再掃除はしていない (PR #264 で実施済み)。ただし上記のとおり署名フィルタは取りこぼすため、**2026-09-18 より前の hunt_events を使う sr 系分析は N の再確認が必要**
## 2026-09-18 — research(family A): 🔒 explore pre-reg 凍結 — ladder の L5 は「梯子の段」ではなく事後ナレーションだった (rule:R1 手続き、純研究)

- 🔒 **family A statement_ladder (台帳 #27) 凍結コミット執行** — 期日 09-24 の **6 日前倒し**。registry `family-a-adversarial-freeze-deadline` resolve → `family-a-explore-verdict-deadline` (2026-09-28) へ置換。**explore 枠 1 消費**。本ラインは scan 第5次 §2.3 会計で**プロジェクト唯一の「着手可能」な供給ライン**
- 🔴 **blocking A-1: primary 検出器 (L≥4 遷移) に事後ナレーションが混入していた** — pin 版 lexicon v1 の level 5 は `レートチェック` (先行) と `介入を実施/行い/行った/いたし/行う`・`平衡操作を実施` (事後・一般論) を同一段に置く。corpus 全期間 512 会見の実査で **L5 判定 9 件すべてが過去形または規範的一般論**、`レートチェック` 由来は **0 件**。実例 = 2023-09-13「昨年９月に…介入を行い、続く10月にも…行った」(11 ヶ月後の回顧) / 2024-10-01「為替介入を行うというのはある意味まれでなければならない」(特定の介入を指さない一般論) / 2026-09-08「日米協調介入を実施したときから」(既往言及)
- **なぜ blocking か** — family A の estimand は**先行検出器の hit/FA 較正**。事後ナレーションを段に数えると (i) 介入直後の会見が必ず L5 に上がる = **「起きたことを読んで当てる」look-ahead が検出器定義の内部に入り** hit を機械的に押し上げ FA を押し下げる、(ii) 回顧・一般論で無関係に発火し FP 側を不規則に汚す。scan 第5次 §1.2 の「negative 欠損は precision を機械的に押し上げる」と同型の欠陥が、データ側ではなく**検出器定義側**にあった
- 🟣 **修正 = 検出器側の水準写像を凍結** (`tools/family_a_ladder_detector.py` 新設、label-free / price-free): leading 語 (`レートチェック`) を含まない L5 会見は、その会見が matched した L1–L4 の最大値へ降格。**pin 済 scorer `tools/mof_statements_lexicon.py` @ `569dbe3f` は不改変** = 比較可能性の凍結 (§0-4) を維持
- 🟠 **A-2: rearm を event-to-event 化** — DRAFT の「直近 R 営業日に L≥4 が無いこと」を**水準系列**で読むと carry T=5 の分だけ実効不応期が **R+T=25bd (≈35 暦日)** へ膨張し、§3 の episode 個別化規約 (gap ≥ 30 暦日 ≈ 21bd) で**隣り合う 2 エピソードの 2 発目を構造的に取り逃す**。event 単位で測ると最小間隔 R+1=21bd となり、episode 規約と整合しつつ H=20 の hit 窓が重ならない (trial が清く分割)
- ✅ **A-3: (T, R, H) = (5, 20, 20) は論拠で据置** — T=5 は会見 cadence 実測 2.1 回/週 に対する「次の会見+余裕1回」の最小値 / R=20 は episode gap 規約との可換性 / **H=R は必須** (H>R で hit 窓が従属化、H<R で死角)。候補空間の残りセルは**恒久放棄**。データ較正はしていない
- ✅ **A-4: 統計量を 1 本に確定** — day-level Peirce/Youden **J = P(armed|介入日) − P(armed|非介入日)**。「リード付き overlap 計数」は event 供給量にスケールし「良い検出器」と「よく鳴る検出器」を分離できないため棄却。null = episode-block circular-shift B=10,000、α=0.05 片側、m=1
- ✅ **A-5/A-6: pass-1 gate を label-free で数値凍結** (E23 two-pass 様式踏襲) — **Gate A (特異度)** armed 営業日率 ≤ 0.25 / **Gate B (供給)** event ≥ 5 **かつ相異なる暦年 ≥ 2**。暦年条件は話者交代の交絡分離: L4 `断固` の年次分布は **2022:3 / 2023:0 / 2024:0 / 2025:0 / 2026:13** で、単一年集中の event 群は「介入前の梯子」でなく「片山期の語法」を測っている可能性を分離できない。**pass-1 は label 非接触 = 不通過なら explore の look を一切消費せず park**
- ✅ **A-7: corpus 連続性 PASS** (scan 第5次 §1.2 の凍結前チェック要求) — `conferences/*.jsonl` 57 月ファイルで **202201→202609 欠落月ゼロ**、レコード 512 / parse 失敗 0、`lexicon_scores.csv` **512 行 = 1:1**、右端 **2026-09-15 = 復旧された negative sample** (`my20260915.html`、max_level 0)。FP 率較正の分母は連続
- ⚠️ **peek 会計 追補** — P-A6: 本検証で観測したのは **signal 側のみ** (水準分布・駆動語句・会見 cadence・corpus 連続性)。**発言×介入ラベルのジョイント量は一度も計算していない**。イベント列挙すら凍結後の pass-1 に回した / P-A7: forward 期の介入エピソード実在は既知 (月次開示 08-28、07-30..08-26 窓 15.4 兆円) だが**日次日付は未開示** — forward OOS は MoF 公式日次開示のみで判定し、**発言テキストからの介入日推定も禁止**
- 🔴 **A-8 (レビュー由来 blocking、Codex P2 / PR #265 → 凍結前に修正)**: 初版の検出器は営業日カレンダー上でのみ会見日を引くため**土日祝開催の会見を黙って無視**していた。corpus 実測で該当 **13/512 件**、うち **2026-05-04 (みどりの日) は L4 `断固`** = trigger 水準なのに **event をひとつも生まない**実害。非営業日会見が集まるのは G7/IMF 総会週末と GW = 為替が最も緊張する局面で、miss 側バイアスが最悪の場所に入る。**修正 = 翌営業日へ roll forward (衝突は max)** — 前方に倒すのは、非営業日の発言が作用しうる最初の日が翌営業日だから (後方 roll は look-ahead)。**凍結後の検出器変更は pre-reg の破棄に等しいため、マージ前に修正**
- ⚠️ **`tools/pr_review_gate.py` が本 P2 を「指摘なし」と報告した** — inline review comment を見ていない。ゲート出力を額面で受け取らず生のレビュー本文を読んだことで捕捉 (MEMORY `project_review_gate_vacuous_2026_09_11` の再発、2 例目)。ゲート自体の修理は別 PR
- 回帰 pin `tests/test_family_a_ladder_detector.py` 20 本 (凍結定数 / A-1 remap 5 ケース / A-2 rearm / hit 窓分割 / gate 形状 / **検出器がラベル・価格を参照しない構造 pin** / A-8 roll-forward 4 本 — うち 1 本は corpus に L≥4 非営業日会見が存在することを pin する退行ガード)
- doc: [[family-a-adversarial-verification-2026-09-18]] / 凍結内容 [[family-a-statement-ladder-prereg-2026-08-19]] §10

## 2026-09-17 — 決裁バッチ執行: P-S1(a) Option C retire / U1 ミッション改定 / kalman postfill / U4 feasibility (user「推奨で進めて」)

- ⬛ **P-S1(a) sweep_reversion_eurgbp_late 退役 (rule:R2)** — estimand 監査 §7 二択で user が (a) Option C 採択。registry `t8-sweep-defer-decision` resolved 化 (net spaced EV −3.33 p/t / cap 救済集合空 / エッジ再現 38% を記録)、判定器は fetch/CLI 層で恒久 verdict `OPTION_C_RETIRED_USER` (evaluate() の凍結文言リプレイは pin 温存、新 pin 2 本 + watch 側退役 pin 1 本)。**shadow rescue は残置** (4原則#3、modules/ 変更ゼロ)。scheduled task `ps1a-sweep-trigger-executor` はマージ後に無効化。決裁記録: [[ps1a-option-c-retire-2026-09-17]]
- 🎯 **U1=(b): 正式ミッション = M3 系列 (+2〜3%/月 複利) へ改定 (rule:R1 user 決裁)** — 旧 anchor「月利21.6%接近」「20%/月」を記録から除去 (歴史文書は不改変保存、superseded バナー方式)。CLAUDE.md / index.md / roadmap v2.3 / rederivation / agents/cma coordinator を改定。スコアリング分母は time-to-M2 に統一。決裁記録: [[u1-mission-redecision-2026-09-17]]。U2/U3/U5 は未決裁のまま
- 🔵 **kalman carve-out GO の前提監査 → postfill packet 起案 (rule:R3 + R1 DRAFT)** — GO brief (09-01) の前提 2 点が stale と判明: carve-out は [[kalman-d7-minlot-carveout-prereg-2026-09-01]] LOCKED (PR #218) で**着地済み**、初 live fill #859468 (09-10、broker +9.1p) も**発生済み** → コード変更 no-op を明示。09-01 LOCK の凍結済み義務 (初 fill + 90 日) を機械執行し registry `t9-kalman-d7-live-n10-ev-check` deadline 2026-11-30 → **2026-12-09**。EV estimand 凍結 (broker realized net) + storm 拡張凍結は [[kalman-d7-carveout-postfill-packet-2026-09-17]] で user 最終承認待ち。座礁していた戦略カードの storm 族 A/B 法医学 (ローカル未コミット) を本 PR で救済
- 📊 **U4 供給空間 feasibility 初版 (rule:R3)** — (a) 有償データ vs (c) FX 以外の比較 [[supply-space-feasibility-2026-09-17]]。packet §U4 の「E22 で決裁点定義済み・即決可能」は PASS 条件付きで実際は不到達 (explore FAIL で不要化済み) と訂正。推奨仮決め案 = (a) 主経路 (E1 verdict 条件付き CME DataMine probe 数百$ 上限) / (c) は S1 まで。判定点 10-15 (E1 first look) / 10-18 (scan#6)

## 2026-09-17 — research(scan#5): 外部仮説スキャン第5次 — WIP 会計訂正 + family A forward コーパスの構造修復 (rule:R3)

- **新規採用 0 (3 周連続)** — E29 インフレリスク条件付き予測可能性 = 棄却 **C4** (条件付けるべき正 EV ホストが母集団に不在、[[friction-adjusted-ev-map-2026-07-07]]) / E30 CLS 決済フロー = 棄却 **C1** (商用のみ、U4 有償候補へ条件付き追加) / E31 グラフ学習・ハイブリッド DL = 棄却 **C2/C3** (E28 同型、OHLCV 3 周 FAIL + Mesfin 2026)
- 🔴 **WIP 発動会計を訂正 (§2)** — 09-15 E23 park 時の「能動測定ライン = **0 本**」は **台帳 #27 (family A) の数え落とし**。統治規則は「S1-S4 の本数」でなく **「今日着手できる本数 ≥1」** (パイプライン §5 追補、2026-08-14 user 承認) であり、#27 の次ステップ (敵対的検証 → 凍結、期日 09-24) はブロッカー無しで着手可能だった → **臨時スキャンの発動条件は成立していなかった**。実害ゼロ (期日 09-18 は翌日、焼いた窓・消費枠なし) だが会計自体が発動ゲートなので訂正。**正: 着手可能 1 / 時限ロック 3 / 条件付き 2 / park 2**。phantom blocker 型の 2 例目
- 🔴 **`mof-statements-daily` の構造欠陥を修復 + 実データ回収 (§1.2)** — 直近 20 run で **8 失敗 (40%)**、サンプル 4/4 が**同一根因 = GDELT HTTP 429** (ローカルでも再現 ⇒ 第4次 FRED の「runner IP WAF」仮説は本件では反証、GDELT 側の慢性レート制限)。`main()` の dict literal 直列評価で最後段 GDELT の raise が**先行 4 ソースの成果ごとプロセスを落とし**、workflow の commit step に `if:` が無いため runner の ephemeral disk ごと破棄されていた。**実害を実測**: 失敗 run 35163419350 は `[daily-conf] new=1` (my20260915.html) / `[daily-rss] new=1` / `[score] 512 conferences` まで到達して全破棄、repo は **511** で取り残されていた
- 🟣 **修復**: per-source isolation (`_STEPS` + try/except、**全ソース試行後**に hard 失敗のみ raise、失敗も summary に `error` 保持) / **soft-hard 分類** `_SOFT_SOURCES={"gdelt"}` (全範囲再取得の派生系列 = 1 日の失敗に情報価値なし。hard 継続は 40% 頻度のアラート = 「読み手のいない検知器」の再生産) / workflow "Commit data" を **`if: ${{ !cancelled() }}`** / **test pin 4 本** (`tests/test_mof_statements_daily_isolation.py`: soft 非 raise / hard raise / **raise は全ソース試行後** / soft 集合固定)
- **回収実行**: 修復後 driver をローカル実行し `my20260915.html` + RSS 1 件を回収、conferences **511→512**。⚠️ 回収した文書は **ladder 語句ヒット 0 = negative sample** — family A の検出器価値は **FP 率較正**にあり、negative 欠損は precision を機械的に押し上げる。凍結 (09-24) 直前だった点で単なる欠損より重い
- 🔵 **欠陥族 3 例目**: zn-cache-refresh (write-only commit) / rate_anchor_ingest (直列 ingest) に続く同型。**第4次は姉妹ツールへ横展開せず 7 日後に実データ欠落として顕在化** → 教訓 [[lesson-defect-family-sweep-siblings-2026-09-17]]。第4次の「日次 union だから恒久損失なし」は **rss (ローリング窓) について偽**と訂正
- ✅ **第4次修復の運用検証を消化 (§1.1)** — `rate-anchor-daily` **4/4 success** (us_treasury date_max 2026-09-16 = Treasury fallback が CI 実働) / `zn-cache-refresh` **2/2 success** (zn_f_daily 08-18 凍結 → 09-16)。第4次「次アクション 3: 初回 green を実ログで見るまで修復完了と言わない」をエビデンス付きでクローズ
- **registry**: `edge-supply-scan-monthly` deadline 09-18 → **2026-10-18** (第6次、四半期モダリティ棚卸し同乗) / `family-a-adversarial-freeze-deadline` に「唯一の着手可能ライン」+ 凍結前 corpus 連続性チェックを追記
- **§4 提案 (未執行、user 決裁事項)**: 月次スキャン → **四半期 + イベント駆動**。根拠 = 直近 2 周 採用 0、棄却理由が C1 有償 / C2 既 ban / C4 正 EV ホスト不在 の 3 分類に収束。**WIP 緊急トリガは維持**するので探索放棄ではない。cadence は user 承認済み規律のため autopilot の R2/R3 権限外
- doc: [[external-hypothesis-scan-round5-2026-09-17]] / [[lesson-defect-family-sweep-siblings-2026-09-17]]

## 2026-09-15 — research(E23): explore verdict = ❌ **UNDERPOWERED / park** — pass-0 census PASS → pass-1 で Gate B N=56<100 (rule:R1 手続き、純研究)

- **期日 09-20 の 5 日前倒しで verdict 確定**。**pass-2 (測定) は解錠せず = イベント×リターンの結合統計を一度も計算していない** → explore 窓の outcome にも OOS 窓にも未接触のまま park (窓は焼いていない)
- **Gate A (headroom) は 3/3 ペア通過** — 無条件 median |fwd5| = EUR_USD 71.5p (閾値 20.0) / GBP_USD 95.0p (45.3) / USD_JPY 81.9p (21.4)。**走る余地はあった**
- ❌ **Gate B (power) 未達: pooled イベント N = 56 < 100** (boe 22 / fed 15 / boj 14 / ecb 5)。会計は閉じている: explore 使用可能文書 327 = イベント 56 + void 267 + 各 CB 初回 4。**void は全件 `delta_nh_zero`** (staleness>120d 0 / Fed·ECB 同日衝突 0 / t0 写像不能 0)、**NH=0 の文書が 279/327 = 85.3%**
- 🔵 **死因 = 特徴量側の疎性 (抽出バグでないことを敵対的に実証)**: 凍結辞書の形容詞語幹は explore コーパスに **7.27 回/文書**出現するのに、直後トークン上位は `in` 500 / `at` 210 / `than` 139 / `the` 111 / `levels` 84 / `trend` 64 … と機能語・辞書外名詞。中銀声明の語法 ("increases **in** the federal funds rate" / "strong **labor** market" / "higher **levels**") が ABG の two-word combination (形容詞語幹 + 名詞語幹の**文内隣接**) と噛み合わない。原典 (Riksbank minutes) は長い叙述的議事録で、政策声明はその語法を持たない。**V6 の文境界規則は正しく機能** ("remained **low. Inflation** remains elevated" を正しく非計数) — バグではない
- ⚠️ **power caveat (§6 の義務)**: 本結果は「中銀テキストに方向情報が無い」ことを**一切示していない**。示したのは「**凍結 ABG 辞書 × G4 政策声明という特徴量化では 10 年分でも検定可能なイベントが 56 件しか作れない**」= **測定可能性の否定**。「CB テキストは falsified」型の引用は estimand 監査なしに禁止 (MEMORY `feedback_audit_past_verdicts_2026_08_05`)
- **救済禁止** (§6): 窓拡張・CB 追加・語彙拡張・文書種追加 (minutes/会見) はいずれも恒久禁止、再開は split 再設計を伴う**新 pre-reg のみ**。explore 枠は LOCK 時消費済み (1/3)、本 verdict で追加消費なし
- 🔴 **供給ラインへの含意**: E23 は park 時点で**唯一の能動測定ライン**だった → **能動測定ライン = 0 本**へ (残は時限系のみ: E1 10-15 / ECG 11-06 / E12 2027-02-05)。registry `edge-supply-scan-monthly` の **WIP 原則 (S1-S4 < 2 本 → 期日を待たず臨時スキャン、R3) の発動条件が成立** → 期日を 10-18 → **09-18 へ前倒し**、到達経路 (第 5 次スキャンの起草先 + 先に読む ban 台帳) を message に明記。外部仮説 explore→OOS 生存は通算 **0/18 系統** (base rate 4%、CI 0.7-19.5% は不変)
- 🟣 **新設 `tools/e23_pass1_events.py`**: イベント列挙 + Gate A/B。**firewall** = 成果物に per-date の forward 値を持たせない (構造テスト pin)。価格は (a) t0→valid D1 写像 (b) Gate A の**シグナル非依存**な無条件 |fwd5| 集計 の 2 用途のみ。価格ソースは family C と同規律で gap-fill 済 `{PAIR}_15m_2014_2026.parquet` に限定 + sha256/行数 manifest assert (`raw/bt-results/e23/data_freeze_manifest_2026-09-15.json`)、**bare rolling parquet はコードとテストで使用禁止**
- 出力: `knowledge-base/raw/analysis/e23-pass1-events-2026-09-15.md` (+ `.json`) / verdict 全文 = pre-reg §11

## 2026-09-15 — research(E23): pass-0 コーパス census 執行 — gates 全 4 CB PASS / pass-1 解錠 (rule:R1 手続き、純研究)

- **起点**: registry `e23-explore-verdict-deadline` (2026-09-20) の未執行。E23 は **現在ただ一本の能動測定ライン** (E21/E22/E7/range_fade が全て FAIL クローズ、残りは時限系 E1 10-15 / ECG 11-06 / E12 2027-02-05)。pre-reg 🔒 [[e23-cb-text-explore-prereg-2026-09-10]] §9-2 の pass-0 (コーパス取得 + census、outcome 非接触) を執行
- 🟣 **新設 `tools/e23_corpus_fetch.py`**: Fed / ECB / BOE / BoJ の**公式サイト primary** から政策声明を取得 (無料・keyless)。**398 文書** → `data/external/cb_statements/{cb}/{YYYY-MM-DD}.json` + `manifest.json` (文書別 sha256 + 文字数)。差分取得 (既取得は再取得しない)。配布形式は BoJ ≤2017 / BOE ≤2020 が PDF、以降 HTML — 同一の境界規則で両方から本文を取る (形式はコンテナであってシグナル DoF ではない)
- 🟣 **新設 `tools/e23_corpus_census.py`**: pre-reg §2 の census gate を機械実行。**verdict = PASS_TO_PASS1** — per-CB 被覆 (各年 ≥6 声明を ≥80% の年で) は fed 10/10 / ecb 10/10 / **boe 8/10 (境界ちょうど、2014 は MPS という文書種が未存在・2015 は 8 月創設)** / boj 10/10 で**生存 CB 4 ≥ 2**。V1 Fed/ECB 同日衝突 0 件 / V3 BoJ 英語版 当日付一致 93/93 / staleness >120d void 0 件 / 機械的欠測 BOE 4 件。出力: `knowledge-base/raw/analysis/e23-pass0-census-2026-09-15.md` (+ `.json`)
- 🔴 **正直な power 警告 (LOCK 時点では未知、§5 P-E3「コーパス本体未読」)**: 凍結 ABG 辞書の当たり密度が **0.036〜0.424 matched bigram / 文書**。生存 CB の explore 文書 327 件のうち **matched bigram を 1 つ以上持つ文書は 50 件** → ΔNH≠0 には NH_t / NH_{t−1} の一方が非ゼロ必要 ∧ 非ゼロ文書 1 件は隣接ペア 2 つにしか関与しない ⇒ **イベント数の機械的上界 = 100 = Gate B 閾値ちょうど**。実 N は void・隣接重複で必ず下回る ⇒ **pass-1 で UNDERPOWERED の公算が高い**。原因は設計どおり (ABG は長い議事録向けの文内隣接カウント、政策声明は短く "remained **low. Inflation** remains elevated" のように文境界を跨ぐ — V6 の文境界規則が正しく弾いておりバグではない)。**救済的な語彙拡張・文境界緩和・文書種追加は §0-3 / §6 により恒久禁止** — 凍結仕様のまま走らせて正直に park する
- ⚖️ **BoJ 文書同定の解釈記録 (pre-reg §10.3、価格に一度も触れずに確定)**: BoJ は**政策変更があった回だけ表題を変える** (2014-10-31 QQE 拡大 / 2016-01-29 NIRP 導入 / 2018-07-31 / 2020-03-16 / 2024-03-19 / 2024-07-31 等)。表題文字列で拾うと **政策ニュース最大の回だけが落ちる = 内容条件付き選択バイアス**で estimand が「政策変更のなかった会合限定の tone 差分」へすり替わる → 同定を **表題一致 → BoJ 主文書スロット `k{YYMMDD}a` → 同日先頭** の順に凍結 (構造ベース、内容非依存)。ECB は "Monetary policy decisions" = 文書種名そのもので同じ問題を持たないため表題一致のまま
- 🔵 **抽出は無トリム規則**: 公式ページの本文コンテナ (Fed `div#article` / ECB・BoJ `main` / BOE は MPS 節境界語) をトリムせず採る。定型フッタは hawk/dove bigram に寄与せず ΔNH は定数を打ち消すため、トリム規則を置かない方が抽出 DoF が閉じる
- 🔵 **読み手が先にあった実証**: 初回取得で ECB 2022 が接続リセットで丸ごと欠落したが、census の年次内訳表 (2022 = 0) が即座に露出 → 再取得で埋めた。[[lesson-constructed-url-404-is-not-absence-2026-08-31]] の「収集経路を足したら読み手を同じコミットで足せ」が今回は先に守られていた形
- 🧪 pin `tests/test_e23_corpus_harness.py` (16 本): 凍結辞書 sha256 == pre-reg pin (doc 側の書き換えも二重照合) / gate 閾値・窓の凍結値 / BOE MPS 節境界 (表題行・目次行を始点にしない) / 公表日 2 形式 / BoJ 同定が表題条件付けに退行しない / census の 80% 境界は inclusive / 生存 <2 で DATA-BLOCKED / **pass-0 モジュールが価格系を参照しない構造 pin**
- ⚙️ `render.yaml` buildFilter に `data/external/cb_statements/**` を追加 (研究ハーネス専用・ランタイム参照ゼロを全数 grep で確認、コーパス一括コミットで取引エンジンを再起動させない)
- **規律**: live/shadow/tier/lot/Kelly 変更ゼロ。価格データ未参照。explore 枠消費なし (LOCK 時に 1/3 消費済み)。残 = pass-1 (イベント列挙) → コミット → pass-2 (測定、seed 20260910)

## 2026-09-14 — feat(kb): 日次市場レビュー + 観測採集プロトコル新設 (S0 intake 層) (rule:R3)

- **起点**: user 依頼「前営業日のチャート検証から毎日複数エッジを設計できないか」。クオンツ判定 = 「毎日勝てるエッジ設計」は base rate 4% ([[process-meta-audit-2026-09-07]] §1) の下で数学的に不成立 (年 700–1000 仮説の多重検定爆発)。**採集と検証を分離**した修正版のみ採用: 日次は記述級の観測採集、検証は既存 pre-reg バッチ経路
- 🔵 **新設**: [[daily-market-review-protocol]] — S0 intake の上流観測層。統計規律 7 項 (記述級のみ / 凍結 look family の registry 事前確認 + outcome 量記載禁止 / counts=marginal 限定 / 保存 OOS 非接触 / トリガ日記録+卒業時 OOS 除外 / 台帳番号は既存経路のみ / 卒業前 ban 監査必須)、卒業 = 同一 family ≥3 独立観測 (独立 = 異日付の異 event)、読み手 4 層宣言、自己反証条項 §6。α 予算消費ゼロ。Tier B-daily (`daily_hypothesis_scan.py`) Phase 3 有効化は非スコープ (別決裁)
- 🔵 観測台帳初号: [[daily-observations-2026-09]] — シード 3 観測 (O-2026-09-11-1 CPI flush 回帰 ⚠️**E15-H1 phase-0 CPI-fade OOS C5 FAIL が直接の先行 ban** / O-2026-09-14-1 WG drift 境界前提破れ / O-2026-09-14-2 CB 会合前週 marginal flag)。`.claude/commands/wiki-daily.md` に Phase 2.5 追加、registry に `daily-market-review-30d-effectiveness` (期日 2026-10-14) 追加
- 🔵 **執行 QA 初発見 (O-2026-09-14-1)**: 2026-09-13 日曜 USD_JPY gap −50.0p で weekend_gap_fade は仕様通り発火 (shadow row id 17602 記録) したが、live 送信は WG_EXEC_B `ABANDONED_DRIFT` (tradeable 時点 drift +41.0p > 凍結境界 +8.0p)。**バグではなく凍結 amendment (user 承認 2026-09-10) の仕様通り**。ただし drift 実測は境界 +8.0p の ~5 倍 / 導出時 p90 6.7p (全 48 pair-weekend) の ~6 倍 — 大ギャップ event ほど live 送信が構造的に不可能になる選択バイアスの疑い。live fill 0 は live send 経路到達 event 4 連続 (meta-audit 集計基準、F2 期限 2026-12-31)。**escalation は registry `weekend-gap-execution-amendment-g0prime` (期日 09-28) へ回付 — +8.0p 境界の R1 再起案は packet §6 事前コミット (fill 不成立 2 連続、本 event は #1) まで保留** (user が独立に指示する場合はこの限りでない)
- ⚠️ **敵対的レビュー (3 レンズ) が初稿を P1×3 で棄却 → 修正済み**: (1) O-2026-09-14-2 初稿の「30 分内回帰率 CB 週比較」は WG の未登録 split 事後シード = 観測前宣言違反 → marginal flag のみに縮退 (2) E7 の family 特徴づけを記憶から誤記 (正: E7=発表後 surprise-z 順方向 drift、直接 ban は E15 phase-0 CPI-fade) → 原本実読を §2.7 に義務化 (3) 初稿が shadow outcome を境界再審の根拠に併記 = selection-on-outcome → outcome 量を削除。**シード観測自身が規律違反を初日に 2 種踏んだ = 定義の緩さは即座に悪用される実証**として protocol 冒頭に記録
- ⚖️ 月利目標への寄与の正直な評価: 本プロトコルは供給レートの乗数であり、M1 (現実的 2027 前半) / M2 (中心 2027-Q4〜2028) / M3 (中心 2029+) の時間軸自体は E1 first look (2026-10-15、⚠️ ingest 停止中 = 09-14 07:01Z 時点も AUTH FAILURE 継続、24h 欠測 breach 09-13T23:57Z 超過 → first look ~4 週延期が発効見込み) と PASS→live 変換の実証に律速される

## 2026-09-14 — diag(exit): 勝ち側 exit の regime break を確定 — shadow の avg_win 縮小は劣化でなく計測の是正 (rule:R3)

- **起点**: 2026-09-13 cell deepdive が最優先アクションに指定した「`sr_anti_hunt_bounce` の avg_win が 2026-05 の 19.03p から 3.5〜5.9p へ 1/5 に縮んだ原因の実測特定」。新ツール `tools/win_side_exit_decomposition.py` (副作用なし) で Render PROD 17,602 件を close_reason × outcome × 保有時間 × MFE へ分解
- 🔵 **確定**: 縮小の原因は市場でも戦略でもなく **shadow の終端機構が 1 日で入れ替わった**こと。WIN 行の終端は `< 06-03` = `MAX_HOLD_TIME` 70.6% / `WEEKEND_CLOSE` 29.4% / `SL_HIT` **0%** (avg_win 19.42p, median 保有 **8.00h**) → `≥ 06-03` = `SL_HIT` **100%** (avg_win 3.96p, median 保有 **0.54〜1.28h**)。`SL_HIT`∧`WIN` = BE/トレールが利益側で刈った の意 (MEMORY `project_sl_hit_label_collision`)
- **機構帰属**: commit `ab7a4931` "fix(exit): persist shadow SL changes directly to DB" (2026-06-03 **07:58 UTC**)。それ以前 shadow の SL 変更は `modify_sl_sync` の False 戻りで毎 iteration ロールバックされ、**BE-lock / SMC BE+0.1 / ATR×0.8 BE / ATR×1.5 trail / v6.4 TP extender が全て dead code** だった ([[lesson-shadow-sl-rollback-bug-2026-06-03]])
- **敵対的検証 3 点**: ①**遷移の鋭さ** — 全戦略 shadow の WIN 行 `SL_HIT` 率は 06-01 0.0%(N=19) / 06-02 0.0%(N=22) → **06-03 76.7%(N=73)** → 06-08 89.3% の step function。市場レジームでは作れない形。②**MFE censoring の排除** — capture 0.815→0.55 と avg_MFE 23.34→6p は exit を早めた機械的帰結 (MFE は exit 時点までしか観測されない)。exit 非依存の指標では全 clean 行 **median MFE が 2.00→5.70p と上昇**、LOSS 行保有時間も 2.01→4.00h と伸長 → **市場側の順行余地は劣化していない**。③**shift-share は非同定** — 群が前後で素に交わらない (share_A(SL_HIT)=0% / share_B=100%) ため `within 100%` は補完値。「群内劣化」と読んではならない
- 🔴 **全戦略への波及 (estimand break)**: shadow pre-fix N=5,377 WR 26.3% / avg_win 11.72p / R:R **1.90** / EV −1.45 → post-fix N=7,200 WR **51.5%** / avg_win 4.35p / R:R **0.55** / EV −1.61。**WR +25.2pp は MEMORY `project_be_trail_inflates_python_bt_wr` の +20pp 水増しの本番 shadow での再現**。EV はほぼ不変 = MEMORY `feedback_partial_quant_trap` の典型。pre-fix shadow R:R 1.90 vs 同期間 live 1.01 (乖離 1.9×) → post-fix shadow 0.55 vs live 0.42 で接近、**異常だったのは pre-fix shadow の方**で fix は live 忠実度を上げた
- ⚖️ **deepdive の解釈訂正**: 「R:R が反転したまま戻っていない = 継続中の構造的劣化」は誤り。**一度きりの計測体制の付け替え**であり、fix を戻さない限り「戻る」ことは起きない
- 🔴 **決定への影響**: 9 週連続で出ている唯一の PAIR_PROMOTED 候補 `sr_anti_hunt_bounce × EUR_JPY × Tokyo × BUY` の掲載値 (N=32 / EV **+7.11** / PF 4.29) は、**pre-fix 14 行が総 pips の 77% (+174.4/+227.6) を担った結果**。fix 日で切ると post-fix は N=18 / EV **+2.96** / R:R 1.04 で、EV は 4.2 分の 1・N は候補化閾値 `MIN_N=20` 未満。前週の「post-May 単独で Wilson_lo 0.567 維持 ✅」は (a) cut が 5 月末で fix 日 (06-03) でない (b) 通した gate が WR ベースで、その WR こそ BE/trail が水増しする量 の 2 点で反証になっていない
- ⚠️ **pre-reg LOCK は不可侵のまま**: forward 枠 (`entry_time ≥ 2026-08-05`, fresh N=32/40) は全数 post-fix で汚染なし。本件は週次レポートが毎週再掲する**記述統計の訂正**であって P-10 の中間再計算ではない
- **恒久ルール + pin**: shadow の payoff 系統計 (`avg_win`/`avg_loss`/`R:R`/`WR`/保有時間) を **2026-06-03T07:58Z をまたいで集計しない**。定数 SSOT = `tools/win_side_exit_decomposition.py::SHADOW_EXIT_REGIME_BREAK`、pin = `tests/test_win_side_exit_decomposition.py` 6 本 (境界定数 / 既定 split が月境界へ戻らない / 宣言フィルタ 3 条件 / **close_reason を outcome 分割なしに集計しない** / 境界が時刻まで効く / 分解合計の健全性)
- **メタ教訓** ([[lesson-shadow-sl-rollback-bug-2026-06-03]] に追記): 修理自体は正しかったが「**この修理は過去データとの比較可能性を壊す**」の 1 行と読み手側の pin が無かったため、下流が **103 日間**境界をまたいで集計し続けた。挙動を変える修理は estimand の断絶を同時に宣言せよ
- 全文: [[win-side-exit-regime-break-2026-06-03]] / 入力証拠: `raw/cell_deepdive/2026-09-13/`

## 2026-09-11 — docs(e1): ingest 停止の帰属精密化 + budget debit 更新 — 復旧は user credentials 再投入のみ (rule:R3)

- **停止境界を Render ログで確定** ([[e1-ingest-outage-2026-09-10]] §7a): 最終 login 成功 09-10T06:58:45Z (PR #231 デプロイ instance) → 最初の失敗 07:06:03Z (PR #232 デプロイ instance)。**credentials 無効化は 7.3 分窓 (JST 15:58–16:06) にサーバ側で発生**。§1 の「~07:18Z 推定」を置換
- **帰属の消去法完遂** (§7b): プロセス停止 / disk / ベンダー API 全面障害 / rate limit (実測 <80 req/24h < 100) を全て実測で除外。統制実験 = garbage credentials で本番と同一の `"Wrong email/password."` (HTTP 200) → API は正常でエラーは認証拒否の正規応答。**残存仮説は (a) password 失効/変更 or (b) account lock のみ** — 新 egress IP login 直後の無効化という時刻相関は (b) を示唆、判別は user の web ログイン + メール受信箱 (09-10 16:00 JST 前後の Myfxbook メール) 確認のみ
- **budget debit 更新** (§7c + [[e1-positioning-ingest-2026-07-14]] §14 台帳新設): 09-11T07:30Z 時点 残 **18.5h (h=4h) / 16.5h (h=24h)**。§2.5-2 連続欠測 24h には **09-11T08:58:44Z 到達**。breach 予測不変 = **09-13T23:57Z (h=24h)** → first look 4 週 postpone = M1 経路 ~4 週遅延。**実務デッドライン = 日曜再開 09-13T21:00Z までの credentials 再投入** ([[e1-ingest-outage-2026-09-10]] §5)
- 通知経路 live 検証 (§7d): anomaly_watcher が `positioning_auth_failed`/`positioning_stale` を 15 分毎に発火中と実測 — 検知系は生きており律速は user アクションのみ。コード変更ゼロ、live 挙動不変。重複修理なし (backoff/fail-loud/runbook は PR #243 で完了済み)

## 2026-09-11 — fix(process): マージゲートが進捗サマリを「レビュー到着」と数えていた — R2 ゲートが全 PR で空だった (rule:R3)

- 🔴 **実測 (PR #249)**: PR open の **18 秒後**に `tools/pr_review_gate.py 249` が「connector レビュー到着済み・P1/P2 指摘なし — **マージ可**」(exit 0) を返した。その時点で Codex connector の進捗サマリ Status は `🔄 **Running**` で、レビュー本体は 1 行も出ていない
- **機構**: `collect_findings` は「author が codex/chatgpt にマッチするコメントが 1 件でもあれば `arrived = True`」としていた。connector は PR open 直後に `<!-- codex-pull-request-review-summary -->` の**状態表**を投げる (Status 列が `🔄 Running` → `✅ Completed` と in-place で書き換わる) ため、この 1 件で到着判定が立ち、findings は当然ゼロなので exit 0。**`--wait` も無効** — 状態 2 を一度も名乗らないので待ちループに入らない
- **影響**: [[process-meta-audit-2026-09-07]] R2 ゲートは「レビュー→マージ 56 秒〜2 分が常態 / PR #213 はレビュー到着の 6 秒前にマージ」を塞ぐために作られたが、**ゲート自身が同じ追認をしていた**。CLAUDE.md がマージ前実行を義務づけている全 PR に対して実質空。「検知器も write-only になりうる」(2026-08-28) / 「防御が名乗る範囲をカバーしない」(keeper 09-10) と同型の 3 例目 — **ゲートは自分が測る量を名乗れていたか**を必ず counterfactual で確認すること
- 🔴 **第 2 の空振り形状 (PR #250 実測、本修理の PR 自身で発覚)**: connector は「To use Codex here, create an environment for this repo」という**セットアップ通知**も同じ author で投げる。レビューは 1 度も走っていないのに、旧判定ではこれが到着 (findings ゼロ → exit 0) になる。サマリ対策だけでは塞がらず、**到着の positive evidence を 3 つに限定**した: (i) 正式 review オブジェクト / (ii) P1/P2 を含む本文 / (iii) サマリ Status=Completed。素の connector コメントは**通知であって到着ではない** (fail-closed)
- **修理**: (a) サマリコメントを findings 母集団から除外し、到着判定は `summary_state()` に一本化。(b) Status=`Running` は **exit 2 (待て)**、`Completed` のみ到着。複数レビューで Running と Completed が混在する場合は **Running 優先** (fail-closed)。(c) サマリ表の Commit 列 SHA と PR HEAD を照合し、不一致なら exit 2 + `@codex review` の実行を指示 — CLAUDE.md が prose で書いていた「修正 push 後は再レビューが自動で走らない」をコードに降ろした
- **pin** (`tests/test_pr_review_gate.py` +10 本、計 24): Running サマリ単独で exit 0 を返さない (欠陥の直接 pin) / Completed + HEAD 一致で exit 0 / Completed だが HEAD 不一致で exit 2 / Running 優先 / サマリ除外が本物の finding コメントを落とさない / セットアップ通知単独で到着にならない / findings ゼロでも正式 review オブジェクトなら到着 / ヘルパの純粋性 / **counterfactual 2 形状** (旧 `collect_findings` を復元すると Running サマリ・通知コメントの両方で exit 0 に戻り、修理後は両方 exit 2 = pin が空でない証拠)
- 本欠陥は PR #249 (ps 席 verdict) のマージ手続き中に、ゲート出力を額面で受け取らず GitHub 側の実状態と突合したことで発見した。#249 自体はその後 Status=Completed / SHA 一致 / findings ゼロを実確認してからマージしている

## 2026-09-11 — verdict(ps): 席供給 30d 再計測 = 🔴 REJECT (capture 20.6%) + §8 帰属完遂 + HourlyEngine C1 計装 (rule:R3)

- **正式 verdict = REJECT** ([[ps-seat-supply-remeasure-2026-09-10]] §7): 窓完成 (2026-08-11〜09-11T00:00Z、`window.complete=true`) 後に `tools/ps_seat_supply_remeasure.py` を pre-reg どおり 1 回実行。design 期待 **34** (床 15 超) / 観測 unique **7** (LIVE 6 / shadow 1) / **capture 20.6%** [Wilson 10.3-36.8%] < 80%。是正前 baseline **31%** (親監査 §1) を**下回り**、PR #172 §7(a) の「31%→~100%」予測は不成立。09-09 中途窓 diagnostic から差分ゼロ (design 側も 1.9 日で 1 本も増えず)。生値: `raw/audits/ps-seat-supply-verdict-2026-09-11.json`
- **§8 補足検証 完遂 — 3 項目とも 3 席 (NZD_JPY/EUR_AUD/USD_CAD、design 17 本) のゼロを説明しない**: ①**hedge_block 寄与 = 0 本**。`MODE_CONFIG` 実測で 3 ペアは搬送 mode が席のみ (15m 対向 mode 不在) = 反対建玉を作る経路が無く**原理的に bind 不能**。実測も 0 ([[ps-seat-hedge-block-snapshot-2026-09-10]] §2、3 桁が立つのは 15m 側 `daytrade_eurgbp` 129 / `daytrade_audjpy` 109 のみ) → 親監査 §3 の hedge_block は **AUD_JPY 固有**で family 要因ではなかった。②**blackout 床 = 17 本中 ~0.2 本**。窓内 deploy を buildFilter 再構成で 104/31日 = 3.4/日、1 回あたり上界 5 分 → 1.2% wall-clock。10x 過大仮定でも ~2.0 本、**説明要因になるには 84% 被覆 (実測の 70 倍) が必要**。③**残余 ~100% は帰属不能**
- 🔴 **残余の性質 = 「未知の抑制要因」ではなく「測っていない」**: 観測面 3 つが揃って hourly 経路を覆っていなかった — `_block_counts` は再起動でゼロリセット (取得時 tick_counts=45 = 数十分ぶん) / `gate_block_daily` (PR #248) は**稼働開始が 09-11** で窓の履歴ゼロ / `evaluated_candidates` (C1) は 2026-04-28 以来 `_dt_engine` 経路にしか call site が無く、**`compute_hourly_signal` は `evaluate_all`→`select_best`→`split_shadow_always` を呼ぶだけで `log_candidates` を呼んでいなかった**。本番 31d summary の 48 戦略に `price_shock_rev_*` が 1 つも無い (観測 7 行を出した EUR_GBP / AUD_JPY の席すら不在) ことで確定。hull funnel (08-24) の「書ける が読めない」より **1 段階手前 = そもそも書いていない**
- **執行 (live 挙動不変)**: `app.py::compute_hourly_signal` の `select_best` 直後に `log_candidates` を追加 (best-effort try/except = DTE 経路と同一契約)。`bar_time` は PR #168 / 08-24 の fallback (`bar_time or df.index[-1]`、UTC 正規化) を踏襲 — live は `compute_fn(df, tf, sr, symbol)` で bar_time を渡さないため素の `bar_time` では hourly 行も全 NULL になる (call-site 欠落 4 例目の再発防止)。pin: `tests/test_hourly_candidate_logging.py` 10 本 (call site 存在 / 敗者含む全候補 / 早期 return より前 / try-except 保護 / bar_time 派生値 / DB 往復の行動証拠 / 候補ゼロ no-op / counterfactual / 5 席の engine 所属)
- **registry**: `ps-seat-supply-remeasure-30d` → **resolved** (REJECT + §8 帰属を resolution に全文記録)。後続 `ps-seat-supply-hourly-c1-coverage` (deadline **2026-09-25**、deadline_info + 実行コマンドを message に埋め込み) を新設 — 計装到達確認 / 書込み量実測 / 3 席残余の (A) 上流 vs (B) 下流 帰属。**3 点が揃うまで残余は「未帰属」据え置き、帰属が出るまで §7(a) 型の供給是正を重ねない**
- **look 保全**: 本件は EV / WR / PnL を一切計算していない (P-10 型 ban 遵守)。`ps-carveout-regate-post-172` (09-30、clean live N≥10 で EV 判定) の look は**未消費** — ただし capture 20.6% のままでは N≥10 到達困難で、同エントリの「N<10 → 供給側の別問題として stale レビュー」分岐に入る見込み

## 2026-09-11 — diag(hull): 発火残余 4.7x の下流 gate 帰属確定 + block 計装 (rule:R3、P8)

- **帰属確定** ([[hull-fire-rate-funnel-2026-08-24]] §8 追記): C1 bar デデュープ (生行は ~52x poll inflation) で 08-26〜09-10 の unique 候補バー 20 / select_best 勝者バー 18 (**7.9/週 = offline 期待 7.61/週 と一致、上流無傷**) に対し trade 化 1 本 (09-01 08:15 shadow) = 生存率 5.6%。直近 7d 勝者バー 4 本 (09-04 08:15/10:00、09-10 09:45/10:45) は全滅。**残余 ~4.7x は 100% select_best 通過後の `_tick_entry` ガードチェーンに局在、order 層は無実** (到達 1 件は正常 shadow 化)
- **勝者バー 1 本ずつの死因** (Render ログ SENTINEL_BLOCK_DIAG 全数突合、帰属可能 14 本): 第一死因 spread_guard 3 / same_price 3 / session_pair(EUR_USD_Tokyo) 3 / score_gate 2 / hedge_block 2 (+二次 score_gate 3、mtf_strong_bias 1)。hull 固有の構造衝突 = **spread_guard×TP=basis 契約 (spread 平常でも 29-36%>20% 常時超過)** と **score_gate×SELL 正 score (SELL 側ほぼ全滅)**。08-26/27 の 4 本は Render ログ実効 retention ~2 週で帰属不能 (証拠の時限消滅、carry-dip 同型)
- **「残余=未計装」の正体 = 計装の揮発性**: killer gate は全て in-memory `_block_counts` + SENTINEL ログで計装済みだったが、counter は再起動毎ゼロ (本番実測 total=9 / hull per_strategy={})・ログは ~2 週失効。→ **`gate_block_daily` 永続日次集計を新設** (`modules/block_event_logger.py`、retention 90d、`_block()`→`_record_entry_block` 抽出 + order_bar_dedup 経路、lock 外 best-effort 書込み)。読み手 = `/api/demo/block-counts?days=N` の `persisted` (writer と同一コミット)。estimand 宣言 `gate_block_attribution` + counterfactual テスト (`tests/test_block_event_logger.py` 10 本 — 永続配線 kill で fail する restart-survival pin / 旧 closure との挙動同一 pin)。**live 挙動 (発注判断・gate 判定) は不変**
- registry `t8-hull-shadow-freq` message 更新: **09-30 retire 判定 (shadow N<5) は誤帰属 — band 割れの実体は「シグナル枯渇」でなく「下流 gate による shadow 蓄積遮断」**。retire/復帰/gate 免除は persisted block 帰属を経由すること。gate 挙動変更 (spread_guard 免除等) は R1/R2 別決裁
- 付随観測 (別 issue 候補): same_price ログ表記バグ (`same_price_0pip`、非 JPY で `{dist*100:.0f}`→"0")、score_gate×hull SELL の sign-flip 整合監査、gate の shadow 分岐が動的 `_is_shadow` でなく静的 `_is_shadow_eligible_full` を見る件 (4原則#3 テンション)
## 2026-09-10 — fix(rnb): confidence 単位不一致 — 新設 shadow レーンの構造的無発火を修理 (rule:R3)

- **バグ 1 確定 (conf 単位不一致)**: `compute_rnb_signal` (app.py) の BUY confidence は `round(min(_score/2.5, 1.0), 2)` = **0-1 スケール (max 1.0)** だったが、`demo_trader._tick_entry` の conf gate (`confidence < confidence_threshold`, threshold=**30**) は全戦略共通で **0-100 スケール**前提 → rnb BUY は 100% `conf<30` block。PR #238 で登録した shadow レーン (LOCK `rnb-support-bounce-shadow-forward`, first look N≥41) は登録直後から構造的無発火 = 観測量が到達不能だった
- **バグ 2 発見・同時修理 (confirm marker 欠落)**: 実 signal 出力の end-to-end 検証で第 2 欠陥を発見 — reasons に "✅" marker がゼロで QUALIFIED_TYPES confirm gate (`no_confirm:` block) でも 100% 死んでいた。conf 修理単独ではレーンは開通しない二重欠陥だった
- **他モード全数調査 (「gate の挙動を全対象に等しく適用と仮定するな」)**: MODE_CONFIG 全 signal_fn (compute_daytrade/swing/hourly/scalp + strategies/ 全戦略クラス + weekend_gap_fade + MassiveSignalEnhancer) の confidence を全数走査 — **全て 0-100 int、0-1 は compute_rnb_signal 唯一**。同型の被害者なし
- **修理 (rnb 限定、blast radius 最小)**: confidence を `int(round(min(_score/2.5, 1.0) * 100))` (実レンジ 40-96) へ正規化 + 確定条件 reasons に "✅" 付与。`compute_rnb_signal` は BT/本番共用 (backtest_mode 引数) のため両経路が同時修理 — なお BT harness (`rnb-support-bounce-ablated-bt-2026-09-10.py`) は confidence 非消費で **BT verdict 不変**。gate 側は無変更 (他モードのスケール非影響)
- **テスト** (`tests/test_rnb_confidence_scale.py` 7 本): 実 signal 出力の単位整合 pin / confirm marker pin / end-to-end (実 BUY sig → conf/confirm gate 通過 → is_shadow=1 行 + OANDA 送信ゼロ = shadow_only 維持) / counterfactual A (旧 0-1 値に戻すと conf gate で red) / counterfactual B ("✅" 剥がすと no_confirm で red) / 他モード gate 境界不変 (29 block / 31 pass)。既存 `test_rnb_shadow_only_registration.py` は手書き sig (conf=80, "✅" 入り) だったため両欠陥を素通ししていた — 実出力 e2e が必須という教訓
- **registry**: `rnb-support-bounce-registration-decision` (resolved) + `rnb-support-bounce-shadow-forward` の message に修理注記 (修理前の無発火期間は cadence 分母から除外 — 行ゼロのため estimand/since は不変)。**lane-health cadence checkpoint 併設 (P16 型)**: `rnb-shadow-lane-health-checkpoint-1` (2026-09-24 に closed shadow N<3 で TRIGGERED) / `-2` (2026-10-08 に N<6) — shadow_count_decision 型の deadline 分岐で機械評価、count のみで P-10 (gate×outcome joint 計算禁止) 非抵触
## 2026-09-11 — fix(keeper): emergency_kill 参照 — kill 状態下の実弾 round-trip 継続を封鎖 (rule:R3)

- **ギャップ確定 (P10、反証レビュー指摘 → コード実読 + 本番 API 実測で自己検証)**: `modules/status_volume_keeper.py` (2026-09-01 user 決裁 案 A、本番稼働中 — 09-10 時点 RT 21 回 / $420k を `/api/demo/status` 実測) は emergency/killed 状態を一切参照していなかった。emergency_kill は口座をフラット化するため、keeper の唯一の補償統制 `openTradeCount != 0` skip は**むしろ外れ**、kill 状態下でも 10,000u USD_JPY 実弾往復が継続する構造 — 549250 事故・watchdog 再武装と同型の「防御が名乗る範囲をカバーしない」クラス
- **修理 (防御の追加のみ — keeper のマンデート/ガード値は不変更)**: 新規発注前に `_emergency_kill_blocked()` を追加 — 共有 DB `system_kv.emergency_killed` (demo_trader の kill/resume と同一キー) を **read-only SQLite で読む** (in-memory 不可、プロセス境界教訓)。kill 中は `skip("emergency_kill")` + transition ログ、**読めない場合も fail-closed** (`kill_state_unreadable`、失敗を `{}` に潰さない)。stale SVK 玉回収は kill 中も実行 (close-only = フラット化整合、emergency_kill は trade_map 経由でしか閉じないため SVK 玉の唯一の回収経路)
- **テスト pin** (`tests/test_status_volume_keeper.py` +4 本 + helper に共有 DB 注入): kill=1 で発注が構造的に起きない / **counterfactual 実施済み** (参照除去で kill 下 "RT done" 発生 = テスト red を実地確認 → 復元 green) / kill=0・行なしでマンデート非影響 / read 失敗 fail-closed / kill 中回収 close-only
- **起票**: 監査盲点 2 (実弾ガバナンス — 自走マージ→auto-deploy→実弾 経路のゲート実効性) を [[decisions/live-governance-gap-audit-packet-2026-09-10]] として起票 (実施は次回監査)。防御追記の記録: [[decisions/status-volume-keeper-2026-09-01]] 追記 2026-09-11

## 2026-09-10 — research(scan#4): 第4次外部仮説スキャン前倒し + E23 S2 完遂 + rate-anchor 修復 (rule:R3、WIP 原則)

- **第4次スキャン (期日 09-18 を 8 日前倒し、WIP 原則 — 能動測定ライン 08-19 以降ゼロ)**: [[research/external-hypothesis-scan-round4-2026-09-10]]。**family A/B/C 統合裁定**: family A (MoF 発言ラダー→介入確率) **採用 = 台帳 #27** (explore 枠は敵対的検証→凍結時に消費、registry `family-a-adversarial-freeze-deadline` 09-24。凍結まで発言×介入ラベル joint 計算禁止) / family B (介入イベント→回避/執行) **不採用 park** (公式ラベル四半期ラグ×価格シグネチャ認定禁止で執行 estimand が構造的に組めない + blocks ≤4 + 2026-05 outcome 既公表。再裁定 = #27 verdict + mof-next-episode-reverdict 完了後) / family C 台帳整合のみ (FAIL 不変)。新規候補 E26 (介入情報リリース) C1 棄却 / E27 (CFTC TFF) #16 ban 正面衝突で棄却 / E28 (ML-FX 文献群) C2/C3 棄却 — **新規採用 0、無料×非隣接空間の枯渇を再確認**。**U4 決裁材料** (有償データ feasibility) を §4 に凍結: 購買推奨ゼロ (ロック済み 4 本は金で前倒し不能)、再上程 = U1「継続」+ verdict 到達後に OTC IV 面 → Databento → OIS の優先順
- **E23 (台帳 #25) 残 item 3 完遂**: testable form DRAFT [[decisions/e23-cb-text-explore-prereg-2026-09-10]] — **Apel–Blix Grimaldi 2012 凍結辞書 primary** (`tools/e23_lexicon_apel_grimaldi.py` 新設 — Riksbank WP 261 原本 PDF から語彙逐語転記: 名詞 11 語幹 + hawk/dove 各 4 形容詞語幹 + unemployment 極性反転、Net Index = (H−D)/(H+D+1)、test pin 8 本)。設計 = ΔNH sign-follow × G4 中銀 (1 中銀 1 文書種) × D1+5 pooled bp、explore 2014-2023 / OOS 2024-2026H1、pass-0 census gates、敵対的検証 (自己) 10 条消化。TDW/WCB (CC BY-NC) は E22 §2.1 型事前コミット節で secondary 保留。**イベント×リターン結合統計は未計算 (S2 規律)、LOCK は別 commit、測定は LOCK 後の別タスク**
- **rate-anchor-daily 修復 (設置以来 17/17 全失敗、rule:R3)**: 二重根因 = (1) FRED fredgraph.csv が GH Actions IP から read timeout 恒常ハング (WAF 型) → `tools/rate_anchor_ingest.py` に home.treasury.gov 公式 CSV fallback (同一値の一次ソース — 08-14 行 4 系列一致を実測) + per-source 隔離 (部分失敗でも成功分を蓄積して終端 raise)、(2) `data/cache/` が gitignore 対象で runner git 2.54+ は tracked でも add 拒否 → `git add -f`。**zn-cache-refresh (4/4 全失敗) も根因 (2) 単独で同時修復** — python step は成功していたのに commit が一度も走らない write-only workflow だった。test pin 6 本追加。恒久データ損失ゼロ (23 日停止のみ、初回 green run で自己修復)。**マージ後 dispatch 検証まで「修復完了」と言わない** (scan#4 §1.1 手順)
- registry: `edge-supply-scan-monthly` deadline → 2026-10-18 + 第4次実行記録 / 新規 `family-a-adversarial-freeze-deadline` (09-24)。台帳: #25 更新 + #27 新設 + scan#4 triage 節 (family B/E26-E28)
- **🔒 E23 explore pre-reg LOCK (別 commit、規約)**: 辞書 sha256 = f49586ca... pin + explore 枠 1/3 消費 + registry `e23-explore-verdict-deadline` (09-20) 併設。queue ticket 20260818-e23 を done へ移送 + SLA waiver 削除 (方針どおり scan#4 と同時処理、期日 09-18 を前倒し履行)。測定 (pass-0 census → two-pass) は LOCK 後の別タスク
## 2026-09-10 — fix(e1): ingest 認証失敗インシデント — backoff + fail-loud + 復旧手順 (rule:R3)

- **P1 進行中インシデント**: Myfxbook 認証失敗 (`Wrong email/password.`) で E1 positioning ingest が 2026-09-10T~07:18Z から停止。最終 verified 06:58:44Z、13 キー全 stale (14:44Z 実測 7.76h)、logins_total=0。§2.5 coverage budget 残 **33.2〜35.2h**、停止継続時の breach 予測 **09-13T23:57Z〜09-14T01:57Z** → 6 primary 全ペア機械除外 → family gate 4 週 postpone (first look 10-15 → ~11-12 = M1 経路 ~4 週遅延)。全会計と復旧手順: [[e1-ingest-outage-2026-09-10]]
- **lockout 防止 backoff** (`modules/positioning_ingest.py` / `modules/myfxbook_client.py`): 認証失敗 (`is_auth_failure` — session 失効/transport と分類分離、marker SSOT は myfxbook_client) で login リトライを exponential backoff 1800s×2^n・**上限 6h**。連続 4 回で長期 pause を明示ログ宣言 (以後 6h 毎 1 回のみ再試行)。**認証成功で即通常化**。backoff skip 中も heartbeat (`last_cycle_at`) は書き verified:* は書かない — 鮮度検知 (registry / watcher) を殺さない。状態は status API `myfxbook.auth_*` に全露出。live 取引経路 非接触 (demo_trader/oanda_bridge/strategies からの参照ゼロ、全数 grep — positioning は E1 データ収集専用)
- **fail-loud 化** (`scripts/anomaly_watcher.py`): 7h+ 無言だった経路を解剖 — 既存 10 検知器は `/api/positioning/status` を見ておらず、registry `e1-positioning-ingest-freshness` は daily cron (00:20Z) のみ、Render ログ [positioning] は読み手ゼロ。WATCHED_PATHS に追加し `positioning_auth_failed` (Discord 毎時) / `positioning_stale` (6h バケット) / `positioning_freshness_missing` (記録のみ) を新設 — 検知遅延 ~17h → **~15 分**
- **テスト**: `tests/test_positioning_ingest.py` +8 本 (**counterfactual pin**: backoff 配線 kill で `test_auth_failure_backoff_counterfactual` が fail / exponential+cap / 長期 pause / 成功即リセット / 非 auth 失敗は backoff しない / no-secrets)、`tests/test_anomaly_watcher_detectors.py` +10 本 (本番実測形状で発火 / estimand 分離 / 読み手 pin = main 配線・通知バケット・event line)
- registry `e1-positioning-ingest-freshness`: note に incident 台帳追記 + reachability に watcher 先行検知経路を追記
## 2026-09-10 — fix(watch): trigger 評価の全面クラッシュ耐性検証 + 評価空白 09-06〜09-10 の影響監査 (rule:R3)

- **検証 (最重要)**: 反証レビュー主張「registry 欠損で prereg_trigger_watch 全面クラッシュ、日次評価 09-06 から死亡」は**PR #236 で修復済み**と実測確定 — origin/main で exit 0 / active 40 エントリ全評価 / EVAL_ERROR 0 件。隔離ラッパ・EVAL_ERROR 別箱・registry lint (check.py 第 9 チェック)・counterfactual テスト (欠落 fixture / fault injection / 型網羅 pin) の全てが導入済みのため重複修理はしない
- **評価空白の影響監査**: [[trigger-watch-gap-audit-2026-09-10|raw/audits/trigger-watch-gap-audit-2026-09-10]] — Tier-A cron 4 run (09-07〜09-10 00:20 UTC) が影響。期日超過・N 到達の見逃しは**ゼロ**。TRIGGERED 2 件: t5-jpy-cap-restore-price (既知・空白起因でない) と **e1-positioning-ingest-freshness (新規・進行中 — 本番 ingest 2026-09-10T06:58Z 停止、全 13 ペア stale 7.9h+、E1 残 coverage budget ~41h への現在進行形の消費)**。E1 復旧は別タスクで追跡。修復後初の cron 配信は 09-11 00:20 UTC のため本監査が修復後最初の読み手
- **残欠陥の同型修理**: `quant_gate_status.run_quant_readiness()` — `r.stdout or r.stderr` が returncode を見ず、非ゼロ exit + 部分 stdout で stderr traceback を黙殺 / stdout 空で素の traceback が本文として流れる (run_prereg_trigger_watch の 2026-09-08 欠陥と同型)。fail-loud 化 (banner + stderr 末尾 6 行 + 部分本文保持、フェンス内描画のため入れ子フェンス回避) + counterfactual テスト 3 本 (`tests/test_m1_clean_live_monitor.py`)
## 2026-09-10 — fix(ci): zn-cache-refresh の git add -f 修正 + ZN cache 鮮度 pin — round-4 発火条件の恒久死亡を解消 (rule:R3)

- **実測根因** (gh run log 4/4、run 34124847021 ほか): `zn-cache-refresh.yml` は fetch 成功 (rows 14225→14537、右端 2026-09-04 まで取得) の直後、commit 段の素の `git add data/cache/yield/ZN_F_1h.parquet` が `.gitignore` の `data/cache/` に拒否され exit 1 — **2026-08-17〜09-07 の全 run が取得データを捨てて死亡**。ファイルは track 済みだが git >= 2.5x は ignored dir 配下への素の add を advice + exit 1 で拒否する (ローカル 2.50.1 で再現確認)。放置すると registry `ws3-round4-eur-divergence-conditional` の発火条件 (cache 被覆 2026-11-15+) が永遠に不成立 = E1 FAIL 時の代替供給 1 本が無期限死亡
- **修理**: `git add -f data/cache/yield/ZN_F_1h.parquet` へ変更 (workflow 内に根因コメント併記)
- **鮮度 pin (読み手の新設)** — 4 回の赤 run を誰も読んでいなかった (「収集済み ≠ 監視済み」の再演): `scripts/check_zn_cache_freshness.py` 新設 — cache 右端が `ZN_CACHE_MAX_AGE_DAYS = 8` 日 (SSOT: `modules/freshness_policy.py`、較正: 正常時 ≈5.8 日 / refresh 1 回失敗 ≈12.8 日の中間) を超えたら Discord 通知 + exit 1。欠損/空/読取り不能も fail 側に倒す (「無ければ skip」禁止)。読み手 = `weekly-audit.yml` の独立 job `zn-cache-freshness` (週次日曜 02:00 UTC)
- **counterfactual pin**: `tests/test_zn_cache_freshness_pin.py` 11 本 — `-f` を外す / weekly-audit の配線を消す の双方で red になることを実地確認 (3 fail)、復元で green。閾値較正域 (6〜12 日) も pin
- **同一ファイル semgrep gate 対応**: weekly-audit.yml の actions を full SHA pin 化 + `github.event.inputs` の run 直接展開を env 経由へ (script injection 防止)
- **マージ後検証 (push ≠ 完了)**: `gh workflow run zn-cache-refresh.yml` → run green → `git show origin/main:data/cache/yield/ZN_F_1h.parquet` の右端が前進したことを実測 (手順は PR 本文)

## 2026-09-10 — feat(wg): 執行契約 (B) エントリー繰り下げ — halt 決定論 fill 0% の修理 (rule:R1 user 承認 2026-09-10)

- **決裁執行**: [[weekend-gap-execution-contract-r1-packet-2026-09-10]] §4 AMENDMENT (user「進めて」2026-09-10)。唯一の OOS 確定 PASS セル weekend_gap_fade の live fill 0/3 の機構 = エンジン発火 21:01 UTC < OANDA 実開場 21:04-21:05 (48/48 実測) → 旧契約 (即時 FOK 1 回) は MARKET_HALTED cancel が決定論的。**次イベント 2026-09-13 (日) 21:00 UTC が改定後初の検証点**
- **§4.1 entry 繰り下げ**: `_weekend_gap_tick` (scoped runner) に前置条件 — live 送信は OANDA 実開場確認 (pricing `tradeable`、quote age <10s、poll ≤60s = tick 周期) 後の**最初の評価 tick**へ。HOLD 中は latch を立てず検出継続。新規 read-only `modules/data.fetch_oanda_pricing_state` + 純関数 `weekend_gap_entry_send_decision` (unit-testable)
- **§4.2/§4.3 放棄境界 (凍結値)**: 初バー ts +15 分超で halt 継続 → latch=`ABANDONED_HALT` / fade 方向 adverse drift (基準 = Sunday open、§5.3 実測と同一定義) > +8.0p → latch=`ABANDONED_DRIFT`。いずれも shadow row は記録 (分母保存)
- **§4.4 halt-race 限定再送**: bridge `open_trade(halt_race_resend=True)` (wg のみ配線) — tradeable 確認後の FOK が `MARKET_HALTED` cancel (cancel tx を response 内で確認済み) で返った場合のみ 30s 後 1 回だけ FOK 再送 (最大計 2 送信)。他 reason / transport error は従来どおり再送禁止 (`max_attempts=1` 不変)
- **§4.5 G1 基準保存**: fill slippage 基準 = 「実際に fill した送信 attempt の直前 quote」— 再送時は再送直前の同サイド quote に基準を差し替え (初回 quote 固定だと繰下げドリフト mean +3.15p が G1 に混入し N=6 で恒久誤停止 = packet §3 の案 A 棄却理由)。通常 fill の基準は従来どおり送信時 quote (非回帰 pin あり)
- **§4.6 観測強化**: 評価ごと `[WEEKEND_GAP][EXEC_B]` ログ (tradeable/quote_age/drift/send_mid) + demo row reasons `[WG_EXEC_B]` 永続化。cap 10.0p 判定は実開場後の実 quote に構造的に移行 (indicative 判定消滅)。`_tick_entry` backstop: tradeable 未確認 sig の live 送信は `weekend_gap_tradeable_unconfirmed` で block (row/latch なし — 冗長エンジン経路の開場前送信も封鎖)
- **不変更 (絶対)**: シグナル定義・qualify 閾値・cap 10.0p・1000u・4h exit・disaster SL 150p・**G1 (+2.0p)/G2 (−60p)/G3 の全定義と閾値**。BT 側変更なし (live 執行層のみの修理 — estimand コスト mean +3.15p は packet §5.3 織り込み済み、実効 EV ≈ +4.75p/event)
- registry (同一コミット): `weekend-gap-live-g1-slippage` / `weekend-gap-live-g2-cumloss` / `project-falsification-f2-wg-live-conversion` に AMENDMENT 発効 + live N カウント起点を追記。新規 `weekend-gap-execution-amendment-g0prime` (期日 09-28) — 改定後最初の 2 qualifying イベントの G0' 検証手順 (EXEC_B ログ / 送信時刻 = 実開場 +0〜2 分 / fill or 正当放棄の分類 / slippage 突合 / 再送 ≤2)。**2 連続 fill 不成立 → 執行モダリティ再審 (R1 再起案)**
- tests: `tests/test_weekend_gap_execution_contract_b.py` **26 本** 新設 — 境界 (tradeable 直後 / +15 分 strictly-after / drift strictly >+8.0p / 符号規約) + **counterfactual kill pin** (繰り下げ配線 kill で 5 tests fail、basis swap kill で 1 test fail を実証) + 再送上限 / fail-closed。既存 29 本は不変 green。`test_preserve_types_tick_entry.py` の wg fixture に runner marker (`_wg_exec_send_ok`) を付与 (backstop 準拠、estimand 不変)
- KB 同一コミット: 戦略カード §執行仕様 AMENDMENT 註記 + イベントログ / packet Status → APPROVED+実装済み / stage-2 pre-reg §2.2 に置換ポインタ (原文保存)
## 2026-09-10 — feat(rnb): rnb_support_bounce stage-1 構造的 shadow-only 登録 + R2 auto-demote gate + pre-reg LOCK (rule:R1 user 承認 2026-09-10)

- **158 日 dead mode の解消** — `rnb_support_bounce` を QUALIFIED_TYPES に登録 + MODE_CONFIG `rnb_usdjpy` に `shadow_only: True` (daytrade_audjpy 前例の 3 点 block: 送信ガード最終段 / resend gate / write-path で **OANDA 発注ゼロを構造保証**)。`_UNIVERSAL_SENTINEL` には意図的に非追加 (sentinel = minlot live 経路 — stage-1 では開けない)。決裁: [[rnb-support-bounce-r1-packet-2026-09-10]] §7 (D1 GO / D2 承認 / D3 GO、user「進めて」2026-09-10)
- **登録は昇格ではない**: 365d BE/Trail-ablated BT は N=126 WR55.6% net EV **+0.04p NS** (p=0.082、2026-03 単月依存)、730d **−2.20p**、Wilson_lo 46.8% < BEV 49.0% = 昇格 gate 不成立 — 正当化は「~3.0 setups/週の無料 shadow N 源」(観測レーンの開通) のみ。BT: `raw/bt-results/rnb-support-bounce-ablated-bt-2026-09-10.md`
- **🔒 pre-reg LOCK `rnb-support-bounce-shadow-forward` 正式化** (packet §9.1): estimand = 2026-09-10 以降 forward shadow rows (USD_JPY×BUY, closed, dedup_violation=0, 厳格 shadow) の WR / net EV (friction 2.14p)。first look = **shadow N≥41 or 2027-01-15 の早い方** (それまで gate×outcome joint 計算禁止 P-10 / 中間再計算禁止)。採用境界 = Wilson_lo>49.0% ∧ net EV>0 (stage-2 R1 起案)、棄却境界 = Wilson_hi<42.9% (gross BEV)、どちらでもなければ N≥82 で 1 回限り再判定。registry: `rnb-support-bounce-shadow-forward` (shadow_count_decision, prereg_trigger_watch 日次評価) 新設 + `rnb-support-bounce-registration-decision` resolve (期日 10-06 前倒し)
- **R2 auto-demote gate 併設** (「無条件 emit は EV<0 で汚染源化」教訓): `tools/rnb_shadow_demote_gate.py` 新設 — shadow closed N≥30 (dedup_violation=0) ∧ Wilson_hi<42.9% で exit 1 = `auto_start=False` 化の R2 起案 (read-only、執行は別 PR)。読み手 = `r2-alert-scheduled.yml` (6h 毎) に配線し、配線の存在自体を `tests/test_rnb_shadow_demote_gate.py` が pin (write-only 検知器の再発防止)。P-10 遵守: 採用側 estimand (Wilson_lo / net EV) は first look まで計算・出力しない
- **テスト**: `tests/test_rnb_shadow_only_registration.py` 新設 (QUALIFIED 化 / shadow_only / sentinel 非追加 pin + worst-case OANDA ゼロ + 帰属証明 control + resend/write-path)、`tests/test_rnb_shadow_demote_gate.py` 新設 (counterfactual 発火/非発火/母集団フィルタ 12 本)、既存 drift pin 3 ファイル更新 (`test_rnb_block_reason_estimand.py` KNOWN_REGISTRATION_DRIFT=空 + BUY→shadow 行 pin / `test_daytrade_audjpy_shadow_only_mode.py` shadow_only 集合 = {daytrade_audjpy, rnb_usdjpy} / `test_preserve_types_tick_entry.py` rnb expect=row)
- KB: strategy card [[rnb-support-bounce]] 新設 (BT 実測を正直に記載) + [[rnb-usdjpy]] mode カード更新 + sync_kb_index / tier_integrity_check --write
## 2026-09-10 — fix(w4): bb_squeeze v2 の live 呼び出し規約 3 層配線落ちを修復 — 127 日沈黙の解消 (rule:R3)

- **経緯**: registry `roster-e2-silent-promoted-cells` の判別 ([[e2-silent-cells-triage-2026-09-10]]、PR #235) で bb_squeeze_breakout×EUR_USD (BUY/SELL) が「配線落ち」と確定 (意図的無効の決裁は不在)。commit 942e3800 (2026-05-06 w4 v2 化) 以降 127 日間、_PAIR_PROMOTED 現役掲載のまま LIVE/shadow 行ゼロ。user「進めて」(2026-09-10) で R3 修復を執行
- **層① live 恒久 None を修復** (`strategies/scalp/squeeze.py`): `_evaluate_v2` の hard-guard `not backtest_mode and bar_time is None → return None` は、live 呼び出し規約 (demo_trader._tick → `compute_fn(df, tf, sr, symbol)` = bar_time 常に None) で評価器を構造的に殺していた。同 wave の xs_momentum idiom (`bar_time or df.index[-1]`) に置換。評価本体は closed signal bar (`iloc[-2]`/`index[-2]`) のみ参照のため **BT (backtest_mode=True, 旧 guard 非適用) との評価 parity は不変** — 同一 df で live 規約と BT 規約の出力一致をテストで pin
- **層② ✅ 欠落を修復**: v2 reasons に ✅ が 1 つもなく、発火しても QUALIFIED gate `no_confirm:bb_squeeze_breakout` (demo_trader.py) で live/shadow とも死んでいた。BUY/SELL の第 1 reason に ✅ 付与。BT 側 `SCALP_BT_QUALIFIED` gate (app.py run_scalp_backtest) も同一述語 `"✅" in r` のため **BT/本番が同時に同じ向きへ直る** (parity 維持)
- **層③ loser-shadow 不達は層①で到達回復**: `split_shadow_always` の 2-lever 配線 (SQUEEZE_REDESIGN_V2 + _SHADOW_PROMOTE) は既存 — 評価器 None で候補が永遠に来なかっただけ。live 規約で生成した候補が score 敗北時に shadow promote へ届くことを end-to-end で pin
- 🛑 **live 送信挙動は変えない — `SQUEEZE_V2_LIVE_HOLD` 新設** (`modules/demo_trader.py`、default=1): 修復単体だと winner 経路が _PAIR_PROMOTED×EUR_USD (2026-05-07 volume emergency 登録、根拠 shadow N=14 EV=+0.01 のみ) 経由で「一度も行使されたことのない live OANDA 送信」を開く — _PAIR_PROMOTED は spread_gate / spread_sl_gate / Phase0 SHADOW gate 免除で、GRAIL/C1/EDGE_CELLS/PRIME/kalman いずれにも bb_squeeze は不在のため **hold が唯一の deciding gate** (counterfactual テストで hold=0 → bridge.open_trade 発生を実測)。v2 wave の設計意図は shadow 実測 (verdict INSUFFICIENT_BT_EVIDENCE → RECOMMEND_SHADOW) であり live 化 R1 は未了 → v2 有効時は winner も shadow 固定。解除は fresh shadow N≥30 の R1 決裁後に env "0"。SQUEEZE_REDESIGN_V2 無効 (v1) 時は hold 不適用 = 挙動変更 scope を v2 に限定
- **テスト**: `tests/test_squeeze_shadow_redesign_v2.py` 旧 pin `test_v2_live_without_bar_time_is_blocked` (壊れた挙動の pin) を修復 pin に反転 + parity/✅/loser-shadow の 3 本追加 (計 10 本)、`tests/test_bb_squeeze_v2_live_hold.py` 新設 4 本 (real _tick_entry 駆動、preserve-types パターン)。**counterfactual 5/5 実地確認** (squeeze.py revert → 4 fail / hold revert → 1 fail、既存 pin は green 維持)。全体 3152 passed
- **BT 検証について (rule:R3 例外の明示)**: 本修復は数学/コード導出による構造バグ修正で 365d BT は skip (Rule 3)。挙動追加は shadow 行の発生のみで実弾リスクゼロ (hold で構造保証)。EUR_USD の エッジ有無は修復後の fresh shadow N で判定する — 旧 shadow N=14 EV=+0.01 / 5d shadow EV=-3.05 は v1 評価器由来で v2 の根拠に引用不可
- registry `roster-e2-silent-promoted-cells`: bb_squeeze 2 セル = 修復実施を追記 (ema200×USD_JPY×SELL / SRM×GBP_USD×BUY は PR #235 で E1 = シグナル未発生に再分類済み)。読み手 `tools/live_roster_attrition.py` の E2_SILENT 解消は修復デプロイ後の行発生で確認
- 決裁: [[e2-silent-cells-triage-2026-09-10]] §2.4 R3 修復案 / 戦略カード: [[bb-squeeze-breakout]]

## 2026-09-10 — fix(process): PR #227 救済 — レビューゲート二重実装の統合とインシデント記録の保全 (rule:R3)

- **経緯**: メタ監査 R2 (マージゲート) を 2 セッションが独立実装し、PR #231 版が main へ先着。座礁した PR #227 (18 巡レビュー済み・CONFLICTING) から**固有価値のみ**を origin/main 起点の救済ブランチへ移植した。ゲート実装自体は #231 版 (`tools/pr_review_gate.py`) を正とし、#227 版 (GraphQL threads / P0 fail-closed / ページング / HEAD_UNREVIEWED) は**移植見送り** — 記録は決裁文書に原文保存し採用可否は別途判断
- **インシデント記録の保全**: [[pr-review-gate-2026-09-08]] 新設 — 「独立レビューは 5.5 ヶ月 write-only」の定量確認 (finding を持つ 35 PR の解決済みスレッド 0 件 / review→merge 中央値 2.8 分) と、**未読 P1 が prereg 監視器を 51 エントリ 2 日間止めていた**実害の一次記録。冒頭に救済経緯を追記済み。[[process-meta-audit-2026-09-07]] R2 行へ執行済みマークを追記
- 🛑 **main の registry は依然壊れたままだった** — `roster-e2-silent-promoted-cells` は `artifact_presence` を名乗りながら `requirements` を欠き、`evaluate_trigger` が KeyError → **本日時点の main でも daily trigger watch は全滅停止し続けていた** (PR #226 で混入、2026-09-06)。`conditional_info` へ型修復 (estimand は成果物着地でなく期日までの判別作業)
- **監視器の恒久堅牢化** (`tools/prereg_trigger_watch.py`、#227 の 18 巡分を一括移植): (a) `evaluate_trigger` 隔離ラッパ — 壊れたエントリは自分だけ `EVAL_ERROR` を名乗り残りは通常評価、(b) `STATE_ERROR` を `DATA_UNAVAILABLE` と別箱化 + `main()` exit 2、(c) `load_registry_raw` — root 台帳の欠落/綴り違い/空を「空の台帳」に畳まず RuntimeError、(d) **registry authoring lint** (`lint_schema` + `lint_registry`) — type 別必須/任意フィールドの reject-by-default、値の型/下限/日付正準形/enum/形 (instrument `CCY_CCY`、endpoint 絶対パス)、`mode` は `MODE_CONFIG` から AST 導出 (手写し禁止)、コレクション要素と入れ子 spec まで 3 層検査。`shadow_count_info` の instrument/direction 未配線 (allowlist にあるのに評価器へ渡らず全ペア計上) も修復
- **`scripts/check.py` に第 9 チェック追加**: `check_prereg_registry_schema()` — registry lint を CI で強制、**検査不能は skip でなく ERROR** (write-only guard の再発防止)
- **`tools/quant_gate_status.py`**: (a) `run_prereg_trigger_watch()` の returncode 検査 — 監視器の故障を「異常なし」と区別 (exit 2 では stdout を捨てない — 壊れた 1 件が他の TRIGGERED を隠さない)、(b) 監視器故障 banner (`WATCH_ALERT_MARK`) と **TRIGGERED 節を M1 より前方へ** — Discord 第 1 メッセージの 1900 字枠内に「要行動」が必ず入る (行 220 字 + 節 700 字の総量予算、溢れ件数は明示告知)。main 側 `_discord_chunks` (4 通分割) と相補
- **registry 追加**: `roster-attrition-88pct-estimand-audit` (resolved — PR #230 が 12 日前倒しで執行済み、旧 D 解釈は棄却) / `registry-lint-declaration-generation` (期日 2026-12-31 — lint 手写しの恒久解 = 評価器側から検査宣言を生成、estimand 宣言表の適用先)
- テスト: `tests/test_prereg_trigger_watch.py` +846 行 (lint 全 family + 隔離 + counterfactual)、`tests/test_m1_clean_live_monitor.py` +11 本 (returncode / banner 前方 / TRIGGERED 総量予算)。**`tests/test_pr_review_gate.py` は #231 実装のインターフェース (`evaluate(pr)->(code,msg)`、exit 0/2/3/4) に適合させて新規作成** — #227 版テスト (GraphQL 前提 10+ 本) の盲目移植はせず、#231 版が提供する性質のみ pin
- **見送り (理由付き)**: #227 版 `tools/pr_review_gate.py` 実装 (main 版と二重実装になる)、CLAUDE.md のゲート節書き換え (#231 版が既に存在 — 「push 後は `@codex review` が必要」の運用注意 1 行のみ追加)、`hunt_events/2026-09-10.jsonl` (#230 と add/add 衝突を再生産するため — データは #227 ブランチに残存)、session log 2 本 (指定救済リスト外・hot file、価値の本体は決裁文書へ保全済み)
- 決裁: [[pr-review-gate-2026-09-08]] / 親: [[process-meta-audit-2026-09-07]] §4.2 R2
## 2026-09-10 — audit(estimand): D クラス「本来出てはいけなかった発火」を棄却 — 15 セル中 1 セルだった (rule:R3)

- 🛑 **旧 `D_NEVER_PROMOTED` の解釈は反証された** — registry `roster-attrition-88pct-estimand-audit` (期日 09-22) の執行。出所は **PR #226 の Codex P1 finding #2** (レビュー到着直後にマージされ未読だった 2 件の 1 件)。指摘どおり判定根拠は「**現在**の昇格集合に不在」だけで、当時の昇格状態を何も測っていなかった
- **実測: D 15 セルの clean LIVE 約定 28 件は全て 2026-04-02〜04-14T02:54Z に閉じている** — Phase-0 三層化 (`_SHADOW_MODE` + `_ELITE_LIVE` + Phase0 tier gate、commit `293165ef` **2026-04-14T08:16:58Z**) の**導入前**。gate 前の `_is_promoted()` は既定 `return True` = **OANDA 送信 allow-by-default** で、2026-04-03 の `8a42d776` は commit message 自体が "temp: disable OANDA strategy promotion filter — send all entries to OANDA" だった ⇒ 昇格集合に無いセルの LIVE 約定は**異常ではなく設計状態**
- **約定 1 件ごとの verdict: 正当 26 / 違反 2** (セル単位 14 / 1)。違反は `dual_sr_bounce × USD_JPY × BUY` の 2 約定 (04-13T13:01Z / 16:01Z、当時 `_FORCE_DEMOTED` 在籍) のみ。⚠️ limitation = `get_strategy_mode()` の手動 override はランタイム DB 状態で再構成不能 → ILLEGIT は条件付き、**LEGIT 側は override の有無に不感なので結論の向きは非対称に安全**
- **クラス別 gate 前後分解で欠陥が D に局在することを確認** — B は 48/83 セルが gate 後も発火 (列挙済み降格機構で実際に止まっている = 帰属妥当)、D は **15/15 が gate 前のみ**で完全分離。B/C/E は「**今**なにが止めているか」= 現在形の問いなので現在の集合を読むのが正しい estimand、**D だけが過去形の主張を運んでいた**
- **引用可否**: 「帰属済み 88.7%」は**引用可・数値不変** (帰属先の機構が変わるだけ = 列挙外だった第 5 の停止機構 = tier 設計変更) / 「停止済み 83 セル N=609 −469.8p」も引用可 / **「D は本来出てはいけなかった発火」は引用禁止** / 「M3 の分子外」は根拠が政策判断へ変わる (経済的には N=28 −26.2p で無視可能、~14 ヶ月 ETA と [[friction-adjusted-ev-map-2026-07-07]] の結論は不変)
- **分類器が見ていない当時の LIVE 資格集合を列挙** — `_ELITE_LIVE` (現 HEAD に**消滅**) / `_GRAIL_CANDIDATES` / `_C1_PROMOTE_CANDIDATES` / PRIME tier A/B (`modules/prime_gate.py`) / `_SCALP_SENTINEL`。`load_stop_sets()` は `_PAIR_PROMOTED` と `_UNIVERSAL_SENTINEL` の 2 本しか読んでいない
- **是正**: `D_NEVER_PROMOTED` → **`D_NOT_LIVE_ELIGIBLE_NOW`** (クラス名が過去形の主張を運ばないように / 旧称復活は pin で防止) + subclass `D1_PRE_TIER_GATE` / `D2_POST_TIER_GATE` 新設 + docstring に棄却と導線。読み手 `tools/roster_d_class_estimand_audit.py` 新設 (約定 1 件ごとに当時デプロイされていた commit を `origin/main` first-parent から特定し `_FORCE_DEMOTED`/`_PAIR_DEMOTED` を AST で読む)
- 🛑 **監査ツールの実装中に自分で同型の欠陥を作りかけた** — `demote_sets_at` が「読めたが集合が無い」を `None` (= 読めなかった) に折り畳み、5 約定が UNRESOLVED に化けていた (2026-08-30 の `fetch_json` blind と同型)。**合成 cache を注入するテストは関数を迂回して検出できない → 契約は関数で pin する**
- テスト: `tests/test_roster_d_class_estimand_audit.py` **11 本** 新設 (定数一致 / gate commit の実在と親 commit に gate が無いこと / 逆方向 (gate 前でも降格中なら違反) / 折り畳み禁止の契約 pin / D subclass 分岐 / 旧称復活防止)。**counterfactual 3/3** が所望のテストのみを落とすことを確認 (折り畳み復活 / 定数不一致 / 降格集合を読まない)
- 教訓: **現在形の集合で過去形の主張をするな。クラス名は estimand を運ぶ** — `D_NEVER_PROMOTED` という名前自体が、根拠より強い主張を毎回の readout で再生産していた
- 🛑 **同日 PR #230 レビューで自分の監査に P1 2 件 + P2 1 件**。(a) **降格集合の不在から昇格方針を推論していた** — 04-02 の発火は `_is_promoted` が**そもそも存在しない**時期 (OANDA ミラーが無条件) で、根拠が別物だった。`promotion_policy_at()` を新設し `_is_promoted()` の既定を AST 分類 (`NO_GATE`/`ALL_SEND`/`ALLOW_BY_DEFAULT`/`DENY_BY_DEFAULT`/`UNKNOWN`、`UNKNOWN` は許可側でなく UNRESOLVED へ)。実測方針内訳 = ALLOW_BY_DEFAULT 23 / ALL_SEND 3 / NO_GATE 2。(b) **「LEGIT 側は override に不感」は誤り** — `_is_promoted()` は既定 return より**手前**で `get_strategy_mode()=="off"` と `_promoted_types` の `status=="demoted"` を見るので**ブロック方向**の再構成不能な自由度がある。verdict 名に条件性を埋め (`PERMITTED_STATIC_RUNTIME_UNKNOWN`)、無条件に確定するのは `PERMITTED_NO_GATE` / `PERMITTED_ALL_SEND` の 2 つだけと明示。(c) **D2 を `attributed_share` の分子に数えていた** — `--anchor` を gate 後に動かすと「定義上要説明」の D2 が share を黙って膨らませる → D1 のみ計上 (既定 anchor では D=15/15 が D1 なので **88.7% は不変**)
- **改訂後の verdict**: 無条件に許可と確定 **5 約定** / 条件付き **21** / 静的方針に反する **2** (セル単位 4 / 11 / 1)。旧解釈の棄却は変わらない (根拠そのものが誤りだったため) が、初版の「26/28 は正当」は言い過ぎだった
- 教訓 (追加): **「不在」から方針を推論するな** — 降格集合が無いことは「その 2 定数が無かった」しか示さない (2026-08-31 の「組み立てた URL の 404 は不在の証拠ではない」と同型)。**限界は verdict 名に書け** — 「LEGIT」は無条件の含意を運ぶので、引用する側が限界を落とせる
- テスト: 11 → **16 本** (方針 3 形の判別 / 条件性の pin / deny-by-default を許可と呼ばない / UNKNOWN が UNRESOLVED へ流れる / D2 除外)。counterfactual **3/3** (方針を不在から推論 / 条件付きを無条件扱い / D2 を帰属済みに数える)
- **PR #230 レビュー 2 巡目 (P2 2 件)**: (a) **`demote_sets_at` が個別代入の解析失敗を `continue` で飛ばしていた** — 部分的にしか読めていない降格集合を「完全に読めた」として扱い、在籍していたセルを PERMITTED 側へ落とす。1 つでも読めなければ `None` (= 再構成不能) を返す **fail closed** へ。(b) 🛑 **撤回した「26/28 約定は正当」が `live_roster_attrition.py` の docstring に残っていた** — 引用可否を KB に書いても、**ツールの docstring は readout の一部**なので毎回の readout で再生産される。撤回を明記した記述に差し替え、**「撤回済み主張が readout に残っていないこと」を CI で pin** (`26/28` に触れるなら「撤回」の語を必須にする性質 pin)。教訓: **主張を撤回したら、その主張を運んでいる全ての readout 面 (docstring / markdown / MEMORY) を同じコミットで洗う**
- テスト: 16 → **18 本**。counterfactual 2/2
- **CI 修理 (座礁救済、3 巡目)**: `test` job の checkout が shallow (fetch-depth 既定 1) のため、実 git 履歴 (gate commit `293165ef` / 全送信期 `8a42d776` / `origin/main` first-parent) を読む pin テスト群が **CI でのみ** fail していた (ローカル full clone は 38/38 pass)。`ci.yml` test job に `fetch-depth: 0` を追加 (hip1-holdout-guard job は既に 0 で前例あり)。assertion message に「定数の誤り vs shallow clone」の区別導線を追記 — 「歴史が読めない」を「定数が誤り」に折り畳まない
- 分析: [[roster-d-class-estimand-audit-2026-09-10]] / 改定対象: [[live-roster-attrition-2026-09-06]] §2.1

## 2026-09-10 — docs(packet): rnb R1 パケット起案 + E2_SILENT 4 セル判別 (rule:R3)

- **rnb_support_bounce 登録 R1 パケット起案** ([[rnb-support-bounce-r1-packet-2026-09-10]]、meta 監査 R4.2-R1(a) の前倒し) — **365d BE/Trail-ablated BT を初実施: N=126 WR 55.6% net EV +0.04p (≈0、p=0.082 NS)、730d は −2.20p、2026-03 単月 +160.9p 依存 ⇒ live 昇格根拠なし**。提案は stage-1 構造的 shadow-only 登録 (`shadow_only: True`、daytrade_audjpy 前例) に限定 + R2 auto demote gate 併設 + pre-reg LOCK 草案 (first look N≥41 or 2027-01-15)。user 決裁欄 D1-D3。BT: `raw/bt-results/rnb-support-bounce-ablated-bt-2026-09-10.md`
- **live 実測頻度の中間読みは無情報と判明** — 現 counter 窓 (09-09 23:28 再デプロイ以降 736 tick) は active hours (UTC 7-20) を 1 分も含まず `unknown_type:rnb_support_bounce`=0 は設計整合。**09-05 以降に active hours を含んだ counter 窓 2 本 (計 ~39h) は snapshot されずに再起動で消滅** — 期日 10-06 判定には UTC 19:5x の block-counts pull 手順 (packet §2.3) が必要
- 🛑 **E2_SILENT 4 セル判別 ([[e2-silent-cells-triage-2026-09-10]]): registry 前提「05-06 以降 4 セル行ゼロ」は本番 DB 実測で 2/4 が偽** — ema200×USD_JPY×SELL は 19 行 (〜08-05)、SRM×GBP_USD は 51 行 (〜08-31) が実在。attrition tool の 30d 窓を「05-06 以降ゼロ」と読み替えた**窓天井の再発** (クラス名が estimand を運んだ)
- 🛑 **真の沈黙は bb_squeeze_breakout×EUR_USD の 2 セルのみ = 配線落ち 3 層** (commit `942e3800` 2026-05-06、最終行と rollout が分単位で一致): (1) v2 評価器が live 呼び出し規約 (bar_time=None) で**構造的 None** — 「shadow で実測する」目的の v2 が実測経路で恒久沈黙、(2) v2 reasons に ✅ 欠落 → 仮に発火しても `no_confirm` gate で死ぬ、(3) loser-shadow 経路は評価器 None で不達。「意図的無効」の決裁は存在せず _PAIR_PROMOTED 現役掲載のまま 127 日
- ema200/SRM の頻度低下は **PR #168 (08-09 ctx.hour_utc 凍結修復) で session gate が 123 日ぶりに実効化した帰結** (意図された設計) + SELL は USD_JPY 上昇 regime で条件不成立 — E1 (supply present) へ再分類を提案
- 観測基盤の欠陥 2 件を起票提案: `/api/demo/live-enable-flags` が REDESIGN_V2 系 ~40 lever を返さず registry の判別手順が実行不能だった / attrition tool に全期間 `last_row_at` が無く「いつから沈黙か」に答えられない
- registry 変更提案 (執行せず): `rnb-support-bounce-registration-decision` へ packet 参照追記 / `roster-e2-silent-promoted-cells` の E2 実体を bb_squeeze 2 セルへ訂正

## 2026-09-10 — feat(kpi): M1 強定義 readout + M3 二定義分離 (rule:R3)

- 🛑 **meta-audit R4(a)/(b) 修復 (user 承認 2026-09-10)** — M1 弱定義 (30d rolling 符号) は新規約定ゼロの機械的反転で「達成」表示になる縮退 KPI で、承認済み強定義が 59 日未実装だった。`tools/m1_clean_live_monitor.py` に `--strong` を追加し、**弱定義 readout は無変更のまま** M1_STRONG + M3a/M3b を追記
- **M1_STRONG は文書 2 系統の定義を両方実装** — セル定義 (rederivation §4 系: clean live 累積 N≥30 ∧ EV≥+1.0p/t ∧ Wilson95下限>0、達成=該当セル≥1) / book 定義 (m1-kpi §8 案: sum>0 ∧ bootstrap P(sum≤0)<0.05) / FULL (両方)。**文書間矛盾 4 件** (資格母集団 / EV 閾値 +1.0 vs >0 / Wilson「>0」は win-rate 解釈で非拘束 / M3b 目標 +0.5% vs +2〜3%) は毎日出力に明示 — 裁定は user
- **M3 を M3a (throughput: 累積 N≥30 セル数/3、線形外挿 ETA 付き) と M3b (return: 正EVセルの 30d 寄与、pips 一次 + JPY/%NAV 推定レイヤ) に分離**。M3a は累積/稼働の二母集団を分けて出力 (休眠 legacy セル `bb_rsi_reversion×USD_JPY` ×2 が累積 N≥30 に混じる — 09-04「0 個」は稼働側の読み)
- **2026-09-10 実測**: M1 弱 = 🔴 NOT_MET (N=17 / −85.0p / P(sum≤0)=0.817、09-04 +19.8p から **MECHANICAL_FLIP で再反転** — 勝ち +92.7p の窓外脱落が主因)。**M1_STRONG 全変種 未達** (セル 0 / literal 1 = 休眠 bb_rsi SELL / book NOT_MET)。M3a **2/3 (稼働 0)**、3 本目 ETA 2026-10-26 (carry_dip)。M3b **−0.075%/月** vs +0.5% = 線形外挿で到達不能
- **読み手を同一コミットで配線** — Tier A cron (`render.yaml` `fx-ai-tier-a-gate-status`) を `--strong` 込みへ更新、`tools/quant_gate_status.py` が pass-through。Discord 送信は 1900 字 hard-cut 単発 → **セクション境界で最大 4 分割**へ (strong 追加で Readiness / prereg watch が毎日切り落とされる副作用の除去)
- テスト: `tests/test_m1_strong_and_m3.py` **25 本** (N=29/30 境界 / EV 0.99/1.00 境界 / Wilson 下限 0 跨ぎ / flip 分解の恒等式 sum_added−sum_aged=sum_now−sum_prev / cron 配線 pin / Discord 分割)。全 suite **3,026 passed** / `check.py` 9/9
- 分析: [[m1-strong-definition-implementation-2026-09-10]] / roadmap KPI 表の反映は user 裁定後 (本コミットでは提案節のみ)

## 2026-09-10 — feat(quality): estimand 宣言表 + 配線チェッカー — 検知器の「名乗る量」を台帳化 (rule:R3)

- **メタ監査 §4.2 R3 の執行** ([[process-meta-audit-2026-09-07]]、user 承認 09-10): 監視バグ潜伏中央値 124 日・QA 起点発見 0/8 の根因 = estimand 混同 (PR #221/#224/#207/#209/#228 が同型) に対し、検知器の estimand を 1 ファイルに外部化した
- **宣言表**: `monitoring/estimand_declarations.yml` — 本番監視 **14 系列** (engine_tick_stall / candidate_stagnation / trade_row_freshness / live_n_stagnation / live_fill_stagnation / db_write_probe / disk_capacity / api_reachability / m1_clean_live_kpi / prereg_trigger_watch / shadow_promote_r2_alert / live_roster_attrition / trade_monitor_activity / demo_trader_watchdog) について claims (名乗る量) / population (母集団) / clock (wall|market_open) / threshold_source (SSOT) / reader (読み手) / counterfactual_test を宣言。**全宣言はコード読解で確認済み — 推測記載ゼロ** (推測で書くこと自体が estimand 混同)
- **チェッカー**: `tools/estimand_declaration_check.py` — schema 検証 + reader/threshold_source/detector の **grep レベル配線検証** (ファイル実在 + 宣言文字列の参照)。counterfactual 不在は WARN (exit 0)、`--strict` で exit 1。PyYAML 依存を避け厳格サブセットを自前パース (逸脱は ParseError — 黙って読み飛ばさない)。モジュールトップ副作用ゼロ
- **チェッカー自体の counterfactual**: `tests/test_estimand_declarations.py` 13 本 — reader を偽パス化 / 参照文字列を偽トークン化 / counterfactual_test を偽パス化 / 閾値シンボル改名 / clock 値域外 / typo フィールド、の各 fixture で checker が ERROR を出すことを pin (「検査を書いたら検査対象を壊して落ちることを確認」)。実宣言表の配線整合も CI で常時 pin
- **既知の負債を可視化**: counterfactual 不在 **8 系列** (candidate_stagnation / db_write_probe / disk_capacity / prereg_trigger_watch / shadow_promote_r2_alert / live_roster_attrition / trade_monitor_activity / demo_trader_watchdog) + 自動読み手なし 1 系列 (live_roster_attrition = ON_DEMAND)。返済計画は [[estimand-declaration-system-2026-09-10]] §5 — 全返済後に `--strict` を CI 既定へ
- **修理 PR 3 フィールド規約**: `.github/pull_request_template.md` 新設 — bugfix PR に「混入日 / 発見日 / 発見手段」欄 (欠陥税の継続測定用、bugfix 以外は N/A) + 検知器追加時のチェックリスト (宣言 + reader + counterfactual test を同一コミット)
- **本番挙動変更ゼロ** (新規ファイル + テンプレのみ、既存 .py 非接触)。`scripts/check.py` への組込みは提案のみ (analyses §6、親セッションが別途実施)
- 分析: [[estimand-declaration-system-2026-09-10]]

## 2026-09-06 — diag(monitoring): LIVE 発火セル 124→3 の帰属 — 88.7% は設計通り、11.3% は帰属不能 (rule:R3)

- 🛑 **09-04 が M3 スループットを「独立ボトルネック」へ昇格させた際の帰属 (「7-8 月の R2 降格バッチ = 設計通り」) は検証されていなかった** — どのセルがどの停止機構で消えたかを機械的に突き合わせた主体が存在しなかった。本コミットで読み手を新設し突合した
- **結果: 帰属済み 88.7%** — anchor 窓 (2026-05-01 終端 30d) の LIVE 発火 **124 セル**の内訳は `B_LIVE_STOPPED` **83** (`_FORCE_DEMOTED`/`_PAIR_DEMOTED`/`HTF_MIXED_LIVE_STOP_CELLS`) / `C_SHADOW_DEMOTED` **12** / `D_NEVER_PROMOTED` **15** / `E_PROMOTED_UNATTRIBUTED` **14**。窓系列は 09-04 の正準値を完全再現 (124/24/26/11/4/3) した上で分解
- 🛑 **止血は損失の圧倒的部分を除去していた** — 停止済み 83 セルは anchor 窓で **N=609 / −469.8 pips**。一方 E の 14 セルは N=34 / −25.1p と小さい。**分母縮小の代償は主に「負け」だった**
- 🛑 **D_NEVER_PROMOTED 15 セルは「失われた機会」ではない** — 昇格集合 (`_PAIR_PROMOTED` ∪ `_UNIVERSAL_SENTINEL`) に**一度も**入っていないのに 2026-04〜05 に LIVE 約定を出していた = 既知の昇格バグ期 (watchdog DECREMENT 再武装 / preserve 型) の残響で、**本来出てはいけなかった発火**。M3 の分子に数えてはならない
- **E は「バグ」ではなく「未帰属」** — CLAUDE.md 原則 3 により LIVE 転送側の winning-location フィルタは**意図的に維持**されるので、昇格済みセルが LIVE ゼロであること自体は正常でありうる。E が閉じないのは **セル単位で「昇格候補が LIVE 約定に至らなかった理由」を永続化する系列が無い**ため (`block_counts` はモード × family 粒度、かつ市場オープン時間しか積み上がらない) = **読み手の粒度不足**であって新種の欠陥ではない
- **E2_SILENT 4 セルは rnb 型シグネチャ** — `bb_squeeze_breakout × EUR_USD` (BUY/SELL) は `_PAIR_PROMOTED` 登録かつ `wiki/index.md` Current Portfolio に現役掲載だが**全行の最終出力が 2026-05-06 = 123 日前**。ただし scalp 側経路は env フラグ依存 (`SQUEEZE_REDESIGN_V2` ∧ `..._SHADOW_PROMOTE`) なので「意図的に無効」と「配線落ち」は **`/api/demo/live-enable-flags` の実測まで区別不能** — 断定しない
- 🛑 **09-04 の含意 3 を部分的に否定** — E1 10 セルが候補行を**転換率 100%** で LIVE 化したと仮定した上限でも、それは原則 3 のフィルタを全部外すことと同義で v2.3 の M6 ゲート (摩擦調整 EV>0) に正面から反し、[[friction-adjusted-ev-map-2026-07-07]] の「live viable な正セル不在」を覆さない ⇒ **「発火機会不足」は摩擦調整 EV 不在の帰結であって独立原因ではない**。M3 行の「別の律速」記述の格下げを提案 (user 決裁、分析 §5)。~14 ヶ月 ETA 自体は不変
- **実装**: `tools/live_roster_attrition.py` (帰属の唯一の再計算主体、markdown / `--json`)。fetch 失敗を空に畳まない (2026-08-30 監視 blind と同型の予防)。停止機構を足したら `load_stop_sets` と pin を同時に直す旨をコード内に明記
- テスト: `tests/test_live_roster_attrition.py` **20 本** (分類優先順位 / 分母 / estimand / 窓境界 / fetch 非畳み込み)。**counterfactual 3/3 が所望のテストだけを落とす**ことを確認 (停止集合を読まない / 停止集合が空 / fetch 失敗を `[]` に畳む)、初回素通りゼロ
- registry: `roster-e2-silent-promoted-cells` (2026-10-06、到達経路 = env 実値確認 → 配線落ちなら R3・無効化解除は R1) を新設
- 分析: [[live-roster-attrition-2026-09-06]] / roadmap: [[roadmap-v2.3-payoff-friction-repair]] KPI 表 M3 行

## 2026-09-05 — fix(monitoring): rnb_usdjpy の block カウンタ estimand 分離 + 153 日 dead mode の検出 (rule:R3)

- 🛑 **監視ログ最古の un-actioned 🔴 (`rnb_usdjpy:direction_filter` の 8 回連続 escalation、2026-08-26→09-04) をクローズ。仮説「compute_rnb_signal の WAIT-path バグ」は外れで、実体は独立した 2 つの構造事実**
- 🛑 **(A) カウンタが測っていない量を名乗っていた** — `direction_filter` は「方向が逆」と「そもそもシグナルが無い (WAIT)」を同名で数えていた。`direction_filter` を持つ唯一のモード `rnb_usdjpy` の signal_fn (`app.compute_rnb_signal`) は **SELL への return path を構造上持たない** ⇒ このカウンタの中身は **恒久的に 100% が WAIT**、「方向棄却」を一度も測っていなかった。実測 (MASSIVE USD_JPY 15m): **12.8y / 315,623 バーで SELL=0 / BUY 2,225 (0.705%) / WAIT 99.295%**、365d・60d でも SELL は厳密ゼロ。本番では 09-04 に **535/535 = 1.0000**、全システム block 集計の **15.6% (第 4 位 family)** = ダッシュボードの 1/6 が恒久的に無情報だった。副作用で WAIT が `conf<30` に到達せず「`conf<30`=ZERO」という**それ自体が異常に見える観測**を生み仮説を補強していた
- 🛑 **(B) 153 日間「動いているが 1 行も出せない」モード** — `rnb_support_bounce` は `QUALIFIED_TYPES` (104 型) にも `CONDITIONAL_TYPES` (空) にも**未登録**。`unknown_type` gate は shadow bypass を持たない無条件 gate なので、BUY が出ても **shadow 1 行すら生まれない**。導入コミット `db5e3e4c` (2026-04-05) は MODE_CONFIG / signal_fn / `_1H_PRESERVE_SLTP` / `MAX_HOLD_SEC` の 4 箇所を配線して `QUALIFIED_TYPES` だけ忘れており、`git log -S` はこの 1 コミットのみ = 以後一度も登録されていない。既存テストは事実を正しく記録していたが**意図された設計として pin**しており、異常として上申する読み手がいなかった (M1 KPI と同じ読み手不在型)
- **修正 (A のみ、挙動不変)**: 同一分岐内で `_block("no_signal" if signal not in ("BUY","SELL") else "direction_filter")` へラベル分離。**制御フロー・発注挙動・shadow 判定は一切不変**、作用域は `direction_filter` を持つ唯一のモード `rnb_usdjpy` に閉じる (作用域自体もテストで pin)
- **恒久ガード新設**: 全 `auto_start` モード (22) の signal_fn が返す **literal** `entry_type` が `QUALIFIED ∪ CONDITIONAL ∪ BLOCKED` に含まれることを AST で検査。違反は `("rnb_usdjpy","rnb_support_bounce")` の **1 件のみ**で、**既知集合との完全一致 (== / ⊆ ではない)** で assert ⇒ 新規ドリフトも既知ドリフトの解消も必ずテストを落とす。変数経由で entry_type を組む関数からは WAIT sentinel の `"wait"` しか抽出できない = ガードは false positive を出さない保守側に倒れる
- **B は修正しない (Rule 1 = user 決裁)**: `QUALIFIED_TYPES` 追加は `_UNIVERSAL_SENTINEL` 経由の minlot live 経路にも触れるため無条件 shadow ではない。確定足ベース頻度推定 **3.0/週 (365d) 〜 3.3/週 (12.8y)** は現行最速 live セル `usdjpy_carry_dip_accumulator` (2.10/週) を上回り **M3 スループット (発火機会不足) への寄与候補**だが、採用は BE/Trail ablated 365d BT + Bonferroni + pre-reg LOCK + R2 自動 demote gate 併設が前提。config コメントの `BUY EV=+7.7` は BE/Trail ablation 前の 2026-04-05 BT 由来で**引用不可**
- **`auto_start: False` 化もしない**: ①このモードは元から 1 行も出せない = 止めるものが無い (原則 1 に抵触しない) ②`_price_history` への USD_JPY 実 Close 供給 (2026-07-06 `PRICE_HISTORY_GUARD` 修正の対象) を壊さない ③下記の予測 3 で live セットアップ頻度が無料で取れる
- **検証可能な予測 (デプロイ後に答え合わせ)**: (1) `rnb_usdjpy:direction_filter` → 恒久 0 (非ゼロなら構造前提が壊れた合図) (2) `rnb_usdjpy:no_signal` ≈ tick 数 (~2,880/日) (3) `rnb_usdjpy:unknown_type:rnb_support_bounce` が**初めて可視化**され tick の ~0.5-0.7% に出る = RNB live セットアップ頻度の初の直接観測。⚠️ estimand 注意 — 上記推定は**確定足**評価、live は 30 秒ごとに**形成中バー**を評価するので消える一時的 BUY を拾い、実測はより高く・ノイジーになりうる
- テスト: `tests/test_rnb_block_reason_estimand.py` 7 本 (挙動 pin 3 + 構造 pin 4)。**counterfactual 8/8 が所望のテストだけを落とす**ことを確認 (ラベル巻き戻し / 常時 no_signal / SELL path 追加 / rnb 登録 / 新規未登録型 / 2 つ目の direction_filter モード / 走査の空振り / 抽出器の無力化)、**初回素通りゼロ**。全 suite **2,960 passed** / `check.py` 9/9
- registry: `rnb-support-bounce-registration-decision` (2026-10-06、到達経路 = 本デプロイで可視化される block family を読む) を新設
- 分析: [[rnb-dead-mode-and-block-estimand-2026-09-05]] / 教訓: [[lesson-block-counter-unmeasured-estimand-2026-09-05]] / roadmap: [[roadmap-v2.3-payoff-friction-repair]] KPI 表 M3 行

## 2026-09-04 — feat(monitoring): M1 KPI に読み手を新設 — 符号は反転していたが 60 日間誰も見ていなかった (rule:R3)

- 🛑 **roadmap 最重要 KPI である M1 (clean live 30d PnL > 0) を再計算する主体がプロジェクトに存在しなかった**。roadmap の M1 行は 2026-07-06 の手動実測 (N=92 / −242.6p) のまま **60 日凍結**され、その間に KPI は符号を反転していた。`clean_n_tracker` は件数、`daily_live_monitor` は cutoff 累計、`anomaly_watcher` は鮮度 — **どれも M1 を測っていない**。08-31 MoF 教訓「収集経路を足したら読み手を同じコミットで足せ」の一段手前 = **指標自体に読み手が無かった**型
- 🛑 **2026-09-04 現在 M1 は文言上は達成 (N=15 / +19.8p、6 月以来初のプラス)。しかしそれは成果ではない**: 08-30→09-01 の符号反転は **新規約定ゼロのまま** 2026-07-31 の `price_shock_rev_aud_jpy_h1_long` **−123.2p** が 30 日窓の外へ抜けたことだけで起きた (Δ=+123.2p、新規寄与 0) = **MECHANICAL_FLIP**
- **符号は統計的に未解決**: bootstrap 95% CI = [−217.6p, +241.2p] (幅は合計値の 23 倍) / P(sum≤0) = **0.426** / 符号検定 p=0.696 / t=0.17。**15 件中 4 件は、その 1 件を抜くだけで符号が消える**
- 🛑 **M3 スループットが独立ボトルネックに昇格 (roadmap 起票)**: LIVE 発火セル数は **124 セル/30d (2026-05) → 3 セル/30d (現在)**。現行レートでの M3 (clean live N≥30 セル 3 個) 到達は **最短 ~14 ヶ月** (carry_dip 2.3ヶ月 / ps_eur_gbp 6.4ヶ月 / ps_aud_jpy 13.8ヶ月、`weekend_gap_fade`・`kalman_d7` は LIVE 約定通算ゼロ)。**「エッジ不在」ではなく「発火機会不足」** — v2.3 が定義したボトルネックとは別の律速。分母縮小自体は 7-8 月 R2 降格による正しい止血だが、副作用として **M1 は「止めるほど達成しやすい」縮退 KPI** になった
- **実装**: `tools/m1_clean_live_monitor.py` (M1 の唯一の SSOT 計算主体、verdict 3 状態 `MET`/`MET_UNDERPOWERED`/`NOT_MET` + 符号反転の帰属 + 1 件脆弱性) → `tools/quant_gate_status.py` (日次 Tier A cron UTC 00:20 → Discord) へ配線。**M1 の定義は変えない** — 生の符号に「その符号が雑音と区別できるか」を併記するだけ。定義への統計資格条件付与は user 決裁事項 (analyses §8)
- **estimand 妥当性**: 新ハーネスで anchor=2026-07-06 を計算すると **N=92 / −242.6p / EV −2.64** = roadmap 記録値と完全一致。⚠️ pip 合計であって口座損益ではない (セル毎に lot が異なる) — M1 の定義由来の限界として明記
- **設計上の罠 2 件**: (1) `send_discord` は 1900 字で切り詰めるので **M1 を末尾に置くと読み手を足したのに誰にも届かない** → `to_markdown` 先頭に固定し順序をテストで pin (2) bootstrap の seed 未固定だと日次 CI が毎回ぶれて読めない → seed 固定を pin
- テスト: `tests/test_m1_clean_live_monitor.py` 17 本。**counterfactual 10/10 が所望どおり落ちる**ことを確認 (estimand 4 条件の各削除 / timestamp 破損の「今」扱い / 配線切断 / セクション末尾移動 / MECHANICAL_FLIP 無効化 / verdict 常時 MET / seed 除去)。初回素通りゼロ
- registry: `m1-sign-flip-durability` (2026-10-06 再読み) / `carry-dip-live-to-shadow-drop-cause` (2026-11-30) を新設、`live-fill-drought-2026-08-26-disposition` は **条件 (a) 成立で RESOLVED** (09-03 に LIVE 約定 2 件発生、転送経路の健全性を再確認)
- 分析: [[m1-kpi-readout-and-mechanical-flip-2026-09-04]] / roadmap: [[roadmap-v2.3-payoff-friction-repair]] KPI 表 M1/M3 + ボトルネック節

## 2026-09-02 (4) — fix(registry): E1 positioning 鮮度監視の陳腐エントリを機械評価型へ移行 (rule:R3)

- 🛑 **「MYFXBOOK 資格情報は user 投入待ち」という 7 週間陳腐化したブロッカー看板を撤去**: 実際は 2026-07-16 に投入済み・first login 同日・ingest は 13/13 ペアで継続稼働中 (本番 `/api/positioning/status` 実測: logged_in=true / consecutive_failures=0 / stale 12 分)。e1 pre-reg LOCK 時 (07-17) に解消が記録されていたのに、registry `e1-positioning-ingest-freshness` が `conditional_info` 型 (機械評価対象外) のまま「投入待ち」を主張し続け、セッション毎の UNRESOLVED リストに偽ブロッカーとして再生産されていた
- **是正**: 約束どおり `ingest_freshness` 型へ移行 (`r3-market-data-ingest-freshness` と同型) — 判定 = health `verified:{PAIR}:outlook` 13 キー、閾値 2h (実測 48 日で 2h 超 gap は 1 回のみ = 08-23 Disk 満杯 71.3h 停止、真検知・修復済み PR #205/#206)
- **first look (10-15) への影響を registry に明記**: 71.3h 停止は評価窓 market-time ~54.6h ≈ **5.7% を消費済み (coverage 予測 94.3% > gate 90%、残 budget ~41h)** — verdict 時に既知 debit として扱う (LOCKED pre-reg 本文は不変更)
- 教訓の再確認: **conditional_info (機械評価なし) の「条件成立」は誰も検知しない** — 条件が Claude/機械で観測可能になった瞬間に型を移行する (evaluator レベル欠陥 PR #195 と同族の「常時 WATCHING」変種)

## 2026-09-02 (3) — feat(gate): 静的 hour block class exemption — min-lot carve-out 契約群 (rule:R1 🔒 user 承認 2026-09-02)

- **[[hourblock-recal-and-ema200-verdict-2026-09-02]] Study 1 推奨経路の執行** (user 承認 2026-09-02「どちらも進めて」、前例 = sweep gbp_asia 免除 08-03「進めて」)。min-lot carve-out 契約群 (`_STATIC_HOURBLOCK_CLASS_EXEMPT` = `_AGG_KELLY_GATE_MINLOT_BYPASS_TYPES` **同一実体 alias**、12 戦略) に限り、6 つの静的 hour/session block (EUR_USD Tokyo / Late NY / H7-8 / H11、USD_JPY H13 / H16-20) の live 抑止を免除。**一般母集団への block は全て維持**、regime/方向系 block は不変更、demoted tier は fail-closed で対象外
- **edge claim ではない**: 根拠 = ①再較正で相対毒性 0/6 (parity、独立窓複製済み) ②class 全員 1000u 固定契約 + binding R2 registry でリスク有界 ③期待効果 +3 イベント/月 (carry_dip 主)。PR #219 の B7/B8 live 層 +EV 観察 (post-hoc N=17/26) は**根拠に不使用** — その裁定は `alpha-scan-b7-b8-livecell-recheck` (11-30) に凍結のまま
- **R2 rollback を同 PR で機械化**: 免除発火時に `[HOURBLOCK_CLASS_EXEMPT]` marker を reasons へ永続 → registry `hourblock-class-exempt-r2-rollback` (`live_count_decision` に `reasons_marker` フィルタを拡張) が **marker 付き clean live N≥10 ∧ pooled EV<0 で免除撤去**。母集団 = 免除で通過した行のみ (estimand 忠実)。期日 2026-12-01 stale review
- テスト 10 本: 6 gate 両側 counterfactual (メンバー通過+marker / 非メンバー従来 block) + identity pin (免除クラス=min-lot set、**性質で pin**) + demoted 除外 + 窓外 marker 不付与 + 計数フィルタ。**counterfactual 実測 = class 空集合化で 7/10 fail → 復元 10/10 pass**
- pre-reg: [[hourblock-class-exemption-prereg-2026-09-02]] (🔒 LOCKED)

## 2026-09-02 (2) — fix(dedup): shadow_emit のプロセス境界 dedup 突破を write-time DB flag で塞ぐ + audit units:0 自己記述化 (rule:R3)

- 🛑 **ema200 forensics ([[hourblock-recal-and-ema200-verdict-2026-09-02]] Study 2) の近接重複 22 ペアの機構を確定**: `_maybe_reserve_signal_emit` の dedup ゲートは **プロセスローカル in-memory 状態**でプロセス境界 (zero-downtime デプロイ重複 / コンテナ置換 / 一時的な第 2 インスタンスが同一 Render Disk SQLite に並走書込み) を越えられない。決め手 = `/api/admin/dedup_status` の counter 矛盾 (単一インスタンスで `shadow_called=1` なのに boot 後 shadow_emit 2 行 = 2 行目は今は存在しない別プロセス由来)。[[lesson-shadow-emit-dedup-2026-04-30]] の restart 消失の**並走版**、dedup 系 5 例目
- 🛑 **boot 時 backfill の write-time ギャップ**: `_backfill_dedup_violation` は境界越え重複を retroactive に flag するが**起動時のみ**。boot 後に生じた重複は次回起動まで未 flag → **その窓で走った point-in-time 分析が N を水増しして見る** (実例 = 2026-07-31 ema200 quant-eval N=79 PASS は当時未 flag の重複込み。**churn 抑制で起動が稀になるほど盲点が広がる**)
- **修正**: `demo_db.open_trade` に **write-time の DB 参照 dedup flag** を追加。shadow 行 INSERT 時、同一 (entry_type, instrument, direction) の dv=0 先行行が TF 窓内にあれば新行を `dedup_violation=1`。共有 DB 参照ゆえプロセス境界を越え、write-time ゆえ即時。**行は必ず保持 (挙動不変・データ非破壊、live 送信 `oanda_trade_id != ''` は対象外) — flag のみ変え、quant-eval/R2 audit が既に除外する列を使う**。boot backfill は歴史回収として存続 (相補的)。skip-insert 案は considered-but-rejected (害は測定 N 水増しのみ、live 重複なし → 既存 flag 方式を踏襲)
- **他戦略への影響 (定量)**: 90d shadow の intra-window 重複 **1,434 行中 1,431 (99.8%) は boot backfill が既に dv=1、未 flag は 3 行 (0.04%)** = **集計 quant-eval への水増しは軽微**。実害は point-in-time 分析に限定 → write-time flag で恒久解消
- **audit units:0 の自己記述化 (同 PR)**: `_open_shadow_emit_trade` の `_add_oanda_audit` block_reason を `shadow_tracking(shadow_emit_no_lot)` へ。units=0 = ロット未割当のトラッキングマーカーであってサイズ 0 の発注ではない旨をコメント併記。`shadow_tracking` prefix 維持で startswith 依存の guard/tool (drift_guard/breakdown/counterfactual) は互換
- テスト: `test_shadow_dedup_write_time_flag.py` 3 本 (cross-process flag / TF 窓境界 / 非重複行 anchor、counterfactual = fix 前は dv=0 で fail 確認済み) + audit 自己記述の exact-value 更新 4 本 (shadow_emit_audit/kalman_v18e/sr_audit_pipeline)。`open_trade` に `entry_time` override 追加 (テストが distinct bar を seed するため、production は常に now)。全 2904 passed / check.py 9/9
- lesson: [[lesson-shadow-emit-dedup-writetime-2026-09-02]] / forensics: [[hourblock-recal-and-ema200-verdict-2026-09-02]] Study 2

## 2026-09-02 (1) — study(recal): v8.9 alpha_scan 静的ブロック 10 件の再較正 — 10/10 PREMISE-INTACT (rule:R3)

- **コード変更ゼロ / 挙動不変。** 2026-04-14 較正 (N=9〜89) の静的ブロック 10 件を、較正と非重複の窓 (2026-04-15〜09-01、clean 11,840 行 = shadow 11,548 / LIVE 292) で再検定 → **全件 PREMISE-INTACT** (新 N=146〜1,404 = 較正の 10〜100 倍、摩擦調整後 EV −2.35〜−4.21、Bonferroni m=10 α=0.005 に対し全て p<1e-4)
- **2026-09-01 readout の「静的 hour block が NY live を不当に削っている」仮説は全母集団水準で反証**。B8 (H16-20×USD_JPY) は N=675 EV_net −3.26 [−3.85, −2.67] = 正しい防御。live 頻度問題の主因は**セル構成 (6 月世代の R2 demote)** に確定
- 事前予想 (§5「較正 N が薄い B6/B7/B10 は STALE だろう」) は**外れた**。母集団オーバーラップも 70.0〜93.8% で estimand 不一致仮説自体が否定
- **post-hoc 観察 (claimable ではない)**: live 転送が現に可能なセルは shadow の 4.0% (462 行) にすぎず、この層では B7/B8 の gross EV が正 (+1.27/+1.09、WR 57.7-64.7%) に反転する。ただし **N=17/26 < 30 かつ post-hoc かつ shadow は BE/Trail 楽観** → **ブロック維持**、次 pre-reg の estimand として registry `alpha-scan-b7-b8-livecell-recheck` (期日 2026-11-30) に登録
- **妥当性チェック (P0) 自体の設計欠陥を発見・是正**: `_is_live_tier_exempt` は時変なのに現在値の静的集合で pin していた → 違反 104 行は偽陽性。再構成の正しさは engine の読み出し経路との**コード同一性**で確定 (`demo_trader.py:5139` ↔ `demo_db.py:2135-2136`)、違反行は 2026-08 で 0/12 に消滅。教訓: [[lesson-validity-check-pins-proxy-2026-09-02]]
- **測定ツール自身のバグを境界値テストが初回検出**: B1 の `(_utc_hour(r) or 99)` が hour==0 を falsy 取りこぼし → N 174→241 に是正 (verdict 不変)。counterfactual 3/3 + 実欠陥 1 = **4/4 が所望どおり失敗**
- pre-reg/verdict: [[alpha-scan-static-block-recalibration-prereg-2026-09-02]] / 数値: `raw/bt-results/alpha-scan-block-recalibration-2026-09-02.json` / ツール: `tools/alpha_scan_block_recalibration.py` (テスト 35 本)

## 2026-09-01 (5) — feat(kalman): min-lot carve-out — 05-28 決裁 live 化の実効化 (rule:R1 🔒 user 承認 2026-09-01)

- 🛑 **kalman_d7 は 05-28 user 決裁 (SUCCESS = OANDA fill ≥1) から 96 日間 live fill ゼロだった**: `_AGG_KELLY_GATE_MINLOT_BYPASS_TYPES` 非所属 + FLAT 5000u > bypass 上限 1000u の二重不適格 (直近 14 日で 6 件 block をログ確認)。gate 衝突は 08-09 設計時に未認識、初認識 = 2026-09-01 session
- **carry_dip 同型の 1000u 固定契約 + bypass set 追加** (リスクは 5000u → 1000u の削減方向、シグナル/SL/TP 不変更)。R2 降格は既存 registry `t9-kalman-d7-live-n10-ev-check` が binding (LIVE N≥10 ∧ EV<0 → 停止)
- テスト 12 本 + counterfactual 実施済み (set から外すと 3 本 fail)。**「live 化を決裁した」≠「送信が発生しうる」 — live 化決裁時は gate chain 最後までの到達性 + fill 発生監視を必須にする** (教訓)
- pre-reg: [[kalman-d7-minlot-carveout-prereg-2026-09-01]] (🔒 LOCKED — user 承認 2026-09-01、同日マージ)
## 2026-09-01 (4) — feat(infra): status volume keeper — OANDA API 存続のための出来高維持 (rule:R3, user 決裁 案 A)

- 🛑 **OANDA JP REST API の存続条件を発見**: Gold ステータス (前月取引量 USD 50 万、新規+決済双方カウント) + プロコース + 残高 25 万円を**継続充足**しないと API 停止 + トークン再発行 (FAQ 720/1730)。8 月出来高 ≈ $28k → **10 月 SILVER 降格見込み = 自動売買・E1 収集・テレメトリの物理停止リスク**。エッジトレードは MIN lot 契約下で構造的に $500k に届かない (有機レバー全部で $82-106k)
- **`modules/status_volume_keeper.py` 新設**: USD_JPY 10,000u の市場即時往復 (数秒保有) × 月 ~26 回で $520k を積む。**env `STATUS_VOLUME_KEEPER_ENABLE` default OFF — arm は user 最終確認後**。ガード = 口座完全フラット要求 (netting 干渉ゼロ) / NAV floor ¥262k / スプレッド >1.0p skip / 日次 3 RT / crash-safe 玉回収。**demo DB 非経由** (Kelly・鮮度検知の母集団を汚染しない — keeper が定期約定を作ると停滞検知が無効化されるため機能要件)。OANDA 側識別は `tradeClientExtensions.tag="SVK"` (market_order に clientExtensions サポート追加)
- **読み手を同一コミットで併設**: `/api/demo/status`.status_volume_keeper telemetry + anomaly_watcher に `nav_floor` (¥262k 警報線、API 停止床 ¥250k) / `svk_behind_pace` 検知器新設 (status 空 run では判定しない — blind ≠ 正常)
- テスト 16 本 (guard chain / 出来高両側カウント / crash 回収 / 月替りリセット / clientExtensions payload / telemetry 読み手 / heartbeat 到達性 pin / 検知器 4 本)
- 決裁: [[status-volume-keeper-2026-09-01]] / 分析: [[live-frequency-and-oanda-status-survival-2026-09-01]]

## 2026-09-01 (3) — fix(deploy): decisions/*.md の deploy churn を塞ぐ (rule:R3)

- 🛑 **KB ドキュメント専用の commit が取引エンジンを再起動していた取りこぼしを発見**。`knowledge-base/wiki/decisions/**` が `buildFilter.ignoredPaths` に無く、**直近 60 日で 23 commit (~0.38 deploy/日) が decisions/*.md だけのために web service を再デプロイ**していた (1 回あたり ~60s の無 tick + ~2.5-3 分の 24 モード ramp)。PR #199/#201 が churn を would-deploy 0 まで落とした後に残っていた
  - **発見の経緯 = 自分で踏んだから**: 本日の PR #214 (verdict、KB のみ) が `decisions/` に verdict doc を置いた結果デプロイが走り、本番が一時 502 → 復帰した。**自分の変更が起こした churn を追跡して初めて設定の穴に気付いた**
- **修復は narrow に**: `decisions/**` を丸ごと ignore して**はならない** — 同ディレクトリの `prereg-trigger-registry.json` は `TRADING_PATH_READ_PATHS` が「cron が読む load-bearing な状態なので保守的にデプロイを起こさせる」と明示している。したがって **markdown だけ**を ignore (`decisions/*.md` + `decisions/**/*.md`、入れ子の `shadow-audit-2026-04-30/` も被覆)
- **性質を対で pin** (構文でなく性質 — PR #209 教訓): `test_decisions_markdown_ignored_but_registry_json_still_deploys` が **①md は ignore される ②registry JSON は ignore されない**を同一 test で並べて固定。片方だけだと「全部 ignore」「全部 deploy」のどちらに倒れても気付けないため対で意味を持つ
- **counterfactual 2 本、いずれも所望どおり失敗**: ⑦`decisions/**` を丸ごと ignore (registry を巻き込む誤り) → 新 test + 既存の取引パス guard の 2 本が落ちる ⑧md の ignore を削除 (churn が戻る) → 新 test が落ちる
- pytest 2,836 passed / check.py 全 9 通過

## 2026-09-01 (2) — verdict(obs): candidate_stagnation 閾値 6h = 据え置き、根拠を N=16 → 90 日実測へ置換 (rule:R3)

- **判定: 閾値 `CANDIDATE_STAGNATION_HOURS = 6` を据え置く**。2026-08-27 以来の暫定値 (バースト実効 N=16 / 10 時間窓) を **90 日 / 書込みタイムスタンプ 274,862 / floor 30 分以上のギャップ 130 本**の実測へ置換 (PR #213 の `view=gaps` で初めて測定可能になった)
- **実測** (窓 2026-06-03 → 2026-09-01): 市場オープン換算 **p50 1.486 / p90 3.000 / p99 3.736 / max 54.666 h**。**閾値 6h での発火は 90 日で 1 回のみ**
- ✅ **その 1 回は誤発火ではなく真の検知**: `2026-08-21 21:59:57 → 2026-08-26 03:39:56` (wall 101.67h / market-open 54.67h) = **Disk 満杯事故 (全 SQLite 書込みが 3.5 日停止)** そのもの。`freshness_policy.py` docstring が「ダッシュボードには何の異常も出なかった」と記録している、監視スタック整備の動機そのものの事故 → **閾値 6h はこの一連の作業を生んだ当の事故を検知でき、かつ 90 日で誤発火ゼロ**
- ✅ **PR #213 のコード由来の予測が的中**: 上位 13 本のうち **12 本が金曜→月曜の週次再開ギャップ**で **3.000〜3.736h に密集** (実時間 50.00〜51.74h)。ばらつきの出所は境界ではなく**金曜最終候補行の時刻** (実測 20:16〜21:59 UTC) — 境界の合成値 3.00h が下限で、最終行が早い週ほど上に伸びる
- 🔵 **閾値が妥当な理由 = 分布に広い空白帯がある**: **3.736h と 54.666h の間に観測がゼロ**。この帯のどこに閾値を置いても 90 日の判定は同一 (誤発火 0 / 真検知 1)。6h は knife-edge ではなく広い平坦域の内側
- ⚠️ **2026-08-27 の根拠記述「max 120.3 分の 3 倍」は誤りだった** — 日次 2h ブロックだけを見て**週次再開ギャップ (3.0〜3.7h) を見落としていた**。真の余裕は 3 倍ではなく **1.61 倍**。ただし空白帯があるため**結論 (据え置き) は不変** — 根拠の方を訂正する
- **動かさなかったもの (意図的)**: 閾値 (下げる根拠も上げる根拠も無い) / **週末境界の 1 時間ずれ** (`freshness_policy` 金 21:00 vs `demo_trader` 金 22:00) — この 1h は週次ギャップ 3.00h に直接乗るが空白帯が広いため判定に影響せず、**実測で害が出ていないものを動かさない**
- **再較正トリガ**: ①誤発火と判明したら**上げる** ②Layer-0 時間帯ブロックまたは週末境界の定義変更 ③候補行ケイデンスの構造変更。**下げるのは実測なしに行わない**
- 詳細: [[candidate-stagnation-threshold-verdict-2026-09-01]] / 一次データ: `knowledge-base/raw/analysis/candidate-write-gaps-90d-2026-09-01.json`

## 2026-09-01 — fix(obs): candidate_stagnation 閾値較正の読み経路の天井を外す (rule:R3)

- 🛑 **未解決事項「`candidate_stagnation` 閾値 6h の再較正 (目安 09-03〜09-10)」は、待っても達成不能な待機だった**。`view=rows` の `LIMIT` は 2,000 行にハードコードされており、本番実測で **9.9 時間**しか遡れない (distinct `created_at` 1,790)。テーブルは **90 日 / 317,542 行**を保持しているのに読み手が見られるのはその **0.5%**。**6 時間の閾値を較正するのに 10 時間の窓しか無い** — 律速は経過時間ではなく**読み経路の天井**なので、1 週間待とうと標本は増えない
  - 「集めたのに読み手が無い」型 (MoF 月次額 = write-only 6 例目 / C1 テーブル自体が 2026-08-24 まで無経路) の**変種**: **読み手はあるが窓が狭すぎて問う質問に答えられない**。到達経路 lint は「読み手が存在するか」は見るが「その読み手が当該の問いに答えられる窓を持つか」までは見ていない
- **修復**: `view=gaps` を新設 (`query_candidate_write_gaps`)。生行をページングして運ぶのをやめ、**サーバ側で分布に畳んでから返す**。SQL の `LAG` で distinct `created_at` の連続差を作り (`idx_evcand_created` が範囲走査を支える)、317k 行を Python に運ばない
  - **estimand**: 検知器は `now - MAX(created_at)` を市場オープン時間で測る。よって較正すべきは「連続書込み間隔の市場オープン時間分布」の**上側の裾**であって中央値ではない (候補行はバースト構造を持つので生の中央値 0.15 分は*バースト内*密度 — 2026-08-27 の自己訂正)。**「バースト」を人為的に定義せずに済む**のは、上側の裾が定義上そのままバースト間ギャップになるから
  - **時計**: `freshness_policy.market_open_hours` (SSOT)。実時間で数えると毎週末 48h のギャップが立ち裾が週末で埋まる
  - **計算量の縮約とその正当性**: 市場オープン時間 ≤ 実時間 が常に成立するので、実時間で floor 未満のギャップは換算後も floor 未満。よって floor (既定 30 分) 以上だけを換算すればよく、これは閾値 (floor よりはるかに大) の誤発火計数に一切影響しない
  - **出力の中心 = 反実仮想の誤発火計数** `would_fire.count` (「この窓で閾値が X だったら何回発火していたか") + `top_gaps` (週末境界か / デプロイ再起動か / 本物の停止か を人間が突き合わせる)
- 🔵 **副次的発見: 最大ギャップは確率的な裾ではない**。10 時間標本の最大は **21:59:59 → 00:00:01 UTC = ちょうど 120.0 分**で、端点が正確な時計値 = **決定論的な日次 2h 空白** (2026-08-27 の「max 120.3 分」も同一構造の可能性)。含意: 閾値 6h は「確率的裾の 3 倍」ではなく「**毎日必ず起きる 2h ブロックの 3 倍**」。較正で本当に見るべきは、この日次ブロックが**祝日・週末境界と重なって積み上がる**ケースが 90 日窓にあるか — 10 時間窓では原理的に見えない
- **counterfactual 4 本、全て所望どおり失敗を確認** (初回素通りゼロ): ① `market_open_hours` → 実時間に差し替え → 週末系 2 test が落ちる ② 閾値既定を SSOT でなくリテラル 6.0 に → SSOT test が落ちる ③ floor 判定を削除し全ギャップで分位 → floor test が落ちる ④ `app.py` の `view=="gaps"` 分岐を削除 → endpoint test 2 本が落ちる
- 🔵 **日次 2h 空白はコードで確定 (推測ではない)**: `is_trade_prohibited` が `hour_utc >= 22` を Layer-0 で禁止し (`tokyo_mode` は `hour_utc < 7` のみ)、その早期 return (`app.py:2325`) は `log_candidates` (`app.py:2742`) **より前**にある → **22:00〜23:59 UTC は毎日、設計上ゼロ行**
- 🔵 **予測: 構造的な最大ギャップは日次 2h ではなく週次 3h** — 市場オープン計上の再開 (`freshness_policy` = 日 21:00 UTC) / エンジン再開 (`demo_trader._is_fx_market_closed` = 日 22:00 UTC) / Layer-0 解除 (`hour_utc>=22` = 月 00:00 UTC) の 3 境界が重なり、金曜最終行→月曜初回は実時間 50.0h・**市場オープン換算 3.00h** で毎週必ず起きる。含意: **閾値 6h の余裕は「max の 3 倍」ではなく約 2 倍**であり、08-27 の根拠記述は日次ブロックだけを見て週次再開を見落としていた可能性が高い。また **2 つの週末境界定義が 1 時間ずれている** (`freshness_policy` 21:00 vs `demo_trader` 22:00) — `freshness_policy` はこれを「24h 閾値に対しては無害」と明示的に許容しているが、**その許容は 24h 閾値に対する判断**で、6h 閾値ではこの 1h がそのまま 3.00h に乗る。⚠️ **コードからの予測であって実測ではない** — 90 日 ≈ 13 週末で readout を回して確定する
- **⚠️ 本 PR は測る手段を敷いただけで、較正そのものは未実施**。デプロイ反映後に 90 日窓で実行して閾値を確定する。誤発火が出たら**上げる** — 下げるのは実測なしに行わない
- 詳細: [[candidate-gap-readout-2026-09-01]] / tests: `tests/test_candidate_write_gaps.py` (8 本)

## 2026-08-31 — data+fix(mof): 月次介入額 15兆3,993億円の開示確認 + 「収集したのに誰も読まない」経路の構造修復 (rule:R3)

- **一次結果**: 財務省 月次開示で **令和8年7月30日〜8月26日 (2026-07-30〜08-26) の外国為替平衡操作額 = 15兆3,993億円** (= 15,399.3 十億円)。公表 2026-08-28、ページ `20260828.html`。**保有データ中で単一窓として過去最大** (2026-04/05 窓 11,734.9 の 1.31 倍、2024-04/05 窓 9,788.5 の 1.57 倍)
  - 月次開示は**方向 (円買い/円売り) も日次帰属も与えない**。2026 年の日次開示済みオペが全て `sell_USD_buy_JPY` であることは断定の根拠にしない。日次は **Q3 四半期開示 (~2026-11-06)** 待ち
  - **user の「7月の負けは介入」説は未決着に戻る**: 08-28 時点では直前窓 0円 で 07-01〜07-29 を反証済みだったが、ワースト 2 日 **07-30 / 07-31 は本窓に入る**。総額 >0 は「窓内のどこかに介入あり」までで、当該日への帰属は主張できない (総額 0 の反証力との非対称性)
- 🛑 **開示は 08-28 に出て、08-29 にはリポジトリ内にあった。それでも 08-31 の期日まで誰も気付かなかった** — 独立した 2 つの欠陥が同時に露見した
  - **(a) 人手経路が公表 URL を「推測」していた**: 過去 12 窓のページ名がたまたま全て月末営業日だったことから命名規則を「月末営業日」と推定し、`20260831.html` を直接叩いて 404 → 「未公表」と結論した。実際は `20260828.html`。**正しい規則は `window_end + 2〜4 日`** であり月末営業日との一致は偶然 (+2/+2/+4/+2)。**構築した URL の 404 は「未公表」の証拠ではなく「自分が予測した名前ではない」しか意味しない**。既存 `tools/mof_interventions_fetch.py` は**正しく index を列挙している** — 人手チェックがそのツールを迂回したことが欠陥
  - **(b) 書き手はいたが読み手がいなかった (write-only 6 例目)**: 日次 cron (`mof-statements-daily`) は index を列挙して **08-29 の commit `b27277d1` で `interventions_monthly_pending.csv` に 15,399.3 を書き込み済み**だった。しかしこの CSV を読む検知器が存在せず、**値は 2 日間リポジトリに座ったまま**。registry のエントリは `deadline_info` = 期日まで何も評価しない型で、宣言された到達経路も (a) の人手経路だった
- **修復**: `tools/prereg_trigger_watch.py` に **`csv_row_match` 型**を新設 — 収集済み CSV に述語一致行が現れたら TRIGGERED。後継エントリ `mof-monthly-disclosure-new-window` (window_end > 2026-08-26 ∧ amount > 0) を registry に登録し、**日次 cron が書く → Tier-A cron (00:20 UTC) が毎日読む**経路を敷設
  - **「取得不能」と「一致ゼロ」を折り畳まない** (PR #207 の `no_rows` vs `error` と同型): ファイル欠落 / パース失敗 / **列欠落 (schema 変化)** / **述語不正 (空 match・未知 op)** はすべて `DATA_UNAVAILABLE`、一致ゼロのみ `WATCHING`。折り畳むと schema が壊れた瞬間から永久に「健全に監視中」を表示し続ける。空 match を弾くのは全行一致による偽発火の防止
  - **回帰の本体**: 実ファイルに対し「08-29 時点の正しい閾値 (window_end > 2026-07-29)」なら TRIGGERED になることを固定 = **この検知器があれば当日に捕まえていた**ことの証明
- **旧 pin が誤った設計そのものを固定していたので置換**: `test_registry_automation_packet_triggers_wired` は `type == "deadline_info"` かつ `deadline == "2026-08-31"` という**構文**を pin していた = 「期日待ち + 人手 URL 推測」という失敗 mode を固定していた。**後継が機械評価可能であるという「性質」**の pin に置換 (PR #209 教訓: 構文でなく性質を pin せよ / 是正は緩めるのでなく絞って強くする)
- **counterfactual 3 本**。⚠️ **②が初回に素通りした**:
  - ① dispatch から `csv_row_match` 分岐を削除 → 落ちる ✅
  - ② `read_csv_rows` がファイル欠落を `[]` に折り畳む → **初回素通り**。evaluate 側で `None` と `[]` を分離しても、**fetcher 側で折り畳んだら意味がない**のに fetcher 単体の pin が無かった → `test_read_csv_rows_returns_none_for_missing_file` を追加して再確認
  - ③ 列欠落を `WATCHING` に折り畳む → 落ちる ✅
  - **教訓: counterfactual が初回に通ったら「安全」ではなく「pin が無い」の証拠** (PR #208 ⑥ / PR #210 ⑧⑨ に続き **3 度目**)
- **T5 復帰第2要件は肯定側材料を初取得、ただし認定は保留 (R1 = user 決裁)**: 第1要件 (D1 close<159.50) は 08-03 以降常時点灯、第2要件は 08-28 時点で**否定側** (直前窓 0円) だったのが本開示で**肯定側に転じた**。本開示は MoF 公式の外部一次情報であり価格推定ではないため cross-LOCK に抵触しない。**しかし (a) 方向が非開示 (b) 介入日が特定できず「160 防衛」の文脈適合を一次情報で確認できない** → **lot 0.5x 維持、変更なし**。決裁材料が揃うのは Q3 四半期開示 (~2026-11-06)
- **MoF family #4 (`mof-next-episode-reverdict`) は実質 load-bearing 化**: 単一窓最大の介入が確認された以上、Q3 開示に新規エピソードが載る公算は高い。ただし §10 の 1 回限り再判定は**四半期開示待ちのまま**で、**現時点で look を消費してはならない**。価格シグネチャからの介入日推定は 2026 窓 OOS を burn するため引き続き禁止
- **live パラメータ・発注挙動は不変更** (監視配管と KB のみ)。テスト **6 件追加** (`tests/test_prereg_trigger_watch.py` 38 → 44)、全 2825 件 green、`scripts/check.py` 全 9 チェック通過

## 2026-08-30 — fix(obs): API 到達不能の無検知を塞ぐ + fetch 失敗を「契約破綻」と誤診する経路を除去 (rule:R3)

- **実測から出発した (仮説ではない)**: 積み残し「`ENGINE_TICK_STALL_MINUTES = 15` の実運用確認 — デプロイ再起動で誤発火しないか」を Render cron ログで検証した際、**別の・より重い欠陥**が露出した
- **誤発火の検証結果 (先に結論)**: PR #208 の live 反映 (2026-08-28T05:59Z) 以降、web service のデプロイ再起動は **3 回** (08-29 03:22-03:24 / 08-29 23:29-23:31 / 08-30 05:15-05:16、いずれも build+deploy 100-110 秒)。この間の 15 分 cron 全 run で `engine_tick_stall` / `engine_tick_never` は **0 件**。⚠️ ただし**3 回中 1 回 (08-29 23:31) は watcher 自身が 502 を掴んで status を読めておらず、「正しく静かだった」のではなく「見えていなかった」** — 誤発火ゼロの母数は実質 2/3。閾値 15 分は据え置き (再較正の材料は増やす方向でのみ動かす)
- 🛑 **露出した欠陥: 本番 web service が落ちている間、監視スタックは落ちていることを報告できない**
  - 2026-08-29T23:31:00-02Z の実 run で `/api/demo/trades` `/api/oanda/status` `/api/demo/status` `/api/admin/disk_status` の **4 本すべてが 502 Bad Gateway** (直前 23:29 の `data(mof-statements)` commit によるデプロイ再起動)
  - 8 検知器のうち **7 個が完全に沈黙**。残る 1 個 (`live_n_stagnation`) が **`stagnation_check_broken`「no parseable timestamp field in /api/demo/trades」** を上げたが、**真因は 502 でありペイロード契約ではない = 誤診**。しかも時間バケット抑制で Discord にすら出ず (`[notify] 1 event(s) suppressed`)
  - **「本番が到達不能」を報告する検知器が存在しなかった**。cron は exit 0 で "finished successfully"、Render の `notifyOnFail` は cron 自身の失敗を見る経路なので発火しない → **web service が恒久的に死んでも通知はゼロ**
  - 構図は 2026-08-21 の Disk 満杯事故 (「凍結した画面は静かな相場と区別がつかない」) の**監視器側での再演**。MEMORY の「検知器そのものも write-only になりうる」の直系
- **根本原因は 1 行**: `fetch_json` が失敗時に `{}` を返し、**「取りに行けなかった」と「空だった」を呼び出し側で区別不能にしていた** — PR #207 で明文化した「`no_rows` と `error` を折り畳むな」と完全に同型
- **修正**:
  - `FetchOutcome(path, ok, payload, reason)` + `fetch_outcome()` を新設し、成否と理由を payload から分離。`fetch_json` は後方互換の薄いラッパとして残す (新規経路では使わないことを main の構造 pin が強制)
  - `check_api_reachability()` を新設。**全滅 = `api_unreachable`** (サービスの死、通知バケット 1h) と **部分失敗 = `api_endpoint_failed`** (そのエンドポイント固有、6h) を**別 type に分ける** — 畳むと切り分け情報が通知から消える
  - `check_live_n_stagnation(..., trades_ok=)`: 取得自体が失敗したときは**何も上げない**。本検知器の「黙って skip するな」という設計思想は維持されている — 沈黙するのは**別の検知器が同じ事実をより正確に報告するとき**だけ
- **デプロイ blip と本物の停止を、状態を持たずに区別する**: `fetch_all()` が**全滅時のみ** `API_RETRY_BACKOFF_SEC = (30, 60, 120)` で再試行する。部分失敗は再試行しない (ramp なら 4 本とも落ちるので、1 本だけの失敗は最初からそのエンドポイント固有の異常)。**実測が閾値を裏付ける**: 08-29 の 502 は 23:31:00 に発生し、デプロイは 23:31:07 に完了している = **30 秒の 1 回目リトライだけで回復していた**。累積 3.5 分は KB 実測の ramp 3.6 分 (PR #199) 相当で、cron 間隔 15 分に対して十分な余裕がある。`attempts` / `waited_sec` は必ずイベントに載せる — 「ramp を跨いだ上でなお全滅」なのか「1 回で諦めた」のかが読み手に分からなければ blip と停止は区別できない
- **cron の exit code は 0 のまま**: Render の `notifyOnFail` は cron 自身の異常を担当する経路であり、そこに web service の停止を混ぜると「どちらが壊れたか」が通知から読めなくなる。出力先は Discord (1h バケット) と stdout の恒久ログ
- **counterfactual 9 本を実行**: ①main から検知器の配線削除 ②`trades_ok` を渡さない ③`trades_ok` ガード撤去 ④`api_unreachable` を NOTIFY_NEVER へ ⑤部分失敗を `api_unreachable` に畳む ⑥部分失敗でもリトライ ⑦リトライ廃止 ⑧`fetch_outcome` が失敗を `ok=True` に潰す ⑨Discord 行を汎用 fallback に戻す。⚠️ **⑧と⑨は初回に素通りした**:
  - ⑧ — 検知器テストが `_fail()` で**手組みした** outcome を使うため、**ok/payload の分離が実際に生まれる場所** (`fetch_outcome` の except 節) が誰にも触られていなかった → `requests.get` を差し替える境界テストを追加
  - ⑨ — 描画 pin の assertion が「長さ > 60」「'json.dumps' を含まない」で、**汎用 fallback 行もその両方を満たしていた** → 専用行にしか現れない文言 (「他の全検知器は盲目である」「エンドポイント固有の異常」) で pin し直し
  - **教訓: counterfactual が初回に通ったら、それは「安全」ではなく「pin が無い」の証拠である** (PR #208 の ⑥ に続き 2 度目)
- **インシデント再生テストを同梱**: 08-29 の 502 シナリオを `main()` に通し、`api_unreachable` が出ること **かつ** `stagnation_check_broken` が出ないことを両側で pin。健全時に `api_*` が出ないことも対で pin (健全時に鳴る検知器は使い物にならない)
- **live パラメータ・発注挙動は不変更** (監視配管のみ)。テスト **25 件追加** (`tests/test_anomaly_watcher_detectors.py` 51 → 76)
- **本番反映を実測確認 (2026-08-30)**: cron `fx-ai-tier-c-anomaly` が **12:50:43Z に `a4c271bf` を checkout**、直後の **13:00:24Z run が「No anomalies detected.」を 2.2 秒で完了**。健全時に `api_unreachable` は出ず、リトライ経路も engage していない (engage すれば最短 +30 秒なので、所要時間がそのまま「リトライしていない」証拠になる)。⚠️ **確認できたのは「健全時に鳴らない」側だけ** — 「デプロイ blip をリトライが吸収する」側は次の再起動待ち。08-29 の実測 (502 発生 23:31:00 / デプロイ完了 23:31:07) から 30 秒の 1 回目で足りる見込みだが、**見込みは観測ではない**

## 2026-08-29 — feat(obs): 鮮度判定のダッシュボード露出 + 閾値/時計の SSOT 化 (rule:R3)

- **積み残し「ダッシュボード UI 側での鮮度表示」を解消**。PR #205/#206 で alert 経路、PR #207/#208 で `/api/demo/status` の生値までは通したが、**人間が実際に見る画面は最後まで blind のままだった**
- **なぜこれが load-bearing か**: 2026-08-21〜08-25 の Render Disk 満杯で全 SQLite 書込みが 3.5 日停止した際、**ダッシュボードは完全に正常に見えた**。凍結した画面は「静かな相場」と区別がつかない。生値 (`last_*_row_age_sec` 等) を payload に足しても、画面に判定が出ていなければ「読まれない計装」のまま (C1 candidate 4ヶ月 write-only と同型)
- **追加**: `modules/freshness_policy.py` — 閾値・週末除外の時計・UI 判定の **SSOT**。`classify_freshness(status)` が 3 系統 (`engine_tick` / `candidate_row` / `trade_row`) の level を返し、`/api/demo/status` に `freshness_ui` として載る。画面 (`templates/index.html` の `renderFreshness`) は**色を塗るだけで閾値を持たない**
- **時計の使い分けが本設計の中核** (混同するとどちらかが必ず誤る):
  - `engine_tick` = **実時間 (wall clock)**、15 分。tick は市場が閉まっていても前進するので、ここで週末除外を噛ませると**本物の週末停止を毎週見逃す**
  - `candidate_row` (6h) / `trade_row` (24h) = **市場オープン時間**。実時間で数えると毎週末必ず誤発火する
- **本番実測で weekend 分岐を検証 (2026-08-29 03:30 UTC、閉場中)**: 候補行は実時間 **20.4 時間**経過だが市場オープン換算 **0.0h** → 正しく `ok`、かつ画面に「市場オープン換算 0.0h (閉場ぶんを除外)」と**理由まで出る**。エンジンは 1 秒 / 24 モード稼働で `ok`。**「古いが正常」と「凍結」を画面上で初めて分離できた**
- **level を 4 状態に分離して折り畳まない**: `ok` / `stale` (閾値超過 = watcher が同じ入力で alert を上げる状態) / `idle` (全モード停止中・行なし = 「止まっている」でなく「**止められている**」、資格 vs 実状態) / `unknown` (値が無い・壊れている)。`unknown` を握り潰さないのは、沈黙こそが `live_n_stagnation` 126 日 no-op の原因だったため
- **SSOT 化で `scripts/anomaly_watcher.py` の重複定義を撤去**: `N_STAGNATION_HOURS` / `CANDIDATE_STAGNATION_HOURS` / `ENGINE_TICK_STALL_MINUTES` / `FX_WEEKEND_CLOSE_HOURS` と `_market_open_hours` は `modules/freshness_policy` へ委譲。**閾値を検知器と画面で別々に持つと、片方を上げたときもう片方が古い閾値で判定し続け、しかも全テストは green のままになる** — PR #199 で実際に踏んだ型 (設定リストにコメントを足したら guard の regex が黙って打ち切られた) の予防
- **counterfactual 4 本で pin の実効性を確認**: ①画面の `renderFreshness` call-site 削除 ②status payload から `freshness_ui` 削除 ③watcher が閾値を直書きに復帰 (SSOT 破れ) ④engine tick に週末除外を混入 — 全てで該当テストが落ちることを実測。**「読み手を併設したか」でなく「読み手が呼ばれているか」まで pin する** (PR #208 の counterfactual ⑥ が初回素通りした教訓の適用)
- ⚠️ **副産物: 既存の構造 pin が実装形に過剰結合していたのを是正** (`tests/test_engine_tick_liveness.py::test_status_payload_includes_engine_tick`)。PR #208 の pin は `"**self._engine_tick_payload()," in SRC` という**ファイル全体へのリテラル一致**で、本 PR が呼び出しを局所変数に束ねる等価リファクタ (`_engine_raw = ...` → `**_engine_raw,`) をした瞬間、**配線は無傷のまま**落ちた。pin が守るべきは「payload が `get_status` の返す dict に到達している」という**性質**であって構文ではない → `get_status` 本体に**スコープを絞った**上で、直接展開・局所変数経由のどちらの形でも配線を確認する形へ。counterfactual 3 本で**旧 pin より強い**ことを確認 (①呼ぶが dict に展開しない ②呼び出し自体を削除 ③`get_status` の外に同じ構文を置く — **③は旧 pin なら素通りしていた**)
- **live パラメータ・発注挙動は不変更** (表示と監視配管のみ)。テスト **17 件追加** (`tests/test_freshness_policy.py`)、既存 watcher テスト 51 件 green、全 736 件 green
- ⚠️ **残る非目標**: 個別モード wedge の検知は引き続き未実装 (payload には `engine_tick_stalest_*` として露出済み)。`CANDIDATE_STAGNATION_HOURS = 6` はバースト実効 N=16 の暫定値のままで、**再較正は 1〜2 週の実運用後** (2026-08-27 起点、目安 09-03〜09-10) — 本 PR では動かしていない


## 2026-08-28 — fix(obs): エンジン生存の真の検知 (tick 前進の実時刻) + MoF 月次介入額の一次確認 (rule:R3)

- **前セッションの積み残しを解消**: 08-27 に「`tick_counts` 差分監視が要るが **cron は状態を持てない**ので設計が要る」として見送った項目。**差分をサーバ側で取れば cron は状態レスのままでよい**というのが解法 — `write_probe.last_ok_at` が既に採っていた形と同じ分業で、常駐プロセス側が経過秒を出す
- **なぜ既存の観測系では足りなかったか (全て estimand がエンジンの下流)**:
  - `main_loop_alive` / `watchdog_alive` は `Thread.is_alive()` = **生きたまま中で詰まっている状態を alive と報告する**
  - `tick_counts` は単調増加カウンタだが **絶対値しか出ていない** ため単発観測では前進を判定できない
  - `candidate_stagnation` (PR #207) は HTF Hard Block の**後**の行を数えるので「全候補ブロック」と「エンジン死亡」を区別できない (08-27 の 73 分ゼロ行が実際にこれで **benign** だった)
  - `live_n_stagnation` は約定ベースで閾値 24h、`db_write_failed` は書込み経路の生死のみ
- **追加**: `DemoTrader._record_tick(mode)` (カウンタ + 実時刻を**不可分**に更新) と `_engine_tick_payload()` → `/api/demo/status` に `engine_tick_{status,age_sec,running_modes,stalest_mode,stalest_age_sec}`。watcher 側に検知器 `check_engine_tick_stall` (`engine_tick_stall` / `engine_tick_never`)
- **estimand が素直なのが本検知器の価値**: tick 前進は **HTF ゲートにもシグナル有無にも市場の開閉にも依存しない** (加算は `_tick` が戻った後で、`_tick` は週末なら early-return するだけ)。したがって `candidate_stagnation` と違い **発火 = エンジン異常と読んでよい唯一の系列**。逆に**週末を市場オープン時間へ換算してはいけない** — そうすると本物の週末停止を毎回見逃す (`live_n_stagnation` とは estimand が違う)
- **閾値の実測根拠 (2026-08-28、本番 24 モード稼働中を 20 秒間隔 x 8 標本 = 142 秒窓で観測、前進イベント n=89)**: 走っている **24/24** モードが窓内で漏れなく前進。モード別間隔 **median 40.4s / p90 60.9s / max 81.2s** (`MODE_CONFIG` の interval_sec 10-60s と整合、max が 60s 超なのは単一 main loop が 24 モードを順に回す直列化ぶん)。engine レベル (= 最も新しい前進) は最速モード scalp (10s) に律速され通常 20s 未満。定常の天井 = 最長 interval 60s + tick タイムアウト 30s ≈ 1.5 分、デプロイ再起動 = PR #199 実測で無 tick 59.5s + ramp 2m39s ≈ **3.6 分**。`ENGINE_TICK_STALL_MINUTES = 15` は **デプロイ ramp の約 4 倍 / engine 定常値の約 30 倍**。検知遅延は cron 15 分で上限 30 分 = 既存 2 検知器 (6h / 24h) より**桁で速い**。⚠️ 標本化間隔 20 秒の **aliasing** で上記ギャップは 20 秒の倍数に量子化され真値より**上振れ** (真値 <= 測定値) = 閾値側に安全なので補正しない。誤発火時は**上げる**
- **`_record_tick` に集約した理由 (call-site 欠落の 5 例目を作らないため)**: increment の 2 行を各 tick 経路にコピーする設計だと、新経路で片方だけ忘れて黙って壊れる。本プロジェクトはこの型を **4 回**踏んでいる (PR #168 `ctx.hour_utc` が live で 123 日定数固着 / PR #204 `bar_time` 全行 NULL 等)。increment とタイムスタンプを別々に書けば 5 回目になるだけなので**最初から不可分**にし、さらに **「`_record_tick` の外に生の increment が生えたら落ちる」構造 pin をテストに置いた**
- **状態の切り分けを折り畳まない**: `ok` / `never_ticked` (起動したが 1 度も tick 未完 = 起動失敗の疑い) / `not_running` (全モード停止中 = **止まっているのではなく止められている**、資格 vs 実状態) を別扱い。web が旧版で field が無い場合は `engine_tick_missing` として**記録は残すが Discord には流さない** (デプロイ直後のバージョン不一致で必ず一度は起きる。沈黙が 126 日 no-op の原因だったので skip もしない)
- ⚠️ **実装中に自分で踏んだ最悪ケースの無検知を塞いだ (レビュー前に実測発見)**: `_main_loop_start_ts` は `_main_loop` の先頭で設定されるため **main loop スレッドが一度も起動しなかった場合には存在しない**。一方 `start()` は `_runners[mode]["running"] = True` を先に立てるので、**「モードは running なのに tick ゼロ」= この検知器が存在する理由そのもの**の状態が作れる。初版はこのとき `engine_tick_age_sec = None` を返し、watcher が `engine_tick_missing` (= NOTIFY_NEVER、web 旧版と同じ袋) に分類して**完全に沈黙**した。本番相当の payload を組んで実測確認 → ①産出側に **モジュール定数 `_PROCESS_START_TS` のフォールバック**を入れて必ず数値を返す ②watcher 側も `never_ticked` かつ age 欠落なら **`engine_tick_never` として鳴らす側に倒す** (契約破れでも沈黙しない)。counterfactual ⑪⑫ で確認済み
- **counterfactual 12 本を実行して確認**: ①タイムスタンプ書込み削除 ②`get_status` 配線削除 (write-only 化) ③生 increment の call-site 復活 ④newest→stalest 取り違え ⑤停止モードを分母に混入 ⑥main() 配線削除 ⑦欠落フィールドの silent skip ⑧週末除外の混入 ⑨`never_ticked` を stall に折り畳み ⑩`not_running` を停止扱い ⑪プロセス起動時刻フォールバック削除 ⑫`never_ticked`+age 欠落の沈黙化 — 全てで該当テストが落ちることを実測。**⑥は初回に素通りした** (検知器を書いても `main()` から呼ばれなければ意味が無い = C1 write-only と同型の失敗が**検知器側**にもあった) ため、配線 pin を追加してから再確認
- **本番で graceful degradation を実測**: 現行 live (旧コード) に対し watcher を dry-run → `engine_tick_missing` 1 件のみ、Discord 通知なし。想定どおり
- **live パラメータ・発注挙動は不変更** (計装と監視の追加のみ)。テスト **29 件追加** (`tests/test_engine_tick_liveness.py` 16 / `tests/test_anomaly_watcher_detectors.py` 13)
- **意図的な非目標**: 個別モードの wedge (main loop は生きているが 1 モードだけ 30 秒タイムアウトを繰り返す) は検知しない — 閾値がモード別 interval 10-60s に依存し較正が別問題。判断材料の `engine_tick_stalest_mode` / `_age_sec` は payload に露出済みなので、必要になった時点で実測して足す

### 付随: MoF 月次介入額の一次確認 (registry `mof-monthly-total-2026-08-29-check`, deadline 08-28)

- **直前窓 令和8年6月29日〜7月29日 (2026-06-29〜07-29) の外国為替平衡操作額 = 0円** (一次ソース `feio/data/monthly/20260731.html`)
- → **user の「7月の負けは介入をくらった」説は 07-29 までについて反証**。月次総額 0 は「窓内のどの日にも介入が無かった」を意味し、総額 >0 が「窓内のどこかに」までしか言えないのと**非対称でゼロの側が遥かに強い** (日次帰属は Q3 開示 ~11 月まで不明)
- **ただしワースト 2 日は未決着**: 07-30 (−69,628円) / 07-31 (−21,370円) は**次の窓 (07-30〜08-27) に落ちる**。当該ページ `20260831.html` は 08-28 時点で **HTTP 404 = 未公表**
- **registry 初稿の公表日想定「~08-29」は誤りだった**: 過去 12 窓のページ名は `20260731 / 20260630 / 20260529 / 20260430 / 20260331 / 20260227 / 20260130 …` = **全て月末営業日**。→ resolve せず **deadline を 2026-08-31 (月) へ再武装**
- **T5 復帰第2要件への含意**: 本開示は**否定側の材料** (0円 = 介入なし)。`t5-jpy-cap-restore-price` は第1要件のみ点灯のまま **lot 0.5x 維持**、変更なし。cross-LOCK (MEMORY `project_t5_restore_mof_crosslock_2026_08_10`) どおり認定は外部一次情報のみで、価格シグネチャからの推定は `mof-next-episode-reverdict` の 2026 窓 OOS を burn するため引き続き禁止 — 本チェックは公式開示の読み取りのみなので抵触しない
- 詳細: [[mof-monthly-total-check-2026-08-28]]

- 教訓: **「cron は状態を持てない」は検知を諦める理由にならない — 状態を持てる側 (常駐プロセス) に差分を寄せればよい。** 観測の分業は「誰が測るか」でなく「誰が状態を保持できるか」で切る。そして **検知器そのものも write-only になりうる**: 今回 counterfactual ⑥ で、検知器を実装して通知文言まで書いても `main()` から呼ばれなければ全テスト green のまま無音である状態が実在した。**計装は「読み手を併設したか」だけでなく「読み手が呼ばれているか」まで pin する**

## 2026-08-27 — fix(obs): 行鮮度を status に出し「凍結 vs 静かな相場」を分離 + 評価停止の新検知 (rule:R3)

- **残穴の位置**: PR #205/#206 で alert 経路 (`write_probe` / `live_n_stagnation`) は塞いだが、`/api/demo/status` **自身**は最終書込み時刻を持たないままだった。08-21 事故で「ダッシュボードが正常に見えた」根本理由がこれ。ダッシュボードは 08-27 時点でも**凍結と閑散を区別できない**
- **追加した読み出し経路**: `DemoDB.get_row_freshness()` → `last_{trade,candidate}_row_{at,age_sec,status}` を status payload へ。判定列は **`created_at`** (DB 側 DEFAULT で必ず埋まる)。`bar_time` は call-site 欠落で live 行が全 NULL だった前例 (PR #204) があり**鮮度の基準に使わない**
- **status を 5 値に分離**: `ok` / `no_rows` / `no_table` / `unparseable` / `error`。**「行が無い」と「クエリが落ちた」を混同させないことが主目的** — silent except は「不発」と「ゼロ件」を区別不能にする (既存教訓)。契約 key は常に存在させる (key 欠落は下流の silent skip を生む = `live_n_stagnation` 126 日 no-op の直接原因)
- **キー衝突の回避**: `get_row_freshness()` の `error`/`now` をそのまま展開すると `/api/demo/status` の汎用 `error` (例外ハンドラが使う) と衝突し、鮮度クエリの失敗が **status 全体の失敗に見える**。`row_freshness_error` / `row_freshness_now` へ名前空間化して詰め替える
- **新検知器 `candidate_stagnation`** — 既存 3 検知器がいずれも見ていない故障モードを埋める: `write_probe` は**書込み経路**の生死しか見ず、評価スレッドが死んで候補がゼロでも ok を返す。`live_n_stagnation` は約定ベースで閾値 24h。そして **watcher はスレッド生存 (`main_loop_alive` 等) を一切見ていなかった** (全数 grep で確認)。`evaluated_candidates` はバー評価ごとの高頻度系列 (本番 315,173 行 vs 約定 16,548 行) なので、停止 ≒「エンジンが評価していない」を約定より遥かに速く捉える
- **閾値の実測根拠 (⚠️ 初稿の統計を自己訂正)**: 候補行は「1 バー評価で複数戦略ぶんが一斉に書かれる」**バースト構造**を持つ (2,000 行 = distinct 時刻 1,608 = **16 バースト**)。よって素の行間隔 median 0.10 分は*バースト内*の密度であり、**停止判定のケイデンスではない** — 混同すると閾値を桁で誤る。正しい指標は**バースト間ギャップ**: **median 3.2 分 / p90 59.7 分 / max 120.3 分** (max = NY クローズ〜アジア early、水 22:00→00:00 UTC の薄商い帯)。`CANDIDATE_STAGNATION_HOURS = 6` は **max の 3 倍**で値としては不変。ただし **バースト実効 N=16** しかなく p90/max は粗い推定 = **暫定値**。1〜2 週後に*バースト間*分布を取り直す。誤発火時は**上げる** (下げる調整は実測なしに行わない)。週末は `_market_open_hours` で除外 (実時間で数えると毎週末誤発火する既知の罠)
- ⚠️ **estimand の限界を本番で実測確認 (重要)**: 候補行は **HTF Hard Block が counter-HTF 候補を除去した後**に書かれるため、本検知器が測るのは「エンジンが評価しているか」ではなく **「候補が select_best 段階まで到達したか」**。08-27T02:25〜03:40 の **73 分ゼロ行**を調べたところ、**DTE 候補が `eurgbp_daily_mr` のみで全件 HTF Hard Block (htf=bull) に除去されていた**のが実体で、同時刻に `tick_counts` は前進 (daytrade 40→43/90s)、`block_counts` も 154 件計上 = **エンジンは完全に生きていた**。→ 通知文言を「engine 停止の疑い」から「候補が select_best に到達していない。benign 要因 (HTF block / 薄商い) を先に潰せ」に改め、docstring に確認手順を明記。**真の engine 停止判定には `tick_counts` の差分監視が必要だが cron は状態を持てないため未実装 (残タスク)**
- **本番実測で自己検証した副産物**: 上記訂正は、デプロイ後に `evaluated_candidates` の行数が 31 分間 1 行も増えないのを見て「定数固着 = コードを疑え」を自分の計測に適用した結果。**当時の 70 分ギャップは p90 (59.7 分) と max の間 = 異常ではなかった**が、初稿の median 0.10 分を信じていれば「700σ の異常」と誤読していた
- **counterfactual 4 本を実行して確認** (deploy-churn 教訓の適用): ①`no_rows`→`error` 折り畳み ②age の定数固着 ③`unparseable` の握り潰し ④市場オープン時間→実時間 のいずれでも該当テストが落ちることを実測。**green のまま無力化していないことの行動証拠**
- **付随 (偽陽性の除去)**: `check.py` の queue SLA 検査が `status:` を読まずファイル名日付のみで判定していたため、**完了済み** (`status: done`) のまま `queue/` に残った family-a タスクを 8 日間「滞留」と警告し続けていた。done 残置を SLA 滞留と**別種の警告に分離** — 偽陽性の常時点灯は本物の停滞 (E23 = in_progress 9 日) を埋もれさせる。当該タスクは Claude Review を付して `done/` へ移送
- **live パラメータ・発注挙動は不変更** (読み出し経路と監視の追加のみ)。テスト 20 件追加 (`tests/test_row_freshness.py` 10 / `tests/test_anomaly_watcher_detectors.py` 10)
- 教訓: **観測基盤の 3 段階 (書ける / 読める / 読んだ値が意味を持つ) は、足した直後に 3 段目まで通しておかないと必ず 1 段目で止まる。** 今回 status に field を足すだけで終えれば C1 テーブルが 4 ヶ月 write-only だったのと同型になるため、**同じコミット内で読み手 (`candidate_stagnation`) を必ず併設した**。検知器を足すときは同時に「この検知器の偽陽性は何か」を実測で決める — 鳴りっぱなしの検知器は無いのと同じ

## 2026-08-26 — fix(infra): Render Disk 満杯による全 DB 書込み停止が **継続中** と判明 → 自己回復 + 検知を新設 (rule:R3)

- **事故は継続中**。本セッション実測 (08-26T03:16-03:18Z) で本番ログに `database or disk is full` が **consecutive=85**、positioning / health / `log_candidates` / `_tick_entry` の全書込み経路が失敗中。検出自体は 08-25 に済んでおり MEMORY 本文も「未復旧」を正しく記録していた (MEMORY.md の索引行だけが閉じた窓のまま = **索引が本文より古い**)。**差分は結論の方**: 前回の「user 操作なしには絶対に直らない」を覆し、`os.remove` によるファイル削除は書込み成功を必要としない = **コード経路で回復できる** (自走原則)
- **実測**: trades 最終行 `entry_time=2026-08-21T18:46:24Z` / `evaluated-candidates` 直近 1・2・3 日いずれも **0 件** / disk = `/var/data` **1 GB**。**クリーン N 蓄積 (M1 の唯一のボトルネック) が 5 日間ゼロ**
- **D1 自己増悪ループ**: `backup_database` が「コピー → ローテーション」順で、満杯時はコピーが例外を投げて**空きを作る唯一の処理に到達しない**。→ ローテーションを先頭へ移し、free-space pre-flight で不足時は `status="skipped_low_disk"` を返す。**counterfactual 確認済** (旧実装で `test_backup_rotates_before_copying` が FAIL)
- **D2 計装ゼロ**: `shutil.disk_usage`/`statvfs` の参照がリポジトリ全体でゼロだった。→ `modules/disk_guard.py` + `GET /api/admin/disk_status` + anomaly_watcher の 15 分毎ポーリング (warn 75% / critical 90%、**閾値は API 応答に同梱 = 本番コードと単一ソース**)
- **D3 retention 不在**: `evaluated_candidates` は 08-24 実測で 517,378 行。→ `prune_candidates` (90 日 = 観測最長読み出し窓 30 日 × 3 倍マージン、env `C1_RETENTION_DAYS`) を起動時 + 日次レビューで実行。⚠️ SQLite `DELETE` はファイルを縮めない = **将来の増加を止める対策であって既存容量の回収ではない** (`VACUUM` は満杯時に最も無い資源を要求するので意図的に不実行)
- **D4 (最悪) 検知器が 126 日間 no-op**: `check_live_n_stagnation` は `status["last_trade_time"]` を読んでいたが、**この key は app.py のどこにも生成箇所が無い** (全数 grep)。docstring 自身が「あると仮定。無ければ skip」と書き、その仮定は一度も検証されなかった。**「24h トレード増加ゼロで警告」= まさにこの事故のための検知器が、事故の間ずっと沈黙していた**。→ 実在を本番応答で確認した `entry_time` を使用 + **時刻が読めない場合を `stagnation_check_broken` として異常報告** (黙って skip する旧挙動こそが欠陥)
- **回復手段**: `disk_guard.emergency_reclaim()` を起動時 (DemoDB 生成より前) + `POST /api/admin/disk_reclaim` に配置。**書込み成功を前提としない `os.remove` によるバックアップ削除**が満杯からの唯一の脱出路。満杯で中断されたコピーは mtime が最新になるため、**readable なコピーを recent より優先**して残す。平常時は no-op
- **live パラメータ・発注挙動は不変更**。テスト 23 件追加 (`tests/test_disk_guard.py` / `tests/test_anomaly_watcher_detectors.py`)
- 教訓: **書込み停止は「異常」ではなく「凍結」として観測される** — メモリ内カウンタ駆動のダッシュボードは永続化層が全滅しても正常に見え続ける。生存監視は**永続化層に到達した最新レコードの時刻**で行う。そして **計装の field 契約は「仮定」ではなく「検証対象」**: 「無ければ skip」と書いた時点で検知器は飾りになる。**測れないなら測れないと鳴らせ**
- 詳細: [[disk-full-write-outage-2026-08-26]]

## 2026-08-24 — fix(obs): evaluated_candidates.bar_time が live 行で全て NULL (call-site 欠落 4 例目、rule:R3)

- PR #203 で C1 テーブルの読み出し経路を新設した直後、本番を初めて読んだところ **hull_donchian_fade 直近 30 日 1,139 行すべて `bar_time IS NULL`**
- 原因 = call site: `_log_cands(..., bar_time=bar_time)`。`bar_time` が渡るのは **BT 経路のみ**で、live 経路 (`demo_trader._tick` → `compute_fn(df, tf, sr, symbol)`) は渡さない → live 行は常に NULL。**2026-08-09 に修復した `ctx.hour_utc` 凍結 (PR #168) と同一の call-site 欠落** で、そのとき同関数内の他の派生値は直したがこの call site は見落とされていた (同型 **4 例目**)
- **なぜ致命的か**: `bar_time` は C1 テーブルで唯一 bar 粒度への正規化を可能にする列。NULL だと **「1 バーを 30 秒 poll で 30 回記録した」と「30 本の別バー」が区別できない** — 実際 1,139 行は 12 日分の poll 膨張であって 1,139 バーではない。funnel 分解 (候補 → select_best → trade) が**原理的に計算できない**
- fix = PR #168 が確立した fallback `_dt_bar_dt` (`bar_time or df.index[-1]`、UTC 正規化) を渡す。`df.index[-1]` は order 層 dedup の `_closed_bar_ts_from_df` と同一基準なので `order_bar_dedup` の 1 バー 1 emit と直接突合できる
- **counterfactual 確認済** (deploy-churn 教訓の適用): 旧コード `bar_time=bar_time` に戻すと新テスト 2 件が落ちることを実行して確認。guard が無力化されていないことの行動証拠
- **副産物 — hull は select_best に勝っていた**: 30 日で `total_candidates 1,139 / n_selected 998 (87.6%)`。`LIVE_PROMOTE_LOSERS` 登録根拠 (2026-06-12「score 3.0-5.0 は敗北し prod fires=0」) と実測が食い違う。さらに **08-07/11/12/13/18 にも selected** = 最終 trade (08-06) 以降も候補生成と選択は継続 → **残余 4.7x の落下点は `_tick_entry` / order 層に確定**
- 付随: `view=meta` 実測 **517,378 行 / 54 戦略 / 2026-04-28〜08-21** (retention 不在の実測値)
- **live パラメータ・発注挙動は不変更** (監査列の埋め戻しのみ)
- 教訓: **「観測基盤を作った」は 3 段階ある — 書ける / 読める / 読んだ値が意味を持つ。** C1 は 4 ヶ月 1 段目しか満たしておらず、読み出しを繋いだ瞬間に 2 段目の欠陥が露出した = **読まれない計装は劣化を検知できない**

## 2026-08-24 — fix(obs): C1 candidate テーブルの読み出し経路を新設 + hull 発火率 funnel 分解 (rule:R3)

- **hull_donchian_fade の「13.3/週 期待 vs 1.62/週 実測」を funnel 分解**した ([[hull-fire-rate-funnel-2026-08-24]])。registry `t8-hull-shadow-freq` が 49 日間 info 表示のまま滞留していた案件
- **平均値が階段関数を隠していた**: hull の trade は全 17 行 (全 shadow)、**最終発火 2026-08-06 で以後 18 日ゼロ**。週平均表示ではこの停止が見えない
- **シグナル生成器は健全**: 凍結スペックを MASSIVE EUR_USD 15m にオフライン再生 (16.3 週) すると **205 signals = 12.59/週** で期待値 13.3 をほぼ再現。無発火だった 08-06〜08-21 窓にも **33 signals** が存在 → 「相場が setup を出さなかった」は棄却
- **funnel**: 12.59/週 → HTF Hard Block **−25.4%** → 9.39/週 → 実測 hold 直列化 → 7.61/週 に対し実測 **1.62/週 = 残余 ~4.7x は未説明で実在**
- **⚠️ 途中で誤結論しかけた点を記録**: `max_hold_bars=96` (24h) を直列化ブロック時間に使うと 3.07/週 まで落ち残余 1.90x = 「ほぼ説明できた」に見えた。だが本番 closed 17 件の実測保有は **median 0.57h** (p90 3.86h) で 24h キャップはほぼ不拘束 → 実測 hold だと残余は **4.7x**。**設計上のキャップを実効値の代理にすると残余を過小評価する**
- **「MR は counter-HTF で kill 率 ~100%」を hull に外挿してはいけない**: 実測 **25.4%**。生存 153 件中 119 件が `htf=mixed` 窓 (Hard Block は bull/bear 限定で mixed 非発動)。sweep の「HTF gate 100% silent drop」は sweep 固有の観測であって family 一般則ではない
- **🔴 真因 (診断が 49 日止まっていた理由) — C1 テーブルが write-only**: `evaluated_candidates` は [[lesson-select-best-bottleneck-2026-04-28]] を受け 2026-04-28 に新設され毎バー書かれ続けていたが、**HTTP route が無く `query_candidate_summary()` の呼び出し元は自身の unit test のみ** (本番参照ゼロ = 実質 dead code)。silent drop を可視化するための観測基盤が、観測できないまま 4 ヶ月データを溜めていた
- **fix**: `GET /api/demo/evaluated-candidates` を新設 (read-only / GET のみ)。`view=summary|rows|meta`、`strategy` / `instrument` / `days` / `limit` フィルタ。`query_candidate_meta` / `query_candidate_rows` を `modules/candidate_logger.py` に追加。テスト 10 件追加 (関数 5 + endpoint 5)
- **estimand 警告を route/関数 docstring に内蔵**: 本テーブルへの記録は **HTF Hard Block が候補リストを削った後**。HTF-blocked 候補は入らない (可視化は `[DTE] HTF_HARD_BLOCK` の stdout のみ) → **count=0 は「シグナルが出なかった」ではなく「select_best 段まで生き残った候補が無かった」**
- **付随観測**: 本テーブルに retention/rotation が無く単調増加する。`view=meta` で総行数を露出させ可視化のみ実施 (挙動不変、retention は別 R3)
- **live パラメータ・発注挙動は不変更** (観測系のみ)
- 教訓: **観測基盤は「書ける」だけでは完成していない。読み出し経路が無い監査テーブルは、無いのと同じ — むしろ「計装済み」という誤った安心を与える分だけ悪い**

## 2026-08-23 — docs(roadmap): T-MTF を CLOSE に是正 (KB drift、rule:R3)

- roadmap v2.3 の **T-MTF 行が 47 日間 🔄「調査中 (別セッション)」のまま残存**していた。実体は **2026-07-07 に PR #58 でクローズ済** — コード側で確認 (`DaytradeEngine.HTF_MIXED_LIVE_STOP_CELLS` = `modules/demo_trader.py:8833` / 診断タグ文言の実装整合コメント = `app.py:2181-2185`)
- 調査結果 (行に反映): 「シグナル抑制中」タグは**診断表示のみ**で、Hard Block は `htf_agreement` が bull/bear のときだけ効き **mixed は素通り**していた (mixed の実効果は legacy score×0.70 減衰のみ、DTE 候補は非抑制) = **バイパス確定**。fix は trendline_sweep×GBP_USD の cell stop 登録。再 live 化は R1
- **なぜ問題か**: 「調査中」の残存は、次セッションが**クローズ済みのバグを再調査する**か、逆に**未解決だと誤認して判断を保留する**。spawn_task で別セッションに渡した項目は、着地確認がロードマップに戻ってこない構造欠陥がある
- 教訓: **別セッションへ委譲した項目は、委譲元のロードマップ行に「誰が・いつ・どこで着地確認するか」を書く。書けないなら委譲しない**

## 2026-08-23 — fix(deploy): 残存デプロイ churn を実測分解して恒久ゼロ化 (phase-2, rule:R3)

- **phase-1 の効果を推定でなく実測で確定**: PR #199 マージ (08-21T01:57Z) 以降の main 31 commit に対し Render が実際に走らせたデプロイは **4 件 = 1.7/日** (baseline 18.8/日 から **−91%**)。§4.2 の推定「7.9/日」は保守的に外していた (実測はその 1/4.6) — **以後この種の効果は Render deploy 一覧との突き合わせで報告する** ([[deploy-churn-trading-gap-2026-08-21]] §8)
- **残存源の全量分解** (ローカル再生が Render の deploy 一覧と 4/4 完全一致 = 網羅性の担保): (a) `analyst-memory.md` **3/平日** (daily_report の post_tokyo/london/ny)、(b) `bt-results/phase1b` + `data/sentiment` 1/日 (phase1b 日次 re-run)、(c) `raw/cell_deepdive/` 不定
- **(a) の再分類 — 「ランタイム read」は粒度が粗すぎた**: 全数 grep で参照経路は `_read_analyst_memory` (app.py:11651) → `get_analyst_opinion` (:11749) → `/api/analyst-opinion` (:12229) の**人手起動エンドポイントのみ**。`modules/` / demo_trader / signal / OANDA 転送からの参照は**ゼロ**、起動時ロードも無し。**助言メモの鮮度のために平日 3 回 × (無 tick ~60s + ramp ~2.5-3 分) ≈ 平日 10 分の劣化取引**を払っていた = 原則 1 違反 → 分類を **取引パス read / 助言専用 read / write-only** の 3 階層に改め、助言専用は ignore 可とした
- **代償の可視化 (サイレントにしないことが交換条件)**: ignore により本番 memo は最後のコード系デプロイ時点で固定される → `/api/analyst-opinion` 応答に **`memory_stale_days`** を同梱し陳腐化を観測可能に (`app.py::_analyst_memory_stale_days`)
- **🔴 副産物 — guard の抽出器がコメント行で黙って打ち切られていた**: `_ignored_paths()` の regex `(?:\s*-\s*.+\n)+` はリスト途中の `# ...` で停止し、以降の entry が検査の視界から消える。`data/**` を誤 ignore する counterfactual を注入しても **6 テスト全て pass** した (= 検査の無力化)。修正 + `test_ignored_paths_parser_sees_entries_after_inline_comments` で pin、修正後は同 counterfactual で 4 テストが落ちることを確認
- **drift guard を非 KB ルートへ拡張**: phase-1 の guard は `"knowledge-base"` 起点リテラルしか走査せず、`data/**` / `bt-results/**` を ignore した瞬間に穴が空く → `test_no_new_runtime_data_path_silently_ignored` を新設 (実測検出 = `data/cache/massive` / `data/cache/yield` / `data/_holdout_locked/MANIFEST.json`、`cached["data"]` 等の dict 添字は偽陽性ゼロ)
- **効果**: 同一 31 commit 窓の再生で would-deploy **4 → 0**。過剰抑制でないことの対照 = 直近 276 commit では **32 commit が依然デプロイを起こす** (`modules/demo_trader.py` / `tools/` / `tests/` / `.github/workflows/` / `prereg-trigger-registry.json` / `data/cache/yield/*.parquet` 等のランタイム read)
- **範囲外 (主張しない)**: 逸失 pip の定量化。主張は「不要な断続窓が構造的に存在し、その全量を実測で特定して消した」機構レベルの事実のみ
- 教訓: **設定リストにコメントを足す変更は、その設定を読むパーサ全部を疑え。guard 自身が無力化されても全テストは green になる — guard を触ったら counterfactual を注入して「落ちること」を必ず確認する**

## 2026-08-21 — fix(deploy): KB ドキュメント commit が取引エンジンを再起動する構造欠陥を是正 (rule:R3)

- **発見**: autopilot ヘルスチェックで本番 502 → 障害ではなく**自分の push が誘発した再デプロイ swap 窓**と判明。「1 commit で取引エンジンが止まる」構造に気づいたのが起点 ([[deploy-churn-trading-gap-2026-08-21]])
- **実測 (origin/main 14 日)**: web service デプロイ **18.8/日**、うち **78% が `knowledge-base/` のみの commit**。`autoDeploy: commit` に path filter が無く、ドキュメント更新がそのまま `demo_trader.py` の per-mode background threads 再起動になっていた
- **1 回のコスト (Render app ログ instance 追跡)**: 旧 instance 最終 tick 01:07:47.8 → 新 instance MainLoop 開始 01:08:47.2 = **完全無 tick ≈59.5 秒**、全 24 モード到達まで **+2m39s**、cold cache で tick#1 が 10s 級 (定常 0.6s)
- **最悪ケース実測**: KB commit が 2m22s 間隔で連続した結果、新 instance が **寿命 85 秒・全モード tick#1〜#3 の warm-up 未完了のまま kill**。連続 KB commit 中はエンジンが定常状態に到達できない
- **対策 (R3)**: `render.yaml` web service に `buildFilter.ignoredPaths` を追加。**ランタイム read パスは意図的に除外** — `wiki/tier-master.json` / `wiki/snapshots/` / `raw/trade-logs/analyst-memory*.md` / `wiki/decisions/prereg-trigger-registry.json` はデプロイを起こさせる。ignore 対象は write-only (`raw/hunt_events/`, `raw/bt-results/`) と純ドキュメントのみ
- **効果 (同一 14 日窓で再生)**: デプロイ **18.8/日 → 7.9/日 (−58%)** (263→110。merge commit は first-parent 差分で評価)。残存最大要因は `analyst-memory.md` (41件、シグナル経路外だがランタイム read のため保守的に残置)
- **再発防止** `tests/test_render_build_filter.py` 3 件: ignoredPaths 縮小検知 / **ランタイム read 巻き込み検知** / **drift guard** (`app.py`+`modules/` の KB 参照を regex 抽出し、ignore に match するものは write-only allowlist 必須)。故意の違反注入で赤くなることを確認済み (非 vacuous)。pyyaml 非依存 (`scripts/check.py` と同じ regex 方式)
- **範囲外 (主張しない)**: 逸失 pip の定量化。断続窓と発火の同時性は未測定 — 主張は「不要な断続窓が構造的に存在した」機構レベルの事実のみ
- 教訓: **CI の paths filter (T15 で撤廃) と CD の build filter は別問題。前者は「テストを回すか」、後者は「取引エンジンを殺すか」**

## 2026-08-19 — research(family-C): rate_anchor_deviation explore — 臨時裁定 #26 + pre-reg 凍結 + two-pass (rule:R1 手続き)

- **family C (user 水平線理論の機械核 v2 = 金利観測フェアバリュー帯乖離リバージョン) を臨時裁定で台帳 #26 に採用** (改訂 WIP 原則: 能動 explore 枠 0/3 + user 直接承認 2026-08-19「進めて」)。claim = PR #197 + edge-dev レーン cross-session 承認、explore 枠 1/3 消費
- **pre-reg 凍結** ([[family-c-rate-anchor-explore-prereg-2026-08-19]]): 片側 LONG onset イベント (2y 金利差 rolling OLS 帯、z 下抜けクロス、Z_th 機械選定) × +21bd 固定 horizon、explore 2014-2021 (介入ゼロ実測窓)、swap 込み・gross/net 分解報告、MoF #4 cross-LOCK 遵守 (OOS は介入隣接 partition)
- **敵対的検証 GO-WITH-CONDITIONS (blocking 10 条、[[family-c-adversarial-verification-2026-08-19]])** — 最重要 3 件を凍結前修復: ① 旧 gate C null が合成 probe で反保守 (type-I 20-29% @ 名目 5%) → **年内 demean + episode-block sign-flip + p≤0.02 較正**へ差し替え、② JGB Golden Week gap (実測 11 暦日) × staleness 5d 規則が 2019-2021 を連鎖 blackout → 12d へ、③ rates-content 識別不能リスク → b≡0 ablation 対照 + 解釈規則凍結
- ハーネス `tools/family_c_anchor_explore.py` (freeze/pass1/pass2/oos、4 点 OOS 機械ロック実装済み) + test pin 19 件。registry `family-c-explore-verdict-deadline` (08-29 backstop) 登録 → 同日 resolve
- **verdict = ❌ FAIL (同日 two-pass、期日 10 日前倒し、OOS 2022+ 非接触封印)**: N=41 (Z_th=1.5)、**gross −20.5p / swap −1.6p / net −24.2p (adverse −32.1p)** — 帯下 onset 後の +21bd は平均続落。gate C (timing 超過 vs 同年無条件ロング) p=0.527、LOYO 符号不安定 (JPY 増価年 2015/16/18 が負殺)。median +1.4p・WR 51% = 左テール支配 (falling-knife 型)。**h5 診断 (非 claim): 初週 +10.9p バウンス → 21bd で逆転** = 「dip は跳ねるが多週ホールドで死ぬ」
- **クローズ範囲発効**: 日次金利差アンカー帯 × USD_JPY × 帯下 onset LONG × 5-63bd 全変種。**user 水平線理論の機械核 v2 死亡 — 裁量スタック残余 = 執行層 (15m/1m) + exit 層のみ**。power caveat: MDE 131p、FAIL≠falsified だが点推定負 = 符号情報を持つ FAIL
- **副次所見**: ablation 対照 (価格のみ z) は Jaccard 0.167 で識別作動 + さらに悪い −65.8p = **USD_JPY 多週 dip-buy は 2015-2021 で機構を問わず負け**。E-C の介入 dip +188p (2026) は非介入 dip で再現されず = 介入型の固有性示唆 (09-18 A/B/C 統合裁定の一次材料)。ppp「USD_JPY だけ IC 負」prior が的中

## 2026-08-19 — fix(watch): 条件付きトリガの評価器レベル欠陥 — 「常時 WATCHING」を機械評価へ (rule:R3)
## 2026-08-19 — research(family-A): statement_ladder explore pre-reg 起草 (DRAFT、測定ゼロ) — 09-18 統合裁定の前提材料 (rule:R3)

- **family A (発言ラダー→介入確率) の explore pre-reg を DRAFT 起草** ([[family-a-statement-ladder-prereg-2026-08-19]])。起点 = `statement-ladder-foundation-readiness` resolve (PR #195、基盤 PR #194) + user「進めて」。claim = queue ticket + 本 PR (E23 方式)
- **estimand = ladder 検出器の較正 (hit / false alarm 率、価格全面不使用)** — dossier の指定どおり「発言ラダー先行 (N=4 記述)」の FP 率測定が本 family の仕事。primary = L≥4 遷移検出器 1 本 (m=1)、(T,R,H)=(5,20,20) 設計仮説、凍結は敵対的検証後に論拠のみで確定
- **正直な拘束を事前固定**: 有効 N=4 episode blocks → **全 verdict 記述級** (edge 主張不可) / **P-A1 = lexicon v1 語彙は 2022/2024 目視検証を経た in-sample 汚染チャネル** → クリーン判定は forward OOS のみ (Q3 開示 ~11-06 が最初の機会、エピソードゼロ四半期も FP 側検証として記録) / lexicon は PR #194 commit `569dbe3f` に pin
- **測定は未実施** (発言×介入ジョイント量ゼロ)。採否・explore 枠は 09-18 edge-supply-scan-monthly の A/B/C 統合裁定。台帳登録案 = #26 `statement_ladder_intervention_prob`。family B (介入イベント→回避/執行) は別 family として E-C 符号逆 prior を継承させる設計指示のみ記載

- **`info`/`conditional_info` 型が dispatch で無条件に `WATCHING` を返すハードコードだった** ([[lesson-trigger-reachability-evaluator-2026-08-19]])。`condition` フィールドの発火条件は **一度も評価されず**、条件が成立しても TRIGGERED にならない設計。ZN 教訓 (「条件を書く」と「条件が起こりうる」は別物) の **4 例目、初の評価器レベル**
- **実害**: `statement-ladder-foundation-readiness` は条件 (当局発言ラダー基盤の main 着地) が **PR #194 (`569dbe3f`) で既に成立済み**だったのに watching 表示のまま滞留。同トリガは family A (発言ラダー→介入確率) の pre-reg 起草ゲート = **能動測定ライン 0 本の状況で唯一動かせる供給ライン作業が黙って停止していた**。`deadline` も無視されており、期日付き手動エントリ (`volstate-split-*` / `carry-dip-v3-revival-watch`) は自分から期限切れを名乗れなかった
- **機械評価型 2 種を追加**: `artifact_presence` (glob + `min_files` の実ファイル判定 =「main に着地したら発火」型) / `data_coverage` (cache 被覆 max 日付 vs 閾値 =「cache が延伸したら発火」型)。取得不能は従来どおり `DATA_UNAVAILABLE` で cron を落とさない
- **`evaluate_manual_info`**: 手動判定エントリでも `deadline` 超過で TRIGGERED (`no-deadline` は無期限 watching のまま)
- **到達経路 lint** (`lint_reachability` / `--lint`、pytest 強制): 機械評価型でないエントリは `reachability` (誰/どのジョブが状態を進めるか) の明記を**必須化** — 5 例目の再発防止本体。現行 registry 違反 0 件
- **`statement-ladder-foundation-readiness` = TRIGGERED → resolve 済み** (会見 corpus 56 月次 jsonl / lexicon ladder スコア / forward 日次 cron を実ファイルで確認)。**family A の pre-reg 起草ゲート解除** — 09-18 スキャン (`edge-supply-scan-monthly`) の A/B/C 統合裁定の前提材料が揃った。⚠️ 基盤は**収集のみ**、発言×介入×価格のジョイント測定は別 pre-reg の観測前 LOCK まで禁止 (MoF #4 cross-LOCK 継続)
- `ws3-round4-eur-divergence-conditional` を `data_coverage` へ移行 → 実測表示 (被覆 2026-08-18 / 閾値 2026-11-15) に変化、延伸経路の実在も同時確認
- live/tier/lot 変更ゼロ。test 7 件新設 + 旧 pin 1 件を現行設計へ更新 (2645 passed)

## 2026-08-18 — feat(data): MoF 通信モダリティ収集基盤 — 介入 ground-truth / 会見 transcript / lexicon ladder / GDELT (rule:R3)

- **新データモダリティ (当局コミュニケーション) の収集基盤を新設** ([[mof-communication-data-infrastructure]]、`data/external/mof_statements/`)。起点 = user 介入主張のスコーピング wf_32d378df (MEMORY `user_manual_edge_usdjpy_carry_2026_08_12` 追記4) — 主軸は「発言ラダー lexicon × 公式介入ラベル」、**X は ToS 上不使用**
- **⚠️ 収集のみ**: 発言×介入×価格のジョイント測定は別 pre-reg まで全面禁止 (MoF #4 cross-LOCK)。価格データ不使用・2026 介入日の価格推定なし (P-10 遵守)
- **介入 ground-truth**: 公式日次明細 CSV (1991-04〜) を正規化、凍結 legacy `mof_interventions.csv` と**行単位 383/383 完全一致**。新規 = 2026 Q2 開示 3 行 (04-30/05-04/05-06、Σ¥11,734.8bn ≒ 月次総額と符合)。**2026-06-29〜07-29 月次窓 = 介入額 0 (公式)**
- **会見 corpus 502 会見 (2022-01〜2026-08)**: online 387 + NDL WARP 115 (pywb `id_` 原本、旧 `.htm` 対応)。**MoF index の欠落 8 ヶ月 (202310-12/202601-04) から未リンク孤児 62 会見を日付総当たりで回収** (神田財務官単独会見 2 本を含む)
- **lexicon ladder v1** (`tools/mof_statements_lexicon.py`、Gnabo 系 talk/act 離散化 L1-L5 + no_comment、大臣側発言のみスコア、テスト 19 本): 目視検証 **PASS** — 2022 窓 (L0-2→09-02 L3→09-29 L4→10-03 L5) / 2024 窓 (L0→03-26 L3→04-02 L5) の両方でエスカレーション可視 (詳細テーブル: `reports/mof_statements_backfill-2026-08-18.md`)
- **forward 日次 cron 新設**: `tools/mof_statements_daily.py` + `.github/workflows/mof-statements-daily.yml` (JST 06:30 — 介入 CSV/会見/news.rss/GDELT、月ページ欠落時は日付プローブへ自動フォールバック)
- **観察事実**: 公式 CSV に 2026 Q2 日次明細が着地済み (08-07 公表) = **#4 pre-reg の verdict 期日 (着地+10 日) 超過中** → verdict 執行を別タスクとして起票 (本基盤では E-A/E-C 量を計算していない)

## 2026-08-18 — feat(automation): family C アンカー自動化パケット — 日次データ基盤 + E-A defensive alert + registry トリガ 3 点 (rule:R3)

- **user 承認 (2026-08-18「自動化させて」) の 3 点パケット** ([[family-c-anchor-automation-2026-08-18]])。live/tier/lot 変更ゼロ、シグナル計算ゼロの純データ基盤 + defensive monitoring
- **① rate-anchor-daily**: `tools/rate_anchor_ingest.py` + 平日 21:15 UTC workflow — MoF JGB 15 テナー (歴史+当月英語版) / FRED DGS1-10 / ZN=F 日足を `data/external/rate_anchor/` に union-merge 蓄積 (単調性 assert、決定的 manifest)。凍結 e20 パネルには非接触。シード済み: JGB 3,328 行 (→08-17) / US 3,554 行 / ZN 756 行。**材料のみ — フェアバリュー帯/乖離の計算は family C pre-reg まで構造的に不実施**
- **② intervention-watch**: `tools/mof_intervention_watch.py` + 00:20 UTC workflow — #4 §2.2 凍結 rule (X,Y)=(2.0, 0.25%) **as-is** で前 UTC 営業日を評価、candidate=1 で Discord 通知 + `knowledge-base/raw/intervention_watch/` JSONL 記録 (dedup 兼用)。**監視のみ — live gating 自動執行は不実装 (§5.5 Variant B = 別 pre-reg + user 承認)、candidate ≠ 介入ラベル、alert-grade (yfinance 1h) と verdict-grade (Massive 15m) を grade フィールドで分離**。test pin で order 系 import を構造遮断
- **③ registry トリガ**: `mof-monthly-total-2026-08-29-check` (user 7月「介入をくらった」説の答え合わせ、着地当日 user 報告) / `statement-ladder-foundation-readiness` (family A 基盤、並行 task_a3b5b005) / `edge-supply-scan-monthly` 増補 (09-18 = A/B/C 統合裁定)。**全トリガに到達経路を明記** (ZN 教訓)
- test 22 件新設 (`tests/test_rate_anchor_ingest.py` / `tests/test_mof_intervention_watch.py`) + registry pin

## 2026-08-17 — research(E22): VRP explore ❌ FAIL (IC −0.025 p=0.760、OOS 非接触) — vol モダリティ恒久クローズ (rule:R1 手続き、台帳 #24)

- **E22 (通貨 VRP = EVZ−RV21 × EUR_USD × 21bd 時系列 IC) の凍結 explore を単独 wave で執行** ([[e22-vrp-explore-prereg-2026-08-17]]、scan 第 3 次 §2/§2.1 の explore 枠 1/3)。敵対的検証 GO-WITH-CONDITIONS (17 条 / blocking 10 条) 全消化 → 🔒 凍結 `f50b680a` → two-pass 測定
- **verdict = explore FAIL (gate C+D+F 同時不通過)**: 両側 circular-shift p = **0.760**、IC = **−0.0249 ≈ 0** の完全 null (N=2,066 / 非重複窓 98)。stressed-net は adverse **−11.2p**・point 端でも **−3.1p** — **swap −16.2p が gross +8.9p を支配** (21bd hold の事前記録どおり)。年次符号 5/8・LOYO 7/8
- **クローズ範囲 (凍結どおり発効)**: 通貨 VRP 全変種 × G10 × 日次〜月次 + 無料 proxy (EVZ/VXFXICLS) — **E24/E25 棄却と合わせ vol モダリティ恒久クローズ、生存モダリティ 6→5 系統**。power caveat 凍結済み (FAIL ≠ falsified、検出力 8–17%、引用は estimand 監査必須)。復活 = 有償 OTC 面 + 新 family + 新敵対的検証のみ
- **§2.1 事前コミット節の帰結執行**: OOS 2022-01..2025-03-11 非接触封印 / **Databento 有償調達の user 決裁は不要化** (PASS 時のみの決裁点だった) / 無料で vol モダリティに白黒 = 主目的達成。外部/新規 family 系統の explore→OOS 生存 **0/16** に更新
- **副産物**: EUR_USD 15m の **2020-10-23..11-16 MASSIVE ベンダー穴を OANDA mid backfill で修復 (+1,440 行、米大統領選挙週回収、`tools/e22_gap_backfill.py`)** — 敵対的検証が実測発見した未開示穴。EVZCLS.csv (FRED、確定終了系列) を git 追跡化 + sha256 manifest 凍結
- **能動的に動かせる供給ラインは E21 (帰属分解、user 決裁 registry 08-31) のみに** — 残りは全て calendar-lock (E12 2027-02 / E1 10-15 / #22 ECG 11-06)。E23 はゲート解除済み (起動判断は次スキャン)。live/tier/lot 変更ゼロ

## 2026-08-17 — research(E7): phase-1 verdict ❌ FAIL (discovery 0/24、OOS 非接触) — イベントモダリティ枯渇、E12 格上げ (rule:R1 手続き)

- **E7 phase-1 (指標サプライズ directional) を期日前倒しで執行** (凍結期日 08-21 の 4 日 / verdict 08-28 の 11 日前倒し、[[e15-e7-event-modality-prereg-2026-07-18]] §13、PR #182)。排他 claim = queue ticket + draft PR (race 対策の初適用)
- **verdict = FAIL (discovery 段)**: §5b 選抜通過 **0/24 → m₁=0**。実効空間 (θ=0.5、12 combo) は time-exit EV 全て負 (−0.31〜−8.15p/trade、N 287–416、blocks 41–62) — power 不足でなく**サプライズ方向 drift の符号が系統的に逆** (発表後 overshoot 回帰と整合)。SIGN-FLIP は §6 事前宣言どおり記述記録のみ (fade 追試 = 新 family + 敵対的検証、phase-0 CPI fade C5 が負の prior)
- **OOS 窓 (2024-01〜2026-06) は結合統計未接触のまま保存**。θ=1.0 は §3.3c 予告どおりゲート機械脱落
- **機械ガード全 green**: parquet 台帳再現 13/13 / census-e7 が §3.3c pre-flight と完全一致 (41/62/22/31、19/16/8/5) / 符号・estimand の手計算 spot check (2020-06-05 NFP z=+30.79 × USD_JPY、+10.46p 一致) / self-test 24-combo 結線
- **§8 固定分岐発動: 両 phase PASS=0 → イベントモダリティ (カレンダー/サプライズ × M15 spot) を枯渇と判定、E12 (CME volume flow、first look 2027-02-05) を供給ライン主候補へ格上げ**。E23 (中銀声明テキスト、E7 verdict までゲート) は本日からゲート解除 = 台帳の次回評価対象
- ハーネス: `event_modality_explore.py` に discovery-e7 / census-e7 / self-test-e7 モード追加 (lib 変更ゼロ — E7_HORIZONS/uncond rule は設計時から準備済み)。test pin 4 件新設 (`tests/test_e7_phase1_explore.py`)。registry `e15-e7-event-prereg-phase1-verdict` resolved

## 2026-08-14 — research(scan): 月次外部仮説スキャン第3次 + 四半期モダリティ棚卸し + ZN=F キャッシュ構造欠陥修復 (rule:R3)

- **月次スキャン第3次を期日 (08-18) の 4 日前倒しで実行** ([[external-hypothesis-scan-round3-2026-08-14]])。起動理由 = WIP 原則は名目 3 系統で充足していたが、**実態は 5 系統すべて calendar-lock 待ちで探索アクティブ枠 0/3** が 9 日間継続していた。「在庫はあるが着手可能な仕事がゼロ」は WIP 原則が防ごうとしている状態そのものと判定
- **裁定**: 採用 2 / 保留 1 / 棄却 2 — **E21 human_signal_stream (user 手動実績の帰属分解、S2 診断枠)** + **E22 通貨 VRP (IV−RV、explore 枠 1/3・条件付き)** / 保留 E23 中銀声明テキスト (E7 verdict 08-28 までゲート、multiplicity 二重取り回避) / 棄却 E24 global vol risk (2026 年新研究が horizon >3ヶ月を再確認 = round-2 の E17 棄却を補強)・E25 synthetic vol surface (Yahoo 価格由来 = 価格モダリティ再着せ替え、E13 同型)
- **E22 の事前コミット節を on-record 化**: explore/OOS は**無料で完結**する (EVZCLS 実測 4,529 行、OOS 終端 2025-03-11) が、**forward の無料経路はゼロ** (EVZCLS 廃止確定 / `^EVZ` delisted / CME scrape は ToS 禁止 / Databento 有償)。よって **PASS = 「live 実装承認」ではなく「有償データ調達の user 決裁点に到達」の意味のみ**。user が調達しない判断をした場合に設計を緩める再訴訟を禁止。枠を使う正当化 = 無料で vol モダリティに白黒がつく非対称
- **E21 のスコープ制限**: estimand は 4 分解 (swap / spot ドリフト β / タイミング残差 α / サイズ寄与) の**会計**であって WR 統計ではない (MEMORY 明示指示)。**M2/M3 直接寄与は小さいと前置** (無レバ carry +0.3-0.4%/月、20%/月には ~25x = unwind 即死)。α≈0 でも human-signal-stream 系統を恒久クローズできる情報価値がある
- **四半期モダリティ棚卸し (初回)**: 閉鎖判定の巻き戻し **ゼロ** (12 モダリティ全て前提有効、うち E17 は新研究で強化)。**生存モダリティは 6 系統のみ、うち能動的に動かせるのは E21/E22 の 2 系統だけ**と確定
- **入手性 re-check で 2 件悪化・1 件構造欠陥を検出** — 悪化: EVZCLS 右端 2025-03-11 で確定終了 / VXFXICLS 2022-02-11 終了。**構造欠陥 = ZN=F 1h キャッシュ (下記)**
- **ZN=F キャッシュ構造欠陥 (R3、本 PR で修復)**: `modules/yield_data.py` が rolling 窓 API の結果でキャッシュを**無条件 overwrite**。`interval="1h"` は period=60d を選ぶため、**一度呼べば 12,760 行が 1,162 行に潰れる**。しかも **2024-02-18→2024-03-21 の約 1 ヶ月は既に yfinance 窓外 = ファイルにしか存在しない**。修正 = `merge_bar_cache()` で union-merge (行数単調非減少 / 重複は fresh 採用) + 1h period を 730d へ + **test pin 7 件**。実行結果 **12,760 → 14,175 行 / 右端 2026-05-15 → 2026-08-14、左端 2024-02-18 保持**
- **到達経路のない registry 条件を是正**: `ws3-round4-eur-divergence-conditional` の発火条件 (cache が 2026-11-15+ へ延伸) は、**キャッシュを伸ばすジョブが存在しなかったため構造的に到達不能**だった (毎日 "watching" 表示は健全性の証拠にならない)。`.github/workflows/zn-cache-refresh.yml` (週次 UTC 月 06:40) を新設して伸長経路を実在させた
- **教訓ページ**: [[lesson-rolling-window-cache-overwrite-2026-08-14]] — rolling 窓 API のキャッシュは union-merge が既定 / 条件付きトリガ登録時は到達経路を message に明記する
- **パイプライン運用規則の追補**: WIP 充足判定は「S1-S4 の本数」ではなく **「今日着手できる本数 ≥1」** で行う ([[edge-development-pipeline-2026-07-18]] §5)
- **registry**: `edge-supply-scan-monthly` 期日 08-18 → **09-18**、`ws3-round4-eur-divergence-conditional` に修復注記
- **評価への影響: なし** — live / tier / lot / Kelly は一切不変更 (純研究 + データ基盤)

## 2026-08-12 — docs(KB): ps_aud_jpy demote 可否 user 決裁 — 見送り採択、LOCK watchdog に委任 (rule:R2 手続きクローズ)

- **user「進めて」(2026-08-12) で推奨案採択**: 549250 (−123.2p) 事故起点の demote 提案 ([[mc-ruin-dashboard-artifact-2026-08-05]] #3) は **demote 見送り** — LOCK 済み基準 (watchdog Live N≥10 EV<0 / N=15 Wilson<0.40 / 2週連続 EV<0 / catastrophic SL率>30%) が唯一の判定器。horizon 損失 cap の R1 amendment は起案しない
- 決裁時状態: 08-04 以降 ps 発火ゼロ (live N=2 のまま、前提不変) / watchdog cron 稼働中 (監視主体併設要件充足)。以後の ps 判定は完全自動 — これで 549250 事故の全 disposition がクローズ
- **評価への影響: なし** (live/tier/lot 全て不変更 — 現状維持の正式化)

## 2026-08-12 — docs(KB): ps carve-out 復帰初週 再ゲート disposition — 席枯渇で初週窓は無効、#172 後へ再アンカー (rule:R3)

- **registry `ps-carveout-firstweek-regate` (期日 08-11 超過で stale 点灯) を決着**。**demote せず** — pre-reg 条件 live N≥10 に対し実測 **N=2**。N ゲートを事後に下げることはしない。詳細: [[ps-carveout-firstweek-regate-disposition-2026-08-12]]
- **実測 (本番 `/api/demo/trades`、date_from=07-28 の 1,427 行)**: ps 行 **8** (全て `price_shock_rev_aud_jpy_h1_long` / AUD_JPY / BUY)、うち **clean live 2** (`oanda_trade_id != '' ∧ dedup_violation != 1`) / shadow 6。他 4 セルは発火ゼロ。live 実績 = 07-29 **+0.6 (WIN)** / 07-31 **−123.2 (LOSS)** = 計 −122.6p
- **(a) AGG_KELLY BYPASS 監査 → carve-out は機能、初週の律速は「席」**: Render app ログ (07-29〜08-01) に AGG_KELLY block はゼロ。支配的なのは `[SHADOW] Slot bypass: price_shock_rev_aud_jpy_h1_long ... (live=1/1 shadow=1/2 → shadow)` で **13 分間に 16 行** = live 席が埋まり ps が shadow へ迂回。**初週の N 不足は carve-out の失敗ではなく席供給の枯渇** → **PR #172 (merged 08-11) で是正済み**。よって初週窓 (07-28〜08-11) は carve-out の EV を測る窓として**無効**と判定し、評価窓を #172 後へ再アンカー
- **(b) exit 分布 → ✅ BE_LOCK OFF 実効**: clean live 2 件は**両方 `close_reason=horizon`** (早期 BE/trail exit なし)。N=2 のため「2/2 一致」水準の証拠と明記。`SL_HIT` ラベル衝突 (2026-08-07) の影響圏外
- **(c) estimand 整合 → ⚠️ 潜在的不整合・現時点の影響ゼロ**: `price_shock_rev_live_watchdog.py` (N≥10 で auto DEMOTE) と `price_shock_rev_promote_evaluator.py` (N≥30 で lot ramp 提案) は非 canonical な **`is_shadow=0`** で live 判定し `dedup_violation` 除外を持たない (KB 規約は `oanda_trade_id != ''`)。**ただし実測乖離ゼロ** — 06-01 以降 7,761 行で `is_shadow=0 ∧ oanda_trade_id 空` = **0 件**、`dedup_violation=1` は shadow 側のみ。**バグとして起票せず**、canonical 判定へのハードニングは別タスク (auto-demote を握るため単独 PR + test pin)
- **registry**: 初週エントリを resolved 化 + 後継 **`ps-carveout-regate-post-172`** 新設 (`live_count_decision`、prefix 一致、since 2026-08-11、N≥10 で EV/Wilson 再判定、backstop 2026-09-30。期日で N<10 なら供給側の別問題として stale レビュー)
- **live パラメータ / tier / lot は一切不変更**。M1 見通しも不変 (wg + ps の live N 蓄積待ち)

## 2026-08-12 — research(E7): phase-1 pre-flight — サプライズパネル凍結と power 開示 (θ=1.0 の 12 combo が結果観測前に脱落) (rule:R1)

- **pre-reg §11 の 2026-08-14 マイルストン (FF gap scrape + データ付録凍結) を 2 日前倒しで完了確認**。§3.3c として追記 ([[e15-e7-event-modality-prereg-2026-07-18]])。**価格データ非接触・イベント×リターン結合統計は未計算** (§10-1 遵守) = 結果観測前の記録
- **価格側 pre-flight**: `e15_e7_data_refreeze.py --verify-only --root <repo>` = **13/13 OK** (台帳 3 点再現)。discovery (08-21) / OOS verdict (08-28) の BLOCKED 要因なし
- **サプライズパネル新設** `tools/e7_surprise_panel.py` — §6 の z = (actual − consensus)/σ_trailing (直近 24 releases、strictly trailing) を機械化。canonical NFP 149 / CPI 149 × R4F forecast × actual (R4F 231 + BLS first print 66、**欠落ゼロ**)。成果物 = `raw/bt-results/e7/e7_surprise_panel.csv` + `e7_surprise_coverage.json`
- **block 実測 (block = イベント、primary 7 ペアが同時発火 → N ≈ blocks×7)**: NFP discovery θ0.5 **41** / θ1.0 22、CPI discovery **62** / 31、NFP OOS **19** / 8、CPI OOS **16** / 5
- **帰結 1 — θ=1.0 の 12 combo は結果を見る前に構造的脱落**: 4 セル全てで §5b(iii) ≥40 も §5c B(d) ≥15 も不達。選抜の必須条件なので**凍結候補にすらならない** → 実効候補空間 **24→12 combo (θ=0.5 のみ)**。**grid/θ/ゲート/α 会計の定義は一切変更していない** (§10-2 遵守、これは可用性の開示であって設計変更ではない)
- **帰結 2 — NFP θ=0.5 discovery は knife-edge (41 vs ゲート 40)**: イベント 1 件の増減で NFP 系 6 combo が消える。ゲート値は凍結済みなので動かさず、凍結表に脆さを併記する規約を宣言
- **帰結 3 — modal 予想を事前記録**: OOS blocks 19/16 → 検出可能平均効果 ≈ 0.33σ_h (NFP) / 0.36σ_h (CPI) = 大効果のみ。**phase-1 の modal outcome も C3 (UNDERPOWERED) または C5** と今宣言 (結果後の言い訳封鎖、phase-0 §9 と同規律)
- **σ_trailing warm-up の帰結 (規則から機械的、裁量ゼロ)**: 各系列の最初の 24 イベント (2014-01〜2015-12) は z 不定で discovery から自動脱落 (120→96)。R4F データ開始が 2014-01 のため pre-2014 充当は不可能
- **除外は宣言済み 1 件のみ**: CPI/OOS の 2025-12-18 (forecast 欠落、§3.3b-6(i) で観測前宣言)。事後裁量による除外ゼロ。§8 DEFERRED 条件は不発 (13/13 ペア OK)
- **test pin** `tests/test_e7_surprise_panel.py` (7 tests): 単位規約 / strictly-trailing σ / **look-ahead canary (未来 release 差し替えで過去 z 不変)** / block ゲート / 実測 block 数の回帰 pin。live/shadow/Kelly/tier は**一切不変更** (純研究)

## 2026-08-09 — fix(live): DT `ctx.hour_utc` が live で 12 に凍結 — 全DT戦略の時間帯ゲートが BT と別物だった (rule:R3)

- **`t9-kalman-d7-fire-info` の 0-fire (実測 0.00/週 vs 期待 3.9/週) の分母調査から発見**。`compute_daytrade_signal` の DT 用 `SignalContext` 構築が `bar_time` 不在時に `hour_utc=12` / `is_friday=False` へ固定フォールバックしていた。**`bar_time` を渡すのは BT 経路のみ** (`app.py:6679/7121`)、**live 経路 (`demo_trader._tick` → `compute_fn(df, tf, sr, symbol)`) は渡さない** → live の DT 全戦略が「常に UTC 12:00・常に金曜でない」前提で時間帯ゲートを評価していた。潜伏 **123 日** (`9c849cef` 2026-04-08 の DT構造改革で再混入。2026-04-04 に同型バグを一度修正済み = **回帰**)
- **証拠 3 系統**: ① code derivation (live 呼び出しが位置引数 4 つ)、② **本番 QUALBAR 実測** — `[kalman_d7] QUALBAR` 12 行が実バー 03:00〜21:15 UTC に散らばるのに**全行 `hour=12`**、③ **自然実験** — `ctx.hour_utc` 直読み群は BT 窓外発火 **83/237 = 35.0%**、`df.index` から自前導出する回避策を持つ群 (turtle_soup / london_session_breakout の redesign_v2) は **0/28 = 0.0%**、**Fisher exact one-sided p = 1.32e-05**
- **実害**: (a) h=12 が窓の穴に落ちる戦略 = **live 発火が構造的に不可能** — kalman_d7×3 variant (LIVE 化から **73 日 0 fire**)、pd_eurjpy_h20 (h==20)、tokyo_range_breakout (7-9)、london_ny_swing (13-17)、tokyo_nakane (00:45-01:15) は shadow N すらゼロ = **探索母集団から消えていた**。(b) h=12 を通す戦略 = 時間帯ゲート常時開放 — squeeze_release_momentum は発火の **86.7%** が BT 窓外、liquidity_sweep 50.0% / inducement_ob 26.7% / trendline_sweep 8.4%。(c) `is_friday` が常に False → **金曜ブロック (`FRIDAY_BLOCK_HOUR` 13〜18) が live で一度も作動していなかった**
- **Rule 3 根拠 = 同一関数内の内部矛盾**: 4 行上の `is_trade_prohibited` は当初から `bar_time if bar_time else datetime.now(timezone.utc)` と正しく降りており、scalp が使う `SignalContext.from_df` も `bar_time → row.name → now()` と正しい。**壊れていたのは DT 経路の直接コンストラクタ呼び出しだけ**。統計的新規主張ではないため 365日BT 不要
- **修正**: DT ctx の時刻導出を `bar_time → df.index[-1] → now(UTC)` に統一 (naive は UTC 扱い / aware は UTC 正規化)。`modules/data.py` が fetch 経路 index を UTC 正規化済みのため live の `df.index[-1].hour` は UTC 時刻。**BT 経路の契約は不変** (明示 `bar_time` が最優先)
- **監視配線バグも同時修正**: 退避条件を載せようとした `prereg_trigger_watch` の `live_count_decision` が `match: prefix` を `fetch_live_count` へ渡しておらず、kalman (1セル=3 entry_type) の live 件数が**恒久的に 0 = 監視が沈黙**する状態だった (T5 の 18 日執行ギャップと同型)。`count_live_matching(prefix=)` を shadow 側と同契約に
- **回帰 pin**: `tests/test_dt_ctx_hour_utc_live.py` (9 tests、**修正前ソースで 7 件が落ちることを検証済**) + `test_prereg_trigger_watch.py` に prefix/配線テスト 2 件。全 suite 2561 passed / `check.py` 全9チェック通過
- **修正の作用方向**: 制限側 (trendline_sweep / squeeze_release_momentum / inducement_ob / liquidity_sweep / post_news_vol / ema200_reversal) = **BT 検証済み設計への復帰で安全**。開放側の大半は shadow のみ = **N 蓄積の回復** (原則4)。唯一 **kalman_d7 は `KALMAN_D7_LIVE_ENABLE=1` (本番 effective) のため live 発火が始まる** — ただし 2026-05-28 に user が option B で明示決裁した設計 (lot 0.5×) を初めて実際に動かすものであり新規昇格ではない (Rule 1 対象外)。決裁時の退避条件を機械監視に載せるため registry に `t9-kalman-d7-live-n10-ev-check` (live N≥10 で EV 判定、期日 2026-11-30) を新設
- **既存判定の訂正**: [[pre-reg-kalman-d7-shadow-fire-recovery-2026-05-28]] §6.5 の「INCONCLUSIVE = 設計対象外局面」は**誤診**と確定 (DIST fail は事実だが、通過していても session gate で必ず落ちていた)。**live/shadow 発火数に依拠した過去判断は本バグの影響を受ける**が、BT/探索側の verdict (WS3 の lfr / htf_fb / T10 / T11 等) は `bar_time` を持つため**影響なし**
- **評価への影響**: tier/lot/live 送信可否は**不変更**。clean live 負エッジ (−242.6p / payoff 0.274) の説明変数が 1 つ増えた (エッジ消滅ではなく執行窓の逸脱による寄与) — 分離定量は修正デプロイ後の N 蓄積待ち。詳細: [[dt-ctx-hour-utc-live-freeze-2026-08-09]]

## 2026-08-07 — fix(live): `SL_HIT` ラベル衝突 — 勝ち決済が SL 狩り防御を発火させていた (rule:R3)

- **08-05 daily 提起の「`SL_HIT` の 46.2% が正 PnL」を解決。汚染ではなく「ラベル衝突」**: `close_reason="SL_HIT"` は「**現在の** SL に価格が触れた」の意味しかなく、BE-lock / トレーリング / Profit Extender が SL を entry より利益側へ動かした後の**利確 exit** も同じラベルになる。データは正しく、名前と下流の解釈が誤っていた
- **本番実測 (N=3308, `/api/demo/trades`)**: SL が**利益側** 1894 本 → 97.6% が正 PnL (中央値 +2.00p / MFE 中央値 5.70p) / **リスク側** 1414 本 → 99.6% が負 PnL (中央値 −6.95p / MFE 0.00p)。**誤分類 1.5%** = SL 位置は事実上完全な判別子。`outcome` 内訳 = **WIN 1792 (54.2%)** / LOSS 1441 / BE 75。08-05 の 46.2% は小標本 (106本) ゆえの**過小評価**だった
- **実害 (live 挙動)**: `_sl_hit_history` を消費する防御 2 本が「ストップ狩りに遭った」前提で動く — ① **cascade cooldown** = 同一ペアの**全戦略**を 45–600s ブロック、② **Fast-SL 適応防御** = 次エントリーの SL を ATR×0.3 拡大。**発火イベントの 54.2% が勝ち由来の誤発火** (Fast-SL 側は 315 件中 180 = 57.1%)。誤発火は USD_JPY 494 / GBP_USD 444 / EUR_USD 306 と**主力ペアに集中**し、4原則 #1「攻める」/ #4 に反していた
- **Rule 3 根拠 = 設計の内部矛盾**: 同じ close 経路の**直前**のブロック (`if outcome != "WIN":` → `_last_exit` / `_total_losses_window`) が「SL 後の再エントリー防止」という**同一目的で既に WIN を除外**しており、隣接する 2 ブロックが非対称に書かれていた。統計的新規主張ではないため 365日BT 不要
- **修正**: ① `demo_trader.py` の履歴記録を `close_reason=="SL_HIT" and outcome != "WIN"` に (BE 75 本は逆行スイープの証拠として**防御に残す**ため `=="LOSS"` ではなく `!="WIN"`)、② `learning_engine.sl_losses` / ③ `daily_review.sl_hits` を `outcome=="LOSS"` で絞る — 両者は「SLヒット率 >60/70% → **SL幅拡大検討**」を焚く advisory で、生カウントでは **82.7%** (真の損切り率 **36.0%**) となり勝ちの多い book に SL 拡大を勧めていた。④ 回帰 pin `tests/test_sl_hit_history_win_guard.py` (4 tests、修正前ソースで落ちる負のコントロール検証済)
- **意図的に見送り**: `close_reason` の改名 (`TRAIL_EXIT` 等) は既存 3308 行と全 BT/分析ハーネスの estimand を非可換に壊すため**しない** — ラベル据え置き・消費者側を正す方針。shadow 行の混入是非 (誤発火 1792 件中 1786 が `is_shadow=1`) は scope 外で継続課題
- **波及**: `shadow_demote_registry.py:40` の demote 根拠「SL_HIT 56.2%」は本汚染値そのもの → 再検討要 (保守側ゆえ緊急性なし、R2 で別途)。**今後 `close_reason` 起点の分析は `outcome` 分割を前提とすること**。MEMORY `project_be_trail_inflates_python_bt_wr` と同一機構が live 側にも出ていた
- **評価への影響**: tier/lot/live 送信可否は**不変更**。変わるのは防御の誤発火が消える点のみ (エントリー機会の回復方向)。詳細: [[sl-hit-label-collision-2026-08-07]]

## 2026-08-05 — fix(bt): daytrade/scalp BT phantom-loss 記帳修正 — LOSS を実効ストップ基準に (rule:R3)

- **R3 調査完結**: sr_anti_hunt×EUR_JPY BT の 05-05 WR84.9% → 08-05 WR0.0% 反転は **regime ではなく `d87d5b6c` (2026-05-15) の `_BT_ABLATE_BE_TRAIL` default 反転**が直接原因。加えて **phantom-loss 記帳バグ**を発見: time-decay tightening (MAX_HOLD×50%) で entry まで引き上げた stop の退出 (実損≈0) を、`actual_sl_m` が「fut_close >元 SL 時のみ設定」のため planned `sl_m` のフル損失で計上。anti-hunt 系は BT の SL 再計算 (QH 前 TP距離/1.2) で sl_m=6.5〜11 ATR となり **1 件 −8.3R 級の架空損失** (trade dump で bars_held 12-17 集中 + actual_sl_m: null 全件を実証)
- **修正**: daytrade/scalp 両エンジンの LOSS 記帳を実効ストップ (`_dt_current_sl`/`_current_sl`) 基準化 + gap なし分岐でも actual_sl_m 必須設定。tools/sr_anti_hunt_bounce_shadow_bt.py `_pnl_r` の `or 1.0` falsy ガードが正当な 0.0 を coerce するバグも修正。run_backtest(1H)=非発現 / run_1h_backtest=既に close-based で対象外。回帰 pin `tests/test_effective_stop_loss_booking.py` (4 tests)、全 suite 2521 passed
- **判定への影響**: 08-05 cell BT の **EV_R=−8.30 は引用禁止** (gate FAIL 結論と forward 枠は不変)。05-05 の WR84.9% は optimistic 虚構 (BE 退出→+0.6×TP credit) で同じく引用禁止。**ablated BT の WR は wide-TP (≳3ATR) 戦略で構造的 ≈0 → wilson_lo 型 R1 ゲートは TP≲2ATR geometry 限定、wide-TP は TV Pine / shadow live で判定**。d87d5b6c 以降の daytrade/scalp BT 絶対 EV は decay-LOSS 比率×sl_m に比例して過大悲観 (相対比較は方向性有効)。詳細: [[bt-harness-effective-stop-booking-2026-08-05]]
- **評価への影響**: live/shadow/tier/lot/Kelly 全て不変更 (BT 評価ロジックのみ)

## 2026-08-05 — docs(KB): ロット階段 R1 パケット標準テンプレ事前凍結 + 計算ツール (rule:R3、live 変更ゼロ)

- **セル・ポートフォリオ論 (user 合意 2026-08-05) 執行項目②**: G3 到達セルの lot 昇格手続きを事前凍結 — [[lot-ladder-template-2026-08]]。標準階段 L0 1000u → L1 5000u → L2 10000u → L3 30000u、昇格 = 段ごと R1 + user 承認 (SLA 48h) / 降格 = R2 自動 (D1 slippage / D2 at-rung 出血 / D3 disaster / D4 合成 DD 4/6/8% NAV / D5 Wilson gate 割れ) の非対称を凍結
- **推奨 lot = min(6 上限)**: half-Kelly 2 基底 (本番 `kelly_fraction` 式同期) / worst-case イベント損失 ≤2.5% NAV / 証拠金 worst-case 同時 ≤40% NAV (25x) / exposure 20k cap / MC P(セル DD>2% NAV, 12mo)≤5% (`monte_carlo_ruin` JPY 建て)。台帳は broker 実約定 JPY のみ (D-a/D-e 整合)
- **計算ツール**: `tools/lot_ladder_calc.py` (§8 パケット機械生成、手計算禁止) + `tests/test_lot_ladder_calc.py` (25 tests、テンプレ worked example を数値 pin)
- **wg 事前充填の主発見**: ① Wilson gate (D-d 拘束) は wg 級統計で **N_required=41 > G3 の 30** = G3 到達≠即増額、② wg の binding constraint は Kelly でなく **disaster SL 150p** (U_cellDD ≈ 5.4k → L1 が実質上限 @NAV 326k)、③ 3 ペア同時セルの L2+ は exposure 20k cap 改定 R1 同梱必須。単一セル垂直増額では thesis に届かない = セル 2〜5 本の合成が必要という算数を再確認
- **評価への影響: なし** — 全セル lot/tier/live 経路不変更。第 1 適用は wg G3 到達時 (fill 修復前提、ETA 2027-05 @現ペース)

## 2026-08-05 — fix(risk): dashboard MC ruin の資本整合 (D-b 完結) + 549250 事故 disposition (rule:R3)

- **「MC ruin 0%→100% 反転」(08-04 daily) の解剖**: gate 側 (`_get_ruin_probability`、実際に live 送信を止める方) の実測 = **ruin 0.0** (post-cutoff 全 N=566 + JPY 整合資本 5,801p、audit に mc_ruin block ゼロ) — **運用凍結は起きていない**。100% は dashboard 専用の三重 artifact (30d n=10 窓 × 資本 1000p ハードコード取り残し × 単位不均一 pip 系列)
- **修復**: `/api/risk/dashboard` の `compute_risk_dashboard` に gate 側と同一式の `initial_capital` (OANDA_EQ_BASE_JPY/OANDA_JPY_PER_PIP_AVG) を接続 + n<20 低信頼フラグ。同一 n=10 系列で ruin **1.0→0.0**。D-b (Track C) が gate 側だけ直して dashboard 側が取り残された「同じ事実の片方欠落」の完結。pin `tests/test_mc_ruin_dashboard_capital_align.py`
- **549250 (−123.2p) disposition**: 実損 ¥1,232 = NAV 0.34%、設計 horizon exit の範囲内。#4 tp=151.25 は placeholder 設計 (バグ非該当、R3 チェック完了)。#2 live_tier_exempt は pre-reg 承認済み estimand (regime veto 追加は Post-hoc tune 禁止に抵触、変更は R1)。#7 wg 非約定 = MARKET_HALTED 確定済み (2cf940f7)。**#3 ps demote 可否は user 決裁材料として整理 (推奨: LOCK の watchdog に委ねる / 代替: horizon 損失 cap の R1 amendment)**。詳細: [[mc-ruin-dashboard-artifact-2026-08-05]]
- **評価への影響**: 表示計量の修正のみ — live/tier/lot/gate 閾値は全て不変更 (Gate2-4 は他条件で引き続き閉)

## 2026-08-05 — docs(KB): sr_anti_hunt_bounce×EUR_JPY R1 昇格判定 NO-GO → forward 確認 pre-reg (rule:R1 手続き、live 変更なし)

- **user「進めて」(2026-08-05) による R1 パケット起案を精査の結果 NO-GO 裁定**: ①起案動機 p=2.2e-11 は dedup_violation 除去 (23/67 重複 emit) 後 **EV t p≈0.094 = n.s.** に減衰、②累計 +272.4p は 2026-05 単月依存 (5月除外で −53.3p)、③live N=4 符号逆、④事前宣言ゲート付き 365d cell BT は **ハーネス整合破綻を検出** (同一ハーネスが 05-05: WR84.9% → 08-05: WR0.0%、9ヶ月重複窓で反転 = app BT パスとの機械的不整合、R3 調査タスク発行) で評価不能。vix pilot 失敗構図より弱い証拠での昇格を回避
- **forward 確認枠 LOCK**: セル凍結 = EUR_JPY×BUY / dedup=0 / 2026-08-05 以降 fresh N≥40 で 1 回限り判定 (EV>0 ∧ Wilson_lo>38.7% ∧ 月次符号≥3/4)。registry `sr-anti-hunt-eurjpy-buy-forward-confirm` (期限 2027-02-28)。中間再計算禁止 (P-10 型)。詳細: [[sr-anti-hunt-eurjpy-r1-verdict-2026-08-05]]
- **評価への影響: なし** — live/tier/lot/shadow 全て不変更。成果物 = 決裁 doc + registry + BT runner (`tools/sr_anti_hunt_eurjpy_cell_bt_2026_08_05.py`) + BT 乖離証拠 (raw/bt-results/)

## 2026-08-03 — fix(live): vix_carry_unwind×USD_JPY Overlap pilot 早期 demote (rule:R2, user 決裁)

- **決裁**: 2026-07-31 quant-eval の早期 demote 推奨を user「進めて」承認 (2026-08-03)。07-07 継続裁定の「demote は user 決裁」要件を充足、checkpoint (live SELL N≥20 or 08-31、registry `vix-sell-pilot-recheck`) を待たず執行
- **根拠 (production 実測)**: live N=26 PnL=−46.9p PF=0.66 EV=−1.80 (月次 3/4 負、07-30 −30.1p) + **shadow エッジ崩壊** 04:+537p → 05〜07 累計 −216p/n=139 → 08-01〜03 −17p/n=7。365d BT 正値 (EV=+0.506 / Overlap cell N=22 EV=+1.297) は forward で反証 — 止血判定は EV 軸・Live>BT の規律に従い demotion に新規 BT 不要 (再昇格 R1 側で要求)
- **執行**: `_PAIR_PROMOTED` 除外 (22→21) + `_PAIR_DEMOTED` 復帰 + `_PAIR_SESSION_FILTER`/`_PAIR_LOT_BOOST` 撤去 (inert だが code consistency)。MIN-lot 1000u 契約 code / agg-Kelly min-lot bypass は再昇格時のため残置。**shadow emit 不変更 (原則3)**。registry resolved 化。pin `tests/test_vix_pilot_demote_pin.py` (5 tests)、session-filter/agg-Kelly 機構テストは合成メンバーシップ化で絶縁
- **評価への影響**: 現役 live 送信経路から最大の出血源 (7月 −34.3p) を除去。残る live 経路 = wg×3 + ps×5 + Grail #1/#4 (監視中)。詳細: [[vix-pilot-early-demote-2026-08-03]]

## 2026-07-31 — fix(live): Grail #19 ny_close_reversal live 経路撤去 + shadow 含む全数 quant-eval (rule:R2)

- **quant-eval 全数監査** ([[quant-eval-2026-07-31]] = `raw/trade-logs/`): post-cutoff closed **14,329 行**を 3 バケット分解 (live 565 / shadow 13,758 / other 6)。live 月次 = 04:−230.7 / 05:**+14.8** / 06:−281.9 / 07:−84.4p。**7 月 live 反実仮想: 修正済みバグ経路 + ny_close + vix を除くと −7.6p** = M1 (月次符号転換) の残存出血源を特定
- **Grail #19 撤去 (rule:R2)**: ny_close_reversal live 経路 (N=4 登録根拠、2026-04-25) が live 0W/4L −9.7p + shadow 両ペア負 → `_GRAIL_CANDIDATES`/`_check_grail_filter` から撤去。shadow emit 継続 (原則3)。pin `tests/test_grail19_ny_close_removal_pin.py`。詳細: [[grail19-ny-close-removal-2026-07-31]]
- **勝ちセル抽出** (Bonferroni m=102): WR vs BEV 二項検定 PASS = sr_anti_hunt_bounce×EUR_JPY (p=2.2e-11) / donchian×NZD_USD (4.2e-6) / ema200_trend_rev×USD_JPY (2.6e-6) / orb_trap×GBP_USD (3.0e-4、EV t 検定も PASS)。**横断勝ち条件 = 方向片側性 + Overlap (12-16 UTC)**。母集団レベルでは confidence≥70 が WR+5.0pp (Bonf PASS、04-22 分析の負相関から反転 — KB 矛盾として記録)
- **vix pilot 証拠更新 (live 変更なし)**: shadow エッジ減衰 (05〜07 累計 −216p) + live 月次 3/4 負 → 早期 demote 推奨を戦略カードに追記、**user 決裁待ち** (07-07 裁定準拠)
- **評価への影響**: live 送信経路 −1 (ny_close Grail)。lot/tier/Kelly 不変更。shadow 蓄積は全戦略不変

- **🎉 3.5 ヶ月ぶりの初 live fill (07-29 04:44 UTC)**: price_shock_rev_aud_jpy×AUD_JPY → OANDA #549235 BUY 1000u @113.466 slip+0.8p。経路検証全クリーン — agg-Kelly BYPASS ログ実射 (D-c-1 carve-out 作動) / broker SL #549237 @112.467 (=2×ATR) + TP 付帯の二層防御 / dedup・slot 正常 / BE_LOCK・ATR-BE 不作動。**§7 免除 deploy (04:22) 後の fill = 完全な LOCK 設計 estimand 下の第 1 号** (戦略カード 現況に記録)。副次観測: broker TP に Quick-Harvest ×0.85 が適用される (988p→840p、horizon 12h では非拘束 — §7 スコープ外として記録)
- **[[mfe-be-lock-design-2026-06-03]] §8 追補**: per-strategy 詳細表 (57d 再計測、適格 9 戦略 **0/9 pass**、Bonferroni p 全 1.0、aggregate ΔEV −0.006 p=0.975) — §8 verdict FAIL の per-strategy 粒度での確定。**評価への影響: なし (記録のみ)**
## 2026-07-29 — fix(data): E15/E7 phase-1 データ前提修理 — plain 15m 台帳再現を 13/13 byte-exact 復元 + never-shorten ガード (rule:R3)

- **発見**: coverage 台帳 (`e15_e7_pair_coverage.json`, 07-21 凍結) が参照する plain `{pair}_15m.parquet` が **11/13 ペアで台帳再現不能** (各種 explore の短い `--days` フル取得による無条件上書きが原因、EUR_AUD は消失)。このままでは phase-1 discovery (08-21) / OOS verdict (08-28) が `load_and_verify_bars` で BLOCKED
- **復元**: phase-0 実行 worktree `e15-oos-20260722` に原本が現存、**phase-0 verdict data_ledger の sha256 と 13/13 完全一致** → `tools/e15_e7_data_refreeze.py --restore-from` で byte-exact 復元 + 判定器実コードで 13/13 GREEN 実証。凍結コピー `data/cache/massive/e15_e7_frozen/` + manifest `raw/bt-results/e15_e7_frozen_manifest_2026-07-29.json` (verdict と同一 sha256 = provenance 連鎖が閉じる)
- **副産物 (重要)**: MASSIVE fresh 再取得で **AUD_USD が台帳比 −25 行 drift** = ベンダー歴史バー集合は不変ではない。pre-reg データ凍結は「cache 参照 + 行数 pin」でなく**ファイル実体コピー + sha256** で行うこと
- **再発防止**: `tools/fetch_massive_data.py` に never-shorten merge ガード (既存行優先・head 保持・tail 延長のみ) + tests 8 本。phase-1 pre-flight = `--verify-only` (runbook `e15_phase0_execution_status.md` 2026-07-29 節)
- **評価への影響: なし** — 価格ファイルの復元のみ、イベント×リターン統計未計算 (§10-1 遵守)、live/shadow/Kelly/tier 不変更

## 2026-07-29 — fix(data): MASSIVE ベンダー欠損 2 区間 (2019-09/2020-10) を OANDA v20 で backfill — 45 ファイル +61,709 行 (rule:R3)

- **holiday カレンダー検証中に発見された USD_JPY の 2 窓 0 行** (2019-09-14〜10-05 / 2020-10-13〜11-14) を全ペア×全 TF に横断展開: 欠損は**ベンダー側の穴** (API 直接プローブでローカルと欠損日リスト完全一致 = キャッシュはミラー、再取得では埋まらない)。重症度はペア依存 — USD_JPY 両窓全欠 / USD_CAD・USD_CHF 2020 窓全欠 / EUR・GBP・NZD 系部分欠 / AUD 系ほぼ完備
- **修理** = `tools/massive_gap_backfill.py` (新規): OANDA v20 mid candles (dailyAlignment=0/UTC = MASSIVE alignment 一致) から**欠損バーのみ**補完。era-local (±90d) pattern guard で当時の session 慣行を保存、既存行バイト不変 assert、`.bak-pre-gapfill` バックアップ + `.audit.json` に backfill provenance、冪等。境界連続性 0.003〜0.07% (クロスソース) を検証
- **凍結物ガード**: plain `{pair}_15m.parquet` 13 本は E15/E7 pre-reg data ledger (rows_at_ledger_last 凍結、phase-1 verdict 08-28) が pin するため **backfill 恒久除外を code pin** (誤適用 6 本は .bak からバイト同一復元済み = net ゼロ)。W3 manifest の sha256 は .bak と一致検証済み。HIP-1 holdout lock (2025-11〜2026-05) は窓外
- **refresh cron が埋めない理由を確定**: `bt_data_cache.py` 差分更新は「最終バー→現在」のみ + 全量上限 180〜730d — 履歴中間の穴は構造的に対象外 (かつベンダーに無い)。詳細: [[massive-vendor-gap-backfill-2026-07-29]]
- 影響 explore 注記: gotobi = robustness 評価済み・verdict 不変 (報告書に data note) / holiday family = 凍結前に是正、pre-reg 時は backfill 済みデータで LOCK すること。**評価への影響: なし — live/shadow/Kelly/tier 不変更**

## 2026-07-28 — fix(live): price_shock_rev ×5 BE_LOCK OFF — 並行セッションと同時執行 (rule:R1)

- 本セッション (day-1 監視) 側でも [[preserve-exit-overlay-2026-07-28]] §5 案(a) を user 「進めて」承認で執行 — main には Track C **D-c-1** が先着 (5 エントリ 0.0 は同値、コメント文言のみ相違 → merge で D-c-1 表記に統一)
- 残存 delta: regression pin `tests/test_mfe_be_lock.py::test_price_shock_rev_disabled_returns_zero` (PRICE_SHOCK_REV_TIER1_TYPES 全体パラメタライズ、family 追加 drift を強制検知) + §5 決裁記録の KB 追記

## 2026-07-28 — feat(risk): Track C 資本配管修復 — ps×5 carve-out + JPY 台帳 SSOT 化 + PYR code pin (rule:R1 user 承認 + R2)

- **決裁**: [[track-c-capital-plumbing-decision-packet-2026-07-28]] を user 承認 (「進めて」= Claude 推奨案採択)。診断: [[track-c-plumbing-audit-2026-07-28]] (全クレーム code 検証 + D-a broker 実測)
- **D-c-1 (R1)**: `_AGG_KELLY_GATE_MINLOT_BYPASS_TYPES` に price_shock_rev ×5 を追加 (全席 1000u 固定契約、>1000u で自動失効) — **07-28「7席再武装」決裁が carve-out 欠落で code 上無効化されていた** (累積 Kelly −0.22 恒久負 → 次 qualify シグナルで shadow 落ち確定だった) の実効化。同時に `MFE_BE_LOCK_STRATEGY_TRIGGERS` へ ps×5 を 0.0 追加 ([[preserve-exit-overlay-2026-07-28]] §5 案(a) — R1 未通過実験レバーの live 波及遮断、estimand を LOCK 済み horizon-exit に近接)。復帰初週再ゲート registry 登録 (`ps-carveout-firstweek-regate`、08-11)
- **D-c-2 (R1)**: donchian×NZD ×2 は選択肢(ii) 採択 — bypass 追加せず gate block のまま shadow N 蓄積 (365d BT FAIL CI 全負、小 N 昇格パターン)
- **D-b (R1)**: DD defensive の SSOT を pip/1000 台帳 → **JPY 台帳** (per-close `pnl_pips × units × pip価値JPY`、母集団 = `oanda_trade_id != ''` broker 実約定 ∧ 非 XAU) に切替。D-a 実測 (実 DD 9.14% / 32,835 JPY) で再基準化 — **切替時 multiplier は 0.20x のまま不変** (現時点の防御は正当)、変わるのは回復経路 (+928p ≈ 57k JPY 相当 → +4.1k JPY で 0.40x 圏 = 恒久ロック解消)。tiers/MC ruin gate は存続、ruin 計量の資本も pip→JPY 整合 (`OANDA_JPY_PER_PIP_AVG`)。`/api/risk/dashboard` dd_status に jpy_ledger 追加・dd_pct の分母 1000 ハードコード修正 (「DD 100.8%」表示 artifact の解消)
- **R2 (D-e 調査起因)**: `_PYRAMIDING_CODE_PIN_DISABLED = True` — PYR child は demo 台帳に行を作らない構造的 orphan (生涯 N=33 / WR 9.5% / net −5,212 JPY / 同一親 6 連 fill = dedup 不全)。[[track-c-de-orphan-investigation-2026-07-28]] (`raw/analysis/`)。**30000u×7 (07-10/13) は preserve 系ではなく手動/外部クライアントと判定 — user 本人操作か要確認 (否ならトークンローテーション Rule 3)**
- tests: `tests/test_track_c_plumbing.py` +33 本 (bypass/BE_LOCK/pip_value_jpy/tier 境界/PYR pin)、`test_pyr_attribution.py` は pin monkeypatch で将来 R1 再武装用に温存。全 2,480 green
- **評価への影響**: live 送信可能セルが wg×3 → **wg×3 + ps×5** に回復 (user 決裁の実効化)。lot は全席 1000u 固定契約のまま — aggregate lot 増はゼロ。dmb×2/legacy は不変

## 2026-07-25 — fix(research): E1 供給ライン phase1b BT の join dtype バグ修正 — 14 ペア中 12 ペアが silent に 0 join だった構造欠陥 (rule:R3)

- **症状**: `phase1b_oanda_contrarian_bt.py` の日次再走が **verdict=NULL** を出し続けていたが、真因は「エッジ不在」ではなく **pandas merge_asof の datetime-unit 不一致**。MASSIVE cache refresh が 12/14 ペアの `{pair}_1h.parquet` を `datetime64[ms, UTC]` で書き直した一方、OANDA-Labs sentiment 履歴は `datetime64[ns, UTC]` のまま → pandas≥2.0 が `incompatible merge keys [0] datetime64[ms, UTC] and datetime64[ns, UTC]` で join 拒否。EUR_CHF/GBP_CHF (偶然 ns のまま) の **2 ペアだけ**が join されていた
- **根拠 (実測)**: 本番 parquet で EUR_USD/USD_JPY/GBP_USD/AUD_USD/EUR_JPY/AUD_JPY = ms → 修正前 **join 0 行** / 修正後 **394〜428 行**。EUR_CHF/GBP_CHF (ns) は 397 行で不変。sentiment 側 = ns 14,140 行
- **修正**: `join_sentiment_to_ohlc` で merge_asof 直前に両キーを `.dt.as_unit("ns")` で ns へ正規化 (resolution-agnostic)。**閾値・grid・holding・survivor gate・verdict ロジックは一切不変** — 純粋に join を成立させるだけの R3 構造 fix (pre-reg LOCK の仮説空間に非接触)
- **影響**: E1 retail-contrarian 供給ライン (M1 の唯一の load-bearing 供給ライン、first-look verdict 2026-10-15) の日次 BT が **2 ペア → 14 ペア全数**で評価されるようになる。verdict は依然 NULL の可能性があるが、以後は「壊れた 2 ペア artifact」でなく全ペア universe 上の真の判定
- **教訓**: 外部 cache refresh がデータの dtype/resolution を変えると、silent に下流 join を破壊しうる。「verdict=NULL が続く」= エッジ不在と即断せず、join 行数の per-pair 監査を挟む (silent 失敗が「不発」と「ゼロ件」を区別不能にする系統: [[lesson-silent-except-hides-nameerror]])
- tests +1 file (`tests/test_phase1b_join_dtype.py`、6 本 — ms/ns/us/s 全 unit で非空 join を pin、全オフライン合成 fixture)。**評価への影響: なし (live/shadow/Kelly/tier 不変更)**

## 2026-07-24 — data(research): E7 phase-1 FF カレンダー歴史+gap import 完了 — §3.3b データ付録凍結 (期日 08-14 の 21 日前倒し、rule:R3)

- **残タスク「FF gap import」を歴史パネルごと一括完結** ([[e15-e7-event-modality-prereg-2026-07-18]] §3.3b 新設): EPSOFT は 2023-03 停止 (延長なし) → **R4F 公開 CSV (keyless、2007〜現在、日次更新) を 2014-01〜2026-07-20 の単一ソースに採用**。値整合 = EPSOFT cross-check **歴史 sample 279/279 完全一致** + 2023 Q1 overlap 114/120 (差分は全て EPSOFT 側 end-of-panel 劣化)
- **dump の実測特性 2 点を E15 canonical anchor 突合 (NFP 149 + CPI 135、miss 0) で特定**: (a) **時刻規約が 2023-08-07 で Europe/London → UTC に切替** → `tools/ff_gap_prepare_r4f.py` が正規化 (b) actual 列が 2023-08 で充填停止 → **判定系列 (NFP/CPI) は BLS 一次リリースの first print** (`tools/ff_gap_bls_first_prints.py`、Wayback §3.2b 経路、**較正 9/9 完全一致**) で補完 — previous 逆引き (改定値) を判定系列に使わない
- **抽出器の kind 順先勝ちバグ 2 種を R4F previous 連鎖との系統突合で検出・修正** (NFP 後方改定括弧 / CPI 後方 y/y — 出現位置最早選択に変更、実文 regression pin 4 本)。shutdown 合算値 (CPI 2025-12-18「over the 2 months」) は機械検出で除外
- **本番 import 済み (Render SSH、dry-run→実行)**: r4f-2014-2026 = 58,713 insert / bls-first-print = 66 actual 補完 / invalid 0。**判定系列 canonical 突合 297/298 完備** (唯一の欠落 = 事前宣言済み CPI 2025-12-18)。forecast の発表前性は発表前日 Wayback snapshot 4/4 一致で機械証明
- tests +23 (全オフライン)。**評価への影響: なし** — 純研究データ基盤、live/shadow/Kelly/tier 不変更。残 = phase-1 discovery 08-21 → verdict 08-28

## 2026-07-24 — data(research): E20 金利差方向バイアス S2 診断 — ❌ §7 exit 未達で棄却・クローズ (rule:R3)

- **rapid_edge_probe の `__dummy_e20__` を実 series に差し替えて S2 執行** ([[e20-rate-differential-s2-diagnostic-2026-07-24]]): `tools/e20_rates_ingest.py` (新規) が S1 §3 台帳の keyless 6 ソース (BIS WS_CBPOL 8/8 政策金利 + 2y = MASSIVE/ECB/MOF/BOE/BoC) から日次パネル→per-pair シグナル CSV を生成 (探索窓保護のため 2022-12-31 で物理切断して commit、sha256 manifest 付き)。GBP は IADB に 2y ZC が無く 5y ZC (IUDSNZC) 代用を明記。価格は **E15 phase-0 凍結 data_ledger と sha256 完全一致の 13 ペア parquet** (main の plain 名は refresh cron 短縮版で研究使用不可 — 部分 parquet 罠の変種を doc §1b/§5-4 に記録)
- **結果 (探索窓 2014-06〜2022-12 のみ、8 run、全 run OOS 非接触確認)**: **carry-level = §7 exit 3/3 欠け** — pooled IC **−0.047 (p≈0) 機構と逆符号で有意**、quintile **単調逆行** (Q1 +7.3 → Q5 −16.0)、EV_net 全負 (AUD_JPY −4.8)。**mom63 = 1/3 欠け (単調性 Q2 −12.9 中抜け) + 補助不合格 3 点** — IC +0.026 (p=0.003) と EV_net(k=5) +2.6p は通るが、EV 正 horizon の fold が [−,−,+] (fold3 単独駆動)、2022 slice +21.4p 集中 (S1 §5-4 の regime 罠)、cell IC 有意ゼロ (78 cell)。breakout 条件付け (user 仮説の形) は**両 variant で uncond より劣化** = テクニカル entry が価値を引く
- **→ E20 クローズ (S3 起案なし、§7 既定の棄却分岐)**。再試行禁止 scope = 凍結 2 variant の同型。rates データ配管は残置 (次の rates 系 S1→S2 は数時間で回せる)。OOS 2023+ は未接触温存
- 成果物: tools 2 本 + spec 8 本 + 診断 raw 17 ファイル + tests +14 (全オフライン)。**評価への影響: なし** — 純研究、live/shadow/Kelly/tier 不変更

## 2026-07-22 — feat(research): S2 共通ハーネス rapid_edge_probe — 仮説スペック 1 ファイル → 探索窓診断 (rule:R3)

- **user 要求「仮説を爆速で実装してテストするフロー」への回答**: [[edge-development-pipeline-2026-07-18]] §2 **S2 (R3 診断) を標準化** — `tools/rapid_edge_probe.py`。YAML/JSON スペック 1 枚 (direction_source: event/series/technical × entry_trigger: none/breakout/pullback × holding: bars/first_touch の小語彙) → ペア×horizon の **IC / 摩擦調整 EV / N / fold 3 分割 / 発火頻度** + S3 起案検討の目安を md+json で自動出力。`--draft-prereg` で S3 pre-reg スケルトン (🔓 DRAFT、LOCK 不能 TODO 付き) も自動 draft。使い方 1 ページ: [[rapid-edge-probe-2026-07-22]]
- **規律は構造で強制**: OOS 窓 (2024-01-01〜) は bars/calendar の load 直後物理スライスで遮断 (明示 `--unlock-oos` + 警告なしにアクセス不能、test pin)。全レポートに「探索診断 ≠ 判定 / live・tier 判断禁止」ヘッダ + **falsified 6 系統 + 価格モダリティ 3 周の再試行禁止チェックリスト**を自動印字。seed 固定 / silent except 禁止 (skip 全件理由カウント) / モジュールトップ副作用ゼロ
- **再発明なし**: estimand コアは `event_modality_lib.py` (§3.5 SSOT: σ_h first-touch SL 優先 / NY17時 roll ATR14d / E1 §3.4 凍結摩擦 / coverage gate)、IC 規律は channel_edge_ic_explore 同型、データは 12y 15m parquet 13 ペア + E15 イベントカレンダー
- **動作実証 2 本 (探索窓のみ — 診断であり判定ではない)**: (a) `nfp_usd_24h` = NFP 後 USD 方向 uncond → pooled EV **−7.4p (h4) / −3.7p (h24)**、fold 不一致 = エッジなし (E15 discovery の NFP uncond 凍結 0 と整合)。(b) `rate_diff_breakout_template` = 金利差方向×breakout の雛形 (外部 series は **E20 feasibility 待ちのためダミー列で構造のみ**) → EV ≈ −摩擦に収束 = 配管正常。`raw/bt-results/rapid_probe_*_2026_07_22.{md,json}`
- tests +27 (`tests/test_rapid_edge_probe.py`、全オフライン合成 fixture — OOS 遮断 / 語彙 / causal entry / SL 優先 / 決定性 / 規律ヘッダ pin)。全 suite 2328 passed / check.py 9/9 green
- **評価への影響: なし** — 純研究インフラ。live/shadow/Kelly/tier 不変
## 2026-07-22 — data(research): E15 phase-0 OOS verdict — ❌ FAIL 0/6 (全候補 C5、rule:R1 手続き、純研究)

- **判定器実装 + clean OOS 判定を執行** ([[e15-e7-event-modality-prereg-2026-07-18]] §5c/§8、期日 07-31 の 9 日前倒し): `tools/event_modality_oos_verdict.py` (extract/verdict 分離、seed=20260718 固定、B=10,000、estimand は lib SSOT 再利用)。**test pin 26 件を先に green にしてから OOS 接触** (§10-6 — 判定分岐 C1–C5/BH-FDR m固定/bootstrap seed 決定論/IM df/ナイフエッジ/canary 検出能力/OOS 窓ガード/摩擦式/join 契約)
- **結果: レグ A 全滅** — BH-FDR q=0.05 (m=6) 通過ゼロ (min p_combo=0.214 ≫ rank-1 閾値 0.0083)。4/6 は点 EV 正 (te/ft 両正、最大 CPI/fade/30m/h24 = +9.68p/p) だが event-block 推論 (bootstrap+IM) で有意性なし → **全 6 候補 C5 REJECT**。C3 ゼロ (blocks 20–28 ≥ 15 で B(d) 充足 — §9 modal 予想 C3 は自らの閾値と整合しない予想だった。§8 字義執行・再解釈なし)。**§8 固定分岐 = phase-1 (E7) 予定どおり実行**。Lee & Wang post-sample 検証も negative (fade は探索で不選抜、follow は OOS 非有意)
- データ整合 green: parquet 台帳再現 13/13 (sha256 凍結) / OOS sanity は CPI 14.3%・FOMC 10.0% >5% だが offset ピーク全種 +0 (時刻正常、explore 窓 user 裁定と同一シグネチャで続行・記録) / リーク canary 実データ 686 件 all clean。collision・週末跨ぎはフラグ記録のみ (§10-3)
- 成果物: `raw/bt-results/e15_phase0_oos_verdict.json` (全統計+trade/event list) + pre-reg §5b 凍結表転記 (🔒 手続き補完)・§8 発動分岐・§12 判定表 + registry `e15-e7-event-prereg-phase0-verdict` resolve + lib 加法拡張 (TradeOutcome.atr / entry_delay_bars / canary ATR 経路) + sanity 検出器の window 共有化
- **評価への影響: なし** — 純研究、live/shadow/Kelly/tier 不変更。次 = phase-1 (FF gap scrape + データ付録凍結 08-14 → verdict 08-28、registry `e15-e7-event-prereg-phase1-verdict` 監視継続)

## 2026-07-22 — docs(research): E20 金利差方向バイアス S1 feasibility — 条件付き採用 (S2 GO) (rule:R3)

- **user 仮説 (2026-07-22)「金利差から計算した方向バイアス × テクニカル entry」を E20 としてパイプライン S1 (C1–C6) で裁定** → [[e20-rate-differential-feasibility-2026-07-22]]。判定 = **条件付き採用 (S2 GO)** — 第 4 モダリティ (rates)、蓄積待ちゼロで BT 即可
- **falsified 台帳との区別を確定**: round-3 (intraday ZN divergence-reversion) とは データ/頻度/機構/役割 の 4 軸で別仮説。hull-donchian USD_CHF ratediff (FALSIFIED) は claim が逆 (fade ゲート ⇔ 継続バイアス)。D1 TSMOM は price-momentum で family 別 — 3 件の教訓ガード (単調性 / USD-neutrality / regime slice) を S2 必須化。E5 term-structure の C1 棄却は日次粒度で解消 (CIP proxy)
- **データ実在を一次確認 (実 fetch 証跡付き)**: 政策金利 8/8 = BIS WS_CBPOL 日次 keyless 単一エンドポイント (1999 実取得、鮮度 07-09〜14)。2y 国債利回り = US (MASSIVE in-house 1962+) / EUR (ECB 2004+) / JPY (MOF 1974+) / GBP (BOE 1995+) / CAD (BoC 2001+) 現行、CHF (SNB 1988+) は **2025-07-31 で cube 凍結**、AUD/NZD は WAF 403 → Wayback 歴史のみ (go-forward gap)
- 条件: claim = 継続バイアス限定 / variant 2 本凍結 / live 段階は AUD/NZD 制限 / 保有 1–10 日は帳簿上限外 (E9 同型 △)。S2 推奨 spec (`tools/rapid_edge_probe_e20.py`) を doc §7 に付す
- **評価への影響: なし** — 純研究 S1、live/shadow/Kelly/tier 不変更

## 2026-07-22 — data(research): E15 phase-0 discovery 実行 — §8 DEFERRED user 承認 → 6 候補凍結 (rule:R1 手続き)

- **§8 DEFERRED 裁定 = user 承認 (2026-07-22)**: sanity フラグ (CPI 43.6%) は verify-times で時刻正常を立証済み・低インパクトイベント由来と裁定、discovery 続行
- **discovery (探索窓 2014-2023 のみ): 54/54 combo 計算 → 選抜規則 (§5b 凍結 = fold→EV-per-vol→種分散) で 6 候補凍結** (FOMC 3 / CPI 3 / NFP 0) — `e15_frozen_candidates.json` + 全 combo 台帳 `e15_discovery.json`
- 価格 parquet は coverage 台帳検証済みフルセット 13/13 を使用 (部分 parquet 罠回避)。OOS 窓 (2024-01-01〜) は未接触 — **次 = clean OOS 判定、verdict 期日 2026-07-31** (registry `e15-e7-event-prereg-phase0-verdict`)。凍結は期日 07-24 の 2 日前倒し
- **評価への影響: なし** — 純研究、live 変更なし
## 2026-07-21 — feat(monitor): R3 market-data ingest 鮮度監視を prereg-trigger-registry に配線 (rule:R3)

- **registry `r3-market-data-ingest-freshness` 追加** ([[market-data-ingest-2026-07-18]] §7 宣言の執行、E1 `e1-positioning-ingest-freshness` と同型): `/api/marketdata/status` の health を毎日機械評価 — `verified:ff_calendar` 24h 超 stale / `verified:cme_bars:*` (7 契約) いずれか 72h 超 stale (週末市場閉鎖 ~2.5d を跨いでも誤警報しない) / キー欠落・min_keys 未達 (worker 未稼働・thread 死の fail-loud 検出) で 🔴 TRIGGERED。API 不達/health DB エラーは DATA_UNAVAILABLE に分離
- 実装 = `tools/prereg_trigger_watch.py` に type=`ingest_freshness` (純関数 `evaluate_ingest_freshness` + fetch 分離、既存パターン準拠)。tests +10 — registry 閾値/契約数がモジュール定数 `STALE_ALERT_*_SEC` / `DEFAULT_CME_SYMBOLS` と乖離したら fail する整合 pin 込み
- deploy 後検証 (§7 次アクション 1) 完了: running=true、ff + cme 7 契約全 verified (2026-07-21T10:55Z)。CME 深 backfill (§7 次アクション 2) は並行セッションが同日 11:10Z に全 7 契約完了済み (§7 に記録)
- **評価への影響: なし** — 監視エントリ + watch ツール拡張のみ。live/shadow/Kelly/tier 不変

## 2026-07-21 — feat(research): E15 phase-0 イベントカレンダー凍結 + §3.2b AMENDMENT — sanity >5% 発火で §8 DEFERRED (rule:R1 手続き、純研究)

- **§3.2b AMENDMENT (結果観測前 data-availability、round-3 前例)**: FRED キー self-provision 不能 → NFP 行に **pre-registered 済み fallback「BLS 公式ページ」を発動** (CPI は「同上」の明確化)。アクセスは Wayback snapshot 経由 (BLS 直接 403)。BLS News Release Archive の**アーカイブ発表ファイル名 = actual release date** を一次記録に格上げ。grid/判定規則は不変更、追記時点でイベント×リターン結合統計は未計算。
- **カレンダー凍結**: `tools/event_calendar_build.py` (politeness 2s/req) → `raw/bt-results/e15_e7_event_calendar.json` + build log。**FOMC 99 / NFP 149 / CPI 149 件** (2014-01〜2026-06、ET→UTC per-date DST)。FOMC は scheduled のみ (unscheduled 4 / cancelled 1 / notation vote 4 除外・記録、monetary20250822a 型の非会合リリースは行内突合で構造排除)。整合性検証 green (explore 窓: NFP 金曜規則・12件/年・欠月ゼロ)、2025 shutdown 異常はフラグのみ (§10-3)。パーサ回帰 pin 15 tests (オフライン fixture)。価格 re-fetch で coverage 台帳 13/13 完全再現。
- **⚠️ §3.2 sanity 発火 → §8 DEFERRED**: フラグ率 CPI 43.6% / NFP 6.8% / FOMC 2.5% (>5%)。処方どおり discovery 停止・再検証 → **verify-times (オフセットピーク検査) で全種 offset +0 ピーク = 時刻は正しい** (フラグは低インフレ期 CPI / COVID 期高ベースライン由来、破損行ゼロ)。しかし §8 明文「sanity >5% — **user 裁定 (勝手に解釈しない)**」に従い **discovery 未実行・user 裁定待ち**。裁定後は push-button (期日 07-24)。
- **役割分離**: 本カレンダー = 歴史 (BLS/Fed 一次、BT 判定用) ⇔ PR #102 FF capture = go-forward ingest (E7 Actual 補完)。非重複。
- **評価への影響なし** — 純研究、live/shadow/Kelly/tier 不変更。**§10-1 遵守: イベント×リターン結合統計は探索窓含め一切未計算** (計算したのはカレンダー件数・整合性・event bar range のみ)。

## 2026-07-21 — feat(research): E15 phase-0 §3.1 価格データ + coverage 凍結 — MASSIVE ブロックは誤り (rule:R1 手続き、純研究)

- **E15 phase-0 の data-run を前進** ([[e15-e7-event-modality-prereg-2026-07-18]] §3.1 執行、runbook `e15_phase0_execution_status.md`)。前回 (07-20) autopilot が「MASSIVE_API_KEY + FRED_API_KEY 双方 credential ブロック」と記録していたが、**MASSIVE 側は事実誤認** (`.env` に実在・稼働)。branch-stale (166 commit 遅れ) を検知し origin/main から再検証 → 自走原則で unblock。
- **成果**: 13 ペア 15m フル歴史 (days=4650) を MASSIVE 取得 → parquet、explore 窓 (2014-01-01〜2023-12-31) coverage 凍結 → `raw/bt-results/e15_e7_pair_coverage.json`。**13/13 pass gate 0.90 (0.974〜1.000)、primary 7/7、EUR_AUD 1.000** → §3.1 縮小分岐 / §8 DEFERRED(primary<5) リスク解消。ハーネス (`_load_pair`→`event_trade`→`run_combo`) を実 parquet でスモーク検証済。
- **残ブロッカー = FRED calendar (NFP/CPI) のみ**: `FRED_API_KEY` 不在・self-provision 不能 (FRED 公開ページ WebFetch 403/urllib timeout、firecrawl キー無)。FOMC は key-free だが歴史ページ書式が不統一 → NFP/CPI と同一 keyed パスで一括構築が正 (discovery は 54 combo family 全 event 揃うまで走らせない=§5b)。
- **§10-1 遵守 (中間 peeking 禁止)**: coverage 件数 + 日付範囲の計上のみ。OOS 窓のイベント×リターン結合統計は一切未計算。**評価への影響なし** — 純研究、live/shadow/Kelly/tier 不変更。期日: 凍結 2026-07-24 / OOS verdict 2026-07-31 (registry `e15-e7-event-prereg-phase0-verdict` 継続監視)。

## 2026-07-18 — docs(prereg): E15+E7 イベントモダリティ・プログラム 単一 family pre-reg 起案 — 🔓 DESIGN self-LOCK (rule:R1 手続き、純研究)

- **[[e15-e7-event-modality-prereg-2026-07-18]]**: round-2 裁定 ([[external-hypothesis-scan-round2-2026-07-18]]) の統合推奨どおり、E15 (FOMC/NFP/CPI イベント窓プレミア/リバーサル、phase-0) + E7 (指標サプライズ directional、phase-1) を**単一 pre-reg family** で起案。方法論 = round-1/2/3 と同一 (discovery diagnostic → 候補固定凍結 → clean OOS、BH-FDR + first-touch EV レグ + ナイフエッジ)、[[edge-development-pipeline-2026-07-18]] S2/S3 統合・型 B
- 設計の要点: (1) **α 会計 = phase 分割 q=0.05+0.05 ≤ 0.10** (E1 の look 分割と同型、multiplicity 二重取り禁止の実装)、(2) **primary = USD-leg 7 ペア block の combo pooled × event-block 推論** (bootstrap + Ibragimov–Müller 併設。T11「EUR_JPY は USD 露出ゼロ」反証の構造的排除)、(3) **凍結規則は raw EV 単独ランク禁止** — fold 安定性 → EV-per-vol → イベント種分散 ([[lesson-freeze-rule-topEV-selects-overfit-2026-07-14]] 反映)、(4) T11 / WMR fix REJECT / E8 棄却との区別を §2 に明示、発表前 entry は構造的にゼロ、(5) 窓 = discovery 〜2023-12-31 / OOS 2024-01〜2026-06-30 (Lee & Wang RAPS 2025 の post-sample = 文献 standing の検証を兼ねる)
- 期日: **phase-0 verdict 2026-07-31** (E1 first look 10-15 より 2.5 ヶ月先行 — WIP 原則の戦略的役割) / phase-1 verdict 2026-08-28。registry `e15-e7-event-prereg-phase0-verdict` / `phase1-verdict` 追加、queue `20260718-e15-e7-event-phase0` 起票、pipeline 状態表 S3 反映
- **評価への影響: なし** — 純研究 pre-reg + 監視エントリのみ。live/shadow/Kelly/tier 一切不変更。PASS でも実装は D4 実装 pre-reg + user 承認 (S5) が別途必要

## 2026-07-18 — docs(process): エッジ開発パイプライン常設化 — 供給ラインの単発プッシュ→常設プロセス転換 (rule:R3)

- **[[edge-development-pipeline-2026-07-18]]**: user 指摘 (07-18) を受け、暗黙だったエッジ開発手続きを S0〜S8 ステージ + **WIP 原則 (S1-S4 に常時 ≥2 仮説、モダリティ分散)** + 月次スキャン cadence として正式化。E1 単一ベット (modal=UNDERPOWERED) の後継不在リスクを構造的に解消する
- registry: `edge-supply-scan-monthly` (次回 2026-08-18) 追加
- **[[external-hypothesis-scan-round2-2026-07-18]] (E7-E19 裁定)**: 採用 3 — **E15 (FOMC/NFP/CPI イベント窓、in-house 12y + 無料カレンダーで即 BT 可 = E1 first look より先に verdict 可能な唯一の候補)** / E7 (指標サプライズ、19y 分単位パネル実確認、E15 と単一 pre-reg family) / E12 (CME 先物 volume flow — **yfinance 1h は 730d rolling で capture 開始遅延 = 歴史の不可逆喪失**)。条件付き E9 (VRP、無料 probe 先行)。棄却 6。データ実在は全て一次確認 (5-agent workflow、敵対的検査込み)
- 今から始めないと不可逆なインフラ 3 件を特定: FF Actual 補完 ingest / CME 1h volume 週次 capture / CME settlement・OI 日次 scrape (§infra 参照)
- 併走: shadow 蓄積詰まり R3 診断 (別ブランチ)
- **評価への影響: なし** — プロセス文書 + 研究裁定 + 監視エントリのみ

## なぜこのページが重要か
定量評価は「いつからのデータを使うか」で結論が180度変わる。
各バージョンの変更が**どのトレードに影響するか**をここで追跡する。

## 2026-07-18 — feat(data): R3 market-data ingest — E7 FF カレンダー + E12 CME 1h volume の go-forward capture 開始 (rule:R3)

- **[[market-data-ingest-2026-07-18]]**: [[external-hypothesis-scan-round2-2026-07-18]] infra_needed_now 3 件の実装裁定。(1) FF カレンダー = ✅ 実装 (faireconomy 公式 feed 6h capture + **翌期 previous 逆引き** actual 補完 + `tools/ff_calendar_import.py` gap 合流経路)、(2) CME FX 先物 1h volume = ✅ 実装 (yfinance 7 契約日次 capture、730d rolling 窓対策)、(3) CME settlement/OI scrape = ❌ **不実装 + round-2 前提訂正** (probe が「scraping は CME Data ToU で禁止」明示 403 / Databento は歴史保持 = 不可逆でない → E9/E10/E14 forward は Databento 一本化)
- 実装 = `modules/market_data_ingest.py` (positioning_ingest パターン準拠: fail-loud / モジュールトップ副作用禁止 / defer_thread fork-safety / health 2 テーブル / content-hash + UNIQUE dedup)。**forecast 凍結を code 強制** (event_time 通過後は feed 側改変を反映しない — E7 surprise estimand の汚染防止)。**形成中 bar 非保存 + 初回 capture 値凍結** (BT 再現性)
- 検証 API: `/api/marketdata/status` / `/api/marketdata/export?table=ff_events|cme_bars|health_log`。tests +38 (offline/deterministic)。smoke: CME 2 symbol × 155 bars 実 fetch→保存成功、FF は 429 rate-limit 実測 → poll 6h + retry 30 分に設計反映
- **評価への影響: なし** — read-only 蓄積 + 検証 API + import ツールのみ。live 発注経路・戦略・Kelly・shadow・BT 関数いずれも不変

## 2026-07-18 — docs(analysis): r2_shadow_demoted_cell「構造的詰まり」診断 — analyst フラグ裁定 = 現状維持 (rule:R3)

- **[[analyses/shadow-accumulation-blockage-diagnosis-2026-07-18]]**: analyst report (07-17 pre_tokyo 等) の「scalp 系全般で r2_shadow_demoted_cell が Sentinel N 蓄積を毎日足止め = 構造的詰まり」フラグをコード + 本番実測で裁定
- **コード実態 = (b)**: gate (`demo_trader.py` L4227-4248 / L3826) は OANDA 送信だけでなく **shadow row の DB 書込み (L5859 `open_trade`) まで完全遮断**。ただし対象は静的 registry (`shadow_demote_registry.py`) の**反証確定済みセルのみ** (retired 5 戦略 N=453〜1,117 + per-cell 5、全て R2 監査根拠つき)
- **実測で「詰まり」を否定**: 30d shadow rows **3,239 件 (~108/日)、147 セル** 蓄積継続。SCALP_SENTINEL 現役 (vol_surge_detector 90 / ma_regime_switch 115 行) は無傷、gate 起因ゼロは bb_rsi_reversion (T10 KILL 済) のみ。registry セルは demotion commit 日 (06-12/06-18/07-02) 以降の流入が正確にゼロ (leak なし)、per-cell 粒度も機能 (engulfing_bb×EUR_USD 157 行 vs ×USD_JPY 0)
- **block 件数は tick 再発火ノイズ**: Render logs 実測 37.4 分で 100 件 (ema_trend_scalp×GBP_USD 単独 ≈2.7/分)。in-memory カウンタは deploy 毎リセット — 「失われた N」の推定量にならない
- **裁定 = 現状維持**: gate は [[lessons/lesson-shadow-always-emit-cleanup-2026-04-28]] が要求した R2 自動 demotion gate の実装そのもので、原則 3 (未解決仮説の検定力保護) と無矛盾。unblock は slot 侵食 (scalp shadow cap 4/pair) で現役セルの蓄積を毀損し統計力を**下げる**。「emit 継続 + 学習除外フラグ」分離案は汚染経路再導入で却下。観測性改善 3 点 (analyst report 注記 / _SCALP_SENTINEL cosmetic 除去 / ログ rate-limit) を別タスク提案
- **評価への影響: なし** — 診断文書のみ、live/shadow 挙動・コード一切不変

## 2026-07-17 — fix(research): E1 ハーネス敵対的レビュー修正 — fatal 2 系統 (look-2 着地 / health 時系列) + major 6 + minor (rule:R3)

- **[[e1-positioning-contrarian-prereg-2026-07-16]] 判定器への敵対的レビュー (spec/leak/stats 3 レンズ、fatal 3 [実質 2 系統] / major 6 / minor 10) を全件処置**。pre-reg 本文は不変更 (LOCK 遵守)
- **F1 (look-2 着地違反)**: `overall_verdict()` が look を知らず second look で C3 → 禁止された `UNDERPOWERED` (= 第 3 look 示唆) を返していた → look=2 では **PASS / REJECT-F / REJECT のみ** に写像 (C3/C2/C5→REJECT、C4→REJECT-F、UNDERPOWERED 到達不能化 = α 会計 q₁+q₂≤0.10 の保証回復)。look=2 × C3 → REJECT / 着地集合の pin テスト追加
- **F2 (health 時系列インフラ、§6-7「estimand を宣言どおりにする運用修理」)**: §2.2 stale cap 主モードが要求する per-instrument verified **時系列**が、本番 `positioning_health` の 1 行 upsert から構造的に得られなかった → (1) `positioning_health_log` append テーブル新設 + `record_health()` が**同一トランザクション**で追記 (~940 行/日)、(2) `/api/positioning/export?table=health_log` read-only export 経路、(3) ハーネス `--verdict-run` は verified 系列欠落で fail-loud 拒否 (明示 `--fallback-mode` でのみ続行)、結果 JSON に `stale_cap_mode: primary|fallback` を必ず記録、fallback 時は §2.2 必須診断 (2h-cap NA の NY 時間帯分布) を併記し**閑散帯集中 → DEFERRED を機械接続** (事前固定分岐、閑散帯 = NY 17:00–03:00 / 総数≥50 / 集中倍率 2.0 を観測前固定)
- **major**: (a) gate2 点推定を全 6 combo 常時計算 — look=2 でナイフエッジ #2(ii) 隣接 combo 参照が機械 FAIL する偽 REJECT バイアスを修復 (`gate2_all_combos` で透明化)、(b) C1/PASS 経路の end-to-end pin — 埋め込み強 contrarian シグナル合成世界で **verdict=PASS/C1 に実到達**する統合テスト (knife 4 点 / confirmatory / Stage B / Gate1+2) + confirmatory 4 分岐・partial IC・S2 lag・S3 pain 式の単体 pin、(c) canary に rank 窓 (strictly trailing / t 非包含) + mid 経路 (確定 bar 限定) の注入点と rank→IC 貫通の検出感度チェックを追加 (リーク rank 実装が fail することを pin — §6-4 委譲の空洞化を修復)、(d) primary parquet 欠落の無言 family 縮小を封鎖 (`--verdict-run` で 13 ペア完備必須、欠落リスト表示で拒否)
- **minor**: verified key の book 成分検査 (outlook 限定) / im_test se=0 の符号盲目 p=0 修正 (逆符号→p=1) / CONFIRMATORY_UNTESTED フラグを C1 限定化 (C2〜C5 汚染除去) / 量子化粒度をペア×統計毎 (S1/S2/S3) に記録 / Stage B 実行条件を c1_candidate (Gate1+2 通過) に拡張 / parquet cutoff 切詰めの機械クリップ + 件数記録 (切詰め規約非依存) / LOCF resampler の DST 跨ぎ週 (2026-11-01) unit test / MBB 全ペア同時 day-draw の pin / **day-block「観測日 index」規約の宣言** (Gate 2 の疎 trade 日で暦 5 営業日と乖離 — LOCK 字義の解釈変更を避け、実装ノートとして verdict JSON (`block_basis`) と本 changelog に宣言。変更でなく宣言で処置した唯一の項目)
- tests 118→160 (E1 96 + ingest 64、全 offline/合成)。**評価への影響: なし** — 判定器 + read-only export 経路 + append テーブルのみ。live 発注経路・戦略・Kelly・shadow 一切不変。verdict 期日 (2026-10-15) の実データ初適用前に修正完了

## 2026-07-17 — feat(research): E1 pre-reg 判定ハーネス実装 — LOCK 後成果物 (rule:R3)

- **[[e1-positioning-contrarian-prereg-2026-07-16]] §7 成果物規定の実装**: 判定器 `tools/e1_positioning_prereg_eval.py` (2,250 行、LOCK 後実装・seed 固定 `SEED_DEFAULT=20261015`)。§7 の規定どおり **LOCF resampler / rank タイ規約 (mid-rank §3.1) / DST 跨ぎ週 (2026-11-01) / ATR (NY17 roll 完結 bar) / OHLCV join 契約 / canary leak test を `tests/test_e1_prereg_eval.py` (58 tests) に pin してから verdict データに触れる**体制を確立
- 実装範囲 = §2.2 市場時間 (America/New_York DST 追随) + LOCF/stale cap (verified 基準)/cycle 証跡、§2.3 join/前方リターン/ATR14d/censoring、§2.5 品質 gate (coverage/stale gap/family postpone/sanity/jump detector 前方+24h)、§3 シグナル 3 本 × rank/hysteresis/金曜窓/年末窓、§4.1 Gate1 (営業日 MBB L=5 B=10k 全ペア同時 + Ibragimov–Müller df=7、p=max、BH q=0.05 m=6)、§4.2 Gate2 (day-block bootstrap、N<60 は点推定分類)、§4.4 C1〜C5 排他分類 + SIGN-FLIP/CONFOUNDED (partial IC)、§4.5 ナイフエッジ 4 点、§2.4 confirmatory 複製検査、§4.3 Stage B、§4.6 Secondary
- **構造的強制 (§6-1/6-2)**: 入力 = 凍結 export artifact + parquet のみ (本番 API/DB 経路をコードに含めない)。synthetic 宣言のない artifact は `--verdict-run` フラグなしで拒否。family gate postpone 時は統計段を一切実行しない (look 非消費の機械化)。canary suite green が verdict 実行の前提条件
- **実データ接触なし — テスト・dry-run は 100% 合成データ** (§6-2「実データへの初適用は verdict 期日 2026-10-15」遵守)。tests 60→118 (58 追加、全 offline/deterministic)。**評価への影響: なし** — 研究ツール + テストのみ、live 発注経路・戦略・Kelly・shadow 一切不変

## 2026-07-16 — feat(research): E1 positioning contrarian pre-reg DRAFT + positioning_health 永続化 + D4 テンプレート (rule:R3)

- **[[e1-positioning-contrarian-prereg-2026-07-16]] (DRAFT)**: 文献駆動・**データ観測前** pre-reg — discovery 2 段階を省き、first look verdict を **2026-10-15** (cutoff = t0+12週) に固定。従来計画 (2-3ヶ月蓄積 → discovery → 凍結 → OOS) 比で **verdict を 1〜2 ヶ月前倒し**。設計 = 8-agent workflow (独立3案 → 統合 → 敵対的レビュー major 11 反映)。階層ゲートキーパー (pooled IC 二重検定 → 摩擦調整 EV conjunction、look 毎 BH q=0.05)、UNDERPOWERED second look (2027-01-06) 事前固定。LOCK 決裁期限 2026-07-17 (registry `e1-prereg-lock-decision-stale`)
- **positioning_health テーブル (pre-reg §2.2 必須インフラ)**: per-instrument `verified:` 時刻 + `last_cycle_at` heartbeat を DB 永続化 — dedup skip (行を書かない) と fetch 失敗の識別を可能にし、LOCF stale cap の活動条件付けバイアスを排除。status API に `health` 露出。詳細: [[e1-positioning-ingest-2026-07-14]] §13
- **[[d4-implementation-prereg-template-2026-07-16]]**: survivor 到達時に即起案できる D4 実装 pre-reg 雛形 (carve-out 2 択 / R2 自動降格 / セル単位判定 / parity / 防御解除ラダー) — 直列待ちの前倒し削減
- tests 56→60。**評価への影響: なし** — read-only 計測基盤 + 文書のみ。live 発注経路・戦略・Kelly・shadow 一切不変

## 2026-07-16 — feat(data): E1 instrument 拡張 6→13 — 将来セル候補の蓄積 clock を前倒し開始 (rule:R3)

- **動機 (最短経路)**: history は今から蓄積する以外に入手不可 (§8c 確定) → 将来ペアの clock は今日始めた分だけ discovery が早まる。outlook は全 symbol 一括 1 リクエスト (probe: n_symbols=186) のため **API 予算コストゼロ**、増分は DB ~940 rows/日のみ
- **追加 7 ペア**: AUD_USD / NZD_USD / USD_CAD / USD_CHF / NZD_JPY / EUR_AUD / EUR_GBP (engine モード/Phase B-1 slot 既存の取引可能ペア)。ペア別 t0 が異なる点を pre-reg 窓設計の必須参照事項として記録。詳細: [[e1-positioning-ingest-2026-07-14]] §12
- **評価への影響: なし** — read-only データ収集の対象拡張のみ。live 発注経路・戦略・Kelly・shadow 一切不変

## 2026-07-16 — fix(data): E1 defer_thread — import 時 network thread 起動の廃止 (第2修正, rule:R3)

- **背景**: §10 修正後も serving プロセスの healed thread がハング (master の cycle は成功 = t0 蓄積開始済み)。帰属 = fork 瞬間に master thread が HTTP 実行中 → socket/ssl 内部 lock が locked のまま複製 (Session 再生成では直らない)
- **根治**: `start_positioning_ingest(defer_thread=True)` — master では thread を起動せず、serving プロセスの初回 heal (§8b) を唯一の起動経路に一本化。status に `current_phase`/`phase_since` 追加 (ハング位置の直接観測)。詳細: [[e1-positioning-ingest-2026-07-14]] §11
- tests 54→56。**評価への影響: なし**

## 2026-07-16 — fix(data): E1 Myfxbook client 2バグ修正 — session 二重エンコード + fork-unsafe HTTP Session (rule:R3)

- **背景**: user が credentials 投入 (05:54Z) → 初回稼働で "Invalid session." + healed thread ハングを実証
- **(a)**: Myfxbook session は発行時点で URL-encoded 済み — params= 再エンコードが二重化。`_get` を組立済み query 方式へ (session は raw 付加)。**(b)**: fork 継承 requests.Session の pool lock が locked のまま複製されハング — pid 変化検知で lazy 再生成。詳細: [[e1-positioning-ingest-2026-07-14]] §10
- 修正版で実 API 検証済み (186 symbols / 対象 6 ペア全取得)。tests 51→54 (回帰 pin 3)
- **評価への影響: なし** — read-only データ収集の修正のみ

## 2026-07-15 — feat(data): E1 ソース転換 — Myfxbook Community Outlook aggregate 版 (オプション A 採択, rule:R3)

- **決裁**: user 全面委任 (2026-07-15「最短がオーダーなので、やり方は任せる」) の下で §8c オプション A 採択。B (practice) は期待値低で保留、C (有償) はコスト非対称、D (閉鎖) は唯一の主戦線を閉じる理由なし。詳細: [[e1-positioning-ingest-2026-07-14]] §9
- **何を**: `modules/myfxbook_client.py` (新規、login/session/re-login、secrets 非開示 pin) + `positioning_ingest.py` ソース抽象 (`POSITIONING_SOURCE` 明示 > MYFXBOOK_EMAIL/PASSWORD 自動検出 > oanda default)。book_type=`outlook`、near_imbalance=NULL (bucket 級放棄の明示)、raw payload を buckets_json に JSON object で温存、content-hash dedup (sha256、snapshot_time は fetch 時刻 μs 精度)、poll ≥900s clamp (rate limit 100 req/24h)
- **受け入れ確認**: `/api/positioning/probe?run=1&source=myfxbook` (login+outlook 1回)。export API は book=outlook を受理
- **user アクション (E1 稼働の唯一の依存点)**: Myfxbook 無料 account 作成 → Render env に `MYFXBOOK_EMAIL`/`MYFXBOOK_PASSWORD` 投入 (§9 手順)
- **評価への影響: なし** — live 発注経路・戦略・Kelly・shadow 一切不変。read-only データ収集のソース交換のみ。tests: test_positioning_ingest.py 34→51

## 2026-07-15 — fix(routing): trendline_sweep 全セル shadow-first demote — ELITE_LIVE all-pairs bypass 除去 (pre-reg 2026-07-13 執行, rule:R2)

- **何を**: `_ELITE_LIVE` から trendline_sweep を除去 (最後の member → 空集合化) + `_PAIR_DEMOTED` に EUR_USD / GBP_USD / EUR_GBP の 3 セルを追加 (gbp_deep_pullback 2026-05-04 と同型)。`TRENDLINE_SWEEP_REDESIGN_V2=1` env の live 復活パスも PAIR_DEMOTED 先勝ちで無効化。`HTF_MIXED_LIVE_STOP_CELLS` の GBP_USD mixed cell stop は部分集合として残置
- **なぜ**: pre-reg `trendline_sweep_gbpusd_pairscope_2026-07-13` (resolved / reviewer=SATISFIED) の terminal action 執行。12y MASSIVE per-cell WF (本番 trigger 無変更) で**全 3 セル FAIL** — netEV: EUR_USD −0.483 (N=3036, WF 1/4) / GBP_USD −3.121 (N=4884, grossEV=−0.095 = 摩擦以前に負) / EUR_GBP −1.449 (N=2829)。BH-FDR (q=0.10, m_eff=4) 生存ゼロ。ELITE_LIVE 根拠の 365d favorable BT (WR 73-81%) は WR 41-44% に崩壊し反証。forward LIVE GBP_USD netEV=−2.35p RR=0.15 が corroborate
- **shadow 継続**: 3 セルとも emit は止めない — is_shadow=1 で記録継続 (4原則#3)。再LIVE化条件 (R1, cell 単位) = forward shadow N≥20 ∧ Wilson_lo≥0.40 (FDR) ∧ WR≥BE-WR@realized-payoff
- **評価への影響**: あり — trendline_sweep の live 発火が全ペアで停止 (ELITE_LIVE 便乗 live はこれで消滅、`_ELITE_LIVE` は空集合)。clean live 集計から trendline_sweep の新規 live row が消える。shadow 統計は不変
- 詳細: [[trendline-sweep]] 判断履歴 / BT: `bt-results/trendline_sweep-12y-pairscope-2026-07-13.json`

## 2026-07-14 — fix(data): E1 positioning worker self-heal + 401 帰属確定 (OANDA book 提供終了) (rule:R3)

- **本番実証 2 問題** ([[e1-positioning-ingest-2026-07-14]] §8): ①全 12 book が HTTP 401 ②worker thread が process ライフサイクルで死ぬ (started_at ありなのに running:false / poll_cycles:0)
- **401 帰属確定 (§8a)**: 当初仮説「OANDA Japan 区分制限」を**棄却** — OANDA は **2024-09-14 に retail API での book 提供を終了** (公式告知 oanda.jp/info/1193 原文確認 + no-token でも同一 generic 401 の実測 + 非日本ユーザー同時遮断の傍証)。fxlabs `/labs/v1/orderbook_data` は 2020 年廃止 (403 HTML 実測)。**auth 修理では直らない → 代替ソース比較 §8c を user 決裁用に整備 (推奨 = Myfxbook aggregate 版転換)**
- **self-heal (§8b)**: demo_trader StatusHeal パターン準拠 — `ensure_running()` (started_at あり × thread 死のみ heal、stop 後は復活せず) + `status()` 冒頭 heal + app.py `before_request` heartbeat (60s throttle、Render health check を恒常 heal 経路化)。status に `restarts`/`last_restart_at` 追加
- **probe API**: `GET /api/positioning/probe?run=1` — v3/accounts 統制付き可用性 probe (read-only ×4)。token/口座 ID 非開示をテストで pin。instrument は whitelist 検証 (path injection 防止)
- **registry**: `e1-positioning-ingest-freshness` → conditional_info 化 — 蓄積ゼロは既知状態、user 決裁まで stale 調査不要
- **評価への影響: なし** — live 発注経路・戦略・Kelly・shadow 一切不変。tests: test_positioning_ingest.py 17→34

## 2026-07-14 — feat(data): E1 positioning ingest — OANDA 建玉/注文比率の snapshot 蓄積基盤 (user GO 2026-07-14, rule:R3)

- **何を**: OANDA v20 positionBook/orderBook (read-only) を 20 分毎 + jitter で snapshot し、既存 SQLite に `positioning_snapshots` (UNIQUE(instrument, book_type, snapshot_time)) として蓄積。buckets は mid ±3% trim + 集計列 (pct_long/short_total, near_imbalance)。対象 6 instruments (USD_JPY/EUR_USD/GBP_USD/EUR_JPY/GBP_JPY/AUD_JPY、env override 可)。dedup 3 層 (book.time メモリ / 再起動 DB seed / UNIQUE)
- **なぜ**: WS3 price-modality 計 3 周 FAIL ([[ws3-round3-crossasset-divergence-prereg-2026-07-13]] §8) → E1 retail-positioning contrarian が主戦線。positioning history は今から蓄積する以外に入手不可 = 稼働開始が最優先。設計: [[e1-positioning-ingest-2026-07-14]]
- **可観測性 (fail-loud)**: `/api/positioning/status` (行数/最新 snapshot_time/連続失敗/可用性マップ) + `/api/positioning/export` (研究用 JSON)。非対応 instrument は初回 4xx 記録→以後 skip。silent except ゼロ
- **監視 (T5 教訓)**: registry `e1-positioning-ingest-freshness` (最終 snapshot 2h 超 stale = 要調査)。`prereg_trigger_watch.py` に info/conditional_info type 追加 (UNAVAILABLE ノイズ→watching)
- **評価への影響: なし** — live 発注経路・戦略・Kelly・shadow 一切不変。read-only データ収集 thread の追加のみ。env `POSITIONING_INGEST_ENABLE=0` で無効化可
- tests: `tests/test_positioning_ingest.py` (17) + prereg watch (+2)。本番検証手順は KB ページ §5 (ローカル token 失効のためデプロイ後検証)

## 2026-07-10 — data(bt): WS3 探索2周目 OOS verdict — ❌ FAIL 0/5、外部仮説探索へ転進 (rule:R1)

- **OOS 窓**: 2024-07-07〜2025-07-07 (再利用 2 回目)。切詰め parquet (末尾 2025-07-07T23:45Z) + **N 凍結→判定の順序執行** (`ws3_round2_oos_entries.json`)。GBP_JPY 15m は Massive 遡及取得で充足、EUR_USD/USD_JPY は stage-1 凍結資産再利用、ep 復元不一致 0/428
- **判定** ([[ws3-round2-explore-prereg-2026-07-10]] §8): 2 レグ (ratio BH-FDR m=5 / §2b 凍結 grid first-touch EV) + ナイフエッジ (LOFO) — **全 5 セル FAIL**。vol_spike×USD_JPY N=27<30 機械 FAIL + ratio 崩壊 0.56 / vsg×GBP_JPY 0.88・dt_sr×GBP_JPY 0.90 崩壊 / sr_fib×GBP_USD 1.21 (p=0.13 n.s.) + EV 孤立格子点 / 最接近 sr_fib×EUR_USD 1.25 (p=0.19) + EV 隣接過半 fail
- **一貫した結論**: round-1→stage-2→round-2 の 2 周で「現行エンジン母集団に OOS 再現の方向性非対称 × 固定 barrier EV の組は無い」。探索窓 EV スクリーン通過 5 セル中 4 セルが OOS で崩壊 = 探索窓 EV は選択バイアスの別表現
- **分岐 (§3 事前固定)**: shadow 母集団内の軸は枯渇 → **外部仮説 (新シグナル系統 — 学術/TV 由来、falsified 6 系統除外) の探索へ転進** (v2.3 WS3 反映)。registry `ws3-round2-oos-verdict-deadline` resolved
- **評価への影響**: なし (純研究、live/shadow 変更なし)

## 2026-07-10 — docs(kb): WS3 探索2周目 pre-reg LOCK — 候補 m=5 凍結 (rule:R1 stage-1 型、純研究)

- **診断** (`raw/bt-results/ws3_round2_scan_2026_07`): 方向分割 196 セル + EUR_GBP (entries=0 構造的) + h96 → 1次候補 8 セル。round-1 checkpoint 窓同一性 0 mismatch
- **§2(ii) 探索窓 first-touch EV スクリーン** (`ws3_round2_ev_screen_2026_07`): **5/8 通過**。脱落 = turtle_soup×GBP_USD / dt_sr_channel×GBP_USD×SELL (孤立格子点) / sr_fib×AUD_JPY×SELL (EV<0)。stage-2 verdict の教訓「非対称 ≠ 固定 barrier で EV 化可能」をスクリーン結果観測前に pre-reg へ反映した a priori 改訂が機能
- **LOCK**: [[ws3-round2-explore-prereg-2026-07-10]] §2b に m=5 + 凍結 grid + 摩擦判定値を固定。registry `ws3-round2-oos-verdict-deadline` (2026-07-17) 追加
- **評価への影響**: なし (純研究、live/shadow 変更なし)

## 2026-07-10 — feat(mode): 15m AUD_JPY shadow-only モード `daytrade_audjpy` 新設 (user 承認 D2)

- **目的**: WS3 stage-2 対象セル htf_false_breakout×AUD_JPY の estimand は **15m** だが、本番 AUD_JPY は 1h モード (`daytrade_1h_audjpy`) のみで 15m shadow 発火ゼロだった。stage-2 PASS 時に shadow parity 検証を即開始できる状態 + AUD_JPY 実測摩擦 (spread/slippage) の取得。決裁メモ: [[shortest-path-decision-memo-2026-07-10]] / pre-reg: [[ws3-stage2-barrier-ev-prereg-2026-07-09]]
- **MODE_CONFIG**: interval 30s / 15m / 60d / compute_daytrade_signal / AUD_JPY / auto_start=True / base_sl_pips=15 (JPY クロス既存値 eurjpy=15 準拠) / **`shadow_only: True`**
- **shadow-only 構造保証 (新機構 `_mode_is_shadow_only`)**: 既存機構では塞げないことを確認の上で追加 — htf_false_breakout は `_SHIELD_EUR_DT_WHITELIST` 登録済みのため `_OANDA_MODE_BLOCKED` 方式は bypass され、N<10 sentinel は agg-Kelly gate も bypass して live minlot 発注される (テストの control ケースで実証: 同一入力×mode=daytrade は 1000u send に到達)。ガードは 3 経路: ①送信ガード最終段 (PRIME/GRAIL/C1/Kalman/edge-cell force-live の後・OANDA 判定の前で shadow 強制、以降 promote 復帰経路なし) ②`_resend_promote_gate_block_reason` に `SHADOW_ONLY_MODE_GATE` (補完送信) ③`_resolve_is_shadow_for_write` (write-path fail-closed)
- **htf_false_breakout 発火経路**: `HTF_FALSE_BREAKOUT_REDESIGN_V2` OFF の legacy 経路のまま (コード変更なし、stage-1 と同一母集団)。v6.1 JPY 追加ゲート (RSI div / OB 接触) は本番仕様どおり適用。QUALIFIED_TYPES は既にグローバル登録済みで per-pair 追加不要、live 転送資格の付与は一切なし
- **テスト**: `tests/test_daytrade_audjpy_shadow_only_mode.py` (9 tests) — 構造 pin / 最悪ケース (N<10 sentinel × strategy_mode=live × bridge active × SHADOW_MODE off) の send ゼロ / control 帰属証明 / resend・write-path gate
- **影響トレード: なし** (live パラメータ不変・OANDA 発注ゼロ。AUD_JPY 15m shadow 行の新規蓄積が開始される)

## 2026-07-09 — fix(tier): FORCE_DEMOTED > PAIR_PROMOTED precedence 全経路統一 (rule:R3)
## 2026-07-10 — docs(kb): 最短経路決裁 (user 承認「進めて」) + 月利目標の段階化 (rule:R3 導出)

- **決裁メモ**: [[shortest-path-decision-memo-2026-07-10]] — 8-agent workflow + 敵対的レビュー3レンズによるゼロベース再検討。**agg-Kelly gate 恒久閉鎖の確定** (固定 cutoff 2026-04-16 累積 −0.2758 → per-cell carve-out なしで正セルも live 発火不能)、D3 決裁 SLA 48h、D4 実装 pre-reg 必須項目 (carve-out + R2 自動降格 + セル単位判定 + parity)
- **目標段階化 (D5)**: [[monthly-target-rederivation-2026-07-10]] — 21.6% の導出考古学 (12-cell 母体 1〜2/12 残存、二重楽観バイアス、pips→%変換消失)。現行制約下天井 = 2セルで +0.15〜2.4%/月。**段階目標 M1 (月次符号転換) → M2 (+0.5%/月) → M3 (+2〜3%/月) へ移行、21.6% は aspirational anchor** — CLAUDE.md / index / roadmap v2.3 反映
- **トラックB 起動**: [[ws3-round2-explore-prereg-2026-07-10]] DRAFT (探索2周目: 方向分割×未走査ペア×h96、判定済み8セル+falsified 6系統除外、queue `20260710-ws3-round2-explore` 排他 claim)
- **評価への影響**: なし (live パラメータ変更なし。D2 15m AUD_JPY shadow-only モードは別 PR)
## 2026-07-09 — fix(tier): FORCE_DEMOTED > PAIR_PROMOTED precedence 全経路統一 (rule:R3)
## 2026-07-10 — WS3 stage-2 verdict: ❌ PASS ゼロ / UNDERPOWERED — barrier EV 化は不成立 (rule:R1)

- pre-reg LOCK ([[ws3-stage2-barrier-ev-prereg-2026-07-09]]) の機械的実行 (期日 07-19 の 9 日前倒し)。OOS-2 = 2022-07-07〜2024-07-06 (第3窓、切詰め worktree)。§3 執行順序遵守 (エントリー抽出 → N 凍結 59/46 → sim)。独立実装の再計算で符号一致検証
- **lfr×EUR_USD: 全 9 構成負 (best −6.51 p/t) → セルクローズ**。SL 先着率 44-75% — stage-1 の中央値非対称は first-touch sequencing で反転
- **htf_fb×AUD_JPY: 1/9 構成のみ +1.15、p_cell 0.594** — fold 集中 (2022 円介入期 +10.8 / 直近 −10.9)・孤立格子点。UNDERPOWERED 分岐 = shadow N≥100 で同一 grid 1 回限り再判定 (registry `ws3-stage2-underpowered-recheck`)
- **帰結: v2.3 WS3 は新シグナル系統 (外部仮説) の探索へ**。TV canon は PASS 候補不在で未評価 (moot)
- **監視配線 (R3)**: `prereg_trigger_watch.py` の shadow_count_decision に instrument フィルタを追加 (無指定だと全ペア合算でセル判定を過大計上) + 回帰テスト。`test_session_time_bias_in_bt_metrics` をパーサ実装 (all-pairs/full-audit 優先) に整合 — 旧実装は辞書順最後の .md を盲目的に見ており研究成果物の追加で誤 red になっていた (テストバグ)
- **影響トレード: なし** (純研究。live/tier 変更ゼロ)
## 2026-07-09 — fix(tier): FORCE_DEMOTED > PAIR_PROMOTED precedence 全経路統一 (rule:R3)
- **latent 疑義の確定**: `_is_promoted_ex` のみ PP 先勝ちで、シグナル経路
  `_is_live_tier_exempt` (9b16ebb5 fail-closed) / `_apply_force_demoted_final_gate` /
  再送 gate と逆。final gate が PP 例外なしに shadow 強制するため live 漏れは構造的に
  不可能 = **実害ゼロ (latent)**。実害候補は「PP でペア復活」の silent 死コード化
  (ema_pullback×JPY 前例) と audit block_cause 誤帰属のみ
- **修正**: `_is_promoted_ex` を FD 先勝ちに統一 + docstring 正準化。FD∩PP=∅
  (tier_integrity_check check#1) のため到達可能入力で挙動不変 (no-op 証明、BT 不要 R3)
- **CI 固定**: `tests/test_pair_promoted_force_demoted_precedence.py` (5 tests) で
  FD∩PP=∅ / PP∩PD=∅ 不変量 + precedence pin。正準文書 = [[system-reference]] Tier
  Precedence セクション (経路別 derivation 表)
- **副次発見の相互裏付け**: post-commit-verify.sh check#3 の `pp_sentinel` premise
  stale (PP∩UNIVERSAL_SENTINEL = {vix_carry_unwind, doji_breakout,
  squeeze_release_momentum} は設計上合法) を本調査でも独立に確認 — 並行セッションの
  check#3 修正 (下記 f292ccb1、マージで合流) と同一結論
- **影響トレード: なし**

## 2026-07-09 — WS3 stage-2 pre-reg LOCKED — user 承認 (rule:R1)

- [[ws3-stage2-barrier-ev-prereg-2026-07-09]] を user 承認「進めて」で 📝 DRAFT → 🔒 LOCKED (決裁期日 07-16 の 7 日前倒し)。verdict 期日 2026-07-19 (LOCK+10d、registry `ws3-stage2-verdict-deadline` 監視)
- **影響トレード: なし** (live パラメータ不変。grid BT / TV 検証の実行解禁のみ)
## 2026-07-09 — post-commit-verify check#3 silent 不発修正 + assertion 現行設計へ張替え (rule:R3 構造バグ)

- **不発の実証と修正** ([[lesson-post-commit-verify-silent-misfire-2026-07-09]]): check #3 (demo_trader tier set 整合検証) は bash double-quoted `python3 -c "..."` 内の f-string `"` によるコード截断で導入 (2026-04-14) 以来一度も実行完了せず、SyntaxError が `|| echo "SKIP"` に吸収される silent 検証ギャップだった。quoted heredoc 化 (check #1 も予防的に同化、check #2 は inline python 非使用で対象外) + 空出力/import 失敗の FAIL 可視化 + `POST_COMMIT_VERIFY_CHANGED` テストシームで red→green 実証
- **stale assertion 発見**: 修復後の初実行が検出した 4 overlap (FD∩SENT=post_news_vol / PP-strat∩SENT=doji_breakout, squeeze_release_momentum, vix_carry_unwind) は全て現行設計の意図的共存 (demote = live 遮断 + shadow 蓄積継続、PAIR_PROMOTED は `_is_promoted_ex`/`_resolve_tier` 両 gate で SENTINEL より先勝ち)。assertion を現行 invariant (`PAIR_PROMOTED∩PAIR_DEMOTED` 同一セル / `ELITE_LIVE∩FORCE_DEMOTED`) へ張替え — 両者とも現状空集合 = 本番 tier 状態は健全
- **影響トレード: なし** (ローカル post-commit hook のみ、live シグナル判定・サイジング不変)

## 2026-07-09 — WS3 stage-2 pre-reg DRAFT 起案 + KB stale 棚卸し (rule:R1 起案 / R3 doc-sync)

- **stage-2 barrier/EV pre-reg DRAFT** ([[ws3-stage2-barrier-ev-prereg-2026-07-09]]): PASS 2 セル限定 h24 barrier grid (m=18)。評価 = 第3窓 OOS-2 (2022-07〜2024-07、2年) で winner's curse 遮断、Westfall–Young max-T セル検定 (FWER 0.10)、TV Pine canon trade-level 突合ゲート、3 分岐 verdict (PASS/UNDERPOWERED/REJECT)。敵対的レビュー 3 レンズ 18 findings 反映 (tie-break 帰属訂正 = SL 優先は swing 規約で fut_close pin より保守側、検定力分析による 2 年窓化、timeout ドリフト PASS の排除等)。**DRAFT — user 決裁期日 2026-07-16 (registry `ws3-stage2-lock-decision-stale` 監視)、LOCK 前の grid BT 実行禁止**
- **KB stale 訂正 (R3 doc-sync、tier 実状態の変更なし)**: london_fix_reversal×GBP の PROMOTED/PAIR_PROMOTED 残存 2 箇所 (`wiki/edge-pipeline.md` / `wiki/strategies/edge-pipeline.md` Stage 6 表) を v9.1 実状態 (Phase0 Shadow + PAIR_DEMOTED×USD_JPY、365d BT GBP EV=−0.239 で demote 済み) に同期 — check.py Edge Stage warn の解消
- **影響トレード: なし** (DRAFT 起案 + doc 同期のみ)

## 2026-07-09 — WS3 stage-1 verdict: ✅ PASS 2/8 — 方向性非対称の OOS 再現 (rule:R1 stage-1)

- pre-reg LOCK ([[ws3-asymmetry-oos-prereg-2026-07-09]]) の機械的実行 (claude 直接、期日 07-16 の7日前倒し)。OOS 窓 2024-07-07〜2025-07-07 (切詰め parquet worktree で look-ahead 遮断、USD_JPY/AUD_JPY は Massive 15m を 2024-05 まで遡及取得)、N=4,980 entries。
- **PASS**: london_fix_reversal×EUR_USD (OOS ratio 1.43 vs 探索 1.51、p=0.0115、CI5% 1.14) / htf_false_breakout×AUD_JPY (1.82 vs 1.39、p=0.0118、CI5% 1.20)。BH-FDR q=0.10 (m=8) + ratio≥1.2 + N≥30 + ナイフエッジ3点全通過。
- 選択バイアス組の崩壊 (htf_fb×EUR_JPY 1.81→0.99 / dt_sr_channel×EUR_USD 1.55→0.62) を確認 = 2段スクリーン設計が機能。持続型 2 セル (lin_reg_channel / dt_fib) は不再現でクローズ。
- **影響トレード: なし (純研究 stage-1)**。次 = stage-2 (PASS 2セル限定 barrier/EV pre-reg + TV Pine canon + user 最終承認)。判定器 `tools/ws3_oos_verdict.py` / スキャン `tools/ws3_mfe_scan.py` (--pairs/--out-suffix 追加)。
## 2026-07-09 — WS4 T15: CI paths filter 撤廃 + QUALIFIED_TYPES drift 検査 + 再送ガード共通化 (rule:R3, audit P1-6/7/8)

- **P1-7 (CI 品質ゲート穴)**: ① `ci.yml` push trigger の paths filter を撤廃 — 旧 filter (`*.py`/`strategies/`/`modules/` のみ) は tests/tools/agents/knowledge-base/scripts 変更の直接 push で CI が一切走らない盲点だった。② hip1-holdout-manifest ガードを CI job 化 (`hip1-holdout-guard`) — .git/hooks/pre-commit はカスタムスクリプト symlink のため pre-commit フレームワークの hook はローカルで一度も実行されていなかった。event diff に対して実行、正規編集は commit message の `HOLDOUT-APPROVED` / `HOLDOUT-VALIDATION-APPROVED` マーカーで通過。③ `agents/cma/dev.agent.yaml` の `--no-verify` 根拠誤記 (「hip1 が full pytest を走らせる」→ 実際はカスタム hook 側) を訂正。actions は full SHA pin 化 (supply-chain)。
- **P1-8 (scalp BT QUALIFIED_TYPES drift)**: `run_scalp_backtest` の inline set を `SCALP_BT_QUALIFIED` に改名 (挙動不変) + 意図的除外 `SCALP_BT_EXCLUDED_TYPES` (mtf_trend_follow / mtf_counter_trend / mtf_regime_trend_cascade = vec harness 専用) を文書化。`scripts/check.py` step 5b が「enabled scalp ⊆ QUALIFIED ∪ EXCLUDED」を機械検査 (drift = ERROR、矛盾登録 = ERROR、stale 除外 = WARN)。意図的 drift で red になることを確認後 green 化。
- **P1-6 (再送ガード共通化)**: `_resend_pending_oanda_trades` は FORCE/PAIR demotion しか再チェックせず Q4/aggregate Kelly/MC-ruin/SHIELD mode を素通しだった (is_shadow 反転バグ 1 つで gate 迂回の直通経路)。共通 helper `_resend_promote_gate_block_reason` が主経路の v9.x SHIELD 群と同判定を resend 直前に再実行。ELITE Q4 免除 / SHIELD whitelist / 1000u min-lot bypass / SENTINEL 免除は主経路と同じに保ち、PRIME lock・edge-cell bypass は per-signal コンテキスト不在のため fail-closed 側へ (5分窓の補完送信のみに影響)。`get_open_trades_without_oanda` に confidence 追加 (Q4 再チェック用)。
- **影響トレード: なし** (live シグナル判定・サイジング不変。resend の fail-closed 化と BT/CI/検査系のみ)。回帰: `tests/test_t15_quality_gates.py` (20 cases)。詳細: [[fable5-system-audit-2026-07-02]]。

## 2026-07-09 — P1-2b 検証クローズ: fut_close tie-break は4エンジン既装 + 回帰 pin 移植 (rule:R3, T14 補完)

- **二重実装レース記録**: T14 (P1-2) は autopilot が PR #65 で実装・マージ、並行セッションの PR #64 (同一実装 + 追加テスト 20 cases) と衝突 → #64 close で解決 (07-07 handoff インシデントと同型)。両実装の意味的差分ゼロを精査確認: (a) 3エンジン cache 無効化 (b) 1H系 BE/Trail guard (block-wrap ⇔ 閾値inf は等価) (c) flag semantics 完全一致。
- **P1-2b (fut_close tie-break) 検証結果: 追加実装不要** — 同一バー TP+SL 同時ヒットの fut_close tie-break は 4 エンジン (run_backtest/scalp/daytrade/1h) 全てに既装、swing はより厳格な保守的 SL 優先 (両ヒット=LOSS)。fut_close→SL 優先への厳格化は BT 全体再較正を伴うため監査どおり P2 据置。
- **#64 由来のテスト delta を移植**: `tests/test_bt_tie_break_regression_pins.py` (13 cases) — ① inline flag 式の canonical AST pin (真偽逆転・env typo 検出、main の既存 pin は参照有無のみ) ② cache key/フラグ照合 pin (stale cache = A/B 汚染防止) ③ P1-2b tie-break pin (TP優先への退行封鎖 + swing SL優先維持)。
- 影響トレード: なし (テスト + KB のみ、app.py 不変更)。

## 2026-07-09 — P1-2: BE/Trail ablation を全 BT エンジンへ展開 (rule:R3, WS4 T14)

- MEMORY 確定事実 `project_be_trail_inflates_python_bt_wr` の水増し源が daytrade 以外の 3 エンジン (`run_backtest` 1H / `run_scalp_backtest` / `run_1h_backtest`) に残存していた (Fable5 監査 P1-2)。daytrade と同じ `_BT_ABLATE_BE_TRAIL` (default ablated、`BT_OPTIMISTIC=1` で旧挙動復元) guard を展開。
- **行動証拠** (scalp fixture `_df_override`): ablated(default) N=84 WR=46.4% vs optimistic N=102 WR=56.9% → **+10.5pp inflation を default で排除**。
- BT cache key を flag-aware 化 (A/B で stale 防止)。AST 構造回帰テスト `tests/test_be_trail_ablation_all_engines.py` 同梱 (4 エンジン guard を pin)。
- **影響トレード: なし** (BT 評価ロジックのみ、live signal/OANDA 転送は不変)。過去 scalp/1H verdict は水増し込みのため再解釈対象。詳細: [[be-trail-ablation-all-engines-2026-07-09]]。残 = P1-2b (fut_close tie-break、副次)。

## 2026-07-09 — WS3 MFE 分布診断: 選抜基準を「MFE 絶対量」→「MFE/MAE 方向性非対称」へ改訂 (rule:R3)

- T2 FAIL 後の WS3 初手 ([[ws3-mfe-distribution-2026-07-08]])。365d baseline 6 pair、N=6,995 entries / 104 cells の forward MFE/MAE (H∈{6..96} bars) を exit 非依存で計測 (`tools/ws3_mfe_scan.py`)。
- **発見1**: MFE 絶対量は豊富 (h24 p50 15-30p) — live 診断の「winners MFE 5.18p」は exit 打ち切りアーティファクトと確定。
- **発見2**: MFE/MAE 比の母集団中央値 0.88 = **価格は走るがシグナル方向に走らない**。希少資源は方向性非対称 (ratio≥1.3 = 7/79 cells)。horizon 持続型 2 cells (lin_reg_channel×EUR_USD 1.38→1.94 / dt_fib_reversal×USD_JPY 1.29→2.05) を次期 pre-reg の検証対象に固定。
- 影響トレード: なし (R3 純診断)。roadmap WS3 節の選抜基準を改訂。事後選択セルの promote 禁止を明記。

## 2026-07-08 — T2 exit-repair grid BT verdict: ❌ FAIL / H0 採択 → WS3 全振り (rule:R1)

- pre-reg LOCK ([[exit-repair-tp-sl-prereg-2026-07-07]]) の機械的実行。executor は Codex queue → claude 直接実行に変更 (user 運用委任、期日 07-21 の 13 日前倒し)。
- **結果: 全 9 構成 FAIL** — BH-FDR q=0.10 全構成 p=1.0 (日次ブロックブートストラップ B=10,000、208 取引日) / WF 3-fold 全構成 0/3 / 摩擦調整 EV 全構成負 (最良 tp0.4×sl0.6 で −2.96 p/t、baseline −6.64 から +3.67 改善もレバー不足)。
- ナイフエッジ3点検査: メカニズムは診断通り作動 (TP-hit 0.215→0.44、EV 両軸厳密単調) した上での**構造的 FAIL**。lag-1 ρ ≈ ±0.06 で自己相関影響なし。感度 run (pre-#58 code、mixed 込み) も同結論 FAIL 0/9。
- 実装: `tools/exit_repair_tp_sl_grid_bt.py` (spawn 分離 grid runner) + `app.py` BT 専用 env hook (`BT_TP_MULT`/`BT_SL_MULT`、env 未設定で完全 no-op)。EUR_JPY 15m parquet の 2ヶ月 stale (silent window 罠) を差分修復。
- **影響トレード: なし (純研究、live パラメータ不変更)**。変わるのは roadmap の主戦線 — §4 固定分岐により **WS3 シグナル張り替え (MFE 分布ベースの entry 再設計) が v2.3 の主戦線**に。exit 側レバーの再試行は禁止。
- 成果物: `raw/bt-results/exit_repair_tp_sl_grid_2026_07.{json,md}` + 感度版。registry `exit-repair-bt-deadline` inactive。verdict 詳細: [[exit-repair-tp-sl-prereg-2026-07-07]] §8

## 2026-07-07 — WS4 Phase B follow-up: shadow 修復層の oscillation 封鎖 + 停止可視化 (PR #59 敵対的レビュー起点, rule:R3)

- PR #59 (P1-3 stale SHADOW_MIGRATION 削除 + P1-9 Kelly raw 化) / PR #60 (T4 摩擦調整 EV マップ) のマージ後、10-agent 敵対的検証 workflow が confirmed した欠陥への追修:
- **oscillation 封鎖**: SHADOW_DRIFT_BACKFILL (2026-05-03) が leak backfill の shadow 分類 (pre-RULE_TS の OANDA-filled リーク行) を次 restart で無条件に live へ巻き戻し、冪等マーカーが再修復を恒久ブロックしていた (空 DB 4-init で再現)。drift rollback の WHERE に `force_demoted_live_leak=0` 除外を追加。
- **修復層停止の可視化 (P2-3 部分)**: leak/flag_drift backfill の unsafe/exception 停止を `[SHADOW_REPAIR_PAUSED]` WARN で毎 restart 表面化。**本番は現在 leak 側 status=unsafe で停止中と実測** (P2-10 新設、修復 chip 化済)。
- **P1-9 スコープ訂正**: `_evaluate_shadow_promotions` は production call site ゼロの dead code — P1-9 で武装されるのは live promotion loop の `_kelly_block` のみ (P2-11 新設)。ゼロ境界は `< 0` が仕様と裁定 (`<= 0` 化は正エッジ誤 block の対称害で不採用)、mirror テストを production 述語に整合。
- 影響トレード: なし (シグナル判定・lot 不変更)。変わるのは修復層の分類安定性と観測性のみ。
- 回帰: tests/test_ws4_phase_b_followup.py (5 cases、oscillation は main で red 確認済み) + test_kelly_promotion_gate.py 整合。詳細: [[fable5-system-audit-2026-07-02]] P1-3 follow-up / P2-3 / P2-10 / P2-11

## 2026-07-07 — HTF mixed cell stop: trendline_sweep×GBP_USD live 転送停止 + mixed 診断タグ是正 (rule:R2/R3)

- T1 forensic §7 の異常 (30d 大負け4発 −53.6p 全てに「⚖️ 4H+1D 不一致 → シグナル抑制中」タグ付き LIVE 発注) の根本原因を特定: **タグは診断のみで、v9.1 HTF Hard Block は bull/bear 限定 — mixed は DTE 候補フィルタ no-op**。trendline_sweep は self-contained HTF guard も持たず、demo_trader v9.3 regime gate も ELITE_LIVE 免除で第2層不在。
- R2 執行: `DaytradeEngine.HTF_MIXED_LIVE_STOP_CELLS = {(trendline_sweep, GBP_USD)}` — mixed 時に候補除外 + shadow 退避 (`[HTF_MIXED_LIVE_STOP]` タグ、is_shadow=1)。根拠 = clean live (06-03..07-03) mixed N=15 EV=−3.38p/−50.7p vs aligned N=4 +1.5p、shadow mixed N=7 EV=−7.20p corroborate。
- R3 執行: reasons の mixed 文言を実状態記述へ是正 (「4H+1D 不一致」substring は query 互換維持)。
- 影響トレード: trendline_sweep×GBP_USD の HTF mixed 状態エントリーが以後 live に乗らない (shadow は継続)。aligned (bull/bear) 状態は不変。BT は `compute_daytrade_signal` 内適用のため自動同期。
- 回帰: tests/test_htf_mixed_live_stop.py (6 cases)。再 live 化は R1 のみ。詳細: [[mtf-mixed-gate-noop-forensic-2026-07-07]]

## 2026-07-06 — order 層 per-bar dedup — engine 再構築で無効化された strategy 内 guard の構造代替 (rule:R3)

- T8 forensic #2 帰結: DaytradeEngine/HourlyEngine が poll 毎に再構築され strategy instance の per-bar dedup/cooldown が live デッドコードだった問題に対し、order 層 (demo_trader) に `(entry_type, instrument, signal, closed_bar_ts)` の per-bar dedup を追加。
- primary `_tick_entry` と shadow emit DB insert が同一 key 空間を共有 (SHADOW_ALWAYS も bypass 不可)。recent_emit は第2防御として併存。block は `order_bar_dedup` counter で観測可能。
- 影響トレード: 同一バー内の重複 emit (live/shadow とも) が DB insert 前に遮断される。1バー1シグナルの BT 前提に live を整合させる方向の変更。multi-bar cooldown の代替は forensic #3 (BT 突合) 後に判断。
- 回帰: tests/test_dedup_gate_all_paths.py (12 cases)。詳細: [[t8-week1-gate-breach-2026-07-06]]
## 2026-07-06 — T9: Kalman D7 qualifying-bar telemetry + pre-reg 分母付き基準へ追補 (rule:R3)

- roadmap v2.2 T9 (最後の未完了項目)。kalman_d7 に QUALBAR print telemetry を追加 — PO-UP transition バー毎に DIST/GAP/ATR-Q/RSI/session の pass/fail と emit 判定を 1 行出力。0-fire の原因 (dormant / filter落ち / 経路ブロック) が production ログで判別可能に。
- class 属性 dedup により engine 毎tick再構築でも同一バー 1 行 (3 variant 共有)。
- pre-reg 2026-05-28 に追補: 判定を「QUALBAR 数 (分母) vs 発火数 (分子)」の表に書換え。emit=True で発火ゼロなら R3 即時 forensic。
- prereg-trigger-registry に `t9-kalman-d7-fire-info` 追加 (prefix マッチ対応を watch tool に実装、BT 期待 3.9/週)。
- 影響トレード: なし (観測性のみ、シグナル判定・lot 不変更)。回帰: tests/test_kalman_d7_qualbar_logging.py (5) + prefix マッチ 1 件。

## 2026-07-06 — pre-reg トリガー監視の自動化 + env gate 宣言整合チェック (rule:R3)

- **tools/prereg_trigger_watch.py** (新規): 機械判定可能な pre-reg トリガー/決定点を registry (decisions/prereg-trigger-registry.json) で管理し毎日評価。Tier A daily cron (quant_gate_status.py) の Discord レポートに統合。初期登録 3 件: T5 復帰条件 (D1<159.50) / sweep P-S1(a) DEFER 決定点 (N≥10 or 09-30 N<5) / hull 頻度 band
- **scripts/check.py チェック8** (新規): demo_trader.py が読む `*_LIVE_ENABLE` env が render.yaml 未宣言なら WARN — decision-without-provisioning クラス (watchdog token / carry dip gate / T5 未執行の 3 例) の構造防止
- **render.yaml**: `KALMAN_D7_LIVE_ENABLE` / `USDJPY_CARRY_DIP_LIVE_ENABLE` を sync:false で宣言 (dashboard 値は不変更)
- 影響トレード: なし (監視・観測性のみ)。背景: T5 トリガーが監視主体不在で 18 日間未執行だった事故
## 2026-07-06 — T5 pre-reg 発動執行: JPYキャップ撤退 SIZE lever 0.5x (rule:R2)

- [[jpy-cap-exit-prereg-2026-06-12]] トリガー1「USD_JPY D1 close > 160.80」が **2026-06-18 に成立済み** (161.295、以降14営業日連続、max 162.631) と本日検出。18日の執行ギャップ (監視機構不在) — pre-reg 文書に発動記録+教訓を追記。
- 執行: `_resolve_jpy_cap_exit_size_lever` — 対象4戦略 (vsg_jpy_reversal / dt_sr_channel_reversal / vix_carry_unwind / ema200_trend_reversal) の **LIVE lot 0.5x** (SIZE lever、lot チェーン最後段)。Shadow 無変更 (原則3)。code pin (`JPY_CAP_EXIT_SIZE_LEVER_ACTIVE`、env/KV 経路なし) + 回帰テスト 5 件。
- **Floor 1000u**: vix Overlap pilot の 1000u 固定検証ロット契約 ([[vix-carry-grail-removal-overlap-1000u-2026-06-15]], agg-Kelly bypass の正当性根拠) と衝突するため `max(1000, 0.5x)` で適用 — 1000u 検証ロットは no-op、1000u 超のみ半減。
- 影響トレード: 以後の対象4戦略 LIVE 送信 lot が半減 (`(JPYCAP0.5x)` lot tag + trade_reason で識別可)。Shadow/BT 系列は不変。
- 復帰 = 復帰条件 (D1<159.50 回帰+介入再確認 / BOJ 後 clean N≥10 EV>0) の KB 記録 + テスト変更を伴う PR のみ。

## 2026-07-06 — T8 初週 R2 STOP: hull/sweep LIVE 転送を code pin で停止 (rule:R2)

- pre-reg [[sweep-hull-live-week1-prereg-2026-06-12]] 拘束ゲート抵触 (sweep=ゲート① 24日 fill 0 / hull=ゲート④ 同一バー再emit) → 裁量禁止条項に従い LIVE 転送停止。
- env フラグでなく `_*_LIVE_ENABLE = False` の code pin (lesson: KV disable は pin にならない)。Shadow は原則3で継続。
- 影響トレード: なし (両戦略とも live fill 実績 0)。復帰 = forensic 完了 + 再 LOCK PR のみ。
- 詳細: [[t8-week1-gate-breach-2026-07-06]]

## 2026-07-06 — rnb WAIT entry=0 恒常汚染の根絶 + QUALBAR print 化 (観測性 R3 バッチ)

- **rnb_usdjpy**: `compute_rnb_signal` WAIT dict の `entry: 0` (2026-04-05 起源) が PRICE_HISTORY_GUARD 発火 ~2,880件/日 の唯一の発生源と特定 → WAIT に実 Close を埋める 1 行修正。ガードの残発火が真の fetch 障害シグナルに戻る。
- **usdjpy_carry_dip QUALBAR**: `logger.info` は本番 handler 未設定で破棄されており T7 E2E 検証が構造的に不可能だった → `print(flush=True)` 化。
- 回帰: tests/test_rnb_wait_entry_price.py (3 cases)。影響トレードなし (シグナル判定・tier/lot 不変更、観測性のみ)。
- 詳細: [[rnb-wait-entry-zero-forensic-2026-07-06]]

## 2026-07-04 — Fable5 監査 Phase A バッチ: edge-cell DD mult / 孤児クローズ年齢ガード / strategy Kelly 汚染除去 (rule:R2+R3)

- **P0-1 (user 決裁)**: edge cell force-live の固定 lot に `max(1000, int(lot × _dd_lot_mult))` を適用。DD defensive 0.2x 下で stage3=10000u フル送信だったバイパスを封鎖、1000u floor でクリーン N 蓄積は継続。
- **P0-2**: `_sync_demo_to_oanda` 孤児クローズに `_ORPHAN_MIN_AGE_SEC=600` の openTime 年齢ガード (parse 不能も fail-safe skip)。再起動直後の正規 live ポジション誤クローズ競合窓を封鎖。
- **P1-1**: `_get_strategy_kelly` を `_get_strategy_kelly_clean` へ委譲 — 実弾サイジング 2 経路 (dynamic boost / half-Kelly cap) + shadow promotion の all-time 汚染 (pre-cutoff/XAU/shadow 混入) を除去。
- **影響トレード**: DD defensive 継続中の E2/E9 マッチが縮小サイズ (5000→1000u 等) で送信される。per-cell EV 評価は pips ベースのため非影響。Kelly boost/cap はクリーン N<10 戦略で不発化 (誤 boost の停止)。
- 回帰テスト 16 本を同コミットで追加。
- 詳細: [[fable5-phase-a-p0-fixes-2026-07-03]] / 監査 SSOT: [[fable5-system-audit-2026-07-02]]

## 2026-07-03 — _price_history 0価格ガード (spike/velocity gate 誤発火修正, rule:R3)

- P1 データ整合性バグ修正: fetch 全滅時の `current_price=0/None` が `_price_history`
  に混入し、spike gate が range=価格そのもの (07-02 12:31 UTC 実例: 16153.1pip/60s =
  USDJPY 161.53) で誤発火 → 当該 instrument **全戦略**の live 送信を 60s〜30min 封鎖
  (shadow-eligible は shadow 化、それ以外は drop) していた。
- 3層ガード: L1 append 前 `price>0` 検証 + `[PRICE_HISTORY_GUARD]` 検出ログ /
  L2 spike 計算側 `p>0` フィルタ / L3 velocity 計算側 `p>0` + current_price 有効時のみ評価。
- **影響トレード**: データソース障害と同期した spike/velocity の shadow 化・drop が本デプロイ
  以降消滅。07-02 12:31-13:42 の vix_carry_unwind 窓内 14/14 shadow はこのバグ起因
  (清浄データでの窓内 live 実証は依然 N=1)。正常 tick での spike/velocity 発火は不変。
  tier/lot 変更なし。
- TDD 8 cases: `tests/test_price_history_zero_price_guard.py`。
  詳細: [[zero-fire-diagnosis-carrydip-vix-2026-07-02]] §2.6

## 2026-07-03 — Watchdog CODE_PIN_SYNC: code pin と KV stage の自動同期

- watchdog に `CODE_PINNED_CELLS` (modules/edge_cell_promote.DISABLED_CELLS のミラー、CI equality テストで乖離固定) を追加。pin cell の KV stage!=0 を検出したら new_stage=0 を発行して同期 (rule:R3 整合性修正)。
- 動機: 2026-07-02 zombie incident で E4 KV が 1 に残置 (DECREMENT stage>=2 ガードのため自然回復しない)。「eligible と effective を区別する」教訓の恒久対応。
- **影響トレード**: なし。lot 決定は従来どおり code pin (`DISABLED_CELLS`) が支配し、本変更は KV 表示状態のみ同期する。
- 詳細: [[edge-cell-e1-e4-code-disable-2026-07-02]] 追記 2026-07-03

## 2026-07-02 — Edge cell E1/E4 code-level DISABLE + watchdog DECREMENT 床バグ修正

- `DISABLED_CELLS` に E1 (dt_bb_rsi_mr ASN SELL) / E4 (bb_rsi_reversion NY SELL) を追加 (rule:R2)。T10 KILL ([[bb-rsi-t10-kill-2026-07-02]]) 拘束事項3 の実施。
- **影響トレード**: E4 経由の bb_rsi_reversion live 発火 (2026-07-02 13:08-19:55 UTC の 11 件が最後) は本デプロイ以降ゼロ。E1 は LOCK 以降 live N=0 で実挙動不変。dt_bb_rsi_mr の通常 PAIR_PROMOTED 経路は不変。
- watchdog `max(1, stage-1)` 床バグ修正 (rule:R3) — stage=0 セルの 0→1 再武装 (zombie) を根絶。**2026-07-02 10:18Z〜デプロイまでの間、E4 の KV disable は 15 分毎に無効化されていた**点に注意 (該当 live 4 件は分析時に E4 force-live として扱う)。
- 詳細: [[edge-cell-e1-e4-code-disable-2026-07-02]]

## 2026-07-02 — Aggregate Kelly Gate raw-fix + 1000u 契約 min-lot bypass (rule:R3+R2)

- P1 死にゲート修正: `kelly_criterion` の `max(0,·)` クリップにより v9.0 SHIELD
  Aggregate Kelly Gate (`< 0` 判定) が構造的に発火不能だった。`full_kelly_raw`
  (非クリップ) を追加し `_get_aggregate_kelly` を raw 化。
- interplay (user 決裁): 1000u 固定契約 3 戦略 (vix_carry_unwind /
  usdjpy_carry_dip_accumulator / sweep_reversion_eurgbp_late) は
  allowlist AND 実効 units<=1000 AND 非XAU の二重ガードで gate bypass。
  hull_donchian_fade (5000u) は対象外。
- 影響: aggregate raw Kelly<0 (2026-07-02 時点 edge=-0.3617) の間、promoted
  非 sentinel/非 edge-cell/非 1000u契約 の OANDA 転送が初めて実ブロックされる。
  tier/lot 変更なし。TDD 10 cases。
- Decision: `decisions/agg-kelly-gate-raw-fix-minlot-bypass-2026-07-02.md`

## 2026-05-21 — SR-family shadow_emit OANDA audit restoration

- `shadow_emit_signals` が `_tick_entry` を経由せず `demo_trades` に直接 Shadow row を書くため、SR-family の OANDA audit skip row が欠落していた問題を修正。
- `sr_*` shadow emit は `demo_trades` 記録後に `oanda_audit` へ `bridge_status=skipped` / `block_reason=shadow_tracking` を永続化する。
- 対象は監視可視性の復旧のみ。OANDA 発注、Live/Shadow 判定、lot sizing は変更しない。

## 2026-05-18 — /api/oanda/stats range window 修正

- OANDA stats endpoint が frontend の `range=today|7d|30d|all` を無視して全期間集計していた問題を修正。
- 既定 window を demo stats と同じ 30d + `2026-04-08T00:00:00` floor にし、`range=all` も fidelity cutoff 以降のみ集計。
- `_filters` / `_db_path` を返し、stats 系 endpoint の表示条件を監査可能にした。

## 2026-05-18 — trend_rebound THESIS_INVALID FORCE_DEMOTED

- C audit verdict により `trend_rebound` を FORCE_DEMOTED に固定。
- 21d shadow N=60 WR=33.3% EV=-1.29p PF=0.66 Kelly=0.000 WF=0/3。
- `trend_rebound` x USD_JPY の PAIR_PROMOTED と EUR_USD の PAIR_DEMOTED を撤去し、
  FORCE_DEMOTED 一括管理へ統合。
- Decision: `decisions/trend-rebound-thesis-invalid-2026-05-18.md`。

## 2026-05-18 — HourlyEngine Shadow Ramp Activation

- 全 10 `daytrade_1h*` modes を `auto_start=True` に変更し、HourlyEngine dormant 状態を解除。
- `_shadow_always` に KSB+DMB+5 PriceShockRev を frozenset 固定し、H1 alpha source を一括 Shadow-only にした。
- XAU modes と 15m/scalp Live 経路は変更なし。Decision: `decisions/hourly-engine-shadow-ramp-2026-05-18.md`。

## 2026-05-18 — Price-Shock Rev Live Activation v2 MIN Lot (rule:R1)

- 5 Price-Shock Rev H1 戦略を Tier 2 Live MIN lot に移行。
- `_shadow_always` から Price-Shock Rev を削除し、KSB/DMB は Shadow-only 維持。
- Live lot は 1000u 固定。lot ramp は N>=30 pre-reg evaluator の提案のみで自動変更しない。
- N>=10 watchdog は EV<0 または Wilson_lower<0.40 で auto-demote state を記録。Decision: `decisions/price-shock-rev-live-activation-2026-05-18.md`。

## 2026-05-18 — Price-Shock Reversion Tier 1 Phase B-1 Shadow

- H1 negative shock LONG 5 戦略を `strategies/hourly/` に追加。
- BT runner と `shift(1)` / rolling 252 / vol quintile を bar-by-bar 一致。
- `demo_trader` で Shadow-only 強制、EUR_GBP/EUR_AUD shared lock を追加。
- Live promote は `decisions/price-shock-rev-promote-criteria-2026-05-18.md` で別判定。

## 2026-05-18 — PRIME v2 Apply

- PRIME v2 apply: 5 entries demoted to Tier C per P1 re-eval verdicts.
- EDGES replaced with the 2026-05-18 Render shadow non-XAU recomputation.
- All current PRIME matches remain Shadow-only; A/B live-lock structure preserved for future candidates.

## 2026-05-18 — PRIME B' Micro LIVE Forward-Fix

- Corrected the grade mismatch between LIVE promotion and Micro LIVE exploration.
- Revived `fib_reversal_PRIME` and `sr_fib_confluence_GBP_ADXQ2` as Tier B `0.05x` measurement cells.
- Kept the other 4 PRIME entries at Tier C `0.0`; no Tier A entries active.
- Existing watchdog safety net remains unchanged: auto-demote at Live `N>=10` and `EV<0`.

## Fidelity Cutoff Timeline

```
2026-04-02  システム稼働開始
     |
2026-04-08  ★ Fidelity Cutoff (v6.3 SLTP修正後)
     |       ├── この日以降のデータ = "クリーンデータ"
     |       └── 以前のデータ = "バグ汚染データ"（SLTPチェッカーバグ含む）
     |
2026-04-09  v7.3-v7.6: XAU修正チェーン
     |       └── XAUデータ: v7.5以前は MAX_SL_DIST=$0.20バグで汚染
     |
2026-04-10  ★★ v8.0-v8.3: 戦略大改革
     |       ├── v8.0: vol_momentum 2.0x, engulfing_bb停止, TREND_BULL遮断
     |       ├── v8.1: TREND_BULL MR免除
     |       ├── v8.2: orb_trap PAIR_PROMOTED, vol_momentum 1.0x
     |       ├── v8.3: 確認足フィルター（bb_rsi/fib/ema_pullback）
     |       └── v8.3以降のデータ = "確認足効果測定用"
     |
2026-04-10  ★★★ v8.4: XAU停止 + Shadow汚染除去
     |       ├── XAUモード停止: scalp_xau, daytrade_xau auto_start=False
     |       ├── get_stats() is_shadow=0 フィルター追加
     |       └── v8.4以降 = "FX-only クリーンデータ"
     |
2026-04-12  Knowledge Base構築
     |       └── 評価基盤の確立
     |
2026-04-12  ★ v8.5: 学術文献6新エッジ戦略 (全Sentinel)
     |       ├── session_time_bias, gotobi_fix, london_fix_reversal
     |       ├── vix_carry_unwind, xs_momentum, hmm_regime_filter
     |       └── 25論文ベース、DaytradeEngine 32戦略化
     |
2026-04-12  ★★ v8.6: 本番昇格 + モード再編
     |       ├── session_time_bias × 3ペア PAIR_PROMOTED (BT WR=69-77%)
     |       ├── london_fix_reversal × GBP_USD PAIR_PROMOTED (BT WR=75%)
     |       ├── london_fix_reversal × USD_JPY PAIR_DEMOTED (BT WR=28.6%)
     |       ├── xs_momentum × USD_JPY PAIR_DEMOTED (BT EV=-0.129)
     |       ├── scalp_eurjpy auto_start=False (friction/ATR=43.6%, 構造的不可能)
     |       ├── scalp_5m_eur + scalp_5m_gbp 新規モード追加 (5m摩擦改善)
     |       ├── 金曜/月曜ブロック全撤去 — 原則#1「攻める」準拠
     |       ├── GBPアジアセッション除外フィルター実装
     |       ├── DSR (Deflated Sharpe Ratio) 実装 — Bailey & Lopez de Prado (2014)
     |       └── BT/Live乖離分析: bb_rsi 25pp乖離の原因分解完了
     |
2026-04-12  v8.7: BT基盤強化
     |       ├── BT Friction Model v3 (Spread/SL Gate + RANGE TP + Quick-Harvest反映)
     |       ├── backtest-long DT/1H対応 (120-365日チャンクBT)
     |       └── BT/Live乖離: Scalp 14-27pp→5-10pp, DT 5.5-10pp→2-4pp (期待)
     |
2026-04-12  v8.8: 生データアルファマイニング
     |       ├── vol_spike_mr: 3x range spike fade (BT JPY PF=1.92, 全戦略最高)
     |       ├── doji_breakout: 3連続doji breakout follow
     |       ├── post_news_vol × USD_JPY PAIR_DEMOTED (120d WR=0%)
     |       └── ema200_trend_reversal × USD_JPY PAIR_DEMOTED (120d WR=0%)
     |
2026-04-13  ★★★ v8.9: Equity Reset — クリーンデータ起点
     |       ├── 旧DD: 2,899pip (289.9%) ← XAU(-2,280pip) + pre-cutoffバグ汚染
     |       ├── リセット: v8.4(2026-04-10T12:00)以降FX-only非Shadowで再計算
     |       ├── 新DD: 8.4pip (0.8%) → lot_mult=1.0x (フルロット)
     |       └── ワンショットマイグレーション (eq_reset_v89フラグで1回のみ実行)
     |
2026-04-17  ★ v9.2.1: MTF Regime Engine + v9.2 guardrail 無効化
     |       ├── D1×H4×H1 階層 regime labeler (7-class)
     |       ├── EUR_USD η² 105× improvement, flip rate 6.1%→0.6%
     |       ├── v9.2 guardrail デフォルト無効化 (6.5年検証で符号逆)
     |       └── shadow_monitor + DB mtf_* カラム追加
     |
2026-04-17  ★★ v9.3 Phase A-C: Strategy-aware MTF + P0 Family Map Forensics
     |       ├── Phase A: 戦略ファミリ考慮 retrospective (LIVE aligned WR +22.9pp)
     |       ├── Phase B: 本番OOS反実仮想 (+508p 改善) — TF sign flip 検出
     |       ├── Phase C P0: 3戦略 mislabel 修正 (macdh_reversal/engulfing_bb → TF, ema_cross → MR)
     |       ├── CORRECTED map で ALL Δ PnL +306p→+1129p (3.7×), 全family符号一致
     |       └── research/edge_discovery/strategy_family_map.py (production module)
     |
2026-04-17  ★★★ v9.3 Phase D+E: A/B Gate Routing + REGIME_ADAPTIVE
             ├── **Phase D**: Hash-based A/B routing (MD5 mod 2 → mtf_gated / label_only)
             │   ├── DB: gate_group / mtf_alignment / mtf_gate_action 追加
             │   ├── Group A conflict → LIVE→SHADOW downgrade (soft gate)
             │   └── 50/50 分布確認 (N=1000 ±50)
             ├── **Phase E**: REGIME_ADAPTIVE_FAMILY (regime別 family override)
             │   ├── bb_rsi_reversion: trend_up=TF / trend_down=MR
             │   ├── fib_reversal: trend_up=MR / trend_down=TF
             │   └── LIVE ΔWR +2.4pp→+9.3pp (4×), IS aligned gap +12.0pp
             └── Tests: 234 passed (new: test_ab_gate.py 7 + TestRegimeAdaptive 7)

2026-04-20  v9.3 Phase F: FAMILY MAP 拡張 — ELITE_LIVE/PAIR_PROMOTED 6戦略追加分類
             ├── **TF追加**: gbp_deep_pullback, trendline_sweep (wiki Category根拠)
             ├── **MR追加**: vwap_mean_reversion, wick_imbalance_reversion (wiki MR根拠)
             ├── **SE追加**: london_fix_reversal (Krohn 2024), vix_carry_unwind (Brunnermeier 2009)
             ├── 未分類→"unknown"から"conflict/neutral"へ: A/B gate が ELITE_LIVEにも機能するように
             ├── RANGINGレジーム下: gbp_deep_pullback/trendline_sweep → conflict → shadow降格（正常）
             ├── RANGINGレジーム下: vwap_mean_reversion/wick_imbalance_reversion → aligned（正常）
             ├── pending (BT forensics必要): doji_breakout, post_news_vol, squeeze_release_momentum
             └── Tests: 234 passed (既存テスト全pass、新分類はwiki根拠で実装)

2026-04-20  ★ v9.x Quant Readiness: 2D v2 Pre-Registration + Dashboard (parallel A+B)
             ├── **Task A — Regime 2D v2 Pre-Registration (data snooping 防止)**:
             │   ├── knowledge-base/wiki/analyses/regime-2d-v2-preregister-2026-04-20.md
             │   ├── 43戦略の family/regime×direction 仮説を backfill 前に pre-commit
             │   ├── Gate 閾値確定: N≥50/cell, |ΔWR|≥10pp, Bonferroni α=0.05/K, IS/OOS 符号一致
             │   ├── Pass/Fail 判定を機械化可能な形で記述 (§3.7)
             │   ├── 禁止事項 (§5): 閾値/仮説の事後調整, cell 除外の事後正当化, 1日データ実装
             │   ├── Bailey & Lopez de Prado (2014) *Backtest Overfitting* 流儀の pre-register
             │   └── Post-execution 記録枠を空のまま commit → data snooping 抑止
             ├── **Task A — Rescan script**: scripts/regime_2d_v2_rescan.py (~470行)
             │   ├── --trades-json input / --output-dir / --dry-run
             │   ├── Fisher's exact (two-sided, SciPy 非依存) + Bonferroni strict
             │   ├── matrix_all / asymmetry_strict / hypothesis_check / gate_candidates / sanity_check
             │   ├── 既存 REGIME_ADAPTIVE_FAMILY (bb_rsi/fib) の sanity check も同時実行
             │   └── Dry-run smoke test pass (synthetic 600 trades, k_eff=1)
             ├── **Task B — Quant Readiness Dashboard**: tools/quant_readiness.py (~340行)
             │   ├── --api / --json / default https://fx-ai-trader.onrender.com
             │   ├── Data accumulation (Live/Shadow N, Kelly progress)
             │   ├── Gate thresholds (Kelly N≥20, DSR N≥50, PP review N≥30+EV>0, FD-risk EV<-0.5)
             │   ├── mtf_regime coverage (labeled/total, regime diversity, missing list)
             │   ├── Alerts (Kelly/coverage/trend_down zero/FD-risk triggers)
             │   ├── セキュリティ: URL scheme allowlist + custom opener (HTTP/HTTPS のみ) →
             │   │   file:// / ftp:// 攻撃面遮断 (CWE-939), verified SSL context (CWE-295)
             │   └── 本番 smoke test: Live=14/20 (70% Kelly), Shadow=849, coverage=30.1% (target 80%)
             │       → trend_down_* 0件警告, backfill 前提の blocker 検出
             ├── **Tests**: tests/test_quant_readiness.py 13 cases
             │   └── URL validation (file/ftp reject), build_accumulation/gate/coverage, alerts, render
             ├── tier_integrity_check --check: PASS (ERROR=0)
             ├── strategies_drift_check: PASS (65 pages clean, exit 0)
             └── 判定プロトコル: **実装提案なし**. 本 commit は "infrastructure 整備" であり
                 backfill 後の 2D v2 rescan / daily readiness snapshot のための pre-commit.
                 実際の strategy 昇格・降格は backfill + N 蓄積後の human review を要求.

2026-04-20  ☆ v9.x Diagnostic: Regime × Strategy 2D Kelly Asymmetry Scan (NO-OP)
             ├── **目的**: 43戦略 × 7 regime × 2 direction の非対称性マトリクスを全探索
             │   └── Phase E (bb_rsi_reversion / fib_reversal) 同等候補があれば REGIME_ADAPTIVE 追加
             ├── **データ**: 本番 API N=786 (Cutoff 2026-04-16以降 / XAU除外 / closed)
             │   └── mtf_regime 本番 DB populate 率 24.5% → research/edge_discovery/mtf_regime_engine で
             │       retrospective labeling (Phase B 済み pipeline 再利用) で 100% カバー
             ├── **結果**: Gate 通過候補 = **0件**
             │   ├── 観測期間 4.6日 → lesson-reactive-changes "1日データ禁止" に抵触
             │   ├── Regime coverage 欠損 (trend_down_* / uncertain が 0 件)
             │   ├── 43戦略中 N≥50/cell を 1つ以上持つのは ema_trend_scalp のみ
             │   ├── Bonferroni α=0.0125 で有意 cell ゼロ (最小 p=0.277)
             │   └── 観測された方向非対称性は全て既存 strategy_aware_alignment で処理済
             ├── **実装**: なし (判断プロトコル #1 違反回避)
             ├── **別 task 提案**: scripts/backfill_mtf_regime.py 作成 → 過去トレードに mtf_regime 注入 → N ≈ 1500+ 規模で再評価
             └── Artifacts: knowledge-base/wiki/analyses/regime-strategy-2d-2026-04-20.md
                 + /tmp/fx-regime-2d-analysis/{matrix_all,asymmetry,asymmetry_strict}.csv

2026-04-20  ★ v9.4: wiki/strategies KB ドリフト一掃 + 検出ツール導入
             ├── 13 ページの Status 行を tier-master.json と整合
             │   ├── bb-rsi-reversion.md: "Tier 1 PP×USD_JPY" → SCALP_SENTINEL + PAIR_DEMOTED(全4ペア)
             │   ├── orb-trap.md: "Tier 1 PP×3ペア" → FORCE_DEMOTED (v9.1 負EV確定)
             │   ├── trendline-sweep.md: "ELITE+FD+PP" → ELITE_LIVE のみ (v9.0 整理)
             │   ├── bb-squeeze-breakout / engulfing-bb / sr-channel-reversal / ema-pullback:
             │   │   FD下のPP死コード記述を削除 (v9.1 cleanup 反映)
             │   ├── london-fix-reversal: "PP×GBP" → Phase0 Shadow (v9.1 GBP PP削除)
             │   ├── vol-momentum-scalp: "SHADOW" → PAIR_PROMOTED×EUR_JPY
             │   ├── three-bar-reversal: "UNI_SENTINEL" → Phase0 Shadow
             │   ├── stoch-trend-pullback: "Sentinel" → FORCE_DEMOTED (v8.9 剥奪)
             │   ├── vol-surge-detector: "Sentinel" → SCALP_SENTINEL + PAIR_DEMOTED
             │   ├── doji-breakout: Status追加 (UNI_SENTINEL + PP×GBP/USDJPY)
             │   ├── fib-reversal: "Tier 2" → FORCE_DEMOTED (Recovery Path active)
             │   ├── liquidity-sweep: "Tier 2 Sentinel" → UNIVERSAL_SENTINEL 明示
             │   ├── post-news-vol: Status 行の USD_JPY をPP→PAIR_DEMOTED に訂正
             │   └── dual-sr-bounce: "FORCE_DEMOTED" → REMOVED (v9.1 死コード削除)
             ├── 旧 Status は「履歴」/「Previously ...」で保持 (削除禁止ルール遵守)
             ├── **新ツール**: tools/strategies_drift_check.py
             │   ├── tier-master.json を truth source として読み込み、md の Status 行を検証
             │   ├── 否定コンテキスト / 履歴マーカーはスキップ
             │   ├── PAIR_PROMOTED scope 内のペアのみ truth と突合
             │   └── exit 1 で pre-commit / CI 組み込み可能
             ├── **テスト**: tests/test_strategies_drift_check.py (11 cases, all pass)
             │   └── 実 KB 回帰テスト込み (test_live_kb_passes_drift_check)
             ├── **lesson**: wiki/lessons/lesson-strategies-page-drift.md
             │   └── lesson-kb-drift-on-context-limit の strategies/ 特化版
             └── 独立ツール設計: tier_integrity_check.py (code 整合) と分離
                 pre-commit 実行順: tier_integrity_check --write → strategies_drift_check

2026-04-20  ★ v9.x Priority 3: Sentinel N 測定バグ修正
             ├── **症状**: UI で 62 戦略中 bb_squeeze_breakout のみ N=1、他 61 戦略 N=0
             │   └── 実測: 本番 DB に closed Shadow trades が 1,466 件存在
             ├── **原因**: `get_trades_for_learning` は is_shadow=0 固定フィルタ
             │   └── `_strategy_n_cache` → `_build_strategy_status_map` の n が Live のみに
             ├── **修正**: `get_shadow_trades_for_evaluation()` 新関数 (is_shadow=1 固定)
             │   ├── `_build_strategy_status_map` に shadow_n/wr/ev 付与
             │   ├── `/api/sentinel/stats` 新設 (entry_type/instrument/after_date フィルタ)
             │   └── `get_trades_for_learning` は**変更なし** (lesson-shadow-contamination 維持)
             └── Tests: 244 passed (new: test_shadow_stats.py 10 = 正例4+負例3+空3)
             参照: [[lesson-sentinel-n-measurement-bug]]

2026-04-20  ★ v9.x Priority 1: Sentinel score_gate バイパス (Clean Slate 窒息対策)
             ├── **背景**: Clean Slate(2026-04-16)以降 Live N=0 / Sentinel N=1(bb_squeeze_breakout only, 62戦略中)
             │   └── score_gate(score<0) が 1日396件ブロック → Sentinel shadow も蓄積不能
             ├── **修正**: demo_trader.py L2761 score_gate に `_sentinel_score_bypass` 追加
             │   ├── SCALP_SENTINEL ∪ UNIVERSAL_SENTINEL のみバイパス (Live 挙動不変)
             │   ├── FORCE_DEMOTED / _ELITE_LIVE / _PAIR_PROMOTED は従来通り score_gate 適用
             │   └── L4179 safety net で is_shadow=True 強制 → 学習汚染リスクゼロ
             ├── **観測性**: Sentinel バイパス時 `[SCORE_GATE] Sentinel bypass:` ログ発行
             ├── **対称性**: spread_wide(L3483) / spike(L3522) と同形パターン
             └── Tests: 234 passed (no new tests — 既存挙動 guard のみ)
             注記: P3 実測で Sentinel N=1,466 判明 → 「N=1」は測定バグ由来。本 bypass は純粋な上振れ策として残存有効。

2026-04-20  ★ v9.x Priority 2: PAIR_PROMOTED SSOT drift 修正 (accounting cleanup)
             ├── demo_db.py `_pair_promoted_overrides` 5 組合せを削除
             │   ├── (ema_pullback, USD_JPY), (fib_reversal, EUR_USD)
             │   ├── (bb_squeeze_breakout, USD_JPY/EUR_USD), (sr_channel_reversal, EUR_USD)
             │   └── 全て v9.1 で demo_trader._PAIR_PROMOTED から既に削除済み → SSOT 二重化解消
             ├── Live 監査 (Render DB, 2046 trades):
             │   ├── fib_reversal×EUR_USD: Live N=51 WR=39% EV=-0.298 PnL=-15p (post 4/7)
             │   ├── bb_squeeze×EUR_USD: Live N=26 WR=11.5% EV=-2.32 (**壊滅**)
             │   ├── sr_channel×EUR_USD: Live N=26 WR=19% EV=-1.20 (**壊滅**)
             │   └── 他 2 組は Live N<20 & Shadow 主体 → 昇格根拠不足
             ├── 365d BT 再検証 Gate: 全 5 組合せが EV≥+0.2 ATR & N≥100 を満たさず
             ├── 60d→180d 符号反転: fib_reversal×EUR_USD (+0.271 → -0.147) — lesson-orb-trap 再現
             ├── 新規 PAIR_PROMOTED 追加: **なし** (Gate 通過候補ゼロ)
             ├── **Retroactive effect**: 起動時 SHADOW_MIGRATION で 66件が is_shadow=0→1 化
             │   └── Kelly プールから stale 負EV trades 除去 → aggregate EV 改善見込み
             ├── **Behavioral change**: なし (5 組合せは既に Live 未送信、shadow 扱い)
             └── 詳細: wiki/analyses/pair-promoted-candidates-2026-04-20.md

2026-04-20  🚨 v9.x Hotfix: resend-shadow-leak — FORCE_DEMOTED が OANDA 実弾送信されるバグ修正
             ├── **症状**: is_shadow=1 の open trade に oanda_trade_id が設定されている
             │   ├── sr_channel_reversal USD_JPY (FORCE_DEMOTED) → oanda_trade_id=320787
             │   ├── orb_trap GBP_USD (FORCE_DEMOTED) → oanda_trade_id=318111
             │   ├── bb_rsi_reversion EUR_USD (PAIR_DEMOTED) → oanda_trade_id=325370
             │   └── vwap_mean_reversion GBP_USD (MTF gate shadow降格) → oanda_trade_id=325362
             ├── **原因**: `_resend_pending_oanda_trades()` (起動時実行) が
             │   `get_open_trades_without_oanda()` を呼ぶ際に `is_shadow` を未フィルタ
             │   → 起動/OANDA再接続時に is_shadow=1 trades も OANDA に送信されていた
             ├── **修正**: `demo_db.py` `get_open_trades_without_oanda()` のSQL に
             │   `AND is_shadow=0` 追加 (1行) → shadow trades は resend 対象外
             └── **lesson**: [[lesson-resend-shadow-leak]]

2026-04-20  ★ v9.5: ema_trend_scalp / trend_rebound Live pair-level breakdown + PAIR_DEMOTED 拡充
             ├── **背景**: Post-P2 Kelly 分析で ema_trend_scalp edge=-0.353 / trend_rebound edge=-0.455
             │   が aggregate edge=-0.1348 の主因と判明 ([[shadow-baseline-2026-04-20]] Phase 2)
             ├── **Live pair-level 実測** (Render prod, is_shadow=0, closed):
             │   ├── ema_trend_scalp: USD_JPY N=19 EV=-0.92 / EUR_USD N=16 EV=-1.22 / GBP_USD N=4 EV=-1.65
             │   ├── trend_rebound:   USD_JPY N=10 EV=-0.78 / EUR_USD N=7 EV=-1.43 / GBP_USD N=1
             │   └── 99% は Fidelity Cutoff (2026-04-16) 以前、v9.2 FORCE_DEMOTE 以降は新規発生なし
             ├── **Shadow↔Live 対照で符号逆転検出** — lesson-orb-trap-bt-divergence 再現:
             │   ├── trend_rebound×USD_JPY: Shadow EV=+1.43 (N=12) → Live EV=-0.78 (N=10)
             │   └── trend_rebound×EUR_USD: Shadow EV=+1.16 (N=7) → Live EV=-1.43 (N=7)
             ├── **Gate (N≥10 ∧ EV≤-0.5 ∧ (WR≤20 ∨ PnL≤-10)) 通過**: 2 combos
             │   ├── ema_trend_scalp×USD_JPY (PnL=-17.5 で PnL criterion 通過)
             │   └── ema_trend_scalp×EUR_USD (既に PAIR_DEMOTED)
             ├── **修正 1**: demo_trader._PAIR_DEMOTED に `(ema_trend_scalp, USD_JPY)` 追加
             │   ├── v8.9 で "SELL PB境界バグ修正済み → 再蓄積" として解除されていたが
             │   │   v9.2 FORCE_DEMOTE で "再蓄積" 方針は無効化。documentation marker として記録
             │   └── 挙動変化なし (strategy が既に FORCE_DEMOTED で OANDA 遮断済)
             ├── **修正 2**: demo_db._force_demoted (shadow migration set) の SSOT drift 修正
             │   ├── demo_trader._FORCE_DEMOTED (18) と demo_db._force_demoted (15) が drift
             │   ├── 欠落: ema_trend_scalp, intraday_seasonality, atr_regime_break
             │   ├── → 起動時 migration で is_shadow=0 残留 trades (ema_trend_scalp Live N=39 等)
             │   │   が shadow pool 化されず Kelly を汚していた bug
             │   └── 修正後、次回起動時 migration で stale Live trades が shadow 化
             ├── **保留**: trend_rebound×USD_JPY (WR=30% PnL=-7.8 で Gate 微不通過、監視継続)
             │   └── 次 Live N≥20 到達時に再判定。lesson-reactive-changes 遵守で反射降格なし
             ├── Validations: tier_integrity_check ERROR=0, strategies_drift_check pass
             └── 詳細: wiki/analyses/ema-tr-live-breakdown-2026-04-20.md
```

2026-04-22  v9.x: TP-hit Quant Analysis (research only, no code change)
             ├── **スコープ**: 全 strategy × pair で TP-hit したトレードの再現性を定量化
             ├── **データ**: `/api/demo/trades?limit=5000` → 非XAU closed 2,267 / WIN 698
             ├── **Phase 1**: Strategy×pair, regime, TF, session, MTF alignment で WR セグメント化
             │   └── 最多 TP-hit = bb_rsi_reversion×USD_JPY (N=127、全 WIN の 18.2%)
             ├── **Phase 2**: TP-hit vs LOSS の feature 分布差 (Mann-Whitney U, Bonferroni)
             │   ├── spread_at_entry: WIN=0.763 < LOSS=0.842 (p=1.94e-5, 有意)
             │   ├── confidence: WIN=59.55 < LOSS=61.16 (負相関, p=1e-3)
             │   └── score: p=0.42 (score_gate は TP-hit 予測力ゼロ)
             ├── **Phase 3-4**: 事前予測可能特徴のみ (post-hoc MAFE 除外) で条件マイニング
             │   ├── 候補 m=107、Bonferroni α=4.7e-4 通過 5 件
             │   └── 高 WR だが 4/5 は Kelly<0 (BEV 押し上げ vs friction キャンセル)
             ├── **Phase 5 安定性** (pre/post cutoff × live/shadow 符号一致):
             │   ├── **最 robust**: bb_rsi_reversion×EUR_USD×BUY (WR 64.5%, EV +1.84 pip,
             │   │   Kelly +0.41, 4/4 window 符号一致) — ただし N=31 境界
             │   └── **最 fragile**: bb_rsi_reversion×USD_JPY×RANGE
             │       pre EV +0.16 → post EV -1.56 (1.7 pip 悪化、[[lesson-orb-trap-bt-divergence]] 再現)
             ├── **DSR 警告**: Bonferroni 通過 5 件は帰無仮説下 FP 期待値 5.4 とほぼ同 → 
             │   family-wise シグナルは弱い、個別採択は stability で決定すべき
             ├── **制限**: Post-cutoff Live N=0、shadow は truncated sample bias 残存、
             │   close_reason 6種(TP_HIT/OANDA_SL_TP/SIGNAL_REVERSE/...)を包括
             ├── **実装提案なし** ([[lesson-reactive-changes]] 遵守) — KB 記録のみ
             └── 詳細: wiki/analyses/tp-hit-quant-analysis-2026-04-20.md,
                 raw/analysis/tp-hit-raw-2026-04-20.csv, scripts/analyze_tp_hits.py

2026-04-22  ★ v9.x: Roadmap-acceleration 二重WF確証による PAIR_PROMOTED 昇格 2件
             ├── **スコープ**: クロスTF walk-forward stability で pos_ratio=1.00 を示した
             │   2セルを Phase0 auto-Shadow / 既存PP未指定 → PAIR_PROMOTED 昇格
             ├── **`streak_reversal × USD_JPY` PAIR_PROMOTED 新規**
             │   ├── P2 15m 365d × 20d window WF (18窓): N=466 EV=+1.362 pos=1.00 CV=0.65 ✅
             │   ├── P4 5m  180d × 30d window WF (7窓):  N=693 EV=+0.948 pos=1.00 CV=0.62 ✅
             │   ├── Bonferroni BT: 5streak BUY N=586 WR=58.7% p=1.3×10⁻⁵
             │   └── 単一TF根拠を超えたクロスTF確証 → 従来 Phase0 inline auto-Shadow を解除
             ├── **`vwap_mean_reversion × USD_JPY` PAIR_PROMOTED 追加**
             │   ├── P4 5m 180d × 30d WF: N=155 EV=+0.925 pos=1.00 CV=0.51 ✅ (最低CV)
             │   ├── 既存PP (EUR_JPY/GBP_JPY/EUR_USD/GBP_USD) に USD_JPY を追加、5ペア化
             │   └── BT 15m 16bar: N=705 WR=55.0% EV=+2.98pip annual +2,099pip
             ├── **根拠プロトコル**: 両セルとも P2(15m)+P4(5m) 二重 WF クロスTF + Bonferroni BT。
             │   lesson-orb-trap-bt-divergence (短期60d BT のカーブフィッティング) を回避するため
             │   365d WF を一次根拠、5m 180d WF を二次確証、単一TF根拠を超える水準を要求した
             ├── **Validations**: tier_integrity_check.py --check ERROR=0 (PP 15→17 entries)、
             │   sync_kb_index.py --write で index.md portfolio セクション更新
             ├── **KB同梱**: wiki/strategies/streak-reversal.md / vwap-mean-reversion.md Status 更新
             │   (lesson-strategies-page-drift / lesson-kb-drift-on-context-limit 遵守)
             └── 詳細: raw/analysis/roadmap-acceleration-synthesis-2026-04-22.md,
                 raw/bt-results/walkforward-365d-w20-usdjpy-2026-04-22.md,
                 raw/bt-results/walkforward-scalp-5m-180d-2026-04-22.md

## バージョン別データ切り口

| 目的 | date_from | 除外条件 | 理由 |
|------|----------|---------|------|
| 全体傾向 | 2026-04-08 | is_shadow=0 | Fidelity Cutoff後クリーンデータ |
| **v8.3確認足効果** | **2026-04-10** | is_shadow=0 | v8.3デプロイ後のみ |
| **XAU停止効果** | **2026-04-10 夕方〜** | is_shadow=0, XAU除外 | v8.4デプロイ後 |
| **FX純粋評価** | 2026-04-08 | is_shadow=0, XAU除外 | FXのみの真のパフォーマンス |
| BT/ライブ比較 | 全期間 | なし | BT乖離幅の把握 |

## 各バージョンの影響範囲

### v7.x (2026-04-09): XAU修正チェーン
| Version | Change | Affected Strategies | Affected Data |
|---------|--------|-------------------|---------------|
| v7.3 | gold PBルーズ化+bbσバグ修正 | gold_trend_momentum | XAU DT |
| v7.4/b/c | extreme_momentum: ADX≥25, MACD-H/EMA9免除 | gold_trend_momentum | XAU DT |
| v7.5 | MAX_SL_DIST: XAU $0.20→$100 | **全XAU戦略** | ★ v7.5前のXAU SLデータは全て汚染 |
| v7.6 | Sentinel units: XAU 1000u→1u | XAU OANDA連携 | XAU audit |

### v8.x (2026-04-10〜): 戦略大改革
| Version | Change | Impact on Data |
|---------|--------|---------------|
| v8.0 | vol_momentum 2.0x, TREND_BULL全遮断 | DT TREBULLトレード消滅 |
| v8.1 | MR免除 (dt_bb_rsi_mr, dt_sr_channel_reversal通過) | DT MRトレード復活 |
| v8.2 | orb_trap PAIR_PROMOTED, vol_momentum 1.0x, bb_squeeze停止 | orb_trap OANDA送信開始 |
| **v8.3** | **確認足(bb_rsi/fib/ema_pullback)** | **★ 即死率の変化を測定する基準点** |
| **v8.4** | **XAU停止 + Shadow除去** | **★ FX-onlyの真のPnLを測定する基準点** |
| v8.5 | 学術文献6新エッジ戦略 (全Sentinel) | 新戦略のライブデータ蓄積開始 |
| **v8.6** | **session_time_bias/london_fix PROMOTED + 5mモード拡張 + DSR実装** | **★ 学術エッジの本番検証開始** |
| v8.7 | BT Friction Model v3 + backtest-long | BT信頼性向上 (乖離幅縮小) |
| v8.8 | vol_spike_mr + doji_breakout + PAIR_DEMOTED追加 | 新アルファ源 + 出血戦略停止 |

## Related
- [[edge-pipeline]] — エッジ仮説の評価はどのデータ期間を使うべきか
- [[independent-audit-2026-04-10]] — "Shadow除去なしにWR/EVは信頼できない"
- [[bb-rsi-reversion]] — WR 52.2% vs 34% の矛盾はデータ期間の差
- [[friction-analysis]] — avg_friction 7.04 は XAU込み。FX-only≈2.5pip
2026-05-04  FX Nexus Step 1 pre-reg and shadow audit scaffolding
             ├── Added FX graph MLE currency value and triangular alpha residual data-layer functions.
             ├── Added opt-in `exec_lag_jitter` timing audit path for DT backtests; default remains 0.0.
             ├── Added `tools/fx_nexus_shadow_audit.py` to produce H1/H2/H3 verdict markdown.
             └── Locked Step 1 criteria in `wiki/decisions/fx-nexus-step1-prereg-2026-05-04.md`.
