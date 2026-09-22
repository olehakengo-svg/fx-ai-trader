# 📝 DRAFT: weekend_gap 執行モダリティ R1 再審 — 骨子 (2026-09-22)

> **Status: 📝 DRAFT — LOCK ではない。R1 起案でもない。** 本文書は「packet §6 の事前コミット『改定後 qualifying イベント 2 連続で fill 不成立 → 執行モダリティ自体を再審 (R1 再起案)』が**発動した場合**に、その日から起案を始められるよう分岐と変更候補を事前固定した骨子」であり、凍結値 (§2/§3/§5 of [[weekend-gap-stage2-execution-prereg-2026-07-24]]、[[weekend-gap-execution-contract-r1-packet-2026-09-10]] §4) は**一切変更しない**。発動しなければ本文書は未発動として archive する。
> rule:R3 (文書のみ、code / registry / live 経路 不変更)。R1 起案への昇格と候補の選択は **user 承認事項**。
> 起点: [[path-to-win-reassessment-2026-09-22]] §3 Rank 6 (「次の qualifying 不成立 1 件で R1 再審発動 → 骨子 DRAFT を 09-27 前に用意」)。
> **本文書で計算していないもの**: shadow row の outcome (pnl / MFE / 埋め率)、G1 slippage 集計、G2 累積、OOS 窓 (2022-01-01〜2026-06-30) の再集計、explore 窓の outcome 条件付き統計。数字は全て価格系 (gap / drift / 時刻) と既存凍結値の引用のみ。

---

## 0. 3 行サマリ

1. **どこにいるか**: 執行契約 (B) 発効 (2026-09-10) 後の qualifying イベントは 1 件 (2026-09-13 USD_JPY、gap −50.0p) で、live は **`ABANDONED_DRIFT` (drift +41.0p > +8.0p)** = 改定後不成立 **1 件目**。09-20 は 3 ペアとも NO-QUALIFY (分母外)。live fill は live 化 (07-25) 以降 **0/4 qualifying イベント**、契約 B 下では 0/1。次の検証点 = **2026-09-27 (日) 21:00 UTC**。
2. **何が起きたら発動するか**: 次の qualifying **pair-event** (時系列順) が `ABANDONED_DRIFT` / `ABANDONED_HALT` / 新種 cancel なら、直前の pair-event (= 09-13 ABANDONED_DRIFT) と合わせて **不成立 2 連続 = packet §6 発動** → 本 DRAFT を R1 起案 packet へ昇格 (user 承認)。fill なら F2 resolve (watcher は TRIGGERED を返すだけ — **registry 明示編集で resolve**、§2) + **G0' 完了** (packet §6 は「改定後の最初の 2 qualifying イベント」に限る — 以後の放棄は記録のみ、rolling gate は未承認)。同一週末に複数 pair-event があれば **system_kv latch `ts` 順**に並べ、**event #2 の結果だけ**で決める (§2)。NO-QUALIFY なら繰越 (§2 で事前固定)。
3. **候補の要点 (§3)**: 09-13 型 (gap が halt 窓 ~4 分で ~47p 消費) を救える契約変更は **drift 境界 +8.0p の変更/撤廃**か**シグナル基準の executable 化**しかなく、いずれも estimand 変更 = **fresh forward OOS のみが confirmatory** (OOS 窓再接触は禁止)。打ち切り +15 分・送信タイミング・指値化は 09-13 型に効かない。契約不変更で今すぐできるのは **放棄イベントの価格系 forward 観測 (§3-6)** のみ。

---

## 1. 現状の事実 (出所付き)

