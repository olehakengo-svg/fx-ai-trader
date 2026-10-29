# Daily Observations — 2026-10 (S0 intake 層、記述級のみ)

**Protocol**: [[daily-market-review-protocol]] — p 値計算禁止 / α 消費ゼロ / 台帳番号なし / 卒業には ban/estimand 監査必須 / 凍結 look 保有 family の outcome 量は記載禁止 (registry 事前確認)。前月: [[daily-observations-2026-09]]

⚠️ 10-01〜10-12 の wiki-daily run は本ファイルに追記していない (10-08〜10-12 は run 自体が trade-log を残していない)。初エントリは 10-13 の 6 日一括 run。

---

### O-2026-10-13-1: SL `REPLACEMENT` storm が単一建玉で過去最大 (57,311 回)、6 日で 95,229 回 — guard 0 計上・cloud 監査は無言 (執行 QA / 制御系)
- **現象**: 2026-10-08 01:03〜16:17 UTC、`usdjpy_carry_dip_accumulator` LIVE 建玉 #1062664 (1,000u BUY @157.832) に対し `STOP_LOSS_ORDER` `REPLACEMENT` **57,311 回** (tx 114,622、4,163/h、送信間隔 median 0.81 s)。同窓 (10-07T22Z〜10-13T12Z) の 4 建玉合計 **95,229 回 / 190,538 tx**。価格は 317 種、同値再送 35,423 / 上 11,070 / 下 10,817 (反転 6,601)、最長同値 run 1,004 @157.843 (= BE+1.1)。同日 10-08 09Z の時間別 tx **9,670** = `storm_guard.config.max_tx_per_hour` 50 の 97 倍。`storm_guard.totals` は 10-13 12:01Z 時点で全 0 (10-10 / 10-13 の deploy で in-process 状態消失、`enforce: false`)。origin/main の 10-08〜10-13 KB 文書 (daily report / R2 alert / monitor alert / weekly audit / alpha scan、30 本超) に storm・`lastTransactionID`・`REPLACEMENT` の言及 **0**
- **トリガ日**: 2026-10-08 (#1062664 / #1098462)、2026-10-09 (#1178008 / #1211263)。計測 2026-10-13
- **想定メカニズム**: 既知の 2 族 (族 A 同一価格ループ / 族 B trail⇄BE 往復 = SL 2-writer 競合) の混合。新規メカニズムではなく、既知欠陥の規模が建玉 hold 時間 (15h14m) に比例して伸びただけ。検知側の欠陥 = guard 状態が process 内のみ (deploy で消える) + cloud 監視が broker tx を読まない
- **family 候補**: 既存 `storm_guard` 系 (新 family なし)。[[project_weekend_market_halted_retry_storm_2026_09_07]] の「2 族」記述への付記
- **反証可能な予測**: hold が 10h を超える次の LIVE 建玉で REPLACEMENT 回数は 30,000 回超 (率 ≈3,000–4,000/h が不変なら)。逆に 1,000/h 未満なら writer 側に未知の抑制が入ったことになる。guard の `enforce` が true になっていれば `detected.breaker` > 0 が最初の 1 時間で出るはず
- **隣接 ban / 凍結 frame**: registry `storm-guard-enforce-decision` (期日 2026-10-20) / `storm-guard-modify-sl` (10-20) が活性。凍結 look 保有 family ではない (outcome 量の記載制限なし)。[[storm-guard-design-2026-09-22]] 追補節が読み手
- **経路**: 執行 QA → **既存 frame 回付** (`storm-guard-enforce-decision` の根拠材料として本観測を供給)。新規 R1 候補は立てない

### O-2026-10-13-2: learner の blacklist 決定が 10 日ぶりに再発火 (id 96) したが `current_params` に到達していない — O-2026-09-18-1 の 2 例目 (執行 QA / 制御系)
- **現象**: `/api/demo/learning` `adjustments[0]` = id 96、2026-10-12 15:44:42 UTC、`scalp` `entry_type_blacklist_add` `sr_channel_reversal` (WR 25.0% / EV −0.98 / sample 190、`win_rate_at` 39.5 / `ev_at` −0.27) — id 95 (10-02 13:49:59) と全フィールド同一。10-13 12:01Z 時点の `current_params.entry_type_blacklist` = `[]`、`strategy_status[sr_channel_reversal].blacklisted` = false / `enabled` = true。両 run とも書き込みだけが起き、読み側に反映されていない
- **トリガ日**: 2026-10-12 (計測 2026-10-13)
- **想定メカニズム**: O-2026-09-18-1 と同じ (学習結果の永続先と `current_params` の読み出し元が一致していない、または deploy で揮発)。10-12 15:44Z の発火は 10-10 12:17Z deploy の後なので「deploy で消えた」では説明できず、書込先≠読出元が有力
- **family 候補**: 既存 O-2026-09-18-1 family への付記 (独立観測 2 件目 — 異なる日付、同一 event 種)
- **反証可能な予測**: 次に id 97 が同内容で出れば「10 日周期の再評価が毎回 no-op」が確定。`entry_type_blacklist` が `[]` 以外になれば本観測は棄却
- **隣接 ban / 凍結 frame**: なし (監査は卒業時)。未決 5「learner no-op 修復」(user 決裁待ち) が既存の受け皿
- **経路**: 既存 family 付記 / 記録のみ

---

### O-2026-10-15-1: `storm_guard` が storm 2 建玉を初めて全数捕捉 (488/488、15/15 + 失敗 125) — 10-05「guard 外の 2nd writer」前提の格下げ (執行 QA / 制御系)
- **現象**: 2026-10-14 05:56:50〜06:42:53 UTC、`usdjpy_carry_dip_accumulator` LIVE #1253195 (1,000u BUY @158.192) に `STOP_LOSS_ORDER` `REPLACEMENT` **488 回**、全て 158.208 (BE+1.6) = 純族 A、自然停止 17 分後に SL 市場到達 +¥16。同日 12:30:05〜12:30:16 に `kalman_d7_po_dn_flip` #1254177 に **15 回** (上 8 / 下 6、族 B)、直後 trail SL +¥157。`/api/oanda/status.storm_guard` (10-15 06:35Z): `trades` に両建玉、`sent_total` 488 (= broker 488) / 140 (成功 140−`failed_total` 125 = 15 = broker 15)、`totals.evaluated` 628、`breaker_trips` 2、`detected` breaker 528 / idempotent 51 / monotonic 18 / deadband 10、`skipped` 全 0 (`enforce: false`)。時間別ピーク 06Z 680 tx/h = `max_tx_per_hour` 50 の 13.6 倍
- **トリガ日**: 2026-10-14 (計測 2026-10-15)
- **想定メカニズム**: guard の in-process 状態が窓中に消えなかった (05:56Z 以降 deploy なし — origin/main は PR #328 04:33Z 以降 docs/data commit のみ) ため、writer の全送信が guard を通過した。10-05 の捕捉率 50.5% は「窓中の状態消失」でも説明可能 ⇒ 「全モードに guard 外の 2nd writer」説は 1 観測で保留。SL 2-writer 競合 (trail vs BE) 自体は #1254177 の往復で再現しており別問題。kalman 側 `failed_total` 125 は SL 約定後の modify 継続 (broker tx なし = HTTP エラー、推定)
- **family 候補**: 既存 `storm_guard` 系 (新 family なし)。[[project_weekend_market_halted_retry_storm_2026_09_07]] の「guard 捕捉率 ~40–50%」記述への反例付記
- **反証可能な予測**: 次に deploy を跨がない窓で storm が起き、guard `sent_total` (成功分) が broker `REPLACEMENT` の 95% 未満なら 2nd writer 説が復活。95% 以上なら 2 例目で「捕捉欠損 = 状態消失」が優勢。また `failed_total` が決済後にだけ増えるなら「決済後 modify 継続」は writer 側の停止条件欠落として独立の R3 候補
- **隣接 ban / 凍結 frame**: registry `storm-guard-enforce-decision` (期日 2026-10-20) / `storm-guard-modify-sl` (10-20) が活性。凍結 look 保有 family ではない
- **経路**: 執行 QA → **既存 frame 回付** (`storm-guard-enforce-decision` の前提 3 点のうち「2-writer 集約」の重み低下を供給)。新規 R1 候補は立てない

### O-2026-10-15-2: 平日 21:03Z の open 側 `MARKET_HALTED` — broker は同 ms で cancel・リトライなし、demo は同 signal を shadow 建玉として保持し −18.8 (執行 QA / 制御系)
- **現象**: 2026-10-14 21:03:52.248 UTC、`usdjpy_carry_dip_accumulator` live-eligible signal (audit id 18973 `sent`、1,000u BUY、signal 158.312) → broker `MARKET_ORDER` 1254212 (FOK、SL 158.154 / TP 158.992 on fill) → `ORDER_CANCEL` 1254213 `MARKET_HALTED` (同 ms)。bridge は `recent_errors` に `OPEN buy ok but no tradeID`、audit に `filled` 行なし。demo は trade #19539 を `is_shadow=1`、entry 158.34 (signal +2.8p)、SL 158.154 (broker 指定値) で保持 → 22:39:49 `SL_HIT` −18.8 (shadow book)。2 時間後の 23:03:47 に同戦略が再 signal → #1254215 fill (−¥150)
- **トリガ日**: 2026-10-14 (計測 2026-10-15)
- **想定メカニズム**: OANDA の平日日次ロールオーバー停止帯 (21:00Z 台) に FOK order が当たった。open 側はリトライループを持たない (tx 2 本で終了) — 週末 halt の exit 側 32,821 回リトライ ([[2026-10-05]]) とは経路が別。demo の shadow 化は「broker fill なし → demo は shadow として追跡」の fallback 経路 (slippage 2.8p は halt 明けの再評価価格と signal の差と推定)
- **family 候補**: 新 event 種 (open 側 halt)。[[project_weekend_market_halted_retry_storm_2026_09_07]] の halt family とは「リトライの有無」で区別、独立 1 件
- **反証可能な予測**: 21:00〜21:05Z 帯の live-eligible signal は今後も `MARKET_HALTED` で cancel され、audit に `sent` のみが残る。signal 時刻を 21:05Z 以降に遅延させる (または halt 帯を entry 除外する) 変更が入れば本観測は再発しない。exit 側で同帯に SL/TP 約定が必要になった場合は週末型のリトライループが出るか (未観測)
- **隣接 ban / 凍結 frame**: なし。未決 8「週末 halt リトライ storm」の受け皿に「平日 open 側」を付記
- **経路**: 記録のみ (独立観測 1 件目、R1 候補は 3 件で検討)

---

### O-2026-10-16-1: `storm_guard` 全数捕捉 2 例目 (269/269) — code deploy (04:42:47Z) の 2h25m 後に起きた storm で guard 状態は健在、O-2026-10-15-1 の反証可能予測「≥95% なら状態消失説が優勢」が成立 (執行 QA / 制御系)
- **現象**: 2026-10-16 07:07:35〜07:15:38 UTC、`usdjpy_carry_dip_accumulator` LIVE #1254229 (1,000u BUY @157.918) に `STOP_LOSS_ORDER` `REPLACEMENT` **269 回** (538 tx)、全て 157.926 (BE+0.8) = 純族 A、median 0.88 s、最大 gap 173 s (2 バースト 186 + 83)、≈2,005/h。自然停止 6m41s 後の 07:22:19 に SL 市場到達 +¥8 (自己約定なし、純族 A 自然停止 5 例目)。`/api/oanda/status.storm_guard` (12:00Z): `trades` 1 件 (`349affe7-c3a`、`sent_total` 269 / `breaker` 219 / `idempotent` 49 / `failed_total` 0 / `tripped` true / `confirmed_sl` 157.926)、`totals.evaluated` 269 = `sent` 269、`breaker_trips` 1、`skipped` 全 0 (`enforce: false`)。**broker 269 と 1:1 (捕捉率 100%)**。10-15 06:36Z に登録されていた 2 建玉と `totals` 628 は消失 (= PR #333 Render live 04:42:47Z、`engine_pid` 129 → 130)
- **トリガ日**: 2026-10-16 (計測 2026-10-16)
- **想定メカニズム**: guard の in-process 状態は deploy で消える (3 例目の確証) が、deploy を跨がない窓では writer の全送信が guard を通過する (2 例連続: 10-14 488/488 + 15/15、10-16 269/269)。10-05 の捕捉率 50.5% は窓中の状態消失で説明可能。「全モードに guard 外の 2nd writer」説は本観測でも反証されず支持もされず (保留継続)。判定順 (推定、コード未読): 2〜50 送目 = idempotent (49 固定、10-15 の 488 回でも 49)、51 送目以降 = breaker (`max_tx_per_hour` 50 超過) ⇒ enforce なら idempotent で 2 送目から block、268/269 (99.6%) が消えた計算
- **family 候補**: 既存 `storm_guard` 系 (新 family なし)。O-2026-10-15-1 の 2 例目 (独立観測 — 異なる日付・異なる deploy 境界)。[[project_weekend_market_halted_retry_storm_2026_09_07]] の「guard 捕捉率 ~40–50%」記述への反例 2 件目
- **反証可能な予測**: 次に deploy を跨がない窓で storm が起き、guard `sent_total` (成功分) が broker `REPLACEMENT` の 95% 未満なら 2nd writer 説が復活。deploy を跨いだ窓で捕捉率が (deploy 後の送信数) / (全送信数) と一致すれば「状態消失 = 捕捉欠損」が確定。`enforce: true` 後の最初の storm で `skipped.idempotent` が `sent_total` − 1 程度なら判定順の推定が正しい
- **隣接 ban / 凍結 frame**: registry `storm-guard-enforce-decision` (期日 2026-10-20、あと 4 日) / `storm-guard-modify-sl` (10-20) が活性。凍結 look 保有 family ではない
- **経路**: 執行 QA → **既存 frame 回付** (`storm-guard-enforce-decision` の根拠材料として本観測を供給 — 前提 3 点のうち「状態永続化」の重みを上げ、「2-writer 集約」の重みをさらに下げる)。新規 R1 候補は立てない

---

### O-2026-10-20-1: carry_dip #1254773 に `REPLACEMENT` 46,091 回 / 11.82 h — 族 B 型 (trail⇄BE 往復) の最大規模、自然停止なし (TP 約定で終了)、`storm_guard` 46,098 − 失敗 7 = 46,091 で全数捕捉 3 例目、O-2026-10-13-1 の予測成立、状態は PR #337 deploy で消失 (4 例目) (執行 QA / 制御系)
- **現象**: 2026-10-19 00:50:52〜12:40:03 UTC、`usdjpy_carry_dip_accumulator` LIVE #1254773 (1,000u BUY @157.751、00:01:43Z fill) に `STOP_LOSS_ORDER` `REPLACEMENT` **46,091 回** (92,182 tx)、率 3,900/h (`max_tx_per_hour` 50 の 78 倍)、送信間隔 median 0.86 s、最大 gap 151 s、gap >10 min 0。価格 347 種 (157.758〜158.275)、同値 30,570 / 上 7,924 / 下 7,596 / 反転 5,222、**157.758 (BE+0.7) が 8,091 回** — 時間帯ごとに trail 側が上げた SL (01Z 157.94 → 12Z 158.28) を BE 側が 157.758 へ引き戻す往復 (BUY の SL を最大 51.7 pip 下げる送信を含む)。最後の `REPLACEMENT` (158.275) は 12:40:03.435Z の `TAKE_PROFIT_ORDER` 約定 (+¥609) と同一秒 = 建玉消滅まで送信継続。`/api/oanda/status.storm_guard` (05:31Z): `trades["57afa08a-184"]` `sent_total` 46,098 / `failed_total` 7 / `breaker` 46,048 / `idempotent` 49 / `tripped` true / `confirmed_sl` 158.275、`totals.evaluated` 46,367 = 269 + 46,098、`breaker_trips` 2、`skipped` 全 0 (`enforce: false`)。**成功 46,091 = broker 46,091 (捕捉率 100%)**。05:34:47Z PR #337 merge → Render deploy (`engine_pid` 130→129、`engine_import_pid` 39→60) → 05:39Z guard `trades` は新建玉 `6c20d641-972` のみ・totals 全 0
- **トリガ日**: 2026-10-19 (計測 2026-10-20)
- **想定メカニズム**: 既知の trail writer ⇄ BE writer の 2-writer 競合 (#950042 初観測、族 B) が hold 12h38m の全期間続いた。guard 捕捉 100% が 3 例連続 (488 / 269 / 46,091) = 全送信が同一プロセスの guard を通過する。10-05 の捕捉率 50.5% は窓中の deploy による状態消失で説明可能 (消失 4 例全てが code deploy と一致)。failed 7 の時刻は guard から読めず、決済済み建玉への modify は broker tx を生まないため「決済後 modify 継続」(O-2026-10-15-1) は broker 側では検証不能
- **family 候補**: 既存 `storm_guard` 系 (付記、4 件目 — 異なる日付・異なる建玉)。[[project_weekend_market_halted_retry_storm_2026_09_07]] の「族 B は自己約定で終わる」記述への反例 (本件は TP 約定で終了、自己約定なし)
- **反証可能な予測**: O-2026-10-13-1 の予測「hold >10h なら 30,000 回超 (率 3,000–4,000/h 不変なら)」は hold 12h38m / 46,091 / 3,900/h で**成立**。次: enforce 執行後 (registry `storm-guard-enforce-execution-window`) の最初の storm で broker `REPLACEMENT` は建玉あたり**実送信上限 (breaker 50/h) 以下**、かつ正当な trail tightening の喪失 0 (`storm-guard-enforce-first-storm-readout`、11-02)。逆に enforce 後も broker `REPLACEMENT` が数百を超えれば guard 外の writer が実在する。⚠️ **skipped カウンタの内訳 (idempotent / breaker / monotonic / deadband) は検知のみの trace から予測できない** — enforce では skip された送信が `sent_ts` に積まれないので breaker は検知時の「51 送目」では trip せず、固定 baseline から ≥1 pip の締め送信は実送信上限まで通り、族 B の緩め送信は monotonic、微差は deadband に落ちる。「enforce なら 46,097/46,098 block」型の数字 (本観測・[[2026-10-20]]・[[usdjpy_carry_dip_accumulator]] の wiki-daily 記述) は検知カウンタの外挿であって enforce 時の予測値ではなく、readout の判定基準に使わない (内訳の予測が要るなら順序付き SL 列を enforce 有効で replay する、PR #342 Codex P2 4333100688)。読み手 (daily report 表 / anomaly_watcher `sl_replacement_storm`) の初出が次 daily report に出なければ PR #337 の配線不備
- **隣接 ban / 凍結 frame**: registry `storm-guard-enforce-decision` は 10-19 に resolved (ENABLE、PR #337)。活性 = `storm-guard-enforce-execution-window` (期日 10-21、open live 0 の窓で env + 再起動 — #1346961 が 05:36:57Z から open で現在窓なし) / `storm-guard-enforce-first-storm-readout` (11-02)。凍結 look 保有 family ではない
- **経路**: 執行 QA → **既存 frame 回付** (10-19 決定の材料 5,881 送信を完了値 46,098 / 46,091 で補完、`storm-guard-enforce-first-storm-readout` の基準値として供給)。新規 R1 候補は立てない

### O-2026-10-20-2: docs/data push は web service を再デプロイしない — `engine_pid` 130 が 10-16 04:42Z → 10-20 05:31Z (3.9 d) 不変、同期間 origin に docs/data commit 48 本 (`data/monitoring/**` 7 本含む)、code commit 0 (執行 QA / 制御系)
- **現象**: `/api/demo/status` `engine_pid` 130 / `engine_import_pid` 39 / `main_loop_restarts` 1 が 2026-10-16 04:42:47Z (PR #333 deploy) から 10-20 05:31Z まで同値、guard `trades["349affe7-c3a"]` (10-16 07Z の storm) が 05:31Z まで残存 = 同一プロセス。同期間に origin/main へ 48 commit (`knowledge-base/raw/**` 53 path / `data/external/**` 15 / `data/monitoring/**` 7 (nav_floor_projection.csv を含む daily report commit) / `data/cache/**` 3 / `wiki/**` 4、PR #335 / #336 含む)、`*.py` / `render.yaml` の変更 0。05:34:47Z の PR #337 (code) merge 後 05:39Z に `engine_pid` 129 / `engine_import_pid` 60、guard 全消失 (8 サンプル同値)
- **トリガ日**: 2026-10-16〜2026-10-20 (計測 2026-10-20)
- **想定メカニズム**: render.yaml 09-24 コメント「`docs(KB): daily report` commit が毎回 web service を再デプロイ」および 10-07 仮説「docs/data push → Render auto-deploy 日次」は本窓では成立していない。可能性: (a) Render の `ignoredPaths` 評価単位が commit ではなく push で、docs-only push が skip されている (b) 09-24 以降に dashboard 側 auto-deploy 設定が変わった (c) 10-15〜16 の pid 94→129 (code commit なし) は deploy ではなく Render 側再起動 (health / memory)。検証は Render deploy ログ (MCP 未認証)
- **family 候補**: 新規 `render_deploy_trigger` (独立 1 件目)。[[2026-10-16]] 発見 5 の pid 94→129 と対照
- **反証可能な予測**: 次の docs/data-only push 群の間も `engine_pid` 129 / `engine_import_pid` 60 / guard 状態が不変なら確定。逆に code commit なしで pid が変われば Render 側再起動が別経路として実在し、guard 状態永続化の優先度が上がる
- **隣接 ban / 凍結 frame**: なし。未決 12 (render.yaml `ignoredPaths` 拡張) が受け皿
- **経路**: 記録のみ (未決 12 へ供給)。🆕 12:00Z 追記: 根拠は「pid 不変」ではなく「guard 状態 `349affe7` の 3.9 d 残存」(O-2026-10-20-3 で pid 再利用が判明)

---

### O-2026-10-20-3: `storm_guard` 状態消失 5 例目 — PR #339 code deploy (Render live 07:14:03Z) で 05:39Z 登録の建玉エントリが消えたが `engine_pid` は 129 のまま = pid 再利用 ⇒ 「pid 不変 = 再デプロイなし」は不成立 (執行 QA / 制御系)
- **現象**: 05:39Z `storm_guard.trades["6c20d641-972"]` (#1346961、`confirmed_sl` 158.044、sent 0) → 12:00Z `trades` {} / totals 全 0。閉じた建玉は guard に残る仕様 (05:31Z に 10-16 分 `349affe7-c3a` が残存) なので消失 = プロセス再起動。origin session log 10-20 Phase 5: 07:11:35Z open 0 → 07:12:15Z PR #339 merge (`modules/hunt_event_logger.py` 含む code) → Render dep-dbbh8k59fdbs73e5hk0g live **07:14:03Z**。`/api/demo/status` `engine_pid` は 05:39Z も 12:00Z も **129** (`engine_import_pid` 59)
- **トリガ日**: 2026-10-20 07:14Z (計測 12:00Z)
- **想定メカニズム**: Render コンテナは毎回同じ fork 順で起動するため、親 web プロセスから fork した engine が同じ pid を得る。10-06 の「pid 130 不変のまま guard 状態消失 (2 例目)」と同じ構造。pid は deploy 判定の識別子にならず、識別子として有効なのは guard 状態の残存 / `main_loop_restarts` / Render deploy ログ
- **family 候補**: `storm_guard` 系 (状態消失サブ family: 10-06 / 10-07 / 10-13 / 10-20 05:34Z #337 / 10-20 07:14Z #339 = 5 例、うち code deploy 起因 4)。`render_deploy_trigger` family (O-10-20-2) への影響: **結論 (docs/data push は再デプロイしない) は維持、根拠を「pid 130 不変」から「guard 状態 `349affe7` の 3.9 d 残存」に差し替え**
- **反証可能な予測**: 次の code deploy でも `engine_pid` が 129 のままなら pid 再利用は構造的。逆に enforce 有効化後、deploy 直後の建玉で `breaker` 履歴なしでも idempotent / monotonic が block するなら、状態永続化は readout の分母 (totals) のためだけに必要
- **隣接 ban / 凍結 frame**: `storm-guard-enforce-execution-window` (10-21) = permission 待ち (classifier [Production Deploy] 拒否、user 操作要)。`storm-guard-enforce-first-storm-readout` (11-02) の totals は deploy 毎に分断される
- **経路**: 記録のみ (未決 19「`storm_guard` 状態の永続化」を新設、user 決裁)

---

### O-2026-10-22-1: learner `entry_type_blacklist_add` が 3 度目 (id 97、10-21 12:47:24) に発火しても `current_params.entry_type_blacklist` は [] のまま — id 95 (10-02) / 96 (10-12) / 97 (10-21) の payload (`sr_channel_reversal` / `sample_size` 190 / `win_rate_at` 39.5 / `ev_at` −0.27 / reason 文字列) が byte 同一 = 書き込みだけでなく分析入力も凍結 (執行 QA / 制御系)
- **現象**: `/api/demo/learning` `adjustments[0]` = id 97 / `2026-10-21 12:47:24` / `parameter` `entry_type_blacklist_add` / `new_value` 1.0 / reason「sr_channel_reversal: WR 25.0%, EV -0.98 → 除外」/ `sample_size` 190 / `win_rate_at` 39.5 / `ev_at` −0.27。同一フィールドが id 96 (10-12 15:44:42) / id 95 (10-02 13:49:59) と完全一致。`current_params.entry_type_blacklist` **[]**、`/api/demo/status` `strategy_status.sr_channel_reversal` = `enabled: true` / `blacklisted: false` / `promo_n` 4 / `promo_ev` +1.73 (engine 側の母集団は learner の N 190 と別)。発火間隔 10.1 d / 8.9 d (≈9.5 d)
- **トリガ日**: 2026-10-21 12:47Z (計測 2026-10-22 12:00Z)
- **想定メカニズム**: (a) 書き込み側 — `entry_type_blacklist_add` の adjustment は履歴テーブルに記録されるが `current_params` へ反映する経路が無い (O-2026-09-18-1 の仮説のまま)。(b) 🆕 分析側 — 3 回の判定根拠 (N 190 / WR 25.0% / EV −0.98) が 19 日間 1 桁も動いていない = learner が参照する `sr_channel_reversal` の標本が 10-02 以降増えていない (scalp 母集団の shadow 行が learner の窓に入らない、または学習入力が静的 snapshot)。engine 側 `promo_n` 4 / `promo_ev` +1.73 との乖離は母集団の違いで説明でき、矛盾ではない
- **family 候補**: learner no-op (O-2026-09-18-1 / O-2026-10-13-2 / 本件) = **独立 3 観測で卒業条件 (≥3) 到達**。制御系 (エッジではない) のため S1 起票対象外 — 受け皿は未決 5 (learner no-op 修復、user 決裁)。[[sr-channel-reversal]] カードには書かない (戦略の状態は不変)
- **反証可能な予測**: (1) 何も変えなければ 2026-10-30〜11-01 に id 98 が同 payload で発火し、`entry_type_blacklist` は [] のまま。(2) 書き込み経路が修復されれば `current_params.entry_type_blacklist` に `sr_channel_reversal` が現れ、`strategy_status.blacklisted` が true になる。(3) 分析入力が生きていれば id 98 の `sample_size` は 190 から動く — 動かなければ (b) が確定
- **隣接 ban / 凍結 frame**: なし (learner は registry entry を持たない)。`sr_channel_reversal` は R2 shadow 母集団、outcome は読まない (本観測は learner の出力フィールドのみ)
- **経路**: 記録のみ → 未決 5 を「family 卒業・user 報告」へ格上げ ([[2026-10-22]] 発見 2)。(ローカル main 座礁分を autopilot 10-23 が origin へ救出、6 例目)

### O-2026-10-29-1 (座礁救出 7 例目、autopilot 10-29 が移植): learner の `entry_type_blacklist` に `sr_channel_reversal` が初めて反映 (`strategy_status.blacklisted: true`) — ただし id 98 (10-22 14:40:46) / id 99 (10-26 14:49:02) の payload は id 95〜97 と byte 同一 (`sample_size` 190 / WR 39.5 / EV −0.27) = 分析入力の凍結は継続、発火周期 9.5 d → 4 d (執行 QA / 制御系)
- **観測** (wiki-daily 10-29 02:00Z): `current_params.entry_type_blacklist` = `["sr_channel_reversal"]` (10-22 12:00Z は [])、`strategy_status.sr_channel_reversal` = `blacklisted: true` / `enabled: true` / `promo_n` 4 不変。O-2026-10-22-1 の反証可能予測 (2)「書き込み経路が修復されれば現れる」が成立、(1)「10-30〜11-01 に id 98」は 8 日早く外れ (id 98 は前回 run の 2h40m 後)、(3)「入力が生きていれば `sample_size` が動く」は不成立 (190 のまま)
- **想定メカニズム** (未特定): (a) 10-23 03:04Z の再起動 (PR #352 registry JSON deploy、`price_shock` latch `refreshed_at` 03:04:28Z) で adjustments 履歴から `current_params` を再構築 — ただし 10-21 05:54Z / 10:06Z / 10-22 06:56Z の 3 再起動では id 95〜97 が反映されなかったため単独説明不足 / (b) id 98 の書き込み経路が異なる (origin に code 変更なし) / (c) in-memory 反映で次 deploy で消える
- **反証可能な予測**: 次の code deploy 後も `entry_type_blacklist` に `sr_channel_reversal` が残れば (a) または永続化、消えれば (c)。`sr_channel_reversal` の shadow 行は demo/trades 10-02〜10-29 窓・audit 1500 窓とも 0 本 = 反映の前後で発火数に差は出ない (`promo_n` 4 は窓外)
- **family**: learner no-op (O-09-18-1 / O-10-13-2 / O-10-22-1、卒業済) の状態を「write-only」→「反映されたが機構不明 + 分析入力凍結」へ更新。制御系のため S1 対象外、未決 5 の user 報告内容を差し替え
- **経路**: 記録のみ ([[2026-10-29]] 発見 2)

### O-2026-10-29-2: PR #346 (LIVE SL の DB persist、10-21 10:06Z deploy) 後 最初の live trail — carry_dip #1346967 で `REPLACEMENT` 1 回 / storm 0、`storm_guard` evaluated 1 / sent 1 / detected.idempotent 0 / detected.monotonic 0 = broker 1:1 (全数捕捉 4 例目、最小) (執行 QA / 制御系)
- **観測**: 10-23 04:02:13Z fill → 06:42:32Z `CLIENT_REQUEST_REPLACED` + `STOP_LOSS_ORDER REPLACEMENT` 156.929 (BE+0.8) の 1 組 → 08:00:44Z SL 約定 +¥7。trail/BE writer は起動した (MAFE fav 23.5p) のに再送なし。従来「BE へ返す」型は 269〜57,311 回の storm を伴った (5 例)。DB `sl` == broker confirmed SL、`sl_initial` 列が初めて LIVE 行に入った。guard 状態は 5.9 d 残存 (本窓 code deploy 0)
- **解釈**: pin `test_real_bridge_guard_counters_zero_after_fix` の期待値 (idempotent == monotonic == 0) を実 trade で初観測 = family A/B の共通根 (送信口の未 persist) の修復と整合。N=1 のため「回帰なし」は暫定、`sl-persist-root-fix-first-live-trail-readout` (11-04) の判定材料
- **付随**: broker SL 約定の 0.92 s 後に demo が `TRADE_CLOSE` を送り `MARKET_ORDER_REJECT` (決済後レース、無害、本戦略で初記録)
- **反証可能な予測**: 次の live trail (favorable ≥ 0.8·ATR 到達建玉) でも `REPLACEMENT` ≤ 数回・idempotent / monotonic 0 なら修復確定。≥50 回の同値再送が再発すれば別 writer (guard 外) 説が復活
- **family**: `storm_guard` 系 (卒業済) — 捕捉率 100% の 4 例目、状態消失なし
- **経路**: 記録のみ ([[2026-10-29]] 発見 1、[[usdjpy_carry_dip_accumulator]] 10-29 節)

---

## 週次 rollup

### 週 2026-10-05〜10-11 / 10-12〜10-13 (遡及、30d レビュー 2026-10-14 で記載 — 10-05 / 10-12 月曜の rollup は未実施だった)
| family | 観測 | 独立 event | 経路 | 卒業 (≥3) |
|---|---|---|---|---|
| `storm_guard` 系 (既存 frame) | O-10-13-1 | 1 (10-08 storm) | 執行 QA → `storm-guard-enforce-decision` (10-20) 回付 | — (新 family でない) |
| learner blacklist write-only (制御系、O-09-18-1 family) | O-10-13-2 | 1 (10-12 id 96) | 既存 family 付記 | **2/3** (09-18 + 10-12) |

- 卒業到達 family なし。learner write-only は 2/3 — ただし制御系欠陥であり S1 (エッジ feasibility) の対象ではなく、到達時の経路は「修復 R3 PR 起票」(user 決裁の未決 5 を既存受け皿とする)
- 10-01〜10-12 の wiki-daily run は本ファイルに追記しなかった (10-06 / 10-07 は run あり・観測 0、10-08〜10-12 は run 欠落)。次回 rollup = 2026-10-19 (月)

### 2026-10-13〜10-19 (月曜 10-19 の wiki-daily 欠落のため 10-20 に代行; ローカル座礁分を autopilot 10-21 が origin へ救出)
| family | 独立観測 (週内) | 累計 | 卒業条件 (≥3) | 経路 |
|---|---|---|---|---|
| `storm_guard` 系 (SL replacement storm / guard 捕捉) | 3 (O-10-13-1 / O-10-15-1 / O-10-16-1) + 10-20 に 4 件目 (O-10-20-1) + 状態消失サブ family 5 例目 (O-10-20-3、12:00Z) | 5 | **到達** | 制御系 (エッジではない) — 既存 frame `storm-guard-enforce-decision` が 10-19 に ENABLE で決着 (PR #337)、S1 起票対象外、user 報告のみ。後継 frame 2 本 (10-21 執行窓 / 11-02 readout) |
| learner no-op (`entry_type_blacklist` write-only) | 1 (O-10-13-2) | 2 (O-09-18-1 含む) | 未達 | 未決 5 (user 決裁待ち) |
| 平日 open 側 `MARKET_HALTED` (リトライなし cancel) | 1 (O-10-15-2) | 1 | 未達 | 記録のみ |
| `render_deploy_trigger` (docs/data push が再デプロイしない) | 0 (10-20 に 1 件目 O-10-20-2、根拠は guard 状態残存 — pid は O-10-20-3 で識別子失格) | 1 | 未達 | 未決 12 |

- 執行 QA 発見 4 (週内 3 + 10-20 の 2 件目は別 family) / 卒業 family (エッジ) 0 / S1 起票 0。10-17〜10-19 の run 欠落 (3 日) で稼働率 4/7
- 次回 rollup = 2026-10-26 (月)

### 2026-10-20〜10-26 (月曜 10-26 の wiki-daily 欠落のため 10-29 に 3 日遅れで代行)
| family | 独立観測 (週内) | 累計 | 卒業条件 (≥3) | 経路 |
|---|---|---|---|---|
| `storm_guard` 系 (SL replacement storm / guard 捕捉 / 状態消失) | 2 (O-10-20-1 族 B 46,091 回 + 全数捕捉 3 例目 / O-10-20-3 状態消失 5 例目) + 10-23 trade の O-10-29-2 (REPLACEMENT 1、捕捉 1:1、状態消失なし) は週外 | 7 | 到達済 | 制御系 — PR #346 (10-21) で caller 側根を修復、`sl-persist-root-fix-first-live-trail-readout` 11-04 / `storm-guard-enforce-first-storm-readout` 11-02 (enforce 未執行) |
| learner no-op (`entry_type_blacklist` write-only) | 1 (O-10-22-1、3 例目) | 3 | **到達 (10-22)** | 未決 5 (user 報告) — 10-29 に O-10-29-1 で「反映されたが機構不明」へ状態更新 |
| `render_deploy_trigger` (docs/data push と再デプロイ) | 1 (O-10-20-2、根拠 = guard 状態 3.9 d 残存) | 1 | 未達 | 未決 12 — 10-23 PR #352 (registry JSON) で latch refresh = deploy 示唆 (記録のみ) |
| 平日 open 側 `MARKET_HALTED` | 0 | 1 | 未達 | 記録のみ |
| deploy 直後 LIVE 送信 | 1 (#1346961、PR #337 の 2m10s 後、O-10-20-1 内) | 2 | 未達 | PR #352 で §3.2 (a) 改定、deploy 後 N 分抑止は user 上程 (10-23) |

- 執行 QA 発見 4 (O-10-20-1 / -2 / -3 / O-10-22-1) / 卒業 family (エッジ) 0 / S1 起票 0。wiki-daily 稼働 10-20 (2 run) / 10-22 のみ = 2/7 日
- 次回 rollup = 2026-11-02 (月)
