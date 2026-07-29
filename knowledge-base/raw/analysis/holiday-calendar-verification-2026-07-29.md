# holiday_liquidity_state_family — 観測前カレンダー検証 (2026-07-29)

**検証者**: 独立 analyst subagent (読み取り専用、結果統計ゼロ — バー存在/出来高/レンジの流動性状態
記述統計のみ)。**verdict: parquet の祝日定義は「連邦祝日としては正確、市場休場としては不適格」 —
凍結前修正が必須 (修正はハードコード日付リストで可能、ハーネス再設計不要)。**

## 定義バグ (build_structural_events.py が USFederalHolidayCalendar 使用のため)

| 項目 | parquet | 実態 | 判定 |
|---|---|---|---|
| **Good Friday** | 全 13 年 us_business_day=True | NYSE/CME 休場、FX 出来高中央値 **43%** = 全カテゴリ最薄 | **欠落 (最重大)** |
| Columbus Day | 休場扱い | 株式開場 (債券のみ)、出来高 70% | 過剰包含 |
| Veterans Day | 休場扱い | 株式開場、出来高 **106%** ≒ 通常日 | **過剰包含 (最不適)** |
| Juneteenth | 2021-06-18〜付与 | NYSE 初観測は 2022 (2021 は開場) | holdout 窓で要修正 |
| 2021-12-31 振替 | 休場扱い | NYSE 開場 (土曜祝日の金曜振替は市場非観測) | holdout 窓で要修正 |
| 半日場 (感謝祭翌日/12月24日) | 表現なし | 出来高 71% / **40%** | covariate として別列挙 |
| JP 年末年始 (12/31, 1/2, 1/3) | 営業日扱い | 銀行休業 | JP 側ギャップ |

## FX 実態 (USD_JPY 1d、記述統計)

- US 休場日にも FX バーは存在 (24/5)。市場修正版 63 イベント中 52 でバーあり (欠落 11 は
  Christmas/NewYear = FX 自体閉場で正しい)
- 薄場は実在: baseline range 72.1p に対し Good Friday 39.1p / July 4 27.9p / Memorial 30.3p —
  **最深部 (Good Friday) を取り逃がし最浅部 (Veterans) を誤含有していた**

## イベント件数 (explore 2014-2020)

- レグ (a) 祝日前営業日: US market 修正版 **63** (federal 版 70 は 14 件汚染) / JP **84** / US∩JP 重複 8 (年末 — 両側除外を推奨)
- レグ (c) US 休場日→翌営業日: **N=52** (H 当日 FX バー存在条件、主系列) / gap 型なら 63 — **anchor は凍結時に片方のみ指定** (researcher DoF の封鎖)
- 両レグとも N≥30 を explore 窓単独でクリア (wave-1 型の power 死リスク低)

## ⚠️ 横断発見: MASSIVE キャッシュに欠損 2 区間 (全 explore 共通のインフラ課題)

**2019-09-14〜10-05 (23 日) + 2020-10-13〜11-14 (34 日)** — 1d と 5m の両方で実測 0 行 (07-29 確認)。
- **gotobi への遡及影響: verdict 不変** — 欠損は explore 8 年の ~2% で gotobi/非 gotobi 両群を等しく欠く
  (diff-in-means 不偏)。C1 +1.92p p=0.0032 (N=557) / P1 kill とも頑健
- wave-1 (月末/VIX) は TV データ測定のため非影響
- holiday family は凍結前 → 再取得 (chip task_146ae96b) または該当 6 イベントの ex-ante 除外列挙が凍結前提

## 凍結ドキュメントに採用する定義 (agent 提案、採択予定)

US 市場休場日 = NYSE フル休場のハードコード列挙 (New Year 観測日 / MLK / Washington / **Good Friday
(easter−2 日: 2014-04-18, 2015-04-03, 2016-03-25, 2017-04-14, 2018-03-30, 2019-04-19, 2020-04-10,
2021-04-02, 2022-04-15, 2023-04-07, 2024-03-29, 2025-04-18, 2026-04-03)** / Memorial / Juneteenth
2022+ / Independence 観測日 / Labor / Thanksgiving / Christmas 観測日。**Columbus・Veterans 除外、
土曜祝日の金曜振替は非観測**)。JP = jpholiday 国民の祝日 (年末年始 12/31・1/2・1/3 は含めない)。
半日場 (感謝祭翌日・12/24 平日・12/26) は休場に含めず flag 列のみ。

## 教訓

外部仮説系 explore は「シグナル定義の凍結」の前に**「カレンダー/データ定義の凍結」を独立ステップ**として
要求する (E20 の estimand ズレ・gotobi の規約差と同型の測定定義リスク — 今回は凍結前に捕捉できた)。
