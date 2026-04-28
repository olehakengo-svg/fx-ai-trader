# SR Anti-Hunt Bounce

## Overview
- **Entry Type**: `sr_anti_hunt_bounce`
- **Category**: MR (Mean Reversion / Defensive bounce at SR)
- **Timeframe**: DT 15m
- **Status**: SHADOW_DEMOTED — R2 triggered 2026-04-28 (本番実測 EV<0 確定、SHADOW_ALWAYS から除外、enabled=True は維持)
- **Active Pairs**: USDJPY, EURUSD, GBPUSD, EURJPY, GBPJPY (全5 majors) — primary 競争通過時のみ trade 化

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

## 本番実測 (2026-04-28, 4 日, N=300 closed)

| Pair | N | WR | mean pnl | sum | sim EV | 乖離 |
|---|---:|---:|---:|---:|---:|---:|
| USD_JPY | 173 | 26% | **-1.41p** | -243.9p | +0.55p | -1.96p |
| EUR_USD | 65 | 20% | **-1.12p** | -72.7p | +0.57p | -1.69p |
| GBP_USD | 50 | 34% | +0.31p | +15.5p | +6.45p | -6.14p |
| EUR_JPY | 8 | 25% | -4.59p | -36.7p | -6.19p | +1.60p |
| GBP_JPY | 4 | 25% | -4.47p | -17.9p | -10.95p | +6.48p |
| **合計** | **300** | **26%** | **-1.19p** | **-355.7p** | — | — |

→ sim EV (Phase 2 audit) が **全 majors で実測より 1.69-6.14p 楽観**評価。BT-Live divergence 確定。
→ **GBP_USD のみ実測 EV>0** だが +0.31p で marginal、friction 1 click で消える水準。
→ R2 Fast & Reactive 警報閾値 (EV<0, N>=30) を **USDJPY/EURUSD で発動** → SHADOW_ALWAYS_STRATEGIES から除外 (2026-04-28 commit)。
→ OANDA forwarding 確認: `is_shadow=0 ∧ oanda_trade_id` で **2 件流入**。`mode=scalp_eur` で 1 件、`mode=daytrade` で 1 件。

## 教訓
- [[../lessons/lesson-shadow-always-emit-cleanup-2026-04-28]] — SHADOW_ALWAYS の無条件 emit は EV<0 戦略を**自動的にデータ蓄積汚染源**にする
- [[../lessons/lesson-data-source-production-first-2026-04-28]] — ローカル DB と本番 DB の乖離調査時は **本番優先**
- [[../decisions/sr-strategies-signal-track-2026-04-28]] — SHADOW_EMIT 経路の元設計

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
