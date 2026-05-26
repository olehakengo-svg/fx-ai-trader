# Pivot Detector v2.5

## Overview
- **Entry Type**: `pivot_detector_v2_5`
- **Category**: MR (Mean Reversion)
- **Timeframe**: DT 15m
- **Status**: PAIR_PROMOTED (EUR_USD) — LIVE intentional exception (rule:R1-EXCEPTION, 2026-05-26)
- **Active Pairs**: EUR_USD only (TV in-house validation; MASSIVE multi-pair BT 未実施)
- **Lot**: 1000u default (no PAIR_LOT_BOOST)
- **Side-channel**: LIVE_PROMOTE_LOSERS (score ~4-5 loses select_best to higher-score primaries)

---

## Hypothesis

EUR_USD M15 において、BB 下限を下抜けつつ RSI 30 以下に達し、EMA(25) を下回り、Volume spike (z≥1.5) が起き、London/NY session 内である全条件成立時、価格は短期 mean-reversion で反発する。これは複合的な exhaustion signal で false positive をフィルタする mean-reversion edge。

References:
- Bollinger 1992 — BB %B mean reversion
- Wilder 1978 — RSI oversold
- Lo & MacKinlay 1988 — short-term reversal

---

## Entry conditions (ALL required)

| Condition | Threshold |
|---|---|
| Pair | EUR_USD |
| TF | M15 |
| Session | UTC hour ∈ [7, 21] |
| BB lower breach | `Low(bar) ≤ BB_lower(20, 2σ)` |
| RSI oversold | `RSI(14) ≤ 30` |
| Downtrend context | `Close(bar) < EMA(25)` |
| Volume spike | `vol_z(20) ≥ 1.5` |

Direction: **LONG only** (Short は TV で PF 0.884 = 負け)。

---

## Exit

| Component | Value |
|---|---|
| Hard stop | `entry − 3 × ATR(14)` |
| Take profit | `entry + 6 × ATR(14)` (RR ≈ 2.0) |
| Max hold | 12 bars (3h @ M15) |
| Trail | demo_trader profit extender 経由 (not in signal) |

---

## TV Backtest (in-house, MASSIVE未)

3000 bars EURUSD M15 (2025-08 ~ 2026-05), TV embedded ZigZag (Dev 0.3%) as ground truth.

### IS / OOS split

| Metric | IS (Aug 2025 - Jan 2026, 6mo) | OOS (Feb - May 2026, 4mo) |
|---|---|---|
| Trades | 30 | 28 |
| Win rate | 76.67% | 64.29% |
| Profit factor | 2.30 | 1.544 |
| Max DD | 0.03% | 0.04% |
| Avg profit | +0.14% | +0.14% |
| Avg loss | -0.20% | -0.15% |
| Wilson lower 95% | — | ≈ 0.46 |

### Comparison vs full period

| Metric | All 10mo (no IS/OOS) | Long+Short (v2.4) |
|---|---|---|
| Profit factor | 1.887 (Long only) | 1.215 (mixed) |
| Win rate | 70.69% | 62.70% |
| Trades | 58 | 126 |

→ **Short cut** で PF 1.215 → 1.887 にジャンプ (Short PF 0.884)。Long-only が edge。

---

## Pre-reg withdrawal LOCK (2026-05-26)

| Condition | Action |
|---|---|
| N=30 で WR < 35% | Shadow demote (auto) |
| N=30 で PF < 1.0 | Shadow demote (auto) |
| N=50 で PF < 1.1 | Manual review |
| Max DD > 8% account | Emergency stop |
| Consecutive 15 losses | Pause 24h |

詳細: `decisions/pivot_detector_v2_5_live_exception_2026_05_26.md`

---

## Implementation

- Signal: `strategies/daytrade/pivot_detector_v2_5.py` (PivotDetectorV25)
- Registration: `strategies/daytrade/__init__.py` (engine list + LIVE_PROMOTE_LOSERS)
- Tier: `modules/demo_trader.py` (QUALIFIED_TYPES + _PAIR_PROMOTED)

---

## Roadmap contribution

月利 100% 目標 (roadmap-v2.1) への寄与:
- Single pair EV/trade (OOS) ≈ +0.036%
- 7 trades/month @ 5% sizing → 0.25%/月
- 100% sizing → 5%/月
- Portfolio (3 pair 無相関想定) → 15%/月
- + 2-3x leverage → 30-45%/月射程

Strategy class: Mean Reversion piece, complement to trend strategies (Kalman D7, trendline_sweep)。
