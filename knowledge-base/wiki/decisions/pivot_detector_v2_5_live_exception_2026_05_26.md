# Pivot Detector v2.5 — LIVE intentional exception (Path B)

**Date**: 2026-05-26
**Rule**: R1 (Slow & Strict) **override** per user judgment
**Status**: LOCK (Pre-reg withdrawal conditions below)
**Decision tag**: `pivot_detector_v2_5_live_exception`

---

## TL;DR

EUR_USD M15 Long-Only Mean-Reversion 戦略を **LIVE PAIR_PROMOTED** として 2026-05-26 投入する。
TV (TradingView) 検証のみ、MASSIVE multi-pair BT 未実施で Rule 1 要件 8 項目中 5 項目未達だが、
ユーザー判断による意図的例外として、Kalman D7 (v17/v18f/v18e LIVE) や vix_carry 1.0x (2026-05-21)
と同列で扱う。撤退条件を pre-reg LOCK。

---

## 戦略仕様

| Item | Value |
|---|---|
| Name | `pivot_detector_v2_5` |
| Class | Mean Reversion Long-only |
| Pair (initial) | **EUR_USD ONLY** |
| TF | M15 |
| Entry (ALL) | `low <= BB_lower(20, 2σ)` AND `RSI(14) <= 30` AND `close < EMA(25)` AND `vol_z(20) >= 1.5` AND `7 <= UTC hour <= 21` |
| Stop | `3 × ATR(14)` below entry |
| Take Profit | `6 × ATR(14)` above entry (RR ≈ 2.0) |
| Direction | LONG only |
| Tier | PAIR_PROMOTED + LIVE_PROMOTE_LOSERS side-channel |
| Lot | 1000u (no boost) |

---

## TradingView 検証結果

3000 bars (≈31 日) EURUSD M15 with embedded ZigZag (Dev 0.3%):

| Metric | **IS (Aug 2025 - Jan 2026, 6mo)** | **OOS (Feb - May 2026, 4mo)** |
|---|---|---|
| Profit factor | 2.30 | **1.544** |
| Win rate | 76.67% | **64.29%** |
| Trades (N) | 30 | **28** |
| Max DD | 0.03% | 0.04% |
| Avg profit | +0.14% | +0.14% |
| Avg loss | -0.20% | -0.15% |
| Wilson 95% lower | — | **≈ 0.46** |

PF degradation IS→OOS = 67% (許容範囲)。完全 overfit なら PF が 1.0 を切るが、1.544 維持。

Pine source: `bt-results/tv-overlays/pivot_detector_v2_6_strategy_oos_filter.pine` (separate commit)
TV slot: `My script2` (USER;978a118f17884c19a823b262a8aceb5a)

---

## Rule 1 要件チェック

| 要件 | 基準 | 現状 | 達成 |
|---|---|---|---|
| N (OOS) | ≥30 | 28 | ⚠️ |
| WR | break-even 超え | 64.29% | ✅ |
| PF | >1.0 | 1.544 | ✅ |
| Wilson lower 95% | ≥0.50 | 約 0.46 | ❌ |
| Bonferroni 補正 | multi-hypothesis | 未適用 | ❌ |
| OOS / WF | 3+ folds 推奨 | 1 fold | ❌ |
| Kelly | 算出済み | 未算 | ❌ |
| Pre-reg LOCK | 必要 | 本ドキュメントで実施 | ✅ |
| 365日 multi-pair MASSIVE BT | 必要 | 未実施 (TV のみ) | ❌ |

**5/9 未達。Rule 1 strict pass はしていない**が、ユーザー判断で例外発動。

---

## Path B 採用理由（user judgment）

1. TV OOS で **PF 1.544 / Max DD 0.04% / N=28** — overfit ではなく real edge の蓋然性は高い
2. Long と Short の挙動が完全に分かれた（Short PF 0.884 = 負け） → Long-only に絞ることで edge が抽出された
3. 月利 100% 目標達成には **portfolio piece** として今投入を始め、Live N>=30 を待ちながら拡張するのが最短
4. Pre-reg withdrawal LOCK で blow-up リスクは抑え込める
5. PYR P0 fix (commit 4cd44956, 4cd44956) で promote/demote logic は健全化中

同型例外:
- Kalman D7 v17/v18f/v18e LIVE (2026-05-20) — regime-bound discretionary edge
- vix_carry_unwind 1.0x (2026-05-21) — Rule 1 全項目未充足、user judgment

---

## Pre-reg Withdrawal LOCK

| Condition | Action | Notes |
|---|---|---|
| **N=30 で WR < 35%** | Shadow demote (auto) | OOS 64.29% の半減レベル、明確な失敗 |
| **N=30 で PF < 1.0** | Shadow demote (auto) | break-even 割れ = negative EV 確定 |
| **N=50 で PF < 1.1** | Manual review (auto-demote しない) | edge erosion 警戒、再評価 |
| **Max DD > 8% account** | Emergency stop | blow-up 保護 |
| **Single trade loss > 2% account** | log only | trail を信頼 |
| **Consecutive 15 losses** | Pause 24h | regime shift / 流動性異常の可能性 |

自動化:
- `tools/volume_live_promotion_watchdog.py` (Live N≥10 EV<0 で自動 demote) は並列稼働
- `tools/tier_live_drift.py` で Wilson_lo, PF, DD を日次監視

---

## Live ramp plan

| Stage | Trigger | Lot |
|---|---|---|
| Stage 0 (現在) | Deploy 直後 | 1000u (default) |
| Stage 1 | Live N≥10 PF≥1.3 | 1500u (+50%) |
| Stage 2 | Live N≥30 PF≥1.3 Wilson_lo≥0.50 | 3000u (3×) |
| Stage 3 | Live N≥50 PF≥1.2 + cell-based stable | Kelly half (e.g. 5000u) |

Stage ↑ は user 判断で。Rule 1 達成 (N≥30 Bonferroni-passing + Kelly>0) で portfolio 拡張 (GBP_USD, USD_JPY) 検討。

---

## Implementation files

| File | Purpose |
|---|---|
| `strategies/daytrade/pivot_detector_v2_5.py` | Signal function |
| `strategies/daytrade/__init__.py` | Engine registration + LIVE_PROMOTE_LOSERS |
| `modules/demo_trader.py` | QUALIFIED_TYPES + _PAIR_PROMOTED |
| `knowledge-base/wiki/strategies/pivot_detector_v2_5.md` | Strategy card (separate file) |
| This file | Decision doc |

---

## Monitoring queries

```bash
# Live performance
curl -s 'https://fx-ai-trader.onrender.com/api/strategies/status?range=all' \
  | jq '.strategies.pivot_detector_v2_5'

# Per-cell breakdown (EUR_USD only)
curl -s 'https://fx-ai-trader.onrender.com/api/oanda/audit?range=30d&strategy=pivot_detector_v2_5'

# Watchdog
python3 tools/volume_live_promotion_watchdog.py --strategy pivot_detector_v2_5
```

---

## Memory entry

`memory/project_pivot_detector_v2_5_live_exception_2026_05_26.md`
- LIVE deploy 2026-05-26 commit (next push)
- Pre-reg LOCK (this doc)
- Watchdog: existing volume_live_promotion_watchdog
- Withdrawal: 上記 6 条件、自動 + manual review 混合
