# Conditional Edge Estimand Framework

**Date**: 2026-04-17
**Status**: DRAFT (要レビュー)
**Author**: Claude (quant mode)
**Parent**: [[sell-bias-root-cause-2026-04-17]], [[data-acquisition-plan-2026-04-17]]
**Tags**: #analysis #methodology #estimand #regime #simpsons-paradox

---

## 0. TL;DR

現行 `RigorousAnalyzer` は戦略 s のエッジを marginal 標本平均 $\hat{\theta}_s = \frac{1}{N} \sum \text{pnl}_i$ として報告している。これは暗黙に **サンプル期間の regime 時間分布 $\pi^{\text{sample}}$ で重み付けされた期待値** であり、本番での期待 PnL $\theta^{\text{prod}}$ とは一般に一致しない。9日・N=1090 のサンプルで $\pi^{\text{sample}} \approx \pi^{\text{prod}}$ が成立する根拠はない。

**是正**: エッジは **regime 条件付きで測定し、長期 regime prior $\pi^{\text{long\_run}}$ で再重み付け**して報告する。さらに、ある regime で $n_{s,r}$ が閾値未満の戦略は `insufficient_regime_coverage` フラグを立て、STRONG/MODERATE 判定を保留する。

これを実装するまで、現行の STRONG/MODERATE ラベルは **すべて "regime-unadjusted, provisional"** として扱う。

---

## 1. 目的

何を推定しているのかを formal に書く。現在、`RigorousAnalyzer` の出力を「本番で得られる期待 PnL」の代理として解釈しているが、この同一視は暗黙で、かつ多くの条件で誤っている。本文書は以下を定める:

1. 真の estimand の数式表現
2. 現行推定量のバイアス特定
3. 是正推定量 (regime-reweighted)
4. エッジ報告時の必須メタ情報

---

## 2. 真の estimand

戦略 $s$ の本番期待 PnL (per trade):

$$
\theta_s^{\text{prod}} \;:=\; \mathbb{E}_{r \sim \pi^{\text{prod}}} \bigl[\; \mathbb{E}[\text{pnl} \mid s, r] \;\bigr]
$$

記号:
- $r \in \{up\_trend,\; down\_trend,\; range,\; uncertain\}$: レジームラベル
- $\pi^{\text{prod}}(r)$: 本番運用期間中に出現する regime の時間比率 (未知)
- $\mathbb{E}[\text{pnl} \mid s, r]$: 戦略 $s$ が regime $r$ で発火した時の trade 当たり期待 PnL

$\pi^{\text{prod}}$ は未知だが、**代理として $\pi^{\text{long\_run}}$** (数年 OANDA OHLC から実測) を採用する:

$$
\hat{\theta}_s^{\text{reweighted}} \;=\; \sum_{r} \pi^{\text{long\_run}}(r) \cdot \hat{\mathbb{E}}[\text{pnl} \mid s, r]
$$

これが本フレームワークが採用する **公式推定量**。

---

## 3. 現行推定量のバイアス

現行 `RigorousAnalyzer.build_pocket` は:

$$
\hat{\theta}_s^{\text{current}} \;=\; \frac{1}{N_s} \sum_{i=1}^{N_s} \text{pnl}_i \;=\; \sum_{r} \pi_s^{\text{sample}}(r) \cdot \hat{\mathbb{E}}[\text{pnl} \mid s, r]
$$

ここで $\pi_s^{\text{sample}}(r) = n_{s,r} / N_s$。つまり **戦略固有のサンプル内 regime 頻度で重み付けしている** (long_run ではない)。

### 3.1 バイアス項

$$
\text{Bias}\bigl(\hat{\theta}_s^{\text{current}}\bigr) \;=\; \sum_r \Bigl[\pi_s^{\text{sample}}(r) - \pi^{\text{long\_run}}(r)\Bigr] \cdot \mathbb{E}[\text{pnl} \mid s, r]
$$

このバイアスがゼロとなる条件:

- (a) $\pi_s^{\text{sample}} = \pi^{\text{long\_run}}$ — サンプルが regime 比率において代表的
- (b) $\mathbb{E}[\text{pnl} \mid s, r]$ が $r$ によらず定数 — 戦略がレジーム無感応

**我々のケースではどちらも成立しない**:
- N=1090 / 9日では regime 比率の中心極限は効かない (9日の regime 構成は5年平均と容易に数十%乖離)
- トレンドフォロー系・カウンタートレンド系・スキャルプ系はいずれも明白に regime 感応

