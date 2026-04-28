# Pre-registration LOCK — Phase 8 Track C (Quantile-Bucketed Continuous)

**Date**: 2026-04-28
**Author**: Claude (quant analyst mode)
**Master plan**: [phase8-master-2026-04-28.md](phase8-master-2026-04-28.md)
**Tool**: `tools/phase8_track_c.py`
**Status**: LOCK — must not be edited after first scan run

## Hypothesis (Track C only)

Phase 7 の固定 threshold (BB%B ≤ 0.2 / 0.4 / 0.6 / 0.8) は market regime
変化に追従しない。Decile (10 quantile) bucketize を rolling window で計算し、
adaptive thresholding によって以下を検証する:

- H1: Tail buckets (D0 = P0–P10, D9 = P90–P100) に EV edge が集中する
- H2: 固定 threshold (Phase 7 / Track A) の bias を回避できる
- H3: Pair-specific な volatility regime characteristic が deciles に反映される

## Features under test (4)

| Feature ID | Source | Decile bucket | Look-ahead 防止 |
|---|---|---|---|
| `bbpb_15m_decile` | 15m BB%B | rolling 30d pct-rank → decile [0..9] | rolling window ending at bar t (no future leak) |
| `rsi_15m_decile` | 15m RSI(14) | 同上 | 同上 |
| `atr_pct_60d_decile` | ATR percentile (60d rank) | 同上 | 二重 rolling: 60d ATR rank → 30d decile |
| `recent_3bar_ret_decile` | 直近 3-bar log-return sum | 同上 | 直近 3-bar 計算時点で確定 |

## Quantile boundary policy

- **Window**: rolling 30 calendar days = `30 × 96 = 2880` bars (15m)
- **Method**: `pd.Series.rolling(window=2880, min_periods=1440).rank(pct=True)`
- **Decile mapping**: `decile = min(floor(pct_rank × 10), 9)` (i.e. D0..D9)
- **Look-ahead safety**:
  - rolling() in pandas は backward-looking (bars [t-N+1 .. t])。bar t の
    pct rank は t 時点で既知の値同士の比較なので将来データ漏洩しない。
  - 各 feature の base value (BB%B / RSI / ATR percentile) も全て backward-looking
- **min_periods 制約**: 最初 15 日 (= 1440 bars) 未満は decile 計算せず NaN

## LOCK 設定 (master plan に従う)

- **Pairs**: `["USD_JPY", "EUR_USD", "GBP_USD", "EUR_JPY", "GBP_JPY"]` (5)
- **Directions**: `["BUY", "SELL"]` (2)
- **Forward bars**: `[4, 8, 12]` (3)
- **Days**: 275 training (holdout 90 reserved)
- **SL / TP**: 1.0 ATR / 1.5 ATR (RR=1.5)
- **Friction**: `friction_for(pair, mode="DT", session)` cell-conditioned
- **Holdout**: 直近 90 日 (Stage 4 OOS reserve、本セッションで Stage 1+2 のみ)
- **Decile count**: 10 (D0..D9)

## Grid size

- 4 features × 10 deciles × 5 pairs × 2 dir × 3 fw = **1,200 cells (Stage 1)**
- Stage 2 pairwise: 4C2 = 6 feature combos × 10×10 buckets × 5 pairs × 2 dir × 3 fw
  = **18,000 cells (Stage 2 max)** (実際には N≥100 で大幅に絞られる)

## Gates (master plan に従う)

| Stage | Gate | Threshold |
|---|---|---|
| Stage 1 | BH-FDR | q = 0.10 |
| Stage 1 | Wilson lower | > 0.50 |
| Stage 1 | N | ≥ 100 |
| Stage 1 | EV | > 0 pip net |
| Stage 1 | trades/month | ≥ 5 |
| Stage 1 | Sharpe per event | > 0.05 |
| Stage 2 | Bonferroni | p × n_tests < 0.05 |
| Stage 2 | Wilson lower | > 0.50 |
| Stage 2 | N | ≥ 100 |
| Stage 2 | EV | > 0 pip net |
| Stage 2 | trades/month | ≥ 5 |

## Cross-track de-dup rule (master responsibility — recorded here for trace)

- Track A の固定 bucketing で発見された cell と、Track C の decile cell の
  underlying boundary を比較。
  - 例: Track A `bbpb_15m_b=0` (≤0.2) と Track C `bbpb_15m_decile=0` (P0..P10)
    の boundary が大幅一致 (>50% same bars) なら **redundant**
- Redundant 候補は Track A を優先 (固定 threshold の方が運用 simple)
- Track C 独自 edge: Track A で発見されない (例: D5..D6 mid-range で WR>50%)
  ものは novel として Stage 2 まで保持

## Output paths

- Stage 1: `raw/phase8/track_c/stage1_decile_<timestamp>.json`
- Stage 2: `raw/phase8/track_c/stage2_decile_pair_<timestamp>.json`
- Boundary 比較レポート: `raw/phase8/track_c/track_a_vs_c_<timestamp>.md`

## Acceptance criteria

- ≥ 0 cell が 全 Stage 2 gate 通過 (期待 1-2 cells)
- 全 cell の rolling decile boundary が Track A の固定 threshold と
  どう違うか (mean P10 / P90 値) を report
- 完了後 master notification + raw JSON commit

## Non-goals (out of scope this session)

- Stage 3 (quarterly stability) — separate session
- Stage 4 (90d holdout OOS) — separate session
- Live shadow deployment — Track C 単独では行わない
