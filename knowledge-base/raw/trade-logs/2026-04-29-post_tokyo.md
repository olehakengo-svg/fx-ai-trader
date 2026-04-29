# Post-Tokyo Report: 2026-04-29

## Analyst Report
# Post-Tokyo Report｜2026-04-29 JST 15:00

---

## 1. 東京セッション結果

| 項目 | 値 |
|---|---|
| セッション時間 | UTC 00:00–06:00 |
| トレード数 (N) | 1 |
| WR | 0.0% (0/1) |
| PnL | **-3.4 pips** |
| 本日累計 PnL | -9.6 pips（N=3, WR=0.0%） |

> ⚠️ N=1は統計的意味なし。単発損失として記録するにとどめる。

---

## 2. What Worked

**該当なし。**
東京セッション内の勝ちトレードはゼロ。

---

## 3. What Didn't Work

| 戦略 | ペア | 方向 | PnL | 失敗要因 |
|---|---|---|---|---|
| bb_rsi_reversion | USD_JPY | BUY | **-3.4 pips** (SL_HIT) | USD/JPY が RANGING（ATR%ile=31%）かつ SMA20 Slope ≈ −0.00013 のフラット環境で買いエントリー → レンジ下限到達前にSLに触れた典型的な低ボラ誤発火 |

- スプレッド 0.8 pips は正常範囲（spread_guard 引っかかりなし）
- **bb_rsi_reversion** はKBに PAIR_PROMOTED / ELITE_LIVE のいずれにも未登録であることに留意

---

## 4. 戦略調整判断

**NO（コード変更なし）**

理由：
- N=1（本日累計N=3）では判断材料として不十分
- bb_rsi_reversion の累積クリーンデータ（Fidelity Cutoff後）が蓄積途上であり、EV算出不可
- レジームはRANGINGで全ペア統一されており、現時点でのパラメータ変更は雑音への過剰反応

---

## 5. ロンドンセッション準備（UTC 07:00–12:00）

### ATR/レジーム変化予測

| ペア | 現状 | ロンドン移行予測 |
|---|---|---|
| GBP_USD | RANGING, ATR%ile=31% | ロンドンオープンで流動性増加 → ATR一時拡大の可能性。ただしトレンド転換には材料不足 |
| EUR_USD | RANGING, ATR%ile=43% | 中程度のボラ。EUR系は4ペアでSMA20 Slope が全てプラス → 緩やかな EUR 強め地合い |
| GBP_JPY | RANGING, ATR%ile=34% | GBP系のロンドン流動性増加でレンジ拡大余地あり |
| EUR_JPY | RANGING, ATR%ile=34% | 同上。JPY側は USD_JPY Slope がフラット → JPY方向感なし |
| USD_JPY | RANGING, ATR%ile=31% | 最も方向感なし。bb_rsi_reversionの発火条件が再び揃いやすい環境 → 要注意 |

### 推奨戦略配分

| 優先度 | 戦略 | ペア | 根拠 |
|---|---|---|---|
| 高 | post_news_vol | EUR_USD, GBP_USD | BT EV +0.817 / +1.762、ロンドン経済指標時間帯と親和性高い |
| 高 | trendline_sweep | EUR_USD, GBP_USD | EV +0.927 / +0.599、ELITE_LIVE、ロンドンオープン初動に有効 |
| 中 | doji_breakout | GBP_USD | EV +0.724、RANGING→軽微ブレイクアウト検出に適合 |
| 低 | bb_rsi_reversion (USD_JPY) | — | 本日すでに損失。RANGING+フラット環境では追加発火を慎重に見る |

### 現在のシステム制約（重要）

- **OANDA Live Rate: 8%（50件中4件のみ転送）**
- Bridge Status: shadow_tracking で 20件 SKIP
- **DD=28.01% → DD防御0.2xスケールアクティブ**
- rnb_usdjpy:direction_filter が 50件ブロック（東京全体で最多）→ RNB戦略の方向フィルターが機能中（RANGING環境では適切な防御）

→ ロンドン移行においても **ポジションサイズは 0.2x 維持が前提**。NAV=436,358 / Balance=436,382 の乖離が小さく Open Trade 1件のみ → 過大ポジションリスクは現時点で低い。

---

## 6. クオンツ見解

---

### 🔴 最重要シグナル

**OANDA Live Rate 8%（50件中4件）の極端な低さが本番稼働の実効性を損なっている。**

本日のブロック TOP は `rnb_usdjpy:direction_filter`（50件）と `recent_emit`・`same_price` 系で占められており、シグナル生成はあるが大半がデモ留まり。Shadow_tracking による 20件 SKIP が加わり、実際に OANDA に届くシグナルがほぼゼロの状態。DD 防御 0.2x 下では「実弾なし」に近い運用が続いており、**クリーンデータ蓄積と Kelly Half 到達の双方が停滞リスクを抱えている。**

### 構造的観察

- **全ペア RANGING（ATR%ile 31–43%）**：東京セッションはレンジ系戦略の誤発火環境。bb_rsi_reversion の SL_HIT はレジームとの不一致が主因であり、戦略固有の問題ではなくマーケット環境の問題として解釈すべき。
- **Block の主因が `recent_emit` 系**：複数の daytrade 戦略で同一時間帯に信号が密集 → フィルタリングが正常に機能している証左だが、同時にシグナル品質（分散）に疑問が残る。
- **bb_rsi_reversion は KB 未登録**：EV 評価なし・BT データなし の状態で本番発火している。Fidelity Cutoff 後 N が蓄積されるまで EV は不明。

### 推奨アクション

1. **ロンドンセッション: `post_news_vol`（EUR_USD, GBP_USD）と `trendline_sweep` を優先監視** — どちらも ELITE/PAIR_PROMOTED かつ BT EV ≥ +0.6 で、ロンドンオープンのボラ拡大と親和性が高い。
2. **bb_rsi_reversion の N 蓄積モニタリング継続** — KB 未登録・EV 未確定のまま繰り返し発火している場合、Sentinel N=30 到達後に EV を算出し昇格/降格判断を行うべき。現時点では「観察対象」として扱う。
3. **DD 28% → DD 防御継続維持（変更不要）** — NAV は安定だが、月利 100% 目標達成には Kelly Half 移行が必須。Cutoff 後クリーンデータ蓄積を最優先とし、OANDA Live Rate 改善の判断は次回レビューサイクルへ持ち越す。

---
*Report generated: 2026-04-29 08:26 UTC | Fidelity Cutoff適用済 | N=1（東京セッション）*
