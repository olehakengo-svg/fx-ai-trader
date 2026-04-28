# Pre-registration LOCK — Phase 8 Track D (Session Boundary Transitions)

**Date**: 2026-04-28
**Author**: Claude (quant analyst mode)
**Master plan**: [phase8-master-2026-04-28.md](phase8-master-2026-04-28.md)
**Tool**: `tools/phase8_track_d.py`
**Status**: LOCK — must not be edited after first scan run

## Hypothesis (Track D only)

Phase 7 single-feature scan の `hour_utc` bucketing は in-session bar 単位で
edge を探していた。Track D は **session 境界 ±1h** を信号源とする:

- H1: Institutional position handover が起こる boundary ±1h で directional
  drift が発生
- H2: NY→Asia / London→NY 等の liquidity transition は EV を残す
- H3: Boundary 内でも 15-min sub-window によって entry timing 効率が異なる

既存戦略 (`london_close_reversal_v2` UTC 20:30-21:00, `gotobi_fix` 00:55,
`london_fix_reversal`) は特定 fix window を扱うが、boundary ±1h transition
window の系統的検定は未実施。

## Boundary windows (6, pre-committed)

| ID | Boundary | Window (UTC) | Hours | Bars/day (15m) |
|----|----------|--------------|-------|----------------|
| `tokyo_to_london` | Tokyo end → London open | 06:00–08:00 | 2.0 | 8 |
| `london_to_ny`    | London → NY overlap | 12:00–14:00 | 2.0 | 8 |
| `ny_to_asia`      | NY close → Asia early | 21:00–23:00 | 2.0 | 8 |
| `pre_tokyo`       | Asia open setup (cross-midnight) | 22:00–00:00 | 2.0 | 8 |
| `pre_london`      | London pre-open last hour | 06:00–07:00 | 1.0 | 4 |
| `pre_ny`          | NY pre-open last hour | 12:30–13:30 | 1.0 | 4 |

**Cross-window overlap (acknowledged at LOCK)**:
- `pre_london` ⊂ `tokyo_to_london` (06-07 ⊂ 06-08)
- `pre_ny` ⊂ `london_to_ny` (12:30-13:30 ⊂ 12-14)
- `pre_tokyo` ∩ `ny_to_asia` (22-23 共有)

両方とも survivor になった場合は narrow window (pre_*) を優先採択。これは
master cross-track de-dup の一段階前で track 内 dedup として処理する。

## Look-ahead safety

- Entry: bar(t).Open (boundary window 内の各 15m bar が candidate)
- ATR (SL/TP): bar(t-1).ATR(14) を使用
- Cross-midnight `pre_tokyo` (22:00–00:00): UTC hour ∈ {22, 23} で判定。
  weekend gap (Friday 22:00 UTC 以降〜Sunday 22:00 UTC 未満) は除外

## LOCK 設定 (master plan に従う)

- **Pairs**: `["USD_JPY", "EUR_USD", "GBP_USD", "EUR_JPY", "GBP_JPY"]` (5)
- **Directions**: `["BUY", "SELL"]` (2)
- **Forward bars**: `[4, 8, 12]` (3)
- **Days**: 275 training (holdout 90 reserved)
- **SL / TP**: 1.0 ATR / 1.5 ATR (RR=1.5)
- **Friction**: `friction_for(pair, mode="DT", session)` cell-conditioned
- **Dedup**: 同 cell 内で前 trade が open 中の signal は skip (trade_sim.dedup=True)

## Grid size

- **Stage 1 (boundary-level)**: 6 boundaries × 5 pairs × 2 dir × 3 fw = **180 cells**
- **Stage 2 (sub-window level)**: 各 boundary 内 15-min sub-window:
  - 2h boundaries (4 個): 8 sub-windows each
  - 1h boundaries (2 個): 4 sub-windows each
  - 計 sub-windows = 4×8 + 2×4 = **40 sub-windows**
  - 40 × 5 pairs × 2 dir × 3 fw = **1,200 cells max** (capacity gate で減少)

## Gates

| Stage | Gate | Threshold | 備考 |
|---|---|---|---|
| Stage 1 | BH-FDR | q = 0.10 | |
| Stage 1 | Wilson lower | > 0.50 | |
| Stage 1 | N | ≥ 50 | **boundary は narrow → 緩和 (master 100 → 50)** |
| Stage 1 | EV | > 0 pip net | |
| Stage 1 | trades/month | ≥ 5 | |
| Stage 1 | Sharpe per event | > 0.05 | |
| Stage 2 | Bonferroni | p × n_tests < 0.05 | |
| Stage 2 | Wilson lower | > 0.50 | |
| Stage 2 | N | ≥ 50 | sub-window では更に narrow |
| Stage 2 | EV | > 0 pip net | |
| Stage 2 | trades/month | ≥ 3 | sub-window で更に緩和 |

**N≥50 緩和の根拠**: boundary は窓が狭く (1-2h × 5d/week × 11 months ≈
220-440 bars/year)、Phase 7 の N≥100 では全 cell が dropout する。緩和は
Wilson_lower > 0.50 + Bonferroni で過学習リスクを抑える。

## Cross-strategy boundary overlap (Track D 独自)

完了後、survivor (boundary, pair, dir, fw) と既存 session-time strategies
の overlap を計算:

| 既存戦略 | UTC window | 重複可能性のある Track D boundary |
|---|---|---|
| `london_close_reversal_v2` | 20:30–21:00 | `ny_to_asia` (21-23) — 隣接、重複なし |
| `gotobi_fix` | 00:55 (約 00:45-01:15) | `pre_tokyo` (22-00) — 隣接、重複なし |
| `london_fix_reversal` | 16:00 fix 周辺 | 該当 boundary なし |

LOCK 時点では boundary survivor は既存戦略と直接重複しない見込み。ただし
master cross-track de-dup で feature/pair/dir 一致あれば redundant 判定。

## Output paths

- Stage 1: `raw/phase8/track_d/stage1_boundary_<timestamp>.json`
- Stage 2: `raw/phase8/track_d/stage2_subwindow_<timestamp>.json`
- Cross-strategy overlap: `raw/phase8/track_d/overlap_with_existing_<timestamp>.md`

## Acceptance criteria

- ≥ 0 cell が 全 Stage 2 gate 通過 (期待 0-2 cells、boundary effect 弱の可能性高)
- 既存 LCR-v2 / gotobi_fix と pair × dir × fw 完全一致なら novel ではない
- 完了後 master notification + raw JSON commit

## Non-goals (out of scope this session)

- Stage 3 (quarterly stability) — separate session
- Stage 4 (90d holdout OOS) — separate session
- Live shadow deployment — Track D 単独では行わない
