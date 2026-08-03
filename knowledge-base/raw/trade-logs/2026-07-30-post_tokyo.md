# Post-Tokyo Report: 2026-07-30

## Analyst Report
# Post-Tokyo Session Report — 2026-07-30 08:35 UTC

---

## 1. 東京セッション結果

**東京セッション: トレードなし**

| 指標 | 値 |
|---|---|
| PnL | 0 pips |
| トレード数 | 0 |
| WR | N/A |

UTC 00:00–06:00 の範囲でエグゼキューションはゼロ。全27モードがRunning（daytrade_xau / scalp_xau / scalp_eurjpy を除く）であるにもかかわらず、1件も約定に至らなかった。

---

## 2. What Worked

**該当トレードなし。**

---

## 3. What Didn't Work

**該当トレードなし。**

ただし「失敗」の代わりに**エグゼキューション阻害要因**を以下に整理する：

| 阻害要因 | 件数 | 主な戦略 |
|---|---|---|
| hedge_block | 42 | gbpusd / eurjpy / gbpjpy / daytrade |
| direction_filter | 16 | rnb_usdjpy |
| r2_shadow_demoted_cell | 16 | 1h_usdchf / scalp / scalp_5m |
| order_bar_dedup | 14 | 1h_nzdjpy / eur / gbpjpy |
| same_price_5pip | 1 | daytrade |

- **hedge_block が東京セッション最大の約定阻止要因（42件/TOP15合計=89件の47%）**。GBP_USD（17件）・EUR_JPY（13件）・GBP_JPY（12件）の3ペアに集中しており、これらペアでヘッジ方向のシグナルが逆張り的に連発したことを示す。
- **direction_filter（rnb_usdjpy 16件）** は、USD_JPY ATR%ile=67%・SMA Slope+0.00248 というRANGING-Upper Bandの環境下でRnBロジックが方向を絞り込めていない状態を反映。
- **r2_shadow_demoted_cell（16件）** はshadow tracking中のセルが本番昇格未完のまま信号を出し続けていることを示す。

---

## 4. 戦略調整判断

**NO — パラメータ変更不要**

根拠：
- 本日セッションN=0 のため統計的判断の基礎なし。
- block_countsはすべてシステム設計内の保護ロジック（hedge_block、direction_filter、shadow demote）が正常作動した結果であり、誤作動ではない。
- OANDA転送率0%は「約定ゼロ」の結果であって、Bridge自体の異常ではない（shadow_tracking 19件 + agg_kelly=-0.343<0 の1件のみ）。
- **agg_kelly=-0.343<0 によるブロック1件**はKelly gate正常動作。DD防御モード（100.01%バリア後保守運用）と整合的。

---

## 5. ロンドンセッション準備（UTC 07:00–12:00）

### ATR/レジーム変化予測

| ペア | 現在ATR%ile | 東京→ロンドン予測 |
|---|---|---|
| GBP_USD | 64% | ロンドンOpen直後に出来高急増→ATR一時的上昇リスク。RANGING上限に近く**ブレイクアウト偽シグナル注意** |
| USD_JPY | 67% | 同様。67%はRANGING高水準で方向感なし→rnb_usdjpy方向確定難しい |
| GBP_JPY | 55% | 中程度。hedge_blockが東京で多発しており、ロンドン初動でも継続の可能性 |
| EUR_USD | 52% | ほぼ中央値。scalp系には最もニュートラルな環境 |
| EUR_JPY | 40% | 相対的に低ATR→daytrade系シグナル閾値を超えにくい可能性 |

全5ペアが**RANGING**。SMAスロープが正負混在（EUR_USDのみ微小マイナス）であり、トレンドフォロー系よりレンジ系が構造的に有利な地合いだが、**ATR%ile 64-67%（GBP_USD/USD_JPY）はRANGING内でのボラ高状態**で偽ブレイクアウトが増えやすい。

### 推奨戦略配分

**NO ACTION推奨**

| 理由 | 詳細 |
|---|---|
| DD防御発動中 | NAV=279,013 / DD=100.01%バリア突破後の保守モード。新規積極展開はリスク管理方針と非整合 |
| データ蓄積不足 | Cutoff後の有効N蓄積途上。昇格基準（N≥30, EV≥1.0）に達している戦略の現況確認要 |
| hedge_block多発 | GBP_USD/EUR_JPY/GBP_JPYでロンドンOpenまでヘッジ方向シグナルが継続する可能性が高く、手動介入の必要なし |
| shadow tracking継続 | OANDA Bridge側で19件がshadow_trackingのためSKIP。デモ結果がLiveに反映されない間は、システム設計通りの評価継続が優先 |

仮にシステムが自律シグナルを出す場合は、**EUR_USD scalp系（ATR%ile=52%、中央値レンジ）** が最もノイズが少ない環境。ただしr2_shadow_demoted_cell（scalp 6件 / scalp_5m 6件）のブロックが継続している点は留意。

---

## 6. クオンツ見解

### 最重要シグナル

**hedge_blockの集中（42件/89件の47%）はシグナル供給量の問題ではなく、方向の問題である。**

東京セッション全体でエグゼキューションゼロという結果は「シグナルが出ていない」のではなく「シグナルが出ても約定ブロックされている」構造を示す。特にGBP_USD・EUR_JPY・GBP_JPYの3ペアはRANGING環境下で**互いに相関した方向シグナルを逆方向に連発**しており、hedge_blockがシステムの過剰ポジションリスクを正当に防いでいる。これは**システムが正常に機能しているシグナル**であって、修正を要する異常ではない。

DD防御モード（100.01%バリア突破後）＋agg_kelly=-0.343<0の状態で約定ゼロは**設計通りの保守的アウトカム**。ロンドンセッションに向けても積極的なポジション追加の根拠は現時点でない。N蓄積とshadow_trackingの昇格判定を粛々と待つフェーズと判断する。