| 項目 | 値 | 出所 |
|---|---|---|
| 契約 B 発効 | 2026-09-10 (user「進めて」、rule:R1)。送信 = OANDA tradeable 確認後の最初の評価 tick / 打ち切り 初バー ts +15 分 / drift 放棄 +8.0p / halt-race 再送 1 回 | packet §4、`strategies/daytrade/weekend_gap_fade.py:89–93` |
| event #1 (2026-09-13) | USD_JPY gap **−50.0p** (Fri close 153.620 → Sun open 153.120) ≥ 21.4p → BUY fade 発火 21:05:03Z、shadow row id 17602。tradeable 確認時 (quote_age 7.5s) の adverse drift **+41.0p > +8.0p** → `ABANDONED_DRIFT`。oanda_audit `weekend_gap_exec_abandon(ABANDONED_DRIFT,drift=+41.00p)` 21:05:05Z。EXEC_B 遷移 (Render ログ実読 09-22): `HOLD` 14 行 21:01:27–21:04:33Z (tradeable=False、halt 窓) → `ABANDONED_DRIFT` 21:05:02.5Z (tradeable=True、quote_age 7.493s、send_mid 153.53 / sunday_open 153.12) | [[daily-observations-2026-09]] O-2026-09-14-1 / [[2026-09-16]] L241 / Render ログ API 実読 2026-09-22 (service `srv-d6va1of5r7bs73en10vg`、2026-09-13T20:55–21:30Z、text=`WEEKEND_GAP` 25 行・hasMore=false) |
| event #1 の他 2 ペア | **EUR_USD gap −2.2p < 20.0p → no-qualify** (21:01:08Z) / **AUD_USD gap −14.7p < 25.0p → no-qualify** (21:01:29Z) — gap 診断ログで**確定** (分母外、pair-event 列に現れない)。⚠️ 09-22 初版は oanda_audit 09-13 行数 1 ([[2026-09-16]] L242) から「no-qualify (推定)」と書いていたが、**audit 不在が証明するのは「監査される執行経路に到達しなかった」ことだけ** — `_weekend_gap_tick` (demo_trader.py:4117–) は weekend_key None / latch 済 / `df is None or len(df) < 10` / `det is None` で**非監査 return** し、`_tick_entry` にも `_add_oanda_audit` 前の early block があるため、qualify して上流で失敗した pair-event を audit 行数では検出できない (PR #281 review P2、2 巡目)。以後は診断ログ (または shadow row) で確定するまで **UNKNOWN と書く** (§6) | Render ログ API 実読 2026-09-22 (service `srv-d6va1of5r7bs73en10vg`、2026-09-13T20:55–21:30Z、text=`WEEKEND_GAP` 25 行・hasMore=false) / code: `modules/demo_trader.py:4136–4172` |
| 2026-09-20 | USD_JPY **−19.0p** < 21.4p / AUD_USD **−20.5p** < 25.0p / EUR_USD **−1.9p** < 20.0p → 3 ペア NO-QUALIFY、row/latch なし | Render ログ `[WEEKEND_GAP]` gap 診断行 2026-09-20T21:01:13–21:01:29Z (2026-09-22 実読、[[2026-09-22-session]]) |
| 不成立カウント | 改定後 qualifying イベント **1/2 消費** (drift 放棄は不成立に含む — registry `weekend-gap-execution-amendment-g0prime` message「halt >15m / drift 放棄 / 新種 cancel」)。NO-QUALIFY は分母外 | packet §6 / registry g0prime |
| live fill 通算 | **0/4** qualifying イベント (07-26 インフラ障害 / 08-02・09-06 MARKET_HALTED / 09-13 ABANDONED_DRIFT)。G1/G2/G3 の live N = 0 | [[weekend-gap-fade]] イベントログ |
| 境界導出時の実測 | OANDA 初 M1 遅延 = **+4.0 分 (48/48、min=max)**。qualifying・cap 通過 N=8 の +5m adverse drift **mean +3.15p**、全 48 pair-weekend p90 **6.7p**、+8.0p 抵触 3/48 (qualifying 0/8) | `bt-results/wg_gap_drift-2026-09-10.json` aggregates / packet §5.2–5.3 |
| 09-13 の drift vs 導出値 | +41.0p は mean 比 ~13 倍、p90 比 ~6 倍 (O-2026-09-14-1 は「~5 倍 / ~6 倍」と記載 — 分母を mean 3.15 とすると 13 倍、p90 6.7 とすると 6.1 倍。本稿は両方併記) | 上記から単純除算 |
| 期日 | registry `weekend-gap-execution-amendment-g0prime` 期日 **2026-09-28** (繰越必要) / F2 `project-falsification-f2-wg-live-conversion` **2026-12-31** (live N=0 なら「PASS→live 変換未実証」認定) / 冬時間初週末 **2026-11-01** | registry |
| 頻度 | 2.07 qualifying 週末/月 (凍結 OOS report §6) → 週末あたり p≈0.48 → 3 週末連続 non-qualifying ≈ 14% ([[path-to-win-reassessment-2026-09-22]] §3 Rank 6 は 14〜17% 幅) | stage-2 prereg §1 |

---

## 2. 分岐の事前固定 — G0' event #2 (改定後 2 番目の qualifying pair-event = 2026-09-27 以降で最初に qualify する pair-event、cap skip 除く)

> packet §6 の境界は「**改定後の最初の 2 qualifying イベント**」に限定された一回限りの配管確認で、rolling gate ではない (`weekend-gap-execution-contract-r1-packet-2026-09-10.md` §6 row 1–2 / registry g0prime)。09-13 USD_JPY `ABANDONED_DRIFT` = event #1 (不成立)。**event #2 が起きた時点で G0' は終了する** — fill なら完了・通常運用、不成立なら 2 連続 = 発動。event #3 以降は存在しない。

