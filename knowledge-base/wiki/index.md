# FX AI Trader Knowledge Base

## 🎯 最重要目標: 月利100% → 年利1,200%
**全施策の判断基準。これに寄与しない施策は後回し。**
- 現在: **DD防御0.2x** (DD=**28.01%**, defensive mode) → 月利47%（BT推定、クリーンデータ蓄積中）
- Phase 3 (Kelly Half): 月利594%
- 詳細: **[[roadmap-v2.1]]** (DT幹+Scalp枝統合、v2.1)
- 旧: [[roadmap-v2]] (v2.0) / [[roadmap-to-100pct]] (v1)
- **最優先: クリーンデータ蓄積 → Kelly Half到達**

<!-- KB_PORTFOLIO_START -->
## Current Portfolio (auto-synced, 2026-05-18)

### ELITE_LIVE (never shadowed)
| Strategy | BT Data | Status |
|----------|---------|--------|
| [[trendline-sweep]] | EUR_USD: EV=+0.927 WR=80.8%; GBP_USD: EV=+0.599 WR=73.1% | ELITE_LIVE |

### PAIR_PROMOTED (SENTINEL)
| Strategy | Pairs | BT Data | Status |
|----------|-------|---------|--------|
| [[bb-squeeze-breakout]] | EUR_USD | no BT data | PAIR_PROMOTED |
| [[doji-breakout]] | GBP_USD, USD_JPY | GBP_USD: EV=+0.724 WR=78.3%; USD_JPY: EV=+0.338 WR=61.9% | PAIR_PROMOTED |
| [[dt-bb-rsi-mr]] | USD_JPY | EUR_USD: EV=-0.077 WR=52.0%; GBP_USD: EV=-0.135 WR=51.3%; USD_JPY: EV=-0.023 WR=54.2% | PAIR_PROMOTED |
| [[dt-sr-channel-reversal]] | EUR_JPY | EUR_JPY: EV=+0.178 WR=63.8% | PAIR_PROMOTED |
| [[ema200-trend-reversal]] | USD_JPY | EUR_USD: EV=+0.410 WR=75.0%; USD_JPY: EV=-0.183 WR=56.2% | PAIR_PROMOTED |
| [[mqe-gbpusd-fix]] | GBP_USD | no BT data | PAIR_PROMOTED |
| [[session-time-bias]] | EUR_USD | EUR_USD: EV=+0.215 WR=69.6%; GBP_USD: EV=+0.113 WR=67.1%; USD_JPY: EV=+0.580 WR=79.0% | PAIR_PROMOTED |
| [[squeeze-release-momentum]] | EUR_USD | EUR_USD: EV=+0.656 WR=73.3% | PAIR_PROMOTED |
| [[sr-fib-confluence]] | GBP_USD | EUR_USD: EV=+0.103 WR=64.9%; USD_JPY: EV=+0.252 WR=67.7% | PAIR_PROMOTED |
| [[trend-rebound]] | USD_JPY | no BT data | PAIR_PROMOTED |
| [[vix-carry-unwind]] | USD_JPY | USD_JPY: EV=+0.212 WR=67.3% | PAIR_PROMOTED |
| [[vol-momentum-scalp]] | EUR_JPY | no BT data | PAIR_PROMOTED |
| [[vsg-jpy-reversal]] | EUR_JPY | no BT data | PAIR_PROMOTED |
| [[wick-imbalance-reversion]] | GBP_USD | no BT data | PAIR_PROMOTED |
| [[xs-momentum]] | EUR_USD, GBP_USD | EUR_USD: EV=+0.225 WR=68.0%; USD_JPY: EV=+0.270 WR=68.7% | PAIR_PROMOTED |
| [[xs-momentum-rsi]] | USD_JPY | no BT data | PAIR_PROMOTED |

