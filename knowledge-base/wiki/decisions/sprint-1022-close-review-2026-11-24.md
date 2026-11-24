# 30 日スプリント (2026-10-22〜11-21) 終了レビュー + 次 30 日 triage — 2026-11-24 (autopilot、rule:R3 文書のみ)

作成規律: 文書のみ (R3、code 変更なし、価格データ・DB 計算ゼロ、凍結 look の outcome 非接触)。registry `sprint-1022-triage-close` (期日 11-21、**3 日超過** = autopilot 11-20 run ENOTFOUND 失敗 + 11-21〜23 未発火、§5) の条件 = (1) [[sprint-0922-close-review-2026-10-21]] §4 の 8 項目の done / in-flight / parked、(2) 巡目実測 (code PR 中央値・上限 ≤6 超過率・繰延 P2 消化率)、(3) market-safe 窓違反件数、(4) deploy 直後 fill (未決 17) の再発件数、(5) 次 30 日 triage (REASSESS §3 形式、両レンズ反証つき)。数字は出所併記、新しい数字は作らない。Live = `oanda_trade_id != ''` のみ。

略号: PREV = [[sprint-0922-close-review-2026-10-21]]、SPRINT = [[sprint-triage-pr-discipline-2026-09-22]]、REASSESS = [[path-to-win-reassessment-2026-09-22]]、REG = `knowledge-base/wiki/decisions/prereg-trigger-registry.json`、TOOL = `tools/pr_round_stats.py` (計数定義 = PREV §2.1 凍結、PR #374)。集計 = merged 2026-10-22〜11-21 の PR **#348〜#383 (36 本)**、TOOL 出力 `raw/analysis/pr-round-stats-sprint1022-close-2026-11-24.json` (2026-11-24 10:1xZ 取得)。陽性対照 (0922 窓) = `raw/analysis/pr-round-stats-sprint0922-control-2026-11-13.json` (PREV §2.5 の規律どおり**両窓とも TOOL の値**で比較し、PREV §2.2 の手集計値とは混在させない)。

---

## 0. TL;DR

- **8 項目 = done 8 / partial 0 / parked 0 (Claude 側)**。user 側の決裁が開いたままのもの 5 件 (W1 10-04 超過 / storm_guard 状態永続化 / deploy 直後 LIVE 送信抑止 / 座礁 main 恒久策 A・B・C / `reset --hard`) は §1 に残置 — autopilot は代行しない。
- **巡目 (`@codex review` 依頼回数、TOOL 字義) 中央値: code PR 0 (n=23) / docs 0 (n=13) / 全体 0** — 0922 窓 (TOOL 再集計、code 中央値 4 / n=47) から**低下**。上限 (≤6) 超過は **1 / 23 = 4.3%** (PR #376 = 9 巡、P1 7) ⇐ 0922 窓 13 / 47 = 27.7% ⇒ PREV §5 の目標「58% → 30% 以下」(手集計基準) は TOOL 基準でも達成、**§3.1 の上限 (≤6) は据え置き** (SPRINT §6 の見直し条件は不成立)。
- **inline P1 7 / P2 18 / P3 0 (全件 40)** ⇐ 0922 窓 P1 75 / P2 271 / 全件 530。**connector の到達率 100% (summary comment 36/36)、findings あり 5/36** (§2.3) ⇒ 減少は「不到達」ではなく「指摘減」。ただし母集団が違う (0922 窓 = live 経路 PR 多数 / 1022 窓 = tools・docs・registry 中心、live 経路 (`modules/`・`app.py`) に触った PR は **4 本** #357 / #363 / #365 / #382) — **「規律が効いた」とは主張しない** (§2.4)。
- **繰延 P2 = 新規 0 件** (REG に窓内の `review-backlog-*` 新規 entry なし、session log に繰延記載なし、P2 18 件は全て PR 内で消化 or 理由付き ack) ⇒ 消化率は分母 0 で定義できない (§2.2)。
- **market-safe 窓違反 0 件** (code PR 23 本のマージ時刻 × live 建玉 7 件の open 区間に交差なし、日曜 20:00–22:30Z のマージ 0、§3)。
- **deploy 直後 fill の再発 1 件** (11-04 02:39:32Z live → carry_dip #1347030 fill 02:39:43Z = **11 秒後**、10-20 の 14 秒と同型。deploy 22 本中 1 本、§3)。候補 (a) 送信抑止は user 上程のまま、(c) 規律文言は 10-23 に改定済み。
- **読み手の固定費 (再掲、悪化)**: autopilot が session log / PR で実在する run 日 **16 / 31 日** (11-17 ENOTFOUND 失敗、他は未発火 = ホスト可用性)、本レビュー自体が 11-20 run の ENOTFOUND 失敗 + 11-21〜23 未発火で **3 日遅延**。wiki-daily も同型 (§5)。供給の回復は user 側 (案 C) にしかない — **案 A (pull-first) は kb-rescue-fold 自動化 (11-14/16) で不要になった = 不採用を記録** (§1 #8)。
- **9 月 22 日決裁「勝てるまで」の 60 日累計** (REASSESS §0 (c)+(b)): (c) 測定可能状態 = 統合パケット v1.0 ✓ + D11 既定凍結 ✓ (10-29) + E1 second look 12-30 ✓ (UNDERPOWERED 経由) / (b) kill 検知器 = F3 両基準 ✓ + DD 台帳 writer 一本化 ✓ (11-04) + units 解決 ✓ (11-19)。(a) M2 到達は依然 user 決裁 (U3 ∧ D1、11-30) 待ち — 構造不変。

---

## 1. 8 項目の判定 (証拠付き)

判定基準 = PREV §1 と同じ (done = PREV §4 の文言どおり main にマージ済み / partial = 主目的は着地したが sub-item 未着手 / parked = 着手せず)。証拠は REG entry の `resolved` 日 + PR 番号 (worktree origin/main 2026-11-24 読み)。

| # | 施策 (PREV §4) | 判定 | 証拠 (done 分) | user 側に残るもの |
|---|---|---|---|---|
| 1 | storm guard enforce 執行 + first-storm readout | **done** | enforce ON **11-03 05:33:27Z** (dep-dbkn3fegekts73ekq5h0、REG `storm-guard-enforce-execution-window` resolved 11-03、通算 10 回目の試行で初成功) / first live trail readout = carry_dip #1347030 (11-04) で正当 tightening 喪失 0、REG `storm-guard-enforce-first-storm-readout` resolved 11-05 (期日 11-15 の 10 日前倒し、PR #367) | なし (R2 解除条件 = 喪失 ≥1 / failed 急増、以後の live trail 4 件 #1347071 / #1347096 / #1347135 / #1347157 で解除事由なし) |
| 2 | family A の根 + storm #3 の 2 writer 特定 (R3) | **done** | 修理 PR #346 (10-21 10:06Z deploy、窓開始前) + readout `sl-persist-root-fix-first-live-trail-readout` resolved 10-29 (#1346967 で `REPLACEMENT` 1 / storm 0、idempotent == monotonic == 0) / REG `family-a-root-two-writer-r3` resolved 10-21 (期日 11-14 の 24 日前) | なし |
| 3 | D11 user 決裁の窓 + F3 両基準 readout (N≥30) | **done** | carry_dip N=30 到達 10-23 (#1346967) → REG `integrated-decision-packet-d11-user-decision` TRIGGERED → **既定 (REG 字義 demo 簿) で凍結** (10-29、PR #354、user 返答なし) / F3 両基準 readout = `m1_clean_live_monitor --strong` 10-29 (demo 2 / broker 2 セル、不一致 0、[[integrated-decision-packet-d1-d12-2026-09-22]] §8-12) | D11 返答は user-response entry (11-29) 経由でも転記しない (Codex P2 4214840473) |
| 4 | E1 POSTPONE 分岐の固定日 (11-05 凍結 / 11-12 verdict) | **done** | 凍結 11-06 (cutoff 11-05T06:33:31Z 到達後、品質 gate 6/6、coverage 92.38%) → first look 判定器 = **UNDERPOWERED** (C3 = S1×24h のみ N=47) → second look cutoff 12-30 / verdict 2027-01-06 (REG `e1-first-look-postponed-freeze-due` / `e1-prereg-verdict-deadline` resolved 11-06、PR #368)。ECG #22 forward first look も同 PR で UNDERPOWERED (second look 2027-01-31) | なし |
| 5 | wg: dst-cutoff R3 (10-25) + G1 (10-31) + W1 user 決裁 | **done** (Claude 側) | `wg-dst-cutoff-basis-r3` resolved 10-22 (構造バグなし、test pin + 監査 tool、PR #350) / 冬時間初週末 11-01 実開場 22:04Z = 乖離 0 (`wg-winter-first-weekend-open-time-check` resolved 11-02、PR #360) / spread re-run 11-04 (`wg-winter-sunday-open-spread-rerun` resolved) / G1 = clean live N=0 のまま roll (REG `weekend-gap-live-g1-slippage` deadline 11-30) | **W1 (REG `wg-execution-modality-r1-packet-v1-w1-decision` 10-04、51 日超過)**。F2 (12-31) に N=0 なら「PASS→live 変換は未実証」認定 |
| 6 | 読み手欠陥 R3 ×2: (a) DD ledger 非計上 (11-07) / (b) carry_dip exit 棚卸し (10-31) | **done** | (a) 消費者棚卸し 10 件 → 実消費者 = 0.2x lever + dd_status の 2 つ = PREV §4 #6 の反証『ledger は 0.2x の入力ではない』を **code 事実で否定** → **修理** (writer `_book_equity_close` 一本化、PR #365、11-04 deploy、CF pin 8) + units 解決 (PR #382、11-19) = `[LEDGER_UNITS]` marker。REG `dd-ledger-nonbooking-consumer-audit` resolved 11-04 / (b) 30/30 を broker tx reason で分類 (TP 2 / ON_FILL SL 12 / BE 8 / trail 7 / halt 1、分類不能 0、REG `carry-dip-exit-type-inventory` resolved 10-29) | 遡及再アンカー (KV 移行、別 R3) / 部分約定時 `currentUnits` (lot↑ R1 packet の同梱要件) は §4 |
| 7 | 規律文言の改定 (R3 文書) | **done** | (i) 執行窓条件に「直近 1 H1 bar に live-eligible signal なし」 + (ii) PR body に estimand 宣言見出し (REG `sprint-1022-policy-wording-r3` resolved 10-23、期日 10-28 の 5 日前、PR #352) | (iii) deploy 後 N 分の LIVE 送信抑止 = 原則 1 と衝突し得るため user 上程のみ (未回答) |
| 8 | プロセス固定費 (i) wiki-daily 欠落原因 / (ii) 座礁 main 恒久策 / (iii) storm_guard 永続化 | **done** + 超過達成 | (i)(ii)(iii) を [[sprint-1022-process-fixed-cost-upsubmit-2026-11-05]] に記録 (REG resolved 11-05、PR #367): (i) 欠落 9/22 営業日 = ホスト可用性、skill 側欠陥 0 / (ii) 3 択 A・B・C を再上程 / (iii) 7 例を R3 候補として起案。**加えて座礁救出の後半を自動化**: `tools/kb_rescue_fold.py` + `kb-rescue-fold.yml` (PR #376、11-14) → CONFLICT 14/14 空振りの R3 修理 (PR #378、11-16) → cron 11-16 07:26Z 以降 **rc 0 連続** (11-18〜11-24 12 run success、`kb-rescue-fold-first-cron-readout` resolved 11-18)。人手救出 PR は PR #373 (11-12) を最後に 0 本 | (ii) の選択 (A / B / C) と `reset --hard`、(iii) の採否は user。**案 A「無回答 = 次 run で実施」は本レビューで不採用に改める**: pull-first は ff 不能日に wiki-daily を丸ごと欠落させる設計だが、fold 自動化後は座礁物が cron で origin に届くため「欠落させない現状」の方が供給を残す (§4 #4 反証) |

**90 日側 parking の再浮上**: なし (PREV §4 末尾の未採用項目は不変)。

**観測 (本レビューで新規)**: origin に `kb-rescue/*` ref が **8 本** (11-16 ×2 / 11-17 / 11-18 / 11-19 ×2 / 11-20 / 11-24) 残存 (11-24 10:0xZ)。cron 11-20 07:51Z は 11-20 ref を PRESENT で prune、11-23 08:23Z / 11-24 00:27Z は **ref 0 本** (fetch 一覧に `kb-rescue/` なし) ⇒ 8 本は**今日のホスト復帰 (09:5xZ) 以降に再 push されたもの** = ローカル main が ahead 20 のまま (`reset --hard` 未執行) なので session-end hook が毎回同じ退避 ref を作り直す。tool 欠陥ではなく、13:00Z cron が PRESENT / prune する見込み (次 run で確認)。固定費としては無害 (cron が吸収) だが「ahead が消えない限り再 push ループは続く」= (ii) の user 決裁待ちの需要側実測。

---

## 2. 巡目実測 (PR #348〜#383、36 本、TOOL)

### 2.1 計数定義 (PREV §2.1 凍結、TOOL 実装)
- 巡目 = issue comment に `@codex review` を含む件数 (connector 自身の投稿を除く = PREV §2.5 の系統差 −1 を織り込み済み)。
- inline P1/P2/P3 = `pulls/{n}/comments` 本文先頭 40 文字の Codex バッジ。
- code PR = title 接頭辞が `docs(` / `kb:` / `research(` でない、**または** docs 接頭辞でも非 `.md` / 非 `knowledge-base/` ファイルを含むもの (registry JSON を含む docs PR は code 側 — PREV §2.5 の「第 3 クラスに切るか」は**切らない** (下記 2.4))。

### 2.2 結果 (両窓とも TOOL)

| 指標 | 1022 窓 code (n=23) | 1022 窓 docs (n=13) | 1022 窓 全体 (n=36) | 0922 窓 全体 (n=62、TOOL) | 0922 窓 code (n=47、TOOL) |
|---|---|---|---|---|---|
| 巡目 中央値 / 平均 / 範囲 | **0** / 1.09 / 0〜9 | 0 / 0.0 / 0 | **0** / 0.69 / 0〜9 | 3 / 3.71 / 0〜18 | 4 / 4.43 / 0〜18 |
| 巡目 >6 (上限超過) | **1 (4.3%)** (#376) | 0 | 1 (2.8%) | 13 (21.0%) | 13 (27.7%) |
| 分布 (巡目: 本数) | 0×12, 1×7, 2, 3, 4, 9 | 0×13 | 0×25, 1×7, 2, 3, 4, 9 | 0×17, 1×8, 2×4, 3×4, 4×3, 5×8, 6×5, 7×7, 8×2, 9, 13, 15, 18 | — |
| inline P1 合計 | 7 (全て #376) | 0 | **7** | **75** | 74 |
| inline P2 合計 (P3) | 15 (0) | 3 (0) | **18 (0)** | 271 (5) | 226 (5) |
| inline 全件 (返信含む) | 37 | 3 | 40 | 530 | 480 |
| 最多巡目 | #376 9 / #364 4 / #348 3 | — | — | #287 18 / #299 15 / #310 13 | — |

**判定**: SPRINT §6「巡目中央値が下がらなければ §3.1 の上限 (≤6) を見直す」— code 中央値 4 → **0** で下がった ⇒ 上限値は据え置き。PREV §5 の目標 (上限超過率 30% 以下) は 4.3% で達成。

**繰延 P2 の消化率**: 窓内に新規の `review-backlog-*` entry は REG に **0 件** (10-22 以降の最終 resolve は `review-backlog-326/328` 10-20 = 前窓)、session log 10-22〜11-19 に「繰延」記載 0 (11-02 の 1 件は wg artifact の文脈で P2 ではない)。P2 18 件は全て PR 内で修正 commit or 理由付き ack (`pr_review_gate.py` exit 0 がマージ条件) ⇒ 繰延 0 / 消化率は**分母 0 で未定義** (記録のみ)。P1 の繰延 0。

### 2.3 connector の到達率 (PREV §2.5 が要求した併記、TOOL の外、`issues/{n}/comments` 2026-11-24 10:0xZ 取得)
- connector summary comment (`<!-- codex-pull-request-review-summary -->`) = **36 / 36 (100%)**。
- summary 内 `has_any_findings` = **true 5 本** (#362 / #363 / #368 / #371 / #376)、false 30 本、parse 不能 1 本 (#353、docs)。
- `pulls/{n}/reviews` に connector の review オブジェクトあり = 11 / 36 (#348 #350 #354 #362 #363 #364 #368 #371 #376 #378 #382) — summary だけで終わる PR が 25 本。
- ⇒ P1 75 → 7 / P2 271 → 18 は**到達の欠落ではない**。

### 2.4 母集団の注意 (「規律が効いた」と読まない理由)
- 0922 窓は live 経路・verdict・凍結 export の PR が多数 (P1 の発生源は estimand / 母集団の指摘、PREV §2.2 (ii))。1022 窓で live 経路 (`modules/` / `app.py`) に触った PR は **4 本** (#357 kalman R2 停止 / #363 max_open / #365 DD ledger writer / #382 units)、残り 19 本の code PR は tools・tests・registry JSON・workflow。P1 7 件は全て #376 (fold tool、19 本側) に集中し、live 経路 4 本の P1 は 0。
- PREV §4 #7 (ii) estimand 宣言見出しの効果は、この母集団差と分離できない (N も小さい) ⇒ **因果は主張しない**。次窓も両窓 TOOL 集計 + 到達率併記を続け、live 経路 PR が増えたときの P1 率で読む。
- 「registry JSON のみを含む docs PR」を第 3 クラスに切るか (PREV §2.5): 1022 窓でそれに当たるのは #352 / #354 / #356 / #358 / #359 / #364 / #366 / #367 / #370 / #372 / #380 の 11 本 (code 23 の約半分)。切ると code 中央値は 12 本で読むことになり差が出ない (いずれも巡目 0〜4) ⇒ **切らない** (定義不変、0922 窓との比較可能性を優先)。

---

## 3. market-safe 窓 (SPRINT §3.2) と deploy 直後 fill (未決 17)

**判定方法 (機械)**: code PR 23 本の `mergedAt` (GitHub API) と、窓内 live 建玉 7 件の open 区間 (`/api/demo/trades` 2026-11-24 09:5xZ、`oanda_trade_id != ''`) の交差。

| live 建玉 (carry_dip USD_JPY BUY、全件 1,000u) | open 区間 (UTC) | 区間内の code マージ |
|---|---|---|
| #1346967 | 10-23 04:02 → 08:00 | なし (#352 は 03:02Z、fill の 59 分前) |
| #1346976 / #1346985 | 10-29 10:16 → 11:02 / 18:52 → 20:01 | なし (#354 は 05:12Z) |
| #1347030 | 11-04 02:39:43 → 02:58 | なし (#365 は 02:37:51Z = fill の **1 分 52 秒前**、deploy live 02:39:32Z の 11 秒後に fill) |
| #1347071 | 11-06 06:03 → 06:52 | なし (#368 は 05:06Z) |
| #1347096 | 11-09 07:01 → 07:54 | なし |
| #1347135 | 11-18 15:03 → 11-19 03:10:22 | なし (#382 は 03:13:52Z = 決済の 3 分 30 秒後、session log に open 0 再確認の時刻あり) |

- **違反 0 件**。日曜 20:00–22:30Z (b) のマージ 0 (窓内の土曜マージ #376 11-14 03:10Z は市場閉鎖中)。
- (a) 改定後の追加条件「直近 1 H1 bar に live-eligible signal なし」(10-23) は session log の記載 (11-03 / 11-04 / 11-19) でしか検証できない = 記録上の違反 0。機械検証するなら audit `bridge_status` の直近 1 時間を merge 時刻で引く読み手が要る (起票しない、次窓で違反が出たら起票)。
- **deploy 直後 fill の再発 = 1 件 / deploy 22 本** (Render `list_deploys` 10-22〜11-19): 11-04 #1347030 (live 02:39:32Z → fill 02:39:43Z、11 秒) — 10-20 (14 秒) と同型。他の 6 fill は最寄り deploy から 54 分 (#1347071) 以上離れている。候補 (a) 送信抑止 (user 上程) は未回答、候補 (c) 文言改定は 10-23 済み — (c) は merge を止めるだけで、deploy **後**の新プロセスの初 signal は止めない (構造上 (a) しか効かない) ⇒ user 上程の継続 (§4 #6)。
- 関連する観測: 11-19 #1347135 は merge の **3 分前**に決済 = 窓が開いた理由。窓の「open 0」判定は heartbeat でなく `open_trades` で行う規律 (MEMORY 10-20) は守られた。

---

## 4. 次 30 日 (2026-11-22〜12-21) triage — REASSESS §3 形式、両レンズ反証つき

レンズ: L1 = time-to-M2 / kill-condition 順 (∞→有限の可能化 / 有限化後に動かす / 効かない) / L2 = 容量・前提条件。反証 = 「やらない」側から読んで keep / reclassify / drop。autopilot 禁止 (SPRINT §5) は不変。time-to-M2 の分子を Claude 単独で動かす施策は本窓も **0** — 窓の中身は固定日の読み手 + R3 1〜2 本 + user 決裁待ちの再上程に絞る。

| # | 施策 | Rule / owner | 期限 | L1 効果 | L2 反証 → 判定 |
|---|---|---|---|---|---|
| 1 | **user 決裁の期日 4 本を既定で閉じる (記録のみ)**: `daily-market-review-abolition-user-decision` (11-26、無回答 = (b) 縮退継続) / `integrated-decision-packet-d1-d12-user-response` + `kalman-d7-live-exit-disposition-user-decision` (11-29、無回答 = D7 (b) 現状維持、D1〜D12 は未返答項目を残して deadline は動かさない) / U3 (11-30) | record-only / user | 11-26 / 11-29 / 11-30 | (a) M2 到達は U3 ∧ D1 の返答でしか有限化しない | 「既定で閉じるなら読まなくてよい」 → **refuted**: 既定の適用自体を KB に書かないと次の読み手が『未決』と誤読する (D11 10-29 の前例) ⇒ keep |
| 2 | **固定日 readout 6 本** (Claude、record-only): 11-30 `weekend-gap-live-g1-slippage` (N=0 なら roll) / `e12-volume-prereg-staleness-review` (継続 or クローズのみ) / `carry-dip-v3-revival-watch` backstop (N≥10、R2 predicate は両基準で再読) / `alpha-scan-b7-b8-livecell-recheck` (live 可能セル層の N、post-hoc 禁止) ・ 12-01 `hourblock-class-exempt-r2-rollback` (marker 付き clean live N<10 なら stale review) ・ 12-03 `edge-supply-active-line-idle-r5` (能動ライン 0 の 30 日判定、11-18 §2.1 の先行列挙を延長) ・ 12-17 第 8 次スキャン (#29 (b) 再裁定を含む) | R3 record-only | 各期日 | 効かない (読み手) / R5 は供給の空白の機械化 | 「全部まとめて 12-03 に読めばよい」 → **refuted**: 11-30 の 4 本は cron (00:20Z 翌日) が個別に TRIGGERED を出す。まとめ読みは期日超過の常態化 (本レビュー 3 日遅延) を増やす ⇒ keep (期日順) |
| 3 | **DD 台帳 readout の estimand 再定義 (R3 文書、12-04)**: `dd-ledger-broker-close-first-booking-readout` は「`OANDA_SL_TP` 決済 ≥1」を条件にするが、deploy 後の broker 先行決済 **5 / 5** (#1347030 / #1347071 / #1347096 / #1347135 / #1347157) が全て engine 同 tick 検知で `SL_HIT` label = `OANDA_SL_TP` は engine が**検知できなかった**決済だけ。live fill 7 件/30 日の頻度では条件が到達不能になり得る。本 run で +14 日 (12-04) に roll し、12-04 に依然 0 件なら「engine 経路の計上は 5/5 実測一致 (+¥102 / +¥117 / +¥235 / −¥182、§6 出所)、broker-only 経路は CF pin 8 本 (`tests/test_dd_ledger_books_broker_closes_r3.py`) で担保」として **resolve (R3 文書、code 変更なし)** | R3 / Claude | 12-04 | 効かない (lever の読み手) | 「live 読み取りが取れるまで待つべき」 → **partially refuted**: 待つコストは 0 だが、entry が永久 roll すると registry の『期日超過』ノイズになる (R5 と同じ enforcement の劣化)。12-04 の 1 回だけ追加で待ち、0 件なら pin で閉じる ⇒ keep (reclassify: readout → pin 担保) |
| 4 | **プロセス固定費の再上程 (user) + 案 A の不採用記録**: (i) autopilot 稼働 16/31 日、wiki-daily 11 月 succeeded 7 run (11-04 / 05 / 06 / 11 / 12 / 13 / 18、`list_task_runs` 直近 12)、失敗は全件 `ENOTFOUND` = ホスト可用性 (11-05 §(i) と同型) → **案 C (クラウド routine 化) を再上程**、無回答でも Claude 側で動かせる代替なし / (ii) 案 A は fold 自動化で不要 (§1 #8) = **不採用** / (iii) `kb-rescue/*` の再 push ループは `reset --hard` (user) まで続く (無害) | R3 記録 / user | 12-04 (中間) | 効かない。供給の回復 | 「案 A はタダなのでやっておけ」 → **refuted**: fold 自動化後の座礁は損失ではない (cron が畳む) が、pull-first は ff 不能日 (= ahead が残る限り毎日) に wiki-daily を**実行させない** = 供給を減らす側に働く ⇒ drop (A)、keep (C 再上程) |
| 5 | **storm_guard 状態永続化 (iii) の再上程**: 再起動による状態消失 **15 例** (11-19 時点、全て PR deploy 帰属 = 定常)。enforce ON 後の喪失は 0 だが readout 分母が毎 deploy でリセットされる。採否は user (R3 候補、live 経路の KV 書き込みが増える) | user | 11-29 (packet と同時) | 効かない | 「material 0 なら放置でよい」 → keep as-is (再上程のみ、起案しない = 11-05 §(iii) の既定どおり) |
| 6 | **deploy 直後 LIVE 送信抑止 (a) の再上程**: 再発 1 件 (11-04、11 秒)。(c) 文言改定では構造上止まらない (§3) | user | 11-29 (packet と同時) | 効かない (執行窓の保護) | 「11 秒後の fill は carry_dip の正当 signal で損失ではない」 → **true**: 原則 1 (攻める) と衝突するため Claude は起案しない、提示のみ ⇒ keep (上程) |
| 7 | **live_fill_stagnation 閾値の再較正 (12-03、R3)**: 窓内 live fill 7 件の到着間隔 (10-23 → 10-29 6.3 d / 10-29 同日 8.6 h / → 11-04 5.3 d / → 11-06 2.1 d / → 11-09 3.0 d / → 11-18 9.3 d / → 11-24 5.6 d) を lesson 手順で取り直す。規律 (a) 閾値は**上げる**方向のみ (b) 消滅構成のギャップを混ぜない (c) 構成変更 (kalman R2 停止 10-30 / ps carve-out 10-10) で n リセット | R3 / Claude | 12-03 | 効かない (検知器) | 「9.3 d の空白は誤発火ではなく実態」 → 閾値 120 h は 11-09〜18 で正しく発火 (daily report 既知) = 誤発火 0 ⇒ 据え置きが既定、数字の取り直しだけ keep |
| 8 | **容量規律**: 上限 ≤6 据え置き (超過 1/23)。estimand 宣言見出しは継続。次窓も TOOL 両窓集計 + 到達率併記 | 文書 | 12-21 | 効かない | 「P1 が 7 まで減ったので規律を緩めてよい」 → **refuted**: 母集団差 (§2.4) で効果が未分離 ⇒ keep |

**採用しなかった / 90 日側のまま**: 遡及再アンカー (KV 移行、lever への影響 = 過去分のみ、T5 R1 packet で同梱) / 部分約定 `currentUnits` (同上) / `ws3-round4-fx-leg-coverage` (`MASSIVE_API_KEY` secret = user、WATCHING 継続) / 執行窓条件 (a) の機械検証器 (違反 0 のうちは起票しない) / PREV §4 末尾の未採用項目。

**固定日 (triage 対象外、登録済み)**: `e1-second-look-freeze-due` 12-30 / `project-falsification-f2-wg-live-conversion` 12-31 / `weekend-gap-live-g2-cumloss` 12-31 / `e1-prereg-second-look` 2027-01-05。

**user 専権 (期日超過、autopilot は代行しない)**: W1 (10-04) / sr-anti-hunt EUR_JPY count-basis・lock-validity (10-12) / OANDA Gold 10 月 record (09-30) / T5 lot 1.0x 復帰 (R1、前提条件は 11-19 で揃った) / rnb 判定 (R1) / `reset --hard`。

---

## 5. 読み手の固定費 (本レビューの遅延の内訳)

| 日 (UTC) | autopilot | wiki-daily | 備考 |
|---|---|---|---|
| 11-17 | failed `ENOTFOUND` (02:05Z) | failed `ENOTFOUND` (13:59Z、11-16 13:18Z 開始分も) | ホスト遅延発火 |
| 11-18 / 11-19 | succeeded | 11-18 succeeded / 11-19 なし | — |
| 11-20 | failed `ENOTFOUND` (03:58Z) | failed `ENOTFOUND` (03:17Z) | 期日 11-20 (dd-ledger) 消化不能 |
| 11-21 / 11-22 / 11-23 | 発火なし | 発火なし (11-21 金 / 11-23 月) | 期日 11-21 (本 entry) 超過 |
| 11-24 | 09:56Z 発火 (定刻 01:09Z から 8.8 h 遅延、全 scheduled task が 09:52〜09:56Z に同時発火 = ホスト復帰) | 09:52Z 発火 (running) | 本 run |

出所: `list_task_runs` (fx-roadmap-autopilot / wiki-daily-update、2026-11-24 10:0xZ)。分類は 11-05 §(i) と同じ (未発火 = 発火記録なし、失敗 = 遅延発火 + DNS 不達)。skill 側の不履行 0。

---

## 6. 出所索引

| 主張 | 出所 |
|---|---|
| 8 項目の文言 | PREV §4 |
| REG resolved 日 / resolution 本文 | `prereg-trigger-registry.json` (origin/main 184bfe63c、2026-11-24) |
| 巡目・P1/P2 (両窓) | `raw/analysis/pr-round-stats-sprint1022-close-2026-11-24.json` / `raw/analysis/pr-round-stats-sprint0922-control-2026-11-13.json` (TOOL) |
| 到達率 / has_any_findings | GitHub API `issues/{n}/comments` + `pulls/{n}/reviews` (#348〜#383、2026-11-24 10:0xZ) |
| code PR の merge 時刻 / live 経路 4 本 | `gh pr view --json mergedAt,files` |
| live 建玉 7 件の open 区間 | `/api/demo/trades?limit=2000` (2026-11-24 09:5xZ) |
| deploy 22 本の live 時刻 | Render `list_deploys` srv-d6va1of5r7bs73en10vg (2026-11-24) |
| DD 台帳の計上一致 (+¥102 / +¥117 / +¥235 / −¥182) | REG `dd-ledger-broker-close-first-booking-readout` note 11-05 / 11-11 / [[2026-11-19-session]] Phase 5 / [[2026-11-24-session]] Phase 2 (`[LEDGER_UNITS] … pnl_jpy=-182.0` 02:04:06.735Z) |
| kb-rescue cron run / ref 再 push | `gh run list --workflow kb-rescue-fold.yml` + run log 11-20 07:51Z / 11-23 08:23Z / 11-24 00:27Z、`git branch -r` 2026-11-24 10:0xZ |
| scheduled task の run 一覧 | `list_task_runs` (2026-11-24 10:0xZ) |
| wiki-daily SKILL.md に pull-first なし | `~/.claude/scheduled-tasks/wiki-daily-update/SKILL.md` (28 行、2026-11-24 読み) |
