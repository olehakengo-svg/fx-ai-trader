# 統合決裁パケット D1〜D12 (+D15) — DRAFT v0 (2026-09-22)

> **種別**: user 決裁パケット (rule:R3 文書 — Claude は起票・推奨・既定挙動の明示まで。D1/D3/D4/D5 の選択そのものは user 専権で、推奨は決裁の代替ではない)
> **Status: DRAFT v0.5** (2026-09-22 起票、同日 PR #279 レビュー消化で 10 点訂正 — 1 巡目: D5 既定の R2 predicate を REG 凍結値に戻す [P1] / carry_dip N≥30 ETA を D5 分岐で条件付け [P2] / floor ¥262,000 到達 ≠ API 停止 を明記 [P2]; 2 巡目: D3 補項 (b) の 3 leg 同時損失を quote 通貨別 pip 値で再計算 ¥22,500→¥31,140、L1 開通 NAV ¥900k→¥1,245,600 [P1] / 「∞→有限は D3 ∧ D1」を「前提は D3、D1 はサイズ」に訂正 [P2]; 3 巡目: D11 無回答の既定を REG F3 `condition` 字義 (N≥30 ∧ PnL>0) に戻す — 強定義 primary の採用は REG 改定を伴う [P2]; 4 巡目: D3 補項 (a) 単 leg 読みでも wg の L1 開通 NAV は binding leg (USD-quote) の ¥472,800 — ¥300,000 は JPY leg 単独 rung (per-leg rung 実装 R1 前提) に限る、D3 参照点を 2 値化 [P1] / kill 順序で floor 幅 03-04〜04-07 と F3 03-31 の重なりを表記 [P2]; 5 巡目: 有限化前提に D2(i)=(a) を併記 — 無回答なら code が L1 5000u × 0.2 → 1000u に潰し入金しても容量が出ない [P2] / §3.4 の「本」= wg 級 3 leg 一括ストリーム (pooled 率) と明示、type×pair×dir 単位では約 3 倍の pair セル換算列を追加 [P2])。**確定版 = 2026-10-08 (E1 cutoff)**。user 返答期限 = **2026-11-30** (E1 verdict 10-15 後の返答を推奨)。D1〜D4 のみ先行返答でも分母は有限化できる。
> **起点**: [[path-to-win-decision-memo-2026-09-20]] §3 Rank 1 / §4.1 末尾 D1〜D12 (L128–140) → 再評価 [[path-to-win-reassessment-2026-09-22]] §1–§4 (訂正一覧・UD1〜UD7) → user 2026-09-22「推奨で任せるから進めて、勝てるまで行こう、ただしとにかくペースアップしたい」。
> **前版パケット**: [[mission-capital-redecision-packet-2026-09-10]] (U1 は [[u1-mission-redecision-2026-09-17]] で決裁済み。U2 = 本稿 D4、U3 = D3、U5 = D10 に吸収)。
> **記述規律**: 数字は出所併記。凍結 look (E1/ECG/E12/wg G1・G2/rnb forward/sr_anti_hunt forward/E23 OOS) の outcome は計算していない。引用禁止値 (nav_floor fit 現況値 / L1 5000u 前提の現 NAV での M2 寄与 / keeper 控除前 M2 算数 / P5 確率 / 「carry_dip 符号逆」/ 「F4 12-03 確定」/ 「33 分」/ 「agg_kelly block (carry_dip)」) は使わない。Live = `oanda_trade_id != ''` のみ。

略号: KB = `knowledge-base/wiki/`、REG = `KB/decisions/prereg-trigger-registry.json`、memo = [[path-to-win-decision-memo-2026-09-20]]、reassess = [[path-to-win-reassessment-2026-09-22]]、template = [[lot-ladder-template-2026-08]]、rederivation = [[monthly-target-rederivation-2026-07-10]]、G1 = `knowledge-base/raw/analysis/path-to-win-2026-09-20/` 系の資本監査 (reassess §1 行 1–2 に統合済み)。

---

## 0. TL;DR

現 NAV ¥275,516.83 (`GET /api/oanda/heartbeat` 2026-09-22T06:19Z) では、**不動点が 3 脚で成立**している: (i) 資本 — OANDA Gold 維持 keeper 26 RT × ¥80 = **¥2,080/月 = 0.755%/月 > M2 +0.5%** (`KB/index.md` L149 tx 照合 / `modules/status_volume_keeper.py:298`)、(ii) エッジ容量 — 制約 4.2 (≤2.5% NAV、template L65) ∧ disaster SL 150p ⇒ units ≤ NAV/60 ⇒ **wg 単独の %NAV 寄与は NAV・keeper・rung に無関係に ≤0.166〜0.432%/月** (reassess §1 行 2)、(iii) 転換 — L0→L1 の錠 G3 (live N≥30 ∧ mean>0 ∧ WR≥35% ∧ disaster 0、template §5) を満たす live 可能セルは **0** (`tools/m1_clean_live_monitor.py --strong` 09-22: M1_STRONG 0 cells)。この 3 脚は Claude の $0 施策空間では 1 本も外れない。**time-to-M2 を ∞ から有限にする前提は D3 (U3 入金 → L1 の算数が閉じる NAV: JPY leg 単独 rung なら ¥300,000、wg 3 leg 一律 rung の現契約 [card L51 単一 lot 定数 ∧ L53 全 leg 執行] なら binding leg = USD-quote の ¥472,800 — D3 補項 (a)) **∧ D2(i)=(a)** (DD lever 0.2x を carve-out rung に乗算しない — 無回答なら code は L1 5000u × 0.2 → floor 1000u に潰す [`demo_trader.py:7571–7578`、D2(i) 既定欄] ので入金しても §3.4 の L1 容量は出ない; 代替は 0.2x 解除 = JPY 台帳 +¥6,178/+¥27,725 の clean live 実現) の 2 つ。D1 (M2 会計定義) は有限化の必要条件ではなく、有限化後の目標サイズを変える** (@¥300k [JPY leg 単独 rung]: A 現行 keeper 込みで 5〜8 本 / B edge-only で 2〜4 本; @¥472,800 [wg 一律 rung]: A 6〜9 本 / B 4〜5 本 — **「本」= wg 級 3 leg 一括ストリーム (pooled 2.1〜3.28 events/月)、D2(ii) 推奨 (c) の type×pair×dir 単位では約 3 倍** (@¥300k B 6〜10 / A 14〜22)、§3.4 — D3 ∧ D2(i)=(a) だけでも A のまま有限) — で、有限化後も時計は G3 が binding (最速セル N≥30 は **D5 の分岐に依存**: (b) as-placed N 継続なら 2026-11-18〜2027-02-07、推奨 (a) 宣言契約復元なら宣言セルの N は復元日から 0 再起動 = 復元日 + 107〜180 日 — §3.4; 2 本目 2027-04+)。**無回答の既定挙動** (実装どおり): 何も起きず、余裕 ¥13,516.83 の 15.4%/月を keeper が消費し続け、F4 資金時計 (REG `project-falsification-f4-nav-floor-clock`) は **fit 推定器ベースで 2026-12-04〜2027-01-08 の幅**で発火 (`tools/nav_floor_projection.py:39,106–120` は行数 ≥7 で fit のみ書く、audit_default「12-03」は書き手の値ではない)、Claude はその時点で record として再上程する (執行はしない)。**10 月・11 月の keeper 支出 ¥4,160 (= 1.51% NAV) は返答期限 11-30 より前に支出が確定する** — 決裁を遅らせるコストは月 ¥2,080 で、これは選択でなく既定の消費である。

---

## 1. 前提条件 (D1〜D12 の返答より先に確認が必要な 2 項目)

### UD1. Gold 算入の画面確認 (期限 2026-09-23、10-01 を待たない)

| 項目 | 内容 |
|---|---|
| 問い | OANDA JP ステータス画面「今月の取引数量」に、9 月 keeper 26 RT ($520,000、同一秒自己往復、`tradeClientExtensions.tag="SVK"`) が **算入されているか**。表示が GOLD 見込みか SILVER 見込みか |
| なぜ今日読めるか | status 頁「毎営業日判定・順次適用・翌月末まで維持」(oanda.jp/lab-education/status/ 2026-09-22 GET、reassess §1 行 8) — 10 月 1 日を待つ必要がない |
| 返答 | `UD1: GOLD` / `UD1: SILVER` / `UD1: 不明` |
| GOLD なら | keeper 設計どおり 10 月 run (¥2,080) 実行。本パケット全項目が有効 |
| SILVER なら | 同一秒自己往復は出来高非算入 = 9 月 ¥2,080 は sunk、10 月 API 停止 (FAQ 1730、token 再発行 + 最短 1 ヶ月)。live 系の D5/D6/D7 は前提消滅、D3 は (ii)/(iii) + 再入場経路に縮約。**本パケットは v0.1 として書き直す** |
| 無回答の既定 | keeper は 10 月 run を実行する (設計どおり)。KB には「Gold 10 月維持は未実証」が残る |

### UD3. M1 レバー (user 手動出来高の同一会員別口座化) の一次確認 — **09-01 案 A の再決裁である**

- **何か**: OANDA 会員ステータスは FAQ 1730「会員ステータスが Gold 以上」/ status 頁「お客様の前月のお取引数量」と **会員 (お客様) 単位**の文言 (2026-09-22 GET)。user が外部業者で行っている USD_JPY 手動売買 (MEMORY `user_manual_edge_usdjpy_carry_2026_08_12` 7 週 N=247 往復) を **同一会員の別 OANDA 口座 (system 口座ではない)** に置けば、Gold 出来高が keeper なしで充足され、system 口座の NAV/M2 母集団を汚さずに必要 gross 1.255% → 0.5% (2.51 倍圧縮) になり得る (reassess §2)。
- **なぜ「再決裁」か**: [[status-volume-keeper-2026-09-01]] で user は **案 A (自動 keeper)** を選び、[[live-frequency-and-oanda-status-survival-2026-09-01]] L36 の **案 B (user 手動出来高)** を退けた。M1 は案 B の変種 (system 口座でなく別口座) なので、09-01 決裁の上書きになる。
- **unverifiable 2 点**: (a) 複数口座の出来高が会員単位で合算されるか — status 頁に「合算 / 複数口座 / 口座単位」の語 0 件。(b) user 側コスト = spread 差 (0.8 銭 − s0) × 出来高 で、上界は $500k 相当 250,000〜260,000 units×RT × 0.8 銭 = **¥2,000〜2,080/月** (= keeper と同額が上界、s0 ≥ 0)。swap/financing 差・個人口座の証拠金・units 下限 (≥1,634u/RT で $500k 充足) は未算入。
- **効くもの / 効かないもの**: 必要 gross% の圧縮には効く。**clock には効かない** (G3 binding、L0 では keeper=0 でも 137.8p/月 @1000u が必要)。
- **返答**: `UD3: 確認する` (→ D3 に第 4 選択肢 (iv) を追加) / `UD3: 見送り` (09-01 案 A 維持)。期限 2026-10-31 (11 月 run に効かせる場合; 10 月 run は ~10-13 完了で間に合わない)。無回答 = 案 A 継続。
- **問い合わせ文案 (user が OANDA サポートへ送る用、Claude 起草)**:

> 件名: 会員ステータス判定における複数口座の取引数量の取り扱いについて
>
> お世話になります。会員番号 [____] の [氏名] です。貴社の会員ステータス制度 (シルバー/ゴールド/プラチナ…) について 2 点確認させてください。
> 1. 同一会員が NY サーバー口座と東京サーバー口座 (または複数の NY サーバー口座) を保有している場合、ステータス判定に用いる「前月のお取引数量」は **会員単位で合算**されますか、それとも **口座単位**で判定されますか。
> 2. 合算される場合、東京サーバー (MT4/MT5) 口座の取引数量も、NY サーバー口座のプロコース REST API 利用条件 (ゴールド以上) の判定に含まれますか。
>
> 以上、よろしくお願いいたします。

---

## 2. 決裁項目 D1〜D12 + D15

書式: 問い / 選択肢 / **Claude 推奨** / 根拠 (2–4 行) / 無回答時の既定 (実装どおり) / 期限。**D1・D3・D4・D5 は user 専権** — 推奨は「一言で返答できる形」に整えたもので、決裁の代替ではない。

| id | 問い | 選択肢 | Claude 推奨 | 根拠 | 無回答時の既定 | 期限 |
|---|---|---|---|---|---|---|
| **D1** (user 専権) | **M2 会計**: M2 「+0.5%/月」の分母・分子に keeper を含めるか | **A** = 現行 (NAV 実現・keeper 込み) 維持、必要 gross 1.255% を rederivation §4 / roadmap KPI 表に併記 / **B** = edge-only に estimand 変更 (keeper は資金時計で別計上、R1) | **B** — ただし **A の 1.255% 表 (§3) を常に併記**する条件付き | (1) A は「生存の会計」、B は「エッジの会計」で測るものが違う。M2 の目的 (rederivation L44: M1 → 2 セル → M3 の橋) はエッジの存在確認であり、Gold 維持費は口座の存続条件 = 資金時計側の変数。(2) A のままだと必要セル数が NAV に依らず keeper (JPY 固定額) で押し上げられ、@¥300k で 5〜8 本 (§3.4、wg 級ストリーム単位; pair セル単位では 14〜22 本) = M3 の「5 セル」と同じ本数を M2 に要求する倒錯が起きる。(3) **倒錯 caveat の反対側**: B は「M2 達成に見えて口座残高は増えない」を許容する定義なので、A の表を併記し、資金時計 (F4) を B の外で独立に読む。(4) 読み手: A は broker NAV 30d Δ (現在**未計測**、broker tx 起点が必須) / B は全 clean live 30d = −27.2p ≈ −0.086〜−0.099% (risk dashboard 09-22)。現行 M3b +0.099% は正 EV セルのみの winner-selected 診断量で、A でも B でもない (`m1_clean_live_monitor.py:523–531`) | 現行 A のまま。必要 gross 1.255% が定義文書に未反映の状態が続く | 2026-11-30 (D1〜D4 は先行返答可) |
| **D2(i)** | **M2 定義の内部不整合 — ラダー文言 vs carve-out 非乗算**: rederivation L44「0.2x→1000u→5000u」と template L73「グローバル DD lever は rung units に乗算しない」のどちらが SSOT か。**これは user 決裁 2 件の衝突**: 07-03 P0-1 ([[fable5-phase-a-p0-fixes-2026-07-03]]、`modules/demo_trader.py:7571–7578` edge-cell lot × `_dd_lot_mult`、floor 1000u) vs 08-05 template L73 | (a) template L73 を SSOT (L1 開通時から carve-out rung に DD lever 非乗算、07-03 P0-1 は非 carve-out に限定) / (b) rederivation 文言を SSOT (L1 の前に 0.2x 再基準化 = env/kv 操作 + JPY 台帳の user 決裁が critical path) | **(a) L73** | (1) 今日は無害 (5000u × 0.2 = 1000u → floor 1000u で L0 と同値) だが、**L1 開通と同時に binding** になり、G3 を通ったセルにだけ開く L1 を 0.2x で 1000u に戻すと昇格が無意味になる。(2) carve-out の標準形は「lever 免除 + 専用降格 gate (§6 D4) 併設」(template L73)。防御は D4 ポートフォリオ降格が代替する。(3) (b) を採ると JPY 台帳 (Track C D-b、[[track-c-capital-plumbing-decision-packet-2026-07-28]]) の解除条件 +¥6,178 (0.4x) / +¥27,725 (1.0x) の clean live 実現が L1 の前提になり、30d −27.2p のペースで到達不能。(4) 07-03 P0-1 の趣旨「固定 lot にも口座防御」は非 carve-out セルで維持する | code の現状 = (b) 的挙動 (`:7571–7578` は乗算する)。L1 開通時に 5000u が 1000u に潰れる | 2026-11-30 |
| **D2(ii)** | **「2 セル以上」の単位**: type か type×pair×dir か。相関セル (全 USD_JPY long) で満たせるか | (a) type / (b) type×pair×dir / (c) (b) + 同一ペア同方向は 1 と数える | **(c) type×pair×dir、同一ペア同方向の相関セルは 1 と数える** | (1) 現行 live 候補 (carry_dip / kalman / #29 BoJ レグ) は全て USD_JPY long で `per-pair 1 position` + `hedge_block` (system-reference L100) により **同じ 1 スロットを排他的に予約**している — 2 type あっても同時に建たないので分散寄与ゼロ。(2) wg の 3 leg (USD_JPY/AUD_USD/EUR_USD) はペアが異なるので (c) では別セルとして数え得るが、**同一イベント (週末ギャップ) を共有する**ため相関は高い — D3 補項 (4.2 多 leg 解釈) と結合して裁定する。(3) (a) は wg 1 type で恒久に 1 セル、(b) 無条件は USD_JPY long の重複計上を許す | 単位未定義のまま。M2 判定器は書けない | 2026-11-30 |
| **D3** (user 専権) | **U3 = floor 前決裁点**: 入金 / 縮退 / 停止 | **(i) 入金** (額は user) / (ii) 縮退 (keeper 停止 → 翌月〜翌々月の Silver 判定で API 停止 [当月 $500k 到達済みなら Gold は翌月末まで維持 — status 頁「翌月末まで維持」] = live 執行・OANDA テレメトリ停止、E1 ingest は Myfxbook で継続、shadow は Massive/yfinance fallback で劣化継続) / (iii) 停止 / (iv) M1 レバー (UD3 確認後のみ) | **(i) 入金** — **額は UD1 = GOLD ∧ E1 verdict (10-15) 後に決める**。最小参照点 = L1 開通差額 + keeper 12 ヶ月 **¥24,960** (12 × ¥2,080) で **2 値**: **JPY leg 単独 rung** (per-leg rung 実装 = wg 専用 rung 定数 R1 が前提、template L114) なら差額 **¥24,483** (¥300,000 − ¥275,517) → **≈ ¥50,000** / **wg 3 leg 一律 rung の現契約** (card L51 単一定数 ∧ L53 全 leg 執行) なら差額 **¥197,283** (¥472,800 − ¥275,517) → **≈ ¥222,000**。どちらが参照点かは D3 補項 (a) の per-leg rung 可否で決まる (§6-7) | (1) 入金は time-to-M2 の **clock には効かない** (G3 binding) が、必要 gross% を圧縮し L1 の算数が閉じる条件を 1 つ外す唯一の分母レバー (reassess §2) — ただし L1 5000u の実効には D2(i)=(a) が併せて必要 (無回答なら 0.2x で 1000u、D2(i) 既定欄)。(2) (ii) は floor 到達を回避するが「攻撃手段そのものの喪失」(4 原則 #1/#4) で、live N の時計が止まり F2/F3 は自動 TRIGGERED。可逆性 (再入場 = token 再発行 + Gold 再取得 = 最短 1 ヶ月 + keeper 1 ヶ月分) は 11-15 までに追補。(3) (iii) は U2 で「研究プロジェクト」を明示するのと同値。(4) E1 PASS (点推定 4%、Wilson 0.7–19.5%) なら第 2 セルの USD-quote 可能性で L1 開通 NAV が ¥472,800 に変わり得るため、額の確定は verdict 後 | 何も起きない。余裕 ¥13,516.83 を 15.4%/月消費、F4 fit 発火 12-04〜01-08 で Claude が record 再上程 (執行なし)。10・11 月 ¥4,160 は期限前に確定支出 | **2026-11-30** |
| **D3 補項** | **制約 4.2「セル単体イベント」の多 leg 解釈** (未裁定 — template L167 は単 leg の worked example): wg 3 leg 同時 disaster を 1 イベントと読むか | (a) 単 leg で 4.2 を読む — 開通 NAV は leg の quote 通貨別 (JPY leg ¥300,000 / USD-quote leg ¥472,800 @157.6)。wg は 3 leg 全執行 ([[weekend-gap-fade]] L53 選択的執行禁止) ∧ lot は `WEEKEND_GAP_FADE_MIN_LOT` 単一定数 (card L51、template L114) なので **wg 全体を L1 に上げる開通 NAV は binding leg の ¥472,800**。¥300,000 は「JPY leg のみ L1、USD-quote leg は L0 据え置き」の per-leg rung (D2(ii) (c) の帰結、実装 = wg 専用 rung 定数 R1 + code) を採る場合に限る / (b) 3 leg 同時 = 1 イベント (USD_JPY ¥7,500 + AUD_USD / EUR_USD 各 ¥11,820 [5 × ¥15.76 × 150p、@157.6、`lot_ladder_calc.py:87–101` quote 通貨別 pip 値] = **¥31,140** → L1 開通 NAV **¥1,245,600** @157.6。旧記載「3 × ¥7,500 = ¥22,500 → ¥900,000」は USD-quote 2 leg を JPY pip 値で数えた誤りで、¥900,000 では 3.46% = 4.2 違反) | **(a) 単 leg で 4.2 を読む** (L167 前例) — ただし wg の開通 NAV は per-leg rung なしの現契約では ¥472,800 と書く (¥300,000 と書かない); 加えて 3 leg 同時 worst-case ¥31,140 (@L1、quote 通貨別 pip 値、USD_JPY レートに比例) を **4.4/4.5/4.6 側で別途評価**し packet に必記 | (1) template L167 の worked example は単 leg で計算され、multi-pair の同時性は 4.4 (証拠金) / 4.5 (exposure cap) が担う設計 (L60–L70)。(2) (b) を採ると wg の L1 は ¥1,245,600 (@157.6) まで開かず、入金の参照点は差額 ¥970,083 = 単 leg JPY ¥24,483 の 39.6 倍 / 単 leg binding USD-quote ¥197,283 の 4.9 倍になる — その決裁は U2 と同時にすべき。(3) 4.4/4.5 の多 leg 同時評価は未計算 (reassess §9-15) — 確定版 (10-08) までに Claude が計算して追補 | 未裁定のまま。L1 packet 生成時に `lot_ladder_calc.py` は単 leg で計算する (現実装) | 2026-11-30 (D3 と同時) |
| **D4** (user 専権) | **U2 = 資本スケール上限** を 1 数字で凍結 | 数字 (¥) | **user の数字** — 参照表: 現 NAV ¥276k → M3 (+2〜3%) 月次 **¥5,510〜8,266** / ¥1M → ¥20k〜30k / ¥10M → ¥200k〜300k (2〜3% × NAV、前版パケット §U2 表の ¥6,500〜9,700 は memo §3 で不一致訂正済み) | (1) lot ladder L2+ の昇格・exposure cap 改定の分母。凍結しない = 「資本投入を予定しない研究プロジェクト」の暗黙決裁 (前版 §U2)。(2) 現 NAV で M3 を完全達成しても手動キャリー (+0.3〜0.4%/月・工数ゼロ、MEMORY `user_manual_edge_usdjpy_carry`) との差は月 ¥5〜7k。(3) D3 (i) の額の上界を規定する | U3 の上界不定、有償 probe (U4 (a)) は自動 NO、非 FX (U4 (c)) は起案不可 | 推奨 2026-10-15 (11-30 まで) |
| **D5** (user 専権) | **carry_dip disposition** (08-05 から未決、08-07 に user 決裁事項と分類、[[usdjpy_carry_dip_accumulator]]) | (a) 宣言契約復元 (SL 150p / TP 80p / trail・BE 免除 / `_QUICK_HARVEST_EXEMPT` / storm guard 着地後) → 宣言セルの N を再起動、as-placed N=14 は別セルとして凍結 / (b) as-placed を新宣言 (BT 根拠なし、Rule 1 例外再承認) / (c) LIVE 停止・shadow 継続 / (d) 現状維持 | **S3 (14 本 one-off 突合、10-06) の結果待ち**。分岐: **両 estimand (demo `pnl_pips` ∧ broker realized) で deduped LIVE EV<0 なら (c)** — ただし demo 側は REG 凍結 R2 (N≥10 ∧ demo EV<0) が D5 を待たず autopilot で先に発火する (lot↓ or LIVE 停止・shadow 継続) ので、その場合 D5 は「shadow 継続下で (a) 復元を起案するか恒久 (c) か」に縮約; **broker のみ EV<0 (demo EV≥0)** なら凍結 R2 は不成立 = autopilot 執行不可 (estimand 差し替え)、乖離を記録して **(a) を R1 pre-reg で起案** (as-placed 戦略の broker 負は復元後の宣言セルの証拠にならない); **両方 EV≥0** なら **(a) を R1 pre-reg で起案** (autopilot 禁止) | (1) 突合済み 7 本は demo −16.4p / broker −41.1p で**両方負**、demo 簿 +103.0p の正符号は未突合 3 本 (+130.9p) が担う — 「符号逆」は refuted、結論は 14/14 でしか出ない (reassess §1 行 4)。(2) SL as-placed 9.8–28.5p vs 宣言 150p = 積まれている N は宣言と別戦略の N で、promote にも falsify にも使えない。(3) (a) は 1 敗 = ¥1,500 = 余裕の 11.1% の tail を持ち、storm guard (memo §4.1-2) の着地が前提。(4) REG `carry-dip-v3-revival-watch` の R2 事前規定 (deduped LIVE N≥10 ∧ EV<0 → lot↓ or LIVE 停止、shadow 継続) は demo `pnl_pips` 基準で凍結されており ([[t5-restore-eval-and-carrydip-revival-2026-08-10]] §事前規定 R2 判定規律 (b)「outcome / pnl_pips で勝敗」)、現状 N=14 EV +7.36 で不成立 — broker のみでの autopilot 執行は estimand 差し替えで不可。**逆に broker との conjunction を predicate に足すのも不可** — 凍結 predicate の黙った厳格化で、demo EV<0 ∧ broker EV≥0 のとき認可済みの損失停止 (R2) が塞がる | 現行 live 継続 (d)。**R2 autopilot の predicate は REG 凍結値のまま不変** = deduped LIVE (`oanda_trade_id!=''` ∧ `dedup_violation!=1`) N≥10 ∧ demo `pnl_pips` EV<0 → lot↓ or LIVE 停止 (shadow 継続)。broker realized は凍結 predicate の外 — broker のみ EV<0 は執行せず記録 (D5 材料)、demo EV<0 (N≥10) は broker 符号に関わらず発火する (conjunction を要求しない)。現状 demo N=14 EV +7.36 で不成立 | 2026-11-30 (REG backstop) |
| **D6** | **ps_aud_jpy** (08-12 user 決裁 = demote 見送り・watchdog 委任、[[price-shock-rev-aud-jpy-h1-long]]): 再上程 | 現状維持 (09-30 regate に委任) / shadow 降格 / 送信保留 (bracket 診断完了まで) | **09-30 regate (REG `ps-carveout-regate-post-172`) に委任** | (1) 08-12 決裁を無回答・default で反転させない。(2) regate は live N≥10 → EV/Wilson、N<10 → stale 分岐が事前規定済み。(3) bracket 不一致 (TP +1,088p / SL −130p) の**診断**は R3 で先行可 | 09-30 regate の結果どおり | 2026-09-30 (regate) |
| **D7** | **kalman postfill packet (DRAFT、[[kalman-d7-carveout-postfill-packet-2026-09-17]]) の承認** | 承認 / 修正指示 / 却下 | **承認** — estimand = **broker realized net** で凍結 + §6-6 に **as-placed SL ≈13.8p vs 宣言 1.5×ATR ≈21.8p の非適合を注記** (契約表は「trail なし・SL 1.5×ATR・winner ride」の現宣言を維持、trail 込みは新宣言 Rule 1) | (1) 初 fill #859468 (09-10、demo +8.2p / broker +¥91) で DRAFT の事後義務が発生済み。(2) broker realized を estimand にしないと D5 と同型の demo/broker 乖離問題を再生産する。(3) 非適合は D5 の EXEC_CONTRACT 検知器 (memo §4.1-4) の counterfactual pin の 1 つ | DRAFT のまま。R2 判定 (REG `t9-kalman-d7-live-n10-ev-check` 12-09) は demo 簿で読まれる | 2026-11-30 |
| **D8** | **4 原則 #3 の解釈**: `velocity_down` ガード (carry_dip 11 日台帳で block 4 = 最多、shadow 行も残さない) を LIVE 側 winning-location フィルタとして容認するか、shadow 分母消失 (原則 #3 前段) を許容するか | 容認 (現状) / shadow 行保存を要求 / ガード撤去 (R1) | **LIVE winning-location として容認、ただし shadow 行保存を R3 で要求** | (1) 原則 #3 後段「LIVE 側は勝てる場所で勝つ条件だけ転送」に適合。(2) 前段「Shadow 分母は削らない」に反して block 時に shadow 行が残らない (`demo_trader.py:6350–6389` 系、`_block` は行を書かない) — 分母保存は code 修正 (R3、live 経路変更なし) で満たせる。(3) 11 日ゼロ自体は統計的に異常でない (Poisson P=0.045〜0.16) ので「設計衝突」と断定しない | 現状維持 (shadow 分母消失を記録し続ける) | 2026-11-30 |
| **D9** | **研究スキャン cadence** | 月次維持 / 四半期 + イベント駆動 (WIP 緊急トリガ維持) | **四半期 + イベント駆動** | (1) 着手可能な能動 family 0 本 (#27 FAIL 09-18)、base rate 4% [0.7–19.5%] で月次スキャンの期待発見数 <0.1。(2) REG `edge-supply-scan-monthly` の「0 本なら期日を待たず臨時 R3」規則は維持 (イベント駆動側)。(3) 容量 [10.5, 19] セッション/30 日の需要削減 | 月次 (10-18 第 6 次) のまま | 2026-11-30 |
| **D10** | **U5 残余 = 固定費台帳** (数字は user)。⚠️ 前版 U5 の「`fx-codex-runner` Suspend」は **stale — Render 上 2026-09-10 に user が suspend 済み** (facts §A) | 月額を入力する / しない | **台帳の器を Claude が作る (R3)、数字は user 入力** — 項目: Render Pro / MASSIVE / Claude / (codex-runner = ¥0 済) / その他 | (1) 固定費合計は KB に無い (memo §6)。(2) M3 完全達成の月次期待 (¥5,510〜8,266 @現 NAV) と固定費の大小は edge の有無と無関係に U2 の判断材料 | 台帳は空欄のまま | 2026-11-30 |
| **D11** | **M1_STRONG / F3 の estimand** (三重不一致: REG「PnL>0」/ monitor 母集団 = demo `pnl_pips` / monitor STRONG = EV≥+1.0 ∧ Wilson_lo>0) | 閾値 (EV>0 / EV≥+1.0 ∧ Wilson_lo>0) × 母集団 (demo `pnl_pips` / broker realized) | **セル定義 EV≥+1.0 ∧ Wilson_lo>0 を primary — ただし採用 = REG F3 `condition` (字義「N>=30 で PnL>0」) の改定を伴う (U7 user 承認 2026-09-10 事項の変更、11-10 まで; 改定前は既定欄の REG 字義が判定 predicate)。母集団は broker realized が全 live セルで揃うまで両基準併記** (N≥30 到達後の基準選択は禁止 — pre-reg 規律) | (1) EV>0 単独は N 不問で 45 セルが該当 (winner-selected)、durable の定義にならない。(2) 母集団を今 broker に片寄せすると D5 の 14/14 突合前に F3 (2027-03-31) の estimand を動かすことになる。(3) 両基準併記は `m1_clean_live_monitor.py --strong` に broker realized 列を足す R3 (memo §4.1-10) で実装可。D14 は新設せず本項に統合 (reassess §3 Rank 1)。(4) REG entry 自体が内部不一致 — `condition` は「PnL>0」、`message` は「M1_STRONG 該当セル 0」、`reachability` は monitor 強定義 readout (`prereg-trigger-registry.json:741–745`)。判定 predicate は `condition` の字義。monitor の「正EV literal」列 (`m1_clean_live_monitor.py:421–422`) も Wilson_lo>0 を足しているので REG 字義の読み手ではない | **REG 凍結 `condition` の字義 = clean live (`oanda_trade_id` 非空 ∧ `dedup_violation!=1`) N≥30 ∧ PnL>0 (demo 簿) で F3 を読む** (`prereg-trigger-registry.json:741`)。monitor 強定義 (EV≥+1.0 ∧ Wilson_lo>0) は readout 併記であって判定 predicate ではない — 例: N≥30 ∧ EV +0.5 のセルは REG 字義では F3 resolve、強定義では非該当 = 2027-03-31 に逆の結果。無回答なら REG 字義が勝つ (強定義を primary にするには REG 改定が先) | 2026-11-10 (carry_dip N≥30 の D5 分岐横断の最速 = (b) as-placed 継続 11-18 の前; 推奨 (a) 復元なら到達はさらに後ろだが期限は最速分岐で置く) |
| **D12** | **CC BY-NC (TDW/WCB) の live 転送資格** — 研究利用は E23 pre-reg §0-4 で可 (決裁不要) ([[e23-cb-text-explore-prereg-2026-09-10]]) | (i) live 転送も許可 / (ii) license-free 再実装を条件 | **(ii) license-free 再実装を条件** | (1) NC ライセンスの商用 (live 送金) 利用はライセンス違反リスク。(2) #29 S1 census は license-free 凍結 lexicon を primary にする設計 (memo §4.1-8) と整合。(3) 急がない — census 結果が出るまで live 転送の対象自体が無い | 転送資格未裁定 (研究利用のみ継続) | 2026-11-30 |
| **D15** | **floor バッファ ¥12,000** (floor ¥262,000 = OANDA 残高条件 ¥250,000 + バッファ、`tools/nav_floor_projection.py:34` / `status_volume_keeper.py:74` / `anomaly_watcher.py:1011`) を縮小するか | 維持 / 縮小 (例 ¥3,000 → keeper-only runway +4.3 ヶ月) | **維持 (縮小しない)** — autopilot 禁止事項として明記 | (1) バッファの導出は KB に無い (meta-audit §2 goals-1「監査バッファ」) が、L0 1 イベント worst ¥1,500 (JPY) / ¥2,364 (USD-quote)、wg 3 leg 同時 @L0 = ¥1,500 + 2 × ¥2,364 = ¥6,228 (quote 通貨別 pip 値、旧 ≈¥5,900 を訂正)、keeper 決済レグ失敗時の裸 10,000u 露出 ¥6〜10k (memo §2.4) の参照点はいずれも ¥12,000 の内側。(2) 縮小は runway のみで time-to-M2 に効かない。(3) F4 凍結トリガ + 3 定数の改定 = 凍結値変更。(4) **floor の estimand**: FAQ 1730 は「NY サーバーの口座残高」= balance、keeper guard と F4 CSV は NAV — 建玉ゼロの今は一致、live 建玉時は決済後 balance で読む | 維持 | — (record) |

**D13 (Gold 画面確認) は §1 UD1 に統合。D14 (F3 estimand 軸) は D11 に統合。**

---

## 3. 資本算数 (再計算、出所併記)

全て 2026-09-22 の一次値から再計算 (reassess §1 行 1–2 / G1 §2 と一致)。**引用禁止値は使っていない** — 特に「L1 5000u 前提の M2 寄与 (¥1,295/本 等)」は現 NAV では L1 が開かないため無効。§3.4 の L1 算数は **D3 (i) 入金で NAV ≥ ¥300,000 (JPY leg 単独 rung) / ≥ ¥472,800 (wg 3 leg 一律 rung の現契約) になり、かつ D2(i)=(a) で DD lever 0.2x が carve-out rung に乗算されない (無回答なら 5000u → 1000u = L0 と同値) 場合にのみ有効**な条件付き計算。

### 3.1 一次値

| 量 | 値 | 出所 |
|---|---|---|
| NAV = balance | **¥275,516.83** (margin_used 0、open_trade_count 0) | `GET /api/oanda/heartbeat` 2026-09-22T06:19:40Z |
| keeper 9 月 | 26 RT、volume $520,000/520,000、last_rt 09-14T01:01Z | `GET /api/demo/status`.status_volume_keeper 06:18Z |
| keeper 単価 | ¥80/RT (0.8 銭 × 10,000u; 実測 −¥80、稀に −¥70) | `KB/index.md` L139/L149 tx 照合 / oanda.jp/course/spread/ プロコース USD/JPY 0.8 銭 原則固定 (配信率 98.24%、09-22 GET) |
| floor / 余裕 | ¥262,000 / **¥13,516.83** | `tools/nav_floor_projection.py:34` / 算数 |
| 30d clean live | n=9、net −27.2p、friction 45.4p | `GET /api/risk/dashboard` 09-22 (`effective_date_from` 2026-08-23) |
| 制約 4.2 cap | 0.025 × NAV = **¥6,887.92** | template L65 / `tools/lot_ladder_calc.py:34` |
| USD_JPY | 157.6 → USD-quote v1000 = ¥15.76/pip | `lot_ladder_calc.py` 実走 (G1 §2.3) |

### 3.2 keeper と M2 必要 gross

| 量 | 式 | 値 |
|---|---|---|
| keeper 月額 | 26 × ¥80 | **¥2,080** (下限 26 × ¥70 = ¥1,820) |
| keeper % | 2,080 / 275,516.83 | **0.7550%/月** (M2 0.5% の 1.51 倍) |
| cost/$ 出来高 | 0.8 銭 ÷ 2 (新規+決済) | ¥0.004/$ → $500k = ¥2,000。**units・時間帯・回数・銘柄 (EUR_USD は ¥0.0054/$ で悪化) に依存しない** = keeper 設計値変更の効果上限 ¥260/月 |
| M2 net (定義 B) | 0.005 × NAV | **¥1,377.58 = 0.5%** → @1000u (¥10/pip) **137.8p/月** |
| M2 gross (定義 A) | 1,377.58 + 2,080 | **¥3,457.58 = 1.2550%/月** → @1000u **345.8p/月** / @5000u 69.2p |
| 対照 | wg 実効 EV +4.75p × 2.1〜3.28/月 | +10.0〜15.6p/月 @L0 (凍結 +7.90p なら 25.9p) — A の 13〜35 倍、B の 5〜14 倍が要る |

### 3.3 制約 4.2 と L1 開通 NAV

| 量 | 式 | 値 |
|---|---|---|
| L1 5000u worst-case (JPY ペア) | 5000/1000 × ¥10 × 150p | **¥7,500 = 2.72% NAV > 2.5%** → `lot_ladder_calc.py --packet` は N に無関係に **HOLD** |
| L1 開通 NAV (JPY ペア、または wg の JPY leg のみ per-leg rung) | 7,500 / 0.025 | **¥300,000** (差 **¥24,483**) |
| L1 開通 NAV (USD-quote @157.6) — **wg 全体 (3 leg 一律 rung、card L51/L53) の binding 値** | 5 × 15.76 × 150 / 0.025 | **¥472,800** (差 **¥197,283**; memo の ¥450k は ¥15/pip で stale) |
| 4.2 ∧ SL 150p の一般形 | units ≤ 0.025 × NAV / (150 × ¥0.01) | **units ≤ NAV/60** (JPY ペア) — NAV に比例、rung 集合 [1000, 5000, 10000, 30000] の床で潰れる |
| wg 単独 %NAV 寄与の上界 | EV × freq × (NAV/60/1000 × ¥10) / NAV = EV × freq / 60 | **0.166%** (4.75p × 2.1) / **0.260%** (4.75 × 3.28) / **0.432%** (凍結 7.9 × 3.28) — **NAV・keeper・rung に無関係に M2 0.5% 未達** → 第 2 セルは資本額では買えない |
| 現 NAV で L1 が開く disaster SL | 6,887.92 / (5 × ¥10) | ≤137.76p (wg 凍結値 150p は LOCKED、変更は R1 = user) |

### 3.4 @NAV ¥300,000 (D3 (i) 入金後 ∧ D2(i)=(a) DD lever 非乗算、JPY leg 単独 rung) の必要セル数 — 条件付き (wg 3 leg 一律 rung なら @¥472,800 で読む; 「本」= wg 級 3 leg 一括ストリーム)

前提: NAV ¥300,000、L1 5000u (¥50/pip) が実効 (D2(i)=(a); 無回答なら 0.2x で 1000u = L0 と同値で本表は成立しない)、**「1 本」= wg 級の 3 leg 一括ストリーム** (実効 EV +4.75p/event、凍結 +7.90p)、頻度は **pooled** = [[weekend-gap-fade]] L19「~3.28 イベント/月 (3 leg 合計) / 2.07 qualifying 週末/月」— 実測 **N=4 週末/58 日 = 2.1/月 (Poisson 95% CI 0.57〜5.37/月)** で設計 3.28/月と区別不能、点推定 2 つを CI 付きで併記する。**D2(ii) 推奨 (c) の type×pair×dir 単位に換算すると pair 別 event 率は pooled の約 1/3 (等分仮定: 1.093 / 0.70 events/月) → 1 セル ¥/月は ¥259.7 / ¥166.2、必要セル数は B 6〜10 本 / A 14〜22 本 (@¥300k) と約 3 倍になる** — pooled 率を pair セルに掛けると過大評価 (単位を混ぜない; pair 別実測 N は §6-8 で置換)。**wg 3 leg 一律 rung の現契約では L1 開通 NAV は ¥472,800 (§3.3) で、必要 ¥/月は B 0.005 × 472,800 = ¥2,364 / A ¥4,444 → セル単価 ¥50/pip 近似 (保守側; USD-quote leg 5000u は ¥78.8/pip で単価上振れ) で B 4〜5 本 / A 6〜9 本** (3.28: B 3.03→4 / A 5.70→6; 2.1: B 4.74→5 / A 8.91→9; pair セル換算 B 10〜15 / A 18〜27)。

| 定義 | 必要 ¥/月 | 1 ストリーム ¥/月 @2.1 (4.75×2.1×50) | @3.28 (4.75×3.28×50) | 必要本数 (ストリーム単位、pooled) | pair セル換算 (率 ÷3 等分仮定) |
|---|---|---|---|---|---|
| **B** (edge-only) | 0.005 × 300,000 = **¥1,500** | ¥498.75 | ¥779.0 | **2〜4 本** (3.28: 1.93→2 / 2.1: 3.01→4) | 6〜10 本 (1.093: 5.78→6 / 0.70: 9.02→10) |
| **A** (keeper 込み) | 1,500 + 2,080 = **¥3,580** | ¥498.75 | ¥779.0 | **5〜8 本** (3.28: 4.60→5 / 2.1: 7.18→8) | 14〜22 本 (13.79→14 / 21.53→22) |

- **A は M3 の「正 EV セル 5 個以上」と同じ本数 (ストリーム単位; pair セル単位なら 14〜22 本) を M2 に要求する** — D1 推奨 B の根拠 (2)。
- **G3 が先**: L0→L1 は G3 (live N≥30 ∧ mean>0 ∧ WR≥35% ∧ disaster 0) ∧ Wilson_lo > BEV ∧ 4.2 の AND 錠 (template §5)。wg live N=0 (F2 12-31)、carry_dip は宣言契約と別の N。**carry_dip の N≥30 到達日は D5 の分岐に依存する** (rate = 0.282/日 [08-14 以降 11 本/39 日] / 0.167/日、G2 §N 時計): **(b) as-placed を新宣言** → 現在 N から継続 = 2026-11-18 (demo 14 基準、+57 日) 〜 2027-02-07 (突合 7 基準、+138 日) / **(a) 推奨経路 (宣言契約復元)** → 宣言セルの N は復元日から **0 再起動**、as-placed 14 は別セル凍結で G3 に算入しない → 到達 = 復元日 + 107〜180 日 (30/0.282〜30/0.167; 例: 11-30 復元なら 2027-03-17〜05-29) / (c) → N 時計停止 / (d) → N は増えるが宣言と別戦略の N で G3 に使えない (D5 根拠 (2))。いずれの分岐でも 2 本目 2027-04+ → **F3 (03-31) が先に来る** (推奨 (a) では 1 本目より F3 が先)。wg N=41 (Wilson 到達) は leg 基準 13.3–16.7 ヶ月 / 週末基準 21–26 ヶ月 (T_conv は改定後 0/1 で未測定)。
- keeper = M2 になる NAV (定義 A で必要 gross = 1.0%) = 2,080 / 0.005 = **¥416,000**。

### 3.5 資金時計と keeper 支出の確定分

| 量 | 式 | 値 |
|---|---|---|
| keeper / 余裕 | 2,080 / 13,516.83 | **15.4%/月** |
| keeper-only runway | 13,516.83 / 2,080 | **6.50 ヶ月** → 2027-04 上旬 (edge PnL=0 仮定) |
| 10・11 月 run (11-30 前に確定) | 2 × 2,080 | **¥4,160 = 1.51% NAV** |
| F1 (2027-02-05) まで (10〜1 月) | 4 × 2,080 | **¥8,320 = 3.02% NAV**、残余 ¥5,197 @edge 0 |
| F4 fit 発火 | `nav_floor_projection.py` fit (行数 ≥7、窓 60 行) | **2026-12-04〜07 (drift 込み) 〜 2027-01-08 (keeper のみ)** — 2 者独立再現、幅で引用。keeper のみなら順序は F2 (12-31) → E1 2nd (01-06) → F4 (01-08) |
| floor 到達 (= keeper guard skip 点、OANDA 直接条件 ¥250,000 ではない — D15 / §4) | keeper のみ / audit_default 82 円/日 | **2027-03-04〜04-07** の幅 |

### 3.6 M1 レバー feasibility (UD3、unverifiable)

| 量 | 式 | 値 |
|---|---|---|
| user 側追加コスト上界 | (0.8 − s0) 銭 × 250,000〜260,000 units×RT | **≤ ¥2,000〜2,080/月** (s0 ≥ 0) — keeper と同額が上界、s0 が大きいほど安い。swap/financing 差・証拠金は未算入 |
| 必要 units/RT | $500k / (2 × 153 RT/月) | **≥1,634u/RT** (外部業者実績 N=247/7 週 ≈ 153 RT/月、MEMORY) |
| 効果 | 必要 gross A → B 相当 | 1.255% → 0.5% (2.51 倍圧縮)。**L0 の ∞ は解けない** (137.8p/月 @1000u)、G3 も残る |
| 成立条件 | 会員単位合算 | **unverifiable** (status 頁に語 0 件) → UD3 一次確認 |

---

## 4. kill 条件の順序と、各点で真であるべきこと

順序 (reassess §6): **10-01 Gold → 10-15 E1 → 11-30 U3 → {F4 12-04〜01-08, F2 12-31} → 02-05 F1 → {floor 03-04〜04-07, F3 / global-stop 03-31}** (**重なり**: floor が drift 込み端 03-04 側なら floor が先、keeper-only 端 04-07 側なら F3 が先 — 順序は実測 floor 日で条件付け、F4 と同じ扱い)。「12-03」「33 分」は書かない。

| 期日 | 条件 | REG id / 出所 | その時点で真であるべきこと (検知器が嘘をつかない条件) | 本パケットとの関係 |
|---|---|---|---|---|
| **2026-09-23** (即日) | UD1 Gold 画面確認 | §1 | 9 月 $520k が算入されている表示。SILVER なら v0.1 書き直し | 前提条件 |
| **2026-10-01** | Gold 10 月判定 (record) | REG 10-01 記録 / memo §4.1-13 | GOLD 維持の KB 記録が存在する (現在は「見込み」のみ) | D5/D6/D7 の前提 |
| **2026-10-08** | E1 cutoff + **本パケット確定版** | [[e1-positioning-contrarian-prereg-2026-07-16]] §2.5 / 本稿 | 凍結 export が 1 回だけ実行され sha256 が raw 側にある。パケット v1 は stale 訂正済み・両基準併記・引用禁止値ゼロ | 確定版期限 |
| **2026-10-15** | E1 first look verdict | REG `e1-prereg-verdict-deadline` | §8 手順のみで解錠。modal = UNDERPOWERED (事前宣言) → second look 2027-01-06。PASS なら D3 額と第 2 セル (USD-quote L1 ¥472,800) を更新して v1.1 | D3 額の確定入力 / D4 推奨期限 |
| **2026-11-10** | D11 両基準併記の実装期限 | 本稿 D11 | `m1_clean_live_monitor.py --strong` に broker realized 列。carry_dip N≥30 (D5 分岐横断の最速 = (b) 11-18; 推奨 (a) では復元日 + 107 日以降) の**前**に基準が凍結されている | F3 の estimand |
| **2026-11-30** | **U3 (D3) 期限** + carry_dip backstop + D1〜D12 返答 | 前版 §U3 / REG `carry-dip-v3-revival-watch` | 返答があれば Claude が KB 反映 (定義文書改定 / 資本上限凍結 / registry) を自走。無回答なら §0 の既定挙動 | 本パケットの期限 |
| **2026-12-04〜2027-01-08** | F4 資金時計 (days_to_floor ≤90) | REG `project-falsification-f4-nav-floor-clock` / `nav_floor_projection.py:106–120` | 発火日は fit ベースで幅を持つ。**推定器を「keeper 決定論分 + edge 30d 実測」に分解する修正 (sprint S-F4) が着地していれば幅は縮む** — 着地前は幅で引用。無回答時は Claude が record 再上程 | 既定挙動の発動点 |
| **2026-12-31** | F2 wg live conversion | REG `project-falsification-f2-wg-live-conversion` | wg live N=0 なら「PASS→live 変換未実証」正式認定。**per-event fill 率が測定されている** (現在 改定後 0/1、未測定) こと。09-27 / 10-04 / 10-11 の G0' event が分母に入る | D2(ii) の第 2 セル候補 (wg) の生死 |
| **2027-01-06** | E1 second look | E1 pre-reg §5 | UNDERPOWERED 分岐の唯一の再判定点。PASS なら実装 pre-reg (D4 様式) → live N≥30 は 2027-05〜09 | D3 額の再更新 |
| **2027-02-05** | F1 supply space | REG `project-falsification-f1-supply-space` | E1/ECG/E12 から OOS PASS 0 → 三択 (有償 / venue / 終了) を **venue feasibility 付き**で起票できる状態 (memo §4.1-12 は未着手) | D4 (U2) が決まっていないと有償 probe は自動 NO |
| **2027-03-04〜04-07** | floor ¥262,000 到達 (keeper 継続 ∧ D3 無回答時) | §3.5 / D15 | **ここに来る前に D3 が決まっている**こと。**到達そのものは API 停止ではない**: ¥262,000 = OANDA 残高条件 ¥250,000 (FAQ 720/1730、[[live-frequency-and-oanda-status-survival-2026-09-01]] L8) + 自前バッファ ¥12,000 (D15) で、到達時に起きるのは keeper guard の発注 skip のみ (`status_volume_keeper.py:234–235` nav_floor)。API 停止は間接経路 — keeper 停止 → 当月出来高 <$500k → 翌月 Silver 判定 → REST API 停止 (FAQ 1730)。Gold 維持期限「翌月末まで」の位相で停止日は **04-01 か 05-01 か未確定** (reassess §4 Rank 1)。残高 ¥250,000 割れ (直接条件) はさらに ¥12,000 下 | D3 の物理的期限 (直接条件は残高 ¥250k、実効期限は keeper guard skip 月)。**F3 (03-31) と重なる**: drift 込み端 03-04 なら floor が先、keeper-only 端 04-07 なら F3 が先 |
| **2027-03-31** | F3 M1 durable cell / global-stop quarterly | REG `project-falsification-f3-m1-durable-cell` / `project-global-stop-quarterly` | F3 の estimand が D11 で一意 (閾値 × 母集団)。D11 無回答なら判定 predicate は REG `condition` 字義 (clean live N≥30 ∧ PnL>0、demo 簿) — monitor 強定義ではない。発火は kill でなく段階設計再導出 — 発火前提で M1→M2→M3 の書き直し準備 | D11 |

**順序が反転する条件**: floor (03-04〜04-07) と F3 (03-31) は重なる — keeper のみなら floor 04-07 で F3 の後、drift 込みなら 03-04 で F3 の前。また keeper のみ burn (drift 0) なら F4 は 2027-01-08 で **F2 (12-31) → E1 2nd (01-06) の後**に来る。この場合「F4 で U3 を強制起票」は F2 の帰結 (wg 第 2 セル消失) を見た後になる — D3 を 11-30 に返す理由はここにある。

---

## 5. 返答書式

各項目を 1 行で。D1〜D4 のみ先行返答でも分母は有限化できる。

```
UD1: GOLD / UD3: 確認する
D1: B / D2: (i) L73 (ii) type×pair×dir / D3: (i) ¥50,000 (補項: 単 leg) / D4: ¥1,000,000 / D5: S3 待ち→分岐どおり / D6: 09-30 委任 / D7: 承認 / D8: 容認+shadow 保存 / D9: 四半期 / D10: Render ¥__ MASSIVE ¥__ Claude ¥__ / D11: EV≥1.0∧Wilson 両基準 / D12: (ii) / D15: 維持
```

「推奨どおり」と 1 語で返された場合の解釈 = 上記例の **D3 の額と D4 の数字と D10 の金額を除く全項目**を Claude 推奨で確定し、D3 額 / D4 / D10 は user の数字を別途待つ (額の推奨はしない — user 専権)。

---

## 6. 確定版 (10-08) までに Claude が埋める欄

1. S3 の carry_dip 14/14 突合結果 → D5 分岐の確定 (10-06)。
2. D3 補項の 4.4/4.5 多 leg 同時評価 (wg 3 leg @L1 の証拠金・exposure cap) の計算 (reassess §9-15)。
3. UD1 の結果反映 (SILVER なら v0.1)。
4. F4 推定器分解 (sprint S-F4) 着地後の発火日幅の再計算。
5. U3 (ii) 縮退の可逆性 (口座切替時の `OANDA_ACCOUNT_ID` / `restore_mappings` / trade_id 名前空間) の記述級列挙 (11-15 まで追補可)。
6. D10 台帳の器 (KB ページ) の作成。
7. D3 補項 (a) の per-leg rung 可否 (wg 専用 rung 定数の R1 要否、template L114 / card L51) の判定と、§3.4 の ¥472,800 版 (wg 3 leg 一律 rung、USD-quote leg 単価 ¥78.8/pip を含む) の再計算 → D3 参照点 (¥50,000 / ¥222,000) の一本化。
8. D2(i) 無回答時の L1 潰れ (5000u × 0.2 → 1000u) の解消経路 ((a) 決裁 or JPY 台帳 0.2x 解除) と D3 入金の同時性の明記; §3.4 pair セル単位の再計算 (pair 別 event 実測 N を wg card から取得し、等分仮定 1/3 を実測比で置換)。

## 7. caveat (本稿が測っていないもの)

- wg 頻度は N=4 で Poisson CI 0.57〜5.37/月 — §3.4 の必要セル数は点推定 2 つの併記であって区間推定ではない。
- drift 13.7 円/日は audit_default 82 − keeper 68.3 の差分仮定で測定値でない。実測対照 30d clean live −27.2p ≈ 9 円/日。
- keeper 月額は ¥1,820〜2,080 の区間 (Σpl 実額は API 非露出)。
- 定義 A (broker NAV 30d Δ) の真値は未計測 (CSV は 09-07 ¥276,304 → 09-21 ¥275,517 の 14 日分のみ)。
- carry_dip 未突合 7 本の broker 符号は未計算 — D5 の入力は S3 待ち。
- M1 レバーの成立条件 (会員単位合算) は unverifiable。
- E1 verdict (10-15) が最大の未知 — PASS なら D3 額・D2(ii) 第 2 セル・順位が変わる。
- 本稿は文書のみ (価格・DB の outcome 計算ゼロ)。

## 関連
[[path-to-win-decision-memo-2026-09-20]] / [[path-to-win-reassessment-2026-09-22]] / [[mission-capital-redecision-packet-2026-09-10]] / [[u1-mission-redecision-2026-09-17]] / [[monthly-target-rederivation-2026-07-10]] / [[lot-ladder-template-2026-08]] / [[shortest-path-decision-memo-2026-07-10]] / [[process-meta-audit-2026-09-07]] / [[status-volume-keeper-2026-09-01]] / [[live-frequency-and-oanda-status-survival-2026-09-01]] / [[kalman-d7-carveout-postfill-packet-2026-09-17]] / [[usdjpy_carry_dip_accumulator]] / [[weekend-gap-fade]] / [[supply-space-feasibility-2026-09-17]] / MEMORY `project_path_to_win_memo_2026_09_20` / `project_oanda_status_api_survival_2026_09_01`
