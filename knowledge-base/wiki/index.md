# FX AI Trader Knowledge Base

## 🎯 最重要目標: 月利100% → 年利1,200%
**全施策の判断基準。これに寄与しない施策は後回し。**
- 現在: **DD防御0.2x** (DD=12.39%, defensive mode) → 月利47%（BT推定）
- Phase 3 (Kelly Half): 月利594%
- 詳細: **[[roadmap-v2.1]]** (DT幹+Scalp枝統合、v2.1)
- 旧: [[roadmap-v2]] (v2.0) / [[roadmap-to-100pct]] (v1)
- **最優先: クリーンデータ蓄積 → Kelly Half到達**

<!-- KB_PORTFOLIO_START -->
## Current Portfolio (auto-synced, 2026-04-15)

### ELITE_LIVE (never shadowed)
| Strategy | BT Data | Status |
|----------|---------|--------|
| [[gbp-deep-pullback]] | GBP_USD: EV=+1.064 WR=75.3% | ELITE_LIVE |
| [[session-time-bias]] | EUR_USD: EV=+0.215 WR=69.6%; GBP_USD: EV=+0.113 WR=67.1%; USD_JPY: EV=+0.580 WR=79.0% | ELITE_LIVE |
| [[trendline-sweep]] | EUR_USD: EV=+0.927 WR=80.8%; GBP_USD: EV=+0.599 WR=73.1% | ELITE_LIVE |

### PAIR_PROMOTED (SENTINEL)
| Strategy | Pairs | BT Data | Status |
|----------|-------|---------|--------|
| [[bb-squeeze-breakout]] | EUR_JPY, EUR_USD, GBP_JPY, USD_JPY | no BT data | PAIR_PROMOTED |
| [[doji-breakout]] | GBP_USD, USD_JPY | GBP_USD: EV=+0.724 WR=78.3%; USD_JPY: EV=+0.338 WR=61.9% | PAIR_PROMOTED |
| [[dt-fib-reversal]] | GBP_USD | EUR_JPY: EV=-0.199 WR=54.3%; EUR_USD: EV=+0.407 WR=80.0%; GBP_USD: EV=+0.374 WR=76.2% | PAIR_PROMOTED |
| [[ema-pullback]] | USD_JPY | no BT data | PAIR_PROMOTED |
| [[engulfing-bb]] | EUR_USD | no BT data | PAIR_PROMOTED |
| [[fib-reversal]] | EUR_USD | no BT data | PAIR_PROMOTED |
| [[london-fix-reversal]] | GBP_USD | EUR_USD: EV=+0.161 WR=66.7%; GBP_USD: EV=-0.150 WR=56.8%; USD_JPY: EV=+0.079 WR=60.9% | PAIR_PROMOTED |
| [[macdh-reversal]] | EUR_JPY, GBP_JPY | no BT data | PAIR_PROMOTED |
| [[orb-trap]] | EUR_USD, GBP_USD, USD_JPY | USD_JPY: EV=+0.866 WR=84.2% | PAIR_PROMOTED |
| [[post-news-vol]] | EUR_USD, GBP_USD | EUR_USD: EV=+0.817 WR=71.4%; GBP_USD: EV=+1.762 WR=88.5% | PAIR_PROMOTED |
| [[squeeze-release-momentum]] | EUR_USD | EUR_USD: EV=+0.656 WR=73.3% | PAIR_PROMOTED |
| [[sr-channel-reversal]] | EUR_USD | no BT data | PAIR_PROMOTED |
| [[stoch-trend-pullback]] | GBP_JPY | no BT data | PAIR_PROMOTED |
| [[vix-carry-unwind]] | USD_JPY | USD_JPY: EV=+0.212 WR=67.3% | PAIR_PROMOTED |
| [[vol-momentum-scalp]] | EUR_JPY | no BT data | PAIR_PROMOTED |
| [[vwap-mean-reversion]] | EUR_JPY, EUR_USD, GBP_JPY, GBP_USD | no BT data | PAIR_PROMOTED |
| [[xs-momentum]] | EUR_USD, GBP_USD | EUR_USD: EV=+0.225 WR=68.0%; USD_JPY: EV=+0.270 WR=68.7% | PAIR_PROMOTED |

