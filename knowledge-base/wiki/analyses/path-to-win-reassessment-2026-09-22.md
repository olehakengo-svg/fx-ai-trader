---
title: 「今どこで止まってて何をすれば勝てるか」再評価 (2026-09-22)
type: analysis
rule: R3 (read-only 分析、live/tier/lot/Kelly 変更ゼロ、凍結 look の outcome 非接触)
supersedes_partial: path-to-win-decision-memo-2026-09-20 (§2.1 D2(i)/USD-quote L1、§2.4 carry_dip 符号逆、§4.1 既定挙動「12-03 F4 強制起票」、L61/L170 N 基準、L107 容量)
provenance: 14-agent workflow (地上検証 4 / 提案 3 / 反証 6 = KB 整合 × 算数 / 統合 1)、orchestrator が Render ログ・本番 API を一次確認。原本: scratchpad ground_G1–G4 / proposal_P_A,P_B,P_C / refute_* (セッション限り)。user 問い「今どこで止まってて何をすれば勝てるか考えた上で教えて」
---

> **位置づけ**: [[path-to-win-decision-memo-2026-09-20]] の 2 日後再評価。不動点 (現行 M2 定義 × 現 NAV × $0 施策 → time-to-M2 = ∞) は**成立、しかも 3 脚 (資本 / エッジ容量 / 転換 G3) で過剰決定**。09-20 メモの誤り 5 点を訂正 (§7)。新事実: 09-22 00:15→03:35Z の HTTP 全断 3h20m (engine 生存、deploy 直後 hang の N=3 仮説) / wg 09-20 NO-QUALIFY → 09-27 繰越 / 着手可能研究ライン 0 / memo §4.1 17 項目 着手 0。
> **統合決裁パケット (D1–D12) の起票 (v0 09-29 / 確定 10-08) はこの文書の訂正一覧を入力にすること。**

# 最終統合 — 「今どこで止まってて何をすれば勝てるか」(2026-09-22、read-only、synthesize 段)

入力: facts (`scratchpad/ground_facts_2026-09-22.md` §A–§H2) / Ground G1–G4 / 提案 P_A・P_B・P_C / 反証 6 本 (kb × arith)。統合規律: どちらかのレンズで refuted の claim は correction 後の文言でのみ採用、action は両レンズ keep のみ「採用」、片方 reclassify は再分類後で採用。数字は出所併記。凍結 look (E1/ECG/E12/wg G1・G2/rnb forward/sr_anti_hunt forward/E23 OOS) の outcome は本稿でも一切計算していない。引用禁止値 (fit 現況値 / L1 5000u 前提 M2 寄与 / keeper 控除前 M2 算数 / P5 確率 / falsified family 再試行) は使わない。
略号: KB = `knowledge-base/wiki/`、REG = `KB/decisions/prereg-trigger-registry.json`、memo = `KB/decisions/path-to-win-decision-memo-2026-09-20.md`、template = `KB/analyses/lot-ladder-template-2026-08.md`、card = `KB/strategies/usdjpy_carry_dip_accumulator.md`、SP = scratchpad。

本稿で追加実読した code (統合者自身の spot check、09-22): `modules/demo_trader.py:7571–7578` (edge-cell lot × `_dd_lot_mult`、P0-1 user 決裁 2026-07-03 コメント付き) / `tools/nav_floor_projection.py:36–42,106–120` (行数 ≥7 で method=fit、audit_default は「実測 fit が立ったら使われない」) / `tools/m1_clean_live_monitor.py:523–531` (`pos_cells = ev > 0`) / `data/monitoring/nav_floor_projection.csv` 末尾 4 行 (09-17〜09-21 全て `fit`、09-20 行なし) / REG 5 entry (g0prime / carry-dip-v3-revival-watch / rnb ckpt-1 / F3 / F4 csv_row_match)。反証レンズの主要訂正はこれで独立確認できた。

---

## 0. 「勝つ」の定義 (3 段、どれを指すかで答えが変わる)

