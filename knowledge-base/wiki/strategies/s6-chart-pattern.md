# S6 Chart Pattern Detector (USDJPY M5)

- **Status**: Wave 2 BT completed; all tested cells rejected (no LIVE / Shadow exposure)
- **Stage**: 0 (BT_REJECTED / NO_EDGE) — detector exists, BT edge not validated
- **Rule**: R1 Slow & Strict
- **Scope**: USD_JPY / M5 only, no LIVE or Shadow routing exposure
- **Artifact**: `data/chart_patterns.db` / `chart_pattern_signals`

## Definition

S6 converts 12 handwritten chart-pattern hypotheses into deterministic ATR-normalized geometry detectors. It is not a trading strategy yet; Wave 1 Phase 0 only labels historical bars and stores candidate entry/SL/TP levels for later Wave 2 backtesting.

Common primitives:
- Swing pivot: strict `k=3` high/low pivot.
- ATR: Wilder ATR(14) on M5 bars.
- Trendline: latest two same-kind pivots.
- Locked thresholds: flat `0.05 ATR/bar`, slope `0.10 ATR/bar`, min height `1.5 ATR`, duration `5..80` bars, breakout buffer `0.10 ATR`, SL buffer `0.50 ATR`, same-pivot tolerance `0.30 ATR`.

## Pattern Catalog

| ID | Pattern | Direction | Geometry |
|---:|---|---|---|
| 1 | ascending_triangle | BUY | flat upper highs, rising lows, alternating 2H/2L |
| 2 | rising_wedge | BUY | rising upper/lower lines, lower slope steeper, width converges >=50% |
| 3 | bull_flag | BUY | prior pole >=3 ATR, downward parallel flag, flag amp <=0.5 pole |
| 4 | descending_triangle | SELL | flat lower lows, falling highs, alternating 2H/2L |
| 5 | falling_wedge | SELL | falling upper/lower lines, upper slope steeper, width converges >=50% |
| 6 | bear_flag | SELL | prior pole down >=3 ATR, upward parallel flag, flag amp <=0.5 pole |
| 7 | double_bottom | BUY | L-H-L with lows within `0.30 ATR`, neckline height >=1.5 ATR |
| 8 | triple_bottom | BUY | L-H-L-H-L, three lows within tolerance, two neck highs near-flat |
| 9 | inverse_head_shoulders | BUY | L-H-L-H-L with lower head, shoulder symmetry <=0.4 |
| 10 | double_top | SELL | H-L-H mirror of double bottom |
| 11 | triple_top | SELL | H-L-H-L-H mirror of triple bottom |
| 12 | head_shoulders | SELL | H-L-H-L-H mirror of inverse H&S |

Entry is bar-close breakout only. Wick-only breakout is rejected. Re-entry dedup uses the locked `(pattern_id, pivot_anchor_ts, pivot_opposite_ts)` tuple.

## Wave Plan

| Wave | Scope | Status |
|---|---|---|
| W1P0 | Detector + label generation, USDJPY M5 only | DONE |
| W2 | USDJPY M5 12.3y backtest by pattern/cell | DONE — all cells REJECT |
| W2a | Spread-adjusted EV and 9-axis root-cause diagnosis | DONE — no spread-adj flips; no LIVE/Shadow eligibility |
| W3 | 6 pair x 3 TF sweep, Bonferroni m=216 | BLOCKED unless detector geometry is revised |
| W4 | Shadow promote / LIVE candidate gate | Not eligible |

## Phase 0 Result

Production run over `data/cache/massive/USD_JPY_5m.parquet` generated 22,094 signals across all 12 patterns. Every pattern exceeded N=30; pivot tuple duplicate count was 0.

| Pattern | N | Avg duration | Avg height ATR |
|---|---:|---:|---:|
| ascending_triangle | 3,772 | 15.4 | 3.97 |
| rising_wedge | 1,747 | 17.4 | 4.67 |
| bull_flag | 376 | 12.4 | 2.61 |
| descending_triangle | 2,839 | 15.3 | 3.89 |
| falling_wedge | 1,251 | 16.9 | 4.54 |
| bear_flag | 261 | 12.3 | 2.76 |
| double_bottom | 4,666 | 8.4 | 2.38 |
| triple_bottom | 155 | 14.5 | 2.23 |
| inverse_head_shoulders | 999 | 18.0 | 3.06 |
| double_top | 4,869 | 8.4 | 2.36 |
| triple_top | 142 | 14.2 | 2.21 |
| head_shoulders | 1,017 | 18.0 | 3.00 |

## Next Task

Wave 2a confirmed no spread-adjusted PROMOTE/SHADOW flips. Before any W3 expansion, keep Wave 2b as detector-geometry diagnosis only; LIVE/Shadow exposure remains explicitly out of scope.

## Wave 2 Result (2026-05-03)

Backtest input was frozen W1P0 labels in `data/chart_patterns.db` (`USD_JPY`/`M5`, 22,094 rows) and `data/cache/massive/USD_JPY_5m.parquet` (2014-01-02 to 2026-04-30). Simulation used `signal_ts + 1 bar` open entry, fixed 1.5 pip USDJPY spread, signal-table SL/TP, max hold 20 bars, and entry-price-based MAFE/MFE.

Verdict summary:

| Mode | Trade fills | Verdict rows | PROMOTE | SHADOW | REJECT | INSUFFICIENT |
|---|---:|---:|---:|---:|---:|---:|
| isolated | 22,093 | 12 | 0 | 0 | 12 | 0 |
| arbitrated | 17,393 | 12 | 0 | 0 | 12 | 0 |
| reversed (wedge #2/#5) | 2,997 | 2 | 0 | 0 | 2 | 0 |

Wedge direction result:

| Pattern | Literal PF | Reversed PF | Direction note |
|---|---:|---:|---|
| rising_wedge | 0.79 | 0.77 | literal slightly better, both REJECT |
| falling_wedge | 0.74 | 0.88 | reversed better, but still REJECT |

Decision record: `knowledge-base/wiki/decisions/s6-w2-bt-2026-05-03.md`.
