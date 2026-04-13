# Post-Tokyo Report: 2026-04-13

## Analyst Report
# Post-Tokyo Session Report｜2026-04-13 JST 15:00

---

## 1. 東京セッション結果

| 指標 | 値 |
|---|---|
| セッション内PnL | **-13.4 pips** |
| トレード数 | **18件** |
| 勝率（WR） | **33.3%** |
| 活性ペア | USD_JPY のみ |

本日累計（36件）: PnL **-35.2 pips** / WR **30.6%**
XAU別枠（11件）: PnL **-1,496 pips**（XAUスケール：要注意）

---

## 2. What Worked

| 戦略 | ペア | PnL | 成功要因 |
|---|---|---|---|
| **trend_rebound** | USD_JPY | **+4.2 pips** | OANDA_SL_TP到達、東京後半の短期ディレクショナル動意を正確に捉えた1発 |
| **engulfing_bb** | USD_JPY | **+5.0 pips** | TP_HIT（エンゴルフィングシグナルがBBサポートと一致） |
| **bb_rsi_reversion** | USD_JPY | **+5.4 / +0.6 pips** | TP_HIT×1＋OANDA_SL_TP×1、平均回帰シグナルが東京RANGING環境に適合（セッション内EV+0.83は最良水準） |

---

## 3. What Didn't Work

| 戦略 | ペア | PnL | 失敗要因 |
|---|---|---|---|
| **sr_channel_reversal** | USD_JPY | **-12.5 pips（8件）** | WR25%・EV -1.56。SL_HIT×4、TIME_DECAY_EXIT×3が示す通り、レンジ内での逆張りエントリーがS/R水準を繰り返し割られ機能不全 |
| **vol_surge_detector** | USD_JPY | **-5.6 pips（2件）** | EV -2.80。東京レンジ環境（ATR%ile 38%）でのボラ方向性判断失敗、BREAKEVENとSL_HIT |
| **stoch_trend_pullback** | USD_JPY | **-3.0 pips（1件）** | N=1のため統計的評価不可（参考値）。OANDA_SL_TP到達でのフル損切り |

---

## 4. 戦略調整判断

**判断: NO（コード変更なし）**

ただし以下の**観察的アラート**を記録する：

| 戦略 | Cutoff後累計N | 本日セッションEV | 調整判断 |
|---|---|---|---|
| **sr_channel_reversal** | KB記載なし（N未追跡） | **-1.56** | ⚠️ N蓄積を至急確認。KB昇格基準（N≥30 & EV≥1.0）からは程遠く、降格基準（N≥30 & EV<-0.5）への該当可能性を追跡開始 |
| **bb_rsi_reversion** | KB: N=77、WR=36.4%、PnL=-42.2 | **+0.83（本日）** | 📌 本日は好調だが累計PnLは-42.2pipと構造的赤字。「本日の回復」を過大評価しない |
| **vol_surge_detector** | KB: N=11、WR=63.6%、PnL=+19.6 | **-2.80（本日）** | 📌 KBでは高WRだが本日完全失敗。N=11の不安定さを示す典型例 |

---

## 5. ロンドンセッション準備（UTC 07:00-）

### レジーム予測

| 観点 | 現状（東京）| ロンドン予測 |
|---|---|---|
| USD_JPY ATR%ile | 38%（RANGING） | EUR/GBP主体のフロー流入でボラ上昇期待。ただしSMA slope+0.00074は方向性弱い |
| EUR_USD | 53% RANGING、slope+0.00211 | ロンドン初動でモメンタム可能性あり |
| GBP_USD | 52% RANGING、slope≒0（-0.00006） | 方向性なし。FX主戦場になりにくい |
| 全体レジーム | 全5ペア RANGING | ロンドン前半はRANGING継続が基本シナリオ。ブレイク確認まで待機が合理的 |

### 推奨戦略配分

**NO ACTION推奨（積極展開なし）**

**根拠:**
1. **本日累計DD -35.2 pips**（WR30.6%）はDD防御閾値への接近を示唆。追い打ちリスク高
2. **全ペアRANGING**（ATR%ile 31-53%、いずれも高ボラでない）— vol_surge_detector・trend_reboundはボラ環境に依存するため優位性減退
3. **sr_channel_reversal（8件・EV -1.56）**がロンドンでも継続発火する場合、損失加速リスク
4. **XAU -1,496 pips（11件）**は別枠だが本日全体のリスク管理上、追加エクスポージャーは抑制が妥当
5. 唯一、**bb_rsi_reversion**はRANGING環境への適合性が本日確認されたが、累計N=77・WR=36.4%・PnL=-42.2の構造的赤字を踏まえると積極推奨には至らない

---

## 6. クオンツ見解

### 最重要シグナル

**sr_channel_reversal の緊急モニタリング開始を推奨する。**

本日東京セッションだけでN=8・EV=-1.56・WR=25%。KBにはこの戦略の Cutoff後累計N が明記されておらず、降格基準（N≥30 & EV<-0.5）の達否が不明のままシステムが最多発火戦略として動いている点が最大の構造的リスクである。

- SL_HIT×4とTIME_DECAY_EXIT×3の混在は「シグナル精度の問題」と「保有時間と市場構造のミスマッチ」が同時に起きていることを示す
- 全ペアRANGING環境下でS/R逆張り戦略が機能不全なのは偶然ではなく、レジーム感応性の問題として解釈すべき
- **今すぐすべきこと**: sr_channel_reversalのCutoff後累計NとEVをKBに登録し、N≥30達成時点で降格/継続の正式判断を行う。それまでは「観察下」として扱う

---
*Report generated: 2026-04-13 07:26 UTC | Analyst: Quant AI Senior*