従って現行推定量は **バイアスあり** と断言できる。残る問いは「バイアスの方向と大きさ」のみ。

### 3.2 前セッションの SELL bias は本バイアスの実例

[[sell-bias-root-cause-2026-04-17]] で発見した現象は数学的には本 bias の具体例:
- $\pi^{\text{sample}}$: EUR_USD/GBP_USD で up_trend 偏在
- SELL 系戦略: $\mathbb{E}[\text{pnl} \mid s, \text{up}] \ll 0$
- 結果: $\hat{\theta}_s^{\text{current}}$ が過度に悲観

逆に同期間の BUY 系戦略の $\hat{\theta}$ は過度に楽観 (未検証)。この **対称バイアス** が現行 STRONG/MODERATE 判定に埋め込まれている。

---

## 4. Simpson's paradox 具体例 (Illustrative)

| 戦略 | $n_{up}$ | $n_{down}$ | $n_{range}$ | $\overline{\text{pnl}}_{up}$ | $\overline{\text{pnl}}_{down}$ | $\overline{\text{pnl}}_{range}$ | Current | Reweighted ($\pi = (0.40, 0.35, 0.25)$) |
|---|---|---|---|---|---|---|---|---|
| A | 100 | 50 | 50 | +1.0p | −0.5p | +0.1p | +0.40p | +0.25p |
| B | 20 | 80 | 20 | −0.3p | +0.8p | +0.1p | +0.45p | +0.39p |
| C | 150 | 0 | 0 | +0.8p | — | — | +0.80p | **推定不能** (regime support 不足) |

示唆:
- 戦略 A は marginal +0.40p だが真の EV は +0.25p — **60%の過大評価**
- 戦略 C は現行 +0.80p で STRONG 判定候補だが、**そもそも down/range regime での挙動が不明**。production で regime が切り替わった時に何が起きるかデータから何も言えない

**教訓**: "marginal positive edge" は "production positive edge" を含意しない。

---

## 5. 分散と信頼区間

Stratified variance (regime を独立層として扱った場合):

$$
\mathrm{Var}\bigl(\hat{\theta}_s^{\text{reweighted}}\bigr) \;=\; \sum_r \bigl[\pi^{\text{long\_run}}(r)\bigr]^{2} \cdot \frac{\hat{\sigma}_{s,r}^{\,2}}{n_{s,r}}
$$

いずれかの $n_{s,r}$ が小さいと分散が発散する。運用判定用のしきい値:

- **全 regime で $n_{s,r} \geq 30$** → `regime_support = FULL`、通常判定
- **一部 regime で $n_{s,r} < 30$ かつ $n_{s,r} \geq 10$** → `regime_support = PARTIAL`、SE を報告しつつ STRONG 不可
- **いずれかの regime で $n_{s,r} < 10$** → `regime_support = INSUFFICIENT`、判定保留 (recommendation は WEAK に強制)

---

## 6. $\pi^{\text{long\_run}}$ の推定方針

### データ源
- OANDA `/v3/instruments/:pair/candles`
- 期間: 過去 5 年
- 時間枠: M30 (M1 だとノイズ過多、H1 だとサンプル少)
- XAU_USD は feedback_exclude_xau (user memory) により除外

### ラベラー仕様
`research/edge_discovery/regime_labeler.py` (別途実装):

- Input: OANDA candle DataFrame (M30, right-aligned 確定足のみ)
- Features:
  - Slope (OLS over last 48 bars) and its t-statistic
  - ADX(14)
  - ATR(14) normalized by price
- Label rule (MVP):
  - `slope_t > +2.0` AND `ADX > 25` → `up_trend`
  - `slope_t < -2.0` AND `ADX > 25` → `down_trend`
  - `|slope_t| < 1.0` AND `ADX < 20` → `range`
  - otherwise → `uncertain`
- Look-ahead防止: window を right-aligned で計算、未来足を含めない

### ペア別 prior
$\pi^{\text{long\_run}}$ は **ペア固有** に推定する。USD_JPY と EUR_USD の regime 分布は構造的に異なる (介入・金利差・キャリー)。

### 実測値 (2026-04-17 推定, `scripts/estimate_regime_prior.py` 出力)

H1 × ~20000 bars (2023-01-29 ~ 2026-04-17, 約 3.2 年):

