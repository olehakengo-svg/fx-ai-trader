# USD/CAD + USD/CHF Pair Surface Final

Generated: 2026-05-18

## Verdict

ACCEPT.

Precedent confirmed:

- `git log --oneline -20` found `9a865564 Add AUD/NZD pair surface slots`.
- `git show --stat 9a865564` established the literal pattern across demo trader, OANDA bridge, app/API, data mapping, dashboard template, tier-master, KB, audit report, and tests.
- Completion wrapper commit `5b051089 feat(codex): complete 20260518-1351-aud-nzd-pair-surface` exists in `done/`, so this task was not aborted.

## Implementation

- Added `USD_CAD` and `USD_CHF` surface pair registration.
- Added `daytrade_1h_usdcad` and `daytrade_1h_usdchf` shadow-only slots with `auto_start=False`.
- Added OANDA bridge resolution for both instruments.
- Added dashboard sidebar/filter/JS labels/pip-value support for both pairs.
- Added API/HMM/pipeline/live-price surface mappings.
- Added MASSIVE parquet symbol aliases for `USDCAD=X` and `USDCHF=X`.
- Added tier-master and KB entries. `USD_CAD` is documented as Tier 1 #3 / Phase B Wave 1 candidate; `USD_CHF` as Tier 3 WATCH / Phase B Wave 1 candidate.
- Added `tests/test_usd_cad_usd_chf_pair_surface.py`.

## Verification

```text
python3 -m py_compile modules/demo_trader.py modules/oanda_bridge.py modules/data.py app.py tools/tier_integrity_check.py tests/test_usd_cad_usd_chf_pair_surface.py
PASS

python3 tools/sync_kb_index.py --write
python3 tools/tier_integrity_check.py --write
PASS

.venv/bin/python -m pytest -q tests/test_usd_cad_usd_chf_pair_surface.py tests/test_aud_nzd_pair_surface.py tests/test_risk_analytics_mc_lot_multiplier.py tests/test_edge_activation_review_fixes.py
24 passed in 7.61s
```

MASSIVE parquet pre-check:

```text
data/cache/massive/USD_CAD_1h.parquet
data/cache/massive/USD_CHF_1h.parquet
data/cache/massive/USD_CAD_4h.parquet
data/cache/massive/USD_CHF_4h.parquet
```

OANDA production tradability:

```text
configured= True
ok= True
USD_CAD= True
USD_CHF= True
```

Manual server check:

- `NO_AUTOSTART=1 PORT=5020 python3 app.py` failed because system Python lacks Flask.
- `NO_AUTOSTART=1 PORT=5020 .venv/bin/python app.py` started successfully.
- `curl -sS http://127.0.0.1:5020/api/demo/status` returned:

```json
{
  "USD_CAD": {"instrument": "USD_CAD", "modes": ["daytrade_1h_usdcad"]},
  "USD_CHF": {"instrument": "USD_CHF", "modes": ["daytrade_1h_usdchf"]}
}
```

## Commit

Commit SHA: `a24cb75e`

Changed files:

- `app.py`
- `final.md`
- `knowledge-base/wiki/index.md`
- `knowledge-base/wiki/tier-master.json`
- `knowledge-base/wiki/tier-master.md`
- `modules/data.py`
- `modules/demo_trader.py`
- `modules/oanda_bridge.py`
- `reports/aud_nzd_surface_audit/SURFACE_AUDIT.md`
- `templates/demo_analysis.html`
- `tests/test_usd_cad_usd_chf_pair_surface.py`
- `tools/tier_integrity_check.py`

Final stash check:

```text
git stash list: empty
```
