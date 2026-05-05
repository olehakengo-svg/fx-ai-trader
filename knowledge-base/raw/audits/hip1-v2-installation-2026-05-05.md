# HIP-1 v2 Installation Report

- Timestamp: `2026-05-05T02:42:46Z`
- Scope: BT/offline-only holdout guard, fail-safe default OFF
- Status: installed

## Implementation Summary

- Added `data/_holdout_locked/MANIFEST.json` with v2 lock window `2025-11-04T00:00:00Z` to `2026-05-04T00:00:00Z`.
- Added `modules.data._apply_holdout_guard(df, source_path)`.
- Wired the guard only inside `_load_parquet_cache_fallback()`.
- Default behavior is fail-safe no-op: `FX_HOLDOUT_GUARD != "1"` returns the original dataframe unchanged with no logging.
- Validation mode behavior: `FX_HOLDOUT_GUARD=1 FX_HOLDOUT_VALIDATION=1` returns the original dataframe unchanged and logs `HOLDOUT VALIDATION MODE`.
- Added local pre-commit hook script for manifest edits and validation-mode run reports.
- Added `tools/audit/holdout_validation_runner.py` skeleton; it sets `os.environ["FX_HOLDOUT_GUARD"] = "1"` immediately after imports.

## Required Reading Note

The requested v2 spec path `knowledge-base/wiki/decisions/holdout-isolation-protocol-2026-05-04.md` was absent in this checkout. Implementation followed the v2 contract supplied in the task prompt. The prior HOLD report was available as `.ai/runs/20260505-004642-meta-hip1-implementation/final.md`.

## LIVE Impact Zero Confirmation

LIVE 影響ゼロ確認: env 未設定で `fetch_ohlcv` 経路の挙動が pre-implementation と完全同値。

Verification method:

1. Created a detached `HEAD` worktree at `/tmp/fx-ai-trader-pre-hip1` for pre-implementation behavior.
2. Ran the same dry-run command from the pre tree and the modified tree with `FX_HOLDOUT_GUARD` unset.
3. Compared stdout/stderr.

Result:

```text
pre_status=0 post_status=0
diff_status=0
  62 /tmp/pre-hip1-venv.txt
  62 /tmp/post-hip1-venv-rerun.txt
   0 /tmp/hip1-live-diff-rerun.txt
```

System `python3` lacks project dependencies in this container, so the bare command failed before project code with `ModuleNotFoundError: No module named 'numpy'`. The regression comparison above used the repository `.venv`, which contains the project dependencies.

## Opt-in BT Cut Verification

Command:

```bash
BT_MODE=1 FX_HOLDOUT_GUARD=1 .venv/bin/python - <<'PY'
from modules.data import fetch_ohlcv

df = fetch_ohlcv('USD_JPY', period='400d', interval='5m')
print(f'rows={len(df)}, max_date={df.index.max()}')
PY
```

Output:

```text
[massive-parquet/5m] USD_JPY 44921 bars (cache_ts=2026-05-03T16:00:29.884824+00:00)
rows=44921, max_date=2025-11-03 23:55:00+00:00
```

Result: PASS. The max returned timestamp is before the lock window start.

## Verification Summary

```text
.venv/bin/python -m pytest tests/test_holdout_guard.py -v
8 passed

.venv/bin/python -m pytest tests/test_fetch_ohlcv_bt_mode.py tests/test_bt_data_loader_parquet_fallback.py -v
5 passed

.venv/bin/python -m ruff check modules/data.py tools/audit/holdout_validation_runner.py tools/precommit/check_holdout_manifest.py
All checks passed!

PATH="$PWD/.venv/bin:$PATH" pre-commit run --all-files
Passed

PATH="$PWD/.venv/bin:$PATH" pre-commit run --files data/_holdout_locked/MANIFEST.json
Failed as expected; manifest edit rejected without --allow-holdout-edit.

python3 tools/audit/holdout_validation_runner.py --help
exit 0
```

## BT Runner Note

Existing BT runners were not changed in this task. To opt into holdout protection until runner-level integration is implemented, launch BT commands with:

```bash
FX_HOLDOUT_GUARD=1 python3 tools/bt/...
```

For local Massive parquet-first BT paths, use `BT_MODE=1 FX_HOLDOUT_GUARD=1 ...` so the loader reads the cache and applies the guard before returning bars.

## Remaining Risks

- Runner-level opt-in is still manual until the future BT runner task.
- The canonical v2 spec file was absent from this checkout, so this report records implementation against the prompt contract.
