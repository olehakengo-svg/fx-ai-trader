# Post-Tokyo Report: 2026-04-22

## Analyst Report
# Post-Tokyo Report — 2026-04-22 07:58 UTC (JST 15:58)

---

## 1. 東京セッション結果

| 項目 | 値 |
|---|---|
| セッション (UTC 00:00–06:00) | **トレードなし** |
| PnL | ¥0 |
| トレード数 | 0 |
| 勝率 | N/A |

東京セッション全体を通じてエントリーはゼロ。ブロック理由の構成がその主因を説明している（後述）。

---

## 2. What Worked

**該当なし**（トレード未発生）

---

## 3. What Didn't Work

**エントリー機会が全面的にブロック** — 以下の4要因が重複して機能した：

| ブロック理由 | 件数 | 主因分析 |
|---|---|---|
| `scalp:spread_guard` | 15 | スプレッドが閾値（Scalp=30%）を超過。東京クローズ前後の流動性低下帯が直撃 |
| `daytrade:score_gate` | 11 | シグナルスコアが通過基準未達。RANGING環境でのトレンドスコア低下 |
| `daytrade_eurgbp:session_pair` | 10 | EUR/GBP東京時間はセッションフィルタ設計上ブロック対象（正常動作） |
| `rnb_usdjpy:direction_filter` | 10 | USD/JPYのRNBが方向フィルタで遮断。USD_JPY SMAスロープ +0.00032（ほぼフラット）と整合 |
| `scalp_5m:sl_cluster` | 8 | SLクラスター検知によるリスク回避（正常動作） |

> **構造的解釈**: spread_guard 15件 + score_gate 11件がボトルネックの二大要因。RANGING相場でスコアが閾値を割り込む設計挙動であり、誤作動ではなく **フィルタが正常機能した結果ゼロトレード** となった。

---

## 4. 戦略調整判断

**→ NO（パラメータ変更不要）**

根拠：
- 全ブロックは設計済みフィルタの正常動作（spread_guard/score_gate/sl_cluster）
- 全通貨ペアが **RANGING × ATR%ile 34–52%**（中程度ボラティリティ） — トレンド系戦略がスコアを取りにくい環境として整合
- Fidelity Cutoff後の累積Nが事実上ゼロ（本日セッション）であり、統計的根拠なしにパラメータ変更を行うリスクが調整メリットを上回る

---

## 5. ロンドンセッション準備（UTC 08:00–）

### ATR/レジーム変化予測

| ペア | 現在レジーム | ATR%ile | ロンドン予測 |
|---|---|---|---|
| EUR_USD | RANGING | 52% | ロンドンオープン (08:00 UTC) でATR拡大の可能性。score_gate通過率が回復する可能性あり |
| GBP_USD | RANGING | 50% | 同上。gbp-deep-pullback / post-news-vol が活性化の好機 |
| EUR_JPY | RANGING | 36% | ATR低水準。VWAP Mean Reversionには好環境だが、DT系は引き続きスコア難 |
| GBP_JPY | RANGING | 34% | 最低ATR%ile — 方向性シグナルに乏しい。積極的期待薄 |
| USD_JPY | RANGING | 40% | SMAスロープほぼゼロ。RNB direction_filterが引き続き機能する可能性高 |

### 推奨戦略配分

| 優先度 | 戦略 | ペア | 根拠 |
|---|---|---|---|
| **高** | `post-news-vol` | EUR_USD, GBP_USD | BT EV+0.817/+1.762と突出。ロンドンオープン直後のVol拡大局面に直結 |
| **高** | `gbp-deep-pullback` | GBP_USD | ELITE_LIVE EV+1.064。GBP_USD ATR50%でプルバック深度が出やすい |
| **中** | `trendline-sweep` | EUR_USD, GBP_USD | EV+0.927/+0.599。ただしRANGINGでは偽ブレイクリスクあり。score_gate通過依存 |
| **中** | `session-time-bias` | USD_JPY | EV+0.580 WR79%。ロンドン移行後のJPYクロス方向付けに期待 |
| **低** | `rnb_usdjpy` | USD_JPY | direction_filterが東京で10件遮断。ロンドンでもフラットSMAが続く場合は期待薄 |
| **待機** | `daytrade_eurgbp` | EUR_GBP | session_pairフィルタがロンドンで解除されるか確認後に判断 |

### 「何もしない」判定

**NO ACTION推奨ではない** — ロンドンオープン時のVol拡大を利用できる戦略（post-news-vol, gbp-deep-pullback）は稼働維持が妥当。ただし **score_gate/spread_guard が東京同様に機能し続ける場合はシステムが自律的に見送る** ため、追加的な手動介入は不要。

---

## 6. クオンツ見解

### 最重要シグナル

**OANDA転送率4%（50件中2件SENT）が示す構造的ギャップ**

全48件がSKIPされている主因は `shadow_tracking`（18件）であり、デモ→本番への昇格評価が進行中であることを示す。一方でFidelity Cutoff後の実トレードNはほぼゼロのまま蓄積されておらず、**昇格判断に必要なN=30への到達見通しが立っていない**。東京セッションのゼロトレードはフィルタの正常動作ではあるが、**クリーンデータ蓄積という最優先目標に対してほぼ進捗していない**点は構造的問題として認識すべきである。現在のRANGING×中程度ATR環境はロンドン移行で改善が見込まれるものの、本日の東京セッション結果は「戦略の問題ではなくレジーム問題」として記録・継続監視を推奨する。N蓄積進捗は **0/30（全戦略）** として次回以降のレポートで追跡が必要。
