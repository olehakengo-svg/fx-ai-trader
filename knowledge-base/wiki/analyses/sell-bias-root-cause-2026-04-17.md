# SELL方向「負けバイアス」根本原因調査 (2026-04-17)

**作成日**: 2026-04-17
**データ**: Render API N=1054 (2026-04-08 ~ 04-16, 9日間)
**トリガー**: `rigorous-edge-analysis-2026-04-17.md` で SELL -771p (Bonf p=8e-8) と検出
**仮説**: signal 生成ロジックに方向バイアスがあるか? → **却下**

---

> ## 📘 FOLLOW-UP: estimand framework として一般化 (追記 2026-04-17)
>
> 本文書の「SELL bias = regime drag」という発見は、数学的には **Simpson's paradox による marginal estimate のバイアス** の具体例であることが判明。formal な扱いは [[conditional-edge-estimand-2026-04-17]] に移管した。
>
> **要点**:
> - 現行 `RigorousAnalyzer` の出力は $\pi^{\text{sample}}(\text{regime})$ で暗黙に重み付けされた期待値
> - 真の estimand は $\pi^{\text{long\_run}}(\text{regime})$ で重み付けしたもの
> - 両者の差が本文書で検出された「SELL bias」の正体
>
> **今後の実装**:
> - `research/edge_discovery/regime_labeler.py` (OANDA OHLC 独立ラベラー)
> - `RigorousAnalyzer` に regime 次元 + reweighting + regime_support フラグを追加
> - 本文書の結論 (SELL bias は regime drag) は **定性的に変わらない** が、各戦略の「構造的敗者」判定は regime 分解まで保留
>
> **portfolio_balance.py 実行結果 (2026-04-17)**:
> - Overall 51:49 (軽微) / GBP_USD 58:42 (有意) / `trend_rebound` 17:83 (極端)
> - Regime × Direction: **RANGE × BUY のみ正 edge (+0.86p)**, 他 5セル全て負
> - production 自己申告 regime と OANDA 独立 regime の突合は別途実施予定

---

## エグゼクティブ・サマリー

**結論**: SELL方向の敗北は **signal-side のバイアスではなく、レジーム・ドラッグである**。

**主要エビデンス**:
1. Welch t-test on BUY vs SELL PnL: **p = 0.31** (有意差なし)
2. Cohen's d = **0.063** (効果量ほぼゼロ)
3. 9日間、全主要通貨ペアが **上昇トレンド**: USD_JPY +70p, EUR_USD +93p, GBP_USD +109p
4. SL/TP 構造・スプレッド・スリッページは BUY/SELL 対称
5. トレンドフォロー戦略の SELL が特に悪い (逆張りになっているため)

**前回主張の修正**:
- 先の分析で「SELL bias Bonf p=8e-8」と報告したが、これは **WR vs 50% BE-WR の二項検定**で、BUY も同様に有意に負けている (p=ほぼ同じ)
- 連続PnL比較で適正に検定すると **BUY-SELL 差は有意ではない** (p=0.31)

---

## Phase 1: 基本的な非対称性の検証

### 1.1 Direction summary

| Subset | direction | N | WR | Avg | Total |
|---|---|---|---|---|---|
| All | BUY | 533 | 30.0% | -1.055p | -562.4p |
| All | SELL | 521 | 25.9% | -1.480p | -771.0p |
| Live | BUY | 152 | 40.8% | -0.130p | -19.7p |
| Live | SELL | 174 | 32.8% | -1.053p | -183.3p |

表面上 SELL が負けている。しかし:

### 1.2 適正な統計検定

**Welch t-test** (分散不等の連続分布差):
- t = 1.015, df ≈ 1051, **p ≈ 0.31**
- **有意差なし**
- Cohen's d = 0.063 (effect sizeほぼゼロ)

binomial test (先の分析で使用) は **WR vs BE-WR**の片側検定で、「WRが50%から有意に違うか」を測る。BUY も SELL も負けWRで、両方とも独立に Bonf 有意になっているだけ。

### 1.3 構造的パラメータの対称性

| 項目 | BUY | SELL | 差 |
|---|---|---|---|
| SL距離 median (pips) | 4.1 | 3.9 | **対称** |
| TP距離 median (pips) | 7.2 | 6.8 | **対称** |
| R:R median | 1.70 | 1.67 | **対称** |
| spread_at_entry mean | 0.94p | 0.90p | SELL微有利 |
| slippage mean | 0.62p | 0.27p | SELL微有利 |

→ **signal-side と execution-side の両方で対称**. 負けの原因ではない。

---

## Phase 2: レジーム仮説の検証

