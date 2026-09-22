# 30 日スプリント triage + PR 規律 — user 決裁「推奨で任せる・ペースアップ」(2026-09-22) の執行枠

作成規律: 文書のみ (R3、code 変更なし、価格データ・DB 計算ゼロ、凍結 look の outcome 非接触)。本文書は [[path-to-win-reassessment-2026-09-22]] §3 Rank 4 (i)(iii)(iv) と §5-1 の成果物であり、同 §3 の 8 項目表・§6「やめること」を **容量規律と引用規律として転記**する。数字は出所 (path:line / API / log) を併記し、新しい数字は作らない。引用禁止値 (nav_floor fit 現況値 / L1 5000u 前提の M2 寄与額 / keeper 控除前の M2 算数 / P5 確率 / falsified family の再試行) は書かない。Live = `oanda_trade_id != ''` のみ。

略号: KB = `knowledge-base/wiki/`、REG = `KB/decisions/prereg-trigger-registry.json`、memo = [[path-to-win-decision-memo-2026-09-20]] (§4.1 = 30 日 17 項目)、REASSESS = [[path-to-win-reassessment-2026-09-22]]、facts = orchestrator 一次事実 (2026-09-22 06:10Z 収集、Render / OANDA / `/api/demo/*` 実読)、G4 = 同日 process・容量 ground (REASSESS §1「プロセス・容量」行 L43 に集約)。

---

## 0. TL;DR

- **user 決裁 (2026-09-22)**: 「推奨で任せるから進めて、勝てるまで行こう、ただしとにかくペースアップしたい」。推奨 = REASSESS §3 の 8 項目 (Rank 1–8) を autopilot で執行、ペースアップ = 欠陥税を下げる容量規律 (本文書 §3)。**品質規律は不変** — 凍結 look の outcome 非接触 / autopilot 禁止 3 件 (carry_dip SL 150p 復元・ps_aud_jpy 降格・M2 estimand 変更) / counterfactual pin は同一 commit。
- **30 日 (〜10-22) は 8 項目に絞る** (memo §4.1 の 17 項目を triage)。落とした 8 項目は 90 日側に parking (§2.2)。理由は「不可能」ではなく **「タイト、triage 必須」** — 供給 [10.5, 19] セッション/30 日 vs 需要 15〜21.5 (G4 §5、REASSESS L43)。
- **PR 規律 4 点** (§3): 起票時に巡目上限を宣言 (P2 ≤6、P1 は例外なく修正) / code PR マージは 1 日 1 バッチで market-safe 窓のみ / 並行 PR は worktree 分離 + hot file 不接触 / `tools/pr_review_gate.py` + inline thread 直読み。
- **09-22 本番 HTTP 全断 00:15→03:35Z (3h20m)** を root cause UNKNOWN で記録 (§4)。daily report の「無料 tier スリープ」帰属は無効。
- 「勝てるまで」の 30 日の意味は REASSESS §0 のとおり **(c) 測定可能状態の確立 (10-08 パケット) + (b) kill 検知器の是正 + floor・観測系の防御**。(a) M2 到達は user 決裁 (U3 ∧ D1) でのみ有限化され、Claude の $0 施策では 30 日で動かない (REASSESS §0–§2)。

---

## 1. user 決裁 2026-09-22 の記録と委任範囲

### 1.1 決裁文言と解釈

