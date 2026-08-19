# Post-Tokyo Report: 2026-08-19

## Analyst Report
# Post-Tokyo Report｜2026-08-19 JST 15:00 (UTC 06:00)

---

## 1. 東京セッション結果

| 項目 | 値 |
|---|---|
| トレード数 (N) | 1 |
| WR | 0.0% (0/1) |
| PnL | **−11.7 pips** |
| 活動戦略 | usdjpy_carry_dip_accumulator |

N=1のため統計的意味はなし。**参考値として扱う**。

---

## 2. What Worked

**なし** — 当該セッションに勝ちトレードは存在しない。

---

## 3. What Didn't Work

| 戦略 | ペア | 方向 | PnL | 失敗要因 |
|---|---|---|---|---|
| usdjpy_carry_dip_accumulator | USD_JPY | BUY | **−11.7 pips (SL_HIT)** | USD/JPY ATR%ile=90%（高ボラ）局面でのDIP買いエントリーがトレンド継続下降に押し切られてSL到達 |

- スプレッド0.8pipは許容範囲内であり、執行品質自体に問題はない
- **SMA20 Slope = −0.00478（全ペア中最大の下降傾き）**の環境下でBUY（carry dip accumulation）は逆風であり、レジーム適合性に疑問が残る

---

## 4. 戦略調整判断

**→ NO（コード変更なし）**

理由：
- N=1は統計的根拠なし。単一SL_HITで調整判断を下すことは統計的に不適切
- ただし**レジーム観察事項**として記録：USD/JPYはATR90%ile×下降SMAであり、carry dip accumulator（BUY bias）との相性が構造的に問われる局面。N≥10蓄積後に再評価要

---

## 5. ロンドンセッション準備（UTC 07:00〜）

### ATR／レジーム変化予測

| ペア | 現状レジーム | ATR%ile | 東京→ロンドン変化予測 |
|---|---|---|---|
| EUR_JPY | RANGING | **90%** | 高ボラ継続。ロンドン勢の参入でトレンド発生リスク↑ |
| GBP_JPY | RANGING | **84%** | 同上。GBP絡みはロンドンopen特有の急動意注意 |
| USD_JPY | RANGING | **90%** | 下降バイアス継続の可能性。BUY戦略は引き続き逆風 |
| EUR_USD | RANGING | 41% | 低ボラ安定。スプレッド比較的良好 |
| GBP_USD | RANGING | 41% | 同上 |

### ブロック状況の確認

本日TOP blockカウントの主因：

| ブロック要因 | 件数 | 解釈 |
|---|---|---|
| daytrade_eurjpy: order_bar_dedup | 10 | EUR/JPY高ボラ環境で同バー重複シグナルが頻発 — 正常動作 |
| rnb_usdjpy: direction_filter | 10 | USD/JPY下降レジームでRnBのBUYシグナルを方向フィルターが遮断 — **フィルターが適切に機能している** |
| daytrade: score_gate | 9 | スコア閾値未達でエントリー見送り — 品質フィルター正常 |
| scalp: r2_shadow_demoted_cell | 9 | シャドウ降格セル回避 — 正常 |
| daytrade_gbpjpy: hedge_block | 6 | GBP/JPY高ボラ下でのヘッジブロック — 正常 |

**全主要ブロック要因は正常防御動作**。異常なブロックパターンは検出されない。

### OANDA転送率の解釈

| 指標 | 値 | 解釈 |
|---|---|---|
| Live Rate | **4%** (2/50) | shadow_tracking=18件が主因。デモ先行フェーズとして正常 |
| Bridge: filled | 1/1 | sent分は100%フィル済み — 執行品質問題なし |
| NAV | 277,947 JPY | DD防御モード維持中 |

### ロンドンセッション推奨戦略配分

**→ NO ACTION推奨（積極的拡張は見送り）**

**根拠：**

1. **DD防御モード継続中**（NAV/Balanceが一致＝ポジションなし、防御態勢維持）
2. **EUR/JPY・USD/JPY・GBP/JPYがATR80-90%ile** — 高ボラRANGINGはスキャルプ系の損切り幅拡大リスクあり
3. **shadow_tracking 18件がOANDA転送を抑制** — これは設計通り。デモ検証継続が優先
4. **rnb_usdjpyのdirection_filterが10件作動** — システムが自律的に不適合シグナルを遮断済み

唯一許容できる活動：
- `scalp_5m`系（EUR_USD・GBP_USD、ATR41%ileの低ボラペア）は spread_guard が通れば自然エントリー可
- ただし現在すべて`r2_shadow_demoted_cell`ブロックが発生しており、システム判断を尊重

---

## 6. クオンツ見解

### 最重要シグナル（1点）

**rnb_usdjpy の direction_filter 10件作動は「異常」ではなく「正解」**

USD/JPY SMA20 Slope = −0.00478（全ペア最大下降）× ATR90%ile という環境は、carry dip accumulator・RnBいずれのBUY戦略にとっても構造的逆風局面。システムが10件のシグナルを方向フィルターで遮断したことは損失回避として機能している。本日唯一エントリーした `usdjpy_carry_dip_accumulator` の −11.7pip SL_HITは、**フィルターをくぐり抜けたシグナルが同じレジーム問題で負けた**という構図であり、注視すべきシグナルである。

**推奨：** USD/JPY関連戦略全般について、SMA20 Slope がフラット〜プラス転換するまでBUY方向エントリーの自然減少を許容する。N≥10蓄積後に `usdjpy_carry_dip_accumulator` のレジーム別EV分解を確認すること。コード変更不要——現状はシステムが自律防御中。
