# E20 金利差方向バイアス × テクニカル entry — S1 feasibility 裁定 (2026-07-22)

> **rule:R3 (S1 feasibility、読み取りのみ)**。live/shadow 不変更。エッジ主張なし。
> **起点**: user 仮説 (2026-07-22)「金利差から計算した方向バイアス × テクニカル entry」を E20 として
> [[edge-development-pipeline-2026-07-18]] S1 (hard constraints C1–C6) で裁定する。
> **関連**: [[external-hypothesis-scan-2026-07-13]] (E1–E6) / [[external-hypothesis-scan-round2-2026-07-18]] (E7–E19) /
> [[ws3-round3-crossasset-divergence-prereg-2026-07-13]] (round-3 FAIL 台帳) / [[hull-donchian-usdchf-ratediff-prereg-2026-06-15]] /
> [[d1-tsmom-basket-pre-reg-2026-06-08]] / [[menkhoff-2012]] / [[iwanaga-sakemoto-2024]]

---

## 1. 仮説定義 (E20)

**E20**: 8 通貨 (USD/EUR/JPY/GBP/AUD/NZD/CAD/CHF) の**日次金利差** — (a) 政策金利差 (level) または
(b) 2y 国債利回り差 (level / 20–63 日変化 = rates momentum) — の符号を**方向バイアス**とし、
テクニカル entry (既存 15m/1h シグナル系 or 日足 entry) を**バイアス方向に限定**する。保有 **1–10 日**。

- **機構仮説**: carry / rates-momentum リスクプレミア (Lustig-Roussanov-Verdelhan 2011、Menkhoff 2012、
  Koijen et al 2018 "Carry")。金利差の符号・トレンドは高金利通貨買い方向の持続的ドリフトを生む。
  シグナルは**低頻度・遅変化** (政策金利は年数回、2y 差の符号転換も年オーダー) — マイクロ構造エッジではなく
  マクロ・リスクプレミアの harvesting + テクニカル entry によるタイミング改善。
- **非主張**: intraday の先行性 (lead-lag) や乖離回帰は**主張しない** (どちらも falsified 済み、§2)。

## 2. falsified 台帳との区別 (C2 の核心 — 先に確定)

### 2a. round-3 cross-asset divergence-reversion (❌ PASS=0、2026-07-14) との区別 — **別仮説**

[[ws3-round3-crossasset-divergence-prereg-2026-07-13]] §8 で死んだのは
「**ZN 先物価格 (1h bar) からの FX 乖離 z-score が 6–48 バーで平均回帰する**」(first-touch EV レグ)。4 軸すべてで異なる:

| 軸 | round-3 (死んだ) | E20 (本裁定) |
|---|---|---|
| データ | ZN=F **先物価格系列** 1h (単一 US rates proxy) | **現物国債利回り差 / 政策金利差** 日次 (8 通貨パネル) |
| 頻度 | intraday 1h、h=6–48 bar | **日足**、保有 1–10 日 |
| 機構 | dislocation の**平均回帰** (逆張り) | carry / rates-momentum の**継続** (順方向バイアス) |
| 役割 | 単独シグナル (first-touch EV) | **条件付けバイアス × テクニカル entry** |

round-3 の結語「価格情報からの systematic edge は枯渇」は **intraday の tradeable 構造**についての確定。
E20 は非価格系列 (金利パネル) を**日次リスクプレミア**として使う別モダリティであり、再試行に該当しない。
なお round-3 §8 の窓消費 (2025-07-01〜2026-05-15) は divergence-reversion family 限定 — E20 は別 family で
未消費 (S3 で窓消費履歴に明記のこと)。

### 2b. hull-donchian USD_CHF 金利差 regime ゲート (FALSIFIED 2026-06-15) との区別 — **claim が逆**

[[hull-donchian-usdchf-ratediff-prereg-2026-06-15]] で falsified されたのは「**wide 金利差が pair をレンジに
ピン留めし fade (逆張り) が効く**」という **range-pinning ゲート**仮説 (USD_CHF 単体、S1 反証窓 2018–19 で
−1.14p、単調性も逆)。E20 の claim は**正反対** (金利差方向への**継続**バイアス) であり同一仮説の再試行ではない。
ただし教訓は直接輸入する: **(i) 金利差 bin での単調性検査を S2 必須ガードにする (ii) 「post-2020 が良い」型の
regime 選択を金利差に偽装しない — 反証窓 (pre-2020 同条件窓) の設計を S3 で義務化**。

