# Edge Lab — Post-hoc Multi-Feature Analysis

- **Generated**: 2026-04-26 03:13 UTC
- **Lookback**: 365d / 15m
- **Min N per bin**: 30

## 特徴量定義
- **T1** (AR(1) momentum): sign(prior 5-bar return) × entry direction
  - `aligned=True`: entry 方向 = 直近 5 本の value 方向 (momentum)
  - `aligned=False`: entry 方向 ≠ 直近 5 本 (counter-trend / MR)
- **T2** (Gotobi): day-of-month ∈ {5,10,15,20,25,月末}
- **D1** (Vol Z-score): σ_20bar の σ_60bar 分布内 z-score、quintile 分け
- **R1** (Hurst): R/S 法による 50 bar Hurst 指数。H<0.45=MR regime / H>0.55=trend regime
- **S3** (Round-number distance): entry price の最寄 .00/.50 レベルへの pip 距離、quintile

**Pooled enriched trades**: 1529

## T1 — AR(1) Momentum Alignment × Session

| Pair | Session | Aligned (momentum) N/WR/EV | Counter (MR) N/WR/EV |
|------|---------|----------------------------|----------------------|
| EUR_USD | London | 427/61.1%/+0.14 | 462/62.1%/+0.15 |
| EUR_USD | NY | 330/55.8%/-0.05 | 310/54.8%/-0.05 |

## T2 — Gotobi Effect (JPY pair × Tokyo session)

| Pair | Session | Gotobi N/WR/EV | Non-Gotobi N/WR/EV | Edge (pip) |
|------|---------|-----------------|--------------------|-----------:|

## D1 — Realized Vol Z-score Quintile (all strategies)

| Pair | Vol Q1 (low) | Q2 | Q3 | Q4 (high) | Q5 (extreme) |
|------|-------------|----|----|----------|---------------|
| EUR_USD | 306/64.4%/+0.22 | 306/55.2%/-0.06 | 305/59.0%/+0.07 | 306/57.2%/+0.01 | 306/59.2%/+0.06 |

## R1 — Hurst Regime (H<0.45 MR / 0.45-0.55 neutral / H>0.55 trend)

| Pair | MR (H<0.45) | Neutral | Trend (H>0.55) |
|------|-------------|---------|----------------|
| EUR_USD | 256/62.1%/+0.16 | 331/59.8%/+0.05 | 942/57.9%/+0.04 |

## S3 — Round-Number Distance Quintile (pips from nearest .00/.50)

| Pair | Q1 (closest) | Q2 | Q3 | Q4 | Q5 (furthest) |
|------|--------------|----|----|----|---------------|
| EUR_USD | 328/56.4%/-0.03 | 305/59.0%/+0.10 | 324/57.7%/-0.06 | 271/60.1%/+0.13 | 301/62.1%/+0.18 |

## Cross: vwap_mean_reversion × Hurst regime (hypothesis: MR works in H<0.45)

| Pair | H<0.45 (MR regime) | Neutral | H>0.55 (trend regime) |
|------|---------------------|---------|-----------------------|
| EUR_USD | — | — | — |

## 判断プロトコル (CLAUDE.md)
- **観測のみ**. 実装判断は別期間 walk-forward で再検証後。
- 1 回 BT の feature binning 発見 → Shadow N≥30 で確証取得まで filter 実装なし (lesson-reactive-changes)
- 各 feature は pair 毎に逆方向の傾きが出ることがある (ksft-vwap 教訓)

## Source
- `tools/edge_lab.py` (post-hoc feature extraction + binning)
- Based on `app.run_daytrade_backtest` trade_log
