# Query 2026-10-09 — 「TradingView で全相場が見える → 為替との連動を導いてエッジ化できるか」

**質問 (user 2026-10-09)**: 「TradingView接続できるから、あらゆる相場見れるよね？これがどう為替に連動してるかを導き出して、エッジ化することは出来る？」
**性格**: `/wiki-query` 回答 (read-only、rule:R3 記録のみ)。**joint な cross-asset × FX の forward outcome 統計は 1 本も計算していない** (P-10 / OOS burn 規律)。tier・live・registry は不変更。
**方法**: KB 横断 workflow 2 本 — pass-1 = 5 レンズ (銘柄クラス / 構成型 / horizon×摩擦 / ban 台帳 / TradingView 能力) → 統合台帳 70 行 → open 候補に反証 3 本ずつ (上限 10) → 審査 3 (quant-risk / mission / data-eng) → 完全性批評 (計 40 agent) / pass-2 = 上限で落ちた 23 候補に combined 反証 → 生存に 3 本 → 審査 (計 27 agent)。批評の指摘は本ページ作成時に一次ファイルで裏取りした (§5)。

---

## 0. 結論 (先出し)

1. **「連動の導出」は既に済んでいる。** rates↔FX の同時刻 linkage は本物 (ZN=F↔USD_JPY 1h contemporaneous IC **−0.585**、[[external-hypothesis-scan-2026-07-13]] §3B) だが、**tradeable な先行 (lag-1) は ≥1h で裁定消滅** (IC 0.0075 → 捕捉 ≈0.09 p/t vs RT 2.14p)。FX 13 ペア内の lead-lag も Lo-MacKinlay 非同期取引 artifact (naive 0.373 → 補正後 0.0041、同 §3A)。
2. **「エッジ化」の素直な 4 構成は全て pre-reg 済みで FAIL or BAN**: (a) lead-lag = E4 閉鎖 (2026-07-13) + copper-china ban「先行資産の差し替えは同型」 / (b) divergence-reversion = E3 round-3 凍結 8/8 OOS 反転 PASS=0 (2026-07-14) / (c) VIX イベント = #7 厳密 p=0.050091 で kill + 再着せ替え 5 本 BAN / (d) 月末 equity flow = #6 IC −0.052 p=0.608 + WMR NULL + SFT-1 corpse ×2。価格系 cross-asset モダリティは **内部 2 周 + 外部 1 周 + Mesfin 2026 で「枯渇」判定** ([[external-hypothesis-scan-round3-2026-08-14]] §3 棚卸しで再確認)。
3. **TradingView は律速ではない。** TV が C1 (データ入手) を変えるのは「非 FX 銘柄の intraday 履歴 ≈20k bars」だけで、そのクラス (intraday cross-asset) こそ閉鎖済み estimand。D1 の open 候補は全て public-fetch 済みで、TV は fetch 工数 (≈15 分/family) を削るが prior も C1 も変えない。TV ネイティブ explore の実績は #6/#7 FAIL (wave-1 report L64:「無料日次データ × 週次/月次イベントの edge < 認定閾値 … TV ネイティブ空間の期待値は今回で較正された」)。
4. **反証を生き残った候補は pass-1 で 2/10**: (a) round-4 EUR divergence-reversion (registry 条件付き、ZN 被覆 ≥2026-11-16 + FX 脚延伸が前提) / (b) catalog idx 19 guidance-shock-yield-proxy-fx-drift (合法だが D1–D20 = 帳簿外・正 EV ホスト不在 → research-only)。審査 3 本とも「合法だが起案価値が低い」(33–40/80)、**どちらも E1 first look (verdict 2026-10-15) と scan #6 (2026-10-18) を displace しない**。**pass-2 (23 本) は 1/23 = E12 (LOCKED 済・TV 無関係・新規でない) のみ、hygiene 2 本、残り 20 本 refuted** (§6)。
5. **副産物 (hygiene)**: 本番 `app.py` は既に DXY / ^VIX / ^TNX / 6J=F を score に掛けている (master_bias ×1.15/×0.55/×0.80、fundamental ×0.07 + daytrade boost ≤8、news ×0.04) が **ablation / IC / pre-reg ゼロ** (§5)。新しい cross-asset gate を語る前に、動いている gate の寄与を R3 で読むのが順序。

**回答の一言**: 「見える相場の数」はエッジの源泉にならない。律速は (i) 未消費の fresh OOS 窓 (暦時間でしか増えない)、(ii) 帳簿 horizon (15m–daily、live host ≤18h) での摩擦生存、(iii) daily+ の執行ホスト不在 (U2 資本決裁待ち)、(iv) explore→OOS 生存 base rate 0/18 ≈ 4% [Wilson 0.7–19.5%] — いずれも TV と無関係。

---

## 1. 連動の導出 — 実測済みの数値 (出典付き)