### 2c. D1 TSMOM basket (NULL 2026-06-08) との区別 — シグナル源が別、教訓は輸入

[[d1-tsmom-basket-pre-reg-2026-06-08]] は**価格モメンタム** (1–12m lookback) の NULL。E20 のシグナルは
金利差 (非価格) で family が別。ただし NULL 解剖の 2 教訓を S2 ガードに内蔵する:
**(i) USD 集中** — 8 USD-pair バスケットは実質単一 USD ベット (net USD = gross の 54%)。E20 は cross-rate
(EUR_JPY / GBP_JPY / AUD_JPY 等) を含め USD-neutrality を診断必須。
**(ii) 2016–2026 は FX トレンドプレミア圧縮 regime** — carry も 2021 年以前は ZIRP 収斂で金利差がほぼ消失していた。
regime slice (pre-2021 収斂期 / 2022–23 発散期 / 2024 unwind 期) を必ず分けて報告。

### 2d. E5 term-structure (棄却 2026-07-13) との関係 — **C1 棄却理由が解消された部分的復活**

E5 は「forward/swap curve データ不能」の **C1 棄却** (仮説内容は未検証)。CIP により forward discount ≈ 金利差
であり、本セッションで国債利回り/政策金利の keyless 経路を実確認 (§3) → **日次粒度では C1 の障害が解消**。
E20 は E5 の「carry 系」部分の data-feasible な再定式化と位置づける (forward points 精度は不要な構成のみ)。

### 2e. その他 falsified 6 系統 (H4 level / channel / horizontal sweep&reclaim / mtf SELL / bb_rsi / T11) — 非該当 (全て価格パターン系統)。

## 3. データ台帳 — 実 fetch 証跡 (2026-07-22、全て本セッションで一次確認)

**方針**: FRED はキー不在で不可 (前提)。全ソース keyless。「ありそう」は排除し、実 fetch の HTTP code・
行・値・期間を記録。

