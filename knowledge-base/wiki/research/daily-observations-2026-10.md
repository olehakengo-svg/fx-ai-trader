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

## 週次 rollup

### 週 2026-10-05〜10-11 / 10-12〜10-13 (遡及、30d レビュー 2026-10-14 で記載 — 10-05 / 10-12 月曜の rollup は未実施だった)
| family | 観測 | 独立 event | 経路 | 卒業 (≥3) |
|---|---|---|---|---|
| `storm_guard` 系 (既存 frame) | O-10-13-1 | 1 (10-08 storm) | 執行 QA → `storm-guard-enforce-decision` (10-20) 回付 | — (新 family でない) |
| learner blacklist write-only (制御系、O-09-18-1 family) | O-10-13-2 | 1 (10-12 id 96) | 既存 family 付記 | **2/3** (09-18 + 10-12) |

- 卒業到達 family なし。learner write-only は 2/3 — ただし制御系欠陥であり S1 (エッジ feasibility) の対象ではなく、到達時の経路は「修復 R3 PR 起票」(user 決裁の未決 5 を既存受け皿とする)
- 10-01〜10-12 の wiki-daily run は本ファイルに追記しなかった (10-06 / 10-07 は run あり・観測 0、10-08〜10-12 は run 欠落)。次回 rollup = 2026-10-19 (月)
