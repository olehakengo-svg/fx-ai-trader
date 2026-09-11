# Post-London Report: 2026-09-11

## Analyst Report
# Post-London Report — 2026-09-11 (JST 01:00)

---

## 1. ロンドンセッション結果

| 指標 | 値 |
|---|---|
| トレード数 (N) | **1** |
| WR | **100.0%** |
| PnL | **+31.1 pips** |
| 戦略 | usdjpy_carry_dip_accumulator |
| ペア | USD_JPY |

---

## 2. What Worked

| 戦略 | ペア | PnL | 成功要因 |
|---|---|---|---|
| usdjpy_carry_dip_accumulator | USD_JPY | **+31.1p** | USD/JPY（ATR%ile 78%・VOLATILE）環境下でキャリーディップ戦略がOANDA SL/TP正常執行、スプレッド0.8pの低摩擦条件でフル利確達成。 |

---

## 3. What Didn't Work

**失敗トレードは存在しない**（N=1、全件WIN）。

ただし「機会損失」として記録すべき事象：

- **block_count累積が依然高水準** — `scalp:r2_shadow_demoted_cell`(854件)・`daytrade_eur:hedge_block`(716件)・`daytrade:hedge_block`(522件)が上位を占め、複数の有望シグナルがエントリーに到達できていない可能性がある。
- **daytrade_1h系・scalp_xau・scalp_eurjpy** は全モードON/OFFながらトレード数ゼロ。

---

## 4. 東京との比較

本データには東京セッション（UTC 00:00–07:00）の分離集計が存在しないため、**本日累計 N=1 がロンドン1件のみ**と判断される。

| 項目 | 東京 | ロンドン |
|---|---|---|
| N | **0**（推定） | **1** |
| WR | — | 100.0% |
| PnL | 0 | +31.1p |
| レジーム | VOLATILE（継続） | VOLATILE（継続） |
| 主要動意 | ほぼなし | USD/JPYが方向性を持った動き |

VOLATILE環境（USD/JPY ATR 78%ile）が東京クローズ後も継続し、ロンドン早期に`carry_dip_accumulator`がシグナルを捉えた構図。東京ではシグナル未発生でN=0が示す通り、同レジームでも**エントリー条件のタイミング感度**が顕在化している。

---

## 5. NYセッション準備

### レジーム・ATR変化予測

| ペア | 現状 | NY移行での変化予測 |
|---|---|---|
| USD_JPY | VOLATILE（78%ile）SMA20下向き | **米国CPI/PPI系指標次第で更にATR拡大リスク**。キャリー系の逆回転に注意 |
| EUR_JPY | VOLATILE（76%ile）SMA20下向き | 下降傾向継続、JPY買いバイアスが支配的 |
| GBP_JPY | VOLATILE（76%ile）SMA20下向き | 同上、ロンドンフィックス後のポジション整理フェーズ |
| EUR_USD | RANGING（38%ile）SMA20上向き | NYで方向感の出にくい値動きが継続する可能性大 |
| GBP_USD | RANGING（34%ile）SMA20横ばい | 同上、スキャルプには不向き |

**レジーム総評**: JPY系3ペアがVOLATILE、USD/EUR・GBP系がRANGING。NY時間はJPYレジームの継続が主シナリオだが、**SMA20が全JPYペアで下向き**＝JPY強含み継続リスクに留意。

### 推奨戦略配分

| 推奨度 | 戦略 | ペア | 根拠 |
|---|---|---|---|
| ◎ 継続監視 | usdjpy_carry_dip_accumulator | USD_JPY | 本日唯一の機能確認済み戦略、VOLATILE環境適合 |
| △ 条件付き | daytrade系 | EUR_JPY / GBP_JPY | VOLATILE適合だが`hedge_block`が高頻度発生中 — ブロック解消次第 |
| ✕ | scalp系（EUR/GBP） | EUR_USD / GBP_USD | RANGINGかつ`r2_shadow_demoted_cell`ブロック多発 — エッジ薄い |

### NYセッションに関する総合判断

> **積極的な新規ポジション追加より、carry_dip_accumulatorの次シグナルを待つ「選択的スタンス」を推奨。**
> USD/JPYのSMA20が-0.00720と強い下向きを示しており、BUYサイドのcarry戦略は逆風方向への転換点に接近している可能性。N=1では判断不能だが、**連続ロングへのバイアスには注意が必要**。

---

## 6. 本日暫定結果

| 指標 | 値 |
|---|---|
| 総トレード数 | **1** |
| WR | **100.0%** |
| 累計PnL | **+31.1 pips** |
| OANDA NAV | ¥275,676 |
| Open Trades | 0（全決済済み） |

---

## 7. クオンツ見解

### 最重要シグナル：「N=1の勝利」より「N=0の沈黙」を問題視せよ

本日ロンドンセッションの実態は**「1戦略のみ機能、残26モード全てN=0」**という極めて偏った活動分布である。

`r2_shadow_demoted_cell`（scalp系合計1,990件超）と`hedge_block`（daytrade系合計1,810件超）が上位ブロック要因を占め、システムは大量のシグナルを**受信しながらもエントリーを出力できていない**状態にある。+31.1pipsは歓迎すべき結果だが、**本日のPnLはシステム能力の断面ではなく、唯一通過できた1シグナルの偶然産物**として解釈すべきだ。

**推奨アクション（判断のみ）**:
1. `r2_shadow_demoted_cell`ブロックの対象セルがなぜ降格しているかを確認し、**復権要件**（N蓄積状況）を把握すること。
2. `hedge_block`が集中するdaytrade_eur・daytrade_gbpusdのヘッジ条件が現在のレジームと整合しているか評価すること。
3. OANDA転送率4%（50件中2件LIVE）は許容範囲内だが、**shadow_trackingで20件が停滞**している点はshadow戦略のLIVE昇格要件（N≥30・EV≥1.0）の進捗確認を急ぐべきシグナルである。