| 結果 (pair-event 単位) | 分類 | 即時アクション (Claude、record-only / R3) | 本 DRAFT の扱い |
|---|---|---|---|
| **fill** (demo row `oanda_trade_id` 非空 ∧ oanda_audit sent→filled、1 回目 `MARKET_HALTED` cancel → 再送 fill を含む) | 成立 = **G0' 完了** (fill 1/2、packet §6 row 1「配管確認完了、通常運用へ」) | **F2 は自動では resolve されない**: `tools/prereg_trigger_watch.py::evaluate_live_count_decision` (L80–99) は clean live N≥n_decide=1 で `TRIGGERED`「再評価を実施せよ」を**返すだけ**で、`active=false` / `resolved` / `resolution` を書かず registry を一切変更しない (watcher に registry 書込み経路なし、2026-09-22 code 読み)。**resolution は明示手順** — §6 の 24h 規則内に registry 編集 PR (別担当) で `active: false` + `resolved: <YYYY-MM-DD>` + `resolution: 「PASS→live 変換の初実証 (F2 U7)、改定後 fill 1/2、demo row id / oanda_trade_id / oanda_audit id」` を記録する (既存 inactive エントリの規約: `resolved` 24/27・`resolution` 25/27、例 `vix-sell-pilot-recheck`)。**編集までは F2 は active のまま TRIGGERED 表示が続く = 未 resolve として扱う** (watcher 出力を resolve 済みの証拠にしない)。G0' 手順 (1)–(5) (registry g0prime) を実施 — (4) の slippage 突合は**当該 1 event の persisted 値の読み取りのみ、rolling 集計はしない** (G1 は code gate、N≥6 まで人手で計算しない)。card へ 24h 以内転記 (§6) | **発動せず → 本 DRAFT は未発動として即 archive** (G0' は 2 event で終了、event #3 は存在しない)。以後の放棄は §3-6 の観測記録のみで、連続不成立 trigger は終了 — 継続 (rolling gate) は packet §6 の改定 = user 承認事項 (PR #281 review P2、4 巡目) |
| **不成立** = qualifying pair-event (cap skip 除く) が demo row `oanda_trade_id` **空**のまま終端したもの: (i) **`ABANDONED_DRIFT` / `ABANDONED_HALT`** (送信前放棄、packet §6「drift 放棄 / halt >15m」)、(ii) **SEND 後 FOK cancel 2 回とも `MARKET_HALTED`** (`modules/oanda_bridge.py:680–719` の halt-race 再送は 1 回目 `MARKET_HALTED` で始まるが 2 回目の応答を制限しない — trade id も filled audit 行も残らない = **halt 型の不成立**、packet §6「halt」系に読む)、(iii) **SEND 後の `MARKET_HALTED` 以外の reason の cancel** (新種 cancel)。(ii) を「新種 cancel でない」として外さない (PR #281 review P2、4 巡目) | **event #2 が不成立 = 09-13 (event #1) と合わせて 2 連続 = packet §6 発動** | 発動時: (i) 事象を card へ 24h 以内転記 (価格系のみ)、(ii) 本 DRAFT §3 の表を一次データで確定し **R1 起案 packet v1 をイベント +7 日以内** (09-27 発動なら 10-04) に起票、(iii) user へ「R1 再審起案の承認」を 1 行で依頼。**発動中の live 経路は契約 B のまま継続** (放棄は fail-closed で shadow 分母を保存する — 止める理由がない、4原則#3)。packet §6 の「family live-execution 保留」を選ぶのも user 事項 | **R1 起案へ昇格** (user 承認) |
| **`SKIPPED_SPREAD`** (cap 10.0p 超) | 正当な未執行 | 分母記録のみ (`block_cause=weekend_gap_spread_cap(spread=X.XXp)`)。packet §6 row 1 の「cap skip を除く」により **G0' の 2 イベントに数えない** → 繰越 | 発動せず |
| **NO-QUALIFY** (3 ペアとも閾値未達) | 分母外 | gap 診断ログの値を card へ転記 (near-miss を理由に閾値は触らない — stage-2 §8)。次週へ繰越 (10-04 → 10-11 → …) | 発動せず |
| **同一週末に複数 pair-event が qualify** (例: fill + abandon) | pair-event 単位、**latch ts 順に逐次適用、G0' の 2 event で終了** | **順序キー = system_kv latch `weekend_gap_fade:{instrument}:{weekend_key}` の `ts`** (demo_trader.py:3995–4012 / 7009–7016: shadow row 作成直後・**OANDA 送信前**に 1 pair-event 1 回だけ永続化、deploy-restart safe — 終端結果の遅延 (halt-race 再送 +30s、`oanda_bridge.py:669–719`) に影響されない)。同 tick の shadow row `entry_time` (demo_trader.py:6949) を副キー、同秒は row id 順。**終端結果 (filled / cancel tx) の時刻で並べない** (反転例 (d))。Render ログ `[WEEKEND_GAP] … qualifying event` 行 (demo_trader.py:4246–4250) は**診断用のみ** — `_tick_entry` 前に print され、max_open / drawdown 等の guard (demo_trader.py:5282–5286) が latch 永続化 (7009–7016) の前に return すると**同一ペアが次 tick で再発火し複数の時刻を持つ**ため順序キーにしない (PR #281 review P2、4 巡目)。row も latch も無いまま entry 窓を終えたペアは列に現れない = §6「qualify 済み・送信経路未到達」の分類未定義項目。専用 first-qualification ts の永続化は code 変更 (R3、凍結値不変更) → §4 row 8 (本 PR では未実施)。**判定は G0' = 改定後最初の 2 qualifying pair-event のみ**: 09-13 USD_JPY = event #1 (不成立)。latch ts 順で最初に来る次の qualifying pair-event = **event #2 で G0' は終了** — fill → 完了・通常運用 (同一週末の後続 pair-event は記録のみ、trigger 対象外)、不成立 → 2 連続 = 発動。worked example (列 = latch ts 順、先頭 = 09-13 DRIFT): (a) `fill → ABANDONED_DRIFT → ABANDONED_HALT` → event #2 = fill → **G0' 完了、発動せず** (後続 2 放棄は §3-6 の観測データ。これを「隣接 2 不成立」として発動させる rolling 規則は packet §6 の外 = 未承認); (b) `ABANDONED_DRIFT → fill → …` → event #2 = DRIFT → **発動** (後続 fill は F2 resolve のみ); (c) `fill → fill → ABANDONED_DRIFT` → (a) と同じ; (d) 順序キーの反例: pair A latch 21:05:02 → SEND → halt-race 再送で 21:05:35 filled、pair B latch 21:05:10 → 即時 `ABANDONED_DRIFT`。latch 順では event #2 = A-fill → G0' 完了・発動せず。終端時刻順なら B-DRIFT が event #2 = **偽の発動**。F2 resolve (registry 明示編集) は fill の事実で独立に起きる。⚠️ packet §6 / registry g0prime は「イベント」の単位 (pair-event / 週末) を明示していない — **本稿の読みは pair-event。週末単位の別規則や G0' 終了後の rolling 連続不成立規則を運用に使うには packet §6 文言の user 承認が先** (未承認、本稿は使わない)。昇格時に文言を確定する | event #2 の結果のみで決まる (G0' 終了後は発動しない) |

**文言上の未整備 (昇格時に解消、凍結値には触れない)**: packet §6 row 1 は「fill 成立 (cap skip / **正当放棄**を除く)」、row 2 は「fill 不成立 (halt >15m / **drift 放棄** / 新種 cancel)」— drift 放棄が「正当放棄」に含まれるなら両行が矛盾する。運用上の読み (O-2026-09-14-1、registry g0prime message、[[2026-09-22-session]]) は **drift/halt 放棄 = 不成立、cap skip のみ = 正当な未執行**。本稿はこの読みで 09-13 を 1 件目とカウントしている。

---

## 3. 変更候補表 (発動時に一次データで確定する — 本稿は骨子)

前提: 09-13 型の不成立は「gap の大半 (~47p/50p) が OANDA halt 窓 (~4 分、48/48 で +4.0 分) の内側で消費される」型。**約定不能な時間帯に起きた値動きは、どの送信タイミング・注文種別でも捕まえられない**。したがって候補は (a) 消費後の残余で入る (drift 境界の変更) か、(b) 消費後の価格を基準に signal を再定義する (estimand の executable 化) か、(c) 何も変えず観測を積む、の 3 系統に分かれる。

| # | 候補 | 触る凍結値 (出所) | estimand への影響 | 09-13 型への効果 | 必要な検証 | user 承認 | 起案者暫定評価 |
|---|---|---|---|---|---|---|---|
| 1 | **打ち切り +15 分 の変更** (+30 分 / entry 窓末端 60 分まで) | `WEEKEND_GAP_HALT_ABANDON_MIN = 15` (`strategies/daytrade/weekend_gap_fade.py:89`)、packet §4-2、test pin `tests/test_weekend_gap_execution_contract_b.py:120` | entry が Sunday open からさらに離れ、繰下げ drift コストが増える方向 (全 48 の +15m adverse drift mean 1.27p / p90 5.6p / max 30.4p、json)。qualifying サブセットの +15m 値は未計測 | **なし** — 打ち切りは一度も binding していない (実開場 +4.0 分 48/48、09-13 も tradeable 確認済みで放棄理由は drift) | 価格のみ: `tools/wg_gap_drift_measure.py` の offset を 30/60 分へ拡張し、09-06 以降の新週末で再計測 (outcome 非結合、OOS 窓不接触) | 凍結値変更 = **R1** | **動機なし、据え置き**。11-01 DST の R3 再導出 (§5) のみ実施 |
| 2a | **drift 境界 +8.0p 据え置き** | — | 不変 | なし (09-13 型は今後も放棄され続ける = 選択バイアス仮説が真なら「最大級 event を live から系統的に除外」) | §3-6 の forward 観測で仮説を検証 | 不要 | 現状。fill 成立率の見積り (点 ~94% / 保守 ~75%、packet §5.2) は **+8.0p 抵触率 3/48 を全週末で置いた値** — qualifying 大 gap 週末での抵触率が高いなら見積りは過大。昇格時に修正値を出す (価格のみで可) |
| 2b | **drift 境界の引き上げ** (例: 固定 12p / 15p / 全週末 p95) | `WEEKEND_GAP_DRIFT_ABANDON_PIPS = 8.0` (`:90`)、packet §4-3、test pin `:132`、demo_trader.py:4192 コメント | 境界は「凍結 stressed-net +7.90p を全消しする水準」として導出 (packet §4-3)。引き上げ = **mean 基準で残余 EV ≤ 0 の event を live 母集団に入れる**。「大 gap ほど 4h で多く戻る」が真なら救われるが、それは **outcome 条件付き主張 = OOS 窓では計算禁止**。shadow 分母は不変 (LIVE 側 winning-location フィルタの緩和、4原則#3 の非対称は保たれる)。G2 (−60p) が per-N の唯一の防波堤になる | 部分的 (+41p は 12p/15p でも放棄。09-13 型を救うには実質 2d) | (i) 価格のみ: \|gap\| vs tradeable 時 drift の相関 (O-2026-09-14-1 の反証可能予測) を forward 週末 + json 48 件で計測 — 可。(ii) outcome 条件付き (drift 帯別の 4h 回帰): **OOS 窓 = 禁止** / **explore 窓 (2014–2021) = 仮説生成のみ可、confirmatory 価値なし**、しかも explore 窓に 1m データが無ければ tradeable 時点 drift を再現できない (実施可能性未確認)。(iii) **fresh forward OOS** (境界値を pre-reg し live/shadow 両方で N 蓄積) = 唯一の confirmatory 経路、N は 2.07 週末/月で遅い | **R1 全段 + user** (凍結値変更 + 4原則 解釈は UD7 と同型) | 効果が限定的で estimand コスト大。**単独では推奨しない** |
| 2c | **gap 比例境界** (0.4×\|gap\| 等) | 同上 | パラメータ面の拡大 (packet §4-3 で**不採用済み**) | 09-13: 0.4×50 = 20p でも +41p は放棄 | 同 2b | R1 | packet 決裁を覆す理由が無い。**不採用維持** |
| 2d | **drift 境界の撤廃** (tradeable 確認のみで送信、G1/G2 のみで防御) | 同上 + packet §4-3 削除 | **per-event の負 EV 上限が消える**: 09-13 なら残余 (−50+41) = 9p の gap を fade する entry になり、凍結 stressed-net +7.90p は mean で全消し済み。live 母集団 = 「qualify した全 event の tradeable 価格 entry」= **OOS が測った estimand (Sunday open 価格 entry) とは別物**。G2 −60p は N=12 まで作動しない | **有効** (09-13 型は fill する) — ただし fill する = 負 EV の可能性が高い event を取ることと同義 | 同 2b(iii): fresh forward OOS のみ。事前に「fill 成立率↑ と per-event EV↓ のトレードオフ」を凍結値からの単純減算で開示 (packet §5.3 の様式) | R1 全段 + user | F2 (12-31、N≥1) を確実に resolve する最短経路だが、**「PASS→live 変換の実証」ではなく「別 estimand の live 開始」**。F2 の趣旨 (PASS の live 変換) を満たすかは user の解釈事項として上程する |
| 3a | **送信タイミング: 現行** (tradeable 後の最初の評価 tick、poll ≤60s) | — | 不変 | なし | — | 不要 | 現状 |
| 3b | **22:01 固定 (spread 崩落後)** | packet §4-1 / stage-2 §1「22:01 遅延は estimand 変更 = OOS 再検証不能 → 前向き検証のみ」(既裁定) | entry が open+61 分 → 繰下げ drift がさらに増加。spread は通常圏 (cap 10.0p の意味が消える) | **なし** (drift は増える方向) | fresh forward のみ (既裁定) | R1 | 既裁定どおり **不採用** |
| 3c | **tradeable poll の短縮** (≤60s → ≤10s) | `WEEKEND_GAP_TRADEABLE_POLL_MAX_SEC = 60.0` (`:91`)、packet §4-1 | drift 窓が最大 50s 短縮 = favorable 方向。estimand 上は同一 (tradeable 後初 tick) | **なし** — 09-13 は tradeable 確認時点 (quote_age 7.5s) で既に +41p。消費は halt 窓内 | 価格のみ: EXEC_B ログの tradeable 確認〜送信の実遅延を forward で記録 | 凍結値 = R1 (ただし方向は保守側のみ) | 効かないので**単独起案しない**。他候補と同時なら同梱可 |
| 3d | **開場前 pending 注文** (halt 中に limit/stop を置き、開場と同時に成立させる) | 契約 B §4-1 (送信前置条件) + stage-2 §2.2 | 指値化 (#4) と同じ estimand 問題 + **OANDA が halt 中の pending order を受理するかが未確認** (`MARKET_HALTED` は FOK cancel の reason として実測済みだが pending 受理可否は一次確認ゼロ) | 不明 (仕様次第。stop 注文なら 09-13 型は約定するが adverse 方向の約定になる) | 一次確認 (OANDA API 仕様 read-only) → 成立しても #4 と同じ検証が必要 | R1 | 一次確認だけは昇格前に可 (仕様読み、発注なし)。採用は #4 と同じ扱い |
| 4 | **指値化** (Sunday open 価格 / open±x に limit、GTD = 打ち切り) | stage-2 §2.2「指値変種は不採用」、packet §3 (C) 棄却 | fill が「価格が基準まで戻る」条件付きになる = **adverse selection** (gap が fade しない/再拡大するときだけ fill) | **なし** — 09-13 は BUY fade で価格が open より +41p 上。open (153.120) の BUY limit は gap 再拡大時しか fill しない | fill 率は forward のみ (shadow 側で「指値なら fill したか」を価格のみで並行記録 = 分母外の観測、stage-2 §2.2 が既に許容) | R1 | 09-13 型の救済にならない。**不採用維持**、並行記録のみ検討 |
| 5 | **シグナル基準の executable 化** (sunday_open = OANDA 初 tradeable mid、gap も同基準で再計算) | シグナル定義 (card §シグナル定義、stage-2 §2.1、OOS prereg §2 凍結定義「Sun 21:00 UTC 以降の最初の 15m バー Open」) — **OOS estimand そのもの** | **最大**。09-13 は gap −50 → 残余 ≈ −9p で **qualify 不成立** (不成立ではなく分母外へ移る)。OOS verdict (arm B PASS) は Sunday open 基準で測ったもので、この定義には**適用できない**。OOS 窓で再計算 = 再接触 = 禁止 → 事実上 **新 family** | 「不成立」を消す (イベント自体が消える) — 選択バイアス問題の定義上の解消であり、EV の証明ではない | fresh forward OOS のみ (N floor は OOS prereg §4(e) arm B N≥60 相当 → 数年)。explore 窓は 1m データが無ければ再現不能 | R1 全段 + user (family 新設に相当) | 論理的に最も正直だが、**時間軸が M 系列と噛み合わない**。昇格時に「選択肢として上程、推奨はしない」 |
| 6 | **契約不変更の forward 観測パケット** (放棄イベントの価格系蓄積) | なし | なし (観測のみ)。EXEC_B ログと `[WG_EXEC_B]` reasons が既に drift / send_mid / tradeable / quote_age を永続化 (§4.6) | 救済しない。**2b/2d/5 の検証入力になる** | 価格のみ: 全 qualifying event の (\|gap\|, tradeable 時 drift, decision) を card に転記 → O-2026-09-14-1 の予測 (\|gap\|≥40p で drift>8p が常態) を N 蓄積で検証。outcome 非結合 | **不要** (記録のみ、R3) | **今すぐ実施 (本 PR の card 転記がその第 1 行)**。no-regret |
| 7 | **G0' 判定規則の文言整備** (packet §6 の「正当放棄」/ 単位) | なし (文言のみ、閾値不変) | なし | なし | — | 解釈確認 1 行 | §2 末尾の読みで運用、昇格時に packet §6 へ追記 |

**表の読み方**: 09-13 型を live fill に変えられるのは 2d と 5 だけで、どちらも「OOS が PASS した estimand とは別の estimand を live で始める」ことになる。これは **「PASS→live 変換の実証」(F2 の趣旨) とは別の問い**であり、昇格時の packet はこの点を user 向け 3 行の 1 行目に置く。

---

## 4. 発動時の R1 起案 packet の構成 (packet 2026-09-10 の様式を踏襲)

| § | 内容 | 本 DRAFT からの引き継ぎ | 発動時に追加する一次データ |
|---|---|---|---|
| 0 | 決裁サマリ 3 行 | §0 | 不成立 2 件目の事実 (時刻・decision・drift・tx) |
| 1 | 故障の機構 (2 不成立の root cause 分解: drift 型 / halt 型 / 新種 cancel) | §1 | 2 件目の EXEC_B ログ全遷移 (HOLD→SEND/ABANDONED)、oanda_audit 行、cancel tx (該当時) |
| 2 | 一次データと測定 (価格のみ、look-burn 回避の宣言) | §3 の検証列 | `tools/wg_gap_drift_measure.py` を 09-06 以降の週末で再走 (offset 拡張含む)、qualifying event の (\|gap\|, drift) 表 |
| 3 | 候補比較 | §3 表を確定 | 各候補の fill 成立率見積り (価格のみ) と per-event EV の凍結値からの単純減算 |
| 4 | AMENDMENT 条項案 (採用候補のみ、承認時にこの文言で LOCK) | — | 触る凍結値の新値と根拠、不変更リストの明示 |
| 5 | fill 成立率の事前見積り + estimand コスト (F2 テンプレ、meta-audit §6) | §3 の estimand 列 | 2 件の不成立を含めた見積り修正 (qualifying 大 gap 週末の抵触率) |
| 6 | 採用/棄却境界 (forward、承認時に凍結) | §2 の様式 | 新契約下の G0'' (最初の 2 qualifying event) と「3 度目はしない」の帰結 (family live-execution 保留の条件) |
| 7 | registry 変更提案 (registry 本体は別担当) | §6 の 24h 規則 | g0prime 期日繰越 / F2 message 追記 / G1・G2 message 追記 |
| 8 | 実装チェックリスト + pre-reg 突合 (stage-2 §8 様式) | — | 凍結値 pin テストの更新範囲、counterfactual pin を同一 commit。**専用 first-qualification ts の system_kv 永続化** (qualifying event 判定時に 1 回、guard early-return の再発火で上書きしない — R3、凍結値不変更、PR #281 review 4 巡目) は発動と無関係に単独 R3 PR で実施可 |

**禁止事項 (packet §4 末尾の継続)**: OOS 再接触・再集計 / qualify 閾値・cap・G1/G2/G3 凍結値の変更 (候補が触るのは §4 AMENDMENT 条項の値のみ) / BE/Trail/TP 追加 / GBP_USD 拡張 / 「observe して待つ」の 3 度目。

---

## 5. 冬時間 2026-11-01 — 打ち切り時刻の R3 再導出 (2026-10-25 までに完了)

- **暦**: EU 夏時間終了 = 2026-10-25 (10 月最終日曜) だが OANDA の週明け開場は NY 17:00 基準で **10-25 は 21:00 UTC のまま** (US は EDT 継続)。US 夏時間終了 = **2026-11-01** (11 月第 1 日曜) → 以後 Sunday open **22:00 UTC**、実開場は stage-2 §2.1 の記載どおり **22:04 見込み** (未実測 — 凍結 12 週末・16 週末とも全て夏時間、packet §5.3 (i))。
- **再導出の対象は「基準時刻の解決」であって「+15 分」ではない** (+15 分は凍結値、変更は R1)。10-25 までに以下を price-only / code-read で確認し、結果を [[weekend-gap-fade]] へ追記する:
  1. `first_bar_ts` (`det["first_bar_ts"]`、demo_trader.py:4205) が冬に **MASSIVE 22:00 stamped バー**へ解決するか — 前冬 (2025-11-02〜2026-03-08) の Sunday 初バー ts を parquet で読む (価格系のみ、outcome 非接触)。`weekend_key_for` は `hour >= 21` で 22:xx を含む (`weekend_gap_fade.py:120` docstring)。qualify guard の冬 22:00 は `tests/test_weekend_gap_fade.py:166` で pin 済みだが、**打ち切り基準 (first_bar_ts + 15 分) の冬解決は pin されていない** → test 追加は R3 (凍結値に触れない)。
  2. もし MASSIVE が冬に 21:00 stamped バーを出す構造なら、打ち切り 21:15 < 実開場 22:04 で **毎冬週末 `ABANDONED_HALT` が決定論的に発火 = 冬季 live fill 0 の構造バグ** → Rule 3 (構造バグ) で 11-01 前に修理。これは「+15 分」の変更ではなく基準時刻の是正。
  3. G0 発火時刻仕様 (冬 22:05±5m、card §前向きゲート) と EXEC_B の実送信時刻の整合を 11-01 当日に確認 (packet §6: 実開場が 22:04–22:05 から >±10 分乖離 → R3 再導出、凍結値変更は R1)。
  4. 11-01 が qualify した場合は **G0' の event としても数える** (DST を分母外にしない)。同日は `tools/sunday_open_spread_measure.py` / `wg_gap_drift_measure.py` の月次 re-run を必ず走らせる (常設 gate、冬時間初週末は注視 — card §前向きゲート「常設」)。
- **期限**: 1–2 を 2026-10-25 まで、3–4 は 11-01 当日〜11-02 (24h 規則)。

---

## 6. 記録規則 — 「イベント後 24h 以内に card 転記」 (g0prime 手順への追記案)

- **事実**: 09-13 の event #1 は O-2026-09-14-1 (09-14) と trade-log 09-16 に記録されたが、戦略カード [[weekend-gap-fade]] のイベントログには **2026-09-22 (9 日後) まで転記されなかった**。G0' 手順は「週次監査で確認」としか書いておらず、card 転記の期限が無かった。
- **規則 (提案、registry g0prime message への追記 = 別担当)**: 日曜 21:00 UTC (冬 22:00) のイベント後 **24h 以内 (月曜 daily report と同時)** に、qualify / NO-QUALIFY を問わず card イベントログへ 1 節を追記する。
- **転記するもの (価格系・執行系のみ)**: ペア別 gap (p) と閾値、**system_kv latch `ts` (pair-event 列の順序キー、§2) と shadow row `entry_time`**、qualifying event ログ行の発火時刻 (診断用 — 再発火があれば全件を列挙し、順序キーには使わない)、decision (SEND / HOLD 回数 / ABANDONED_* / SKIPPED_SPREAD)、tradeable・quote_age、drift (p)、send_mid、latch 値、oanda_audit id / tx id と終端結果の時刻 (fill / cancel — 順序キーには使わない)、fill 時は `oanda_trade_id` と当該 1 event の persisted slippage 値 (配管確認、集計しない)。
- **ペア別分類の確定源は Render ログ `[WEEKEND_GAP]` gap 診断行 (`gap=… no-qualify` / `qualifying event`) または shadow row のみ**。oanda_audit の有無・行数から no-qualify を推定しない — audit 不在は「監査経路未到達」しか意味せず、`_weekend_gap_tick` の非監査 return (weekend_key None / latch 済 / データ欠損・不足 / det None) や `_tick_entry` の早期 block で qualify 後に消えた pair-event と区別できない。診断行が retention (~30 日) 内に読めなければ当該ペアは **UNKNOWN** と転記し、pair-event 列 (§2) と G0' カウントは「UNKNOWN が qualify していた場合の条件付き」で併記する (PR #281 review P2、2 巡目)。**診断行自体が無い qualify 済みペア** (データ欠損で `det is None` かつ `gap_pips` None、または `_tick_entry` 早期 block) は packet §6 の列挙 (halt / drift / 新種 cancel) の外 = 分類未定義 → 昇格時の文言確定事項 (§3 row 7) に含める。
- **転記しないもの**: shadow row の pnl / MFE / 埋め率、G1 rolling mean、G2 累積、drift 帯別や CB 週別などの条件付き outcome (O-2026-09-14-2 の教訓 — 未登録 split の事後シードは禁止)。
- **NO-QUALIFY 週末も転記する**: 近接値 (09-20 の −19.0p / −20.5p) は「閾値を触る根拠」ではなく「分母外イベントの記録」。閾値は凍結値 (stage-2 §8)。

---

## 7. 禁止事項 (本 DRAFT と昇格後の packet に共通)

- OOS 窓 (2022-01-01〜2026-06-30) の再接触・再集計、shadow outcome の転記、G1/G2 の中間計算、drift 帯別・gap 帯別の 4h 回帰の計算 (どの窓でも confirmatory には使えない、explore 窓は仮説生成のみ)。
- 凍結値 (+15 分 / +8.0p / poll 60s / quote age 10s / 再送 30s×1 / cap 10.0p / 1000u / 4h / disaster SL 150p / qualify 閾値 / G1 +2.0p / G2 −60p / G3) の autopilot 変更。全て R1 + user。
- near-miss (09-20 −19.0p / −20.5p、07-26 +19.9p) を理由にした qualify 閾値の再計算 (定義ドリフト、`weekend_gap_fade.py:50–51` コメント)。
- 「live fill 0/7 累計」型の改定前後混在カウント ([[path-to-win-reassessment-2026-09-22]] §7-7)。改定後の連続不成立は **契約 B 下の qualifying イベントのみ**で数える。
- 「観測して待つ」の 3 度目 (packet §6)。発動したら 7 日以内に packet v1 を出す。
- 本 DRAFT を LOCK / 決裁済みとして引用すること。
- watcher (`evaluate_live_count_decision`) の `TRIGGERED` 表示を F2 **resolved** と読むこと — resolve は registry の `active:false` + `resolved` + `resolution` 明示記録のみ (§2 row 1、PR #281 review P2)。
- pair-event 列を週末単位で一括分類すること (fill の有無で週末をまとめて成立/不成立と読む) — 判定は pair-event 単位、対象は G0' の 2 event のみ (§2、PR #281 review P2 1・4 巡目)。
- G0' event #2 が fill で完了した後も連続不成立 trigger を生かし続けること (rolling gate) — packet §6 は「改定後の最初の 2 qualifying イベント」のみ、継続は packet 改定 = user 承認 (PR #281 review P2 4 巡目)。
- SEND 後 2 回とも `MARKET_HALTED` cancel を「新種 cancel でない」として不成立から外すこと — trade id も filled audit 行も無い = 不成立 (halt 型) (§2 row 2、PR #281 review P2 4 巡目)。
- oanda_audit の不在・行数から未観測ペアを no-qualify と分類すること — 確定源は gap 診断ログ / shadow row のみ、読めなければ UNKNOWN (§6、PR #281 review P2 2 巡目)。
- pair-event 列を終端結果 (filled / cancel tx) の時刻、または Render ログの qualifying event 発火時刻で並べること — 順序キーは system_kv latch `ts` (送信前・1 回・永続) のみ。終端時刻は halt-race 再送 +30s で反転し、ログ行は guard early-return で同一ペアが再発火して複数時刻を持つ (§2 (d)、PR #281 review P2 3・4 巡目)。

---

## 8. user 承認が必要になる点 (発動時のみ、現時点では 0 件)

| id | 問い | 選択肢 | いつ |
|---|---|---|---|
| W1 | R1 再審起案の承認 (packet v1 提示) | 起案する / family live-execution 保留 / 契約 B 継続で観測延長 (packet §6 は「3 度目はしない」と凍結しているため、これは §6 の撤回 = 明示決裁が必要) | 不成立 2 件目 +7 日以内 |
| W2 | 候補の選択 (§3: 2a / 2b / 2d / 5 / 6 のみ、他は不採用維持) | packet v1 §3 の比較表 | packet v1 提示後 |
| W3 | F2 の解釈 — 「PASS→live 変換の実証」は Sunday open 基準 estimand の live fill のみを指すか、executable 基準 (2d/5) の fill も含むか | 前者 / 後者 | W2 と同時 (2d/5 を選ぶ場合のみ) |
| W4 | 4原則#3 の解釈 — drift 境界は「勝てる場所で勝つ条件だけ転送する LIVE 側フィルタ」として意図的か (UD7 velocity_down と同型) | 解釈の裁定 | W2 と同時 (2b/2d の場合) |

---

## 参照

- [[weekend-gap-fade]] (戦略カード、イベントログ 2026-09-13 / 2026-09-20 節は本 PR で転記) / [[weekend-gap-execution-contract-r1-packet-2026-09-10]] (§4 AMENDMENT、§5 見積り、§6 境界) / [[weekend-gap-stage2-execution-prereg-2026-07-24]] (§2.2 原文、§8 禁止事項) / [[weekend-gap-oos-prereg-2026-07-24]] (§3 OOS 窓と接触規律)
- [[daily-observations-2026-09]] O-2026-09-14-1 (event #1 の価格系記述と選択バイアス仮説) / O-2026-09-14-2 (未登録 split 事後シード禁止の教訓)
- [[2026-09-16]] L241–242 (oanda_audit の放棄行と日別行数) / [[2026-09-22-session]] (09-20 NO-QUALIFY の Render ログ実読)
- [[path-to-win-reassessment-2026-09-22]] §3 Rank 6 / §7-7 / §8 (wg 頻度 N=4 の caveat)
- [[process-meta-audit-2026-09-07]] §6 F2 (2026-12-31)
- code: `strategies/daytrade/weekend_gap_fade.py:50–58, 68–70, 89–97` / `modules/demo_trader.py:97–100, 4180–4245` / `tests/test_weekend_gap_execution_contract_b.py:54–66, 120, 132` / `tests/test_weekend_gap_fade.py:166`
- data: `bt-results/wg_gap_drift-2026-09-10.json` (16 週末 × 3 ペア、2026-05-24〜09-06、価格のみ)
- 規律: [[lesson-asymmetric-agility-2026-04-25]] (停止 = R2 軽 / 増額・契約変更 = R1 重)、MEMORY `feedback_audit_past_verdicts_2026_08_05` (falsification 引用前の estimand 監査)