### SHADOW (Data Collection)
| Strategy | BT Data | Notes |
|----------|---------|-------|
| [[bb-rsi-ema-aligned]] | no BT data | SCALP_SENTINEL |
| [[bb-rsi-reversion]] | no BT data | SCALP_SENTINEL |
| [[dt-fib-reversal]] | EUR_JPY: EV=-0.199 WR=54.3%; EUR_USD: EV=+0.407 WR=80.0%; GBP_USD: EV=+0.374 WR=76.2% | UNIVERSAL_SENTINEL |
| [[eurgbp-daily-mr]] | no BT data | UNIVERSAL_SENTINEL |
| [[gbp-deep-pullback]] | GBP_USD: EV=+1.064 WR=75.3% | LOT_BOOST (not sentinel/elite) |
| [[gotobi-fix]] | no BT data | UNIVERSAL_SENTINEL |
| [[htf-false-breakout]] | EUR_USD: EV=+0.352 WR=80.0%; GBP_USD: EV=+0.552 WR=75.0%; USD_JPY: EV=+0.660 WR=80.0% | LOT_BOOST (not sentinel/elite) |
| [[liquidity-sweep]] | no BT data | UNIVERSAL_SENTINEL |
| [[london-close-reversal]] | no BT data | UNIVERSAL_SENTINEL |
| [[london-close-reversal-v2]] | no BT data | UNIVERSAL_SENTINEL |
| [[london-fix-reversal]] | EUR_USD: EV=+0.161 WR=66.7%; GBP_USD: EV=-0.150 WR=56.8%; USD_JPY: EV=+0.079 WR=60.9% | LOT_BOOST (not sentinel/elite) |
| [[london-ny-swing]] | GBP_USD: EV=+0.362 WR=72.7% | LOT_BOOST (not sentinel/elite) |
| [[ma-mr-hybrid]] | no BT data | SCALP_SENTINEL |
| [[ma-regime-switch]] | no BT data | SCALP_SENTINEL |
| [[ma-trend-perfect]] | no BT data | SCALP_SENTINEL |
| [[macd-rsi-pullback]] | no BT data | UNIVERSAL_SENTINEL |
| [[mtf-counter-trend-scalp]] | no BT data | SCALP_SENTINEL |
| [[mtf-regime-range-cascade-scalp]] | no BT data | SCALP_SENTINEL |
| [[mtf-regime-trend-cascade-scalp]] | no BT data | SCALP_SENTINEL |
| [[mtf-reversal-confluence]] | no BT data | LOT_BOOST (not sentinel/elite) |
| [[mtf-trend-follow-scalp]] | no BT data | SCALP_SENTINEL |
| [[pd-eurjpy-h20-bbpb3-sell]] | no BT data | UNIVERSAL_SENTINEL |
| [[price-shock-reversion]] | no BT data | UNIVERSAL_SENTINEL |
| [[sr-weighted-bounce]] | no BT data | UNIVERSAL_SENTINEL |
| [[sr-weighted-break]] | no BT data | UNIVERSAL_SENTINEL |
| [[streak-reversal]] | no BT data | shadow only |
| [[tokyo-range-breakout-up]] | no BT data | LOT_BOOST (not sentinel/elite) |
| [[turtle-soup]] | GBP_USD: EV=+0.386 WR=69.7% | LOT_BOOST (not sentinel/elite) |
| [[vol-spike-mr]] | USD_JPY: EV=+0.148 WR=64.6% | UNIVERSAL_SENTINEL |
| [[vol-surge-detector]] | no BT data | SCALP_SENTINEL |

### FORCE_DEMOTED (stopped)
| Strategy | BT Data | Status |
|----------|---------|--------|
| [[atr-regime-break]] | no BT data | FORCE_DEMOTED |
| [[donchian-momentum-breakout]] | no BT data | FORCE_DEMOTED |
| [[ema-cross]] | no BT data | FORCE_DEMOTED |
| [[ema-pullback]] | no BT data | FORCE_DEMOTED |
| [[ema-ribbon-ride]] | no BT data | FORCE_DEMOTED |
| [[ema-trend-scalp]] | no BT data | FORCE_DEMOTED |
| [[engulfing-bb]] | no BT data | FORCE_DEMOTED |
| [[fib-reversal]] | no BT data | FORCE_DEMOTED |
| [[inducement-ob]] | no BT data | FORCE_DEMOTED |
| [[intraday-seasonality]] | no BT data | FORCE_DEMOTED |
| [[lin-reg-channel]] | no BT data | FORCE_DEMOTED |
| [[macdh-reversal]] | no BT data | FORCE_DEMOTED |
| [[ob-retest]] | no BT data | FORCE_DEMOTED |
| [[orb-trap]] | USD_JPY: EV=+0.866 WR=84.2% | FORCE_DEMOTED |
| [[post-news-vol]] | EUR_USD: EV=+0.817 WR=71.4%; GBP_USD: EV=+1.762 WR=88.5% | FORCE_DEMOTED |
| [[price-shock-rev-aud-jpy-h1-long]] | no BT data | FORCE_DEMOTED |
| [[price-shock-rev-eur-aud-h1-long]] | no BT data | FORCE_DEMOTED |
| [[price-shock-rev-eur-gbp-h1-long]] | no BT data | FORCE_DEMOTED |
| [[price-shock-rev-nzd-jpy-h1-long]] | no BT data | FORCE_DEMOTED |
| [[price-shock-rev-usd-cad-h1-long]] | no BT data | FORCE_DEMOTED |
| [[sr-break-retest]] | no BT data | FORCE_DEMOTED |
| [[sr-channel-reversal]] | no BT data | FORCE_DEMOTED |
| [[stoch-trend-pullback]] | no BT data | FORCE_DEMOTED |
| [[v-reversal]] | no BT data | FORCE_DEMOTED |
| [[vwap-mean-reversion]] | no BT data | FORCE_DEMOTED |

