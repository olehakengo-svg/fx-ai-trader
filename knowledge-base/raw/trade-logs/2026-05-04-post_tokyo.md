# Post-Tokyo Report: 2026-05-04

## Analyst Report
# 東京セッション総括レポート（2026-05-04 JST 15:00）

---

## 1. 東京セッション結果

| 項目 | 値 |
|---|---|
| セッション時間 | UTC 00:00–06:00 |
| トレード数 | **N=3** |
| 勝率 | **66.7%** |
| 純PnL | **+1.1 pips** |
| 対象ペア | USD_JPY のみ |

> ⚠️ N=3 は統計的に「データなし」水準。数値は参考値として扱う。

---

## 2. What Worked

| 戦略 | ペア | 方向 | PnL | 成功要因 |
|---|---|---|---|---|
| **streak_reversal** | USD_JPY | SELL | **+0.7 pips** | OANDA_SL_TP決済、スプレッド0.8pipsと低摩擦環境でUSD/JPY SELL側の逆張りが短期的に機能 |
| **bb_rsi_reversion** | USD_JPY | SELL | **+6.4 pips** | TP_HIT、USD/JPY VOLATILE レジーム下でバンド端からの回帰が高EV条件を満たした |

---

## 3. What Didn't Work

| 戦略 | ペア | 方向 | PnL | 失敗要因 |
|---|---|---|---|---|
| **bb_rsi_reversion** | USD_JPY | SELL | **−6.0 pips** | SL_HIT、同戦略・同方向の連続エントリーにより1発目のTP利益（+6.4）を2発目のSL（−6.0）がほぼ相殺、ネット+0.4pipsに留まる |

> 注目点：bb_rsi_reversion の2トレードを合算すると EV=+0.20（N=2）。個別の損益振れ幅（±6 pips）に対しネット収益が微小であり、1トレードあたりのリスクリワード効率が低い状態。

---

## 4. 戦略調整判断

**判断: NO（コード変更なし）**

| 理由 | 詳細 |
|---|---|
| N不足 | N=3は統計的閾値（N=30）の10%。調整の根拠なし |
| EV方向 | bb_rsi_reversion EV=+0.20、streak_reversal EV=+0.70、どちらも正値 |
| レジーム整合 | USD_JPY VOLATILE (ATR%ile=67%)は逆張り系（bb_rsi、streak）と方向整合 |
| vix_carry_unwind 乖離 | BT WR=67.3% vs Live WR=25.0%（N=4）は要継続観察だが、N=4で降格判断には早い |

---

## 5. ロンドンセッション準備（UTC 07:00–）

### レジーム変化予測

| ペア | 現在レジーム | ロンドン移行予測 | 影響 |
|---|---|---|---|
| USD_JPY | VOLATILE (67%ile) | 持続見込み（欧州参入でボラ追加） | bb_rsi_reversion・streak_reversal 継続有効 |
| GBP_USD | TRENDING_UP (40%ile) | トレンドフォロー強化の可能性 | gbp-deep-pullback・doji-breakout 有利 |
| EUR_USD | RANGING (36%ile) | ロンドン初動でブレイク試行の可能性 | squeeze_release_momentum・bb-squeeze-breakout 注目 |
| EUR_JPY | VOLATILE (66%ile) | 継続VOLATILE | ボラ系戦略有利、ただし hedge_block 多発注意 |
| GBP_JPY | VOLATILE (55%ile) | 継続 | max_open/recent_emit ブロックに注意（TOP15に daytrade_gbpjpy が2件） |

### 推奨戦略配分

```
優先度 HIGH:
  - gbp_deep_pullback / GBP_USD（ELITE_LIVE、TRENDING_UP レジーム適合）
  - post_news_vol / GBP_USD・EUR_USD（PAIR_PROMOTED、EV=+1.762/+0.817 最高水準）
  - trendline_sweep / EUR_USD・GBP_USD（ELITE_LIVE、ロンドン初動ブレイクに適合）

優先度 MEDIUM:
  - bb_rsi_reversion / USD_JPY（本日プラス確認、VOLATILE継続）
  - squeeze_release_momentum / EUR_USD（RANGING→ブレイク移行狙い）

優先度 LOW / 監視のみ:
  - vix_carry_unwind / USD_JPY（Live WR=25%、BT比-75pp乖離中、N=4で判断保留）
  - rnb_usdjpy（direction_filter ブロック39件、シグナル生成効率が低い）
```

### ブロック要因への注意

- **scalp:max_open（47件）・scalp_eur:max_open（46件）**: ロンドン初動の出来高増加で改善する可能性あるが、ポジション上限が引き続きボトルネック
- **hedge_block 多発（scalp_5m=34、daytrade_eurjpy=33）**: 同方向ポジション集中→通貨リスク集中リスク。ロンドンで方向感が出ればブロック解消の可能性

### OANDA転送率

| 指標 | 値 | 評価 |
|---|---|---|
| Live Rate | **8%（4/50）** | 極めて低い |
| shadow_tracking ブロック | 20件 | 主因：SENTINELステージ戦略が本番昇格待ち |

> OANDA転送率8%は構造的に正常（大半がSENTINEL収集フェーズ）。異常ではないが、Kelly Half到達（月利594%目標）には本番転送比率の改善が必須条件。

---

## 6. クオンツ見解

### 最重要シグナル

**vix_carry_unwind の Live/BT 乖離（ΔWR=−75pp）は現時点で最大の警戒シグナルだが、N=4での降格判断は時期尚早。**

BT（N=0→バックテストデータ実質なし）に対してLive WR=25%（N=4、うち1勝3敗）という乖離は、戦略の構造的崩壊である可能性と、単純なN不足によるランダム性の両方が考えられる。**N=10到達まで観察継続が妥当。N=10でWR≤30%が続く場合に降格検討。**

本日東京セッションの本質は「N=3・PnL+1.1pips」という水準ではなく、**bb_rsi_reversion が VOLATILE レジーム下で±6pipsの損益を相殺してネット微益に留まった**点にある。勝率66.7%でEV正値であることは確認できるが、**1トレードあたりのリスク（6pips）に対してネット収益（+0.4pips）の効率が低い**——これはサンプル数が増えた際に注視すべき構造的コストの可能性。

**推奨アクション（判断のみ）:**
1. `vix_carry_unwind / USD_JPY`: N=10到達まで観察。降格判断保留
2. `post_news_vol / GBP_USD`: EV=+1.762はポートフォリオ最高水準。ロンドン初動の経済指標タイミングを最優先監視対象に
3. OANDA転送率8%: 現フェーズでは許容。ただしSENTINEL戦略のN=30到達加速が月利目標達成の最短経路
