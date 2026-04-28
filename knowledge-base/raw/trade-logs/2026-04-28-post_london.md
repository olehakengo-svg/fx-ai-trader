# Post-London Report: 2026-04-28

## Analyst Report
# ロンドンセッション総括レポート
**2026-04-28 | UTC 07:00–16:00 | JST 01:00 Post-London**

---

## 1. ロンドンセッション結果

| 指標 | 値 |
|---|---|
| トレード数（N） | 1 |
| 勝率（WR） | 100.0%（1/1） |
| PnL | +1.3 pips |
| 純益評価 | 統計的意味なし（N=1） |

ロンドンセッション中に発火したのは **session_time_bias / GBP_USD / SELL** の1件のみ。
結果はWIN（SL_HIT経由）でPnL +1.3 pips。スプレッドも1.3 pipsと記録されており、
**実質的な摩擦調整EVはほぼゼロ**（gross pips = spread と等しい）。

---

## 2. What Worked

| 戦略 | ペア | 方向 | PnL | 成功要因 |
|---|---|---|---|---|
| session_time_bias | GBP_USD | SELL | +1.3 pips | ELITE_LIVE戦略がGBP_USD RANGING環境でSELLバイアスに乗り、SL到達前に目標到達（SL_HIT = 相手側がhit = 利確） |

> **補足**: Reason欄の "SL_HIT" はシステム側のSL管理ロジック（相手ポジションのSL到達＝利確）として解釈。

---

## 3. What Didn't Work

**失敗トレード: なし**（N=1のためロンドン単体では未達なし）

ただし本日累計（東京+ロンドン）ベースでは：

| 本日累計N | WR | PnL |
|---|---|---|
| 10 | 30.0% | **−8.3 pips** |

→ ロンドン前（東京セッション）で**9件 / WR約22% / PnL −9.6 pips**相当が発生していた計算。
東京セッションで複数の損失トレードが集積しており、ロンドンの+1.3は焼け石に水。

---

## 4. 東京セッションとの比較

| 比較軸 | 東京（推計） | ロンドン |
|---|---|---|
| N | ≈9件 | 1件 |
| WR | ≈22% | 100%（N=1、参考値） |
| PnL | ≈−9.6 pips | +1.3 pips |
| レジーム | RANGING（ATR低め） | RANGING継続 |
| 主な阻害要因 | max_open多発・recent_emit多発 | max_open継続、block多数 |

**構造的観察**: レジームは東京→ロンドン通じて全ペアRANGING継続。
ATR%ile（33〜50%ile）は中程度で、方向性トレンドが乏しく、
DT系（daytrade_gbpusd/eurgbp/eur等）の`recent_emit`ブロックが多発したことが発火件数の激減を招いた。

---

## 5. NYセッション準備（UTC 16:00–21:00）

### ATR/レジーム変化予測

- 現在全ペアRANGING（ATR%ile 33〜50%）
- NYオープン（UTC 13:00–16:00）での**USD_JPY方向性が最注目**：SMA20 Slope = −0.00019とほぼフラット、RANGING継続見込み
- GBP_USD・EUR_USD はSlope正（微弱上昇バイアス）→ NY指標次第でブレイクの可能性あり
- **ただし本日は特段の高インパクト指標なし前提**では、RANGING継続が最有力シナリオ

### 推奨戦略配分

| 戦略 | ペア | 根拠 |
|---|---|---|
| session_time_bias | GBP_USD, USD_JPY | ELITE_LIVE。RANGING環境でも機能実績あり。本日唯一のWIN |
| trendline_sweep | EUR_USD, GBP_USD | ELITE_LIVE。RANGING→軽微トレンド転換に感応 |
| post_news_vol | GBP_USD | PAIR_PROMOTED。BT EV=+1.762。NYオープン付近のボラ拡大局面限定 |

> **⚠️ NO ACTION推奨条件**: max_openブロックが継続している場合（現在scalp/scalp_eur系でブロック多発中）、追加エントリーを焦る必要はない。blockが解消されるまで待機が合理的。

### 見送り推奨

| 戦略 | 理由 |
|---|---|
| rnb_usdjpy | direction_filterで121件ブロック → フィルタが市場を拒否している状態 |
| daytrade_eurgbp | session_pairで45件ブロック → セッション外として排除されている |

---

## 6. 本日暫定結果（東京＋ロンドン累計）

| 指標 | 値 |
|---|---|
| 累計N | 10 |
| WR | 30.0% |
| 累計PnL | **−8.3 pips** |
| OANDA転送率 | 0%（全50件SKIP） |
| OANDAオープントレード | 0 |

---

## 7. クオンツ見解

### 🔴 最重要シグナル（1点）

**本日のWR=30%・PnL=−8.3 pipsは、ロンドンの+1.3が誤魔化しているが、東京セッションの構造的不調を示している。**

block_countsを見ると`rnb_usdjpy:direction_filter=121`が突出しており、
これはdirection_filterが現在のUSD_JPY（SMA Slope=−0.00019、ほぼゼロ）を
「方向性なし＝発火不可」と正しく判断している証拠。システムはフィルタ通り機能しているが、
**方向性のないレジームで発火した9件（東京）がWR22%程度に留まった原因は、
RANGING環境でのシグナル品質低下**にある。

本日はN=10・Cutoff後データとして蓄積はされているが、
**単日判断は禁物**（N<30）。ただし、RANGING継続中にDT系が30%未満のWRを記録している傾向は
**蓄積データが増えるにつれて統計的に問題化するリスクあり**。
NYセッションで無理に枚数を増やすより、session_time_biasとtrendline_sweep（ELITE_LIVE）への
絞り込みが現時点の最適解。
