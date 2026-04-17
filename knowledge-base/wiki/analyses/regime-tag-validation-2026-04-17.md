# Regime Tag Validation — production vs OANDA-independent

**Date**: 2026-04-17
**Status**: Complete — decisive finding (action E from portfolio-balance-audit)
**Author**: Claude (quant mode)
**Parent**: [[conditional-edge-estimand-2026-04-17]], [[portfolio-balance-audit-2026-04-17]]
**Tags**: #analysis #regime #validation #critical
**Tool**: `tools/regime_cross_tab.py --date-from 2026-04-08`

---

## 0. TL;DR

**production の regime tag は信頼不能。即時分析変数から除外すべき。**

- Strict agreement (prod tag == independent labeler): **22.7%** (N=326)
- Loose agreement (both classify as trend-class): **35.6%**
- production `TREND_BEAR` の **37% は実際には up_trend** ← 逆方向のラベル
- production `RANGE` の **0.8% のみ** が independent labeler でも range
- production `RANGE` の 52% は uncertain、33% は up_trend
- π_sample(range) は production 40.2% vs independent **3.1%** — 13倍乖離 ([[conditional-edge-estimand-2026-04-17]] §6 の仮説を定量確認)

**意味**: 過去 KB で production regime 列に基づいた全ての「regime-conditional edge」主張は artefact の可能性が高い。独立 labeler による再計算まで全 provisional。

---

## 1. 方法

9日 (2026-04-08 〜 2026-04-17) の LIVE trade N=326 を対象。

**入力**:
- `production.trades.regime` — production が entry 時刻に自己申告
- OANDA M30 candle × 5 instrument × 1000 bars (= ~20日相当、9日サンプルを十分カバー)
- Independent labeler: `research/edge_discovery/regime_labeler.py` (conditional-edge-estimand §6)
  - slope_t > +2.0 AND ADX > 25 → up_trend
  - slope_t < −2.0 AND ADX > 25 → down_trend
  - |slope_t| < 1.0 AND ADX < 20 → range
  - otherwise → uncertain

**処理**: 各 trade の entry_time 以前の直近確定 M30 bar に付与された independent regime を "right-aligned, no look-ahead" で join。

---

## 2. Cross-tab (row %): production → independent

production が X とラベルした trade が independent labeler で何に分類されたか:

| prod \ ind | down_trend | range | uncertain | up_trend |
|---|---|---|---|---|
| **RANGE** (N=131)     | 14.5% | **0.8%** | 51.9% | 32.8% |
| **TREND_BEAR** (N=97) | 34.0% |  3.1% | 25.8% | **37.1%** |
| **TREND_BULL** (N=95) |  6.3% |  6.3% | 45.3% | 42.1% |
| UNKNOWN (N=3)         |  0.0% |  0.0% |  0.0% | 100.0% |

### 観察

1. **production RANGE の 0.8% のみが真の range**
   - 残り 99.2% は「低 ADX のトレンド残り (up 33%, down 15%)」または「転換帯 (uncertain 52%)」
   - production classifier は RANGE を閾値として異常に緩く定義している
2. **production TREND_BEAR の 37% は independent では up_trend**
   - **真逆のラベル**。TREND_BEAR 判定トレードの 1/3 以上が実際には上昇局面で執行された
   - これは [[sell-bias-root-cause-2026-04-17]] の SELL 戦略 up-trend 逆行現象の直接証拠
3. **production TREND_BULL の精度は相対的に高い** (42% 一致、反対ラベル 6%)
   - BULL → BEAR の逆誤判率は低い。classifier が sell-side でより保守的
4. **uncertain (transition帯) が全 production tag で 26-52% を占める**
   - production は uncertain という概念を持たず、全て trend or range に強制分類している

---

## 3. π_sample: independent labeler

| regime | π_sample (9日, LIVE) | π_long_run (3.2年, H1) |
|---|---|---|
| up_trend   | **37.4%** | ~22% |
| down_trend | 17.8% | ~22% |
| range      | **3.1%** | ~4% |
| uncertain  | 41.7% | ~52% |

### 観察

- **up_trend が long_run の 1.7倍** — サンプル期間が統計的に非代表
- down_trend が 0.8倍、range は長期一致、uncertain が 0.8倍
- π_sample ≠ π_long_run が [[conditional-edge-estimand-2026-04-17]] §3 のバイアス項を直接発動させる
- 特に「SELL 系戦略の marginal 負値」は up_trend の過剰サンプルで拡大して見える

