# Post-Tokyo Report: 2026-07-24

## Analyst Report
# Post-Tokyo Report — 2026-07-24 08:33 UTC (JST 15:33)

---

## 1. 東京セッション結果

| 項目 | 値 |
|---|---|
| セッション (UTC 00:00-06:00) | **トレードなし** |
| PnL | — |
| トレード数 | 0 |
| WR | — |

東京セッション全体でエントリーゼロ。シグナル発生はあったが、後述のブロック機構が全件遮断。

---

## 2. What Worked

**該当なし** — 本セッション内に執行済みトレードが存在しないため評価対象なし。

---

## 3. What Didn't Work

**該当なし** — 同上。ただしブロックログに以下の注目パターンを確認：

| 主因ブロック | 件数 | 判断 |
|---|---|---|
| `scalp_eur: r2_shadow_demoted_cell` | 11件 | Sentinel機構が正常作動しデモトレードを遮断（設計通り） |
| `scalp_5m_eur: r2_shadow_demoted_cell` | 5件 | 同上 |
| `daytrade_eur: order_bar_dedup` | 4件 | 同一バー内重複注文防止（設計通り） |
| `scalp_5m_gbp: order_bar_dedup` | 4件 | 同上 |
| `daytrade_eurgbp: hedge_block` | 3件 | ヘッジ方向ブロック（設計通り） |
| `rnb_usdjpy: direction_filter` | 3件 | 方向フィルター作動（設計通り） |

→ **全ブロックが設計通り**。システム異常なし。

---

## 4. 戦略調整判断

**NO** — コード変更は今回スコープ外。また本セッションでの実トレードがN=0のため、統計的根拠に基づくパラメータ変更判断は不可。

---

## 5. ロンドンセッション準備

### レジーム現況 → ロンドン移行予測

| ペア | 現レジーム | ATR%ile | SMA20 Slope | ロンドン移行予測 |
|---|---|---|---|---|
| EUR/JPY | RANGING | 34% | +0.00230 | ボラ低位継続。Scalp系エッジ薄 |
| EUR/USD | RANGING | 36% | +0.00013 | 同上。方向感なし |
| GBP/JPY | **TRENDING_UP** | **60%** | +0.00553 | ロンドン勢参入でトレンド加速可能性あり。DT系有利 |
| GBP/USD | RANGING | 60% | +0.00337 | ATR%ile高いがSlopeはまだ弱く移行期 |
| USD/JPY | RANGING | 67% | +0.00217 | ATR高くてもトレンドなし — ノイズ環境 |

### 推奨戦略配分

| 戦略 | ペア | 判断 | 根拠 |
|---|---|---|---|
| `daytrade_gbpjpy` | GBP/JPY | **優先監視** | TRENDING_UP×ATR60%ile — DT系が最も条件合致 |
| `daytrade_gbpusd` | GBP/USD | 次点監視 | ATR高いがRANGING — ブレイクout確認後 |
| `scalp_eur` / `scalp_5m_eur` | EUR/USD, EUR/JPY | **待機推奨** | r2_shadow_demoted_cellブロック多発中。レジームも低ATR。エッジ薄 |
| `rnb_usdjpy` | USD/JPY | **待機推奨** | direction_filterが3件遮断。RANGINGでRnBエッジも不明確 |

### OANDA転送率

- **Live Rate: 0%（50件全件SKIP）**
- Block理由: 全件 `shadow_tracking`（= Sentinel追跡中のデモ専用状態）
- **→ 本番口座への影響ゼロ。DD防御態勢維持中（設計通り）**

**NAV: 279,009 JPY / Open Trades: 0** — ポジションクリーン。

---

## 6. クオンツ見解

### 最重要シグナル（1点）

**「scalp_EUR系のshadow_demoted_cellブロックが東京セッションで16件（11+5）発生 — これはEUR系Scalpが本番昇格から最も遠い位置にいることを明示している」**

本セッションの最大観察事項は「何も起きなかった」ではなく、**EUR系Scalp戦略が繰り返しSentinelにブロックされ続けている**という構造的事実だ。r2_shadow_demoted_cellブロックは「一度デモレベルに降格されたセルがまだ回復しておらず、本番昇格要件（N≥30 & EV≥1.0）に達していない」ことを意味する。

本番転送率0%はDD防御の正常動作だが、**シグナルが出ているにもかかわらず全件ブロックされている状態が続く限り、段階目標M1（月次符号転換）の達成機会そのものが失われる**。

GBP/JPYのTRENDING_UP単独上昇は現状のロンドン移行において唯一の構造的優位点だが、`daytrade_gbpjpy`のN蓄積状況がデータ上確認できないため、今の判断は「監視優先・静観」が妥当。**今週のロンドンセッションでGBP/JPY DT系がN蓄積を進められるかどうか**が、昇格パイプライン回復の実質的チェックポイントとなる。
