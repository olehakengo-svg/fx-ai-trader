# VWAP Calibration Baseline (Pre-Fix)

**Date**: 2026-04-23
**Purpose**: commit `b37ee8b` (VWAP conf_adj 中立化) の効果測定用 **pre-deploy baseline** を固定記録
**Data**: Render `/api/demo/trades`, shadow=1, CLOSED, entry_time >= 2026-04-08 (fidelity cutoff), non-XAU
**Tool**: [tools/vwap_calibration_monitor.py](../../../tools/vwap_calibration_monitor.py)

## Baseline: Confidence bucket × Strategy category (N=2039)

| bucket | TF N | TF WR | TF EV_cost | MR N | MR WR | MR EV_cost | OTHER N | OTHER WR | OTHER EV_cost |
|---|---|---|---|---|---|---|---|---|---|
| 30-39 | 9 | 22.2% | -4.54p | 27 | 40.7% | -0.87p | 44 | 29.6% | -2.57p |
| 40-49 | 49 | 24.5% | -1.94p | 152 | 25.0% | -1.77p | 55 | 34.5% | -1.08p |
| 50-54 | 70 | **32.9%** | -0.73p | 129 | **31.8%** | -1.27p | 59 | 18.6% | -2.46p |
| 55-59 | 86 | 18.6% | -2.07p | 132 | 21.2% | -2.22p | 50 | 12.0% | -2.94p |
| 60-64 | 62 | 25.8% | -2.02p | 132 | 23.5% | -2.41p | 72 | 18.1% | -3.63p |
| 65-69 | 127 | 26.0% | -1.20p | 178 | 34.3% | -1.58p | 75 | 12.0% | -4.42p |
| 70-79 | 165 | **15.2%** | **-3.02p** | 205 | 18.1% | **-3.90p** | 106 | 25.5% | -1.93p |
| 80-89 | — | — | — | 25 | 32.0% | -2.01p | 14 | 7.1% | -7.57p |
| 90+ | — | — | — | 4 | 75.0% | +5.47p | 12 | 8.3% | -8.40p |

## Category totals

| Category | N | WR | EV_cost |
|---|---|---|---|
| TF | 568 | 22.4% | -2.01p |
| MR | 984 | 26.2% | -2.21p |
| OTHER | 487 | 20.5% | -3.02p |

## Monotonicity (Pooled)

| Zone | N | WR | EV_cost |
|---|---|---|---|
| Low-conf (<55) | 594 | **28.6%** | -1.62p |
| High-conf (≥65) | 911 | **22.5%** | -2.75p |
| **Delta** | | **-6.1pp (inverse)** | |

## Category-specific Monotonicity (重要発見)

| Category | Low N | Low WR | High N | High WR | Delta WR |
|---|---|---|---|---|---|
| **TF** | 128 | 28.9% | 292 | 19.9% | **-9.0pp** |
| **MR** | 308 | 29.2% | 412 | 26.5% | **-2.8pp** |

### 予想外の結果

仮説: 「VWAP TF-bias が MR 戦略を特に傷つけている」
実測: **TF の逆校正のほうが深刻** (Δ -9.0pp vs -2.8pp)

考察:
- VWAP は寄与因子の1つだが主因ではない
- TF 戦略群 (ema_pullback, ema200_trend_reversal, trend_rebound, ema_trend_scalp) 側の
  confidence score 計算に別の逆校正要因 (恐らく MTF alignment, ADX boost, slope加点など)
- 単純な「カテゴリ別 VWAP conf_adj 復活」(TF+2 / MR-2) だけでは解決しない

## Deploy 後の測定プラン

1. commit `b37ee8b` Render deploy 後、**N≥200 の新規 shadow 蓄積** まで待機 (~1週間)
2. `tools/vwap_calibration_monitor.py --since 2026-04-24` で post-deploy を計測
3. 比較指標:
   - Pooled Delta WR: -6.1pp → より0に近づくか (VWAP寄与分が消失)
   - TF Delta WR: -9.0pp → 改善幅が小さければ TF 側に別の calibration bug
   - Bucket 70-79 WR: 18.7% (最悪) → 改善するか

## Phase 2 判定基準 (GO/NOGO)

| 結果 | 判定 | 次アクション |
|---|---|---|
| Pooled Delta: -6.1pp → +3pp 以上 | GO ✅ | カテゴリ別 conf_adj 復活 (TF+2 / MR-2) |
| Pooled Delta: -6.1pp → -3〜+3pp (flat) | 部分GO | VWAP は中立のまま、confidence gate 全体の Platt/Isotonic 再校正 |
| Pooled Delta: 変化なし (< 2pp 差) | NOGO | 逆校正主因は別 (MTF/ADX等)、再調査 |

## 派生知見

- **75.0% WR の 90+ bucket (MR, N=4)** は外れ値 — 単一戦略 × tail-driven の可能性大、無視
- **OTHER カテゴリ (N=487)** が最も EV 悪い (-3.02p) — 分類不明戦略の多くがバグ信号の可能性
  Phase 2 で OTHER の entry_type を棚卸しして TF/MR/廃止 に分類し直す

## References

- Fix commit: `b37ee8b fix(signals): neutralize VWAP zone/slope conf_adj (inverse calibration)`
- Validation script: `tools/vwap_calibration_monitor.py`
- Related lesson: [[lesson-vwap-inverse-calibration-2026-04-23]]
- Raw snapshot: this baseline is frozen — do NOT overwrite, use timeseries pages for re-measurements