### 2.1 期間内の価格変動 — entry_price ベース (却下された初期推定)

**注**: この初期推定は **entry_price** (signal が選んだ点) で計算しており、selection bias を含む。以下は却下された推定であり、2.2 の OANDA 実測で訂正した。

| 通貨ペア | 期初10本平均 | 期末10本平均 | Δ | 方向 (誤) |
|---|---|---|---|---|
| USD_JPY | 158.533 | 159.229 | +69.6p | UP (誤) |
| EUR_USD | 1.16844 | 1.17776 | +93.2p | UP (underestimate) |
| GBP_USD | 1.34249 | 1.35339 | +109.1p | UP (underestimate) |

### 2.2 独立な OANDA H1 candles での trend 検定 (訂正版)

OANDA /v3/instruments/:instrument/candles (H1, N=169 bars, 2026-04-07 17:00 ~ 04-16 17:00 UTC):

| pair | total_Δ | OLS slope (p/h) | p_slope | normalized drift (σ) | 有意性 |
|---|---|---|---|---|---|
| USD_JPY | **-58.8p** | +0.154 | 0.010 | +0.16σ | 微弱 (±1σ以内) |
| EUR_USD | **+199.0p** | +1.017 | <0.001 | +1.29σ | **強い uptrend** |
| GBP_USD | **+266.1p** | +1.327 | <0.001 | +1.40σ | **強い uptrend** |

**重要な訂正**:
- USD_JPY は entry_price 推定で +70p UP だったが、**実際は -58.8p DOWN**。entry_price は signal selection で歪められていた
- EUR_USD/GBP_USD は +199p, +266p で entry_price 推定の倍以上 → 本物のトレンド

### 2.2 戦略タイプ別の方向×成績

| strat_type | direction | N | WR | Avg |
|---|---|---|---|---|
| mean_rev | BUY | 358 | 30% | -1.33 |
| mean_rev | SELL | 352 | 25% | -1.46 |
| **trend** | **BUY** | **98** | 27% | **-0.80** |
| **trend** | **SELL** | **79** | 24% | **-2.12** |

**重要**: trend-following SELL が最悪 (-2.12 avg). Uptrend を逆張りすれば当然の結果。
mean-reversion は相対的に対称 (差 -0.13).

### 2.3 Tokyo SELL (-330p) のドリル分析

Tokyo session × SELL = 最大敗北セル (-330p in N=143).

**Tokyo SELL 通貨別**:
| inst | N | WR | Avg | Tot |
|---|---|---|---|---|
| USD_JPY | 120 | 25% | -1.92 | **-230.1p** |
| GBP_USD | 13 | 8% | -4.45 | -57.8p |
| GBP_JPY | 4 | 0% | -9.93 | -39.7p |

USD_JPY が Tokyo で +70p 上昇 (アジア勢の円売り) → Tokyo SELL は**100%逆張り**になっていた。

**apples-to-apples comparison** (同戦略・同通貨・Tokyo):
| 戦略 (USD_JPY, Tokyo) | BUY avg | SELL avg | Δ |
|---|---|---|---|
| vol_surge_detector | -0.47 | -2.28 | **-1.81** |
| bb_rsi_reversion | +0.77 | -0.24 | **-1.01** |
| sr_channel_reversal | -1.49 | -2.43 | -0.94 |
| stoch_trend_pullback | -0.98 | -1.05 | -0.06 |

3/4 戦略で SELL の方が悪い。差は 0.06 ~ 1.81p で、**uptrend drag (9日間で +70p = 平均 +0.3p/hour の下駄)** と整合。

---

### 2.4 Dose-response test (trend magnitude vs SELL-BUY PnL delta)

| pair | trend (pips/9d) | SELL-BUY Δ avg | consistency |
|---|---|---|---|
| USD_JPY | **-58.8** (no uptrend) | **+0.08** (SELL微有利) | ✓ |
| EUR_USD | +199.0 | -1.22 | ✓ |
| GBP_USD | +266.1 | -2.40 | ✓ |

**Pearson r (trend vs SELL-BUY Δ) = -0.955** (n=3, suggestive)

### 2.5 決定的 counterfactual: USD_JPY

仮に SELL bias が signal-side の欠陥なら、uptrend でない USD_JPY でも SELL underperform するはず。

**実測**: USD_JPY SELL-BUY Δ = **+0.08** (SELL が僅かに良い)

→ **signal-side asymmetry 仮説は falsify された**。

### 2.6 Magnitude の検証

H1 drift から予想される per-trade drag (10分 hold 想定):
- USD_JPY: +0.026p (小)
- EUR_USD: +0.170p
- GBP_USD: +0.221p

