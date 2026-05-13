# Post-Tokyo Report: 2026-05-13

## Analyst Report
# Post-Tokyo Session Report｜2026-05-13 08:51 UTC

---

## 1. 東京セッション結果

**東京セッション: トレードなし**

| 指標 | 値 |
|---|---|
| PnL | 0.0 pips |
| トレード数 | 0 |
| 勝率 | N/A |
| OANDAアクティブ | True |
| NAV | 300,090.97 |
| Open Trades | 0 |

東京セッション（UTC 00:00–06:00）において、デモ・本番ともにエントリー成立ゼロ。

---

## 2. What Worked

**該当なし（トレードゼロのため）**

---

## 3. What Didn't Work

**直接の損失トレードなし**。ただし「機会損失」の観点で主因を分析する。

### ブロック要因ランキング（本日主因）

| 順位 | 要因 | 件数 | 主な戦略 |
|---|---|---|---|
| 1 | `hedge_block` | 46件 | DT系全般（EUR/GBP/JPY） |
| 2 | `direction_filter` | 9件 | rnb_usdjpy |
| 3 | `r2_shadow_demoted_cell` | 10件 | scalp_5m_gbp, scalp_5m, scalp |
| 4 | `recent_emit` | 2件 | daytrade |
| 5 | `same_price_5pip` | 2件 | daytrade |

**主因: `hedge_block`が圧倒的（全ブロックの約66%）。**  
EUR_JPY・GBP_JPYが `VOLATILE（ATR%ile 83%/79%）` で急激なボラティリティを示しており、ヘッジ検知がほぼ全DT系で発動。オープンポジションがないにもかかわらずブロックが連発しているのは、市場の方向性が頻繁に反転し、仮想ポジション管理上の「ヘッジ判定」が過敏に反応している可能性を示す。

---

## 4. 戦略調整判断

**→ NO（パラメータ変更なし）**

**根拠:**
- Fidelity Cutoff（2026-04-08）以降のCleanデータN=0（本日セッション）であり、統計的判断の基礎がない
- ブロックは設計通りの防御動作であり、`VOLATILE`レジーム下では正常挙動
- `xs_momentum GBP_USD` はLive N=3、`vix_carry_unwind USD_JPY` はLive N=4 — いずれもN<10のため「データなし」扱い（判断不可）
- DD=28.01%のDD防御0.2xモード継続中 → リスクパラメータ触媒は禁止水域

---

## 5. ロンドンセッション準備

### ATR/レジーム変化予測

| ペア | 現在レジーム | ロンドン移行予測 | 注意点 |
|---|---|---|---|
| EUR_JPY | VOLATILE (83%ile) | 継続/さらに拡大リスク | SMA slope -0.0027（下降トレンド継続） |
| GBP_JPY | VOLATILE (79%ile) | ロンドン開始でスパイク確率高 | 最もヘッジブロック発生リスク大 |
| GBP_USD | RANGING (53%ile) | 欧州指標次第でVOLATILEへ転換可能性 | slope +0.0021（やや上昇バイアス） |
| EUR_USD | RANGING (34%ile) | Ranging継続の可能性高い | 低ボラ環境、scalp向き |
| USD_JPY | RANGING (78%ile) | 表面上Ranging、実態はJPY不安定 | slope -0.0032（円高圧力） |

### 推奨戦略配分

**EUR_USD（RANGING低ボラ）**  
→ `scalp` / `scalp_eur` / `session-time-bias` — スプレッド収益狙いに最適環境

**GBP_USD（RANGING中程度）**  
→ `scalp_5m_gbp`（ただし`r2_shadow_demoted_cell`3件確認→shadow品質監視継続）  
→ `doji-breakout GBP_USD` — BT EV=+0.724は参考値として有望

**EUR_JPY・GBP_JPY（VOLATILE）**  
→ **DT系は`hedge_block`連発が予想されるため消極的推奨**  
→ `vol-momentum-scalp EUR_JPY` / `vsg-jpy-reversal` はsentinel段階のためN蓄積優先

**USD_JPY**  
→ `rnb_usdjpy` は`direction_filter`が9件発動 — 現在の方向性不明瞭環境では待機が合理的

### Sentinel N蓄積進捗（N=30まで）

| 戦略 | 現在N(Live) | 残り | 判断可能まで |
|---|---|---|---|
| vix_carry_unwind | 4 | 26件 | 遠い |
| xs_momentum (GBP_USD) | 3 | 27件 | 遠い |

**全Sentinel戦略: N=30到達まで判断保留。強制介入禁止。**

---

## 6. クオンツ見解

### 最重要シグナル

**`hedge_block`の異常集中（全ブロックの66%）がシステム全体の機会損失の主因。**

EUR_JPY（ATR 83%ile）・GBP_JPY（ATR 79%ile）の高ボラ環境が、DT系6戦略で計46件のヘッジ検知を誘発している。これは**レジームと戦略の構造的ミスマッチ**を示す。VOLATILEレジームでDT系をフル稼働させると、トレードゼロのまま監視リソースだけ消費するという「空振りコスト」が発生している。

OANDA転送率4%（2/50件）・shadow_trackingブロック20件も合わせると、**本日のシステム出力の大半は防御動作**であり、これ自体は設計通りだが、ロンドン移行後にEUR_USDとGBP_USDのRANGINGが継続するならば、DT系ではなく**スキャルプ系への資源集中**が合理的判断となる。DD=28.01%の現状でポジティブEV積み上げのためにはレジームと戦略のマッチングを意識した待機戦略が優先事項。

---
*Report generated: 2026-05-13 08:51 UTC | Data Fidelity Cutoff: 2026-04-08T00:00:00Z | DD防御0.2xモード適用中*
