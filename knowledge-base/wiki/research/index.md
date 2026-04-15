# Research Index — 学術文献とエッジ発見

## Purpose
学術論文・市場マイクロ構造研究からFXトレーディングエッジを体系的に発見・評価・実装するためのハブ。

## Pipeline: 論文 → エッジ仮説 → 戦略実装
```
raw/papers/         → 論文の要約・メモ（原典保管）
wiki/research/      → テーマ別の研究サーベイ（統合知識）
wiki/strategies/    → 戦略詳細 + エッジ仮説 + パイプライン
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

## Papers Read (25 papers, 2026-04-12 sweep)

### Pre-existing (7 papers)
| Authors | Year | Title | Theme | Edge |
|---|---|---|---|---|
| Osler | 2003 | Currency orders and exchange rate dynamics | [[microstructure-stop-hunting]] | → [[liquidity-sweep]] |
| Kyle | 1985 | Continuous Auctions and Insider Trading | [[microstructure-stop-hunting]] | Supporting |
| Bulkowski | 2005 | Encyclopedia of Chart Patterns | False breakout | → [[orb-trap]] |
| Jegadeesh & Titman | 1993 | Returns to Buying Winners | [[momentum-anomaly]] | → [[vol-momentum-scalp]] |
| Andersen et al | 2003 | Micro Effects of Macro Announcements | [[session-effects]] | → tokyo_nakane |
| Baur & McDermott | 2010 | Is Gold a Safe Haven? | Gold | → gold_trend (STOPPED) |
| Lo & MacKinlay | 1988 | Stock Prices Do Not Follow Random Walks | Reversal | → [[bb-rsi-reversion]] |

### 2026-04-12 Sweep — Microstructure (11 papers)
| Authors | Year | Title | Edge | Priority |
|---|---|---|---|---|
| **Breedon & Ranaldo** | **2013** | Intraday Patterns in FX Returns | → [[session-time-bias]] | **★★★★★** |
| **Krohn, Mueller & Whelan** | **2024** | FX Fixings Returns around the Clock | → [[london-fix-reversal]] | **★★★★★** |
| **Brunnermeier, Nagel & Pedersen** | **2009** | Carry Trades and Currency Crashes | → [[vix-carry-unwind]] | **★★★★** |
| **Menkhoff et al** | **2012** | Carry Trades and Global FX Volatility | → vol regime switch | **★★★★★** |
| Evans & Lyons | 2002 | Order Flow and Exchange Rate Dynamics | Theoretical (need flow data) | ★★ |
| Bjonnes & Rime | 2004 | Dealer Behavior in FX | Theoretical | ★ |
| IMF WP/19/136 | 2019 | Anatomy of Sudden Yen Appreciations | Supporting timing | ★★★ |
| Ito & Yabu | 2007 | What Prompts Japan to Intervene | Conditional: level trade | ★★ |
| Chaboud et al | 2014 | Rise of the Machines | Supporting theory | ★★ |
| Fratzscher et al | 2019 | Systematic Intervention Detection | NLP needed → reject | ★ |
| Menkhoff et al | 2012b | Currency Momentum Strategies | → [[xs-momentum-dispersion]] | ★★★★ |

### 2026-04-12 Sweep — Anomalies (8 papers)
| Authors | Year | Title | Edge | Priority |
|---|---|---|---|---|
| **Bessho et al** | **2023** | Gotobi Anomaly | → [[gotobi-fix]] | **★★★★★** |
| **Ito & Yamada** | **2017** | Puzzles in Tokyo Fixing | → [[gotobi-fix]] supporting | **★★★★** |
| **Melvin & Prins** | **2015** | Equity Hedging at London Fix | → month-end rebal | **★★★★** |
| **Andersen & Bollerslev** | **1998** | DM-Dollar Intraday Volatility | → U-shape vol | **★★★★** |
| **Barardehi & Bernhardt** | **2025** | Revisiting U-Shaped Vol | → orb_trap enhance | **★★★** |
| Harvey et al | 2025 | Unintended Consequences of Rebalancing | month-end | ★★★ |
| Yamori & Kurihara | 2004 | Day-of-Week Effect in FX | Weak (post-1990s) | ★ |
| Hsieh & Kleidon | 1996 | Bid-Ask Spreads in FX | Execution timing | ★★★ |

### 2026-04-12 Sweep — Advanced (6 papers)
| Authors | Year | Title | Edge | Priority |
|---|---|---|---|---|
| **Eriksen** | **2019** | XS Return Dispersion + Momentum | → [[xs-momentum-dispersion]] | **★★★★** |
| **Iwanaga & Sakemoto** | **2024** | Cross-Momentum: Equity×Currency | Cross-asset signal | **★★★** |
| Della Corte et al | 2016 | Volatility Risk Premia | EVZ/JYVIX proxy possible | ★★★ |
| HMM studies | 2024 | Regime Detection via HMM | → [[hmm-regime-overlay]] | **★★★** |
| Bossens et al | 2019 | Vol Smile Forecasting | **REJECT** (institutional data) | ✗ |
| Jia et al | 2024 | Info Spillover via ML | **REJECT** (NLP infra) | ✗ |

## Explored Territories (updated 2026-04-12)
- [x] Intraday volatility patterns → Andersen & Bollerslev 1998 ★★★★
- [x] FX dealer inventory → Bjonnes & Rime 2004 (theoretical only)
- [x] Carry trade unwinding → Brunnermeier 2009 ★★★★
- [x] Central bank intervention → Ito & Yabu 2007 (conditional)
- [x] Fix-related flows → Krohn 2024, Bessho 2023 ★★★★★
- [x] Options-implied sentiment → Della Corte 2016 (partial)
- [x] Weekend gap → Yamori & Kurihara 2004 (weak effect)

## Still Unexplored
- [ ] High-frequency lead-lag between FX pairs (Hasbrouck 2003 framework)
- [ ] FX term structure predictability (forward rate bias decomposition)
- [ ] Machine learning ensemble for FX (Gu, Kelly & Xiu 2020 framework applied to FX)

## Templates
- [[edge-hypothesis]] -- エッジ仮説テンプレート
- [[paper-summary]] -- 論文サマリーテンプレート
