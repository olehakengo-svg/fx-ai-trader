# 高N負け組の adverse-selection 診断 & counter-stop-hunt 既存資産評価

**Date**: 2026-04-23
**Author**: Claude (quant mode)
**Window**: post-cutoff 2026-04-08 〜 2026-04-23 (16 days)
**Data**: `/api/demo/trades` (N=2313 CLOSED, shadow=2057 / live=256)
**Trigger**: ユーザー質問「shadow N 多いのになぜ負けるか / 逆指値狩り逆手 戦略検討」
**Parent**: [[liquidity-sweep]], [[trendline-sweep]], [[osler-2003]], [[mfe-zero-analysis]]

---

## 0. TL;DR

1. **高N負け組は全て retail 教科書パターン** → Kyle(1985) λ / Osler(2003) SL cluster cascade で数学的に説明可能。MFE=0 率 30-67% が adverse selection の実測証拠
2. **Counter-stop-hunt 戦略は既に 3 系統実装済**。`trendline_sweep` (ELITE_LIVE, shadow +13.78p/trade GBP_USD BUY), `liquidity_sweep` (SENTINEL N=2 未評価), `ema200_trend_reversal` (shadow USD_JPY 両側正 EV)
3. **新規 counter-stop-hunt 戦略の追加は不要**。既存 `liquidity_sweep` の N 蓄積と、高N負け組の **pair×side cell レベル pruning** が ROI 最大
4. **Simpson's paradox 多発**: aggregate 負けでも pair×side で正セルあり (engulfing_bb × USD_JPY × SELL 等)

---

## 1. shadow N 多いのに負ける理由 — 数学的 3 層

### 1.1 第1層: Kyle (1985) λ adverse selection

価格形成 `p = μ + λ·(x_I + x_U)`。retail が **同一 entry signal** で相関注文を出すと、LP は x_U を観測可能 → fills = worst fill。教科書パターン fires = 逆選択シグナル化。

**実測**: 10 戦略すべて MFE=0 率 30-67% (bb_rsi 44%, engulfing 43%, sr_fib 51%, macdh 38%)。エントリー方向そのものが問題。

### 1.2 第2層: Osler (2003) SL clustering cascade

SL 注文がラウンドナンバー/Fib/S-R/BB 外縁にクラスタリング → LP sweep → cascade。教科書パターン entry 水準 = SL cluster の裏側。

### 1.3 第3層: 同一 microstructure の 2 峰性

| 入り方 | EV 結果 |
|---|---|
| 素直に逆張り (bb_rsi, fib_reversal, sr_fib_confluence) | -0.91 〜 -5.14p |
| Sweep 後 reclaim (trendline_sweep, liquidity_sweep 設計) | +3.55 〜 +13.78p |

**同じ価格構造で retail 側と informed 側の EV が反転**。

---

## 2. 観測: 高 N 負け組の avg PnL / MFE=0 率

post-cutoff shadow+live aggregate:

| 戦略 | N | WR | avg | MFE=0率 | 判定 |
|---|--:|--:|--:|--:|---|
| ema_trend_scalp | 489 | 20% | -0.92p | 41% | 教科書 trend scalp |
| bb_rsi_reversion | 303 | 34% | -1.71p | 44% | 教科書逆張り |
| sr_channel_reversal | 208 | 24% | -0.90p | 46% | S/R range |
| stoch_trend_pullback | 171 | 22% | -0.06p | 35% | flat だが MFE 悪 |
| engulfing_bb | 166 | 27% | -2.38p | 43% | candle + BB |
| fib_reversal | 148 | 28% | -0.91p | 38% | Fib retracement |
| vol_surge_detector | 113 | 35% | -0.32p | 31% | volatility surge |
| bb_squeeze_breakout | 99 | 23% | -0.18p | 42% | squeeze breakout |
| sr_fib_confluence | 75 | 21% | -5.14p | 51% | S/R + Fib |
| macdh_reversal | 46 | 13% | -8.92p | 38% | 最悪 avg |

**全 10 戦略で MFE=0 率 ≥30%** = Kyle λ の実測証拠。

---

## 3. pair × side × (live|shadow) 分解 — Simpson's paradox 発掘

