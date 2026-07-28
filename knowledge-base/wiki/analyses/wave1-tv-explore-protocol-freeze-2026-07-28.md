# wave-1 TV 凍結探索プロトコル — equity_monthend_conditional + vix_carry_unwind_continuation (2026-07-28)

**性格**: 観測前プロトコル凍結 (explore 段階)。tier action なし、live 変更なし。
**位置づけ**: [[hypothesis-catalog-2026-07-24]] 台帳 #6 / #7 の fetch queue 消化。TV ネイティブデータ
(TVC:SPX / TVC:VIX) で fetch 工程を省略できるため、user 指示「TV で先に消化してよい」に基づき TV explore で執行。
**アクティブ枠**: wave-0 3 本は全て verdict 完了、MoF は LOCKED 受動 → 本 2 本でアクティブ 2/3。
**規律の出典**: [[edge-dev-postmortem-2026-07-24]] §6 処方箋 + hypothesis-catalog 凍結プロトコル。

> **注記 (skill 整合)**: `/wiki-edge-eval` の Stage ゲート (SL/TP 定義・BEV_WR・15m TF) は旧 Edge Pipeline
> のもので exit-free explore とは競合する。本 explore は台帳凍結プロトコル (2026-07-24, user 承認「探索最大化」)
> に従い、旧ゲートは stage-2 (執行設計) 昇格時に適用する。

---

## 共通凍結事項

- **データ**: TradingView OANDA feed、D1。条件系列は `request.security` 同一 TF (D1→D1、date 整列)。
  lookahead 整合: SPX close 16:00 ET / VIX close 16:15 ET < FX D1 close 17:00 ET → 同日 close 利用は先読みなし
- **explore 窓**: イベント日 (シグナル確定日) が **2014-01-01〜2021-12-31**。OOS 2022+ は Pine から
  エクスポートすらしない (候補凍結後に 1 回だけ接触)
- **測定**: exit 機構フリー。forward close-to-close リターン h ∈ {1d, 3d, 5d} (FX 営業日ベース) +
  5d 窓内 MFE/MAE (予測方向符号)。土曜バー (feed artifact、price_shock 監査の教訓) は除外
- **統計**: per-event rows を TV から回収し、統計計算はローカル (TV=測定カノン、統計=post-processing)。
  **primary test は各ファミリ 1 本** (下記)、BH-FDR q=0.10 を primary 2 本横断で適用。
  他ホライズン・per-pair は supporting (選択に使わない)
- **headroom gate**: 予測方向 MFE p50 (5d) ≥ 10 × per-pair RT friction。per-pair RT 摩擦 (凍結):
  USD_JPY 2.14p / EUR_USD 2.00p / GBP_USD 4.53p / EUR_JPY 2.50p / AUD_JPY 3.00p / NZD_JPY 3.50p /
  CAD_JPY 3.50p / GBP_JPY 4.50p / AUD_USD 2.50p / NZD_USD 3.00p / USD_CAD 2.80p (未実測ペアは保守設定)。
  感度: 実測フロア 1.30p でも報告
- **パラメータ探索なし**: 単一凍結構成のみ。knife-edge 摂動 (±20%) は生存時の診断であり選択ではない
- **生存時の次段**: 候補凍結 → OOS pre-reg DRAFT → 敵対的レビュー → LOCK → OOS verdict (weekend_gap
  様式 [[weekend-gap-oos-prereg-2026-07-24]] 踏襲)。全滅なら healthy kill を台帳へ
- **成果物**: Pine ソース `bt-results/tv-overlays/wave1_*.pine`、per-event rows
  `knowledge-base/raw/bt-results/wave1-tv-explore-*-2026-07-28.json`、report `reports/*-2026-07-28.md`

## H1: equity_monthend_conditional (台帳 #6)

- **メカニズム**: 年金・ファンドの月末リバランス + FX ヘッジ再調整。株式の月中騰落幅に**比例**する
  月末 USD フロー (Melvin-Prins 型)。条件付きであることが本質