| # | 通貨 | ソース / エンドポイント | 粒度・系列 | 深さ (実測) | 鮮度 (実測) | go-forward | 証跡 |
|---|---|---|---|---|---|---|---|
| D1 | **USD** | **MASSIVE (in-house)** `/fed/v1/treasury-yields` | 日次 1m〜30y (2y/10y 列あり) | 仕様 1962+、**2014-01-02 実取得** (2y 0.39/10y 3.00) | **2026-07-20** (2y 4.21/10y 4.60) | ✅ in-house API そのまま | call_api 2 回実取得 |
| D2 | **EUR** | ECB Data Portal `data-api.ecb.europa.eu/service/data/YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y` (SR_10Y も) | 日次 AAA ゾーン Svensson spot、全テナー | **2004-09-06 実取得** (2.641) | **2026-07-20** (2y 2.710/10y 3.168) | ✅ keyless REST、CSV | curl 4 回 200 |
| D3 | **JPY** | MOF `mof.go.jp/jgbs/reference/interest_rate/data/jgbcm_all.csv` | 日次 JGB 1y–40y (Shift-JIS、和暦) | **S49.9.24 = 1974-09-24 実取得**、13,250 行 | **R8.6.30 = 2026-06-30** (2y 1.165/10y 2.690) — **更新ラグ ~3 週** | ✅ 同一 CSV が追記更新 (ラグ月次オーダー、政策金利で補間可) | curl 200 1.17MB 全 DL |
| D4 | **GBP** | BOE IADB `bankofengland.co.uk/boeapps/iadb/fromshowcolumns.asp?csv.x=yes&SeriesCodes=IUDSNZC,IUDMNZC…` (ZC 5y/10y。IUDSNPY/IUDMNPY par、IUDBEDR Bank Rate も稼働) | 日次 gilt zero-coupon / par | **1995-01-03 実取得** (10y ZC 8.65) | **2026-07-09** (10y ZC 4.975) | ✅ keyless CSV API (要 `-L` リダイレクト追従) | curl 200 ×3 |
| D5 | **CAD** | BoC Valet `bankofcanada.ca/valet/observations/BD.CDN.2YR.DQ.YLD,BD.CDN.10YR.DQ.YLD/json` | 日次 benchmark 2y/10y | **2001-01-02 実取得** (2y 5.11/10y 5.28)、それ以前は空 | **2026-07-13** (2y 2.88/10y 3.56) | ✅ keyless JSON/CSV API | curl 200 ×3 |
| D6 | **CHF** | SNB `data.snb.ch/api/cube/rendoblid/data/csv/en` (連邦債 spot 1J–30J) | 日次 2J/10J0 | **1988-01-04 実取得** (2J 3.691) | ⚠️ **2025-07-31 で凍結** (PublishingDate 2025-09-01、全テナー同時停止 = cube 廃止/改編とみられる) | ❌ gap — 後継 cube 未解決 (S2 前に 1 probe)。**政策金利は D9 で現行** | curl 200 5.4MB 全 DL、全テナー max 日付検査 |
| D7 | **AUD** | RBA `rba.gov.au/statistics/tables/csv/f2-data.csv` (FCMYGBAG2D/FCMYGBAG10D) | 日次 AGS 2y/3y/5y/10y | 直 curl / WebFetch とも **403 (Akamai、UA 偽装でも不可)**。**Wayback 実取得 OK**: 2023-06-08 snapshot = 2021-01-04〜2023-06 (2y 0.08 @2021-01-04)。CDX 上のスナップショットは 2018〜2023 に点在 → **歴史 stitching は 2018+ 限定・非連続リスク** | ❌ 最新 snapshot 2023-06 | ❌ gap — 政策金利 (D9、last 2026-07-09) が fallback。Render 本番 IP からの直 fetch は未検証 (別 IP で通る可能性はあるが**主張しない**) | curl 403×2 + Wayback 200 126KB + CDX 照会 |
| D8 | **NZD** | RBNZ `rbnz.govt.nz/.../b2/hb2-daily.xlsx` (INM.DG102.N = govt 2y、10y 列も同帳票) | 日次 OCR + 国債 1y/2y/5y/10y | 直 curl **403 (WAF)**。**Wayback 2025-02-01 snapshot 実取得 OK** (2018-01-03〜、2y 1.91 @2018-01-03)。旧年ファイル (2009–2017 等) も同経路と推定 (未実測) | ❌ 最新 snapshot 2025-02 | ❌ gap — 政策金利 (D9、last 2026-07-10) が fallback | curl 403 + Wayback 200 254KB、openpyxl で列名実確認 |
| D9 | **全 8 通貨 政策金利** | **BIS SDMX** `stats.bis.org/api/v1/data/WS_CBPOL/D.US+XM+JP+GB+AU+NZ+CA+CH/all?format=csv` | **日次パネル、単一エンドポイント** | 数十年 (CH は 1946 起点と系列注記。**1999-01 実取得** CH/NZ) | **2026-07-14** (US 3.625/XM 2.25/JP 1.0/GB 3.75/CA 2.25/CH 0.0)。**AU 2026-07-09 / NZ 2026-07-10 = 公表ラグ ~1 週** | ✅ keyless。ラグ ~1 週は政策金利の変化頻度 (年数回) に対して実害小 (決定日直後のみ注意) | curl 200 ×3、8 REF_AREA 実値確認 |

**FX 側 (突合対象)**: MASSIVE C:EURUSD 日足 **2014-06 実取得** / 2005 は空 → **FX 日次パネルの床 ≈ 2014**
(12y、in-house 済)。金利パネルの方が深いので、BT 有効窓は FX 側律速で **2014-06〜2026-07 (~12y)**。

**台帳サマリ**:
- **政策金利差パネル = 8/8 通貨、単一 keyless ソース (BIS)、10y+ 深度、go-forward 稼働中** — E20 primary に十分。
- **2y 国債利回り差パネル = 6/8 が現行** (USD/EUR/JPY/GBP/CAD + CHF は 2025-07 まで)。AUD/NZD は
  Wayback stitching で BT 用歴史は組めるが (2018+)、**go-forward は WAF で経路なし**。
- **E1 型の不可逆性は無い** — 政策金利・主要国利回りはいつでも遡及再取得可能。例外は AUD/NZD 国債利回り
  (Wayback 頼み、snapshot 頻度は年オーダー) と CHF 後継 cube。**「今から蓄積しないと消える」データではない**
  (E12 の 730d rolling とは構造が違う) — ingest は S2 GO と同時で間に合う。

## 4. C1–C6 裁定表

制約定義は [[external-hypothesis-scan-2026-07-13]] §4 と同一。

