# Family #5 cot_spec_positioning_extreme_weekly — EXPLORE report (2026-07-24)

**Verdict (explore-stage): ❌ FAIL — BH-FDR 生存ゼロ (primary m=36 / pooled m=6)。方向・ホライズン・通貨・サイド・年次のいずれにも整合的構造なし。OOS pre-reg は起案しない (無理に候補を作らない原則)。**

**Hypothesis (両方向を m にカウント)**: 投機筋 (CFTC legacy non-commercial) の net_pct_oi が rolling 3y percentile の極値にあるとき、(a) REVERSION: crowded trade の飽和 → 通貨は週次ホライズンで平均回帰する (fade the crowd)、(b) CONTINUATION: 機関投機筋のインフォームド・フロー → 継続する。母集団は機関投機筋 — E1 (Myfxbook リテール) とは別。E1 データには一切接触していない。

## 設計 (凍結パラメータ)

- **explore 窓**: COT シグナル 2010-01-05..2021-12-28 (2010-2012 は rolling 3y warmup に焼却)。**価格イベント窓は 2014-01..2021-11** — 12y parquet (`data/cache/massive/{PAIR}_1d_2014_2026.parquet`) が 2013-12-30 起点のため。2013 年のオンセット (計 23 件) は `pre_price_history` skip として正直に計上
- **OOS LOCK**: COT report_date と価格 index の両方を hard filter < 2022-01-01 + assert。**2022+ の COT×価格ジョイント分析は接触ゼロ**
- **シグナル**: net_pct_oi の trailing 156 週 (3y) percentile rank (backward-looking inclusive、リークなし)。極値ゾーン = pct ≥ 0.90 (crowded long) / ≤ 0.10 (crowded short)。p5/p95 は診断バンド (m 外、ラベル明示)
- **エピソード化**: 連続極値週 = 1 イベント。イベント = ゾーン・オンセット (圏外→圏内の最初の週) のみ — ポジショニングの強い自己相関による擬似反復を遮断
- **release-lag (凍結)**: report_date (火曜 as-of) + **3 営業日** = 金曜 15:30 ET 公表。entry = 公表後**翌週月曜の日足 Open** (祝日ガード ≤3d)。lookahead assert 2 本: `entry > publish` / `entry − report ≥ 6 日` (全 113 イベント通過)
- **ペア変換**: EUR/GBP/AUD = base (BUY 通貨 = BUY ペア)、**JPY/CAD/CHF = quote (BUY 通貨 = SELL ペア、符号反転をマップで固定)**
- **測定**: exit-free forward net/MFE/MAE @ {1w, 2w, 4w} = {5, 10, 20} 営業日バー (土日行は drop — MASSIVE feed 土曜行 artifact 対応)。entry バーを含む (entry 価格 = 当該バー Open、バー内の H/L は Open より後 — lookahead なし)。**net は REVERSION 方向に符号付け** (+ = fade the crowd 勝ち)、continuation は鏡像
- **摩擦**: RT 控除 + adverse swap stress 2.5%/年 × {7, 14, 28} swap-days (multi-week 条項 — swap 純額は方向依存のため adverse ケースで併記)。RT: EUR 2.0p / JPY 2.14p / GBP 4.53p (KB) + **AUD_USD 2.5p / USD_CAD 3.0p / USD_CHF 3.0p は KB friction table 外の理論仮置き**
- **統計**: one-sided episode bootstrap (B=10,000、seed 20260724)。pooled は entry-date block (同週クロス通貨相関)。**BH-FDR q=0.10、primary family m=36** (6 通貨 × 3 ホライズン × 2 方向)、pooled family m=6 別建て

## 1. イベント数 (検証)

| 通貨→ペア | signal 週 | 圏内週 | onsets | **N 測定** | 件/年 | エピソード長 p50 | skips |
|---|---|---|---|---|---|---|---|
| EUR→EUR_USD | 471 | 87 | 10 | **9** | 1.1 | 6w | pre_price 1 |
| GBP→GBP_USD | 471 | 111 | 21 | **17** | 2.1 | 3w | pre_price 4 |
| AUD→AUD_USD | 471 | 138 | 26 | **22** | 2.8 | 4w | pre_price 4 |
| JPY→USD_JPY | 471 | 157 | 33 | **26** | 3.3 | 2w | pre_price 7 |
| CAD→USD_CAD | 471 | 108 | 17 | **13** | 1.6 | 4w | pre_price 4 |
| CHF→USD_CHF | 471 | 123 | 30 | **26** | 3.3 | 2w | pre_price 3 / span_guard 1 |

