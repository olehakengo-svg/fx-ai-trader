# holiday_liquidity_state_family 縮約版 凍結探索プロトコル — 背景 explore (2026-07-29)

**性格**: 観測前プロトコル凍結 (explore 段階 + PASS 時 OOS 単一接触ルール込み)。tier action なし、
live 変更なし。台帳 **#15** 登録 (**背景線 — BH 分母は本 family 内 m=2 のみ**、他 family と共有しない。
wave-2 敵対的検証の指定どおり)。
**敵対的検証**: GO-WITH-CONDITIONS (2 レグ縮約 + 背景線格下げ) —
`raw/analysis/new-angle-adversarial-verification-2026-07-28.md`。レグ (b) JP クラスタ / (d) |z|>2
オーバーシュートは power 死の実測反証で**削除済み** (再追加は新データ + 別 pre-reg のみ)。
**前提条件の解決**:
1. カレンダー定義 ✅ — [[holiday-calendar-verification-2026-07-29]] **§5 の凍結定義文案をそのまま採択**
   (観測フリー検証済み: Good Friday 追加 / Columbus・Veterans 除外 / JP 年末年始除外)
2. MASSIVE 欠損 2 窓 ✅ — 2019-09-14〜10-05 / 2020-10-13〜11-14 は OANDA backfill 済みを実測確認
   (全 8 ペア 1d で gap1=18 行 / gap2=28 行)。該当イベントは包含、**除外感度を診断で併記**
3. structural_events.parquet ✅ — jp_holiday は explore 窓 (〜2020) を完全カバー (parquet は 2026-04-30 まで)

