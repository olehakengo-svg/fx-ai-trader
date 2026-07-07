# Post-London Report: 2026-06-24

## Analyst Report
# ロンドンセッション Post-London Report
**2026-06-24 | UTC 07:00–16:00 総括 (JST 01:00)**

---

## 1. ロンドンセッション結果

| 指標 | 値 |
|---|---|
| セッション内トレード数 | **1件** |
| 勝率 (WR) | **100.0%** |
| セッションPnL | **+2.4 pips** |
| 決済方式 | OANDA_SL_TP（正常決済） |

極めて低頻度のセッション。システム全体として**24モード稼働中、発火はvsg_jpy_reversal/EUR_JPYの1件のみ**。

---

## 2. What Worked

| 戦略 | ペア | 方向 | Outcome | PnL | Spread |
|---|---|---|---|---|---|
| vsg_jpy_reversal | EUR_JPY | SELL | WIN | +2.4 pips | 1.5 pips |

**成功要因**: EUR/JPYがVOLATILE（ATR%ile 67%、SMA20 Slope −0.00032の緩やかな下方傾斜）の環境下でSELLシグナルが機能し、スプレッド1.5pipsを差し引いても正EV実現。OANDA_SL_TPによる規律ある決済が奏功。

---

## 3. What Didn't Work

**該当トレードなし**（セッション内の敗北トレードは0件）。

ただし、機会損失の観点では深刻な構造的ブロックが継続：

| ブロック主因 | Count（全期間累計） | 影響戦略 |
|---|---|---|
| rnb_usdjpy: direction_filter | 297 | rnb_usdjpy |
| daytrade_eurgbp: hedge_block | 175 | daytrade_eurgbp |
| daytrade_gbpusd: hedge_block | 166 | daytrade_gbpusd |
| scalp系: r2_shadow_demoted_cell | 148+82+82+63+61=436 | scalp全般 |

→ **scalp系のr2_shadow_demoted_cellによる集計436件**が最大の機会喪失源。シャドー追跡による本番スキップが支配的。

---

## 4. 東京との比較

| 指標 | 東京セッション（推定） | ロンドンセッション |
|---|---|---|
| トレード数 | 0件（本日累計N=1のため） | 1件 |
| WR | — | 100% |
| PnL | +0.0 | +2.4 pips |
| USD_JPY レジーム | RANGING (ATR 59%) | RANGING継続 |
| EUR/GBP系 | VOLATILE傾向 | VOLATILE（ATR 62–72%） |

東京では発火ゼロ。ロンドン開始直後またはセッション中盤にvsg_jpy_reversalが唯一のシグナルを出力。JPY系はRANGINGからVOLATILEへの移行境界にあり、ロンドン序盤の方向性発現が捕捉できた可能性。

---

## 5. NYセッション準備

### ATR/レジーム変化予測
- **EUR系・GBP系（VOLATILE継続）**: ATR%ile 62–72%圏でロンドン終値を引き継ぐため、NYオープン（UTC 13:00–）でボラティリティ縮小局面に入るリスクあり。ただし米指標（週次ベース）次第でスパイクあり。
- **USD_JPY（RANGING）**: SMA20 Slope +0.00350と上向きバイアスあり。RANGING継続ならブレイクアウト系は不利。
- **全通貨でSMA20 Slopeが弱いマイナス（EUR/GBP系）** → リバーサル系に有利な環境。

### 推奨戦略配分

| 優先度 | 戦略 | ペア | 根拠 |
|---|---|---|---|
| ◎ | vsg_jpy_reversal | EUR_JPY | 本日実績あり・VOLATILEレジーム継続・下方バイアス整合 |
| ○ | scalp系（shadow解除ペア限定） | EUR/GBP | VOLATILE環境はscalpに有利だが、shadow_blockが解除されなければ実質不可 |
| △ | daytrade_eur / daytrade_gbpusd | EUR_USD / GBP_USD | hedge_blockとrecent_emitが多発中→自然発火待ち |
| ✗ | rnb_usdjpy | USD_JPY | direction_filter 297件=構造的に発火困難、RANGINGレジームとも不整合 |

### OANDA転送率への注意
現在の**Live Rate 4%（2/50）**は極めて低い。本番口座への実転送はshadow_tracking解除を待つ必要あり。NYセッションでの新規シグナルもskip優勢が続く見込み。

**→ 積極的な追加アクションは不要。「待機しながらvsg_jpy_reversalの追加発火を観察」が最適。**

---

## 6. 本日暫定結果（東京+ロンドン累計）

| 指標 | 値 |
|---|---|
| 本日累計トレード数 | **1件** |
| 累計WR | **100.0%** |
| 累計PnL | **+2.4 pips** |
| OANDA NAV | 286,272.78 |
| OANDA Open Trades | 1件（継続中の可能性） |

---

## 7. クオンツ見解

### 最重要シグナル（1点）

**「1日1件・Live Rate 4%」という構造は、現在のシステムが事実上デモ専用稼働状態であることを示している。**

本日ロンドンセッションで唯一発火したvsg_jpy_reversal（EUR_JPY, +2.4pips）は正当な結果だが、**N=1では統計的判断不能**（「データなし」水準）。より重大なのは、OANDA転送率4%・shadow_tracking 18件という数字であり、**本番口座へのフローが設計上制限されている状態が継続**していること。24モード稼働・436件超のscalp shadow demotedブロックという巨大な機会損失と合わせると、**システムはシグナル生成能力よりもフィルタリング・シャドー追跡が過剰支配している局面**にある。NYセッションで追加のvsg_jpy_reversalシグナルが発火してN≥5程度の累積データが得られれば、この戦略が構造的に機能しているかどうかの最初の判断材料となる。現時点では「待機継続」が唯一合理的な判断。
