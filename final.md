# feat(regime): universal dow_regime tagging

## Scope

- Added `demo_trades.dow_regime` as a separate Dow Theory H1 ADX/ER/BBW observation tag.
- Left existing `regime` JSON, `mtf_regime`, score-race logic, signal generation logic, OANDA bridge, and live runner untouched.
- Extended trade insertion through `DemoDB.open_trade(..., dow_regime=None)` so omitted values persist as `NULL`.
- Added best-effort signal-time tagging in `DemoTrader._compute_dow_regime()` with failure logged and `None` returned, so classifier failure never blocks entry.
- Added `tools/dow_regime_backfill.py`; dry-run is the default, `--apply` is required for writes, and writes are chunked.
- Added real classifier/cache-backed tests in `tests/test_dow_regime_tagging.py`.

## Commit

Implementation commit: `4c2aa8cc feat(regime): universal dow_regime tagging + classifier consensus consultation [rule:R1]`

Completion record commit: `beda4a6f docs(codex): complete universal dow_regime tagging task`

## Verification

```text
python3 -m pytest tests/test_dow_regime_tagging.py
/usr/bin/python3: No module named pytest

./.venv/bin/python -m pytest tests/test_dow_regime_tagging.py
4 passed in 2.64s

./.venv/bin/python -m pytest tests/test_v2_regime_tagging.py tests/test_cross_pair_confluence.py
10 passed in 3.56s
```

## Guardrails

- Existing `regime` column not edited.
- Existing `mtf_regime` column not edited.
- Score-race and signal generation logic not edited.
- `lib/regime_classifier.py` thresholds not changed.
- OANDA bridge/live runner not edited.
- Backfill script was not run against production DB.