---

## 4. Independent regime × direction × PnL (LIVE)

| regime | dir | N | WR | Avg | Med |
|---|---|---|---|---|---|
| up_trend   | BUY  | 60 | 31.7% | **−1.49p** | −3.00p |
| up_trend   | SELL | 62 | 45.2% | −0.28p | −2.10p |
| down_trend | BUY  | 24 | 45.8% | −0.00p | −3.00p |
| down_trend | SELL | 34 | 26.5% | −0.79p | −3.00p |
| range      | SELL |  6 |  0.0% | −2.85p | −3.15p |
| **uncertain** | **BUY**  | 64 | 48.4% | **+1.19p** | −0.10p |
| uncertain  | SELL | 72 | 27.8% | −1.69p | −3.00p |

### 驚きの発見

1. **唯一の黒字セルは uncertain × BUY** (+1.19p, N=64, WR=48.4%)
   - production view で +0.86p だった "RANGE × BUY" の正体は **uncertain (転換帯) × BUY**
   - つまりエッジは「range regime」ではなく「regime 不確定帯での BUY」
2. **up_trend × BUY が −1.49p で最悪水準**
   - 直観 (trend-follow BUY が勝つ) と逆
   - 原因仮説: ポートフォリオが mean-reversion 重量 (bb_rsi, sr_channel_reversal 等)。up_trend 中の MR BUY は「pullback 下で逆張り BUY → 短期反発せず継続下落」パターンを拾う
3. **up_trend × SELL が -0.28p で相対的にマシ**
   - これも直観逆だが、ポートフォリオ内の SELL が up_trend 中に「一時的反落」を拾い、わずかに回収している
4. **down_trend × BUY = ±0 (N=24)**, **down_trend × SELL = −0.79p (N=34)**
   - down_trend での SELL (trend-follow) も負 — これも MR-dominant の帰結
5. **uncertain × SELL は -1.69p の最悪** — uncertainty 帯で逆張り SELL が壊滅

### 含意

- **ポートフォリオ全体として trend-aligned BUY/SELL は negative EV、counter-trend BUY/SELL も negative EV**
- 唯一正値は uncertain × BUY。これは何を意味するか?
  - 解釈1: uncertain は「明確な trend でも range でもない」状態で、volume や news 以外の要因で微小な positive skew がある (検証余地)
  - 解釈2: BUY は FX 全般の positive carry 漂流 (円安持続、ドル高維持) を拾う passive exposure。uncertain 局面でのみ counter-signal が弱く、drift が表出する
  - **解釈2が有力**: production の RANGE tag 40% と独立 labeler の uncertain 42% がほぼ同比 → "production が RANGE と呼んでいた期間" は実質 uncertain で、そこでの BUY 黒字は passive drift の拾い

---

## 5. 既存結論への影響

### 5.1 [[portfolio-balance-audit-2026-04-17]] §2 の再解釈

- **production view**: RANGE × BUY = +0.86p (N=63) が唯一の黒字
- **independent view**: uncertain × BUY = +1.19p (N=64) が唯一の黒字
- これは **同じ取引群** (production が RANGE と呼んでいたものの 52% が uncertain に落ちた)
- つまり **エッジ主張の substance は変わらないが、regime の呼び名が違う**
- 以後 KB では independent labeler の "uncertain" を正式な regime 層として使用

### 5.2 `mode=scalp` STRONG (+0.24p) への影響

- scalp は RANGE × BUY 黒字に依存している可能性が高い
- 独立 labeler で再分解すると実体は uncertain × BUY の drift 拾い
- **production 判断には使わない**: π_long_run(uncertain)=52% と π_sample(uncertain)=42% の乖離は小さいので reweight 後も positive を維持する可能性はあるが、**"uncertain × BUY で passive carry を拾うだけの戦略"** と明示してから扱う

### 5.3 [[sell-bias-root-cause-2026-04-17]] への追記

- TREND_BEAR 判定の 37% が実際 up_trend だった事実は、SELL bias の **直接的な機序** を示す
- production が TREND_BEAR と自己申告した期間の 1/3 は実は上昇相場 → SELL 戦略が逆行して大損
- 原因は production classifier の down-side での誤検出率の高さ (TREND_BULL は誤判率 6% vs TREND_BEAR は誤判率 34%)

