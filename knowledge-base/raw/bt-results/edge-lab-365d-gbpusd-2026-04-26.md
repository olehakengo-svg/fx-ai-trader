# Edge Lab — Post-hoc Multi-Feature Analysis

- **Generated**: 2026-04-26 03:12 UTC
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

**Pooled enriched trades**: 1969

## T1 — AR(1) Momentum Alignment × Session

| Pair | Session | Aligned (momentum) N/WR/EV | Counter (MR) N/WR/EV |
|------|---------|----------------------------|----------------------|
| GBP_USD | Tokyo | 124/56.5%/-0.07 | 130/58.5%/+0.03 |
| GBP_USD | London | 472/59.5%/+0.00 | 457/61.1%/+0.04 |
| GBP_USD | NY | 393/51.4%/-0.18 | 374/57.5%/-0.04 |

## T2 — Gotobi Effect (JPY pair × Tokyo session)

| Pair | Session | Gotobi N/WR/EV | Non-Gotobi N/WR/EV | Edge (pip) |
|------|---------|-----------------|--------------------|-----------:|

## D1 — Realized Vol Z-score Quintile (all strategies)

| Pair | Vol Q1 (low) | Q2 | Q3 | Q4 (high) | Q5 (extreme) |
|------|-------------|----|----|----------|---------------|
| GBP_USD | 394/60.2%/+0.03 | 394/54.3%/-0.17 | 393/56.5%/+0.03 | 394/55.3%/-0.11 | 394/61.2%/+0.05 |

## R1 — Hurst Regime (H<0.45 MR / 0.45-0.55 neutral / H>0.55 trend)

| Pair | MR (H<0.45) | Neutral | Trend (H>0.55) |
|------|-------------|---------|----------------|
| GBP_USD | 349/58.5%/+0.02 | 444/57.9%/-0.06 | 1176/57.1%/-0.04 |

## S3 — Round-Number Distance Quintile (pips from nearest .00/.50)

| Pair | Q1 (closest) | Q2 | Q3 | Q4 | Q5 (furthest) |
|------|--------------|----|----|----|---------------|
| GBP_USD | 417/59.5%/+0.03 | 385/56.6%/-0.11 | 395/58.7%/-0.03 | 388/58.2%/+0.04 | 384/54.2%/-0.12 |

## Cross: vwap_mean_reversion × Hurst regime (hypothesis: MR works in H<0.45)

| Pair | H<0.45 (MR regime) | Neutral | H>0.55 (trend regime) |
|------|---------------------|---------|-----------------------|
| GBP_USD | — | — | — |

## 判断プロトコル (CLAUDE.md)
- **観測のみ**. 実装判断は別期間 walk-forward で再検証後。
- 1 回 BT の feature binning 発見 → Shadow N≥30 で確証取得まで filter 実装なし (lesson-reactive-changes)
- 各 feature は pair 毎に逆方向の傾きが出ることがある (ksft-vwap 教訓)

## Source
- `tools/edge_lab.py` (post-hoc feature extraction + binning)
- Based on `app.run_daytrade_backtest` trade_log
