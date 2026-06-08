# Session Time Bias — セッション時刻バイアス

## Stage: UNIVERSAL_SENTINEL (2026-05-01 audit P0-8 phase 1)

> **2026-05-01 demote**: ELITE_LIVE → UNIVERSAL_SENTINEL (Live N=9 WR=22.2% PnL=-43.4p; pre-reg LOCK 撤回は別 PR)

### Historical (pre-demote, 365d BT)

### 365-day BT Scan Results
| Pair | EV | WR | N |
|------|----|----|---|
| USD_JPY | +0.580 | 79.0% | 157 |
| EUR_USD | +0.215 | 69.6% | 566 |
| GBP_USD | +0.113 | 67.1% | 516 |

## Hypothesis
通貨は自国のトレーディング時間帯に減価する傾向がある（Breedon & Ranaldo 2013）。東京時間にJPY売り、ロンドン時間にGBP売りの方向性ドリフトが存在。

## Academic Backing
| Paper | Finding | Confidence |
|-------|---------|-----------|
| [[breedon-ranaldo-2013]] | 自国時間帯に通貨が減価。21年間9通貨ペアで統計的に高度に有意 | ★★★★★ |

## Quantitative Definition
```python
# Entry: セッションオープン付近で自国通貨SELL
# Tokyo (UTC 0): SELL JPY → BUY USD/JPY
# London (UTC 7): SELL GBP → BUY EUR/GBP or SELL GBP/USD
# Exit: 次のセッション移行前（4-8時間保有）
# SL: ATR(1H) × 1.5
# TP: ATR(1H) × 2.0
```

## Friction Viability
| Pair | Friction(RT) | Est. SL | Friction/SL | BEV_WR | Margin |
|------|-------------|---------|-------------|--------|--------|
| USD_JPY | 2.14pip | ~25pip | 8.6% | ~33% | 研究値で十分 |

## Correlation with Existing
| Strategy | Expected r | Basis |
|----------|-----------|-------|
| orb_trap | 低〜中 | 時間帯重複あるが、ORフェイクアウト vs 方向性ドリフトで別メカニズム |
| bb_rsi | 低 | MR vs ドリフト、独立 |

## Implementation Path
- [x] Stage 1: DISCOVERED (2026-04-12)
- [x] Stage 2: FORMULATED (2026-04-12)
- [x] Stage 3: BACKTESTED — BT WR=69-77% (2026-04-12)
- [x] Stage 4: SENTINEL (v8.5, 2026-04-12)
- [x] Stage 6: PROMOTED (v8.6, 2026-04-12) — 3ペア PAIR_PROMOTED
- [x] Stage 7: ELITE_LIVE (2026-04-17) — 全ペア自動通過、PAIR_PROMOTED重複は整理

## Live Performance (post-cutoff, 2026-04-08〜)
| Strategy | Pairs | N | WR | PnL |
|---|---|---|---|---|
| session_time_bias | all | 4 | 0.0% | -25.8 pip |

⚠️ WR=0% (N=4) vs BT WR=67-79%. N below judgment threshold (min N=10). Monitor closely.
Data source: /api/demo/stats?date_from=2026-04-08 (2026-04-20)

## Key Advantage
**実装複雑度 1/5** — 時刻ルールのみ。最もシンプルな新エッジ。

## Related
- [[session-effects]]
- [[research/index]]

## 2026-06-08 Edge Cell Filter Redesign

**Status**: implemented per `docs/superpowers/specs/2026-06-08-session-time-bias-bb-rsi-edge-cell-redesign-design.md`

**Filter** (applied at evaluate() entry):
- ON: LDN session (UTC 07-13) × ADX[15,30] × dist_EMA200<0.5%
- OFF: ASN/NY/LATE, ADX outside [15,30], price >0.5% from EMA200

**SIZE lever (Candidate.lot_multiplier)**:
- CORE 1.5x: + ADX[25,30] OR regime=RANGE
- EDGE 1.0x: otherwise (when filter passes)

**Empirical baseline (40-day shadow data, N=396)**:
- baseline (no filter): WR 30.1%, mean -2.06p, sum -816p
- proposed (filter applied): in-sample N=126, WR 45.2%, mean +0.93p, sum +117p
- swing: +933p (in-sample)

**OOS expectation**: probability-weighted EV +¥30-50k/月 (5k unit baseline lot).

**Rollback**: `SESSION_TIME_BIAS_CELL_FILTER_V1=0` env flag bypasses filter.

**30-day reconciliation target (2026-07-08)**: N>=60, mean>=+0.3p, Wilson_lo>=0.35.
