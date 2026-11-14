# Daily Observations — 2026-11 (S0 intake 層、記述級のみ)

**Protocol**: [[daily-market-review-protocol]] — p 値計算禁止 / α 消費ゼロ / 台帳番号なし / 卒業には ban/estimand 監査必須 / 凍結 look 保有 family の outcome 量は記載禁止 (registry 事前確認)。前月: [[daily-observations-2026-10]]

---

### O-2026-11-02-1: グローバル建玉上限 `max_open`=8 が shadow 建玉を数え、carry_dip の live-eligible シグナルを shadow 化 (Live vs Shadow 分離の違反、live 機会喪失 1/12) (執行 QA / 制御系)
- **現象**: 2026-10-30 08:02:59Z `usdjpy_carry_dip_accumulator` BUY USD_JPY (demo row 20285、confluence STRONG、`[SLTP_CONSTRUCT] sl_p=18.6 tp_p=80.3`) が `[SHADOW_BYPASS] max_open` で `is_shadow=1` として記録。oanda_audit 同時刻行は `bridge_status=skipped / block_reason=shadow_tracking / is_live=false`。同時刻の open live 建玉は 0 (kalman #1346985 は 10-29 20:01Z 決済済み、carry_dip 21:04Z は `MARKET_HALTED`) = 上限 8 を埋めていたのは **shadow 建玉のみ**
- **トリガ日**: 2026-10-30 (観測 2026-11-02、autopilot run)
- **想定メカニズム**: `modules/demo_trader.py` の max_open 節は `_n_open = len(open_trades)` (live + shadow の総数) を live 上限 `max_open_trades`=8 と比較し、`_COUNT_GATE_BYPASS_LIVE_EXCEPTIONS` 非所属の live-eligible 型は `_is_slot_shadow_eligible` 経由で shadow に落とす (shadow 側の上限は max_open+8)。per-cell 上限 (`max_per_mode_pair`) は 2026-04-30 に live / shadow を別カウント化済みだが、グローバル上限は未分離。kalman_d7 3 variant は bypass 所属のため影響 0、carry_dip は非所属
- **規模**: 単一エンジン期 (10-05〜11-02、PROD snapshot 20,307 行) の live-eligible 型 `[SHADOW_BYPASS] max_open` = carry_dip **1 件** / live-eligible 発火 12 件 (LIVE 11 + max_open 1; 別に `MARKET_HALTED` 由来の shadow 化 2 件は別機構)。全型では 9 件
- **経路**: rule:R3 構造バグ (shadow が live を削る = 原則 1 + [[feedback_live_vs_shadow_strict_separation]])。修理 = live cap を `is_shadow` 偽の建玉数で判定 (shadow cap は総数のまま)。live 経路変更のため review gate + open live 0 の窓でマージ。registry `max-open-live-cap-counts-shadow-r3` (11-04)。lot / シグナル / 凍結値は非接触。outcome は読まない → ✅ **修理 PR #363 (2026-11-03、autopilot、rule:R3)**: live 上限を `_n_open_live` で判定、shadow 上限は総数のまま上流 shadow 行にも適用 (旧実装の誤 marker も解消)、CF pin 7 本。code derivation [[max-open-live-cap-counts-shadow-r3-2026-11-03]]。registry 期日 11-10 (deploy 後に live-eligible 型で `[SHADOW_BYPASS] max_open` 0 件を確認して resolve)

### O-2026-11-02-2: pre-reg gate (N≥10 ∧ EV<0) 成立から R2 執行までの latency (16h22m) で LIVE fill #11 (−¥105) が通過 — env が user 専権のため autopilot は code pin で閉じた (執行 QA / 制御系)
- **現象**: registry `t9-kalman-d7-live-n10-ev-check` の条件は 2026-10-29 **11:02:10Z** (#1346976 決済、po_dn N 10 / EV −1.27) に成立。`kalman_d7_po_dn_flip` は **18:52:48Z** (7h50m 後) に #1346985 を LIVE 送信・約定し、ON_FILL SL 157.862 (−10.4p) に 20:01:39Z 到達 = broker **−¥105** / demo −10.8 `SL_HIT` (`REPLACEMENT` 0、hold 1h09m)。autopilot 10-30 の PR #357 (merge 03:22:04Z / Render live **03:24:17Z** = 本 fill の 8h32m 後) が `_KALMAN_D7_R2_LIVE_STOP = True` で live 経路を閉鎖 (registry resolved 10-30)。wiki-daily 10-29 12:00Z は gate 成立を「執行は autopilot / user」と記録のみ
- **トリガ日**: 2026-10-29 (fill) / 2026-10-30 (執行)。計測 2026-11-02 (wiki-daily)
- **想定メカニズム**: LOCK 09-01 §R2 の撤退経路は env `KALMAN_D7_LIVE_ENABLE=0` だが Render env は autopilot から変更不可 (classifier [Production Deploy]、`STORM_GUARD_ENFORCE=1` 拒否 8 回と同じ構造) ⇒ 執行は「次の autopilot run + PR + CI + deploy」を待つ。gate 判定を engine 内で行う経路 (N・EV を `strategy_status.promo_*` から読んで live override を自動で閉じる) は存在しない。cost = latency 窓内の live-eligible 発火数 × 平均損失 (本件 1 本)
- **family 候補**: 新規「pre-reg gate → 執行 latency」(制御系)。隣接 = env 専権 family (enforce 拒否 ×8 / 本件) — 同根 (autopilot は env を触れない)
- **反証可能な予測**: 次に registry の `live_count_decision` 型 gate が成立する戦略 (`price_shock_rev_eur_gbp_h1_long` N 9 → 10 で EV<0 なら auto-demote) では、engine 内 latch (`price_shock_rev_auto_demotions`) があるため latency 中の追加 fill は **0** になる。1 本以上通れば latch 設計にも同じ穴がある
- **隣接 ban / 凍結 frame**: `kalman-d7-live-exit-disposition-user-decision` (11-29、再 live 化 R1)。凍結 look 保有 family ではない。outcome は broker realized (price-only) のみ記載
- **経路**: 記録のみ → 次の registry 改定時に「gate 成立時点で engine 側 latch を置く」R3 提案の材料 (live 経路変更のため user 決裁)。[[2026-11-02]] 発見 1 / [[kalman-d7-po-dn-flip]]

---
### O-2026-11-04-1: learner id 100 (11-03 14:22:37Z) が deploy で消えた `entry_type_blacklist` を再反映 — O-2026-10-29-3 の反証可能予測が成立 (制御系 / learner)
- **現象**: 11-03 05:33:44Z の enforce deploy (`dep-dbkn3fegekts73ekq5h0`、`engine_pid` 94→95 / import 59→60) 後、`current_params.entry_type_blacklist` は `[]` (11-02 12:33Z 観測、10-29 05:14Z deploy で消失して以来)。learner `adjustments` id 100 が **11-03 14:22:37Z** に発火 (id 99 10-26 14:49:02Z から 8.0 d、payload は id 95 以来凍結の `sr_channel_reversal: WR 25.0%, EV -0.98 → 除外` / sample 190 / ev_at −0.27 / win_rate_at 39.5) ⇒ 11-04 02:03Z 観測で `entry_type_blacklist` **`["sr_channel_reversal"]`**、`strategy_status.sr_channel_reversal.blacklisted` **true**
- **トリガ日**: 2026-11-03 (発火) / 計測 2026-11-04 (wiki-daily)
- **想定メカニズム**: blacklist は in-memory 状態で deploy 毎に消え (O-2026-10-29-1 (c))、learner は `learn_every_n`=10 とは無関係な不定周期 (10 / 9 / 1 / 4 / 8 d) で同一 payload を再適用する。deploy → 再反映の空白 **8h49m** が「blacklist 不在」窓。`sr_channel_reversal` の shadow 発火は 10-02 以降 0 のため、この窓でも実害 0
- **family 候補**: learner no-op family (O-2026-10-29-1 / -3 と同根)。隣接 = deploy で消える in-memory 状態 (storm_guard 状態消失 ×7 と同構造)
- **反証可能な予測**: (a) 次の code deploy 後、id 101 発火までの間は再び `[]` に戻る (deploy 時刻と learner 時刻の両方を wiki-daily が記録できれば判定可)。(b) `sr_channel_reversal` が shadow で発火した日に blacklist が真に効くなら、その日の `by_type` N は増えない (write-only の判定はこの観測を待つ)
- **隣接 ban / 凍結 frame**: なし (記録のみ)。outcome 不使用
- **経路**: 記録のみ → learner 状態の永続化 (未決 19 と同じ「状態永続化」R3 の材料)。[[2026-11-04]] 発見 3

---

### O-2026-11-04-2: DD 台帳 (JPY、0.2x lever の SSOT) が broker 側決済 `OANDA_SL_TP` を計上しない — 未計上 17 件 / net +212.7p、lever は悲観側に歪み (執行 QA / 制御系)
- **現象**: `_sync_oanda_closures` (OANDA が SL/TP 注文で先に決済した live 建玉を `OANDA_SL_TP` で DB close) は pip 台帳 / JPY 台帳 / `_dd_lot_mult` / KV を更新しない。engine 側 close 経路だけが writer を持つ。wiki-daily [[2026-10-20]] 発見 3 (14 例 / 155.0p) → index Defensive 行が「only SL_HIT is booked」rule として 17 例目まで追跡
- **トリガ日**: 2026-10-20 (発見) / 2026-11-04 (棚卸し + 修理、autopilot)
- **想定メカニズム**: Track C D-b (07-28) が writer を engine 側にのみ置いた。carry_dip / kalman の TP は broker `TAKE_PROFIT_ORDER` で先に約定する (10-29 exit 棚卸し) ため**勝ち側が系統的に抜ける**。close review §4 #6 の「ledger は 0.2x 判定の入力ではない」は誤り — `_dd_lot_mult` は起動時・決済時とも JPY 台帳 DD から `get_dd_lot_multiplier` で再計算される
- **規模**: PROD snapshot (4,000 行、D-b 母集団 ∧ exit_time ≥ 07-28) で `OANDA_SL_TP` **17 件 / +212.7p** (carry_dip 12 / kalman 5) vs `SL_HIT` 12 / −172.7p。台帳 DD 10.08% → 計上していれば ≈9.5% (¥10/pip 慣行)、tier 0.20 (≥8%) は不変。向きは不定 (10-20 −10.7p の損失側未計上あり)
- **経路**: rule:R3 構造バグ → **修理 PR (autopilot 2026-11-04)**: writer を `_book_equity_close` に一本化し両経路から呼ぶ、CF pin 8 本。遡及計上なし / units 列欠落 (¥10/pip 慣行) は残余。code derivation [[dd-ledger-broker-close-booking-r3-2026-11-04]]、registry `dd-ledger-nonbooking-consumer-audit` resolve → 後継 `dd-ledger-broker-close-first-booking-readout` (11-20)



## 週次 rollup

### 2026-10-27〜11-02 (月曜 11-02 定刻、wiki-daily 稼働 10-29 ×2 run / 11-02 = 2/7 日)
| family | 独立観測 (週内) | 累計 | 卒業条件 (≥3) | 経路 |
|---|---|---|---|---|
| `storm_guard` 系 (SL replacement storm / guard 捕捉 / 状態消失) | 2 (O-10-29-2 carry_dip 初 live trail `REPLACEMENT` 1・捕捉 1:1 / 12:00Z kalman #1346976 追認 N=2) + 状態消失 6 例目 (05:14Z registry JSON deploy)。#1346985 は置換 0 | ≥9 | 到達済 | 制御系 — PR #346 修復は N=2 で回帰なし。**enforce 未執行 (拒否 8 回、registry 11-03、user)** |
| learner no-op / in-memory 反映 | 2 (O-10-29-1 反映 / O-10-29-3 deploy で消失) | 5 | 到達済 | 未決 5 — id 100 未発火 (6.9 d)、falsifier 未判定 |
| 平日 open 側 `MARKET_HALTED` (リトライなし cancel) | 1 (O-10-30-1、cloud、carry_dip 21:04Z) | 2 | 未達 (3 例目で lessons 候補) | 記録のみ (halt 窓後の再送 R3 は live 経路変更) |
| `render_deploy_trigger` (docs/data/tools push と再デプロイ) | 1 (10-29 05:14Z registry JSON deploy = 2 例目; 11-02 PR #360 tools 変更での deploy は 3 例目候補) | 2–3 | 未達 | 未決 12 |
| deploy 直後 LIVE 送信 | 0 (#1346985 は 05:14Z deploy の 13.6 h 後) | 2 | 未達 | PR #352 §3.2 (a) 改定済 |
| 🆕 Live vs Shadow 分離違反 (`max_open` が shadow を数える) | 1 (O-11-02-1、cloud、carry_dip 10-30 08:03Z) | 1 | 未達 | R3 registry `max-open-live-cap-counts-shadow-r3` 11-04 (autopilot) → **修理 PR #363 (11-03)**、deploy 後 0 件確認 11-10 |
| 🆕 pre-reg gate → 執行 latency | 1 (O-11-02-2、kalman #1346985 −¥105) | 1 | 未達 | 記録のみ → 次 registry 改定で engine latch 提案 |
| 決済後レース (`MARKET_ORDER_REJECT` `TRADE_DOESNT_EXIST`) | 2 (10-29 #1346976 0.41 s / #1346985 0.41 s) | 4 | **到達 (実害 0)** | 無害のため lessons 不要、未決 21 で記録継続 |

- 執行 QA 発見 5 (O-10-29-1 / -2 / -3 / O-10-30-1 / O-11-02-1 / O-11-02-2 のうち週内 6、新 family 2) / 卒業 family (エッジ) 0 / S1 起票 0。戦略 LIVE: fill 3 / 決済 3 (10-23 #1346967 +¥7 は前週、本週 #1346976 +¥11 / #1346985 −¥105 = **−¥94**)、kalman live 停止 (PR #357)、SVK 11 月 3 RT −¥240
- 次回 rollup = 2026-11-09 (月)

### 2026-11-02〜11-08 (月曜 11-09 定刻は run 欠落、wiki-daily 11-11 が 2 日遅れで代行; wiki-daily 稼働 11-02 / 11-04 / 11-05 / 11-06 = 4/7 日)
| family | 独立観測 (週内) | 累計 | 卒業条件 (≥3) | 経路 |
|---|---|---|---|---|
| `storm_guard` 系 (SL replacement storm / guard 捕捉 / 状態消失) | 2 (O-11-05-1 enforce 下 初 live trail: 70 評価 / 5 送信 / deadband 65 / 喪失 0; O-11-06-1 状態消失 8 例目 = tools/tests のみの PR #367 deploy) | ≥11 | 到達済 | 制御系 — enforce 執行済 (11-03)、readout resolved 11-05 (enforce 維持)。永続化 R3 は sprint-1022 (iii) user 決裁待ち |
| learner no-op / in-memory 反映 | 1 (O-11-04-1 id 100 再反映 = O-10-29-3 falsifier 成立) + 併記 1 (11-05 deploy で再消失 = 予測 (a) 成立) | 6 | 到達済 | 未決 5 — 機構「deploy で消え、次の learner 調整で再適用」を 2 周期で確認、11-09 id 101 で 3 周期目 (O-11-11-1) |
| Live vs Shadow 分離違反 (`max_open` が shadow を数える) | 1 (O-11-02-1) | 1 | 未達 | **R3 修理 PR #363 (11-03) → registry resolved 11-05** (deploy 後 147 行 marker 0、carry_dip #20454 live 化) |
| pre-reg gate → 執行 latency | 1 (O-11-02-2、kalman #1346985 16h22m) | 1 | 未達 | 記録のみ → 次 registry 改定で engine latch 提案 |
| 🆕 DD 台帳 非計上 (broker 側決済 `OANDA_SL_TP`) | 1 (O-11-04-2、17 件 / net +212.7p、lever 悲観側) | 1 | 未達 | **R3 修理 PR #365 (11-04) writer 一本化** → readout `dd-ledger-broker-close-first-booking-readout` (11-20、material 0) |
| `render_deploy_trigger` (docs/data/tools push と再デプロイ) | 1 (O-11-06-1 PR #367 tools/tests のみで deploy = 4 例目) | 3–4 | **到達** | 未決 12 — ただし 11-11 窓で docs/data 59 commit が再起動 0 (O-11-11-2) = 条件は「`ignoredPaths` 外のパスを含む push」に絞られる (記録のみ) |
| deploy 直後 LIVE 送信 | 1 (O-11-05-1 #1347030 = deploy の 12 秒後) | 3 | **到達** | PR #352 §3.2 (a) 改定済 (窓条件に「直近 H1 bar に live-eligible signal なし」)。実害 0 (fresh guard state で捕捉) |
| 決済後レース (`MARKET_ORDER_REJECT` `TRADE_CLOSE`) | 1 (11-04 #1347030 同秒) | 5 | 到達 (実害 0) | 無害、未決 21 で記録継続 |
| cloud 報告の盲点 (guard 表を live trail / deploy に紐付けない) | 2 (11-05 70/5/65 を「ノイズ」と読む / 11-06 消失・deploy に言及なし) | 2 | 未達 | 改善候補 = guard 表に `oanda_trade_id` + `engine_import_pid` + 直近 deploy 時刻を併記 (autopilot 起票、記録のみ) |

- 執行 QA 発見 6 (O-11-02-1 / -2 / O-11-04-1 / -2 / O-11-05-1 / O-11-06-1、新 family 2 = DD 台帳 / cloud 盲点) / 卒業 family (エッジ) 0 / S1 起票 0。戦略 LIVE: fill 2 / 決済 2 (#1347030 11-04 +¥106 / #1347071 11-06 +¥271 = **+¥377**)、SVK 11-02〜11-06 15 RT −¥1,180。`STORM_GUARD_ENFORCE=1` 執行 (11-03 05:33Z、10 回目の試行)、kalman live 停止継続、E1 / ECG first look は 11-06 に両方 UNDERPOWERED
- 次回 rollup = 2026-11-16 (月)

### O-2026-11-05-1: `STORM_GUARD_ENFORCE=1` 下の初 live trail (carry_dip #1347030) で guard が 70 評価中 65 送信を dead-band で止め、5 送信は単調・DB sl == broker SL (喪失 0) — enforce の実効を初観測 (執行 QA / 制御系)
- **現象**: 11-04 02:39:44Z carry_dip BUY 1,000u @157.582 (PR #365 Render live 02:39:32Z の **12 秒後**、`engine_import_pid` 60→59 の新プロセス初 tick)。ON_FILL SL 157.405 / TP 158.266 → SL `REPLACEMENT` ×5 (02:52:39 157.592 / 02:55:49 157.656 / 02:56:10 157.666 / 02:56:12 157.678 / 02:57:50 157.689、単調増加、同値再送 0) → 02:58:24Z `STOP_LOSS_ORDER` @157.688 +¥106 (demo +10.2 `SL_HIT`、同秒に engine close の `MARKET_ORDER_REJECT` 1 = レース、無害)。`/api/oanda/status.storm_guard` (11-05 02:02Z): enforce true / evaluated **70** / sent **5** / failed 0 / `skipped.deadband` **65** / `detected.*` 全 0 / breaker 0 / `trades` {} (決済後クリア)。broker `REPLACEMENT` 5 = sent 5、demo 行 20454 `sl` 157.689 == broker 最終 SL、`sl_initial` 157.405 == ON_FILL SL
- **トリガ日**: 2026-11-04 (建玉) / 計測 2026-11-05 (wiki-daily)
- **想定メカニズム**: Tier2 trail writer (favorable ≥ 1.5·ATR_eff、0.001 刻み新高値 trail、§8.7 で「未検証の脚」) が 19 分の hold 中に ~70 回 (≈3.7/min) 評価し、1.0p dead-band が 65 件を吸収、残り 5 件が単調に送信された。enforce 前 (10-15〜10-19 の観測) なら 70 件全送信 = 「平常 3 送信型」と「storm」の中間型が初めて enforce で圧縮された。**喪失 0 / 4xx 0** ⇒ [[storm-guard-design-2026-09-22]] §7.3 の rollback 条件 (喪失 ≥1 or failed 急増) 不成立
- **併記 (O-2026-11-04-1 予測 (a) 成立)**: 同 deploy (02:39:32Z) で learner `current_params.entry_type_blacklist` が `["sr_channel_reversal"]` → **`[]`** に再消失 (11-05 02:02Z 観測、id 101 未発火)。deploy 時刻と learner 時刻の両方が記録された初例 = 「deploy で in-memory 状態が消え、次の learner 調整で再適用」の機構を 2 周期で確認
- **併記 (cloud 報告の盲点)**: autopilot post_ny 11-04 は guard 表 70 / 5 / 65 / 0 を記録したが「guard 登録建玉なし」「SL 微調整ノイズ」と読み、#1347030 の live trail に紐付けていない (`trades` {} が決済後にクリアされるため、表だけでは建玉が見えない)。daily report の guard 表に当該 `oanda_trade_id` / 評価窓の建玉を併記する改善候補 (記録のみ)
- **family 候補**: SL replacement storm family (A/B、enforce 後は「圧縮型」)。隣接 = deploy 直後 LIVE 送信 (10-20 #1346961 = 2 分後、本例 = 12 秒後、2 例目)
- **反証可能な予測**: (a) 次の live trail でも `detected.idempotent` = `detected.monotonic` = 0 かつ DB sl == broker SL が続く (喪失 0 が N≥3 で定常なら enforce の readout は閉じられる)。(b) 次の code deploy で guard totals が 0 に戻る (状態消失 ×7 の構造は enforce 下でも不変)。(c) id 101 発火で blacklist が再反映される (O-2026-11-04-1 と同じ周期)
- **隣接 ban / 凍結 frame**: なし (記録のみ)。outcome (+¥106) は guard 判定に使わない。registry `storm-guard-enforce-first-storm-readout` (11-15) / `max-open-live-cap-counts-shadow-r3` (11-10) の material = 本建玉、resolve 記録は autopilot
- **経路**: 記録のみ → §7.5 追補 + carry_dip カード。[[2026-11-05]] 発見 1

---

### O-2026-11-06-1: `storm_guard.enforce` true 下でも PR #367 (tools/tests 変更の診断枠 PR) の auto-deploy で guard totals (evaluated 70 / sent 5 / deadband 65) が全 0 に戻った — O-2026-11-05-1 予測 (b) 成立、状態消失 8 例目、cloud 4 報告が消失を記録せず (執行 QA / 制御系)
- **現象**: 11-05 02:02Z wiki-daily が読んだ `/api/oanda/status.storm_guard.totals` = evaluated **70** / sent **5** / `skipped.deadband` **65** (#1347030 の live trail、readout material) が、11-06 03:18Z には **evaluated 0 / sent 0 / skipped 全 0 / `trades` {}** (enforce true / config 不変)。`/api/demo/status` の `engine_import_pid` **59→60** (`engine_pid` 95 不変、`main_loop_restarts` 1)、`price_shock_rev_auto_demotions.refreshed_at` **11-05T02:46:29Z** (起動時マーカー、前例 11-04 は deploy live 02:39:32Z → 02:48:09Z)、`block_counts` 合計が 9,815 (11-05 02:02Z) → 9,451 (11-06 02:05Z) → 9,811 (03:18Z) と減少後に再増加 = 新プロセスでカウンタ起点がリセット。origin: **PR #367 merge 11-05 02:44:33Z** (`tools/adhoc29_lexicon_abgh2019.py` / `tools/adhoc29_abgh_census.py` / `tests/` 2 本 + KB、engine コード非接触) ⇒ merge の約 2 分後に Render auto-deploy (deploy id は Render MCP 未認証のため未取得、推定時刻 02:45〜02:46Z)。open live 0 のため broker 側 `REPLACEMENT` 0 = totals 0 と整合 (喪失の判定材料なし)
- **トリガ日**: 2026-11-05 02:4xZ (deploy) / 計測 2026-11-06 (wiki-daily 03:18Z)
- **想定メカニズム**: guard 状態は in-memory のみ (永続化は sprint-1022 (iii) の R3 候補、user 決裁待ち) で、`render.yaml` の `ignoredPaths` が `tools/**` / `tests/**` を除外しないため、engine に触れない診断枠 PR でも再デプロイ → 状態消失。enforce は env で再読込されるため **guard 機能は継続** (config / enforce true は復元)、消えるのは readout の分母 (totals / per-trade counts) のみ。11-05 02:02Z の読み取りはリセットの約 44 分前 = readout material は窓内で捕捉できていた (autopilot の resolve 11-05 は 02:06Z snapshot 基準、同様に窓内)
- **併記 (cloud 盲点 2 例目)**: autopilot daily report 11-05 post_tokyo 04:58Z / post_london 14:25Z / post_ny 21:43Z / 11-06 pre_tokyo 02:07Z の guard 表は全て `0 / 0 / 0 / 0` を記録したが、11-04 post_ny の 70/5/65 からの消失も PR #367 deploy も言及なし (11-05 の「70/5/65 をノイズと読む」に続く盲点)。改善候補: guard 表に `engine_import_pid` と直近 deploy 時刻を併記 (記録のみ、autopilot 起票)
- **family 候補**: storm_guard 系 (状態消失、本例で 8 例目: 10-06 / 10-07 / 10-13 ×?/ 10-20 (5) / 10-29 (6) / 11-03〜04 (7、PR #363/#364/#365) / 本例) + `render_deploy_trigger` (docs/data/tools push と再デプロイ、週次 rollup 11-02 の 2〜3 例に続く **4 例目候補** = tools/tests のみの PR)
- **反証可能な予測**: (a) 次の tools/tests/docs のみの PR merge 後 10 分以内に `engine_import_pid` が +1 され totals が 0 に戻る (`ignoredPaths` 仮説)。(b) 次の live trail は fresh state で broker `REPLACEMENT` と 1:1 (捕捉率 100%、消失の影響は分母のみ)。(c) 永続化 R3 が未決裁のままなら、11-15 までに deploy ≥1 回 ⇒ totals は累積しない (readout の N は「deploy 間の live trail 数」でしか数えられない)
- **隣接 ban / 凍結 frame**: なし (記録のみ)。outcome 非結合
- **経路**: 記録のみ → [[storm-guard-design-2026-09-22]] §7.5 追補 1 行 + 未決 19 (永続化) の材料。[[2026-11-06]] 発見 1

---

### O-2026-11-11-1: learner id 101 (11-09 21:23:47Z) が deploy で消えた `entry_type_blacklist` を再反映 — O-2026-11-05-1 予測 (c) 成立、「deploy で消失 → 次の learner 調整で再適用」の 3 周期目 (制御系 / learner)
- **現象**: 11-06 03:18Z wiki-daily で `current_params.entry_type_blacklist` = `[]` (11-05 02:39Z PR #365 deploy で消失、id 100 11-03 14:22:37Z の反映分)。11-11 05:49Z: `adjustments[0]` = **id 101 / 2026-11-09 21:23:47Z** (`scalp` / `entry_type_blacklist_add` / `sr_channel_reversal: WR 25.0%, EV -0.98 → 除外` / sample_size 190 / win_rate_at 39.5 / ev_at −0.27 = id 100 / 99 と byte 一致、15 回目の同一再発行)、`entry_type_blacklist` = **`["sr_channel_reversal"]`**、`strategy_status[sr_channel_reversal].blacklisted` **true** (100 戦略中 1)。id 100 → 101 の間隔 **6.3 d** (過去 10 / 9 / 1 / 4 / 8 / 6.3 d = 不定)、deploy による消失 → 再適用の空白 **4.8 d** (11-05 02:39Z → 11-09 21:23Z)
- **トリガ日**: 2026-11-09 (観測 2026-11-11、11-07〜11-10 の wiki-daily 欠落のため空白の上限は 4.8 d として記録)
- **想定メカニズム**: O-2026-11-04-1 と同じ — learner の blacklist は in-memory のみで deploy ごとに消え、`learn_every_n` 10 到達の次回調整で再発行・再適用される。reason 文字列が現サンプルから再計算されていない点 (sample_size 190 固定) も不変 = 文言を現況統計として引用不可 ([[sr-channel-reversal]] 2026-09-16 節)
- **規模**: `sr_channel_reversal` の shadow 発火は本窓 audit 182 行中 0 (10-02 以降 0 継続) ⇒ blacklist の有無による live / shadow 実害は 0。意味は「apply path が機能していること」の 3 周期目の確認のみ
- **family 候補**: learner no-op / in-memory 反映 (累計 7)。隣接 = `render_deploy_trigger` (deploy が消す側)
- **反証可能な予測**: (a) 次の code / 非 ignoredPaths deploy で再び `[]` に戻る (3 周期目の消失)。(b) 再適用までの空白は `learn_every_n` 10 の到達間隔に一致する (shadow 決済 10 本ごと ⇒ 1 d 以内のはずだが実測 4.8 d / 8h49m と不定 = 調整の発火条件は別にある可能性、記録のみ)。(c) `blacklisted: true` 1/100 は次の deploy で 0/100 に戻る
- **隣接 ban / 凍結 frame**: なし (記録のみ)。outcome 非結合
- **経路**: 記録のみ → [[sr-channel-reversal]] 1 行追記、未決 5 更新。[[2026-11-11]]

---

### O-2026-11-11-2: enforce 下の live trail 2 例目 (carry_dip #1347071) で guard 3 評価 / 3 送信 / deadband 0 = broker `REPLACEMENT` 3 と 1:1、DB sl == broker SL (喪失 0、N=2) — および guard 状態が 4.96 d / origin 59 commit を跨いで残存 (再起動 3 回は 11-06 03:18〜06:42Z の窓に集中) (執行 QA / 制御系)
- **現象**: #1347071 (11-06 06:03:04Z BUY 1,000u @157.767、ON_FILL SL 157.593 / TP 158.443) に SL `REPLACEMENT` ×3 = 06:42:06Z 157.778 (BE+1.1) → 06:45:03Z 158.013 → 06:45:04Z 158.038 (単調、刻み +18.5p / +23.5p / +2.5p = 全て 1.0p dead-band 以上) → 06:52:01Z `STOP_LOSS_ORDER` @158.038 +¥271 (demo +26.8 `SL_HIT`、同秒 engine close `MARKET_ORDER_REJECT` = レース)。11-11 05:49Z `/api/oanda/status.storm_guard`: enforce true / evaluated **3** / sent **3** / failed 0 / skipped 全 0 / detected 全 0 / `trades` {}。broker `REPLACEMENT` 3 = sent 3 = evaluated 3、demo 行 20619 `sl` 158.038 == broker 最終 SL == 約定 order ⇒ 正当な tightening の喪失 0。#1347096 (11-09) は `REPLACEMENT` 0 (MAFE fav 5.6p、writer 未起動 exit 3 例目) で guard 非接触
- **併記 (状態残存)**: totals 3/3 は 11-06 06:45Z → 11-11 05:49Z の **4.96 d** 残存、`engine_pid` 131 / `engine_import_pid` 63 不変。同期間に origin/main へ 59 commit (`raw/trade-logs/*-monitor.md` / `raw/audits/**` / `data/` rate anchor・mof・G0・ZN=F・`nav_floor_projection.csv`) = **再起動 0** ⇒ O-2026-10-20-2 (docs/data push は再デプロイしない) を支持。一方 `engine_import_pid` 60 → 63 (+3) は 11-06 03:18Z〜06:42Z に集中し、同窓の origin push 3 本 (PR #368 05:06:43Z = `reports/ecg-forward-2026-11-06.md` 含む / hook auto-save bf9b4d6a 05:07:41Z = `raw/trade-logs` + `wiki/analyses` + `wiki/index.md` のみ / PR #369 05:13:39Z = `wiki/research/daily-observations-2026-11.md` 含む) と件数一致。`render.yaml` `ignoredPaths` で説明できるのは #368 (reports/) と #369 (wiki/research/) の 2 本、hook commit (全パス ignoredPaths 内) の 1 本は説明できない (Render deploy ログは MCP 未認証で未取得)
- **トリガ日**: 2026-11-06 (trail) / 2026-11-06〜11-11 (残存)。観測 2026-11-11
- **想定メカニズム**: (trail) 11-05 の 70/5/65 (3.7 評価/分、1 pip 未満の刻みを deadband が吸収) と異なり、本例は評価 3 回で全て ≥ 1 pip の刻み = caller が毎 tick 再計算しても new_sl が変わらなければ evaluated に計上されない (11-05 は trail 幅が細かく毎 tick 変化)。(残存) guard 状態は in-memory、消えるのは再起動時のみ = 再起動を起こすのは非 ignoredPaths の push、ただし hook commit 分の 1 回は未説明 (Render 側の deploy 判定が「commit 単位」でなく「push 単位 = 同時に積まれた複数 commit の和集合」なら、05:06〜05:13Z の 3 push が 1〜2 deploy に畳まれるはずで +3 とは逆方向 ⇒ 別要因 = 例えば PR #368 が 2 段 (merge commit + branch) で deploy された可能性、記録のみ)
- **family 候補**: storm_guard 系 (累計 ≥12、enforce 下 喪失 0 は N=2) + `render_deploy_trigger` (条件の絞り込み材料)
- **反証可能な予測**: (a) 次の live trail でも sent == broker `REPLACEMENT` かつ DB sl == broker SL (N=3 で O-2026-11-05-1 予測 (a) を閉じる)。(b) 次に `engine_import_pid` が +1 するのは非 ignoredPaths パス (code / tools / tests / reports / wiki/research / wiki/decisions/*.json / data?) を含む push の直後 10 分以内、docs-only push では +0 が続く。(c) 評価回数は trail 刻みの細かさに比例し、deadband skip は「刻み < 1 pip の tick 数」に一致する (次の trail で `evaluated − sent` と Render ログの SKIP 件数を突合)
- **隣接 ban / 凍結 frame**: なし (記録のみ)。outcome (+¥271 / −¥148) は guard 判定に使わない
- **経路**: 記録のみ → [[storm-guard-design-2026-09-22]] §7.5 追補 2026-11-11 + [[usdjpy_carry_dip_accumulator]] カード、未決 12 / 19 / 27 の材料。[[2026-11-11]] 戦略 LIVE 節


---

### O-2026-11-12-1: `storm_guard` totals (enforce 下 live trail 2 例目の 3/3) と learner `entry_type_blacklist` が同時に消失 = 再起動 ≈11-11 09:58Z、状態消失 9 例目 — ただし `engine_import_pid` 63 不変 (pid は再起動検知器にならない)、トリガ push は未帰属 (執行 QA / 制御系)
- **現象**: 11-11 05:49Z `storm_guard.totals` evaluated 3 / sent 3 (`trades` {} は決済後クリア済) + `current_params.entry_type_blacklist` `["sr_channel_reversal"]`。11-12 01:22Z: totals **全 0**、blacklist **`[]`**、`strategy_status.blacklisted` 0/100、`price_shock_rev_auto_demotions.refreshed_at` 11-06T05:08:27Z → **11-11T09:58:34Z** (5.2 d ぶりの更新 = 起動マーカー)、`engine_pid` 131 → 130、`main_loop_restarts` 1 不変、`engine_import_pid` **63 不変**。cloud pre_tokyo 11-11 (commit 13:55Z) / post_ny 11-11 (22:23Z) の guard 表は 0/0/0「guard 登録建玉なし」(消失・再起動への言及なし)
- **トリガ日**: 2026-11-11 (≈09:58Z、観測 2026-11-12 01:22Z)
- **想定メカニズム**: in-memory 状態 2 系統 (guard totals / learner blacklist) の同時消失 + 起動マーカー更新 ⇒ プロセス再起動。本窓で origin/main に入った非 `ignoredPaths` push は **PR #370 (06:30:39Z merge、`tools/mof_forward_reverdict.py` + `tests/` ×2)** のみ = O-2026-11-11-2 予測 (b) の方向と整合するが、merge → マーカー **3h28m** は Render auto-deploy (2〜5 分) で説明できず、audit 行にも 09:58Z 前後の空白なし (空白は 04:47→06:01Z 1.23 h / 18:19→20:47Z 2.46 h のみ)。候補 3 択: (i) PR #370 の deploy がキュー遅延、(ii) Render 側の再起動 (health / maintenance、push 非依存)、(iii) マーカーが起動以外でも更新される (ttl 600 s だが 5.2 d 静止していたため可能性低)。`engine_import_pid` 不変はコンテナ再作成時の決定論的 pid (同じ起動順 ⇒ 同じ pid) で説明可能 = **10-06 の「pid 130 不変のまま全消失」と同型** ⇒ 再起動検知は guard totals / blacklist / `refreshed_at` の 3 点で行い、pid 差分を否定根拠に使わない
- **規模**: 消失した material (3/3、喪失 0、N=2) は [[2026-11-11]] / [[storm-guard-design-2026-09-22]] §7.5 追補 2026-11-11 に記録済 ⇒ **情報喪失 0**。enforce / config は env 復元で機能継続。blacklist 消失の実害 0 (`sr_channel_reversal` shadow 発火 10-02 以降 0)。状態消失 累計 9 例 (10-06 / 10-07 / 10-13 / 10-20 / 10-29 / 11-03〜04 / 11-05 / 本例 + 1)
- **併記 (記録のみ、outcome 非結合)**: 本窓 live-eligible 11 = 全て `agg_kelly=-0.231<0` blocked (`xs_momentum_rsi` USD_JPY BUY ×10 12:03〜17:46Z + `doji_breakout` GBP_USD ×1)。blocked 10 本の shadow 双子は **10 本全決済 +42.6** (12:03〜14:16Z の 4 本 `TP_HIT` +12.4 / +15.2 / +15.2 / +14.0、以後 `SL_HIT` −8.8 / +9.2 / −8.9 / +0.8 / −8.7、`SIGNAL_REVERSE` +2.2) = USD_JPY +115p 上昇日の順張り。gate の outcome 判定・α 消費には使わない (`agg_kelly` gate の設計は portfolio Kelly、単日 shadow で評価しない)
- **family 候補**: storm_guard 系 状態消失 (累計 9) + learner in-memory 反映 (累計 8) + `render_deploy_trigger` (帰属未確定のため条件絞り込みには使えない、反例候補として保持)
- **反証可能な予測**: (a) 次の wiki-daily で SVK RT 0 (target 到達後の停止) かつ guard totals 0 / blacklist `[]` のまま (再起動がなければ不変)。(b) 次の learner 調整 (id 102) で blacklist が再反映される (5 周期目、空白は `learn_every_n` 10 到達に依存)。(c) 次の状態消失時に `refreshed_at` の更新時刻 ± 10 分以内に origin/main の非 ignoredPaths push が存在しなければ (ii) Render 側再起動説を採用、存在すれば (i) に戻す
- **隣接 ban / 凍結 frame**: なし (記録のみ)。outcome 非結合
- **経路**: 記録のみ → [[storm-guard-design-2026-09-22]] 追補 2026-11-12 + [[usdjpy_carry_dip_accumulator]] / [[sr-channel-reversal]] カード 1 節、未決 5 / 12 / 19 / 33 / 34 の材料。[[2026-11-12]] guard 節


---

### O-2026-11-13-1: 再起動 10 例目 (11-12 04:18:10Z) = PR #372 deploy (registry JSON) と 13 秒差で一致 / 9 例目 (11-11 09:58Z) は対応 deploy なし → Render 側再起動 (ii) を採用 (執行 QA / 制御系)
- **現象**: 11-13 05:37Z `/api/demo/status`: `price_shock_rev_auto_demotions.refreshed_at` 11-11T09:58:34Z → **11-12T04:18:10Z**、`engine_import_pid` 63 → **62**、`engine_pid` 130 不変、`main_loop_restarts` 1、`storm_guard` totals 全 0 / `refreshed_at` null。Render deploy 一覧 (MCP、workspace tea-d6va…): **dep-dbqjr849v7es73do5rcg** commit f2a57988 (PR #372 merge 04:16:30Z) startedAt 04:16:33Z → **finishedAt 04:18:23Z live**。11-11 の deploy は dep-dbq0n4e0tbcc73fnfetg (PR #370、06:30:41Z → 06:32:46Z live) のみで、09:58Z 前後に deploy なし
- **トリガ日**: 2026-11-12 (10 例目) / 2026-11-11 (9 例目の帰属)。観測 2026-11-13
- **想定メカニズム**: PR #372 は `.claude/commands/wiki-daily.md` + `prereg-trigger-registry.json` + KB md を含む。render.yaml (2026-09-01) は `decisions/*.md` だけを ignore し registry JSON は意図的に deploy させる ⇒ docs(KB) 接頭辞でも registry を触る autopilot PR は毎回 engine を再起動する (設計どおり、O-2026-11-11-2 予測 (b) の「wiki/decisions/*.json」経路の初の直接確認)。9 例目は push → マーカー 3h28m で deploy なし ⇒ O-2026-11-12-1 予測 (c) の条件「± 10 分以内の非 ignoredPaths push なし」が成立 = **(ii) Render 側再起動** (health / maintenance、push 非依存)
- **規模**: 10 例目の喪失 material 0 (totals は 9 例目で既に 0、learner blacklist `[]` のまま)。11 月前半の再起動 5 回 (11-06 ×3 / 11-11 / 11-12) 中 4 回が PR deploy、1 回が Render 側
- **family 候補**: storm_guard 系 状態消失 (累計 10) + `render_deploy_trigger` (registry JSON 経路の陽性例 1、Render 側再起動の例 1 = 条件は「非 ignoredPaths push」だけでは閉じない)
- **反証可能な予測**: (a) 本 run の PR (registry JSON を含む) merge から 5 分以内に `refreshed_at` が更新され `engine_import_pid` が変わる (11 例目、設計どおり)。(b) 次に push なしで `refreshed_at` が更新されたら Render 側再起動 2 例目として O-2026-11-12-1 (ii) を確定する
- **隣接 ban / 凍結 frame**: なし (記録のみ)。outcome 非結合
- **経路**: 記録のみ → [[storm-guard-design-2026-09-22]] §7.6 + [[2026-11-13-session]] Phase 2。guard 状態永続化 (sprint-1022 #8) の需要側材料

---

### O-2026-11-13-2: wiki-daily 15:14Z 終端確認 — 状態消失 10・11 例目 (material 0) の終端状態と pid 再利用 3 例目 / learner id 102 未発火 (shadow 決済 112 で調整 0 = 予測 (b) 反証 2 例目) / risk 窓ロールで carry_dip Kelly が insufficient / R2 CRITICAL 7 → 5 は N 窓抜け (執行 QA / 制御系 / 推定器) — O-2026-11-13-1 は autopilot が origin に記録済 (ローカル未 pull)
- **現象 (制御系)**: 11-13 15:14Z `/api/demo/status`: `engine_import_pid` 63 → **39**、`price_shock_rev_auto_demotions.refreshed_at` 11-11T09:58:34Z → **11-13T06:14:52Z**、`engine_pid` **130 不変**、`main_loop_restarts` 1、`storm_guard` totals 全 0 / `trades` {}、learner blacklist `[]` → `[]`。autopilot 11-13 (origin [[storm-guard-design-2026-09-22]] §7.6 / O-2026-11-13-1) が中間状態 (63 → 62 @11-12 04:18:10Z = PR #372 deploy 13 秒差 / 62 → 39 @06:14:52Z = PR #374 deploy 1m47s) を Render deploy 一覧で記録済。本 run の追加確認: 06:15:14Z (deploy live の 12 秒後) に audit 行 = 空白なし; 11-12 04:16〜04:18Z の deploy は audit 空白 03:24 → 04:42Z (1.30 h) の中にあり単独では帰属できない (autopilot の deploy 一覧が一次)。`engine_pid` 130 は 2 回の再起動を跨いで不変 = **pid 再利用 3 例目** (10-06 pid 130 / 10-20 pid 129 / 本例)
- **現象 (learner)**: `adjustments[0]` id 101 (11-09 21:23:47Z) のまま id 102 未発火。本窓 shadow 決済 **112 本** (demo/trades 実数、`shadow_count` +111 は 01:45Z fetch 基準) = `learn_every_n` 10 の 11 周期分 ⇒ O-2026-11-11-1 予測 (b)「空白は `learn_every_n` 到達に一致」は 11-11 (8h49m / 4.8 d 不定) に続き **2 例目の不成立**。live 決済は本窓 0
- **現象 (推定器)**: `risk/dashboard` 窓ロール 10-12T23:54 → **10-14T15:14:03** (n 13 → 11、出 2 / 入 0、決済 0) で `strategy_kelly[usdjpy_carry_dip_accumulator]` が n 10 / half 0.1241 → **insufficient (n 9)**、全体 Kelly +0.2603 → +0.2001 / 0.0833、MC median DD 30.34 → 40.29 / worst99 66.74 → 93.34。R2 alert 11-12 00:02Z CRITICAL 7 → 11-13 13:55Z **5**: 外れた `bb_squeeze_breakout` EUR_USD は N 32 → **27** (EV −1.867 のまま WARN)、`dt_sr_channel_reversal` GBP_USD は一覧外 = 30d 窓の N 減少で閾値 (N≥30) を割っただけ
- **トリガ日**: 2026-11-12 / 11-13 (観測 2026-11-13 15:14Z)
- **想定メカニズム**: (制御系) registry JSON / tools を含む PR は Render が再デプロイ → コンテナ再作成 → in-memory 状態 (guard totals / learner blacklist / `_entry_atr`) 消失。pid は再作成時の決定論的割当で同値になりうる = 検知器にならない (3 例目で確定扱い)。(learner) 調整の発火は shadow 決済カウンタではなく live 決済 (本窓 0) または mode 別・条件付きカウンタ ⇒ 「`learn_every_n` 10 = shadow 10 本ごと」の読みは誤り (記録のみ、コード演繹は本 run では行わない)。(推定器) 30d rolling の n が 10 前後を往復するため carry_dip の Kelly / DSR は窓ロールで出たり消えたりする ([[feedback_cohort_time_check]] 型 = 歴史の出入りを現状の変化と取り違えない)。R2 の CRITICAL 減も同型
- **規模**: 状態消失 累計 **11 例** (10-06 / 10-07 / 10-13 / 10-20 / 10-29 / 11-03〜04 / 11-05 / 11-11 / 11-12 / 11-13 + 1)、11 月前半 再起動 6 回中 5 回が PR deploy (§7.6)、喪失 material は 10・11 例目とも 0。learner 無調整の空白 3.7 d (id 101 から)。実害: guard 機能継続 (enforce / config は env)、blacklist 消失の実害 0 (`sr_channel_reversal` 発火 0)
- **family 候補**: storm_guard 系 状態消失 (累計 11) + `render_deploy_trigger` (registry JSON 経路 陽性 2 例目、tools 経路 陽性、Render 側 1 例) + learner in-memory 反映 (累計 9、発火条件 未同定) + 推定器 窓ロール反転 (risk Kelly 5 度目、R2 CRITICAL 窓抜け)
- **反証可能な予測**: (a) 次の learner 調整 (id 102) は live 決済が ≥1 本入った後に発火し、shadow 決済のみの窓では発火しない (次 3 run で live 決済 0 のまま id 102 が出れば棄却)。(b) 次に origin へ registry JSON / tools を含む PR が merge されたら 5 分以内に `refreshed_at` 更新 + `engine_import_pid` 変化 (O-2026-11-13-1 (a) の継続、3 例目で定常扱い)。(c) carry_dip `strategy_kelly` は次に live 決済が 1 本入ると n 10 で再出現する (窓依存の確認)。(d) `bb_squeeze_breakout` EUR_USD は R2 30d 窓で N<30 のまま WARN に留まり、EV は改善しない (次 R2 alert で N と EV を併読)
- **隣接 ban / 凍結 frame**: なし (記録のみ)。outcome 非結合 (`doji_breakout` 双子 −9.6 は gate 判定に使わない)
- **経路**: 記録のみ → [[storm-guard-design-2026-09-22]] 追補 2026-11-13 + [[usdjpy_carry_dip_accumulator]] / [[sr-channel-reversal]] カード 1 節、未決 5 / 12 / 19 / 33 の材料、🆕 未決 35 (月曜 rollup 廃止、PR #372) / 36 (LIVE 途絶 4.34 d)。[[2026-11-13]] guard 節 / learner 節
