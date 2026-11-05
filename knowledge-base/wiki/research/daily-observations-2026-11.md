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