| 項 | 内容 |
|---|---|
| 決裁文言 (verbatim) | 「推奨で任せるから進めて、勝てるまで行こう、ただしとにかくペースアップしたい」(2026-09-22、workflow harness 経由の user 発言) |
| 「推奨」の指示対象 | REASSESS §3 の 8 項目 (Rank 1–8、両レンズ keep または再分類後で採用) と §5「今週やること」。09-20 memo §4.1 の 17 項目ではない (REASSESS で 5 点訂正済み、memo は SSOT から REASSESS に更新) |
| 「進めて」の範囲 | Claude autopilot = R3 文書 / tools・tests PR / live 経路の R3 構造修理 (storm guard) / record-only 転記 / registry 期日消化。**Rule 1 (新戦略・新フィルタ・昇格・lot↑) と user 専権事項は含まない** |
| 「勝てるまで」 | 30 日で到達可能なのは REASSESS §0 の (c)+(b)。(a) M2 は time-to-M2 = ∞ (現行定義 × 現 NAV × $0 施策、REASSESS §1–§2) で **user 決裁 (U3 ∧ D1) 待ち**。「勝てる」を M2 到達と読み替えて lot↑ / 新セル追加 / gate 緩和を autopilot で行うことは本決裁の範囲外 |
| 「ペースアップ」 | 09-18〜22 の人手 commit 62 件のうち review-fix 48 件 = **77.4%** (G4 §2.1)、code PR の巡目中央値 ≈ 8.5 (#273 は 27 波、G4 §5.1)。この欠陥税を下げる = **§3 の PR 規律**。品質規律の緩和ではない |

### 1.2 委任外 (user 専権 — autopilot・default で反転させない)

| id | 事項 | 根拠 | 期限 / 既定 |
|---|---|---|---|
| U2 | 資本上限 (1 数字) | [[process-meta-audit-2026-09-07]] 残 user 決裁 / REASSESS §4 UD4 | 推奨 10-15 (11-30 まで) / 無回答 = U3 上界不定 |
| U3 | 入金 / 縮退 / 停止 | memo D3 / REASSESS §4 UD5 | 11-30 (E1 verdict 10-15 後) / 無回答 = 何も起きず、F4 fit 発火は 12-04〜01-08 の幅 (keeper のみなら F2 12-31 の後)、Claude は 12-03 に record 再上程 (執行なし) |
| D1 | M2 会計 (A: NAV 実現 keeper 込み / B: edge-only) | memo D1 / REASSESS Rank 1 | 11-30 / 無回答 = 現行 A のまま。**M2 estimand 変更は autopilot 禁止** |
| D5 | carry_dip disposition (SL 150p 復元 / velocity_down 免除 / LIVE 停止・shadow 継続 / 現状維持) | 08-07 user 決裁事項 (memo §4.1 禁止 3 件) / REASSESS §4 UD6 | 11-30 (REG `carry-dip-v3-revival-watch` backstop) / 現行 live 継続。R2 autopilot は demo `pnl_pips` と broker realized の **両方**で deduped LIVE N≥10 ∧ EV<0 のときのみ |
| D6 | ps_aud_jpy 降格 | 08-12 user 決裁 (watchdog 委任) / REG `ps-carveout-regate-post-172` 09-30 | 09-30 regate に委任、autopilot 降格禁止 |
| UD1 | Gold 算入確認 (OANDA status 画面「今月の取引額」に 9 月 keeper 26 RT が算入されているか) | REASSESS §4 UD1 (status 頁「毎営業日判定・順次適用」= 今日読める) | 09-23 即日 / 無回答 = keeper は設計どおり 10 月 run |
| UD2 | Render workspace 選択 (対話セッション 1 回、§4 の request log 読み取り前提) | REASSESS §4 UD2 | 09-26 / 無回答 = root cause UNKNOWN のまま |
| その他 | kalman 契約変更 (D7) / 0.2x 再基準化 / floor バッファ ¥12,000 縮小 / wg disaster SL 137p・rung 4000u (LOCKED) / G3 N≥30・Wilson gate 緩和 / keeper on-off / U3 前の live セル追加・lot↑ / wg 執行モダリティ R1 再審の承認 | REASSESS §6「autopilot 禁止」 | user または Rule 1 のみ |

---

## 2. 30 日 (〜2026-10-22) 採用 8 項目と 90 日 parking

### 2.1 採用 8 項目 (REASSESS §3 L67–L74 の転記、correction 反映後の文言)

| Rank | 施策 | owner / Rule | 期限 | 効果 (time-to-M2 3 択) | 反証結果 |
|---|---|---|---|---|---|
| **1** | **統合決裁パケット起票** (v0 09-29 → 確定 10-08、user 返答 11-30、D1–D4 先行可)。同梱: D1 A/B の読み手 3 行 (A = broker NAV Δ、未計測・broker tx 起点必須 / B = 全 clean live 30d −0.086〜−0.099% / 現行 M3b = winner-selected 診断ラベル) / **D2(i) = 07-03 P0-1 (`modules/demo_trader.py:7571–7578`) vs 08-05 template L73 の user 決裁 2 件の衝突として上程** (L1 開通と同時に binding) / D3 4.2 多 leg 解釈は user 項目 (L1 開通 NAV ¥300k vs ¥900k) / D10 は固定費台帳の月額のみ / D11 に母集団軸 (demo `pnl_pips` vs broker realized) + 閾値軸 (REG PnL>0 vs monitor EV≥+1.0 ∧ Wilson_lo>0) を追加 (D14 新設せず) / D15 floor バッファ (¥262k は自前、OANDA 条件は残高 ≥¥250k) / USD-quote L1 ¥472,800 / carry_dip N 基準 (demo 14 / broker 11 / 突合 7、reconcile 対象 14 本) / 2 セル算数 @NAV ¥300k を Poisson CI 付き併記 / M1 feasibility (09-01 案 A 再決裁・swap 項・unverifiable 明記) / U3 期限 vs keeper 支出 / Gold 判定を前提条件に。**既定挙動 = 「無回答なら何も起きず余裕 ¥13,517 の 15.4%/月を消費、F4 fit 発火は 12-04〜01-08、Claude は 12-03 に record として再上程 (執行はしない)」** | R3 文書 / Claude → user-decision | v0 09-29 / 確定 10-08 | **∞→有限の唯一経路の「可能化」** (D3=(i) ∧ D1)。Claude 単独では効かない | 3 提案とも keep (6/6)。訂正: L1 5000u 前提の M2 寄与額を除去 / 既定挙動「F4 12-03」は fit writer で不成立 / 「D3 既決」refuted / 「D2(i) 表示のみ」refuted / D14 は D11 統合 |
| **2** | **E1 凍結 export tool + 10-08→10-15 手順書 + second look cutoff #2 (12-30) 手順 + UNDERPOWERED 時 (a-1) probe 扱いの一行定義** (10-14 まで KB 固定)。`/api/positioning/export` snapshots 13 instrument + health_log → JSON/parquet + sha256 → `raw/bt-results/`、合成 artifact roundtrip テスト同 PR pin。**試走は `table=health_log` か合成 artifact のみ** (limit=1 snapshots は生 skew 値閲覧で [[e1-positioning-contrarian-prereg-2026-07-16]] §6-2 許可リスト外)。tool 不在 ≠ verdict 無効 (手続き要件は手作業でも満たせる) | R3 / Claude | 10-06 (cutoff 10-08T06:33:31Z の前) | 効かない (E1 PASS 点推定 4.0%、Wilson 0.7–19.5% / PASS でも live N≥30 は 2027-05〜09) | 3 提案 keep (6/6)。訂正: 試走範囲 / 「無効化リスク」の限定 |
| **3** | **kill 検知器の estimand 是正 (観測前)**: (i) **F4 推定器 hardening を 30 日に戻す** — 「keeper 決定論分 + edge 30d 実測」への分解 (窓延長は効かない)、counterfactual pin は再現値で書く、REG `project-falsification-f4-nav-floor-clock` message に方法変更 + 発火日シフトを記録、cron 側で writer 失敗 (09-22 03:13Z) を露出 / (ii) **F3 両基準併記**: `tools/m1_clean_live_monitor.py --strong` に broker realized 列を EV≥+1.0 ∧ Wilson_lo>0 の同 2 条件で計算 (Rank 5 の reconcile 出力に直列依存)、REG `project-falsification-f3-m1-durable-cell` message に「D11 決裁まで両基準併記・N≥30 到達後の基準選択は禁止」1 文 / (iii) M3b 出力に「winner-selected 診断」ラベル | R3 (tools + REG message) / Claude、基準選択は user (D11) | F4 10-31 / F3 11-10 (carry_dip N≥30 最速 11-18 の前) | 効かない (有限化後: N 基準で carry_dip N≥30 到達日が Δ≈2.7 ヶ月動く) | P_A stop「F4 は fit 非依存で 90 日へ」= 両レンズ refuted → 30 日復帰 / P_B Rank 2 keep / P_C Rank 3 reclassify (D11 統合) |
| **4** | **容量規律 + インシデント記録 + deploy churn 遮断** — **(i)(iii)(iv) = 本文書** (§3.1 巡目上限 / §2 triage / §4 インシデント) / (ii) マージ窓 = §3.2 / (v) daily report 全 API 失敗時 NO-DATA スタブ + analyst prompt にホスティング事実 (monitoring 経路 = review gate 対象) / (vi) `render.yaml` ignoredPaths に **`data/external/**` と `data/monitoring/**` のみ追加** (`data/cache/**` は CI pin `tests/test_render_build_filter.py:29–35,94–101` + `modules/yield_data.py:23,43` runtime read で FAIL → 別 R3 で 3 階層再分類) / (vii) DB 非接触 engine-tick health endpoint + per-request latency log | R3 / Claude | (i)(iii)(iv) 09-23 / (v)(vi) 10-03 / (vii) 10-10、中間チェック 10-06 | 効かない (前提条件 + F4 入力欠行防止 + 再起動 reset 減) | P_A Rank 3 keep (P2 限定) / Rank 4 reclassify / P_C Rank 8 keep。「`data/cache/**` 追加」refuted / 「夜間 deploy 2 回/日」→ ≥3 回/日 / 「算数で不可能」→「タイト」 |
| **5** | **carry_dip: card L3 訂正 + 14 本 reconcile (one-off GET) + block 理由確認**: (a) [[usdjpy_carry_dip_accumulator]] L3 の agg_kelly 帰属を code (bypass set `demo_trader.py:10560–10586`) と 11d block 台帳 (AGG_KELLY 0) で訂正、L1「08-14 以降」と #677396 (08-12) の衝突も訂正 / (b) 未突合 7 本 (#677931/#681149/#837978/#847578/#549260/#573986/#677396) を `/api/oanda/transactions` GET で one-off 突合し 14/14 の符号確定 / (c) 11 fill の entry 直前 60 分下落幅 vs velocity_down 20p 閾値を **価格キャッシュ (H1/M15) から計算** (Render ログ retention 30 日で 08-14 以降は不在) → 「≈5 シグナルの block 理由確認」として R3 文書 (「帰属確定」「設計衝突」と断定しない) / (d) block 台帳 readout tool。**R2 autopilot 執行は demo `pnl_pips` と broker realized の両方で deduped LIVE N≥10 ∧ EV<0 のときのみ** (現状 demo N=14 EV +7.36 で不成立、突合 7 本は N<10) | R3 分析 + tools PR / Claude、R2 は上記条件のみ、D5 は user | 10-06 (パケット v1 入力) / tool 10-15 | 効かない (carry_dip は G3 不成立で L1 候補外) | P_A Rank 5 keep / P_C Rank 5・7 reclassify。「符号逆」refuted (突合 7 本は demo −16.4p / broker −41.1p で両方負、正符号は未突合 3 本 +130.9p が担う) / 「08-14 以降ログ」refuted / broker-only R2 執行は凍結 estimand 差し替えで不可 |
| **6** | **wg G0' 記録 + 09-27 21:00Z event #3 の分岐事前固定**: [[weekend-gap-fade]] card L118 以降に 09-13 ABANDONED_DRIFT (+41.0p > +8.0p) と 09-20 NO-QUALIFY (USD_JPY −19.0p < 21.4p / AUD_USD −20.5p < 25.0p) を転記。**09-13 は改定後 1 件目の不成立として既カウント** → 次の qualifying 不成立 1 件で「執行モダリティ R1 再審」発動 → 骨子 DRAFT (打ち切り +15 分 / drift +8.0p の変更候補と estimand 影響表) を 09-27 前に用意。分岐: fill → F2 resolve + 変換係数 N=1 / ABANDONED_* → R1 再審起案 / NO-QUALIFY → 10-04 繰越 (分母外)。11-01 DST 打ち切り時刻の R3 再導出を 10-25 まで | record-only + R3 文書 / Claude、R1 再審承認は user | 転記 09-24 / 骨子 DRAFT 09-26 / REG `weekend-gap-execution-amendment-g0prime` 09-28 | 二値: fill → 有限化後の経路 A (wg L1、NAV ≥¥300k) 生存 / 不成立 → 第 2 セル候補消失 | P_A Rank 6 keep / P_C Rank 6 keep (訂正: (1−p)² → (1−p)、期限 09-27 前) / P_B Action 6「0/7 累計」は改定前後混在で reclassify |
| **7** | **storm guard 4 点** (`OandaBridge.modify_sl` / `modify_sl_sync` `modules/oanda_bridge.py:963–1008`、4 点いずれも不在を code 確認): 累積 tx breaker → 冪等 (同値再送 skip) → 単調性 (BUY で SL 下げ禁止) → 1-pip dead-band。log-only 検知器を先に入れ、counterfactual pin (各 guard kill で storm fixture が通る) を同一 commit、CF 前に pycache purge。wg 凍結値 (card L42) に触れないことを PR で明示、修正後は Rule 2 監視。**巡目上限 ≤6 (P2)、market-safe 窓でマージ (§3.2)。容量スリップ時は検知器のみ着地し guard 本体は 90 日へ**。「1 tail ¥1,500 = 11.1%」は disaster SL 150p の尾、storm の尾は不利側自己約定 (直接 PnL ¥0 実績) — 別物 | R3 (構造バグ、live 経路 PR-1) / Claude | 10-10〜10-20 | 効かない (PnL 0)。floor 尾の保護のみ | 3 提案 keep (6/6)。語法訂正のみ |
| **8** | **研究側の期日消化 (件数・手続きのみ)**: (i) rnb ckpt-1 (REG `rnb-shadow-lane-health-checkpoint-1` 09-24) TRIGGERED 時 lane-health 調査 — **件数のみ、WR/EV 不接触**、09-10 conf 単位バグ再発型を最初に疑う / (ii) E23 P1×3「park 根拠の estimand 監査」(REG `review-backlog-253-257-digest` 10-03) — Gate A 再計算は pass-1 測定可能性メトリクスの範囲に限定し OOS 窓に触れない、pass-2 は解錠しない、park は動かさない / (iii) **#29 S1 census は step 0 (license-free dense 凍結 stance モデルの候補・ライセンス・訓練標本 explore 窓重複調査) のみ**、結論は 10-18 を待たず臨時スキャン記録 (C1–C6、候補ゼロでも可) として置く (REG `edge-supply-scan-monthly` WIP 規則)。ABG 辞書 (NH=0 279/327) での census は走らせない | R3 / Claude | rnb 09-26 / E23 10-03 / census step 0 即時 (〜10-03) | 効かない (F1 分子分母に入らない) | 3 提案 keep。訂正: #29 時期 (即時) / E23 の P-10 境界 |

### 2.2 90 日側へ parking した項目と理由

memo §4.1 の 17 項目 → 上表 8 項目への対応と、落とした項目の行き先。parking の判断軸は time-to-M2 寄与 (全 17 項目でゼロ、memo §3) ではなく **(a) kill-condition 順 (F4 → F2 → F1) / (b) 決裁の前提材料か / (c) live 経路 single-writer の直列容量** (G4 §5.4)。

| memo §4.1 # | 項目 | 行き先 | parking 理由 / 再浮上条件 |
|---|---|---|---|
| 1 | 統合決裁パケット | **Rank 1** | — |
| 2 | storm guard 4 点 (live PR-1) | **Rank 7** | — |
| 3 | `tools/broker_ledger_reconcile.py` (汎用 reconcile tool) | **90 日**。D5 入力は Rank 5(b) の one-off GET 14 本で足りる | 汎用 tool は #273 型欠陥族 (fetch/完全性の窓) そのもので 27 波 (G4 §5.2 需要 1〜3 セッション)。再浮上 = 突合対象が 14 本を超えて定常化したとき |
| 4 | `EXEC_CONTRACT[entry_type]` log-only 検知器 (live PR-2) | **90 日** | F2 帰結 (12-31) と同時期で足りる。live 経路 single-writer で PR-1 (storm guard = floor の tail) が先。12 type の契約表を KB から起こす需要 1.5〜2.5 セッション。**bypass set 衛生** (vix demoted / sweep retired が set に残存) は同 PR で扱うのが自然なので同時期 |
| 5 | F4 推定器修正 + keeper 計装露出 (live PR-3) | **Rank 3(i)** (30 日に復帰) | P_A の「90 日へ」は両レンズ refuted (fit writer が読み手) |
| 6 | wg G0' 記録・分岐 | **Rank 6** | — |
| 7 | E1 first look §8 執行 | **Rank 2** (export tool + 手順書) + 10-15 固定日 | — |
| 8 | #29 S1 census | **Rank 8(iii)** step 0 のみ | 全 census は ABG 辞書疎性で走らせない |
| 9 | E23 P1×3 estimand 監査 | **Rank 8(ii)** | — |
| 10 | readout 欠落修復 (m1 monitor KB 日次記録 / `/api/demo/stats` 厳格性 pin / attribution gross-net 併記 / engine_tick 転記) | **Rank 3(iii) の M3b ラベル + B 行再ラベルのみ 30 日、残りは 90 日** | 決裁の前提材料でない。再浮上 = パケット確定 (10-08) 後の空き容量 |
| 11 | 時計台帳 v0 (live 経路欠陥の混入日 / 発見日 / 失われた qualifying event 数) | **90 日** | record-only、決裁前提材料でない。Tier A cron 配線は monitoring 経路 = review gate 対象で巡目コスト高 |
| 12 | venue 変更 feasibility (記述級) | **90 日、ただし U3(ii) 縮退の可逆性材料は 11-15 までにパケット追補として前倒し可** | 決裁は F1 (2027-02-05) 後。前倒し可の範囲 = V2「新規口座開設後は翌月末までゴールド」の既存会員追加口座への適用可否 (unverifiable、user 一次確認) + 口座切替 code 影響 (`OANDA_ACCOUNT_ID` / `restore_mappings` / trade_id 名前空間、記述級) — P_B Action 5 両レンズ keep |
| 13 | Gold 10 月判定 | **UD1 (user、09-23 即日)** | 画面確認は user のみ可 |
| 14 | Turtle S2 D1 shadow readout | **90 日、「N/PF/OOS PF 確認」ではなく Render cron `fx-ai-turtle-s2-d1` の liveness 確認に読み替え** | N=0 は BT 基準で 30% 程度は自然、readout は書けない。liveness 確認は UD2 (workspace 選択) が前提 |
| 15 | CME capture に ZQ=F / SR3=F | **90 日** | web 再起動を伴う種まき = deploy churn 源 (§4)。t2m2 効果ゼロ、E12 first look 2027-02-05 まで急がない |
| 16 | daily market review 30d 有効性レビュー | 固定日 (REG `daily-market-review-30d-effectiveness` 10-14、record-only) | triage 対象外 (登録済み期日) |
| 17 | 第 6 次スキャン | 固定日 (REG `edge-supply-scan-monthly` 10-18) | triage 対象外。Rank 8(iii) の臨時スキャン記録を持ち込む |

**parking の共通ルール**: 90 日側の項目は着手しない (「無料」並行の禁止、§5)。再浮上は 10-06 中間チェックか 10-22 スプリント終了レビューでのみ判定し、その時点の供給 (実測セッション数 × 実測税率) を根拠に書く。

---

## 3. PR 規律 (ペースアップの実体 — 欠陥税を巡目構造で下げる)

観測値 (G4 §2.1・§5.1、09-18〜22): 人手 commit 62 件中 review-fix 48 件 (77.4%) / code PR の巡目 2 (#275) / 5 (#267, #276) / 12 (#272) / 14 (#270) / 27 (#273)、中央値 ≈ 8.5 / 1 巡 ≈ 15 分 (Claude 修正 + CI 4.5 分 + connector 往復) / #273 は 58 commit ≈ 4.4 時間の CI 待ちのみ。09-19 triage 19/19 が実欠陥で **誤検知 0** ([[pr-review-gate-inline-blindness-2026-09-18]])。⇒ 税は「ノイズ」ではなく「上限のない真陽性」。したがって **上限は P2 に限定し、P1 は上限の対象外**。

### 3.1 起票時の巡目上限宣言

1. **PR body に固定見出し「レビュー巡目上限」を置き、起票時に宣言する**: `P2 ≤6 巡 / P1 は例外なく修正 (上限対象外)`。上限は PR ごとに下げてよいが上げない。
2. **P1 (正しさ・estimand・live 経路・monitoring に触る欠陥) は巡目に関係なく全件修正**。P1 を「上限超過」で繰延しない (CLAUDE.md マージゲート節、09-19 triage で 19/19 実欠陥)。
3. **上限到達後に残った P2** は registry に **estimand 注記付きで繰延** し、PR body と最終 commit message に「未修正 P2: N 件 (registry id)」と明記する。「ゲート通過」「クリーン」とは書かない (REG `review-backlog-272-273-continuation` message: 最終巡でも毎回 1〜2 件の新規 P2 が出続ける)。
4. 修正 push 後は再レビューが自動で走らない — `gh pr comment <N> --body "@codex review"` を先に実行してから `tools/pr_review_gate.py <N>` を再実行する ([[pr-review-gate-2026-09-08]] §5c)。
5. **本文書以降に起票する全 code PR に適用**。docs/KB のみの PR は connector レビューの対象だが、巡目上限宣言は任意 (P1 が出れば同様に修正)。

### 3.2 マージバッチと market-safe 窓

| 種別 | 規律 | 根拠 |
|---|---|---|
| code PR (tools / tests / modules / registry .json = デプロイあり) | **1 日 1 バッチ**。並行 PR は直列にマージし、バッチの前後で `main == origin/main` を確認 | 09-22 は 2.5h で instance restart ×4 (03:33:38 Render restart + deploy 03:56 #272 / 04:09 #273 / 06:01 #276、facts §H) = in-memory 状態 reset ×4 (velocity ガード `_price_history` 空 → fail-open 窓、REASSESS §8) |
| 避ける窓 (a) | **open live trade がある時** (`/api/demo/status` および OANDA `open_trade_count` が 0 であることをマージ直前に確認) | deploy 再起動で OandaBridge / SL-TP 監視 / `_price_history` が reset される |
| 避ける窓 (b) | **日曜 20:00–22:30Z (wg event 窓)**。OANDA 実開場 21:04–21:05Z 前後の G0' 手順 (REG `weekend-gap-execution-amendment-g0prime`: 送信時刻 = 開場 +0〜2 分、poll ≤60s) を deploy 再起動で潰さない | F2 (`project-falsification-f2-wg-live-conversion` 12-31) の分子は 1 fill で決まる二値イベント (Rank 6) |
| docs/KB のみ (`knowledge-base/wiki/{decisions,analyses,strategies,research,learning}/**.md` = `render.yaml:39–53` ignoredPaths でデプロイなし) | CI green で即マージ可 (CLAUDE.md コードレビュー節どおり)。ただし `knowledge-base/wiki/decisions/*.json` (registry) はデプロイありなので code PR 扱い | — |
| マージ手順 | CI green → (code PR は) `tools/pr_review_gate.py <N>` + inline thread 直読み → `gh pr merge <N> --merge --admin` を単独コマンド形で (CLAUDE.md 自走原則) | — |

### 3.3 並行 PR の分離

- **必ず自分専用 worktree** (`.worktrees/<slug>`、`git worktree add ... origin/main`)。main checkout 直下のファイルは編集しない (scheduled task がローカル checkout で走る構造は恒久、MEMORY `project_scheduled_tasks_run_stale_local_main`)。
- **hot file 不接触**: `knowledge-base/wiki/index.md` / `log.md` / `changelog.md` / `CHANGELOG.md` / `sessions/*` / `audit-index.md` / `render.yaml` / `app.py` / `scripts/anomaly_watcher.py` / `modules/freshness_policy.py` / `tools/daily_report*` / `knowledge-base/raw/trade-logs/*`。これらに触る変更は 1 セッションが所有し、他は返り値 (needs_orchestrator) で依頼する。
- **REG (`prereg-trigger-registry.json`) は 1 セッションのみ編集可**。他セッションは追加したい entry を返り値に書く (並行編集は union 解決不能な JSON conflict を作る)。
- **post-commit 末尾差分** (REG `kb-session-log-postcommit-trailing-edit` 10-13): `scripts/hooks/git-post-commit.sh` がコミット後に session log へ追記するため、worktree に必ず 1 本の未コミット差分が残る。**PR に含めない** (worktree 側で `git checkout -- knowledge-base/wiki/sessions/` で戻す)。恒久修理は Rank 4(iii)「先に塞ぐ」。

### 3.4 commit・検証の衛生 (既存 lesson の再掲、規律として固定)

- foreground commit + 明示 timeout + `git -C <絶対パス>`。成否は `git log -1 --format='%h %s'` と `git status --porcelain` で検証 (exit 0 は嘘をつく、MEMORY `feedback_commit_exit0_lies_autosaver_bypasses_precommit`)。`--no-verify` 禁止。
- code を触ったら `PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest tests/ -x -q` + `python3 scripts/check.py` を worktree 内で実行 (stale bytecode 事故防止で `-B` 必須、MEMORY `feedback_pycache_prefix_stale_bytecode_verification`)。counterfactual pin の前に pycache purge。
- 一括置換はファイルでなく行にスコープ ([[lesson-unscoped-global-replace-2026-09-18]])。片側を塞いだら対称な反対側を同じ PR で確認 ([[lesson-symmetric-side-check-2026-09-19]])。

---

## 4. 09-22 本番 HTTP 全断 (00:15→03:35Z、3h20m) の記録 — root cause UNKNOWN

2026-09-22、`https://fx-ai-trader.onrender.com` への全 HTTP 要求が **00:15:43Z (最初の 499) → 03:35:55Z (最初の 200)** の 3 時間 20 分、応答しなかった (Render request log 実読: 直前の最終 200 は 00:03:10Z の `/api/demo/trades?...status=closed` 2.8 MB / 1.3 s、edge-cell-watchdog; その間に deploy 00:04:04 (auto: rate anchor daily ingest) と 00:12:50→00:14:47 (data(mof-statements): daily collect) が走り、新 instance は gunicorn 00:14:32 / worker 00:14:46 / MainLoop 00:14:51 で起動したが、その boot から HTTP は一度も答えていない)。**engine は生存**していた — MainLoop tick は 02:40Z (tick #140) と 02:58–03:33Z (tick #290–#340) に直接観測され、tick 計数は 00:14 起動から連続稼働と整合する (00:14–02:40 は tick 計数からの推定、直接証拠は 02:40 以降)。03:33:38Z に Render が instance を restart (deploy ではない; `render.yaml` に healthCheckPath なし = TCP-only なので HTTP health-check 起因の restart ではなく、原因は別 background セッションで調査中)、03:35:55Z に最初の 200。その後 deploy による restart が 03:56 (#272) / 04:09 (#273) / 06:01 (#276)。**root cause は UNKNOWN** — 仮説 H1 (03:00Z H1 バー close の HourlyEngine + C1 `evaluated_candidates` 書込みによる SQLite write-lock 競合) / H2 (gunicorn 1 worker × 8 gthreads の pool 枯渇: 15s で放棄された要求がスレッドを塞ぎ続ける) / H3 (Render edge) はいずれも Render request log / app log を対話セッションで読まないと判別できない (UD2)。同型の疑い: 09-15 03:39–03:49Z の 499 burst → 03:49:54 instance restart / 09-21 03:14Z の 502 1 件。3 例とも直前に deploy 発生 commit があるが、**「deploy 直後 HTTP hang」は N=3 の仮説**であり、再現率の点推定 (「2/7 日」等、N=2 で Wilson 4–40%) は引用しない。

帰結: (1) **daily report `knowledge-base/raw/trade-logs/2026-09-22-pre_tokyo.md:63` の「Render側のコールドスタート（無料tier特有のスリープ）」という帰属は無効** — 本番は Render Pro (CLAUDE.md L80「本番: … (Render Pro, auto-deploy from main)」) でスリープは存在せず、report は 0 データで原因を書いた (本文書はファイルを編集せず、この 1 段落で無効化を宣言する; 恒久対策は Rank 4(v) NO-DATA スタブ + analyst prompt へのホスティング事実注入)。(2) `tools/nav_floor_projection.py --append` writer が 03:13Z に失敗 → `data/monitoring/nav_floor_projection.csv` の 09-22 行欠落 (09-20 の欠行は日曜 = `.github/workflows/daily-report.yml:6` cron `1-5` 仕様で別原因)。F4 の読み手は fit で、欠行は発火日を数日動かす (Rank 3(i))。(3) 外部読み手 (Tier C anomaly 15 分 cron / edge-cell-watchdog / daily report / nav_floor writer) は 3h20m のあいだ「engine 死亡」と「HTTP 盲目」を区別できず、いずれも service を回復させる escalation をしなかった — MEMORY `project_monitoring_blind_during_outage_2026_08_30` の教訓の再発形。(4) 夜間 deploy 源は **≥3/日** (00:04 rate anchor: `data/external` + `data/cache/yield/ZN_F_1h.parquet` / 00:12 mof: `data/external` / ~03:1xZ nav_floor CSV: `data/monitoring`) で、`render.yaml:39–53` の ignoredPaths はいずれも cover しない = [[deploy-churn-trading-gap-2026-08-21]] の残余。対策は Rank 4(vi) (`data/external/**` + `data/monitoring/**` のみ、`data/cache/**` は禁止 §5)。「盲目は 33 分」(facts §H 初版) は §H2 で 3h20m に superseded、引用禁止。

---

## 5. やめること (REASSESS §6 の引用規律としての転記)

以下は本スプリント中の全記録 (KB / PR body / daily report / registry message / MEMORY) に適用する。違反を見つけたら書いた側を直す (元記録が凍結文書なら注記で無効化)。

**引用・記述の禁止**
- 「carry_dip は demo +103.0p / broker −41.1p で符号逆」— 母集団不一致。正: 突合 7 本は両方負 (demo −16.4 / broker −41.1)、正符号は未突合 3 本 +130.9p が担う。14/14 の結論ではない。
- 「F4 は 12-03 に発火」を確定事実として。読み手は fit、発火は 12-04〜01-08 の幅、keeper のみなら F2 の後。kill 順序は「10-01 Gold → 10-15 E1 → 11-30 U3 → {F4 12-04〜01-08, F2 12-31} → 02-05 F1 → 03-04〜04-07 floor → 03-31 F3/global-stop」と書く。
- 「無回答 = 12-03〜05 F4 強制起票」を既定挙動として (現行 writer では来ない)。
- 「0.2x は live 送信のどこにも乗算されていない」— 正: 乗算後に固定 lot / floor 1000u で無効化、L1 では edge-cell 経路で binding。
- 「D3 (4.2 多 leg) は template 既決」— 未裁定、user 項目。
- 「keeper=0 なら wg L3 で 1.086%」等、rung が 4.2 違反となる NAV を分母にした %。
- 「M3b return +0.099%/月」を M2 進捗として (winner-selected、keeper 非含)。
- 「入金 = M2 加速」も「入金 = 生存のみ」も — 「clock には効かない、必要 gross% は圧縮」に限定。
- 「実測 2.1/月 では 3 本」— wg 頻度は N=4、Poisson 95% CI 0.57〜5.37/月で設計 3.28 と区別不能。点推定 2 つを CI 付きで併記。
- 「API 生存余裕 ¥1,037〜−¥1,566」を自前バッファ (¥262k) 基準と明記せずに。OANDA 条件は残高 ≥¥250k。
- 「30 日の需要 > 供給は算数で不可能」— 供給は [10.5, 19]、正は「17 項目 + registry 15 件 + 継続レビュー全部は不可 = triage 必須」。
- 「夜間 deploy 2 回/日」→ ≥3 回/日。「再現率 2/7 日」の点推定引用 (N=2、Wilson 4–40%)。「09-22 の盲目は 33 分」(3h20m に superseded)。
- 「velocity_down 4 = 4 バー」の断定 / 「carry_dip drought = 設計衝突」の断定 (11 日ゼロは Poisson P = 0.045〜0.16 で異常でない、機構は仮説)。
- 「clean N はゼロ速度」を限定なしで (正: 契約準拠 N に限定、生の clean N は 2.1/週)。「carry_dip は agg_kelly で block」(card L3 訂正対象)。
- memo L107「~5 セッション」/ L61・L170「N≥30 が 2027-Q1〜Q2」を N 基準なしで。
- 「keeper cap 0.5p は観測ゼロだから無効」→ 構造根拠 (プロコース USD/JPY 0.8 銭 原則固定) で。
- (継続) nav_floor fit 現況値 / L1 5000u 前提の M2 寄与 / keeper 控除前 M2 算数 / P5 40–50% / falsified family の再試行 / 凍結 look の outcome 計算。

**作業の禁止**
- `data/cache/**` を ignoredPaths に追加すること (CI pin + runtime read)。08-14 以降の Render ログに依存する計画 (retention で不在)。
- broker realized のみで REG `carry-dip-v3-revival-watch` の R2 を autopilot 執行すること (凍結 estimand = demo `pnl_pips` の差し替え)。
- F4 推定器修正を 90 日へ外すこと / fit 窓の延長で直そうとすること (窓は既に 2 サイクル超)。
- 巡目上限なしのレビュー消化、P1 を上限超過で繰延すること、市場時間中 (open live trade あり) の code PR マージ、tools/文書 PR の「無料」並行、日曜 20:00–22:30Z のマージ (§3)。
- daily report が全 API 失敗時に原因を書くこと。0 データで原因を KB に永続化すること (§4)。
- limit=1 snapshots での E1 export 試走 (生 skew 値閲覧)。export を 2 回以上実行すること。C3 combo を #20 composite に登録すること。
- ABG 辞書での #29 census 実行。Turtle S2 を N=0 で「N/PF/OOS PF 確認」として計上すること。
- user 手動売買を system 口座で行う案 (keeper flat ガード常時 skip、M2 帰属不能)。keeper 設計値 (cap / 窓 / units / RT / 銘柄 / target) の変更提案 (効果上限 ¥260/月)。
- **autopilot 禁止 (user または R1)**: carry_dip SL 150p 復元 / velocity_down 免除 / ps_aud_jpy 降格 (09-30 regate 委任) / kalman 契約変更 / M2 estimand 変更 / 0.2x 再基準化 (env・kv) / floor バッファ ¥12,000 縮小 (F4 凍結トリガ + 3 定数) / wg disaster SL 137p・rung 4000u (LOCKED 凍結値) / G3 N≥30・Wilson gate 緩和 (07-10 D-d / 08-05 template の撤回、ruin 63% 教訓と衝突) / keeper on-off / U3 前の live セル追加・lot↑。

---

## 6. チェックポイント

| 日付 | 内容 | 判定基準 |
|---|---|---|
| 09-23 | 本文書 (Rank 4 (i)(iii)(iv)) 着地 / UD1・UD2 を user に 1 行で依頼 | — |
| 10-06 | Rank 4 中間チェック | 8 項目の done / in-flight / not-started を証拠付きで判定 (G4 §1 と同形式)。起票した code PR の巡目実測 (中央値、P2 上限超過回数、繰延 P2 件数) と market-safe 窓違反 0 件。90 日側から再浮上させる項目があれば供給実測を根拠に |
| 10-22 | スプリント終了レビュー | 同上 + 次 30 日 triage (REASSESS §3 形式で再評価、両レンズ反証つき)。巡目中央値が 8.5 から下がらなければ §3.1 の上限値 (≤6) 自体を見直す — 品質規律ではなく容量規律の側を動かす |

registry への追加希望 (本 PR では REG を編集しない、orchestrator 経由): `sprint-0922-triage-midcheck` (10-06、条件 = 8 項目の done 判定 + 巡目実測を KB 記録) / `sprint-0922-triage-close` (10-22、条件 = 終了レビュー + 次 30 日 triage 文書)。

---

## 7. 出所索引

| 主張 | 出所 |
|---|---|
| 8 項目表・parking 一覧・やめること | [[path-to-win-reassessment-2026-09-22]] §3 L61–L76 / §5 L94–L104 / §6 L106–L138 |
| 17 項目の原本 | [[path-to-win-decision-memo-2026-09-20]] §4.1 L105–L128 |
| 供給 [10.5, 19] / 需要 15〜21.5 / 巡目中央値 8.5 / 税率 77.4% (48/62) / live PR 3 本 4〜6 セッション | G4 §2.1・§5.1–§5.4 (REASSESS §1 L43 に集約) |
| 09-22 HTTP 全断の時刻列 | facts §H・§H2 (Render request log / app log 実読、06:40Z・06:45Z 再クエリ) |
| daily report 誤帰属 | `knowledge-base/raw/trade-logs/2026-09-22-pre_tokyo.md:63` |
| Render Pro | `CLAUDE.md:80` |
| cron 平日限定 | `.github/workflows/daily-report.yml:6` |
| ignoredPaths 現行 | `render.yaml:39–53` |
| `data/cache/**` 禁止の根拠 | `tests/test_render_build_filter.py:29–35,94–101` / `modules/yield_data.py:23,43` |
| wg 送信時刻規定 | REG `weekend-gap-execution-amendment-g0prime` message (2) |
| post-commit 末尾差分 | REG `kb-session-log-postcommit-trailing-edit` / `scripts/hooks/git-post-commit.sh` |
| レビュー真陽性 19/19 | [[pr-review-gate-inline-blindness-2026-09-18]] |
| user 決裁の履歴 (U1) | [[u1-mission-redecision-2026-09-17]] |
| 残 user 決裁 (U2/U3/U5) | [[process-meta-audit-2026-09-07]] |
| lot ladder / 4.2 | [[lot-ladder-template-2026-08]] L65, L73, L79, L167 |
| keeper | [[status-volume-keeper-2026-09-01]] / [[live-frequency-and-oanda-status-survival-2026-09-01]] |