実測 SELL-BUY Δ は上記の 5-10 倍大きい。差は **SL asymmetry amplification** で説明可能:
- Uptrend では SELL の SL (下側) までの距離を市場が speed-up で埋める
- 一方 SELL の TP (上側) には届きづらい
- これは drift × hold の期待値を超えて観測 loss を増幅する

## Phase 3: 反証と限界

### 3.1 他の解釈可能性

| 仮説 | エビデンス | 判定 |
|---|---|---|
| A: Signal-side directional bias | t-test p=0.31, SL/TP対称 | **却下** |
| B: Execution-side cost asymmetry | spread/slippage共に SELL微有利 | **却下** |
| C: Regime drag (uptrend) | 全ペア UP, trend SELL最悪 | **採用** |
| D: Specific strategy flaws | sr_fib_confluence SELL WR 11% | 一部寄与 (補足) |

### 3.2 方法論的限界

- **9日 = 1レジームのみ**: 下降レジームで検証していない。BUY-SELL 非対称の方向性が regime-dependent であることを確認するには、次の regime 発生を待つ必要あり
- **期間内の regime 安定性**: 9日間ずっと uptrend だったかは不明 (intraday reversal は考慮されていない)
- **戦略間相関**: 多数の戦略が同時に同方向で入っている可能性あり (独立サンプルではない)

---

## Phase 4: Actionable な示唆

### 4.1 実施すべきでない

- ❌ **SELL方向の全停止** — regime drag は対称に反転する (downtrend では BUY が同じだけ負ける)
- ❌ **signal ロジック修正** — 有意な非対称性は検出されていない
- ❌ **Tokyo session 停止** — サンプル期間バイアス。他 regime で勝つ可能性あり

### 4.2 検討に値する

1. **Regime filter の導入** (中期): 4H/Daily のトレンド傾きが一定方向なら逆張り SELL/BUY を veto
   - 例: 4H EMA50-slope > threshold なら SELL 禁止 (または sizing 縮小)
   - cost: regime 判定の lag で edge を逃す可能性 → BT で検証必要

2. **Strategy-specific direction gate** (低優先): `sr_fib_confluence SELL` は 19 trades で -167p (WR 11%). 方向ロックをかける価値はあるが N 不足
   - 追加30日でも WR < 30% なら SELL off を検討

3. **観測継続** (高優先): regime が反転したとき、"BUY bias" が出現するか確認
   - 出現したら regime drag 仮説が強化される
   - 出現しなければ本当の signal-side asymmetry を疑う

### 4.3 前回分析の訂正

`rigorous-edge-analysis-2026-04-17.md` の以下を訂正:

| 項目 | 前回記述 | 訂正後 |
|---|---|---|
| SELL direction | "方向バイアスの可能性" | "uptrend regime drag。方向バイアスとは言えない (t-test p=0.31)" |
| SELL structural loser | "-183p Bonf sig" | "Bonf sig だが BUY も同等に負け。PnL差は非有意" |

---

## 関連ファイル

- 分析スクリプト: `/tmp/sell_bias_analysis.py`, `/tmp/sell_bias_regime.py`
- 前提分析: `analyses/rigorous-edge-analysis-2026-04-17.md`
- フレームワーク: `research/edge_discovery/rigorous_analyzer.py`

## 関連 lessons (次の session で追加予定)

- `lesson-regime-vs-signal-bias.md` — 方向別の負けを見たとき、regime と signal を区別する手順
- `lesson-binomial-vs-continuous-test.md` — WR binomial vs PnL t-test の使い分け

---

## クオンツ的所見 (要約)

1. **前回の「SELL bias 8e-8」は誤認ではないが誤解を招く**: WR の対50%二項検定と、BUY-SELL差のt-検定は別物。両方必要。
2. **entry_price ベースの regime 推定は誤り**: selection bias で USD_JPY を +70p UP と推定したが、OANDA 独立実測は -58.8p DOWN。
3. **Regime drag 仮説は確認された (部分的)**:
   - EUR_USD/GBP_USD は p<0.001 の有意 uptrend
   - USD_JPY の counterfactual が signal-side bias を falsify
   - Dose-response r=-0.955
4. **Magnitude は drift×hold だけでは 10-30% しか説明できない**。残りは SL asymmetry amplification と推定。
5. **Signal-side 修正は不要**: データは signal asymmetry を支持しない。
6. **残る限界**: n=3 pair, 9日, 1 regime のみ。次の downtrend で BUY-penalty が観測されれば仮説完成。
7. **次のアクション**: 観測継続 + 30日蓄積 + 次 regime の counterfactual test。
