# 30 日スプリント (2026-09-22〜10-22) 終了レビュー + 次 30 日 triage — 2026-10-21 (autopilot、rule:R3 文書のみ)

作成規律: 文書のみ (R3、code 変更なし、価格データ・DB 計算ゼロ、凍結 look の outcome 非接触)。registry `sprint-0922-triage-close` (期日 10-22) の条件 = (1) 8 項目の done / in-flight / parked、(2) 巡目実測 (中央値・P2 上限超過回数・繰延 P2 消化率)、(3) market-safe 窓違反件数、(4) 次 30 日 triage (REASSESS §3 形式、両レンズ反証つき)。数字は出所併記、新しい数字は作らない。引用禁止値 ([[sprint-triage-pr-discipline-2026-09-22]] §5) は書かない。Live = `oanda_trade_id != ''` のみ。

略号: SPRINT = [[sprint-triage-pr-discipline-2026-09-22]]、REASSESS = [[path-to-win-reassessment-2026-09-22]]、REG = `knowledge-base/wiki/decisions/prereg-trigger-registry.json`、MID = REG `sprint-0922-midpoint-check` (resolved 10-05)。集計 = PR #280〜#341 (62 本、全て merged、GitHub API `issues/{n}/comments` / `pulls/{n}/comments` / `pulls/{n}/reviews`、2026-10-21 03:4xZ 取得; 中間ファイル scratchpad `pr_rounds.jsonl` はリポジトリ非保存)。

---

## 0. TL;DR

