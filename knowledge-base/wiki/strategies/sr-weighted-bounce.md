---
name: sr_weighted_bounce
mode: daytrade
status: shadow_only_audit_only
created_at: 2026-05-13
strategy_type: MR
family: bounce
parent_lineage: sr_anti_hunt_bounce (Phase 2 BT survivor)
tier: 0 (audit_only)
---

# SR Weighted Bounce v1

## 思想
SR 水平線の重み (touch_count + D1/W1 confluence + round_number + rejection magnitude) で
gate された **heavy wall reversal**。survivor `sr_anti_hunt_bounce` の anti-hunt SL geometry
を継承しつつ、weight gate で sigal の母集団を絞り込む。

## 司令塔仮説 (2026-05-13)
- 既存 5 SR 戦略 (`sr_anti_hunt_bounce` 含む) は touch_count を gate に使っていなかった
- `sr_detector` / `find_sr_levels_weighted` の weight info を捨てている (smoking gun:
  sr_break_retest.py:61 `MIN_CLUSTERS=1`)
- 「重い壁ほど反発エッジが強い」を実トレードで検証

## エントリ条件
| # | 条件 | 値 |
|---|---|---|
| 1 | ペア | USDJPY/EURUSD/GBPUSD/EURJPY/GBPJPY |
| 2 | ADX | < 30 |
| 3 | composite_weight | >= 3.0 |
| 4 | weight percentile | 上位 30% |
| 5 | SR proximity | < 0.4 ATR |
| 6 | 反転足確認 | signal 方向の実体 |
| 7 | 直近 2 本に hunt wick | なし |

## Composite Weight
`1.0 × own_touch + 3.0 × d1_touch + 5.0 × w1_touch + 2.0 × round_score + 1.5 × magnitude_score`
(Wave 1 固定、post-hoc selection 罠回避のため sweep しない)

## SL/TP
- SL = level − sign × (P90_excursion + 0.5 × ATR) (2026-Q1 calibration、Shadow N>=30 後 re-audit)
- TP = min(next_opposite_SR, entry + 2.0 × SL_dist)、MIN_RR=1.5

## Shadow promotion gate (Tier 0 → 1)
- N >= 30 trades
- Wilson_lo (95% LB, Bonferroni m=2 (bounce/break 想定)) >= 0.40
- 単一年 WR>=90% 集中 flag が出ていない

## Live promotion gate (Tier 1 → 2)
- N >= 100 trades
- Bonferroni m=2 再現性
- WF 3+ folds pos_ratio >= 0.8
- Kelly >= 0.20

## 起源 / 関連
- 経緯: `wiki/decisions/2026-05-13-sr-weighted-bounce-shadow-injection.md` (生成予定)
- 親 lineage: sr_anti_hunt_bounce ([wiki/strategies/sr-anti-hunt-bounce.md](sr-anti-hunt-bounce.md))
- Phase 2 BT: `bt-results/sr-weight-phase2-bin-bhfdr-2026-05-11.json`
- audit v2 forensic: `reports/sr_phase2_vs_audit_v2_forensic_2026-05-13.md`

## 計装
- entry_type: `sr_weighted_bounce`
- sr_meta は既存 oanda_audit DDL (sr_strength/sr_touches/sr_days_span/sr_is_strong/sr_distance_atr)
  に composite_weight 追加列が要れば Phase 2.5 で別タスク化