| 制約 | 判定 | 根拠 |
|---|---|---|
| **C1 データ実現可能性** | ✅ (政策金利 8/8 現行) / △ (2y 利回りは 6/8 現行、AUD/NZD go-forward gap) | §3 実 fetch 台帳。BT は今日から可能 (蓄積待ちゼロ、E15 と同型の利点)。FX 側 12y (MASSIVE in-house) |
| **C2 falsified 区別** | ✅ | §2 で 4 系統 (round-3 / hull-ratediff / D1 TSMOM / E5) と個別に区別確定。ただし hull-ratediff・D1 の**教訓ガード 3 点を S2 必須化** (単調性 / USD-neutrality / regime slice) が条件 |
| **C3 portfolio 非重複** | ✅ | rates データを使う稼働戦略ゼロ。E1 (positioning)・E15/E7 (イベント)・E12 (volume) と直交。round-4 条件付き (EUR divergence) は intraday 逆張りで構成が別 (両方 rates を使う点のみ S3 で相互参照) |
| **C4 摩擦生存** | ✅ (定性、§5) | 保有 1–10 日: RT 2–4.5p は日次ボラ 60–100p の 3–7%、5 日ホールドの σ (~130–220p) の 2–3%。intraday (15m σ 8–15p に対し RT 20–40%) 比で**摩擦比 ~10 倍有利**。ただし financing/swap を EV モデルに必須算入 (§5) |
| **C5 反カーブフィッティング** | ✅ (条件付き) | 単一変数 (金利差符号 / Δ符号) の simple-first。variant は **2 つに事前凍結** (carry-level / rates-momentum)。horizon×pair の discovery は BH-FDR pre-reg 必須 (WS3 同一方法論) |
| **C6 revealed-edge 整合** | ✅ | 「バイアス × テクニカル entry」= LIVE 側 winning-location フィルタ設計 (原則 3) と同型。唯一 ELITE_LIVE の trendline_sweep には触れない (bias overlay の検証は shadow/BT read-only で行う) |

## 5. 摩擦生存の事前確率 (C4 定性詳細)

1. **スプレッド/スリッページ**: RT 2–4.5p 固定に対し、保有 1–10 日の期待変動は日次 ATR 60–100p ×
   √(1–10) = 60–320p。摩擦比 1.4–7.5% — 本プロジェクトの intraday 帳簿 (20–40%) と比べ構造的に有利。
2. **financing/swap (多日保有の新規摩擦項)**: OANDA financing ≈ 金利差 ± markup (~0.5–1.5%/年)。
   carry 方向に張る場合は**追い風** (差 2.6% の USD_JPY ロングで ~+1.0p/日 − markup ~0.4p/日)。
   rates-momentum variant が anti-carry 方向になる局面では**逆風** (差 + markup が両方コスト)。
   → S2 の EV primitive に **financing 項 (±diff/365 × price − markup/365 × price × hold 日数) を必須実装**。
3. **週末ギャップ**: 1–10 日保有は週末跨ぎ必然。ギャップはバイアス方向に対称でない保証なし — S2 で
   週末跨ぎ有無の EV 分解を報告項目に含める。
4. **文献事前確率**: G10 carry は取引コスト控除後も有意が通説 (Menkhoff 2012 JF、Burnside 2011)、
   ただし 2010 年代にプレミア圧縮、2024-08 に大型 unwind。E20 のシグナルは遅変化で turnover 極小のため
   コスト側は問題にならない — **リスクは摩擦でなく「エッジが regime 依存 (2022–23 発散期に集中) か」**。
   これは round-3 の教訓 (探索窓 regime artifact) と同型の罠であり、S2/S3 の regime slice + 反証窓設計で潰す。

## 6. 判定 — **条件付き採用 → S2 (R3 診断) GO**

採用条件 (S2/S3 設計に義務として持ち込む):
1. **claim は継続バイアスのみ** — 金利差による fade/range ゲート側の主張は [[hull-donchian-usdchf-ratediff-prereg-2026-06-15]] で falsified 済みのため本 family では禁止。
2. **variant 事前凍結 (2 本)**: (a) carry-level = sign(政策金利差) (b) rates-momentum = sign(Δ63d 2y 差)。第 3 variant の後出し追加は禁止。
3. **教訓ガード 3 点を S2 レポート必須項目に**: 金利差 quintile 単調性 / USD-neutrality (cross-rate 込みパネル) / regime slice (≤2021 収斂・2022–23 発散・2024+ unwind)。
4. **pair scope**: BT は 13 ペア可 (AUD/NZD は Wayback 歴史 + 政策金利)。**live go-forward を要する段階では 2y variant は AUD/NZD 除外 or 政策金利 variant に限定** (§3 gap)。
5. **horizon 帳簿警告 (E9 と同じ △)**: 保有 1–10 日は現行エンジン (15m/1h、intraday 志向) の上限外。S5 到達時に hold 機構の実装が必要になることを pre-flag — S1/S2 の feasibility には影響しないが、M1 寄与のリードタイムに含める。