### 3.1 Aggregate 負けでも cell 正の例（選別可能）

| 戦略 | 正 cell | 判定 |
|---|---|---|
| bb_rsi_reversion | EUR_USD × BUY LIVE N=12 +1.37p / SHADOW N=8 +2.99p | unresolved task 既追跡 |
| bb_squeeze_breakout | USD_JPY × SELL SHADOW N=28 +1.83p | PAIR_PROMOTED は USD_JPY だが方向不問 — SELL 限定化検討 |
| engulfing_bb | USD_JPY × SELL SHADOW N=41 +0.23p / GBP_USD × BUY N=11 +1.81p | 方向非対称 |
| vol_surge_detector | USD_JPY × SELL SHADOW N=25 +1.36p / EUR_USD × BUY LIVE N=5 +1.44p | |
| sr_channel_reversal | GBP_USD × SELL SHADOW N=23 +0.24p | 唯一の非 JPY 正セル |
| dt_bb_rsi_mr | GBP_USD × BUY N=14 +1.49p / EUR_USD × BUY N=7 +2.06p (aggregate +0.65p) | **FORCE_DEMOTED 誤判の可能性** |

### 3.2 完全切断候補（aggregate + 全 cell 負け）

| 戦略 | 最悪 cell |
|---|---|
| macdh_reversal | USD_JPY × BUY N=16 WR=6% avg=-4.77p MFE=0 40% |
| sr_fib_confluence | EUR_JPY × BUY N=16 WR=6% avg=-8.30p |
| v_reversal (UNIVERSAL_SENTINEL) | USD_JPY × BUY SHADOW N=12 avg=-2.93p — BT 未検証で shadow 明確に負け |
| ema_trend_scalp × GBP_USD | BUY N=54 WR=11% avg=-2.64p / SELL N=36 WR=14% avg=-2.48p |

### 3.3 `bb_rsi_reversion × USD_JPY` 最大セルの詳細

- BUY LIVE N=49 WR=43% avg=-0.08p **MFE=0=57%**
- SELL LIVE N=50 WR=40% avg=+0.03p **MFE=0=53%**

**USD_JPY は live でほぼ flat + MFE=0 過半**。「flat = 放置」ではなく「高い adverse selection 下で生き残っている」= 信号強度を上げれば正に転じる可能性あり、ただし単純 fire 継続は ROI ゼロ。

---

## 4. Counter-Stop-Hunt 系 既存資産の評価

### 4.1 `trendline_sweep` (ELITE_LIVE)

| cell | N | WR | avg |
|---|--:|--:|--:|
| GBP_USD × BUY SHADOW | 4 | 75% | **+13.78p** |
| GBP_USD × SELL SHADOW | 3 | 0% | -6.50p |

- BT: GBP_USD EV=+0.599 / EUR_USD EV=+0.927
- **Live N=0 (30d window)** — 最近 fire してない（問題）
- Shadow GBP_USD BUY は BT と整合

**所見**: ELITE_LIVE 位置付けだが fire 頻度が低すぎる。fire 条件 review 推奨。

### 4.2 `ema200_trend_reversal` (PAIR_PROMOTED USD_JPY)

| cell | N | WR | avg |
|---|--:|--:|--:|
| USD_JPY × BUY SHADOW | 7 | 57% | +4.61p |
| USD_JPY × SELL SHADOW | 6 | 67% | **+8.47p** |
| EUR_JPY × BUY SHADOW | 5 | 0% | -11.06p ← 毒 |
| GBP_JPY × BUY SHADOW | 2 | 50% | +13.00p |
| USD_JPY × BUY LIVE | 2 | 0% | -8.45p |

- BT: EUR_USD +0.410 / USD_JPY -0.183
- Shadow aggregate +1.17p / live small-N 負け逆転

**所見**: BT と shadow が USD_JPY で乖離（BT 負 → shadow 正）。Live N=2 で判断不能だが **EUR_JPY cell は毒**。次 session で pair 絞り込み検討。

### 4.3 `liquidity_sweep` (UNIVERSAL_SENTINEL)

- Live N=1 / Shadow N=1 → **実質未評価**
- 30d window 内で fire が極少
- 740 行実装済 (v8.2, ADX<25 / wick_ratio≥0.60 / next-bar)

