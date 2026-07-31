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

## External-Hypothesis Transition (2026-07-13)
WS3 内部母集団探索 2 周 FAIL → 外部仮説転進。スクリーン + 実証 probe: [[external-hypothesis-scan-2026-07-13]]。
- 律速 = **データモダリティ** (価格 OHLCV 枯渇。Mesfin 2026 arXiv:2605.04004 が外部で同型 falsification)。
- 採用候補: **E3 cross-asset divergence-reversion** → [[ws3-round3-crossasset-divergence-prereg-2026-07-13]] (self-LOCK)。
- 保留 (user infra 決定): E1 retail-positioning contrarian (JIFMIM 2025)。
- 第 2 次スキャン (E7–E19): [[external-hypothesis-scan-round2-2026-07-18]] — E15/E7 イベント + E12 flow 採用。
- **E20 金利差方向バイアス × テクニカル entry (user 仮説 2026-07-22)**: [[e20-rate-differential-feasibility-2026-07-22]] — **S1 条件付き採用 (S2 GO)**。政策金利差 8/8 (BIS keyless) + 2y 国債差 6/8 現行を実 fetch 確認、第 4 モダリティ (rates)。
- **EA Landscape Sweep (user 指示 2026-07-31)**: [[ea-landscape-sweep-2026-07-31]] — 「勝てている EA」13 ソース大規模調査 (31-agent、113 findings → 18 敵対的検証)。**multi-year verified の勝者は 2 アーキタイプに収斂** (ナイトスキャル MR = ブローカー回収済みで移植不能 / コモディティ三角クロス = per-position 核が未検証)。GO 2 family → 台帳 #20 commodity_cross_range_mr / #21 equity_curve_shadow_gating (queued)。副産物 = 生存率ベースレート割引関数 + THA→E7 prior 加点。

## Still Unexplored
- [x] ~~High-frequency lead-lag between FX pairs (Hasbrouck 2003)~~ → **CLOSED 2026-07-13**: OHLCV 内部 + cross-asset とも ≥1h で裁定消滅 (実証 probe、[[external-hypothesis-scan-2026-07-13]] §3)。naive の有意は Lo-MacKinlay 非同期取引 artifact
- [~] FX term structure predictability (forward rate bias) → **不能**: spot only、forward/swap curve データなし。**部分的復活 2026-07-22**: CIP proxy (国債利回り差/政策金利差、keyless 実確認) により日次粒度の carry 系構成は C1 解消 → [[e20-rate-differential-feasibility-2026-07-22]]
- [~] Machine learning ensemble (Gu, Kelly & Xiu 2020) → **原則棄却**: データ蓄積フェーズでの curve-fit + complex-gate-edge-destruction 教訓に反
- [ ] Cross-asset (equity ES→FX) divergence — E3 の rates 版で PASS≥1 なら equity へ拡張

## Templates
- [[edge-hypothesis]] -- エッジ仮説テンプレート
- [[paper-summary]] -- 論文サマリーテンプレート
