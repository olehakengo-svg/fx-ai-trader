# SR Anti-Hunt Bounce

## Overview
- **Entry Type**: `sr_anti_hunt_bounce`
- **Category**: MR (Mean Reversion / Defensive bounce at SR)
- **Timeframe**: DT 15m
- **Status**: NEW (2026-04-27) — Shadow 5 majors 全走 (PAIR_PROMOTED 不在で OANDA は default Sentinel 0.01lot)
- **Active Pairs**: USDJPY, EURUSD, GBPUSD, EURJPY, GBPJPY (全5 majors)

## 攻めの姿勢 (CLAUDE.md 4原則)
- 「攻撃は最大の防御」「クリーンデータ蓄積が最優先」
- audit で edge 弱い pair も Shadow 走行で real-time 検証 — gatekeeping より data accumulation
- 30 trade 蓄積後に net_edge_audit / cell_edge_audit で per-pair 判定して PAIR_PROMOTED 判断

## Phase 2 Audit Findings (365d, M15, k=2.0)
| Pair | n_hunts | Wilson lower | bench WR | net_edge | trade EV (sim) | PF | Kelly |
|---|---|---|---|---|---|---|---|
| USD_JPY | 53 | 46.9% | 27.1% | +33.3% | +0.55p | 1.046 | +0.018 |
| EUR_USD | 81 | 54.6% | 24.0% | +41.5% | +0.57p | 1.060 | +0.029 |
| GBP_USD | 104 | 47.1% | 25.0% | +31.7% | +6.45p | 1.997 | +0.257 |
| EUR_JPY | 31 | 29.2% | 20.0% | +25.2% | -6.19p | 0.599 | -0.237 |
| GBP_JPY | 39 | 16.5% | 21.5% | +6.7% | -10.95p | 0.444 | -0.495 |

→ Reversal-WR としては全ペアで Wilson lower > bench (4 ペア Bonferroni 有意)
→ Trade-outcome では USD_JPY/EUR_USD/GBP_USD のみ EV>0 (sim)
→ Quarterly stability: USD_JPY のみ std<0.10 で安定、EUR/GBP_USD はやや不安定
→ **Live 検証で確定する** (Shadow data accumulation 優先)

## Signal Logic
1. ペアフィルター: 5 majors すべて
2. ATR-normalized 近接判定: `|entry - level| < 0.4 × ATR`
3. レジームフィルター: ADX < 30
4. 直近 2 本以内に hunt-style breach が**無い**
5. 反転足確認 (BUY なら Close > Open)
6. SL = level − sign × (P90_excursion + 0.5 × ATR)  ※anti-hunt placement
7. TP: 対側 SR or RR=2.0 (MIN_RR=1.5)

## Components
- `modules/sr_detector.py` — KDE + obviousness scoring (round-number, touch_count, age 統合)
- `research/edge_discovery/hunt_analyzer.py` — hunt 統計 + reversal WR
- `tools/sr_audit.py` — CLI audit
- `tools/sr_rigor_audit.py` — Wilson + Bonferroni + Quarterly + Trade-Sim audit
- `strategies/daytrade/sr_anti_hunt_bounce.py`

## Tests
- `tests/test_sr_detector.py`, `tests/test_hunt_analyzer.py`, `tests/test_sr_strategies.py`

## Related
- [[sr-liquidity-grab]] — 攻撃側
- [[index]] — Tier classification
- [[friction-analysis]] — ペア別摩擦
