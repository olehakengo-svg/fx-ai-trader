# gotobi_tokyo_fix_usdjpy 凍結探索プロトコル — 較正プライマリ + 単一昇格テール cell (2026-07-28)

**性格**: 観測前プロトコル凍結 (explore 段階)。tier action なし、live 変更なし。台帳 #13 登録。
**敵対的検証**: GO-WITH-CONDITIONS 通過 (`knowledge-base/raw/analysis/new-angle-adversarial-verification-2026-07-28.md`) —
全条件を本ドキュメントに反映済み。
**フレーミング**: 主目的は **測定ハーネスの較正** — 既知の公表実在効果 (Ito-Yamada 2017 gotobi 仲値アノマリー)
を我々の測定器が gross で回収できるかのポジティブコントロール。postmortem §4f (BE/Trail 水増しを
3 ヶ月検出できなかった測定器故障史) への直接の解毒剤。較正レグは昇格 look を消費しない (m=0)。
昇格適格は単一テール cell のみ (m=1)。

---

## 凍結事項

### データ・窓
- **測定器**: main checkout `data/cache/massive/USD_JPY_5m_2014_2026.parquet` (903,828 行、フル被覆) +
  `USD_JPY_1d_2014_2026.parquet`。JP 営業日判定 = `data/calendar/structural_events.parquet`
  (jp_business_day、2014-01-01〜2026-04-30 実在確認済み)。worktree の部分 parquet は使用禁止 (罠確認済み)
- **explore = 2014-01-01〜2021-12-31 / OOS = 2022-01-01〜2026-04-30** (wave 標準 split に統一、
  OOS 上限はカレンダー parquet 被覆に合わせる)。OOS は候補凍結後 1 回のみ
- 土曜バー除外・feed 不良プリントは price_shock 監査の除外規則を流用

### gotobi 定義 (in-repo 3 文書矛盾の一本化)
- **gotobi カレンダー日 = {5, 10, 15, 20, 25, 30}** (2 月は 30 → 月末カレンダー日)。文献準拠
- **繰り越し規約 primary = Convention A: 翌 JP 営業日** (手形法翌営業日慣行 + catalog #0 "rolled forward")。
  **Convention B (前営業日) は較正診断のみ** — 選択には使わない。両規約の較正結果を並記し、
  規約誤りの検出自体を較正価値とする

### 測定レグ (全て exit-free)
| レグ | 定義 | 役割 | 検定 |
|---|---|---|---|
| **C1 較正** | gotobi 営業日の 00:00 UTC open → 00:55 UTC close (5m、fix 直前まで) vs 非 gotobi JP 営業日の同窓 diff-in-means | 公表効果 (+2〜6p、gotobi 日 USD 買い) の gross 回収チェック | month-block permutation 10,000×、m=0 |
| **C2 較正** | 同日 00:55 → 06:00 UTC の diff-in-means | 公表の fix 後反転の回収 | 同上、m=0 |
| **P1 昇格テール cell (唯一)** | **月末最終 JP 営業日** (最重量 gotobi、規約非依存で一意) の 00:00 → 21:00 UTC D1 リターン vs 非 gotobi 営業日 | 昇格適格の単一検定 | 片側 (+)、month-block permutation、**m=1、α=0.05** |

### kill rule (凍結)
- **C1 が公表効果を回収できない** (点推定が負 or p≥0.05): 昇格なし + **測定ハーネス調査を起票**
  (それ自体が較正の成果)
- **P1: D1 drift < 13.0p または p ≥ 0.05 → family クローズ、OOS 接触なし**。
  13p = 実測フロア RT 1.30p × 10 (寛大側)。理論 RT 基準なら 21.4p — 両方報告し、binding は 13p を
  事前採用 (根拠: USD_JPY は floor 実測の主対象ペア)。**誓約: sub-13p の結果を事後に「有望」と
  再解釈しない。C1 較正成功 + P1 死亡でも新 cell を生やさない**
- wave-1 制約の明記: 無条件月末 D1 ドリフト ≈ 0 は 07-28 に実測済み (pooled USD-adjusted −1.1p) —
  **P1 死亡が既定路線**であることを了解の上で登録 (estimand は東京 fix・USD_JPY 単独・JP 営業日
  基準で異なるが、期待値は低い)

### 統計・診断 (凍結)
- 検定: 2 標本 permutation (gotobi ラベルを月内シャッフル) 10,000×、seed 20260728
- 必須診断 (選択に使わない): 曜日組成の感度 (weekday-matched 再計算)、rolling 2y 減衰カーブ
  (2017 公表後の減衰検査)、Convention A/B 並記、年次符号分布
- 検定力: C1 は explore gotobi ≈550-580 日 vs 非 gotobi ≈1400 日、効果 2-6p に対し SE≈0.6p で十分。
  P1 は N≈96、SE≈6p — 13p 閾値に対し検出可能

### 隣接差分 (必須節)
- **session/hour バケット 12y REJECT との差分**: あちらは全日プールの再帰的時計バケット。本件は
  **同一時計窓での gotobi vs 非 gotobi 営業日の diff-in-means** — hour-bucket 効果は両群に共通で
  差分により相殺され、残るのは日付条件付きフローのみ (直交コントラスト、敵対的検証で定量成立を確認済み)
- **月末 WMR REJECT / wave-1 月末条件付き FAIL との差分**: 別 fix (東京 9:55 vs ロンドン 16:00)、
  別カウンターパーティ (輸入企業決済 vs 指数リバランス)、無条件 diff-in-means (株 MTD 条件なし)
- **in-shadow tokyo_nakane_momentum (推定 r>0.7) / gotobi_fix SENTINEL カード**: 本 family で台帳統合。
  昇格が発生する場合は同一 family として扱い二重計上しない

### 台帳
m=13 として登録。単独 family (較正プライマリのため promotion m はテール cell の 1 のみ)。
アクティブ枠 1/3 消費。

## 成果物 (予定)
`tools/gotobi_calibration_explore.py` / `knowledge-base/raw/bt-results/gotobi-calibration-explore-2026-07-28.json` /
`reports/gotobi-calibration-explore-2026-07-28.md` / 台帳 verdict 追記