| 計測 | 値 | 出典 |
|---|---|---|
| ZN=F→USD_JPY 1h contemporaneous IC (probe 438 bars) | **−0.585** | [[external-hypothesis-scan-2026-07-13]] §3B |
| 同 lag-1 lead IC → 捕捉 | 0.0075 → ≈0.09 p/t (vs RT 2.14p) | 同上 |
| full window (2024-02→2026-05) contemporaneous IC | USD_JPY −0.46 / EUR_JPY −0.27 / GBP_JPY −0.28 / AUD_JPY −0.19 / EUR_USD +0.28 / GBP_USD +0.27、lag-1 全て ≈0 | [[ws3-round3-crossasset-divergence-prereg-2026-07-13]] §2a AMENDMENT |
| FX 13 ペア内 lead-lag (1h, N=20,443, 2023–26) | naive max\|IC\| 0.373 (Bonferroni-sig 50 pairs) → liquid-hours + destale で **0.0041** (own lag-1 autocorr EUR_GBP −0.41 / AUD_JPY −0.32 = bid-ask bounce) | 同 §3A、`tools/ws3_leadlag_ic_explore.py` |
| 株→JPY σ-impulse (SPX / Nikkei / NQ × σ{1.0,1.5,2.0} × fwd{1,2,4}、54 cells) | Bonferroni 有意 **0** (例: SPX σ1.0 fwd1 USD_JPY n=54 WR 64.8% だが avg −0.3p) | `tools/aeo_audit.py`、`raw/aeo_audit/aeo_audit_20260427_1311.json` (R3 監査、pre-reg なし) |

機構的含意: FX は 24h 市場で「株式が閉まっている間に情報が溜まる」窓が存在しない。cross-asset 情報は ≥1h で同時反映され、残るのは同時刻の linkage (= 乖離の基準線にしか使えない) と、それを使った divergence-reversion は round-3 で死んだ。

## 2. エッジ構成別の既往 — 台帳 70 行の要約 (FAIL 14 / BAN 12 / 条件付き 7 / 未着手 25 / 範囲外 10 / live 降格 1 / KB 未記載 1)

