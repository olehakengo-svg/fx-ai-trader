# Edge Lab — Post-hoc Multi-Feature Analysis

- **Generated**: 2026-04-26 03:17 UTC
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

**Pooled enriched trades**: 1144

## T1 — AR(1) Momentum Alignment × Session

| Pair | Session | Aligned (momentum) N/WR/EV | Counter (MR) N/WR/EV |
|------|---------|----------------------------|----------------------|
| EUR_JPY | Tokyo | 108/56.5%/-0.08 | 106/58.5%/-0.01 |
| EUR_JPY | London | 254/57.9%/-0.05 | 256/66.4%/+0.18 |
| EUR_JPY | NY | 209/57.9%/-0.05 | 203/58.1%/-0.04 |

## T2 — Gotobi Effect (JPY pair × Tokyo session)

| Pair | Session | Gotobi N/WR/EV | Non-Gotobi N/WR/EV | Edge (pip) |
|------|---------|-----------------|--------------------|-----------:|
| EUR_JPY | Tokyo | 39/61.5%/+0.20 | 175/56.6%/-0.10 | +0.31 |
| EUR_JPY | London | 108/63.0%/+0.09 | 402/61.9%/+0.06 | +0.03 |
| EUR_JPY | NY | 85/63.5%/+0.10 | 327/56.6%/-0.08 | +0.18 |

## D1 — Realized Vol Z-score Quintile (all strategies)

| Pair | Vol Q1 (low) | Q2 | Q3 | Q4 (high) | Q5 (extreme) |
|------|-------------|----|----|----------|---------------|
| EUR_JPY | 229/55.0%/-0.14 | 229/58.5%/+0.00 | 228/64.5%/+0.10 | 229/65.1%/+0.15 | 229/56.3%/-0.09 |

## R1 — Hurst Regime (H<0.45 MR / 0.45-0.55 neutral / H>0.55 trend)

| Pair | MR (H<0.45) | Neutral | Trend (H>0.55) |
|------|-------------|---------|----------------|
| EUR_JPY | 204/62.3%/+0.05 | 266/60.2%/+0.01 | 674/59.1%/-0.01 |

## S3 — Round-Number Distance Quintile (pips from nearest .00/.50)

| Pair | Q1 (closest) | Q2 | Q3 | Q4 | Q5 (furthest) |
|------|--------------|----|----|----|---------------|
| EUR_JPY | 239/62.8%/+0.05 | 220/58.6%/+0.03 | 228/60.5%/+0.00 | 236/57.6%/-0.07 | 221/59.7%/+0.02 |

## Cross: vwap_mean_reversion × Hurst regime (hypothesis: MR works in H<0.45)

| Pair | H<0.45 (MR regime) | Neutral | H>0.55 (trend regime) |
|------|---------------------|---------|-----------------------|
| EUR_JPY | — | — | — |

## 判断プロトコル (CLAUDE.md)
- **観測のみ**. 実装判断は別期間 walk-forward で再検証後。
- 1 回 BT の feature binning 発見 → Shadow N≥30 で確証取得まで filter 実装なし (lesson-reactive-changes)
- 各 feature は pair 毎に逆方向の傾きが出ることがある (ksft-vwap 教訓)

## Source
- `tools/edge_lab.py` (post-hoc feature extraction + binning)
- Based on `app.run_daytrade_backtest` trade_log