### SHADOW (Data Collection)
| Strategy | BT Data | Notes |
|----------|---------|-------|
| [[bb-rsi-reversion]] | no BT data | SCALP_SENTINEL |
| [[dt-sr-channel-reversal]] | EUR_JPY: EV=+0.178 WR=63.8% | UNIVERSAL_SENTINEL |
| [[eurgbp-daily-mr]] | no BT data | UNIVERSAL_SENTINEL |
| [[gotobi-fix]] | no BT data | UNIVERSAL_SENTINEL |
| [[liquidity-sweep]] | no BT data | UNIVERSAL_SENTINEL |
| [[london-close-reversal]] | no BT data | UNIVERSAL_SENTINEL |
| [[trend-rebound]] | no BT data | UNIVERSAL_SENTINEL |
| [[v-reversal]] | no BT data | UNIVERSAL_SENTINEL |
| [[vol-spike-mr]] | USD_JPY: EV=+0.148 WR=64.6% | UNIVERSAL_SENTINEL |
| [[vol-surge-detector]] | no BT data | SCALP_SENTINEL |

### FORCE_DEMOTED (stopped)
| Strategy | BT Data | Status |
|----------|---------|--------|
| [[dt-bb-rsi-mr]] | EUR_USD: EV=-0.077 WR=52.0%; GBP_USD: EV=-0.135 WR=51.3%; USD_JPY: EV=-0.023 WR=54.2% | FORCE_DEMOTED |
| [[dual-sr-bounce]] | USD_JPY: EV=+0.280 WR=70.3% | FORCE_DEMOTED |
| [[ema-cross]] | no BT data | FORCE_DEMOTED |
| [[ema-ribbon-ride]] | no BT data | FORCE_DEMOTED |
| [[inducement-ob]] | no BT data | FORCE_DEMOTED |
| [[lin-reg-channel]] | no BT data | FORCE_DEMOTED |
| [[pivot-breakout]] | no BT data | FORCE_DEMOTED |
| [[sr-break-retest]] | no BT data | FORCE_DEMOTED |
| [[sr-fib-confluence]] | EUR_USD: EV=+0.103 WR=64.9%; USD_JPY: EV=+0.252 WR=67.7% | FORCE_DEMOTED |

<!-- KB_PORTFOLIO_END -->

## System State (v9.0+ / v2.1)
- Defensive mode: **0.2x** (DD=12.39%, defensive mode — v8.4以降クリーンデータ起点)
- XAU: **Stopped** (v8.4) -- post-cutoff XAU loss = -2,280pip (102% of total loss)
- FX-only post-cutoff: **-646pip (赤字)**
- Ruin probability: ~100% (Kelly=-0.18, aggregate edge negative — recalc needed with clean data)
- scalp_eurjpy: **Stopped** (v8.6) -- friction/ATR=43.6%, 構造的不可能
- scalp_5m_eur / scalp_5m_gbp: **Active** (v8.6) -- 5m摩擦改善モード
- New modes (v9.0): **daytrade_eurjpy**, **daytrade_gbpjpy**, **[[rnb-usdjpy]]** (all auto_start)
- ELITE_LIVE tier (v2.1): session_time_bias, trendline_sweep, gbp_deep_pullback
- SHADOW_MODE: **active** (env SHADOW_MODE=true)
- Massive API: **primary data source** (全6ペア×全TF)
- New strategies (v2.1): ny_close_reversal, streak_reversal, vwap_mean_reversion
- Aggregate Kelly gate: **実装済み** (v9.0) -- Kelly<0で自動ブロック
- MC ruin gate: **実装済み** (v9.0) -- 取引前に破産確率チェック
- Phase Gate API: `/api/phase-gate` (Gate 1-4条件をエンドポイントで公開)
- DSR: **実装済み** (v8.6) -- Bailey & Lopez de Prado (2014)
- BT Friction Model: **v3** (v8.7) -- Spread/SL Gate + RANGE TP + Quick-Harvest反映
- 金曜/月曜ブロック: **撤去済み** (v8.6) -- 原則#1「攻める」準拠
- GBPアジア除外: **実装済み** (v8.6)

## Key Decisions
- [[independent-audit-2026-04-10]] -- 2 audits, binding recommendations
- [[xau-stop-rationale]] -- FX profitable without XAU
- [[mfe-zero-analysis]] -- 90.6% of losses never go favorable