| 構成型 | 代表 | 状態 | 数値 | 出典 |
|---|---|---|---|---|
| lead-lag (rates / equity / commodity / cross-pair) | E4 | **BANNED** (R3 probe で閉鎖 → ban として運用) | lag-1 IC 0.0075 / 0.0041 | scan 07-13 §3、catalog `banned[]` copper-china-demand-aud「continuous standardized return of a lead asset → lagged forward FX IC は E4 と同型、asset-swap retry」 |
| 同・株 σ-impulse | AEO 監査 | BANNED (E4 に包含) | 54 cells sig 0 | `raw/aeo_audit/` |
| 同・SPX drawdown → 翌 Tokyo USD_JPY | #28 | BANNED (equity-stress JPY 再着せ替え) | — | catalog 07-24 |
| divergence-reversion (rates) | E3 round-3 | **FAIL_TESTED** | 216→47→top-8 凍結、OOS 8/8 反転 (explore EV_ft +3.0〜+6.5 → OOS −0.70〜−7.39 p/t)、leg A BH-FDR 0/8 (min p 0.140)、leg B 0/8 | [[ws3-round3-crossasset-divergence-prereg-2026-07-13]] §8、[[lesson-freeze-rule-topEV-selects-overfit-2026-07-14]] |
| 同・round-4 EUR (pair 分散 freeze) | registry | **CONDITIONAL_REENTRY** | post-hoc 非 claimable: EUR_USD W240 z2.5 H12 OOS N=33 EV_ft +3.52 IC −0.16 / EUR_JPY W240 z2.0 H12 N=77 +2.02 IC −0.23 | registry `ws3-round4-eur-divergence-conditional` (threshold 2026-11-15) |
| 同・equity (ES/SPX) 版 | research/index L101 | **反証 3/3** = E3 family の asset-swap (copper ban 同型) + OOS 消費済 + 同 horizon で rates 版が全セル負 | — | 本ページ §4 |
| 同・gold–JPY 相関ブレイク | #34 | OPEN (ADJACENT-CAUTION、「round-3 corpse の最近縁」) | — | catalog |
| cross-momentum (Iwanaga & Sakemoto 2024、Nikkei/S&P 1M → JPY bias) | edge-pipeline L75 / xs-momentum card L21 | **BANNED** (pass-2 訂正: E4 asset-swap 同型 + #6 で同変数 1d FAIL + monthly 帳簿外) | — | §6 |
| event-conditional (vol) | #7 vix_carry_unwind_continuation (TV explore) | **FAIL_TESTED** (knife-edge) | pooled short 3d +46.2p/event、厳密 p=**0.050091** > 0.05、headroom 32–55× 通過 = power 型 FAIL、同型再試行禁止 | [[wave1-tv-explore-protocol-freeze-2026-07-28]]、`reports/wave1-tv-explore-monthend-vix-2026-07-28.md` |
| 同・VIX 系再着せ替え 5 本 (regime-transition / term-structure / tail / realized-vol degross …) | #26/#27/#75 等 | **BANNED** (rejected_as_banned) | — | catalog triage |
| 同・MOVE 債券 vol ショック | #64 | CONDITIONAL (triage KILL、「現行 split では検証不能、2022+ を explore に含む split 再設計 or forward のみ」) | — | `raw/analysis/new-angle-adversarial-verification-2026-07-28.md` |
| 同・live セル | vix_carry_unwind×USD_JPY×SELL | **LIVE_DEMOTED** (R2 2026-08-03) | live N=26 −46.9p、shadow 05–07 累計 −216p | [[vix-pilot-early-demote-2026-08-03]] |
| event-conditional (equity flow) | #6 equity_monthend_conditional (TV explore) | **FAIL_TESTED** | IC(1d) −0.052 p=0.608 (N=96 月×6 ペア) | 同 wave-1 |
| 同・無条件月末 WMR fix | — | FAIL (REJECT NULL 2026-06-18) | — | [[monthend-fix-pre-reg-2026-06-18]] |
| 同・SFT-1 (2026-05-04) | quarter_end_jpy_repat / month_end_usd_rebalance_short | FAIL (REJECT / BLOCKED) — **台帳が見落としていた corpse** | PF 0.476 (N=23) / PF 0.81 (USDJPY 部分 N=156、EUR/GBP BLOCKED_DATA) | `raw/bt-results/sft1-*-2026-05-04.md` |
| 同・MSCI/FTSE / GPIF 四半期末 | — | BANNED / CONDITIONAL | — | catalog rejected_as_banned |
| rates anchor / carry | E20 (政策金利差 / Δ63bd 2y 差 × 日足バイアス) | FAIL (S2 棄却、carry IC −0.047 逆符号) | — | [[e20-rate-differential-s2-diagnostic-2026-07-24]] §4 |
| 同 | family C #26 (2y UST−JGB 帯 × USD_JPY 帯下 LONG × 21bd) | FAIL | N=41 net −24.2p、gate C p=0.527 | [[family-c-rate-anchor-explore-prereg-2026-08-19]] §11 |
| 同 | hull_donchian USD_CHF × Fed–SNB 差 regime gate | FAIL (falsified) | — | learning/hull-donchian-usdchf-ratediff-prereg-2026-06-15 |
| 同 | ppp_real_fx_gap_reversion #14 | FAIL | IC +0.113 p=0.129 | catalog L78 |
| 同・OIS/policy-path anchor (ZQ/SR3 種まき) | U4 (c) | CONDITIONAL (「$0 種まきのみ、起案は U1 後」) — 反証 2/3 (host 不在、未着手) | — | [[external-hypothesis-scan-round4-2026-09-10]] §4 |
| vol modality | E22 VRP (EVZ−RV21 × EUR_USD) | FAIL | IC −0.025 p=0.76 (完全 null) | [[e22-vrp-explore-prereg-2026-08-17]] |
| 同 | E17/E24 (17 通貨 OTC IV) / E25 (synthetic surface) | BANNED | horizon >3 ヶ月 / 価格再着せ替え | round-2 / round-3 |
| 同 | E10 RR gate / E11 ATM IV / 有償 OTC 面 probe | CONDITIONAL (U4 a-1、E1 非 PASS なら scan #6 で CME DataMine 一回性 probe を裁定) | — | [[supply-space-feasibility-2026-09-17]] §4 |
| positioning | COT #5 / #16 / S3 TFF | FAIL、E27 BANNED (「週次 COT 設計空間は実質全クローズ、母集団問わず」) | #5 BH-FDR 0/36、#16 IC +0.019 p=0.565、鏡像恒等 0.93 | catalog L66/L79 |
| 同・リテール (非 cross-asset) | E1 Myfxbook | LOCKED、verdict 2026-10-15 | — | registry `e1-prereg-verdict-deadline` |
| 実約定フロー (先物→現物) | E12 CME 1h volume | LOCKED、first look 2027-02-05 | — | [[e12-volume-forward-prereg-2026-07-29]] |
| regime filter on hosts (VIX / DXY / TNX / 6J) | macro protocol Step 1–3 / E29 | **CONDITIONAL** — round-5 E29「棄却 (C4) … 条件付けるべき正 EV ホストが母集団に存在しない … ホストが 1 本でも生まれたら再検討可」 | friction-adjusted EV map: net+ = 1/39 type・3/89 cell (shadow のみ)、唯一の net+ は live 負 | [[external-hypothesis-scan-round5-2026-09-17]] §3、[[friction-adjusted-ev-map-2026-07-07]] §1 |
| 市場の変更 (指数 CFD / crypto を直接取引) | U4 (c-1)(c-3) | OUT_OF_SCOPE (S1 研究のみ、live 化は U2 先行) | — | [[supply-space-feasibility-2026-09-17]] §2 |
| ML / graph-learning cross-asset feature stack | E6 / E28 / E31 | BANNED | — | round-4 / round-5 |

生存モダリティ (2026-08-14 四半期棚卸し) = **非価格のみ** (E1 positioning / E7 event [08-17 FAIL で枯渇] / E12 flow / #22 ECG / E22 vol [08-17 FAIL] / E21 帰属)。cross-asset「価格」はこの棚卸しの時点で閉鎖済みで、本クエリは新反証を 1 件も見つけていない。

## 3. TradingView が足すもの / 足さないもの

**接続の現状 (2026-10-09 実測)**: TradingView Desktop は起動中 (PID 88205) だが CDP 無しで `tv_health_check` は「CDP connection failed」。MCP から使うには **CDP 付きで再起動 = user 操作** (queue `20260927-0300-kalman-d7-v17-canon-tv-harness` と同じ前提、autopilot 不可)。本クエリでは user の TV を kill せず、KB と tool schema から能力を判定した。

| 項目 | 実態 | 出典 |
|---|---|---|
| MCP 転送 | `data_get_ohlcv` ≤500 bars/call (tool schema)、`batch_run` は symbol×TF 反復 — 履歴 export 経路ではない | tool schema |
| 唯一の bulk export 経路 | Pine `indicator()` + `var` 配列 + `request.security(..., "D", close)` + `table.new` → `data_get_pine_tables`、統計はローカル (`tools/wave1_tv_explore_stats.py`)。1 family × 6 pairs ≈ 15 分 | `bt-results/tv-overlays/wave1_*_export.pine`、wave-1 report「教訓」 |
| `strategy()` の制約 | pine_tables / labels / trades が `strategy()` では空を返す MCP 回帰 → export は `indicator()` 必須。Deep Backtest (2002–2026) は `strategy()` のみ | ema-trend-scalp-redesign-2026-05-14 / h4-level-edge-falsification-2026-06-22 L12 |
| プランのバー上限 | ~20,000 bars/chart (15m BT ≈ 10 ヶ月で打ち切り)。D1 は実質無制限 (wave-1 は OANDA D1 2014〜を取得)。**1h ≈3.3 年は外挿で KB 未実測** | [[mtf-regime-switch-eurusd-falsified-2026-06-25]] §2 L51 |
| 上限は楽観バイアスの温床 | mtf TREND SELL: TV 10 ヶ月 PF 1.63 vs 複数年 PF 1.07 / xs_momentum Python WR 69% vs TV 43.5% | 同 L76、memory feedback_tv_edge_discovery_loop |
| lookahead 整合 | `request.security` は `lookahead_off` 必須。SPX 16:00 ET / VIX 16:15 ET < FX D1 close 17:00 ET → 同日条件付けは先読みなし | [[tv-pine-edge-discovery-framework]] L20/L61、wave-1 freeze L17 |
| TV で届く cross-asset 銘柄 | TVC:DXY / TVC:US10Y / TVC:GB02Y / CME:ES / CME:NKD / COMEX:HG / NYMEX:CL / CBOE:VIX3M / TVC:MOVE / FRED:BAMLH0A0HYM2 / BTCUSD 等 (TVC 利回り指数の close 時刻は KB 未検証、wiki に US02Y/GB02Y 使用実績ゼロ) | tradingview レンズ `symbol_search` |
| **TV が本当に足すもの** | 非 FX 銘柄の 1h 履歴 ≈20k bars (yfinance 1h 730d rolling = ZN floor 2024-02-18 / Massive 先物 aggs ~2024-07 / 株 ~2y を超える) — **ただしそのクラス (intraday cross-asset) は E4 BAN + E3 FAIL の閉鎖済み estimand**。CBOT:ZN1! は yfinance ZN=F とロール規約が違い round-4 harness に混在不可 | 本ページ §1–§2 |
| TV が足さないもの | fresh OOS バー (暦時間でしか増えない) / OTC FX オプション面 (E22 復活経路) / CLS 決済フロー / 15m 長期履歴 (in-repo Massive 15m は 2013-10→2026-10-09 の 318,020 行 ≫ TV ≈10 ヶ月) | — |
| 評価正本ルール | Live > TV Pine Strategy Tester > Python BT。TV PASS は測定のみ、live 化は stage-2 pre-reg + user (Rule 1) | memory feedback_tv_edge_discovery_loop |
| TV ネイティブ explore 実績 | #6 FAIL / #7 FAIL (knife-edge) / level_fb_d1 FAIL / mtf_regime falsified → TV-device explore 生存 0/3〜0/4。研究スキャン 5 周に TradingView 言及 0 件 | wave-1 report L64、catalog L84 |

**判定**: 「TV に繋がるから」は C1 の一部 (fetch 工数) にしか効かない。open 候補の D1 データは全て `data_status: public-fetch` (yfinance/FRED) で、TV はコストを下げるが prior・ban・horizon・host・OOS 窓のどれも動かさない。

## 4. 反証を生き残った候補 (pass-1: 2/10) と最早合法着手点

### 4a. WS3 round-4 EUR divergence-reversion (CONDITIONAL_REENTRY) — 審査 33 / 36 / 40 (80 点満点)
- **法的地位**: ws3-round3 pre-reg §8 L116「条件付き round-4 (登録済トリガ)」 + registry `ws3-round4-eur-divergence-conditional` (active、type=data_coverage、source `data/cache/yield/ZN_F_1h.parquet`、threshold_date 2026-11-15)。FAIL 判定文書自身が結果観測前に事前固定した 1 回限りの例外。FAIL なら family 恒久クローズ。反証 3 本中 BAN レンズ / friction レンズは「反証不能」、data レンズは「family 本体は FAIL_TESTED」の分類訂正のみ。
- **データ到達 (一次実測)**: ZN 脚 = main 15,034 行 → 2026-10-06T01Z (worktree 15,103 行 → 10-09T01Z)。主経路は `.github/workflows/rate-anchor-daily.yml` (平日 21:15 UTC、`rate_anchor_ingest.py fetch --refresh-zn`)、`zn-cache-refresh.yml` (月 06:40 UTC) は backstop。evaluator は strict `>` (`tools/prereg_trigger_watch.py` L236) → **TRIGGERED は被覆 max ≥ 2026-11-16**。FX 脚 = harness が読む plain `*_1h.parquet` は 2026-05-15T13Z で終端、refresh job 不在 — pre-reg §8 は「FX + rates cache が …延伸したら」と**両脚**を要求するが registry は ZN 単脚判定 (path-to-win-reassessment L192 既指摘)。審査 #3 の実測: Massive 15m → 1h resample は vendor 1h と O/H/L/C/V bit-exact 一致 (EUR_USD 507/507、EUR_JPY 499/499、2025-03) → FX 1h 脚は R3 で構築可。残る穴 = EUR_JPY の vendor 欠落 (fresh 窓 05-16→07-15 に 21 gap / 6d04h、E1 複製 `data/cache/e1_ohlcv` は 07-28→10-04 しか補填していない)。
- **pre-reg 本文の不整合 (訂正必須)**: §2c L64 は OOS 窓を「2024-07-01〜2026-05-15」と書くが L41 (再指定) / §8 L85 / 窓消費履歴 L119 は「2025-07-01〜」。round-4 pre-reg は消費済窓を 2025-07-01〜2026-05-15 と明記して訂正する。
- **power / headroom**: post-hoc 生存セルの EV_ft +2.02〜+3.52 p/t = RT の 1〜1.75× で catalog ハード条件 headroom ≥10× に遠い。EUR_USD は §8 の N=33/10.5 ヶ月から 6 ヶ月窓 ≈19 < 30 → **N≥30 到達 ≈2027-03**、11-16 時点は EUR_JPY 単セル verdict + EUR_USD は事前宣言 UNDERPOWERED 分岐。
- **TV 必要度 0–1**: fresh バーは TV でも作れない。CBOT:ZN1! はロール規約差で harness 混入禁止。
- **最早合法着手**: pre-reg DRAFT + R3 infra (FX 15m→1h resample job / registry source を ZN+FX 両脚化 / §2c 訂正 / EUR_JPY gap 補填) = **scan #6 (2026-10-18) 裁定で上程可 (データ非接触)**。凍結 LOCK + OOS 実行 = 2026-11-16 以降。WIP 会計では受動 (条件付き) 線のまま、能動枠には数えない。

### 4b. guidance-shock-yield-proxy-fx-drift (catalog idx 19、OPEN_UNTESTED / ADJACENT-CAUTION) — 審査 32 / 39 / 32
- **実体**: 中銀決定日の自国 2y 利回り 1 日変化 (非決定日分布で z 化) top tercile → FX D1–D20。`hypothesis-catalog-2026-07-24.json` catalog[19] にのみ存在し md 台帳 #1–#28 未登録 (**md 台帳 #19 = round_number_major_level FAIL とは番号衝突、別物**)。KB で一度も走っていない。
- **BAN 非該当**: catalog `banned[]` は 2 件のみ。E7 §13 は「FOMC rate surprise・中銀声明テキスト … 本 ban の射程外 — 新 family として台帳経由でのみ」と carve-out、E20 §4 ban は「sign(政策金利差)/sign(Δ63bd 2y 差) × 日足バイアス × テクニカル entry、保有 1–10d」の同型再提案 (本件は決定日 1 日 z、水準・Δ63・cross-pair rank・テクニカル gating 不使用)。差分節に E20 / E7 / E23 §6 / family C の 4 corpse を原文引用する必要。
- **なぜ起案価値が低いか**: D1–D20 は帳簿外 (`modules/demo_trader.py` MAX_HOLD_SEC daytrade 8h / daytrade_1h ~18h、swing DISABLED)、正 EV ホスト不在 (E29 C4 同型)、daily+ は「資本が先」(mission-capital packet U4(b)、U2 未決裁)。→ **research-only (live 変換主張なし) としてのみ scan #6 で台帳登録可否を裁定**。再入条件 = daily+ 執行 pre-reg 成立 or 信頼できる net+ live セル ≥1。
- **TV 必要度 2–3**: データは in-repo / keyless (FRED DGS2 or yfinance)、TV は GB02Y 1 脚のみ。

### 4c. 反証で落ちた 8 候補 (pass-1) — 落ちた理由の型
- equity (ES/SPX) divergence 拡張 (3/3): E3 family の asset-swap = copper ban 同型 + OOS 消費済 + rates 版が同 horizon で全セル負。
- OIS/policy-path anchor (2/3): 種まき未着手 (`DEFAULT_CME_SYMBOLS` に ZQ/SR3 なし)、host 不在、family C 復活は「新 family + 新敵対的検証」が条件。
- CIP/UIP/yield-spread 残差 trio (3/3): 07-24 口頭 screening で REJECT/REJECT/HOLD、weekly+ = 帳簿外、catalog #23 の CIP 較正ポインタ (krohn-2024) は誤引用。
- ust10y impulse #29 / curve slope #30 (2/3, 3/3): 形式が copper ban の「continuous standardized impulse → lagged FX IC」と同一、1–5d は host 不在。
- cb-balance-sheet #59 (3/3): 4–12w = 帳簿外。
- ust-coupon 15th #10 (3/3): headroom 2–7× で entry gate 不通過、gotobi/fix 系隣接。
- GPIF 四半期末 (3/3): **SFT-C quarter_end_jpy_repat (2026-05-04、N=23 PF 0.476 boot p 0.907) が同一窓の無条件 corpse** = 台帳の「Never run」は誤り。

## 5. 完全性批評が拾った見落とし — 一次ファイルで裏取り済み

| 指摘 | 裏取り | 含意 |
|---|---|---|
| SFT-1 structural-flow family (2026-05-04) が台帳に無い | `raw/bt-results/sft1-quarter-end-jpy-repat-2026-05-04.md` PF 0.4756 (scenario D) / `sft1-month-end-usd-rebalance-2026-05-04.md` PF 0.8140 (BLOCKED、EUR/GBP データ欠) | 月末・四半期末リバランス系は corpse 3 本 (SFT-A / WMR 06-18 / #6 07-28) + SFT-C。catalog idx 81 / 6 (fiscal year-end repatriation) は SFT-C を引用せず再提案している |
| **本番に既に入っている未検証 cross-asset overlay** | `app.py` L534 `get_master_bias` (inst / cot / dxy_ema の多数決 → ×1.15 / ×0.55 / ×0.80)、L941 `institutional_flow_score` (6J=F force index、DX-Y.NYB force index、^VIX)、L1094 `fundamental_score` (^TNX L1109 / DXY L1136 / ^VIX L1150 → `fund_n×0.07` L1708、daytrade boost ≤8 L3168–3172)、L1991 `get_news_sentiment` (USDJPY=X / JPY=X / DX-Y.NYB の yfinance news → ×0.04)。`modules/bt_vec_harness.py` L837 は BT 窓で one-shot 静的 master_bias = BT/Live 非対称 | ablation / IC / pre-reg が一切ない gate が全 daytrade/scalp signal に乗っている。**新 gate 提案の前に R3 readout (PAIR_PROMOTED セルでの乗除の寄与) が順序** |
| jpy-cap-exit (🔒 LOCKED R1) の BOJ 利上げトリガー | [[jpy-cap-exit-prereg-2026-06-12]] L14「BOJ 利上げ実施」→ 4 戦略 live lot 0.5x (SIZE lever)、未発火 | 金利イベント → live サイズという regime_filter_on_host が台帳外で稼働予約済み |
| donchian_momentum_breakout の USD/JPY SELL 非対称 | `strategies/hourly/donchian_momentum_breakout.py` L196–201「ドル円ショートは金利差に逆行 → ADX≥25 必須 (BUY 18)」 | データ検証の無い rates テーゼのハードコード (minor) |
| ZN 延伸経路の実態 | 主 = rate-anchor-daily.yml 平日 21:15 UTC `--refresh-zn`、zn-cache-refresh.yml 月 06:40 は backstop (自己申告 L11)。evaluator strict `>` | registry の TRIGGERED は 11-16 以降、日次で到達 |
| E3 pre-reg §2c L64 の OOS 窓表記 | 2024-07-01 (L64) vs 2025-07-01 (L41 / L85 / L119) | round-4 pre-reg で明示訂正 |
| Gap-1 cross-pair confluence の「DXY」 | `tools/cross_pair_confluence.py` は 6 FX ペア合成 proxy (ICE DXY ではない) | KB 唯一の「DXY 条件付け」実測は合成 proxy 上 |
| `rapid_probe_rate_diff_breakout_template_2026_07_22` | direction_source = DUMMY ±1 (配管テスト) | corpse ではない (E20 行から漏れていた唯一の rates artifact) |
| TV 1h ≈3.3 年 | KB 実測は「15m ≈10 ヶ月 / ~20k bars」のみ、1h は外挿 | §3 に注記済み |
| catalog idx 4 / 11 / 14 (CME 14:00 CT settlement / NY cut pin / CB 決定後 60 分符号) | 全て OPEN、headroom 3–6× (<10×) or E15 FOLLOW 形と同一条件付け | pass-2 で未検証、起案価値は低い |

## 6. 第 2 パス — 上限で落ちた 23 候補の combined 反証

**結果**: 23 本中 **反証されなかったのは 1 本 (E12 CME 先物実約定 volume flow)** — ただし 2026-07-29 に 🔒 LOCKED 済みの forward pre-reg (台帳 #10) で、新規でも TV 線でもない (審査 46/80、TV 必要度 0)。**hygiene 2 本** (macro regime conditioning / 本番 master_bias overlay) は「エッジ候補ではなく、動いている gate の R3 監査項目」。残り 20 本は 3 軸 (ban 隣接 / データ・TV / horizon・摩擦・host) で refuted。pass-1 と合算すると **open 33 本のうち「今」合法に起案できるものは 0**、生存 3 本 (round-4 条件付き / idx 19 research-only / E12 LOCKED) は全て TV を必要としない。

⚠️ **E12 と TradingView の相性**: E12 pre-reg §7 は volume × price の joint look を全主体に禁止している。TV 接続後に **6E/6J 等の CME 出来高を FX チャートと並べて眺める行為そのものが LOCK 違反 (汚染ハザード)** — TV が「使える」ようになっても E12 関連銘柄は 2027-02-05 の first look まで開かない。

**pass-1 台帳からの status 訂正 (pass-2 の反証根拠付き)**:

| 候補 | pass-1 | pass-2 訂正 | 決め手 |
|---|---|---|---|
| Stock→FX cross-momentum (Iwanaga & Sakemoto; Nikkei/S&P 1M → JPY bias) | OPEN | **BANNED** | 「先行資産の連続リターン → 遅行 FX」= E4 閉鎖 + copper ban の asset-swap 同型。同じ SPX 1M 変数は #6 で 1d FAIL (IC −0.052 p=0.608、3d/5d は事後選択で非 claimable)。monthly は帳簿外 (U4(b)「資本が先」、round-4 §4(d)「起案しない」)。host xs_momentum は 20×15m bar momentum で Nikkei コード無し、3 ペア PAIR_DEMOTED (08-05/08-10)。edge-pipeline L75/L128 の「データ取得方法調査」行は閉鎖行へ更新すべき |
| japan-sq-day-morning-flow (#9) | OPEN | CONDITIONAL | catalog 自身の hard gate (MFE p50 ≥ 10× RT) に対し headroom 6–9×。gotobi/fix 系・session_time_bias 隣接 |
| boj-shock #18 / us-surprise #24 | OPEN | CONDITIONAL | E7/E15 再入条件 (新 family + 凍結窓非接触 + 敵対的検証) 未達、D1–D20 host 不在 |
| E10 RR gate / E11 ATM IV / 有償 OTC 面 | CONDITIONAL | CONDITIONAL | 残るのは data-procurement R1 (scan #6、E1 非 PASS 時) のみ、エッジ候補ではない |
| usd-stress-beta-timing (#57) / credit-spread-impulse (#36) | OPEN (catalog ban=CLEAR) | CONDITIONAL | catalog の ban=CLEAR は 07-24 時点、4 日後の #7 kill (07-28) で stale。VIX 系イベント集合の重複表 + 2022 前後符号 guard が再入条件 |
| MOVE #64 | CONDITIONAL | CONDITIONAL | 再入条件 (2022+ を explore に含む split 再設計 or forward) は E1/scan #6 前に充足不能 |
| em-proxy #58 / OPEC #25 / ToT #33・#60 / cesi #13 | OPEN | **OUT_OF_SCOPE** | 1–2w / D1–D10 / 2–8w / D5–D20 = 帳簿外 (live host ≤18h、swing DISABLED)。TV は寄与なし |
| oil-shock-event-cad (#32) | OPEN | OPEN (refuted) | copper ban が明示的に許す角度 (tail-event + lag>0 KILL) で未実行だが、3–10d の host 不在 + swap 純額条項。合法だが起案価値なし |
| gold-jpy-cobreak (#34) | OPEN | CONDITIONAL | round-3 corpse の最近縁、round-4 条件付き pending 中の double-dip 禁止 |
| user 原油テーゼ ① | OPEN | OUT_OF_SCOPE | 帳簿に乗る機械形 (連続 lead-lag / 乖離 / イベント) が全て閉鎖モダリティに着地。E21 帰属で user 実績 = β (swap 28% + drift 72%、α p=0.32) |
| usdjpy_carry_dip_accumulator | OPEN | OUT_OF_SCOPE | cross-asset 入力ゼロ (`evaluate()` は Close / RSI(14) / 静的 ceiling 159.50 / blackout 窓のみ) — carry は docstring のテーゼ |
| imm-roll-week-cot-pressure | OPEN | **BANNED** | signal = COT leveraged-funds net z = 閉鎖済み週次 COT モダリティ (#5/#16/E27、母集団問わず) |
| E1 Myfxbook | OPEN | OUT_OF_SCOPE | 同一ペア自身のリテール建玉 = cross-asset でない。verdict 10-15 まで P-10 |
| oanda_labs 派生 (#79/#82/#84) | OPEN | CONDITIONAL | E1 と同一機構で parked、E1 verdict 後のみ |
| E12 CME volume flow | OPEN | OPEN (LOCKED) | 上記。first look 2027-02-05、鮮度レビュー 2026-11-30 |
| E30 CLS | CONDITIONAL | CONDITIONAL | 有償・価格未取得。U4 (a-2) |
| BTC/crypto impulse | NEVER_MENTIONED | **BANNED** | 連続形 = E4 asset-swap、risk-off gauge 形 = equity-stress JPY 再着せ替え ban。2014–2021 explore 窓は BTC 非定常 |
| macro regime conditioning (VIX/DXY/TNX/6J filters) | CONDITIONAL | **HYGIENE** | E29 C4 (正 EV ホスト不在) が拘束。監査項目: layer1_dir の {bull/bear/neutral/missing} 分布、fund_total が ±0.15/±0.25 を超える頻度、fetch 失敗率 (`[INST/*]`/`[FUND/*]` 例外) |
| 本番 master_bias / fundamental / news overlay | OPEN | **HYGIENE** | §5。監査項目: Render ログ 30d の例外行 vs 成功 tick、demo_trades の layer1_dir 分布 (≥95% neutral なら 3 分岐は死んでいて overlay は定数 ×0.80 damp)、production `fetch_ohlcv` の Volume 非ゼロ率 (force index の分母) |


## 7. クオンツ判断と次アクション

**回答**: 「連動の導出」は済 (§1)。「エッジ化」は、本プロジェクトの摩擦 (2–4.5p RT)・帳簿 (15m–daily、live host ≤18h)・OOS 規律の下で、素直な 4 構成 + 周辺 10 系統が全て pre-reg 済み FAIL or BAN (§2)。TradingView は fetch 工数しか変えず (§3)、生存候補 2 本は「合法だが起案価値が低い」(§4)。**できる/できないで言えば「価格系クロスアセットは既に試して出来なかった、TV はそれを覆さない」が KB の答え**。

**今やらないこと**: 10-15 (E1 verdict) までは cross-asset 系を一切起案しない。E1 は唯一の主力供給ライン、能動 explore 枠の現在値確定は scan #6 (10-18)。

**scan #6 (2026-10-18、四半期モダリティ棚卸し同乗) に載せる 3 件**:
1. **round-4 EUR divergence の pre-reg DRAFT + R3 infra** (§4a): FX 15m→1h resample job / registry `ws3-round4-eur-divergence-conditional` の両脚化 (ZN + FX、strict `>` 明記) / §2c L64 訂正 / EUR_JPY fresh 窓 gap 補填 / EUR_USD UNDERPOWERED 分岐の事前固定。データ非接触。
2. **catalog idx 19 の research-only 登録可否** (§4b): U2 (資本) 決裁と連動、live 変換主張なしで台帳登録するか parked のままか。
3. **本番 cross-asset overlay の R3 ablation readout** (§5): master_bias / fundamental / news の各乗除が PAIR_PROMOTED セルの shadow/live EV に与えた寄与を読む (観測のみ、変更は Rule 1)。新 cross-asset gate の議論はこの readout が前提。

**KB 更新 (本 PR)**: research/index.md L101「E3 rates PASS≥1 なら equity へ拡張」= 条件永久不成立を明記して本ページへ差し替え / External-Hypothesis Transition 節に本クエリを追記。registry・pre-reg 本文・catalog は本 PR で触らない (scan #6 の裁定材料)。

**TradingView の再接続**: CDP 付き再起動は user 操作。接続しても本件で TV が必要になるのは #19 の GB02Y 脚程度で、round-4 には不要。 **接続後も CME FX 先物 (6E/6J…) の出来高を FX と並べて見ない** — E12 LOCK §7 の joint look 禁止 (§6)。queue `20260927-0300` (kalman v17 canon 再走) の方が TV を待っている本命。

## 8. 参照
- [[external-hypothesis-scan-2026-07-13]] / [[external-hypothesis-scan-round2-2026-07-18]] / [[external-hypothesis-scan-round3-2026-08-14]] / [[external-hypothesis-scan-round4-2026-09-10]] / [[external-hypothesis-scan-round5-2026-09-17]]
- [[ws3-round3-crossasset-divergence-prereg-2026-07-13]] / [[lesson-freeze-rule-topEV-selects-overfit-2026-07-14]] / `knowledge-base/wiki/decisions/prereg-trigger-registry.json`
- [[hypothesis-catalog-2026-07-24]] + `knowledge-base/raw/analysis/hypothesis-catalog-2026-07-24.json` / `raw/analysis/new-angle-adversarial-verification-2026-07-28.md`
- [[wave1-tv-explore-protocol-freeze-2026-07-28]] / `reports/wave1-tv-explore-monthend-vix-2026-07-28.md` / [[tv-pine-edge-discovery-framework]] / [[mtf-regime-switch-eurusd-falsified-2026-06-25]]
- [[macro-data-analysis-protocol]] / [[friction-adjusted-ev-map-2026-07-07]] / [[supply-space-feasibility-2026-09-17]] / [[path-to-win-reassessment-2026-09-22]]
- `raw/bt-results/sft1-*-2026-05-04.md` / `raw/aeo_audit/aeo_audit_20260427_1311.json` / `tools/ws3_leadlag_ic_explore.py` / `tools/ws3_crossasset_divergence_explore.py` / `app.py` (L534 / L941 / L1094 / L1991)
- workflow 成果物 (session scratchpad、git 外): pass-1 `wf_2f258f76-6c5` (40 agent) / pass-2 `wf_d55c6e53-2f4`
