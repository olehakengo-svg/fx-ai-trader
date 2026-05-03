# S6 Chart Pattern Detector (USDJPY M5)

- **Status**: PARKED 2026-05-04 — Wave 2b pre-registration BT confirmed no edge; ATR 12-pattern geometry on USD_JPY M5 not pursued further (no LIVE / Shadow exposure)
- **Stage**: 0 (BT_REJECTED / PARKED) — detector exists, BT edge not validated across 4 wave checkpoints (W1P0 / W2 / W2a / W2b)
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
| W2b | Top-3 London_NY_overlap candidates, rr=1.25, dual intrabar resolve | DONE — 18 INSUFFICIENT / 6 REJECT; no PROMOTE/SHADOW |
| W3 | 6 pair x 3 TF sweep, Bonferroni m=216 | BLOCKED unless W2b follow-up explicitly reopens scope |
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

Wave 2b confirmed no PROMOTE/SHADOW rows under the pre-registered top-3 London_NY_overlap diagnostic. C1/C2 remained N<30 on OOS_1; C3 reached OOS_1 N=58 but PF=1.18 below the SHADOW gate. Before any W3 expansion, decide whether to run Wave 2c regime deepdive or park S6; LIVE/Shadow exposure remains explicitly out of scope.

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

## Wave 2b Result (2026-05-04)

Pre-registration input was frozen W1P0 labels in `data/chart_patterns.db` and OHLC from `data/cache/massive/USD_JPY_5m.parquet`. Simulation used `signal_ts + 1 bar` open entry, `12 <= hour(signal_ts UTC) < 16` with entry also constrained to 12-15 UTC for the locked verification check, W2a empirical hour spread, frozen SL, recomputed `rr=1.25` TP, max hold 30 bars, and both `SL_FIRST` / `TP_FIRST` intrabar interpretations.

Verdict summary:

| Rows | PROMOTE | SHADOW | REJECT | INSUFFICIENT |
|---:|---:|---:|---:|---:|
| 24 | 0 | 0 | 6 | 18 |

OOS_1 main verdict:

| Candidate | Cell | SL_FIRST | TP_FIRST | Note |
|---|---|---|---|---|
| C1 | triple_bottom x London_NY_overlap x rr=1.25 | INSUFFICIENT, N=9, EV=-2.96, PF=0.79 | INSUFFICIENT, N=9, EV=-2.96, PF=0.79 | N<30 |
| C2 | triple_top x London_NY_overlap x rr=1.25 | INSUFFICIENT, N=5, EV=13.69, PF=5.84 | INSUFFICIENT, N=5, EV=13.69, PF=5.84 | N<30 |
| C3 | inverse_head_shoulders x London_NY_overlap x rr=1.25 | REJECT, N=58, EV=1.91, PF=1.18 | REJECT, N=58, EV=1.91, PF=1.18 | PF<1.2 SHADOW gate |

Decision record: `knowledge-base/wiki/decisions/s6-w2b-pre-reg-bt-2026-05-04.md`.
