# 「勝てる方法」決裁メモ v2 — 5 視点提案 × 2 レンズ批判 × 完全性批評の統合、分母 = time-to-M2 (2026-09-20)

作成規律: 文書のみ (価格データ・DB 計算ゼロ、P-10 LOCK 非接触)。数字は入力 (提案 5 本 + 批判 10 本 + 完全性批評 + 棚卸しノート 4 本) から転記し、load-bearing なものは KB 原本で再照合した (照合結果を各行に併記)。正式ミッション = M3 系列 (+2〜3%/月 複利)、経路 M1→M2→M3、**全施策のスコアリング分母は time-to-M2 短縮** (U1=(b) 2026-09-17、`KB/decisions/u1-mission-redecision-2026-09-17.md` L1–L11 実読)。旧 anchor は使わない。批判で refuted された核は採用せず、salvageable のみ拾う。

略号: KB = `/Users/jg-n-012/test/fx-ai-trader/knowledge-base/wiki/`、RAW = `/Users/jg-n-012/test/fx-ai-trader/knowledge-base/raw/`、MEM = `/Users/jg-n-012/.claude/projects/-Users-jg-n-012-test-fx-ai-trader/memory/`、SP = `knowledge-base/raw/analysis/path-to-win-2026-09-20/` (棚卸しノート 4 本 + arith_29.py を永続化済み)、REG = `KB/decisions/prereg-trigger-registry.json` (67 entries、2026-09-20 実読)。提案は P1 (#29 研究供給) / P2 (CCE 執行変換) / P3 (keeper 存続税) / P4 (N 時計保全) / P5 (2 レッグ D1 ブック) と呼ぶ。

前版 (harness 切り詰めで P1/P2 のみ受領) との差分: 5 本すべて受領。P3/P5 を正面から採否判定。ランキング・主経路・実行計画は白紙から再構成。§2 の verified 事実と付録 A は前版から継承 (再照合済み)。

---

## 1. TL;DR

**「勝てる方法」への正直な答え: 5 提案・10 批判・完全性批評は、独立に同じ不動点に収束した — 現 NAV ¥275,517 では OANDA Gold 維持の keeper (¥2,080/月 = 0.755%/月) が M2 (+0.5%/月 NAV 実現) を 1.51 倍で食い、これを埋める唯一の階段 L1 5000u は制約 4.2 で NAV ≥ ¥300k まで開かず、その NAV を keeper 自身が毎月削る。この自己強化ループを Claude の施策空間 ($0 レバー) は 1 本も解けない。time-to-M2 は U3=(i) 入金 (user 専権) を除くあらゆる手に対して ∞ に発散している。5 提案の核は 5 本とも批判に耐えなかった (core_survives = false × 5)。**

- **主経路 (1 本)**: **統合決裁パケット 1 本** — U3 (入金 / 縮退 / 停止) + U2 (資本上限) + M2 会計 (keeper 込み NAV 実現のまま必要 gross を再導出するか、estimand を変えるか) + M2 定義の内部不整合 2 点 (0.2x ラダー文言 vs carve-out 非乗算 / 「2 セル」の単位) + carry_dip disposition + ps_aud_jpy 再上程 を **1 本のパケット**に束ね、Claude が 10-08 (E1 cutoff) までに自走起票、user は E1 verdict (10-15) を見てから 11-30 (packet §U3 期限) までに一言で返す。**これだけが分母を ∞ から有限に変える**。5 提案が延べ 32 件 (重複除去 ~18 件) の決裁を 4 通りの期限で要求している状態を止める。
- **併走 (補助 2 本)**:
  1. **執行契約コンフォーマンスの「検知器 + ガード + 台帳」版** (P2 と P4 の salvageable の union、fail-closed block / live-hold / default-on-timeout は外す) — storm guard 4 点 (`OandaBridge.modify_sl`)、broker 台帳 readout で carry_dip 残 4/11 を閉じ 11/11 の符号を確定、宣言 bracket ↔ ON_FILL SL/TP の **log-only** 突合 + counterfactual pin、時計台帳 v0。全て autopilot R3。PnL は 1p も生まないが、「M2 判定に使える clean N」が現在ゼロ速度で積まれている事実を可視化し、floor バッファ ¥13,517 への storm/tail 打撃を止める。
  2. **weekend_gap G0' 分岐の事前固定 (今夜 2026-09-20 21:00 UTC → 不成立なら 09-27、REG `weekend-gap-execution-amendment-g0prime` 09-28)** — fill 1 本で F2 resolve = PASS→live 変換係数がプロジェクト史上初めて N=1 で測れる。2 連続不成立 → 執行モダリティ R1 再審 (凍結分岐) → M2 の第 2 セル候補が消え、主経路の全分岐が 2028+ へ後退する二値イベント。
- **止めること**: (1) #29 を time-to-M2 レバーとして起案 (無条件寄与 +0.4〜1.6pp、S1 census のみ残す)。(2) carry_dip SL 150p 復元 / ps_aud_jpy 降格 / kalman 契約変更を autopilot R2/R3 で執行 (3 件とも KB 記録上 user 決裁事項)。(3) β バラストを system 口座に建てる (P5 分岐 B の月次合計は keeper 込みで負)。(4) keeper spread cap 1.0→0.5p (KB の全 26 RT が 0.7–0.8p、≤0.5p 観測ゼロ)。(5) M2 の estimand を user 上程なしに書き換える (keeper 除外 / 30d→6 ヶ月 rolling)。(6) 「臨時スキャンを撃たない」と宣言する (REG `edge-supply-scan-monthly` は 0 本なら臨時 R3 を規定 — S1 census を臨時スキャン記録にして規則内で満たす)。(7) L1 5000u 前提の M2 寄与引用、keeper 控除前の M2 算数引用、`nav_floor_projection.csv` fit 値 (242 日) の現況引用。(8) 1-unit 実弾プローブ (SVK 決裁の DB 非書込み要件と矛盾、per-pair 1 position で live 送信を block)。(9) 決裁を「期限なし carry-forward」で転記すること。

---

## 2. 規定事実 — 全体を決める算数 (完全性批評 strongest_single_fact を再照合して **採用、5 点修正**)

### 2.1 keeper コスト vs M2 (最重要、KB 原本で verified)

| 量 | 値 | 出所 (照合済) |
|---|---|---|
| NAV | **¥275,517** (09-14〜09-19 不動) | `data/monitoring/nav_floor_projection.csv` 末尾 3 行 (実読) |
| floor | **¥262,000** = OANDA JP 「口座残高 25 万以上」+ バッファ ¥12,000 | `tools/nav_floor_projection.py` L34 / `modules/status_volume_keeper.py` L74 / `KB/analyses/live-frequency-and-oanda-status-survival-2026-09-01.md` L8 (FAQ 720 原文 = **残高**) |
| 余裕 | **¥13,517** | 算数 |
| keeper 実測 | **26 RT × ¥80 = ¥2,080/月 = 0.755%/月 NAV** (全観測 RT は −¥80 or −¥70 = 0.8/0.7p) | `KB/index.md` L149 (tx 709548〜709596)、L134 / `RAW/trade-logs/2026-09-10.md` L119–121 — **verified** |
| M2 定義 | **+0.5%/月 (NAV 実現、30d rolling) = M1 + 防御解除ラダー (0.2x→1000u→5000u) + 2 セル以上** | `KB/analyses/monthly-target-rederivation-2026-07-10.md` L44 — **verified (実読)**。KPI L3 = NAV 実現月利 = mission (L48) |
| open item | 「M1/M2 の目標基準が keeper 差し引き後か」= **未解消** | `KB/index.md` L149 末尾 / `KB/decisions/process-meta-audit-2026-09-07.md` L91 goals-1 — 09-20 時点で解消記録なし |
| 制約 4.2 | worst-case 1 イベント ≤ **2.5% NAV = ¥6,888** | `KB/analyses/lot-ladder-template-2026-08.md` L65 / `tools/lot_ladder_calc.py` L34 `CELL_EVENT_LOSS_CAP_PCT=0.025` — **verified** |

**帰結 (SP `ground_capital_clock.md` §2c、5 提案の算数批判 5 本が独立に同値を再導出)**:
- M2 が NAV 実現定義である限り、edge 側の必要 gross = ¥1,378 + ¥2,080 = **¥3,458/月 = 1.255%/月 = 346p/月 @1000u、69p/月 @5000u**。
- **現 NAV では L1 5000u が全候補で制約 4.2 違反**: wg / carry_dip 宣言セルとも disaster SL 150p × ¥50 = ¥7,500 > ¥6,888 (template 表 L167 の「可」は NAV 326k 前提)。L1 開通 = **NAV ≥ ¥300,000 (JPY ペア) / ≥ ¥450,000 (USD-quote、¥15/pip)**。`lot_ladder_calc.py --packet` は N がいくら積まれても HOLD を返す。
- **∴ 現 NAV では全セル L0 1000u。L0 で 346p/月 = 最良 net EV (wg 凍結 +7.90p、実効 +4.75p) の 3–6 倍が要る → 現行定義 × 現 NAV × L0 では time-to-M2 = ∞** (期待値ではなく上限の問題)。
- **NAV を上げても keeper は JPY 固定額なので必要セル数は増える**: 定義 A (NAV 実現) では wg 級 L1 (凍結 EV ¥1,295/本、実効 EV ¥779/本) が **現 NAV+入金で 3 本 (実効 5 本)、NAV ¥416k で 4 本 (実効 6 本)** (P3 算数批判 §1)。「2 本で足りる」は **定義 B (edge-only、keeper を資金時計で別計上) かつ NAV ≥ ¥300k** でのみ成立 (2 × ¥1,295 = ¥2,590 > ¥1,378; 実効 EV でも 2 × ¥779 = ¥1,558 > ¥1,378)。**定義 B は M2 の estimand 変更 = user 専権 (R1)、R4(c) の「keeper 控除後で再導出」は必要 gross の計算指示であって定義変更ではない** (P3 KB 批判)。
- **M2 定義文書の内部不整合 (未裁定)**: rederivation L44 は「防御解除ラダー 0.2x→1000u→5000u」を必要条件に含むが、ladder L73 は「グローバル DD lever は rung units に乗算しない (carve-out 契約)」— 前者なら L1 に 0.2x 再基準化 (eq_peak ラチェット +988p、コード変更 = user 決裁、`shortest-path-decision-memo-2026-07-10.md` §1c) が前提、後者なら不要。P3 は後者、P1/P2 算数批判は前者を採った。**どちらが SSOT かを決めないと L1 到達日が計算不能**。
- **「2 セル以上」の単位が未定義** (type か type×pair×dir か、相関セルで満たせるか)。現行 live ロースタと候補 2 セル目 (kalman / carry_dip / #29 BoJ レグ / P5 β) は **全て USD_JPY・全 LONG** (SP `ground_edge_inventory.md` §4.4) で、`per-pair 1 position` (`KB/analyses/system-reference.md` L100) + `hedge_block` により **同じ 1 スロットに互いに排他的な玉を予約している** (#29 の BoJ hawkish = USD_JPY short は他の long が開いていると送信不能)。

### 2.2 資金時計 (keeper と floor は結合、推定器は月内位相で振動)

| burn 前提 | floor 到達 | F4 (−90d) 発火 | 出所 |
|---|---|---|---|
| keeper のみ 68.3 円/日 (edge PnL=0) | **2027-04-06** (6.5 ヶ月) | 2027-01-06 | SP `ground_capital_clock.md` §3c |
| audit_default 82 円/日 (keeper + drift 13.7) | **2027-03-03** (5.4 ヶ月) | **2026-12-03** | `tools/nav_floor_projection.py` L35–38 / CSV audit_default 行 |
| fit 現値 55.8 円/日 | 2027-05-19 | 2027-02-18 | CSV 09-19 行 — **位相依存の楽観値、現況引用禁止** (fit 窓 7 行 < keeper 周期 30 日、5 日で 164→242) |

- keeper を続ける = edge が月 +0.755% 以上出さない限り残高条件の方が先に割れる。keeper の floor ガード (L74) は失敗モードを「残高割れ」→「翌月 Gold 失効」に変えるだけで、どちらも API 停止 (復帰 = token 再発行 + 最短 1 ヶ月、survival doc L21)。
- **floor の estimand は「口座残高」(balance)** で、F4 時計・5 提案は NAV (evaluated equity) を読む。現在は建玉ゼロで一致しているが、含み損益を常時抱える設計 (P1 D1+5 保有 / P2・P4 の SL 150p 復元 / P5 β 常設) では balance と NAV が乖離し、floor 到達の定義が提案ごとに変わる (完全性批評 §4 — 採用)。
- **決裁遅延のコスト**: 1 ヶ月 = ¥2,080 = 余裕の 15.4% (drift 込み 18.5%)。無回答の既定挙動は「F4 発火時に再上程・それまで現状維持」(`KB/decisions/mission-capital-redecision-packet-2026-09-10.md` L63 実読) = **毎月余裕の 15% を消費し続ける選択**。

### 2.3 M2 より前に発火するプロジェクト kill 条件 (REG 実読、id 訂正)

| 条件 | REG id | 期日 | 内容 | 見通し |
|---|---|---|---|---|
| F3 | `project-falsification-f3-m1-durable-cell` (前版の `f3-cell-throughput` は誤 id) | **2027-03-31** | M1_STRONG 該当セル 0 → 段階設計再導出 | M1_STRONG 0/117。最速セルでも N≥30 が 2027-Q1〜Q2 → **発火確率高** |
| global-stop | `project-global-stop-quarterly` | **2027-03-31** | 連続 2 四半期 OOS PASS 0 ∧ 正セル 0 → 全面棚卸し | base rate 4% → **発火確率高** |
| F1 | `project-falsification-f1-supply-space` | 2027-02-05 | E1/ECG/E12 から OOS PASS 0 → **有償データ / venue 変更 / 終了 の三択を強制起票** (結合 FAIL 事前見積り 61–89%) | venue 変更は既に三択に在る — ただし floor (2027-03〜04) はその 1 ヶ月後で **順序が逆** (完全性批評 §1 — 採用、feasibility を F1 前に持つ) |
| F2 | `project-falsification-f2-wg-live-conversion` | 2026-12-31 | wg live N=0 → PASS→live 変換未実証 | 今夜 / 09-27 で決まる |
| F4 | `project-falsification-f4-nav-floor-clock` | days_to_floor ≤90 | 入金/縮退/停止の強制起票 | audit_default で 2026-12-03 |

### 2.4 その他の規定事実 (verified)

- **着手可能な能動研究ライン = 0 本** (#27 FAIL 09-18)。時限 3 本 (E1 10-15 / ECG 11-06 / E12 2027-02-05) は金でも前倒し不能 (SP `ground_supply_pipeline.md` §0、§4)。**REG `edge-supply-scan-monthly` は「着手できる本数が 0 なら期日を待たず臨時スキャン (R3)」を規定** (実読) — P1/P4/P5 が揃って「臨時スキャンを撃たない」としたのは規則違反。
- **唯一の OOS PASS = weekend_gap_fade、live 約定 0/4 event** (07-26 infra / 08-02, 09-06 MARKET_HALTED / 09-13 ABANDONED_DRIFT +41.0p は設計どおり放棄)。AMENDMENT B 実効 EV +4.75p/event、fill 成立率見積 点 94% / 保守 75%、qualifying 実測 4 件/58 日 = 2.1/月 (設計 3.28 の 64%) (`KB/strategies/weekend-gap-fade.md` L37–38, L114–118 / `RAW/trade-logs/2026-09-16.md` L241)。**戦略カードのイベントログは 09-10 で止まっており 09-13 の記載が無い** (P4 KB 批判 — 読み手欠落の実例)。
- **唯一の「正 EV 候補」carry_dip は broker 突合 7/11 で ≈ −41.1p (符号逆)、残 4 本 (#677931/#681149/#837978/#847578) 未突合、SL 契約破棄 11/11 (9.8–28.5p vs 宣言 150p)、TP 65.5p 固定 (最有力原因 = `_QUICK_HARVEST_MULT 0.85` 非免除、80×0.85=68p — P2 KB 批判)、storm 5/11** (`KB/strategies/usdjpy_carry_dip_accumulator.md` §(4)(5)(6))。**kalman も非適合**: #859468 の as-placed SL ≈13.8p vs 宣言 1.5×ATR ≈21.8p (P2 KB 批判)。**契約復元は 2026-08-07 session L26 で「user 決裁事項」と分類済み** (実読: 「live の SL 幾何を 18.8p → 150p へ 8 倍にする変更であり、08-05 の判断 (user 決裁事項) を維持」)。REG `carry-dip-v3-revival-watch` の事前規定 R2 = 「deduped LIVE N≥10 ∧ EV<0 → lot 下げ or LIVE 停止 (shadow 継続)」、backstop 2026-11-30 (実読)。
- **ps_aud_jpy: N=4 / −180.0p = book 全損の 27.3%、bracket TP +1,088p / SL −130p 宣言不一致・未診断。demote 見送りは 2026-08-12 user 決裁済み・判定は LOCK watchdog に委任・「早期介入は user 決裁のみ」** (MEM `project_549250_incident_mc_ruin_fix_2026_08_05.md` L16, L20 実読)。REG `ps-carveout-regate-post-172` 09-30 (N<10 なら stale 分岐)、`ps-seat-supply-hourly-c1-coverage` 09-25 (帰属前に供給是正を重ねない)。
- **bypass set は code 上 12 type = vix_carry_unwind / usdjpy_carry_dip / sweep_reversion_eurgbp_late / weekend_gap_fade / ps×5 / kalman×3** (`modules/demo_trader.py` L10545–10570、P2 KB 批判) — 提案の「wg×3 / carry_dip / ps×5 / kalman×3」はペア数と type 数を混同。demote 済み vix と retire 済み sweep が set に残存。
- **最終 live fill = #893161 2026-09-11T11:02:36Z → 09-18 freshness stale 初発** (`RAW/trade-logs/2026-09-18.md`)。執行系 3 提案の fill 率見積りは engine tick が生きている前提だが、現在値の引用がない (完全性批評 §13)。
- **Gold 10 月維持は「見込み」のみ**: keeper $520k/$520k target_reached (09-17 実測) は事実だが、OANDA が同一秒自己往復を出来高に算入した証拠 (ステータス画面「来月 GOLD」) は KB に記録なし (grep: index / log / feasibility / memory — 該当ゼロ、`supply-space-feasibility-2026-09-17.md` L11 も「維持見込み」)。**5 提案全てが未検証で依存**。
- **U3 (ii) 縮退の blast radius は survival doc L14 より小さい**: 「E1 positioning ingest (OANDA v3 order book) 停止」は stale — E1 は 2026-07-15 に Myfxbook Community Outlook へ転換済み (`modules/myfxbook_client.py` 実在、MEM `project_ws3_external_hypothesis_transition_2026_07_13.md` L28–35)。API 停止で止まるのは live 執行・OANDA テレメトリ・OANDA 価格 primary (Massive/yfinance fallback で shadow 継続)。
- **keeper の tail**: 決済レグ失敗時は `open_trade_ids` を state に永続化し「次 cycle で回収」(`modules/status_volume_keeper.py` L285–292 実読) — orphan 追跡はある。ただし回収までの間 10,000u (edge lot の 10 倍) が裸で立ち、σ_day 60–100p × ¥100 = ¥6–10k = バッファの 44–74% の露出 (完全性批評 §2)。emergency_kill 尊重は 09-11 に修理済み (L154–181)、G3 (実弾コンポーネント台帳) / G6 (台帳外約定検知) は起票のみ (`KB/decisions/live-governance-gap-audit-packet-2026-09-10.md` L36, L39, L65)。
- **REG に `review-backlog-253-257-digest` は不在 (67 id 全数照合)、PR #272 は 09-20 時点 OPEN (`gh pr view 272`: mergedAt null)**。MEM の「PR #272 マージ済み」は stale。P1 step 3 / E23 P1 消化の前提 = PR #272 マージ。
- **摩擦モデル 4.5 ヶ月無較正 (kb-14、期日 09-18 超過)、即席実測は過小推定側 (EUR_JPY 1.9x)** (`KB/decisions/blocker-refutation-2026-09-10.md` L66)。加えて `pnl_pips` は fill 価格に摩擦内蔵 (`friction-adjusted-ev-map-2026-07-07.md` §7-2) で、risk dashboard の friction 行 (09-18 63.6p) は二重計上疑い — 09-16 log の「未控除」主張と KB 内で矛盾。**本メモの net EV / 摩擦数字は全て未較正 estimand を継承**。

---

## 3. 提案ランキング表 (分母 = time-to-M2 短縮、baseline = KB 中央 2027-Q4〜2028 / P(M2≤2027 末) 15–25%、`process-meta-audit-2026-09-07.md` L106 — ただしこの baseline 自体が keeper 未反映・L1 可 (NAV 326k)・fill 100% 前提で楽観)

**再導出した baseline**: 現行定義 × 現 NAV × $0 施策 → **∞**。U3=(i) 入金 (≥¥25k で L1 開通、+keeper 月 ¥2,080 × 月数) + 定義 B → binding = wg N=41 (fill 1.97–2.77/月で 2027-12〜2028-06) ∧ 第 2 セル (E1 second look 2027-01-06 PASS → 実装 1 ヶ月 → live N≥30 2–6 ヶ月 → G3 2027-05〜09、P(PASS) ≈ 4–19%) → **中央 2028-H1、P(M2≤2027 末) ≈ 1–5%**。定義 A (NAV 実現) なら 3–5 セル必要 → **2028-H2 以降**。**どの分岐でも 2027-03-31 (F3 / global-stop) が先に来る**。

| Rank | 施策 | 核の生存 (批判 2 レンズ) | 算数レンズ再計算 t2m2 | 採用度 | 理由 |
|---|---|---|---|---|---|
| **1** | **統合決裁パケット: U3 / U2 / M2 会計 (A: NAV 実現 keeper 込み・必要 gross 1.255% を定義文書に反映 vs B: edge-only・keeper は資金時計で別計上) / M2 定義不整合 2 点 (0.2x ラダー文言 vs carve-out、「2 セル」単位) / carry_dip disposition / ps_aud_jpy 再上程 / kalman DRAFT packet 承認** — P3 step 4・7・10 + P5 step 1・3 + P2 決裁 6 件 + P4 決裁 3 件 + 完全性批評 §7・§8・§16 の統合 | 提案の「核」ではなく 5 本の salvageable が重なる交点。P3 診断 (keeper 0.755% > M2 0.5%、損益分岐 NAV ¥416k / ¥832k / ¥2.08M) は算数批判 2 本とも「正しい、KB 3 箇所に散在、定義文書未反映」と確認 | **∞ → 有限**にする唯一の変数。定義 A + 入金 → 3–5 セル → 2028-H2+。定義 B + 入金 ≥¥300k → 2 セル → 中央 2028-H1、P(≤2027 末) 1–5%。無回答 (既定挙動) → 12-03 F4 強制起票まで現状維持 = 余裕の 15%/月消費 | **採用 (user 決裁上程、Claude は packet を 10-08 までに自走起票、期限は 11-30 の 1 本に統一)** | time-to-M2 の値そのものを決める。研究・執行は分母を有限にした後にしか効かない。5 提案が同じ決裁を 3 度ずつ異なる既定・期限・分類で要求している (完全性批評 §16) — 実測レイテンシ B 型 18 日 (`blocker-refutation-2026-09-10.md` §2) で直列なら 30d を超過するため、1 パケットに束ねる |
| **2** | **執行契約コンフォーマンスの検知器 + ガード + 台帳版** — P2 step 1 (log-only 化) / 3 / 4 / 6 + P4 step 1 / 2 (block 外し) の union | **P2 核 = refuted (KB high / 算数 high)**: autopilot R3 で carry_dip 契約復元 + 全ゲート estimand 統一は KB の決裁分類 4 点と衝突 (08-07 user 決裁事項 / preserve-exit-overlay §5 前例 / kalman packet は DRAFT / wg G1・G2 凍結値変更は R1)、fail-closed は kalman も block、¥636/月 摩擦停止は送り続ける carry_dip 分が残り不成立。**P4 核 = refuted (KB high / 算数 high)**: default-on-timeout は packet L63 の既定挙動と逆、ps_aud_jpy live-hold は 08-12 user 決裁を無回答で反転、1-unit プローブは SVK 決裁 (DB 非書込み) と矛盾 + per-pair 衝突 | P2 自己申告 −1〜2 ヶ月 → **≈0〜0.6 ヶ月** (成功枝 Δ0〜3 ヶ月 × P 0.10–0.20、L1 は現 NAV で HOLD、carry_dip 宣言セル N_required は WR≥80% でなければ 41 を超える)。P4 自己申告 3〜6 ヶ月 → **0〜1 ヶ月** (2 本目 PASS 条件付き 0.11–0.39 × 3–6、成分 (i)(ii) は M2 の critical path 外、(iii) は検出≠修理で半分以下)。**t2m2 直接寄与 ≈ 0。価値 = 判定到達時間 (carry_dip 11/11 符号確定 → revival-watch R2 が読める) + floor バッファ防御 (storm / tail)** | **部分採用 (autopilot R3)**: storm guard 4 点 + fault-injection pin 4 本 + storm 検知器 / `tools/broker_ledger_reconcile.py` で carry_dip 4/11 突合 / `EXEC_CONTRACT` 表 (code の 12 type と一致) の **log-only** 突合 + counterfactual pin (#677402 NG / #709570 NG / #859468 NG / tx 837792 OK) + Discord 読み手 / 時計台帳 v0 (event 数で数える) / readout 欠落修復。**契約復元・fail-closed block・estimand 統一・live-hold は Rank 1 パケットへ** | 「宣言と別の戦略の N を積んでいる」は verified で、その N は promote にも falsify にも使えない。ただし直す権限は user にあり、Claude が先行できるのは「測る・守る・突合する」まで。broker 11/11 で EV<0 が確定すれば REG 事前規定 R2 (LIVE 停止・shadow 継続) は autopilot 執行可 — 復元して再開するかが user 決裁 |
| **3** | **weekend_gap G0' 分岐固定 (09-20 / 09-27) + F2** | 既定路線 (REG g0prime 09-28) — 5 提案とも P2 step 5 / P5 step 7 以外は条件付けていない | fill → 経路 A 生存 (L1 起案 2027-12〜2028-06、NAV ≥ ¥300k 必要)。**2 連続不成立 → R1 再審 = 第 2 セル候補消失 → Rank 1 の全分岐が 2028+ へ後退** | **採用 (record-only + 分岐手順)** | PASS→live 変換係数がプロジェクト史上初めて N=1 で測れる二値イベント。戦略カードのイベントログ更新 (09-13 未記載) を同時に |
| **4** | **P3: keeper 存続税の構造是正** | **核 = refuted (KB high / 算数 high)**: (i) 「M2 分母から外す」= estimand 変更 (R1、R4 目的「達成に見えて達成でない倒錯の排除」と正面衝突)、(ii) ¥/RT 半減 = KB の全観測 (0.7–0.8p) が否定・≤0.5p 観測ゼロ・day≥15 緩和で Gold 未達リスク、(iii) 残余は既承認・既起票 (index L149 / meta-audit L91 R4(c) / packet §U3 / round4 §4(d)) の再掲。診断部分は算数批判 2 本とも「正しい」 | **0 ヶ月** (U3 入金を除く)。(B) keeper ¥1,300 でも drift 込み runway 7.9 ヶ月 < wg G3 10.8 ヶ月で floor 先着。(C) NAV ¥416k では必要セル 4 本 (実効 6 本) に増える | **部分採用 (R3、Rank 1 に吸収 / 独立実施)**: step 4 = R4(c) 未執行分の執行 (M2 定義不変、必要 gross 表 + NAV 損益分岐表 + Tier A KPI に keeper%/NAV と floor 予測日) / step 5 = F4 推定器修正 (keeper 確定分 + edge 30d 実測に分解 or 窓 ≥30 暦日、counterfactual pin) / step 1 縮小版 = keeper `history` の `pl_jpy`/`spread_pips` を `get_worker_status` に露出 + 月次 KB 行 / step 9 = `lot_ladder_calc.py` で毎月 L1 可否文書化 / step 6 = 相互リンク 1 行。**step 2 (cap 0.5p) / step 3 (口座出来高カウント、効果 ≈ −¥100/月) は起案しない** | keeper は必要セル数を 2→3 に押し上げる 1 変数で、「どのエッジ発見でも解けない構造問題」は過大 (wg 級 L1 3 本で吸収可)。AMENDMENT B の EV 半減 (7.90→4.75p、3→5 本) の方が影響が大きい。P3 の真の価値は「M2 の会計を定義文書に反映せよ」の 1 点 |
| **5** | **P1: #29 dense-stance 中銀声明ドリフト (D1+5)** | **核 = refuted (算数 high)、KB レンズは適法性のみ肯定 (medium)**: 起案自体は E23 §6 復活経路・非 ban・非 look で適法。ただし Wilson N=41 と 15p/event は同時成立せず (N_required 160)、7 CB 上限 4.58 event/月 (6 は到達不能)、keeper 控除後 +0.49%→−0.03%、L1 は制約 4.2 違反、P(PASS) 8–12% の根拠なし (headroom 通過後の決着 0/4、方向 prior は E23 §1 で消費済み)、TDW 学習標本が explore 窓と重複、CC BY-NC 使用時は PASS でも live 転送資格なし (E23 §0-4) | 提案 +6–8pp → **+0.4〜1.6pp** (P(PASS) 4–8% × P(M2≤2027\|PASS) ≤0.1–0.2)。PASS 分岐でも M2 最速 2027-Q4、中央 2028-H2〜2029。USD_JPY レグの swap は E23 Gate D 1.5p/5bd bound (pre-reg L66) を継承すると 3–5 倍過小評価 (e20 feasibility 実勢 −5〜−7p/event、完全性批評 §9) | **部分採用 (S1 census のみ、$0・outcome 非接触・「研究 intake」会計)**: license-free 凍結 lexicon を primary、TDW/WCB は記述 secondary (研究利用は E23 §0-4 で可 — user 決裁で止めない = 幻ブロッカー再生産の回避)。結果を **C1–C6 形式の臨時スキャン (単独候補) として記録** = REG 規則充足。「LLM zero-shot 採点は知識カットオフ汚染のため恒久禁止」を text モダリティ C5 規律として KB 新規追加。explore LOCK の可否は S1 結果 + PR #272 マージ後の E23 P1 監査の後に別途裁定 (本メモは起案を承認しない)。step 7 の「UNDERPOWERED 時 C3 combo を #20 に登録」は E1 §4.4/§6-3 違反 (P-10 隣接) → second look 後に限定 | 研究供給の WIP 規則を満たす手段としての価値は残るが、time-to-M2 レバーではない。F1 の分子・分母に #29 は入らない (REG 凍結) |
| **6** | **P5: 15m α 工場を閉じ、USD_JPY β + wg の 2 レッグ D1 ブック** | **核 = refuted (KB high / 算数 high)**: β 根拠 3 点が全て estimand 不一致 (8h+ ホールド +138k は非 claim 記述所見で同窓 buy&hold −48k / sleeve +66.1p は carry_dip α の demo 簿で broker 符号逆 / E20 「全 fold 正」は棄却 family の explore サブグループ、pre-2022 は全負)。分岐 B (NAV ¥1M) の月次合計 = keeper −0.208% + swap +0.10% + wg L0 +0.01% = **−0.09〜−0.10%/月で符号が負**、M2 には drift +0.59%/月 (USD_JPY +7.3%/yr) が必要 = コイン投げ。「中央 2027-Q3〜Q4」と「P 40–50%」は両立しない。U1 (M3 = ミッションそのもの、3 日前) を新データなしに格下げ、M2 estimand を 6 ヶ月 rolling へ変更、step 4 の autopilot R2 表記は 08-12 user 決裁と REG 2 本を覆す。per-pair 1 position で wg/kalman/carry_dip と衝突 | **改善なし**。到達確率 40–50% は USD_JPY の方向のコイン投げで、システム寄与は −0.09%/月。分岐 A (現 NAV) の「到達不能」のみ正しい | **棄却 (核)。部分採用**: step 6 Turtle S2 D1 shadow readout (pre-reg 履行、learning/ に月次レポート 0 本 = write-only、昇格は R1) / step 1 U3 前倒し (Rank 1 に吸収) / step 2 4原則 1/4 の**監査** (閉じる前提でなく、meta-audit §8 盲点 #1 の U9 議題として) / 診断部分 (keeper > M2、floor 結合)。**β は system 口座で起案しない (P3 stops と一致、round4 §4(d) 維持)** — user 手動キャリーは別口座で M2 母集団の外に置く | 「keeper を払い続けながら USD_JPY β に賭ける」と同値。分散ゼロ (2 レッグとも USD_JPY long)。P5 自身が認める「暦時間の劇的短縮ではない」 |
| **7** | **ps_aud_jpy de-risk** | 完全性批評 §10 / P2・P4・P5 が 3 通りの覆し方で要求 | t2m2 効果ゼロ、floor 防御のみ (1 fill −45〜−123p = バッファの 3.3–9.1%、月 ≈ −¥900 で floor 延伸 +2 ヶ月) | **user 決裁 (Rank 1 パケット内)、既定 = 09-30 regate に委任** | 08-12 user 決裁 (demote 見送り・watchdog 委任) を autopilot / default で反転させない。bracket 不一致の**診断**は R3 で今日可能 |
| **8** | **venue 変更の feasibility (record-only、$0)** | 完全性批評 §1 (誰も検討していない) | keeper=0 なら必要 gross 1.255%→0.5% (2.5 倍圧縮) = どの $0 レバーより大きいが、可否・spread・最小 lot は KB 不在 | **採用 (R3 文書、F1 前に順序を正す)** | REG F1 TRIGGERED の三択に「venue 変更」は既在だが、floor (2027-03〜04) は F1 (02-05) の直後で選択肢を持たずに迎える。国内 API 提供社の条件を記述級で並べるだけ (決裁は F1 後) |
| **9** | **U5 fx-codex-runner Suspend + 固定費台帳** | 完全性批評 §11 | t2m2 効果ゼロ。固定費 > M3 月額 (¥5,510〜8,266 再計算値) なら edge 有無に無関係 | **user 決裁 (dashboard 操作は user のみ)** + Claude が台帳の器 | KB に月次固定費合計なし |

**棄却した主張 (採用しない、引用禁止)**: P1 time_to_m2_estimate 全文 (+6–8pp / L1 +1.4%/月 / N=41 2027-08 / 「スケジュールを崩壊させるものは無い」) / P2 「M2 判定可能 N 12–15/月」「¥636/月 摩擦停止」「storm は Gold を直接脅かす」(Gold は取引量条件、tx 数は文書化条件に無い) / P3 「¥/RT ≤ ¥50」「API 停止 → E1 ingest 停止」「runway 10.4 ヶ月」/ P4 「期待 3〜6 ヶ月短縮」「48 日 = 決定論的バグ」(失われた N は 2 event)「既存 pending 6 件」(t8 は 09-17 RESOLVED) / P5 「P(M2≤2027 末) 40–50%」「M3 完全達成でも月 ¥6,500〜9,700」(2〜3% × ¥275,517 = ¥5,510〜8,266、packet 側の数字が本文と不一致)。

---

## 4. 実行計画

### 4.1 30 日 (〜2026-10-20) — 日程上の固定点: 09-20 wg / 09-25 ps 帰属 / 09-28 g0prime / 09-30 ps regate / 10-08 E1 cutoff / 10-14 daily review 30d / 10-15 E1 verdict + U2 推奨期限 / 10-18 第 6 次スキャン

**autopilot 容量の予算 (完全性批評 §12 — 採用)**: live 経路コード PR は single-writer 直列で **3 本に圧縮** (P2 4 + P4 3 + P3 2 → 3)。tools / 文書 PR は並行可。合計 ~5 セッション。欠陥税 75% を前提に、各 PR は counterfactual pin 同一コミット + `tools/pr_review_gate.py` + `@codex review` 再要請 + inline thread 直読み。

**autopilot (Rule 2/3 or record-only)**
1. [D+0〜7、10-08 まで / R3 文書] **統合決裁パケット起票** (§4.1 末尾の user 項目 D1–D12 を 1 文書に)。同梱: (a) M2 必要 gross 表 (定義 A 1.255% / 定義 B 0.5% + keeper 別行) と NAV 損益分岐表 (keeper = M2 @¥416k、L1 開通 ¥300k / ¥450k、L2 ¥600k) = R4(c) 未執行分、(b) 各分岐の time-to-M2 再導出 (本メモ §3 冒頭)、(c) floor estimand 注記 (残高 vs NAV)、(d) 既定挙動 = 無回答なら 12-03 F4 強制起票、(e) 入金額の参照点は「L1 開通 ¥25k + keeper 12 ヶ月 ¥25k」を最小として提示 (額は user 専権)、(f) E1 verdict (10-15) を見てから返答する sequencing を明記 (完全性批評 §10)。**M2 定義は user 裁定まで現行 (NAV 実現) のまま**。
2. [D+0〜10 / R3、live 経路 PR-1] **storm guard 4 点** (累積 tx breaker → 冪等 → 単調性アサート → dead-band 1pip) を `modules/oanda_bridge.py` `modify_sl` / `modify_sl_sync` に + fault-injection pin 4 本 (各 guard を kill すると storm fixture が通ってしまうテスト) + storm 検知器 (open trade あたり tx 数の読み手、Discord)。KB (kalman packet §1-3 / carry_dip card §(3)) が「別 R3 修理 PR」と規定済み。
3. [D+0〜10 / R3、tools PR] **`tools/broker_ledger_reconcile.py`** (`/api/oanda/transactions` span≤100 増分ページング + キャッシュ + 429 backoff) → **carry_dip 残 4/11 を先に閉じ 11/11 の符号を確定** → daily report に「demo vs broker 差 >1p 一覧」。**broker 11/11 で deduped LIVE N≥10 ∧ EV<0 が確定した場合、REG `carry-dip-v3-revival-watch` の事前規定 R2 (LIVE 停止・shadow 継続) を autopilot 執行**し、契約復元して再開するかは D5 (user) へ。ゲート estimand の差し替え (wg G1・G2 / kalman / ps regate) は行わない (R1 / DRAFT 承認待ち)。
4. [D+7〜17 / R3、live 経路 PR-2] **`EXEC_CONTRACT[entry_type]` を log-only conformance 検知器**として導入 — 対象 = code の bypass set 12 type (vix_carry / sweep 含む、宣言なし = 「set 残存」として記録)、項目 = SL/TP mode+値・exit・trail/BE 可否・units・TIF。`_tick_entry` 送信直前と ON_FILL 事後の両方で `contract_violation(field, declared, actual)` を記録、**block しない**。counterfactual pin: #677402 (SL 9.8p vs 150p) NG / #709570 (TP +1,088p) NG / #859468 (SL 13.8p vs 21.8p) NG / tx 837792 (SL ≈155p) OK / 検知器 kill でテスト落ち。Discord に件数/日。12 セルの非適合率を実測してから fail-closed 化を D5/D7 に上げる。
5. [D+10〜20 / R3、live 経路 PR-3] **F4 推定器修正 + keeper 計装露出**: `tools/nav_floor_projection.py` の burn を「keeper 確定分 (target/units × ¥/RT 実測 ÷ 30.44 ≈ 68.3 円/日、決定論) + edge 30d 実現 PnL」に分解 or fit 窓 ≥30 暦日を必須化、counterfactual pin (09-15〜09-19 の 82→55.8 振動を再現する既知入力で落ちるテスト)。`status_volume_keeper.get_worker_status` に `history` の `pl_jpy` / `spread_pips` 分布を露出 + 月次 KB 行 (RT 数 / Σpl / spread 分布)。**ガード値 (cap 1.0p / 窓 UTC 0-5) は不変更**。
6. [今夜 09-20 21:00 UTC → 月曜 daily report / record-only] **wg G0' 第 2 イベント**: REG g0prime 手順 (1)–(5)。fill → F2 resolve + 変換係数 N=1。ABANDONED_* → 2 連続不成立成立 → **執行モダリティ R1 再起案の骨子を同週 DRAFT** (打ち切り +15 分 / drift +8.0p は R1 でしか動かせない)。qualifying 不成立 (gap 小) なら 09-27 へ繰越 (分母に入れない)。**戦略カードのイベントログに 09-13 / 09-20 を追記** (現在 09-10 で停止)。
7. [〜10-08 cutoff / 10-15 verdict / record-only] **E1 first look を §8 どおり執行** (P-10 解除は §8 手順のみ)。PASS 分岐用 D4 実装 pre-reg の pre-draft (outcome 非接触、order construction の unit test / dry-run は発注なし)。UNDERPOWERED 分岐で C3 combo を #20 に回す手順は second look (2027-01-06) verdict 後に限定。
8. [D+3〜14 / record-only、$0] **#29 S1 census (価格非接触)**: 398 文書コーパスに license-free 凍結 lexicon を as-is 推論し「連続声明ペアの |ΔStance| が雑音帯を超える割合」だけを数える。TDW/WCB は記述 secondary。結果を **C1–C6 形式の臨時スキャン (単独候補) として `wiki/research/` に記録** = REG `edge-supply-scan-monthly` 規則充足。「LLM zero-shot 採点は知識カットオフ汚染のため恒久禁止」を text モダリティ C5 規律として KB 追加。explore LOCK は別裁定 (explore 枠の現在値 0/3 か 1/3 かを catalog 運用ルールで先に確定)。
9. [PR #272 マージ後 / R3] **E23 P1 3 件を「park 根拠の estimand 監査」として消化** (Gate A explore 窓限定再計算 / Fed discovery を FOMC statement に限定 = manifest 変更 / BoJ 英語版時刻)。「park の再判定」ではない。registry `review-backlog-253-257-digest` は #272 差分にのみ存在することを前提に記録。
10. [D+0〜14 / R3] **readout 欠落修復**: `tools/m1_clean_live_monitor.py` 値の KB 日次記録、`/api/demo/stats` N=587 の `oanda_trade_id != ''` 厳格性 pin、risk dashboard attribution の gross/net 併記 + **friction 行の二重計上疑い (pnl_pips 摩擦内蔵) を明記**して estimand 確定、engine_tick liveness の現在値を KB に転記。
11. [D+0〜14 / R3 文書] **時計台帳 v0**: live 経路欠陥 (_is_xau_inst / wg 21:01 / DT hour_utc / bb_squeeze / live_fill 検知 / carry_dip bracket / ps_aud_jpy bracket) を「混入日 / 発見日 / 発見手段 / 影響セル / **失われた qualifying event 数**」で集計 (cell-days ではなく event 数、07-24〜07-28 の重複を分離)。Tier A cron に「pending 決裁の経過日数」「T_conv per live cell」を配線。**既定動作の自動執行は付けない**。
12. [D+0〜14 / R3 文書、$0] **venue 変更 feasibility (記述級)**: 国内 FX API 提供社の API 利用条件 (出来高ティア gate の有無 / 最小 lot / 主要ペア spread / 残高条件) を一次情報で並べ、keeper=0 化の可否を「検討済み・未検証」から「記述済み」に上げる。決裁は F1 (2027-02-05) 後だが、floor がその直後に来るため材料を先に持つ。
13. [10-01 以降 / record-only] **Gold 10 月判定の実証**: ステータス画面 or API で GOLD 表示を確認し KB に記録 (画面確認が user のみ可なら user 項目)。SILVER なら全 live 部分が同時停止 = Rank 1 パケットの前提が変わる。
14. [D+0〜7 / R3] **Turtle S2 D1 shadow readout** (`wiki/learning/s2-shadow-monthly-*.md` 0 本 = pre-reg 履行漏れ)。N / PF / OOS PF の確認のみ、昇格は R1。
15. [任意・$0 / R3] CME capture に ZQ=F / SR3=F — REG `r3-market-data-ingest-freshness` min_keys 更新 + E12 7 契約 capture 非摂動を同 PR で pin。
16. [10-14 / record-only] daily market review 30d 有効性レビュー (REG) — 稼働率 <50% or 発見 0 なら廃止提案どおり。
17. [10-18 / R3] 第 6 次スキャン (四半期モダリティ棚卸し同乗)。S1 census 結果を持ち込む。cadence 決裁 (D9) 前でも規則内。

**user 決裁必須 — 統合パケット 1 本 (D1–D12、Claude 起票 10-08、返答期限 11-30 の 1 本に統一、E1 verdict 10-15 後の返答を推奨)**
- **D1. M2 会計**: A = 現行 (NAV 実現、keeper 込み) を維持し必要 gross 1.255% を rederivation §4 / roadmap v2.3 KPI 表に併記 / B = edge-only に estimand 変更 (keeper は資金時計で別計上、R1)。**推奨は明示しない — 倒錯 (達成に見えて達成でない) の回避と、到達可能な経路の存在はトレードオフで user の価値判断**。
- **D2. M2 定義の内部不整合裁定**: (i) 「0.2x→1000u→5000u」文言 vs ladder L73 carve-out 非乗算 — どちらが SSOT か (前者なら L1 に再基準化コード変更が前提)。(ii) 「2 セル以上」の単位 (type / type×pair×dir) と相関セル (全 USD_JPY long) で満たせるか。
- **D3. U3**: (i) 入金 (最小参照点 = L1 開通 ¥25k + keeper 12 ヶ月 ¥25k、keeper=M2 ¥416k、L2 ¥600k) / (ii) 縮退 (keeper 停止 = 翌月 API 停止、E1 ingest は Myfxbook で継続、shadow は fallback で劣化継続) / (iii) 停止。期限 11-30 (F4 12-03 前)。
- **D4. U2**: 資本上限を 1 数字で凍結 (推奨期限 10-15、F4 前 11-30 まで)。
- **D5. carry_dip disposition** (08-05 から未決、08-07 に user 決裁事項と分類): (a) 契約復元 (SL 150p / TP 80p / trail・BE・BE_LOCK・C1 免除 / `1h_rr_low` 免除 / `_QUICK_HARVEST_EXEMPT` 登録 + storm guard 着地後) → 宣言セルの N を修正日から再起動、as-placed N=14 は「別セル (as-placed 変種)」として凍結記録 / (b) as-placed を新宣言 (Rule 1 例外の再承認、BT 根拠なし) / (c) LIVE 停止・shadow 継続。tail: (a) は 1 敗 = ¥1,500 = バッファの 11.1%。broker 11/11 の符号を添えて上程 (§4.1-3 の結果待ち)。
- **D6. ps_aud_jpy**: 08-12 決裁 (watchdog 委任) の再上程 — 現状維持 (09-30 regate に委任) / shadow 降格 / 送信保留 (bracket 診断完了まで)。診断は R3 で先行。
- **D7. kalman postfill packet (DRAFT) の承認**: broker realized net を estimand に凍結 + as-placed SL ≈13.8p vs 宣言 ≈21.8p の非適合を §6-6 に追記 + 契約表に「trail なし・SL 1.5×ATR・winner ride」を書くか trail 込みを新宣言 (Rule 1) にするか。
- **D8. 4原則 1/4 の妥当性監査** を U9 議題に (meta-audit §8 盲点 #1) — 「閉じる」前提でなく、live N=587 → promote 可能セル 0 / shadow net+ 1/39 type の payoff 定量を材料に。
- **D9. cadence**: 月次 → 四半期 + イベント駆動 (WIP 緊急トリガ維持、round5 §4)。
- **D10. U5**: Render dashboard で `fx-codex-runner` Suspend (user のみ) + 固定費台帳への月額入力 (Render Pro / MASSIVE / Claude / codex-runner、KB に無い)。
- **D11. M1_STRONG 変種 4 件** (既存 pending) — 少なくとも主定義 (EV≥+1.0 vs >0 / Wilson の読み) を期限付きで。未決なら default = 現行 primary。
- **D12. CC BY-NC (TDW/WCB)**: 研究利用は E23 pre-reg §0-4 で可 (決裁不要) — **live 転送のみ** (i) 許可 / (ii) license-free 再実装を条件 を裁定。#29 S1 の結果が出るまで急がない。
- **(単独・随時) Gold 10 月判定の画面確認** (D13 相当、§4.1-13)。

### 4.2 90 日 (〜2026-12-20) — 固定点: 11-06 ECG / 11-14 MoF #4 / 11-30 U3 期限 + carry_dip backstop / 12-03 F4 (audit_default) / 12-09 kalman R2 / 12-31 F2 / 2027-02-05 F1 / 2027-03-31 F3 + global-stop

**autopilot**
- [10-15] E1 verdict 執行。PASS → 実装 pre-reg を user 承認へ (SLA 48h)、Rank 1 パケットの U3 額と D2 (第 2 セル) を verdict で更新して再提示。UNDERPOWERED (modal) → second look 2027-01-06 へ自動、パケットは据え置き。
- [11-06] ECG #22 first look §8 執行 — PASS でも供給ではなく選別 (active 4 セルの gate R1)、M2 寄与は M3b 側で別計上。
- [11-14] MoF #4 reverdict → family B「発言層なしで設計」再裁定 (起案は S1 / E1 の結果次第)。
- [11-30] carry_dip backstop (N<10 なら低頻度=構造的の再確認のみ) / U3 期限到来 → 無回答なら 12-03 F4 で強制再上程 (既定挙動)。
- [12-09] kalman R2 (broker net、N<10 なら stale review)。BT WR 23.91% は G3 の WR≥35% に構造的不達 → L1 候補から外して会計。
- [12-31] F2 checkpoint: wg live N=0 なら「PASS→live 変換未実証」正式認定 → pre-reg テンプレに「執行契約表 + fill 成立率事前見積り + 制約 4.2 での実効 rung」を必須欄化 (F2 帰結として — 現時点では条件付き)。
- [継続] 最初に G3 (live N≥30 ∧ mean>0 ∧ WR≥35% ∧ disaster 0) に届いたセルで `tools/lot_ladder_calc.py --packet` を機械生成 — **現 NAV では制約 4.2 で HOLD が返ることを packet に明記** = U3 (i) なしでは起案権が発生しても増額不能。
- [12-20] 時計台帳 90d レビュー (lost event 数 / T_conv / 契約検査の検出件数)。F2 判定材料に「不成立が執行契約由来か流動性由来か」を添える。
- [〜2027-02-05] F1 verdict 執行 → TRIGGERED なら三択 (有償 / venue / 終了) を **§4.1-12 の feasibility 付き**で起票。
- [〜2027-03-31] F3 / global-stop 判定 — 発火は kill ではなく「段階設計再導出 / 全面棚卸し」。発火前提で M1→M2→M3 の書き直しを準備 (旧 anchor 不使用)。

**user 決裁 (90d)**
- E1 PASS 時の実装 pre-reg (D4) 承認。
- wg 2 連続不成立時の執行モダリティ R1 再起案の承認。
- ps closed-bar 化 (P-2、R1) — 09-25 帰属後に packet。
- 0.2x DD 再基準化 (D2 で前者 SSOT の場合) — U3 (i) と同時でなければ L1 は開かない。
- F1 TRIGGERED 時の三択。

---

## 5. 正直な caveat

1. **M2 は現行定義 × 現 NAV では到達不能 (∞)**。期待値が低いのではなく、L0 1000u の上限 (346p/月 = 最良 net EV の 3–6 倍) と制約 4.2 (L1 不成立) による上限の話。研究供給を増やしても執行を直しても、この 2 つが動かない限り分母は動かない。5 提案の算数批判 5 本が独立に同じ不動点に収束し、5 提案のどれもこれを解かなかった。
2. **入金 + 定義 B でも中央は 2028-H1、P(M2≤2027 末) ≈ 1–5%**。KB baseline (2027-Q4〜2028 / 15–25%) は keeper 未反映・L1 可 (NAV 326k)・fill 100% 前提で楽観。本メモは日程を短縮していない — 変わるのは「算数が閉じる経路が存在する」ことだけ。定義 A (NAV 実現) なら 3–5 セル必要で 2028-H2 以降。
3. **M2 より先に 2027-03-31 (F3 / global-stop) が来る**。両方とも発火確率が高い (M1_STRONG 0/117、base rate 4%、最速セルの N≥30 が 2027-Q1〜Q2)。発火は kill ではなく設計再導出だが、ミッションの段階設計が書き直される前提で計画すべき。
4. **keeper を続ける限り floor 到達 (2027-03〜04) が F1 (2027-02-05) の直後に来る**。API を生かして E1 second look / E12 first look を迎えるには U3 決裁 (入金 or 縮退の受容) が 11-30 までに必要。無回答 = 12-03 に F4 が強制起票、それまで毎月余裕の 15% を消費。
5. **Gold 10 月維持は未実証**。keeper の同一秒自己往復が OANDA 出来高に算入される証拠は KB に無い。10-01 判定で SILVER なら、本メモの live 部分 (Rank 2・3、D5–D7) は同時に停止し、Rank 1 パケットの前提 (keeper を払う意味) が消える。
6. **今夜 (09-20) の wg イベントで 2 連続不成立なら、M2 の第 2 セル候補が消え、全分岐が 2028+ へ後退する**。その場合は執行モダリティ R1 再審が Rank 3 から最優先に入れ替わる。
7. **M1 (clean live 符号転換) すら未達**: 直近 30d N=14–17 / gross +1.9p / friction 63.6p (33.5 倍、ただし二重計上疑い)、M1_STRONG 0/117、唯一の正 EV 候補 carry_dip は broker 基準で符号逆。**「勝てる方法」の現在の正解は「勝つ」ではなく「測定可能な状態を作り、資本の決裁を取り、2027-03-31 を設計どおり通過する」**。
8. **本メモの全 net EV / 摩擦数字は 4.5 ヶ月無較正 estimand を継承** — 再較正で悲観側に動く可能性を明記して引用すること。
9. **4原則#1/#4 との緊張**: 本メモは防御的施策 (検知器 / de-risk / 縮退案) を上位に置いている。整合根拠は「shadow 分母は保存」「LIVE 側 winning-condition 維持は原則#3 後段の設計どおり」「floor 到達 = 攻撃手段そのものの喪失」の 3 点だが、これは解釈であり、D8 (U9) で user が原則の読みを変えれば順位は動く。

---

## 6. この分析自体の限界

- **文書のみ**: 価格データ・DB 計算ゼロ。σ_5d / N_required / floor 日程 / P(M2≤2027 末) は純算数の点推定 (区間を持たない)。KB 中央シナリオの再導出も点推定の掛け算。
- **今夜 21:00 UTC の wg イベントは執筆時点で未発生** — §4.1-6 は分岐の事前固定であり結果ではない。今日の session log は空 (`KB/sessions/2026-09-20-session.md` に本文なし)、trade-log 最新は 09-19。
- **E1 verdict (10-15) が本メモの最大の未知**: modal は UNDERPOWERED だが PASS なら Rank 1 パケットの U3 額・D2 第 2 セル・Rank 5 (#29) の優先度が変わる。10-15 後にランキングを再評価すること (パケット返答をその後に置く理由)。
- **estimand 未確認のまま転記した数字**: `/api/demo/stats` N=587 の厳格性、risk dashboard n=14/15 が clean live 厳格定義か、friction 行の二重計上、carry_dip「in-regime 8–11 fill/月」(4 週単一窓)、wg fill 成立率 (改定後実績 1 event / 0 fill)、kalman as-placed SL 13.8p (exit − 9.1p からの逆算)。
- **手動玉の混入は未確認**: Track C (07-28) の 30,000u×7 は user 手動と確認済みだが、9 月の trade-log に手動言及なし・09-10 `openTradeCount` 0。継続していれば NAV 実現 M2 は帰属不能で、手動出来高が Gold に算入される (keeper 部分冗長)。P5 の「別口座」仮定は未検証。
- **固定運用費の合計は KB に無く、本メモも数字を持たない** (D10)。
- **venue 変更の可否は未調査** (§4.1-12 は「記述級で並べる」まで)。keeper=0 の venue が存在しない可能性はある。
- **Gold 出来高カウントの実証** は user の画面確認に依存する可能性 (§4.1-13)。
- **決裁レイテンシ**: 統合パケット 1 本でも user が 12 項目を一度に裁定できる保証はない。実測 B 型 18 日 (blocker-refutation §2) を前提に 11-30 期限を置いたが、D1–D4 だけ先行返答でも分母は有限化できる旨をパケットに明記する。
- **P2 / P4 の批判本文は入力で全文受領** (前版の切断は解消)。ただし両批判の「摩擦 ¥636 は消えない」判定は friction 行の二重計上疑いと同じ estimand 問題を抱えており、どちらの向きにも確定していない。

---

## 付録 A. 転記数字の出所索引 (再利用時はこのパスを併記)

| 数字 | 出所 |
|---|---|
| NAV ¥275,517 / floor ¥262,000 / 余裕 ¥13,517 / fit 55.8 円/日・242 日 | `data/monitoring/nav_floor_projection.csv` 末尾 3 行 (09-17〜09-19) |
| floor = 「口座残高 25 万」(残高基準) / Gold = 前月 $500k 新規+決済・毎営業日判定・翌月末まで / 復帰 token 再発行 + 1 ヶ月 | `KB/analyses/live-frequency-and-oanda-status-survival-2026-09-01.md` L8–L21 |
| keeper ¥2,080/月 = 26 × ¥80 = 0.755% / 全 RT 0.7–0.8p | `KB/index.md` L149, L134 / `RAW/trade-logs/2026-09-10.md` L119–121 |
| keeper 決済レグ失敗の永続化・次 cycle 回収 / emergency_kill 尊重 (09-11) | `modules/status_volume_keeper.py` L154–181, L285–292 |
| M2 定義 (+0.5% NAV 実現 30d、0.2x→1000u→5000u ラダー、2 セル) / KPI L3 = mission | `KB/analyses/monthly-target-rederivation-2026-07-10.md` L44, L48 |
| 必要 gross ¥3,458 = 1.255% = 346p@1000u / 69p@5000u / 損益分岐 ¥416k・¥832k・¥2.08M | SP `ground_capital_clock.md` §2b–2c (算数) |
| 制約 4.2 ≤2.5% NAV / carve-out は rung に 0.2x 非乗算 / G3 定義 / N_required 41 (wg placeholder) / L167 は NAV 326k 前提 | `KB/analyses/lot-ladder-template-2026-08.md` L6, L56, L65, L73, L167 / `tools/lot_ladder_calc.py` L34, L72, L137 |
| 0.2x eq_peak ラチェット +988p = 再基準化コード変更 | `KB/decisions/shortest-path-decision-memo-2026-07-10.md` §1c (定義出所のみ、旧 anchor 不使用) |
| wg 凍結 +7.90p / 実効 +4.75p / 3.28 event/月 / fill 94%・75% / 0/4 event / 09-13 ABANDONED_DRIFT +41.0p / 2 連続不成立 → R1 | `KB/strategies/weekend-gap-fade.md` L19–20, L37–38, L42, L114–118 / `RAW/trade-logs/2026-09-16.md` L241 / `KB/decisions/weekend-gap-execution-contract-r1-packet-2026-09-10.md` §5–§6 |
| wg L1 +0.46% < 0.5% (keeper 無視) / 中央 2027-Q4〜2028 / P 15–25% / M2 必要 gross 1.25% 未再導出 / §8 盲点 #1 | `KB/decisions/process-meta-audit-2026-09-07.md` L91, L106, L146–147, L203, L213–214 |
| carry_dip 11/11 SL 契約破棄 / TP 65.5p / storm 5/11 / broker 7/11 ≈ −41.1p / R3 08-05 未決 | `KB/strategies/usdjpy_carry_dip_accumulator.md` §(1)(3)(4)(5)(6) |
| carry_dip 契約復元 = user 決裁事項 | `KB/sessions/2026-08-07-session.md` L26, L35 |
| `_QUICK_HARVEST_MULT 0.85` / bypass set 12 type / `_block` は行を書かない | `modules/demo_trader.py` L10266, L10545–10570, L4977 (P2 KB 批判の実読を転記) |
| kalman as-placed SL ≈13.8p vs 宣言 ≈21.8p / BT WR 23.91% / packet DRAFT 承認待ち / R2 12-09 | `KB/strategies/kalman-d7-po-dn-flip.md` L64–70 / `KB/decisions/kalman-d7-carveout-postfill-packet-2026-09-17.md` §0, §3, §6-6 / REG `t9-kalman-d7-live-n10-ev-check` |
| ps_aud_jpy −180p / 27.3% / bracket 不一致 / 08-12 user 決裁 (demote 見送り・watchdog 委任) | `RAW/trade-logs/2026-09-18.md` L89 / `KB/strategies/price-shock-rev-aud-jpy-h1-long.md` L30–48 / MEM `project_549250_incident_mc_ruin_fix_2026_08_05.md` L16, L20 |
| REG 期日: g0prime 09-28 / ps c1 09-25 / ps regate 09-30 / E1 10-15 / scan 10-18 (0 本なら臨時 R3) / daily review 10-14 / ECG 11-06 / MoF 11-14 / carry_dip 11-30 / kalman 12-09 / F2 12-31 / F1 2027-02-05 (三択に venue 変更) / F3 `f3-m1-durable-cell` 2027-03-31 / global-stop 2027-03-31 / F4 ≤90d | `KB/decisions/prereg-trigger-registry.json` (67 entries、2026-09-20 実読) |
| U2/U3/U5 選択肢 / U3 期限 11-30 / 無回答既定 = F4 発火時再上程 | `KB/decisions/mission-capital-redecision-packet-2026-09-10.md` L5, L21, L35, L63 |
| U1=(b)、スコアリング分母 = time-to-M2 | `KB/decisions/u1-mission-redecision-2026-09-17.md` L1–L11 |
| E1 = Myfxbook (OANDA v20 book 2024-09-14 終了) | MEM `project_ws3_external_hypothesis_transition_2026_07_13.md` L28–35 / `modules/myfxbook_client.py` |
| Gold 10 月「維持見込み」のみ (画面記録なし) | `KB/analyses/supply-space-feasibility-2026-09-17.md` L11 / grep 該当ゼロ |
| E23 Gate A 71.5/95.0/81.9p / N=56 / Gate D swap 1.5p/5bd / §0-4 live 転送資格 / §6 復活経路 | `KB/decisions/e23-cb-text-explore-prereg-2026-09-10.md` L66, L215, §0-4, §6, §10–§11 |
| #29 再計算 (N_required 160 @15p / 55 会合 = 4.58/月 / +0.4–1.6pp) | P1 算数批判 §1–§2, §再計算 (入力転記) |
| P5 分岐 B 再計算 (−0.09〜−0.10%/月、必要 drift +0.59%/月) | P5 算数批判 §再計算 (入力転記) |
| base rate 4.0% [0.7–19.5%] / 外部 0/18 / 着手可能 0 本 | SP `ground_supply_pipeline.md` §0, §2, §4 |
| 摩擦 4.5 ヶ月無較正 (kb-14) / レイテンシ A 0–3 日・B 18 日 | `KB/decisions/blocker-refutation-2026-09-10.md` L64, L66 |
| pnl_pips 摩擦内蔵 (二重計上) | `KB/analyses/friction-adjusted-ev-map-2026-07-07.md` §7-2 |
| per-pair 1 position / Max open 4 | `KB/analyses/system-reference.md` L100 |
| 実弾ガバナンス G3/G6 起票のみ | `KB/decisions/live-governance-gap-audit-packet-2026-09-10.md` L36, L39, L65 |
| PR #272 OPEN / registry id 不在 | `gh pr view 272` / REG 全数照合 (2026-09-20) |
