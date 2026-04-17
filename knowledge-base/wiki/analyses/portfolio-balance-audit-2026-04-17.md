# Portfolio BUY/SELL Balance Audit — 2026-04-17

**Date**: 2026-04-17
**Status**: Analysis complete (next action #5 from conditional-edge-estimand)
**Author**: Claude (quant mode)
**Parent**: [[conditional-edge-estimand-2026-04-17]], [[sell-bias-root-cause-2026-04-17]]
**Tags**: #analysis #regime #simpsons-paradox #audit
**Tool**: `tools/portfolio_balance.py --date-from 2026-04-08`

---

## 0. TL;DR

9日 N=1098 のポートフォリオ全体で構造的 long-bias 仮説は **棄却** (BUY:SELL = 51:49, p=0.33)。
しかし **RANGE regime 内の direction asymmetry** という別の本質的問題が浮上:

- RANGE × BUY: N=63, WR=52.4%, Avg=**+0.86p**
- RANGE × SELL: N=68, WR=32.4%, Avg=**−1.57p**
- Spread = **2.43p** (Simpson's paradox の教科書例)

そして RANGE の production 自己申告比率は **π_sample = 40.2%** に対し OANDA 独立 labeler 基準の **π_long_run ≈ 4%** — **10倍の乖離**。現 production regime tag は実質信頼不能と判断すべき。

---

## 1. 検証した仮説と結果

| # | 仮説 | 結果 | 証拠 |
|---|------|------|------|
| H1 | ポートフォリオ全体に構造的 long-bias | **棄却** | 565:533 (51%B/49%S), χ² p=0.3342 |
| H2 | 特定 instrument で方向偏り | **部分支持** | GBP_USD 58%B (p=0.049) のみ ⚠ |
| H3 | 特定 entry_type で方向偏り | **支持** (2件) | ema_trend_scalp 65%B (p=0.0055), trend_rebound 17%B (p=0.0003) |
| H4 | SELL bias は direction 自体の問題 | **棄却** | BUY marginal=−0.13p, SELL marginal=−1.05p — 差はあるが原因は後述 |
| H5 | regime × direction 相互作用が存在 | **強く支持** | RANGE cell で spread 2.43p |

---

## 2. 決定的発見: RANGE × DIRECTION 非対称性

```
regime       dir   N     WR      Avg
TREND_BULL   BUY   56    30.4%   -0.44p
TREND_BULL   SELL  39    28.2%   -0.87p
TREND_BEAR   BUY   30    36.7%   -0.57p
TREND_BEAR   SELL  67    35.8%   -0.64p
RANGE        BUY   63    52.4%   +0.86p  ← 唯一の黒字セル
RANGE        SELL  68    32.4%   -1.57p  ← 最悪セル
```

**読み方**:
- TREND_BULL/TREND_BEAR では direction spread が小さい (0.43p, 0.07p) — regime 情報そのものは方向予測力が弱い
- RANGE では direction spread が 2.43p と突出
- これは「真の RANGE regime における mean reversion が機能している」か、または
- **「production が RANGE と自己申告した実質的 bull-bias 期間」で BUY が passive long-beta を拾っている** かのいずれか

後者を強く示唆する傍証:
- サンプル期間 (2026-04-08 以降 9日) は独立検証で EUR_USD/GBP_USD が有意 up-trend ([[sell-bias-root-cause-2026-04-17]])
- production tag の RANGE 比率 40% vs long_run 実測 4% は classifier 閾値の緩さを意味する
- 真の range なら BUY も SELL も WR ≈ 50% に収束するはず。実際は BUY=52%/SELL=32% という **非対称**

結論: **RANGE tag は RANGE を意味していない**。現状は "low-ADX のトレンド残り" を RANGE と誤ラベルしている可能性大。

---

## 3. 棄却された仮説の再解釈

### 3.1 "BUY:SELL 全体比率" は意味のないメトリック

当初の作業仮説は「ポートフォリオが BUY に偏っている → up-trend サンプル期間で passive long を拾っている → SELL 側が相対的に悪く見える」というもの。

実測は 51:49 で有意差なし。しかし per-regime で見ると:
- BUY の regime 別 spread = +0.86p (RANGE) − (−0.57p) (TREND_BEAR) = **1.43p**
- SELL の regime 別 spread = (−0.64p) (TREND_BEAR) − (−1.57p) (RANGE) = **0.93p**

つまり direction 自体の偏りはないが、direction × regime の交互作用が巨大。[[conditional-edge-estimand-2026-04-17]] の §3.1 で予測されたバイアス項の実例。

### 3.2 ema_trend_scalp 65%B, trend_rebound 83%S

両者とも意図的な directional 戦略。
- ema_trend_scalp: EMA trend-following → 当該期間の up-trend で BUY 側が多いのは自然
- trend_rebound: mean reversion 系で SELL 偏り — 逆張り戦略が up-trend 期間に SELL を多発させた設計通りの振る舞い

これらは「エッジが壊れている」ではなく「regime exposure が偏っている」。edge 評価には必ず regime-stratified が必要。

### 3.3 USD_JPY は BUY/SELL 両方 negative (Avg=−0.42p/−0.21p)

N=645 の最大セルで両方向とも marginal negative。これは regime bias ではなく **instrument 固有の friction** を示唆 (spread, SL friction, quick-harvest の相互作用)。[[friction-analysis]] との突き合わせが必要。

---

## 4. Simpson's paradox の実例 (per conditional-edge-estimand §4 の具体化)

戦略群全体 (LIVE, N=326) について:

| regime | π_sample | π_long_run | BUY Avg | SELL Avg |
|---|---|---|---|---|
| TREND_BULL | 29.1% | ~22% | −0.44p | −0.87p |
| TREND_BEAR | 29.8% | ~22% | −0.57p | −0.64p |
| RANGE | 40.2% | ~4% | **+0.86p** | **−1.57p** |
| UNCERTAIN | 0.9% | ~52% | — | — |

注: production は UNCERTAIN をほぼ RANGE に寄せている (production tag に UNCERTAIN が事実上存在しない)。これが RANGE 40% の元凶。

**Reweighted marginal (仮置き、π_long_run 使用)**:
- BUY reweighted ≈ 0.22×(−0.44) + 0.22×(−0.57) + 0.04×(+0.86) + 0.52×(未測) = 計算不能
- 結論: **UNCERTAIN セルのサンプルが枯渇しているため reweight は現状不可能**
- これは [[conditional-edge-estimand-2026-04-17]] §5 の `regime_support = INSUFFICIENT` 相当

---

## 5. 即時アクション（優先順）

| # | アクション | 工数 | 根拠 |
|---|------|------|------|
| A | production regime classifier の threshold を OANDA 独立 labeler と突き合わせ | 1h | RANGE 10倍乖離の原因特定 |
| B | GBP_USD 58%B skew の発生源戦略を特定 (per-strategy × GBP_USD direction 内訳) | 0.5h | instrument × strategy の conditional check |
| C | USD_JPY friction の再測定 (BUY/SELL 両方 negative の原因特定) | 1h | friction-analysis 更新 |
| D | ema_trend_scalp, trend_rebound の regime-stratified EV を計算 | 0.5h | directional 戦略を regime で裁量 |
| E | regime_labeler を 9日サンプルに適用し、production tag と cross-tab | 1h | §2 の誤ラベル仮説の直接検証 |

**推奨順序**: E (決定的) → A (E の結果を使う) → D (即効判定) → B, C (並行)

---

## 6. 既存 KB への影響

### [[sell-bias-root-cause-2026-04-17]] に追記必要
- 「SELL 偏り説」は direction 全体では棄却されたが、**RANGE × SELL で局所的に顕在化** と update
- EUR_USD SELL (N=30, WR=13%, Avg=−2.46p) と GBP_USD SELL (N=14, WR=7%) は極端で、up-trend regime で SELL 戦略が逆行した典型例

### [[rigorous-edge-analysis-2026-04-17]] に caveat
- すべての STRONG/MODERATE は regime-unadjusted
- 特に `mode=scalp` STRONG (N=152, Avg+0.24p) は RANGE × BUY の +0.86p が寄与している可能性が高い
- regime_labeler 適用後に再評価するまで production 判断には使用しない

### [[conditional-edge-estimand-2026-04-17]] §8 update
- §8.1 (scalp STRONG) に「RANGE × BUY が主寄与の仮説」を追加
- §8.2 (SELL 17件) に「RANGE × SELL −1.57p が主犯の可能性」を追加

---

## 7. 結論

1. **構造的 long-bias 仮説は棄却** — BUY:SELL=51:49
2. **新仮説**: production RANGE tag が信頼不能。π_sample(RANGE)=40% vs π_long_run(range)≈4% の 10倍乖離は classifier 差では説明不足で、UNCERTAIN が全て RANGE に吸収されている可能性
3. **SELL bias の真の所在**: RANGE × SELL セル (N=68, Avg=−1.57p)。特に EUR_USD/GBP_USD SELL は当該期間の up-trend 逆行で極端に悪化
4. **次の決定的実験**: regime_labeler を 9日サンプルに適用し、production RANGE tag が何の独立ラベルに対応するかを直接計測 (action E)

---

## Links
- [[conditional-edge-estimand-2026-04-17]] — 本分析の framework
- [[sell-bias-root-cause-2026-04-17]] — 初期仮説 (本分析で refine)
- [[rigorous-edge-analysis-2026-04-17]] — caveat 対象
- [[friction-analysis]] — USD_JPY 両方向 negative の診断に使用
