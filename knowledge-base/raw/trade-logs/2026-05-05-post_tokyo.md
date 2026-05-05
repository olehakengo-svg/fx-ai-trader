# Post-Tokyo Report: 2026-05-05

## Analyst Report
# Post-Tokyo Report — 2026-05-05 08:19 UTC (JST 15:19)

---

## 1. 東京セッション結果

| 指標 | 値 |
|---|---|
| セッション内トレード数 | **0件** |
| PnL | — |
| WR | — |

**東京セッション: トレードなし**

本日累計ではN=1、WR=0%、PnL=**-7.4 pips**（セッション外の1件、詳細不明）。

---

## 2. What Worked

**該当なし** — 東京セッション中に約定トレードは存在しない。

---

## 3. What Didn't Work

**該当なし** — ただし、-7.4 pipsの1件（本日累計）が唯一の記録。N=1のため統計的評価不可。参考値として記録にとどめる。

---

## 4. 戦略調整判断

**NO — パラメータ変更不要**

根拠：
- Cutoff後のトレードがN=1（本日のみ）のため、いかなる戦略も統計的判断基準（N≥10「傾向」、N≥30「判断可能」）に達していない
- 東京セッション0件は「戦略の問題」ではなく、後述のブロック構造と流動性起因と判断

---

## 5. ロンドンセッション準備

### ATR/レジーム変化予測

| ペア | 現レジーム | ATR%ile | ロンドン開始時の予測 |
|---|---|---|---|
| EUR_JPY | VOLATILE | 72% | ボラ継続、スプレッド拡張リスク大 |
| GBP_JPY | VOLATILE | 55% | ロンドン参入でボラ上昇余地あり |
| GBP_USD | TRENDING_UP | 41% | トレンドフォロー系に有利 |
| EUR_USD | RANGING | 38% | Scalp系は機能しやすいが伸びが限定的 |
| USD_JPY | VOLATILE | 71% | ヘッジブロック多発中、注意 |

**レジームサマリー**: JPY絡みペア（EUR_JPY・USD_JPY）は高ATRかつヘッジブロック多発。GBP_USDはTRENDING_UPかつBT実績のある戦略（`gbp-deep-pullback`・`trendline-sweep`）が配置済みで最も条件が整う。

### 推奨戦略配分

| 優先度 | 戦略 | ペア | 根拠 |
|---|---|---|---|
| 🔴 最優先 | `gbp-deep-pullback` | GBP_USD | ELITE_LIVE・BT EV=+1.064・TRENDING_UP整合 |
| 🔴 最優先 | `trendline-sweep` | GBP_USD | ELITE_LIVE・BT EV=+0.599・同上 |
| 🟡 注目 | `post-news-vol` | GBP_USD | BT EV=+1.762と最高水準・ロンドン経済指標後に有効 |
| 🟡 注目 | `trendline-sweep` | EUR_USD | BT EV=+0.927・RANGING中はフェイクブレイクに注意 |
| 🟢 待機 | `doji-breakout` | GBP_USD | BT EV=+0.724・センチネル蓄積中 |
| ⚪ 見送り | JPY絡み全般 | EUR_JPY, USD_JPY | hedge_block多発（計77件）＋高ATR = コスト超過リスク |

**ロンドン経済指標**（本日確認推奨）: 欧州指標リリース前後は`post-news-vol`のシグナル発火条件に注意。

### DD防御モード確認

> KB記載: **DD=28.01%、DD防御0.2x発動中**

ロット縮小0.2xが継続適用中。高EVセットアップでも約定サイズが抑制されるため、**勝ち逃し**より**損失限定**を優先する局面。積極介入は不要。

---

## 6. ブロック構造の主因分析（補足）

| 主要ブロック理由 | 件数 | 含意 |
|---|---|---|
| `daytrade_eurjpy:hedge_block` | 58 | EUR_JPY逆方向ポジ保有が多い＝通貨リスク集中の証拠 |
| `rnb_usdjpy:direction_filter` | 58 | USD_JPY方向感不一致、VOLATILE環境下で当然 |
| `daytrade_eurgbp:recent_emit` | 46 | 短時間内重複シグナル抑制（正常機能） |
| `daytrade_gbpusd:recent_emit` | 45 | 同上 |
| `scalp_5m_gbp:hedge_block` | 45 | GBP_JPY/GBP_USD間のリスク相殺機能が頻繁に発火 |

→ `recent_emit`系ブロックは**システム正常動作**。`hedge_block`多発は**ポジション方向集中**のシグナル。OANDA転送率0%（50件全SKIP）はshadow_trackingによる正常なデモ運用継続。

---

## クオンツ見解

### 最重要シグナル（1点）

**ヘッジブロック多発 = 方向性集中リスクの可視化**

`hedge_block`計188件（eurjpy:58 + scalp_5m_gbp:45 + daytrade_eur:26 + daytrade:19 + scalp_5m_eur:40）は、複数戦略が同一通貨ブロック（JPY売り・GBP買い）に集中している証拠である。これ自体はリスク管理が機能している証拠だが、**裏を返せば、システムが特定方向にバイアスを持つシグナルを大量生成している**ことを意味する。現在のVOLATILEレジーム（EUR_JPY ATR=72%、USD_JPY=71%）下では、この方向集中が一度外れたときの損失が通常より大きくなる点に注意が必要。

**推奨アクション**: OANDA転送再開（shadow卒業）の判断はN≥30到達まで保留を継続。現時点で昇格候補に達したCutoff後戦略は存在しない。ロンドンセッションでは`gbp-deep-pullback`と`trendline-sweep`のGBP_USD軸に絞り、DD防御0.2x継続のもと損失の絶対値管理を優先せよ。