**メカニズム** (payload 凍結文): 市場クローズ状態の流動性真空 — (a) 祝日前営業日のブックフラット化強制
(リスク枠強制)、(c) 米休場日の薄場ムーブは情報含有が低く翌営業日に反転。
**prior = low** (株式 pre-holiday drift は長期文献、FX は薄い)。KB 87 本中唯一の「祝日フラグ未検証」
estimand 空間 (カタログ #43/#52 系譜)。

---

## 凍結事項 — カレンダー定義 (観測フリー再現済み)

- **US 市場休場** = NYSE フル休場のハードコード列挙 (tool 内に explore/OOS 両リスト実体を凍結)。
  explore 2014-2020 = **63 日** (9×7: New Year 観測日 / MLK / Washington / Good Friday / Memorial /
  Independence 観測日 (2015・2020 は 07-03 金曜観測) / Labor / Thanksgiving / Christmas 観測日)。
  **服喪等の特別休場は列挙外 = 不使用** (2018-12-05 Bush、2025-01-09 Carter — ex-ante 明記)。
  2021-12-31 は開場 (土曜 New Year 非観測)、Juneteenth は 2022+ のみ
- **JP 祝日** = `structural_events.parquet` の jp_holiday=True の**平日のみ** (振替休日込み、
  年末年始 12/31・1/2・1/3 は祝日でない)。この規則で N_JP=84 を厳密再現
- **eve 規則**: eve(h) = h より前の直近の平日かつ非祝日。連続祝日 run は同一 eve に自動 dedup。
  イベント帰属窓 = **祝日 h の日付**で判定 (eve が窓外へはみ出すのは許容、例 2013-12-31)
- **US∩JP 共有 eve は両集団から除外** — explore 8 件: 2013-12-31, 2014-12-31, 2015-12-31,
  2016-12-30, 2017-11-22, 2017-12-29, 2018-12-31, 2019-12-31
- **再現済みカウント (凍結)**: US eve 63 / JP eve 84 / overlap 8 / レグ (c) USD_JPY N=52
  (欠落 11 = Christmas・New Year の FX 自体閉場、全 52 件で翌営業日バーも存在)
- **半日場** (感謝祭翌日・12/24 平日・12/26) は営業日扱い、flag を診断列に併記 (レグ c の
  Thanksgiving 翌日 D1 は構造的に半日場 — 除外しない、ex-ante 記録)

## 凍結事項 — 窓・データ

- **split = family 系譜どおり explore 2014-01-01〜2020-12-31 / OOS 2021-01-01〜2026-06-30**。
  ⚠️ 汎用 wave split (2014-2021/2022+) からの**明示逸脱** — 根拠: (i) 候補 payload
  (catalog #43/#52 test_design) が生成時からこの split で凍結、(ii) 観測フリー・カレンダー検証の
  全カウントがこの split で実施済み、(iii) 低 N family のため OOS 側の検定力を確保。
  OOS は候補凍結後 1 回のみ接触
- **データ**: main checkout `data/cache/massive/{PAIR}_1d_2014_2026.parquet` 7 ペア
  (USD_JPY, EUR_USD, GBP_USD, AUD_USD, NZD_USD, USD_CAD, USD_CHF) + `EUR_JPY_1d.parquet`
  (**2016-04-18 開始の部分参加** — ex-ante 記録)。1d バー = UTC 暦日、O→C で測定。
  pip = JPY クオート 0.01 / その他 0.0001
- **OOS 窓の細目**: US レグ = 休場 54 日 (2021:9, 2022:9, 2023:10, 2024:10, 2025:10, 2026H1:6。
  2025-01-09 服喪は除外)。JP eve は parquet 網羅域 **2021-01-01〜2026-04-30** まで

## 凍結事項 — レグ (a) pre-holiday risk-tilt (primary 1 本、両側)

- **イベント**: US eve (63−8=55) × 8 ペア + JP eve (84−8=76) × JPY 2 ペア (USD_JPY, EUR_JPY)。
  (pair, eve) はバー存在時のみ参加
- **basket 方向規約 (凍結)**: + = safer 通貨高。ヒエラルキー JPY > CHF > USD > その他。
  sign = {USD_JPY:−1, EUR_USD:−1, GBP_USD:−1, AUD_USD:−1, NZD_USD:−1, USD_CAD:+1, USD_CHF:−1,
  EUR_JPY:−1}。signed return = sign × (C−O)/pip
- **仮説 (両側)**: eve 日の pooled signed mean ≠ 0。**両側にする理由 (ex-ante)**: 機構 prior が
  符号で対立 — ブックフラット化/ヘッジ需要 = リスクオフ (+) vs 株式 pre-holiday drift の
  リスクセンチメント転写 = リスクオン (−)。符号を観測前に固定できない仮説は片側にしない。
  **PASS 時は explore の観測符号を OOS で凍結し片側化**
- **ホライズン**: eve 日の O→C (24h exit-free) のみが primary。+48h (eve O → 翌バー C) は診断

## 凍結事項 — レグ (c) US 休場翌営業日反転 (primary 1 本、片側)

- **イベント**: US 休場日 H (explore 63) × ペア P で、P の 1d バーが H と D1 (次の US 営業日 =
  凍結リスト外の次の平日) の両方に存在する組。USD_JPY で N=52 を再現済み
- **方向 = −sign(R_H)**、R_H = C_H − O_H (per pair)。R_H = 0 は除外
- **測定**: D1 の O→C を方向符号付け。**仮説 (片側)**: pooled mean > 0 (薄場ムーブは情報含有が
  低く反転する — 機構が符号を固定)
- Good Friday の D1 = 月曜 (週末跨ぎ) を含む (ex-ante 記録、診断で分解併記)

## 凍結事項 — 統計・判定 (機械適用)

- **月ブロック sign-flip permutation**: block = (year, month) (イベント日基準)。block 単位で
  全観測の符号を同時反転。**20,000 回、seed 20260729**。
  レグ a: p = (1+#{|perm mean| ≥ |obs mean|})/20001 (両側) / レグ c: p = (1+#{perm mean ≥ obs mean})/20001 (片側)。
  床は「p<1e-4」表記
- **family BH-FDR q=0.10、m=2** (レグ a, c の primary のみ。診断は分母に入れない)
- **必須合格条件 (レグごと、全て充足で PASS)**:
  - (i) BH-FDR 通過
  - (ii) 最小効果ゲート: |pooled mean| ≥ **5.0p** (系譜 #43 の 5p/day ゲート、DOW 型 sub-friction
    昇格の防止。最大 RT 4.53p 超の水準)
  - (iii) headroom: 方向側 MFE (dir=+ → H−O, dir=− → O−L; レグ a の dir = pooled mean の観測符号
    × basket 規約, レグ c は per-event dir) / RT_pair の pooled 中央値 ≥ **10**。
    RT 凍結値 = {USD_JPY 2.14, EUR_USD 2.00, GBP_USD 4.53, EUR_JPY 2.50} (KB friction 表) +
    {AUD_USD 3.00, NZD_USD 3.50, USD_CAD 3.50, USD_CHF 3.50} (保守的理論値)。
    実測フロア 1.30p の感度を診断併記
  - (iv) LOYO 頑健性: leave-one-year-out (イベント年 7 通り) 全てで pooled mean の符号不変
- **kill rule**: 上記いずれか不成立 → 当該レグ kill。両レグ kill → **family FAIL クローズ、
  OOS 未接触保存**、台帳 verdict 記録。**同型再試行禁止スコープ = 「祝日/休場カレンダーフラグ ×
  日次 (D1-D2) exit-free」** — 再挑戦は新モダリティ (intraday マイクロストラクチャ等) + 明示差分節のみ
- **knife-edge**: BH 閾値の 0.5〜2 倍域の p は 3 点検査 (LOYO / block 粒度を四半期に変更 /
  seed 変更) 全通過で初めて PASS
- **事後の閾値変更・ホライズン切替・sub-threshold 再解釈は禁止** (凍結ルールの機械適用)

## 凍結事項 — OOS (PASS レグのみ、単一接触)

- explore で PASS したレグのみ、同一定義・同一統計で OOS (2021-01-01〜2026-06-30、JP eve は
  〜2026-04-30) を 1 回だけ測定。レグ a は explore 符号に固定した**片側**。m = OOS 進出レグ数で BH
- 合格条件 (i)〜(iv) を同一適用 (LOYO は 2021〜2026 の年数で)
- **OOS PASS → R1 パケット起案で停止** (live 実装なし、user 最終承認まで)。FAIL → family クローズ

## 診断 (選択に使わない、報告のみ)

集団別 (US-eve / JP-eve) 分解 / per-pair 分解 / 非 basket 素符号 (クオート方向) mean / +48h /
eve 日レンジ比 (全平日 baseline 対比) / |R_H| 分布とレグ c の小 |R_H| 希釈率 / backfill 2 窓除外感度 /
半日場 flag 分解 / Good Friday (週末跨ぎ D1) 分解 / RT floor 1.30p 感度

## 隣接差分 (必須節)

- **session_time_bias (12y 全ペア REJECT)**: 毎日再帰する時計バケット vs 年 ~21 回の非再帰的
  市場クローズ状態イベント。estimand 独立 (カタログ生成時 grep で祝日フラグ検定ゼロを確認済み)
- **E15 無条件イベント窓 (FAIL 0/6)**: FF ニュースリリースの intraday 窓 vs 休場状態の日次
  ホライズン。データ源・状態変数とも別
- **vix_carry_unwind (kill、禁止 = VIX レベル閾値×JPY クロス short×固定 1-5d)**: レグ a の basket は
  リスクオン符号なら JPY short 成分を含む。**差分 = イベント定義が価格/vol 非条件のカレンダー事象**で、
  VIX 閾値 onset を含まない。禁止スコープ外であることを明示
- **T11 (REJECT)**: intraday cross-sectional MR vs D1 イベント条件付き時系列反転。knife-edge 3 点検査を標準装備
- **gotobi/仲値 (クローズ)**: 五十日は暦日周期 (市場は開いている)。本 family は「市場が閉まる」ことが条件
- **weekend_gap (live)**: 週末は本 family のイベントに含まれない (祝日のみ)。estimand も gap fill ではない
- **gbp_asia_flash_crash live 負けフィルタ**: 弱体化禁止 (原則 3)。本 explore は shadow/live に一切触れない

## 事前宣言 — 期待の較正

無料日次×カレンダー系は wave-1/2 で期待値較正済み (ほぼ枯渇)。**FAIL が既定路線**という前提で登録し
healthy kill を許容する。5p 最小効果ゲートと headroom≥10x は sub-friction 発見を昇格させないための装置。
本 explore は Stage 2 (wave-3 生成) の前座であり、pre-reg スロットを消費しない背景線。

## 成果物

`tools/holiday_liquidity_explore.py` / `knowledge-base/raw/bt-results/holiday-liquidity-explore-2026-07-29.json` /
`reports/holiday-liquidity-explore-2026-07-29.md` / 台帳 #15 verdict 追記