**所見**: fire 頻度低の原因調査が先。RANGE regime 検出が厳しすぎる可能性。

### 4.4 `orb_trap` (FORCE_DEMOTED)

| cell | N | WR | avg |
|---|--:|--:|--:|
| GBP_USD × BUY SHADOW | 3 | 67% | +9.77p |
| EUR_USD × BUY SHADOW | 2 | 0% | -5.40p |

Shadow aggregate +3.70p (N=5 小)。**FORCE_DEMOTED で shadow 正** は再評価候補だが N<20 で Gate 未達。

### 4.5 `inducement_ob` / `wick_imbalance_reversion` (counter-stop-hunt 意図だが死亡)

- inducement_ob: GBP_USD × BUY SHADOW N=2 avg=-6.80p (既 FORCE_DEMOTED)
- wick_imbalance_reversion: GBP_USD/EUR_USD BUY shadow N=2 each avg -4.90/-10.60p

**教訓**: 「stop-hunt reverse」意図だけでは勝てない。**Wick ratio 数量化 + next-bar confirmation + regime gate** 全て必要 (liquidity_sweep の設計要素)。

---

## 5. クオンツ判断 — 次アクション優先度

### 5.1 Implementation 保留（1 日データ禁止原則）

- ❌ 新規 counter-stop-hunt 戦略の追加 (既存 3 系統で十分)
- ❌ `ema_trend_scalp` 逆シグナル BT — 魅力的だが現セッション Scope 外

### 5.2 分析継続 / モニター

- `liquidity_sweep` fire 頻度調査 — 90d window で live+shadow N を確認、30d で N 極少なら Regime gate 再検証
- `trendline_sweep` live N=0 問題 — fire 条件 review
- `ema200_trend_reversal × EUR_JPY` cell の毒性 (N=5 avg -11.06p) — PAIR_DEMOTED 候補

### 5.3 unresolved task との連動

- `bb_rsi_reversion × EUR_USD × BUY` 監視継続（現 LIVE N=12 +1.37p / SHADOW N=8 +2.99p — 両チャネル正）
- `bb_squeeze_breakout × USD_JPY × SELL` 監視（SHADOW N=28 +1.83p）— 現 PAIR_PROMOTED は方向非限定、SELL 限定化検討
- `dt_bb_rsi_mr` recovery 候補 — aggregate shadow +0.65p (FORCE_DEMOTED から再評価の根拠)

### 5.4 KB 更新

- このノート = 高N負け組の diagnostic stamp
- `[[trendline-sweep]]` / `[[liquidity-sweep]]` へ本分析のリンク追加推奨
- [[index]] UNRESOLVED への追記候補:
  - [ ] `trendline_sweep` live N=0 原因調査 (30d window)
  - [ ] `liquidity_sweep` fire 頻度 90d 調査

---

## 6. 「逆指値狩りを逆手」に対するクオンツ見解

**結論**: 仮説は学術的 (Osler/Kyle) にもデータ (MFE=0 + trendline_sweep 実績) にも **強く支持**。ただし:

1. **既に 3 系統実装済**。追加より既存評価完了が先
2. **`inducement_ob` / `wick_imbalance_reversion` は死亡** — 単なる「sweep reverse」意図だけでは負ける。定義の定量化が必須
3. **月利 100% roadmap への寄与は限定的**。`trendline_sweep` 1 戦略で年間 +80-120p 程度。データ蓄積フェーズでは bb_rsi/session_time_bias の **cell 単位選別の方が ROI 大**
4. **現 DD=25.9% defensive mode** では新戦略 bring-up のリスク非対称 (lesson: 唯一の正エッジ戦略に対する実験は最悪エッジ消滅)

## 7. 関連

- [[osler-2003]] — SL clustering 理論
- [[kyle-1985]] — λ adverse selection
- [[liquidity-sweep]] — counter-stop-hunt 実装
- [[trendline-sweep]] — counter-stop-hunt ELITE_LIVE
- [[mfe-zero-analysis]] — 先行 MFE=0 分析
- [[lesson-reactive-changes]] — 1 日データで実装しない原則
- [[conditional-edge-estimand-2026-04-17]] — pair×side cell 選別の先行事例