- **8 項目 = done 5 / partial 3 / parked 0**。partial 3 (Rank 3 / 4 / 5) はいずれも「主目的は着地、付属のツール化 (M3b ラベル tool 反映 / NO-DATA スタブ / engine-tick endpoint / block 台帳 readout) が未着手」で、決裁の前提材料は全て揃った (§1)。
- **巡目 (`@codex review` 依頼回数) 中央値: code PR 7 (n=31) / docs 1 (n=31) / 全体 5** — 09-18〜22 基準 8.5 から**低下** ⇒ SPRINT §6 の条件「下がらなければ上限値を見直す」は不成立、**§3.1 の上限 (P2 ≤6) は据え置き**。ただし上限超過は code 18/31 (58%)、P1 は 75 件 (全件修正、繰延 0)、P2 271 件 (§2)。
- **繰延 P2 消化率 = 起票時 9/9 (100%)、以後の繰延も未消化 0** (§2.3)。
- **market-safe 窓違反 1 件** (10-16 PR #333 を open trade #1254229 ありでマージ、遡及記録)。10-19 以降の code マージ 4 本は open 0 で遵守。新型の穴 = **deploy 直後 (2 分) の新規 LIVE 送信**が執行窓を塞いだ (10-20、未決 17) — 規律は「merge 時 open 0」しか見ていない (§3)。
- 次 30 日 (10-22〜11-21) は **8 項目** (§4)。time-to-M2 への効果は前スプリント同様「∞→有限の可能化」に限られ、Claude 単独で動く分子は 0 — 30 日の中身は **(a) 執行待ちの live 保護 1 本 (storm guard enforce = user の 1 操作)、(b) 固定日の verdict 3 本 (D11 ≒10-25 / E1 11-05・11-12 / 第 7 次 11-17)、(c) 読み手欠陥の R3 2 本 (DD ledger 非計上 / family A 根 + 2-writer)、(d) プロセス欠陥の user 上程 2 本 (wiki-daily 欠落・座礁 main / deploy 直後 fill)** に絞る。
- **9 月 22 日決裁の文言「勝てるまで」の 30 日の実績** (REASSESS §0 の (c)+(b)): (c) 測定可能状態 = 統合パケット v1.0 ✓ + D11 両基準 ✓ + E1 凍結 ✓ (POSTPONE) / (b) kill 検知器是正 = F4 分解 ✓ / F3 両基準 ✓。(a) M2 到達は依然 user 決裁 (U3 ∧ D1) 待ち — 30 日で動かせない構造は不変。

---

## 1. 8 項目の判定 (証拠付き、MID 10-05 の続き)

判定基準: done = SPRINT §2.1 の文言どおり main にマージ済み / partial = 主目的は着地したが文言内の sub-item が未着手 / parked = 着手せず 90 日側へ。証拠は PR 番号 + ファイル (worktree origin/main 2026-10-21 読み)。

| Rank | 施策 | 判定 | 証拠 (done 分) | 未着手 sub-item と行き先 |
|---|---|---|---|---|
| 1 | 統合決裁パケット | **done** | v0.6 #279 (09-22) → **確定版 v1.0 #317 (10-07)** `decisions/integrated-decision-packet-d1-d12-2026-09-22.md` L1/L4、UD1 結果 = GOLD (09-23、L227) | user 返答 11-30 (REG `integrated-decision-packet-d1-d12-user-response` 11-29)。Claude 側残なし |
| 2 | E1 凍結 export tool + 手順書 + cutoff #2 + (a-1) 一行定義 | **done** | `tools/e1_positioning_frozen_export.py` (#286) / `decisions/e1-first-look-runbook-2026-09-22.md` L127 (cutoff #2 12-30)、L135 (§8 (a-1) 一行定義) / 凍結 export 実行 #321 (10-09) / **first look #1 = POSTPONE** #323 (10-10、coverage 88.6% < 90%、統計未計算) → cutoff 11-05 / verdict 11-12 | 固定日 2 本 (REG `e1-first-look-postponed-freeze-due` 11-05 / `e1-prereg-verdict-deadline` 11-11) |
| 3 | kill 検知器の estimand 是正 | **partial** | (i) F4 分解 #285 + TRANSFER_FUNDS 調整 #295、CSV 毎日 (MID (iii) ✓) / (ii) **F3 両基準併記 #338 (10-20)** `tools/m1_clean_live_monitor.py --strong` broker 列 + `/api/oanda/trades_remote`、616 件被覆 | (iii) M3b「winner-selected 診断」ラベル: KB (`analyses/m1-kpi-readout-and-mechanical-flip-2026-09-04.md` L253 / REASSESS) にはあるが `tools/m1_clean_live_monitor.py` L854–871 の M3b 出力 `definition` には未反映 → 次 30 日 (R3、tools 1 行 + pin) |
| 4 | 容量規律 + インシデント記録 + deploy churn 遮断 | **partial** | (i)(iii)(iv) SPRINT 文書 #280 / (ii) §3.2 窓 (§3 で実績) / (vi) `render.yaml` ignoredPaths に `data/external/{cb_statements,rate_anchor,mof_statements}/**` + `data/monitoring/**` + `wiki/research/**` (#297、L89/L100/L101/L118/L131) — 0 時台 deploy は 09-25 以降 0 (MID (v)) | (v) daily report **NO-DATA スタブ未実装** (全 API 失敗時も `run_analyst` を呼ぶ、`scripts/daily_report.py` L1273–1297; ホスティング事実の注入 L235/L266/L314 は実装済み = 誤帰属の再発防止は半分着地) / (vii) **DB 非接触 engine-tick endpoint 未実装** (`/healthz` L13682 は `get_status()` + `request_tick()`、`/healthz/http` は意図的に DB 接触; per-request latency log は `[API-SLOW]` >2.0 s のみ L185–194) → 両方 90 日側 (優先度低: 09-22 型 HTTP 盲目は 10 月に再発 0、[[http-blind-fork-poisoning-2026-09-22]] の根因修理 #277 以降) |
| 5 | carry_dip: card L3 訂正 + 14 本 reconcile + block 理由確認 + readout tool | **partial** | (a) card L3 訂正 + (b) 14/14 突合 #282 (09-22)、以後 29/29 突合継続 ([[usdjpy_carry_dip_accumulator]] 10-20 節) / R2 predicate 不成立 (demo N 29 EV +5.50 / broker +4.79p、両正) | (c) 「≈5 シグナルの block 理由確認」はカード Status 行 L3 の 1 文 (`velocity_down` 4 / `same_price_3pip` 1 / AGG_KELLY 0、qualifying H1 bar 2 本とも 38–57p 急落中 — 帰属確定ではない) のみで § 化なし / (d) block 台帳 readout tool **未実装** (`/api/demo/block-counts` 消費は ps-seat readout #339 で手動) → (c) は D5 材料として足りる (user 決裁 11-30)、(d) は 90 日側 |
| 6 | wg G0' 記録 + event #3 分岐事前固定 | **done** | card 転記 #281 / 骨子 DRAFT #289 / **event #2 (09-27) ABANDONED_DRIFT → 2 連続不成立 → packet §6 発動 → R1 再審 packet v1 #304** (user 決裁 W1〜W6、REG `wg-execution-modality-r1-packet-v1-w1-decision` 10-04 **未決・契約 B 継続**) | user 専権。Claude 側 = `wg-dst-cutoff-basis-r3` (10-25) + `weekend-gap-live-g1-slippage` (10-31) |
| 7 | storm guard 4 点 | **done** (判断まで) / 執行は user 待ち | 4 点 (breaker / 冪等 / 単調性 / dead-band) #287 (09-22、`modules/oanda_bridge.py` L64–69、L1233–1288)、繰延 P2 消化 #314、**読み手配線 + ENABLE 判断 #337 (10-19)**、検知のみ epoch で storm 3 波 / 4 建玉 (488 / 15 / 269 / 46,091) 全数捕捉・偽陽性 0 ([[storm-guard-design-2026-09-22]] §7) | **env `STORM_GUARD_ENFORCE=1` 未設定** — 執行窓は 10-20 07:11Z〜10-21 03:27Z (≥20 h) 開いていたが classifier [Production Deploy] 拒否 2 回 = user の 1 操作待ち (REG `storm-guard-enforce-execution-window` 10-22)。「容量スリップ時は検知器のみ着地」の分岐には入らなかった (guard 本体は着地済み) |
| 8 | 研究側の期日消化 | **done** | (i) rnb ckpt-1 → lane-health precheck #283 + 真因修理 #290/#291、ckpt-2 通過 #321 / (ii) E23 P1×3 estimand 監査 #309 / (iii) #29 step 0 #284 → **第 6 次スキャン #341 (10-20、採用 0、#29 step 1 census 承認)** | 第 7 次 = REG `edge-supply-scan-monthly` 11-17、#29 census gate `adhoc-scan-29-step1-census-gate` 11-07 |

90 日側 parking (SPRINT §2.2) の再浮上: なし。再浮上条件 (供給実測) は §2.4 の需要超過で成立しない。bypass set 衛生 (vix demoted / sweep retired の残存) は EXEC_CONTRACT 検知器と同時期のまま。

---

## 2. 巡目実測 (PR #280〜#341、62 本)

### 2.1 計数定義
- **巡目 = issue comment に `@codex review` を含む件数** (起票時の自動レビュー 1 回は含まない。SPRINT 起票日の計数と同じ定義、REG `sprint-0922-triage-close` message)。
- **inline P1/P2/P3 = `pulls/{n}/comments` の本文先頭 40 文字の Codex バッジ** (`![P1 Badge]` 形式、`**P1**` 形式は不使用)。inline 件数は author 返信を含む (530 件)。
- **code PR = title 接頭辞が docs(/kb:/research( でない、または docs 接頭辞でも非 `.md` / 非 KB ファイルを含むもの** (#288 / #302 / #304 / #318 / #321 / #323 の 6 本は docs 接頭辞だが registry JSON や tools を含むので code 側)。

### 2.2 結果

| 指標 | code PR (n=31) | docs-only (n=31) | 全体 (n=62) |
|---|---|---|---|
| 巡目 中央値 / 平均 / 範囲 | **7** / 7.03 / 1〜19 | 1 / 3.65 / 0〜16 | **5** (62 本の第 31・32 位がともに 5) |
| 巡目 >6 (上限超過) | **18 (58%)** (7×3 + 8×5 + 9×5 + 10×3 + 14 + 19) | 8 (7×4 + 8×3 + 16) | 26 (42%) |
| 分布 | 1, 3×5, 4×3, 5×3, 6, 7×3, 8×5, 9×5, 10×3, 14, 19 | 0, 1×15, 3×3, 4, 5, 6×2, 7×4, 8×3, 16 | — |
| inline P1 合計 | 56 | 19 | **75** |
| inline P2 合計 | — | — | **271** (P3 5) |
| P1 > 0 の PR | 17 本: #283(1) #286(9) #287(18) #289(2) #296(1) #299(12) #302(4) #304(8) #306(1) #308(1) #310(6) #312(2) #319(6) #321(1) #323(1) #338(1) #341(1) | | |
| 最多巡目 | #287 storm guard 19 / #299 (座礁救済 docs) 16 / #310 14 | | |

**判定**: SPRINT §6「巡目中央値が 8.5 から下がらなければ §3.1 の上限値 (≤6) 自体を見直す」— code 中央値 7 (全体 5) で**下がった** ⇒ 上限値は据え置き。ただし「下がった」の読み方に 2 つの注意: (i) 09-18〜22 の 8.5 は「巡目」(修正 push 回数) で、本集計は「依頼回数」 — 同一 PR で依頼 1 回 = 修正 push 1 回なので近似だが、起票時の自動レビューを含めない分だけ本集計が 1 小さい (比較は 7+1 = 8 vs 8.5 と読むのが保守的 = **ほぼ横ばい**)。(ii) P1 75 件は上限の対象外 (全件修正の規律) で、上限超過 18 本の多くは P1 消化で巡目が伸びたもの (#287 P1 18 / #299 P1 12 / #304 P1 8) — **上限を下げても P1 が減らない限り巡目は減らない**。⇒ 容量規律の改定は見送り、代わりに §4 で「起票時の P1 予防」(estimand 宣言を PR body 固定見出しに) を規律として追加提案する (R3、文書)。

### 2.3 繰延 P2 の消化率
- 起票時 (09-22 ウェーブ) 繰延 9 件 (REG `review-backlog-sprint0922-p2-deferrals` + sub-entry 0926 / 1003 / 1005 / 1007 + #284 4070489881) = **9/9 resolved** (#309 / #310 / #314 / #330 で消化、索引 entry も resolved)。
- スプリント中の新規繰延 (#273 → #326 消化 / #310 → #328 / #314 最終 HEAD → #318 / #317 → #318 / #326 → #339 / #328 → #339 / #302 → #305) = **全て resolved、未消化 0** (REG で active かつ `review-backlog-*` の entry は 2026-10-21 時点 0)。
- `review-ack` を「解決」として使った件数 0 (繰延は全て registry entry 付き)。**P1 の繰延 0**。

### 2.4 供給・需要の実測
- 期間 30 日で merged 62 本 (2.07 本/日)、うち autopilot (scheduled) 起点 ≈30 本、対話セッション起点 ≈32 本。SPRINT 想定の供給 [10.5, 19] セッション/30 日に対し、実セッション数は未計測 (session log 30 本 + 対話並行) — **供給の実測は本レビューでも出せない** (計測器なし)。需要側は registry 期日 (10-22 時点 active 11 本、うち user 専権 4) で読む。
- 10 月の **wiki-daily scheduled run 欠落 9 日** (10-20 trade-log 記載) と **座礁 main の救済 PR 8 本** (既往 7 本 = #299 / #301 / #312 / #315 / #332 / #335 / #336 + 本 run #342) は、供給の一部が「欠落の穴埋め」に消費されていることを示す (1 本 ≈ 0.5 セッション ⇒ 4 セッション ≈ 供給の 21〜38%、§4 #8) — 次 30 日の需要にこの固定費を計上する。

---

## 3. market-safe 窓 (SPRINT §3.2) の実績

| 日付 | PR | open live at merge | 判定 |
|---|---|---|---|
| 10-16 04:26Z | #333 (code: bt cache) | **1 (#1254229)** | **違反 1 件** — 2.4 h 後に storm #2 (269 送信) が同建玉で発生、guard 状態は deploy で消失していた (10-19 session log L25 の遡及記録) |
| 10-19 | #337 (code) | 0 (05:34:47Z、別セッション) | 遵守 — ただし deploy live 05:36:42Z の **14 秒後に #1346961 fill** (新プロセスの初 signal) |
| 10-20 | #339 / #338 / #341 (code) | 0 (07:11Z 窓) | 遵守 |
| 09-22〜10-15 | #284〜#331 | 記録上の違反なし (session log / log.md に §3.2 違反の記載 0) | — |

- **違反件数 1** (10-16)。再発防止は 10-19 run で明文化済み (「open 0 を確認してからマージ」を session log に時刻付きで残す)。
- **規律の穴 (新型)**: §3.2 (a) は merge 時点の open 0 しか見ないため、deploy 直後の新プロセスが 2 分以内に LIVE 送信すると (10-20 05:36:56Z) 執行窓 (env 変更 = 再起動) が翌日まで塞がれる。候補 3 つ ([[2026-10-20]] 未決 17: (a) deploy 後 N 分の LIVE 送信抑止 / (b) merge を signal 候補の bar 境界外に / (c) 執行窓条件を「open 0 ∧ 直近 signal なし」に) は **(a) が live 経路変更 (原則 1 に抵触し得る = user 決裁)、(c) は規律の文言変更のみ (R3)** — §4 #7 で (c) を採用提案、(a) は user 上程。
- 日曜 20:00–22:30Z (b) の違反 0 (期間中の日曜マージ 0)。

---

## 4. 次 30 日 (2026-10-22〜11-21) triage — REASSESS §3 形式、両レンズ反証つき

レンズ: **L1 = time-to-M2 / kill-condition 順** (∞→有限の可能化 / 有限化後に動かす / 効かない、REASSESS §3 の 3 択) / **L2 = 容量・前提条件** (直列容量 1 本の live 経路、deploy 窓、user 専権の切り分け)。反証 = 各項目を「やらない」側から読んで keep / reclassify / drop を書く。autopilot 禁止 (SPRINT §5) は不変。

| # | 施策 | Rule / owner | 期限 | L1 効果 | L2 反証 → 判定 |
|---|---|---|---|---|---|
| 1 | **storm guard enforce 執行 + first-storm readout** — user が (a) Render dashboard env / (b) MCP allow のどちらかを行う → autopilot が執行 (open 0 窓) → 最初の live trail で DB `sl` vs `confirmed_sl` 突合 (正当 tightening 喪失 0)。喪失 ≥1 / failed 急増で env 解除 (R2) | R2 執行 / user の 1 操作 | REG `storm-guard-enforce-execution-window` 毎日 +1 / readout = 執行日 +12 d | 効かない (PnL 0)。floor 尾の保護 + broker tx 46,091/建玉 の停止 | 「enforce なしでも実害 ¥0 なのだから急がない」 → **refuted**: 10-19 storm は BUY の SL を最大 51.7 pip 下げる送信を含み (族 B)、保護水準の劣化は実害。user 操作 1 回で済む最小コスト ⇒ keep (#1) |
| 2 | **family A の根 (LIVE 経路 `modify_sl_sync` 成功後の DB `sl` 未更新) + storm #3 の 2 writer (trail ⇄ BE) 特定** — R3 構造修理、live 経路 PR、巡目上限 ≤6 宣言、open 0 窓マージ。enforce 後も caller は毎 tick 再計算 → skip を続ける (CPU/ログ) | R3 / Claude | 11-14 (enforce 執行 + readout 後) | 効かない。制御系 | 「enforce が止めるなら根は直さなくてよい」 → **partially refuted**: guard は送信を止めるが writer の往復 (BE 引き戻し) は DB 側で続き、DB `sl` が broker と乖離したまま = readout の突合が毎回 fail する。順序は #1 → readout → #2 (readout が「正当 tightening 喪失」を出したら #2 の優先度が上がる) ⇒ keep、#1 の後 |
| 3 | **D11 user 決裁の窓 (carry_dip N 29/30、次 fill で閉じる ≒10-25) + F3 両基準 readout (N≥30 到達時に `--strong --json` を凍結記録)** — 基準選択は user、Claude は両基準を並記したまま到達を記録 | record-only / user (D11) | D11 窓 = 次 carry_dip fill / F3 readout = 到達日 | 有限化後の N 基準 (Δ≈2.7 ヶ月) | 「無回答なら REG 字義 (demo 簿) で凍結 = 何も起きない」 → keep (記録のみ、分岐は既定挙動で閉じる)。⚠️ N≥30 到達後の基準選択禁止 ([[d11-both-basis-m1-monitor-2026-10-19]]) |
| 4 | **E1 POSTPONE 分岐の固定日**: cutoff 11-05T06:33:31Z 凍結 (`--postponed` 再凍結、別複製・別 marker) → verdict 11-12 (判定器 11-06〜11-11) | R3 record-only / Claude | 11-05 / 11-12 | 効かない (E1 PASS 点推定 4%) | 「coverage 88.6% が 11-05 でも 90% に届かない」可能性 — ingest 停止 2 件 (08-21〜26 / 09-10〜14) は窓外へ出るので届く見込み。届かなければ手順書 §8-1 の固定分岐 (再 POSTPONE は 1 回まで) ⇒ keep |
| 5 | **wg: `wg-dst-cutoff-basis-r3` (10-25、前冬 Sunday 初バー ts の parquet 実測 + `first_bar_ts` 解決先) + `weekend-gap-live-g1-slippage` (10-31 roll) + W1 user 決裁 (10-04 超過、契約 B 継続)** | R3 / Claude、W1 は user | 10-25 / 10-31 | 二値 (wg L1 経路の生存) | 「DST 再導出は 11-01 まで不要」 → **refuted**: 11-01 の Sunday open が 22:00Z になるなら G0' 手順 (送信 = 開場 +0〜2 分) が 1 時間ずれて ABANDONED_HALT 決定論になる = 構造バグ ⇒ keep (10-25、価格系のみ) |
| 6 | **読み手欠陥 R3 ×2**: (a) DD ledger が `OANDA_SL_TP` 決済を計上しない (14 例、累積 155.0 pip、[[2026-10-20]] 発見 3) — risk ledger の計上経路を broker 決済まで広げるか、「ledger は SL_HIT 経路のみ」と注記して KPI から外すかの R3 文書 + 読み手 / (b) carry_dip 29 fill の exit 種別棚卸し (broker tx `reason` で TP / SL / BE / trail を分類、record-only、未決 18) | R3 / Claude (monitoring 経路 = Codex ゲート) | (a) 11-07 / (b) 10-31 | 効かない。ただし (a) は M1 KPI の読み手 (ledger を引用する文書が 155 pip 悪い側に偏る) | 「ledger は 0.2x 判定の入力ではない (dd_pct は KPI 除外済み)」 → (a) は **reclassify**: 修理ではなく「注記 + 引用禁止」の文書 R3 で足りる可能性 — 先に ledger の消費者 (0.2x lever / daily report / index 行) を棚卸しして判定。(b) keep (D5 材料) |
| 7 | **規律文言の改定 (R3 文書)**: (i) 執行窓条件を「open 0 ∧ 直近 signal なし (直近 1 H1 bar に live-eligible signal がない)」へ (§3 の新型の穴、候補 (c)) / (ii) PR body 固定見出しに **estimand 宣言** (母集団・分母・凍結値への非接触) を追加 — P1 の最頻型 (estimand / 母集団) の起票時予防 / (iii) deploy 後 N 分の LIVE 送信抑止 (候補 (a)) は原則 1 と衝突し得るので **user 上程のみ** | R3 文書 / Claude、(iii) は user | 10-28 | 効かない。前提条件 | 「規律を増やすと容量を食う」 → (i)(ii) は文言 2 行、計測は既存 (session log / PR body)。(iii) は live 経路変更なので提案止まり ⇒ keep (i)(ii)、(iii) user |
| 8 | **プロセス固定費の削減 (user 上程)**: (i) wiki-daily scheduled run の欠落 (10 月 9 日 / 21 日 = 43%) の原因 (scheduled task 側のログ) を 1 回調査して記録 / (ii) 座礁ローカル main (behind 300 超、救済 PR 7 本) の恒久策 3 択 (reset --hard は user 操作) を packet 追補として再上程 / (iii) `storm_guard` 状態の永続化 (deploy 毎に消失、5 例) は enforce とは別の R3 候補として user 決裁待ちに置く (readout 分母にのみ影響) | R3 記録 / user | 11-07 | 効かない。供給の回復 | 「救済 PR は docs-only で安い」 → **partially refuted**: 救済 1 本 ≈ 0.5 セッション (差分照合 + Codex 1〜2 巡)、本スプリント 30 日で **8 本** (§2.4: 既往 7 本 + 本 run #342) = **4 セッション ≈ 供給 [10.5, 19] の 21〜38%** (既往 7 本のみでも 3.5 セッション = 18〜33%)。原因調査 1 回は元が取れる ⇒ keep (i)(ii)、(iii) は記録のみ |

**採用しなかった / 90 日側のまま**: Rank 4 (v) NO-DATA スタブ / (vii) engine-tick endpoint (10 月再発 0) / Rank 5 (d) block 台帳 readout tool / Rank 3 (iii) M3b ラベル tool 反映 (tools 1 行、ついでの PR に同乗可、単独では起票しない) / EXEC_CONTRACT 検知器 / 汎用 reconcile tool / 時計台帳 v0 / venue feasibility / Turtle S2 liveness / CME ZQ・SR3 / bypass set 衛生。

**固定日 (triage 対象外、登録済み)**: `single-engine-shadow-rate-attribution-readout` 10-27 / `adhoc-scan-29-step1-census-gate` 11-07 / `edge-supply-scan-monthly` 第 7 次 11-17 / `integrated-decision-packet-d1-d12-user-response` 11-29 / `kalman-d7-live-exit-disposition-user-decision` 11-29 / U3 11-30。

**user 専権 (期日超過、autopilot は代行しない)**: W1 (10-04) / sr-anti-hunt EUR_JPY count-basis・lock-validity (10-12) / OANDA Gold 10 月 record (09-30) / D5・D11 (11-30 / ≒10-25)。

---

## 5. チェックポイント

| 日付 | 内容 | 判定基準 |
|---|---|---|
| 11-07 | 中間: #1 執行済みか (user 操作の有無)、#4 凍結、#5 DST、#6(b)、#8(i) | 執行されていなければ「permission 待ち N 日」を数字で記録、#2 は着手しない |
| 11-21 | 終了レビュー (REG `sprint-1022-triage-close`) | §1 形式 + 巡目 (code 中央値、上限超過率 58% → 30% 以下が目標)、繰延 P2 消化率、窓違反 0、deploy 直後 fill の再発件数 |

## 6. 出所索引

| 主張 | 出所 |
|---|---|
| 8 項目の文言・判定基準 | SPRINT §2.1 / REASSESS §3 L67–L74 |
| 中間チェック | REG `sprint-0922-midpoint-check` resolution (10-05) |
| 巡目・P1/P2 集計 | GitHub API (PR #280〜#341、2026-10-21 03:4xZ)、計数定義は §2.1 |
| 起票時の巡目 5〜18 (中央値 6) / 繰延 9 件 | REG `sprint-0922-triage-close` message |
| 10-16 違反 | `sessions/2026-10-19-session.md` L25 |
| deploy 直後 fill | `sessions/2026-10-20-session.md` Phase 1 / [[2026-10-20]] 発見 2・未決 17 |
| storm guard 捕捉 3 波 / enforce 判断 / 執行窓 | [[storm-guard-design-2026-09-22]] §7.1–7.4 |
| D11 両基準 | [[d11-both-basis-m1-monitor-2026-10-19]] |
| E1 POSTPONE | [[e1-first-look-runbook-2026-09-22]] §8-1 / PR #323 |
| render.yaml ignoredPaths | `render.yaml` L50–131 |
| daily_report ホスティング事実 / NO-DATA 不在 | `scripts/daily_report.py` L235, L266, L314, L1273–1297 |
| healthz | `app.py` L185–194, L13682, L13700 |
| M3b 出力 | `tools/m1_clean_live_monitor.py` L854–871 |
| carry_dip card L3 / 29 fill | [[usdjpy_carry_dip_accumulator]] L3, 10-20 節 |
| wiki-daily 欠落 9 日 / 座礁 | [[2026-10-20]] 未決 13 / 発見 5、PR #299 #301 #312 #315 #332 #335 #336 |