### 5.4 [[rigorous-edge-analysis-2026-04-17]] 全判定への impact

- すべての STRONG/MODERATE は production regime に非依存で計算されているので **直接影響なし**
- ただし、将来 regime-stratified に拡張する際は **絶対に production regime を使わない** — 独立 labeler 必須
- caveat 文言に「production regime tag は cross-tab で 22.7% 一致率しかないため分析変数として非採用」を明記

---

## 6. 次アクション（優先順）

| # | アクション | 工数 | 根拠 |
|---|---|---|---|
| α | production regime tag を analytics 層で deprecate (読み取り禁止フラグ) | 0.5h | 22.7% 一致率のデータを分析に使うのは誤り |
| β | `RigorousAnalyzer` を independent labeler 連携に改修 | 1日 | conditional-edge-estimand §7 の公式規約 |
| γ | per-strategy regime-stratified EV を independent labeler ベースで再計算 | 1日 | β 完了後、既存 STRONG/MODERATE 再評価 |
| δ | production regime classifier 自体を修正 (別 issue) | 別途 | 本番 signal 生成への影響範囲調査必要 |

**推奨**: α と β を先行。γ は β の出力物。δ は trading logic への影響が大きいため別途 design review 必要。

### δ の注意点

production regime tag は単に分析用ではなく、**本番 signal 生成の gate/filter に実際に使われている** (grep 確認済み):

| ファイル:行 | 用途 | 22.7% 一致率の影響 |
|---|---|---|
| `modules/demo_trader.py:2502` | rule regime と HMM regime の整合チェック | rule 側が誤分類なら整合性ロジック自体がノイズ |
| `modules/demo_trader.py:2955` | daytrade mode × TREND_BULL 時の特殊処理 | TREND_BULL 誤判 6% なので相対的に安全 |
| `modules/demo_trader.py:3263` | TREND_BULL かつ BUY 時の処理 | 同上、誤判 6% |
| `modules/demo_trader.py:3307` | BUY かつ TREND_BEAR かつ confidence<70 で reject | **TREND_BEAR 誤判 34% → 妥当な BUY を 1/3 不正 reject** |

特に 3307: "up_trend 中に TREND_BEAR と誤判定され、BUY がブロックされる" ケースが体系的に発生。これが **up_trend × BUY の負値** の一因の可能性 (残った BUY が conviction 低いもの + 不自然な select bias)。

**結論**: signal 生成への影響は非 trivial で、α (analytics 層 deprecate) は即時可能だが、δ (signal 層修正) は BT 回帰込みの design review が必要。当面の対策:

1. 即時: α と β で分析層の汚染を止める
2. 短期: δ のスコープで demo_trader.py:3307 を中心に BT 再走 (production regime → independent regime に feature 差し替え)
3. 中期: production regime classifier 自体を independent labeler に置き換え (production signal 生成系の一貫性のため)

---

## 7. 結論

1. production regime tag は実態との一致率 22.7% で **分析変数として使用不可**
2. π_sample は independent labeler で up_trend 37%, uncertain 42% と測定 — long_run から up-trend 過剰、uncertain 過少
3. 唯一の黒字セルは **uncertain × BUY = +1.19p** (production の "RANGE × BUY" の正体)
4. trend-aligned・counter-trend どちらも全体負。ポートフォリオはほぼ mean-reversion 依存で、trend 局面で全部負ける構造
5. SELL bias は `TREND_BEAR` タグ 37% の逆誤判から部分的に説明可能 — ただし up_trend 本体での SELL が実際は BUY より軽微な負値 (−0.28p vs −1.49p) であり、「SELL が本質的に悪い」のではなく「BUY がポートフォリオ内の MR 戦略配置で自爆している」

---

## Links
- [[conditional-edge-estimand-2026-04-17]] — §6 (regime labeler) の実施
- [[portfolio-balance-audit-2026-04-17]] — §2 の RANGE × BUY の正体を本分析で特定
- [[sell-bias-root-cause-2026-04-17]] — TREND_BEAR 37% 逆誤判が機序
- [[rigorous-edge-analysis-2026-04-17]] — regime-stratified 改修の前提
- [[friction-analysis]] — up_trend × BUY −1.49p の原因の 1 つとして MR pullback loss を要検証
