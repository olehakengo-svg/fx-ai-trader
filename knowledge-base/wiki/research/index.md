# Research Index — 学術文献とエッジ発見

## Purpose
学術論文・市場マイクロ構造研究からFXトレーディングエッジを体系的に発見・評価・実装するためのハブ。

## Pipeline: 論文 → エッジ仮説 → 戦略実装
```
raw/papers/         → 論文の要約・メモ（原典保管）
wiki/research/      → テーマ別の研究サーベイ（統合知識）
wiki/edges/         → 実装可能なエッジ仮説（評価付き）
wiki/hypotheses/    → 実装待ちのアイデアキュー
strategies/         → コード化されたもの
```

## Active Research Themes
- [[microstructure-stop-hunting]] — SLクラスターの流動性スイープ
- [[session-effects]] — セッション開始/終了の非対称性
- [[mean-reversion-regimes]] — レジーム依存の平均回帰
- [[momentum-anomaly]] — 短期モメンタム効果
- [[order-flow-toxicity]] — 注文フロー毒性と価格影響

## Discovered Edges (Evaluation Pipeline)
See [[edge-pipeline]]

## Papers Read
| ID | Authors | Year | Title | Theme | Edge Found? |
|---|---|---|---|---|---|
| [[osler-2003]] | Osler | 2003 | Currency orders and exchange rate dynamics | [[microstructure-stop-hunting]] | YES → [[liquidity-sweep]] |
| [[kyle-1985]] | Kyle | 1985 | Continuous Auctions and Insider Trading | [[microstructure-stop-hunting]] | Supporting |
| [[bulkowski-2005]] | Bulkowski | 2005 | Encyclopedia of Chart Patterns | False breakout | YES → [[orb-trap]], [[liquidity-sweep]] |
| [[jegadeesh-titman-1993]] | Jegadeesh & Titman | 1993 | Returns to Buying Winners | [[momentum-anomaly]] | YES → [[vol-momentum-scalp]] |
| [[andersen-2003]] | Andersen et al | 2003 | Micro Effects of Macro Announcements | [[session-effects]] | YES → tokyo-nakane-momentum |
| [[baur-2010]] | Baur & McDermott | 2010 | Is Gold a Safe Haven? | Gold momentum | Applied → gold_trend_momentum (STOPPED) |
| [[lo-mackinlay-1988]] | Lo & MacKinlay | 1988 | Stock Market Prices Do Not Follow Random Walks | Short-term reversal | Supporting [[bb-rsi-reversion]] |

## Unexplored Territories (Research Queue)
- [ ] Intraday volatility patterns (Andersen & Bollerslev 1997)
- [ ] FX dealer inventory management (Lyons 1995, Bjonnes & Rime 2005)
- [ ] Carry trade unwinding dynamics (Brunnermeier et al 2008)
- [ ] Options-implied sentiment in FX (Garman-Kohlhagen framework)
- [ ] Central bank intervention detection (Neely 2005)
- [ ] Weekend gap exploitation (Bollen & Inder 2002)
- [ ] Fix-related flows beyond nakane (Evans & Lyons 2002)