<!-- KB_PORTFOLIO_END -->

## System State (v9.5 / v2.1)
- Defensive mode: **0.2x** (DD=**42.21%** / 422.1pip ⚠️⚠️, defensive mode — Render API 2026-05-07 wiki-daily-update)
- XAU: **Stopped** (v8.4) -- post-cutoff XAU loss = -2,280pip (102% of total loss)
- FX-only post-cutoff (2026-04-08〜) — **2026-05-07 wiki-daily-update** (risk API gross, includes shadow):
  - Total N=530, WR=38.5%, EV=-0.78, PnL=-414.2pip (gross: shadow + live combined)
  - **TRUE_LIVE** (`is_shadow=0 AND oanda_trade_id != ''`) SSOT — 2026-05-03 実測: **N=371** (incl BE) / **346** (WIN/LOSS), WR=39.89%, EV=-0.686, PnL=-254.6pip (see [[aggregate-kelly-decomposition-2026-05-03-corrigendum]])
  - FLAG_DRIFT (`is_shadow=0` だが OANDA未送信): N=140, WR=32.86%, PnL=-132.4pip (`raw/audits/oanda-passthrough-gap-2026-05-03.md` 由来 write-path bug)
  - SHADOW (`is_shadow=1`): N=3,819, WR=23.72%, PnL=-4,985.6pip — **Live 判断には混入禁止** (memory `feedback_live_vs_shadow_strict_separation`)
  - 旧記載 "N=29 (`oanda_trade_id != ''`)" は **誤り** — 実態は `mode='daytrade'` only サブセット、SUPERSEDED by [[aggregate-kelly-decomposition-2026-05-03-corrigendum]]
