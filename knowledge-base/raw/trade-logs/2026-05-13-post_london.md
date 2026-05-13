# Post-London Report: 2026-05-13

## Analyst Report
# ロンドンセッション総括レポート
**2026-05-13 JST 01:00（UTC 16:00）時点**

---

## 1. ロンドンセッション結果

| 指標 | 値 |
|---|---|
| トレード数 | 3件 |
| 勝率 | 66.7%（2勝1敗） |
| セッションPnL | **+14.9 pips** |
| 平均PnL/トレード | +4.97 pips |

セッション全体として小幅プラス。ただし3件は統計的判断に十分なサンプルではなく、傾向の確認に留める。

---

## 2. What Worked ✅

| 戦略 | ペア | PnL | 件数 |
|---|---|---|---|
| **sr_fib_confluence** | GBP_USD | **+29.0 pips** | 2件 |

- **成功要因**: GBP_USDがRANGINGレジーム（ATR%ile=53%、SMA傾斜+0.208と緩やかな上昇）にあり、S/R+Fib水準がレジスタンスとして機能したSELL2発が共にOANDA_SL_TP決済で完遂。
- 特に1件目（+27.7 pips）はRR比が良好で、spread（1.3）対比でも十分なリターン。

---

## 3. What Didn't Work ❌

| 戦略 | ペア | PnL | 件数 |
|---|---|---|---|
| **xs_momentum** | GBP_USD | **-14.1 pips** | 1件 |

- **失敗要因**: RANGING環境（ATR%ile=53%）でモメンタム戦略を発動したが、方向性が持続せずSL_HIT。RANGINGレジームはモメンタム系にとって構造的不利環境であり、今回のSELL方向に対しGBP_USDのSMAは上向き（+0.208）—逆方向への偏りが原因。

---

## 4. 東京セッションとの比較

東京セッションデータが本データに含まれていないため直接比較数値は取れないが、以下の観察を記録する：

| 観点 | 評価 |
|---|---|
| 本日累計 = セッション内累計（N=3, +14.9pips） | 東京セッションでのトレードは**ゼロ**と推定 |
| ロンドン活性度 | 僅か3件——システムは大量にBlock（max_open/hedge_block）されており、エントリー機会が著しく制限された |
| レジーム変化 | EUR_JPY・GBP_JPY共にVOLATILE（ATR%ile 79-83%）——JPY主導の荒れた値動きがDaytrade系のhedge_blockを連発させた可能性が高い |

**東京比較の結論**: 東京でゼロ → ロンドンで3件。ロンドン開始でGBP_USDが動いたことで初めてエントリーが通った。しかしBlock件数の多さ（daytrade系hedge_blockだけで計803件）は、日中を通じてシステムが「待機状態」に近かったことを示す。

---

## 5. NYセッション準備（UTC 16:00以降）

### レジーム・ATR変化予測

| ペア | 現在レジーム | NY移行予測 | 理由 |
|---|---|---|---|
| GBP_USD | RANGING(53%) | **RANGING維持〜軽微なVolatility上昇** | NY初動での米指標次第だが基本RANGING継続 |
| USD_JPY | RANGING(78%) | **RANGING（高ATR）** | 78%ile——すでにATR高め、方向感は出にくい |
| EUR_USD | RANGING(34%) | **RANGING維持** | ATR低位（34%ile）、大きな動きは期待薄 |
| EUR_JPY / GBP_JPY | VOLATILE(83%/79%) | **VOLATILE継続警戒** | JPYボラが高水準——DT系のhedge_blockが継続するリスク大 |

### 推奨戦略配分

| 優先度 | 戦略 | ペア | 根拠 |
|---|---|---|---|
| **高** | **sr_fib_confluence** | GBP_USD | 本日実績あり、RANGING環境に適合。引き続き待機エントリー狙い |
| **中** | **trendline_sweep** (ELITE_LIVE) | EUR_USD, GBP_USD | WR実績高（BT: EUR 80.8%、GBP 73.1%）、RANGING環境でも機能しやすい |
| **低** | **xs_momentum** | GBP_USD | **RANGING継続中は不利。本日すでに-14.1pips。NOY推奨** |
| **待機** | DT系（daytrade_eurjpy等） | — | VOLATILE継続でhedge_blockが多発する構造的問題あり、今夜は期待薄 |

> ⚠️ **xs_momentumについては「何もしない」が最適**：RANGINGレジームでモメンタム系を積極起用するのは摩擦負けリスクが高い。

---

## 6. 本日暫定結果

| 指標 | 値 |
|---|---|
| 累計トレード数 | **3件** |
| 累計WR | **66.7%** |
| 累計PnL | **+14.9 pips** |
| OANDA Live転送率 | **16%**（50件中8件SENT） |
| OANDA Bridge（本セッション） | sent=1, filled=1, skipped=18 |

---

## 7. クオンツ見解

### 🔴 最重要シグナル

**xs_momentum (GBP_USD) のRANGING環境での稼働継続が最大リスク。**

BT乖離テーブルに注目: `xs_momentum / GBP_USD` はBT WR=63.5%に対しLive WR=25.0%（N=4、ΔWR=**-38.5pp**）で🔴アラート発令中。今日の-14.1pipsはこの乖離パターンの延長線上にある。N=4と小サンプルではあるが、**RANGINGレジームでモメンタム系が機能しない**という構造的説明がつく。BTデータが存在しない（N_BT=0）にもかかわらずLive起動している点も懸念。

**推奨アクション**: xs_momentum/GBP_USDはN=30到達まで引き続き観察継続だが、RANGINGレジーム継続中の間は**SENTINEL格下げまたは取引停止**を検討すべきタイミング。N=4で判断するのは早計だが、方向性（レジーム不適合）は明確にネガティブ。

一方、**sr_fib_confluence (GBP_USD)** は本日+29.0pipsと好調。KB記載のBTデータ（EUR_USD: EV=+0.103, USD_JPY: EV=+0.252）はGBP_USDではなく、本ペアはBT未集計——すなわちLiveデータで独自にN蓄積中という点で、今後のN=30達成を注視すべき戦略筆頭候補。