## Session History
- [[sessions/2026-04-15-session]] — KB broken-link修正+orphanファイル統合
- [[sessions/2026-04-14-session]] — H15検証+SENTINEL矛盾修正+QHシミュレーション+漏れ分析
- [[sessions/2026-04-13-session]] — v8.9 Equity Reset + KB全面改修(25 Phase) + 4セッションレポート + パイプライン修復
- [[sessions/2026-04-12-session]] — 6新エッジ実装+学術監査+KB構築

## Lessons Learned (間違いと教訓)
- [[lessons/index]] — **過去の間違い・修正・教訓の蓄積** (Shadow汚染, XAU歪み, BT hardcode等)
- 次のセッション開始時に必ず参照すること

## Research & Edge Discovery
- [[research/index]] -- 学術文献インデックス、研究テーマ一覧
- [[edge-pipeline]] -- エッジ仮説の評価パイプライン (6 stages)
- Active themes: [[microstructure-stop-hunting]], [[session-effects]], [[mean-reversion-regimes]]

## Data & Evaluation
- [[changelog]] -- **バージョン別変更+評価基準日タイムライン** (どの期間で評価すべきか)
- Latest snapshot: [[snapshot-2026-04-12]] (250t post-cutoff)
- Friday analysis: [[2026-04-10-friday]] (74t, FX黒字+143pip)

### Friday 4/10 Key Finding
- FX-only: **+143.4 pip (黒字)** / XAU込み: -386.6 pip
- bb_rsi instant death: **60%** (pre-v8.3: 77.6% → v8.3効果の兆候)
- stoch_trend_pullback instant death: **50%** (pre: 83% → 改善)
- fib_reversal instant death: 71% (pre: 75.9% → ほぼ変化なし)

## Links
- [[friction-analysis]] -- Per-pair friction, BEV_WR
- [[changelog]] -- Fidelity Cutoff timeline + version impact matrix
- [[leaked-items]] -- KB漏れ項目トラッキング
- [[log]] -- 作業ログ

## Other Strategies (not in portfolio)
- [[adx-trend-continuation]] / [[donchian-momentum-breakout]] / [[ema-trend-scalp]] / [[ema200-trend-reversal]]
- [[htf-false-breakout]] / [[jpy-basket-trend]] / [[london-breakout]] / [[london-ny-swing]]
- [[london-session-breakout]] / [[london-shrapnel]] / [[mtf-reversal-confluence]] / [[ny-close-reversal]]
- [[streak-reversal]] / [[tokyo-bb]] / [[tokyo-nakane-momentum]] / [[turtle-soup]]
- [[force-demoted-strategies]] -- 降格戦略の一覧と理由

## Data & Archives

### BT Results
- [[bt-120d-v3-all-pairs-2026-04-12]] / [[bt-full-audit-2026-04-12]] / [[bt-grand-audit-2026-04-12]]
- [[bt-scalp-5m-55d-2026-04-12]] / [[bt-v3-friction-model-2026-04-12]]
- [[bt-v85-all-pairs-2026-04-12]] / [[bt-v85-new-edges-2026-04-12]] / [[bt-v86-time-expansion-2026-04-12]]
- [[comprehensive-bt-scan-2026-04-14]] / [[massive-alpha-scan-2026-04-14]] / [[shadow-bt-reeval-2026-04-14]]

### Trade Logs
- [[2026-04-15-pre_tokyo]]
- [[2026-04-14-monitor]] / [[2026-04-14-pre_tokyo]] / [[2026-04-14-post_tokyo]]
- [[2026-04-14-quant-analysis]] / [[2026-04-14-detailed-quant-analysis]]
- [[2026-04-13-monitor]] / [[2026-04-13-pre_tokyo]] / [[2026-04-13-post_tokyo]] / [[2026-04-13-post_ny]]
- [[2026-04-10-friday]]
- [[analyst-memory]] / [[analyst-memory-archive]]

### Market Analysis
- [[2026-04-14-regime]] / [[2026-04-13-regime]]

### Audits
- [[2026-04-13-weekly]] / [[2026-04-13-ev-decomposition]]
- [[alpha-scan-2026-04-13]] / [[alpha-scan-2026-04-14]] / [[alpha-scan-2026-04-15]]

### Analyses
- [[auto-improvement-pipeline]] / [[bt-live-divergence]] / [[claude-harness-design]]
- [[friction-analysis]] / [[mfe-zero-analysis]] / [[system-reference]]

### Syntheses
- [[profit-projection-2026-04-12]] / [[roadmap-to-100pct]] / [[roadmap-v2]] / [[roadmap-v2.1]]