| 段 | 定義 | 今日の答え |
|---|---|---|
| (a) M2 到達 | +0.5%/月 NAV 実現 (rederivation L44)、L0→L1 昇格を含む | **30 日で勝てる手は無い**。time-to-M2 は現行定義 × 現 NAV × $0 施策で ∞ (§2)。有限化の前提は user 決裁 U3 入金 (D3 (i)、L1 算数が閉じる NAV = JPY leg 単独 rung ¥300k / wg 3 leg 一律 rung の現契約 ¥472,800 — PR #279 P1 訂正) ∧ D2(i)=(a) (DD lever 非乗算 — 無回答なら code が L1 5000u × 0.2 → 1000u に潰し入金しても容量が出ない、PR #279 P2 訂正) で、D1 会計定義は有限化後のサイズ (A 9〜14 本 / B 4〜6 本 @¥300k — 混合 rung [USD_JPY のみ L1、USD-quote leg は L0] 平均 ¥27.17/pip、wg 級 3 leg 一括ストリーム単位、type×pair×dir 単位では約 3 倍、PR #279 P1/P2 訂正) を変えるだけ (訂正 PR #279 P2: D3 ∧ D1 の conjunction ではない)。有限化後の時計も G3 (live N≥30) が binding で 2028 年台 |
| (b) kill 条件を設計どおり通過 | 10-01 Gold → 10-15 E1 → 11-30 U3 → {F4 12-04〜01-08, F2 12-31} → 02-05 F1 → 03-31 F3/global-stop を、検知器が嘘をつかない状態・API 生存のまま迎える | **今日は 3 検知器とも「発火しても不発火でも設計どおりと言えない」**: F3 は estimand 未宣言、F4 は fit を読み発火日が 1 ヶ月動く、F2 は per-event fill 率が未測定 (§1 計測層) |
| (c) 測定可能状態の確立 | 10-08 統合決裁パケットが正しい入力 (stale 訂正済み・両基準併記・引用禁止値なし) で user に届く | **未起票** (facts §A)。30 日の Claude の仕事はここに集約される |

**結論**: 30 日で「勝つ」= (c) を 10-08 に出し、(b) の 3 検知器を 11-10 までに正し、floor 尾 (storm) と観測系 (HTTP 盲目・deploy churn) を守ること。(a) は user 決裁待ち。3 提案 × 2 レンズの反証を通ってもこの骨格は 1 箇所も動かなかった。

---

## 1. どこで止まっているか (層別、証拠付き)

| 層 | 主張 (反証通過後の文言) | 証拠 |
|---|---|---|
| **資本 × M2 定義 (∞ の源)** | NAV ¥275,516.83 (09-14 から不動)、keeper 26 RT × ¥80 = ¥2,080 = **0.755%/月 > M2 0.5%**。必要 gross = 0.005×NAV + 2,080 = ¥3,457.58 = **1.255%/月 = 345.8p/月 @1000u**。L1 5000u は 4.2 (≤2.5% NAV = ¥6,887.92) を ¥7,500 で違反 → tool HOLD。L1 開通 NAV = **¥300,000** (JPY ペア、差 ¥24,483) / **¥472,800** (USD-quote @157.6、差 ¥197,283 — **wg は 3 leg 全執行 ∧ 単一 lot 定数 (card L51/L53) なので wg 全体の開通はこちらが binding**、PR #279 P1 訂正)。**L0→L1 は G3 (live N≥30 ∧ mean>0 ∧ WR≥35% ∧ disaster 0) ∧ Wilson_lo>BEV ∧ 4.2 の AND 錠** — 今日 G3 を満たす live 可能セルは 0 (M1_STRONG 0)。片方を外しても開かない (時点依存: carry_dip が demo 基準で N≥30 に届く 11-18 以降は 4.2 が再び binding) | facts §B L17–L20 / G1 §2.1–2.3 (tool 実走 HOLD/PROPOSE) / template L65, L79 / `tools/lot_ladder_calc.py:31,34` / refute_P_C_arith C1 |
| **同 (より強い形)** | 4.2 ∧ disaster SL 150p ⇒ units ≤ NAV/60 ⇒ **wg 単独の %NAV 寄与 ≤ EV×freq×0.01/60 = 0.166% (4.75p×2.1) / 0.260% (4.75×3.28) / 0.432% (凍結 7.9×3.28) — NAV・keeper・rung に無関係に M2 不達**。第 2 セルは資本額では買えない | refute_P_B_kb C2 / refute_P_B_arith C2 (両レンズ一致)。KB 既存 `process-meta-audit-2026-09-07.md` L106 の強化版 |
| **執行 (N 時計)** | clean live N: 30d **9** (2.1/週)、7d 0、最終 fill 09-11T11:02Z から 10.8 日。律速は **agg_kelly ではなく `_tick_entry` 下流ガード**: carry_dip = velocity_down 4 (バー数の上界) / same_price_3pip 1 / AGG_KELLY **0** (11d 台帳)、shadow 行も残らない (分母消失)。card L3 の agg_kelly 帰属は code (bypass set `demo_trader.py:10560–10586`) と台帳に反する。**ただし 11 日ゼロは統計的に異常ではない** (Poisson P = 0.045〜0.16)。積まれている N は宣言契約と別戦略の N (SL as-placed 11.7–28.5p vs 150p、cooldown 非執行)。N≥30 1 本目 = carry_dip 2026-11-18 (demo 14) 〜 2027-02-07 (突合 7)、2 本目 2027-04+ → F3 (03-31) が先 | G2 §1–§3, §6 / SP `block_counts_11d.json` / `demo_trader.py:6350–6389` / refute_P_C_arith C3 |
| **計測 (kill 検知器)** | (i) 本番の M2 系数値 `m1_clean_live_monitor.py:523–531` は **正EV セル (EV>0、N 不問、45 セル) の 30d pips/NAV = +0.099%** = winner-selected 診断量。同 30d の全 clean live は **−27.2p = −0.099% (¥10/pip 一律) / −0.086% (銘柄別)**。定義 A (入出金調整後 broker NAV Δ — 生 NAV Δ は D3 入金を虚偽リターンに数える、PR #279 P2 訂正) の 30d 読み手は不在・真値未計測。(ii) **F3 の estimand 三重不一致**: REG「PnL>0」/ monitor 母集団 = demo `pnl_pips` / monitor STRONG = EV≥+1.0 ∧ Wilson_lo>0。(iii) **F4 の読み手は fit** (`nav_floor_projection.py:111–115`、CSV 09-16 以降 fit のみ) → 発火は keeper のみ **2027-01-08** / drift 込み **2026-12-04〜07** (2 者独立再現)。memo「12-03」は audit_default 前提で書き手の値ではない。keeper のみなら **F2 (12-31) → E1 2nd (01-06) → F4 (01-08)** に順序反転。(iv) **「carry_dip 符号逆」は refuted**: 突合 7 本は demo −16.4p / broker −41.1p で**両方負**。demo 簿 +103.0p の正符号は broker 未突合 3 本 (#549260 +29.0 / #573986 +63.7 / #681149 +38.2 = +130.9p) が担う。reconcile 対象は 11 本でなく **14 本** | refute_P_B_kb/arith C1 / refute_P_C_kb C2・C4 / refute_P_C_arith C2・C4 / 本稿 spot check |
| **研究供給** | 着手可能 family **0** (#27 FAIL 09-18、#29 未登録)。時限 look 3 本 (E1 10-15 / ECG 11-06 / E12 02-05) は金でも前倒し不能。E1 評価器 green (96 tests / self-check pass) だが **凍結 export tool 不在** — pre-reg §2.5-6 が要求するのは手続きであり tool 不在 = verdict 無効ではない (無効化は §6 違反時のみ)。E1 modal = UNDERPOWERED (事前宣言)。rnb closed shadow N=2、09-24 ckpt-1 (n_floor 3) TRIGGERED 見込み (統計的には弱い信号 P(N≤2)=0.114 だが規則上の調査義務は成立) | G3 §0–§2, §4.1 / refute_P_A_kb claim 6 / refute_P_A_arith Rank 8 |
| **観測・監視** | 09-22 **00:15→03:35Z (3h20m)** 全 HTTP 499/502、engine 生存 (03:18:41Z shadow 行 id 18184 DB commit; 直接証拠は 02:40 以降、窓前半は tick 計数からの推定)。再起動 ×4。09-15 / 09-21 / 09-22 の 3 例とも直前に deploy 発生 commit あり (4d51c1b1 / d8f92726 / 85a823ce+05450797) = 「deploy 直後 HTTP hang」は N=3 の仮説。**夜間 deploy 源は ≥3/日**: rate anchor 00:04Z (data/external + **data/cache/yield/ZN_F_1h.parquet**) / mof 00:12Z (data/external) / **nav_floor CSV ~03:1xZ (data/monitoring)**。`data/cache/**` は `modules/yield_data.py:23,43` が Path 連結で読み `tests/test_render_build_filter.py:29–35,94–101` が trading-path として pin → ignore 追加は CI FAIL。daily report 03:10 は 0 データで「無料 tier」と誤帰属して KB 永続化。nav_floor CSV 欠行は 09-22 のみ (09-20 は日曜 = cron `1-5` 仕様) | facts §H2 / G2 §5 / refute_P_A_kb claim 3・4 / refute_P_A_arith claim 3・4 |
| **プロセス・容量** | memo §4.1 17 項目 done 0 / in-flight 0。09-18〜22 人手 commit 62 の 77% がレビュー修正、code PR 巡目中央値 8.5 (#273 27 波)。供給は **[10.5, 19] セッション/30 日** (税率 75% は commit ベースでレビュー時間を需要と二重計上 → セッションベース 55–60% なら 16.8–18.9)、需要 15〜21.5 → **「不可能」ではなく「タイト、triage 必須」**。live PR 3 本だけなら 4〜6 セッションで収まる (G4 §5.4)。並行 PR は conflict + post-commit 末尾差分で merge を 2 回止めた | G4 §1–§5 / refute_P_A_arith claim 2 / refute_P_C_arith claim 6 |
| **決裁** | パケット未起票。**D2(i) は「表示のみ」でなく user 決裁 2 件の衝突** (07-03 P0-1 `demo_trader.py:7571–7578` = edge-cell lot × dd_mult vs 08-05 template L73 = 乗算しない) で L1 開通と同時に binding (5000u×0.2 → 1000u)。**D3 (4.2 多 leg 解釈) は未裁定** (template L167 は単 leg の worked example)、wg 3 leg 同時 L1 = USD_JPY ¥7,500 + AUD_USD/EUR_USD 各 ¥11,820 = ¥31,140 = 11.3% NAV (quote 通貨別 pip 値 @157.6) → L1 開通 NAV ¥300k (JPY leg 単独 rung) / ¥472,800 (wg 一律 rung) vs ¥1,245,600 (旧「¥22,500 = 8.2% → ¥900k」は USD-quote leg を JPY pip 値で数えた誤り、訂正 PR #279 P1)。D10 は stale (codex-runner 09-10 suspended)。**Gold 算入 (同一秒往復) は status 頁「毎営業日判定・順次適用」により今日 user 画面で読める** (10-01 待ち不要) | refute_P_B_kb C3・Action 3 / refute_P_B_arith §1-5 / facts §A L13 |

**層をまたぐ結論**: 下 6 層のどれを直しても最上層の ∞ は解けない。最上層は user 決裁でのみ有限化され、有限化後の時計も G3 (2027-07+ / 2028 年台) が binding で 30 日で動かす $0 施策は無い。**30 日の容量配分の基準は time-to-M2 寄与ではなく (a) 決裁を正しい入力で可能にする (b) kill 検知器を正す (c) floor と観測系を守る** — 3 提案とも同じ結論で、反証でも動かなかった。

---

## 2. 不動点は今日も成立するか

**成立する。しかも 09-20 memo より強い形で。** 理由 3 点 (両レンズ通過):
1. **数値ごと不変**: NAV / keeper 26 RT / 0.2x とも 09-20 と同一 (G1 §3.1)。keeper 単価は プロコース USD/JPY **0.8 銭 原則固定 (配信率 98.24%、実測 0.7–0.8p)** で cost/$ = ¥0.0035〜0.004 の構造下限 → spread cap / 窓 / units / RT 数 / 銘柄 / ベーシック / Silver 存続 / 隔月化 (K1–K7) は全て無効 (効果上限 ¥260/月)。
2. **過剰決定**: (i) 資本 (keeper 0.755% > 0.5%) / (ii) エッジ容量 (4.2 拘束下 wg ≤0.43% NAV 不変) / (iii) 転換 G3 (N≥30 セル 0、最速 2026-11-18〜2027-02-07 — as-placed N 継続 (D5 (b)) の場合; 宣言契約復元 (a) なら宣言セルの N は復元日から 0 再起動 = 復元日 + 107〜180 日、訂正 PR #279 P2) の 3 脚。$0 レバーで有限化できるものは無い。
3. **有限化後も遠い**: D3=(i) 入金 ≥¥24,483 [JPY leg 単独 rung; wg 一律 rung なら ≥¥197,283 @¥472,800、PR #279 P1 訂正 — いずれも今日 NAV 基準の差額、入金日 NAV で再基準化 (11-30 なら ≥¥28,643 / ≥¥201,443)、PR #279 P2 訂正] ∧ D2(i)=(a) ∧ D1=B なら @NAV ¥300k で必要セル **B 4〜6 本 / A 9〜14 本** (混合 rung 平均 ¥27.17/pip [USD_JPY のみ L1]、wg 級 3 leg 一括ストリーム単位、pooled 頻度 2.1 vs 3.28/月 — type×pair×dir 単位では約 3 倍 = B 11〜17 / A 26〜40、PR #279 P1/P2 訂正; N=4・Poisson 95% CI 0.57〜5.37/月で区別不能 → 点推定 2 つを CI 付き併記)。wg N=41 到達は leg 基準 13.3–16.7 ヶ月 / 週末基準 21–26 ヶ月 (T_conv 0.75–0.94 は実測 0/1 で未測定) → 2027-11〜2028-11。

**最強の生存カウンターレバー = M1 (user 手動 USD_JPY 出来高を同一会員の別 OANDA 口座へ → keeper 停止)**: spread 差の上界 (0.8 − s0)銭 × 250,000〜260,000 units×RT ≤ **¥2,000〜2,080/月** で keeper 以下、必要 gross 1.255% → 0.5% + 2,080/NAV に圧縮 (2.51 倍)。ただし (a) 会員単位合算は status 頁に「合算/複数口座/口座単位」の語 0 件 = **unverifiable** (OANDA 一次確認は user 経由)、(b) spread-only 上界で swap/financing 差・個人口座 (NAV 0) の証拠金・units 下限 ≥1,634u/RT が抜けている、(c) 09-01 user 決裁 案 A が案 B (user 手動出来高) を退けた選択の**再決裁**、(d) **L0 の ∞ は解けない** (keeper=0 でも 137.8p/月 @1000u 必要、G3 も残る)。⇒ パケットに feasibility + user 確認項目として同梱するに留める。**入金 U3 は clock には効かない (G3 binding) が必要 gross% を圧縮する (feasibility には効く) — 「生存のみ」でも「M2 加速」でもなく「clock には効かない」と限定して書く。**

---

## 3. 勝つための施策ランキング (30 日、両レンズ keep または再分類後で採用、最大 8)

t2m2 効果は 3 択: ∞→有限 (の可能化) / 有限化後に動かす / 効かない。

| Rank | 施策 (correction 反映後) | Rule / owner | 期限 | 効果 | 反証結果 |
|---|---|---|---|---|---|
| **1** | **統合決裁パケット起票** (v0 09-29 → 確定 10-08、user 返答 11-30、D1–D4 先行可)。同梱: D1 (A/B、読み手 3 行 = A 入出金調整後 broker NAV Δ [未計測・broker tx 起点必須] / B 全 clean live −0.086〜−0.099% / 現行 M3b = winner-selected 診断ラベル) / **D2(i) = 07-03 P0-1 vs 08-05 template L73 の user 決裁 2 件の衝突として上程** (L1 開通と同時に binding、JPY 台帳 SSOT +¥6,178/+¥27,725) / **D3 4.2 多 leg 解釈は user 項目のまま** (¥300k [JPY leg 単独 rung] / ¥472,800 [wg 一律 rung] vs ¥1,245,600 @157.6、旧 ¥900k は PR #279 P1 で訂正) / D10 は固定費台帳の月額のみ / **D11 に母集団軸 (demo pnl_pips vs broker realized) + 閾値 (REG PnL>0 vs monitor EV≥+1.0∧Wilson) を追加** (D14 新設せず、kalman D7 と整合) / D15 floor バッファ: **¥262k は自前バッファ、OANDA 条件は残高 ≥¥250k、API 停止は keeper guard skip → 翌月 Silver の間接経路で停止日 04-01 か 05-01 か未確定** / USD-quote L1 ¥472,800 / carry_dip N 基準 (demo 14 / broker 11 / 突合 7、reconcile 14 本) / 2 セル算数 @NAV ¥300k を CI 付き併記 / M1 feasibility (09-01 案 A 再決裁・swap 項・unverifiable 明記) / U3 期限 vs keeper 支出 (10・11 月 run ¥4,160 = 1.51% NAV は 11-30 前に支出確定、F1 まで ¥8,320 = 3.02%、残余 ¥5,197 @edge 0) / Gold 判定を前提条件に。**既定挙動は「無回答 = 何も起きず余裕 ¥13,517 の 15.4%/月を消費、F4 fit 発火は 12-04〜01-08 (12-03 ではない)、Claude は 12-03 に record として再上程 (執行はしない、P4 型 default-on-timeout ではない)」と書く** | R3 文書 / Claude → user-decision | v0 2026-09-29 / 確定 10-08 | **∞→有限の唯一経路の「可能化」** (前提は D3=(i) ∧ D2(i)=(a) [無回答なら 0.2x で L1 が 1000u に潰れる]; D1 は有限化後のサイズ A 9〜14 / B 4〜6 本 [混合 rung ストリーム単位] を変えるだけ — 訂正 PR #279 P2)。Claude 単独では効かない | 3 提案とも keep (6/6 レンズ)。訂正: ¥1,295/本 (L1 5000u 前提 = 引用禁止) 除去 / 既定挙動の F4 12-03 は fit writer で不成立 / D3「既決」refuted / D2(i)「表示のみ」refuted / D14 は D11 統合 |
| **2** | **E1 凍結 export tool + 10-08→10-15 手順書 + second look cutoff #2 (12-30) 手順 + UNDERPOWERED 時 (a-1) probe 扱いの一行定義** (10-14 まで KB 固定)。`/api/positioning/export` snapshots 13 instrument + health_log → JSON/parquet + sha256 → `raw/bt-results/`、合成 artifact roundtrip テスト同 PR pin、M15 parquet cutoff スライス手順 (cache gitignored → sha256 を raw 側に)。**試走は `table=health_log` か合成 artifact のみ** (limit=1 snapshots は生 skew 値 1 行閲覧で §6-2 許可リスト外)。tool 不在 ≠ verdict 無効 (手続き要件は手作業でも満たせる) — tool は「1 回だけ」規約の機械担保 | R3 / Claude | 2026-10-06 (cutoff 10-08T06:33:31Z の前) | 効かない (E1 PASS 4.0% 点推定、Wilson 0.7–19.5% / PASS でも live N≥30 は 2027-05〜09) | 3 提案 keep (6/6)。訂正: 試走範囲 / 「無効化リスク」の限定 |
| **3** | **kill 検知器の estimand 是正 (観測前)**: (i) **F4 推定器 hardening を 30 日に戻す** — 「keeper 決定論分 + edge 30d 実測」への分解 (窓延長は効かない: 60 行 ≈10 週は既に 2 サイクル超、振動の原因は窓未充填 11 行 + 月内位相)、counterfactual pin は再現値 (10-20: keeper のみ 168 / drift 込み 140、12-10: 111 / 78 の区間外で落ちる) で書く、REG F4 message に方法変更 + 発火日シフトを記録 (U7 トリガ = condition 不変)、cron 側で writer 失敗 (09-22 03:13) を露出 (tool 層は exit 1 で既に fail-loud) / (ii) **F3 両基準併記**: `m1_clean_live_monitor.py --strong` に broker realized 列 (Rank 5 の reconcile 出力に直列依存) を **EV≥+1.0 ∧ Wilson_lo>0 の同 2 条件で**計算、REG F3 message に「D11 決裁まで両基準併記・N≥30 到達後の基準選択は禁止」1 文追記 / (iii) M3b 出力に「winner-selected 診断」ラベル、B 行は既存 M1 KPI 行の再ラベルで足りる | R3 (tools + REG message) / Claude、基準選択は user (D11) | F4 2026-10-31 / F3 2026-11-10 (carry_dip N≥30 最速 11-18 の前) | 効かない (有限化後: N 基準で carry_dip N≥30 到達日が Δ≈2.7 ヶ月動く) | P_A stop「F4 は fit 非依存で 90 日へ」= **両レンズ refuted** → 30 日復帰 / P_B Rank 2 keep (A 行の broker 起点必須) / P_C Rank 3 reclassify (D11 統合、2 条件) |
| **4** | **容量規律 + インシデント記録 + deploy churn 遮断**: (i) PR ごとに巡目上限 ≤6 を起票時に事前宣言 — **上限は P2 限定、P1 は例外なく修正** (CLAUDE.md マージゲート、09-19 triage 19/19 実欠陥)、超過 P2 は estimand 注記付き registry 繰延で「未修正」明記 / (ii) code PR マージは市場時間外にバッチ、並行 PR は直列、**日曜 20:00–22:30Z (wg event) は除外窓** / (iii) 17 項目 → 30 日 8 項目 (本表) + 90 日側の triage 文書 (post-commit 末尾差分 registry 10-13 を先に塞ぐ) / (iv) 09-22 3h20m HTTP 盲目を KB 記録 — **root cause UNKNOWN で書く**、daily report L63「無料 tier」無効化 / (v) daily report 全 API 失敗時 NO-DATA スタブ + analyst prompt にホスティング事実 (monitoring 経路 = review gate 対象) / (vi) **`render.yaml` ignoredPaths に `data/external/**` と `data/monitoring/**` のみ追加** (00:12 mof deploy と 03:1x CSV deploy を止める)。`data/cache/**` は CI pin + `yield_data.py` read で FAIL → `data/cache/yield` の 3 階層再分類 (runtime importer = `tools/rate_anchor_ingest.py` のみの grep 証拠付き) を別 R3 で。00:04 rate-anchor deploy は当面残る / (vii) DB 非接触 engine-tick health endpoint + per-request latency log (10-10) | R3 / Claude | (i)(iii)(iv) 2026-09-23 / (v)(vi) 10-03 / (vii) 10-10、中間チェック 10-06 | 効かない (前提条件 + F4 入力欠行防止 + 再起動 reset 減) | P_A Rank 3 keep (2 限定) / Rank 4 reclassify (c 分割) / P_C Rank 8 keep。claim 4 `data/cache/**` は **refuted** / 「2 回/日」→ ≥3 回/日 / 再現率 2/7 は N=2 Wilson 4–40% で点推定引用不可 / 「算数で不可能」→「タイト」 |
| **5** | **carry_dip: card L3 訂正 + 14 本 reconcile (one-off GET) + block 理由確認**: (a) card L3 の agg_kelly 帰属を code・台帳根拠で訂正、card L1「08-14 以降」と #677396 (08-12) の衝突も訂正 / (b) 未突合 7 本 (#677931/#681149/#837978/#847578 + #549260/#573986/#677396) を `/api/oanda/transactions` GET で one-off 突合し 14/14 の符号確定 (汎用 `broker_ledger_reconcile.py` は #273 型欠陥族 27 波 → 90 日) / (c) 11 fill の entry 直前 60 分下落幅 vs velocity_down 20p 閾値は **価格キャッシュ (H1/M15) から計算** (08-14 以降の Render ログは retention で存在しない; carry_dip は凍結 look でない) → 「≈5 シグナルの block 理由確認」として R3 文書 (「帰属確定」「設計衝突」と断定しない) / (d) block 台帳 readout tool (`/api/demo/block-counts` 消費、予約 L5506 前後で per-tick/bar 区別、cell 別 T_conv 週次)。**R2 autopilot の predicate は REG 凍結値のまま = deduped LIVE N≥10 ∧ demo `pnl_pips` EV<0 → lot↓ or LIVE 停止 (shadow 継続)。broker との conjunction は要求しない** (要求すると凍結 predicate の黙った厳格化になり、demo EV<0 ∧ broker EV≥0 で認可済みの損失停止が塞がる — 訂正 PR #279 P1; REG 凍結規律は pnl_pips = demo 簿; 現状 demo N=14 EV +7.36 で不成立、突合 7 本 broker −5.9p/t は凍結 estimand の外かつ N=7<10) — broker のみ EV<0 は estimand 差し替えになるので執行せず乖離を D5 材料として記録。契約復元 / velocity 免除 / 再開は user (D5) | R3 分析 + tools PR / Claude、R2 は上記条件のみ autopilot、D5 は user | 2026-10-06 (パケット v1 入力) / tool 10-15 | 効かない (carry_dip は G3 不成立で L1 候補外、N 増は M2 非寄与) | P_A Rank 5 keep (注記) / P_C Rank 5・7 reclassify。「符号逆」**refuted** / 「08-14 以降ログ」refuted / R2 broker-only 執行は凍結 estimand 差し替えで不可 |
| **6** | **wg G0' 記録 + 09-27 21:00Z event #3 の分岐事前固定**: card L118 以降に 09-13 ABANDONED_DRIFT (+41.0p > +8.0p、trade-log 09-16 L241 に事象記録済み = 「card 未転記」) と 09-20 NO-QUALIFY (USD_JPY −19.0p < 21.4p / AUD_USD −20.5p < 25.0p) を転記。**09-13 は改定後 1 件目の不成立として既カウント** (REG g0prime は drift 放棄を不成立に含む) → **次の qualifying 不成立 1 件で「執行モダリティ R1 再審」発動** → 骨子 DRAFT (打ち切り +15 分 / drift +8.0p の変更候補と estimand 影響表) を **09-27 前**に用意 (user 承認)。分岐: fill → F2 resolve + 変換係数 N=1 / ABANDONED_* → R1 再審起案 / NO-QUALIFY → 10-04 繰越 (分母外、P(3 週末とも non-qualifying) ≈14〜17%)。11-01 DST 打ち切り時刻の R3 再導出を 10-25 まで、イベント後 24h 記録を g0prime 手順に追記 | record-only + R3 文書 / Claude、R1 再審承認は user | 転記 2026-09-24 / 骨子 DRAFT 09-26 / registry 09-28 | 二値: fill → 有限化後の経路 A (wg L1、NAV ≥¥300k [JPY leg 単独 rung] / ≥¥472,800 [一律 rung]) 生存 / 不成立 → 第 2 セル候補消失。N=41 到達 13.3–16.7 ヶ月 (leg 3.28/月) 〜 21–26 ヶ月 (週末 2.1/月)、T_conv 未測定 | P_A Rank 6 keep / P_C Rank 6 keep (訂正: (1−p)² → (1−p)、期限 10-25 → 09-27 前) / P_B Action 6「0/7 累計」は改定前後混在で reclassify → 既存規則への keeper 分岐追記に |
| **7** | **storm guard 4 点** (`OandaBridge.modify_sl` / `modify_sl_sync` `oanda_bridge.py:963–1008`、4 点いずれも不在を code 確認): 累積 tx breaker → 冪等 (同値再送 skip) → 単調性 (BUY で SL 下げ禁止) → 1-pip dead-band。log-only 検知器を先に入れ、counterfactual pin (各 guard kill で storm fixture が通る) を同一 commit、CF 前に pycache purge。wg (trail なし、card L42 不変更値) の凍結値に触れないことを PR で明示、修正後は Rule 2 監視。巡目上限 ≤6 (P2)、市場時間外マージ。容量スリップ時は検知器のみ着地し guard 本体は 90 日へ。**「1 tail ¥1,500 = 11.1%」は disaster SL 150p の尾、storm の尾は不利側自己約定 (直接 PnL ¥0 実績) — 別物として書く**。tail は未定量 | R3 (構造バグ、live 経路 PR-1) / Claude | 2026-10-10〜10-20 | 効かない (PnL 0)。floor 尾の保護のみ | 3 提案 keep (6/6)。語法訂正のみ |
| **8** | **研究側の期日消化 (件数・手続きのみ)**: (i) rnb ckpt-1 (09-24) TRIGGERED 時 lane-health 調査 — conf gate / QUALIFIED_TYPES / shadow_only 配線 / 信号頻度 UTC 7–20、**件数のみ、WR/EV 不接触**、09-10 conf 単位バグ再発型を最初に疑う / (ii) E23 P1×3「park 根拠の estimand 監査」(registry 10-03) — **Gate A 再計算は pass-1 測定可能性メトリクス (辞書カバレッジ) の範囲に限定し OOS 窓に触れない**、Fed discovery を FOMC statement 限定 (manifest 変更)、BoJ 英訳時刻検証、pass-2 は解錠しない、park は動かさない (Gate B N=56<100 は Gate A 非依存) / (iii) **#29 S1 census は step 0 (license-free dense 凍結 stance モデルの候補・ライセンス・訓練標本の explore 窓 2014–2023 重複調査) のみ**、結論は **10-18 を待たず即時に臨時スキャン記録 (C1–C6、候補ゼロでも可) として置く** (WIP 規則「0 本なら期日を待たない」)。ABG 辞書 (NH=0 279/327) での census は走らせない | R3 / Claude | rnb 2026-09-26 / E23 10-03 / census step 0 即時 (〜10-03) | 効かない (F1 分子分母に入らない、memo Rank 5 refuted +0.4〜1.6pp) | 3 提案 keep。訂正: #29 時期 (即時) / E23 の P-10 境界 |

**採用しなかった / 90 日側**: EXEC_CONTRACT 検知器 (live PR-2、F2 帰結 12-31 と同時期) / 汎用 reconcile tool / 時計台帳 v0 / venue feasibility (記述級、**ただし U3 (ii) 縮退の可逆性材料 (V2「新規口座開設後は翌月末までゴールド」の既存会員追加口座への適用可否 = unverifiable、口座切替 code 影響 = 記述級) は 11-15 までにパケット追補として前倒し可** — P_B Action 5 両レンズ keep) / Turtle S2 readout (N=0 → Render cron liveness 確認に読み替え) / CME ZQ・SR3 (web 再起動を伴う種まき) / readout 欠落修復の残り / bypass set 衛生。

---

## 4. user 決裁が必要な事項 (期限・無回答時既定)

| id | 問い | 選択肢 | 期限 | 無回答時の既定 (実装どおり) |
|---|---|---|---|---|
| UD1 | **Gold 算入確認** — OANDA status 画面「今月の取引額」に 9 月 keeper 26 RT ($520k、同一秒自己往復) が算入されているか。status 頁は「毎営業日判定・順次適用・翌月末まで維持」なので **今日読める** | GOLD 表示 / SILVER 表示 / 不明 | 2026-09-23 (即日、10-01 を待たない) | keeper は設計どおり 10 月 run (¥2,080) を実行。SILVER なら live 系施策 (Rank 5・7) の前提消滅、U3 は (ii)/(iii)+再入場経路に縮約、9 月 ¥2,080 は sunk |
| UD2 | **Render workspace 選択** (対話セッション 1 回) — 09-22 HTTP 盲目の root cause (H1 SQLite lock / H2 gthread 枯渇 / H3 edge) の request log 読み取り、Turtle S2 cron liveness 確認の前提 | 選択する / しない | 2026-09-26 | root cause は UNKNOWN のまま KB 記録。velocity_down 検証は価格キャッシュ経路 (Rank 5c) で代替 |
| UD3 | **M1 一次確認** — OANDA に「会員ステータスの出来高は同一会員の複数口座で合算されるか」を確認 + 外部業者の s0・units・RT/月・swap 条件を Claude に渡す (Claude は問い合わせ文案まで) | 確認する (→ U3 に第 4 選択肢 (iv) 追加) / 見送り (09-01 案 A 維持) | 2026-10-31 (11 月 run に効かせる場合; 10 月 run は ~10-13 完了で間に合わない) | keeper 継続 (09-01 案 A のまま)、M1 はパケットに unverifiable 記載 |
| UD4 | **U2 資本上限** (1 数字) | 数字 | 2026-10-15 推奨 (11-30 まで) | U3 の上界不定、(a-1) 有償 probe は自動 NO、(c) 非 FX は起案不可 |
| UD5 | **D1–D12 返答** (+D3 多 leg 解釈 / D2(i) は 07-03 vs 08-05 の衝突として / D11 に母集団・閾値軸 / D15 自前バッファ) — D1–D4 先行返答でも分母は有限化できる | パケット記載の選択肢 | 2026-11-30 (E1 verdict 10-15 後) | **何も起きず余裕 ¥13,517 の 15.4%/月を消費**。F4 fit 発火は 12-04〜01-08 (keeper のみなら F2 12-31 の後)。Claude は 12-03 に record として再上程 (執行なし)。10・11 月 run ¥4,160 は期限前に支出確定 |
| UD6 | **D5 carry_dip disposition** — 宣言 SL 150p 復元 / velocity_down 免除 (live セル新フィルタ = R1) / LIVE 停止・shadow 継続 / 現状維持。入力 = Rank 5 の 14/14 突合 (10-06) + block 理由確認 | 4 択 | 2026-11-30 (REG backstop) | 現行 live 継続。R2 autopilot は REG 凍結 predicate (deduped LIVE N≥10 ∧ demo `pnl_pips` EV<0) のまま — 成立なら lot↓ or LIVE 停止 (shadow 継続); broker のみ EV<0 は記録のみ (訂正 PR #279 P1: 両 estimand conjunction は凍結 predicate の厳格化で不可) |
| UD7 | **D8 4 原則解釈** — velocity_down が LIVE 側 winning-location フィルタとして意図的か、shadow 行も消している (原則#3 前段) のを許容するか / 「監視盲目でも攻める」と tail 統制の優先 | 解釈の裁定 | 2026-11-30 (パケット同梱) | 現状維持 (shadow 分母消失を記録し続ける) |

---

## 5. Claude が今週やること (09-22〜09-28、順番どおり)

1. **09-23**: triage 文書 (17 → 本表 8 + 90 日側) + PR 起票時の巡目上限規律 (P2 ≤6、P1 例外なし) + 市場時間外マージ規律 (日曜 20:00–22:30Z 除外) を KB に 1 本。09-22 インシデントを **root cause UNKNOWN** で KB 記録、daily report L63「無料 tier」を無効と明記。user に UD1 (Gold 画面、今日) と UD2 (workspace) を 1 行で依頼。
2. **09-24**: wg card に 09-13 / 09-20 を転記 (「card 未転記」)。rnb ckpt-1 の件数判定 (N<3 なら TRIGGERED) → lane-health 調査開始 (件数のみ)。
3. **09-24〜26**: `render.yaml` ignoredPaths に `data/external/**` + `data/monitoring/**` のみ追加する PR (test 追加、`data/cache/**` は触らない、市場時間外マージ)。post-commit 末尾差分 (registry 10-13) を先に塞ぐ。
4. **09-26**: wg「次 qualifying 不成立で R1 再審」の骨子 DRAFT (user 承認前提、09-27 前)。rnb lane-health 結論 (件数のみ)。
5. **09-26〜28**: carry_dip card L3 訂正 + 7 本 one-off GET 突合 (14 本基準) の着手。#29 step 0 (dense license-free 凍結モデル同定) を臨時スキャン記録として即時に置く。
6. **09-29**: パケット v0 (Rank 1 の訂正一覧を全て反映、引用禁止値ゼロ、既定挙動は fit ベース)。E1 export tool の設計・合成 roundtrip テスト着手 (10-06 着地)。
7. **記録の禁止事項を今週から適用**: fit 現況値の数値転記をしない (「6 日で 2 倍近く動いた」と述べるだけ)、「符号逆」「33 分」「agg_kelly block」「12-03 確定」を書かない。

---

## 6. やめること

**引用・記述**
- 「carry_dip は demo +103.0p / broker −41.1p で符号逆」— 母集団不一致。正: 突合 7 本は両方負 (−16.4 / −41.1)、正符号は未突合 3 本 +130.9p が担う。
- 「F4 は 12-03 に発火」を確定事実として。読み手は fit、発火は 12-04〜01-08 の幅、keeper のみなら F2 の後。kill 順序は「10-01 Gold → 10-15 E1 → 11-30 U3 → {F4 12-04〜01-08, F2 12-31} → 02-05 F1 → {floor 03-04〜04-07, F3/global-stop 03-31}」と書く (PR #279 P2 訂正: floor 幅が F3 を跨ぐので重なりとして表記、順序は実測 floor 日で条件付け)。
- 「無回答 = 12-03〜05 F4 強制起票」を既定挙動として (現行 writer では来ない)。
- 「0.2x は live 送信のどこにも乗算されていない」— 正: 乗算後に固定 lot / floor 1000u で無効化、L1 では edge-cell 経路で binding。
- 「D3 (4.2 多 leg) は template 既決」— 未裁定、user 項目。
- 「keeper=0 なら wg L3 で 1.086%」等、rung が 4.2 違反となる NAV を分母にした %。
- 「M3b return +0.099%/月」を M2 進捗として (winner-selected、keeper 非含)。
- 「入金 = M2 加速」も「入金 = 生存のみ」も — 「clock には効かない、必要 gross% は圧縮」に限定。
- 「実測 2.1/月 では 3 本」— N=4、CI 0.57〜5.37 で設計 3.28 と区別不能。点推定 2 つを CI 付きで併記。
- 「API 生存余裕 ¥1,037〜−¥1,566」を自前バッファ (¥262k) 基準と明記せずに。OANDA 条件は残高 ≥¥250k、02-05 時点は ¥2,614〜4,477、drift 13.7 円/日は監査由来の差分仮定。
- 「30 日の需要 > 供給は算数で不可能」— 供給は [10.5, 19]、正は「17 項目 + registry 15 件 + 継続レビュー全部は不可 = triage 必須」。「55% なら供給 17」は 18.9 の誤記。
- 「夜間 deploy 2 回/日」→ ≥3 回/日。「再現率 2/7 日」の点推定引用 (N=2、Wilson 4–40%)。「09-22 の盲目は 33 分」(3h20m に superseded)。
- 「velocity_down 4 = 4 バー」の断定 / 「carry_dip drought = 設計衝突」の断定 (P = 0.045〜0.16 で異常でない、機構は仮説)。
- 「clean N はゼロ速度」を限定なしで (正: 契約準拠 N に限定、生の clean N は 2.1/週)。「carry_dip は agg_kelly で block」(card L3 訂正対象)。
- memo L107「~5 セッション」/ L61・L170「N≥30 が 2027-Q1〜Q2」を N 基準なしで。
- 「keeper cap 0.5p は観測ゼロだから無効」→ 構造根拠 (0.8 銭 原則固定) で。
- (継続) nav_floor fit 現況値 / L1 5000u 前提の M2 寄与 (¥1,295/本 を含む) / keeper 控除前 M2 算数 / P5 40–50% / falsified family の再試行 / 凍結 look の outcome 計算。

**作業**
- `data/cache/**` を ignoredPaths に追加すること (CI pin + runtime read)。08-14 以降の Render ログに依存する計画 (retention で不在)。
- broker realized のみで REG `carry-dip-v3-revival-watch` の R2 を autopilot 執行すること (凍結 estimand = demo pnl_pips の差し替え)。
- F4 推定器修正を 90 日へ外すこと / fit 窓の延長で直そうとすること (窓は既に 2 サイクル超)。
- 巡目上限なしのレビュー消化、P1 を上限超過で繰延すること、市場時間中の code PR マージ (09-22 は 2.5h で再起動 ×4)、tools/文書 PR の「無料」並行、日曜 20:00–22:30Z のマージ。
- daily report が全 API 失敗時に原因を書くこと。0 データで原因を KB に永続化すること。
- limit=1 snapshots での E1 export 試走 (生 skew 値閲覧)。export を 2 回以上実行すること。C3 combo を #20 composite に登録すること。
- ABG 辞書での #29 census 実行。Turtle S2 を N=0 で「N/PF/OOS PF 確認」として計上すること。
- user 手動売買を system 口座で行う案 (keeper flat ガード常時 skip、M2 帰属不能)。keeper 設計値 (cap / 窓 / units / RT / 銘柄 / target 520k→500k、効果 ≤¥260/月) の変更提案。
- **autopilot 禁止 (user または R1)**: carry_dip SL 150p 復元 / velocity_down 免除 / ps_aud_jpy 降格 (09-30 regate 委任) / kalman 契約変更 / M2 estimand 変更 / 0.2x 再基準化 (env・kv) / floor バッファ ¥12,000 縮小 (F4 凍結トリガ + 3 定数) / wg disaster SL 137p・rung 4000u (LOCKED 凍結値) / G3 N≥30・Wilson gate 緩和 (07-10 D-d / 08-05 template の撤回、ruin 63% 教訓と衝突) / keeper on-off / U3 前の live セル追加・lot↑。

---

## 7. 今回 refuted された主張 (レンズ・根拠)

1. **P_A claim 4「`data/cache/**` を ignoredPaths に追加して安全」** — kb+arith: `render.yaml:35–36` R3 決裁コメント、`tests/test_render_build_filter.py:29–35,94–101` の trading-path pin、`modules/yield_data.py:23,43` の Path 連結 read (grep 偽陰性)。
2. **P_A stop 3「F4 発火は audit_default 行で fit 非依存 → 推定器修正は 90 日へ」** — kb+arith: `nav_floor_projection.py:106–120` は行数 ≥7 で fit のみ書く、CSV 09-16 以降全 fit。本稿 spot check で確認。
3. **P_A Rank 1/10「無回答 = 12-03〜05 F4 強制起票」(既定挙動)** — 上記 2 の帰結。fit 発火は 12-04〜01-08。
4. **P_B C3「0.2x は今日の live 送信のどこにも乗算されていない」** — kb: `demo_trader.py:7126/7134` で乗算、`7571–7578` edge-cell 経路 (07-03 user 決裁) でも乗算 → L1 5000u × 0.2 → 1000u。arith: 文言偽・効果 (L0 1000u 不変) は真。**帰結が逆転**: D2(i) は表示裁定でなく実決裁。
5. **P_B Action 3(c)「D3 は template 既決 → 記録へ」** — kb+arith: L67 は 4.4 (証拠金) 側、L167 は単 leg worked example、多 leg 同時 disaster を 1 イベントと数えるかは未裁定。
6. **P_B C2 の部分「keeper=0 なら L3 で 1.086%」「L2+keeper=0 で 0.5% 超なら反証」** — kb+arith: 基底混在。4.2 ∧ SL150p ⇒ wg ≤0.166〜0.432% NAV 不変 → 反証条件自体が成立不能。結論 (第 2 セル必須) は強化。
7. **P_B Action 6「wg 0/7 累計」** — kb: 改定前 MARKET_HALTED cancel と改定後を混在。凍結境界は「改定後 qualifying 2 連続」で 09-13 は 1 件消費済み。
8. **P_B Action 4 期限「10-24 = 10 月 run 完了前」** — arith: 10 月 run は 26 RT / 3 RT/日 ≈ 9 営業日 → ~10-13 完了。
9. **P_C claim 4「carry_dip は demo +103.0 / broker −41.1 で符号逆」** — arith (API 実読): 同一 7 本 demo −16.4p、両方負。正符号は未突合 3 本 +130.9p。reconcile 対象 14 本。
10. **P_C thesis「API 生存のまま E1 second look / E12 first look を迎える」** — kb: E1 ingest = Myfxbook (OANDA API 非依存、memo §3 で P3 同旨を棄却済み)。API が gate するのは live 経路 (F2/F3) のみ。
11. **P_C claim 6「triage なしでは Rank 1–6 も間に合わない」** — arith: G4 §5.4 は live PR 3 本 4〜6 セッションで供給 10.5 内。Rank 1–6 ≈6.5〜9.5 < 10.5。正は「17 項目 + registry 全部は不可」。
12. **P_C claim 2 の反証テスト位相値 (10-10 ≈153 / 10-20 ≈131 / 11-20 ≈95)** — arith: 再現値 250/168/136 (keeper) / 207/140/104 (drift)。そのまま使うと 10 月に誤って「反証」成立。
13. **P_C Rank 7「Render ログ 08-14 以降を数える」** — arith: retention 30 日 (REG `carry-dip-live-to-shadow-drop-cause`「~09-26 消滅」) → 08-23 以降しか無い。価格キャッシュで代替可。
14. **P_C Rank 9「fit 窓を keeper 周期 ≥2 サイクルに」** — arith: 60 行 ≈10 週は既に 2 サイクル超、原因は窓未充填 + 位相。
15. **P_C Rank 5「REG 事前規定 R2 を broker 11/11 で autopilot 執行」** — kb+arith: REG 凍結規律「outcome・pnl_pips で勝敗」= demo 簿。demo 基準では N=14 EV +7.36 で不成立。
16. **P_A claim 2 / Rank 3 数字「税率 55% なら供給 17」「算数で不可能」** — arith: 42×0.45 = 18.9、レビュー時間の二重計上で供給は [10.5, 19]。
17. **P_A Rank 4 式「夜間 deploy 2 回/日」「再現率 2/7」** — arith: `data/monitoring/nav_floor_projection.csv` の日次 commit (d8f92726 03:12Z → 03:14 502) が第 3 源、N=2 で Wilson 4–40%。
18. **P_A Rank 6 / stuck 表「L0 上限 ~+10p/月 = 4.75×2.1」** — arith: 2.1 は qualifying 週末/月、leg 基準は 3.28/月 → 15.6p (実効) / 25.9p (凍結)。∞ の結論は不変 (346p の 13 倍以上)。
19. **P_A Rank 1 式「2 セル × wg 級 ¥1,295/本」** — kb: L1 5000u 前提の M2 寄与 = facts §G 引用禁止。arith: 凍結 BT EV × 入金前 NAV、実効 EV ¥779 vs 入金後 1 セル ¥750 で紙一重。
20. **P_B C5「s0 > 0.8 銭でも符号反転」** — arith: 方向が逆 (s0 > 0.8 なら user は得)。

---

## 8. caveat

- **wg 頻度は N=4** (4 週末/58 日)。Poisson 95% CI 0.57〜5.37/月で設計 3.28 を含む。「2.1 vs 3.28」を対置する全ての算数は点推定。
- **drift 13.7 円/日は測定値でない** (audit_default 82 − keeper 68.3 の差分仮定)。実測対照 30d clean live −27.2p ≈ 9 円/日。資金時計の区間は「上限側シナリオ」。
- **keeper 月額は ¥1,820〜2,080 の区間** (RT に −¥70 実測あり)。Σpl 実額は API 非露出。
- **floor の estimand**: FAQ 1730「NY サーバーの口座残高」= balance、keeper guard と F4 CSV は NAV。建玉ゼロの今は一致。「live 1 敗で消える」は決済後 balance で読む。
- **09-22 HTTP 盲目の engine 生存の直接証拠は 02:40 以降**、00:14–02:40 は tick 計数からの推定。「deploy 直後 hang」は N=3 の仮説で root cause UNKNOWN。HTTP 側時刻は orchestrator の Render 再クエリに依拠。
- **容量見積りは 5 日 / 12 PR の観測からの外挿**、CI なし。fx-roadmap-autopilot の実行頻度 (供給の分母) は未確定。
- **velocity_down 4 は bar 単位初回到達の上界** (再起動で `_price_history` 空 → fail-open、再到達しうる)。
- **E1 verdict (10-15) が最大の未知**: PASS (点推定 4%、Wilson 0.7–19.5%) なら U3 額と第 2 セルが変わる。UNDERPOWERED (modal) なら本稿の順位は不変。
- **carry_dip の broker 未突合 7 本の符号は未計算** — 「符号逆」を refuted したのは突合済み範囲の同符号であって、14/14 での結論ではない。
- **F4 シミュレーションは keeper 月初 1〜9 日消費・writer 毎日成功を仮定**。欠行パターンで数日動く。発火日は幅で引用。
- **M1 の成立条件 (会員単位合算) は status 頁に語 0 件で unverifiable**。V2 の既存会員適用も同様。
- **wg T_conv は改定後 0/1 で未測定** — N=41 到達月数は全て期待値。
- **本稿は文書のみ**。Render request log / app log は非対話で読めず、Rank 4(vii) 以降の恒久修理と Rank 5(c) の機構検証は user の workspace 選択後に確定する。

---

## 9. 未検証事項 (完全性批評 — この分析が検証していないこと)

1. 09-22 HTTP 盲目の root cause (H1 SQLite lock / H2 gthread 枯渇 / H3 edge) — Render request log 未読。09-15 / 09-21 との同型性も N=3 仮説のまま。
2. OANDA 会員ステータスの複数口座合算 (M1) と V2「新規口座開設後 Gold 付与」の既存会員追加口座適用 — 一次確認ゼロ。
3. 同一秒自己往復が OANDA 出来高に算入されるか (Gold 10 月) — 画面未確認。SILVER 時の API 停止日 (現 Gold の維持期限依存) も未確定。
4. carry_dip 未突合 7 本 (#677931/#681149/#837978/#847578/#549260/#573986/#677396) の broker 符号 — 未計算。D5 の入力が揃っていない。
5. 定義 A (入出金調整後 broker NAV 30d Δ) の真値 — CSV は 09-07 ¥276,304 → 09-21 ¥275,517 (Δ −¥787/14 日) しか無く、30d は未計測。
6. 09-22 blackout が E1 の coverage (§2.5-1 ≥90%) に与えた影響 — §6-2 で閲覧可能な品質メトリクスだが未計算 (verdict 時に併記が必要)。
7. Turtle S2 cron (`fx-ai-turtle-s2-d1`) の Render 上の稼働 (run 履歴 / 401・503) — 未確認。0 行は BT 基準で 30% 程度は自然。
8. ws3-round4 EUR divergence の FX 脚: Massive 1h cache が 05-15 / 07-03 で停止、refresh ジョブ不在、REG は ZN 単脚判定 — 11-15 TRIGGERED でも新 OOS 窓が作れない可能性を放置している。
9. explore 枠の現在値 (0/3〜2/3) — park (#25) と FAIL (#27) がスロットを解放するかの catalog 運用規則が明文化されていない。
10. fx-roadmap-autopilot の実行頻度 (SKILL.md に schedule なし) — 30 日供給の分母。
11. velocity_down 4 が 4 バーか再起動再到達の混入か — 価格キャッシュ経路 (Rank 5c) 未実施。
12. 再起動直後の velocity ガード fail-open 窓 (`_price_history` 空) の実長と、09-22 の 4 再起動で live 送信に触れたか (今日は fill 0 なので実害なし)。
13. daily report / nav_floor writer の HTTP 失敗が cron 側で露出されるか — tool 層は exit 1、cron 側 (daily-report.yml) の露出は未確認。
14. `spread_at_entry` 列が実測か定数か (2,002 行で USD_JPY / EUR_USD とも全時間帯 0.80 一定、G1 §5-6) — 摩擦 estimand (kb-14 無較正) に関わる、未検査。
15. 制約 4.4 / 4.5 (証拠金) の多 leg 同時評価 — D3 の ¥300k/¥472,800 vs ¥1,245,600 (旧 ¥900k、PR #279 P1 訂正) は 4.2 のみの計算、4.4/4.5 側は未計算。
16. `data/cache/yield` の 3 階層再分類 (runtime importer = `tools/rate_anchor_ingest.py` のみの主張) — grep のみで、web プロセス内の動的 import 経路までは未追跡。
17. D1–D12 の各項目の本文再監査 — D2(i) / D3 / D10 / D11 以外は memo 記載を引き継いでおり、stale 検査は未実施。
18. wg 09-27 / 10-04 / 10-11 が qualify するか — 事前には決まらない (P(3 週末 non-qualifying) ≈14〜17%)。F2 見通しは条件付き。
19. pycache purge の CI / pre-commit 組み込み — 未着手のまま。組み込まないと今後の counterfactual pin 全部が「読まれていない CF」の疑いを持つ (MEMORY 09-22)。
20. E23 Gate A の explore 窓限定再計算が「pass-1 測定可能性メトリクス」の範囲に収まる実装境界 — 本稿は境界を宣言しただけで、実装時の P-10 検査は未実施。
21. 30d 窓の 2,002 行検閲 (08-18 以降 34.8 日) により 60d レートは測定不能 — live N 時計の推定は全て 30d/39d 率の期待値。
22. U3 (ii) 縮退の可逆性 (口座切替時の `OANDA_ACCOUNT_ID` / `restore_mappings` / trade_id 名前空間の code 影響) — 記述級の列挙のみ、未検証。

> **UD1 結果 (2026-09-23)**: user 画面確認で **GOLD** 表示 (keeper $520k 算入)。§4 UD1 の SILVER 分岐は不発、packet v0 の前提維持。詳細は [[integrated-decision-packet-d1-d12-2026-09-22]] 末尾「UD1 結果」。