- **隣接差分 (必須節)**: 棄却済み無条件 month-end WMR fix (2026-06-18 REJECT NULL) は「全月末に同方向
  ドリフト」を検定した。本仮説の estimand は「**月次クロスセクション変動**: SPX MTD リターンと月末 FX
  リターンの順位相関」。無条件形はドリフト平均、本形は条件変数の IC — 推定量が直交。
  **kill rule (凍結)**: pooled IC(1d) が有意でない、または conditional tercile spread が unconditional
  |mean| を明確に (≥2×) 上回らなければ即 kill
- **universe**: EUR_USD, GBP_USD, USD_JPY, AUD_USD, NZD_USD, USD_CAD (OANDA)
- **条件変数**: MTD = SPX_close(D−1) / SPX_close(前月最終 FX 営業日) − 1。D = 月の最終 FX 営業日、
  D−1 = その前営業日。シグナル確定 = D−1 の FX close
- **エントリー proxy**: D−1 close。方向マップ: SPX MTD > 0 → USD 売り (EUR_USD 等 USD-quote は LONG、
  USD_JPY/USD_CAD は SHORT)。MTD < 0 は逆
- **USD-adjusted return**: USD-quote ペアは raw、USD-base ペアは −raw (「対 USD 外貨リターン」に正規化)
- **primary test (凍結)**: 月ごとに 6 ペアの USD-adjusted 1d forward return を平均 (月次クラスタ化、
  N=96) → Spearman IC vs MTD。p は permutation (10,000×)。**片側ではなく両側** (フローの符号理論は
  buy/sell 対称)
- **supporting**: per-pair IC、h=3d/5d IC (反転/持続診断)、|MTD| tercile 単調性 (COT の教訓)、
  top-tercile signed net move vs friction
- **N**: 96 ヶ月 × 6 ペア

## H2: vix_carry_unwind_continuation (台帳 #7)

- **メカニズム**: VIX スパイク → キャリー強制解消はマージンコール/リスク限度の逐次発動で**複数日に
  波及** (Brunnermeier carry crash)。onset 翌日以降の JPY 買い continuation を検定
- **隣接差分 (必須節)**: E20 凍結 (2026-07-24) は carry-rank / mom63 の**日次クロスセクション IC
  (無条件・レベル/ランク推定量)**。本仮説は **稀イベント条件付き時系列 continuation**: (a) 条件 = VIX
  ショックで carry シグナル自体を使わない、(b) universe は JPY クロス固定でランク選択なし、(c) 推定量 =
  イベント後 forward 平均。E20 の凍結範囲 (rank/mom63 変種) と重ならない
- **universe**: AUD_JPY, NZD_JPY, GBP_JPY, EUR_JPY, CAD_JPY, USD_JPY (OANDA)。CHF_JPY は funder×funder で除外
- **イベント (凍結)**: TVC:VIX daily close が 25 を上抜けクロス (prev ≤ 25 かつ close > 25)。
  de-cluster: 直前イベントから 10 FX 営業日未満は不採用。onset 日 = クロスを観測した FX 営業日
- **エントリー proxy**: onset 日 FX close で JPY クロス SHORT (continuation = JPY 高継続)
- **primary test (凍結)**: イベントごとに 6 ペアの signed 3d net move (short 方向、pips) を平均
  (イベントクラスタ化) → 片側 sign-permutation (10,000×) で mean > 0
- **supporting**: h=1d/5d、per-pair、MFE/MAE p50 headroom、threshold {20, 30} + de-cluster {5, 20}d
  の knife-edge 摂動 (生存時のみ)
- **N 見込み**: explore 窓で 15〜25 イベント (低頻度・イベントアンカー — postmortem 成功パターン 3 適合)

## 多重検定台帳への影響

両ファミリは m=12 に登録済み (#6/#7)。本 explore は各 1 構成の凍結測定でありパラメータ grid を舐めない
→ m 増加なし。生存して OOS pre-reg する場合に OOS 側の分母を消費する。

## 事前宣言 — 失敗条件 (healthy kill)

- H1: primary IC p ≥ 0.05 / tercile 非単調 / conditional が unconditional を上回らない / headroom < 10×
- H2: primary p ≥ 0.05 (BH 後) / headroom < 10× / 効果が 2020-03 単一イベントに >50% 集中 (COT の
  SNB 教訓: 単一イベント支配は incoherent 扱い)
- いずれも FAIL は台帳に verdict 追記して終了。無理に候補を作らない
