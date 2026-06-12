# Post-London Report: 2026-06-12

## Analyst Report
# ロンドンセッション総括レポート — 2026-06-12 Post-London (JST 01:00)

---

## 1. ロンドンセッション結果

| 指標 | 値 |
|---|---|
| **PnL** | **-9.6 pips** |
| **トレード数** | **16件** |
| **勝率** | **75.0% (12W / 4L)** |
| **平均勝ちトレード** | +1.72 pips |
| **平均負けトレード** | -7.30 pips |
| **損益比（実測）** | 約 1:4.24（逆方向）|

**概評**: 勝率75%にもかかわらずPnLがマイナスという典型的な「非対称損失」セッション。少数の大損失（-15.4, -7.4, -5.6）が多数の小勝利を食い潰している。

---

## 2. What Worked ✅

| 戦略 | ペア | PnL | 成功要因 |
|---|---|---|---|
| **zz_pivot_v60_sr** | EUR_USD | +3.6 pips (2件) | EUR_USDのRANGINGレジーム（ATR47%ile）がピボット反転精度を支え、2連続OANDA_SL_TP達成。|
| **wick_imbalance_reversion** | GBP_USD | +2.3 pips (1件) | RANGING環境下での価格行動パターンが機能、スプレッド1.3pipsを吸収しEV+2.30。|
| **vix_carry_unwind** | USD_JPY | +4.9 pips (5W) | USD_JPYのRANGINGかつ低ATR（29%ile）環境でSELL方向7連打のうち5勝。キャリー巻き戻しロジックが方向性フィルターとして有効機能。|

---

## 3. What Didn't Work ❌

| 戦略 | ペア | PnL | 失敗要因 |
|---|---|---|---|
| **trendline_sweep / GBP_USD** | GBP_USD | **-11.7 pips（4件合計）** | 1件の-15.4pips SL_HITが致命的。GBP_USDがRANGING（ATR40%ile）にもかかわらずトレンドライン突破を狙う戦略を展開→レジームミスマッチ。EV=-2.35。|
| **ema200_trend_reversal / USD_JPY** | USD_JPY | **-5.6 pips（1件）** | USD_JPY ATR29%ile（低ボラ）でのSELL→SL_HIT。EV=-5.60は単発でも構造的に危険な水準。BTデータでUSD_JPY EV=-0.183と既に負のシグナルあり。|
| **vix_carry_unwind（損失2件）** | USD_JPY | **-8.2 pips** | -7.4pips SL_HITが1件。全体5勝2敗で方向性は合っているが、SL設定が非対称損失を生んでいる（+1.8平均勝ち vs -4.1平均負け）。|

---

## 4. 東京との比較

> ※本日累計17件・PnL -15.2pipsに対してロンドン16件・-9.6pipsであることから、**東京セッションは約1件・-5.6pips**と推定される。

| 指標 | 東京（推定） | ロンドン | 変化 |
|---|---|---|---|
| **トレード数** | ~1件 | 16件 | ▲大幅増（ロンドン流動性） |
| **PnL** | ~-5.6 pips | -9.6 pips | 悪化 |
| **WR** | 不明（サンプル過小） | 75.0% | ― |
| **主因** | 単発損失（推定） | 非対称SL損失（-15.4, -7.4, -5.6） | 構造同一 |
| **レジーム** | ロンドン開始前（低流動性） | RANGING支配（4ペア中4） | 継続RANGING |

**観察**: レジームは東京→ロンドン通じてRANGING基調を維持。ロンドンで活動量が急増したが、大型SL_HITがセッション収益を圧迫するパターンが両セッション共通。

---

## 5. NYセッション準備

### レジーム変化予測（ロンドン→NY移行）

| ペア | 現在レジーム | NY移行予測 | 根拠 |
|---|---|---|---|
| USD_JPY | RANGING (ATR29%ile) | **RANGING継続** | ATR最低水準、NY序盤のUSデータ次第で一時的変動の可能性あり |
| EUR_USD | RANGING (ATR47%ile) | **RANGING/微Volatile化** | SMAスロープ-0.00421で下落バイアス、NYオープンで方向感が出やすい |
| GBP_USD | RANGING (ATR40%ile) | **RANGING** | スロープ-0.00323、流動性はNYで増加するが中央値ATR帯 |
| GBP_JPY | RANGING (ATR55%ile) | **要注意（Volatile化リスク）** | ATR55%ile + SMAスロープ+0.00105、ロンドン→NY移行で最もBreakoutリスク高 |
| EUR_JPY | VOLATILE (ATR52%ile) | **VOLATILE継続** | 唯一のVOLATILEレジーム、NYでの円動向次第で加速の可能性 |

### 推奨戦略配分

| 優先度 | 戦略 | ペア | 理由 |
|---|---|---|---|
| **推奨継続** | zz_pivot_v60_sr | EUR_USD | 本日2/2勝、RANGING環境と親和性高、EV+1.80実測 |
| **推奨継続** | wick_imbalance_reversion | GBP_USD | RANGING×価格行動系、本日EV+2.30 |
| **条件付き継続** | vix_carry_unwind | USD_JPY | 方向性は機能中、ただしSL幅の非対称性に注意 |
| **⚠️ 要警戒** | trendline_sweep | GBP_USD | RANGINGレジームでの運用継続はレジームミスマッチ、本日EV=-2.35 |
| **🚫 NO ACTION推奨** | ema200_trend_reversal | USD_JPY | ATR29%ile低ボラ環境での逆張り→本日-5.6pips SL_HIT、BT EV=-0.183と整合 |

> **NY全体方針**: 大型損失の主因はトレンドフォロー系戦略のRANGING環境投入。NYオープン（UTC 13:00以降）でUSD関連ボラが上昇しなければ、**zz_pivot_v60_sr・wick_imbalance_reversionのピボット/リバーサル系を軸に絞り込むことが合理的**。GBP_JPYのATR55%ilが突破するようであれば別途判断。

---

## 6. 本日暫定結果（東京+ロンドン累計）

| 指標 | 値 |
|---|---|
| **総トレード数** | **17件** |
| **WR** | **70.6%** |
| **累計PnL** | **-15.2 pips** |
| **OANDA転送率** | 12%（50件中6件SENT） |
| **Open Trades** | 0件 |
| **NAV** | 291,882.36 |

---

## 7. クオンツ見解

### 🔴 最重要シグナル：「高勝率・負PnL」構造の固定化

本日累計WR70.6%・PnL-15.2pipsという数値は、**勝率が高いほど安心できない**パターンの典型例として警戒レベルに達している。

本日の損失の約82%（-12.4 pips相当）は**trendline_sweep/GBP_USD**と**ema200_trend_reversal/USD_JPY**の計2戦略・3件のSL_HITに集中している。両戦略の共通点は「トレンド追随型ロジック」を「4ペア全RANGING環境」に投
