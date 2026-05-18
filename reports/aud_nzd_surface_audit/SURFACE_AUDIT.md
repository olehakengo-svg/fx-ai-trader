# AUD/NZD Surface Audit

Date: 2026-05-18

Target pairs: `AUD_JPY`, `NZD_JPY`, `AUD_USD`, `NZD_USD`, `EUR_AUD`

## Summary

| layer | file | 5 pair support | downstream impact |
|---|---|---:|---|
| demo_trader pair list | `modules/demo_trader.py` | 対応済 | `MODE_CONFIG` now exposes one `daytrade_1h_*` shadow slot per target pair; `/api/demo/status` includes both `modes` and `pairs` entries. All five slots are `auto_start=False`. |
| OANDA bridge instrument | `modules/oanda_bridge.py`, `modules/oanda_client.py` | 一部 | `SUPPORTED_INSTRUMENTS` resolves all five target pairs and Live account instruments verified tradable. Practice account verification could not complete because no practice credential env was available; no pair was disabled. |
| UI dashboard | `templates/demo_analysis.html` | 対応済 | Sidebar pair selector, JS `PAIRS`, `MODE_DEFS`, trade log labels, open-position labels, and pip-value maps include all five pairs. `static/` does not exist in this checkout. |
| API endpoints | `app.py`, `modules/demo_trader.py` | 対応済 | `/api/demo/status` returns target pairs in `pairs` and mode instruments. `/api/oanda/live` price polling list and BT pipeline instrument map include target pairs. `/api/risk/dashboard` remains pair-agnostic and now receives `by_instrument` output from risk analytics. |
| Strategy registration | `modules/demo_trader.py`, `app.py` | 対応済 | `price_shock_reversion` is registered as a qualified/universal sentinel strategy. No Live flag or promotion flag was enabled. |
| Risk analytics | `modules/risk_analytics.py` | 対応済 | `compute_risk_dashboard()` accepts synthetic positions for all five pairs without `KeyError` and emits per-instrument aggregation under `by_instrument`. |
| tier-master | `knowledge-base/wiki/tier-master.json`, `knowledge-base/wiki/tier-master.md`, `tools/tier_integrity_check.py` | 対応済 | `price_shock_reversion` is listed as `UNIVERSAL_SENTINEL`; Phase B-1 shadow candidate pairs are listed separately so they are visible without Live promotion. |
| KB index | `knowledge-base/wiki/index.md`, `tools/sync_kb_index.py` | 対応済 | Auto-synced portfolio includes `price_shock_reversion`; System State lists the five Phase B-1 shadow candidate pair slots. |

## Changed Files Required By Audit

- `modules/demo_trader.py`
- `modules/oanda_bridge.py`
- `modules/oanda_client.py`
- `modules/data.py`
- `modules/risk_analytics.py`
- `app.py`
- `templates/demo_analysis.html`
- `tools/tier_integrity_check.py`
- `knowledge-base/wiki/index.md`
- `knowledge-base/wiki/tier-master.md`
- `knowledge-base/wiki/tier-master.json`
- `tests/test_aud_nzd_pair_surface.py`

## Downstream Loading Map

- `app.py` imports `_demo_trader` and returns `DemoTrader.get_status()` through `/api/demo/status`.
- `app.py` uses `modules.risk_analytics.compute_risk_dashboard()` for `/api/risk/dashboard`.
- `modules/demo_trader.py` constructs `OandaBridge` and passes `instrument` through `open_trade()` only when existing promotion gates allow OANDA transfer.
- `templates/demo_analysis.html` is rendered by `/demo-analysis`.
- `tools/sync_kb_index.py --write` reads `modules/demo_trader.py` and rewrites the portfolio block in `knowledge-base/wiki/index.md`.
- `tools/tier_integrity_check.py --write` reads `modules/demo_trader.py`, discovers strategy files, and rewrites `knowledge-base/wiki/tier-master.{md,json}`.

## Repro Commands

```bash
grep -RInE "USD_JPY|EUR_USD|AUD_JPY|NZD_JPY|AUD_USD|NZD_USD|EUR_AUD|SUPPORTED_PAIRS|QUALIFIED_TYPES|STRATEGY_TYPES" modules app.py templates static knowledge-base tests tools 2>/dev/null
grep -RInE "route\\(|api/demo/status|api/demo/trades|api/risk/dashboard|risk/dashboard|demo/status" app.py modules templates static tests 2>/dev/null
find data/cache/massive -maxdepth 1 -type f \( -name 'AUD_JPY*' -o -name 'NZD_JPY*' -o -name 'AUD_USD*' -o -name 'NZD_USD*' -o -name 'EUR_AUD*' \) | sort
python3 -m py_compile modules/demo_trader.py modules/oanda_bridge.py modules/oanda_client.py modules/data.py modules/risk_analytics.py app.py tools/tier_integrity_check.py
.venv/bin/python -m pytest --collect-only tests/test_aud_nzd_pair_surface.py
.venv/bin/python -m pytest tests/test_aud_nzd_pair_surface.py tests/test_risk_analytics_mc_lot_multiplier.py tests/test_edge_activation_review_fixes.py
python3 tools/sync_kb_index.py --write
python3 tools/tier_integrity_check.py --write
NO_AUTOSTART=1 PORT=5018 .venv/bin/python app.py
curl -sS http://127.0.0.1:5018/api/demo/status
curl -sS http://127.0.0.1:5018/api/risk/dashboard
```

Note: plain `python3 app.py` failed in this container because the system Python lacks Flask; `.venv/bin/python app.py` was used for the actual local server verification.

## OANDA Tradability

- Live account: `AUD_JPY`, `NZD_JPY`, `AUD_USD`, `NZD_USD`, `EUR_AUD` all returned by `OandaClient.list_instruments()`.
- Practice account: not verified. This environment has no `OANDA_PRACTICE_TOKEN` / `OANDA_PRACTICE_ACCOUNT_ID`; attempting the practice base URL with available credentials returned 401 insufficient authorization.

No target pair was marked `Shadow only / OANDA execution disabled` because Live tradability passed and Practice could not be assessed with valid practice credentials.
