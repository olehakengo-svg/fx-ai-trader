---
name: sr_weighted_break
mode: daytrade
status: shadow_only_audit_only
created_at: 2026-05-13
strategy_type: pullback
family: break
family_pair: sr_weighted_bounce (bounce family)
parent_lineage: sr_break_retest (smoking gun MIN_CLUSTERS=1 を是正、weight gate 化)
tier: 0 (audit_only)
---

# SR Weighted Break v1

- **Status**: SHADOW_ONLY (audit_only, Tier 0) — Wave 1 Shadow 蓄積中、N>=30 で re-audit

## 思想
SR 水平線の重み (touch_count + D1/W1 confluence + round_number + rejection magnitude)
で gate された **heavy wall breakout retest**。`sr_weighted_bounce` と family pair を
組み、heavy wall の両方向エッジ (反発 vs 突破) を Shadow で並走検証。

## 司令塔仮説 (2026-05-13)
- 既存 sr_break_retest は Williams Fractal 独自検出 + MIN_CLUSTERS=1 で軽い壁も拾う
- 本戦略は production と同 detector (sr_detector / find_sr_levels_weighted) を消費し、
  composite weight gate で母集団を絞り込む
- 「重い壁ほど breakout 後の retest follow-through が強い」を実トレードで検証

## エントリ条件
| # | 条件 | 値 |
|---|---|---|
| 1 | ペア | USDJPY/GBPUSD/EURJPY/GBPJPY (EUR/USD/EUR/GBP 除外) |
| 2 | ADX | >= 20 |
| 3 | composite_weight | >= 3.0 |
| 4 | weight percentile | 上位 30% |
| 5 | Break body | >= 25% range |
| 6 | Break margin | close > level + 0.05 ATR (BUY) |
| 7 | Retest zone | < 0.5 ATR from broken level |
| 8 | Retest EMA9 confirmation | close > EMA9 (BUY) |
| 9 | HTF 方向 | 矛盾 (bear/bull) なら block |

## SL/TP
- SL = broken_level ∓ 0.3 ATR (role reversal placement)
- TP = min(next opposite SR, entry + 2.0 × SL_dist)、MIN_RR=1.5

## Shadow promotion gate (Tier 0 → 1)
- N >= 30 trades
- Wilson_lo (95% LB, Bonferroni m=2 (bounce/break family-wise)) >= 0.40
- 単一年 WR>=90% 集中 flag が出ていない

## Live promotion gate (Tier 1 → 2)
- N >= 100 trades
- Bonferroni m=2 再現性
- WF 3+ folds pos_ratio >= 0.8
- Kelly >= 0.20

## 起源 / 関連
- Family pair: sr_weighted_bounce ([wiki/strategies/sr-weighted-bounce.md](sr-weighted-bounce.md))
- 親 lineage: sr_break_retest ([wiki/strategies/sr-break-retest.md](sr-break-retest.md))
  → MIN_CLUSTERS=1 smoking gun を是正
- Decision: `wiki/decisions/2026-05-13-sr-weighted-break-shadow-injection.md` (生成予定)
- 経緯: `reports/sr_phase2_vs_audit_v2_forensic_2026-05-13.md`
