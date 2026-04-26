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

**Pooled enriched trades**: 1180

## T1 — AR(1) Momentum Alignment × Session

| Pair | Session | Aligned (momentum) N/WR/EV | Counter (MR) N/WR/EV |
|------|---------|----------------------------|----------------------|
| GBP_JPY | Tokyo | 86/67.4%/+0.24 | 119/63.0%/+0.12 |
| GBP_JPY | London | 264/60.2%/+0.06 | 263/66.2%/+0.20 |
| GBP_JPY | NY | 214/63.1%/+0.06 | 230/57.8%/-0.03 |

## T2 — Gotobi Effect (JPY pair × Tokyo session)

| Pair | Session | Gotobi N/WR/EV | Non-Gotobi N/WR/EV | Edge (pip) |
|------|---------|-----------------|--------------------|-----------:|
| GBP_JPY | Tokyo | 38/60.5%/-0.05 | 167/65.9%/+0.22 | -0.26 |
| GBP_JPY | London | 109/64.2%/+0.15 | 418/62.9%/+0.12 | +0.03 |
| GBP_JPY | NY | 98/63.3%/+0.12 | 346/59.5%/-0.01 | +0.14 |

## D1 — Realized Vol Z-score Quintile (all strategies)

| Pair | Vol Q1 (low) | Q2 | Q3 | Q4 (high) | Q5 (extreme) |
|------|-------------|----|----|----------|---------------|
| GBP_JPY | 236/64.0%/+0.15 | 236/57.2%/-0.01 | 236/66.1%/+0.23 | 236/66.1%/+0.14 | 236/58.5%/-0.05 |

## R1 — Hurst Regime (H<0.45 MR / 0.45-0.55 neutral / H>0.55 trend)

| Pair | MR (H<0.45) | Neutral | Trend (H>0.55) |
|------|-------------|---------|----------------|
| GBP_JPY | 234/66.2%/+0.22 | 297/59.6%/-0.03 | 649/62.2%/+0.10 |

## S3 — Round-Number Distance Quintile (pips from nearest .00/.50)

| Pair | Q1 (closest) | Q2 | Q3 | Q4 | Q5 (furthest) |
|------|--------------|----|----|----|---------------|
| GBP_JPY | 239/65.3%/+0.20 | 233/61.8%/+0.05 | 236/62.3%/+0.03 | 243/62.6%/+0.11 | 229/59.8%/+0.06 |

## Cross: vwap_mean_reversion × Hurst regime (hypothesis: MR works in H<0.45)

| Pair | H<0.45 (MR regime) | Neutral | H>0.55 (trend regime) |
|------|---------------------|---------|-----------------------|
| GBP_JPY | — | — | — |

## 判断プロトコル (CLAUDE.md)
- **観測のみ**. 実装判断は別期間 walk-forward で再検証後。
- 1 回 BT の feature binning 発見 → Shadow N≥30 で確証取得まで filter 実装なし (lesson-reactive-changes)
- 各 feature は pair 毎に逆方向の傾きが出ることがある (ksft-vwap 教訓)

## Source
- `tools/edge_lab.py` (post-hoc feature extraction + binning)
- Based on `app.run_daytrade_backtest` trade_log