```
Pair        up_trend  down_trend  range   uncertain  n_bars
EUR_USD      21.8%     22.7%       4.4%    51.2%     19999
USD_JPY      21.0%     21.3%       4.0%    53.8%     19999
GBP_USD      22.1%     21.6%       4.1%    52.2%     19999
AUD_USD      18.9%     19.5%       5.0%    56.6%     19999
(XAU_USD: 除外)
```

**観察**:
- 全ペアで up:down がほぼ対称 (21:21 〜 22:23). これは FX が相対価格である性質と整合.
- `range` (厳密定義: |slope_t|<1 AND ADX<20) はわずか 4-5%. 閾値が厳しい.
- `uncertain` が 51-57% と大半を占める — 転換帯 (slope弱 × ADX強、slope強 × ADX弱) がここに落ちる.
- **サンプル (9日, production 自己申告タグ) との乖離**:
    - production: TREND_BULL 29% / TREND_BEAR 30% / RANGE 40%
    - long_run: up 21% / down 22% / range 4%
    - **production 自己申告は range を過大カウント** (閾値設定が異なる classifier ゆえ)
- **従って production regime 列をそのまま π_sample として reweight するのは不適切**. 必ず独立ラベラー経由で両方を再計算すること.

### 既知の限界
- 3.2 年ウィンドウは "long run" とはいえ 2023 以降の金融緩和縮小 regime に偏っている. 将来は 5 年 rolling に拡張.
- ADX/slope ベースの ternary label は情報損失あり (詳細は §10).
- 各ペアで同じ閾値 — ペアのボラティリティに対する補正なし (将来 improvement 候補).

---

## 7. エッジ報告の必須規約 (今後 `RigorousAnalyzer` に追加)

1. `n, wr, avg_pips` — marginal 参考値 (従来通り)
2. `π_sample(r)` — per-regime サンプル比率 (ポケットごとに必須)
3. `Ê[pnl | r]` と `n_r` — 各 regime ($n_r \geq 10$ のもののみ表示)
4. `θ̂_reweighted` — $\pi^{\text{long\_run}}$ 再重み付け EV
5. `SE(θ̂_reweighted)` — stratified 標準誤差
6. `regime_support` ∈ {FULL, PARTIAL, INSUFFICIENT}
7. `recommendation` 決定ロジック:
   - STRONG: Bonf 有意 AND $\thetâ_{\text{reweighted}} > 0$ AND `regime_support == FULL` AND WF stable AND $N \geq 30$
   - MODERATE: FDR 有意 AND $\thetâ_{\text{reweighted}} > 0$ AND `regime_support != INSUFFICIENT` AND $N \geq 30$
   - WEAK: それ以外
8. 出力に常に `π_sample` disclaimer を添付 (サンプル regime 構成が表示されない edge 主張を禁止)

---

## 8. 既存結論への影響

### 8.1 `mode=scalp` STRONG (LIVE, N=152, WR=44%, BE=61%, Avg+0.24p, PF=1.14, WF=Y)

- サンプル期間: 2026-04-08 以降 9日
- 同期間の EUR_USD/GBP_USD は OANDA 独立検証で有意な up-trend
- scalp mode の BUY:SELL 比率未測 — もし BUY 偏りなら marginal +0.24p は passive long beta の可能性大
- WR(44%) < BE-WR(61%) + Avg(+0.24p) の組み合わせは **少数の大勝トレードが期待値を持ち上げる signature**。これは regime-specific "big winner" の特徴と整合
- **新規約により `regime_support` 未算出につき recommendation 保留 (WEAK 相当)**
- **Production 判断には使わない** — regime 分解後に再評価

### 8.2 負 Bonf-significant セル 17件 (LIVE, SELL/trend 系主体)

[[sell-bias-root-cause-2026-04-17]] の通り、同じバイアスが逆方向に作用した可能性が極めて高い。
- regime 分解で $\mathbb{E}[\text{pnl} \mid s, \text{down\_trend}] > 0$ となる cell が出る可能性あり
- その場合は「SELL 戦略自体は down regime で有効、但し production で出るか否かは別問題」という**条件付き有効性**の報告になる
- これらを「構造的敗者」として demote する現行プロセスは一時保留が望ましい

### 8.3 全 STRONG/MODERATE 判定

regime-unadjusted である旨を KB レポートに明示。[[rigorous-edge-analysis-2026-04-17]] にも caveat 追記必要。

---

## 9. Next actions (優先順)

