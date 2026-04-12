# FX AI Trader Knowledge Base

## Current Portfolio (v8.4, 2026-04-12)

### Tier 1 -- Core Alpha
| Strategy | Pair | WR(post-cut) | PnL | Kelly | Status |
|----------|------|-------------|-----|-------|--------|
| [[bb-rsi-reversion]] | USD_JPY | 36.4% (N=77) | -42.2 | 0% | PAIR_PROMOTED (v8.3 confirmation candle deployed, monitoring) |
| [[orb-trap]] | USD_JPY, EUR_USD, GBP_USD | 50% (N=2) | +7.6 | insuff | PAIR_PROMOTED (BT WR=79%, N accumulating) |

### Tier 2 -- Promising (Sentinel)
| Strategy | N(post-cut) | WR | PnL | Notes |
|----------|------------|-----|-----|-------|
| [[vol-momentum-scalp]] | 10 | 80.0% | +21.6 | Highest WR, 1.0x boost |
| [[vol-surge-detector]] | 11 | 63.6% | +19.6 | |
| [[fib-reversal]] | 32 | 40.6% | +21.9 | Recovery path: N>=30 WR>=50% -> SENTINEL |
| [[stoch-trend-pullback]] | 13 | 30.8% | +163.2 | One big win skews PnL |
| [[liquidity-sweep]] | 0 | - | - | NEW: Osler 2003 stop-hunt reversal |

### Tier 4 -- Stopped
See [[force-demoted-strategies]]

## System State
- Defensive mode: 0.2x lot (DD > 5%)
- XAU: **Stopped** (v8.4) -- post-cutoff XAU loss = -2,280pip (102% of total loss)
- FX-only post-cutoff: **+96.8pip (profitable)**
- Ruin probability: 85.58% (pre-XAU-stop, expected to improve)

## Key Decisions
- [[independent-audit-2026-04-10]] -- 2 audits, binding recommendations
- [[xau-stop-rationale]] -- FX profitable without XAU
- [[mfe-zero-analysis]] -- 90.6% of losses never go favorable

## Lessons Learned (間違いと教訓)
- [[lessons/index]] — **過去の間違い・修正・教訓の蓄積** (Shadow汚染, XAU歪み, BT hardcode等)
- 次のセッション開始時に必ず参照すること

## Research & Edge Discovery
- [[research/index]] -- 学術文献インデックス、研究テーマ一覧
- [[edge-pipeline]] -- エッジ仮説の評価パイプライン (6 stages)
- Active themes: [[microstructure-stop-hunting]], [[session-effects]], [[mean-reversion-regimes]]

## Data & Evaluation
- [[changelog]] -- **バージョン別変更+評価基準日タイムライン** (どの期間で評価すべきか)
- Latest snapshot: `raw/trade-logs/snapshot-2026-04-12.md` (250t post-cutoff)
- Friday analysis: `raw/trade-logs/2026-04-10-friday.md` (74t, FX黒字+143pip)

### Friday 4/10 Key Finding
- FX-only: **+143.4 pip (黒字)** / XAU込み: -386.6 pip
- bb_rsi instant death: **60%** (pre-v8.3: 77.6% → v8.3効果の兆候)
- stoch_trend_pullback instant death: **50%** (pre: 83% → 改善)
- fib_reversal instant death: 71% (pre: 75.9% → ほぼ変化なし)

## Links
- [[friction-analysis]] -- Per-pair friction, BEV_WR
- [[changelog]] -- Fidelity Cutoff timeline + version impact matrix