**優先順位の位置づけ**: E15/E7 (verdict 07-31) と E1 (10-15) が先行稼働中のため、E20 は
[[edge-development-pipeline-2026-07-18]] §3 WIP 原則の**第 3–4 系統** (金利モダリティ) として並走に足る。
蓄積待ちゼロで S2 は数日で完了可能 — E15 FAIL 時の後継候補としての価値が高い。

## 7. S2 診断の推奨 spec (rapid_edge_probe 用)

- **ハーネス**: `tools/rapid_edge_probe_e20.py` (新規)。データローダは `tools/tsmom_basket_bt.py` (D1 MASSIVE)、
  IC 計測は `tools/h4_level_edge_explore.py` / `tools/ws3_crossasset_divergence_explore.py` の流儀を流用。
- **データ準備**: `data/cache/rates/` を新設 — BIS WS_CBPOL 日次 8 通貨 (D9) + 2y 利回り (D1–D6、
  AUD/NZD は Wayback stitch)。UTC 日付で FX D1 (MASSIVE、2014-06+) に as-of merge
  (**公表ラグ分は shift(1) で look-ahead 排除**。BIS AU/NZ の ~1 週ラグも as-of で自然に扱う)。
- **探索窓 / OOS 温存 (S2 は探索窓のみに接触)**: 提案 = 探索 2014-06-01〜2022-12-31 / OOS 温存
  2023-01-01〜cache 末尾 (~3.5y、2024 unwind と 2025–26 を含む判別力の高い窓)。確定は S3 pre-reg で。
- **計測 (探索窓のみ)**:
  1. 無条件バイアス IC: sign(diff) / sign(Δdiff) vs forward k 日リターン (k∈{1,3,5,10})、pair 別 +
     panel pooled、日次ブロックブートストラップ。
  2. 摩擦調整 EV: RT 2.5p + financing (±diff − markup 1%/年、§5-2 式) 込みの k=5 保有 EV (p/t)。
  3. ガード 3 点 (§6-3) + 発火頻度 (バイアス符号の変化回数/年 — turnover 確認)。
  4. テクニカル entry 相互作用の予備計測 (read-only): 既存 shadow 履歴の entry 方向とバイアス一致/不一致で
     成績 2 分割 (bias-agreement uplift)。live/shadow への変更はしない。
- **S2 exit 条件**: pooled IC が機構整合符号で有意水準に近い ∧ EV_net(k=5) > 0 ∧ 単調性 OK →
  S3 pre-reg (型 B: discovery→凍結→OOS) 起案。いずれか大きく欠ける → 棄却 doc 化 (research/ に append)。
- **infra (S2 GO と同時、R3・E1 と同じ決裁枠)**: 週次 rates ingest job (BIS + D1–D5 API) を
  `data/cache/rates/` に追記 — 遡及可能データが大半のため緊急性は低いが、AUD/NZD/CHF の経路解決
  (CHF 後継 cube 1 probe、AUD/NZD は政策金利で開始) だけ先に確定させる。

---

## 本裁定の位置づけ

- 実行: 2026-07-22、S1 feasibility (R3、読み取りのみ)。データ実在は全て本セッション一次確認
  (curl HTTP code / 実値 / 期間を §3 に記録、「ありそう」ゼロ)。
- 前回: [[external-hypothesis-scan-2026-07-13]] (E1–E6) / [[external-hypothesis-scan-round2-2026-07-18]] (E7–E19)。
  本裁定で E20 を**条件付き採用 (S2 GO)** — 金利モダリティは両スキャンの結論「供給は新データモダリティから」
  に対する第 4 の具体ライン (sentiment / event / flow / **rates**)。
- **次アクション**: (1) S2 rapid_edge_probe (§7 spec、数日) (2) CHF 後継 cube probe + AUD/NZD 経路確定
  (3) S2 通過時は型 B pre-reg 起案 (WS3 同一方法論、windows は §7 提案から S3 で LOCK)。