- Ruin probability: **2.08%** ⚠️ (MC 5,000 sims, N=300 forward — Render API 2026-05-07; was 1.88% on 2026-05-03)
- Aggregate Kelly: **0.0** (raw edge=-17.06%; TRUE_LIVE SSOT: N=371 raw=-0.69) — Bonferroni-powered cell-level demote が実行可能、N=371 で Gate 1 unlock 経路が再開
- Aggregate Kelly decomposition 2026-05-03: 旧 doc は SUPERSEDED。新 SSOT: [[aggregate-kelly-decomposition-2026-05-03-corrigendum]] (TRUE_LIVE Strategy × Pair 出血ランキング、ELITE_LIVE `session_time_bias × GBP_USD` 出血特定)
- Last updated: 2026-05-07 (wiki-daily-update auto); prev: 2026-05-03 (Render API direct)
- scalp_eurjpy: **Stopped** (v8.6) -- friction/ATR=43.6%, 構造的不可能
- scalp_5m_eur / scalp_5m_gbp: **Active** (v8.6) -- 5m摩擦改善モード
- New modes (v9.0): **daytrade_eurjpy**, **daytrade_gbpjpy**, **[[rnb-usdjpy]]** (all auto_start)
- Phase B-1 Shadow candidate pair slots: **USD_CAD** (Tier 1 #3 / Phase B Wave 1 candidate), **USD_CHF** (Tier 3 WATCH / Phase B Wave 1 candidate), **AUD_JPY**, **NZD_JPY**, **AUD_USD**, **NZD_USD**, **EUR_AUD** (`price_shock_reversion`, surface-only; Live promotion disabled in this task)
- ELITE_LIVE tier: **trendline_sweep** only (per tier-master.md 2026-05-07; session_time_bias=PAIR_PROMOTED EUR_USD, gbp_deep_pullback=PAIR_DEMOTED GBP_USD)
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
- **MTF Regime Engine**: **active** (v9.2.1) — D1×H4×H1 階層 labeler, shadow monitor
- **Strategy-aware MTF alignment**: **active** (v9.3 P0) — 4 family (TF/MR/BO/SE) × regime
- **REGIME_ADAPTIVE_FAMILY**: **active** (v9.3 P2) — bb_rsi/fib の regime 別 family override
- **A/B Gate Routing**: **active** (v9.3 Phase D) — hash-based 50/50 (mtf_gated / label_only)
  - Group A conflict → LIVE→SHADOW downgrade (soft gate)
  - 5-7日で N≥500/group, 30日で p<0.05 検出想定

## Key Decisions
- [[complex-gate-edge-destruction-pattern-2026-05-03]] -- **🎯 最新 (2026-05-03)** Complex gate edge-destruction pattern — MTF cascade / HMM / multi-condition gate は BT で映えても Live/OOS で edge 破壊 (4例再現)、Wave 設計に simple-first 原則導入 (rule:R3)
- [[aggregate-kelly-decomposition-2026-05-03-corrigendum]] -- **🎯 SSOT (rev2)** TRUE_LIVE bucket only N=371、Strategy×Pair 出血ランキング再特定、ELITE_LIVE `session_time_bias × GBP_USD` 出血特定、surgical demote 経路は **再開可能**
- [[aggregate-kelly-decomposition-2026-05-03]] -- (2026-05-03 旧) 数値部分は corrigendum で SUPERSEDED (N=29 は mode='daytrade' subset 誤集計)
- [[regime-cascade-empirical-redesign-2026-04-30]] -- Regime Cascade 実測再設計 — v1 教科書仮説を否定、binary moderate_trend gate 採用、range cascade 停止 (rule:R1+R3)
- [[strategies-page-audit-followup-2026-04-30]] -- B1/B3 訂正: ELITE bypass 不要・FORCE_DEMOTED Live発火0件確認。direction_cells API 追加
- [[shadow-deep-mining-2026-04-24]] -- Shadow 7次元診断 → Scenario A 追認 / bb_rsi・ema・sr_channel の MR 系は現行 regime で dead (friction>edge)
- [[pre-registration-mafe-dynamic-exit-2026-04-24]] -- MAFE-based Time-Decay Exit の forward-usable pre-reg (target: bb_rsi_reversion, 48 param cells, Bonferroni α=1.04e-3)
- [[external-audit-2026-04-24]] -- **🎯 最新監査** Gap/Over-eng/Resource/Must-Do-Don't + surgery 結果 (§5 Action Items tracked)
- [[audit-completion-protocol]] -- 監査後の completion 追跡フロー (session-start で §5 確認必須)
- [[independent-audit-2026-04-10]] -- 2 audits, binding recommendations
- [[xau-stop-rationale]] -- FX profitable without XAU
- [[mfe-zero-analysis]] -- 90.6% of losses never go favorable
- [[defensive-mode-unwind-rule]] -- DD防御 0.2x 解除条件（段階A自動/B品質ゲート/C手動）
- [[negative-strategy-stopping-rule]] -- Shadow 止血ルール Level A/B/C（Bayesian 基準）

## Session History
- **2026-05-07 wiki-daily-update** — N=530 total (shadow+live, post-2026-04-08), WR=38.5%, PnL=-414.2pip (gross), DD=42.21%⚠️ (+1.56pp from 2026-05-03), ruin=2.08%, live fills=4 (GBP_USD×3 + USD_JPY×1 daytrade, OANDA#383016-383039), total system=5,295. bb_rsi N=187 -52.7pip, session_time_bias N=9 WR=22.2% -43.4pip⚠️, vix_carry_unwind N=8 -41.5pip⚠️
- **2026-04-30 session** — Regime Cascade v2.1 実装+commit (binary moderate_trend, L3 slim, SL floor). direction_cells API 追加. B1/B3 監査訂正. 2コミット push
- **2026-04-29 wiki-daily-update** — N=286, WR=38.1%, PnL=-228.6pip, DD=34.76% ⚠️ (from 32.32%), ruin=1.72% (from 2.72%), vol_momentum_scalp唯一正Kelly (+7.78%), live fills=0 (全shadow_tracking), latest OANDA ID=3590
- **2026-04-24 wiki-daily-update** — N=259, WR=39.0%, PnL=-215.0pip, DD=32.32% ⚠️ (from 28.01%), ruin=2.72% ⚠️ (from 0.78%), vwap_mr N=10 -47.7pip OANDA kill-switch適用, live fills=1 (GBP_USD bb_rsi #378534)
- **2026-04-23 wiki-daily-update** — N=255, WR=39.6%, PnL=-171.9pip, DD=28.01%, ruin=0.78% ⚠️ (from 0.04%), vwap_mr N=8 -17.5pip継続悪化, live fills=0
- [[sessions/quant-edge-scan-2026-04-23]] — **🎯 最新** Session/Horizon/Regime 3軸エッジスキャン (T3 Tokyo Range Breakout 確認 / L1 OFI MR / edge_lab T1-T2-D1-R1-S3 実行)
- [[sessions/handover-2026-04-22]] — **🎯 次セッション引き継ぎ** 2026-04-22 総括: TP-hit 分析 + Scalp vwap_mr バグ修正 + Exposure/Resend fix + OSS 横断調査/qlib/pybroker 転用
- [[sessions/handover-tp-hit-quant-analysis-2026-04-21]] — **🎯 次セッション引き継ぎ #2** TP-hit 698件 quant 分析 (family-wise noise 結論、3副次発見: score 予測力ゼロ / confidence 負相関 / spread edge 有意)
- [[sessions/2026-04-22-session]] — TP-hit quant 分析 (research only, 実装なし) + KB ドキュメンテーション強化
- [[sessions/handover-shadow-deep-analysis-2026-04-21]] — **🎯 次セッション引き継ぎ** Shadow 全戦略 TP/SL 分析 + 戦略分割
- [[sessions/2026-04-21-session]] — Attack A (bb_squeeze×USD_JPY PAIR_PROMOTED) + Attack B (negative戦略止血条件) + Tier1 BT validation + Quant深部検証
- [[sessions/2026-04-20-session]] — Sentinel score_gate bypass (P1) + N measurement fix (P3) + KB drift fix (P4) + shadow baseline analysis + resend-shadow-leak fix
- [[sessions/2026-04-17-session]] — conditional edge estimand framework + KB整合修正
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
- [[bt-live-divergence-scan-2026-04-22]] / [[bt-live-divergence-v3-full-stack-2026-04-22]] — 365d JPY DT + 180d Scalp fresh BT

### Trade Logs
- [[2026-05-07]] — daily summary (auto-generated 2026-05-07)
- [[2026-04-29]] — daily summary (auto-generated 2026-04-29)
- ~~[[2026-04-27]]~~ — daily summary (auto-generated 2026-04-27)
- [[2026-04-27-monitor]] / [[2026-04-27-pre_tokyo]] / [[2026-04-27-post_tokyo]]
- [[2026-04-24]] — daily summary (auto-generated 2026-04-24)
- [[2026-04-23]] — daily summary (auto-generated 2026-04-23)
- [[2026-04-22]] — daily summary (auto-generated 2026-04-22)
- [[2026-04-21]] — daily summary (auto-generated 2026-04-21)
- [[2026-04-21-monitor]] / [[2026-04-21-pre_tokyo]] / [[2026-04-21-post_tokyo]]
- [[2026-04-20]] — daily summary (auto-generated 2026-04-20)
- [[2026-04-20-monitor]] / [[2026-04-20-post_tokyo]]
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
- [[conditional-edge-estimand-2026-04-17]] / [[portfolio-balance-audit-2026-04-17]] / [[regime-tag-validation-2026-04-17]]
- [[mtf-regime-validation-2026-04-17]] — MTF engine + Phase A-E (strategy-aware alignment, P0 forensics, A/B gate, REGIME_ADAPTIVE)
- [[edge-matrix-2026-04-23]] — Session × Horizon × Regime quant edge hypothesis map (T1-T4/L1-L3/N1-N3/S1-S4/D1-D3/R1-R3/TR1-TR4)
- [[spread-at-entry-confounding-2026-04-23]] — handover p=1.9e-5 edge が Simpson's paradox 由来と判定 (INVALIDATED)
- [[score-predictive-power-2026-04-23]] — score aggregate p=0.55 noise 確認 + bb_rsi_reversion で inverse 傾向 (N>=200 で再検証)
- [[phase2a-deploy-status-2026-04-23]] — Phase 2a 3 commit deploy 確認 + Phase 2a.1 未配線 (registry 定義のみ、MTF gate 未変更). holdout 2026-05-07 まで保留

### Syntheses
- [[profit-projection-2026-04-12]] / [[roadmap-to-100pct]] / [[roadmap-v2]] / [[roadmap-v2.1]]
