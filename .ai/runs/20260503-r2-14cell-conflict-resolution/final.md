# R2 14-cell conflict resolution final

Status: ACCEPT

## Summary

Implemented the R2 TRUE_LIVE 14-cell stop LOCK in the runtime tier source.
The task document described `tier-master.json` as the edit target, but the
actual OANDA gate reads `DemoTrader._PAIR_DEMOTED` / `_PAIR_PROMOTED`.
Therefore the runtime source was updated first, then `tier-master.md/json`
were regenerated from `tools/tier_integrity_check.py --write`.

## Files changed

- `modules/demo_trader.py`
- `knowledge-base/wiki/tier-master.md`
- `knowledge-base/wiki/tier-master.json`
- `knowledge-base/wiki/strategies/bb-squeeze-breakout.md`
- `tests/test_r2_14cell_lock.py`
- `.ai/runs/20260503-r2-14cell-conflict-resolution/final.md`

## Tier changes

Removed from `PAIR_PROMOTED`:

- `bb_squeeze_breakout × USD_JPY`
- `vix_carry_unwind × USD_JPY`

Added to `PAIR_DEMOTED`:

- `vwap_mean_reversion × GBP_USD`
- `vix_carry_unwind × USD_JPY`
- `sr_channel_reversal × USD_JPY`
- `bb_rsi_reversion × USD_JPY`
- `session_time_bias × GBP_USD`
- `bb_squeeze_breakout × USD_JPY`
- `vol_surge_detector × USD_JPY`
- `v_reversal × USD_JPY`
- `trend_rebound × USD_JPY`
- `sr_channel_reversal × EUR_USD`

Already in `PAIR_DEMOTED`:

- `bb_rsi_reversion × EUR_USD`
- `engulfing_bb × USD_JPY`
- `engulfing_bb × EUR_USD`
- `stoch_trend_pullback × USD_JPY`

Also removed stale pair-level live overrides:

- `bb_squeeze_breakout × USD_JPY` from `_PAIR_LOT_BOOST`
- `vix_carry_unwind × USD_JPY` from `_QUICK_HARVEST_EXEMPT`

## Drift table

`python3 tools/r2_strategy_instrument_counterfactual.py --dry-run --trades /tmp/live-trades-20260503.json --mc-iterations 1000 --mc-horizon 60`

Bucket split: TRUE_LIVE=371 (-254.6p), FLAG_DRIFT=140 (-132.4p), SHADOW=3819 (-4985.6p).

Counterfactual: aggregate raw Kelly `-0.1326 -> -0.0028`; MC60d `0.8650 -> 0.0090`; actions=14.

| Strategy | Instrument | N | EV | Raw Kelly | Action |
|---|---|---:|---:|---:|---|
| vwap_mean_reversion | GBP_USD | 5 | -11.62 | -9.6833 | STOP_OANDA |
| vix_carry_unwind | USD_JPY | 7 | -6.04 | -0.4111 | STOP_OANDA |
| sr_channel_reversal | USD_JPY | 22 | -1.40 | -0.5469 | STOP_OANDA |
| bb_rsi_reversion | USD_JPY | 58 | -0.52 | -0.1503 | STOP_OANDA |
| session_time_bias | GBP_USD | 7 | -4.00 | -3.0769 | STOP_OANDA |
| bb_squeeze_breakout | USD_JPY | 9 | -1.40 | -0.6364 | STOP_OANDA |
| bb_rsi_reversion | EUR_USD | 12 | -0.97 | -0.2283 | STOP_OANDA |
| vol_surge_detector | USD_JPY | 26 | -0.36 | -0.1212 | STOP_OANDA |
| engulfing_bb | USD_JPY | 9 | -0.83 | -0.3049 | STOP_OANDA |
| engulfing_bb | EUR_USD | 6 | -0.98 | -0.1513 | STOP_OANDA |
| v_reversal | USD_JPY | 5 | -0.98 | -0.1114 | STOP_OANDA |
| trend_rebound | USD_JPY | 8 | -0.50 | -0.1630 | STOP_OANDA |
| sr_channel_reversal | EUR_USD | 8 | -0.49 | -0.0739 | STOP_OANDA |
| stoch_trend_pullback | USD_JPY | 17 | -0.15 | -0.0376 | STOP_OANDA |

## Verification

- `python3 -m pytest -q tests/test_r2_14cell_lock.py`: 3 passed
- `python3 tools/tier_integrity_check.py --write`: wrote `tier-master.md/json`, no ERROR/WARN
- `python3 tools/tier_integrity_check.py --check`: pass, no ERROR/WARN
- `python3 tools/strategies_drift_check.py`: all 81 pages clean
- `python3 -m pytest -q tests/test_r2_14cell_lock.py tests/test_strategies_drift_check.py tests/test_oanda_passthrough_gap_audit.py`: 18 passed

Full-suite verification is run by pre-commit before the deployment commit.

## Residual risks

- Counterfactual uses `/tmp/live-trades-20260503.json`; a fresh Render snapshot was unavailable in the prior run.
- Verdict remains NEEDS_MORE_EVIDENCE, not full Gate0 recovery: raw Kelly improves to near-zero but not positive.
- `vix_carry_unwind` remains in strategy-level lot boost for non-USD_JPY pairs; this task only blocks the bleeding USD_JPY cell.

## Next

- Run a 7-day post-merge audit after live N accumulates.
- Continue `r2-tier1-hour-bucket-extension` if raw Kelly remains slightly negative.
- Only after Gate0 stabilizes, register `sr_channel_reversal × EUR_USD 5m` as the A3 simple Shadow candidate.