Pooled N=113 (96 distinct entry Mondays)。エピソード化は効いている (圏内週 87-157 → イベント 9-26 = 擬似反復を 1/6〜1/10 に圧縮)。face validity: CHF 2015-01-06 crowded short onset → reversion = BUY CHF、entry 2015-01-12、01-15 SNB フロア撤廃 → net_1w +1538.3p。**バー単位の手検証で script 出力と完全一致** (net_1w 1538.3 / net_2w 1317.9)。JPY crowded long 2020-03-10 (COVID) → entry 03-16 → +389p (リスクオフ円高) も整合。

## 2. 通貨別 forward 統計 — net は REVERSION 方向 (pips、exit-free)

| 通貨 | h | net mean | net med | sd | p_rev | p_cont | MFE p50 (rev) | headroom rev/cont | swap stress | stressed rev / cont |
|---|---|---|---|---|---|---|---|---|---|---|
| EUR (N=9) | 1w | +17.9 | +44.1 | 94 | 0.275 | 0.716 | 91 | 46×/41× | 5.5 | +10.4 / −25.4 |
| | 2w | +45.2 | +64.4 | 206 | 0.236 | 0.755 | 124 | 62×/71× | 10.9 | +32.3 / −58.1 |
| | 4w | −125.0 | −54.3 | 201 | 0.984 | 0.017 | 133 | 66×/115× | 21.8 | −148.8 / +101.2 |
| GBP (N=17) | 1w | +11.7 | −8.4 | 172 | 0.392 | 0.604 | 96 | 21×/21× | 6.4 | +0.7 / −22.6 |
| | 2w | −105.4 | −82.6 | 201 | 0.991 | **0.008** | 96 | 21×/39× | 12.8 | −122.8 / +88.1 |
| | 4w | −14.8 | −59.5 | 517 | 0.550 | 0.439 | 141 | 31×/61× | 25.7 | −45.0 / −15.4 |
| AUD (N=22) | 1w | −4.2 | −18.8 | 106 | 0.588 | 0.427 | 60 | 24×/33× | 3.6 | −10.3 / −1.9 |
| | 2w | −35.2 | −14.2 | 126 | 0.909 | 0.089 | 70 | 28×/47× | 7.2 | −44.8 / +25.5 |
| | 4w | −5.4 | −32.5 | 154 | 0.556 | 0.439 | 117 | 47×/53× | 14.3 | −22.2 / −11.5 |
| JPY (N=26) | 1w | +3.7 | +4.7 | 166 | 0.450 | 0.540 | 74 | 35×/25× | 5.3 | −3.7 / −11.1 |
| | 2w | −32.7 | −6.6 | 184 | 0.823 | 0.173 | 90 | 42×/40× | 10.5 | −45.4 / +20.0 |
| | 4w | −13.6 | +7.4 | 244 | 0.605 | 0.394 | 120 | 56×/68× | 21.1 | −36.8 / −9.6 |
| CAD (N=13) | 1w | +8.5 | +3.9 | 100 | 0.377 | 0.619 | 90 | 30×/17× | 6.2 | −0.8 / −17.7 |
| | 2w | +34.2 | +28.2 | 163 | 0.212 | 0.782 | 132 | 44×/36× | 12.5 | +18.8 / −49.7 |
| | 4w | +49.2 | +21.4 | 176 | 0.148 | 0.858 | 196 | 66×/47× | 24.9 | +21.3 / −77.1 |
| CHF (N=26) | 1w | +77.3 | +5.0 | 320 | 0.076 | 0.918 | 80 | 27×/25× | 4.6 | +69.6 / −84.9 |
| | 2w | +50.2 | −18.9 | 284 | 0.183 | 0.812 | 108 | 36×/29× | 9.3 | +37.9 / −62.5 |
| | 4w | +30.1 | −0.7 | 228 | 0.265 | 0.745 | 185 | 62×/39× | 18.6 | +8.6 / −51.7 |

### Pooled (N=113、entry-date block bootstrap)

| h | net mean (pips) | net med | net mean (bp) | p_rev | p_cont |
|---|---|---|---|---|---|
| 1w | +22.0 | +1.2 | +21.3 | 0.119 | 0.882 |
| 2w | −11.1 | −16.7 | −8.9 | 0.726 | 0.283 |
| 4w | −3.8 | −22.6 | −1.1 | 0.554 | 0.447 |

**pooled 1w reversion (+22.0p) は SNB 1 イベント (+1538p) が 63% を占める** — 除外で mean +8.4p / median **+0.9p**。pips と bp で符号・大きさ一致 (pip 異質性の問題ではない)。

