# 反証: H4 水平線 × 15m に方向性エッジ無し (2026-06-22)

- **判定**: REJECT / 棚上げ。**再試行禁止**（この特徴量セット・相互作用定義では）。
- **rule**: R1 相当（新規エッジ評価を full statistical rigor で実施 → null）。
- **動機**: user が TV で見ていた "EURUSD 15m hull donchian fade" が強く見えたが、Strategy Tester 実数で摩擦控除後マイナスと判明（下記）。そこから「H4水平線で反発 or ブレイク、15mエントリー」を data-driven 探索した。
- **関連**: [[friction-analysis]] / spec `docs/superpowers/specs/2026-06-22-h4-level-edge-discovery-design.md` / tool `tools/h4_level_edge_explore.py`

## 経緯（同セッションで3方向検証、全て収束）

### 0. きっかけ — TV "Hull-Donchian FADE" v241 の実態
- chart 上は `study()`(インジケーター) で Strategy Tester 数値ゼロ → 目視の錯覚だった。
- `strategy()` 版 (My script2, **version 241**) を Deep Backtest (2002-2026):
  - N=5,865 / WR=73.45% / **PF=1.108** / +5.31% / MaxDD 0.99%。
  - **PF は摩擦ゼロのグロス**。平均 +0.9pip/trade に対し EUR_USD RT friction 2.0pip → **摩擦控除後マイナス**。
  - ソースに **stop loss 無し**（basis-touch exit のみ）+ 241改訂 + maxWidth=3.86「train-q33」= カーブフィット。
  - 教訓再確認: WR73% の正体は高WR薄エッジ fade の視覚錯覚。[[feedback_tv_edge_discovery_loop]] / [[project_be_trail_inflates_python_bt_wr]] の典型。

### 1. TV proto (frozen-spec, slippage=10=2.0pip RT, EUR_USD ~10ヶ月 in-sample)
| 戦略 | N | WR | PF | PnL |
|---|---|---|---|---|
| H4 heavy-wall **reversal** | 982 | 33.7% | **0.767** | -1.19% |
| H4 heavy-wall **breakout** | 447 | 35.1% | **0.841** | -0.50% |
- 2R TP の損益分岐 WR = 33.3%(グロス)。両者ともこの分岐線上に張り付き → **方向エッジ≈ゼロ、摩擦が両者をマイナスに押し下げ**。in-sample で負け = OOS では確実に負け。

### 2. Python Stage-1 IC 分析 (6ペア, train 60% = 2022-01〜2024-08, N=10k-15k/ペア)
- tool: `tools/h4_level_edge_explore.py`（因果性厳守: Fractal n=2 swing は +2bar 確定後のみ使用、holdout 不参照、Spearman IC のみ＝閾値最適化なし）。
- 特徴量8 × ターゲット4 × horizon2 = 64検定, Bonferroni α=0.05/64=0.00078。
- **結果**:
  - 唯一強い IC = **`atr_regime → abs(return)`** (|IC|≈0.10-0.17, 全ペア★)。= **方向中立のボラ予測**。WR を 33% から持ち上げない。
  - 方向性 (continuation/reversion) IC は軒並み **|IC|<0.05**、★は散発的で**ペア間再現性なし**。
  - quintile 単調性が立った方向性セルは 6ペア中 **1組のみ** (GBP_USD h48, 偶発域)。
  - EUR_JPY の巨大 quintile は 2022 円安**トレンドドリフト混入**で wall エッジではない。

## 結論
**H4 heavy wall は「ボラ拡大の場所」は当てるが「方向」は当てない。** N=10k-15k で方向性ICが立たない = サンプル不足ではなく**本当に無い**。FXスポットでは abs-return 予測を直接マネタイズ不可（オプション無し）。よって方向性アイデアは死。

設計 §11 の「クリーンな反証」を達成（v241 と違い汚染データを残さない）。

## 残骸の活用余地（別タスク）
- `atr_regime` は方向でなく**ボラフィルタ/TP・SLスケーリング**として既存有望戦略 ([[trendline-sweep]] 等) に転用検討可。それ単体は戦略にならない。
- `tools/h4_level_edge_explore.py` は他の水準定義 (HVN / 日足ピボット / セッション高安) の IC 探索に再利用可能なハーネス。

## 再発防止
次に「水平線/SR で反発・ブレイク」系を提案する前に本ページを参照。swing×touch 定義は null 確定済み。別定義を試すなら IC ハーネスで先に方向性 IC を確認してから実装。