| # | アクション | ファイル | 工数 | 前提 |
|---|---|---|---|---|
| 1 | `regime_labeler.py` 実装 + unit test | `research/edge_discovery/regime_labeler.py` | 0.5日 | OANDA API 接続 (既存) |
| 2 | `π_long_run` 推定スクリプト + KB 表埋め | `scripts/estimate_regime_prior.py` | 0.5日 | #1 |
| 3 | `RigorousAnalyzer` に `regime` 次元と `θ̂_reweighted`, SE, regime_support 追加 | `research/edge_discovery/rigorous_analyzer.py` | 1日 | #1, #2 |
| 4 | `tests/test_regime_labeler.py`, `tests/test_rigorous_analyzer.py` 拡張 | tests/ | 0.5日 | #3 |
| 5 | ポートフォリオ BUY:SELL 比率監査 (構造的 long-bias の即時診断) | `tools/portfolio_balance.py` | 0.5h | 独立 |
| 6 | 既存 KB (`rigorous-edge-analysis-2026-04-17`, `sell-bias-root-cause-2026-04-17`) に caveat 追記 | knowledge-base/ | 0.5h | 独立 |
| 7 | `mode=scalp` STRONG の regime 分解再評価 | `rigorous-edge-analysis-2026-04-17.md` 更新 | 0.5h | #3 |

**推奨順序**: #5 → #6 (即効・並行) → #1 → #2 → #3 → #4 → #7

---

## 10. 既知の限界と今後の拡張

- **Regime ラベルが ternary (+ uncertain)** — 情報損失あり。連続値 (trend strength × range width) による soft weighting の方が望ましい。MVP 後に検討。
- **$\pi^{\text{long\_run}}$ 自体の time-varying 性** — 10年スケールで regime 分布は構造変化する (例: 2020-2022 超緩和期 → 2023-2025 引き締め期)。5年 rolling で再推定する運用が必要。
- **Regime と戦略の非独立性** — 戦略発火条件に ADX や slope 等を含む場合、regime ラベルと発火は相関。条件付き期待値の解釈に注意 ("この戦略は up regime で勝つ" が tautological にならないか)。
- **Purged CV との統合** — Walk-forward stability を regime-stratified に変更する際、López de Prado (2018) "Advances in Financial Machine Learning" の Purged K-Fold を採用すべき。fold 境界で regime transition が跨ぐと leakage の危険あり。
- **π_prod との乖離リスク** — 本番が long-run prior と異なる regime に入った場合 (構造変化局面)、reweighted estimator も誤る。これは原理的に回避不能。対策は live PnL の rolling monitoring と早期ストップ。
- **個別ペア × regime の cell が小さい問題** — N=1090 の現サンプルでは多くの cell で $n_{s,r} < 30$ となる。当面は `regime_support = PARTIAL` が主で、FULL は稀。**累計 5000 トレード超までは大半の cell で SE が広い** ことを許容する必要あり。

---

## 11. 用語集

- **Estimand**: 推定したい真の量 (θ)。estimator (推定量 $\hat{\theta}$) とは区別される。
- **Marginal estimate**: 条件付けなしの標本平均。 $\frac{1}{N}\sum \text{pnl}_i$。
- **Conditional estimate**: 層 (regime) 内での期待値。 $\hat{\mathbb{E}}[\text{pnl} \mid s, r]$。
- **Reweighted estimate**: 条件付き期待値を外部の prior で重み付けした estimator。
- **Simpson's paradox**: 層ごとの関係と全体の関係が逆転する現象。本フレームワークが直接対処する課題。
- **Regime support**: 戦略 s が各 regime で十分なサンプルを持つか (FULL / PARTIAL / INSUFFICIENT)。
- **$\pi^{\text{sample}}$**: サンプル期間の regime 時間比率。データから観測可能。
- **$\pi^{\text{long\_run}}$**: 長期 (数年) 平均の regime 時間比率。OANDA OHLC から推定。本フレームワークで prior として採用。
- **$\pi^{\text{prod}}$**: 本番運用期間中の真の regime 比率。事前には未知。

---

## Links
- [[sell-bias-root-cause-2026-04-17]] — 本フレームワーク導出の契機となった SELL bias 分析
- [[data-acquisition-plan-2026-04-17]] — regime 検証用 OANDA OHLC 取得計画
- [[rigorous-edge-analysis-2026-04-17]] — 改訂前の edge 分析結果 (本文書により全面再解釈が必要)
- [[claude-harness-design]] — クオンツ動作モード全体方針
- [[bt-live-divergence]] — BT/Live 乖離の他の要因 (regime は 6 要因の 1 つ)
