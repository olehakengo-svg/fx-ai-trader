# S6 Chart Pattern Detector

Status: Wave 1 Phase 0 detector implemented; production verdict blocked by missing local parquet.
Date: 2026-05-03
Scope: detector + label regression only. No BT, Shadow, LIVE, OANDA, Tier registration, or strategy routing changes.

## Wave Plan

| Wave | Scope | Status |
|---|---|---|
| W1P0 | 1 pair x 1 TF x 12 pattern detector + deterministic fixture | Implemented, synthetic tests pass |
| W2 | USD_JPY M5 12.3y BT and cell verdict | Next task |
| W3 | 6 pair x 3 TF sweep, Bonferroni m=216 | Out of scope |
| W4 | Shadow promote / LIVE candidate via W3-1 H1 gate | Out of scope |

## Locked Geometry

Common primitives:
- Swing pivot `k=3`: strict high/low vs 3 bars on both sides.
- ATR: 14-period Wilder ATR on M5 OHLC.
- Trendline: latest two same-kind pivots.
- Locked thresholds: `EPS_FLAT=0.05*ATR/bar`, `EPS_SLOPE=0.10*ATR/bar`, `MIN_PATTERN_HEIGHT=1.5*ATR`, `MIN_DURATION_BARS=5`, `MAX_DURATION_BARS=80`, `BREAKOUT_BUFFER=0.10*ATR`, `SL_BUFFER=0.50*ATR`, `PIVOT_TOLERANCE=0.30*ATR`.

Pattern set:

| ID | Name | Direction | Detector condition |
|---|---|---|---|
| 1 | ascending_triangle | BUY | flat upper highs, rising lows, alternating pivots, height gate |
| 2 | rising_wedge | BUY | rising upper/lower lines, lower slope greater than upper, convergence >=50% |
| 3 | bull_flag | BUY | 10-20 bar pole >=3 ATR, falling parallel flag, flag amplitude <=0.5 pole |
| 4 | descending_triangle | SELL | mirror of ascending triangle |
| 5 | falling_wedge | SELL | falling upper/lower lines, upper line falls faster into lower line, convergence >=50% |
| 6 | bear_flag | SELL | mirror of bull flag |
| 7 | double_bottom | BUY | two lows within tolerance, intervening high neckline, 5-50 bar spacing |
| 8 | triple_bottom | BUY | three lows within tolerance, two intermediate highs flat within 0.4 ATR |
| 9 | inverse_head_shoulders | BUY | lower head, shoulders within 0.5 ATR, time symmetry ratio <=0.4 |
| 10 | double_top | SELL | mirror of double bottom |
| 11 | triple_top | SELL | mirror of triple bottom |
| 12 | head_shoulders | SELL | mirror of inverse head and shoulders |

Entry/SL/TP:
- Entry is bar-close only. Wick-only breakouts are ignored.
- BUY trigger: `close[t] > breakout_level + 0.10*ATR`; SELL trigger: `close[t] < breakout_level - 0.10*ATR`.
- BUY SL: min pattern low pivots minus `0.50*ATR`; SELL SL: max pattern high pivots plus `0.50*ATR`.
- TP uses measured move: pattern height for triangle/wedge/flag, neckline-to-extreme for double/triple and H&S.
- Re-entry dedup key: `(pattern_id, pivot_anchor_ts, pivot_opposite_ts)` with in-memory fired set plus SQLite `UNIQUE`.

## Phase 0 Result

Implemented files:
- `tools/s6_chart_pattern_detector.py`
- `tools/s6_run_w1p0.py`
- `tests/test_s6_chart_pattern_detector.py`
- `tests/fixtures/manual_chart_pattern_labels.csv`

Verification completed:
- `python3 tools/s6_chart_pattern_detector.py --self-test`: 12/12 synthetic hit.
- `python3 -m pytest -q tests/test_s6_chart_pattern_detector.py`: 29 passed.
- Bar-close gate is covered by a wick-only breakout regression test.
- Re-entry dedup is covered by SQLite insert-or-ignore and duplicate pivot tuple test.
- SL/TP/Entry calculations are checked against raw geometry for all 12 patterns.

Production verification blocked:
- `data/cache/massive/USD_JPY_5m.parquet` is absent in this checkout; `data/` does not exist.
- Therefore USD_JPY M5 12.3y signal counts, duration distribution, height distribution, and `data/chart_patterns.db` population were not produced here.

## Next Task

After the required parquet is present, rerun:

```bash
python3 tools/s6_run_w1p0.py --pair USD_JPY --tf M5 \
  --parquet data/cache/massive/USD_JPY_5m.parquet \
  --db data/chart_patterns.db
```

If all 12 patterns produce N>=30 and total N>=360, proceed to Wave 2 BT spec proposal. If total N<360 or 3+ patterns have N<30, keep Wave 1 open and analyze which locked geometry clauses are too restrictive before proposing any threshold unlock task.