## 3. BH-FDR 判定 (q=0.10)

- **primary family (m=36)**: min p = **0.0077** @ GBP|2w|continuation。BH 閾値 k=1 で 0.10/36 = **0.0028** → **生存 0/36**
- **pooled family (m=6)**: min p = **0.119** @ pooled|1w|reversion → **生存 0/6**

min-p セル (GBP 2w continuation、N=17) は両隣ホライズンが不支持 (1w: rev 側 +11.7p / 4w: cont mean わずか +14.8p、p=0.44) の**単一ホライズン孤立シグナル** — T11 教訓のナイフエッジ型。BH を通過していたとしても kill 対象の形状。

## 4. 診断 — 構造の不在 (全滅の質的確認)

1. **ホライズン間の符号反転**: EUR は 2w rev +45p → 4w rev −125p。GBP は 2w だけ continuation。効果が実在するならホライズン間で单調に蓄積/減衰するはず
2. **サイド split (2w, fade 方向 mean)**: EUR long-fade −61 / short-fade **+178**、JPY long-fade −85 / short-fade **+28**、CAD +4 / +70、GBP −60 / −170 — サイド間で符号が割れる通貨が半数。crowding メカニズムなら両サイド同符号のはず
3. **extremity terciles (onset percentile 極端度 × net2w median)**: 単調性 **0/6 通貨** (increasing も decreasing もゼロ)
4. **年次安定性 (pooled net2w mean)**: 2015 +85 / 2016 **−144** / 2017 +8 / 2020 +18 — 年次で符号が振動
5. **診断バンド p5/p95 (m 外)**: EUR は continuation 寄り (p_cont 0.03-0.08)、CAD は reversion 寄り (p_rev 0.015-0.078、N=11)、AUD も rev 寄り、JPY は 1w cont 寄り — **通貨間で逆方向に「有意風」が出る**のはノイズの多重比較そのもの。バンドを締めても方向が収束しない

## 5. Headroom と摩擦 (参考)

- headroom (MFE p50 / RT) は **21×〜115×** で全セル充足 — 週次ホライズンではカタログ入場条件 (10×RT) は無拘束。**拘束は方向性の不在であり、器の不足ではない**
- adverse swap stress (2.5%/年) は 4w で 14-26p — 週次 sd (100-320p) 比で小さいが、仮に小さいエッジ (数十 pips) が実在しても 4w 保有では実質的な hurdle になる水準 (multi-week 条項の定量確認)

## 6. Honest read

1. **per-currency は検出力不足が構造的** (N=9-26、weekly sd 100-320p → BH 通過に必要な効果 ≈ 60-150p/週)。しかし FAIL の根拠は検出力だけではない — **pooled (N=113) の点推定自体が小さく (±22p 以下) かつ符号不安定**。「有望だが underpowered」ではなく「点推定が incoherent」
2. 唯一目立つ pooled 正値 (1w rev +22p) は SNB depeg 1 件の外れ値駆動 (median +0.9p)。イベント・アウトライアを除くと何も残らない
3. 学術文献とも整合: legacy COT の投機筋ポジションに FX 先物の予測力がほぼ無いという null 結果 (Sanders, Irwin & Merrin 2009 等) を再確認した形
4. 3y percentile / p10-p90 / episode-onset という 1 つの設計点しか試していない (パラメータ探索なし — カーブフィッティング禁止準拠)。ただし §4 の構造不在 (サイド不一致・tercile 非単調・年次振動) は閾値やウィンドウの選び直しで治る形状ではない — **同型再試行 (percentile 窓/閾値の変種) は非推奨**
5. **変化率系 (net の週次Δ、flow) や commercial (実需) 側は本 explore の対象外** — 別 estimand であり、起こすなら新 family + 台帳新行 + pre-2022 explore から (本結果による ban は「net_pct_oi レベル極値 × 週次ホライズン」に限定)

**→ 台帳 family #5 の運用ルール「explore IC が綺麗な場合のみ pre-reg スロット消費」に従い、OOS pre-reg は起案しない。OOS (2022-01-01..2026-06-30) の COT×価格ジョイント分析は未接触のまま保存される。**

## Artifacts

- Script: `tools/cot_extreme_explore.py` (seed 20260724、B=10,000; OOS lock assert ×2 + release-lag lookahead assert ×2)
- JSON: `bt-results/cot_extreme_explore-2026-07-24.json` (per-event リスト・全診断込み)
- This report: `reports/cot_extreme_explore-2026-07-24.md`
- Pre-reg DRAFT: **なし** (生存候補ゼロ)
