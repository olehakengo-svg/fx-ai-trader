# FX AI Trader Knowledge Base

## 🎯 最重要目標: 月利100% → 年利1,200%
**全施策の判断基準。これに寄与しない施策は後回し。**
- 現在: **DD防御0.2x** (DD=12.39%, defensive mode) → 月利47%（BT推定）
- Phase 3 (Kelly Half): 月利594%
- 詳細: **[[roadmap-v2.1]]** (DT幹+Scalp枝統合、v2.1)
- 旧: [[roadmap-v2]] (v2.0) / [[roadmap-to-100pct]] (v1)
- **最優先: クリーンデータ蓄積 → Kelly Half到達**

## Current Portfolio (v8.9, 2026-04-13)

### Tier 1 -- Core Alpha
| Strategy | Pair | WR(post-cut) | PnL | Kelly | Status |
|----------|------|-------------|-----|-------|--------|
| ~~[[bb-rsi-reversion]]~~ | ~~USD_JPY~~ | 38.2% (N=76) | -21.0 | -5.5% | **PAIR_DEMOTED** (v8.9: EV=-0.28確定, Kelly=-5.5%) → Tier 3 |
| [[orb-trap]] | USD_JPY, EUR_USD, GBP_USD | 50% (N=2) | +7.6 | insuff | PAIR_PROMOTED (BT WR=79%, N accumulating) |
| [[session-time-bias]] | USD_JPY, EUR_USD, GBP_USD | — | — | — | PAIR_PROMOTED (v8.6, BT WR=69-77%, 学術★★★★★, score 5.5 fix deployed, awaiting first live fire) |
| [[london-fix-reversal]] | GBP_USD | — | — | — | PAIR_PROMOTED (v8.6, BT WR=75%, 学術★★★★★) |

### Tier 2 -- Promising (Sentinel)
| Strategy | N(post-cut) | WR | PnL | Notes |
|----------|------------|-----|-----|-------|
| [[vol-momentum-scalp]] | 10 | 80.0% | +21.6 | Highest WR, 1.0x boost |
| [[vol-surge-detector]] | 15 | 46.7% | +1.9 | WR低下中 (was 63.6% at N=11) |
| [[fib-reversal]] | 32 | 40.6% | +21.9 | Recovery path: N>=30 WR>=50% -> SENTINEL |
| ~~[[stoch-trend-pullback]]~~ | 19 | 31.6% | -18.5 | **FORCE_DEMOTED** (v8.9: EV=-0.97全ペア負) → Tier 3 |
| [[liquidity-sweep]] | 0 | - | - | Osler 2003 stop-hunt reversal |
| [[vol-spike-mr]] | 0 | - | - | v8.8: 3x range spike fade (BT JPY PF=1.92★) |
| [[doji-breakout]] | 0 | - | - | v8.8: 3連続doji breakout follow |
| [[gotobi-fix]] | 0 | - | - | v8.5: 五十日仲値BUY (発火窓=月6日) |
| [[vix-carry-unwind]] | 0 | - | - | v8.5: VIX急騰→JPY long (低頻度高インパクト) |
| [[xs-momentum-dispersion]] | 0 | - | - | v8.5: 通貨モメンタム+分散フィルター |
| [[hmm-regime-overlay]] | 0 | - | - | v8.5: 2状態HMMレジーム (防御オーバーレイ) |

### Tier 3 -- PAIR_DEMOTED (特定ペアで停止)
| Strategy | Pair | Reason |
|----------|------|--------|
| london_fix_reversal | USD_JPY | v8.6: BT WR=28.6% EV=-0.752 |
| xs_momentum | USD_JPY | v8.6: BT EV=-0.129 |
| post_news_vol | USD_JPY | v8.8: 120d BT WR=0% EV=-3.706 |
| ema200_trend_reversal | USD_JPY | v8.8: 120d BT WR=0% EV=-1.887 |
| dt_bb_rsi_mr | EUR_USD | v8.9: N=7 WR=14.3% EV=-4.09 FORCE_DEMOTED |

### Tier 4 -- Stopped
See [[force-demoted-strategies]]

## System State (v8.9)
- Defensive mode: **0.2x** (DD=12.39%, defensive mode — v8.4以降クリーンデータ起点)
- XAU: **Stopped** (v8.4) -- post-cutoff XAU loss = -2,280pip (102% of total loss)
- FX-only post-cutoff: **-646pip (赤字)**
- Ruin probability: ~100% (Kelly=-0.18, aggregate edge negative — recalc needed with clean data)
- scalp_eurjpy: **Stopped** (v8.6) -- friction/ATR=43.6%, 構造的不可能
- scalp_5m_eur / scalp_5m_gbp: **Active** (v8.6) -- 5m摩擦改善モード
- DSR: **実装済み** (v8.6) -- Bailey & Lopez de Prado (2014)
- BT Friction Model: **v3** (v8.7) -- Spread/SL Gate + RANGE TP + Quick-Harvest反映
- 金曜/月曜ブロック: **撤去済み** (v8.6) -- 原則#1「攻める」準拠
- GBPアジア除外: **実装済み** (v8.6)

## Key Decisions
- [[independent-audit-2026-04-10]] -- 2 audits, binding recommendations
- [[xau-stop-rationale]] -- FX profitable without XAU
- [[mfe-zero-analysis]] -- 90.6% of losses never go favorable

## Session History
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
