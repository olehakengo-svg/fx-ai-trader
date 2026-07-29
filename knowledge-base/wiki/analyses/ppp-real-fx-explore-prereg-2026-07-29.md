# ppp_real_fx_gap_reversion 凍結探索プロトコル — 単独 wave (2026-07-29)

**性格**: 観測前プロトコル凍結 (explore 段階)。tier action なし、live 変更なし。台帳 #14 登録
(単独 family — wave-1 教訓「強 prior 家系は m を割らない」の適用)。
**敵対的検証**: GO-WITH-CONDITIONS (`raw/analysis/new-angle-adversarial-verification-2026-07-28.md`
候補 1) — **条件 1-5 を全て本ドキュメントで解決してから凍結** (下記 §条件解決)。
**メカニズム**: 実質為替レートの PPP 乖離は貿易実需 (価格強制的) により 4-12 週で平均回帰する。
FX で最も追試された value ファクター (Menkhoff+ 2017 / Asness+ 2013)。公表後減衰 ~50% 織込み済み。

---

## 条件解決 (敵対的検証 5 条件)

1. **explore 窓の成立** ✅ — FRED H.10 日次 FX (2008-01-02〜) + CPI 8 系列を取得済み
   (`data/external/ppp/`、README に系列 ID/再現コマンド/QA)。全 7 ペアで 5y rolling z の
   有効開始 = **2013-01-02** → explore 2014-01-01 開始に +364d 余裕
2. **スワップ会計の一本化** ✅ — **「純額スワップ込み EV、サイド選別なし」を採択**
   (キャリー整合フィルタは不採用: 金利のシグナル入力化は E20 隣接を濃くし N を削るため)。
   スワップ費用 = 政策金利差 (e20_rates_ingest 残置パネル) × h/252、ポジション方向で符号付け
   (pay/earn 対称)。感度: earn 側 25% adverse haircut。**金利はコスト会計のみに使用し、
   シグナル・フィルタには一切使わない** (E20 差分の核心)
3. **極値レグの降格** ✅ — |z|>2 イベントパネルは **記述的 secondary** (promotion 検定から除外)
4. **USD 因子の共通性** ✅ — bootstrap は **時間ブロック (6 ヶ月) × 全ペア同時リサンプル**
   (dollar factor を保存したまま帰無分布を生成)。実効独立性 ~1-2 を前提にした設計
5. **CPI vintage** ✅ — 全系列 NSA (改定ほぼゼロ、FRED ページで確認済)。シグナル利用可能日 =
   **参照期間の末日 + 45 日** (月次は月末+45d、**AU/NZ 四半期は四半期末+45d** — FRED の
   期間初日スタンプをそのまま使うと look-ahead になる罠を README §4 に記録)。実勢公表ラグ
   ≤25-30d に対し保守的

## 凍結事項

- **データ**: FX = FRED H.10 日次 (7 ペア: EUR_USD, USD_JPY, GBP_USD, AUD_USD, NZD_USD,
  USD_CAD, USD_CHF)。CPI = US CPIAUCNS / EA CP0000EZ19M086NEST / JP BIS M.JP.628 /
  GB GBRCPIALLMINMEI / AU・NZ 四半期 (OECD 系列) / CA CANCPIALLMINMEI / CH CHECPIALLMINMEI。
  リターン測定は同じ H.10 系列で行う (シグナルと測定の系列統一。OANDA/MASSIVE との突合は
  生存時の stage-2 で)
- **シグナル (単一凍結構成、grid なし)**: 実質為替 q_t = log(S_t) + log(CPI_foreign/CPI_US)。
  S = USD 建て統一 (H.10 の向きを 1 USD あたり外貨に正規化、q 上昇 = USD 実質高)。
  CPI は vintage ラグ適用後の最新利用可能値を月内 step 補間 (前方埋めのみ)。
  **z_t = (q_t − mean_5y(q)) / std_5y(q)** (rolling 1260 営業日、完全窓必須)
- **サンプリング**: 月末営業日 (シグナル確定日)。explore = シグナル日 **2014-01-31〜2021-12-31**
  (96 ヶ月 × 7 ペア = 672 obs)。**OOS = 2022-01〜2026-06、候補凍結後 1 回のみ**
- **予測方向**: 高 z (USD 実質割高) → USD 減価 = 対 USD 外貨リターン正。
  IC は Spearman(−z_usd_adjusted, fwd return)、fwd return は USD-adjusted (外貨/USD 向き)
- **ホライズン**: fwd {21, 42, 63} 営業日 close-to-close。**primary = 42bd** (機構 4-12 週の中央)、
  21/63 は supporting。重複窓は時間ブロック bootstrap で処理し、**非重複サブサンプル
  (四半期末のみ、h=63bd) を confirmatory 診断**として併記
- **primary test (単独 family、α=0.05)**: pooled Spearman IC (672 obs) の両側 p を
  6 ヶ月時間ブロック × 同時ペア bootstrap (10,000×、seed 20260729) で評価
- **必須合格条件 (すべて、凍結)**:
  (i) primary IC p < 0.05 かつ符号が回帰方向
  (ii) quintile 単調性: pooled quintile 平均が予測方向に単調 (隣接違反 ≤1 かつ Q1−Q5 スプレッド符号正)
  (iii) **キャリー中立化 (E20 隣接ガード、ハード条件)**: z を政策金利差に横断回帰した残差 z⊥ の
       IC が原 IC の 50% 以上を保持し符号不変
  (iv) headroom: シグナル上位/下位 quintile の |fwd 63bd 純移動| (スワップ純額控除後) の中央値
       ≥ 10 × per-pair RT friction
  (v) regime 分解: 効果が単一年に >50% 集中しない (COT/E20 教訓)
- **kill**: 上記いずれか不成立 → family クローズ、OOS 未接触、台帳 verdict 記録。
  再試行は「新データ (実質金利版等) + 明示差分」のみ
- **診断 (選択に使わない)**: 年次 IC 系列 / per-pair IC / |z|>2 記述パネル / 21・63bd /
  非重複 confirmatory / スワップ感度 (haircut 25%)
- **成果物**: `tools/ppp_real_fx_explore.py` / `knowledge-base/raw/bt-results/ppp-real-fx-explore-2026-07-29.json` /
  `reports/ppp-real-fx-explore-2026-07-29.md` / 台帳 verdict 追記

## 隣接差分 (必須節)

- **E20 (carry-rank/mom63 凍結)**: E20 は金利差そのものをシグナル化した日次クロスセクション。
  本 family は **CPI 価格レベルのみをシグナル**とし金利入力ゼロ (コスト会計を除く)、符号構造は
  回帰 (キャリーは順張り)。合格条件 (iii) で残差直交性を強制
- **D1 TSMOM / EMA pullback (falsified)**: 価格モメンタム系とは推定量が直交 (レベル・アンカー
  かつ回帰方向)
- **M1 寄与の位置づけ**: 月次シグナル × 4-12 週ホールドのため寄与は遅い。live 化しても
  低頻度資産クラスとしての追加 (順序判断に織込み済み)

## 事前宣言 — 期待の較正

wave-1 較正 (無料日次×週次/月次イベント系の edge < 閾値) の直撃クラスではないが、currency value
の 2011-2020 実績低迷は公知。**FAIL が十分あり得る前提**で登録し、healthy kill を許容する。
